"""Tests for credit assessment types module."""

import pytest
from pydantic import ValidationError

from modules.credit.types import (
    PRODUCT_THRESHOLDS,
    SCORE_BANDS,
    SCORE_WEIGHTS,
    AccountSummary,
    ActionPriority,
    BarrierSeverity,
    CreditAssessmentResult,
    CreditBarrier,
    CreditProfile,
    CreditReadiness,
    DisputePathway,
    DisputeStep,
    EligibilityItem,
    LegalTheory,
    ScoreBand,
    ScoreImpact,
    ThresholdEstimate,
)


# --- Cycle 1: Enum Tests ---


class TestBarrierSeverity:
    """Tests for BarrierSeverity enum."""

    def test_has_high_value(self) -> None:
        assert BarrierSeverity.HIGH == "high"

    def test_has_medium_value(self) -> None:
        assert BarrierSeverity.MEDIUM == "medium"

    def test_has_low_value(self) -> None:
        assert BarrierSeverity.LOW == "low"

    def test_has_exactly_three_members(self) -> None:
        assert len(BarrierSeverity) == 3


class TestScoreBand:
    """Tests for ScoreBand enum."""

    def test_has_excellent(self) -> None:
        assert ScoreBand.EXCELLENT == "excellent"

    def test_has_good(self) -> None:
        assert ScoreBand.GOOD == "good"

    def test_has_fair(self) -> None:
        assert ScoreBand.FAIR == "fair"

    def test_has_poor(self) -> None:
        assert ScoreBand.POOR == "poor"

    def test_has_very_poor(self) -> None:
        assert ScoreBand.VERY_POOR == "very_poor"

    def test_has_exactly_five_members(self) -> None:
        assert len(ScoreBand) == 5


class TestLegalTheory:
    """Tests for LegalTheory enum."""

    def test_has_fcra_607b(self) -> None:
        assert LegalTheory.FCRA_607B == "fcra_607b_accuracy"

    def test_has_fcra_611(self) -> None:
        assert LegalTheory.FCRA_611 == "fcra_611_reinvestigation"

    def test_has_fcra_605b(self) -> None:
        assert LegalTheory.FCRA_605B == "fcra_605b_identity_theft"

    def test_has_fcra_623(self) -> None:
        assert LegalTheory.FCRA_623 == "fcra_623_furnisher_duties"

    def test_has_fdcpa_809(self) -> None:
        assert LegalTheory.FDCPA_809 == "fdcpa_809_validation"

    def test_has_fdcpa_807(self) -> None:
        assert LegalTheory.FDCPA_807 == "fdcpa_807_false_representation"

    def test_has_metro2_dofd(self) -> None:
        assert LegalTheory.METRO2_DOFD == "metro2_dofd_violation"

    def test_has_metro2_logic(self) -> None:
        assert LegalTheory.METRO2_LOGIC == "metro2_logical_inconsistency"

    def test_has_state_law(self) -> None:
        assert LegalTheory.STATE_LAW == "state_law_violation"

    def test_has_exactly_nine_members(self) -> None:
        assert len(LegalTheory) == 9


# --- Cycle 2: AccountSummary and CreditProfile Tests ---


class TestAccountSummary:
    """Tests for AccountSummary model."""

    def test_creates_with_defaults(self) -> None:
        summary = AccountSummary(total_accounts=5, open_accounts=3)
        assert summary.total_accounts == 5
        assert summary.open_accounts == 3
        assert summary.closed_accounts == 0
        assert summary.negative_accounts == 0
        assert summary.collection_accounts == 0
        assert summary.total_balance == 0.0
        assert summary.total_credit_limit == 0.0
        assert summary.monthly_payments == 0.0

    def test_creates_with_all_fields(self) -> None:
        summary = AccountSummary(
            total_accounts=10,
            open_accounts=7,
            closed_accounts=3,
            negative_accounts=2,
            collection_accounts=1,
            total_balance=15000.0,
            total_credit_limit=50000.0,
            monthly_payments=500.0,
        )
        assert summary.negative_accounts == 2
        assert summary.total_balance == 15000.0


