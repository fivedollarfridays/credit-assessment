"""Dispute letter types, bureau info, and template model."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LetterType(StrEnum):
    """Types of dispute letters."""

    VALIDATION = "validation"
    INACCURACY = "inaccuracy"
    COMPLETENESS = "completeness"
    OBSOLETE_ITEM = "obsolete_item"
    IDENTITY_THEFT = "identity_theft"


class Bureau(StrEnum):
    """Credit reporting bureaus."""

    EQUIFAX = "equifax"
    EXPERIAN = "experian"
    TRANSUNION = "transunion"


class BureauAddress(BaseModel):
    """Mailing address for a credit bureau dispute department."""

    name: str
    street: str
    city: str
    state: str
    zip_code: str


class LetterTemplate(BaseModel):
    """A dispute letter template with placeholders and legal citations."""

    letter_type: LetterType
    variation: int = Field(ge=1, le=3)
    subject_template: str
    body_template: str
    legal_citations: list[str]
    required_fields: list[str]


# ---------------------------------------------------------------------------
# Bureau mailing addresses (dispute departments)
# ---------------------------------------------------------------------------

BUREAU_ADDRESSES: dict[Bureau, BureauAddress] = {
    Bureau.EQUIFAX: BureauAddress(
        name="Equifax Information Services LLC",
        street="P.O. Box 740256",
        city="Atlanta",
        state="GA",
        zip_code="30374-0256",
    ),
    Bureau.EXPERIAN: BureauAddress(
        name="Experian",
        street="P.O. Box 4500",
        city="Allen",
        state="TX",
        zip_code="75013",
    ),
    Bureau.TRANSUNION: BureauAddress(
        name="TransUnion LLC Consumer Dispute Center",
        street="P.O. Box 2000",
        city="Chester",
        state="PA",
        zip_code="19016",
    ),
}
