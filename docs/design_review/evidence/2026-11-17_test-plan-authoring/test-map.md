# MAP_TEST — test-code facts at commit 1afa63f88 (snapshot snap2)

Conventions. Paths are relative to snap2/python/corpus-structure unless prefixed "root" (snap2-level:
root conftest.py, root scripts/). "Modules" = files; "test modules" = test_*.py.
Corpus size: 842 .py under tests/ (701 test_*.py). snap2 omits the repository-root tests/ tree
(34 files: tests/conftest.py, tests/scripts/*, tests/test_native_*.py, tests/test_pdf_*.py); I listed it
with `git ls-tree 1afa63f88` and read single files with `git show` where noted. Nothing was run.

Method key. "Exhaustive" = whole-tree AST or grep over tests/ + root scripts/ + root conftest.py.
"Sampled" = I opened the file(s) named. Fixture definitions come from an AST scan of every
`@...fixture` decorator in tests/, root scripts/ and root conftest.py (228 definitions: 136 function,
93 module, 25 session scope). Fixture-request counts come from AST of function arguments plus
`usefixtures`; indirect parametrization and `request.getfixturevalue` are NOT counted (noted where it matters).

---------------------------------------------------------------------------------------------------
## M1 — Prepared-state inventory

### M1.1 Native deployment head (database template for all semantic DB tests)
- Owner: root scripts/native_test_support.py `SemanticDeployment` (:281), `PgAdmin.deployment` (:938),
  `_publish_deployment` (:995), `deployment_key` (:896); pure key root scripts/native_deployment_key.py
  `deployment_key` (:109); construction root scripts/native_deployment_build.py:12-19 (`construct_deployment`
  = extension check, empty-namespace check, `semantic.migrations.upgrade(connection)` to head).
- Builds: one sealed database (ALLOW_CONNECTIONS false, IS_TEMPLATE false) cloned from `cs_template` and
  migrated to alembic head. Consumers clone it with `CREATE DATABASE .. TEMPLATE head` plus owner/ACL/
  db-setting/role-setting policy replay (`replay_policy` :589).
- KEY (exact inputs, native_deployment_key.py:109-158; assembled native_test_support.py:896-936):
  1. chain: sha256 of each .py/.mako under python/corpus-structure/semantic_alembic;
  2. artifacts: every other chain file (219 .json, 147 .txt under versions/) by (relative path, size,
     st_mtime_ns), NOT content;
  3. module_imports: sha256 of package .py files reached by a fixed-point import closure from the chain .py
     files (module-level imports only; nested function imports excluded; package initializers read);
  4. construction: sha256 of .py files in the import closure of native_deployment_build.py (nested imports
     included);
  5. uv.lock sha256; 6. `sys.version`;
  7. server: `server_version_num`, `pg_control_system().system_identifier`, `cs_template` database oid,
     installed extension name->version map, (rolname, oid) of the six semantic principals (names from
     `scripts/pg_semantic_roles.sh --principals`).
- Plausible determinants OMITTED (source-established): package data files that are not .py (model/*.yaml
  incl. semantic/physical.yaml, the 36 semantic/sql/*.sql, JSON model assets) because `_module_files`
  (:50-66) accepts only `.py`; PgAdmin's own publication/policy-replay code (native_test_support.py,
  core/db/ownership.py); `cs_template` contents beyond oid + extension versions; ops/postgresql
  provisioning, role attributes/passwords/grants, cluster settings; Settings/env; artifact edits that
  preserve size and mtime.
- Scope/lifetime: session fixture per xdist worker (tests/conftest.py:408) over a database that lives in
  PostgreSQL. `CORPUS_CI_RUN_SCOPE=narrowed` (path/selection runs) => reusable head `cs_sem_head_<key16>`
  retained ACROSS sessions (newest 3 kept, `_retain_deployments` :1088); `qualification` => run-private head
  `cs_sem_head_<key16>_<run8>` (:298-306), rebuilt each run. Workers of one run share one head via advisory
  leases (shared lease + exclusive `:build` lease).
- Stale detection: first clone per `SemanticDeployment` object (per worker) runs `verify_deployment_catalog`
  and compares `current_revision` with `head_revision()` (:352-390); failure => `_replace` (:335): rename
  stale head, record "deployment_key_gap", build a run-private head. So the key is advisory; correctness
  rests on the revision+catalog check (production verifier src/corpus_structure/semantic/
  execution_admission.py:81). `_publish_deployment` refuses an existing head that is unowned, unsealed or
  connectable (:995-1003).
- Consumers: see M2.2; 168 test modules mention at least one native DB fixture name (exhaustive grep).

### M1.2 Per-test clones (template reuse, not state reuse)
- `commit_db_engine` tests/native_fixture_support.py:22: `CREATE DATABASE .. TEMPLATE head` per TEST
  (`cs_sem_test_<pid>_<token>`), policy replay, drop at teardown. 45 test modules (49 incl. support).
  Purpose engines: `commit_writer_engine` :58 (21 test modules), `commit_reader_engine` :67 (13),
  `commit_admitter_engine` :87 (6), `commit_evaluator_engine` :76 (0).
- `semantic_bare_engine` :30: clone of `cs_template` (no semantic schema) per test; 36 test modules; hand-built
  helper functions/DDL and cold-bootstrap controls.
- `semantic_database_at(revision)` :42: per call, clone of `cs_template` + `upgrade(conn, revision)` (migration
  replay); 1 module.
- `infrastructure_engine` tests/conftest.py:462 (session) / `infrastructure_commit_engine` :477 (function):
  clone `cs_template` with its policy; 6 + 2 test modules.
- `_semantic_session_engine` tests/conftest.py:430 (session): one writable clone of the head per worker, lent
  as `native_read` (:437; 4 modules) and `native_rollback` (:443; 16 modules), rollback-only connections.
- Key for these = random `database_name(kind)` (native_test_support.py:99-120); content identity is the head.

### M1.3 Scenario seeds (`scenario_seeds`)
- Owner: root scripts/native_scenario_seeds.py `ScenarioSeeds` (:183); fixture tests/conftest.py:486 (session,
  per worker; closed at teardown).
- Builds: per recipe, a clone of the head populated by a recipe-type builder (tests/scenario_recipes.py
  registry: exact type -> builder; 8 registrations: Kernel, OriginalSeed, BindingSource, Sql, PolicyProjection,
  DeclaredAgent, DeclaredServing, + a test-only Tiny), validated, SEALED, file tree chmod'd read-only
  (`_freeze_tree` :168).
- KEY: in-memory dict key `(recipe, head.name)` (:206): dataclass equality/hash of the recipe object plus
  head database name. `recipe_id` = sha256 of canonical JSON of recipe fields (frozen dataclasses, bytes,
  tuples, scalars only; :34-60) is recorded for provenance. OMITTED: builder/stage code, production modules the
  builder executes (unless their bytes are already recipe fields), Settings.
- Lifetime: per worker, session. Not persisted; no cross-worker sharing (each worker builds its own
  `cs_sem_seed_<pid>_<token>`); dropped at close.
- Stale detection: every hit calls `validate` (:277-301): recipe_id recomputed; db oid/owner/ownership comment;
  sealed (not connectable, not template); policy equals captured; no backend connected. Each clone runs
  `stage.validate_clone(admin)` (:310, :338) and must have a fresh OID (:314).
- Modes: `commit_clone(recipe)` (:304) fresh clone per test; `rollback_family(recipe)` (:322) one family clone per
  (recipe, head) per worker reused through rollback-only cases.
- Consumers: 25 test modules request `scenario_seeds` directly (37 with support); `ddo_kernel` adds 35.

### M1.4 `ddo_kernel` and kernel preparation
- tests/conftest.py:517 -> tests/semantic/data_operation_kernel_support.py `kernel_clone` (:298): requires
  `request.param` to be a `KernelRecipe` (indirect parametrization), `scenario_seeds.commit_clone(recipe)`,
  wraps as `Kernel`. Function scope; 35 test modules (38 incl. support).
- `KernelRecipe` (:63) fields: name, schema_text, declaration_content, manifest_text, execution_profile,
  project_id, declaration_path, additional_files, python_sources, captured_inputs.
- `_prepared_kernel = cache(_prepare_kernel)` (:161): process-lifetime functools.cache keyed by full KernelRecipe
  equality; holds a TemporaryDirectory; runs production `prepare_data_operation_inputs` / `prepare_release` /
  `bound_data_operation_model` / `prepare_data_operation_runtime` (:105-160). Never invalidated. The seed
  builder `build_kernel` (:288) calls `prepare_kernel(recipe, directory=<seed dir>)`: a SECOND, uncached
  preparation into the seed's directory, then `admit_kernel` (persist_release, admit_data_operation_release,
  persist_runtime_binding, direct Core insert into `data.project` :242).
- Recipes are synthetic (inline YAML schema + declarations, STORAGE etc.) or captured production composers
  (`CapturedKernelInputs`).

### M1.5 PDF recipe / `current_pdf_source` and factory
- Owner tests/semantic/current_pdf_source_support.py. `current_pdf_recipe(directory, math_context)` (:46) composes
  production capture/views/region/visual/discovery/profile sources into a `KernelRecipe` with `captured_inputs`.
  A SECOND function of the same name exists at tests/semantic/current_pdf_integration_support.py:63.
- Source-established consequence: production `pdf_capture_custody` (src/corpus_structure/semantic/pdf_capture.py:62-102)
  embeds `str(assets.root.resolve())`, `str(Path(directory).resolve())` and the hex of 14 production .py files
  in the execution-custody artifact. The recipe passes `PreparedPdfAssets(directory, ...)` and `directory/"owned"`
  where `directory` is the test's `tmp_path`, so the KernelRecipe (hence recipe_id, seed identity, and
  `_prepared_kernel` key) differs per test directory. ~25 call sites pass `tmp_path` or a per-module `mktemp`
  (grep `current_pdf_recipe(`). Hard-coded: `PdfRecipe("0"*40, "1"*40, device="cpu", ocr_device="cpu",
  recipe_id="docling-standard-pdf-stream-v1")` (:50-56).
- `_current_pdf_source` (:300-381), per test: patch `PdfWorker.stream`; build a 1-page pdfium document;
  `scenario_seeds.commit_clone(recipe)`; initialize source project; register original; freeze/register demand via the
  production planner; delete the original file; run production `execute_data_demand` (asserts 2 receipts).
  `current_pdf_source` :384 (7 test modules), `current_pdf_source_factory` :390 (17). PDF capture re-executes per
  test; only release admission is seed-cached.
- Other composers: tests/semantic/pdf_staging_support.py:347, tests/evaluate/declared_record_native_support.py:53,
  current_contextual_support.py:128/190, structural_*_native_support.py, rich_domain_native_support.py:40.

### M1.6 Module/session-scoped model, release and pack builders (exhaustive AST)
- 93 module + 25 session fixtures. 49 (48 module, 1 session) call a preparation entry (`prepare_release(`,
  `compile_data_operations(`, `prepare_packs(`, `prepare_kernel(`, `compile_source(`, `acquire_*(`) in 42 modules;
  each is rebuilt per module per xdist worker; no key, no on-disk reuse, no cross-module sharing. Examples:
  tests/semantic/test_external_rich_extraction.py:31/53/58, test_semantic_mcp.py:25/58/63, test_pdf_domain.py:27/33,
  characterization_support.py:45/50, test_contextual_workflow_native.py:116.
- Cross-module sharing exists only for session fixtures: tests/statistics_pack_support.py:11-25 (3 modules; calls
  production `prepare_packs`), tests/math/conftest.py:29-79 (spike_*/s0r2_* chains), tests/ingest/conftest.py:24,
  tests/llm/conftest.py:147.
