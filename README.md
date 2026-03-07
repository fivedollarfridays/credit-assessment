# Credit Assessment API

A production-grade FastAPI credit assessment platform. Evaluates credit profiles and provides readiness scores, barrier analysis, FCRA-compliant dispute pathways, product eligibility, score simulation, dispute letter generation, and longitudinal score tracking.

## Features

- **Credit Assessment Engine** -- FICO-weighted scoring with barrier analysis, product eligibility, and threshold estimates
- **Score Simulation** -- "what-if" projections (pay down balance, remove collection, etc.)
- **Dispute Lifecycle** -- full state machine (DRAFT > SENT > IN_REVIEW > RESPONDED > RESOLVED/ESCALATED) with FCRA 30/45-day deadline tracking
- **Dispute Letter Generation** -- 5 template types (validation, inaccuracy, completeness, obsolete item, identity theft) with legal citations
- **Score History** -- longitudinal tracking with source attribution (assessment/manual/external) and trend analysis
- **Multi-Tenant SaaS** -- org-scoped data isolation, RBAC (admin/analyst/viewer), scoped API keys
- **Billing** -- Stripe subscription integration with tier-based rate limiting
- **Webhooks** -- async delivery with retry logic and HMAC signature verification
- **Feature Flags** -- server-side toggles, per-org and percentage-based rollout
- **FCRA/GDPR Compliance** -- disclosures, audit trail, consent management, data export, atomic deletion
- **Observability** -- structured logging, Prometheus metrics, Sentry error tracking

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

No PostgreSQL or Redis required for development -- falls back to SQLite and in-memory rate limiting.

## Authentication

The API supports two auth methods:

### API Key (server-to-server)

Start with `API_KEY=dev-test-key` and pass the header:

```
X-API-Key: dev-test-key
```

### JWT (user sessions)

Dev mode has demo credentials (`admin`/`admin`):

```bash
# Get a token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use it
curl http://localhost:8000/v1/assess \
  -H "Authorization: Bearer <token>"
```

Demo credentials are disabled in production (`ENVIRONMENT=production`).

## API Endpoints

### Core Assessment

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/assess` | Full credit assessment (requires CreditProfile) |
| `POST` | `/v1/assess/simple` | Simplified assessment (flat fields, auto-derives score band) |
| `GET` | `/v1/assessments` | Paginated assessment history |

### Score Simulation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/simulate` | Score impact simulation with proposed actions |
| `POST` | `/v1/simulate/simple` | Simplified simulation input |

### Disputes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/disputes` | Create dispute (DRAFT status) |
| `GET` | `/v1/disputes` | List disputes (filterable by status, paginated) |
| `GET` | `/v1/disputes/{id}` | Get single dispute |
| `PATCH` | `/v1/disputes/{id}/status` | Update status with transition validation |
| `GET` | `/v1/disputes/deadlines` | Approaching FCRA deadlines |

### Dispute Letters

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/letters` | Generate dispute letter from template |
| `POST` | `/v1/letters/batch` | Batch letter generation |

### Score History

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/scores/history` | Paginated timeline with trend analysis |
| `POST` | `/v1/scores` | Record manual score entry |

### Auth & Users

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/token` | Get JWT access token |
| `POST` | `/auth/refresh` | Refresh token |
| `POST` | `/users/register` | Create account |
| `POST` | `/users/login` | Login |
| `POST` | `/users/reset-password` | Request password reset |
| `POST` | `/users/confirm-reset` | Confirm reset with token |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/webhooks` | Register webhook endpoint |
| `GET` | `/v1/webhooks` | List registered webhooks |
| `GET` | `/v1/webhooks/{id}/deliveries` | Delivery log |
| `DELETE` | `/v1/webhooks/{id}` | Remove webhook |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/admin/users` | List users (admin only) |
| `POST` | `/v1/admin/api-keys` | Create scoped API key |
| `GET` | `/v1/admin/audit-log` | Compliance audit trail |
| `DELETE` | `/v1/admin/api-keys/{key}` | Revoke API key |

### Feature Flags

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/flags` | Create flag |
| `GET` | `/v1/flags` | List flags |
| `PUT` | `/v1/flags/{key}` | Update flag |
| `DELETE` | `/v1/flags/{key}` | Delete flag |
| `GET` | `/v1/flags/{key}/evaluate` | Evaluate flag for current user |

### Data Rights (GDPR/CCPA)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/data-export` | Export user data |
| `DELETE` | `/data` | Delete user data |
| `POST` | `/consent` | Record consent |
| `DELETE` | `/consent` | Withdraw consent |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness check |
| `GET` | `/disclosures` | FCRA Section 605 disclosures |
| `GET` | `/legal/privacy` | Privacy policy |
| `GET` | `/legal/terms` | Terms of service |
| `GET` | `/docs/guide` | API guide |
| `GET` | `/docs/examples` | Code examples |

## Credit Assessment Request

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

Or use the simplified endpoint (`POST /v1/assess/simple`) which auto-derives `score_band` and accepts flat fields:

