"""FastAPI router for credit assessment endpoint."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .admin_routes import router as admin_router
from .dashboard_routes import dashboard_page_router, router as dashboard_router
from .assess_routes import router as assess_router
from .auth_routes import router as auth_router
from .data_rights_routes import router as data_rights_router
from .disclosures_routes import router as disclosures_router
from .docs_routes import router as docs_router
from .flag_routes import router as flag_router
from .legal_routes import router as legal_router
from .letter_routes import router as letter_router
from .simulate_routes import router as simulate_router
from .user_routes import router as user_router
from .webhook_routes import router as webhook_router
from .config import settings
from . import api_docs, database, logging_config, middleware, rate_limit
from .observability import setup_observability
from .models_db import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logging_config.configure_logging(
        json_output=settings.is_production, log_level=settings.log_level
    )
    engine = database.create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.db_session_factory = database.get_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(
    title="Credit Assessment API",
    version="1.0.0",
    description=api_docs.API_DESCRIPTION,
    openapi_tags=api_docs.API_TAGS,
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.state.limiter = rate_limit.limiter
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
v1_router.include_router(webhook_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(disclosures_router)
v1_router.include_router(flag_router)
v1_router.include_router(letter_router)  # v1-only: new features skip legacy paths
v1_router.include_router(simulate_router)  # v1-only: new features skip legacy paths

# Legacy unversioned routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(legal_router)
app.include_router(data_rights_router)
app.include_router(docs_router)
app.include_router(disclosures_router)
app.include_router(assess_router, deprecated=True)
rate_limit.register_rate_limit_handler(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)
app.add_middleware(middleware.RequestIdMiddleware)
app.add_middleware(middleware.DeprecationMiddleware)
app.add_middleware(rate_limit.RateLimitHeaderMiddleware)
app.add_middleware(middleware.HstsMiddleware, prod_check=lambda: settings.is_production)
app.add_middleware(
    middleware.HttpsRedirectMiddleware, prod_check=lambda: settings.is_production
)


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
            await database.check_db_health(factory)
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
            checks["status"] = "degraded"
    if settings.redis_url is not None:
        if await rate_limit.check_redis_health(settings.redis_url):
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
            checks["status"] = "degraded"
    return checks


# Include v1 router after all v1 routes are defined
app.include_router(v1_router)
app.include_router(dashboard_page_router)
