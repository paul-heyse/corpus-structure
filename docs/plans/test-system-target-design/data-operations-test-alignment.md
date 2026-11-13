# Data-operations test alignment

**Status:** Proposed plan; nothing implemented. **Created:** 2026-11-13.

This companion owns the design of the test support, isolation, independent evidence, cutover
transfer and final evidence mapping for the tests of the declared-data-operations (DDO) work:
packages TS-17 to TS-22. The [coordinator](../test-system-target-design_2026-11-13.md) owns
package state, the shared contracts and the disposition of every finding named here; this
document does not restate them.

**Baseline and evidence labels.** Source was read at `main` `074638c64`, 2026-11-13, three
commits after the series' authoring baseline `f03170a89`; `tests/semantic/test_data_operation_storage.py`
is unchanged between them (2,198 lines). Another session is editing DDO code and tests, so line
citations are as read and may move. Every design statement is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-13**. Durations quoted from the audit are
**Measured** from stored results on a shared workstation and are orders of magnitude. Paths
written `tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written
as root `…` or start with `docs/` or `scripts/`.

**Sources.** The [design review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md)
§4.3 (DDO support), §4.6 B (lease expiry), §4.8 (cutover and the union), §4.9 (independent
evidence), §6.1 DTA-031, §6.5 DTA-033 to 036, §12 RC03 and §13; its
[supporting document](../../design_review/reviews/test-system-target-design/options-and-classification.md)
Parts B.2 and B.3; and the audit findings
[DTA-031](../../design_review/test-audit/execution-and-qualification.md#dta-031),
[DTA-033](../../design_review/test-audit/evidence-and-discrimination.md#dta-033),
[DTA-034](../../design_review/test-audit/support-structure.md#dta-034),
[DTA-035](../../design_review/test-audit/retirement-transfer.md#dta-035) and
[DTA-036](../../design_review/test-audit/retirement-transfer.md#dta-036).

## Current baseline and what is reused

Thirty-seven `test_data_operation_*.py` modules exist (33 under `tests/semantic/`, 4 under
`tests/orchestrate/`), plus `tests/test_cli_demands.py` and several product and source modules
that use the DDO compiler. They have no support owner.

- **The storage test module is the support library.** `tests/semantic/test_data_operation_storage.py`
  defines the base declaration and five variants (`:62–160`), the clone fixture
  `ddo_kernel_engine` (`:163–169`), the `kernel` fixture (`:172–253`) and the demand helpers
  `attach` (`:256`), `claim` (`:334`), `retain` (`:349`), `publish` (`:383`) and `cancel_demand`
  (`:1341`). Seven other modules import from it.
- **The admission sequence is written out seven times in six modules.** Persist the release,
  admit it, persist the runtime binding, insert a project row: storage `:229–233`,
  `test_data_operation_population_native.py:138–142`, `test_data_operation_consumer_native.py:365–369`,
  `test_data_operation_original_native.py:107–110` and `:286–289` (the project row comes from
  `private_source` there), `tests/orchestrate/test_data_operation_execution.py:78–82` and
  `tests/orchestrate/test_data_operation_claim_source_native.py:82–86`.
- **Every native check clones a fresh database.** The kernel holds no claim, lease or clock
  value, yet it is rebuilt per case. Measured in the audit: the storage module's 26 tests spent
  416 s in setup and 44 s in their bodies in one stored run.
- **Imports cross a non-package directory.** `tests/orchestrate/` has no `__init__.py`, and
  three of its modules import `..semantic.test_…` relatively, which under
  `--import-mode=importlib` (root `pyproject.toml:63`) loads the target a second time under
  another name (review §4.3 rule 2).

Reused unchanged, and not to be weakened:

- hand-authored compiler node ids, refusals and recipe-sensitivity perturbations;
- literal canonical framing vectors (`tests/semantic/test_data_operation_identity.py:65–78`,
  `test_data_operation_identity_native.py:22–86`);
- hand-authored graph topologies, independent wire bounds and behavioral tests of generated types;
- real-transaction concurrency, visibility and purpose-principal controls in the storage module;
- the production `claim_source_item__data_operation__` declaration
  (`src/corpus_structure/semantic/identity.py:43–105`), which six pure modules import from
  production on purpose.

## Target design and contracts

The DDO tests get support named for the units the DDO design itself names, and each native test
states what isolation its claim needs.

| Operation | Consumes | Decides | Produces | Owner |
|---|---|---|---|---|
| Declaration builder | A vocabulary preset and explicit case fields | Nothing hidden: every field a test asserts on is an argument at the call site | A declaration mapping | TS-17 |
| `compiled(recipe)` | A recipe value (TS-06 contract) | Whether this worker has already compiled it | The compiled effective model, memoized per process | TS-17 |
| `admit_kernel(connection, recipe)` | A connection in an open transaction and a `KernelRecipe` | Nothing; it is the one persist, admit, bind, project sequence | Committed kernel rows when the caller commits, and a `Kernel` handle | TS-17 |
| Interim `kernel` fixture | A `KernelRecipe` | Nothing | A fresh clone of the head per test with `admit_kernel` run on it: the isolation the tests have today | TS-17; removed by TS-18 |
| `ddo_kernel(recipe)` | A `KernelRecipe`, the seed operation (TS-08) and the commit class (TS-05) | Which seed to clone | `scenario_seeds.commit_clone(recipe)`: a fresh commit-class clone of that recipe's sealed seed, with the handle exposing the purpose engines of that clone | TS-18 |
| `expire_lease(kernel, task_id)` | A claimed data task | Nothing | The task's `lease_until` moved one second into the past, as the publisher role | TS-18 |
| `WireCheckedStorage` | Hand-written replies per native operation | Whether each input and each reply satisfies the production wire | The reply, or the wire's own refusal | TS-20 |
| Binding case table | Independently authored cases | Nothing | One set of expected members, roles, positions, support and witnesses for two executors | TS-20 |

**What consumers stop doing.** Importing from a `test_*` module; importing relatively from
`tests/orchestrate/`; writing out the admission sequence; building a kernel per test; cloning a
database to call an installed function; sleeping to expire a lease; replacing
`DataOperationStorage` with an unchecked class; executing compiled bindings on SQLite.

**Preserved guarantees.** Every test that commits, races, cancels or uses a second login still
runs on its own database with real logins. A kernel clone is admitted by production's
`admit_data_operation_release`, once per recipe per worker, not simulated. Expected values stay
authored at the test or in an independent table.

**Intentional behavior changes.** The execution fixture's captured module name becomes fixed, so
its release identity is the same in every test and worker. Three lease-expiry tests no longer
depend on the wall clock. Compiled binding tests run on PostgreSQL and therefore need a deployed
head.

**A new DDO native test, in the target.** It imports builders from support, names a
`KernelRecipe` (an existing one, or a new value declared beside the others), and requests either
`ddo_kernel(recipe)` for a committing claim or the rollback or read class for a claim that
commits nothing. Between TS-17 and TS-18 the committing form is the interim `kernel` fixture
with the same recipe. A test whose claim is a bare database requests a cold deployment fixture.
It does not define a fixture that calls `persist_release`. TS-17 should land before DDO-06 adds
native tests so that those start in this shape; the coordinator records that ordering as a
handover.

### Library and system mechanisms

The mechanisms are the review's §7 rows, used as selected there: clone of a sealed seed by
`CREATE DATABASE … TEMPLATE` (seed operation, TS-08); the read class by `SET TRANSACTION READ
ONLY`, which refuses writes and DDL with `25006`; the rollback class by SQLAlchemy Core
`Connection.begin()` and `rollback()` with savepoints; and canonical absolute imports of support
modules on the configured `pythonpath` (root `pyproject.toml:74`). One consequence matters here
and is not in the review: a read-only transaction cannot create a function, including one in
`pg_temp`, so a test that installs SQL from source text belongs to the rollback class even when
it writes no rows (see TS-18).

## RC03

RC03 is accepted (coordinator, rule changes): DDO native checks run on clones and seeds of the
deployed head under the named isolation classes, and the working database is not a test lane.
The sentence it corrects is in the DDO contracts companion
(`docs/plans/declared-data-operations/contracts-and-compilation.md:359–361`). That edit belongs
to the DDO plan's owner; this series does not edit that plan. Everything below designs to clones
and seeds.

## TS-17 — DDO support modules and kernel recipes

**Required input.** TS-06's placement and import rules and its recipe-value contract.

### Placement

Support modules live in the `semantic` test package (`tests/semantic/__init__.py` exists) and
are imported by canonical absolute name, `from semantic.<module> import …`, from every
directory including `tests/orchestrate/`. None is named `test_*`, so none is collected. Proposed
modules, following the existing `*_support.py` naming in that directory:

| Module (`tests/semantic/`) | Holds |
|---|---|
| `data_operation_declaration_support.py` | Vocabulary presets, declaration builders, `compiled(recipe)`, `subject_context(...)`, `root_subject(...)`, and the pure helpers other modules borrow today (`contract`, `declarations`, `identity`, `resolved_binding` from the compilation module; `model`, `operation` from the demands module) |
| `data_operation_kernel_support.py` | `KernelRecipe`, the ten recipe values, `admit_kernel`, the `Kernel` handle, the function behind the interim `kernel` fixture, `original_target` |
| `data_operation_demand_support.py` | `attach`, `claim`, `retain`, `publish`, `cancel_demand`, `expire_lease` |
| `data_operation_port_support.py` | `fixture_source`, `kind` (`test_data_operation_ports.py:36,41`), `scope` (`test_data_operation_cpu.py:31`), `captured` (`test_data_operation_wire.py:27`) |
| `data_operation_binding_support.py` | The binding connection, its `context`, `evaluate`, `field`, `literal` helpers, and (TS-20) the binding case table and `WireCheckedStorage` |

A kernel fixture is needed in two directories, so by TS-06's rule it is registered in the
package `tests/conftest.py` as a thin wrapper over a function in the kernel support module.
TS-17 registers the interim one: a function-scoped `kernel` fixture that takes a `KernelRecipe`
as its indirect parameter, creates a fresh clone of the head as `ddo_kernel_engine` does today
(`:163–169`), and runs `admit_kernel` on it. That is the isolation the tests have now, so TS-17
needs neither TS-05 nor TS-08. TS-18 replaces it with `ddo_kernel(recipe)`.

### Declaration builders

Six declaration families exist. The compiler closes only `profile`
(`src/corpus_structure/semantic/data_operation_compilation.py:71`), capability `forms`, and the
role `direction`, `collection`, `presence` and support `provenance` literals
(`data_operation_model.py:69–90`). It accepts any non-empty text for subject, context,
applicability, coverage, outcomes, precision, and the `preparation`, `cancellation` and
`ownership` capabilities. So the families' vocabulary differences are free text to the compiler,
and matter only where something downstream reads a value.

| Family | Defined at | Used by | Vocabulary that is case-defining | Target |
|---|---|---|---|---|
| Native source | storage `:62–95` plus five variants `:98–160` | storage, population, consumer, original, execution, claim-source, subjects | `outcomes` (success, empty, failed: `retain` passes them), `context` (project, source, analyzed-scope reach the request), `cancellation`, `ownership`; execution overrides `cancellation` to `call-boundary` and the role kind (`test_data_operation_execution.py:37–40`), which production reads at `data_operation_ports.py:780–781`; original sets `preparation: pdf-native` | `native_declaration(identifier, *, behavior, roles, outcomes, context, cancellation, ownership, preparation, parameters)` with no defaults for the case-defining fields; the five variants become calls |
| Compilation `contract()` | `test_data_operation_compilation.py:40–91` | compilation, original-support | None asserted; callers vary `entrypoints`, `profile`, `binding`, `dependencies`, `effects`, state and assets | Merge candidates for one `declaration(identifier, *, vocabulary, profile, binding, dependencies, potential_dependencies, parameters, …)` builder. `vocabulary` is a frozen preset naming subject, context, applicability, coverage, outcomes, cancellation and ownership |
| Demands `operation()` | `test_data_operation_demands.py:24–59` | demands, json (`:25`, lazy) | None asserted; callers vary `dependencies`, `potential_dependencies`, `profile`, `parameters` | same builder |
| Bindings `declaration()` | `test_data_operation_bindings.py:409–457` | bindings | None asserted; callers vary `potential_dependencies` only | same builder |
| Parameters' own | `test_data_operation_parameters.py:62–99` | parameters | Typed parameters are the case | same builder, parameters explicit |
| Production `claim_source_item` | `src/…/semantic/identity.py:43–105` | wire, ports, cpu, member-projection, artifacts, batch-activity | It is production's declaration | Stays imported from production; no builder |

The merge has one constraint. Compile-only tests hold hand-authored node ids and digests, and a
compiled identity covers the whole declaration. So the merged builder starts with one preset per
existing family (the present values, unchanged), and two families share a preset only after
their modules pass on it. Where a hand-authored expectation depends on a family's vocabulary,
the preset stays and the reason is a comment on it; the expectation is not regenerated to fit.
Two strengths the review records (§4.9) must survive the merge. Source-capture tests keep an
unknown value distinct from an absent one, and equal bodies under different contexts give
distinct products. The fields that make those cases differ stay explicit arguments at the call
site, and no shared preset or default collapses unknown into absent or makes two contexts equal.
`test_data_operation_subjects.py:11`, a pure compiler test that imports the native storage
module for one dictionary, takes the native builder from support.

`compiled(recipe)` memoizes `compile_data_operations` by recipe value for the process. About
sixteen modules compile their own model today; they move as they are touched, not in one sweep.
`subject_context(project, subject, source, scope)` and `root_subject(subject, source, scope)`
replace positional literals such as `SubjectContext("ddo-test", "subject:one", "source:test",
b'{"page":1}')` (storage `:958`) with named fields.

### `KernelRecipe` and `admit_kernel`

`KernelRecipe` is a frozen, hashable, data-only value: schema text, declarations (or captured
Python source), kinds, model version, execution profile, project id, and for the original
recipes the private-source stage they sit on. Under TS-06's dispatch rule it registers exactly
one builder, which calls `admit_kernel` and commits; the seed operation finds it by the recipe's
type. `admit_kernel(connection, recipe)` prepares the inputs in a
per-recipe directory (the checkout path does not enter identity:
`data_operation_preparation.py:3–4`), then runs the one sequence and returns a frozen `Kernel`:
engine or connection, `prepared`, `model`, runtime id, runtime inputs, the identity map, and the
recipe. It replaces the seven sites listed above. If production gains an activation operation
for data-operation releases, `admit_kernel` calls it and nothing else changes.

The ten recipes:

| Recipe | Today | Content | Shared by |
|---|---|---|---|
| Storage | storage `:172–253` | `urn:ddo-test`; six declarations; one evaluator kind; `execution:test`; project `ddo-test` | storage (42 tests), service (1 test) |
| Population | population `:33–142` | `urn:ddo-selection`; discover, consumer, child; `execution:test`; `ddo-test` | population (5) |
| Consumer: document, projection, structural, occurrences | consumer `:66`, `:175–253` | The repository consumer model plus control producers, one release per case; model v2 | consumer (one test, four cases); one recipe each |
| Execution | execution `:34–83` | `urn:exec`; `answer` and `broken` in captured Python source; project `execution` | execution (2) |
| Claim source | claim-source `:36–86` | `urn:production-claim-test`; a verbatim copy of production `identity.py` | claim-source (1) |
| Original fact | original `:33–110` | `urn:original-fact-test` with `core.yaml`; `execution:original-fact`; project from the private source | original (1) |
| Original PDF | original `:271–289` | As above with `preparation: pdf-native` and PDF contracts; `execution:original-pdf` | original (1) |

The review counted nine; claim source is the tenth. Two points on stability. The execution
recipe's module name is `"ddo_execution_" + uuid4().hex` today (`:35`), which makes its release
identity differ per test; the recipe fixes the name (for example `ddo_execution_fixture`), and
the test keeps its own `monkeypatch.syspath_prepend` for the directory that holds the module.
The claim-source recipe depends on the bytes of production `identity.py`, which are stable for
one source tree; that is intended. The runtime id includes `sys.version`
(`data_operation_runtime.py:31,39`), stable for all workers on one interpreter.

### Importers migrated

| Module | Import today | Becomes |
|---|---|---|
| `test_data_operation_population_native.py` | `:29` `_declaration, claim, publish`; `:30` `ddo_kernel_engine` | declaration and demand support; the interim `kernel` fixture |
| `test_data_operation_consumer_native.py` | `:56` `_declaration, claim`; `:57` `ddo_kernel_engine` | same |
| `test_data_operation_original_native.py` | `:29` `_declaration` | declaration support |
| `test_data_operation_subjects.py` | `:11` `_declaration` | declaration support |
| `test_data_operation_service.py` | `:12–13` `ddo_kernel_engine`, `kernel` | the interim `kernel` fixture |
| `orchestrate/test_data_operation_execution.py` | `:29–30`, relative | absolute, from support |
| `orchestrate/test_data_operation_claim_source_native.py` | `:27–33`, relative | absolute, from support |
| `orchestrate/test_data_operation_batch_activity.py` | `:67–68`, relative and inside a function: `scope`, `fixture_source`, `kind` | absolute, from port support |
| `test_data_operation_cpu.py` | `:28` `fixture_source, kind` from the ports test module | port support |
| `test_data_operation_population_selection.py` | `:17–25` binding connection and helpers | binding support |
| `test_data_operation_parameters.py` | `:15–17`, absolute `semantic.test_data_operation_binding_native` | binding support |
| `test_data_operation_json.py` | `:25`, lazy `model, operation` from the demands test module | declaration support |
| `test_data_operation_original_support.py` | `:17` four helpers from the compilation test module | declaration support |
| `test_original_documents.py` | `:17` `original_target`, `:18` `captured` | kernel and port support |

`test_data_operation_compilation.py:625` imports `bundle, schema` from `test_conditional_rules`;
that is not DDO support and follows TS-06.

**Superseded machinery removed.** The six declaration helpers, the `kernel` and
`ddo_kernel_engine` fixtures and the demand helpers leave the storage test module; the
`fixture as fixture` re-exports go with them. The storage module's own tests request the
interim `kernel` fixture with the storage recipe.

**Coordination.** The storage test module is under active edit by the DDO session. Moving
helpers out is one commit agreed with that session, done when its tree is quiet, so that a
concurrent edit to `attach` or `kernel` is not lost.

**Acceptance.** No DDO test module imports from a `test_*` module (search `from \.+\w*\.?test_`
and `from semantic\.test_` under `tests/`); no relative import remains in
`tests/orchestrate/test_data_operation_*.py`; `persist_runtime_binding` after
`admit_data_operation_release` appears once in tests, in `admit_kernel` (replacement-runtime
calls at storage `:543`, `:1524`, `:1730` are cases, not admission, and stay).

**Verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_data_operation_storage.py`,
then the population, consumer, service, subjects and the two `tests/orchestrate/` native modules
by path. TS-17 alone changes no isolation, so results should match the runs before it.

