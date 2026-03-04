"""Tests for user registration, login, and password reset endpoints — T4.1 TDD."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings()


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


def _mock_db_factory(mock_session):
    """Create a mock session factory that yields mock_session."""
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return factory


class TestRegisterEndpoint:
    """Test POST /auth/register."""

    def test_register_returns_201(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 201

    def test_register_returns_user_email(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new2@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert data["email"] == "new2@example.com"

    def test_register_does_not_return_password(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new3@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email_returns_409(self):
        client = _get_client()
        payload = {"email": "dupe@example.com", "password": "Secret123!"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409


class TestLoginEndpoint:
    """Test POST /auth/login."""

    def test_login_returns_tokens(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "login2@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login2@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self):
        client = _get_client()
        resp = client.post(
            "/auth/login",
            json={"email": "noone@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401


class TestPasswordReset:
    """Test password reset flow."""

    def test_request_reset_returns_200(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "reset@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/reset-password",
            json={"email": "reset@example.com"},
        )
        assert resp.status_code == 200

    def test_request_reset_nonexistent_returns_200(self):
        """Returns 200 even for nonexistent email to prevent enumeration."""
        client = _get_client()
        resp = client.post(
            "/auth/reset-password",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200

    def test_confirm_reset_invalid_token_returns_400(self):
        client = _get_client()
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": "bogus-token", "new_password": "NewPass!"},
        )
        assert resp.status_code == 400

    def test_confirm_reset_changes_password(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "reset2@example.com", "password": "OldPass123!"},
        )
        # Request reset token
        resp = client.post(
            "/auth/reset-password",
            json={"email": "reset2@example.com"},
        )
        token = resp.json().get("reset_token")

        # Confirm reset with new password
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token, "new_password": "NewPass456!"},
        )
        assert resp.status_code == 200

        # Login with new password
        resp = client.post(
            "/auth/login",
            json={"email": "reset2@example.com", "password": "NewPass456!"},
        )
        assert resp.status_code == 200
