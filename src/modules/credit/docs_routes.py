"""API endpoints for documentation and integration guides."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .api_docs import get_code_examples, get_integration_guide
from .roles import Role, require_role

router = APIRouter(prefix="/docs", tags=["docs"])

# Pre-compute the combined guide response (static data).
_GUIDE_RESPONSE: dict = {
    **get_integration_guide(),
    "code_examples": get_code_examples(),
}


@router.get("/guide")
def guide() -> dict:
    """Return the integration guide with auth, endpoints, and error handling."""
    return _GUIDE_RESPONSE


@router.get("/examples")
def examples() -> dict:
    """Return code examples in Python, JavaScript, and curl."""
    return get_code_examples()


@router.get(
    "/openapi.json",
    dependencies=[Depends(require_role(Role.ADMIN))],
    include_in_schema=False,
)
def openapi_spec(request: Request) -> dict:
    """Return OpenAPI spec (accessible in production behind admin auth)."""
    return request.app.openapi()
