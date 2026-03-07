"""Tests for Baby INERTIA liberation endpoints."""

from __future__ import annotations

from modules.credit.tests.conftest import VALID_ASSESS_PAYLOAD


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_LIBERATE_PAYLOAD = {"profile": VALID_ASSESS_PAYLOAD}

_LIBERATE_WITH_CONTEXT = {
    "profile": VALID_ASSESS_PAYLOAD,
    "target_industries": ["healthcare_cna"],
    "denial_context": {"reason": "credit", "lender": "Big Bank"},
    "bureau_reports": {
        "equifax": {"score": 740},
        "experian": {"score": 735},
    },
}

_PHANTOM_TAX_PAYLOAD = {"profile": VALID_ASSESS_PAYLOAD}

_COMPARE_BUREAUS_PAYLOAD = {
    "profile": VALID_ASSESS_PAYLOAD,
    "bureau_reports": {
        "equifax": {"score": 740},
        "experian": {"score": 735},
    },
}


# ---------------------------------------------------------------------------
# Cycle 1: POST /v1/liberate
# ---------------------------------------------------------------------------


class TestLiberateEndpoint:
    """Test POST /v1/liberate — full liberation plan."""

    def test_liberate_returns_200(self, client, bypass_auth):
        resp = client.post("/v1/liberate", json=_LIBERATE_PAYLOAD)
        assert resp.status_code == 200

    def test_liberate_has_liberation_plan(self, client, bypass_auth):
        resp = client.post("/v1/liberate", json=_LIBERATE_PAYLOAD)
        data = resp.json()
        assert "liberation_plan" in data

    def test_liberate_has_reasoning_chain(self, client, bypass_auth):
        resp = client.post("/v1/liberate", json=_LIBERATE_PAYLOAD)
        data = resp.json()
        assert "reasoning_chain" in data
        assert isinstance(data["reasoning_chain"], list)

    def test_liberate_requires_auth(self, client):
        resp = client.post("/v1/liberate", json=_LIBERATE_PAYLOAD)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cycle 2: POST /v1/phantom-tax
# ---------------------------------------------------------------------------


class TestPhantomTaxEndpoint:
    """Test POST /v1/phantom-tax — poverty tax receipt."""

    def test_phantom_tax_200(self, client, bypass_auth):
        resp = client.post("/v1/phantom-tax", json=_PHANTOM_TAX_PAYLOAD)
        assert resp.status_code == 200

    def test_phantom_tax_has_total(self, client, bypass_auth):
        resp = client.post("/v1/phantom-tax", json=_PHANTOM_TAX_PAYLOAD)
        data = resp.json()
        assert "total_annual_tax" in data

    def test_phantom_tax_requires_auth(self, client):
        resp = client.post("/v1/phantom-tax", json=_PHANTOM_TAX_PAYLOAD)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cycle 3: POST /v1/compare-bureaus
# ---------------------------------------------------------------------------


class TestCompareBureausEndpoint:
    """Test POST /v1/compare-bureaus — cross-bureau scan."""

    def test_compare_bureaus_200(self, client, bypass_auth):
        resp = client.post("/v1/compare-bureaus", json=_COMPARE_BUREAUS_PAYLOAD)
        assert resp.status_code == 200

    def test_compare_bureaus_requires_bureau_reports(self, client, bypass_auth):
        resp = client.post(
            "/v1/compare-bureaus",
            json={"profile": VALID_ASSESS_PAYLOAD},
        )
        assert resp.status_code == 422

    def test_compare_bureaus_requires_auth(self, client):
        resp = client.post("/v1/compare-bureaus", json=_COMPARE_BUREAUS_PAYLOAD)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cycle 4: POST /v1/liberate/print
# ---------------------------------------------------------------------------


class TestLiberatePrintEndpoint:
    """Test POST /v1/liberate/print — HTML export."""

    def test_print_returns_html(self, client, bypass_auth):
        resp = client.post("/v1/liberate/print", json=_LIBERATE_PAYLOAD)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_print_contains_liberation_plan(self, client, bypass_auth):
        resp = client.post("/v1/liberate/print", json=_LIBERATE_PAYLOAD)
        assert "Liberation Plan" in resp.text

    def test_print_requires_auth(self, client):
        resp = client.post("/v1/liberate/print", json=_LIBERATE_PAYLOAD)
        assert resp.status_code in (401, 403)
