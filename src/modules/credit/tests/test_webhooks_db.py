"""Tests for webhook API endpoints and delivery DB persistence — T20.2."""

import asyncio

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.webhook_delivery import (
    WebhookDeliveryStatus,
    deliver_event,
    get_delivery_log,
)
from modules.credit.webhooks import EventType, create_webhook


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


class TestDeliveryLogDB:
    """Delivery log persists to DB."""

    def test_get_delivery_log_empty(self, db_factory):
        async def _run():
            async with db_factory() as session:
                result = await get_delivery_log(session, webhook_id="nonexistent")
                assert result == []

        asyncio.run(_run())

    @pytest.mark.asyncio
    async def test_delivery_records_to_db(self, db_factory):
        async with db_factory() as session:
            wh = await create_webhook(
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

        async with db_factory() as session:
            log = await get_delivery_log(session, webhook_id=wh.id)
            assert len(log) == 1
            assert log[0]["status"] == "success"


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
    async def test_deliver_event_http_error(self, db_factory):
        """Network errors are caught and recorded as failures."""
        async with db_factory() as session:
            wh = await create_webhook(
                session,
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
                db_factory=db_factory,
                event_type=EventType.ASSESSMENT_COMPLETED,
                payload={"score": 50},
            )
        assert len(result) == 1
        assert result[0].status == WebhookDeliveryStatus.FAILED
        assert result[0].status_code is None
        async with db_factory() as session:
            log = await get_delivery_log(session, webhook_id=wh.id)
            assert len(log) == 1
            assert log[0]["status"] == "failed"


class TestWebhookTenantIsolation:
    """Webhook endpoints enforce ownership — users can't access other users' webhooks."""

    @staticmethod
    def _auth_override(identity: str):
        from modules.credit.auth import AuthIdentity

        return lambda: AuthIdentity(identity=identity)

    def _create_webhook(self, client, url="https://example.com/h"):
        return client.post(
            "/v1/webhooks",
            json={
                "url": url,
                "events": ["assessment.completed"],
                "secret": "webhook-secret-0123456789",
            },
        )

    def test_list_only_own_webhooks(self, client):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.router import app

        app.dependency_overrides[verify_auth] = self._auth_override("user-a")
        self._create_webhook(client, "https://a.com/h")

        app.dependency_overrides[verify_auth] = self._auth_override("user-b")
        self._create_webhook(client, "https://b.com/h")

        resp = client.get("/v1/webhooks")
        urls = [w["url"] for w in resp.json()]
        assert "https://b.com/h" in urls
        assert "https://a.com/h" not in urls

        app.dependency_overrides.pop(verify_auth, None)

    def test_delete_other_users_webhook_returns_404(self, client):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.router import app

        app.dependency_overrides[verify_auth] = self._auth_override("user-a")
        wh_id = self._create_webhook(client).json()["id"]

        app.dependency_overrides[verify_auth] = self._auth_override("user-b")
        resp = client.delete(f"/v1/webhooks/{wh_id}")
        assert resp.status_code == 404

        app.dependency_overrides.pop(verify_auth, None)

    def test_deliveries_other_users_webhook_returns_404(self, client):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.router import app

        app.dependency_overrides[verify_auth] = self._auth_override("user-a")
        wh_id = self._create_webhook(client).json()["id"]

        app.dependency_overrides[verify_auth] = self._auth_override("user-b")
        resp = client.get(f"/v1/webhooks/{wh_id}/deliveries")
        assert resp.status_code == 404

        app.dependency_overrides.pop(verify_auth, None)

    def test_register_sets_owner_id(self, client):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.router import app

        app.dependency_overrides[verify_auth] = self._auth_override("owner-x")
        self._create_webhook(client)

        resp = client.get("/v1/webhooks")
        assert len(resp.json()) >= 1

        app.dependency_overrides[verify_auth] = self._auth_override("other-user")
        resp = client.get("/v1/webhooks")
        assert len(resp.json()) == 0

        app.dependency_overrides.pop(verify_auth, None)
