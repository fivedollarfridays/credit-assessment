"""Tests for HTTPS/TLS enforcement — T3.1 TDD."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from modules.credit.config import Settings

_DEV_SETTINGS = Settings(environment="development")
_PROD_SETTINGS = Settings(environment="production")


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


class TestHstsHeader:
    """HSTS header enforcement in production mode."""

    def test_hsts_header_present_in_production(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _PROD_SETTINGS):
            resp = client.get("/health")
            assert "strict-transport-security" in resp.headers

    def test_hsts_header_has_max_age(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _PROD_SETTINGS):
            resp = client.get("/health")
            hsts = resp.headers.get("strict-transport-security", "")
            assert "max-age=" in hsts

    def test_hsts_includes_subdomains(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _PROD_SETTINGS):
            resp = client.get("/health")
            hsts = resp.headers.get("strict-transport-security", "")
            assert "includeSubDomains" in hsts

    def test_hsts_header_absent_in_development(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _DEV_SETTINGS):
            resp = client.get("/health")
            assert "strict-transport-security" not in resp.headers


class TestHttpsRedirect:
    """HTTPS redirect enforcement in production mode."""

    def test_http_redirects_to_https_in_production(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _PROD_SETTINGS):
            resp = client.get("/health", follow_redirects=False)
            assert resp.status_code in (301, 307)
            assert resp.headers["location"].startswith("https://")

    def test_no_redirect_in_development(self):
        client = _get_client()
        with patch("modules.credit.router.settings", _DEV_SETTINGS):
            resp = client.get("/health")
            assert resp.status_code == 200
