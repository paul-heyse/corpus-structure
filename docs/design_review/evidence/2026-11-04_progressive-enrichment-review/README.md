# Retained development table contributions before complete-reading acceptance

**Tested for this detached comparison, 2026-11-04.** Every one of the 80
occurrence-matched development table candidates already preserves the reference's
table/cell location, header path, cell value and caption with exact role semantics
and evidence agreement. Every matched candidate differs in `row_label`, `unit`
and `note`. This establishes useful retained partial structure inside this failed
complete-reading baseline. It establishes no standalone operation accuracy,
acceptance authority, generalization or whole-M1 qualification.

The [progressive corpus enrichment functional review](../../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md)
consumes this result. The existing M1 coordinator continues to own execution and
qualification; execution remains stopped. No production contract or reference
label changed.

## Question and frozen scope

Do the existing 80 unaccepted table-occurrence matches contain correct usable
subrecords, and which fields prevent the whole reading from agreeing?

The [original protected development assessment](../2026-11-04_m1-independent-assessment/development-grade-001-summary.json)
grades run14 against feature-fit C23/C24: 270 reference readings, zero accepted
predictions, 190 missing occurrences and 80 unaccepted matching table occurrences.
This investigation does not rerun or replace that assessment.

Only Grinstead–Snell development data is used. The original independently authored
reference bytes remain in
[`m1-training-alignment/feature-fit-protected.json`](../2026-11-04_m1-training-alignment/feature-fit-protected.json),
whose SHA-256 is
`76ae523a875d5b678330fb8e9ffbf3f1d543768c57e577cd3aecf996ec7ec855`.
The script checks feature-fit partition, C23/C24 identity and the 270-reading
denominator before selecting unit2/C24/source-view23's 80 table readings. C24's
original content digest is
`02b6c639b284dedd2922ca68d9397eac0d42b2afaa9f00c0f3e4a475545d43d7`.
No reference is copied, edited or reauthored here. No Forbes/NIST held-out labels
or errors are read.

One narrow ordinary-reader query captured task37/run14/source-view23's 182 table
candidate interpretations, plus the two examples' actual policy events and one
native structural contribution. The complete original task body is not copied;
its canonical-body SHA-256 is
`3238bee07c13b24c437812089843f538d68561dd724322377539ab045ec782f7`
over 12,211,787 canonical bytes. The envelope source, input/configuration hashes,
release, task and source-view identities are in the
[capture](raw/task37-table-candidates.json). Its full task contains 232 candidate
interpretations across families; this capture retains the 182 table candidates.

Both sides use release
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.
The inspected source revision is `8695e869a8f38bbd521dd88470fff86009f94f05`.
Capture used Python3.14.10 on `paul-X870-AORUS-ELITE-WIFI7`; no model was loaded.

## Method and exact result

[`compare_retained_tables.py`](compare_retained_tables.py) matches immutable
occurrence IDs, then calls the existing pure
`evaluate.record_alignment._meaning` and `_evidence` helpers on each role.
`_meaning` excludes explanatory prose and local evidence identifiers while
preserving actual field semantics and alternative values; `_evidence` compares
evidence availability, evidence-set identities and alternative evidence.
Both sides share the same archived release and source pins, so no cross-release
correspondence or semantic relabeling is introduced.

The [immutable comparison output](raw/comparison-001.json) contains all 80 matched
candidate/reference identities, per-role comparison outcomes, two exact field
examples, retained native contribution and actual policy events. The 102 table
interpretations without a matching reference occurrence are counted separately;
they are not silently included in the 80-case agreement denominator.

| Quantity | Existing retained result |
| --- | ---: |
| Reference table occurrences in C24 | 80 |
| Table candidate interpretations in task37 | 182 |
| Occurrence-matched candidate interpretations | 80 |
| Distinct matched reference occurrences | 80 |
| Unmatched candidate interpretations | 102 |

| Role, among the 80 matched candidates | Exact role-semantics agreement | Exact evidence agreement |
| --- | ---: | ---: |
| table | 80/80 | 80/80 |
| cell | 80/80 | 80/80 |
| header_path | 80/80 | 80/80 |
| cell_value | 80/80 | 80/80 |
| caption | 80/80 | 80/80 |
| row_label | 0/80 | 0/80 |
| unit | 0/80 | 0/80 |
| note | 0/80 | 0/80 |

Every matched candidate's differing-role combination is exactly
`note,row_label,unit`. These are finite retained-case facts, not newly estimated
operation precision/recall. All 80 candidates retain candidate standing.

## Two actual local examples and contribution attribution

`record:74387f5822fcea8e8727ca38f94b3148b55fdfecafcd19c1d14d0b452176891d`,
interpretation
`record-interpretation:a088275ff3f6832893d0486b300438e8e8a28b743244e7484496a94d04c86fe8`,
binds native table0/cell8. Its header `Poisson`, cell value `.9048` and caption
`Table 5.1: Poisson approximation to the binomial distribution.` agree with C24,
including exact evidence. C24's row label is present `0`; the candidate row label
is unresolved. C24's unit and note are inspected `unstated` with available
evidence; the candidate fields are unresolved with unavailable evidence. Absent
values therefore do not establish semantic or evidence agreement for unit/note.