class TestCreditProfile:
    """Tests for CreditProfile model."""

    def test_valid_score_at_lower_bound(self) -> None:
        profile = CreditProfile(
            current_score=300,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=50.0,
            account_summary=AccountSummary(total_accounts=1, open_accounts=1),
            payment_history_pct=80.0,
            average_account_age_months=12,
            negative_items=[],
        )
        assert profile.current_score == 300

    def test_valid_score_at_upper_bound(self) -> None:
        profile = CreditProfile(
            current_score=850,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=5.0,
            account_summary=AccountSummary(total_accounts=10, open_accounts=8),
            payment_history_pct=100.0,
            average_account_age_months=120,
            negative_items=[],
        )
        assert profile.current_score == 850

    def test_rejects_score_below_300(self) -> None:
        with pytest.raises(ValidationError):
            CreditProfile(
                current_score=299,
                score_band=ScoreBand.VERY_POOR,
                overall_utilization=50.0,
                account_summary=AccountSummary(
                    total_accounts=1, open_accounts=1
                ),
                payment_history_pct=80.0,
                average_account_age_months=12,
                negative_items=[],
            )

    def test_rejects_score_above_850(self) -> None:
        with pytest.raises(ValidationError):
            CreditProfile(
                current_score=851,
                score_band=ScoreBand.EXCELLENT,
                overall_utilization=5.0,
                account_summary=AccountSummary(
                    total_accounts=10, open_accounts=8
                ),
                payment_history_pct=100.0,
                average_account_age_months=120,
                negative_items=[],
            )

    def test_has_all_required_fields(self) -> None:
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=4),
            payment_history_pct=95.0,
            average_account_age_months=36,
            negative_items=[],
        )
        assert profile.current_score == 700
        assert profile.score_band == ScoreBand.GOOD
        assert profile.overall_utilization == 30.0
        assert profile.account_summary.total_accounts == 5
        assert profile.payment_history_pct == 95.0
        assert profile.average_account_age_months == 36
        assert profile.negative_items == []

    def test_negative_items_default_empty(self) -> None:
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=4),
            payment_history_pct=95.0,
            average_account_age_months=36,
        )
        assert profile.negative_items == []


# --- Cycle 3: ScoreImpact Tests ---


class TestScoreImpact:
    """Tests for ScoreImpact model."""

    def test_from_range_classmethod(self) -> None:
        impact = ScoreImpact.from_range(10, 30)
        assert impact.min_points == 10
        assert impact.max_points == 30
        assert impact.expected_points == 20

    def test_from_range_single_point(self) -> None:
        impact = ScoreImpact.from_range(5, 5)
        assert impact.expected_points == 5

    def test_creates_with_explicit_values(self) -> None:
        impact = ScoreImpact(
            min_points=5, max_points=15, expected_points=12
        )
        assert impact.min_points == 5
        assert impact.max_points == 15
        assert impact.expected_points == 12


# --- Cycle 4: CreditBarrier and CreditReadiness Tests ---


class TestCreditBarrier:
    """Tests for CreditBarrier model."""

    def test_validates_with_required_fields(self) -> None:
        barrier = CreditBarrier(
            severity=BarrierSeverity.HIGH,
            description="Multiple collections on file",
        )
        assert barrier.severity == BarrierSeverity.HIGH
        assert barrier.description == "Multiple collections on file"
        assert barrier.affected_accounts == []
        assert barrier.estimated_resolution_days == 0

    def test_validates_with_all_fields(self) -> None:
        barrier = CreditBarrier(
            severity=BarrierSeverity.MEDIUM,
            description="High utilization",
            affected_accounts=["acct-001", "acct-002"],
            estimated_resolution_days=60,
        )
        assert len(barrier.affected_accounts) == 2
        assert barrier.estimated_resolution_days == 60


