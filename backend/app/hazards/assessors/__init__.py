"""
The nine hazard assessors.

Each module exposes `hazard: HazardType` and `assess(ctx) -> HazardRisk | None`,
and nothing else. They are pure functions over the context: no HTTP, no shared
mutable state, no knowledge of each other. That is what lets the engine run them
all and lose only the ones whose evidence is missing.
"""

from types import ModuleType

from app.hazards.assessors import (
    cyclone,
    drought,
    earthquake,
    flood,
    heat,
    landslide,
    tsunami,
    volcano,
    wildfire,
)

# Order is the tie-break when two hazards score identically, roughly by how
# little time the reader would have to act.
ASSESSORS: tuple[ModuleType, ...] = (
    earthquake,
    tsunami,
    volcano,
    flood,
    cyclone,
    landslide,
    wildfire,
    heat,
    drought,
)

__all__ = ["ASSESSORS"]
