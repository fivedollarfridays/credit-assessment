"""Score history endpoint routes — timeline, manual entry, trend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .assess_routes import verify_auth
from .auth import AuthIdentity
from .database import get_db
from .rate_limit import limiter
from .models_db import ScoreHistory
from .repo_scores import ScoreHistoryRepository
from .score_models import ScoreSource
from .types import ScoreBand

router = APIRouter()


class ManualScoreRequest(BaseModel):
    """Request body for manual score entry."""

    score: int = Field(ge=300, le=850)
    score_band: ScoreBand
    notes: str | None = Field(default=None, max_length=500)


def _entry_to_dict(record: ScoreHistory) -> dict:
    """Convert a ScoreHistory record to a JSON-serializable dict."""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "score": record.score,
        "score_band": record.score_band,
        "source": record.source,
        "assessment_id": record.assessment_id,
        "notes": record.notes,
        "recorded_at": (record.recorded_at.isoformat() if record.recorded_at else None),
    }


def _compute_trend(entries: list) -> tuple[str, int]:
    """Compute trend direction and delta from score entries (oldest-first)."""
    if len(entries) < 2:
        return "stable", 0
    delta = entries[-1].score - entries[-2].score
    if delta > 0:
        return "up", delta
    if delta < 0:
        return "down", delta
    return "stable", 0


@router.get("/scores/history")
@limiter.limit("60/minute")
async def get_score_history(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Get paginated score history with trend analysis."""
    repo = ScoreHistoryRepository(db)
    entries = await repo.list_by_user(auth.identity, limit=limit, offset=offset)
    latest = (
        entries[0] if entries and offset == 0 else await repo.get_latest(auth.identity)
    )
    trend_entries = await repo.get_trend(auth.identity, days=days)
    trend, delta = _compute_trend(trend_entries)
    return {
        "entries": [_entry_to_dict(e) for e in entries],
        "latest_score": latest.score if latest else None,
        "delta": delta,
        "trend": trend,
    }


@router.post("/scores", status_code=201)
@limiter.limit("30/minute")
async def record_manual_score(
    request: Request,
    body: ManualScoreRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record a manual score entry."""
    repo = ScoreHistoryRepository(db)
    entry = await repo.record(
        user_id=auth.identity,
        score=body.score,
        score_band=body.score_band,
        source=ScoreSource.MANUAL,
        org_id=auth.org_id,
        notes=body.notes,
    )
    return _entry_to_dict(entry)
