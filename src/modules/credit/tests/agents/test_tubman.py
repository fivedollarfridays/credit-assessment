"""Tests for Tubman (Underground Scout) agent -- cross-bureau discrepancy scanner."""

from __future__ import annotations

import pytest

from modules.credit.agents.base import AgentResult
from modules.credit.agents.tubman import Metro2FormatValidator, TubmanAgent
from modules.credit.types import CreditProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent() -> TubmanAgent:
    return TubmanAgent()


def _make_account(
    creditor: str = "ABC Bank",
    account_number: str = "****1234",
    balance: float = 2500,
    credit_limit: float = 5000,
    payment_status: str = "current",
    account_status: str = "open",
    date_opened: str = "2023-01-15",
    date_of_first_delinquency: str | None = None,
    account_type: str = "credit_card",
) -> dict:
    return {
        "creditor": creditor,
        "account_number": account_number,
        "balance": balance,
        "credit_limit": credit_limit,
        "payment_status": payment_status,
        "account_status": account_status,
        "date_opened": date_opened,
        "date_of_first_delinquency": date_of_first_delinquency,
        "account_type": account_type,
    }


def _two_bureau_context(
    experian_accounts: list[dict],
    equifax_accounts: list[dict],
) -> dict:
    return {
        "bureau_reports": {
            "experian": {"accounts": experian_accounts},
            "equifax": {"accounts": equifax_accounts},
        },
    }


# ---------------------------------------------------------------------------
# TestTubmanSkip
# ---------------------------------------------------------------------------


class TestTubmanSkip:
    """Agent must skip when bureau data is absent or insufficient."""

    def test_skipped_without_bureau_reports(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        result = agent.execute(poor_profile_structured, context=None)
        assert result.status == "skipped"

    def test_skipped_single_bureau(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = {
            "bureau_reports": {
                "experian": {"accounts": [_make_account()]},
            },
        }
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.status == "skipped"


# ---------------------------------------------------------------------------
# TestTubmanBalanceMismatch
# ---------------------------------------------------------------------------


class TestTubmanBalanceMismatch:
    """Balance mismatch detection across bureaus."""

    def test_balance_mismatch_detected(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500)],
            equifax_accounts=[_make_account(balance=2800)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.status == "success"
        discs = [d for d in result.data["discrepancies"] if d["type"] == "balance_mismatch"]
        assert len(discs) >= 1

    def test_balance_within_tolerance(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500)],
            equifax_accounts=[_make_account(balance=2550)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "balance_mismatch"]
        assert len(discs) == 0

    def test_percentage_tolerance(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """Large balance, small absolute diff but > 5% triggers mismatch."""
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=1000)],
            equifax_accounts=[_make_account(balance=1060)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "balance_mismatch"]
        assert len(discs) >= 1

    def test_mismatch_severity_and_recommended_bureau(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """Balance mismatch should be high severity; recommends bureau with higher balance."""
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500)],
            equifax_accounts=[_make_account(balance=2800)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "balance_mismatch"]
        assert discs[0]["severity"] == "high"
        assert discs[0]["recommended_dispute_bureau"] == "equifax"

    def test_multiple_mismatches(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(creditor="ABC Bank", account_number="****1234", balance=2500),
                _make_account(creditor="XYZ Lender", account_number="****5678", balance=10000),
            ],
            equifax_accounts=[
                _make_account(creditor="ABC Bank", account_number="****1234", balance=2800),
                _make_account(creditor="XYZ Lender", account_number="****5678", balance=12000),
            ],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "balance_mismatch"]
        assert len(discs) >= 2


# ---------------------------------------------------------------------------
# TestTubmanDateDiscrepancy
# ---------------------------------------------------------------------------


class TestTubmanDateDiscrepancy:
    """Date discrepancy detection across bureaus."""

    def test_dofd_mismatch_critical(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(date_of_first_delinquency="2022-01-15"),
            ],
            equifax_accounts=[
                _make_account(date_of_first_delinquency="2022-06-01"),
            ],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["field"] == "date_of_first_delinquency"]
        assert len(discs) >= 1
        assert discs[0]["severity"] == "critical"

    def test_date_opened_mismatch(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(date_opened="2022-01-15")],
            equifax_accounts=[_make_account(date_opened="2022-06-01")],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["field"] == "date_opened"]
        assert len(discs) >= 1

    def test_date_within_tolerance(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(date_opened="2023-01-15")],
            equifax_accounts=[_make_account(date_opened="2023-01-30")],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["field"] == "date_opened"]
        assert len(discs) == 0

    def test_null_vs_date(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(date_of_first_delinquency=None),
            ],
            equifax_accounts=[
                _make_account(date_of_first_delinquency="2022-06-01"),
            ],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["field"] == "date_of_first_delinquency"]
        assert len(discs) >= 1

    def test_both_null_no_discrepancy(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(date_of_first_delinquency=None),
            ],
            equifax_accounts=[
                _make_account(date_of_first_delinquency=None),
            ],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["field"] == "date_of_first_delinquency"]
        assert len(discs) == 0


