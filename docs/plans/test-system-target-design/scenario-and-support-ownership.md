# Scenario and support ownership

**Status:** Accepted design companion; the [coordinator](../test-system-target-design_2026-11-13.md)
owns current implementation, findings and qualification state. **Created:** 2026-11-13.

**Present-state framing, 2026-11-13.** Non-gated functional scope has reached the coordinator's
integration boundary. The [assembled review](../../design_review/reviews/design_review_test-system-assembled_2026-11-13.md)
assesses that implemented architecture within its stated scope. The contracts and original
implementation instructions below retain the accepted design; dated source descriptions are
baseline evidence, not current implementation or qualification claims.

This companion owns the designs of TS-06 (support placement, import rules and recipe values),
TS-07 (staged builders, focused consumers and the recipe memo) and TS-15 (one owner of the
primary-layer assembly). The [coordinator](../test-system-target-design_2026-11-13.md) owns
package state, the dependency queue and the disposition of every finding named here.

**Baseline and evidence.** The original source reading was on `main` between `f03170a89` and
`434023ee8`; revision source was inspected at `b1b4a4de0`, 2026-11-13. This revision incorporates
[I03, I04, I05, I06 and I11](../../plan_improvement_reviews/test-system-target-design_2026-11-13.md)
of the plan-improvement review. Line citations are as read. Design statements were **Proposed**
at original authoring and subsequently accepted through the coordinator. Baseline source facts are
**Interface-checked by source inspection, 2026-11-13**. Durations quoted from the audit are
**Measured** from stored results and are orders of magnitude. No package has a speed target.

