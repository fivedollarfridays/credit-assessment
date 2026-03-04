"""Dashboard module — usage analytics, customer management, system health."""

from __future__ import annotations

from .audit import get_audit_trail
from .billing import count_active_subscriptions, get_subscription
from .tenant import get_all_assessments, get_org_assessments
from .roles import Role
from .user_routes import (
    count_users,
    get_all_users,
    get_user,
    set_user_role,
    update_user,
)
from .webhooks import get_webhooks


def _build_customer_info(
    email: str,
    user: dict,
    sub: dict | None,
    assessment_count: int,
) -> dict:
    """Build a customer info dict from user, subscription, and assessment data."""
    return {
        "email": email,
        "role": user.get("role", "viewer"),
        "is_active": user.get("is_active", True),
        "org_id": user.get("org_id", ""),
        "plan": sub["plan"] if sub else None,
        "assessment_count": assessment_count,
    }


def get_usage_overview() -> dict:
    """Aggregate usage statistics across all stores."""
    total_assessments = len(get_all_assessments())
    return {
        "total_users": count_users(),
        "total_assessments": total_assessments,
        "active_subscriptions": count_active_subscriptions(),
    }


def get_customer_list() -> list[dict]:
    """Return enriched customer list with subscription and assessment data."""
    customers: list[dict] = []
    for email, user in get_all_users().items():
        sub = get_subscription(email)
        org_id = user.get("org_id", "")
        assessments = get_org_assessments(org_id)
        customers.append(_build_customer_info(email, user, sub, len(assessments)))
    return customers


def get_customer_detail(email: str) -> dict | None:
    """Return detailed info for a single customer."""
    user = get_user(email)
    if user is None:
        return None
    sub = get_subscription(email)
    org_id = user.get("org_id", "")
    assessments = get_org_assessments(org_id)
    info = _build_customer_info(email, user, sub, len(assessments))
    info["subscription_status"] = sub["status"] if sub else None
    return info


def update_customer(
    email: str,
    *,
    role: Role | None = None,
    is_active: bool | None = None,
) -> dict | None:
    """Update customer fields (admin-only). Returns updated customer or None."""
    user = get_user(email)
    if user is None:
        return None
    # Role is a privileged field — use set_user_role (admin context only).
    if role is not None:
        set_user_role(email, role)
    # is_active goes through the public update_user allowlist.
    if is_active is not None:
        update_user(email, is_active=is_active)
    updated = get_user(email)
    return {"email": email, "role": updated["role"], "is_active": updated["is_active"]}


def get_system_health() -> dict:
    """Return system health summary from in-memory stores."""
    return {
        "status": "ok",
        "users": count_users(),
        "audit_entries": len(get_audit_trail()),
        "webhooks": len(get_webhooks()),
    }
