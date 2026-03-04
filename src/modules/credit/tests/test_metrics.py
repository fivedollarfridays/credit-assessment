"""Tests for Prometheus metrics and health probes — T3.4 TDD."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings()


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


class TestMetricsEndpoint:
    """Test GET /metrics."""

    def test_metrics_returns_200(self):
        client = _get_client()
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_returns_prometheus_format(self):
        client = _get_client()
        resp = client.get("/metrics")
        content_type = resp.headers.get("content-type", "")
        assert "text/plain" in content_type or "text/plain" in resp.text[:100]

    def test_metrics_includes_http_request_data(self):
        client = _get_client()
        # Make a request first so metrics are populated
        client.get("/health")
        resp = client.get("/metrics")
        assert "http_request" in resp.text or "http_requests" in resp.text


class TestReadyEndpoint:
    """Test GET /ready."""

    def test_ready_returns_200(self):
        client = _get_client()
        resp = client.get("/ready")
        assert resp.status_code == 200

    def test_ready_returns_status(self):
        client = _get_client()
        resp = client.get("/ready")
        data = resp.json()
        assert "status" in data

    def test_ready_reports_db_ok_when_connected(self):
        from modules.credit.router import app

        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        app.state.db_session_factory = mock_factory
        try:
            client = TestClient(app)
            resp = client.get("/ready")
            data = resp.json()
            assert data["database"] == "ok"
            assert data["status"] == "ok"
        finally:
            del app.state.db_session_factory

    def test_ready_reports_degraded_when_db_fails(self):
        from modules.credit.router import app

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("connection refused")
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        app.state.db_session_factory = mock_factory
        try:
            client = TestClient(app)
            resp = client.get("/ready")
            data = resp.json()
            assert data["database"] == "unavailable"
            assert data["status"] == "degraded"
        finally:
            del app.state.db_session_factory
