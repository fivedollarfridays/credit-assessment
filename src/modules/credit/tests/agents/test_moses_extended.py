"""Extended Moses tests — circuit breakers, DLQ, performance, output, context."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from modules.credit.agents.base import AgentResult
from modules.credit.agents.resilience import CircuitBreaker


def _ok(name: str, data: dict | None = None) -> AgentResult:
    return AgentResult(
        agent_name=name, status="success", data=data or {}, execution_ms=1.0
    )


def _build_all_mocks() -> dict[str, MagicMock]:
    agents = {}
    for name in (
        "parks",
        "king",
        "phantom",
        "truth",
        "robinson",
        "gray",
        "tubman",
        "lewis",
        "colvin",
    ):
        m = MagicMock()
        m.name = name
        agents[name] = m
    agents["parks"].execute.return_value = _ok(
        "parks",
        {
            "life_barriers": {"employment": [], "housing": []},
            "doors_analysis": [
                {"threshold": 580, "new_doors": ["housing:private"], "count": 1}
            ],
            "cheapest_door": {"threshold": 580, "points_needed": 45},
            "roi_per_door": [],
        },
    )
    agents["king"].execute.return_value = _ok(
        "king",
        {
            "phases": [{"phase": 1, "name": "Bureau Disputes", "steps": []}],
            "total_estimated_days": 90,
        },
    )
    agents["phantom"].execute.return_value = _ok(
        "phantom",
        {
            "total_annual_tax": 4200,
            "methodology_source": "Bristol PFRC",
            "components": {},
            "validation": {"in_range": True, "capped": False, "original_total": 4200},
        },
    )
    agents["truth"].execute.return_value = _ok(
        "truth", {"passes": True, "recommendations": []}
    )
    for n in ("robinson", "gray", "tubman", "lewis", "colvin"):
        agents[n].execute.return_value = _ok(n, {"placeholder": True})
    return agents


@pytest.fixture
def mock_agents():
    return _build_all_mocks()


@pytest.fixture
def mock_kevin():
    assess = MagicMock()
    assess.assess.return_value = MagicMock(
        barrier_severity="high",
        barrier_details=[],
        readiness=MagicMock(score=35),
        dispute_pathway=MagicMock(steps=[], total_estimated_days=30),
    )
    dispute = MagicMock()
    dispute.generate_pathway.return_value = MagicMock(steps=[], total_estimated_days=30)
    return {"assessment": assess, "dispute": dispute}


def _make_moses(mock_agents, mock_kevin):
    from modules.credit.agents.moses import MosesAgent

    agent = MosesAgent()
    agent._agents = mock_agents
    agent._assessment_svc = mock_kevin["assessment"]
    agent._dispute_svc = mock_kevin["dispute"]
    return agent


class TestMosesCircuitBreaker:
    def test_circuit_opens_after_failures(self, poor_profile_structured, mock_kevin):
        agents = _build_all_mocks()
        agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["fail"]
        )
        moses = _make_moses(agents, mock_kevin)
        for _ in range(3):
            moses.execute(poor_profile_structured)
        assert moses._breakers["parks"].state == "open"

    def test_circuit_prevents_calls(self, poor_profile_structured, mock_kevin):
        agents = _build_all_mocks()
        agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["fail"]
        )
        moses = _make_moses(agents, mock_kevin)
        for _ in range(3):
            moses.execute(poor_profile_structured)
        agents["parks"].execute.reset_mock()
        moses.execute(poor_profile_structured)
        assert not agents["parks"].execute.called

    def test_circuit_breaker_per_agent(self, poor_profile_structured, mock_kevin):
        agents = _build_all_mocks()
        moses = _make_moses(agents, mock_kevin)
        assert "parks" in moses._breakers
        assert "king" in moses._breakers
        assert moses._breakers["parks"] is not moses._breakers["king"]

    def test_circuit_state_in_summary(self, poor_profile_structured, mock_kevin):
        agents = _build_all_mocks()
        agents["colvin"].execute.return_value = AgentResult(
            agent_name="colvin", status="error", errors=["fail"]
        )
        moses = _make_moses(agents, mock_kevin)
        for _ in range(3):
            moses.execute(poor_profile_structured)
        result = moses.execute(poor_profile_structured)
        assert result.data["validation_summary"]["circuits_opened"] >= 1

    def test_half_open_allows_retry(self, poor_profile_structured, mock_kevin):
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=0.01)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        time.sleep(0.02)
        assert cb.state == "half-open"
        assert cb.allow_request() is True


class TestMosesDLQ:
    def test_dlq_stores_failures(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["colvin"].execute.side_effect = RuntimeError("crash")
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        assert moses._dlq.count >= 1

    def test_dlq_count_in_summary(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["colvin"].execute.side_effect = RuntimeError("crash")
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["validation_summary"]["dlq_count"] >= 1

    def test_dlq_entry_has_agent_name(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["lewis"].execute.side_effect = RuntimeError("crash")
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        entries = moses._dlq.to_dicts()
        names = [e["agent_name"] for e in entries]
        assert "lewis" in names

    def test_dlq_entry_has_error(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["lewis"].execute.side_effect = RuntimeError("kaboom")
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        entries = moses._dlq.to_dicts()
        assert any("kaboom" in e["error_message"] for e in entries)


class TestMosesPerformance:
    def test_per_agent_ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "parks" in result.data["performance"]["per_agent_ms"]

    def test_total_time_ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["performance"]["total_time_ms"] >= 0

    def test_under_100ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["performance"]["total_time_ms"] < 100


class TestMosesOutput:
    def test_community_impact(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "$14.6M" in result.data["community_impact"]

    def test_why_deterministic(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "Dynatrace" in result.data["why_deterministic"]

    def test_validation_summary_structure(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        vs = result.data["validation_summary"]
        for key in (
            "agents_passed",
            "agents_fallback",
            "fallback_details",
            "circuits_opened",
            "dlq_count",
        ):
            assert key in vs

    def test_compliance_section(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "compliance" in result.data

    def test_agent_registered(self):
        from modules.credit.agents.moses import MosesAgent  # noqa: F401
        from modules.credit.agents import list_agents

        assert "moses" in list_agents()


class TestMosesContextPassing:
    def test_parks_result_passed_to_king(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        king_call = mock_agents["king"].execute.call_args
        ctx = king_call[1].get("context", {})
        assert "parks_result" in ctx

    def test_parks_result_passed_to_lewis(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        lewis_call = mock_agents["lewis"].execute.call_args
        ctx = lewis_call[1].get("context", {})
        assert "parks_result" in ctx


# ---------------------------------------------------------------------------
# TestMosesWiring — factory and auto-discovery
# ---------------------------------------------------------------------------


class TestMosesWiring:
    """Tests for create_wired_moses() factory and auto-discovery."""

    def test_create_wired_moses_populates_agents(self):
        from modules.credit.agents import create_wired_moses

        moses = create_wired_moses()
        assert len(moses._agents) >= 7
        for name in (
            "parks",
            "king",
            "colvin",
            "robinson",
            "lewis",
            "phantom",
            "truth",
        ):
            assert name in moses._agents

    def test_create_wired_moses_agents_are_instances(self):
        from modules.credit.agents import create_wired_moses
        from modules.credit.agents.base import BaseAgent

        moses = create_wired_moses()
        for agent in moses._agents.values():
            assert isinstance(agent, BaseAgent)

    def test_bare_moses_auto_discovers(self):
        """MosesAgent() with no args should auto-populate from registry."""
        from modules.credit.agents.moses import MosesAgent

        # Ensure agent modules are imported
        import modules.credit.agents.parks  # noqa: F401
        import modules.credit.agents.king  # noqa: F401

        moses = MosesAgent()
        # Should have at least parks and king from registry
        assert len(moses._agents) >= 2

    def test_explicit_agents_override_registry(self):
        """Passing explicit agents dict should use those, not registry."""
        from modules.credit.agents.moses import MosesAgent

        mock = MagicMock()
        mock.name = "test"
        moses = MosesAgent(agents={"test": mock})
        assert moses._agents == {"test": mock}
        assert "parks" not in moses._agents
