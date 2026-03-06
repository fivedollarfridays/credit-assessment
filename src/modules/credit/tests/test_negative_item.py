"""Tests for structured NegativeItem type — T21.1 TDD."""

from __future__ import annotations

import pytest

from modules.credit.assessment import CreditAssessmentService
from modules.credit.dispute_pathway import DisputePathwayGenerator
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    NegativeItem,
    NegativeItemType,
    ScoreBand,
)


# ---------------------------------------------------------------------------
# Cycle 1: NegativeItemType enum
# ---------------------------------------------------------------------------


class TestNegativeItemType:
    """Test NegativeItemType enum values."""

    def test_has_collection(self):
        assert NegativeItemType.COLLECTION.value == "collection"

    def test_has_late_payment(self):
        assert NegativeItemType.LATE_PAYMENT.value == "late_payment"

    def test_has_charge_off(self):
        assert NegativeItemType.CHARGE_OFF.value == "charge_off"

    def test_has_identity_theft(self):
        assert NegativeItemType.IDENTITY_THEFT.value == "identity_theft"

    def test_has_wrong_balance(self):
        assert NegativeItemType.WRONG_BALANCE.value == "wrong_balance"

    def test_has_obsolete_item(self):
        assert NegativeItemType.OBSOLETE_ITEM.value == "obsolete_item"

    def test_has_unauthorized_inquiry(self):
        assert NegativeItemType.UNAUTHORIZED_INQUIRY.value == "unauthorized_inquiry"

    def test_has_dofd_error(self):
        assert NegativeItemType.DOFD_ERROR.value == "dofd_error"

    def test_has_exactly_eight_types(self):
        assert len(NegativeItemType) == 8


# ---------------------------------------------------------------------------
# Cycle 2: NegativeItem model
# ---------------------------------------------------------------------------


class TestNegativeItem:
    """Test NegativeItem Pydantic model."""

    def test_create_minimal(self):
        item = NegativeItem(
            type=NegativeItemType.COLLECTION, description="Medical collection"
        )
        assert item.type == NegativeItemType.COLLECTION
        assert item.description == "Medical collection"

    def test_optional_fields_default_none(self):
        item = NegativeItem(
            type=NegativeItemType.LATE_PAYMENT, description="Late payment"
        )
        assert item.creditor is None
        assert item.amount is None
        assert item.date_reported is None
        assert item.date_of_first_delinquency is None
        assert item.status is None

    def test_full_structured_item(self):
        item = NegativeItem(
            type=NegativeItemType.COLLECTION,
            description="Medical collection from ABC Hospital",
            creditor="ABC Hospital",
            amount=2500.0,
            date_reported="2025-01-15",
            date_of_first_delinquency="2024-06-01",
            status="open",
        )
        assert item.creditor == "ABC Hospital"
        assert item.amount == 2500.0
        assert item.date_reported == "2025-01-15"
        assert item.status == "open"

    def test_amount_must_be_non_negative(self):
        with pytest.raises(ValueError):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Bad amount",
                amount=-100.0,
            )

    def test_description_max_length(self):
        with pytest.raises(ValueError):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="x" * 201,
            )

    def test_rejects_semantically_invalid_date(self):
        with pytest.raises(ValueError, match="Invalid date"):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Bad date",
                date_reported="2024-13-45",
            )

    def test_rejects_invalid_dofd(self):
        with pytest.raises(ValueError, match="Invalid date"):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Bad dofd",
                date_of_first_delinquency="2024-00-01",
            )

    def test_valid_status_enum(self):
        from modules.credit.types import NegativeItemStatus

        item = NegativeItem(
            type=NegativeItemType.COLLECTION,
            description="Test",
            status="disputed",
        )
        assert item.status == NegativeItemStatus.DISPUTED

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Test",
                status="bogus_status",
            )

    def test_creditor_max_length(self):
        with pytest.raises(ValueError):
            NegativeItem(
                type=NegativeItemType.COLLECTION,
                description="Test",
                creditor="x" * 101,
            )


# ---------------------------------------------------------------------------
# Cycle 3: String coercion in CreditProfile
# ---------------------------------------------------------------------------


