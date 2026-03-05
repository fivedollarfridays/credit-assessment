"""User management routes: registration, login, password reset."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from .auth import TokenResponse, issue_token_for
from .password import hash_password, verify_password
from .roles import Role
from .user_store import (
    create_user,
    get_user,
    pop_reset_token,
    set_password_hash,
    store_reset_token,
    validate_password,
)

router = APIRouter(prefix="/auth", tags=["users"])


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
def register(req: RegisterRequest) -> RegisterResponse:
    """Register a new user with email and password."""
    if get_user(req.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    create_user(
        req.email,
        password_hash=hash_password(req.password),
        role=Role.VIEWER.value,
        org_id=f"org-{req.email.split('@')[0]}",
    )
    return RegisterResponse(email=req.email)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT token."""
    user = get_user(req.email)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token_for(req.email))


@router.post("/reset-password", response_model=ResetResponse)
def request_reset(req: ResetRequest) -> ResetResponse:
    """Request a password reset. Returns 200 regardless to prevent enumeration."""
    if get_user(req.email) is not None:
        store_reset_token(secrets.token_urlsafe(32), req.email)
    return ResetResponse()


@router.post("/confirm-reset")
def confirm_reset(req: ConfirmResetRequest) -> dict:
    """Confirm password reset with token and new password."""
    email = pop_reset_token(req.token)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    set_password_hash(email, hash_password(req.new_password))
    return {"message": "Password reset successfully"}
