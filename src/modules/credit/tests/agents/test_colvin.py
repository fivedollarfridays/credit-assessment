"""Tests for Colvin (First Strike) agent -- 40-day attack cycle generator."""

from __future__ import annotations

import pytest

from modules.credit.agents import get_agent
from modules.credit.agents.base import AgentResult
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    from modules.credit.agents.colvin import ColvinAgent

    return ColvinAgent()


@pytest.fixture
def single_item_profile() -> CreditProfile:
    """Profile with one CHARGE_OFF item."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=82.0,
        account_summary=AccountSummary(
            total_accounts=5,
            open_accounts=3,
            negative_accounts=1,
            collection_accounts=0,
            total_balance=4200.0,
            total_credit_limit=5100.0,
            monthly_payments=180.0,
        ),
        payment_history_pct=68.0,
        average_account_age_months=18,
        negative_items=[
            NegativeItem(
                type=NegativeItemType.CHARGE_OFF,
                description="Charged-off credit card - $3,000",
                amount=3000.0,
                creditor="Big Bank",
            ),
        ],
    )


@pytest.fixture
def empty_items_profile() -> CreditProfile:
    """Profile with no negative items."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=82.0,
        account_summary=AccountSummary(
            total_accounts=5,
            open_accounts=3,
            total_balance=4200.0,
            total_credit_limit=5100.0,
            monthly_payments=180.0,
        ),
        payment_history_pct=68.0,
        average_account_age_months=18,
        negative_items=[],
    )


# ---------------------------------------------------------------------------
# TestColvinCycles
# ---------------------------------------------------------------------------