**Paths.** `tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written
as root `tests/…`, `scripts/…`, `conftest.py`, `pyproject.toml`. Section references (§4.3 and so
on) are to the [source review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md).

## Original inspection baseline and reused mechanisms

- **Support modules already exist and show the target.** `tests/semantic/domain_scenarios.py`,
  `agent_scenarios.py`, `reference_scenarios.py`, `serving_scenarios.py`,
  `witnessed_scenario_support.py`, `native_record_fixtures.py` and the package-root
  `pdf_acceptance_support.py` are imported by canonical name and are never collected.
- **Only two test directories are packages**: `tests/semantic/` and `tests/methods/` have an
  `__init__.py`. Root `pyproject.toml:74` puts `scripts` and `python/corpus-structure/tests` on
  `pythonpath`, and `:63` selects `--import-mode=importlib`.
- **Staged preparation already exists for math.** `tests/math/conftest.py:28–46` chains
  `spike_content` → `spike_readings` → `spike_extraction` → `spike_scoped`, and consumers request
  the stage they read. `prepare_record_source` (`tests/semantic/native_record_fixtures.py:208–277`)
  is already the pure first stage of the record source and returns a frozen `RecordPreparation`.
- **Production memoizes preparation.** `_prepare_release_cached` is an `lru_cache(maxsize=8)` on
  its hashable inputs (`src/corpus_structure/semantic/prepare.py:592–598`).

Defects at the original inspection baseline (DTA-009, DTA-018, DTA-029):

- A scenario is chosen by which fixture name a module imported. `private_source`
  (`native_record_fixtures.py:791–819`) merges a sibling fixture, `private_source_options`
  (default `:781–783`), with indirect parameters. Eleven modules override that fixture, and 26
  import lines re-export one of the public definitions so that pytest can resolve it.
  `tests/semantic/test_structural_native_replay.py:57–70` picks its source text by reading
  `request.node.callspec`.
- Test modules act as support libraries. A line search at the baseline finds about 310 import
  statements that name a `test_*` module, from 85 owner modules into 175 files (the audit counted
  266 lines at its own baseline).
- Non-package directories use relative imports: `tests/acceptance/conftest.py:3–4`,
  `tests/acceptance/test_regeneration.py:38`, `tests/orchestrate/test_data_operation_execution.py:29–30`,
  `test_data_operation_claim_source_native.py:27–33`, `test_data_operation_batch_activity.py:67–68`,
  and single-dot forms in `tests/schema/` (three files, `.lint_support`), `tests/evaluate/`
  (`test_record_policy_product.py:9`, `test_record_reference_applicability.py:20`), `tests/ingest/`
  (`test_pdf_chandra_document.py:16`, `test_definition_rules.py:20–21`, `test_pdf_visual_mapping.py:10`)
  and `tests/db/test_lifetime_native.py:34`.
- The large builders return only their end state, so a consumer that needs a persisted release
  pays for views, runs, tasks and claims.

## Target design and contracts

**Placement and import rules** (§4.3).

1. Shared builders, fixtures, recipe values and doubles live in modules whose names do not start
   with `test_`. They are imported by one canonical absolute name: `semantic.<module>`,
   `methods.<module>`, or a package-root module on `pythonpath`.
2. No module imports from a `test_*` module. No module in a non-package directory uses a relative
   import. Under importlib mode a file in a non-package directory is named from its
   rootdir-relative path, so `..semantic.X` from `tests/orchestrate/` loads `semantic/X.py` a
   second time under another name (reproduced for `tests/acceptance/conftest.py:3–4`, §7 "Import
   identity"). An absolute import of a `test_*` file in a non-package directory executes that file
   a second time in the same way.
3. Fixtures needed across directories live in the package `tests/conftest.py`: the lifecycle, the
   isolation classes and the purpose engines ([TS-05](isolation-and-seeds.md)).
4. A scenario is selected by a frozen recipe value visible where the case is declared.
5. Large builders are compositions of stages with frozen outputs. The seed boundary is the last
   stage before a claim.
6. A double that disables production verification lives in a named support module that says what
   it disables.

**Why not make every test directory a package.** It would remove the double load, but
`tests/math/` would become a top-level package named `math` on `pythonpath` and collide with the
standard library. The rules above need no new packages.

**The recipe value and its preparation projection.** A frozen, hashable dataclass fully
describes a scenario and is visible at the call site. The full recipe plus the head identifies
a seed ([TS-08](isolation-and-seeds.md)); the recipe also supplies its receipt's `scenario_seed`
label. Pure-stage reuse uses a smaller projection containing that stage's actual inputs
(TS-07), rather than fields used only by publication or task creation. Both values carry data
only, never callables, so equality is by value. This distinction lets replay cases vary text
without rebuilding the same prepared release, while still giving different complete scenarios
different seeds.

**Recipe dispatch.** TS-06 owns the rule that turns a recipe into a build. Each recipe type
has exactly one builder in a minimal support-level dispatch (`recipe type -> builder`), and the
seed operation finds the builder by the recipe's type. Named compositions and any ordinary
provider patches remain values and functions local to that recipe's support owner. For example,
the record-source builder resolves `"reference"` to its `reference_inputs` composition locally;
when it needs a provider patch, it applies that patch inside `pytest.MonkeyPatch.context()`
around the build only. There is no common composition or patch registration API. A seed's key is
therefore the recipe value plus the head; the builder is implied by the recipe type and is not
part of the key. An implementation override ([TS-03](implementation-snapshot-and-timing.md)) is
never a recipe field and is never seedable.

**Stage outputs.** Each stage returns a frozen dataclass that holds the previous stage's output
and what it added. Row snapshots are read-only mappings. A test that needs a changed field makes
a copy with `dataclasses.replace` or keeps a local variable; it does not assign to the case.

**What consumers stop doing.** Overriding or re-exporting `private_source_options`; reading
`callspec`; importing helpers from test modules; assigning attributes onto a shared case object
(`case.cut`, `case.run`, `case.task`, `case.task_row` are assigned by tests today); building a
whole scenario to read its first stage.

**Preserved guarantees.** Builders keep using real producers and real purpose logins. Builders
that are the subject of a test (native record publication, the PDF build) keep building, because
the build is their claim. `tests/semantic/test_scenario_ports.py:59–87` keeps guarding against
preparation at import. Independent expected values stay with their tests; a recipe never
generates an expected answer.

**Intentional behavior changes.** Modules that select a recipe by indirect parametrization gain
a parameter id in their test ids. This is an intentional one-time change: retry selections
stored from before it no longer match those tests and are not carried over. A test that mutated a shared case object fails with a
frozen-instance error until it copies.

## Pivotal mechanisms

| Mechanism | Use here | Limit | Reference |
|---|---|---|---|
| Canonical absolute imports on `pythonpath` | One module object per support file | Relative imports from non-package files load twice | §7 "Import identity"; pytest 9.1.1 `_pytest/pathlib.py` |
| Indirect parametrization and factory fixtures | Passing a recipe to a fixture | A module-wide parameter changes test ids | pytest documentation |
| Frozen dataclasses | Recipe values and stage outputs | Fields must be hashable for recipes; tuples in place of lists | Python standard library |
| `functools.cache` keyed by a stage's preparation recipe | Reuses input assembly before production's prepared-release cache | Ordinary worker lifetime only; TS-03 overrides bypass snapshot-dependent memo reads and writes | Python standard library; [override contract](implementation-snapshot-and-timing.md#override-validity-across-caches) |

## TS-06 — Support modules, import rules and recipe values

**Required input.** None. It shares the package conftest with TS-05; one owner should hold that
file in sequence (coordinator, shared editing surfaces).

**Implementation vision.**

*Recipe values replace fixture-name overrides.* `native_record_fixtures.py` gains
`RecordSourceRecipe` with the fields the fixture reads today at `:800–818`: the input composition
by name, `additional_methods`, `include_blank_cell`, `record_method`, `record_configuration_hash`,
`sibling_captions` and `sibling_references`. `sibling_originals` is not a recipe field: it
installs an implementation override, so its consumers keep a separate per-test fixture on a
commit-class build that holds TS-03's override for the fixture's lifetime, and that path is
never seeded. `private_source` takes the recipe as its indirect parameter and uses the default
recipe when a test passes none. The `private_source_options` fixture and its merge at `:800`
go. The overriding modules state their recipe instead:

| Module (override line) | Recipe it states |
|---|---|
| `test_interpretations_native.py:22` | The interpretations composition (bundle and dependencies transforms for statistics terminology) |
| `test_table_correspondence_native.py:40`, `test_condition_publication_native.py:77`, `test_protected_comparison_gap_native.py:70` | Characterization |
| `test_record_reading_closure_native.py:28` | Source reading |
| `test_local_semantic_admission_native.py:48`, `reference_scenarios.py:197` (re-exported to six `evaluate/` and `semantic/` modules) | Reference |
| `tests/evaluate/test_record_policy_authority_native.py:134` | The policy-authority statistics bundle, named in that test's support |
| `test_artifact_identity_registered_native.py:58` | Characterization over reference |
| `test_pm2_parser_stage_native.py:38` | `sibling_references` set to the parser samples (opt-in assets) |
| `test_structural_native_replay.py:58` | One recipe per case: `sibling_references` is the case's text, built in the parametrize list, which states directly what the `callspec` read inferred |

The existing indirect parameters (`additional_methods` in the contextual and judged tests,
`include_blank_cell` at `test_contributions_native.py:346`, `record_configuration_hash` at
`tests/evaluate/test_operation_assessment_native.py:443`) become recipe values in the same
position. A module whose every test uses one non-default recipe declares it once with a
module-level `pytestmark = pytest.mark.parametrize("private_source", [RECIPE], indirect=True,
ids=[…])`. The 26 `private_source_options as private_source_options` re-exports are
deleted.

*Minimal builder dispatch (I11).* One support module at the package tests root associates recipe
types with builders for generic seeding. It refuses duplicate associations and unknown recipe
types. Each recipe's support module supplies its association alongside the type; importing the
recipe makes its builder available. `RecordSourceRecipe`, the serving recipe (TS-08) and
`KernelRecipe` (TS-17) use that rule. Composition names and patch functions are resolved beside
the corresponding builder through ordinary local values/functions. Adding a record composition
therefore edits its owner and consumers without adding a second global registration protocol.
Reconsider a common extension API only if independently supplied scenario extensions need it;
none of the inspected consumers supplies that requirement.

*Builders leave `test_*` modules, by consumer cluster.* Each cluster moves in one change with
its importers, into a support module named for what it builds. The clusters, largest first:

| Cluster | Owners at the inspection baseline (importing files) | Notes |
|---|---|---|
| Method assembly and fixtures | `methods/test_m1_source_preparation.py` (14), `test_scoped_relations.py` (11), `test_m1_producer.py` (9), `test_record_assembly.py` (8), `test_native_evidence.py`, `test_m1_source_profile.py`, `test_pm2_source.py` | Crosses into `tests/semantic/`; TS-15 touches the same files |
| Record contracts, releases and staging | `semantic/test_record_contracts.py` (12), `test_releases.py` (8), `test_analytics.py` (8), `test_formal_evidence.py` (8), `test_proposals.py` (6) | `stage` from `test_releases.py` is used by `test_release_compatibility.py:102` |
| Execution release | `test_execution_release.py` (5): private `_bundle`, `_project`, `_stage_authored_sql` | Names become public in support |
| PDF publication and recognition | `test_pdf_publication.py` (6), `test_pdf_ocr_contracts.py` (4), `test_pdf_native_consumer_journey.py`, `ingest/test_pdf_recognition.py` (`landmark_pdf`) | Joins `pdf_acceptance_support.py` where meaning matches |
| Annotation fixtures | `ingest/test_annotations.py` (9) | A non-package owner imported by absolute name, so it loads twice today |
| Scenario builders | `test_identity_exclusions.py` (`exclusion_result`, 4), `test_structural_products.py` (4), `test_typed_structural_composition.py` (4), `test_selected_source_native.py`, `test_companion_export_native.py` | `exclusion_result` moves beside `agent_scenarios.py`; TS-10 and TS-11 seed it |
| Evaluation helpers | `evaluate/test_operation_assessment_native.py` (`freeze`, 3), `test_record_alignment.py`, `test_record_references.py`, `test_characterization_assessment.py` | Non-package owners; support goes to a package-root module |
| Review-bundle double | `test_review_bundle.py:202–208`, re-exported through `test_section_heading_replay.py:36` and imported by `test_dossier_contributions.py:26` | See below |
| DDO helpers | `test_data_operation_storage.py` (7) and four other owners | Owned by TS-17; not moved here |

Owners with one or two importers move with whichever cluster they belong to, or are inlined
where the helper is trivial. Existing support modules are extended where meaning matches; a
parallel module with a new name is not introduced for the same responsibility.

*Relative imports become canonical.* The relative imports listed in the baseline become
canonical absolute imports of support modules; the single-dot forms import helpers that move to
support in their cluster. One site is not this package's: the re-exports in
`tests/acceptance/conftest.py:3–4` and the `from semantic.conftest import … as …` lines in
`tests/evaluate/` are removed by [TS-05](isolation-and-seeds.md), which moves the commit-class
fixtures to the package conftest.

*The statistics-pack fixtures get one owner (I05).* Four modules each prepare the statistics pack in
a module fixture: `stats` in `tests/orchestrate/test_policy.py:36–38`, `prepared` in
`tests/semantic/test_interpretations.py:22–24`, `prepared` and `policy` in
`tests/schema/test_rules.py:25–32`, and `inputs` and `policy` in
`tests/semantic/test_rule_literal_bindings.py:16–23`. They become one session fixture with a
distinctive name, such as `statistics_pack_prepared`, in one support module, and the four modules
request it. Any shared dependent policy fixture also gets a distinctive name. TS-12 can group
the old module-local fixtures first using consumer-module qualifiers. The merge replaces those
rows with the distinctive shared fixture name without a qualifier, in the same change. A support
module qualifier would not match an item collected from a consumer module.

*CLI registration follows invocation (I06/W2).* Move both imports of
`corpus_structure.cli.app.app` and `corpus_structure.cli.output.CliState` from package
`tests/conftest.py:37–38` into `Cli.__call__` (`:150–155`). Importing either CLI submodule first
executes `src/corpus_structure/cli/__init__.py`, which eagerly loads the command registry; moving
only `app` would leave unconditional activation through `output`. Keep the existing `CliRunner`,
settings callable, environment handling and separate stdout/stderr behavior. Constructing the
fixture or collecting an unrelated test no longer activates the CLI through these two imports.
Other tests can still import the CLI explicitly, so this does not promise that every non-CLI
selection avoids the registry. W2 is scheduled here alongside early TS-04 work; its structural
benefit does not depend on a timing experiment. W3 argument screening remains a separate
conditional candidate under its custody contract.

*The verification-disabling double gets a named home.* `synthetic_source_projection` replaces
`review_bundle._verify_source_projections` with a function returning an empty set. It moves to
`tests/semantic/review_bundle_doubles.py`, whose docstring states that it disables source
projection verification and names the native test that covers the real check. Its three
consumers import it from there.

**Superseded machinery removed.** `private_source_options` and every override and re-export; the
`callspec` read; the four separate statistics-pack fixtures; the re-export chains between test
modules.

**Failure case this prevents.** Today, deleting the re-export at
`tests/semantic/test_review_cli_native.py:28` silently switches that module from the reference
bundle to the default bundle, and no assertion names the difference. In the target the recipe is
a value in the module; removing it is a visible edit to the scenario.

**Acceptance and closure.** By search over package and root tests (DTA-009): no import statement
names a `test_*` module; no module outside `tests/semantic/` and `tests/methods/` uses a relative
import; no `private_source_options` definition or import; no `callspec` read. The relative
import in `tests/acceptance/conftest.py` is counted with TS-05, which removes it. Every recipe
type has exactly one registered builder, and no recipe field holds a callable or an
implementation override. The DDO part of the same closure belongs to TS-17. Collection of the
whole package succeeds and `test_scenario_ports.py` still passes. A cold child process can load
package conftest for a non-CLI collection without those imports loading the command registry;
existing `cli` fixture consumers retain their settings and output behavior. Shared statistics
fixtures retain their affinity designation after the move; a same-name local fixture in an
unrelated module does not acquire it. These are planned controls, not current execution claims.

**Verification.** Per cluster: `uv run ci test -- PATH` for the moved owner and two or three of
its importers. For the recipe change: `uv run ci test --
python/corpus-structure/tests/semantic/test_structural_native_replay.py
python/corpus-structure/tests/semantic/test_review_cli_native.py`.
For the lazy imports, use the existing conftest/CLI harness to check a cold non-CLI collection
and representative `cli` consumers, observing imported modules rather than asserting duration.

**Original implementation premises (current dispositions: coordinator).** Whether any double-loaded module's duplicated state changes a result was not
established; the rules remove the question.

## TS-07 — Staged builders, focused consumers and the recipe memo

**Required input.** TS-06 (recipe values and support placement), TS-03's implemented
[override-validity contract](implementation-snapshot-and-timing.md#override-validity-across-caches)
before memo reuse, and TS-05 (the commit-class fixtures and `commit_clone()`, which the
second-database consumer below uses).

**Implementation vision.** Three builders become stage functions in their existing modules. The
full builder stays as the composition of its stages, so no consumer has to change until it wants
an earlier stage. Line ranges are today's code for each stage.

`build_record_source` (`tests/semantic/native_record_fixtures.py:292–646`):

| Stage | At the inspection baseline | Adds to the output | Notes |
|---|---|---|---|
| Prepared | `:309–397`, over `prepare_record_source` | Bundle, dependencies, profile, prepared release | Pure. The `sibling_originals` patch (`:387`) is not part of the recipe path: it stays in the per-test fixture that holds TS-03's override |
| Release persisted | `:398–416` | Project and input realization | Admin commit |
| Source published | `:434–593` | Document, run, source task, native product, two source views | Claims the source task at `:499` and completes it; nothing stays leased. Writes `source.pdf` and the `native` spool under the builder's directory (`:479`, `:510`) |
| Record task created | `:594–615` | Record method, configuration and task | **Seed boundary** |
| Record task claimed | `:616–628` | `held`, `view_row`, `task_row` | Runs in the consumer's clone or case transaction |

`build_domain_case` (`tests/semantic/domain_scenarios.py:65–651`):

| Stage | At the inspection baseline | Options that affect it |
|---|---|---|
| Release | `:96–199`, plus prior knowledge `:200–233` when `known` | `rules`, `graph`, `known`, `input_noise`, `nary`, `broken`, `formulas`, `global_person_identity`, `integer_alias`, `incomplete_key`, `membership_subtype`, `characterization` |
| Views and run | `:234–267` | `duplicate`, `statement_packets` |
| Method and task | `:268–302` | `math` |
| Claimed and framed | `:303–306` | — |
| Proposal | `:307–478`, pure | `local_known`, `claim_chain`, `cycle`, `condition`, `authored_alternative`, `isolated_entity`, `attribute_assertions` |
| Completed and sealed | `:479–568` | `report_count`, `second_math` |
| Foreign run | `:569–650` | `unselected_report` |

The case ends with every task complete, so the whole case is seedable; the release-and-views
prefix is the alternative boundary, and [TS-11](isolation-and-seeds.md) chooses between them
by dependency and reuse inspection, as recorded in TS-11.

`build_resubmission_case` (`tests/semantic/agent_scenarios.py:36–174`):

| Stage | At the inspection baseline |
|---|---|
| Prepared | `:49–95`, pure |
| Release persisted | `:96–109`, with `activate_release` when composed |
| Document and run | `:110–153`; writes the controlled PDF at `path` |
| Views published | `:154–161`; an internal ingest claim is completed |
| Primary bound and agent queued | `:162–173`; the agent task is unleased until `queue_next` |

`exclusion_result`, once in support, is this composition plus a proposal stage, then sealed or
finalized.

**Focused consumers** (DTA-018) request the stage they read:

| Consumer | Builds at the inspection baseline | Requests in the target |
|---|---|---|
| `tests/evaluate/test_record_policy_native.py:15–47` and the test at `:49` | The full `private_source` | The release-persisted stage and authored candidates; `eval.record_policy_full_correct` reads its arguments and one `sem.artifact` row |
| `tests/semantic/test_cli_failures.py:228–239` | A full composed resubmission case, keeping only `prepared` | The release-persisted stage of the composed recipe |
| `tests/semantic/test_release_compatibility.py:92–123` | A second database by replaying the whole chain through `semantic_database_at("head")` (`tests/semantic/conftest.py:48–57`) | Two commit-class clones of the head (`commit_db_engine` and `commit_clone()`), which are the same deployment. Other users of `semantic_database_at` target real revisions and keep the replay |
| `tests/ingest/test_pdf_recognition.py:381–417` | Its owner through a helper that skips when the isolated parser environment is absent (`:166–172`) | Constructs the owner without the isolated runtime, once reading `RecognitionWorker` confirms construction does not validate it; otherwise the prerequisite becomes a marker ([TS-13](evidence-contracts.md)) |
| Provider opt-in tests that skip in the body after fixtures ran | Clone, release, PDF and source before the skip | Owned by TS-13 |

The DDO forged-graph family, which builds more than the demand it reads, is TS-18's.

**Preparation-recipe memo (I03).** Production's eight-entry cache is keyed by assembled inputs,
so a call still assembles and hashes the bundle before lookup. Support reuses that assembly
through a small `RecordPreparationRecipe(composition, additional_methods)`, projected from
`RecordSourceRecipe` before calling the pure `prepare_record_source`. The composition name
selects the locally owned bundle/dependency transforms; `additional_methods` supplies its method
extension tuple. These are precisely the varying arguments of the inspected pure function
(`native_record_fixtures.py:208–277`). Publication text (`sibling_captions` and
`sibling_references`), blank-cell choices, task method and task configuration remain in the full
scenario recipe but are absent from this preparation key. The full recipe plus head remains
the seed key: sharing preparation never equates distinct persisted scenarios.

One ordinary worker-local memo maps that projection to the frozen `RecordPreparation`, holding
values for the worker's life. The other two builders gain preparation reuse only for a meaningful
shared pure prefix, keyed by the inputs that prefix actually consumes; their later-stage fields
are not automatically added to a cache key. No dependency-tracking framework or blanket
whole-recipe memo is introduced. Production's prepared-release cache remains independently
keyed by its explicit bundle, dependencies, profile and compiler stack.

Before consulting the support memo, its wrapper checks `implementation_overridden()`. Under an
override it computes the pure stage afresh, bypassing both reads and writes; normal warm entries
remain untouched. This applies to any support prefix whose assembly acquires installed
implementation inputs. TS-03 owns the affected context and parser-result caches and the nested,
exception-safe lifetime. Persisting a release, writing PDFs/spools, publication, task creation
and claims remain effectful stages outside this memo, fresh for the selected isolation contract.
Independent expected results remain authored by the tests.

**Consumers migrated.** The four focused consumers above; `private_source`, which composes the
stages; the builders' call sites are unchanged unless they adopt an earlier stage.

**Superseded machinery removed.** The `SimpleNamespace` results of `build_record_source` and
`curated_case`; assignments onto case objects; the `semantic_database_at("head")` use in
`test_release_compatibility.py`.

**Acceptance and closure.** The named consumers request only what they read (DTA-018). Each
builder's full composition returns what it returned before, shown by its existing consumers
passing unchanged. A stage output cannot be assigned to. Replay recipes differing only in
later-stage text acquire the same ordinary preparation once; changed composition or methods
acquire another. Their effectful stages still run independently. With ordinary preparation warm,
nested overrides that keep profile identifiers unchanged neither read that preparation nor
write to its ordinary memo; exceptional exit restores ordinary reuse. TS-03 supplies the matching
parser/context controls, so a support-only counter is insufficient to establish the whole scope.

**Verification.** `uv run ci test -- python/corpus-structure/tests/evaluate/test_record_policy_native.py
python/corpus-structure/tests/semantic/test_cli_failures.py
python/corpus-structure/tests/semantic/test_release_compatibility.py`, then one integrated
consumer per builder (`test_record_publication_native.py`, `test_domain_operations.py`,
`test_runtime_entrypoints.py`).

**Resolved during execution (2026-11-13).** Task creation stores `invocation_key` before
claim; the frozen pre-claim descriptor retains it and validates the queued task posture.
Claim-time rows still belong to the claimed stage. The record-policy consumers use only
persisted release inputs and authored candidates; they no longer publish PDFs or claim tasks.
The selected domain boundaries are the whole exact-default case and the formula-capability
release/views prefix, without a mandatory timing profile.

## TS-15 — One owner of the primary-layer assembly

**Required input.** None.

**Implementation vision.** The sequence that turns a controlled annotation into a native primary
layer is written out in seven places: construct `NativeEvidenceBuilder`, call
`native.spacy(...)`, build `native_run("spacy", …)`, attach availability rows, finish.

| Copy | Lines | Digest at the inspection baseline | Availability rows |
|---|---|---|---|
| `tests/methods/primary_reading_fixture.py` (`primary_product`) | `:140–167` | Overwritten with the pipeline digest (`:155`) | Mapped through `SPACY_COLUMNS` |
| `tests/methods/navigation_fixture.py` | `:56–93` | Pipeline (`:78`) | `SPACY_COLUMNS` |
| `tests/native_math_primary.py` | `:84–127` | Pipeline (`:118`) | `SPACY_COLUMNS` |
| `tests/methods/test_math_scope_primary.py` | `:82–109` | Derived by `native_run` | `SPACY_COLUMNS` |
| `tests/methods/test_construction_named.py` | `:93–116` | Derived | `SPACY_COLUMNS` |
| `tests/methods/test_m1_producer.py` | `:189–219` | Derived | `SPACY_COLUMNS` |
| `tests/methods/test_primary_reading_consumers.py` | `:116–157` | Derived | Production's `_availability(native, "spacy")` (`:155`) |

`native_run` derives `configuration_digest` from the configuration text
(`src/corpus_structure/methods/native_evidence.py:119`). The copies restate how production
assembles the layer, so they are parallel setup, not independent expectations, and a reader
cannot tell intended variation from drift.

One function in a support module of the `methods` package (importable as `methods.<module>` from
the package-root `native_math_primary.py` as well) owns the native half. Its arguments are the
things the copies vary: views and products, operation and profile, configuration text, reference
numbers, the prepared release, and a required keyword `digest` with two values, `"pipeline"` and
`"derived"`. There is no default, so the digest choice is visible at each call site. The
availability mapping is one choice inside the owner; the seventh copy's use of the production
helper is reconciled when it moves, by checking that both forms give the same rows for its inputs.

**Consumers migrated.** The seven copies call the owner. The eight files that already use
`primary_product` are unchanged. Not in the footprint: `tests/methods/test_native_evidence.py`,
whose subject is the builder itself, `test_contextual_characterization.py:46–57`, and the HanLP
path in `test_definition_declaration_primary.py`.

**Acceptance and closure.** The seven copies call one owner with an explicit digest policy
(DTA-029). Each consumer's existing tests pass with the digest it used before.

**Verification.** `uv run ci test -- python/corpus-structure/tests/methods/test_math_scope_primary.py
python/corpus-structure/tests/methods/test_construction_named.py
python/corpus-structure/tests/methods/test_m1_producer.py
python/corpus-structure/tests/methods/test_primary_reading_consumers.py`.

**Original implementation premise (current disposition: coordinator).** Which differences between copies other than the digest are intended was not
established for every site. Each surviving difference becomes an explicit argument; a difference
with no consumer that depends on it is removed.

## Outside this companion

- The isolation-class fixtures, the seed operation and which recipes are seeded:
  [isolation classes and scenario seeds](isolation-and-seeds.md) (TS-05, TS-08, TS-10, TS-11).
- Prerequisite markers for provider and asset opt-ins: [evidence contracts](evidence-contracts.md) (TS-13).
- DDO declaration builders, `KernelRecipe`, `admit_kernel` and the DDO import closure:
  [data-operations test alignment](data-operations-test-alignment.md) (TS-17).
- Affinity groups for designated preparation and for rollback families:
  [run shape and scheduling](run-shape-and-scheduling.md) (TS-12).
- The two module-level `prepare_release` bindings the audit notes
  (`tests/semantic/test_prepare.py:584`, `test_projection_analysis_products.py:124`) are not in
  this series' scope.
