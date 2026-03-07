"""Phantom (Poverty Tax Calculator) agent — Bristol PFRC methodology."""

from __future__ import annotations

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config
from .scoring import score_to_band as _score_to_band

# Action descriptions for each component in the kill plan
_KILL_ACTIONS: dict[str, str] = {
    "credit_premium": "Pay down debt and improve score to reduce APR differential",
    "insurance_premium": "Improve score to qualify for lower insurance rates",
    "employment_barrier": "Clear collections and raise score to unlock blocked jobs",
    "housing_premium": "Raise score to reduce rent premiums and deposit multipliers",
}


def _calc_credit_premium(band: str, total_balance: float, config: dict) -> dict:
    """Calculate credit premium scaled by actual debt."""
    bands = config["components"]["credit_premium"]["bands"]
    base_cost = bands[band]["annual_cost"]
    annual_cost = base_cost * (total_balance / 10_000.0)
    annual_cost = max(0.0, annual_cost)
    return {
        "annual_cost": round(annual_cost, 2),
        "source": config["components"]["credit_premium"]["source"],
        "methodology": "APR differential per $10K debt, scaled to actual balance",
    }


def _calc_insurance_premium(band: str, config: dict) -> dict:
    """Calculate insurance premium -- direct lookup, no scaling."""
    bands = config["components"]["insurance_premium"]["bands"]
    annual_cost = float(bands[band]["annual_cost"])
    return {
        "annual_cost": annual_cost,
        "source": config["components"]["insurance_premium"]["source"],
    }


def _is_blocked(
    industry: str,
    score: int,
    collection_accounts: int,
    rules: dict,
) -> bool:
    """Check whether a score/collection combo blocks an industry."""
    industry_rule = rules.get("industries", {}).get(industry)
    if industry_rule is None:
        return False
    if industry_rule.get("collection_blocker") and collection_accounts > 0:
        return True
    min_score = industry_rule.get("min_score")
    if min_score is not None and score < min_score:
        return True
    return False


def _calc_employment_barrier(
    industry: str,
    score: int,
    collection_accounts: int,
    config: dict,
) -> dict:
    """Calculate employment barrier cost for a target industry."""
    rules = load_config("employment_credit_rules")
    categories = config["components"]["employment_barrier"]["categories"]
    source = config["components"]["employment_barrier"]["source"]

    # Check if the industry exists in the poverty tax categories
    cat = categories.get(industry)

    blocked = _is_blocked(industry, score, collection_accounts, rules)

    if not blocked or cat is None:
        return {
            "annual_cost": 0.0,
            "industry": industry,
            "blocked_wage": 0.0,
            "unblocked_wage": 0.0,
            "source": source,
        }

    return {
        "annual_cost": float(cat["annual_loss"]),
        "industry": industry,
        "blocked_wage": cat["blocked_wage"],
        "unblocked_wage": cat["unblocked_wage"],
        "source": source,
    }


def _calc_housing_premium(band: str, config: dict) -> dict:
    """Calculate housing premium -- direct lookup, no scaling."""
    bands = config["components"]["housing_premium"]["bands"]
    annual_cost = float(bands[band]["annual_cost"])
    return {
        "annual_cost": annual_cost,
        "source": config["components"]["housing_premium"]["source"],
    }


def _build_kill_plan(components: dict) -> list[dict]:
    """Build kill plan sorted by annual_savings descending."""
    items: list[dict] = []
    for comp_name, comp_data in components.items():
        cost = comp_data["annual_cost"]
        if cost > 0:
            items.append(
                {
                    "component": comp_name,
                    "annual_savings": cost,
                    "action": _KILL_ACTIONS.get(comp_name, "Improve credit profile"),
                    "priority": 0,  # placeholder, assigned after sorting
                }
            )
    items.sort(key=lambda x: x["annual_savings"], reverse=True)
    for idx, item in enumerate(items):
        item["priority"] = idx + 1
    return items


def _calc_urgency(total: float) -> dict:
    """Break total annual cost into day/week/month."""
    return {
        "cost_per_day": round(total / 365, 2),
        "cost_per_week": round(total / 52, 2),
        "cost_per_month": round(total / 12, 2),
    }


def _calc_wage_comparison(total: float, min_wage: float) -> dict:
    """Compare poverty tax to minimum wage."""
    per_hour = total / 2080.0
    return {
        "poverty_tax_per_hour": round(per_hour, 2),
        "al_minimum_wage": min_wage,
        "tax_as_pct_of_minimum": round(per_hour / min_wage, 4),
    }


def _apply_validation(total: float, config: dict) -> tuple[float, dict]:
    """Clamp total to validation range, return clamped total and flags."""
    vmin = config["validation_range"]["min"]
    vmax = config["validation_range"]["max"]
    original = total
    capped = False
    in_range = True

    if total < vmin:
        total = float(vmin)
        capped = True
        in_range = False
    elif total > vmax:
        total = float(vmax)
        capped = True
        in_range = False

    return total, {
        "in_range": in_range,
        "capped": capped,
        "original_total": round(original, 2),
    }


def _assemble_result(
    agent_name: str,
    components: dict,
    total: float,
    validation: dict,
    config: dict,
    min_wage: float,
) -> AgentResult:
    """Build the final AgentResult from computed components."""
    return AgentResult(
        agent_name=agent_name,
        status="success",
        data={
            "total_annual_tax": total,
            "components": components,
            "methodology_source": config["methodology"],
            "cpi_multiplier": config["cpi_inflation_multiplier"],
            "gbp_usd_rate": config["gbp_usd_rate"],
            "montgomery_adjusted": config["montgomery_adjusted"],
            "kill_plan": _build_kill_plan(components),
            "urgency": _calc_urgency(total),
            "wage_comparison": _calc_wage_comparison(total, min_wage),
            "validation": validation,
        },
    )


@register
class PhantomAgent(BaseAgent):
    """Poverty Tax Calculator -- Bristol PFRC methodology for Montgomery, AL."""

    name = "phantom"
    description = "Calculates annual poverty tax using Bristol PFRC framework"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        ctx = context or {}
        config = load_config("poverty_tax_tables")
        city = load_config("city_config")

        band = _score_to_band(profile.current_score)
        balance = profile.account_summary.total_balance
        collections = profile.account_summary.collection_accounts
        industry = ctx.get("target_industry", "healthcare_cna")

        components = {
            "credit_premium": _calc_credit_premium(band, balance, config),
            "insurance_premium": _calc_insurance_premium(band, config),
            "employment_barrier": _calc_employment_barrier(
                industry,
                profile.current_score,
                collections,
                config,
            ),
            "housing_premium": _calc_housing_premium(band, config),
        }

        raw_total = sum(c["annual_cost"] for c in components.values())
        total, validation = _apply_validation(raw_total, config)

        return _assemble_result(
            self.name,
            components,
            total,
            validation,
            config,
            city["minimum_wage"],
        )
