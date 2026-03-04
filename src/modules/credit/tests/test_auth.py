"""Tests for JWT authentication — T3.2 TDD."""

from unittest.mock import patch

import pytest


class TestJwtConfigSettings:
    """Test JWT-related settings in config."""

    def test_default_jwt_secret(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.jwt_secret == "change-me-in-production"

    def test_jwt_secret_from_env(self):
        with patch.dict("os.environ", {"JWT_SECRET": "super-secret-key"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.jwt_secret == "super-secret-key"

    def test_default_jwt_algorithm(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.jwt_algorithm == "HS256"

    def test_default_jwt_expiry_minutes(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.jwt_expiry_minutes == 30


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token_returns_string(self):
        from modules.credit.auth import create_access_token

        token = create_access_token(
            subject="user1", secret="test-secret", algorithm="HS256", expire_minutes=30
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_subject(self):
        from modules.credit.auth import create_access_token, decode_token

        token = create_access_token(
            subject="user1", secret="test-secret", algorithm="HS256", expire_minutes=30
        )
        payload = decode_token(token, secret="test-secret", algorithm="HS256")
        assert payload["sub"] == "user1"

    def test_create_access_token_has_expiry(self):
        from modules.credit.auth import create_access_token, decode_token

        token = create_access_token(
            subject="user1", secret="test-secret", algorithm="HS256", expire_minutes=30
        )
        payload = decode_token(token, secret="test-secret", algorithm="HS256")
        assert "exp" in payload


class TestTokenValidation:
    """Test JWT token validation."""

    def test_decode_valid_token(self):
        from modules.credit.auth import create_access_token, decode_token

        token = create_access_token(
            subject="user1", secret="my-secret", algorithm="HS256", expire_minutes=30
        )
        payload = decode_token(token, secret="my-secret", algorithm="HS256")
        assert payload["sub"] == "user1"

    def test_decode_wrong_secret_raises(self):
        from modules.credit.auth import (
            InvalidTokenError,
            create_access_token,
            decode_token,
        )

        token = create_access_token(
            subject="user1", secret="right-secret", algorithm="HS256", expire_minutes=30
        )
        with pytest.raises(InvalidTokenError):
            decode_token(token, secret="wrong-secret", algorithm="HS256")

    def test_decode_expired_token_raises(self):
        from modules.credit.auth import (
            InvalidTokenError,
            create_access_token,
            decode_token,
        )

        token = create_access_token(
            subject="user1",
            secret="test-secret",
            algorithm="HS256",
            expire_minutes=-1,
        )
        with pytest.raises(InvalidTokenError):
            decode_token(token, secret="test-secret", algorithm="HS256")

    def test_decode_garbage_token_raises(self):
        from modules.credit.auth import InvalidTokenError, decode_token

        with pytest.raises(InvalidTokenError):
            decode_token("not-a-token", secret="test-secret", algorithm="HS256")
