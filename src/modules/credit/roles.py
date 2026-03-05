"""Role-based access control definitions."""

from __future__ import annotations

import enum
import logging

from fastapi import HTTPException, Request, Security

from .assess_routes import verify_auth
from .auth import API_KEY_IDENTITY, api_key_header

_logger = logging.getLogger(__name__)


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


def require_role(*allowed: Role):
    """FastAPI dependency that checks the user has an allowed role."""
    allowed_values = {r.value for r in allowed}

    async def _check(
        request: Request,
        api_key: str | None = Security(api_key_header),
    ) -> str:
        from .repo_users import UserRepository

        auth = await verify_auth(request, api_key)

        # Scoped API key — role comes from the key itself
        if auth.is_scoped_key:
            if auth.role not in allowed_values:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return auth.identity

        # Static API key — no role, reject
        if auth.identity == API_KEY_IDENTITY:
            raise HTTPException(
                status_code=403,
                detail="API key users cannot access role-restricted endpoints",
            )

        # JWT user — use role from token claims if present, else DB lookup
        if auth.role is not None:
            if auth.role not in allowed_values:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return auth.identity
        factory = getattr(request.app.state, "db_session_factory", None)
        if factory is None:
            raise HTTPException(status_code=500, detail="Database not available")
        async with factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email(auth.identity)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        user_role = user.role or Role.VIEWER.value
        if user_role not in allowed_values:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return auth.identity

    return _check
