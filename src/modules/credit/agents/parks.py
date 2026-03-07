"""Parks (Barrier Breaker) agent — maps credit profile to life barriers."""

from __future__ import annotations

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config
from .scoring import score_to_band as _score_to_band

_THRESHOLDS = [580, 620, 650, 700, 750]

_BEST_AUTO_BAND = "750-850"
_BEST_INSURANCE_BAND = "750-850"


def _build_employment(
    profile: CreditProfile, industries: dict, target: list[str] | None
) -> list[dict]:
    """Assess employment barriers for each industry."""
    has_collections = profile.account_summary.collection_accounts > 0
    results: list[dict] = []
    for name, rules in industries.items():
        if target and name not in target:
            continue
        freq = rules["check_frequency"]
        min_score = rules.get("min_score")
        coll_block = rules.get("collection_blocker", False)
        blocked = False
        reason = "No credit check required"
        if freq in ("always", "sometimes"):
            if min_score is not None and profile.current_score < min_score:
                blocked = True
                reason = f"Score {profile.current_score} below minimum {min_score}"
            if coll_block and has_collections:
                blocked = True
                reason = f"Collections block entry ({profile.account_summary.collection_accounts} on file)"
        results.append(
            {
                "industry": name,
                "status": "blocked" if blocked else "accessible",
                "reason": reason,
                "avg_wage": rules["avg_wage"],
            }
        )
    return results


def _build_housing(profile: CreditProfile, housing_types: dict) -> list[dict]:
    """Assess housing barriers for each type."""
    has_collections = profile.account_summary.collection_accounts > 0
    results: list[dict] = []
    for name, rules in housing_types.items():
        min_score = rules.get("min_score")
        credit_check = rules.get("credit_check", False)
        collection_ok = rules.get("collection_ok", True)
        blocked = False
        if credit_check:
            if min_score is not None and profile.current_score < min_score:
                blocked = True
            if not collection_ok and has_collections:
                blocked = True
        results.append(
            {
                "type": name,
                "status": "blocked" if blocked else "accessible",
                "min_score": min_score,
            }
        )
    return results


def _build_auto(profile: CreditProfile, auto_cfg: dict) -> dict:
    """Calculate auto loan barrier vs best available rate."""
    bands = auto_cfg["score_bands"]
    band_key = _score_to_band(profile.current_score)
    current = bands[band_key]
    best = bands[_BEST_AUTO_BAND]
    monthly_diff = round(current["monthly"] - best["monthly"], 2)
    return {
        "current_band": band_key,
        "apr": current["apr"],
        "monthly": current["monthly"],
        "vs_best": {
            "apr_diff": round(current["apr"] - best["apr"], 2),
            "monthly_diff": monthly_diff,
            "annual_extra": round(monthly_diff * 12, 2),
        },
    }


def _build_insurance(profile: CreditProfile, ins_cfg: dict) -> dict:
    """Calculate insurance premium barrier vs best available."""
    premiums = ins_cfg["annual_premium_by_score"]
    band_key = _score_to_band(profile.current_score)
    current_premium = premiums[band_key]
    best_premium = premiums[_BEST_INSURANCE_BAND]
    return {
        "current_band": band_key,
        "annual_premium": current_premium,
        "vs_best": current_premium - best_premium,
    }


def _build_doors(
    profile: CreditProfile, emp_cfg: dict, housing_cfg: dict
) -> list[dict]:
    """Identify which new doors open at each score threshold."""
    doors: list[dict] = []
    for threshold in _THRESHOLDS:
        if threshold <= profile.current_score:
            doors.append({"threshold": threshold, "new_doors": [], "count": 0})
            continue
        new_doors: list[str] = []
        for ind, rules in emp_cfg["industries"].items():
            if rules.get("min_score") == threshold:
                new_doors.append(f"employment:{ind}")
        for ht, rules in housing_cfg["housing_types"].items():
            if rules.get("min_score") == threshold:
                new_doors.append(f"housing:{ht}")
        doors.append(
            {"threshold": threshold, "new_doors": new_doors, "count": len(new_doors)}
        )
    return doors


def _cheapest_door(profile: CreditProfile, doors: list[dict]) -> dict:
    """Find lowest threshold above current score that opens new doors."""
    for entry in doors:
        if entry["threshold"] > profile.current_score and entry["count"] > 0:
            return {
                "threshold": entry["threshold"],
                "points_needed": entry["threshold"] - profile.current_score,
                "new_doors": entry["new_doors"],
            }
    return {"threshold": 0, "points_needed": 0, "new_doors": []}


def _build_roi(
    profile: CreditProfile, doors: list[dict], auto_cfg: dict, ins_cfg: dict
) -> list[dict]:
    """Calculate ROI for reaching each threshold."""
    auto_bands = auto_cfg["score_bands"]
    ins_premiums = ins_cfg["annual_premium_by_score"]
    current_auto_band = _score_to_band(profile.current_score)
    current_auto_monthly = auto_bands[current_auto_band]["monthly"]
    current_ins = ins_premiums[_score_to_band(profile.current_score)]
    roi_list: list[dict] = []
    for entry in doors:
        t = entry["threshold"]
        if t <= profile.current_score:
            continue
        future_auto_band = _score_to_band(t)
        future_monthly = auto_bands[future_auto_band]["monthly"]
        future_ins = ins_premiums[future_auto_band]
        auto_annual = round((current_auto_monthly - future_monthly) * 12, 2)
        ins_annual = current_ins - future_ins
        total_annual = round(auto_annual + ins_annual, 2)
        roi_list.append(
            {
                "threshold": t,
                "annual_savings": total_annual,
                "five_year_savings": round(total_annual * 5, 2),
                "doors": entry["new_doors"],
            }
        )
    roi_list.sort(key=lambda r: r["five_year_savings"], reverse=True)
    return roi_list


@register
class ParksAgent(BaseAgent):
    """Maps credit barriers across employment, housing, auto, insurance."""

    name = "parks"
    description = "Barrier Breaker: maps life barriers from credit profile"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        emp_cfg = load_config("employment_credit_rules")
        housing_cfg = load_config("housing_thresholds")
        auto_cfg = load_config("auto_rates")
        ins_cfg = load_config("insurance_by_score")

        target = (context or {}).get("target_industries")

        employment = _build_employment(profile, emp_cfg["industries"], target)
        housing = _build_housing(profile, housing_cfg["housing_types"])
        auto = _build_auto(profile, auto_cfg)
        insurance = _build_insurance(profile, ins_cfg)
        doors = _build_doors(profile, emp_cfg, housing_cfg)
        cheapest = _cheapest_door(profile, doors)
        roi = _build_roi(profile, doors, auto_cfg, ins_cfg)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "life_barriers": {
                    "employment": employment,
                    "housing": housing,
                    "auto": auto,
                    "insurance": insurance,
                },
                "doors_analysis": doors,
                "cheapest_door": cheapest,
                "roi_per_door": roi,
            },
        )
