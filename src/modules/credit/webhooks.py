"""Webhook system — registration CRUD and shared types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from .repo_webhooks import WebhookRepository


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


async def create_webhook(
    session: AsyncSession,
    *,
    url: str,
    events: list[EventType],
    secret: str,
    owner_id: str | None = None,
) -> WebhookRegistration:
    """Register a new webhook endpoint."""
    wh_id = uuid.uuid4().hex[:12]
    repo = WebhookRepository(session)
    db_wh = await repo.create(
        id=wh_id,
        url=url,
        events=[e.value for e in events],
        secret=secret,
        owner_id=owner_id,
    )
    return _to_registration(db_wh)


def _to_registration(db_wh) -> WebhookRegistration:
    """Convert DB model to WebhookRegistration dataclass."""
    return WebhookRegistration(
        id=db_wh.id,
        url=db_wh.url,
        events=[EventType(e) for e in db_wh.events],
        secret=db_wh.secret,
        owner_id=db_wh.owner_id,
        is_active=db_wh.is_active,
    )


async def count_webhooks(session: AsyncSession) -> int:
    """Count registered webhooks."""
    repo = WebhookRepository(session)
    return await repo.count()


async def get_webhooks(
    session: AsyncSession, *, owner_id: str | None = None
) -> list[WebhookRegistration]:
    """List registered webhooks, optionally filtered by owner."""
    repo = WebhookRepository(session)
    if owner_id is not None:
        hooks = await repo.list_by_owner(owner_id)
    else:
        hooks = await repo.list_all()
    return [_to_registration(h) for h in hooks]


async def get_webhook(
    session: AsyncSession, webhook_id: str
) -> WebhookRegistration | None:
    """Get a single webhook by ID."""
    repo = WebhookRepository(session)
    db_wh = await repo.get(webhook_id)
    if db_wh is None:
        return None
    return _to_registration(db_wh)


async def webhook_exists(session: AsyncSession, webhook_id: str) -> bool:
    """Check if a webhook is registered."""
    repo = WebhookRepository(session)
    return await repo.get(webhook_id) is not None


async def get_subscribed_webhooks(
    session: AsyncSession, event_type: EventType
) -> list[WebhookRegistration]:
    """Return active webhooks subscribed to the given event type."""
    repo = WebhookRepository(session)
    hooks = await repo.get_subscribed(event_type.value)
    return [_to_registration(h) for h in hooks]


async def delete_webhook(session: AsyncSession, webhook_id: str) -> bool:
    """Remove a webhook. Returns True if found and removed."""
    repo = WebhookRepository(session)
    return await repo.delete(webhook_id)
