"""Tests for Truth (Compliance Witness) agent."""

from __future__ import annotations

import re

import pytest

from modules.credit.agents.base import AgentResult, load_config
from modules.credit.types import CreditProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_truth():
    """Import and instantiate Truth agent."""
    from modules.credit.agents.truth import TruthAgent

    return TruthAgent()


def _get_banned_validator():
    """Import and instantiate BannedPatternValidator."""
    from modules.credit.agents.truth import BannedPatternValidator

    return BannedPatternValidator()


def _get_eoscar_validator():
    """Import and instantiate EoscarAntiTemplateValidator."""
    from modules.credit.agents.truth import EoscarAntiTemplateValidator

    return EoscarAntiTemplateValidator()


# ---------------------------------------------------------------------------
# Shared text samples
# ---------------------------------------------------------------------------

CLEAN_SPECIFIC_TEXT = (
    "The balance field on my Capital One account #1234 reports $3,200 "
    "but the correct value is $1,800. I have attached my March 2026 "
    "statement and payment receipt as supporting evidence."
)

FRAUD_TEXT = "We offer guaranteed removal of all negative items from your report."

EMOTIONAL_TEXT = "Please help me, this is so unfair. I demand you fix my report."

TEMPLATE_TEXT = (
    "I am writing to dispute the information on my credit report. "
    "As per my rights under the FCRA, please investigate this matter. "
    "I request that you delete this inaccurate information."
)

LEGAL_HEAVY_TEXT = (
    "Under FCRA 611 and FDCPA 809, pursuant to 15 USC 1681i "
    "and 15 USC 1692g, I cite CFR 12 1022.43. "
    "Per FCRA section 623, FDCPA requirements apply. "
    "Additional words here now."
)

BULLET_TEXT = (
    "- Item one about balance\n"
    "- Item two about payment status\n"
    "- Item three about date opened\n"
    "- Item four with $500 correct value\n"
    "Some closing paragraph with attached proof."
)


# ===========================================================================
# TestBannedPatternValidator
# ===========================================================================


class TestBannedPatternValidator:
    def test_clean_text_passes(self):
        v = _get_banned_validator()
        result = v.check(CLEAN_SPECIFIC_TEXT)
        assert result["passes"] is True
        assert result["warnings"] == []

    def test_croa_fraud_detected(self):
        v = _get_banned_validator()
        result = v.check(FRAUD_TEXT)
        assert result["passes"] is False
        cats = [w["category"] for w in result["warnings"]]
        assert "croa_fraud" in cats

    def test_emotional_pattern_detected(self):
        v = _get_banned_validator()
        result = v.check("Please help me fix my credit report issues.")
        assert result["passes"] is False
        cats = [w["category"] for w in result["warnings"]]
        assert "emotional_patterns" in cats

    def test_eoscar_template_detected(self):
        v = _get_banned_validator()
        result = v.check("I am writing to dispute the items on my report.")
        assert result["passes"] is False
        cats = [w["category"] for w in result["warnings"]]
        assert "eoscar_template_phrases" in cats

    def test_multiple_violations(self):
        v = _get_banned_validator()
        text = (
            "I am writing to dispute this. We guarantee guaranteed removal. "
            "Please help me."
        )
        result = v.check(text)
        assert result["passes"] is False
        cats = {w["category"] for w in result["warnings"]}
        assert len(cats) >= 2

    def test_case_insensitive(self):
        v = _get_banned_validator()
        result = v.check("We promise GUARANTEED REMOVAL of everything.")
        assert result["passes"] is False
        cats = [w["category"] for w in result["warnings"]]
        assert "croa_fraud" in cats

    def test_cpn_detected(self):
        v = _get_banned_validator()
        result = v.check("Apply for a CPN to start fresh.")
        assert result["passes"] is False
        cats = [w["category"] for w in result["warnings"]]
        assert "croa_fraud" in cats

    def test_empty_text_passes(self):
        v = _get_banned_validator()
        result = v.check("")
        assert result["passes"] is True
        assert result["warnings"] == []


# ===========================================================================
# TestEoscarAntiTemplateValidator
# ===========================================================================


