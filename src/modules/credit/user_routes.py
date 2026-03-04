"""User management routes: registration, login, password reset."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from .auth import create_access_token
from .config import settings
from .password import hash_password, verify_password
from .roles import Role

router = APIRouter(prefix="/auth", tags=["users"])

# In-memory user store — replaced by DB repository in production.
_users: dict[str, dict] = {}
_reset_tokens: dict[str, str] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    email: str
    message: str = "User registered successfully"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResetRequest(BaseModel):
    email: EmailStr


class ResetResponse(BaseModel):
    message: str = "If the email exists, a reset link has been sent"
    reset_token: str | None = None


class ConfirmResetRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(req: RegisterRequest) -> RegisterResponse:
    """Register a new user with email and password."""
    if req.email in _users:
        raise HTTPException(status_code=409, detail="Email already registered")
    _users[req.email] = {
        "email": req.email,
        "password_hash": hash_password(req.password),
        "is_active": True,
        "role": Role.VIEWER.value,
        "org_id": f"org-{req.email.split('@')[0]}",
    }
    return RegisterResponse(email=req.email)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    """Authenticate user and return JWT token."""
    user = _users.get(req.email)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        subject=req.email,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expiry_minutes,
    )
    return LoginResponse(access_token=token)


@router.post("/reset-password", response_model=ResetResponse)
def request_reset(req: ResetRequest) -> ResetResponse:
    """Request a password reset. Returns 200 regardless to prevent enumeration."""
    token = None
    if req.email in _users:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = req.email
    return ResetResponse(reset_token=token)


@router.post("/confirm-reset")
def confirm_reset(req: ConfirmResetRequest) -> dict:
    """Confirm password reset with token and new password."""
    email = _reset_tokens.pop(req.token, None)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    _users[email]["password_hash"] = hash_password(req.new_password)
    return {"message": "Password reset successfully"}
