"""Credit assessment scoring engine and orchestrator."""

from __future__ import annotations

from typing import TypedDict

from .dispute_pathway import DisputePathwayGenerator
from .types import (
    BarrierSeverity,
    ConfidenceLevel,
    CreditAssessmentResult,
    CreditBarrier,
    CreditProfile,
    CreditReadiness,
    DisputePathway,
    EligibilityItem,
    EligibilityStatus,
    HIGH_UTILIZATION_THRESHOLD,
    MODERATE_UTILIZATION_THRESHOLD,
    PRODUCT_THRESHOLDS,
    SCORE_BANDS,
    SCORE_WEIGHTS,
    ScoreBand,
    ThresholdEstimate,
)

class BracketData(TypedDict):
    """Type for utilization bracket impact data."""

    impact: int


class UtilizationImpact(TypedDict):
    """Return type for utilization impact calculation."""

    low: int
    high: int


UTILIZATION_BRACKETS: dict[tuple[int, int], BracketData] = {
    (0, 1): {"impact": 50},
    (1, 10): {"impact": 45},
    (10, 20): {"impact": 35},
    (20, 30): {"impact": 25},
    (30, 50): {"impact": 10},
    (50, 75): {"impact": 0},
    (75, 90): {"impact": -15},
    (90, 100): {"impact": -30},
}
# Empirical estimate: ~0.2 FICO points per day from consistent positive behavior
_POINTS_PER_DAY = 0.2


def _estimate_days_for_gap(gap: int) -> int:
    """Estimate days needed to close a score gap."""
    return int(gap / _POINTS_PER_DAY)


def get_score_band(score: int) -> ScoreBand:
    """Get the score band for a given FICO score."""
    for band_name, bounds in SCORE_BANDS.items():
        if bounds["min"] <= score <= bounds["max"]:
            return ScoreBand(band_name)
    return ScoreBand.VERY_POOR


def get_utilization_impact(current_util: float, target_util: float) -> UtilizationImpact:
    """Calculate estimated score impact of changing utilization."""

    def _bracket_impact(util: float) -> int:
        for (low, high), data in UTILIZATION_BRACKETS.items():
            if low <= util < high:
                return data["impact"]
        return -30  # Maxed out

    current_impact = _bracket_impact(current_util)
    target_impact = _bracket_impact(target_util)
    improvement = target_impact - current_impact

    return {
        "low": max(0, int(improvement * 0.7)),
        "high": int(improvement * 1.3),
    }


