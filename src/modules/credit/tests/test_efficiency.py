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
from collections import OrderedDict
from unittest.mock import patch

from modules.credit.admin_routes import _api_keys
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


class TestApiKeysOrderedDict:
    """_api_keys must be OrderedDict with popitem(last=False) eviction."""

    def test_api_keys_is_ordered_dict(self) -> None:
        assert isinstance(_api_keys, OrderedDict)

    def test_popitem_last_false_evicts_oldest(self) -> None:
        """OrderedDict.popitem(last=False) removes the first inserted key."""
        saved = OrderedDict(_api_keys)
        _api_keys.clear()
        _api_keys["first"] = {"org_id": "o1", "role": "viewer", "expires_at": None}
        _api_keys["second"] = {"org_id": "o2", "role": "viewer", "expires_at": None}
        evicted_key, _ = _api_keys.popitem(last=False)
        assert evicted_key == "first"
        assert "second" in _api_keys
        _api_keys.clear()
        _api_keys.update(saved)


class TestDashboardUsesCountFunctions:
    """Dashboard must use count functions, not len(get_*())."""

    def test_overview_uses_count_all_assessments(self) -> None:
        """get_usage_overview should call count_all_assessments, not get_all_assessments."""
        from modules.credit.dashboard import get_usage_overview

        with patch("modules.credit.dashboard.count_all_assessments", return_value=42):
            result = get_usage_overview()
        assert result["total_assessments"] == 42

    def test_customer_list_uses_count_org_assessments(self) -> None:
        """get_customer_list should call count_org_assessments per customer."""
        from modules.credit.dashboard import get_customer_list
        from modules.credit.user_store import _users
        from modules.credit.password import hash_password

        _users.clear()
        _users["a@b.com"] = {
            "email": "a@b.com",
            "password_hash": hash_password("pw"),
            "is_active": True,
            "role": "viewer",
            "org_id": "org-a",
        }
        with patch("modules.credit.dashboard.count_org_assessments", return_value=7):
            customers = get_customer_list()
        assert customers[0]["assessment_count"] == 7
        _users.clear()

    def test_system_health_uses_count_audit_entries(self) -> None:
        """get_system_health should call count_audit_entries, not len(get_audit_trail())."""
        from modules.credit.dashboard import get_system_health

        with (
            patch("modules.credit.dashboard.count_audit_entries", return_value=99),
            patch("modules.credit.dashboard.count_webhooks", return_value=5),
        ):
            health = get_system_health()
        assert health["audit_entries"] == 99
        assert health["webhooks"] == 5
