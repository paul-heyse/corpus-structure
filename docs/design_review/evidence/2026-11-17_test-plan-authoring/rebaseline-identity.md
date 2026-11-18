# REBASE_B: TDM-03/04/05/06/07/08/13/14 re-read at 12f57dc4d

Source: snapshot snap4 of 12f57dc4d. History: `git diff|log 50827eb9f..12f57dc4d` (104 commits).
Paths: `tests/...`, `src/...` relative to python/corpus-structure; "root ..." = repository root.
Nothing run; no database touched. The key's own `import_closure` was run statically (ast, no import of the package)
against the snapshot with a scratch script (plan2/closure_run.py).

Scanned exhaustively: every path cited in the four companions (existence check; only `data_operations.sql` is gone);
diff stats of every cited file between the two commits; target_alembic (all 29 revisions: pins, imports); all
`current_pdf_recipe` and `startswith("data-operations/")` sites; all `prepare_release(`/`compile_data_operations(`
files; AST count of test functions per PDF-source fixture; all 26 test files added since 50827eb9f (refusal shape).
Sampled: bodies of the DuckDB relational tests (read two in full, skimmed three), the new generated-program tests
(grep for refusal and substring shape only), converter-double internals, set-wise validity generator.

## 0. What changed in this range that matters to these packages (commit ids)

- Hand SQL removed: `semantic/sql/data_operations.sql` (2910d9817, d422c48e7), `data_operation_support_scopes.sql`,
  `data_operation_external.sql`, `data_operation_bindings.sql`, `pdf_observation.sql`, five `pdf_record_*.sql`.
  Sixteen hand .sql files remain in `src/corpus_structure/semantic/sql/`: admission, closure, contextual_neighborhood, data_operation_identity, data_operation_source_admission,
  data_operation_task_checks, data_operation_visual_read, exclusions, fact, identity, pdf_descriptor, selection,
  source_originals, source_record_graph, source_record_recognition, validation.
- target_alembic grew from 22 to 29 revisions: N7 68cb15217, N8 be969a6f2, N9 c00156f1a, N10 50708123c, N11 8384a80c9,
  N12 8d8cb9c05, N13 553d27a43 (each a frozen generator output).
- Controlled PDF converter doubles now certify through production: 1d22c41cb (adds `certify_controlled_pdf_stream`,
  tests/pdf_acceptance_support.py:34) and 8a5c074f0 (production `StreamingPdfResult.certified_reply`,
  src/ingest/pdf_streaming.py:573; fixture-only occurrence writer retired).
- `semantic_principals()` in-process: 781350991 (scripts/native_test_support.py:396-401).
- 26 new test files (generated-program controls), listed in plan2/newtests.txt.
- DuckDB conversion (ef6a7b13f, 048d5ab17, dbe22b899) landed BEFORE 50827eb9f, and the six DuckDB modules are
  unchanged since (no diff).
- Files NOT touched in the range (so every baseline line cite for them still holds): scripts/native_deployment_key.py,
  native_deployment_build.py, native_scenario_seeds.py, tests/semantic/data_operation_kernel_support.py,
  the five bundle-typing support modules, declared_record_grading_support.py, statistics_pack_support.py,
  tests/native_refusals.py, tests/conftest.py, root tests/scripts/test_native_deployment_key.py and
  test_native_scenario_seeds.py, src semantic/regeneration.py, composed.py, pdf_capture.py, data_operation_identity.py,
  data_operation_admission.py, selected_query_cache.py, demand_queries.py, change_impact.py, file_custody.py,
  orchestrate/execution_host.py.

## 1. Deployment key questions (answers)

