"""Configuration from environment variables."""

from __future__ import annotations

import os


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins from environment."""
    raw = os.environ.get("CORS_ORIGINS", "")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000"]


def get_api_key() -> str | None:
    """Get API key from environment. None means auth is disabled (dev mode)."""
    return os.environ.get("API_KEY")


def get_environment() -> str:
    """Get deployment environment. Defaults to 'development'."""
    return os.environ.get("ENVIRONMENT", "development")


def is_production() -> bool:
    """Check if running in production."""
    return get_environment() == "production"