- functools cache/lru_cache: 50 decorated functions in 36 files + `_prepared_kernel`. Mostly nullary or small-key
  process singletons of immutable inputs: tests/archived_source.py:13 (file by name),
  semantic/data_operation_declaration_support.py:147 `compiled(DeclarationRecipe)`, record_contracts_support.py:48/69,
  semantic/data_operation_binding_support.py:75, tests/math_support.py:190. No invalidation; none keys on source bytes.
- `tmp_path_factory.mktemp` in 15 files (module-scope seeds: characterization_native_support.py:88,
  test_actual_e5_selected_context_native.py:142, test_contextual_workflow_native.py:116).
- `model_checkout` tests/model_change_support.py: function scope; copies model files + physical sources + alembic
  env into tmp and runs `git init` + commit per test; 8 modules.

### M1.7 Private-cohort bootstrap (separate provisioning path)
- Root scripts/native_private_cohort.py + tests/native_private_bootstrap.py: own pg_virtualenv cohort; creates
  `cs_template` and roles itself (native_private_bootstrap.py:66 CREATE ROLE, :81 CREATE DATABASE cs_template).
  Shared-cluster provisioning is shell: root scripts/pg_provision.sh, pg_semantic_roles.sh; ops/postgresql (not in snapshot).

### M1.8 How production keys the analogous thing
- Release: src/corpus_structure/semantic/prepare.py:985 `"release:" + sha256(manifest)`; manifest (:954-980) = root,
  data_operation_model sha, source-interface sha, profile, pinned library versions, sorted (source name, digest),
  sorted (dependency name, digest), ontology sources, vocabularies. Content-addressed.