class TestNegativeItemCoercion:
    """Test string-to-NegativeItem auto-coercion in CreditProfile."""

    def _make_profile(self, negative_items):
        return CreditProfile(
            current_score=650,
            score_band=ScoreBand.FAIR,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=90.0,
            average_account_age_months=36,
            negative_items=negative_items,
        )

    def test_string_coerced_to_negative_item(self):
        profile = self._make_profile(["collection_medical"])
        assert len(profile.negative_items) == 1
        assert isinstance(profile.negative_items[0], NegativeItem)

    def test_collection_string_infers_type(self):
        profile = self._make_profile(["collection_medical_2500"])
        assert profile.negative_items[0].type == NegativeItemType.COLLECTION

    def test_late_payment_string_infers_type(self):
        profile = self._make_profile(["late_payment_30day"])
        assert profile.negative_items[0].type == NegativeItemType.LATE_PAYMENT

    def test_charge_off_string_infers_type(self):
        profile = self._make_profile(["charge_off_credit_card"])
        assert profile.negative_items[0].type == NegativeItemType.CHARGE_OFF

    def test_identity_theft_string_infers_type(self):
        profile = self._make_profile(["identity_theft_account"])
        assert profile.negative_items[0].type == NegativeItemType.IDENTITY_THEFT

    def test_unknown_string_defaults_to_late_payment(self):
        profile = self._make_profile(["unknown_thing"])
        assert profile.negative_items[0].type == NegativeItemType.LATE_PAYMENT

    def test_structured_item_accepted(self):
        item = {
            "type": "collection",
            "description": "Medical collection",
            "amount": 2500.0,
        }
        profile = self._make_profile([item])
        assert isinstance(profile.negative_items[0], NegativeItem)
        assert profile.negative_items[0].type == NegativeItemType.COLLECTION
        assert profile.negative_items[0].amount == 2500.0

    def test_mixed_strings_and_objects(self):
        items = [
            "collection_medical",
            {"type": "late_payment", "description": "Auto loan late"},
        ]
        profile = self._make_profile(items)
        assert len(profile.negative_items) == 2
        assert all(isinstance(i, NegativeItem) for i in profile.negative_items)
        assert profile.negative_items[0].type == NegativeItemType.COLLECTION
        assert profile.negative_items[1].type == NegativeItemType.LATE_PAYMENT

    def test_string_description_preserved(self):
        """Coerced string becomes the description."""
        profile = self._make_profile(["collection_medical_2500"])
        assert profile.negative_items[0].description == "collection_medical_2500"

    def test_empty_list_still_works(self):
        profile = self._make_profile([])
        assert profile.negative_items == []

    def test_max_50_items_enforced(self):
        with pytest.raises(ValueError):
            self._make_profile(["item"] * 51)


# ---------------------------------------------------------------------------
# Cycle 4: Dispute pathway with structured items
# ---------------------------------------------------------------------------


class TestDisputePathwayStructuredItems:
    """Test dispute pathway uses NegativeItem.type directly."""

    def test_structured_collection_generates_fdcpa_step(self):
        profile = CreditProfile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=30.0,
            account_summary=AccountSummary(
                total_accounts=5, open_accounts=3, collection_accounts=1
            ),
            payment_history_pct=70.0,
            average_account_age_months=36,
            negative_items=[
                NegativeItem(
                    type=NegativeItemType.COLLECTION,
                    description="Medical collection",
                    amount=2500.0,
                    creditor="ABC Hospital",
                )
            ],
        )
        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(profile)
        assert len(pathway.steps) >= 1
        collection_steps = [
            s for s in pathway.steps if "collection" in s.action.lower()
        ]
        assert len(collection_steps) >= 1
        assert "FDCPA" in collection_steps[0].legal_basis

    def test_structured_item_description_in_action(self):
        profile = CreditProfile(
            current_score=650,
            score_band=ScoreBand.FAIR,
            overall_utilization=30.0,
            account_summary=AccountSummary(total_accounts=5, open_accounts=3),
            payment_history_pct=90.0,
            average_account_age_months=36,
            negative_items=[
                NegativeItem(
                    type=NegativeItemType.LATE_PAYMENT,
                    description="Auto loan 30-day late",
                )
            ],
        )
        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(profile)
        assert len(pathway.steps) >= 1
        assert "Auto loan 30-day late" in pathway.steps[0].action

    def test_mixed_string_and_structured_pathway(self):
        """Pathway works with mix of coerced strings and structured items."""
        profile = CreditProfile(
            current_score=520,
            score_band=ScoreBand.VERY_POOR,
            overall_utilization=30.0,
            account_summary=AccountSummary(
                total_accounts=5, open_accounts=3, collection_accounts=1
            ),
            payment_history_pct=70.0,
            average_account_age_months=36,
            negative_items=[
                "collection_medical_2500",
                NegativeItem(
                    type=NegativeItemType.LATE_PAYMENT,
                    description="Auto loan 60-day late",
                ),
            ],
        )
        gen = DisputePathwayGenerator()
        pathway = gen.generate_pathway(profile)
        assert len(pathway.steps) >= 2


# ---------------------------------------------------------------------------
# Cycle 5: Existing fixtures backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Ensure all existing conftest fixtures still work."""

    def test_good_profile_fixture(self, good_credit_profile):
        assert len(good_credit_profile.negative_items) == 0

    def test_poor_profile_fixture(self, poor_credit_profile):
        assert len(poor_credit_profile.negative_items) == 3
        assert all(
            isinstance(i, NegativeItem) for i in poor_credit_profile.negative_items
        )

    def test_fair_profile_fixture(self, fair_credit_profile):
        assert len(fair_credit_profile.negative_items) == 1
        assert isinstance(fair_credit_profile.negative_items[0], NegativeItem)

    def test_thin_file_fixture(self, thin_file_profile):
        assert len(thin_file_profile.negative_items) == 0

    def test_assessment_still_works_with_coerced_items(self, poor_credit_profile):
        service = CreditAssessmentService()
        result = service.assess(poor_credit_profile)
        assert result.barrier_severity.value == "high"
        assert result.readiness.score >= 0
        assert len(result.dispute_pathway.steps) >= 3
