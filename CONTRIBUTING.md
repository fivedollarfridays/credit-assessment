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
make dev       # Start dev server (localhost:8000)
make test      # Run tests
make lint      # Run linter
make fmt       # Auto-format code
make check     # Run all checks (lint + format + tests)
```

## Code Standards

- **100% test coverage** — enforced by CI
- **TDD** — write failing tests before implementation
- **ruff** — linting and formatting (auto-runs via pre-commit)
- **Architecture limits** — files under 200 lines (warning), 400 lines (error)
- Run `bpsai-pair arch check <file>` before submitting

## Project Layout

```
src/modules/credit/
  config.py              # Settings (pydantic-settings)
  router.py              # FastAPI app + route mounting
  auth.py / auth_routes.py    # JWT + API key auth
  user_store.py / user_routes.py  # User data layer + routes
  assess_routes.py       # Credit assessment endpoint
  assessment.py          # Scoring engine
  roles.py               # RBAC (admin/analyst/viewer)
  tenant.py              # Multi-tenant org isolation
  webhooks.py / webhook_delivery.py  # Webhook system
  tests/                 # 797+ tests
```

## Commit Messages

Follow existing style: short summary, optional body with details.

```
Sprint 15: module decomposition, store encapsulation, dependency pinning
```

## Pull Requests

- Branch from `main`
- All CI checks must pass
- Include test coverage for new code
