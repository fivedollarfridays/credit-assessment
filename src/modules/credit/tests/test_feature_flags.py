"""Tests for feature flags — evaluation, targeting, admin management."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

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
    reset_flags,
    update_flag,
)
from modules.credit.router import app


@pytest.fixture(autouse=True)
def _clean():
    reset_flags()
    yield
    reset_flags()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- Flag CRUD ---


class TestFlagCRUD:
    def test_create_flag(self):
        flag = create_flag(
            key="new-scoring", description="New scoring algo", enabled=False
        )
        assert isinstance(flag, FeatureFlag)
        assert flag.key == "new-scoring"
        assert flag.enabled is False
        # Default enabled is False
        default_flag = create_flag(key="beta-ui")
        assert default_flag.enabled is False

    def test_get_flag(self):
        create_flag(key="test-flag", enabled=True)
        flag = get_flag("test-flag")
        assert flag is not None
        assert flag.enabled is True

    def test_get_flag_not_found(self):
        assert get_flag("nonexistent") is None

    def test_get_all_flags(self):
        create_flag(key="f1")
        create_flag(key="f2")
        assert len(get_all_flags()) == 2

    def test_update_flag_enable(self):
        create_flag(key="f", enabled=False)
        updated = update_flag("f", enabled=True)
        assert updated is not None
        assert updated.enabled is True
        # Cover description-only update (feature_flags.py:87)
        updated = update_flag("f", description="new desc")
        assert updated is not None
        assert updated.description == "new desc"
        assert updated.enabled is True  # unchanged

    def test_update_flag_not_found(self):
        assert update_flag("missing", enabled=True) is None

    def test_delete_flag(self):
        create_flag(key="f")
        assert delete_flag("f") is True
        assert get_flag("f") is None

    def test_delete_flag_not_found(self):
        assert delete_flag("missing") is False

    def test_create_flag_duplicate_raises(self):
        create_flag(key="dup")
        with pytest.raises(ValueError, match="already exists"):
            create_flag(key="dup")


# --- Targeting rules ---


class TestTargeting:
    def test_no_rules_uses_enabled(self):
        create_flag(key="f", enabled=True)
        assert evaluate_flag("f") is True

    def test_disabled_flag_always_false(self):
        create_flag(key="f", enabled=False)
        assert evaluate_flag("f") is False

    def test_missing_flag_returns_false(self):
        assert evaluate_flag("nonexistent") is False

    def test_org_targeting(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f", targeting=[TargetingRule(type=RuleType.ORG, values=["org-acme"])]
        )
        assert evaluate_flag("f", org_id="org-acme") is True
        assert evaluate_flag("f", org_id="org-other") is False

    def test_user_targeting(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f",
            targeting=[TargetingRule(type=RuleType.USER, values=["alice@acme.com"])],
        )
        assert evaluate_flag("f", user_id="alice@acme.com") is True
        assert evaluate_flag("f", user_id="bob@corp.com") is False

    def test_percentage_targeting_zero(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f", targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["0"])]
        )
        assert evaluate_flag("f", user_id="anyone") is False
        # Cover user_id=None for percentage targeting (feature_flags.py:121)
        assert evaluate_flag("f") is False

    def test_percentage_targeting_hundred(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f", targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["100"])]
        )
        assert evaluate_flag("f", user_id="anyone") is True

    def test_percentage_invalid_value_returns_false(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f", targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["abc"])]
        )
        assert evaluate_flag("f", user_id="anyone") is False
        # Cover unknown rule type fallback (feature_flags.py:127)
        fake_rule = TargetingRule(type=RuleType.ORG, values=[])
        fake_rule.type = "unknown_type"  # type: ignore[assignment]
        assert _matches_rule(fake_rule, "f", org_id=None, user_id=None) is False

    def test_percentage_deterministic(self):
        """Same user_id always gets the same result."""
        create_flag(key="f", enabled=True)
        update_flag(
            "f", targeting=[TargetingRule(type=RuleType.PERCENTAGE, values=["50"])]
        )
        results = [evaluate_flag("f", user_id="stable-user") for _ in range(10)]
        assert len(set(results)) == 1  # Always same result

    def test_multiple_rules_any_match(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f",
            targeting=[
                TargetingRule(type=RuleType.ORG, values=["org-acme"]),
                TargetingRule(type=RuleType.USER, values=["bob@corp.com"]),
            ],
        )
        assert evaluate_flag("f", org_id="org-acme") is True
        assert evaluate_flag("f", user_id="bob@corp.com") is True
        assert evaluate_flag("f", org_id="org-other") is False


# --- Performance ---


class TestPerformance:
    def test_evaluation_under_1ms(self):
        create_flag(key="f", enabled=True)
        update_flag(
            "f",
            targeting=[
                TargetingRule(type=RuleType.ORG, values=["org-1"]),
                TargetingRule(type=RuleType.PERCENTAGE, values=["50"]),
            ],
        )
        start = time.perf_counter_ns()
        for _ in range(1000):
            evaluate_flag("f", org_id="org-1", user_id="user-1")
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        avg_ms = elapsed_ms / 1000
        assert avg_ms < 1.0, f"Average evaluation took {avg_ms:.3f}ms"


# --- API Endpoints ---


class TestFlagEndpoints:
    def test_create_flag_endpoint(self, client, admin_headers):
        resp = client.post(
            "/v1/flags",
            json={"key": "new-flag", "description": "Test", "enabled": False},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["key"] == "new-flag"
        # Cover duplicate flag creation 409 (flag_routes.py:69-70)
        dup_resp = client.post(
            "/v1/flags",
            json={"key": "new-flag", "description": "Dup", "enabled": False},
            headers=admin_headers,
        )
        assert dup_resp.status_code == 409

    def test_list_flags_endpoint(self, client, admin_headers):
        create_flag(key="f1")
        resp = client.get("/v1/flags", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_flag_endpoint(self, client, admin_headers):
        create_flag(key="f", enabled=False)
        resp = client.put("/v1/flags/f", json={"enabled": True}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_update_flag_not_found(self, client, admin_headers):
        resp = client.put(
            "/v1/flags/missing", json={"enabled": True}, headers=admin_headers
        )
        assert resp.status_code == 404

    def test_delete_flag_endpoint(self, client, admin_headers):
        create_flag(key="f")
        resp = client.delete("/v1/flags/f", headers=admin_headers)
        assert resp.status_code == 200

    def test_delete_flag_not_found(self, client, admin_headers):
        resp = client.delete("/v1/flags/missing", headers=admin_headers)
        assert resp.status_code == 404

    def test_evaluate_flag_endpoint(self, client):
        create_flag(key="f", enabled=True)
        resp = client.get("/v1/flags/f/evaluate", headers={"X-API-Key": "test"})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_requires_auth(self, client):
        resp = client.get("/v1/flags")
        assert resp.status_code in (401, 403)

    def test_targeting_rule_rejects_invalid_type(self, client, admin_headers):
        create_flag(key="f", enabled=True)
        resp = client.put(
            "/v1/flags/f",
            json={"targeting": [{"type": "invalid_type", "values": ["x"]}]},
            headers=admin_headers,
        )
        assert resp.status_code == 422