# ---------------------------------------------------------------------------
# TestTubmanDuplicateAccount
# ---------------------------------------------------------------------------


class TestTubmanDuplicateAccount:
    """Duplicate account detection within a single bureau."""

    def test_duplicate_detected(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(creditor="ABC Bank", account_number="****1234"),
                _make_account(creditor="ABC Bank", account_number="****5678"),
            ],
            equifax_accounts=[_make_account()],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "duplicate_account"]
        assert len(discs) >= 1

    def test_different_creditors_no_duplicate(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(creditor="ABC Bank", account_number="****1234"),
                _make_account(creditor="XYZ Lender", account_number="****5678"),
            ],
            equifax_accounts=[_make_account()],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "duplicate_account"]
        assert len(discs) == 0

    def test_same_account_no_duplicate(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[
                _make_account(creditor="ABC Bank", account_number="****1234"),
                _make_account(creditor="ABC Bank", account_number="****1234"),
            ],
            equifax_accounts=[_make_account()],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "duplicate_account"]
        assert len(discs) == 0

    def test_mixed_file_risk_detected(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx: dict = {
            "bureau_reports": {
                "experian": {
                    "accounts": [_make_account()],
                    "personal_info": {"name": "Maria Garcia", "address": "123 Main St"},
                },
                "equifax": {
                    "accounts": [_make_account()],
                    "personal_info": {"name": "Maria R Garcia", "address": "456 Oak Ave"},
                },
            },
        }
        result = agent.execute(poor_profile_structured, context=ctx)
        discs = [d for d in result.data["discrepancies"] if d["type"] == "mixed_file_risk"]
        assert len(discs) >= 1


# ---------------------------------------------------------------------------
# TestTubmanAccountMatching
# ---------------------------------------------------------------------------


class TestTubmanAccountMatching:
    """Account matching logic across bureaus."""

    def test_match_by_creditor_and_number(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(creditor="ABC Bank", account_number="****1234", balance=3000)],
            equifax_accounts=[_make_account(creditor="ABC Bank", account_number="****1234", balance=3500)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["accounts_matched"] >= 1

    def test_case_insensitive_match(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(creditor="ABC Bank", account_number="****1234", balance=3000)],
            equifax_accounts=[_make_account(creditor="abc bank", account_number="****1234", balance=3500)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["accounts_matched"] >= 1

    def test_no_match_different_creditor(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(creditor="ABC Bank", account_number="****1234")],
            equifax_accounts=[_make_account(creditor="XYZ Lender", account_number="****1234")],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["accounts_matched"] == 0

    def test_partial_account_match(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        """Last 4 digits match should count as a match."""
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(creditor="ABC Bank", account_number="XXXX-1234", balance=3000)],
            equifax_accounts=[_make_account(creditor="ABC Bank", account_number="****1234", balance=3500)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["accounts_matched"] >= 1


# ---------------------------------------------------------------------------
# TestTubmanMetro2Validator
# ---------------------------------------------------------------------------


class TestTubmanMetro2Validator:
    """Metro2 format validator utility."""

    def test_validator_loads_positions(self) -> None:
        validator = Metro2FormatValidator()
        assert "account_type" in validator.field_positions
        assert validator.field_positions["account_type"]["start"] == 26

    def test_validator_codes_and_structure(self) -> None:
        validator = Metro2FormatValidator()
        codes = validator.field_positions["account_type"]["codes"]
        assert codes["18"] == "Credit Card"
        for field_name, pos in validator.field_positions.items():
            assert "start" in pos
            assert "end" in pos


# ---------------------------------------------------------------------------
# TestTubmanOutput
# ---------------------------------------------------------------------------


class TestTubmanOutput:
    """Output structure and sorting."""

    def test_severity_summary(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500, date_of_first_delinquency="2022-01-15")],
            equifax_accounts=[_make_account(balance=2800, date_of_first_delinquency="2022-06-01")],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        summary = result.data["severity_summary"]
        assert set(summary.keys()) == {"critical", "high", "medium", "low"}

    def test_sorted_by_severity(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500, date_of_first_delinquency="2022-01-15")],
            equifax_accounts=[_make_account(balance=2800, date_of_first_delinquency="2022-06-01")],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        discs = result.data["discrepancies"]
        for i in range(len(discs) - 1):
            assert severity_order[discs[i]["severity"]] <= severity_order[discs[i + 1]["severity"]]

    def test_total_discrepancies_count(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account(balance=2500)],
            equifax_accounts=[_make_account(balance=2800)],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["total_discrepancies"] == len(result.data["discrepancies"])

    def test_bureaus_compared(
        self, agent: TubmanAgent, poor_profile_structured: CreditProfile
    ) -> None:
        ctx = _two_bureau_context(
            experian_accounts=[_make_account()],
            equifax_accounts=[_make_account()],
        )
        result = agent.execute(poor_profile_structured, context=ctx)
        assert set(result.data["bureaus_compared"]) == {"experian", "equifax"}
