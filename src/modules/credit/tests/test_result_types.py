"""Tests for credit assessment result and compound types."""

from modules.credit.types import (
    BarrierSeverity,
    CreditAssessmentResult,
    CreditBarrier,
    CreditProfile,
    CreditReadiness,
    DisputePathway,
    EligibilityItem,
    ScoreBand,
    ThresholdEstimate,
)


class TestThresholdEstimate:
    """Tests for ThresholdEstimate model."""

    def test_validates_with_required_fields(self) -> None:
        estimate = ThresholdEstimate(
            threshold_name="FHA Mortgage",
            threshold_score=580,
        )
        assert estimate.threshold_name == "FHA Mortgage"
        assert estimate.threshold_score == 580
        assert estimate.estimated_days is None
        assert estimate.already_met is False
        assert estimate.confidence == "medium"

    def test_validates_already_met(self) -> None:
        estimate = ThresholdEstimate(
            threshold_name="Secured Credit Card",
            threshold_score=300,
            already_met=True,
            estimated_days=0,
            confidence="high",
        )
        assert estimate.already_met is True
        assert estimate.confidence == "high"


class TestEligibilityItem:
    """Tests for EligibilityItem model."""

    def test_validates_with_required_fields(self) -> None:
        item = EligibilityItem(
            product_name="FHA Mortgage",
            category="mortgage",
            required_score=580,
            status="eligible",
        )
        assert item.product_name == "FHA Mortgage"
        assert item.category == "mortgage"
        assert item.required_score == 580
        assert item.status == "eligible"
        assert item.gap_points is None
        assert item.estimated_days_to_eligible is None
        assert item.blocking_factors == []

    def test_validates_blocked_item(self) -> None:
        item = EligibilityItem(
            product_name="Rewards Credit Card",
            category="credit_card",
            required_score=700,
            status="blocked",
            gap_points=50,
            estimated_days_to_eligible=180,
            blocking_factors=["low_score", "high_utilization"],
        )
        assert item.status == "blocked"
        assert item.gap_points == 50
        assert len(item.blocking_factors) == 2


class TestCreditAssessmentResult:
    """Tests for CreditAssessmentResult model."""

    def test_has_all_five_output_fields(self) -> None:
        readiness = CreditReadiness(score=70, fico_score=650, score_band="fair")
        pathway = DisputePathway()
        result = CreditAssessmentResult(
            barrier_severity=BarrierSeverity.MEDIUM,
            readiness=readiness,
            dispute_pathway=pathway,
        )
        assert result.barrier_severity == BarrierSeverity.MEDIUM
        assert result.barrier_details == []
        assert result.readiness.score == 70
        assert result.thresholds == []
        assert result.dispute_pathway == pathway
        assert result.eligibility == []

    def test_has_default_disclaimer(self) -> None:
        readiness = CreditReadiness(score=50, fico_score=600, score_band="poor")
        result = CreditAssessmentResult(
            barrier_severity=BarrierSeverity.HIGH,
            readiness=readiness,
            dispute_pathway=DisputePathway(),
        )
        assert result.disclaimer == "All estimates are for educational purposes only."

    def test_validates_with_full_data(self) -> None:
        readiness = CreditReadiness(score=85, fico_score=740, score_band="excellent")
        barrier = CreditBarrier(
            severity=BarrierSeverity.LOW,
            description="Minor issue",
        )
        threshold = ThresholdEstimate(
            threshold_name="Prime Auto",
            threshold_score=700,
            already_met=True,
        )
        eligibility = EligibilityItem(
            product_name="Rewards Card",
            category="credit_card",
            required_score=700,
            status="eligible",
        )
        result = CreditAssessmentResult(
            barrier_severity=BarrierSeverity.LOW,
            barrier_details=[barrier],
            readiness=readiness,
            thresholds=[threshold],
            dispute_pathway=DisputePathway(),
            eligibility=[eligibility],
        )
        assert len(result.barrier_details) == 1
        assert len(result.thresholds) == 1
        assert len(result.eligibility) == 1


class TestFixtures:
    """Tests that conftest fixtures produce valid profiles."""

    def test_good_credit_profile(self, good_credit_profile: CreditProfile) -> None:
        assert good_credit_profile.current_score == 740
        assert good_credit_profile.score_band == ScoreBand.GOOD
        assert good_credit_profile.overall_utilization == 20.0
        assert good_credit_profile.account_summary.negative_accounts == 0

    def test_poor_credit_profile(self, poor_credit_profile: CreditProfile) -> None:
        assert poor_credit_profile.current_score == 520
        assert poor_credit_profile.score_band == ScoreBand.VERY_POOR
        assert poor_credit_profile.overall_utilization == 85.0
        assert poor_credit_profile.account_summary.collection_accounts == 3
        assert len(poor_credit_profile.negative_items) == 3

    def test_fair_credit_profile(self, fair_credit_profile: CreditProfile) -> None:
        assert fair_credit_profile.current_score == 650
        assert fair_credit_profile.score_band == ScoreBand.FAIR
        assert fair_credit_profile.overall_utilization == 45.0
        assert fair_credit_profile.account_summary.negative_accounts == 1

    def test_thin_file_profile(self, thin_file_profile: CreditProfile) -> None:
        assert thin_file_profile.current_score == 620
        assert thin_file_profile.score_band == ScoreBand.POOR
        assert thin_file_profile.account_summary.total_accounts == 2
        assert thin_file_profile.negative_items == []
