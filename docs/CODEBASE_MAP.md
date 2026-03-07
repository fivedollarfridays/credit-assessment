# Codebase Map — Credit Assessment API

> Generated: 2026-03-06 | Source: `src/modules/credit/` (excludes tests)

---

## 1. Module Map

### Core & Application Wiring

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `__init__.py` | 43 | Re-exports all public types from `types.py` | All domain types & constants | `types` |
| `main.py` (src/) | 6 | Uvicorn entry point | `app` | `router` |
| `router.py` | 141 | FastAPI app factory, lifespan, middleware stack, route registration | `app` | 17 route modules, `config`, `database`, `logging_config`, `middleware`, `observability`, `models_db`, `rate_limit`, `api_docs` |
| `config.py` | 78 | Pydantic-settings from env vars | `Settings`, `settings` | - |
| `database.py` | 41 | Async SQLAlchemy engine & session factory | `create_engine`, `get_session_factory`, `get_db` | - |
| `logging_config.py` | 48 | Structlog configuration (JSON/console) | `configure_logging`, `get_logger` | - |
| `middleware.py` | 89 | HSTS, HTTPS redirect, deprecation, request-ID middleware | 4 middleware classes | `sentry` |

### Types & Domain Models

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `types.py` | 333 | All domain enums, Pydantic models, constants | `CreditProfile`, `CreditAssessmentResult`, `NegativeItem`, `ScoreBand`, `ActionType`, `SCORE_BANDS`, `SCORE_WEIGHTS`, `PRODUCT_THRESHOLDS` | `disclosures` |
| `score_models.py` | 13 | Score source enum | `ScoreSource` | - |
| `dispute_models.py` | 31 | Dispute status enum & transition rules | `DisputeStatus`, `VALID_TRANSITIONS` | - |
| `letter_types.py` | 75 | Letter type/bureau enums, template model | `LetterType`, `Bureau`, `BureauAddress`, `LetterTemplate`, `BUREAU_ADDRESSES` | - |
| `disclosures.py` | 86 | FCRA disclaimer, adverse action notice, projection disclaimer | `FCRA_DISCLAIMER`, `ADVERSE_ACTION_NOTICE_TEMPLATE`, `PROJECTION_DISCLAIMER`, `get_disclosures` | - |

### Authentication & Authorization

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `auth.py` | 95 | JWT creation/decoding, auth identity, bearer extraction | `AuthIdentity`, `TokenResponse`, `create_access_token`, `decode_token`, `issue_token_for`, `extract_bearer_token` | `config` |
| `auth_routes.py` | 47 | Token issuance & refresh endpoints | `router` | `assess_routes`, `auth`, `config` |
| `user_routes.py` | 181 | Register, login, password reset flows | `router` | `audit`, `auth`, `config`, `database`, `password`, `repo_users`, `roles`, `user_store` |
| `password.py` | 15 | Bcrypt hash & verify | `hash_password`, `verify_password` | - |
| `user_store.py` | 29 | Password complexity validation | `validate_password` | - |
| `roles.py` | 74 | RBAC enum & `require_role` dependency | `Role`, `require_role`, `is_admin` | `assess_routes`, `auth`, `repo_users` |
| `tenant.py` | 58 | Multi-tenant org scoping | `Organization`, `ScopedAssessmentRepository`, `resolve_org_id` | `repo_assessments`, `roles` |

### Assessment & Scoring

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `assessment.py` | 316 | Core credit assessment engine | `CreditAssessmentService`, `get_score_band`, `get_utilization_impact` | `dispute_pathway`, `types` |
| `assess_routes.py` | 367 | Assessment API endpoints & `verify_auth` dependency | `router`, `verify_auth`, `SimpleCreditProfile` | `assessment`, `auth`, `billing`, `config`, `database`, `rate_limit`, `repo_api_keys`, `repo_assessments`, `repo_scores`, `score_models`, `types` |
| `score_routes.py` | 99 | Score history & manual score endpoints | `router` | `assess_routes`, `auth`, `database`, `rate_limit`, `models_db`, `repo_scores`, `score_models`, `types` |

### Simulation

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `simulation.py` | 194 | Score simulation engine for what-if scenarios | `ScoreSimulator`, `SimulationAction`, `SimulationResult` | `assessment`, `types` |
| `simulate_routes.py` | 63 | Simulation API endpoints | `router` | `assess_routes`, `disclosures`, `rate_limit`, `simulation`, `types` |

### Dispute & Letter Generation

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `dispute_pathway.py` | 187 | Dispute pathway generator with legal theories | `DisputePathwayGenerator`, `ISSUE_PATTERNS` | `types` |
| `dispute_routes.py` | 158 | Dispute CRUD & lifecycle endpoints | `router` | `assess_routes`, `auth`, `database`, `dispute_models`, `letter_types`, `rate_limit`, `models_db`, `repo_disputes` |
| `letter_generator.py` | 112 | Dispute letter generation from templates | `LetterGenerator`, `LetterRequest`, `GeneratedLetter` | `disclosures`, `letter_templates`, `letter_types`, `types` |
| `letter_routes.py` | 51 | Letter generation endpoints (single + batch) | `router` | `assess_routes`, `letter_generator`, `rate_limit` |
| `letter_templates.py` | 400 | 13 letter template variations across 5 types | `TEMPLATES`, `get_template` | `letter_types` |

