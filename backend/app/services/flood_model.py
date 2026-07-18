"""
Flood risk prediction model (calibrated heuristic).

Predicts flood probability 1-7 days ahead for each basin based on:
- Current and forecasted river discharge
- Upstream rainfall (cumulative and forecasted)
- Seasonal patterns
- Discharge anomaly (vs historical median)

The scorer is a transparent, calibrated multi-factor heuristic: a sigmoid on the
discharge-to-threshold ratio, weighted by the 3-day trend, upstream rainfall, and
season. It needs no trained-model artifact or heavy ML runtime — which keeps the
production image small and the forecast fully explainable.
"""

import logging
import numpy as np
from datetime import datetime, date
from typing import Optional

from app.models.schemas import (
    FloodRiskScore, RiskLevel, BasinConfig, DailyDischarge
)
from app.services.weather_data import RainfallData

logger = logging.getLogger(__name__)

# The highest probability we will ever report. Operational flood forecasting
# always carries irreducible uncertainty — model error, ungauged tributaries,
# and growing forecast lead time — so a credible early-warning system never
# tells a community it is "100% certain" to flood. We cap the signal here so
# every downstream surface (web gauge, mobile, SMS, advisory) stays honest.
MAX_FLOOD_PROBABILITY = 0.95


def compute_flood_risk(
    basin: BasinConfig,
    discharge_data: list[DailyDischarge],
    rainfall_data: list[RainfallData],
) -> FloodRiskScore:
    """
    Compute flood risk score for a basin.

    Uses feature engineering + a calibrated multi-factor heuristic scorer.

    Args:
        basin: Basin configuration with thresholds
        discharge_data: Recent + forecasted discharge
        rainfall_data: Recent + forecasted upstream rainfall

    Returns:
        FloodRiskScore with probability and risk level
    """
    features = engineer_features(basin, discharge_data, rainfall_data)

    # Compute daily probabilities for next 7 days
    probabilities = compute_daily_probabilities(basin, discharge_data, rainfall_data, features)

    # Overall probability is the max of next 3 days (actionable window)
    probability = max(probabilities[:3]) if probabilities else 0.0

    # Determine risk level from probability
    risk_level = probability_to_risk_level(probability)

    # Estimate days until threshold exceedance
    threshold_days = estimate_threshold_exceedance(
        basin, discharge_data, features
    )

    return FloodRiskScore(
        basin_id=basin.id,
        risk_level=risk_level,
        probability=round(probability, 3),
        probabilities_7day=[round(p, 3) for p in probabilities],
        threshold_exceedance_days=threshold_days,
        confidence=compute_confidence(features),
        model_features=features,
        generated_at=datetime.utcnow(),
    )


def engineer_features(
    basin: BasinConfig,
    discharge_data: list[DailyDischarge],
    rainfall_data: list[RainfallData],
) -> dict:
    """
    Engineer features from discharge + rainfall data.
    Returns a dict of feature name → value.
    """
    features = {}

    # ── Discharge features ──────────────────────────────────────────
    today_idx = None
    today = date.today()
    for i, d in enumerate(discharge_data):
        if d.date == today:
            today_idx = i
            break

    if today_idx is None:
        # Find the closest date to today
        today_idx = len(discharge_data) // 2

    # Current discharge
    current = discharge_data[today_idx] if today_idx < len(discharge_data) else None
    if current and current.discharge_mean is not None:
        features["discharge_current"] = current.discharge_mean
    else:
        features["discharge_current"] = 0.0

    # Discharge anomaly (ratio vs historical median)
    if basin.historical_median_m3s > 0:
        features["discharge_anomaly"] = features["discharge_current"] / basin.historical_median_m3s
    else:
        features["discharge_anomaly"] = 1.0

    # Discharge ratio to flood threshold
    if basin.flood_threshold_m3s > 0:
        features["discharge_flood_ratio"] = features["discharge_current"] / basin.flood_threshold_m3s
    else:
        features["discharge_flood_ratio"] = 0.0

    # Forecasted discharge (days 1-7)
    for d_offset in range(1, 8):
        idx = today_idx + d_offset
        if idx < len(discharge_data) and discharge_data[idx].discharge_mean is not None:
            features[f"discharge_forecast_d{d_offset}"] = discharge_data[idx].discharge_mean
        else:
            features[f"discharge_forecast_d{d_offset}"] = features["discharge_current"]

    # 3-day trend (slope)
    recent_vals = []
    for i in range(max(0, today_idx - 2), today_idx + 1):
        if i < len(discharge_data) and discharge_data[i].discharge_mean is not None:
            recent_vals.append(discharge_data[i].discharge_mean)
    if len(recent_vals) >= 2:
        features["discharge_trend_3d"] = (recent_vals[-1] - recent_vals[0]) / len(recent_vals)
    else:
        features["discharge_trend_3d"] = 0.0

    # Max forecasted discharge
    forecast_vals = [features.get(f"discharge_forecast_d{d}", 0) for d in range(1, 8)]
    features["discharge_forecast_max"] = max(forecast_vals) if forecast_vals else 0.0

    # ── Rainfall features ────────────────────────────────────────────
    rain_today_idx = None
    for i, r in enumerate(rainfall_data):
        if r.date == today:
            rain_today_idx = i
            break
    if rain_today_idx is None:
        rain_today_idx = len(rainfall_data) // 2

    # Cumulative past rainfall
    past_3d = sum(
        r.precipitation_sum
        for r in rainfall_data[max(0, rain_today_idx - 2): rain_today_idx + 1]
    )
    past_7d = sum(
        r.precipitation_sum
        for r in rainfall_data[max(0, rain_today_idx - 6): rain_today_idx + 1]
    )
    features["precip_cumulative_3d"] = past_3d
    features["precip_cumulative_7d"] = past_7d

    # Forecasted rainfall (next 3 days)
    for d_offset in range(1, 4):
        idx = rain_today_idx + d_offset
        if idx < len(rainfall_data):
            features[f"precip_forecast_d{d_offset}"] = rainfall_data[idx].precipitation_sum
        else:
            features[f"precip_forecast_d{d_offset}"] = 0.0

    features["precip_forecast_3d_total"] = sum(
        features.get(f"precip_forecast_d{d}", 0) for d in range(1, 4)
    )

    # ── Seasonal features ────────────────────────────────────────────
    features["month"] = today.month
    features["is_ond_season"] = 1.0 if today.month in [10, 11, 12] else 0.0
    features["is_mam_season"] = 1.0 if today.month in [3, 4, 5] else 0.0

    return features


