"""FastAPI router for credit assessment endpoint."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .admin_routes import router as admin_router
from .api_docs import API_DESCRIPTION, API_TAGS
from .assess_routes import router as assess_router
from .auth_routes import router as auth_router
from .data_rights_routes import router as data_rights_router
from .disclosures import get_disclosures
from .docs_routes import router as docs_router
from .legal_routes import router as legal_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    configure_logging(json_output=settings.is_production, log_level=settings.log_level)
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.db_session_factory = get_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(
    title="Credit Assessment API",
    version="1.0.0",
    description=API_DESCRIPTION,
    openapi_tags=API_TAGS,
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
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
v1_router.include_router(legal_router)
v1_router.include_router(data_rights_router)
v1_router.include_router(docs_router)
v1_router.include_router(assess_router)

# Legacy unversioned routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(legal_router)
app.include_router(data_rights_router)
app.include_router(docs_router)
app.include_router(assess_router, deprecated=True)
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


@app.get("/disclosures")
def disclosures() -> dict:
    """Return FCRA Section 505 disclosures and legal notices."""
    return get_disclosures()


@v1_router.get("/disclosures")
def v1_disclosures() -> dict:
    """Return FCRA Section 505 disclosures and legal notices (v1)."""
    return get_disclosures()


# Include v1 router after all v1 routes are defined
app.include_router(v1_router)
