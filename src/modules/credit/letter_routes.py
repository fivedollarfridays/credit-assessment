"""Letter generation endpoint routes — dispute letter creation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .assess_routes import verify_auth
from .letter_generator import GeneratedLetter, LetterGenerator, LetterRequest
from .rate_limit import limiter

router = APIRouter()

_generator = LetterGenerator()


class BatchLetterRequest(BaseModel):
    """Request body for batch letter generation."""

    requests: list[LetterRequest] = Field(min_length=1, max_length=10)


class BatchLetterResponse(BaseModel):
    """Response for batch letter generation."""

    letters: list[GeneratedLetter]


@router.post(
    "/disputes/letters",
    response_model=GeneratedLetter,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def generate_letter(request: Request, body: LetterRequest) -> GeneratedLetter:
    """Generate a single dispute letter."""
    return _generator.generate(body)


@router.post(
    "/disputes/letters/batch",
    response_model=BatchLetterResponse,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("10/minute")
async def generate_letters_batch(
    request: Request, body: BatchLetterRequest
) -> BatchLetterResponse:
    """Generate multiple dispute letters (max 10)."""
    letters = _generator.generate_batch(body.requests)
    return BatchLetterResponse(letters=letters)
