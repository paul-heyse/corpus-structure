# Native lifecycle and deployment

**Status:** Proposed plan; nothing implemented. **Created:** 2026-11-13.

This companion owns the design of packages TS-00, TS-01 and TS-02: the two superseding decision
records, one naming, lease and sweep authority for every database the tests create, and the
keyed, verified head deployment. The
[coordinator](../test-system-target-design_2026-11-13.md) owns package state, finding disposition
and the rule decisions RC01–RC04; nothing here restates them.

**Baseline and evidence.** Source was read at `main` `683e9a955` on 2026-11-13; another session
was committing during authoring, so line citations are as read. Design statements are
**Proposed**. Source facts are **Interface-checked by source inspection, 2026-11-13**. Durations
quoted from the audit are **Measured** from stored results on a shared workstation and are
orders of magnitude. Paths `tests/…` and `src/…` are relative to `python/corpus-structure/`;
root paths are written as root `tests/…`, `scripts/…`, `docs/…`. Section references (§4.1 and so
on) are to the
[design review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md).

## Current baseline and what is reused

`PgAdmin` in `scripts/native_test_support.py` is the lifecycle owner and stays the only one.
The series reuses, unchanged in meaning:

- acknowledged creation and the OID-bound ownership stamp (`PgAdmin.create` `:192–203`;
  `src/corpus_structure/core/db/ownership.py:38–40,87–89`);
- authenticated, unforced drops with a bounded wait for backends to exit (`_drop`, `:213–242`);
- policy capture, replay and comparison (`policy` `:264–304`, `replay_policy` `:306–371`),
  including refusal when replay authority is missing (`:312–313`, `:392–397`);
- session advisory leases taken on `postgres` (`lease` `:538–545`, `lock_sql` `:86–88`);
- `database(name, source, policy=…)` (`:443–493`) as the route for every clone.

What the baseline does that the target replaces:

| Fact at the baseline | Where |
|---|---|
| Each pytest process builds its own head, `cs_sem_head_<pid>_<hex12>`, by running the whole chain | `tests/conftest.py:255–260`; `semantic_template`, `scripts/native_test_support.py:612–630` |
| Names are composed at fourteen call sites in four shapes | `tests/conftest.py:258,265,283,299`; `tests/semantic/conftest.py:23–24`; `tests/semantic/serving_scenarios.py:251,308`; `tests/db/test_cli_db.py:89,132,133`; `tests/test_db_fixtures.py:183–184`; root `tests/scripts/test_parallel_harness.py:65,79` |
| Three created names match no sweep rule | `cs_sem_m1_attributed_<hex12>` (`tests/semantic/test_native_attributed_evidence.py:53`); `cs_sem_test_<hex20>` with no process id (`tests/semantic/test_serving_scenario_lifecycle.py:39`); `cs_ddo_case_<hex12>` (`tests/semantic/test_data_operation_storage.py:165`) |
| The sweep reduces `ci_test_<pid>_<n>` to `ci_test_<pid>` before locking, while `database()` leases the full name (F01) | `TEST_DB` `:45`, sweep `:592–596`, lease `:452` |
| The sweep raises when a candidate is still connected (F04) | `_drop` raises SQLSTATE `55006` after two seconds; the sweep collects it and raises a group, `:596–609`; `native_server` sweeps at session setup, `tests/conftest.py:250` |
| A retired template scheme is still carried (DTA-030) | `TEMPLATE_PREFIX`, `TEMPLATE_RETENTION`, `STAMP` `:46–49`; `stamp()` `:547–552`; the `STAMP` branch of `owned_comment` `:248`; the `cs_tpl_` sweep branch `:580–586` |

The measured build is 37–55 s on one or two workers and 87–92 s each when sixteen build at once
(§4.1, §6.1). The chain directory `python/corpus-structure/semantic_alembic/` holds 876 files in
`versions/` and about 1.3 GB, and grows with every native candidate.

## Target design and contracts

