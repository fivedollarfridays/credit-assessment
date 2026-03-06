"""Shared fixtures for Baby INERTIA agent tests."""

from __future__ import annotations

import pytest

from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


@pytest.fixture
def poor_profile_structured() -> CreditProfile:
    """Maria example: score 535, CNA applicant, 2 collections."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=82.0,
        account_summary=AccountSummary(
            total_accounts=5,
            open_accounts=3,
            negative_accounts=2,
            collection_accounts=2,
            total_balance=4200.0,
            total_credit_limit=5100.0,
            monthly_payments=180.0,
        ),
        payment_history_pct=68.0,
        average_account_age_months=18,
        negative_items=[
            NegativeItem(type=NegativeItemType.COLLECTION, description="Medical collection - $1,200", amount=1200.0, creditor="ABC Collections"),
            NegativeItem(type=NegativeItemType.COLLECTION, description="Phone bill collection - $450", amount=450.0, creditor="XYZ Recovery"),
        ],
    )
