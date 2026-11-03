# M1 source population and initial family guidance

**2026-11-03. Tested:** read-only freezing of the retained five-view development source cut.
**Proposed:** `m1-statistics-pilot-guideline-1`, the family subsets and future release sampling below.
This is M1-01 evidence, not a second package-state owner. The
[coordinator](../../../plans/first-production-milestone_2026-11-03.md) owns completion and the
[evaluation companion](../../../plans/first-production-milestone/evaluation-qualification-and-gap-driven-expansion.md#M1-01)
owns the requested boundary. Baseline examined: `ae30daba41aec5b4b89fc2ce6a7a4872f46f1f56`.
The shared worker/executor contracts and execute-plan skill apply. No declarations were edited.

## Frozen source cut and what it establishes

The existing `selected_source_views` and `load_source_view(..., analysis=False)` readers loaded
the actual retained database sources. The connection set `SET TRANSACTION READ ONLY` and
`SHOW transaction_read_only` returned `on`. Only selected source views, published native source
records and their release/lineage, original document identity and the run identity were read.
No predictions, production knowledge output, reference answers or queued task bodies were read.
Run6 and tasks27–31 were not changed or claimed. No provider, GPU, PDF conversion, publication,
schema installation or persistent-default change ran.

[manifest.json](manifest.json) freezes the exact source/project/release/view/product/projection/
recipe pins, original PDF hash, per-view detached-content hash and artifact digests.
[sources.json.gz](sources.json.gz) contains retained text, pieces, native items, ancestry and
health once per view, compressed deterministically. It preserves text imperfections, table cells,
formula occurrences and native item provenance. It is a detached source snapshot, not a complete
copy of the database's recognition/reconciliation graph. Live source diagnostics remain addressed
by their original pin; the snapshot does not invent missing intake or recognition content.

| View | Retained section | Projection characters | Native items | Projection pieces |
| --- | --- | ---: | ---: | ---: |
| 1 | 1.1: Sets | 35,092 | 1,793 | 1,807 |
| 2 | 1.2: Functions | 32,790 | 2,359 | 2,363 |
| 3 | 1.3: Relations | 7,564 | 682 | 655 |
| 4 | 1.8: Combinatorial Structures | 29,141 | 1,472 | 1,613 |
| 5 | 5.6: The Normal Distribution | 19,923 | 840 | 872 |

All five views derive from document4, Siegrist `siegrist_random/Full_PDF/Full.pdf`, original
content hash `e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9`.
They share task6 / `integrated` /
`1882a372985949584bc3c15a3df8b2c6a9f21a1b610dd2b583cea70dc44975ac` and selected run6 release
`release:a13bbbd140a8586951a328a1fd261d17a2feb8a4810c3075243da0685bb3f9f7`.
The original identity was read from the database; this inventory does not re-hash or audit the
original PDF bytes. The lead selection file's digest is verified against the actual view pins.
The five analysis views are all intact descendant selections, not five independent documents.

Retained health says conversion `success`, display coverage `partial`, cell coverage `unknown`;
individual retained formula outcomes include `unknown`. These are source health observations,
not evidence that every original region or formula was faithfully recovered. Native item labels
are inventory cues, not record-family labels or reference readings.

## Denominators, sampling and isolation

[regions.jsonl](regions.jsonl) inventories **all 7,310 projection pieces**, including structural,
empty or unknown-labelled pieces. Every row has its view, source snapshot hash, original-origin
group, native pointer, exact original projection interval/text and text digest. Piece labels:
4,096 text, 1,003 formula, 372 list-item, 154 section-header, 11 caption, 6 picture, 5 table,
5 code, 2 footnote and 1,656 unknown. Five table-labelled pieces reference **one native table**;
piece counts must not be relabelled table counts, occurrence counts or fact counts. Native source
items can overlap/split projection pieces; preserve those memberships when authoring records.

[sample.json](sample.json) freezes seed `20261103` and a uniform sample without replacement
of 40 of these pieces, each inclusion probability `40/7310`. It separately lists the first two
pieces per observed label as a purposive development challenge cohort. The random sample is a
source-region inspection lead, not a full-record recall sample: overlapping semantic records can
touch several pieces, so naive record counting or inverse piece weighting would be wrong. For
each selected piece, the independent author must first define a coherent target region and bounded
context; target regions must then be reconciled to a disjoint eligible-region sampling frame,
with their actual selection probabilities, before reporting full-record prevalence/recall.
Keep zero-record and unsupported/unreadable target regions. Do not select only emitted records.

**Isolation decision for this pilot:** all five sections and all of their overlapping windows,
copies, table repetitions and related editions belong to one origin group, `pdf:<original hash>`.
All frozen inputs here are **development only** because their text was inspected during design.
Feature fitting, final-event calibration and final assessment partitions are empty. There is no
credible source-group-separated four-way split within this single book. A later within-book
chapter/section experiment requires an explicit evaluator partition extension and a within-book
claim; it must not be labelled independent-book evidence.

Release source population, independently sampled eligible-region population and original-page
coverage-audit population remain distinct and **unfrozen**. Freeze additional independent origins,
deduplication/edition groups, strata, source-unit sampling probabilities and the desired precision
claim before selecting the group-aware interval/sample-size procedure. Do not bootstrap one book
as many independent groups or use a degenerate all-correct interval as a lower-bound certificate.
The original-page audit must sample pages/regions outside emitted output and account for absent,
unreadable, unsupported and unrun regions. This inventory supplies no original-page denominator.
Clean/degraded prose, mathematics, definitions, examples, lists, tables/notes, cross-references and
empty results remain required cohorts; observed native labels alone do not establish their coverage.

## Initial supported family guidance

The proposed guidance below informs `domains/statistics/semantic.yaml`; that model's assigned
worker owns declarations, requiredness, family IDs and effective release. These notes are an early
authoring agreement, not a parallel executable schema. Freeze the admitted schema/guideline revision
and independent source-authoring format together before reference acquisition. Existing accepted
guideline rules retain their authority; any conflict returns to the coordinator.

Common rules:

- Field states are `present`, `unstated`, `inapplicable`, `unresolved`. `Unstated` means an inspected
  relevant source does not state an applicable role; missing model output cannot establish it.
  `Inapplicable` follows the family meaning. `Unresolved` records ambiguity, alternatives and reason.
  A required meaning-changing unresolved role prevents accepted complete-record publication.
- Preserve source wording as literal evidence. Typed/classified role labels remain distinguishable
  from quoted words. Keep original values separate from normalized values and derived results;
  normalization cites a versioned rule/original, derivation cites premises and deterministic rule.
  Preserve exact decimal/scientific strings, mathematical tokens and units without binary-float
  substitution. No source claim becomes a fact of scientific truth by being faithfully read.
- Every required meaning-bearing role has a located evidence set. A set may contain discontinuous
  spans, native items, cells and formula occurrences, each in its own declared coordinate space.
  Coarse native item evidence is explicitly coarse. Missing cell boxes stay absent; source-view
  character offsets cannot masquerade as cell coordinates or original PDF bounding boxes.
- Required qualifiers include negation, modality, attribution, quantification, conditions and scope
  whenever changing/omitting them changes the source reading. An implicit universal affirmative
  assertion cannot be invented from an omitted cue. Optional genuinely unstated roles may remain
  unstated. Operation failure, unsupported, not-run and cancellation are operation dispositions.
- An occurrence binds family, selected source pin and native anchor membership under the occurrence
  recipe. Repeated identical strings/windows are not independent facts. Reconcile duplicate windows
  without erasing distinct source occurrences; count source occurrences and consolidated qualified
  facts separately. One record lowered into several assertions retains common record membership.
- Core comparison measures identity/required semantic roles; full comparison includes every
  meaning-changing qualifier, units, role and scope; evidence comparison assesses all required
  anchors/precision. Report partial fields separately. Missing required evidence is a full-record
  error even if core strings align. The protected evaluator owns the implementation of these views.

| Family and initial useful subset | Required roles and conditional requirements | Source-only lead / support boundary |
| --- | --- | --- |
| Definitions/concepts: explicit local definition and explicit alias | Literal term and defining passage, local sense/scope. Alias/hierarchy/instance relation only when explicitly stated; anchor both endpoints and the relation cue. Global merge is not implied. | View2 opening definition of function and explicit “map or mapping”; view3 opening definition of relation. Projection often joins words (`Afunctionf`); preserve this defect and use native anchors rather than manufacturing clean quotes. |
| Qualified local assertions: explicit local proposition | Subject, predicate and object/proposition, with source-supported polarity/modality, attribution, quantification, conditions and scope as applicable. A coherent literal proposition is allowed only under the model's supported shape; omitted qualifiers cannot be silently reconstructed. | View1 source assertion that a set is determined by its elements and its conditional equality formula. Proof text is a source assertion, not a verified proof; linked formulas stay separate native evidence. |
| Measurements/comparisons: explicit numeric property/value/role | Referent, property, original numeric value/range, value role; unit when stated or needed to interpret a dimensionful quantity; comparator, bounds, uncertainty, reference quantity and conditions when applicable. Preserve assumptions and hypothetical status. | View5 `view5:piece835`, native `#/texts/68254`, explicitly assumes bottle volume mean `0.5 liter` and standard deviation `0.01 liter`. This is a hypothetical example, not an empirical measurement. Numeric exercise instructions or derived answers do not become source measurements. |
| Table assertions: explicit native cells with recoverable row/header meaning | Native table occurrence and cell identity, row identity, complete header path and literal cell value. Applicable captions/units/notes require separately anchored inheritance. Blank, dash, missing and zero differ. | View4 native `#/tables/33`, physical page85, has nine cells and 3×3 topology; native header/row text includes truncated `Without`. Native parent table bbox exists but cell bbox is absent. Recover missing qualifier only through explicit bounded source context; otherwise unresolved. No parent-header/blank/note challenge is established by this single simple table. |
| Formula/symbol context: existing formula with explicit local declaration | Native formula occurrence and local scope; symbol literal/meaning with declaration evidence when linking an explicitly declared symbol. Domains/assumptions and declaration scope are required when stated. Missing declarations remain unstated/unresolved according to the released shape; do not guess by spelling. | View5 `view5:piece16`, native `#/texts/170109`, has the standard normal density with domain; nearby prose declares its role. Formula occurrence, recognized LaTeX, parsed meaning and a source result claim remain distinct. Cross-section symbol reuse is not identity or proof. |

These are **eligibility leads**, not independent annotations, accepted records, gold labels or a
claim that every family has sufficient useful release support. The table's missing header wording,
formula health, fused prose and incomplete source coverage make abstention/unsupported outcomes
necessary parts of the supported subset. Engineering transfer journeys require independent source
fixtures for their named cases; this statistics book does not provide pressure or complex
parent-header/blank/note cases by implication.

## Independent reference acquisition still required

The existing run6 source-only preparation and A/B/C lifecycle is a usable source/input provenance
lead, but its `AgentAuthoredBatch` reference schema is not the five-family evaluator contract.
Its two-section source packet does not establish full M1 family readings or reference agreement.
Do not register old agent-only grades as new five-family gold.

After model/evaluator agreement, independently author all in-scope records and explicit empty
outcomes in each sampled coherent source region, using source frames plus the frozen guideline.
Two fresh source-only authors and a separately attributed adjudicator receive no extractor
predictions, factors, reference expectations or production credentials. Retain agreement,
adjudication reasons and independent quality checks under the existing protected evaluator owner.
Use the selected view's release/pins and independent original-page fidelity checks; disagreement
with intake is a source limitation, not permission to silently repair retained literal evidence.
Reference-authoring assistance remains separate from CPU extraction and its independence claim.

This worker did not execute provider inference. Thus independent reference acquisition is
`not_run`; final release assessment is `blocked` on independently authored five-family references,
adequate isolated source groups, frozen release/audit populations and a defensible frozen interval
procedure. No precision, recall, calibration, quality gate, throughput or release/default claim follows.

## Commands, results and replay

The actual source read command was:

```bash
CORPUS_DATABASE__URL='postgresql://corpus_sem_writer@/corpus_pdf_20261102?host=/var/run/postgresql&port=5434' \
CORPUS_RUNTIME__DEFAULT_PROJECT=pdf-docling-adoption \
uv run python docs/design_review/evidence/2026-11-03_m1-population/inventory.py
```

**passed, 2026-11-03:** source read/freeze returned `transaction_read_only: on`, five source views,
one source-origin group, 7,310 regions and sample40. Existing release preparation emitted ambiguous
attribute warnings; the read completed successfully. The helper refuses to overwrite a frozen
inventory: a repeat requires a newly dated/revisioned evidence location, preserving these artifacts.
No new production semantics or validator was introduced by the inventory helper.

[cpu-source-paragraph.json](cpu-source-paragraph.json) is a 439-character actual view5 paragraph
at selected-view interval `[29,468)`, with full view pin and its three overlapping native pieces.
It is intended for a bounded development CPU operation check by the coordinator. It contains
source only; no expected answer or prediction is included. Its use for development keeps this
origin out of final assessment.

Detached digest/sample verification: `uv run python docs/design_review/evidence/2026-11-03_m1-population/verify.py`.
Production extraction, independent authoring, grading, fitting/calibration, original-PDF auditing,
full tests and release qualification: **not_run**. Maintenance/formatting belongs to the coordinator.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Retained source development population](records/m1.development-population.json) | M1-01 | passed | — | 2026-11-03 |
<!-- evidence-index:end -->
