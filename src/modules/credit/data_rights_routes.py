"""API endpoints for GDPR/CCPA data rights."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .assess_routes import verify_auth
from .auth import AuthIdentity
from .data_rights import (
    delete_user_data,
    export_user_data,
    record_consent,
    withdraw_consent,
)
from .database import get_db
from .repo_users import UserRepository
from .roles import Role

router = APIRouter(prefix="/user", tags=["data-rights"])


class ConsentRequest(BaseModel):
    """Request body for recording consent."""

    user_id: str
    consent_version: str


async def _resolve_user_id(
    auth: AuthIdentity, requested_user_id: str | None, db: AsyncSession
) -> str:
    """Resolve effective user_id. Admins may override; others get their own.

    Verifies current role from DB (not just JWT claims) for GDPR-sensitive ops.
    """
    if requested_user_id is not None and requested_user_id != auth.identity:
        repo = UserRepository(db)
        user = await repo.get_by_email(auth.identity)
        if user is not None and user.role == Role.ADMIN.value:
            return requested_user_id
        raise HTTPException(status_code=403, detail="Cannot access another user's data")
    return auth.identity


@router.get("/data-export")
async def data_export(
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = None,
) -> dict:
    """Export all data for a user (GDPR Article 15 / CCPA right to know)."""
    effective_id = await _resolve_user_id(auth, user_id, db)
    return await export_user_data(db, user_id=effective_id)


@router.delete("/data")
async def data_delete(
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = None,
) -> dict:
    """Delete all data for a user (GDPR Article 17 / CCPA right to delete)."""
    effective_id = await _resolve_user_id(auth, user_id, db)
    return await delete_user_data(db, user_id=effective_id)


@router.post("/consent")
async def consent(
    body: ConsentRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record user consent with version tracking."""
    effective_id = await _resolve_user_id(auth, body.user_id, db)
    await record_consent(db, user_id=effective_id, consent_version=body.consent_version)
    return {
        "status": "recorded",
        "user_id": effective_id,
        "version": body.consent_version,
    }


@router.delete("/consent")
async def consent_withdraw(
    body: ConsentRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Withdraw consent for a specific version (GDPR Article 7)."""
    effective_id = await _resolve_user_id(auth, body.user_id, db)
    await withdraw_consent(
        db, user_id=effective_id, consent_version=body.consent_version
    )
    return {
        "status": "withdrawn",
        "user_id": effective_id,
        "version": body.consent_version,
    }
