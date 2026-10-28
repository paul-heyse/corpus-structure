# D7 · Evaluation, goldens and the outer loop

**Proposed (2026-10-28).** How quality is measured without per-item human verification: the
versioned guideline, blind two-pass golden authoring by Opus with adjudication, splits and
leakage rules, alignment and scoring, witnesses that do not depend on Opus, experiments and
promotion, and the operator's outer loop of direction. Tables: [D3 §7](D3-database.md#7-eval-goldens-and-results).

## 1. The problem and the answer

Goldens are written by Opus; the pipeline escalates to Opus. Scoring one against the other could
measure only agreement with Opus, and a guideline nobody reviews could drift. The design answers
with five separate mechanisms, none sufficient alone:

| Risk | Mechanism | Section |
|---|---|---|
| Goldens copy pipeline output | Authoring is blind to every pipeline output; packets carry no hints | §3 |
| One annotator's idiosyncrasy becomes truth | Two blind passes, measured agreement, explicit adjudication with reasons | §3 |
| The pipeline is tuned to the test goldens | Test split never used for prompts, fitting, agent work or error analysis | §4 |
| Opus is systematically wrong in a way both passes share | Witnesses independent of Opus: author markup not consumed, computation, reference facts | §6 |
| The guideline drifts from what the operator wants | The operator directs from an outer loop; every direction is versioned and re-scored | §2, §8 |

Agreement between the two blind passes is reported as the **ceiling**: no metric is read as
meaningful beyond the annotators' own agreement on that predicate.

## 2. Guidelines

- **Location and versions.** `domains/<name>/guideline.md`; each content change is a
  `meta.guideline_version` (content hash, label, parent, change note, author). The generated
  inventory (D2 §7.5) is regenerated per schema version, so the guideline always names the
  current schema.
- **Core tags.** Sections marked `<!-- core -->` are included in LLM prompts (D4 §4.2); the
  whole guideline is given to golden authors.
- **Change classes.**

| Class | Example | Who may apply it | Golden consequence |
|---|---|---|---|
| Clarification | Adds an example; rewords without changing what is annotated | Opus directly (recorded, listed in the next digest) | None; units stay `adjudicated` |
| Rule change | "Annotate proof steps that state named results" | Opus, only citing an operator direction id, or after the operator's `ack` in the digest | Affected units become `stale` and are re-authored (§3.5) |
| Schema-driven | A predicate is split | With a schema version and migration (D2 §8) | Items migrated; orphans re-authored |

- **Affected units** of a rule change are those with golden items of the predicates or classes
  the change names, or of the statement kinds it names; the proposal lists them, the tool
  computes them, and the larger set is used.
- **Direction log.** Each operator direction is appended to the guideline's direction log
  (D2 §10.11) with the changes and re-authorings it caused.

## 3. Golden authoring protocol

### 3.1 Units and sets

A golden unit is one annotation unit (a `unit` segment, or a paragraph outside units) of one
rendition. Sets (`eval.golden_set`) are per split and guideline version. Initial sizes, kept
small while debugging: **dev 40 units, test 40 units** from the first-pass chapters, stratified
by statement kind, chapter and math share; growing to about 150 each by phase 2 (`OPEN-D7-1`).
The trace units T1–T4 are in dev; the spike core units are in dev.

**Split assignment** (`ci golden split`). Within each chapter, pages are ordered by
`sha256(source_uri + seed)` and every fifth goes to test (about 20%); the four spike pages are
forced to dev. Assignments live in `eval.document_split` and change only by operator direction.

**Unit sampling** (`ci golden create --split S --size N --seed K`). Units are drawn from the
split's pages; strata are statement kind (markup hint, else M05, else `narrative`) × math-share
tercile (M02); allocation is proportional with at least one unit per non-empty stratum; within a
stratum units are taken in order of `sha256(unit_key + seed)`.

### 3.2 Pass A and pass B (blind)

Two fresh Opus subagent sessions, dispatched by the Claude Code session, each receive only:

