"""Webhook management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .assess_routes import verify_auth
from .webhooks import (
    EventType,
    create_webhook,
    delete_webhook,
    get_delivery_log,
    get_webhooks,
    webhook_exists,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[EventType]
    secret: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL must start with https:// or http://")
        return v

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("Secret must be at least 16 characters")
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


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=201,
    dependencies=[Depends(verify_auth)],
)
def register_webhook(req: WebhookCreateRequest) -> WebhookResponse:
    """Register a new webhook endpoint."""
    wh = create_webhook(url=req.url, events=req.events, secret=req.secret)
    return _to_response(wh)


@router.get("", dependencies=[Depends(verify_auth)])
def list_webhooks() -> list[WebhookResponse]:
    """List all registered webhooks."""
    return [_to_response(wh) for wh in get_webhooks()]


@router.get("/{webhook_id}/deliveries", dependencies=[Depends(verify_auth)])
def webhook_deliveries(webhook_id: str) -> dict:
    """Get delivery log for a specific webhook."""
    if not webhook_exists(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    log = get_delivery_log(webhook_id=webhook_id)
    return {"deliveries": log, "total": len(log)}


@router.delete("/{webhook_id}", dependencies=[Depends(verify_auth)])
def remove_webhook(webhook_id: str) -> dict:
    """Delete a webhook registration."""
    if not delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}
