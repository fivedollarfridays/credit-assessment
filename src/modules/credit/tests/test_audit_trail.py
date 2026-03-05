"""Tests for compliance audit trail: logging, hashing, querying, retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from modules.credit.audit import (
    AUDIT_RETENTION_DAYS,
    MAX_AUDIT_ENTRIES,
    _audit_entries,
    create_audit_entry,
    get_audit_trail,
    hash_pii,
    purge_audit_trail,
    reset_audit_trail,
)
from modules.credit.retention import purge_by_age
from modules.credit.router import app
from modules.credit.tests.conftest import patch_auth_settings, register_and_login
from modules.credit.user_routes import _users


# ---------------------------------------------------------------------------
# Cycle 0: Shared purge_by_age utility
# ---------------------------------------------------------------------------


class TestPurgeByAge:
    """Tests for shared time-based purge utility."""

    def test_purge_removes_old_records(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        new = datetime.now(timezone.utc).isoformat()
        records = [{"ts": old, "x": 1}, {"ts": new, "x": 2}]
        kept, purged = purge_by_age(records, timestamp_key="ts", max_age_days=365)
        assert purged == 1
        assert len(kept) == 1
        assert kept[0]["x"] == 2

    def test_purge_keeps_unparseable_timestamps(self) -> None:
        records = [{"ts": "not-a-date"}, {"ts": ""}]
        kept, purged = purge_by_age(records, timestamp_key="ts", max_age_days=30)
        assert purged == 0
        assert len(kept) == 2

    def test_purge_empty_list(self) -> None:
        kept, purged = purge_by_age([], timestamp_key="ts", max_age_days=30)
        assert purged == 0
        assert kept == []


# ---------------------------------------------------------------------------
# Cycle 1: PII hashing
# ---------------------------------------------------------------------------


class TestPiiHashing:
    """Tests for PII field hashing in audit records."""

    def test_hash_pii_returns_string(self) -> None:
        result = hash_pii("test@example.com")
        assert isinstance(result, str)

    def test_hash_pii_is_deterministic(self) -> None:
        assert hash_pii("user@test.com") == hash_pii("user@test.com")

    def test_hash_pii_differs_for_different_inputs(self) -> None:
        assert hash_pii("a@test.com") != hash_pii("b@test.com")

    def test_hash_pii_is_not_reversible(self) -> None:
        hashed = hash_pii("sensitive@data.com")
        assert "sensitive" not in hashed
        assert "@" not in hashed


# ---------------------------------------------------------------------------
# Cycle 2: Audit entry creation
# ---------------------------------------------------------------------------


class TestAuditEntryCreation:
    """Tests for creating audit trail entries."""

    def test_create_audit_entry(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="user-1",
            request_summary={"score": 650},
            result_summary={"readiness": 55},
        )
        assert isinstance(entry, dict)

    def test_audit_entry_has_timestamp(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="u1",
            request_summary={},
            result_summary={},
        )
        assert "timestamp" in entry

    def test_audit_entry_has_action(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="u1",
            request_summary={},
            result_summary={},
        )
        assert entry["action"] == "assess"

    def test_audit_entry_hashes_user_id(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="user@example.com",
            request_summary={},
            result_summary={},
        )
        assert entry["user_id_hash"] != "user@example.com"
        assert "user_id_hash" in entry

    def test_audit_entry_includes_request_summary(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="u1",
            request_summary={"score": 700},
            result_summary={},
        )
        assert entry["request_summary"] == {"score": 700}

    def test_audit_entry_includes_result_summary(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="u1",
            request_summary={},
            result_summary={"readiness": 80, "severity": "low"},
        )
        assert entry["result_summary"]["readiness"] == 80

    def test_audit_entry_optional_org_id(self) -> None:
        reset_audit_trail()
        entry = create_audit_entry(
            action="assess",
            user_id="u1",
            request_summary={},
            result_summary={},
            org_id="org-abc",
        )
        assert entry["org_id"] == "org-abc"


# ---------------------------------------------------------------------------
# Cycle 3: Querying audit logs
# ---------------------------------------------------------------------------


class TestAuditQuerying:
    """Tests for querying audit trail entries."""

    def test_get_audit_trail_returns_list(self) -> None:
        reset_audit_trail()
        entries = get_audit_trail()
        assert isinstance(entries, list)

    def test_get_audit_trail_returns_created_entries(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        create_audit_entry(
            action="assess", user_id="u2", request_summary={}, result_summary={}
        )
        entries = get_audit_trail()
        assert len(entries) == 2

    def test_get_audit_trail_filter_by_action(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        create_audit_entry(
            action="export", user_id="u2", request_summary={}, result_summary={}
        )
        entries = get_audit_trail(action="assess")
        assert len(entries) == 1
        assert entries[0]["action"] == "assess"

    def test_get_audit_trail_limit(self) -> None:
        reset_audit_trail()
        for i in range(5):
            create_audit_entry(
                action="assess",
                user_id=f"u{i}",
                request_summary={},
                result_summary={},
            )
        entries = get_audit_trail(limit=3)
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# Cycle 4: Retention policy
# ---------------------------------------------------------------------------


class TestAuditRetention:
    """Tests for audit log retention policy."""

    def test_purge_old_audit_entries(self) -> None:
        reset_audit_trail()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=3000)).isoformat()
        _audit_entries.append(
            {"action": "assess", "timestamp": old_ts, "user_id_hash": "x"}
        )
        purged = purge_audit_trail(max_age_days=2555)  # ~7 years
        assert purged >= 1
        assert len(get_audit_trail()) == 0

    def test_purge_keeps_recent_entries(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        purged = purge_audit_trail(max_age_days=2555)
        assert purged == 0
        assert len(get_audit_trail()) == 1

    def test_default_retention_is_seven_years(self) -> None:
        assert AUDIT_RETENTION_DAYS == 2555

    def test_store_is_bounded(self) -> None:
        reset_audit_trail()
        for i in range(MAX_AUDIT_ENTRIES + 100):
            create_audit_entry(
                action="assess", user_id=f"u{i}", request_summary={}, result_summary={}
            )
        assert len(get_audit_trail()) <= MAX_AUDIT_ENTRIES


# ---------------------------------------------------------------------------
# Cycle 5: Admin audit endpoint
# ---------------------------------------------------------------------------


class TestAuditEndpoint:
    """Tests for admin audit log query endpoint."""

    def _get_admin_token(self, client):
        """Register a user, set admin role, return Bearer token."""
        token = register_and_login(client, "auditadmin@test.com")
        _users["auditadmin@test.com"]["role"] = "admin"
        return token

    def test_audit_endpoint_requires_admin_auth(self) -> None:
        client = TestClient(app)
        with patch_auth_settings():
            resp = client.get("/v1/admin/audit-log")
            assert resp.status_code in (401, 403)

    def test_audit_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        with patch_auth_settings():
            token = self._get_admin_token(client)
            resp = client.get(
                "/v1/admin/audit-log",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_audit_endpoint_returns_list(self) -> None:
        client = TestClient(app)
        with patch_auth_settings():
            token = self._get_admin_token(client)
            data = client.get(
                "/v1/admin/audit-log",
                headers={"Authorization": f"Bearer {token}"},
            ).json()
            assert isinstance(data, dict)
            assert "entries" in data
            assert isinstance(data["entries"], list)

    def test_audit_endpoint_filter_by_action(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        create_audit_entry(
            action="export", user_id="u2", request_summary={}, result_summary={}
        )

        client = TestClient(app)
        with patch_auth_settings():
            token = self._get_admin_token(client)
            data = client.get(
                "/v1/admin/audit-log",
                params={"action": "assess"},
                headers={"Authorization": f"Bearer {token}"},
            ).json()
            assert len(data["entries"]) == 1

    def test_audit_endpoint_with_limit(self) -> None:
        reset_audit_trail()
        for i in range(5):
            create_audit_entry(
                action="assess",
                user_id=f"u{i}",
                request_summary={},
                result_summary={},
            )

        client = TestClient(app)
        with patch_auth_settings():
            token = self._get_admin_token(client)
            data = client.get(
                "/v1/admin/audit-log",
                params={"limit": 2},
                headers={"Authorization": f"Bearer {token}"},
            ).json()
            assert len(data["entries"]) == 2
