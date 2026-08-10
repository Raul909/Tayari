"""
Schemas for the multi-hazard layer.

Tayari began as a river-flood system: the unit of analysis was a *basin*, and
every model output was a flood probability. Those models still exist and still
run — see `app/services/flood_model.py` — but they only ever answered one
question for eight places.

This module generalizes the shape of an answer so the same product can speak
about an earthquake in Nepal, an eruption in Indonesia and a heatwave in Spain
without inventing a new response format for each. The unit of analysis becomes a
*location*, and the output becomes a list of `HazardRisk` — one per hazard that
location is genuinely exposed to.

The flood schemas in `app/models/schemas.py` are deliberately left untouched:
the calibrated basin pipeline is the most trustworthy thing in the codebase and
should not be destabilized by a refactor aimed at breadth.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.schemas import Language, RiskLevel, UserRole


# ─── Hazard taxonomy ──────────────────────────────────────────────────────────


class HazardType(str, Enum):
    """
    The hazards Tayari can assess anywhere on Earth.

    The list is limited to hazards for which a free, keyless, global,
    continuously-updated data source actually exists. A hazard we cannot
    genuinely observe is worse than a hazard we omit: a permanently green card
    for something we are not really watching teaches people to trust a signal
    that was never there.
    """

    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    TSUNAMI = "tsunami"
    VOLCANO = "volcano"
    CYCLONE = "cyclone"
    EXTREME_HEAT = "extreme_heat"
    WILDFIRE = "wildfire"
    DROUGHT = "drought"
    LANDSLIDE = "landslide"


class Onset(str, Enum):
    """
    How much warning the physics of a hazard permits.

    This drives the interface as much as the risk score does. A drought at
    MODERATE and an earthquake at MODERATE call for completely different
    behaviour, and the difference is onset: one gives you a season to prepare,
    the other gives you no notice at all and is therefore about *readiness*
    rather than *forecast*.
    """

    INSTANT = "instant"      # no useful forecast lead time (earthquake)
    MINUTES = "minutes"      # tsunami after a nearby rupture
    HOURS = "hours"          # flash flood, severe storm, volcanic ashfall
    DAYS = "days"            # river flood, heatwave, cyclone landfall
    SEASONS = "seasons"      # drought


class HazardIndicator(BaseModel):
    """One human-readable measurement behind a hazard score."""

    label: str
    value: str
    detail: Optional[str] = None
    trend: Optional[str] = Field(
        default=None, description="rising | falling | steady, when meaningful"
    )


class HazardEvent(BaseModel):
    """A real, dated occurrence — an earthquake, an eruption, a flood crest."""

    id: str
    hazard: HazardType
    title: str
    latitude: float
    longitude: float
    occurred_at: Optional[datetime] = None
    magnitude: Optional[float] = Field(default=None, description="Richter/moment magnitude, quakes only")
    depth_km: Optional[float] = None
    distance_km: Optional[float] = Field(default=None, description="Distance from the queried location")
    url: Optional[str] = None
    detail: Optional[str] = None


class HazardRisk(BaseModel):
    """
    Tayari's assessment of one hazard at one location.

    Two numbers, deliberately kept apart:

    * `susceptibility` — can this happen here at all? Slow-moving, derived from
      terrain, climatology and geological history. Nairobi's tsunami
      susceptibility is ~0 forever.
    * `score` — is it happening or about to? Fast-moving, derived from live
      feeds.

    Collapsing them into one number was tempting and wrong. A coastal city sits
    at high tsunami susceptibility permanently, and showing that as a permanent
    high *risk* is precisely the alarm fatigue that makes people ignore the one
    warning that matters.
    """

    hazard: HazardType
    label: str
    icon: str
    risk_level: RiskLevel
    score: float = Field(ge=0, le=1, description="Current, live risk 0-1")
    susceptibility: float = Field(
        ge=0, le=1, description="Baseline exposure of this location to this hazard"
    )
    headline: str = Field(description="One plain-language line: what is happening")
    summary: str = Field(default="", description="Two or three sentences of context")
    indicators: list[HazardIndicator] = Field(default_factory=list)
    onset: Onset
    lead_time: Optional[str] = Field(
        default=None, description="Plain-language warning time, e.g. '2-3 days'"
    )
    confidence: float = Field(ge=0, le=1, default=0.5)
    data_sources: list[str] = Field(default_factory=list)
    events: list[HazardEvent] = Field(default_factory=list)
    event_driven: bool = Field(
        default=True,
        description=(
            "True when the score reflects something that is happening or forecast; False "
            "when it is only the standing readiness floor for an unforecastable hazard"
        ),
    )
    degraded: bool = Field(
        default=False,
        description="True when a feed failed and this score is partial or stale",
    )
    note: Optional[str] = Field(
        default=None, description="Caveat shown with the card, e.g. why it is degraded"
    )
    assessed_at: datetime


# ─── Location ─────────────────────────────────────────────────────────────────


class TerrainProfile(BaseModel):
    """
    What the ground around a point looks like, sampled from a digital elevation
    model. Several hazards hinge on this and on nothing else: a landslide needs
    slope, a tsunami needs a coast and low ground, a storm surge needs both.
    """

    elevation_m: Optional[float] = None
    distance_to_coast_km: Optional[float] = Field(
        default=None, description="None when no ocean was found within the probe radius"
    )
    local_relief_m: Optional[float] = Field(
        default=None, description="Elevation range within ~25 km — a proxy for steepness"
    )
    max_slope_deg: Optional[float] = None
    is_coastal: bool = False


class LocationRef(BaseModel):
    """A place Tayari has been asked about."""

    latitude: float
    longitude: float
    name: Optional[str] = None
    admin1: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    population: Optional[int] = None
    terrain: Optional[TerrainProfile] = None


class LocationHazardProfile(BaseModel):
    """The complete multi-hazard answer for one location."""

    location: LocationRef
    overall_risk: RiskLevel
    top_hazard: Optional[HazardType] = None
    headline: str = ""
    hazards: list[HazardRisk] = Field(
        default_factory=list, description="Hazards this location is exposed to, most urgent first"
    )
    screened_out: list[HazardType] = Field(
        default_factory=list,
        description="Hazards assessed as not physically relevant here — shown so the "
        "absence of a card is visibly a decision rather than an omission",
    )
    languages: list[Language] = Field(default_factory=lambda: [Language.ENGLISH])
    generated_at: datetime
    partial: bool = Field(
        default=False, description="True when one or more feeds failed"
    )


class HazardAdvisoryRequest(BaseModel):
    """Ask for an advisory about one hazard at one location."""

    latitude: float
    longitude: float
    hazard: HazardType
    place_name: Optional[str] = None
    role: UserRole = UserRole.GENERAL
    language: Language = Language.ENGLISH


class HazardAdvisory(BaseModel):
    """
    What to do about one hazard, for one reader, in one language.

    `language` and `requested_language` differ whenever the model could not
    write the requested language safely and the advisory was delivered in a
    fallback instead. The interface has to show that difference: silently
    handing someone English when they asked for Daasanach is a smaller failure
    than pretending the English *is* Daasanach.
    """

    hazard: HazardType
    risk_level: RiskLevel
    latitude: float
    longitude: float
    place_name: Optional[str] = None
    role: UserRole
    language: Language = Field(description="The language actually delivered")
    requested_language: Language = Field(description="The language originally asked for")
    title: str
    body: str
    actions: list[str] = Field(default_factory=list)
    ai_generated: bool = Field(
        default=False,
        description="True when written by the model (may contain mistakes); False for "
        "human-reviewed templates",
    )
    generated_at: datetime
    valid_until: datetime


class PlaceResult(BaseModel):
    """A geocoding search hit."""

    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    country_code: Optional[str] = None
    admin1: Optional[str] = None
    population: Optional[int] = None
    timezone: Optional[str] = None
