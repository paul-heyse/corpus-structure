# Isolation classes and scenario seeds

**Status:** Proposed plan; nothing implemented. **Created:** 2026-11-13.

This companion owns the designs of TS-05 (isolation-class fixtures), TS-08 (the seed operation),
TS-10 (rollback families and read-class checks) and TS-11 (commit-class consumers on recipe
seeds). The [coordinator](../test-system-target-design_2026-11-13.md) owns package state, the
dependency queue and the disposition of every finding named here; this page does not restate them.

**Baseline and evidence.** Source was read on `main` between `f03170a89` and `434023ee8`,
2026-11-13, while another session was committing declared-data-operations (DDO) work; line
citations are as read. Every design statement is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-13**. Durations quoted from the audit are
**Measured** from stored results on a shared workstation and are orders of magnitude. Receipts
that show one seed or one family clone per worker are functional evidence, not speed claims.

**Revision input:** [I01/I02/I10](../../plan_improvement_reviews/test-system-target-design_2026-11-13.md)
integrated against clean source `b1b4a4de0` (2026-11-13). The operator accepted I02's
infrastructure-base change on 2026-11-13; TS-00 routes RC05 through the ADR-0032 successor.
All fixture and production changes described here remain **Proposed**.

**Paths.** `tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written
as root `tests/…`, `scripts/…`, `conftest.py`, `pyproject.toml`. Section references (§4.1 and so
on) are to the [source review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md).

## Current baseline and what is reused

- **One lifecycle owner.** `PgAdmin.database(name, source, policy=…)` (`scripts/native_test_support.py:444`)
  leases an absent name, creates it through the acknowledged path, replays the captured policy and
  drops it with an authenticated, unforced drop. Every database in this companion is created
  through it. `principal_engine` (`:633`) resolves a purpose login against the original endpoint
  and binds it to one owned database.
- **A rollback idiom.** `rollback_connection(engine)` (`:54–61`) lends one connection whose outer
  transaction rolls back on exit. The `db` fixture (`tests/conftest.py:288–292`) applies it to a
  per-worker session clone, `db_engine` (`:279–285`, named `ci_test_<pid>`).
- **A commit idiom.** `semantic_db_engine` (`tests/semantic/conftest.py:27–34`) is a fresh clone of
  the head per test, with purpose engines beside it (`:60–101`) and an alias `admitter` (`:104–106`).
  At the baseline 165 test files name a fixture of this family (149 name `semantic_db_engine`).
- **A sealed seed.** `tests/semantic/serving_scenarios.py:241–344` builds one committed scenario
  per worker through real producers, checks policy, seals it, revalidates before each clone and
  hands each consumer a fresh clone whose connections record `scenario_seed` in the receipt
  (`scripts/native_test_support.py:746`).

What does not exist: a way for a test to say which isolation its claim needs. A test that only
reads, a refusal family whose every write rolls back and a test that commits across logins all
request the same fresh clone, and thirteen cases of one refusal each rebuild one committed scenario.

## Target design and contracts

A test requests one of four classes by fixture. There is no implicit default (§4.2). Cold
deployment fixtures (`semantic_bare_engine`, `semantic_database_at`) are a fifth named kind
outside the four classes: a test whose claim is a bare or partly migrated database requests one
of them, and they keep running the real chain.

| Class | The test receives | Base | How the premise is enforced | Valid uses | Invalid uses |
|---|---|---|---|---|---|
| pure | No native resource | — | No native fixture in the closure | Compiler, codec, wire, preparation, routing | — |
| read | One `Connection` in a `READ ONLY` transaction, always rolled back | The per-worker session clone of the head | PostgreSQL refuses writes, DDL and temporary tables with `25006` | Literal-argument calls of installed functions, catalog reads, identity vectors | Privilege refusals of writes: the read-only check runs first, so `25006` masks `42501` |
| rollback | A case object: a writable maintenance connection, principal connections on request, and a reader engine whose sessions are forced read-only. No writable `Engine` | The per-worker session clone, or one family clone of a seed | Each lent connection's outer transaction must still be active at teardown; the case proves reach and reason ([TS-09](evidence-contracts.md)) | DDL installed and used in one transaction; refusal families whose writes all roll back; permission refusals; single-session `SERIALIZABLE` refusals | Separate-login visibility of uncommitted work, commits, races, cancellation, `NOTIFY`, session-level locks or settings, assertions on absolute generated ids, product code that commits on its own connection |
| commit | An `Engine` on a fresh committed clone, with purpose engines | The head, or a seed | Its own database | Everything else | — |

**What consumers stop doing.** Choosing isolation by which fixture happened to be imported;
rebuilding an identical committed scenario per case; creating databases by hand
(`test_serving_scenario_lifecycle.py:39`); re-exporting engine fixtures across directories.

**Preserved guarantees.** Fresh committed clones with real logins wherever a claim commits, races,
cancels or needs a second login. Policy capture, replay and comparison for every clone, seed and
seed clone. Authenticated, unforced drops. Real producers and real purpose engines in every seed
build. Receipts that distinguish a seed's origin from the clone a test used. Cold deployment
controls (`semantic_bare_engine`, `semantic_database_at`, `semantic_absent_database`) are untouched
and stay requestable as their own kind.

**Infrastructure is a distinct base (I02).** Driver-only claims use provisioned `cs_template`
through the same `PgAdmin` naming, leases, acknowledged creation, policy replay and authenticated
cleanup. They acquire neither the semantic head nor its key/checker. Shared infrastructure
connections serve read-only SQL and connection exercises with no durable effects; a rollback
connection also permits transaction-local utility DDL/DML. A case that creates durable state gets
an isolated infrastructure clone. This is a fixture-base distinction, not another lifecycle or a
semantic shared-engine exception. Semantic guards and semantic catalog expectations still use
the four classes above. Cold routes remain separately named.

**Intentional behavior changes.** No writable `Engine` is exposed on a shared semantic clone.
The earlier `shared_clone_engine` target and its durable-state comparator are removed.
A test in the wrong semantic class fails loudly: a hidden write in the read class raises `25006`; a commit
through a rollback-class connection fails teardown; a production path that commits on its own
connection is exposed by the next case's positive control and absence checks. Fixture names change
for about 165 files.

## Pivotal mechanisms

| Mechanism | Use here | Limit that shapes the design | Reference |
|---|---|---|---|
| `CREATE DATABASE … TEMPLATE` from a sealed source | Seed, family clone, commit clone | Refused while any session is connected to the source, after up to five seconds; so a seed is sealed and client-free before any clone | §7 row 1 |
| What a clone carries | Objects and in-database grants only | `datacl`, settings and the ownership comment are not copied; policy replay stays per clone | §7 row 4 |
| `DROP DATABASE` | Every clone drop | Forces an immediate checkpoint of the cluster; fewer clones is the safe lever | §7 row 3 |
| Read-only transactions | Read class; the rollback class's reader engine | `25006` precedes the privilege check | §7 "Read class" |
| Core `begin()`, `begin_nested()`, isolation set before `begin()` | Rollback class | Sequences do not roll back; `now()` is fixed per transaction; `NOTIFY` is never delivered | §7 "Rollback class" |

## TS-05 — Isolation-class fixtures

**Required input.** TS-00 (the successor to [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md)
allows read-only/rolled-back semantic transactions and records RC05's infrastructure base),
TS-01 (the naming function, including infrastructure kinds), and the TS-02 early acquisition
slice (head-derived clones are verified before exposure without requesting a class fixture).
TS-02's remaining publication/retention work is not a reason to make verification depend on
TS-05, and infrastructure-only fixtures do not acquire the semantic handle.

**Implementation vision.** All class fixtures live in the package `tests/conftest.py`, so every
test directory sees them without imports. Fixture names below are this package's proposal and are
fixed in its first change; other companions use them.

- **Session clone.** This package owns the per-worker semantic session clone, `ci_test_<pid>`.
  Today's `db_engine` becomes its private base, created lazily only when a `native_read` or
  `native_rollback` consumer needs it. Request the clone through TS-02's acquisition handle,
  which verifies it if verification is pending and returns it only after success. Commit-only,
  seed-only and infrastructure-only selections do not instantiate this clone. The clone's
  writable `Engine` is private to the fixtures; verification never calls back into them.
- **`native_read`.** Opens a connection on the session clone, starts a transaction with
  `postgresql_readonly=True`, yields the `Connection` and rolls back. It connects as maintenance;
  a claim about what a restricted login may read uses the rollback class.
- **`native_rollback`.** Yields a `RollbackCase` built by one support function over a base
  database name, so the same object serves the session clone and a seed's family clone:
  - `connection`: a maintenance connection inside an outer transaction (today's `db`).
  - `principal(purpose, isolation_level=None)`: a context manager yielding a connection logged in
    as that purpose's real role, inside its own outer transaction; the isolation level is applied
    before `begin()`. Product code that uses `SET LOCAL ROLE` works unchanged.
  - `reader`: an `Engine` whose sessions are forced read-only (connected with
    `default_transaction_read_only=on`, under the purpose the fixture is asked for). The
    operator allowed it on 2026-11-13 and the ADR-0032 successor names it. It exists
    because `_cut_input(engine, …)` (`src/corpus_structure/semantic/domain_operations.py:818–824`)
    opens its own `REPEATABLE READ` read-only connection on committed state, and five refusal
    families call it. It sees committed state only, never a case's uncommitted writes.
  - Teardown asserts every lent outer transaction is still active (`Transaction.is_active`), then
    rolls back and disposes. An inactive outer transaction means the body committed or rolled back
    the fixture's transaction; the test fails with that message.
- **Commit class.** `semantic_db_engine` and its purpose engines move from
  `tests/semantic/conftest.py` to the package conftest under names that say what they are:
  `commit_db_engine`, `commit_writer_engine`, `commit_reader_engine`, `commit_evaluator_engine`,
  `commit_admitter_engine`, and `commit_application_settings` for today's
  `semantic_application_settings` (`tests/conftest.py:233–239`). A factory fixture
  `commit_clone()` yields a further fresh clone of the head for the tests that need two databases.
  The `admitter` alias goes; its six consumer files name the admitter engine directly.
- **Infrastructure fixtures.** `infrastructure_engine` yields the shared per-worker maintenance
  engine on a clone of provisioned `cs_template` for pools, scalar SQL, notices, cancellation,
  reuse and backend-settlement exercises with no durable state. `infrastructure_rollback`
  lends an outer transaction on that base and rolls it back, enforcing the same active-outer-
  transaction rule as `native_rollback`. `infrastructure_commit_engine` yields a fresh isolated
  clone for durable DDL/DML or cases whose effects otherwise need isolation. Capture the
  template policy and replay/compare it per clone; use the TS-01 infrastructure name kinds.
  Extension/version checks and real maintenance authentication remain prerequisites. These
  fixtures do not request semantic principals, the semantic head or a durable-state comparator.
  Their names state the infrastructure base; they are not aliases for semantic fixtures.
- **Native server prerequisites.** Keep `native_server` as the common `PgAdmin` acquisition,
  extension/template checks, sweep and observed server context. Move its current unconditional
  `semantic_principals()`/`check_roles()` to the semantic acquisition/cold-route prerequisite
  that actually needs those logins. Semantic purpose fixtures still fail when their roles are
  missing; infrastructure-only acquisition requires only its actual maintenance/template
  capabilities. Do not turn a missing semantic role into a backend-only refusal.
- **Cold deployment fixtures.** `semantic_bare_engine` and `semantic_database_at`
  (`tests/semantic/conftest.py:37–57`) stay where they are and keep their behavior. They are
  the fifth named kind: a consumer whose claim is a bare or partly migrated database requests
  one by name and is not asked to pick one of the four classes.
- `DB_FIXTURES` (`tests/conftest.py:71–88`) lists the new names so the `db` marker keeps applying.

**Consumers migrated.**

- The rename of the `semantic_*_engine` family is mechanical and is done with this package in one
  change: fixture parameters, `from semantic.conftest import … as …` re-exports (for example
  `tests/evaluate/test_record_policy_native.py:5–6`) and `tests/acceptance/conftest.py:3–4`, which
  disappear because the package conftest already provides the fixtures. This package removes
  them; [TS-06](scenario-and-support-ownership.md) does not claim them. No test changes class
  in this step.
- Classify actual legacy `db`/`db_engine` consumers by claim rather than renaming all `db`
  uses to `native_rollback`. The focused source inspection at `b1b4a4de0` found requestable
  `db_engine` consumers in the three `tests/db` modules and `tests/test_db_fixtures.py`, plus
  `db` fixture consumers in `tests/core/test_method.py` and `tests/db/test_store.py`. Local
  variables named `db` in PDF scenarios are not uses of this fixture.

| Actual consumer | Target and reason |
|---|---|
| `tests/db/test_store.py`: pool/JSONB, extension-version refusal, notice callback | `infrastructure_engine`; no semantic guard/schema used. `observed_store_checkouts` observes this selected engine, retaining actual pool provenance |
| `test_store.py::test_errors_are_classified` | `infrastructure_rollback`; scalar error and temporary-table constraint classification inside savepoints |
| `tests/db/test_lifetime_native.py`: pooling, cancellation/COPY, renewal exit/deadline, runtime diagnostic | `infrastructure_engine`; preserve real queries, auth, cancellation, reuse and backend settlement |
| `test_lifetime_native.py::test_mid_write_native_failure_has_independent_zero_row_rollback` (`:162`) | `infrastructure_commit_engine`; commits an ordinary `public.pg_runtime_effect` table, then independently checks zero rows after failure |
| `tests/db/test_adbc_lifetime.py`: resolver parity, real cancel/reuse, binding-query cancellation (`:300`) | `infrastructure_engine`; binding is patched before semantic work to run `pg_sleep`, and cancellation forbids bulk acquisition, so this claim needs no semantic guard |
| `tests/core/test_method.py`: payload hash/JSONB round trip (`:174,187`) | `infrastructure_rollback`; utility table and casts only |
| `tests/test_db_fixtures.py`: rollback helper (`:36`), extension checks (`:92,108`), generic lease/sweep controls | Infrastructure transaction/server as appropriate; the retained-head exclusion control explicitly requests a head when it asserts that property |
| `tests/test_db_fixtures.py`: migrated-template identity (`:21`) and cold build (`:178`) | Explicit semantic session/acquisition and cold fixtures; their claims depend on the semantic revision and real chain |

Read remaining fixture-closure consumers, including dynamically requested fixtures and new source
changes, when implementing. An actual semantic guard caller receives an explicit semantic
fixture; a newly found durable infrastructure case receives its isolated fixture. No module-wide
assumption may silently move semantic claims onto `cs_template`. Pure cases in these modules
remain pure. `observed_store_checkouts` changes together with its callers so it never lazily
recreates the old `db_engine` path.

**Superseded machinery removed.** The engine fixtures in `tests/semantic/conftest.py` (the file
keeps `database_name` only until TS-01 replaces it, and the cold-route fixtures), the acceptance
conftest's re-exports (and the file, which holds nothing else), the `admitter` alias, and `db`
and `db_engine` as requestable names. The old `shared_clone_engine` proposal is not implemented;
no fixture or semantic durable-state comparator for it is introduced. Remove the unconditional
semantic-role prerequisite from common infrastructure acquisition while retaining it at semantic
consumers.

**Example and failure case.** A check of `data.local_semantic_case_matches` requests `native_read`
and runs seventeen cases on one clone. If someone later adds a temporary table to that function,
every case fails with `25006`, naming the hidden write. A refusal case that calls `publish_batch`,
which commits on its own connection, passes alone; the next case's absence check finds the
committed batch and fails, pointing at the leak.

**Acceptance and closure.** Each class fixture has a self-test in the package's
`tests/test_db_fixtures.py`: a write through `native_read` raises `25006`; a
commit through `native_rollback.connection` fails teardown; a principal connection reports the
purpose's `session_user`; the reader engine refuses a write; `commit_clone()` yields a fresh
OID. Infrastructure controls retain actual extension/authentication and cancellation/reuse;
isolated durable-write cases receive distinct OIDs and cannot affect the shared infrastructure
base. A backend-only selection creates neither a semantic head nor `ci_test_<pid>` and does not
check semantic roles; an explicit semantic acquisition still refuses missing semantic roles.
No source names `semantic_db_engine`, `semantic_writer_engine`, `semantic_reader_engine`,
`semantic_evaluator_engine` or `semantic_admitter_engine`. `test_lifetime_native.py` no longer
commits through the semantic shared clone. No fixture yields a writable `Engine` on a shared
semantic clone. Every legacy fixture consumer is classified and migrated, including its observer;
no semantic comparator or `shared_clone_engine` fallback remains.

**Verification.** `uv run ci test -- python/corpus-structure/tests/test_db_fixtures.py
python/corpus-structure/tests/db`, then one module per directory that used the old names. The
rename is checked by collection of the whole package (`--collect-only` through the managed route).

**Implementation judgment.** The table is the inspected migration scope, not an enduring
catalog. Re-read affected bodies at execution, especially patched semantic entry points: a test
whose patch no longer intercepts before a semantic guard must request an explicit semantic
fixture or preserve an independently meaningful infrastructure-only boundary. Keep any newly
found durable effect isolated rather than adding a comparator to the shared base.

## TS-08 — The seed operation

**Required input.** TS-00 (the successor to [ADR-0048](../../adr/0048-populated-native-scenarios.md)),
TS-01 (a `seed` kind in the naming function), the TS-02 early acquisition slice (first useful
clone verification before a seed builder), TS-03 (the implementation override, so a build can
refuse to run under one) and TS-06 (the recipe value). The seed operation needs this working
clone contract, not a TS-05 session clone or the whole SQL/TAP/private-cluster harness described
in [PostgreSQL tooling](postgresql-tooling.md).

**Implementation vision.** `scripts/native_test_support.py` gains one seed registry, held per
worker by a session-scoped fixture in the package conftest (`scenario_seeds`). It generalizes
`_serving_seed_lifecycle` and `_validate_serving_seed` (`serving_scenarios.py:218–285`).

| Step | What the operation does | Generalized from |
|---|---|---|
| Key | `(recipe value, head name)`. The recipe is the frozen, data-only value of [TS-06](scenario-and-support-ownership.md). The builder is not part of the key: TS-06's rule gives each recipe type exactly one registered builder, so the recipe type implies it | `_serving_recipe_id` (`:195–205`), which hashed builder source instead |
| Build, on a fixture's first request | Refuse if an implementation override is active (`implementation_overridden()`, TS-03). Request `cs_sem_seed_…` through the head acquisition handle, which creates it through `PgAdmin.database`, verifies a pending reused head on that clone and retries a stale source before exposing it. Only then look up the recipe type's builder in TS-06's registry and run it with the admin engine, purpose engines from `principal_engine`, and a directory from `tmp_path_factory.mktemp("seed-…")`. A recipe's own provider patches are applied by that builder inside `pytest.MonkeyPatch.context()` and are removed before sealing. Dispose every engine | `:249–260` |
| Posture checks | Policy equals the head's; record the OID; no task in the seed is unfinished, meaning none is in a claimed or running state (the check reads task status and does not consult `lease_until`, so an expired lease does not pass); then `ALLOW_CONNECTIONS false`; then confirm sealed and client-free | `:262–264`, `:283–284`, `:231–238` |
| Files | Every file the builder wrote is made read-only, and so is the directory, so a consumer that writes into scenario files fails instead of changing the next consumer's input | new |
| Descriptor | A frozen value: database, OID, policy, recipe id, the builder's frozen stage output, the directory, and `origin` for receipts | `ServingScenarioSeed` (`:161–182`) |
| Revalidate before each clone | OID and policy unchanged, still sealed and client-free | `_validate_serving_seed` |
| Commit clone | `scenario_seeds.commit_clone(recipe)`: a fresh clone with policy replay and a fresh OID; purpose engines carry `scenario_seed=origin` | `serving_read_scenario` (`:300–344`) |
| Family clone | `scenario_seeds.rollback_family(recipe)`: one clone per worker per recipe, left open, wrapped by the same `RollbackCase` as TS-05; each case gets new connections. It is called from one named fixture per family (TS-10) | new |
| Lifetime | The worker's session. Family clones are dropped before their seed; all head-derived clones are released before the acquisition handle's usage lease. No session clone is required. A failed build releases its database, as `test_failed_seed_build_releases_owned_database` requires today | `:73–97` of the lifecycle test |

**What a seed may contain.** Committed state with **no unfinished task** (operator decision,
2026-11-13; stated in the ADR-0048 successor). Completed attempts are allowed:
`build_domain_case`, `build_resubmission_case`, `exclusion_result` and the serving seed all end
with completed attempts and no task claimed or running, and consumers take their own claims on
their clone, so lease freshness and attempt numbering are as today. A task that is claimed or
running keeps a seed from sealing whether or not its lease has expired. A seed holds no
session-level state and nothing produced under an implementation override. Consumers that assert
a time relation between seeded stamps and their own clock, or absolute generated ids that the
descriptor does not record, are not seed consumers.

**Who may request a seed.** Fixtures only. `scenario_seeds.commit_clone(recipe)` and
`scenario_seeds.rollback_family(recipe)` are called by fixtures, which resolve before the test
body runs and therefore before any patch the body applies. A test body, or a builder called
from a body, never requests a seed. No detection of a live patch is attempted; this ordering
is the rule, and it is checked by search. The one condition that is detectable, an installed
implementation override, is refused at build time.

**Receipts.** `origin` is a string mapping with `scenario` (the recipe's label), `recipe_id`,
`source_database`, `source_database_oid` and the head name; a recipe may add fields (the serving
seed keeps `release_id` and `manifest_digest`). It travels through the existing `scenario_seed`
argument of `principal_engine` and `observe_engine` (`scripts/native_test_support.py:633–665`).
`database()` gains the same optional argument so a clone's maintenance connection records it too.
Nothing in `scripts/test_receipts.py` changes; it already stores the field (`:492–495`).

**Consumers migrated.** `serving_scenario_seed` and `serving_read_scenario` become a serving
recipe and a thin fixture over `commit_clone`; the serving-specific realization check (`:314–323`)
moves into the recipe's descriptor check. `test_serving_scenario_lifecycle.py` keeps its three
claims against the common operation: a changed descriptor is refused, two clones are isolated
(the second obtained from `commit_clone`, not a hand-written name at `:39`), and a failed build
leaves no database.

**Superseded machinery removed.** `_serving_seed_lifecycle`, `_validate_serving_seed`,
`_serving_recipe_id`, `_database_oid` and the two dataclasses in `serving_scenarios.py`.

**Failure case.** A builder that returns while its record task is claimed fails the
unfinished-task check at build time with the task named, instead of producing clones whose tests
fail five minutes into a run.

**Acceptance and closure.** The serving seed uses the common operation (F03). A seed control
shows: one build for two requests of an equal recipe; a build refused under an implementation
override; a patch applied by a registered builder gone after the build; a builder that leaves a
task claimed or running refused, including one whose lease has already expired; a write into a
seed file refused; a commit clone and a family clone each carry `scenario_seed` in their native
context. A seed-only selection uses its seed-build clone for pending verification, creates no
semantic session clone and starts no builder on a stale source; mixed seed/commit/read consumers
share one completed verification per process. By search, no test body calls `scenario_seeds.commit_clone` or
`scenario_seeds.rollback_family`.

**Verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_serving_scenario_lifecycle.py
python/corpus-structure/tests/semantic/test_serving.py`.

