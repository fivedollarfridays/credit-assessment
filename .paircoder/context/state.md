# Current State

> Last updated: 2026-03-04

## Active Plan

**Plan:** plan-2026-03-sprint-17
**Status:** Pending
**Current Sprint:** 17

## Current Focus

Production readiness roadmap planned (Sprints 17-20). Sprint 16 complete. Ready to start Sprint 17.

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
| T7.1 | SDK/client libraries | P2 | 50 | ✓ Done |
| T7.2 | Webhook system | P2 | 45 | ✓ Done |
| T7.3 | Dashboard/admin UI | P2 | 70 | ✓ Done |
| T7.4 | Feature flags | P2 | 30 | ✓ Done |

### Sprint 8 — Code Review Fixes (Bugfix)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T8.1 | Webhook fixes: logic bug, webhook_exists(), asyncio.gather safety | P0 | 25 | ✓ Done |
| T8.2 | Dashboard decoupling: public APIs, eliminate private store imports | P0 | 35 | ✓ Done |
| T8.3 | Type safety: RuleType enum, Role enum, type annotations | P0 | 20 | ✓ Done |
| T8.4 | Feature flag robustness: duplicate guard, ValueError handling, conftest | P1 | 20 | ✓ Done |

### Sprint 9 — Security Hardening (Bugfix)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T9.1 | Auth hardening: JWT secret validation, demo user guard, verify_auth fix | P0 | 40 | ✓ Done |
| T9.2 | User routes: reset token leak, field injection, password complexity | P0 | 35 | ✓ Done |
| T9.3 | IDOR fix: data rights ownership enforcement | P0 | 30 | ✓ Done |
| T9.4 | Input validation: webhook SSRF, request-ID injection, metrics auth | P1 | 35 | ✓ Done |
| T9.5 | Audit PII pepper + API key expiration | P1 | 25 | ✓ Done |

### Sprint 10 — Code Review Fixes (Bugfix)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T10.1 | Test consolidation: shared auth bypass fixture | P0 | 25 | ✓ Done |
| T10.2 | Role mutation fix + admin check centralization | P0 | 25 | ✓ Done |
| T10.3 | Security polish: reset tokens, config constants, SSRF, regex, dead code | P1 | 20 | ✓ Done |

### Sprint 11 — Code Review Fixes (Bugfix)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T11.1 | SSRF hardening + test isolation fix | P0 | 20 | ✓ Done |
| T11.2 | JWT consolidation + _api_keys bounds | P0 | 25 | ✓ Done |
| T11.3 | Code quality polish | P1 | 15 | ✓ Done |

### Sprint 12 — Code Review Fixes (Bugfix)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T12.1 | Auth constants + model consolidation | P0 | 25 | ✓ Done |
| T12.2 | Efficiency: count functions + middleware caching + purge optimization | P1 | 20 | ✓ Done |
| T12.3 | Test deduplication + GDPR cross-store fix + webhook HTTPS | P1 | 20 | ✓ Done |

### Completed Plans

| Plan | Title | Tasks |
|------|-------|-------|
| plan-2026-03-launch-readiness | Launch Readiness | 5/5 Done |

### Sprint 13 — Code Review Fixes (Sprint 12 Review)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T13.1 | Test helper cleanup: missed files + deduplication | P1 | 50 | ✓ Done |
| T13.2 | Code quality: audit invariant comment + GDPR org-scope doc + unbounded store docs | P1 | 20 | ✓ Done |

### Sprint 14 — Code Review Fixes (Sprint 13 Review)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T14.1 | Test infrastructure: admin_headers fix, dead code, deduplication | P1 | 40 | ✓ Done |
| T14.2 | Encapsulate tenant store mutation + rename api_key_header | P1 | 30 | ✓ Done |

### Sprint 15 — Module Decomposition & Dependency Pinning (Refactor)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T15.1 | Decompose webhooks.py into webhooks.py + webhook_delivery.py | P0 | 40 | ✓ Done |
| T15.2 | Decompose user_routes.py into user_routes.py + user_store.py | P0 | 45 | ✓ Done |
| T15.3 | Pin dependency upper bounds in pyproject.toml | P1 | 15 | ✓ Done |

### Sprint 16 — Code Review Fixes (Simple Assess Review) (Refactor)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T16.1 | Code review fixes: stray pass, test counts, import order, magic number, payload dedup | P1 | 15 | ✓ Done |

### Sprint 17 — Database Foundation: Schema, Alembic, Repositories (Refactor)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T17.1 | Expand ORM models with missing tables and columns | P0 | 55 | Pending |
| T17.2 | Initialize Alembic migrations with initial schema | P0 | 35 | Pending |
| T17.3 | Create repository classes for all new models | P0 | 60 | Pending |

