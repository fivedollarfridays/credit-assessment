"""Tests for dispute lifecycle endpoints — T23.2 TDD."""

from __future__ import annotations

_ITEM = {"type": "collection", "description": "Medical debt sent to collections"}


# ---------------------------------------------------------------------------
# Cycle 1: POST /v1/disputes — create dispute
# ---------------------------------------------------------------------------


class TestCreateDispute:
    def test_creates_in_draft_status(self, client, bypass_auth):
        resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["bureau"] == "equifax"
        assert data["round"] == 1
        assert data["id"] is not None

    def test_requires_auth(self, client):
        resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        assert resp.status_code in (401, 403)

    def test_rejects_missing_bureau(self, client, bypass_auth):
        resp = client.post(
            "/v1/disputes",
            json={"negative_item_data": _ITEM},
        )
        assert resp.status_code == 422

    def test_rejects_missing_item_data(self, client, bypass_auth):
        resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax"},
        )
        assert resp.status_code == 422

    def test_accepts_optional_letter_type(self, client, bypass_auth):
        resp = client.post(
            "/v1/disputes",
            json={
                "bureau": "experian",
                "negative_item_data": _ITEM,
                "letter_type": "validation",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["letter_type"] == "validation"


# ---------------------------------------------------------------------------
# Cycle 2: GET /v1/disputes — list disputes
# ---------------------------------------------------------------------------


class TestListDisputes:
    def test_list_returns_paginated(self, client, bypass_auth):
        for _ in range(3):
            client.post(
                "/v1/disputes",
                json={"bureau": "equifax", "negative_item_data": _ITEM},
            )
        resp = client.get("/v1/disputes")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_list_with_status_filter(self, client, bypass_auth):
        client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        resp = client.get("/v1/disputes", params={"status": "draft"})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "draft"

    def test_list_with_pagination(self, client, bypass_auth):
        for _ in range(5):
            client.post(
                "/v1/disputes",
                json={"bureau": "equifax", "negative_item_data": _ITEM},
            )
        resp = client.get("/v1/disputes", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_list_requires_auth(self, client):
        resp = client.get("/v1/disputes")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cycle 3: GET /v1/disputes/{id} — get single dispute
# ---------------------------------------------------------------------------


class TestGetDispute:
    def test_get_by_id(self, client, bypass_auth):
        create_resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        dispute_id = create_resp.json()["id"]
        resp = client.get(f"/v1/disputes/{dispute_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == dispute_id

    def test_get_nonexistent_returns_404(self, client, bypass_auth):
        resp = client.get("/v1/disputes/99999")
        assert resp.status_code == 404

    def test_get_requires_auth(self, client):
        resp = client.get("/v1/disputes/1")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cycle 4: PATCH /v1/disputes/{id}/status — update status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    def test_draft_to_sent(self, client, bypass_auth):
        create_resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        dispute_id = create_resp.json()["id"]
        resp = client.patch(
            f"/v1/disputes/{dispute_id}/status",
            json={"status": "sent"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["sent_at"] is not None
        assert data["deadline_at"] is not None

    def test_invalid_transition_returns_400(self, client, bypass_auth):
        create_resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        dispute_id = create_resp.json()["id"]
        resp = client.patch(
            f"/v1/disputes/{dispute_id}/status",
            json={"status": "resolved"},
        )
        assert resp.status_code == 400

    def test_nonexistent_dispute_returns_404(self, client, bypass_auth):
        resp = client.patch(
            "/v1/disputes/99999/status",
            json={"status": "sent"},
        )
        assert resp.status_code == 404

    def test_update_requires_auth(self, client):
        resp = client.patch(
            "/v1/disputes/1/status",
            json={"status": "sent"},
        )
        assert resp.status_code in (401, 403)

    def test_resolution_field_on_resolve(self, client, bypass_auth):
        create_resp = client.post(
            "/v1/disputes",
            json={"bureau": "equifax", "negative_item_data": _ITEM},
        )
        did = create_resp.json()["id"]
        # Walk through full lifecycle: draft -> sent -> in_review -> responded -> resolved
        for status in ("sent", "in_review", "responded"):
            client.patch(f"/v1/disputes/{did}/status", json={"status": status})
        resp = client.patch(
            f"/v1/disputes/{did}/status",
            json={"status": "resolved", "resolution": "Item removed from report"},
        )
        assert resp.status_code == 200
        assert resp.json()["resolution"] == "Item removed from report"


# ---------------------------------------------------------------------------
# Cycle 5: GET /v1/disputes/deadlines — approaching deadlines
# ---------------------------------------------------------------------------


class TestDeadlines:
    def test_deadlines_endpoint(self, client, bypass_auth):
        resp = client.get("/v1/disputes/deadlines")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_deadlines_requires_auth(self, client):
        resp = client.get("/v1/disputes/deadlines")
        assert resp.status_code in (401, 403)

    def test_deadlines_days_ahead_param(self, client, bypass_auth):
        resp = client.get("/v1/disputes/deadlines", params={"days_ahead": 14})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 6: Admin org-wide access
# ---------------------------------------------------------------------------


class TestAdminAccess:
    def test_admin_can_list_org_disputes(self, client, admin_headers):
        resp = client.get("/v1/disputes", headers=admin_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()