## TS-18 — DDO native tests on kernel seeds and named isolation classes

**Required input.** TS-05 (class fixtures), TS-08 (`scenario_seeds.commit_clone(recipe)`),
TS-17. The two original recipes also need TS-07's pre-claim private-source stage; until it
exists they stay on a per-test build through `admit_kernel`.

**Vision.** A kernel seed is built once per recipe per worker: clone the head, run the
recipe's registered builder (`admit_kernel`, commit), check, seal. `ddo_kernel(recipe)` is a
fixture over `scenario_seeds.commit_clone(recipe)`: it clones the seed into a commit-class
database and returns the `Kernel` handle, which exposes the purpose engines of that clone. It
replaces TS-17's interim `kernel` fixture, which is removed. The Python-side values in the handle (`prepared`, `model`,
runtime) come from the same per-process memo that built the seed, which is coherent because
seeds are per worker. Tests that commit nothing stop cloning.

| Module | Today | Target class | Seed or source |
|---|---|---|---|
| `test_data_operation_storage.py` | `kernel` per test | commit, from the storage seed; `:756` read; `:2171` read | storage |
| `test_data_operation_service.py` | `kernel` (one test), pure (one test) | commit from the storage seed; pure | storage |
| `test_data_operation_population_native.py` | own kernel per test | commit | population |
| `test_data_operation_consumer_native.py` | four releases per run | commit | four consumer seeds |
| `orchestrate/test_data_operation_execution.py` | own kernel, uuid name | commit | execution |
| `orchestrate/test_data_operation_claim_source_native.py` | own kernel | commit | claim source |
| `test_data_operation_original_native.py` | commits on `semantic_db_engine` with `private_source` | commit | two original seeds over the pre-claim stage; the third test is pure |
| `test_data_operation_binding_native.py`, `…_population_selection.py`, `…_parameters.py` | `binding_native_connection` installs functions in a transaction it rolls back, on a fresh clone (`:42–72`) | rollback | head family clone |
| `test_data_operation_source_native.py` | `source_builder_connection` (`:37–47`), rolled back; one test with `private_source` | rollback; the `private_source` test commit from its seed | head; private-source seed |
| `test_data_operation_identity_native.py` | two tests execute SQL source text into `pg_temp` and roll back (`:59–86`, `:117–136`) | rollback | head |
| `test_data_operation_json.py` (new since the review) | one native test, same `pg_temp` pattern (`:79–116`); three pure | rollback; pure | head |
| `test_data_operation_selected_graph_sql.py` (new) | `semantic_bare_engine` | unchanged: a bare database is its claim, and `semantic_bare_engine` is a cold deployment fixture, the fifth named kind outside the four classes (TS-05) | none |
| `test_data_operation_outcomes.py`, `…_population_context.py` (new) | pure | pure | none |
| `test_data_operation_bindings.py`, `…_consumer_bindings.py` | SQLite | rollback on PostgreSQL (TS-20) | head |
| All other `test_data_operation_*` modules, `tests/test_cli_demands.py` | pure | pure | none |

