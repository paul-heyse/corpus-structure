# F06 map: completed-capture seed stage for the current PDF source fixtures

Snapshot: scratchpad/audit/snap3/python/corpus-structure/ (commit 50827eb9f). Paths below are relative to it
(`scripts/…` = snap3/scripts/…). Nothing was run. Read fully: tests/semantic/current_pdf_source_support.py,
tests/scenario_recipes.py, scripts/native_scenario_seeds.py, data_operation_kernel_support.py lines 40-310,
data_operation_original_support.py lines 1-135, the pdf_capture.py custody/port code. Sampled (call-site
windows, not whole files): every consumer module listed below, current_artifact_support.py,
current_pdf_integration_support.py, declared_record_native_support.py, pdf_streaming.py (producer/finish
paths), pdf_publication.py (grep only), original_documents.py.

## 1. `_current_pdf_source` end to end

Definitions (tests/semantic/current_pdf_source_support.py):
- `_current_pdf_source(scenario_seeds, tmp_path, monkeypatch, *, stream=None, sections=(), math_context=False)`
  contextmanager, line 292. Yields a frozen `CurrentPdfSource(kernel, demand_id, document_key, original, sections)`.
- `current_pdf_source` fixture, line 383 (function scope; no args varied: default stream, sections=(), math False).
- `current_pdf_source_factory` fixture, line 389; returns `acquire(rows, *, math_context=False)` which builds a
  `_section_stream(rows, …)` and passes `sections = ("#/groups/0".."#/groups/n-1")`; returns the context manager
  (caller must use `with`).
- Registration: none in a conftest. tests/conftest.py defines only `scenario_seeds` (line 486, session scope,
  `ScenarioSeeds(native_server, semantic_head_template, native_settings, tmp_path_factory.mktemp)`). Each consumer
  module re-exports the fixture by import (`from semantic.current_pdf_source_support import current_pdf_source as
  current_pdf_source`), 17 modules.

Steps, in order:
1. `monkeypatch.setattr(PdfWorker, "stream", stream or _controlled_stream)` (in-process; persists for the whole test).
2. Builds a blank 1-page PDF with pypdfium2 and writes it to `tmp_path/independent-original.pdf`.
3. `recipe = current_pdf_recipe(tmp_path, math_context)`: a `KernelRecipe("current-pdf-source", …,
   captured_inputs=CapturedKernelInputs(bundle, dependencies, PreparationProfile))`, project_id None,
   execution_profile "source-native". The PDF capture custody artifact is built with
   `PreparedPdfAssets(tmp_path, b"{}", ())` and `directory=tmp_path/"owned"`.
4. `scenario_seeds.commit_clone(recipe)`: seed = release persisted + data-operation release admitted + runtime
   binding persisted (build_kernel). The test gets a fresh clone database.
5. In one write transaction on the clone: `initialize_source_project(PROJECT="current-source-catalog")`,
   `register_original_document(original_path=str(tmp_path/…pdf))`, `acquire_original_document_selection`,
   `freeze_demand(targets=("source.pdf_views/discovery",), selections only when sections given)`,
   `DemandPlanner.register`. Commits.
6. `path.unlink()` (retained custody must serve; no local fallback).
7. `execute_data_demand(kernel.purpose("write"), demand, source_root=ROOT, admission_engine=purpose("admit"),
   project_id=PROJECT, database_capacity=6)`; asserts `receipt_count == 2`. This is the full capture: private
   native build, spool, certification, access projection, freeze/prepare/validate/seal publication, discovery.
8. Yields `CurrentPdfSource`. The clone is torn down when the context exits.

Varying inputs per consumer: `stream` (converter double), `sections`, `math_context`. Via the factory: `rows`
(label, text, orig, formula-outcome) and `math_context`. `rows` fix both the double's document and `sections`.
Constant: original PDF bytes (one blank 200x300 page), PROJECT, document_key, execution profile.

