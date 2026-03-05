"""Tests for webhook system — registration, delivery, retry, signatures."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from modules.credit.router import app
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
    reset_webhooks,
    webhook_exists,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_webhooks()
    yield
    reset_webhooks()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
    def test_create_webhook(self):
        wh = create_webhook(
            url="https://example.com/hook",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="my-secret",
        )
        assert isinstance(wh, WebhookRegistration)
        assert wh.url == "https://example.com/hook"
        assert wh.events == [EventType.ASSESSMENT_COMPLETED]
        assert wh.is_active is True
        assert wh.id is not None

    def test_create_webhook_multiple_events(self):
        wh = create_webhook(
            url="https://example.com/hook",
            events=[EventType.ASSESSMENT_COMPLETED, EventType.SUBSCRIPTION_UPDATED],
            secret="s",
        )
        assert len(wh.events) == 2

    def test_get_webhooks_empty(self):
        assert get_webhooks() == []

    def test_get_webhooks_returns_registered(self):
        create_webhook(
            url="https://a.com/h", events=[EventType.ASSESSMENT_COMPLETED], secret="s"
        )
        create_webhook(
            url="https://b.com/h", events=[EventType.SUBSCRIPTION_UPDATED], secret="s"
        )
        assert len(get_webhooks()) == 2

    def test_webhook_exists(self):
        wh = create_webhook(
            url="https://example.com/hook",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
        )
        assert webhook_exists(wh.id) is True
        assert webhook_exists("nonexistent") is False

    def test_get_webhooks_by_owner(self):
        create_webhook(
            url="https://a.com/h",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
            owner_id="org1",
        )
        create_webhook(
            url="https://b.com/h",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
            owner_id="org2",
        )
        assert len(get_webhooks(owner_id="org1")) == 1

    def test_get_subscribed_webhooks_filters_by_event(self):
        create_webhook(
            url="https://a.com/h",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
        )
        create_webhook(
            url="https://b.com/h",
            events=[EventType.SUBSCRIPTION_UPDATED],
            secret="s",
        )
        matching = get_subscribed_webhooks(EventType.ASSESSMENT_COMPLETED)
        assert len(matching) == 1
        assert matching[0].url == "https://a.com/h"

    def test_get_subscribed_webhooks_excludes_inactive(self):
        wh = create_webhook(
            url="https://a.com/h",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
        )
        wh.is_active = False
        assert get_subscribed_webhooks(EventType.ASSESSMENT_COMPLETED) == []

    def test_get_subscribed_webhooks_empty(self):
        assert get_subscribed_webhooks(EventType.RATE_LIMIT_WARNING) == []


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
    async def test_deliver_event_success(self):
        create_webhook(
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
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 85},
            )
        assert len(result) == 1
        assert result[0].status == WebhookDeliveryStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_deliver_event_skips_unsubscribed(self):
        create_webhook(
            url="https://example.com/hook",
            events=[EventType.SUBSCRIPTION_UPDATED],
            secret="s",
        )
        with patch(
            "modules.credit.webhook_delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await deliver_event(
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 85},
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_deliver_event_records_failure(self):
        create_webhook(
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
        # Even at attempt 10, cap at 300s
        assert next_retry_delay(attempt=10) <= 300


# --- Delivery log ---


class TestDeliveryLog:
    @pytest.mark.asyncio
    async def test_delivery_log_recorded(self):
        wh = create_webhook(
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
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 90},
            )

        log = get_delivery_log(webhook_id=wh.id)
        assert len(log) == 1
        assert log[0]["status"] == "success"
        assert log[0]["event_type"] == EventType.ASSESSMENT_COMPLETED

    def test_delivery_log_empty(self):
        assert get_delivery_log(webhook_id="nonexistent") == []


# --- API Endpoints ---


@pytest.mark.usefixtures("bypass_auth")
class TestWebhookEndpoints:
    def test_register_webhook(self, client):
        resp = client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/hook"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_webhook_invalid_event(self, client):
        resp = client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["invalid.event"],
                "secret": "s",
            },
        )
        assert resp.status_code == 422
        # Cover URL validator (webhook_routes.py:30)
        resp = client.post(
            "/v1/webhooks",
            json={
                "url": "ftp://example.com/hook",
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )
        assert resp.status_code == 422

    def test_list_webhooks(self, client):
        client.post(
            "/v1/webhooks",
            json={
                "url": "https://a.com/h",
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )
        resp = client.get("/v1/webhooks")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_delivery_log_endpoint_not_found(self, client):
        resp = client.get("/v1/webhooks/nonexistent/deliveries")
        assert resp.status_code == 404

    def test_delete_webhook(self, client):
        create_resp = client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/h",
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )
        wh_id = create_resp.json()["id"]
        resp = client.delete(f"/v1/webhooks/{wh_id}")
        assert resp.status_code == 200
        assert get_webhooks() == []

    def test_delete_webhook_not_found(self, client):
        resp = client.delete("/v1/webhooks/nonexistent")
        assert resp.status_code == 404

    def test_webhook_deliveries_for_existing_webhook(self, client):
        """GET deliveries returns log dict for an existing webhook."""
        create_resp = client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/h",
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )
        wh_id = create_resp.json()["id"]
        resp = client.get(f"/v1/webhooks/{wh_id}/deliveries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deliveries"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_deliver_event_http_error(self):
        """Network errors are caught and recorded as failures."""
        wh = create_webhook(
            url="https://example.com/hook",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="secret",
        )
        with patch("modules.credit.webhook_delivery.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_cls.return_value = mock_client

            result = await deliver_event(
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 50},
            )
        assert len(result) == 1
        assert result[0].status == WebhookDeliveryStatus.FAILED
        assert result[0].status_code is None
        log = get_delivery_log(webhook_id=wh.id)
        assert len(log) == 1
        assert log[0]["status"] == "failed"