### Business Features

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `billing.py` | 156 | Stripe billing integration | `create_checkout_session`, `handle_webhook`, `get_subscription`, `record_usage` | `rate_limit`, `repo_billing` |
| `dashboard.py` | 112 | Admin dashboard data aggregation | `get_usage_overview`, `get_customer_list`, `get_customer_detail`, `update_customer`, `get_system_health` | `audit`, `billing`, `repo_users`, `roles`, `tenant`, `webhooks` |
| `dashboard_routes.py` | 86 | Dashboard API & static page serving | `router`, `dashboard_page_router` | `dashboard`, `database`, `roles` |
| `data_rights.py` | 130 | GDPR/CCPA data export, delete, consent | `export_user_data`, `delete_user_data`, `record_consent`, `withdraw_consent` | `repo_data_rights`, `repo_assessments` |
| `data_rights_routes.py` | 100 | Data rights API endpoints | `router` | `assess_routes`, `auth`, `data_rights`, `database`, `repo_users`, `roles` |
| `feature_flags.py` | 170 | Feature flag system with targeting rules | `FeatureFlag`, `TargetingRule`, `RuleType`, `create_flag`, `evaluate_flag` | `repo_flags` |
| `flag_routes.py` | 139 | Feature flag CRUD & evaluation endpoints | `router` | `assess_routes`, `database`, `feature_flags`, `roles` |
| `legal.py` | 156 | Privacy policy, ToS, acceptance tracking | `get_privacy_policy`, `get_terms_of_service`, `record_tos_acceptance` | - |
| `legal_routes.py` | 21 | Legal document endpoints | `router` | `legal` |

### Webhooks

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `webhooks.py` | 114 | Webhook registration CRUD | `WebhookRegistration`, `EventType`, `create_webhook`, `get_webhooks`, `delete_webhook` | `repo_webhooks` |
| `webhook_routes.py` | 140 | Webhook management endpoints with SSRF protection | `router` | `assess_routes`, `auth`, `config`, `database`, `webhook_delivery`, `webhooks` |
| `webhook_delivery.py` | 129 | Webhook dispatch, HMAC signatures, retry logic | `deliver_event`, `compute_signature`, `get_delivery_log` | `repo_webhooks`, `webhooks` |

### Ops & Infrastructure

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `rate_limit.py` | 112 | Rate limiting with SlowAPI + Redis | `limiter`, `SubscriptionTier`, `TIER_LIMITS`, `RateLimitHeaderMiddleware` | `config` (lazy) |
| `metrics.py` | 24 | Prometheus metrics instrumentation | `setup_metrics` | `assess_routes` |
| `observability.py` | 16 | Unified observability setup | `setup_observability` | `metrics`, `sentry` |
| `sentry.py` | 26 | Sentry error tracking setup | `setup_sentry`, `set_request_id_tag` | - |
| `alerting.py` | 79 | Alert rules for error rate & latency | `AlertRule`, `AlertSeverity`, `check_error_rate`, `check_latency` | - |
| `audit.py` | 75 | PII-safe audit trail with HMAC hashing | `create_audit_entry`, `get_audit_trail`, `hash_pii` | `config`, `repository` |
| `backup.py` | 51 | Backup config & retention policies | `BackupConfig`, `RetentionPolicy`, `should_retain` | - |
| `deploy.py` | 52 | Graceful shutdown & health validation | `setup_graceful_shutdown`, `validate_health` | - |
| `retention.py` | 32 | Generic age-based record purging | `purge_by_age` | - |
| `api_docs.py` | 171 | OpenAPI description, tags, integration guide, code examples | `API_DESCRIPTION`, `API_TAGS`, `get_integration_guide`, `get_code_examples` | - |
| `docs_routes.py` | 38 | Developer docs endpoints | `router` | `api_docs`, `roles` |
| `admin_routes.py` | 94 | Admin API: user list, API key management, audit log | `router` | `audit`, `database`, `repo_api_keys`, `roles` |

### Repositories (Data Access Layer)

| File | Lines | Purpose | Key Exports | Dependencies |
|------|-------|---------|-------------|--------------|
| `models_db.py` | 263 | All SQLAlchemy ORM models (14 tables) | `Base`, all DB model classes | - |
| `repository.py` | 92 | Audit log repository | `AuditRepository` | `models_db` |
| `repo_users.py` | 101 | User & reset token repository | `UserRepository`, `ResetTokenRepository` | `models_db` |
| `repo_api_keys.py` | 71 | Scoped API key repository | `ApiKeyRepository` | `models_db` |
| `repo_assessments.py` | 122 | Assessment record repository | `AssessmentRepository` | `models_db` |
| `repo_scores.py` | 88 | Score history repository | `ScoreHistoryRepository` | `models_db` |
| `repo_billing.py` | 53 | Subscription repository | `SubscriptionRepository` | `models_db` |
| `repo_data_rights.py` | 104 | Consent & user assessment repository | `ConsentRepository`, `UserAssessmentRepository` | `models_db` |
| `repo_disputes.py` | 158 | Dispute record repository with transition validation | `DisputeRepository` | `dispute_models`, `letter_types`, `models_db` |
| `repo_flags.py` | 55 | Feature flag repository | `FeatureFlagRepository` | `models_db` |
| `repo_webhooks.py` | 106 | Webhook registration & delivery log repository | `WebhookRepository`, `WebhookDeliveryRepository` | `models_db` |

