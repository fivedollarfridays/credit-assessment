"""Liberation endpoint routes -- Baby INERTIA credit agents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .assess_routes import verify_auth
from .agents.moses import MosesAgent
from .agents.phantom import PhantomAgent
from .agents.tubman import TubmanAgent
from .agents.export import render_liberation_plan
from .types import CreditProfile

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LiberateRequest(BaseModel):
    """Request body for the full liberation plan endpoint."""

    profile: CreditProfile
    target_industries: list[str] = []
    target_goals: list[str] = []
    denial_context: dict | None = None
    bureau_reports: dict | None = None


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
async def liberate(request: Request, body: LiberateRequest) -> LiberateResponse:
    """Run full Liberation Plan with all Baby INERTIA agents."""
    moses = MosesAgent()
    context = _build_moses_context(body)
    result = moses.execute(body.profile, context)
    return LiberateResponse(
        liberation_plan=result.data.get("liberation_plan", {}),
        reasoning_chain=result.data.get("reasoning_chain", []),
        validation_summary=result.data.get("validation_summary", {}),
        performance=result.data.get("performance", {}),
    )


@router.post("/phantom-tax", dependencies=[Depends(verify_auth)])
async def phantom_tax(request: Request, body: PhantomTaxRequest) -> dict:
    """Calculate poverty tax receipt using Phantom agent."""
    phantom = PhantomAgent()
    result = phantom.execute(body.profile)
    return result.data


@router.post("/compare-bureaus", dependencies=[Depends(verify_auth)])
async def compare_bureaus(
    request: Request, body: CompareBureausRequest
) -> dict:
    """Cross-bureau discrepancy scan using Tubman agent."""
    tubman = TubmanAgent()
    result = tubman.execute(body.profile, {"bureau_reports": body.bureau_reports})
    return result.data


@router.post(
    "/liberate/print",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_auth)],
)
async def liberate_print(
    request: Request, body: LiberateRequest
) -> HTMLResponse:
    """Render a printable HTML Liberation Plan."""
    moses = MosesAgent()
    context = _build_moses_context(body)
    result = moses.execute(body.profile, context)
    html = render_liberation_plan(result.data)
    return HTMLResponse(content=html)
