"""
Wildfire weather assessment.

This card scores fire *weather*, not fire. Detecting active fires needs
satellite thermal anomalies (NASA FIRMS), which requires an API key and
therefore does not meet this engine's keyless constraint. Rather than half-do
it, the card is named for what it actually measures and the distinction is
stated to the reader.

Fire weather is worth its own card regardless, because it is the forecastable
half of the problem. A fire needs fuel, ignition and weather; only the weather
can be predicted, and it is what decides whether an ignition stays a campfire or
crosses a valley. The scoring uses the Chandler Burning Index — an established
formulation from temperature and humidity — modulated by wind, which drives
spread, and by antecedent dryness, which decides whether there is anything ready
to burn.

Susceptibility is a fuel argument. A hyper-arid desert has little to burn and a
permanently wet rainforest rarely dries out; the dangerous middle is country
that grows a fuel load in a wet season and cures it in a dry one.
"""

from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.WILDFIRE

# Chandler Burning Index bands. The published scale calls 50 moderate and
# 97.5 extreme; those are the bands for the index itself, and mapping them
# straight onto a 0-1 risk score made the top of the range too easy to reach.
# The ramp is widened so EXTREME requires sustained conditions well past the
# index's own extreme threshold.
CBI_MODERATE = 55.0
CBI_EXTREME = 125.0

WET_DAY_MM = 1.0


