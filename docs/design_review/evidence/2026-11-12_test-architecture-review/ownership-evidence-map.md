# Scenario ownership, refusal-evidence and evidence-class map

Baseline `784d86f118c5dcd061e22901abaf6032c3ffe6b5` (clean tree). Read-only; nothing run, collected or
timed. Paths are relative to `/home/paul/corpus-structure`. `PT/` abbreviates
`python/corpus-structure/tests/`. Counts come from an AST pass over every `*.py` under `PT/` and `tests/`
(import statements including function-local ones; `from X import n`, `import X`; targets resolved to
files in the two test trees) and from `grep`/AST searches whose scope is stated per item. Scratch scripts and
raw output are in `scratchpad/work/` (`imp.py`, `q*.py`, `raises.py`, `test_targets.txt`, `priv.txt`).

Terminology note: the audit's "root `tests/pdf_region_support.py`" is `PT/pdf_region_support.py`
(package-tests root). Repository-root `tests/` holds only `conftest.py`, 19 `test_*.py`, `tests/scripts/`
(10 files) and `tests/evidence/`.

---

## 1. Support owners today

### 1a. Dedicated support modules (non-`test_*`), importers counted from the AST pass

"T" = importing `test_*` modules; "S" = importing support/conftest modules. None of these imports from a
`test_*` module (checked for every module in the table).

