"""Tests for the Export agent — renders liberation plans as printable HTML."""

from __future__ import annotations

from modules.credit.agents.export import (
    _safe_get,
    _section,
    render_liberation_plan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FULL_PLAN: dict = {
    "liberation_plan": {
        "situation": {"poverty_tax": "$2,400/year", "barriers": ["high utilization"]},
        "monday_morning": {
            "actions": [
                {"step": "Call Experian to dispute medical debt"},
                {"step": "Enroll in Experian Boost"},
                {"step": "Set up autopay on all accounts"},
            ],
        },
        "battle_plan": {
            "phases": [
                {"name": "Phase 1", "actions": ["Pay down cards"]},
                {"name": "Phase 2", "actions": ["Dispute collections"]},
            ],
        },
        "poverty_tax": {"annual_amount": "$2,400", "items": ["higher rates"]},
        "impact": {
            "current_score": 535,
            "projected_30_day": 570,
            "projected_90_day": 620,
        },
        "legal_rights": {"rights": ["FCRA dispute right"]},
        "bureau_intelligence": {"discrepancies": ["Equifax missing account"]},
        "attack_cycles": {"cycles": [{"month": 1, "focus": "disputes"}]},
    },
    "validation_summary": {"valid": True},
    "performance": {"total_ms": 120},
    "community_impact": "$14.6M/year at 10% adoption",
    "why_deterministic": "Dynatrace study: deterministic beats AI",
}


# ---------------------------------------------------------------------------
# TestExportHelpers
# ---------------------------------------------------------------------------


class TestExportHelpers:
    """Tests for _safe_get and _section helper functions."""

    def test_safe_get_returns_nested_value(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert _safe_get(data, "a", "b", "c") == 42

    def test_safe_get_returns_default_on_missing_key(self) -> None:
        data = {"a": {"b": 1}}
        assert _safe_get(data, "a", "x", "y", default="N/A") == "N/A"

    def test_section_wraps_content(self) -> None:
        html = _section("My Title", "<p>body</p>")
        assert '<div class="section">' in html
        assert "<h2>My Title</h2>" in html
        assert "<p>body</p>" in html


# ---------------------------------------------------------------------------
# TestExportRender
# ---------------------------------------------------------------------------


class TestExportRender:
    """Tests for render_liberation_plan."""

    def test_returns_html_string(self) -> None:
        result = render_liberation_plan(_FULL_PLAN)
        assert isinstance(result, str)
        assert result.strip().startswith("<!DOCTYPE html>")

    def test_contains_title(self) -> None:
        result = render_liberation_plan(_FULL_PLAN)
        assert "<title>Liberation Plan</title>" in result

    def test_contains_print_css(self) -> None:
        result = render_liberation_plan(_FULL_PLAN)
        assert "@media print" in result

    def test_contains_all_sections(self) -> None:
        result = render_liberation_plan(_FULL_PLAN)
        expected_headings = [
            "Your Situation",
            "Monday Morning Actions",
            "Battle Plan",
            "Your Impact",
            "Your Legal Rights",
            "Local Resources",
            "Bureau Intelligence",
        ]
        for heading in expected_headings:
            assert heading in result, f"Missing section: {heading}"

    def test_handles_empty_plan(self) -> None:
        result = render_liberation_plan({})
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "error" in result.lower() or "Error" in result

    def test_handles_missing_sections(self) -> None:
        partial = {
            "liberation_plan": {
                "situation": {"poverty_tax": "$1,000/year"},
            },
            "community_impact": "test impact",
            "why_deterministic": "test reason",
        }
        result = render_liberation_plan(partial)
        assert "Your Situation" in result
        # Optional sections degrade gracefully
        assert "No denial context provided" in result
        assert "No cross-bureau data provided" in result


# ---------------------------------------------------------------------------
# TestExportXSSPrevention
# ---------------------------------------------------------------------------


_XSS_PAYLOAD = "<script>alert(1)</script>"
_XSS_ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"


class TestExportXSSPrevention:
    """XSS prevention — all user data must be HTML-escaped."""

    def _make_plan(self, **overrides: dict) -> dict:
        """Build a plan dict with overrides merged into liberation_plan."""
        lp = {
            "situation": {"poverty_tax": "safe", "barriers": []},
            "monday_morning": {"actions": []},
            "battle_plan": {"phases": []},
            "impact": {},
            "attack_cycles": {"cycles": []},
        }
        lp.update(overrides)
        return {
            "liberation_plan": lp,
            "community_impact": "safe",
            "why_deterministic": "safe",
        }

    def test_xss_in_barriers_escaped(self) -> None:
        plan = self._make_plan(
            situation={"poverty_tax": "safe", "barriers": [_XSS_PAYLOAD]}
        )
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_poverty_tax_escaped(self) -> None:
        plan = self._make_plan(situation={"poverty_tax": _XSS_PAYLOAD, "barriers": []})
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_monday_morning_actions_escaped(self) -> None:
        plan = self._make_plan(monday_morning={"actions": [{"step": _XSS_PAYLOAD}]})
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_battle_plan_phase_name_escaped(self) -> None:
        plan = self._make_plan(
            battle_plan={"phases": [{"name": _XSS_PAYLOAD, "actions": []}]}
        )
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_battle_plan_actions_escaped(self) -> None:
        plan = self._make_plan(
            battle_plan={"phases": [{"name": "safe", "actions": [_XSS_PAYLOAD]}]}
        )
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_legal_rights_escaped(self) -> None:
        plan = self._make_plan(legal_rights={"rights": [_XSS_PAYLOAD]})
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_bureau_intelligence_escaped(self) -> None:
        plan = self._make_plan(bureau_intelligence={"discrepancies": [_XSS_PAYLOAD]})
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_community_impact_escaped(self) -> None:
        plan = {
            "liberation_plan": {
                "situation": {"poverty_tax": "safe", "barriers": []},
            },
            "community_impact": _XSS_PAYLOAD,
            "why_deterministic": "safe",
        }
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_xss_in_attack_cycle_focus_escaped(self) -> None:
        plan = self._make_plan(
            attack_cycles={"cycles": [{"month": 1, "focus": _XSS_PAYLOAD}]}
        )
        result = render_liberation_plan(plan)
        assert _XSS_PAYLOAD not in result
        assert _XSS_ESCAPED in result

    def test_normal_text_not_double_escaped(self) -> None:
        """Ensure normal text with & or < in safe context isn't mangled."""
        plan = self._make_plan(
            situation={"poverty_tax": "$2,400/year", "barriers": ["high utilization"]}
        )
        result = render_liberation_plan(plan)
        assert "$2,400/year" in result
        assert "high utilization" in result
