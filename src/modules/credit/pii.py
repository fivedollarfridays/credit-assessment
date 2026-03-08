"""Shared PII detection and scrubbing utilities."""

from __future__ import annotations

import re
from typing import Any

# Require TLD of 2+ alpha chars to avoid false positives like "version2.0@1.0"
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}"
)
JWT_RE = re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+")
API_KEY_RE = re.compile(r"sk-[a-zA-Z0-9_-]{10,}")
REDACTED = "[REDACTED]"

_MAX_SCRUB_DEPTH = 20


def scrub_string(value: str) -> str:
    """Scrub PII patterns (emails, JWTs, API keys) from a string."""
    value = EMAIL_RE.sub(REDACTED, value)
    value = JWT_RE.sub(REDACTED, value)
    value = API_KEY_RE.sub(REDACTED, value)
    return value


def scrub_value(value: Any, *, _depth: int = 0) -> Any:
    """Recursively scrub PII from a value with depth protection."""
    if _depth >= _MAX_SCRUB_DEPTH:
        return value
    if isinstance(value, str):
        return scrub_string(value)
    if isinstance(value, dict):
        return {k: scrub_value(v, _depth=_depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_value(item, _depth=_depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(item, _depth=_depth + 1) for item in value)
    return value
