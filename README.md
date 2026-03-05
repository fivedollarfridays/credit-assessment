# Credit Assessment API

A FastAPI-based credit assessment service that evaluates credit profiles and provides readiness scores, barrier analysis, dispute pathways, product eligibility, and threshold estimates.

## Quick Start

```bash
# Clone and run with Docker
docker-compose up

# The API is available at http://localhost:8000
curl http://localhost:8000/health
```

## Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
make install

# Set up pre-commit hooks
pre-commit install

# Run tests
make test

# Start the development server
make dev
```

## API Reference

### Health Check

```
GET /health
```

Returns `{"status": "ok"}`.

### Credit Assessment

```
POST /v1/assess
Content-Type: application/json
X-API-Key: your-api-key
```

> **Note:** The legacy `POST /assess` endpoint still works but is deprecated. Use `/v1/assess`.

**Request:**

```json
{
  "current_score": 650,
  "score_band": "fair",
  "overall_utilization": 45.0,
  "account_summary": {
    "total_accounts": 6,
    "open_accounts": 4,
    "closed_accounts": 2,
    "negative_accounts": 1,
    "collection_accounts": 0,
    "total_balance": 13500.0,
    "total_credit_limit": 30000.0,
    "monthly_payments": 450.0
  },
  "payment_history_pct": 88.0,
  "average_account_age_months": 36,
  "negative_items": ["late_payment_30day"]
}
```

**Response:**

```json
{
  "barrier_severity": "medium",
  "readiness": {
    "score": 55,
    "fico_score": 650,
    "score_band": "fair",
    "factors": {
      "payment_history": 26.4,
      "utilization": 11.0,
      "account_age": 9.0,
      "account_mix": 6.0,
      "negative_items": -5.0
    }
  },
  "barriers": [...],
  "thresholds": [...],
  "dispute_pathway": {...},
  "eligibility": [...],
  "disclaimer": "This assessment is for educational purposes only..."
}
```

### Score Bands

| Band | Score Range |
|------|-----------|
| Excellent | 750-850 |
| Good | 700-749 |
| Fair | 650-699 |
| Poor | 600-649 |
| Very Poor | 300-599 |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | API authentication key (empty = auth disabled) | _(none)_ |
| `JWT_SECRET` | JWT signing secret | `change-me-in-production` |
| `ENVIRONMENT` | Deployment environment | `development` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./credit.db` |
| `REDIS_URL` | Redis URL for rate limiting | _(none, falls back to in-memory)_ |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

Copy `.env.example` to `.env` for local configuration:

```bash
cp .env.example .env
```

## Make Targets

```bash
make install   # Install dependencies
make dev       # Start dev server (port 8000)
make test      # Run tests
make coverage  # Run tests with coverage report
make lint      # Run linter
make fmt       # Auto-format code
make check     # Run all checks (lint + format + tests)
make docker    # Build Docker image
make clean     # Remove build artifacts
```

## Testing

```bash
# Run all tests (797+, 100% coverage)
make test

# Run with coverage report
make coverage

# Run specific test file
pytest src/modules/credit/tests/test_assessment.py -v
```

## Architecture

```
src/modules/credit/
  config.py              # Settings (pydantic-settings)
  router.py              # FastAPI app + route mounting
  auth.py                # JWT tokens, API key auth
  auth_routes.py         # /auth/token, /auth/refresh
  user_store.py          # User data-access layer
  user_routes.py         # Registration, login, password reset
  roles.py               # RBAC (admin/analyst/viewer)
  assess_routes.py       # POST /v1/assess endpoint
  assessment.py          # Credit scoring engine
  dispute_pathway.py     # Legal dispute pathway generator
  tenant.py              # Multi-tenant org isolation
  billing.py             # Stripe billing integration
  rate_limit.py          # Per-customer rate limiting
  webhooks.py            # Webhook registration CRUD
  webhook_delivery.py    # Webhook delivery + HMAC signatures
  feature_flags.py       # Gradual rollout flags
  audit.py               # Compliance audit trail
  data_rights.py         # GDPR/CCPA data handling
  dashboard.py           # Admin usage analytics
  middleware.py          # Request IDs, HSTS, HTTPS redirect
  metrics.py             # Prometheus instrumentation
  database.py            # SQLAlchemy async engine
  models_db.py           # ORM models
  repository.py          # Database repositories
  tests/                 # 797+ tests, 100% coverage
```

## License

Proprietary. All rights reserved. See [LICENSE](LICENSE).
