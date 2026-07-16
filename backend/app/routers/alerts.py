"""
Alert and community report API routers.

Community reports, their advice threads, and sent-alert history are persisted
to the shared database (Neon Postgres in production, SQLite locally) so they
survive restarts and are visible to both the web dashboard and the mobile app.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.db_models import AdviceORM, AlertORM, ReportORM
from app.models.schemas import (
    AdviceSubmission, AlertRecord, AlertRequest, AlertResponse,
    CommunityReport, ReportAdvice, ReportEdit, ReportStatus, ReportSubmission,
)
from app.services.advisory import generate_advisory
from app.services.alerts import send_sms_alert
from app.services.flood_data import fetch_river_discharge
from app.services.flood_model import compute_flood_risk
from app.services.impact import compute_impact
from app.services.weather_data import fetch_upstream_rainfall

import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer()

async def verify_supabase_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not settings.supabase_jwt_secret:
        return None # Auth disabled if no secret
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}")


import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directory for report photos.
# NOTE: on ephemeral hosts (e.g. Render/Koyeb free tier) this disk is wiped on
# redeploy. The report *record* below is durable in the database; for durable
# photo binaries, point photo storage at object storage (Cloudflare R2 / S3).
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "reports"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_basins_path = Path(__file__).parent.parent / "data" / "basins.json"


def _get_basin_config(basin_id: str):
    from app.models.schemas import BasinConfig
    with open(_basins_path) as f:
        data = json.load(f)
    for b in data["basins"]:
        if b["id"] == basin_id:
            return BasinConfig(**b)
    raise HTTPException(status_code=404, detail=f"Basin '{basin_id}' not found")


# ─── ORM → Pydantic mappers ──────────────────────────────────────────────────

def _to_report_schema(row: ReportORM) -> CommunityReport:
    """Convert a ReportORM row (with its advice) to the API schema."""
    return CommunityReport(
        id=row.id,
        basin_id=row.basin_id,
        status=ReportStatus(row.status),
        latitude=row.latitude,
        longitude=row.longitude,
        description=row.description,
        reporter_name=row.reporter_name,
        photo_url=row.photo_url,
        submitted_at=row.submitted_at,
        advice=[
            ReportAdvice(
                id=a.id,
                message=a.message,
                author_name=a.author_name,
                author_role=a.author_role,
                created_at=a.created_at,
            )
            for a in row.advice
        ],
    )


# ─── Alert Endpoints ─────────────────────────────────────────────────────────

@router.post("/alerts/send", response_model=AlertResponse, status_code=202)
async def send_alert(
    request: AlertRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_payload: dict = Depends(verify_supabase_jwt),
):
    """
    Send an SMS alert for a basin (Load Balanced).

    Checks the database to ensure we haven't already alerted this basin within
    the last 12 hours (caching for safety to prevent SMS spam).
    If clear, queues the heavy LLM and SMS network tasks to run in the background.
    """
    basin = _get_basin_config(request.basin_id)
    
    # 1. Caching / Safety Check: Has an alert been sent in the last 12 hours?
    stmt = select(AlertORM).where(
        AlertORM.basin_id == request.basin_id,
        AlertORM.risk_level.in_(["HIGH", "EXTREME"]) # Only check for high risk/extreme floods
    ).order_by(AlertORM.id.desc()).limit(1)
    
    recent_alert = (await session.scalars(stmt)).first()
    if recent_alert:
        # Check time difference
        time_since = datetime.now(recent_alert.sent_at.tzinfo) - recent_alert.sent_at
        if time_since.total_seconds() < 12 * 3600:
            return AlertResponse(
                success=True,
                message="Alert skipped: An alert was already sent for this basin within the last 12 hours.",
                sms_count=0
            )

    # 2. Queue Background Task
    background_tasks.add_task(
        _process_and_send_alert,
        request=request,
        basin=basin
    )
    
    return AlertResponse(
        success=True,
        message="Alert processing queued successfully.",
        sms_count=len(request.phone_numbers)
    )

async def _process_and_send_alert(request: AlertRequest, basin):
    """Background task to generate advisory and send SMS."""
    # We need a new DB session since this runs in the background
    from app.db import SessionLocal
    
    try:
        # Generate the advisory — fetch both data feeds concurrently
        discharge_data, rainfall_data = await asyncio.gather(
            fetch_river_discharge(
                basin.gauge_point.latitude,
                basin.gauge_point.longitude,
                forecast_days=3,
                past_days=7,
            ),
            fetch_upstream_rainfall(
                basin.upstream_point.latitude,
                basin.upstream_point.longitude,
                forecast_days=3,
                past_days=7,
            ),
        )

        risk = compute_flood_risk(basin, discharge_data, rainfall_data)
        impact = compute_impact(request.basin_id, risk.risk_level)

        advisory = await generate_advisory(
            risk=risk,
            impact=impact,
            basin_name=basin.name,
            river_name=basin.river,
            country=basin.country,
            role=request.role,
            language=request.language,
        )

        # Format SMS text
        sms_text = f"{advisory.title}\n\n{advisory.body}\n\n"
        sms_text += "\n".join(f"• {a}" for a in advisory.actions[:3])  # Max 3 actions for SMS

        # Send via Africa's Talking
        await send_sms_alert(sms_text, request.phone_numbers)

        # Record alert to the database
        async with SessionLocal() as session:
            session.add(AlertORM(
                basin_id=request.basin_id,
                risk_level=risk.risk_level.value,
                role=request.role.value,
                language=request.language.value,
                recipients_count=len(request.phone_numbers),
                advisory_text=sms_text,
            ))
            await session.commit()
            
    except Exception as e:
        logger.error(f"Failed to process background alert for {basin.id}: {e}")


@router.get("/alerts/history", response_model=list[AlertRecord])
async def get_alert_history(
    basin_id: str = Query(None, description="Filter by basin ID"),
    limit: int = Query(50, description="Max number of records"),
    session: AsyncSession = Depends(get_session),
):
    """Get the history of sent alerts (most recent last)."""
    stmt = select(AlertORM)
    if basin_id:
        stmt = stmt.where(AlertORM.basin_id == basin_id)
    stmt = stmt.order_by(AlertORM.id.desc()).limit(limit)

    rows = list(reversed((await session.scalars(stmt)).all()))
    from app.models.schemas import RiskLevel, UserRole, Language
    return [
        AlertRecord(
            id=r.id,
            basin_id=r.basin_id,
            risk_level=RiskLevel(r.risk_level),
            role=UserRole(r.role),
            language=Language(r.language),
            recipients_count=r.recipients_count,
            sent_at=r.sent_at,
            advisory_text=r.advisory_text,
        )
        for r in rows
    ]


# ─── Community Report Endpoints ──────────────────────────────────────────────

@router.post("/reports", response_model=CommunityReport)
async def submit_report(
    report: ReportSubmission,
    session: AsyncSession = Depends(get_session),
):
    """
    Submit a community report from the field.

    Community members can report ground conditions via the app or SMS reply.
    Reports appear as pins on the map and serve as ground truth
    for model validation. Persisted to the shared database.
    """
    row = ReportORM(
        basin_id=report.basin_id,
        status=report.status.value,
        latitude=report.latitude,
        longitude=report.longitude,
        description=report.description,
        reporter_name=report.reporter_name,
        photo_url=report.photo_url,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(f"Community report #{row.id} submitted for {report.basin_id}")

    return _to_report_schema(row)


@router.post("/reports/upload", response_model=CommunityReport)
async def submit_report_with_photo(
    basin_id: str = Form(...),
    status: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Submit a community report with an optional photo upload.

    Accepts multipart/form-data so the mobile app can send the compressed
    JPEG binary alongside the report fields in a single request.
    """
    # Validate status before we touch the disk or database.
    status_enum = ReportStatus(status)

    row = ReportORM(
        basin_id=basin_id,
        status=status_enum.value,
        latitude=latitude,
        longitude=longitude,
        description=description,
        reporter_name=reporter_name,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    if photo and photo.filename:
        # Generate a unique filename to avoid collisions
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{row.id}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = UPLOAD_DIR / filename

        contents = await photo.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        row.photo_url = f"/uploads/reports/{filename}"
        await session.commit()
        await session.refresh(row)
        logger.info(f"Saved report photo: {filepath} ({len(contents)} bytes)")

    logger.info(f"Community report #{row.id} (with photo) submitted for {basin_id}")
    return _to_report_schema(row)


@router.get("/reports", response_model=list[CommunityReport])
async def get_reports(
    basin_id: str = Query(None, description="Filter by basin ID"),
    limit: int = Query(50, description="Max number of records"),
    session: AsyncSession = Depends(get_session),
):
    """Get community reports (most recent last), optionally filtered by basin."""
    stmt = select(ReportORM)
    if basin_id:
        stmt = stmt.where(ReportORM.basin_id == basin_id)
    stmt = stmt.order_by(ReportORM.id.desc()).limit(limit)

    rows = list(reversed((await session.scalars(stmt)).all()))
    return [_to_report_schema(r) for r in rows]


@router.patch("/reports/{report_id}", response_model=CommunityReport)
async def edit_report(
    report_id: int,
    edit: ReportEdit,
    session: AsyncSession = Depends(get_session),
):
    """
    Edit a community report's status, description, or reporter name.

    Open to anyone using the app or the mobile app — Tayari is a shared,
    community-owned board, so a reporter can correct their own report and a
    coordinator can update a stale status (e.g. from `water_rising` to
    `all_clear`). Only the fields provided in the request are changed.
    """
    row = await session.get(ReportORM, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Report #{report_id} not found")

    if edit.status is not None:
        row.status = edit.status.value
    if edit.description is not None:
        row.description = edit.description
    if edit.reporter_name is not None:
        row.reporter_name = edit.reporter_name

    await session.commit()
    await session.refresh(row)
    logger.info(f"Report #{report_id} edited")
    return _to_report_schema(row)


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a community report and its advice thread.

    Also removes the uploaded photo from disk if present. Cascade on the advice
    relationship clears the thread automatically.
    """
    row = await session.get(ReportORM, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Report #{report_id} not found")

    # Best-effort cleanup of the on-disk photo.
    if row.photo_url:
        photo_path = Path(__file__).parent.parent.parent / row.photo_url.lstrip("/")
        try:
            photo_path.unlink(missing_ok=True)
        except OSError:
            logger.warning(f"Could not delete photo for report #{report_id}")

    await session.delete(row)
    await session.commit()
    logger.info(f"Report #{report_id} deleted")


@router.delete("/reports/{report_id}/advice/{advice_id}", response_model=CommunityReport)
async def delete_report_advice(
    report_id: int,
    advice_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a single piece of advice from a report's thread."""
    advice_row = await session.get(AdviceORM, advice_id)
    if advice_row is None or advice_row.report_id != report_id:
        raise HTTPException(
            status_code=404,
            detail=f"Advice #{advice_id} not found on report #{report_id}",
        )
    await session.delete(advice_row)
    await session.commit()

    row = await session.get(ReportORM, report_id)
    return _to_report_schema(row)


@router.post("/reports/{report_id}/advice", response_model=CommunityReport)
async def add_report_advice(
    report_id: int,
    advice: AdviceSubmission,
    session: AsyncSession = Depends(get_session),
):
    """
    Attach advice or guidance to a community report.

    Coordinators, responders, and fellow community members can respond to a
    field report with concrete guidance — where to evacuate, which road is
    passable, who to contact. The advice thread is returned with the report.
    """
    row = await session.get(ReportORM, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Report #{report_id} not found")

    session.add(AdviceORM(
        report_id=report_id,
        message=advice.message.strip(),
        author_name=advice.author_name,
        author_role=advice.author_role,
    ))
    await session.commit()
    await session.refresh(row)
    logger.info(f"Advice added to report #{report_id}")

    return _to_report_schema(row)
