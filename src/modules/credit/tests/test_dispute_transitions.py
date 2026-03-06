"""Tests for dispute status transitions and FCRA deadlines — T23.1 TDD."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.dispute_models import DisputeStatus
from modules.credit.models_db import Base
from modules.credit.repo_disputes import DisputeRepository

_ITEM = {"type": "collection", "description": "test"}


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
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_draft_to_sent(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                assert updated.status == "sent"
                assert updated.sent_at is not None

        asyncio.run(_run())

    def test_sent_to_in_review(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.IN_REVIEW
                )
                assert updated.status == "in_review"

        asyncio.run(_run())

    def test_in_review_to_responded(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                for st in (DisputeStatus.SENT, DisputeStatus.IN_REVIEW):
                    await repo.update_status(
                        rec.id, user_id="u1@test.com", new_status=st
                    )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.RESPONDED
                )
                assert updated.status == "responded"
                assert updated.responded_at is not None

        asyncio.run(_run())

    def test_responded_to_resolved(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                for st in (
                    DisputeStatus.SENT,
                    DisputeStatus.IN_REVIEW,
                    DisputeStatus.RESPONDED,
                    DisputeStatus.RESOLVED,
                ):
                    await repo.update_status(
                        rec.id, user_id="u1@test.com", new_status=st
                    )
                found = await repo.get(rec.id, user_id="u1@test.com")
                assert found.status == "resolved"

        asyncio.run(_run())

    def test_responded_to_escalated(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                for st in (
                    DisputeStatus.SENT,
                    DisputeStatus.IN_REVIEW,
                    DisputeStatus.RESPONDED,
                    DisputeStatus.ESCALATED,
                ):
                    await repo.update_status(
                        rec.id, user_id="u1@test.com", new_status=st
                    )
                found = await repo.get(rec.id, user_id="u1@test.com")
                assert found.status == "escalated"

        asyncio.run(_run())

    def test_escalated_to_sent_increments_round(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                for st in (
                    DisputeStatus.SENT,
                    DisputeStatus.IN_REVIEW,
                    DisputeStatus.RESPONDED,
                    DisputeStatus.ESCALATED,
                ):
                    await repo.update_status(
                        rec.id, user_id="u1@test.com", new_status=st
                    )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                assert updated.round == 2
                assert updated.sent_at is not None

        asyncio.run(_run())

    def test_invalid_transition_rejected(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                with pytest.raises(ValueError, match="transition"):
                    await repo.update_status(
                        rec.id,
                        user_id="u1@test.com",
                        new_status=DisputeStatus.RESOLVED,
                    )

        asyncio.run(_run())

    def test_draft_to_in_review_rejected(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                with pytest.raises(ValueError, match="transition"):
                    await repo.update_status(
                        rec.id,
                        user_id="u1@test.com",
                        new_status=DisputeStatus.IN_REVIEW,
                    )

        asyncio.run(_run())

    def test_update_nonexistent_raises(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                with pytest.raises(ValueError, match="not found"):
                    await repo.update_status(
                        999, user_id="u1@test.com", new_status=DisputeStatus.SENT
                    )

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# FCRA deadline calculation
# ---------------------------------------------------------------------------


class TestDeadlineCalculation:
    def test_standard_30_day_deadline(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                assert updated.deadline_at is not None
                delta = updated.deadline_at - updated.sent_at
                assert delta.days == 30

        asyncio.run(_run())

    def test_identity_theft_45_day_deadline(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com",
                    bureau="equifax",
                    negative_item_data={
                        "type": "identity_theft",
                        "description": "fraud",
                    },
                    letter_type="identity_theft",
                )
                updated = await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                delta = updated.deadline_at - updated.sent_at
                assert delta.days == 45

        asyncio.run(_run())

    def test_approaching_deadlines(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                found = await repo.get(rec.id, user_id="u1@test.com")
                found.deadline_at = datetime.now(timezone.utc) + timedelta(days=3)
                await s.commit()
                approaching = await repo.get_approaching_deadlines(
                    user_id="u1@test.com", days_ahead=7
                )
                assert len(approaching) == 1

        asyncio.run(_run())

    def test_no_approaching_if_far_out(self, db_factory):
        async def _run():
            async with db_factory() as s:
                repo = DisputeRepository(s)
                rec = await repo.create(
                    user_id="u1@test.com", bureau="equifax", negative_item_data=_ITEM
                )
                await repo.update_status(
                    rec.id, user_id="u1@test.com", new_status=DisputeStatus.SENT
                )
                approaching = await repo.get_approaching_deadlines(
                    user_id="u1@test.com", days_ahead=7
                )
                assert len(approaching) == 0

        asyncio.run(_run())
