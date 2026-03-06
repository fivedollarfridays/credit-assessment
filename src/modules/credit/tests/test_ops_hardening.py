"""Tests for T20.3 — operational hardening: gunicorn, Redis, OpenAPI behind auth."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from modules.credit.config import Settings

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


# --- Dockerfile: gunicorn with configurable workers ---


class TestDockerfileGunicorn:
    def test_dockerfile_uses_gunicorn(self):
        content = (_PROJECT_ROOT / "Dockerfile").read_text()
        assert "gunicorn" in content

    def test_dockerfile_uses_uvicorn_worker_class(self):
        content = (_PROJECT_ROOT / "Dockerfile").read_text()
        assert "uvicorn.workers.UvicornWorker" in content

    def test_dockerfile_respects_web_concurrency(self):
        content = (_PROJECT_ROOT / "Dockerfile").read_text()
        assert "WEB_CONCURRENCY" in content


# --- docker-compose: Redis service ---


class TestDockerComposeRedis:
    def test_has_redis_service(self):
        data = yaml.safe_load((_PROJECT_ROOT / "docker-compose.yml").read_text())
        assert "redis" in data["services"]

    def test_redis_uses_alpine_image(self):
        data = yaml.safe_load((_PROJECT_ROOT / "docker-compose.yml").read_text())
        image = data["services"]["redis"]["image"]
        assert "redis" in image and "alpine" in image

    def test_api_has_redis_url(self):
        data = yaml.safe_load((_PROJECT_ROOT / "docker-compose.yml").read_text())
        env = data["services"]["api"]["environment"]
        redis_found = any("REDIS_URL" in str(e) for e in env)
        assert redis_found, "API service missing REDIS_URL env var"

    def test_api_depends_on_redis(self):
        data = yaml.safe_load((_PROJECT_ROOT / "docker-compose.yml").read_text())
        depends = data["services"]["api"]["depends_on"]
        assert "redis" in depends


# --- OpenAPI spec behind auth in production ---


class TestOpenApiBehindAuth:
    def test_openapi_endpoint_requires_auth(self, client):
        resp = client.get("/v1/docs/openapi.json")
        assert resp.status_code in (401, 403)

    def test_openapi_endpoint_accessible_with_admin(self, client, admin_headers):
        resp = client.get("/v1/docs/openapi.json", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "info" in data
        assert "paths" in data

    def test_openapi_endpoint_returns_valid_spec(self, client, admin_headers):
        resp = client.get("/v1/docs/openapi.json", headers=admin_headers)
        data = resp.json()
        assert data["info"]["title"] == "Credit Assessment API"
        assert data["info"]["version"] == "1.0.0"


# --- Readiness probe: Redis connectivity ---


class TestReadinessRedis:
    def test_ready_includes_redis_when_configured(self, client):
        with patch("modules.credit.router.settings", Settings(
            jwt_secret="test-secret",
            redis_url="redis://localhost:6379",
            database_url="sqlite+aiosqlite://",
        )):
            with patch(
                "modules.credit.rate_limit.check_redis_health",
                new_callable=AsyncMock,
                return_value=True,
            ):
                resp = client.get("/ready")
                assert resp.status_code == 200
                assert resp.json()["redis"] == "ok"

    def test_ready_skips_redis_when_not_configured(self, client):
        resp = client.get("/ready")
        data = resp.json()
        assert "redis" not in data or data.get("redis") is None

    def test_ready_reports_redis_unavailable(self, client):
        with patch("modules.credit.router.settings", Settings(
            jwt_secret="test-secret",
            redis_url="redis://localhost:6379",
            database_url="sqlite+aiosqlite://",
        )):
            with patch(
                "modules.credit.rate_limit.check_redis_health",
                new_callable=AsyncMock,
                return_value=False,
            ):
                resp = client.get("/ready")
                data = resp.json()
                assert data["redis"] == "unavailable"
                assert data["status"] == "degraded"


# --- check_redis_health function ---


class TestCheckRedisHealth:
    @pytest.mark.asyncio
    async def test_returns_true_on_successful_ping(self):
        from modules.credit.rate_limit import check_redis_health

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch("modules.credit.rate_limit.redis.asyncio.from_url", return_value=mock_redis):
            assert await check_redis_health("redis://localhost:6379") is True

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self):
        from modules.credit.rate_limit import check_redis_health

        with patch(
            "modules.credit.rate_limit.redis.asyncio.from_url",
            side_effect=Exception("connection refused"),
        ):
            assert await check_redis_health("redis://localhost:6379") is False

    @pytest.mark.asyncio
    async def test_returns_false_on_ping_failure(self):
        from modules.credit.rate_limit import check_redis_health

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("timeout"))
        mock_redis.aclose = AsyncMock()

        with patch("modules.credit.rate_limit.redis.asyncio.from_url", return_value=mock_redis):
            assert await check_redis_health("redis://localhost:6379") is False


# --- pyproject.toml: gunicorn dependency ---


class TestGunicornDependency:
    def test_gunicorn_in_dependencies(self):
        content = (_PROJECT_ROOT / "pyproject.toml").read_text()
        assert "gunicorn" in content
