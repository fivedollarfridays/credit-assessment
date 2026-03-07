"""Tests for input validation hardening (H-1, H-2, H-3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# H-1: SimpleCreditProfile.negative_items bounds
# ---------------------------------------------------------------------------


class TestSimpleCreditProfileBounds:
    """Validate max_length on SimpleCreditProfile.negative_items."""

    def _make_profile(self, **overrides):
        from modules.credit.assess_routes import SimpleCreditProfile

        defaults = {
            "credit_score": 600,
            "utilization_percent": 30.0,
            "total_accounts": 5,
            "open_accounts": 3,
            "payment_history_percent": 90.0,
            "oldest_account_months": 24,
        }
        defaults.update(overrides)
        return SimpleCreditProfile(**defaults)

    def test_accepts_50_items(self) -> None:
        items = [f"item {i}" for i in range(50)]
        profile = self._make_profile(negative_items=items)
        assert len(profile.negative_items) == 50

    def test_rejects_51_items(self) -> None:
        items = [f"item {i}" for i in range(51)]
        with pytest.raises(ValidationError):
            self._make_profile(negative_items=items)

    def test_rejects_overlong_string(self) -> None:
        items = ["x" * 201]
        with pytest.raises(ValidationError):
            self._make_profile(negative_items=items)

    def test_accepts_200_char_string(self) -> None:
        items = ["x" * 200]
        profile = self._make_profile(negative_items=items)
        assert len(profile.negative_items[0]) == 200


# ---------------------------------------------------------------------------
# H-2: LiberateRequest / CompareBureausRequest bureau_reports bounds
# ---------------------------------------------------------------------------


class TestBureauReportsBounds:
    """Validate bureau_reports dict size cap."""

    def _make_profile(self):
        from modules.credit.types import CreditProfile, AccountSummary, ScoreBand

        return CreditProfile(
            current_score=535,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=82.0,
            account_summary=AccountSummary(
                total_accounts=5,
                open_accounts=3,
                total_balance=4200.0,
                total_credit_limit=5100.0,
                monthly_payments=180.0,
            ),
            payment_history_pct=68.0,
            average_account_age_months=18,
            negative_items=[],
        )

    def test_accepts_3_bureaus(self) -> None:
        from modules.credit.liberate_routes import CompareBureausRequest

        profile = self._make_profile()
        req = CompareBureausRequest(
            profile=profile,
            bureau_reports={"Experian": {}, "Equifax": {}, "TransUnion": {}},
        )
        assert len(req.bureau_reports) == 3

    def test_rejects_6_bureaus(self) -> None:
        from modules.credit.liberate_routes import CompareBureausRequest

        profile = self._make_profile()
        reports = {f"bureau_{i}": {} for i in range(6)}
        with pytest.raises(ValidationError):
            CompareBureausRequest(profile=profile, bureau_reports=reports)


# ---------------------------------------------------------------------------
# H-3: audit_log limit parameter bounds
# ---------------------------------------------------------------------------


class TestAuditLogLimitBounds:
    """Validate that audit_log limit uses Query bounds."""

    def test_limit_has_query_bounds(self) -> None:
        """The limit parameter should have ge=1, le=500 bounds."""
        import inspect
        from fastapi.params import Query as QueryParam
        from modules.credit.admin_routes import audit_log

        sig = inspect.signature(audit_log)
        limit_param = sig.parameters["limit"]
        default = limit_param.default
        assert isinstance(default, QueryParam), "limit should use Query()"
        # FastAPI stores metadata on the field_info
        metadata = default.metadata
        ge_found = any(getattr(m, "ge", None) == 1 for m in metadata)
        le_found = any(getattr(m, "le", None) == 500 for m in metadata)
        assert ge_found, "limit should have ge=1"
        assert le_found, "limit should have le=500"
