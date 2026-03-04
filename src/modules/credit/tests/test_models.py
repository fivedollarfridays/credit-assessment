"""Tests for credit assessment Pydantic models — basic types."""

import pytest
from pydantic import ValidationError

from modules.credit.types import (
    AccountSummary,
    ActionPriority,
    BarrierSeverity,
    CreditBarrier,
    CreditProfile,
    CreditReadiness,
    DisputePathway,
    DisputeStep,
    ScoreBand,
    ScoreImpact,
)


class TestAccountSummary:
    """Tests for AccountSummary model."""

    def test_creates_with_defaults(self) -> None:
        summary = AccountSummary(total_accounts=5, open_accounts=3)
        assert summary.total_accounts == 5
        assert summary.open_accounts == 3
        assert summary.closed_accounts == 0
        assert summary.negative_accounts == 0
        assert summary.collection_accounts == 0
        assert summary.total_balance == 0.0
        assert summary.total_credit_limit == 0.0
        assert summary.monthly_payments == 0.0

    def test_creates_with_all_fields(self) -> None:
        summary = AccountSummary(
            total_accounts=10,
            open_accounts=7,
            closed_accounts=3,
            negative_accounts=2,
            collection_accounts=1,
            total_balance=15000.0,
            total_credit_limit=50000.0,
            monthly_payments=500.0,
        )
        assert summary.negative_accounts == 2
        assert summary.total_balance == 15000.0


class TestCreditProfile:
    """Tests for CreditProfile model."""

    def test_valid_score_at_lower_bound(self) -> None:
        profile = CreditProfile(
            current_score=300,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=50.0,
            account_summary=AccountSummary(total_accounts=1, open_accounts=1),
            payment_history_pct=80.0,
            average_account_age_months=12,
            negative_items=[],
        )
        assert profile.current_score == 300

    def test_valid_score_at_upper_bound(self) -> None:
        profile = CreditProfile(
            current_score=850,
            score_band=ScoreBand.EXCELLENT,
            overall_utilization=5.0,
            account_summary=AccountSummary(total_accounts=10, open_accounts=8),
            payment_history_pct=100.0,
            average_account_age_months=120,
            negative_items=[],
        )
        assert profile.current_score == 850

    def test_rejects_score_below_300(self) -> None:
        with pytest.raises(ValidationError):
            CreditProfile(
                current_score=299,
                score_band=ScoreBand.VERY_POOR,
                overall_utilization=50.0,
                account_summary=AccountSummary(total_accounts=1, open_accounts=1),
                payment_history_pct=80.0,
                average_account_age_months=12,
                negative_items=[],
            )

    def test_rejects_score_above_850(self) -> None:
        with pytest.raises(ValidationError):
            CreditProfile(
                current_score=851,
                score_band=ScoreBand.EXCELLENT,
                overall_utilization=5.0,
                account_summary=AccountSummary(total_accounts=10, open_accounts=8),
                payment_history_pct=100.0,
                average_account_age_months=120,
                negative_items=[],
            )

    def test_has_all_required_fields(self) -> None:
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=4),
            payment_history_pct=95.0,
            average_account_age_months=36,
            negative_items=[],
        )
        assert profile.current_score == 700
        assert profile.score_band == ScoreBand.GOOD
        assert profile.overall_utilization == 30.0
        assert profile.account_summary.total_accounts == 5
        assert profile.payment_history_pct == 95.0
        assert profile.average_account_age_months == 36
        assert profile.negative_items == []

    def test_negative_items_default_empty(self) -> None:
        profile = CreditProfile(
            current_score=700,
            score_band=ScoreBand.GOOD,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=4),
            payment_history_pct=95.0,
            average_account_age_months=36,
        )
        assert profile.negative_items == []


