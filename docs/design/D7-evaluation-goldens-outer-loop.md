# D7 · Evaluation, goldens and the outer loop

**Proposed (2026-10-28).** How quality is measured without per-item human verification: the
versioned guideline, blind two-pass golden authoring by Sonnet with adjudication, splits and
leakage rules, alignment and scoring, witnesses that do not depend on the golden author, experiments and
promotion, and the operator's outer loop of direction. Tables: [D3 §7](D3-database.md#7-eval-goldens-and-results).

## 1. The problem and the answer

Goldens are written by **Sonnet 5.5** subagents (ADR-0011); the pipeline escalates to Opus, the
agent tier. Keeping the golden author apart from the escalation tier means a pipeline tuned toward
Opus's habits is not rewarded by Opus-written goldens. Goldens could still encode their author's
habits, and a guideline nobody reviews could drift. The design answers with five separate
mechanisms, none sufficient alone:

> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)
> Status: **Measured** (S0-R2, 2026-10-28): Sonnet from unit packets with the §3.2 inputs reached full-tier
> F1 0.77 against the reference, against 0.68 for the Opus passes on the earlier inputs
> ([S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md); record s0r2.scores)

| Risk | Mechanism | Section |
|---|---|---|
| Goldens copy pipeline output | Authoring is blind to every pipeline output; packets carry no hints | §3 |
| One annotator's idiosyncrasy becomes truth | Two blind passes, measured agreement, explicit adjudication with reasons | §3 |
| The pipeline is tuned to the test goldens | Test pages never used for examples, prompts, fitting, training or error analysis; test units are extracted like any other | §4 |
| The golden author is systematically wrong in a way both passes share | Witnesses independent of the golden author: author markup not consumed, computation, reference facts | §6 |
| The guideline drifts from what the operator wants | The operator directs from an outer loop; every direction is versioned and re-scored | §2, §8 |

Agreement between the two blind passes is reported as the **ceiling**: no metric is read as
meaningful beyond the annotators' own agreement on that predicate.

## 2. Guidelines

- **Location and versions.** `domains/<name>/guideline.md`; each content change is a
  `meta.guideline_version` (content hash, label, parent, change note, author). The generated
  annotator reference (D2 §7.5, §10.10) is regenerated per schema version, so the guideline and the
  reference always name the current schema.
- **Conventions are written, not inferred.** Every choice an annotator would otherwise have to guess
  (statement roles, modality, which claims carry conditions, symbol bindings, parameter names) is a
  rule in the guideline. Where the guideline is silent, annotators agree on content and diverge on
  qualifiers, and the reference silently takes one annotator's habit (S0: core F1 0.93 against full
  0.63 between two Opus passes; the smaller models' losses concentrated at unwritten conventions).
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
- **Checking a rule change.** A change of the rule class is checked before it is adopted, by the
  procedure S0-R2 used:
  - one Sonnet pass and one Haiku pass from packets, under the changed guideline; Haiku serves as a
    clarity probe here, not as an author;
  - over the units used to write the change, plus held-out dev units from pages not used for it.
    The held-out units are fresh each time, since units once used become rule-writing units;
  - against a reference conformed to the changed rule, with the conformance decisions recorded;
  - pass against pass reported beside pass against reference;
  - any reference correction made after seeing a pass reported with the figures before it.

  The result is an evidence record (ADR-0010). Clarifications need no check.

## 3. Golden authoring protocol

### 3.1 Units and sets

