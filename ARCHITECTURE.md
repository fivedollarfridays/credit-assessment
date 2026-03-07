# Baby INERTIA Architecture

## Why Deterministic?

> "Deterministic AI with causal grounding achieves 12x higher success rates, 3x faster resolution, and 50% lower cost vs. LLM-only approaches."
> -- Dynatrace Perform 2026

Baby INERTIA uses zero AI/LLM API calls. Every agent is pure Python with deterministic logic, research-backed lookup tables, and validated legal citations. This is not a limitation -- it is a design decision.

### The Problem with LLM-Based Credit Advice

1. **Hallucination risk** -- LLMs fabricate legal citations and statute numbers
2. **Non-reproducibility** -- Same input produces different outputs across runs
3. **Cost** -- API calls add per-request cost that scales with usage
4. **Latency** -- Network round-trips add 500ms-3s per LLM call
5. **Compliance** -- FCRA/FDCPA compliance requires verifiable, auditable outputs

### The Deterministic Advantage

1. **Reproducibility** -- Same input always produces same output
2. **Auditability** -- Every recommendation traces to a specific statute or data source
3. **Speed** -- All 10 agents execute in <100ms combined
4. **Cost** -- $0 per request, $0 per month, $0 forever
5. **Testability** -- 300+ tests verify every code path

## Agent Flow

```
CreditProfile (input)
       |
       v
+--[Kevin Services]--+
| CreditAssessment   |
| ScoreSimulator     |
| DisputePathway     |
+--------+-----------+
         |
   +-----v------+
   |   PARKS    |  --> Life barriers (employment, housing, auto, insurance)
   +-----+------+
         |
   +-----v------+     +----------+     +----------+
   |   KING     | <-- | ROBINSON |     |  TRUTH   | (compliance gate)
   +-----+------+     +----------+     +-----+----+
         |                                    |
   +-----v------+     +----------+     +-----v----+
   |  COLVIN    |     |   GRAY   |     |  TUBMAN  |
   +-----+------+     +----------+     +----------+
         |                 |                 |
   +-----v------+         |                 |
   |   LEWIS    |         |                 |
   +-----+------+         |                 |
         |                 |                 |
   +-----v-----------v----v-----------v-----+
   |              PHANTOM                    |
   |        (Poverty Tax Calculator)         |
   +-----------------+-----------------------+
                     |
               +-----v------+
               |   MOSES    |  (Orchestrator)
               |  + Truth   |  (Final compliance gate)
               +-----+------+
                     |
               +-----v------+
               |   EXPORT   |  (HTML Liberation Plan)
               +-------------+
```

## Resilience Patterns

### Circuit Breaker

Each agent has a circuit breaker (failure_threshold=3, timeout=60s). After 3 consecutive failures, the circuit opens and the agent is skipped with a safe fallback value. After 60 seconds, the circuit enters half-open state and allows one retry.

### Dead Letter Queue (DLQ)

Every failed agent execution is logged to an in-memory DLQ with timestamp, agent name, error type, and input summary. The DLQ is included in the API response as `validation_summary.dlq_count` for transparency.

### Performance Benchmark

Every agent is individually timed using `time.perf_counter()`. The response includes `performance.per_agent_ms` showing exactly how long each agent took.

## Zero Breaking Changes

Baby INERTIA adds 4 new endpoints under `/v1/`. All existing endpoints (`/assess`, `/v1/simulate`, `/v1/disputes`) return identical responses. The agents directory is self-contained with zero imports into existing modules.
