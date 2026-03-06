"""Colvin (First Strike) -- 40-day attack cycle generator with bureau rotation.

Generates dispute attack cycles with anti-flagging diversity metrics.
All disputes target FACTUAL inaccuracies per Fifth Circuit context.
"""

from __future__ import annotations

from . import register
from .base import AgentResult, BaseAgent, load_config
from ..types import CreditProfile, NegativeItem, NegativeItemType

_BUREAUS = ["Experian", "Equifax", "TransUnion"]
_FORMAT_TYPES = ["prose", "bullets", "numbered"]
_CYCLE_DAYS = 40


# ---------------------------------------------------------------------------
# Factual target generation
# ---------------------------------------------------------------------------


def _factual_target(item: NegativeItem) -> str:
    """Generate a factual dispute target string based on item type."""
    amount_str = f"${item.amount:,.0f}" if item.amount else "$0"
    targets: dict[NegativeItemType, str] = {
        NegativeItemType.COLLECTION: (
            f"Balance of {amount_str} is factually inaccurate "
            "-- request validation of debt amount"
        ),
        NegativeItemType.LATE_PAYMENT: (
            "Payment status reported as late is factually incorrect"
        ),
        NegativeItemType.CHARGE_OFF: (
            f"Charge-off balance of {amount_str} does not reflect "
            "actual amount owed"
        ),
        NegativeItemType.WRONG_BALANCE: (
            f"Reported balance of {amount_str} differs from actual balance"
        ),
        NegativeItemType.DOFD_ERROR: (
            "Date of first delinquency reported is factually incorrect"
        ),
    }
    return targets.get(
        item.type,
        "Reported information contains factual inaccuracies requiring investigation",
    )


# ---------------------------------------------------------------------------
# Attack cycle builder
# ---------------------------------------------------------------------------


def _build_cycles(
    items: list[NegativeItem], issue_types: dict
) -> list[dict]:
    """Build attack cycles for all negative items using legal basis rotation."""
    cycles: list[dict] = []
    for item_idx, item in enumerate(items):
        item_type_key = item.type.value
        rounds = issue_types.get(item_type_key, [])
        if not rounds:
            continue
        target = _factual_target(item)
        for round_idx, basis_info in enumerate(rounds):
            bureau = _BUREAUS[(item_idx + round_idx) % 3]
            day_start = round_idx * _CYCLE_DAYS
            cycles.append({
                "cycle": round_idx + 1,
                "item": item.description,
                "creditor": item.creditor or "",
                "bureau": bureau,
                "legal_basis": basis_info["basis"],
                "statutes": basis_info["statutes"],
                "day_start": day_start,
                "day_end": day_start + _CYCLE_DAYS - 1,
                "factual_target": target,
                "format_recommendation": _FORMAT_TYPES[round_idx % 3],
            })
    return cycles


# ---------------------------------------------------------------------------
# Bureau distribution
# ---------------------------------------------------------------------------


def _bureau_distribution(cycles: list[dict]) -> dict[str, int]:
    """Count how many cycles go to each bureau."""
    dist = {b: 0 for b in _BUREAUS}
    for c in cycles:
        dist[c["bureau"]] += 1
    return dist


# ---------------------------------------------------------------------------
# Diversity metric
# ---------------------------------------------------------------------------


def _compute_diversity(cycles: list[dict]) -> float:
    """Compute anti-flagging diversity metric (0.0-1.0).

    Measures structural diversity across three dimensions:
    - paragraph_lengths: variation in cycle index (proxy for paragraph count)
    - syntax_pattern: variation in format type mix
    - format_type: variation across prose/bullets/numbered
    """
    if len(cycles) <= 1:
        return 1.0

    # Paragraph length variation: how many distinct cycle numbers
    cycle_nums = {c["cycle"] for c in cycles}
    para_score = min(len(cycle_nums) / 3.0, 1.0)

    # Syntax pattern variation: mix of format recommendations
    formats_used = {c["format_recommendation"] for c in cycles}
    syntax_score = len(formats_used) / len(_FORMAT_TYPES)

    # Format type variation: ratio of unique formats to total cycles
    format_score = min(len(formats_used) / min(len(cycles), 3), 1.0)

    return round((para_score + syntax_score + format_score) / 3.0, 4)


def _phrase_variation_count(cycles: list[dict]) -> int:
    """Count unique legal basis phrases across all cycles."""
    return len({c["legal_basis"] for c in cycles})


# ---------------------------------------------------------------------------
# Colvin agent
# ---------------------------------------------------------------------------


@register
class ColvinAgent(BaseAgent):
    """First Strike -- 40-day attack cycle generator."""

    name: str = "colvin"
    description: str = "First Strike -- 40-day attack cycles with bureau rotation"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        config = load_config("legal_basis_rotation")
        issue_types = config.get("issue_types", {})
        fifth_circuit = config.get("fifth_circuit_context", "")

        items = profile.negative_items
        cycles = _build_cycles(items, issue_types)

        diversity = _compute_diversity(cycles)
        # Auto-rotate format if diversity is low
        if diversity < 0.7 and cycles:
            for i, c in enumerate(cycles):
                c["format_recommendation"] = _FORMAT_TYPES[i % 3]
            diversity = _compute_diversity(cycles)

        total_days = 0
        if cycles:
            total_days = max(c["day_end"] for c in cycles) + 1

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "attack_cycles": cycles,
                "total_cycles": len(cycles),
                "total_days": total_days,
                "bureau_distribution": _bureau_distribution(cycles),
                "diversity_metric": diversity,
                "phrase_variation_count": _phrase_variation_count(cycles),
                "fifth_circuit_context": fifth_circuit,
                "items_covered": len(items),
            },
        )