**Where source differs from the review.** The review placed both identity-native tests in the
read class. They create `pg_temp` functions from source text, which a read-only transaction
refuses, so they are rollback class. The read class fits the two checks that call the
*deployed* function and write nothing: `data.ddo_normalize` at storage `:756–788` and
`data.ddo_json_meaning` at `:2171–2198`.

**Refusal families.** Invalid output (`:627`, four cases), renewal with a different fence
(`:1283`, four cases) and forged graph (`:1991`, four cases) each commit an attach or a claim
before the refused call. They take the commit class from the storage seed: one clone per case,
no kernel build. Moving them to the rollback class would need the attach and claim inside the
case transaction; that is a later option for TS-10's method, not required here.

**Forged graph builds only what it reads.** The family calls `attach(kernel)` (`:1997`) to
obtain a frozen selection, which registers a demand and also creates a request and task it never
uses. In the target it registers the demand alone and reads the selection from that; this is
the DDO instance of DTA-018 and the coordinator's row for that finding names TS-18. Its
`match=r"graph|closure|discovery"` (`:2019`) accepts any of three reasons for each of four
mutations; pinning one reason per mutation is TS-09's contract applied here.

**Lease expiry.** Production accepts `lease_seconds` from 1 to 86,400 and compares every expiry
with `clock_timestamp()` (`src/…/semantic/sql/data_operations.sql:735`, `:743–745`, `:762`,
`:773`, `:780`); there is no time parameter and none is added. `expire_lease` uses the idiom
already in the suite (`tests/semantic/test_operations.py:985–992`, with its comment "Time expiry
is fixture setup, not a write capability granted to the worker";
`tests/semantic/test_claim_owner_native.py:155–162`): in one transaction on the clone's
maintenance engine, `SET LOCAL ROLE corpus_sem_publisher`, then `UPDATE ops.task SET
lease_until = clock_timestamp() - interval '1 second'`. The data-task guard
(`src/…/semantic/sql/execution_guards.sql:4–20`) accepts this by reading: the role is the
publisher, the request generation is unchanged, and attempt, holder and status do not change.

