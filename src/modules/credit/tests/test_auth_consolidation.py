"""Tests for auth module consolidation — T12.1 TDD."""

from __future__ import annotations

from unittest.mock import patch

from modules.credit.config import Settings


# ---------------------------------------------------------------------------
# Cycle 1: API_KEY_IDENTITY constant
# ---------------------------------------------------------------------------


class TestApiKeyIdentityConstant:
    """API_KEY_IDENTITY must be a string constant defined in auth.py."""

    def test_api_key_identity_exists(self):
        from modules.credit.auth import API_KEY_IDENTITY

        assert isinstance(API_KEY_IDENTITY, str)

    def test_api_key_identity_value(self):
        from modules.credit.auth import API_KEY_IDENTITY

        assert API_KEY_IDENTITY == "api-key-user"


# ---------------------------------------------------------------------------
# Cycle 2: api_key_header singleton
# ---------------------------------------------------------------------------


class TestApiKeyHeaderSingleton:
    """api_key_header must be defined once in auth.py."""

    def testapi_key_header_exists(self):
        from modules.credit.auth import api_key_header

        assert api_key_header is not None

    def testapi_key_header_name(self):
        from modules.credit.auth import api_key_header

        assert api_key_header.model.name == "X-API-Key"


# ---------------------------------------------------------------------------
# Cycle 3: TokenResponse model
# ---------------------------------------------------------------------------


class TestTokenResponseModel:
    """TokenResponse must be a Pydantic model in auth.py."""

    def test_token_response_exists(self):
        from modules.credit.auth import TokenResponse

        assert TokenResponse is not None

    def test_token_response_has_access_token(self):
        from modules.credit.auth import TokenResponse

        resp = TokenResponse(access_token="abc123")
        assert resp.access_token == "abc123"

    def test_token_response_default_token_type(self):
        from modules.credit.auth import TokenResponse

        resp = TokenResponse(access_token="abc123")
        assert resp.token_type == "bearer"


# ---------------------------------------------------------------------------
# Cycle 4: issue_token_for helper
# ---------------------------------------------------------------------------


class TestIssueTokenFor:
    """issue_token_for must call create_access_token with settings."""

    def test_issue_token_for_returns_string(self):
        from modules.credit.auth import issue_token_for

        token = issue_token_for("user@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_issue_token_for_creates_valid_jwt(self):
        from modules.credit.auth import decode_token, issue_token_for
        from modules.credit.config import settings

        token = issue_token_for("user@example.com")
        payload = decode_token(
            token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        assert payload["sub"] == "user@example.com"

    def test_issue_token_for_uses_settings(self):
        """issue_token_for must read from config settings."""
        test_settings = Settings(jwt_secret="custom-test-secret", jwt_algorithm="HS256")
        with patch("modules.credit.auth.settings", test_settings):
            from modules.credit.auth import decode_token, issue_token_for

            token = issue_token_for("admin@test.com")
            payload = decode_token(
                token, secret="custom-test-secret", algorithm="HS256"
            )
            assert payload["sub"] == "admin@test.com"
