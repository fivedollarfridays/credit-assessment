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
    database_url: str = "sqlite+aiosqlite:///./credit.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1

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
