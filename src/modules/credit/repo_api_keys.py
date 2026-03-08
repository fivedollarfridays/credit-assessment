"""Repository class for scoped API keys."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import ApiKeyDB


def _hash_key(key: str) -> str:
    """Return the SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(key.encode()).hexdigest()


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
        entry = ApiKeyDB(
            key_hash=_hash_key(key),
            key_prefix=key[:8],
            org_id=org_id,
            role=role,
            expires_at=expires_at,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def lookup(self, key: str) -> ApiKeyDB | None:
        hashed = _hash_key(key)
        entry = await self._session.get(ApiKeyDB, hashed)
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
        hashed = _hash_key(key)
        result = await self._session.execute(
            update(ApiKeyDB)
            .where(ApiKeyDB.key_hash == hashed)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._session.commit()
        return result.rowcount > 0

    async def revoke_by_prefix(self, prefix: str) -> bool:
        """Revoke an API key by its 8-char prefix (avoids raw key in URLs).

        Note: prefix collisions are theoretically possible but extremely
        unlikely (~1 in 10^7 for 10k keys).  If multiple keys share a
        prefix, all matching active keys are revoked.
        """
        result = await self._session.execute(
            update(ApiKeyDB)
            .where(ApiKeyDB.key_prefix == prefix, ApiKeyDB.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        if result.rowcount > 1:
            logging.getLogger(__name__).warning(
                "revoke_by_prefix matched %d keys for prefix %s",
                result.rowcount,
                prefix,
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
