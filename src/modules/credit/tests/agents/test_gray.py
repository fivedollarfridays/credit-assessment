"""Tests for Gray (Rights Enforcer) agent."""

from __future__ import annotations


from modules.credit.agents.base import AgentResult, load_config
from modules.credit.types import CreditProfile


def _get_gray():
    """Import and instantiate Gray agent."""
    from modules.credit.agents.gray import GrayAgent

    return GrayAgent()


def _run_gray(
    profile: CreditProfile,
    context: dict | None = None,
    *,
    expect_status: str = "success",
) -> AgentResult:
    """Execute Gray agent and assert expected status."""
    agent = _get_gray()
    result = agent.execute(profile, context)
    assert result.status == expect_status
    return result


def _make_denial_context(**overrides) -> dict:
    """Build a standard denial_context dict with sensible defaults."""
    base = {
        "denial_type": "credit",
        "denial_reasons": ["serious delinquency"],
        "creditor_name": "ABC Bank",
        "state": "AL",
        "notices_received": [
            "specific reasons for denial OR right to request reasons",
            "CRA contact info",
            "credit score used",
        ],
    }
    base.update(overrides)
    return {"denial_context": base}


# ---- Skip Behavior ----


class TestGraySkip:
    def test_skipped_without_denial_context(self, poor_profile_structured):
        """No denial_context in context -> status='skipped'."""
        result = _run_gray(
            poor_profile_structured, context=None, expect_status="skipped"
        )
        assert result.agent_name == "gray"

    def test_skipped_with_empty_context(self, poor_profile_structured):
        """Empty context dict -> status='skipped'."""
        result = _run_gray(poor_profile_structured, context={}, expect_status="skipped")
        assert result.agent_name == "gray"


# ---- Denial Decoder ----


