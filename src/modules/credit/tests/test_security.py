"""Tests for API security features — T5.2 TDD."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings

_VALID_PAYLOAD = {
    "current_score": 740,
    "score_band": "good",
    "overall_utilization": 20.0,
    "account_summary": {"total_accounts": 8, "open_accounts": 6},
    "payment_history_pct": 98.0,
    "average_account_age_months": 72,
}


@pytest.fixture
def client():
    from modules.credit.router import app

    return TestClient(app)


class TestApiKeyAuth:
    """Test API key authentication (T5.2)."""

    def test_no_key_required_when_env_unset(self, client):
        """When API_KEY env is not set, requests pass through."""
        response = client.post("/assess", json=_VALID_PAYLOAD)
        assert response.status_code == 200

    def test_rejects_wrong_api_key(self, client):
        """When API_KEY is set, wrong key returns 403."""
        mock = Settings(api_key="secret-key")
        with patch("modules.credit.router.settings", mock):
            response = client.post(
                "/assess",
                json=_VALID_PAYLOAD,
                headers={"X-API-Key": "wrong-key"},
            )
            assert response.status_code == 403

    def test_rejects_missing_api_key(self, client):
        """When API_KEY is set, missing key returns 403."""
        mock = Settings(api_key="secret-key")
        with patch("modules.credit.router.settings", mock):
            response = client.post("/assess", json=_VALID_PAYLOAD)
            assert response.status_code == 403

    def test_accepts_correct_api_key(self, client):
        """When API_KEY is set, correct key passes."""
        mock = Settings(api_key="secret-key")
        with patch("modules.credit.router.settings", mock):
            response = client.post(
                "/assess",
                json=_VALID_PAYLOAD,
                headers={"X-API-Key": "secret-key"},
            )
            assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting (T5.2)."""

    def test_rate_limit_handler_returns_429(self, client):
        """Exercise the rate_limit_handler exception handler."""
        import asyncio

        from slowapi.errors import RateLimitExceeded
        from starlette.requests import Request

        from modules.credit.router import app

        scope = {"type": "http", "headers": []}
        request = Request(scope)
        exc = MagicMock(spec=RateLimitExceeded)

        handler = app.exception_handlers[RateLimitExceeded]
        response = asyncio.run(handler(request, exc))
        assert response.status_code == 429
        assert response.body == b'{"detail":"Rate limit exceeded"}'
