"""Tests for Moses (Orchestrator) agent — wires all Baby INERTIA agents."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from modules.credit.agents.base import AgentResult
from modules.credit.agents.resilience import CircuitBreaker


# ---------------------------------------------------------------------------
# Helpers: mock agent factory + mock Kevin services
# ---------------------------------------------------------------------------


def _ok(name: str, data: dict | None = None) -> AgentResult:
    """Build a successful AgentResult."""
    return AgentResult(
        agent_name=name, status="success", data=data or {}, execution_ms=1.0
    )


def _make_parks_ok() -> AgentResult:
    return _ok(
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


def _make_king_ok() -> AgentResult:
    return _ok(
        "king",
        {
            "phases": [{"phase": 1, "name": "Bureau Disputes", "steps": []}],
            "total_estimated_days": 90,
        },
    )


def _make_phantom_ok() -> AgentResult:
    return _ok(
        "phantom",
        {
            "total_annual_tax": 4200,
            "methodology_source": "Bristol PFRC",
            "components": {},
            "validation": {"in_range": True, "capped": False, "original_total": 4200},
        },
    )


def _make_truth_ok() -> AgentResult:
    return _ok("truth", {"passes": True, "recommendations": []})


def _make_generic_ok(name: str) -> AgentResult:
    return _ok(name, {"placeholder": True})


def _build_all_mocks() -> dict[str, MagicMock]:
    """Return a dict of mock agents keyed by name."""
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
    agents["parks"].execute.return_value = _make_parks_ok()
    agents["king"].execute.return_value = _make_king_ok()
    agents["phantom"].execute.return_value = _make_phantom_ok()
    agents["truth"].execute.return_value = _make_truth_ok()
    for n in ("robinson", "gray", "tubman", "lewis", "colvin"):
        agents[n].execute.return_value = _make_generic_ok(n)
    return agents


@pytest.fixture
def mock_agents():
    return _build_all_mocks()


@pytest.fixture
def mock_kevin():
    """Mock Kevin's 3 services."""
    assess = MagicMock()
    assess.assess.return_value = MagicMock(
        barrier_severity="high",
        barrier_details=[],
        readiness=MagicMock(score=35),
        dispute_pathway=MagicMock(steps=[], total_estimated_days=30),
    )
    dispute = MagicMock()
    dispute.generate_pathway.return_value = MagicMock(
        steps=[],
        total_estimated_days=30,
    )
    return {"assessment": assess, "dispute": dispute}


def _make_moses(mock_agents, mock_kevin):
    """Create a MosesAgent with injected mocks."""
    from modules.credit.agents.moses import MosesAgent

    agent = MosesAgent()
    agent._agents = mock_agents
    agent._assessment_svc = mock_kevin["assessment"]
    agent._dispute_svc = mock_kevin["dispute"]
    return agent


# ===========================================================================
# TestMosesExecution
# ===========================================================================


