"""
The shared evidence bundle every assessor reads from.

Nine hazards do not mean nine times the network traffic. Most of them are
different questions asked of the same few observations — the rainfall that
drives a flood also drives a landslide and, by its absence, a drought — so the
context is gathered once, concurrently, and handed to every assessor.

The rule throughout is that a missing feed is a `None` field, never an
exception. One dead upstream should cost the user one hazard card, not the
whole page.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.hazards import feeds, volcano_catalog
from app.hazards.cache import TTLCache, geo_key
from app.hazards.geo import probe_terrain
from app.models.hazards import HazardEvent, TerrainProfile
from app.models.schemas import DailyDischarge

logger = logging.getLogger(__name__)

_terrain_cache = TTLCache(ttl_seconds=30 * 24 * 3600, max_entries=512)


@dataclass
class HazardContext:
    """Everything known about one location at one moment."""

    latitude: float
    longitude: float

    terrain: TerrainProfile = field(default_factory=TerrainProfile)
    weather: Optional[feeds.WeatherBundle] = None
    climate: Optional[feeds.ClimateBaseline] = None
    discharge: Optional[list[DailyDischarge]] = None
    discharge_climatology: Optional[feeds.DischargeClimatology] = None
    seismic: Optional[feeds.SeismicHistory] = None
    recent_quakes: Optional[list[HazardEvent]] = None
    volcanoes: list[volcano_catalog.NearbyVolcano] = field(default_factory=list)
    volcano_activity: list[feeds.VolcanoActivity] = field(default_factory=list)

    failed_feeds: list[str] = field(default_factory=list)

    @property
    def partial(self) -> bool:
        return bool(self.failed_feeds)


async def _terrain(latitude: float, longitude: float) -> TerrainProfile:
    """Terrain, cached for a month — bedrock is not a time series."""
    key = geo_key(latitude, longitude, precision=2)
    cached = _terrain_cache.get(key)
    if cached is not None:
        return cached
    client = await feeds.get_client()
    profile = await probe_terrain(client, latitude, longitude)
    # Only cache a probe that actually resolved something; caching an empty
    # profile for a month would make one bad minute permanent.
    if profile.elevation_m is not None:
        _terrain_cache.set(key, profile)
    return profile


async def _discharge(latitude: float, longitude: float) -> Optional[list[DailyDischarge]]:
    """
    Global GloFAS discharge for an arbitrary point.

    Unlike the eight curated basins, an arbitrary coordinate has no calibrated
    thresholds, so the flood assessor derives them from the point's own recent
    record. We therefore ask for the full 92 days of history Open-Meteo allows
    rather than the 30 the basin pipeline uses.
    """
    from app.services.flood_data import fetch_river_discharge

    try:
        return await fetch_river_discharge(
            latitude, longitude, forecast_days=7, past_days=92
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Discharge feed failed at ({latitude}, {longitude}): {e}")
        return None


async def build_context(latitude: float, longitude: float) -> HazardContext:
    """
    Gather every feed for a location in parallel.

    Seven upstream calls, one round-trip's worth of latency. `return_exceptions`
    keeps a single raising task from cancelling its siblings — the whole point of
    doing this concurrently is lost if one slow API can void the other five.
    """
    ctx = HazardContext(latitude=latitude, longitude=longitude)

    results = await asyncio.gather(
        _terrain(latitude, longitude),
        feeds.fetch_weather_bundle(latitude, longitude),
        feeds.fetch_climate_baseline(latitude, longitude),
        _discharge(latitude, longitude),
        feeds.fetch_discharge_climatology(latitude, longitude),
        feeds.fetch_seismic_history(latitude, longitude),
        feeds.fetch_recent_quakes(latitude, longitude),
        feeds.fetch_volcano_activity(),
        return_exceptions=True,
    )
    terrain, weather, climate, discharge, discharge_clim, seismic, quakes, activity = results

    def _unwrap(value, label: str, default=None):
        if isinstance(value, BaseException):
            logger.warning(f"Feed '{label}' raised: {value}")
            ctx.failed_feeds.append(label)
            return default
        if value is None:
            ctx.failed_feeds.append(label)
            return default
        return value

    ctx.terrain = _unwrap(terrain, "terrain", TerrainProfile()) or TerrainProfile()
    ctx.weather = _unwrap(weather, "weather")
    ctx.climate = _unwrap(climate, "climate")
    ctx.discharge = _unwrap(discharge, "discharge")
    ctx.discharge_climatology = _unwrap(discharge_clim, "discharge_climatology")
    ctx.seismic = _unwrap(seismic, "seismic")
    ctx.recent_quakes = _unwrap(quakes, "earthquakes")
    ctx.volcano_activity = _unwrap(activity, "volcano_activity", []) or []

    # Local only — the catalog is in memory, so this cannot fail on the network.
    ctx.volcanoes = volcano_catalog.nearby_volcanoes(latitude, longitude, radius_km=150.0)

    if ctx.failed_feeds:
        logger.info(
            f"Context for ({latitude}, {longitude}) is partial; failed: {ctx.failed_feeds}"
        )
    return ctx
