"""Repository classes for GDPR consent and user assessments."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import ConsentRecord, UserAssessment


class ConsentRepository:
    """CRUD operations for GDPR consent records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user_id: str, consent_version: str) -> ConsentRecord:
        rec = ConsentRecord(user_id=user_id, consent_version=consent_version)
        self._session.add(rec)
        await self._session.commit()
        await self._session.refresh(rec)
        return rec

    async def check(self, user_id: str, consent_version: str) -> bool:
        result = await self._session.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_version == consent_version,
            )
        )
        return result.scalar_one() > 0

    async def withdraw(self, user_id: str, consent_version: str) -> bool:
        result = await self._session.execute(
            delete(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_version == consent_version,
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def get_by_user(self, user_id: str) -> list[ConsentRecord]:
        result = await self._session.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == user_id)
        )
        return list(result.scalars().all())


class UserAssessmentRepository:
    """CRUD operations for per-user assessment records (GDPR)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user_id: str, assessment_data: dict) -> UserAssessment:
        rec = UserAssessment(user_id=user_id, assessment_data=assessment_data)
        self._session.add(rec)
        await self._session.commit()
        await self._session.refresh(rec)
        return rec

    async def get_by_user(self, user_id: str) -> list[UserAssessment]:
        result = await self._session.execute(
            select(UserAssessment)
            .where(UserAssessment.user_id == user_id)
            .order_by(UserAssessment.recorded_at.desc())
        )
        return list(result.scalars().all())

    async def delete_by_user(self, user_id: str) -> int:
        result = await self._session.execute(
            delete(UserAssessment).where(UserAssessment.user_id == user_id)
        )
        await self._session.commit()
        return result.rowcount
