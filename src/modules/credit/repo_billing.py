"""Repository class for Stripe subscriptions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import Subscription


class SubscriptionRepository:
    """CRUD operations for subscription records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, email: str, subscription_id: str, status: str, plan: str
    ) -> Subscription:
        result = await self._session.execute(
            select(Subscription).where(Subscription.email == email)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.subscription_id = subscription_id
            existing.status = status
            existing.plan = plan
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        sub = Subscription(
            email=email, subscription_id=subscription_id, status=status, plan=plan
        )
        self._session.add(sub)
        await self._session.commit()
        await self._session.refresh(sub)
        return sub

    async def get_by_email(self, email: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.email == email)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Subscription]:
        result = await self._session.execute(select(Subscription))
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self._session.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
        return result.scalar_one()
