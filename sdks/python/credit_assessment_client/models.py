"""Request and response models for the Credit Assessment API."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AccountSummary:
    """Credit account summary."""

    total_accounts: int
    open_accounts: int
    closed_accounts: int = 0
    negative_accounts: int = 0
    collection_accounts: int = 0
    total_balance: float = 0.0
    total_credit_limit: float = 0.0
    monthly_payments: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_accounts": self.total_accounts,
            "open_accounts": self.open_accounts,
            "closed_accounts": self.closed_accounts,
            "negative_accounts": self.negative_accounts,
            "collection_accounts": self.collection_accounts,
            "total_balance": self.total_balance,
            "total_credit_limit": self.total_credit_limit,
            "monthly_payments": self.monthly_payments,
        }


@dataclass
class CreditProfile:
    """Credit profile for assessment requests."""

    current_score: int
    score_band: str
    overall_utilization: float
    account_summary: AccountSummary
    payment_history_pct: float
    average_account_age_months: int
    negative_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "current_score": self.current_score,
            "score_band": self.score_band,
            "overall_utilization": self.overall_utilization,
            "account_summary": self.account_summary.to_dict(),
            "payment_history_pct": self.payment_history_pct,
            "average_account_age_months": self.average_account_age_months,
            "negative_items": self.negative_items,
        }


@dataclass
class AssessmentResult:
    """Credit assessment response."""

    barrier_severity: str
    readiness: dict
    barrier_details: list[dict] = field(default_factory=list)
    thresholds: list[dict] = field(default_factory=list)
    dispute_pathway: dict = field(default_factory=dict)
    eligibility: list[dict] = field(default_factory=list)
    disclaimer: str = ""

    @property
    def readiness_score(self) -> int:
        return self.readiness.get("score", 0)

    @classmethod
    def from_dict(cls, data: dict) -> AssessmentResult:
        return cls(
            barrier_severity=data.get("barrier_severity", ""),
            readiness=data.get("readiness", {}),
            barrier_details=data.get("barrier_details", []),
            thresholds=data.get("thresholds", []),
            dispute_pathway=data.get("dispute_pathway", {}),
            eligibility=data.get("eligibility", []),
            disclaimer=data.get("disclaimer", ""),
        )