- Request: semantic/data_operation_identity.py:502 `SemanticRequestKey` = canonical identity of (recipe, subject,
  subject_context, inputs, parameters, inference). Recipe identity :403 `recipe_fingerprint(recipe,
  implementation_slices=...)`; slice identity :378 `implementation_slice_fingerprint` = rooted graph +
  normalization contract + opaque-boundary digests, refusing unknown required dependencies. Runtime: semantic/
  data_operation_runtime.py (`RuntimeBinding`).
- Contrast (facts): test keys are object equality, path/mtime, or AST import-closure hashes; none uses
  `canonical_identity`, `recipe_fingerprint` or `implementation_slice_fingerprint`.

---------------------------------------------------------------------------------------------------
## M2 — Fixture graph facts

### M2.1 Consumption of the two lists (exhaustive grep for each name)
- `PREPARATION_AFFINITY` root conftest.py:11-56: read only by `_preparation_group` (:59-73) from the
  `pytest_collection_modifyitems` wrapper (:90-104). `item.fixturenames` (transitive closure) is intersected with
  the tuple; matching `(fixture, module|None, group)` entries add an `xdist_group(group)` marker; conflicting groups
  raise UsageError; `module` entries match `item.path.relative_to(rootpath)` exactly. No other reader.
- `DB_FIXTURES` tests/conftest.py:101-142: read only at :279-282 to add `pytest.mark.db` when any name is in
  `item.fixturenames`; `db` feeds the plugin's `native_required` (root scripts/qualification_plugin.py:~233).
  20 modules (57 sites) also mark `db` explicitly.
- Definition status (names appearing in no `@fixture` anywhere):
  * PREPARATION_AFFINITY: 37 entries (31 literal + 6 generated). 14 defined, 23 undefined.
    Defined: spike_readings/extraction/scoped + s0r2_readings/extraction/scoped (math conftest, session);
    statistics_pack_inputs/prepared/rules_policy (session); profile (module fixtures in 6 files; entry is
    path-qualified to semantic/test_hanlp_products.py); local_semantic_sql_batch (module,
    tests/semantic/test_local_semantic_admission.py:184); native_read (function; entry qualified to
    test_contextual_workflow_native.py); binding_native_connection (function,
    semantic/data_operation_binding_support.py:118); selected_graph_case (function,
    semantic/test_data_operation_storage.py:2458).
    Undefined (23): source_release (qualified to "tests/test_native_run_scope.py", a root-tree file that exists in git
    but has no such fixture, checked with `git show`), record_custody_case, record_identity_case, record_graph_case,
    contextual_atomic_case, local_witness_case, judged_semantic_case, interpretation_source_case,
    runtime_registration_case, unbound_arrow_case, domain_default_case, domain_formula_source, resubmission_case,
    resubmission_historical_source, exclusion_case, exclusion_read_case, exclusion_literal_case,
    exclusion_refusal_family, occurrence_case, occurrence_refusal_family, imported_declaration_case,
    imported_membership_case, declared_membership_case.
  * DB_FIXTURES: 38 entries. 11 undefined (domain_default_case, domain_formula_source, exclusion_case,
    exclusion_read_case, exclusion_literal_case, exclusion_refusal_family, occurrence_case,
    occurrence_refusal_family, imported_declaration_case, imported_membership_case, declared_membership_case).
    6 more are defined but unsatisfiable: record_source_admin/writer/reader/evaluator/admitter/settings
    (tests/conftest.py:532-567) depend on `private_source`, defined nowhere; no test requests any of them.
  * Dangling requests: tests/semantic/test_source_routing.py:9-12 requests `domain_default_case` (setup error).
    tests/test_native_refusals.py:11,25,37 request fixture `db`, defined nowhere. These two are the only
    unexplained undefined requests in an all-test_* argument scan (minus builtins/parametrize/hypothesis names).
- Defined, 0 test-module requests by argument: `commit_evaluator_engine` (native_fixture_support.py:76);
  `ddo_original_source` (tests/conftest.py:571; only support modules and 2 non-test modules mention it);
  `ddo_application_settings` :578 has 2 test modules.

