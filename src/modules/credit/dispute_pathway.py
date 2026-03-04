"""Dispute pathway generator — issue detection and step generation."""

from __future__ import annotations

import logging
from typing import TypedDict

from .types import (
    ActionPriority,
    CreditProfile,
    DisputePathway,
    DisputeStep,
    HIGH_UTILIZATION_THRESHOLD,
    LegalTheory,
)

logger = logging.getLogger(__name__)


class IssuePattern(TypedDict):
    """Type for issue pattern entries."""

    legal_theories: list[LegalTheory]
    statutes: list[str]
    priority: ActionPriority
    estimated_days: int
    action: str
    legal_basis: str


ISSUE_PATTERNS: dict[str, IssuePattern] = {
    "late_payment": {
        "legal_theories": [LegalTheory.FCRA_607B, LegalTheory.FCRA_611],
        "statutes": ["15 U.S.C. § 1681e(b)", "15 U.S.C. § 1681i(a)"],
        "priority": ActionPriority.HIGH,
        "estimated_days": 30,
        "action": "Dispute late payment",
        "legal_basis": "FCRA Section 611 — Reinvestigation of disputed information",
    },
    "charge_off": {
        "legal_theories": [
            LegalTheory.FCRA_607B,
            LegalTheory.FCRA_623,
            LegalTheory.METRO2_LOGIC,
        ],
        "statutes": ["15 U.S.C. § 1681s-2(b)", "15 U.S.C. § 1681e(b)"],
        "priority": ActionPriority.HIGH,
        "estimated_days": 45,
        "action": "Dispute charge-off",
        "legal_basis": "FCRA Section 623 — Furnisher duties upon dispute",
    },
    "collection": {
        "legal_theories": [
            LegalTheory.FDCPA_809,
            LegalTheory.FCRA_611,
            LegalTheory.FCRA_623,
        ],
        "statutes": ["15 U.S.C. § 1692g", "15 U.S.C. § 1681i"],
        "priority": ActionPriority.CRITICAL,
        "estimated_days": 30,
        "action": "Validate and dispute collection",
        "legal_basis": "FDCPA Section 809 — Debt validation",
    },
    "identity_theft": {
        "legal_theories": [LegalTheory.FCRA_605B],
        "statutes": ["15 U.S.C. § 1681c-2"],
        "priority": ActionPriority.CRITICAL,
        "estimated_days": 6,
        "action": "File identity theft dispute",
        "legal_basis": "FCRA Section 605B — Identity theft block",
    },
    "wrong_balance": {
        "legal_theories": [LegalTheory.FCRA_607B, LegalTheory.METRO2_LOGIC],
        "statutes": ["15 U.S.C. § 1681e(b)"],
        "priority": ActionPriority.MEDIUM,
        "estimated_days": 30,
        "action": "Dispute incorrect balance",
        "legal_basis": "FCRA Section 607(b) — Accuracy requirements",
    },
    "obsolete_item": {
        "legal_theories": [LegalTheory.FCRA_607B],
        "statutes": ["15 U.S.C. § 1681c"],
        "priority": ActionPriority.HIGH,
        "estimated_days": 30,
        "action": "Request removal of obsolete item",
        "legal_basis": "FCRA Section 605 — Obsolete information (7-year rule)",
    },
    "unauthorized_inquiry": {
        "legal_theories": [LegalTheory.FCRA_607B],
        "statutes": ["15 U.S.C. § 1681b"],
        "priority": ActionPriority.LOW,
        "estimated_days": 30,
        "action": "Dispute unauthorized inquiry",
        "legal_basis": "FCRA Section 604 — Permissible purpose required",
    },
    "dofd_error": {
        "legal_theories": [LegalTheory.METRO2_DOFD, LegalTheory.FCRA_607B],
        "statutes": ["15 U.S.C. § 1681e(b)"],
        "priority": ActionPriority.HIGH,
        "estimated_days": 30,
        "action": "Dispute date of first delinquency error",
        "legal_basis": "Metro 2 DOFD reporting requirements",
    },
}

_PRIORITY_ORDER = {
    ActionPriority.CRITICAL: 0,
    ActionPriority.HIGH: 1,
    ActionPriority.MEDIUM: 2,
    ActionPriority.LOW: 3,
}


class DisputePathwayGenerator:
    """Generates prioritized dispute pathways from credit profiles."""

    def generate_pathway(self, profile: CreditProfile) -> DisputePathway:
        """Generate a prioritized dispute pathway."""
        items = self._build_item_steps(profile)
        items.extend(self._build_profile_steps(profile))

        if not items:
            return DisputePathway()

        # Sort by priority (CRITICAL first), then renumber
        items.sort(key=lambda x: _PRIORITY_ORDER.get(x[0].priority, 3))

        all_theories: set[str] = set()
        all_statutes: set[str] = set()
        steps: list[DisputeStep] = []

        for i, (step, pattern) in enumerate(items, 1):
            step.step_number = i
            steps.append(step)
            for theory in pattern["legal_theories"]:
                all_theories.add(theory.value)
            all_statutes.update(pattern["statutes"])

        return DisputePathway(
            steps=steps,
            total_estimated_days=sum(s.estimated_days for s in steps),
            statutes_cited=sorted(all_statutes),
            legal_theories=sorted(all_theories),
        )

    def _classify_issue_type(self, item_str: str) -> str:
        """Classify issue type from a negative item string."""
        lower = item_str.lower()
        if "collection" in lower:
            return "collection"
        if "charge_off" in lower or "chargeoff" in lower:
            return "charge_off"
        if "late" in lower:
            return "late_payment"
        if "identity" in lower or "theft" in lower:
            return "identity_theft"
        if "balance" in lower or "wrong" in lower:
            return "wrong_balance"
        if "obsolete" in lower:
            return "obsolete_item"
        if "inquiry" in lower:
            return "unauthorized_inquiry"
        if "dofd" in lower or "delinquency" in lower:
            return "dofd_error"
        logger.warning("Unknown issue type '%s', defaulting to late_payment", item_str)
        return "late_payment"

    def _build_item_steps(
        self, profile: CreditProfile
    ) -> list[tuple[DisputeStep, IssuePattern]]:
        """Build dispute steps from negative items."""
        result: list[tuple[DisputeStep, IssuePattern]] = []
        for item in profile.negative_items:
            issue_type = self._classify_issue_type(item)
            pattern = ISSUE_PATTERNS[issue_type]
            step = DisputeStep(
                step_number=0,
                action=f"{pattern['action']}: {item}",
                description=(
                    f"File dispute for {issue_type.replace('_', ' ')}: {item}"
                ),
                legal_basis=pattern["legal_basis"],
                estimated_days=pattern["estimated_days"],
                priority=pattern["priority"],
            )
            result.append((step, pattern))
        return result

    def _build_profile_steps(
        self, profile: CreditProfile
    ) -> list[tuple[DisputeStep, IssuePattern]]:
        """Build additional steps from profile-level issues."""
        result: list[tuple[DisputeStep, IssuePattern]] = []
        if profile.overall_utilization > HIGH_UTILIZATION_THRESHOLD and profile.account_summary.total_credit_limit > 0:
            pattern = ISSUE_PATTERNS["wrong_balance"]
            step = DisputeStep(
                step_number=0,
                action="Review balance reporting accuracy",
                description=(
                    f"Verify reported balances are accurate "
                    f"(utilization at {profile.overall_utilization:.0f}%)"
                ),
                legal_basis=pattern["legal_basis"],
                estimated_days=30,
                priority=ActionPriority.MEDIUM,
            )
            result.append((step, pattern))
        return result
