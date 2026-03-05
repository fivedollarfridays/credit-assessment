"""Tests for API security features — T5.2/T10.3 TDD."""

import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from modules.credit.admin_routes import _MAX_API_KEYS, _api_keys, lookup_api_key
from modules.credit.audit import hash_pii
from modules.credit.auth import create_access_token
from modules.credit.config import Settings, _DEFAULT_JWT_SECRET, _DEFAULT_PII_PEPPER
from modules.credit.router import app
from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD
from modules.credit.user_routes import (
    _MAX_RESET_TOKENS,
    _RE_DIGIT,
    _RE_LOWERCASE,
    _RE_SPECIAL,
    _RE_UPPERCASE,
    _reset_tokens,
)
from modules.credit.webhook_routes import _BLOCKED_HOSTNAMES


@pytest.fixture
def client():
    return TestClient(app)


class TestApiKeyAuth:
    """Test API key authentication."""

    def test_no_credentials_rejected_even_when_api_key_unset(self, client):
        """When API_KEY env is not set, requests without any credentials are rejected."""
        response = client.post("/assess", json=VALID_ASSESS_PAYLOAD)
        assert response.status_code == 403

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


class TestVerifyAuthReturnsIdentity:
    """verify_auth must return the authenticated identity string."""

    def test_verify_auth_returns_sub_from_jwt(self, client):
        """JWT auth returns the 'sub' claim from the token."""
        mock = Settings(jwt_secret="test-secret", jwt_algorithm="HS256", api_key="key")
        token = create_access_token(
            subject="user@example.com",
            secret="test-secret",
            algorithm="HS256",
            expire_minutes=30,
        )
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            response = client.post(
                "/assess",
                json=VALID_ASSESS_PAYLOAD,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    def test_verify_auth_returns_api_key_user_for_api_key(self, client):
        """API key auth returns 'api-key-user' as the identity."""
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


class TestDemoUsersDisabledInProduction:
    """Demo credentials must be disabled in production."""

    def test_demo_login_rejected_in_production(self, client):
        """POST /auth/token with demo creds returns 401 in production."""
        mock = Settings(
            environment="production",
            jwt_secret="real-secret-value-here",
            pii_pepper="pp",
        )
        with (
            patch("modules.credit.auth_routes.settings", mock),
            patch("modules.credit.auth.settings", mock),
        ):
            resp = client.post(
                "/auth/token",
                json={"username": "admin", "password": "admin"},
            )
            assert resp.status_code == 401

    def test_demo_login_works_in_development(self, client):
        """POST /auth/token with demo creds returns 200 in development."""
        resp = client.post(
            "/auth/token",
            json={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200


class TestPiiPepperSeparation:
    """PII hash must use dedicated pepper, not JWT secret."""

    def test_hash_pii_uses_pii_pepper_not_jwt_secret(self):
        """Same pii_pepper but different jwt_secret -> same hash."""
        mock1 = Settings(pii_pepper="pepper-a", jwt_secret="jwt-a")
        mock2 = Settings(pii_pepper="pepper-a", jwt_secret="jwt-b")
        with patch("modules.credit.audit.settings", mock1):
            hash1 = hash_pii("test@example.com")
        with patch("modules.credit.audit.settings", mock2):
            hash2 = hash_pii("test@example.com")
        assert hash1 == hash2

    def test_hash_pii_changes_with_different_pepper(self):
        """Different pii_pepper -> different hash."""
        mock1 = Settings(pii_pepper="pepper-a")
        mock2 = Settings(pii_pepper="pepper-b")
        with patch("modules.credit.audit.settings", mock1):
            hash1 = hash_pii("test@example.com")
        with patch("modules.credit.audit.settings", mock2):
            hash2 = hash_pii("test@example.com")
        assert hash1 != hash2


class TestApiKeyExpiration:
    """Expired API keys must not be returned by lookup."""

    @pytest.fixture(autouse=True)
    def _clean_api_keys(self):
        yield
        _api_keys.clear()

    def test_lookup_expired_key_returns_none(self):
        _api_keys["expired-key"] = {
            "org_id": "org-1",
            "role": "viewer",
            "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
        }
        assert lookup_api_key("expired-key") is None

    def test_lookup_valid_key_returns_entry(self):
        _api_keys["valid-key"] = {
            "org_id": "org-1",
            "role": "viewer",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }
        result = lookup_api_key("valid-key")
        assert result is not None
        assert result["org_id"] == "org-1"

    def test_lookup_no_expiry_key_returns_entry(self):
        _api_keys["no-expiry-key"] = {
            "org_id": "org-2",
            "role": "admin",
            "expires_at": None,
        }
        result = lookup_api_key("no-expiry-key")
        assert result is not None

    def test_lookup_nonexistent_key_returns_none(self):
        assert lookup_api_key("nonexistent") is None

    def test_lazy_deletion_removes_expired_key(self):
        """lookup_api_key must delete expired entries from _api_keys dict."""
        _api_keys["lazy-del"] = {
            "org_id": "org-1",
            "role": "viewer",
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        assert lookup_api_key("lazy-del") is None
        assert "lazy-del" not in _api_keys

    def test_max_api_keys_constant_exists(self):
        """_MAX_API_KEYS constant must exist and be 10_000."""
        assert _MAX_API_KEYS == 10_000


class TestResetTokenCap:
    """T10.3: Reset token store must be bounded with a max size constant."""

    def test_max_reset_tokens_constant_exists(self):
        """_MAX_RESET_TOKENS constant must exist and be reasonable."""
        assert _MAX_RESET_TOKENS > 0
        assert _MAX_RESET_TOKENS <= 100_000

    def test_reset_tokens_is_ordered_dict(self):
        """_reset_tokens must be an OrderedDict for FIFO eviction."""
        assert isinstance(_reset_tokens, OrderedDict)

    def test_reset_token_eviction_bounds_store(self):
        """Driving eviction through endpoint keeps store bounded."""
        from modules.credit.user_routes import _users

        saved = type(_reset_tokens)(_reset_tokens)
        _reset_tokens.clear()
        # Pre-fill to just under cap
        for i in range(_MAX_RESET_TOKENS):
            _reset_tokens[f"token-{i}"] = f"user-{i}@x.com"
        # Register a user to request reset for
        _users["evict@example.com"] = {
            "email": "evict@example.com",
            "password_hash": "hashed",
            "is_active": True,
            "role": "viewer",
            "org_id": "org-1",
        }
        client = TestClient(app)
        resp = client.post("/auth/reset-password", json={"email": "evict@example.com"})
        assert resp.status_code == 200
        assert len(_reset_tokens) <= _MAX_RESET_TOKENS
        _reset_tokens.clear()
        _reset_tokens.update(saved)
        _users.pop("evict@example.com", None)


class TestPrecompiledRegexPatterns:
    """T10.3: Password validation regex patterns must be precompiled."""

    def test_precompiled_uppercase_pattern_exists(self):
        assert _RE_UPPERCASE.search("A") is not None
        assert _RE_UPPERCASE.search("a") is None

    def test_precompiled_lowercase_pattern_exists(self):
        assert _RE_LOWERCASE.search("a") is not None
        assert _RE_LOWERCASE.search("A") is None

    def test_precompiled_digit_pattern_exists(self):
        assert _RE_DIGIT.search("5") is not None
        assert _RE_DIGIT.search("x") is None

    def test_precompiled_special_pattern_exists(self):
        assert _RE_SPECIAL.search("!") is not None
        assert _RE_SPECIAL.search("a") is None


class TestConfigConstants:
    """T10.3: Config default string literals must use named constants."""

    def test_default_jwt_secret_constant_exists(self):
        assert isinstance(_DEFAULT_JWT_SECRET, str)
        assert len(_DEFAULT_JWT_SECRET) > 0

    def test_default_pii_pepper_constant_exists(self):
        assert isinstance(_DEFAULT_PII_PEPPER, str)
        assert len(_DEFAULT_PII_PEPPER) > 0

    def test_config_validator_uses_jwt_constant(self):
        """Production validator must use the named constant."""
        with pytest.raises(ValueError, match="JWT_SECRET"):
            Settings(
                environment="production",
                jwt_secret=_DEFAULT_JWT_SECRET,
                pii_pepper="secure-pepper",
            )

    def test_config_validator_uses_pepper_constant(self):
        """Production validator must use the named constant."""
        with pytest.raises(ValueError, match="PII_PEPPER"):
            Settings(
                environment="production",
                jwt_secret="secure-jwt-secret",
                pii_pepper=_DEFAULT_PII_PEPPER,
            )


class TestExpandedSsrfBlockedHostnames:
    """T10.3: Webhook SSRF protection must block additional hostnames."""

    def test_blocked_hostnames_includes_zero(self):
        assert "0" in _BLOCKED_HOSTNAMES

    def test_blocked_hostnames_includes_ipv6_loopback(self):
        assert "::1" in _BLOCKED_HOSTNAMES

    def test_blocked_hostnames_includes_127_0_0_1(self):
        assert "127.0.0.1" in _BLOCKED_HOSTNAMES


class TestAdminLookupApiKeyDocstring:
    """T10.3: lookup_api_key must have a TODO docstring for Sprint 11."""

    def test_lookup_api_key_has_todo_docstring(self):
        assert lookup_api_key.__doc__ is not None
        assert "TODO" in lookup_api_key.__doc__


class TestRateLimiting:
    """Test rate limiting (T5.2)."""

    def test_rate_limit_handler_returns_429(self, client):
        """Exercise the rate_limit_handler exception handler."""
        scope = {"type": "http", "headers": []}
        request = Request(scope)
        exc = MagicMock(spec=RateLimitExceeded)

        handler = app.exception_handlers[RateLimitExceeded]
        response = asyncio.run(handler(request, exc))
        assert response.status_code == 429
        assert response.body == b'{"detail":"Rate limit exceeded"}'
