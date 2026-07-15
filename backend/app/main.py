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
from app.routers import forecasts, alerts

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)

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
    logger.info(f"   Anthropic API: {'configured' if settings.anthropic_api_key else 'NOT configured (using templates)'}")
    logger.info(f"   Africa's Talking: {'configured' if settings.at_api_key else 'NOT configured (simulated SMS)'}")
    logger.info(f"   Frontend URL: {settings.frontend_url}")
    yield
    # Cleanup
    from app.services.flood_data import _client
    if _client and not _client.is_closed:
        await _client.aclose()
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

# Add rate limiting handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add basic security headers against XSS and other attacks"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(forecasts.router, prefix="/api", tags=["forecasts"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])

# Serve uploaded report photos
_uploads_dir = Path(__file__).parent.parent / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/")
@limiter.limit("10/minute")
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
            "send_alert": "/api/alerts/send",
            "reports": "/api/reports",
        },
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}
