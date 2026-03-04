"""FastAPI router for credit assessment endpoint."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from .assessment import CreditAssessmentService
from .auth import InvalidTokenError, decode_token, extract_bearer_token
from .admin_routes import router as admin_router
from .auth_routes import router as auth_router
from .user_routes import router as user_router
from .config import settings
from .database import check_db_health, create_engine, get_session_factory
from .logging_config import configure_logging
from .observability import setup_observability
from .rate_limit import RateLimitHeaderMiddleware, limiter, register_rate_limit_handler
from .middleware import (
    DeprecationMiddleware,
    HstsMiddleware,
    HttpsRedirectMiddleware,
    RequestIdMiddleware,
)
from .models_db import Base
from .repository import AssessmentRepository
from .types import CreditAssessmentResult, CreditProfile

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_prod = settings.is_production


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    configure_logging(json_output=_prod, log_level=settings.log_level)
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.db_session_factory = get_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(
    title="Credit Assessment API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _prod else "/docs",
    redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
)
app.state.limiter = limiter
setup_observability(
    app,
    dsn=settings.sentry_dsn,
    environment=settings.environment,
    traces_sample_rate=settings.sentry_traces_sample_rate,
)
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router)
v1_router.include_router(user_router)
v1_router.include_router(admin_router)

# Legacy unversioned routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
register_rate_limit_handler(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(DeprecationMiddleware)
app.add_middleware(RateLimitHeaderMiddleware)
app.add_middleware(HstsMiddleware, prod_check=lambda: settings.is_production)
app.add_middleware(HttpsRedirectMiddleware, prod_check=lambda: settings.is_production)


# --- Auth helpers ---


async def verify_auth(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> None:
    """Validate JWT Bearer or legacy API key. Skip auth in dev mode."""
    bearer = extract_bearer_token(request)
    if bearer is not None:
        try:
            decode_token(
                bearer,
                secret=settings.jwt_secret,
                algorithm=settings.jwt_algorithm,
            )
            return
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    expected = settings.api_key
    if expected is None:
        return
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


# --- Service deps ---


def get_assessment_service() -> CreditAssessmentService:
    """Provide CreditAssessmentService via dependency injection."""
    return CreditAssessmentService()


# --- Endpoints ---


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


@app.get("/ready")
async def ready(request: Request) -> dict:
    """Readiness probe — checks service dependencies."""
    checks: dict = {"status": "ok"}
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is not None:
        try:
            await check_db_health(factory)
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
            checks["status"] = "degraded"
    return checks


async def _run_assessment(
    request: Request,
    profile: CreditProfile,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Shared assessment logic for versioned and legacy endpoints."""
    result = service.assess(profile)
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is not None:
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
    return result


@v1_router.post(
    "/assess",
    response_model=CreditAssessmentResult,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def v1_assess(
    request: Request,
    profile: CreditProfile,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Run full credit assessment (v1)."""
    return await _run_assessment(request, profile, service)


@app.post(
    "/assess",
    response_model=CreditAssessmentResult,
    dependencies=[Depends(verify_auth)],
    deprecated=True,
)
@limiter.limit("30/minute")
async def assess(
    request: Request,
    profile: CreditProfile,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Run full credit assessment. Deprecated: use /v1/assess instead."""
    return await _run_assessment(request, profile, service)


# Include v1 router after all v1 routes are defined
app.include_router(v1_router)
