"""User data-access layer — stores, queries, and mutations."""

from __future__ import annotations

import re
from collections import OrderedDict

from .roles import Role

# --- In-memory stores ---

_users: dict[str, dict] = {}

_MAX_RESET_TOKENS = 10_000
_reset_tokens: OrderedDict[str, str] = OrderedDict()

_ALLOWED_UPDATE_FIELDS: frozenset[str] = frozenset({"is_active", "org_id"})

# Precompiled regex patterns for password validation.
_RE_UPPERCASE = re.compile(r"[A-Z]")
_RE_LOWERCASE = re.compile(r"[a-z]")
_RE_DIGIT = re.compile(r"\d")
_RE_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def create_user(
    email: str, *, password_hash: str, role: str, org_id: str
) -> dict:
    """Create a new user. Raises ValueError if email already registered."""
    if email in _users:
        raise ValueError("Email already registered")
    user = {
        "email": email,
        "password_hash": password_hash,
        "is_active": True,
        "role": role,
        "org_id": org_id,
    }
    _users[email] = user
    return user


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


def set_password_hash(email: str, password_hash: str) -> None:
    """Update a user's password hash."""
    _users[email]["password_hash"] = password_hash


def store_reset_token(token: str, email: str) -> None:
    """Store a password reset token, evicting oldest if at capacity."""
    _reset_tokens[token] = email
    while len(_reset_tokens) > _MAX_RESET_TOKENS:
        _reset_tokens.popitem(last=False)


def pop_reset_token(token: str) -> str | None:
    """Pop and return the email for a reset token, or None if not found."""
    return _reset_tokens.pop(token, None)
