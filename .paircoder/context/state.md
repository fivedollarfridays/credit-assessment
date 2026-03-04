# Current State

> Last updated: 2026-03-04

## Active Plan

**Plan:** plan-2026-03-plan-saas-readiness
**Status:** Planned
**Current Sprint:** 5

## Current Focus

Production operations: load testing, blue/green deploys, alerting, backup/DR, and runbooks.

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
| T4.1 | User management — signup, login, reset | P0 | 60 | ✓ Done |
| T4.2 | RBAC — roles with scoped API keys | P0 | 55 | ✓ Done |
| T4.3 | Per-customer rate limiting | P1 | 40 | ✓ Done |
| T4.4 | Billing integration — Stripe | P1 | 70 | ✓ Done |
| T4.5 | Tenant isolation — org-scoped data | P0 | 50 | ✓ Done |
| T4.6 | API versioning — /v1/ prefix | P1 | 30 | ✓ Done |

### Sprint 5 — Phase 4: Production Operations (Weeks 9-10)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T5.1 | Load testing — Locust/K6 scripts | P1 | 35 | ✓ Done |
| T5.2 | Blue/green deploys | P0 | 50 | ✓ Done |
| T5.3 | Alerting — PagerDuty/Opsgenie | P1 | 35 | ✓ Done |
| T5.4 | Backup and disaster recovery | P0 | 45 | ✓ Done |
| T5.5 | Runbooks — incident response | P2 | 20 | ✓ Done |

### Sprint 6 — Phase 5: Compliance & Documentation (Weeks 11-12)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T6.1 | FCRA Section 505 disclosures | P0 | 40 | ✓ Done |
| T6.2 | Privacy policy + Terms of Service | P1 | 30 | ✓ Done |
| T6.3 | GDPR/CCPA data handling | P0 | 55 | ✓ Done |
| T6.4 | Audit trail — log assessments | P0 | 45 | ✓ Done |
| T6.5 | API docs site — OpenAPI + guides | P1 | 35 | ✓ Done |

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

### Session: 2026-03-04 — Code review fixes (all findings)

- **Security**: Added admin auth (`require_role(Role.ADMIN)`) to audit-log endpoint, added `Depends(verify_auth)` to all 3 data-rights endpoints
- **Bounded stores**: Changed `_audit_entries` from `list` to `deque(maxlen=100_000)`
- **PII hashing**: Upgraded `hash_pii` from unsalted SHA-256 to HMAC-SHA256 with pepper
- **Shared utility**: Extracted `purge_by_age()` to `retention.py`, used by both `audit.py` and `data_rights.py`
- **Stringly-typed fields**: Changed 3 types.py fields to use proper enums (`ScoreBand`, `ConfidenceLevel`, `EligibilityStatus`)
- **Other**: Singleton assessment service, f-string date interpolation in legal.py, `set -euo pipefail` in `_common.sh`
- **Test cleanup**: Consolidated per-method lazy imports to top-level in `test_audit_trail.py` (41→10 imports) and `test_data_rights.py` (38→10 imports)
- **Shared test fixtures**: Added `VALID_ASSESS_PAYLOAD` and `client` fixture to conftest.py
- 576 tests, 100% coverage, 0 arch errors

- **T6.5 done** (auto-updated by hook)

- **T6.5 done** (auto-updated by hook)

### Session: 2026-03-04 — T6.5: API docs site — OpenAPI + guides

- Created `api_docs.py`: API_DESCRIPTION and API_TAGS constants for enriched OpenAPI spec, `get_integration_guide()` with auth/endpoints/errors/rate_limiting sections, `get_code_examples()` with Python/JavaScript/curl samples
- Created `docs_routes.py`: APIRouter with `GET /docs/guide` and `GET /docs/examples` (no auth required)
- Enriched FastAPI app: version "1.0.0", full description, tag metadata for all endpoint groups
- Extracted `assess_routes.py`: moved verify_auth, get_assessment_service, and assessment endpoints out of router.py to fix import count violation (23→19 imports, 222→120 lines)
- Updated test patches in test_security.py and test_auth_endpoints.py to cover assess_routes.settings
- 19 new tests in test_api_docs.py, 570 total passing, 100% coverage, 0 arch errors
- **Sprint 6 complete!** All 5 tasks done.

- **T6.4 done** (auto-updated by hook)

- **T6.3 done** (auto-updated by hook)

- **T6.2 done** (auto-updated by hook)

- **T6.1 done** (auto-updated by hook)

- **T6.4 done** (auto-updated by hook)

### Session: 2026-03-04 — T6.4: Audit trail — log assessments

- Created `audit.py`: `hash_pii()` (SHA-256 one-way hash), `create_audit_entry()` with hashed user_id, `get_audit_trail()` with action/limit filters, `purge_audit_trail()` with FCRA 7-year default retention (2555 days)
- Added `GET /v1/admin/audit-log` endpoint with action and limit query params to admin_routes.py
- Audit entries include: action, user_id_hash (PII hashed), request_summary, result_summary, timestamp, optional org_id
- 22 new tests in test_audit_trail.py, 551 total passing, 100% coverage, 0 arch errors

