"""Tests for webhook URL security — SSRF protection and HTTPS enforcement."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from modules.credit.webhook_delivery import _resolve_and_check
from modules.credit.webhook_routes import _is_private_ip


def _post_webhook(client, url: str):
    return client.post(
        "/v1/webhooks",
        json={
            "url": url,
            "events": ["assessment.completed"],
            "secret": "webhook-secret-01234567890abcdef",
        },
    )


# --- SSRF Protection ---


@pytest.mark.usefixtures("bypass_auth")
class TestSsrfProtection:
    """Test that webhook URL validation blocks internal/private addresses."""

    def test_rejects_localhost_url(self, client):
        resp = _post_webhook(client, "https://localhost/hook")
        assert resp.status_code == 422

    def test_rejects_private_ip_192_168(self, client):
        resp = _post_webhook(client, "https://192.168.1.1/hook")
        assert resp.status_code == 422

    def test_rejects_127_0_0_1(self, client):
        resp = _post_webhook(client, "https://127.0.0.1/hook")
        assert resp.status_code == 422

    def test_rejects_metadata_169_254(self, client):
        resp = _post_webhook(client, "http://169.254.169.254/latest/meta-data/")
        assert resp.status_code == 422

    def test_rejects_zero_hostname(self, client):
        resp = _post_webhook(client, "https://0/hook")
        assert resp.status_code == 422

    def test_rejects_ipv6_loopback_bracket(self, client):
        resp = _post_webhook(client, "https://[::1]/hook")
        assert resp.status_code == 422

    def test_accepts_public_https_url(self, client):
        resp = _post_webhook(client, "https://example.com/hook")
        assert resp.status_code == 201


# --- SSRF hardening: expanded IP range detection ---


class TestSsrfExpandedRanges:
    """T11.1: _is_private_ip must block carrier-grade NAT and multicast."""

    def test_carrier_grade_nat_blocked(self):
        """100.64.0.0/10 (carrier-grade NAT) must be treated as non-global."""
        assert _is_private_ip("100.64.0.1") is True

    def test_multicast_blocked(self):
        """224.0.0.1 (multicast) must be treated as non-global."""
        assert _is_private_ip("224.0.0.1") is True


# --- HTTPS enforcement in production ---


class TestWebhookHttpsInProduction:
    """Production webhooks must require https:// URLs."""

    @pytest.mark.usefixtures("bypass_auth")
    def test_http_rejected_in_production(self, client):
        """http:// URLs must be rejected when environment=production."""
        from modules.credit.config import Settings

        prod = Settings(
            environment="production",
            jwt_secret="prod-secret-value",
            pii_pepper="prod-pepper-value",
        )
        with patch("modules.credit.webhook_routes.settings", prod):
            resp = _post_webhook(client, "http://example.com/hook")
            assert resp.status_code == 422

    @pytest.mark.usefixtures("bypass_auth")
    def test_http_allowed_in_development(self, client):
        """http:// URLs are allowed in development."""
        from modules.credit.config import Settings

        dev = Settings(environment="development")
        with patch("modules.credit.webhook_routes.settings", dev):
            resp = _post_webhook(client, "http://example.com/hook")
            assert resp.status_code == 201

    @pytest.mark.usefixtures("bypass_auth")
    def test_https_allowed_in_production(self, client):
        """https:// URLs must always be accepted in production."""
        from modules.credit.config import Settings

        prod = Settings(
            environment="production",
            jwt_secret="prod-secret-value",
            pii_pepper="prod-pepper-value",
        )
        with patch("modules.credit.webhook_routes.settings", prod):
            resp = _post_webhook(client, "https://example.com/hook")
            assert resp.status_code == 201


# --- DNS rebinding protection at delivery time ---


class TestDnsRebindingProtection:
    """T25.2: _resolve_and_check blocks private IPs resolved at delivery time."""

    def test_loopback_ip_blocked(self) -> None:
        """127.0.0.1 resolved at delivery time should raise ValueError."""
        fake_addrinfo = [(socket.AF_INET, 0, 0, "", ("127.0.0.1", 0))]
        with patch(
            "modules.credit.webhook_delivery.socket.getaddrinfo",
            return_value=fake_addrinfo,
        ):
            with pytest.raises(ValueError, match="non-global"):
                _resolve_and_check("https://evil.com/hook")

    def test_private_ip_blocked(self) -> None:
        """192.168.1.1 resolved at delivery time should raise ValueError."""
        fake_addrinfo = [(socket.AF_INET, 0, 0, "", ("192.168.1.1", 0))]
        with patch(
            "modules.credit.webhook_delivery.socket.getaddrinfo",
            return_value=fake_addrinfo,
        ):
            with pytest.raises(ValueError, match="non-global"):
                _resolve_and_check("https://evil.com/hook")

    def test_link_local_blocked(self) -> None:
        """169.254.169.254 (cloud metadata) should raise ValueError."""
        fake_addrinfo = [(socket.AF_INET, 0, 0, "", ("169.254.169.254", 0))]
        with patch(
            "modules.credit.webhook_delivery.socket.getaddrinfo",
            return_value=fake_addrinfo,
        ):
            with pytest.raises(ValueError, match="non-global"):
                _resolve_and_check("https://evil.com/hook")

    def test_ipv6_loopback_blocked(self) -> None:
        """::1 resolved at delivery time should raise ValueError."""
        fake_addrinfo = [(socket.AF_INET6, 0, 0, "", ("::1", 0, 0, 0))]
        with patch(
            "modules.credit.webhook_delivery.socket.getaddrinfo",
            return_value=fake_addrinfo,
        ):
            with pytest.raises(ValueError, match="non-global"):
                _resolve_and_check("https://evil.com/hook")

    def test_dns_resolution_failure_raises(self) -> None:
        """DNS resolution failure (gaierror) should raise ValueError."""
        with patch(
            "modules.credit.webhook_delivery.socket.getaddrinfo",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            with pytest.raises(ValueError, match="DNS resolution failed"):
                _resolve_and_check("https://nonexistent.example.com/hook")
