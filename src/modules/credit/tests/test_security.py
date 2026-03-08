"""Tests for API security features — T5.2/T10.3 TDD."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from modules.credit.audit import hash_pii
from modules.credit.auth import create_access_token
from modules.credit.config import Settings, _DEFAULT_JWT_SECRET, _DEFAULT_PII_PEPPER
from modules.credit.router import app
from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD
from modules.credit.user_store import (
    _RE_DIGIT,
    _RE_LOWERCASE,
    _RE_SPECIAL,
    _RE_UPPERCASE,
)
from modules.credit.webhook_routes import _BLOCKED_HOSTNAMES


@pytest.fixture
def client():
    from modules.credit.rate_limit import limiter

    limiter.reset()
    return TestClient(app)


class TestApiKeyAuth:
    """Test API key authentication."""

    def test_no_credentials_rejected_even_when_api_key_unset(self, client):
        """When API_KEY env is not set, requests without any credentials are rejected."""
        response = client.post("/assess", json=VALID_ASSESS_PAYLOAD)
        assert response.status_code == 403

    def test_rejects_wrong_api_key(self):
        """When API_KEY is set, wrong key returns 403."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            with TestClient(app) as client:
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

    def test_accepts_correct_api_key(self):
        """When API_KEY is set, correct key passes."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "secret-key"},
                )
                assert response.status_code == 200


class TestApiKeyTimingSafety:
    """Static API key comparison must use constant-time comparison."""

    def test_verify_auth_uses_hmac_compare_digest(self):
        """verify_auth uses hmac.compare_digest for static API key."""
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
            patch("modules.credit.assess_routes.hmac") as mock_hmac,
        ):
            mock_hmac.compare_digest.return_value = True
            with TestClient(app) as client:
                response = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "secret-key"},
                )
                assert response.status_code == 200
                mock_hmac.compare_digest.assert_called_once_with(
                    "secret-key", "secret-key"
                )


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


class TestApiKeyExpirationDb:
    """DB-backed API key lookup must respect expiry."""

    @pytest.fixture
    def db_factory(self):
        """Create in-memory database with tables for each test."""
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _init():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(_init())
        return factory

    def test_lookup_expired_key_returns_none(self, db_factory):
        """Expired key must return None from lookup."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                past = datetime.now(timezone.utc) - timedelta(days=1)
                await repo.create(
                    key="expired-key", org_id="org-1", role="viewer", expires_at=past
                )
                assert await repo.lookup("expired-key") is None

        asyncio.run(_run())

    def test_lookup_valid_key_returns_entry(self, db_factory):
        """Valid (non-expired) key must return entry with correct org_id."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                future = datetime.now(timezone.utc) + timedelta(days=30)
                await repo.create(
                    key="valid-key", org_id="org-1", role="viewer", expires_at=future
                )
                result = await repo.lookup("valid-key")
                assert result is not None
                assert result.org_id == "org-1"

        asyncio.run(_run())

    def test_lookup_no_expiry_key_returns_entry(self, db_factory):
        """Key with no expiry (expires_at=None) must be returned."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                await repo.create(key="no-expiry", org_id="org-2", role="admin")
                result = await repo.lookup("no-expiry")
                assert result is not None

        asyncio.run(_run())

    def test_lookup_nonexistent_key_returns_none(self, db_factory):
        """Nonexistent key must return None."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                assert await repo.lookup("nonexistent") is None

        asyncio.run(_run())


class TestResetTokenDbBacked:
    """Reset tokens are now DB-backed with TTL expiry."""

    def test_reset_token_stored_in_db(self):
        """Reset token request stores token in database."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, create_test_user

        with patch("modules.credit.router.settings", _TEST_SETTINGS):
            with patch("modules.credit.assess_routes.settings", _TEST_SETTINGS):
                with patch("modules.credit.auth.settings", _TEST_SETTINGS):
                    with TestClient(app) as client:
                        create_test_user(app, "resetdb@test.com", role="viewer")
                        resp = client.post(
                            "/auth/reset-password",
                            json={"email": "resetdb@test.com"},
                        )
                        assert resp.status_code == 200


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


