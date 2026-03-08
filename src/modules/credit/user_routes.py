"""User management routes: registration, login, password reset."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from .models_db import User
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import create_audit_entry, hash_pii
from .rate_limit import limiter
from .auth import TokenResponse, issue_token_for
from .config import settings
from .database import get_db
from .password import hash_password, verify_password
from .repo_users import ResetTokenRepository, UserRepository
from .roles import Role
from .user_store import validate_password

router = APIRouter(prefix="/auth", tags=["users"])

# Pre-hashed dummy for constant-time response on user-not-found.
# Note: computed per-worker process; each gunicorn worker gets its own value.
# This is acceptable — the hash only needs to be valid bcrypt for timing parity.
_DUMMY_HASH = hash_password("dummy-constant-time-pad")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password(v)


class RegisterResponse(BaseModel):
    email: str
    message: str = "User registered successfully"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResetRequest(BaseModel):
    email: EmailStr


class ResetResponse(BaseModel):
    message: str = "If the email exists, a reset link has been sent"


class ConfirmResetRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password(v)


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("3/minute")
async def register(
    request: Request, req: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """Register a new user with email and password."""
    repo = UserRepository(db)
    if await repo.get_by_email(req.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    await repo.create(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.VIEWER.value,
        org_id=f"org-{uuid.uuid4().hex[:12]}",
    )
    return RegisterResponse(email=req.email)


def _check_lockout(user: User, now: datetime) -> JSONResponse | None:
    """Return a 429 response if the user is currently locked out, else None."""
    if user.locked_until is None:
        return None
    locked = user.locked_until
    if locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)
    if locked > now:
        retry_after = int((locked - now).total_seconds()) + 1
        return JSONResponse(
            status_code=429,
            content={"detail": "Account temporarily locked"},
            headers={"Retry-After": str(retry_after)},
        )
    # Lockout expired — reset
    user.failed_login_attempts = 0
    user.locked_until = None
    return None


@router.post("/login", response_model=None)
@limiter.limit("5/minute")
async def login(
    request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse | JSONResponse:
    """Authenticate user and return JWT token. Locks after repeated failures."""
    repo = UserRepository(db)
    user = await repo.get_by_email(req.email)
    if user is None:
        # Constant-time: run bcrypt even for missing users to prevent timing enumeration
        verify_password("dummy", _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    now = datetime.now(timezone.utc)
    locked_resp = _check_lockout(user, now)
    if locked_resp is not None:
        return locked_resp

    if not verify_password(req.password, user.password_hash) or not user.is_active:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = now + timedelta(
                minutes=settings.lockout_duration_minutes
            )
            await create_audit_entry(
                db,
                action="account_locked",
                user_id=req.email,
                request_summary={"email_hash": hash_pii(req.email)},
                result_summary={
                    "attempts": user.failed_login_attempts,
                    "locked_until": user.locked_until.isoformat(),
                },
            )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Success — reset counter
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    return TokenResponse(
        access_token=issue_token_for(
            req.email, org_id=user.org_id or None, role=user.role or None
        )
    )


@router.post("/reset-password", response_model=ResetResponse)
@limiter.limit("3/minute")
async def request_reset(
    request: Request, req: ResetRequest, db: AsyncSession = Depends(get_db)
) -> ResetResponse:
    """Request a password reset. Returns 200 regardless to prevent enumeration."""
    user_repo = UserRepository(db)
    if await user_repo.get_by_email(req.email) is not None:
        token_repo = ResetTokenRepository(db)
        await token_repo.store(secrets.token_urlsafe(32), req.email)
    return ResetResponse()


@router.post("/confirm-reset")
@limiter.limit("5/minute")
async def confirm_reset(
    request: Request, req: ConfirmResetRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Confirm password reset with token and new password."""
    token_repo = ResetTokenRepository(db)
    email = await token_repo.pop(req.token)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user_repo = UserRepository(db)
    await user_repo.set_password_hash(email, hash_password(req.new_password))
    # Invalidate all remaining reset tokens for this email to prevent reuse
    await token_repo.delete_by_email(email)
    return {"message": "Password reset successfully"}