class TestScoreImpact:
    """Tests for ScoreImpact model."""

    def test_from_range_classmethod(self) -> None:
        impact = ScoreImpact.from_range(10, 30)
        assert impact.min_points == 10
        assert impact.max_points == 30
        assert impact.expected_points == 20

    def test_from_range_single_point(self) -> None:
        impact = ScoreImpact.from_range(5, 5)
        assert impact.expected_points == 5

    def test_creates_with_explicit_values(self) -> None:
        impact = ScoreImpact(min_points=5, max_points=15, expected_points=12)
        assert impact.min_points == 5
        assert impact.max_points == 15
        assert impact.expected_points == 12


class TestCreditBarrier:
    """Tests for CreditBarrier model."""

    def test_validates_with_required_fields(self) -> None:
        barrier = CreditBarrier(
            severity=BarrierSeverity.HIGH,
            description="Multiple collections on file",
        )
        assert barrier.severity == BarrierSeverity.HIGH
        assert barrier.description == "Multiple collections on file"
        assert barrier.affected_accounts == []
        assert barrier.estimated_resolution_days == 0

    def test_validates_with_all_fields(self) -> None:
        barrier = CreditBarrier(
            severity=BarrierSeverity.MEDIUM,
            description="High utilization",
            affected_accounts=["acct-001", "acct-002"],
            estimated_resolution_days=60,
        )
        assert len(barrier.affected_accounts) == 2
        assert barrier.estimated_resolution_days == 60


class TestCreditReadiness:
    """Tests for CreditReadiness model."""

    def test_validates_with_required_fields(self) -> None:
        readiness = CreditReadiness(
            score=75,
            fico_score=700,
            score_band="good",
        )
        assert readiness.score == 75
        assert readiness.fico_score == 700
        assert readiness.score_band == "good"
        assert readiness.factors == {}

    def test_validates_with_factors(self) -> None:
        readiness = CreditReadiness(
            score=85,
            fico_score=740,
            score_band="excellent",
            factors={"payment_history": 95.0, "utilization": 80.0},
        )
        assert readiness.factors["payment_history"] == 95.0

    def test_rejects_score_above_100(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(score=101, fico_score=700, score_band="good")

    def test_rejects_score_below_0(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(score=-1, fico_score=700, score_band="good")

    def test_rejects_fico_below_300(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(score=50, fico_score=299, score_band="very_poor")

    def test_rejects_fico_above_850(self) -> None:
        with pytest.raises(ValidationError):
            CreditReadiness(score=50, fico_score=851, score_band="excellent")


class TestDisputeStep:
    """Tests for DisputeStep model."""

    def test_validates_with_required_fields(self) -> None:
        step = DisputeStep(
            step_number=1,
            action="Send validation letter",
            description="Request debt validation from collector",
        )
        assert step.step_number == 1
        assert step.action == "Send validation letter"
        assert step.legal_basis is None
        assert step.estimated_days == 30
        assert step.priority == ActionPriority.MEDIUM

    def test_validates_with_all_fields(self) -> None:
        step = DisputeStep(
            step_number=2,
            action="File dispute",
            description="Dispute inaccurate reporting",
            legal_basis="FCRA 611",
            estimated_days=45,
            priority=ActionPriority.HIGH,
        )
        assert step.legal_basis == "FCRA 611"
        assert step.estimated_days == 45
        assert step.priority == ActionPriority.HIGH


class TestDisputePathway:
    """Tests for DisputePathway model."""

    def test_validates_with_defaults(self) -> None:
        pathway = DisputePathway()
        assert pathway.steps == []
        assert pathway.total_estimated_days == 0
        assert pathway.statutes_cited == []
        assert pathway.legal_theories == []

    def test_validates_with_steps(self) -> None:
        step = DisputeStep(
            step_number=1,
            action="Validate debt",
            description="Send validation letter",
        )
        pathway = DisputePathway(
            steps=[step],
            total_estimated_days=30,
            statutes_cited=["FCRA 611"],
            legal_theories=["fcra_611_reinvestigation"],
        )
        assert len(pathway.steps) == 1
        assert pathway.total_estimated_days == 30
        assert "FCRA 611" in pathway.statutes_cited