| Question | Answer at 12f57dc4d |
|---|---|
| `PgAdmin.deployment_key` chain | Still `repository / "python/corpus-structure/semantic_alembic"` (root scripts/native_test_support.py:912; file shifted +, same code). Unchanged since 50827eb9f |
| `upgrade` chain | `ALEMBIC_DIR = parents[3] / "target_alembic"` (src/semantic/migrations.py:14, used :18-24). Unchanged. So the defect stands |
| target_alembic revisions | 29 (was 22), all `semantic_ddo_*`, linear, root `semantic_ddo_current_root`, head `semantic_ddo_pe_n13`. 32 .py/.mako files (29 revisions + versions/__init__.py + env.py + script.py.mako); 87 artifacts (29 x {_upgrade.txt, _native.json, _admission.sql}); about 342 MB on disk (357.8 MB git blobs; bodies alone 93.7 MB). semantic_alembic unchanged: 285 revision .py, 1.8 GB |
| Executed bodies import at module level | Yes, 29/29: line 6 of every `*_upgrade.txt` is `from corpus_structure.semantic import alembic_native, alembic_privileges` (module level; also module-level `import pgvector.sqlalchemy`, sqlalchemy). Bodies are 29 files; `alembic_privileges.owned_operation` appears in 7 of them only (186 uses), so the plan's "first statement uses owned_operation" is not general |
| Artifacts digest-pinned | Yes, all 87: every revision file has exactly three `*_SHA256 = ` constants (upgrade, native state, admission) and `_read(name, digest)` refuses mismatch. No unpinned artifact exists, so the key's `artifacts` component (path, size, mtime at root scripts/native_deployment_key.py:146-148) would be empty under the pinned-artifact rule |
| Key components now | Unchanged function (6 components + server): `chain` (digest of .py/.mako), `artifacts` (size+mtime), `module_imports`, `construction`, `lockfile`, `interpreter`, `server` (version, cluster, template oid, extensions, principals as (name, oid)). TypedDict at native_deployment_key.py:17-24 |
| Static closure, frozen tree (what the key hashes today) | 25 package modules, equals the earlier state.md figure. Includes schema/model.py, schema/relational.py, core/canonical.py |
| Static closure, target tree, bodies not walked (module-level) | 21 modules: `__init__`, core/{__init__,db/{__init__,extensions,lifetime,store},execution_policy}, semantic/{__init__,alembic_defaults,alembic_environment,alembic_indexes,alembic_native,identity,migrations,native_catalog,native_objects,prepared_sql,refusals,types,value_codec}, settings. No `schema/*`, no `metadata.py`, no `alembic_privileges` |
| Static closure, target tree plus bodies as sources | 22: adds only `semantic/alembic_privileges.py`. `alembic_native` is already reached through the revision's `native_objects` import, so the plan's "brings alembic_native and alembic_privileges in" overstates; only alembic_privileges is new |
| Construction closure | 15 files, unchanged (`construct_deployment` reaches migrations.py, core/db/*, identity, refusals, types, value_codec, settings). `host_bootstrap.py` is in neither closure |
| host_bootstrap.py | Exists since before baseline (358 lines); only diff in range is `--record` default (c3cfcb4c6). `PRINCIPALS` at :41, `peer_principals` :194, `main` :338 prints the principals. Consumed by `semantic_principals()` and both shell scripts (`render` in pg_provision.sh:17 and pg_semantic_roles.sh:6) |
| semantic_principals | NOW `from corpus_structure.core.db.host_bootstrap import PRINCIPALS; return {p.purpose: p.name ...}` (native_test_support.py:396-401, 781350991). No subprocess, no shell. Callers unchanged: key (:896), readiness (:929), tests/native_private_bootstrap.py:55, tests/db/test_native_host.py:14,26, tests/semantic/test_native_fixtures.py:140 via tests/conftest.py:325 |
| `--principals` script mode | Still present (scripts/pg_semantic_roles.sh:9-12) with no caller (`justfile:232` calls the script bare). Removable; the plan's "if TDM-00 confirms no caller" is now confirmed by git grep of justfile, ops, scripts at 12f57dc4d |
| Test provisioning | tests/native_private_bootstrap.py (241 lines, untouched in range) still creates roles, `cs_template` and extensions by hand-written SQL (:30-106). Not routed through host_bootstrap. ADR-0131 step 5 is therefore only half done: shell scripts use the builders, the private-host test path does not |
| Policy comparison | Unchanged. `replay_policy` ends with `actual = self.policy(name); if actual != policy: raise` (:645-648); `PgAdmin.database` then `if self.policy(name) != policy: raise` (:755-757). Duplicate remains |
| Root tests of the key | root tests/scripts/test_native_deployment_key.py (159 lines, 8 tests, unchanged). Real-tree case `test_real_chain_closure_contains_known_direct_machinery` (:137-159) passes `semantic_alembic` and asserts `metadata.py` and `relational.py` are in module_imports; neither is in the target-tree closure, so this test must change with TDM-06 (new fact). Other 7 cases use a temporary tree with a function-body import test (:88) |
| New test of principals | root tests/scripts/test_private_cohort.py:600-612 `test_private_principal_inventory_needs_no_shell_tool_path` (literal six-purpose mapping; independent expectation). It supplies the plan's "principals without a process" case |

## 2. TDM-06 (key, provisioning)

| Aspect | Status |
|---|---|
| Delivered (fully) | Principals without a subprocess (781350991) and a test of it (test_private_cohort.py:600). Spawn count per call: 0 (was 1 python process per call, 2 calls per key/readiness) |
| Delivered (not at all) | Chain still the frozen tree; no executed-body sources; artifacts by size+mtime; role facts still (name, oid); second policy comparison; `--principals` mode |
| Remaining, restated | (1) key chain from `migrations.ALEMBIC_DIR` (29 revisions); (2) bodies as sources (adds only alembic_privileges, 22-module closure); (3) function-level imports of chain files (revisions have `from ...alembic_privileges import admit_privileges` inside `upgrade()` at semantic_ddo_current_root.py:41; target modules already reached via bodies); (4) drop size+mtime: the artifact component is empty because all 87 are pinned; (5) widen role facts (still `SELECT rolname,oid FROM pg_roles`, native_test_support.py:~900); (6) delete the second `policy` comparison (:755-757); (7) delete `--principals`; (8) adjust root test :137-159 (expected module names) |
| Moved | Cites `native_test_support.py:917`, `:896-930`, `:901`, `:934`, `:397-405`: now :912, :891-925, :896, :929, :396-401. `:995-1057` `_publish_deployment` etc. shifted by about -5 after the removed import and function body |
| New cause since baseline | Revisions are now generated artifacts (N7-N13 are "model-owned"); the key correctly need not cover the generator modules because bodies are frozen and digest-pinned, but a stale-head risk exists only in the revision bytes. Reusable heads under the old key name unaffected. host_bootstrap.py is NOT in the key and must not be (plan item 5 agrees). The key also silently ignores `native_objects` helper functions imported lazily |
| Plan statement false | "The conversion added two target revisions"; "22 revisions, 24 Python files, 66 artifacts, about 250 MB"; "all 22 bodies"; "semantic_principals runs the role script on every call... worse than the review recorded"; "`pg_semantic_roles.sh --principals`... starts `uv run`... a second Python process" (the mode is dead code now) |

## 3. TDM-03 and TDM-07 (recipes, acquisition)

| Item | State at 12f57dc4d |
|---|---|
| `current_pdf_recipe` definitions | Two, unchanged: tests/semantic/current_pdf_source_support.py:46 `(directory, *, math_context=False)` and tests/semantic/current_pdf_integration_support.py:63 `(directory, *, integration_policy=None)` |
| Call sites | 23 call lines in 19 files, exactly as the plan: declared_record_native_support, characterization_native_support, current_artifact_support, current_contextual_support (2), current_pdf_integration_support (2), current_pdf_source_support (1), current_pm2_native_support, pdf_staging_support, rich_domain_native_support, structural_admission_native_support, structural_production_native_support, test_current_pdf_source_inputs, test_pdf_materialization_native, test_pdf_resource_custody, test_pdf_transform_demand_native, test_pdf_transform_operations (3), test_selected_native_scoring_native, test_source_profiles, test_source_project_native |
| tmp_path embedded | Yes. Both composers pass `PreparedPdfAssets(directory, b"{}", ())` and `directory=directory / "owned"` into `pdf_capture_operation_sources`; the integration one also writes `directory/"explicit-provider.py"` (integration_support.py:86-89 region) and `directory/"receipts"` |
| Production custody binds paths | Yes, unchanged: src/semantic/pdf_capture.py:62-104 `pdf_capture_custody` writes `assets.root.resolve()` and `Path(directory).resolve()` (both inside the canonical bytes of artifact `pdf-capture/execution-custody`) and reads workspace back from it |
| `_prepared_kernel = cache(...)` | tests/semantic/data_operation_kernel_support.py:161, unbounded, `prepare_kernel` :164-167; `build_kernel` :288 bypasses it. All unchanged |
| Statistics pack typed by hand | The five support modules are unchanged and still type it: record_contracts_support.py:48-66 (importers 23), evaluation_record_alignment_support.py:45-63 (7), methods/record_assembly_support.py:23-49 (15), methods/m1_producer_support.py:32-54 (5, `@cache def bundle()`), evaluate/declared_record_grading_support.py:34-48 (6). Importer counts match the plan exactly. Also typed: tests/semantic/test_declared_record_sources.py:201-205, test_m1_declared_products.py, test_statistics_model.py:20-24, rich_domain_preservation_support.py:52, orchestrate/test_m1_declared_native.py; toy: current_pdf_integration_support.py:118, test_native_definition_demand.py:63, test_native_parser_demand.py, orchestrate/test_source_demand_native.py. One more file reads pack files into a bundle: tests/semantic/test_data_operation_compilation.py:717-719 (compilation is its subject; probably legitimate). Grep for `statistics_semantic|toy_semantic` finds 19 files (some only match names) |
| Production acquisition users in tests | tests/statistics_pack_support.py:10-25 (session fixtures; 1 importer file), tests/semantic/test_trace_reference_fixture.py:34 (`prepare_pack`), test_alias_policy, test_terminology, test_schema_product_cli, test_cli_schema_diagnostic_boundaries (composition subject). Production `acquire_pack` regeneration.py:60, `acquire_packs` :297, `prepare_packs` :348 unchanged |
| Grading model/release pairing | Unchanged: declared_record_grading_support.py `current()` (:34-57) calls `prepare_release(bundle)` and `compile_data_operations(bundle, declarations=(reading_resolution_declarations(),), ...)`; `cut()` writes `prepared.release_id`. Six importers. Files containing both `prepare_release(` and `compile_data_operations(`: 39 (unchanged). `prepare_release(` files 132 (plan: 131), 266 call sites (same) |
| Recipe-extension sequences | 15 sites in 13 files, unchanged: `not ... .startswith("data-operations/")` at declared_record_native_support:166, declared_rich_native_support:55, test_actual_e5_selected_context_native:128, rich_domain_external_support:56, current_contextual_support:143,202, characterization_native_support:71, operation_event_native_support:46, rich_domain_native_support:59, structural_production_native_support:58, current_pm2_native_support:49,176, structural_admission_native_support:62, test_selected_native_scoring_native:70, current_artifact_support:55. No new production function reopens packaged inputs (composed.py untouched; `read_data_operation_inputs` composed.py:82 still the only reader; 27 call lines in 23 test files) |
| `admit_kernel` vs production | `admit_kernel` data_operation_kernel_support.py:228-252 unchanged (persist_release, admit_data_operation_release, persist_runtime_binding). Production still has no single admission op; the same three-step sequence appears in src/schema/model_deployment.py:994-1010 and releases.py:585-598 (conversion made no change). Other test sites doing the sequence: tests/orchestrate/test_data_operation_cross_release_native.py:96-100 (all three), tests/semantic/test_original_document_custody_native.py:34-37 and test_record_archive_guards_native.py:106-109 (persist+admit), test_execution_release.py, and NEW test_original_descriptor_registration.py:111-112 (persist+admit; added by the conversion) |
| Seed/registry | scripts/native_scenario_seeds.py unchanged (recipe_id :56, registry keying :200-209, files-inside-seed :237-245, freeze :168-175,268) |

TDM-03 delivered: nothing. Remaining: everything, with counts above unchanged; add test_original_descriptor_registration.py to the admission-order scope and
test_data_operation_compilation.py:717 to the typed-pack look-over. TDM-07 delivered: nothing; the line cites for TDM-07 moved only because
current_pdf_source_support.py shrank 19 lines (8a5c074f0): `_current_pdf_source` 270-357 (plan 293-380), `commit_clone` :303 (plan :325-326),
fixtures :361 `current_pdf_source` and :367 `current_pdf_source_factory` (plan 293-410), `admit_current_target` :458 (plan :481-492),
`current_integration_journey` current_pdf_integration_support.py:229 (plan :198), OriginalSeedRecipe sites
test_pdf_materialization_native.py:80 (plan :83), test_pdf_transform_demand_native.py:175 (plan :178), integration_support :247.
New cause: the controlled converter doubles now certify through `certify_controlled_pdf_stream`/`certified_reply`, which is
independent of the recipe split but means the capture still runs full production certification per consumer (cost, not a
correctness change).

## 4. TDM-08 (completed-capture seed)

| Item | State |
|---|---|
| `_current_pdf_source` | Still performs project init, registers one original, freezes and registers a discovery demand, deletes the file (:347), executes `execute_data_demand` and asserts `receipt_count == 2` (:348-356) per consumer, in a `commit_clone(recipe)` of a per-`tmp_path` recipe (:303). No seed stage for the capture |
| Consumers (AST count) | `current_pdf_source`: 12 test functions in 7 modules (test_current_source_graph_native 1, test_source_discovery_native 1, test_source_search 5, test_companion_export_native 2, test_native_render_journey 1, test_pdf_observation_catalog 1, test_native_exports 1). Equals pdf-source-consumers.md. `current_pdf_source_factory`: 16 test functions in 14 modules, plus helper journeys. `table_source` (a context-manager helper, not a fixture): 4 functions in 2 modules (test_pm2_parser_stage_native, test_pm2_result_native). `structural_native_journey` 2, `operation_event_journey` 3, `primary_source_case` 2, `current_workflow_case` 3, `actual_e5_native_case` 1, `current_contextual_case` 8. `rich_publication`: 13 functions in 4 modules, not 14 (same at both commits: 2+1+2+8) |
| Seed registry | Unchanged |
| TDM-01 defects | All three still present: test_witnessed_publication_native.py:31 and test_condition_publication_native.py:56 call `current_pdf_source_factory(...)` without `with`; test_source_discovery_native.py:52 writes `kernel.preparation.directory / "uncaptured.pdf"` into the frozen seed directory |
| Controlled converter (TDM-09 prerequisite) | Partly changed: doubles still local callables patched with `monkeypatch.setattr(PdfWorker, "stream", ...)` at current_pdf_source_support.py:292, current_artifact_support.py:215, current_pdf_integration_support.py:426, declared_record_native_support.py:354, test_pdf_materialization_native.py:79, test_pdf_transform_demand_native.py:170 (plus rich_domain_native_support, test_nce02_native_scope). All now return `certify_controlled_pdf_stream(...)` or `result.certified_reply(...)`. `write_native_occurrence_batches` has no remaining caller in tests or src. What TDM-08 needs (data-described content, installable outside a test) does not exist; `_section_stream(rows, ...)` is still a closure |

Delivered: nothing of the seed stage. Remaining: unchanged (23 consumer functions to classify). New: the certified converter makes the seed
stage more valuable (each consumer capture now runs the real certification path).

## 5. TDM-04 (identity vectors)

| Item | State |
|---|---|
| Vector module | tests/semantic/data_operation_identity_vectors.py unchanged: `ContextualProductVector(name, project, source, scope, literal)` (5 fields), `_PRODUCT` literal contains `["subject_definition",["string","document"]]`, five cases |
| Native consumer | tests/semantic/test_data_operation_identity_native.py:23-41: commit d422c48e7 added `"subject_definition": "document"` to the hand-built mapping (:32). The plan's "by reading, not run, its five cases cannot pass" is now false; the premise of "no input literal in the consumer" is still unmet (constant, not a vector field). The scope still goes through `json.loads` then `json.dumps(value)` (:23-41), so `equal-json-number` (`b'{"page":1.2500}'`) sends `1.25` |
| Python consumer | test_data_operation_identity.py:35-63 passes `subject_definition="document"` itself (:38, :48); completeness test :407-430 still does not vary subject_definition (test file untouched) |
| Native helper reads | Third test still installs `sql/data_operation_identity.sql` by path (:57-59); the file still exists. The fourth test now installs `data.ddo_json_meaning` through the generated `data_operation_value_sql()` + `semantic/native_program_support.routine_declaration` (NEW helper: pglast `parse_sql`, rename into pg_temp), replacing the former text slice of data_operations.sql |
| Request identity, Python | `SemanticRequestKey` src/semantic/data_operation_identity.py:502-530, unchanged; no literal vector in tests. Canonical tag `"semantic-request"` (:520) |
| Request identity, native | `data_operations.sql:1027` is gone. Installed `data.ddo_identity` is generated: src/semantic/data_operation_value_native.py (routine at ~:447). Users: request_attachment_native.py:1526 (`Assign("key", func.data.ddo_identity("semantic-request", meaning))`) and binding_admission_native.py:213. A native test can call the installed function by name as the plan intends |
| Python-vs-native storage comparison | tests/semantic/test_data_operation_storage.py:2272-2299 (was :2289-2294) still compares the deployed product key with `contextual_product_identity(...)` using `subject_definition="original-occurrence"`; same circular shape as the plan describes |
| Consumers of CONTEXTUAL_PRODUCTS | Still only the two test modules |

Delivered: none of the target (a one-line patch made the native cases passable). Remaining: record field set, JSON text with the authored
scope bytes, new subject_definition and local-subject cases, the request-identity vector, completeness variation, drop the constants in both consumers.

## 6. TDM-05 (generated-program tests assert meaning)

| Site | State at 12f57dc4d |
|---|---|
| Four renderer-spelling literals | tests/semantic/test_pdf_source_search_projection.py:36 (`CAST('english' AS REGCONFIG)`), :40 (`USING gin (search_vector)`), :124 (`CAST('simple' AS REGCONFIG)`); test_companion_export.py:398 (`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ WRITE` now matched as a whole statement in `events`); tests/schema/test_pdf_shared_stream_data_steps.py:55 (`LOCK ops.pdf_artifact_part`); test_target_installation.py:276 (`kind = 'execution_model'`, with message :277). All files unchanged except test_target_installation.py (hunk is near :279-296, below the cited line) |
| `RETIRED_PARTS` equality | test_pdf_shared_stream_data_steps.py:98 (and :59-60); `RETIRED_PARTS` = src/schema/data_step_programs.py:52, still `("ops.pdf_artifact_part", "ops.pdf_stage_artifact_part")`. Unchanged |
| New spelling assertions added by the conversion | test_target_installation.py:279-295 now asserts `"float8send(CAST(kb.pdf_record_access.ordinal AS DOUBLE PRECISION))" in str(equality)` (rewrote the old `float8send("ordinal"::double precision)`); test_native_program_table_outputs.py:35 `'"position" bigint' in program`; sentinel absence `"__DDO_READ_BOUNDARY_PROGRAMS__" not in sql` (test_data_read_boundary_native.py:258), `"__DDO_SOURCE_CAPTURE_PROGRAMS__" not in sql` (test_source_capture_native.py:330). The first two are renderer-spelling in the F07 sense and belong in the site table |
| pglast capability | More use than the plan cites: native_program_support.py (parse_sql, CreateFunctionStmt, RawStream), test_host_bootstrap.py, test_pdf_validation_read_native.py. test_target_installation.py's pglast sites are still at :202-238 and :99-119 |
| Lowering-identity test | tests/semantic/test_pdf_producer_certification.py:135-146 (equality at :138 `require_lowering_identity(context) == sha256(artifact.content).hexdigest()`), `require_lowering_identity` src/semantic/pdf_lowering.py:~285-310 (refusals "PDF lowering contract differs from the captured execution basis", captured-source mismatch). Still circular, no refusal tests added |
| `LOWERING_FILES` | Still a hand-kept tuple, now ~70 entries (was ~58): 17 generator modules added (pdf_publication_read_native, pdf_companion_read_native, pdf_validation_read_native, pdf_record_context_native, pdf_record_event_queries, pdf_selected_source_native, pdf_record_pages_native, pdf_record_proof_native, pdf_record_digest_native, pdf_identity_frames_native, pdf_record_access_native, pdf_binary_identity_native, pdf_completion_native, pdf_target_identity_native, pdf_companion_adoption_native, pdf_integrated_native, pdf_observation_native) and five `semantic/sql/pdf_record_*.sql` removed. Nothing derives it and no test checks it (no reference in tests/); `_implementation_sources` pdf_lowering.py:~259-272 reads it. The coordinator's handover row stands, and the list grew with the conversion |
| Scalar validity vs set evaluator | `data_operations.sql:391-434` gone. Now generated in src/semantic/data_validity_native.py: closure routine `ddo_valid_closure` (program at ~:575-625, parameters seed_uses, seed_episodes, boundary, seed_populations) and `ddo_node_valid` built at :624-650 as `coalesce((select valid from ddo_valid_closure(...) where kind=... and id=...), false)`. Delegation still true. The closure test is tests/semantic/test_data_operation_storage.py:2818-2846 (duplicate seeds and a deliberate cycle); none of the plan's reference graphs (shared descendants, mixed seeds, two-node cycle, supersession) exist. Other tests that stub `ops.ddo_node_valid` with a trivial function: test_record_policy_native_predicate.py:108, test_pdf_validation_read_native.py:103, test_source_capture_native.py:53 (fixture stubs, not reference cases) |
| Search selection digest | tests/semantic/test_source_search.py:141-185, :222-227 unchanged; `selection` still recomputed with `sha256` at :178 over production projection output; no pure production function found in src/semantic/pdf_source_search.py |

### DuckDB relational modules (the plan said they "did not exist in this form at 50827eb9f": false)

They exist at 50827eb9f (ef6a7b13f, 048d5ab17, dbe22b899 are ancestors) and no file changed in the range. Modules:
src/semantic/rich_relations.py + analytical_kernels.py (rich evaluator), src/serve/companion_export.py (companion export),
src/ingest/pdf_stream_reconciliation.py + pdf_candidate_geometry.py (PDF derived analysis), src/semantic/artifact_identity.py.

| Test | Expected rows |
|---|---|
| tests/semantic/test_rich_relations.py (201 lines, 4 tests) | Hand-authored small Arrow tables (nulls kept distinct, duplicates, empty inputs, ordering of `supports`/`evidence`) with literal expected rows; docstring says independent. Conforms. Not exhaustive on ordering-of-input |
| tests/semantic/test_rich_rule_evaluation.py (945 lines) | Evaluates real policies over authored source values; asserts literal statuses (accepted/rejected/candidate/ambiguous, rule names, severities). A few expectations are derived from the result itself (`selected_occurrence_ids == {decision.occurrence_id}`, `min(result.selected_fact_ids)`). Sampled lines 148-330 only: mostly authored, mixed |
| tests/semantic/test_companion_export.py (inventory, compare, multiset difference, incomparable projection) | Hand-authored two-row inputs with literal expected distributions, endpoint tuples, removed-row counts (`len(removed) == 1`); conforms for small cases, no null/empty-input case |
| tests/semantic/test_pdf_stream_reconciliation.py | Journal/IPC byte-preservation tests with literal tuples; not relational expected rows from a relation |
| tests/ingest/test_pdf_candidate_source.py:143 and root tests/test_pdf_candidate_geometry.py (:81, :125, :167, :189, :247) | Hand-authored boxes and literal `(candidate_index, item_ref, match_count)` lists; `:125` compares the DuckDB range join with an independent in-test center oracle over a 6x6 point grid (computed by a different, simpler method: conforms) |
| tests/semantic/test_artifact_identity.py and others | not read |

Result: no module was found whose expected rows come from running the relation or are copied from its output; the plan's relational item
reduces to "record as conforming" plus optional discriminating cases (null/empty/order for companion export). Not every file read.

## 7. TDM-13 (ten mechanisms)

| # | Mechanism, where it lives now | Observable now | Existing independent tests since baseline |
|---|---|---|---|
| 1 | Oracle skip: generator src/semantic/pdf_certification_native.py program `read_pdf_certification_requirement` (select at :363-403, `Assign("basis_", "producer-certified")` :461, call :490); installed as `ops.read_pdf_certification_requirement`; Python decision src/semantic/pdf_publication.py `validate_pdf_build` (:782-824, `force_oracle or requirement.oracle_receipt_id is None`). Lines :363-386/:456-462 still hold for the generator; pdf_publication lines moved (companion function removed, -71 lines) | return of the program, rows of `ops.pdf_roundtrip_oracle`, published basis | None supplies the table. tests/semantic/test_pdf_certification_programs.py:56-76 pins SQLSTATE (P0002 for the requirement on an unknown build) with no positive control and no message. test_pdf_validation_read_native.py:200 checks "no passed round-trip oracle" in the frozen check dispatch against a stubbed `control_oracle` table (a different decision) |
| 2 | Kernel-sealed completion: generator src/semantic/data_completion_settlement_native.py:622-690 (`routine("ops","ddo_require_episode_correspondence",...)`, kernel branch `If(row("receipt", receipt, "validating_kernel_digest").is_distinct_from(_KERNEL), ...)` at :661, message "historical intent payload digest differs" :667); `data_derivation_native.py:614` writes `validating_kernel_digest`; callers contextual_admission_native:226, rich_admission_native:483, artifact_admission_native:58, definition_admission_native:129, record_policy_completion_native:595, operation_event_native:409, record_grade_native:709 | SQLSTATE 23514 or absence; reading `validating_kernel_digest` of the receipt | None. Equal path only: test_data_operation_storage.py:2872-2894 (renamed `test_native_completion_receipt_records_actual_validator_not_release_expectation`, asserts receipt digest equals the seal digest, an independent read). test_data_completion_settlement_programs.py only runs plpgsql_check on the routine signatures |
| 3 | Lowered release facts: `sem.ddo_lower_data_operation_definitions` src/semantic/data_operation_compiler_native.py:1040-1110 (re-lowering update at :1070-1080, refusal "release facts changed under admitted release" :1099); readers: data_operation_read_native.py:207-213 ("read-only inspection native source correspondence differs", 23514), demand_registration_native.py:602, demand_authority_native.py:137 | `lowering_digest` column; reader refusals | Partial, NEW tests/semantic/test_data_operation_compiler_native.py (A, 493 lines): `:181` admit twice returns the same literal dict and `lowering_digest == digest` (digest = sha256 of the program the test itself installs and injects, so an independent expectation of the install, not of a stale-column refusal); `:367` relower requires finalization, retains immutable facts, and after the data-step control the column equals the digest; `:218` five mutations refused with literal messages and zero partial facts. Missing: stale column refuses read/demand, re-admission re-lowers a stale column, new-release admission does not repair it. Neither message "read-only inspection native source correspondence differs" nor "release facts changed under admitted release" appears in any test |
| 4 | Validity closure: src/semantic/data_validity_native.py (`ddo_valid_closure` ~:575-625, `ddo_node_valid` :624-650) | rows of closure | Unchanged: one duplicate-seed/cycle test (test_data_operation_storage.py:2818-2846) |
| 5 | Selected-query cache: unchanged src/semantic/selected_query_cache.py:60-86; demand key demand_queries.py:196-212; five serve modules unchanged | counting spy only | None added. Support autouse fixture tests/semantic/selected_query_cache_support.py:13-17 (`clear_selected_query_cache`, before and after); importers: test_rich_query_delivery, test_current_candidate_facets, test_current_composite_delivery, test_demand_results, test_grouped_record_interpretations, test_selected_structural_readers (6 modules, unchanged); `control_frontier` :26-40 in the same module. tests/conftest.py unchanged (Hypothesis ci profile still :95-99) |
| 6 | Change scope: src/semantic/change_impact.py:157-200 unchanged; tests/semantic/test_change_impact.py unchanged | roots/affected sets | None added |
| 7 | File custody racy window: src/semantic/file_custody.py unchanged; test_file_custody.py:16-21 unchanged | `racily_clean` | None added |
| 8 | Execution-basis cache: src/orchestrate/execution_host.py:74-82,198 unchanged; test_execution_host.py:68 (`test_verified_basis_reuses_only_exact_engine_header_runtime_and_root`) unchanged | object identity, spy | None added |
| 9 | Native host profile: src/methods/native_host.py `_validate_startup` :197-206 (still inline comparisons; unchanged) | startup observation | None; TDM-11 scope unchanged |
| 10 | Deployment key + seed origin: root scripts/native_deployment_key.py unchanged; root tests/scripts/test_native_deployment_key.py unchanged; tests/test_scenario_recipes.py unchanged | digest/components | Only new: test_private_cohort.py:600 (principals). Key table still waits for TDM-06 |

Other TDM-13 facts: the plan's "data_operations.sql" line cites for mechanisms 2, 3, 4 (:1273-1299, :1291, :18, :633, :2233-2246, :391-434) are dead; the
replacements are above. Mechanism 3 is the only one where the conversion supplied part of the table (re-admission replay, immutable facts, digest after
re-lowering). The new conversion tests do not use the oracle/perturbation form for any of the ten.

## 8. TDM-14 (refusal sites)

| Plan site | Now | Pins SQLSTATE and message after a positive control? |
|---|---|---|
| test_established_validity_native.py:224 | same line, bare `DBAPIError` in a six-way loop | No |
| test_data_operation_context_fanin_native.py:158 | same, bare `DBAPIError` | No |
| test_data_operation_binding_native.py:714 | now :713 (`match="checked project"`) and :726 bare; file gained 142 lines (new tests) | :713 partly (message, no SQLSTATE); :726 No. Also :848-850 and :954-958 pin SQLSTATE only |
| test_data_operation_external_native.py:169 | same, bare | No |
| test_data_operation_authored.py:212 | same, bare (:203 and :359 carry messages) | No |
| test_data_operation_population_selection.py:168 | now :164, bare | No |
| test_current_pdf_integration_native.py:119,136,165,298 | same lines, bare `DBAPIError`; :266 (42501) and :362 (23514) pin SQLSTATE only | No. File's setup premise (converter copies) is moot, see below |
| test_record_publication_native.py:156,167,192,203,304,363 | file untouched; :156 is `InvalidContinuation`, :203 `RichQueryRefused` (not ValueError, never was); :167,192,304,363 bare `ValueError` | No |
| test_definition_model_native.py:156,163 | same, bare `ValueError` (:211 has a message match) | No |
| test_execution_admission_expectations.py:103,122,135 | same lines, bare `ExecutionAdmissionError` | No |
| test_pdf_shared_streams.py:155-157, 231-233 | same: `sqlstate == "23514"` alone (also :178 55P03, :187 P0004) | SQLSTATE only |
| tests/test_source_cli.py:231, 274, 367 | same, `exit_code != 0` only | No |
| Conversion tests listed (test_closure_native.py four sites e.g. :80-97, test_data_claim_native, test_data_claim_batch_native, test_data_attempt_release_native, test_pdf_stage_lifecycle, test_pdf_certification_programs.py:56-76) | All still present. Shape unchanged: inline `getattr(...orig, "sqlstate", None)`; closure sites additionally assert a message substring on `str(...)` at :87 and :93-95; claim/release tests combine `match=` with SQLSTATE; certification_programs has no positive control and no message | Mixed |

Helper tests/native_refusals.py (13-49) and test_native_refusals.py unchanged. Users of `native_refusal`: 8 consumer files
(data_operation_binding_support, test_data_operation_storage, test_native_closure, test_native_refusal_detail, test_pdf_spool_native,
test_pdf_stage_context, test_pdf_staging, test_db_fixtures); none of the 26 newly added files uses it.
New since baseline: 25 added test files with 40+ `pytest.raises(DBAPIError...)` sites; message-only: test_data_operation_compiler_native (6 raises, 10 match),
test_pdf_companion_read_native, test_record_policy_native_access, test_support_trust_native (all `match=`, no SQLSTATE);
SQLSTATE-only: test_pdf_access_correspondence_programs (2), test_data_completion_settlement_programs (1, P0001),
test_native_refusal_detail (1, but the same test also asserts `message_primary` and `message_detail` exactly: conforms);
mixed: test_data_read_boundary_native (6 raises, 5 sqlstate, 1 message), test_data_product_admission_programs (4/4/3),
test_pdf_validation_read_native (6/1/7), test_native_release_guards, test_pdf_companion_adoption_programs, test_operation_event_programs,
test_pdf_freeze_programs, test_pdf_inventory_programs, test_pdf_publication_controls (each about 2 raises with SQLSTATE and one message).
Candidate scope addition: the SQLSTATE-only new tests above.

TDM-14 order premise: "test_current_pdf_integration_native.py cannot set up before TDM-09 (stale converter copies)" is no longer supported: the integration
journey's converter (current_pdf_integration_support.py:260-294) now returns `certify_controlled_pdf_stream(...)`; the copy still exists but is certified.
Whether it sets up was not run. The nine integration-module sites can be converted without waiting for TDM-09 if its setup holds.

## 9. Plan statements that are now false (or need restating)

1. preparation-identity: "It added two target revisions" and "22 revisions rooted at `semantic_ddo_current_root`, 24 Python files, 66 artifacts, about 250 MB": now 29 revisions, 32 py/mako, 87 artifacts, about 342 MB.
2. preparation-identity (baseline, role scripts): `semantic_principals()` runs `pg_semantic_roles.sh --principals` and starts a second Python process; "worse than the review recorded". False since 781350991 (in-process `PRINCIPALS`). The `--principals` mode now has no caller at all.
3. preparation-identity item 2: bodies bring in "`alembic_native` and `alembic_privileges`": only `alembic_privileges` is new (22-module closure vs 21); `alembic_native` is already reached via `native_objects`.
4. preparation-identity: "the module-level imports first walk... 25 package modules over the frozen tree": true for the frozen tree, but the target tree closure is 21 (22 with bodies); the plan should state those numbers, not defer them.
5. preparation-identity: "`tests/native_private_bootstrap.py:30-106`... likely to call the shared builders by the time this series runs": it does not; it is unchanged hand SQL.
6. preparation-identity and coordinator: seven "uncertified converter copies" / "stopped producing what production requires" and the fixture-only occurrence writer: now certified through production and the writer has no callers (1d22c41cb, 8a5c074f0). Eight local `controlled_stream`-style doubles remain, so TDM-09's unification and data-described content (TDM-08's prerequisite) are still open, but "uncertified" and "by reading cannot set up because of DTA-041" are not current.
7. model-binding TDM-04: "by reading, not run, its five parametrized cases cannot pass" (native consumer lacked `subject_definition`): false since d422c48e7. The vector-record gap, constants in both consumers and the `1.2500` loss remain.
8. model-binding TDM-04 and TDM-13: `data.ddo_identity('semantic-request', …)` at `data_operations.sql:1027` and every `data_operations.sql:NNN` cite (:391-434, :426-434, :1273-1299, :1291, :18, :633, :2233-2246): the file is deleted; replacements are generator modules named in sections 5-7.
9. model-binding TDM-05: "the converted relational modules ... did not exist in this form at 50827eb9f; none is cited here": they existed (conversion commits precede 50827eb9f) and are unchanged; the modules and their tests are listed in section 6, and none was found to compute expected rows from the relation.
10. model-binding baseline: "none of the files below changed between the review's commit and the authoring baseline" is moot, but now in the range `test_target_installation.py` changed (float8send spelling assertion rewritten, new spelling literal); `LOWERING_FILES` is ~70 entries and no longer includes the five `.sql` files.
11. model-binding TDM-03 acceptance text "At the baseline this read refuses with 'release lacks an unambiguous target operation model' (data_operation_admission.py:41-48)": that source is unchanged, claim still holds by reading; no change.
12. preparation-identity TDM-08/TDM-07: line cites to `current_pdf_source_support.py:293-380/:325-326/:293-410/:481-492` and `current_pdf_integration_support.py:198`: shifted to :270-357, :303, :361-383, :458 and :229.
13. preparation-identity: "`rich_publication` fixture has 14 consuming functions": 13 at both commits.
14. reuse-and-refusal: "`tests/native_refusals.py`... nine files use it at the baseline": 8 consumer files now (plus the helper and its own test); none of the new files uses it.
15. reuse-and-refusal TDM-14: `test_record_publication_native.py:156, 203` listed as "bare `ValueError`": they are `InvalidContinuation` and `RichQueryRefused`; the "fourteen cases in two tests" count was not re-derived; the nine integration-module sites "cannot set up before TDM-09" is no longer supported (see 6).
16. reuse-and-refusal "If the conversion added a safety case of its own": it added the mechanism-3 partial cases (test_data_operation_compiler_native.py:181, :218, :367), no oracle-skip, kernel-seal or cache cases.
17. reuse-and-refusal TDM-13 mechanism 1 cites `pdf_publication.py:851-901` and `:1113-1156`: moved (decision now :782-824); generator cites `pdf_certification_native.py:363-386, 456-462` still hold.
18. TDM-06 acceptance: root test `test_real_chain_closure_contains_known_direct_machinery` expects `metadata.py` and `relational.py` in `module_imports` over `semantic_alembic`; after the chain fix neither is in the closure and the test's expected set changes (the plan says only that its real-tree case passes the frozen tree at :141).
19. coordinator "Foundations": "the seed registry can express a second stage" and "controlled converter named by recipe data": the registry is unchanged and still true; the converter is not yet data-described.

## 10. Packages: delivered / remaining / moved / new (compact)

| Package | Delivered by conversion | Remaining | Moved | New cause |
|---|---|---|---|---|
| TDM-03 | none | all (typed packs 5 support + about 11 test files; grading pairing; 15 extension sites; 23 recipe call lines; admission-order consolidation) | none, all cites hold | new admission-order sites: test_original_descriptor_registration.py:111-112; test_data_operation_compilation.py:717 pack read |
| TDM-04 | native cases made passable (d422c48e7) | record fields, native JSON text, new cases, request vector, drop constants | data_operations.sql:1027 -> request_attachment_native.py:1526, binding_admission_native.py:213 | `routine_declaration` helper (pglast) available for native vector installs |
| TDM-05 | none of the seven sites | all seven rows, lowering refusals, closure reference graphs, search digest | validity -> data_validity_native.py; closure test :2818 | two new spelling asserts (test_target_installation.py:294, test_native_program_table_outputs.py:35); LOWERING_FILES grew to ~70; DuckDB tests already conform |
| TDM-06 | in-process principals + its test | chain, bodies, content-only artifacts, role facts, second policy compare, drop `--principals`, root test edit | native_test_support lines | 29 revisions; generated frozen bodies; private bootstrap still hand SQL |
| TDM-07 | none | whole package | support-file line shifts | none |
| TDM-08 | converter now certified (not data-described) | whole package; 3 TDM-01 defects still present | support-file line shifts | certified capture makes each per-consumer capture costlier |
| TDM-13 | mechanism 3 partial tests | tables 1, 2, 3 (rest), 5-8, 10; mechanism 4 reference cases (TDM-05); cache-scope fixture | data_operations.sql cites to generator modules | no change to caches, custody, host, key |
| TDM-14 | none | same sites plus new SQLSTATE-only tests | line shifts (binding_native :714->:713; population_selection :168->:164) | 26 new test files with inline-SQLSTATE refusals; native_refusal unused in them |
