"""Assessment endpoint routes with auth helpers."""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Security,
)

from .assessment import CreditAssessmentService
from .auth import (
    API_KEY_IDENTITY,
    InvalidTokenError,
    _api_key_header,
    decode_token,
    extract_bearer_token,
)
from .config import settings
from .rate_limit import limiter
from .repository import AssessmentRepository
from .types import CreditAssessmentResult, CreditProfile

router = APIRouter()


async def verify_auth(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Validate JWT Bearer or API key. Always requires credentials.

    Returns the authenticated identity (email from JWT sub, or 'api-key-user').
    """
    bearer = extract_bearer_token(request)
    if bearer is not None:
        try:
            payload = decode_token(
                bearer,
                secret=settings.jwt_secret,
                algorithm=settings.jwt_algorithm,
            )
            return payload["sub"]
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    expected = settings.api_key
    if expected is not None and api_key == expected:
        return API_KEY_IDENTITY

    raise HTTPException(status_code=403, detail="Invalid or missing credentials")


_assessment_service = CreditAssessmentService()


def get_assessment_service() -> CreditAssessmentService:
    """Provide CreditAssessmentService via dependency injection."""
    return _assessment_service


async def _persist_assessment(
    factory, profile: CreditProfile, result: CreditAssessmentResult
) -> None:
    """Persist assessment result to database (runs in background)."""
    async with factory() as session:
        repo = AssessmentRepository(session)
        await repo.save_assessment(
            credit_score=profile.current_score,
            score_band=profile.score_band.value,
            barrier_severity=result.barrier_severity.value,
            readiness_score=result.readiness.score,
            request_payload=profile.model_dump(mode="json"),
            response_payload=result.model_dump(mode="json"),
        )


async def _run_assessment(
    request: Request,
    profile: CreditProfile,
    background_tasks: BackgroundTasks,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Shared assessment logic for versioned and legacy endpoints."""
    result = service.assess(profile)
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is not None:
        background_tasks.add_task(_persist_assessment, factory, profile, result)
    return result


@router.post(
    "/assess",
    response_model=CreditAssessmentResult,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def assess(
    request: Request,
    profile: CreditProfile,
    background_tasks: BackgroundTasks,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Run full credit assessment."""
    return await _run_assessment(request, profile, background_tasks, service)
