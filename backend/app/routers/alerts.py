"""
Alert and community report API routers.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from typing import Optional

from app.models.schemas import (
    AlertRequest, AlertResponse, AlertRecord,
    ReportSubmission, CommunityReport, ReportStatus,
    UserRole, Language,
)
from app.services.alerts import send_sms_alert
from app.services.advisory import generate_advisory
from app.services.flood_data import fetch_river_discharge
from app.services.weather_data import fetch_upstream_rainfall
from app.services.flood_model import compute_flood_risk
from app.services.impact import compute_impact

import json
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory stores (use database in production)
_alert_history: list[AlertRecord] = []
_community_reports: list[CommunityReport] = []
_report_id_counter = 0
_alert_id_counter = 0

# Upload directory for report photos
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "reports"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load basin config helper
_basins_path = Path(__file__).parent.parent / "data" / "basins.json"

def _get_basin_config(basin_id: str):
    from app.models.schemas import BasinConfig
    with open(_basins_path) as f:
        data = json.load(f)
    for b in data["basins"]:
        if b["id"] == basin_id:
            return BasinConfig(**b)
    raise HTTPException(status_code=404, detail=f"Basin '{basin_id}' not found")


# ─── Alert Endpoints ─────────────────────────────────────────────────────────

@router.post("/alerts/send", response_model=AlertResponse)
async def send_alert(request: AlertRequest):
    """
    Send an SMS alert for a basin.

    Generates an AI advisory in the specified role and language,
    then sends it via Africa's Talking SMS.
    """
    global _alert_id_counter

    basin = _get_basin_config(request.basin_id)

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
    result = await send_sms_alert(sms_text, request.phone_numbers)

    # Record alert
    _alert_id_counter += 1
    _alert_history.append(AlertRecord(
        id=_alert_id_counter,
        basin_id=request.basin_id,
        risk_level=risk.risk_level,
        role=request.role,
        language=request.language,
        recipients_count=len(request.phone_numbers),
        sent_at=datetime.utcnow(),
        advisory_text=sms_text,
    ))

    return result


@router.get("/alerts/history", response_model=list[AlertRecord])
async def get_alert_history(
    basin_id: str = Query(None, description="Filter by basin ID"),
    limit: int = Query(50, description="Max number of records"),
):
    """Get the history of sent alerts."""
    records = _alert_history
    if basin_id:
        records = [r for r in records if r.basin_id == basin_id]
    return records[-limit:]


# ─── Community Report Endpoints ──────────────────────────────────────────────

@router.post("/reports", response_model=CommunityReport)
async def submit_report(report: ReportSubmission):
    """
    Submit a community report from the field.

    Community members can report ground conditions via the app or SMS reply.
    Reports appear as pins on the map and serve as ground truth
    for model validation.
    """
    global _report_id_counter
    _report_id_counter += 1

    community_report = CommunityReport(
        id=_report_id_counter,
        basin_id=report.basin_id,
        status=report.status,
        latitude=report.latitude,
        longitude=report.longitude,
        description=report.description,
        reporter_name=report.reporter_name,
        photo_url=report.photo_url,
        submitted_at=datetime.utcnow(),
    )

    _community_reports.append(community_report)
    logger.info(f"Community report #{_report_id_counter} submitted for {report.basin_id}")

    return community_report


@router.post("/reports/upload", response_model=CommunityReport)
async def submit_report_with_photo(
    basin_id: str = Form(...),
    status: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    """
    Submit a community report with an optional photo upload.

    Accepts multipart/form-data so the mobile app can send the compressed
    JPEG binary alongside the report fields in a single request.
    """
    global _report_id_counter
    _report_id_counter += 1

    photo_url = None
    if photo and photo.filename:
        # Generate a unique filename to avoid collisions
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{_report_id_counter}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = UPLOAD_DIR / filename

        contents = await photo.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        photo_url = f"/uploads/reports/{filename}"
        logger.info(f"Saved report photo: {filepath} ({len(contents)} bytes)")

    # Map the raw status string to the enum value
    status_enum = ReportStatus(status)

    community_report = CommunityReport(
        id=_report_id_counter,
        basin_id=basin_id,
        status=status_enum,
        latitude=latitude,
        longitude=longitude,
        description=description,
        reporter_name=reporter_name,
        photo_url=photo_url,
        submitted_at=datetime.utcnow(),
    )

    _community_reports.append(community_report)
    logger.info(f"Community report #{_report_id_counter} (with photo) submitted for {basin_id}")

    return community_report


@router.get("/reports", response_model=list[CommunityReport])
async def get_reports(
    basin_id: str = Query(None, description="Filter by basin ID"),
    limit: int = Query(50, description="Max number of records"),
):
    """Get community reports, optionally filtered by basin."""
    reports = _community_reports
    if basin_id:
        reports = [r for r in reports if r.basin_id == basin_id]
    return reports[-limit:]
