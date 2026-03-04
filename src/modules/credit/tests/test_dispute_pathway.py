"""Tests for dispute pathway generator — TDD: written before implementation."""

import pytest

from modules.credit.types import (
    ActionPriority,
    CreditProfile,
    DisputePathway,
    DisputeStep,
)


class TestIssuePatterns:
    """Test ISSUE_PATTERNS constant."""

    def test_has_collection_pattern(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        assert "collection" in ISSUE_PATTERNS

    def test_has_late_payment_pattern(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        assert "late_payment" in ISSUE_PATTERNS

    def test_has_charge_off_pattern(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        assert "charge_off" in ISSUE_PATTERNS

    def test_has_all_eight_patterns(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        assert len(ISSUE_PATTERNS) == 8

    def test_patterns_have_legal_theories(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        for key, pattern in ISSUE_PATTERNS.items():
            assert "legal_theories" in pattern, f"{key} missing legal_theories"
            assert len(pattern["legal_theories"]) > 0

    def test_patterns_have_statutes(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        for key, pattern in ISSUE_PATTERNS.items():
            assert "statutes" in pattern, f"{key} missing statutes"
            assert len(pattern["statutes"]) > 0

    def test_patterns_have_priority(self):
        from modules.credit.dispute_pathway import ISSUE_PATTERNS

        for key, pattern in ISSUE_PATTERNS.items():
            assert "priority" in pattern, f"{key} missing priority"
            assert isinstance(pattern["priority"], ActionPriority)


class TestClassifyIssueType:
    """Test issue type classification from negative item strings."""

    def test_collection_classified(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("collection_medical_2500") == "collection"

    def test_late_payment_classified(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("late_payment_30day") == "late_payment"

    def test_charge_off_classified(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("charge_off_credit_card") == "charge_off"

    def test_identity_theft_classified(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("identity_theft_account") == "identity_theft"

    def test_unknown_defaults_to_late_payment(self):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        assert gen._classify_issue_type("unknown_thing") == "late_payment"


class TestGeneratePathway:
    """Test full pathway generation."""

    def test_no_negatives_empty_pathway(self, good_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(good_credit_profile)
        assert isinstance(pathway, DisputePathway)
        assert len(pathway.steps) == 0
        assert pathway.total_estimated_days == 0

    def test_collections_generate_steps(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        assert len(pathway.steps) >= 3

    def test_late_payment_generates_step(self, fair_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(fair_credit_profile)
        assert len(pathway.steps) >= 1

    def test_steps_ordered_by_priority(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        priority_order = {
            ActionPriority.CRITICAL: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.MEDIUM: 2,
            ActionPriority.LOW: 3,
        }
        values = [priority_order[s.priority] for s in pathway.steps]
        assert values == sorted(values)

    def test_pathway_has_legal_theories(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        assert len(pathway.legal_theories) > 0

    def test_pathway_has_statutes(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        assert len(pathway.statutes_cited) > 0

    def test_total_estimated_days(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        assert pathway.total_estimated_days > 0
        total = sum(s.estimated_days for s in pathway.steps)
        assert pathway.total_estimated_days == total

    def test_thin_file_empty_pathway(self, thin_file_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(thin_file_profile)
        assert len(pathway.steps) == 0

    def test_steps_numbered_sequentially(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        for i, step in enumerate(pathway.steps, 1):
            assert step.step_number == i

    def test_collection_step_cites_fdcpa(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        collection_steps = [
            s for s in pathway.steps if "collection" in s.action.lower()
        ]
        assert len(collection_steps) > 0
        for step in collection_steps:
            assert step.legal_basis is not None
            assert "FDCPA" in step.legal_basis or "FCRA" in step.legal_basis

    def test_high_utilization_adds_step(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        util_steps = [
            s
            for s in pathway.steps
            if "utilization" in s.description.lower()
            or "balance" in s.description.lower()
        ]
        assert len(util_steps) >= 1

    def test_each_step_has_legal_basis(self, poor_credit_profile):
        from modules.credit.dispute_pathway import DisputePathwayGenerator

        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(poor_credit_profile)
        for step in pathway.steps:
            assert step.legal_basis is not None
            assert len(step.legal_basis) > 0
