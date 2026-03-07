"""Extended Phantom tests — kill plan, urgency, wage comparison, registration."""

from __future__ import annotations

import pytest

from modules.credit.agents.base import AgentResult


def _run_phantom(profile, context=None) -> AgentResult:
    from modules.credit.agents.phantom import PhantomAgent

    agent = PhantomAgent()
    result = agent.execute(profile, context)
    assert result.status == "success"
    return result


class TestPhantomKillPlan:
    def test_kill_plan_sorted_by_savings(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        kill_plan = result.data["kill_plan"]
        for i in range(len(kill_plan) - 1):
            assert kill_plan[i]["annual_savings"] >= kill_plan[i + 1]["annual_savings"]

    def test_kill_plan_has_all_components(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        kill_plan = result.data["kill_plan"]
        assert len(kill_plan) >= 3

    def test_kill_plan_actions(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        kill_plan = result.data["kill_plan"]
        for item in kill_plan:
            assert "component" in item
            assert "annual_savings" in item
            assert "action" in item
            assert "priority" in item
            assert isinstance(item["action"], str)
            assert len(item["action"]) > 0


class TestPhantomUrgency:
    def test_cost_per_day(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        total = result.data["total_annual_tax"]
        urgency = result.data["urgency"]
        assert urgency["cost_per_day"] == pytest.approx(total / 365, rel=1e-2)

    def test_cost_per_week(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        total = result.data["total_annual_tax"]
        urgency = result.data["urgency"]
        assert urgency["cost_per_week"] == pytest.approx(total / 52, rel=1e-2)

    def test_cost_per_month(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        total = result.data["total_annual_tax"]
        urgency = result.data["urgency"]
        assert urgency["cost_per_month"] == pytest.approx(total / 12, rel=1e-2)


class TestPhantomWageComparison:
    def test_poverty_tax_per_hour(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        total = result.data["total_annual_tax"]
        wage = result.data["wage_comparison"]
        assert wage["poverty_tax_per_hour"] == pytest.approx(total / 2080, rel=1e-2)

    def test_tax_as_pct_of_minimum(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        wage = result.data["wage_comparison"]
        expected_pct = wage["poverty_tax_per_hour"] / 7.25
        assert wage["tax_as_pct_of_minimum"] == pytest.approx(expected_pct, rel=1e-2)


class TestPhantomRegistration:
    def test_agent_registered(self):
        import modules.credit.agents.phantom  # noqa: F401
        from modules.credit.agents import list_agents

        assert "phantom" in list_agents()
