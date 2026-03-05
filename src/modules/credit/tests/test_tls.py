"""Tests for HTTPS/TLS enforcement — T3.1 TDD."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.credit.middleware import HstsMiddleware, HttpsRedirectMiddleware


def _make_app(*, hsts_prod: bool, redirect_prod: bool) -> FastAPI:
    """Build a minimal FastAPI app with TLS middleware configured."""
    test_app = FastAPI()

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    test_app.add_middleware(HstsMiddleware, prod_check=lambda: hsts_prod)
    test_app.add_middleware(HttpsRedirectMiddleware, prod_check=lambda: redirect_prod)
    return test_app


class TestHstsHeader:
    """HSTS header enforcement in production mode."""

    def test_hsts_header_present_in_production(self):
        app = _make_app(hsts_prod=True, redirect_prod=False)
        client = TestClient(app)
        resp = client.get("/health")
        assert "strict-transport-security" in resp.headers

    def test_hsts_header_has_max_age(self):
        app = _make_app(hsts_prod=True, redirect_prod=False)
        client = TestClient(app)
        resp = client.get("/health")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "max-age=" in hsts

    def test_hsts_includes_subdomains(self):
        app = _make_app(hsts_prod=True, redirect_prod=False)
        client = TestClient(app)
        resp = client.get("/health")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "includeSubDomains" in hsts

    def test_hsts_header_absent_in_development(self):
        app = _make_app(hsts_prod=False, redirect_prod=False)
        client = TestClient(app)
        resp = client.get("/health")
        assert "strict-transport-security" not in resp.headers


class TestHttpsRedirect:
    """HTTPS redirect enforcement in production mode."""

    def test_http_redirects_to_https_in_production(self):
        app = _make_app(hsts_prod=False, redirect_prod=True)
        client = TestClient(app)
        resp = client.get("/health", follow_redirects=False)
        assert resp.status_code in (301, 307)
        assert resp.headers["location"].startswith("https://")

    def test_no_redirect_in_development(self):
        app = _make_app(hsts_prod=False, redirect_prod=False)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
