"""Tests for AssessmentRepository and AuditRepository expanded methods."""

import asyncio

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base


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


class TestAssessmentRepositoryUserIdMethods:
    def test_save_with_user_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                rec = await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    user_id="u1@test.com",
                )
                assert rec.user_id == "u1@test.com"

        asyncio.run(_run())

    def test_get_by_user_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    user_id="u1@test.com",
                )
                await repo.save_assessment(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                    user_id="u2@test.com",
                )
                records = await repo.get_by_user_id("u1@test.com")
                assert len(records) == 1
                assert records[0].credit_score == 740

        asyncio.run(_run())

    def test_delete_by_user_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    user_id="u1@test.com",
                )
                count = await repo.delete_by_user_id("u1@test.com")
                assert count == 1
                assert await repo.get_by_user_id("u1@test.com") == []

        asyncio.run(_run())


class TestAssessmentRepositoryOrgMethods:
    def test_save_with_org_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                rec = await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    org_id="org-1",
                )
                assert rec.org_id == "org-1"

        asyncio.run(_run())

    def test_get_by_org_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    org_id="org-1",
                )
                await repo.save_assessment(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                    org_id="org-2",
                )
                records = await repo.get_by_org_id("org-1")
                assert len(records) == 1
                assert records[0].credit_score == 740

        asyncio.run(_run())

    def test_count_all(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                assert await repo.count_all() == 0
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                )
                assert await repo.count_all() == 1

        asyncio.run(_run())

    def test_count_by_org_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    org_id="org-1",
                )
                await repo.save_assessment(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                    org_id="org-2",
                )
                assert await repo.count_by_org_id("org-1") == 1
                assert await repo.count_by_org_id("org-2") == 1
                assert await repo.count_by_org_id("org-3") == 0

        asyncio.run(_run())

    def test_count_by_user_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                    user_id="user-A",
                )
                await repo.save_assessment(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                    user_id="user-A",
                )
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=70,
                    request_payload={},
                    response_payload={},
                    user_id="user-B",
                )
                assert await repo.count_by_user_id("user-A") == 2
                assert await repo.count_by_user_id("user-B") == 1
                assert await repo.count_by_user_id("user-C") == 0

        asyncio.run(_run())

    def test_get_by_org_id_with_limit_offset(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = AssessmentRepository(s)
                for i in range(5):
                    await repo.save_assessment(
                        credit_score=700 + i,
                        score_band="good",
                        barrier_severity="low",
                        readiness_score=80,
                        request_payload={},
                        response_payload={},
                        org_id="org-1",
                    )
                page = await repo.get_by_org_id("org-1", limit=2, offset=1)
                assert len(page) == 2

        asyncio.run(_run())


class TestAuditRepositoryExpanded:
    def test_create_entry_with_org(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as s:
                repo = AuditRepository(s)
                entry = await repo.create_entry(
                    action="assess",
                    user_id_hash="abc123",
                    request_summary={"score": 740},
                    result_summary={},
                    org_id="org-1",
                )
                assert entry.user_id_hash == "abc123"
                assert entry.org_id == "org-1"

        asyncio.run(_run())

    def test_count(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as s:
                repo = AuditRepository(s)
                assert await repo.count() == 0
                await repo.create_entry(
                    action="a",
                    user_id_hash="x",
                    request_summary={},
                    result_summary={},
                )
                assert await repo.count() == 1

        asyncio.run(_run())

    def test_list_by_action(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as s:
                repo = AuditRepository(s)
                await repo.create_entry(
                    action="assess",
                    user_id_hash="x",
                    request_summary={},
                    result_summary={},
                )
                await repo.create_entry(
                    action="login",
                    user_id_hash="x",
                    request_summary={},
                    result_summary={},
                )
                results = await repo.list_by_action("assess")
                assert len(results) == 1

        asyncio.run(_run())
