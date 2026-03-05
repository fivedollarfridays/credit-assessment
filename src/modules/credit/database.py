"""Async database engine and session factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.requests import Request

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


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


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    factory = request.app.state.db_session_factory
    async with factory() as session:
        yield session
