# Attributed private source evidence and prepared context2

**Tested scoped candidate · 2026-11-03.** ADR-0051, source baseline `9374ac37`, isolated
`codex/m1-source-evidence`. This evidence concerns pure binding/context and native private
source custody. It does not establish final forward migration, producer integration, public
record publication, model inference, scientific correctness or complete M1 qualification.
No live application/default database was migrated. Every native database used the existing
PgAdmin disposable lifecycle on dedicated `18/corpus` and owner-tagged
`cs_sem_m1_attributed_<uuid>` names; cleanup follows context exit.

## Contract

The released observations model owns optional v2 anchor binding (`version=2`,
`policy=attributed-selected-source-2`, `relationship=primary|selected_context`). Missing binding
retains the old same-pin canonical contract. `selected_context` asserts run-selected same-product
custody, not structural note/declaration applicability. Every anchor retains its complete own
projection/recipe/source-view pin; primary occurrence anchors remain selected canonical/native
addresses under `source-anchor-membership-1`. Captured-recognition anchors cannot replace them.

`captured_recognition` has an explicit selected occurrence, retained product and occurrence,
direct decision relation/outcome and exact endpoint role (`input|evidence|alternative`). The
address retains the complete unchanged provider occurrence JSON and observation JSON, including
original precision/region and available image/raw response provenance. Text start/end locate only
the captured occurrence string. Current supported provider precision is unknown/coarse/block,
without provider exact bounds; unsupported provider contracts refuse. Legacy `recognized_text`
continues to resolve canonical native text.

`ops.record_captured_recognition_text` composes protected sealed context selection and exact
persisted endpoint targets with admitted recognition product/body/occurrence custody. It never
accepts Python traces or caller text as native authority. Direct decisions with
selected/added/replaced/retained_alternative outcomes can be read only when authenticated output
and recognition endpoints tie them to the selected occurrence. Endpoint alternative/upstream
retained disposition remains explicit and does not erase genuine captured literal candidate
text. Rejected decisions lacking such an authenticated output route remain unsupported; raw
upstream traces can remain computation dependencies. OCR decoded word/line admission and arbitrary
ordinary cross-product composition remain unsupported.

Context2 requires invocation-owned `PreparedNativeSources`; immutable source pins, validated
partition, item/cell locator map, interval index and dependency digest are prepared once.
Subsequent contexts require the exact same source objects. Sources, considered/rejected
candidates, retrieval outcomes, relationship reasons, policies and bounds affect identity.
There is no global cache or durable preparation store. Context1 and proposal frames2/3 retain
their meanings.

`context.read_span(..., prepared=effective_release, policy="synthetic-whitespace-1")` returns
ordered genuine pieces and gap/model-span diagnostics. `.original_pieces` never joins them into
a literal quote. `.receipt()` validates against released `RecordContextReading`/`RecordContextGap`
and belongs in computation diagnostics; it does not alter source evidence-set identity.
Synthetic punctuation/labels, synthetic-only or boundary-gap readings, unsupported policies,
lossy maps and mismatched model text refuse. Attributed accepted multi-piece literals require
original piece sequences. Private accepted standing continues to refuse native admission.

## Attempts and commands

Run from the main checkout to use its uv environment, with the isolated source first:

```
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-source-evidence/python/corpus-structure/src uv run pytest <isolated test paths> -q --tb=short
uv run pyrefly check --site-packages-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages <isolated owned Python/test paths>
uv run ruff check <isolated owned Python/test paths>
```

- **passed:** `prepare_candidate.py --out create-attempt-1`: actual CREATE of helper/completion on
  disposable frozen native100, rolled back, database dropped. This establishes SQL creation only.
- **passed:** `prepare_candidate.py --candidate --out candidate-attempt-{1,2,3,4}`: ordinary native
  candidate authoring on disposable native100. All candidates/raw stdout/stderr are retained;
  candidate4 supersedes the earlier implementation candidates. Root separately bound the isolated
  expected descriptor to candidate4's exact catalog body hash
  `3bd2bab5487ef923d99ac6aca5d2b666146c2ba31cad95494307f5691c05ef90`.
