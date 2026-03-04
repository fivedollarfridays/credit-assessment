"""Stripe billing integration: subscriptions, usage metering, webhooks."""

from __future__ import annotations

import logging

import stripe
from stripe import SignatureVerificationError as _StripeSignatureError

from .rate_limit import SubscriptionTier

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
BillingPlan = SubscriptionTier

# Prices in cents. None = custom pricing.
PLAN_PRICES: dict[SubscriptionTier, int | None] = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.STARTER: 2900,
    SubscriptionTier.PRO: 9900,
    SubscriptionTier.ENTERPRISE: None,
}

# In-memory subscription store — replaced by DB in production.
_subscriptions: dict[str, dict] = {}


def update_subscription(
    email: str, subscription_id: str, status: str, plan: str
) -> None:
    """Update local subscription record."""
    _subscriptions[email] = {
        "subscription_id": subscription_id,
        "status": status,
        "plan": plan,
    }


def get_subscription(email: str) -> dict | None:
    """Get subscription for a user. Returns None if not found."""
    return _subscriptions.get(email)


def create_checkout_session(
    *,
    customer_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
):
    """Create a Stripe Checkout Session for subscription signup."""
    return stripe.checkout.Session.create(
        customer_email=customer_email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
    )


def record_usage(*, subscription_item_id: str, quantity: int = 1) -> None:
    """Record a usage event for metered billing."""
    try:
        stripe.SubscriptionItem.create_usage_record(
            subscription_item_id, quantity=quantity
        )
    except Exception:
        logger.warning("Failed to record usage event for %s", subscription_item_id)


def create_portal_session(*, customer_id: str, return_url: str):
    """Create a Stripe Billing Portal session for self-service management."""
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def handle_webhook(*, payload: bytes, sig_header: str, webhook_secret: str) -> dict:
    """Process a Stripe webhook event."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, _StripeSignatureError):
        return {"status": "error", "detail": "Invalid payload"}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        email = data.get("customer_email")
        sub_id = data.get("subscription")
        if email and sub_id:
            update_subscription(email, sub_id, "active", SubscriptionTier.STARTER.value)
    elif event_type == "customer.subscription.updated":
        logger.info("Subscription updated: %s", data.get("id"))
    elif event_type == "customer.subscription.deleted":
        logger.info("Subscription deleted: %s", data.get("id"))

    return {"status": "processed"}
