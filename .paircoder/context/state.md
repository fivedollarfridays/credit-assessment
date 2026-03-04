# Current State

> Last updated: 2026-03-03

## Active Plan

**Plan:** plan-2026-03-plan-saas-readiness
**Status:** Planned
**Current Sprint:** 2

## Current Focus

SaaS readiness: containerize, add CI/CD, structured logging, env management, and documentation.

## Task Status

### Sprint 2 — Phase 1: Deployable (Weeks 1-2)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T2.1 | Dockerfile + docker-compose | P0 | 35 | ✓ Done |
| T2.2 | CI/CD pipeline (GitHub Actions) | P0 | 40 | ✓ Done |
| T2.3 | Structured logging with request IDs | P1 | 30 | ✓ Done |
| T2.4 | .env management — dotenv + secrets | P1 | 20 | ✓ Done |
| T2.5 | README with setup/run instructions | P1 | 15 | ✓ Done |

### Sprint 3 — Phase 2: Secure & Observable (Weeks 3-4)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T3.1 | HTTPS / TLS enforcement | P1 | 35 | ✓ Done |
| T3.2 | JWT auth replacing API key | P0 | 55 | ✓ Done |
| T3.3 | Database + migrations (PostgreSQL + Alembic) | P0 | 70 | ✓ Done |
| T3.4 | Prometheus metrics + health checks | P1 | 40 | ✓ Done |
| T3.5 | Error tracking — Sentry integration | P1 | 25 | ✓ Done |

### Sprint 4 — Phase 3: Multi-Tenant SaaS (Weeks 5-8)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T4.1 | User management — signup, login, reset | P0 | 60 | Pending |
| T4.2 | RBAC — roles with scoped API keys | P0 | 55 | Pending |
| T4.3 | Per-customer rate limiting | P1 | 40 | Pending |
| T4.4 | Billing integration — Stripe | P1 | 70 | Pending |
| T4.5 | Tenant isolation — org-scoped data | P0 | 50 | Pending |
| T4.6 | API versioning — /v1/ prefix | P1 | 30 | Pending |

### Sprint 5 — Phase 4: Production Operations (Weeks 9-10)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T5.1 | Load testing — Locust/K6 scripts | P1 | 35 | Pending |
| T5.2 | Blue/green deploys | P0 | 50 | Pending |
| T5.3 | Alerting — PagerDuty/Opsgenie | P1 | 35 | Pending |
| T5.4 | Backup and disaster recovery | P0 | 45 | Pending |
| T5.5 | Runbooks — incident response | P2 | 20 | Pending |

### Sprint 6 — Phase 5: Compliance & Documentation (Weeks 11-12)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T6.1 | FCRA Section 505 disclosures | P0 | 40 | Pending |
| T6.2 | Privacy policy + Terms of Service | P1 | 30 | Pending |
| T6.3 | GDPR/CCPA data handling | P0 | 55 | Pending |
| T6.4 | Audit trail — log assessments | P0 | 45 | Pending |
| T6.5 | API docs site — OpenAPI + guides | P1 | 35 | Pending |

### Sprint 7 — Phase 6: Growth (Ongoing)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T7.1 | SDK/client libraries | P2 | 50 | Pending |
| T7.2 | Webhook system | P2 | 45 | Pending |
| T7.3 | Dashboard/admin UI | P2 | 70 | Pending |
| T7.4 | Feature flags | P2 | 30 | Pending |

### Completed Plans

| Plan | Title | Tasks |
|------|-------|-------|
| plan-2026-03-launch-readiness | Launch Readiness | 5/5 Done |

## What Was Just Done

- **T3.5 done** (auto-updated by hook)

- **T3.4 done** (auto-updated by hook)

- **T3.1 done** (auto-updated by hook)

### Session: 2026-03-04 — T3.5: Sentry error tracking

- Created `sentry.py`: `setup_sentry` (init with DSN/env/traces) + `set_request_id_tag`
- Added `sentry_dsn` and `sentry_traces_sample_rate` to Settings config
- Added `sentry-sdk[fastapi]>=2.0` to dependencies
- Sentry initializes on app startup, no-op when DSN is not set
- Request IDs automatically tagged via middleware for log correlation
- Extracted `check_db_health` to `database.py` to fix router import count
- 8 new tests in test_sentry.py, 274 total passing, 100% coverage, 0 arch errors

### Session: 2026-03-04 — T3.4: Prometheus metrics + health checks

- Created `metrics.py`: Prometheus instrumentation via `prometheus-fastapi-instrumentator`
- Added `GET /metrics` endpoint (Prometheus scraping, auto HTTP latency/error tracking)
- Added `GET /ready` readiness probe (checks DB connectivity, returns degraded if unavailable)
- Extracted auth endpoints to `auth_routes.py` (APIRouter) to fix router.py arch violations
- Added `prometheus-fastapi-instrumentator>=7.0` to dependencies
- 7 new tests in test_metrics.py, 266 total passing, 100% coverage, 0 arch errors

### Session: 2026-03-04 — T3.1: HTTPS / TLS enforcement

- Created `HstsMiddleware` in middleware.py — adds `Strict-Transport-Security` header in production
- Created `HttpsRedirectMiddleware` in middleware.py — redirects HTTP→HTTPS in production (307)
- Both middlewares use dynamic `prod_check` callback (testable, respects runtime config)
- Created `Caddyfile` — reverse proxy with TLS termination + security headers
- Created `docker-compose.prod.yml` — adds Caddy service, sets `ENVIRONMENT=production`
- Dev mode unaffected — no HSTS, no redirect on HTTP
- 6 new tests in test_tls.py, 259 total passing, 100% coverage