class CreditAssessmentService:
    """Orchestrates all five credit assessment outputs."""

    def __init__(self) -> None:
        self._dispute_gen = DisputePathwayGenerator()

    def assess(self, profile: CreditProfile) -> CreditAssessmentResult:
        """Run full assessment producing all five outputs."""
        severity, barriers = self._compute_barrier_severity(profile)
        readiness = self._compute_readiness_score(profile)
        thresholds = self._estimate_days_to_thresholds(profile)
        eligibility = self._compute_eligibility(profile)
        dispute_pathway = self._build_dispute_pathway(profile)

        return CreditAssessmentResult(
            barrier_severity=severity,
            barrier_details=barriers,
            readiness=readiness,
            thresholds=thresholds,
            dispute_pathway=dispute_pathway,
            eligibility=eligibility,
        )

    def _compute_barrier_severity(
        self, profile: CreditProfile
    ) -> tuple[BarrierSeverity, list[CreditBarrier]]:
        """Classify barriers as HIGH / MEDIUM / LOW."""
        acct = profile.account_summary
        has_collections = acct.collection_accounts > 0
        high_util = profile.overall_utilization > HIGH_UTILIZATION_THRESHOLD
        very_low_score = profile.current_score < 580

        if has_collections or high_util or very_low_score:
            return BarrierSeverity.HIGH, self._high_barriers(profile)

        has_negatives = len(profile.negative_items) > 0
        moderate_util = profile.overall_utilization > MODERATE_UTILIZATION_THRESHOLD
        low_score = profile.current_score < 650

        if has_negatives or moderate_util or low_score:
            return BarrierSeverity.MEDIUM, self._medium_barriers(profile)

        return BarrierSeverity.LOW, []

    def _high_barriers(self, profile: CreditProfile) -> list[CreditBarrier]:
        """Build HIGH severity barrier list."""
        barriers: list[CreditBarrier] = []
        acct = profile.account_summary
        if acct.collection_accounts > 0:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.HIGH,
                description=f"{acct.collection_accounts} collection account(s) on file",
                estimated_resolution_days=90,
            ))
        if profile.overall_utilization > HIGH_UTILIZATION_THRESHOLD:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.HIGH,
                description=(
                    f"Utilization at {profile.overall_utilization:.0f}%"
                    " (above 75%)"
                ),
                estimated_resolution_days=60,
            ))
        if profile.current_score < 580:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.HIGH,
                description=f"Score {profile.current_score} is below 580",
                estimated_resolution_days=180,
            ))
        return barriers

    def _medium_barriers(self, profile: CreditProfile) -> list[CreditBarrier]:
        """Build MEDIUM severity barrier list."""
        barriers: list[CreditBarrier] = []
        if len(profile.negative_items) > 0:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.MEDIUM,
                description=f"{len(profile.negative_items)} negative item(s) on file",
            ))
        if profile.overall_utilization > MODERATE_UTILIZATION_THRESHOLD:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.MEDIUM,
                description=(
                    f"Utilization at {profile.overall_utilization:.0f}%"
                    " (above 50%)"
                ),
            ))
        if profile.current_score < 650:
            barriers.append(CreditBarrier(
                severity=BarrierSeverity.MEDIUM,
                description=f"Score {profile.current_score} is below 650",
            ))
        return barriers

    def _compute_readiness_score(self, profile: CreditProfile) -> CreditReadiness:
        """Normalize profile into a 0-100 readiness score."""
        acct = profile.account_summary

        payment_factor = profile.payment_history_pct / 100.0
        util_factor = max(0.0, (100 - profile.overall_utilization)) / 100.0
        age_factor = min(1.0, profile.average_account_age_months / 84.0)
        mix_factor = min(1.0, acct.total_accounts / 10.0)
        new_credit_factor = 0.7 if acct.open_accounts > 0 else 0.5

        factor_score = (
            payment_factor * SCORE_WEIGHTS["payment_history"]
            + util_factor * SCORE_WEIGHTS["utilization"]
            + age_factor * SCORE_WEIGHTS["credit_age"]
            + mix_factor * SCORE_WEIGHTS["credit_mix"]
            + new_credit_factor * SCORE_WEIGHTS["new_credit"]
        )

        fico_normalized = (profile.current_score - 300) / 550.0

        neg_penalty = min(
            0.3,
            len(profile.negative_items) * 0.05
            + acct.collection_accounts * 0.05,
        )

        raw = fico_normalized * 0.5 + factor_score * 0.5 - neg_penalty
        score = max(0, min(100, int(raw * 100)))

        return CreditReadiness(
            score=score,
            fico_score=profile.current_score,
            score_band=get_score_band(profile.current_score),
            factors={
                "payment_history": round(payment_factor, 3),
                "utilization": round(util_factor, 3),
                "credit_age": round(age_factor, 3),
                "credit_mix": round(mix_factor, 3),
                "new_credit": round(new_credit_factor, 3),
            },
        )

    def _estimate_days_to_thresholds(
        self, profile: CreditProfile
    ) -> list[ThresholdEstimate]:
        """Estimate days to reach each score-band threshold."""
        defs = [
            ("Poor Credit", SCORE_BANDS["poor"]["min"]),
            ("Fair Credit", SCORE_BANDS["fair"]["min"]),
            ("Good Credit", SCORE_BANDS["good"]["min"]),
            ("Excellent Credit", SCORE_BANDS["excellent"]["min"]),
        ]
        results: list[ThresholdEstimate] = []
        for name, min_score in defs:
            gap = min_score - profile.current_score
            if gap <= 0:
                results.append(
                    ThresholdEstimate(
                        threshold_name=name,
                        threshold_score=min_score,
                        estimated_days=0,
                        already_met=True,
                        confidence=ConfidenceLevel.HIGH,
                    )
                )
            else:
                results.append(
                    ThresholdEstimate(
                        threshold_name=name,
                        threshold_score=min_score,
                        estimated_days=_estimate_days_for_gap(gap),
                        already_met=False,
                        confidence=ConfidenceLevel.MEDIUM if gap < 50 else ConfidenceLevel.LOW,
                    )
                )
        return results

    def _compute_eligibility(
        self, profile: CreditProfile
    ) -> list[EligibilityItem]:
        """Compare profile score against product thresholds."""
        items: list[EligibilityItem] = []
        for product_name, info in PRODUCT_THRESHOLDS.items():
            required = info["score"]
            category = info["category"]
            gap = required - profile.current_score

            if gap <= 0:
                items.append(
                    EligibilityItem(
                        product_name=product_name,
                        category=category,
                        required_score=required,
                        status=EligibilityStatus.ELIGIBLE,
                        gap_points=0,
                    )
                )
            else:
                items.append(
                    EligibilityItem(
                        product_name=product_name,
                        category=category,
                        required_score=required,
                        status=EligibilityStatus.BLOCKED,
                        gap_points=gap,
                        estimated_days_to_eligible=_estimate_days_for_gap(gap),
                        blocking_factors=self._blocking_factors(profile, required),
                    )
                )
        return items

    def _blocking_factors(
        self, profile: CreditProfile, required_score: int
    ) -> list[str]:
        """Identify reasons a product is blocked."""
        factors: list[str] = [
            f"Score {profile.current_score} below {required_score}"
        ]
        if profile.overall_utilization > MODERATE_UTILIZATION_THRESHOLD:
            factors.append("High utilization")
        if profile.account_summary.collection_accounts > 0:
            factors.append("Active collections")
        return factors

    def _build_dispute_pathway(self, profile: CreditProfile) -> DisputePathway:
        """Delegate to DisputePathwayGenerator for full pathway."""
        return self._dispute_gen.generate_pathway(profile)
