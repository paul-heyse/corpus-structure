# PostgreSQL typed-domain execution · 2026-11-09

The [owning series](../../../plans/postgresql-typed-domain_2026-11-09.md) owns PTD-00–02 state.
The model-change request binds the acquired development predecessor to the typed source change.
Table shapes remain unchanged; source-derived companion projection identities and execution ABI
require regenerated native admission products. Preview/candidate/deployment and scoped test outcomes
are recorded in the owning plan after execution. No benchmark or quantitative benefit is claimed.

## Native delivery

2026-11-09: final preview `79b053fa24aa4f94b9c23797ee475aa1`, rollback-only candidate
`708d49125fd1412ca852c0568f1611ec`, registration `c503278362e74579950de718cc7079a1`
and deployment `f5cffb0c7ffe4065ba623c4b3738146f` **passed** through `uv run ci model change
preview`, `candidate`, `register` and `deploy`. The exact request is [model-change.yaml](model-change.yaml).
Candidate review used `ci model change inspect --view patch` and `inspect-candidate` plus the
emitted migration source. Five native updates and physical-contract registration preserve table
shapes while replacing source-derived projection and admission identities. The frozen files live
under `python/corpus-structure/semantic_alembic/versions/semantic_ptd_typed_bindings*`.

Deployment reached `semantic_ptd_typed_bindings` from `semantic_pm2_named_pieces`, archiving and
admitting `release:2498340837f5fe3a4e118bdbf00811e67a2912be8e79d3a2765d7372a6cf01de` on the
acquired development target. No project activation, run promotion or default change was performed.
Earlier previews `017fa80d23ed427fa0504db600e27e1c` and `6416f1ffbb384b5ba18f979891e33bd6`
were superseded by final generated-source preparation; neither was deployed.

## Runtime compiler integration correction

The first native acceptance run `b354ccddde814329bf04e6b2bd7c0ae4` **failed** (43 passed,
three failed): the native runtime-binding validator still required compiler27. The correction
supports27/28 and requires manifest/compiler equality with the archived execution model, preserving
the start_run ABI fence. The new compiler_mismatch test independently attempts supported-but-wrong27.

The [follow-up request](runtime-model-change.yaml) binds the exact first PTD predecessor.
Preview `e9453551c1d84cd3af072113608c40ff`, rollback-only candidate
`a0e15cb84b564de0a8f54e4161b2a840`, registration `9deb8c2a7c2a4fbda7937bba43beeb8f`
and deployment `a488fc505b664419be2de459ce8e46b9` **passed** on 2026-11-09 via the same
ci model-change stages. Two native operations and zero ordinary operations reached
`semantic_ptd_runtime_compiler`; the semantic release remained unchanged. Both frozen revisions
are retained. Independent source reviews found no material findings in PTD01, PTD02 or this guard
correction; reviewers did not run tests. Final affected functional selections follow this migration.

## Final functional selections · 2026-11-09

Both commands use `uv run ci test --json --` followed by the following module paths under
`python/corpus-structure/tests/`. Source was frozen and the acquired native head was
semantic_ptd_runtime_compiler. These are scoped package controls, not PTD-11 qualification.

- **passed**, 135/135, result be28b618badb4ea8a26cf3de610658cc: semantic/test_operation_call_generation.py,
  semantic/test_typed_realization.py, semantic/test_core_operation_calls.py,
  semantic/test_companion_call_bindings.py, semantic/test_projection_recipe.py,
  schema/test_relational.py, semantic/test_companion_export.py,
  semantic/test_database_description.py, semantic/test_interop.py, db/test_adbc_lifetime.py,
  semantic/test_runtime_bindings_native.py.
- **passed**, 46/46, result950e50b599334c85919d5fecebe1281d: semantic/test_companion_export_native.py,
  semantic/test_columnar_journey.py, semantic/test_analytics.py, semantic/test_capture_policy.py,
  semantic/test_capture_capacity.py, semantic/test_read_contracts.py.

The runtime controls include unsupported compiler and supported-but-mismatched compiler refusals.
The ADBC controls include real cancellation and driver/resolver parity. Independent expected rows,
closed values and SQL/JSON null controls cover companion materialization and actual detached export.
Final result IDs and both deployment IDs are held for the owning plan.

