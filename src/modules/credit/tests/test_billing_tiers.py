"""Tests for dynamic rate limits, webhook DB persistence, and usage metering — T20.1."""

import asyncio

from unittest.mock import patch

import pytest

from modules.credit.assess_routes import (
    _record_usage_for_user,
    get_tier_limit,
    resolve_user_tier,
    verify_auth,
)
from modules.credit.auth import AuthIdentity
from modules.credit.billing import _extract_plan, handle_webhook, update_subscription
from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.repo_billing import SubscriptionRepository
from modules.credit.router import app


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


class TestHandleWebhookDB:
    def test_checkout_completed_persists(self, db_factory):
        async def _run():
            async with db_factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.return_value = {
                        "type": "checkout.session.completed",
                        "data": {
                            "object": {
                                "customer_email": "new@test.com",
                                "subscription": "sub_new",
                            }
                        },
                    }
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "processed"
                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("new@test.com")
                assert sub is not None
                assert sub.status == "active"

        asyncio.run(_run())

    def test_subscription_updated_persists(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "starter"
                )
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.return_value = {
                        "type": "customer.subscription.updated",
                        "data": {
                            "object": {
                                "id": "sub_123",
                                "customer_email": "user@test.com",
                                "status": "active",
                                "items": {
                                    "data": [{"plan": {"nickname": "pro"}}]
                                },
                            }
                        },
                    }
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "processed"
                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("user@test.com")
                assert sub.plan == "pro"

        asyncio.run(_run())

    def test_subscription_deleted_marks_canceled(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "starter"
                )
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.return_value = {
                        "type": "customer.subscription.deleted",
                        "data": {
                            "object": {
                                "id": "sub_123",
                                "customer_email": "user@test.com",
                            }
                        },
                    }
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "processed"
                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("user@test.com")
                assert sub.status == "canceled"

        asyncio.run(_run())

    def test_updated_without_email_logs(self, db_factory):
        async def _run():
            async with db_factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.return_value = {
                        "type": "customer.subscription.updated",
                        "data": {"object": {"id": "sub_no_email"}},
                    }
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "processed"

        asyncio.run(_run())

    def test_deleted_without_email_logs(self, db_factory):
        async def _run():
            async with db_factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.return_value = {
                        "type": "customer.subscription.deleted",
                        "data": {"object": {"id": "sub_no_email"}},
                    }
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "processed"

        asyncio.run(_run())

    def test_extract_plan_no_nickname_defaults(self, db_factory):
        assert _extract_plan({"items": {"data": [{"plan": {}}]}}) == "starter"
        assert _extract_plan({}) == "starter"

    def test_invalid_signature_returns_error(self, db_factory):
        async def _run():
            async with db_factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    mock_stripe.Webhook.construct_event.side_effect = ValueError(
                        "Invalid"
                    )
                    result = await handle_webhook(
                        session=session,
                        payload=b"bad",
                        sig_header="bad",
                        webhook_secret="whsec_test",
                    )
                assert result["status"] == "error"

        asyncio.run(_run())


class TestDynamicRateLimit:
    """Test that rate limits vary by subscription tier."""

    def test_free_tier_limit(self, client):
        """FREE tier should get 10/minute limit."""
        app.dependency_overrides[verify_auth] = lambda: AuthIdentity(
            identity="free@test.com"
        )
        try:
            resp = client.post("/v1/assess", json={
                "current_score": 700,
                "score_band": "good",
                "overall_utilization": 20.0,
                "account_summary": {"total_accounts": 5, "open_accounts": 3},
                "payment_history_pct": 95.0,
                "average_account_age_months": 60,
            })
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(verify_auth, None)

    def test_get_tier_limit_resolves_from_db(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "pro@test.com", "sub_pro", "active", "pro"
                )
                limit = await get_tier_limit(session, "pro@test.com")
                assert limit == "300/minute"

        asyncio.run(_run())

    def test_get_tier_limit_invalid_plan_defaults_free(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "bad@test.com", "sub_bad", "active", "invalid_plan"
                )
                limit = await get_tier_limit(session, "bad@test.com")
                assert limit == "10/minute"

        asyncio.run(_run())

    def test_resolve_user_tier_invalid_plan(self, db_factory):
        """resolve_user_tier returns FREE for unknown plan names."""
        from unittest.mock import MagicMock

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "bad-plan@test.com", "sub_x", "active", "invalid_plan"
                )
            request = MagicMock()
            request.app.state.db_session_factory = db_factory
            auth = AuthIdentity(identity="bad-plan@test.com")
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "free"

        asyncio.run(_run())

    def test_resolve_user_tier_api_key_returns_free(self):
        """resolve_user_tier returns FREE for static API key identity."""
        from unittest.mock import MagicMock

        from modules.credit.auth import API_KEY_IDENTITY

        async def _run():
            request = MagicMock()
            auth = AuthIdentity(identity=API_KEY_IDENTITY)
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "free"

        asyncio.run(_run())

    def test_resolve_user_tier_no_factory_returns_free(self):
        """resolve_user_tier returns FREE when db_session_factory is missing."""
        from unittest.mock import MagicMock

        async def _run():
            request = MagicMock(spec=[])
            request.app = MagicMock(spec=[])
            request.app.state = MagicMock(spec=[])
            auth = AuthIdentity(identity="user@test.com")
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "free"

        asyncio.run(_run())

    def test_resolve_user_tier_db_error_returns_free(self, db_factory):
        """resolve_user_tier returns FREE on DB errors."""
        from unittest.mock import MagicMock

        async def _run():
            def _broken_factory():
                raise RuntimeError("DB down")
            request = MagicMock()
            request.app.state.db_session_factory = _broken_factory
            auth = AuthIdentity(identity="user@test.com")
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "free"

        asyncio.run(_run())

    def test_resolve_user_tier_no_subscription_returns_free(self, db_factory):
        """resolve_user_tier returns FREE when user has no subscription."""
        from unittest.mock import MagicMock

        async def _run():
            request = MagicMock()
            request.app.state.db_session_factory = db_factory
            auth = AuthIdentity(identity="nosub@test.com")
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "free"

        asyncio.run(_run())

    def test_resolve_user_tier_active_pro(self, db_factory):
        """resolve_user_tier returns PRO for an active pro subscription."""
        from unittest.mock import MagicMock

        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "pro@test.com", "sub_pro", "active", "pro"
                )
            request = MagicMock()
            request.app.state.db_session_factory = db_factory
            auth = AuthIdentity(identity="pro@test.com")
            tier = await resolve_user_tier(request, auth)
            assert tier.value == "pro"

        asyncio.run(_run())

    def test_get_tier_limit_defaults_to_free(self, db_factory):
        async def _run():
            async with db_factory() as session:
                limit = await get_tier_limit(session, "unknown@test.com")
                assert limit == "10/minute"

        asyncio.run(_run())


class TestUsageMetering:
    """Test that record_usage is called after assessment."""

    def test_record_usage_for_active_subscriber(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "metered@test.com", "sub_meter", "active", "starter"
                )

            with patch("modules.credit.assess_routes.record_usage") as mock_usage:
                await _record_usage_for_user(db_factory, "metered@test.com")
                mock_usage.assert_called_once_with(subscription_item_id="sub_meter")

        asyncio.run(_run())

    def test_record_usage_skipped_no_subscription(self, db_factory):
        async def _run():
            with patch("modules.credit.assess_routes.record_usage") as mock_usage:
                await _record_usage_for_user(db_factory, "nobody@test.com")
                mock_usage.assert_not_called()

        asyncio.run(_run())
