"""Shared time-based data retention utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def purge_by_age(
    records: list[dict],
    *,
    timestamp_key: str,
    max_age_days: int,
) -> tuple[list[dict], int]:
    """Purge records older than max_age_days.

    Returns (kept_records, purged_count). Records with unparseable
    timestamps are kept (fail-safe).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    kept: list[dict] = []
    purged = 0
    for record in records:
        ts_str = record.get(timestamp_key, "")
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts >= cutoff:
                kept.append(record)
            else:
                purged += 1
        except (ValueError, TypeError):
            kept.append(record)
    return kept, purged
