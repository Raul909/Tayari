"""
Earthquake assessment.

This is the hazard that forced the design of `HazardRisk` to keep susceptibility
and live score apart. Earthquakes cannot be predicted — not by Tayari, not by
anyone — so a card that behaves like a forecast would be a lie told at the
worst possible moment.

What can be stated truthfully is two things. First, how often and how hard this
ground has shaken in the instrumental record, which is what actually determines
whether the building someone is sitting in will survive. Second, what has
happened nearby in the last month, because a recent significant rupture raises
aftershock probability for a real and knowable window.

The live score therefore never claims to anticipate a rupture. It carries a
readiness floor proportional to long-run seismicity — capped below HIGH, since
nothing is imminent — and rises above that only in response to earthquakes that
have already occurred.
"""

import math
from datetime import datetime, timezone
from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.EARTHQUAKE

# A seismically active region never drops to "nothing to see here", but neither
# is it an emergency on a quiet Tuesday. Capping the readiness floor here keeps
# Tokyo permanently at MODERATE — which is exactly right — while leaving HIGH
# and EXTREME to mean something has actually happened.
READINESS_CAP = 0.34

AFTERSHOCK_WINDOW_DAYS = 14


def _shaking_intensity(magnitude: float, distance_km: float, depth_km: Optional[float]) -> float:
    """
    Roughly how strongly a given earthquake was felt at the query point, 0-1.

    A crude distance-attenuation relation, not a ShakeMap: magnitude sets the
    energy, distance and depth take it away. It is used only for ranking and
    phrasing, never presented to the reader as an intensity value.
    """
    hypo = math.sqrt(distance_km**2 + ((depth_km or 10.0) ** 2))
    # Felt radius grows roughly exponentially with magnitude.
    reach_km = 10.0 * (10 ** (0.5 * (magnitude - 4.0)))
    attenuation = 1.0 / (1.0 + (hypo / max(reach_km, 5.0)) ** 1.6)
    return clamp01(ramp(magnitude, 3.0, 7.5) * attenuation)


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    history = ctx.seismic
    quakes = ctx.recent_quakes or []

    if history is None and not quakes:
        return None

    # ── Susceptibility: what the instrumental record says about this ground ──
    susceptibility = 0.0
    rate = 0.0
    if history is not None:
        rate = history.annual_rate_m45
        # Log scale: 0.02 events/yr (one per 50 years) to 5/yr spans the range
        # from "stable craton" to "subduction margin", and only a log axis puts
        # those two on the same 0-1 line without one of them saturating.
        rate_score = ramp(math.log10(rate + 1e-3), -1.7, 0.7)
        magnitude_score = ramp(history.max_magnitude or 0.0, 5.0, 8.0)
        susceptibility = clamp01(0.55 * rate_score + 0.45 * magnitude_score)

    if susceptibility < SUSCEPTIBILITY_FLOOR and not quakes:
        return None

    # ── Live score: only what has already happened ───────────────────────────
    now = datetime.now(timezone.utc)
    recent_score = 0.0
    strongest = None
    for quake in quakes:
        if quake.magnitude is None:
            continue
        felt = _shaking_intensity(quake.magnitude, quake.distance_km or 0.0, quake.depth_km)
        age_days = (
            (now - quake.occurred_at).total_seconds() / 86400.0
            if quake.occurred_at
            else AFTERSHOCK_WINDOW_DAYS
        )
        # Aftershock sequences decay fast. Two weeks out, a mainshock is history
        # rather than an active elevation of risk.
        recency = clamp01(1.0 - (age_days / AFTERSHOCK_WINDOW_DAYS))
        weighted = felt * (0.45 + 0.55 * recency)
        if weighted > recent_score:
            recent_score, strongest = weighted, quake

    readiness_floor = susceptibility * READINESS_CAP
    score = max(readiness_floor, recent_score)
    # Whether this card is about something that happened or about the standing
    # readiness of a seismic region. The distinction drives which safety actions
    # are shown: post-event advice ("treat cracked buildings as unsafe") is
    # alarming nonsense on an ordinary day, and every seismic city sits at the
    # readiness floor permanently. Presence of *any* recent tremor is not the
    # test — a distant M2.6 changes nothing.
    event_driven = recent_score > readiness_floor

    # ── Wording ──────────────────────────────────────────────────────────────
    felt_recently = [q for q in quakes if (q.magnitude or 0) >= 4.0]
    if strongest is not None and recent_score >= 0.25:
        when = _relative_time(strongest.occurred_at, now)
        headline = (
            f"M{strongest.magnitude:.1f} earthquake {strongest.distance_km:.0f} km away, {when}"
        )
        summary = (
            f"{strongest.title}. Aftershocks are normal after an event this size and can "
            f"bring down structures the first shock weakened. Treat damaged buildings as "
            f"unsafe until someone qualified has looked at them."
        )
    elif history is not None and susceptibility >= 0.4:
        headline = "Seismically active area — no significant recent activity"
        summary = (
            f"No forecast of earthquakes is possible anywhere in the world, including here. "
            f"What is known is the record: {history.count_m45:,} magnitude 4.5+ earthquakes "
            f"within {history.radius_km} km since {history.since_year}"
        )
        if history.max_magnitude:
            summary += f", the largest an M{history.max_magnitude:.1f}"
            if history.max_event_year:
                summary += f" in {history.max_event_year}"
        summary += ". That makes preparation, not prediction, the thing that saves lives here."
    else:
        headline = "Low earthquake activity in the historical record"
        summary = (
            "This area has seen little significant seismic activity in the instrumental "
            "record. Earthquakes remain possible everywhere, but they are not a leading "
            "risk here."
        )

    # ── Indicators ───────────────────────────────────────────────────────────
    indicators = []
    if history is not None:
        indicators.append(
            indicator(
                f"M4.5+ within {history.radius_km} km",
                f"{history.count_m45:,}",
                detail=f"since {history.since_year} — about {rate:.1f} per year",
            )
        )
        if history.max_magnitude:
            detail = history.max_event_place or None
            if history.max_event_year:
                detail = f"{history.max_event_year}" + (f" — {detail}" if detail else "")
            indicators.append(
                indicator("Largest on record", f"M{history.max_magnitude:.1f}", detail=detail)
            )
    indicators.append(
        indicator(
            "Last 30 days",
            f"{len(quakes)} event{'s' if len(quakes) != 1 else ''}",
            detail=(
                f"{len(felt_recently)} at magnitude 4.0 or above"
                if felt_recently
                else "none at magnitude 4.0 or above"
            ),
        )
    )

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        events=quakes[:5],
        # High confidence in the *observations*: USGS is authoritative and these
        # are recorded events, not model output. The confidence figure says
        # nothing about predicting the next one, which remains impossible.
        confidence=0.9 if history is not None else 0.6,
        event_driven=event_driven,
        lead_time="No forecast is possible — this is a readiness score",
        degraded=history is None,
        note=(
            "Historical seismicity is unavailable, so this reflects recent events only."
            if history is None
            else None
        ),
    )


def _relative_time(when: Optional[datetime], now: datetime) -> str:
    if when is None:
        return "recently"
    hours = (now - when).total_seconds() / 3600.0
    if hours < 1:
        return "in the last hour"
    if hours < 24:
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''} ago"
    days = int(hours / 24)
    return f"{days} day{'s' if days != 1 else ''} ago"
