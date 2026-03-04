"""Configuration from environment variables using pydantic-settings."""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "change-me-in-production"
_DEFAULT_PII_PEPPER = "default-pii-pepper"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./credit.db"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1
    redis_url: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    pii_pepper: str = _DEFAULT_PII_PEPPER

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        """Reject insecure defaults in production."""
        if self.is_production:
            if self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET must be set to a secure value in production"
                )
            if self.pii_pepper == _DEFAULT_PII_PEPPER:
                raise ValueError(
                    "PII_PEPPER must be set to a secure value in production"
                )
        return self


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
