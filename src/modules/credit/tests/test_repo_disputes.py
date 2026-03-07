"""Tests for DisputeRepository CRUD — T23.1 TDD."""

import asyncio

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.dispute_models import DisputeStatus
from modules.credit.models_db import Base
from modules.credit.repo_disputes import DisputeRepository


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
# Cycle 1: DisputeStatus enum
# ---------------------------------------------------------------------------


class TestDisputeStatus:
    def test_has_six_states(self):
        assert len(DisputeStatus) == 6

    def test_status_values(self):
        assert DisputeStatus.DRAFT == "draft"
        assert DisputeStatus.SENT == "sent"
        assert DisputeStatus.IN_REVIEW == "in_review"
        assert DisputeStatus.RESPONDED == "responded"
        assert DisputeStatus.RESOLVED == "resolved"
        assert DisputeStatus.ESCALATED == "escalated"


# ---------------------------------------------------------------------------
# Cycle 2: Repository CRUD
# ---------------------------------------------------------------------------

_ITEM = {"type": "collection", "description": "test"}


class TestDisputeCreate:
    def test_create_dispute(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="user@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                assert rec.id is not None
                assert rec.user_id == "user@test.com"
                assert rec.bureau == "equifax"
                assert rec.status == "draft"
                assert rec.round == 1

        asyncio.run(_run())

    def test_create_with_org_and_letter_type(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="user@test.com",
                    bureau="experian",
                    negative_item_data=_ITEM,
                    org_id="org-1",
                    letter_type="validation",
                )
                assert rec.org_id == "org-1"
                assert rec.letter_type == "validation"

        asyncio.run(_run())


class TestDisputeGet:
    def test_get_by_id_and_user(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                found = await repo.get(rec.id, user_id="u1@test.com")
                assert found is not None
                assert found.id == rec.id

        asyncio.run(_run())

    def test_get_scoped_to_user(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                found = await repo.get(rec.id, user_id="other@test.com")
                assert found is None

        asyncio.run(_run())


class TestDisputeList:
    def test_list_by_user(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                for bureau in ("equifax", "experian"):
                    await repo.create(
                        user_id="u1@test.com",
                        bureau=bureau,
                        negative_item_data=_ITEM,
                    )
                await repo.create(
                    user_id="u2@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                assert len(await repo.list_by_user("u1@test.com")) == 2

        asyncio.run(_run())

    def test_list_with_status_filter(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                rec2 = await repo.create(
                    user_id="u1@test.com", bureau="experian", negative_item_data=_ITEM
                )
                await repo.update_status(
                    rec2.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                drafts = await repo.list_by_user(
                    "u1@test.com", status_filter=DisputeStatus.DRAFT
                )
                assert len(drafts) == 1

        asyncio.run(_run())

    def test_list_with_pagination(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                for i in range(5):
                    await repo.create(
                        user_id="u1@test.com",
                        bureau="equifax",
                        negative_item_data={**_ITEM, "description": f"item {i}"},
                    )
                page = await repo.list_by_user("u1@test.com", limit=2, offset=2)
                assert len(page) == 2

        asyncio.run(_run())

    def test_count_by_user(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                for bureau in ("equifax", "experian"):
                    await repo.create(
                        user_id="u1@test.com",
                        bureau=bureau,
                        negative_item_data=_ITEM,
                    )
                assert await repo.count_by_user("u1@test.com") == 2
                assert await repo.count_by_user("other@test.com") == 0

        asyncio.run(_run())

    def test_count_by_user_with_status_filter(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                d1 = await repo.create(
                    user_id="u1@test.com",
                    bureau="equifax",
                    negative_item_data=_ITEM,
                )
                await repo.create(
                    user_id="u1@test.com",
                    bureau="experian",
                    negative_item_data=_ITEM,
                )
                # Update one to "sent" status
                await repo.update_status(
                    d1.id,
                    user_id="u1@test.com",
                    new_status=DisputeStatus.SENT,
                )
                assert (
                    await repo.count_by_user(
                        "u1@test.com", status_filter=DisputeStatus.SENT
                    )
                    == 1
                )
                assert (
                    await repo.count_by_user(
                        "u1@test.com", status_filter=DisputeStatus.DRAFT
                    )
                    == 1
                )
                assert await repo.count_by_user("u1@test.com") == 2

        asyncio.run(_run())