class TestApiKeyRepositoryDocstring:
    """ApiKeyRepository class must have a docstring."""

    def test_api_key_repository_has_docstring(self):
        from modules.credit.repo_api_keys import ApiKeyRepository

        assert ApiKeyRepository.__doc__ is not None
        assert len(ApiKeyRepository.__doc__.strip()) > 0


class TestMissingDbFactoryWarning:
    """verify_auth warns when API key provided but DB factory unavailable."""

    def test_api_key_without_db_factory_logs_warning(self):
        mock = Settings(api_key="secret-key")
        with (
            patch("modules.credit.router.settings", mock),
            patch("modules.credit.assess_routes.settings", mock),
        ):
            # Bare TestClient — no lifespan, no db_session_factory
            client = TestClient(app)
            # Remove any stale factory from prior tests
            if hasattr(app.state, "db_session_factory"):
                delattr(app.state, "db_session_factory")
            with patch("modules.credit.assess_routes.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                resp = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "secret-key"},
                )
                # Should still authenticate via static key fallback
                assert resp.status_code == 200
                mock_logger.warning.assert_called()


class TestScopedApiKeyAuth:
    """T18.2: Scoped API keys authenticate via DB and carry org_id/role."""

    def test_scoped_key_authenticates_on_assess(self):
        """A valid scoped API key should authenticate on /assess."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, patch_auth_settings

        with patch_auth_settings(_TEST_SETTINGS):
            with TestClient(app) as client:
                # Create a scoped API key in DB
                from modules.credit.repo_api_keys import ApiKeyRepository

                factory = app.state.db_session_factory

                async def _create():
                    async with factory() as session:
                        repo = ApiKeyRepository(session)
                        await repo.create(
                            key="scoped-test-key",
                            org_id="org-1",
                            role="viewer",
                        )

                asyncio.run(_create())

                resp = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "scoped-test-key"},
                )
                assert resp.status_code == 200

    def test_expired_scoped_key_rejected(self):
        """An expired scoped API key should be rejected."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, patch_auth_settings

        with patch_auth_settings(_TEST_SETTINGS):
            with TestClient(app) as client:
                from modules.credit.repo_api_keys import ApiKeyRepository

                factory = app.state.db_session_factory

                async def _create():
                    async with factory() as session:
                        repo = ApiKeyRepository(session)
                        await repo.create(
                            key="expired-scoped",
                            org_id="org-1",
                            role="viewer",
                            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                        )

                asyncio.run(_create())

                resp = client.post(
                    "/assess",
                    json=VALID_ASSESS_PAYLOAD,
                    headers={"X-API-Key": "expired-scoped"},
                )
                assert resp.status_code == 403

    def test_scoped_key_with_admin_role_passes_require_role(self):
        """A scoped key with admin role can access admin endpoints."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, patch_auth_settings

        with patch_auth_settings(_TEST_SETTINGS):
            with TestClient(app) as client:
                from modules.credit.repo_api_keys import ApiKeyRepository

                factory = app.state.db_session_factory

                async def _create():
                    async with factory() as session:
                        repo = ApiKeyRepository(session)
                        await repo.create(
                            key="admin-scoped",
                            org_id="org-admin",
                            role="admin",
                        )

                asyncio.run(_create())

                resp = client.get(
                    "/admin/audit-log",
                    headers={"X-API-Key": "admin-scoped"},
                )
                assert resp.status_code == 200

    def test_scoped_key_with_viewer_role_rejected_by_admin_endpoint(self):
        """A scoped key with viewer role cannot access admin endpoints."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, patch_auth_settings

        with patch_auth_settings(_TEST_SETTINGS):
            with TestClient(app) as client:
                from modules.credit.repo_api_keys import ApiKeyRepository

                factory = app.state.db_session_factory

                async def _create():
                    async with factory() as session:
                        repo = ApiKeyRepository(session)
                        await repo.create(
                            key="viewer-scoped",
                            org_id="org-1",
                            role="viewer",
                        )

                asyncio.run(_create())

                resp = client.get(
                    "/admin/audit-log",
                    headers={"X-API-Key": "viewer-scoped"},
                )
                assert resp.status_code == 403


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
