"""Tests for letter generation endpoints — T22.3 TDD."""

from __future__ import annotations

import pytest


VALID_LETTER_PAYLOAD = {
    "negative_item": {
        "type": "collection",
        "description": "Medical debt sent to collections",
        "creditor": "ABC Collections",
        "amount": 1500.0,
        "date_reported": "2024-01-15",
    },
    "letter_type": "validation",
    "bureau": "equifax",
    "consumer_name": "Jane Doe",
}


# ---------------------------------------------------------------------------
# Cycle 1: POST /v1/disputes/letters — auth + response shape
# ---------------------------------------------------------------------------


class TestLetterEndpoint:
    def test_returns_200_with_auth(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_letter_fields(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        data = resp.json()
        assert "subject" in data
        assert "body" in data
        assert "bureau" in data
        assert "bureau_address" in data
        assert "legal_citations" in data
        assert "letter_type" in data
        assert "generated_at" in data
        assert "disclaimer" in data

    def test_body_contains_consumer_name(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        data = resp.json()
        assert "Jane Doe" in data["body"]

    def test_body_contains_creditor(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        data = resp.json()
        assert "ABC Collections" in data["body"]

    def test_bureau_matches_request(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        data = resp.json()
        assert data["bureau"] == "equifax"

    def test_letter_type_matches_request(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        data = resp.json()
        assert data["letter_type"] == "validation"


# ---------------------------------------------------------------------------
# Cycle 2: Auth + validation
# ---------------------------------------------------------------------------


class TestLetterAuth:
    def test_requires_auth(self, client):
        resp = client.post("/v1/disputes/letters", json=VALID_LETTER_PAYLOAD)
        assert resp.status_code in (401, 403)

    def test_rejects_invalid_letter_type(self, client, bypass_auth):
        payload = {**VALID_LETTER_PAYLOAD, "letter_type": "bogus"}
        resp = client.post("/v1/disputes/letters", json=payload)
        assert resp.status_code == 422

    def test_rejects_invalid_bureau(self, client, bypass_auth):
        payload = {**VALID_LETTER_PAYLOAD, "bureau": "fake_bureau"}
        resp = client.post("/v1/disputes/letters", json=payload)
        assert resp.status_code == 422

    def test_rejects_missing_consumer_name(self, client, bypass_auth):
        payload = {
            k: v for k, v in VALID_LETTER_PAYLOAD.items() if k != "consumer_name"
        }
        resp = client.post("/v1/disputes/letters", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cycle 3: POST /v1/disputes/letters/batch
# ---------------------------------------------------------------------------


class TestLetterBatch:
    BATCH_PAYLOAD = {
        "requests": [
            VALID_LETTER_PAYLOAD,
            {
                **VALID_LETTER_PAYLOAD,
                "letter_type": "inaccuracy",
                "bureau": "experian",
            },
        ],
    }

    def test_batch_returns_200(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters/batch", json=self.BATCH_PAYLOAD)
        assert resp.status_code == 200

    def test_batch_returns_list(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters/batch", json=self.BATCH_PAYLOAD)
        data = resp.json()
        assert "letters" in data
        assert len(data["letters"]) == 2

    def test_batch_requires_auth(self, client):
        resp = client.post("/v1/disputes/letters/batch", json=self.BATCH_PAYLOAD)
        assert resp.status_code in (401, 403)

    def test_batch_rejects_empty(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters/batch", json={"requests": []})
        assert resp.status_code == 422

    def test_batch_rejects_more_than_10(self, client, bypass_auth):
        payload = {"requests": [VALID_LETTER_PAYLOAD] * 11}
        resp = client.post("/v1/disputes/letters/batch", json=payload)
        assert resp.status_code == 422

    def test_batch_each_has_letter_fields(self, client, bypass_auth):
        resp = client.post("/v1/disputes/letters/batch", json=self.BATCH_PAYLOAD)
        data = resp.json()
        for letter in data["letters"]:
            assert "subject" in letter
            assert "body" in letter
            assert "legal_citations" in letter


# ---------------------------------------------------------------------------
# Cycle 4: All letter types via endpoint
# ---------------------------------------------------------------------------


class TestAllLetterTypesEndpoint:
    @pytest.mark.parametrize(
        "letter_type",
        ["validation", "inaccuracy", "completeness", "obsolete_item", "identity_theft"],
    )
    def test_each_type_generates(self, client, bypass_auth, letter_type):
        payload = {**VALID_LETTER_PAYLOAD, "letter_type": letter_type}
        resp = client.post("/v1/disputes/letters", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["letter_type"] == letter_type
        assert data["body"]


# ---------------------------------------------------------------------------
# Cycle 5: Optional fields
# ---------------------------------------------------------------------------


class TestLetterOptionalFields:
    def test_account_number_in_body(self, client, bypass_auth):
        payload = {**VALID_LETTER_PAYLOAD, "account_number": "ACCT-99999"}
        resp = client.post("/v1/disputes/letters", json=payload)
        data = resp.json()
        assert "ACCT-99999" in data["body"]

    def test_specific_variation(self, client, bypass_auth):
        payload = {**VALID_LETTER_PAYLOAD, "variation": 2}
        resp = client.post("/v1/disputes/letters", json=payload)
        assert resp.status_code == 200