- **T6.3 done** (auto-updated by hook)

### Session: 2026-03-04 — T6.3: GDPR/CCPA data handling

- Created `data_rights.py`: consent tracking (record/check/withdraw/get), user assessment storage, data export (GDPR Article 15), data deletion with cascade (GDPR Article 17), retention purge by age
- Created `data_rights_routes.py`: `GET /v1/user/data-export`, `DELETE /v1/user/data`, `POST /v1/user/consent`
- Consent is version-specific with timestamp, withdrawal supported
- Deletion cascades to consent records and assessments, returns summary with counts
- Purge function removes assessments older than configurable max_age_days
- 25 new tests in test_data_rights.py, 529 total passing, 100% coverage, 0 arch errors

- **T6.2 done** (auto-updated by hook)

### Session: 2026-03-04 — T6.2: Privacy policy + Terms of Service

- Created `legal.py`: privacy policy (v1.0) covering data collection, use, retention, sharing, security, rights; terms of service (v1.0) covering API usage, liability, termination
- Both documents versioned with version string and effective_date
- In-memory ToS acceptance tracking: `record_tos_acceptance()`, `check_tos_accepted()`, `get_tos_acceptance()`
- Created `legal_routes.py`: APIRouter with `GET /legal/privacy` and `GET /legal/terms` (no auth required)
- Endpoints mounted at root and `/v1` prefix
- 27 new tests in test_legal.py, 504 total passing, 100% coverage, 0 arch errors

- **T6.1 done** (auto-updated by hook)

### Session: 2026-03-04 — T6.1: FCRA Section 505 disclosures

- Created `disclosures.py`: FCRA_DISCLAIMER constant, ADVERSE_ACTION_NOTICE_TEMPLATE with placeholder fields, consumer rights text, data usage notice
- `get_disclosures()` returns structured dict of all disclosure texts
- Updated `CreditAssessmentResult.disclaimer` default to use `FCRA_DISCLAIMER` (replaces old one-liner)
- Added `GET /disclosures` and `GET /v1/disclosures` endpoints (no auth required)
- Adverse action notice template has {consumer_name}, {action_taken}, {reasons}, {date} placeholders
- Updated existing test_result_types.py to match new FCRA disclaimer
- 23 new tests in test_disclosures.py, 477 total passing, 100% coverage, 0 arch errors

- **T5.5 done** (auto-updated by hook)
- **T5.4 done** (auto-updated by hook)
- **T5.3 done** (auto-updated by hook)
- **T5.2 done** (auto-updated by hook)
- **T5.1 done** (auto-updated by hook)

### Session: 2026-03-04 — Sprint 5: Production Operations (T5.1-T5.5)

- **T5.1**: Locust load test scripts for /health and /v1/assess, docker-compose.loadtest.yml, AST-based tests
- **T5.2**: Blue/green deploy utilities (deploy.py), graceful shutdown (SIGTERM), health validation, deploy/rollback scripts
- **T5.3**: AlertRule dataclass, AlertSeverity enum, Prometheus alerting rules, Alertmanager config with PagerDuty/Slack
- **T5.4**: BackupConfig/RetentionPolicy dataclasses, retention logic, backup/restore shell scripts
- **T5.5**: Runbooks for service outage, database recovery, deployment rollback, security incident
- T5.1-T5.4 implemented in parallel (4 worktree agents), T5.5 done sequentially
- 454 tests total, 100% coverage, 0 arch errors
- **Sprint 5 complete!** All 5 tasks done.

- **T5.1 done**

### Session: 2026-03-03 — T5.1: Load testing — Locust/K6 scripts

- Created `loadtests/locustfile.py`: `CreditApiUser(HttpUser)` with `health_check` (weight 1) and `assess` (weight 3) tasks
- `health_check` hits `GET /health`, `assess` hits `POST /v1/assess` with sample profile payload and X-API-Key header
- Created `docker-compose.loadtest.yml`: `api` service (app) + `locust` service (locustio/locust image, port 8089)
- Added `locust>=2.0` to dev dependencies in pyproject.toml
- 15 tests in test_loadtest.py using AST-based verification (avoids gevent monkey-patching conflicts with asyncio suite)
- 389 total passing, 100% coverage, 0 arch errors

- **T5.3 done**

### Session: 2026-03-03 — T5.3: Alerting — PagerDuty/Opsgenie

- Created `alerting.py`: `AlertSeverity` enum (CRITICAL/WARNING/INFO), `AlertRule` dataclass, 3 default rules (high_error_rate, high_latency_p95, health_check_failure)
- `get_alert_rules()` returns copy of default rules, `check_error_rate()` and `check_latency()` for threshold evaluation
- Created `alerting/prometheus_rules.yml`: HighErrorRate (>5%, 2m), HighLatencyP95 (>500ms, 5m), HealthCheckFailure (up==0, 1m) with runbook annotations
- Created `alerting/alertmanager.yml`: route critical to PagerDuty, warnings to Slack, default webhook receiver
- Escalation policies: critical alerts route to PagerDuty, warning alerts route to Slack channel
- 27 new tests in test_alerting.py, 401 total passing, 100% coverage, 0 arch errors