Task37's retained native-structure report at context101 already contains table
`#/tables/0`, cell `#/tables/0/data/table_cells/8`, header span0:7, value span91:96
and caption span127:189. The assembled candidate independently retains header
source projection13708:13715, value13799:13804 and caption14345:14407, with their
native item pointers. This is a native structural contribution, routed by
`methods/m1_source.py` through `assemble_native_records` and the existing record
assembler. It is not credited to GLiNER. The earlier scoped inspection also saw
same-context GLiNER header fragments such as `100p` and `.001` proposed as
`cell_value` with unresolved states; the new bounded capture does not copy those
model reports or use them to infer decoder causes.

`record:811b546e25ab4518e1efdc6ca5edb4301a3bf407ce9a2b429f88948f9a60fe41`,
interpretation
`record-interpretation:00a44dada916ce22e94d42dc0632c06a334702e2e06c18bef652d2fec1cfa45e`,
binds native table0/cell9. It preserves `.9048` and the complete ordered header
pieces `Binomial`, `n`, `= 100`, `p`, `= .001`, with exact reference agreement.
It has the same row-label/unit/note differences as the first example.

Both examples' retained record-policy events are `not_run`: feature-instance
digest, feature-input digest and final event score are null; diagnostic is
`fitted record policy instance unavailable`. The detached comparison creates no
score, fitted policy or admission.

## Execution and immutable receipts

Capture command, **passed**, one ordinary `purpose="read"` connection and
read-only transaction, verified2026-11-04:

```sh
uv run python docs/design_review/evidence/2026-11-04_progressive-enrichment-review/compare_retained_tables.py --capture
```

Detached comparison command, **passed**, no DB connection, verified2026-11-04:

```sh
uv run python docs/design_review/evidence/2026-11-04_progressive-enrichment-review/compare_retained_tables.py
```

The actual stdout/stderr are retained in [capture-001.log](raw/capture-001.log)
and [comparison-001.log](raw/comparison-001.log). Exclusive creation protects all
outputs. The capture and comparison bind immutable executed-script copies and
hashes under `raw/`; their source helpers and frozen inputs are hash-referenced.
For a later pure replay, use a new output basename, for example
`--output-stem comparison-002`; do not rerun capture or overwrite existing bytes.
The existing repository attributes put every `raw/` artifact through Git LFS.

## Earlier interactive observations and limits

The following were observed during the preceding read-only inquiry, before this
artifact was authorized. They are reported observations, not reproduced outputs
of this comparison script; no historical log files have been invented.

- A bulk `eval.record_policy_prediction_frame` SELECT for run14/set1/table/
  feature-fit spent several minutes in native source-custody validation. It was
  interrupted; exit130 and transaction rollback were observed. No frame output,
  grade or fit was persisted. This capture uses neither that function nor a
  substitute privileged connection.
- An initial pure whole-reading replay failed before coordinate acquisition
  because JSON lists were passed to strict Python tuple validation. Retrying
  with the existing fitter's `prepared.validate_json("SourceRecord", ...)`
  normalization succeeded. That inquiry used the normal evaluator reader and
  authenticated coordinate owners:205 reference coordinate texts from source
  run11 and4 candidate coordinate texts from run14 for the first example.
  `whole_reading_correct` returned false, and a detached accepted comparison
  refused `accepted record has an unresolved meaning-changing role`. Original
  candidate standing was unchanged. This replay is not repeated here and is
  separate from the 80-case detached comparison above.

The original protected assessment remains the authority for complete-reading
quality. Hidden proposal/suppression/abstention causes remain unavailable. No
accepted record, source-quality authority, new grade, fitted policy, product test,
model/PDF/training execution or held-out error inspection was performed. Those
operations are **not_run** in this artifact. Record finalization, index/render
integration and the principal review belong to the root agent.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Correct local table contributions within unaccepted whole readings](records/m1.retained-table-contributions.json) | M1-13 | passed | progressive-corpus-enrichment O01, progressive-corpus-enrichment O02 | 2026-11-04 |
<!-- evidence-index:end -->

## Review publication checks

Root finalized `m1.retained-table-contributions` and rendered
[the count matrix](contribution-summary.md) from its catalog values with
`just evidence render docs/design_review/evidence/2026-11-04_progressive-enrichment-review/contribution-summary.md.j2`.
The initial record draft used `#O01` item references unsupported by the existing evidence schema;
it failed validation/finalization and rendering. The retained
[failed validation](raw/record-draft-validation-failed.log) is publication metadata only.
The corrected draft uses qualified item references; comparison data and outputs were unchanged.

**passed**,2026-11-04: `just evidence` (202records/112folders,0errors,40existing warnings),
`just turn-end` (756Python files unchanged), and `just docs-check` (541canonical pages,
0link errors). Their publication logs are retained under `raw/publication-*`.
These are documentation/evidence checks, not product or model qualification.
