"""Privacy policy, terms of service, and legal document management."""

from __future__ import annotations

from datetime import datetime, timezone

_PRIVACY_VERSION = "1.0"
_PRIVACY_EFFECTIVE = "2026-03-04"

_PRIVACY_CONTENT = (
    "PRIVACY POLICY\n"
    "\n"
    f"Effective Date: {_PRIVACY_EFFECTIVE}\n"
    "\n"
    "1. INFORMATION WE COLLECT\n"
    "We collect credit profile data that you voluntarily submit through our "
    "API, including credit scores, account summaries, utilization rates, "
    "payment history, and negative item descriptions. We also collect "
    "technical data such as IP addresses, request timestamps, and API key "
    "identifiers for security and operational purposes.\n"
    "\n"
    "2. HOW WE USE YOUR INFORMATION\n"
    "We use your credit profile data solely to generate credit assessment "
    "results, including readiness scores, barrier analysis, dispute pathways, "
    "timeline estimates, and product eligibility evaluations. We do not use "
    "your data for lending decisions, underwriting, or credit reporting.\n"
    "\n"
    "3. DATA RETENTION\n"
    "Assessment records are retained for audit and compliance purposes. "
    "You may request deletion of your data at any time by contacting our "
    "support team. We retain anonymized, aggregated data for service "
    "improvement. Backup data follows our retention policy: 7 daily, "
    "4 weekly, and 12 monthly snapshots.\n"
    "\n"
    "4. DATA SHARING\n"
    "We do not sell, rent, or share your personal credit data with third "
    "parties, credit bureaus, creditors, or data brokers. We may share "
    "anonymized aggregate statistics for research purposes. We may disclose "
    "data when required by law, court order, or regulatory authority.\n"
    "\n"
    "5. DATA SECURITY\n"
    "We protect your data using encryption in transit (TLS), secure "
    "authentication (JWT), role-based access controls, and audit logging. "
    "Access to personal data is restricted to authorized personnel only.\n"
    "\n"
    "6. YOUR RIGHTS\n"
    "You have the right to access, correct, or delete your personal data. "
    "You may withdraw consent at any time. For GDPR and CCPA rights, see "
    "our data handling policy.\n"
    "\n"
    "7. CONTACT\n"
    "For privacy inquiries, contact our Data Protection Officer at "
    "privacy@example.com."
)

_TOS_VERSION = "1.0"
_TOS_EFFECTIVE = "2026-03-04"

_TOS_CONTENT = (
    "TERMS OF SERVICE\n"
    "\n"
    f"Effective Date: {_TOS_EFFECTIVE}\n"
    "\n"
    "1. ACCEPTANCE OF TERMS\n"
    "By accessing or using the Credit Assessment API, you agree to be bound "
    "by these Terms of Service. If you do not agree, you must not use the "
    "service.\n"
    "\n"
    "2. API USAGE\n"
    "You may use the API solely for lawful purposes consistent with these "
    "terms. You must not exceed your rate limit tier, attempt to circumvent "
    "authentication, or use the API to make credit decisions as defined by "
    "the Fair Credit Reporting Act.\n"
    "\n"
    "3. ACCOUNT RESPONSIBILITIES\n"
    "You are responsible for maintaining the confidentiality of your API "
    "keys and credentials. You must notify us immediately of any unauthorized "
    "use of your account.\n"
    "\n"
    "4. SERVICE AVAILABILITY\n"
    "We aim to provide 99.9% uptime but do not guarantee uninterrupted "
    "service. Scheduled maintenance windows will be communicated in advance. "
    "We reserve the right to modify or discontinue the service with "
    "30 days notice.\n"
    "\n"
    "5. LIMITATION OF LIABILITY\n"
    "The service is provided 'as is' without warranties of any kind. We "
    "shall not be liable for any indirect, incidental, or consequential "
    "damages arising from your use of the service. Our total liability "
    "shall not exceed the fees paid by you in the 12 months preceding "
    "the claim.\n"
    "\n"
    "6. INTELLECTUAL PROPERTY\n"
    "All assessment algorithms, scoring models, and API documentation "
    "remain our intellectual property. You retain ownership of your input "
    "data.\n"
    "\n"
    "7. TERMINATION\n"
    "We may suspend or terminate your access for violation of these terms, "
    "non-payment, or abusive behavior. Upon termination, your right to use "
    "the API ceases immediately. You may request export of your data within "
    "30 days of termination.\n"
    "\n"
    "8. GOVERNING LAW\n"
    "These terms are governed by the laws of the United States. Disputes "
    "shall be resolved through binding arbitration."
)

# --- In-memory ToS acceptance store ---

_tos_acceptances: dict[str, dict] = {}


def get_privacy_policy() -> dict[str, str]:
    """Return the current privacy policy document."""
    return {
        "version": _PRIVACY_VERSION,
        "effective_date": _PRIVACY_EFFECTIVE,
        "content": _PRIVACY_CONTENT,
    }


def get_terms_of_service() -> dict[str, str]:
    """Return the current terms of service document."""
    return {
        "version": _TOS_VERSION,
        "effective_date": _TOS_EFFECTIVE,
        "content": _TOS_CONTENT,
    }


def record_tos_acceptance(user_id: str, tos_version: str) -> None:
    """Record that a user accepted a specific ToS version."""
    key = f"{user_id}:{tos_version}"
    _tos_acceptances[key] = {
        "user_id": user_id,
        "tos_version": tos_version,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }


def check_tos_accepted(user_id: str, tos_version: str) -> bool:
    """Check if a user has accepted a specific ToS version."""
    key = f"{user_id}:{tos_version}"
    return key in _tos_acceptances


def get_tos_acceptance(user_id: str, tos_version: str) -> dict | None:
    """Get the acceptance record for a user and ToS version."""
    key = f"{user_id}:{tos_version}"
    return _tos_acceptances.get(key)


def reset_acceptances() -> None:
    """Reset all acceptance records (for testing)."""
    _tos_acceptances.clear()
