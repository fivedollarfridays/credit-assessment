"""Tests for blue/green deployment utilities -- T5.2 TDD."""

from __future__ import annotations

import os
import signal
import stat
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

# Project root is 3 levels up from this test file's src/modules/credit/tests/
_PROJECT_ROOT = Path(__file__).resolve().parents[4]


class TestGracefulShutdown:
    """Test graceful shutdown state management."""

    def test_initial_state_is_not_shutting_down(self):
        from modules.credit.deploy import is_shutting_down

        assert is_shutting_down() is False

    def test_setup_graceful_shutdown_registers_sigterm_handler(self):
        from modules.credit.deploy import setup_graceful_shutdown

        old_handler = signal.getsignal(signal.SIGTERM)
        try:
            setup_graceful_shutdown()
            handler = signal.getsignal(signal.SIGTERM)
            assert handler is not old_handler
            assert callable(handler)
        finally:
            signal.signal(signal.SIGTERM, old_handler)

    def test_sigterm_handler_sets_shutting_down(self):
        from modules.credit.deploy import (
            is_shutting_down,
            reset_shutdown_state,
            setup_graceful_shutdown,
        )

        old_handler = signal.getsignal(signal.SIGTERM)
        try:
            reset_shutdown_state()
            setup_graceful_shutdown()
            handler = signal.getsignal(signal.SIGTERM)
            # Simulate SIGTERM by calling the handler directly
            handler(signal.SIGTERM, None)
            assert is_shutting_down() is True
        finally:
            reset_shutdown_state()
            signal.signal(signal.SIGTERM, old_handler)

    def test_reset_shutdown_state(self):
        from modules.credit.deploy import (
            is_shutting_down,
            reset_shutdown_state,
            setup_graceful_shutdown,
        )

        old_handler = signal.getsignal(signal.SIGTERM)
        try:
            setup_graceful_shutdown()
            handler = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)
            assert is_shutting_down() is True
            reset_shutdown_state()
            assert is_shutting_down() is False
        finally:
            signal.signal(signal.SIGTERM, old_handler)


class TestValidateHealth:
    """Test health validation for blue/green deployments."""

    @pytest.mark.asyncio
    async def test_returns_true_when_both_endpoints_healthy(self):
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
    async def test_returns_false_when_health_unhealthy(self):
        from modules.credit.deploy import validate_health

        healthy_response = AsyncMock()
        healthy_response.status_code = 200

        unhealthy_response = AsyncMock()
        unhealthy_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[unhealthy_response, healthy_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("modules.credit.deploy.httpx.AsyncClient", return_value=mock_client):
            result = await validate_health("http://localhost:8000")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_ready_unhealthy(self):
        from modules.credit.deploy import validate_health

        healthy_response = AsyncMock()
        healthy_response.status_code = 200

        unhealthy_response = AsyncMock()
        unhealthy_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[healthy_response, unhealthy_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("modules.credit.deploy.httpx.AsyncClient", return_value=mock_client):
            result = await validate_health("http://localhost:8000")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self):
        from modules.credit.deploy import validate_health

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("modules.credit.deploy.httpx.AsyncClient", return_value=mock_client):
            result = await validate_health("http://localhost:8000")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_custom_timeout(self):
        from modules.credit.deploy import validate_health

        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "modules.credit.deploy.httpx.AsyncClient", return_value=mock_client
        ) as mock_cls:
            await validate_health("http://localhost:8000", timeout=10)
            mock_cls.assert_called_once_with(timeout=10)


class TestDeployConfigFiles:
    """Test that deployment config files exist and are valid."""

    def test_docker_compose_deploy_exists(self):
        path = _PROJECT_ROOT / "docker-compose.deploy.yml"
        assert path.exists(), f"docker-compose.deploy.yml not found at {path}"

    def test_docker_compose_deploy_is_valid_yaml(self):
        path = _PROJECT_ROOT / "docker-compose.deploy.yml"
        content = path.read_text()
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "services" in data

    def test_docker_compose_deploy_has_blue_and_green(self):
        path = _PROJECT_ROOT / "docker-compose.deploy.yml"
        data = yaml.safe_load(path.read_text())
        services = data["services"]
        assert "api-blue" in services
        assert "api-green" in services

    def test_deploy_script_exists(self):
        path = _PROJECT_ROOT / "deploy" / "blue_green.sh"
        assert path.exists(), f"deploy/blue_green.sh not found at {path}"

    def test_deploy_script_is_executable(self):
        path = _PROJECT_ROOT / "deploy" / "blue_green.sh"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "blue_green.sh is not executable"

    def test_rollback_script_exists(self):
        path = _PROJECT_ROOT / "deploy" / "rollback.sh"
        assert path.exists(), f"deploy/rollback.sh not found at {path}"

    def test_rollback_script_is_executable(self):
        path = _PROJECT_ROOT / "deploy" / "rollback.sh"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "rollback.sh is not executable"
