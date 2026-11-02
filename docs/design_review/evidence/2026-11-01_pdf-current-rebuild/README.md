# Current-deployment retained-book rebuild

Status: **Current native storage chain and empty task completion Tested 2026-11-01.** Three current-target
storage attempts failed before seal; deliberate interruptions, exact frozen resumes and the later
committed-publication recovery are recorded below. Current raw, organized and enriched products are
sealed; regeneration, provider, extraction and complete-knowledge outcomes remain unclaimed.
The PDF plan remains the owner of package completion and qualification.

`rebuild_current_book.py` derives the retained native chain onto the separately initialized
`corpus_pdf_20261101`, currently requiring the reviewed `semantic_pdf_address_20261101` (0076)
deployment. The first attempt used 0068 and is preserved below.
It never clones, upgrades or writes `corpus_pdf_20261031`. Historical metadata and exact recipe
bytes are inventoried only inside a read-only repeatable-read snapshot. Initialization uses the
ordinary current migration route before `--execute`; the driver does not issue deployment DDL.

The inputs are the operator-retained canonical envelopes under `build/pdf-current-rebuild/`:

| Historical pin | Exact byte SHA256 | Structural predecessor |
| --- | --- | --- |
| `2/native` | `ca05561954ebf2318e2f020590d74cd87ecac6917e2e992a7b24b679cb6ce504` | None |
| `2/organized` | `f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba` | `2/native` |
| `7/math-enriched` | `8468df6fb3af853b1d0757b18facc7ecd2ff25fa301e8f4b8e05aa2930b6948d` | `2/organized` |

The driver checks each exact byte hash, byte length and parent chain before any target write.
At execution it retains those historical bytes and source recipes under the output's `raw/`,
prepares the current statistics pack, admits its authored SQL through reference analysis, and
registers the actual original PDF. Each storage-derivation task records the old source pin and
its explicit current structural parent. `migrate_retained_pdf_envelope` owns maintained claims,
retained-byte verification, native computed-grid projection, typed page payloads, private staging,
validation and protected publication. No historical inference is relabelled as newly performed.
The original PDF remains SHA256
`e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9`.

The current structural chain is explicit: the new raw pin is used by the new organized product;
that new organized pin is used by the new enriched product. The production derivation recipe
binds both historical and current parent identity. Old task IDs never become unresolved inputs
in the fresh database. Exact retained envelope identity and current logical record identity are
distinct. Current native semantics remain an explicit materialized phase.

Run the local check from the repository root:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-rebuild/rebuild_current_book.py
```

Passed 2026-11-01: three exact witnesses and 3,438 actual retained observation files found.
This is a local custody/inventory result; receipt inventory alone does not establish recipe
compatibility or successful current reuse. No database connection is opened by this default mode.

After the coordinator freezes source and deploys the reviewed current successor, normal
execution uses:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-rebuild/rebuild_current_book.py --execute
```

`runtime/checkpoint.json` owns each exact task and publication. It is reused on retry; a frozen
build resumes through `resume_pdf_publication`, while failures remain in `attempts.jsonl`.
A currently held claim is refused rather than stolen. Each sealed storage task then closes through the current `complete_task` fence with
`observations=[]` and `outcome="empty"`; checkpointing separates protected publication from
terminal task completion so a retry can finish the same task without publishing a replacement.
The storage tasks create no selected knowledge result or extraction observations. Do not report them as a completed regeneration.
No broad database cleanup is authorized by this driver.

After all three native products publish, `runtime/regenerate-command.json` records the exact
next `ci regenerate --native-source runtime/math-enriched.pin.json --leave-unselected` invocation,
including its corpus and target URL. Set `CORPUS_NEMOTRON__RECEIPTS` to the existing actual
`docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/runtime/pages` root. The production
recognizer determines compatible page A/B/C reuse with `reuse_failures=True`; an endpoint is
needed if a required compatible receipt is missing. Neither receipt presence nor local raw
transcription establishes endpoint availability or current complete-product acceptance.

Remaining acceptance: execute the storage chain on current 0076; run current integration and
knowledge regeneration without selecting it; retain actual failures/retries/cancellation; inspect
public selected reads, exact exports and current consumers; perform independent reference grading
and applicable full functional/provider/nonfunctional qualification under the coordinator.

## Current attempt receipts — 2026-11-01

