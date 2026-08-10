"""
Shared scoring vocabulary for the hazard assessors.

Nine hazards measured in nine different units — cubic metres per second, moment
magnitude, degrees Celsius, rainfall percentile — have to end up on one
comparable scale, or the interface cannot honestly say which one to worry about
first. Everything here exists to make that translation explicit and identical
across hazards rather than improvised nine times.
"""

import math
from typing import Optional

from app.models.hazards import HazardIndicator
from app.models.schemas import RiskLevel

# The band edges. These are the same thresholds the calibrated flood model has
# always used (`services/flood_model.probability_to_risk_level`), reused
# deliberately: a HIGH heat card and a HIGH flood card should mean the same
# thing to a reader, and they only can if one table defines both.
EXTREME_AT = 0.75
HIGH_AT = 0.50
MODERATE_AT = 0.25


def to_risk_level(score: float) -> RiskLevel:
    if score >= EXTREME_AT:
        return RiskLevel.EXTREME
    if score >= HIGH_AT:
        return RiskLevel.HIGH
    if score >= MODERATE_AT:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MODERATE: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.EXTREME: 3,
}


def sigmoid(x: float, midpoint: float = 0.5, steepness: float = 8.0) -> float:
    """Smooth 0-1 ramp, clamped against overflow."""
    z = max(-20.0, min(20.0, steepness * (x - midpoint)))
    return 1.0 / (1.0 + math.exp(-z))


def ramp(value: float, low: float, high: float) -> float:
    """
    Linear 0-1 ramp between two thresholds.

    Used where a sigmoid would be false precision — most hazard thresholds are
    expert judgement about where "uncomfortable" becomes "dangerous", and a
    straight line between two defensible numbers is the honest shape for that.
    """
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def indicator(
    label: str, value: str, detail: Optional[str] = None, trend: Optional[str] = None
) -> HazardIndicator:
    return HazardIndicator(label=label, value=value, detail=detail, trend=trend)


def trend_word(delta: float, deadband: float = 0.0) -> str:
    if delta > deadband:
        return "rising"
    if delta < -deadband:
        return "falling"
    return "steady"
