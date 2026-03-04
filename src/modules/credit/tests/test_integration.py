"""Integration tests + coverage gap tests."""

from modules.credit.types import (
    BarrierSeverity,
    CreditAssessmentResult,
)


class TestEndToEndAssessment:
    """Feed each fixture through the full pipeline."""

    def test_good_credit_full_pipeline(self, good_credit_profile):
        from modules.credit.assessment import CreditAssessmentService

        result = CreditAssessmentService().assess(good_credit_profile)
        assert isinstance(result, CreditAssessmentResult)
        assert result.barrier_severity == BarrierSeverity.LOW
        assert result.readiness.score >= 70
        assert len(result.eligibility) == 8
        assert len(result.dispute_pathway.steps) == 0

    def test_poor_credit_full_pipeline(self, poor_credit_profile):
        from modules.credit.assessment import CreditAssessmentService

        result = CreditAssessmentService().assess(poor_credit_profile)
        assert result.barrier_severity == BarrierSeverity.HIGH
        assert result.readiness.score < 40
        assert len(result.dispute_pathway.steps) >= 3
        assert len(result.dispute_pathway.statutes_cited) > 0
        blocked = [i for i in result.eligibility if i.status == "blocked"]
        assert len(blocked) >= 3

    def test_fair_credit_full_pipeline(self, fair_credit_profile):
        from modules.credit.assessment import CreditAssessmentService

        result = CreditAssessmentService().assess(fair_credit_profile)
        assert result.barrier_severity == BarrierSeverity.MEDIUM
        assert 0 <= result.readiness.score <= 100
        assert len(result.thresholds) == 4
        assert len(result.dispute_pathway.steps) >= 1

    def test_thin_file_full_pipeline(self, thin_file_profile):
        from modules.credit.assessment import CreditAssessmentService

        result = CreditAssessmentService().assess(thin_file_profile)
        assert isinstance(result, CreditAssessmentResult)
        assert result.readiness.fico_score == 620
        assert len(result.dispute_pathway.steps) == 0


class TestCoverageGaps:
    """Tests targeting uncovered branches."""

    def test_utilization_at_100_percent(self):
        """Cover the return -30 fallback in _bracket_impact."""
        from modules.credit.assessment import get_utilization_impact

        result = get_utilization_impact(100.0, 5.0)
        assert result["low"] > 0
        assert result["high"] > 0

    def test_classify_wrong_balance(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("wrong_balance_on_card") == "wrong_balance"

    def test_classify_obsolete_item(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("obsolete_item_7yr") == "obsolete_item"

    def test_classify_unauthorized_inquiry(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert (
            gen._classify_issue_type("unauthorized_inquiry") == "unauthorized_inquiry"
        )

    def test_classify_dofd_error(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("dofd_error_on_account") == "dofd_error"

    def test_get_score_band_fallback(self):
        """Cover the fallback return in get_score_band for out-of-range scores."""
        from modules.credit.assessment import get_score_band
        from modules.credit.types import ScoreBand

        assert get_score_band(0) == ScoreBand.VERY_POOR

    def test_medium_barrier_moderate_utilization(self):
        """Cover MEDIUM barrier with moderate utilization (50-75%)."""
        from modules.credit.assessment import CreditAssessmentService
        from modules.credit.types import AccountSummary, CreditProfile, ScoreBand

        profile = CreditProfile(
            current_score=680,
            score_band=ScoreBand.FAIR,
            overall_utilization=60.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=95.0,
            average_account_age_months=36,
        )
        svc = CreditAssessmentService()
        severity, barriers = svc._compute_barrier_severity(profile)
        from modules.credit.types import BarrierSeverity

        assert severity == BarrierSeverity.MEDIUM
        descriptions = [b.description for b in barriers]
        assert any("above 50%" in d for d in descriptions)

    def test_classifier_unknown_issue_logs_warning(self):
        """Cover logger.warning for unknown issue type fallback."""
        from unittest.mock import patch
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        with patch("modules.credit.dispute_pathway.logger") as mock_logger:
            result = gen._classify_issue_type("some_unknown_thing")
            assert result == "late_payment"
            mock_logger.warning.assert_called_once()
