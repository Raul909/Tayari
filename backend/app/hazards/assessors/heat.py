"""
Extreme heat assessment.

Heat kills more people in most years than any other weather hazard, and it does
it without a single dramatic image, which is exactly why it needs a card of its
own rather than a line in a weather forecast.

The threshold is local, never absolute. 38 °C is an ordinary afternoon in
Khartoum and a mass-casualty event in Glasgow, because what harms people is heat
their bodies, homes and hospitals are not adapted to. So the comparison is
always against this location's own recent climatology for this time of year —
and the trigger is the 98th percentile of that distribution, not a number from a
table.

Two refinements matter. Humidity is applied as a multiplier on the dry-bulb
exceedance rather than being folded into it, because it is what stops sweat from
working — but the reanalysis baseline is dry-bulb, so comparing apparent
temperature directly against it mixes units and inflates every humid climate.
And duration counts: the danger of a heatwave is cumulative, since a night that
never cools below the mid-20s gives the body no chance to recover, and the death
toll climbs with each such night.
"""

from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.EXTREME_HEAT

# A night this warm prevents physiological recovery; consecutive ones are what
# turns a hot spell into a lethal one.
TROPICAL_NIGHT_C = 25.0


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    weather = ctx.weather
    climate = ctx.climate
    if weather is None:
        return None

    tmax_future = weather.future(weather.tmax)
    apparent_future = weather.future(weather.apparent_max)
    tmin_future = weather.future(weather.tmin)
    if not tmax_future:
        return None

    peak_tmax = max(tmax_future)
    peak_apparent = max(apparent_future) if apparent_future else peak_tmax

    # Without local climatology there is no honest threshold, so fall back to a
    # conservative absolute one and say the confidence is lower.
    if climate is None or climate.tmax_seasonal_p98 is None:
        p90 = 35.0
        p98 = 40.0
        seasonal_mean = 30.0
        degraded = True
    else:
        p90 = climate.tmax_seasonal_p90 or 35.0
        p98 = climate.tmax_seasonal_p98
        seasonal_mean = climate.tmax_seasonal_mean or p90
        degraded = False

    susceptibility = clamp01(ramp(p98, 26.0, 45.0))
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Live score ───────────────────────────────────────────────────────────
    # How far past the local 98th percentile the forecast goes. Five degrees
    # over a threshold that is itself a once-in-fifty-days temperature is an
    # exceptional event anywhere on Earth.
    #
    # Measured on dry-bulb only, against a dry-bulb baseline. Feeding apparent
    # temperature into this comparison mixes units — the reanalysis baseline has
    # no humidity term to be compared against — and it showed: a humid 30 °C
    # monsoon day in Kathmandu, entirely normal there, was scoring as dangerous
    # heat. Humidity still counts, but as the multiplier below, where it belongs.
    exceedance = peak_tmax - p98
    exceedance_score = ramp(exceedance, -2.0, 6.0)

    hot_days = sum(1 for t in tmax_future if t >= p90)
    duration_score = ramp(hot_days, 1.0, 5.0)

    tropical_nights = sum(1 for t in tmin_future if t >= TROPICAL_NIGHT_C)
    night_score = ramp(tropical_nights, 1.0, 4.0)

    # Humidity as a multiplier rather than an addend: when apparent temperature
    # runs far above dry-bulb, the same air temperature is considerably more
    # dangerous, and that gap is the signal.
    humidity_gap = peak_apparent - peak_tmax
    humidity_factor = 1.0 + 0.25 * ramp(humidity_gap, 1.0, 8.0)

    score = clamp01(
        (0.6 * exceedance_score + 0.25 * duration_score + 0.15 * night_score) * humidity_factor
    )

    # ── Wording ──────────────────────────────────────────────────────────────
    # Only mention apparent temperature when humidity is making it worse;
    # "34°C, feels like 33°C" reads as noise and undercuts the warning.
    feels_like = f", feels like {peak_apparent:.0f}°C" if humidity_gap >= 1.5 else ""

    if exceedance_score >= 0.6:
        headline = f"Dangerous heat — {peak_tmax:.0f}°C forecast{feels_like}"
        summary = (
            f"That is well above the hottest {hot_days or 1} days this location normally sees at "
            f"this time of year (typically {seasonal_mean:.0f}°C). Heat of this kind harms people "
            f"indoors and alone more than people outdoors — the ones at risk are the elderly, the "
            f"very young, and anyone working through the afternoon."
        )
    elif score >= 0.25:
        headline = f"Hot spell — {peak_tmax:.0f}°C over {hot_days} day{'s' if hot_days != 1 else ''}"
        summary = (
            f"Warmer than usual for the season here (normally around {seasonal_mean:.0f}°C) but "
            f"within what this place experiences. Worth planning outdoor work around."
        )
    else:
        headline = f"Normal temperatures — peaking at {peak_tmax:.0f}°C"
        summary = (
            f"The week ahead stays within the usual range for this location "
            f"(around {seasonal_mean:.0f}°C at this time of year)."
        )

    indicators = [
        indicator(
            "Hottest day ahead",
            f"{peak_tmax:.0f}°C",
            detail=f"feels like {peak_apparent:.0f}°C" if humidity_gap >= 1.5 else None,
        ),
        indicator(
            "Local extreme threshold",
            f"{p98:.0f}°C",
            detail=f"hottest 2% of days at this time of year, {climate.years}-year record"
            if climate
            else "generic threshold — local climatology unavailable",
        ),
        indicator(
            "Days above usual",
            f"{hot_days} of {len(tmax_future)}",
            detail=f"above {p90:.0f}°C",
        ),
    ]
    if tropical_nights:
        indicators.append(
            indicator(
                "Nights above 25°C",
                str(tropical_nights),
                detail="The body cannot recover from heat without a cool night",
            )
        )

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        confidence=0.5 if degraded else 0.8,
        lead_time="2-7 days",
        degraded=degraded,
        note=(
            "Local climatology was unavailable, so a generic temperature threshold was used "
            "instead of this location's own."
            if degraded
            else None
        ),
    )
