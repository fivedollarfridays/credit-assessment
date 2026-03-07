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
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Medical collection - $1,200",
                amount=1200.0,
                creditor="ABC Collections",
            ),
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Phone bill collection - $450",
                amount=450.0,
                creditor="XYZ Recovery",
            ),
        ],
    )


@pytest.fixture
def profile_with_mixed_items() -> CreditProfile:
    """Profile with collection, charge-off, and late payment."""
    return CreditProfile(
        current_score=535,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=80.0,
        account_summary=AccountSummary(
            total_accounts=6,
            open_accounts=3,
            negative_accounts=3,
            collection_accounts=1,
            total_balance=5000.0,
            total_credit_limit=6000.0,
            monthly_payments=200.0,
        ),
        payment_history_pct=60.0,
        average_account_age_months=24,
        negative_items=[
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Medical debt collection",
                amount=1500.0,
                creditor="ABC Collections",
            ),
            NegativeItem(
                type=NegativeItemType.CHARGE_OFF,
                description="Credit card charge off",
                amount=3000.0,
                creditor="Big Bank",
            ),
            NegativeItem(
                type=NegativeItemType.LATE_PAYMENT,
                description="30 day late payment",
                amount=0.0,
                creditor="Utility Co",
            ),
        ],
    )


@pytest.fixture
def no_negative_profile() -> CreditProfile:
    """Profile with no negative items."""
    return CreditProfile(
        current_score=720,
        score_band=ScoreBand.GOOD,
        overall_utilization=20.0,
        account_summary=AccountSummary(
            total_accounts=5,
            open_accounts=4,
        ),
        payment_history_pct=98.0,
        average_account_age_months=60,
        negative_items=[],
    )
