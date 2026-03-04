"""API documentation: integration guide, code examples, and OpenAPI metadata."""

from __future__ import annotations

API_DESCRIPTION = (
    "The Credit Assessment API evaluates credit profiles and returns five "
    "integrated outputs: a readiness score (0-100), barrier severity "
    "classification, timeline estimates for reaching credit score thresholds, "
    "product eligibility assessments, and structured dispute pathways with "
    "legal citations.\n\n"
    "## Authentication\n\n"
    "All assessment endpoints require a Bearer JWT token or API key in the "
    "`X-API-Key` header. Public endpoints (`/health`, `/disclosures`, "
    "`/legal/*`, `/docs/*`) do not require authentication.\n\n"
    "## Rate Limiting\n\n"
    "Assessment endpoints are rate-limited per subscription tier. "
    "Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, "
    "`X-RateLimit-Reset`) are included in responses."
)

API_TAGS = [
    {"name": "assessment", "description": "Credit profile assessment endpoints"},
    {"name": "auth", "description": "Authentication and token management"},
    {"name": "admin", "description": "Admin-only user and key management"},
    {"name": "legal", "description": "Privacy policy and terms of service"},
    {"name": "data-rights", "description": "GDPR/CCPA data export and deletion"},
    {"name": "docs", "description": "API documentation and integration guides"},
    {"name": "health", "description": "Health and readiness probes"},
]

_INTEGRATION_GUIDE: dict = {
    "authentication": (
        "Obtain a JWT token by posting credentials to POST /v1/auth/token. "
        "Include the token in the Authorization header as 'Bearer <token>'. "
        "Alternatively, pass an API key via the X-API-Key header. "
        "Tokens expire after the configured TTL (default: 60 minutes). "
        "Use POST /v1/auth/refresh to renew an active token."
    ),
    "endpoints": [
        {
            "method": "POST",
            "path": "/v1/assess",
            "description": "Run a full credit assessment. Requires auth.",
        },
        {
            "method": "GET",
            "path": "/v1/disclosures",
            "description": "FCRA Section 505 disclosures. No auth required.",
        },
        {
            "method": "GET",
            "path": "/v1/legal/privacy",
            "description": "Privacy policy. No auth required.",
        },
        {
            "method": "GET",
            "path": "/v1/legal/terms",
            "description": "Terms of service. No auth required.",
        },
        {
            "method": "GET",
            "path": "/v1/user/data-export",
            "description": "Export all user data (GDPR). Requires user_id param.",
        },
        {
            "method": "DELETE",
            "path": "/v1/user/data",
            "description": "Delete all user data (GDPR). Requires user_id param.",
        },
        {
            "method": "GET",
            "path": "/health",
            "description": "Health check. No auth required.",
        },
        {
            "method": "GET",
            "path": "/ready",
            "description": "Readiness probe with DB check. No auth required.",
        },
    ],
    "error_handling": (
        "Errors return JSON with a 'detail' field describing the issue. "
        "HTTP 422: Validation error (invalid input). "
        "HTTP 401: Invalid or missing JWT token. "
        "HTTP 403: Invalid or missing API key. "
        "HTTP 429: Rate limit exceeded (check Retry-After header). "
        "HTTP 500: Internal server error."
    ),
    "rate_limiting": (
        "Rate limits are applied per subscription tier: "
        "FREE: 10/minute, STARTER: 60/minute, PRO: 300/minute, "
        "ENTERPRISE: unlimited. "
        "Response headers include X-RateLimit-Limit, X-RateLimit-Remaining, "
        "and X-RateLimit-Reset."
    ),
}

_CODE_EXAMPLES: dict[str, str] = {
    "python": (
        "import requests\n"
        "\n"
        'url = "https://api.example.com/v1/assess"\n'
        "headers = {\n"
        '    "Authorization": "Bearer YOUR_JWT_TOKEN",\n'
        '    "Content-Type": "application/json",\n'
        "}\n"
        "payload = {\n"
        '    "current_score": 650,\n'
        '    "score_band": "fair",\n'
        '    "overall_utilization": 45.0,\n'
        '    "account_summary": {\n'
        '        "total_accounts": 6,\n'
        '        "open_accounts": 4\n'
        "    },\n"
        '    "payment_history_pct": 88.0,\n'
        '    "average_account_age_months": 36,\n'
        '    "negative_items": ["late_payment_30day"]\n'
        "}\n"
        "\n"
        "response = requests.post(url, json=payload, headers=headers)\n"
        "result = response.json()\n"
        "print(f\"Readiness: {result['readiness']['score']}/100\")\n"
    ),
    "javascript": (
        'const url = "https://api.example.com/v1/assess";\n'
        "\n"
        "const response = await fetch(url, {\n"
        '  method: "POST",\n'
        "  headers: {\n"
        '    "Authorization": "Bearer YOUR_JWT_TOKEN",\n'
        '    "Content-Type": "application/json",\n'
        "  },\n"
        "  body: JSON.stringify({\n"
        "    current_score: 650,\n"
        '    score_band: "fair",\n'
        "    overall_utilization: 45.0,\n"
        "    account_summary: { total_accounts: 6, open_accounts: 4 },\n"
        "    payment_history_pct: 88.0,\n"
        "    average_account_age_months: 36,\n"
        '    negative_items: ["late_payment_30day"],\n'
        "  }),\n"
        "});\n"
        "\n"
        "const result = await response.json();\n"
        "console.log(`Readiness: ${result.readiness.score}/100`);\n"
    ),
    "curl": (
        "curl -X POST https://api.example.com/v1/assess \\\n"
        '  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        "  -d '{\n"
        '    "current_score": 650,\n'
        '    "score_band": "fair",\n'
        '    "overall_utilization": 45.0,\n'
        '    "account_summary": {"total_accounts": 6, "open_accounts": 4},\n'
        '    "payment_history_pct": 88.0,\n'
        '    "average_account_age_months": 36,\n'
        '    "negative_items": ["late_payment_30day"]\n'
        "  }'"
    ),
}


def get_integration_guide() -> dict:
    """Return the full integration guide as structured data."""
    return _INTEGRATION_GUIDE


def get_code_examples() -> dict[str, str]:
    """Return code examples for Python, JavaScript, and curl."""
    return _CODE_EXAMPLES
