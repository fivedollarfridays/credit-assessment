"""API endpoints for documentation and integration guides."""

from __future__ import annotations

from fastapi import APIRouter

from .api_docs import get_code_examples, get_integration_guide

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