State when it returns: all committed (every write is in `engine.begin()` blocks; `execute_data_demand` returns
after both receipts). No unfinished task is expected (the seed registry itself refuses `claimed/running`
`ops.task` rows at sealing, native_scenario_seeds.py:247-257, a rule that would apply to a captured stage too).
Filesystem leftovers: `tmp_path/independent-original.pdf` deleted; `tmp_path/owned/producer/...` holds the build
spool (manifest.jsonl per attempt, page/record Arrow replays) because the spool is retained, not cleaned
(pdf_streaming.py:168-169 docstring; `spool.close()` only). DB rows contain the path strings (see section 4).

IMPORTANT, found while tracing: the seed key is the recipe value. `pdf_capture_custody`
(src/corpus_structure/semantic/pdf_capture.py:81-102) canonicalises `str(assets.root.resolve())` and
`str(Path(directory).resolve())` into the `pdf-capture/execution-custody` SourceArtifact, so the recipe (hence
`recipe_id`, release_id, runtime_id and the `ScenarioSeeds._seeds` key) embeds the test's `tmp_path`. In the
function-scoped fixtures, no two tests share a recipe, so today there is no seed reuse across tests for
`current_pdf_source*`: each test builds its own seed (release admission) plus a clone. Also each seed's
`directory` is a new `tmp_path_factory.mktemp("seed-KernelRecipe")`. A second stage keyed on the same recipe
would have one consumer per key unless the path is made test-independent (e.g. a fixed directory).
Module-scoped fixtures (section 2, rows M) already use one stable `tmp_path_factory.mktemp` directory.

## 2. Consumers of `current_pdf_source`, `current_pdf_source_factory`, `_current_pdf_source`

Counting unit: test functions (cases = incl. parametrization). All consumers commit further writes (they run
more demands or register more rows); fine for a clone. Capture state is read, never altered, except where noted.

### A. Default fixture `current_pdf_source` (default stream "Independent current source", no sections) — all "after"
Recipe R0 = (default stream, sections=(), math False). 12 functions, 16 cases, all one recipe (if the path were
shared):
| module | test | notes |
|---|---|---|
| semantic/test_current_source_graph_native.py | test_actual_computational_source_hierarchy_keeps_native_pointer_custody | reads, exports demand |
| semantic/test_source_discovery_native.py | test_actual_source_discovery_closure_and_scoped_child_publication [3 cases] | registers a second original + runs a discovery demand. Writes `kernel.preparation.directory/"uncaptured.pdf"` for the views=False cases: that is the frozen seed directory; by reading it should raise PermissionError (not run, unverified) |
| semantic/test_companion_export_native.py | test_current_selected_companion_families_export_exact_empty_populations | read/export |
| same | test_export_cancellation_spans_actual_metadata_handoff_and_bulk [3 cases] | read; patches export module |
| semantic/test_source_search.py | test_source_search_requires_only_source_demand_and_mcp_returns_exact_handles; test_artifact_pages_remain_bound_to_exact_selected_publication; test_publication_fill_is_separately_bounded_replays_exact_set_and_authenticates_pin; test_opening_search_hit_rechecks_fresh_pinned_projection; test_concurrent_first_find_uses_one_bounded_producer_and_both_requests_progress | 5 fns; read/search; two monkeypatch DataOperationStorage/pdf_section_views after capture |
| semantic/test_native_render_journey.py | test_current_native_render_retains_real_original_geometry_and_png | new render demand, executes |
| semantic/test_pdf_observation_catalog.py | test_failed_provider_observation_remains_selected_and_inspectable | new visual demand + external packet submit; `dataclasses.replace(case, demand_id=…)` |
| semantic/test_native_exports.py | test_complete_docling_json_export_preserves_native_shape | export |
Open point: render/visual demands execute after capture with the stream patch still active; whether they need
the patch is unverified (visual render reads retained publication; unlikely).

