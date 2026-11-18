# Declarations, retirement and execution: fixture declarations, SQL from its owner, and the host lock

**Status:** In execution. Fixture declarations, reusable SQL subjects and private lock controls are implemented.
**Created:** 2026-11-17. **Revised:** 2026-11-18. Writing this plan authorizes no implementation.

This companion owns the designs of **TDM-15** (preparation declarations at the fixture and the
`db` mark from the native root), **TDM-16** (production SQL obtained from its owner and checked in
the cheapest class that still tests the deployment) and **TDM-17** (the ordinary-lane host test
without the real GPU lock). It contributes to findings
[DTA-037](../../design_review/test-audit/retirement-transfer.md#dta-037),
[DTA-047](../../design_review/test-audit/execution-and-qualification.md#dta-047) and
[DTA-048](../../design_review/test-audit/execution-and-qualification.md#dta-048), depends on rule
changes RC09 and RC10, which the operator accepted on 2026-11-17, and states the
[retirement rules](#retirement-rules) that later changes follow. Package state, the queue,
finding dispositions, shared contracts, deferrals, rejected options and external context are the
[coordinator's](../test-domain-model-and-execution_2026-11-17.md).

**Baseline and evidence.** Section references such as §4.5 mean the
[design review of 2026-11-17](../../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
which read source at `1afa63f88`. The series was authored at `50827eb9f` and revised at
`12f57dc4d`, 2026-11-18, after the model-owned SQL conversion (ADR-0131) was complete and while
its validation was running. Source facts were re-read in a frozen export of `12f57dc4d` and are
**Interface-checked by source inspection, 2026-11-18**, with line citations as of that commit; the
library facts were not re-read and keep their 2026-11-17 label. Nothing was run; where this
document says a test cannot set up or pass, that is by reading, not run. Every design statement
is **Proposed**. No speedup is claimed. The investigation reports this companion draws on are in
the evidence folder `docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../../design_review/evidence/2026-11-17_test-plan-authoring/state.md), for the
revision the
[boundaries re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-boundaries.md),
and the
[library capability notes](../../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md), which read the installed pytest
9.1.1 and pytest-xdist 3.8.0; one library fact is marked there as inferred from source and not
documented, and confirming it is the first step of TDM-15. `tests/…` and `src/…` are relative to
`python/corpus-structure/`; repository-root paths are written as root `conftest.py` and root
`scripts/…`. The review did not read the root `tests/` tree. The revision's export contains it,
and it was scanned for fixture definitions and for the names in the two lists.

**Integrated improvement review.** Recommendations
[I04](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I04) and
[I05](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I05), reviewed
at `aea554e5c`, replace the name registry with item-resolved metadata and refine evidence and
retirement below. The earlier source and library observations retain their original scope.

## Why this work exists

Three things in the test system are stated in one place and true in another.

1. **Which fixtures need the database, and which share a worker, are two hand-kept lists of
   names.** Fixtures were retired and the lists were not, so most of their entries now name
   nothing (DTA-037). The lists also cannot say anything about a fixture added tomorrow.
2. **Tests read production SQL as text from files, and expression checks create a whole
   database for each case although they write nothing** (DTA-047). The model-owned SQL conversion
   (ADR-0131) deleted eleven of those files and moved most of their readers onto the generators.
   Ten test modules still read production SQL by path, two tests cannot pass by reading because
   the file each depends on is gone, and the number of test files that create a database per case
   rose from 45 to 61, because the conversion's own new tests install generated programs that
   way.
3. **One ordinary test takes the operator's real host-wide GPU lock** and fails, with a message
   blaming the wrong cause, when a real capture is running on the workstation (DTA-048).

The common remedy is the review's §4.6: nothing should name machinery by hand at a distance. A
declaration lives on the thing it describes; a test's subject is obtained from its owner by
import or by its installed name. Then retiring a mechanism breaks its dependents at the moment of
retirement, visibly, and no separate checker is needed to notice.

**What this companion consumes.** The isolation-class fixtures of the earlier test-system plan
(`native_read`, `native_rollback`, the commit and infrastructure fixtures; ADR-0101), which are
kept; the record of RC09 and the superseding record for ADR-0101 that carries RC10, both from
TDM-00; TDM-00's re-read of changes after `12f57dc4d`; and the test helper the conversion added
for selecting one routine from a generated program
(`tests/semantic/native_program_support.py`), which TDM-16 extends.

**What it produces.** A `db` mark and worker groups that follow the fixture graph; no hand list;
no test that reads production SQL by path or cuts it by text; expression checks that run against
installed objects without a database per case; and an ordinary host test that cannot be failed by
another process.

**Where its responsibility ends.** The single test that requests a fixture defined nowhere, the
reader of a deleted file and the test that patches a read production no longer performs are
repaired first by TDM-01 (coordinator), because they are evidence that is absent today; this companion gives their final form. What a generated-SQL test should
*assert* (meaning rather than renderer spelling) is TDM-05's
([model binding and independence](model-binding-and-independence.md)); TDM-16 decides only where a
test's SQL comes from and which class it runs in. The refusal contract for the checks TDM-16
rewrites is TDM-14's ([reuse and refusal evidence](reuse-and-refusal-evidence.md)).

## Baseline at `12f57dc4d`

### The two lists (DTA-037)

- **Worker groups.** Root `conftest.py:10–57` holds `PREPARATION_AFFINITY`, 37 rows of fixture
  name, optional consumer path and group. A collection hook intersects it with each item's fixture
  closure, refuses an item that falls into two groups (`:72–75`) and adds one `xdist_group` mark
  (`:91–98`). Of the 37 rows, 23 name a fixture defined nowhere in the package tests, the root
  `tests/` tree, the root scripts or the root conftest (scan of every fixture definition in all
  four). One more is dead in effect: the row that qualifies
  `native_read` by `tests/semantic/test_contextual_workflow_native.py` (`:37–41`) names a module
  that does not request `native_read` (search of that file, by reading). Thirteen rows are live:
  six session-scoped mathematics fixtures (`tests/math/conftest.py:34–64`), three statistics-pack
  fixtures (`tests/statistics_pack_support.py:10–25`), `profile` qualified to
  `tests/semantic/test_hanlp_products.py` (`:35`), `local_semantic_sql_batch`
  (`tests/semantic/test_local_semantic_admission.py:184`), and two rollback-family fixtures,
  `binding_native_connection` (`tests/semantic/data_operation_binding_support.py:118`) and
  `selected_graph_case` (`tests/semantic/test_data_operation_storage.py:2464`).
- **The `db` mark.** `tests/conftest.py:101–142` holds `DB_FIXTURES`, 38 names, and a hook marks
  any item whose closure intersects it (`:279–282`). Eleven names are defined nowhere. Six more
  are the `record_source_*` fixtures (`:533–569`); five of them depend on `private_source`, which
  is defined nowhere, the sixth depends on one of the five, and no test requests any of them. The
  mark matters: the qualification plugin reports marked items as requiring the native server and
  records every item's groups (root `scripts/qualification_plugin.py:222–243`).
- **Every live native fixture reaches one root.** `native_server` (`tests/conftest.py:395–406`)
  is a dependency, direct or transitive, of every defined name in `DB_FIXTURES` (read of
  `tests/conftest.py:388–579` and `tests/native_fixture_support.py`). `native_settings` (`:337–340`)
  is deliberately not native: it only captures environment settings.
- **Explicit marks are common.** 58 `pytest.mark.db` decorations or module marks in 21 test files
  state the dependency at the test; one of them arrived with a test the conversion added. Three modules state an `xdist_group` at module level.
- **Seven dynamic requests.** A fixture requested through `request.getfixturevalue` is not in the
  closure pytest computes, so no derivation from the closure can see it. The complete list:

| Site | What it requests | Is the native root already static? | Why it is dynamic |
|---|---|---|---|
| `tests/conftest.py:505`, inside `observed_store_checkouts` | `infrastructure_engine` | Not through this fixture; its eight consumers in `tests/db/test_store.py` and `test_lifetime_native.py` use `usefixtures` and, where read, also name `infrastructure_engine` | No reason found |
| `tests/test_db_fixtures.py:130` | `infrastructure_commit_engine` | Yes, the test names `native_server` | The test first replaces `semantic_ready` and `deployment_key` with functions that fail, then acquires; the order is the claim |
| `tests/semantic/test_runtime_principal_current_native.py:21` | One of four `commit_*_engine` fixtures chosen by parameter | Yes, `commit_db_engine` | Selection by parameter |
| `tests/semantic/test_native_fixtures.py:164` | One of four `commit_*_engine` fixtures chosen by parameter | No; the test carries `@pytest.mark.db` (`:149`) | Selection by parameter |
| `tests/semantic/test_native_fixtures.py:548–550`, inside `captured_semantic_engines` | `native_server`, `semantic_head_template`, `native_settings` | No; its consumer carries `@pytest.mark.db` (`:562`) | The requests must happen after receipt capture is active; the comment says so |

- **Dead modules and one dangling request.** Four support modules under `tests/semantic/` have no
  importer (`scenario_preparation_support.py`, `primary_formal_fixture.py`,
  `method_dimensions_native_support.py`, `characterization_construction_support.py`).
  `tests/semantic/test_source_routing.py:9–12` requests `domain_default_case`, which is defined
  nowhere, so by reading it fails at setup. An exhaustive comparison of requested fixture names
  with defined fixtures over 930 files found exactly one other undefined request, the `db`
  fixture of `tests/test_native_refusals.py`, which the coordinator's TDM-01 owns.
- **The root tree holds nothing parallel.** The root `tests/` tree has no second list, no live
  fixture declaration and no reference to either list. Root `scripts/qualification_plugin.py` and
  `scripts/test_receipts.py` only read marks, and root `tests/scripts/test_parallel_harness.py`
  uses explicit `db` and `xdist_group` marks.

**Delivered by the conversion:** nothing. Root `conftest.py`, `tests/conftest.py`,
`tests/native_fixture_support.py`, the mathematics and statistics fixture modules and the
qualification plugin are unchanged since the authoring baseline, and the counts above are the
same apart from the moved line and the explicit-mark count. The conversion added ten fixtures
(`product_connection`, `read_boundary_control`, `release_guard_context`,
`event_scope_connection`, `adoption`, `generated_companion_reads`, `validation_controls`,
`feature_body_control`, `source_capture_control` and `support_control`). Each is built on
`semantic_bare_engine`, `native_rollback` or the already grouped `binding_native_connection`, and
none declares a group or needs one.

### Production SQL read as text (DTA-047)

**Delivered by the conversion.** Sixteen hand-written files remain in
`src/corpus_structure/semantic/sql/`, against 27 at the authoring baseline. The eleven deleted in
between include `data_operations.sql` (`2910d9817`), the file most readers cut by anchor text.
Ten of the nineteen modules that read production SQL by path at the authoring baseline now import
the generator that owns their subject (for example `d422c48e7` and `a727a9878`): the
trust-snapshot, selected-graph, execution-guard, replicate-policy, JSON-meaning and
record-policy-predicate checks, the population-selection check, and the three PDF record checks.
An eleventh, `test_data_operation_storage.py:72`, was found not to be a read. Both tests whose
anchors were absent were rewritten in that move, so they no longer fail on a missing anchor. The
source half of this package is therefore mostly delivered. The class half is not: each of those
moved checks still creates a database per case, and the conversion's new tests added more.

**Path readers that remain.** Ten test modules read production SQL by path at `12f57dc4d`:

| Module (all `tests/semantic/`) | What it reads | State |
|---|---|---|
| `test_native_sql_body.py:202–217` | `closure.sql`, which exists, and `execution_projection_check.sql`, which was deleted before the authoring baseline | `FileNotFoundError`, by reading; TDM-01 repairs it |
| `test_native_closure.py:268–290` | Replaces `Path.read_text` for the name `pdf_record_context.sql`, deleted in `5341e93dd`, and then calls `function_bodies(publication_sql())` | New since the authoring baseline. Production no longer reads that file (`publication_sql` builds from `pdf_record_context_sql(metadata)`), so the replacement never fires and, by reading, the test's `'changed_descriptor'` assertion fails; TDM-01 repairs it |
| `test_data_operation_retirement_context_sql.py:21–36` | `data_operation_task_checks.sql` by path, then four `source.index(…)` cuts of the output of `target_task_guard_sql` | The only reader that still cuts by anchor text; works |
| `test_data_operation_protocol_values.py:151` | `data_operation_task_checks.sql` | Works |
| `test_data_operation_cpu_basis.py:68–83` | `closure.sql` and `identity.sql` | Works |
| `test_data_product_admission_programs.py:27`, `test_pdf_validation_read_native.py:64–66` | `identity.sql` | New test files from the conversion; work |
| `test_data_operation_identity_native.py:56–58` | `data_operation_identity.sql`, which no production module loads | Works while the file exists |
| `test_target_installation.py:161` | `source_record_recognition.sql` | Works |
| `test_data_operation_constraint_custody.py:94–95` | `admission.sql`, and `source_record_graph.sql`, which no production module loads | Works while the files exist |

`test_native_release_guards.py:142` reads a frozen, digest-pinned migration artifact under
`target_alembic/versions/`, not a file of the production SQL directory; that artifact is its
subject and the test is outside this package.

**Files without a loader.** Six of the sixteen remaining files have no loader in `src/`:
`exclusions.sql`, `fact.sql`, `selection.sql`, `validation.sql`, `source_record_graph.sql` and
`data_operation_identity.sql`. They are plausibly superseded production machinery and are a row
of the coordinator's [production context](../test-domain-model-and-execution_2026-11-17.md#handovers),
not scope here; the two tests that read two of them are scope.

**The target is now common.** Many tests take their subject from its owner. Besides the three the
authoring baseline named (`test_data_operation_runtime.py`, `test_source_metadata_codec_native.py`
and `test_target_installation.py`), the conversion added a helper,
`routine_declaration(source, schema, name, *, temporary=True)`
(`tests/semantic/native_program_support.py:7`), which parses a generated program, selects one
routine by schema and name and can rename it into `pg_temp`. Used with the existing isolation
fixtures it is the good route this package extends: `test_support_trust_native.py` executes the
generator's program on the grouped rollback family, `test_data_operation_compiler_native.py` has
fourteen cases on `native_rollback`, `test_data_operation_identity_native.py:24, 46` calls the
installed function on `native_read`, and `test_pdf_freeze_programs.py`,
`test_pdf_publication_controls.py` and `test_pdf_validation_seal_programs.py` use commit clones
with `native_rollback`.

**`function_bodies` stays.** It has four production callers (`native_products.py:288`,
`native_authoring.py:826`, `execution_admission.py:396`, `native_admission.py:445`; definition at
`native_products.py:308`). Its remaining test users pass it generated programs, apart from the
two broken tests above.

**One database per case.** `semantic_bare_engine` (`tests/native_fixture_support.py:29–38`)
creates a database from the server template for each test. Its module says it exists for
bootstrap and historical-upgrade obligations (`:1–5`). 61 files use it at `12f57dc4d`, in 107
direct requests (88 by tests, 19 by fixtures); 45 files did at the authoring baseline. All
sixteen files added to that count are conversion tests that install generated programs into a
fresh database per case: `test_data_operation_read_native`, `test_data_product_admission_programs`,
`test_data_read_boundary_native`, `test_native_parameter_defaults`,
`test_native_program_table_outputs`, `test_native_refusal_detail`, `test_native_release_guards`,
`test_operation_event_programs`, `test_pdf_companion_adoption_programs`,
`test_pdf_companion_read_native`, `test_pdf_record_event_queries`,
`test_pdf_validation_read_native`, `test_record_policy_native_access`,
`test_selected_source_search`, `test_source_capture_native` and `test_support_trust_native`. The
expression checks the audit names are all still on that class, including those whose source the
conversion corrected: the trust-snapshot module, whose fixture `snapshot_connection`
(`test_data_operation_trust_snapshot_sql.py:16–31`) creates an `ops` schema in the bare database
and installs `ddo_trust_snapshot_meaning` there under its real name; the selected-graph,
execution-guard, replicate-policy and record-policy-predicate checks;
`test_data_operation_retirement_context_sql.py`; `test_data_operation_null_scope.py`, a pure
PostgreSQL expression check that touches no semantic object; and `cpu_basis_connection`
(`test_data_operation_cpu_basis.py:61–90`), which builds six relations by hand without foreign
keys and is imported by three other modules (`test_cpu_authority_reply_native.py`,
`test_rich_admission_native.py`, `test_established_validity_native.py`).
`test_source_metadata_codec_native.py:15–28` still takes its program from the generator and then
installs it into a fresh bare database per case to call one pure function. No test moved to
`native_read`, `native_rollback` or `infrastructure_rollback` in the interval.

### The host lock (DTA-048)

`test_residency_hands_off_actual_gpu_capacity_and_restarts_real_host`
(`tests/methods/test_native_host.py:716–752`) declares a residency over a real peer process,
infers once, enters `residency.external_gpu`, asserts that the first host's process group is no
longer live (`:738`), and then enters the real `pdf_gpu_slot` under a two-second deadline whose
failure message is "previous NLP group retained PDF GPU capacity" (`:739–745`). The slot is an
exclusive `flock` on `/tmp/corpus-structure-pdf-gpu-<uid>.lock`
(`src/corpus_structure/ingest/pdf_capacity.py:42–64`), the lock every real capture on the host
holds. The native host group does not take that lock (search of `src/` for the slot's callers:
PDF recognition and visual requests only), so acquiring it shows nothing about the group. It shows
only that no other process on the workstation is capturing. The slot's own tests cover quarantine
after an uncertain retirement with the lock calls replaced
(`tests/ingest/test_pdf_capacity.py:106–127`); no test covers waiting on a held lock or the order
in which the slot borrows the GPU from resident hosts and then locks.

**Delivered by the conversion:** nothing. Both files and the capacity module are unchanged since
the authoring baseline.

## Target design

### Declarations follow the fixture graph (TDM-15)

**The `db` mark derives from one name.** An item is marked when `native_server` is in its fixture
closure. The 38-name list becomes that one name, and its dead entries disappear with it. An
explicit `pytest.mark.db` on a test or module remains a valid declaration and is how a test with a
deliberately dynamic request states its dependency.

**Dynamic requests are for claims about order.** The review proposed that all seven become static
dependencies (§4.5). Reading them refines that: in three sites the dynamic request is the test's
claim or serves a parameter choice with the native root already static, and making them static
would either destroy the claim or acquire engines the case does not use. The rule is therefore:
a native fixture is requested dynamically only where the order of acquisition is what the test
asserts or where a parameter selects among fixtures; such a test either names the native root as
an ordinary parameter or carries the explicit mark. Every other dynamic request becomes a
parameter.

**A worker group is declared where the fixture is defined.** A small project decorator wraps
`pytest.fixture`, passes through scope, name and parameters, and attaches affinity metadata to
the defining fixture function. The root hook reads metadata only from definitions resolved for
the collected item. Same-name fixtures in sibling scopes and child overrides remain valid. A
parent definition contributes only where the override actually requests that parent.

One narrow adapter owns access to pytest 9.1.1's internal resolved-fixture information and checks
its supported version and shape. An unsupported or unrepresentable resolution receives an
explicit diagnostic and uses a public explicit declaration on the affected test where needed.
The implementation must establish root/package parity and hook order before depending on the
adapter. No mutable global fixture-name registry is introduced.

The hook combines the resolved fixture groups with explicit `xdist_group` declarations. Matching
names coalesce into one group. Distinct groups produce a collection usage error naming the item
and contributing definitions. Emit exactly one group mark before xdist processes it. A dynamic
`getfixturevalue` dependency that needs affinity declares its preparation prerequisite on the
owning fixture explicitly, since static resolution cannot infer that runtime dependency.

**Which fixtures declare a group** is unchanged policy, carried from the earlier review: session
and module fixtures that hold expensive shared pure preparation, and rollback families, are
grouped; commit-class consumers of a seed are not, because grouping them would serialize real test
bodies onto one worker. This package moves the thirteen live rows and adds a declaration for the
one rollback-family fixture the table never listed (`policy_projection_connection`,
`tests/semantic/test_record_policy_completion_native.py:79`). It does not go looking for new
groups, and none of the ten fixtures the conversion added needs one.

**Alternatives rejected.**

- *Correct the two lists by hand.* They drift again at the next retirement; this is how DTA-030
  became DTA-037.
- *Carry the group as a mark on a fixture parameter* (`pytest.param(..., marks=…)`). It changes
  every consumer's node identity, and xdist joins several group marks into a new group silently.
- *Use a global registry keyed by fixture name.* It loses item-level override resolution and
  rejects valid sibling definitions. Keeping one version-checked adapter limits the internal
  pytest dependency to the responsibility that needs it.
- *A check that every listed name exists.* It is a lint over a list that should not exist.

### SQL from its owner, in the class that tests the deployment (TDM-16)

Two questions are separate for each check: where the SQL under test comes from, and what database
state the check runs against.

**Source.** A test never opens a production `.sql` file and never derives a fragment from
production text by searching it. It obtains its subject in one of two ways:

- *by installed name*: it calls the function, or exercises the trigger or constraint, that the
  deployment installed, on a database cloned from the head;
- *by import from the owner*: it imports the generator or builder that produces the program or
  expression and uses what that returns. Where the check needs one routine of a generated
  program, `routine_declaration` selects it from the generator's output by schema and name.

A guard that exists only as lines inside a function body has no name of its own. Its behaviour is
tested through the function that contains it. Where the owner exports the guard as a named expression builder,
as the conversion did for the selected-dependency predicate (`dependency_selection_differs`) and
the execution-evidence guard (`execution_evidence_differs`), a test may import that; a test does
not recreate one by cutting text.

**Class.** The route follows from what the claim needs, cheapest first:

| The check needs | Route | Why |
|---|---|---|
| To call an installed function with literal arguments, or to read the catalog | The read class: `native_read`, a read-only transaction on the worker's session clone of the head, rolled back | It tests the object the deployment installed, with its owner, grants and search path, and creates no database. The review prefers it for that reason (§5.2) |
| Rows, temporary objects, or a statement obtained from a generator installed for the duration of the case, on the real schema | The rollback class: `native_rollback` on the session clone, or a rollback family of the smallest existing seed when the case needs a prepared scenario | Still the deployed schema with its keys, triggers and grants; one transaction per case, no database per case |
| Only PostgreSQL itself: how an expression, a bind type or a standalone program that references no semantic object evaluates | A rolled-back infrastructure connection: `infrastructure_rollback` on the worker's clone of the server template | RC10. There is no deployed object in the claim, so a semantic head would add nothing; the check may install temporary objects and writes nothing durable |
| A bare or partly migrated database as the claim | `semantic_bare_engine` and the revision fixtures, unchanged | Bootstrap and upgrade obligations |

**Where each route is right.** The read class is the default for anything installed, and it is the
right route even when the infrastructure connection would be cheaper, because the audit's
complaint was not only cost: a test named `_native` that runs a re-cut fragment on a substitute
relation cannot see a defect in how deployment installs the function, or in anything outside the
fragment. The infrastructure route is right only when the subject is not a deployed object at
all. `tests/semantic/test_data_operation_null_scope.py` is the model case: it evaluates a
production SQLAlchemy bind type and comparison against literal JSON values and touches no semantic
relation. A test on the infrastructure route does not claim "native" in its name. The read class
has one limit to respect: a read-only transaction refuses a write with `25006` before PostgreSQL
checks privileges, so a claim about a privilege refusal of a write belongs to the rollback class.

**Cases the deployed schema forbids.** Some checks feed a function rows that the deployed keys and
triggers would refuse, for example a historical state. `cpu_basis_connection` builds relations
without foreign keys for this reason. Such a case keeps a substitute schema, with two changes: its
programs come from their owners by import, and the substitute is built once for the module and
used through rolled-back transactions instead of once per case. The package's evidence names each
such case and what the deployed schema forbids; a case that can be expressed on the deployed
schema moves to the rollback class.

**Alternatives rejected.**

- *Move every expression check to the infrastructure connection.* Cheapest, and allowed by RC10,
  but it keeps testing a fragment instead of the deployment for subjects that are installed.
- *Keep the per-case bare database and only change the source.* It fixes orphaning and keeps a
  database per case for checks that write nothing.
- *Parse the file and select the function structurally* (pglast instead of anchor text). The
  reader survives reformatting and is still orphaned when the file is deleted. Selecting a
  routine structurally from a generator's output, as `routine_declaration` does, has no such
  weakness, because the generator is imported.

### The ordinary host test without the real lock (TDM-17)

The test keeps what it establishes about the residency: inside `external_gpu` the previous host's
process group is gone, and the next inference starts a new host with a new generation. It stops
entering the real slot, and its name stops saying it hands off actual GPU capacity.

The claim the slot acquisition was meant to support, that the resident hosts are retired before
the slot's lock is taken, is a property of how `pdf_gpu_slot` is composed, and is tested there
without the host-wide lock: one control records that the borrow from resident hosts is entered
before the lock call, and one control exercises the real `flock` call on a private file, holding
the lock on a second descriptor and observing that the slot keeps polling its liveness callback
until the holder releases. The existing quarantine control stays.

The lock path is built inside the function from `Path("/tmp")` and opened with `os.open`
(`src/corpus_structure/ingest/pdf_capacity.py:51–52`). Replacing `os.open` would affect every
caller in the process, so the control instead redirects the lock path by replacing the
module-level `Path` name in `corpus_structure.ingest.pdf_capacity` for the duration of the
control, so that `/tmp` resolves to the test's temporary directory. A module constant or
parameter would be the natural seam; that is a row of the coordinator's
[production context](../test-domain-model-and-execution_2026-11-17.md#handovers), not scope here.

## Pivotal library capabilities

| Capability | API | What the design relies on | Limit | Reference |
|---|---|---|---|---|
| Fixture closure per item | `item.fixturenames` in `pytest_collection_modifyitems` | It contains parameters, `usefixtures` and autouse fixtures with all their transitive dependencies | Fixtures requested through `request.getfixturevalue` are absent | pytest 9.1.1 `_pytest/fixtures.py`, `FuncFixtureInfo` docstring (`:399–412`), installed source; the [library capability notes](../../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md), section A on pytest (fixture closure) |
| No metadata on fixtures | — | A mark applied to a fixture is an error since pytest 9.0, hence the project decorator | — | [pytest deprecations, "Applying a mark to a fixture function"](https://docs.pytest.org/en/9.1.x/deprecations.html#applying-a-mark-to-a-fixture-function); the library capability notes, section A on pytest (marks on fixtures) |
| Undefined fixture names | — | A test naming an undefined fixture fails at setup, not at collection; pytest has no strict option for fixture names | So a hand list can never be validated by pytest | The library capability notes, section A on pytest (`fixtures.py:1873–1877`, installed source) |
| Worker affinity | `--dist=loadgroup` with one `xdist_group` mark per item | All items with the same group run on one worker | Several marks on one item are joined into a new group named by the sorted names, so the hook must emit one mark | [xdist distribution modes](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst); `xdist/remote.py:242–253`, installed source |
| Identical collection on every worker | — | Metadata is read from the same resolved definitions in every worker | Group derivation must not depend on the worker or on time | The library capability notes, section B on pytest-xdist (`loadscope.py`, installed source) |
| **Hook order (inferred)** | `@pytest.hookimpl(tryfirst=True)` on the root hook | The root hook adds group marks before xdist's worker plugin reads them. The worker plugin is registered after the initial conftests, and pluggy calls later registrations first | **Not documented by xdist; inferred from installed source (`remote.py:122, 420–427`).** Confirming it is the first step of TDM-15 | The library capability notes, section B on pytest-xdist (hook order) |
| Read-only transactions | `rollback_connection(…, readonly=True)` behind `native_read` (`tests/conftest.py:436–439`) | PostgreSQL refuses writes and temporary tables | `25006` precedes the privilege check | ADR-0101; [PostgreSQL 18 `SET TRANSACTION`](https://www.postgresql.org/docs/18/sql-set-transaction.html) |
| Advisory file locks | `fcntl.flock` on distinct open file descriptions | A second descriptor on the same file conflicts with the first even within one process, which lets a control hold the lock without a second process | Linux semantics | [`flock(2)`](https://man7.org/linux/man-pages/man2/flock.2.html) |

## TDM-15 — Preparation declarations at the fixture

**Prerequisite.** TDM-01, for the shared conftest edits: both packages edit `tests/conftest.py`
and root `conftest.py`, and TDM-01's repairs land first. The coordinator's record of RC09 is what
authorizes removing the fixture-name table that the earlier plan's package TS-12 introduced; the
package checks that the record exists before it removes the table.

**First step: confirm the hook order.** The design relies on the root hook's marks being present
when xdist's worker plugin rewrites node identities, and on the `db` mark being present when
pytest applies `-m` deselection. Both hold today by position, and this package does not move
either hook, but the first is an inference from source. Confirm it before building on it: read
the installed registration order (`xdist/remote.py`), and run a two-worker selection that contains
at least three tests of one declared group interleaved with ungrouped tests, checking in the
stored result that all members of the group ran on one worker and that the plugin's recorded
`affinity_groups` name the group. If the order does not hold, the remedy is local, the hook's
ordering attribute, and the rest of the design is unaffected.

**Implementation vision.** The decorator and resolved-definition adapter live in one module
under root `scripts/`, beside the test infrastructure shared by both trees. The decorator stores
metadata on the fixture definition and preserves pytest's normal fixture semantics. Root
`conftest.py` resolves each item's actual definitions through the adapter and applies the conflict
and coalescing rules above. It preserves explicit marks while emitting a single resolved group
before xdist handles the item.

The package conftest's hook marks an item `db` when `native_server` is in its closure. The fixture
`observed_store_checkouts` takes `infrastructure_engine` as an ordinary parameter. The
parameter-selected test without a static native fixture
(`test_native_fixtures.py:149–170`) names `commit_db_engine` as a parameter, which its four
candidate engines already depend on, and drops its explicit mark. The two order-sensitive sites
(`test_db_fixtures.py:130`, `test_native_fixtures.py:546–550`) keep their dynamic requests; the
second keeps its consumer's explicit mark, and a comment at each says the order is the claim.

**Decisions this package owns.** The decorator's name and module, and whether the six
mathematics fixtures each declare the group or only the two the other four depend on. Fixture
names follow pytest resolution and need no global uniqueness rule.

**Consumers migrated (complete scope).** The thirteen live rows of the table, declared at their
definitions in `tests/math/conftest.py`, `tests/statistics_pack_support.py`,
`tests/semantic/test_hanlp_products.py`, `tests/semantic/test_local_semantic_admission.py`,
`tests/semantic/data_operation_binding_support.py` and
`tests/semantic/test_data_operation_storage.py`; the rollback-family fixture in
`test_record_policy_completion_native.py`; the two hooks; the dynamic-request sites as stated. The
one row that names a root-tree test (`source_release`, `tests/test_native_run_scope.py`) is dead
by a scan of that file, which exists and does not name `source_release`. The root `tests/` tree
outside `tests/scripts/` is out of the series' scope and is not edited; the scan at `12f57dc4d`
found no parallel list and no live declaration in it, so no scope question arises. The tests of
the qualification plugin under root `tests/scripts/` are in scope; none names either list.

**Superseded machinery removed.** `PREPARATION_AFFINITY` and the consumer-path qualification in
`_preparation_group`; `DB_FIXTURES`; the six `record_source_*` fixtures; the four unimported
support modules. `tests/semantic/test_source_routing.py` is rewritten or removed by TDM-01 under
the transfer rule below; this package only confirms it no longer names an undefined fixture.

**Preserved.** The refusal of conflicting groups. Explicit `db` and `xdist_group` marks. The
plugin's `native_required` and `affinity_groups` records, which keep reading marks. The decision
not to group commit-class seed consumers.

**Failure behaviour.** Conflicting resolved preparation requirements fail at collection with
item and definition context. Legitimate same-name definitions resolve normally. A removed fixture
carries its metadata away, and a surviving request for it fails at setup with pytest's fixture
error. Collection success alone establishes no fixture-body or dynamic-setup success.

**Acceptance evidence.** The expectations are authored or come from the mechanism being replaced,
never from the new derivation itself.

- *Nothing changed that should not have.* Collect the whole package and root trees (collection
  only; nothing in the root tree is edited) before and
  after the change and compare the two maps the plugin already records at `collection_finish`:
  node identity to `affinity_groups`, and the `native_required` list. The expected difference is
  written down by hand before the comparison: no group changes, because every removed row named no
  live fixture, apart from the newly declared rollback family; no
  `native_required` change. A derivation rooted at the wrong fixture, or a lost declaration, shows
  as an unexpected difference.
- *The mark follows the root.* Three small controls in the fixture test module, each asserting on
  its own item: a test that requests only `native_settings` has no `db` mark; a test that reaches
  `infrastructure_engine` only through `usefixtures("observed_store_checkouts")` has it; a test
  that requests a commit engine has it. The second fails if the dynamic request was not made
  static.
- *A declaration groups its consumers.* A control fixture declared with a literal group name and a
  test that depends on it through a second fixture: the test's single `xdist_group` mark carries
  that literal. A second control declares two groups in one closure and expects the usage error.
- *Resolution is local.* Sibling fixtures with the same name carry independent groups. A child
  override uses its own group, and an override requesting its parent includes that parent's
  requirement. Matching explicit and inferred groups coalesce; differing groups fail early.
- *Dynamic prerequisites are explicit.* A grouped dynamic request uses its owning fixture's
  declared prerequisite. A targeted setup run exercises that route and the adapter's unsupported
  shape/version diagnostic. Root and package collection agree, and a bounded two-worker run
  preserves normalized logical identities and the intended worker placement.
- *The lists are gone.* A search finds no `PREPARATION_AFFINITY`, no `DB_FIXTURES`, no
  `record_source_`, none of the four module names, and `getfixturevalue` only at the sites this
  section names.

Targeted verification: `tests/test_db_fixtures.py`, `tests/semantic/test_native_fixtures.py`,
`tests/db/`, the six modules whose fixtures gain declarations, and a collection-only pass of both
trees.

## TDM-16 — Production SQL from its owner; expression checks in the read class

**Prerequisite.** TDM-00 supplies the superseding record for ADR-0101 that states RC10 and its
re-read of changes after `12f57dc4d`. TDM-01 has repaired the reader of the deleted file and the
stale patch in `test_native_closure.py`.

**Delivered by the conversion.** Ten path readers moved to generator imports, both missing
anchors were resolved, and `routine_declaration` exists (commits named in the baseline). The
package no longer rewrites those readers' sources. Its remaining scope is the ten path readers
of the baseline table, the one anchor cutter among them, and the class of every check that
creates a database per case without claiming a bare database, which is the larger part and grew
with the conversion.

**First step: classify.** List every test that opens a file under the production SQL directory
or searches production SQL text, and every one of the 61 files that use `semantic_bare_engine`
whose claim is not a bare or partly migrated database. For each, record the subject (which
function, trigger, expression or program), whether the head has it as an installed object
(`to_regprocedure` and the catalog decide, not memory), and the route from the table above. The
lists in this document's baseline are complete at `12f57dc4d` for path readers and name the
sixteen new bare-engine files; the classification of the other 45 is this step.

**Implementation vision.** Each check keeps its cases and its expected values, which are already
hand-authored tables of inputs and outcomes, and changes how it reaches its subject.

- A check of an installed function calls it by its installed name in the read class. The
  trust-snapshot comparisons become calls of the installed `ops.ddo_trust_snapshot_meaning` on
  `native_read` with the same argument tuples; the per-case database, the `ops` schema created in
  it and the private install of the routine go. `test_source_metadata_codec_native.py` calls the
  installed `data.record_json_source` instead of installing the generator's output into a bare
  database. The replicate-policy, JSON-meaning, read-visibility and population-projection
  functions are reached the same way.
- A check whose claim is about the generator's current output, and not about what the head has
  installed, installs that output for the case on `native_rollback`: the whole program with
  `execute_native_sql`, or one routine through `routine_declaration` under `pg_temp`. This is the
  route for the sixteen conversion test files that install generated programs into a fresh
  database per case, wherever the deployed schema admits their rows. It is the route
  `test_support_trust_native.py` and `test_data_operation_compiler_native.py` already show.
- A check of a guard inside a function body exercises the enclosing installed function in the
  rollback class, with the rows the guard needs and the refusal it raises, asserted under the
  refusal contract (TDM-14). The binding trust-snapshot guard is of this kind. The
  selected-dependency predicate and the execution-evidence guard are now imported as named
  expression builders; those checks keep the import and are evaluated on the route their
  dependencies allow.
- A check of a trigger exercises the installed trigger in the rollback class; the
  retirement-context check stops reading `data_operation_task_checks.sql` by path and stops
  assembling a trigger body from four text cuts.
- A check that reads a whole file to install or compare it takes the program from the production
  function that loads the file, or compares against the catalog of the head, according to its
  claim. The two checks that read a file no production module loads
  (`test_data_operation_identity_native.py:56–58`, and the `source_record_graph.sql` half of
  `test_data_operation_constraint_custody.py:94–95`) test the installed object if the head has
  one; if it has none, the subject is gone and the check is removed under the transfer rule.
- `test_data_operation_null_scope.py` and any check found to need only PostgreSQL move to
  `infrastructure_rollback`.
- `cpu_basis_connection` and its three importing modules follow the rule for cases the deployed
  schema forbids.

Tests' own control SQL, the statements a test writes to set up or to observe, is untouched.
ADR-0131 preserves it, and ending text cutting concerns production's SQL only.

**Decisions this package owns.** The route of each check, by the table; which rollback-class
checks use the session clone and which a rollback family of an existing seed; new names for tests
that leave the deployed schema.

**Consumers migrated (complete scope).** The ten path-reading modules of the baseline table, and
every check among the 61 users of the bare engine whose claim is not a bare or partly migrated
database, including the sixteen conversion test files. The modules named in this section are
examples of each kind; the classification of the first step is the scope.

**Superseded machinery removed.** Every `files("corpus_structure.semantic").joinpath("sql/…")`
and path-built read of production SQL in tests; every `.index(` cut of production text; every
install of a production routine into a per-case database for a check that writes nothing
durable; the use of `function_bodies` on text a test read from a file.

**Preserved.** Every case and its literal expected outcome. Bare and revision fixtures for
bootstrap and upgrade claims. The generator imports the conversion delivered.
`routine_declaration`, which this package uses more widely. `function_bodies` itself, which is
production code with four production callers.

**Failure behaviour.** After this package a retirement of a production function fails its checks
with PostgreSQL's undefined-function error, and a retirement of a generator fails them at import
during collection. Neither waits for someone to run one particular file.

**Acceptance evidence.**

- *The cases survived.* Compare collected identities where the move can lose or regroup cases,
  and record any changed expectations with their reason. The expected values are the independent
  expectation and predate the change.
- *The check reaches the installed object.* One reach control per route. In the rollback class,
  replace the installed function under test with a body that returns a constant, inside the
  case's transaction, and require the check's own assertion to fail for a case whose expected
  value differs from the constant. A check that still evaluates a private copy passes when it
  should fail. This control is written once for the trust-snapshot function and once for a
  trigger.
- *The intended database class is exercised.* Use existing native provenance receipts for the
  migrated installed-release journeys. Generated-scratch expression checks, installed-release
  admission and bare/bootstrap checks retain their distinct subjects and setup. A rollback
  connection running a temporary routine establishes that temporary-program claim.
- *No text reading.* A search of `tests/` finds no read of a path under the production SQL
  directory and no search of production SQL text.
- *Names are true.* No test on the infrastructure route or a substitute schema has `native` in its
  name; a search over the moved modules shows it.

Targeted verification: each moved module by path.

**Later retirements.** Validation of the conversion is still running. A reader that a further
retirement breaks before this package runs is rewritten here from its cases, which survive in the
test even when its source text does not. A function removed without a successor has no subject
left; its checks are removed under the transfer rule.

## TDM-17 — The ordinary host test without the real GPU lock

**Prerequisite.** None.

**Implementation vision.** In `tests/methods/test_native_host.py` the residency test loses the
import of `pdf_gpu_slot`, the deadline and the slot block, and is renamed for what it shows: the
residency retires its group for an external borrower and restarts a real host afterwards. Its
remaining assertions are unchanged.

In `tests/ingest/test_pdf_capacity.py` two controls join the existing quarantine control. The
first replaces the borrow of resident hosts and the lock call with recorders and expects the
literal order borrow, then lock. The second replaces the module-level `Path` name in
`corpus_structure.ingest.pdf_capacity` for its duration, so that the lock file lies in the test's
temporary directory, takes the lock on a separate descriptor, enters the slot with a liveness
callback that counts its calls and releases the holder on the third, and expects entry after
exactly three calls (the slot calls the callback before each lock attempt); a variant whose callback raises on the second call expects that exception
and no entry. Neither touches the host-wide path.

**Consumers migrated (complete scope).** One test. No other test enters the real slot: every
other user replaces the slot or the lock calls (search for `pdf_gpu_slot` in `tests/`).

**Acceptance evidence.**

- *Host retirement and lock ownership are observed separately.* The ordinary test reaches
  residency retirement and restart through its live host route. The lock controls use the
  private file and independent descriptors to exercise waiting and release. A recorder confirms
  that the ordinary test never requests the accelerator slot or host-wide lock.
- *The order is tested.* Swapping the borrow and the lock in the slot fails the first control.
- *Waiting is tested.* A slot that returned without the lock, or that stopped calling the liveness
  callback while waiting, fails the second control; the expected call count is a literal.
- A search finds no entry into the real slot in `tests/`.

Targeted verification: `tests/methods/test_native_host.py` and `tests/ingest/test_pdf_capacity.py`.

## Retirement rules

These four rules are what makes a checker unnecessary. They are obligations on any later change
that retires a production mechanism, a fixture or a support module, including any further SQL
retirement. Nothing enforces them mechanically, by decision: rules 1 and 2 make a
violation of the others fail loudly on its own.

1. **Derive, do not list.** A fact about a fixture (it needs the database, it shares a worker) is
   stated on the fixture or derived from the fixture graph. A change that adds a list of fixture,
   module or test names kept apart from what it names is reintroducing the defect.
2. **Obtain a subject from its owner.** A test imports the generator, builder or type it tests, or
   names the installed object. It does not open a production file by path or search production
   text. A retiring change can then find every dependent test by removing the owner: imports fail
   at collection and installed names fail with a missing-object error.
3. **The retiring change removes its tests and their machinery, and transfers first.** Before
   deleting a test with the mechanism it tested, the change asks whether any behaviour that
   survives the retirement was evidenced only by that test. If so, it moves that evidence onto the
   surviving owner and says where in its commit message; if not, it says that nothing transfers.
   The fixtures, support modules and declarations that only those tests used go in the same
   change.
4. **Production kept alive only by tests retires with those tests.** Production code whose last
   caller is a test is deleted together with that test, inside the package that owns the test.
   The scheduled items include `admitted_startup_matches` and its mechanism-only tests in
   TDM-11, subject to a named accepted consumer check, and the `--principals` mode of root
   `scripts/pg_semantic_roles.sh`, which has no caller and goes in TDM-06. The two the authoring
   baseline named are settled: the conversion deleted the fixture-only occurrence writer
   (`8a5c074f0`), and `function_bodies` has four production callers and stays. Other superseded
   production machinery (the remaining items of
   [DA-080](../../design_review/audit/boundaries-and-composition.md#da-080), and the six SQL
   files without a loader) appears in the coordinator's production-context
   [table](../test-domain-model-and-execution_2026-11-17.md#handovers), not scope of this series.

## What the rule-change records must say

TDM-00 writes them; this companion needs the following content.

**RC09, recorded in the coordinator.** The `db` mark derives from the native root fixture.
Worker groups are declared at the fixture definition. The fixture-name table introduced by the
earlier plan's TS-12 and the `DB_FIXTURES` list are removed. Explicit marks on tests remain valid.
A native fixture is requested dynamically only where acquisition order is the claim or a parameter
selects among fixtures.

**RC10, in the successor to ADR-0101.** The sentence that infrastructure clones are "shared only
for connection exercises without durable effects" is widened: a rolled-back infrastructure
connection may also run an expression check that installs only temporary objects and references
no semantic object. The record should also say what this does not change: a check of an installed
semantic object uses the semantic read or rollback class, so that it tests the deployment.

## Deferred

[DTA-026](../../design_review/test-audit/execution-and-qualification.md#dta-026), the remaining
test of interpreter-private state, is deferred to an interpreter change; the coordinator's
[list](../test-domain-model-and-execution_2026-11-17.md#candidates-and-deferrals) records it, together with the deferral of grouping
commit-class consumers of a seed and the rejection of change-based test selection.

## Open questions

| Question | Evidence that settles it | Work it constrains |
|---|---|---|
| Do the root hook's marks precede xdist's reading of them? | TDM-15's first step | The grouping half of TDM-15; a negative answer changes one hook attribute |
| Does the head install the routines that the sixteen conversion test files install per case, and the functions of the two SQL files no production module loads? | The catalog, in TDM-16's classification | Whether a check calls the installed object, installs the generator's output for the case, or has no subject left |
| How many expression checks need rows the deployed schema forbids? | TDM-16's classification | The size of the substitute-schema remainder; if it is most of them, the audit's fidelity gap is narrower than read and the coordinator is told |
| Does the read-only transaction refuse any installed function that a check must call, for example one that creates a temporary table? | The first run of each moved module; `25006` is the signal | That check moves to the rollback class |

## State

The coordinator owns [scoped results and qualification](../test-domain-model-and-execution_2026-11-17.md#implementation-evidence).
