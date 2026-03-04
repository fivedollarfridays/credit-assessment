"""Tests for credit assessment service — TDD: written before implementation."""

from modules.credit.assessment import (
    CreditAssessmentService,
    get_score_band,
    get_utilization_impact,
)
from modules.credit.types import (
    AccountSummary,
    BarrierSeverity,
    CreditAssessmentResult,
    CreditProfile,
    CreditReadiness,
    ScoreBand,
    ThresholdEstimate,
)


class TestGetScoreBand:
    """Test score band classification helper."""

    def test_excellent(self):
        assert get_score_band(750) == "excellent"
        assert get_score_band(850) == "excellent"

    def test_good(self):
        assert get_score_band(700) == "good"
        assert get_score_band(749) == "good"

    def test_fair(self):
        assert get_score_band(650) == "fair"
        assert get_score_band(699) == "fair"

    def test_poor(self):
        assert get_score_band(600) == "poor"
        assert get_score_band(649) == "poor"

    def test_very_poor(self):
        assert get_score_band(300) == "very_poor"
        assert get_score_band(599) == "very_poor"


class TestGetUtilizationImpact:
    """Test utilization impact calculation."""

    def test_low_to_lower(self):
        result = get_utilization_impact(20.0, 5.0)
        assert result["low"] >= 0
        assert result["high"] > result["low"]

    def test_high_to_low(self):
        result = get_utilization_impact(80.0, 10.0)
        assert result["low"] > 0
        assert result["high"] > 0

    def test_same_bracket_returns_zero(self):
        result = get_utilization_impact(15.0, 15.0)
        assert result["low"] == 0
        assert result["high"] == 0

    def test_worse_utilization_negative(self):
        result = get_utilization_impact(10.0, 80.0)
        assert result["low"] <= 0


class TestComputeBarrierSeverity:
    """Test barrier severity classification."""

    def test_high_severity_collections(self, poor_credit_profile):
        svc = CreditAssessmentService()
        severity, barriers = svc._compute_barrier_severity(poor_credit_profile)
        assert severity == BarrierSeverity.HIGH

    def test_high_severity_low_score(self):
        profile = CreditProfile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=90.0,
            average_account_age_months=24,
        )
        svc = CreditAssessmentService()
        severity, _ = svc._compute_barrier_severity(profile)
        assert severity == BarrierSeverity.HIGH

    def test_high_severity_high_utilization(self):
        profile = CreditProfile(
            current_score=680,
            score_band=ScoreBand.FAIR,
            overall_utilization=80.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=95.0,
            average_account_age_months=36,
        )
        svc = CreditAssessmentService()
        severity, _ = svc._compute_barrier_severity(profile)
        assert severity == BarrierSeverity.HIGH

    def test_medium_severity_negatives(self, fair_credit_profile):
        svc = CreditAssessmentService()
        severity, barriers = svc._compute_barrier_severity(fair_credit_profile)
        assert severity == BarrierSeverity.MEDIUM

    def test_low_severity_good_credit(self, good_credit_profile):
        svc = CreditAssessmentService()
        severity, barriers = svc._compute_barrier_severity(good_credit_profile)
        assert severity == BarrierSeverity.LOW

    def test_barriers_list_populated_for_high(self, poor_credit_profile):
        svc = CreditAssessmentService()
        _, barriers = svc._compute_barrier_severity(poor_credit_profile)
        assert len(barriers) > 0
        assert all(b.severity == BarrierSeverity.HIGH for b in barriers)

    def test_barriers_empty_for_low(self, good_credit_profile):
        svc = CreditAssessmentService()
        _, barriers = svc._compute_barrier_severity(good_credit_profile)
        assert len(barriers) == 0


