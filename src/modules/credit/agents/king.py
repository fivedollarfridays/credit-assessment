"""King (Pathway Commander) agent — 3-phase battle plan for credit improvement."""

from __future__ import annotations

from ..types import CreditProfile, NegativeItemType
from . import register
from .base import AgentResult, BaseAgent, load_config

_ITEM_PRIORITY = {
    NegativeItemType.COLLECTION: 0,
    NegativeItemType.CHARGE_OFF: 1,
    NegativeItemType.IDENTITY_THEFT: 2,
    NegativeItemType.WRONG_BALANCE: 3,
    NegativeItemType.DOFD_ERROR: 4,
    NegativeItemType.OBSOLETE_ITEM: 5,
    NegativeItemType.UNAUTHORIZED_INQUIRY: 6,
    NegativeItemType.LATE_PAYMENT: 7,
}

_DEFAULT_CREDIT_ACTIONS = [
    {
        "action": "Open a secured credit card",
        "impact": "Builds positive payment history",
        "timeline": "1-3 months to see impact",
        "why_now": "Establishing positive tradelines helps offset negatives",
    },
    {
        "action": "Become an authorized user on a trusted account",
        "impact": "Inherits account age and payment history",
        "timeline": "1-2 months to report",
        "why_now": "Fastest way to add positive history without new credit inquiry",
    },
    {
        "action": "Maintain on-time payments on all accounts",
        "impact": "Payment history is 35% of FICO score",
        "timeline": "Ongoing, visible in 3-6 months",
        "why_now": "Consistent payments during dispute resolution prevent further damage",
    },
]


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity of word sets from two strings."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _is_substantially_same(desc_a: str, desc_b: str, threshold: float) -> bool:
    """Check if two dispute descriptions exceed the substantially-same threshold."""
    return _jaccard_similarity(desc_a, desc_b) >= threshold


def _sorted_items(profile: CreditProfile) -> list:
    """Return negative items sorted by priority (collections first)."""
    return sorted(
        profile.negative_items,
        key=lambda item: _ITEM_PRIORITY.get(item.type, 99),
    )


def _build_phase1(profile: CreditProfile, rotation: dict) -> dict:
    """Build Phase 1: Bureau Disputes (FCRA 611)."""
    sorted_items = _sorted_items(profile)
    steps = []
    for item in sorted_items:
        item_type = item.type.value
        rounds = rotation["issue_types"].get(item_type, [])
        round1 = rounds[0] if rounds else {"basis": "FCRA 611", "statutes": []}
        steps.append(
            {
                "item": item.description,
                "item_type": item_type,
                "creditor": item.creditor or "Unknown",
                "legal_basis": round1["basis"],
                "statutes": round1["statutes"],
                "target": "bureau",
                "estimated_days": 30,
            }
        )
    return {
        "phase": 1,
        "name": "Bureau Disputes",
        "legal_basis": "FCRA \u00a7611",
        "estimated_days": 30,
        "steps": steps,
        "why_this_order": (
            "Bureau disputes must be attempted before direct furnisher "
            "disputes. The bureaus are required to investigate under FCRA "
            "611, and this establishes the dispute record needed for Phase 2."
        ),
    }


def _check_blocked(
    item_desc: str,
    previous_disputes: list[dict],
    threshold: float,
) -> dict | None:
    """Check if an item is blocked by a substantially-same previous dispute."""
    for prev in previous_disputes:
        prev_desc = prev.get("description", "")
        if _is_substantially_same(item_desc, prev_desc, threshold):
            return {
                "description": item_desc,
                "blocked_by": prev_desc,
                "similarity": round(_jaccard_similarity(item_desc, prev_desc), 2),
                "rule": "16 CFR 660.4(f)",
            }
    return None


def _validate_basis(basis_type: str | None, permissible: list[dict]) -> bool:
    """Check if a basis type is in the permissible list."""
    valid_types = {p["type"] for p in permissible}
    return basis_type in valid_types


def _make_phase2_step(item, round2: dict, furnisher_cfg: dict) -> dict:
    """Create a single Phase 2 dispute step for an item."""
    return {
        "item": item.description,
        "item_type": item.type.value,
        "creditor": item.creditor or "Unknown",
        "legal_basis": round2["basis"],
        "statutes": round2["statutes"],
        "target": "furnisher",
        "estimated_days": 30,
        "documentation_required": furnisher_cfg["documentation_required"],
        "permissible_basis": round2["basis"],
    }