### B. Factory `current_pdf_source_factory` (rows -> `_section_stream`, sections groups/0..n-1)
Each recipe below = (rows, math). "after" claims with a distinct recipe = **varies** unless noted. Counts are functions.
| module | test/fixture | rows / args | class |
|---|---|---|---|
| semantic/test_selected_source_native.py | test_native_selection_context_and_offline_preparation | 2 formula rows, math_context=True | varies |
| semantic/test_native_definition_demand.py | test_actual_definition_demand_retains_provider_pair_and_exact_component_source (gpu, provider) | 1 text row (long definition TEXT) | varies |
| semantic/test_native_parser_demand.py | test_actual_parser_demand_preserves_three_families_and_exact_resume (gpu) | 1 row, 3 joined passages | varies |
| semantic/test_pm2_parser_stage_native.py | test_actual_dipo_reclaim_refuses_stale_holder_before_current_publication (gpu) | 1 row, 2-sentence passage | varies |
| semantic/test_pm2_result_native.py | test_original_spelling_remains_inspectable_without_current_native_occurrence | 1 row ("text","x+y","x + y") | varies |
| same | test_actual_current_d1_limitation_is_inspectable_beside_successful_products (gpu) | 3 rows ("12", 6000x"12", 7000x"unexamined") | varies |
| semantic/test_nce02_native_scope.py | test_current_native_clipped_role_population_detects_omitted_roles | 1 row "The analyst records the input." | varies |
| semantic/test_structural_native_replay.py | test_current_native_comparison_consumes_actual_predicate_and_formal_source_products [2 cases] | 2 rows per case, different literals per case | varies (1 consumer per recipe) |
| semantic/test_structural_admission_native.py | fixture structural_native_journey -> 2 tests (test_actual_structural_authorship_issuer_dossier_selected_gap_and_detached_export; test_definition_admission_refuses_same_shaped_controlled_fixture_producer) | 2 identical text rows (TEXT) | after; 2 consumers, same recipe; the journey itself is built per test (function fixture) and runs a compare demand first |
| semantic/test_operation_event_native_journey.py | fixture operation_event_journey -> 3 tests | 2 rows ("We define variance as spread.", "We define mass as inertia.") | after; 3 consumers, same recipe |
| semantic/test_definition_model_native.py | test_current_named_definition_preserves_source_cue_and_refuses_changed_cpu_body_atomically | 1 row "We define variance as spread." | after; patches `retain_data_completion_intent` during later demand |
| semantic/test_witnessed_publication_native.py | test_exact_component_admits_without_whole_applicability | same 1 row literal | STALE: calls `current_pdf_source_factory(...)` without `with`, so `source` is an unentered context manager; `admit_current_target(source…)` reads `.kernel` and cannot work by source reading |
| semantic/test_condition_publication_native.py | test_condition_admits_only_the_exact_supported_roles [2 cases] | 1 row per case | STALE, same missing `with` |
| semantic/test_selected_native_scoring_native.py | test_native_whole_block_questions_keep_exact_custody_and_missing_populations | 1 row "Ada acts." | varies |
| semantic/test_source_search.py | test_cached_native_search_preserves_english_rank_ties_and_exact_cursor | 3 rows, repeated "The runner was running." | varies |
| orchestrate/test_native_math_analysis_demand.py | test_actual_math_request_retains_source_coordinates_and_resumes_without_new_work | 1 formula row "f(x)=x" | varies |
| orchestrate/test_source_demand_native.py | fixture primary_source_case -> 2 tests (gpu): test_two_language_regions_…, test_empty_selected_source_population_… | 2 rows (PASSAGES) | after; 2 consumers, same recipe |
| orchestrate/test_m1_declared_native.py | helper `_case(empty=)` used by 2 tests | empty=True: 1 empty row; empty=False: 1 row SENTENCE (gpu) | varies (1 each) |
All B consumers except the two STALE ones assert on behaviour that starts at the completed capture (they then run
`admit_current_target` + `current_consumer_request(discover=True)`, which discovers the captured members; none
re-runs capture). B count: 24 functions/fixtures-consumers (counting fixtures as their dependent tests: 31 tests
incl. stale), 14 distinct row-recipes among the non-stale ones; the recipes with more than one consumer are
structural_native_journey (2), operation_event_journey (3), primary_source_case (2), and the single-row
"We define variance…" literal (definition_model + the stale witnessed test).

