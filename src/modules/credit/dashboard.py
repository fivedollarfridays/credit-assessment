"""Dashboard module — usage analytics, customer management, system health."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .audit import count_audit_entries
from .billing import count_active_subscriptions, get_subscription
from .repo_users import UserRepository
from .roles import Role
from .tenant import count_all_assessments, count_org_assessments
from .webhooks import count_webhooks


def _build_customer_info(
    email: str,
    user_role: str,
    is_active: bool,
    org_id: str,
    sub: dict | None,
    assessment_count: int,
) -> dict:
    """Build a customer info dict from user, subscription, and assessment data."""
    return {
        "email": email,
        "role": user_role,
        "is_active": is_active,
        "org_id": org_id,
        "plan": sub["plan"] if sub else None,
        "assessment_count": assessment_count,
    }


async def get_usage_overview(session: AsyncSession) -> dict:
    """Aggregate usage statistics across all stores."""
    repo = UserRepository(session)
    return {
        "total_users": await repo.count(),
        "total_assessments": count_all_assessments(),
        "active_subscriptions": count_active_subscriptions(),
    }


async def get_customer_list(session: AsyncSession) -> list[dict]:
    """Return enriched customer list with subscription and assessment data."""
    repo = UserRepository(session)
    users = await repo.list_all()
    customers: list[dict] = []
    for user in users:
        sub = get_subscription(user.email)
        customers.append(
            _build_customer_info(
                user.email,
                user.role or Role.VIEWER.value,
                user.is_active,
                user.org_id or "",
                sub,
                count_org_assessments(user.org_id or ""),
            )
        )
    return customers


async def get_customer_detail(email: str, session: AsyncSession) -> dict | None:
    """Return detailed info for a single customer."""
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        return None
    sub = get_subscription(email)
    org_id = user.org_id or ""
    info = _build_customer_info(
        email,
        user.role or Role.VIEWER.value,
        user.is_active,
        org_id,
        sub,
        count_org_assessments(org_id),
    )
    info["subscription_status"] = sub["status"] if sub else None
    return info


async def update_customer(
    email: str,
    session: AsyncSession,
    *,
    role: Role | None = None,
    is_active: bool | None = None,
) -> dict | None:
    """Update customer fields (admin-only). Returns updated customer or None."""
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        return None
    if role is not None:
        user.role = role.value
    if is_active is not None:
        user.is_active = is_active
    await session.commit()
    return {"email": email, "role": user.role, "is_active": user.is_active}


async def get_system_health(session: AsyncSession) -> dict:
    """Return system health summary."""
    repo = UserRepository(session)
    return {
        "status": "ok",
        "users": await repo.count(),
        "audit_entries": await count_audit_entries(session),
        "webhooks": count_webhooks(),
    }
