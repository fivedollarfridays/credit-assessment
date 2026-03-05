"""User management routes: registration, login, password reset."""

from __future__ import annotations

import re
import secrets
from collections import OrderedDict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from .auth import TokenResponse, issue_token_for
from .password import hash_password, verify_password
from .roles import Role

router = APIRouter(prefix="/auth", tags=["users"])

# In-memory user store — replaced by DB repository in production.
_users: dict[str, dict] = {}

_MAX_RESET_TOKENS = 10_000
_reset_tokens: OrderedDict[str, str] = OrderedDict()

_ALLOWED_UPDATE_FIELDS: frozenset[str] = frozenset({"is_active", "org_id"})

# Precompiled regex patterns for password validation.
_RE_UPPERCASE = re.compile(r"[A-Z]")
_RE_LOWERCASE = re.compile(r"[a-z]")
_RE_DIGIT = re.compile(r"\d")
_RE_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def get_all_users() -> dict[str, dict]:
    """Return a copy of all users keyed by email."""
    return dict(_users)


def get_user(email: str) -> dict | None:
    """Get a user by email. Returns None if not found."""
    return _users.get(email)


def count_users() -> int:
    """Return the number of registered users."""
    return len(_users)


def validate_password(password: str) -> str:
    """Validate password complexity. Returns password if valid, raises ValueError otherwise.

    Requirements: min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not _RE_UPPERCASE.search(password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not _RE_LOWERCASE.search(password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not _RE_DIGIT.search(password):
        raise ValueError("Password must contain at least one digit")
    if not _RE_SPECIAL.search(password):
        raise ValueError("Password must contain at least one special character")
    return password


def update_user(email: str, **fields: object) -> dict | None:
    """Update user fields by email. Only allowlisted fields are applied."""
    user = _users.get(email)
    if user is None:
        return None
    safe_fields = {k: v for k, v in fields.items() if k in _ALLOWED_UPDATE_FIELDS}
    user.update(safe_fields)
    return user


def set_user_role(email: str, role: Role) -> dict | None:
    """Set a user's role. Privileged -- callers must enforce admin auth."""
    user = _users.get(email)
    if user is None:
        return None
    user["role"] = role.value
    return user


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


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT token."""
    user = _users.get(req.email)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token_for(req.email))


@router.post("/reset-password", response_model=ResetResponse)
def request_reset(req: ResetRequest) -> ResetResponse:
    """Request a password reset. Returns 200 regardless to prevent enumeration."""
    if req.email in _users:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = req.email
        while len(_reset_tokens) > _MAX_RESET_TOKENS:
            _reset_tokens.popitem(last=False)
    return ResetResponse()


@router.post("/confirm-reset")
def confirm_reset(req: ConfirmResetRequest) -> dict:
    """Confirm password reset with token and new password."""
    email = _reset_tokens.pop(req.token, None)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    _users[email]["password_hash"] = hash_password(req.new_password)
    return {"message": "Password reset successfully"}
