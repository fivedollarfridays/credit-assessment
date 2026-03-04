"""Tests for GDPR/CCPA data rights: consent, export, deletion, retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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
        data = client.delete("/v1/user/data", params={"user_id": "del-user"}).json()
        assert data["user_id"] == "del-user"
        assert "deleted_at" in data

    def test_consent_endpoint_records_consent(self) -> None:
        reset_data_rights()
        client = TestClient(app)
        resp = client.post(
            "/v1/user/consent",
            json={"user_id": "c-user", "consent_version": "1.0"},
        )
        assert resp.status_code == 200
        assert check_consent(user_id="c-user", consent_version="1.0") is True

    def test_data_endpoints_require_auth_when_configured(self) -> None:
        locked = Settings(api_key="secret-key")
        client = TestClient(app)
        with patch("modules.credit.assess_routes.settings", locked):
            assert (
                client.get("/v1/user/data-export", params={"user_id": "x"}).status_code
                == 403
            )
            assert (
                client.delete("/v1/user/data", params={"user_id": "x"}).status_code
                == 403
            )
            assert (
                client.post(
                    "/v1/user/consent", json={"user_id": "x", "consent_version": "1.0"}
                ).status_code
                == 403
            )