Earlier results remain distinct: a645562e6e254c7a83f482fcba6a25ec (50 passed/one stale native ABI
failure),393f274eed72444596c9386197168cd8 (three passed/one formatting assertion, repaired),
1f77392c8cfe42a5885e88c6fc6f17ea (14 passed/four incorrect implicit-principal expectations,
repaired),27fbb02fa1644bb18f6a05321445dddd (seven passed/one stale native ABI failure),
and b354ccddde814329bf04e6b2bd7c0ae4 (43 passed/three compiler-guard failures, repaired).
Final full selections supersede these obligations without erasing their original outcomes.
The earlier d34df6bf976b4e2fb81f949f5a7e8922 passed122 before the runtime correction;
the final135 rerun covers that selection plus the runtime controls on corrected native context.

## PTD-03–09 native delivery · 2026-11-09

The [continuation request](continuation-model-change.yaml) binds clean 8afc18ad9 and predecessor
semantic_ptd_runtime_compiler. Final preview 2394ddcbac2449bf95a3626e007ec6e8, rollback-only
candidate 4225ba41270048e1896a58590561edcf, registration 7a83276831af42c9bd2c7b8d19ec6883 and
deployment 68b7e28b67c145e88daaac717fb4bd32 **passed** through the existing ci model-change workflow.
Earlier preparations were superseded before effects; only this final candidate was registered.
Frozen semantic_ptd_explanations files preserve the existing revision history.

The native transition changed sem.require_archive_bytes, sem.require_execution_projection and
data.execution_contract_descriptor: three native operations, zero ordinary operations. Qualified
identities, owner and ACL preservation were inspected through the new operations view. The SQL
view independently exposed the exact compiler allowlist edit at original line523 of retained
closure.sql, including before/after text and original character offsets. No submitted data query
was executed by inspection.

Development reached semantic_ptd_explanations, archiving/admitting/verifying
release:8b4ac3cba09cfd6d7cdf17bb58e1739b0e8e7b0e6f627a352545821d8bd82d4d. Semantic compiler 19
retains18 reading; execution compiler remains28. No default, project activation or promotion
changed. The acquired target remains corpus_structure_dev, PostgreSQL18.6, port5434, OID 25921445,
system identifier 7701811359771751232, maintenance principal paul.

Independent source reviews covered checked occurrence authority, v2/v3 reading, exact retrieval,
metadata attribution, coverage correspondence/custody/cursors, and frozen SQL/native inspection.
Repairs addressed lost origins, mixed metadata provenance, exact independent export metadata,
retained before-source/deletions/CRLF, publication-before-settlement and deterministic diff refs.
Reviewers did not run product/native suites; one review used fresh-process deterministic-edit
checks. Their findings were repaired within this execution scope.

## PTD-03–09 final functional union · 2026-11-09

All following selections use `uv run ci test --json --` and paths beneath
`python/corpus-structure/tests/`. Production source was frozen for each final selection;
read-only report repairs affect the read selection and do not invalidate the independent
analysis/retrieval or native-authoring inputs. All final native selections use the registered
`semantic_ptd_explanations` context (isolated native-authoring fixtures retain their own acquired
identities). Actual source/context applicability remains bounded to these packages.

| Result | Outcome | Selection |
| --- | --- | --- |
| `0ae75b9e833541f6bb869eb8b2113a69` | passed · 135 | semantic/test_projection_analysis.py, test_projection_analysis_products.py, test_operation_reporting.py, test_operation_reporting_native.py, test_published_operation_reports.py, test_prepared_sql.py, test_contextual_enrichment_native.py, test_contextual_query_replay.py; methods/test_contextual_candidates.py |
| `ccb53a58e65540ac82f6a7f6bf882778` | passed · 29 | semantic/test_database_description.py, test_coverage_comparison.py, test_companion_export_native.py, test_companion_export.py, test_interop.py |
| `de4136c30b534910a2a82eb371363cdd` | passed · 27 | test_cli_model_inspect.py; schema/test_model_explanation.py, test_model_change_preview.py |
| `cecab02c994640bb8709119c2f6447d9` | passed · 23 | semantic/test_alembic_native.py, test_native_candidate_cli.py |
| `2f9e04ef39c8412e93e8de5ebcf3931f` | passed · 6 | semantic/test_pm2_parser_stage_native.py, test_pm2_result_native.py, with `-k 'not alternate_domain_parser_run_retains_siblings_after_profile_refusal'` |

