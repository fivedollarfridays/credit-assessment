"""Gray (Rights Enforcer) agent -- adverse action decoder.

Only fires when denial_context is provided. Decodes denial reasons,
checks for FCRA violations, and recommends a dispute letter bridge.
"""

from __future__ import annotations

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config

_SCORE_DISCLOSURE_TYPES = frozenset({"credit", "insurance", "auto_loan"})
_SCORE_KEYWORDS = ("credit score", "score disclosure", "score used")


def _decode_reasons(denial_reasons: list[str], decoder_cfg: dict) -> list[dict]:
    """Decode each denial reason into plain English with metadata."""
    known = decoder_cfg["denial_reasons"]
    decoded: list[dict] = []
    for reason in denial_reasons:
        lower = reason.lower().strip()
        if lower in known:
            entry = known[lower]
            decoded.append(
                {
                    "original": reason,
                    "plain_english": entry["plain_english"],
                    "likely_items": entry["likely_items"],
                    "recommended_action": entry["recommended_action"],
                }
            )
        else:
            decoded.append(
                {
                    "original": reason,
                    "plain_english": "Contact creditor for details on this denial reason",
                    "likely_items": [],
                    "recommended_action": "contact_creditor",
                }
            )
    return decoded


def _check_violations(
    denial_type: str,
    notices_received: list[str],
    rules_cfg: dict,
) -> list[dict]:
    """Compare received notices against required notices for the denial type."""
    type_rules = rules_cfg["denial_types"].get(denial_type, {})
    required = type_rules.get("required_notices", [])
    damages = type_rules.get("violation_damages", {})
    governing_law = type_rules.get("governing_law", "")

    received_lower = {n.lower() for n in notices_received}
    violations: list[dict] = []

    for notice in required:
        if not _notice_matches(notice.lower(), received_lower):
            violations.append(
                {
                    "type": "missing_notice",
                    "description": f"Required notice not received: {notice}",
                    "governing_law": governing_law,
                    "damages": damages,
                }
            )

    return violations


def _notice_matches(required: str, received_set: set[str]) -> bool:
    """Check if a required notice is satisfied by any received notice."""
    for received in received_set:
        if required == received:
            return True
        # Handle score-related keywords for FCRA 609(f)
        if any(kw in required for kw in _SCORE_KEYWORDS):
            if any(kw in received for kw in _SCORE_KEYWORDS):
                return True
    return False


def _build_letter_bridge(
    denial_type: str,
    creditor_name: str,
    violations: list[dict],
    decoded_reasons: list[dict],
    state: str,
) -> dict:
    """Build parameters for the dispute letter generation endpoint."""
    return {
        "letter_type": "adverse_action_response",
        "denial_type": denial_type,
        "creditor_name": creditor_name,
        "violations_found": [v["description"] for v in violations],
        "denial_reasons_decoded": [
            {"original": d["original"], "plain_english": d["plain_english"]}
            for d in decoded_reasons
        ],
        "state": state,
    }


@register
class GrayAgent(BaseAgent):
    """Adverse action decoder and FCRA violation checker."""

    name = "gray"
    description = "Rights Enforcer: decodes denials, checks FCRA violations"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        denial_ctx = (context or {}).get("denial_context")
        if not denial_ctx:
            return AgentResult(agent_name=self.name, status="skipped")

        denial_type = denial_ctx.get("denial_type", "credit")
        denial_reasons = denial_ctx.get("denial_reasons", [])
        creditor_name = denial_ctx.get("creditor_name", "Unknown")
        state = denial_ctx.get("state", "AL")
        notices_received = denial_ctx.get("notices_received", [])

        decoder_cfg = load_config("denial_decoder")
        rules_cfg = load_config("adverse_action_rules")

        decoded = _decode_reasons(denial_reasons, decoder_cfg)
        violations = _check_violations(denial_type, notices_received, rules_cfg)

        type_rules = rules_cfg["denial_types"].get(denial_type, {})
        sol_years = type_rules.get("statute_of_limitations_years", 2)

        letter = _build_letter_bridge(
            denial_type, creditor_name, violations, decoded, state
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "denial_type": denial_type,
                "decoded_reasons": decoded,
                "violations": violations,
                "has_violations": len(violations) > 0,
                "state": state,
                "recommended_letter": letter,
                "statute_of_limitations_years": sol_years,
            },
        )
