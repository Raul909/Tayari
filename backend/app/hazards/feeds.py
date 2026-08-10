"""
Upstream data feeds for the multi-hazard engine.

Every hazard in Tayari is scored from a live, public, keyless source. This
module is the only place that talks to those sources; the assessors receive
parsed structures and never touch HTTP. That separation is what makes a hazard
degrade on its own — a USGS outage takes down the earthquake card and leaves the
other eight standing.

Caching is aggressive and tiered by how fast the underlying truth moves.
Bedrock does not change between requests, so seismic history is cached for a
day; an earthquake swarm does, so recent events are cached for three minutes.
"""

import asyncio
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings
from app.hazards.cache import TTLCache, geo_key
from app.hazards.geo import haversine_km
from app.models.hazards import HazardEvent, HazardType, PlaceResult

logger = logging.getLogger(__name__)

# ─── Endpoints ────────────────────────────────────────────────────────────────

# Routed through the Cloudflare Worker proxy — see `config.Settings`. Render's
# egress IP is rate-limited by Open-Meteo and times out against volcano.si.edu,
# which silently cost six of the nine hazards in production while every one of
# them worked locally. USGS is reachable from Render and is called directly.
FORECAST_API = settings.weather_api_base
ARCHIVE_API = settings.archive_api_base
GEOCODE_API = settings.geocode_api_base
GVP_WEEKLY_RSS = settings.volcano_activity_feed

USGS_COUNT = "https://earthquake.usgs.gov/fdsnws/event/1/count"
USGS_QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_EVENT_PAGE = "https://earthquake.usgs.gov/earthquakes/eventpage/"

DAILY_FORECAST_VARS = (
    "temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
    "precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max,relative_humidity_2m_min"
)
DAILY_ARCHIVE_VARS = "temperature_2m_max,precipitation_sum"

# How far back the weather bundle looks. 92 days is Open-Meteo's cap for
# `past_days` and happens to be exactly the window drought and fuel-dryness need.
PAST_DAYS = 92
FORECAST_DAYS = 7
CLIMATOLOGY_YEARS = 5


_weather_cache = TTLCache(ttl_seconds=3600)
_climate_cache = TTLCache(ttl_seconds=7 * 24 * 3600, max_entries=256)
_discharge_climatology_cache = TTLCache(ttl_seconds=7 * 24 * 3600, max_entries=256)
_seismic_cache = TTLCache(ttl_seconds=24 * 3600, max_entries=256)
_quake_cache = TTLCache(ttl_seconds=180)
_volcano_activity_cache = TTLCache(ttl_seconds=3 * 3600, max_entries=4)
_geocode_cache = TTLCache(ttl_seconds=24 * 3600)


# ─── Parsed feed structures ───────────────────────────────────────────────────


@dataclass
class WeatherBundle:
    """
    Daily weather for one point: ~92 days of history and 7 of forecast, in one
    array per variable with `forecast_start` marking the boundary.

    Note that gust and humidity values are only populated in the forecast half —
    Open-Meteo's past-days reanalysis does not carry them — so anything scored
    from those variables is a forward-looking signal by construction.
    """

    dates: list[date]
    tmax: list[Optional[float]]
    tmin: list[Optional[float]]
    apparent_max: list[Optional[float]]
    precip: list[Optional[float]]
    wind_max: list[Optional[float]]
    gust_max: list[Optional[float]]
    rh_min: list[Optional[float]]
    forecast_start: int

    def past(self, values: list[Optional[float]], days: int) -> list[float]:
        """The last `days` observed values, nulls dropped."""
        start = max(0, self.forecast_start - days)
        return [v for v in values[start : self.forecast_start] if v is not None]

    def future(self, values: list[Optional[float]]) -> list[float]:
        return [v for v in values[self.forecast_start :] if v is not None]


