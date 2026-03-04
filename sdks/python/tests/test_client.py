"""Tests for Credit Assessment Python SDK client."""

from __future__ import annotations

import pytest

from credit_assessment_client.client import CreditAssessmentClient
from credit_assessment_client.auth import BearerAuth, ApiKeyAuth
from credit_assessment_client.models import (
    AccountSummary,
    CreditProfile,
    AssessmentResult,
)
from credit_assessment_client.exceptions import (
    AuthenticationError,
    ApiError,
    RateLimitError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Client instantiation
# ---------------------------------------------------------------------------


class TestClientInit:
    """Tests for client construction and configuration."""

    def test_client_with_base_url(self) -> None:
        client = CreditAssessmentClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_client_strips_trailing_slash(self) -> None:
        client = CreditAssessmentClient(base_url="https://api.example.com/")
        assert client.base_url == "https://api.example.com"

    def test_client_with_api_key_auth(self) -> None:
        client = CreditAssessmentClient(
            base_url="https://api.example.com",
            auth=ApiKeyAuth("my-key"),
        )
        assert client.auth is not None

    def test_client_with_bearer_auth(self) -> None:
        client = CreditAssessmentClient(
            base_url="https://api.example.com",
            auth=BearerAuth("my-token"),
        )
        assert client.auth is not None

    def test_client_default_timeout(self) -> None:
        client = CreditAssessmentClient(base_url="https://api.example.com")
        assert client.timeout == 30.0

    def test_client_custom_timeout(self) -> None:
        client = CreditAssessmentClient(
            base_url="https://api.example.com", timeout=60.0
        )
        assert client.timeout == 60.0


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


class TestAuthHelpers:
    """Tests for authentication helper classes."""

    def test_api_key_auth_headers(self) -> None:
        auth = ApiKeyAuth("secret-key")
        headers = auth.headers()
        assert headers == {"X-API-Key": "secret-key"}

    def test_bearer_auth_headers(self) -> None:
        auth = BearerAuth("my-jwt-token")
        headers = auth.headers()
        assert headers == {"Authorization": "Bearer my-jwt-token"}

    def test_api_key_auth_repr_hides_key(self) -> None:
        auth = ApiKeyAuth("secret-key")
        assert "secret-key" not in repr(auth)

    def test_bearer_auth_repr_hides_token(self) -> None:
        auth = BearerAuth("my-jwt-token")
        assert "my-jwt-token" not in repr(auth)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModels:
    """Tests for SDK request/response models."""

    def test_account_summary_creation(self) -> None:
        summary = AccountSummary(total_accounts=8, open_accounts=6)
        assert summary.total_accounts == 8
        assert summary.open_accounts == 6
        assert summary.closed_accounts == 0

    def test_credit_profile_creation(self) -> None:
        profile = CreditProfile(
            current_score=740,
            score_band="good",
            overall_utilization=20.0,
            account_summary=AccountSummary(total_accounts=8, open_accounts=6),
            payment_history_pct=98.0,
            average_account_age_months=72,
        )
        assert profile.current_score == 740
        assert profile.score_band == "good"

    def test_credit_profile_to_dict(self) -> None:
        profile = CreditProfile(
            current_score=740,
            score_band="good",
            overall_utilization=20.0,
            account_summary=AccountSummary(total_accounts=8, open_accounts=6),
            payment_history_pct=98.0,
            average_account_age_months=72,
        )
        d = profile.to_dict()
        assert isinstance(d, dict)
        assert d["current_score"] == 740
        assert d["account_summary"]["total_accounts"] == 8

    def test_assessment_result_from_dict(self) -> None:
        data = {
            "barrier_severity": "low",
            "barrier_details": [],
            "readiness": {"score": 85, "fico_score": 740, "score_band": "good"},
            "thresholds": [],
            "dispute_pathway": {"steps": [], "total_estimated_days": 0},
            "eligibility": [],
            "disclaimer": "Test disclaimer",
        }
        result = AssessmentResult.from_dict(data)
        assert result.barrier_severity == "low"
        assert result.readiness["score"] == 85

    def test_assessment_result_readiness_score(self) -> None:
        data = {
            "barrier_severity": "low",
            "readiness": {"score": 85, "fico_score": 740, "score_band": "good"},
        }
        result = AssessmentResult.from_dict(data)
        assert result.readiness_score == 85


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for SDK exception hierarchy."""

    def test_api_error_has_status_code(self) -> None:
        err = ApiError("Server error", status_code=500)
        assert err.status_code == 500
        assert "Server error" in str(err)

    def test_auth_error_is_api_error(self) -> None:
        err = AuthenticationError("Invalid token")
        assert isinstance(err, ApiError)
        assert err.status_code == 401

    def test_rate_limit_error_has_retry_after(self) -> None:
        err = RateLimitError("Too many requests", retry_after=30)
        assert isinstance(err, ApiError)
        assert err.status_code == 429
        assert err.retry_after == 30

    def test_validation_error_is_api_error(self) -> None:
        err = ValidationError("Invalid input", details=[{"field": "score"}])
        assert isinstance(err, ApiError)
        assert err.status_code == 422
        assert len(err.details) == 1
