"""Tests for RBAC — roles, role enforcement, and API keys — T4.2 TDD."""

from modules.credit.config import Settings
from modules.credit.tests.conftest import (
    _TEST_SETTINGS,
    patch_auth_settings,
    register_and_login,
)


def _get_client():
    from fastapi.testclient import TestClient

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

    def test_admin_can_list_users(self):
        client = _get_client()
        with patch_auth_settings():
            token = register_and_login(client, "admin@test.com")
            from modules.credit.user_store import _users

            _users["admin@test.com"]["role"] = "admin"

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_viewer_cannot_access_admin_endpoints(self):
        client = _get_client()
        with patch_auth_settings():
            token = register_and_login(client, "viewer@test.com")
            from modules.credit.user_store import _users

            _users["viewer@test.com"]["role"] = "viewer"

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403

    def test_missing_bearer_returns_403(self):
        client = _get_client()
        with patch_auth_settings():
            resp = client.get("/admin/users")
            assert resp.status_code == 403
            assert resp.json()["detail"] == "Invalid or missing credentials"

    def test_invalid_token_returns_401(self):
        client = _get_client()
        with patch_auth_settings():
            resp = client.get(
                "/admin/users",
                headers={"Authorization": "Bearer bad-token"},
            )
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid or expired token"

    def test_api_key_rejected_on_role_restricted_endpoint(self):
        """API key users cannot access role-restricted endpoints."""
        settings_with_key = Settings(jwt_secret="test-secret", api_key="test-api-key")
        client = _get_client()
        with patch_auth_settings(settings_with_key):
            resp = client.get(
                "/admin/users",
                headers={"X-API-Key": "test-api-key"},
            )
            assert resp.status_code == 403
            assert (
                resp.json()["detail"]
                == "API key users cannot access role-restricted endpoints"
            )

    def test_valid_token_unknown_user_returns_401(self):
        client = _get_client()
        with patch_auth_settings():
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="ghost@test.com",
                secret=_TEST_SETTINGS.jwt_secret,
                algorithm=_TEST_SETTINGS.jwt_algorithm,
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

    def test_admin_can_create_api_key(self):
        client = _get_client()
        with patch_auth_settings():
            token = register_and_login(client, "keyadmin@test.com")
            from modules.credit.user_store import _users

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
        with patch_auth_settings():
            token = register_and_login(client, "revokeadmin@test.com")
            from modules.credit.user_store import _users

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
        with patch_auth_settings():
            token = register_and_login(client, "revoke404@test.com")
            from modules.credit.user_store import _users

            _users["revoke404@test.com"]["role"] = "admin"

            resp = client.delete(
                "/admin/api-keys/nonexistent-key",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404

    def test_api_key_has_expiration(self):
        client = _get_client()
        with patch_auth_settings():
            token = register_and_login(client, "expadmin@test.com")
            from modules.credit.user_store import _users

            _users["expadmin@test.com"]["role"] = "admin"

            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-3", "role": "analyst", "expires_in_days": 30},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "expires_at" in data


class TestApiKeyEviction:
    """Test that _api_keys store is bounded via FIFO eviction."""

    def test_create_api_key_evicts_oldest_when_over_cap(self):
        """Creating an API key when at cap evicts the oldest entry."""
        from modules.credit.admin_routes import _MAX_API_KEYS, _api_keys

        saved = dict(_api_keys)
        _api_keys.clear()
        # Pre-fill to exactly the cap
        for i in range(_MAX_API_KEYS):
            _api_keys[f"prefill-{i}"] = {
                "org_id": "org-x",
                "role": "viewer",
                "expires_at": None,
            }
        assert len(_api_keys) == _MAX_API_KEYS
        first_key = next(iter(_api_keys))

        client = _get_client()
        with patch_auth_settings():
            token = register_and_login(client, "evictadmin@test.com")
            from modules.credit.user_store import _users

            _users["evictadmin@test.com"]["role"] = "admin"
            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-evict", "role": "viewer"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            # The oldest key should have been evicted
            assert first_key not in _api_keys
            assert len(_api_keys) <= _MAX_API_KEYS
            _api_keys.clear()
            _api_keys.update(saved)
            _users.pop("evictadmin@test.com", None)


class TestIsAdmin:
    """Test is_admin helper function."""

    def test_is_admin_returns_true_for_admin(self):
        from modules.credit.roles import is_admin

        assert is_admin({"role": "admin"}) is True

    def test_is_admin_returns_false_for_viewer(self):
        from modules.credit.roles import is_admin

        assert is_admin({"role": "viewer"}) is False

    def test_is_admin_returns_false_for_none(self):
        from modules.credit.roles import is_admin

        assert is_admin(None) is False

    def test_is_admin_returns_false_for_missing_role(self):
        from modules.credit.roles import is_admin

        assert is_admin({}) is False
