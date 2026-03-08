"""Feature flag admin API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .assess_routes import verify_auth
from .database import get_db
from .rate_limit import limiter
from .feature_flags import (
    FeatureFlag,
    RuleType,
    TargetingRule,
    create_flag,
    delete_flag,
    evaluate_flag,
    get_all_flags,
    update_flag,
)
from .roles import Role, require_role

router = APIRouter(prefix="/flags", tags=["feature-flags"])


class FlagCreateRequest(BaseModel):
    key: str
    description: str = ""
    enabled: bool = False


class TargetingRuleModel(BaseModel):
    type: RuleType
    values: list[str] = []


class FlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    description: str | None = None
    targeting: list[TargetingRuleModel] | None = None


class FlagResponse(BaseModel):
    key: str
    description: str
    enabled: bool
    targeting: list[TargetingRuleModel]


def _to_response(flag: FeatureFlag) -> FlagResponse:
    return FlagResponse(
        key=flag.key,
        description=flag.description,
        enabled=flag.enabled,
        targeting=[
            TargetingRuleModel(type=r.type, values=r.values) for r in flag.targeting
        ],
    )


@router.post(
    "",
    response_model=FlagResponse,
    status_code=201,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
@limiter.limit("30/minute")
async def create(
    request: Request,
    req: FlagCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> FlagResponse:
    """Create a new feature flag."""
    try:
        flag = await create_flag(
            db, req.key, description=req.description, enabled=req.enabled
        )
    except ValueError:
        raise HTTPException(status_code=409, detail="Flag already exists")
    return _to_response(flag)


@router.get(
    "",
    response_model=list[FlagResponse],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
@limiter.limit("60/minute")
async def list_flags(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[FlagResponse]:
    """List all feature flags."""
    return [_to_response(f) for f in await get_all_flags(db)]


@router.put(
    "/{key}",
    response_model=FlagResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
@limiter.limit("30/minute")
async def update(
    request: Request,
    key: str,
    req: FlagUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> FlagResponse:
    """Update a feature flag."""
    targeting = (
        [TargetingRule(type=r.type, values=r.values) for r in req.targeting]
        if req.targeting
        else None
    )
    flag = await update_flag(
        db, key, enabled=req.enabled, description=req.description, targeting=targeting
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    return _to_response(flag)


@router.delete("/{key}", dependencies=[Depends(require_role(Role.ADMIN))])
@limiter.limit("30/minute")
async def remove(
    request: Request,
    key: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a feature flag."""
    if not await delete_flag(db, key):
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"message": f"Flag '{key}' deleted"}


@router.get("/{key}/evaluate", dependencies=[Depends(verify_auth)])
@limiter.limit("60/minute")
async def evaluate(
    request: Request,
    key: str,
    org_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Evaluate a flag for the given context."""
    return {
        "key": key,
        "enabled": await evaluate_flag(db, key, org_id=org_id, user_id=user_id),
    }
