"""Repository classes for users and reset tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import ResetToken, User


class UserRepository:
    """CRUD operations for user accounts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, email: str, password_hash: str, role: str, org_id: str
    ) -> User:
        user = User(email=email, password_hash=password_hash, role=role, org_id=org_id)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(User))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def set_role(self, email: str, role: str) -> bool:
        result = await self._session.execute(
            update(User).where(User.email == email).values(role=role)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def set_password_hash(self, email: str, password_hash: str) -> bool:
        result = await self._session.execute(
            update(User).where(User.email == email).values(password_hash=password_hash)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def delete_by_email(self, email: str) -> bool:
        result = await self._session.execute(delete(User).where(User.email == email))
        await self._session.commit()
        return result.rowcount > 0


class ResetTokenRepository:
    """CRUD operations for password reset tokens with TTL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(self, token: str, email: str, ttl_minutes: int = 30) -> None:
        if ttl_minutes <= 0:
            return
        entry = ResetToken(token=token, email=email)
        self._session.add(entry)
        await self._session.commit()

    async def pop(self, token: str, ttl_minutes: int = 30) -> str | None:
        result = await self._session.execute(
            select(ResetToken).where(ResetToken.token == token)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)
        created = entry.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            await self._session.execute(
                delete(ResetToken).where(ResetToken.token == token)
            )
            await self._session.commit()
            return None
        email = entry.email
        await self._session.execute(delete(ResetToken).where(ResetToken.token == token))
        await self._session.commit()
        return email

    async def delete_by_email(self, email: str) -> int:
        """Delete all reset tokens for a given email (invalidation after use)."""
        result = await self._session.execute(
            delete(ResetToken).where(ResetToken.email == email)
        )
        await self._session.commit()
        return result.rowcount

    async def prune_expired(self, ttl_minutes: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)
        result = await self._session.execute(
            delete(ResetToken).where(ResetToken.created_at < cutoff)
        )
        await self._session.commit()
        return result.rowcount