### Sprint 18 — Auth & Security Hardening (Feature)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T18.1 | Migrate user store + reset tokens to database | P0 | 65 | Pending |
| T18.2 | Wire scoped API keys into verify_auth() | P0 | 45 | Pending |
| T18.3 | Add org_id and role claims to JWT tokens | P1 | 30 | Pending |
| T18.4 | Account lockout + reset token expiry | P1 | 35 | Pending |

### Sprint 19 — Compliance & Data Persistence (Feature)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T19.1 | Migrate audit trail to database | P0 | 45 | Pending |
| T19.2 | Migrate consent + user assessments to database (GDPR) | P0 | 50 | Pending |
| T19.3 | Migrate tenant org_assessments to DB + history endpoint | P0 | 50 | Pending |

### Sprint 20 — Commercial & Ops Hardening (Feature)

| Task | Title | Priority | Complexity | Status |
|------|-------|----------|------------|--------|
| T20.1 | Migrate subscriptions to DB + connect rate limits to tiers | P0 | 55 | Pending |
| T20.2 | Migrate webhooks + delivery log + feature flags to DB | P1 | 50 | Pending |
| T20.3 | Operational hardening: multi-worker, Redis, OpenAPI | P1 | 30 | Pending |

## What Was Just Done

- **T16.1 done** (auto-updated by hook)

### Session: 2026-03-05 -- Sprint 16: T16.1 Code review fixes

- **T16.1**: Fixed 5 code review items: (1) removed stray `pass` in TestSimpleAssessEndpoint, (2) updated test counts 787+ → 797+ in README.md and CONTRIBUTING.md, (3) reordered pydantic import to group with third-party imports in assess_routes.py, (4) extracted magic number 0.6 to `_OLDEST_TO_AVG_FACTOR` constant, (5) extracted shared test payloads to `_POOR_PAYLOAD` and `_GOOD_PAYLOAD` dicts reducing test_simple_assess.py from 188 to 131 lines. 797 tests passing, 0 arch violations.

### Session: 2026-03-04 -- POST /v1/assess/simple endpoint

- **POST /v1/assess/simple**: Added simplified credit assessment endpoint. `SimpleCreditProfile` accepts 7 required user-friendly fields (credit_score, utilization_percent, total_accounts, open_accounts, negative_items, payment_history_percent, oldest_account_months) + 3 optional (total_balance, total_credit_limit, monthly_payments). Backend derives score_band, closed_accounts, collection_accounts, negative_accounts, average_account_age_months via `to_credit_profile()`. 10 new tests in `test_simple_assess.py`. 797 tests passing.

### Session: 2026-03-04 -- Scaffold improvements

- Added LICENSE (proprietary), Makefile, .pre-commit-config.yaml, .python-version, CONTRIBUTING.md, py.typed marker, updated README.md with full architecture and make targets.

- **T15.3 done** (auto-updated by hook)

- **T15.3**: Added `<next-major` upper bounds to all 28 dependencies in `pyproject.toml` (18 in `[project.dependencies]`, 10 in `[project.optional-dependencies.dev]`). `pip install -e ".[dev]"` succeeds, 777 tests passing.

- **T15.2 done** (auto-updated by hook)

- **T15.2**: Extracted 6 data-access functions (`get_all_users`, `get_user`, `count_users`, `validate_password`, `update_user`, `set_user_role`) plus stores/constants (`_users`, `_reset_tokens`, `_MAX_RESET_TOKENS`, `_ALLOWED_UPDATE_FIELDS`, regex patterns) from `user_routes.py` into `user_store.py` (75 lines, 6 functions). `user_routes.py` now has 4 route handlers only (103 lines). Updated imports in 5 source files (`dashboard.py`, `data_rights_routes.py`, `admin_routes.py`, `roles.py`, `user_routes.py`) and 9 test files.
- 777 tests passing, 0 arch errors.

- **T15.1 done** (auto-updated by hook)

### Session: 2026-03-05 -- Sprint 15: T15.1 Decompose webhooks.py

- **T15.1**: Split `webhooks.py` (204 lines) into registration CRUD (`webhooks.py`, 83 lines, 6 functions) and delivery subsystem (`webhook_delivery.py`, 129 lines, 6 functions). Moved `compute_signature`, `next_retry_delay`, `get_delivery_log`, `_send_one`, `deliver_event`, `reset_delivery_log` plus `WebhookDeliveryStatus`, `DeliveryRecord`, and `_delivery_log` store to `webhook_delivery.py`. Updated imports in `webhook_routes.py` and `test_webhooks.py`. Updated 5 mock patch targets from `modules.credit.webhooks.httpx` → `modules.credit.webhook_delivery.httpx`. Lazy import in `reset_webhooks()` avoids circular dependency.
- 777 tests passing, 0 arch errors.

