"""Data access layer for assessment records."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import AssessmentRecord


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
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> AssessmentRecord:
        """Persist an assessment record and return it with assigned ID."""
        record = AssessmentRecord(
            credit_score=credit_score,
            score_band=score_band,
            barrier_severity=barrier_severity,
            readiness_score=readiness_score,
            request_payload=request_payload,
            response_payload=response_payload,
            user_id=user_id,
            org_id=org_id,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_assessment(self, record_id: int) -> AssessmentRecord | None:
        """Retrieve an assessment record by ID, or None if not found."""
        return await self._session.get(AssessmentRecord, record_id)

    async def get_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AssessmentRecord]:
        """Return assessment records for a specific user with pagination."""
        result = await self._session.execute(
            select(AssessmentRecord)
            .where(AssessmentRecord.user_id == user_id)
            .order_by(AssessmentRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_by_user_id(self, user_id: str, *, commit: bool = True) -> int:
        """Delete all assessment records for a user. Returns count deleted."""
        result = await self._session.execute(
            delete(AssessmentRecord).where(AssessmentRecord.user_id == user_id)
        )
        if commit:
            await self._session.commit()
        return result.rowcount

    async def get_by_org_id(
        self,
        org_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AssessmentRecord]:
        """Return assessment records for a specific org with pagination."""
        result = await self._session.execute(
            select(AssessmentRecord)
            .where(AssessmentRecord.org_id == org_id)
            .order_by(AssessmentRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count all assessment records."""
        result = await self._session.execute(select(func.count(AssessmentRecord.id)))
        return result.scalar_one()

    async def count_by_user_id(self, user_id: str) -> int:
        """Count assessment records for a specific user."""
        result = await self._session.execute(
            select(func.count(AssessmentRecord.id)).where(
                AssessmentRecord.user_id == user_id
            )
        )
        return result.scalar_one()

    async def count_by_org_id(self, org_id: str) -> int:
        """Count assessment records for a specific org."""
        result = await self._session.execute(
            select(func.count(AssessmentRecord.id)).where(
                AssessmentRecord.org_id == org_id
            )
        )
        return result.scalar_one()

    async def list_assessments(self, *, limit: int = 100) -> list[AssessmentRecord]:
        """Return assessment records ordered by creation time."""
        result = await self._session.execute(
            select(AssessmentRecord)
            .order_by(AssessmentRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