### C. Direct `_current_pdf_source(...)` calls (custom stream and/or tmp dir)
| module | what | class |
|---|---|---|
| semantic/test_contextual_workflow_native.py | module-scope fixture `current_workflow_case`, own `tmp_path_factory.mktemp`, 1 text row, sections groups/0; 3 tests (one parametrized) | after; capture already shared once per module |
| semantic/test_actual_e5_selected_context_native.py | module-scope `actual_e5_native_case`, 1 text row; 1 test (parametrized) | after (shared per module) |
| semantic/test_current_contextual_native.py | module-scope `current_contextual_case`, 2 text rows, sections groups/0,1; 5 tests in this module + 3 in test_current_contextual_witness_native.py (imports the fixture) | after (shared per module) |
| semantic/test_nce02_native_scope.py | `test_current_native_list_host_requires_exact_selected_membership`: custom `list_stream` (list intro + items), sections groups/0 | varies |
| semantic/test_artifact_identity_registered_native.py | `test_current_artifact_numeric_policy_…` [2 cases]: `artifact_stream(rows)` (caption/text rows); typed case additionally runs `companion_source` for a second original (capture inside the test, patched stream) | varies (1 each); typed case partly capture |
| semantic/current_pm2_native_support.py | helper `table_source` (controlled_table_stream, groups/0) used by 4 tests: test_pm2_parser_stage_native (test_unrequested_parser_scope_…, test_cancelled_current_pm2_scope_…) and test_pm2_result_native (test_controlled_cell_mapping_…, test_actual_literal_provider_answer_… (gpu)) | after; 4 consumers, one recipe (table stream) |
| orchestrate/test_pdf_streaming_integration.py | test_real_private_native_pipeline_retains_pages_then_adopts_after_retirement: stream `inspect_reply`, patches `pdf_staging.adopt_pdf_batch`, `run_private_native_pdf_build`, then reads per-run `directory.glob("pdf-source-*")` and `*/attempt-*/manifest.jsonl` | **capture** (the claim is the capture) |

### D. Sibling builders that run a capture through a converter double (not via `_current_pdf_source`)
Each has its own recipe type/commit_clone; none uses the f06 default recipe.
1. tests/semantic/current_pdf_integration_support.py `current_integration_journey` (OriginalSeedRecipe(current_pdf_recipe(tmp_path)), integration-version recipe, patches `PdfWorker.stream` and recognition/integrated hooks; options raw_responses, outcome, before_draft/observation, expect_unresolved_page, reclaim_after_recognition, candidate_pages). 13 call sites in 5 modules: test_current_pdf_integration_native.py (6), test_native_attributed_evidence.py (2), test_pdf_json_publication.py (1), test_pdf_ocr_contracts.py (2 parametrized). All **capture** (interrupt/reclaim, per-call `case.calls`, forged inputs, provider outcomes).
2. tests/semantic/current_artifact_support.py: `companion_source(source, directory, monkeypatch, rows)` runs a second capture inside an existing clone (1 consumer: the typed case above). **capture**. `artifact_recipe` is a target recipe only.
3. tests/semantic/rich_domain_native_support.py: `toy_publication` fixture -> `current_record_policy_journey(recipe=toy_recipe(tmp_path))`; 1 test (test_native_toy_filing_occurrences_…). Also test_rich_domain_preservation_native.py line ~236 (test_native_record_reading_retains_original_decimal_spelling) and test_rich_domain_external_native.py (parametrized by case) call the journey with a patched `controlled_table_stream` (decimal_source_stream), so capture input varies. Classes: toy_publication after/varies; the two direct = varies.
4. tests/evaluate/declared_record_native_support.py `current_record_policy_journey(…, recipe, source_count=4)`: initialises project, registers `source_count` (default 4) blank PDFs, one discovery demand, `execute_data_demand`, asserts `receipt_count == 2*source_count`; stream `controlled_table_stream` (one 2-cell table per original). Consumers (tests): fixture `current_record_policy` (3 tests: test_declared_record_native_journey x2 (one with source_count=1), test_authored_interpretations_native x1); `current_rich_policy` (test_declared_rich_native_journey, 1 test); `rich_publication` (semantic/record_publication_native_support.py; recipe publication_recipe) used by 14 test functions (test_record_publication_native 8, test_record_support_native 2, test_record_alternative_publication_native 2, test_rich_domain_preservation_native 1 parametrized...) all **after**, one recipe (source_count 4, table stream). Others: toy (1), decimal/external (2 functions). Total journey consumers: about 21 functions, of which 14+3+1 share recipes by fixture but each recipe embeds its own `tmp_path` too (policy_recipe/rich_policy_recipe/publication_recipe/toy_recipe take `tmp_path`).
5. tests/evaluate/declared_record_native_support.py also defines `controlled_table_stream` and `policy_recipe`; test_declared_record_native_journey.py line 23 test only prepares the recipe (no capture); test_native_logical_family_contract… takes scenario_seeds directly (not a capture builder).

