"""
Open-Meteo Flood API client — fetches GloFAS river discharge forecasts.
No API key required. Data source: Copernicus GloFAS v4 at ~5 km resolution.
"""

import httpx
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.config import settings
from app.models.schemas import DailyDischarge, DischargeTimeSeries

logger = logging.getLogger(__name__)

# Reusable async HTTP client
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create the HTTP client singleton."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def fetch_river_discharge(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    past_days: int = 30,
) -> list[DailyDischarge]:
    """
    Fetch river discharge data from Open-Meteo Flood API.

    Args:
        latitude: Gauge point latitude
        longitude: Gauge point longitude
        forecast_days: Number of forecast days (1-210)
        past_days: Number of past days to include (0-92)

    Returns:
        List of DailyDischarge records
    """
    client = await get_client()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "river_discharge,river_discharge_mean,river_discharge_max,river_discharge_min,river_discharge_median",
        "forecast_days": forecast_days,
        "past_days": past_days,
        "timeformat": "iso8601",
    }

    try:
        response = await client.get(settings.flood_api_base, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch flood data: {e}")
        raise

    daily = data.get("daily", {})
    times = daily.get("time", [])

    results = []
    for i, t in enumerate(times):
        results.append(DailyDischarge(
            date=date.fromisoformat(t),
            discharge_mean=_safe_get(daily, "river_discharge_mean", i),
            discharge_max=_safe_get(daily, "river_discharge_max", i),
            discharge_min=_safe_get(daily, "river_discharge_min", i),
            discharge_median=_safe_get(daily, "river_discharge_median", i),
        ))

    logger.info(
        f"Fetched {len(results)} discharge records for ({latitude}, {longitude})"
    )
    return results


async def fetch_historical_discharge(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> list[DailyDischarge]:
    """
    Fetch historical discharge data using date range.
    Used for hindcast demo (e.g., Beledweyne Nov 2023).

    Args:
        latitude: Gauge point latitude
        longitude: Gauge point longitude
        start_date: ISO date string (YYYY-MM-DD)
        end_date: ISO date string (YYYY-MM-DD)

    Returns:
        List of DailyDischarge records
    """
    client = await get_client()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "river_discharge,river_discharge_mean,river_discharge_max,river_discharge_min,river_discharge_median",
        "start_date": start_date,
        "end_date": end_date,
        "timeformat": "iso8601",
    }

    try:
        response = await client.get(settings.flood_api_base, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch historical flood data: {e}")
        raise

    daily = data.get("daily", {})
    times = daily.get("time", [])

    results = []
    for i, t in enumerate(times):
        results.append(DailyDischarge(
            date=date.fromisoformat(t),
            discharge_mean=_safe_get(daily, "river_discharge_mean", i),
            discharge_max=_safe_get(daily, "river_discharge_max", i),
            discharge_min=_safe_get(daily, "river_discharge_min", i),
            discharge_median=_safe_get(daily, "river_discharge_median", i),
        ))

    logger.info(
        f"Fetched {len(results)} historical records for ({latitude}, {longitude}) "
        f"from {start_date} to {end_date}"
    )
    return results


def _safe_get(daily: dict, key: str, index: int) -> Optional[float]:
    """Safely get a value from the daily data arrays."""
    values = daily.get(key, [])
    if index < len(values):
        return values[index]
    return None