- **failed, retained:** initial pure attempt used unsupported `equals_number`; changed the released
  version constraint to supported min/max equality before the passing runs.
- **failed, retained:** `native-attempt-1.log` stopped at the exact predecessor descriptor fence.
  No acceptance waiver or monkeypatch was used; root updated the expected hash from the authored
  candidate catalog, then repeated against that exact candidate.
- **failed, retained:** `native-attempt-2.log` expected raw DBAPIError but the existing completion
  owner correctly mapped native refusal to InvariantViolation; the test now accepts that protocol.
- **failed, retained:** `native-attempt-3.log` and `native-attempt-4.log` show direct selected-membership
  removal denied by ACL and then by immutability. The revised negative test creates a real second
  run selecting only the primary view through `ops.select_source_view`; the related view remains
  extant and correctly pinned but unselected in that new run. No trigger was disabled.

## Final scoped outcomes, 2026-11-03

- **passed:** pure source contexts/record contracts/attributed evidence, 76 tests,
  `python-shared-final.log`. This includes old frame/context meanings, repeated strings,
  individual related pins, captured text versus coarse provider geometry, genuine original
  pieces/whitespace diagnostics, explicit policy and preparation reuse.
- **passed:** candidate4 native controls, 15 tests, `native-final.log`. Candidate4 precedes
  the shared report guard factoring and bulk-reader extension. Its artifact/source witness
  remains separate (`candidate4-source-witness.json`, `raw/candidate4-sources/`).
- **passed:** candidate5 native shared endpoint, 18 tests, `native-shared-attempt-1.log`.
  This covers the prior controls plus completed immutable report equality and internal-only
  helper ACL, ordered bulk report/origin metadata, one native product-pointer hydration for
  two reports, cut/duplicate refusal and predecessor absence versus explicit empty records.
- **passed:** after adapting the test harness to apply the development candidate only over
  frozen100 and otherwise use the deployed forward head, the completed-report smoke test
  passed (`native-harness-final.log`). Functional tests and exact deployment checks are not
  skipped on a newer head.
- **passed:** scoped Ruff and Pyrefly (`ruff-shared.log`, `pyrefly-shared.log`); type checking
  explicitly uses the main environment's installed packages while resolving isolated sources.
- **not_run:** final assembled forward migration/producer/publication/release qualification.
  Root owns the coherent final head and must reassess these results after integration.

The candidate5 descriptor body hash is
`117c1c849e1755dac03bc4599b3f1f1186344e63b094c2955d5699dd83bc67c0`.
`source-sha256.txt` and `raw/candidate5-sources/` retain the final local implementation,
including root-owned native registration, exact descriptor and software input closure changes.
Candidate authoring passed with four native and zero ordinary operations. The native report
custody owner is now `ops.validate_source_record_report(bigint,jsonb)`: publisher-owned,
PUBLIC revoked, no reader/writer grant. Live completion binds its actual outcome and calls this
owner; completed-origin calls require exact immutable task-result body/release equality.
Distinct anchors/pins are prepared once per report, native pointers are hydrated as one set,
and exact recognition addresses are memoized within the invocation.

The bulk Python interface is `read_private_record_reports(reader, task_ids)`; singular reads
delegate. It preserves requested order, selected/origin task IDs, release, optional cut/source/
outcome metadata, and absent versus empty records. It reads the exact task set once, prepares
producing-run source membership together, groups native readers/pointers by exact product/release,
and resolves distinct captured addresses in one protected VALUES query. No global reuse owner
or new persisted lifecycle is introduced.

`native-attempt-5.log` retains fourteen passing controls followed by a refused nonexistent
retained-alternative relation: that negative outcome exposed a missing test-fixture insertion,
which was corrected before `native-final.log`. No production guard was relaxed. Candidate5
extends that passing implementation through the shared guard and bulk reader.

## Captured context and final source-coordinate split

