"""Data access layer for assessment records and audit logs."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import AssessmentRecord, AuditLog


class AssessmentRepository:
    """CRUD operations for assessment records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_assessment(
        self,
        *,
        credit_score: int,
        score_band: str,
        barrier_severity: str,
        readiness_score: int,
        request_payload: dict,
        response_payload: dict,
    ) -> AssessmentRecord:
        """Persist an assessment record and return it with assigned ID."""
        record = AssessmentRecord(
            credit_score=credit_score,
            score_band=score_band,
            barrier_severity=barrier_severity,
            readiness_score=readiness_score,
            request_payload=request_payload,
            response_payload=response_payload,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_assessment(self, record_id: int) -> AssessmentRecord | None:
        """Retrieve an assessment record by ID, or None if not found."""
        return await self._session.get(AssessmentRecord, record_id)

    async def list_assessments(self, *, limit: int = 100) -> list[AssessmentRecord]:
        """Return assessment records ordered by creation time."""
        result = await self._session.execute(
            select(AssessmentRecord)
            .order_by(AssessmentRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AuditRepository:
    """CRUD operations for audit log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_action(
        self,
        *,
        action: str,
        resource: str,
        detail: dict | None = None,
        user_id_hash: str | None = None,
        org_id: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            action=action,
            resource=resource,
            detail=detail,
            user_id_hash=user_id_hash,
            org_id=org_id,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def count(self) -> int:
        """Count total audit entries."""
        result = await self._session.execute(select(func.count(AuditLog.id)))
        return result.scalar_one()

    async def list_by_action(self, action: str) -> list[AuditLog]:
        """Return audit entries filtered by action."""
        result = await self._session.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())
