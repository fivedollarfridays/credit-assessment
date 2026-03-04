"""Credit assessment domain types and constants."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class BarrierSeverity(str, Enum):
    """Severity level for credit barriers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoreBand(str, Enum):
    """FICO score band classification."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


class LegalTheory(str, Enum):
    """Legal theories for credit disputes."""

    FCRA_607B = "fcra_607b_accuracy"
    FCRA_611 = "fcra_611_reinvestigation"
    FCRA_605B = "fcra_605b_identity_theft"
    FCRA_623 = "fcra_623_furnisher_duties"
    FDCPA_809 = "fdcpa_809_validation"
    FDCPA_807 = "fdcpa_807_false_representation"
    METRO2_DOFD = "metro2_dofd_violation"
    METRO2_LOGIC = "metro2_logical_inconsistency"
    STATE_LAW = "state_law_violation"


class ActionType(str, Enum):
    """Types of credit improvement actions."""

    PAY_DOWN_DEBT = "pay_down_debt"
    DISPUTE_NEGATIVE = "dispute_negative"
    BECOME_AUTHORIZED_USER = "become_authorized_user"
    OPEN_SECURED_CARD = "open_secured_card"
    AVOID_NEW_INQUIRIES = "avoid_new_inquiries"
    KEEP_ACCOUNTS_OPEN = "keep_accounts_open"
    DIVERSIFY_CREDIT_MIX = "diversify_credit_mix"
    PAY_ON_TIME = "pay_on_time"
    REDUCE_UTILIZATION = "reduce_utilization"
    REMOVE_COLLECTION = "remove_collection"


class ActionPriority(str, Enum):
    """Priority level for credit actions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# --- Pydantic Models ---


class AccountSummary(BaseModel):
    """Summary of credit accounts."""

    total_accounts: int
    open_accounts: int
    closed_accounts: int = 0
    negative_accounts: int = 0
    collection_accounts: int = 0
    total_balance: float = 0.0
    total_credit_limit: float = 0.0
    monthly_payments: float = 0.0


class CreditProfile(BaseModel):
    """Credit profile for assessment."""

    current_score: int = Field(ge=300, le=850)
    score_band: ScoreBand
    overall_utilization: float
    account_summary: AccountSummary
    payment_history_pct: float
    average_account_age_months: int
    negative_items: list[str] = []


class ScoreImpact(BaseModel):
    """Estimated score impact of an action."""

    min_points: int
    max_points: int
    expected_points: int

    @classmethod
    def from_range(cls, min_pts: int, max_pts: int) -> ScoreImpact:
        """Create ScoreImpact from a min/max range."""
        return cls(
            min_points=min_pts,
            max_points=max_pts,
            expected_points=(min_pts + max_pts) // 2,
        )


class CreditBarrier(BaseModel):
    """A barrier to credit improvement."""

    severity: BarrierSeverity
    description: str
    affected_accounts: list[str] = []
    estimated_resolution_days: int = 0


class CreditReadiness(BaseModel):
    """Credit readiness assessment score."""

    score: int = Field(ge=0, le=100)
    fico_score: int = Field(ge=300, le=850)
    score_band: str
    factors: dict[str, float] = {}


class DisputeStep(BaseModel):
    """A single step in a dispute pathway."""

    step_number: int
    action: str
    description: str
    legal_basis: str | None = None
    estimated_days: int = 30
    priority: ActionPriority = ActionPriority.MEDIUM


class DisputePathway(BaseModel):
    """Full dispute pathway with steps and legal theories."""

    steps: list[DisputeStep] = []
    total_estimated_days: int = 0
    statutes_cited: list[str] = []
    legal_theories: list[str] = []


class ThresholdEstimate(BaseModel):
    """Estimate for reaching a credit score threshold."""

    threshold_name: str
    threshold_score: int
    estimated_days: int | None = None
    already_met: bool = False
    confidence: str = "medium"


class EligibilityItem(BaseModel):
    """Eligibility assessment for a credit product."""

    product_name: str
    category: str
    required_score: int
    status: str
    gap_points: int | None = None
    estimated_days_to_eligible: int | None = None
    blocking_factors: list[str] = []


class CreditAssessmentResult(BaseModel):
    """Complete credit assessment output."""

    barrier_severity: BarrierSeverity
    barrier_details: list[CreditBarrier] = []
    readiness: CreditReadiness
    thresholds: list[ThresholdEstimate] = []
    dispute_pathway: DisputePathway
    eligibility: list[EligibilityItem] = []
    disclaimer: str = "All estimates are for educational purposes only."


# --- Constants ---


SCORE_WEIGHTS: dict[str, float] = {
    "payment_history": 0.35,
    "utilization": 0.30,
    "credit_age": 0.15,
    "credit_mix": 0.10,
    "new_credit": 0.10,
}

SCORE_BANDS: dict[str, dict[str, int]] = {
    "excellent": {"min": 750, "max": 850},
    "good": {"min": 700, "max": 749},
    "fair": {"min": 650, "max": 699},
    "poor": {"min": 600, "max": 649},
    "very_poor": {"min": 300, "max": 599},
}

PRODUCT_THRESHOLDS: dict[str, dict[str, str | int]] = {
    "FHA Mortgage": {"score": 580, "category": "mortgage"},
    "Conventional Mortgage": {"score": 620, "category": "mortgage"},
    "Prime Auto Loan": {"score": 700, "category": "auto"},
    "Subprime Auto Loan": {"score": 500, "category": "auto"},
    "Rewards Credit Card": {"score": 700, "category": "credit_card"},
    "Secured Credit Card": {"score": 300, "category": "credit_card"},
    "Personal Loan": {"score": 640, "category": "personal_loan"},
    "Best Rate Mortgage": {"score": 740, "category": "mortgage"},
}
