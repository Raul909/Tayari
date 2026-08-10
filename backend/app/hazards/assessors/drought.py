"""
Drought assessment.

The slowest hazard here, and the one where early warning has historically had
the most room to help: a drought developing over a season leaves months in which
a herder can sell stock while prices hold, or a household can plant a shorter-
cycle seed. The information usually exists long before anyone acts on it, which
is the exact gap Tayari was built to close.

Scoring compares the last 90 days of rainfall against the same 90-day calendar
window in each of the previous five years. That is a like-for-like comparison —
a dry August measured against other Augusts — rather than against an annual
mean, which would flag every dry season on Earth as a drought.

The honest limitation is the sample: five prior years give a coarse percentile,
so the card reports a low confidence and phrases the finding as a comparison
("driest of the last five years") rather than as a return period it cannot
support.
"""

from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.DROUGHT


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    weather = ctx.weather
    climate = ctx.climate
    if weather is None or climate is None:
        return None

    observed = weather.past(weather.precip, 90)
    if len(observed) < 60:
        return None
    current_90d = sum(observed)

    history = climate.precip_90d_history
    if len(history) < 3:
        return None
    baseline = sum(history) / len(history)

    # ── Susceptibility: how much does a dry season hurt here? ────────────────
    annual = climate.annual_precip_mean
    if annual is None:
        aridity = 0.5
    else:
        # Drier places are more exposed, but a true hyper-arid desert is not "in
        # drought" — it is a desert, and the people there are adapted to it.
        aridity = clamp01(1.0 - ramp(annual, 150.0, 1400.0))
        if annual < 120.0:
            aridity *= 0.5

    # Somewhere with wildly variable rainfall year to year is more drought-prone
    # than somewhere equally dry but reliable.
    variability = 0.0
    if baseline > 0 and len(history) >= 3:
        spread = (max(history) - min(history)) / baseline
        variability = clamp01(ramp(spread, 0.3, 1.5))

    susceptibility = clamp01(0.65 * aridity + 0.35 * variability)
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Live score: where does this season sit? ──────────────────────────────
    ratio = current_90d / baseline if baseline > 0 else 1.0
    deficit_score = 1.0 - ramp(ratio, 0.25, 1.0)

    percentile = climate.precip_percentile(current_90d)
    rank_score = (1.0 - percentile) if percentile is not None else deficit_score

    forecast_rain = sum(weather.future(weather.precip))
    relief = ramp(forecast_rain, 10.0, 80.0)

    score = clamp01((0.6 * deficit_score + 0.4 * rank_score) * susceptibility * (1.0 - 0.4 * relief))

    drier_than = sum(1 for v in history if current_90d < v)
    shortfall_pct = (1.0 - ratio) * 100.0

    if score >= 0.5:
        headline = f"Serious rainfall deficit — {shortfall_pct:.0f}% below normal"
        summary = (
            f"The last 90 days brought {current_90d:.0f} mm against a typical {baseline:.0f} mm "
            f"for this season, drier than {drier_than} of the last {len(history)} years. Water "
            f"points and pasture will come under pressure before crops visibly fail, so the "
            f"decisions that matter — destocking, water storage, seed choice — are the ones "
            f"made now rather than later."
        )
    elif score >= 0.25:
        headline = f"Rainfall running below normal — {current_90d:.0f} mm in 90 days"
        summary = (
            f"About {shortfall_pct:.0f}% below the {baseline:.0f} mm typical for this window. "
            f"Not yet a drought, but worth watching if the next rains are late."
        )
    else:
        headline = f"Rainfall near normal — {current_90d:.0f} mm in 90 days"
        summary = (
            f"Close to the {baseline:.0f} mm typical for this season here. No developing "
            f"rainfall deficit."
        )

    indicators = [
        indicator(
            "Rain, last 90 days",
            f"{current_90d:.0f} mm",
            detail=f"{shortfall_pct:+.0f}% vs typical {baseline:.0f} mm",
            trend="falling" if ratio < 0.85 else ("rising" if ratio > 1.15 else "steady"),
        ),
        indicator(
            "Compared with recent years",
            f"drier than {drier_than} of {len(history)}",
            detail=f"same 90-day window, {climate.years}-year record",
        ),
        indicator("Rain forecast, next 7 days", f"{forecast_rain:.0f} mm"),
    ]
    if annual is not None:
        indicators.append(indicator("Typical annual rainfall", f"{annual:.0f} mm"))

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        # Five comparison years is a thin sample for a percentile, and saying so
        # is more useful than a confident number nobody should rely on.
        confidence=0.45,
        lead_time="Weeks to months",
        note=(
            f"Compared against only {len(history)} previous years of reanalysis. Treat this as "
            f"a trend signal; your national meteorological service publishes seasonal forecasts "
            f"built on far longer records."
        ),
    )
