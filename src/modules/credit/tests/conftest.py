"""Shared fixtures for credit module tests."""

import pytest

from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    ScoreBand,
)


@pytest.fixture
def good_credit_profile() -> CreditProfile:
    """Score=740, no negatives, 20% utilization."""
    return CreditProfile(
        current_score=740,
        score_band=ScoreBand.GOOD,
        overall_utilization=20.0,
        account_summary=AccountSummary(
            total_accounts=8,
            open_accounts=6,
            closed_accounts=2,
            negative_accounts=0,
            collection_accounts=0,
            total_balance=8000.0,
            total_credit_limit=40000.0,
            monthly_payments=350.0,
        ),
        payment_history_pct=98.0,
        average_account_age_months=72,
        negative_items=[],
    )


@pytest.fixture
def poor_credit_profile() -> CreditProfile:
    """Score=520, 3 collections, 85% utilization."""
    return CreditProfile(
        current_score=520,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=85.0,
        account_summary=AccountSummary(
            total_accounts=12,
            open_accounts=5,
            closed_accounts=7,
            negative_accounts=5,
            collection_accounts=3,
            total_balance=42500.0,
            total_credit_limit=50000.0,
            monthly_payments=1200.0,
        ),
        payment_history_pct=62.0,
        average_account_age_months=48,
        negative_items=[
            "collection_medical_2500",
            "collection_utility_800",
            "collection_credit_card_5000",
        ],
    )


@pytest.fixture
def fair_credit_profile() -> CreditProfile:
    """Score=650, 1 negative, 45% utilization."""
    return CreditProfile(
        current_score=650,
        score_band=ScoreBand.FAIR,
        overall_utilization=45.0,
        account_summary=AccountSummary(
            total_accounts=6,
            open_accounts=4,
            closed_accounts=2,
            negative_accounts=1,
            collection_accounts=0,
            total_balance=13500.0,
            total_credit_limit=30000.0,
            monthly_payments=450.0,
        ),
        payment_history_pct=88.0,
        average_account_age_months=36,
        negative_items=["late_payment_30day"],
    )


@pytest.fixture
def thin_file_profile() -> CreditProfile:
    """Score=620, 2 accounts, no negatives."""
    return CreditProfile(
        current_score=620,
        score_band=ScoreBand.POOR,
        overall_utilization=30.0,
        account_summary=AccountSummary(
            total_accounts=2,
            open_accounts=2,
            closed_accounts=0,
            negative_accounts=0,
            collection_accounts=0,
            total_balance=1500.0,
            total_credit_limit=5000.0,
            monthly_payments=75.0,
        ),
        payment_history_pct=100.0,
        average_account_age_months=8,
        negative_items=[],
    )