class TestComputeReadinessScore:
    """Test readiness score normalization."""

    def test_good_credit_high_readiness(self, good_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(good_credit_profile)
        assert isinstance(readiness, CreditReadiness)
        assert readiness.score >= 70
        assert readiness.score <= 100

    def test_poor_credit_low_readiness(self, poor_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(poor_credit_profile)
        assert readiness.score < 40

    def test_readiness_score_range(self, fair_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(fair_credit_profile)
        assert 0 <= readiness.score <= 100

    def test_readiness_has_factors(self, good_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(good_credit_profile)
        assert "payment_history" in readiness.factors
        assert "utilization" in readiness.factors

    def test_readiness_fico_matches(self, good_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(good_credit_profile)
        assert readiness.fico_score == 740

    def test_readiness_score_band(self, good_credit_profile):
        svc = CreditAssessmentService()
        readiness = svc._compute_readiness_score(good_credit_profile)
        assert readiness.score_band == "good"


class TestEstimateDaysToThresholds:
    """Test threshold estimation."""

    def test_already_met_threshold(self, good_credit_profile):
        svc = CreditAssessmentService()
        thresholds = svc._estimate_days_to_thresholds(good_credit_profile)
        fair_threshold = next(
            (t for t in thresholds if t.threshold_name == "Fair Credit"), None
        )
        assert fair_threshold is not None
        assert fair_threshold.already_met is True
        assert fair_threshold.estimated_days == 0

    def test_not_met_threshold(self, poor_credit_profile):
        svc = CreditAssessmentService()
        thresholds = svc._estimate_days_to_thresholds(poor_credit_profile)
        good_threshold = next(
            (t for t in thresholds if t.threshold_name == "Good Credit"), None
        )
        assert good_threshold is not None
        assert good_threshold.already_met is False
        assert good_threshold.estimated_days is not None
        assert good_threshold.estimated_days > 0

    def test_returns_multiple_thresholds(self, fair_credit_profile):
        svc = CreditAssessmentService()
        thresholds = svc._estimate_days_to_thresholds(fair_credit_profile)
        assert len(thresholds) >= 3

    def test_threshold_has_required_fields(self, fair_credit_profile):
        svc = CreditAssessmentService()
        thresholds = svc._estimate_days_to_thresholds(fair_credit_profile)
        for t in thresholds:
            assert isinstance(t, ThresholdEstimate)
            assert t.threshold_name
            assert t.threshold_score > 0


class TestComputeEligibility:
    """Test product eligibility computation."""

    def test_good_credit_eligible_for_most(self, good_credit_profile):
        svc = CreditAssessmentService()
        items = svc._compute_eligibility(good_credit_profile)
        eligible = [i for i in items if i.status == "eligible"]
        assert len(eligible) >= 5

    def test_poor_credit_limited_eligibility(self, poor_credit_profile):
        svc = CreditAssessmentService()
        items = svc._compute_eligibility(poor_credit_profile)
        blocked = [i for i in items if i.status == "blocked"]
        assert len(blocked) >= 3

    def test_eligibility_gap_points(self, fair_credit_profile):
        svc = CreditAssessmentService()
        items = svc._compute_eligibility(fair_credit_profile)
        blocked = [i for i in items if i.status == "blocked"]
        for item in blocked:
            assert item.gap_points is not None
            assert item.gap_points > 0

    def test_eligibility_has_all_products(self, good_credit_profile):
        svc = CreditAssessmentService()
        items = svc._compute_eligibility(good_credit_profile)
        assert len(items) == 8  # matches PRODUCT_THRESHOLDS count

    def test_secured_card_always_eligible(self, poor_credit_profile):
        svc = CreditAssessmentService()
        items = svc._compute_eligibility(poor_credit_profile)
        secured = next(
            (i for i in items if i.product_name == "Secured Credit Card"), None
        )
        assert secured is not None
        assert secured.status == "eligible"


class TestAssess:
    """Test the full orchestration method."""

    def test_returns_assessment_result(self, good_credit_profile):
        svc = CreditAssessmentService()
        result = svc.assess(good_credit_profile)
        assert isinstance(result, CreditAssessmentResult)

    def test_all_five_outputs_populated(self, fair_credit_profile):
        svc = CreditAssessmentService()
        result = svc.assess(fair_credit_profile)
        assert result.barrier_severity is not None
        assert result.readiness is not None
        assert len(result.thresholds) > 0
        assert result.dispute_pathway is not None
        assert len(result.eligibility) > 0

    def test_poor_credit_high_severity(self, poor_credit_profile):
        svc = CreditAssessmentService()
        result = svc.assess(poor_credit_profile)
        assert result.barrier_severity == BarrierSeverity.HIGH
        assert result.readiness.score < 40

    def test_good_credit_low_severity(self, good_credit_profile):
        svc = CreditAssessmentService()
        result = svc.assess(good_credit_profile)
        assert result.barrier_severity == BarrierSeverity.LOW
        assert result.readiness.score >= 70

    def test_has_disclaimer(self, good_credit_profile):
        svc = CreditAssessmentService()
        result = svc.assess(good_credit_profile)
        assert "educational" in result.disclaimer.lower()

    def test_thin_file_profile(self, thin_file_profile):
        svc = CreditAssessmentService()
        result = svc.assess(thin_file_profile)
        assert isinstance(result, CreditAssessmentResult)
        assert result.readiness.fico_score == 620
