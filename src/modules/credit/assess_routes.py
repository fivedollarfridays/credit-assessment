"""Assessment endpoint routes with auth helpers."""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Security,
)
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from .assessment import CreditAssessmentService, get_score_band
from .auth import (
    API_KEY_IDENTITY,
    AuthIdentity,
    InvalidTokenError,
    api_key_header,
    decode_token,
    extract_bearer_token,
)
from .assess_tasks import (
    persist_assessment,
    record_score_history,
    record_usage_for_user,
)
from .billing import get_subscription
from .config import settings
from .database import get_db
from .rate_limit import SubscriptionTier, limiter, resolve_tier
from .repo_api_keys import ApiKeyRepository
from .repo_assessments import AssessmentRepository

from .types import (
    AccountSummary,
    CreditAssessmentResult,
    CreditProfile,
    NegativeItemType,
    _infer_item_type,
)

router = APIRouter()


async def _lookup_scoped_key(request: Request, api_key: str) -> AuthIdentity | None:
    """Try to authenticate via a scoped API key from DB. Returns None if not found."""
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        logging.getLogger(__name__).warning(
            "API key provided but db_session_factory unavailable; "
            "scoped key lookup skipped"
        )
        return None
    async with factory() as session:
        repo = ApiKeyRepository(session)
        entry = await repo.lookup(api_key)
        if entry is not None:
            return AuthIdentity(
                identity=f"apikey:{entry.org_id}",
                org_id=entry.org_id,
                role=entry.role,
                is_scoped_key=True,
            )
    return None


