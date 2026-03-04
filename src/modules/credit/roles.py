"""Role-based access control definitions."""

from __future__ import annotations

import enum

from fastapi import HTTPException, Request

from .auth import InvalidTokenError, decode_token, extract_bearer_token
from .config import settings


class Role(str, enum.Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


def require_role(*allowed: Role):
    """FastAPI dependency that checks the user has an allowed role."""
    allowed_values = {r.value for r in allowed}

    def _check(request: Request) -> str:
        from .user_routes import _users

        bearer = extract_bearer_token(request)
        if bearer is None:
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        try:
            payload = decode_token(
                bearer, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
            )
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        email = payload["sub"]
        user = _users.get(email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        user_role = user.get("role", Role.VIEWER.value)
        if user_role not in allowed_values:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return email

    return _check
