"""Tests for T12.2 — count functions, middleware caching, purge optimization."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from modules.credit.audit import (
    count_audit_entries,
    create_audit_entry,
    purge_audit_trail,
)
from modules.credit.database import create_engine, get_session_factory
from modules.credit.middleware import HstsMiddleware, HttpsRedirectMiddleware
from modules.credit.models_db import Base
from modules.credit.repo_api_keys import ApiKeyRepository
from modules.credit.repo_assessments import AssessmentRepository
from modules.credit.tenant import (
    count_all_assessments,
    count_org_assessments,
)
from modules.credit.webhooks import (
    EventType,
    count_webhooks,
    create_webhook,
    reset_webhooks,
)


def _make_db():
    """Create in-memory database for tests."""
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


class TestCountAuditEntries:
    """count_audit_entries() returns count without copying."""

    def test_returns_zero_on_empty(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_audit_entries(session)

        assert asyncio.run(_run()) == 0

    def test_returns_correct_count(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u2",
                    request_summary={},
                    result_summary={},
                )
                return await count_audit_entries(session)

        assert asyncio.run(_run()) == 2

    def test_returns_int(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_audit_entries(session)

        assert isinstance(asyncio.run(_run()), int)


class TestCountAllAssessments:
    """count_all_assessments() sums across all orgs via SQL COUNT."""

    def test_returns_zero_on_empty(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_all_assessments(session)

        assert asyncio.run(_run()) == 0

    def test_counts_across_orgs(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    org_id="org-A",
                )
                await repo.save_assessment(
                    credit_score=750,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=85,
                    request_payload={},
                    response_payload={},
                    org_id="org-A",
                )
                await repo.save_assessment(
                    credit_score=800,
                    score_band="excellent",
                    barrier_severity="low",
                    readiness_score=95,
                    request_payload={},
                    response_payload={},
                    org_id="org-B",
                )
                return await count_all_assessments(session)

        assert asyncio.run(_run()) == 3

    def test_returns_int(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_all_assessments(session)

        assert isinstance(asyncio.run(_run()), int)


class TestCountOrgAssessments:
    """count_org_assessments() returns count for a specific org."""

    def test_returns_zero_for_unknown_org(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_org_assessments(session, "org-nonexistent")

        assert asyncio.run(_run()) == 0

    def test_returns_correct_count(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                repo = AssessmentRepository(session)
                await repo.save_assessment(
                    credit_score=700,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80,
                    request_payload={},
                    response_payload={},
                    org_id="org-X",
                )
                await repo.save_assessment(
                    credit_score=750,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=85,
                    request_payload={},
                    response_payload={},
                    org_id="org-X",
                )
                await repo.save_assessment(
                    credit_score=800,
                    score_band="excellent",
                    barrier_severity="low",
                    readiness_score=95,
                    request_payload={},
                    response_payload={},
                    org_id="org-Y",
                )
                x = await count_org_assessments(session, "org-X")
                y = await count_org_assessments(session, "org-Y")
                return x, y

        x, y = asyncio.run(_run())
        assert x == 2
        assert y == 1

    def test_returns_int(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_org_assessments(session, "org-Z")

        assert isinstance(asyncio.run(_run()), int)


class TestCountWebhooks:
    """count_webhooks() returns count without copying."""

    def setup_method(self) -> None:
        reset_webhooks()

    def teardown_method(self) -> None:
        reset_webhooks()

    def test_returns_zero_on_empty(self) -> None:
        assert count_webhooks() == 0

    def test_returns_correct_count(self) -> None:
        create_webhook(
            url="https://a.com/h",
            events=[EventType.ASSESSMENT_COMPLETED],
            secret="s",
        )
        create_webhook(
            url="https://b.com/h",
            events=[EventType.SUBSCRIPTION_UPDATED],
            secret="s",
        )
        assert count_webhooks() == 2

    def test_returns_int(self) -> None:
        assert isinstance(count_webhooks(), int)


class TestPurgeAuditDB:
    """purge_audit_trail uses DB DELETE with date filter."""

    def test_purge_none_when_all_recent(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                await create_audit_entry(
                    session,
                    action="assess",
                    user_id="u1",
                    request_summary={},
                    result_summary={},
                )
                purged = await purge_audit_trail(session, max_age_days=50)
                count = await count_audit_entries(session)
                return purged, count

        purged, count = asyncio.run(_run())
        assert purged == 0
        assert count == 1


class TestMiddlewareCachedProdCheck:
    """Middleware evaluates prod_check once at init (boolean _is_prod)."""

    def test_hsts_caches_prod_check_as_bool(self) -> None:
        mw = HstsMiddleware(app=None, prod_check=lambda: True)
        assert mw._is_prod is True
        mw2 = HstsMiddleware(app=None, prod_check=lambda: False)
        assert mw2._is_prod is False

    def test_https_redirect_caches_prod_check_as_bool(self) -> None:
        mw = HttpsRedirectMiddleware(app=None, prod_check=lambda: True)
        assert mw._is_prod is True
        mw2 = HttpsRedirectMiddleware(app=None, prod_check=lambda: False)
        assert mw2._is_prod is False

    def test_hsts_prod_check_called_once_at_init(self) -> None:
        call_count = {"n": 0}

        def counter():
            call_count["n"] += 1
            return True

        HstsMiddleware(app=None, prod_check=counter)
        assert call_count["n"] == 1

    def test_https_redirect_prod_check_called_once_at_init(self) -> None:
        call_count = {"n": 0}

        def counter():
            call_count["n"] += 1
            return True

        HttpsRedirectMiddleware(app=None, prod_check=counter)
        assert call_count["n"] == 1


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
        assert result.key == "test-key-1"
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
                    patch("modules.credit.dashboard.count_webhooks", return_value=5),
                ):
                    health = await get_system_health(session)
            return health

        health = asyncio.run(_run())
        assert health["audit_entries"] == 99
        assert health["webhooks"] == 5
