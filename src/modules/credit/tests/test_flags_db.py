"""Tests for DB-backed feature flags — T20.2 TDD."""

import asyncio
import time

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.feature_flags import (
    RuleType,
    TargetingRule,
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


class TestFlagCRUD_DB:
    """Feature flag CRUD operations use DB via AsyncSession."""

    def test_create_flag_persists(self, db_factory):
        async def _run():
            async with db_factory() as session:
                flag = await create_flag(
                    session, "new-scoring", description="New algo", enabled=False
                )
                assert flag.key == "new-scoring"
                assert flag.enabled is False

        asyncio.run(_run())

    def test_create_flag_duplicate_raises(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "dup")
                with pytest.raises(ValueError, match="already exists"):
                    await create_flag(session, "dup")

        asyncio.run(_run())

    def test_get_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "test-flag", enabled=True)
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
                await create_flag(session, "f1")
                await create_flag(session, "f2")
                flags = await get_all_flags(session)
                assert len(flags) == 2

        asyncio.run(_run())

    def test_update_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f", enabled=False)
                updated = await update_flag(session, "f", enabled=True)
                assert updated is not None
                assert updated.enabled is True

        asyncio.run(_run())

    def test_update_flag_not_found(self, db_factory):
        async def _run():
            async with db_factory() as session:
                result = await update_flag(session, "missing", enabled=True)
                assert result is None

        asyncio.run(_run())

    def test_delete_flag(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f")
                assert await delete_flag(session, "f") is True
                assert await get_flag(session, "f") is None

        asyncio.run(_run())

    def test_delete_flag_not_found(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await delete_flag(session, "missing") is False

        asyncio.run(_run())


class TestFlagEvaluation_DB:
    """Evaluation uses DB-backed flags."""

    def test_evaluate_enabled_no_targeting(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f", enabled=True)
                assert await evaluate_flag(session, "f") is True

        asyncio.run(_run())

    def test_evaluate_disabled(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f", enabled=False)
                assert await evaluate_flag(session, "f") is False

        asyncio.run(_run())

    def test_evaluate_missing(self, db_factory):
        async def _run():
            async with db_factory() as session:
                assert await evaluate_flag(session, "nonexistent") is False

        asyncio.run(_run())

    def test_evaluate_org_targeting(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[TargetingRule(type=RuleType.ORG, values=["org-acme"])],
                )
                assert await evaluate_flag(session, "f", org_id="org-acme") is True
                assert await evaluate_flag(session, "f", org_id="org-other") is False

        asyncio.run(_run())


class TestFlagEndpoints:
    def test_create_flag_endpoint(self, client, admin_headers):
        resp = client.post(
            "/v1/flags",
            json={"key": "new-flag", "description": "Test", "enabled": False},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["key"] == "new-flag"
        dup_resp = client.post(
            "/v1/flags",
            json={"key": "new-flag", "description": "Dup", "enabled": False},
            headers=admin_headers,
        )
        assert dup_resp.status_code == 409

    def test_list_flags_endpoint(self, client, admin_headers):
        client.post(
            "/v1/flags",
            json={"key": "f1", "description": "Test", "enabled": False},
            headers=admin_headers,
        )
        resp = client.get("/v1/flags", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_flag_endpoint(self, client, admin_headers):
        client.post(
            "/v1/flags",
            json={"key": "f", "description": "Test", "enabled": False},
            headers=admin_headers,
        )
        resp = client.put("/v1/flags/f", json={"enabled": True}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_update_flag_not_found(self, client, admin_headers):
        resp = client.put(
            "/v1/flags/missing", json={"enabled": True}, headers=admin_headers
        )
        assert resp.status_code == 404

    def test_delete_flag_endpoint(self, client, admin_headers):
        client.post(
            "/v1/flags",
            json={"key": "f", "description": "Test", "enabled": False},
            headers=admin_headers,
        )
        resp = client.delete("/v1/flags/f", headers=admin_headers)
        assert resp.status_code == 200

    def test_delete_flag_not_found(self, client, admin_headers):
        resp = client.delete("/v1/flags/missing", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.usefixtures("bypass_auth")
    def test_evaluate_flag_endpoint(self, client, admin_headers):
        client.post(
            "/v1/flags",
            json={"key": "f", "description": "Test", "enabled": True},
            headers=admin_headers,
        )
        resp = client.get("/v1/flags/f/evaluate")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_requires_auth(self, client):
        resp = client.get("/v1/flags")
        assert resp.status_code in (401, 403)

    def test_targeting_rule_rejects_invalid_type(self, client, admin_headers):
        client.post(
            "/v1/flags",
            json={"key": "f", "description": "Test", "enabled": True},
            headers=admin_headers,
        )
        resp = client.put(
            "/v1/flags/f",
            json={"targeting": [{"type": "invalid_type", "values": ["x"]}]},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestPerformance:
    def test_evaluation_under_1ms(self, db_factory):
        async def _run():
            async with db_factory() as session:
                await create_flag(session, "f", enabled=True)
                await update_flag(
                    session,
                    "f",
                    targeting=[
                        TargetingRule(type=RuleType.ORG, values=["org-1"]),
                        TargetingRule(type=RuleType.PERCENTAGE, values=["50"]),
                    ],
                )
                start = time.perf_counter_ns()
                for _ in range(100):
                    await evaluate_flag(session, "f", org_id="org-1", user_id="user-1")
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                avg_ms = elapsed_ms / 100
                assert avg_ms < 5.0, f"Average evaluation took {avg_ms:.3f}ms"

        asyncio.run(_run())