@dataclass
class ClimateBaseline:
    """
    What "normal" means at this location, derived from five years of reanalysis.

    Absolute thresholds are useless across a planet: 38 °C is an ordinary
    afternoon in Khartoum and a deadly anomaly in Glasgow. Every threshold in the
    heat, wildfire and drought assessors is therefore expressed against this
    local distribution rather than a global constant.
    """

    years: int
    # Seasonal = same calendar window (±15 days) across all sampled years, so a
    # July heatwave is compared against July and not against the annual mean.
    tmax_seasonal_mean: Optional[float] = None
    tmax_seasonal_p90: Optional[float] = None
    tmax_seasonal_p98: Optional[float] = None
    # Historical 90-day rainfall totals for this same calendar window, used to
    # place the current 90-day total in its local distribution.
    precip_90d_history: list[float] = field(default_factory=list)
    annual_precip_mean: Optional[float] = None
    # How unevenly rain falls across the year: (wettest month - driest month)
    # over the mean month. Total rainfall alone cannot tell a fire climate from
    # a wet one — Amsterdam and a Mediterranean hillside can receive similar
    # annual totals — but the shape of the year can. Rain spread evenly keeps
    # vegetation green; rain concentrated in one season grows a fuel load and
    # then cures it, which is the pattern every major fire climate shares.
    precip_seasonality: Optional[float] = None

    def precip_percentile(self, current_90d: float) -> Optional[float]:
        """Where the current 90-day rainfall total sits historically, 0-1."""
        if len(self.precip_90d_history) < 3:
            return None
        below = sum(1 for v in self.precip_90d_history if v <= current_90d)
        return below / len(self.precip_90d_history)


@dataclass
class DischargeClimatology:
    """
    Flow percentiles for one river cell, standing in for calibrated thresholds
    at locations Tayari has not individually calibrated.
    """

    years: int
    samples: int
    p50: float
    p90: float
    p98: float
    record_max: float
    median_annual_max: Optional[float] = None

    @property
    def bankfull(self) -> float:
        """
        The flow at which this river fills its channel, in m³/s.

        Taken as the median annual maximum — roughly a 2-year return period,
        the conventional bankfull estimate. An earlier version used the 98th
        percentile of daily flow, which sounds strict and is not: a river
        exceeds it on about seven days a year, every year, which is a seasonal
        high and emphatically not a flood. That version had Tokyo at EXTREME
        during ordinary monsoon rain.
        """
        if self.median_annual_max is not None:
            return self.median_annual_max
        return self.p98

    @property
    def has_river(self) -> bool:
        """
        Whether this coordinate sits on a river GloFAS actually models.

        Off the river network the model still returns a number, just a
        vanishingly small one. Without this check a hilltop in the desert gets a
        flood card whose threshold is a fraction of a cubic metre per second,
        and it would light up the first time it rained.
        """
        return self.p98 >= 1.0


@dataclass
class SeismicHistory:
    """How often, and how hard, the ground near this point has shaken."""

    radius_km: int
    since_year: int
    count_m45: int
    max_magnitude: Optional[float] = None
    max_event_year: Optional[int] = None
    max_event_place: Optional[str] = None
    # Great earthquakes anywhere in the surrounding ocean basin. Kept separate
    # from the local counts because tsunami sources are characteristically
    # *distant*: the 2004 Indian Ocean tsunami killed people in Chennai from a
    # rupture 1,500 km away, and Chennai's own 250 km neighbourhood is
    # essentially aseismic. Judging tsunami exposure on local seismicity would
    # have cleared every coastline that has actually suffered one.
    distant_great_quakes: int = 0
    distant_radius_km: int = 0

    @property
    def annual_rate_m45(self) -> float:
        span = max(1, date.today().year - self.since_year)
        return self.count_m45 / span


@dataclass
class VolcanoActivity:
    """One volcano currently featured in the Smithsonian/USGS weekly report."""

    name: str
    latitude: float
    longitude: float
    headline: str
    status: str
    summary: str
    url: str


# ─── HTTP ─────────────────────────────────────────────────────────────────────


_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Shared client for every hazard feed. Connection reuse matters here —
    a cold profile makes six upstream calls and TLS setup would dominate."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=10.0),
            headers={"User-Agent": "Tayari/2.0 (multi-hazard early warning; +https://tayari.pages.dev)"},
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=60),
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


# ─── River discharge climatology ──────────────────────────────────────────────

FLOOD_ARCHIVE_API = settings.flood_api_base