| Scope | Outcome | Receipt |
| --- | --- | --- |
| 0068 candidate/fresh-head source match | passed | `ci schema native-candidate`: 23 desired native objects, one descriptor transition, no ordinary schema operations; targeted native closure/bootstrap controls passed |
| Fresh target initialization | passed | `runtime/target-init.json`: `corpus_pdf_20261101`, revision `semantic_pdf_stream_20261101`, descriptor SHA256 `65bbc9f95b3527a87267547c450aa0cc072402f7dca9b119c12d951ae018adfc` |
| First native storage attempt | failed before seal | `runtime/storage-attempt-001.log`, `runtime/attempts.jsonl`: claim renewal SQLSTATE `55P03` while locking `ops.task` during a companion adoption transaction |
| Current source/project preparation | passed for the attempted storage run | `runtime/release.json`, `runtime/checkpoint.json`; the raw source task and open private build survive for explicit retry |
| Three-product publication and regeneration | not_run to completion | No sealed product, selected result or complete-knowledge claim follows from this attempt |

The failed operation stopped after the renewal owner reported its error. Its durable task/build
and exact historical envelope are preserved. The coordinator must reconcile the production
transaction/renewal behavior and current native admission before a retry; no timeout, ownership
check, validation or admission was bypassed. A direct attempt to invoke the ungranted descriptor
function as maintenance was also refused (`42501`); the initialization receipt uses its catalog
body hash instead and records that refusal.


The first attempt's known unsealed state has now settled: task 1 is `failed`, its lease is null,
and build `a0285103bcc323ef1600a837d85e92dc115053ee96bed6a55a56c614c34e5d8a` is `abandoned`.
`runtime/checkpoint-superseded-001.json` preserves the exact checkpoint;
`runtime/supersession-001.json` records the guarded abandonment and failed completion after
confirming zero frozen or published effects. The two cleanup logs remain, including a mistaken
read-only frozen-table column query and the corrected terminal-holder expectation. The native
terminal row keeps `claimed_by` as provenance while clearing its lease.

The production fix bounds outer companion transactions by the existing 64-row/4-MiB limits.
0069 changes only the current source-admission descriptor and preserves 0068. The driver requires
`--supersede-known-open` to start a new release/task branch from this known failed state; it
rechecks the exact archived checkpoint, terminal failed tasks, abandoned builds and absence of
frozen/published effects. It refuses to replace uncertain or published work. Current project
activation uses the existing generation-fenced `activation_token` / `activate_release` route.
The explicit retry is:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-rebuild/rebuild_current_book.py --execute --supersede-known-open
```

Attempt 002 (`runtime/storage-attempt-002.log`) prepared and activated release
`release:9489848b380040eb34305a56b53cb03cbf00292ab052968053e13c1669f680ea` on 0069 and
created raw task 2. It failed before seal with SQLSTATE `23514`,
`parsing record shape differs: PdfRecordNativeHealth`: the retained adapter's health row
carried an undeclared `derivation` wrapper. The existing recipe already binds retained-envelope,
source-recipe, projection-profile and old/current structural parent attribution. The renewal
lock timeout from attempt 001 did not recur during this attempt. Its open private build and
checkpoint remain; no raw/organized/enriched product has sealed yet. This refusal does not
establish current storage, provider or knowledge-regeneration qualification.


Attempt 002 has also been fenced and settled under its original 0069 deployment: task 2 is
`failed`, has no lease, and its private build is `abandoned`. The exact checkpoint is retained
as `runtime/checkpoint-superseded-002.json`; `runtime/supersession-003.json` records the known
health-shape refusal and confirms no frozen/published effects. 0070 preserves 0068 and 0069,
updates only the source-admission descriptor, and has passed fresh bootstrap, frozen-head
provenance and exact empty-current-candidate controls. `runtime/target-migrate-0070.log` records
the normal target-only migration. Attempt 003 uses the explicit health-refusal receipt:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-rebuild/rebuild_current_book.py --execute --supersede-known-open --supersession-receipt docs/design_review/evidence/2026-11-01_pdf-current-rebuild/runtime/supersession-003.json
```

Its outcome is pending in `runtime/storage-attempt-003.log`; do not treat a launched process or
a private checkpoint as publication. No reference data or acceptance control was relaxed.


## Frozen raw resumption and qualification boundary

