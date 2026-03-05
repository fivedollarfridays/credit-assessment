"""Webhook system — registration CRUD and shared types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    """Supported webhook event types."""

    ASSESSMENT_COMPLETED = "assessment.completed"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    RATE_LIMIT_WARNING = "rate_limit.warning"


@dataclass
class WebhookRegistration:
    """A registered webhook endpoint."""

    id: str
    url: str
    events: list[EventType]
    secret: str
    owner_id: str | None = None
    is_active: bool = True


# --- In-memory store ---
# _webhooks is unbounded — acceptable for MVP. Cap or migrate to DB.

_webhooks: dict[str, WebhookRegistration] = {}


def reset_webhooks() -> None:
    """Clear all registrations and delivery logs (testing)."""
    _webhooks.clear()
    from .webhook_delivery import reset_delivery_log

    reset_delivery_log()


def create_webhook(
    *,
    url: str,
    events: list[EventType],
    secret: str,
    owner_id: str | None = None,
) -> WebhookRegistration:
    """Register a new webhook endpoint."""
    wh = WebhookRegistration(
        id=uuid.uuid4().hex[:12],
        url=url,
        events=events,
        secret=secret,
        owner_id=owner_id,
    )
    _webhooks[wh.id] = wh
    return wh


def count_webhooks() -> int:
    """Count registered webhooks without copying."""
    return len(_webhooks)


def get_webhooks(*, owner_id: str | None = None) -> list[WebhookRegistration]:
    """List registered webhooks, optionally filtered by owner."""
    hooks = list(_webhooks.values())
    if owner_id is not None:
        hooks = [h for h in hooks if h.owner_id == owner_id]
    return hooks


def webhook_exists(webhook_id: str) -> bool:
    """Check if a webhook is registered."""
    return webhook_id in _webhooks


def get_subscribed_webhooks(event_type: EventType) -> list[WebhookRegistration]:
    """Return active webhooks subscribed to the given event type."""
    return [
        wh for wh in _webhooks.values() if event_type in wh.events and wh.is_active
    ]


def delete_webhook(webhook_id: str) -> bool:
    """Remove a webhook. Returns True if found and removed."""
    return _webhooks.pop(webhook_id, None) is not None
