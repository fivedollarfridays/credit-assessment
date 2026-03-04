"""Configuration from environment variables using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


# Module-level singleton — parsed once, reused everywhere.
settings = Settings()


# --- Backward-compatible standalone functions (delegate to singleton) ---


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins."""
    return settings.cors_origins


def get_api_key() -> str | None:
    """Get API key. None means auth is disabled (dev mode)."""
    return settings.api_key


def get_environment() -> str:
    """Get deployment environment."""
    return settings.environment


def is_production() -> bool:
    """Check if running in production."""
    return settings.is_production
