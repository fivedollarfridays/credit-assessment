# Baby INERTIA Integration Report

> Recommended path forward for maximum hackathon value.

---

## Executive Summary

Baby INERTIA proposes 10 deterministic agents, ~5,260 new lines, 300 tests, 4 endpoints, and ~4.5 hours of build time. After analyzing the plan against both codebases (credit-assessment: 64 modules, 1,154 tests; MontGoWork: 16 sprints, 590 tests), this report identifies which components deliver unique value, which duplicate existing systems, and how to integrate the valuable pieces without creating architectural conflict.

**Bottom line:** 4 of the 10 agents are genuinely new capabilities. 3 are upgrades to existing systems. 3 duplicate what MontGoWork already does better. The recommended path absorbs the 4 new agents and 3 upgrades across both repos in ~3 hours, skips the duplicates, and produces a unified demo narrative.

---

## Part 1: Component-by-Component Disposition

### ABSORB (New Capabilities -- Build These)

#### 1. Phantom -- Poverty Tax Calculator

**What it does:** Calculates the dollar-per-day and dollar-per-hour cost of bad credit using Bristol PFRC methodology. Four components: credit premium, insurance gap, employment barrier, housing premium. Produces a "Poverty Tax Receipt" with traced methodology.

**Why it's valuable:** This is the single most compelling demo moment in the entire plan. "Bad credit costs Maria $5.34/hour on a $7.25/hour wage -- a 73% invisible tax." No existing system in either repo does this. It transforms abstract score numbers into visceral dollar amounts.

**Overlap:** Zero. Neither credit-assessment nor MontGoWork has cost-of-credit quantification.

**Where it lives:** MontGoWork backend as `app/modules/poverty_tax/`. MontGoWork already owns the Montgomery context (population, poverty rate, living wage). The credit API provides the score and barriers; MontGoWork's poverty_tax module interprets them through Montgomery's economic lens.

**Estimated scope:** ~250 lines + `poverty_tax_tables.json` config + ~25 tests. The plan's 310-line estimate includes wage comparison and inflation derivation, which is right.

**Integration point:** `generate_plan()` in MontGoWork calls poverty_tax after receiving credit assessment results. Output goes into the existing Career Center Package as a new section. The Claude narrative prompt gets a new variable: `poverty_tax_summary`.

---

#### 2. Gray -- Adverse Action Decoder

**What it does:** When a user reports being denied (job, apartment, auto loan, insurance), Gray decodes the denial: what law applies (FCRA 615, ECOA), what the creditor was required to do, what rights the user has, and what letter to send. Bridges to the existing letter generator.

**Why it's valuable:** MontGoWork's assessment asks about barriers but doesn't help users understand *why* they were denied or what to do about a specific denial. Gray fills this gap. The letter bridge to the existing `/v1/letters` endpoint means zero duplicate code.

**Overlap:** Zero for denial decoding. The letter bridge reuses the existing credit-assessment letter system.

**Where it lives:** Credit-assessment API as `src/modules/credit/denial_decoder.py` + config files (`adverse_action_rules.json`, `denial_decoder.json`). Exposed via a new endpoint `POST /v1/denials/decode`. MontGoWork proxies to it when the user reports a denial.

**Estimated scope:** ~150 lines + 2 config files + ~18 tests.

**Integration point:** Optional context in MontGoWork's credit assessment flow. If the user selects "I was denied for [job/housing/auto/insurance]" on the credit form, MontGoWork passes that to the decode endpoint and shows the result alongside the credit assessment.

---

#### 3. Tubman -- Cross-Bureau Discrepancy Scanner

**What it does:** Compares data across 2-3 credit bureaus and finds exploitable inconsistencies: balance mismatches (>$100 or >10%), date discrepancies, duplicate accounts, mixed file risk. Each discrepancy gets severity ranking and recommended dispute bureau.

**Why it's valuable:** This is a genuinely new analytical capability. If a user has reports from multiple bureaus, finding inconsistencies is the highest-success-rate dispute strategy. No existing system does this.

