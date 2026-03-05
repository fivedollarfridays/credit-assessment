"""Tests for Stripe billing integration — T4.4 TDD."""

from unittest.mock import MagicMock, patch

from modules.credit.config import Settings

_BILLING_SETTINGS = Settings(
    jwt_secret="test-secret",
    api_key=None,
    stripe_secret_key="sk_test_fake",
    stripe_webhook_secret="whsec_test_fake",
)


def _get_client():
    from fastapi.testclient import TestClient

    from modules.credit.router import app

    return TestClient(app)


class TestBillingPlanEnum:
    """Test BillingPlan enum values."""

    def test_has_free_plan(self):
        from modules.credit.billing import BillingPlan

        assert BillingPlan.FREE.value == "free"

    def test_has_starter_plan(self):
        from modules.credit.billing import BillingPlan

        assert BillingPlan.STARTER.value == "starter"

    def test_has_pro_plan(self):
        from modules.credit.billing import BillingPlan

        assert BillingPlan.PRO.value == "pro"

    def test_has_enterprise_plan(self):
        from modules.credit.billing import BillingPlan

        assert BillingPlan.ENTERPRISE.value == "enterprise"

    def test_has_exactly_four_plans(self):
        from modules.credit.billing import BillingPlan

        assert len(BillingPlan) == 4


class TestPlanPricing:
    """Test plan pricing configuration."""

    def test_free_plan_price(self):
        from modules.credit.billing import PLAN_PRICES, BillingPlan

        assert PLAN_PRICES[BillingPlan.FREE] == 0

    def test_starter_plan_price(self):
        from modules.credit.billing import PLAN_PRICES, BillingPlan

        assert PLAN_PRICES[BillingPlan.STARTER] == 2900

    def test_pro_plan_price(self):
        from modules.credit.billing import PLAN_PRICES, BillingPlan

        assert PLAN_PRICES[BillingPlan.PRO] == 9900

    def test_enterprise_plan_is_custom(self):
        from modules.credit.billing import PLAN_PRICES, BillingPlan

        assert PLAN_PRICES[BillingPlan.ENTERPRISE] is None


class TestCreateCheckoutSession:
    """Test Stripe checkout session creation."""

    @patch("modules.credit.billing.stripe")
    def test_creates_checkout_session(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            url="https://checkout.stripe.com/test"
        )
        from modules.credit.billing import create_checkout_session

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
        from modules.credit.billing import create_checkout_session

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
        from modules.credit.billing import record_usage

        record_usage(subscription_item_id="si_test_123", quantity=1)
        mock_stripe.SubscriptionItem.create_usage_record.assert_called_once_with(
            "si_test_123", quantity=1
        )

    @patch("modules.credit.billing.stripe")
    def test_records_usage_graceful_on_error(self, mock_stripe):
        mock_stripe.SubscriptionItem.create_usage_record.side_effect = Exception(
            "API error"
        )
        from modules.credit.billing import record_usage

        # Should not raise
        record_usage(subscription_item_id="si_test_123", quantity=1)


class TestWebhookHandler:
    """Test Stripe webhook processing."""

    @patch("modules.credit.billing.stripe")
    def test_webhook_verifies_signature(self, mock_stripe):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"customer_email": "user@test.com", "subscription": "sub_123"}
            },
        }
        from modules.credit.billing import handle_webhook

        result = handle_webhook(
            payload=b'{"type":"checkout.session.completed"}',
            sig_header="test_sig",
            webhook_secret="whsec_test",
        )
        assert result["status"] == "processed"
        mock_stripe.Webhook.construct_event.assert_called_once()

    @patch("modules.credit.billing.stripe")
    def test_webhook_rejects_invalid_signature(self, mock_stripe):
        mock_stripe.Webhook.construct_event.side_effect = ValueError(
            "Invalid signature"
        )
        from modules.credit.billing import handle_webhook

        result = handle_webhook(
            payload=b"bad", sig_header="bad_sig", webhook_secret="whsec_test"
        )
        assert result["status"] == "error"

    @patch("modules.credit.billing.stripe")
    def test_webhook_handles_subscription_updated(self, mock_stripe):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_123", "status": "active"}},
        }
        from modules.credit.billing import handle_webhook

        result = handle_webhook(
            payload=b"{}", sig_header="sig", webhook_secret="whsec_test"
        )
        assert result["status"] == "processed"

    @patch("modules.credit.billing.stripe")
    def test_webhook_handles_subscription_deleted(self, mock_stripe):
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_123"}},
        }
        from modules.credit.billing import handle_webhook

        result = handle_webhook(
            payload=b"{}", sig_header="sig", webhook_secret="whsec_test"
        )
        assert result["status"] == "processed"


class TestBillingPortal:
    """Test billing portal session creation."""

    @patch("modules.credit.billing.stripe")
    def test_creates_portal_session(self, mock_stripe):
        mock_stripe.billing_portal.Session.create.return_value = MagicMock(
            url="https://billing.stripe.com/portal"
        )
        from modules.credit.billing import create_portal_session

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


class TestSubscriptionStore:
    """Test in-memory subscription tracking."""

    def test_update_subscription_stores_data(self):
        from modules.credit.billing import _subscriptions, update_subscription

        update_subscription("user@test.com", "sub_123", "active", "starter")
        assert _subscriptions["user@test.com"]["subscription_id"] == "sub_123"
        assert _subscriptions["user@test.com"]["status"] == "active"
        assert _subscriptions["user@test.com"]["plan"] == "starter"
        # Clean up
        _subscriptions.pop("user@test.com", None)

    def test_get_subscription_returns_none_for_unknown(self):
        from modules.credit.billing import get_subscription

        assert get_subscription("nobody@test.com") is None

    def test_get_subscription_returns_data(self):
        from modules.credit.billing import (
            _subscriptions,
            get_subscription,
            update_subscription,
        )

        update_subscription("known@test.com", "sub_456", "active", "pro")
        sub = get_subscription("known@test.com")
        assert sub["plan"] == "pro"
        # Clean up
        _subscriptions.pop("known@test.com", None)

    def test_list_subscriptions_empty(self):
        from modules.credit.billing import _subscriptions, list_subscriptions

        _subscriptions.clear()
        assert list_subscriptions() == {}

    def test_list_subscriptions_returns_all(self):
        from modules.credit.billing import (
            _subscriptions,
            list_subscriptions,
            update_subscription,
        )

        _subscriptions.clear()
        update_subscription("a@test.com", "sub_1", "active", "pro")
        update_subscription("b@test.com", "sub_2", "canceled", "starter")
        result = list_subscriptions()
        assert len(result) == 2
        assert "a@test.com" in result
        assert "b@test.com" in result
        _subscriptions.clear()

    def test_count_active_subscriptions(self):
        from modules.credit.billing import (
            _subscriptions,
            count_active_subscriptions,
            update_subscription,
        )

        _subscriptions.clear()
        update_subscription("a@test.com", "sub_1", "active", "pro")
        update_subscription("b@test.com", "sub_2", "canceled", "starter")
        assert count_active_subscriptions() == 1
        _subscriptions.clear()
