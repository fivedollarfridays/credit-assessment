"""Tests for Parks (Barrier Breaker) agent."""

from __future__ import annotations

import pytest

from modules.credit.agents.base import AgentResult
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


@pytest.fixture
def excellent_profile() -> CreditProfile:
    """High-score profile with no collections."""
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
def no_collections_low_score() -> CreditProfile:
    """Low score but zero collections."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=82.0,
        account_summary=AccountSummary(
            total_accounts=5,
            open_accounts=3,
            collection_accounts=0,
            total_balance=4200.0,
            total_credit_limit=5100.0,
        ),
        payment_history_pct=68.0,
        average_account_age_months=18,
        negative_items=[],
    )


def _get_parks():
    """Import and instantiate Parks agent."""
    from modules.credit.agents.parks import ParksAgent

    return ParksAgent()


def _run_parks(profile: CreditProfile, context: dict | None = None) -> AgentResult:
    """Execute Parks agent and assert success."""
    agent = _get_parks()
    result = agent.execute(profile, context)
    assert result.status == "success"
    return result


# ---- Employment ----


class TestParksEmployment:
    def test_blocked_industries_with_collections(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        emp = result.data["life_barriers"]["employment"]
        by_name = {e["industry"]: e for e in emp}
        assert by_name["finance_banking"]["status"] == "blocked"
        assert by_name["healthcare_admin"]["status"] == "blocked"

    def test_accessible_industries_no_credit_check(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        emp = result.data["life_barriers"]["employment"]
        by_name = {e["industry"]: e for e in emp}
        assert by_name["food_service"]["status"] == "accessible"
        assert by_name["retail"]["status"] == "accessible"
        assert by_name["manufacturing"]["status"] == "accessible"

    def test_score_based_blocking(self, poor_profile_structured):
        """finance_banking has min_score 650, score 535 should be blocked."""
        result = _run_parks(poor_profile_structured)
        emp = result.data["life_barriers"]["employment"]
        by_name = {e["industry"]: e for e in emp}
        entry = by_name["finance_banking"]
        assert entry["status"] == "blocked"
        assert (
            "score" in entry["reason"].lower()
            or "collection" in entry["reason"].lower()
        )

    def test_no_collections_still_score_blocked(self, no_collections_low_score):
        """Even with 0 collections, score 535 < 650 blocks finance_banking."""
        result = _run_parks(no_collections_low_score)
        emp = result.data["life_barriers"]["employment"]
        by_name = {e["industry"]: e for e in emp}
        assert by_name["finance_banking"]["status"] == "blocked"

    def test_target_industries_filter(self, poor_profile_structured):
        ctx = {"target_industries": ["food_service", "retail"]}
        result = _run_parks(poor_profile_structured, context=ctx)
        emp = result.data["life_barriers"]["employment"]
        industries = {e["industry"] for e in emp}
        assert industries == {"food_service", "retail"}

    def test_all_accessible_high_score(self, excellent_profile):
        result = _run_parks(excellent_profile)
        emp = result.data["life_barriers"]["employment"]
        for entry in emp:
            assert entry["status"] == "accessible", (
                f"{entry['industry']} should be accessible"
            )

    def test_wage_included(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        emp = result.data["life_barriers"]["employment"]
        for entry in emp:
            assert "avg_wage" in entry, f"{entry['industry']} missing avg_wage"
            assert isinstance(entry["avg_wage"], (int, float))


# ---- Housing ----


class TestParksHousing:
    def test_section8_always_accessible(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        housing = result.data["life_barriers"]["housing"]
        by_type = {h["type"]: h for h in housing}
        assert by_type["section_8"]["status"] == "accessible"

    def test_private_rental_blocked_low_score(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        housing = result.data["life_barriers"]["housing"]
        by_type = {h["type"]: h for h in housing}
        assert by_type["private_rental"]["status"] == "blocked"

    def test_collections_block_private(self):
        """Score 620 meets min but collections still block private_rental."""
        profile = CreditProfile(
            current_score=620,
            score_band=ScoreBand.POOR,
            overall_utilization=40.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                collection_accounts=1,
                total_balance=2000.0,
                total_credit_limit=5000.0,
            ),
            payment_history_pct=85.0,
            average_account_age_months=24,
            negative_items=[
                NegativeItem(
                    type=NegativeItemType.COLLECTION,
                    description="Old debt",
                    amount=300.0,
                ),
            ],
        )
        result = _run_parks(profile)
        housing = result.data["life_barriers"]["housing"]
        by_type = {h["type"]: h for h in housing}
        assert by_type["private_rental"]["status"] == "blocked"

    def test_fha_blocked_low_score(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        housing = result.data["life_barriers"]["housing"]
        by_type = {h["type"]: h for h in housing}
        assert by_type["fha_mortgage"]["status"] == "blocked"


# ---- Auto & Insurance ----


class TestParksAutoInsurance:
    def test_auto_rate_for_535(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        auto = result.data["life_barriers"]["auto"]
        assert auto["current_band"] == "500-549"
        assert auto["apr"] == 21.0
        assert auto["monthly"] == 404.22

    def test_insurance_premium_for_535(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        ins = result.data["life_barriers"]["insurance"]
        assert ins["current_band"] == "500-549"
        assert ins["annual_premium"] == 3450

    def test_vs_best_calculations(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        auto = result.data["life_barriers"]["auto"]
        vs = auto["vs_best"]
        assert vs["apr_diff"] == pytest.approx(21.0 - 4.5)
        assert vs["monthly_diff"] == pytest.approx(404.22 - 279.65)
        annual_extra = (404.22 - 279.65) * 12
        assert vs["annual_extra"] == pytest.approx(annual_extra)

        ins = result.data["life_barriers"]["insurance"]
        assert ins["vs_best"] == 3450 - 1450


# ---- Doors ----


class TestParksDoors:
    def test_doors_analysis_structure(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        doors = result.data["doors_analysis"]
        assert isinstance(doors, list)
        for entry in doors:
            assert "threshold" in entry
            assert "new_doors" in entry
            assert "count" in entry

    def test_cheapest_door_for_535(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        cd = result.data["cheapest_door"]
        # First threshold above 535 that opens new doors
        assert cd["threshold"] >= 536
        assert cd["points_needed"] == cd["threshold"] - 535
        assert len(cd["new_doors"]) > 0

    def test_roi_sorted_by_value(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        roi = result.data["roi_per_door"]
        assert isinstance(roi, list)
        # Sorted by five_year_savings descending
        for i in range(len(roi) - 1):
            assert roi[i]["five_year_savings"] >= roi[i + 1]["five_year_savings"]

    def test_points_needed_calculation(self, poor_profile_structured):
        result = _run_parks(poor_profile_structured)
        cd = result.data["cheapest_door"]
        assert (
            cd["points_needed"]
            == cd["threshold"] - poor_profile_structured.current_score
        )


# ---- Edge Cases ----


class TestParksEdgeCases:
    def test_excellent_score_no_barriers(self, excellent_profile):
        result = _run_parks(excellent_profile)
        barriers = result.data["life_barriers"]

        # All employment accessible
        for e in barriers["employment"]:
            assert e["status"] == "accessible"

        # All housing accessible
        for h in barriers["housing"]:
            assert h["status"] == "accessible"

        # Auto: best band
        assert barriers["auto"]["current_band"] == "750-850"
        assert barriers["auto"]["vs_best"]["apr_diff"] == pytest.approx(0.0)

        # Insurance: best band
        assert barriers["insurance"]["current_band"] == "750-850"
        assert barriers["insurance"]["vs_best"] == 0

    def test_empty_negative_items(self, no_collections_low_score):
        result = _run_parks(no_collections_low_score)
        assert result.status == "success"
        # Government jobs only blocked by collections, not by score
        emp = result.data["life_barriers"]["employment"]
        by_name = {e["industry"]: e for e in emp}
        assert by_name["government_federal"]["status"] == "accessible"