**Tested scoped foundation, 2026-11-03.** Context2 now also composes a separate captured-text
variant without changing canonical NativeFrameSource text. `PreparedCapturedCoordinate.from_coordinate`
consumes the released `RecordCoordinateText`/`RecordCapturedRecognition` shapes; its selected pin,
provider text and unchanged provider occurrence must agree. Supplied inputs are still unauthenticated
until the native coordinate owner rechecks actual custody. `PreparedNativeSources(..., captured=...)`
bounds address count and retained captured characters within the invocation. `CapturedRecognitionSlice`
uses exact coordinate identity and subrange. `CapturedSpanEvidence` exposes an explicitly typed
captured address and can produce the existing released RecordAnchor; it has no fabricated native
locator or source_field. Exact captured characters do not promote provider PDF precision.

`captured_dependencies` and immutable `captured_coordinates` preserve considered/rejected addresses
and release/source dependencies. Equal strings under a different product/occurrence/relation remain
different computations. The existing canonical GLiNER mapper and record assembler explicitly refuse
captured variants until adopted. Actual producer/model adoption remains open.

The final native source-only owner is
`ops.validate_source_record_coordinates(bigint,bigint,text,jsonb)`. It authenticates selected
run/view/source pins, released SourceRecord/family shape, primary canonical occurrence recipe and
real coordinates/recognition. It has no production or acceptance authority. Source aliases must be
bound by the caller. `validate_source_record_report` retains producer/configuration/outcome,
completed exact-body equality, logical alias and private accepted-standing refusal, then calls
this one source owner. Both are publisher-only internal functions. Reference wrappers separately
own evaluator/guideline/frozen-frame authority and full cross-object structural completeness.
The Python `authenticated_source_record_coordinates` mirrors source-only custody; its private
wrapper preserves task alias and accepted-standing refusal. The existing set query also requires
the supplied prepared release to equal the selected run release.

Final scope:

- **passed:** 99 deterministic mapping/record/canonical-consumer controls,
  `python-final-coordinate-split.log`.
- **passed:** 19 actual disposable PostgreSQL controls on candidate6,
  `native-final-coordinate-split.log`. Recognition inputs are retained fixture bytes; this is
  source-custody qualification, never a passed recognizer/provider/model execution claim.
- **passed:** 2 targeted source-only/private/bulk checks after adding Python/native release parity,
  including a wrong-prepared-release refusal, `native-release-parity-final.log`.
- **passed:** final scoped Ruff (`ruff-final.log`) and Pyrefly with zero errors
  (`pyrefly-final.log`). The unchanged baseline redundant ContextRefused/ValueError exception tuple
  in record_assembly still emits one Pyrefly warning.
- **not_run:** final assembled forward migration, producer/reference/publication integration,
  model execution and complete M1 qualification. Root owns those obligations.

Candidate6 has five native and zero ordinary operations; its exact descriptor hash is
`3ca53097baa97530f6753c032229b5b88fd3c4ddd552d06a7b25454e0cf8fe04`.
`production-source-sha256.txt` fixes the 15 production inputs, including both method refusal
fences and the root-owned implementation closure/native registration/exact descriptor.
`final-source-sha256.txt` and `raw/final-sources/` preserve all 19 final source/test/repro inputs.
The earlier `source-sha256.txt`/`raw/candidate5-sources/` remain the pre-captured-context,
pre-reference-split witness. No predecessor migration or frozen artifact was edited.

The first evidence-finalize invocation used a nonexistent `evidence` executable; the existing
`uv run python -m corpus_evidence` entry point is used below. Final import/line formatting failures
remain in `ruff-final-format-attempt.log` and were repaired before the final Ruff pass.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Attributed source coordinates, captured context and shared custody candidate](records/m1.attributed-source-candidate.json) | M1-03 | passed | — | 2026-11-03 |
<!-- evidence-index:end -->

## Integrated isolation snapshot

The completed isolated contribution was integrated into main at `db9c5a25` and its temporary
worktree removed. Its dirty source/evidence state and exact baseline are preserved in the
[verified snapshot](../2026-11-03_m1-public-record-projection/raw/integrated-worktrees/source-evidence.tar.gz).
Historical isolated-path commands require restoring that baseline and snapshot. Current machinery
uses the main-tree commands in the [integrated evidence](../2026-11-03_m1-public-record-projection/README.md);
this does not promote historical receipts to final native or release qualification.
