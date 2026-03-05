"""JWT token creation and validation."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import jwt
from fastapi.security import APIKeyHeader
from jwt.exceptions import PyJWTError
from pydantic import BaseModel
from starlette.requests import Request

from .config import settings

# Shared constants
API_KEY_IDENTITY = "api-key-user"


@dataclass
class AuthIdentity:
    """Authenticated identity from JWT or API key."""

    identity: str
    org_id: str | None = None
    role: str | None = None
    is_scoped_key: bool = field(default=False)


# Shared API key header dependency (single definition for the whole app).
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or expired."""


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


def extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str,
    expire_minutes: int,
    org_id: str | None = None,
    role: str | None = None,
) -> str:
    """Create a signed JWT access token with optional org_id and role claims."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(minutes=expire_minutes)
    payload: dict = {"sub": subject, "exp": expire, "iat": now}
    if org_id is not None:
        payload["org_id"] = org_id
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict:
    """Decode and validate a JWT token. Raises InvalidTokenError on failure."""
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


def issue_token_for(
    subject: str,
    *,
    org_id: str | None = None,
    role: str | None = None,
) -> str:
    """Create a JWT for *subject* using application settings."""
    return create_access_token(
        subject=subject,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
        org_id=org_id,
        role=role,
    )