---

## 2. API Endpoints

### Auth (`/auth`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/auth/token` | No | `TokenRequest{username, password}` | `TokenResponse{access_token, token_type}` | Default |
| POST | `/auth/refresh` | JWT | - | `TokenResponse` | Default |
| POST | `/auth/register` | No | `RegisterRequest{email, password}` | `RegisterResponse{email, message}` | Default |
| POST | `/auth/login` | No | `LoginRequest{email, password}` | `TokenResponse` or 429 lockout | Default |
| POST | `/auth/reset-password` | No | `ResetRequest{email}` | `ResetResponse{message}` | Default |
| POST | `/auth/confirm-reset` | No | `ConfirmResetRequest{token, new_password}` | `{message}` | Default |

### Assessment (`/assess`, `/v1/assess`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/assess` | JWT/API-Key | `CreditProfile` | `CreditAssessmentResult` | Tier-based |
| POST | `/assess/simple` | JWT/API-Key | `SimpleCreditProfile` | `CreditAssessmentResult` | Tier-based |
| GET | `/assessments` | JWT/API-Key | Query: `limit`, `offset` | `{items, total, limit, offset}` | Default |

### Scores (`/v1/scores`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/v1/scores/history` | JWT/API-Key | Query: `limit`, `offset`, `days` | `{entries, total, trend, trend_delta}` | `10/minute` |
| POST | `/v1/scores` | JWT/API-Key | `ManualScoreRequest{score, score_band, notes}` | `{entry, message}` | `10/minute` |

### Simulation (`/v1/simulate`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/v1/simulate` | JWT/API-Key | `SimulationRequest{profile, actions}` | `SimulationResponse` | `10/minute` |
| POST | `/v1/simulate/simple` | JWT/API-Key | `SimpleSimulationRequest{profile, actions}` | `SimulationResponse` | `10/minute` |

### Disputes (`/v1/disputes`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/v1/disputes` | JWT/API-Key | `CreateDisputeRequest{bureau, negative_item_data, letter_type}` | `{dispute}` | `10/minute` |
| GET | `/v1/disputes` | JWT/API-Key | Query: `status`, `limit`, `offset` | `{items, total}` | `30/minute` |
| GET | `/v1/disputes/{id}` | JWT/API-Key | - | `{dispute}` | `30/minute` |
| PATCH | `/v1/disputes/{id}/status` | JWT/API-Key | `StatusUpdateRequest{status, resolution}` | `{dispute}` | `10/minute` |
| GET | `/v1/disputes/deadlines` | JWT/API-Key | Query: `days_ahead` | `{deadlines}` | `30/minute` |

### Letters (`/v1/disputes/letters`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/v1/disputes/letters` | JWT/API-Key | `LetterRequest` | `GeneratedLetter` | `30/minute` |
| POST | `/v1/disputes/letters/batch` | JWT/API-Key | `BatchLetterRequest{requests[]}` | `BatchLetterResponse{letters[]}` | `10/minute` |

### Dashboard (`/dashboard`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/dashboard/overview` | Admin | - | `{total_users, total_assessments, ...}` | Default |
| GET | `/dashboard/customers` | Admin | - | `[customer_info]` | Default |
| GET | `/dashboard/customers/{email}` | Admin | - | `{customer_detail}` | Default |
| PUT | `/dashboard/customers/{email}` | Admin | `CustomerUpdate{role, is_active}` | `{customer}` | Default |
| DELETE | `/dashboard/customers/{email}` | Admin | - | `{customer}` | Default |
| GET | `/dashboard/health` | Admin | - | `{system_health}` | Default |
| GET | `/dashboard` | No | - | Static HTML | Default |

### Admin (`/admin`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/admin/users` | Admin | - | `[user_dict]` | Default |
| POST | `/admin/api-keys` | Admin | `ApiKeyRequest{org_id, role, expires_in_days}` | `ApiKeyResponse{api_key, ...}` | Default |
| GET | `/admin/audit-log` | Admin | Query: `action`, `limit` | `{entries}` | Default |
| DELETE | `/admin/api-keys/{key}` | Admin | - | `{message}` | Default |

### Webhooks (`/webhooks`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/webhooks` | JWT/API-Key | `WebhookCreateRequest{url, events, secret}` | `WebhookResponse` | Default |
| GET | `/webhooks` | JWT/API-Key | - | `[WebhookResponse]` | Default |
| GET | `/webhooks/{id}/deliveries` | JWT/API-Key | - | `{deliveries, total}` | Default |
| DELETE | `/webhooks/{id}` | JWT/API-Key | - | `{message}` | Default |

### Data Rights (`/user`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/user/data-export` | JWT/API-Key | Query: `user_id` | `{export_data}` | Default |
| DELETE | `/user/data` | JWT/API-Key | Query: `user_id` | `{deleted_counts}` | Default |
| POST | `/user/consent` | JWT/API-Key | `ConsentRequest{user_id, consent_version}` | `{message}` | Default |
| DELETE | `/user/consent` | JWT/API-Key | `ConsentRequest{user_id, consent_version}` | `{message}` | Default |

