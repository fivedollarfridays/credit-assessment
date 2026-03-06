"""Letter generation engine — produces dispute letters from templates."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .disclosures import FCRA_DISCLAIMER
from .letter_templates import TEMPLATES, get_template
from .letter_types import BUREAU_ADDRESSES, Bureau, LetterType
from .types import NegativeItem


class LetterRequest(BaseModel):
    """Input for generating a dispute letter."""

    negative_item: NegativeItem
    letter_type: LetterType
    bureau: Bureau
    consumer_name: str = Field(min_length=1, max_length=200)
    consumer_address: str | None = Field(default=None, max_length=500)
    account_number: str | None = Field(default=None, max_length=50)
    variation: int | None = None


class GeneratedLetter(BaseModel):
    """A fully rendered dispute letter."""

    subject: str
    body: str
    bureau: Bureau
    bureau_address: str
    legal_citations: list[str]
    letter_type: LetterType
    negative_item_description: str
    generated_at: str
    disclaimer: str


def _format_bureau_address(bureau: Bureau) -> str:
    """Format bureau address as a multi-line mailing string."""
    addr = BUREAU_ADDRESSES[bureau]
    return f"{addr.name}\n{addr.street}\n{addr.city}, {addr.state} {addr.zip_code}"


def _build_placeholder_values(
    req: LetterRequest, bureau_address: str
) -> dict[str, str]:
    """Build the placeholder dict from request + negative item fields."""
    item = req.negative_item
    addr = BUREAU_ADDRESSES[req.bureau]
    return {
        "consumer_name": req.consumer_name,
        "consumer_address": req.consumer_address or "",
        "creditor": item.creditor or "N/A",
        "account_number": req.account_number or "N/A",
        "amount": f"{item.amount:.2f}" if item.amount is not None else "0.00",
        "date": item.date_reported or item.date_of_first_delinquency or "N/A",
        "description": item.description,
        "bureau_name": addr.name,
        "bureau_address": bureau_address,
    }


class _SafeMapping(dict):
    """Restrict format_map to key lookup only — no attribute traversal."""

    def __getattr__(self, key: str) -> str:
        raise AttributeError(f"Attribute access not allowed: {key}")


class LetterGenerator:
    """Generates dispute letters from templates and request data."""

    def generate(self, request: LetterRequest) -> GeneratedLetter:
        """Generate a single dispute letter."""
        template = get_template(request.letter_type, request.variation)
        bureau_address = _format_bureau_address(request.bureau)
        values = _SafeMapping(_build_placeholder_values(request, bureau_address))

        subject = template.subject_template.format_map(values)
        body = template.body_template.format_map(values)

        return GeneratedLetter(
            subject=subject,
            body=body,
            bureau=request.bureau,
            bureau_address=bureau_address,
            legal_citations=template.legal_citations,
            letter_type=request.letter_type,
            negative_item_description=request.negative_item.description,
            generated_at=datetime.now(timezone.utc).isoformat(),
            disclaimer=FCRA_DISCLAIMER,
        )

    def generate_batch(self, requests: list[LetterRequest]) -> list[GeneratedLetter]:
        """Generate multiple letters, auto-varying templates per type."""
        type_counters: dict[LetterType, int] = {}
        results: list[GeneratedLetter] = []

        for req in requests:
            if req.variation is None:
                lt = req.letter_type
                count = type_counters.get(lt, 0)
                variations = TEMPLATES[lt]
                auto_var = variations[count % len(variations)].variation
                type_counters[lt] = count + 1
                req = req.model_copy(update={"variation": auto_var})
            results.append(self.generate(req))

        return results
