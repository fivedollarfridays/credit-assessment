"""GDPR/CCPA data rights: consent, export, deletion, and retention."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .repo_data_rights import ConsentRepository, UserAssessmentRepository
from .repo_assessments import AssessmentRepository


def _consent_to_dict(rec: object) -> dict:
    """Convert a ConsentRecord ORM object to a plain dict."""
    return {
        "user_id": rec.user_id,
        "consent_version": rec.consent_version,
        "consented_at": rec.consented_at.isoformat() if rec.consented_at else None,
    }


# --- Consent tracking ---


async def record_consent(
    session: AsyncSession, *, user_id: str, consent_version: str
) -> None:
    """Record that a user gave consent for a specific version."""
    repo = ConsentRepository(session)
    await repo.record(user_id, consent_version)


async def check_consent(
    session: AsyncSession, *, user_id: str, consent_version: str
) -> bool:
    """Check if a user has given consent for a specific version."""
    repo = ConsentRepository(session)
    return await repo.check(user_id, consent_version)


async def get_consent_record(
    session: AsyncSession, *, user_id: str, consent_version: str
) -> dict | None:
    """Get the consent record for a user and version."""
    repo = ConsentRepository(session)
    rec = await repo.get_one(user_id, consent_version)
    return _consent_to_dict(rec) if rec else None


async def withdraw_consent(
    session: AsyncSession, *, user_id: str, consent_version: str
) -> None:
    """Withdraw consent for a specific version."""
    repo = ConsentRepository(session)
    await repo.withdraw(user_id, consent_version)


# --- Assessment data per user ---


async def record_user_assessment(
    session: AsyncSession, *, user_id: str, assessment: dict
) -> None:
    """Store an assessment record for a user."""
    repo = UserAssessmentRepository(session)
    await repo.record(user_id, assessment)


# --- Data export (right to access) ---


async def export_user_data(session: AsyncSession, *, user_id: str) -> dict:
    """Export all data for a user (GDPR Article 15 / CCPA right to know)."""
    consent_repo = ConsentRepository(session)
    assessment_repo = UserAssessmentRepository(session)
    db_assessment_repo = AssessmentRepository(session)

    consent_records = await consent_repo.get_by_user(user_id)
    consent_list = [_consent_to_dict(rec) for rec in consent_records]

    user_assessments = await assessment_repo.get_by_user(user_id)
    assessment_list = [rec.assessment_data for rec in user_assessments]

    db_assessments = await db_assessment_repo.get_by_user_id(user_id)
    for rec in db_assessments:
        assessment_list.append(rec.response_payload)

    return {
        "user_id": user_id,
        "consent_records": consent_list,
        "assessments": assessment_list,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Data deletion (right to be forgotten) ---


async def delete_user_data(session: AsyncSession, *, user_id: str) -> dict:
    """Delete all data for a user (GDPR Article 17 / CCPA right to delete).

    All deletes run in a single transaction for atomicity.
    """
    consent_repo = ConsentRepository(session)
    assessment_repo = UserAssessmentRepository(session)
    db_assessment_repo = AssessmentRepository(session)

    consent_deleted = await consent_repo.delete_by_user(user_id, commit=False)
    assessments_deleted = await assessment_repo.delete_by_user(user_id, commit=False)
    db_assessments_deleted = await db_assessment_repo.delete_by_user_id(
        user_id, commit=False
    )
    await session.commit()

    return {
        "user_id": user_id,
        "consent_records_deleted": consent_deleted,
        "assessments_deleted": assessments_deleted + db_assessments_deleted,
        "db_assessments_deleted": db_assessments_deleted,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Data retention / purge ---


async def purge_expired_data(session: AsyncSession, *, max_age_days: int = 365) -> int:
    """Purge user assessment records older than max_age_days. Returns count."""
    repo = UserAssessmentRepository(session)
    return await repo.purge_by_age(max_age_days)