- the guideline version (full text) and schema inventory;
- the unit packet in golden mode: the D4 §4.1 packet **without hints, known entities, alternatives or any
  pipeline output**, with standing context chosen by the rule "previous binding sentences in the
  same section" computed from the text alone (not from M13);
- the page's full canonical text for reference (guideline §10.2: read the page, annotate only
  the unit);
- the model-facing ClaimProposalBatch schema (D2 §7.3).

They do not see each other's output, earlier golden versions, run claims or metrics. Each pass
is submitted through `write_golden` (D8) with `pass: a` or `pass: b` and stored as an
`eval.golden_pass` row (the intervention row references it); quotes are located into offsets as in D4 §4.3. A pass whose quotes cannot be
located is returned to its author once with the failures listed.

### 3.3 Agreement

Passes A and B are aligned with the scorer of §5 (treating A as reference and B as prediction,
then symmetrized). Per unit and predicate, agreement at the core, full and evidence tiers is
stored in the unit's `agreement` record and aggregated per predicate as the **ceiling**.

### 3.4 Adjudication (pass C)

A third fresh session receives the guideline, the packet, both passes and the alignment diff
(matched, A-only, B-only, matched-with-qualifier-differences). For each difference it decides:
keep A, keep B, keep both as a **faithful ambiguity** (golden alternatives), drop both, or
rewrite; each decision has a one-line reason, and decisions that the guideline does not settle
are marked `guideline_gap` with the rule they touch. The result is the golden unit's items
(stored form); the unit becomes `adjudicated`. `guideline_gap` marks feed the operator's digest
(§8).

### 3.5 Staleness and re-authoring

A rule change or schema change marks affected units `stale`. Stale units are re-authored by the
full protocol (A, B, C, blind; earlier versions are not shown). Earlier versions remain in the
database for comparison, so the effect of a guideline change on the goldens themselves is
visible (items added, removed, changed).

### 3.6 What goldens contain

Goldens follow the guideline exactly: what the source states, in claim form, with bindings,
conditions, modality and evidence; `unsupported` items for what the schema cannot say; no
derived facts. They never reference run keys; entities and claims carry local refs, and global
entities carry canonical labels for cross-unit identity.

## 4. Splits and leakage

- **Split by document.** All units of a page are in one split, so the test split shares no page
  with dev. Pages are assigned by stratified sampling over chapters; the four spike pages are
  dev. The test set is frozen at each phase gate (`frozen_at`); between gates it changes only by
  re-authoring stale units.
- **Never on the test split:**
  1. as prompt examples (D4 §4.2) or in agent packets' retrieval;
  2. in confidence fitting or calibration (D5 §6.4), or any learned threshold;
  3. in adapter training or prompt optimization (phase 3);
  4. for agent extraction or adjudication in any run: policies exclude units with `split =
     test` from agent routing, so test-split knowledge in the promoted run is pipeline-only;
  5. for item-level error analysis: digests and agent-visible reports show test metrics in
     aggregate only, never test items or test errors.
- **Experiments decide on dev**; the test split is scored at phase gates and when a promotion
  candidate is evaluated for a gate.

## 5. Alignment and scoring

### 5.1 What is compared

For a golden unit, the run's **predicted set** is the claims whose primary evidence lies in the
unit's segment or whose statement is anchored there. Two readings are reported: *strict*
(status `accepted`) and *lenient* (`accepted`, `candidate`, `ambiguous`); also a precision–recall
curve over confidence.

### 5.2 Entity alignment

Golden entities align to run entities per unit by type plus: normalized symbol and same scope
segment for local entities; canonical label or alias for global ones; overlapping evidence as
tie-breaker. Matching is one-to-one, maximizing summed similarity with
`scipy.optimize.linear_sum_assignment`.

### 5.3 Claim alignment tiers