**Open premises.** Whether any consumer re-reads a seeded `original_path` file is unsettled; the
read-only directory makes a read harmless and a write loud, so the first consumers settle it.
TS-03 must expose whether an override is active.

## TS-10 — Rollback families and read-class checks

**Required input.** TS-05, TS-08, the stage outputs of TS-07, and for each family its refusal
contract from [TS-09](evidence-contracts.md). A family moves only together with its contract.

**Membership criterion.** A family joins the rollback class when: its cases share one committed
scenario; every case write happens inside the case's rolled-back transaction; no case depends on a
lease taken before the case began; nothing has session-level effect; and no assertion names an
absolute generated id. A family that fails the criterion stays in the commit class on a clone of
its seed, which still removes the rebuild.

**One named fixture per family.** This package defines, for each family, one fixture with a
name unique across both test trees. The fixture calls `scenario_seeds.rollback_family(recipe)`
with the family's recipe and yields the `RollbackCase`. Cases request that fixture, so the
seed is requested before any body runs and the TS-12 hook can see the family in `fixturenames`.

**Shape of a migrated case.** Request the family's fixture; open a principal connection
(isolation set first where the product uses `SERIALIZABLE`); run the positive control in a
savepoint and roll it back; run the refusal; assert reach, reason and effect. Setup that commits
identically per case today moves into the seed. A family's committing positive case takes a
fixture over `scenario_seeds.commit_clone(recipe)` of the same seed. Each family is one xdist
work unit through the family groups of TS-12 (see the
[run-shape companion](run-shape-and-scheduling.md)); until that lands, cases spread over workers
and each worker builds its own seed.