0071 passed fresh-head/current-candidate and independent binary/native-budget controls. Its
normal deployment is retained in `runtime/target-migrate-0071.log`. Attempt 004 was deliberately
interrupted during source coordination, with zero frozen/published effects; its exact open build
was resumed without replacement. The resumed build reached frozen inventory
`285a247e2e274673f85dfc701412f98ea8104fc2d6b5fe7c6a6d1b79efd91e34`:
267,052 native records and 106,142 references. Native `prepare_pdf_build` remained active without
waits/blockers, with a correlated reference-resolution path identified for structural repair.
`runtime/interrupt-attempt-004.json`, `interrupt-attempt-005.json` and the interrupted process logs
retain both interruptions; the frozen union and producing release were not superseded.

0072 adds set-based reference preparation and state-preserving frozen-owner reattachment.
The declared resume operation still has no lifecycle transition: only attempt/holder may change;
state, source/schema/recipe, frozen digest and uploaded values stay unchanged. Fifteen scoped
actual PostgreSQL controls passed, including seven reference-resolution cases, two frozen-resume
cases, current/fresh native closure, existing open resume and a complete small native seal.
`runtime/target-migrate-0072.log` records deployment. A bounded production claim-renewal supervisor
kept the paused claim and was stopped/joined before the exact frozen resume.

