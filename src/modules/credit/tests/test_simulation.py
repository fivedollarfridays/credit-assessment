"""Tests for score impact simulation engine — T21.2 TDD."""

from __future__ import annotations

from modules.credit.simulation import ScoreSimulator, SimulationAction, SimulationResult
from modules.credit.types import (
    AccountSummary,
    ActionType,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
    ScoreImpact,
)


# ---------------------------------------------------------------------------
# Cycle 1: SimulationAction + SimulationResult types
# ---------------------------------------------------------------------------


class TestSimulationTypes:
    """Test SimulationAction and SimulationResult Pydantic models."""

    def test_action_minimal(self):
        action = SimulationAction(action_type=ActionType.PAY_DOWN_DEBT)
        assert action.action_type == ActionType.PAY_DOWN_DEBT
        assert action.target_amount is None
        assert action.target_item is None

    def test_action_with_amount(self):
        action = SimulationAction(
            action_type=ActionType.PAY_DOWN_DEBT, target_amount=5000.0
        )
        assert action.target_amount == 5000.0

    def test_result_has_required_fields(self):
        result = SimulationResult(
            original_score=650,
            projected_score=680,
            score_delta=ScoreImpact(min_points=20, max_points=40, expected_points=30),
            actions_applied=[SimulationAction(action_type=ActionType.PAY_DOWN_DEBT)],
        )
        assert result.original_score == 650
        assert result.projected_score == 680
        assert result.score_delta.expected_points == 30
        assert len(result.actions_applied) == 1


# ---------------------------------------------------------------------------
# Cycle 2: Basic simulate()
# ---------------------------------------------------------------------------


class TestSimulateBasic:
    """Test ScoreSimulator.simulate() with no actions."""

    def _make_profile(self, score=650, utilization=30.0):
        return CreditProfile(
            current_score=score,
            score_band=ScoreBand.FAIR if 650 <= score <= 699 else ScoreBand.GOOD,
            overall_utilization=utilization,
            account_summary=AccountSummary(
                total_accounts=6, open_accounts=4,
                total_balance=9000.0, total_credit_limit=30000.0,
            ),
            payment_history_pct=90.0,
            average_account_age_months=36,
        )

    def test_empty_actions_returns_original_score(self):
        profile = self._make_profile()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [])
        assert result.original_score == 650
        assert result.projected_score == 650
        assert result.score_delta.expected_points == 0

    def test_empty_actions_returns_empty_actions_list(self):
        profile = self._make_profile()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [])
        assert result.actions_applied == []


# ---------------------------------------------------------------------------
# Cycle 3: PAY_DOWN_DEBT + REDUCE_UTILIZATION
# ---------------------------------------------------------------------------


class TestUtilizationActions:
    """Test actions that affect utilization."""

    def _high_util_profile(self):
        return CreditProfile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=85.0,
            account_summary=AccountSummary(
                total_accounts=6, open_accounts=4,
                total_balance=42500.0, total_credit_limit=50000.0,
            ),
            payment_history_pct=80.0,
            average_account_age_months=36,
        )

    def test_pay_down_debt_increases_score(self):
        profile = self._high_util_profile()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(
                action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
            ),
        ])
        assert result.projected_score > result.original_score
        assert result.score_delta.expected_points > 0

    def test_pay_down_debt_reduces_utilization(self):
        """Paying down $20k on $50k limit should drop utilization."""
        profile = self._high_util_profile()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(
                action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
            ),
        ])
        # Score should increase — utilization goes from 85% to 45%
        assert result.score_delta.expected_points >= 10

    def test_reduce_utilization_increases_score(self):
        profile = self._high_util_profile()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(
                action_type=ActionType.REDUCE_UTILIZATION, target_amount=30.0
            ),
        ])
        assert result.projected_score > result.original_score

    def test_pay_down_debt_score_clamped_to_850(self):
        """Score cannot exceed 850."""
        profile = CreditProfile(
            current_score=840,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=60.0,
            account_summary=AccountSummary(
                total_accounts=10, open_accounts=8,
                total_balance=18000.0, total_credit_limit=30000.0,
            ),
            payment_history_pct=99.0,
            average_account_age_months=120,
        )
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(
                action_type=ActionType.PAY_DOWN_DEBT, target_amount=15000.0
            ),
        ])
        assert result.projected_score <= 850


# ---------------------------------------------------------------------------
# Cycle 4: REMOVE_COLLECTION + DISPUTE_NEGATIVE
# ---------------------------------------------------------------------------


class TestNegativeItemActions:
    """Test actions that remove negative items."""

    def _profile_with_collections(self):
        return CreditProfile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=40.0,
            account_summary=AccountSummary(
                total_accounts=8, open_accounts=4,
                collection_accounts=2, negative_accounts=3,
                total_balance=12000.0, total_credit_limit=30000.0,
            ),
            payment_history_pct=70.0,
            average_account_age_months=36,
            negative_items=[
                NegativeItem(
                    type=NegativeItemType.COLLECTION,
                    description="Medical collection",
                    amount=2500.0,
                ),
                NegativeItem(
                    type=NegativeItemType.COLLECTION,
                    description="Utility collection",
                    amount=800.0,
                ),
                NegativeItem(
                    type=NegativeItemType.LATE_PAYMENT,
                    description="Auto loan late",
                ),
            ],
        )

    def test_remove_collection_increases_score(self):
        profile = self._profile_with_collections()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(action_type=ActionType.REMOVE_COLLECTION),
        ])
        assert result.projected_score > result.original_score
        assert result.score_delta.expected_points >= 20

    def test_dispute_negative_increases_score(self):
        profile = self._profile_with_collections()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(action_type=ActionType.DISPUTE_NEGATIVE),
        ])
        assert result.projected_score > result.original_score

    def test_remove_collection_bounded_under_100(self):
        profile = self._profile_with_collections()
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(action_type=ActionType.REMOVE_COLLECTION),
        ])
        assert result.score_delta.expected_points <= 100


# ---------------------------------------------------------------------------
# Cycle 5: PAY_ON_TIME
# ---------------------------------------------------------------------------


class TestPayOnTime:
    """Test PAY_ON_TIME action."""

    def test_pay_on_time_increases_score(self):
        profile = CreditProfile(
            current_score=620,
            score_band=ScoreBand.POOR,
            overall_utilization=30.0,
            account_summary=AccountSummary(
                total_accounts=6, open_accounts=4,
                total_balance=9000.0, total_credit_limit=30000.0,
            ),
            payment_history_pct=80.0,
            average_account_age_months=36,
        )
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(action_type=ActionType.PAY_ON_TIME),
        ])
        assert result.projected_score > result.original_score

    def test_pay_on_time_bounded(self):
        profile = CreditProfile(
            current_score=620,
            score_band=ScoreBand.POOR,
            overall_utilization=30.0,
            account_summary=AccountSummary(
                total_accounts=6, open_accounts=4,
                total_balance=9000.0, total_credit_limit=30000.0,
            ),
            payment_history_pct=80.0,
            average_account_age_months=36,
        )
        sim = ScoreSimulator()
        result = sim.simulate(profile, [
            SimulationAction(action_type=ActionType.PAY_ON_TIME),
        ])
        assert result.score_delta.expected_points <= 15
