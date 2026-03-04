"""API endpoints for GDPR/CCPA data rights."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .assess_routes import verify_auth
from .data_rights import (
    delete_user_data,
    export_user_data,
    record_consent,
)

router = APIRouter(prefix="/user", tags=["data-rights"])


class ConsentRequest(BaseModel):
    """Request body for recording consent."""

    user_id: str
    consent_version: str


@router.get("/data-export", dependencies=[Depends(verify_auth)])
def data_export(user_id: str) -> dict:
    """Export all data for a user (GDPR Article 15 / CCPA right to know)."""
    return export_user_data(user_id)


@router.delete("/data", dependencies=[Depends(verify_auth)])
def data_delete(user_id: str) -> dict:
    """Delete all data for a user (GDPR Article 17 / CCPA right to delete)."""
    return delete_user_data(user_id)


@router.post("/consent", dependencies=[Depends(verify_auth)])
def consent(body: ConsentRequest) -> dict:
    """Record user consent with version tracking."""
    record_consent(user_id=body.user_id, consent_version=body.consent_version)
    return {
        "status": "recorded",
        "user_id": body.user_id,
        "version": body.consent_version,
    }