| Module (under `PT/`) | Owns | Importers |
|---|---|---|
| `semantic/native_record_fixtures.py` (1138 lines) | `publish_native_record_fixture` (`:109`), `prepare_record_source` (`:208`), `build_record_source` (`:292`), record/candidate builders (`candidate :649`, `identities :708`, `unit :714`, `complete :731`, `bypass :746`), fixtures `private_source_options/private_preparation/private_source` (`:781-819`), `contribution_drafts :822`, `curated_case :923`, `contextual_result :984` | T 41, S 3 (`pdf_acceptance_support`, `reference_scenarios`, `witnessed_scenario_support`) |
| `semantic/operation_scenario_support.py` | `prepare_operation_scenario` (synthetic releases) | T 17, S 2 (`pdf_integration_support`, `pdf_staging_support`) |
| `semantic/pdf_staging_support.py` | `_private_build_factory :28`, fixtures `create_private_build/private_build`, `native_batch` | T 17 |
| `pdf_acceptance_support.py` (594) | controlled retained PDF: `no_inference_child`, `seed_retained_integrated_product`, `write_controlled_pdf`, `publish_controlled_pdf_views`, `native_evidence_sources` | T 12, S 3 (`agent_/domain_/reference_scenarios`) |
| `semantic/agent_scenarios.py` | `build_resubmission_case`, `lease_and_read` | T 12, S 2 (`reference_scenarios`, `serving_scenarios`) |
| `semantic/domain_scenarios.py` (811) | `DomainFixtureConfig`, `build_domain_case`, `fixture_model`, `seed`, `batch` | T 13 |
| `semantic/primary_native_support.py` | `stage_primary_layers`, `publish_primary_layers`, `bind_primary_agent_run` | T 10, S 2 |
| `methods/primary_reading_fixture.py` | `prepared()` (lru_cache release), `primary_product` | T 11, S 1 (`navigation_fixture`) |
| `semantic/method_dimensions_support.py` | `fixture_execution_inputs`, `prepare_fixture_pack` | T 5, S 6 (all the scenario builders) |
| `semantic/inventory_reading.py` | `inventory_*` readers | T 9 |
| `methods/navigation_fixture.py` | `primary_navigation`, `view_from_frame` | T 9 |
| `semantic/reference_scenarios.py` (442) | `publish_reference_case`, `private_source_options` override (`:197`), `reference_source`, `expected_reading`, `create_case`, `native_pass` | T 8 |
| `semantic/witnessed_scenario_support.py` (772) | `completed_metadata`, `completed_component_case`, `completed_relationship_case`, `authored_component_admission` | T 8 |
| `semantic/pdf_integration_support.py` (575) | fixtures `pdf13_context/native_source/independent_integrated/pdf13_db`, `make_native_source`, `publish`, `mutate_selected`; also holds private `_publish_record_document/_values` | T 7 |
| `semantic/primary_formal_fixture.py` | `release`, `formal_layers` | T 6, S 1 |
| `semantic/archive_faults.py` | `administrative_archive_edit` | T 6 |
| `semantic/structural_release_fixture.py` | `released_report` | T 4 |
| `schema/lint_support.py` | pinned LinkML CLI contract (`report_errors`, `lint_errors`) | T 3 |
| `archived_source.py` | retained historical archive inputs | T 1, S 2 (`ingest/conftest`, `llm/conftest`) |
| `math_support.py` (428) | math page fixtures/`_run_pages`, `MathEnv` | T 2, S 1 (`math/conftest`) |
| `native_math_primary.py` | `native_view`, `primary_layers`, `pure_source_release` | T 2 |
| `model_change_support.py` | `model_checkout` fixture | T 2 |
| `pdf_process_support.py` / `pdf_region_support.py` / `pdf_validation_support.py` | spawn targets / asymmetric PDF / validation child targets | T 2 / T 1 (+`pdf_staging_support`) / T 1 |
| `semantic/serving_scenarios.py` | `build_completed_serving_case`, `ServingScenarioSeed`, fixtures `serving_scenario_seed/serving_read_scenario`, `_validate_serving_seed` | T 2 |
| `math_worker_cases.py`, `math_worker_transport.py`, `methods/gliner_worker_cases.py` | subprocess targets | T 1 / S 1 (`math_support`) / T 1 |
| `core/translate.py` | `candidate_set` (T2 translation) | loaded by path via `importlib.util` at `PT/core/test_references.py:201-209`; not imported |
| `fixtures/support.py` | `S0Fixture`, readers `load_s0/load_segments/load_target` | **no importer found** (searched `load_s0`, `load_target`, `load_segments`, `fixtures.support`, `fixtures import support` over the repo's Python) |
| `semantic/snapshot_restore.py` | `restore_finished_metadata` | **no importer found** (searched `snapshot_restore`, `restore_finished_metadata` over repo Python; only the definition) |

Fixtures defined in support modules, not conftests, are activated by being imported into a test module's
namespace (the `from … import name as name` idiom, e.g. `PT/semantic/test_native_attributed_evidence.py:33-36`).

### 1b. Conftests

| File | Owns |
|---|---|
| `tests/conftest.py` (16) | `pytest_configure`: `db` marker, scratch root `build/tmp/pytest` |
| `PT/conftest.py` (321) | hypothesis profiles; markers `db`,`gpu`,`corpus` (`:101-103`); `pytest_collection_modifyitems` adds `db` to items whose fixtures intersect `DB_FIXTURES` (`:71-87,129-130`) and skips `corpus` items with `qualification_prerequisite=corpus` (`:131-138`); `Cli`/`cli`; `db_support` (a fixture exposing `PgAdmin`, `TEMPLATE_RETENTION`, … because "importlib import mode leaves this module unimportable", `:177-180`); session `native_settings`, `native_server`, `semantic_head_template`; autouse `refuse_unbound_application_target`; `db_engine`/`db` (session, rolled back), `committing_db`, `semantic_absent_database`, `observed_store_checkouts` |
| `PT/semantic/conftest.py` (106) | function-scoped clones: `semantic_db_engine`, `semantic_bare_engine`, `semantic_database_at`, principal engines (`writer/reader/evaluator/admitter`) |
| `PT/acceptance/conftest.py` (4 lines) | re-imports `semantic_db_engine`, `semantic_writer_engine` from `..semantic.conftest` (`:3-4`) |
| `PT/ingest/conftest.py`, `llm/conftest.py`, `math/conftest.py`, `orchestrate/conftest.py` | per-area retained inputs / `ingest`, `env`, `orch` fixtures |

`semantic.conftest` is also imported as a module by 9 modules (24 absolute + 3 relative import statements by
the dual-name pass in §10): the `semantic_*_engine` fixtures are re-exported by name into `evaluate/*`,
`acceptance/conftest.py`, `semantic/reference_scenarios.py:53-62`, `orchestrate/test_pdf_*_native.py:8`.

### 1c. `test_*` modules imported by other modules (reverse view)

Totals: 255 import statements target 75 distinct `test_*` modules, from 148 distinct importing modules
(the audit says 266 `from …test_… import` lines; the difference is method of counting, not investigated).
Direction of the 255: semantic→semantic 139, methods→methods 51, semantic→methods 21, methods→semantic 20,
evaluate→evaluate 8, ingest→ingest 5, methods→ingest 4, semantic→ingest 3, evaluate→semantic 2,
semantic→evaluate 1, db→db 1.

Ranked by number of distinct importing modules (full list: `scratchpad/work/test_targets.txt`; top 30):

| # | Owner `test_*` module (`PT/`) | What is imported (names) |
|---|---|---|
| 14 | `methods/test_m1_source_preparation.py` | `source`, `native_table_source`, `table_cell`, `dense_table_source` (builders) |
| 12 | `semantic/test_record_contracts.py` | `PIN`, `bind`, `finish`, `release_inputs`, `table_record`, `formula_record`, `measurement_record`, `record_from_fields` |
| 11 | `methods/test_scoped_relations.py` | `complete_native_fields`, `discover_relations`, `original_inputs`, `source` |
| 9 | `methods/test_m1_producer.py` | `view`, `release`, `ROOT`, `ControlledDecoder`, `owned_reader`, `detail_object(s)` |
| 8 | `semantic/test_analytics.py` | `prepared_inputs`, `empty_packet` |
| 8 | `ingest/test_annotations.py` | `ControlledPipeline`, `item`, `controlled`, `primary_product` |
| 8 | `methods/test_record_assembly.py` | `context`, `release`, `report`, `span`, `fields`, `source` |
| 7 | `semantic/test_formal_evidence.py` | `prepared`, `operation`, `source` |
| 6 | `semantic/test_pdf_publication.py` | `stage_complete_native` |
| 6 | `semantic/test_releases.py` | `stage`, `source_bundle` |
| 6 | `semantic/test_proposals.py` | `prepared`, `batch`, `frame` |
| 5 | `semantic/test_execution_release.py` | **`_bundle`, `_project`, `_stage_authored_sql`** (private) |
| 4 | `semantic/test_identity_exclusions.py`; `semantic/test_typed_structural_composition.py`; `semantic/test_structural_products.py`; `semantic/test_pdf_ocr_contracts.py`; `methods/test_pm2_source.py` | `exclusion_result`; `threshold_inputs`/`revision_inputs`; `inputs`; `inventory`; `identity_map`/`source_context` |
| 3 | `semantic/test_companion_export_native.py` (`read_settings`); `test_review_bundle.py` (`synthetic_source_projection`, `source_row`); `test_selected_source_native.py` (`publish_selected`, `deploy_selected`); `test_pdf_native_consumer_journey.py` (`native_build_resubmission_case`); `methods/test_native_evidence.py` (`builder_for`, `metadata`, `native_source`, `prepared`); `semantic/test_model_characterization.py` (`builder`, `gliner_profile`, …) | |
| 1–2 | 45 further owners | see raw file |

Directory shape: only `methods/` and `semantic/` have `__init__.py` (`find … -name __init__.py`); see §10.

### 1d. Private-name (`_x`) imports across test modules (complete; 14 statements, resolved to test-tree modules)

| Importer (`PT/`) | Owner | Names |
|---|---|---|
| `math/test_workers.py:9` | `math_support` | `_run_pages` |
| `methods/test_definition_applicability.py:825,969` | `methods.test_predicate_frames` | `_PREFIX` |
| `methods/test_witnessed_source_links.py:26` | `methods.test_inline_formula_occurrences` | `_FROZEN_TEXT` |
| `semantic/test_contextual_query_replay.py:31` | `semantic.test_section_heading_replay` | `_source` |
| `semantic/test_execution_projection.py:149`, `test_native_closure.py:154`, `test_pdf_record_native.py:489`, `test_runtime_identity.py:24` | `semantic.test_execution_release` | `_bundle` |
| `semantic/test_sql_admission_phases.py:16` | `semantic.test_execution_release` | `_project`, `_stage_authored_sql` |
| `semantic/test_operation_reporting_native.py:140` | `semantic.test_inference` | `_inference_publication_state` |
| `semantic/test_pdf_integrated.py:31` | `semantic.pdf_integration_support` | `_publish_record_document`, `_publish_record_values` |
| `semantic/test_prepared_graph_candidates.py:125` | `semantic.test_ontology` | `_bound_projection` |
| `semantic/test_serving_scenario_lifecycle.py:14` | `semantic.serving_scenarios` | `_validate_serving_seed` |

(Also seen, production not test: `PT/methods/test_primary_reading_consumers.py:11` imports private
`_availability` from `corpus_structure.methods.native_evidence`.)

A verification-disabling fixture also travels by import: `synthetic_source_projection`
(`PT/semantic/test_review_bundle.py:201-208`, monkeypatches `review_bundle._verify_source_projections`
to `lambda *_: set()`), re-exported by `test_section_heading_replay.py:36` (from `test_review_bundle`) and
re-re-exported to `test_contextual_query_replay.py:32`; imported also by `test_dossier_contributions.py:26`.

---

## 2. The `private_source` family contract

### 2a. Builders and their options (`PT/semantic/native_record_fixtures.py`)

`prepare_record_source(*, bundle_transform=None, dependencies_transform=None, additional_methods=())`
(`:208-277`) is pure: builds the schema bundle (core.yaml + a "private-records" schema), applies
`bundle_transform`, derives `dependencies` via `domain_rule_inputs`, `analytical_inputs`,
`composed_dependencies(… fixture_execution_inputs("private.source","private.records",*additional_methods))`,
applies `dependencies_transform`, calls `prepare_release` with `PreparationProfile("semantic-2")`. Returns
`RecordPreparation(bundle, dependencies, profile, prepared)` (`:281`). **These three options are the only
ones that can change the prepared release.**

`build_record_source(admin, writer, directory, preparation, *, include_blank_cell=False,
record_method_spec=None, record_configuration_hash="private-config", sibling_captions=(),
sibling_references=(), sibling_originals=(), monkeypatch=None, project_id="private-records",
existing_project=False, source_tag="")` (`:292-646`). Effects:

| Option | Effect (lines) | Changes prepared release? |
|---|---|---|
| `include_blank_cell` | table has a third empty cell (`:324,333`) | no; source content |
| `sibling_captions` / `sibling_references` | texts of the "Other source" section items (`:338-352`); captions become `DocItemLabel.CAPTION` | no; source content |
| `sibling_originals` | sibling items are formulas with `orig` (`:341-347,355-397`); builds an authored section-text policy, replaces the `execution/implementation/pdf/section-text-recipe.json` dependency artifact (`:375-383`), **monkeypatches `contracts.analysis_implementation_inputs`** (`:386-396`, the one production monkeypatch), and **re-runs `prepare_release`** (`:397`) | **yes**; the stored release is the second preparation (`persist_release … prepared` at `:399`), so `preparation.prepared` is not what is committed |
| `record_method_spec` / `record_configuration_hash` | registered record method/config for the leased task (`:594-605`); hash also used in `complete`/`bypass` as literal `"private-config"` (`:739,752`) | no |
| `project_id`, `existing_project`, `source_tag` | create/reuse project+realization (`:312,398-416`); `source_tag`/`project_id` change original bytes (`:314-317`) | no; used by direct callers only |
| `monkeypatch` | required only for `sibling_originals` (`:358` assert) | – |

Everything else is fixed: source/original bytes, doc structure, run, tasks, one leased `record` task, two
views (`private-view` over the table, `other-view` over the sibling). Returned `SimpleNamespace`
(`:629-646`): `project_id, prepared, preparation_inputs, writer, run, task, held, view, other_view,
source_task, view_row, task_row, method, record_configuration_hash, table, sibling`.

The fixture `private_source` (`:791-819`) merges `private_source_options | getattr(request,"param",{})` and
forwards **only** `record_method`, `bundle_transform`, `dependencies_transform`, `additional_methods`,
`include_blank_cell`, `record_configuration_hash`, `sibling_captions`, `sibling_references`,
`sibling_originals`; `project_id`/`existing_project`/`source_tag` are not reachable through the fixture.

### 2b. Direct (non-fixture) callers
`PT/semantic/test_pm2_result_native.py:91-101` (calls `prepare_record_source()`, appends a question
artifact to `dependencies`, calls `prepare_release` itself, then `build_record_source(… monkeypatch=…)`);
`PT/semantic/test_artifact_identity_registered_native.py:125-135` calls `build_record_source` a second time
with `case` (the first case, duck-typed as `preparation`: needs `.preparation_inputs` and `.prepared`),
`project_id=case.project_id, existing_project=True, source_tag=…, sibling_captions=…`.

### 2c. `private_source_options` overrides (12 definitions incl. the default; all `@pytest.fixture` at module scope)

| Definition | Sets | Release effect |
|---|---|---|
| `native_record_fixtures.py:782` | `{}` | – (default) |
| `reference_scenarios.py:197` | `bundle_transform=reference_inputs` | yes |
| `test_artifact_identity_registered_native.py:58` | `bundle_transform=characterization_inputs∘reference_inputs` | yes |
| `test_condition_publication_native.py:77` | `bundle_transform=characterization_inputs` | yes |
| `test_local_semantic_admission_native.py:48` | `bundle_transform=reference_inputs` | yes |
| `test_protected_comparison_gap_native.py:70` | `bundle_transform=characterization_inputs` | yes |
| `test_record_reading_closure_native.py:28` | `bundle_transform=source_reading_inputs` | yes |
| `test_table_correspondence_native.py:40` | `bundle_transform=characterization_inputs` | yes |
| `test_interpretations_native.py:22` | `bundle_transform` (adds `domains/statistics/terminology.yaml` module, root imports it) **and** `dependencies_transform` (`acquire_terminology` artifacts/ontology) | yes |
| `evaluate/test_record_policy_authority_native.py:134` | `bundle_transform` (adds statistics semantic.yaml sans `TableRecordFields`, then `source_reading_inputs`, `reference_inputs`) **and** `record_method` (`extract.m1_candidates` v3, tier `encoder`) | yes (+method) |
| `test_pm2_parser_stage_native.py:38` | `sibling_references=parser_samples` (depends on fixture `parser_samples`) | no |
| `test_structural_native_replay.py:58` | `sibling_references` chosen by inspecting `request.node.callspec.params` (`left`/`right`, `connector`, else `_COMPARISON_LITERALS`) | no |

Re-export wiring (consumers import the options fixture by name): default from `native_record_fixtures`
imported by ~20 modules (e.g. `test_local_admission_native.py:21`, `test_contributions_native.py:19`,
`evaluate/test_record_policy_native.py:9`); the `reference_scenarios` variant imported by
`test_review_cli_native.py:28` and `evaluate/{test_operation_fitting_native:15,
test_characterization_assessment_native:15, test_operation_assessment_native:15}`.
`private_preparation` (`:786`, `prepare_record_source()` with defaults) has one consumer:
`test_private_records.py:47,266`. 35 modules reference `private_source`.

### 2d. Indirect parametrization / `callspec` (AST search for `parametrize` whose first argument names `private_source`)

24 parametrize calls. Variant dicts: `{"additional_methods": ("private.contextual",)}` ×16
(`test_contextual_enrichment_native.py` 8, `test_local_semantic_admission_native.py` 8; release-changing);
`{"include_blank_cell": True}` (`test_contributions_native.py:346`); `{"record_configuration_hash":
_CELL_CONFIGURATION}` (`evaluate/test_operation_assessment_native.py:443`);
`dict(bundle_transform=characterization_references, additional_methods=("native-binding",))`
(`evaluate/test_characterization_assessment_native.py:77`; release-changing); `{}` vs
`{"sibling_captions": EDITIONS, "sibling_references": (CROSS_WORK_REFERENCE,)}` with ids
(`test_artifact_identity_registered_native.py`); four `sibling_references`/`sibling_originals` variants in
`test_pm2_result_native.py:284,652`, `test_protected_comparison_gap_native.py:150`, and a
`(private_source, qualifier, host)` tuple parametrization with `sibling_references`
(`test_condition_publication_native.py`); `judged_source` parametrized `{"partition": …}`
(`test_local_semantic_admission_native.py:475`). The `request.param` merge is the only read of param
(`native_record_fixtures.py:800`); the `callspec` read is the single site `test_structural_native_replay.py:59`.

**Release-changing variants** (so the committed scenario differs): all `bundle_transform` /
`dependencies_transform` / `additional_methods` values above, plus `sibling_originals`. **Later-behaviour
only**: `include_blank_cell`, `sibling_captions/references`, `record_configuration_hash`, `record_method`
(not checked whether a method name absent from the release's execution inputs is refused by
`record_method(..., prepared=prepared)`; open).

Each `private_source` instantiation starts from the function-scoped `semantic_db_engine` clone (§1b);
`prepare_release` is called once per instantiation (twice with `sibling_originals`); the
`production cache` noted by the audit (DTA-029) was not examined here.

---

## 3. The big builders

### 3a. `build_domain_case` (`PT/semantic/domain_scenarios.py:65-95`), returns `(prepared, run, cut)`

Keywords (25): `rules`(bytes), `graph`, `duplicate`, `formulas`(seq), `known`, `local_known`,
`input_noise`, `nary`, `broken`, `claim_chain`, `cycle`, `condition`(dict), `report_count`(int),
`global_person_identity`, `authored_alternative`, `integer_alias`, `math`(dict), `second_math`(dict),
`statement_packets`(str, `"different"` special), `attribute_assertions`, `incomplete_key`,
`isolated_entity`, `membership_subtype`, `unselected_report`, `characterization`. Always: builds the schema,
persists the release, creates project `"p"`, publishes controlled PDF views, creates run/tasks,
completes the proposal, `seal_cut(…, final=True)` (`:560-570`). Switch branches: schema `:105-141,187`,
data `:200,224,337-400,419-455`, packet variants `:476-526`, foreign run `:569-640`.

Call sites (AST, 24 total, grouped by keyword set):

| Option set | Sites | Where |
|---|---|---|
| none | 11 | `test_audit_closure_native.py` (83,107,187,…), `test_domain_operations.py:22,…` |
| `formulas` | 2 | `test_audit_closure_native.py:241`, `test_domain_operations.py:316` |
| `formulas`+`math` | 2 | `test_domain_operations.py:657,706` |
| `rules`; `graph`; `duplicate`+`rules`; `known`+`local_known`; `nary`; `broken`+`nary`; `claim_chain`; `cycle`; `condition`+`formulas`; `authored_alternative`+`formulas`; `integer_alias`+`rules`; `input_noise`+`known`; `graph`+`isolated_entity` | 1 each | `test_domain_operations.py:77,105,276,374,427,457,483,501,524,590,626,757,816` |
| `formulas`+`global_person_identity`+`report_count` | 1 | `test_domain_operations.py:551` |
| + `math`+`second_math` | 1 | `test_domain_operations.py:730` |
| `graph`+`membership_subtype`+`unselected_report` | 1 | `test_domain_operations.py:880` |
| `attribute_assertions`; `incomplete_key` | 1 each | `test_audit_closure_native.py:29,139` |
| `duplicate`; `known` | 1 each | `test_occurrence_context.py:47`; `test_evaluation_boundaries.py:223` |
| `characterization`+`global_person_identity`+`graph`+`membership_subtype` | 1 | `test_imported_declaration_membership.py:47` |
| `global_person_identity`+`report_count`+`statement_packets` | 1 | `test_statement_anchors.py:59` |

Never used by any call site: `second_math` alone, `unselected_report` without `graph`+`membership_subtype`.
Return unpacking (grep of assignment patterns): `(_prepared, _run, cut)` 15, `(prepared, _run, cut)` 6,
`(_, _, cut)` 5, `(_prepared, run, cut)` 4, `(prepared, run, cut)` 2, `(prepared, _, cut)` 2,
`(_, run, _)` 1 - i.e. `cut` is read by nearly every site; `run` by 7; `prepared` by 10. 13 importing
modules (§1a); 4 modules actually call it.

### 3b. `build_resubmission_case` (`PT/semantic/agent_scenarios.py:36-174`), returns `(prepared, run, task, locator)`

Keywords (7): `composed`, `identity_keyed`, `global_names`, `domain`, `evaluation_policy`, `query_inputs`,
`model` (**`model` passed by no call site**; used for the agent config). Always: schema, release via
`proposal_inputs`, `analytical_inputs`, `composed_dependencies(fixture_execution_inputs("pdf.controlled-source",
"coverage.witness"))`, `characterization_inputs` (`:75-94`), persists release, project `"resubmit"`,
realization `"input"`, one controlled PDF paragraph `"Alice is here."`, run, document, published view,
`bind_primary_agent_run`, `queue_agent` (`:96-174`).

| Option set | Sites | Where |
|---|---|---|
| `composed` | 14 | `test_read_contracts.py:129`, `test_cli_failures.py:235`, `test_runtime_entrypoints.py:160,478,…` |
| none | 7 | `test_agent_resubmission.py:23`, `test_runtime_entrypoints.py:59,266,329,…` |
| `composed`+`global_names`+`identity_keyed` | 1 | `test_identity_exclusions.py:28` |
| `composed`+`domain`+`query_inputs` | 1 | `serving_scenarios.py:46` |
| `composed`+`evaluation_policy` | 1 | `test_reference_evaluation.py:449` |

Reads from the result: `(prepared, run, task, locator)` 6; `(_prepared, run, task, locator)` 4;
`(_, run, _, _)` 3; `(prepared, run, task, _)` 2; `(prepared, _, _, _)` 2; `(prepared, _, task, _)` 1;
(and `prepared, run_id, task_id, _locator` once). The native variant
`native_build_resubmission_case` lives in a *test* module, `PT/semantic/test_pdf_native_consumer_journey.py`
(5 calls with no keyword, 1 with `ancestor`; returns 5-tuples `(…, view_id|view|child, key)`), imported by
`test_source_search.py:10`, `test_mcp_source_transport.py:256`, `test_native_exports.py:10`.

---

## 4. Primary-layer assembly copies (DTA-029)

Reference: `PT/methods/primary_reading_fixture.py:31-127` `primary_product(text, product, profile, *,
configuration="independent-native-columns", rules=())`: builds `view` (SimpleNamespace), `scope` with
profile `"test-source-readings"`, `operation` (runtime `"test-runtime"`, model `"test-native"`, context
`"exact-authored-columns"`); `NativeEvidenceBuilder(profile="spacy_only", families=SPACY_FAMILIES)`;
`native.spacy(view, product, "spacy")`; `native_run("spacy","spacy_only",configuration, model/version/
runtime_version from the product, components=asdict(product.components))`; then **overwrites**
`run["configuration_digest"] = product.pipeline_config_digest`; availability from `SPACY_COLUMNS`;
`native.finish(prepared())`; `native_layer.reference(101)`; then a `ConstructionLayer`+`populate`
(+`populate_named` if `rules`); reading ref 102; returns `PrimaryAnnotationProduct`.
Release: module `prepared()` `lru_cache(maxsize=1)` (`:23-28`).

| Copy (`PT/…`) | Differences from the reference |
|---|---|
| `methods/navigation_fixture.py:18-97` | native stage identical in shape (placeholder `"fixture"` configuration; **overwrites** `configuration_digest`; availability from `SPACY_COLUMNS`); loops `for product in annotations` calling `native.spacy` per product but builds one run from `annotations[0]`; reads view from source; constructs `FAMILY`/`PRIMARY_RULE_FAMILY` navigation layer + optional formal layer; `task_start` parameter (201/202/203) instead of 101/102; reuses `prepared()` from the shared fixture. Consumer claim is navigation, so the construction half necessarily differs |
| `native_math_primary.py:45-145` | computes `nlp`, annotates itself (`annotate`), `operation` carries a digest of binders/rules/macros config, `native_run(…, nlp.config.to_str(), …)`; overwrites `configuration_digest`; **empty-text branch** records every `SPACY_FAMILIES` family without a spaCy run (`:124-125`); adds `build_formal_layer` and `populate_math_scope`; refs 100/101/102; takes `prepared` as argument |
| `methods/test_math_scope_primary.py:~60-135` | placeholder `"cfg"`; `native_run(…, nlp.config.to_str(), …)`; **does not** overwrite `configuration_digest`; availability from `SPACY_COLUMNS`; ref 101; math `FAMILY` layer only; optional `recognized` formal-view rewrite |
| `methods/test_construction_named.py:~60-140` | placeholder `"cfg"`; real `controlled.config.to_str()`; **does not** overwrite digest; availability from `SPACY_COLUMNS`; ref 101; named-rule layer with authored `AnnotationRule`s |
| `methods/test_m1_producer.py:140-250` | statistics-domain registry config; one run from `products[0]` after looping `native.spacy` over all products; digest not overwritten; ref 101; `populate_named` with `PreparedAnnotationRules(nlp.vocab, …)`; then the producer under test is run and the `reader` stub is returned |
| `methods/test_primary_reading_consumers.py:116-175` | hard-codes model `en_core_web_sm`/`3.8.0`/`3.8.18`, no `components`; availability via private production helper `_availability(native,"spacy")` (`:11,152`); optional heading product with rewritten POS/tags; installs a monkeypatch that fails if `pipeline` reruns; ref 100/101 |
| `methods/test_definition_declaration_primary.py:150-260` | **not the spaCy path**: `profile="full_native"`, `HANLP_FAMILIES`, `native.annotation`/`native.hanlp_sentence` over authored token/dependency/SRL rows, `native_run("hanlp","full_native","{}", model="authored-native-columns",…)`, authored primary terms; refs 101/102 |
| `methods/test_contextual_characterization.py:46-57` | only `native_run(provider,"fixture","{}",…)` rows for `maverick`/`dipo` with `configuration_codec`; no spaCy builder, no availability |
| `methods/test_native_evidence.py` | builder is the subject under test (excluded from the finding) |

Observed differences by axis: (i) `configuration_digest` overwritten: reference, navigation, `native_math_primary`;
not overwritten: `test_math_scope_primary`, `test_construction_named`, `test_m1_producer` (the audit names
only the construction-named copy). (ii) Operation/profile/configuration strings differ per file.
(iii) Source of `prepared`: shared `lru_cache` `prepared()` (reference, navigation), a fixture argument
(`native_math_primary`, `test_primary_reading_consumers`, `test_construction_named`), a local `prepared()`
(`test_math_scope_primary`, `test_definition_declaration_primary`), or a stub reader
(`test_m1_producer`). Whether each difference is required by the consumer's claim: construction half
(navigation, math scope, named rules, authored HanLP, M1 producer) is plausibly claim-specific from source;
the native half differences in (i)-(ii) are not tied to any claim visible in the source (e.g. the
test files give no reason for not overwriting the digest); not established beyond this.

---

## 5. Refusal-evidence practice

**No shared refusal-assertion helper exists.** Searches: `grep -rn "def .*refus\|def raises\|def assert_.*(refus|reject)\|def expect_"`
over `PT/`, `tests/`, `scripts/` returns only test functions and local `refuse()` stubs (CLI), nothing
reusable; `sqlstate`, `message_primary`, `constraint_name`, `pgcode` are all spelled inline.

### 5a. Idioms in use (counts: grep over `PT/`; `sqlstate` 119 lines in 51 files; `message_primary` 19; `constraint_name` 16 incl. non-test stubs; `pgcode` 0; `.diag` 32)

1. **Class only.** `with pytest.raises(DBAPIError), conn.begin_nested():` (model: `semantic/test_publication.py:229`,
   `semantic/test_native_closure.py:74`). Plain; may be followed by post-state assertions.
2. **Class + regex on text.** `pytest.raises(DBAPIError, match="immutable semantic content")`
   (`semantic/test_native_closure.py:83`; `match="failed analysis"` `test_characterization_native.py:~385`).
   220 `DBAPIError`+`match` sites by AST count.
3. **SQLSTATE only.** `assert getattr(refusal.value.orig,"sqlstate",None) == "42501"`
   (`evaluate/test_operation_fitting_native.py:262-263`; per denied statement `semantic/test_native_fixtures.py:192-199`;
   all eight runtime-binding mutations `semantic/test_runtime_bindings_native.py:~146-148`, `"23514"`).
4. **(sqlstate, message_primary) tuple.** `assert (native.orig.sqlstate, native.orig.diag.message_primary) == ("23514", msg)`
   (`semantic/test_private_records.py:157,196,421`; `semantic/test_pdf_publication.py:163-166`
   `("P0004","private PDF build is not owned/open")`; `test_publication.py:142,165,203`).
5. **(sqlstate, constraint_name) tuple** for FK/unique refusals
   (`semantic/test_local_admission_native.py:174`; `db/test_native_diagnostic_facts.py`).
6. **Per-case expected pair from a dict keyed by the corruption label**, then one assertion over
   `(sqlstate, constraint_name|message_primary)`: `semantic/test_local_semantic_admission_native.py:597-621`
   and `test_local_admission_native.py:163-188` (precedent for per-case reasons in a mutation family).
7. **Positive control in a savepoint, then the refusal.** `with conn.begin_nested() as positive: bypass(case, conn, (candidate(case),)); assert …; positive.rollback()`
   then `pytest.raises((DBAPIError, InvariantViolation)) as caught` with the unwrap
   `native = caught.value.__cause__ if isinstance(caught.value, InvariantViolation) else caught.value`
   (`semantic/test_private_records.py:131-176`, repeated at `:196`, `:421`;
   clean-baseline `with conn.begin_nested() as accepted: publish(clean) … accepted.rollback()` in
   `test_local_semantic_admission_native.py:575-585`, `test_local_admission_native.py:~150-165`).
8. **Atomicity-after-refusal** (state probes after the `raises`): `test_contextual_enrichment_native.py:155-157`
   (`kb.contextual_vector`, `kb.source_contribution` empty), `test_private_records.py:178-195`.
9. **Python-side:** `pytest.raises(ValueError, match=…)` 683 sites, `ValidationError` with `match` 72
   (AST, `PT/`+`tests/`); pydantic refusals in `core/test_shapes.py`.
10. **CLI:** `exit_code == 2` plus `any(word in result.output …)` (`methods/test_m1_cli.py:34-35`),
    or `exit_code != 0` (`test_source_cli.py:357`), versus `error["code"]=="SemanticRefusal"` plus exact
    message (`test_cli.py:374-381`).

### 5b. Sites with no inspectable reason (AST over `with pytest.raises(...)` items in `PT/` and `tests/`)

Definition: `pytest.raises(X)` with no `match=` and no `as` binding (so nothing can be asserted on the
exception object). Totals: `DBAPIError` bare 83 (28 modules), with `match` 220, with `as` 79 (the `as`
group is not classified further: `as caught` then `.orig.sqlstate` is common, but not every such site
asserts); `ValueError` bare 85 (49 modules); `ValidationError` bare 102 (46 modules). Subclass names
(`IntegrityError`, etc.) are not counted (6 grep hits). "In loop/param" = enclosing function has a
`parametrize` decorator or the call sits in a `for`/`while`; **a `parametrize` over a fixture is counted
too, so this overstates mutation families** (see note under the table).

`pytest.raises(DBAPIError)` bare, by module (number; of which in loop/param):

| Module (`PT/`) | Bare | In loop/param |
|---|---|---|
| `semantic/test_characterization_native.py` | 21 | 21 (parametrize is over `private_build`; sites are single refusals, not mutation labels) |
| `semantic/test_publication.py` | 10 | 4 |
| `evaluate/test_record_references_native.py` | 8 | 4 |
| `semantic/test_artifact_identity_native.py` | 5 | 3 |
| `semantic/test_operations.py` | 4 | 3 |
| `semantic/test_native_attributed_evidence.py` | 4 | 2 |
| `semantic/test_native_closure.py` | 4 | 1 |
| `evaluate/test_operation_fitting_native.py`, `semantic/test_published_region_artifact.py`, `test_pdf_record_identity.py`, `test_alembic_native.py`, `test_source_views.py`, `test_arrow_publication.py` | 2 each | 1,2,2,0,0,1 |
| 18 modules with 1 each | 18 | `test_operation_assessment_native:349`, `test_selected_source_native:467`, `test_interpretations_native:162`, `test_native_agent_hold:84`, `test_runtime_bindings_native:161`, `test_contextual_enrichment_native:154`, `test_reference_evaluation:340`, `test_record_reading_closure_native:208`, `test_query:500`, `test_native_documents:326`, `test_interruption:51`, `test_published_document_native:127`, `test_pdf_staging:76`, `orchestrate/test_pdf_streaming_integration:224`, `orchestrate/test_pdf_cancellation_native:50` (+3) |

Bare `ValueError` in loop/param (47 sites, 33 modules): largest `evaluate/test_record_statistics.py` 5,
`semantic/test_dossier_contributions.py` 3, `test_characterization.py` 3, `core/test_canonical.py` 2,
`test_contextual_enrichment.py` 2, `test_characterization_evidence.py` 2, `test_pdf_payload_validation.py` 2,
`test_pdf_integrated.py` 2, `tests/scripts/test_test_receipts.py` 2 (full list: `python3 -I scratchpad/work/raises.py fam`).
Bare `ValidationError` in loop/param (40 sites, 29 modules): `core/test_shapes.py` 9, `core/test_dispatch.py` 2,
`semantic/test_dossier_contributions.py` 2, `test_record_policy.py` 2, 25 others 1 each.
The mutation families that DTA-001 names are included in these counts as follows:
`test_operation_fitting_native.py:306` (12 labelled mutations; `_label` discarded),
`test_contextual_enrichment_native.py:154` (13 `corruption` params), `test_interpretations_native.py:162` (8-mutation loop),
`test_arrow_publication.py:480` (6 `changes` params), the runtime-binding mutation test (`test_runtime_bindings_native.py:~136-148`) is not bare (it
uses `as rejected` with SQLSTATE `23514` alone); the bare site at `:161` is the separate immutability loop;
`test_review_bundle.py:771` (16 `corruption` params, bare `ValueError`),
`test_record_references_native.py:97-108` (3 bare + more at `:136,144,156,443`).

### 5c. Intended refusal reasons per production source (identified from `src/…/semantic/sql/*.sql`; guard text and SQLSTATE; mapping to the mutated input is by reading the guard conditions, not by running)

**Privilege sites** (test_publication.py:225-231, test_arrow_publication.py:180-185, test_native_closure.py:66-75)
- Writer `INSERT INTO data.entity`: guard is the absence of INSERT privilege - `REVOKE ALL ON ALL TABLES IN
  SCHEMA data,sem FROM corpus_sem_writer,corpus_sem_reader,PUBLIC` (`semantic_alembic/versions/semantic_0003_publication.sql:8`),
  with only `GRANT SELECT ON data.entity TO corpus_sem_writer/reader` (`semantic_0026_admission.sql:200-201`) → SQLSTATE `42501`.
  Without that, the row would fail the FK noted by the audit (`physical.yaml:499-521`, an FK violation `23503`),
  so SQLSTATE alone (`42501` vs `23503`) separates the two.
- Reader `SELECT data.begin_stage()`: EXECUTE granted only to `corpus_sem_writer` (`semantic/sql/transport.sql:51`) → `42501`.
- `test_native_closure.py:66-75` `UPDATE/DELETE/TRUNCATE/INSERT` as `admitter`: privilege (`42501`);
  its second block pins the immutability trigger `'immutable semantic content: %.% %'` `23514` (`semantic/sql/closure.sql:6`) and
  `'finalized release cannot acquire intrinsic meaning: %'` `23514` (`closure.sql:14`) by `match=`.

**`eval.record_operation_event_fit`** (`test_operation_fitting_native.py:279-307`; guard `semantic/sql/operation_event_fitting.sql:388-470`), all `23514`:
| label | guard (message at line) |
|---|---|
| cut | `:393` "operation fitting source/frame/C snapshot is stale or forged" |
| shape | `:442` "operation fitted parameters must be finite and shape-complete" |
| label leak | `:435` "fitted parameters lack exact event applicability or finite algorithm" (extra key `parameters-ARRAY[…]<>'{}'`) |
| class counts | `:407` "operation fit result changes the declared event/label population" |
| event identity | `:452` "operation predictions change exact event/label identity" |
| null algorithm `regularization_c|tolerance|max_iterations` | `:435` (same as label leak) |
| prediction prior/fitted probability 2, None, -1, None | `:462` "operation predictions require finite status-qualified probabilities" |
So the twelve cases reach 6 distinct messages.

**`sem.register_runtime_binding`** (`test_runtime_bindings_native.py:100-148`; guard `semantic/sql/runtime_bindings.sql`, all `23514` except none): release → `:27` "unsupported runtime binding contract" (`manifest.release_id` ≠ r); archive (`content_hex` altered) → `:58` "runtime source archive differs from declared digest"; contract (`version`) → `:27`; model → `:32` "runtime binding belongs to another execution model"; compiler_mismatch → `:32`; compiler `"26"` → `:27` (value outside `('27','28')`); semantic (`[]`) → `:37` "runtime semantic inputs differ from released meaning"; membership (`inputs[1:]`) → `:67` "runtime source archive membership differs from manifest". (Mapping from reading conditions; at least `compiler_mismatch` vs `model` and `release` vs `contract` not independently disambiguated.)

**Contextual enrichment** (`test_contextual_enrichment_native.py:65-157`, 13 corruptions via `bypass` → completion path; relevant guards in `semantic/sql/source_contributions.sql`, all `23514`): vector_dimension → `:2441/2443` "contextual vector profile/source/value binding differs"; foreign_inventory, forge_type, forge_parent → `:2490` "contextual inventory identity differs from eligible representations"; stale_representation → `:2504` "target representation differs or lacks its exact profile/vector"; omit_registry → `:2392/2403` curated-registry custody; wrong_occurrence/policy/rank/fusion/channel → candidate-list guards `:2589`, `:2605`, `:2742`, `:2764`, `:2768`; wrong_decision → `:2782/2784` "relationship identity differs from complete question decision"; empty_selected → `:195-199` "decision outcome differs from question-relative selection" (via `ops.validate_contextual_selection`). Exact one-to-one mapping not traced for the five candidate-list cases.

**`ops.require_source_interpretation`** (`test_interpretations_native.py:~125-162`, 8 mutations; `source_contributions.sql:1-75`, `23514`): cut → "interpretation source record differs from completed pinned result"; field/span → "interpretation focus does not authenticate record field source span"; metadata → "interpretation vocabulary metadata pins differ"; candidate → "candidate differs from released vocabulary"; selection → "selected terminology mapping lacks examined candidate or predicate"; direction/matching_predicate → "candidate matching field or predicate differs from source metadata" / selected-mapping guard (not separated).

**`data.publish_derived_batch_v2`** (`test_arrow_publication.py:456-493`, 6 `changes`; `semantic/sql/derived_publication.sql:55-82`): `projection`/`contract`/`operation` variants fall to "derived analytical projection policy is unsupported" (`:63`) or "accepted inference requires exact same-realization input" (`:81-82`); `cut`/`profile` → "candidate projection requires bound cut/profile" (`:65`) etc.; not traced per case.

**`native_pass` / reference passes** (`evaluate/test_record_references_native.py:97-108`): candidate guards `semantic/sql/native_references.sql:79,83,89,96` ("native reference pass differs from independent bound source frame", "…quote source was not independently supplied", "…citation differs from source-local projection", "…outside supplied independent sentences") and `record_references.sql:19,81` ("immutable source-origin assignment differs", "immutable reference source frame differs"); which guard fires for the duplicate pass id and the reversed `(b, a)` dependency order was not traced.

**`write_review_bundle`** (`test_review_bundle.py:673-773`, 16 corruptions → bare `ValueError`): guards are Python `raise ValueError(...)` in `src/corpus_structure/serve/review_bundle.py` (e.g. `:1932` "dossier predecessor differs from original producer custody", `:1957`, `:1963`, `:1972`, `:1989`, `:2051`, `:2071`, plus the `:1200` projection digest check (disabled by the fixture)); each corruption's own message not mapped.

**CLI sites**: `methods/test_m1_cli.py:9-35` - five parametrized argument sets; messages come from the CLI parser/validator, not identified here. `test_source_cli.py:356-357` retired positional form - not identified.

---

## 6. Absence and presence assertions

Named sites:

- **DTA-027** `PT/test_cli.py:93-106`. Production: `operations.py:161` `safe_text` then `stdout[-12000:]` (`:186`), `stderr[-6000:]` (`:187`). The test child is a 45-char URL + 11,960 filler + a 63-char tail. Assertion is `all(secret not in output …)` for three secrets only; no positive premise (e.g. the retained text beginning/ending, mask token present, or length) is asserted. Redaction-of-stderr controls are in `test_cli_recipe_reporting.py` (below).
- `PT/test_settings.py:151-154` (`test_report_masks_endpoint_url_credentials`): `Settings(llm={"endpoint": …user:secret@…?token=opaque})`; asserts only `"secret" not in rendered and "opaque" not in rendered`; no positive host/port/mask assertion in this test. `:197-202` (nemotron endpoint, fragment `private`): `all(secret not in rendered …)` over `settings_report(...).model_dump_json()` only.
  Compare positive-premise siblings: `test_settings.py:44-53` asserts the masked `postgresql://deployer:{MASK}@remote.example/corpus` before `"maintenance-secret" not in report.model_dump_json()`; `:109-114` asserts `MASK` equality for `llm.api_key` and the URL before absence; `:130-142` asserts host, port, query keys equal `MASK` before absence.

Same shape found by search (`grep -nE "\bnot in\b"` over `test_cli*.py`, `test_settings*.py`, `test_source_cli.py`, `test_review_cli.py`, `test_characterization_settings.py`, `test_semantic_runtime_settings.py`; ~90 lines). Secret/private-data absence only, with whether a positive premise is in the same test:

| Site (`PT/`) | Absent | Positive premise in test |
|---|---|---|
| `test_semantic_runtime_settings.py:179` | `reader-secret`, `admitter-secret` from `settings_report(...).model_dump_json()` | **none** (the test is `test_new_purpose_passwords_are_masked`; no `MASK`/url shape asserted) |
| `test_semantic_runtime_settings.py:43` | substring `"password"` | url username/password/host/query asserted just above (`:36-42`), not of the report |
| `test_cli_command_context.py:86` | `"private"`, `"secret"` in `result.stdout` | selection fields and `resources[key] == resolved[key]` asserted (`:76-84`); not the masked value form |
| `test_cli.py:382` | sentinel in `result.stdout` | exact error code and message (`:374-381`) |
| `test_cli_recipe_output.py:255`, `:57` | `first-secret`/`second-secret` from `row.text`; `EARLY-ERROR` | `row.text == "kept\n"` and byte counts asserted (`:253-254`) |
| `test_cli_recipe_reporting.py:64,250` | `example-secret`, `hidden-native-secret` | `"password=**********" in excerpt["text"]` asserted (`:62`, `:251`) |
| `test_cli_recipe_reporting.py:317,338-341` | `first-secret`/`later-secret`; `sensitive-first/-middle/-last` | `selected.text == "kept"`, `selected.truncated`, `basis == "retained_safe_output"` |
| `test_cli_model_inspect.py:204` | `secret` in `bounded.stdout` | `"**********" in bounded.stdout` (same line) |
| `test_cli_test_evidence.py:274,297,525,614` | `fixture-secret`, `must stay private`, ANSI | not examined line by line |
| `test_cli_managed.py:234` | `secret` from `safe_text(url)` | none beyond absence |
| `test_cli_correction_replay.py:81,127,334`, `test_cli_schema_diagnostic_boundaries.py:71,137,290,340` | private input/value | not examined |

Presence/count assertions of DTA-006 (`semantic/test_identity_exclusions.py:127-142`, `test_exclusion_comparison.py:108-119`,
`test_reference_evaluation.py:127-163`, `test_execution_projection.py:127-133`, `test_contextual_workflow_native.py:189,198,202`) were not
re-verified; only the DTA-027 neighbours above were examined.

---

## 7. Evidence-class identity (DTA-028)

### Switches (search: `os.environ`/`getenv` and `skip`/`skipif`/`importorskip`/`mark.corpus|gpu` in `PT/` and `tests/`)

| Switch | Read where | Marker or body | What it changes |
|---|---|---|---|
| `CORPUS_PM2_NATIVE_TEST_ASSETS` | `semantic/test_pm2_result_native.py:327` | **body** (`if assets:`) | same test identity either opens real PM2 workers (`:327-363`, profile `device: "cuda"`) and then runs the lease-loss control (`:364`, `:565-631`) or completes through hand-written replies with a `controlled-test` checkpoint (from `:366`); no skip, same outcome class |
| same | `semantic/test_characterization_native.py:1727,2112` | body, `pytest.skip(...)` | provider-gated tests skipped when unset |
| same | `semantic/test_pm2_parser_stage_native.py:42-44` | **marker** `skipif(not os.environ.get(...))` evaluated at collection; env read again in body `:87,117` | whole node skipped unless set |
| `CORPUS_GLINER_DIAGNOSTIC=1` | `methods/test_gliner.py:381-383` | marker `skipif` | pinned checkpoint diagnostic opt-in |
| `CORPUS_TEST_NATIVE_AUTH_CRASH=1` | `tests/scripts/test_native_auth.py:562,681,810,939,1086` | marker `skipif` | shared-cluster auth crash controls |
| `CORPUS_PDF_REPLAY_PAYLOAD`, `CORPUS_PDF_QUALIFICATION_SOURCE` | `semantic/test_pdf_json_publication.py:201-212`, `semantic/test_native_documents.py:84-98` | body, then `pytest.skip` when file absent/LFS pointer | path override of retained evidence input; no controlled branch |
| `CORPUS_REVIEW_CONTROL_DEST` | `semantic/test_review_failed_assembly_native.py:252-254` | body, `shutil.copytree` side effect only | output copy; no behaviour change |
| `QUALIFICATION_CONTROL_RECEIPTS` | `tests/scripts/test_parallel_harness.py:45,230`, `test_test_receipts.py:406,1088,1188` | body | retains the control receipts |
| `corpus` marker | `PT/conftest.py:122-138`; `mark.corpus` in `ingest/test_renditions.py:105`, `math/test_scope.py:100`, `math/test_coverage.py:31`, `llm/test_cascade.py:244`, `fixtures/test_fixtures.py:221`, `semantic/test_native_documents.py:28` (param) | marker | hook sets `qualification_prerequisite=corpus` + `qualification_reason` and `mark.skip` when the local corpus is missing |
| `gpu` marker | declared at `PT/conftest.py:102`; **no `mark.gpu` use found** (`grep -rn "mark\.gpu" python tests scripts`) | – | – |
| tool probes | `skipif(shutil.which("pyrefly"|"linkml-lint") is None, reason="blocked: …")` (`core/test_method.py:232`, `schema/test_packs.py:120`, `schema/test_model.py:43,49`, `semantic/test_scenario_ports.py:12`, `test_typed_realization.py:82`, `test_operation_call_generation.py:256`) | marker | reason text starts with "blocked:" |
| in-body environment/asset probes | `ingest/test_pdf_recognition.py:172` (`pytest.skip` when Nemotron runtime absent), `tests/test_pdf_alignment.py:172-175`, `semantic/test_artifact_identity.py:337` (`importorskip("splink")`) | body | – |

Other env: `HYPOTHESIS_PROFILE` (`PT/conftest.py:69`) selects `ci` (derandomized, 300 examples) vs `dev`;
no marker or receipt field records it. 43 `skipif/skip/importorskip/mark.(gpu|corpus)` lines total in `PT/`+`tests/` (grep).

### Markers (`pyproject.toml:57-60`, addopts `:46-56`)
Declared: `db`, `shared_cluster_fault`. `--strict-markers` is on. Further markers are added at runtime:
`db` (`tests/conftest.py:8`, `PT/conftest.py:101`), `gpu`, `corpus` (`PT/conftest.py:102-103`). Default
selection `-m "not shared_cluster_fault"`; `--dist=loadgroup`, `-n auto`, `--max-worker-restart=0`.
`xdist_group` is used (receipt `affinity_groups` collects it).

### What the receipt records (`scripts/qualification_plugin.py`, `scripts/test_receipts.py`)
- `collection_finish` event (`qualification_plugin.py:102-132`): `selected`, `nodeid_aliases`,
  `affinity_groups`, and `native_required` = items carrying the `db` marker (`:125-127`). `db` is assigned by
  `PT/conftest.py:129-130` from fixture names (`DB_FIXTURES`).
- Per-report `user_properties` `qualification_prerequisite` + `qualification_reason`: added by
  `pytest_runtest_makereport` when `PrerequisiteUnavailable` (scripts/test_prerequisites.py:8) is raised
  (`qualification_plugin.py:166-175`; raised from `scripts/native_test_support.py:257,506,522,531` for
  database/role prerequisites) and by `PT/conftest.py:131-138` for the `corpus` marker.
- `qualification_optional`: **read** at `test_receipts.py:481` (skipped + optional → `inapplicable`, otherwise `blocked`);
  set only by tests of the receipt machinery (`tests/scripts/test_test_receipts.py:265,722`); no setter in `PT/` or `scripts/` was found.
- Status derivation `_node_status` (`test_receipts.py:466-490`): failed+prerequisite → `blocked`; failed
  → `failed`; skipped → `inapplicable` (optional) / `blocked`; all three phases passed → `passed`.
  A `pytest.skip` from the provider tests therefore appears as `blocked` with the skip reason text; a pass
  of `test_pm2_result_native` under either branch appears as `passed` with no property distinguishing them.
- Native context: `record_native_context` (`qualification_plugin.py:51-64`) emitted from
  `native_test_support.py:725,774` (database acquisition). `_complete_native_context` (`test_receipts.py:492+`)
  requires item-bound `native-context/v1` with database identity (`database_oid`, `current_user`, `host`,
  `port`, `server_*`). Obligation: `native_required` items that pass must have a complete context
  (`test_receipts.py:686-722`). The context carries database acquisition only; no provider/asset/GPU field was found in it.
- Environment variables (assets, diagnostic, hypothesis profile) appear nowhere in `scripts/` (grep `PM2_NATIVE`, `NATIVE_TEST_ASSETS`, `GLINER_DIAGNOSTIC` in `scripts/`: none).

---

## 8. CPU lifecycle seams (DTA-026)

`src/corpus_structure/semantic/cpu_execution.py` (1064 lines).

- **Construction/ownership.** `CPUExecutionScope.__init__(prepared, policy=None)` (`:598-620`): policy
  defaults to `CharacterizationExecutionPolicy()` (`core/execution_policy.py:12-28`: `workers=2`,
  `max_submissions=2`, `max_owned_bytes=2 GiB`, …); `self._context = multiprocessing.get_context("spawn")`
  hard-coded (`:607`); a spawn `Event` and `Array("q", 2*max_submissions)` for stop/cancellation (`:608-609`).
  The executor is **created lazily** inside `_executor()` (`:622-642`) under `self._lock`:
  `ProcessPoolExecutor(max_workers=policy.workers, mp_context=self._context, initializer=_initialize,
  initargs=(capsule, self._stop, self._cancellation, policy.cpu_native_threads))` - the name
  `ProcessPoolExecutor` is looked up as a module attribute (import at `:10`), followed by
  `_PoolOwnership.capture(pool)` (`:641`), which reads private `pool._processes` and
  `pool._executor_manager_thread` (`:479-484`).
- **Grace constants.** `_COOPERATIVE_CLOSE_SECONDS = 5.0`, `_WORKER_EXIT_SECONDS = 5.0` (`:456-457`),
  module constants, read at `:545` (exit deadline = `deadline + 5.0`), `:819` (close deadline), `:820`
  (close-lock acquire timeout 10.0), `:879` (no-pool signaler join). Nothing outside this module
  references them (grep `_COOPERATIVE_CLOSE_SECONDS|_WORKER_EXIT_SECONDS` over `src`, `PT`, `tests`, `scripts`).
  Poll intervals 0.05/0.01 s are literals inside `_PoolOwnership.shutdown` (`:500,555,584`).
- **Existing injection points:** constructor args `prepared`, `policy` only; module attribute
  `ProcessPoolExecutor` (monkeypatched by one test); module constants above (not patched by any test);
  `_PoolOwnership.shutdown` (class attribute patched by one test); instance attribute `pool.submit`
  (patched per instance). No clock, executor-factory, context or deadline parameter.
- **Private `ProcessPoolExecutor` attributes touched by `PT/semantic/test_cpu_lifecycle.py`:**

| Attribute | Test lines | Use |
|---|---|---|
| `_initializer`, `_initargs` (write, read) | `:92-94` (test 2), `:144-145` (test 3), `:208-209` (test 4), `:326-327` (test 5) | replace/wrap the initializer so the parent's spawn `Event` reaches the child through initializer arguments; comment at `:91`: synchronization objects may cross spawn only as initializer args. Child jobs then fetch `_TEST_EVENT` (`:120-134`) instead of receiving it as a task argument |
| `_executor_manager_thread_wakeup.wakeup()` | `:261` | force the manager to observe the dead worker |
| `_broken`, `_shutdown_lock.locked()` | `:262` | wait until the manager is in broken-pool cleanup holding the shutdown lock |
| `_executor_manager_thread` | `:265` | give `ownership.manager` the live manager thread |
| `pool.submit` (public attr, monkeypatched on instance) | `:97,148,226,330` | submit a custom job instead of the production `_dispatch` |

  Test 1 (`:59-84`) uses the module-attribute seam instead: monkeypatches `cpu_execution.ProcessPoolExecutor`
  with a wrapper that overrides `initializer`/`initargs` kwargs. Tests also reach production-private state:
  `execution._context`, `_pool`, `_admissions`, `_closed`, `_physical_retired`, `_close_finished`,
  `handle._cancelled`, `_PoolOwnership.capture/processes/manager/shutdown`, `cpu_execution._worker_active`,
  `_WORKER_CANCELLATION`, `_WORKER_STOP._cond` (`:309,315`). Wall-clock assertions tied to the 5 s constants:
  `4.5 <= elapsed < 12` (`:78`), `< 5` (`:111`), `< 12` (`:161,282`), `9.5 <= … < 12` (`:376`), `< 5` (`:371`), `< 1` (`:355,367`).
  Production itself reads `pool._shutdown_lock`, `_shutdown_thread`, `_executor_manager_thread` (`:508-513`),
  documented as CPython 3.14 specific (`:461-467`).
- Imports for the test: `packet` from `semantic.test_cpu_execution`, `prepared` from `semantic.test_formal_evidence`
  (`:15-16`, both test-module owners; `test_formal_evidence` is imported by 7 modules).

---

## 9. Superseded machinery (DTA-030)

Search scope: whole repository, `grep -rnI`; **excluded** `docs/plans/`, `docs/design_review/evidence/`
(retained by standing rule), `.git`, `target`, `build`, `.venv`, `__pycache__`. Nothing in `justfile`, `ops/`,
`pyproject.toml`, `python/corpus-structure/src/`, `.github/` matched any item below.

**`cs_tpl_` scheme.** Source/tests only:
- `scripts/native_test_support.py`: `TEMPLATE_PREFIX = "cs_tpl_"` `:46`, `TEMPLATE_RETENTION = timedelta(days=1)` `:47`,
  `STAMP = re.compile(r"corpus-structure test template, last used (\S+)")` `:49`, stamp branch of `owned_comment` `:248`,
  `PgAdmin.stamp()` `:547-552`, `sweep()` `:555-586` selects `starts_with(datname, :tpl)` (`:574`), parses `cs_tpl_[0-9a-f]{16}(?:_build)?` (`:581`), ages by `STAMP`.
  Current templates are `cs_sem_head_<pid>_…` (`PT/conftest.py:257-259`); the sweep also handles `ci_test_*` and `cs_sem_*`.
- `PT/conftest.py:43` (import `TEMPLATE_RETENTION`), `:170` (class attribute on `DatabaseSupport`).
- `PT/test_db_fixtures.py:124-152`: fabricates `cs_tpl_…` names (`:128-129`), `db_support.TEMPLATE_RETENTION` (`:132`), `db_server.stamp(...)` (`:136-138`).
- Docs: only the audit pages (`docs/design_review/test-audit/execution-and-qualification.md:43`, `retirement-transfer.md:16-23`). Retained (excluded) mentions: `docs/plans/phase-0/foundations.md:233`, evidence folders.
- Whether `cs_tpl_*` databases still exist on the dev cluster: not checked (no database access).

**`committing_db`.** `PT/conftest.py:13` (docstring), `:74` (in `DB_FIXTURES`), `:295-303` (definition);
sole consumer `PT/test_db_fixtures.py:57-66` (self-test). 192 retained files under excluded paths mention it (collection manifests/receipts).

**Candidate branch.** `PT/semantic/test_native_attributed_evidence.py:50-72` overrides `semantic_db_engine` (new
name `cs_sem_m1_attributed_<hex>` rather than `database_name("test")`), and when `current_revision(conn) ==
"semantic_m1_private_20261103"` replays `docs/design_review/evidence/2026-11-03_m1-attributed-evidence/candidate-attempt-6/candidate/native_operations.json`
(`CANDIDATE` constant `:41-45`) via `NativeTransitionOp`/`admit_native`. That revision id is created by
`semantic_alembic/versions/0100_m1_private_records.py` and followed by `0101_m1_records.py`; the template
database is a frozen deployment at head (`PT/semantic/conftest.py:1-3`) and later revisions exist (e.g.
`semantic_alembic/versions/semantic_tc11_view_capacity.py`), so the branch condition is not true at head
according to source; not run. Same module also: `:33` absolute `semantic.native_record_fixtures` import vs `:35-36` relative.

**Legacy `python/corpus-structure/alembic/`.** Tracked files: `script.py.mako`, `versions/.gitkeep`,
`0001_initial_schema.py`, `0002_preserve_reference_descriptors.py`, `0003_preserve_statement_order_and_reference_roles.py`
(`git ls-files`). The reader is `semantic/migrations.py:14` `ALEMBIC_DIR = …/ "semantic_alembic"`. Search for
`corpus-structure/alembic`, `alembic/versions`, `0001_initial_schema`, `0003_preserve_statement` outside the
excluded paths: only `docs/design_review/test-audit/retirement-transfer.md:46`. Not referenced from
`pyproject.toml` (ruff/pytest), `justfile`, `ops/`, `scripts/`, `.github/`.

---

## 10. Module import naming

Facts from source:
- `pyproject.toml:46-61`: `--import-mode=importlib`; `pythonpath = ["scripts", "python/corpus-structure/tests"]`;
  `consider_namespace_packages` is not set (pytest default false). Installed pytest 9.1.1
  (`.venv/lib/python3.14/site-packages/_pytest`).
- Only `PT/methods/__init__.py` and `PT/semantic/__init__.py` exist (`find … -name __init__.py`, excluding
  caches). All other test directories (`ingest`, `evaluate`, `db`, `core`, `orchestrate`, `schema`, `math`,
  `llm`, `acceptance`, `agent`, `pool`, …) and `PT/` itself are not packages.
- `_pytest/pathlib.py:548-598` (`import_path`, importlib mode): `resolve_pkg_root_and_module_name`
  (`:847-880`) uses the topmost `__init__.py` chain (`resolve_package_path`); for a file in `semantic/` or
  `methods/` the key is `semantic.test_x` / `methods.test_x`, `sys.modules[module_name]` is returned if
  already present (`:557-560`) and otherwise the file is loaded via `_import_module_using_spec`
  (`:624-715`, which sets `sys.modules[module_name]` itself and the attribute on the parent package).
  If the file is not in a package (`CouldNotResolvePathError`) the fallback is
  `module_name_from_path(path, rootpath)` (`:761-790`): the path relative to `config.rootpath`, dots/hyphens
  kept as-is except `.`→`_`, e.g. `python.corpus-structure.tests.ingest.test_annotations`, with
  `insert_missing_modules` creating empty parents (`:597-598,716`). Callers pass `root=config.rootpath`
  (`_pytest/python.py:508-513`, conftests `config/__init__.py:758-763`).
- Consequences determined from that code (not observed at runtime):
  1. For `semantic.*` and `methods.*`, `from semantic.x import …` (absolute, via `pythonpath`) and
     `from .x import …` (relative) resolve to the same `sys.modules` key `semantic.x`; no second copy is created
     by the naming difference alone. 22 targets are imported both ways (largest: `semantic.native_record_fixtures`
     abs 38 / rel 58; `semantic.conftest` abs 24 / rel 3; `methods.test_m1_source_preparation` 8/8;
     `methods.primary_reading_fixture` 5/9; `semantic.reference_scenarios` 10/3; `methods.test_scoped_relations` 7/6; `methods.navigation_fixture` 6/6).
     `semantic/conftest.py` is loaded by pytest under `semantic.conftest` (same key as the absolute import).
  2. For test modules in non-package directories that other modules import by absolute name
     (`from ingest.test_annotations import …` finds the namespace-style directory via `pythonpath`), the
     import creates `ingest.test_annotations` while pytest collected the same file as
     `python.corpus-structure.tests.ingest.test_annotations`: two module objects, each executing the file.
     Targets (importer counts from the AST pass): `ingest/test_annotations.py` 9 statements (from `methods/` and `semantic/` plus
     relative from `ingest/test_definition_rules.py:20-21`, which resolves under the made-up collected name);
     `evaluate/test_characterization_assessment.py` 4, `evaluate/test_operation_assessment_native.py` 2 (one from `semantic/test_review_cli_native.py`),
     `evaluate/test_record_alignment.py` 2, `ingest/test_pdf_recognition.py` 2, `evaluate/test_record_references.py` 1,
     `db/test_store.py` 1, `ingest/test_pdf_assembly.py` 1. Cross-directory importers: `methods/*`, `semantic/*` (absolute).
  3. Top-level support modules (e.g. `pdf_acceptance_support`, `math_support`) are imported only by their
     absolute name (via `pythonpath`) and are not collected: single key.
- Open (not established): whether `evaluate`, `ingest`, `db`, `core` top-level names could be shadowed by an
  installed distribution on `sys.path` (not checked); whether any state in the duplicated modules
  (caches, `lru_cache`, monkeypatched module attributes) matters for any test; actual `sys.modules`
  contents in a worker (no collection allowed).