**Overlap:** Zero.

**Where it lives:** Credit-assessment API as `src/modules/credit/bureau_compare.py` + `metro2_consistency_rules.json`. Exposed via `POST /v1/compare-bureaus`. MontGoWork can optionally proxy to it if multi-bureau data is available, but this is a secondary feature for the hackathon since most users won't have multi-bureau reports in the wizard flow.

**Estimated scope:** ~180 lines + config + ~20 tests.

**Integration point:** Standalone endpoint in credit-assessment API. MontGoWork integration deferred unless time permits -- this is a "nice to have" for the demo, not core flow.

---

#### 4. Colvin -- Anti-Detection Engine

**What it does:** Ensures dispute letters across multiple rounds are structurally and linguistically diverse to avoid e-OSCAR ACDV flagging. Rotates legal bases, varies paragraph structure, measures anti-flagging diversity score (0-1).

**Why it's valuable:** The credit-assessment API already has dispute lifecycle tracking (rounds) and letter generation, but nothing ensures round-over-round diversity. Colvin is the missing piece that makes the multi-round dispute system actually effective against bureau AI.

**Overlap:** Complementary to existing `letter_generator.py` and `dispute_routes.py`. Does not duplicate -- enhances.

**Where it lives:** Credit-assessment API as `src/modules/credit/letter_diversity.py` + `legal_basis_rotation.json`. Integrated into the existing letter generation pipeline -- `letter_generator.py` calls Colvin before emitting the final letter.

**Estimated scope:** ~150 lines + config + ~18 tests.

**Integration point:** Internal to credit-assessment API. MontGoWork sees no change -- letters returned from `/v1/letters` are automatically diversified.

---

### UPGRADE (Enhance Existing Systems)

#### 5. Parks Door Analysis -- Upgrade Credit Barrier Card

**What it does:** Maps credit score to specific blocked/open doors across employment categories, housing types, auto loan rates, and insurance premiums. Counts doors at each threshold. Identifies the "cheapest door" (lowest score gap to open).

**Current state:** MontGoWork's credit integration knows three things: HIGH/MEDIUM/LOW severity, and it filters jobs into three buckets. The credit API returns `eligibility[]` with product-level blocking. Neither system maps to *specific life categories* the way Parks does.

**What changes:** Enrich the credit-assessment API's `/v1/assess` response with a new `doors_analysis` field. This is an additive, backward-compatible change -- existing consumers ignore new fields.

**Where it lives:** Credit-assessment API. New file `src/modules/credit/doors.py` (~120 lines) + config files (`employment_credit_rules.json`, `housing_thresholds.json`, `auto_rates.json`, `insurance_by_score.json`). Called from `assessment.py` during the existing assessment pipeline.

**MontGoWork change:** The `CreditResults.tsx` component and the Career Center Package gain a "Doors" section: "Your score blocks 3 job categories. The cheapest to open: CNA jobs at 580 (45 points away)." The existing `after_repair` job bucket becomes more specific.

**Estimated scope:** ~120 lines + 4 config files + ~15 tests in credit-assessment. ~30 lines frontend change in MontGoWork.

---

#### 6. King Phasing -- Upgrade Dispute Pathway

**What it does:** Restructures the flat dispute step list into phased execution: Phase 1 (bureau disputes under FCRA 611), Phase 2 (direct-to-furnisher under FCRA 623(b)), Phase 3 (credit building). Adds `why_this_order` explanations and dependency validation.

**Current state:** The credit API's `dispute_pathway` returns a flat list of steps with priorities. There's no phasing, no furnisher-direct strategy, and no dependency validation.

**What changes:** Modify `dispute_pathway.py` to structure output into phases. Add `creditor_contacts.json` for furnisher addresses. The response shape changes from `steps[]` to `phases[{phase, steps[], why_this_order}]` -- this is a breaking change to the `dispute_pathway` field, so either version the field or add `phased_pathway` alongside.

**Where it lives:** Credit-assessment API. Modify existing `dispute_pathway.py` + add `creditor_contacts.json`.

