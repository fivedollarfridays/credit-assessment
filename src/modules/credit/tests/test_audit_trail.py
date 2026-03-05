"""Tests for compliance audit trail: logging, hashing, querying, retention."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from modules.credit.audit import (
    AUDIT_RETENTION_DAYS,
    count_audit_entries,
    create_audit_entry,
    get_audit_trail,
    hash_pii,
    purge_audit_trail,
)
from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.retention import purge_by_age
from modules.credit.router import app
from modules.credit.tests.conftest import create_test_user, patch_auth_settings


@pytest.fixture
def db_factory():
    """Create in-memory database with tables for each test."""
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


# ---------------------------------------------------------------------------
# Cycle 0: Shared purge_by_age utility
# ---------------------------------------------------------------------------


class TestPurgeByAge:
    """Tests for shared time-based purge utility."""

    def test_purge_removes_old_records(self) -> None:
        from datetime import datetime, timedelta, timezone

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
# Cycle 2: Audit entry creation (DB-backed)
# ---------------------------------------------------------------------------


class TestAuditEntryCreation:
    """Tests for creating audit trail entries via database."""

    def test_create_audit_entry(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="user-1",
                    request_summary={"score": 650},
                    result_summary={"readiness": 55},
                )
                assert isinstance(entry, dict)

        asyncio.run(_run())

    def test_audit_entry_has_timestamp(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                assert "timestamp" in entry

        asyncio.run(_run())

    def test_audit_entry_has_action(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                assert entry["action"] == "assess"

        asyncio.run(_run())

    def test_audit_entry_hashes_user_id(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="user@example.com",
                    request_summary={},
                    result_summary={},
                )
                assert entry["user_id_hash"] != "user@example.com"
                assert "user_id_hash" in entry

        asyncio.run(_run())

    def test_audit_entry_includes_request_summary(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={"score": 700},
                    result_summary={},
                )
                assert entry["request_summary"] == {"score": 700}

        asyncio.run(_run())

    def test_audit_entry_includes_result_summary(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={"readiness": 80, "severity": "low"},
                )
                assert entry["result_summary"]["readiness"] == 80

        asyncio.run(_run())

    def test_audit_entry_optional_org_id(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entry = await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                    org_id="org-abc",
                )
                assert entry["org_id"] == "org-abc"

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 3: Querying audit logs
# ---------------------------------------------------------------------------


class TestAuditQuerying:
    """Tests for querying audit trail entries."""

    def test_get_audit_trail_returns_list(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                entries = await get_audit_trail(session)
                assert isinstance(entries, list)

        asyncio.run(_run())

    def test_get_audit_trail_returns_created_entries(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u2",
                    request_summary={},
                    result_summary={},
                )
                entries = await get_audit_trail(session)
                assert len(entries) == 2

        asyncio.run(_run())

    def test_get_audit_trail_filter_by_action(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                await create_audit_entry(
                    session,
                    action="export",
                    user_id="u2",
                    request_summary={},
                    result_summary={},
                )
                entries = await get_audit_trail(session, action="assess")
                assert len(entries) == 1
                assert entries[0]["action"] == "assess"

        asyncio.run(_run())

    def test_get_audit_trail_limit(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                for i in range(5):
                    await create_audit_entry(
                        session,
                        action="assess",
                        user_id=f"u{i}",
                        request_summary={},
                        result_summary={},
                    )
                entries = await get_audit_trail(session, limit=3)
                assert len(entries) == 3

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 4: Retention policy
# ---------------------------------------------------------------------------


class TestAuditRetention:
    """Tests for audit log retention policy."""

    def test_purge_keeps_recent_entries(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                purged = await purge_audit_trail(session, max_age_days=2555)
                assert purged == 0
                entries = await get_audit_trail(session)
                assert len(entries) == 1

        asyncio.run(_run())

    def test_default_retention_is_seven_years(self) -> None:
        assert AUDIT_RETENTION_DAYS == 2555

    def test_count_returns_correct_value(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                assert await count_audit_entries(session) == 0
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                assert await count_audit_entries(session) == 1

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 5: Admin audit endpoint
# ---------------------------------------------------------------------------


class TestAuditEndpoint:
    """Tests for admin audit log query endpoint."""

    def _get_admin_headers(self):
        """Create admin user and return Bearer headers."""
        from modules.credit.auth import create_access_token
        from modules.credit.tests.conftest import _TEST_SETTINGS

        return {
            "Authorization": f"Bearer {create_access_token(subject='auditadmin@test.com', secret=_TEST_SETTINGS.jwt_secret, algorithm=_TEST_SETTINGS.jwt_algorithm, expire_minutes=30)}"
        }

    def test_audit_endpoint_requires_admin_auth(self) -> None:
        with patch_auth_settings():
            with TestClient(app) as client:
                resp = client.get("/v1/admin/audit-log")
                assert resp.status_code in (401, 403)

    def test_audit_endpoint_returns_200(self) -> None:
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "auditadmin@test.com", role="admin")
                headers = self._get_admin_headers()
                resp = client.get("/v1/admin/audit-log", headers=headers)
                assert resp.status_code == 200

    def test_audit_endpoint_returns_list(self) -> None:
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "auditadmin@test.com", role="admin")
                headers = self._get_admin_headers()
                data = client.get("/v1/admin/audit-log", headers=headers).json()
                assert isinstance(data, dict)
                assert "entries" in data
                assert isinstance(data["entries"], list)

    def test_audit_endpoint_with_limit(self) -> None:
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "auditadmin@test.com", role="admin")
                headers = self._get_admin_headers()
                data = client.get(
                    "/v1/admin/audit-log",
                    params={"limit": 2},
                    headers=headers,
                ).json()
                assert isinstance(data["entries"], list)
