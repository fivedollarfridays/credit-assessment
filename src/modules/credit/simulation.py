"""Score impact simulation engine — what-if analysis for credit actions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .assessment import get_utilization_impact
from .types import ActionType, CreditProfile, NegativeItem, ScoreImpact

# Score impact ranges by action type (low, high) — based on FICO factor weight
# approximations. PAY_DOWN_DEBT and REDUCE_UTILIZATION are computed dynamically.
FIXED_ACTION_IMPACTS: dict[ActionType, tuple[int, int]] = {
    ActionType.REMOVE_COLLECTION: (20, 50),
    ActionType.DISPUTE_NEGATIVE: (10, 40),
    ActionType.PAY_ON_TIME: (5, 15),
    ActionType.BECOME_AUTHORIZED_USER: (5, 20),
    ActionType.OPEN_SECURED_CARD: (3, 10),
    ActionType.KEEP_ACCOUNTS_OPEN: (0, 5),
    ActionType.AVOID_NEW_INQUIRIES: (0, 5),
    ActionType.DIVERSIFY_CREDIT_MIX: (3, 10),
}

PAY_ON_TIME_PCT_INCREMENT = 2.0


class SimulationAction(BaseModel):
    """A proposed credit improvement action for simulation."""

    action_type: ActionType
    target_amount: float | None = Field(default=None, ge=0.0)
    target_item: str | NegativeItem | None = None  # reserved for item-level targeting


class SimulationResult(BaseModel):
    """Result of simulating proposed credit actions."""

    original_score: int
    projected_score: int
    score_delta: ScoreImpact
    actions_applied: list[SimulationAction] = []


class _WorkingState:
    """Mutable state tracking profile changes during simulation."""

    def __init__(self, profile: CreditProfile) -> None:
        self.utilization = profile.overall_utilization
        self.balance = profile.account_summary.total_balance
        self.credit_limit = profile.account_summary.total_credit_limit
        self.payment_history_pct = profile.payment_history_pct
        self.negative_count = len(profile.negative_items)
        self.collection_count = profile.account_summary.collection_accounts
        self.total_min = 0
        self.total_max = 0
        self.total_expected = 0

    def add_impact(self, low: int, high: int) -> None:
        """Add a bounded score impact."""
        expected = (low + high) // 2
        self.total_min += low
        self.total_max += high
        self.total_expected += expected


class ScoreSimulator:
    """Simulates credit score impact of proposed actions."""

    def simulate(
        self, profile: CreditProfile, actions: list[SimulationAction]
    ) -> SimulationResult:
        """Simulate score impact of proposed actions."""
        original = profile.current_score

        if not actions:
            return SimulationResult(
                original_score=original,
                projected_score=original,
                score_delta=ScoreImpact.from_range(0, 0),
                actions_applied=[],
            )

        state = _WorkingState(profile)

        for action in actions:
            self._apply_action(action, state, profile)

        projected = max(300, min(850, original + state.total_expected))
        return SimulationResult(
            original_score=original,
            projected_score=projected,
            score_delta=ScoreImpact(
                min_points=state.total_min,
                max_points=state.total_max,
                expected_points=state.total_expected,
            ),
            actions_applied=list(actions),
        )

    def _apply_action(
        self,
        action: SimulationAction,
        state: _WorkingState,
        profile: CreditProfile,
    ) -> None:
        """Dispatch to the appropriate action handler."""
        handler = _ACTION_HANDLERS.get(action.action_type)
        if handler:
            handler(self, action, state, profile)

    def _handle_pay_down_debt(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        amount = action.target_amount or 0.0
        if state.credit_limit <= 0 or amount <= 0:
            return
        old_util = state.utilization
        new_balance = max(0.0, state.balance - amount)
        new_util = (new_balance / state.credit_limit) * 100.0
        state.balance = new_balance
        state.utilization = new_util
        impact = get_utilization_impact(old_util, new_util)
        state.add_impact(impact["low"], impact["high"])

    def _handle_reduce_utilization(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        target_util = action.target_amount
        if target_util is None:
            return
        old_util = state.utilization
        if target_util >= old_util:
            return
        state.utilization = target_util
        if state.credit_limit > 0:
            state.balance = (target_util / 100.0) * state.credit_limit
        impact = get_utilization_impact(old_util, target_util)
        state.add_impact(impact["low"], impact["high"])

    def _handle_remove_collection(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        if state.collection_count <= 0:
            return
        state.collection_count -= 1
        state.negative_count = max(0, state.negative_count - 1)
        low, high = FIXED_ACTION_IMPACTS[ActionType.REMOVE_COLLECTION]
        state.add_impact(low, high)

    def _handle_dispute_negative(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        if state.negative_count <= 0:
            return
        state.negative_count -= 1
        low, high = FIXED_ACTION_IMPACTS[ActionType.DISPUTE_NEGATIVE]
        state.add_impact(low, high)

    def _handle_pay_on_time(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        if state.payment_history_pct >= 100.0:
            return
        state.payment_history_pct = min(
            100.0, state.payment_history_pct + PAY_ON_TIME_PCT_INCREMENT
        )
        low, high = FIXED_ACTION_IMPACTS[ActionType.PAY_ON_TIME]
        state.add_impact(low, high)

    def _handle_fixed_impact(
        self, action: SimulationAction, state: _WorkingState, profile: CreditProfile
    ) -> None:
        """Handle actions with fixed score impact ranges."""
        low, high = FIXED_ACTION_IMPACTS[action.action_type]
        state.add_impact(low, high)


_ACTION_HANDLERS = {
    ActionType.PAY_DOWN_DEBT: ScoreSimulator._handle_pay_down_debt,
    ActionType.REDUCE_UTILIZATION: ScoreSimulator._handle_reduce_utilization,
    ActionType.REMOVE_COLLECTION: ScoreSimulator._handle_remove_collection,
    ActionType.DISPUTE_NEGATIVE: ScoreSimulator._handle_dispute_negative,
    ActionType.PAY_ON_TIME: ScoreSimulator._handle_pay_on_time,
    ActionType.BECOME_AUTHORIZED_USER: ScoreSimulator._handle_fixed_impact,
    ActionType.OPEN_SECURED_CARD: ScoreSimulator._handle_fixed_impact,
    ActionType.KEEP_ACCOUNTS_OPEN: ScoreSimulator._handle_fixed_impact,
    ActionType.AVOID_NEW_INQUIRIES: ScoreSimulator._handle_fixed_impact,
    ActionType.DIVERSIFY_CREDIT_MIX: ScoreSimulator._handle_fixed_impact,
}
