"""
Open-Meteo Weather API client — fetches upstream rainfall forecasts.
No API key required.
"""

import httpx
import logging
from datetime import date
from typing import Optional

from app.config import settings
from app.services.flood_data import get_client

logger = logging.getLogger(__name__)


class RainfallData:
    """Rainfall data for a single day."""
    def __init__(self, day: date, precipitation_sum: float = 0.0, rain_sum: float = 0.0):
        self.date = day
        self.precipitation_sum = precipitation_sum
        self.rain_sum = rain_sum


async def fetch_upstream_rainfall(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    past_days: int = 14,
) -> list[RainfallData]:
    """
    Fetch upstream rainfall data from Open-Meteo Weather API.

    Args:
        latitude: Upstream catchment center latitude
        longitude: Upstream catchment center longitude
        forecast_days: Number of forecast days
        past_days: Number of past days for trend analysis

    Returns:
        List of RainfallData records
    """
    client = await get_client()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum,rain_sum",
        "forecast_days": forecast_days,
        "past_days": past_days,
        "timeformat": "iso8601",
    }

    try:
        response = await client.get(settings.weather_api_base, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch weather data: {e}")
        raise

    daily = data.get("daily", {})
    times = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])
    rain = daily.get("rain_sum", [])

    results = []
    for i, t in enumerate(times):
        results.append(RainfallData(
            day=date.fromisoformat(t),
            precipitation_sum=precip[i] if i < len(precip) and precip[i] is not None else 0.0,
            rain_sum=rain[i] if i < len(rain) and rain[i] is not None else 0.0,
        ))

    logger.info(
        f"Fetched {len(results)} rainfall records for ({latitude}, {longitude})"
    )
    return results