### E. Reference only (no capture): current_pdf_recipe imported to build target recipes
characterization_native_support, pdf_staging_support, structural_production_native_support,
structural_admission_native_support, current_contextual_support, operation_event_native_support,
current_pm2_native_support (recipe part), test_source_project_native.py, test_source_profiles.py,
test_current_pdf_source_inputs.py, test_data_operation_test_support.py, test_scenario_ports.py (import smoke), and
the sibling recipes in D. Also `admit_current_target` (current_pdf_source_support.py:481) is called by ~12
modules after the capture; it admits a second kernel into the same clone (writes a new release; needs no
capture directory).

## 3. Grouping "after" consumers by capture recipe (counts of test functions, non-stale)
Recipes keyed on identical (stream, sections, math):
- R0 default stream: 12 functions (16 cases) — the only group with a large shared recipe in the `current_pdf_source` family.
- table stream via `table_source` (groups/0): 4 functions.
- structural journey rows (TEXT, TEXT): 2 functions (one fixture).
- operation_event two-literal rows: 3 functions (one fixture).
- primary_source_case two PASSAGES rows: 2 functions (one fixture).
- module-scope shared already: contextual_workflow (3 fns), e5 (1 fn), current_contextual (+witness) (8 fns); one capture per module today.
- single-row "We define variance as spread.": 1 functional consumer (definition_model) + 1 stale.
- Singletons (varies): selected_source (math), native_definition, native_parser, pm2 dipo reclaim, pm2 x+y, pm2 d1, nce02 clipped role, nce02 list host, scoring "Ada acts.", search cached ties, math analysis, m1 empty, m1 sentence, structural replay (2 cases, 2 recipes), artifact identity (2 cases) = about 16 recipes with one consumer.
- Journey (declared_record) family: policy/rich/publication/toy recipes, each with its own tmp_path embedded: rich_publication 14 fns; current_record_policy 3 (2 with source_count default, 1 with 1); current_rich_policy 1; toy 1.
Distinct completed-capture recipes needed to serve all after consumers: about 25 (1 for R0 with 12; plus
table 4, structural 2, event 3, source_demand 2; rest 1-3 each), plus the journey family 4 recipes (14, 3, 1, 1).
Capture consumers: test_pdf_streaming_integration (1), current_integration_journey (13 sites), companion_source
(1), plus the list/artifact cases if the capture claim is wanted.

