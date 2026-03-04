"""Auth endpoint routes (token issuance and refresh)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .assess_routes import verify_auth
from .auth import create_access_token
from .config import settings

# Demo credentials — only active when environment != "production".
_DEMO_USERS = {"admin": "admin"}

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_demo_users() -> dict[str, str]:
    """Return demo users only in non-production environments."""
    if settings.is_production:
        return {}
    return _DEMO_USERS


class TokenRequest(BaseModel):
    """Credentials for token issuance."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
def issue_token(creds: TokenRequest) -> TokenResponse:
    """Issue a JWT access token for valid credentials."""
    if _get_demo_users().get(creds.username) != creds.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        subject=creds.username,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
    )
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(identity: str = Depends(verify_auth)) -> TokenResponse:
    """Refresh a JWT token. Requires a valid Bearer token or API key."""
    if identity == "api-key-user":
        raise HTTPException(status_code=401, detail="Cannot refresh API key")
    token = create_access_token(
        subject=identity,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
    )
    return TokenResponse(access_token=token)