def _chandler_burning_index(temp_c: float, humidity_pct: float) -> float:
    """
    Chandler Burning Index from temperature (°C) and relative humidity (%).

    Deliberately the published formula rather than an invented one: it has been
    used operationally for decades, and a hazard score should be traceable to
    something a fire officer would recognise.
    """
    rh = max(0.0, min(100.0, humidity_pct))
    return max(
        0.0,
        (((110.0 - 1.373 * rh) - 0.54 * (10.20 - temp_c)) * (124.0 * 10.0 ** (-0.0142 * rh))) / 60.0,
    )


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    weather = ctx.weather
    if weather is None:
        return None

    tmax_future = weather.future(weather.tmax)
    rh_future = weather.future(weather.rh_min)
    wind_future = weather.future(weather.wind_max)
    if not tmax_future or not rh_future:
        return None

    # ── Susceptibility: is there fuel that cures? ────────────────────────────
    annual_rain = ctx.climate.annual_precip_mean if ctx.climate else None
    if annual_rain is None:
        fuel_factor = 0.5
    else:
        # Enough rain to grow fuel, not so much that it never dries: rises
        # through semi-arid grassland and Mediterranean scrub, falls away in
        # true desert (nothing to burn) and wet tropics (never cures).
        amount = clamp01(
            ramp(annual_rain, 100.0, 400.0) * (1.0 - ramp(annual_rain, 1600.0, 3200.0))
        )
        # Annual total alone put Amsterdam above Phoenix, which is backwards.
        # Seasonality is what separates them: rain falling evenly all year keeps
        # a landscape green, while the same total concentrated into a wet season
        # grows fuel and then cures it. Every major fire climate on Earth has
        # that shape.
        seasonality = ctx.climate.precip_seasonality if ctx.climate else None
        season_factor = 0.5 if seasonality is None else ramp(seasonality, 0.4, 1.8)
        fuel_factor = clamp01(amount * (0.3 + 0.7 * season_factor))

    dry_days = sum(1 for p in weather.past(weather.precip, 30) if p < WET_DAY_MM)
    observed_30 = len(weather.past(weather.precip, 30)) or 1
    dryness = dry_days / observed_30

    susceptibility = clamp01(0.25 * dryness + 0.75 * fuel_factor)
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Is the fuel actually cured, for *this* place? ────────────────────────
    # The single most important correction in this assessor. A hot dry week
    # produces a high Chandler index anywhere, including over ground that is
    # green because the season has been wet — which had Amsterdam scoring
    # EXTREME on a warm August afternoon. What burns is fuel that is dry
    # relative to its own normal, so the seasonal rainfall deficit gates the
    # whole score.
    rain_90d = sum(weather.past(weather.precip, 90))
    seasonal_deficit = 0.5
    if ctx.climate is not None:
        percentile = ctx.climate.precip_percentile(rain_90d)
        if percentile is not None:
            # A wet season leaves green fuel; a dry one cures it.
            seasonal_deficit = clamp01(1.0 - percentile)
        elif ctx.climate.precip_90d_history:
            baseline = sum(ctx.climate.precip_90d_history) / len(ctx.climate.precip_90d_history)
            if baseline > 0:
                seasonal_deficit = clamp01(1.0 - ramp(rain_90d / baseline, 0.2, 1.1))
    # Never fully off: a green landscape in a wet year can still carry fire
    # through a long enough hot spell.
    cured = 0.3 + 0.7 * seasonal_deficit

    # ── Live score: fire weather over the forecast window ────────────────────
    cbi_values = [
        _chandler_burning_index(t, rh)
        for t, rh in zip(tmax_future, rh_future)
    ]
    peak_cbi = max(cbi_values) if cbi_values else 0.0
    # Scored on the mean of the three worst days rather than the single peak.
    # Fire danger is cumulative — one hot afternoon between damp days is not the
    # same as a dry spell — and a single-day peak saturated the index far too
    # easily, which is how a warm August day in the Netherlands reached the top
    # of the scale.
    worst_three = sorted(cbi_values, reverse=True)[:3]
    sustained_cbi = sum(worst_three) / len(worst_three) if worst_three else 0.0
    cbi_score = ramp(sustained_cbi, CBI_MODERATE, CBI_EXTREME)

    peak_wind = max(wind_future) if wind_future else 0.0
    # Wind is the difference between a fire that is fought and one that is fled.
    wind_factor = 1.0 + 0.45 * ramp(peak_wind, 20.0, 60.0)

    rain_30d = sum(weather.past(weather.precip, 30))
    rain_7d = sum(weather.past(weather.precip, 7))
    forecast_rain = sum(weather.future(weather.precip))
    # Recent or imminent rain genuinely removes the hazard for a while.
    wetting = ramp(rain_7d + forecast_rain, 5.0, 40.0)

    score = clamp01(cbi_score * wind_factor * susceptibility * cured * (1.0 - 0.75 * wetting))

    days_since_rain = _days_since_rain(weather)
    min_rh = min(rh_future) if rh_future else 100.0

    if score >= 0.5:
        headline = f"Dangerous fire weather — {peak_wind:.0f} km/h winds, {min_rh:.0f}% humidity"
        summary = (
            f"Hot, dry and windy over the next few days, with no rain in {days_since_rain} days. "
            f"A fire starting in these conditions spreads faster than people can walk. Avoid any "
            f"open flame or machinery that throws sparks, and decide now what you would take."
        )
    elif score >= 0.25:
        headline = "Elevated fire risk in the days ahead"
        summary = (
            f"Conditions are drying out — {days_since_rain} days without rain and humidity "
            f"dropping to {min_rh:.0f}%. Fires that start will be harder to control than usual."
        )
    else:
        headline = "Low fire danger this week"
        summary = (
            f"{rain_30d:.0f} mm of rain in the last month and humidity holding above "
            f"{min_rh:.0f}% keep fire spread unlikely."
        )

    indicators = [
        indicator(
            "Fire weather index",
            f"{sustained_cbi:.0f}",
            detail=f"Chandler Burning Index, worst 3 days (peak {peak_cbi:.0f}) — above 97 is extreme",
        ),
        indicator("Lowest humidity ahead", f"{min_rh:.0f}%"),
        indicator("Peak wind", f"{peak_wind:.0f} km/h"),
        indicator(
            "Days since rain",
            str(days_since_rain),
            detail=f"{rain_30d:.0f} mm in the last 30 days",
        ),
        indicator(
            "Fuel dryness for this season",
            f"{seasonal_deficit * 100:.0f}%",
            detail=f"{rain_90d:.0f} mm over 90 days, against this location's own normal",
        ),
    ]

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        confidence=0.6,
        lead_time="1-7 days",
        note=(
            "This measures fire weather, not active fires. Tayari has no satellite hot-spot "
            "feed; for fires burning right now, your national fire service is the source."
        ),
    )


def _days_since_rain(weather) -> int:
    """How many consecutive recent days recorded less than 1 mm."""
    past = weather.past(weather.precip, 60)
    count = 0
    for value in reversed(past):
        if value >= WET_DAY_MM:
            break
        count += 1
    return count
