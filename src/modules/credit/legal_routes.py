"""API endpoints for legal documents (privacy policy, terms of service)."""

from __future__ import annotations

from fastapi import APIRouter

from .legal import get_privacy_policy, get_terms_of_service

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/privacy")
def privacy_policy() -> dict:
    """Return the current privacy policy."""
    return get_privacy_policy()


@router.get("/terms")
def terms_of_service() -> dict:
    """Return the current terms of service."""
    return get_terms_of_service()
