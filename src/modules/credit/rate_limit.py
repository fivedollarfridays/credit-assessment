"""Rate limiting configuration with per-customer tiers."""

from __future__ import annotations

import enum
import logging

import redis
from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
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


def register_rate_limit_handler(app: FastAPI) -> None:
    """Register the rate-limit exceeded exception handler on the app."""

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )


async def check_redis_health(redis_url: str) -> bool:
    """Check Redis connectivity by attempting a PING."""
    r = None
    try:
        r = redis.asyncio.from_url(redis_url)
        await r.ping()
        return True
    except Exception:
        return False
    finally:
        if r is not None:
            await r.aclose()
