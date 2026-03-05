"""Repository class for scoped API keys."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import ApiKeyDB


class ApiKeyRepository:
    """CRUD operations for org-scoped API keys."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        key: str,
        org_id: str,
        role: str,
        expires_at: datetime | None = None,
    ) -> ApiKeyDB:
        entry = ApiKeyDB(key=key, org_id=org_id, role=role, expires_at=expires_at)
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def lookup(self, key: str) -> ApiKeyDB | None:
        entry = await self._session.get(ApiKeyDB, key)
        if entry is None:
            return None
        if entry.revoked_at is not None:
            return None
        if entry.expires_at is not None:
            expires = entry.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return None
        return entry

    async def revoke(self, key: str) -> bool:
        result = await self._session.execute(
            update(ApiKeyDB)
            .where(ApiKeyDB.key == key)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._session.commit()
        return result.rowcount > 0

    async def list_by_org(self, org_id: str) -> list[ApiKeyDB]:
        result = await self._session.execute(
            select(ApiKeyDB).where(
                ApiKeyDB.org_id == org_id, ApiKeyDB.revoked_at.is_(None)
            )
        )
        return list(result.scalars().all())

    async def prune_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            delete(ApiKeyDB).where(ApiKeyDB.expires_at < now)
        )
        await self._session.commit()
        return result.rowcount
