"""Async database engine and session factory."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(url: str, **kwargs) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(url, **kwargs)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_db_health(factory: async_sessionmaker[AsyncSession]) -> bool:
    """Check database connectivity. Returns True if healthy."""
    async with factory() as session:
        await session.execute(text("SELECT 1"))
    return True
