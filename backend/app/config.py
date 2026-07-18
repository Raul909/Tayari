"""
Tayari configuration — loads settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # App
    app_name: str = "Tayari"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "info"

    # API Keys
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    groq_model: str = "llama-3.3-70b-versatile"
    # Accept either name — HF's own docs use HF_TOKEN, while older code here
    # used HF_API_TOKEN. Reading both means the key is picked up regardless of
    # which one is set in the environment (e.g. the Render dashboard).
    hf_api_token: Optional[str] = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")

    # SMS delivery — Twilio. When these three are set, alerts go out as real SMS
    # via the Twilio REST API; otherwise sends are simulated (logged only) so
    # local demos never fail. On a Twilio *trial* account, delivery is limited to
    # numbers verified in the console.
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None

    # Database & Auth
    database_url: str = "sqlite+aiosqlite:///./tayari.db"
    supabase_jwt_secret: Optional[str] = None

    # External APIs (routed through Cloudflare Worker proxy to avoid Render rate limits)
    flood_api_base: str = "https://tayari-pinger.indialayers-dev.workers.dev/flood"
    weather_api_base: str = "https://tayari-pinger.indialayers-dev.workers.dev/weather"

    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"

    # Forecast settings
    forecast_days: int = 7
    past_days: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