**Strengths the migration keeps.** The per-case reason tables stay at the call site, one
expected reason per mutation. The transaction-local `plan_cache_mode` replays
(`tests/semantic/test_local_semantic_admission_native.py:546`; review §6.1) stay: `SET LOCAL`
is transaction-scoped, so a replay runs unchanged inside a case transaction, and a family is
not migrated in a way that drops it.

**Scope.** Every family below has a disposition, and the package closes when each is migrated
or holds the disposition stated. The first table was confirmed by a full read of bodies and
builders on 2026-11-13:

| Family | Cases | Target class | Seeds | Moves into the seed | Conditions and blockers |
|---|---|---|---|---|---|
| Forged custody, `tests/semantic/test_private_records.py:131–176` | 12 | rollback | Default record source at the pre-claim stage | Nothing more; the `records` claim (`native_record_fixtures.py:616`) is taken inside the case transaction | The refused call is `complete_task` on that claim. Already the strongest reason form (`23514` plus exact message, `:157–160`) |
| Graph-forbidden products, same file `:223–263` | 8 | rollback, and it moves when it uses `publish_on_connection` (`src/…/semantic/publication.py:728`); until that switch it stays in the commit class on a clone of the seed | Same | — | `publish_batch(engine)` (`:256`, `publication.py:771`) commits with retries. No positive control today |
| Corrupt derived identity, same file `:385–424` | 4 | rollback | Same | — | Uses `SET LOCAL ROLE`. Whether `data.validate_source_record_structure` writes is unverified; the rollback class tolerates it |
| Exclusion tampering, `tests/semantic/test_identity_exclusions_native.py:21–230` | 18 | rollback, `SERIALIZABLE` per case | Two `exclusion_result` recipes: `finalize=False, citations=2, local_ids=("p_","q")` with `attribute_assertions` false (10 cases) and true (8) | The whole builder | `_cut_input` takes the reader engine. Two weak expected strings and no positive control (TS-09) |
| Contextual atomic refusal, `tests/semantic/test_contextual_enrichment_native.py:65–157` | 13 | rollback | Record source with `additional_methods=("private.contextual",)` at the pre-claim stage, plus the curated method, configuration and task | `curated_case`'s committed rows (`native_record_fixtures.py:923–962`); its claim (`:963`) moves into the case | Bare `pytest.raises(DBAPIError)` at `:154` and no positive control (TS-09) |
| Forged judged rows, `tests/semantic/test_local_semantic_admission_native.py:505–660` | 10 | rollback. Declaring and scoping its provider patches is part of this package | `judged_source` with `cases=2, grades=2` | Everything `judged_source` commits | Four provider patches stay live in the body today (`witnessed_scenario_support.py:500,548,551,555`). This package names them as values of the recipe, has the registered builder apply them around the build only, and leaves any patch a case body still needs to the case, applied after its fixtures resolve. Whether the `P0002` assertion at `:622` survives a seeded clone is unverified |
| Occurrence context, `tests/semantic/test_occurrence_context.py:143–199` | 8 | rollback, on the same terms | `_source(outside=False)` over `build_domain_case(duplicate=True)` | The whole builder | `locate_proposal` is patched for the body today (`:46`); this package scopes it the same way. No positive control |
| Imported membership lineage, `tests/semantic/test_imported_declaration_membership.py:228–333` | 6 | rollback for five; `valid` takes `commit_clone` | `imported_declaration_case` (`:43`) | The whole builder, including `consolidate_cut` | `entity`, `class` and `establishment` share one message; `revision` and `run` share another (TS-09) |
| Declared membership lineage, `tests/semantic/test_domain_operations.py:864–992` | 6 | rollback for `class`, `declaration`, `resolution`, `cut`; `valid` takes `commit_clone` | Two: `graph=True, membership_subtype=True`, and the same with `unselected_report=True` for `source_cut` | The whole builder | `source_cut` reads one row across other runs' observations, so its seed has its own family clone and nothing else shares it. Three mutations use `match=None` (TS-09) |
| Case-match function, `tests/semantic/test_local_semantic_admission.py:121–147` | 17 | read | None | — | `data.local_semantic_case_matches` is `IMMUTABLE` with no DML |
| Named-cue dispatch, `tests/semantic/test_contextual_workflow_native.py:29–135` | 10 | read | None | — | `ops.contextual_primary_named_cue` is `STABLE` |
| Permission refusals: `test_identity_exclusions_native.py:233–244` (3), `test_domain_operations.py:246`, `test_occurrence_context.py:315` | 5 | rollback on the session clone, writer principal connection | None | — | All assert message regexes today; TS-09 pins `42501` |
| `test_domain_operations.py:254` | 1 | stays commit | None | — | An admin commits `GRANT TEMP ON DATABASE` (`:257–260`) |

