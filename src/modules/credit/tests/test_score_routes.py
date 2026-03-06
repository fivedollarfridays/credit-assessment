"""Tests for score history endpoints — T23.3 TDD."""

from __future__ import annotations

from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD


# ---------------------------------------------------------------------------
# Cycle 4: GET /v1/scores/history
# ---------------------------------------------------------------------------


class TestScoreHistoryEndpoint:
    def test_returns_200(self, client, bypass_auth):
        resp = client.get("/v1/scores/history")
        assert resp.status_code == 200

    def test_response_shape(self, client, bypass_auth):
        resp = client.get("/v1/scores/history")
        data = resp.json()
        assert "entries" in data
        assert "latest_score" in data
        assert "delta" in data
        assert "trend" in data

    def test_requires_auth(self, client):
        resp = client.get("/v1/scores/history")
        assert resp.status_code in (401, 403)

    def test_pagination_params(self, client, bypass_auth):
        resp = client.get(
            "/v1/scores/history", params={"limit": 5, "offset": 0, "days": 30}
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 5: POST /v1/scores — manual score entry
# ---------------------------------------------------------------------------


class TestManualScoreEntry:
    def test_creates_manual_entry(self, client, bypass_auth):
        resp = client.post(
            "/v1/scores",
            json={"score": 720, "score_band": "good"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 720
        assert data["source"] == "manual"

    def test_accepts_notes(self, client, bypass_auth):
        resp = client.post(
            "/v1/scores",
            json={"score": 650, "score_band": "fair", "notes": "From annual report"},
        )
        assert resp.status_code == 201
        assert resp.json()["notes"] == "From annual report"

    def test_requires_auth(self, client):
        resp = client.post(
            "/v1/scores",
            json={"score": 720, "score_band": "good"},
        )
        assert resp.status_code in (401, 403)

    def test_rejects_invalid_score(self, client, bypass_auth):
        resp = client.post(
            "/v1/scores",
            json={"score": 200, "score_band": "poor"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cycle 6: Auto-record on assessment
# ---------------------------------------------------------------------------


class TestAutoRecordOnAssessment:
    def test_assessment_records_score(self, client, bypass_auth):
        # Run an assessment
        client.post("/v1/assess", json=VALID_ASSESS_PAYLOAD)
        # Check history has an entry
        resp = client.get("/v1/scores/history")
        data = resp.json()
        assert len(data["entries"]) >= 1
        assert data["entries"][0]["source"] == "assessment"

    def test_trend_direction_up(self, client, bypass_auth):
        # Use manual entries for reliable ordering
        client.post(
            "/v1/scores",
            json={"score": 620, "score_band": "poor"},
        )
        client.post(
            "/v1/scores",
            json={"score": 720, "score_band": "good"},
        )
        resp = client.get("/v1/scores/history")
        data = resp.json()
        assert data["trend"] == "up"
        assert data["delta"] > 0

    def test_trend_direction_down(self, client, bypass_auth):
        client.post("/v1/scores", json={"score": 720, "score_band": "good"})
        client.post("/v1/scores", json={"score": 620, "score_band": "poor"})
        resp = client.get("/v1/scores/history")
        data = resp.json()
        assert data["trend"] == "down"
        assert data["delta"] < 0

    def test_trend_direction_stable(self, client, bypass_auth):
        client.post("/v1/scores", json={"score": 700, "score_band": "good"})
        client.post("/v1/scores", json={"score": 700, "score_band": "good"})
        resp = client.get("/v1/scores/history")
        data = resp.json()
        assert data["trend"] == "stable"
        assert data["delta"] == 0
