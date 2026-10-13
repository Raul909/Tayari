"""
Tayari — AI Multi-Hazard Early Warning & Early Action System
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import forecasts, alerts, chat, user, feedback, hazards

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Configure rate limiting
from app.limiter import limiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🌍 Tayari starting up...")
    logger.info(f"   Environment: {settings.environment}")
    from app.services.alerts import twilio_configured
    from app.hazards.registry import HAZARD_META
    from app.hazards.volcano_catalog import _load as load_volcanoes
    logger.info(f"   Hazards: {len(HAZARD_META)} · volcano catalog: {len(load_volcanoes())} entries")
    logger.info(f"   Groq API: {'configured' if settings.groq_api_key else 'NOT configured (using templates)'}")
    logger.info(f"   Twilio SMS: {'configured' if twilio_configured() else 'NOT configured (simulated SMS)'}")
    logger.info(f"   Frontend URL: {settings.frontend_url}")

    # Create database tables and import any legacy JSON reports.
    from app.db import init_db, close_db
    from app.services.report_migration import migrate_legacy_reports
    await init_db()
    await migrate_legacy_reports()

    # Warm the location-independent feeds in the background. A Render cold
    # start is exactly when the first visitor is waiting, and these two global
    # downloads would otherwise land on that visitor's request.
    import asyncio
    from app.hazards.feeds import warm_global_feeds
    warm_task = asyncio.create_task(warm_global_feeds())

    yield

    warm_task.cancel()

    # Cleanup
    from app.services.flood_data import _client
    if _client and not _client.is_closed:
        await _client.aclose()
    from app.hazards.feeds import close_client as close_hazard_client
    await close_hazard_client()
    await close_db()
    logger.info("🌍 Tayari shutting down.")


app = FastAPI(
    title="Tayari API",
    description=(
        "AI Multi-Hazard Early Warning & Early Action System. "
        "Scores flood, earthquake, tsunami, volcanic, storm, heat, wildfire, "
        "drought and landslide risk for any location on Earth, generates "
        "multilingual impact-based advisories, and delivers alerts via SMS."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Add rate limiting handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Concurrency limiter — cap active requests, with a per-request ceiling.
# 45s rather than 30: a cold hazard profile makes seven upstream calls, and on
# a Render free-tier cold start those were being cut off mid-flight.
_semaphore = asyncio.Semaphore(100)
REQUEST_TIMEOUT_SECONDS = 45

class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """
    Caps concurrent requests and bounds how long any one may run.

    It deliberately does NOT flatten application errors into "Server busy".
    It used to: every unhandled exception — a bug, a missing key, a paused
    database — came back as a 503 saying the server was busy, logged as a
    one-line str(e) with no traceback. The server was not busy, and the one
    message that would have identified the problem was the one being thrown
    away; an afternoon of alert failures read as capacity trouble.

    Capacity problems get 504/503 because that is what they are. Everything
    else is re-raised so FastAPI returns a real 500 and the traceback reaches
    the log.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async with _semaphore:
                    return await call_next(request)
        except asyncio.TimeoutError:
            logger.warning(
                f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s: "
                f"{request.method} {request.url.path}"
            )
            return JSONResponse({"detail": "Request timeout"}, status_code=504)
        except Exception:
            logger.exception(
                f"Unhandled error handling {request.method} {request.url.path}"
            )
            raise

app.add_middleware(ConcurrencyLimitMiddleware)

# ─── Caching policy ──────────────────────────────────────────────────────────
#
# The API sits behind Tayari's edge gateway (frontend/functions/api), which caches
# whatever this table marks public and nothing else. That makes this table the
# single place that decides how fresh each answer must be, so it is written per
# route rather than as one blanket header:
#
#   max-age                 how long a browser or the phone app may reuse it
#   s-maxage                how long the edge serves it without asking us
#   stale-while-revalidate  how much longer the edge may serve it while it
#                           fetches a fresh copy in the background
#   stale-if-error          how long the edge may keep serving it when this
#                           server is asleep, overloaded or down
#
# The last one is what lets Tayari stay up on a free instance that sleeps: the
# edge keeps answering for places people have recently checked, and every client
# shows the data's own timestamp, so a stale answer is never mistaken for a new one.
#
# Anything not listed — accounts, saved preferences, alert history with phone
# numbers in it — is `private, no-store` and never cached anywhere shared.

import re

