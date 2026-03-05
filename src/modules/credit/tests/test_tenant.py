"""Tests for tenant isolation — T4.5 TDD."""

import asyncio

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.tests.conftest import patch_auth_settings


def _get_client():
    from fastapi.testclient import TestClient

    from modules.credit.router import app

    return TestClient(app)


def _make_db():
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


class TestOrgModel:
    """Test Organization data model."""

    def test_org_has_org_id_field(self):
        from modules.credit.tenant import Organization

        org = Organization(org_id="org-1", name="Acme Corp")
        assert org.org_id == "org-1"

    def test_org_has_name_field(self):
        from modules.credit.tenant import Organization

        org = Organization(org_id="org-1", name="Acme Corp")
        assert org.name == "Acme Corp"


class TestUserOrgAssociation:
    """Test users are associated with organizations."""

    def test_register_user_with_org(self):
        from modules.credit.repo_users import UserRepository

        with patch_auth_settings():
            from fastapi.testclient import TestClient

            from modules.credit.router import app

            with TestClient(app) as client:
                client.post(
                    "/auth/register",
                    json={"email": "orguser@test.com", "password": "Secret123!"},
                )

                async def _check():
                    async with app.state.db_session_factory() as session:
                        repo = UserRepository(session)
                        user = await repo.get_by_email("orguser@test.com")
                        return user

                user = asyncio.run(_check())
                assert user is not None
                assert user.org_id is not None


class TestApiKeyOrgResolution:
    """Test API keys resolve to correct org."""

    def test_api_key_contains_org_id(self):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            engine = create_engine("sqlite+aiosqlite://", echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="test-key", org_id="org-1", role="analyst")
                entry = await repo.lookup("test-key")
                assert entry is not None
                assert entry.org_id == "org-1"
            await engine.dispose()

        asyncio.run(_run())


class TestTenantResolver:
    """Test resolving org_id from request context."""

    def test_resolve_org_from_user(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "a@test.com", "org_id": "org-1", "role": "analyst"}
        assert resolve_org_id(user_data) == "org-1"

    def test_resolve_org_returns_none_for_missing(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "a@test.com", "role": "analyst"}
        assert resolve_org_id(user_data) is None

    def test_admin_can_specify_org_override(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "admin@test.com", "org_id": "org-admin", "role": "admin"}
        assert resolve_org_id(user_data, override_org="org-other") == "org-other"

    def test_non_admin_cannot_override_org(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "user@test.com", "org_id": "org-1", "role": "analyst"}
        assert resolve_org_id(user_data, override_org="org-other") == "org-1"


class TestScopedRepository:
    """Test repository queries are scoped by org_id."""

    def test_scoped_repo_requires_org_id(self):
        from modules.credit.tenant import ScopedAssessmentRepository

        repo = ScopedAssessmentRepository(session=None, org_id="org-1")
        assert repo.org_id == "org-1"

    def test_scoped_repo_rejects_none_org_id(self):
        import pytest

        from modules.credit.tenant import ScopedAssessmentRepository

        with pytest.raises(ValueError, match="org_id"):
            ScopedAssessmentRepository(session=None, org_id=None)


class TestCrossTenantIsolation:
    """Test that tenants cannot access each other's data."""

    def test_org_store_isolation(self):
        from modules.credit.repo_assessments import AssessmentRepository
        from modules.credit.tenant import get_org_assessments

        factory = _make_db()

        async def _run():
            async with factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    org_id="org-A",
                )
                await repo.save_assessment(
                    credit_score=800,
                    score_band="excellent",
                    barrier_severity="low",
                    readiness_score=95,
                    request_payload={},
                    response_payload={},
                    org_id="org-B",
                )
                org_a = await get_org_assessments(session, "org-A")
                org_b = await get_org_assessments(session, "org-B")
                org_c = await get_org_assessments(session, "org-C")
                assert len(org_a) == 1
                assert org_a[0].credit_score == 700
                assert len(org_b) == 1
                assert org_b[0].credit_score == 800
                assert len(org_c) == 0

        asyncio.run(_run())

    def test_admin_can_query_across_orgs(self):
        from modules.credit.tenant import count_all_assessments

        factory = _make_db()

        async def _run():
            async with factory() as session:
                from modules.credit.repo_assessments import AssessmentRepository

                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    org_id="org-X",
                )
                await repo.save_assessment(
                    credit_score=800,
                    score_band="excellent",
                    barrier_severity="low",
                    readiness_score=95,
                    request_payload={},
                    response_payload={},
                    org_id="org-Y",
                )
                total = await count_all_assessments(session)
                assert total >= 2

        asyncio.run(_run())