The exact raw-only resume is:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-rebuild/rebuild_current_book.py --execute --resume-frozen-raw --reattach-settled-claim docs/design_review/evidence/2026-11-01_pdf-current-rebuild/runtime/interrupt-attempt-005.json
```

This route opens the original archived release/schema context, verifies the recorded frozen
binding, invokes `resume_pdf_publication`, and stops after publication and terminal empty-task
completion. It does not prepare a new release or relower/reupload the raw records. The current
log is `runtime/storage-attempt-006-frozen-resume.log`. At the latest recorded observation,
reference preparation, native capture and child validation had completed; validated access
projection adoption was active and advancing. `runtime/progress.jsonl` retains bounded stage,
claim and actual PostgreSQL activity observations. No seal was claimed at that observation.

The raw 0071 retained adapter intentionally supplies no occurrence derivative in this preserved
snapshot. Its prospective qualification is limited to the complete original native graph,
access and provenance. It is an intermediate structural parent, never the selected consumer
source. Corrected organized/enriched production uses the existing native-occurrence generator;
that terminal enriched product is the adoption target. The explicit `--reuse-published-prefix`
route checks the protected immutable raw pin, original producing release, source/schema and
terminal task; it archives the exact checkpoint and creates only remaining tasks under the new
release. It never republishes or relabels the preserved raw source. No current consumer or
knowledge qualification follows until those actual downstream journeys finish.


0073 was normally migrated onto the current target while the same raw frozen resume continued.
`runtime/target-migrate-0073.log` records the applied transition. It changes keyed access/region
lookups, selected-product producing-schema identity and the admission descriptor, with no table
DDL, ABI or effect-version change. The original raw producing release and frozen snapshot remain
unchanged. `build/pdf73-targeted.log` records six passing affected PostgreSQL cases: frozen/current
native controls, keyed replay, full seal with schema identity, and actual typed companion export.
Five cold CLI/MCP registration checks also passed after operation-local ADBC/Arrow imports.
At 14:11:47 America/New_York, raw projection adoption had committed 35,518 access and 33,090
region rows; the active access batch had no blockers. This is an observed progress count, not a
throughput or complete-publication claim. The task-qualified retained recipe filename is sound for
this chain: native and organized task-2 recipe bytes both hash to
`fcea5b6ed390cc510feca777bb568a8948194b152caaf691e983dffaf4377b68`.


The raw final validation under 0073 reached the ownership guard and remained CPU-active with
no blockers. `runtime/raw-owner-edges-explain.json` captures a read-only EXPLAIN: a nested-loop
left join over 267,052 native rows and 426,822 estimated materialized edges. This is planner
evidence, not an executed benchmark. The equivalent grouped ownership counts produce a hash
left join in `runtime/raw-owner-counts-proposed-explain.json`; multiplicity uses `count(parent_id)`,
including duplicate edges from the same parent, with zero owners for the root and one otherwise.
Five subsequent validation plans are retained in `runtime/raw-remaining-validation-explain.json`.
The ordered membership lookup already used an index-only probe; 0074 additionally binds its
revision explicitly. The missing-target check used a hash anti join and parent/child checks
used pointer index probes. A full reference/address plan was unavailable to the diagnostic
maintenance role because the byte-equality function correctly refused EXECUTE permission;
no permissions were changed.

The coordinator authorized graceful interruption of this validation. Attempt 006 settled with
exit 130 and retains its original log. `runtime/interrupt-attempt-006.json` binds the unchanged
checkpoint, producing release, frozen digest, 267,052 native rows, 52,987 access rows and 49,756
region rows, with no publication. The exact task 4 / attempt 2 claim is maintained by the existing
production claim supervisor (`runtime/raw-claim-hold-0074.*`), without data or publication effects.
The successor resumes this same immutable snapshot after the normal 0074 migration; it does not
relower or upload it again.


0074 native authoring and seven affected PostgreSQL checks passed (three fresh/current native
controls, two ownership-negative controls, full seal, and projection replay); scoped typing passed.
The current authoring database reproduced zero native and zero ordinary operations.
`runtime/native-0074.json` binds the frozen artifacts, test and deployment logs. The normal
`runtime/target-migrate-0074.log` deployment completed before the supervisor stopped and joined
cleanly. `runtime/storage-attempt-007-frozen-resume.log` resumes the original71 frozen build using
`interrupt-attempt-006.json`. At 14:35:19 America/New_York, its callback validation and projection
replay had completed and final native validation was active without blockers; no seal was yet
claimed. The producing release, frozen digest and existing staged inventory were preserved.


The raw final validation and seal under 0074 **committed successfully**. The process then failed
with renewal lock timeout (55P03) at the maintained-claim scope exit. The raw native pin is
`4/native/7326ebf1aa74f611a4b152a68fe37ca1f9c5f76286484e566e5811c96b1faa6d`.
The protected publication and validation row (`native_callbacks=true`) were read back exactly
in `runtime/settled-attempt-007.json`; the producing71 release and frozen digest are unchanged.
The local checkpoint had not yet been updated when the scope exit raised. The failure log stays
unchanged, and the committed product was neither recreated nor relabelled.

`runtime/settle-committed-raw-007.json` and its log record the known-commit recovery: authenticate
the settled process and exact checkpoint, read the exact protected publication, save that binding,
then call the normal `complete_task` operation under its original archived release with no
observations and outcome `empty`. The task and checkpoint are now terminal/completed, and
`runtime/native.pin.json` plus `runtime/raw-producing-qualification.json` bind the result.
This raw intermediate qualifies original graph, access and provenance only. It is not the selected
consumer source, because the producing71 retained adapter omitted its occurrence derivative.
Remaining corrected organized/enriched products still supply the intended consumer source.

The seal function currently takes the task owner fence before recomputing the full projection
contract. That is a concrete remaining publication/heartbeat contention issue: this run's product
committed, while the renewal thread timed out on its task row. Remaining derivatives are held for
the coordinator's bounded source correction; no lease errors or qualification failures are ignored.


0075 closes the remaining validation-receipt lifetime boundary. The model-owned projection-write
profile is validated through the existing operational contract boundary and admits READ COMMITTED
before any projection build lock. Validation contract v3 binds the sorted unique allowed isolation
meaning, independently of explanatory rationale. Lookup, native validation and seal reject stale
unfinished final witnesses with fresh-current-storage-rebuild guidance. They consume an immutable
current witness without repeating the projection fold; existing published pins remain unchanged.
The frozen native state has 27 desired objects, ten native transitions and zero ordinary DDL.
The changed annotation gets an exact unchanged-CHECK physical receipt alias; its source digest
remains `86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0`.
`runtime/native-0075.json` binds these artifacts and verification logs.

Thirteen affected PostgreSQL cases passed: three native closure/head controls; two actual
stale-snapshot isolation controls; three stale witness consumers (lookup, native validation, seal);
full seal; projection replay; two frozen-owner controls; and actual companion export. Scoped typing
passed. The authoring database reproduced zero current native/ordinary changes. The normal target
migration passed (`runtime/target-migrate-0075.log`). This is bounded affected verification, not a
repeat of complete qualification.

`runtime/raw-readonly-0075.json` verifies the previously sealed raw pin without validation or
publication writes: its retained envelope is exactly 47,748,822 bytes with the original
`ca05561954ebf2318e2f020590d74cd87ecac6917e2e992a7b24b679cb6ce504` SHA; producing semantic
context matches the product view; native item access succeeds under 0075. The raw pin keeps its
original71 producing release. The explicit published-prefix receipt and archived checkpoint preserve
that identity. Remaining organized/enriched storage is now running under current release
`release:d97e7deac34f3061b58b0b5f4d989b1db5088d67ea5da6104f821ed34022682f`, beginning with task5,
structural parent task4/native. Its log is `runtime/storage-attempt-008-current-prefix.log`.


The organized snapshot did contain the corrected native occurrence index:
`runtime/organized-occurrence-inventory.json` and `runtime/organized-occurrence-kinds.json`
record 107,687 occurrences: 49,024 items, 6,342 formulas, 2,565 inherited table cells and
49,756 PDF-point regions. The earlier companion receipt totals described a different subset
of the upload protocol. The original read-only diagnostic assumed the wrong stage key and a
reserved SQL alias; corrected queries and these diagnostic failures are acknowledged in the records.

Preparation of the second product exposed a planner issue for an unseen, uncommitted product:
`runtime/organized-reference-prepare-explain.json` shows the empty streamed-target fallback using
a native PK prefix scan per reference. The actual frozen source has 274,189 native records,
110,900 ordinary `$ref` rows and zero streamed native addresses/references. A once-per-build
materialized target set removes that repeated native scan while preserving inline addressing,
mixed representations and scalar cardinality. The prospective and exact-current read-only EXPLAIN
receipts are `runtime/organized-materialized-reference-explain.json` and
`runtime/organized-reference-prepare-0076-explain.json`; neither executes an ANALYZE query.

The coordinator authorized graceful SIGINT of attempt 008 (exit 130), retaining its complete log.
`runtime/interrupt-attempt-008.json` binds the unchanged organized75 frozen digest
`d223994e85236d2fbe6e5b6932954ab3e6a50b4d42368ab355a092c888ad990e`, all 107,687 staged
occurrences, and the clean rollback of uncommitted final rows (no validation/publication).
`runtime/organized-claim-hold-0076.*` maintained only that exact task's claim and then stopped
cleanly before resume. There was no abandonment or staging reupload.

0076 has two native transitions (prepare plus descriptor), 27 desired objects, zero ordinary DDL,
and unchanged physical identity. Eleven affected PostgreSQL checks passed (native3, reference7,
full seal), scoped typing passed and the authoring database reproduced zero native/ordinary changes.
`runtime/native-0076.json` binds artifacts, logs and deployment. The evidence driver now admits
only an authenticated exact first frozen unfinished suffix and ordered completed prefixes. Prefix
reuse independently checks each producing task/release, protected pin, original envelope SHA and
admitted structural parent, preserving each producing release. It does not relabel old work.

`runtime/storage-attempt-009-organized-resume.log` resumes that same organized75 snapshot under
compatible native76, stopping after its seal/completion. At 15:31:51 America/New_York, new
preparation and callback/projection replay had completed, final validation was active with no
blockers, and all 107,687 occurrences were visible in the final private relation. On success,
explicit reuse of raw71 + organized75 will create the remaining enriched task under current76.


The complete current native storage chain **passed**, with all three import tasks terminal `empty`
and their leases cleared. `runtime/native-chain-publications.json` is the stable exact witness:

| Current pin | Producing release | Qualified boundary |
| --- | --- | --- |
| `4/native/7326ebf1aa74f611a4b152a68fe37ca1f9c5f76286484e566e5811c96b1faa6d` | original71 | Original native graph/access/provenance intermediate; not selected source |
| `5/organized/792b6c863f13abedefcb9ea1b1a0dbf6fac1e9e0291963525fe27c9edcfec782` | original75 | Current organized native graph plus full 107,687 occurrence index |
| `6/math-enriched/e1ffcf06fe12df156cf893d6b80554257228133bced93549b4cbba3a5016cd65` | current76 | Current enriched input for full integration; 109,933 occurrences and 1,589 encoded candidate-page records |

The last producing release is
`release:04d071213a20681590ca31cc5a5af8f7fc4071af8389d89d4d7d4b7f51927a4a`.
The final pin does not itself claim current whole-book integrated recognition: its retained native
recognition-coverage metadata has 30 records. The next current integrated phase requests every
physical page; its request outcomes/selection coverage must qualify the whole 1,589-page source.

`runtime/organized-terminal-and-elapsed.json` records the observed final validation start
15:30:49.134 America/New_York and successful completion-log write 15:45:37.670: 888.536 seconds
through validation, seal and task completion in this one run. Earlier interrupted preparation and
source authoring are outside that interval. This is an actual-run observation, not isolated speed
qualification. Enriched attempt010 completed normally; no publication error or heartbeat failure
was suppressed.

The grammar deadline/GC correction settled before integration release capture. Native77 has
one descriptor transition, 27 desired objects, zero ordinary DDL and unchanged physical identity;
its three native closure controls passed and the current candidate reproduced zero changes.
`runtime/native-0077.json` binds the authoring/deployment logs. The coordinator separately owns
actual grammar and full-suite qualification; these native controls do not duplicate that claim.

The first current source-preparation invocation created run7 and failed before recognition or
integration publication. `runtime/source-prepare-attempt-001.*` preserves the refusal. The native
record representation legitimately omits serialization-only computed table grids, while a native
export includes them. The hierarchy reader's previous raw serializer-equality check rejected this
valid declared representation. The read-only diagnostic found `/tables/0/data/grid` as the first
change; the original retained document and validated export had exactly the same canonical SHA.
No retained bytes, original artifacts, geometry or supplied field values were rewritten.

Native78 captures the bounded reader correction: verify exact payload SHA and JSON-object shape,
verify the model-owned serialization projection, and reuse the strict shared native callbacks and
returned typed model. Supplied computed grids, finite JSON, field presence, geometry and list
ordering remain checked. Native78 again has one descriptor transition, 27 desired objects, zero
ordinary DDL and unchanged physical identity. The affected union passed 130 tests, including the
three native controls; all 12 conversion caller tests also passed. Scoped typing passed. The
actual sealed enriched input loaded successfully with 1,589 pages and 101 tables and the original
field-only payload SHA. `runtime/native-0078.json` and
`runtime/native-snapshot-load-current.json` bind this bounded verification. The exact current
candidate reproduced zero native and ordinary changes, and normal target migration passed.

The second actual source-preparation invocation created run8 under release
`release:0df838beaf2ed6b228c01a8abb0be9aed0eb1d01b842dc2d145cb177c2cf0a93`.
It failed after strict snapshot loading: current JSON-backed reconciliation replay restores
candidate identity pairs as lists, and a consumer used the list itself as a mapping key.
`runtime/source-prepare-attempt-002.*` preserves the settled failure; task8 failed with its lease
cleared, without an integrated publication. The proposed consumer correction reconstructs the
qualified `(input_index, occurrence_id)` key explicitly, preserving the journal representation.
The command in
`runtime/source-prepare-command.json` requests `--scope pdf-qualification`, `--prepare-only` and
`--leave-unselected`, with the owned target and actual retained Nemotron receipts. The scope
selects five analysis roots with descendants after reconciliation, while the method requests all
physical pages because `recognition_pages` is unset. Integrated publication and source readiness
are separate pending outcomes; no knowledge extraction or default selection is claimed. The earlier
generic `regenerate-command.json` remains an unexecuted template. User commit `bc29df1c` captured
the already frozen source78 bytes during this execution; it did not invalidate source admission.

Native79 captures the qualified correspondence-key and completed-row journal boundary.
Thirty-four reconciliation checks passed, including independent matched/equal/ambiguous endpoint
expectations and materialized/Arrow parity. The actual PostgreSQL/IPC publication control passed
using `uv run python -m pytest`; two earlier console-script invocations retained their child-import
failures and receive no publication credit. Native closure3 passed; current reproduction was 0/0,
and normal target migration passed. `runtime/native-0079.json` binds these bounded checks.
No whole-book retry was launched under79: the coordinator's source review requested a concrete
multiple-observation alias control first.

That control reproduced a second ownership defect: a later equal reading mutated an earlier
materialized correspondence's evidence through its shared `_Origin` dictionary, whereas the journal
had already retained the correct earlier bytes. The failed control is
`build/pdf80-correspondence-alias-red.log`. A completed correspondence now owns a bounded deep copy
of its evidence, independently of later origin accumulation. It retains original input indices,
source identities, order and all candidate endpoints. Successor80 qualification passed: 36 affected reconciliation/actual PostgreSQL-IPC cases,
three native closure controls, scoped typing and lint. Current reproduction was zero native and
ordinary changes; normal target migration passed (`runtime/native-0080.json`). The actual
whole-book source retry003 is now running with the same input pin, `--prepare-only` and
`--leave-unselected`. No native chain pin or original artifact is changed.

The current retry is run9, release
`release:6cdfc95cd566c1dd69fac349e087e8ea2c52e1ac4ba29363685549f4d5e0cffa`.
It passed reconciliation and opened integrated build
`9372bc8fe8c89ac1d3b3a9ca57959846b81c6d44df78f09ad93402a56632056c`.
`runtime/source-prepare-attempt-003-observations.json` binds the exact current task9 replay:
A has 1,589 successes plus two preserved partial primary responses, B has 1,589 successes,
and routed C has 261 successes across 156 physical pages. A/B cover every page 1–1,589;
all 3,441 requests retain raw responses. This verifies request replay only, while integrated
publication and source readiness remain pending.

The completed reconciliation journal has 3,442 input rows, 213,448 occurrences, 270,423 relations,
45,018 mapping reports and 3,441 coverage rows. Native lowering/upload completed with 780,702
staged native rows. Companion upload is active; `runtime/source-progress.jsonl` records actual
committed milestones. No unsealed build is represented as a published source.

Run9 was gracefully cancelled before sealing after a confirmed metadata-affinity defect. Its
copied parent formula outcomes still referred to old pointers after native selection renumbering;
all first20 sampled pointers changed content. The frozen SQL metadata independently confirms
misattribution. The exact diagnostic, interruption and settled state are retained in
`runtime/source-prepare-attempt-003-*.json`. Run/task are cancelled with no lease; the build stays
frozen, one successful native-callback receipt remains and protected publication count is zero.
Frozen Arrow and access projection were hard-linked into
`runtime/private/integrated/task9-stopped-001/` before normal cancellation cleanup. No native
chain pin, staging row or original evidence was abandoned or replaced.

The operator then prioritized avoiding repeated validation work over choosing16 versus32 workers.
The bounded read-only accounts are [validation capacity](validation_capacity.md) and
[metadata affinity](metadata_attribution.md). The implemented corrections and their qualification boundary are recorded below. No new
validation registry or host/database settings change was introduced.


## Validation work and admission correction (2026-11-01)

The SQL package now aggregates owner/membership/region inventories once, uses root reachability
and full composite lookup keys, verifies every immutable artifact stream once at complete identity
entry, and retains the exact ordered identity fold. Printable ASCII uses PostgreSQL JSON string
encoding with the previous Unicode/control fallback. Twenty-seven focused SQL controls passed,
including independent cycle, duplicate edge, missing membership, byte corruption and unreferenced
stream cases. The capacity note qualifies the result without a numerical speedup claim.

Native81 freezes the integrated metadata policy, validation contract v4 and filtered nine-argument
private reader. Its fresh-head attempt exposed an authoring defect: the explicit old eight-argument
retirement executed, while its descriptor entry survived in admission. The immutable81 snapshot
and its failed setup receipt remain preserved (`runtime/pdf81-fresh-controls.log`). Target80 was
not migrated until the forward correction was qualified.

Native82 fixes the authoring route rather than adding an old-reader stub: one declared predecessor
owns both transition and admission inputs; hash-checked predecessor admission and explicit prior
retirements carry forward; baseline65 backfill requires a currently desired identity still present
in that predecessor admission. Explicit frozen states derive admission from their own descriptor
and guard, and incomplete explicit sources refuse clearly. Three focused retirement/authority
controls passed, including unchanged successor absence and intentional reintroduction.

The ordinary82 candidate has30 desired objects, one descriptor transition and zero ordinary DDL.
All three fresh-head native controls passed, and the next current candidate has zero native and
zero ordinary operations with byte-identical admission. The owned target migrated normally
80→81→82; physical model f013 is unchanged from81. Exact hashes and logs are bound in
`runtime/native-0082.json`. No failed attempt was removed or assigned acceptance credit.
Actual integrated book rerun and consumer readiness remain pending the coordinator's publication
checks; cancelled run9 is still unqualified and its frozen/raw evidence remains preserved.