**Lease premise for the two `complete_task` families.** Whether `complete_task` refuses an
expired but unreclaimed lease before its `23514` guard was not determined. Taking the claim
inside the case transaction makes the question moot: the lease is seconds old in every case and
is rolled back with it. The seed therefore ends before the claim, which is the TS-07 pre-claim stage.

**Families the review confirmed, also in scope.** Their bodies were not re-read for this
companion; each is read against the membership criterion when it moves, and one that fails it
takes the commit class on a clone of its seed, which is its disposition then.

| Family | Target class | Note |
|---|---|---|
| `tests/semantic/test_runtime_bindings_native.py:100–148` | rollback | Eight mutations under `23514` alone; TS-09 adds the constraint name or message per mutation |
| The witness refusals of `tests/semantic/test_local_admission_native.py` | rollback | `local_cut` moves into the seed |
| `tests/semantic/test_arrow_publication.py:445–495` | rollback | Six unbound intents under a bare `DBAPIError`; TS-09 pins each |

**Not in scope.** `tests/semantic/test_witnessed_applicability_native.py:172–197` is listed in
the supporting document's Part B.1 and was confirmed neither by the review nor here. It stays
as it is and is not a closure obligation of this package.

**Acceptance and closure.** Every family in the scope tables is migrated or holds the
disposition stated for it. For each migrated family, the receipt shows one seed and one family
clone per worker that ran it; every case asserts positive control, exact reason and absence; no
case body commits (DTA-025). The two function families show one session clone and no per-case clone.

