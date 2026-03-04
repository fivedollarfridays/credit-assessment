"""Tests for API security features — T5.2 TDD."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD


@pytest.fixture
def client():
    from modules.credit.router import app

    return TestClient(app)


class TestApiKeyAuth:
    """Test API key authentication (T5.2)."""

    def test_no_key_required_when_env_unset(self, client):
        """When API_KEY env is not set, requests pass through."""
        response = client.post("/assess", json=VALID_ASSESS_PAYLOAD)
        assert response.status_code == 200

    def test_rejects_wrong_api_key(self, client):
        """When API_KEY is set, wrong key returns 403."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            response = client.post(
                "/assess",
                json=VALID_ASSESS_PAYLOAD,
                headers={"X-API-Key": "wrong-key"},
            )
            assert response.status_code == 403

    def test_rejects_missing_api_key(self, client):
        """When API_KEY is set, missing key returns 403."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            response = client.post("/assess", json=VALID_ASSESS_PAYLOAD)
            assert response.status_code == 403

    def test_accepts_correct_api_key(self, client):
        """When API_KEY is set, correct key passes."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            response = client.post(
                "/assess",
                json=VALID_ASSESS_PAYLOAD,
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