async def verify_auth(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AuthIdentity:
    """Validate JWT Bearer or API key. Always requires credentials.

    Returns AuthIdentity with identity string, plus org_id/role for scoped keys.
    """
    bearer = extract_bearer_token(request)
    if bearer is not None:
        try:
            payload = decode_token(
                bearer,
                secret=settings.jwt_secret,
                algorithm=settings.jwt_algorithm,
            )
            return AuthIdentity(
                identity=payload["sub"],
                org_id=payload.get("org_id"),
                role=payload.get("role"),
            )
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    if api_key is not None:
        # Always run both checks to normalize timing (prevents oracle on DB lookup)
        scoped = await _lookup_scoped_key(request, api_key)
        expected = settings.api_key
        static_ok = expected is not None and hmac.compare_digest(api_key, expected)
        if scoped is not None:
            return scoped
        if static_ok:
            return AuthIdentity(identity=API_KEY_IDENTITY)

    raise HTTPException(status_code=403, detail="Invalid or missing credentials")


def _parse_tier(plan: str | None) -> SubscriptionTier:
    """Parse a plan string into a SubscriptionTier, defaulting to FREE."""
    if plan is None:
        return SubscriptionTier.FREE
    try:
        return SubscriptionTier(plan)
    except ValueError:
        return SubscriptionTier.FREE


async def get_tier_limit(db: AsyncSession, identity: str) -> str | None:
    """Resolve rate limit string for user's subscription tier."""
    sub = await get_subscription(db, identity)
    tier = _parse_tier(sub["plan"] if sub else None)
    return resolve_tier(tier)


async def resolve_user_tier(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
) -> SubscriptionTier:
    """Resolve authenticated user's subscription tier from DB."""
    if auth.identity == API_KEY_IDENTITY:
        return SubscriptionTier.FREE
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        return SubscriptionTier.FREE
    try:
        async with factory() as session:
            sub = await get_subscription(session, auth.identity)
    except Exception:
        return SubscriptionTier.FREE
    if sub is None or sub["status"] != "active":
        return SubscriptionTier.FREE
    return _parse_tier(sub["plan"])


_assessment_service = CreditAssessmentService()


def get_assessment_service() -> CreditAssessmentService:
    """Provide CreditAssessmentService via dependency injection."""
    return _assessment_service


async def _run_assessment(
    request: Request,
    profile: CreditProfile,
    background_tasks: BackgroundTasks,
    service: CreditAssessmentService,
    auth: AuthIdentity,
) -> CreditAssessmentResult:
    """Shared assessment logic for versioned and legacy endpoints."""
    result = service.assess(profile)
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is not None:
        background_tasks.add_task(
            persist_assessment,
            factory,
            profile,
            result,
            auth.identity,
            auth.org_id,
        )
        background_tasks.add_task(record_usage_for_user, factory, auth.identity)
        if auth.identity != API_KEY_IDENTITY:
            background_tasks.add_task(
                record_score_history,
                factory,
                profile,
                auth.identity,
                auth.org_id,
            )
    return result


@router.post(
    "/assess",
    response_model=CreditAssessmentResult,
)
@limiter.limit("300/minute")
async def assess(
    request: Request,
    profile: CreditProfile,
    background_tasks: BackgroundTasks,
    service: CreditAssessmentService = Depends(get_assessment_service),
    auth: AuthIdentity = Depends(verify_auth),
) -> CreditAssessmentResult:
    """Run full credit assessment with tier-based rate limiting."""
    return await _run_assessment(request, profile, background_tasks, service, auth)


_OLDEST_TO_AVG_FACTOR = 0.6  # heuristic: average account age ≈ 60% of oldest


class SimpleCreditProfile(BaseModel):
    """Simplified credit profile — user-friendly fields, backend derives the rest."""

    credit_score: int = Field(ge=300, le=850)
    utilization_percent: float = Field(ge=0.0, le=100.0)
    total_accounts: int = Field(ge=0)
    open_accounts: int = Field(ge=0)
    negative_items: list[Annotated[str, Field(max_length=200)]] = Field(
        default=[], max_length=50
    )
    payment_history_percent: float = Field(ge=0.0, le=100.0)
    oldest_account_months: int = Field(ge=0, le=1200)
    total_balance: float = Field(default=0.0, ge=0.0)
    total_credit_limit: float = Field(default=0.0, ge=0.0)
    monthly_payments: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def _check_open_le_total(self) -> SimpleCreditProfile:
        if self.open_accounts > self.total_accounts:
            raise ValueError("open_accounts cannot exceed total_accounts")
        return self

    def to_credit_profile(self) -> CreditProfile:
        """Convert to the full CreditProfile used by the assessment engine."""
        closed = self.total_accounts - self.open_accounts
        collections = sum(
            1
            for item in self.negative_items
            if _infer_item_type(item) == NegativeItemType.COLLECTION
        )
        return CreditProfile(
            current_score=self.credit_score,
            score_band=get_score_band(self.credit_score),
            overall_utilization=self.utilization_percent,
            account_summary=AccountSummary(
                total_accounts=self.total_accounts,
                open_accounts=self.open_accounts,
                closed_accounts=closed,
                negative_accounts=len(self.negative_items),
                collection_accounts=collections,
                total_balance=self.total_balance,
                total_credit_limit=self.total_credit_limit,
                monthly_payments=self.monthly_payments,
            ),
            payment_history_pct=self.payment_history_percent,
            average_account_age_months=int(
                self.oldest_account_months * _OLDEST_TO_AVG_FACTOR
            ),
            negative_items=self.negative_items,
        )


@router.post(
    "/assess/simple",
    response_model=CreditAssessmentResult,
)
@limiter.limit("300/minute")
async def assess_simple(
    request: Request,
    simple: SimpleCreditProfile,
    background_tasks: BackgroundTasks,
    service: CreditAssessmentService = Depends(get_assessment_service),
    auth: AuthIdentity = Depends(verify_auth),
) -> CreditAssessmentResult:
    """Run credit assessment from simplified input."""
    profile = simple.to_credit_profile()
    return await _run_assessment(request, profile, background_tasks, service, auth)


@router.get("/assessments")
@limiter.limit("30/minute")
async def list_assessments(
    request: Request,
    auth: AuthIdentity = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return paginated assessment history for the authenticated user's org."""
    if auth.identity == API_KEY_IDENTITY:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
    repo = AssessmentRepository(db)
    org_id = auth.org_id
    if org_id:
        records = await repo.get_by_org_id(org_id, limit=limit, offset=offset)
        total = await repo.count_by_org_id(org_id)
    else:
        records = await repo.get_by_user_id(auth.identity, limit=limit, offset=offset)
        total = await repo.count_by_user_id(auth.identity)
    items = [
        {
            "id": r.id,
            "credit_score": r.credit_score,
            "score_band": r.score_band,
            "barrier_severity": r.barrier_severity,
            "readiness_score": r.readiness_score,
            "user_id": r.user_id,
            "org_id": r.org_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}
