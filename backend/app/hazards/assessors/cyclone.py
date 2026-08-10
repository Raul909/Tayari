"""
Cyclone and severe storm assessment.

An honest scoping note, because this is the hazard where it would be easiest to
overclaim: Tayari does not track named tropical cyclones. There is no free,
keyless, global feed of live storm tracks and forecast cones, and inventing one
from wind fields would be worse than not having it.

What this card scores is the thing that actually reaches the ground — damaging
wind and torrential rain in the seven-day forecast — whether it arrives as a
named cyclone, a monsoon depression or a severe local squall. A household
boarding windows does not need the storm's name. Where a real cyclone is
inbound, the wind and rain signal rises days ahead of landfall, which is the
window this is meant to catch.
"""

from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.CYCLONE

# Damaging-wind bands, in km/h gusts. 60 is where light structures and trees
# start to fail; 120 is destructive; beyond 180 is major-cyclone territory.
GUST_NUISANCE = 55.0
GUST_DAMAGING = 120.0
GUST_SEVERE = 185.0

# Daily rainfall bands, in mm. 50 mm in a day is a soaking; 200 mm is the kind
# of total that produces flash flooding almost anywhere.
RAIN_HEAVY = 50.0
RAIN_TORRENTIAL = 200.0


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    weather = ctx.weather
    if weather is None:
        return None

    gusts = weather.future(weather.gust_max)
    winds = weather.future(weather.wind_max)
    rain = weather.future(weather.precip)
    if not gusts and not rain:
        return None

    max_gust = max(gusts) if gusts else 0.0
    max_wind = max(winds) if winds else 0.0
    max_daily_rain = max(rain) if rain else 0.0
    total_rain = sum(rain) if rain else 0.0

    # ── Susceptibility ───────────────────────────────────────────────────────
    # Tropical cyclones form in a latitude band and need warm ocean; the coast
    # is where surge is added to wind. Outside that band severe storms still
    # happen, so the floor never reaches zero.
    abs_lat = abs(ctx.latitude)
    tropical_band = 1.0 - ramp(abs_lat, 30.0, 45.0) if abs_lat >= 5.0 else ramp(abs_lat, 0.0, 5.0)
    coastal_bonus = 0.0
    coast_km = ctx.terrain.distance_to_coast_km
    if coast_km is not None:
        coastal_bonus = 0.35 * (1.0 - ramp(coast_km, 0.0, 100.0))

    # Climatology grounds this in what the place actually experiences rather
    # than in latitude alone: a wet tropical coast and a tropical desert sit at
    # the same latitude and do not face the same storms.
    wetness = 0.0
    if ctx.climate and ctx.climate.annual_precip_mean:
        wetness = 0.3 * ramp(ctx.climate.annual_precip_mean, 300.0, 1800.0)

    susceptibility = clamp01(0.15 + 0.5 * tropical_band + coastal_bonus + wetness)
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    # ── Live score ───────────────────────────────────────────────────────────
    gust_score = ramp(max_gust, GUST_NUISANCE, GUST_SEVERE)
    # Weighted so that gusts crossing into damaging territory dominate.
    if max_gust >= GUST_DAMAGING:
        gust_score = max(gust_score, 0.6 + 0.4 * ramp(max_gust, GUST_DAMAGING, GUST_SEVERE))
    rain_score = ramp(max_daily_rain, RAIN_HEAVY, RAIN_TORRENTIAL)
    multi_day_rain_score = ramp(total_rain, RAIN_HEAVY * 2, RAIN_TORRENTIAL * 2)

    # Wind and water are independently destructive, so the worse one leads
    # rather than being averaged away by the calmer one.
    score = max(gust_score, 0.85 * rain_score, 0.7 * multi_day_rain_score)
    if gust_score > 0.3 and rain_score > 0.3:
        score = clamp01(score + 0.12)  # wind plus water is worse than either

    peak_day = None
    if gusts and max_gust > 0:
        idx = weather.forecast_start + gusts.index(max_gust)
        if idx < len(weather.dates):
            peak_day = weather.dates[idx]

    # ── Wording ──────────────────────────────────────────────────────────────
    if max_gust >= GUST_DAMAGING:
        headline = f"Destructive winds forecast — gusts to {max_gust:.0f} km/h"
        summary = (
            f"Gusts of this strength take down power lines, tear roofing and make travel "
            f"dangerous. Secure or bring in anything loose outside, and expect power and "
            f"phone networks to fail."
        )
    elif max_daily_rain >= RAIN_TORRENTIAL * 0.6:
        headline = f"Torrential rain forecast — up to {max_daily_rain:.0f} mm in a day"
        summary = (
            f"{total_rain:.0f} mm is forecast over the next seven days. Rain at this rate "
            f"overwhelms drainage and causes flash flooding in low-lying streets and "
            f"underpasses well before any river responds."
        )
    elif max_gust >= GUST_NUISANCE * 1.4 or max_daily_rain >= RAIN_HEAVY:
        headline = f"Unsettled: gusts to {max_gust:.0f} km/h, {total_rain:.0f} mm of rain"
        summary = (
            "Nothing severe in the forecast, but enough wind and rain to disrupt travel and "
            "outdoor work."
        )
    else:
        headline = "No severe storm signal in the next 7 days"
        summary = (
            f"Winds peak at {max_wind:.0f} km/h with {total_rain:.0f} mm of rain over the week — "
            f"ordinary conditions for this location."
        )

    indicators = [
        indicator(
            "Peak gusts",
            f"{max_gust:.0f} km/h",
            detail=f"on {peak_day.strftime('%a %d %b')}" if peak_day else None,
        ),
        indicator("Heaviest day of rain", f"{max_daily_rain:.0f} mm"),
        indicator("Rain, next 7 days", f"{total_rain:.0f} mm"),
    ]
    if coast_km is not None and coast_km <= 25:
        indicators.append(
            indicator(
                "Storm surge exposure",
                f"{coast_km:.0f} km from the coast",
                detail="Onshore winds pile water against the shore ahead of the storm",
            )
        )

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        confidence=0.7,
        lead_time="1-7 days",
        note=(
            "Scored from forecast wind and rainfall, not from named-cyclone tracking. For an "
            "approaching named storm, your national meteorological service has the track and "
            "the landfall time."
        ),
    )
