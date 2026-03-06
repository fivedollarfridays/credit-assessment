"""Dispute lifecycle endpoint routes — create, list, update, deadlines."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .assess_routes import verify_auth
from .auth import AuthIdentity
from .database import get_db
from .dispute_models import DisputeStatus
from .letter_types import Bureau
from .rate_limit import limiter
from .models_db import DisputeRecord
from .repo_disputes import DisputeRepository

router = APIRouter()


class CreateDisputeRequest(BaseModel):
    """Request body for creating a dispute."""

    bureau: Bureau
    negative_item_data: dict
    letter_type: str | None = None


class StatusUpdateRequest(BaseModel):
    """Request body for updating dispute status."""

    status: DisputeStatus
    resolution: str | None = Field(default=None, max_length=500)


def _dispute_to_dict(record: DisputeRecord) -> dict:
    """Convert a DisputeRecord to a JSON-serializable dict."""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "org_id": record.org_id,
        "bureau": record.bureau,
        "negative_item_data": record.negative_item_data,
        "letter_type": record.letter_type,
        "status": record.status,
        "round": record.round,
        "sent_at": record.sent_at.isoformat() if record.sent_at else None,
        "deadline_at": record.deadline_at.isoformat() if record.deadline_at else None,
        "responded_at": (
            record.responded_at.isoformat() if record.responded_at else None
        ),
        "resolution": record.resolution,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@router.post("/disputes", status_code=201)
@limiter.limit("30/minute")
async def create_dispute(
    request: Request,
    body: CreateDisputeRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new dispute in DRAFT status."""
    repo = DisputeRepository(db)
    record = await repo.create(
        user_id=auth.identity,
        bureau=body.bureau,
        negative_item_data=body.negative_item_data,
        org_id=auth.org_id,
        letter_type=body.letter_type,
    )
    return _dispute_to_dict(record)


@router.get("/disputes/deadlines")
@limiter.limit("60/minute")
async def list_deadlines(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    days_ahead: int = Query(default=7, ge=1, le=90),
) -> dict:
    """List the authenticated user's disputes with approaching FCRA deadlines."""
    repo = DisputeRepository(db)
    records = await repo.get_approaching_deadlines(
        user_id=auth.identity, days_ahead=days_ahead
    )
    return {"items": [_dispute_to_dict(r) for r in records]}


@router.get("/disputes")
@limiter.limit("60/minute")
async def list_disputes(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    status: DisputeStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """List disputes for the authenticated user."""
    repo = DisputeRepository(db)
    user_id = auth.identity
    records = await repo.list_by_user(
        user_id, status_filter=status, limit=limit, offset=offset
    )
    total = await repo.count_by_user(user_id, status_filter=status)
    return {
        "items": [_dispute_to_dict(r) for r in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/disputes/{dispute_id}")
@limiter.limit("60/minute")
async def get_dispute(
    request: Request,
    dispute_id: int,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single dispute by ID."""
    repo = DisputeRepository(db)
    record = await repo.get(dispute_id, user_id=auth.identity)
    if record is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _dispute_to_dict(record)


@router.patch("/disputes/{dispute_id}/status")
@limiter.limit("30/minute")
async def update_dispute_status(
    request: Request,
    dispute_id: int,
    body: StatusUpdateRequest,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update dispute status with transition validation."""
    repo = DisputeRepository(db)
    try:
        record = await repo.update_status(
            dispute_id,
            user_id=auth.identity,
            new_status=body.status,
            resolution=body.resolution,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    return _dispute_to_dict(record)
