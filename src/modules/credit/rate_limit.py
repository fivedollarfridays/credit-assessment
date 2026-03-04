"""Rate limiting configuration with per-customer tiers."""

from __future__ import annotations

import enum
import logging

import time

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SubscriptionTier(str, enum.Enum):
    """Customer subscription tiers (billing + rate limiting)."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Backwards-compatible alias
RateTier = SubscriptionTier

TIER_LIMITS: dict[SubscriptionTier, str | None] = {
    SubscriptionTier.FREE: "10/minute",
    SubscriptionTier.STARTER: "60/minute",
    SubscriptionTier.PRO: "300/minute",
    SubscriptionTier.ENTERPRISE: None,  # unlimited
}


def resolve_tier(tier: SubscriptionTier | None) -> str | None:
    """Return the rate limit string for a given tier. Defaults to FREE."""
    if tier is None:
        tier = SubscriptionTier.FREE
    return TIER_LIMITS[tier]


def create_limiter(redis_url: str | None = None) -> Limiter:
    """Create a Limiter, optionally backed by Redis with in-memory fallback."""
    if redis_url is not None:
        try:
            return Limiter(key_func=get_remote_address, storage_uri=redis_url)
        except Exception:
            logger.warning("Redis unavailable, falling back to in-memory rate limiting")
    return Limiter(key_func=get_remote_address)


def _get_redis_url() -> str | None:
    """Get Redis URL from settings at import time."""
    from .config import settings

    return settings.redis_url


limiter = create_limiter(redis_url=_get_redis_url())


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """Add rate limit headers to responses on rate-limited endpoints."""

    def __init__(self, app, *, limit: str = "10/minute") -> None:
        super().__init__(app)
        self._limit = limit
        self._parse_limit(limit)

    def _parse_limit(self, limit: str) -> None:
        parts = limit.split("/")
        self._max_requests = int(parts[0])

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path in {"/assess", "/v1/assess"}:
            reset_at = int(time.time()) + 60
            response.headers["X-RateLimit-Limit"] = str(self._max_requests)
            response.headers["X-RateLimit-Remaining"] = str(self._max_requests - 1)
            response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response


def register_rate_limit_handler(app: FastAPI) -> None:
    """Register the rate-limit exceeded exception handler on the app."""

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )
