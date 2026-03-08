"""Tests for LOW severity security audit fixes (T26.4).

A06-1: Unused requests dependency removed
A07-2: Demo credentials from env vars, not hardcoded
A01-2: Assessment list returns summary only (no full payloads)
A10-2: validate_health rejects non-http(s) URLs
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# A06-1: Unused requests production dependency
# ---------------------------------------------------------------------------


class TestRequestsDependencyRemoved:
    """The `requests` library should not be a production dependency."""

    def test_requests_not_in_production_dependencies(self) -> None:
        from pathlib import Path

        toml_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
        content = toml_path.read_text()
        # Find the [project] dependencies block; requests should not appear
        # We check that "requests" is not listed as a dependency line
        in_deps = False
        for line in content.splitlines():
            if line.strip().startswith("dependencies"):
                in_deps = True
                continue
            if in_deps and line.strip() == "]":
                break
            if in_deps and "requests" in line.lower():
                pytest.fail(
                    f"'requests' found in production dependencies: {line.strip()}"
                )


# ---------------------------------------------------------------------------
# A07-2: Demo credentials from env vars, not hardcoded
# ---------------------------------------------------------------------------


class TestDemoCredsFromEnvVars:
    """Demo credentials should come from config, not hardcoded constants."""

    def test_no_hardcoded_demo_users_constant(self) -> None:
        """The module should not have a hardcoded _DEMO_USERS dict with creds."""
        import modules.credit.auth_routes as mod

        # _DEMO_USERS should no longer contain hardcoded credentials
        if hasattr(mod, "_DEMO_USERS"):
            assert mod._DEMO_USERS == {}, (
                "_DEMO_USERS should be empty (creds come from config)"
            )

    def test_demo_login_works_with_env_vars(self, client) -> None:
        """Demo login works when demo_username/demo_password are set in config."""
        from modules.credit.config import Settings

        s = Settings(demo_username="testuser", demo_password="testpass")
        with patch("modules.credit.auth_routes.settings", s):
            resp = client.post(
                "/auth/token",
                json={"username": "testuser", "password": "testpass"},
            )
            assert resp.status_code == 200

    def test_demo_login_fails_without_env_vars(self, client) -> None:
        """Without demo creds configured, demo login returns 401."""
        from modules.credit.config import Settings

        s = Settings()  # no demo_username/demo_password
        with patch("modules.credit.auth_routes.settings", s):
            resp = client.post(
                "/auth/token",
                json={"username": "admin", "password": "admin"},
            )
            assert resp.status_code == 401

    def test_demo_login_rejected_in_production_even_with_env_vars(self, client) -> None:
        """Production mode rejects demo creds even when configured."""
        from modules.credit.config import Settings

        s = Settings(
            environment="production",
            jwt_secret="real-secret-here",
            pii_pepper="real-pepper-here",
            database_url="postgresql+asyncpg://u:p@localhost/db",
            demo_username="admin",
            demo_password="admin",
        )
        with (
            patch("modules.credit.auth_routes.settings", s),
            patch("modules.credit.auth.settings", s),
        ):
            resp = client.post(
                "/auth/token",
                json={"username": "admin", "password": "admin"},
            )
            assert resp.status_code == 401

    def test_config_has_demo_settings(self) -> None:
        """Settings should have demo_username and demo_password fields."""
        from modules.credit.config import Settings

        s = Settings(demo_username="u", demo_password="p")
        assert s.demo_username == "u"
        assert s.demo_password == "p"

    def test_config_demo_defaults_to_none(self) -> None:
        """Demo settings default to None."""
        from modules.credit.config import Settings

        s = Settings()
        assert s.demo_username is None
        assert s.demo_password is None


# ---------------------------------------------------------------------------
# A01-2: Assessment list returns summary only
# ---------------------------------------------------------------------------


class TestAssessmentListSummaryOnly:
    """GET /assessments should return summary fields, not full payloads."""

    def test_items_exclude_request_payload(self, client, admin_headers) -> None:
        import asyncio

        from modules.credit.repo_assessments import AssessmentRepository
        from modules.credit.router import app

        factory = app.state.db_session_factory

        async def _insert():
            async with factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={"secret": "data"},
                    response_payload={"full": "response"},
                    user_id="admin@test.com",
                    org_id="org-admin",
                )

        asyncio.run(_insert())
        resp = client.get("/v1/assessments", headers=admin_headers)
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert "request_payload" not in item, "request_payload should be excluded"
            assert "response_payload" not in item, "response_payload should be excluded"

    def test_items_contain_summary_fields(self, client, admin_headers) -> None:
        resp = client.get("/v1/assessments", headers=admin_headers)
        data = resp.json()
        for item in data["items"]:
            for key in [
                "id",
                "credit_score",
                "score_band",
                "barrier_severity",
                "readiness_score",
                "created_at",
            ]:
                assert key in item, f"Summary field {key!r} missing from item"


# ---------------------------------------------------------------------------
# A10-2: validate_health rejects non-http(s) URLs
# ---------------------------------------------------------------------------


class TestValidateHealthUrlScheme:
    """validate_health should only accept http:// and https:// URLs."""

    @pytest.mark.asyncio
    async def test_rejects_file_scheme(self) -> None:
        from modules.credit.deploy import validate_health

        result = await validate_health("file:///etc/passwd")
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_ftp_scheme(self) -> None:
        from modules.credit.deploy import validate_health

        result = await validate_health("ftp://evil.com/payload")
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_no_scheme(self) -> None:
        from modules.credit.deploy import validate_health

        result = await validate_health("localhost:8000")
        assert result is False

    @pytest.mark.asyncio
    async def test_accepts_http_scheme(self) -> None:
        from unittest.mock import AsyncMock

        from modules.credit.deploy import validate_health

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("modules.credit.deploy.httpx.AsyncClient", return_value=mock_client):
            result = await validate_health("http://localhost:8000")
        assert result is True

    @pytest.mark.asyncio
    async def test_accepts_https_scheme(self) -> None:
        from unittest.mock import AsyncMock

        from modules.credit.deploy import validate_health

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("modules.credit.deploy.httpx.AsyncClient", return_value=mock_client):
            result = await validate_health("https://prod.example.com")
        assert result is True
