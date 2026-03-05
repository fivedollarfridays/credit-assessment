# MontGoWork — Credit Assessment Integration Guide

> For the World Wide Vibes Hackathon (March 5-9, 2026).
> Wire this up Thursday morning with zero guesswork.

---

## 1. Dev Startup (Copy-Paste Ready)

```bash
cd ~/projects/credit-assessment

# Install dependencies (one time)
pip install -e ".[dev]"

# Start the API
API_KEY=dev-test-key uvicorn main:app --app-dir src --reload --port 8000
```

**That's it.** No PostgreSQL, no Redis, no Docker required for dev.

| Question | Answer |
|----------|--------|
| PostgreSQL needed? | No. Falls back to SQLite (`credit.db` in project root) |
| Redis needed? | No. Rate limiting falls back to in-memory |
| Default port? | **8000** |
| Required env vars? | **None.** All have defaults. Set `API_KEY` for API key auth. |
| Health check | `GET http://localhost:8000/health` → `{"status": "ok"}` |

### Optional Env Vars

| Var | Default | Notes |
|-----|---------|-------|
| `API_KEY` | `None` (disabled) | Set any string to enable X-API-Key auth |
| `JWT_SECRET` | `change-me-in-production` | Auto-set for dev |
| `ENVIRONMENT` | `development` | Enables demo credentials |
| `DATABASE_URL` | `sqlite+aiosqlite:///./credit.db` | Override for Postgres |
| `REDIS_URL` | `None` | Override for Redis-backed rate limiting |

---

## 2. Auth for Dev

### Simplest Path: API Key (Recommended for MontGoWork Proxy)

Start the server with `API_KEY=dev-test-key`, then pass the header:

```
X-API-Key: dev-test-key
```

This is the best option for a server-to-server proxy. No user registration, no token refresh, no expiry.

### Alternative: Demo JWT

Dev mode has built-in demo credentials (`admin`/`admin`):

```bash
# Get a JWT (valid for 30 minutes)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
# → {"access_token": "eyJ...", "token_type": "bearer"}

# Use it
curl http://localhost:8000/v1/assess \
  -H "Authorization: Bearer eyJ..."
```

Demo credentials are disabled in production (`ENVIRONMENT=production`).

### What the MontGoWork Proxy Should Send

```
POST /v1/assess HTTP/1.1
Host: <credit-api-host>:8000
Content-Type: application/json
X-API-Key: dev-test-key

{ ... credit profile ... }
```

---

## 3. Request Schema — CreditProfile

### Pydantic Model

```python
class AccountSummary(BaseModel):
    total_accounts: int         # >= 0, REQUIRED
    open_accounts: int          # >= 0, REQUIRED
    closed_accounts: int = 0    # >= 0, optional
    negative_accounts: int = 0  # >= 0, optional
    collection_accounts: int = 0 # >= 0, optional
    total_balance: float = 0.0  # >= 0, optional
    total_credit_limit: float = 0.0  # >= 0, optional
    monthly_payments: float = 0.0    # >= 0, optional

class CreditProfile(BaseModel):
    current_score: int              # 300-850, REQUIRED
    score_band: ScoreBand           # "excellent"|"good"|"fair"|"poor"|"very_poor", REQUIRED
    overall_utilization: float      # 0.0-100.0, REQUIRED
    account_summary: AccountSummary # REQUIRED
    payment_history_pct: float      # 0.0-100.0, REQUIRED
    average_account_age_months: int # 0-1200, REQUIRED
    negative_items: list[str] = []  # optional, max 50 items, each max 200 chars
```

### Score Band Validation

The `score_band` must match `current_score`. If they don't match, you get a 422:

| Score Band | Score Range |
|-----------|-------------|
| `excellent` | 750-850 |
| `good` | 700-749 |
| `fair` | 650-699 |
| `poor` | 600-649 |
| `very_poor` | 300-599 |

### Minimal Valid Payload

```json
{
  "current_score": 700,
  "score_band": "good",
  "overall_utilization": 25.0,
  "account_summary": {"total_accounts": 5, "open_accounts": 3},
  "payment_history_pct": 95.0,
  "average_account_age_months": 48
}
```

### Maria's Full Payload (Demo Persona)

