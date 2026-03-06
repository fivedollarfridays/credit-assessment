"""Credit assessment domain types and constants."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

from .disclosures import FCRA_DISCLAIMER


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


class ConfidenceLevel(str, Enum):
    """Confidence level for estimates."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EligibilityStatus(str, Enum):
    """Eligibility status for credit products."""

    ELIGIBLE = "eligible"
    BLOCKED = "blocked"


class ActionPriority(str, Enum):
    """Priority level for credit actions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NegativeItemType(str, Enum):
    """Classification of negative credit items."""

    LATE_PAYMENT = "late_payment"
    CHARGE_OFF = "charge_off"
    COLLECTION = "collection"
    IDENTITY_THEFT = "identity_theft"
    WRONG_BALANCE = "wrong_balance"
    OBSOLETE_ITEM = "obsolete_item"
    UNAUTHORIZED_INQUIRY = "unauthorized_inquiry"
    DOFD_ERROR = "dofd_error"


_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def _validate_date_str(v: str) -> str:
    """Validate that a date string is a real calendar date."""
    from datetime import datetime

    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date: {v}") from None
    return v


class NegativeItemStatus(str, Enum):
    """Status of a negative credit item."""

    OPEN = "open"
    CLOSED = "closed"
    DISPUTED = "disputed"
    PAID = "paid"
    SETTLED = "settled"


class NegativeItem(BaseModel):
    """Structured negative credit item with metadata."""

    type: NegativeItemType
    description: str = Field(max_length=200)
    creditor: str | None = Field(default=None, max_length=100)
    amount: float | None = Field(default=None, ge=0.0)
    date_reported: str | None = Field(default=None, pattern=_DATE_PATTERN)
    date_of_first_delinquency: str | None = Field(default=None, pattern=_DATE_PATTERN)
    status: NegativeItemStatus | None = None

    @field_validator("date_reported", "date_of_first_delinquency")
    @classmethod
    def _check_real_date(cls, v: str | None) -> str | None:
        return _validate_date_str(v)


def _infer_item_type(text: str) -> NegativeItemType:
    """Infer NegativeItemType from a free-text string."""
    lower = text.lower()
    if "collection" in lower:
        return NegativeItemType.COLLECTION
    if "charge_off" in lower or "chargeoff" in lower:
        return NegativeItemType.CHARGE_OFF
    if "late" in lower:
        return NegativeItemType.LATE_PAYMENT
    if "identity" in lower or "theft" in lower:
        return NegativeItemType.IDENTITY_THEFT
    if "balance" in lower or "wrong" in lower:
        return NegativeItemType.WRONG_BALANCE
    if "obsolete" in lower:
        return NegativeItemType.OBSOLETE_ITEM
    if "inquiry" in lower:
        return NegativeItemType.UNAUTHORIZED_INQUIRY
    if "dofd" in lower or "delinquency" in lower:
        return NegativeItemType.DOFD_ERROR
    return NegativeItemType.LATE_PAYMENT


SCORE_BANDS: dict[str, dict[str, int]] = {
    "excellent": {"min": 750, "max": 850},
    "good": {"min": 700, "max": 749},
    "fair": {"min": 650, "max": 699},
    "poor": {"min": 600, "max": 649},
    "very_poor": {"min": 300, "max": 599},
}


# --- Pydantic Models ---


class AccountSummary(BaseModel):
    """Summary of credit accounts."""

    total_accounts: int = Field(ge=0)
    open_accounts: int = Field(ge=0)
    closed_accounts: int = Field(default=0, ge=0)
    negative_accounts: int = Field(default=0, ge=0)
    collection_accounts: int = Field(default=0, ge=0)
    total_balance: float = Field(default=0.0, ge=0.0)
    total_credit_limit: float = Field(default=0.0, ge=0.0)
    monthly_payments: float = Field(default=0.0, ge=0.0)


class CreditProfile(BaseModel):
    """Credit profile for assessment."""

    current_score: int = Field(ge=300, le=850)
    score_band: ScoreBand
    overall_utilization: float = Field(ge=0.0, le=100.0)
    account_summary: AccountSummary
    payment_history_pct: float = Field(ge=0.0, le=100.0)
    average_account_age_months: int = Field(ge=0, le=1200)
    negative_items: list[NegativeItem] = Field(default=[], max_length=50)

    @field_validator("negative_items", mode="before")
    @classmethod
    def _coerce_negative_items(cls, v: list) -> list:
        """Coerce plain strings into NegativeItem objects."""
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(
                    {"type": _infer_item_type(item).value, "description": item}
                )
            else:
                result.append(item)
        return result

    @model_validator(mode="after")
    def _check_score_band(self) -> CreditProfile:
        band = SCORE_BANDS[self.score_band.value]
        lo, hi = band["min"], band["max"]
        if not (lo <= self.current_score <= hi):
            msg = (
                f"score_band {self.score_band.value} requires score "
                f"{lo}-{hi}, got {self.current_score}"
            )
            raise ValueError(msg)
        return self


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
    score_band: ScoreBand
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
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class EligibilityItem(BaseModel):
    """Eligibility assessment for a credit product."""

    product_name: str
    category: str
    required_score: int
    status: EligibilityStatus
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
    disclaimer: str = FCRA_DISCLAIMER


# --- Constants ---


SCORE_WEIGHTS: dict[str, float] = {
    "payment_history": 0.35,
    "utilization": 0.30,
    "credit_age": 0.15,
    "credit_mix": 0.10,
    "new_credit": 0.10,
}

HIGH_UTILIZATION_THRESHOLD: float = 75.0
MODERATE_UTILIZATION_THRESHOLD: float = 50.0

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
