"""
The contract every hazard assessor implements, plus the builder they share.

An assessor is a pure function from `HazardContext` to `HazardRisk | None`.
Returning `None` means "this hazard is not physically relevant here" — a
landlocked city gets no tsunami card at all rather than a permanently green one,
because a green card is a claim of active monitoring and nobody should have to
scroll past seven of those to reach the one that matters.
"""

from datetime import datetime, timezone
from typing import Optional, Protocol

from app.hazards.context import HazardContext
from app.hazards.registry import meta
from app.hazards.scoring import clamp01, to_risk_level
from app.models.hazards import HazardEvent, HazardIndicator, HazardRisk, HazardType


class Assessor(Protocol):
    hazard: HazardType

    def __call__(self, ctx: HazardContext) -> Optional[HazardRisk]: ...


def build_risk(
    hazard: HazardType,
    score: float,
    susceptibility: float,
    headline: str,
    summary: str = "",
    indicators: Optional[list[HazardIndicator]] = None,
    events: Optional[list[HazardEvent]] = None,
    confidence: float = 0.6,
    lead_time: Optional[str] = None,
    event_driven: bool = True,
    degraded: bool = False,
    note: Optional[str] = None,
) -> HazardRisk:
    """Assemble a `HazardRisk`, filling in everything the registry already knows."""
    m = meta(hazard)
    score = clamp01(score)
    return HazardRisk(
        hazard=hazard,
        label=m.label,
        icon=m.icon,
        risk_level=to_risk_level(score),
        score=round(score, 3),
        susceptibility=round(clamp01(susceptibility), 3),
        headline=headline,
        summary=summary,
        indicators=indicators or [],
        onset=m.onset,
        lead_time=lead_time if lead_time is not None else m.lead_time,
        confidence=round(clamp01(confidence), 2),
        data_sources=m.data_sources,
        events=events or [],
        event_driven=event_driven,
        degraded=degraded,
        note=note,
        assessed_at=datetime.now(timezone.utc),
    )


# Below this, a hazard is treated as not applicable to a location and no card is
# produced. It is deliberately low: the intent is to drop the physically
# impossible (tsunami in Chad), not to hide the merely unlikely.
SUSCEPTIBILITY_FLOOR = 0.08