### Feature Flags (`/flags`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| POST | `/flags` | Admin | `FlagCreateRequest{key, description, enabled}` | `FlagResponse` | Default |
| GET | `/flags` | JWT/API-Key | - | `[FlagResponse]` | Default |
| PUT | `/flags/{key}` | Admin | `FlagUpdateRequest{enabled, description, targeting}` | `FlagResponse` | Default |
| DELETE | `/flags/{key}` | Admin | - | `{message}` | Default |
| GET | `/flags/{key}/evaluate` | JWT/API-Key | Query: `org_id`, `user_id` | `{key, enabled}` | Default |

### Legal (`/legal`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/legal/privacy` | No | - | `{version, effective_date, content}` | Default |
| GET | `/legal/terms` | No | - | `{version, effective_date, content}` | Default |

### Docs (`/docs`)

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/docs/guide` | No | - | `{integration_guide}` | Default |
| GET | `/docs/examples` | No | - | `{code_examples}` | Default |
| GET | `/docs/openapi.json` | Admin | - | OpenAPI spec | Default |

### Disclosures

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/disclosures` | No | - | `{fcra, adverse_action, ...}` | Default |

### Health

| Method | Path | Auth | Request Model | Response Model | Rate Limit |
|--------|------|------|---------------|----------------|------------|
| GET | `/health` | No | - | `{status}` | Default |
| GET | `/ready` | No | - | `{status, database, redis}` | Default |

---

## 3. Data Models

### Pydantic Models (Request/Response)

