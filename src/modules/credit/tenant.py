"""Tenant isolation: org-scoped data access and resolution."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from .repo_assessments import AssessmentRepository
from .roles import is_admin


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
    if override_org is not None and is_admin(user_data):
        return override_org
    return user_org


class ScopedAssessmentRepository:
    """Assessment repository scoped to a single org_id."""

    def __init__(self, session, org_id: str | None) -> None:
        if org_id is None:
            raise ValueError("org_id is required for tenant-scoped queries")
        self._session = session
        self.org_id = org_id


async def get_org_assessments(session: AsyncSession, org_id: str) -> list:
    """Get assessments for a specific organization."""
    repo = AssessmentRepository(session)
    return await repo.get_by_org_id(org_id)


async def count_all_assessments(session: AsyncSession) -> int:
    """Count all assessments across all orgs."""
    repo = AssessmentRepository(session)
    return await repo.count_all()


async def count_org_assessments(session: AsyncSession, org_id: str) -> int:
    """Count assessments for a specific org."""
    repo = AssessmentRepository(session)
    return await repo.count_by_org_id(org_id)
