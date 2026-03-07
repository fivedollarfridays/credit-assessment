"""Webhook management API endpoints."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from .assess_routes import verify_auth
from .auth import AuthIdentity
from .config import settings
from .database import get_db
from .rate_limit import limiter
from .webhook_delivery import get_delivery_log, is_non_routable
from .webhooks import (
    EventType,
    create_webhook,
    delete_webhook,
    get_webhook,
    get_webhooks,
)

_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0", "0", "127.0.0.1", "::1"}
# NOTE: Hostname string matching at registration time. DNS rebinding protection
# (re-resolving at delivery time) is handled by _resolve_and_check() in
# webhook_delivery.py — blocks private/loopback/link-local resolved IPs.

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _is_private_ip(hostname: str) -> bool:
    """Return True if hostname is not a globally routable IP."""
    cleaned = hostname.strip("[]")
    try:
        addr = ipaddress.ip_address(cleaned)
    except ValueError:
        return False
    return is_non_routable(addr)


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[EventType]
    secret: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL must start with https:// or http://")
        if settings.is_production and v.startswith("http://"):
            raise ValueError("Production webhooks require https://")
        parsed = urlparse(v)
        hostname = (parsed.hostname or "").lower()
        if hostname in _BLOCKED_HOSTNAMES:
            raise ValueError("URL must not point to localhost or internal addresses")
        if _is_private_ip(hostname):
            raise ValueError("URL must not point to private or reserved IP addresses")
        return v

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters")
        return v


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[EventType]
    is_active: bool


def _to_response(wh) -> WebhookResponse:
    return WebhookResponse(
        id=wh.id, url=wh.url, events=wh.events, is_active=wh.is_active
    )


def _check_ownership(wh, auth: AuthIdentity) -> None:
    """Raise 404 if webhook doesn't belong to the authenticated user."""
    if wh is None or wh.owner_id != auth.identity:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=201,
)
@limiter.limit("10/minute")
async def register_webhook(
    request: Request,
    req: WebhookCreateRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Register a new webhook endpoint."""
    wh = await create_webhook(
        db, url=req.url, events=req.events, secret=req.secret, owner_id=auth.identity
    )
    return _to_response(wh)


@router.get("")
@limiter.limit("60/minute")
async def list_webhooks(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookResponse]:
    """List webhooks owned by the authenticated user."""
    return [_to_response(wh) for wh in await get_webhooks(db, owner_id=auth.identity)]


@router.get("/{webhook_id}/deliveries")
@limiter.limit("60/minute")
async def webhook_deliveries(
    request: Request,
    webhook_id: str,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get delivery log for a specific webhook."""
    wh = await get_webhook(db, webhook_id)
    _check_ownership(wh, auth)
    log = await get_delivery_log(db, webhook_id=webhook_id)
    return {"deliveries": log, "total": len(log)}


@router.delete("/{webhook_id}")
@limiter.limit("10/minute")
async def remove_webhook(
    request: Request,
    webhook_id: str,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a webhook registration."""
    wh = await get_webhook(db, webhook_id)
    _check_ownership(wh, auth)
    await delete_webhook(db, webhook_id)
    return {"message": "Webhook deleted"}
