"""Tests for DB-backed billing CRUD functions — T20.1 TDD."""

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


class TestUpdateSubscriptionDB:
    def test_stores_subscription(self, db_factory):
        from modules.credit.billing import update_subscription

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "starter"
                )
                from modules.credit.repo_billing import SubscriptionRepository

                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("user@test.com")
                assert sub is not None
                assert sub.subscription_id == "sub_123"
                assert sub.status == "active"
                assert sub.plan == "starter"

        asyncio.run(_run())

    def test_upserts_existing(self, db_factory):
        from modules.credit.billing import update_subscription

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "starter"
                )
                await update_subscription(
                    session, "user@test.com", "sub_456", "canceled", "pro"
                )
                from modules.credit.repo_billing import SubscriptionRepository

                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("user@test.com")
                assert sub.subscription_id == "sub_456"
                assert sub.status == "canceled"
                assert sub.plan == "pro"

        asyncio.run(_run())


class TestGetSubscriptionDB:
    def test_returns_none_for_unknown(self, db_factory):
        from modules.credit.billing import get_subscription

        async def _run():
            async with db_factory() as session:
                result = await get_subscription(session, "nobody@test.com")
                assert result is None

        asyncio.run(_run())

    def test_returns_subscription_dict(self, db_factory):
        from modules.credit.billing import get_subscription, update_subscription

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "pro"
                )
                result = await get_subscription(session, "user@test.com")
                assert result is not None
                assert result["plan"] == "pro"
                assert result["status"] == "active"
                assert result["subscription_id"] == "sub_123"

        asyncio.run(_run())


class TestListSubscriptionsDB:
    def test_returns_all(self, db_factory):
        from modules.credit.billing import list_subscriptions, update_subscription

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "a@test.com", "sub_1", "active", "pro"
                )
                await update_subscription(
                    session, "b@test.com", "sub_2", "canceled", "starter"
                )
                result = await list_subscriptions(session)
                assert len(result) == 2
                emails = {s["email"] for s in result}
                assert "a@test.com" in emails
                assert "b@test.com" in emails

        asyncio.run(_run())


class TestCountActiveDB:
    def test_counts_active_only(self, db_factory):
        from modules.credit.billing import (
            count_active_subscriptions,
            update_subscription,
        )

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "a@test.com", "sub_1", "active", "pro"
                )
                await update_subscription(
                    session, "b@test.com", "sub_2", "canceled", "starter"
                )
                count = await count_active_subscriptions(session)
                assert count == 1

        asyncio.run(_run())
