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
from app.hazards.geo import haversine_km
from app.hazards.scoring import clamp01, indicator, ramp
from app.hazards.volcano_catalog import NearbyVolcano
from app.models.hazards import HazardEvent, HazardRisk, HazardType

hazard = HazardType.VOLCANO

# Beyond this, proximity stops meaning much for anything except ashfall, which
# is real but is a different (and much less acute) problem.
MAX_RELEVANT_DISTANCE_KM = 100.0
# How close a weekly-report coordinate must be to a catalog volcano to be
# considered the same volcano.
ACTIVITY_MATCH_KM = 25.0

READINESS_CAP = 0.28


def _eruption_recency(eruption) -> float:
    """How much a catalogued eruption should raise present concern, 0-1."""
    when = eruption.last_activity
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

    # ── Live: is any of them in this week's activity report? ─────────────────
    # When the feed is unavailable we must not imply the volcano is quiet — that
    # is the one claim this card is least entitled to make on missing data.
    activity_unavailable = "volcano_activity" in ctx.failed_feeds
    active: list[tuple[NearbyVolcano, object]] = []
    for _, nv in scored:
        for report in ctx.volcano_activity:
            if (
                haversine_km(
                    nv.volcano.latitude, nv.volcano.longitude, report.latitude, report.longitude
                )
                <= ACTIVITY_MATCH_KM
            ):
                active.append((nv, report))
                break

    # Nearest volcano with an eruption in the catalog's lookback window.
    recent: Optional[tuple[NearbyVolcano, object]] = None
    for _, nv in scored:
        for eruption in ctx.recent_eruptions:
            if eruption.volcano_number == nv.volcano.number:
                recent = (nv, eruption)
                break
        if recent:
            break

    events: list[HazardEvent] = []
    score = susceptibility * READINESS_CAP

    if active:
        nv, report = active[0]
        proximity = 1.0 - ramp(nv.distance_km, 5.0, MAX_RELEVANT_DISTANCE_KM)
        # An eruption in progress 15 km away and one 90 km away are both worth
        # knowing about, and are not remotely the same emergency.
        score = clamp01(0.45 + 0.5 * proximity)
        headline = f"{nv.volcano.name} is active — {nv.distance_km:.0f} km away"
        summary = (
            f"{report.status}. {report.summary[:320]}".strip()
            if report.summary
            else f"{nv.volcano.name} appears in the current Smithsonian/USGS Weekly Volcanic "
            f"Activity Report ({report.status})."
        )
        for nv_active, rep in active[:3]:
            events.append(
                HazardEvent(
                    id=f"gvp-{nv_active.volcano.number}",
                    hazard=hazard,
                    title=rep.headline,
                    latitude=nv_active.volcano.latitude,
                    longitude=nv_active.volcano.longitude,
                    distance_km=nv_active.distance_km,
                    url=nv_active.volcano.url,
                    detail=rep.status,
                )
            )
    elif recent is not None:
        # The weekly report — the genuinely live signal — is unreachable from
        # any datacenter IP. The eruption catalog is reachable and lags by a few
        # months, so it can say what has erupted recently but never what is
        # erupting today. The wording keeps that distinction rather than
        # borrowing the authority of a live feed.
        nv, eruption = recent
        proximity = 1.0 - ramp(nv.distance_km, 5.0, MAX_RELEVANT_DISTANCE_KM)
        score = clamp01((0.3 + 0.35 * proximity) * _eruption_recency(eruption))
        headline = f"{nv.volcano.name} was {eruption.label} — {nv.distance_km:.0f} km away"
        summary = (
            f"The Smithsonian eruption catalog records {nv.volcano.name} as "
            f"{eruption.label} ({eruption.activity_type.lower()}). That catalog lags real time "
            f"by a few months, so this is recent activity rather than a live status. A volcano "
            f"that has erupted this recently can do so again with days to weeks of warning — "
            f"know your evacuation route and keep dust masks for ashfall."
        )
        events.append(
            HazardEvent(
                id=f"gvp-eruption-{eruption.volcano_number}-{eruption.last_activity}",
                hazard=hazard,
                title=f"{eruption.volcano_name} — {eruption.activity_type}",
                latitude=eruption.latitude,
                longitude=eruption.longitude,
                occurred_at=(
                    datetime.combine(eruption.last_activity, time(), tzinfo=timezone.utc)
                    if eruption.last_activity
                    else None
                ),
                distance_km=nv.distance_km,
                url=nv.volcano.url,
                detail=eruption.label,
            )
        )
    elif activity_unavailable:
        headline = f"{closest.volcano.name} is {closest.distance_km:.0f} km away — live status unavailable"
        summary = (
            f"{closest.volcano.name} is the nearest volcano, and it has no eruption on record "
            f"in the last three years. The weekly activity report could not be reached, so "
            f"Tayari cannot confirm its status today — check your national volcano observatory "
            f"if you need certainty."
        )
    else:
        last = closest.volcano.last_eruption_year
        when = (
            f"last erupted in {last}"
            if last and last > 0
            else (f"last erupted around {abs(last)} BCE" if last else "no dated eruption on record")
        )
        headline = f"{closest.volcano.name} is {closest.distance_km:.0f} km away — currently quiet"
        summary = (
            f"{closest.volcano.name} ({closest.volcano.type or 'volcano'}, {when}) is the nearest "
            f"volcano and is not in the current weekly activity report. Living near a volcano is "
            f"mostly a matter of knowing the evacuation route and keeping dust masks for ashfall; "
            f"eruptions are usually preceded by days or weeks of detectable unrest."
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
    if active:
        indicators.append(
            indicator(
                "In this week's activity report",
                f"{len(active)} nearby",
                detail="Smithsonian / USGS Weekly Volcanic Activity Report",
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
        confidence=0.75 if active else (0.5 if recent else (0.3 if activity_unavailable else 0.6)),
        event_driven=bool(active),
        degraded=activity_unavailable and recent is None,
        note=(
            "Weekly activity reporting covers volcanoes with observatory coverage; a quiet "
            "entry here is not a guarantee of no unrest at an unmonitored volcano."
        ),
    )