These are 220 distinct selected nodes, not a sum of all intermediate attempts. CLI/MCP report
consumption, actual PostgreSQL metadata/retrieval/custody, offline external Arrow consumption,
and real restricted-principal native operations have explicit controls. Mocked provider outputs
in plumbing fixtures do not establish live provider qualification or extraction quality.

The extra seven-node reader regression invocation `f8e7ea3e1da9400a814bb147f1a80850` was
**blocked**: six passed, while the alternate-domain parser transfer requires opt-in locked native
assets (`CORPUS_PM2_NATIVE_TEST_ASSETS`). That provider-transfer case is excluded from this
provider-free package qualification, not silently counted as passed. The applicable six-node
rerun above passed. PTD-11 must reassess the applicable series/provider union; no current
live-provider result is claimed.

Preserved integration failures include `6cc620cd12f44974a7c809e4b4ff7e7b` (two transient runtime-pin
mismatches during generation); `9df38c84cba1408a9ea00ac6dd68210e` (27 passed/two fixture expectation
failures); `0211bc3f050f457b94782962b9518dc9` (28 passed/one real continuation failure: ephemeral
capture ID was incorrectly hashed); and `5ec2780f777e4272877d0412200bea4c` (22 passed/one managed
SQL fixture missing required CREATE OR REPLACE). Final full selections cover their applicable
obligations after repair. Earlier reader failures before deployment were the old native compiler
allowlist refusing19, not permission to weaken archive identity checks.

The final continuation includes explicit reflected ENUM/DOMAIN identity and mixed-field metadata
provenance; cursor identity preserves stable contexts while displaying each capture ID. Candidate
source inspection preserves deletions, CRLF/Unicode, retained before-source and unchanged siblings.
SQL diagnostic publication precedes settlement, and stable edit references/order do not confer
semantic-equivalence claims. Large-file views expose bounded changed-line excerpts from retained
text without reanalysis. The final independent metadata oracle specifies actual source/type values
rather than comparing two generated schemas as its correctness oracle.

Final test/deployment/preview/candidate receipts and the named failed/blocked attempts are held
for the owning plan. Broad series qualification, Rust, live-provider transfer and benefit benchmarks
are **not_run** for this package boundary. Final formatting/typing/lint/model/docs outcomes are
recorded in STATUS and the coordinator.

## Completion repairs and PTD-10 execution

Execution began at clean `489e78b06`. The owning coordinator retains CA01–04 and both PTD-10
slices; investigation dispositions and PM2 defaults remain unchanged. Three isolated implementation
worktrees were integrated into main and removed after their clean changes were cherry-picked.
Integrated executable source and frozen native delivery are committed as `4d89b7c3b`.

CA01 validates explicit anchored correspondence edges without treating inherited model-to-physical
backreferences as physical self-declarations. Independent review identified a schema-level-slot
bypass in the first repair; direct and inherited schema-slot cases were added and the focused
managed run `78a96e149215451a915ae04cb5798a67` passed17 after correction. CA02 extends the existing
connection lifetime with close-only child ownership and append-only cleanup failures. CA03 changes
only LocatedValidationReport to v3 and delegates optional detail to the existing retained pager.
CA04 adds an actual reader-role inaccessible-relation control, rather than an invented missing table.

PTD-10 keeps generation-tagged deltas in the existing trusted workspace and counts INSERT/RETURNING
CTE results; final semantic facts/proofs and publication remain separate. A one-entry reader cache
retains only deeply immutable contextual preparation, with per-query admission and borrowed snapshots.
Initial cache controls passed5 (`174dbf24ba06452882627fa19a70b753`), then7 including source-reader
lifetimes (`99be4c5ef8c74e49abcf68575c3f2bcb`), then10 after rejecting mutable record lookalikes
(`aa67389e61b346aab81eb8344b30a32f`). These are successive scoped runs, not additive qualification.

