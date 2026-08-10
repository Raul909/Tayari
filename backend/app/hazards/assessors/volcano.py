"""
Volcanic hazard assessment.

Of the three geophysical hazards this is the one where a warning is genuinely
possible. Unrest builds over days or weeks, observatories publish what they see,
and the Smithsonian and USGS summarise it worldwide every Thursday. So unlike
earthquakes, "is the volcano near me doing something right now?" has a real
answer, and it is the answer this card leads with.

Susceptibility is proximity weighted by how recently the volcano has erupted.
A Holocene volcano that last erupted 6,000 years ago and one that erupted last
year are both in the catalog and are not the same thing to live next to.
"""

from datetime import datetime, time, timezone
from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.hazards.volcano_catalog import NearbyVolcano
from app.models.hazards import HazardEvent, HazardRisk, HazardType

hazard = HazardType.VOLCANO

# Beyond this, proximity stops meaning much for anything except ashfall, which
# is real but is a different (and much less acute) problem.
MAX_RELEVANT_DISTANCE_KM = 100.0
READINESS_CAP = 0.28


def _eruption_recency(eruption) -> float:
    """How much a catalogued eruption should raise present concern, 0-1."""
    when = eruption.reference_date
    if when is None:
        return 0.4
    months = (datetime.now(timezone.utc).date() - when).days / 30.44
    if months <= 6:
        return 1.0
    if months <= 12:
        return 0.8
    if months <= 24:
        return 0.6
    return 0.45


