"""Tests for webhook system — registration, delivery, retry, signatures."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from unittest.mock import AsyncMock, patch

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.webhook_delivery import (
    WebhookDeliveryStatus,
    compute_signature,
    deliver_event,
    get_delivery_log,
    next_retry_delay,
)
from modules.credit.webhooks import (
    EventType,
    WebhookRegistration,
    create_webhook,
    get_subscribed_webhooks,
    get_webhooks,
    webhook_exists,
)


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


# --- EventType enum ---


class TestEventType:
    def test_assessment_completed(self):
        assert EventType.ASSESSMENT_COMPLETED == "assessment.completed"

    def test_subscription_updated(self):
        assert EventType.SUBSCRIPTION_UPDATED == "subscription.updated"

    def test_rate_limit_warning(self):
        assert EventType.RATE_LIMIT_WARNING == "rate_limit.warning"


# --- Registration ---


class TestWebhookRegistration:
    def test_create_webhook(self, db_factory):
        async def _run():
            async with db_factory() as session:
                wh = await create_webhook(
                    session,
                    url="https://example.com/hook",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="my-secret",
                )
                assert isinstance(wh, WebhookRegistration)
                assert wh.url == "https://example.com/hook"
                assert wh.events == [EventType.ASSESSMENT_COMPLETED]
                assert wh.is_active is True
                assert wh.id is not None

        asyncio.run(_run())

    def test_create_webhook_multiple_events(self, db_factory):
        async def _run():
            async with db_factory() as session:
                wh = await create_webhook(
                    session,
                    url="https://example.com/hook",
                    events=[
                        EventType.ASSESSMENT_COMPLETED,
                        EventType.SUBSCRIPTION_UPDATED,
                    ],
                    secret="s",
                )
                assert len(wh.events) == 2

        asyncio.run(_run())

    def test_get_webhooks_empty(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await get_webhooks(session) == []

        asyncio.run(_run())

    def test_get_webhooks_returns_registered(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_webhook(
                    session,
                    url="https://a.com/h",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                )
                await create_webhook(
                    session,
                    url="https://b.com/h",
                    events=[EventType.SUBSCRIPTION_UPDATED],
                    secret="s",
                )
                assert len(await get_webhooks(session)) == 2

        asyncio.run(_run())

    def test_webhook_exists(self, db_factory):
        async def _run():
            async with db_factory() as session:
                wh = await create_webhook(
                    session,
                    url="https://example.com/hook",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                )
                assert await webhook_exists(session, wh.id) is True
                assert await webhook_exists(session, "nonexistent") is False

        asyncio.run(_run())

    def test_get_webhooks_by_owner(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_webhook(
                    session,
                    url="https://a.com/h",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                    owner_id="org1",
                )
                await create_webhook(
                    session,
                    url="https://b.com/h",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                    owner_id="org2",
                )
                assert len(await get_webhooks(session, owner_id="org1")) == 1

        asyncio.run(_run())

    def test_get_subscribed_webhooks_filters_by_event(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_webhook(
                    session,
                    url="https://a.com/h",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                )
                await create_webhook(
                    session,
                    url="https://b.com/h",
                    events=[EventType.SUBSCRIPTION_UPDATED],
                    secret="s",
                )
                matching = await get_subscribed_webhooks(
                    session, EventType.ASSESSMENT_COMPLETED
                )
                assert len(matching) == 1
                assert matching[0].url == "https://a.com/h"

        asyncio.run(_run())

    def test_get_subscribed_webhooks_empty(self, db_factory):
        async def _run():
            async with db_factory() as session:
                result = await get_subscribed_webhooks(
                    session, EventType.RATE_LIMIT_WARNING
                )
                assert result == []

        asyncio.run(_run())


# --- HMAC Signature ---


class TestSignature:
    def test_compute_signature(self):
        payload = b'{"event": "test"}'
        secret = "webhook-secret"
        sig = compute_signature(payload, secret)
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_signature_changes_with_payload(self):
        secret = "s"
        sig1 = compute_signature(b"payload1", secret)
        sig2 = compute_signature(b"payload2", secret)
        assert sig1 != sig2


# --- Delivery ---


class TestDelivery:
    @pytest.mark.asyncio
    async def test_deliver_event_success(self, db_factory):
        async with db_factory() as session:
            await create_webhook(
                session,
                url="https://example.com/hook",
                events=[EventType.ASSESSMENT_COMPLETED],
                secret="secret",
            )
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        with patch(
            "modules.credit.webhook_delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await deliver_event(
                db_factory=db_factory,
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 85},
            )
        assert len(result) == 1
        assert result[0].status == WebhookDeliveryStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_deliver_event_skips_unsubscribed(self, db_factory):
        async with db_factory() as session:
            await create_webhook(
                session,
                url="https://example.com/hook",
                events=[EventType.SUBSCRIPTION_UPDATED],
                secret="s",
            )
        result = await deliver_event(
            db_factory=db_factory,
            event_type=EventType.ASSESSMENT_COMPLETED,
            payload={"score": 85},
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_deliver_event_records_failure(self, db_factory):
        async with db_factory() as session:
            await create_webhook(
                session,
                url="https://example.com/hook",
                events=[EventType.ASSESSMENT_COMPLETED],
                secret="s",
            )
        mock_resp = AsyncMock()
        mock_resp.status_code = 500
        with patch(
            "modules.credit.webhook_delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await deliver_event(
                db_factory=db_factory,
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"data": "x"},
            )
        assert len(result) == 1
        assert result[0].status == WebhookDeliveryStatus.FAILED


# --- Retry logic ---


class TestRetryLogic:
    def test_first_retry_delay(self):
        assert next_retry_delay(attempt=0) == 1

    def test_second_retry_delay(self):
        assert next_retry_delay(attempt=1) == 2

    def test_third_retry_delay(self):
        assert next_retry_delay(attempt=2) == 4

    def test_max_capped(self):
        assert next_retry_delay(attempt=10) <= 300


# --- Delivery log ---


class TestDeliveryLog:
    @pytest.mark.asyncio
    async def test_delivery_log_recorded(self, db_factory):
        async with db_factory() as session:
            wh = await create_webhook(
                session,
                url="https://example.com/hook",
                events=[EventType.ASSESSMENT_COMPLETED],
                secret="s",
            )
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        with patch(
            "modules.credit.webhook_delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            await deliver_event(
                db_factory=db_factory,
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 90},
            )

        async with db_factory() as session:
            log = await get_delivery_log(session, webhook_id=wh.id)
            assert len(log) == 1
            assert log[0]["status"] == "success"
            assert log[0]["event_type"] == EventType.ASSESSMENT_COMPLETED

    def test_delivery_log_empty(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await get_delivery_log(session, webhook_id="nonexistent") == []

        asyncio.run(_run())
