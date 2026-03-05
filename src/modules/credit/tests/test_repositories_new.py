"""Tests for new repository classes — T17.3 TDD."""

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


class TestUserRepository:
    def test_create_and_get_by_email(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                user = await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="org-1"
                )
                assert user.id is not None
                found = await repo.get_by_email("a@b.com")
                assert found is not None
                assert found.role == "viewer"

        asyncio.run(_run())

    def test_get_by_email_not_found(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                assert await repo.get_by_email("nope@x.com") is None

        asyncio.run(_run())

    def test_count(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                assert await repo.count() == 0
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                assert await repo.count() == 1

        asyncio.run(_run())

    def test_update_role(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                updated = await repo.set_role("a@b.com", "admin")
                assert updated is True
                user = await repo.get_by_email("a@b.com")
                assert user.role == "admin"

        asyncio.run(_run())

    def test_list_all(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                await repo.create(
                    email="c@d.com", password_hash="h", role="admin", org_id="o"
                )
                users = await repo.list_all()
                assert len(users) == 2

        asyncio.run(_run())


class TestResetTokenRepository:
    def test_store_and_pop(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com")
                email = await repo.pop("tok-1")
                assert email == "a@b.com"
                # second pop returns None (consumed)
                assert await repo.pop("tok-1") is None

        asyncio.run(_run())

    def test_expired_token_returns_none(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com", ttl_minutes=0)
                # TTL of 0 means already expired
                assert await repo.pop("tok-1") is None

        asyncio.run(_run())


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

    def test_revoke(self, db_factory):
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as s:
                repo = ApiKeyRepository(s)
                await repo.create(key="k1", org_id="org-1", role="analyst")
                revoked = await repo.revoke("k1")
                assert revoked is True
                assert await repo.lookup("k1") is None

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


class TestAuditRepositoryExpanded:
    def test_log_with_expanded_fields(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as s:
                repo = AuditRepository(s)
                entry = await repo.log_action(
                    action="assess",
                    resource="credit_profile",
                    detail={"score": 740},
                    user_id_hash="abc123",
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
                await repo.log_action(action="a", resource="r")
                assert await repo.count() == 1

        asyncio.run(_run())

    def test_list_by_action(self, db_factory):
        from modules.credit.repository import AuditRepository

        async def _run():
            async with db_factory() as s:
                repo = AuditRepository(s)
                await repo.log_action(action="assess", resource="r")
                await repo.log_action(action="login", resource="r")
                results = await repo.list_by_action("assess")
                assert len(results) == 1

        asyncio.run(_run())