**Verification.** One family at a time, for example `uv run ci test --
python/corpus-structure/tests/semantic/test_private_records.py`.

## TS-11 — Commit-class consumers on recipe seeds

**Required input.** TS-07 and TS-08.

**Implementation vision.** Committing consumers need fresh state, not a fresh build (F03). Each
recipe below is built once per worker and cloned per consumer; the consumer then takes its own
claims.

| Builder | Seed boundary | Recipes | Consumers |
|---|---|---|---|
| `build_record_source` behind `private_source` (`native_record_fixtures.py:292–646`) | The pre-claim stage, after the record task is created (`:615`) and before the second claim (`:616`) | One per distinct recipe value. Input compositions in use: default; characterization (three modules); reference (the local-admission module and `reference_scenarios.py`, re-exported to six more); source-reading; interpretations; policy-authority; characterization over reference. Further fields: `additional_methods`, `include_blank_cell`, `record_configuration_hash` | 116 test functions by a contributor's count. The fixture clones the seed and runs only the claimed stage |
| `build_domain_case` (`domain_scenarios.py:65–651`) | Whole case (it ends lease-free), or the release-and-views prefix (`:96–267`), decided by the profile below | 15 distinct release prefixes over 36 sites; the default prefix alone serves 11 sites | `test_domain_operations.py`, `test_audit_closure_native.py`, `test_evaluation_boundaries.py`, `test_source_routing.py` and others |
| `build_resubmission_case` (`agent_scenarios.py:36–174`) | Whole case; the agent task is queued and unleased until `queue_next` | Composed (14 of 24 sites), default (7), three others | `test_runtime_entrypoints.py`, `test_reference_evaluation.py`, the exclusion and serving builders |
| `exclusion_result` (`test_identity_exclusions.py:16–121`, moved to support by TS-06) | After `seal_cut` (`:107–112`) for `finalize=False`; after `finalize_bound_run` (`:113`) otherwise | By its keyword set | Seven sites; the tampering family's two recipes are shared with TS-10 |