_CACHE_POLICY = [
    # Live: earthquakes feed tsunami warnings, which count in minutes.
    (re.compile(r"^/api/hazards$"), "public, max-age=60, s-maxage=60, stale-while-revalidate=60, stale-if-error=86400"),
    (re.compile(r"^/api/hazards/events/live$"), "public, max-age=60, s-maxage=120, stale-while-revalidate=120, stale-if-error=86400"),
    # Generated text, already cached for hours on the server.
    (re.compile(r"^/api/hazards/[a-z_]+/advisory$"), "public, max-age=300, s-maxage=1800, stale-while-revalidate=1800, stale-if-error=86400"),
    (re.compile(r"^/api/advisory/[\w-]+$"), "public, max-age=300, s-maxage=1800, stale-while-revalidate=1800, stale-if-error=86400"),
    # Hydrology moves hourly.
    (re.compile(r"^/api/forecasts/[\w-]+(/history)?$"), "public, max-age=60, s-maxage=600, stale-while-revalidate=600, stale-if-error=86400"),
    (re.compile(r"^/api/basins$"), "public, max-age=300, s-maxage=3600, stale-while-revalidate=3600, stale-if-error=604800"),
    # Reference data: places and the hazard catalogue barely change.
    (re.compile(r"^/api/hazards/types$"), "public, max-age=3600, s-maxage=86400, stale-while-revalidate=86400, stale-if-error=604800"),
    (re.compile(r"^/api/places/search$"), "public, max-age=86400, s-maxage=604800, stale-if-error=604800"),
    # Community reports: shared, but people expect a new one to show up quickly.
    # The edge also drops this entry whenever a report is posted through it.
    (re.compile(r"^/api/reports$"), "public, max-age=0, s-maxage=15, stale-while-revalidate=15, stale-if-error=3600"),
    # Uploaded photos and voice notes get a new name for every file.
    (re.compile(r"^/(uploads|static/audio)/"), "public, max-age=604800, s-maxage=2592000, immutable"),
]


def cache_policy(path: str) -> str:
    for pattern, policy in _CACHE_POLICY:
        if pattern.match(path):
            return policy
    return "private, no-store"


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Security headers on every response, and the caching policy on GETs."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.method == "GET" and response.status_code == 200:
        response.headers["Cache-Control"] = cache_policy(request.url.path)
    elif "cache-control" not in response.headers:
        # Errors are never cached: a 503 during a cold start must not be served
        # back to the next hundred visitors as if it were the answer.
        response.headers["Cache-Control"] = "no-store"
    return response

# CORS — allow frontend (dev + production)
_cors_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    # Cloudflare Pages production domain
    "https://tayari.pages.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://(.*\.)?tayari\.pages\.dev",  # main and preview deploys
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers. Hazards first: it is the layer the app now leads with, and
# its /api/hazards/{hazard}/advisory path must be matched before any broader
# pattern a later router might introduce.
app.include_router(hazards.router, prefix="/api", tags=["hazards"])
app.include_router(forecasts.router, prefix="/api", tags=["forecasts"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(user.router)
# Serve uploaded report photos
_uploads_dir = Path(__file__).parent.parent / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# Serve generated voice notes
_audio_dir = Path(__file__).parent.parent / "static/audio"
_audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=str(_audio_dir)), name="audio")


@app.get("/api/info")
async def root(request: Request):
    """Health check and API info."""
    from app.hazards.registry import HAZARD_META

    return {
        "name": "Tayari API",
        "version": settings.app_version,
        "status": "running",
        "description": "AI Multi-Hazard Early Warning & Early Action System",
        "docs": "/docs",
        "hazards_assessed": len(HAZARD_META),
        "basins_calibrated": 8,
        "endpoints": {
            "hazard_profile": "/api/hazards?lat={lat}&lon={lon}",
            "hazard_types": "/api/hazards/types",
            "hazard_advisory": "/api/hazards/{hazard}/advisory?lat={lat}&lon={lon}",
            "live_events": "/api/hazards/events/live",
            "place_search": "/api/places/search?q={name}",
            "basins": "/api/basins",
            "forecast": "/api/forecasts/{basin_id}",
            "advisory": "/api/advisory/{basin_id}",
            "chat": "/api/chat/{basin_id}",
            "user": "/api/user/me",
            "send_alert": "/api/alerts/send",
            "reports": "/api/reports",
        },
    }



