# Rebase A: TDM-01, 09, 10, 11, 12, 15, 16, 17 against 12f57dc4d (plan baseline 50827eb9f)

Paths: `tests/…` and `src/…` are relative to python/corpus-structure/ in the snapshot of 12f57dc4d;
"root X" is repository root. All statements are by reading; nothing was run. 104 commits lie between.
Method. Exhaustive (AST scans of snapshot AND of a `git archive` of 50827eb9f, so every count has a
before/after): fixture definitions vs requested names over 930 files (package tests, root tests/,
root scripts/, root conftest.py); every `from corpus_structure… import` in tests/scripts (0 missing
modules or names at both commits; `type X =` aliases handled); every test-tree `from semantic.x import`
(0 missing); every `corpus_structure/…` path string in tests (0 missing); every `semantic_bare_engine`,
`__new__`, `getfixturevalue`, `.sql` path reader, `stream` replacement, `PdfStreamReply(` site.
Sampled: bodies of tests (setup logic read only for the named tests), root tests/scripts content.
Git-changed files in scope since baseline: the only src files touched in the packages' areas are
ingest/pdf_streaming.py, ingest/pdf_worker.py, orchestrate/pdf_streaming.py, orchestrate/project.py,
semantic/data_operation_storage.py (bodies, no new signatures), and the SQL/native program modules.
UNCHANGED since baseline: orchestrate/data_operations.py, methods/native_host.py, methods/native_profiles.py,
ingest/pdf_capacity.py, ingest/pdf_build_spool.py, root conftest.py, tests/conftest.py,
tests/native_fixture_support.py, tests/math/conftest.py, tests/statistics_pack_support.py,
scripts/qualification_plugin.py, tests/methods/* (except test_nce02_cross_block.py), tests/orchestrate/
byte_admission/basis/host tests, tests/ingest/test_pdf_capacity.py. Every line cite for those holds.

## Q1. The PDF converter boundary (TDM-09), direct answers

Emitter. `StreamingPdfResult.certified_reply(self, request: PdfStreamRequest, *, on_replay)` at
src/ingest/pdf_streaming.py:573-603 (added 8a5c074f0). It takes a FINISHED result (document, spool,
status, errors, recipe, formula outcomes, `effective_options`), not a producer. Body: `write_record_batches`
(:411) with `on_batch=on_replay`; `on_replay(_ref(request.record_root/"completion.jsonl","native_completion"))`
(:589, completion reference still recomputed from a file name, now in one place); `certify_native_stream`
(src/semantic/pdf_certification.py:466); returns the nine-field `PdfStreamReply`.
Callers (exactly three): the worker child src/ingest/pdf_worker.py:105
(`result = streamed.certified_reply(request, on_replay=acknowledged)`, `streamed` from
`StreamingPdfProducer(...).run(...)` at :100); test helper `certify_controlled_pdf_stream`
tests/pdf_acceptance_support.py:34-71 (new in 1d22c41cb, trimmed in 8a5c074f0); test helper
`_certified_controlled_reply` tests/semantic/current_pdf_source_support.py:198-209.
Preparation order. Unchanged. `StreamingPdfProducer.run` (pdf_streaming.py:612) writes
`native-preparation.json` from `converter.prepared_options_report` (:627), checks identity vs recovered
pages, calls `spool.on_page(prepared)` (:637, the child's acknowledgement) and only then converts. The
child still builds payload family + spool inline (pdf_worker.py:95-101). No extracted protocol function.
Controlled-path preparation report. NOT produced by production. Both helpers write
`streamed.effective_options` as the preparation entry: `b'{"fixture":"controlled-source-search"}'` /
`…-sections"}` (current_pdf_source_support.py:230, :442) or the dataclass default `b"{}"` for the other
seven (they pass six positional args). Neither passes `native_preparation_identity`
(pdf_build_spool.py:211 reads `_preparation`; it runs only on resume, `ready_pages` :312, and
`verify_spool_recovery`), so it is harmless until a controlled path recovers. The spool is built as
`PdfStreamSpool(spool_root, check_active=…)`: no `on_page`, no payload family, no recovery pages.
`PdfWorker.stream` (pdf_worker.py:253-268) still takes ten keywords, not a request object; one production
caller orchestrate/pdf_streaming.py:421 (was :493-505, moved by 1d60efc30). Both helpers rebuild a
`PdfStreamRequest` by hand (pdf_acceptance_support.py:49-62; current_pdf_source_support.py:232-250, :410-473).
Test-side replacements today (all replace `PdfWorker.stream` with `monkeypatch.setattr`):
- Through the shared emitter via `certify_controlled_pdf_stream` (7 sites, were the "seven five-field
  doubles", all moved in 1d22c41cb): current_pdf_integration_support.py:286-302 (installed :426),
  current_artifact_support.py:120-135 (:215), evaluate/declared_record_native_support.py:191-243 (:354),
  test_pdf_materialization_native.py:60-79, test_pdf_transform_demand_native.py:90-170,
  test_nce02_native_scope.py:231-245 (`stream=list_stream` :266), rich_domain_native_support.py:132-146
  (`decimal_source_stream` :93).
- Through the shared emitter via `_certified_controlled_reply` (2): `_controlled_stream`
  (current_pdf_source_support.py:212, default :292) and `_section_stream` (:388, caller `stream=` at
  test_current_contextual_native.py:83, test_actual_e5_selected_context_native.py:152,
  test_artifact_identity_registered_native.py:70, test_contextual_workflow_native.py:133,
  factory :373-380).
- Still hand-built reply: tests/orchestrate/test_pdf_private_execution.py:144-175 (child double: imports
  `_atomic_bytes, _ref` at :144, writes preparation `{"fixture":"prepared-native"}` and `b"{}\n"`
  completion, builds `PdfStreamReply(... effective_options=options, certification=…, access_replay=…)`;
  changed by 1d60efc30/bbdf77479). Non-converter replies that stay: tests/pdf_process_support.py:83,100;
  tests/ingest/test_pdf_build_spool.py:308 (spool unit); `PdfStreamReply` isinstance check
  tests/orchestrate/test_pdf_streaming_integration.py:120.
- Not a reply but the same hand-copy of "write batches then adopt": tests/semantic/selected_source_native_support.py:136,299
  and tests/pdf_acceptance_support.py:90 (`stage_pdf_document`) call `write_record_batches` and
  `adopt_pdf_batch`/`adopt_controlled_companions` directly (present at baseline, not in plan).
Gone: `write_native_occurrence_batches` (0 refs in src+tests; removed 8a5c074f0). Test imports of
`_atomic_bytes`: tests/pdf_acceptance_support.py:50, current_pdf_source_support.py:200,
test_pdf_private_execution.py:144; of `_ref`: test_pdf_private_execution.py:144,
test_pdf_shared_streams.py:449 (unrelated: `iter_replay_artifact_batches`).
test_current_pdf_source_inputs.py:58-68: UNCHANGED and still broken. `_section_stream(rows, SimpleNamespace(recipe),
SimpleNamespace(digest), spool_root=…, …)` omits `validation_contract`, `lowering_identity`,
`payload_schema`; helper reads `options["validation_contract"]`, `["lowering_identity"]`,
`["payload_schema"]` (current_pdf_source_support.py:~468-470) -> KeyError before first assertion.
Contract control (controlled vs real child): none. The real-child test is
test_pdf_streaming_integration.py::test_real_private_native_pipeline_retains_pages_then_adopts_after_retirement
(starts ~:108; `_ScriptedDocumentConverter` :21-95 still uses `object.__new__` at :28,:33; unchanged).
Content as data / installable outside pytest: NO. Content is closures (`rows` tuples captured in `stream(...)`
functions, per-module functions); installation is `monkeypatch.setattr(pdf_worker.PdfWorker,"stream",…)` at
6 sites with a pytest `monkeypatch`; `_current_pdf_source(scenario_seeds, tmp_path, monkeypatch, *, stream=…)`
takes the fixture. A seed builder cannot enter it.

### TDM-09 table
| Part | Delivered | Remaining |
|---|---|---|
| One production owner of certify + reply assembly | PARTLY (8a5c074f0): `certified_reply` owns record batches, completion ref, certification, nine-field reply; child + both test helpers call it | The owning function the plan designed (request + producer + callback, covers preparation, spool, payload family, producer run) does not exist; `_native_child` still has the inline sequence |
| Removal of the five-field doubles | FULLY (1d22c41cb): none remain; all 7 + 2 route through the emitter | none |
| Fixture-only occurrence writer | FULLY (8a5c074f0) | none |
| Preparation report from production on controlled path | NOT | hand-written `b'{"fixture":…}'` / `b"{}"` in 3 helpers (pdf_acceptance_support.py:64-69, current_pdf_source_support.py:203-208, test_pdf_private_execution.py:146-152) |
| `effective_options` field removed from StreamingPdfResult | NOT (:386) | still the sole carrier; controlled helpers rely on it as the preparation bytes |
| `PdfWorker.stream(request)` | NOT | keyword form, 1 prod caller orchestrate/pdf_streaming.py:421; test callers test_actual_pdf_spool_resume.py:87,101,119, tests/ingest/test_pdf_streaming.py:324,374 |
| No test restates request assembly | NOT; moved | `certify_controlled_pdf_stream` (pdf_acceptance_support.py:49-62) and two sites in current_pdf_source_support.py rebuild `PdfStreamRequest` from keywords (`page_range`, `recovery_pages` options) |
| Private-name imports `_atomic_bytes`/`_ref` removed | NOT | 3 sites (above) |
| Content as hashable data + installer without fixture (TDM-08 need) | NOT | all |
| Contract control vs real child | NOT | none exists |
| `test_current_pdf_source_inputs` | NOT | still KeyError |
| Former consumers set up | CHANGED: now set up by reading (the "cannot set up" premise is false) | verify by run |
New: `pdf_acceptance_support.certify_controlled_pdf_stream` (23 importer files of that module) is a new
shared copy of request assembly + preparation placement; `selected_source_native_support.py` ×2.
Consumers counts (same as plan): importers of current_pdf_integration_support 8, current_artifact_support 2,
rich_domain_native_support 3, declared_record_native_support 14; current_pdf_source_support 43.

## Q2. TDM-10 executor
`NativeDemandExecutor.__init__` data_operations.py:634-693, unchanged (commits since: none in that file).
Reservation `self.reservation = 2 * max_packet_bytes + 3 * max_reply_bytes` :689, refusal :690-691; same
eight native interaction rows (file unchanged; line cites hold). No new seam/collaborator in production.
`__new__`/`object.__new__` constructions of NativeDemandExecutor (7, unchanged): test_data_operation_byte_admission.py:71,
test_data_operation_execution_basis.py:47,109,396,465, tests/semantic/test_d1_limitation.py:292,
tests/semantic/test_data_operation_capabilities.py:428. Missed by plan: tests/semantic/test_data_operation_consumers.py:118-142
casts a `SimpleNamespace(engine=…, model=…, demand=…, policy=…)` to the executor and calls the unbound
`NativeDemandExecutor._hydrate(executor, …)` (same private-state coupling, no `__new__`); also
`NativeDemandExecutor._retained_failure` called unbound at test_data_operation_relay.py:157,227 (static;
fine). Copied formula: test_data_operation_byte_admission.py:56 (`policy_for`) and :79 (`controlled_executor`);
`controlled_executor` def :69, 12 calls (269…751), importers test_data_operation_execution_basis.py:12,183 and
tests/orchestrate/test_execution_host.py:163,203,238,244,369,374. Module-name replacement of
`DataOperationStorage`/`DemandPlanner`: byte_admission.py:136,174; execution_basis.py:82,140-142,413,493.
Fault-injection sites unchanged: test_prepared_authority_batch_native.py:98, test_pm2_parser_stage_native.py:174-195,
current_pdf_integration_support.py:441-507. `WireCheckedStorage` tests/semantic/data_operation_binding_support.py:240-262 unchanged.
Conversion effect: production storage bodies changed (data_operation_storage.py, ~20 commits, e.g. 5a2383a02)
but no executor call surface moved; the fake dict replies the tests return are unchanged and unvalidated.
| Part | Delivered | Remaining |
|---|---|---|
| Seam 2, tests via public constructor, literal reservation pin | NOT AT ALL | all, as planned; open premise 3 (`trust_snapshot={}` replies, execution_basis.py:72,418) still to check |
Extra scope: test_data_operation_consumers.py:118-142 (SimpleNamespace executor).

## Q3. TDM-11 native host
`NativeHost._validate_startup` methods/native_host.py:196-213 (staticmethod, 11 field comparisons: provider,
profile, runtime_identity, assets, device-prefix, dtype `"torch."+`, backend, matmul_precision,
cudnn_allow_tf32 identity, native_threads.intra_op/inter_op), single caller :185; message "native host executed a
different frozen provider profile" appears in no test (grep over tests, root tests, scripts). Population check :181-183.
All UNCHANGED. Peer tests/methods/native_host_cases.py: echo metadata :22-40, `startup-hang` :11. Invented refusal
unchanged: tests/methods/test_characterization_resources.py:59-61 (`Group.startup`), test at :243-252.
Missed by plan: tests/methods/test_native_host.py:57 builds `native_host.NativeHost.__new__(native_host.NativeHost)` and
assigns private fields (reader-routing test); not the profile path. `admitted_startup_matches`
methods/native_profiles.py:165 still has no src caller; only tests/methods/test_native_host.py:617-677 (10 refs).
| Part | Delivered | Remaining |
|---|---|---|
| Public comparison, per-field cases, reach control, invented refusal removed | NOT AT ALL | all; no conversion commit touched methods/ except test_nce02_cross_block.py (30d9e53e4, unrelated) |

## Q4. TDM-12
All cited sites unchanged. `_page` tests/semantic/test_demand_results.py:20-91, 11 importers still (10 semantic + tests/evaluate/test_selected_operation_events.py:7;
list matches plan). `control_frontier` tests/semantic/selected_query_cache_support.py:27-43, 3 invented messages; users 4
(test_current_candidate_facets, test_current_composite_delivery, test_grouped_record_interpretations, test_selected_structural_readers);
production `recheck_selected_frontier` callers serve/structural_products.py:265, serve/identity_exclusion_comparison.py:133.
Population-close `Storage(DataOperationCalls)` tests/semantic/test_data_operation_demands.py:635-650 (:641 `close_data_population`) unchanged.
Encoder fakes unchanged: test_contextual_encoder_batch.py:104-128 (`(1.0,0.0)` constant), test_contextual_owned_encoder.py:23-31.
Corrections to plan counts: `_complete_ready` (test_data_operation_population_native.py:145) has FOUR importers at the baseline and now, not two:
test_data_operation_context_fanin_native.py:18, test_selected_source_acquisition_native.py:29, test_data_operation_pinned_reuse_native.py:29,
test_data_operation_transitive_read_native.py:27 (plan undercounted; not a conversion change). Test modules imported from another test
directory: by my AST scan 17 import statements in 10 files at BOTH commits (plan: 16 in 9); extra file: tests/evaluate/test_selected_native_question.py
(from semantic.test_selected_references), plus semantic/test_record_support_native.py (from evaluate.test_declared_rich_native_journey),
methods/test_m1_predicate_inputs.py, methods/test_characterization_composition.py. Relative imports: 3 in semantic/ (test_pdf_payload_validation.py,
test_pdf_stream_reconciliation.py, test_native_child_edge_guard.py), directory is a package; none in non-package dirs. Private-name imports from
non-production modules: 63 at baseline, 67 now by my count (+4 from conversion-added tests); plan said 65.
| Part | Delivered | Remaining |
|---|---|---|
| `_page` validated builder, recheck double, close double, encoder fake, cross-directory imports, `_complete_ready` | NOT AT ALL | all; add the two missed `_complete_ready` importers and the extra cross-directory files |
Note: `read_demand_result` etc. wire types were regenerated; `validate_native_wire("read_demand_result","output",…)`
(src/semantic/demand_results.py:502) was not re-read here. If the generated record type changed, the page correction is larger (plan already says so).

## Q5. TDM-15
Root conftest.py:10-57 `PREPARATION_AFFINITY` = 37 rows; hook :60-98 unchanged. Of 37 rows 23 name no fixture defined anywhere
(scan over package tests, root tests/, root scripts/, root conftest.py): source_release, record_custody_case, record_identity_case, record_graph_case,
contextual_atomic_case, local_witness_case, judged_semantic_case, interpretation_source_case, runtime_registration_case, unbound_arrow_case,
domain_default_case, domain_formula_source, resubmission_case, resubmission_historical_source, exclusion_case, exclusion_read_case,
exclusion_literal_case, exclusion_refusal_family, occurrence_case, occurrence_refusal_family, imported_declaration_case, imported_membership_case,
declared_membership_case. 14 rows resolve to definitions (13 live + the `native_read` row qualified to test_contextual_workflow_native.py): six math
(tests/math/conftest.py:34,39,44,54,59,64), statistics_pack_support.py:11,16,21, `profile` (6 definitions exist; the row is qualified to
semantic/test_hanlp_products.py:35), local_semantic_sql_batch test_local_semantic_admission.py:184, binding_native_connection
data_operation_binding_support.py:118, selected_graph_case test_data_operation_storage.py:2464 (MOVED from :2458 by 088248c53).
tests/conftest.py:101-142 `DB_FIXTURES` 38 names, 11 undefined (domain_default_case, domain_formula_source, exclusion_case, exclusion_read_case,
exclusion_literal_case, exclusion_refusal_family, occurrence_case, occurrence_refusal_family, imported_declaration_case, imported_membership_case,
declared_membership_case), 27 defined. Hook :279-282 unchanged. `record_source_*` fixtures tests/conftest.py:533-569 (6: settings + admin/writer/reader/
evaluator/admitter; five take undefined `private_source`); 0 test requests (grep over package tests, root tests, scripts). Root tests/ tree (now in snapshot):
no parallel list, no live fixture declaration, no `PREPARATION_AFFINITY`/`DB_FIXTURES`/`native_required` reference except root scripts/qualification_plugin.py
:226,:241 and scripts/test_receipts.py (read marks only); root tests/scripts/test_parallel_harness.py uses only explicit `db`/`xdist_group` marks. Root
tests/ has no `source_release` fixture (the row naming tests/test_native_run_scope.py is dead; the file exists, grep finds no `source_release`).
Four unimported support modules still exist and have 0 importers anywhere: tests/semantic/scenario_preparation_support.py, primary_formal_fixture.py,
method_dimensions_native_support.py, characterization_construction_support.py. `getfixturevalue` sites: 7 unchanged (tests/conftest.py:505;
test_db_fixtures.py:130; test_runtime_principal_current_native.py:21; test_native_fixtures.py:164,548,549,550).
Explicit `pytest.mark.db`: 58 occurrences in 21 files (57/20 at baseline; +1 in a conversion test; plan said 56/19). Rollback families
(`scenario_seeds.rollback_family`): same 4 fixture/test sites as at baseline (test_data_operation_storage.py:2465, data_operation_binding_support.py:119,
test_record_policy_completion_native.py:79 [fixture `policy_projection_connection`, plan's "never listed" fixture], test_scenario_seeds.py:101,113).
New fixtures from the conversion (10): product_connection, read_boundary_control, release_guard_context, event_scope_connection, adoption,
generated_companion_reads, validation_controls, feature_body_control, source_capture_control, support_control; all built on `semantic_bare_engine`,
`native_rollback` or `binding_native_connection` (already in the table); none declares a group. test_support_trust_native.py imports
`binding_native_connection` (already grouped "ddo_binding_source").
| Part | Delivered | Remaining |
|---|---|---|
| Whole package | NOT AT ALL (no conftest, root conftest, qualification-plugin or math/statistics commit) | as planned. Counts unchanged except selected_graph_case line :2464 and explicit-mark counts |

## Q6. TDM-16
Production `.sql` under src/corpus_structure/semantic/sql/: 27 at baseline, 16 now. DELETED (commit): data_operations.sql 2910d9817;
data_operation_support_scopes.sql d422c48e7; data_operation_external.sql 623e49ccf; pdf_observation.sql 8ec93520c; pdf_record_artifact_identity.sql and
pdf_record_identity.sql 364ff2f76; data_operation_bindings.sql b1c10cbbf; pdf_record_access_correspondence.sql 6091bbd43; pdf_record_logical_identity.sql
ee20c99dc; pdf_record_context.sql 5341e93dd; pdf_record_proof_reader.sql 07fb187cf. Also deleted earlier: execution_projection_check.sql.
REMAINING 16 and loaders:
- admission.sql: native_products.py:182,390; schema/model_deployment.py:53; read as text by constraint_custody test.
- closure.sql: semantic/target_installation.py (`sql.joinpath(filename).read_text()` :~224, :~243).
- identity.sql: target_installation.py (same loop).
- data_operation_task_checks.sql: data_operation_protocol.py:126; native_products.py:186; target_installation.py:302.
- contextual_neighborhood.sql: data_operation_storage.py:498; semantic/contextual_neighborhood.py:77.
- data_operation_source_admission.sql: semantic/data_operation_source_native.py:14.
- data_operation_visual_read.sql: semantic/data_operation_visual_read.py:16.
- source_originals.sql: semantic/original_document_contracts.py:19,126.
- pdf_descriptor.sql: target_installation.py:78. source_record_recognition.sql: target_installation.py:92.
- NO loader in src (grep of src, tests, scripts): exclusions.sql, fact.sql, selection.sql, validation.sql, source_record_graph.sql (read only as text by
  test_data_operation_constraint_custody.py:94-95 for source_record_graph.sql); data_operation_identity.sql (only reader:
  test_data_operation_identity_native.py:58). Only generic mention: schema/model_explanation.py:423 (git diff roots) and model_change.py:393 (file hashing).
  These five-six are orphaned production files, retirement-rule-4 candidates (not tests alone: unloaded, plausibly dead).
`function_bodies`: still exists, src/semantic/native_products.py:308. Production callers exist: native_products.py:288, native_authoring.py:826,
execution_admission.py:396, native_admission.py:445. So rule 4 does not apply; it STAYS. Test users: test_native_inventory.py:2,23 (direct unit),
test_native_release_guards.py:18,145 (target_alembic n7 admission.sql + `admission_kernel()`), test_native_closure.py:222,224,270-285,
test_native_sql_body.py:203-207.
Tests reading production .sql by path today (plan: 19 modules; now 10):
| Module:line | Target | State |
|---|---|---|
| test_native_sql_body.py:202-217 | closure.sql (exists), execution_projection_check.sql (DELETED) | still FileNotFoundError; file unchanged since baseline |
| test_native_closure.py:268-290 | `Path.read_text` patched for name `pdf_record_context.sql` (deleted 5341e93dd), then `function_bodies(publication_sql())` | NEW BREAKAGE: production no longer reads that file (publication_sql builds from `pdf_record_context_sql(metadata)`, pdf_publication_native.py:422,483), so the replacement never fires and `'changed_descriptor'` assertion fails by reading |
| test_data_operation_retirement_context_sql.py:21-36 | data_operation_task_checks.sql (exists) + 4 `source.index(...)` cuts of `target_task_guard_sql` output, per-case `semantic_bare_engine` | still text cuts (only remaining anchor cutter); changed by b1c10cbbf |
| test_data_operation_protocol_values.py:151 | task_checks.sql, via path | works |
| test_data_operation_cpu_basis.py:68-83 | closure.sql, identity.sql by path; `cpu_basis_connection` :62 on bare engine, 6 FK-less tables, then installs generated programs | unchanged; imported by 3 modules |
| test_data_operation_identity_native.py:56-58 | data_operation_identity.sql (no prod loader); native_read cases :24,:46 are the target class | unchanged |
| test_data_product_admission_programs.py:27; test_pdf_validation_read_native.py:64-66 | identity.sql path read (NEW files from conversion) | new path readers |
| test_target_installation.py:161 | source_record_recognition.sql | works |
| test_data_operation_constraint_custody.py:94-95 | admission.sql, source_record_graph.sql parse | works |
| test_native_release_guards.py:142 | target_alembic/versions/semantic_ddo_pe_n7_admission.sql (archived migration, not semantic/sql) | exists; fine |
No longer path readers (moved to generator imports by a727a9878/d422c48e7 etc.): trust_snapshot (`support_trust_native_sql`, anchors gone; the
plan's :53 anchor no longer exists), selected_graph (`dependency_selection_differs`), execution_guard (`execution_evidence_differs`),
replicate_policy (`demand_authority_sql`), data_operation_json (`data_operation_value_sql`), record_policy_native_predicate
(`record_policy_native_sql`), population_selection (`binding_source_recipe().codecs.decode()`), pdf_access_correspondence, pdf_record_native,
pdf_record_context, data_operation_storage.py:72 (captured sources `.endswith(".sql")`, not a read).
New helper: tests/semantic/native_program_support.py:7 `routine_declaration(source, schema, name, *, temporary=True)` (parses generated SQL, optionally
renames to pg_temp), used by trust_snapshot, replicate_policy, data_operation_json, identity_native. Good examples of the target "obtain from owner": the
three the plan names plus test_support_trust_native.py (`execute_native_sql(binding_native_connection, support_trust_native_sql(metadata))`, rollback family),
test_data_operation_compiler_native.py (14 `native_rollback`), test_data_operation_identity_native.py:24,46 (`native_read` on the installed function),
test_pdf_freeze_programs.py / test_pdf_publication_controls.py / test_pdf_validation_seal_programs.py (commit clones + `native_rollback`).
`semantic_bare_engine` (tests/native_fixture_support.py, creates a database per test; file unchanged): 61 files / 246 refs now vs 45 / 198 at
baseline (plan said 44 files). 16 NEW user files from conversion tests, contradicting the plan's "other new tests use commit and rollback":
test_data_operation_read_native, test_data_product_admission_programs, test_data_read_boundary_native, test_native_parameter_defaults,
test_native_program_table_outputs, test_native_refusal_detail, test_native_release_guards, test_operation_event_programs,
test_pdf_companion_adoption_programs, test_pdf_companion_read_native, test_pdf_record_event_queries, test_pdf_validation_read_native,
test_record_policy_native_access, test_selected_source_search, test_source_capture_native, test_support_trust_native. 107 direct requests
(88 by tests, 19 by fixtures). Bare-engine expression checks that now take generated programs but still use a database per case:
trust_snapshot (fixture `snapshot_connection` :17, installs `ddo_trust_snapshot_meaning` with `temporary=False`), selected_graph, execution_guard,
replicate_policy, retirement_context, record_policy_native_predicate, null_scope (:14,:32,:48, pure PostgreSQL expression, never touches a semantic object),
`metadata_codec` (test_source_metadata_codec_native.py:15-28, plan's example still true), cpu_basis_connection (three importers:
test_cpu_authority_reply_native, test_rich_admission_native, test_established_validity_native), product_connection, access_database, context_database, etc.
Related TDM-05 (not 16) pattern, none new: order-by-text assertions `body.index(a) < body.index(b)` on generated bodies in
test_data_claim_native.py:42-46, test_data_attempt_release_native.py:45-47, test_data_operation_renewal_native.py:37-39, test_projection_recipe.py:104,
test_data_read_boundary_native.py:259 (new file).
| Part | Delivered | Remaining |
|---|---|---|
| Subject from owner (no path read, no anchor cut) | PARTLY, by the conversion: 9 plan modules moved to generator imports; anchors resolved | 10 path readers above; retirement_context cuts; test_native_closure stale patch; test_native_sql_body deleted file |
| Class (no database per case for expression checks) | NOT; WORSE | per-case databases rose 45 -> 61 files; none moved to native_read/native_rollback/infrastructure_rollback (the only `infrastructure_rollback` users remain conftest, core/test_method, db/test_store, semantic/test_data_operation_wire, test_native_rowtype_evolution) |
| `function_bodies` deletion | N/A: production callers exist | none |
| Orphan production SQL files | new | exclusions/fact/selection/validation/source_record_graph/data_operation_identity .sql have no loader: decide by production owner/rule 4 |

## Q7. TDM-01 table and new finds
Fixture check method: AST scan of fixture definitions (decorators `pytest.fixture`, `name=`), test/fixture parameters minus `parametrize` argnames
and defaulted arguments, hypothesis `@given` names (a, b, c, blocks, data, ids, latex, literal, order, seed, tails, toks, value, values) filtered by
hand, scope check (same file, ancestor conftest, imported name, ancestor conftest import; re-binding `x = module.x` handled). Result: exactly two
undefined fixture requests at both commits; no `usefixtures` name undefined.
| Row | State at 12f57dc4d |
|---|---|
| test_source_routing.py:9-12 (`domain_default_case`) | STILL BROKEN (file unchanged; fixture defined nowhere) |
| test_native_sql_body.py:200-216 (deleted file) | STILL BROKEN (:205-207), unchanged |
| trust_snapshot_sql.py:53 / selected_graph_sql.py:34 anchors | FIXED by the conversion (rewritten to generators, d422c48e7, a727a9878); they now cost a database per case |
| test_witnessed_publication_native.py, test_condition_publication_native.py (factory without `with`) | STILL BROKEN (unchanged; `current_pdf_source_factory(...)` returns `_current_pdf_source(...)`, a `@contextmanager`, :54-56 / :29-31 use `.kernel` on it) |
| test_source_discovery_native.py (cases without views, `kernel.preparation.directory/"uncaptured.pdf"` :52) | UNCHANGED; not re-verified in depth |
| test_current_pdf_source_inputs.py:58-68 | STILL BROKEN (KeyError), TDM-09 |
| Seven converter copies | FIXED by reading (1d22c41cb, 8a5c074f0): now certified; the Preparation payload is not production-derived but non-blocking |
| Native identity vectors (TDM-04) | not re-examined by me; no conversion commit named it |
| tests/test_native_refusals.py (`db`) | STILL BROKEN: 4 tests request `db`; defined nowhere in package tests, root tests/, root scripts/, root conftest (the root tree IS now searched) |
New cannot-pass by reading: (1) tests/semantic/test_native_closure.py:268-290 (above). (2) fixtures `record_source_*` (tests/conftest.py:533-569) depend on undefined `private_source` but no test requests them (dormant). No other: 0 unresolved `corpus_structure` imports, 0 unresolved test-tree imports, 0 missing referenced paths. Not checkable by this
method: tests whose bodies call changed production signatures (needs a run).

## Q8. TDM-17
UNCHANGED. test_residency_hands_off_actual_gpu_capacity_and_restarts_real_host: tests/methods/test_native_host.py:716-752 (`pdf_gpu_slot` import :719,
`bounded` deadline :738-741, slot :744); src/ingest/pdf_capacity.py: `pdf_gpu_slot` :25-42, `_locked_gpu_slot` :~45-70, `Path("/tmp")` path built :51
inside the function, flock loop calls `check_active` before each attempt, borrower `external_execution_gpu` entered first. tests/ingest/test_pdf_capacity.py:
only the quarantine control (:106-127, mocks os.open/fstat/close/flock) plus 4 other tests; no order or waiting control. Real-slot users in tests: only
test_native_host.py:744 and the mocked-lock quarantine test (:120,:127). Other tests replace the slot (test_pdf_visual_requests.py:99,359,
test_pdf_recognition_slots.py:93, test_pdf_recognition.py:73,203).
| Delivered | Remaining |
|---|---|
| NOT AT ALL | all |

## Plan statements that are now false (or need rewording)
Coordinator (test-domain-model-and-execution_2026-11-17.md):
1. "Authoring baseline … Line citations … will have moved": correct, and for the PDF seams specifically ADR-0131's step 3 is DONE, not pending.
2. TDM-01 table row "Seven uncertified converter copies and their consumers | Production refuses their reply | TDM-09": false; they now emit certified replies.
3. TDM-01 row for trust_snapshot:53/selected_graph:34 anchors: gone (rewritten); drop the row.
4. TDM-00 "expects these to have moved: the seven uncertified converter copies and the fixture-only occurrence writer": both done (1d22c41cb, 8a5c074f0). The
   remaining readers of data_operations.sql: file deleted (2910d9817); step 4 kernels done.
5. Package queue TDM-09 Delivers "all copies and the fixture-only occurrence writer removed": writer removed, copies replaced; what remains is the
   producer-owned sequence, request-object `stream`, controlled-content-as-data, production-derived preparation report, the contract control.
6. "TDM-09 and the conversion" paragraph: the conversion has landed the writer's retirement; TDM-09 no longer deletes it.
7. TDM-14 "nine sites in the PDF integration module cannot set up before [TDM-09]": the seven-double dependency is gone; the integration module's sites
   now set up (by reading). The need that remains is the real-child integration control and scope of controlled helpers.
8. Handovers: "Superseded production machinery ... `function_bodies` in TDM-16 if no production caller remains": production callers remain (4); delete only the clause. Orphaned `.sql` files with no loader are a new handover item.
Controlled-boundaries companion:
9. Baseline "Seven doubles never adopted it … returns a five-field reply … no certification … every consumer fails during setup": false now.
10. "A writer exists only for those seven. `write_native_occurrence_batches` (:567) has no production caller": symbol deleted.
11. "One certified test helper exists … four defects … repeats the child's order by hand … imports `_atomic_bytes` and `_ref` (:201)": now one import (`_atomic_bytes`) and no manual reply assembly; it
    calls `certified_reply`. Its callers are `_controlled_stream`/`_section_stream` at :212, :388 (not :274/:463); preparation bytes `b'{"fixture":…}'` still hand-written, true.
12. "What the conversion had already corrected at the baseline: nothing in this finding. Two of nine sites used the certified helper": superseded; all nine do.
13. "The protocol is inline in the worker child … nine-field PdfStreamReply" (`pdf_worker.py:82-133`): reply assembly moved into `StreamingPdfResult.certified_reply`; the child now has 49 fewer lines; sequence otherwise inline (lines 95-105).
14. "Every double is replaced by a content value", complete-consumer scope list: the 7 doubles' sites are the callers of `certify_controlled_pdf_stream`; new copy `pdf_acceptance_support.py:34-71` must be added; `orchestrate/pdf_streaming.py:493` is :421.
    "Removed: nine stream doubles; `write_native_occurrence_batches`": the latter is already gone.
15. `Open question 1` mentions certification inputs; unaffected. Open question 5/6 unchanged.
16. TDM-10: "No file under src/…/orchestrate or tests/orchestrate changed since the review": true of the executor files; but orchestrate/pdf_streaming.py and test_pdf_private_execution.py did change (PDF only). Add test_data_operation_consumers.py:118-142 to the executor scope.
17. TDM-12: "`_complete_ready` … imported by two other modules": four importers. "nine importing files, sixteen import statements": 10 files / 17 statements by AST.
Declarations companion:
18. "Baseline at 50827eb9f … `The conversion changed none of this`" (lists): still true for conftests; `selected_graph_case` is at test_data_operation_storage.py:2464; explicit db marks 58/21.
19. "27 hand-written files remain … Nine were deleted": 16 remain.
20. "Nineteen test modules read production SQL by path": 10 do; of the "Two anchors absent" the tests were rewritten; "Eight of nineteen cut by anchor": one (retirement_context) cuts.
    "Three tests show the target (runtime_binding_sql, source_value_native_sql, execution_projection_check_sql)" now many more.
21. "44 files use `semantic_bare_engine` … Six bare-engine users were added by the conversion, while its other new tests use the commit and rollback classes": 61 files; 16 added by the conversion all use bare per-case databases (some also native_rollback).
22. TDM-16 "reader of the deleted file": test_native_sql_body still; also test_native_closure.py:271-285 (not in plan).
23. TDM-16 Superseded machinery: "`function_bodies` as a test-side way to select production text": the selection-by-file uses vanished except test_native_sql_body/test_native_closure/test_native_release_guards; production callers keep the function.
24. TDM-16 "trust-snapshot comparisons become calls of `ops.ddo_trust_snapshot_meaning` on `native_read` … the temporary copy under `pg_temp` and the three text cuts go": the text cuts are already gone (generator import); the per-case database and non-temp install (`temporary=False`) remain; `ops.ddo_trust_snapshot_meaning` is a generated program (support_trust_native.py:126), data_operation_read_native.py:634-635 calls it.
25. TDM-16 "`test_source_metadata_codec_native.py` … calls the installed `data.record_json_source`": still unconverted for class (true), ok.
26. TDM-15 "Four unimported support modules; no test requests any record_source_*": still true. TDM-15 counts (37 rows / 23 dead / 13 live; 38 / 11) still exact.
27. TDM-17: nothing false.
28. TDM-11: nothing false; add `NativeHost.__new__` (test_native_host.py:57) as private-state construction, optional.
