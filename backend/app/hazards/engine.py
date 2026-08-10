"""
The orchestrator: location in, multi-hazard profile out.

Everything below this line is about ordering and honesty rather than physics.
The assessors decide what is true; this module decides what a person sees first,
which for a warning system is nearly as consequential. A page that lists nine
hazards alphabetically has technically told you about the flood arriving
tomorrow, and has functionally buried it.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.hazards import feeds
from app.hazards.assessors import ASSESSORS
from app.hazards.context import HazardContext, build_context
from app.hazards.registry import meta
from app.hazards.scoring import RISK_ORDER
from app.models.hazards import (
    HazardRisk,
    HazardType,
    LocationHazardProfile,
    LocationRef,
    Onset,
)
from app.models.schemas import Language, RiskLevel

logger = logging.getLogger(__name__)

# Hazards that arrive with no useful warning are promoted when they are live,
# because the reader's remaining decision time is measured in minutes.
URGENT_ONSETS = {Onset.INSTANT, Onset.MINUTES, Onset.HOURS}


def _sort_key(risk: HazardRisk) -> tuple:
    """
    Rank hazards by how urgently they need attention.

    Severity leads, but onset breaks near-ties: a landslide and a drought both
    scoring 0.4 are not equally urgent, because one of them can happen tonight.
    Susceptibility comes last so that among genuinely comparable cards the one
    this location is most exposed to sits higher.
    """
    urgency_bonus = 0.08 if (meta(risk.hazard).onset in URGENT_ONSETS and risk.score >= 0.25) else 0.0
    return (
        -RISK_ORDER[risk.risk_level],
        -(risk.score + urgency_bonus),
        -risk.susceptibility,
    )


async def assess_location(
    latitude: float,
    longitude: float,
    place: Optional[LocationRef] = None,
    ctx: Optional[HazardContext] = None,
) -> LocationHazardProfile:
    """
    Assess every hazard at a location and assemble the profile.

    An assessor raising is contained here rather than allowed to void the page:
    one hazard's bug costs its own card and is logged loudly, because the
    alternative — a blank screen during an emergency — is the worse failure by
    a wide margin.
    """
    if ctx is None:
        ctx = await build_context(latitude, longitude)

    risks: list[HazardRisk] = []
    screened_out: list[HazardType] = []

    for module in ASSESSORS:
        try:
            risk = module.assess(ctx)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Assessor '{module.hazard.value}' failed at ({latitude}, {longitude}): {e}")
            continue
        if risk is None:
            screened_out.append(module.hazard)
        else:
            risks.append(risk)

    risks.sort(key=_sort_key)

    overall = RiskLevel.LOW
    for risk in risks:
        if RISK_ORDER[risk.risk_level] > RISK_ORDER[overall]:
            overall = risk.risk_level

    top = risks[0] if risks else None
    headline = _profile_headline(risks, place)

    location = place or LocationRef(latitude=latitude, longitude=longitude)
    location.terrain = ctx.terrain

    return LocationHazardProfile(
        location=location,
        overall_risk=overall,
        top_hazard=top.hazard if top else None,
        headline=headline,
        hazards=risks,
        screened_out=screened_out,
        languages=_languages_for(location),
        generated_at=datetime.now(timezone.utc),
        partial=ctx.partial,
    )


def _profile_headline(risks: list[HazardRisk], place: Optional[LocationRef]) -> str:
    """One line summarising the whole location."""
    where = (place.name if place and place.name else "this location")
    if not risks:
        return f"No hazards could be assessed for {where} right now."

    elevated = [r for r in risks if RISK_ORDER[r.risk_level] >= RISK_ORDER[RiskLevel.MODERATE]]
    if not elevated:
        return (
            f"Nothing elevated at {where}. {len(risks)} hazard"
            f"{'s are' if len(risks) != 1 else ' is'} being monitored here."
        )

    top = elevated[0]
    if len(elevated) == 1:
        return f"{top.label} is the active concern at {where} — {top.headline}"
    others = len(elevated) - 1
    return (
        f"{top.label} leads {others + 1} elevated hazards at {where} — {top.headline}"
    )


def _languages_for(location: LocationRef) -> list[Language]:
    """
    Advisory languages to offer for a location.

    Tayari's non-English languages exist because they are the mother tongues of
    the communities the flood system was built for, and they carry hand-reviewed
    safety vocabulary. Offering them worldwide would be worse than useless — a
    Somali advisory is not helpful in Peru, and would displace the English one.
    So the extra languages appear only where they are actually spoken, and
    everywhere else the list is English alone until real coverage exists.
    """
    by_country: dict[str, list[Language]] = {
        "so": [Language.SOMALI, Language.ARABIC],
        "ke": [Language.SWAHILI],
        "tz": [Language.SWAHILI],
        "ug": [Language.SWAHILI],
        "et": [Language.AMHARIC, Language.OROMO, Language.AFAR],
        "er": [Language.ARABIC, Language.AFAR],
        "dj": [Language.AFAR, Language.ARABIC, Language.SOMALI],
        "ss": [Language.ARABIC, Language.DINKA],
        "sd": [Language.ARABIC],
        "eg": [Language.ARABIC],
        "sa": [Language.ARABIC],
        "ae": [Language.ARABIC],
        "ye": [Language.ARABIC],
        "iq": [Language.ARABIC],
        "jo": [Language.ARABIC],
        "ma": [Language.ARABIC],
        "dz": [Language.ARABIC],
        "tn": [Language.ARABIC],
        "ly": [Language.ARABIC],
    }
    code = (location.country_code or "").lower()
    extras = by_country.get(code, [])
    return [Language.ENGLISH] + [lang for lang in extras if lang != Language.ENGLISH]


async def global_events(min_magnitude: float = 4.5, days: int = 7) -> dict:
    """
    Live hazard events worldwide, for the map layer.

    Earthquakes come from USGS with a magnitude floor — below about M4.5 the map
    becomes a solid band along every plate boundary and stops communicating
    anything. Volcanic activity comes from the current weekly report.
    """
    from app.hazards import volcano_catalog

    quakes = await feeds.fetch_global_quakes(min_magnitude=min_magnitude, days=days)
    activity = await feeds.fetch_volcano_activity()

    eruptions = []
    for report in activity or []:
        matched = volcano_catalog.match_volcano(report.latitude, report.longitude)
        eruptions.append(
            {
                "id": f"gvp-{matched.number}" if matched else f"gvp-{report.name}",
                "hazard": HazardType.VOLCANO.value,
                "title": report.headline,
                "name": matched.name if matched else report.name,
                "country": matched.country if matched else None,
                "latitude": report.latitude,
                "longitude": report.longitude,
                "status": report.status,
                "url": matched.url if matched else report.url,
            }
        )

    return {
        "earthquakes": [q.model_dump(mode="json") for q in quakes],
        "volcanoes": eruptions,
        # Distinguishes "nothing is erupting" from "we could not find out",
        # so a client never renders an unread feed as an empty world.
        "unavailable": [] if activity is not None else ["volcanoes"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [
            "USGS Earthquake Hazards Program",
            "Smithsonian / USGS Weekly Volcanic Activity Report",
        ],
    }
