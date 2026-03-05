"""Tests for API versioning — T4.6 TDD."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings(jwt_secret="test-secret", api_key=None)

_VALID_PAYLOAD = {
    "current_score": 740,
    "score_band": "good",
    "overall_utilization": 20.0,
    "account_summary": {"total_accounts": 8, "open_accounts": 6},
    "payment_history_pct": 98.0,
    "average_account_age_months": 72,
}


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


@pytest.mark.usefixtures("bypass_auth")
class TestVersionedAssess:
    """Test /v1/assess endpoint."""

    def test_v1_assess_returns_200(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/v1/assess", json=_VALID_PAYLOAD)
            assert resp.status_code == 200

    def test_v1_assess_returns_assessment_result(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/v1/assess", json=_VALID_PAYLOAD)
            data = resp.json()
            assert "readiness" in data
            assert "barrier_severity" in data


class TestUnversionedEndpoints:
    """Test unversioned endpoints remain at root."""

    def test_health_at_root(self):
        client = _get_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_not_under_v1(self):
        client = _get_client()
        resp = client.get("/v1/health")
        assert resp.status_code in (404, 405)


@pytest.mark.usefixtures("bypass_auth")
class TestDeprecationHeader:
    """Test deprecation header on legacy unversioned /assess."""

    def test_legacy_assess_still_works(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert resp.status_code == 200

    def test_legacy_assess_has_deprecation_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert "Deprecation" in resp.headers

    def test_legacy_assess_has_sunset_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/assess", json=_VALID_PAYLOAD)
            assert "Sunset" in resp.headers

    def test_v1_assess_no_deprecation_header(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post("/v1/assess", json=_VALID_PAYLOAD)
            assert "Deprecation" not in resp.headers


class TestVersionedAuth:
    """Test auth endpoints under /v1."""

    def test_v1_auth_register(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            resp = client.post(
                "/v1/auth/register",
                json={"email": "v1user@test.com", "password": "Secret123!"},
            )
            assert resp.status_code == 201

    def test_v1_auth_login(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _SETTINGS):
            client.post(
                "/v1/auth/register",
                json={"email": "v1login@test.com", "password": "Secret123!"},
            )
            resp = client.post(
                "/v1/auth/login",
                json={"email": "v1login@test.com", "password": "Secret123!"},
            )
            assert resp.status_code == 200
            assert "access_token" in resp.json()


class TestOpenApiVersioned:
    """Test OpenAPI spec reflects versioned paths."""

    def test_openapi_includes_v1_assess(self):
        client = _get_client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/v1/assess" in paths
