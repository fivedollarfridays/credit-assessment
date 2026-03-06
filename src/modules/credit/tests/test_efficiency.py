"""Tests for T12.2 — count functions, middleware caching, purge optimization."""

from __future__ import annotations

import asyncio
from modules.credit.audit import (
    count_audit_entries,
    create_audit_entry,
    purge_audit_trail,
)
from modules.credit.database import create_engine, get_session_factory
from modules.credit.middleware import HstsMiddleware, HttpsRedirectMiddleware
from modules.credit.models_db import Base
from modules.credit.repo_assessments import AssessmentRepository
from modules.credit.tenant import (
    count_all_assessments,
    count_org_assessments,
)
from modules.credit.webhooks import (
    EventType,
    count_webhooks,
    create_webhook,
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

    def test_returns_zero_on_empty(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_webhooks(session)

        assert asyncio.run(_run()) == 0

    def test_returns_correct_count(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                await create_webhook(
                    session,
                    url="https://a.com/h",
                    events=[EventType.ASSESSMENT_COMPLETED],
                    secret="s",
                )
                await create_webhook(
                    session,
                    url="https://b.com/h",
                    events=[EventType.SUBSCRIPTION_UPDATED],
                    secret="s",
                )
                return await count_webhooks(session)

        assert asyncio.run(_run()) == 2

    def test_returns_int(self) -> None:
        factory = _make_db()

        async def _run():
            async with factory() as session:
                return await count_webhooks(session)

        assert isinstance(asyncio.run(_run()), int)


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
