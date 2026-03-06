"""Integration tests for Baby INERTIA agent chain -- real agents, no mocking."""

from __future__ import annotations

import pytest

from modules.credit.agents.base import AgentResult
from modules.credit.agents.moses import MosesAgent
from modules.credit.agents.parks import ParksAgent
from modules.credit.agents.king import KingAgent
from modules.credit.agents.colvin import ColvinAgent
from modules.credit.agents.robinson import RobinsonAgent
from modules.credit.agents.lewis import LewisAgent
from modules.credit.agents.phantom import PhantomAgent
from modules.credit.agents.truth import TruthAgent
from modules.credit.agents.gray import GrayAgent
from modules.credit.agents.tubman import TubmanAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wired_moses() -> MosesAgent:
    """Create a MosesAgent with all real sub-agents wired in."""
    moses = MosesAgent()
    moses._agents = {
        "parks": ParksAgent(),
        "king": KingAgent(),
        "colvin": ColvinAgent(),
        "robinson": RobinsonAgent(),
        "lewis": LewisAgent(),
        "phantom": PhantomAgent(),
        "truth": TruthAgent(),
        "gray": GrayAgent(),
        "tubman": TubmanAgent(),
    }
    return moses


# ---------------------------------------------------------------------------
# TestAgentChainIntegration
# ---------------------------------------------------------------------------


class TestAgentChainIntegration:
    """End-to-end integration tests with real agent instances."""

    def test_full_liberation_plan(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        assert result.status == "success"
        lp = result.data["liberation_plan"]
        assert "situation" in lp
        assert "battle_plan" in lp
        assert "poverty_tax" in lp
        assert "impact" in lp
        assert "monday_morning" in lp
        assert "attack_cycles" in lp

    def test_backward_compatibility_assess(self, poor_profile_structured):
        """CreditAssessmentService still works after liberation wiring."""
        from modules.credit.assessment import CreditAssessmentService
        svc = CreditAssessmentService()
        result = svc.assess(poor_profile_structured)
        assert result.readiness.score >= 0
        assert result.barrier_severity is not None

    def test_all_agents_fire_in_order(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        chain = result.data["reasoning_chain"]
        expected_base = ["parks", "king", "colvin", "robinson", "lewis", "phantom", "truth"]
        actual_base = [n for n in chain if n in expected_base]
        assert actual_base == expected_base

    def test_conditional_gray_skips(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        chain = result.data["reasoning_chain"]
        assert "gray" not in chain

    def test_conditional_tubman_skips(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        chain = result.data["reasoning_chain"]
        assert "tubman" not in chain

    def test_truth_compliance_check(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        assert "compliance" in result.data

    def test_phantom_range_validation(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        total = tax.get("total_annual_tax", 0)
        assert 1500 <= total <= 15000

    def test_methodology_source_present(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        assert "methodology_source" in tax
        assert "Bristol" in tax["methodology_source"] or "PFRC" in tax["methodology_source"]

    def test_reasoning_chain_populated(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        chain = result.data["reasoning_chain"]
        assert isinstance(chain, list)
        assert len(chain) >= 7

    def test_city_config_loaded(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        assert "community_impact" in result.data
        assert "$" in result.data["community_impact"]

    def test_parks_barriers_present(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        situation = result.data["liberation_plan"]["situation"]
        assert isinstance(situation, dict)

    def test_colvin_cycles_present(self, poor_profile_structured):
        moses = _make_wired_moses()
        result = moses.execute(poor_profile_structured)
        cycles = result.data["liberation_plan"]["attack_cycles"]
        assert isinstance(cycles, dict)
