"""FCRA Section 505 disclosures and adverse action notice templates."""

from __future__ import annotations

FCRA_DISCLAIMER: str = (
    "This credit assessment is provided for educational and informational "
    "purposes only. This service is not a consumer reporting agency as defined "
    "by the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq., and "
    "the information provided does not constitute a consumer report. The scores, "
    "estimates, and recommendations presented are not intended to be used as a "
    "basis for any credit, employment, insurance, or other eligibility decision. "
    "Under FCRA Section 605, consumers have the right to dispute inaccurate "
    "information directly with credit reporting agencies. If you believe any "
    "information on your credit report is inaccurate, you should contact the "
    "relevant credit bureau directly. All timeline estimates and score "
    "projections are approximate and for educational purposes only."
)

ADVERSE_ACTION_NOTICE_TEMPLATE: str = (
    "NOTICE OF ADVERSE ACTION\n"
    "\n"
    "Date: {date}\n"
    "Consumer: {consumer_name}\n"
    "\n"
    "Action Taken: {action_taken}\n"
    "\n"
    "Principal Reason(s) for Adverse Action:\n"
    "{reasons}\n"
    "\n"
    "Under the Fair Credit Reporting Act (FCRA), you have the right to:\n"
    "\n"
    "1. Obtain a free copy of your credit report from the consumer reporting "
    "agency that provided the information within 60 days of this notice.\n"
    "\n"
    "2. Dispute the accuracy or completeness of any information in your "
    "credit report directly with the consumer reporting agency.\n"
    "\n"
    "3. Submit a statement of dispute to the consumer reporting agency, "
    "which must be included in future reports.\n"
    "\n"
    "Federal Trade Commission\n"
    "Washington, DC 20580\n"
    "www.ftc.gov\n"
    "\n"
    "Consumer Financial Protection Bureau\n"
    "P.O. Box 4503\n"
    "Iowa City, Iowa 52244\n"
    "www.consumerfinance.gov"
)

_CONSUMER_RIGHTS: str = (
    "Under the Fair Credit Reporting Act (FCRA), you have the following rights: "
    "(1) You have the right to receive a copy of your credit report. "
    "(2) You have the right to dispute incomplete or inaccurate information. "
    "(3) Consumer reporting agencies must correct or delete inaccurate, "
    "incomplete, or unverifiable information, typically within 30 days. "
    "(4) You may seek damages from violators in court. "
    "(5) Identity theft victims have additional rights under FCRA Section 605B. "
    "For more information, visit www.consumerfinance.gov or contact the "
    "Consumer Financial Protection Bureau."
)

_DATA_USAGE_NOTICE: str = (
    "The credit profile data you submit is used solely to generate your "
    "assessment results. We do not share your data with third-party credit "
    "reporting agencies, creditors, or data brokers. Assessment results are "
    "stored for your records and are not used for any lending or underwriting "
    "decision."
)


PROJECTION_DISCLAIMER: str = (
    "Score projections are estimates based on general FICO scoring factors. "
    "Actual results may vary. This is not financial advice."
)


def get_disclosures() -> dict[str, str]:
    """Return all required disclosure texts as a structured dictionary."""
    return {
        "fcra_disclaimer": FCRA_DISCLAIMER,
        "adverse_action_notice_template": ADVERSE_ACTION_NOTICE_TEMPLATE,
        "consumer_rights": _CONSUMER_RIGHTS,
        "data_usage_notice": _DATA_USAGE_NOTICE,
        "projection_disclaimer": PROJECTION_DISCLAIMER,
    }
