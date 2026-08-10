"""
The Smithsonian Holocene volcano catalog, loaded once and queried by proximity.

1,214 volcanoes is small enough that a linear scan with a haversine per entry
costs well under a millisecond, so there is no spatial index here and no reason
for one. Regenerate the underlying file with
`backend/scripts/build_volcano_catalog.py`.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.hazards.geo import haversine_km

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent.parent / "data" / "volcanoes.json"


@dataclass
class Volcano:
    number: int
    name: str
    country: Optional[str]
    region: Optional[str]
    type: Optional[str]
    last_eruption_year: Optional[int]
    elevation_m: Optional[int]
    latitude: float
    longitude: float

    @property
    def url(self) -> str:
        return f"https://volcano.si.edu/volcano.cfm?vn={self.number}"

    @property
    def erupted_in_last_century(self) -> bool:
        return self.last_eruption_year is not None and self.last_eruption_year >= 1925


@dataclass
class NearbyVolcano:
    volcano: Volcano
    distance_km: float


_volcanoes: Optional[list[Volcano]] = None
_source_note: str = ""


def _load() -> list[Volcano]:
    global _volcanoes, _source_note
    if _volcanoes is not None:
        return _volcanoes

    try:
        with _CATALOG_PATH.open() as fh:
            payload = json.load(fh)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Volcano catalog unavailable at {_CATALOG_PATH}: {e}")
        _volcanoes = []
        return _volcanoes

    _source_note = f"{payload.get('source', 'Smithsonian GVP')} (retrieved {payload.get('retrieved', 'unknown')})"
    rows = payload.get("volcanoes") or []
    parsed: list[Volcano] = []
    for row in rows:
        try:
            num, name, country, region, vtype, last_eruption, elevation, lat, lon = row
        except (TypeError, ValueError):
            continue
        parsed.append(
            Volcano(
                number=num,
                name=name,
                country=country,
                region=region,
                type=vtype,
                last_eruption_year=last_eruption,
                elevation_m=elevation,
                latitude=lat,
                longitude=lon,
            )
        )
    _volcanoes = parsed
    logger.info(f"Loaded {len(parsed)} Holocene volcanoes from the Smithsonian catalog")
    return _volcanoes


def source_note() -> str:
    _load()
    return _source_note


def nearby_volcanoes(
    latitude: float, longitude: float, radius_km: float = 150.0, limit: int = 5
) -> list[NearbyVolcano]:
    """Volcanoes within `radius_km`, nearest first."""
    found = [
        NearbyVolcano(volcano=v, distance_km=round(d, 1))
        for v in _load()
        if (d := haversine_km(latitude, longitude, v.latitude, v.longitude)) <= radius_km
    ]
    found.sort(key=lambda nv: nv.distance_km)
    return found[:limit]


def by_number(volcano_number: int) -> Optional[Volcano]:
    """Look up a volcano by its Smithsonian number — the exact join key."""
    return _by_number().get(volcano_number)


_number_index: Optional[dict[int, Volcano]] = None


def _by_number() -> dict[int, Volcano]:
    global _number_index
    if _number_index is None:
        _number_index = {v.number: v for v in _load()}
    return _number_index


def match_volcano(latitude: float, longitude: float, tolerance_km: float = 25.0) -> Optional[Volcano]:
    """
    Find the catalog entry for a coordinate reported by the weekly activity feed.

    Matching on position rather than name is deliberate: the weekly report writes
    "Etna" where the catalog may hold a different transliteration, and a missed
    match on an erupting volcano is a silent failure of exactly the kind this
    system exists to prevent.
    """
    best: Optional[Volcano] = None
    best_distance = tolerance_km
    for v in _load():
        d = haversine_km(latitude, longitude, v.latitude, v.longitude)
        if d <= best_distance:
            best, best_distance = v, d
    return best
