"""Lewis (Impact Projector) agent -- life outcome projections at multiple horizons."""

from __future__ import annotations

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config

LIFE_THRESHOLDS: dict[int, list[str]] = {
    580: ["Private rental without extra deposit", "FHA mortgage eligible"],
    620: ["Conventional mortgage eligible", "Better auto loan rates"],
    650: ["Most credit cards available", "Lower insurance premiums"],
    700: ["Prime auto loan rates", "Best credit card rewards", "Most jobs accessible"],
    750: ["Best mortgage rates", "Lowest insurance premiums", "Premium credit products"],
}

JOBS_BY_SCORE: dict[int, list[str]] = {
    0: ["food_service", "retail", "manufacturing", "warehouse_logistics", "construction"],
    580: ["healthcare_cna", "trucking_cdl", "education_teacher"],
    620: ["healthcare_admin", "government_state"],
    650: ["finance_banking", "government_federal"],
}

_DEFAULT_30_DAY_BUMP = 15
_DEFAULT_90_DAY_BUMP = 40
_DO_NOTHING_DROP = 5
_SCORE_MIN = 300
_SCORE_MAX = 850


def _clamp_score(score: int) -> int:
    """Clamp a score to the valid 300-850 range."""
    return max(_SCORE_MIN, min(_SCORE_MAX, score))


def _score_to_band(score: int) -> str:
    """Map a numeric score to the config band key."""
    if score >= 750:
        return "750-850"
    if score >= 700:
        return "700-749"
    if score >= 650:
        return "650-699"
    if score >= 600:
        return "600-649"
    if score >= 550:
        return "550-599"
    if score >= 500:
        return "500-549"
    return "300-499"


def _get_life_outcomes(score: int) -> list[str]:
    """Return all life outcomes unlocked at the given score."""
    outcomes: list[str] = []
    for threshold, items in LIFE_THRESHOLDS.items():
        if score >= threshold:
            outcomes.extend(items)
    return outcomes


def _get_accessible_jobs(score: int) -> list[str]:
    """Return all jobs accessible at the given score."""
    jobs: list[str] = []
    for threshold, items in JOBS_BY_SCORE.items():
        if score >= threshold:
            jobs.extend(items)
    return jobs


def _build_projections(
    profile: CreditProfile, context: dict | None
) -> dict[str, int]:
    """Calculate score projections for each timepoint."""
    current = profile.current_score
    sim = (context or {}).get("simulation_result", {})

    return {
        "current": current,
        "30_days": _clamp_score(sim.get(30, current + _DEFAULT_30_DAY_BUMP)),
        "90_days": _clamp_score(sim.get(90, current + _DEFAULT_90_DAY_BUMP)),
        "do_nothing": _clamp_score(current - _DO_NOTHING_DROP),
    }


def _build_timepoint(
    score: int, ins_premiums: dict, auto_bands: dict
) -> dict:
    """Build the full projection dict for a single timepoint."""
    band = _score_to_band(score)
    auto_info = auto_bands[band]
    return {
        "score": score,
        "life_outcomes": _get_life_outcomes(score),
        "accessible_jobs": _get_accessible_jobs(score),
        "insurance_premium": ins_premiums[band],
        "auto_rate": {"apr": auto_info["apr"], "monthly": auto_info["monthly"]},
    }


def _calc_savings(
    current_band: str,
    projected_band: str,
    ins_premiums: dict,
    auto_bands: dict,
) -> dict[str, float]:
    """Calculate annual savings between current and projected bands."""
    ins_saving = max(0.0, ins_premiums[current_band] - ins_premiums[projected_band])
    auto_saving = max(
        0.0,
        (auto_bands[current_band]["monthly"] - auto_bands[projected_band]["monthly"]) * 12,
    )
    return {
        "insurance": round(ins_saving, 2),
        "auto": round(auto_saving, 2),
        "total": round(ins_saving + auto_saving, 2),
    }


def _find_new_doors(current_score: int, projected_score: int) -> list[str]:
    """Find life outcomes that open between current and projected scores."""
    current_outcomes = set(_get_life_outcomes(current_score))
    projected_outcomes = set(_get_life_outcomes(projected_score))
    return sorted(projected_outcomes - current_outcomes)


def _pick_motivational_message(
    current: int, day30: int, day90: int
) -> str:
    """Select a motivational message based on score projections."""
    if day30 >= 580 and current < 580:
        return "In just 30 days, you could qualify for private rental housing"
    if day90 >= 650 and current < 650:
        return (
            "Within 90 days, you could access most credit cards "
            "and lower insurance rates"
        )
    if day90 >= 700 and current < 700:
        return (
            "By 90 days, prime auto loan rates and most jobs "
            "become accessible"
        )
    return "Every point improvement opens new doors — your plan starts today"


@register
class LewisAgent(BaseAgent):
    """Projects life outcomes at different time horizons."""

    name = "lewis"
    description = "Impact Projector: maps score projections to life outcomes"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        ins_cfg = load_config("insurance_by_score")
        auto_cfg = load_config("auto_rates")
        ins_premiums = ins_cfg["annual_premium_by_score"]
        auto_bands = auto_cfg["score_bands"]

        scores = _build_projections(profile, context)
        current_band = _score_to_band(scores["current"])

        projections = {
            key: _build_timepoint(score, ins_premiums, auto_bands)
            for key, score in scores.items()
        }

        band_30 = _score_to_band(scores["30_days"])
        band_90 = _score_to_band(scores["90_days"])

        annual_savings = {
            "30_day_plan": _calc_savings(current_band, band_30, ins_premiums, auto_bands),
            "90_day_plan": _calc_savings(current_band, band_90, ins_premiums, auto_bands),
        }

        new_doors = {
            "by_30_days": _find_new_doors(scores["current"], scores["30_days"]),
            "by_90_days": _find_new_doors(scores["current"], scores["90_days"]),
        }

        message = _pick_motivational_message(
            scores["current"], scores["30_days"], scores["90_days"]
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "projections": projections,
                "annual_savings": annual_savings,
                "new_doors": new_doors,
                "motivational_message": message,
            },
        )
