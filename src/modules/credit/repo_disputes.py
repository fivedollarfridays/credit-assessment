"""Data access layer for dispute records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .dispute_models import (
    IDENTITY_THEFT_DEADLINE_DAYS,
    STANDARD_DEADLINE_DAYS,
    DisputeStatus,
    VALID_TRANSITIONS,
)
from .letter_types import LetterType
from .models_db import DisputeRecord


class DisputeRepository:
    """CRUD operations for dispute lifecycle records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: str,
        bureau: str,
        negative_item_data: dict,
        org_id: str | None = None,
        letter_type: str | None = None,
    ) -> DisputeRecord:
        """Create a new dispute in DRAFT status."""
        record = DisputeRecord(
            user_id=user_id,
            bureau=bureau,
            negative_item_data=negative_item_data,
            org_id=org_id,
            letter_type=letter_type,
            status=DisputeStatus.DRAFT,
            round=1,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get(self, dispute_id: int, *, user_id: str) -> DisputeRecord | None:
        """Get a dispute by ID, scoped to user."""
        result = await self._session.execute(
            select(DisputeRecord).where(
                DisputeRecord.id == dispute_id,
                DisputeRecord.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        *,
        status_filter: DisputeStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DisputeRecord]:
        """List disputes for a user with optional status filter."""
        stmt = select(DisputeRecord).where(DisputeRecord.user_id == user_id)
        if status_filter is not None:
            stmt = stmt.where(DisputeRecord.status == status_filter)
        stmt = (
            stmt.order_by(DisputeRecord.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self, user_id: str, *, status_filter: DisputeStatus | None = None
    ) -> int:
        """Count disputes for a user, optionally filtered by status."""
        stmt = select(func.count(DisputeRecord.id)).where(
            DisputeRecord.user_id == user_id
        )
        if status_filter is not None:
            stmt = stmt.where(DisputeRecord.status == status_filter)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update_status(
        self,
        dispute_id: int,
        *,
        user_id: str,
        new_status: DisputeStatus,
        resolution: str | None = None,
    ) -> DisputeRecord:
        """Transition a dispute to a new status with validation."""
        record = await self.get(dispute_id, user_id=user_id)
        if record is None:
            raise ValueError(f"Dispute {dispute_id} not found for user {user_id}")

        current = DisputeStatus(record.status)
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from {current} to {new_status}")

        now = datetime.now(timezone.utc)
        record.status = new_status

        if new_status == DisputeStatus.SENT:
            record.sent_at = now
            days = self._deadline_days(record)
            record.deadline_at = now + timedelta(days=days)
            if current == DisputeStatus.ESCALATED:
                record.round += 1

        if new_status == DisputeStatus.RESPONDED:
            record.responded_at = now

        if resolution is not None:
            record.resolution = resolution

        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_approaching_deadlines(
        self,
        *,
        user_id: str,
        days_ahead: int = 7,
        limit: int = 100,
    ) -> list[DisputeRecord]:
        """Return sent/in-review disputes with deadlines within N days for a user."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        result = await self._session.execute(
            select(DisputeRecord)
            .where(
                DisputeRecord.user_id == user_id,
                DisputeRecord.deadline_at.isnot(None),
                DisputeRecord.deadline_at <= cutoff,
                DisputeRecord.deadline_at >= now,
                DisputeRecord.status.in_([DisputeStatus.SENT, DisputeStatus.IN_REVIEW]),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _deadline_days(record: DisputeRecord) -> int:
        """Return FCRA deadline days based on dispute type."""
        item_type = (record.negative_item_data or {}).get("type", "")
        id_theft = LetterType.IDENTITY_THEFT.value
        if item_type == id_theft or record.letter_type == id_theft:
            return IDENTITY_THEFT_DEADLINE_DAYS
        return STANDARD_DEADLINE_DAYS
