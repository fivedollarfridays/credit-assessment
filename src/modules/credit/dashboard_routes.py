"""Dashboard API endpoints — admin-only analytics and customer management."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .dashboard import (
    get_customer_detail,
    get_customer_list,
    get_system_health,
    get_usage_overview,
    update_customer,
)
from .database import get_db
from .roles import Role, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class CustomerUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


@router.get("/overview", dependencies=[Depends(require_role(Role.ADMIN))])
async def overview(db: AsyncSession = Depends(get_db)) -> dict:
    """Usage overview: total users, assessments, active subscriptions."""
    return await get_usage_overview(db)


@router.get("/customers", dependencies=[Depends(require_role(Role.ADMIN))])
async def customers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all customers with enriched data."""
    return await get_customer_list(db)


@router.get("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
async def customer_detail(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get detailed info for a single customer."""
    detail = await get_customer_detail(email, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return detail


@router.put("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
async def update_customer_endpoint(
    email: str, req: CustomerUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    """Update customer role or active status."""
    result = await update_customer(email, db, role=req.role, is_active=req.is_active)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@router.delete("/customers/{email}", dependencies=[Depends(require_role(Role.ADMIN))])
async def deactivate_customer(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Deactivate a customer (soft delete)."""
    result = await update_customer(email, db, is_active=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": f"Customer {email} deactivated", **result}


@router.get("/health", dependencies=[Depends(require_role(Role.ADMIN))])
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """System health metrics."""
    return await get_system_health(db)


# --- Static page router (mounted at root, not under /v1) ---

_STATIC_DIR = Path(__file__).parent / "static"
dashboard_page_router = APIRouter(tags=["dashboard"])


# CSP hashes correspond to inline blocks in static/dashboard.html:
#   script-src hash: SHA-256 of <script>...</script> content (lines 83-168)
#   style-src hash:  SHA-256 of <style>...</style> content (lines 7-38)
# If those blocks change, recompute: echo -n '<content>' | openssl dgst -sha256 -binary | base64
_DASHBOARD_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'sha256-MdAXo8Dsf/xlo39xyvC4ljV9IdXnMoEKyz692W6FR9c='; "
    "style-src 'self' 'sha256-MhxhWmSyTtdEXOb/gJ9lIXYvPbK8vA2rtYgdT+z6gDk='; "
    "connect-src 'self'; frame-ancestors 'none'"
)


@dashboard_page_router.get("/dashboard", include_in_schema=False)
def serve_dashboard() -> FileResponse:
    """Serve the admin dashboard UI with security headers."""
    resp = FileResponse(_STATIC_DIR / "dashboard.html", media_type="text/html")
    resp.headers["content-security-policy"] = _DASHBOARD_CSP
    return resp
