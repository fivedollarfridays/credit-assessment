"""Auth endpoint routes (token issuance and refresh)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .auth import InvalidTokenError, create_access_token, decode_token
from .config import settings

# Hard-coded demo credentials — replace with database lookup in production.
_DEMO_USERS = {"admin": "admin"}

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    """Credentials for token issuance."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


def _extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


@router.post("/token", response_model=TokenResponse)
def issue_token(creds: TokenRequest) -> TokenResponse:
    """Issue a JWT access token for valid credentials."""
    if _DEMO_USERS.get(creds.username) != creds.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        subject=creds.username,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
    )
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request) -> TokenResponse:
    """Refresh a JWT token. Requires a valid Bearer token."""
    bearer = _extract_bearer_token(request)
    if bearer is None:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    try:
        payload = decode_token(
            bearer, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    token = create_access_token(
        subject=payload["sub"],
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
    )
    return TokenResponse(access_token=token)
