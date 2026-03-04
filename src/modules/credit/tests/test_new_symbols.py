"""Tests for T1.1 — ConfidenceLevel, EligibilityStatus, utilization thresholds."""

from modules.credit.types import (
    HIGH_UTILIZATION_THRESHOLD,
    MODERATE_UTILIZATION_THRESHOLD,
    ConfidenceLevel,
    EligibilityStatus,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_has_high_value(self) -> None:
        assert ConfidenceLevel.HIGH == "high"

    def test_has_medium_value(self) -> None:
        assert ConfidenceLevel.MEDIUM == "medium"

    def test_has_low_value(self) -> None:
        assert ConfidenceLevel.LOW == "low"

    def test_has_exactly_three_members(self) -> None:
        assert len(ConfidenceLevel) == 3


class TestEligibilityStatus:
    """Tests for EligibilityStatus enum."""

    def test_has_eligible_value(self) -> None:
        assert EligibilityStatus.ELIGIBLE == "eligible"

    def test_has_blocked_value(self) -> None:
        assert EligibilityStatus.BLOCKED == "blocked"

    def test_has_exactly_two_members(self) -> None:
        assert len(EligibilityStatus) == 2


class TestUtilizationThresholds:
    """Tests for utilization threshold constants."""

    def test_high_utilization_threshold_is_75(self) -> None:
        assert HIGH_UTILIZATION_THRESHOLD == 75.0

    def test_moderate_utilization_threshold_is_50(self) -> None:
        assert MODERATE_UTILIZATION_THRESHOLD == 50.0

    def test_moderate_below_high(self) -> None:
        assert MODERATE_UTILIZATION_THRESHOLD < HIGH_UTILIZATION_THRESHOLD
