"""Stripe billing integration: subscriptions, usage metering, webhooks."""

from __future__ import annotations

import logging

import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError as _StripeSignatureError

from .rate_limit import SubscriptionTier
from .repo_billing import SubscriptionRepository

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


async def update_subscription(
    session: AsyncSession, email: str, subscription_id: str, status: str, plan: str
) -> None:
    """Persist subscription record to database."""
    repo = SubscriptionRepository(session)
    await repo.upsert(email, subscription_id, status, plan)


async def get_subscription(session: AsyncSession, email: str) -> dict | None:
    """Get subscription for a user. Returns dict or None."""
    repo = SubscriptionRepository(session)
    sub = await repo.get_by_email(email)
    if sub is None:
        return None
    return {
        "subscription_id": sub.subscription_id,
        "status": sub.status,
        "plan": sub.plan,
    }


async def list_subscriptions(session: AsyncSession) -> list[dict]:
    """Return all subscriptions as list of dicts."""
    repo = SubscriptionRepository(session)
    subs = await repo.list_all()
    return [
        {
            "email": s.email,
            "subscription_id": s.subscription_id,
            "status": s.status,
            "plan": s.plan,
        }
        for s in subs
    ]


async def count_active_subscriptions(session: AsyncSession) -> int:
    """Count subscriptions with status 'active'."""
    repo = SubscriptionRepository(session)
    return await repo.count_active()


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


async def handle_webhook(
    *,
    session: AsyncSession,
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
) -> dict:
    """Process a Stripe webhook event, persisting subscription changes to DB."""
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
            await update_subscription(
                session, email, sub_id, "active", SubscriptionTier.STARTER.value
            )
    elif event_type == "customer.subscription.updated":
        email = data.get("customer_email")
        sub_id = data.get("id")
        if email and sub_id:
            status = data.get("status", "active")
            plan = _extract_plan(data)
            await update_subscription(session, email, sub_id, status, plan)
        else:
            logger.info("Subscription updated: %s", data.get("id"))
    elif event_type == "customer.subscription.deleted":
        email = data.get("customer_email")
        sub_id = data.get("id")
        if email and sub_id:
            await update_subscription(session, email, sub_id, "canceled", "free")
        else:
            logger.info("Subscription deleted: %s", data.get("id"))

    return {"status": "processed"}


def _extract_plan(data: dict) -> str:
    """Extract plan name from Stripe subscription data."""
    items = data.get("items", {}).get("data", [])
    if items:
        nickname = items[0].get("plan", {}).get("nickname")
        if nickname:
            return nickname.lower()
    return "starter"