### M2.2 Shared fixtures carrying expensive preparation (module counts = AST arguments + usefixtures)
| fixture | def | scope | modules |
| native_server | tests/conftest.py:396 | session | 8 test (10 all) |
| semantic_head_template | :409 | session | 2 (4) |
| db_server | :424 | session | 1 |
| commit_db_engine | native_fixture_support.py:22 | function | 45 (49) |
| semantic_bare_engine | :30 | function | 36 |
| native_rollback / native_read | tests/conftest.py:443/437 | function | 16 (17) / 4 |
| commit_clone | :454 | function | 2 |
| infrastructure_engine / _rollback / _commit_engine | :462/471/477 | session/function | 6 / 4 / 2 |
| commit_application_settings | :389 | function | 7 |
| scenario_seeds | :486 | session | 25 (37) |
| ddo_kernel | :517 | function | 35 (38; indirect) |
| current_pdf_source / _factory | current_pdf_source_support.py:384/390 | function | 7 / 17 |
| observed_store_checkouts | :499 | function | 2 |
| cli | :313 | function | 38 |
- `current_pdf_source*` is not registered in conftest; consumers import it into their module. tests/conftest.py
  re-exports others with `as` at :32-62. All function-scope DB fixtures clone per test; sharing exists only at
  head (session) and seed (session, worker-local) levels. Module-scoped builders: M1.6.

### M2.3 xdist grouping / scheduling
- Root pyproject.toml (`git show 1afa63f88:pyproject.toml`) `[tool.pytest.ini_options]`: testpaths
  ["tests","python/corpus-structure/tests"], `--import-mode=importlib`, `-n auto`, `--dist=loadgroup`,
  `--max-worker-restart=0`, `-m "not shared_cluster_fault"`, `--strict-markers`; markers provider_evidence,
  prerequisite(name), sql_family(...), db, shared_cluster_fault; pythonpath ["scripts","python/corpus-structure/tests"].
- `loadgroup` semantics (inference, not observed): only `xdist_group` tests stay together; ungrouped tests are
  scheduled individually, so a module's tests and its module-scoped fixtures can spread over workers.
- Group sources: (a) PREPARATION_AFFINITY, 14 live entries (math_preparation, statistics_pack, hanlp_profile,
  local_semantic_sql, named_cue_read, ddo_binding_source, ddo_selected_graph); (b) explicit marks at 3 sites only:
  tests/semantic/test_actual_e5_selected_context_native.py:55, test_actual_pdf_spool_resume.py:19,
  test_actual_gliner_batch_semantics.py:43. None of the 93 module-scoped builders (M1.6), the `scenario_seeds` users
  or `ddo_kernel` users carries a group.
- Root conftest.py also: scratch under build/tmp/pytest (:77-87); `shared_cluster_fault` controls refuse any parallel
  run or mixing with ordinary tests (:107-111).
- Root scripts/qualification_plugin.py: logical node ids before group suffixes (:57-70); `affinity_groups` per
  node at collection_finish (:225-236); worker events (:392-398); `native_required` = `db`-marked.
  cli/testing.py:364 states worker assignments are not retained ("Affinity groups are collection designations").
- `uv run ci test -- PATH`: cli/testing.py `run_tests` (:889) -> `_lane` (:707-790) sets CORPUS_CI_* (narrowed/
  selection => `CORPUS_CI_RUN_SCOPE=narrowed` = reusable head; full => `qualification` = run-private head) and runs
  `run_recipe("test-all")` -> root scripts/test_receipts.py:2255-2300: paths => `-n auto --dist=loadgroup -m "not
  shared_cluster_fault"`; exactly one explicit `::` node id => `-n 0`; N>1 explicit node ids without -k =>
  `--maxprocesses N`; fault lane and collection-only => `-n 0`; `--workers` overrides only for the ordinary lane.
  `ci test scheduling <id>` reads logical affinity vs observed workers (cli/testing.py:1270).

---------------------------------------------------------------------------------------------------
## M3 — Boundary doubles and bypassed constructors

