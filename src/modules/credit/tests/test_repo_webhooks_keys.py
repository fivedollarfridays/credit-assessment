"""Tests for webhook, API key, and feature flag repositories."""

import asyncio
from datetime import datetime, timedelta, timezone

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


class TestWebhookRepository:
    def test_create_and_get(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                wh = await repo.create(
                    id="wh-1",
                    url="https://example.com/hook",
                    events=["assessment.completed"],
                    secret="s3cret",
                    owner_id="org-1",
                )
                assert wh.id == "wh-1"
                found = await repo.get("wh-1")
                assert found is not None
                assert found.url == "https://example.com/hook"

        asyncio.run(_run())

    def test_list_by_owner(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                await repo.create(
                    id="wh-1",
                    url="https://a.com",
                    events=[],
                    secret="s",
                    owner_id="org-1",
                )
                await repo.create(
                    id="wh-2",
                    url="https://b.com",
                    events=[],
                    secret="s",
                    owner_id="org-2",
                )
                org1 = await repo.list_by_owner("org-1")
                assert len(org1) == 1
                assert org1[0].id == "wh-1"

        asyncio.run(_run())

    def test_list_all(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                await repo.create(id="wh-1", url="https://a.com", events=[], secret="s")
                await repo.create(id="wh-2", url="https://b.com", events=[], secret="s")
                all_wh = await repo.list_all()
                assert len(all_wh) == 2

        asyncio.run(_run())

    def test_get_subscribed(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                await repo.create(
                    id="wh-1",
                    url="https://a.com",
                    events=["assessment.completed"],
                    secret="s",
                )
                await repo.create(
                    id="wh-2",
                    url="https://b.com",
                    events=["subscription.updated"],
                    secret="s",
                )
                matched = await repo.get_subscribed("assessment.completed")
                assert len(matched) == 1
                assert matched[0].id == "wh-1"

        asyncio.run(_run())

    def test_delete(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                await repo.create(id="wh-1", url="https://a.com", events=[], secret="s")
                deleted = await repo.delete("wh-1")
                assert deleted is True
                assert await repo.get("wh-1") is None

        asyncio.run(_run())

    def test_count(self, db_factory):
        from modules.credit.repo_webhooks import WebhookRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookRepository(s)
                assert await repo.count() == 0
                await repo.create(id="wh-1", url="https://a.com", events=[], secret="s")
                assert await repo.count() == 1

        asyncio.run(_run())


class TestWebhookDeliveryRepository:
    def test_log_and_get(self, db_factory):
        from modules.credit.repo_webhooks import WebhookDeliveryRepository

        async def _run():
            async with db_factory() as s:
                repo = WebhookDeliveryRepository(s)
                await repo.log_delivery(
                    webhook_id="wh-1",
                    event_type="assessment.completed",
                    status="success",
                    status_code=200,
                )
                records = await repo.get_by_webhook("wh-1")
                assert len(records) == 1
                assert records[0].status == "success"

        asyncio.run(_run())


class TestApiKeyRepository:
    def test_create_and_lookup(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                await repo.create(key="k1", org_id="org-1", role="analyst")
                result = await repo.lookup("k1")
                assert result is not None
                assert result.org_id == "org-1"

        asyncio.run(_run())

    def test_lookup_missing_key_returns_none(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                assert await repo.lookup("nonexistent") is None

        asyncio.run(_run())

    def test_expired_key_returns_none(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                past = datetime.now(timezone.utc) - timedelta(hours=1)
                await repo.create(
                    key="k1", org_id="org-1", role="analyst", expires_at=past
                )
                assert await repo.lookup("k1") is None

        asyncio.run(_run())

    def test_revoked_key_returns_none(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                await repo.create(key="k1", org_id="org-1", role="analyst")
                await repo.revoke("k1")
                assert await repo.lookup("k1") is None

        asyncio.run(_run())

    def test_list_by_org(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                await repo.create(key="k1", org_id="org-1", role="analyst")
                await repo.create(key="k2", org_id="org-1", role="viewer")
                await repo.create(key="k3", org_id="org-2", role="admin")
                org1_keys = await repo.list_by_org("org-1")
                assert len(org1_keys) == 2

        asyncio.run(_run())

    def test_prune_expired(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                past = datetime.now(timezone.utc) - timedelta(hours=1)
                await repo.create(
                    key="k1", org_id="org-1", role="analyst", expires_at=past
                )
                await repo.create(key="k2", org_id="org-1", role="viewer")
                pruned = await repo.prune_expired()
                assert pruned == 1

        asyncio.run(_run())


class TestFeatureFlagRepository:
    def test_create_and_get(self, db_factory):
        from modules.credit.repo_flags import FeatureFlagRepository

        async def _run():
            async with db_factory() as s:
                repo = FeatureFlagRepository(s)
                flag = await repo.create(
                    key="new-ui", description="New UI", enabled=False
                )
                assert flag.key == "new-ui"
                found = await repo.get("new-ui")
                assert found is not None
                assert found.enabled is False

        asyncio.run(_run())

    def test_set_enabled(self, db_factory):
        from modules.credit.repo_flags import FeatureFlagRepository

        async def _run():
            async with db_factory() as s:
                repo = FeatureFlagRepository(s)
                await repo.create(key="f1", description="", enabled=False)
                updated = await repo.set_enabled("f1", enabled=True)
                assert updated is True
                flag = await repo.get("f1")
                assert flag.enabled is True

        asyncio.run(_run())

    def test_list_all(self, db_factory):
        from modules.credit.repo_flags import FeatureFlagRepository

        async def _run():
            async with db_factory() as s:
                repo = FeatureFlagRepository(s)
                await repo.create(key="f1", description="", enabled=False)
                await repo.create(key="f2", description="", enabled=True)
                flags = await repo.list_all()
                assert len(flags) == 2

        asyncio.run(_run())

    def test_delete(self, db_factory):
        from modules.credit.repo_flags import FeatureFlagRepository

        async def _run():
            async with db_factory() as s:
                repo = FeatureFlagRepository(s)
                await repo.create(key="f1", description="", enabled=False)
                deleted = await repo.delete("f1")
                assert deleted is True
                assert await repo.get("f1") is None

        asyncio.run(_run())