A golden unit is one annotation unit (a `unit` segment, or a paragraph outside units) of a page,
identified by its **unit key**, the unit's generated locator
([D1 §3.4](D1-knowledge-representation.md#34-locators)), not by a rendition, so it survives a
content-preserving ingest change and an edit elsewhere on its page that leaves its locator
unique. Its authority is what its passes wrote: the model-facing batch of each pass with its
citation frame ([D1 §10.3](D1-knowledge-representation.md#103-stability-limits), D2 §7.3). Golden items (`eval.golden_item`) are a projection of pass C's batch,
derived per rendition by the production quote cascade (D4 §4.3) and recording the rendition they
were derived on (P0CL-03; operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28)

Sets (`eval.golden_set`) are per split and guideline version. Initial sizes, kept
small while debugging: **dev 40 units, test 40 units** from the first-pass chapters, stratified
by statement kind, chapter and math share; growing to about 150 each by phase 2 (`OPEN-D7-1`).
The trace units T1–T4 and the spike core units are forced into dev by the sampler (below).
They become goldens only by this protocol: phase 0 **re-authors** them with Sonnet passes
(§3.2–§3.4). The S0/S0-R2 v1
reference is not imported as goldens. Opus passes and the root authored it, and the phase 0
extractor is also Opus, so importing it would reward a pipeline for Opus's habits, the bias ADR-0011
removed. It serves as fixture proposals for the deterministic acceptance test (D9 §4) and as a
witness (§6).
> Status: **Proposed** (2026-10-28, design authority; independence per ADR-0011)

**Split assignment** (`ci golden split`). Within each chapter, pages are ordered by
`sha256(source_uri + seed)` and every fifth goes to test (about 20%). Two kinds of page are
assigned before sampling:
- **Reserved:** pages that supply the annotator reference's worked examples (D2 §10.10; for
  statistics v1, `special/Weibull.html`). They are in no split and never golden units, so the
  examples every prompt carries never sit in an evaluated set.
- **Forced to dev:** pages used to write or check guideline rules (the four spike pages, and
  `special/Pareto.html` and `special/ChiSquare.html`, the S0-R2 held-out pages).

Assignments live in `eval.document_split` and change only by operator direction.

**Unit sampling** (`ci golden create --split S --size N --seed K`). Units are drawn from the
split's pages; strata are statement kind (markup hint, else M05, else `narrative`) × math-share
tercile (M02); allocation is proportional with at least one unit per non-empty stratum; within a
stratum units are taken in order of `sha256(unit_key + seed)`, which the locator-based unit key
keeps stable across content-preserving ingest changes. **Forced units** are taken
before sampling: for dev, the trace units and the spike core units (the `trace` and `core12`
slices, D2 §12.2), which the phase 0 gate's typed questions and the S0-R2 comparisons need. They
count towards their strata, and sampling fills the remaining places (P0CL-10; operator,
2026-10-28). Sampling the dev set also fills the golden-unit pages of the `phase0-golden` slice
(D2 §12.2), which is declared by name and resolved from the set.
> Status: **Proposed** (2026-10-28)

### 3.2 Pass A and pass B (blind)

Two fresh **Sonnet 5.5** subagent sessions, dispatched by the Claude Code session, each receive only:

- the guideline version (full text);
- the annotator reference generated from the schema version (D2 §10.10): entity types with their
  identity slots; every predicate with its statement role, modality and condition rule; qualifiers;
  enums; exact value and condition-node shapes; and complete worked examples taken from pages outside
  every golden split (§4);
- the unit packet in golden mode: the D4 §4.1 packet **without hints, known entities, alternatives or any
  pipeline output** except one: its standing context is assembled by query from M13, a deterministic
  rule method over the text, whose version is recorded on the pass: for each symbol the unit uses, the
  sentence holding the binding site M13 assigns it, when that sentence lies outside the unit, plus
  the site a "Suppose again" reopens. Each context sentence carries an id (`cN`) that evidence may cite;
- the model-facing ClaimProposalBatch schema (D2 §7.3) and the validator, which reports format and
  invariant errors and guideline-rule warnings (D2 §7.4).

The page's full text is not given: the query-assembled context carries what the unit depends on.
The model is recorded on each `eval.golden_pass`; another model is a revisit of ADR-0011.

> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)
> Status: **Measured** on twelve core units and six held-out units (S0-R2, 2026-10-28):
> Sonnet 0.77 and Haiku 0.68 full-tier F1 against the reference from these inputs, against 0.37 and
> 0.35 from the guideline, schema and positional context alone. Sonnet and Haiku agreed with each
> other at 0.76 on the held-out units. Whether page text still helps with these inputs was not run
> (records s0r2.inputs, s0r2.scores).

They do not see each other's output, earlier golden versions, run claims or metrics. Each pass
is submitted through `write_golden` (D8) with `pass: a` or `pass: b` and stored as an
`eval.golden_pass` row holding the authored batch and its citation frame (the intervention row
references it). At submission its quotes are located on the current rendition as in D4 §4.3, as a
check: a pass whose quotes cannot be located is returned to its author once with the failures
listed.

### 3.3 Agreement

Passes A and B are aligned with the scorer of §5 (treating A as reference and B as prediction,
then symmetrized). Per unit and predicate, agreement at the core, full and evidence tiers is
stored in the unit's `agreement` record and aggregated per predicate as the **ceiling**.

### 3.4 Adjudication (pass C)

Pass C's task is created by `write_golden` in the transaction that stores the second of the
unit's passes A and B (D8 §2.2), so no command or orchestrator step has to notice that both exist.
> Status: **Proposed** (2026-10-28)

A third fresh Sonnet session receives the guideline, the annotator reference, the packet, both passes and the alignment diff
(matched, A-only, B-only, matched-with-qualifier-differences). For each difference it decides:
keep A, keep B, keep both as a **faithful ambiguity** (golden alternatives), drop both, or
rewrite; each decision has a one-line reason, and decisions that the guideline does not settle
are marked `guideline_gap` with the rule they touch. The result is pass C's authored batch with
its citation frame, from which the unit's golden items are derived per rendition (§3.1); the unit
becomes `adjudicated`. `guideline_gap` marks feed the operator's digest
(§8). Adjudication decides contested items and finds guideline gaps; it is not expected to raise a
unit above its better pass (S0-R2: a Sonnet adjudicator over a Sonnet and a Haiku pass scored 0.75
against the Sonnet pass's 0.77; record s0r2.adjudication). Every `guideline_gap` decision is a
candidate rule for the guideline.

### 3.5 Staleness and re-authoring

A rule change or schema change marks affected units `stale`. Stale units are re-authored by the
full protocol (A, B, C, blind; earlier versions are not shown). Earlier versions remain in the
database for comparison, so the effect of a guideline change on the goldens themselves is
visible (items added, removed, changed).

**A rendition the unit's citation frame no longer resolves on** is the third trigger (P0CL-03;
operator, 2026-10-28). When a run's rendition of the page refuses a frame locator, or the
located sentence's text differs from the frame's (D1 §10.3), the unit is stale. It is first
**re-located**: each cited sentence is found on the new rendition by its recorded text, the
frame's locators are regenerated, and the golden items are derived again. Only if a cited
sentence is no longer there is the unit re-authored by the full protocol. A content-preserving
ingest change triggers nothing, because it keeps the rendition (D1 §3.1), and an edit elsewhere
on the page leaves the unit's frame resolving.
> Status: **Proposed** (2026-10-28)

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
- **Never on the test split.** Test pages enter no training, fitting, prompt-optimization or
  example set, and test results no item-level analysis:
  1. as prompt examples (D4 §4.2) or in agent packets' retrieval. Example retrieval for any unit
     also excludes the unit's own page, so no candidate is scored on a golden it was shown (its
     own unit, or a page whose units share running examples, `OPEN-D7-3`);
  2. in confidence fitting or calibration (D5 §6.4), or any learned threshold;
  3. in adapter training or prompt optimization (phase 3), the agent's output on test pages
     included;
  4. for item-level error analysis: digests and agent-visible reports show test metrics in
     aggregate only, never test items or test errors.
- **Routing is not a leakage rule.** Test units route to the agent like any unit: the routing
  context has no split symbol (D6 §7.2), so test scores measure the deployed system, its agent
  tier included, rather than the pipeline without it. Test protection is the training, fitting
  and example exclusion above (P0CL-16; operator, 2026-10-28). In phase 0 no test page is extracted, because the `phase0-golden` slice holds none
  (§9).
  > Status: **Proposed** (2026-10-28)
- **Experiments decide on dev**; the test split is scored at phase gates and when a promotion
  candidate is evaluated for a gate.

## 5. Alignment and scoring

### 5.1 What is compared

For a golden unit, the unit key is resolved on the rendition the run selected for its page
(`kb.run_rendition`, D3 §8), and the golden items compared are the stored form derived on that
same rendition (§3.1). The run's **predicted set** is the claims whose primary evidence lies in
the resolved segment or whose statement is anchored there. Run and goldens are therefore compared
on one rendition, whichever rendition the passes were written on (P0CL-03; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

**Context premises are scored once.** A golden item recorded as a context premise (D2 §7.3; its
evidence cites `cN` sentences outside the unit) is scored as an item only in the golden unit
whose own text states it. In every other unit it is scored only through the `claim` nodes that
reference it, at full tier, which matches because the premise's statement keys the same in every
unit (D1 §10.1). Such items carry the `context` flag (D3 `eval.golden_item`). Counting them as
items in each dependent unit would make them false negatives there; widening the predicted set
would count them twice. Two readings are reported: *strict*
(status `accepted`) and *lenient* (`accepted`, `candidate`, `ambiguous`); also a precision–recall
curve over confidence.

### 5.2 Entity alignment

Golden entities align to run entities per unit by type plus: normalized symbol and same scope
segment for local entities; canonical label or alias for global ones; overlapping evidence as
tie-breaker. Matching is one-to-one, maximizing summed similarity with
`scipy.optimize.linear_sum_assignment(…, maximize=True)`. Pairs below a tier's similarity threshold
are removed from the cost matrix **before** assignment, not discarded after it, so a weak pair cannot
displace a strong one ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) IE-6). Tier preferences combined into one
matrix use weights derived from the candidate counts, not fixed powers of ten, which stay exact only
below 1,000 candidates per unit.

