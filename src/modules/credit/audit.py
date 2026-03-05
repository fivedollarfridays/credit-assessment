"""Compliance audit trail: logging, PII hashing, querying, and retention."""

from __future__ import annotations

import hashlib
import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .repository import AuditRepository

# Default retention: ~7 years (FCRA compliance)
AUDIT_RETENTION_DAYS = 2555


def hash_pii(value: str) -> str:
    """HMAC-SHA256 hash of a PII value for audit storage using dedicated pepper."""
    pepper = settings.pii_pepper
    return hmac.new(pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


async def create_audit_entry(
    session: AsyncSession,
    *,
    action: str,
    user_id: str,
    request_summary: dict,
    result_summary: dict,
    org_id: str | None = None,
) -> dict:
    """Create and store an audit trail entry with hashed PII."""
    repo = AuditRepository(session)
    entry = await repo.create_entry(
        action=action,
        user_id_hash=hash_pii(user_id),
        request_summary=request_summary,
        result_summary=result_summary,
        org_id=org_id,
    )
    return {
        "action": entry.action,
        "user_id_hash": entry.user_id_hash,
        "request_summary": entry.request_summary,
        "result_summary": entry.result_summary,
        "org_id": entry.org_id,
        "timestamp": entry.created_at.isoformat() if entry.created_at else None,
    }


async def get_audit_trail(
    session: AsyncSession,
    *,
    action: str | None = None,
    org_id: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query audit entries with optional filters."""
    repo = AuditRepository(session)
    return await repo.list_entries(action=action, org_id=org_id, limit=limit)


async def count_audit_entries(session: AsyncSession) -> int:
    """Return count of audit entries."""
    repo = AuditRepository(session)
    return await repo.count()


async def purge_audit_trail(
    session: AsyncSession,
    max_age_days: int = AUDIT_RETENTION_DAYS,
) -> int:
    """Purge audit entries older than max_age_days. Returns count purged."""
    repo = AuditRepository(session)
    return await repo.purge_old(max_age_days=max_age_days)
