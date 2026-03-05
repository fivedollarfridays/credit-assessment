"""Data access layer for assessment records and audit logs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
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

    async def create_entry(
        self,
        *,
        action: str,
        user_id_hash: str,
        request_summary: dict,
        result_summary: dict,
        org_id: str | None = None,
    ) -> AuditLog:
        """Create a full audit entry with request/result summaries."""
        entry = AuditLog(
            action=action,
            resource="credit_assessment",
            user_id_hash=user_id_hash,
            request_summary=request_summary,
            result_summary=result_summary,
            org_id=org_id,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def list_entries(
        self,
        *,
        action: str | None = None,
        org_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Query audit entries with optional filters, returned as dicts."""
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if org_id is not None:
            stmt = stmt.where(AuditLog.org_id == org_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "action": r.action,
                "user_id_hash": r.user_id_hash,
                "request_summary": r.request_summary,
                "result_summary": r.result_summary,
                "org_id": r.org_id,
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def purge_old(self, max_age_days: int = 2555) -> int:
        """Delete audit entries older than max_age_days. Returns count deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        result = await self._session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        await self._session.commit()
        return result.rowcount