### 5.3 Claim alignment tiers

| Tier | A golden claim and a run claim match when |
|---|---|
| **core** | Same predicate; subjects aligned; objects aligned (entities) or equivalent (values) |
| **full** | core, plus equal modality and polarity, equal statement role, equivalent identity qualifiers (`param_values` key by key), and equivalent conditions |
| **evidence** | full, plus the run claim's primary evidence overlaps a golden primary span or lies in the same sentence |

- **Value equivalence.** Formulas: SymPy `simplify(a - b) == 0` with macros expanded, falling
  back to numeric comparison at random points satisfying the claims' conditions when
  simplification times out (`OPEN-D7-2`), the points drawn from a generator seeded by the two
  claims' keys so a comparison repeats exactly; sets: SymPy set equality; numbers: equal after unit
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
| Scope accuracy | Share of aligned local entities with the golden scope segment. Against goldens it is not fully independent of M13: golden extents are written from the context M13 chose (§3.2) |
| Identity quality | B-cubed precision and recall of run global entities against golden canonical labels across units; merge and split error counts |
| Derived correctness | Derived claims are excluded from precision; scored separately as share `consistent` under M21 or aligned to a golden item |
| Calibration | Expected calibration error of confidence on dev (D5 §6.4) |

**Uncertainty.** Every score has a 95% interval from 1,000 bootstrap resamples over units;
comparisons between runs use the paired bootstrap on the same units. The realization is
`scipy.stats.bootstrap` behind a thin wrapper, which reproduced the S0 intervals to within one ulp
(interfaces note IE-5, probe 2026-10-28), with four rules: the **percentile** method is named
(SciPy's default BCa gives different intervals); the **unit order** is fixed and recorded with the
seed, because it is part of the result; resamples where a score is undefined (no golden items of a
predicate) are **skipped and counted** from `bootstrap_distribution` rather than turning the
interval into NaN; run-to-run comparisons use the **paired-difference** form. Page-cluster intervals
are available for reports where units of one page are not independent.
> Status: **Tested** for parity with the spike's intervals (2026-10-28)

**Reading agreement with a reference.** A reference adjudicated from one model's passes favours that
model where the guideline is silent, so a comparison of annotators or authors reports pass against
pass (symmetrized, no reference) beside pass against reference, and checks any rule change on units
from pages not used to write it. A reference correction made after seeing a pass is reported with the
figures before it (S0, S0-R2, 2026-10-28).

**Re-scoring.** Results reference the golden set version they used and record the pass-C
batches they scored (`eval.result.golden_snapshot`, D3 §7), so a result stays tied to the items it
used after a unit is re-authored. When goldens change, kept runs that matter (the promoted run
and open experiments) are re-scored (`ops.run.kind = rescore`), so trends compare like with like.

## 6. Independent witnesses

Evidence of quality that does not pass through the golden author. A witness is valid for a metric only if no
method in the run consumed the witness's information for the output being measured; the
registry in `evaluate/witnesses.py` declares, per witness, which method inputs disqualify it.

| Witness | Measures | Independence condition |
|---|---|---|
| **Author markup** | `dfn` terms imply a definition statement defining that term: recall of `defines` claims for marked terms; block classes (`p.dfn`, `p.math`) and section titles imply statement kinds | Valid only in an ablation run (consolidation `use_markup_hints: false`, M08 off) that the experiment harness makes on dev units; never in ordinary runs, which use markup |
| **Computation** | Correctness (not guideline compliance) of distribution, moment and support claims: M21 verifier outcomes over accepted claims | Reported separately from runs where verifiers were confidence sources (the experiment harness can mask verifier sources) |
| **Reference facts** | A small reference pack in the domain (`domains/statistics/reference/`): supports, standard parameterizations, means and variances of common families, written from `sympy.stats` and `scipy.stats` definitions | Not readable by any method; consulted only by evaluation |
| **Cross-pass agreement** | Annotator agreement (§3.3) | Independent of the pipeline, not of the golden author |
| **Spike reference (v1)** | Agreement between the re-authored dev goldens and the S0/S0-R2 v1 reference on the units both cover; disagreements are read as guideline gaps or golden errors | Independent of the golden author's passes; not of the guideline, which was written from it |

**Random audit with prediction-powered inference.** At each phase gate a uniform random sample
of accepted claims from the whole corpus (default 100, excluding golden units) is judged by a
fresh session of the golden author's model (Sonnet, ADR-0011; Proposed, not yet run) in audit mode (blind to confidence and sources) under the guideline. Combined
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
5. **Bootstrap (phase 0).** No baseline exists before the first full run. The phase 0 first pass
   is a sequence of `agent_mode: complete` runs over the first-pass corpus scoped to the
   `phase0-golden` slice (§9; D6 §8), each reusing every finished task (D6 §4), so each is a
   finished snapshot and none waits across sessions;
   `wait` is for short slice runs only (D6 §2). The operator promotes the first of them that has
   no unresolved agent task, with `ci promote`, an operator act recorded as an intervention.
   Before the operator confirms, `ci promote` shows the **pre-registered readings**, fixed here
   before any phase 0 result is seen (P0CL-10; operator, 2026-10-28):
   - dev full-tier F1 with its interval (§5.4), beside the S0-R2 figures (record s0r2.scores);
   - identity quality: B-cubed precision and recall of the run's global entities against the
     golden canonical labels (§5.4);
   - the unlocated-quote rate: evidence items left `evidence_unlocated` (D4 §4.3);
   - the rule-warning rate: claims with an M19 `warning`, the `guideline:` group included (D2 §7.4).

   The readings inform the operator's decision and set no automatic threshold, since phase 0 has
   nothing to compare with but the spike. The promoted run becomes the baseline for the first
   experiments and the reference run that later runs record (`ops.run.reference_run_id`, D3 §4)
   for known entities and linking (D4 §4.1, D5 §3.3). Until the phase 2 identity gate, linking to
   it reuses entity keys but not canonical labels, so phase 0's label choices do not persist
   before identity is measured (D5 §3.3). The `trace` and `spike-pages` runs are debug slices and
   are never promoted (D6 §8).
> Status: **Proposed** (2026-10-28, design authority; readings P0CL-10)

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
7. Health: orphaned or stale judgments, failed tasks, skipped units by reason (`scope`, `budget`, …; D6 §1).

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
| 0 | Trace units and spike pages answer their typed questions from the database; evaluation runs | Trace acceptance tests pass on fixture proposals (D9 §4). The live `trace` and `spike-pages` runs answer their typed questions: the typed-query rows (D8 §5) for the trace and core units align with expectations derived from their re-authored dev goldens, the golden items each query selects, at the §5.3 tiers. `ci eval` produces dev scores with intervals. Successive `complete` runs scoped to `phase0-golden` converge with no unresolved agent task, and the operator promotes one after reading the pre-registered readings (§7 item 5) |
| 1 | F1 and intervention share measured per type and stage | Dev and test scores per predicate; `intervention.share` per predicate group and stage |
| 2 | Identity errors measured; confidence calibrated on goldens | B-cubed and merge/split counts; ECE ≤ 0.05 on dev |
| 3 | Intervention share falls at equal or better F1 | Test full-tier F1 not worse (paired bootstrap) and `intervention.share` lower than at the phase 2 gate |
| 4 | Coverage rises; new types reach target F1 | Unsupported-item rate falls; new predicates reach their target F1 on dev and test |
| 5 | A new pack built with bounded interventions | The new pack's dev goldens are authored and scored; F1 and `intervention.share` per type and stage are reported against the statistics pack at its phase 1 gate |

**Phase 0 freeze.** Phase 0 holds schema v0 (with S4's corrections) and guideline v1 fixed for
everything it extracts and scores: the dev goldens and the `phase0-golden` runs. The
`phase0-golden` slice (D2 §12.2, D6 §8) is the phase 0 extraction scope: the pages holding dev
golden units (listed once the dev set is sampled, §3.1), the forced-dev pages, and the trace and
core-unit pages, which is what the gate, the §7
experiments on the dev golden units and the reference-run bootstrap need; every other eligible
unit is recorded `skipped` with reason `scope` (D6 §7.4), and no test page is in it (P0CL-09;
operator, 2026-10-28). The promoted run and the goldens it is scored against therefore share one
version. The guideline v2 and schema v0.2 rows (D2 §11, OPEN-D2-7…20) land at the phase 0
boundary through the §2 rule-change check, because claim keys and goldens move with them. The
full first pass runs after them, in phase 1 with M10.
> Status: **Proposed** (2026-10-28)

## 10. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D7-1 | Golden set sizes that give useful intervals per predicate group at acceptable authoring time | Phase 1 interval widths |
| OPEN-D7-2 | Formula equivalence: SymPy simplification versus numeric sampling under conditions, and timeouts | Spike S5; S0 evidence (2026-10-28): canonical form decided nearly every value comparison; SymPy and numeric tiers a handful of times; manual decisions recorded with reasons |
| OPEN-D7-3 | Split granularity: page or chapter (pages within a chapter share running examples) | Phase 1: compare dev–test gaps |
| OPEN-D7-4 | Whether `ppi_py` (and which version) fits the audit design, or a hand-written PPI mean estimator suffices | Phase 2 |
| OPEN-D7-5 | Whether the page's full text still helps golden passes once standing context is assembled by query (S0-R2 ran packets only) | A paired run with and without page text on dev units |
