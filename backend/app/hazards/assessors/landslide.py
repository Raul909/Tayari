"""
Landslide assessment.

Two ingredients, both measurable, and the hazard needs both: a slope steep
enough to fail, and enough water in the ground to make it. Flat country never
gets a card no matter how hard it rains, and a mountainside in a dry spell sits
at its baseline. Multiplying rather than adding the two is what encodes that —
either one at zero should produce zero.

Terrain comes from the DEM probe in `geo.py`. Local relief carries more weight
than the point slope estimate: a 6 km sample spacing cannot resolve the roadside
cut or the hillside terrace that actually fails, but the presence of hundreds of
metres of relief within a few kilometres reliably indicates country where such
slopes exist. Relief-based susceptibility is standard practice in regional
landslide mapping for the same reason.

Antecedent rainfall matters as much as the storm itself. A hillside that has
absorbed three weeks of rain will fail under an amount that would run harmlessly
off dry ground, which is why the score reads both windows.
"""

from typing import Optional

from app.hazards.assessors.base import SUSCEPTIBILITY_FLOOR, build_risk
from app.hazards.context import HazardContext
from app.hazards.scoring import clamp01, indicator, ramp
from app.models.hazards import HazardRisk, HazardType

hazard = HazardType.LANDSLIDE

# Below this, terrain within the probe radius is too flat for slope failure to
# be a meaningful hazard.
MIN_RELIEF_M = 80.0


def assess(ctx: HazardContext) -> Optional[HazardRisk]:
    weather = ctx.weather
    terrain = ctx.terrain

    relief = terrain.local_relief_m
    if relief is None or relief < MIN_RELIEF_M:
        return None

    # ── Susceptibility: is this steep country? ───────────────────────────────
    relief_score = ramp(relief, MIN_RELIEF_M, 1200.0)
    slope_score = ramp(terrain.max_slope_deg or 0.0, 1.0, 12.0)
    susceptibility = clamp01(0.7 * relief_score + 0.3 * slope_score)
    if susceptibility < SUSCEPTIBILITY_FLOOR:
        return None

    if weather is None:
        return build_risk(
            hazard=hazard,
            score=susceptibility * 0.2,
            susceptibility=susceptibility,
            headline="Steep terrain — rainfall data unavailable",
            summary=(
                "This location sits in country steep enough for slope failure, but the rainfall "
                "feed that would show whether the ground is saturated is not available right now."
            ),
            indicators=[indicator("Local relief", f"{relief:.0f} m within 20 km")],
            confidence=0.3,
            degraded=True,
            note="Rainfall feed unavailable — this reflects terrain only.",
        )

    # ── Trigger: how much water is in and going into the ground? ─────────────
    rain_30d = sum(weather.past(weather.precip, 30))
    rain_7d = sum(weather.past(weather.precip, 7))
    future_rain = weather.future(weather.precip)
    rain_3d_forecast = sum(future_rain[:3])
    peak_day = max(future_rain) if future_rain else 0.0

    # Ground already wet from the preceding weeks.
    antecedent = clamp01(0.6 * ramp(rain_7d, 20.0, 150.0) + 0.4 * ramp(rain_30d, 80.0, 500.0))
    # The burst that actually sets it off.
    trigger = clamp01(0.6 * ramp(rain_3d_forecast, 25.0, 180.0) + 0.4 * ramp(peak_day, 20.0, 120.0))

    # Saturated ground plus a downpour is far worse than either alone, so the
    # antecedent term amplifies the trigger rather than being averaged with it.
    score = clamp01(susceptibility * trigger * (0.55 + 0.75 * antecedent))

    if score >= 0.5:
        headline = f"Slope failure risk — {rain_3d_forecast:.0f} mm forecast on saturated ground"
        summary = (
            f"{rain_7d:.0f} mm has already fallen here in the past week and more is coming. On "
            f"slopes this steep, saturated ground gives way with little warning, most often at "
            f"night and most often below road cuts and above stream channels. If you are downslope "
            f"of a steep face, this is the hazard to move away from."
        )
    elif score >= 0.25:
        headline = "Wet ground on steep terrain — watch for slope movement"
        summary = (
            f"{rain_7d:.0f} mm in the past week with {rain_3d_forecast:.0f} mm forecast. Watch for "
            f"new cracks in the ground, tilting trees or poles, and springs appearing where there "
            f"were none — all signs a slope is moving."
        )
    else:
        headline = f"Steep terrain, ground not saturated"
        summary = (
            f"Slope failure needs both steep ground and heavy rain. The terrain here qualifies "
            f"({relief:.0f} m of relief nearby), but with {rain_7d:.0f} mm in the past week and "
            f"{rain_3d_forecast:.0f} mm forecast, the water is not there."
        )

    indicators = [
        indicator(
            "Local relief",
            f"{relief:.0f} m",
            detail="elevation range within 20 km",
        ),
        indicator(
            "Rain, last 7 days",
            f"{rain_7d:.0f} mm",
            detail=f"{rain_30d:.0f} mm over 30 days",
        ),
        indicator("Rain forecast, next 3 days", f"{rain_3d_forecast:.0f} mm"),
        indicator("Heaviest day ahead", f"{peak_day:.0f} mm"),
    ]

    return build_risk(
        hazard=hazard,
        score=score,
        susceptibility=susceptibility,
        headline=headline,
        summary=summary,
        indicators=indicators,
        confidence=0.5,
        lead_time="Hours — during and just after heavy rain",
        note=(
            "Terrain is sampled from a digital elevation model at kilometre spacing, so it "
            "identifies landslide-prone country rather than individual unstable slopes. Local "
            "geology, deforestation and road cuts matter enormously and are not represented."
        ),
    )
