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
