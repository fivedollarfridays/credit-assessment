"""Tests for GDPR/CCPA data rights: consent, export, deletion, retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.data_rights import (
    _user_assessments,
    check_consent,
    delete_user_data,
    export_user_data,
    get_consent_record,
    purge_expired_data,
    record_consent,
    record_user_assessment,
    reset_data_rights,
    withdraw_consent,
)
from modules.credit.router import app


# ---------------------------------------------------------------------------
# Cycle 1: Consent tracking
# ---------------------------------------------------------------------------


class TestConsentTracking:
    """Tests for consent management with version and timestamp."""

    def test_record_consent(self) -> None:
        reset_data_rights()
        record_consent(user_id="u1", consent_version="1.0")

    def test_check_consent_true_when_given(self) -> None:
        reset_data_rights()
        record_consent(user_id="u2", consent_version="1.0")
        assert check_consent(user_id="u2", consent_version="1.0") is True

    def test_check_consent_false_when_not_given(self) -> None:
        reset_data_rights()
        assert check_consent(user_id="u3", consent_version="1.0") is False

    def test_consent_is_version_specific(self) -> None:
        reset_data_rights()
        record_consent(user_id="u4", consent_version="1.0")
        assert check_consent(user_id="u4", consent_version="2.0") is False

    def test_consent_has_timestamp(self) -> None:
        reset_data_rights()
        record_consent(user_id="u5", consent_version="1.0")
        record = get_consent_record(user_id="u5", consent_version="1.0")
        assert record is not None
        assert "consented_at" in record

    def test_withdraw_consent(self) -> None:
        reset_data_rights()
        record_consent(user_id="u6", consent_version="1.0")
        assert check_consent(user_id="u6", consent_version="1.0") is True
        withdraw_consent(user_id="u6", consent_version="1.0")
        assert check_consent(user_id="u6", consent_version="1.0") is False

    def test_withdraw_nonexistent_consent_is_noop(self) -> None:
        reset_data_rights()
        withdraw_consent(user_id="nobody", consent_version="1.0")  # should not raise


# ---------------------------------------------------------------------------
# Cycle 2: Data export
# ---------------------------------------------------------------------------


class TestDataExport:
    """Tests for user data export (right to access)."""

    def test_export_returns_dict(self) -> None:
        reset_data_rights()
        result = export_user_data(user_id="u1")
        assert isinstance(result, dict)

    def test_export_contains_user_id(self) -> None:
        reset_data_rights()
        result = export_user_data(user_id="u1")
        assert result["user_id"] == "u1"

    def test_export_contains_consent_records(self) -> None:
        reset_data_rights()
        record_consent(user_id="u2", consent_version="1.0")
        result = export_user_data(user_id="u2")
        assert "consent_records" in result
        assert len(result["consent_records"]) == 1

    def test_export_contains_assessments(self) -> None:
        reset_data_rights()
        result = export_user_data(user_id="u1")
        assert "assessments" in result
        assert isinstance(result["assessments"], list)

    def test_export_contains_exported_at(self) -> None:
        reset_data_rights()
        result = export_user_data(user_id="u1")
        assert "exported_at" in result

    def test_export_stores_user_assessment(self) -> None:
        reset_data_rights()
        record_user_assessment(user_id="u3", assessment={"score": 700, "band": "good"})
        result = export_user_data(user_id="u3")
        assert len(result["assessments"]) == 1
        assert result["assessments"][0]["score"] == 700


# ---------------------------------------------------------------------------
# Cycle 3: Data deletion (right to be forgotten)
# ---------------------------------------------------------------------------


class TestDataDeletion:
    """Tests for user data deletion with cascade."""

    def test_delete_removes_consent(self) -> None:
        reset_data_rights()
        record_consent(user_id="d1", consent_version="1.0")
        delete_user_data(user_id="d1")
        assert check_consent(user_id="d1", consent_version="1.0") is False

    def test_delete_removes_assessments(self) -> None:
        reset_data_rights()
        record_user_assessment(user_id="d2", assessment={"score": 650})
        delete_user_data(user_id="d2")
        result = export_user_data(user_id="d2")
        assert len(result["assessments"]) == 0

    def test_delete_returns_summary(self) -> None:
        reset_data_rights()
        record_consent(user_id="d3", consent_version="1.0")
        record_user_assessment(user_id="d3", assessment={"score": 600})
        summary = delete_user_data(user_id="d3")
        assert summary["user_id"] == "d3"
        assert summary["consent_records_deleted"] >= 1
        assert summary["assessments_deleted"] >= 1
        assert "deleted_at" in summary

    def test_delete_nonexistent_user_returns_zero_counts(self) -> None:
        reset_data_rights()
        summary = delete_user_data(user_id="ghost")
        assert summary["consent_records_deleted"] == 0
        assert summary["assessments_deleted"] == 0

    def test_delete_also_removes_org_assessments(self) -> None:
        """GDPR: delete_user_data must also purge tenant._org_assessments."""
        from modules.credit.tenant import _org_assessments

        reset_data_rights()
        _org_assessments.clear()
        _org_assessments["org-1"].append({"user_id": "d-org", "score": 700})
        _org_assessments["org-1"].append({"user_id": "other", "score": 800})
        _org_assessments["org-2"].append({"user_id": "d-org", "score": 600})

        summary = delete_user_data(user_id="d-org")
        assert summary["org_assessments_deleted"] == 2
        # Only "other" remains in org-1
        assert len(_org_assessments["org-1"]) == 1
        assert _org_assessments["org-1"][0]["user_id"] == "other"
        # org-2 should be cleaned up entirely
        assert "org-2" not in _org_assessments
        _org_assessments.clear()

    def test_delete_org_assessments_empty_returns_zero(self) -> None:
        """No org assessments to delete returns 0 for org_assessments_deleted."""
        from modules.credit.tenant import _org_assessments

        reset_data_rights()
        _org_assessments.clear()
        summary = delete_user_data(user_id="nobody")
        assert summary["org_assessments_deleted"] == 0
        _org_assessments.clear()


# ---------------------------------------------------------------------------
# Cycle 4: Data retention / purge
# ---------------------------------------------------------------------------


class TestDataRetention:
    """Tests for automatic data retention purge."""

    def test_purge_removes_old_assessments(self) -> None:
        reset_data_rights()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        _user_assessments.setdefault("old-user", []).append(
            {"score": 500, "recorded_at": old_ts}
        )
        purged = purge_expired_data(max_age_days=365)
        assert purged >= 1
        result = export_user_data(user_id="old-user")
        assert len(result["assessments"]) == 0

    def test_purge_keeps_recent_assessments(self) -> None:
        reset_data_rights()
        record_user_assessment(user_id="recent", assessment={"score": 750})
        purged = purge_expired_data(max_age_days=365)
        assert purged == 0
        result = export_user_data(user_id="recent")
        assert len(result["assessments"]) == 1

    def test_purge_returns_count(self) -> None:
        reset_data_rights()
        count = purge_expired_data(max_age_days=365)
        assert isinstance(count, int)
        assert count >= 0


# ---------------------------------------------------------------------------
# Cycle 5: API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("bypass_auth")
class TestDataRightsEndpoints:
    """Tests for GDPR/CCPA API endpoints."""

    def test_export_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.get("/v1/user/data-export", params={"user_id": "test-user"})
        assert resp.status_code == 200

    def test_export_endpoint_returns_user_data(self) -> None:
        client = TestClient(app)
        data = client.get(
            "/v1/user/data-export", params={"user_id": "test-user"}
        ).json()
        assert data["user_id"] == "test-user"
        assert "consent_records" in data
        assert "assessments" in data

    def test_delete_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.delete("/v1/user/data", params={"user_id": "test-user"})
        assert resp.status_code == 200

    def test_delete_endpoint_returns_summary(self) -> None:
        client = TestClient(app)
        data = client.delete("/v1/user/data", params={"user_id": "test-user"}).json()
        assert data["user_id"] == "test-user"
        assert "deleted_at" in data

    def test_consent_endpoint_records_consent(self) -> None:
        reset_data_rights()
        client = TestClient(app)
        resp = client.post(
            "/v1/user/consent",
            json={"user_id": "test-user", "consent_version": "1.0"},
        )
        assert resp.status_code == 200
        assert check_consent(user_id="test-user", consent_version="1.0") is True

    def test_data_endpoints_require_auth_when_configured(self) -> None:
        from modules.credit.assess_routes import verify_auth

        locked = Settings(api_key="secret-key")
        # Remove the dependency override so the real verify_auth runs
        app.dependency_overrides.pop(verify_auth, None)
        try:
            client = TestClient(app)
            with patch("modules.credit.assess_routes.settings", locked):
                assert client.get("/v1/user/data-export").status_code == 403
                assert client.delete("/v1/user/data").status_code == 403
                assert (
                    client.post(
                        "/v1/user/consent",
                        json={"user_id": "x", "consent_version": "1.0"},
                    ).status_code
                    == 403
                )
        finally:
            app.dependency_overrides[verify_auth] = lambda: "test-user"


# ---------------------------------------------------------------------------
# Cycle 6: IDOR protection — ownership enforcement
# ---------------------------------------------------------------------------


class TestIdorProtection:
    """Tests for IDOR protection: users cannot access other users' data."""

    @pytest.fixture(autouse=True)
    def _setup_users(self):
        """Set up test users and auth overrides."""
        from modules.credit.password import hash_password
        from modules.credit.user_routes import _users

        _users["user-a@test.com"] = {
            "email": "user-a@test.com",
            "password_hash": hash_password("Passw0rd!"),
            "is_active": True,
            "role": "viewer",
            "org_id": "org-a",
        }
        _users["admin@idor.com"] = {
            "email": "admin@idor.com",
            "password_hash": hash_password("Passw0rd!"),
            "is_active": True,
            "role": "admin",
            "org_id": "org-admin",
        }
        yield
        _users.pop("user-a@test.com", None)
        _users.pop("admin@idor.com", None)

    def _override_identity(self, identity: str):
        from modules.credit.assess_routes import verify_auth

        app.dependency_overrides[verify_auth] = lambda: identity

    def test_export_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        client = TestClient(app)
        resp = client.get("/v1/user/data-export", params={"user_id": "user-b"})
        assert resp.status_code == 403
        assert "another user" in resp.json()["detail"].lower()

    def test_export_allows_admin_override(self) -> None:
        self._override_identity("admin@idor.com")
        client = TestClient(app)
        resp = client.get("/v1/user/data-export", params={"user_id": "user-b"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user-b"

    def test_delete_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        client = TestClient(app)
        resp = client.delete("/v1/user/data", params={"user_id": "user-b"})
        assert resp.status_code == 403

    def test_consent_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        client = TestClient(app)
        resp = client.post(
            "/v1/user/consent",
            json={"user_id": "user-b", "consent_version": "1.0"},
        )
        assert resp.status_code == 403
