"""API endpoints for GDPR/CCPA data rights."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .assess_routes import verify_auth
from .data_rights import (
    delete_user_data,
    export_user_data,
    record_consent,
)
from .roles import is_admin
from .user_store import get_user

router = APIRouter(prefix="/user", tags=["data-rights"])


class ConsentRequest(BaseModel):
    """Request body for recording consent."""

    user_id: str
    consent_version: str


def _resolve_user_id(caller_identity: str, requested_user_id: str | None) -> str:
    """Resolve effective user_id. Admins may override; others get their own."""
    if requested_user_id is not None and requested_user_id != caller_identity:
        caller = get_user(caller_identity)
        if is_admin(caller):
            return requested_user_id
        raise HTTPException(status_code=403, detail="Cannot access another user's data")
    return caller_identity


@router.get("/data-export")
def data_export(
    identity: str = Depends(verify_auth), user_id: str | None = None
) -> dict:
    """Export all data for a user (GDPR Article 15 / CCPA right to know)."""
    effective_id = _resolve_user_id(identity, user_id)
    return export_user_data(effective_id)


@router.delete("/data")
def data_delete(
    identity: str = Depends(verify_auth), user_id: str | None = None
) -> dict:
    """Delete all data for a user (GDPR Article 17 / CCPA right to delete)."""
    effective_id = _resolve_user_id(identity, user_id)
    return delete_user_data(effective_id)


@router.post("/consent")
def consent(body: ConsentRequest, identity: str = Depends(verify_auth)) -> dict:
    """Record user consent with version tracking."""
    effective_id = _resolve_user_id(identity, body.user_id)
    record_consent(user_id=effective_id, consent_version=body.consent_version)
    return {
        "status": "recorded",
        "user_id": effective_id,
        "version": body.consent_version,
    }