```
cs_template (provisioned)
  │  build as cs_sem_build_<pid>_<hex12>, seal, publish by rename
  ▼
cs_sem_head_<key16>           reused by narrowed runs with the same key; verified once per process that did not build it
cs_sem_head_<key16>_<run8>    run-private: qualification runs, and the replacement for a stale head
  │
  └─► clones through PgAdmin.database, with policy replay, as today
```

| Operation | Consumes | Decides | Produces |
|---|---|---|---|
| Naming function (TS-01) | A kind and its parameters (process id, key, run identity) | Nothing at run time: the table of kinds is the decision | The name, its lease key and its sweep rule |
| Sweep (TS-01) | The cluster's database list and the naming table | Per owned candidate: drop, skip as leased, skip as still connected | A result naming what was dropped and what was skipped |
| Deployment (TS-02) | The deployment key, the run scope, the run identity, `cs_template` | Reuse or build, under the build lock | A sealed head under a stable name, a usage lease held for the session, the head's policy |
| Verification (TS-02) | The per-worker session clone of a head this process did not build | Whether the deployed catalog matches the frozen expectations of the head revision | Pass, or a replacement run-private head, a report of the stale one, and a deployment-key gap recorded in the receipt and the output |

**What consumers stop doing.** Composing database names; leasing or sweeping by a second
derivation; building a head per process; treating a leftover database as a setup failure.

**Preserved guarantees.** Every clone still gets policy capture, replay and comparison, and
setup is still refused when replay authority is missing. Drops stay authenticated and unforced;
no termination right is added. A head is sealed and client-free before anything clones it. The
cold deployment controls keep executing the real chain in every run: `test_migration_chain.py`,
`test_model_deployment.py`, `semantic_bare_engine` and `semantic_database_at`
(`tests/semantic/conftest.py:37–57`), and CLI initialization (`tests/db/test_cli_db.py`). Fresh
committed clones with real logins are untouched.

**Intentional behavior changes.** A head outlives the session that built it. A worker never
drops a head. A narrowed run may execute against a head built by an earlier run, after
verifying it. The sweep reports connected residue instead of failing setup.

## Pivotal library mechanisms

The review's §7 table is the reference; these rows carry the design.

| Mechanism | Condition the design relies on | Reference |
|---|---|---|
| `CREATE DATABASE … TEMPLATE` | The source must have no connected session; concurrent clones of one source proceed; the database comment, `datacl` and settings are not copied, so the stamp is written per clone and policy is replayed | §7 rows 1 and 4; PostgreSQL 18 `sql-createdatabase` |
| `ALTER DATABASE … RENAME TO` | Refused while a session is connected to the database; keeps the OID, and `pg_shdescription` is keyed by OID, so the ownership stamp survives | §7 row 2; documented, not yet exercised here (open premise) |
| Session advisory locks | Lock tags include the current database OID, so every lease is taken on `postgres`, as `PgAdmin.connect()` already defaults; a session lock ends with its session, including a dead client's | §7 row 5 |
| `DROP DATABASE` | Each drop requests an immediate, forced, waited checkpoint for the whole cluster; fewer head drops is the safe lever | §7 row 3 |
| xdist run identity | The `testrun_uid` session fixture is shared by a run's workers and generated locally without workers (`.venv/…/xdist/plugin.py:400–407`) | §7 row 6 |
| `ast`, `importlib.util.find_spec`, `hashlib` | A static walk sees import statements only; a dynamic import by string would escape it | §7 row 13 |

## TS-00 — Baseline reconciliation and the two superseding decisions

**Required input.** The operator decisions recorded in the coordinator.

**Baseline reconciliation.** Before any edit, re-read every `path:line` in this companion that
the first packages touch, since the tree moved during authoring. Run the existing sweep once on
the cluster so per-process heads from earlier runs are gone before TS-01 and TS-02 change the
naming.

**Successor to [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) (RC01).** Create
it with `just adr supersede ADR-0032 <slug>`; the next free number at the baseline was 0101 and
a concurrent session may take it. It must decide:

