"""Tests for consent, user assessment, and subscription repositories."""

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


class TestSubscriptionRepository:
    def test_upsert_and_get(self, db_factory):
        from modules.credit.repo_billing import SubscriptionRepository

        async def _run():
            async with db_factory() as s:
                repo = SubscriptionRepository(s)
                await repo.upsert("a@b.com", "sub_1", "active", "starter")
                sub = await repo.get_by_email("a@b.com")
                assert sub is not None
                assert sub.plan == "starter"

        asyncio.run(_run())

    def test_upsert_updates_existing(self, db_factory):
        from modules.credit.repo_billing import SubscriptionRepository

        async def _run():
            async with db_factory() as s:
                repo = SubscriptionRepository(s)
                await repo.upsert("a@b.com", "sub_1", "active", "starter")
                updated = await repo.upsert("a@b.com", "sub_2", "canceled", "pro")
                assert updated.subscription_id == "sub_2"
                assert updated.plan == "pro"
                assert updated.status == "canceled"

        asyncio.run(_run())

    def test_list_all(self, db_factory):
        from modules.credit.repo_billing import SubscriptionRepository

        async def _run():
            async with db_factory() as s:
                repo = SubscriptionRepository(s)
                await repo.upsert("a@b.com", "sub_1", "active", "starter")
                await repo.upsert("c@d.com", "sub_2", "active", "pro")
                subs = await repo.list_all()
                assert len(subs) == 2

        asyncio.run(_run())

    def test_count_active(self, db_factory):
        from modules.credit.repo_billing import SubscriptionRepository

        async def _run():
            async with db_factory() as s:
                repo = SubscriptionRepository(s)
                await repo.upsert("a@b.com", "sub_1", "active", "starter")
                await repo.upsert("c@d.com", "sub_2", "canceled", "starter")
                assert await repo.count_active() == 1

        asyncio.run(_run())


class TestConsentRepository:
    def test_record_and_check(self, db_factory):
        from modules.credit.repo_data_rights import ConsentRepository

        async def _run():
            async with db_factory() as s:
                repo = ConsentRepository(s)
                await repo.record("user-1", "v1.0")
                assert await repo.check("user-1", "v1.0") is True
                assert await repo.check("user-1", "v2.0") is False

        asyncio.run(_run())

    def test_withdraw(self, db_factory):
        from modules.credit.repo_data_rights import ConsentRepository

        async def _run():
            async with db_factory() as s:
                repo = ConsentRepository(s)
                await repo.record("user-1", "v1.0")
                deleted = await repo.withdraw("user-1", "v1.0")
                assert deleted is True
                assert await repo.check("user-1", "v1.0") is False

        asyncio.run(_run())

    def test_get_by_user(self, db_factory):
        from modules.credit.repo_data_rights import ConsentRepository

        async def _run():
            async with db_factory() as s:
                repo = ConsentRepository(s)
                await repo.record("user-1", "v1.0")
                await repo.record("user-1", "v2.0")
                records = await repo.get_by_user("user-1")
                assert len(records) == 2

        asyncio.run(_run())


class TestUserAssessmentRepository:
    def test_record_and_get(self, db_factory):
        from modules.credit.repo_data_rights import UserAssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = UserAssessmentRepository(s)
                await repo.record("user-1", {"score": 700})
                records = await repo.get_by_user("user-1")
                assert len(records) == 1
                assert records[0].assessment_data["score"] == 700

        asyncio.run(_run())

    def test_delete_by_user(self, db_factory):
        from modules.credit.repo_data_rights import UserAssessmentRepository

        async def _run():
            async with db_factory() as s:
                repo = UserAssessmentRepository(s)
                await repo.record("user-1", {"score": 700})
                count = await repo.delete_by_user("user-1")
                assert count == 1
                assert await repo.get_by_user("user-1") == []

        asyncio.run(_run())


class TestConsentRepositoryDeleteByUser:
    def test_delete_all_user_consents(self, db_factory):
        from modules.credit.repo_data_rights import ConsentRepository

        async def _run():
            async with db_factory() as s:
                repo = ConsentRepository(s)
                await repo.record("user-1", "v1.0")
                await repo.record("user-1", "v2.0")
                await repo.record("user-2", "v1.0")
                count = await repo.delete_by_user("user-1")
                assert count == 2
                assert await repo.get_by_user("user-1") == []
                assert len(await repo.get_by_user("user-2")) == 1

        asyncio.run(_run())
