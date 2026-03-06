"""Dispute letter template registry — 5 types x 2-3 variations."""

from __future__ import annotations
import random

from .letter_types import BUREAU_ADDRESSES, LetterTemplate, LetterType  # noqa: F401

_VALIDATION_TEMPLATES = [
    LetterTemplate(
        letter_type=LetterType.VALIDATION,
        variation=1,
        subject_template="Debt Validation Request — {account_number}",
        body_template=(
            "I am writing pursuant to my rights under the Fair Debt Collection "
            "Practices Act, 15 U.S.C. § 1692g, to request validation of the "
            "alleged debt referenced above.\n\n"
            "Creditor: {creditor}\nAccount Number: {account_number}\n"
            "Alleged Amount: ${amount}\n\n"
            "Please provide: (1) an itemized statement of all fees and charges, "
            "(2) a copy of the original signed agreement, (3) proof of licensure "
            "to collect in my state, and (4) chain of assignment documentation.\n\n"
            "Until validated, cease all collection activity and do not report "
            "this account to any consumer reporting agency.\n\n"
            "Sincerely,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1692g (FDCPA — Validation of debts)",
            "15 U.S.C. § 1692e (FDCPA — False or misleading representations)",
        ],
        required_fields=["consumer_name", "creditor", "account_number", "amount"],
    ),
    LetterTemplate(
        letter_type=LetterType.VALIDATION,
        variation=2,
        subject_template="Request for Debt Verification — {account_number}",
        body_template=(
            "I received communication regarding an alleged debt and am "
            "exercising my right under 15 U.S.C. § 1692g to request "
            "verification.\n\n"
            "Creditor: {creditor}\nAccount: {account_number}\n"
            "Amount Claimed: ${amount}\n\n"
            "I dispute this debt and request: (1) complete payment history, "
            "(2) documentation proving I agreed to this amount, and "
            "(3) proof of authority to collect on this account.\n\n"
            "Per the FDCPA, cease collection until validated. Failure to "
            "comply constitutes a violation of federal law.\n\n"
            "Respectfully,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1692g (FDCPA — Validation of debts)",
        ],
        required_fields=["consumer_name", "creditor", "account_number", "amount"],
    ),
    LetterTemplate(
        letter_type=LetterType.VALIDATION,
        variation=3,
        subject_template="Validation Notice — {account_number}",
        body_template=(
            "Pursuant to 15 U.S.C. § 1692g, I demand validation of "
            "the debt referenced below.\n\n"
            "Creditor: {creditor}\nAccount: {account_number}\n"
            "Amount: ${amount}\n\n"
            "Provide the original signed contract, full payment ledger, "
            "and proof of your licensure. No further contact or credit "
            "reporting until validated.\n\n{consumer_name}"
        ),
        legal_citations=["15 U.S.C. § 1692g (FDCPA — Validation of debts)"],
        required_fields=["consumer_name", "creditor", "account_number", "amount"],
    ),
]