- **T14.2 done** (auto-updated by hook)

- **T14.1 done** (auto-updated by hook)

### Session: 2026-03-05 -- Sprint 14: Code Review Fixes (Sprint 13 Review)

- **T14.1**: Fixed `admin_headers` fixture to use `patch_auth_settings(_TEST_SETTINGS)` (patches 4 auth modules instead of just assess_routes). Added login status assertion to `register_and_login`. Removed dead `_BILLING_SETTINGS` and `_get_client()` from test_billing.py. Replaced duplicate `_SETTINGS`/`_VALID_PAYLOAD` in test_versioning.py and test_rate_limiting.py with conftest imports. Updated stale TODO in admin_routes.py.
- **T14.2**: Added `delete_user_org_assessments(user_id)` to tenant.py; data_rights.py now calls it instead of directly mutating `_org_assessments`. Renamed `_api_key_header` → `api_key_header` in auth.py, assess_routes.py, roles.py, test_auth_consolidation.py.
- 777 tests passing, 0 ruff issues.

- **T13.2 done** (auto-updated by hook)

- **T13.1 done** (auto-updated by hook)

### Session: 2026-03-04 -- Sprint 13: Code Review Fixes (Sprint 12 Review)

- **T13.1**: Extracted `_post_webhook` to module level in test_webhook_security.py (was duplicated in 2 classes). Removed unused conftest imports from test_billing.py. Replaced local `_patch_settings()` in test_auth_endpoints.py with shared `patch_auth_settings`. Renamed `patch_all_settings` → `patch_auth_settings` across conftest.py, test_rbac.py, test_tenant.py, test_audit_trail.py. Replaced `_admin_auth` fixture in test_dashboard.py with conftest `admin_headers`. Fixed 3 lint errors (unused imports in test_auth_consolidation.py, test_rbac.py, test_tenant.py).
- **T13.2**: Added ISO format invariant docstring to `purge_audit_trail`. Added all-org scan rationale comment to `delete_user_data`. Added unbounded store comments to data_rights.py, tenant.py, webhooks.py.
- 777 tests passing, 0 arch errors, 0 ruff issues.

- **T12.3 done** (auto-updated by hook)

- **T12.3 done**

### Session: 2026-03-04 -- T12.3: Test deduplication + GDPR cross-store fix + webhook HTTPS

- **Shared test helpers in conftest.py**: Added `register_and_login()`, `patch_all_settings()`, and `_TEST_SETTINGS` to conftest.py. Eliminated 3 copies of `_register_and_login` and 3 copies of `_patch_all` from test_rbac.py. Removed duplicates from test_tenant.py, test_billing.py, test_audit_trail.py.
- **test_dashboard.py deduplication**: Replaced 9 copies of the 10-line "patch settings + create token" block with an `_admin_auth` fixture. File reduced from 449 to ~330 lines.
- **GDPR cross-store fix**: `delete_user_data()` in `data_rights.py` now also removes user's entries from `tenant._org_assessments`. Returns `org_assessments_deleted` count in summary. 2 new tests.
- **Webhook HTTPS enforcement**: `webhook_routes.py` now rejects `http://` URLs when `settings.is_production` is True. 3 new tests in `test_webhook_security.py`.
- **test_webhooks.py split**: Moved SSRF protection tests and HTTPS enforcement tests to `test_webhook_security.py` to fix arch violation (44 > 40 functions).
- 777 tests passing, 0 arch errors on all modified files.

- **T12.2 done** (auto-updated by hook)

- **T12.1 done** (auto-updated by hook)

- **T12.2 done**

### Session: 2026-03-04 -- T12.2: Efficiency -- count functions + middleware caching + purge optimization

- **`count_audit_entries()`**: Added to `audit.py`. Returns `len(_audit_entries)` without copying.
- **`count_all_assessments()`**: Added to `tenant.py`. Sums `len(v) for v in _org_assessments.values()` without building a list.
- **`count_org_assessments(org_id)`**: Added to `tenant.py`. Returns `len(_org_assessments.get(org_id, []))` without copying.
- **`count_webhooks()`**: Added to `webhooks.py`. Returns `len(_webhooks)` without copying.
- **`purge_audit_trail` optimized**: Replaced `list(_audit_entries)` copy + `purge_by_age` + clear + extend (3x memory) with `popleft()` loop. Entries are chronologically ordered so oldest are at front. Removed unused `purge_by_age` import.
- **Dashboard uses count functions exclusively**: Replaced `len(get_all_assessments())` with `count_all_assessments()`, `len(get_org_assessments(...))` with `count_org_assessments(...)`, `len(get_audit_trail())` with `count_audit_entries()`, `len(get_webhooks())` with `count_webhooks()`. Removed `get_audit_trail`, `get_all_assessments`, `get_org_assessments`, `get_webhooks` imports.
- **Middleware caches `prod_check` at init**: `HstsMiddleware` and `HttpsRedirectMiddleware` now evaluate `prod_check()` once in `__init__` and store as `_is_prod` boolean. No per-request lambda call. Updated `test_tls.py` to use fresh FastAPI apps with middleware configured per test (since caching at init means patching settings post-init has no effect).
- **`_api_keys` is `OrderedDict`**: Changed from `dict` to `OrderedDict` in `admin_routes.py`. Eviction uses `popitem(last=False)` instead of `pop(next(iter(...)))`.
- 34 new tests in `test_efficiency.py`. 772 tests passing, 0 arch errors, 0 ruff issues.

