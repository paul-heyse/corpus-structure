# Support structure and boundary fidelity

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13.** See the
[baseline](README.md#baseline).
Sharing types, validators and valid setup is useful; an expectation assessing their correctness
must retain a challenge independent of the relevant mistake.

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

<a id="dta-029"></a>

## DTA-029 — The primary-layer assembly scaffold is hand-copied across method tests

**FP-03/04, DP-06/16; A3; companion §2.** The sequence that turns a controlled annotation into
a native primary layer — construct `NativeEvidenceBuilder`, call `native.spacy(...)`, build
`native_run("spacy", "spacy_only", …)`, attach availability rows mapped through
`SPACY_COLUMNS`, then finish — is written out separately in seven files:
`tests/methods/primary_reading_fixture.py:83–104`, `tests/methods/navigation_fixture.py:47–75`,
`tests/native_math_primary.py:84–118`, `tests/methods/test_math_scope_primary.py:82–90`,
`tests/methods/test_construction_named.py:93–111`, `tests/methods/test_m1_producer.py:187–198`
and `tests/methods/test_primary_reading_consumers.py:116–142`. Not part of this footprint
(footprint refined by the [design review](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md),
2026-11-12): `tests/methods/test_native_evidence.py` constructs the builder as its subject under
test, `tests/methods/test_contextual_characterization.py:46–57` only appends provider metadata
rows, and `tests/methods/test_definition_declaration_primary.py` uses the HanLP path.

The copies restate how production assembles the layer rather than expected results, so they
are not independent oracles; they are parallel setup. A change to the assembly contract must
be mirrored in each copy, and a copy that lags keeps passing against an obsolete shape. Each
copy chooses its own operation, profile and configuration text, which decide what the
consuming test exercises. The copies already differ in one visible respect: the shared fixture,
the navigation copy and `native_math_primary` overwrite `configuration_digest` with the pipeline
digest, while the math-scope, construction-named and M1-producer copies let `native_run` derive
it (`src/corpus_structure/methods/native_evidence.py:117`). That difference looks
deliberate; it shows that a reader cannot tell intended variation from drift without comparing
the copies.

A shared owner exists and is used from eight other files (`primary_product` in
`primary_reading_fixture.py`). Which other differences between copies are intended was not
established for every site. Related release preparation is duplicated at module boundaries
with identical inputs in four modules (`primary_reading_fixture.py:23–28`,
`test_construction_named.py:34–40`, `test_native_evidence.py:36–42`,
`test_characterization_composition.py:16–26`); the production cache absorbs that repetition
within a process, so it is noted as duplicated ownership rather than repeated work.

<a id="dta-028"></a>

## DTA-028 — One provider test identity passes on a controlled branch

**FP-02/05/06, DP-21/22; G7; companion §5/6.**
`tests/semantic/test_pm2_result_native.py:286–563` is a single test whose evidence class is
chosen by an ambient environment variable read in the body (`:327`). With
`CORPUS_PM2_NATIVE_TEST_ASSETS` set it opens real workers and settles a claim, and only then
runs the reassignment-after-lease-loss control for this provider (`:364`, `:565–631`; lease
expiry itself has controls in other modules). Without it, the same test identity completes
through hand-written replies with a `controlled-test` checkpoint (from `:366`). A passing
receipt for that node therefore does not say whether a provider ran. Operator evidence and
plans do record the variable on the command line, which is how the distinction is carried
today; the machine receipt does not. The repository's reporting rule is that a mocked provider
is never `passed`; here the distinction is not carried by the test identity, a marker or the
recorded outcome.

The neighbouring provider tests show both alternatives: a marker that skips the provider test
when assets are absent (`tests/semantic/test_pm2_parser_stage_native.py:42–44`) and a separate
explicitly controlled test in the same file (`test_pm2_result_native.py:104–278`).

A lower-weight footprint of the same labelling concern is naming. Some tests whose
collaborators are replaced are named for the actual boundary:
`tests/semantic/test_native_candidate_cli.py:65` asserts rollback on a fake connection;
`tests/ingest/test_pdf_capacity.py:1` describes restoring GPU ownership through a local HTTP
double. Module docstrings usually state the limit, as `tests/orchestrate/test_source_operation.py:1`
does ("native boundaries are controlled") for tests named actual, real and live, and STATUS
reports controlled panels as controlled. The naming sites alone would not be a finding; they
matter where a result is read by test name.

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

<a id="dta-005"></a>

## DTA-005 — Selected assembled scenarios use production composition

**FP-03/04, DP-01/06; A2/A3; companion §1/2.** Still holds;
`tests/semantic/serving_scenarios.py:353–357` and `tests/semantic/test_pack_acquisition.py`
compose through `prepare_packs`, and `tests/orchestrate/test_policy.py:36–38` does so as a
module fixture.

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