### M3.1 PDF converter boundary
Production: src/corpus_structure/ingest/pdf_worker.py:280 `stream(...)`; the real child (:85-135) writes records,
acknowledges `completion.jsonl` as `native_completion`, calls `certify_native_stream`
(semantic/pdf_certification.py:466) and returns `PdfStreamReply(status, errors, recipe, page_replays, records,
effective_options, certified_sets, certification, access_replay)` (ingest/pdf_stream_types.py:145). Production
publication REFUSES a reply lacking certification: orchestrate/pdf_streaming.py:529 ("native PDF publication has no
producer certification").
Test replacements (exhaustive grep `PdfWorker`, `"stream"`, `PdfStreamReply(`):
- Certified (write `native-preparation.json`, `completion.jsonl`, companions, certificate, access replay through
  production `certify_native_stream`): tests/semantic/current_pdf_source_support.py `_certified_controlled_reply`
  :188, `_controlled_stream` :235, `_section_stream` :411. Users: `current_pdf_source` (7), factory (17),
  test_contextual_workflow_native.py:125, test_actual_e5_selected_context_native.py:147,
  test_current_pdf_source_inputs.py:49-58.
- Uncertified (5-argument `PdfStreamReply("success", (), recipe, (), records + occurrences)`: default
  effective_options b"{}", no companions, `certification=None`, `access_replay=None`, no native_preparation/
  completion entries; they call `write_native_occurrence_batches` + `write_record_batches`):
  1. tests/semantic/test_pdf_transform_demand_native.py:66-110 (also patches `PdfWorker.enrich` :173 and
     `RecognitionWorker._recognize_pages`);
  2. tests/semantic/test_pdf_materialization_native.py:36-80;
  3. tests/semantic/current_pdf_integration_support.py:260-306 (patched :429; document from a retained native
     fixture, candidate pages on the spool);
  4. tests/semantic/current_artifact_support.py `artifact_stream` :80-140 (patched :218, used by `companion_source`);
  5. tests/evaluate/declared_record_native_support.py `controlled_table_stream` :190-247 (patched :357);
  6. tests/semantic/rich_domain_native_support.py `decimal_source_stream` :93-152 (substituted for #5 by
     `monkeypatch.setattr(support, "controlled_table_stream", ...)` in test_rich_domain_preservation_native.py:235,
     test_rich_domain_external_native.py:53-56);
  7. tests/semantic/test_nce02_native_scope.py `list_stream` :205-251 (passed as `stream=` to `_current_pdf_source`
     :269).
  Sites 1-5 and 7 reach production `execute_data_demand`. Whether each passes the :529 check at this commit was NOT run;
  fact only: their reply lacks the fields that check requires.
- Other: tests/orchestrate/test_pdf_streaming_integration.py:112 replaces only `PdfWorker._child_target` with a child
  that swaps docling `DocumentConverter` for `_ScriptedDocumentConverter` (:96-103): real child + certification path,
  external converter only. tests/orchestrate/test_pdf_private_execution.py:206 replaces the whole `PdfWorker` class,
  `OwnedPdfSource.acquire`, `begin_pdf_build`, capacity hooks (labelled pure ownership control).
  tests/pdf_process_support.py:83/100 and tests/ingest/test_pdf_build_spool.py:308 construct replies for process/spool
  controls. 6 `PdfWorker.stream` setattr sites; 8 PdfWorker setattr sites overall.
- Production-route alternative in tests: tests/pdf_acceptance_support.py `stage_pdf_document` :34 (certifies authored
  bytes via `prepare_pdf_producer_contract`, `write_pdf_companion_sets`, `PdfProducerPayloads.certify`, `adopt_pdf_batch`,
  `stage_pdf_access_projection`, `record_pdf_producer_certification`; docstring: shares production callbacks, keeps
  expectations independent). Users: tests/semantic/test_pdf_projection_replay.py:42, test_pdf_owner_counts.py:107
  (2 modules), plus `stage_complete_native` :146 and `seed_pdf_shared_stream` :222 (raw SQL constructor). It stages into a
  database directly, not through `PdfWorker`. Nearest production-route stream double: `_certified_controlled_reply`.

### M3.2 Executor constructed without its constructor
- `object.__new__`/`__new__` of NativeDemandExecutor: 7 sites (exhaustive grep `__new__\(`):
  tests/semantic/test_d1_limitation.py:292; tests/semantic/test_data_operation_capabilities.py:428;
  tests/orchestrate/test_data_operation_execution_basis.py:47,109,396,465; tests/orchestrate/test_data_operation_byte_admission.py:71.
  Attributes assigned/monkeypatched afterwards, counts of uses across these files: _physical 13, engine 6, holder 4,
  model 3, runtime 2, prepared 2, and one each of reservation, port_workers, policy, budget, _preparation_bytes,
  _quarantined, _failed_requests, capability_factories, fitter_engine, nemotron_endpoint, _contexts, _target_context;
  replaced methods _hydrate, _prepare_ready, _ready_context, _execution_context, _port, _publish, _retain_answer,
  _ready_items, _prepare_page. Most sites assign 1-4 attributes (private-method controls); byte_admission.py:71-90
  assigns ~14 incl. `model` as a SimpleNamespace.
- Other bypassed constructors (same grep): PublishedPdfReader x10 (test_pdf_lifetimes:86,147; test_pdf_record_reader:92,110;
  test_pdf_transform_operations:313; test_scoped_native_inspection:75; test_pdf_whole_read_scope:16,93;
  test_native_source_budgets:93; test_pdf_read_cancellation:119), PooledConnection x2 (db/test_notice_registration.py:20,31),
  _RunExecution (orchestrate/test_data_operation_physical.py:44), _RequestExecution (test_data_operation_relay.py:13),
  docling pipeline/CodeFormulaVlmModel (test_pdf_streaming_integration.py:28,33), NativeHost (methods/test_native_host.py:57),
  InvariantViolation (test_native_refusals.py:57).
- Public constructor src/corpus_structure/orchestrate/data_operations.py:631-698. Required: `engine`, `prepared:
  PreparedRelease`, `runtime: RuntimeBinding` (same release_id), `sources: PythonSourceCollection`. Derived inside:
  `DataExecutionBasis` (prepared, runtime, sources, schema, declarations, captured_contracts, runtime_locations) or
  `execution_host.context(basis)`; `bound_data_operation_model(prepared)` (real model); `database_capacity` via
  `_database_capacity` (:614): an engine without `_corpus_store` REQUIRES explicit `database_capacity >= 3`;
  `port_workers = min(policy.max_provider_jobs, capacity-2)` (>=1); `reservation = 2*max_packet_bytes +
  3*max_reply_bytes` must be <= `policy.max_owned_bytes`; `OwnedByteBudget`; `capability_factories` checked against the
  model (`capabilities.preparation == "none"` => refusal); holder uuid; lock/quarantine flag. `_failed_requests` and
  `_physical` are set later (:1952, :1959), not in `__init__`.
- Public-constructor sites for comparison (engine, prepared, runtime, sources, usually runtime_locations/schema/
  `database_capacity=6`): tests/orchestrate/test_data_operation_execution.py:71, test_data_operation_stream_execution.py:92,
  test_data_operation_claim_source_native.py:86, test_m1_declared_native.py:131, tests/semantic/test_data_operation_external_native.py:186.
  Production wrapper `execute_data_demand` (semantic/data_operation_service.py:211) adds host scope, admission-engine target
  comparison and `database_capacity`.

### M3.3 Native host doubles vs real checks
- Real: src/corpus_structure/methods/native_host.py: `NativeHost._validate_startup` (:197-213: provider, profile
  fingerprint, runtime_identity, assets, device, dtype `torch.<dtype>`, backend, matmul_precision, cudnn_allow_tf32,
  intra/inter-op threads); `NativeHostGroup.declare` (:512-546: conflicting acquisition identity, post-serving
  declaration refusal, thread-policy equality, one offline backbone cache per host); `startup` (:620) = declare + ensure +
  host startup record; `NativeHostResidency` (:660). Worker loaders methods/native_host_adapters.py `load` (:17),
  `_gliner` (:76), `_spacy` (:268).
- Doubles (grep `class Group|class Host|def startup(self`, `"NativeHostGroup"`, `group_factory`):
  * tests/methods/test_characterization_resources.py:45-103 `Group` (patched by `monkeypatch.setattr(resources,
    "NativeHostGroup", Group)` :104; 2 uses): `startup(selected, active)` :59 re-implements ONE check
    (`native.artifacts != {"artifact": 1}` -> Pm2WorkerRefused) and returns a fabricated startup dict (runtime_identity,
    assets, device, dtype); `declare` re-implements declared-before-serving; `infer_result` fabricates
    `NativeHostResult`/`NativeExecutionReceipt`.
  * tests/methods/test_native_host.py:99-111 `Host` (host_factory) and :330 `Group` (patched `native_host.NativeHostGroup`
    :347; `group_factory=` :733, :814): startup `{fingerprint: {}}`. The same module has real tests of the real checks
    (:563 real host startup cancellation, :616/:642 startup comparison/pool roster).
  * tests/semantic/test_hanlp_products.py:286-300 `Host`: `declare` stores; `startup` asserts selection identity and
    returns `dict(max_sentences=8)`.
  * tests/semantic/test_downstream_profile_acquisition.py:69 patches `NativeHostGroup.__init__` to a no-provider constructor.
  Real-group users: tests/semantic/native_provider_support.py:21, test_sentence_products.py:183-186,
  test_construction_products.py:456-466, test_combined_native_qualification.py:87.
  None of the doubles invokes `_validate_startup` or the declare checks; each owner module restates a subset.

---------------------------------------------------------------------------------------------------
## M4 — SQL text coupling and hand-written SQL in tests (ADR-0131 context)

Production hand-authored SQL: 36 files in src/corpus_structure/semantic/sql/ (data_operations.sql, closure.sql,
pdf_record_*.sql, record_policy.sql, ...); migrations: semantic_alembic/versions (219 .json, 147 .txt, 285 .py, + .sql),
target_alembic/versions 20 files. Whole-tree counts (files / occurrences, exhaustive grep):
text( 173 / 878; exec_driver_sql 80 / 435; INSERT INTO 36 / 96 (into ops|sem|data|kb|meta: 18 / 61); UPDATE..SET 25 / 52;
DELETE FROM 11 / 20; UPDATE/DELETE on production relations 19 files; ALTER TABLE|FUNCTION|ROLE|DATABASE|SCHEMA|TYPE 20 / 38;
CREATE [OR REPLACE] FUNCTION 41 / 92; GRANT/REVOKE 23 / 64; SET [LOCAL] ROLE 26 / 52; `FROM (sem|data|kb|meta|ops).<rel>`
93 / 405; schema-qualified relation literals 229 / 1656; pg_catalog/information_schema 25 / 55; literal `corpus_sem_*` roles
48 / 217; Core `table("..")` 30 / 100; Core `insert(` 36 / 81; pglast 30 / 49; `prepare_sql(` 26 / 39;
`assert "<text>" in <source|sql|body|statement>` 52 / 115.
### M4.1 Tests that read production .sql files (17 modules)
tests/semantic/: test_data_operation_constraint_custody, _cpu_basis, _execution_guard_sql, _identity_native, _json,
_population_selection, _protocol_values, _replicate_policy_sql, _retirement_context_sql, _selected_graph_sql,
_trust_snapshot_sql, test_native_sql_body, test_pdf_access_correspondence, test_pdf_record_context, test_pdf_record_native,
test_record_policy_native_predicate, test_target_installation. Mostly `files("corpus_structure.semantic").joinpath(
"sql/data_operations.sql")` (10 modules) or `src/.../sql/<name>.sql`.
### M4.2 Splicing SQL by anchor text (8 modules)
`source.index("CREATE OR REPLACE FUNCTION ops.x(")` / `"IF .."` / `"END $$;"`, cut a function or guard fragment,
`.replace("ops.", "pg_temp.")`, execute on a bare/rollback connection: test_data_operation_trust_snapshot_sql.py:19-26,52-60,126;
_identity_native.py:121-124; _json.py:85-89; _replicate_policy_sql.py:13-16; _execution_guard_sql.py:29; _selected_graph_sql.py:33-36;
_retirement_context_sql.py:31-36,146-149; test_record_policy_native_predicate.py:111-114. Also test_record_fit_native.py:192
(`sql.replace("__DDO_CORE_<NAME>__", body)`), test_published_section_views.py:312, test_pdf_observations.py:252.
### M4.3 Substring assertions on SQL text
test_native_sql_body.py:195-215 (`function_bodies(...)` of closure.sql then `"... IS DISTINCT FROM '24'" in archive`,
`"THEN RETURN;" not in ...`); tests/schema/test_data_steps.py:84-88 (generated N1 step statements contain
`"SELECT DISTINCT sem.data_operation_definition.release_id"`, `"UPDATE ops.data_population SET context_key="`); 52 files overall
carry `assert "<text>" in <sql/source/body/statement>` (115 sites, includes non-SQL sources).
### M4.4 Hand-written SQL to set up / inspect / tamper
- Setup: 18 files insert into production schemas (61 sites): tests/pdf_acceptance_support.py:222-260 `seed_pdf_shared_stream`
  (raw INSERT/UPDATE of `ops.pdf_stage_artifact_stream` / `ops.pdf_artifact_stream`), tests/semantic/test_pdf_companion_field_reader.py:52-78
  (`CREATE TABLE ops.pdf_artifact_stream` + INSERT), data_operation_kernel_support.py:242 (Core insert into `data.project`).
- Inspect: `SELECT .. FROM (ops|sem|data|kb).<rel>` in 93 files, e.g. orchestrate/test_data_operation_execution.py (counts of
  `ops.data_derivation`, `kb.data_product.canonical_body`).
- Posture/catalog: tests/semantic/test_data_operation_storage_posture_native.py:7-40 hand-lists RELATIONS and PURPOSE_ROLES with
  raw pg_class/pg_trigger queries.
- Fixture-only writers: `seed_pdf_shared_stream` (docstring: raw constructor, administrative SQL fixtures only); the production-route
  writer is `stage_pdf_document` (M3.1).
### M4.5 Tests of the new generators and what they compare against
- tests/semantic/test_physical_checks.py (167 lines): builds a throwaway LinkML schema with `ph:checks`/`ph:indexes` annotations
  via `compile_metadata`; compares generated `CheckConstraint` columns, `physical_expression_sql(check.sqltext) == '"end" >= start'`
  and `str(CreateIndex(index).compile(dialect=postgresql)) == "CREATE INDEX ix_start ON data.span ... WHERE start IS NOT NULL"`
  (hand-written expected strings). :41-83 uses production `PHYSICAL_MODEL` with one byte replacement (`ph:search_configuration:
  english -> simple`) and asserts vector/population predicates. :86-130 executes generated DDL on `semantic_bare_engine`
  (hand-written `CreateSchema("data")`, inserts, expected IntegrityError) and an Alembic autogenerate ordering check;
  PostgreSQL behavior is the independent oracle.
- tests/semantic/test_pdf_prepare_model.py (58 lines): mutates cloned `Table`s from production `metadata` (quoted column rename,
  appended column), calls private `_prepare_pdf_copy_statements`, compiles with literal binds, parses with pglast, compares the INSERT column
  list and SELECT projection to the same Tables' column names (expectation derived from the metadata the generator reads, independent of
  SQL text). Second test asserts `inventory["ops.prepare_pdf_build(text,bigint,bigint,text,text)"]["execute_roles"] == ["corpus_sem_writer"]`
  (hand-written signature and role). The family tuple `("companion","endpoint","companion_field","access","region")` is hand-listed (:20-24).
- tests/schema/test_data_steps.py (292 lines): generated `DataStep` statements asserted by substring (M4.3), `implementation_sha256`
  length 64, libraries == {sqlalchemy, alembic, pglast}; Alembic op ordering against hand-built ops; frozen-upgrade test executes stored
  statements with a stub and asserts equality with `step.statements`.
- Related, not generated-SQL tests: tests/semantic/test_prepared_sql.py, tests/test_cli_model_inspect.py, tests/schema/test_model_explanation.py
  (`prepare_sql("SELECT ..")` inline strings; SQL-source preparation/explanation).
### M4.6 Provisioning that creates roles/databases/grants itself
- PgAdmin (root scripts/native_test_support.py): `create` :464-475 (f-string `CREATE DATABASE {quote(name)} TEMPLATE {quote(template)}`
  plus production `DatabaseCreation`/`stamp_owned`); `replay_policy` :589-640 (ALTER DATABASE OWNER/CONNECTION LIMIT, REVOKE ALL / GRANT
  with grant options, `ALTER DATABASE .. SET .. FROM CURRENT`, `ALTER ROLE .. IN DATABASE .. SET`, role-self replay via purpose logins);
  `seal_database` :978; `_publish_deployment` :995 (create build db, construct, seal, RENAME); `sweep` :852; `policy` :547. `semantic_principals()`
  :397 shells `pg_semantic_roles.sh --principals`; `check_roles` only verifies existence (no CREATE ROLE in test support).
- Production counterpart that already clones from a template: src/corpus_structure/cli/db.py `_create` (:71-137): encoding check,
  template-exists check, extension check, pglast `CreatedbStmt`, `stamp_owned`; core/db/ownership.py (`DatabaseReservation`,
  `DatabaseCreation`, `OwnedDatabase`, `stamp_owned`, `acknowledged_database`). PgAdmin imports the ownership types but does not call `_create`;
  src has no CREATE/DROP DATABASE, ALTER DATABASE, CREATE ROLE or ALLOW_CONNECTIONS outside cli/db.py (grep of src *.py).
- Other direct DB creation in tests: tests/test_db_fixtures.py:279, tests/db/test_cli_db.py:108, tests/semantic/test_native_deployments.py:171,
  test_native_fixtures.py:204,374,409 (f-string `CREATE DATABASE .. TEMPLATE template0`; 7 sites in 5 files); tests/native_private_bootstrap.py:66,81.
- Roles are provisioned by shell (root scripts/pg_semantic_roles.sh: publisher/writer/reader/evaluator/fitter/admitter); tests only name them
  (48 files, 217 literals) though `semantic_principals()` exists. In-test role/grant SQL: GRANT/REVOKE 23 files, SET ROLE 26, ALTER ROLE/DATABASE 20.

---------------------------------------------------------------------------------------------------
## M5 — Model restatement vs deliberate independence

### M5.1 Support modules: production pack acquisition vs own model (exhaustive grep)
- Production acquisition (`prepare_packs`/`acquire_packs`/`acquire_pack`, semantic/regeneration.py:297-354; composes semantic.yaml + core.yaml +
  terminology + methods.yaml + rules + native/physical/DDO sources): 7 files: tests/statistics_pack_support.py:11-25 (the ONLY non-test support
  module), tests/schema/test_packs.py, tests/semantic/test_alias_policy.py, test_pack_acquisition.py, test_schema_product_cli.py,
  test_terminology.py, tests/test_cli_schema_diagnostic_boundaries.py.
- Own model compilation: `prepare_release(` 131 files / 266 sites; literal `SourceBundle(` 144 / 213; literal `SourceArtifact(` 180 / 366;
  `compile_data_operations(` 88 / 286; inline `id: urn:`/`id: https://` YAML schemas 54 files / 72; reads of core.yaml 102 files / 144.
- Hand-listed bundle contents mirroring `acquire_pack`: statistics semantic.yaml (15 files), terminology.yaml (10), artifact names
  "statistics_semantic" (13), "semantic_core" (23), "statistics_terminology" (10). Examples: tests/semantic/record_contracts_support.py:48-62
  (3-file SourceBundle: domains/statistics/semantic.yaml, model core.yaml, terminology.yaml, then `observation_inputs`, `prepare_release`);
  tests/evaluate/declared_record_native_support.py, tests/methods/m1_producer_support.py, methods/record_assembly_support.py,
  tests/orchestrate/test_m1_declared_native.py, tests/semantic/test_declared_record_sources.py, test_m1_declared_products.py, test_statistics_model.py.
- tests/model_change_support.py:14-17 hand-lists `("core.yaml","system.yaml","revisions.yaml")`; physical sources come via production closure helpers.
- Direct domain-dir references: `domains/` 47 files / 100 sites; `DOMAINS /` 8 files.
### M5.2 Operation ids, class names, role and relation lists (literal counts)
- Operation ids: 15 distinct `"source.<family>/<op>"` literals in 28 files, ~120 occurrences: "source.selected_views/discovery" 21,
  "source.pdf_views/discovery" 19, "source.pdf/capture" 19, "source.pdf_recognition/observe" 13, "source.pdf_integrated/reconcile" 9,
  "source.pdf_sections/organize" 8. Model IRIs `https://corpus-structure.dev/semantic/...`: 43 files / 92 (DdoSelectedNativeSource 20,
  DdoPredicateInspectionReport 6, DdoCandidateInspectionReport 6, ...). `Ddo[A-Z]\w+` class-name literals: 110 files / 878 (DdoRichEntity 44,
  DdoRichOccurrence 40, DdoRichAdmission 36, DdoRichSelectedMember 34, DdoSelectedNativeSource 32, ...).
- Relation lists (>=5 schema-qualified names in one literal): 16 lists in 12 files, e.g. test_metadata.py:224,236; test_target_installation.py:23,33,44;
  test_pdf_publication.py:662; test_record_policy_native_predicate.py:87; test_data_operation_cpu_basis.py:73; test_rich_admission_native.py:27.
  Long lowercase-token lists (>=9) in 45 files (51 lists; mixed content incl. DB_FIXTURES and tests/test_cli.py:16).
- Role names `corpus_sem_*`: 48 files / 217 literals; `PURPOSE_ROLES` test_data_operation_storage_posture_native.py:13-19.
- Column shape: reflection (`.c.keys()`, inspector, information_schema) in 13 files / 20 sites: most column-shape checks reflect rather than restate.
  Hand-written row dicts (not reliably greppable, not counted): pdf_acceptance_support.py `inventory()` :196-215, `seed_pdf_shared_stream` params.
- Enum/value-set members: no global scan (no reliable grep); not established.
- Fixture-name lists as restatement of fixture graph: DB_FIXTURES (38) and PREPARATION_AFFINITY (37), 17+23 stale (M2.1).
### M5.3 Deliberately independent expectations (do not count as duplication)
- tests/semantic/record_contracts_support.py: "fixture coordinates and role expectations are authored independently" (`record_from_fields`
  :119-125; `table_record` :124, `formula_record`, `measurement_record`), finished through production identity functions (`record_identity`,
  `interpretation_identity`). 10 consumer modules (test_record_product_schema, test_record_projection, test_interpretations, test_rich_queries,
  test_rich_scientific, test_rich_operations, test_rich_knowledge_sources, test_attributed_source_evidence, rich_record_readings_support,
  attributed_source_evidence_support). It compiles its own 3-file model (M5.1), not `prepare_packs`.
- tests/pdf_acceptance_support.py: shares production callbacks/validation; "expected native values and deliberate SQL tampering stay independent"
  (:34-45; "independent expected text" in `stage_complete_native`).
- tests/semantic/test_data_operation_storage_posture_native.py:7-9: "Independent actual storage expectations".
- tests/semantic/current_pdf_source_support.py:188,235: fixture document content independently authored; encoding/certification are production calls.
- tests/semantic/test_data_operation_identity_native.py `JSON_MEANING_VECTORS` (hand vectors vs SQL function and `semantic_value`);
  test_physical_checks.py expected predicate/index strings; test_data_steps.py `len(step.implementation_sha256) == 64`.
- tests/evaluate/golden/ (test_sets.py, test_split.py), tests/fixtures/semantic + tests/fixtures/trace archived inputs (tests/archived_source.py:13),
  tests/evaluation_record_alignment_support.py, tests/evaluate/declared_record_grading_support.py. A phrase grep ("independent(ly) authored|expected|
  oracle|source|original|selected") hits 89 files; I did not classify each.

---------------------------------------------------------------------------------------------------
## Sampling statement
Exhaustive (whole-tree grep/AST): fixture definitions and scopes; request counts (arguments + usefixtures only); undefined fixture names; cache
decorators (50); `__new__` sites; `PdfWorker`/`PdfStreamReply(` sites; SQL-token counts in M4; `prepare_packs` family; `Ddo*`, IRI, operation-id,
role-name literals.
Sampled (files opened): native_test_support.py, native_deployment_key.py, native_scenario_seeds.py, tests/conftest.py, root conftest.py,
current_pdf_source_support.py, data_operation_kernel_support.py, pdf_acceptance_support.py, the uncertified stream doubles, test_native_host.py,
test_characterization_resources.py, test_physical_checks.py, test_pdf_prepare_model.py, test_data_steps.py (header and assertions), four SQL-splicing
tests, record_contracts_support.py, and the production counterparts named above.
Not done: no test was run (pass/fail of the uncertified doubles and of test_source_routing.py is unobserved); module-scoped fixture spreading across
workers is inferred from loadgroup semantics; classification of the 89 "independent" files and an enum/value-set restatement scan were not completed;
root tests/ (34 files) was only listed. Scenario-seed build cost per recipe and counts of distinct recipes were not measured.