| Tier | A golden claim and a run claim match when |
|---|---|
| **core** | Same predicate; subjects aligned; objects aligned (entities) or equivalent (values) |
| **full** | core, plus equal modality and polarity, equal statement role, equivalent identity qualifiers (`param_values` key by key), and equivalent conditions |
| **evidence** | full, plus the run claim's primary evidence overlaps a golden primary span or lies in the same sentence |

- **Value equivalence.** Formulas: SymPy `simplify(a - b) == 0` with macros expanded, falling
  back to numeric comparison at random points satisfying the claims' conditions when
  simplification times out (`OPEN-D7-2`); sets: SymPy set equality; numbers: equal after unit
  conversion within 1e-9 relative; text: canonical form (D1 §6.2).
- **Condition equivalence.** Both trees canonicalized; leaves matched one-to-one (values by
  equivalence, `claim` leaves by the alignment of the referenced claims, `phrase` leaves by
  span overlap). With M20 available, z3 equivalence of the translatable parts replaces leaf
  matching.
- Claims are matched one-to-one per unit and tier, maximizing the number of matches.
- **Faithful ambiguity.** A golden alternative group matches if the run has an alternative group
  over the same readings, or any one reading (counted as `ambiguity_collapsed`).

### 5.4 Scores

| Score | Definition |
|---|---|
| Precision, recall, F1 | Per tier; per predicate, statement kind, chapter; micro and macro |
| Unsupported recall | Share of golden `unsupported` items the run also records as `unsupported` (span overlap) |
| Binding accuracy | Over symbols of aligned formula values: run binding kind and target equal to golden |
| Scope accuracy | Share of aligned local entities with the golden scope segment |
| Identity quality | B-cubed precision and recall of run global entities against golden canonical labels across units; merge and split error counts |
| Derived correctness | Derived claims are excluded from precision; scored separately as share `consistent` under M21 or aligned to a golden item |
| Calibration | Expected calibration error of confidence on dev (D5 §6.4) |

**Uncertainty.** Every score has a 95% interval from 1,000 bootstrap resamples over units;
comparisons between runs use the paired bootstrap on the same units.

**Re-scoring.** Results reference the golden set version they used. When goldens change, kept
runs that matter (the promoted run and open experiments) are re-scored (`ops.run.kind =
rescore`), so trends compare like with like.

## 6. Independent witnesses

Evidence of quality that does not pass through Opus. A witness is valid for a metric only if no
method in the run consumed the witness's information for the output being measured; the
registry in `evaluate/witnesses.py` declares, per witness, which method inputs disqualify it.

| Witness | Measures | Independence condition |
|---|---|---|
| **Author markup** | `dfn` terms imply a definition statement defining that term: recall of `defines` claims for marked terms; unit id prefixes imply statement kinds | Valid only in an ablation run (consolidation `use_markup_hints: false`, M08 off) that the experiment harness makes on dev units; never in ordinary runs, which use markup |
| **Computation** | Correctness (not guideline compliance) of distribution, moment and support claims: M21 verifier outcomes over accepted claims | Reported separately from runs where verifiers were confidence sources (the experiment harness can mask verifier sources) |
| **Reference facts** | A small reference pack in the domain (`domains/statistics/reference/`): supports, standard parameterizations, means and variances of common families, written from `sympy.stats` and `scipy.stats` definitions | Not readable by any method; consulted only by evaluation |
| **Cross-pass agreement** | Annotator agreement (§3.3) | Independent of the pipeline, not of Opus |

**Random audit with prediction-powered inference.** At each phase gate a uniform random sample
of accepted claims from the whole corpus (default 100, excluding golden units) is judged by a
fresh Opus session in audit mode (blind to confidence and sources) under the guideline. Combined
with the pipeline's confidence over all accepted claims through prediction-powered inference
(`ppi_py`, mean estimation), this gives a corpus-level precision estimate with a valid interval,
not just a golden-unit estimate. The audit sample is never used for fitting.

## 7. Experiments and promotion

An experiment (`ops.experiment`) tests one change: a method configuration, model, policy
version, schema version or guideline version.

1. **Hypothesis and metrics**: a target metric (for example full-tier F1 on `has_distribution`)
   and guard metrics (overall full-tier F1, `intervention.share`, `confidence.ece`).