**MontGoWork change:** Career Center Package's `_build_credit_pathway()` now shows phased steps instead of a flat list.

**Estimated scope:** ~80 lines modification to existing code + config + ~15 tests.

---

#### 7. Truth Compliance Gate -- Upgrade Letter Generator

**What it does:** Validates all dispute letter output for FCRA/FDCPA/CROA compliance. Scans for banned patterns (emotional language, template signatures, excessive legal citations). Blocks output that would get flagged.

**Current state:** The letter generator produces letters but has no output validation layer.

**What changes:** Add a validation pass at the end of `letter_generator.py`'s generation pipeline. If output fails validation, it's rewritten to be more specific and less template-like.

**Where it lives:** Credit-assessment API. New file `src/modules/credit/letter_compliance.py` (~120 lines) + `banned_patterns.json`. Called from `letter_generator.py` as a post-generation gate.

**MontGoWork change:** None. Letters returned by the API are automatically compliant.

**Estimated scope:** ~120 lines + config + ~15 tests.

---

### SKIP (Duplicates Existing MontGoWork Systems)

#### 8. Robinson -- Door Finder (SKIP)

**Reason:** MontGoWork already has a 5-factor resource scoring engine (`scoring.py`), Montgomery-specific resource database with health decay, BrightData job scraping with exponential backoff, and resource affinity routing. Robinson's `alternative_services.json` and `montgomery_resources.json` are inferior versions of MontGoWork's `data/montgomery_resources.json` + SQLite resource table.

**What to salvage:** Robinson's "free_stack calculator" concept (3 free actions, 45 minutes, estimated score improvement) is a good UX idea. This can be a ~20-line function added to MontGoWork's credit results display, not a full agent.

---

#### 9. Lewis -- Impact Projector (SKIP)