@app.get("/health")
async def health():
    """
    Health check. Includes the deployed git commit (Render injects
    RENDER_GIT_COMMIT) so "which code is actually live?" is a one-request
    question instead of a guessing game.

    Deliberately does NOT touch the database — this is Render's liveness probe,
    and a transient DB hiccup must never make Render recycle a healthy instance.
    Use /health/db for a database-touching keep-alive.
    """
    import os
    return {
        "status": "healthy",
        "version": settings.app_version,
        "commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:12],
    }


@app.get("/api/health/client")
async def health_client(request: Request):
    """
    What this server can see of the caller: the address the rate limiter keys
    on, and the forwarding headers it was derived from. Under /api so it can be
    called through the edge gateway, which is the chain worth checking: that
    Cloudflare edge → Render still delivers the real client address — if `client_ip` ever shows a Cloudflare or private address, every
    visitor is sharing one rate-limit bucket again.
    """
    from app.net import client_ip

    return {
        "client_ip": client_ip(request),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "via_edge": request.headers.get("x-tayari-edge") is not None,
    }


@app.get("/health/db")
async def health_db():
    """
    Database keep-alive. Runs a trivial `SELECT 1` so a serverless/managed
    Postgres (Supabase) never pauses from inactivity — the Cloudflare pinger
    hits this on its cron. Kept separate from /health so a DB problem can't
    fail Render's liveness probe. Returns 503 (not 500) if the DB is unreachable
    so the pinger logs it without implying the app itself is down.
    """
    from sqlalchemy import text
    from app.db import SessionLocal
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as e:
        logger.warning(f"DB keep-alive failed: {e}")
        return JSONResponse(
            {"status": "error", "database": "unreachable", "detail": str(e)[:150]},
            status_code=503,
        )


@app.get("/health/feeds")
async def health_feeds():
    """
    Reachability of every upstream the hazard engine depends on.

    Added after a production incident worth recording: the Smithsonian volcano
    feed was unreachable from Render for hours while the app reported nothing
    wrong, because a failed fetch and an empty week looked identical downstream.
    A warning system that cannot say which of its own senses have gone dark is
    one bad afternoon away from confidently reporting calm.

    Each feed is probed independently with a short timeout. Slow, so it is not
    the liveness probe — /health stays cheap and DB-free for Render.
    """
    import asyncio
    import time

    import httpx

    from app.hazards import feeds as hz

    probes = {
        "weather (Open-Meteo forecast)": (
            hz.FORECAST_API,
            {"latitude": 0, "longitude": 0, "daily": "temperature_2m_max", "forecast_days": 1},
        ),
        "archive (Open-Meteo reanalysis)": (
            hz.ARCHIVE_API,
            {
                "latitude": 0,
                "longitude": 0,
                "start_date": "2025-01-01",
                "end_date": "2025-01-02",
                "daily": "precipitation_sum",
            },
        ),
        "elevation (Copernicus DEM)": (
            settings.elevation_api_base,
            {"latitude": 0, "longitude": 0},
        ),
        "discharge (GloFAS)": (
            settings.flood_api_base,
            {"latitude": 25.6, "longitude": 85.1, "daily": "river_discharge", "forecast_days": 1},
        ),
        "geocoding (Open-Meteo)": (hz.GEOCODE_API, {"name": "Nairobi", "count": 1, "format": "json"}),
        "earthquakes (USGS)": (
            hz.USGS_COUNT,
            {"format": "geojson", "minmagnitude": 6, "starttime": "2026-01-01"},
        ),
        "volcanoes (Smithsonian GVP)": (
            hz.GVP_WFS,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeName": hz.GVP_ERUPTIONS_LAYER,
                "outputFormat": "application/json",
                "cql_filter": "ContinuingEruption = true",
                "count": 1,
            },
        ),
    }

    async def probe(name: str, url: str, params: dict) -> dict:
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params or None)
            return {
                "feed": name,
                "ok": resp.status_code == 200,
                "status": resp.status_code,
                "ms": round((time.monotonic() - started) * 1000),
                "bytes": len(resp.content),
                "content_type": resp.headers.get("content-type", "")[:40],
            }
        except Exception as e:  # noqa: BLE001
            return {
                "feed": name,
                "ok": False,
                "ms": round((time.monotonic() - started) * 1000),
                "error": f"{type(e).__name__}: {str(e)[:160]}",
            }

    results = await asyncio.gather(
        *(probe(name, url, params) for name, (url, params) in probes.items())
    )
    healthy = all(r["ok"] for r in results)
    return JSONResponse(
        {"status": "ok" if healthy else "degraded", "feeds": results},
        status_code=200 if healthy else 503,
    )
