"""Tests for JWT auth endpoints and integration — T3.2 TDD."""

from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD, patch_auth_settings

_JWT_SETTINGS = Settings(
    jwt_secret="test-secret-key",
    jwt_expiry_minutes=30,
    api_key="legacy-api-key",
    database_url="sqlite+aiosqlite://",
    demo_username="admin",
    demo_password="admin",
)


class TestTokenEndpoint:
    """Test POST /auth/token."""

    def test_issue_token_returns_access_token(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/token",
                    json={"username": "admin", "password": "admin"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    def test_issue_token_wrong_credentials_returns_401(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/token",
                    json={"username": "admin", "password": "wrong"},
                )
                assert response.status_code == 401


class TestJwtBearerAuth:
    """Test JWT Bearer token auth on protected endpoints."""

    def _get_token(self, client):
        resp = client.post(
            "/auth/token",
            json={"username": "admin", "password": "admin"},
        )
        return resp.json()["access_token"]

    def test_assess_with_valid_jwt(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                token = self._get_token(client)
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200

    def test_assess_with_invalid_jwt_returns_401(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"Authorization": "Bearer invalid-token"},
                )
                assert response.status_code == 401

    def test_assess_without_auth_returns_403(self):
        """When JWT is configured, no auth header returns 403."""
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post("/assess", json=VALID_ASSESS_PAYLOAD)
                assert response.status_code == 403


class TestTokenRefresh:
    """Test POST /auth/refresh."""

    def test_refresh_returns_new_token(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                resp = client.post(
                    "/auth/token",
                    json={"username": "admin", "password": "admin"},
                )
                old_token = resp.json()["access_token"]
                resp = client.post(
                    "/auth/refresh",
                    headers={"Authorization": f"Bearer {old_token}"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    def test_refresh_without_bearer_returns_403(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                resp = client.post("/auth/refresh")
                assert resp.status_code == 403

    def test_refresh_with_invalid_token_returns_401(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                resp = client.post(
                    "/auth/refresh",
                    headers={"Authorization": "Bearer garbage"},
                )
                assert resp.status_code == 401

    def test_refresh_with_api_key_returns_401(self):
        """Refreshing with an API key instead of JWT returns 401."""
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                resp = client.post(
                    "/auth/refresh",
                    headers={"X-API-Key": "legacy-api-key"},
                )
                assert resp.status_code == 401
                assert resp.json()["detail"] == "Cannot refresh API key"


class TestLegacyApiKeyCompat:
    """Test that legacy API key still works alongside JWT."""

    def test_legacy_api_key_still_accepted(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "legacy-api-key"},
                )
                assert response.status_code == 200

    def test_legacy_wrong_api_key_rejected(self):
        from modules.credit.router import app

        with patch_auth_settings(_JWT_SETTINGS):
            with TestClient(app) as client:
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "wrong-key"},
                )
                assert response.status_code == 403
