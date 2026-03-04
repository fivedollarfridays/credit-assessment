"""Tests for input validation constraints — T5.1 TDD."""

import pytest
from pydantic import ValidationError

from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    ScoreBand,
)


class TestAccountSummaryValidation:
    """Validate AccountSummary rejects negative numeric fields."""

    def test_rejects_negative_total_accounts(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=-1, open_accounts=0)

    def test_rejects_negative_open_accounts(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=-1)

    def test_rejects_negative_closed_accounts(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, closed_accounts=-1)

    def test_rejects_negative_negative_accounts(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, negative_accounts=-1)

    def test_rejects_negative_collection_accounts(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, collection_accounts=-1)

    def test_rejects_negative_total_balance(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, total_balance=-100.0)

    def test_rejects_negative_total_credit_limit(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, total_credit_limit=-1.0)

    def test_rejects_negative_monthly_payments(self) -> None:
        with pytest.raises(ValidationError):
            AccountSummary(total_accounts=5, open_accounts=3, monthly_payments=-50.0)


class TestCreditProfileValidation:
    """Validate CreditProfile field constraints."""

    def _make_profile(self, **overrides):
        defaults = {
            "current_score": 700,
            "score_band": ScoreBand.GOOD,
            "overall_utilization": 30.0,
            "account_summary": AccountSummary(total_accounts=5, open_accounts=3),
            "payment_history_pct": 95.0,
            "average_account_age_months": 36,
        }
        defaults.update(overrides)
        return CreditProfile(**defaults)

    def test_rejects_negative_utilization(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(overall_utilization=-1.0)

    def test_rejects_utilization_above_100(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(overall_utilization=101.0)

    def test_accepts_utilization_at_zero(self) -> None:
        profile = self._make_profile(overall_utilization=0.0)
        assert profile.overall_utilization == 0.0

    def test_accepts_utilization_at_100(self) -> None:
        profile = self._make_profile(overall_utilization=100.0)
        assert profile.overall_utilization == 100.0

    def test_rejects_negative_payment_history(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(payment_history_pct=-1.0)

    def test_rejects_payment_history_above_100(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(payment_history_pct=101.0)

    def test_rejects_negative_account_age(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(average_account_age_months=-1)

    def test_rejects_account_age_above_1200(self) -> None:
        with pytest.raises(ValidationError):
            self._make_profile(average_account_age_months=1201)

    def test_accepts_account_age_at_zero(self) -> None:
        profile = self._make_profile(average_account_age_months=0)
        assert profile.average_account_age_months == 0

    def test_rejects_too_many_negative_items(self) -> None:
        items = [f"item_{i}" for i in range(51)]
        with pytest.raises(ValidationError):
            self._make_profile(negative_items=items)

    def test_accepts_50_negative_items(self) -> None:
        items = [f"item_{i}" for i in range(50)]
        profile = self._make_profile(negative_items=items)
        assert len(profile.negative_items) == 50

    def test_rejects_long_negative_item_string(self) -> None:
        long_item = "x" * 201
        with pytest.raises(ValidationError):
            self._make_profile(negative_items=[long_item])

    def test_accepts_200_char_negative_item(self) -> None:
        item = "x" * 200
        profile = self._make_profile(negative_items=[item])
        assert len(profile.negative_items[0]) == 200

    def test_rejects_mismatched_score_band(self) -> None:
        with pytest.raises(ValidationError, match="score_band"):
            self._make_profile(
                current_score=520,
                score_band=ScoreBand.EXCELLENT,
            )

    def test_accepts_matching_score_band(self) -> None:
        profile = self._make_profile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
        )
        assert profile.score_band == ScoreBand.VERY_POOR