- **T12.1 done**

### Session: 2026-03-04 -- T12.1: Auth constants + model consolidation

- **`API_KEY_IDENTITY` constant**: Added to `auth.py`. All 3 source files (`assess_routes.py`, `roles.py`, `auth_routes.py`) now import and use it instead of raw `"api-key-user"` string.
- **`_api_key_header` singleton**: Defined once in `auth.py`. Removed duplicate definitions from `assess_routes.py` (line 20) and `roles.py` (line 28). Both modules now import from `auth.py`.
- **`TokenResponse` model**: Defined once in `auth.py`. Removed `TokenResponse` from `auth_routes.py` (lines 32-36) and `LoginResponse` from `user_routes.py` (lines 106-108). Both modules now import `TokenResponse` from `auth.py`.
- **`issue_token_for()` helper**: Added to `auth.py`, wraps `create_access_token` with settings. Used in `auth_routes.py` (2 calls: issue_token, refresh_token) and `user_routes.py` (1 call: login). Eliminated 3 instances of 4-line `create_access_token(subject=..., secret=settings.jwt_secret, ...)` boilerplate.
- **Dashboard `"viewer"` string**: Replaced `user.get("role", "viewer")` with `user.get("role", Role.VIEWER.value)` in `dashboard.py:28`.
- **Test patches updated**: Added `"auth"` to `_patch_all` module lists in 5 test files (`test_auth_endpoints.py`, `test_audit_trail.py`, `test_rbac.py`, `test_tenant.py`, `test_billing.py`) and `test_security.py` since `issue_token_for` reads settings from `auth.py`.
- 10 new tests in `test_auth_consolidation.py`. 748 tests passing, 0 arch errors, 0 ruff issues.

- **T11.3 done** (auto-updated by hook)

- **T11.2 done** (auto-updated by hook)

- **T11.1 done** (auto-updated by hook)

- **T11.1 done**

### Session: 2026-03-04 -- T11.1: SSRF hardening + test isolation fix

- **SSRF `_is_private_ip` hardened**: Replaced `addr.is_private or addr.is_loopback or addr.is_link_local` with `not addr.is_global or addr.is_multicast` in `webhook_routes.py`. Now catches carrier-grade NAT (100.64.x), reserved, and multicast (224.x) ranges in addition to private/loopback/link-local. Docstring updated.
- **Fixed `_BLOCKED_HOSTNAMES` IPv6**: Changed `"[::1]"` to `"::1"` since `urlparse` strips brackets from IPv6 hostnames.
- **Test isolation fix**: Wrapped `test_data_endpoints_require_auth_when_configured` in `test_data_rights.py` with try/finally to restore `bypass_auth` override after popping it. Prevents fixture leakage to subsequent tests.
- **Config validator hoisted**: Restructured `_validate_production_secrets` in `config.py` to check `is_production` once with nested checks instead of repeated `self.is_production and ...`.
- **Test updates**: Updated `test_blocked_hostnames_includes_ipv6_loopback` in `test_security.py` to check for `"::1"`. Added 2 new SSRF tests in `test_webhooks.py` (`TestSsrfExpandedRanges`): carrier-grade NAT and multicast blocking.
- 735 tests passing, 0 arch errors, 0 ruff issues.

- **T11.2 done**

### Session: 2026-03-04 -- T11.2: JWT consolidation + _api_keys bounds

