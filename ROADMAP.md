# Roadmap

## Completed

### Phase 1: Core Platform (Sprints 1-5)

- [x] Credit assessment engine with FICO-weighted scoring
- [x] Barrier analysis, product eligibility, threshold estimates
- [x] Dispute pathway generator with FCRA/FDCPA legal citations
- [x] FastAPI router with versioned API (`/v1/`)
- [x] Docker + docker-compose
- [x] GitHub Actions CI/CD (lint, test, coverage, Docker build)
- [x] Structured logging with request IDs
- [x] Environment-based configuration (pydantic-settings)

### Phase 2: Security & Multi-Tenant (Sprints 3-4, 9-11, 14, 18)

- [x] JWT authentication (replacing API-key-only auth)
- [x] RBAC: admin, analyst, viewer roles
- [x] Scoped API keys (per-org, per-user, with expiration)
- [x] Account lockout after failed login attempts
- [x] SSRF protection on webhook URLs
- [x] IDOR enforcement on all data-access endpoints
- [x] Request-ID validation (injection prevention)
- [x] Production secret validation (JWT_SECRET, PII_PEPPER)
- [x] Multi-tenant org isolation with row-level scoping
- [x] Password complexity enforcement (bcrypt)

### Phase 3: Compliance & Billing (Sprints 4, 6)

- [x] FCRA Section 605 disclosures
- [x] GDPR/CCPA: consent tracking, data export, atomic deletion
- [x] Compliance audit trail (database-backed)
- [x] Privacy policy and Terms of Service endpoints
- [x] Stripe subscription integration
- [x] Tier-based rate limiting (starter/professional/enterprise)

### Phase 4: Growth Features (Sprints 7-8)

- [x] Webhook system with async delivery, retry logic, HMAC signatures
- [x] Admin dashboard (usage analytics, customer management)
- [x] Feature flags (percentage rollout, per-org targeting)

### Phase 5: Database Persistence (Sprints 17, 19-20)

- [x] SQLAlchemy async ORM with full schema
- [x] Repository pattern for all data access
- [x] Audit trail migration from in-memory to database
- [x] User, subscription, webhook, feature flag persistence
- [x] Bounded queries (LIMIT to prevent DoS)

### Phase 6: Advanced Credit Features (Sprints 21-23)

- [x] Structured negative item types (8 categories with typed objects)
- [x] Score simulation engine (10 action handlers using FICO factor weights)
- [x] `POST /v1/simulate` endpoint
- [x] Dispute letter template system (5 letter types with legal citations)
- [x] Letter generation engine (3 bureau addresses, placeholder substitution)
- [x] Dispute lifecycle management (6-state machine with transition validation)
- [x] FCRA deadline tracking (30-day standard, 45-day identity theft)
- [x] Score history tracking with source attribution and trend analysis
- [x] Auto-record scores on each authenticated assessment

## Planned

### Credit Report Parsing (Deferred)

The largest remaining feature -- effectively a separate service.

- [ ] PDF upload endpoint
- [ ] Text extraction from credit report PDFs
- [ ] Tradeline detection and parsing
- [ ] Auto-populate CreditProfile from parsed report
- [ ] Support for Equifax, Experian, TransUnion report formats

**Dependencies:** Requires the core assessment + dispute engine to be complete (done).

### Production Hardening

- [ ] Alembic migration scripts for PostgreSQL deployment
- [ ] Redis-backed rate limiting in production
- [ ] Stripe webhook event processing
- [ ] Email delivery for password resets and dispute notifications
- [ ] Background job queue (Celery or similar) for letter delivery and webhook retries

### API Expansion

- [ ] `GET /v1/disputes/{id}/letters` -- list letters generated for a dispute
- [ ] `POST /v1/disputes/{id}/send` -- mark dispute as sent with tracking info
- [ ] Score history analytics (monthly averages, percentile tracking)
- [ ] Batch assessment endpoint for portfolio analysis
- [ ] SDK packages published to PyPI, npm, Go modules

## Quality Gates

All completed work maintains:

- **100% test coverage** (enforced in CI, `fail_under=100`)
- **1,154+ tests** across 68 test files
- **0 lint violations** (ruff check + format)
- **Architecture constraints** enforced per-file (< 400 LOC source, < 15 functions, < 20 imports)