async def fetch_discharge_climatology(
    latitude: float, longitude: float
) -> Optional["DischargeClimatology"]:
    """
    Five years of daily river discharge at a point, reduced to flow percentiles.

    The eight curated basins have thresholds calibrated against documented
    historical floods — the most trustworthy numbers in the system. An arbitrary
    coordinate has nothing of the kind, and inventing an absolute threshold in
    m³/s would be meaningless across rivers spanning six orders of magnitude.

    So the threshold comes from the river's own record: what counts as a flood
    here is a flow this river rarely reaches. It is weaker than true return-period
    analysis and is labelled as such wherever it surfaces, but it is derived from
    real observations at the real location rather than guessed.
    """
    key = geo_key(latitude, longitude, precision=2)
    cached = _discharge_climatology_cache.get(key)
    if cached is not None:
        return cached

    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=365 * CLIMATOLOGY_YEARS)

    client = await get_client()
    try:
        resp = await client.get(
            FLOOD_ARCHIVE_API,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "river_discharge",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=45.0,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Discharge climatology failed at ({latitude}, {longitude}): {e}")
        return None

    times = daily.get("time") or []
    raw = daily.get("river_discharge") or []
    values = [v for v in raw if v is not None]
    if len(values) < 365:
        return None

    # Annual maxima, for the bankfull threshold. One peak per year is the
    # standard input to flood-frequency analysis, and the median of them
    # approximates the 2-year return period — the flow at which a channel is
    # full and water starts spilling onto the floodplain.
    by_year: dict[int, float] = {}
    for stamp, value in zip(times, raw):
        if value is None:
            continue
        year = int(stamp[:4])
        if value > by_year.get(year, float("-inf")):
            by_year[year] = value
    annual_maxima = sorted(by_year.values())

    climatology = DischargeClimatology(
        years=CLIMATOLOGY_YEARS,
        samples=len(values),
        p50=_percentile(values, 0.50) or 0.0,
        p90=_percentile(values, 0.90) or 0.0,
        p98=_percentile(values, 0.98) or 0.0,
        median_annual_max=(
            _percentile(annual_maxima, 0.50) if len(annual_maxima) >= 3 else None
        ),
        record_max=round(max(values), 2),
    )
    _discharge_climatology_cache.set(key, climatology)
    return climatology


# ─── Weather ──────────────────────────────────────────────────────────────────


async def fetch_weather_bundle(latitude: float, longitude: float) -> Optional[WeatherBundle]:
    """Daily weather history + forecast for a point. None if the feed fails."""
    key = geo_key(latitude, longitude)
    cached = _weather_cache.get(key)
    if cached is not None:
        return cached

    client = await get_client()
    try:
        resp = await client.get(
            FORECAST_API,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": DAILY_FORECAST_VARS,
                "past_days": PAST_DAYS,
                "forecast_days": FORECAST_DAYS,
                "timezone": "UTC",
            },
        )
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Weather feed failed at ({latitude}, {longitude}): {e}")
        return None

    times = daily.get("time") or []
    if not times:
        return None

    dates = [date.fromisoformat(t) for t in times]
    today = datetime.now(timezone.utc).date()
    forecast_start = next((i for i, d in enumerate(dates) if d >= today), len(dates))

    bundle = WeatherBundle(
        dates=dates,
        tmax=daily.get("temperature_2m_max") or [],
        tmin=daily.get("temperature_2m_min") or [],
        apparent_max=daily.get("apparent_temperature_max") or [],
        precip=daily.get("precipitation_sum") or [],
        wind_max=daily.get("wind_speed_10m_max") or [],
        gust_max=daily.get("wind_gusts_10m_max") or [],
        rh_min=daily.get("relative_humidity_2m_min") or [],
        forecast_start=forecast_start,
    )
    _weather_cache.set(key, bundle)
    return bundle