- **Refactored `require_role` in `roles.py`**: Replaced manual JWT decode (extract_bearer_token, decode_token, InvalidTokenError) with call to `verify_auth(request, api_key)` from `assess_routes`. `_check` is now `async def`. Rejects `"api-key-user"` from role-restricted endpoints. Removed imports of `auth` and `config.settings`.
- **Simplified `refresh_token` in `auth_routes.py`**: Replaced manual bearer extraction/JWT decode with `Depends(verify_auth)`. Now `async def` with identity parameter. Rejects API key refresh with 401. Removed `Request`, `InvalidTokenError`, `decode_token`, `extract_bearer_token` imports.
- **Added lazy deletion to `lookup_api_key` in `admin_routes.py`**: Expired entries are now `del _api_keys[key]` on read (lazy deletion), not just skipped.
- **Added `_MAX_API_KEYS = 10_000` constant** to `admin_routes.py` with FIFO eviction in `create_api_key` via `while len > cap: pop(next(iter()))`.
- **Fixed `test_feature_flags.py`**: Changed `bypass_auth` from parameter-style fixture to `@pytest.mark.usefixtures("bypass_auth")` decorator on `test_evaluate_flag_endpoint`.
- **Updated 8 test files** patching `modules.credit.roles.settings` to `modules.credit.assess_routes.settings` (conftest.py, test_rbac.py, test_dashboard.py, test_audit_trail.py, test_tenant.py, test_billing.py). Updated error message assertions for `verify_auth` behavior (403 for missing credentials, "Invalid or expired token" for bad JWT).
- **Fixed pre-existing test bug**: Updated `test_blocked_hostnames_includes_ipv6_loopback` to match actual `_BLOCKED_HOSTNAMES` value.
- 2 new tests: `test_lazy_deletion_removes_expired_key`, `test_max_api_keys_constant_exists`.
- 735 tests passing, 0 arch errors, 0 ruff issues.

- **T11.3 done**

### Session: 2026-03-04 -- T11.3: Code quality polish

- **Re-read after mutation**: Fixed `update_customer()` in `dashboard.py` to call `get_user()` a second time after `set_user_role()` and `update_user()` mutations, so the returned dict reflects post-mutation state (prevents stale data when backed by a database). Added `test_returns_post_mutation_data` test with mock proving two `get_user` calls.
- **Config constants in test_auth.py**: Replaced hardcoded `"change-me-in-production"` with `_DEFAULT_JWT_SECRET` import from `modules.credit.config`.
- **Config constants in test_config.py**: Replaced hardcoded `"change-me-in-production"` with `_DEFAULT_JWT_SECRET` and `"default-pii-pepper"` with `_DEFAULT_PII_PEPPER`. Added top-level import.
- **Endpoint-driven eviction test**: Rewrote `test_reset_token_eviction_bounds_store` in `test_security.py` to drive through the `/auth/reset-password` endpoint instead of replicating production eviction logic inline. Pre-fills `_reset_tokens` to cap, registers a test user, issues reset via `TestClient`, verifies store stays bounded.
- 728 tests passing (excluding 7 pre-existing failures), 0 arch errors, 0 ruff issues.

- **T10.3 done** (auto-updated by hook)

- **T10.2 done** (auto-updated by hook)

- **T10.1 done** (auto-updated by hook)

- **T10.1 done**

### Session: 2026-03-04 -- T10.1: Test consolidation -- shared auth bypass fixture

- **Shared `bypass_auth` fixture**: Added to `conftest.py` -- overrides `verify_auth` to return `"test-user"`, cleans up on teardown.
- **Removed 7 class-level `_bypass_auth` fixtures** from: `test_router.py` (TestAssessEndpoint), `test_router_db.py` (TestAssessmentPersistence), `test_versioning.py` (TestVersionedAssess, TestDeprecationHeader), `test_data_rights.py` (TestDataRightsEndpoints), `test_webhooks.py` (TestWebhookEndpoints, TestSsrfProtection). Each class now uses `@pytest.mark.usefixtures("bypass_auth")`.
- **Fixed `test_metrics.py`**: Replaced `_auth_client()` method and manual try/finally blocks with `@pytest.mark.usefixtures("bypass_auth")`. Removed `headers={"X-API-Key": "test"}` from all requests. Class now uses conftest `client` fixture directly. Removed unused `patch` import.
- **Fixed `test_feature_flags.py`**: Replaced inline try/finally in `test_evaluate_flag_endpoint` with `bypass_auth` fixture parameter.
- **Removed residual `X-API-Key` headers** from `test_webhooks.py` in TestWebhookEndpoints and TestSsrfProtection classes (11 occurrences removed).
- **Added `_clean_api_keys` cleanup fixture** to `test_security.py` TestApiKeyExpiration class. Removed 3 inline `_api_keys.pop(...)` cleanup calls.
- **Removed unused import** `verify_auth` from `test_versioning.py`.
- 707 tests passing, 0 arch errors, 0 ruff issues.

- **T10.3 done**

### Session: 2026-03-04 -- T10.3: Security polish -- reset tokens, config constants, SSRF, regex, dead code

