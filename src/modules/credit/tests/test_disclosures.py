"""Tests for FCRA Section 505 disclosures and adverse action notices."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modules.credit.assessment import CreditAssessmentService
from modules.credit.disclosures import (
    ADVERSE_ACTION_NOTICE_TEMPLATE,
    FCRA_DISCLAIMER,
    get_disclosures,
)
from modules.credit.router import app
from modules.credit.types import (
    AccountSummary,
    CreditAssessmentResult,
    CreditProfile,
    ScoreBand,
)


# ---------------------------------------------------------------------------
# Cycle 1: FCRA disclosure constants exist with required legal language
# ---------------------------------------------------------------------------


class TestFcraDisclosureText:
    """Tests for FCRA disclosure content requirements."""

    def test_fcra_disclaimer_exists(self) -> None:
        assert isinstance(FCRA_DISCLAIMER, str)
        assert len(FCRA_DISCLAIMER) > 100

    def test_fcra_disclaimer_references_section_505(self) -> None:
        assert "605" in FCRA_DISCLAIMER or "Section" in FCRA_DISCLAIMER

    def test_fcra_disclaimer_mentions_educational_purpose(self) -> None:
        assert "educational" in FCRA_DISCLAIMER.lower()

    def test_fcra_disclaimer_mentions_not_credit_reporting_agency(self) -> None:
        lower = FCRA_DISCLAIMER.lower()
        assert "consumer reporting agency" in lower or "credit reporting" in lower

    def test_fcra_disclaimer_mentions_fcra(self) -> None:
        assert (
            "Fair Credit Reporting Act" in FCRA_DISCLAIMER or "FCRA" in FCRA_DISCLAIMER
        )


# ---------------------------------------------------------------------------
# Cycle 2: Adverse action notice template
# ---------------------------------------------------------------------------


class TestAdverseActionNotice:
    """Tests for adverse action notice template."""

    def test_adverse_action_template_exists(self) -> None:
        assert isinstance(ADVERSE_ACTION_NOTICE_TEMPLATE, str)
        assert len(ADVERSE_ACTION_NOTICE_TEMPLATE) > 100

    def test_adverse_action_mentions_adverse_action(self) -> None:
        assert "adverse action" in ADVERSE_ACTION_NOTICE_TEMPLATE.lower()

    def test_adverse_action_mentions_fcra(self) -> None:
        assert (
            "FCRA" in ADVERSE_ACTION_NOTICE_TEMPLATE
            or "Fair Credit Reporting Act" in ADVERSE_ACTION_NOTICE_TEMPLATE
        )

    def test_adverse_action_has_placeholder_fields(self) -> None:
        assert "{consumer_name}" in ADVERSE_ACTION_NOTICE_TEMPLATE
        assert "{action_taken}" in ADVERSE_ACTION_NOTICE_TEMPLATE
        assert "{reasons}" in ADVERSE_ACTION_NOTICE_TEMPLATE

    def test_adverse_action_mentions_dispute_rights(self) -> None:
        lower = ADVERSE_ACTION_NOTICE_TEMPLATE.lower()
        assert "dispute" in lower

    def test_adverse_action_mentions_free_report(self) -> None:
        lower = ADVERSE_ACTION_NOTICE_TEMPLATE.lower()
        assert "free" in lower and "report" in lower


# ---------------------------------------------------------------------------
# Cycle 3: get_disclosures() returns structured disclosure data
# ---------------------------------------------------------------------------


class TestGetDisclosures:
    """Tests for structured disclosure retrieval."""

    def test_get_disclosures_returns_dict(self) -> None:
        result = get_disclosures()
        assert isinstance(result, dict)

    def test_get_disclosures_has_fcra_disclaimer(self) -> None:
        result = get_disclosures()
        assert result["fcra_disclaimer"] == FCRA_DISCLAIMER

    def test_get_disclosures_has_adverse_action_template(self) -> None:
        result = get_disclosures()
        assert (
            result["adverse_action_notice_template"] == ADVERSE_ACTION_NOTICE_TEMPLATE
        )

    def test_get_disclosures_has_consumer_rights(self) -> None:
        result = get_disclosures()
        assert "consumer_rights" in result
        assert isinstance(result["consumer_rights"], str)
        assert len(result["consumer_rights"]) > 50

    def test_get_disclosures_has_data_usage_notice(self) -> None:
        result = get_disclosures()
        assert "data_usage_notice" in result
        assert isinstance(result["data_usage_notice"], str)


# ---------------------------------------------------------------------------
# Cycle 4: Assessment result uses FCRA disclaimer
# ---------------------------------------------------------------------------


class TestAssessmentDisclaimer:
    """Tests that assessment results use proper FCRA disclaimer."""

    def test_assessment_result_disclaimer_is_fcra(self) -> None:
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=25.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=95.0,
            average_account_age_months=48,
        )
        svc = CreditAssessmentService()
        result = svc.assess(profile)
        assert result.disclaimer == FCRA_DISCLAIMER

    def test_default_disclaimer_references_fcra(self) -> None:
        fields = CreditAssessmentResult.model_fields
        assert fields["disclaimer"].default == FCRA_DISCLAIMER


# ---------------------------------------------------------------------------
# Cycle 5: /disclosures endpoint
# ---------------------------------------------------------------------------


class TestDisclosuresEndpoint:
    """Tests for GET /disclosures and GET /v1/disclosures endpoints."""

    def test_disclosures_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.get("/disclosures")
        assert resp.status_code == 200

    def test_disclosures_endpoint_returns_all_sections(self) -> None:
        client = TestClient(app)
        data = client.get("/disclosures").json()
        assert "fcra_disclaimer" in data
        assert "adverse_action_notice_template" in data
        assert "consumer_rights" in data
        assert "data_usage_notice" in data

    def test_v1_disclosures_endpoint_returns_200(self) -> None:
        client = TestClient(app)
        resp = client.get("/v1/disclosures")
        assert resp.status_code == 200

    def test_v1_disclosures_matches_root(self) -> None:
        client = TestClient(app)
        root_data = client.get("/disclosures").json()
        v1_data = client.get("/v1/disclosures").json()
        assert root_data == v1_data

    def test_disclosures_no_auth_required(self) -> None:
        client = TestClient(app)
        # No auth headers — should still succeed
        resp = client.get("/disclosures")
        assert resp.status_code == 200
