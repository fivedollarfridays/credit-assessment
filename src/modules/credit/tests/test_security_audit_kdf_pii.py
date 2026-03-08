"""Tests for MEDIUM severity security audit fixes (T27.3).

A02-2: KDF upgrade from SHA-256 to PBKDF2HMAC
A09-1: PII scrubbing in Sentry before_send and structlog processor
"""

from __future__ import annotations

from unittest.mock import patch


# ---------------------------------------------------------------------------
# A02-2: PBKDF2HMAC KDF upgrade
# ---------------------------------------------------------------------------


class TestPbkdf2KdfUpgrade:
    """crypto.py must use PBKDF2HMAC instead of raw SHA-256."""

    def test_uses_pbkdf2hmac_not_raw_sha256(self) -> None:
        """_get_fernet must use PBKDF2HMAC, not hashlib.sha256 directly."""
        import inspect

        from modules.credit import crypto

        source = inspect.getsource(crypto._get_fernet)
        assert "PBKDF2HMAC" in source, (
            "_get_fernet must use PBKDF2HMAC, found raw SHA-256 instead"
        )

    def test_pbkdf2_uses_sufficient_iterations(self) -> None:
        """PBKDF2HMAC must use at least 100,000 iterations."""
        from modules.credit.crypto import _KDF_ITERATIONS

        assert _KDF_ITERATIONS >= 100_000, (
            f"PBKDF2HMAC iterations must be >= 100,000, got {_KDF_ITERATIONS}"
        )

    def test_encrypt_decrypt_round_trip_with_new_kdf(self) -> None:
        """Encryption/decryption must still work after KDF upgrade."""
        from modules.credit.crypto import decrypt_field, encrypt_field

        # Clear any cached Fernet instances from previous test runs
        from modules.credit.crypto import _get_fernet

        _get_fernet.cache_clear()

        key = "test-kdf-upgrade-key"
        plaintext = "my-webhook-secret-value"
        encrypted = encrypt_field(plaintext, key)
        assert encrypted != plaintext
        assert decrypt_field(encrypted, key) == plaintext

    def test_backward_compat_old_sha256_ciphertexts(self) -> None:
        """Old ciphertexts encrypted with SHA-256 KDF must still decrypt."""
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        from modules.credit.crypto import _get_fernet, decrypt_field

        _get_fernet.cache_clear()

        # Simulate old SHA-256 KDF encryption
        key = "backward-compat-test-key"
        old_digest = hashlib.sha256(key.encode()).digest()
        old_fernet = Fernet(base64.urlsafe_b64encode(old_digest))
        old_ciphertext = old_fernet.encrypt(b"legacy-secret").decode()

        # New decrypt_field must still handle this
        result = decrypt_field(old_ciphertext, key)
        assert result == "legacy-secret"


# ---------------------------------------------------------------------------
# A09-1: Sentry before_send PII scrubbing
# ---------------------------------------------------------------------------


class TestSentryPiiScrubbing:
    """Sentry must scrub PII from events via before_send hook."""

    def test_setup_sentry_includes_before_send(self) -> None:
        """setup_sentry must pass a before_send hook to sentry_sdk.init."""
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn="https://key@sentry.io/123", environment="production")
            call_kwargs = mock_sdk.init.call_args[1]
            assert "before_send" in call_kwargs, (
                "Sentry init missing before_send PII scrubbing hook"
            )
            assert callable(call_kwargs["before_send"])

    def test_before_send_scrubs_email(self) -> None:
        """before_send must redact email addresses from event data."""
        from modules.credit.sentry import _scrub_pii_from_event

        event = {
            "message": "Error for user test@example.com",
            "extra": {"email": "user@domain.org"},
        }
        scrubbed = _scrub_pii_from_event(event, {})
        assert "test@example.com" not in str(scrubbed)
        assert "user@domain.org" not in str(scrubbed)

    def test_before_send_scrubs_jwt(self) -> None:
        """before_send must redact JWT tokens from event data."""
        from modules.credit.sentry import _scrub_pii_from_event

        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        event = {"message": f"Auth failed with token {jwt}"}
        scrubbed = _scrub_pii_from_event(event, {})
        assert jwt not in str(scrubbed)

    def test_before_send_scrubs_api_key(self) -> None:
        """before_send must redact API key prefixes from event data."""
        from modules.credit.sentry import _scrub_pii_from_event

        event = {"message": "Key sk-proj-abc123def456 is invalid"}
        scrubbed = _scrub_pii_from_event(event, {})
        assert "sk-proj-abc123def456" not in str(scrubbed)


# ---------------------------------------------------------------------------
# A09-1: Structlog PII processor
# ---------------------------------------------------------------------------


class TestStructlogPiiProcessor:
    """Structlog must have a processor that redacts PII patterns."""

    def test_pii_processor_redacts_email(self) -> None:
        """PII processor must redact email addresses in log event values."""
        from modules.credit.logging_config import redact_pii

        event_dict = {"event": "login failed", "email": "user@example.com"}
        result = redact_pii(None, None, event_dict)
        assert "user@example.com" not in str(result)

    def test_pii_processor_redacts_nested_email_in_message(self) -> None:
        """PII processor must redact emails embedded in string values."""
        from modules.credit.logging_config import redact_pii

        event_dict = {"event": "Error processing user@test.org request"}
        result = redact_pii(None, None, event_dict)
        assert "user@test.org" not in str(result)

    def test_pii_processor_preserves_non_pii(self) -> None:
        """Non-PII values must pass through unchanged."""
        from modules.credit.logging_config import redact_pii

        event_dict = {"event": "health check", "status": "ok", "count": 42}
        result = redact_pii(None, None, event_dict)
        assert result["event"] == "health check"
        assert result["status"] == "ok"
        assert result["count"] == 42

    def test_pii_processor_in_structlog_pipeline(self) -> None:
        """redact_pii must be included in the structlog processor chain."""
        import inspect

        from modules.credit import logging_config

        source = inspect.getsource(logging_config.configure_logging)
        assert "redact_pii" in source, (
            "redact_pii processor not found in configure_logging pipeline"
        )