class TestGrayDenialDecoder:
    def test_decode_serious_delinquency(self, poor_profile_structured):
        """'serious delinquency' should be decoded to plain English."""
        ctx = _make_denial_context(denial_reasons=["serious delinquency"])
        result = _run_gray(poor_profile_structured, context=ctx)
        decoded = result.data["decoded_reasons"]
        assert len(decoded) == 1
        assert decoded[0]["original"] == "serious delinquency"
        assert (
            "past due" in decoded[0]["plain_english"].lower()
            or "collections" in decoded[0]["plain_english"].lower()
        )

    def test_decode_multiple_reasons(self, poor_profile_structured):
        """Multiple denial reasons should all be decoded."""
        reasons = [
            "serious delinquency",
            "proportion of balances to credit limits",
        ]
        ctx = _make_denial_context(denial_reasons=reasons)
        result = _run_gray(poor_profile_structured, context=ctx)
        decoded = result.data["decoded_reasons"]
        assert len(decoded) == 2
        originals = {d["original"] for d in decoded}
        assert originals == set(reasons)

    def test_unknown_reason_fallback(self, poor_profile_structured):
        """Unrecognized denial reason gets a generic fallback message."""
        ctx = _make_denial_context(denial_reasons=["some unknown reason"])
        result = _run_gray(poor_profile_structured, context=ctx)
        decoded = result.data["decoded_reasons"]
        assert len(decoded) == 1
        assert decoded[0]["original"] == "some unknown reason"
        assert "contact" in decoded[0]["plain_english"].lower()

    def test_recommended_action_included(self, poor_profile_structured):
        """Each decoded reason must include a recommended_action."""
        ctx = _make_denial_context(
            denial_reasons=["serious delinquency", "too many accounts with balances"]
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        for item in result.data["decoded_reasons"]:
            assert "recommended_action" in item
            assert isinstance(item["recommended_action"], str)
            assert len(item["recommended_action"]) > 0

    def test_likely_items_included(self, poor_profile_structured):
        """Each decoded reason must include a likely_items list."""
        ctx = _make_denial_context(denial_reasons=["serious delinquency"])
        result = _run_gray(poor_profile_structured, context=ctx)
        decoded = result.data["decoded_reasons"]
        assert "likely_items" in decoded[0]
        assert isinstance(decoded[0]["likely_items"], list)
        assert len(decoded[0]["likely_items"]) > 0

    def test_all_known_reasons_decoded(self, poor_profile_structured):
        """All 6 known reasons in denial_decoder.json should be decodable."""
        decoder_cfg = load_config("denial_decoder")
        all_reasons = list(decoder_cfg["denial_reasons"].keys())
        assert len(all_reasons) == 6
        ctx = _make_denial_context(denial_reasons=all_reasons)
        result = _run_gray(poor_profile_structured, context=ctx)
        decoded = result.data["decoded_reasons"]
        assert len(decoded) == 6
        for item in decoded:
            assert "contact creditor" not in item["plain_english"].lower(), (
                f"Known reason '{item['original']}' should not get fallback"
            )


# ---- Violations ----


class TestGrayViolations:
    def test_missing_notice_is_violation(self, poor_profile_structured):
        """Missing a required notice should produce a violation."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=["CRA contact info"],  # missing others
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        violations = result.data["violations"]
        assert len(violations) > 0
        # At least one violation for missing notices
        descriptions = [v["description"] for v in violations]
        assert any(
            "missing" in d.lower() or "not received" in d.lower() for d in descriptions
        )

    def test_all_notices_received_no_violations(self, poor_profile_structured):
        """When all required notices are received, no violations."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=[
                "specific reasons for denial OR right to request reasons",
                "CRA contact info",
                "credit score used",
            ],
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        assert result.data["violations"] == []
        assert result.data["has_violations"] is False

    def test_employment_pre_adverse_required(self, poor_profile_structured):
        """Employment denial requires pre-adverse action notice."""
        ctx = _make_denial_context(
            denial_type="employment",
            notices_received=["final adverse action notice"],  # missing pre-adverse
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        violations = result.data["violations"]
        assert len(violations) > 0
        missing_descriptions = " ".join(v["description"].lower() for v in violations)
        assert "pre-adverse" in missing_descriptions

    def test_score_disclosure_violation(self, poor_profile_structured):
        """Credit denial without score disclosure is a violation."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=[
                "specific reasons for denial OR right to request reasons",
                "CRA contact info",
                # missing "credit score used"
            ],
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        violations = result.data["violations"]
        assert len(violations) > 0
        descriptions = " ".join(v["description"].lower() for v in violations)
        assert "score" in descriptions or "credit score" in descriptions

    def test_has_violations_flag(self, poor_profile_structured):
        """has_violations should be True when violations are present."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=[],  # no notices at all
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        assert result.data["has_violations"] is True

    def test_violation_includes_damages(self, poor_profile_structured):
        """Each violation should include damages info from the config."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=[],
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        violations = result.data["violations"]
        assert len(violations) > 0
        for v in violations:
            assert "damages" in v
            assert isinstance(v["damages"], dict)


# ---- State Laws ----


class TestGrayStateLaws:
    def test_default_state_al(self, poor_profile_structured):
        """When no state provided, defaults to AL."""
        denial = {
            "denial_type": "credit",
            "denial_reasons": ["serious delinquency"],
            "notices_received": [],
        }
        ctx = {"denial_context": denial}
        result = _run_gray(poor_profile_structured, context=ctx)
        assert result.data["state"] == "AL"

    def test_state_override_applied(self, poor_profile_structured):
        """State from denial_context should be used."""
        ctx = _make_denial_context(state="CA")
        result = _run_gray(poor_profile_structured, context=ctx)
        assert result.data["state"] == "CA"

    def test_statute_of_limitations(self, poor_profile_structured):
        """Output should include statute_of_limitations_years."""
        ctx = _make_denial_context(denial_type="employment")
        result = _run_gray(poor_profile_structured, context=ctx)
        assert "statute_of_limitations_years" in result.data
        assert isinstance(result.data["statute_of_limitations_years"], int)
        assert result.data["statute_of_limitations_years"] == 2


# ---- Letter Bridge ----


class TestGrayLetterBridge:
    def test_letter_bridge_structure(self, poor_profile_structured):
        """recommended_letter should have the required keys."""
        ctx = _make_denial_context()
        result = _run_gray(poor_profile_structured, context=ctx)
        letter = result.data["recommended_letter"]
        assert letter["letter_type"] == "adverse_action_response"
        assert "denial_type" in letter
        assert "creditor_name" in letter
        assert "violations_found" in letter
        assert "denial_reasons_decoded" in letter
        assert "state" in letter

    def test_letter_includes_violations(self, poor_profile_structured):
        """Violations should be passed through to letter params."""
        ctx = _make_denial_context(
            denial_type="credit",
            notices_received=[],  # triggers violations
        )
        result = _run_gray(poor_profile_structured, context=ctx)
        letter = result.data["recommended_letter"]
        assert isinstance(letter["violations_found"], list)
        assert len(letter["violations_found"]) > 0

    def test_letter_includes_creditor(self, poor_profile_structured):
        """creditor_name should be passed through to letter params."""
        ctx = _make_denial_context(creditor_name="XYZ Lender")
        result = _run_gray(poor_profile_structured, context=ctx)
        letter = result.data["recommended_letter"]
        assert letter["creditor_name"] == "XYZ Lender"


# ---- Registration ----


class TestGrayRegistration:
    def test_agent_registered(self):
        """Gray should be in the agent registry."""
        from modules.credit.agents import _REGISTRY

        # Force import to trigger registration
        import modules.credit.agents.gray  # noqa: F401

        assert "gray" in _REGISTRY

    def test_agent_name(self):
        """Agent instance name should be 'gray'."""
        agent = _get_gray()
        assert agent.name == "gray"
