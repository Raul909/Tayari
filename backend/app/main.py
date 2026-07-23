"""
Tayari — AI Flood Early Warning & Early Action System
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import forecasts, alerts, chat, user

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
    logger.info("🌊 Tayari starting up...")
    logger.info(f"   Environment: {settings.environment}")
    from app.services.alerts import twilio_configured
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
    await close_db()
    logger.info("🌊 Tayari shutting down.")


app = FastAPI(
    title="Tayari API",
    description=(
        "AI Flood Early Warning & Early Action System for the IGAD region. "
        "Predicts river flooding 1-7 days ahead, generates multilingual "
        "impact-based advisories, and delivers alerts via SMS."
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
    if request.method == "GET" and response.status_code == 200:
        # Cache GET endpoints for 60 seconds on the client / CDN edge
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

# Register routers
app.include_router(forecasts.router, prefix="/api", tags=["forecasts"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
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
    return {
        "name": "Tayari API",
        "version": settings.app_version,
        "status": "running",
        "description": "AI Flood Early Warning & Early Action System",
        "docs": "/docs",
        "basins_monitored": 3,
        "endpoints": {
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
    """
    import os
    return {
        "status": "healthy",
        "version": settings.app_version,
        "commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:12],
    }