Maria: FICO 520, one $2,500 medical collection (18 months old), 3 late payments (24 months old), 85% utilization, denied for employment and auto loan.

```json
{
  "current_score": 520,
  "score_band": "very_poor",
  "overall_utilization": 85.0,
  "account_summary": {
    "total_accounts": 8,
    "open_accounts": 4,
    "closed_accounts": 4,
    "negative_accounts": 4,
    "collection_accounts": 1,
    "total_balance": 12750.0,
    "total_credit_limit": 15000.0,
    "monthly_payments": 380.0
  },
  "payment_history_pct": 72.0,
  "average_account_age_months": 36,
  "negative_items": [
    "collection_medical_2500",
    "late_payment_30day_auto",
    "late_payment_60day_credit_card",
    "late_payment_30day_personal"
  ]
}
```

---

## 4. Working curl Command (Maria)

```bash
curl -X POST http://localhost:8000/v1/assess \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-test-key" \
  -d '{
    "current_score": 520,
    "score_band": "very_poor",
    "overall_utilization": 85.0,
    "account_summary": {
      "total_accounts": 8,
      "open_accounts": 4,
      "closed_accounts": 4,
      "negative_accounts": 4,
      "collection_accounts": 1,
      "total_balance": 12750.0,
      "total_credit_limit": 15000.0,
      "monthly_payments": 380.0
    },
    "payment_history_pct": 72.0,
    "average_account_age_months": 36,
    "negative_items": [
      "collection_medical_2500",
      "late_payment_30day_auto",
      "late_payment_60day_credit_card",
      "late_payment_30day_personal"
    ]
  }'
```

---

## 5. Actual Response (Maria)

This is the real output from the API — not mocked:

