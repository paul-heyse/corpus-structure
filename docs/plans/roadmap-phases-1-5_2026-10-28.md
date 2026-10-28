# Roadmap: phases 1–5

**Status:** Roadmap, not an execution plan (2026-10-28). It says what each phase after phase 0 adds,
what must be true before it starts, which spike or measurement decides its open choices, and when
it gets a detailed plan. Execution belongs to the detailed phase plans, the first of which is the
[phase 0 series](phase-0_2026-10-28.md); spike execution belongs to the
[design-spikes series](design-spikes-s0-s1_2026-10-28.md); design findings to the
[design-phase plan](design-phase_2026-10-28.md). **Revised:** 2026-10-28.

The phases, their gates and their scope are owned by the design: the phase table in
[D0](../design/D0-target-overview.md#phases), the gates in [D7 §9](../design/D7-evaluation-goldens-outer-loop.md#9-phase-gates),
the method phases in [D4 §3](../design/D4-method-catalog.md), consolidation by phase in
[D5 §11](../design/D5-consolidation-identity-confidence.md) and policies by phase in
[D6 §7.5](../design/D6-orchestration-metrics-policies.md). This page links them and adds only the
sequencing view: what feeds each phase and what would change it.

## The principle every phase follows

Each phase ends with the whole loop running on the whole corpus and the typed questions answered
from the database (P12 in the [design rationale](../design/rationale.md)). A method replaces
another only when golden-set evaluation shows it matches or beats it (D7 §7). Targets for each
gate are set from the previous phase's measured baseline, not guessed now (rationale §4.15).

## Phase 1 · Baseline

| | |
|---|---|
| **Adds** | Encoders and readers (M04 embeddings, M05–M07 GLiNER2, M08 patterns when a gap names it, M12 quantities, M22 cues); M11's SymPy conversion; M13 as the scope source for consolidation; the local LLM tier (M10 propose, M16 judge); M14 lexical linking; slots and alternatives (D5 §5.4); cold-start confidence (D5 §6.3); the `adjudicate` tool; exports (D8 §6); `kb.embedding` in a new migration |
| **Entry** | The phase 0 gate (D7 §9 row 0) passed, with the first first-pass run promoted (D7 §7 bootstrap); the dev goldens re-authored by the Sonnet protocol; schema v0.2 and guideline v2 landed at the phase 0 boundary (D7 §9 phase 0 freeze) |
| **Decided by** | **S2:** whether GLiNER2 carries `has_distribution` at useful recall on math-dense text; raw, masked or Unicode math (OPEN-D2-2); mention overlap near math (OPEN-D5-4); whether the spaCy→GLiNER2 candidate-scoring method enters the catalogue. **S3:** the local model, reasoning setting and packet unit (OPEN-D4-1, D4-2, D4-4); output caps; whether M16 pre-adjudication is worth running before the agent. **S5:** grammar coverage, the backend (OPEN-D4-3) and equivalence tiers (OPEN-D7-2). **S7:** the embedding model and dimension (OPEN-D3-2), and whether vectors add recall over aliases and fuzzy matching. **G1:** the GPU mode (OPEN-D6-2) |
| **Detailed plan** | Written when S2, S3, S5 and S7 have reported and X2 has folded them in |
| **Risks** | Math density makes encoders look weak and the LLM tier strong on statistics, which will not generalize to business text (rationale §6.1): do not over-tune the encoder tier to Siegrist. Output caps, not input caps, bind the LLM tiers (§6.7) |

## Phase 2 · Consolidation

| | |
|---|---|
| **Adds** | M14 vector linking; M15 record linkage (Splink, conditional); M20 z3 consistency (conditional, on measured conflicts); M23 derived claims (trace T3 D1); the latent-truth confidence model (pgmpy `DiscreteBayesianNetwork`, `DiscreteEM`, `VariableElimination`) with isotonic calibration; identity grey-zone adjudication; golden sets grown towards about 150 units each; the random audit with prediction-powered inference (D7 §6, OPEN-D7-4) |
| **Entry** | The phase 1 gate; enough aligned claims to fit the latent model (OPEN-D5-2) |
| **Decided by** | Phase 1 measurements: per-method sensitivity and false-positive rates per predicate group; identity error rates (which decide whether Splink's multi-attribute linkage is needed in statistics at all); S5's z3 results for M20; OPEN-D6-1 (barriers versus dataflow) once runs are long enough for idle GPU time to matter. Python 3.14 wheels for pgmpy and splink are checked here (OPEN-D9-1) |
| **Detailed plan** | Written at the phase 1 gate |
| **Risks** | Identity across units and pages (parameter names, families' parameterizations, RG-7) is likely the first large source of identity errors (rationale §6.4) |

## Phase 3 · Distillation

| | |
|---|---|
| **Adds** | Escalation ladders across tiers; GLiNER2 LoRA adapters trained on agent corrections (the main route by which interventions decline); few-shot examples, then prompt optimization (gepa) against dev goldens; thresholds tuned from adjudications that cluster by score (rationale §4.9) |
| **Entry** | The phase 2 gate; enough agent corrections per type to train an adapter |
| **Decided by** | Phase 2's calibrated confidence and per-method reliability, which the scale-back policies read (D6 §7.5 row 3) |
| **Detailed plan** | Written at the phase 2 gate |
| **Risks** | Residual circularity: golden author and agent tier are models of one family (rationale §6.3). The witnesses (D7 §6) are the independent check and must exist before distillation is judged |

## Phase 4 · Schema depth

| | |
|---|---|
| **Adds** | Coverage-gap discovery: the fact-bearing coverage trigger and LLM open extraction (D6 §7.3); schema versions with migrations (D2 §8); statistics verifiers (M21) as confidence sources |
| **Entry** | The phase 3 gate |
| **Decided by** | The unsupported-item rate and the fact-bearing coverage share; S5's verifier results |
| **Detailed plan** | Written at the phase 3 gate |
| **Risks** | Guideline revisions written from too few units encode Siegrist's quirks as conventions: every rule change goes through the D7 §2 check on held-out units (rationale §6.2) |

## Phase 5 · Second corpus

| | |
|---|---|
| **Adds** | A domain pack for a more NLP-natural corpus, chosen where statistics struggled; later hosted models and tenants (DESIGN §1.2); the generality checklist's constructs exercised for real (DESIGN §1.3): multi-attribute identity, valid time, tables with units, rules as derived models, email threads; pgmpy as an output model of stated business dependencies (D0, "Later uses") |
| **Entry** | The phase 4 gate, or earlier if math density stalls statistics progress (D0 decisions) |
| **Decided by** | Which corpus; the D7 §9 phase 5 row measures the new pack against the statistics pack's phase 1 gate |
| **Detailed plan** | Written when the corpus is chosen |
| **Risks** | Anything statistics-specific that leaked into the core; the design/target reviews use the generality checklist as change scenarios to catch it early |

## Deferred, each with its trigger

The design's deliberately-left-out list (D0) and the design-phase plan's deferred table hold the
methods that enter only when a measured gap names them: PSL and AMIE rule mining, cvxpy family
selection, causal discovery from data, MinHash source dependence, retrieval fusion and reranking,
sealed publication, exact replay, the hosted tier before phase 5, RDF publication, product Rust.
