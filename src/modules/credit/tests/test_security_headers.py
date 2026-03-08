"""Tests for security headers: middleware, dashboard CSP, and rate limiting on auth.

Covers audit findings #4, #7, #8.
"""

from __future__ import annotations


class TestSecurityHeadersMiddleware:
    """Finding #8: X-Content-Type-Options, Referrer-Policy, Permissions-Policy on all responses."""

    def test_health_has_x_content_type_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_health_has_referrer_policy(self, client):
        resp = client.get("/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_health_has_permissions_policy(self, client):
        resp = client.get("/health")
        assert (
            resp.headers.get("permissions-policy")
            == "camera=(), microphone=(), geolocation=()"
        )


class TestDashboardSecurityHeaders:
    """Finding #7: CSP and frame protection on GET /dashboard."""

    def test_dashboard_has_csp_header(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        csp = resp.headers.get("content-security-policy")
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_dashboard_has_x_frame_options(self, client):
        resp = client.get("/dashboard")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_dashboard_has_x_content_type_options(self, client):
        resp = client.get("/dashboard")
        assert resp.headers.get("x-content-type-options") == "nosniff"


class TestAuthRateLimiting:
    """Finding #4: Rate limit decorators on auth endpoints."""

    def test_login_has_rate_limit_decorator(self):
        from modules.credit.user_routes import login

        assert hasattr(login, "__wrapped__"), "login should have rate limit decorator"

    def test_register_has_rate_limit_decorator(self):
        from modules.credit.user_routes import register

        assert hasattr(register, "__wrapped__"), (
            "register should have rate limit decorator"
        )

    def test_request_reset_has_rate_limit_decorator(self):
        from modules.credit.user_routes import request_reset

        assert hasattr(request_reset, "__wrapped__"), (
            "request_reset should have rate limit decorator"
        )

    def test_confirm_reset_has_rate_limit_decorator(self):
        from modules.credit.user_routes import confirm_reset

        assert hasattr(confirm_reset, "__wrapped__"), (
            "confirm_reset should have rate limit decorator"
        )
