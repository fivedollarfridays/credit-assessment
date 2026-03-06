"""Tests for Stripe billing integration — T4.4 TDD."""

import asyncio

from unittest.mock import MagicMock, patch

import pytest

from modules.credit.billing import (
    PLAN_PRICES,
    BillingPlan,
    count_active_subscriptions,
    create_checkout_session,
    create_portal_session,
    get_subscription,
    handle_webhook,
    list_subscriptions,
    record_usage,
    update_subscription,
)
from modules.credit.config import Settings
from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.repo_billing import SubscriptionRepository


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


class TestBillingPlanEnum:
    """Test BillingPlan enum values."""

    def test_has_free_plan(self):
        assert BillingPlan.FREE.value == "free"

    def test_has_starter_plan(self):
        assert BillingPlan.STARTER.value == "starter"

    def test_has_pro_plan(self):
        assert BillingPlan.PRO.value == "pro"

    def test_has_enterprise_plan(self):
        assert BillingPlan.ENTERPRISE.value == "enterprise"

    def test_has_exactly_four_plans(self):
        assert len(BillingPlan) == 4


class TestPlanPricing:
    """Test plan pricing configuration."""

    def test_free_plan_price(self):
        assert PLAN_PRICES[BillingPlan.FREE] == 0

    def test_starter_plan_price(self):
        assert PLAN_PRICES[BillingPlan.STARTER] == 2900

    def test_pro_plan_price(self):
        assert PLAN_PRICES[BillingPlan.PRO] == 9900

    def test_enterprise_plan_is_custom(self):
        assert PLAN_PRICES[BillingPlan.ENTERPRISE] is None


class TestCreateCheckoutSession:
    """Test Stripe checkout session creation."""

    @patch("modules.credit.billing.stripe")
    def test_creates_checkout_session(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            url="https://checkout.stripe.com/test"
        )
        result = create_checkout_session(
            customer_email="user@test.com",
            price_id="price_test_123",
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
        )
        assert result.url == "https://checkout.stripe.com/test"
        mock_stripe.checkout.Session.create.assert_called_once()

    @patch("modules.credit.billing.stripe")
    def test_checkout_sets_correct_mode(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            url="https://x.com"
        )
        create_checkout_session(
            customer_email="user@test.com",
            price_id="price_test_123",
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
        )
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "subscription"


class TestRecordUsage:
    """Test usage metering for /assess calls."""

    @patch("modules.credit.billing.stripe")
    def test_records_usage_event(self, mock_stripe):
        record_usage(subscription_item_id="si_test_123", quantity=1)
        mock_stripe.SubscriptionItem.create_usage_record.assert_called_once_with(
            "si_test_123", quantity=1
        )

    @patch("modules.credit.billing.stripe")
    def test_records_usage_graceful_on_error(self, mock_stripe):
        mock_stripe.SubscriptionItem.create_usage_record.side_effect = Exception(
            "API error"
        )
        # Should not raise
        record_usage(subscription_item_id="si_test_123", quantity=1)


class TestWebhookHandler:
    """Test Stripe webhook processing with DB persistence."""

    @patch("modules.credit.billing.stripe")
    def test_webhook_verifies_signature(self, mock_stripe, db_factory):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"customer_email": "user@test.com", "subscription": "sub_123"}
            },
        }

        async def _run():
            async with db_factory() as session:
                result = await handle_webhook(
                    session=session,
                    payload=b'{"type":"checkout.session.completed"}',
                    sig_header="test_sig",
                    webhook_secret="whsec_test",
                )
                assert result["status"] == "processed"
                mock_stripe.Webhook.construct_event.assert_called_once()

        asyncio.run(_run())

    @patch("modules.credit.billing.stripe")
    def test_webhook_rejects_invalid_signature(self, mock_stripe, db_factory):
        mock_stripe.Webhook.construct_event.side_effect = ValueError(
            "Invalid signature"
        )

        async def _run():
            async with db_factory() as session:
                result = await handle_webhook(
                    session=session,
                    payload=b"bad",
                    sig_header="bad_sig",
                    webhook_secret="whsec_test",
                )
                assert result["status"] == "error"

        asyncio.run(_run())

    @patch("modules.credit.billing.stripe")
    def test_webhook_handles_subscription_updated(self, mock_stripe, db_factory):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer_email": "user@test.com",
                    "status": "active",
                    "items": {"data": [{"plan": {"nickname": "pro"}}]},
                }
            },
        }

        async def _run():
            async with db_factory() as session:
                result = await handle_webhook(
                    session=session,
                    payload=b"{}",
                    sig_header="sig",
                    webhook_secret="whsec_test",
                )
                assert result["status"] == "processed"

        asyncio.run(_run())

    @patch("modules.credit.billing.stripe")
    def test_webhook_handles_subscription_deleted(self, mock_stripe, db_factory):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer_email": "user@test.com",
                }
            },
        }

        async def _run():
            async with db_factory() as session:
                result = await handle_webhook(
                    session=session,
                    payload=b"{}",
                    sig_header="sig",
                    webhook_secret="whsec_test",
                )
                assert result["status"] == "processed"

        asyncio.run(_run())


class TestBillingPortal:
    """Test billing portal session creation."""

    @patch("modules.credit.billing.stripe")
    def test_creates_portal_session(self, mock_stripe):
        mock_stripe.billing_portal.Session.create.return_value = MagicMock(
            url="https://billing.stripe.com/portal"
        )
        result = create_portal_session(
            customer_id="cus_test_123",
            return_url="https://app.com/dashboard",
        )
        assert result.url == "https://billing.stripe.com/portal"


class TestBillingSettings:
    """Test billing-related settings."""

    def test_stripe_secret_key_defaults_to_none(self):
        s = Settings()
        assert s.stripe_secret_key is None

    def test_stripe_webhook_secret_defaults_to_none(self):
        s = Settings()
        assert s.stripe_webhook_secret is None

    def test_stripe_secret_key_from_env(self):
        s = Settings(stripe_secret_key="sk_test_xyz")
        assert s.stripe_secret_key == "sk_test_xyz"


class TestSubscriptionStoreDB:
    """Test DB-backed subscription tracking."""

    def test_update_subscription_stores_data(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "user@test.com", "sub_123", "active", "starter"
                )
                repo = SubscriptionRepository(session)
                sub = await repo.get_by_email("user@test.com")
                assert sub.subscription_id == "sub_123"
                assert sub.status == "active"
                assert sub.plan == "starter"

        asyncio.run(_run())

    def test_get_subscription_returns_none_for_unknown(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await get_subscription(session, "nobody@test.com") is None

        asyncio.run(_run())

    def test_get_subscription_returns_data(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "known@test.com", "sub_456", "active", "pro"
                )
                sub = await get_subscription(session, "known@test.com")
                assert sub["plan"] == "pro"

        asyncio.run(_run())

    def test_list_subscriptions_empty(self, db_factory):
        async def _run():
            async with db_factory() as session:
                result = await list_subscriptions(session)
                assert result == []

        asyncio.run(_run())

    def test_list_subscriptions_returns_all(self, db_factory):
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

    def test_count_active_subscriptions(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await update_subscription(
                    session, "a@test.com", "sub_1", "active", "pro"
                )
                await update_subscription(
                    session, "b@test.com", "sub_2", "canceled", "starter"
                )
                assert await count_active_subscriptions(session) == 1

        asyncio.run(_run())
