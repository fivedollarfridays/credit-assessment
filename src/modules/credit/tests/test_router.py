"""Tests for FastAPI router — TDD: written before implementation."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from modules.credit.router import app

    return TestClient(app)


class TestLifespan:
    """Test application lifespan lifecycle."""

    def test_lifespan_configures_logging(self):
        import asyncio

        from modules.credit.router import app, lifespan

        async def _run():
            async with lifespan(app):
                pass

        asyncio.run(_run())


class TestHealthEndpoint:
    """Test GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self, client):
        response = client.get("/health")
        assert response.json()["status"] == "ok"


@pytest.mark.usefixtures("bypass_auth")
class TestAssessEndpoint:
    """Test POST /assess."""

    def test_valid_good_profile_returns_200(self, client):
        payload = {
            "current_score": 740,
            "score_band": "good",
            "overall_utilization": 20.0,
            "account_summary": {"total_accounts": 8, "open_accounts": 6},
            "payment_history_pct": 98.0,
            "average_account_age_months": 72,
        }
        response = client.post("/assess", json=payload)
        assert response.status_code == 200

    def test_returns_all_five_outputs(self, client):
        payload = {
            "current_score": 650,
            "score_band": "fair",
            "overall_utilization": 45.0,
            "account_summary": {
                "total_accounts": 6,
                "open_accounts": 4,
                "negative_accounts": 1,
            },
            "payment_history_pct": 88.0,
            "average_account_age_months": 36,
            "negative_items": ["late_payment_30day"],
        }
        response = client.post("/assess", json=payload)
        data = response.json()
        assert "barrier_severity" in data
        assert "readiness" in data
        assert "thresholds" in data
        assert "dispute_pathway" in data
        assert "eligibility" in data

    def test_returns_disclaimer(self, client):
        payload = {
            "current_score": 740,
            "score_band": "good",
            "overall_utilization": 20.0,
            "account_summary": {"total_accounts": 8, "open_accounts": 6},
            "payment_history_pct": 98.0,
            "average_account_age_months": 72,
        }
        response = client.post("/assess", json=payload)
        data = response.json()
        assert "educational" in data["disclaimer"].lower()

    def test_invalid_score_returns_422(self, client):
        payload = {
            "current_score": 200,
            "score_band": "very_poor",
            "overall_utilization": 50.0,
            "account_summary": {"total_accounts": 5, "open_accounts": 3},
            "payment_history_pct": 80.0,
            "average_account_age_months": 24,
        }
        response = client.post("/assess", json=payload)
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client):
        payload = {"current_score": 700}
        response = client.post("/assess", json=payload)
        assert response.status_code == 422

    def test_poor_profile_high_severity(self, client):
        payload = {
            "current_score": 520,
            "score_band": "very_poor",
            "overall_utilization": 85.0,
            "account_summary": {
                "total_accounts": 12,
                "open_accounts": 5,
                "negative_accounts": 5,
                "collection_accounts": 3,
            },
            "payment_history_pct": 62.0,
            "average_account_age_months": 48,
            "negative_items": [
                "collection_medical_2500",
                "collection_utility_800",
                "collection_credit_card_5000",
            ],
        }
        response = client.post("/assess", json=payload)
        data = response.json()
        assert data["barrier_severity"] == "high"
        assert data["readiness"]["score"] < 40
