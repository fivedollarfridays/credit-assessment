"""JWT token creation and validation."""

from __future__ import annotations

import datetime

from jose import JWTError, jwt


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or expired."""


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str,
    expire_minutes: int,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "exp": expire, "iat": now}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict:
    """Decode and validate a JWT token. Raises InvalidTokenError on failure."""
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
