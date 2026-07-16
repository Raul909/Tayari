"""
One-time migration of legacy JSON-file community reports into the database.

Earlier versions of Tayari stored community reports in
``app/data/community_reports.json``. This importer runs on startup and, if that
file exists and the database has no reports yet, copies them (with their advice
threads) into the durable database. It renames the file afterwards so the
import never runs twice. Safe to keep indefinitely; a no-op once migrated.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.db_models import AdviceORM, ReportORM

logger = logging.getLogger(__name__)

_LEGACY_STORE = Path(__file__).parent.parent / "data" / "community_reports.json"


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def migrate_legacy_reports() -> None:
    if not _LEGACY_STORE.exists():
        return

    async with SessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(ReportORM))
        if existing:
            # DB already has reports — don't double-import. Retire the file.
            _retire_legacy_file()
            return

        try:
            raw = json.loads(_LEGACY_STORE.read_text())
        except Exception:
            logger.exception("Could not read legacy reports file — skipping import")
            return

        imported = 0
        for r in raw.get("reports", []):
            try:
                row = ReportORM(
                    basin_id=r["basin_id"],
                    status=r["status"],
                    latitude=r["latitude"],
                    longitude=r["longitude"],
                    description=r.get("description"),
                    reporter_name=r.get("reporter_name"),
                    photo_url=r.get("photo_url"),
                    submitted_at=_parse_dt(r.get("submitted_at")) or datetime.utcnow(),
                )
                for a in r.get("advice", []):
                    row.advice.append(AdviceORM(
                        message=a["message"],
                        author_name=a.get("author_name"),
                        author_role=a.get("author_role"),
                        created_at=_parse_dt(a.get("created_at")) or datetime.utcnow(),
                    ))
                session.add(row)
                imported += 1
            except (KeyError, TypeError):
                logger.exception("Skipping malformed legacy report: %r", r)

        if imported:
            await session.commit()
            logger.info(f"   Migrated {imported} legacy community report(s) into the database")

    _retire_legacy_file()


def _retire_legacy_file() -> None:
    try:
        _LEGACY_STORE.rename(_LEGACY_STORE.with_suffix(".json.imported"))
    except OSError:
        logger.warning("Could not rename legacy reports file after import")
