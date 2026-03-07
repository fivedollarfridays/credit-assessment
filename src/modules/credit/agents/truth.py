"""Truth (Compliance Witness) agent — CROA fraud and e-OSCAR template detection."""

from __future__ import annotations

import re

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config


# ---------------------------------------------------------------------------
# Validators (not agents — plain classes)
# ---------------------------------------------------------------------------


class BannedPatternValidator:
    """Check text against CROA fraud, emotional, and e-OSCAR template patterns."""

    _CATEGORIES = ("croa_fraud", "emotional_patterns", "eoscar_template_phrases")

    def __init__(self) -> None:
        self._patterns = load_config("banned_patterns")

    def check(self, text: str) -> dict:
        """Return ``{"passes": bool, "warnings": [...]}``."""
        warnings: list[dict] = []
        lower = text.lower()
        for category in self._CATEGORIES:
            for entry in self._patterns.get(category, []):
                if entry["pattern"].lower() in lower:
                    warnings.append(
                        {
                            "category": category,
                            "pattern": entry["pattern"],
                            "reason": entry["reason"],
                        }
                    )
        return {"passes": len(warnings) == 0, "warnings": warnings}


class EoscarAntiTemplateValidator:
    """Detect template-like dispute content via structural analysis."""

    _FIELD_NAMES = re.compile(
        r"balance|date opened|account status|payment status",
        re.IGNORECASE,
    )
    _REPORTED_VALUE = re.compile(
        r"\$\s*\d|"  # dollar amount
        r"\d{4}-\d{2}-\d{2}|"  # date
        r"\b(paid|unpaid|delinquent|current|charged off)\b",
        re.IGNORECASE,
    )
    _CORRECT_VALUE = re.compile(r"\b(correct|actual|should be)\b", re.IGNORECASE)
    _EVIDENCE = re.compile(
        r"\b(attached|enclosed|statement|receipt|proof)\b", re.IGNORECASE
    )
    _LEGAL_CITATIONS = re.compile(r"\u00a7|USC|CFR|FCRA|FDCPA", re.IGNORECASE)

    def __init__(self) -> None:
        self._config = load_config("eoscar_patterns")

    def check(self, text: str) -> dict:
        """Analyse *text* and return structural + specificity metrics."""
        structure_hash = self._compute_structure_hash(text)
        specificity = self._compute_specificity(text)
        legal_ratio = self._compute_legal_ratio(text)
        content_flags = self._find_content_flags(text)

        hardened = (
            specificity >= 0.6 and len(content_flags) == 0 and legal_ratio <= 0.05
        )

        return {
            "structure_hash": structure_hash,
            "specificity_score": specificity,
            "legal_language_ratio": round(legal_ratio, 4),
            "content_flags_found": content_flags,
            "eoscar_hardened": hardened,
        }

    # -- private helpers ---------------------------------------------------

    def _compute_structure_hash(self, text: str) -> str:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        paragraph_count = max(len(paragraphs), 1)

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        else:
            avg_len = 0.0

        lines = [ln for ln in text.split("\n") if ln.strip()]
        if lines:
            bullet_lines = sum(
                1
                for ln in lines
                if re.match(r"^\s*[-*]\s", ln) or re.match(r"^\s*\d+[.)]\s", ln)
            )
            fmt = "bullets" if bullet_lines / len(lines) > 0.30 else "prose"
        else:
            fmt = "prose"

        return f"{paragraph_count}:{round(avg_len)}:{fmt}"

    def _compute_specificity(self, text: str) -> float:
        present = 0
        if self._FIELD_NAMES.search(text):
            present += 1
        if self._REPORTED_VALUE.search(text):
            present += 1
        if self._CORRECT_VALUE.search(text):
            present += 1
        if self._EVIDENCE.search(text):
            present += 1
        return present / 4.0

    def _compute_legal_ratio(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        citations = len(self._LEGAL_CITATIONS.findall(text))
        return citations / len(words)

    def _find_content_flags(self, text: str) -> list[str]:
        lower = text.lower()
        return [
            flag
            for flag in self._config.get("content_flags", [])
            if flag.lower() in lower
        ]


# ---------------------------------------------------------------------------
# Truth Agent
# ---------------------------------------------------------------------------


def _build_recommendations(banned: dict, eoscar: dict) -> list[str]:
    """Generate human-readable recommendations from validation results."""
    recs: list[str] = []

    for warning in banned.get("warnings", []):
        if warning["category"] == "croa_fraud":
            recs.append(f"Remove CROA violation: {warning['reason']}")
        elif warning["category"] == "emotional_patterns":
            recs.append(f"Replace emotional language: {warning['reason']}")
        elif warning["category"] == "eoscar_template_phrases":
            recs.append(f"Rewrite template phrase: {warning['reason']}")

    if not eoscar.get("eoscar_hardened", False):
        if eoscar.get("specificity_score", 0) < 0.6:
            recs.append(
                "Add specific details: field name, reported value, "
                "correct value, and supporting evidence"
            )
        if eoscar.get("content_flags_found"):
            recs.append("Rewrite flagged template phrases to be original")
        if eoscar.get("legal_language_ratio", 0) > 0.05:
            recs.append("Reduce legal citations — focus on facts, not statutes")

    return recs


@register
class TruthAgent(BaseAgent):
    """Compliance Witness — validates text against CROA and e-OSCAR rules."""

    name = "truth"
    description = "Checks outputs for CROA fraud patterns, emotional language, and e-OSCAR templates"

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        text = (context or {}).get("text_to_check")
        if not text:
            return AgentResult(agent_name=self.name, status="skipped")

        banned_result = BannedPatternValidator().check(text)
        eoscar_result = EoscarAntiTemplateValidator().check(text)
        recommendations = _build_recommendations(banned_result, eoscar_result)

        passes = banned_result["passes"] and eoscar_result["eoscar_hardened"]

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "passes": passes,
                "banned_pattern_check": banned_result,
                "eoscar_check": eoscar_result,
                "recommendations": recommendations,
            },
        )
