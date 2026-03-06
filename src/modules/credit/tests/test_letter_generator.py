"""Tests for letter generation engine — T22.2 TDD."""

from __future__ import annotations

import pytest

from modules.credit.letter_generator import (
    GeneratedLetter,
    LetterGenerator,
    LetterRequest,
)
from modules.credit.letter_types import Bureau, LetterType
from modules.credit.types import NegativeItem, NegativeItemType


@pytest.fixture
def generator():
    return LetterGenerator()


@pytest.fixture
def collection_item():
    return NegativeItem(
        type=NegativeItemType.COLLECTION,
        description="Medical debt sent to collections",
        creditor="ABC Collections",
        amount=1500.0,
        date_reported="2024-01-15",
    )


@pytest.fixture
def validation_request(collection_item):
    return LetterRequest(
        negative_item=collection_item,
        letter_type=LetterType.VALIDATION,
        bureau=Bureau.EQUIFAX,
        consumer_name="Jane Doe",
    )


# ---------------------------------------------------------------------------
# Cycle 1: generate() basic output
# ---------------------------------------------------------------------------


class TestGenerateBasic:
    def test_returns_generated_letter(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert isinstance(result, GeneratedLetter)

    def test_subject_filled(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.subject
        assert "{" not in result.subject

    def test_body_filled(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.body
        assert "{" not in result.body

    def test_consumer_name_in_body(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert "Jane Doe" in result.body

    def test_creditor_in_body(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert "ABC Collections" in result.body

    def test_bureau_set(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.bureau == Bureau.EQUIFAX

    def test_bureau_address_formatted(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert "Equifax" in result.bureau_address
        assert "Atlanta" in result.bureau_address

    def test_legal_citations_present(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert len(result.legal_citations) > 0

    def test_letter_type_set(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.letter_type == LetterType.VALIDATION

    def test_generated_at_iso(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert "T" in result.generated_at  # ISO format

    def test_disclaimer_present(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.disclaimer
        assert (
            "not legal advice" in result.disclaimer.lower()
            or "educational" in result.disclaimer.lower()
        )


# ---------------------------------------------------------------------------
# Cycle 2: All letter types
# ---------------------------------------------------------------------------


class TestAllLetterTypes:
    @pytest.mark.parametrize("letter_type", list(LetterType))
    def test_generates_for_each_type(self, generator, collection_item, letter_type):
        req = LetterRequest(
            negative_item=collection_item,
            letter_type=letter_type,
            bureau=Bureau.EXPERIAN,
            consumer_name="Test User",
        )
        result = generator.generate(req)
        assert result.letter_type == letter_type
        assert result.body
        assert "{" not in result.body


class TestSpecificVariation:
    def test_explicit_variation(self, generator, collection_item):
        req = LetterRequest(
            negative_item=collection_item,
            letter_type=LetterType.INACCURACY,
            bureau=Bureau.TRANSUNION,
            consumer_name="Test User",
            variation=2,
        )
        result = generator.generate(req)
        assert result.body


# ---------------------------------------------------------------------------
# Cycle 3: Batch generation
# ---------------------------------------------------------------------------


class TestBatchGeneration:
    def test_batch_returns_list(self, generator, collection_item):
        requests = [
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="User",
            ),
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.INACCURACY,
                bureau=Bureau.EXPERIAN,
                consumer_name="User",
            ),
        ]
        results = generator.generate_batch(requests)
        assert len(results) == 2

    def test_batch_auto_varies(self, generator, collection_item):
        requests = [
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="User",
            ),
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EXPERIAN,
                consumer_name="User",
            ),
        ]
        results = generator.generate_batch(requests)
        # Auto-variation should assign different variations for same letter type
        assert results[0].subject != results[1].subject


# ---------------------------------------------------------------------------
# Cycle 4: Optional fields
# ---------------------------------------------------------------------------


class TestOptionalFields:
    def test_no_account_number(self, generator, collection_item):
        req = LetterRequest(
            negative_item=collection_item,
            letter_type=LetterType.VALIDATION,
            bureau=Bureau.EQUIFAX,
            consumer_name="User",
        )
        result = generator.generate(req)
        assert "{account_number}" not in result.body

    def test_account_number_filled(self, generator, collection_item):
        req = LetterRequest(
            negative_item=collection_item,
            letter_type=LetterType.VALIDATION,
            bureau=Bureau.EQUIFAX,
            consumer_name="User",
            account_number="ACCT-12345",
        )
        result = generator.generate(req)
        assert "ACCT-12345" in result.body

    def test_no_creditor_uses_na(self, generator):
        item = NegativeItem(
            type=NegativeItemType.LATE_PAYMENT,
            description="Late payment on unknown account",
        )
        req = LetterRequest(
            negative_item=item,
            letter_type=LetterType.INACCURACY,
            bureau=Bureau.EQUIFAX,
            consumer_name="User",
        )
        result = generator.generate(req)
        assert "{creditor}" not in result.body

    def test_negative_item_description_in_output(self, generator, validation_request):
        result = generator.generate(validation_request)
        assert result.negative_item_description == "Medical debt sent to collections"


# ---------------------------------------------------------------------------
# Cycle 5: Input validation on LetterRequest
# ---------------------------------------------------------------------------


class TestLetterRequestValidation:
    def test_consumer_name_required(self, collection_item):
        with pytest.raises(ValueError):
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="",
            )

    def test_consumer_name_max_length(self, collection_item):
        with pytest.raises(ValueError):
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="x" * 201,
            )

    def test_account_number_max_length(self, collection_item):
        with pytest.raises(ValueError):
            LetterRequest(
                negative_item=collection_item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="User",
                account_number="x" * 51,
            )


class TestSafeMapping:
    def test_attribute_access_blocked(self):
        from modules.credit.letter_generator import _SafeMapping

        m = _SafeMapping({"key": "value"})
        assert m["key"] == "value"
        with pytest.raises(AttributeError, match="Attribute access not allowed"):
            _ = m.key
