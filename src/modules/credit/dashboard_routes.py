"""Dashboard API endpoints — admin-only analytics and customer management."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .dashboard import (
    get_customer_detail,
    get_customer_list,
    get_system_health,
    get_usage_overview,
    update_customer,
)
from .roles import Role, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class CustomerUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


@router.get("/overview", dependencies=[Depends(require_role(Role.ADMIN))])
def overview() -> dict:
    """Usage overview: total users, assessments, active subscriptions."""
    return get_usage_overview()


@router.get("/customers", dependencies=[Depends(require_role(Role.ADMIN))])
def customers() -> list[dict]:
    """List all customers with enriched data."""
    return get_customer_list()


@router.get("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
def customer_detail(email: str) -> dict:
    """Get detailed info for a single customer."""
    detail = get_customer_detail(email)
    if detail is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return detail


@router.put("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
def update_customer_endpoint(email: str, req: CustomerUpdate) -> dict:
    """Update customer role or active status."""
    result = update_customer(email, role=req.role, is_active=req.is_active)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@router.delete("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
def deactivate_customer(email: str) -> dict:
    """Deactivate a customer (soft delete)."""
    result = update_customer(email, is_active=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": f"Customer {email} deactivated", **result}


@router.get("/health", dependencies=[Depends(require_role(Role.ADMIN))])
def health() -> dict:
    """System health metrics."""
    return get_system_health()


# --- Static page router (mounted at root, not under /v1) ---

_STATIC_DIR = Path(__file__).parent / "static"
dashboard_page_router = APIRouter(tags=["dashboard"])


@dashboard_page_router.get("/dashboard", include_in_schema=False)
def serve_dashboard() -> FileResponse:
    """Serve the admin dashboard UI."""
    return FileResponse(_STATIC_DIR / "dashboard.html", media_type="text/html")
