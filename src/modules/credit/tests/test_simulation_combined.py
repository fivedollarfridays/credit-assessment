"""Tests for simulation — remaining actions, stacking, edge cases — T21.2."""

from __future__ import annotations

from modules.credit.simulation import ScoreSimulator, SimulationAction
from modules.credit.types import (
    AccountSummary,
    ActionType,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


def _poor_profile():
    return CreditProfile(
        current_score=520,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=85.0,
        account_summary=AccountSummary(
            total_accounts=6,
            open_accounts=4,
            collection_accounts=2,
            negative_accounts=3,
            total_balance=42500.0,
            total_credit_limit=50000.0,
        ),
        payment_history_pct=70.0,
        average_account_age_months=24,
        negative_items=[
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Medical",
                amount=2500.0,
            ),
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Utility",
                amount=800.0,
            ),
            NegativeItem(
                type=NegativeItemType.LATE_PAYMENT,
                description="Auto late",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Cycle 6: BECOME_AUTHORIZED_USER + OPEN_SECURED_CARD + DIVERSIFY_CREDIT_MIX
# ---------------------------------------------------------------------------


class TestCreditBuildingActions:
    """Test actions that build credit history."""

    def test_become_authorized_user(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.BECOME_AUTHORIZED_USER),
            ],
        )
        assert result.projected_score > result.original_score
        assert result.score_delta.expected_points >= 5

    def test_open_secured_card(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.OPEN_SECURED_CARD),
            ],
        )
        assert result.projected_score > result.original_score

    def test_diversify_credit_mix(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.DIVERSIFY_CREDIT_MIX),
            ],
        )
        assert result.projected_score > result.original_score


# ---------------------------------------------------------------------------
# Cycle 7: KEEP_ACCOUNTS_OPEN + AVOID_NEW_INQUIRIES
# ---------------------------------------------------------------------------


class TestPreventiveActions:
    """Test actions that prevent score drops."""

    def test_keep_accounts_open(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.KEEP_ACCOUNTS_OPEN),
            ],
        )
        assert result.projected_score >= result.original_score
        assert result.score_delta.expected_points >= 0

    def test_avoid_new_inquiries(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.AVOID_NEW_INQUIRIES),
            ],
        )
        assert result.projected_score >= result.original_score
        assert result.score_delta.expected_points >= 0


# ---------------------------------------------------------------------------
# Cycle 8: Multiple action stacking
# ---------------------------------------------------------------------------


class TestActionStacking:
    """Test that multiple actions compound correctly."""

    def test_two_actions_compound(self):
        profile = _poor_profile()
        sim = ScoreSimulator()
        single = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
                ),
            ],
        )
        double = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
                ),
                SimulationAction(action_type=ActionType.REMOVE_COLLECTION),
            ],
        )
        assert double.projected_score > single.projected_score
        assert double.score_delta.expected_points > single.score_delta.expected_points

    def test_all_ten_action_types_have_handlers(self):
        """Every ActionType value should be handled without error."""
        profile = _poor_profile()
        sim = ScoreSimulator()
        for action_type in ActionType:
            result = sim.simulate(
                profile,
                [
                    SimulationAction(action_type=action_type, target_amount=5000.0),
                ],
            )
            assert isinstance(result.projected_score, int)

    def test_stacked_actions_sequential(self):
        """Actions applied in sequence — second pay_down sees reduced balance."""
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
                ),
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT, target_amount=20000.0
                ),
            ],
        )
        # Two $20k payments on $42.5k balance should reduce to ~$2.5k
        assert result.projected_score > result.original_score


