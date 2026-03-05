"""Tests for T12.2 — count functions, middleware caching, purge optimization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from modules.credit.audit import (
    _audit_entries,
    count_audit_entries,
    create_audit_entry,
    purge_audit_trail,
    reset_audit_trail,
)
from modules.credit.tenant import (
    _org_assessments,
    count_all_assessments,
    count_org_assessments,
    store_org_assessment,
)
from unittest.mock import patch

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base
from modules.credit.repo_api_keys import ApiKeyRepository
from modules.credit.middleware import HstsMiddleware, HttpsRedirectMiddleware
from modules.credit.webhooks import (
    EventType,
    count_webhooks,
    create_webhook,
    reset_webhooks,
)


class TestCountAuditEntries:
    """count_audit_entries() returns count without copying."""

    def test_returns_zero_on_empty(self) -> None:
        reset_audit_trail()
        assert count_audit_entries() == 0

    def test_returns_correct_count(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        create_audit_entry(
            action="assess", user_id="u2", request_summary={}, result_summary={}
        )
        assert count_audit_entries() == 2

    def test_returns_int(self) -> None:
        reset_audit_trail()
        assert isinstance(count_audit_entries(), int)


class TestCountAllAssessments:
    """count_all_assessments() sums across all orgs without list build."""

    def setup_method(self) -> None:
        _org_assessments.clear()

    def teardown_method(self) -> None:
        _org_assessments.clear()

    def test_returns_zero_on_empty(self) -> None:
        assert count_all_assessments() == 0

    def test_counts_across_orgs(self) -> None:
        store_org_assessment("org-A", {"score": 700})
        store_org_assessment("org-A", {"score": 750})
        store_org_assessment("org-B", {"score": 800})
        assert count_all_assessments() == 3

    def test_returns_int(self) -> None:
        assert isinstance(count_all_assessments(), int)


class TestCountOrgAssessments:
    """count_org_assessments() returns count for a specific org."""

    def setup_method(self) -> None:
        _org_assessments.clear()

    def teardown_method(self) -> None:
        _org_assessments.clear()

    def test_returns_zero_for_unknown_org(self) -> None:
        assert count_org_assessments("org-nonexistent") == 0

    def test_returns_correct_count(self) -> None:
        store_org_assessment("org-X", {"score": 700})
        store_org_assessment("org-X", {"score": 750})
        store_org_assessment("org-Y", {"score": 800})
        assert count_org_assessments("org-X") == 2
        assert count_org_assessments("org-Y") == 1

    def test_returns_int(self) -> None:
        assert isinstance(count_org_assessments("org-Z"), int)


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


class TestPurgeAuditPopleft:
    """purge_audit_trail uses popleft -- no full list copy."""

    def test_purge_removes_old_keeps_recent(self) -> None:
        reset_audit_trail()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        new_ts = datetime.now(timezone.utc).isoformat()
        _audit_entries.append(
            {"action": "old", "timestamp": old_ts, "user_id_hash": "x"}
        )
        _audit_entries.append(
            {"action": "new", "timestamp": new_ts, "user_id_hash": "y"}
        )
        purged = purge_audit_trail(max_age_days=50)
        assert purged == 1
        assert len(_audit_entries) == 1
        assert _audit_entries[0]["action"] == "new"

    def test_purge_all_old(self) -> None:
        reset_audit_trail()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        _audit_entries.append({"action": "a", "timestamp": old_ts, "user_id_hash": "x"})
        _audit_entries.append({"action": "b", "timestamp": old_ts, "user_id_hash": "y"})
        purged = purge_audit_trail(max_age_days=50)
        assert purged == 2
        assert len(_audit_entries) == 0

    def test_purge_none_when_all_recent(self) -> None:
        reset_audit_trail()
        create_audit_entry(
            action="assess", user_id="u1", request_summary={}, result_summary={}
        )
        purged = purge_audit_trail(max_age_days=50)
        assert purged == 0
        assert len(_audit_entries) == 1


class TestMiddlewareCachedProdCheck:
    """Middleware evaluates prod_check once at init (boolean _is_prod)."""

    def test_hsts_caches_prod_check_as_bool(self) -> None:
        """HstsMiddleware._is_prod should be a bool, evaluated at init."""
        mw = HstsMiddleware(app=None, prod_check=lambda: True)
        assert mw._is_prod is True
        mw2 = HstsMiddleware(app=None, prod_check=lambda: False)
        assert mw2._is_prod is False

    def test_https_redirect_caches_prod_check_as_bool(self) -> None:
        """HttpsRedirectMiddleware._is_prod should be a bool, evaluated at init."""
        mw = HttpsRedirectMiddleware(app=None, prod_check=lambda: True)
        assert mw._is_prod is True
        mw2 = HttpsRedirectMiddleware(app=None, prod_check=lambda: False)
        assert mw2._is_prod is False

    def test_hsts_prod_check_called_once_at_init(self) -> None:
        """prod_check lambda should be called exactly once during __init__."""
        call_count = {"n": 0}

        def counter():
            call_count["n"] += 1
            return True

        HstsMiddleware(app=None, prod_check=counter)
        assert call_count["n"] == 1

    def test_https_redirect_prod_check_called_once_at_init(self) -> None:
        """prod_check lambda should be called exactly once during __init__."""
        call_count = {"n": 0}

        def counter():
            call_count["n"] += 1
            return True

        HttpsRedirectMiddleware(app=None, prod_check=counter)
        assert call_count["n"] == 1


class TestApiKeyDbPersistence:
    """API keys are DB-backed via ApiKeyRepository."""

    def test_create_key_persists_and_lookup_returns_it(self) -> None:
        """Creating an API key persists it so lookup returns the record."""
        import asyncio

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
        """Revoking a key makes lookup return None."""
        import asyncio

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
        """get_usage_overview should call count_all_assessments, not get_all_assessments."""
        import asyncio

        from modules.credit.dashboard import get_usage_overview
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                with patch(
                    "modules.credit.dashboard.count_all_assessments", return_value=42
                ):
                    result = await get_usage_overview(session)
            return result

        result = asyncio.run(_run())
        assert result["total_assessments"] == 42

    def test_customer_list_uses_count_org_assessments(self) -> None:
        """get_customer_list should call count_org_assessments per customer."""
        import asyncio

        from modules.credit.dashboard import get_customer_list
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_users import UserRepository
        from modules.credit.password import hash_password

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
                    "modules.credit.dashboard.count_org_assessments", return_value=7
                ):
                    customers = await get_customer_list(session)
            return customers

        customers = asyncio.run(_run())
        assert customers[0]["assessment_count"] == 7

    def test_system_health_uses_count_audit_entries(self) -> None:
        """get_system_health should call count_audit_entries, not len(get_audit_trail())."""
        import asyncio

        from modules.credit.dashboard import get_system_health
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with factory() as session:
                with (
                    patch(
                        "modules.credit.dashboard.count_audit_entries",
                        return_value=99,
                    ),
                    patch("modules.credit.dashboard.count_webhooks", return_value=5),
                ):
                    health = await get_system_health(session)
            return health

        health = asyncio.run(_run())
        assert health["audit_entries"] == 99
        assert health["webhooks"] == 5