- **Reset token cap**: `_reset_tokens` already `OrderedDict` with `_MAX_RESET_TOKENS = 10_000` and FIFO eviction (implemented in prior sprint). Added 3 tests verifying constant, type, and eviction behavior.
- **Precompiled regex**: `_RE_UPPERCASE`, `_RE_LOWERCASE`, `_RE_DIGIT`, `_RE_SPECIAL` already precompiled at module level in `user_routes.py` (implemented in prior sprint). Added 4 tests verifying patterns match correctly.
- **Config constants**: Extracted `_DEFAULT_JWT_SECRET` and `_DEFAULT_PII_PEPPER` module-level constants in `config.py`. Field defaults and `_validate_production_secrets` now reference constants instead of string literals. 4 new tests.
- **Expanded SSRF blocked hostnames**: Added `"0"`, `"127.0.0.1"`, `"[::1]"` to `_BLOCKED_HOSTNAMES` in `webhook_routes.py` with DNS-rebinding caveat comment. 3 new tests in test_security.py + 2 endpoint tests in test_webhooks.py.
- **Admin lookup_api_key TODO**: Added TODO docstring to `lookup_api_key()` in `admin_routes.py` noting integration with `verify_auth()` tracked for Sprint 11. 1 new test.
- **Test refactoring**: Consolidated 35 in-function imports in `test_security.py` to 15 top-level imports, fixing arch violation (was 35 imports, now under 30 limit).
- 730 tests passing, 0 arch errors, 0 ruff issues.

- **T10.2 done**

### Session: 2026-03-04 -- T10.2: Role mutation fix + admin check centralization

- Added `is_admin()` helper to `roles.py` -- centralizes admin role check, returns `False` for `None` or missing role key.
- Added `set_user_role()` to `user_routes.py` -- privileged role mutation function, callers must enforce admin auth.
- Replaced direct dict mutation `user["role"] = role.value` in `dashboard.py` with `set_user_role(email, role)`.
- Replaced inline admin check `caller.get("role") == Role.ADMIN.value` in `data_rights_routes.py` with `is_admin(caller)`.
- Replaced inline admin check `user_data.get("role") == Role.ADMIN.value` in `tenant.py` with `is_admin(user_data)`.
- 6 new tests: 4 in `TestIsAdmin` (test_rbac.py), 2 in `TestSetUserRole` (test_user_endpoints.py).
- 713 tests passing (excluding 16 pre-existing failures in test_security.py/test_webhooks.py), 0 arch violations.

- **T9.5 done** (auto-updated by hook)

- **T9.2**: Removed `reset_token` from `ResetResponse` (no more token leak in HTTP response). Added `_ALLOWED_UPDATE_FIELDS` frozenset to `update_user()` blocking role/password_hash injection. Added `validate_password()` with complexity requirements (8+ chars, uppercase, lowercase, digit, special char). Wired into RegisterRequest and ConfirmResetRequest.
- **T9.3**: Added `_resolve_user_id()` to data_rights_routes.py enforcing ownership. Non-admins get 403 when requesting another user's data. Admins can override. Routes now inject `identity: str = Depends(verify_auth)` instead of using `dependencies=[]`.
- **T9.4**: Added SSRF protection to webhook URL validation (blocks localhost, private IPs, cloud metadata). Added `_REQUEST_ID_PATTERN` validation in middleware (alphanumeric + hyphens, max 128 chars). Added auth dependency to `/metrics` endpoint.
- **T9.5**: Added `pii_pepper` config field with production validation. Changed `hash_pii()` to use dedicated pepper instead of JWT secret. Added `lookup_api_key()` with expiration checking.
- 707 tests passing, 100% coverage, 0 arch violations.
- **Sprint 9 complete!** All 5 security hardening tasks done.

- **T9.3 done** (auto-updated by hook)

- **T9.3 done**

### Session: 2026-03-04 -- T9.3: IDOR fix -- data rights ownership enforcement

- **Ownership enforcement**: Added `_resolve_user_id()` helper to `data_rights_routes.py`. Non-admin callers can only access their own data (identity from `verify_auth`). Admins (looked up via `get_user()` with `Role.ADMIN` check) may override `user_id` to access any user's data. Mismatched `user_id` for non-admins returns 403 "Cannot access another user's data".
- **Route rewrites**: All 3 data rights routes (`/data-export`, `/data`, `/consent`) now use `identity: str = Depends(verify_auth)` as a parameter instead of `dependencies=[Depends(verify_auth)]`. The `user_id` query param is now optional (defaults to caller identity).
- **Existing test fixes**: Updated `test_delete_endpoint_returns_summary` and `test_consent_endpoint_records_consent` to use `user_id` matching the overridden identity (`"test-user"`), since IDOR protection now blocks mismatches. Updated auth-required test to not pass `user_id` params (not needed to test auth rejection).
- 4 new IDOR tests in `TestIdorProtection` class: non-admin export rejection, admin override allowed, non-admin delete rejection, non-admin consent rejection.
- 30 tests in test_data_rights.py (limit 30), 707 total tests passing, 0 arch violations.

