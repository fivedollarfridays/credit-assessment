"""Auth endpoint routes (token issuance and refresh)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .assess_routes import verify_auth
from .auth import API_KEY_IDENTITY, TokenResponse, issue_token_for
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


@router.post("/token", response_model=TokenResponse)
def issue_token(creds: TokenRequest) -> TokenResponse:
    """Issue a JWT access token for valid credentials."""
    if _get_demo_users().get(creds.username) != creds.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token_for(creds.username))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(identity: str = Depends(verify_auth)) -> TokenResponse:
    """Refresh a JWT token. Requires a valid Bearer token or API key."""
    if identity == API_KEY_IDENTITY:
        raise HTTPException(status_code=401, detail="Cannot refresh API key")
    return TokenResponse(access_token=issue_token_for(identity))
