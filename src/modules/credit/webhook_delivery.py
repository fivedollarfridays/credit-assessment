"""Webhook delivery subsystem — signatures, retry, dispatch."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

import httpx

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repo_webhooks import WebhookDeliveryRepository
from .webhooks import EventType, WebhookRegistration, get_subscribed_webhooks

MAX_RETRY_DELAY = 300  # seconds

logger = logging.getLogger(__name__)


class WebhookDeliveryStatus(StrEnum):
    """Delivery attempt outcome."""

    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class DeliveryRecord:
    """Result of a single delivery attempt."""

    webhook_id: str
    event_type: EventType
    status: WebhookDeliveryStatus
    status_code: int | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def compute_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def next_retry_delay(attempt: int) -> int:
    """Exponential backoff: 2^attempt seconds, capped at MAX_RETRY_DELAY."""
    return min(2**attempt, MAX_RETRY_DELAY)


async def get_delivery_log(session: AsyncSession, *, webhook_id: str) -> list[dict]:
    """Get delivery history for a webhook from DB."""
    repo = WebhookDeliveryRepository(session)
    entries = await repo.get_by_webhook(webhook_id)
    return [
        {
            "event_type": e.event_type,
            "status": e.status,
            "status_code": e.status_code,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


async def _send_one(
    client: httpx.AsyncClient,
    wh: WebhookRegistration,
    event_type: EventType,
    body: bytes,
    db_factory: async_sessionmaker[AsyncSession],
) -> DeliveryRecord:
    """Deliver a single webhook and record the result."""
    sig = compute_signature(body, wh.secret)
    headers = {"Content-Type": "application/json", "X-Webhook-Signature": sig}
    try:
        resp = await client.post(wh.url, content=body, headers=headers)
        status = (
            WebhookDeliveryStatus.SUCCESS
            if resp.status_code < 400
            else WebhookDeliveryStatus.FAILED
        )
        record = DeliveryRecord(
            webhook_id=wh.id,
            event_type=event_type,
            status=status,
            status_code=resp.status_code,
        )
    except (httpx.HTTPError, OSError) as exc:
        logger.warning("Webhook delivery failed for %s: %s", wh.id, exc)
        record = DeliveryRecord(
            webhook_id=wh.id, event_type=event_type, status=WebhookDeliveryStatus.FAILED
        )
    async with db_factory() as session:
        repo = WebhookDeliveryRepository(session)
        await repo.log_delivery(
            webhook_id=wh.id,
            event_type=event_type,
            status=record.status,
            status_code=record.status_code,
        )
    return record


async def deliver_event(
    *,
    db_factory: async_sessionmaker[AsyncSession],
    event_type: EventType,
    payload: dict,
) -> list[DeliveryRecord]:
    """Deliver an event to all subscribed webhooks. Returns delivery records."""
    async with db_factory() as session:
        matching = await get_subscribed_webhooks(session, event_type)

    if not matching:
        return []

    body = json.dumps({"event": event_type, "data": payload}).encode()
    async with httpx.AsyncClient(timeout=10.0) as http:
        results = await asyncio.gather(
            *(_send_one(http, wh, event_type, body, db_factory) for wh in matching),
            return_exceptions=True,
        )
    return [r for r in results if isinstance(r, DeliveryRecord)]
