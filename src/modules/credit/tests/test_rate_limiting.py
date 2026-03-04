"""Tests for per-customer rate limiting — T4.3 TDD."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings(jwt_secret="test-secret", api_key=None)

_VALID_PAYLOAD = {
    "current_score": 740,
    "score_band": "good",
    "overall_utilization": 20.0,
    "account_summary": {"total_accounts": 8, "open_accounts": 6},
    "payment_history_pct": 98.0,
    "average_account_age_months": 72,
}


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


class TestRateTierEnum:
    """Test RateTier enum values."""

    def test_has_free_tier(self):
        from modules.credit.rate_limit import RateTier

        assert RateTier.FREE.value == "free"

    def test_has_starter_tier(self):
        from modules.credit.rate_limit import RateTier

        assert RateTier.STARTER.value == "starter"

    def test_has_pro_tier(self):
        from modules.credit.rate_limit import RateTier

        assert RateTier.PRO.value == "pro"

    def test_has_enterprise_tier(self):
        from modules.credit.rate_limit import RateTier

        assert RateTier.ENTERPRISE.value == "enterprise"

    def test_has_exactly_four_tiers(self):
        from modules.credit.rate_limit import RateTier

        assert len(RateTier) == 4


class TestTierLimits:
    """Test rate limit values per tier."""

    def test_free_tier_limit(self):
        from modules.credit.rate_limit import TIER_LIMITS, RateTier

        assert TIER_LIMITS[RateTier.FREE] == "10/minute"

    def test_starter_tier_limit(self):
        from modules.credit.rate_limit import TIER_LIMITS, RateTier

        assert TIER_LIMITS[RateTier.STARTER] == "60/minute"

    def test_pro_tier_limit(self):
        from modules.credit.rate_limit import TIER_LIMITS, RateTier

        assert TIER_LIMITS[RateTier.PRO] == "300/minute"

    def test_enterprise_tier_is_unlimited(self):
        from modules.credit.rate_limit import TIER_LIMITS, RateTier

        assert TIER_LIMITS[RateTier.ENTERPRISE] is None


class TestRateLimitHeaders:
    """Test rate limit headers in responses."""

    def test_response_includes_rate_limit_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert "X-RateLimit-Limit" in resp.headers

    def test_response_includes_remaining_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert "X-RateLimit-Remaining" in resp.headers

    def test_response_includes_reset_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert "X-RateLimit-Reset" in resp.headers


class TestRateLimitExceeded:
    """Test 429 response behavior."""

    def test_429_includes_retry_after(self):
        import asyncio
        from unittest.mock import MagicMock

        from slowapi.errors import RateLimitExceeded
        from starlette.requests import Request

        from modules.credit.router import app

        scope = {"type": "http", "headers": []}
        request = Request(scope)
        exc = MagicMock(spec=RateLimitExceeded)

        handler = app.exception_handlers[RateLimitExceeded]
        response = asyncio.run(handler(request, exc))
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestResolveCustomerTier:
    """Test tier resolution from user context."""

    def test_default_tier_is_free(self):
        from modules.credit.rate_limit import resolve_tier

        assert resolve_tier(None) == "10/minute"

    def test_resolve_starter_tier(self):
        from modules.credit.rate_limit import RateTier, resolve_tier

        assert resolve_tier(RateTier.STARTER) == "60/minute"

    def test_resolve_enterprise_returns_none(self):
        from modules.credit.rate_limit import RateTier, resolve_tier

        assert resolve_tier(RateTier.ENTERPRISE) is None


class TestRedisBackend:
    """Test Redis-backed rate limiting with fallback."""

    def test_redis_url_in_settings(self):
        s = Settings(redis_url="redis://localhost:6379")
        assert s.redis_url == "redis://localhost:6379"

    def test_redis_url_defaults_to_none(self):
        s = Settings()
        assert s.redis_url is None

    def test_graceful_fallback_when_redis_unavailable(self):
        """Rate limiting should still work with in-memory fallback."""
        from unittest.mock import patch as mock_patch

        from slowapi import Limiter
        from slowapi.util import get_remote_address

        from modules.credit.rate_limit import create_limiter

        with mock_patch(
            "modules.credit.rate_limit.Limiter",
            side_effect=[Exception("connection refused"), Limiter(key_func=get_remote_address)],
        ):
            lim = create_limiter(redis_url="redis://nonexistent:6379")
            assert lim is not None

    def test_successful_redis_connection(self):
        """When Redis connects, use the Redis-backed limiter."""
        from modules.credit.rate_limit import create_limiter

        lim = create_limiter(redis_url="redis://localhost:6379")
        assert lim is not None
