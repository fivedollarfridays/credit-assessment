"""Repository classes for webhooks and delivery logs."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import WebhookDeliveryDB, WebhookRegistrationDB


class WebhookRepository:
    """CRUD operations for webhook registrations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        id: str,
        url: str,
        events: list,
        secret: str,
        owner_id: str | None = None,
    ) -> WebhookRegistrationDB:
        wh = WebhookRegistrationDB(
            id=id, url=url, events=events, secret=secret, owner_id=owner_id
        )
        self._session.add(wh)
        await self._session.commit()
        await self._session.refresh(wh)
        return wh

    async def get(self, webhook_id: str) -> WebhookRegistrationDB | None:
        return await self._session.get(WebhookRegistrationDB, webhook_id)

    async def list_all(self) -> list[WebhookRegistrationDB]:
        result = await self._session.execute(select(WebhookRegistrationDB))
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: str) -> list[WebhookRegistrationDB]:
        result = await self._session.execute(
            select(WebhookRegistrationDB).where(
                WebhookRegistrationDB.owner_id == owner_id
            )
        )
        return list(result.scalars().all())

    async def get_subscribed(self, event_type: str) -> list[WebhookRegistrationDB]:
        result = await self._session.execute(
            select(WebhookRegistrationDB).where(
                WebhookRegistrationDB.is_active.is_(True)
            )
        )
        all_active = result.scalars().all()
        return [wh for wh in all_active if event_type in wh.events]

    async def delete(self, webhook_id: str) -> bool:
        result = await self._session.execute(
            delete(WebhookRegistrationDB).where(WebhookRegistrationDB.id == webhook_id)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count(WebhookRegistrationDB.id))
        )
        return result.scalar_one()


class WebhookDeliveryRepository:
    """CRUD operations for webhook delivery logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_delivery(
        self,
        *,
        webhook_id: str,
        event_type: str,
        status: str,
        status_code: int | None = None,
    ) -> WebhookDeliveryDB:
        entry = WebhookDeliveryDB(
            webhook_id=webhook_id,
            event_type=event_type,
            status=status,
            status_code=status_code,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def get_by_webhook(
        self, webhook_id: str, *, limit: int = 100
    ) -> list[WebhookDeliveryDB]:
        result = await self._session.execute(
            select(WebhookDeliveryDB)
            .where(WebhookDeliveryDB.webhook_id == webhook_id)
            .order_by(WebhookDeliveryDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