2. **Runs**: baseline (the promoted configuration) and candidate on the same scope: the dev
   golden units, plus the first-pass corpus when the change affects non-golden metrics (yield,
   conflicts, cost). Reuse (D6 §4) makes the baseline mostly free.
3. **Decision rule**: promote when the target improves with a paired-bootstrap interval
   excluding zero and no guard regresses beyond its tolerance (default one point of F1, 0.02
   ECE); reject when the target does not improve; inconclusive otherwise. Opus records the
   decision through `decide_experiment` (D8); the operator can veto in the digest.
4. **Promotion**: the candidate configuration becomes the baseline; the next full run of it
   becomes the promoted run (`meta.project.promoted_run_id`).

Gap proposals from policies (D6 §7.3), schema proposals and guideline rule changes all reach the
promoted configuration only through this path.

## 8. The operator's outer loop

The operator does not verify golden items. The operator reads a short **direction digest** and
responds with directions.

### 8.1 The digest

Produced by `ci digest` (D8 §4) after each working session or experiment batch, at most about two
pages:

1. Dev metric changes since the last digest, with intervals; test metrics only at gates, in
   aggregate.
2. Guideline changes applied (clarifications) and awaiting `ack` (rule changes), each with its
   reason and affected-unit count.
3. Disagreement themes: A/B and adjudication differences clustered by predicate and guideline
   rule, each with up to three dev examples (quote, the two readings, the adjudication reason).
4. `guideline_gap` marks: questions the adjudicator could not settle from the guideline.
5. Coverage gaps: `unsupported` items clustered by text similarity, with counts (candidates for
   schema growth, phase 4).
6. Open proposals: schema changes, policy and gap proposals, experiments awaiting decision or
   veto.
7. Health: orphaned or stale judgments, failed tasks, budget skips.

### 8.2 Directions

A direction is free text in the operator's words with an optional scope (predicate, class,
statement kind, chapter, global), recorded through `record_direction` (D8) as an
`ops.intervention` of kind `direction` and in the direction log. Opus turns a direction into
guideline changes (rule class, citing the direction), schema or policy proposals, and
re-authoring of affected units; the next digest shows what changed and the effect on metrics.
The operator's other actions are `ack` (rule-class guideline changes) and `veto` (an experiment
decision); neither is required for clarifications or for ordinary runs.

### 8.3 What the operator is protected from

The digest never asks the operator to judge an individual claim. If the same theme recurs in
three consecutive digests without a direction, it is flagged as needing direction; otherwise the
system proceeds under the current guideline.

## 9. Phase gates

| Phase | Gate (D0) | Measured as |
|---|---|---|
| 0 | Trace units and spike pages answer their typed questions from the database; evaluation runs | Trace acceptance tests pass (D9 §4); `ci eval` produces scores for dev |
| 1 | F1 and intervention share measured per type and stage | Dev and test scores per predicate; `intervention.share` per predicate group and stage |
| 2 | Identity errors measured; confidence calibrated on goldens | B-cubed and merge/split counts; ECE ≤ 0.05 on dev |
| 3 | Intervention share falls at equal or better F1 | Test full-tier F1 not worse (paired bootstrap) and `intervention.share` lower than at the phase 2 gate |
| 4 | Coverage rises; new types reach target F1 | Unsupported-item rate falls; new predicates reach their target F1 on dev and test |

## 10. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D7-1 | Golden set sizes that give useful intervals per predicate group at acceptable authoring time | Phase 1 interval widths |
| OPEN-D7-2 | Formula equivalence: SymPy simplification versus numeric sampling under conditions, and timeouts | Spike S5 |
| OPEN-D7-3 | Split granularity: page or chapter (pages within a chapter share running examples) | Phase 1: compare dev–test gaps |
| OPEN-D7-4 | Whether `ppi_py` (and which version) fits the audit design, or a hand-written PPI mean estimator suffices | Phase 2 |