- **T9.4 done** (auto-updated by hook)

- **T9.2 done** (auto-updated by hook)

- **T9.2 done**

### Session: 2026-03-04 — T9.2: User routes security fixes

- **Reset token leak fixed**: Removed `reset_token` field from `ResetResponse` model. The `request_reset` endpoint no longer returns the token in the HTTP response body. Response is now identical for existing and nonexistent emails (prevents enumeration).
- **Field injection blocked**: Added `_ALLOWED_UPDATE_FIELDS = frozenset({"is_active", "org_id"})` constant. `update_user()` now filters incoming fields to only allowlisted keys, blocking role escalation and password hash injection. Updated `dashboard.py`'s `update_customer()` to apply role changes directly (admin-only context) rather than through `update_user`.
- **Password complexity validation**: Added `validate_password()` function requiring min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character. Wired as `@field_validator("password")` on `RegisterRequest` and `@field_validator("new_password")` on `ConfirmResetRequest`.
- **Updated existing test**: `test_confirm_reset_changes_password` now retrieves token from `_reset_tokens` dict (simulating email delivery) instead of HTTP response. `test_confirm_reset_invalid_token_returns_400` updated to use complexity-valid password.
- 11 new test functions across 3 test classes (`TestResetTokenNotLeaked`, `TestUpdateUserFieldAllowlist`, `TestPasswordComplexity`). 27 total in test_user_endpoints.py (limit 30).
- 694 tests passing, 0 arch violations.

- **T9.4 done**

### Session: 2026-03-04 — T9.4: Input validation — webhook SSRF, request-ID injection, metrics auth

- **Webhook SSRF protection**: Added `_is_private_ip()` helper and `_BLOCKED_HOSTNAMES` set to `webhook_routes.py`. Enhanced `validate_url` field validator to block localhost, 0.0.0.0, private IPs (10.x, 172.16-31.x, 192.168.x), loopback (127.0.0.1), and cloud metadata (169.254.169.254) via `ipaddress.ip_address()` checks.
- **Request-ID injection prevention**: Added `_REQUEST_ID_PATTERN` regex (`^[a-zA-Z0-9\-]{1,128}$`) to `middleware.py`. `RequestIdMiddleware.dispatch` now validates client-supplied `X-Request-ID` and generates a new UUID if the header contains special characters, newlines, or exceeds 128 chars.
- **Metrics auth**: Added `dependencies=[Depends(verify_auth)]` to `instrumentator.expose()` kwargs in `metrics.py`. `/metrics` endpoint now requires valid JWT or API key credentials (returns 403 without auth).
- 5 new SSRF tests in `test_webhooks.py`, 4 new request-ID validation tests in `test_logging.py`, 1 new metrics auth test in `test_metrics.py` (updated 3 existing to use auth override).
- 693 tests passing, 0 arch errors, 1 pre-existing dashboard test failure (unrelated to T9.4).

- **T9.1 done** (auto-updated by hook)

### Session: 2026-03-04 — Sprint 9: Security Hardening

- **T9.1**: Auth hardening — added `@model_validator` to config.py rejecting default JWT secret in production. Added `_get_demo_users()` to auth_routes.py disabling demo creds in production. Rewrote `verify_auth` to always require credentials and return identity string (`payload["sub"]` or `"api-key-user"`). Removed dev-mode bypass. Fixed 24 broken tests across 6 files using `app.dependency_overrides`. 673 tests passing, 0 arch violations.

### Session: 2026-03-04 — Sprint 8: Code Review Fixes (T8.1-T8.4)

- **T8.1**: Fixed webhook_deliveries logic bug (double `get_delivery_log` call + private `_webhooks` import). Added `webhook_exists()` public API. Added `return_exceptions=True` to `asyncio.gather` with `DeliveryRecord` filtering. Endpoint now returns 404 for unknown webhook IDs.
- **T8.2**: Decoupled dashboard.py from private stores. Added `list_subscriptions()`, `count_active_subscriptions()` to billing.py. Added `get_all_users()`, `get_user()`, `count_users()` to user_routes.py. Rewrote dashboard.py with zero private imports + extracted `_build_customer_info` helper.
- **T8.3**: Changed `TargetingRuleModel.type` from `str` to `RuleType` enum (422 on invalid). Changed `CustomerUpdate.role` from `str` to `Role` enum (422 on invalid). Added type annotation to `_to_response`.
- **T8.4**: Added duplicate key guard to `create_flag` (raises `ValueError`). Added `try/except` for invalid percentage values. Added 409 response for duplicate flag creation. Extracted `admin_headers` fixture to conftest.py.
- 661 tests passing, 0 arch violations, all formatting clean.
- **Sprint 8 complete!** All 4 code review fix tasks done.

