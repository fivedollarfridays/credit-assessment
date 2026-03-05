"""Tests for GDPR/CCPA data rights: consent, export, deletion, retention."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.data_rights import (
    check_consent,
    delete_user_data,
    export_user_data,
    get_consent_record,
    purge_expired_data,
    record_consent,
    record_user_assessment,
    withdraw_consent,
)
from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base, UserAssessment
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
# Cycle 1: Consent tracking
# ---------------------------------------------------------------------------


class TestConsentTracking:
    """Tests for consent management with version and timestamp."""

    def test_record_consent(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u1", consent_version="1.0")

        asyncio.run(_run())

    def test_check_consent_true_when_given(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u2", consent_version="1.0")
                assert (
                    await check_consent(session, user_id="u2", consent_version="1.0")
                    is True
                )

        asyncio.run(_run())

    def test_check_consent_false_when_not_given(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                assert (
                    await check_consent(session, user_id="u3", consent_version="1.0")
                    is False
                )

        asyncio.run(_run())

    def test_consent_is_version_specific(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u4", consent_version="1.0")
                assert (
                    await check_consent(session, user_id="u4", consent_version="2.0")
                    is False
                )

        asyncio.run(_run())

    def test_consent_has_timestamp(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u5", consent_version="1.0")
                record = await get_consent_record(
                    session, user_id="u5", consent_version="1.0"
                )
                assert record is not None
                assert "consented_at" in record

        asyncio.run(_run())

    def test_withdraw_consent(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u6", consent_version="1.0")
                assert (
                    await check_consent(session, user_id="u6", consent_version="1.0")
                    is True
                )
                await withdraw_consent(session, user_id="u6", consent_version="1.0")
                assert (
                    await check_consent(session, user_id="u6", consent_version="1.0")
                    is False
                )

        asyncio.run(_run())

    def test_withdraw_nonexistent_consent_is_noop(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await withdraw_consent(session, user_id="nobody", consent_version="1.0")

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 2: Data export
# ---------------------------------------------------------------------------


class TestDataExport:
    """Tests for user data export (right to access)."""

    def test_export_returns_dict(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                result = await export_user_data(session, user_id="u1")
                assert isinstance(result, dict)

        asyncio.run(_run())

    def test_export_contains_user_id(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                result = await export_user_data(session, user_id="u1")
                assert result["user_id"] == "u1"

        asyncio.run(_run())

    def test_export_contains_consent_records(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="u2", consent_version="1.0")
                result = await export_user_data(session, user_id="u2")
                assert "consent_records" in result
                assert len(result["consent_records"]) == 1

        asyncio.run(_run())

    def test_export_contains_assessments(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                result = await export_user_data(session, user_id="u1")
                assert "assessments" in result
                assert isinstance(result["assessments"], list)

        asyncio.run(_run())

    def test_export_contains_exported_at(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                result = await export_user_data(session, user_id="u1")
                assert "exported_at" in result

        asyncio.run(_run())

    def test_export_stores_user_assessment(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_user_assessment(
                    session,
                    user_id="u3",
                    assessment={"score": 700, "band": "good"},
                )
                result = await export_user_data(session, user_id="u3")
                assert len(result["assessments"]) == 1
                assert result["assessments"][0]["score"] == 700

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 3: Data deletion (right to be forgotten)
# ---------------------------------------------------------------------------


class TestDataDeletion:
    """Tests for user data deletion with cascade."""

    def test_delete_removes_consent(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="d1", consent_version="1.0")
                await delete_user_data(session, user_id="d1")
                assert (
                    await check_consent(session, user_id="d1", consent_version="1.0")
                    is False
                )

        asyncio.run(_run())

    def test_delete_removes_assessments(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_user_assessment(
                    session, user_id="d2", assessment={"score": 650}
                )
                await delete_user_data(session, user_id="d2")
                result = await export_user_data(session, user_id="d2")
                assert len(result["assessments"]) == 0

        asyncio.run(_run())

    def test_delete_returns_summary(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_consent(session, user_id="d3", consent_version="1.0")
                await record_user_assessment(
                    session, user_id="d3", assessment={"score": 600}
                )
                summary = await delete_user_data(session, user_id="d3")
                assert summary["user_id"] == "d3"
                assert summary["consent_records_deleted"] >= 1
                assert summary["assessments_deleted"] >= 1
                assert "deleted_at" in summary

        asyncio.run(_run())

    def test_delete_nonexistent_user_returns_zero_counts(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                summary = await delete_user_data(session, user_id="ghost")
                assert summary["consent_records_deleted"] == 0
                assert summary["assessments_deleted"] == 0

        asyncio.run(_run())

    def test_delete_also_removes_db_assessments(self, db_factory) -> None:
        """GDPR: delete_user_data removes DB assessment records by user_id."""
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    user_id="d-org",
                    org_id="org-1",
                )
                await repo.save_assessment(
                    credit_score=600,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                    user_id="d-org",
                    org_id="org-2",
                )
                summary = await delete_user_data(session, user_id="d-org")
                remaining = await repo.get_by_user_id("d-org")
                return summary, remaining

        summary, remaining = asyncio.run(_run())
        assert summary["db_assessments_deleted"] == 2
        assert len(remaining) == 0

    def test_delete_org_assessments_empty_returns_zero(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                summary = await delete_user_data(session, user_id="nobody")
                return summary

        summary = asyncio.run(_run())
        assert summary["db_assessments_deleted"] == 0


# ---------------------------------------------------------------------------
# Cycle 4: Data retention / purge
# ---------------------------------------------------------------------------


class TestDataRetention:
    """Tests for automatic data retention purge."""

    def test_purge_removes_old_assessments(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                # Manually insert an old record
                old_ts = datetime.now(timezone.utc) - timedelta(days=400)
                session.add(
                    UserAssessment(
                        user_id="old-user",
                        assessment_data={"score": 500},
                        recorded_at=old_ts,
                    )
                )
                await session.commit()
                purged = await purge_expired_data(session, max_age_days=365)
                assert purged >= 1
                result = await export_user_data(session, user_id="old-user")
                assert len(result["assessments"]) == 0

        asyncio.run(_run())

    def test_purge_keeps_recent_assessments(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                await record_user_assessment(
                    session, user_id="recent", assessment={"score": 750}
                )
                purged = await purge_expired_data(session, max_age_days=365)
                assert purged == 0
                result = await export_user_data(session, user_id="recent")
                assert len(result["assessments"]) == 1

        asyncio.run(_run())

    def test_purge_returns_count(self, db_factory) -> None:
        async def _run():
            async with db_factory() as session:
                count = await purge_expired_data(session, max_age_days=365)
                assert isinstance(count, int)
                assert count >= 0

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 5: API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("bypass_auth")
class TestDataRightsEndpoints:
    """Tests for GDPR/CCPA API endpoints."""

    def test_export_endpoint_returns_200(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/v1/user/data-export", params={"user_id": "test-user"})
            assert resp.status_code == 200

    def test_export_endpoint_returns_user_data(self) -> None:
        with TestClient(app) as client:
            data = client.get(
                "/v1/user/data-export", params={"user_id": "test-user"}
            ).json()
            assert data["user_id"] == "test-user"
            assert "consent_records" in data
            assert "assessments" in data

    def test_delete_endpoint_returns_200(self) -> None:
        with TestClient(app) as client:
            resp = client.delete("/v1/user/data", params={"user_id": "test-user"})
            assert resp.status_code == 200

    def test_delete_endpoint_returns_summary(self) -> None:
        with TestClient(app) as client:
            data = client.delete(
                "/v1/user/data", params={"user_id": "test-user"}
            ).json()
            assert data["user_id"] == "test-user"
            assert "deleted_at" in data

    def test_consent_endpoint_records_consent(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/v1/user/consent",
                json={"user_id": "test-user", "consent_version": "1.0"},
            )
            assert resp.status_code == 200

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
            from modules.credit.auth import AuthIdentity

            app.dependency_overrides[verify_auth] = lambda: AuthIdentity(
                identity="test-user"
            )


# ---------------------------------------------------------------------------
# Cycle 6: IDOR protection — ownership enforcement
# ---------------------------------------------------------------------------


class TestIdorProtection:
    """Tests for IDOR protection: users cannot access other users' data."""

    @pytest.fixture(autouse=True)
    def _setup_users(self):
        """Set up test users in DB and auth overrides."""
        from modules.credit.tests.conftest import _TEST_SETTINGS, create_test_user

        with patch_auth_settings(_TEST_SETTINGS):
            with TestClient(app) as client:  # noqa: F841 — triggers lifespan
                create_test_user(app, "user-a@test.com", role="viewer", org_id="org-a")
                create_test_user(
                    app, "admin@idor.com", role="admin", org_id="org-admin"
                )
                yield
        app.dependency_overrides.clear()

    def _override_identity(self, identity: str, role: str | None = None):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.auth import AuthIdentity

        app.dependency_overrides[verify_auth] = lambda: AuthIdentity(
            identity=identity, role=role
        )

    def test_export_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "user-a@test.com", role="viewer", org_id="org-a")
                resp = client.get("/v1/user/data-export", params={"user_id": "user-b"})
                assert resp.status_code == 403
                assert "another user" in resp.json()["detail"].lower()

    def test_export_allows_admin_override(self) -> None:
        self._override_identity("admin@idor.com", role="admin")
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(
                    app, "admin@idor.com", role="admin", org_id="org-admin"
                )
                resp = client.get("/v1/user/data-export", params={"user_id": "user-b"})
                assert resp.status_code == 200
                assert resp.json()["user_id"] == "user-b"

    def test_delete_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "user-a@test.com", role="viewer", org_id="org-a")
                resp = client.delete("/v1/user/data", params={"user_id": "user-b"})
                assert resp.status_code == 403

    def test_consent_rejects_different_user_for_non_admin(self) -> None:
        self._override_identity("user-a@test.com")
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "user-a@test.com", role="viewer", org_id="org-a")
                resp = client.post(
                    "/v1/user/consent",
                    json={"user_id": "user-b", "consent_version": "1.0"},
                )
                assert resp.status_code == 403

    def test_demoted_admin_cannot_override_user_id(self) -> None:
        """JWT claims admin but DB says viewer — DB wins for GDPR ops."""
        self._override_identity("demoted@test.com", role="admin")
        with patch_auth_settings():
            with TestClient(app) as client:
                create_test_user(app, "demoted@test.com", role="viewer", org_id="org-d")
                resp = client.get(
                    "/v1/user/data-export", params={"user_id": "someone-else"}
                )
                assert resp.status_code == 403