**`CreditProfile`** (`types.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| `current_score` | `int` | 300-850 |
| `score_band` | `ScoreBand` | Must match score range |
| `overall_utilization` | `float` | 0.0-100.0 |
| `account_summary` | `AccountSummary` | - |
| `payment_history_pct` | `float` | 0.0-100.0 |
| `average_account_age_months` | `int` | 0-1200 |
| `negative_items` | `list[NegativeItem]` | Max 50, strings auto-coerced |

**`AccountSummary`** (`types.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| `total_accounts` | `int` | >= 0 |
| `open_accounts` | `int` | >= 0 |
| `closed_accounts` | `int` | >= 0 |
| `negative_accounts` | `int` | >= 0 |
| `collection_accounts` | `int` | >= 0 |
| `total_balance` | `float` | >= 0.0 |
| `total_credit_limit` | `float` | >= 0.0 |
| `monthly_payments` | `float` | >= 0.0 |

**`NegativeItem`** (`types.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| `type` | `NegativeItemType` | Enum |
| `description` | `str` | Max 200 chars |
| `creditor` | `str \| None` | Max 100 chars |
| `amount` | `float \| None` | >= 0.0 |
| `date_reported` | `str \| None` | YYYY-MM-DD, validated |
| `date_of_first_delinquency` | `str \| None` | YYYY-MM-DD, validated |
| `status` | `NegativeItemStatus \| None` | Enum |

**`CreditAssessmentResult`** (`types.py`)
| Field | Type |
|-------|------|
| `barrier_severity` | `BarrierSeverity` |
| `barrier_details` | `list[CreditBarrier]` |
| `readiness` | `CreditReadiness` |
| `thresholds` | `list[ThresholdEstimate]` |
| `dispute_pathway` | `DisputePathway` |
| `eligibility` | `list[EligibilityItem]` |
| `disclaimer` | `str` (FCRA_DISCLAIMER) |

**`SimpleCreditProfile`** (`assess_routes.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| `credit_score` | `int` | 300-850 |
| `utilization_percent` | `float` | 0.0-100.0 |
| `total_accounts` | `int` | >= 0 |
| `open_accounts` | `int` | >= 0, <= total_accounts |
| `negative_items` | `list[str]` | Default [] |
| `payment_history_percent` | `float` | 0.0-100.0 |
| `oldest_account_months` | `int` | 0-1200 |
| `total_balance` | `float` | >= 0.0 |
| `total_credit_limit` | `float` | >= 0.0 |
| `monthly_payments` | `float` | >= 0.0 |

**`SimulationAction`** (`simulation.py`)
| Field | Type |
|-------|------|
| `action_type` | `ActionType` |
| `target_amount` | `float \| None` |
| `target_item` | `str \| NegativeItem \| None` |

**`LetterRequest`** (`letter_generator.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| `negative_item` | `NegativeItem` | - |
| `letter_type` | `LetterType` | Enum |
| `bureau` | `Bureau` | Enum |
| `consumer_name` | `str` | 1-200 chars |
| `consumer_address` | `str \| None` | Max 500 |
| `account_number` | `str \| None` | Max 50 |
| `variation` | `int \| None` | - |

### Enums

| Enum | Module | Values |
|------|--------|--------|
| `ScoreBand` | `types.py` | EXCELLENT, GOOD, FAIR, POOR, VERY_POOR |
| `BarrierSeverity` | `types.py` | HIGH, MEDIUM, LOW |
| `ActionType` | `types.py` | PAY_DOWN_DEBT, DISPUTE_NEGATIVE, BECOME_AUTHORIZED_USER, OPEN_SECURED_CARD, AVOID_NEW_INQUIRIES, KEEP_ACCOUNTS_OPEN, DIVERSIFY_CREDIT_MIX, PAY_ON_TIME, REDUCE_UTILIZATION, REMOVE_COLLECTION |
| `ActionPriority` | `types.py` | CRITICAL, HIGH, MEDIUM, LOW |
| `LegalTheory` | `types.py` | FCRA_607B, FCRA_611, FCRA_605B, FCRA_623, FDCPA_809, FDCPA_807, METRO2_DOFD, METRO2_LOGIC, STATE_LAW |
| `NegativeItemType` | `types.py` | LATE_PAYMENT, CHARGE_OFF, COLLECTION, IDENTITY_THEFT, WRONG_BALANCE, OBSOLETE_ITEM, UNAUTHORIZED_INQUIRY, DOFD_ERROR |
| `NegativeItemStatus` | `types.py` | OPEN, CLOSED, DISPUTED, PAID, SETTLED |
| `ConfidenceLevel` | `types.py` | HIGH, MEDIUM, LOW |
| `EligibilityStatus` | `types.py` | ELIGIBLE, BLOCKED |
| `ScoreSource` | `score_models.py` | ASSESSMENT, MANUAL, EXTERNAL |
| `DisputeStatus` | `dispute_models.py` | DRAFT, SENT, IN_REVIEW, RESPONDED, RESOLVED, ESCALATED |
| `LetterType` | `letter_types.py` | VALIDATION, INACCURACY, COMPLETENESS, OBSOLETE_ITEM, IDENTITY_THEFT |
| `Bureau` | `letter_types.py` | EQUIFAX, EXPERIAN, TRANSUNION |
| `EventType` | `webhooks.py` | ASSESSMENT_COMPLETED, SUBSCRIPTION_UPDATED, RATE_LIMIT_WARNING |
| `Role` | `roles.py` | ADMIN, ANALYST, VIEWER |
| `SubscriptionTier` | `rate_limit.py` | FREE, STARTER, PRO, ENTERPRISE |
| `RuleType` | `feature_flags.py` | ORG, USER, PERCENTAGE |
| `AlertSeverity` | `alerting.py` | CRITICAL, WARNING, INFO |

---

## 4. Service Layer

### `CreditAssessmentService` (`assessment.py`)
| Method | Input | Output |
|--------|-------|--------|
| `assess(profile)` | `CreditProfile` | `CreditAssessmentResult` |
| `_compute_barrier_severity(profile)` | `CreditProfile` | `(BarrierSeverity, list[CreditBarrier])` |
| `_high_barriers(profile)` | `CreditProfile` | `list[CreditBarrier]` |
| `_medium_barriers(profile)` | `CreditProfile` | `list[CreditBarrier]` |
| `_compute_readiness_score(profile)` | `CreditProfile` | `CreditReadiness` |
| `_estimate_days_to_thresholds(profile)` | `CreditProfile` | `list[ThresholdEstimate]` |
| `_compute_eligibility(profile)` | `CreditProfile` | `list[EligibilityItem]` |
| `_build_dispute_pathway(profile)` | `CreditProfile` | `DisputePathway` |

### `ScoreSimulator` (`simulation.py`)
| Method | Input | Output |
|--------|-------|--------|
| `simulate(profile, actions)` | `CreditProfile`, `list[SimulationAction]` | `SimulationResult` |
| `_apply_action(action, state, profile)` | Action + working state | Mutates state |
| `_handle_pay_down_debt(...)` | Action + state + profile | Mutates state |
| `_handle_reduce_utilization(...)` | Action + state + profile | Mutates state |
| `_handle_remove_collection(...)` | Action + state + profile | Mutates state |
| `_handle_dispute_negative(...)` | Action + state + profile | Mutates state |
| `_handle_pay_on_time(...)` | Action + state + profile | Mutates state |

### `DisputePathwayGenerator` (`dispute_pathway.py`)
| Method | Input | Output |
|--------|-------|--------|
| `generate(profile)` | `CreditProfile` | `DisputePathway` |
| `_build_item_steps(profile)` | `CreditProfile` | `list[(DisputeStep, IssuePattern)]` |
| `_build_profile_steps(profile)` | `CreditProfile` | `list[(DisputeStep, IssuePattern)]` |

### `LetterGenerator` (`letter_generator.py`)
| Method | Input | Output |
|--------|-------|--------|
| `generate(request)` | `LetterRequest` | `GeneratedLetter` |
| `generate_batch(requests)` | `list[LetterRequest]` | `list[GeneratedLetter]` |

---

## 5. Database

### SQLAlchemy Tables (`models_db.py`)

**`assessment_records`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `credit_score` | Integer | NOT NULL |
| `score_band` | String(20) | NOT NULL |
| `barrier_severity` | String(10) | NOT NULL |
| `readiness_score` | Integer | NOT NULL |
| `request_payload` | JSON | NOT NULL |
| `response_payload` | JSON | NOT NULL |
| `user_id` | String(255) | Nullable |
| `org_id` | String(100) | Nullable |
| `created_at` | DateTime | server_default=now() |

**`users`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `email` | String(255) | UNIQUE, NOT NULL |
| `password_hash` | String(255) | NOT NULL |
| `role` | String(20) | default="viewer" |
| `org_id` | String(100) | default="" |
| `is_active` | Boolean | default=True |
| `failed_login_attempts` | Integer | default=0 |
| `locked_until` | DateTime(tz) | Nullable |
| `created_at` | DateTime | server_default=now() |

**`audit_logs`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `action` | String(50) | NOT NULL |
| `resource` | String(100) | default="" |
| `detail` | JSON | Nullable |
| `user_id_hash` | String(128) | Nullable |
| `org_id` | String(100) | Nullable |
| `request_summary` | JSON | Nullable |
| `result_summary` | JSON | Nullable |
| `created_at` | DateTime | server_default=now() |

**`subscriptions`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `email` | String(255) | NOT NULL, INDEX |
| `subscription_id` | String(255) | NOT NULL |
| `status` | String(20) | NOT NULL |
| `plan` | String(20) | NOT NULL |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate |

**`consent_records`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `user_id` | String(255) | NOT NULL, INDEX |
| `consent_version` | String(20) | NOT NULL |
| `consented_at` | DateTime | server_default=now() |

**`user_assessments`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `user_id` | String(255) | NOT NULL, INDEX |
| `assessment_data` | JSON | NOT NULL |
| `recorded_at` | DateTime | server_default=now() |

**`reset_tokens`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `token` | String(64) | UNIQUE, NOT NULL |
| `email` | String(255) | NOT NULL |
| `created_at` | DateTime | server_default=now() |

**`webhook_registrations`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK |
| `url` | String(2048) | NOT NULL |
| `events` | JSON (list) | NOT NULL |
| `secret` | String(255) | NOT NULL |
| `owner_id` | String(255) | Nullable |
| `is_active` | Boolean | default=True |
| `created_at` | DateTime | server_default=now() |

**`webhook_deliveries`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `webhook_id` | String(36) | NOT NULL, INDEX |
| `event_type` | String(50) | NOT NULL |
| `status` | String(10) | NOT NULL |
| `status_code` | Integer | Nullable |
| `created_at` | DateTime | server_default=now() |

**`api_keys`**
| Column | Type | Constraints |
|--------|------|-------------|
| `key` | String(64) | PK |
| `org_id` | String(100) | NOT NULL, INDEX |
| `role` | String(20) | NOT NULL |
| `expires_at` | DateTime | Nullable |
| `revoked_at` | DateTime | Nullable |
| `created_at` | DateTime | server_default=now() |

**`feature_flags`**
| Column | Type | Constraints |
|--------|------|-------------|
| `key` | String(100) | PK |
| `description` | String(500) | default="" |
| `enabled` | Boolean | default=False |
| `targeting` | JSON (list) | Nullable |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate |

**`dispute_records`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `user_id` | String(255) | NOT NULL, INDEX |
| `org_id` | String(100) | Nullable |
| `bureau` | String(20) | NOT NULL |
| `negative_item_data` | JSON | NOT NULL |
| `letter_type` | String(30) | Nullable |
| `status` | String(20) | default="draft" |
| `round` | Integer | default=1 |
| `sent_at` | DateTime(tz) | Nullable |
| `deadline_at` | DateTime(tz) | Nullable |
| `responded_at` | DateTime(tz) | Nullable |
| `resolution` | String(500) | Nullable |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate |
| **Index** | `ix_dispute_user_status` | (user_id, status) |
| **Index** | `ix_dispute_deadline` | (deadline_at) |

**`score_history`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `user_id` | String(255) | NOT NULL, INDEX |
| `org_id` | String(100) | Nullable |
| `score` | Integer | NOT NULL |
| `score_band` | String(20) | NOT NULL |
| `source` | String(20) | NOT NULL |
| `assessment_id` | Integer | Nullable |
| `notes` | String(500) | Nullable |
| `recorded_at` | DateTime | server_default=now() |

### Relationships & Foreign Keys

No explicit SQLAlchemy `ForeignKey` or `relationship()` constraints are defined. Tables are linked at the application layer by matching `user_id`, `org_id`, `webhook_id`, and `assessment_id` values.

---

## 6. Architecture Diagram

```
                     Client Request
                          |
                    +-----v------+
                    |   FastAPI   |
                    |   (router)  |
                    +-----+------+
                          |
              +-----------+-----------+
              |     Middleware Stack   |
              |  HttpsRedirect        |
              |  HSTS                 |
              |  RateLimitHeader      |
              |  Deprecation          |
              |  RequestId            |
              |  CORS                 |
              +-----------+-----------+
                          |
                    +-----v------+
                    | Auth Layer |
                    | verify_auth|
                    |  JWT / Key |
                    +-----+------+
                          |
           +--------------+---------------+
           |              |               |
     +-----v---+   +-----v----+   +------v------+
     |  Route   |   |  Route   |   |   Route     |
     | Handlers |   | Handlers |   |  Handlers   |
     | (assess) |   | (dispute)|   | (dashboard) |
     +-----+----+   +-----+---+   +------+------+
           |               |              |
     +-----v----+   +-----v----+   +-----v-----+
     | Service  |   | Service  |   |  Service   |
     | Layer    |   | Layer    |   |  Layer     |
     | Assess-  |   | Dispute  |   | Dashboard  |
     | ment     |   | Pathway  |   | Billing    |
     | Simulate |   | Letters  |   | Audit      |
     +-----+----+   +-----+---+   +-----+------+
           |               |              |
     +-----v----+   +-----v----+   +-----v-----+
     | Repos    |   | Repos    |   |  Repos     |
     | Assess-  |   | Dispute  |   | Users      |
     | ments    |   | Webhooks |   | Billing    |
     | Scores   |   | Flags    |   | DataRights |
     +-----+----+   +-----+---+   +-----+------+
           |               |              |
           +-------+-------+--------------+
                   |
             +-----v------+
             | SQLAlchemy  |
             | AsyncSession|
             +-----+------+
                   |
             +-----v------+
             | SQLite/PG   |
             | (async)     |
             +-------------+
```

### Middleware Execution Order (outermost first)

1. `HttpsRedirectMiddleware` -- redirect HTTP to HTTPS in production
2. `HstsMiddleware` -- add HSTS header in production
3. `RateLimitHeaderMiddleware` -- add rate limit headers
4. `DeprecationMiddleware` -- mark legacy endpoints
5. `RequestIdMiddleware` -- assign/propagate X-Request-ID
6. `CORSMiddleware` -- handle CORS preflight

### API Versioning

- `/v1/*` -- versioned routes (all features)
- `/*` -- legacy unversioned routes (subset, `/assess` deprecated with Sunset header)

---

## 7. Intelligence Capabilities

### Credit Assessment Scoring (`assessment.py`)

- **Readiness score** (0-100): Weighted composite of payment history (35%), utilization (30%), credit age (15%), credit mix (10%), new credit (10%) -- mirrors FICO factor weights
- **Barrier detection**: Identifies HIGH barriers (collections, charge-offs, score < 580, utilization > 75%) and MEDIUM barriers (late payments, utilization > 50%, thin file < 3 accounts, short history < 24 months)
- **Score band classification**: Maps FICO scores to EXCELLENT (750-850), GOOD (700-749), FAIR (650-699), POOR (600-649), VERY_POOR (300-599)
- **Threshold estimation**: Projects days to reach product thresholds (FHA Mortgage 580, Conventional 620, Prime Auto 700, etc.) using _POINTS_PER_DAY = 0.2
- **Product eligibility**: Evaluates eligibility for 8 credit products with blocking factor analysis

### Dispute Pathway Generation (`dispute_pathway.py`)

- **8 issue patterns** with mapped legal theories, statutes, and estimated resolution days:
  - Late payment: FCRA 611, 30 days
  - Charge-off: FCRA 607(b) + 611, 45 days
  - Collection: FDCPA 809 + FCRA 611, 45 days
  - Identity theft: FCRA 605(b), 45 days
  - Wrong balance: FCRA 607(b), 30 days
  - Obsolete item: FCRA 605(a), 30 days
  - Unauthorized inquiry: FCRA 611, 30 days
  - DOFD error: Metro-2 DOFD violation, 30 days
- **Priority-based ordering**: CRITICAL > HIGH > MEDIUM > LOW
- **Legal theory mapping**: FCRA, FDCPA, Metro-2, State law citations

### Letter Generation (`letter_generator.py`, `letter_templates.py`)

- **5 letter types**: Validation, Inaccuracy, Completeness, Obsolete Item, Identity Theft
- **13 template variations** total (2-3 per type)
- **3 bureau addresses**: Equifax (Atlanta), Experian (Allen TX), TransUnion (Chester PA)
- **Auto-variation** for batch generation to avoid identical letters
- **Legal citations** embedded per template
- **FCRA disclaimer** auto-appended

### Score Simulation (`simulation.py`)

- **10 action types** with impact modeling:
  - Pay down debt: utilization-based impact calculation
  - Reduce utilization: bracket-based scoring (0-9%, 10-29%, 30-49%, 50-74%, 75%+)
  - Remove collection: 25-45 point impact
  - Dispute negative: 10-25 points
  - Pay on time: 5-15 points + payment history % increment
  - Become authorized user: 10-30 points
  - Open secured card: 5-15 points
  - Keep accounts open: 3-10 points
  - Avoid new inquiries: 5-10 points
  - Diversify credit mix: 5-15 points
- **Min/max/expected** three-point estimate for all projections
- **Working state model** that tracks mutations across chained actions

### Score History (`score_routes.py`, `repo_scores.py`)

- **Trend computation**: Compares latest score to previous entries, reports "up", "down", or "stable" with delta
- **Multi-source tracking**: Assessment-generated, manual entry, external import
- **Time-windowed queries**: Configurable lookback (1-365 days)

### Dispute Lifecycle (`dispute_models.py`, `dispute_routes.py`, `repo_disputes.py`)

- **6 statuses**: DRAFT -> SENT -> IN_REVIEW -> RESPONDED -> RESOLVED/ESCALATED
- **State machine**: Validated transitions prevent illegal state changes
- **FCRA deadline tracking**: 30 days standard, 45 days for identity theft
- **Deadline alerts**: Query disputes approaching FCRA deadlines

### Feature Flags (`feature_flags.py`)

- **3 targeting rule types**: org-based, user-based, percentage-based (hash-based consistent bucketing)
- **Full CRUD** with admin-only write access
- **Evaluation endpoint** for runtime flag checks

---

## 8. Integration Points

### Stripe (`billing.py`)

- `stripe.checkout.Session.create()` -- create checkout sessions
- `stripe.billing.MeterEvent.create()` -- usage-based metering
- `stripe.billing_portal.Session.create()` -- customer portal
- `stripe.Webhook.construct_event()` -- webhook signature verification
- Events handled: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

### Sentry (`sentry.py`)

- `sentry_sdk.init()` -- error tracking with configurable DSN, environment, trace sample rate
- `sentry_sdk.set_tag("request_id", ...)` -- request correlation

### Redis (`rate_limit.py`)

- Used as backing store for SlowAPI rate limiter
- `redis.Redis(url).ping()` -- health check
- Optional: falls back to in-memory limiting when Redis unavailable

### Webhooks (`webhook_delivery.py`)

- HMAC-SHA256 signed payloads
- Async delivery via `httpx.AsyncClient`
- Exponential backoff retry (2^n seconds, max 300s)
- Delivery logging to `webhook_deliveries` table
- SSRF protection: blocks localhost, private IPs, requires HTTPS in production

### Prometheus (`metrics.py`)

- `prometheus_fastapi_instrumentator` -- automatic HTTP metrics instrumentation

### Structlog (`logging_config.py`)

- JSON output in production, console in development
- Request-ID bound to context vars

---

## 9. Gaps & Enhancement Opportunities

### Missing / Scaffolded

1. **No Alembic migration files** -- tables created via `Base.metadata.create_all` (fine for SQLite, problematic for production PostgreSQL)
2. **No foreign key constraints** -- all table relationships are application-level only; no DB-enforced referential integrity
3. **ToS acceptance** (`legal.py`) uses **in-memory dict** (`_tos_acceptances`) -- lost on restart; should use DB
4. **No email delivery** -- password reset generates tokens but never sends emails; `request_reset` returns 200 silently
5. **Webhook retry** -- `next_retry_delay()` is defined but **no actual retry loop** is implemented; delivery is fire-once
6. **No background task scheduler** -- expired token pruning, data retention purging, and backup execution have functions but no scheduled invocation
7. **Dashboard static file** (`static/`) directory referenced but may not contain actual HTML

### Incomplete

8. **`_OLDEST_TO_AVG_FACTOR`** defined in `assess_routes.py` but only used in `SimpleCreditProfile.to_credit_profile()` -- coupling between route layer and domain logic
9. **`BillingPlan`** re-exported as alias of `SubscriptionTier` -- legacy coupling that could be cleaned up
10. **`assess_routes.py` at 367 lines** -- close to the 400-line architecture limit; `verify_auth` is imported by many modules, creating a dependency hub

### Enhancement Opportunities

11. **Async webhook retry queue** -- replace fire-once with persistent job queue (e.g., Celery, arq, or DB-backed)
12. **Real email integration** -- SendGrid/SES for password reset and dispute notifications
13. **Pagination standardization** -- some endpoints return `{items, total}`, others return `{entries, total}`; unify response shape
14. **Score history foreign key** -- `assessment_id` in `score_history` is not a FK; could link to `assessment_records`
15. **Rate limit per-endpoint** -- currently tier-based globally; some endpoints have `@limiter.limit()` decorators but not all
16. **API key rotation** -- keys can be created and revoked but not rotated (create new + grace period)
17. **Dispute document attachments** -- no file upload support for supporting documents
18. **Multi-bureau dispute tracking** -- disputes are per-bureau; no unified cross-bureau dispute view

---

## 10. Stats

### Summary

| Metric | Value |
|--------|-------|
| Total source files | 64 |
| Total lines of code | 6,873 |
| Average lines per file | 107 |
| Largest file | `letter_templates.py` (400 lines) |
| SQLAlchemy tables | 14 |
| API endpoints | ~45 |
| Pydantic models | ~25 |
| Repository classes | 11 |
| Service classes | 4 |
| Enums | 18 |

### Lines Per Module Group

| Group | Files | Lines | % |
|-------|-------|-------|---|
| Types & Domain Models | 5 | 538 | 7.8% |
| Auth & Users | 7 | 499 | 7.3% |
| Assessment & Scoring | 6 | 1,003 | 14.6% |
| Simulation | 2 | 257 | 3.7% |
| Dispute & Letters | 6 | 1,065 | 15.5% |
| Business Features | 12 | 1,321 | 19.2% |
| Webhooks | 3 | 383 | 5.6% |
| Ops & Infrastructure | 12 | 823 | 12.0% |
| Repositories | 10 | 941 | 13.7% |
| Core & Wiring | 4 | 276 | 4.0% |

*Note: router.py counted under Core; models_db.py counted under Repositories.*

### Top 10 Largest Files

| File | Lines |
|------|-------|
| `letter_templates.py` | 400 |
| `assess_routes.py` | 367 |
| `types.py` | 333 |
| `assessment.py` | 316 |
| `models_db.py` | 263 |
| `simulation.py` | 194 |
| `dispute_pathway.py` | 187 |
| `user_routes.py` | 181 |
| `api_docs.py` | 171 |
| `feature_flags.py` | 170 |
