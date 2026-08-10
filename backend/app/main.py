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

    yield

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

# Concurrency limiter — cap active requests at 100 with a 30s timeout per request
_semaphore = asyncio.Semaphore(100)

class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            async with asyncio.timeout(30):
                async with _semaphore:
                    return await call_next(request)
        except asyncio.TimeoutError:
            return JSONResponse({"detail": "Request timeout"}, status_code=504)
        except Exception as e:
            logger.error(f"Middleware execution error: {e}")
            return JSONResponse({"detail": "Server busy"}, status_code=503)

app.add_middleware(ConcurrencyLimitMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add basic security headers against XSS and enable client caching for GET endpoints."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if (
        request.method == "GET"
        and response.status_code == 200
        and not request.url.path.startswith("/health")
    ):
        # Cache GET endpoints for 60 seconds on the client / CDN edge. Health
        # checks are exempt: /health is Render's liveness probe and /health/db
        # must actually reach the database on every hit (see below), so neither
        # may be served from a cache.
        response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=600"
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
        "volcanoes (Smithsonian GVP)": (hz.GVP_WEEKLY_SOURCES[0], {}),
        "volcanoes direct (Smithsonian GVP)": (hz.GVP_WEEKLY_SOURCES[1], {}),
        "volcano catalog (GVP GeoServer)": (
            "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows",
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeName": "GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions",
                "outputFormat": "application/json",
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
