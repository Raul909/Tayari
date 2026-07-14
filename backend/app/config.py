"""
Tayari configuration — loads settings from environment variables.
"""

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
    anthropic_api_key: Optional[str] = None
    at_username: str = "sandbox"
    at_api_key: Optional[str] = None

    # Database
    database_url: str = "sqlite+aiosqlite:///./tayari.db"

    # Open-Meteo (no key needed)
    flood_api_base: str = "https://flood-api.open-meteo.com/v1/flood"
    weather_api_base: str = "https://api.open-meteo.com/v1/forecast"

    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"

    # Forecast settings
    forecast_days: int = 7
    past_days: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
