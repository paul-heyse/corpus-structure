# Support structure and boundary fidelity

**Interface-checked by source inspection, 2026-11-12.** See the [baseline](README.md#baseline).
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
The same support module is imported under two names in places
(`tests/semantic/test_native_attributed_evidence.py:33` uses `semantic.native_record_fixtures`
while `:35–36` use the relative form; `test_runtime_identity.py:24` uses the absolute
`semantic.test_execution_release` where siblings use the relative one). Whether that yields
two module objects, and so duplicated fixtures and caches, under `--import-mode=importlib` was
not determined.

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
`SPACY_COLUMNS`, then finish — is written out separately in
`tests/methods/primary_reading_fixture.py:84–104`, `tests/methods/navigation_fixture.py:56–75`,
`tests/methods/test_construction_named.py:95–111`,
`tests/methods/test_contextual_characterization.py:46–57`,
`tests/methods/test_math_scope_primary.py`, `tests/methods/test_m1_producer.py`,
`tests/methods/test_primary_reading_consumers.py`,
`tests/methods/test_definition_declaration_primary.py` and `tests/native_math_primary.py`.
`tests/methods/test_native_evidence.py` constructs the builder as its subject under test and is
not part of this footprint.

The copies restate how production assembles the layer rather than expected results, so they
are not independent oracles; they are parallel setup. A change to the assembly contract must
be mirrored in each copy, and a copy that lags keeps passing against an obsolete shape. Each
copy chooses its own operation, profile and configuration text, which decide what the
consuming test exercises. The copies already differ in one visible respect: the shared fixture
and the navigation copy pass placeholder configuration and overwrite `configuration_digest`,
while the construction-named copy passes real configuration text and lets `native_run` derive
the digest (`src/corpus_structure/methods/native_evidence.py:117`). That difference looks
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
