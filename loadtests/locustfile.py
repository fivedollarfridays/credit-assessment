"""Locust load testing script for Credit Assessment API."""

from locust import HttpUser, between, task


class CreditApiUser(HttpUser):
    """Simulates a user interacting with the Credit Assessment API."""

    wait_time = between(0.5, 2)

    @task(1)
    def health_check(self) -> None:
        """GET /health -- lightweight liveness probe."""
        self.client.get("/health")

    @task(3)
    def assess(self) -> None:
        """POST /v1/assess -- main assessment endpoint."""
        self.client.post(
            "/v1/assess",
            json={
                "current_score": 740,
                "score_band": "good",
                "overall_utilization": 20.0,
                "account_summary": {
                    "total_accounts": 8,
                    "open_accounts": 6,
                },
                "payment_history_pct": 98.0,
                "average_account_age_months": 72,
            },
            headers={"X-API-Key": "test-key"},
        )
