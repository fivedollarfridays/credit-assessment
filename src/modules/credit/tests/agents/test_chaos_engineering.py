"""Chaos engineering tests for Baby INERTIA agent resilience."""

from __future__ import annotations

from unittest.mock import MagicMock

from modules.credit.agents.base import AgentResult
from modules.credit.agents.moses import MosesAgent, _fallback_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _failing_agent(name: str) -> MagicMock:
    """Create a mock agent that always raises."""
    m = MagicMock()
    m.name = name
    m.execute.side_effect = RuntimeError(f"{name} exploded")
    return m


def _ok_agent(name: str, data: dict | None = None) -> MagicMock:
    """Create a mock agent that returns success."""
    m = MagicMock()
    m.name = name
    m.execute.return_value = AgentResult(
        agent_name=name,
        status="success",
        data=data or {},
        execution_ms=1.0,
    )
    return m


def _make_moses_with(agents: dict) -> MosesAgent:
    """Create a MosesAgent with specific agents wired in."""
    moses = MosesAgent()
    moses._agents = agents
    return moses


# ---------------------------------------------------------------------------
# TestChaosEngineering
# ---------------------------------------------------------------------------


class TestChaosEngineering:
    """Verify resilience under failure conditions."""

    def test_all_agents_fail_simultaneously(self, poor_profile_structured):
        """All agents raise -- Moses returns degraded, no crash."""
        agents = {
            name: _failing_agent(name)
            for name in (
                "parks",
                "king",
                "colvin",
                "robinson",
                "lewis",
                "phantom",
                "truth",
            )
        }
        moses = _make_moses_with(agents)
        result = moses.execute(poor_profile_structured)
        assert result.status == "success"
        assert "liberation_plan" in result.data
        summary = result.data["validation_summary"]
        assert summary["agents_fallback"] >= 7

    def test_partial_failures_no_cascade(self, poor_profile_structured):
        """One agent fails, others still produce data."""
        agents = {
            "parks": _failing_agent("parks"),
            "king": _ok_agent(
                "king", {"phases": [{"phase": 1, "name": "P1", "steps": []}]}
            ),
            "colvin": _ok_agent("colvin"),
            "robinson": _ok_agent("robinson"),
            "lewis": _ok_agent("lewis"),
            "phantom": _ok_agent(
                "phantom",
                {
                    "total_annual_tax": 4000,
                    "methodology_source": "Bristol PFRC",
                    "components": {},
                    "validation": {
                        "in_range": True,
                        "capped": False,
                        "original_total": 4000,
                    },
                },
            ),
            "truth": _ok_agent("truth", {"passes": True}),
        }
        moses = _make_moses_with(agents)
        result = moses.execute(poor_profile_structured)
        assert result.status == "success"
        lp = result.data["liberation_plan"]
        assert "battle_plan" in lp
        summary = result.data["validation_summary"]
        assert summary["agents_passed"] >= 6

    def test_malformed_input_recovery(self, poor_profile_structured):
        """Weird profile values do not crash the pipeline."""
        from modules.credit.agents.phantom import PhantomAgent

        phantom = PhantomAgent()
        result = phantom.execute(
            poor_profile_structured, context={"target_industry": "nonexistent"}
        )
        assert result.status == "success"

    def test_null_pointer_safety(self, poor_profile_structured):
        """None context and empty negative items do not crash."""
        moses = _make_moses_with({})
        result = moses.execute(poor_profile_structured, context=None)
        assert result.status == "success"
        assert "liberation_plan" in result.data

    def test_circuit_breaker_opens(self, poor_profile_structured):
        """After 3 failures, circuit opens and blocks further calls."""
        agents = {name: _failing_agent(name) for name in ("parks",)}
        moses = _make_moses_with(agents)
        # Run 3 times to trip the breaker
        for _ in range(3):
            moses.execute(poor_profile_structured)
        breaker = moses._breakers["parks"]
        assert breaker.state == "open"

    def test_dlq_stores_failures(self, poor_profile_structured):
        """Failed agent entries are recorded in the DLQ."""
        agents = {"parks": _failing_agent("parks")}
        moses = _make_moses_with(agents)
        moses.execute(poor_profile_structured)
        assert moses._dlq.count >= 1

    def test_validation_contracts_catch_malformed(self, poor_profile_structured):
        """Bad Phantom output triggers fallback via validation contract."""
        bad_phantom = _ok_agent("phantom", {"total_annual_tax": 0, "no_source": True})
        agents = {"phantom": bad_phantom}
        moses = _make_moses_with(agents)
        result = moses.execute(poor_profile_structured)
        summary = result.data["validation_summary"]
        assert "phantom" in summary["fallback_details"]

    def test_fallback_data_never_null(self):
        """All typed fallbacks return non-null data dicts."""
        for name in ("parks", "king", "phantom", "unknown"):
            fb = _fallback_result(name)
            assert fb.data is not None
            assert isinstance(fb.data, dict)
