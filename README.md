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
pip install -e ".[dev]"

# Run tests
coverage run -m pytest src/modules/credit/tests/ -v

# Start the development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Reference

### Health Check

```
GET /health
```

Returns `{"status": "ok"}`.

### Credit Assessment

```
POST /assess
Content-Type: application/json
X-API-Key: your-api-key  (required if API_KEY env var is set)
```

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
| `ENVIRONMENT` | Deployment environment | `development` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

Copy `.env.example` to `.env` for local configuration:

```bash
cp .env.example .env
```

## Testing

```bash
# Run all tests
coverage run -m pytest src/modules/credit/tests/ -v

# Check coverage (must be 100%)
coverage report --show-missing

# Run specific test file
pytest src/modules/credit/tests/test_assessment.py -v
```

## Architecture

```
src/modules/credit/
  types.py             # Domain models, enums, constants (Pydantic v2)
  config.py            # Settings class (pydantic-settings)
  assessment.py        # Credit scoring engine
  dispute_pathway.py   # Legal dispute pathway generator
  router.py            # FastAPI endpoints (/health, /assess)
  logging_config.py    # Structured logging (structlog)
  middleware.py        # Request ID middleware
  tests/               # 220+ tests, 100% coverage
```

## License

TBD
