"""Tests for RBAC — roles, role enforcement, and API keys — T4.2 TDD."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings(jwt_secret="test-secret", api_key=None)


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


class TestRoleEnum:
    """Test Role enum values."""

    def test_has_admin_role(self):
        from modules.credit.roles import Role

        assert Role.ADMIN.value == "admin"

    def test_has_analyst_role(self):
        from modules.credit.roles import Role

        assert Role.ANALYST.value == "analyst"

    def test_has_viewer_role(self):
        from modules.credit.roles import Role

        assert Role.VIEWER.value == "viewer"

    def test_has_exactly_three_roles(self):
        from modules.credit.roles import Role

        assert len(Role) == 3


class TestRoleEnforcement:
    """Test role-based access on endpoints."""

    def _register_and_login(self, client, email, password="Secret123!"):
        client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        resp = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        return resp.json()["access_token"]

    def _patch_all(self):
        from contextlib import ExitStack
        stack = ExitStack()
        for mod in ["router", "auth_routes", "user_routes", "roles"]:
            stack.enter_context(patch(f"modules.credit.{mod}.settings", _SETTINGS))
        return stack

    def test_admin_can_list_users(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "admin@test.com")
            from modules.credit.user_routes import _users
            _users["admin@test.com"]["role"] = "admin"

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_viewer_cannot_access_admin_endpoints(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "viewer@test.com")
            from modules.credit.user_routes import _users
            _users["viewer@test.com"]["role"] = "viewer"

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403

    def test_missing_bearer_returns_401(self):
        client = _get_client()
        with self._patch_all():
            resp = client.get("/admin/users")
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Missing Bearer token"

    def test_invalid_token_returns_401(self):
        client = _get_client()
        with self._patch_all():
            resp = client.get(
                "/admin/users",
                headers={"Authorization": "Bearer bad-token"},
            )
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid token"

    def test_valid_token_unknown_user_returns_401(self):
        client = _get_client()
        with self._patch_all():
            from modules.credit.auth import create_access_token
            token = create_access_token(
                subject="ghost@test.com",
                secret=_SETTINGS.jwt_secret,
                algorithm=_SETTINGS.jwt_algorithm,
                expire_minutes=30,
            )
            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 401
            assert resp.json()["detail"] == "User not found"


class TestApiKeyModel:
    """Test API key creation and management."""

    def _register_and_login(self, client, email, password="Secret123!"):
        client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        resp = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        return resp.json()["access_token"]

    def _patch_all(self):
        from contextlib import ExitStack
        stack = ExitStack()
        for mod in ["router", "auth_routes", "user_routes", "roles"]:
            stack.enter_context(patch(f"modules.credit.{mod}.settings", _SETTINGS))
        return stack

    def test_admin_can_create_api_key(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "keyadmin@test.com")
            from modules.credit.user_routes import _users
            _users["keyadmin@test.com"]["role"] = "admin"

            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-1", "role": "analyst"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "api_key" in data

    def test_admin_can_revoke_api_key(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "revokeadmin@test.com")
            from modules.credit.user_routes import _users
            _users["revokeadmin@test.com"]["role"] = "admin"

            create_resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-2", "role": "viewer"},
                headers={"Authorization": f"Bearer {token}"},
            )
            api_key = create_resp.json()["api_key"]

            resp = client.delete(
                f"/admin/api-keys/{api_key}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["message"] == "API key revoked"

    def test_revoke_nonexistent_key_returns_404(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "revoke404@test.com")
            from modules.credit.user_routes import _users
            _users["revoke404@test.com"]["role"] = "admin"

            resp = client.delete(
                "/admin/api-keys/nonexistent-key",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404

    def test_api_key_has_expiration(self):
        client = _get_client()
        with self._patch_all():
            token = self._register_and_login(client, "expadmin@test.com")
            from modules.credit.user_routes import _users
            _users["expadmin@test.com"]["role"] = "admin"

            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-3", "role": "analyst", "expires_in_days": 30},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "expires_at" in data
