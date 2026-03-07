"""Tubman (Underground Scout) -- cross-bureau discrepancy scanner.

Only fires when bureau_reports has 2+ bureaus. Detects inconsistencies in
how the same account is reported across different credit bureaus.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations

from . import register
from .base import AgentResult, BaseAgent, load_config
from ..types import CreditProfile

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _field_rule(fields: list[dict], name: str) -> dict | None:
    """Look up a field rule by name from the consistency config."""
    for f in fields:
        if f["name"] == name:
            return f
    return None


# ---------------------------------------------------------------------------
# Account matching
# ---------------------------------------------------------------------------


def _last4(account_number: str) -> str:
    """Extract last 4 characters from an account number."""
    cleaned = "".join(c for c in account_number if c.isdigit())
    return cleaned[-4:] if len(cleaned) >= 4 else cleaned


def _accounts_match(a: dict, b: dict) -> bool:
    """Two accounts match if same creditor (case-insensitive) AND same last 4."""
    cred_a = a.get("creditor", "").strip().lower()
    cred_b = b.get("creditor", "").strip().lower()
    if cred_a != cred_b:
        return False
    num_a = a.get("account_number", "")
    num_b = b.get("account_number", "")
    if num_a == num_b:
        return True
    return _last4(num_a) == _last4(num_b) and len(_last4(num_a)) == 4


# ---------------------------------------------------------------------------
# Balance mismatch detector
# ---------------------------------------------------------------------------


def _check_balance_mismatch(
    acct_a: dict,
    acct_b: dict,
    bureau_a: str,
    bureau_b: str,
    rule: dict,
) -> dict | None:
    """Check if balance differs beyond tolerance across two bureaus."""
    bal_a = acct_a.get("balance")
    bal_b = acct_b.get("balance")
    if bal_a is None or bal_b is None:
        return None
    diff = abs(bal_a - bal_b)
    tol_abs = rule.get("tolerance_abs", 100)
    tol_pct = rule.get("tolerance_pct", 5)
    max_bal = max(abs(bal_a), abs(bal_b), 1)
    pct_diff = (diff / max_bal) * 100
    if diff <= tol_abs and pct_diff <= tol_pct:
        return None
    worse_bureau = bureau_a if bal_a > bal_b else bureau_b
    return {
        "type": "balance_mismatch",
        "creditor": acct_a.get("creditor", ""),
        "field": "balance",
        "values": {
            "bureau_a": {"bureau": bureau_a, "value": bal_a},
            "bureau_b": {"bureau": bureau_b, "value": bal_b},
        },
        "severity": rule.get("severity", "high"),
        "recommended_dispute_bureau": worse_bureau,
        "description": f"Balance differs by ${diff:.0f} ({pct_diff:.1f}%) between {bureau_a} and {bureau_b}",
    }


# ---------------------------------------------------------------------------
# Date discrepancy detector
# ---------------------------------------------------------------------------


def _parse_date(val: str | None) -> datetime | None:
    """Parse YYYY-MM-DD date string, returning None on failure."""
    if val is None:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _check_date_field(
    acct_a: dict,
    acct_b: dict,
    bureau_a: str,
    bureau_b: str,
    field: str,
    rule: dict,
) -> dict | None:
    """Check if a date field differs beyond tolerance_days across bureaus."""
    val_a = acct_a.get(field)
    val_b = acct_b.get(field)
    if val_a is None and val_b is None:
        return None
    if (val_a is None) != (val_b is None):
        worse = bureau_a if val_a is not None else bureau_b
        return {
            "type": "date_discrepancy",
            "creditor": acct_a.get("creditor", ""),
            "field": field,
            "values": {
                "bureau_a": {"bureau": bureau_a, "value": val_a},
                "bureau_b": {"bureau": bureau_b, "value": val_b},
            },
            "severity": rule.get("severity", "medium"),
            "recommended_dispute_bureau": worse,
            "description": f"{field} present on {worse} but missing on the other bureau",
        }
    dt_a = _parse_date(val_a)
    dt_b = _parse_date(val_b)
    if dt_a is None or dt_b is None:
        return None
    diff_days = abs((dt_a - dt_b).days)
    tolerance = rule.get("tolerance_days", 31)
    if diff_days <= tolerance:
        return None
    worse = bureau_a if dt_a > dt_b else bureau_b
    return {
        "type": "date_discrepancy",
        "creditor": acct_a.get("creditor", ""),
        "field": field,
        "values": {
            "bureau_a": {"bureau": bureau_a, "value": val_a},
            "bureau_b": {"bureau": bureau_b, "value": val_b},
        },
        "severity": rule.get("severity", "medium"),
        "recommended_dispute_bureau": worse,
        "description": f"{field} differs by {diff_days} days between {bureau_a} and {bureau_b}",
    }


# ---------------------------------------------------------------------------
# Duplicate account detector
# ---------------------------------------------------------------------------


def _detect_duplicates(bureau_name: str, accounts: list[dict]) -> list[dict]:
    """Find same creditor with different account numbers on one bureau."""
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(accounts):
        for j, b in enumerate(accounts):
            if i >= j:
                continue
            cred_a = a.get("creditor", "").strip().lower()
            cred_b = b.get("creditor", "").strip().lower()
            if cred_a != cred_b:
                continue
            num_a = a.get("account_number", "")
            num_b = b.get("account_number", "")
            if num_a == num_b:
                continue
            pair_key = (min(num_a, num_b), max(num_a, num_b))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            results.append(
                {
                    "type": "duplicate_account",
                    "creditor": a.get("creditor", ""),
                    "field": "account_number",
                    "values": {
                        "bureau_a": {"bureau": bureau_name, "value": num_a},
                        "bureau_b": {"bureau": bureau_name, "value": num_b},
                    },
                    "severity": "medium",
                    "recommended_dispute_bureau": bureau_name,
                    "description": f"Possible duplicate: same creditor '{a.get('creditor', '')}' with different account numbers on {bureau_name}",
                }
            )
    return results


# ---------------------------------------------------------------------------
# Mixed file risk detector
# ---------------------------------------------------------------------------


def _detect_mixed_file(bureau_reports: dict) -> list[dict]:
    """Look for name/address variations across bureaus."""
    results: list[dict] = []
    bureaus_with_info = {
        name: data.get("personal_info", {})
        for name, data in bureau_reports.items()
        if data.get("personal_info")
    }
    bureau_names = list(bureaus_with_info.keys())
    for ba, bb in combinations(bureau_names, 2):
        info_a = bureaus_with_info[ba]
        info_b = bureaus_with_info[bb]
        name_a = info_a.get("name", "").strip().lower()
        name_b = info_b.get("name", "").strip().lower()
        addr_a = info_a.get("address", "").strip().lower()
        addr_b = info_b.get("address", "").strip().lower()
        if name_a and name_b and name_a != name_b:
            results.append(
                {
                    "type": "mixed_file_risk",
                    "creditor": "N/A",
                    "field": "name",
                    "values": {
                        "bureau_a": {"bureau": ba, "value": info_a.get("name", "")},
                        "bureau_b": {"bureau": bb, "value": info_b.get("name", "")},
                    },
                    "severity": "high",
                    "recommended_dispute_bureau": bb,
                    "description": f"Name differs between {ba} and {bb}",
                }
            )
        if addr_a and addr_b and addr_a != addr_b:
            results.append(
                {
                    "type": "mixed_file_risk",
                    "creditor": "N/A",
                    "field": "address",
                    "values": {
                        "bureau_a": {"bureau": ba, "value": info_a.get("address", "")},
                        "bureau_b": {"bureau": bb, "value": info_b.get("address", "")},
                    },
                    "severity": "high",
                    "recommended_dispute_bureau": bb,
                    "description": f"Address differs between {ba} and {bb}",
                }
            )
    return results


# ---------------------------------------------------------------------------
# Metro2 format validator
# ---------------------------------------------------------------------------


class Metro2FormatValidator:
    """Validates Metro2 field positions from configuration."""

    def __init__(self) -> None:
        cfg = load_config("metro2_consistency_rules")
        self.field_positions: dict = cfg.get("metro2_field_positions", {})

    def get_code_label(self, field: str, code: str) -> str | None:
        """Return human-readable label for a Metro2 code."""
        pos = self.field_positions.get(field, {})
        return pos.get("codes", {}).get(code)


# ---------------------------------------------------------------------------
# Tubman agent
# ---------------------------------------------------------------------------


def _compare_matched_pair(
    a: dict,
    b: dict,
    ba: str,
    bb: str,
    fields: list[dict],
) -> list[dict]:
    """Compare two matched accounts across bureaus for all field rules."""
    results: list[dict] = []
    bal_rule = _field_rule(fields, "balance")
    if bal_rule:
        disc = _check_balance_mismatch(a, b, ba, bb, bal_rule)
        if disc:
            results.append(disc)
    for date_field in ("date_opened", "date_of_first_delinquency"):
        date_rule = _field_rule(fields, date_field)
        if date_rule:
            disc = _check_date_field(a, b, ba, bb, date_field, date_rule)
            if disc:
                results.append(disc)
    return results


def _cross_bureau_scan(
    bureau_reports: dict,
    bureau_names: list[str],
    fields: list[dict],
) -> tuple[list[dict], int]:
    """Scan all bureau pairs for discrepancies. Return (discrepancies, match_count)."""
    discrepancies: list[dict] = []
    matched_pairs: set[tuple[str, str, str, str]] = set()
    for ba, bb in combinations(bureau_names, 2):
        accts_a = bureau_reports[ba].get("accounts", [])
        accts_b = bureau_reports[bb].get("accounts", [])
        for a in accts_a:
            for b in accts_b:
                if not _accounts_match(a, b):
                    continue
                pair_key = (
                    ba,
                    bb,
                    a.get("creditor", "").lower(),
                    _last4(a.get("account_number", "")),
                )
                matched_pairs.add(pair_key)
                discrepancies.extend(_compare_matched_pair(a, b, ba, bb, fields))
    return discrepancies, len(matched_pairs)


def _build_severity_summary(discrepancies: list[dict]) -> dict[str, int]:
    """Count discrepancies by severity level."""
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in discrepancies:
        sev = d["severity"]
        if sev in summary:
            summary[sev] += 1
    return summary


@register
class TubmanAgent(BaseAgent):
    """Cross-bureau discrepancy scanner."""

    name: str = "tubman"
    description: str = "Underground Scout -- cross-bureau discrepancy scanner"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        context = context or {}
        bureau_reports = context.get("bureau_reports", {})
        bureau_names = list(bureau_reports.keys())
        if len(bureau_names) < 2:
            return AgentResult(agent_name=self.name, status="skipped")

        fields = load_config("metro2_consistency_rules")["fields"]
        discs, match_count = _cross_bureau_scan(bureau_reports, bureau_names, fields)
        for name in bureau_names:
            discs.extend(
                _detect_duplicates(name, bureau_reports[name].get("accounts", []))
            )
        discs.extend(_detect_mixed_file(bureau_reports))
        discs.sort(key=lambda d: _SEVERITY_ORDER.get(d["severity"], 99))

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "discrepancies": discs,
                "total_discrepancies": len(discs),
                "bureaus_compared": bureau_names,
                "accounts_matched": match_count,
                "severity_summary": _build_severity_summary(discs),
            },
        )