def _recency_weight(last_eruption_year: Optional[int]) -> float:
    """
    How much a volcano's eruptive history should count toward present risk.

    The bands are coarse on purpose. The catalog's `Last_Eruption_Year` is a
    single number standing in for wildly varying evidence quality — an observed
    2022 eruption and a radiocarbon date with centuries of uncertainty are both
    just integers here — so anything finer would be false precision.
    """
    if last_eruption_year is None:
        return 0.25  # Holocene activity, undated
    if last_eruption_year >= 1975:
        return 1.0
    if last_eruption_year >= 1900:
        return 0.8
    if last_eruption_year >= 1500:
        return 0.55
    if last_eruption_year >= 0:
        return 0.35
    return 0.2


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    nearby = [nv for nv in ctx.volcanoes if nv.distance_km <= MAX_RELEVANT_DISTANCE_KM]
    if not nearby:
        return None

    scored: list[tuple[float, NearbyVolcano]] = []
    for nv in nearby:
        proximity = 1.0 - ramp(nv.distance_km, 5.0, MAX_RELEVANT_DISTANCE_KM)
        weight = _recency_weight(nv.volcano.last_eruption_year)
        scored.append((clamp01(proximity * (0.35 + 0.65 * weight)), nv))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    susceptibility, closest = scored[0]
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Live: is a nearby volcano erupting? ─────────────────────────────────
    # `continuing` is the Global Volcanism Program's own determination that an
    # eruption has not ended. It replaces the weekly activity report this code
    # used to scrape, which volcano.si.edu serves to no datacenter IP at all.
    activity_unavailable = "eruptions" in ctx.failed_feeds
    by_volcano = {e.volcano_number: e for e in ctx.eruptions}

    erupting: Optional[tuple[NearbyVolcano, object]] = None
    recent: Optional[tuple[NearbyVolcano, object]] = None
    for _, nv in scored:
        eruption = by_volcano.get(nv.volcano.number)
        if eruption is None:
            continue
        if eruption.continuing and erupting is None:
            erupting = (nv, eruption)
        elif not eruption.continuing and recent is None:
            recent = (nv, eruption)
    # An eruption in progress always outranks a past one, however close.
    if erupting is not None:
        recent = None

    events: list[HazardEvent] = []
    score = susceptibility * READINESS_CAP

    def _record(nv: NearbyVolcano, eruption) -> None:
        events.append(
            HazardEvent(
                id=f"gvp-{eruption.volcano_number}",
                hazard=hazard,
                title=f"{eruption.volcano_name} — {eruption.label}",
                latitude=eruption.latitude,
                longitude=eruption.longitude,
                occurred_at=(
                    datetime.combine(eruption.reference_date, time(), tzinfo=timezone.utc)
                    if eruption.reference_date
                    else None
                ),
                distance_km=nv.distance_km,
                url=nv.volcano.url,
                detail=eruption.label,
            )
        )

    if erupting is not None:
        nv, eruption = erupting
        proximity = 1.0 - ramp(nv.distance_km, 5.0, MAX_RELEVANT_DISTANCE_KM)
        # An eruption 15 km away and one 90 km away are both worth knowing
        # about, and are not remotely the same emergency.
        score = clamp01(0.45 + 0.5 * proximity)
        vei = f", VEI {eruption.vei}" if eruption.vei is not None else ""
        headline = f"{nv.volcano.name} is erupting — {nv.distance_km:.0f} km away"
        summary = (
            f"The Global Volcanism Program lists {nv.volcano.name} as an ongoing eruption "
            f"({eruption.label}{vei}), last observed "
            f"{eruption.reference_date.strftime('%d %B %Y') if eruption.reference_date else 'recently'}. "
            f"Follow the exclusion zone your volcano observatory has set, keep dust masks for "
            f"ashfall, and stay out of valleys and river channels downstream — lahars move far "
            f"faster than a person can run, even in dry weather."
        )
        _record(nv, eruption)
    elif recent is not None:
        nv, eruption = recent
        proximity = 1.0 - ramp(nv.distance_km, 5.0, MAX_RELEVANT_DISTANCE_KM)
        score = clamp01((0.3 + 0.35 * proximity) * _eruption_recency(eruption))
        headline = f"{nv.volcano.name} was {eruption.label} — {nv.distance_km:.0f} km away"
        summary = (
            f"{nv.volcano.name} is not currently erupting, but the Global Volcanism Program "
            f"records it as {eruption.label}. A volcano that has erupted this recently can do "
            f"so again, usually after days to weeks of detectable unrest — which is time enough "
            f"to act if you already know the evacuation route."
        )
        _record(nv, eruption)
    elif activity_unavailable:
        headline = (
            f"{closest.volcano.name} is {closest.distance_km:.0f} km away — status unavailable"
        )
        summary = (
            f"{closest.volcano.name} is the nearest volcano. The Global Volcanism Program's "
            f"eruption feed could not be reached, so Tayari cannot say whether it is currently "
            f"erupting — check your national volcano observatory if you need certainty."
        )
    else:
        last = closest.volcano.last_eruption_year
        when = (
            f"last erupted in {last}"
            if last and last > 0
            else (f"last erupted around {abs(last)} BCE" if last else "no dated eruption on record")
        )
        headline = f"{closest.volcano.name} is {closest.distance_km:.0f} km away — not erupting"
        summary = (
            f"{closest.volcano.name} ({closest.volcano.type or 'volcano'}, {when}) is the nearest "
            f"volcano and has no eruption in progress. Living near a volcano is mostly a matter of "
            f"knowing the evacuation route and keeping dust masks for ashfall; eruptions are "
            f"usually preceded by days or weeks of detectable unrest."
        )

    indicators = [
        indicator(
            "Nearest volcano",
            closest.volcano.name,
            detail=f"{closest.distance_km:.0f} km away"
            + (f" · {closest.volcano.type}" if closest.volcano.type else ""),
        ),
        indicator(
            "Last known eruption",
            str(closest.volcano.last_eruption_year)
            if closest.volcano.last_eruption_year and closest.volcano.last_eruption_year > 0
            else "Undated / prehistoric",
        ),
        indicator(
            "Volcanoes within 100 km",
            str(len(nearby)),
            detail=", ".join(nv.volcano.name for nv in nearby[:3]) if len(nearby) > 1 else None,
        ),
    ]
    if erupting is not None:
        indicators.append(
            indicator(
                "Eruption in progress",
                erupting[0].volcano.name,
                detail=f"{erupting[1].label} · Global Volcanism Program",
            )
        )

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        events=events,
        confidence=0.85 if erupting else (0.6 if recent else (0.3 if activity_unavailable else 0.7)),
        event_driven=erupting is not None,
        degraded=activity_unavailable,
        note=(
            "Eruption status comes from the Smithsonian Global Volcanism Program, which covers "
            "volcanoes with observatory reporting; a quiet entry is not a guarantee of no unrest "
            "at an unmonitored volcano."
        ),
    )