1. The head is built once per deployment key and reused across sessions by narrowed runs. This
   replaces "builds the frozen semantic head once per session" and "Session templates have no
   persistent reuse/invalidation key", and re-decides Option 4, which ADR-0032 rejected as
   unnecessary for a session-local contract. The record should state that ADR-0032's own
   revisit trigger, session preparation ceasing to fit the supported workload, is met.
2. The key is narrow, and a reused head is verified with production's deployment check once
   per pytest process that did not build it ([the key](#deployment-key)); the options table
   below is the alternatives section. The record states the strength of that check honestly:
   it compares the deployed catalog with the frozen expectations of the head revision, and it
   is not equality with a fresh build. A failed verification is recorded in the receipt and
   the output as a deployment-key gap, so the key is corrected instead of the head being
   silently replaced. The record also notes that file modification times in the key give a
   fresh checkout or worktree a new key for the same content, which costs a rebuild and is not
   a correctness issue.
3. Unnarrowed (qualification) runs build a run-private head, so evidence of record never rests
   on reuse across runs.
4. Publication is by rename; retention is by count; the one lifecycle owner sweeps.
5. Option 3 narrows: a read-only or rolled-back transaction on a shared clone is allowed for a
   claim that involves no separate-login commit, race, cancellation or notification. The
   record names the two engines the operator allowed on a shared clone (2026-11-13): the
   rollback class's reader engine, whose sessions are forced read-only
   (`default_transaction_read_only=on`), and `shared_clone_engine`, kept for the three
   `tests/db` connection-lifecycle modules with a check after each test that nothing durable
   changed on the shared clone. No other writable engine exists on a shared clone. The
   isolation classes themselves are designed in the
   [isolation companion](isolation-and-seeds.md).
6. Unchanged, restated: policy capture, replay and comparison per clone; authenticated,
   unforced drops; real-chain cold deployment controls; refusal on unavailable replay authority.

Design text to amend in the same change:

| Location | Present text | Change |
|---|---|---|
| root `docs/design/D3-database.md:691` | "Semantic templates expire with the session; the legacy cache keeps its existing lifetime." | The head is keyed, reused by narrowed runs, verified once per process that did not build it, run-private for qualification, retained by count |
| root `docs/design/D3-database.md:714` | `> Decision: ADR-0032` | The successor's number |
| root `docs/design/DESIGN.md:630–636` | "clone a session-built frozen semantic deployment" | A keyed, verified deployment; the `> Decision:` line names the successor |
| root `docs/design/D9-repository-and-phase0.md:198` | §4 Tests, Database row: "clone one package-wide migrated session template … ADR-0032 own the contract" | The keyed head and the successor |

**Successor to [ADR-0048](../../adr/0048-populated-native-scenarios.md) (RC04).** It must decide
that seeds are the general mechanism for any recipe that meets the seed premises, per worker;
that "Only the repeated default completed serving scenario uses a named immutable session seed"
is replaced; that "deployment/publication/write-lifecycle tests remain independently prepared"
narrows to tests whose claim includes the seeded stages; and that Option 2's rejection of a
rollback-only transaction narrows to claims that need committed cross-session isolation.
It states the seed rule the operator decided on 2026-11-13: a seed may hold completed attempts
but no unfinished task, meaning no task in a claimed or running state, whether or not its lease
has expired; the seed build checks task status, not only `lease_until`. It also states that
seeds are requested only through fixtures, never from a test body.
Unchanged: no persistent scenario cache, nothing commits to a shared clone, every committing
reader gets a fresh clone with replay, seed origin and clone context stay distinct in receipts,
expected results are authored at each test. It cites the ADR-0032 successor where ADR-0048 cites
ADR-0032 (its Context at `:16` and the last paragraph of its Decision). Amend root `docs/design/D3-database.md` ("Accepted target" paragraph,
about `:706–712`) and root `docs/design/DESIGN.md:638–644`. The seed premises are owned by the
[isolation companion](isolation-and-seeds.md); the record links them.

**Acceptance.** `uv run ci adr lint` passes; both old records carry `status: superseded` and
`superseded-by`; the four design locations name the successors. The root's `just turn-end`
regenerates the index.

## TS-01 — One naming, lease and sweep authority

**Required input.** None. It precedes TS-02 and the seed operation (TS-08), which add kinds.

**Implementation vision.** `scripts/native_test_support.py` gains one function that returns, for
a kind, a small frozen value holding the name, the lease key and the sweep rule. The sweep
recognizes names through the same table, so a name that the function can produce is by
construction a name the sweep understands, and a kind cannot be added without stating how it is
retired.

| Kind | Name | Lease key | Sweep rule |
|---|---|---|---|
| Session clone | `ci_test_<pid>` | the name | Drop when unleased |
| Test, bare, revision, init clones | `cs_sem_<kind>_<pid>_<hex12>` | the name | Drop when unleased |
| Per-process head (interim; TS-02 removes the kind) | `cs_sem_head_<pid>_<hex12>` | the name | Drop when unleased, as today |
| Head build (TS-02) | `cs_sem_build_<pid>_<hex12>` | the name | Drop when unleased |
| Reusable head (TS-02) | `cs_sem_head_<key16>` | the name; a second key derived from it is the build lock | Retained by count inside the deployment operation; never by the general sweep |
| Run-private head (TS-02) | `cs_sem_head_<key16>_<run8>` | as the reusable head | Drop when unleased |
| Retired head (TS-02) | `cs_sem_stale_<pid>_<hex12>` | the name | Drop when unleased |
| Seed (TS-08) | `cs_sem_seed_<pid>_<hex12>` | the name | Drop when unleased |

The interim kind exists because the session head fixture keeps creating today's per-process
head until TS-02 lands; with it, every name the tests create comes from the function from TS-01
onward.

Callers pass a kind; the fourteen composition sites listed in the baseline call the function, and
`database_name` in `tests/semantic/conftest.py:23–24` becomes a thin call to it or goes. The
controls that fabricate a foreign process id (`tests/semantic/test_native_fixtures.py:19–20`)
pass that id explicitly.

**F01.** The lease and the sweep read the key from the same value. With `committing_db` gone the
`_<n>` suffix has no producer, so `TEST_DB` (`:45`) loses its optional group and the reduction
at `:592–595` goes.

**F04.** The sweep keeps trying each unleased owned candidate. A drop that ends with SQLSTATE
`55006` after `_drop`'s bounded wait is recorded as skipped and left for a later sweep; any
other failure, and any authentication or ownership defect, still raises. `sweep()` returns a
result naming dropped and skipped databases instead of a bare list; its five callers
(`tests/conftest.py:250`, `tests/test_db_fixtures.py:142,149`,
`tests/semantic/test_native_fixtures.py:206,211`) read `.dropped`. `native_server` records the
skipped names in the session's receipt context and prints one diagnostic line, so the residue
stays visible until it is removed.

**Superseded machinery removed.**

- `TEMPLATE_PREFIX`, `TEMPLATE_RETENTION`, `STAMP`, `stamp()`, the `STAMP` branch of
  `owned_comment`, the `cs_tpl_` sweep branch, and the now unused `datetime` imports
  (`scripts/native_test_support.py:14,46–49,248,547–552,563,580–586`).
- The `TEMPLATE_RETENTION` import and re-export in `tests/conftest.py:43,170`.
- `committing_db` (`tests/conftest.py:295–303`), `_clones` (`:276`), its entry in `DB_FIXTURES`
  (`:74`), the docstring line (`:13`), and its self-test
  `test_committing_db_commits_on_its_own_clone` (`tests/test_db_fixtures.py:57–66`). No other
  consumer exists by a search of both test trees.
- The shadowing `semantic_db_engine` fixture in
  `tests/semantic/test_native_attributed_evidence.py:50–69`, with `CANDIDATE` (`:42–47`) and
  the imports only it uses. Its candidate branch compares the head revision with
  `semantic_m1_private_20261103` and cannot run. The module then receives the package fixture.
  The evidence folder it pointed at stays; evidence is never deleted.
- `tests/semantic/snapshot_restore.py`, which nothing imports.
- The other two escaping names: `tests/semantic/test_serving_scenario_lifecycle.py:39` takes a
  test-clone name from the function; `ddo_kernel_engine`
  (`tests/semantic/test_data_operation_storage.py:163–169`) does the same. That file is under
  active edit by the declared-data-operations (DDO) session, so the one-line change is
  coordinated with it; TS-17 and TS-18 later replace the fixture.

`owned_comment` also accepts the fixed comment `corpus-structure owned test database` (`:247`).
Nothing in the repository writes it (searched `scripts/`, both test trees and `src/`), and
unlike the OID-bound stamp it would authenticate any database carrying that text. It is removed
with `STAMP`, after the same cluster check.

**One-time cluster check.** Before the `cs_tpl_` branch and the two legacy comment forms are
removed, and while the baseline code can still authenticate them, list databases whose name
starts with `cs_tpl_` or whose comment is either legacy form, and drop each owned, unleased one
through `PgAdmin.drop`. The implementer records the names found, or that none were, in the
commit message. This is a cluster operation during execution, not a probe.

**Controls.** `test_sweep_honours_leases_and_template_age` (`tests/test_db_fixtures.py:124–152`)
is rewritten without stamps or ages: an unleased owned name of each swept kind is dropped; a
leased name survives through that name's own lease (F01); another project's database and
untagged residue survive; a name of the reusable-head kind is not touched by the general sweep.
A new control holds a connection to an owned, unleased residue database and asserts that the
sweep completes, reports the skip, and drops the database on a later sweep once the connection
closes (F04). A small table-driven control asserts that every kind's produced name is
recognized with the same lease key.

**Acceptance and closure.** No source names `cs_tpl_`, `STAMP`, `TEMPLATE_RETENTION` or
`committing_db`; every name the tests create comes from the naming function; one derivation
serves lease and sweep; a sweep that meets connected residue completes and reports it.

**Targeted verification.** `uv run ci test -- python/corpus-structure/tests/test_db_fixtures.py
python/corpus-structure/tests/semantic/test_native_fixtures.py
python/corpus-structure/tests/semantic/test_serving_scenario_lifecycle.py
python/corpus-structure/tests/semantic/test_native_attributed_evidence.py`, and root
`tests/scripts/test_parallel_harness.py`.

## TS-02 — The keyed, verified head

**Required input.** TS-00 (the ADR-0032 successor) and TS-01 (the naming table).

### Options

| Option | What a run pays | Why it is or is not selected |
|---|---|---|
| Run-scoped head: one per run, shared by the run's workers, dropped at run end | A full build in every run, about 40 s even for one test | Removes duplicate builds inside a run only. Needs a run-end owner; a killed controller leaves residue. Rejected: the focused-run floor stays |
| Full-closure key: chain plus every module the chain can reach, following imports inside functions | A build whenever any reached module changes | The closure is 531 of the package's 566 modules, because `semantic/contracts.py` is in it. Over 793 commits since 2026-11-06, 457 touched package source, so the key would change on most product commits. Rejected: complete, and nearly useless in the edit–test loop |
| **Narrow key plus verification**: chain, the 28 modules the chain imports at module level, `uv.lock`, the build procedure, the server; each process that did not build a reused head verifies it once | A build when the chain or its module-level machinery changes: 97 of the 793 commits; 9 touched `uv.lock` | **Selected.** The key is cheap and stable, and it does not have to be provably complete, because production's own deployment check catches a head whose deployed catalog differs from the head revision's frozen expectations |
| Chain-only key | A build when the chain changes: 66 of 793 commits | Rejected: revisions execute product modules at import, and a changed helper such as `alembic_native` would not change the key. It saves 31 builds in 793 commits over the selected key and leans on verification for an expected case rather than a residual one |

The figures are the author's read-only AST walk at `f03170a89` and are **Measured** for that
baseline only.

<a id="deployment-key"></a>

### The deployment key

The key is the SHA-256 of a canonical JSON document with these components. It is computed once
per pytest process by one function in `scripts/native_test_support.py` that takes its roots as
arguments, so a control can run it over a temporary tree without a database.

| Component | How it is computed | Why |
|---|---|---|
| Chain revisions and environment | Content digest of every `.py` and `.mako` file under `python/corpus-structure/semantic_alembic/`, with relative paths | The revisions are the deployment; 186 of them pin the SHA-256 of their frozen artifacts in source |
| Frozen artifacts | Relative path, size and modification time of every other file under the chain | The directory is about 1.3 GB; hashing it in sixteen workers is avoidable because the pins live in the revision files and a fresh build verifies them. Modification times give a fresh checkout or worktree a new key for the same content; that costs a rebuild and is not a correctness issue |
| Module-level import closure | An `ast` walk from every chain `.py` file over import statements that are not inside a function body, resolved with `importlib.util.find_spec`, kept where the module is inside `corpus_structure`, repeated to a fixed point; content digest of each file reached, including package `__init__` files | These modules run when a revision is imported. The set is computed, never listed, so a revision that starts importing another module enters the key by itself. It was 28 modules at the baseline |
| Build procedure | Content digest of `scripts/native_test_support.py` | It holds the build steps |
| Libraries and interpreter | Content digest of root `uv.lock`; `sys.version` | Alembic, SQLAlchemy, psycopg and pglast execute the chain |
| Server and cluster | `server_version_num`; `pg_control_system().system_identifier`; the OID of `cs_template` and its extension versions (`PgAdmin.installed()`, `:495–499`); the OIDs of the semantic principals | A re-provisioned template or recreated role changes what a build produces |

What the key leaves out on purpose is every module the chain reaches only through an import
inside a function. Verification narrows that gap and does not close it: it compares the
deployed catalog with the frozen expectations of the head revision, so it catches a head whose
function bodies, owners, privileges or constraints differ from them. It is not equality with a
fresh build.

### The deployment operation

`PgAdmin` gains one operation that the session head fixture calls in place of
`semantic_template(name)`. It consumes the key, whether the head must be run-private, and the
run identity.

1. Take the name from the naming function: `cs_sem_head_<key[:16]>`, or with `_<run[:8]>`
   appended when run-private.
2. Take the shared usage lease on the name and hold it for the session. Then take the exclusive
   build lock, a second advisory key derived from the name. Two keys are needed: a builder must
   not wait for other runs' usage leases to end, and the sweep must not drop a head that a
   process uses or is about to use.
3. If an owned, sealed database with that name exists, release the build lock, read its policy
   from the catalog and return it as reused.
4. Otherwise build: create `cs_sem_build_<pid>_<hex12>` from `cs_template` through acknowledged
   creation; run the extension and namespace checks and `upgrade(conn)` exactly as
   `semantic_template` does today (`:617–624`); dispose the engine; capture the policy; seal
   with `ALLOW_CONNECTIONS false`; rename to the final name; release the build lock. A failure
   before the rename drops the build database through the authenticated drop.
5. After the usage lease is held, apply retention to reusable heads: keep the newest three by
   database OID and drop older ones whose usage lease can be taken exclusively. Three covers
   the current key, a sibling worktree's key and one predecessor. Retention is by count because
   the ownership stamp is the only comment; there is no last-used stamp to keep.
6. Never drop a head from a worker. Run-private heads are dropped by the next sweep once
   unleased.

`SemanticTemplate` (`:114–117`) stays the handle: name and policy. `semantic_template`, the
per-process name at `tests/conftest.py:258` and the interim per-process head kind in the naming
table are removed.

### Run scope

The managed route sets one new environment value, `CORPUS_CI_RUN_SCOPE`, where `_lane` builds
the child environment (`src/corpus_structure/cli/testing.py:481–498`). It is `qualification`
when the campaign is unnarrowed (`narrowed` is false at `:586` and no retry selection is
given), for both the ordinary and the fault lane, and `narrowed` otherwise. The name joins the
scrubbed set at `:485–490` so an outer value never leaks in. The value reaches pytest by
inheritance: the `test-all` recipe (root `justfile:19–33`) and `run_python`
(`scripts/test_receipts.py:320–337`) pass the environment through. The head fixture reads it;
an absent value means narrowed, so plain `pytest` reuses. Today only `CORPUS_CI_PYTHON_ONLY`
distinguishes a narrowed ordinary lane, and it means something else.

### Verification

The process that built a head does not verify it. Every other pytest process verifies once, at
head acquisition, on its per-worker session clone. That is about once per worker in a full
narrowed run. An unnarrowed run builds its own run-private head from the source it tests and
does not verify it.

*Who owns the session clone.* TS-05 owns the per-worker session clone `ci_test_<pid>`, created
lazily on first use by a read, rollback or `shared_clone_engine` consumer, or by verification.
Once TS-05 exists, verification asks TS-05's fixture for the clone. Before that, the head
fixture creates the clone itself at this point when the head was not built here and lends the
same clone to `db_engine` (`tests/conftest.py:279–285`) afterwards. In both orders verification
adds no clone that the session would not otherwise be able to use.

*Strength.* The check establishes that the deployed catalog matches the frozen expectations of
the head revision. It does not establish that the head equals what a fresh build from this
source would produce. On a maintenance transaction on the session clone it checks that `current_revision` equals `head_revision()` and calls production's
`verify_deployment_catalog(connection, revision=head_revision())`
(`src/corpus_structure/semantic/execution_admission.py:149–187`), which compares the deployed
function bodies and runs the frozen catalog checks for owner, privileges and constraints inside
a savepoint that is rolled back.

On failure the worker drops only its own session clone, releases its usage lease on the stale
name, obtains a run-private head through the same operation (one build per run, behind the
build lock), and reports the stale head's name in its receipt. The failure is also recorded,
in the receipt and in one line of output, as a deployment-key gap: a head that fails
verification under an unchanged key means the key missed an input, and the record is what gets
the key corrected instead of the head being silently healed. So that later runs with the same
key do not each pay a build, the worker then tries to take the stale head's usage lease
exclusively; if it succeeds it renames the head to the retired kind, which the next sweep drops,
and if another process still uses it the head is left and reported. Nothing is dropped in
place. The replacement run-private head was built in this run and, like a qualification run's
head, is not verified again by the workers that join it.

### Receipts

The head fixture emits one session-scope native context per process through
`record_native_context(…, scope="session")` (the route `record_server_context` uses, `:758–782`)
carrying the head name, the key, the run scope, whether this process built or reused the head,
the verification outcome, and, when one was replaced, the stale head's name with the
deployment-key gap.
`scripts/test_receipts.py` already retains native context events per receipt (`:686,782`); the
classification adds a small per-receipt projection of these head records so that reuse can be
read without opening event files. Reuse recorded this way is functional evidence, not a speed
claim.

### Failure cases

| Case | What happens |
|---|---|
| Crash in the middle of a build | The build lock and the build database's lease end with the session. Only `cs_sem_build_*` exists; the head name never did. The next process builds; the sweep drops the residue, or skips and reports it while a dead client's backend is still running the migration (F04) |
| Two runs with one key | The second waits on the build lock, finds the published head, and reuses it after verifying. Neither waits for the other's usage lease |
| A migration edited during a run | Workers that start after the edit compute another key and build or reuse another head, so one run can use two heads, as two workers can deploy two chains today. Each receipt names its head. Frozen source at qualification excludes the case |
| A stale head | Verification fails; the worker continues on a run-private head, records the deployment-key gap, and reports and retires the stale one, as above. Cold deployment controls ran the real chain in the same run regardless |
| A sweep while a builder waits | The waiter already holds the shared usage lease on the head name, so the sweep's exclusive try fails and it skips. Retention runs only after the retaining process holds its own lease, so it cannot evict the head it is about to use |
| A head renamed or dropped between the existence check and the first clone | Cannot happen while the usage lease is held: both retirement and retention need that lease exclusively |

### Controls to add or change

- `test_session_database_is_cloned_from_the_migrated_template` (`tests/test_db_fixtures.py:20–32`)
  keeps its assertions; the head name now follows the keyed pattern.
- `test_current_template_cold_build_is_sealed_and_disposed` (`tests/test_db_fixtures.py:178–208`)
  becomes the control of build and publication under a test-private key: the published head is
  sealed and has no backend, no build database of this process remains, a clone is at the head
  revision, and after the lease is released the sweep drops the run-private head.
- `test_head_is_sealed_and_has_no_migration_backend` and
  `test_fresh_committed_clones_are_isolated` (`tests/semantic/test_native_fixtures.py:23–71`)
  stay as they are.
- New, in `tests/semantic/test_native_fixtures.py`, each under a test-private key so the
  session's real head is never involved: a second acquisition with the same key reuses without
  calling `upgrade`; a build whose `upgrade` raises leaves no database under the head name and
  no build residue; two concurrent acquisitions of one absent key run `upgrade` once; a head
  whose deployed function body was altered before sealing fails verification, is replaced by a
  run-private head, is retired, and leaves a deployment-key gap in the session's native context; a sweep during a held usage lease skips the head; retention
  keeps three and drops the fourth only when unleased.
- New, without a database: the key changes when a chain file, a closure module or `uv.lock`
  changes and not when an unrelated package module changes; the computed closure contains the
  modules the revisions import directly (`native_objects`, `alembic_native`, `alembic_defaults`,
  `alembic_indexes`, `metadata`, `migrations`, `schema.relational`), so a broken walk fails
  loudly. The control does not pin the set of 28.
- Root `tests/scripts/test_test_receipts.py`: the head projection over canned events.
- `src/corpus_structure/cli/testing.py`: a control that an unnarrowed campaign passes
  `qualification` and a narrowed or retry lane passes `narrowed`.

**Successful example.** `uv run ci test -- python/corpus-structure/tests/semantic/test_native_fixtures.py`
run twice with no source change: both receipts name the same `cs_sem_head_<key16>`; the first
records it built (or reused, if an earlier run left it), the second records it reused and
verified. `uv run ci test` then names a `cs_sem_head_<key16>_<run8>` in every worker's record.

**Acceptance and closure.** Receipts of two consecutive narrowed runs name one head and the
second records reuse and verification; an unnarrowed run names a run-private head; a failed
verification is recorded as a deployment-key gap; no per-process head creation remains; policy replay, authenticated drops and the cold deployment
controls are unchanged.

**Targeted verification.** `uv run ci test -- python/corpus-structure/tests/test_db_fixtures.py
python/corpus-structure/tests/semantic/test_native_fixtures.py`, root
`tests/scripts/test_test_receipts.py`, and the CLI testing controls. Record `uv run ci doctor`
if the run meets an environment-shaped failure.

**Open premises.**

| Premise | What settles it | If it fails |
|---|---|---|
| Rename publishes a build and keeps the OID-keyed stamp | The first build in TS-02 | Build under the final name behind the build lock and seal last; an unsealed database under a head name is then recognizable residue, and step 3 treats it as absent after dropping it |
| The deployment check is cheap enough to run once per process that did not build the head | The first verified runs | Verify once per head per day, or only when a key component changed since the head's build |
| Computing the key per worker is not material | Observed in the first full run | Compute it once in the controller and pass it to workers through `workerinput` |
| Three retained heads fit the disk | The head's on-disk size, observed once | Lower the count |
| One held lease connection per worker is acceptable against `max_connections` | Read `ops/postgresql/corpus.conf` when implementing | Take the usage lease on the connection that already serves the session, if one is introduced |

## Outside this companion

The isolation classes, the session clone and its read and rollback fixtures (TS-05), the seed
operation and its `seed` kind (TS-08), and the families that use them are in the
[isolation companion](isolation-and-seeds.md). Worker sizing, which removes the other half of a
focused run's fixed cost, is in [run shape and scheduling](run-shape-and-scheduling.md). The
candidates not scheduled, including seeds shared across a run's workers, and the rejected
options are in the coordinator's
[candidates section](../test-system-target-design_2026-11-13.md#candidates-rejected-options-and-open-premises).
