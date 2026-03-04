"""Tests for credit assessment enums and constants."""

from modules.credit.types import (
    PRODUCT_THRESHOLDS,
    SCORE_BANDS,
    SCORE_WEIGHTS,
    ActionPriority,
    BarrierSeverity,
    LegalTheory,
    ScoreBand,
)


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
