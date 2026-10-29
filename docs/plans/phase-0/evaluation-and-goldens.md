# Phase 0: evaluation and goldens

**Status:** Active. **Built (2026-10-29):** P0-E-1 (split in `eval/split.yaml`, sampler, sets, the golden
store, `ci golden`) and P0-E-2a (equivalence, alignment, agreement; S0 parity exact). Not started:
E2b (scoring; replaces O1's `evaluate.score` stub), E3. Part of the [phase 0 series](../phase-0_2026-10-28.md), which
owns shared decisions, contracts, the dependency graph and build findings.
**Revised:** 2026-10-28, for the [domain-model alignment review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md) and its
[target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md) ("TM"), following coordinator decisions 2, 16, 19, 20 and 22: re-location adds a
citation-frame version with a parent link instead of rewriting a frame, golden items are keyed by
their derivation, and golden passes carry `payload_schema_id` (E1; [DA-009](../../design_review/audit/semantic-model-and-authority.md#da-009)); scoring
reads the run as of its cut, records the key scheme, maps keys across schemes only through the
carry-over map, and may run its set steps in pool and interchange's engine (E2b). Prerequisites
follow [coordinator §7](../phase-0_2026-10-28.md#7-dependencies-and-readiness).

This document builds `evaluate/` and its `ci` groups (`ci golden`, `ci eval`, `ci digest`,
`ci promote`; coordinator §3 decision 10) for D9 §5 P0.10 and the golden part of P0.11. It carries
the build half of P0CL-03 for goldens, P0CL-08's E2a/E2b split, P0CL-09's packet count, P0CL-10's
readings and unit-level forcing, P0CL-16's test protection, and the review's Observation 6
(`golden_snapshot`) from the
[contract-layer review](../../design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md).
The design owner of everything here is [D7](../../design/D7-evaluation-goldens-outer-loop.md), with
its tables in [D3 §7](../../design/D3-database.md) and its commands in
[D8 §4](../../design/D8-agent-and-query-interfaces.md); golden authorship is
[ADR-0011](../../adr/0011-golden-author-and-annotator-inputs.md).

## 1. What this document builds

**Responsibilities.**

- **Split, sets and the golden store (E1).** The page split; golden sets sampled with the trace
  and core units forced into dev; each set's golden run and its pass A and B tasks; the one owner
  of `eval.golden_*` writes, through the repository's primitives (P0-F-4); golden items derived
  per pass, rendition, cascade version and schema version; staleness, and re-location as a new
  frame version; when a golden run finishes; the golden-unit list behind the `phase0-golden` scope.
- **Alignment (E2a).** Two claim sets of one unit on one rendition, aligned at the D7 §5.3 tiers
  with tiered value equivalence; the A/B agreement record and the diff pass C reads.
- **Scores and the operator's readings (E2b).** Run scoring with intervals, as of the run's cut and
  under its key scheme, the `evaluate` stage's method, `ci eval`; the pre-registered promotion
  readings and `ci promote`; live-run answers for the gate; digest v0.
- **Dev goldens (E3).** Authoring the dev set by the Sonnet protocol through the golden tools; the
  exact `phase0-golden` packet count; the ceiling; the v1 reference as witness; the OPEN-D7-5
  comparison.

**Where they end.** The golden server, its tools, the `golden.pass` method, the golden-mode
packet, the alignment process inside the golden server and the work-queue skill are the agent
interface's (A2). This document provides what they call. Slice resolution, runs, tasks, leases
and fates are orchestration's; E1 supplies the unit list that orchestration resolves. The stored
form of a batch is A0's cascade, keys and canonical forms are foundations', and the grammar is
ingest and math's. Consolidation and the typed queries belong to consolidation and queries. The
golden and frame-version tables are generated from `system` (model and projections, P0-M-1,
P0-M-2), and the payload-schema registry is P0-M-4's; the cut is orchestration's (P0-O-1); the
in-process engine is pool and interchange's (P0-P-2).
Outside phase 0: experiments and `ci experiment` (D7 §7 items 1–4, phase 1), the PPI audit
(phase 2), and the author-markup, computation and reference-facts witnesses (which need ablation
runs, M21 and the reference pack). Test goldens are sampled but not authored (§3.12).

**The phase 0 extraction scope and its size.** The operator chose a unit-level scope on
2026-10-28: the four spike pages whole (LocationScale, Normal, LogNormal, Gamma; 208 annotation
units, which hold the trace and core units) plus each dev golden unit by its unit locator
(coordinator §3 decision 9, D2 §12.2). D6 §7.4 records the whole-page alternative as rejected. A
simulation of D7 §3.1's split and sampler on S1's segmentation showed why a page-level scope would
not do:

| Scope | Pages | Packets: median (5–95 %) over 500 seeds |
|---|---|---|
| Full first pass, test and reserved pages excluded | about 66 | 3,826 (3,709–3,945); D6 §7.4 says about 3,800 |
| Whole pages: the dev golden units' pages, the forced-dev pages and the spike pages | 26 (22–29) | 1,655 (1,405–1,914) |
| **Chosen:** the spike pages whole plus the dev golden units by locator | 4 pages + 22–27 units | **234 (231–235)** |

*Measured by simulation (2026-10-28).*
- **Inputs:** S1's segmentation (`results/s1/sizes.tsv`, 4,509 annotation units on the 78
  first-pass pages, 58 per page on average) and the corpus index's chapters.
- **Rules:** §3.1–§3.2's realization of D7 §3.1, with dev size 40 and the 13 trace and `core12`
  locators forced.
- **Seeds:** seeds 0–499, one per split and sampling pair.
- **Limit:** S1 segment keys stand in for unit keys, so the figures are a distribution, not the
  exact count.

The script is to be filed with the phase 0 evidence (`2026-10-28_phase0-golden-size/`). The
`spike-pages` run already works the 208 spike-page packets, and `phase0-golden` runs reuse them
by content digest, so the agent's added work for the first pass is the 22–27 golden units off
the spike pages. E3 computes the exact count (§3.4).

**Change scenarios.**

- **A second domain pack.** Evaluation reads the following from the pack and the compiled schema
  and names no statistics class or predicate:
  - class scope and `ci:identity_keys`;
  - each predicate's identity qualifiers and qualifier kinds;
  - the alias rules;
  - its split inputs and baselines.

  The spike's `FamilyParameter` pass becomes a pass over identity-dependent classes in general
  (§3.5). Only a pack's own `eval/` files are new.
- **A table segment with quantities.** Numbers compare as canonical decimals with units as
  written. When pint joins with M12 in phase 1, only the comparator's number tier changes.
- **A claim with `valid_time` and attribution.** Both are identity qualifiers (decision 14), so
  the full tier compares them key by key through the schema lookup, intervals endpoint by
  endpoint, with no change to evaluation.
- **An email thread's segment kinds.** A golden unit is an annotation unit (D1 §3.4). The sampler
  draws from the same enumeration of annotation units that the `propose` stage selects from
  (§8, open point 5), so a new source profile's unit kinds reach sampling unchanged.
- **Guideline v2 at the phase 0 boundary.** Affected units become `stale` and are re-authored in
  a new authoring round (§3.3). Results keep the pass-C ids they scored (`golden_snapshot`), so
  earlier results remain readable.
- **A key-scheme change** (decision 20). Goldens carry no keys, so alignment is unaffected. Each
  result records its run's key scheme, and a comparison of two runs under different schemes maps
  keys through the carry-over map, never by recomputation (§3.7).

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (document · package; design) | Used by |
|---|---|---|
| Package, settings, Typer app and its registration, conftest and database fixtures | foundations · F1 (D9 §1, §3) | all |
| Canonical value forms, condition canonicalization, the symbol rule, label normalization; stored-item and citation-frame models; `RenditionContent` | foundations · F2a, F2b (D1 §6.2, §7, §10.1, §10.3; D2 §7.3) | E1, E2a |
| Locator generator, resolver and refusal; the unit key | ingest and math · I0 (D1 §3.4) | E1, E2b |
| The `eval`, `kb` and `ops` tables. They include `eval.golden_set.sampling`, the split's seed and reason, the `promotion` intervention kind, `payload_schema_id` on `eval.golden_pass`, and the frame-version rows (generated from `system` by model and projections, P0-M-2). Also the repository, `kb.run_rendition` and `kb.run_observation` | foundations · F4 (D3 §4, §7, §8, as amended; §7's frame versions at P0-D-1) | E1, E2b |
| The payload-schema registry and reader dispatch (an unknown id refused) | ADR-0022; TM §9 · [model and projections](model-and-projections.md) P0-M-4 | E1 (passes and frames), E2b (reading proposal payloads) |
| The run's cut `ops.run.cut_at` (fates `finished_at <= cut_at`) and its recorded key scheme | D6 §3.1, D3 §8 as amended at P0-D-2; coordinator decision 16 · orchestration P0-O-1 | E2b |
| The key scheme and the carry-over map (translation T8) | D1 §10.1, §10.3; ADR-0023; coordinator decision 20 · foundations P0-F-2d, P0-F-2e | E2b |
| The engine interface over Arrow relations: DuckDB 2.0 in process beside a Python reference, set-equal | ADR-0021; TM §10; coordinator decision 22 · [pool and interchange](pool-and-interchange.md) P0-P-1, P0-P-2 | E2b (candidate pairs, run diffs, score aggregates), optionally |
| Renditions, annotation units, sentences, author markup, M02 math share and macro tables, as functions and as a run recorded them | ingest and math · I1a, I1b (D4 M01–M03) | E1 (strata), E2a (macros) |
| The grammar's reading of a value under a declared kind, its SymPy value, the time limit and the main-thread guard | ingest and math · I2a (D4 M11; ADR-0012) | E2a |
| The quote cascade: authored batch and citation frame to stored form on a rendition, with its cascade version, typed frame outcomes (`FrameFailureReason`) and re-location reported, never written | agent interface · A0 (D4 §4.3) | E1, E2a, E2b, E3 |
| Compiled schema lookup: class scope, `ci:identity_keys`, per-predicate identity qualifiers, qualifier and map-value kinds. Also the pack's worked examples `reference/E*`, whose pages are reserved | schema and rules · S1 (D2 §3, §7, §7.5) | E1, E2a |
| Projects and documents (`kb.document.meta` chapter and `first_pass`); runs and task creation; the method-contract types and registry; pack configuration (`aliases`, `math`); fates as of the run's cut | orchestration · O0, O1 (D4 §1; D6 §1–§4; D3 §4, §8) | E1, E2b |
| Declared slices (`trace`, `core12`, stored as `ops.debug_slice` rows); slice resolution with the `{golden_set: <label>}` include; the run's recorded `scope` | orchestration: P0-O-1 stores the declared slices (pack-version upsert); P0-O-2 resolves slices and scope (D2 §12.2, D6 §8) | E1 (the forced units, read from the stored rows; its tests write their own rows, so the package needs no O2 code), E2b, E3 (packet count) |
| Materialized claims, entities, statements and evidence; statuses; `completeness.evidence_coarse`; M19 warning outcomes | consolidation and queries · C1 (D5 §5.6, §8, §11) | E2b |
| Typed queries with the run selector | consolidation and queries · C2 (D8 §5) | E2b |
| The submission harness `intervene.testing`, which C3 uses and which runs outside pytest | agent interface · A1 (D8 §2.1; D9 §4) | E2b (live-run answers) |
| `golden.pass`, the golden server and tools, its alignment process, the golden agent file and work-queue skill. `write_golden` stores passes and E2a's agreement result through the golden store (§3.3), and under a lock on the `eval.golden_unit` row creates exactly one pass-C task. The profile `--variant page-text` serves the page text, leases nothing and stores no pass | agent interface · A2 (D8 §2.2, §3; D3 §8) | E3 |
| `fixtures/s0`: the v1 reference for the 13 annotation units of `core12` | foundations · F3 (D9 §1) | E3 |
| Evidence: `s0.agreement`, `s0.instruments`, `s0r2.scores`, `s0r2.reference-v1`; the [interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §5 and its probe P3 | spike series; library research | tests, baselines |

### 2.2 Produced

| Contract | Design owner | Implemented here | Consumers |
|---|---|---|---|
| Page split | D7 §3.1, §4; D3 §7 | `ci golden split`; `eval.document_split`; a split lookup | E1; agent interface's example exclusion (phase 1); digest |
| Golden sets and units; each set's golden run with its A/B tasks; golden-run settlement | D7 §3.1; D3 §7, §8 | `ci golden create --label`, `ci golden status` | A2 (`golden_next`), O2, E2b, E3 |
| The golden store: passes with `payload_schema_id`, frame versions, agreement record, adjudication, items per (pass, rendition, cascade version, schema version), staleness and re-location | D7 §3.2–§3.5; D3 §7 | `evaluate/goldens.py` | A2 (`write_golden`, `read_golden_unit`), E2b, E3 |
| The unit list of a golden set, with its hash | D2 §12.2; D7 §3.1 | `golden_units(project, label)` | O2 (slice resolution), E3 (packet count) |
| Alignment and value equivalence | D7 §5.2, §5.3 | `evaluate/align.py`, `evaluate/equivalence.py` | A2's alignment process, E2b, E3, A3 |
| Agreement and the pass-C diff: one result model, stored whole as the unit's agreement | D7 §3.3, §3.4; D3 §7 | `unit_agreement` and its result model | A2 (computes and stores it), E1, E2b (digest) |
| Run scores with intervals; the `evaluate` stage's method | D7 §5.1, §5.4; D6 §2 | `evaluate.score`, `ci eval`, `eval.alignment`, `eval.result` | operator, orchestration, readings, digest |
| Pre-registered readings and promotion | D7 §7 item 5; D3 §8 | `ci promote`; `domains/statistics/eval/baselines.yaml` | operator; the gate |
| Live-run answers | D7 §9; D9 §4 | `evaluate/answers.py` | the gate |
| Digest v0 | D7 §8.1; D8 §4 | `ci digest` | operator |
| The adjudicated dev set, the ceiling, the v1 witness, OPEN-D7-5 | D7 §3, §6, §10; ADR-0011 | E3 | E2b, the gate, A3, phase 1 examples |

## 3. Design of the parts

### 3.1 The split (E1)

`ci golden split [--seed K]` assigns every registered document of the project once, in one
transaction (D7 §3.1):

1. **Reserved:** the pages of the pack's worked examples, read from the examples' citation frames
   through S1's loader (statistics v1: `special/Weibull.html`). These pages are in no split.
2. **Forced dev:** the pages the pack declares in `eval/split.yaml` under `forced_dev`, each with
   its reason (the four spike pages, `special/Pareto.html` and `special/ChiSquare.html`). A page
   that is both reserved and forced is refused.
3. **Hash:** every other document. Documents are grouped by chapter (`kb.document.meta.chapter`,
   documents without one forming one group) and ordered by `sha256(source_uri + str(seed))`, with
   `source_uri` as stored and UTF-8 encoded. Within each group the 5th, 10th, … pages (0-based
   index mod 5 = 4) go to test and the rest to dev.

Each row records the seed and its reason (`reserved`, `forced_dev`, `hash`). The default seed is
in `eval/split.yaml`. Existing rows never change. A document registered later is placed by rule 3
among its chapter's unassigned documents, so a new page cannot move an assigned one between
splits. A pack change that contradicts an existing row (a page newly forced but already in test)
is refused and reported. Reassignment is an operator direction (D7 §3.1), outside phase 0.
**Proposed** (2026-10-28).

### 3.2 Sets, the sampler and the golden run (E1)

The command is `ci golden create --split S --label L [--size N] [--seed K] [--from-run RUN]`.
D7 §3.1 gives the protocol; the realization below fixes what D7 leaves open. **Proposed**
(2026-10-28).

- **Source run.** `RUN` defaults to the latest finished run whose `scope` stage covered every
  first-pass document. The sampler reads from it:
  - the selected renditions (`kb.run_rendition`);
  - the annotation units and author markup;
  - the M02 math shares (`ops.measurement`, read through reuse);
  - its M13 output.

  The golden packets read the same run, which becomes the golden run's `parent_run_id`. An
  `ingest` run is refused because it has no M13 output (§8, open point 1).
- **Pool.** The pool is the claim-bearing annotation units of S's pages among the first-pass
  documents, on `RUN`'s renditions. The statement kind comes from author markup through the
  source profile, else `narrative`; `proof` and `solution` are excluded (D2 §3.3). Each unit is
  named by I0's generated locator, its unit key.
- **Forced units** (dev only). The `trace` and `core12` slice locators (`ops.debug_slice`) are
  resolved with I0 on `RUN`'s renditions; a refusal fails the command. That gives 13 annotation
  units, because T1 is two.
- **Strata.** Statement kind × math-share tercile. The cut points are the pool's ⅓ and ⅔ order
  statistics, and they are recorded.
- **Allocation.**
  - Each stratum gets N × its share of the pool, floored, with at least one place per non-empty
    stratum; remaining places go by largest remainder.
  - Forced units count towards their strata. Where they exceed a quota, the excess comes from the
    stratum furthest above its exact share, never below max(1, its forced count).
  - More forced units than N is refused.
- **Order.** Within a stratum, units are taken in order of `sha256(unit_key + str(seed))`,
  skipping forced units. Because the unit key is a locator, the sample survives
  content-preserving ingest changes.
- **Writes, in one transaction:**
  - `eval.golden_set`: label, split, the frozen schema and guideline versions, and `sampling`
    (seed, size, cut points, allocation per stratum, forced unit keys, sampler version, source
    run);
  - `eval.golden_unit` rows (`draft`, `authored_rendition_id` from `RUN`);
  - the golden run (`ops.run` kind `golden`, `parent_run_id` = `RUN`, the set's versions, status
    `awaiting_agent`);
  - one `golden.pass/a` and one `golden.pass/b` task per unit (`unit_type 'golden_unit'`),
    created through orchestration's task creation, so their digests come from the agent
    interface's `golden.pass` method and their leases from the one queue (decision 4).

  E1 depends on the registry interface, not on A2. Its tests register a test method under that
  name.
- **Settlement.** `settle_golden_run(run)` sets the golden run `finished`, with `finished_at`,
  when every unit of its set is `adjudicated`. A2 calls it in the transaction that writes a
  pass C, and `ci golden status` calls it too. A run with any `draft` or `stale` unit is not
  finished.
- **Sizes.** Dev 40 and test 40 (D7 §3.1); `UNIQUE (project, label, split)` refuses a reused
  label.

### 3.3 The golden store: passes, items, staleness (E1)

`evaluate/goldens.py` is the only module that writes `eval.golden_*` rows, and it writes them
through the repository's primitives (P0-F-4: `store_golden_pass`, `set_golden_unit` and the bulk
helpers). A2 calls it inside its own transactions. The functions:

- `record_pass` writes the authored batch, its citation frame as the pass's first frame version,
  decisions, session reference, model and inputs (D3 §7), unique per (unit, pass, guideline
  version). Batch and frame carry the `payload_schema_id` of their registered payload classes
  (P0-M-4; [R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06), TM §9), so a reader dispatches by the recorded schema and refuses an
  unknown one. The session check between passes A and B is A2's.
- `record_agreement` stores E2a's whole agreement result on the unit (§3.6), validated against
  E2a's model at this boundary. `mark_adjudicated` follows pass C. The lock on the
  `eval.golden_unit` row, which ensures that concurrent A and B writes create exactly one pass-C
  task, is `write_golden`'s (A2).
- `ensure_items(pass_c, rendition, schema_version)` derives a unit's golden items. Items are keyed
  by pass, rendition, cascade version and schema version ([R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06); DA-009): the cascade
  version is A0's, and the schema version is the one whose compiled names derive the stored form
  (the golden set's frozen version in phase 0). If items under that key are absent, it resolves the
  pass's frame versions on the rendition (below) and derives the stored form from pass C's batch and
  the newest frame version that resolves, with A0's cascade. It writes one `eval.golden_item` per
  entity, statement, claim, alternative group and `unsupported` item, each recording the frame
  version it came from.
  - `context` is set on a context premise of this unit: an `assumption` statement anchored only at
    `cN` sentences, or a premise claim whose evidence cites only `cN` sentences (D2 §10.2). Such
    items are scored only through the `claim` nodes that reference them (D7 §5.1).
  - An unlocated golden quote gets a coarse span over its cited sentence, as proposals do
    (D4 §4.3, D5 §5.6). It is counted per unit in `ci golden status`.
  - Items are never edited (D3 §7). `write_golden` derives none.
- **Frame resolution.** `frame_status(pass, rendition)` resolves the pass's frame versions through
  A0's frame resolution (foundations' `resolve_frame` on I0's resolver), whose outcomes carry
  `FrameFailureReason` codes. Evaluation keeps no resolver or re-location rule of its own.
- **Staleness and re-location (D7 §3.5).** A frame that does not resolve marks the unit `stale`,
  and nothing is derived.
  - Re-location is A0's rule: each cited sentence's recorded text must occur in exactly one
    sentence of the page on the new rendition, and A0 reports the locator I0's generator gives it.
  - On success E1 **adds a frame version** to each of the unit's passes, in one transaction: the
    new locators with the recorded texts unchanged, a parent link to the version it re-located, the
    rendition it was re-located onto and its `payload_schema_id`. No frame is rewritten in place, so
    a result whose `golden_snapshot` scored the unit, and the items derived from the earlier
    version, stay exactly as they were (coordinator decision 2; [R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06); D3 §7 as amended at
    P0-D-1, replacing its "re-location rewrites only the frame's locators"). It then derives the
    items, updates the unit's `current_locator` (D3 §7) and returns the unit to `adjudicated`.
  - Otherwise the unit stays `stale` for re-authoring by the full protocol, in a new authoring
    round (§8, open point 4).

  Re-location never resolves to a nearest match.

A unit whose own key is refused on a run's rendition is handled the same way, through its frame's
unit sentences (§8, open point 3). A content-preserving ingest change triggers nothing: it keeps
the rendition row (D1 §3.1), so the existing items serve. **Proposed** (2026-10-28; P0CL-03).

### 3.4 The `phase0-golden` unit list (E1) and its packet count (E3)

`golden_units(project, label)` returns the set's unit keys (status not `retired`), sorted, and the
sha256 of their newline-joined list. Orchestration resolves the slice's `{golden_set: <label>}`
include with it at run start and records the list and hash in the run's `scope` option (D2 §12.2,
D6 §8). Every key in it lies on a dev page, which the function asserts. A key that a run's
rendition refuses fails that run's start under D6 §8's locator rule, naming the unit; re-location
(§3.3) or retirement is the remedy.

**The exact packet count (E3).** E3 adds the count to `ci golden status --label L`, which then
resolves `phase0-golden` exactly as orchestration does: through O2's resolver, on the source run's
renditions. It prints the number
of distinct claim-bearing annotation units selected: the spike pages' units together with the
golden units. That is the number of `propose` tasks (M24, `awaiting_agent` or `reused`) a
`phase0-golden` run over those renditions creates. The closure check for P0CL-09 is that the
first `phase0-golden` run's `propose` task count equals the printed figure, recorded with the run
id at qualification. The expected value is §1's, about 234 (231–235). **Proposed** (2026-10-28).

### 3.5 Alignment (E2a)

**Sides.** An `AlignmentSide` is one golden unit's claim set on one rendition:

- entities: type, scope, label and aliases, symbol, identity, scope segment;
- statements: kind and anchor spans;
- claims, as F2b's stored items: predicate, subject, object value or reference, qualifiers with
  conditions, statement role, evidence spans with roles;
- alternative groups and `unsupported` spans;
- the unit's sentence spans;
- uncounted context items, kept for leaf matching.

E2a adapts stored-form batches (golden items, a derived pass); E2b adapts a run's materialized
rows. The alignment context is:

- S1's schema lookup;
- F2b's label normalization with the pack's `aliases`;
- the rendition's macro table under the pack's `math` fallback;
- a value comparator.

Sides and context are plain data, so the computation can run in another process. The spike's
behaviour is **Tested** in the instruments (record `s0.instruments`, hand alignment agreeing);
the product realization is **Proposed** (2026-10-28).

**Entities** (D7 §5.2). Types must be equal. The similarity rules are:

- *Statements.* By anchor overlap: 0.6 + 0.3 × overlap ratio, + 0.1 for equal kind.
- *Global entities.* An equal normalized label or alias scores 1.0, and equality after the alias
  rules 0.9. A fuzzy match never aligns: a rapidfuzz `token_sort_ratio` of 90 or more is recorded
  as a label near miss for the digest. The v0 global classes are named mathematical objects, where
  one word changes identity.
- *Identity-dependent classes.* These are classes whose `ci:identity_keys` name an entity-valued
  slot; for statistics, `FamilyParameter` with `family` (D2 §3.1).
  - They align in later passes, in the dependency order of those keys; a cycle is refused when
    the context is built.
  - Two such entities are identical when every referenced entity is aligned to its counterpart
    and the remaining identity keys are equal after normalization.
  - Differing names with aligned references count as an identity near miss.
- *Local entities.* The normalized symbol (F2b's symbol rule) scores 0.7, + 0.2 for the same
  scope segment. Labels after the article rule are used when neither side has a symbol. A scope
  mismatch stays alignable, so scope accuracy can be measured (D7 §5.2 as amended).
- *Tie-breaker.* + 0.05 when the entities' claim evidence overlaps.

**Assignment.** Similarities below the threshold (0.5) are set to zero *before*
`scipy.optimize.linear_sum_assignment(sim, maximize=True)`, and zero-weight pairs are dropped
after. A weak pair therefore cannot displace a strong one (interfaces note §5.1: on
`[[0.5, 0], [0.98, 0.49]]` masking keeps `(1, 0)` at 0.98; assigning first keeps `(0, 0)`).

**Claims** (D7 §5.3).

- *Tiers.* Core: predicate, aligned subject, and an aligned object or an equivalent value. Full
  adds:
  - modality, polarity and statement role;
  - each identity qualifier from the lookup: maps key by key, entity qualifiers by alignment,
    condition-valued qualifiers by tree equivalence;
  - conditions, compared as F2b-canonical trees with their leaves matched one-to-one (values by
    equivalence, `claim` leaves through the claim matching, `phrase` leaves by span overlap or
    text).

  Evidence adds primary-span overlap or the same sentence.
- *Fixed point.* Leaf equality depends on the matching, so the core matching is found by
  fixed-point iteration. Pass 0 accepts any core-compatible premise pair; later passes judge
  leaves through the current matching. There are at most 8 passes, and non-convergence is
  recorded. The full tier, the evidence tier and the diagnostics use the final matching. A
  conclusion failing the full tier only because its premise failed the core tier is listed as
  *cascaded*.
- *Matching.* Each tier maximizes the number of matches. The core matching prefers, in order: more
  core pairs, more full-compatible pairs, more evidence-compatible pairs, then larger evidence
  overlap. Its weights are b³, b², b and the overlap ratio, with b = min(|R|, |P|) + 1, so lower
  terms can never outweigh one unit of a higher term at any unit size. This replaces fixed powers
  of ten (IE-6).
- *Groups and unsupported items.* An alternative group is `matched`, `ambiguity_collapsed` or
  `unmatched`. `unsupported` items match by the maximum number of overlapping pairs.
- *Diagnostics.* Field failures per core pair, binding correctness per symbol of aligned formula
  values, scope pairs and near misses.

**Value equivalence** (`evaluate/equivalence.py`; D7 §5.3, OPEN-D7-2). Each comparison records the
tier that decided it:

1. **Canonical.** F2b's canonical forms:
   - formulas and sets by token form;
   - numbers as typed canonical decimals with units as written (pint joins in phase 1);
   - text NFC and casefolded; dates ISO verbatim;
   - intervals by their endpoints and inclusivity;
   - references by entity alignment.
2. **Symbolic.** I2a's reading of each value under its slot's kind (formula, then relation, then
   member; `set_expr` for sets), with the binding map's symbols declared as variables. The SymPy
   value comes from the grammar's transformer. Equality is `simplify(a − b) == 0` under a time
   limit, with:
   - equations compared up to sign;
   - relations after rewriting `>` as `<`;
   - sets by an empty symmetric difference;
   - memberships and chains structurally.

   No SymPy value is stored: M11's conversion output is phase 1, and consolidation's SymPy fusion
   too (D5 §11).
3. **Numeric.** Values are evaluated at points satisfying the claims' top-level `member` and
   `cmp` conditions, by rejection sampling from `np.random.default_rng(seed)`. The seed is the
   sha256 of the sorted pair of canonical value forms plus the canonical conditions. Goldens carry
   no keys, and the result is independent of argument order. At least six distinct valid points
   are needed to decide, with relative tolerance 1e-9.
4. **Undecided.** Counted as unequal. Each undecided comparison is logged with the pair, the reason
   and the grammar status, and counted in the result detail and the digest. There is no manual
   tier.

Results are cached per comparator by canonical pair, canonical conditions and declared variables.

**Where it runs.** Tiers 2 and 3 use the grammar and SymPy under `setitimer` time limits, so they
run only on a process's main thread. The grammar raises off it, and the comparator checks the
same guard before `simplify`. `ci eval`, the `evaluate` stage (a `cpu` worker process) and the
golden server's single-worker alignment process (D8 §2.2 as amended; D4 M11) satisfy the guard.
The main MCP server never calls E2a. **Proposed** (2026-10-28).

### 3.6 Agreement and the pass-C diff (E2a)

`unit_agreement(pass_a, pass_b, rendition, context)` works in four steps:

1. Derive both passes' stored forms on the unit's current rendition with A0, in memory, since
   golden items project only pass C.
2. Align A as reference against B, and the reverse.
3. Count items per predicate and tier. An alternative group is one item, and context items are
   not counted.
4. Symmetrize: per tier, take the mean of the two directions' F1, flagging any asymmetry
   (D7 §3.3).

It returns one result model, owned by E2a, with two parts:

- the agreement counts and symmetrized F1 per predicate and tier;
- the diff for pass C (D7 §3.4): matched, A-only, B-only, and matched with qualifier differences
  (core pairs failing the full tier, with their fields). Each entry carries local references into
  both passes; A2 renders it into the packet.

`write_golden` stores the whole result as the unit's `agreement`, through `record_agreement`, in
the transaction that writes the second blind pass. `read_golden_unit` for pass C serves the
stored diff, so the diff is computed once. Every reader (A2, `ci golden status`, the digest)
validates the stored JSON against the model, so a model change surfaces at that boundary.
`ci golden status` aggregates the ceiling per predicate over adjudicated units. Inputs and outputs
are plain data, for the alignment process. **Proposed** (2026-10-28).

### 3.7 Run scoring and intervals (E2b)

**What is scored.** The run's golden set is the given label, or else the dev set of the run's
guideline version. Only its `adjudicated` units in the run's scope are scored: the slice, the
recorded scope list, or all units.

**As of the cut** (coordinator decision 16; [R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08); DA-024). The run is read as of
`ops.run.cut_at`, which orchestration seals in a short transaction before the final pass: the
materialized rows the final pass wrote from the pool as of the cut, the proposals' `unsupported`
items through `kb.run_observation` as of the cut, and fates with `finished_at <= cut_at`. The
`evaluate` stage runs after the seal over rows that no longer change, and a completion stamped after
the cut is unresolved for the run, so a score never includes work the run did not consolidate. The run's own finalize-stage outputs (M19 verifications, `rules.evaluated` measurements) finish
after the cut, so the rule-warning reading selects them by the sealed `ops.run.cut_m19_task_id`
(coordinator decision 16; DA-015), not through the cut views.

For each unit, scoring follows D7 §5.1:

- The unit key is resolved on the run's selected rendition (`kb.run_rendition`) with I0. A
  refusal hands the unit to E1's staleness handling, and the unit is excluded and counted.
- `ensure_items` provides the golden side on that rendition.
- The predicted side is the run's claims whose primary evidence lies in the resolved segment, or
  whose statement is anchored there (`kb.claim_evidence`, `kb.entity_anchor`). It also carries:
  - the run claims their `claim` leaves reference, uncounted, for leaf matching;
  - their entities and the unit's statements and alternative groups;
  - the `unsupported` items of the unit's proposals, read through `kb.run_observation` and
    located on the run's rendition with A0.

**Where the set steps run** (coordinator decision 22; TM §10; [R09](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r09)). Candidate pairs
(golden × run entities and claims of a unit, filtered by type before similarity), run diffs and
score aggregates are joins and group-bys, so E2b may run them in pool and interchange's in-process
DuckDB engine over Arrow relations, through P0-P-2's interface (built before E2b, since C1 needs
it). Similarity, the masking, `linear_sum_assignment` and the bootstrap stay in Python, NumPy and
SciPy. Every aggregate that feeds a float sums in key order on both paths (`sum(x ORDER BY key)` in
the engine), so a score is the same bit for bit on either; if the engine path is used, it is tested
set-equal to the Python path on the same fixtures. Phase 0's dev set of 40 units needs nothing beyond
the Python path, so using the engine there is a choice (§8), not a requirement.

Two readings are scored: *strict* (`accepted`) and *lenient* (`accepted`, `candidate`,
`ambiguous`). The precision–recall curve and calibration wait for a confidence model; derived
correctness waits for derived claims (D5 §11 row 0).

**Scores** (D7 §5.4):

- precision, recall and F1 per tier, micro and macro over predicates, and per predicate,
  statement kind and chapter;
- unsupported recall, binding accuracy and scope accuracy;
- identity quality;
- counts of undecided equivalences, excluded units and cascaded pairs.

Identity quality is B-cubed, which is new code with no spike counterpart:

- Mentions are the golden global-entity references across the scored units.
- G(m) is the golden cluster: class and normalized canonical label.
- R(m) is the run entity key aligned to m, or m itself when unaligned.
- Precision is the mean over mentions of |G(m) ∩ R(m)| / |R(m)|; recall is the mean of
  |G(m) ∩ R(m)| / |G(m)|.
- A merge is a run cluster spanning several golden clusters; a split is a golden cluster spanning
  several run clusters. Both are counted.

**Intervals** (D7 §5.4; interfaces note §5.2, **Tested** by P3 for parity with the S0 intervals,
2026-10-28). The call is `scipy.stats.bootstrap((n_ref, n_pred, matched_ref, matched_pred), stat,
paired=True, vectorized=True, method="percentile", n_resamples=1000, rng=np.random.default_rng(seed),
axis=-1)`.

- The statistics are ratios of sums over the resampled units, with predicates batched on a leading
  axis.
- The interval is `np.nanpercentile(res.bootstrap_distribution, [2.5, 97.5], axis=-1)`, with the
  share of undefined resamples reported. SciPy's own interval turns NaN when any resample is
  undefined.
- The unit order is the sorted unit keys, recorded with the seed and the NumPy and SciPy versions,
  because order is part of the result.
- `rng` is passed by keyword as a `Generator` (SPEC 7; Context7, SciPy docs, 2026-10-28).
- Macro F1 and B-cubed are not ratios of per-unit sums. They use `vectorized=False` over the same
  resampled units.
- Two runs are compared by the paired difference on shared units, with the share ≤ 0.
- Page-cluster intervals are available for reports.

**Persistence.** One transaction writes two kinds of row:

- `eval.alignment`: one row per golden item and tier it matched, or `none` with a null target.
- `eval.result`, whose `golden_snapshot` holds the sorted pass-C ids scored (Observation 6). Its
  detail holds the interval, the undefined share, the unit-order hash, the seed, the library
  versions, the reading, the undecided count and the run's key scheme.

Re-scoring adds rows, and readers take the latest per run and set. Re-scoring a kept run is
`ci eval RUN`, so phase 0 needs no `rescore` run kind.

**Keys and their scheme** (coordinator decision 20; [R02](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r02)). The keys an alignment or result
names are under its run's recorded key scheme, which the result records. Goldens carry no keys, so
scoring a run against goldens never depends on a scheme. Where E2b compares rows of two runs by key
(a run diff, the digest's changes), it compares within one scheme, or carries the earlier run's keys
and any judgment that names them through foundations' carry-over map (T8). A key with no
counterpart in the map is reported, never matched by recomputation or guess.

**Entry points.**

- `evaluate.score`: a run-level task of the `evaluate` stage, never reused. Its outcome is `empty`
  when no adjudicated unit is in scope.
- `ci eval [RUN] [--split dev|test] [--label L] [--json]` (D8 §4).

An all-undefined score is stored as a null value with its n, never as NaN. **Proposed**
(2026-10-28).

### 3.8 The pre-registered readings and `ci promote` (E2b)

These readings are fixed here, before any phase 0 result is seen (D7 §7 item 5; P0CL-10). They
inform the operator and set no threshold.

| Reading | Definition |
|---|---|
| Dev full-tier F1 | Micro, strict and lenient, with its 95 % percentile interval and n units (§3.7). It is shown beside the baselines in `domains/statistics/eval/baselines.yaml`, all from record `s0r2.scores`: `refv1_vs_a_full_f1` 0.676 and `refv1_vs_b_full_f1` 0.681 (Opus v0 passes against the v1 reference); `refv1_vs_sv_full_f1` 0.766 (Sonnet v1); `sv_vs_hv.held_out_full_f1` 0.759 (Sonnet against Haiku on held-out units, no reference). The dev set's own full-tier A/B ceiling is shown with them. The display states that these are other measurements, with other references, units and authors |
| Identity | B-cubed precision and recall of the run's global entities against the golden canonical labels, with merges and splits |
| Unlocated-quote rate | Evidence items left `evidence_unlocated` over all evidence items, in the M24 proposals of the run's in-scope units (`kb.run_observation` as of the cut, reused proposals included) |
| Rule-warning rate | Claims of the run with at least one M19 warning outcome, the `guideline:` group included, over the run's claims |

Coverage is shown beside them as context: eligible units, extracted, skipped by reason, and
unresolved as of the run's cut; dev units scored out of those adjudicated. Each `baselines.yaml`
entry carries its id, record, result name, value, label, units and reference. A test checks every
value against its record.

**`ci promote RUN`** refuses unless all of the following hold:

- the run is finished and of kind `full` (never `slice` or `golden`);
- no agent task is unresolved as of its cut (orchestration's fate reader, `finished_at <= cut_at`);
- it uses the golden set's schema and guideline versions.

If the run's latest dev result does not cover every adjudicated unit, the command scores the run
first. It then shows the readings and asks for confirmation (`--yes` for scripts and tests). On
confirmation, one transaction:

- sets `meta.project.promoted_run_id`;
- writes an `ops.intervention` of kind `promotion` (actor `human:operator`) whose refs hold the
  result ids, the readings as shown and the hash of the baselines file.

Declining writes nothing. **Proposed** (2026-10-28).

### 3.9 Live-run answers (E2b)

D7 §9 measures "answer their typed questions" for the live runs by aligning their typed-query rows
with expectations from the re-authored dev goldens (D9 §4 as amended). The steps:

1. **Expectation run.** A slice run over `core12` (13 units). Its proposals are those units'
   pass-C batches with their citation frames, submitted through the agent interface's submission
   harness `intervene.testing`, which C3 also uses and which runs outside pytest, and consolidated
   like any run.
2. **Isolation.** The expectation run's submissions must never settle, or be reused by, the live
   runs' agent tasks; the reverse would leak goldens into a scored run. Twins and reuse match on
   method configuration and input hash (D6 §4), so the expectation run proposes through a
   dedicated named M24 configuration (`agent.opus/expectation` in `methods.yaml`). How a run names
   it is §8 open point 2.
3. **Questions.** D8 §5.3's questions for the trace units, and `statement(locator)` for each core
   unit (D8 §5.3 as amended).
4. **Alignment.** For each question, the claims its rows cite on both runs are adapted by E2b's
   run-side adapter and aligned with E2a per unit.
5. **Report.** Per question: expected, returned and matched, per tier. They are stored as
   `eval.result` rows with `scope_type 'query'`, the query and its parameters as `scope_key`, and
   the pass-C ids in `golden_snapshot`. No threshold is set.

**Proposed** (2026-10-28).

### 3.10 Digest v0 (E2b)

`ci digest [--since RUN] [--json]` is read-only and bounded at 12,000 characters, about two pages
(D7 §8.1):

1. **Dev metric changes.** The latest scored run against the previous one of the same scope (or
   `--since`), with intervals and the paired difference on shared units. Units are paired by unit
   key, which no key scheme affects; a listing of changed claims compares keys as §3.7 states.
   Test metrics appear only at gates, in aggregate.
2. **Guideline versions** since then. The phase 0 freeze normally leaves this empty.
3. **Disagreement themes.** Pass-C decisions and A/B diffs grouped by predicate and by the guideline
   rule a decision cites, with up to three dev examples each (quote, the two readings, the reason).
4. **`guideline_gap` marks.**
5. **Coverage gaps.** `unsupported` items grouped by statement kind and predicate context, with
   counts and three examples. Clustering by text similarity waits for M04 (phase 1).
6. **Open proposals.** The D8 §2.3 tools are phase 1, so this lists pending re-authoring.
7. **Health.** Stale golden units, undecided equivalences, failed tasks, skipped units by reason,
   and label and identity near misses.

The MCP `digest` tool is phase 1 (D8 §2.4). **Proposed** (2026-10-28).

### 3.11 Dev goldens, the v1 witness and OPEN-D7-5 (E3)

**Authoring.** After `ci golden create --split dev --label L`, the Claude Code session works the
golden run through the work-queue skill. For each unit, a fresh Sonnet 5.5 subagent writes
pass A, another pass B, and a third pass C, each through its own golden server (agent interface;
ADR-0011). That is 120 sessions for 40 units. Every subagent's transcript is audited, tool call by
tool call (OPEN-D8-3's practice): it may use only the golden tools and its own inputs, never
another pass, run output or metric. The audit summary goes into the qualification evidence.

**The v1 witness** (D7 §6). The v1 reference (`fixtures/s0`, the 13 forced units) is derived on
the production rendition with A0. It is aligned with the same units' pass-C items both ways:
golden as reference, and pass against pass, symmetrized. Disagreements are listed per unit with
their failing fields, and each is read as a guideline gap or a golden error, with the reason
recorded. The result is an evidence record (ADR-0010), not an `eval.result` row, since no run is
involved. `evaluate/witnesses.py` declares the phase 0 witnesses and what disqualifies each:

- `cross_pass`: independent of the pipeline, not of the golden author;
- `spike_reference_v1`: independent of the golden author's passes, not of the guideline.

**OPEN-D7-5** (D7 §10). The golden server's profile `--variant page-text` (agent interface) serves
the golden-mode packet with the page's full text added. It leases nothing and stores no pass, so
the variant passes cannot enter the golden tables. The design:

- **Units.** 12 dev units from pages that are neither forced-dev nor spike pages.
- **Passes.** Two fresh Sonnet passes per unit with page text (T1, T2), 24 sessions.
- **Comparisons:**
  - T1–T2 agreement against the same units' A–B agreement (determinacy);
  - T against pass C, beside A and B against pass C, with paired-bootstrap intervals over units.
    Pass C was adjudicated from A and B, which favours them; this is stated with the figures
    (D7 §5.4's reading rule).
- **Pre-registered rule.** Page text is adopted, as a revisit of ADR-0011, only if the full-tier
  interval of (T vs C) − (A, B vs C) excludes zero in favour of text, and T–T agreement is not
  below A–B.
- **Storage.** The session writes each variant pass's batch and frame to the comparison's evidence
  folder. E3's driver aligns them with E2a, and the result is an evidence record.

**Proposed** (2026-10-28).

### 3.12 Test-split protection (D7 §4; P0CL-16)

- Test units route like any unit; protection is the training, fitting and example exclusion.
- E1's split lookup is what the agent interface's phase 1 example retrieval excludes by.
- Phase 0 authors no test golden. Test sets can be sampled, but their golden runs open in phase 1.
- No command prints a test golden item, alignment or error. `ci eval --split test` and the digest
  show aggregates only, at gates.
- The `phase0-golden` list holds only dev units, which `golden_units` asserts.

## 4. Ports

| Spike module (under `docs/design_review/evidence/2026-10-28_design-spikes/code/`) | Product module | Kept | Changed or dropped |
|---|---|---|---|
| `instruments/align.py` | `evaluate/align.py` (E2a) | Tiers; the fixed-point claim-leaf matching; the cascade list; alternatives; unsupported matching; binding and scope diagnostics; near misses; `describe` for hand checking | Thresholds before assignment; size-derived weights; the identity-key pass in place of the `FamilyParameter` pass; aliases and head words from the pack through F2b; stored-item models instead of dicts; the `FUZZY_TYPES` mechanism and the extra `*_nocascade` tiers dropped |
| `instruments/values.py` | `evaluate/equivalence.py` (E2a) | The canonical, symbolic and numeric tiers; relation, membership and set handling; the comparison log with its deciding tier; the cache | The canonical tier through F2b's forms (token form, typed decimals); the grammar through I2a; the numeric seed per pair from a NumPy `Generator`; undecided counted unequal. Dropped: `FALLBACK_MACROS`, `CONSTANTS` and `_UNITS` copies of pack data, pint, the manual TSV tier, the global `PARSE_LOG`, and `canonical_value` and `text_norm` (now F2b's) |
| `instruments/conditions.py` | `trees_equivalent` and the perfect leaf matching in `evaluate/equivalence.py` | Leaf matching rules | Canonicalization is F2b's |
| `instruments/scores.py` | `evaluate/scores.py` (E2b); item counting and `symmetrized` in E2a | Alternative group as one item; micro, macro and per-predicate PRF; unsupported recall; binding and scope accuracy; field breakdown | `scipy.stats.bootstrap` wrapper instead of the hand-written loop. Dropped: `kappas` (statsmodels is not a dependency, and D7 §5.4 has no kappa), `key_agreement` (spike keys), `write_tsv` |
| `instruments/schema_lookup.py`, `instruments/batch.py` | none | — | S1's lookup and F2b's models |
| `s0d_compare.py` | test-only side builder for the parity test | Side construction from `sample.json` and S1 segments | Not product code |
| `tests_instruments/test_align.py`, `test_values.py`, `fixtures.py` | `tests/evaluate/` | The §9 perturbation suite and the value cases (F1–F5), the T2/T3 stored models as hand-made fixtures | pint and manual-tier cases dropped |

**Known spike defects not ported:**

- `_assign` thresholds after assignment;
- lexicographic weights 1e6/1e3/1/1e-3, exact only below 1,000 candidates;
- statistics names and pack data in generic code;
- one fixed numeric seed for every comparison;
- tier 1 printed from the grammar's tree instead of the token form (ADR-0012);
- the manual tier.

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-E-1 | The split, sampler, sets and units, the golden run with its A/B tasks and its settlement, the golden store with `payload_schema_id`, items keyed by pass, rendition, cascade version and schema version, staleness, re-location as frame versions, `golden_units`; `ci golden split`, `create`, `status` | P0-F-4, P0-I-1a, P0-O-1, P0-A-0, P0-M-4 (P0-I-0 and P0-S-1 through them) | Same seed, same split and sample. The 13 forced units are in dev and counted towards their strata, with exactly N units. A set opens a golden run with 2N tasks, which finishes only when every unit is adjudicated. Items are derived per rendition with `context` flags, keyed by pass, rendition, cascade version and schema version, and a cascade-version change derives new items beside the old. A re-location writes a new frame version with a parent link and leaves the earlier version, its items and every result that scored it unchanged. Passes and frames carry `payload_schema_id`, and an unknown id is refused on read (DA-009). `golden_units` holds no test unit | A new paragraph before a golden unit: its frame resolves and items are re-derived at shifted offsets. An edit that lengthens a cited sentence's locator: an in-place rewrite would change the frame an earlier `golden_snapshot` scored, while a new version keeps it. An edit to a cited sentence marks the unit stale; re-location by recorded text fails, and re-authoring is required |
| P0-E-2a | Alignment, value equivalence, agreement and the pass-C diff | P0-F-2b, P0-S-1, P0-I-2a, P0-A-0 | The ported suite passes. S0 parity: aligning the spike's stored passes A and B (`results/s0/stored/pass_a`, `pass_b`) per S0 unit gives `s0.agreement`'s 0.933, 0.627 and 0.600, with S0's 13 recorded equivalence decisions supplied through a test-only decision input; the figures under the product rule and the pairs that differ are reported beside them. The identity-key pass aligns a toy class with no statistics names | Masking before assignment keeps the 0.98 pair in `[[0.5, 0], [0.98, 0.49]]`. A comparison called off the main thread raises |
| P0-E-2b | Scoring and intervals, `eval.alignment` and `eval.result`, `evaluate.score`, `ci eval`, the readings and `ci promote`, `baselines.yaml`, live-run answers, digest v0 | P0-C-1, P0-C-2, P0-E-2a, P0-A-1 (`intervene.testing`, for the answers) | Intervals reproduce the P3 figures in S0's recorded unit order (core 0.827064…–1.0, full 0.428544…–0.752607, evidence 0.367967…–0.746849) and differ in unit-key order. Every result carries `golden_snapshot`. `ci promote` refuses a slice run and a run with tasks unresolved as of its cut, and writes one `promotion` intervention when confirmed. A completion stamped after the cut is absent from the scored side and counted unresolved. Every result records its run's key scheme; a comparison across two schemes goes through the carry-over map. `baselines.yaml` values equal their records | A run whose evaluate stage sees no adjudicated unit records `empty`, not NaN. The expectation run's submissions leave the live run's awaiting tasks untouched. A run diff that recomputes earlier keys under the current scheme instead of carrying them over |
| P0-E-3 | Authoring the dev set, the exact `phase0-golden` packet count in `ci golden status`, the ceiling, the v1 witness, OPEN-D7-5 | P0-A-2, P0-F-3, P0-O-2 | 40 dev units `adjudicated` and the golden run `finished`. `ci golden status` prints the packet count, and the first `phase0-golden` run's `propose` task count equals it. Every pass records Sonnet and its inputs, A and B come from different server instances, and every transcript is audited. The ceiling is reported, the witness record written, and the OPEN-D7-5 record written with its decision | A subagent whose transcript shows it read another pass: that pass is discarded and re-run |

**Mechanisms and evidence per package.**

- **P0-E-1.** The repository and SQLAlchemy Core (F4); `hashlib.sha256`; I0's generator and
  resolver; A0's cascade, cascade version and frame resolution; M4's registry ids and reader
  dispatch; orchestration's task creation and registry interface. It consumes the
  `s6.*` records through F4's migration 0001 and `s1.corpus` and `s1.rendition-identity` through
  I1.
- **P0-E-2a.** `linear_sum_assignment(maximize=True)` with masking first (interfaces note §5.1);
  NumPy `default_rng` (§5.3); SymPy 1.14 `simplify` and sets (held, `docs/pins.md`); rapidfuzz
  `token_sort_ratio` for near-miss diagnostics only. It consumes `s0.instruments` and
  `s0.agreement` as test oracles, and `s4.*` (through S1's lookup), `s5.coverage` and
  `s5.keys-property` (through I2a and F2a).
- **P0-E-2b.** `scipy.stats.bootstrap` as in §3.7 (interfaces note §5.2, IE-5); the run's cut
  (O1); F2e's carry-over map; optionally P2's engine with ordered aggregates. It consumes
  `s0.agreement`, P3's recorded output and `s0r2.scores`.
- **P0-E-3.** ADR-0011's protocol; O2's resolver for the packet count. It consumes
  `s0r2.reference-v1`, `s0r2.inputs` and `s0r2.adjudication` as the comparison context.

## 6. Tests

All database tests use foundations' per-session test database, the compiled-schema fixture and
the trace slice fixture. Corpus-gated tests skip when `docs/statistics_corpus` is absent. The
parity tests read the tracked spike results as data and never import spike code (coordinator §13).

- **P0-E-1.**
  - Split determinism and its rules on a hand-made ten-page chapter: reserved and forced pages,
    every fifth to test, no reassignment when a page is added.
  - A Hypothesis property: permuting the input order of documents or units leaves split and
    sample unchanged.
  - Sampler allocation by hand on a small pool: minimum one per stratum, forced excess, refusal
    when forced exceeds N.
  - Golden-run creation and settlement with a test method; item derivation and the `context`
    flag on a T2-like unit with a context premise.
  - Frame resolution and re-location across three renditions: content-identical, an edit
    elsewhere, a changed cited sentence; a re-location adds frame version 2 with parent 1, and
    version 1, its items and a result that scored them are byte-for-byte unchanged.
  - Items keyed by derivation: a bumped cascade version derives a second item set beside the first.
  - The registry boundary: a pass whose `payload_schema_id` is unknown is refused on read.
- **P0-E-2a.**
  - The ported perturbation and value suites, with expected outcomes written from D7 §5.3, not
    from the aligner.
  - Hypothesis properties: swapping sides transposes the matching; permuting item order leaves it
    unchanged; numeric seeds do not depend on argument order.
  - The masking counterexample; weights on a unit with more than 1,000 candidates; undecided
    counted unequal; the main-thread guard.
  - The S0 parity test (§5).
- **P0-E-2b.**
  - Interval parity in both orders.
  - NaN-skipping against a hand-computed distribution on a three-unit case.
  - B-cubed on hand-made clusterings with values worked by hand.
  - `ci eval`, `ci promote` (with `CliRunner` input) and `ci digest` through Typer's `CliRunner`,
    stdout and stderr apart.
  - A digest over a test set prints no test item.
  - The expectation-run isolation test.
  - The cut: a completion stamped after `cut_at` is absent from the scored side and counted
    unresolved by `ci promote`'s check.
  - Key schemes: each result records its run's scheme; a fixture run pair under two schemes is
    compared through F2e's carry-over map, and a key the map lacks is reported.
  - If the engine path is used: set equality with the Python path on shuffled fixtures, and equal
    scores bit for bit.
- **P0-E-3.** The packet count equals the `propose` task count of a `phase0-golden` run on
  fixture pages (with O2). Authoring is operational: its checks are the acceptance queries above,
  the transcript audit and the two evidence records. A probe at A2 checks golden-server separation
  (the review's Observation 9) before the first pass.

## 7. Indicative size

| Package | Product lines (tests excluded) |
|---|---|
| P0-E-1 | 450 |
| P0-E-2a | 550 (the aligner about 300, equivalence about 200, agreement about 50) |
| P0-E-2b | 400 (scores and intervals 160, readings and promotion 60, answers 60, digest 120) |
| P0-E-3 | 100 (witness registry, witness and OPEN-D7-5 drivers) |
| **Total** | 1,500, the coordinator's budget |

The spike's `align.py`, `values.py`, `conditions.py` and `scores.py` are about 1,800 lines. The
port fits by dropping pack-data copies, the manual tier, pint, kappas and key agreement, and by
taking canonical forms from F2b.

## 8. Choices left to implementation, and open points

**Choices left to implementation:**

- module boundaries inside `evaluate/`;
- whether sides are frozen dataclasses or Pydantic models;
- the row layout of `eval.alignment` per tier;
- `describe`'s format;
- the digest's wording and grouping thresholds;
- CLI rendering and `--json` models;
- cache sizes;
- whether `ci golden status` gives the ceiling with intervals;
- whether E2b's candidate pairs, run diffs and aggregates run in P2's engine or in Python
  (set-equal either way, §3.7);
- the layout of a frame-version row beyond §3.3's fields, within D3 §7;
- the form of the test-only decision input used by the parity test, which no command or
  configuration reaches.

**Open points.** Each needs its owner's answer before the package named.

1. **The source run for `ci golden create` (P0-E-1; orchestration).** The golden packets need
   corpus-wide M13 output before the set exists, and the `phase0-golden` scope cannot start before
   it. Proposed: run the `spike-pages` qualification as a `complete` run of kind `full` scoped to
   `spike-pages`, which runs the base stages over the corpus but asks the agent only for the spike
   pages. That changes the qualification order's `spike-pages` slice run.
2. **Naming the expectation configuration for a run (P0-E-2b; orchestration, agent interface).**
   This needs a run option, or a policy entry, that routes `propose` to `agent.opus/expectation`.
3. **A golden unit whose own key moves (P0-E-1; D3 §7; orchestration).** An edit elsewhere on its
   page can lengthen its generated prefix (D1 §10.3). D3 §7 now keeps `unit_key` as the unit's
   identity and records the moved locator in `current_locator`, which re-location updates (§3.3).
   Open: whether `golden_units` hands orchestration the current locators for scope resolution, so a
   `phase0-golden` run on the new rendition does not refuse the old key (O2).
4. **Re-authoring rounds (P0-E-1; D3 §8).** D3 §8 says one golden run per set and guideline
   version. Proposed: one golden run per authoring round, so re-authoring stale units after the
   first run finished opens a second.
5. **The enumeration of annotation units (P0-E-1; ingest and math or foundations).** The sampler
   and the `propose` stage must select from one function. No package names its owner.
6. **`domains/statistics/eval/split.yaml` (P0-E-1; D2 §2).** This proposed file holds the
   forced-dev pages with their reasons and the split seed, beside `baselines.yaml`. The pack
   layout should name it.
