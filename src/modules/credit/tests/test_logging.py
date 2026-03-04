"""Tests for structured logging and request ID middleware — TDD."""

import pytest
from fastapi.testclient import TestClient


class TestGetLogger:
    """Test structured logger factory."""

    def test_returns_structlog_logger(self):
        from modules.credit.logging_config import get_logger

        log = get_logger()
        assert hasattr(log, "info")
        assert hasattr(log, "warning")
        assert hasattr(log, "error")

    def test_named_logger(self):
        from modules.credit.logging_config import get_logger

        log = get_logger("my.module")
        assert log is not None

    def test_configure_json_output(self):
        from modules.credit.logging_config import configure_logging

        configure_logging(json_output=True)  # covers JSON renderer branch

    def test_configure_console_output(self):
        from modules.credit.logging_config import configure_logging

        configure_logging(json_output=False)  # covers ConsoleRenderer branch


class TestRequestIdMiddleware:
    """Test X-Request-ID middleware."""

    @pytest.fixture
    def client(self):
        from modules.credit.router import app

        return TestClient(app)

    def test_response_has_request_id_header(self, client):
        response = client.get("/health")
        assert "x-request-id" in response.headers

    def test_request_id_is_uuid_format(self, client):
        import uuid

        response = client.get("/health")
        rid = response.headers["x-request-id"]
        uuid.UUID(rid)  # raises if not valid UUID

    def test_client_provided_request_id_is_used(self, client):
        response = client.get("/health", headers={"X-Request-ID": "custom-id-123"})
        assert response.headers["x-request-id"] == "custom-id-123"

    def test_different_requests_get_different_ids(self, client):
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


class TestRequestIdValidation:
    """Test that X-Request-ID header is validated against injection attacks."""

    @pytest.fixture
    def client(self):
        from modules.credit.router import app

        return TestClient(app)

    def test_rejects_newlines(self, client):
        """Request-ID containing newlines should be replaced with a generated UUID."""
        import uuid

        response = client.get(
            "/health", headers={"X-Request-ID": "bad-id\r\nInjected-Header: pwned"}
        )
        rid = response.headers["x-request-id"]
        assert "\r" not in rid
        assert "\n" not in rid
        # Should be a valid UUID (generated replacement)
        uuid.UUID(rid)

    def test_rejects_special_chars(self, client):
        """Request-ID with special chars (not alphanumeric/hyphens) is replaced."""
        import uuid

        response = client.get(
            "/health", headers={"X-Request-ID": "id; DROP TABLE users;--"}
        )
        rid = response.headers["x-request-id"]
        # Should be replaced with a generated UUID
        uuid.UUID(rid)

    def test_accepts_valid_alphanumeric(self, client):
        """Valid alphanumeric request ID with hyphens should be accepted."""
        response = client.get(
            "/health",
            headers={"X-Request-ID": "abc-123-DEF-456"},
        )
        assert response.headers["x-request-id"] == "abc-123-DEF-456"

    def test_rejects_overly_long(self, client):
        """Request-ID exceeding 128 characters should be replaced."""
        import uuid

        long_id = "a" * 200
        response = client.get("/health", headers={"X-Request-ID": long_id})
        rid = response.headers["x-request-id"]
        assert len(rid) <= 128
        uuid.UUID(rid)
