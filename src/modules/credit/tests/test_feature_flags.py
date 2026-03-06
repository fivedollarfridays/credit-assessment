"""Tests for feature flags — evaluation, targeting, admin management."""

from __future__ import annotations

import asyncio

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.feature_flags import (
    FeatureFlag,
    RuleType,
    TargetingRule,
    _matches_rule,
    create_flag,
    delete_flag,
    evaluate_flag,
    get_all_flags,
    get_flag,
    update_flag,
)
from modules.credit.models_db import Base


@pytest.fixture
def db_factory():
    """Create in-memory database with tables for each test."""
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


# --- Flag CRUD ---


class TestFlagCRUD:
    def test_create_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                flag = await create_flag(
                    session, key="new-scoring", description="New scoring algo", enabled=False
                )
                assert isinstance(flag, FeatureFlag)
                assert flag.key == "new-scoring"
                assert flag.enabled is False
                default_flag = await create_flag(session, key="beta-ui")
                assert default_flag.enabled is False

        asyncio.run(_run())

    def test_get_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="test-flag", enabled=True)
                flag = await get_flag(session, "test-flag")
                assert flag is not None
                assert flag.enabled is True

        asyncio.run(_run())

    def test_get_flag_not_found(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await get_flag(session, "nonexistent") is None

        asyncio.run(_run())

    def test_get_all_flags(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f1")
                await create_flag(session, key="f2")
                assert len(await get_all_flags(session)) == 2

        asyncio.run(_run())

    def test_update_flag_enable(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=False)
                updated = await update_flag(session, "f", enabled=True)
                assert updated is not None
                assert updated.enabled is True
                updated = await update_flag(session, "f", description="new desc")
                assert updated is not None
                assert updated.description == "new desc"
                assert updated.enabled is True

        asyncio.run(_run())

    def test_update_flag_not_found(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await update_flag(session, "missing", enabled=True) is None

        asyncio.run(_run())

    def test_delete_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f")
                assert await delete_flag(session, "f") is True
                assert await get_flag(session, "f") is None

        asyncio.run(_run())

    def test_delete_flag_not_found(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await delete_flag(session, "missing") is False

        asyncio.run(_run())

    def test_create_flag_duplicate_raises(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="dup")
                with pytest.raises(ValueError, match="already exists"):
                    await create_flag(session, key="dup")

        asyncio.run(_run())


# --- Targeting rules ---


class TestTargeting:
    def test_no_rules_uses_enabled(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                assert await evaluate_flag(session, "f") is True

        asyncio.run(_run())

    def test_disabled_flag_always_false(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=False)
                assert await evaluate_flag(session, "f") is False

        asyncio.run(_run())

    def test_missing_flag_returns_false(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await evaluate_flag(session, "nonexistent") is False

        asyncio.run(_run())

    def test_org_targeting(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.ORG, values=["org-acme"])],
                )
                assert await evaluate_flag(session, "f", org_id="org-acme") is True
                assert await evaluate_flag(session, "f", org_id="org-other") is False

        asyncio.run(_run())

    def test_user_targeting(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[
                        TargetingRule(type=RuleType.USER, values=["alice@acme.com"])
                    ],
                )
                assert (
                    await evaluate_flag(session, "f", user_id="alice@acme.com") is True
                )
                assert (
                    await evaluate_flag(session, "f", user_id="bob@corp.com") is False
                )

        asyncio.run(_run())

    def test_percentage_targeting_zero(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["0"])],
                )
                assert await evaluate_flag(session, "f", user_id="anyone") is False
                assert await evaluate_flag(session, "f") is False

        asyncio.run(_run())

    def test_percentage_targeting_hundred(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["100"])],
                )
                assert await evaluate_flag(session, "f", user_id="anyone") is True

        asyncio.run(_run())

    def test_percentage_invalid_value_returns_false(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["abc"])],
                )
                assert await evaluate_flag(session, "f", user_id="anyone") is False
                fake_rule = TargetingRule(type=RuleType.ORG, values=[])
                fake_rule.type = "unknown_type"  # type: ignore[assignment]
                assert (
                    _matches_rule(fake_rule, "f", org_id=None, user_id=None) is False
                )

        asyncio.run(_run())

    def test_percentage_deterministic(self, db_factory):
        """Same user_id always gets the same result."""

        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["50"])],
                )
                results = [
                    await evaluate_flag(session, "f", user_id="stable-user")
                    for _ in range(10)
                ]
                assert len(set(results)) == 1

        asyncio.run(_run())

    def test_multiple_rules_any_match(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, key="f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[
                        TargetingRule(type=RuleType.ORG, values=["org-acme"]),
                        TargetingRule(type=RuleType.USER, values=["bob@corp.com"]),
                    ],
                )
                assert await evaluate_flag(session, "f", org_id="org-acme") is True
                assert (
                    await evaluate_flag(session, "f", user_id="bob@corp.com") is True
                )
                assert await evaluate_flag(session, "f", org_id="org-other") is False

        asyncio.run(_run())
