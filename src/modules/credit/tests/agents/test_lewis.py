"""Tests for Lewis (Impact Projector) agent."""

from __future__ import annotations


from modules.credit.agents.base import AgentResult
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    ScoreBand,
)


def _get_lewis():
    """Import and instantiate Lewis agent."""
    from modules.credit.agents.lewis import LewisAgent

    return LewisAgent()


def _run_lewis(profile: CreditProfile, context: dict | None = None) -> AgentResult:
    """Execute Lewis agent and assert success."""
    agent = _get_lewis()
    result = agent.execute(profile, context)
    assert result.status == "success"
    return result


# ---- Registration ----


class TestLewisRegistration:
    def test_agent_registered(self):
        """lewis should appear in the agent registry."""
        from modules.credit.agents import list_agents

        # Force import so the decorator fires
        import modules.credit.agents.lewis  # noqa: F401

        assert "lewis" in list_agents()

    def test_agent_name(self):
        agent = _get_lewis()
        assert agent.name == "lewis"


# ---- Projections ----


class TestLewisProjections:
    def test_current_score_matches_profile(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        proj = result.data["projections"]
        assert proj["current"]["score"] == 535

    def test_30_day_estimate(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        proj = result.data["projections"]
        assert proj["30_days"]["score"] == 550  # 535 + 15

    def test_90_day_estimate(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        proj = result.data["projections"]
        assert proj["90_days"]["score"] == 575  # 535 + 40

    def test_do_nothing_degrades(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        proj = result.data["projections"]
        assert proj["do_nothing"]["score"] == 530  # 535 - 5
        assert proj["do_nothing"]["score"] < poor_profile_structured.current_score

    def test_custom_simulation_result(self, poor_profile_structured):
        ctx = {"simulation_result": {30: 560, 90: 610}}
        result = _run_lewis(poor_profile_structured, context=ctx)
        proj = result.data["projections"]
        assert proj["30_days"]["score"] == 560
        assert proj["90_days"]["score"] == 610

    def test_scores_capped_at_850(self):
        profile = CreditProfile(
            current_score=830,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=10.0,
            account_summary=AccountSummary(
                total_accounts=10,
                open_accounts=8,
                total_balance=5000.0,
                total_credit_limit=50000.0,
            ),
            payment_history_pct=99.0,
            average_account_age_months=120,
            negative_items=[],
        )
        result = _run_lewis(profile)
        proj = result.data["projections"]
        # 830 + 40 = 870 but capped at 850
        assert proj["90_days"]["score"] <= 850
        assert proj["30_days"]["score"] <= 850


# ---- Life Outcomes ----


class TestLewisLifeOutcomes:
    def test_current_outcomes_for_535(self, poor_profile_structured):
        """Score 535 is below 580, so no LIFE_THRESHOLDS outcomes."""
        result = _run_lewis(poor_profile_structured)
        outcomes = result.data["projections"]["current"]["life_outcomes"]
        assert outcomes == []

    def test_90_day_outcomes_improved(self, poor_profile_structured):
        """Score 575 is still below 580, but with simulation at 610 we get outcomes."""
        ctx = {"simulation_result": {30: 560, 90: 610}}
        result = _run_lewis(poor_profile_structured, context=ctx)
        outcomes = result.data["projections"]["90_days"]["life_outcomes"]
        assert "Private rental without extra deposit" in outcomes
        assert "FHA mortgage eligible" in outcomes

    def test_all_outcomes_at_750(self):
        profile = CreditProfile(
            current_score=760,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=15.0,
            account_summary=AccountSummary(
                total_accounts=8,
                open_accounts=6,
                total_balance=3000.0,
                total_credit_limit=20000.0,
            ),
            payment_history_pct=99.0,
            average_account_age_months=72,
            negative_items=[],
        )
        result = _run_lewis(profile)
        outcomes = result.data["projections"]["current"]["life_outcomes"]
        # All thresholds met at 760
        assert "Best mortgage rates" in outcomes
        assert "FHA mortgage eligible" in outcomes
        assert "Prime auto loan rates" in outcomes

    def test_do_nothing_fewer_outcomes(self):
        """Score exactly at 580 -- do_nothing drops to 575, losing outcomes."""
        profile = CreditProfile(
            current_score=580,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=60.0,
            account_summary=AccountSummary(
                total_accounts=4,
                open_accounts=3,
                total_balance=3000.0,
                total_credit_limit=5000.0,
            ),
            payment_history_pct=75.0,
            average_account_age_months=24,
            negative_items=[],
        )
        result = _run_lewis(profile)
        current_outcomes = result.data["projections"]["current"]["life_outcomes"]
        do_nothing_outcomes = result.data["projections"]["do_nothing"]["life_outcomes"]
        assert len(do_nothing_outcomes) < len(current_outcomes)


# ---- Jobs ----


class TestLewisJobs:
    def test_jobs_at_535(self, poor_profile_structured):
        """Score 535 only meets threshold 0 -- basic jobs."""
        result = _run_lewis(poor_profile_structured)
        jobs = result.data["projections"]["current"]["accessible_jobs"]
        assert "food_service" in jobs
        assert "retail" in jobs
        assert "manufacturing" in jobs
        # Should NOT include 580-level jobs
        assert "healthcare_cna" not in jobs

    def test_jobs_at_650(self):
        profile = CreditProfile(
            current_score=650,
            score_band=ScoreBand.FAIR,
            overall_utilization=40.0,
            account_summary=AccountSummary(
                total_accounts=6,
                open_accounts=4,
                total_balance=6000.0,
                total_credit_limit=15000.0,
            ),
            payment_history_pct=90.0,
            average_account_age_months=36,
            negative_items=[],
        )
        result = _run_lewis(profile)
        jobs = result.data["projections"]["current"]["accessible_jobs"]
        assert "finance_banking" in jobs
        assert "government_federal" in jobs

    def test_jobs_list_grows(self, poor_profile_structured):
        """90-day projected score should unlock more jobs than current."""
        ctx = {"simulation_result": {30: 560, 90: 620}}
        result = _run_lewis(poor_profile_structured, context=ctx)
        current_jobs = result.data["projections"]["current"]["accessible_jobs"]
        ninety_jobs = result.data["projections"]["90_days"]["accessible_jobs"]
        assert len(ninety_jobs) > len(current_jobs)


# ---- Annual Savings ----


class TestLewisAnnualSavings:
    def test_30_day_savings_calculated(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        savings = result.data["annual_savings"]["30_day_plan"]
        assert "total" in savings
        assert isinstance(savings["total"], (int, float))

    def test_90_day_savings_calculated(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        savings_30 = result.data["annual_savings"]["30_day_plan"]["total"]
        savings_90 = result.data["annual_savings"]["90_day_plan"]["total"]
        # 90-day savings should be >= 30-day savings
        assert savings_90 >= savings_30

    def test_savings_components(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        for plan_key in ("30_day_plan", "90_day_plan"):
            plan = result.data["annual_savings"][plan_key]
            assert "insurance" in plan
            assert "auto" in plan
            assert "total" in plan

    def test_savings_non_negative(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        for plan_key in ("30_day_plan", "90_day_plan"):
            plan = result.data["annual_savings"][plan_key]
            assert plan["insurance"] >= 0
            assert plan["auto"] >= 0
            assert plan["total"] >= 0


# ---- New Doors ----


class TestLewisNewDoors:
    def test_new_doors_by_30_days(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        new_doors = result.data["new_doors"]
        assert "by_30_days" in new_doors
        assert isinstance(new_doors["by_30_days"], list)

    def test_new_doors_by_90_days(self, poor_profile_structured):
        """With simulation pushing to 610, doors open at 580."""
        ctx = {"simulation_result": {30: 560, 90: 610}}
        result = _run_lewis(poor_profile_structured, context=ctx)
        new_doors = result.data["new_doors"]
        assert "by_90_days" in new_doors
        assert isinstance(new_doors["by_90_days"], list)
        # Score goes from 535 to 610, passing 580 threshold
        assert "Private rental without extra deposit" in new_doors["by_90_days"]


# ---- Motivational Message ----


class TestLewisMotivation:
    def test_motivational_message_present(self, poor_profile_structured):
        result = _run_lewis(poor_profile_structured)
        msg = result.data["motivational_message"]
        assert isinstance(msg, str)
        assert len(msg) > 0
