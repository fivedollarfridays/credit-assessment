"""Tests for Phantom (Poverty Tax Calculator) agent."""

from __future__ import annotations

import pytest

from modules.credit.agents.base import AgentResult, load_config
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


# ---- Fixtures ----


@pytest.fixture
def excellent_profile() -> CreditProfile:
    """Score 780, low balance, no negatives."""
    return CreditProfile(
        current_score=780,
        score_band=ScoreBand.EXCELLENT,
        overall_utilization=15.0,
        account_summary=AccountSummary(
            total_accounts=8,
            open_accounts=6,
            collection_accounts=0,
            total_balance=3000.0,
            total_credit_limit=20000.0,
        ),
        payment_history_pct=99.0,
        average_account_age_months=72,
        negative_items=[],
    )


@pytest.fixture
def fair_profile() -> CreditProfile:
    """Score 650, moderate balance."""
    return CreditProfile(
        current_score=650,
        score_band=ScoreBand.FAIR,
        overall_utilization=45.0,
        account_summary=AccountSummary(
            total_accounts=6,
            open_accounts=4,
            collection_accounts=0,
            total_balance=13500.0,
            total_credit_limit=30000.0,
        ),
        payment_history_pct=88.0,
        average_account_age_months=36,
        negative_items=[],
    )


@pytest.fixture
def lowest_band_profile() -> CreditProfile:
    """Score 400, high balance, collections."""
    return CreditProfile(
        current_score=400,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=90.0,
        account_summary=AccountSummary(
            total_accounts=8,
            open_accounts=3,
            collection_accounts=3,
            total_balance=25000.0,
            total_credit_limit=28000.0,
        ),
        payment_history_pct=50.0,
        average_account_age_months=24,
        negative_items=[
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Medical $5000",
                amount=5000.0,
            ),
            NegativeItem(
                type=NegativeItemType.COLLECTION, description="CC $8000", amount=8000.0
            ),
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Utility $500",
                amount=500.0,
            ),
        ],
    )


