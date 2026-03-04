"""Role-based access control definitions."""

from __future__ import annotations

import enum

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from .assess_routes import verify_auth


class Role(str, enum.Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


def is_admin(user_data: dict | None) -> bool:
    """Check if user has admin role. Returns False for None."""
    if user_data is None:
        return False
    return user_data.get("role") == Role.ADMIN.value


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_role(*allowed: Role):
    """FastAPI dependency that checks the user has an allowed role."""
    allowed_values = {r.value for r in allowed}

    async def _check(
        request: Request,
        api_key: str | None = Security(_api_key_header),
    ) -> str:
        from .user_routes import get_user

        identity = await verify_auth(request, api_key)
        if identity == "api-key-user":
            raise HTTPException(
                status_code=403,
                detail="API key users cannot access role-restricted endpoints",
            )
        user = get_user(identity)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        user_role = user.get("role", Role.VIEWER.value)
        if user_role not in allowed_values:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return identity

    return _check
