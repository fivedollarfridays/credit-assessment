"""Tests for async database engine and session factory — T3.3 TDD."""

import asyncio

from sqlalchemy import text


class TestDatabaseEngine:
    """Test async engine creation."""

    def test_create_engine_returns_async_engine(self):
        from sqlalchemy.ext.asyncio import AsyncEngine

        from modules.credit.database import create_engine

        engine = create_engine("sqlite+aiosqlite://")
        assert isinstance(engine, AsyncEngine)

    def test_create_engine_accepts_kwargs(self):
        from sqlalchemy.ext.asyncio import AsyncEngine

        from modules.credit.database import create_engine

        engine = create_engine("sqlite+aiosqlite://", echo=True)
        assert isinstance(engine, AsyncEngine)


class TestSessionFactory:
    """Test async session factory."""

    def test_get_session_factory_returns_callable(self):
        from modules.credit.database import create_engine, get_session_factory

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)
        assert callable(factory)

    def test_session_can_execute_query(self):
        from modules.credit.database import create_engine, get_session_factory

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with factory() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar()

        value = asyncio.run(_run())
        assert value == 1
