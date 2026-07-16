"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class UserRole(str, Enum):
    FARMER = "farmer"
    PASTORALIST = "pastoralist"
    COUNTY_OFFICER = "county_officer"
    COMMUNITY_LEADER = "community_leader"
    GENERAL = "general"


class Language(str, Enum):
    ENGLISH = "en"
    SOMALI = "so"
    SWAHILI = "sw"
    AMHARIC = "am"
    OROMO = "om"
    ARABIC = "ar"        # Sudanese / Juba Arabic (Blue Nile, White Nile)
    AFAR = "aa"          # Afar lowlands (Awash / Dubti)
    DINKA = "din"        # Jonglei / Bor (White Nile)
    DAASANACH = "dsh"    # Lower Omo / Omorate
    LUHYA = "luy"        # Budalangi / Lake Victoria basin (Nzoia)
    TURKANA = "tuv"      # Lake Turkana shore


# Advisories in these languages have human-reviewed templates in the repo. When
# the LLM is used instead (any language, but especially the others below), the
# advisory is flagged ai_generated so the UI can show an "AI can make mistakes"
# note. See Advisory.ai_generated.
VERIFIED_LANGUAGES = {Language.ENGLISH, Language.SOMALI, Language.SWAHILI}


class ReportStatus(str, Enum):
    WATER_RISING = "water_rising"
    ROAD_FLOODED = "road_flooded"
    EVACUATING = "evacuating"
    ALL_CLEAR = "all_clear"


# ─── Basin Models ─────────────────────────────────────────────────────────────

class BasinCoordinates(BaseModel):
    """Gauge point coordinates for a river basin."""
    latitude: float
    longitude: float


class UpstreamPoint(BaseModel):
    """Upstream catchment center for rainfall monitoring."""
    latitude: float
    longitude: float


class BasinConfig(BaseModel):
    """Configuration for a monitored river basin."""
    id: str
    name: str
    river: str
    country: str
    gauge_point: BasinCoordinates
    upstream_point: UpstreamPoint
    flood_threshold_m3s: float = Field(description="Discharge threshold for flood (m³/s)")
    warning_threshold_m3s: float = Field(description="Discharge threshold for warning (m³/s)")
    historical_median_m3s: float = Field(description="Long-term median discharge (m³/s)")
    description: str = ""
    languages: list[Language] = Field(
        default_factory=lambda: [Language.ENGLISH],
        description="Locally relevant advisory languages, mother-tongue first",
    )


class BasinSummary(BaseModel):
    """Basin with current risk level for list view."""
    id: str
    name: str
    river: str
    country: str
    latitude: float
    longitude: float
    current_risk: RiskLevel = RiskLevel.LOW
    current_discharge: Optional[float] = None
    flood_probability: Optional[float] = None
    last_updated: Optional[datetime] = None
    languages: list[Language] = Field(default_factory=lambda: [Language.ENGLISH])


# ─── Forecast Models ──────────────────────────────────────────────────────────

class DailyDischarge(BaseModel):
    """Single day discharge data."""
    date: date
    discharge_mean: Optional[float] = None
    discharge_max: Optional[float] = None
    discharge_min: Optional[float] = None
    discharge_median: Optional[float] = None


class DischargeTimeSeries(BaseModel):
    """Time series of discharge data."""
    basin_id: str
    data: list[DailyDischarge]
    flood_threshold: float
    warning_threshold: float
    historical_median: float


class FloodRiskScore(BaseModel):
    """ML model output: flood risk assessment."""
    basin_id: str
    risk_level: RiskLevel
    probability: float = Field(ge=0, le=1, description="Flood probability 0-1")
    probabilities_7day: list[float] = Field(description="Daily probabilities for next 7 days")
    threshold_exceedance_days: Optional[int] = Field(
        None, description="Estimated days until flood threshold crossed"
    )
    confidence: float = Field(ge=0, le=1, default=0.5)
    model_features: Optional[dict] = Field(None, description="Key features used by model")
    generated_at: datetime


# ─── Impact Models ────────────────────────────────────────────────────────────

class InfrastructureItem(BaseModel):
    """A school, clinic, or other infrastructure at risk."""
    name: str
    type: str  # school, clinic, hospital, market
    latitude: float
    longitude: float
    distance_to_river_km: Optional[float] = None