- **T5.4 done**

### Session: 2026-03-03 — T5.4: Backup and disaster recovery

- Created `backup.py`: `RetentionPolicy` (daily=7, weekly=4, monthly=12), `BackupConfig` (validates database_url), `get_backup_filename()` (UTC timestamp), `should_retain()` (tiered retention logic)
- Created `scripts/backup.sh`: automated `pg_dump | gzip` backup with cron-ready header
- Created `scripts/restore.sh`: `gunzip | psql` restore with file-existence check
- Both scripts are executable and document RTO/RPO < 1 hour
- 22 new tests in test_backup.py, 396 total passing, 100% coverage on backup.py, 0 arch errors

- **T4.6 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.6: API versioning — /v1/ prefix

- Created `/v1` versioned router wrapping auth, user, admin, and assess endpoints
- `POST /v1/assess` is the primary versioned endpoint
- Legacy `POST /assess` still works but marked `deprecated=True`
- `DeprecationMiddleware` adds `Deprecation`, `Sunset`, and `Link` headers on legacy `/assess`
- `/health`, `/ready`, `/metrics` remain at root (unversioned)
- OpenAPI spec reflects `/v1/` paths
- 11 tests in test_versioning.py, 374 total, 100% coverage, 0 arch errors
- **Sprint 4 complete!** All 6 tasks done.

- **T4.5 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.5: Tenant isolation — org-scoped data

- Created `tenant.py`: `Organization` dataclass, `resolve_org_id()`, `ScopedAssessmentRepository`
- In-memory `_org_assessments` store with `store_org_assessment()`/`get_org_assessments()`
- Admin-only `get_all_assessments()` for cross-org queries
- `resolve_org_id()` allows admin org override, non-admins locked to their org
- User registration now auto-assigns `org_id` derived from email prefix
- `ScopedAssessmentRepository` requires non-null `org_id` (raises ValueError)
- 12 tests in test_tenant.py, 363 total, 100% coverage, 0 arch errors

- **T4.4 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.4: Billing integration — Stripe

- Created `billing.py`: `BillingPlan` enum (FREE/STARTER/PRO/ENTERPRISE) with pricing
- `create_checkout_session()`: Stripe Checkout for subscription signup
- `record_usage()`: metered billing per /assess call with graceful error handling
- `handle_webhook()`: processes checkout.session.completed, subscription.updated/deleted
- `create_portal_session()`: self-service billing portal
- In-memory `_subscriptions` store with `update_subscription()`/`get_subscription()`
- Added `stripe_secret_key` and `stripe_webhook_secret` to Settings
- 24 tests in test_billing.py, 351 total, 100% coverage, 0 arch errors

- **T4.3 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.3: Per-customer rate limiting

- Created `RateTier` enum (FREE, STARTER, PRO, ENTERPRISE) with per-tier limits in `rate_limit.py`
- Added `resolve_tier()` for looking up tier rate limit strings
- Added `create_limiter()` with optional Redis backend and graceful in-memory fallback
- Added `RateLimitHeaderMiddleware` injecting X-RateLimit-Limit/Remaining/Reset headers on `/assess`
- 429 responses now include `Retry-After` header
- Added `redis_url` to Settings config
- 20 tests in test_rate_limiting.py, 327 total, 100% coverage, 0 arch errors

- **T4.2 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.2: RBAC — roles with scoped API keys

- Created `roles.py`: `Role` enum (ADMIN, ANALYST, VIEWER) + `require_role()` FastAPI dependency
- Created `admin_routes.py`: `GET /admin/users` and `POST /admin/api-keys` (admin-only endpoints)
- Created `rate_limit.py`: extracted rate limiter + handler from router.py (fixed import count)
- User registration now assigns default `viewer` role
- 10 tests in test_rbac.py (enum, enforcement, API keys, error branches), 304 total, 100% coverage, 0 arch errors

- **T4.1 done** (auto-updated by hook)

- **T3.5 done** (auto-updated by hook)

- **T3.4 done** (auto-updated by hook)

- **T3.1 done** (auto-updated by hook)

### Session: 2026-03-04 — T4.1: User management

- Created `User` ORM model in models_db.py (email, password_hash, is_active)
- Created `password.py`: bcrypt hash/verify using `bcrypt` directly (passlib incompatible with bcrypt 4.x)
- Created `user_routes.py`: register, login, reset-password, confirm-reset endpoints
- Added `email-validator>=2.0` to dependencies
- Created `observability.py` to consolidate metrics + sentry setup (fixed router import count)
- 20 new tests (test_user_model.py + test_user_endpoints.py), 294 total, 100% coverage, 0 arch errors

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

Sprint 6 complete! All compliance & documentation tasks done (T6.1-T6.5). Next: Sprint 7 — Growth (T7.1-T7.4: SDK/client libraries, webhook system, dashboard/admin UI, feature flags).


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