def compute_daily_probabilities(
    basin: BasinConfig,
    discharge_data: list[DailyDischarge],
    rainfall_data: list[RainfallData],
    features: dict,
) -> list[float]:
    """
    Compute flood probability for each of the next 7 days.
    Uses a calibrated multi-factor heuristic model.
    """
    probabilities = []
    today = date.today()

    # Find today's index in discharge data
    today_idx = None
    for i, d in enumerate(discharge_data):
        if d.date == today:
            today_idx = i
            break
    if today_idx is None:
        today_idx = len(discharge_data) // 2

    for day_offset in range(1, 8):
        idx = today_idx + day_offset

        # Get forecasted discharge for this day
        if idx < len(discharge_data) and discharge_data[idx].discharge_mean is not None:
            forecast_discharge = discharge_data[idx].discharge_mean
        else:
            forecast_discharge = features.get("discharge_current", 0)

        # Factor 1: Discharge ratio to thresholds (primary signal)
        discharge_ratio = forecast_discharge / basin.flood_threshold_m3s if basin.flood_threshold_m3s > 0 else 0
        discharge_prob = _sigmoid(discharge_ratio, midpoint=0.7, steepness=6.0)

        # Factor 2: Discharge trend (rising = more dangerous)
        trend = features.get("discharge_trend_3d", 0)
        trend_factor = 1.0 + min(max(trend / basin.historical_median_m3s, -0.3), 0.3)

        # Factor 3: Upstream rainfall (leading indicator — rain today = flood in 2-3 days)
        rain_factor = 1.0
        precip_total = features.get("precip_cumulative_3d", 0) + features.get("precip_forecast_3d_total", 0)
        if precip_total > 50:  # Heavy rain
            rain_factor = 1.3
        elif precip_total > 30:
            rain_factor = 1.15
        elif precip_total > 15:
            rain_factor = 1.05

        # Factor 4: Seasonal adjustment
        season_factor = 1.0
        if features.get("is_ond_season", 0) == 1.0:
            season_factor = 1.1  # OND is peak flood season in East Africa
        elif features.get("is_mam_season", 0) == 1.0:
            season_factor = 1.05

        # Combine factors
        combined_prob = discharge_prob * trend_factor * rain_factor * season_factor

        # Reduce confidence for later days (uncertainty grows)
        uncertainty_decay = 1.0 - (day_offset - 1) * 0.05
        combined_prob *= uncertainty_decay

        # Clamp to [0, MAX]. The ceiling (not 1.0) keeps the forecast credible:
        # even a river already over its banks carries residual uncertainty.
        combined_prob = max(0.0, min(MAX_FLOOD_PROBABILITY, combined_prob))
        probabilities.append(combined_prob)

    return probabilities


def _sigmoid(x: float, midpoint: float = 0.5, steepness: float = 10.0) -> float:
    """Sigmoid function for smooth probability mapping."""
    z = steepness * (x - midpoint)
    # Clamp to prevent overflow
    z = max(-20, min(20, z))
    return 1.0 / (1.0 + np.exp(-z))


def probability_to_risk_level(probability: float) -> RiskLevel:
    """Convert flood probability to categorical risk level."""
    if probability >= 0.75:
        return RiskLevel.EXTREME
    elif probability >= 0.50:
        return RiskLevel.HIGH
    elif probability >= 0.25:
        return RiskLevel.MODERATE
    else:
        return RiskLevel.LOW


def estimate_threshold_exceedance(
    basin: BasinConfig,
    discharge_data: list[DailyDischarge],
    features: dict,
) -> Optional[int]:
    """Estimate the number of days until the flood threshold might be exceeded."""
    today = date.today()
    today_idx = None
    for i, d in enumerate(discharge_data):
        if d.date == today:
            today_idx = i
            break
    if today_idx is None:
        return None

    for d_offset in range(1, 8):
        idx = today_idx + d_offset
        if idx < len(discharge_data) and discharge_data[idx].discharge_mean is not None:
            if discharge_data[idx].discharge_mean >= basin.flood_threshold_m3s:
                return d_offset

    return None


def compute_confidence(features: dict) -> float:
    """
    Estimate model confidence based on data quality.
    Higher when we have strong signals in multiple features.
    """
    signals = 0
    total = 0

    # Check if we have real discharge data
    if features.get("discharge_current", 0) > 0:
        signals += 1
    total += 1

    # Check if we have forecast data
    if features.get("discharge_forecast_d1", 0) > 0:
        signals += 1
    total += 1

    # Check if we have rainfall data
    if features.get("precip_cumulative_3d", 0) > 0 or features.get("precip_forecast_3d_total", 0) > 0:
        signals += 1
    total += 1

    return round(signals / total, 2) if total > 0 else 0.5
