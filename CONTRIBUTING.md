# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
make install
pre-commit install
```

## Development Workflow

```bash
make dev       # Start dev server (localhost:8000, API_KEY=dev-test-key)
make test      # Run tests
make lint      # Run linter
make fmt       # Auto-format code
make check     # Run all checks (lint + format + tests)
```

## Code Standards

- **100% test coverage** -- enforced by CI (`fail_under=100`)
- **TDD** -- write failing tests before implementation
- **ruff** -- linting and formatting (auto-runs via pre-commit)
- **Architecture limits** -- source files < 400 lines, < 15 functions, < 20 imports
- Run `bpsai-pair arch check <file>` before submitting

## Project Layout

```
src/modules/credit/
  config.py                # Settings (pydantic-settings)
  router.py                # FastAPI app + route mounting
  auth.py / auth_routes.py # JWT + API key auth
  user_store.py / user_routes.py  # User data layer + routes
  assess_routes.py         # Credit assessment endpoints
  assessment.py            # Scoring engine
  simulation.py            # Score simulation engine
  dispute_routes.py        # Dispute lifecycle endpoints
  letter_generator.py      # Dispute letter generation
  score_routes.py          # Score history endpoints
  roles.py                 # RBAC (admin/analyst/viewer)
  tenant.py                # Multi-tenant org isolation
  webhooks.py / webhook_delivery.py  # Webhook system
  feature_flags.py / flag_routes.py  # Feature flags
  data_rights.py           # GDPR/CCPA compliance
  models_db.py             # ORM models
  repo_*.py                # Repository pattern (7 repos)
  tests/                   # 1,154+ tests, 100% coverage
```

## Commit Messages

Follow existing style: short summary, optional body with details.

```
Sprint 23: dispute lifecycle + score history -- models, endpoints, code review fixes
```

## Pull Requests

- Branch from `main`
- All CI checks must pass (lint, format, 100% coverage)
- Include test coverage for new code
