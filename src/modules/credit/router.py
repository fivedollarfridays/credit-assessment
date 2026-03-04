"""FastAPI router for credit assessment endpoint."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from .assessment import CreditAssessmentService
from .config import get_api_key, get_cors_origins, is_production
from .types import CreditAssessmentResult, CreditProfile

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Credit Assessment API",
    version="0.1.0",
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
    openapi_url=None if is_production() else "/openapi.json",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 on rate limit exceeded."""
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> None:
    """Validate API key if configured. Skip auth in dev mode."""
    expected = get_api_key()
    if expected is None:
        return
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


def get_assessment_service() -> CreditAssessmentService:
    """Provide CreditAssessmentService via dependency injection."""
    return CreditAssessmentService()


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


@app.post(
    "/assess",
    response_model=CreditAssessmentResult,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("30/minute")
def assess(
    request: Request,
    profile: CreditProfile,
    service: CreditAssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResult:
    """Run full credit assessment."""
    return service.assess(profile)