class TestColvinCycles:
    """40-day attack cycle generation."""

    def test_cycles_generated_for_each_item(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """2 collection items x 3 rounds each = 6 cycles."""
        result = agent.execute(poor_profile_structured)
        assert result.status == "success"
        assert len(result.data["attack_cycles"]) == 6

    def test_cycle_is_40_days(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Each cycle spans exactly 40 days (0-indexed: day_end - day_start = 39)."""
        result = agent.execute(poor_profile_structured)
        for cycle in result.data["attack_cycles"]:
            assert cycle["day_end"] - cycle["day_start"] == 39

    def test_day_ranges_sequential(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Cycles for the same item should have sequential, non-overlapping day ranges."""
        result = agent.execute(poor_profile_structured)
        cycles = result.data["attack_cycles"]
        # Group by item description
        by_item: dict[str, list] = {}
        for c in cycles:
            by_item.setdefault(c["item"], []).append(c)
        for item_cycles in by_item.values():
            sorted_cycles = sorted(item_cycles, key=lambda c: c["cycle"])
            for i in range(1, len(sorted_cycles)):
                assert sorted_cycles[i]["day_start"] > sorted_cycles[i - 1]["day_end"]

    def test_legal_basis_rotates(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Each round for the same item uses a different legal basis."""
        result = agent.execute(poor_profile_structured)
        cycles = result.data["attack_cycles"]
        by_item: dict[str, list] = {}
        for c in cycles:
            by_item.setdefault(c["item"], []).append(c)
        for item_cycles in by_item.values():
            bases = [c["legal_basis"] for c in item_cycles]
            assert len(bases) == len(set(bases)), "Legal bases should be unique per item"

    def test_statutes_included(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Every cycle must include at least one statute."""
        result = agent.execute(poor_profile_structured)
        for cycle in result.data["attack_cycles"]:
            assert len(cycle["statutes"]) >= 1

    def test_cycle_structure(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """All required fields are present in each cycle."""
        result = agent.execute(poor_profile_structured)
        required_keys = {
            "cycle", "item", "creditor", "bureau",
            "legal_basis", "statutes", "day_start", "day_end",
            "factual_target", "format_recommendation",
        }
        for cycle in result.data["attack_cycles"]:
            assert required_keys.issubset(cycle.keys())


# ---------------------------------------------------------------------------
# TestColvinBureauRotation
# ---------------------------------------------------------------------------


class TestColvinBureauRotation:
    """Bureau rotation across cycles."""

    def test_bureaus_rotate(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Consecutive rounds for the same item use different bureaus."""
        result = agent.execute(poor_profile_structured)
        cycles = result.data["attack_cycles"]
        by_item: dict[str, list] = {}
        for c in cycles:
            by_item.setdefault(c["item"], []).append(c)
        for item_cycles in by_item.values():
            sorted_cycles = sorted(item_cycles, key=lambda c: c["cycle"])
            for i in range(1, len(sorted_cycles)):
                assert sorted_cycles[i]["bureau"] != sorted_cycles[i - 1]["bureau"]

    def test_all_three_bureaus_used(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """All three bureaus appear in bureau_distribution."""
        result = agent.execute(poor_profile_structured)
        dist = result.data["bureau_distribution"]
        assert set(dist.keys()) == {"Experian", "Equifax", "TransUnion"}

    def test_distribution_roughly_even(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """No single bureau handles more than 50% of total cycles."""
        result = agent.execute(poor_profile_structured)
        dist = result.data["bureau_distribution"]
        total = sum(dist.values())
        for count in dist.values():
            assert count <= total * 0.5 + 1  # +1 for rounding

    def test_no_consecutive_same_bureau(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """For each item, no two consecutive rounds go to the same bureau."""
        result = agent.execute(poor_profile_structured)
        cycles = result.data["attack_cycles"]
        by_item: dict[str, list] = {}
        for c in cycles:
            by_item.setdefault(c["item"], []).append(c)
        for item_cycles in by_item.values():
            sorted_cycles = sorted(item_cycles, key=lambda c: c["cycle"])
            for i in range(1, len(sorted_cycles)):
                assert sorted_cycles[i]["bureau"] != sorted_cycles[i - 1]["bureau"]


# ---------------------------------------------------------------------------
# TestColvinDiversity
# ---------------------------------------------------------------------------


class TestColvinDiversity:
    """Anti-flagging diversity metrics."""

    def test_diversity_score_range(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Diversity metric is between 0.0 and 1.0."""
        result = agent.execute(poor_profile_structured)
        score = result.data["diversity_metric"]
        assert 0.0 <= score <= 1.0

    def test_diversity_above_threshold(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Diversity score should be >= 0.7 for well-distributed cycles."""
        result = agent.execute(poor_profile_structured)
        assert result.data["diversity_metric"] >= 0.7

    def test_format_recommendations(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Each cycle has a format_recommendation (prose/bullets/numbered)."""
        result = agent.execute(poor_profile_structured)
        valid_formats = {"prose", "bullets", "numbered"}
        for cycle in result.data["attack_cycles"]:
            assert cycle["format_recommendation"] in valid_formats

    def test_phrase_variation_count(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """phrase_variation_count counts unique legal basis phrases."""
        result = agent.execute(poor_profile_structured)
        count = result.data["phrase_variation_count"]
        assert isinstance(count, int)
        assert count >= 1


# ---------------------------------------------------------------------------
# TestColvinFactualTargets
# ---------------------------------------------------------------------------


class TestColvinFactualTargets:
    """Factual dispute target generation."""

    def test_collection_factual_target(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Collection items mention balance/amount in factual target."""
        result = agent.execute(poor_profile_structured)
        for cycle in result.data["attack_cycles"]:
            # All items in poor_profile_structured are collections
            assert "balance" in cycle["factual_target"].lower() or \
                   "amount" in cycle["factual_target"].lower()

    def test_factual_target_includes_amount(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Dollar amount appears in the factual target for collection items."""
        result = agent.execute(poor_profile_structured)
        for cycle in result.data["attack_cycles"]:
            assert "$" in cycle["factual_target"]

    def test_all_targets_factual(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """All targets mention 'factual' or specific data points."""
        result = agent.execute(poor_profile_structured)
        for cycle in result.data["attack_cycles"]:
            target_lower = cycle["factual_target"].lower()
            assert "factual" in target_lower or "$" in cycle["factual_target"]

    def test_fifth_circuit_context(
        self, agent, poor_profile_structured: CreditProfile
    ) -> None:
        """Output includes fifth_circuit_context string."""
        result = agent.execute(poor_profile_structured)
        assert "fifth_circuit_context" in result.data
        assert "FACTUAL" in result.data["fifth_circuit_context"]


# ---------------------------------------------------------------------------
# TestColvinEdgeCases
# ---------------------------------------------------------------------------


class TestColvinEdgeCases:
    """Edge case handling."""

    def test_no_negative_items(self, agent, empty_items_profile) -> None:
        """Empty negative items produces empty attack cycles."""
        result = agent.execute(empty_items_profile)
        assert result.status == "success"
        assert result.data["attack_cycles"] == []
        assert result.data["total_cycles"] == 0

    def test_single_item(self, agent, single_item_profile) -> None:
        """Single item generates correct number of cycles (3 for charge_off)."""
        result = agent.execute(single_item_profile)
        assert result.status == "success"
        # charge_off has 3 rounds in legal_basis_rotation.json
        assert len(result.data["attack_cycles"]) == 3
        assert result.data["items_covered"] == 1


# ---------------------------------------------------------------------------
# TestColvinRegistration
# ---------------------------------------------------------------------------


class TestColvinRegistration:
    """Agent registration in the registry."""

    def test_agent_registered(self) -> None:
        """Colvin agent is discoverable in the registry."""
        import modules.credit.agents.colvin  # noqa: F401

        assert get_agent("colvin") is not None

    def test_agent_name(self, agent) -> None:
        """Agent name property is 'colvin'."""
        assert agent.name == "colvin"