**Recipes in scope.** The package closes on these, so it cannot close empty:

- the default and the reference `private_source` recipes, at the pre-claim stage;
- the default and the `formulas` release prefixes of `build_domain_case`, at the boundary the
  profile below chooses;
- the default and the composed `build_resubmission_case` recipes;
- `exclusion_result` before finalize (`finalize=False`).

Any other recipe in the table may be adopted the same way and is not a closure obligation.

Variants that are not seeded stay on a per-test build and say why at the call site: the
structural-replay recipes (each case's text differs) and the opt-in parser samples.
`sibling_originals` is outside this package for good. It installs an implementation override
over `contracts.analysis_implementation_inputs` (`native_record_fixtures.py:387`), and an
override is never a recipe field and never seedable: that path stays on a per-test commit-class
build, with [TS-03](implementation-snapshot-and-timing.md) holding the override for the
fixture's lifetime.

**What gains little.** `pdf13_db` (`tests/semantic/pdf_integration_support.py:326`) claims at
`:379` and stores its original under that live lease at `:380`, so a seed would stop before most
of its work. It stays as it is. Builders that are the subject of their test keep building.

**Selected domain boundaries (operator-approved execution approach, 2026-11-13).**
Seed the exact default whole case for the eleven identical complete consumers. Seed the
release-and-views prefix for formulas variants, whose expressions, conditions and mathematical
configuration differ later. Preparation consumes only formula capability; its key does not
contain expression text. This removes repeated complete setup where identical and shares the
stable prefix where later behavior varies. The coordinator's qualitative execution-fit rule
supersedes the earlier mandatory timing profile; no measured speedup is claimed.

**Consumers migrated.** `private_source` keeps its name and return shape; its body becomes
"clone the recipe's seed, run the claimed stage". Sites that call the builders in the body move
the request into a fixture that takes the recipe and calls
`scenario_seeds.commit_clone(recipe)`; the body reads the descriptor and never requests the
seed itself.

**Acceptance and closure.** The builder of each recipe in scope runs once per worker and its
consumers obtain clones, shown by `scenario_seed` in their receipts (F03).

**Verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_record_publication_native.py`
for the record source; `…/test_domain_operations.py` and `…/test_runtime_entrypoints.py` for the
other two builders.

**Open premises.** Whether `invocation_key` exists before a claim is unsettled, so the claimed
stage reads `task_row` after its claim, as `:617–628` does today. Whether any `private_source`
consumer asserts a time relation to seeded stamps is settled by reading consumers as each recipe
is adopted; one that does stays on a per-test build.

## Outside this companion

- Names, leases, the sweep and the keyed head: the
  [lifecycle companion](native-lifecycle-and-deployment.md) (TS-01, TS-02).
- Recipe values, staged builders and support placement:
  [scenario and support ownership](scenario-and-support-ownership.md) (TS-06, TS-07).
- The refusal contract and its site list: [evidence contracts](evidence-contracts.md) (TS-09).
- Family and preparation groups: [run shape and scheduling](run-shape-and-scheduling.md) (TS-12).
- DDO kernel seeds and the classes of DDO native tests:
  [data-operations test alignment](data-operations-test-alignment.md) (TS-17, TS-18).
- Seeds shared across a run's workers, and reopening a seed's persisted release through the
  archive reader, are candidates recorded in the coordinator with their triggers.
