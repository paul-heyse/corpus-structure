# Support structure and boundary fidelity

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13 and 2026-11-17.** See the
[baseline](README.md#baseline).
Sharing types, validators and valid setup is useful; an expectation assessing their correctness
must retain a challenge independent of the relevant mistake.

<a id="refresh-2026-11-17-support"></a>

## Refresh of 2026-11-17

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline](README.md#baseline)). No test was run.

| Earlier finding | Status at `fbd3f2a98` |
|---|---|
| DTA-009 | Standing, changed footprint |
| DTA-029 | No longer applicable; the same cause recurs as DTA-041 |
| DTA-028 | Corrected |
| DTA-034 | Partly corrected, changed footprint |
| DTA-016, 005 | Changed footprint |
| DTA-012 | Stands |
| DTA-008 | No longer applicable |

Support worth preserving, read in this refresh: the sealed scenario seeds (frozen recipe
values, read-only seed files, a fresh clone per consumer, validation on every reuse); the
staged declared scenarios that replaced the mode-flag builders; the wire-checked routing double;
hand-authored record expectations kept deliberately independent
(`tests/semantic/record_contracts_support.py:124–384`); and `stage_pdf_document`, which routes
fixtures through real certification (`tests/pdf_acceptance_support.py:34–143`).

<a id="dta-041"></a>

### DTA-041 — The controlled PDF converter is hand-copied nine times, and the copies no longer produce what production requires

**FP-02, FP-03, FP-06; DP-16, DP-23; H1; companion §2, §3, §5.** The cause DTA-029 described,
now in the scenarios most source tests share.

Integrated source scenarios replace the parent-side `PdfWorker.stream` with a local function
that builds a document, writes record and occurrence batches and returns
`PdfStreamReply("success", (), recipe, (), records + occurrences)`. Nine copies exist with no
owner: `tests/semantic/current_pdf_source_support.py:198–250` and `:372–437`,
`current_pdf_integration_support.py:260–306`, `current_artifact_support.py:140`,
`rich_domain_native_support.py:152`, `tests/evaluate/declared_record_native_support.py:247`,
and inside the test bodies of `test_pdf_materialization_native.py:80`,
`test_pdf_transform_demand_native.py:110` and `test_nce02_native_scope.py:251`.

The doubles patch the class attribute, so the real `run_private_native_pdf_build` runs and
calls them (`src/corpus_structure/orchestrate/pdf_streaming.py:409, 493`). Two unconditional
checks on that fresh path now refuse what they return:

- immediately after the stream, spool completion requires exactly one native-preparation and
  one native-completion entry (`src/corpus_structure/ingest/pdf_build_spool.py:744–748`). The
  doubles emit only record and occurrence batches; production emits the completion entry in the
  worker (`ingest/pdf_worker.py:114–116`). This arrived in commit `7f3951adf` (2026-11-17
  14:08, "runtime not_run");
- the caller then raises "native PDF publication has no producer certification" when the
  reply's certification or access replay is missing (`pdf_streaming.py:529–530`). Both default
  to `None` and the doubles do not set them (`ingest/pdf_stream_types.py:145–154`). This arrived
  in `22254ed01` (2026-11-17 15:43, "runtime not_run").

Neither commit changed the copies. The only branch that reuses a reply needs a prior complete
spool in the same directory, which a fresh per-test directory does not have. The copies also
write occurrences through a method production no longer calls.

**Consequence.** Every consumer of these scenarios fails during setup: `current_pdf_source` and
its factory (23 test files), the integration journeys, and the record-policy, rich-domain and
artifact journeys. One shared setup failure stands in front of every product claim those tests
make. This is established from source and not observed: no stored result exercises any of
these consumers after 14:08 on 2026-11-17.

**Contrary evidence.** Replacing only the converter is a sound boundary choice.
`pdf_acceptance_support.stage_pdf_document` stays current because it certifies through
production, and one double does supply the fields
(`tests/orchestrate/test_pdf_private_execution.py:164–172`).

**Footprint.** The nine copies and both refusals are established; the function was read in
full for the challenge.

<a id="dta-042"></a>

### DTA-042 — Support modules restate how the domain pack and the captured recipe are composed, and one pairs a model with a release that does not contain it

**FP-04/A2; DP-01, DP-06, DP-16; companion §1, §2.**

Five modules hand-list the same statistics base bundle (`semantic.yaml`, `terminology.yaml`,
`core.yaml`, wrapped by layered inputs): `tests/semantic/record_contracts_support.py:48–66`,
`tests/evaluation_record_alignment_support.py:45–63`,
`tests/methods/record_assembly_support.py:23–49`, `tests/methods/m1_producer_support.py:32–54`
and `tests/evaluate/declared_record_grading_support.py:34–48`. Production owns pack acquisition
(`src/corpus_structure/semantic/regeneration.py:297–354`); among support modules only
`tests/statistics_pack_support.py:10–12` uses it. Two recipes write a modified copy of the
domain schema, removing a class and re-pointing imports
(`tests/evaluate/declared_record_native_support.py:60–73`;
`tests/semantic/rich_domain_native_support.py:47–49`).

Each of the five builds its model with its own `compile_data_operations(bundle)` rather than
binding the model from its release. In `declared_record_grading_support.py:51–56` the model is
compiled with reading-resolution declarations and Python sources while the paired release is
prepared without dependencies, so the model under test and the release under test differ.

A related repetition: about twelve recipe builders repeat the same sequence to extend the
captured PDF recipe (read the captured inputs, drop artifacts under production's private
`"data-operations/"` prefix, recombine sources and dependencies), and two different functions
are both named `current_pdf_recipe`
(`tests/semantic/current_pdf_source_support.py:46`; `current_pdf_integration_support.py:63`).

**Consequence.** A change to the pack layout or to how captured inputs compose has to be
mirrored by hand in each copy. Drift in the recipe sequence fails loudly. The model and release
mismatch means a scenario can bind records against a release whose admitted model is not the
one it compiled; no wrong result from this was established.

**What to keep.** The hand-authored record contents and the deliberate alignment sub-model are
independent expectations, not duplication.

<a id="dta-043"></a>

### DTA-043 — Byte-admission and execution-basis tests assemble the executor from private fields and carry their own copy of the reservation formula

**FP-01, FP-02, FP-06; DP-23; A1; companion §2, §5.**

`controlled_executor` (`tests/orchestrate/test_data_operation_byte_admission.py:69–197`)
creates `NativeDemandExecutor` through `__new__`, assigns about eighteen private attributes,
stubs eight private methods, and patches the planner and storage. It sets
`reservation = 2*packet + 3*reply` (`:79`, and again in `policy_for`, `:51–57`), a copy of
production's formula (`src/corpus_structure/orchestrate/data_operations.py:689`). Its claim
double returns hand-written payloads with no wire validation (`:145–170`).
`test_data_operation_execution_basis.py` and `test_execution_host.py` import the builder from
that test module, and the former builds four more executors with `object.__new__`. Sixteen
test functions depend on the builder.

**Consequence.** If production changes how the reservation or another derived field is
computed, these tests keep testing admission against a value production no longer uses. Any
change to executor internals means editing all of them.

**Contrary evidence.** Production exposes a constructor that accepts the execution basis, host,
database capacity and capability factories and computes the reservation and budget itself
(`src/corpus_structure/orchestrate/data_operations.py:634–654, 689–693`); these tests bypass
it. The tests do exercise the real byte budget, process host and CPU call
planning with a real prepared capsule (`:227–299`), and native execution is covered separately
through the kernel fixture. The structure and the duplicated formula are established; whether
any other derived field has already diverged was not examined.

## Earlier findings

<a id="dta-009"></a>

## DTA-009 — Scenario ownership sits in test modules and fixture-name bindings

**FP-01/03/06, DP-17; A1; companion §2/3.** The manifestations named on 2026-11-05 are
corrected. `tests/evaluate/test_record_references_native.py` and
`tests/evaluate/test_record_policy_authority_native.py` no longer replace another test host's
globals; they import `expected_reading`, `assign_origin` and related builders from
`tests/semantic/reference_scenarios.py` and production. `tests/semantic/test_publication.py` no
longer computes a release at import time; two module-level `prepare_release` bindings remain
(`tests/semantic/test_prepare.py:584`, `tests/semantic/test_projection_analysis_products.py:124`).

The cause has moved rather than closed. Scenario policy is still decided by where a name was
imported from, in three current forms.

**A shared fixture is specialized by overriding a sibling fixture name.** `private_source`
(`tests/semantic/native_record_fixtures.py:791–819`) merges `private_source_options` with
indirect parameters. Eleven modules override `private_source_options`
(`reference_scenarios.py:197`, `test_interpretations_native.py:22`,
`test_table_correspondence_native.py:40`, `test_structural_native_replay.py:58`,
`test_pm2_parser_stage_native.py:38`, `test_protected_comparison_gap_native.py:70`,
`test_record_reading_closure_native.py:28`, `test_condition_publication_native.py:77`,
`test_local_semantic_admission_native.py:48`, `test_artifact_identity_registered_native.py:58`
and `tests/evaluate/test_record_policy_authority_native.py:134`, beside the default at
`native_record_fixtures.py:782`). Options can carry transform functions for the bundle and
dependencies, and one option makes the builder monkeypatch a production function
(`native_record_fixtures.py:386–396`). Which release a case runs under therefore depends on a
fixture name resolved by import: `tests/semantic/test_review_cli_native.py:28` imports the
options fixture from `reference_scenarios`, while most consumers import the default from
`native_record_fixtures`. `test_structural_native_replay.py:57–70` selects source text by
inspecting `request.node.callspec`. Dropping a re-export or reordering indirect parameters
changes setup without any assertion naming the decisive default. This is more explicit than
the earlier global patching: the options dictionary is a stated surface, the fixture is
realistic rather than a stand-in, and monkeypatching is restored per test.

**Test modules act as support libraries for other test modules.** There are 266
`from …test_… import` lines across the package tests. Most import public builders from a
cohesive owner. The sharper cases:

- Private names: `_bundle`, `_project` and `_stage_authored_sql` from
  `tests/semantic/test_execution_release.py` into `test_runtime_identity.py:24`,
  `test_native_closure.py:154`, `test_execution_projection.py:149`, `test_pdf_record_native.py:489`
  and `test_sql_admission_phases.py:16`; `_source` through
  `test_contextual_query_replay.py:31`; `_inference_publication_state` into
  `test_operation_reporting_native.py:140`; `_bound_projection` into
  `test_prepared_graph_candidates.py:125`.
- A fixture that disables production verification travels by import.
  `synthetic_source_projection` (`tests/semantic/test_review_bundle.py:202–208`) replaces
  `review_bundle._verify_source_projections` with a function returning an empty set. It is
  re-exported through `test_section_heading_replay.py:36` to
  `test_contextual_query_replay.py:32` and imported by `test_dossier_contributions.py:26`, a
  three-module chain. Each test opts in by naming the fixture, so nothing is disabled
  invisibly; the concern is that a verification-disabling double is owned by a test module.
  The fixture is labelled synthetic and the native proof has its own test.
- Cross-directory chains: semantic tests import fixtures from `tests/methods/test_*` modules
  (for example `test_dossier_contributions.py:12–13`, `test_artifact_identity.py:77–78`,
  `test_contextual_characterization.py:5–8`), methods and evaluate tests import from
  `tests/semantic/test_*`, and `tests/methods/test_record_assembly.py`,
  `test_scoped_relations.py` and `test_native_evidence.py` each supply builders to four or more
  sibling modules.

A behavior-preserving edit to one test module's helper can change the premise of several
others, and collecting a consumer imports and executes its owner. No case was found where this
coupling currently changes what a test asserts. Dedicated owners already exist and show the
alternative (`domain_scenarios.py`, `reference_scenarios.py`, `serving_scenarios.py`,
`witnessed_scenario_support.py`, root `tests/pdf_region_support.py`);
`tests/semantic/test_scenario_ports.py:59–87` guards against eager preparation at import.
Test modules are also loaded twice in some cases (settled by the
[design review](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md),
2026-11-12, from pytest 9.1.1's `import_path`). Only `tests/semantic/` and `tests/methods/` are
packages. A test file in a non-package directory is collected under a rootdir-relative module
name, and importing it by absolute name through the configured `pythonpath` executes the file
again as a second module object with its own classes, fixtures and caches. Importers exist, for
example `from evaluate.test_operation_assessment_native import freeze`
(`tests/evaluate/test_characterization_assessment_native.py:10`,
`tests/semantic/test_review_cli_native.py:13`) and `from ingest.test_annotations import …`
(`tests/semantic/test_nce02_native_scope.py:103`, `tests/methods/test_native_evidence.py:9`).
Absolute and relative imports of `semantic.*` and `methods.*` modules resolve to one module, so
they are not duplicates. Whether the duplicated state changes any test's result was not
established.

**Changed footprint, 2026-11-13 — the declared-data-operations tests have no support owner.**
The 32 `test_data_operation_*.py` modules added since the last baseline share setup the same
way, and no support module exists for them.

- `tests/semantic/test_data_operation_storage.py` is the support library for the native kernel.
  Its private builder `_declaration()` (`:61–94`) fixes the subject kind, the context shape and
  the behavior name that other cases run under. It is imported by
  `test_data_operation_subjects.py:11`, `test_data_operation_original_native.py:29`,
  `test_data_operation_population_native.py:29`, `test_data_operation_consumer_native.py:55` and
  `tests/orchestrate/test_data_operation_execution.py:29`; the fixtures `ddo_kernel_engine` and
  `kernel` and the helpers `claim` and `publish` travel the same way. `test_data_operation_subjects.py`
  is a pure compiler test and imports the native storage module for that one dictionary.
- Other owners by accident of where a helper was first written: `contract`, `declarations`,
  `identity` and `resolved_binding` come from `test_data_operation_compilation.py`;
  `fixture_source` and `kind` from `test_data_operation_ports.py`; the binding-native connection
  and its `context`, `evaluate`, `field` and `literal` helpers from
  `test_data_operation_binding_native.py`; `original_target` from
  `test_data_operation_original_native.py` and `captured` from `test_data_operation_wire.py`
  into `test_original_documents.py:17–18`.
- The admission sequence (persist the release, admit it, persist the runtime binding, insert a
  project) is written out three times, the pattern [DTA-029](#dta-029) records for the
  primary-layer scaffold: `test_data_operation_storage.py:228–232`,
  `test_data_operation_population_native.py:137–151` and
  `tests/orchestrate/test_data_operation_execution.py:76–80`.
- A new import form reaches across a non-package directory. `tests/orchestrate/` has no
  `__init__.py`, and its data-operation tests import `from ..semantic.test_data_operation_storage`
  (`test_data_operation_execution.py:29–30`) and `..semantic.test_data_operation_ports`
  (`test_data_operation_batch_activity.py:67–68`). The paragraph above says relative imports of
  `semantic.*` resolve to one module; that was established for importers inside the package.
  A contributor's reading of pytest 9.1.1's `import_path` is that a non-package file is named
  from its rootdir-relative path, so `..semantic.X` resolves to a different module name from the
  collected `semantic.X` and the file runs a second time. This was not executed. The storage
  module holds no module-level state today, so the consequence is latent.

The target design names the things these helpers build: a compiled effective model, an admitted
release, a `SubjectContext` root, a demand and its attachment, a purpose principal. Each of
those is a natural unit of test support, and none has an owned module. A change to a private
helper in the storage test module silently changes what five other modules exercise. The
companion (§2) does not require support to mirror production; the point is that case-defining
defaults are owned by whichever test module wrote them first. No case was found where this
changes what a test asserts.

**Large mode-flag builders decide unrelated cases.** `build_domain_case`
(`tests/semantic/domain_scenarios.py:65–95`) takes about twenty-five keyword switches and
`build_resubmission_case` (`tests/semantic/agent_scenarios.py:36–174`) seven; both always
publish controlled views and create a run and task, and the latter always runs real primary
producers. Their default proposals define what other cases mean. Consumers that need only a
fragment are recorded under [DTA-018](execution-and-qualification.md#dta-018).

**Status, 2026-11-17, source `fbd3f2a98`.** Standing, changed footprint. Real support modules now exist for the data-operation tests and are widely used. Test modules still serve as support for others: a scan of both test trees finds 91 files that import a `test_*` module, including across directories without packages, which contradicts the 2026-11-13 reconciliation's search result. Examples: `tests/semantic/test_change_impact.py:655–661` calls another module's test function as its scenario builder; the private `_page` in `test_demand_results.py:20` is imported by eleven modules; `_complete_ready` in `test_data_operation_population_native.py:145` by four; `controlled_executor` travels from one orchestrate test module to two others ([DTA-043](#dta-043)). Generic fixture names are defined in several modules (`prepared` in eight, `acquired` in seven), so which one a test gets depends on its imports. Whether cross-directory imports load a module twice under the current import mode was not run.

<a id="dta-029"></a>

## DTA-029 — No longer applicable; the cause recurs elsewhere

**No longer applicable (2026-11-17, source `fbd3f2a98`).** `NativeEvidenceBuilder` and the copied scaffold are gone; primary assembly has one owner (`tests/methods/declared_primary_fixture.py`). The same cause, an unowned hand-copied production sequence, recurs in the PDF converter copies ([DTA-041](#dta-041)). Earlier text is in Git at `fbd3f2a98`.

<a id="dta-028"></a>

## DTA-028 — Corrected

**Corrected (2026-11-17, source `fbd3f2a98`).** The provider tests carry provider-evidence and prerequisite markers and the file has no controlled branch (`tests/semantic/test_pm2_result_native.py:232–235, 258–260, 324–326`). Earlier text is in Git at `fbd3f2a98`.

<a id="dta-034"></a>

## DTA-034 — Two declared-data-operation claims are checked on a substitute below the boundary they reach

**FP-02/06, DP-23; companion §5/7. Interface-checked by source inspection, 2026-11-13.** Lower
weight; recorded because the plan's own rule is that a substitute cannot stand in for the
native boundary.

*Storage doubles sit below wire validation.* `DataOperationStorage.invoke` validates the input
and the output of every native call against the closed wire contract
(`src/corpus_structure/semantic/data_operation_storage.py:317–332`). The planner and service
routing tests replace the whole storage object with a class whose `invoke` returns hand-written
dictionaries (`tests/semantic/test_data_operation_demands.py:216–221`,
`tests/semantic/test_data_operation_service.py:16–27`). A contributor judged that some of those
payloads would not pass the wire contract; the coordinator confirmed the doubles bypass
validation and did not check each payload against it. A planner or service change that emits or
accepts a shape the wire forbids would pass these tests. The claims are routing claims, and
native tests in the same files cover the real path, which bounds the exposure.

*Binding semantics run on SQLite.* `tests/semantic/test_data_operation_bindings.py:130` and
`tests/semantic/test_data_operation_consumer_bindings.py:88` execute compiled bindings on
`sqlite://`. Production executes the same compiled statements on PostgreSQL through the
planner's storage connection. The matrix of null-as-unknown, distinctness, ordering and covers
semantics has no PostgreSQL counterpart for the compiled path, and no file runs one case set
through both the Python-compiled and the native binding implementations (the native vectors are
in `test_data_operation_binding_native.py`, the compiled ones here). The compiler uses portable
SQLAlchemy Core constructs and integrated PostgreSQL paths exist in the storage, population and
execution tests, so this is a fidelity gap of uncertain size and not an observed divergence.
Running pure binding semantics without a database is also the economical choice, and should not
be lost in closing it.

**Status, 2026-11-17, source `fbd3f2a98`.** Partly corrected, changed footprint. The SQLite substitute is gone, binding semantics run on PostgreSQL with independently authored rows (`tests/semantic/test_data_operation_bindings.py:136–215`), and the wire-checked routing double validates native input and output contracts (`tests/semantic/data_operation_binding_support.py:240–262`). Substitutes that still stand below the boundary they claim, unvalidated:

- `_page`, a hand-written native read-result page that the result reader loads raw, is never checked against the generated wire type and reaches eleven modules (`tests/semantic/test_demand_results.py:20–91`);
- `control_frontier` re-implements the native recheck's refusals for every query-cache consumer test (`tests/semantic/selected_query_cache_support.py:27–43`);
- a raw double for closing a population (`tests/semantic/test_data_operation_demands.py:635–660`) and the claim double in [DTA-043](#dta-043);
- `_native`-named tests on a hand-built substitute schema ([DTA-047](execution-and-qualification.md#dta-047)).

If the native page or refusal changes shape, these consumers keep passing on the old one.

<a id="dta-016"></a>

## DTA-016 — Actual stdio and production serializer controls correct the substituted-boundary gaps

**FP-02/05/06, DP-23; companion §1/3/5/6.** Still holds with a grown footprint.
`tests/semantic/test_runtime_entrypoints.py:463–609` uses the SDK stdio transport over a real
child for four modes and asserts process-group disposal and zero remaining database sessions.
For the three non-complete modes the task assertion is only that the row is not `done`
(`:608`), which does not distinguish leased, pending, failed or released, and the cancelled
mode cancels at a checkpoint before the lease. `tests/semantic/test_pdf_record_reader.py:438–466`
still iterates production `iter_native_json` and asserts the chunk bound and exact
reconstruction. In-memory controls keep their distinct scope.

**Status, 2026-11-17, source `fbd3f2a98`.** Changed footprint: the stdio control moved to `tests/semantic/test_external_runtime_native.py:50` and `structural_production_native_support.py:227–285`. Not re-examined further.

<a id="dta-005"></a>

## DTA-005 — Selected assembled scenarios use production composition

**FP-03/04, DP-01/06; A2/A3; companion §1/2.** Still holds;
`tests/semantic/serving_scenarios.py:353–357` and `tests/semantic/test_pack_acquisition.py`
compose through `prepare_packs`, and `tests/orchestrate/test_policy.py:36–38` does so as a
module fixture.

**Status, 2026-11-17, source `fbd3f2a98`.** Changed footprint: `serving_scenarios.py` is gone, and production pack composition is used by one support module; see [DTA-042](#dta-042).

<a id="dta-012"></a>

## DTA-012 — Historical macro configuration ownership is explicit

**FP-04/06, DP-01/06; companion §1/2/8.** Still holds; `tests/math_support.py:10–13` and
`tests/llm/conftest.py:7–10` keep their frozen-oracle statements although `math_support.py`
itself changed substantially.

<a id="dta-008"></a>

## DTA-008 — Previously missing method-contract fields remain corrected

**FP-02/04, DP-24; companion §1/5.** Still holds; the hand-built method descriptors found in
the evaluate tests declare `unit_type` and `Config`
(`tests/evaluate/test_record_references_native.py:614–621,699–706`,
`tests/evaluate/test_record_policy_authority_native.py:158–166`). Other `SimpleNamespace`
descriptors were not audited.

**Status, 2026-11-17, source `fbd3f2a98`.** No longer applicable: the cited evaluation test files are gone.
