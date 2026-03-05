"""Repository class for feature flags."""

from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import FeatureFlagDB


class FeatureFlagRepository:
    """CRUD operations for feature flags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        key: str,
        description: str = "",
        enabled: bool = False,
        targeting: list | None = None,
    ) -> FeatureFlagDB:
        flag = FeatureFlagDB(
            key=key, description=description, enabled=enabled, targeting=targeting
        )
        self._session.add(flag)
        await self._session.commit()
        await self._session.refresh(flag)
        return flag

    async def get(self, key: str) -> FeatureFlagDB | None:
        return await self._session.get(FeatureFlagDB, key)

    async def list_all(self) -> list[FeatureFlagDB]:
        result = await self._session.execute(select(FeatureFlagDB))
        return list(result.scalars().all())

    async def update(self, key: str, **fields) -> bool:
        result = await self._session.execute(
            update(FeatureFlagDB).where(FeatureFlagDB.key == key).values(**fields)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def delete(self, key: str) -> bool:
        result = await self._session.execute(
            delete(FeatureFlagDB).where(FeatureFlagDB.key == key)
        )
        await self._session.commit()
        return result.rowcount > 0