### Frozen native delivery

The [completion request](completion-model-change.yaml) binds semantic_ptd_explanations on the
acquired dedicated development database. Preview `8049ee9347024b9e94bd3e465d2e1029`, rollback-only
candidate `b3d73252b5174fb590f4123312441f0b`, registration `3a063ff60d574d2f9ba8d6b7fea65417` and
deployment `e8bfe22b0e9a45b3a054b6fbb4bdd3af` passed through the installed model-change workflow.
Candidate operations inspection showed exactly three native body changes: begin/end inference
workspace and execution_contract_descriptor, preserving owners/ACLs and zero ordinary operations.
The workspace functions now use current source custody under the existing frozen authoring owner.
Earlier preview `c4a6ad708877408e8579ce652fe9b2a1` and candidate `3df400d617ff48e98b40e05a14f4fe11`
were superseded before registration when inspection showed the bootstrap workspace functions were
not yet routed to their changed source. No earlier candidate was deployed or overwritten.

Deployment reached semantic_ptd_completion_repairs and archived/admitted/verified
`release:40ec92fe2798e6567132154a20f080e6137f956869eb657dbf3973f490c2252b` on
corpus_structure_dev, PostgreSQL18.6, socket5434, OID25921445, system identifier7701811359771751232.
Semantic compiler19, execution compiler28 and old readable products remain unchanged. No project
activation, run promotion or default change occurred. Runtime inputs already capture the changed
modules through the existing package source footprint; no second provenance registry was added.

Independent implementation reviews found no remaining material issue after the CA01 follow-up;
reviewers did not run native tests. Initial typing diagnostics caught an erroneous import rewrite,
missing normalized-library casts and deliberately invalid test inputs without casts; those were
repaired. The coherent endpoint types, lint and model consistency commands passed before authoring.
Functional acceptance and final-source qualification are recorded below after their actual runs.

### Scoped functional acceptance · 2026-11-10

`uv run ci test --json --` with the20 affected modules selected306 nodes in managed result
`41a05bca8d3e4b1bb040352783e270fa`:304 passed,2 failed. These failures were fixture errors:
subproperty_of was not a supported model key, and the frozen-head provenance witness retained a
compiler27 expectation. The explicit LinkML is_a/inverse/flag fixture now has a finite independently
specified nine-edge closure. Retry `d5bffc40ceeb4384817c7c94e96dcec7` passed that case but retained
the old compiler assertion; retry `d4711850662d41e9b2a3ac2b211ef249` passed the corrected witness.
No production/native changes occurred between these attempts.

`ci test coverage` over that chain reports306 required node identities covered, zero unresolved,
no missing required lanes and complete required native observations. Its aggregate status retains
failed attempt history and marks source differences. The coordinator accepts the two explicit
fixture corrections/formatting/evidence documentation for this bounded result; a coverage report alone is not complete
qualification. Original failed attempts and final receipts are held. The current inaccessible
relation, real ADBC failure custody, validation/archive detail, trusted generation workspace,
resident/transient retrieval and Reader controls are included in the20 modules.

`uv run ci check --json` passed on integrated production source, including typing, lint, dependency
policy, docs and clippy. Empty rule lanes report not_run. `uv run ci model check --json` passed.
Rust context: rustc 1.101.0-nightly (2d20b42b8, 2026-11-04). The broad campaign and affected-source
replacements are recorded below; PTD-11 adoption remains separate.

### Broad verification and repairs · 2026-11-10

Broad `uv run ci test --json` settled as **failed** in `2f5991c83eef42d98a8c3657c264fc77`:
ordinary selected 5,700, passed 5,687, failed 11 and blocked two; exclusive fault selected/passed eight.
No worker loss or interrupted custody was reported. Passing replacements cover all 11 failures;
the original receipt and all following attempts are held.