- **T3.2 done** (auto-updated by hook)

### Session: 2026-03-04 — T3.2: JWT auth replacing API key

- Created `auth.py`: `create_access_token`, `decode_token`, `InvalidTokenError` using python-jose
- Added `jwt_secret`, `jwt_algorithm`, `jwt_expiry_minutes` to Settings config
- Replaced `verify_api_key` with `verify_auth` — supports JWT Bearer + legacy API key fallback
- Added `POST /auth/token` endpoint (issue JWT from username/password)
- Added `POST /auth/refresh` endpoint (refresh valid JWT)
- Added `python-jose[cryptography]>=3.3` and `passlib[bcrypt]>=1.7` to dependencies
- 20 new tests (test_auth.py + test_auth_endpoints.py), 253 total passing, 100% coverage

- **T3.3 done** (auto-updated by hook)

- **T3.3 done**

### Session: 2026-03-04 — T3.3: Database + migrations

- Added `sqlalchemy[asyncio]>=2.0`, `aiosqlite>=0.20`, `alembic>=1.13` to dependencies
- Created `database.py`: async engine factory + session factory
- Created `models_db.py`: AssessmentRecord + AuditLog ORM models (SQLAlchemy 2.0 declarative)
- Created `repository.py`: AssessmentRepository (save/get/list) + AuditRepository (log_action)
- Initialized Alembic with initial migration (assessment_records + audit_logs tables)
- Added PostgreSQL service to docker-compose.yml with health checks
- Wired database into router lifespan (auto-creates tables on startup)
- `/assess` endpoint now persists results to database (graceful fallback when no DB)
- Added `database_url` to Settings (default: SQLite for local dev)
- 232 tests, 100% coverage, 0 arch violations

- **T2.5 done** (auto-updated by hook)

### Session: 2026-03-03 — T2.5: README

- Created README.md with: Quick Start, Local Development, API Reference (full request/response example), Score Bands, Environment Variables, Testing, Architecture, License placeholder

- **T2.2 done** (auto-updated by hook)

### Session: 2026-03-03 — T2.2: CI/CD pipeline

- Created `.github/workflows/ci.yml`: lint (ruff), test (coverage 100%), build (Docker)
- Created `.github/workflows/docker-publish.yml`: build + push to ghcr.io on version tags
- Added `ruff>=0.4` and `coverage>=7.0` to dev dependencies
- Both workflow YAML files validated

- **T2.1 done** (auto-updated by hook)

### Session: 2026-03-03 — T2.1: Dockerfile + docker-compose

- Created multi-stage `Dockerfile` (builder → test → production), non-root user, Python 3.13-slim
- Created `docker-compose.yml` with health check, volume mount, env vars
- Created `.dockerignore` excluding dev files
- Created `src/main.py` entry point
- Docker not available in WSL2 — build verification deferred to CI
- 220 tests pass, 100% coverage

- **T2.3 done** (auto-updated by hook)

### Session: 2026-03-03 — T2.3: Structured logging

- Added `structlog>=24.0` to pyproject.toml
- Created `logging_config.py` with JSON (prod) / console (dev) renderers
- Created `middleware.py` with RequestIdMiddleware (X-Request-ID header + structlog context)
- Updated router.py to add middleware and configure logging
- 7 new tests in test_logging.py, 220 total passing, 100% coverage

- **T2.4 done** (auto-updated by hook)

### Session: 2026-03-03 — T2.4: .env management

- Added `pydantic-settings>=2.0` to pyproject.toml
- Created `Settings` class in config.py with typed fields (api_key, cors_origins, environment, log_level, host, port)
- Kept backward-compatible standalone functions (get_api_key, get_cors_origins, etc.)
- Created `.env.example` with all env vars documented
- Added .env, .env.local, .env.production to .gitignore
- 17 new tests in test_config.py, 213 total passing, 100% coverage

### Session: 2026-03-03 — Created SaaS Readiness Plan

- Created plan `plan-2026-03-plan-saas-readiness` with 30 tasks across 6 sprints
- Sprint 2 (Phase 1: Deployable): 5 tasks, 140 complexity points
- Sprint 3 (Phase 2: Secure & Observable): 5 tasks, 225 complexity points
- Sprint 4 (Phase 3: Multi-Tenant SaaS): 6 tasks, 305 complexity points
- Sprint 5 (Phase 4: Production Operations): 5 tasks, 185 complexity points
- Sprint 6 (Phase 5: Compliance & Documentation): 5 tasks, 205 complexity points
- Sprint 7 (Phase 6: Growth): 4 tasks, 195 complexity points
- Total: 30 tasks, 1,255 complexity points
- Created SaaS readiness plan: 30 tasks across 6 sprints (S2-S7)


## What's Next

Sprint 3 complete (all 5 tasks done). Next: Sprint 4 (Multi-Tenant SaaS).


## Blockers

None currently.

## Quick Commands

```bash
# Check status
bpsai-pair status

# List tasks
bpsai-pair task list --plan plan-2026-03-plan-saas-readiness

# Start working on a task
bpsai-pair task update T2.1 --status in_progress

# Complete a task
bpsai-pair task update T2.1 --status done
```
