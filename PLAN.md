# Plan: Launch Readiness

**Plan ID:** plan-2026-03-launch-readiness
**Type:** chore
**Goal:** Get all 255 tests green with 100% coverage so the credit assessment module is functional.

## Current State

- **152/255 tests pass**, 90 fail, 13 error
- Root cause: `assessment.py` and `dispute_pathway.py` import 4 symbols that don't exist in `types.py`
- Secondary: `AccountSummary` and `CreditProfile` lack validation constraints (16 test failures)
- `slowapi` used in `router.py` but not declared in `pyproject.toml`

## Tasks

### T1.1 — Add missing symbols to `types.py` [P0, complexity: 20]
Add to `types.py`:
- `ConfidenceLevel` enum (`high`, `medium`, `low`)
- `EligibilityStatus` enum (`eligible`, `blocked`)
- `HIGH_UTILIZATION_THRESHOLD = 75`
- `MODERATE_UTILIZATION_THRESHOLD = 50`
- Update `__init__.py` exports

**Impact:** Unblocks ~103 failing tests (all ImportError cascades).

### T1.2 — Add validation constraints to models [P0, complexity: 30]
- `AccountSummary`: Add `Field(ge=0)` to all 8 numeric fields
- `CreditProfile`: Add `Field(ge=0, le=100)` to utilization/payment_history, `Field(ge=0, le=1200)` to account age, `max_length=50` on negative_items list, `max_length=200` on each item string
- Add `@model_validator` to check `score_band` matches `current_score`

**Impact:** Fixes 16 failing validation tests. **Depends on T1.1.**

### T1.3 — Add `slowapi` to `pyproject.toml` [P1, complexity: 5]
Add `"slowapi>=0.1.9"` to `[project] dependencies`.

**Impact:** Ensures fresh installs work. **Independent of T1.1/T1.2.**

### T1.4 — Get all tests green + 100% coverage [P0, complexity: 30]
Run full suite, fix any remaining failures, ensure coverage meets `fail_under = 100`.

**Depends on T1.1, T1.2, T1.3.**

### T1.5 — Commit all files [P1, complexity: 10]
Stage and commit all source, test, and config files.

**Depends on T1.4.**

## Execution Order

```
T1.1 ──→ T1.2 ──→ T1.4 ──→ T1.5
T1.3 ────────────↗
```

T1.1 and T1.3 can run in parallel. T1.2 depends on T1.1. T1.4 depends on all three. T1.5 depends on T1.4.

## Files Modified

| File | Task | Change |
|------|------|--------|
| `src/modules/credit/types.py` | T1.1, T1.2 | Add enums, constants, Field constraints, validator |
| `src/modules/credit/__init__.py` | T1.1 | Add new exports |
| `pyproject.toml` | T1.3 | Add slowapi dependency |

## Risk Assessment

- **Low risk**: All changes are additive — no existing behavior is modified
- **No test changes**: All fixes target source code only; test assertions remain unchanged
- **TDD approach**: Tests already exist and define expected behavior precisely
