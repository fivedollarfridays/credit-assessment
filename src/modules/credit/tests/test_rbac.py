"""Tests for RBAC — roles, role enforcement, and API keys — T4.2 TDD."""

from contextlib import contextmanager

from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.router import app
from modules.credit.tests.conftest import (
    _TEST_SETTINGS,
    create_test_user,
    patch_auth_settings,
)


@contextmanager
def _get_client(settings: Settings | None = None):
    """Yield a TestClient with auth settings patched and lifespan active."""
    from modules.credit.rate_limit import limiter

    limiter.reset()
    limiter.enabled = False
    try:
        with patch_auth_settings(settings):
            with TestClient(app) as client:
                yield client
    finally:
        limiter.enabled = True


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
        with _get_client() as client:
            create_test_user(app, "admin@test.com", role="admin")
            resp = client.post(
                "/auth/login",
                json={"email": "admin@test.com", "password": "Secret123!"},
            )
            token = resp.json()["access_token"]

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_viewer_cannot_access_admin_endpoints(self):
        with _get_client() as client:
            create_test_user(app, "viewer@test.com", role="viewer")
            resp = client.post(
                "/auth/login",
                json={"email": "viewer@test.com", "password": "Secret123!"},
            )
            token = resp.json()["access_token"]

            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403

    def test_missing_bearer_returns_403(self):
        with _get_client() as client:
            resp = client.get("/admin/users")
            assert resp.status_code == 403
            assert resp.json()["detail"] == "Invalid or missing credentials"

    def test_invalid_token_returns_401(self):
        with _get_client() as client:
            resp = client.get(
                "/admin/users",
                headers={"Authorization": "Bearer bad-token"},
            )
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid or expired token"

    def test_api_key_rejected_on_role_restricted_endpoint(self):
        """API key users cannot access role-restricted endpoints."""
        settings_with_key = Settings(jwt_secret="test-secret", api_key="test-api-key")
        with _get_client(settings_with_key) as client:
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
        with _get_client() as client:
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

    def _admin_token(self, client, email):
        """Create admin user and return login JWT."""
        create_test_user(app, email, role="admin")
        resp = client.post(
            "/auth/login", json={"email": email, "password": "Secret123!"}
        )
        return resp.json()["access_token"]

    def test_admin_can_create_api_key(self):
        with _get_client() as client:
            token = self._admin_token(client, "keyadmin@test.com")
            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-1", "role": "analyst"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "api_key" in data

    def test_admin_can_revoke_api_key_by_prefix(self):
        with _get_client() as client:
            token = self._admin_token(client, "revokeadmin@test.com")
            create_resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-2", "role": "viewer"},
                headers={"Authorization": f"Bearer {token}"},
            )
            api_key = create_resp.json()["api_key"]
            key_prefix = api_key[:8]
            resp = client.delete(
                f"/admin/api-keys/{key_prefix}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["message"] == "API key revoked"

    def test_revoke_nonexistent_prefix_returns_404(self):
        with _get_client() as client:
            token = self._admin_token(client, "revoke404@test.com")
            resp = client.delete(
                "/admin/api-keys/xxxxxxxx",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404

    def test_api_key_has_expiration(self):
        with _get_client() as client:
            token = self._admin_token(client, "expadmin@test.com")
            resp = client.post(
                "/admin/api-keys",
                json={"org_id": "org-3", "role": "analyst", "expires_in_days": 30},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "expires_at" in data


class TestApiKeyDbManagement:
    """Test DB-backed API key management via ApiKeyRepository."""

    def test_create_persists_key_in_db(self):
        """Creating a scoped API key persists it and lookup succeeds."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                created = await repo.create(
                    key="test-key-1", org_id="org-1", role="analyst"
                )
                assert created.key_prefix == "test-key"
                found = await repo.lookup("test-key-1")
                assert found is not None
                assert found.org_id == "org-1"
                assert found.role == "analyst"
            await engine.dispose()

        asyncio.run(_run())

    def test_revoke_makes_lookup_return_none(self):
        """Revoking a key causes subsequent lookup to return None."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="revoke-key", org_id="org-2", role="viewer")
                revoked = await repo.revoke("revoke-key")
                assert revoked is True
                found = await repo.lookup("revoke-key")
                assert found is None
            await engine.dispose()

        asyncio.run(_run())

    def test_revoke_by_prefix_works(self):
        """Revoking by key_prefix finds and revokes the key."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="prefix-test-key", org_id="org-p", role="viewer")
                revoked = await repo.revoke_by_prefix("prefix-t")
                assert revoked is True
                found = await repo.lookup("prefix-test-key")
                assert found is None
            await engine.dispose()

        asyncio.run(_run())

    def test_revoke_by_prefix_nonexistent_returns_false(self):
        """Revoking by a nonexistent prefix returns False."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                revoked = await repo.revoke_by_prefix("nonexist")
                assert revoked is False
            await engine.dispose()

        asyncio.run(_run())

    def test_revoke_by_prefix_multi_key_collision(self):
        """Revoking a prefix matching multiple keys revokes all and logs warning."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="collide-aaa", org_id="org-c", role="viewer")
                await repo.create(key="collide-bbb", org_id="org-c", role="viewer")
            async with factory() as session:
                repo = ApiKeyRepository(session)
                revoked = await repo.revoke_by_prefix("collide-")
                assert revoked is True
            await engine.dispose()

        asyncio.run(_run())

    def test_lookup_nonexistent_key_returns_none(self):
        """Looking up a key that was never created returns None."""
        import asyncio

        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                found = await repo.lookup("does-not-exist")
                assert found is None
            await engine.dispose()

        asyncio.run(_run())


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


class TestRequireRoleMissingDb:
    """require_role returns 500 when DB factory is unavailable and JWT has no role."""

    def test_missing_db_factory_returns_500(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from modules.credit.auth import create_access_token
        from modules.credit.config import Settings
        from modules.credit.router import app

        test_settings = Settings(api_key=None, jwt_secret="test-secret")
        # JWT without role claim — forces DB lookup in require_role
        token = create_access_token(
            subject="user@test.com",
            secret="test-secret",
            algorithm="HS256",
            expire_minutes=5,
        )
        with (
            patch("modules.credit.router.settings", test_settings),
            patch("modules.credit.assess_routes.settings", test_settings),
        ):
            client = TestClient(app)
            # Remove any stale factory
            if hasattr(app.state, "db_session_factory"):
                delattr(app.state, "db_session_factory")
            resp = client.get(
                "/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 500
            assert "database" in resp.json()["detail"].lower()
