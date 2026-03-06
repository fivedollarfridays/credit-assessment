"""Tests for dispute letter template system — T22.1 TDD."""

from __future__ import annotations

import pytest

from modules.credit.letter_types import (
    Bureau,
    BureauAddress,
    LetterTemplate,
    LetterType,
)


# ---------------------------------------------------------------------------
# Cycle 1: Enums and types
# ---------------------------------------------------------------------------


class TestLetterType:
    def test_has_five_types(self):
        assert len(LetterType) == 5

    def test_validation_type(self):
        assert LetterType.VALIDATION == "validation"

    def test_inaccuracy_type(self):
        assert LetterType.INACCURACY == "inaccuracy"

    def test_completeness_type(self):
        assert LetterType.COMPLETENESS == "completeness"

    def test_obsolete_item_type(self):
        assert LetterType.OBSOLETE_ITEM == "obsolete_item"

    def test_identity_theft_type(self):
        assert LetterType.IDENTITY_THEFT == "identity_theft"


class TestBureau:
    def test_has_three_bureaus(self):
        assert len(Bureau) == 3

    def test_equifax(self):
        assert Bureau.EQUIFAX == "equifax"

    def test_experian(self):
        assert Bureau.EXPERIAN == "experian"

    def test_transunion(self):
        assert Bureau.TRANSUNION == "transunion"


class TestBureauAddress:
    def test_fields(self):
        addr = BureauAddress(
            name="Equifax",
            street="P.O. Box 740256",
            city="Atlanta",
            state="GA",
            zip_code="30374",
        )
        assert addr.name == "Equifax"
        assert addr.zip_code == "30374"


class TestLetterTemplate:
    def test_required_fields(self):
        tpl = LetterTemplate(
            letter_type=LetterType.VALIDATION,
            variation=1,
            subject_template="Debt Validation Request",
            body_template="I am writing to request validation of {creditor}.",
            legal_citations=["15 U.S.C. § 1692g"],
            required_fields=["creditor"],
        )
        assert tpl.letter_type == LetterType.VALIDATION
        assert tpl.variation == 1
        assert "creditor" in tpl.required_fields


# ---------------------------------------------------------------------------
# Cycle 2: Template registry
# ---------------------------------------------------------------------------


class TestTemplateRegistry:
    def test_all_letter_types_have_templates(self):
        from modules.credit.letter_templates import TEMPLATES

        for lt in LetterType:
            assert lt in TEMPLATES, f"Missing templates for {lt}"

    def test_each_type_has_2_to_3_variations(self):
        from modules.credit.letter_templates import TEMPLATES

        for lt in LetterType:
            count = len(TEMPLATES[lt])
            assert 2 <= count <= 3, f"{lt} has {count} variations, expected 2-3"

    def test_variations_numbered_sequentially(self):
        from modules.credit.letter_templates import TEMPLATES

        for lt in LetterType:
            variations = [t.variation for t in TEMPLATES[lt]]
            assert variations == list(range(1, len(variations) + 1))

    def test_total_template_count(self):
        from modules.credit.letter_templates import TEMPLATES

        total = sum(len(v) for v in TEMPLATES.values())
        assert 10 <= total <= 15


class TestGetTemplate:
    def test_get_specific_variation(self):
        from modules.credit.letter_templates import get_template

        tpl = get_template(LetterType.VALIDATION, variation=1)
        assert tpl.letter_type == LetterType.VALIDATION
        assert tpl.variation == 1

    def test_get_random_variation(self):
        from modules.credit.letter_templates import get_template

        tpl = get_template(LetterType.INACCURACY)
        assert tpl.letter_type == LetterType.INACCURACY
        assert tpl.variation >= 1

    def test_invalid_variation_raises(self):
        from modules.credit.letter_templates import get_template

        with pytest.raises(ValueError, match="variation"):
            get_template(LetterType.VALIDATION, variation=99)


class TestLegalCitations:
    """Each template type cites the correct statute."""

    def test_validation_cites_fdcpa(self):
        from modules.credit.letter_templates import TEMPLATES

        for tpl in TEMPLATES[LetterType.VALIDATION]:
            citations = " ".join(tpl.legal_citations)
            assert "1692" in citations, "Validation should cite FDCPA (§1692)"

    def test_inaccuracy_cites_fcra_611(self):
        from modules.credit.letter_templates import TEMPLATES

        for tpl in TEMPLATES[LetterType.INACCURACY]:
            citations = " ".join(tpl.legal_citations)
            assert "1681" in citations, "Inaccuracy should cite FCRA"

    def test_completeness_cites_fcra_623(self):
        from modules.credit.letter_templates import TEMPLATES

        for tpl in TEMPLATES[LetterType.COMPLETENESS]:
            citations = " ".join(tpl.legal_citations)
            assert "1681" in citations, "Completeness should cite FCRA"

    def test_obsolete_cites_fcra_605(self):
        from modules.credit.letter_templates import TEMPLATES

        for tpl in TEMPLATES[LetterType.OBSOLETE_ITEM]:
            citations = " ".join(tpl.legal_citations)
            assert "1681c" in citations, "Obsolete should cite FCRA §605 (1681c)"

    def test_identity_theft_cites_fcra_605b(self):
        from modules.credit.letter_templates import TEMPLATES

        for tpl in TEMPLATES[LetterType.IDENTITY_THEFT]:
            citations = " ".join(tpl.legal_citations)
            assert "1681c-2" in citations, "ID theft should cite FCRA §605B"


class TestBureauAddresses:
    def test_all_bureaus_have_addresses(self):
        from modules.credit.letter_templates import BUREAU_ADDRESSES

        for bureau in Bureau:
            assert bureau in BUREAU_ADDRESSES

    def test_addresses_have_required_fields(self):
        from modules.credit.letter_templates import BUREAU_ADDRESSES

        for bureau, addr in BUREAU_ADDRESSES.items():
            assert addr.name, f"{bureau} missing name"
            assert addr.street, f"{bureau} missing street"
            assert addr.city, f"{bureau} missing city"
            assert addr.state, f"{bureau} missing state"
            assert addr.zip_code, f"{bureau} missing zip"


class TestPlaceholderConsistency:
    """All templates use the same placeholder syntax."""

    def test_body_templates_use_brace_placeholders(self):
        import re

        from modules.credit.letter_templates import TEMPLATES

        for lt, templates in TEMPLATES.items():
            for tpl in templates:
                # Should use {placeholder} syntax, not %s or $var
                assert "%s" not in tpl.body_template
                # Allow $ as currency symbol (e.g. ${amount}), reject $var syntax
                assert "$" not in tpl.body_template.replace("${", "")
                # Should have at least one placeholder
                placeholders = re.findall(r"\{(\w+)\}", tpl.body_template)
                assert len(placeholders) > 0, (
                    f"{lt} v{tpl.variation} has no placeholders"
                )

    def test_required_fields_match_placeholders(self):
        import re

        from modules.credit.letter_templates import TEMPLATES

        for lt, templates in TEMPLATES.items():
            for tpl in templates:
                placeholders = set(re.findall(r"\{(\w+)\}", tpl.body_template))
                for field in tpl.required_fields:
                    assert field in placeholders, (
                        f"{lt} v{tpl.variation}: required field '{field}' "
                        f"not found in body placeholders"
                    )