```json
{
  "barrier_severity": "high",
  "barrier_details": [
    {
      "severity": "high",
      "description": "1 collection account(s) on file",
      "affected_accounts": [],
      "estimated_resolution_days": 90
    },
    {
      "severity": "high",
      "description": "Utilization at 85% (above 75%)",
      "affected_accounts": [],
      "estimated_resolution_days": 60
    },
    {
      "severity": "high",
      "description": "Score 520 is below 580",
      "affected_accounts": [],
      "estimated_resolution_days": 180
    }
  ],
  "readiness": {
    "score": 20,
    "fico_score": 520,
    "score_band": "very_poor",
    "factors": {
      "payment_history": 0.72,
      "utilization": 0.15,
      "credit_age": 0.429,
      "credit_mix": 0.8,
      "new_credit": 0.7
    }
  },
  "thresholds": [
    {
      "threshold_name": "Poor Credit",
      "threshold_score": 600,
      "estimated_days": 400,
      "already_met": false,
      "confidence": "low"
    },
    {
      "threshold_name": "Fair Credit",
      "threshold_score": 650,
      "estimated_days": 650,
      "already_met": false,
      "confidence": "low"
    },
    {
      "threshold_name": "Good Credit",
      "threshold_score": 700,
      "estimated_days": 900,
      "already_met": false,
      "confidence": "low"
    },
    {
      "threshold_name": "Excellent Credit",
      "threshold_score": 750,
      "estimated_days": 1150,
      "already_met": false,
      "confidence": "low"
    }
  ],
  "dispute_pathway": {
    "steps": [
      {
        "step_number": 1,
        "action": "Validate and dispute collection: collection_medical_2500",
        "description": "File dispute for collection: collection_medical_2500",
        "legal_basis": "FDCPA Section 809 — Debt validation",
        "estimated_days": 30,
        "priority": "critical"
      },
      {
        "step_number": 2,
        "action": "Dispute late payment: late_payment_30day_auto",
        "description": "File dispute for late payment: late_payment_30day_auto",
        "legal_basis": "FCRA Section 611 — Reinvestigation of disputed information",
        "estimated_days": 30,
        "priority": "high"
      },
      {
        "step_number": 3,
        "action": "Dispute late payment: late_payment_60day_credit_card",
        "description": "File dispute for late payment: late_payment_60day_credit_card",
        "legal_basis": "FCRA Section 611 — Reinvestigation of disputed information",
        "estimated_days": 30,
        "priority": "high"
      },
      {
        "step_number": 4,
        "action": "Dispute late payment: late_payment_30day_personal",
        "description": "File dispute for late payment: late_payment_30day_personal",
        "legal_basis": "FCRA Section 611 — Reinvestigation of disputed information",
        "estimated_days": 30,
        "priority": "high"
      },
      {
        "step_number": 5,
        "action": "Review balance reporting accuracy",
        "description": "Verify reported balances are accurate (utilization at 85%)",
        "legal_basis": "FCRA Section 607(b) — Accuracy requirements",
        "estimated_days": 30,
        "priority": "medium"
      }
    ],
    "total_estimated_days": 150,
    "statutes_cited": [
      "15 U.S.C. § 1681e(b)",
      "15 U.S.C. § 1681i",
      "15 U.S.C. § 1681i(a)",
      "15 U.S.C. § 1692g"
    ],
    "legal_theories": [
      "fcra_607b_accuracy",
      "fcra_611_reinvestigation",
      "fcra_623_furnisher_duties",
      "fdcpa_809_validation",
      "metro2_logical_inconsistency"
    ]
  },
  "eligibility": [
    {
      "product_name": "FHA Mortgage",
      "category": "mortgage",
      "required_score": 580,
      "status": "blocked",
      "gap_points": 60,
      "estimated_days_to_eligible": 300,
      "blocking_factors": ["Score 520 below 580", "High utilization", "Active collections"]
    },
    {
      "product_name": "Conventional Mortgage",
      "category": "mortgage",
      "required_score": 620,
      "status": "blocked",
      "gap_points": 100,
      "estimated_days_to_eligible": 500,
      "blocking_factors": ["Score 520 below 620", "High utilization", "Active collections"]
    },
    {
      "product_name": "Prime Auto Loan",
      "category": "auto",
      "required_score": 700,
      "status": "blocked",
      "gap_points": 180,
      "estimated_days_to_eligible": 900,
      "blocking_factors": ["Score 520 below 700", "High utilization", "Active collections"]
    },
    {
      "product_name": "Subprime Auto Loan",
      "category": "auto",
      "required_score": 500,
      "status": "eligible",
      "gap_points": 0,
      "estimated_days_to_eligible": null,
      "blocking_factors": []
    },
    {
      "product_name": "Rewards Credit Card",
      "category": "credit_card",
      "required_score": 700,
      "status": "blocked",
      "gap_points": 180,
      "estimated_days_to_eligible": 900,
      "blocking_factors": ["Score 520 below 700", "High utilization", "Active collections"]
    },
    {
      "product_name": "Secured Credit Card",
      "category": "credit_card",
      "required_score": 300,
      "status": "eligible",
      "gap_points": 0,
      "estimated_days_to_eligible": null,
      "blocking_factors": []
    },
    {
      "product_name": "Personal Loan",
      "category": "personal_loan",
      "required_score": 640,
      "status": "blocked",
      "gap_points": 120,
      "estimated_days_to_eligible": 600,
      "blocking_factors": ["Score 520 below 640", "High utilization", "Active collections"]
    },
    {
      "product_name": "Best Rate Mortgage",
      "category": "mortgage",
      "required_score": 740,
      "status": "blocked",
      "gap_points": 220,
      "estimated_days_to_eligible": 1100,
      "blocking_factors": ["Score 520 below 740", "High utilization", "Active collections"]
    }
  ],
  "disclaimer": "This credit assessment is provided for educational and informational purposes only. This service is not a consumer reporting agency as defined by the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq., and the information provided does not constitute a consumer report. The scores, estimates, and recommendations presented are not intended to be used as a basis for any credit, employment, insurance, or other eligibility decision. Under FCRA Section 605, consumers have the right to dispute inaccurate information directly with credit reporting agencies. If you believe any information on your credit report is inaccurate, you should contact the relevant credit bureau directly. All timeline estimates and score projections are approximate and for educational purposes only."
}
```

### Response Schema Summary

All 5 outputs confirmed present:

| Output | Field | Type | Maria's Value |
|--------|-------|------|---------------|
| Barrier Severity | `barrier_severity` | `"high"` / `"medium"` / `"low"` | `"high"` |
| Barrier Details | `barrier_details[]` | Array of {severity, description, estimated_resolution_days} | 3 barriers (collections, utilization, low score) |
| Readiness Score | `readiness.score` | 0-100 int | **20** out of 100 |
| Factor Breakdown | `readiness.factors` | Dict of 5 weighted factors (0.0-1.0) | payment_history: 0.72, utilization: 0.15 |
| Time to Thresholds | `thresholds[]` | Array of {threshold_name, threshold_score, estimated_days, already_met, confidence} | 400 days to Poor (600), 650 to Fair, 900 to Good |
| Dispute Pathway | `dispute_pathway.steps[]` | Ordered steps with legal_basis, priority, estimated_days | 5 steps, 150 total days, starts with collection dispute |
| Legal Citations | `dispute_pathway.statutes_cited` | Federal statute references | 15 U.S.C. §§ 1681e(b), 1681i, 1681i(a), 1692g |
| Product Eligibility | `eligibility[]` | Array of {product_name, status, gap_points, estimated_days_to_eligible, blocking_factors} | Eligible: Subprime Auto, Secured Card. Blocked: everything else. |
| FCRA Disclaimer | `disclaimer` | String (always present in response body) | Full FCRA disclaimer text |

---

## 6. Integration Contract

| Question | Answer |
|----------|--------|
| Content-Type | `application/json` |
| Rate limit (dev) | 30/minute on `/v1/assess` (in-memory, resets on restart) |
| Rate limit headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| FCRA disclaimer | Included in every response JSON as `disclaimer` field |
| Separate disclaimer endpoint? | Also at `GET /disclosures` (no auth) but not needed — it's in every response |
| CORS needed? | **No.** Server-to-server from FastAPI proxy. CORS only matters for browser requests. |
| 422 errors | Invalid payload (bad score_band/score mismatch, out-of-range values) |
| 403 errors | Missing or wrong credentials |

---

## 7. Python Proxy Snippet (httpx async)

### Recommended: Using `/assess/simple`

```python
"""MontGoWork credit assessment proxy — calls credit API's simple endpoint."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/credit", tags=["credit"])

CREDIT_API_BASE = "http://localhost:8000"
CREDIT_API_KEY = "dev-test-key"


class SimpleCreditRequest(BaseModel):
    """Flat fields — no score_band derivation or AccountSummary needed."""
    credit_score: int = Field(ge=300, le=850)
    utilization_percent: float = Field(ge=0.0, le=100.0)
    total_accounts: int = Field(ge=0)
    open_accounts: int = Field(ge=0)
    negative_items: list[str] = []
    payment_history_percent: float = Field(ge=0.0, le=100.0)
    oldest_account_months: int = Field(ge=0)
    total_balance: float = 0.0
    total_credit_limit: float = 0.0
    monthly_payments: float = 0.0


@router.post("/assess")
async def assess_credit(profile: SimpleCreditRequest):
    """Proxy to the credit assessment microservice (simple endpoint)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{CREDIT_API_BASE}/v1/assess/simple",
            json=profile.model_dump(),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": CREDIT_API_KEY,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=resp.json().get("detail", "Credit API error"),
        )
    return resp.json()
```

### Legacy: Using `/assess` (full CreditProfile)

<details>
<summary>Click to expand if you need the full-schema version</summary>

```python
"""MontGoWork credit assessment proxy — calls Shawn's credit API."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/credit", tags=["credit"])

CREDIT_API_BASE = "http://localhost:8000"
CREDIT_API_KEY = "dev-test-key"


class CreditProfileRequest(BaseModel):
    """Thin proxy — passes through to credit API."""
    current_score: int
    score_band: str
    overall_utilization: float
    account_summary: dict
    payment_history_pct: float
    average_account_age_months: int
    negative_items: list[str] = []


@router.post("/assess")
async def assess_credit(profile: CreditProfileRequest):
    """Proxy to the credit assessment microservice."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{CREDIT_API_BASE}/v1/assess",
            json=profile.model_dump(),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": CREDIT_API_KEY,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=resp.json().get("detail", "Credit API error"),
        )
    return resp.json()
```

</details>

### Usage from MontGoWork Frontend