def _convert_to_bureau(step: dict, warnings: list[str]) -> None:
    """Convert an invalid direct furnisher dispute to bureau method."""
    step["target"] = "bureau"
    step["converted"] = True
    warnings.append(
        f"Dispute for '{step['item']}' converted to bureau method: "
        "basis not in permissible list per 16 CFR 660.4(a)"
    )


def _build_phase2(
    profile: CreditProfile,
    rotation: dict,
    furnisher_cfg: dict,
    context: dict,
) -> dict:
    """Build Phase 2: Direct Furnisher Disputes (FCRA 623(b))."""
    sorted_items = _sorted_items(profile)
    previous_disputes = context.get("previous_disputes", [])
    threshold = furnisher_cfg.get("substantially_same_threshold", 0.70)
    force_invalid = context.get("force_invalid_basis", False)

    steps: list[dict] = []
    blocked: list[dict] = []
    warnings: list[str] = []

    for item in sorted_items:
        rounds = rotation["issue_types"].get(item.type.value, [])
        round2 = rounds[1] if len(rounds) > 1 else {"basis": "FCRA 623", "statutes": []}

        block_info = _check_blocked(item.description, previous_disputes, threshold)
        if block_info is not None:
            blocked.append(block_info)
            continue

        step = _make_phase2_step(item, round2, furnisher_cfg)
        if force_invalid:
            _convert_to_bureau(step, warnings)
        steps.append(step)

    return {
        "phase": 2,
        "name": "Direct Furnisher Disputes",
        "legal_basis": "FCRA \u00a7623(b)",
        "estimated_days": 30,
        "steps": steps,
        "blocked_disputes": blocked,
        "compliance_warnings": warnings,
        "why_this_order": (
            "Direct furnisher disputes require new evidence and must follow "
            "an initial bureau dispute. Under FCRA 623(b), furnishers must "
            "investigate only after receiving notice from a bureau."
        ),
    }


def _build_phase3(context: dict, profile: CreditProfile) -> dict:
    """Build Phase 3: Credit Building recommendations."""
    parks = context.get("parks_result")

    if parks and parks.get("doors_analysis"):
        actions = _parks_based_actions(parks, profile)
    else:
        actions = _default_actions(profile)

    return {
        "phase": 3,
        "name": "Credit Building",
        "estimated_days": 90,
        "actions": actions,
        "why_this_order": (
            "Credit building starts after dispute resolution to maximize "
            "impact. New positive tradelines compound with removed negatives."
        ),
    }


def _parks_based_actions(parks: dict, profile: CreditProfile) -> list[dict]:
    """Generate credit-building actions using Parks doors analysis."""
    actions = []
    doors = parks.get("doors_analysis", [])
    for door_entry in doors:
        threshold = door_entry.get("threshold", 0)
        new_doors = door_entry.get("new_doors", [])
        if threshold > profile.current_score and new_doors:
            points = threshold - profile.current_score
            door_list = ", ".join(new_doors)
            actions.append(
                {
                    "action": f"Reach score {threshold} to unlock new doors",
                    "impact": f"Opens {len(new_doors)} new opportunities: {door_list}",
                    "timeline": f"Target {points} point improvement over 3-6 months",
                    "why_now": f"Score {threshold} unlocks doors that are currently closed",
                }
            )
            break

    actions.extend(_default_actions(profile))
    return actions


def _default_actions(profile: CreditProfile) -> list[dict]:
    """Generate basic credit-building actions based on score band."""
    return list(_DEFAULT_CREDIT_ACTIONS)


@register
class KingAgent(BaseAgent):
    """Pathway Commander: creates a 3-phase battle plan for credit improvement."""

    name = "king"
    description = "Creates a 3-phase dispute and credit-building battle plan"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        ctx = context or {}
        rotation = load_config("legal_basis_rotation")
        furnisher_cfg = load_config("direct_furnisher_requirements")

        phase1 = _build_phase1(profile, rotation)
        phase2 = _build_phase2(profile, rotation, furnisher_cfg, ctx)
        phase3 = _build_phase3(ctx, profile)

        phases = [phase1, phase2, phase3]
        total_days = sum(p["estimated_days"] for p in phases)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "phases": phases,
                "total_estimated_days": total_days,
                "dependency_graph": {
                    "phase_2_requires": ["phase_1_completion"],
                },
                "items_count": {
                    "phase_1": len(phase1["steps"]),
                    "phase_2": len(phase2["steps"]),
                    "phase_3": len(phase3["actions"]),
                },
            },
        )
