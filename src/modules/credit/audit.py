"""Compliance audit trail: logging, PII hashing, querying, and retention."""

from __future__ import annotations

import hashlib
import hmac
import itertools
from collections import deque
from datetime import datetime, timedelta, timezone

from .config import settings

# Default retention: ~7 years (FCRA compliance)
AUDIT_RETENTION_DAYS = 2555
MAX_AUDIT_ENTRIES = 100_000

_audit_entries: deque[dict] = deque(maxlen=MAX_AUDIT_ENTRIES)


def count_audit_entries() -> int:
    """Return count of audit entries without copying."""
    return len(_audit_entries)


def reset_audit_trail() -> None:
    """Reset all audit entries (for testing)."""
    _audit_entries.clear()


def hash_pii(value: str) -> str:
    """HMAC-SHA256 hash of a PII value for audit storage using dedicated pepper."""
    pepper = settings.pii_pepper
    return hmac.new(pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_audit_entry(
    *,
    action: str,
    user_id: str,
    request_summary: dict,
    result_summary: dict,
    org_id: str | None = None,
) -> dict:
    """Create and store an audit trail entry with hashed PII."""
    entry: dict = {
        "action": action,
        "user_id_hash": hash_pii(user_id),
        "request_summary": request_summary,
        "result_summary": result_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if org_id is not None:
        entry["org_id"] = org_id
    _audit_entries.append(entry)
    return entry


def get_audit_trail(
    *,
    action: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query audit entries with optional filters."""
    it = iter(_audit_entries)
    if action is not None:
        it = (e for e in it if e["action"] == action)
    if limit is not None:
        it = itertools.islice(it, limit)
    return list(it)


def purge_audit_trail(max_age_days: int = AUDIT_RETENTION_DAYS) -> int:
    """Purge audit entries older than max_age_days. Returns count purged.

    Relies on chronological insertion order and consistent ISO 8601 format
    (datetime.isoformat() produces +00:00 suffix, never Z). Lexicographic
    comparison is safe under these invariants.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    purged = 0
    while _audit_entries and _audit_entries[0]["timestamp"] < cutoff:
        _audit_entries.popleft()
        purged += 1
    return purged