| Managed result | Actual selected scope and outcome |
| --- | --- |
| `4da4034d3624439da0f951eee0d8f35f` | **passed 53**: full CLI, ADBC lifetime and PM2 source modules; existing fresh CLI/MCP import assertions unchanged |
| `6e4640940c8d41fd9c4c6abf98a0d4d8` | **passed five**: explicit registry, PreparedRelease fixture, semantic archive/compiler and execution ABI expectations |
| `9c85162e9d8f46b5bbb872618a4838c3` | **failed one**: added redundant late Alembic lookup encountered the deployment fixture's deliberately poisoned bytecode; no native claim taken from this attempt |
| `8387b5b538d240238224343e5741844d` | **passed one**: corrected exact non-head deployment, retained resumption, independent successor descriptor and separate activation control |
| `e1d9a4ec39934413b1a45500269914e8` | **passed six**: installed test-evidence reporting, expanded redacted diagnostics and bounds, custody and coverage controls |
| `c2b3f0a5e78b4c058e570345d16b20aa` | **failed**: 56 selected, 53 passed, three export acquisition mocks still patched a removed module alias; native analytics/export/description/interop included |
| `366d5148cd8e4ccf93e8affb62316973` | **passed three**: exact retry of those corrected driver acquisition/cancellation/failure-custody controls |

The CLI import chain loaded PyArrow through database description → shared ADBC acquisition; the
MCP chain loaded spaCy through contribution composition → PM2 source → sentence preparation.
Drivers now load during actual acquisition; the sentence-token constructor loads only during the
HanLP layout operation. Connection/type annotations stay typing-only. Frozen contextual preparation
and its exact immutable-record guards were not weakened. Consumer mocks patch actual driver modules.

The M1 registry already had `structure.definition_declaration_components`; the contribution fixture
omitted the public PreparedRelease definitions tuple. Other stale expectations named semantic
compiler 18/execution ABI 27 instead of current 19/28. The deployment fixture incorrectly combined
current prepared products with frozen DMA-native 18/27 admission, causing `archive manifest identity
differs` after migration. It now uses explanations → completion_repairs. Actual selected-revision,
unapplied independently altered successor, resume and separate activation checks remain. The extra
late head lookup was redundant with its earlier non-head proof and incompatible with its deliberate
poisoned bytecode control; removing it changed no production behavior.

`ci test failures` previously clipped the decisive ReleaseConflict message at 600 characters and
offered no larger typed view. The ordinary managed JUnit role supplied the diagnosis once; the
owning CLI is now repaired. `uv run ci test failures 2f5991c83eef42d98a8c3657c264fc77 --lane ordinary
--diagnostic-chars 32768 --json` **passed**, exposing that exact message without exporting artifacts.
The new bound ranges from 1 to 32,768, defaults to 600, redacts before clipping and excludes source/
captured streams. The six reporting controls independently check redaction, full text and refusals.

`uv run ci test coverage` with the broad result first and all seven table results then supplied
**5,706 covered of 5,708 required identities**, no missing lanes and two unresolved nodes. Its
aggregate outcome remains **failed** with original attempt history; neither delivery of the report
nor the covered count establishes full-series qualification. Source differences are expected:
post-broad executable changes are the two import boundaries and the default-preserving diagnostic
option, plus the stated test fixes/formatting. All affected responsibilities have passing selections.
These changes are committed as `f56cddc4b`; initial integrated delivery remains `4d89b7c3b`.

Native context differences include intentionally isolated historical migrations and bare/null
revisions. Broad ordinary observation reports 962 required native nodes, zero native unresolved;
the fault lane reports seven required, zero unresolved. Passing affected runs report complete native
observations where required (six, one and 16 respectively, overlapping rather than additive).
The intermediate deployment attempt alone reports `no_claim` and contributes no native acceptance;
its successful retry observes explanations/completion_repairs and preserves the isolation boundary.
The coordinator accepts this source/context applicability only for its declared delivery claim.

Unresolved cases remain **blocked**: the GLiNER native-boundary diagnostic requires explicit
`CORPUS_GLINER_DIAGNOSTIC=1` with the pinned Base checkpoint; alternate-domain parser transfer
requires `CORPUS_PM2_NATIVE_TEST_ASSETS` naming locked native assets. Neither opt-in was selected;
no live-provider/transfer-quality claim is made. Their prior premises remain PTD-11 inputs.

