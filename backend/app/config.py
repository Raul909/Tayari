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
    at_username: str = "sandbox"
    at_api_key: Optional[str] = os.getenv("AT_API_KEY")

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
