"""Tests for API security features — T5.2 TDD."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


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
        with patch("modules.credit.router.get_api_key", return_value="secret-key"):
            response = client.post(
                "/assess",
                json=_VALID_PAYLOAD,
                headers={"X-API-Key": "wrong-key"},
            )
            assert response.status_code == 403

    def test_rejects_missing_api_key(self, client):
        """When API_KEY is set, missing key returns 403."""
        with patch("modules.credit.router.get_api_key", return_value="secret-key"):
            response = client.post("/assess", json=_VALID_PAYLOAD)
            assert response.status_code == 403

    def test_accepts_correct_api_key(self, client):
        """When API_KEY is set, correct key passes."""
        with patch("modules.credit.router.get_api_key", return_value="secret-key"):
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
        from modules.credit.router import rate_limit_handler
        from starlette.requests import Request

        import asyncio
        from unittest.mock import MagicMock

        scope = {"type": "http", "headers": []}
        request = Request(scope)
        exc = MagicMock()
        response = asyncio.get_event_loop().run_until_complete(
            rate_limit_handler(request, exc)
        )
        assert response.status_code == 429
        assert response.body == b'{"detail":"Rate limit exceeded"}'


class TestCorsOrigins:
    """Test CORS configuration (T5.2)."""

    def test_cors_origins_from_env(self):
        """CORS_ORIGINS env var is parsed into list."""
        with patch.dict(
            "os.environ",
            {"CORS_ORIGINS": "https://app.example.com, https://admin.example.com"},
        ):
            from modules.credit.config import get_cors_origins

            origins = get_cors_origins()
            assert origins == [
                "https://app.example.com",
                "https://admin.example.com",
            ]

    def test_cors_default_localhost(self):
        """Default CORS origin is localhost:3000."""
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import get_cors_origins

            origins = get_cors_origins()
            assert origins == ["http://localhost:3000"]


class TestConfigFunctions:
    """Test config.py utility functions (T5.2)."""

    def test_get_api_key_returns_none_when_unset(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import get_api_key

            assert get_api_key() is None

    def test_get_api_key_returns_value(self):
        with patch.dict("os.environ", {"API_KEY": "my-secret"}):
            from modules.credit.config import get_api_key

            assert get_api_key() == "my-secret"

    def test_get_environment_defaults_to_development(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import get_environment

            assert get_environment() == "development"

    def test_get_environment_from_env(self):
        with patch.dict("os.environ", {"ENVIRONMENT": "staging"}):
            from modules.credit.config import get_environment

            assert get_environment() == "staging"

    def test_is_production_true(self):
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            from modules.credit.config import is_production

            assert is_production() is True

    def test_is_production_false(self):
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            from modules.credit.config import is_production

            assert is_production() is False
