"""FCRA disclosures endpoints."""

from fastapi import APIRouter

from .disclosures import get_disclosures

router = APIRouter(tags=["disclosures"])


@router.get("/disclosures")
def disclosures() -> dict:
    """Return FCRA Section 505 disclosures and legal notices."""
    return get_disclosures()
