# PCE-00–03 foundation execution

Execution evidence, 2026-11-05. Initial baseline `cd9bd586`; the
[PCE coordinator](../../../plans/progressive-corpus-enrichment_2026-11-04.md) owns package state.
This folder retains source-only inputs, independent fresh references, retained-output recovery,
native custody checks and protected assessment. Source capture alone establishes no operation
quality. The selected increment stops at PCE-03; public admission, portable review bundles and
full-series qualification remain later work.

## Source-only capture

`uv run ci golden record-packet --unit 1 --project m1-source-grinstead-snell --pass A --json`
and the corresponding unit2 command passed under the evaluator capability. Original packets
are `raw/source-only-unit-{1,2}-002.json`, with stderr alongside them. They contain source,
guideline and original frame metadata, without producer predictions or grading labels.
The first unit1 invocation omitted the project and failed with unknown semantic project;
`raw/source-only-unit-1.json` preserves that failure. A subsequent ordinary-reader inventory
confirmed the configured corpus_structure_dev and project names; an attempted eval-table read
under that ordinary reader refused permission. No reference data was exposed by that refusal.

## Frozen bounded source-first selection

`uv run python docs/design_review/evidence/2026-11-05_pce-foundations/prepare_cohort.py`
passed: six source cases, comprising five text items and one table with sixteen body cells.
The script freezes up to four text items and one table per view, ordering native pointers by
SHA-256 before consulting predictions. `raw/source-cohort-001.json` binds source input hashes,
selected pointers, table cells, questions and explicit scope. View22 contains only Chapter5's
heading; view23 contains the chapter body. Five text items are the combined count across views,
not five items in one view. Original feature_fit origin assignments remain unchanged.

These are bounded development cases, not a population sample or whole-corpus completeness
claim. The registered origin partition is `feature_fit`; exposure here makes these development
material, not an untouched final cohort.

## Fresh reference authority

The operator's 2026-11-05 direction replaces inadequate historical-reference adaptation with
fresh question-specific authoring. The new operation protocol contains no historical-field
projection, old-reference coordinate bridge or derived-C bypass. Historical whole-reading
labels are not inputs to the new assessment. No historical data deletion was necessary to
author fresh cases. Complete retained producer bytes remain input-contract fixtures, independently
assessed under the new contracts; they establish no new producer quality.

`raw/author-source-packet-001.json` contains source/context and the rubric, without candidates
or scores. Separate fresh Sol/high contexts authored `raw/author-A-001.json` and
`raw/author-B-001.json`. A third fresh Sol/high context inspected source and both passes to
write `raw/author-C-001.json`, retaining disagreements, permissible structures and limits.
The authors inspected supplied native text/table structure; original page-image completeness
is uninspected. Four contextual symbol roles remain unassessed against the current products,
because a literal or `formula.symbol` product does not establish the independently described
prose role.

`raw/pce03-fresh-source-wrappers-001.json` faithfully serializes those immutable authored answers
into 93 facets per pass: four literal symbol occurrences, four contextual roles, five explicit
definition/alias-cue states, sixteen cell literals/states and sixty-four cell attachments.
Each wrapper preserves the original author artifact hash, case/facet and serializer hash.
An inspected blank field uses a structural subject, never an invented empty quotation.
Zero output cannot satisfy a required state-capture question. Source-first protected registration
passed with sets4/5 and passes34–42 (`raw/pce03-fresh-source-register-001.json`).

## Private native foundation and preservation

The additive frozen migration131 is `semantic_pce_foundation_20261105`. Its persistent deployment
passed (`raw/migrate-working-001.json`), preserving all71 existing task reports,1830 observations,
38 source views,3 documents,33 reference passes and33 frames at migration time. Project-default
rows and the task37 raw-body digest were unchanged. This is preservation evidence at deployment,
not a claim that later authorized new runs create no additional rows.

The first proposals exposed a post-hydration byte check, an unestablished occurrence join,
an undefined native SQL variable and a dropped blank-field inspection subject. Corrections are
integrated through `9ea94d84`/main`74dd8423`. The completed `raw/native-controls-006.log` has71
passing controls covering private contributions, protected assessment, existing private records,
record references and attributed evidence. Earlier failed native/control attempts remain here;
progress dots from an incomplete attempt are not acceptance receipts.

Private products retain one task envelope, with indexed selection before bounded detail
hydration. Source occurrence, semantic product and `(origin_task_id, contribution_id)` producer
observation are distinct grains; cache aliases do not multiply independent observations.
Native graph publication still refuses private source products.

## Retained returned-output recovery

The replay scripts consume the complete returned raw object, independently of diagnostic score
projection. `raw/pce02-task37-replay-summary-002.json` records366 recovery operations and5074
products; the registered-method read-only port adds63 attachment operations and25 derived
relations (`raw/pce02-historical-port-summary-001.json`):429 operations and5099 products in all.
The kind inventory is1136 occurrences,3269 proposals,232 diagnostics,437 composites and25
relations. No required retained input was unavailable. These are attributable returned/derived
products, not5099 correct facts. Natural-group-derived attachments are not native relation-head
observations.

`raw/bind-retained-002.json` records full-batch binding without product drops. Its2272 located
observations refer to447 physical occurrences; overlapping windows remain attributable and
dependent. Missing scores, explicit raw nulls, unsupported shapes and assembly failure remain
visible instead of becoming fabricated zero scores, absent source claims or discarded products.

## Actual source and retained-output journey

