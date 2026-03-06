"""Tests for score history tracking — T23.3 TDD."""

import asyncio

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.score_models import ScoreSource


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
# Cycle 1: ScoreSource enum
# ---------------------------------------------------------------------------


class TestScoreSource:
    def test_has_three_values(self):
        assert len(ScoreSource) == 3

    def test_source_values(self):
        assert ScoreSource.ASSESSMENT == "assessment"
        assert ScoreSource.MANUAL == "manual"
        assert ScoreSource.EXTERNAL == "external"


# ---------------------------------------------------------------------------
# Cycle 2: Repository — record + get_latest
# ---------------------------------------------------------------------------


class TestScoreRecord:
    def test_record_score(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                rec = await repo.record(
                    user_id="u1@test.com",
                    score=720,
                    score_band="good",
                    source=ScoreSource.ASSESSMENT,
                )
                assert rec.id is not None
                assert rec.score == 720
                assert rec.source == "assessment"

        asyncio.run(_run())

    def test_record_with_optional_fields(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                rec = await repo.record(
                    user_id="u1@test.com",
                    score=650,
                    score_band="fair",
                    source=ScoreSource.MANUAL,
                    org_id="org-1",
                    notes="Manual entry from report",
                )
                assert rec.org_id == "org-1"
                assert rec.notes == "Manual entry from report"

        asyncio.run(_run())

    def test_get_latest(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                await repo.record(
                    user_id="u1@test.com",
                    score=650,
                    score_band="fair",
                    source=ScoreSource.ASSESSMENT,
                )
                await repo.record(
                    user_id="u1@test.com",
                    score=680,
                    score_band="fair",
                    source=ScoreSource.ASSESSMENT,
                )
                latest = await repo.get_latest("u1@test.com")
                assert latest is not None
                assert latest.score == 680

        asyncio.run(_run())

    def test_get_latest_no_records(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                latest = await repo.get_latest("nobody@test.com")
                assert latest is None

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Cycle 3: Repository — list + trend
# ---------------------------------------------------------------------------


class TestScoreList:
    def test_list_by_user(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                for score in (600, 620, 640):
                    await repo.record(
                        user_id="u1@test.com",
                        score=score,
                        score_band="fair",
                        source=ScoreSource.ASSESSMENT,
                    )
                await repo.record(
                    user_id="u2@test.com",
                    score=700,
                    score_band="good",
                    source=ScoreSource.MANUAL,
                )
                records = await repo.list_by_user("u1@test.com")
                assert len(records) == 3

        asyncio.run(_run())

    def test_list_with_pagination(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                for score in (600, 620, 640, 660, 680):
                    await repo.record(
                        user_id="u1@test.com",
                        score=score,
                        score_band="fair",
                        source=ScoreSource.ASSESSMENT,
                    )
                page = await repo.list_by_user("u1@test.com", limit=2, offset=1)
                assert len(page) == 2

        asyncio.run(_run())

    def test_get_trend(self, db_factory):
        async def _run():
            from modules.credit.repo_scores import ScoreHistoryRepository

            async with db_factory() as s:
                repo = ScoreHistoryRepository(s)
                for score in (600, 620, 640):
                    await repo.record(
                        user_id="u1@test.com",
                        score=score,
                        score_band="fair",
                        source=ScoreSource.ASSESSMENT,
                    )
                trend = await repo.get_trend("u1@test.com", days=90)
                assert len(trend) == 2  # last 2 entries for trend
                # Trend should be chronological (oldest first)
                assert trend[0].score == 620
                assert trend[-1].score == 640

        asyncio.run(_run())
