"""Admin endpoints for user and API key management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .audit import get_audit_trail
from .roles import Role, require_role
from .user_routes import get_all_users

router = APIRouter(prefix="/admin", tags=["admin"])

# In-memory API key store — replaced by DB in production.
_api_keys: dict[str, dict] = {}


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
def list_users() -> list[dict]:
    """List all registered users. Admin only."""
    return [
        {
            "email": email,
            "role": u.get("role", Role.VIEWER.value),
            "is_active": u.get("is_active", True),
        }
        for email, u in get_all_users().items()
    ]


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=201,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def create_api_key(req: ApiKeyRequest) -> ApiKeyResponse:
    """Create a scoped API key for an organization. Admin only."""
    key = secrets.token_urlsafe(32)
    expires_at = None
    if req.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)
    _api_keys[key] = {"org_id": req.org_id, "role": req.role, "expires_at": expires_at}
    return ApiKeyResponse(
        api_key=key,
        org_id=req.org_id,
        role=req.role,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/audit-log", dependencies=[Depends(require_role(Role.ADMIN))])
def audit_log(action: str | None = None, limit: int | None = None) -> dict:
    """Query audit trail entries with optional filters."""
    entries = get_audit_trail(action=action, limit=limit)
    return {"entries": entries, "total": len(entries)}


@router.delete("/api-keys/{api_key}", dependencies=[Depends(require_role(Role.ADMIN))])
def revoke_api_key(api_key: str) -> dict:
    """Revoke an API key. Admin only."""
    if _api_keys.pop(api_key, None) is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked"}
