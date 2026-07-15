"""
API routers for basin listing and forecast endpoints.

These are the core endpoints that the frontend consumes.
"""

import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    BasinSummary, BasinConfig, FullForecast, DischargeTimeSeries,
    FloodRiskScore, RiskLevel, UserRole, Language, DailyDischarge
)
from app.services.flood_data import fetch_river_discharge, fetch_historical_discharge
from app.services.weather_data import fetch_upstream_rainfall
from app.services.flood_model import compute_flood_risk
from app.services.impact import compute_impact
from app.services.advisory import generate_advisory

logger = logging.getLogger(__name__)
router = APIRouter()

# Load basins config
_basins_path = Path(__file__).parent.parent / "data" / "basins.json"
_basins: list[BasinConfig] = []


def _load_basins() -> list[BasinConfig]:
    """Load basin configurations from JSON file."""
    global _basins
    if not _basins:
        with open(_basins_path) as f:
            data = json.load(f)
        for b in data["basins"]:
            _basins.append(BasinConfig(**b))
    return _basins


def _get_basin(basin_id: str) -> BasinConfig:
    """Get a specific basin by ID."""
    basins = _load_basins()
    for b in basins:
        if b.id == basin_id:
            return b
    raise HTTPException(status_code=404, detail=f"Basin '{basin_id}' not found")


# ─── Basin Endpoints ──────────────────────────────────────────────────────────

async def _summarize_basin(basin: BasinConfig) -> BasinSummary:
    """Build a summary for a single basin. Fetches its two data feeds in parallel."""
    try:
        # Discharge + rainfall are independent — fetch them concurrently.
        discharge, rainfall = await asyncio.gather(
            fetch_river_discharge(
                basin.gauge_point.latitude,
                basin.gauge_point.longitude,
                forecast_days=3,
                past_days=3,
            ),
            fetch_upstream_rainfall(
                basin.upstream_point.latitude,
                basin.upstream_point.longitude,
                forecast_days=3,
                past_days=3,
            ),
        )

        risk = compute_flood_risk(basin, discharge, rainfall)

        # Current discharge = most recent available past data point
        current_discharge = None
        for d in reversed(discharge):
            if d.discharge_mean is not None:
                current_discharge = d.discharge_mean
                break

        return BasinSummary(
            id=basin.id,
            name=basin.name,
            river=basin.river,
            country=basin.country,
            latitude=basin.gauge_point.latitude,
            longitude=basin.gauge_point.longitude,
            current_risk=risk.risk_level,
            current_discharge=current_discharge,
            flood_probability=risk.probability,
            last_updated=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Error fetching data for basin {basin.id}: {e}")
        return BasinSummary(
            id=basin.id,
            name=basin.name,
            river=basin.river,
            country=basin.country,
            latitude=basin.gauge_point.latitude,
            longitude=basin.gauge_point.longitude,
        )


@router.get("/basins", response_model=list[BasinSummary])
async def list_basins():
    """
    List all monitored basins with their current risk levels.

    Returns quick-loading summary data. For full forecasts,
    use GET /forecasts/{basin_id}.

    All basins are summarized concurrently so total latency is roughly one
    upstream round-trip rather than the sum across every basin.
    """
    basins = _load_basins()
    return await asyncio.gather(*(_summarize_basin(b) for b in basins))


# ─── Forecast Endpoints ──────────────────────────────────────────────────────

@router.get("/forecasts/{basin_id}", response_model=FullForecast)
async def get_forecast(
    basin_id: str,
    role: UserRole = Query(UserRole.GENERAL, description="Target audience role"),
    language: Language = Query(Language.ENGLISH, description="Advisory language"),
):
    """
    Get the full forecast for a basin, including:
    - Discharge time series (past 30 days + 7-day forecast)
    - Flood risk score with 7-day probabilities
    - Impact assessment (population + infrastructure at risk)
    - AI-generated multilingual advisory
    """
    basin = _get_basin(basin_id)

    # Fetch data from both APIs concurrently
    discharge_data, rainfall_data = await asyncio.gather(
        fetch_river_discharge(
            basin.gauge_point.latitude,
            basin.gauge_point.longitude,
            forecast_days=7,
            past_days=30,
        ),
        fetch_upstream_rainfall(
            basin.upstream_point.latitude,
            basin.upstream_point.longitude,
            forecast_days=7,
            past_days=14,
        ),
    )

    # Compute flood risk
    risk = compute_flood_risk(basin, discharge_data, rainfall_data)

    # Compute impact
    impact = compute_impact(basin_id, risk.risk_level)

    # Generate advisory
    advisory = await generate_advisory(
        risk=risk,
        impact=impact,
        basin_name=basin.name,
        river_name=basin.river,
        country=basin.country,
        role=role,
        language=language,
    )

    # Get current discharge for summary
    from datetime import date
    current_discharge = None
    today = date.today()
    for d in discharge_data:
        if d.date == today and d.discharge_mean is not None:
            current_discharge = d.discharge_mean
            break
    if current_discharge is None:
        for d in reversed(discharge_data):
            if d.discharge_mean is not None:
                current_discharge = d.discharge_mean
                break

    return FullForecast(
        basin=BasinSummary(
            id=basin.id,
            name=basin.name,
            river=basin.river,
            country=basin.country,
            latitude=basin.gauge_point.latitude,
            longitude=basin.gauge_point.longitude,
            current_risk=risk.risk_level,
            current_discharge=current_discharge,
            flood_probability=risk.probability,
            last_updated=datetime.utcnow(),
        ),
        discharge=DischargeTimeSeries(
            basin_id=basin_id,
            data=discharge_data,
            flood_threshold=basin.flood_threshold_m3s,
            warning_threshold=basin.warning_threshold_m3s,
            historical_median=basin.historical_median_m3s,
        ),
        risk=risk,
        impact=impact,
        advisory=advisory,
    )


@router.get("/forecasts/{basin_id}/history")
async def get_forecast_history(
    basin_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Get historical discharge data for a basin.
    Used for the hindcast demo (e.g., Beledweyne Nov 2023).
    """
    basin = _get_basin(basin_id)

    discharge = await fetch_historical_discharge(
        basin.gauge_point.latitude,
        basin.gauge_point.longitude,
        start_date=start_date,
        end_date=end_date,
    )

    return DischargeTimeSeries(
        basin_id=basin_id,
        data=discharge,
        flood_threshold=basin.flood_threshold_m3s,
        warning_threshold=basin.warning_threshold_m3s,
        historical_median=basin.historical_median_m3s,
    )


# ─── Advisory Endpoint ───────────────────────────────────────────────────────

@router.get("/advisory/{basin_id}", response_model=dict)
async def get_advisory(
    basin_id: str,
    role: UserRole = Query(UserRole.GENERAL),
    language: Language = Query(Language.ENGLISH),
):
    """
    Get just the AI advisory for a basin, in a specific role and language.
    Useful for the SMS preview and language switcher.
    """
    basin = _get_basin(basin_id)

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
    impact = compute_impact(basin_id, risk.risk_level)

    advisory = await generate_advisory(
        risk=risk,
        impact=impact,
        basin_name=basin.name,
        river_name=basin.river,
        country=basin.country,
        role=role,
        language=language,
    )

    return {
        "advisory": advisory.model_dump(),
        "sms_text": f"{advisory.title}\n\n{advisory.body}\n\n" +
                    "\n".join(f"• {a}" for a in advisory.actions),
    }