| Site | Test | Target |
|---|---|---|
| `:1298` | `test_native_request_renewal_cannot_revive_an_expired_attempt` (`:1295–1303`) | Keeps its one-second lease and real wait. It is the control that expiry follows the advancing clock and that one second is an admitted lease |
| `:486` | `test_expired_owner_cannot_publish_but_exact_intent_can_be_adopted` | `expire_lease` |
| `:567` | `test_invalid_retained_runtime_rebinds_generation_only_after_lease_expiry[False]` | `expire_lease` |
| `:1747` | `test_revoked_runtime_without_retained_intent_refreshes_only_unleased_generation[expired]` | `expire_lease` |

**Open question, settled first.** `:2116–2121` already updates `lease_until` on a data task, in
the `uncommitted_intent=True` branch, through `kernel["engine"]` with no `SET LOCAL ROLE`. That
engine is the maintenance login (`scripts/native_test_support.py:444`). The source guard refuses
any data-task update whose `current_user` is not `corpus_sem_publisher`
(`execution_guards.sql:5–7`), so by reading, this statement should raise. Either the deployed
head's guard differs from source, or the branch does not run as read. TS-18 settles it by
reading the guard body on a head clone or running that one test. If the deployed guard differs,
it is a product question for the DDO owner (already in the coordinator's handovers) and
`expire_lease` is checked against the deployed guard before the three sites move. Either way the
site ends up using `expire_lease`.

**Purpose principals.** Three storage tests build `principal_engine(native_settings, purpose,
database)` by hand (`:1188–1193`, `:1881–1885`, `:1917–1920`). They take the purpose engines
that the `ddo_kernel` handle exposes for its commit clone, which
`scenario_seeds.commit_clone(recipe)` provides. TS-05's principal connections belong to the
rollback class and are not used here.

**Successful example.** `test_native_atomic_publication_and_exact_receipt_replay` requests
`ddo_kernel(STORAGE)`, receives a fresh clone holding the admitted release, and runs its body
unchanged. The module's receipt shows one storage seed build on the worker and one clone per
committing test.

**Revealing failure.** A recipe whose build is not reproducible, as the execution recipe would
be with its uuid name, produces a seed whose release id differs from the handle a second
consumer computes. The seed check compares the stored release id with the handle's and refuses
the seed; it must not surface as a confusing refusal inside a test body.

**Open premises.**

| Premise | Settled by | If it fails |
|---|---|---|
| Sealed kernel rows carry no database or role names | The first storage seed clone's tests: the purpose-principal and visibility tests exercise grants and ownership on the clone | That recipe stays on a per-test build through `admit_kernel`, in a module-local fixture that says why |
| The deployed data-task guard matches source | As above, before the lease sites move | Product question to the DDO owner |
| `private_source` has a pre-claim stage the original recipes can seed on | TS-07 | The two original tests stay per-test |

**Acceptance** (review closure for DTA-031). No DDO native test defines a fixture that clones a
database or admits a release, apart from a recipe held back by an open premise below. Each
requests a named class or, where a bare database is its claim, a cold deployment fixture. The
interim `kernel` fixture is gone. The storage module's receipt shows
one kernel seed per recipe per worker. `time.sleep(1.05)` remains at one site.

**Verification.** The module paths in the table, one at a time, with
`uv run ci test -- python/corpus-structure/tests/semantic/<module>`; then the storage and
service modules together to see one shared seed on a worker.

## TS-19 — Literal vectors for the contextual product identity

**Required input.** None; independent of the lifecycle work.

**Baseline.** Products are keyed by `contextual_product_identity`
(`src/corpus_structure/semantic/data_operation_identity.py:471–483`): the canonical identity in
domain `product` of a mapping with `kind`, `subject`, `subject_context` (the context's
`identity_record`, `data_operation_model.py:553–561`) and `body`. Its only test reads the stored
request context, calls the same function and compares with the stored key (storage
`:1811–1837`). A mistake made the same way in Python and SQL passes.

**Vision.** Add vectors to `tests/semantic/test_data_operation_identity.py` in the style already
there (`:65–78`): the canonical input written out by hand as bytes, starting
`["ddo","product","1",…`, and the expected digest computed from those bytes with `hashlib`. The
bytes are authored from ADR-0100 and the framing rules, not produced by calling `semantic_value`
or `canonical_bytes`. The set varies, one at a time:

- **the domain tag:** the same value under another domain gives different bytes and digest;
- **the nesting of the subject context:** `subject_context` is a nested mapping with its four
  fields, the scope carried as decimal-valued JSON meaning; a vector with the context fields
  flattened into the outer mapping is a distinct, wrong input and must not match;
- **local-subject qualification:** one local `subject` under two projects, two original sources
  and two analyzed scopes yields distinct keys, and `subject` appears both at the top level and
  inside the context.

The same literal context then goes through the deployed native identity function
(`data.ddo_identity`, `sql/data_operations.sql:73`) in the read class, in
`test_data_operation_identity_native.py`, and must give the literal key. The storage test's
Python-to-stored comparison stays as an agreement check.

**Uncalled helpers.** `product_identity` (`:426–434`) and `subject_identity` (`:407–419`) have
no caller: a word search of `src/` and `tests/` on 2026-11-13 finds only their definitions and
`tests/semantic/test_data_operation_identity.py:25,31,305–317`. Once that search is repeated at
implementation time, both functions and
`test_subject_occurrence_context_order_and_product_provenance_separation` (`:297–317`) are
deleted. TS-19 deletes them in this series unless the DDO identity package has already removed
them. This removes production source under the DDO session's edit, so the two sessions agree
which commit carries the deletion. The vectors do not wait for it, but DTA-033 closes only when
the helpers are gone, whichever package removed them.

**One JSON-meaning table.** Three places hold JSON-meaning checks: storage `:2171–2198` (the
deployed function), `test_data_operation_identity_native.py:90–136` (source text in `pg_temp`,
the same eight vectors verbatim) and `test_data_operation_json.py:79–116` (source text, a
different fractional-scope case). The eight-vector table moves to one place in the
identity-native module, consumed by the deployed-function check (read class) and the source-text
check (rollback class); the storage copy is deleted. The fractional case in the json module is a
different claim and stays.

**Revealing failure.** Change the domain string in `contextual_product_identity` and in the SQL
together: today everything passes; with the vectors, the pure test and the native test both fail.

**Acceptance** (review closure for DTA-033). A vector fails for a changed domain tag, changed
nesting, or changed local qualification; the two helpers and their test are gone, by this
package or by the DDO identity package; one copy of
the eight-vector table remains.

**Verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_data_operation_identity.py`
and `…/test_data_operation_identity_native.py`. A deliberate identity change migrates the
vectors with it, as ADR-0100 says.

## TS-20 — Wire-checked double and binding parity

**Required input.** TS-05 (rollback class), TS-17 (support modules).

**`WireCheckedStorage`.** Production `DataOperationStorage.invoke` validates the input and the
output of every native call (`src/…/semantic/data_operation_storage.py:320–341`, calling
`validate_native_wire`, `data_operation_wire.py:307`). Two routing tests replace the whole
object with a class that returns hand-written dictionaries
(`tests/semantic/test_data_operation_demands.py:216–219`,
`tests/semantic/test_data_operation_service.py:16–27`). The double in support takes the replies,
refuses an unknown operation name, validates the input with `validate_native_wire(name,
"input", …)`, records the call, validates the hand-written reply with `validate_native_wire(name,
"output", …)` and returns it. A routing test then fails when the planner or service emits or
accepts a shape the wire forbids. Payloads the wire rejects are fixed, not tolerated: by a
contributor's reading the service test's pins (`"frontier_at": "now"`, `"selection": {"model":
"frozen"}`, `:29–39`) and the demands test's partial snapshot (`:206–213`) are candidates; each
is settled by running it through the validator.

**Binding parity.** DDO-03's own obligation is the specification
(`docs/plans/declared-data-operations/contracts-and-compilation.md:356`): native and Python
binding-result boundaries retain an independently specified set of members and roles,
positions, support and witnesses, tested for too many and too few roles, wrong-source joins, two
distinct passages sharing text, present-empty versus unknown optional input, incomplete negative
lookup, member addition and removal, and unselected alternatives, with explanations that
identify the actual unmet obligation. Today no file runs one case set through both paths.

The case table in binding support holds, per case, the admitted rows, the declared roles, and
the authored expectation: selected members by role and position, support and witnesses, or the
refusal and the obligation it names. Nothing in the table is computed by either implementation.
Two executors consume it, both in the rollback class:

- **compiled:** `compile_binding` and `execute_binding` on a PostgreSQL connection, the route
  production takes on the planner's connection
  (`src/…/semantic/data_operation_demands.py:658`); the admitted-rows table that the `storage`
  fixture builds on SQLite today (`test_data_operation_bindings.py:104–130`) is created inside
  the case transaction and rolls back with it;
- **native:** the binding functions installed by the binding connection
  (`test_data_operation_binding_native.py:42–72`).

**The SQLite runs go.** `create_engine("sqlite://")` at `test_data_operation_bindings.py:130`
and `test_data_operation_consumer_bindings.py:88` is removed unless a supported consumer
executes bindings on SQLite; none was found, and SQLite's null and ordering semantics differ.
The existing compiled-binding tests keep their assertions and move their fixture to the rollback
class; tests in those modules that never touch the engine stay pure. The cost is plain: these
modules now need a deployed head, where they needed none. With a reused head and one family
clone per worker that is a small fixed cost per run, and it buys the dialect production uses.

**Revealing failure.** A case with a present-empty optional input and one with an unknown
optional input give the same result on one path and different results on the other. Today that
cannot be seen; with one table it fails on the diverging executor, naming the case.

**Acceptance** (review closure for DTA-034). The two routing tests use `WireCheckedStorage`; one
case table runs through both binding paths on PostgreSQL; no test source names `sqlite://` in
the two binding modules.

**Verification.** `uv run ci test --` with the demands, service, bindings, consumer-bindings and
binding-native module paths.

## TS-21 — Cutover transfer

**Gate.** Each retiring DDO package. Current DDO package state is read from the
[DDO coordinator](../declared-data-operations_2026-11-12.md), not copied here. This series
prepares; the transfer itself happens in the commit that retires a mechanism.

**The rule** (review §4.8; it applies the DDO plan's own text at
`docs/plans/declared-data-operations/preservation-adoption-and-qualification.md:53–55`,
`change-reuse-and-consolidation.md:74–77` and `demand-planning-and-execution.md:327–329`):

1. A test whose every assertion restates the removed mechanism is deleted in the retiring
   package's commit. The commit names the test and the surviving-surface control that covers the
   same behavior.
2. A mixed test is re-expressed on the surviving surface before the mechanism goes. The cheap
   route is through support: a staged builder or recipe is re-pointed once and its tests follow
   (`build_domain_case`, `build_resubmission_case`, `projection()` in
   `tests/orchestrate/test_source_progress.py:71`).
3. Behavior with no counterpart on the new surface gets one before removal. The audit found none
   for source-view batching, readiness progress and characterization recovery.
4. Closure per package: a word search of `tests/` for the mechanism's names returns nothing, and
   each deletion is named in a commit. No per-test register is kept.

**Mechanisms, owners and affected tests.** Owners are as the DDO plan names them. File lists are
a word search of `tests/` on 2026-11-13 (occurrence counts in parentheses).

| Mechanism | DDO package that retires it | Test files naming it |
|---|---|---|
| `reused_task_id`, copied reused status | Not named as an identifier in the DDO plan. Copied reused-task fulfillment retires "only with their DDO-07/08/10 callers moved" (`products-and-support.md:104–105`), copied reused status with DDO-09 (`change-reuse-and-consolidation.md:74`), "copied reused tasks" at DDO-11 step 6 | `semantic/test_operations.py` (4), `test_runtime_bindings_native.py` (2), `test_coverage_comparison.py` (2), `test_retained_source_budgets.py` (2), and one each in `test_retained_source_reuse_native.py`, `test_local_semantic_admission_native.py`, `test_pdf_visual_requests.py`, `test_pm2_result_native.py`, `test_reference_evaluation.py`, `test_review_bundle.py` |
| `valid_reuse` runtime equality | DDO-09 | `semantic/test_runtime_bindings_native.py` (1), `test_dossier_contributions.py` (1) |
| `task_dependency`, `task_dependency_scope` | DDO-09 | `semantic/test_source_jit_native.py` (3), `test_source_views.py` (1) |
| `freshness_seed`, run-anchor, freshness salts | DDO-06 step 4 (`demand-planning-and-execution.md:324`); salts DDO-09; DDO-11 step 6 | `orchestrate/test_characterization_recovery.py` (4), `semantic/test_characterization_native.py` (1) |
| `source_dependencies` | DDO-06 step 4; DDO-08 (`operations-and-adapter-cutover.md:58`, `:111`) | `methods/test_m1_readings.py` (2), `semantic/test_characterization_native.py` (1), `test_source_views.py` (1) |
| `OperationDescriptor` bypasses | DDO-08 (`operations-and-adapter-cutover.md:58`) | `semantic/test_characterization_native.py` (2) |
| `SourceOperationLink`, stage-run sequencing | DDO-06 step 4, "only when native Demand reporting and public consumers carry its required lineage" (`:325–326`) | `orchestrate/test_source_progress.py` (5), `test_characterization_recovery.py` (2) |
| `max_active_stage_runs` | Not named in the DDO plan; nearest is DDO-06's stage-run retirement. The DDO owner names the package | `orchestrate/test_ready_coordination.py` (3), `test_execution_preparation.py` (1), `core/test_execution_policy.py` (1) |
| `TopologicalSorter` classification | DDO-08 (`operations-and-adapter-cutover.md:87–93`) | No test names it; `semantic/test_domain_operations.py:508` asserts the "cyclic source claim reference" text tied to it |

**Per-file leads.** These are the supporting document's Part B.3: a contributor's dispositions,
mostly by token match, with line numbers as that contributor read them at `28b4a53db`. They were
not re-read here. They are inputs to each retiring package, not decisions.

| File (`tests/`) | Lead: mechanism-only | Lead: mixed, re-express | Counterpart cited |
|---|---|---|---|
| `semantic/test_operations.py` | Reuse status and `reused_task_id` (`:415`, read), nine forged-reuse cases (`:562`, read), freshness as invocation salt (part of `:827`) | Terminal fence, exact replay, sealed cut; wrong attempt; cancel drains claims; stale lease | Storage publication and replay, expired owner, writer bypass, cancellation |
| `semantic/test_runtime_bindings_native.py` | Reuse part of `:180` (read) | Runtime-change fence; altered bindings; immutability | Storage revoked and invalid runtime tests |
| `semantic/test_source_jit_native.py` | `ops.task_dependency` assertions | Stale completion refused after reclaim | Population fan-in (partial); none for source-view batching |
| `orchestrate/test_characterization_recovery.py` | Anchor, run-option link, freshness seed (five tests, read) | Capacity-policy change, receipt failure, provider identity | None found |
| `orchestrate/test_source_progress.py` | One reused-count assertion | About eight readiness tests through `projection()` | None found |
| `orchestrate/test_ready_coordination.py` | The stage-cap parameter only | Claim and byte-budget behavior | `orchestrate/test_data_operation_batch_activity.py` (partial) |
| `semantic/test_characterization_native.py` | Mechanism inputs in three tests | Publication, sealing, size limits; most tests need re-fixturing | None |
| `semantic/test_domain_operations.py` | None | The cyclic-reference expectation, which DDO-08 replaces with the A↔B→C, D and self-loop set | — |
| `semantic/test_retained_source_reuse_native.py` | All seven assert through `reused_task_id` | Re-express as selection of exact pins and refusal of mismatches | DDO selection in population and consumer native tests |
| Further files in the table above | Field-only uses | Keep, minus the retired field | Per file at the owning package |

**What this series prepares now.** TS-07's staged builders give `build_domain_case`,
`build_resubmission_case` and the progress `projection()` one place to re-point. TS-17's demand
helpers and TS-18's `ddo_kernel` are the surviving surface a re-expressed test lands on. TS-18's seeds
make a re-expressed native test cheap enough to write per behavior. None of this deletes or
rewrites a test of the old path: that path is live until cutover and its tests are current
evidence for current code.

**What waits for each DDO package.** The classification of each test (delete or re-express), the
counterparts for the three uncovered behaviors, and the deletions. The retiring package's owner
does them with the rule above; the leads save the search.

**Acceptance** (review closure for DTA-035). Per retiring package: no test source names the
retired mechanism, and each deletion is named in a commit that cites its surviving control.

## TS-22 — DDO-12 evidence mapping and provider run

**Gate.** TS-13 (provider and controlled identities split) and DDO-12. This series delivers two
things: the evidence mapping, as the table in this section, and the provider run. It does not
edit the DDO plan. Adding the mapping to DDO-12's own obligation table is the DDO owner's edit
at DDO-12 time, and the coordinator lists it as a handover.

**The union, as refined.** The four path lists in the DDO coordinator are receipts of bounded
campaigns and say they are not DDO-12. DDO-12 already defines the union
(`docs/plans/declared-data-operations/preservation-adoption-and-qualification.md:65–70`): after
all functional scope and retirement, freeze final source and run `uv run ci test` and
`uv run ci check`, with native fault and provider lanes explicitly covered and missing providers
kept open. The target form has three parts.

1. The full ordinary and fault lanes on frozen final source, with a run-private head (TS-02).
   This covers every DDO module by construction, including those in no recorded campaign.
2. One provider run with the provider prerequisites present. After TS-13, provider-gated
   identities are distinct from their controlled counterparts, so in this run each either passes
   or resolves `blocked` with its prerequisite named in the receipt. A controlled identity never
   stands in for a provider row.
3. An evidence mapping for DDO-12's obligation table (`:72–81`): the table below, completed at
   DDO-12 time, names the test identities that discriminate each row and states which rows
   still lack evidence. It is handed to the DDO owner, who can carry it into that table as an
   evidence column; DDO-12 consumes its own table, so this adds no register.

**The eight rows and what is known to belong in the mapping.** Row names are the DDO plan's. The
assignment of gaps to rows is this author's reading and is confirmed with the DDO owner.

| Obligation row | Evidence to name (leads) | Known gaps to state until closed |
|---|---|---|
| Model/compiler/identity | Compilation, identity and identity-native modules; TS-19's contextual identity vectors | Graph example sets; helper-body and inherited-value change locality in the source-change matrix |
| Binding and native admission | Binding-native module; TS-20's case table through both paths; purpose refusals in storage | One case set through both binding implementations, until TS-20 lands |
| Native request/concurrency/recovery | Storage concurrency, expiry, cancellation and replay tests; DDO-06's checks as they are written | Overlapping publication with differing intents; invalidated support recovered through a real consumer |
| Providers | Provider identities from the provider run | Any identity that resolves `blocked`; no mocked provider counts |
| Reuse/change | DDO-09's checks as written; the re-expressed tests from TS-21 | Helper-body and inherited-value locality; whatever TS-21 leaves without a counterpart |
| Serving/evaluation | Named by the DDO owner at DDO-10 | Not assessed by the audit |
| Retained whole document | Named by the DDO owner at DDO-11 | Not assessed by the audit |
| Generality | Named by the DDO owner | Not assessed by the audit |

**Acceptance** (review closure for DTA-036). At DDO-12 the mapping table here names
discriminating test identities, or states the gap, for each obligation row and has been handed
to the DDO owner; the provider run's receipt shows provider identities `passed` or `blocked`.

**Verification.** `uv run ci test` and `uv run ci check` on the frozen source; the provider run
through the managed route with prerequisites present. Results are read from their managed
receipts by id.

## Handovers to the DDO plan owner

The coordinator holds the one list
([Handovers to other owners](../test-system-target-design_2026-11-13.md#handovers-to-other-owners)):
RC03; the ordering of TS-05, TS-06 and TS-17 before DDO-06 and the gating of DDO-06 to DDO-12
on TS-21 and TS-22; the edit to the DDO-12 obligation table; the coordinated deletion of the
two uncalled identity helpers; the stale findings-table rows; the double deployment
verification in `admit_data_operation_release`; the lease-update question; the package that
retires `max_active_stage_runs` and `reused_task_id`, which the DDO plan does not name; and the
assurance gaps. This companion adds no second copy.

## What remains outside this companion

- The isolation-class fixtures, the seed operation and the recipe contract are designed in
  [isolation classes and scenario seeds](isolation-and-seeds.md) and
  [scenario and support ownership](scenario-and-support-ownership.md); this companion consumes
  them.
- The refusal contract (reach, reason, effect) for the DDO refusal families, including the
  forged-graph reasons, is [evidence contracts](evidence-contracts.md), TS-09.
- The provider and controlled identity split is TS-13 in the same companion.
- Production changes to the DDO kernel, the DDO plan's packages and its documents belong to the
  DDO plan's owner.
