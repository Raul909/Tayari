"""
River flood assessment for an arbitrary location.

This assessor deliberately does not implement a flood model. Tayari already has
one — `services/flood_model.compute_flood_risk` — calibrated against documented
historical floods and validated by true skill statistic per basin. Writing a
second, less tested scorer for the global case would mean the product's answer
to "will the river flood?" depends on which screen you asked from.

So the global path reuses it, and the only new work is supplying the thresholds
a basin config would normally carry. Those come from the river's own five-year
flow record: a flood is a flow this river almost never reaches. The result is
weaker than the curated basins' calibration and says so — `confidence` is
lower and the note is explicit — but it is the same model, fed honestly.
"""

import logging
from datetime import date
from typing import Optional

from app.hazards.assessors.base import build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import indicator, trend_word
from app.models.hazards import HazardRisk, HazardType
from app.models.schemas import BasinConfig, BasinCoordinates, UpstreamPoint
from app.services.flood_model import compute_flood_risk
from app.services.weather_data import RainfallData

logger = logging.getLogger(__name__)

hazard = HazardType.FLOOD


def _synthetic_basin(ctx: HazardContext) -> Optional[BasinConfig]:
    """
    Build the BasinConfig the calibrated model expects, from derived thresholds.

    `flood_threshold` is bankfull discharge, estimated as the median annual
    maximum flow — conventionally about a 2-year return period, the flow at
    which a channel fills and water begins spilling onto the floodplain.
    `warning_threshold` sits at 70% of that, where the river is high enough to
    act on but has not yet left its banks.
    """
    clim = ctx.discharge_climatology
    if clim is None or not clim.has_river:
        return None

    bankfull = max(clim.bankfull, 0.1)
    return BasinConfig(
        id=f"loc_{ctx.latitude:.3f}_{ctx.longitude:.3f}",
        name="This location",
        river="Nearest modelled river",
        country="",
        gauge_point=BasinCoordinates(latitude=ctx.latitude, longitude=ctx.longitude),
        upstream_point=UpstreamPoint(latitude=ctx.latitude, longitude=ctx.longitude),
        flood_threshold_m3s=bankfull,
        warning_threshold_m3s=max(bankfull * 0.7, 0.05),
        historical_median_m3s=max(clim.p50, 0.01),
    )


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    if not ctx.discharge:
        return None

    basin = _synthetic_basin(ctx)
    if basin is None:
        # No modelled river cell here. Heavy rainfall is still a hazard at such
        # a location, but it is surface-water flooding rather than river
        # flooding, and it surfaces on the storm card where the rainfall
        # forecast actually lives.
        return None

    rainfall = _rainfall_series(ctx)
    risk = compute_flood_risk(basin, ctx.discharge, rainfall)

    clim = ctx.discharge_climatology
    features = risk.model_features or {}
    current = features.get("discharge_current") or 0.0
    forecast_max = features.get("discharge_forecast_max") or 0.0
    trend = features.get("discharge_trend_3d", 0.0)

    ratio = (current / basin.flood_threshold_m3s) if basin.flood_threshold_m3s else 0.0

    if risk.threshold_exceedance_days is not None:
        days = risk.threshold_exceedance_days
        headline = (
            f"River may reach flood level in {days} day{'s' if days != 1 else ''}"
        )
    elif ratio >= 0.85:
        headline = "River is running close to its flood level"
    elif trend > 0 and ratio >= 0.5:
        headline = "River is rising but still below flood level"
    else:
        headline = "River levels are normal for this location"

    summary = (
        f"Flow is {current:,.0f} m³/s, {ratio * 100:.0f}% of the level at which this river fills "
        f"its channel. The next seven days peak at {forecast_max:,.0f} m³/s."
    )
    if risk.threshold_exceedance_days is not None:
        summary += (
            " Water leaving the channel typically reaches low-lying fields and roads before "
            "it reaches homes, so the time to move livestock and documents is now."
        )

    indicators = [
        indicator(
            "River flow now",
            f"{current:,.0f} m³/s",
            detail=f"{ratio * 100:.0f}% of flood level",
            trend=trend_word(trend, deadband=max(0.01, basin.historical_median_m3s * 0.02)),
        ),
        indicator("Peak in next 7 days", f"{forecast_max:,.0f} m³/s"),
        indicator(
            "Bankfull level (derived)",
            f"{basin.flood_threshold_m3s:,.0f} m³/s",
            detail=f"median annual peak over {clim.years} years — about a 1-in-2-year flow"
            if clim
            else None,
        ),
    ]
    rain_3d = features.get("precip_forecast_3d_total")
    if rain_3d is not None:
        indicators.append(
            indicator("Rain forecast, next 3 days", f"{rain_3d:.0f} mm")
        )

    return build_risk(
        hazard=hazard,
        score=risk.probability,
        # A location on a modelled river is by definition exposed to river
        # flooding; how exposed is a question of how close it usually runs to
        # its own high-flow threshold.
        susceptibility=min(1.0, 0.35 + 0.65 * min(1.0, ratio)),
        headline=headline,
        summary=summary,
        indicators=indicators,
        confidence=min(risk.confidence, 0.7),
        lead_time="1-7 days",
        note=(
            "Flood thresholds here are derived from this river's own five-year flow record "
            "rather than calibrated against documented floods. The eight monitored basins have "
            "thresholds calibrated event by event and are more reliable."
        ),
    )


def _rainfall_series(ctx: HazardContext) -> list[RainfallData]:
    """
    Adapt the weather bundle to the shape the flood model expects.

    The curated basins sample rainfall at an upstream catchment centre, which is
    the hydrologically correct place to look. For an arbitrary point we have no
    catchment delineation, so rainfall is sampled at the location itself — a
    real approximation, and one reason this path reports lower confidence.
    """
    weather = ctx.weather
    if weather is None:
        return []
    series: list[RainfallData] = []
    for day, precip in zip(weather.dates, weather.precip):
        if precip is None:
            continue
        series.append(RainfallData(day=day, precipitation_sum=precip, rain_sum=precip))
    return series