# ---------------------------------------------------------------------------
# Cycle 9: Edge cases + bounds
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and bounds."""

    def test_zero_balance_pay_down_no_crash(self):
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=0.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                total_balance=0.0,
                total_credit_limit=20000.0,
            ),
            payment_history_pct=95.0,
            average_account_age_months=48,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT, target_amount=5000.0
                ),
            ],
        )
        # Already at 0 utilization — no improvement
        assert result.projected_score == result.original_score

    def test_no_negatives_remove_collection_no_crash(self):
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=20.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                total_balance=4000.0,
                total_credit_limit=20000.0,
            ),
            payment_history_pct=95.0,
            average_account_age_months=48,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.REMOVE_COLLECTION),
            ],
        )
        assert result.projected_score == result.original_score

    def test_score_never_below_300(self):
        """Projected score should never drop below 300."""
        profile = CreditProfile(
            current_score=310,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=10.0,
            account_summary=AccountSummary(
                total_accounts=2,
                open_accounts=1,
                total_balance=500.0,
                total_credit_limit=5000.0,
            ),
            payment_history_pct=50.0,
            average_account_age_months=6,
        )
        sim = ScoreSimulator()
        # Even with no impact, score should stay >= 300
        result = sim.simulate(
            profile,
            [
                SimulationAction(action_type=ActionType.AVOID_NEW_INQUIRIES),
            ],
        )
        assert result.projected_score >= 300

    def test_single_action_under_100_points(self):
        """No single action should produce >100pt expected swing."""
        profile = _poor_profile()
        sim = ScoreSimulator()
        for action_type in ActionType:
            result = sim.simulate(
                profile,
                [
                    SimulationAction(action_type=action_type, target_amount=50000.0),
                ],
            )
            assert result.score_delta.expected_points <= 100, (
                f"{action_type.value} produced {result.score_delta.expected_points}pt swing"
            )

    def test_reduce_utilization_none_target_no_op(self):
        """REDUCE_UTILIZATION with no target_amount is a no-op."""
        profile = _poor_profile()
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [SimulationAction(action_type=ActionType.REDUCE_UTILIZATION)],
        )
        assert result.projected_score == result.original_score

    def test_dispute_negative_no_negatives_no_op(self):
        """DISPUTE_NEGATIVE with no negative items is a no-op."""
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=20.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                total_balance=4000.0,
                total_credit_limit=20000.0,
            ),
            payment_history_pct=95.0,
            average_account_age_months=48,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [SimulationAction(action_type=ActionType.DISPUTE_NEGATIVE)],
        )
        assert result.projected_score == result.original_score

    def test_pay_on_time_perfect_history_no_op(self):
        """PAY_ON_TIME with 100% payment history is a no-op."""
        profile = CreditProfile(
            current_score=750,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=15.0,
            account_summary=AccountSummary(
                total_accounts=8,
                open_accounts=6,
                total_balance=3000.0,
                total_credit_limit=20000.0,
            ),
            payment_history_pct=100.0,
            average_account_age_months=72,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [SimulationAction(action_type=ActionType.PAY_ON_TIME)],
        )
        assert result.projected_score == result.original_score

    def test_reduce_utilization_target_above_current_is_noop(self):
        """REDUCE_UTILIZATION with target >= current util is a no-op."""
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=20.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                total_balance=2000.0,
                total_credit_limit=10000.0,
            ),
            payment_history_pct=95.0,
            average_account_age_months=60,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.REDUCE_UTILIZATION,
                    target_amount=30.0,
                )
            ],
        )
        assert result.score_delta.expected_points == 0

    def test_pay_down_debt_zero_credit_limit_is_noop(self):
        """PAY_DOWN_DEBT with zero credit limit returns early."""
        profile = CreditProfile(
            current_score=650,
            score_band=ScoreBand.FAIR,
            overall_utilization=0.0,
            account_summary=AccountSummary(
                total_accounts=2,
                open_accounts=1,
                total_balance=500.0,
                total_credit_limit=0.0,
            ),
            payment_history_pct=90.0,
            average_account_age_months=24,
        )
        sim = ScoreSimulator()
        result = sim.simulate(
            profile,
            [
                SimulationAction(
                    action_type=ActionType.PAY_DOWN_DEBT,
                    target_amount=200.0,
                )
            ],
        )
        assert result.score_delta.expected_points == 0

    def test_ten_actions_boundary_accepted(self):
        """Exactly 10 actions (max_length) should be accepted."""
        from modules.credit.simulate_routes import SimulationRequest

        req = SimulationRequest(
            profile=CreditProfile(
                current_score=700,
                score_band=ScoreBand.GOOD,
                overall_utilization=30.0,
                account_summary=AccountSummary(total_accounts=5, open_accounts=3),
                payment_history_pct=95.0,
                average_account_age_months=60,
            ),
            actions=[
                SimulationAction(action_type=ActionType.PAY_ON_TIME) for _ in range(10)
            ],
        )
        assert len(req.actions) == 10
