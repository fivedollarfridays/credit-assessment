"""Liberation endpoint routes -- Baby INERTIA credit agents."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from .assess_routes import verify_auth
from .agents import create_wired_moses
from .agents.phantom import PhantomAgent
from .agents.tubman import TubmanAgent
from .agents.export import render_liberation_plan
from .rate_limit import limiter
from .types import CreditProfile

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


_MAX_BUREAU_KEYS = 5
_MAX_CONTEXT_KEYS = 20


def _check_bureau_keys(v: dict) -> dict:
    """Shared validator: reject bureau_reports with too many keys."""
    if len(v) > _MAX_BUREAU_KEYS:
        raise ValueError(f"bureau_reports may have at most {_MAX_BUREAU_KEYS} keys")
    return v


class LiberateRequest(BaseModel):
    """Request body for the full liberation plan endpoint."""

    profile: CreditProfile
    target_industries: list[Annotated[str, Field(max_length=100)]] = Field(
        default=[], max_length=20
    )
    target_goals: list[Annotated[str, Field(max_length=100)]] = Field(
        default=[], max_length=20
    )
    denial_context: dict | None = None
    bureau_reports: dict | None = None

    @field_validator("bureau_reports")
    @classmethod
    def _cap_bureau_reports(cls, v: dict | None) -> dict | None:
        if v is not None:
            _check_bureau_keys(v)
        return v

    @field_validator("denial_context")
    @classmethod
    def _cap_denial_context(cls, v: dict | None) -> dict | None:
        if v is not None and len(v) > _MAX_CONTEXT_KEYS:
            raise ValueError(
                f"denial_context may have at most {_MAX_CONTEXT_KEYS} keys"
            )
        return v


class LiberateResponse(BaseModel):
    """Response from the full liberation plan endpoint."""

    liberation_plan: dict
    reasoning_chain: list[str] = []
    validation_summary: dict = {}
    performance: dict = {}


class PhantomTaxRequest(BaseModel):
    """Request body for the poverty tax receipt endpoint."""

    profile: CreditProfile


class CompareBureausRequest(BaseModel):
    """Request body for the cross-bureau scan endpoint."""

    profile: CreditProfile
    bureau_reports: dict

    @field_validator("bureau_reports")
    @classmethod
    def _cap_bureau_reports(cls, v: dict) -> dict:
        return _check_bureau_keys(v)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_moses_context(body: LiberateRequest) -> dict | None:
    """Build context dict from optional LiberateRequest fields."""
    context: dict = {}
    if body.target_industries:
        context["target_industries"] = body.target_industries
    if body.denial_context:
        context["denial_context"] = body.denial_context
    if body.bureau_reports:
        context["bureau_reports"] = body.bureau_reports
    return context or None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/liberate",
    response_model=LiberateResponse,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def liberate(request: Request, body: LiberateRequest) -> LiberateResponse:
    """Run full Liberation Plan with all Baby INERTIA agents."""
    moses = create_wired_moses()
    context = _build_moses_context(body)
    result = await asyncio.to_thread(moses.execute, body.profile, context)
    return LiberateResponse(
        liberation_plan=result.data.get("liberation_plan", {}),
        reasoning_chain=result.data.get("reasoning_chain", []),
        validation_summary=result.data.get("validation_summary", {}),
        performance=result.data.get("performance", {}),
    )


@router.post("/phantom-tax", dependencies=[Depends(verify_auth)])
@limiter.limit("60/minute")
async def phantom_tax(request: Request, body: PhantomTaxRequest) -> dict:
    """Calculate poverty tax receipt using Phantom agent."""
    phantom = PhantomAgent()
    result = await asyncio.to_thread(phantom.execute, body.profile)
    return result.data


@router.post("/compare-bureaus", dependencies=[Depends(verify_auth)])
@limiter.limit("60/minute")
async def compare_bureaus(request: Request, body: CompareBureausRequest) -> dict:
    """Cross-bureau discrepancy scan using Tubman agent."""
    tubman = TubmanAgent()
    result = await asyncio.to_thread(
        tubman.execute, body.profile, {"bureau_reports": body.bureau_reports}
    )
    return result.data


@router.post(
    "/liberate/print",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def liberate_print(request: Request, body: LiberateRequest) -> HTMLResponse:
    """Render a printable HTML Liberation Plan."""
    moses = create_wired_moses()
    context = _build_moses_context(body)
    result = await asyncio.to_thread(moses.execute, body.profile, context)
    html = render_liberation_plan(result.data)
    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
            "X-Frame-Options": "DENY",
        },
    )