@pytest.fixture
def zero_balance_profile() -> CreditProfile:
    """Score 535, but $0 balance."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=0.0,
        account_summary=AccountSummary(
            total_accounts=3,
            open_accounts=2,
            collection_accounts=0,
            total_balance=0.0,
            total_credit_limit=2000.0,
        ),
        payment_history_pct=70.0,
        average_account_age_months=12,
        negative_items=[],
    )


def _get_phantom():
    """Import and instantiate Phantom agent."""
    from modules.credit.agents.phantom import PhantomAgent

    return PhantomAgent()


def _run_phantom(profile: CreditProfile, context: dict | None = None) -> AgentResult:
    """Execute Phantom agent and assert success."""
    agent = _get_phantom()
    result = agent.execute(profile, context)
    assert result.status == "success"
    return result


# ---- TestPhantomScoreBand ----


class TestPhantomScoreBand:
    def test_score_535_maps_to_500_549(self):
        from modules.credit.agents.scoring import score_to_band

        assert score_to_band(535) == "500-549"

    def test_score_750_maps_to_750_850(self):
        from modules.credit.agents.scoring import score_to_band

        assert score_to_band(750) == "750-850"

    def test_score_300_maps_to_300_499(self):
        from modules.credit.agents.scoring import score_to_band

        assert score_to_band(300) == "300-499"

    def test_score_650_maps_to_650_699(self):
        from modules.credit.agents.scoring import score_to_band

        assert score_to_band(650) == "650-699"


# ---- TestPhantomCreditPremium ----


class TestPhantomCreditPremium:
    def test_credit_premium_scaled_by_debt(self, poor_profile_structured):
        """$4200 balance -> cost * (4200/10000) = cost * 0.42."""
        result = _run_phantom(poor_profile_structured)
        credit = result.data["components"]["credit_premium"]
        config = load_config("poverty_tax_tables")
        band_cost = config["components"]["credit_premium"]["bands"]["500-549"][
            "annual_cost"
        ]
        expected = band_cost * (4200.0 / 10000.0)
        assert credit["annual_cost"] == pytest.approx(expected)

    def test_credit_premium_zero_for_excellent(self, excellent_profile):
        result = _run_phantom(excellent_profile)
        credit = result.data["components"]["credit_premium"]
        assert credit["annual_cost"] == 0.0

    def test_credit_premium_max_for_lowest(self, lowest_band_profile):
        """300-499 band has highest cost."""
        result = _run_phantom(lowest_band_profile)
        credit = result.data["components"]["credit_premium"]
        config = load_config("poverty_tax_tables")
        band_cost = config["components"]["credit_premium"]["bands"]["300-499"][
            "annual_cost"
        ]
        expected = band_cost * (25000.0 / 10000.0)
        assert credit["annual_cost"] == pytest.approx(expected)

    def test_credit_premium_no_debt_zero(self, zero_balance_profile):
        result = _run_phantom(zero_balance_profile)
        credit = result.data["components"]["credit_premium"]
        assert credit["annual_cost"] == 0.0


# ---- TestPhantomInsurance ----


class TestPhantomInsurance:
    def test_insurance_cost_for_535(self, poor_profile_structured):
        """500-549 band -> $2000."""
        result = _run_phantom(poor_profile_structured)
        ins = result.data["components"]["insurance_premium"]
        assert ins["annual_cost"] == 2000.0

    def test_insurance_zero_for_excellent(self, excellent_profile):
        result = _run_phantom(excellent_profile)
        ins = result.data["components"]["insurance_premium"]
        assert ins["annual_cost"] == 0.0

    def test_insurance_cost_matches_config(self, fair_profile):
        """650-699 band -> verify against config."""
        result = _run_phantom(fair_profile)
        ins = result.data["components"]["insurance_premium"]
        config = load_config("poverty_tax_tables")
        expected = config["components"]["insurance_premium"]["bands"]["650-699"][
            "annual_cost"
        ]
        assert ins["annual_cost"] == expected


# ---- TestPhantomEmployment ----


class TestPhantomEmployment:
    def test_default_industry_healthcare_cna(self, poor_profile_structured):
        """Default industry when not specified is healthcare_cna."""
        result = _run_phantom(poor_profile_structured)
        emp = result.data["components"]["employment_barrier"]
        assert emp["industry"] == "healthcare_cna"

    def test_custom_target_industry(self, poor_profile_structured):
        """Context overrides default industry."""
        result = _run_phantom(
            poor_profile_structured, {"target_industry": "finance_banking"}
        )
        emp = result.data["components"]["employment_barrier"]
        assert emp["industry"] == "finance_banking"

    def test_employment_cost_with_blocking(self, poor_profile_structured):
        """Score 535 with collections -> blocked from healthcare_admin."""
        result = _run_phantom(
            poor_profile_structured, {"target_industry": "healthcare_admin"}
        )
        emp = result.data["components"]["employment_barrier"]
        config = load_config("poverty_tax_tables")
        expected = config["components"]["employment_barrier"]["categories"][
            "healthcare_admin"
        ]["annual_loss"]
        assert emp["annual_cost"] == expected

    def test_employment_zero_when_not_blocked(self, excellent_profile):
        """780 score, no collections -> no employment barrier."""
        result = _run_phantom(excellent_profile)
        emp = result.data["components"]["employment_barrier"]
        assert emp["annual_cost"] == 0.0


# ---- TestPhantomHousing ----


class TestPhantomHousing:
    def test_housing_cost_for_535(self, poor_profile_structured):
        """500-549 band -> $2400."""
        result = _run_phantom(poor_profile_structured)
        housing = result.data["components"]["housing_premium"]
        assert housing["annual_cost"] == 2400.0

    def test_housing_zero_for_excellent(self, excellent_profile):
        result = _run_phantom(excellent_profile)
        housing = result.data["components"]["housing_premium"]
        assert housing["annual_cost"] == 0.0

    def test_housing_cost_matches_config(self, fair_profile):
        """650-699 band -> verify against config."""
        result = _run_phantom(fair_profile)
        housing = result.data["components"]["housing_premium"]
        config = load_config("poverty_tax_tables")
        expected = config["components"]["housing_premium"]["bands"]["650-699"][
            "annual_cost"
        ]
        assert housing["annual_cost"] == expected


# ---- TestPhantomTotal ----


class TestPhantomTotal:
    def test_total_is_sum_of_components(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        comps = result.data["components"]
        expected = (
            comps["credit_premium"]["annual_cost"]
            + comps["insurance_premium"]["annual_cost"]
            + comps["employment_barrier"]["annual_cost"]
            + comps["housing_premium"]["annual_cost"]
        )
        validation = result.data["validation"]
        assert validation["original_total"] == pytest.approx(expected)

    def test_total_capped_at_max(self, lowest_band_profile):
        """Extreme profile should not exceed 15000."""
        result = _run_phantom(lowest_band_profile)
        assert result.data["total_annual_tax"] <= 15000.0

    def test_total_floored_at_min(self, excellent_profile):
        """Excellent score -> components near zero, but floor at 1500."""
        result = _run_phantom(excellent_profile)
        assert result.data["total_annual_tax"] >= 1500.0

    def test_validation_flags(self, excellent_profile):
        """Excellent profile total < 1500, so should be capped up."""
        result = _run_phantom(excellent_profile)
        validation = result.data["validation"]
        assert validation["capped"] is True
        assert validation["in_range"] is False

    def test_maria_total_reasonable(self, poor_profile_structured):
        """Score 535 total should be in $3000-$8000 range."""
        result = _run_phantom(poor_profile_structured)
        total = result.data["total_annual_tax"]
        assert 3000 <= total <= 8000


# ---- TestPhantomKillPlan ----


class TestPhantomKillPlan:
    def test_kill_plan_sorted_by_savings(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        kill_plan = result.data["kill_plan"]
        for i in range(len(kill_plan) - 1):
            assert kill_plan[i]["annual_savings"] >= kill_plan[i + 1]["annual_savings"]

    def test_kill_plan_has_all_components(self, poor_profile_structured):
        result = _run_phantom(poor_profile_structured)
        kill_plan = result.data["kill_plan"]
        # Should have all 4 components (those with non-zero cost)
        assert len(kill_plan) >= 3  # at least 3 non-zero components

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


# ---- TestPhantomUrgency ----


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


# ---- TestPhantomWageComparison ----


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


# ---- TestPhantomRegistration ----


class TestPhantomRegistration:
    def test_agent_registered(self):
        # Importing the module triggers registration
        import modules.credit.agents.phantom  # noqa: F401
        from modules.credit.agents import _REGISTRY

        assert "phantom" in _REGISTRY
