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
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, Request
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.limiter import limiter

from app.db import get_session
from app.models.db_models import AdviceORM, AlertORM, ReportORM, UserProfileORM
from app.models.schemas import (
    AdviceSubmission, AlertRecord, AlertRequest, AlertResponse,
    CommunityReport, ReportAdvice, ReportEdit, ReportStatus, ReportSubmission,
    RiskLevel,
)
from app.services.advisory import generate_advisory
from app.services.alerts import send_sms_alert
from app.services.auth import get_current_user, get_optional_user
from app.services.flood_data import fetch_river_discharge
from app.services.flood_model import compute_flood_risk
from app.services.impact import compute_impact
from app.services.weather_data import fetch_upstream_rainfall

import json
import time

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory tracking of phone number dispatches with timestamp to prevent duplicate alerting
_phone_send_history: dict[str, float] = {}
PHONE_COOLDOWN_SECONDS = 300  # 5 minutes cooldown per phone number


# Upload directory for report photos.
# NOTE: on ephemeral hosts (e.g. Render/Koyeb free tier) this disk is wiped on
# redeploy. The report *record* below is durable in the database; for durable
# photo binaries, point photo storage at object storage (Cloudflare R2 / S3).
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "reports"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_basins_path = Path(__file__).parent.parent / "data" / "basins.json"

# One lock per basin serializes concurrent /alerts/send calls for that basin so
# the 12-hour dedup check-then-act below can't race two simultaneous requests
# into both queuing (and paying for) a duplicate Twilio SMS blast.
_alert_locks: dict[str, asyncio.Lock] = {}


def _get_alert_lock(basin_id: str) -> asyncio.Lock:
    lock = _alert_locks.get(basin_id)
    if lock is None:
        lock = _alert_locks[basin_id] = asyncio.Lock()
    return lock


# Risk levels a sent AlertORM row can carry once fully processed — used to
# filter out in-flight "PENDING" reservation rows from the public history feed.
_TERMINAL_RISK_LEVELS = [r.value for r in RiskLevel]


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
@limiter.limit("10/minute")
async def send_alert(
    request: Request,
    alert_req: AlertRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user: Optional[UserProfileORM] = Depends(get_optional_user),
):
    """
    Send an SMS alert for a basin (Load Balanced).

    Accessible to all users (guests and signed-in members).
    Enforces a 5-minute per-phone-number rate limit to prevent sending
    alerts to the same phone number repeatedly within a short window.
    """
    # 1. Per-phone rate limit check
    now = time.time()
    rate_limited_phones = []
    valid_phones = []
    for phone in alert_req.phone_numbers:
        last_sent = _phone_send_history.get(phone, 0)
        if (now - last_sent) < PHONE_COOLDOWN_SECONDS:
            rate_limited_phones.append(phone)
        else:
            valid_phones.append(phone)

    if rate_limited_phones:
        mins_remaining = int((PHONE_COOLDOWN_SECONDS - (now - _phone_send_history[rate_limited_phones[0]])) / 60) + 1
        return AlertResponse(
            success=False,
            message=f"Rate limit: {', '.join(rate_limited_phones)} received an alert recently. Please wait ~{mins_remaining} min before sending again.",
            sms_count=0,
        )

    basin = _get_basin_config(alert_req.basin_id)

    # 2. Reserve dedup slot for basin
    async with _get_alert_lock(alert_req.basin_id):
        stmt = select(AlertORM).where(
            AlertORM.basin_id == alert_req.basin_id,
            # HIGH/EXTREME = a completed send; PENDING = one currently in flight.
            AlertORM.risk_level.in_(["HIGH", "EXTREME", "PENDING"]),
        ).order_by(AlertORM.id.desc()).limit(1)

        recent_alert = (await session.scalars(stmt)).first()
        if recent_alert:
            if recent_alert.risk_level == "PENDING":
                return AlertResponse(
                    success=True,
                    message="Alert skipped: a send for this basin is already in progress.",
                    sms_count=0,
                )
            time_since = datetime.now(recent_alert.sent_at.tzinfo) - recent_alert.sent_at
            if time_since.total_seconds() < 12 * 3600:
                return AlertResponse(
                    success=True,
                    message="Alert skipped: An alert was already sent for this basin within the last 12 hours.",
                    sms_count=0
                )

        # Record phone timestamps
        for phone in valid_phones:
            _phone_send_history[phone] = now

        # Reserve the dedup slot synchronously, before queuing the background
        # task, so a concurrent request sees it immediately (see PENDING check above).
        pending = AlertORM(
            basin_id=alert_req.basin_id,
            risk_level="PENDING",
            role=alert_req.role.value,
            language=alert_req.language.value,
            recipients_count=len(alert_req.phone_numbers),
            advisory_text="",
        )
        session.add(pending)
        await session.commit()
        await session.refresh(pending)

    background_tasks.add_task(
        _process_and_send_alert,
        request=alert_req,
        basin=basin,
        alert_row_id=pending.id,
    )

    return AlertResponse(
        success=True,
        message="Alert processing queued successfully.",
        sms_count=len(alert_req.phone_numbers)
    )

async def _process_and_send_alert(request: AlertRequest, basin, alert_row_id: int):
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

        # Deliver via Twilio (or simulate if Twilio isn't configured)
        await send_sms_alert(sms_text, request.phone_numbers)

        # Resolve the PENDING reservation into the completed alert record.
        async with SessionLocal() as session:
            row = await session.get(AlertORM, alert_row_id)
            if row is not None:
                row.risk_level = risk.risk_level.value
                row.advisory_text = sms_text
                await session.commit()

    except Exception as e:
        logger.error(f"Failed to process background alert for {basin.id}: {e}")
        # Drop the PENDING reservation so a failed send doesn't permanently
        # block future alerts for this basin.
        async with SessionLocal() as session:
            row = await session.get(AlertORM, alert_row_id)
            if row is not None and row.risk_level == "PENDING":
                await session.delete(row)
                await session.commit()


@router.get("/alerts/history", response_model=list[AlertRecord])
async def get_alert_history(
    basin_id: str = Query(None, description="Filter by basin ID"),
    limit: int = Query(50, description="Max number of records"),
    session: AsyncSession = Depends(get_session),
):
    """Get the history of sent alerts (most recent last)."""
    from app.models.schemas import UserRole, Language

    stmt = select(AlertORM).where(AlertORM.risk_level.in_(_TERMINAL_RISK_LEVELS))
    if basin_id:
        stmt = stmt.where(AlertORM.basin_id == basin_id)
    stmt = stmt.order_by(AlertORM.id.desc()).limit(limit)

    rows = list(reversed((await session.scalars(stmt)).all()))
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
@limiter.limit("5/minute")
async def submit_report(
    request: Request,
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
@limiter.limit("5/minute")
async def submit_report_with_photo(
    request: Request,
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
    try:
        status_enum = ReportStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {[s.value for s in ReportStatus]}",
        )

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
@limiter.limit("10/minute")
async def edit_report(
    request: Request,
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
@limiter.limit("10/minute")
async def delete_report(
    request: Request,
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
@limiter.limit("10/minute")
async def delete_report_advice(
    request: Request,
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
@limiter.limit("10/minute")
async def add_report_advice(
    request: Request,
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
