"""User utilities — password validation."""

from __future__ import annotations

import re

# Precompiled regex patterns for password validation.
_RE_UPPERCASE = re.compile(r"[A-Z]")
_RE_LOWERCASE = re.compile(r"[a-z]")
_RE_DIGIT = re.compile(r"\d")
_RE_SPECIAL = re.compile(r"[^A-Za-z0-9]")


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
