"""GDPR/CCPA data rights: consent, export, deletion, and retention."""

from __future__ import annotations

from datetime import datetime, timezone

from .retention import purge_by_age

# --- In-memory stores (consistent with project pattern) ---
# Unbounded — acceptable for MVP. Cap or migrate to DB before production.
# See also: tenant._org_assessments, webhooks._webhooks.

_consent_records: dict[str, dict] = {}
_user_assessments: dict[str, list[dict]] = {}


def reset_data_rights() -> None:
    """Reset all data rights stores (for testing)."""
    _consent_records.clear()
    _user_assessments.clear()


# --- Consent tracking ---


def record_consent(user_id: str, consent_version: str) -> None:
    """Record that a user gave consent for a specific version."""
    key = f"{user_id}:{consent_version}"
    _consent_records[key] = {
        "user_id": user_id,
        "consent_version": consent_version,
        "consented_at": datetime.now(timezone.utc).isoformat(),
    }


def check_consent(user_id: str, consent_version: str) -> bool:
    """Check if a user has given consent for a specific version."""
    return f"{user_id}:{consent_version}" in _consent_records


def get_consent_record(user_id: str, consent_version: str) -> dict | None:
    """Get the consent record for a user and version."""
    return _consent_records.get(f"{user_id}:{consent_version}")


def withdraw_consent(user_id: str, consent_version: str) -> None:
    """Withdraw consent for a specific version."""
    _consent_records.pop(f"{user_id}:{consent_version}", None)


# --- Assessment data per user ---


def record_user_assessment(user_id: str, assessment: dict) -> None:
    """Store an assessment record for a user."""
    entry = {**assessment, "recorded_at": datetime.now(timezone.utc).isoformat()}
    _user_assessments.setdefault(user_id, []).append(entry)


# --- Data export (right to access) ---


def export_user_data(user_id: str) -> dict:
    """Export all data for a user (GDPR Article 15 / CCPA right to know)."""
    consent_list = [
        rec for key, rec in _consent_records.items() if key.startswith(f"{user_id}:")
    ]
    assessments = _user_assessments.get(user_id, [])
    return {
        "user_id": user_id,
        "consent_records": consent_list,
        "assessments": list(assessments),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Data deletion (right to be forgotten) ---


def delete_user_data(user_id: str) -> dict:
    """Delete all data for a user (GDPR Article 17 / CCPA right to delete)."""
    from .tenant import delete_user_org_assessments

    consent_keys = [k for k in _consent_records if k.startswith(f"{user_id}:")]
    for key in consent_keys:
        del _consent_records[key]

    assessments = _user_assessments.pop(user_id, [])

    # Also remove from org-scoped store (GDPR completeness).
    org_deleted = delete_user_org_assessments(user_id)

    return {
        "user_id": user_id,
        "consent_records_deleted": len(consent_keys),
        "assessments_deleted": len(assessments),
        "org_assessments_deleted": org_deleted,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Data retention / purge ---


def purge_expired_data(max_age_days: int = 365) -> int:
    """Purge assessment records older than max_age_days. Returns count purged."""
    total_purged = 0
    for user_id in list(_user_assessments):
        kept, purged = purge_by_age(
            _user_assessments[user_id],
            timestamp_key="recorded_at",
            max_age_days=max_age_days,
        )
        total_purged += purged
        if kept:
            _user_assessments[user_id] = kept
        else:
            del _user_assessments[user_id]
    return total_purged
