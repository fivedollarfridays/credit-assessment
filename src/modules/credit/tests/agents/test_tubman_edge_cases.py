"""Coverage tests for Tubman edge cases — None returns, dedup skips, unknown codes."""

from __future__ import annotations

from modules.credit.agents.tubman import (
    Metro2FormatValidator,
    _check_balance_mismatch,
    _check_date_field,
    _detect_duplicates,
    _field_rule,
    _parse_date,
)


# ---------------------------------------------------------------------------
# TestFieldRuleNotFound — tubman.py:29
# ---------------------------------------------------------------------------


class TestFieldRuleNotFound:
    """_field_rule returns None when no matching field name exists."""

    def test_returns_none_for_missing_field(self) -> None:
        fields = [{"name": "balance"}, {"name": "date_opened"}]
        assert _field_rule(fields, "nonexistent_field") is None

    def test_returns_none_for_empty_list(self) -> None:
        assert _field_rule([], "balance") is None


# ---------------------------------------------------------------------------
# TestCheckBalanceNone — tubman.py:72
# ---------------------------------------------------------------------------


class TestCheckBalanceNone:
    """_check_balance_mismatch returns None when a balance is None."""

    def test_returns_none_when_bal_a_is_none(self) -> None:
        acct_a = {"creditor": "Test", "balance": None}
        acct_b = {"creditor": "Test", "balance": 1000}
        rule = {"tolerance_abs": 100, "tolerance_pct": 5, "severity": "high"}
        assert _check_balance_mismatch(acct_a, acct_b, "bu_a", "bu_b", rule) is None

    def test_returns_none_when_bal_b_is_none(self) -> None:
        acct_a = {"creditor": "Test", "balance": 1000}
        acct_b = {"creditor": "Test"}
        rule = {"tolerance_abs": 100, "tolerance_pct": 5, "severity": "high"}
        assert _check_balance_mismatch(acct_a, acct_b, "bu_a", "bu_b", rule) is None

    def test_returns_none_when_both_none(self) -> None:
        acct_a = {"creditor": "Test"}
        acct_b = {"creditor": "Test"}
        rule = {"tolerance_abs": 100, "tolerance_pct": 5, "severity": "high"}
        assert _check_balance_mismatch(acct_a, acct_b, "bu_a", "bu_b", rule) is None


# ---------------------------------------------------------------------------
# TestParseDateNone — tubman.py:103, 106-107
# ---------------------------------------------------------------------------


class TestParseDateNone:
    """_parse_date returns None for None input and invalid date strings."""

    def test_returns_none_for_none_input(self) -> None:
        assert _parse_date(None) is None

    def test_returns_none_for_invalid_format(self) -> None:
        assert _parse_date("not-a-date") is None

    def test_returns_none_for_wrong_format(self) -> None:
        assert _parse_date("01/15/2023") is None


# ---------------------------------------------------------------------------
# TestCheckDateFieldNone — tubman.py:103, 106-107, 140
# ---------------------------------------------------------------------------


class TestCheckDateFieldNone:
    """_check_date_field returns None when dates can't be parsed or within tolerance."""

    def test_returns_none_when_both_dates_unparseable(self) -> None:
        acct_a = {"creditor": "Test", "date_opened": "bad-date"}
        acct_b = {"creditor": "Test", "date_opened": "also-bad"}
        rule = {"tolerance_days": 31, "severity": "medium"}
        result = _check_date_field(acct_a, acct_b, "bu_a", "bu_b", "date_opened", rule)
        assert result is None

    def test_returns_none_when_diff_within_tolerance(self) -> None:
        acct_a = {"creditor": "Test", "date_opened": "2023-01-01"}
        acct_b = {"creditor": "Test", "date_opened": "2023-01-15"}
        rule = {"tolerance_days": 31, "severity": "medium"}
        result = _check_date_field(acct_a, acct_b, "bu_a", "bu_b", "date_opened", rule)
        assert result is None


# ---------------------------------------------------------------------------
# TestDuplicatePairKeySkip — tubman.py:183
# ---------------------------------------------------------------------------


class TestDuplicatePairKeySkip:
    """_detect_duplicates skips already-seen account pairs."""

    def test_triplicate_accounts_produce_unique_pairs_only(self) -> None:
        """Three accounts from same creditor: each unique pair appears only once."""
        accounts = [
            {"creditor": "ABC Bank", "account_number": "1111"},
            {"creditor": "ABC Bank", "account_number": "2222"},
            {"creditor": "ABC Bank", "account_number": "1111"},
        ]
        results = _detect_duplicates("experian", accounts)
        pair_keys = [
            (
                min(d["values"]["bureau_a"]["value"], d["values"]["bureau_b"]["value"]),
                max(d["values"]["bureau_a"]["value"], d["values"]["bureau_b"]["value"]),
            )
            for d in results
        ]
        assert len(pair_keys) == len(set(pair_keys)), (
            "Duplicate pair_key was not skipped"
        )


# ---------------------------------------------------------------------------
# TestMetro2GetCodeLabelNone — tubman.py:270-271
# ---------------------------------------------------------------------------


class TestMetro2GetCodeLabelNone:
    """Metro2FormatValidator.get_code_label returns None for unknown field/code."""

    def test_returns_none_for_unknown_field(self) -> None:
        validator = Metro2FormatValidator()
        assert validator.get_code_label("nonexistent_field", "01") is None

    def test_returns_none_for_unknown_code(self) -> None:
        validator = Metro2FormatValidator()
        assert validator.get_code_label("account_type", "ZZ") is None
