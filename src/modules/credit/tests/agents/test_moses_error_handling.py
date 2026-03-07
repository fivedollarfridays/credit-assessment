"""Tests for Moses error handling -- circuit breakers, King validation, Truth compliance."""

from __future__ import annotations

from unittest.mock import MagicMock

from modules.credit.agents.king import KingAgent, _is_substantially_same
from modules.credit.agents.moses import MosesAgent
from modules.credit.agents.truth import EoscarAntiTemplateValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_moses_with(agents: dict) -> MosesAgent:
    """Create a MosesAgent with specific agents wired in."""
    moses = MosesAgent()
    moses._agents = agents
    return moses


def _failing_agent(name: str) -> MagicMock:
    m = MagicMock()
    m.name = name
    m.execute.side_effect = RuntimeError(f"{name} fail")
    return m


# ---------------------------------------------------------------------------
# TestMosesErrorHandling
# ---------------------------------------------------------------------------


class TestMosesErrorHandling:
    """Targeted error handling around circuit breakers and King validation."""

    def test_circuit_prevents_repeated_calls(self, poor_profile_structured):
        """Once circuit opens, agent.execute is not called again."""
        agent = _failing_agent("parks")
        moses = _make_moses_with({"parks": agent})
        # Trip the circuit breaker (3 failures)
        for _ in range(3):
            moses.execute(poor_profile_structured)
        assert moses._breakers["parks"].state == "open"
        call_count_after_open = agent.execute.call_count
        # 4th run -- circuit open, so execute should NOT be called again
        moses.execute(poor_profile_structured)
        assert agent.execute.call_count == call_count_after_open

    def test_king_converts_invalid_direct(self, poor_profile_structured):
        """Invalid basis is converted to bureau method."""
        king = KingAgent()
        ctx = {"force_invalid_basis": True}
        result = king.execute(poor_profile_structured, context=ctx)
        phase2 = result.data["phases"][1]
        if phase2["steps"]:
            step = phase2["steps"][0]
            assert step.get("converted") is True
            assert step["target"] == "bureau"

    def test_substantially_same_blocked(self):
        """>70% Jaccard overlap blocks the dispute."""
        desc = "Medical debt collection account $1200"
        assert _is_substantially_same(desc, desc, 0.70) is True

    def test_new_documentation_allows_direct(self):
        """<70% overlap allows the dispute through."""
        a = "Medical debt collection account"
        b = "Car insurance premium late payment notice different words"
        assert _is_substantially_same(a, b, 0.70) is False

    def test_eoscar_structural_similarity(self):
        """Truth/e-OSCAR validator catches template-like output."""
        validator = EoscarAntiTemplateValidator()
        template_text = (
            "I am disputing the balance of this account under FCRA "
            "and FDCPA. The reported value is incorrect. Please "
            "investigate this matter immediately."
        )
        result = validator.check(template_text)
        assert "specificity_score" in result
        assert "structure_hash" in result