Final `uv run ci check --json` **passed** after fixing the last export mock alias found by its
earlier type check. Empty rule lanes were **not_run**. `uv run ci model check --json` **passed**
at revision 0.6.5, digest prefix `89b083ed4152`. Fresh `uv run ci db status --maintenance --json`
**passed** on corpus_structure_dev at semantic_ptd_completion_repairs, with the same acquired
database identity listed above. Rust functional selection was empty, **not_run**; rustc context is
1.101.0-nightly (2d20b42b8, 2026-11-04). Benchmarks were **not_run**. PTD-11 assembled review,
remaining qualification/adoption and PM2 return handoff remain open in the coordinator.

Publication and handoff: `uv run ci docs check` and root `just turn-end` **passed**, 2026-11-10.
The publication check found zero link errors; the two pre-existing phase-0 descriptor-tag warnings
remain outside this change. Concurrent domain-data-model research/review documentation is preserved.

## PTD-11 assembled acceptance · 2026-11-10

Source entry `8e69e2b5f` was clean. Fresh `uv run ci db status --maintenance --json` passed at
semantic_ptd_completion_repairs on the original acquired development identity. Native candidate
`b3d73252b5174fb590f4123312441f0b` operations inspection passed: exactly begin/end inference
workspace and execution descriptor body changes, preserving owners/ACLs. Retained preview
`8049ee9347024b9e94bd3e465d2e1029` SQL inspection passed with explicit structural limitations for
multi-statement PL/pgSQL; this is frozen source inspection, not execution or a fresh candidate.

Fresh `uv run ci schema check --domain statistics --dependency-detail --dependency-limit 2 --json`
passed and reproduced release40ec92fe2798e6567132154a20f080e6137f956869eb657dbf3973f490c2252b and
execution19c58f16a1e8d8aacf80cc8553799ea42260467832d74f5fb767a53a0bc11821.
Validation remains v3; helper bodies are explicitly unassessed and the requested occurrence page
is bounded rather than a completeness claim. `uv run ci db check --release
release:40ec92fe2798e6567132154a20f080e6137f956869eb657dbf3973f490c2252b --json` passed through
the actual reader, matching that execution identity and physical89a7c561254db10003b43437832e1188e02ccfebe68e00913b1f40e6fbce7e52.
These connect current compilation, retained authoring and actual native admission/read without
changing project activation, selection, defaults or historical pins. Final test/review receipts follow.

### Assembled review and focused controls

The independent assembled design/target review consumes audit publication044915435 and source8e69e2b5f.
Its bounded judgment accepts all four change/failure scenarios, with no new blocking finding or rule
impact. Reviewers ran no product/provider/native tests; actual qualification remains separate.
The review and new reader acceptance are committed as dfe77f5a3; executable production code is unchanged.

| Result | Scope and actual outcome |
| --- | --- |
| `456148ba0629437bb3ea156ba49de628` | **passed one**: real pinned GLiNER CPU boundary diagnostic, explicit CORPUS_GLINER_DIAGNOSTIC=1 |
| `f126b0c67f8f4d54947de6102c8ef6e0` | **passed one**: actual HanLP/Maverick/Dipo CUDA transfer under locked build/models/pm2, successful siblings plus deliberately wrong-profile refusal |
| `31f61b3ea77f4d729d8ccf56825ecea6` | **passed 73**: shared generated/call/type controls, actual archived CLI/MCP reporting, composed frozen native changes, exact deployment/resume, completed native coverage and disconnected four-family exchange |
| `843fe40c43804d2091606401e62a72d0` | **failed**: two selected, existing composed retrieval passed, new native reader case lacked its required private.contextual fixture declaration |
| `fe2dcae5558145e89655f2f880481711` | **passed one**: corrected parameterized real ScopedSourceReader preparation/snapshot journey |