class TestMosesExecution:
    def test_all_agents_called(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        for name in (
            "parks",
            "king",
            "colvin",
            "robinson",
            "lewis",
            "phantom",
            "truth",
        ):
            assert mock_agents[name].execute.called, f"{name} not called"

    def test_execution_order(self, poor_profile_structured, mock_agents, mock_kevin):
        call_order = []
        for name, m in mock_agents.items():
            orig_rv = m.execute.return_value

            def _side(prof, _n=name, _rv=orig_rv, **kw):
                call_order.append(_n)
                return _rv

            m.execute.side_effect = _side
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        expected_base = [
            "parks",
            "king",
            "colvin",
            "robinson",
            "lewis",
            "phantom",
            "truth",
        ]
        actual_base = [n for n in call_order if n in expected_base]
        assert actual_base == expected_base

    def test_result_has_liberation_plan(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "liberation_plan" in result.data

    def test_reasoning_chain(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        chain = result.data["reasoning_chain"]
        assert isinstance(chain, list)
        assert len(chain) >= 7

    def test_conditional_gray_skipped(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured, context={})
        assert not mock_agents["gray"].execute.called

    def test_conditional_tubman_skipped(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured, context={})
        assert not mock_agents["tubman"].execute.called

    def test_gray_fires_with_denial(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        ctx = {"denial_context": {"reason": "too many collections"}}
        moses.execute(poor_profile_structured, context=ctx)
        assert mock_agents["gray"].execute.called

    def test_tubman_fires_with_bureaus(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        ctx = {"bureau_reports": {"experian": {}, "equifax": {}}}
        moses.execute(poor_profile_structured, context=ctx)
        assert mock_agents["tubman"].execute.called


# ===========================================================================
# TestMosesValidation
# ===========================================================================


class TestMosesValidation:
    def test_parks_validation_passes(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        lp = result.data["liberation_plan"]
        assert "situation" in lp

    def test_parks_validation_fails_fallback(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["parks"].execute.return_value = _ok("parks", {"bad": True})
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        lp = result.data["liberation_plan"]
        assert "situation" in lp  # fallback used

    def test_king_validation_passes(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        lp = result.data["liberation_plan"]
        assert "battle_plan" in lp

    def test_phantom_validation_range(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        assert 1500 <= tax.get("total_annual_tax", 0) <= 15000

    def test_phantom_out_of_range_fallback(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["phantom"].execute.return_value = _ok(
            "phantom",
            {
                "total_annual_tax": 0,
                "methodology_source": "Bristol PFRC",
            },
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        assert tax["total_annual_tax"] == 3500

    def test_phantom_fallback_has_methodology(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["phantom"].execute.return_value = _ok(
            "phantom",
            {
                "total_annual_tax": 0,
            },
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        assert "methodology_source" in tax


# ===========================================================================
# TestMosesFallbacks
# ===========================================================================


class TestMosesFallbacks:
    def test_phantom_fallback_is_3500(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["phantom"].execute.return_value = AgentResult(
            agent_name="phantom", status="error", errors=["boom"]
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        tax = result.data["liberation_plan"]["poverty_tax"]
        assert tax["total_annual_tax"] == 3500

    def test_king_fallback_has_phases(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["king"].execute.return_value = AgentResult(
            agent_name="king", status="error", errors=["boom"]
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        bp = result.data["liberation_plan"]["battle_plan"]
        assert "phases" in bp

    def test_parks_fallback_empty(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["boom"]
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        sit = result.data["liberation_plan"]["situation"]
        assert sit.get("doors_analysis") == []

    def test_fallback_details_tracked(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["boom"]
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        fb = result.data["validation_summary"]["fallback_details"]
        assert "parks" in fb

    def test_agents_fallback_count(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        mock_agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["boom"]
        )
        mock_agents["phantom"].execute.return_value = AgentResult(
            agent_name="phantom", status="error", errors=["bang"]
        )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["validation_summary"]["agents_fallback"] == 2

    def test_fallback_never_null(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        for name in ("parks", "king", "phantom"):
            mock_agents[name].execute.return_value = AgentResult(
                agent_name=name, status="error", errors=["fail"]
            )
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        lp = result.data["liberation_plan"]
        assert lp["situation"] is not None
        assert lp["battle_plan"] is not None
        assert lp["poverty_tax"] is not None


# ===========================================================================
# TestMosesCircuitBreaker
# ===========================================================================


class TestMosesCircuitBreaker:
    def test_circuit_opens_after_failures(self, poor_profile_structured, mock_kevin):
        agents = _build_all_mocks()
        agents["parks"].execute.return_value = AgentResult(
            agent_name="parks", status="error", errors=["fail"]
        )
        moses = _make_moses(agents, mock_kevin)
        # run 3 times to trip the breaker
        for _ in range(3):
            moses.execute(poor_profile_structured)
        cb = moses._breakers["parks"]
        assert cb.state == "open"

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


# ===========================================================================
# TestMosesDLQ
# ===========================================================================


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


# ===========================================================================
# TestMosesPerformance
# ===========================================================================


class TestMosesPerformance:
    def test_per_agent_ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        perf = result.data["performance"]["per_agent_ms"]
        assert "parks" in perf

    def test_total_time_ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["performance"]["total_time_ms"] >= 0

    def test_performance_in_output(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "performance" in result.data

    def test_under_100ms(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert result.data["performance"]["total_time_ms"] < 100


# ===========================================================================
# TestMosesOutput
# ===========================================================================


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
            assert key in vs, f"missing key: {key}"

    def test_compliance_section(self, poor_profile_structured, mock_agents, mock_kevin):
        moses = _make_moses(mock_agents, mock_kevin)
        result = moses.execute(poor_profile_structured)
        assert "compliance" in result.data

    def test_agent_registered(self):
        from modules.credit.agents.moses import MosesAgent  # noqa: F401
        from modules.credit.agents import list_agents

        assert "moses" in list_agents()


# ===========================================================================
# TestMosesContextPassing
# ===========================================================================


class TestMosesContextPassing:
    def test_parks_result_passed_to_king(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        king_call = mock_agents["king"].execute.call_args
        ctx = (
            king_call[1].get("context") or king_call[0][1]
            if len(king_call[0]) > 1
            else king_call[1].get("context", {})
        )
        assert "parks_result" in ctx

    def test_parks_result_passed_to_lewis(
        self, poor_profile_structured, mock_agents, mock_kevin
    ):
        moses = _make_moses(mock_agents, mock_kevin)
        moses.execute(poor_profile_structured)
        lewis_call = mock_agents["lewis"].execute.call_args
        ctx = (
            lewis_call[1].get("context") or lewis_call[0][1]
            if len(lewis_call[0]) > 1
            else lewis_call[1].get("context", {})
        )
        assert "parks_result" in ctx


class TestSharedResilienceState:
    """T25.3: create_wired_moses() should share breakers/DLQ/benchmark."""

    def test_two_moses_share_breakers_identity(self) -> None:
        """Two consecutive create_wired_moses() calls share the same breakers dict."""
        from modules.credit.agents import create_wired_moses

        m1 = create_wired_moses()
        m2 = create_wired_moses()
        assert m1._breakers is m2._breakers

    def test_breaker_tripped_persists_across_instances(self) -> None:
        """Breaker tripped in instance 1 stays open for instance 2."""
        from modules.credit.agents import create_wired_moses

        m1 = create_wired_moses()
        # Trip parks breaker
        for _ in range(3):
            m1._breakers["parks"].record_failure()
        assert m1._breakers["parks"].state == "open"

        m2 = create_wired_moses()
        assert m2._breakers["parks"].state == "open"
        # Reset for cleanup
        m1._breakers["parks"].reset()

    def test_dlq_shared_across_instances(self) -> None:
        """DLQ entries from instance 1 are visible in instance 2."""
        from modules.credit.agents import create_wired_moses

        m1 = create_wired_moses()
        m1._dlq.add(agent_name="test", error=Exception("test error"))
        assert m1._dlq.count == 1

        m2 = create_wired_moses()
        assert m2._dlq.count >= 1
        # Cleanup
        m1._dlq.drain()