class TestCreditReadiness:
    """Tests for CreditReadiness model."""

    def test_validates_with_required_fields(self) -> None:
        readiness = CreditReadiness(
            score=75,
            fico_score=700,
            score_band="good",
        )
        assert readiness.score == 75
        assert readiness.fico_score == 700
        assert readiness.score_band == "good"
        assert readiness.factors == {}

    def test_validates_with_factors(self) -> None:
        readiness = CreditReadiness(
            score=85,
            fico_score=740,
            score_band="excellent",
            factors={"payment_history": 95.0, "utilization": 80.0},
        )
        assert readiness.factors["payment_history"] == 95.0

    def test_rejects_score_above_100(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(
                score=101,
                fico_score=700,
                score_band="good",
            )

    def test_rejects_score_below_0(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(
                score=-1,
                fico_score=700,
                score_band="good",
            )

    def test_rejects_fico_below_300(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(
                score=50,
                fico_score=299,
                score_band="very_poor",
            )

    def test_rejects_fico_above_850(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(
                score=50,
                fico_score=851,
                score_band="excellent",
            )


# --- Cycle 5: DisputeStep and DisputePathway Tests ---


class TestDisputeStep:
    """Tests for DisputeStep model."""

    def test_validates_with_required_fields(self) -> None:
        step = DisputeStep(
            step_number=1,
            action="Send validation letter",
            description="Request debt validation from collector",
        )
        assert step.step_number == 1
        assert step.action == "Send validation letter"
        assert step.legal_basis is None
        assert step.estimated_days == 30
        assert step.priority == ActionPriority.MEDIUM

    def test_validates_with_all_fields(self) -> None:
        step = DisputeStep(
            step_number=2,
            action="File dispute",
            description="Dispute inaccurate reporting",
            legal_basis="FCRA 611",
            estimated_days=45,
            priority=ActionPriority.HIGH,
        )
        assert step.legal_basis == "FCRA 611"
        assert step.estimated_days == 45
        assert step.priority == ActionPriority.HIGH


class TestDisputePathway:
    """Tests for DisputePathway model."""

    def test_validates_with_defaults(self) -> None:
        pathway = DisputePathway()
        assert pathway.steps == []
        assert pathway.total_estimated_days == 0
        assert pathway.statutes_cited == []
        assert pathway.legal_theories == []

    def test_validates_with_steps(self) -> None:
        step = DisputeStep(
            step_number=1,
            action="Validate debt",
            description="Send validation letter",
        )
        pathway = DisputePathway(
            steps=[step],
            total_estimated_days=30,
            statutes_cited=["FCRA 611"],
            legal_theories=["fcra_611_reinvestigation"],
        )
        assert len(pathway.steps) == 1
        assert pathway.total_estimated_days == 30
        assert "FCRA 611" in pathway.statutes_cited


# --- Cycle 6: EligibilityItem, ThresholdEstimate, CreditAssessmentResult ---


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
        readiness = CreditReadiness(
            score=70, fico_score=650, score_band="fair"
        )
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
        readiness = CreditReadiness(
            score=50, fico_score=600, score_band="poor"
        )
        result = CreditAssessmentResult(
            barrier_severity=BarrierSeverity.HIGH,
            readiness=readiness,
            dispute_pathway=DisputePathway(),
        )
        assert (
            result.disclaimer
            == "All estimates are for educational purposes only."
        )

    def test_validates_with_full_data(self) -> None:
        readiness = CreditReadiness(
            score=85, fico_score=740, score_band="excellent"
        )
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


# --- Cycle 7: Constants Tests ---


class TestScoreWeights:
    """Tests for SCORE_WEIGHTS constant."""

    def test_weights_sum_to_one(self) -> None:
        total = sum(SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_has_expected_keys(self) -> None:
        expected = {
            "payment_history",
            "utilization",
            "credit_age",
            "credit_mix",
            "new_credit",
        }
        assert set(SCORE_WEIGHTS.keys()) == expected


class TestScoreBands:
    """Tests for SCORE_BANDS constant."""

    def test_excellent_range(self) -> None:
        assert SCORE_BANDS["excellent"]["min"] == 750
        assert SCORE_BANDS["excellent"]["max"] == 850

    def test_good_range(self) -> None:
        assert SCORE_BANDS["good"]["min"] == 700
        assert SCORE_BANDS["good"]["max"] == 749

    def test_fair_range(self) -> None:
        assert SCORE_BANDS["fair"]["min"] == 650
        assert SCORE_BANDS["fair"]["max"] == 699

    def test_poor_range(self) -> None:
        assert SCORE_BANDS["poor"]["min"] == 600
        assert SCORE_BANDS["poor"]["max"] == 649

    def test_very_poor_range(self) -> None:
        assert SCORE_BANDS["very_poor"]["min"] == 300
        assert SCORE_BANDS["very_poor"]["max"] == 599

    def test_has_all_five_bands(self) -> None:
        assert len(SCORE_BANDS) == 5


class TestProductThresholds:
    """Tests for PRODUCT_THRESHOLDS constant."""

    def test_has_fha_mortgage(self) -> None:
        assert "FHA Mortgage" in PRODUCT_THRESHOLDS
        assert PRODUCT_THRESHOLDS["FHA Mortgage"]["score"] == 580

    def test_has_conventional_mortgage(self) -> None:
        assert "Conventional Mortgage" in PRODUCT_THRESHOLDS
        assert PRODUCT_THRESHOLDS["Conventional Mortgage"]["score"] == 620

    def test_has_prime_auto_loan(self) -> None:
        assert "Prime Auto Loan" in PRODUCT_THRESHOLDS
        assert PRODUCT_THRESHOLDS["Prime Auto Loan"]["category"] == "auto"

    def test_has_secured_credit_card(self) -> None:
        assert "Secured Credit Card" in PRODUCT_THRESHOLDS
        assert PRODUCT_THRESHOLDS["Secured Credit Card"]["score"] == 300

    def test_has_rewards_credit_card(self) -> None:
        assert "Rewards Credit Card" in PRODUCT_THRESHOLDS

    def test_has_personal_loan(self) -> None:
        assert "Personal Loan" in PRODUCT_THRESHOLDS

    def test_has_at_least_eight_products(self) -> None:
        assert len(PRODUCT_THRESHOLDS) >= 8


# --- Cycle 8: Fixture Validation Tests ---


class TestFixtures:
    """Tests that conftest fixtures produce valid profiles."""

    def test_good_credit_profile(
        self, good_credit_profile: CreditProfile
    ) -> None:
        assert good_credit_profile.current_score == 740
        assert good_credit_profile.score_band == ScoreBand.GOOD
        assert good_credit_profile.overall_utilization == 20.0
        assert good_credit_profile.account_summary.negative_accounts == 0

    def test_poor_credit_profile(
        self, poor_credit_profile: CreditProfile
    ) -> None:
        assert poor_credit_profile.current_score == 520
        assert poor_credit_profile.score_band == ScoreBand.VERY_POOR
        assert poor_credit_profile.overall_utilization == 85.0
        assert poor_credit_profile.account_summary.collection_accounts == 3
        assert len(poor_credit_profile.negative_items) == 3

    def test_fair_credit_profile(
        self, fair_credit_profile: CreditProfile
    ) -> None:
        assert fair_credit_profile.current_score == 650
        assert fair_credit_profile.score_band == ScoreBand.FAIR
        assert fair_credit_profile.overall_utilization == 45.0
        assert fair_credit_profile.account_summary.negative_accounts == 1

    def test_thin_file_profile(
        self, thin_file_profile: CreditProfile
    ) -> None:
        assert thin_file_profile.current_score == 620
        assert thin_file_profile.score_band == ScoreBand.POOR
        assert thin_file_profile.account_summary.total_accounts == 2
        assert thin_file_profile.negative_items == []
