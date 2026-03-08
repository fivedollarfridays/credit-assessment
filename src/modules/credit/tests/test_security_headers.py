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

    def test_dashboard_csp_no_unsafe_inline_scripts(self, client):
        """A05-1: script-src must not use 'unsafe-inline'."""
        resp = client.get("/dashboard")
        csp = resp.headers.get("content-security-policy", "")
        # Extract script-src directive
        for directive in csp.split(";"):
            d = directive.strip()
            if d.startswith("script-src"):
                assert "'unsafe-inline'" not in d, (
                    f"script-src must not include 'unsafe-inline': {d}"
                )
                assert "'sha256-" in d, f"script-src should use hash-based CSP: {d}"

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


class TestCryptoFieldEncryption:
    """A02-2: Webhook secrets must be encrypted at rest."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        from modules.credit.crypto import decrypt_field, encrypt_field

        key = "test-encryption-key-for-webhook-secrets"
        plaintext = "my-super-secret-hmac-key-32chars!"
        encrypted = encrypt_field(plaintext, key)
        assert encrypted != plaintext
        assert decrypt_field(encrypted, key) == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self) -> None:
        from modules.credit.crypto import encrypt_field

        key = "test-key"
        plaintext = "same-value"
        a = encrypt_field(plaintext, key)
        b = encrypt_field(plaintext, key)
        # Fernet uses random IV so ciphertexts should differ
        assert a != b

    def test_decrypt_with_wrong_key_raises(self) -> None:
        import pytest

        from modules.credit.crypto import decrypt_field, encrypt_field

        encrypted = encrypt_field("secret", "correct-key")
        with pytest.raises(Exception):
            decrypt_field(encrypted, "wrong-key")

    def test_encrypt_field_none_key_returns_plaintext(self) -> None:
        from modules.credit.crypto import encrypt_field

        result = encrypt_field("plaintext-value", None)
        assert result == "plaintext-value"

    def test_decrypt_field_none_key_returns_as_is(self) -> None:
        from modules.credit.crypto import decrypt_field

        result = decrypt_field("not-encrypted", None)
        assert result == "not-encrypted"

    def test_config_has_webhook_encryption_key(self) -> None:
        from modules.credit.config import Settings

        s = Settings()
        assert s.webhook_encryption_key is None

    def test_config_accepts_webhook_encryption_key(self) -> None:
        from modules.credit.config import Settings

        s = Settings(webhook_encryption_key="my-secret-key")
        assert s.webhook_encryption_key == "my-secret-key"
