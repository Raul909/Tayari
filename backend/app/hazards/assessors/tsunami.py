"""
Tsunami assessment.

Three conditions have to hold at once, and all three are measurable: the
location must be near a coast, it must be low enough for water to reach it, and
there must be a seismic source capable of generating a wave. Fail any one and
no card is produced — a hill town 200 m above the sea is coastal and is not at
risk of inundation, and telling it otherwise wastes the attention that a real
warning needs.

Tayari is explicitly not a tsunami warning centre. When a wave is actually
inbound, the authority is the regional warning centre and the trigger is a
siren or a cell broadcast, not a web page. What this card does is the part that
has to happen *before* that: make sure a coastal household knows in advance
that it is in an inundation zone, and knows which way is uphill.
"""

from datetime import datetime, timezone
from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.TSUNAMI

# A tsunamigenic earthquake is large, shallow and under water. Below roughly
# M6.5 an ocean-wide wave is very unlikely; below ~70 km depth the rupture no
# longer displaces the seafloor enough to matter.
TSUNAMIGENIC_MIN_MAGNITUDE = 6.5
TSUNAMIGENIC_MAX_DEPTH_KM = 70.0
ACTIVE_WINDOW_HOURS = 12.0

MAX_INUNDATION_ELEVATION_M = 40.0
MAX_COASTAL_DISTANCE_KM = 25.0

READINESS_CAP = 0.30


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    terrain = ctx.terrain
    coast_km = terrain.distance_to_coast_km
    elevation = terrain.elevation_m

    # No ocean found within the 200 km probe radius — this is inland.
    if coast_km is None:
        return None
    if elevation is not None and elevation > MAX_INUNDATION_ELEVATION_M:
        return None
    if coast_km > MAX_COASTAL_DISTANCE_KM:
        return None

    coastal_factor = 1.0 - ramp(coast_km, 0.0, MAX_COASTAL_DISTANCE_KM)
    elevation_factor = (
        1.0 - ramp(elevation, 10.0, MAX_INUNDATION_ELEVATION_M) if elevation is not None else 0.6
    )

    # Without an earthquake source there is nothing to generate a wave, so
    # seismicity gates the whole hazard — the Baltic coast is flat and low and is
    # not a tsunami risk.
    #
    # The source has to be looked for at ocean-basin scale, not locally. Chennai
    # sits on an essentially aseismic coast and lost hundreds of people in 2004
    # to a rupture 1,500 km away; scoring it on local seismicity screened it out
    # entirely. `distant_great_quakes` counts M7.5+ within 3,000 km, which is the
    # question that actually matters for a coastline.
    history = ctx.seismic
    if history is None:
        return None
    source_factor = clamp01(
        0.65 * ramp(float(history.distant_great_quakes), 1.0, 40.0)
        + 0.35 * ramp(history.max_magnitude or 0.0, 6.5, 8.5)
    )

    susceptibility = clamp01(coastal_factor * elevation_factor * source_factor)
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Live: has something just ruptured offshore? ──────────────────────────
    now = datetime.now(timezone.utc)
    trigger = None
    trigger_score = 0.0
    for quake in ctx.recent_quakes or []:
        if (quake.magnitude or 0) < TSUNAMIGENIC_MIN_MAGNITUDE:
            continue
        if quake.depth_km is not None and quake.depth_km > TSUNAMIGENIC_MAX_DEPTH_KM:
            continue
        age_hours = (
            (now - quake.occurred_at).total_seconds() / 3600.0 if quake.occurred_at else 999.0
        )
        if age_hours > ACTIVE_WINDOW_HOURS:
            continue
        magnitude_score = ramp(quake.magnitude, TSUNAMIGENIC_MIN_MAGNITUDE, 8.5)
        recency = clamp01(1.0 - age_hours / ACTIVE_WINDOW_HOURS)
        candidate = clamp01(0.55 + 0.45 * magnitude_score) * (0.5 + 0.5 * recency)
        if candidate > trigger_score:
            trigger_score, trigger = candidate, quake

    score = max(susceptibility * READINESS_CAP, trigger_score * susceptibility + trigger_score * 0.3)

    if trigger is not None:
        headline = (
            f"M{trigger.magnitude:.1f} offshore earthquake {trigger.distance_km:.0f} km away — "
            f"check official tsunami warnings now"
        )
        summary = (
            f"{trigger.title}. An earthquake of this size and depth near the coast can "
            f"generate a tsunami. Do not wait for a wave to be visible and do not wait for "
            f"this page: if the ground shook hard enough that standing was difficult, move "
            f"inland and uphill immediately, then follow your national warning centre."
        )
    else:
        headline = "In a coastal zone that a tsunami could reach"
        summary = (
            "No tsunami threat is active. This location is flagged because it sits low and "
            "close to a coast in a seismically capable region, which means the response has "
            "to be decided in advance — after the shaking starts there are only minutes. "
            "Know your route to high ground before you need it."
        )

    indicators = [
        indicator("Distance to coast", f"{coast_km:.0f} km" if coast_km >= 1 else "<1 km"),
        indicator(
            "Ground elevation",
            f"{elevation:.0f} m" if elevation is not None else "unknown",
            detail="Water can reach well beyond the shoreline where land is this low"
            if elevation is not None and elevation <= 15
            else None,
        ),
    ]
    indicators.append(
        indicator(
            "Tsunami-capable earthquakes nearby",
            f"{history.distant_great_quakes}",
            detail=f"M7.5+ within {history.distant_radius_km:,} km since 1900",
        )
    )
    if history.max_magnitude:
        indicators.append(
            indicator(
                "Largest earthquake within 300 km",
                f"M{history.max_magnitude:.1f}",
                detail=f"{history.max_event_year}" if history.max_event_year else None,
            )
        )

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        events=[trigger] if trigger else [],
        confidence=0.55,
        lead_time="Minutes to hours after a rupture — prepare in advance",
        note=(
            "Tayari is not a tsunami warning centre. For a live threat, follow your national "
            "warning authority; this card exists to make sure you know in advance that you "
            "are in an exposed zone."
        ),
    )