async def fetch_climate_baseline(latitude: float, longitude: float) -> Optional[ClimateBaseline]:
    """Five years of reanalysis, reduced to the local normals the assessors need."""
    key = geo_key(latitude, longitude, precision=1)
    cached = _climate_cache.get(key)
    if cached is not None:
        return cached

    # The reanalysis archive lags real time by around five days. The extra 120
    # days on the start bound are not slack: the oldest 90-day comparison window
    # ends five years ago and reaches back a further 90 days before that, so
    # without the padding the earliest year is always short of data and silently
    # drops out of the drought baseline.
    end = date.today() - timedelta(days=7)
    start = end - timedelta(days=365 * CLIMATOLOGY_YEARS + 120)

    client = await get_client()
    try:
        resp = await client.get(
            ARCHIVE_API,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": DAILY_ARCHIVE_VARS,
                "timezone": "UTC",
            },
            timeout=45.0,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Climate archive failed at ({latitude}, {longitude}): {e}")
        return None

    times = daily.get("time") or []
    if not times:
        return None

    dates = [date.fromisoformat(t) for t in times]
    tmax_series = daily.get("temperature_2m_max") or []
    precip_series = daily.get("precipitation_sum") or []

    today = date.today()
    doy_now = today.timetuple().tm_yday

    def _day_distance(d: date) -> int:
        """Circular distance in days between `d` and today's calendar date."""
        diff = abs(d.timetuple().tm_yday - doy_now)
        return min(diff, 365 - diff)

    seasonal_tmax = [
        t
        for d, t in zip(dates, tmax_series)
        if t is not None and _day_distance(d) <= 15
    ]

    # Historical 90-day rainfall totals ending on the same calendar date in each
    # prior year — the like-for-like comparison for "is this season dry?".
    precip_by_date = {d: (p or 0.0) for d, p in zip(dates, precip_series)}
    history_90d: list[float] = []
    for years_back in range(1, CLIMATOLOGY_YEARS + 1):
        try:
            anchor = today.replace(year=today.year - years_back)
        except ValueError:  # 29 February
            anchor = today.replace(year=today.year - years_back, day=28)
        window = [
            precip_by_date.get(anchor - timedelta(days=offset))
            for offset in range(90)
        ]
        present = [v for v in window if v is not None]
        if len(present) >= 60:
            history_90d.append(sum(present))

    annual_mean = None
    valid_precip = [p for p in precip_series if p is not None]
    if valid_precip:
        annual_mean = sum(valid_precip) / len(valid_precip) * 365.0

    # Monthly climatology across all sampled years, reduced to a seasonality
    # index. Uses daily means per month rather than monthly totals so months of
    # unequal length and partial years at the edges of the window compare fairly.
    monthly_totals: dict[int, list[float]] = {}
    for d, p in zip(dates, precip_series):
        if p is not None:
            monthly_totals.setdefault(d.month, []).append(p)
    seasonality = None
    if len(monthly_totals) == 12:
        monthly_means = [sum(v) / len(v) for v in monthly_totals.values()]
        overall = sum(monthly_means) / len(monthly_means)
        if overall > 0:
            seasonality = round((max(monthly_means) - min(monthly_means)) / overall, 3)

    baseline = ClimateBaseline(
        years=CLIMATOLOGY_YEARS,
        tmax_seasonal_mean=_mean(seasonal_tmax),
        tmax_seasonal_p90=_percentile(seasonal_tmax, 0.90),
        tmax_seasonal_p98=_percentile(seasonal_tmax, 0.98),
        precip_90d_history=history_90d,
        annual_precip_mean=round(annual_mean, 1) if annual_mean is not None else None,
        precip_seasonality=seasonality,
    )
    _climate_cache.set(key, baseline)
    return baseline


def _mean(values: list[float]) -> Optional[float]:
    return round(sum(values) / len(values), 2) if values else None


def _percentile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered)) - 1)))
    return round(ordered[idx], 2)


# ─── Earthquakes ──────────────────────────────────────────────────────────────

SEISMIC_RADIUS_KM = 250
SEISMIC_SINCE_YEAR = 1970
RECENT_QUAKE_RADIUS_KM = 400
RECENT_QUAKE_DAYS = 30
RECENT_QUAKE_MIN_MAG = 2.5

# Tsunami sources are basin-scale. 3,000 km covers the subduction zone that
# actually threatens a given coastline — Sumatra from Sri Lanka, Chile from
# Polynesia, the Aleutians from Hawai'i — and M7.5 is roughly the floor for
# generating a destructive far-field wave.
TSUNAMI_SOURCE_RADIUS_KM = 3000
TSUNAMI_SOURCE_MIN_MAGNITUDE = 7.5