```
POST /api/credit/assess
Content-Type: application/json

{
  "current_score": 520,
  "score_band": "very_poor",
  "overall_utilization": 85.0,
  "account_summary": {
    "total_accounts": 8,
    "open_accounts": 4,
    "collection_accounts": 1
  },
  "payment_history_pct": 72.0,
  "average_account_age_months": 36,
  "negative_items": ["collection_medical_2500", "late_payment_30day_auto"]
}
```

---

## 8. Gotchas and Blockers

### Score Band Must Match Score

The API validates that `score_band` is consistent with `current_score`. If Maria's score is 520, the band **must** be `"very_poor"` (300-599). Sending `"poor"` (600-649) with score 520 returns a 422. Your frontend/intake form should auto-derive the band:

```python
def score_to_band(score: int) -> str:
    if score >= 750: return "excellent"
    if score >= 700: return "good"
    if score >= 650: return "fair"
    if score >= 600: return "poor"
    return "very_poor"
```

### negative_items Are Free-Text Strings

The engine pattern-matches on prefixes: `collection_`, `late_payment_`, `charge_off_`, `identity_theft_`, etc. For the best dispute pathway output, use descriptive strings like `"collection_medical_2500"` or `"late_payment_60day_credit_card"`. Plain strings like `"bad debt"` still work but generate generic dispute steps.

### Estimated Days Are Rough

`estimated_days` in thresholds uses ~0.2 FICO points per day of consistent positive behavior. These are directional, not precise — fine for a hackathon demo but flag them as estimates in the UI.

### The API Is Stateless for Assessments

Each `POST /v1/assess` is a pure computation — no user context is stored. The API has database persistence for audit trails but the assessment itself is a stateless function of the input profile. You can call it as many times as you want with different profiles.

### No HTTPS in Dev

Dev runs plain HTTP on port 8000. No TLS setup needed. HTTPS is enforced only when `ENVIRONMENT=production`.

---

## 9. Recommended: Use `/assess/simple` Instead

Your proxy currently builds the full `CreditProfile` — deriving `score_band`, constructing `AccountSummary`, estimating `average_account_age_months`. Our `/v1/assess/simple` endpoint does all of that for you:

```json
POST /v1/assess/simple
{
  "credit_score": 520,
  "utilization_percent": 85.0,
  "total_accounts": 8,
  "open_accounts": 4,
  "negative_items": ["collection_medical_2500", "late_payment_30day_auto"],
  "payment_history_percent": 72.0,
  "oldest_account_months": 60,
  "total_balance": 12750.0,
  "total_credit_limit": 15000.0,
  "monthly_payments": 380.0
}
```

**Why switch:**
- No `score_band` derivation needed — the API derives it from `credit_score`
- No `AccountSummary` construction — just pass flat fields
- `oldest_account_months` instead of `average_account_age_months` — easier for users to know
- Same response schema, same auth, same rate limits
- If we change score band boundaries, your code stays correct automatically

**What changes in MontGoWork's proxy:**
- Remove `score_to_band()` helper
- Remove `AccountSummary` construction
- Change endpoint from `/v1/assess` to `/v1/assess/simple`
- Pass flat fields directly from your intake form

---

## 10. Rate Limits

Your proxy should be aware of rate limits, especially during demo flows with pre-crawl + assessment:

| Limit | Value | Scope |
|-------|-------|-------|
| `/v1/assess` and `/v1/assess/simple` | 30 requests/minute | Per client IP |
| Dev mode | In-memory counter, resets on server restart |
| Rate limit headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| Over limit | HTTP 429 with `Retry-After` header |

For a hackathon demo this is unlikely to matter, but if you batch-process multiple users or retry aggressively, you could hit it.

---

## Quick Reference Card

```
START:    API_KEY=dev-test-key uvicorn main:app --app-dir src --reload --port 8000
HEALTH:   curl http://localhost:8000/health
SIMPLE:   POST http://localhost:8000/v1/assess/simple  +  X-API-Key: dev-test-key  (recommended)
FULL:     POST http://localhost:8000/v1/assess         +  X-API-Key: dev-test-key  (if you need full control)
SCHEMA:   GET  http://localhost:8000/openapi.json  (full OpenAPI spec)
DOCS:     GET  http://localhost:8000/docs          (Swagger UI, dev only)
```