**Reason:** The credit-assessment API already has `simulation.py` with 10 action handlers. MontGoWork already has a `ComparisonView.tsx` component showing "Today vs. In 3 Months." Lewis repackages these into "doors opened count + annual savings" -- a display concern, not a new computation. The doors-opened count comes from Parks (which we're building). Annual savings is a multiplication.

**What to salvage:** Add a `savings_estimate` field to Parks' door analysis output. One line: `annual_savings = sum(door.annual_cost_difference for door in newly_opened_doors)`.

---

#### 10. Moses -- Orchestrator (SKIP)

**Reason:** MontGoWork's `generate_plan()` is already the orchestrator. It chains resource matching, job filtering, WIOA screening, credit assessment, and AI narrative generation. Adding a second orchestrator creates confusion about which pipeline produces "the plan." Moses's circuit breaker and dead letter queue are production-hardening patterns, not hackathon necessities.

**What to salvage:** Moses's `reasoning_chain` concept (visible agent collaboration narrative) is a good idea for the demo. Implement this as metadata in MontGoWork's existing plan output: `pipeline_steps: [{module, input_summary, output_summary, duration_ms}]`. ~30 lines in `engine.py`.

---

#### 11. Export -- HTML Liberation Plan (SKIP)

**Reason:** MontGoWork already has PDF export via html2pdf.js with barrier cards, job matches, next steps, credit info, QR code for feedback, and email delivery. The HTML export is a downgrade -- no QR codes, no email, no feedback loop.

**What to salvage:** Nothing. MontGoWork's export is strictly better.

---

## Part 2: Recommended Build Plan

### Sprint 24: Baby INERTIA Core (Credit-Assessment API)

Estimated: ~2.5 hours

| Task | Description | Lines | Tests | Priority |
|------|-------------|-------|-------|----------|
| T24.1 | Phantom poverty tax engine + config | ~250 | ~25 | P0 |
| T24.2 | Parks door analysis + 4 config files | ~120 | ~15 | P0 |
| T24.3 | Gray denial decoder + config | ~150 | ~18 | P0 |
| T24.4 | King phased dispute pathway upgrade | ~80 | ~15 | P1 |
| T24.5 | Colvin letter diversity + config | ~150 | ~18 | P1 |
| T24.6 | Truth compliance gate + config | ~120 | ~15 | P1 |
| T24.7 | Tubman cross-bureau scanner + config | ~180 | ~20 | P2 |

**Total new code:** ~1,050 lines (vs. plan's 3,350 -- 69% reduction by cutting duplicates)
**Total new tests:** ~126 (vs. plan's 300)
**Total new config:** ~7 JSON files (vs. plan's 17 -- cut Robinson/Lewis/Moses/Export configs)

### MontGoWork Integration (Separate Sprint)

Estimated: ~1 hour

| Task | Description | Where |
|------|-------------|-------|
| MW.1 | Poverty tax module + Career Center Package section | backend `app/modules/poverty_tax/` |
| MW.2 | Credit proxy upgrade: add doors_analysis to CreditAssessmentResult type | backend `app/modules/credit/types.py` |
| MW.3 | CreditResults.tsx: add doors section + poverty tax display | frontend |
| MW.4 | Career Center PDF: add poverty tax section | frontend PlanExport |
| MW.5 | Claude narrative prompt: add poverty tax variable | backend `app/ai/prompts.py` |
| MW.6 | Optional: denial context on credit form | frontend CreditForm + backend proxy |

---

## Part 3: Demo Narrative (Unified)

The plan's demo moment is strong but currently tells two stories. Here's the unified version:

> Maria walks into MontGoWork. She's unemployed, has a criminal record, no reliable transportation, and bad credit -- FICO 520 with a medical collection and three late payments.
>
> She answers 7 questions on her phone. MontGoWork identifies 4 barriers: credit, transportation, criminal record, and training. It matches her with 3 Montgomery resources, finds 8 jobs she can reach by bus, and screens her for WIOA support.
>
> Then the credit engine goes deeper. It finds her score blocks 3 specific job categories -- the cheapest to unlock is CNA at 580, just 45 points away. It calculates that bad credit costs her $5.34 per hour -- on a $7.25 wage, that's a 73% poverty tax. It generates a phased dispute plan: Phase 1 targets the medical collection with the bureau, Phase 2 goes directly to the creditor with new evidence, Phase 3 starts credit building with a secured card.
>
> Every dispute letter is unique -- structurally varied to beat e-OSCAR AI detection. Every dollar in the poverty tax is traced to Bristol PFRC methodology. Every number is sourced.
>
> She walks out with a Career Center Ready Package: staff summary, document checklist, what to say, phased credit repair plan, poverty tax receipt, and 8 job matches. One visit. One plan. Zero cost.
>
> Scale that to Montgomery's 41,729 residents in poverty -- $14.6 million per year leaving this community through the poverty premium alone.

**Why this works better than the dual-system approach:**
- One story, one product, one plan page
- Poverty tax is *inside* the Career Center Package, not a separate endpoint
- Dispute strategy is *inside* the credit results, not a competing "Liberation Plan"
- The judge sees one integrated system, not two APIs stapled together

---

## Part 4: What We Gain vs. What We Cut

### What the Hackathon Gains

| Capability | Source | Demo Impact |
|------------|--------|-------------|
| Poverty Tax Receipt ($5.34/hr on $7.25/hr) | Phantom | The demo moment. Visceral, quantified, sourced. |
| Door Analysis (3 jobs blocked, cheapest at 580) | Parks | Makes credit score tangible. "45 points = CNA jobs." |
| Denial Decoder ("here's what the law says they owed you") | Gray | New capability for denied users. |
| Phased Dispute Strategy (bureau > furnisher > build) | King | Smarter than flat step list. |
| Anti-Detection Letters (beat e-OSCAR ACDV) | Colvin | Technical credibility with judges. |
| Compliance Gate (no template signatures) | Truth | "Every letter passes CROA validation." |
| Cross-Bureau Scanner (find inconsistencies) | Tubman | Advanced feature, shows depth. |
| Community Impact ($14.6M/year) | Phantom math | Scales the story to Montgomery. |

### What We Cut (and Why It's Fine)

| Cut | Reason | What Replaces It |
|-----|--------|------------------|
| Robinson agent | MontGoWork's 5-factor scoring + BrightData is better | Existing resource matching |
| Lewis agent | simulation.py + ComparisonView already exist | Parks savings_estimate field |
| Moses orchestrator | generate_plan() is already the orchestrator | Existing MontGoWork pipeline |
| Export HTML | MontGoWork's PDF export is more mature | Existing PDF with poverty tax section added |
| 10 agent config files | Robinson/Lewis/Moses/Export don't need configs | 7 config files instead of 17 |
| Circuit breaker/DLQ | Production hardening, not hackathon demo value | Not needed for demo |
| CreditPulse event bus | Over-engineered for 4 agents | Direct function calls |
| ARCHITECTURE.md | Nice-to-have doc | Existing README + ROADMAP |
| METHODOLOGY.md | Phantom's methodology_source field in the response covers this | Response metadata |

### Net Effect

| Metric | Baby INERTIA Plan | Recommended Path | Reduction |
|--------|-------------------|------------------|-----------|
| New code lines | 3,350 | ~1,050 | 69% less |
| New test count | 300 | ~126 | 58% less |
| Config files | 17 | 7 | 59% less |
| New endpoints | 4 | 3 | 25% less |
| Build time | 4.5 hours | ~3 hours | 33% less |
| Duplicate code risk | High (3 agents duplicate MontGoWork) | Zero | Eliminated |
| Architectural conflict | Yes (2 orchestrators, 2 export systems) | None | Eliminated |
| Demo narrative | Split (Liberation Plan vs MontGoWork plan) | Unified | Cleaner |

---

## Part 5: Risk Assessment

### Remaining Risks

1. **Time pressure:** ~3 hours is still significant. If time runs short, cut P2 (Tubman) and P1 items (King, Colvin, Truth) -- Phantom and Parks alone deliver the demo moment.

2. **Config data quality:** The plan claims verified data (Census, MIT, BLS) but the JSON files don't exist yet. Budget 30 minutes for config creation and source verification.

3. **Architecture constraints:** Credit-assessment enforces < 400 LOC/file, < 15 functions, < 20 imports. Phantom at ~250 lines is fine. All others are under limit.

4. **MontGoWork integration:** Changing the Career Center Package to include poverty tax requires frontend changes. If the frontend developer isn't available, the poverty tax can live as a standalone credit-assessment endpoint and be shown separately.

5. **Backward compatibility:** Adding `doors_analysis` and `phased_pathway` to the credit API response must not break MontGoWork's existing `CreditAssessmentResult` type. Use additive fields only.

### Minimum Viable Demo (If Only 1.5 Hours)

Build only Phantom (poverty tax) and Parks (door analysis). Skip everything else. These two alone deliver:
- "$5.34/hour poverty tax on $7.25/hour wage"
- "45 points to CNA jobs"
- "$14.6M/year leaving Montgomery"

That's enough for the demo moment.

---

## Part 6: Decision Matrix

| Priority | Build? | Agent/Feature | Hours | Hackathon Impact |
|----------|--------|---------------|-------|------------------|
| P0 | YES | Phantom (poverty tax) | 0.75 | The demo moment |
| P0 | YES | Parks (door analysis) | 0.5 | Makes score tangible |
| P0 | YES | Gray (denial decoder) | 0.5 | New user capability |
| P1 | YES if time | King (phased pathway) | 0.5 | Smarter disputes |
| P1 | YES if time | Colvin (anti-detection) | 0.5 | Technical credibility |
| P1 | YES if time | Truth (compliance gate) | 0.5 | Quality assurance |
| P2 | MAYBE | Tubman (cross-bureau) | 0.75 | Advanced feature |
| -- | NO | Robinson (resources) | -- | MontGoWork does this |
| -- | NO | Lewis (projections) | -- | simulation.py does this |
| -- | NO | Moses (orchestrator) | -- | generate_plan() does this |
| -- | NO | Export (HTML) | -- | PDF export does this |