async def fetch_seismic_history(latitude: float, longitude: float) -> Optional[SeismicHistory]:
    """
    The long-run seismicity of a location, from the USGS catalog.

    This is Tayari's answer to a question nobody can forecast. We cannot say
    when the next earthquake will be, but "107 magnitude-4.5+ events within
    250 km since 1970, the largest an M8" tells a resident something true and
    actionable about the building they live in.
    """
    key = geo_key(latitude, longitude, precision=1)
    cached = _seismic_cache.get(key)
    if cached is not None:
        return cached

    client = await get_client()
    common = {
        "format": "geojson",
        "latitude": latitude,
        "longitude": longitude,
        "maxradiuskm": SEISMIC_RADIUS_KM,
    }

    async def _count() -> Optional[int]:
        resp = await client.get(
            USGS_COUNT,
            params={**common, "minmagnitude": 4.5, "starttime": f"{SEISMIC_SINCE_YEAR}-01-01"},
        )
        resp.raise_for_status()
        return resp.json().get("count")

    async def _largest() -> Optional[dict]:
        resp = await client.get(
            USGS_QUERY,
            params={
                **common,
                "maxradiuskm": 300,
                "minmagnitude": 5.0,
                "starttime": "1900-01-01",
                "orderby": "magnitude",
                "limit": 1,
            },
        )
        resp.raise_for_status()
        features = resp.json().get("features") or []
        return features[0] if features else None

    async def _distant_great() -> Optional[int]:
        """Great earthquakes across the surrounding ocean basin — tsunami sources."""
        resp = await client.get(
            USGS_COUNT,
            params={
                "format": "geojson",
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": TSUNAMI_SOURCE_RADIUS_KM,
                "minmagnitude": TSUNAMI_SOURCE_MIN_MAGNITUDE,
                "starttime": "1900-01-01",
            },
        )
        resp.raise_for_status()
        return resp.json().get("count")

    try:
        count, largest, distant = await asyncio.gather(_count(), _largest(), _distant_great())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"USGS seismic history failed at ({latitude}, {longitude}): {e}")
        return None

    history = SeismicHistory(
        radius_km=SEISMIC_RADIUS_KM,
        since_year=SEISMIC_SINCE_YEAR,
        count_m45=count or 0,
        distant_great_quakes=distant or 0,
        distant_radius_km=TSUNAMI_SOURCE_RADIUS_KM,
    )
    if largest:
        props = largest.get("properties") or {}
        history.max_magnitude = props.get("mag")
        history.max_event_place = props.get("place")
        epoch_ms = props.get("time")
        if epoch_ms:
            history.max_event_year = datetime.fromtimestamp(
                epoch_ms / 1000, tz=timezone.utc
            ).year

    _seismic_cache.set(key, history)
    return history


async def fetch_recent_quakes(
    latitude: float, longitude: float, radius_km: int = RECENT_QUAKE_RADIUS_KM
) -> Optional[list[HazardEvent]]:
    """Earthquakes near this point in the last 30 days, largest first."""
    key = f"{geo_key(latitude, longitude)}|{radius_km}"
    cached = _quake_cache.get(key)
    if cached is not None:
        return cached

    start = (datetime.now(timezone.utc) - timedelta(days=RECENT_QUAKE_DAYS)).date()
    client = await get_client()
    try:
        resp = await client.get(
            USGS_QUERY,
            params={
                "format": "geojson",
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": radius_km,
                "minmagnitude": RECENT_QUAKE_MIN_MAG,
                "starttime": start.isoformat(),
                "orderby": "magnitude",
                "limit": 25,
            },
        )
        resp.raise_for_status()
        features = resp.json().get("features") or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"USGS recent quakes failed at ({latitude}, {longitude}): {e}")
        return None

    events = [
        evt
        for evt in (_quake_to_event(f, latitude, longitude) for f in features)
        if evt is not None
    ]
    _quake_cache.set(key, events)
    return events


def _quake_to_event(feature: dict, latitude: float, longitude: float) -> Optional[HazardEvent]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    depth = coords[2] if len(coords) > 2 else None
    epoch_ms = props.get("time")
    event_id = feature.get("id") or props.get("code") or f"{lat},{lon}"
    return HazardEvent(
        id=str(event_id),
        hazard=HazardType.EARTHQUAKE,
        title=props.get("title") or props.get("place") or "Earthquake",
        latitude=lat,
        longitude=lon,
        occurred_at=(
            datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc) if epoch_ms else None
        ),
        magnitude=props.get("mag"),
        depth_km=round(depth, 1) if isinstance(depth, (int, float)) else None,
        distance_km=round(haversine_km(latitude, longitude, lat, lon), 1),
        url=props.get("url") or f"{USGS_EVENT_PAGE}{event_id}",
        detail=props.get("place"),
    )


async def fetch_global_quakes(min_magnitude: float = 4.5, days: int = 7) -> list[HazardEvent]:
    """
    Significant earthquakes worldwide — the live layer behind the global map.
    Returns an empty list rather than raising: the map degrades to no pins.
    """
    key = f"global|{min_magnitude}|{days}"
    cached = _quake_cache.get(key)
    if cached is not None:
        return cached

    start = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    client = await get_client()
    try:
        resp = await client.get(
            USGS_QUERY,
            params={
                "format": "geojson",
                "minmagnitude": min_magnitude,
                "starttime": start.isoformat(),
                "orderby": "time",
                "limit": 200,
            },
        )
        resp.raise_for_status()
        features = resp.json().get("features") or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"USGS global quake feed failed: {e}")
        return []

    events = [e for e in (_quake_to_event(f, 0.0, 0.0) for f in features) if e is not None]
    for e in events:
        e.distance_km = None  # meaningless without a reference point
    _quake_cache.set(key, events)
    return events