class TestEoscarAntiTemplateValidator:
    def test_specific_dispute_hardened(self):
        v = _get_eoscar_validator()
        result = v.check(CLEAN_SPECIFIC_TEXT)
        assert result["specificity_score"] >= 0.6
        assert result["eoscar_hardened"] is True

    def test_generic_template_not_hardened(self):
        v = _get_eoscar_validator()
        result = v.check(TEMPLATE_TEXT)
        # Template text lacks specificity elements
        assert result["specificity_score"] < 0.6 or len(result["content_flags_found"]) > 0
        assert result["eoscar_hardened"] is False

    def test_structure_hash_format(self):
        v = _get_eoscar_validator()
        result = v.check(CLEAN_SPECIFIC_TEXT)
        assert re.match(r"^\d+:\d+:(prose|bullets)$", result["structure_hash"])

    def test_bullet_format_detected(self):
        v = _get_eoscar_validator()
        result = v.check(BULLET_TEXT)
        assert result["structure_hash"].endswith(":bullets")

    def test_prose_format_detected(self):
        v = _get_eoscar_validator()
        result = v.check(CLEAN_SPECIFIC_TEXT)
        assert result["structure_hash"].endswith(":prose")

    def test_legal_language_ratio_excessive(self):
        v = _get_eoscar_validator()
        result = v.check(LEGAL_HEAVY_TEXT)
        assert result["legal_language_ratio"] > 0.05

    def test_legal_language_ratio_normal(self):
        v = _get_eoscar_validator()
        result = v.check(CLEAN_SPECIFIC_TEXT)
        assert result["legal_language_ratio"] <= 0.05

    def test_content_flags_found(self):
        v = _get_eoscar_validator()
        text = "I am writing to formally dispute the balance on my account."
        result = v.check(text)
        assert len(result["content_flags_found"]) > 0

    def test_specificity_score_calculation(self):
        v = _get_eoscar_validator()
        # Text with all four elements
        text = (
            "The balance field reports $3,200 but the correct "
            "value should be $1,800. I have attached my statement as proof."
        )
        result = v.check(text)
        assert 0.0 <= result["specificity_score"] <= 1.0
        assert result["specificity_score"] >= 0.75  # all 4 present


# ===========================================================================
# TestTruthAgent
# ===========================================================================


class TestTruthAgent:
    def test_skipped_without_text(self, poor_profile_structured):
        agent = _get_truth()
        result = agent.execute(poor_profile_structured)
        assert result.status == "skipped"

    def test_clean_specific_text_passes(self, poor_profile_structured):
        agent = _get_truth()
        ctx = {"text_to_check": CLEAN_SPECIFIC_TEXT}
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.status == "success"
        assert result.data["passes"] is True

    def test_fraud_text_fails(self, poor_profile_structured):
        agent = _get_truth()
        ctx = {"text_to_check": FRAUD_TEXT}
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.status == "success"
        assert result.data["passes"] is False

    def test_template_text_fails(self, poor_profile_structured):
        agent = _get_truth()
        ctx = {"text_to_check": TEMPLATE_TEXT}
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.status == "success"
        assert result.data["passes"] is False

    def test_recommendations_generated(self, poor_profile_structured):
        agent = _get_truth()
        ctx = {"text_to_check": FRAUD_TEXT}
        result = agent.execute(poor_profile_structured, context=ctx)
        assert result.data["passes"] is False
        assert len(result.data["recommendations"]) > 0

    def test_agent_registered(self):
        # Importing the module triggers registration
        import modules.credit.agents.truth  # noqa: F401
        from modules.credit.agents import get_agent

        assert get_agent("truth") is not None

    def test_agent_name(self):
        agent = _get_truth()
        assert agent.name == "truth"

    def test_result_structure(self, poor_profile_structured):
        agent = _get_truth()
        ctx = {"text_to_check": CLEAN_SPECIFIC_TEXT}
        result = agent.execute(poor_profile_structured, context=ctx)
        data = result.data
        assert "passes" in data
        assert "banned_pattern_check" in data
        assert "eoscar_check" in data
        assert "recommendations" in data
        assert "passes" in data["banned_pattern_check"]
        assert "warnings" in data["banned_pattern_check"]
        assert "structure_hash" in data["eoscar_check"]
        assert "specificity_score" in data["eoscar_check"]
        assert "legal_language_ratio" in data["eoscar_check"]
        assert "content_flags_found" in data["eoscar_check"]
        assert "eoscar_hardened" in data["eoscar_check"]