_INACCURACY_TEMPLATES = [
    LetterTemplate(
        letter_type=LetterType.INACCURACY,
        variation=1,
        subject_template="Dispute of Inaccurate Information — {account_number}",
        body_template=(
            "I am writing to dispute inaccurate information on my credit "
            "report pursuant to Section 611 of the Fair Credit Reporting "
            "Act, 15 U.S.C. § 1681i.\n\n"
            "Bureau: {bureau_name}\n"
            "Creditor: {creditor}\n"
            "Account Number: {account_number}\n\n"
            "The following information is inaccurate: {description}\n\n"
            "Under FCRA Section 611(a), you are required to conduct a "
            "reasonable reinvestigation within 30 days and correct or "
            "delete any information that cannot be verified. Please "
            "investigate this matter and provide written notification "
            "of the results.\n\n"
            "Sincerely,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681i(a) (FCRA § 611 — Reinvestigation)",
            "15 U.S.C. § 1681e(b) (FCRA § 607 — Accuracy)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "description",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.INACCURACY,
        variation=2,
        subject_template="Formal Dispute — Inaccurate Reporting on {account_number}",
        body_template=(
            "This letter serves as a formal dispute of information appearing "
            "on my {bureau_name} credit report that I believe to be inaccurate.\n\n"
            "Creditor: {creditor}\n"
            "Account: {account_number}\n"
            "Issue: {description}\n\n"
            "I am exercising my rights under 15 U.S.C. § 1681i to request "
            "a reinvestigation. The reported information does not accurately "
            "reflect the status of this account.\n\n"
            "Please correct this information and send me an updated copy "
            "of my credit report reflecting the changes.\n\n"
            "Thank you,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681i (FCRA § 611 — Reinvestigation)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "description",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.INACCURACY,
        variation=3,
        subject_template="Credit Report Error Dispute — {account_number}",
        body_template=(
            "I have reviewed my credit report from {bureau_name} and "
            "identified the following error that requires correction "
            "under the Fair Credit Reporting Act.\n\n"
            "Account: {account_number}\n"
            "Creditor: {creditor}\n"
            "Error: {description}\n\n"
            "Section 611 of the FCRA requires you to investigate disputed "
            "items within 30 days. If the information cannot be verified, "
            "it must be promptly deleted per 15 U.S.C. § 1681i(a)(5)(A).\n\n"
            "I look forward to your prompt resolution.\n\n"
            "Regards,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681i(a) (FCRA § 611 — Reinvestigation)",
            "15 U.S.C. § 1681i(a)(5)(A) (Deletion of unverifiable info)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "description",
        ],
    ),
]

_COMPLETENESS_TEMPLATES = [
    LetterTemplate(
        letter_type=LetterType.COMPLETENESS,
        variation=1,
        subject_template="Dispute — Incomplete Information on {account_number}",
        body_template=(
            "I am writing to dispute incomplete reporting on my credit "
            "report under Section 623 of the Fair Credit Reporting Act.\n\n"
            "Bureau: {bureau_name}\n"
            "Creditor: {creditor}\n"
            "Account Number: {account_number}\n\n"
            "The reported information is incomplete: {description}\n\n"
            "Under 15 U.S.C. § 1681s-2(b), furnishers are required to "
            "report complete and accurate information. Incomplete reporting "
            "that creates a misleading impression violates FCRA Section "
            "607(b). Please investigate and update this account to reflect "
            "complete information.\n\n"
            "Sincerely,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681s-2(b) (FCRA § 623 — Furnisher duties)",
            "15 U.S.C. § 1681e(b) (FCRA § 607 — Accuracy)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "description",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.COMPLETENESS,
        variation=2,
        subject_template="Incomplete Credit Reporting Dispute — {account_number}",
        body_template=(
            "I am formally disputing the incomplete reporting of the "
            "following account on my {bureau_name} credit report.\n\n"
            "Creditor: {creditor}\n"
            "Account: {account_number}\n"
            "Deficiency: {description}\n\n"
            "Furnishers have an obligation under 15 U.S.C. § 1681s-2 to "
            "provide complete information. The current reporting omits "
            "material details, which misrepresents my credit history.\n\n"
            "I request a full investigation and correction within 30 days "
            "as required by the FCRA.\n\n"
            "Thank you,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681s-2 (FCRA § 623 — Furnisher duties)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "description",
        ],
    ),
]

_OBSOLETE_TEMPLATES = [
    LetterTemplate(
        letter_type=LetterType.OBSOLETE_ITEM,
        variation=1,
        subject_template="Demand for Removal of Obsolete Item — {account_number}",
        body_template=(
            "I am writing to request the removal of an obsolete item "
            "from my credit report under Section 605 of the FCRA.\n\n"
            "Bureau: {bureau_name}\n"
            "Creditor: {creditor}\n"
            "Account Number: {account_number}\n"
            "Date of First Delinquency: {date}\n\n"
            "Under 15 U.S.C. § 1681c(a), consumer reporting agencies "
            "may not report adverse information that is more than seven "
            "years old from the date of first delinquency. This item "
            "has exceeded the allowable reporting period and must be "
            "removed immediately.\n\n"
            "Sincerely,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681c(a) (FCRA § 605 — Obsolete information)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "date",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.OBSOLETE_ITEM,
        variation=2,
        subject_template="Time-Barred Item Removal Request — {account_number}",
        body_template=(
            "This letter serves as a formal demand to remove the following "
            "time-barred item from my {bureau_name} credit report.\n\n"
            "Account: {account_number}\n"
            "Creditor: {creditor}\n"
            "Original Delinquency Date: {date}\n\n"
            "Section 605 of the Fair Credit Reporting Act (15 U.S.C. "
            "§ 1681c) prohibits the reporting of adverse items beyond "
            "seven years. The item identified above has surpassed this "
            "statutory limit. Continued reporting constitutes a violation "
            "of the FCRA.\n\n"
            "Please remove this item and confirm in writing.\n\n"
            "Regards,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681c (FCRA § 605 — Obsolete information)",
            "15 U.S.C. § 1681c(a)(4) (7-year reporting limit)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "date",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.OBSOLETE_ITEM,
        variation=3,
        subject_template="Obsolete Item Removal — {account_number}",
        body_template=(
            "The item below exceeds the 7-year reporting period under "
            "15 U.S.C. § 1681c and must be removed from my {bureau_name} "
            "report.\n\n"
            "Creditor: {creditor}\nAccount: {account_number}\n"
            "Date of First Delinquency: {date}\n\n"
            "Remove this item immediately and confirm in writing.\n\n"
            "{consumer_name}"
        ),
        legal_citations=["15 U.S.C. § 1681c(a) (FCRA § 605 — Obsolete information)"],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "date",
        ],
    ),
]

_IDENTITY_THEFT_TEMPLATES = [
    LetterTemplate(
        letter_type=LetterType.IDENTITY_THEFT,
        variation=1,
        subject_template="Identity Theft Dispute — Block Request for {account_number}",
        body_template=(
            "I am a victim of identity theft and am writing pursuant to "
            "Section 605B of the Fair Credit Reporting Act to request "
            "that you block the following fraudulent information.\n\n"
            "Bureau: {bureau_name}\n"
            "Fraudulent Account: {account_number}\n"
            "Creditor: {creditor}\n"
            "Amount: ${amount}\n\n"
            "Enclosed please find:\n"
            "- A copy of my FTC Identity Theft Report\n"
            "- Proof of my identity\n\n"
            "Under 15 U.S.C. § 1681c-2, you are required to block "
            "this information within 4 business days of receiving "
            "this notice and supporting documentation.\n\n"
            "Sincerely,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681c-2 (FCRA § 605B — Identity theft block)",
            "15 U.S.C. § 1681i (FCRA § 611 — Reinvestigation)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "amount",
        ],
    ),
    LetterTemplate(
        letter_type=LetterType.IDENTITY_THEFT,
        variation=2,
        subject_template="Fraudulent Account Block Request — {account_number}",
        body_template=(
            "I am writing to report that the account listed below was "
            "opened fraudulently as a result of identity theft.\n\n"
            "Bureau: {bureau_name}\n"
            "Account: {account_number}\n"
            "Creditor: {creditor}\n"
            "Fraudulent Amount: ${amount}\n\n"
            "I am exercising my rights under 15 U.S.C. § 1681c-2 "
            "(FCRA Section 605B) to have this information blocked from "
            "my credit file. An FTC Identity Theft Report and proof of "
            "identity are enclosed.\n\n"
            "Please block this item within the 4-business-day statutory "
            "deadline and notify me in writing.\n\n"
            "Thank you,\n{consumer_name}"
        ),
        legal_citations=[
            "15 U.S.C. § 1681c-2 (FCRA § 605B — Identity theft block)",
        ],
        required_fields=[
            "consumer_name",
            "bureau_name",
            "creditor",
            "account_number",
            "amount",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TEMPLATES: dict[LetterType, list[LetterTemplate]] = {
    LetterType.VALIDATION: _VALIDATION_TEMPLATES,
    LetterType.INACCURACY: _INACCURACY_TEMPLATES,
    LetterType.COMPLETENESS: _COMPLETENESS_TEMPLATES,
    LetterType.OBSOLETE_ITEM: _OBSOLETE_TEMPLATES,
    LetterType.IDENTITY_THEFT: _IDENTITY_THEFT_TEMPLATES,
}


def get_template(
    letter_type: LetterType, variation: int | None = None
) -> LetterTemplate:
    """Return a template by type and optional variation number.

    If variation is None, a random variation is selected.
    """
    templates = TEMPLATES[letter_type]
    if variation is None:
        return random.choice(templates)
    for tpl in templates:
        if tpl.variation == variation:
            return tpl
    valid = [t.variation for t in templates]
    raise ValueError(f"Invalid variation {variation} for {letter_type}; valid: {valid}")