The guarded `pce03_native_assessment_001.py` driver restricts the source graph to retained
`ingest.pdf_integrated` and the prediction graph to that intake plus the retained-reading
resolver. It refuses an unexpected method inventory before provider execution. Runtime admission
and an empty nondefault input passed (`raw/runtime-001.json`). The source-only run23 passed with
source-ready cut24/final cut25 and current views39/40 (`raw/pce03-source-run-001.json`). It reused
the exact retained source product; no conversion or provider call occurred. Project selection
was null before and after.

The first retained-output attempt refused native source hydration because a report-local16-row
budget had leaked into the independent source-context boundary. Its failure, executed driver and
stderr remain in `raw/pce03-retained-products-run-001*`. The two-line repair preserves the report
guard and forwards only the actual caller source budget to source hydration/selection. Controlled
budget propagation and M1 reading checks passed21 cases (`raw/pce03-budget-focused-002.stdout`);
the first incomplete test fixture failure remains alongside it. Actual native hydration still
requires the subsequent registered journey, separately recorded below.

No extraction, OCR, recognition, encoder or training model has been rerun by these steps. Fresh
reference authors are model-assisted assessors and are attributed as such; this statement does
not describe their authoring as model-free.

## Completed current journey and scoped acceptance

**Implemented and bounded Tested,2026-11-05.** The completed increment is PCE-00–03. Source
run27/cut31 and retained-output run28/cut33 use semantic release`19379a91…`, whose model,
manifest and artifacts stayed byte-identical across the later validator repair. Runtime custody
is independent. Native132 migration passed hashes over21 critical retained tables; native133
passed22 including the actual runtime archives/pins. `runtime-migrate-working-001/002` failed
before mutation due evidence-script SQL construction;003/004 are the committed passing migrations.
`raw/legacy-runtime-read-001.json` reopens old run26's5099 contributions and432 operations through
the ordinary reader, with its172 original source inputs rather than current-code substitution.

The scoped functional union at source`75d5e98b` passed421 tests
(`raw/root-final-functional-002.log`). The affected133 operation/scientific/source-record
grading branches then passed12 native controls in the
[dispatch account](../2026-11-05_operation-grade-dispatch/README.md). This reassesses the changed
guard; it is not an overlapping-count total or full PCE-11 qualification. Global typing and Ruff
passed at the recorded source, and final maintenance/publication checks are recorded separately.

Actual grading first exposed the shared trigger's legacy scientific-array assumption. Native133
dispatches from immutable set protocol to the existing operation validator, preserving record/
scientific checks and rejecting forged protocol claims. The independent
[identity account](../2026-11-05_operation-grade-dispatch/identity-after.json) proves unchanged
semantic release/model/manifest/artifacts and a changed runtime fingerprint. Source runs, source
frames and fresh references were not regenerated for this operational repair.

Fresh source sets6/7 retain passes43–51; output sets8/9 retain52–57. Source evaluation7→9 covers
attachments and10→12 recovery; output evaluations8/11 cover the distinct frozen output frame.
`raw/pce03-fresh-custody-final-001.json` authenticates all stored grade bodies, frame/pass hashes,
C-to-A/B provenance and exports; defaults remain null/null/generation0. Feature-fit default exports
withhold judgments. Raw independent authors and scoped reports remain available here for the
operator; these exposed cases cannot be relabelled an untouched final population.

| Direction | Actual bounded result |
|---|---|
| Source-first93 facets | 16 supported,73 unsupported,4 unassessed |
| Captured cell facets | Nine stated literals and seven explicit inspected unstated cells; no silent-zero credit |
| Source gaps | 64 table attachments, five explicit cue-state products and four scientific-symbol literals missing; four contextual roles unassessed |
| Same-case source diff | 16 newly captured,73 unchanged,4 still unresolved; no observed correction/regression/newly-spurious change |
| Output-first24 facets | Three supported,five unsupported,two ambiguous,fourteen unassessed |

These are actual producer assessments, distinct from C's authored8supported/2ambiguous/14unassessed
source expectations. A coarse item location can fail an exact literal question while producer
execution and the product remain present. The actual relation population has25 definition
attachments and no table relations. The failed search for a real positive table-association case
is retained as a coverage finding, not replaced with an invented passing example. Independent
constructed native association controls establish their own functional behavior.

The fixed24 questions were not reselected after the identity-scheme transition:
`raw/pce03-fixed-output-reidentification-003.json` authenticates complete95-product endpoint/member
closure and exact operation/item/value/score/physical-source equality. Eight discrimination
controls reject wrong role, member order, value, document, occurrence, closure and source mapping.
The initial slow evidence-only JSON query was cancelled and replaced with compact-index selection
and one bounded report hydration; both attempts remain recorded.

Native-grade003's genuine trigger failure and serializer004's rolled-back transactions remain
alongside successful005. `raw/pce03-journey-attempts-002.json` indexes these and the runtime-preparation
serializer attempts; source/reference bytes were not rewritten to make an attempt pass.
`raw/pce03-actual-assessment-summary-001.json` derives counts from sealed reports only.

The coordinator owns ensuing refinements and findings. Public local admission, complete portable
review bundles, new producer efficacy, original-page completeness, scientific numerical truth,
calibration/population estimates and full-series operational qualification remain outside this
increment. No default adoption occurred. All integration worktrees have been merged and removed.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**PCE**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Private progressive contributions and fresh protected operation assessment](records/pce.foundations-00-03.json) | PCE-00–03 | passed | PCE-00, PCE-01, PCE-02, PCE-03 | 2026-11-05 |
<!-- evidence-index:end -->
