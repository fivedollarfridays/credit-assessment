"""Data access layer for score history records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import ScoreHistory
from .score_models import ScoreSource


class ScoreHistoryRepository:
    """CRUD operations for score history tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        user_id: str,
        score: int,
        score_band: str,
        source: ScoreSource,
        org_id: str | None = None,
        assessment_id: int | None = None,
        notes: str | None = None,
    ) -> ScoreHistory:
        """Record a new score entry."""
        entry = ScoreHistory(
            user_id=user_id,
            score=score,
            score_band=score_band,
            source=source,
            org_id=org_id,
            assessment_id=assessment_id,
            notes=notes,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def get_latest(self, user_id: str) -> ScoreHistory | None:
        """Get the most recent score entry for a user."""
        result = await self._session.execute(
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .order_by(ScoreHistory.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ScoreHistory]:
        """List score history for a user (newest first)."""
        result = await self._session.execute(
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .order_by(ScoreHistory.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trend(self, user_id: str, *, days: int = 90) -> list[ScoreHistory]:
        """Get last 2 score entries within N days for trend calculation."""
        # SQLite stores naive datetimes via func.now(); strip tzinfo to match.
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        result = await self._session.execute(
            select(ScoreHistory)
            .where(
                ScoreHistory.user_id == user_id,
                ScoreHistory.recorded_at >= cutoff,
            )
            .order_by(ScoreHistory.id.desc())
            .limit(2)
        )
        entries = list(result.scalars().all())
        entries.reverse()  # oldest first for trend calculation
        return entries
