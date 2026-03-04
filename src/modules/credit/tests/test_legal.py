"""Tests for privacy policy, terms of service, and legal document management."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.credit.legal import (
    check_tos_accepted,
    get_privacy_policy,
    get_terms_of_service,
    get_tos_acceptance,
    record_tos_acceptance,
    reset_acceptances,
)
from modules.credit.router import app


# ---------------------------------------------------------------------------
# Cycle 1: Privacy policy content
# ---------------------------------------------------------------------------


class TestPrivacyPolicy:
    """Tests for privacy policy document."""

    def test_privacy_policy_exists(self) -> None:
        doc = get_privacy_policy()
        assert isinstance(doc, dict)

    def test_privacy_policy_has_version(self) -> None:
        doc = get_privacy_policy()
        assert "version" in doc
        assert isinstance(doc["version"], str)

    def test_privacy_policy_has_effective_date(self) -> None:
        doc = get_privacy_policy()
        assert "effective_date" in doc

    def test_privacy_policy_has_content(self) -> None:
        doc = get_privacy_policy()
        assert "content" in doc
        assert len(doc["content"]) > 200

    def test_privacy_policy_covers_data_collection(self) -> None:
        content = get_privacy_policy()["content"].lower()
        assert "collect" in content

    def test_privacy_policy_covers_data_use(self) -> None:
        content = get_privacy_policy()["content"].lower()
        assert "use" in content

    def test_privacy_policy_covers_data_retention(self) -> None:
        content = get_privacy_policy()["content"].lower()
        assert "retain" in content or "retention" in content

    def test_privacy_policy_covers_data_sharing(self) -> None:
        content = get_privacy_policy()["content"].lower()
        assert "share" in content or "third part" in content


# ---------------------------------------------------------------------------
# Cycle 2: Terms of service content
# ---------------------------------------------------------------------------


class TestTermsOfService:
    """Tests for terms of service document."""

    def test_terms_exists(self) -> None:
        doc = get_terms_of_service()
        assert isinstance(doc, dict)

    def test_terms_has_version(self) -> None:
        doc = get_terms_of_service()
        assert "version" in doc

    def test_terms_has_effective_date(self) -> None:
        doc = get_terms_of_service()
        assert "effective_date" in doc

    def test_terms_has_content(self) -> None:
        doc = get_terms_of_service()
        assert "content" in doc
        assert len(doc["content"]) > 200

    def test_terms_covers_api_usage(self) -> None:
        content = get_terms_of_service()["content"].lower()
        assert "api" in content

    def test_terms_covers_liability(self) -> None:
        content = get_terms_of_service()["content"].lower()
        assert "liability" in content or "liable" in content

    def test_terms_covers_termination(self) -> None:
        content = get_terms_of_service()["content"].lower()
        assert "terminat" in content


# ---------------------------------------------------------------------------
# Cycle 3: ToS acceptance tracking
# ---------------------------------------------------------------------------


class TestTosAcceptance:
    """Tests for Terms of Service acceptance tracking."""

    def test_record_acceptance(self) -> None:
        reset_acceptances()
        record_tos_acceptance(user_id="user-1", tos_version="1.0")

    def test_check_acceptance_returns_true_when_accepted(self) -> None:
        reset_acceptances()
        record_tos_acceptance(user_id="user-2", tos_version="1.0")
        assert check_tos_accepted(user_id="user-2", tos_version="1.0") is True

    def test_check_acceptance_returns_false_when_not_accepted(self) -> None:
        reset_acceptances()
        assert check_tos_accepted(user_id="user-3", tos_version="1.0") is False

    def test_acceptance_is_version_specific(self) -> None:
        reset_acceptances()
        record_tos_acceptance(user_id="user-4", tos_version="1.0")
        assert check_tos_accepted(user_id="user-4", tos_version="1.0") is True
        assert check_tos_accepted(user_id="user-4", tos_version="2.0") is False

    def test_acceptance_records_timestamp(self) -> None:
        reset_acceptances()
        record_tos_acceptance(user_id="user-5", tos_version="1.0")
        record = get_tos_acceptance(user_id="user-5", tos_version="1.0")
        assert record is not None
        assert "accepted_at" in record


# ---------------------------------------------------------------------------
# Cycle 4: /legal/privacy and /legal/terms endpoints
# ---------------------------------------------------------------------------


class TestLegalEndpoints:
    """Tests for legal document API endpoints."""

    def test_privacy_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.get("/legal/privacy")
        assert resp.status_code == 200

    def test_privacy_endpoint_returns_document(self) -> None:
        client = TestClient(app)
        data = client.get("/legal/privacy").json()
        assert "version" in data
        assert "content" in data

    def test_terms_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.get("/legal/terms")
        assert resp.status_code == 200

    def test_terms_endpoint_returns_document(self) -> None:
        client = TestClient(app)
        data = client.get("/legal/terms").json()
        assert "version" in data
        assert "content" in data

    def test_v1_privacy_endpoint(self) -> None:
        client = TestClient(app)
        resp = client.get("/v1/legal/privacy")
        assert resp.status_code == 200

    def test_v1_terms_endpoint(self) -> None:
        client = TestClient(app)
        resp = client.get("/v1/legal/terms")
        assert resp.status_code == 200

    def test_legal_endpoints_no_auth_required(self) -> None:
        client = TestClient(app)
        assert client.get("/legal/privacy").status_code == 200
        assert client.get("/legal/terms").status_code == 200
