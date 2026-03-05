"""Tests for POST /v1/assess/simple — simplified credit assessment endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from modules.credit.router import app

_POOR_PAYLOAD = {
    "credit_score": 520,
    "utilization_percent": 85.0,
    "total_accounts": 8,
    "open_accounts": 4,
    "negative_items": ["collection_medical"],
    "payment_history_percent": 72.0,
    "oldest_account_months": 60,
}

_GOOD_PAYLOAD = {
    "credit_score": 700,
    "utilization_percent": 25.0,
    "total_accounts": 5,
    "open_accounts": 3,
    "payment_history_percent": 95.0,
    "oldest_account_months": 48,
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.usefixtures("bypass_auth")
class TestSimpleAssessEndpoint:
    """Test the simplified assessment endpoint."""

    def test_returns_200(self, client):
        resp = client.post("/v1/assess/simple", json=_POOR_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_all_assessment_fields(self, client):
        resp = client.post("/v1/assess/simple", json=_POOR_PAYLOAD)
        data = resp.json()
        assert "barrier_severity" in data
        assert "readiness" in data
        assert "thresholds" in data
        assert "dispute_pathway" in data
        assert "eligibility" in data
        assert "disclaimer" in data

    def test_derives_score_band(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={**_POOR_PAYLOAD, "utilization_percent": 30.0},
        )
        assert resp.status_code == 200
        assert resp.json()["readiness"]["score_band"] == "very_poor"

    def test_derives_score_band_excellent(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={
                **_GOOD_PAYLOAD,
                "credit_score": 780,
                "utilization_percent": 10.0,
                "total_accounts": 12,
                "open_accounts": 8,
                "payment_history_percent": 99.0,
                "oldest_account_months": 180,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["readiness"]["score_band"] == "excellent"

    def test_counts_collections_from_negative_items(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={
                **_POOR_PAYLOAD,
                "negative_items": [
                    "collection_medical",
                    "collection_utility",
                    "late_payment_auto",
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        descriptions = [b["description"] for b in data["barrier_details"]]
        assert any("collection" in d.lower() for d in descriptions)

    def test_minimal_payload(self, client):
        """Only required fields — everything else defaults."""
        resp = client.post("/v1/assess/simple", json=_GOOD_PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["readiness"]["score_band"] == "good"

    def test_optional_balance_fields(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={
                **_GOOD_PAYLOAD,
                "credit_score": 650,
                "utilization_percent": 40.0,
                "total_accounts": 6,
                "open_accounts": 4,
                "payment_history_percent": 88.0,
                "oldest_account_months": 36,
                "total_balance": 13500.0,
                "total_credit_limit": 30000.0,
                "monthly_payments": 450.0,
            },
        )
        assert resp.status_code == 200

    def test_invalid_score_returns_422(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={**_GOOD_PAYLOAD, "credit_score": 200},
        )
        assert resp.status_code == 422

    def test_open_exceeds_total_returns_422(self, client):
        resp = client.post(
            "/v1/assess/simple",
            json={**_GOOD_PAYLOAD, "total_accounts": 3, "open_accounts": 5},
        )
        assert resp.status_code == 422


class TestScoreToBand:
    """Unit tests for _score_to_band helper."""

    def test_out_of_range_raises(self):
        from modules.credit.assess_routes import _score_to_band

        with pytest.raises(ValueError, match="out of range"):
            _score_to_band(200)


class TestSimpleAssessAuth:
    """Auth is required for /v1/assess/simple."""

    def test_requires_auth(self):
        raw_client = TestClient(app)
        resp = raw_client.post("/v1/assess/simple", json=_GOOD_PAYLOAD)
        assert resp.status_code in (401, 403)
