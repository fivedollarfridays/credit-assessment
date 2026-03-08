"""Background tasks for assessment persistence, usage metering, and score history."""

from __future__ import annotations

import logging

from .audit import create_audit_entry
from .billing import get_subscription, record_usage
from .repo_assessments import AssessmentRepository
from .repo_scores import ScoreHistoryRepository
from .score_models import ScoreSource
from .types import CreditAssessmentResult, CreditProfile

logger = logging.getLogger(__name__)


async def persist_assessment(
    factory: object,
    profile: CreditProfile,
    result: CreditAssessmentResult,
    user_id: str | None = None,
    org_id: str | None = None,
) -> None:
    """Persist assessment result and compliance audit entry (background task)."""
    try:
        async with factory() as session:
            repo = AssessmentRepository(session)
            await repo.save_assessment(
                credit_score=profile.current_score,
                score_band=profile.score_band.value,
                barrier_severity=result.barrier_severity.value,
                readiness_score=result.readiness.score,
                request_payload=profile.model_dump(mode="json"),
                response_payload=result.model_dump(mode="json"),
                user_id=user_id,
                org_id=org_id,
            )
            await create_audit_entry(
                session,
                action="assessment_run",
                user_id=user_id or "anonymous",
                request_summary={"endpoint": "/assess"},
                result_summary={
                    "score_band": result.readiness.score_band.value,
                    "barrier_severity": result.barrier_severity.value,
                },
                org_id=org_id,
            )
    except Exception:
        logger.warning("Failed to persist assessment", exc_info=True)


async def record_usage_for_user(factory: object, identity: str) -> None:
    """Look up user's subscription and record usage (background task)."""
    try:
        async with factory() as session:
            sub = await get_subscription(session, identity)
            if sub and sub["status"] == "active":
                record_usage(subscription_item_id=sub["subscription_id"])
    except Exception:
        logger.debug("Usage metering skipped", exc_info=True)


async def record_score_history(
    factory: object,
    profile: CreditProfile,
    user_id: str,
    org_id: str | None = None,
) -> None:
    """Auto-record score to history after assessment (background task)."""
    try:
        async with factory() as session:
            repo = ScoreHistoryRepository(session)
            await repo.record(
                user_id=user_id,
                score=profile.current_score,
                score_band=profile.score_band.value,
                source=ScoreSource.ASSESSMENT,
                org_id=org_id,
            )
    except Exception:
        logger.warning("Failed to record score history", exc_info=True)
