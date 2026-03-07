"""Admin endpoints for user and API key management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import get_audit_trail
from .database import get_db
from .rate_limit import limiter
from .repo_api_keys import ApiKeyRepository
from .roles import Role, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class ApiKeyRequest(BaseModel):
    org_id: str
    role: Role
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    api_key: str
    org_id: str
    role: str
    expires_at: str | None = None


@router.get("/users", dependencies=[Depends(require_role(Role.ADMIN))])
@limiter.limit("60/minute")
async def list_users(
    request: Request, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """List all registered users. Admin only."""
    from .repo_users import UserRepository

    repo = UserRepository(db)
    users = await repo.list_all()
    return [
        {
            "email": u.email,
            "role": u.role or Role.VIEWER.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=201,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request, req: ApiKeyRequest, db: AsyncSession = Depends(get_db)
) -> ApiKeyResponse:
    """Create a scoped API key for an organization. Admin only."""
    key = secrets.token_urlsafe(32)
    expires_at: datetime | None = None
    if req.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)
    repo = ApiKeyRepository(db)
    await repo.create(
        key=key, org_id=req.org_id, role=req.role.value, expires_at=expires_at
    )
    return ApiKeyResponse(
        api_key=key,
        org_id=req.org_id,
        role=req.role,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/audit-log", dependencies=[Depends(require_role(Role.ADMIN))])
@limiter.limit("60/minute")
async def audit_log(
    request: Request,
    action: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query audit trail entries with optional filters."""
    entries = await get_audit_trail(db, action=action, limit=limit)
    return {"entries": entries, "count": len(entries)}


@router.delete("/api-keys/{api_key}", dependencies=[Depends(require_role(Role.ADMIN))])
@limiter.limit("10/minute")
async def revoke_api_key(
    request: Request, api_key: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Revoke an API key. Admin only."""
    repo = ApiKeyRepository(db)
    revoked = await repo.revoke(api_key)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked"}
