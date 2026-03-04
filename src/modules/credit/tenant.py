"""Tenant isolation: org-scoped data access and resolution."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Organization:
    """Organization entity."""

    org_id: str
    name: str


def resolve_org_id(user_data: dict, override_org: str | None = None) -> str | None:
    """Resolve the org_id from user context.

    Admins may override to query a different org's data.
    Non-admins always get their own org_id.
    """
    user_org = user_data.get("org_id")
    if override_org is not None and user_data.get("role") == "admin":
        return override_org
    return user_org


class ScopedAssessmentRepository:
    """Assessment repository scoped to a single org_id."""

    def __init__(self, session, org_id: str | None) -> None:
        if org_id is None:
            raise ValueError("org_id is required for tenant-scoped queries")
        self._session = session
        self.org_id = org_id


# In-memory org-scoped assessment store — replaced by DB in production.
_org_assessments: dict[str, list[dict]] = defaultdict(list)


def store_org_assessment(org_id: str, assessment: dict) -> None:
    """Store an assessment scoped to an organization."""
    _org_assessments[org_id].append(assessment)


def get_org_assessments(org_id: str) -> list[dict]:
    """Get assessments for a specific organization."""
    return list(_org_assessments.get(org_id, []))


def get_all_assessments() -> list[dict]:
    """Get all assessments across all orgs. Admin only."""
    result = []
    for assessments in _org_assessments.values():
        result.extend(assessments)
    return result