class ImpactAssessment(BaseModel):
    """Impact-based forecast: who and what is at risk."""
    basin_id: str
    risk_level: RiskLevel
    estimated_population_at_risk: int
    schools_at_risk: int
    clinics_at_risk: int
    hospitals_at_risk: int
    markets_at_risk: int
    infrastructure_details: list[InfrastructureItem] = []
    flood_zone_km: float = Field(description="Buffer radius from river in km")


# ─── Advisory Models ──────────────────────────────────────────────────────────

class Advisory(BaseModel):
    """AI-generated multilingual advisory."""
    basin_id: str
    risk_level: RiskLevel
    role: UserRole
    language: Language
    title: str
    body: str
    actions: list[str] = Field(description="Specific actions to take")
    generated_at: datetime
    valid_until: datetime
    ai_generated: bool = Field(
        default=False,
        description="True when written by the AI model (may contain mistakes); False for human-reviewed templates",
    )


# ─── Alert Models ─────────────────────────────────────────────────────────────

class AlertRequest(BaseModel):
    """Request to send an alert."""
    basin_id: str
    role: UserRole = UserRole.GENERAL
    language: Language = Language.ENGLISH
    phone_numbers: list[str] = Field(description="Phone numbers in international format")


class AlertResponse(BaseModel):
    """Result of sending an alert."""
    success: bool
    message: str
    sms_count: int = 0
    advisory_preview: str = ""


class AlertRecord(BaseModel):
    """Historical alert record."""
    id: int
    basin_id: str
    risk_level: RiskLevel
    role: UserRole
    language: Language
    recipients_count: int
    sent_at: datetime
    advisory_text: str


# ─── Community Report Models ─────────────────────────────────────────────────

class ReportSubmission(BaseModel):
    """Community report from the field."""
    basin_id: str
    status: ReportStatus
    latitude: float
    longitude: float
    description: Optional[str] = None
    reporter_name: Optional[str] = None
    photo_url: Optional[str] = None


class ReportEdit(BaseModel):
    """Editable fields on a community report. All optional — only sent fields change."""
    status: Optional[ReportStatus] = None
    description: Optional[str] = None
    reporter_name: Optional[str] = None


class AdviceSubmission(BaseModel):
    """Advice or guidance to attach to a community report."""
    message: str = Field(min_length=2, max_length=1000)
    author_name: Optional[str] = None
    author_role: Optional[str] = None


class ReportAdvice(BaseModel):
    """Stored advice on a community report."""
    id: int
    message: str
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    created_at: datetime


class CommunityReport(BaseModel):
    """Stored community report."""
    id: int
    basin_id: str
    status: ReportStatus
    latitude: float
    longitude: float
    description: Optional[str] = None
    reporter_name: Optional[str] = None
    photo_url: Optional[str] = None
    submitted_at: datetime
    advice: list[ReportAdvice] = Field(default_factory=list)


# ─── Full Forecast Response ───────────────────────────────────────────────────

class FullForecast(BaseModel):
    """Complete forecast for a basin — combines all data."""
    basin: BasinSummary
    discharge: DischargeTimeSeries
    risk: FloodRiskScore
    impact: ImpactAssessment
    recent_reports: list[CommunityReport] = []

# ─── Chat Response ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(max_length=500)
    role: UserRole = UserRole.GENERAL
    language: Language = Language.ENGLISH
    session_messages: list[dict] = Field(default_factory=list, description="Prior [{role, content}] turns")

class ChatResponse(BaseModel):
    reply: str
    messages_remaining: int


# ─── Auth and User Models ─────────────────────────────────────────────────────

class UserProfile(BaseModel):
    id: str
    display_name: Optional[str] = None
    preferred_role: str
    preferred_language: str
    created_at: datetime

class SavedBasinResponse(BaseModel):
    basin_id: str
    created_at: datetime

class UserPrefsResponse(BaseModel):
    phone_number: Optional[str] = None
    sms_language: str
    sms_role: str
    notify_risk_level: str

class UserPrefsUpdate(BaseModel):
    phone_number: Optional[str] = None
    sms_language: Optional[str] = None
    sms_role: Optional[str] = None
    notify_risk_level: Optional[str] = None
