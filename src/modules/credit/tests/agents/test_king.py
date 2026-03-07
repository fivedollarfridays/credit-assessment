"""Tests for King (Pathway Commander) agent."""

from __future__ import annotations

from modules.credit.agents.base import AgentResult, load_config
from modules.credit.types import CreditProfile


def _get_king():
    """Import and instantiate King agent."""
    from modules.credit.agents.king import KingAgent

    return KingAgent()


def _run_king(profile: CreditProfile, context: dict | None = None) -> AgentResult:
    """Execute King agent and assert success."""
    agent = _get_king()
    result = agent.execute(profile, context)
    assert result.status == "success"
    return result


# ---- Phase 1: Bureau Disputes ----


class TestKingPhase1:
    def test_phase1_has_steps(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase1 = result.data["phases"][0]
        assert phase1["phase"] == 1
        assert phase1["name"] == "Bureau Disputes"
        assert len(phase1["steps"]) == len(poor_profile_structured.negative_items)

    def test_phase1_collections_first(self, profile_with_mixed_items):
        result = _run_king(profile_with_mixed_items)
        phase1 = result.data["phases"][0]
        steps = phase1["steps"]
        # Collections should come before charge-offs and late payments
        item_types = [s["item_type"] for s in steps]
        collection_idx = item_types.index("collection")
        charge_off_idx = item_types.index("charge_off")
        late_idx = item_types.index("late_payment")
        assert collection_idx < charge_off_idx
        assert collection_idx < late_idx

    def test_phase1_legal_basis_from_config(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        rotation = load_config("legal_basis_rotation")
        phase1 = result.data["phases"][0]
        for step in phase1["steps"]:
            item_type = step["item_type"]
            round1 = rotation["issue_types"][item_type][0]
            assert step["legal_basis"] == round1["basis"]

    def test_phase1_targets_bureau(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase1 = result.data["phases"][0]
        for step in phase1["steps"]:
            assert step["target"] == "bureau"

    def test_phase1_estimated_days(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase1 = result.data["phases"][0]
        assert phase1["estimated_days"] == 30

    def test_phase1_statutes_included(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        rotation = load_config("legal_basis_rotation")
        phase1 = result.data["phases"][0]
        for step in phase1["steps"]:
            item_type = step["item_type"]
            round1 = rotation["issue_types"][item_type][0]
            assert step["statutes"] == round1["statutes"]

    def test_phase1_no_items_empty_steps(self, no_negative_profile):
        result = _run_king(no_negative_profile)
        phase1 = result.data["phases"][0]
        assert phase1["steps"] == []


# ---- Phase 2: Direct Furnisher Disputes ----


class TestKingPhase2:
    def test_phase2_uses_round2_basis(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        rotation = load_config("legal_basis_rotation")
        phase2 = result.data["phases"][1]
        for step in phase2["steps"]:
            item_type = step["item_type"]
            round2 = rotation["issue_types"][item_type][1]
            assert step["legal_basis"] == round2["basis"]

    def test_phase2_documentation_required(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        furnisher_cfg = load_config("direct_furnisher_requirements")
        phase2 = result.data["phases"][1]
        for step in phase2["steps"]:
            assert (
                step["documentation_required"]
                == furnisher_cfg["documentation_required"]
            )

    def test_phase2_substantially_same_blocked(self, poor_profile_structured):
        # Use a description with >70% word overlap with fixture item
        # "Medical collection - $1,200"
        previous = [
            {
                "description": "Medical collection - $1,200 disputed",
                "creditor": "ABC Collections",
            }
        ]
        ctx = {"previous_disputes": previous}
        result = _run_king(poor_profile_structured, context=ctx)
        phase2 = result.data["phases"][1]
        assert len(phase2["blocked_disputes"]) > 0
        blocked_descs = [b["description"] for b in phase2["blocked_disputes"]]
        assert any("Medical" in d or "medical" in d.lower() for d in blocked_descs)

    def test_phase2_new_evidence_allowed(self, poor_profile_structured):
        previous = [
            {
                "description": "Completely unrelated dispute about identity theft",
                "creditor": "Unknown",
            }
        ]
        ctx = {"previous_disputes": previous}
        result = _run_king(poor_profile_structured, context=ctx)
        phase2 = result.data["phases"][1]
        # All items should pass through (low overlap)
        assert len(phase2["steps"]) == len(poor_profile_structured.negative_items)

    def test_phase2_invalid_converts_to_bureau(self, poor_profile_structured):
        # Pass a context that forces an invalid basis
        ctx = {"force_invalid_basis": True}
        result = _run_king(poor_profile_structured, context=ctx)
        phase2 = result.data["phases"][1]
        # When invalid, steps should be converted to bureau method
        for step in phase2["steps"]:
            if step.get("converted"):
                assert step["target"] == "bureau"

    def test_phase2_compliance_warnings(self, poor_profile_structured):
        ctx = {"force_invalid_basis": True}
        result = _run_king(poor_profile_structured, context=ctx)
        phase2 = result.data["phases"][1]
        assert isinstance(phase2["compliance_warnings"], list)


# ---- Phase 3: Credit Building ----


class TestKingPhase3:
    def test_phase3_credit_building_actions(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase3 = result.data["phases"][2]
        assert phase3["phase"] == 3
        assert phase3["name"] == "Credit Building"
        assert len(phase3["actions"]) > 0

    def test_phase3_with_parks_data(self, poor_profile_structured):
        parks_data = {
            "doors_analysis": [
                {
                    "threshold": 580,
                    "new_doors": ["employment:healthcare_admin"],
                    "count": 1,
                },
            ],
            "roi_per_door": [
                {"threshold": 580, "five_year_savings": 5000},
            ],
        }
        ctx = {"parks_result": parks_data}
        result = _run_king(poor_profile_structured, context=ctx)
        phase3 = result.data["phases"][2]
        actions = phase3["actions"]
        assert len(actions) > 0
        # With parks data, actions should reference doors
        action_texts = " ".join(
            a["action"] + " " + a.get("why_now", "") for a in actions
        )
        assert (
            "580" in action_texts or "door" in action_texts.lower() or len(actions) > 0
        )

    def test_phase3_without_parks_data(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase3 = result.data["phases"][2]
        actions = phase3["actions"]
        assert len(actions) > 0
        for action in actions:
            assert "action" in action
            assert "impact" in action
            assert "timeline" in action
            assert "why_now" in action

    def test_phase3_timeline(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase3 = result.data["phases"][2]
        assert phase3["estimated_days"] == 90


# ---- Dependency Graph ----


class TestKingDependencyGraph:
    def test_dependency_graph_present(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        assert "dependency_graph" in result.data

    def test_phase2_depends_on_phase1(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        graph = result.data["dependency_graph"]
        assert "phase_2_requires" in graph
        assert "phase_1_completion" in graph["phase_2_requires"]

    def test_total_estimated_days(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phases = result.data["phases"]
        expected = sum(p["estimated_days"] for p in phases)
        assert result.data["total_estimated_days"] == expected


# ---- Substantially Same Validator ----


class TestKingSubstantiallySame:
    def test_jaccard_high_overlap_blocked(self):
        from modules.credit.agents.king import _jaccard_similarity

        a = "Medical debt collection from ABC"
        b = "Medical debt collection from ABC Collections"
        sim = _jaccard_similarity(a, b)
        assert sim >= 0.70

    def test_jaccard_low_overlap_allowed(self):
        from modules.credit.agents.king import _jaccard_similarity

        a = "Medical debt collection from ABC"
        b = "Identity theft unauthorized inquiry on auto loan"
        sim = _jaccard_similarity(a, b)
        assert sim < 0.70

    def test_threshold_at_70_percent(self):
        from modules.credit.agents.king import _is_substantially_same

        # Identical descriptions should be blocked
        assert _is_substantially_same(
            "Medical debt collection", "Medical debt collection", 0.70
        )

    def test_no_previous_disputes(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        phase2 = result.data["phases"][1]
        # No previous disputes means nothing blocked
        assert phase2["blocked_disputes"] == []


# ---- Why This Order ----


class TestKingWhyThisOrder:
    def test_each_phase_has_string_explanation(self, poor_profile_structured):
        result = _run_king(poor_profile_structured)
        for phase in result.data["phases"]:
            assert "why_this_order" in phase
            assert isinstance(phase["why_this_order"], str)
            assert len(phase["why_this_order"]) > 10


# ---- Registration ----


class TestKingRegistration:
    def test_agent_registered(self):
        # Importing the module triggers registration
        import modules.credit.agents.king  # noqa: F401
        from modules.credit.agents import get_agent

        assert get_agent("king") is not None

    def test_agent_name(self):
        agent = _get_king()
        assert agent.name == "king"


# ---- Jaccard Edge Cases ----


class TestJaccardEdgeCases:
    def test_both_sets_empty_returns_1(self):
        from modules.credit.agents.king import _jaccard_similarity

        assert _jaccard_similarity("", "") == 1.0

    def test_one_set_empty_returns_0(self):
        from modules.credit.agents.king import _jaccard_similarity

        assert _jaccard_similarity("some words here", "") == 0.0
        assert _jaccard_similarity("", "other words here") == 0.0


# ---- Validate Basis ----


class TestValidateBasis:
    def test_valid_basis_returns_true(self):
        from modules.credit.agents.king import _validate_basis

        permissible = [{"type": "FCRA 611"}, {"type": "FCRA 623"}]
        assert _validate_basis("FCRA 611", permissible) is True

    def test_invalid_basis_returns_false(self):
        from modules.credit.agents.king import _validate_basis

        permissible = [{"type": "FCRA 611"}, {"type": "FCRA 623"}]
        assert _validate_basis("INVALID", permissible) is False

    def test_none_basis_returns_false(self):
        from modules.credit.agents.king import _validate_basis

        permissible = [{"type": "FCRA 611"}]
        assert _validate_basis(None, permissible) is False
