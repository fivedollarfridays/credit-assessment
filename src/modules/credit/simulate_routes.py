"""Simulation endpoint routes — what-if score analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .assess_routes import SimpleCreditProfile, verify_auth
from .disclosures import PROJECTION_DISCLAIMER
from .rate_limit import limiter
from .simulation import ScoreSimulator, SimulationAction, SimulationResult
from .types import CreditProfile

router = APIRouter()

_simulator = ScoreSimulator()


class SimulationRequest(BaseModel):
    """Request body for full simulation."""

    profile: CreditProfile
    actions: list[SimulationAction] = Field(min_length=1, max_length=10)


class SimulationResponse(SimulationResult):
    """Simulation result with projection disclaimer."""

    disclaimer: str = PROJECTION_DISCLAIMER


class SimpleSimulationRequest(BaseModel):
    """Request body for simple simulation."""

    profile: SimpleCreditProfile
    actions: list[SimulationAction] = Field(min_length=1, max_length=10)


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def simulate(request: Request, body: SimulationRequest) -> SimulationResponse:
    """Simulate score impact of proposed actions."""
    result = _simulator.simulate(body.profile, body.actions)
    return SimulationResponse.model_validate(result, from_attributes=True)


@router.post(
    "/simulate/simple",
    response_model=SimulationResponse,
    dependencies=[Depends(verify_auth)],
)
@limiter.limit("30/minute")
async def simulate_simple(
    request: Request, body: SimpleSimulationRequest
) -> SimulationResponse:
    """Simulate from simplified profile input."""
    profile = body.profile.to_credit_profile()
    result = _simulator.simulate(profile, body.actions)
    return SimulationResponse.model_validate(result, from_attributes=True)