The new case spies the actual Core relation constructor and runs real native retrieval. Independently
expected dense/alias/quiet outputs, query refusal on a preparation hit, pool checkout/checkin,
closed borrowed Connection objects, owner restoration and distinct reader preparation are asserted.
No retrieval mock or new close lifecycle is introduced. The fixture correction changes collection
identity; held exact retry `2d6039412c9041c0931ab084a12f36ed` validly refused stale collection
rather than executing a different node. A precise typing annotation on normalized vector kwargs repaired the endpoint type diagnostic.
All named functional results are held, including failures/refusals.

Fresh full campaign `ca15c575254346db8552f611bdd5f071` ran with both explicit opt-ins:
`CORPUS_GLINER_DIAGNOSTIC=1 CORPUS_PM2_NATIVE_TEST_ASSETS="$PWD/build/models/pm2" uv run ci test --json`.
Its settled scope/outcome and affected replacement are recorded below. Source differences during qualification are
recorded by managed invocations; no native migration/default/project activation is performed here.

### Live-campaign GLiNER protocol timeout repair

While the full campaign remained active it reported the controlled production-child-loop test.
The ordinary managed failure view was legitimately partial until settlement. A bounded read of
that node's provisional crash message (no source/captured streams) established `native GLiNER
operation timed out` for context one. This diagnostic fallback was not used as final qualification.
An unchanged isolated reproduction passed one in held `117e8de814a74ce4a27fb23ce3d714b2`, consistent
with load-sensitive startup rather than a deterministic protocol error.

The positive recovery test allowed five seconds for spawn, imports, native preparation and IPC.
Its local profile now allows 60 seconds, because its assertion concerns continued protocol use after
preparation refusal, not startup latency. Production deadlines and the explicit 0.5-second timeout/
kill/join test are unchanged. This test-only repair is committed as `8ae0b9617`.
`CORPUS_GLINER_DIAGNOSTIC=1 uv run ci test --json -- python/corpus-structure/tests/methods/test_gliner.py`
passed all 34 tests in held `37900849e37a4208b7cf2219555aa70a`, including the real checkpoint diagnostic,
protocol recovery and strict timeout controls. The running broad attempt retains its original failure;
final settled coverage will account for the affected replacement and its exact source footprint.

### Final PTD-11 qualification · 2026-11-10

Broad `ca15c575254346db8552f611bdd5f071` settled failed with 5,701 ordinary selected/5,700 passed/
one failed, and all eight exclusive fault checks passed. There were no blocked nodes or unsettled
custody. Both required real provider cases and the added native scoped-reader case passed in this
fresh campaign. The settled `ci test failures --diagnostic-chars 32768 --json` report confirmed the
single protocol startup timeout. Held passing module `37900849e37a4208b7cf2219555aa70a` supplies the
final affected source after the isolated test budget repair.

`uv run ci test coverage ca15c575254346db8552f611bdd5f071 37900849e37a4208b7cf2219555aa70a
--view unresolved --limit 20 --json` passed delivery of the bounded report: 5,709 required/covered,
zero unresolved, no missing lanes, two complete native observations plus one not_required context,
no context unknowns. The aggregate status remains failed from preserved attempt history. Source
and native-context differences are exposed; the coordinator's final qualification section explicitly
accepts the scoped union and final-source applicability. The test budget change is the only executable
mutation during broad execution; no production/native/schema/runtime implementation changed.

Final repository check passed types/lint/docs/dependencies/clippy and process checks; empty rules
were not_run. Model consistency passed 0.6.5/89b083ed4152. Fresh post-campaign maintenance status
again observed semantic_ptd_completion_repairs and the original OID/system identity. Rust context
remained 1.101.0-nightly (2d20b42b8,2026-11-04); Rust functional selection was empty/not_run. No
benefit benchmark or broad quality claim follows. Final publication and handoff checks are recorded
in the coordinator/STATUS. The selected series is complete at that declared boundary.

Required native observations: ordinary 963 and fault 7, each with zero native unresolved. The
GLiNER module replacement requires no database observation; real CPU provider behavior is exercised.

Final publication `uv run ci docs check --json` and root `just turn-end` passed, 2026-11-10;
zero link errors. The two pre-existing phase-0 descriptor-tag warnings remain outside this scope.
