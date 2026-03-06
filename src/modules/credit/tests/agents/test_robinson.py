"""Tests for Robinson (Door Finder) agent — free credit-building opportunities."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from modules.credit.agents.base import AgentResult, load_config
from modules.credit.agents.robinson import RobinsonAgent
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    ScoreBand,
)


@pytest.fixture
def agent() -> RobinsonAgent:
    return RobinsonAgent()


@pytest.fixture
def result(agent: RobinsonAgent, poor_profile_structured: CreditProfile) -> AgentResult:
    return agent.execute(poor_profile_structured)


@pytest.fixture
def thin_profile() -> CreditProfile:
    """Profile with only 2 accounts and 6 months average age."""
    return CreditProfile(
        current_score=620,
        score_band=ScoreBand.POOR,
        overall_utilization=25.0,
        account_summary=AccountSummary(
            total_accounts=2,
            open_accounts=2,
            total_balance=500.0,
            total_credit_limit=2000.0,
            monthly_payments=50.0,
        ),
        payment_history_pct=100.0,
        average_account_age_months=6,
        negative_items=[],
    )


@pytest.fixture
def normal_profile() -> CreditProfile:
    """Profile with good accounts, low utilization, not thin."""
    return CreditProfile(
        current_score=700,
        score_band=ScoreBand.GOOD,
        overall_utilization=20.0,
        account_summary=AccountSummary(
            total_accounts=8,
            open_accounts=6,
            total_balance=4000.0,
            total_credit_limit=20000.0,
            monthly_payments=200.0,
        ),
        payment_history_pct=97.0,
        average_account_age_months=48,
        negative_items=[],
    )


class TestRobinsonOpportunities:
    """Verify service loading, ordering, and eligibility flags."""

    def test_free_services_first(self, result: AgentResult) -> None:
        """Free services (cost=0) should appear before paid ones."""
        opps = result.data["opportunities"]
        first_paid_idx = None
        for i, svc in enumerate(opps):
            if svc["cost"] > 0:
                first_paid_idx = i
                break
        # All items before first_paid_idx must be free
        if first_paid_idx is not None:
            for svc in opps[:first_paid_idx]:
                assert svc["cost"] == 0

    def test_all_services_returned(self, result: AgentResult) -> None:
        """All services from the config file should be present."""
        config = load_config("alternative_services")
        expected_count = len(config["services"])
        assert len(result.data["opportunities"]) == expected_count

    def test_sorted_by_impact_within_free(self, result: AgentResult) -> None:
        """Within free group, sorted by max impact_points descending."""
        opps = result.data["opportunities"]
        free_services = [s for s in opps if s["cost"] == 0]
        max_impacts = [s["impact_points"]["max"] for s in free_services]
        assert max_impacts == sorted(max_impacts, reverse=True)

    def test_eligibility_flags(self, result: AgentResult) -> None:
        """Each service must have an 'eligible' boolean field."""
        for svc in result.data["opportunities"]:
            assert "eligible" in svc
            assert isinstance(svc["eligible"], bool)

    def test_service_structure(self, result: AgentResult) -> None:
        """Each service has required fields: name, type, cost, impact_points, how."""
        required = {"name", "type", "cost", "impact_points", "how"}
        for svc in result.data["opportunities"]:
            assert required.issubset(svc.keys()), f"Missing keys in {svc['name']}"


class TestRobinsonFreeStack:
    """Verify free stack construction."""

    def test_free_stack_has_3_actions(self, result: AgentResult) -> None:
        """Free stack should contain exactly 3 actions."""
        assert len(result.data["free_stack"]["actions"]) == 3

    def test_combined_impact_calculated(self, result: AgentResult) -> None:
        """Combined impact min/max should be sums of top-3 free service impacts."""
        stack = result.data["free_stack"]
        actions = stack["actions"]
        expected_min = sum(a["impact_points"]["min"] for a in actions)
        expected_max = sum(a["impact_points"]["max"] for a in actions)
        assert stack["combined_impact"]["min"] == expected_min
        assert stack["combined_impact"]["max"] == expected_max

    def test_free_stack_cost_is_zero(self, result: AgentResult) -> None:
        """Free stack cost field must be '$0'."""
        assert result.data["free_stack"]["cost"] == "$0"


class TestRobinsonThinFile:
    """Verify thin file detection logic."""

    def test_not_thin_file(
        self, agent: RobinsonAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """Maria: 5 accounts + 18 months average age = NOT thin."""
        res = agent.execute(poor_profile_structured)
        assert res.data["is_thin_file"] is False

    def test_thin_file_low_accounts(
        self, agent: RobinsonAgent, thin_profile: CreditProfile
    ) -> None:
        """< 3 total accounts = thin file."""
        res = agent.execute(thin_profile)
        assert res.data["is_thin_file"] is True

    def test_thin_file_young_history(self, agent: RobinsonAgent) -> None:
        """< 12 months average account age = thin file."""
        profile = CreditProfile(
            current_score=650,
            score_band=ScoreBand.FAIR,
            overall_utilization=30.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=4,
                total_balance=2000.0,
                total_credit_limit=8000.0,
                monthly_payments=100.0,
            ),
            payment_history_pct=95.0,
            average_account_age_months=8,
            negative_items=[],
        )
        res = agent.execute(profile)
        assert res.data["is_thin_file"] is True


class TestRobinsonResources:
    """Verify local resources are included."""

    def test_local_resources_included(self, result: AgentResult) -> None:
        """Resources from montgomery_resources.json should be present."""
        config = load_config("montgomery_resources")
        expected_count = len(config["resources"])
        assert len(result.data["local_resources"]) == expected_count

    def test_resource_structure(self, result: AgentResult) -> None:
        """Each resource must have name, phone, and services."""
        required = {"name", "phone", "services"}
        for res in result.data["local_resources"]:
            assert required.issubset(res.keys()), f"Missing keys in {res['name']}"


class TestRobinsonRecommendation:
    """Verify recommendation text based on profile."""

    def test_high_utilization_recommendation(
        self, agent: RobinsonAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """82% utilization should trigger utilization-specific recommendation."""
        res = agent.execute(poor_profile_structured)
        assert "paying down balances" in res.data["recommendation"].lower()

    def test_default_recommendation(
        self, agent: RobinsonAgent, normal_profile: CreditProfile
    ) -> None:
        """Normal profile should get default recommendation."""
        res = agent.execute(normal_profile)
        assert "good habits" in res.data["recommendation"].lower()


class TestRobinsonBrightData:
    """Verify Bright Data integration stub."""

    def test_no_api_key_returns_static(
        self, agent: RobinsonAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """Without BRIGHT_DATA_API_KEY, jobs should indicate static source."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRIGHT_DATA_API_KEY", None)
            res = agent.execute(poor_profile_structured)
        jobs = res.data["jobs"]
        assert jobs["live_data"] is False
        assert jobs["source"] == "static"

    def test_with_api_key_still_static(
        self, agent: RobinsonAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """With BRIGHT_DATA_API_KEY set, still static for now (Block 6)."""
        with patch.dict(os.environ, {"BRIGHT_DATA_API_KEY": "test-key"}):
            res = agent.execute(poor_profile_structured)
        jobs = res.data["jobs"]
        assert jobs["live_data"] is False
        assert jobs["source"] == "static"


class TestRobinsonMeta:
    """Verify agent metadata and registration."""

    def test_agent_name(self, agent: RobinsonAgent) -> None:
        assert agent.name == "robinson"

    def test_agent_description(self, agent: RobinsonAgent) -> None:
        assert "door" in agent.description.lower() or "opportunit" in agent.description.lower()

    def test_result_status_success(self, result: AgentResult) -> None:
        assert result.status == "success"
        assert result.agent_name == "robinson"
