"""
Impact-based forecasting engine.

Converts flood risk levels into human impact estimates:
- Population at risk (from pre-processed WorldPop data)
- Infrastructure at risk (schools, clinics, hospitals, markets)

Data is pre-computed and stored in basins.json for hackathon speed.
Architecture supports future real-time raster analysis.
"""

import json
import logging
from pathlib import Path

from app.models.schemas import (
    ImpactAssessment, InfrastructureItem, RiskLevel
)

logger = logging.getLogger(__name__)

# Load basin data at module level
_basins_path = Path(__file__).parent.parent / "data" / "basins.json"
_basin_data: dict = {}


def _load_basin_data():
    """Load basin data from JSON file."""
    global _basin_data
    if not _basin_data:
        with open(_basins_path) as f:
            _basin_data = json.load(f)
    return _basin_data


def compute_impact(basin_id: str, risk_level: RiskLevel) -> ImpactAssessment:
    """
    Compute impact assessment for a basin at a given risk level.

    Args:
        basin_id: Basin identifier (e.g., 'shabelle')
        risk_level: Current risk level

    Returns:
        ImpactAssessment with population and infrastructure at risk
    """
    data = _load_basin_data()

    # Get impact data for this basin
    impact_data = data.get("impact_data", {}).get(basin_id, {})
    infra_data = data.get("infrastructure", {}).get(basin_id, [])

    # For LOW risk, minimal impact
    if risk_level == RiskLevel.LOW:
        return ImpactAssessment(
            basin_id=basin_id,
            risk_level=risk_level,
            estimated_population_at_risk=0,
            schools_at_risk=0,
            clinics_at_risk=0,
            hospitals_at_risk=0,
            markets_at_risk=0,
            infrastructure_details=[],
            flood_zone_km=0,
        )

    # Get data for this risk level
    level_data = impact_data.get(risk_level.value, {})
    if not level_data:
        # Fall back to MODERATE if no data for this level
        level_data = impact_data.get("MODERATE", {
            "population_at_risk": 5000,
            "schools": 1,
            "clinics": 1,
            "hospitals": 0,
            "markets": 1,
            "flood_zone_km": 2,
        })

    flood_zone = level_data.get("flood_zone_km", 5)

    # Build infrastructure details
    # For higher risk levels, include more infrastructure
    infra_items = []
    schools_count = level_data.get("schools", 0)
    clinics_count = level_data.get("clinics", 0)
    hospitals_count = level_data.get("hospitals", 0)
    markets_count = level_data.get("markets", 0)

    # Pick infrastructure items by type
    type_counts = {
        "school": schools_count,
        "clinic": clinics_count,
        "hospital": hospitals_count,
        "market": markets_count,
    }

    for item in infra_data:
        item_type = item.get("type", "")
        if type_counts.get(item_type, 0) > 0:
            infra_items.append(InfrastructureItem(
                name=item["name"],
                type=item["type"],
                latitude=item["latitude"],
                longitude=item["longitude"],
            ))
            type_counts[item_type] -= 1

    return ImpactAssessment(
        basin_id=basin_id,
        risk_level=risk_level,
        estimated_population_at_risk=level_data.get("population_at_risk", 0),
        schools_at_risk=level_data.get("schools", 0),
        clinics_at_risk=level_data.get("clinics", 0),
        hospitals_at_risk=level_data.get("hospitals", 0),
        markets_at_risk=level_data.get("markets", 0),
        infrastructure_details=infra_items,
        flood_zone_km=flood_zone,
    )