```json
{
  "credit_score": 650,
  "utilization_percent": 45.0,
  "total_accounts": 6,
  "open_accounts": 4,
  "payment_history_percent": 88.0,
  "oldest_account_months": 36,
  "negative_items": ["late_payment_30day"]
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
| `API_KEY` | API key for X-API-Key auth (empty = auth disabled) | _(none)_ |
| `JWT_SECRET` | JWT signing secret | `change-me-in-production` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRY_MINUTES` | Token lifetime | `30` |
| `ENVIRONMENT` | `development` / `staging` / `production` | `development` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./credit.db` |
| `REDIS_URL` | Redis URL for rate limiting | _(none, falls back to in-memory)_ |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `SENTRY_DSN` | Sentry error tracking DSN | _(none)_ |
| `STRIPE_SECRET_KEY` | Stripe API secret key | _(none)_ |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | _(none)_ |
| `PII_PEPPER` | Pepper for PII hashing | `default-pii-pepper` |
| `MAX_LOGIN_ATTEMPTS` | Failed logins before lockout | `5` |
| `LOCKOUT_DURATION_MINUTES` | Lockout duration | `15` |

Copy `.env.example` to `.env` for local configuration:

```bash
cp .env.example .env
```

## Make Targets

```bash
make install   # Install dependencies
make dev       # Start dev server (port 8000, API_KEY=dev-test-key)
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
# Run all tests (1,154+, 100% coverage enforced)
make test

# Run with coverage report
make coverage

# Run specific test file
pytest src/modules/credit/tests/test_assessment.py -v
```

## Architecture

```
src/modules/credit/
  # Configuration & Startup
  config.py               # Settings (pydantic-settings)
  router.py               # FastAPI app + route mounting
  database.py             # SQLAlchemy async engine
  models_db.py            # ORM models (User, Assessment, Dispute, ScoreHistory, etc.)
  logging_config.py       # Structured logging setup
  middleware.py           # Request IDs, HSTS, HTTPS redirect
  observability.py        # Sentry + Prometheus setup

  # Auth & Users
  auth.py                 # JWT tokens, API key auth, verify_auth
  auth_routes.py          # /auth/token, /auth/refresh
  user_store.py           # User data-access layer
  user_routes.py          # Registration, login, password reset
  roles.py                # RBAC (admin/analyst/viewer)
  password.py             # bcrypt hashing

  # Core Assessment
  assess_routes.py        # POST /v1/assess, /v1/assess/simple
  assessment.py           # Credit scoring engine (FICO-weighted)
  types.py                # CreditProfile, AccountSummary, ScoreBand, etc.

  # Simulation
  simulation.py           # Score impact simulation engine (10 action handlers)
  simulate_routes.py      # POST /v1/simulate

  # Disputes
  dispute_models.py       # DisputeStatus enum, transition rules, FCRA deadlines
  dispute_pathway.py      # Legal dispute pathway generator
  dispute_routes.py       # CRUD + status transitions
  repo_disputes.py        # Dispute repository

  # Letters
  letter_types.py         # Bureau enum, LetterType enum
  letter_templates.py     # 5 dispute letter templates
  letter_generator.py     # Template engine with bureau addresses
  letter_routes.py        # POST /v1/letters

  # Score History
  score_models.py         # ScoreSource enum
  score_routes.py         # GET /v1/scores/history, POST /v1/scores
  repo_scores.py          # Score history repository

  # Multi-Tenant & Billing
  tenant.py               # Org isolation
  billing.py              # Stripe billing integration
  rate_limit.py           # Per-customer rate limiting (tier-based)

  # Webhooks
  webhooks.py             # Webhook registration CRUD
  webhook_delivery.py     # Async delivery + HMAC signatures
  webhook_routes.py       # Webhook endpoints

  # Feature Flags
  feature_flags.py        # Flag evaluation engine
  flag_routes.py          # Flag CRUD + evaluation endpoints

  # Compliance & Legal
  audit.py                # Compliance audit trail
  data_rights.py          # GDPR/CCPA data handling
  data_rights_routes.py   # Export, delete, consent endpoints
  disclosures.py          # FCRA Section 605 content
  disclosures_routes.py   # GET /disclosures
  legal.py                # Privacy policy, terms of service
  legal_routes.py         # Legal document endpoints

  # Admin & Ops
  admin_routes.py         # Admin user/key/audit management
  dashboard.py            # Usage analytics engine
  dashboard_routes.py     # Admin dashboard endpoints
  metrics.py              # Prometheus instrumentation
  alerting.py             # PagerDuty/Opsgenie integration
  backup.py               # Database backup utilities
  deploy.py               # Blue/green deployment helpers
  retention.py            # Data retention policies
  sentry.py               # Sentry configuration

  # Data Access
  repository.py           # Base repository patterns
  repo_api_keys.py        # API key repository
  repo_assessments.py     # Assessment history repository
  repo_billing.py         # Billing repository
  repo_data_rights.py     # Data rights repository
  repo_flags.py           # Feature flag repository
  repo_users.py           # User repository
  repo_webhooks.py        # Webhook repository

  # API Documentation
  api_docs.py             # OpenAPI metadata
  docs_routes.py          # Guide and example endpoints

  tests/                  # 1,154+ tests, 100% coverage
```

## License

Proprietary. All rights reserved. See [LICENSE](LICENSE).
