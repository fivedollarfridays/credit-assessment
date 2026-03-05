"""Tests for POST /v1/simulate endpoint — T21.3 TDD."""

from __future__ import annotations

from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD


# ---------------------------------------------------------------------------
# Cycle 1: POST /v1/simulate — auth + response shape
# ---------------------------------------------------------------------------


class TestSimulateEndpoint:
    """Test POST /v1/simulate with full CreditProfile."""

    VALID_SIMULATE_PAYLOAD = {
        "profile": VALID_ASSESS_PAYLOAD,
        "actions": [{"action_type": "pay_down_debt", "target_amount": 5000.0}],
    }

    def test_returns_200_with_auth(self, client, bypass_auth):
        resp = client.post("/v1/simulate", json=self.VALID_SIMULATE_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_simulation_fields(self, client, bypass_auth):
        resp = client.post("/v1/simulate", json=self.VALID_SIMULATE_PAYLOAD)
        data = resp.json()
        assert "original_score" in data
        assert "projected_score" in data
        assert "score_delta" in data
        assert "actions_applied" in data

    def test_projected_score_is_int(self, client, bypass_auth):
        resp = client.post("/v1/simulate", json=self.VALID_SIMULATE_PAYLOAD)
        data = resp.json()
        assert isinstance(data["projected_score"], int)
        assert data["original_score"] == 740


# ---------------------------------------------------------------------------
# Cycle 2: POST /v1/simulate/simple
# ---------------------------------------------------------------------------


class TestSimulateSimple:
    """Test POST /v1/simulate/simple with SimpleCreditProfile."""

    SIMPLE_PAYLOAD = {
        "profile": {
            "credit_score": 650,
            "utilization_percent": 60.0,
            "total_accounts": 6,
            "open_accounts": 4,
            "payment_history_percent": 85.0,
            "oldest_account_months": 48,
            "total_balance": 18000.0,
            "total_credit_limit": 30000.0,
        },
        "actions": [
            {"action_type": "pay_down_debt", "target_amount": 10000.0},
        ],
    }

    def test_simple_returns_200(self, client, bypass_auth):
        resp = client.post("/v1/simulate/simple", json=self.SIMPLE_PAYLOAD)
        assert resp.status_code == 200

    def test_simple_converts_profile(self, client, bypass_auth):
        resp = client.post("/v1/simulate/simple", json=self.SIMPLE_PAYLOAD)
        data = resp.json()
        assert data["original_score"] == 650
        assert data["projected_score"] > 650


# ---------------------------------------------------------------------------
# Cycle 3: Validation + auth
# ---------------------------------------------------------------------------


class TestSimulateValidation:
    """Test validation and auth on simulate endpoints."""

    def test_requires_auth(self, client):
        payload = {
            "profile": VALID_ASSESS_PAYLOAD,
            "actions": [{"action_type": "pay_on_time"}],
        }
        resp = client.post("/v1/simulate", json=payload)
        assert resp.status_code in (401, 403)

    def test_rejects_empty_actions(self, client, bypass_auth):
        payload = {
            "profile": VALID_ASSESS_PAYLOAD,
            "actions": [],
        }
        resp = client.post("/v1/simulate", json=payload)
        assert resp.status_code == 422

    def test_rejects_more_than_10_actions(self, client, bypass_auth):
        payload = {
            "profile": VALID_ASSESS_PAYLOAD,
            "actions": [{"action_type": "pay_on_time"}] * 11,
        }
        resp = client.post("/v1/simulate", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cycle 4: Disclaimer
# ---------------------------------------------------------------------------


class TestSimulateDisclaimer:
    """Test FCRA disclaimer in simulation response."""

    def test_response_includes_disclaimer(self, client, bypass_auth):
        payload = {
            "profile": VALID_ASSESS_PAYLOAD,
            "actions": [{"action_type": "pay_on_time"}],
        }
        resp = client.post("/v1/simulate", json=payload)
        data = resp.json()
        assert "disclaimer" in data
        assert "estimates" in data["disclaimer"].lower()

    def test_simple_includes_disclaimer(self, client, bypass_auth):
        payload = {
            "profile": {
                "credit_score": 650,
                "utilization_percent": 60.0,
                "total_accounts": 6,
                "open_accounts": 4,
                "payment_history_percent": 85.0,
                "oldest_account_months": 48,
            },
            "actions": [{"action_type": "pay_on_time"}],
        }
        resp = client.post("/v1/simulate/simple", json=payload)
        data = resp.json()
        assert "disclaimer" in data
