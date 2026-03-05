"""Tests for repository data access layer — T3.3 TDD."""

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


class TestSaveAssessment:
    """Test saving assessment records."""

    def test_save_returns_record_with_id(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                record = await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={"current_score": 740},
                    response_payload={"barrier_severity": "low"},
                )
                assert record.id is not None
                assert record.credit_score == 740

        asyncio.run(_run())

    def test_save_persists_to_database(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                saved = await repo.save_assessment(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                )
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                found = await repo.get_assessment(saved.id)
                assert found is not None
                assert found.credit_score == 650

        asyncio.run(_run())


class TestGetAssessment:
    """Test retrieving assessment records."""

    def test_get_nonexistent_returns_none(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                result = await repo.get_assessment(999)
                assert result is None

        asyncio.run(_run())

    def test_list_assessments_returns_all(self, db_factory):
        from modules.credit.repo_assessments import AssessmentRepository

        async def _run():
            async with db_factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={},
                    response_payload={},
                )
                await repo.save_assessment(
                    credit_score=520,
                    score_band="very_poor",
                    barrier_severity="high",
                    readiness_score=25,
                    request_payload={},
                    response_payload={},
                )
                records = await repo.list_assessments()
                assert len(records) == 2

        asyncio.run(_run())


class TestAuditLog:
    """Test audit log operations."""

    def test_create_entry_stores_request_and_result(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                entry = await repo.create_entry(
                    action="assess",
                    user_id_hash="abc123",
                    request_summary={"score": 650},
                    result_summary={"readiness": 55},
                )
                assert entry.id is not None
                assert entry.action == "assess"
                assert entry.request_summary == {"score": 650}
                assert entry.result_summary == {"readiness": 55}
                assert entry.user_id_hash == "abc123"

        asyncio.run(_run())

    def test_create_entry_with_org_id(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                entry = await repo.create_entry(
                    action="assess",
                    user_id_hash="x",
                    request_summary={},
                    result_summary={},
                    org_id="org-abc",
                )
                assert entry.org_id == "org-abc"

        asyncio.run(_run())

    def test_list_entries_returns_all(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                await repo.create_entry(
                    action="assess",
                    user_id_hash="a",
                    request_summary={},
                    result_summary={},
                )
                await repo.create_entry(
                    action="export",
                    user_id_hash="b",
                    request_summary={},
                    result_summary={},
                )
                entries = await repo.list_entries()
                assert len(entries) == 2

        asyncio.run(_run())

    def test_list_entries_filter_by_action(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                await repo.create_entry(
                    action="assess",
                    user_id_hash="a",
                    request_summary={},
                    result_summary={},
                )
                await repo.create_entry(
                    action="export",
                    user_id_hash="b",
                    request_summary={},
                    result_summary={},
                )
                entries = await repo.list_entries(action="assess")
                assert len(entries) == 1
                assert entries[0]["action"] == "assess"

        asyncio.run(_run())

    def test_list_entries_with_limit(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                for i in range(5):
                    await repo.create_entry(
                        action="assess",
                        user_id_hash=f"u{i}",
                        request_summary={},
                        result_summary={},
                    )
                entries = await repo.list_entries(limit=3)
                assert len(entries) == 3

        asyncio.run(_run())

    def test_purge_old_entries(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as session:
                repo = AuditRepository(session)
                await repo.create_entry(
                    action="assess",
                    user_id_hash="a",
                    request_summary={},
                    result_summary={},
                )
                # Recent entry should not be purged
                purged = await repo.purge_old(max_age_days=2555)
                assert purged == 0
                assert await repo.count() == 1

        asyncio.run(_run())