# ─── Volcanoes ────────────────────────────────────────────────────────────────

_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_POINT_RE = re.compile(r"<georss:point>\s*([-\d.]+)\s+([-\d.]+)\s*</georss:point>", re.S)
_DESC_RE = re.compile(r"<description>(.*?)</description>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


async def fetch_volcano_activity() -> Optional[list[VolcanoActivity]]:
    """
    Volcanoes in the current Smithsonian/USGS Weekly Volcanic Activity Report.

    Global and small (about two dozen entries), so it is fetched once and shared
    by every request rather than per-location. Matching to the catalog is done
    on the report's own coordinates, not on its name — report titles carry
    inconsistent diacritics and local spellings, and a name mismatch on a
    volcano hazard is not an acceptable failure mode.

    Returns `None` when the feed could not be read, and an empty list only when
    the report genuinely lists nothing. The distinction is not pedantry: an
    earlier version returned `[]` for both, so one failed fetch was
    indistinguishable from "no volcano on Earth is erupting this week" — and,
    cached for three hours, it told Yogyakarta that Merapi was quiet while
    Merapi was erupting 30 km away. A failure must never be cached as an answer.
    """
    cached = _volcano_activity_cache.get("weekly")
    if cached is not None:
        return cached

    client = await get_client()
    try:
        resp = await client.get(GVP_WEEKLY_RSS, timeout=40.0)
        resp.raise_for_status()
        xml = resp.content.decode("latin-1", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"GVP weekly activity feed failed: {e}")
        return None

    if "<rss" not in xml and "<item>" not in xml:
        # A 200 carrying something that is not the report — a proxy error page,
        # a captive portal. An empty week and a wrong body are not the same fact.
        logger.warning("GVP weekly feed returned a non-RSS body; treating as unavailable")
        return None

    activity: list[VolcanoActivity] = []
    for raw in _ITEM_RE.findall(xml):
        title_match = _TITLE_RE.search(raw)
        point_match = _POINT_RE.search(raw)
        if not title_match or not point_match:
            continue
        title = _unescape(title_match.group(1)).strip()

        # "Etna (Italy) - Report for 30 July-5 August 2026 - New Eruptive Activity"
        name = title.split("(")[0].strip()
        status = title.rsplit(" - ", 1)[-1].strip() if " - " in title else "Activity reported"

        desc_match = _DESC_RE.search(raw)
        summary = ""
        if desc_match:
            summary = _TAG_RE.sub(" ", _unescape(desc_match.group(1)))
            summary = re.sub(r"\s+", " ", summary).strip()

        activity.append(
            VolcanoActivity(
                name=name,
                latitude=float(point_match.group(1)),
                longitude=float(point_match.group(2)),
                headline=title,
                status=status,
                summary=summary[:600],
                url="https://volcano.si.edu/reports_weekly.cfm",
            )
        )

    _volcano_activity_cache.set("weekly", activity)
    logger.info(f"GVP weekly report: {len(activity)} volcanoes with current activity")
    return activity


def _unescape(text: str) -> str:
    return (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&amp;", "&")
    )


# ─── Geocoding ────────────────────────────────────────────────────────────────


async def search_places(name: str, count: int = 8) -> list[PlaceResult]:
    """Forward geocoding, so people can ask about a place by name."""
    query = name.strip()
    if len(query) < 2:
        return []
    key = f"{query.lower()}|{count}"
    cached = _geocode_cache.get(key)
    if cached is not None:
        return cached

    client = await get_client()
    try:
        resp = await client.get(
            GEOCODE_API,
            params={"name": query, "count": count, "language": "en", "format": "json"},
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Geocoding failed for '{query}': {e}")
        return []

    places = [
        PlaceResult(
            name=r.get("name") or query,
            latitude=r["latitude"],
            longitude=r["longitude"],
            country=r.get("country"),
            country_code=r.get("country_code"),
            admin1=r.get("admin1"),
            population=r.get("population"),
            timezone=r.get("timezone"),
        )
        for r in results
        if r.get("latitude") is not None and r.get("longitude") is not None
    ]
    _geocode_cache.set(key, places)
    return places
