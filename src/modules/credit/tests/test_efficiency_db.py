"""Tests for dashboard count-function usage and API key DB persistence."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.repo_api_keys import ApiKeyRepository


def _make_db():
    """Create in-memory database for tests."""
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


class TestApiKeyDbPersistence:
    """API keys are DB-backed via ApiKeyRepository."""

    def test_create_key_persists_and_lookup_returns_it(self) -> None:
        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="test-key-1", org_id="org-1", role="viewer")
                found = await repo.lookup("test-key-1")
                return found

        result = asyncio.run(_run())
        assert result is not None
        assert result.key_prefix == "test-key"
        assert result.org_id == "org-1"
        assert result.role == "viewer"

    def test_revoked_key_lookup_returns_none(self) -> None:
        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="revoke-me", org_id="org-2", role="admin")
                await repo.revoke("revoke-me")
                found = await repo.lookup("revoke-me")
                return found

        result = asyncio.run(_run())
        assert result is None


class TestDashboardUsesCountFunctions:
    """Dashboard must use count functions, not len(get_*())."""

    def test_overview_uses_count_all_assessments(self) -> None:
        from modules.credit.dashboard import get_usage_overview

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                with patch(
                    "modules.credit.dashboard.count_all_assessments",
                    new=AsyncMock(return_value=42),
                ):
                    result = await get_usage_overview(session)
            return result

        result = asyncio.run(_run())
        assert result["total_assessments"] == 42

    def test_customer_list_uses_count_org_assessments(self) -> None:
        from modules.credit.dashboard import get_customer_list
        from modules.credit.password import hash_password
        from modules.credit.repo_users import UserRepository

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                repo = UserRepository(session)
                await repo.create(
                    email="a@b.com",
                    password_hash=hash_password("pw"),
                    role="viewer",
                    org_id="org-a",
                )
                with patch(
                    "modules.credit.dashboard.count_org_assessments",
                    new=AsyncMock(return_value=7),
                ):
                    customers = await get_customer_list(session)
            return customers

        customers = asyncio.run(_run())
        assert customers[0]["assessment_count"] == 7

    def test_system_health_uses_count_audit_entries(self) -> None:
        from modules.credit.dashboard import get_system_health

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                with (
                    patch(
                        "modules.credit.dashboard.count_audit_entries",
                        new=AsyncMock(return_value=99),
                    ),
                    patch(
                        "modules.credit.dashboard.count_webhooks",
                        new=AsyncMock(return_value=5),
                    ),
                ):
                    health = await get_system_health(session)
            return health

        health = asyncio.run(_run())
        assert health["audit_entries"] == 99
        assert health["webhooks"] == 5
