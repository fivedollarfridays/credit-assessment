"""Tests for expanded ORM models — T17.1 TDD."""

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


class TestUserModelExpanded:
    """User model should have role and org_id columns."""

    def test_user_has_role_and_org_id(self, db_factory):
        from modules.credit.models_db import User

        async def _run():
            async with db_factory() as session:
                user = User(
                    email="test@example.com",
                    password_hash="hashed",
                    role="viewer",
                    org_id="org-1",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                assert user.role == "viewer"
                assert user.org_id == "org-1"

        asyncio.run(_run())


class TestAssessmentRecordExpanded:
    """AssessmentRecord should have user_id and org_id columns."""

    def test_assessment_has_user_and_org(self, db_factory):
        from modules.credit.models_db import AssessmentRecord

        async def _run():
            async with db_factory() as session:
                record = AssessmentRecord(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    user_id="user@test.com",
                    org_id="org-1",
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)
                assert record.user_id == "user@test.com"
                assert record.org_id == "org-1"

    def test_assessment_user_and_org_nullable(self, db_factory):
        from modules.credit.models_db import AssessmentRecord

        async def _run():
            async with db_factory() as session:
                record = AssessmentRecord(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                )
                session.add(record)
                await session.commit()
                assert record.user_id is None
                assert record.org_id is None

        asyncio.run(_run())


class TestSubscriptionModel:
    """Subscription model stores Stripe subscription data."""

    def test_create_subscription(self, db_factory):
        from modules.credit.models_db import Subscription

        async def _run():
            async with db_factory() as session:
                sub = Subscription(
                    email="cust@example.com",
                    subscription_id="sub_abc123",
                    status="active",
                    plan="starter",
                )
                session.add(sub)
                await session.commit()
                await session.refresh(sub)
                assert sub.id is not None
                assert sub.email == "cust@example.com"
                assert sub.plan == "starter"

        asyncio.run(_run())


class TestConsentRecordModel:
    """ConsentRecord tracks GDPR consent."""

    def test_create_consent_record(self, db_factory):
        from modules.credit.models_db import ConsentRecord

        async def _run():
            async with db_factory() as session:
                rec = ConsentRecord(
                    user_id="user-1",
                    consent_version="v1.0",
                )
                session.add(rec)
                await session.commit()
                await session.refresh(rec)
                assert rec.id is not None
                assert rec.user_id == "user-1"
                assert rec.consented_at is not None

        asyncio.run(_run())


class TestWebhookRegistrationModel:
    """WebhookRegistrationDB stores webhook endpoints."""

    def test_create_webhook(self, db_factory):
        from modules.credit.models_db import WebhookRegistrationDB

        async def _run():
            async with db_factory() as session:
                wh = WebhookRegistrationDB(
                    id="wh-1",
                    url="https://example.com/webhook",
                    events=["assessment.completed"],
                    secret="s3cret",
                    owner_id="org-1",
                )
                session.add(wh)
                await session.commit()
                await session.refresh(wh)
                assert wh.id == "wh-1"
                assert wh.is_active is True

        asyncio.run(_run())


class TestWebhookDeliveryModel:
    """WebhookDeliveryDB logs delivery attempts."""

    def test_create_delivery(self, db_factory):
        from modules.credit.models_db import WebhookDeliveryDB

        async def _run():
            async with db_factory() as session:
                d = WebhookDeliveryDB(
                    webhook_id="wh-1",
                    event_type="assessment.completed",
                    status="success",
                    status_code=200,
                )
                session.add(d)
                await session.commit()
                await session.refresh(d)
                assert d.id is not None
                assert d.status_code == 200

        asyncio.run(_run())


class TestApiKeyModel:
    """ApiKeyDB stores scoped API keys."""

    def test_create_api_key(self, db_factory):
        from modules.credit.models_db import ApiKeyDB
        from modules.credit.repo_api_keys import _hash_key

        async def _run():
            async with db_factory() as session:
                key = ApiKeyDB(
                    key_hash=_hash_key("test-key-abc"),
                    key_prefix="test-key",
                    org_id="org-1",
                    role="analyst",
                )
                session.add(key)
                await session.commit()
                await session.refresh(key)
                assert key.key_hash == _hash_key("test-key-abc")
                assert key.key_prefix == "test-key"
                assert key.expires_at is None
                assert key.revoked_at is None

        asyncio.run(_run())


class TestFeatureFlagModel:
    """FeatureFlagDB stores feature flags."""

    def test_create_flag(self, db_factory):
        from modules.credit.models_db import FeatureFlagDB

        async def _run():
            async with db_factory() as session:
                flag = FeatureFlagDB(
                    key="new-scoring",
                    description="New scoring algorithm",
                    enabled=False,
                    targeting=[{"type": "org", "values": ["org-1"]}],
                )
                session.add(flag)
                await session.commit()
                await session.refresh(flag)
                assert flag.key == "new-scoring"
                assert flag.enabled is False
                assert flag.targeting[0]["type"] == "org"

        asyncio.run(_run())


class TestAuditLogExpanded:
    """AuditLog should have user_id_hash and org_id columns."""

    def test_audit_has_expanded_fields(self, db_factory):
        from modules.credit.models_db import AuditLog

        async def _run():
            async with db_factory() as session:
                entry = AuditLog(
                    action="assess",
                    resource="credit_profile",
                    detail={"score": 740},
                    user_id_hash="abc123hash",
                    org_id="org-1",
                )
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
                assert entry.user_id_hash == "abc123hash"
                assert entry.org_id == "org-1"

        asyncio.run(_run())
