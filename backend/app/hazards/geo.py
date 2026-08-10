"""
Geometry helpers, and the terrain probe several hazards depend on.

The interesting piece here is `probe_terrain`. Tsunami, landslide and storm
surge all need to know something about the shape of the ground — is there an
ocean nearby, is it steep — and the obvious ways to get that (a coastline
shapefile, a global slope raster) mean shipping hundreds of megabytes of
geodata, which a free-tier container cannot hold.

Instead we sample a digital elevation model at ~40 points around the location in
a single request. A sample at or below sea level is ocean, so the nearest such
sample gives distance to coast; the spread of the land samples gives local
relief, which is a serviceable proxy for slope. One HTTP call, no bundled
geodata, and the answer is derived from the same DEM a shapefile would have been
built from.
"""

import logging
import math
from typing import Optional

import httpx

from app.config import settings
from app.models.hazards import TerrainProfile

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088

# Proxied for the same reason as the other Open-Meteo feeds (see feeds.py).
ELEVATION_API = settings.elevation_api_base

# Rings sampled around the point, in km. The inner rings resolve steepness that
# matters for landslides; the outer ones are there to find an ocean. 200 km is
# where we stop calling a place "coastal" for tsunami purposes anyway.
PROBE_RADII_KM = (3.0, 8.0, 20.0, 50.0, 120.0, 200.0)
PROBE_BEARINGS = tuple(range(0, 360, 60))  # every 60° → 6 per ring


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """The point `distance_km` away from (lat, lon) along a compass bearing."""
    ang = distance_km / EARTH_RADIUS_KM
    brg = math.radians(bearing_deg)
    p1 = math.radians(lat)
    l1 = math.radians(lon)

    p2 = math.asin(math.sin(p1) * math.cos(ang) + math.cos(p1) * math.sin(ang) * math.cos(brg))
    l2 = l1 + math.atan2(
        math.sin(brg) * math.sin(ang) * math.cos(p1),
        math.cos(ang) - math.sin(p1) * math.sin(p2),
    )
    lat2 = math.degrees(p2)
    lon2 = (math.degrees(l2) + 540) % 360 - 180  # normalize to [-180, 180]
    return round(lat2, 4), round(lon2, 4)


def _slope_deg(rise_m: float, run_km: float) -> float:
    if run_km <= 0:
        return 0.0
    return math.degrees(math.atan((rise_m / 1000.0) / run_km))


async def probe_terrain(
    client: httpx.AsyncClient, latitude: float, longitude: float
) -> TerrainProfile:
    """
    Sample the elevation model around a point and derive coastal distance,
    local relief and maximum slope.

    Never raises: terrain is an input to several hazards but the absence of it
    must degrade those hazards individually rather than fail the whole profile.
    """
    points: list[tuple[float, float, float]] = [(latitude, longitude, 0.0)]
    for radius in PROBE_RADII_KM:
        for bearing in PROBE_BEARINGS:
            plat, plon = destination_point(latitude, longitude, bearing, radius)
            points.append((plat, plon, radius))

    lats = ",".join(f"{p[0]}" for p in points)
    lons = ",".join(f"{p[1]}" for p in points)

    try:
        resp = await client.get(
            ELEVATION_API, params={"latitude": lats, "longitude": lons}, timeout=20.0
        )
        resp.raise_for_status()
        elevations = resp.json().get("elevation") or []
    except Exception as e:  # noqa: BLE001 — any failure degrades, never propagates
        logger.warning(f"Terrain probe failed at ({latitude}, {longitude}): {e}")
        return TerrainProfile()

    if len(elevations) != len(points):
        logger.warning(
            f"Terrain probe returned {len(elevations)} elevations for {len(points)} points"
        )
        if not elevations:
            return TerrainProfile()

    centre_elev: Optional[float] = elevations[0] if elevations else None

    # Sea level is the ocean test. Open-Meteo's DEM returns 0.0 over water; a
    # genuine land pixel at exactly 0 m is rare enough, and being slightly
    # over-inclusive about "coastal" is the safe direction to err for tsunami.
    coast_km: Optional[float] = None
    land_elevations: list[float] = []
    max_slope = 0.0

    for (plat, plon, radius), elev in zip(points[1:], elevations[1:]):
        if elev is None:
            continue
        if elev <= 0.0:
            if coast_km is None or radius < coast_km:
                coast_km = radius
        else:
            land_elevations.append(elev)
            if centre_elev is not None and radius <= 20.0:
                max_slope = max(max_slope, _slope_deg(abs(elev - centre_elev), radius))

    if centre_elev is not None and centre_elev > 0:
        land_elevations.append(centre_elev)

    # Relief is measured over the inner rings only (≤ 20 km). Sampling out to
    # 200 km would report a coastal plain 150 km from a mountain range as steep.
    near = [
        e
        for (plat, plon, radius), e in zip(points[1:], elevations[1:])
        if e is not None and e > 0 and radius <= 20.0
    ]
    if centre_elev is not None and centre_elev > 0:
        near.append(centre_elev)
    relief = (max(near) - min(near)) if len(near) >= 2 else None

    return TerrainProfile(
        elevation_m=centre_elev,
        distance_to_coast_km=coast_km,
        local_relief_m=round(relief, 1) if relief is not None else None,
        max_slope_deg=round(max_slope, 2) if max_slope else None,
        # Sea level *and* proximity both matter: a clifftop town 40 m up is on
        # the coast but is not in a tsunami inundation zone.
        is_coastal=coast_km is not None and coast_km <= 50.0,
    )