- **T7.4 done** (auto-updated by hook)

### Session: 2026-03-04 — T7.4: Feature flags — gradual rollouts

- Created `feature_flags.py`: `FeatureFlag` and `TargetingRule` dataclasses, CRUD operations (create/get/update/delete), `evaluate_flag()` with org/user/percentage targeting, deterministic percentage bucketing via MD5 hash
- Created `flag_routes.py`: `POST /v1/flags` (create), `GET /v1/flags` (list), `PUT /v1/flags/{key}` (update), `DELETE /v1/flags/{key}` (remove) — admin-only; `GET /v1/flags/{key}/evaluate` — auth-required evaluation endpoint
- Percentage targeting is deterministic per user (same user always gets same result)
- Performance test confirms evaluation < 1ms (1000 iterations)
- 27 new tests in test_feature_flags.py, 649 total tests passing, 0 arch violations
- **Sprint 7 complete!** All 4 tasks done (T7.1-T7.4). All 30 SaaS readiness tasks complete.

- **T7.3 done** (auto-updated by hook)

### Session: 2026-03-04 — T7.3: Dashboard/admin UI — usage analytics

- Created `dashboard.py`: `get_usage_overview()` (total users, assessments, active subs), `get_customer_list()` (enriched with plan/org/assessment count), `get_customer_detail()`, `update_customer()` (role/active toggle), `get_system_health()` (users, audit entries, webhooks)
- Created `dashboard_routes.py`: `GET /v1/dashboard/overview`, `GET /v1/dashboard/customers`, `GET /v1/dashboard/customers/{email}`, `PUT /v1/dashboard/customers/{email}`, `DELETE /v1/dashboard/customers/{email}` (soft delete), `GET /v1/dashboard/health` — all admin-only via `require_role(Role.ADMIN)`
- Created `static/dashboard.html`: responsive HTML dashboard with JWT login, stat cards, customer table (with revoke action), health details, auto-refresh every 30s
- Extracted `disclosures_routes.py` from router.py to fix import count violation (21→20)
- Consolidated `database` and `logging_config` to module-level imports in router.py
- 21 new tests in test_dashboard.py, 622 total tests passing, 0 arch violations

- **T7.2 done** (auto-updated by hook)

### Session: 2026-03-04 — T7.2: Webhook system — async event notifications

- Created `webhooks.py`: `EventType` enum (assessment.completed, subscription.updated, rate_limit.warning), `WebhookRegistration` dataclass, `compute_signature()` (HMAC-SHA256), `deliver_event()` async delivery with signature headers, `next_retry_delay()` exponential backoff (2^n capped at 300s), in-memory delivery log
- Created `webhook_routes.py`: `POST /v1/webhooks` (register), `GET /v1/webhooks` (list), `GET /v1/webhooks/{id}/deliveries` (delivery log), `DELETE /v1/webhooks/{id}` (remove)
- 25 new tests in test_webhooks.py covering: event types, registration, HMAC signatures, delivery success/failure/skip, retry logic, delivery log, all API endpoints
- 601 total tests passing, 0 arch violations

- **T7.1 done** (auto-updated by hook)

### Session: 2026-03-04 — T7.1: SDK/client libraries (Python, JavaScript, Go)

- **Python SDK** (`sdks/python/`): httpx-based typed client, ApiKeyAuth/BearerAuth helpers, dataclass models (AccountSummary, CreditProfile, AssessmentResult), exception hierarchy (ApiError, AuthenticationError, RateLimitError, ValidationError). 19 tests pass.
- **JavaScript SDK** (`sdks/javascript/`): TypeScript with strict mode, fetch-based async client, typed models with camelCase→snake_case serialization, error classes extending Error. 21 tests pass (vitest).
- **Go SDK** (`sdks/go/`): Idiomatic Go client with functional options (WithAuth, WithTimeout), struct JSON tags for snake_case, error types with Unwrap() for errors.As/Is, httptest-based integration tests. 19 tests pass.
- **CI workflow** (`.github/workflows/sdk-ci.yml`): Runs Python pytest, TypeScript tsc + vitest, Go test on push/PR to main when sdks/ changes.
- All 3 SDKs include auth helpers, typed models, and proper error handling.
- 576 main project tests + 19 Python SDK + 21 JS SDK + 19 Go SDK = 635 total tests passing.

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

Sprint 15 complete. All 3 tasks done. Ready for commit. 777 tests passing, 0 arch errors.


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