## 4. What a completed-capture seed would need beyond DB rows
Reads after capture (all tests above) go through DB connections: `serve/source_catalog.read_source_catalog`,
`serve/selected_pdf.acquire_selected_pdf_source`, native_source export, search projection
(`ensure_pdf_search_projection`), `read_demand_result`, `stream_demand_result`. I grepped the serve readers
(selected_pdf, source_catalog, pdf_source_search) for Path/glob use; no hits. Therefore reading a clone needs no
files from the capture directory.
Files that do exist after capture: `<tmp_path>/owned/producer/<…>/attempt-N/manifest.jsonl` and the page/record
Arrow replays (orchestrate/pdf_streaming.py:1008 `directory=directory/"producer"`, spool retained; also
`submitted-<task>-<attempt>.pdf` written at pdf_streaming.py:998). The producer registers spool contributors and
selected replay bytes in the DB (`register_pdf_spool_contributor(manifest_bytes, selected_replays)`,
pdf_streaming.py:511-526), so DB-side custody is self-contained. Resume-from-completed
(`finish_existing_pdf_product`) returns from DB state; spool recovery (`verify_spool_recovery(directory…)`)
is only for interrupted builds. Only test_pdf_streaming_integration reads those directories, and it is a capture test.
Absolute-path dependence recorded in the DB: (a) the retained runtime/release holds the
`pdf-capture/execution-custody` artifact with `directory=tmp_path/"owned"` and `assets.root=tmp_path`
(resolved at pdf_capture.py:resolve_pdf_capture_port 429-455); this only matters if a later demand executes
`source.pdf/capture` again, and such a demand would also need `PdfWorker.stream` patched to the double;
(b) `original_path` text on the registered original document row (value only, bytes are retained in DB; the file
is unlinked before capture); (c) the release id/runtime id/recipe_id derive from (a), so any seed built at one
directory has ids tied to that directory string. Consumers' own consumer kernels use `tmp_path/"consumer"` and
`tmp_path/"recipe"` directories (written after the clone, not part of any seed). A clone consumer that reuses
`source.kernel.preparation.directory` (frozen seed dir) cannot write there (see test_source_discovery note).
Sandbox: `ScenarioSeed.directory` files are `chmod -w` frozen after sealing; seed_files must resolve under that directory.

## 5. How the seed registry would express a second stage
- A recipe is any hashable frozen dataclass of immutable data (str/bool/int/finite float/bytes/tuple/None or
  nested frozen dataclasses); `recipe_id` = sha256 of its JSON form (native_scenario_seeds.py:34-60). Seed key is
  `(recipe, head.name)`; equal recipes share one seed per session. `register_scenario_builder(type, builder)`
  (tests/scenario_recipes.py) is exact-type, one builder per type, duplicate registration raises, subclasses do
  not inherit.
- Builder signature: `builder(recipe, admin, writer, directory, *, purpose_engine)`; `admin` is an Engine on the
  new database cloned from the semantic head template, `writer` the write-purpose engine, `directory` a fresh
  `mktemp("seed-<RecipeType>")` path, `purpose_engine(name)` makes other purpose engines (disposed after build).
- It must return a frozen dataclass stage with `seed_files: tuple[Path,...]` (existing, under `directory`) and
  `validate_clone(admin)`; optional `seed_origin` string mapping.
- Sealing (`ScenarioSeeds.seed`, lines 224-275): refuses a stage that is not a frozen dataclass; refuses seed
  files outside/missing; runs `validate_clone`; refuses any `ops.task` in status claimed or running; checks the
  policy unchanged; disposes the admin engine; seals the database (no sessions: `validate` waits for backend
  exit, no persistent connections); chmod-freezes every file under `directory`, refuses symlinks. Clones
  (`commit_clone`, `rollback_family`) copy the database; a clone must have a different OID, runs
  `validate_clone` again, and gets fresh purpose engines. `rollback_family` also uses the seed.
- Existing precedent for a layered stage: `OriginalSeedRecipe(target: KernelRecipe)` ->
  `OriginalSeedStage(original, kernel: KernelSeedStage)` (tests/semantic/data_operation_original_support.py):
  its builder admits the kernel, initialises the project and registers one original with an `independent-original.pdf`
  in the seed directory, and its `seed_files` returns only the kernel's files because reads use retained DB bytes.
  The kernel stage is `KernelSeedStage(preparation, identities, recipe)` with `seed_files` = every file under
  `preparation.directory` (the captured python sources) and `validate_clone` checking runtime binding and admitted
  operations. A completed-capture stage would be a new recipe type wrapping the capture inputs (rows, sections,
  math_context, and the stream double identity), whose builder would have to run the converter patch itself (the
  builder has no `monkeypatch`; it would use `unittest.mock`/its own context), its `purpose_engine("admit")`
  and `execute_data_demand`, and whose `validate_clone` could check the selected publication exists.
- Things a seed may not contain: unfinished claimed/running tasks, live backend sessions, symlinks, files outside
  its directory, a non-frozen stage value, and values that are not immutable data in the recipe (callables such
  as the stream double cannot be part of the recipe; they would need a data selector such as a named stream
  variant plus a registry of doubles).
