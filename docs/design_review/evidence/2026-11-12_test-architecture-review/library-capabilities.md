# Library and system capabilities for cheaper test preparation and scheduling

Evidence map for the test architecture and efficiency design review. Baseline `main` at
`784d86f11`. Researched 2026-11-12. These are capabilities and limits for the reviewer to weigh,
not recommendations.

## Versions examined

| Component | Version | Source |
|---|---|---|
| pytest | 9.1.1 | `pyproject.toml:19`, `uv.lock:4585` |
| pytest-xdist | 3.8.0 (execnet 2.1.2, psutil 7.2.2) | `pyproject.toml:32`, `uv.lock:4622` |
| hypothesis | 6.170.12 | `pyproject.toml:22` |
| SQLAlchemy | 2.1.6 | `python/corpus-structure/pyproject.toml:33` |
| psycopg / psycopg-pool | 3.3.6 / 3.3.3 | `python/corpus-structure/pyproject.toml:21-22` |
| filelock | 4.2.4, **transitive only** (not declared) | `.venv/.../filelock-4.2.4.dist-info`, `uv.lock:219` |
| PostgreSQL server | 18.6 (`/usr/lib/postgresql/18/bin/postgres --version`) | cluster `18/corpus`, data on **ext4** (`findmnt` on `/var/lib/postgresql`) |

The installed `/etc/postgresql/18/corpus/conf.d/corpus.conf` is byte-identical to
`ops/postgresql/corpus.conf` (checked with `diff`). Host: 16 physical / 32 logical CPUs. psutil
reports `cpu_count(logical=False)=16`, so `-n auto` means 16 workers.

**How strong each claim is:** **[doc]** means the documentation for the pinned version states it.
**[src]** means I read it in the installed source; it describes current behaviour, not a promised
contract. **[src-18]** means PostgreSQL `REL_18_STABLE` source fetched from GitHub, which is the
branch head, not the 18.6 tag. **[ext]** means general platform knowledge that I did not check
against a primary source this session. Site-packages paths below are relative to
`.venv/lib/python3.14/site-packages/`.

---

## 1. pytest-xdist: building a session-scoped resource once per run

**Documented pattern [doc]** (xdist 3.8.0 `docs/how-to.rst`, "Making session-scoped fixtures
execute only once"):
- A session fixture takes `tmp_path_factory` and `worker_id`. If `worker_id == "master"` (no
  xdist), it builds directly.
- Otherwise it uses `root = tmp_path_factory.getbasetemp().parent`, the directory shared by all
  workers, and the first worker builds under `FileLock(str(fn) + ".lock")`. Later workers read
  `fn`.
- The documentation says xdist has **no built-in** exactly-once support. It calls this pattern
  "a starting point" and says it is applicable to "initializing a database service and populating
  initial tables".
- A second documented pattern uses `testrun_uid` (an id shared by all workers in one run) with an
  OS semaphore to create one database per run.

Why the shared directory works: the controller passes each worker
`basetemp = <controller basetemp>/<gateway id>` (`xdist/workermanage.py:340-341`), so the parent
directory is common to all workers **[src]**. In this repository, `conftest.py:9-18` moves pytest's
temp root to `build/tmp/pytest` through `PYTEST_DEBUG_TEMPROOT` before xdist allocates scratch. The
parent directory is still shared.

`testrun_uid` is a fresh `uuid4().hex` per controller run unless `--testrunuid` is given
(`workermanage.py:56-58`). Workers receive it through `workerinput["testrunuid"]` and the
environment variable `PYTEST_XDIST_TESTRUNUID` (`remote.py:416`) **[src]**.

**Failure and cleanup semantics. The documentation is silent on all of these; each is an
observation or inference.**
- **Teardown.** The documented pattern has no teardown. No worker knows whether it is the last
  one, so a worker-built shared resource has no natural owner for cleanup. Files under basetemp
  fall to pytest's basetemp retention. Database objects need an explicit owner, which in practice
  is the controller (see the hooks below) or a sweep at the start of the next run keyed by
  `testrun_uid`.
- **Builder crash.** filelock 4.x on Linux uses `fcntl.flock`, which the kernel releases when the
  process dies **[ext]**. The next waiter then gets the lock, sees no artifact, and builds. If the
  builder died after starting to write, `fn.is_file()` is true but the content is partial. A
  sentinel file or atomic rename is needed; the documented example does not show one.
- **`--max-worker-restart=0`** (repo `pyproject.toml` addopts). `DSession.worker_errordown`
  (`xdist/dsession.py:238-266`) reports the crashed item as failed (`handle_crashitem`, `:432-453`),
  increments the failure count, and because `0` is exceeded it calls `triggershutdown()`. Other
  workers get `shutdown` and finish what they already hold. No replacement worker is cloned
  **[src]**.
- **A database-native alternative to filelock.** A session-level `pg_advisory_lock` taken on the
  connection that builds the resource is also released when that backend's session ends, so a
  crash is handled by the server **[doc]** (PostgreSQL 18 §13.3.5). This needs no undeclared
  `filelock` dependency.

**Controller-side hooks [src unless marked]:**
- **`pytest_configure` runs in both processes.** The controller and every worker run it. Workers
  carry `config.workerinput`. The predicates are `xdist.is_xdist_worker(request_or_session)` and
  `xdist.is_xdist_controller(...)` (`xdist/plugin.py:342-366`).
- **`pytest_sessionstart` on the controller.** DSession spawns the workers in its own
  `pytest_sessionstart`, which is marked `trylast=True` (`dsession.py:82-92`). A conftest
  `pytest_sessionstart` without `trylast` therefore runs on the controller before any worker
  exists. That ordering follows from pluggy's documented `trylast` semantics.
  - Limit: the controller **never collects** (`DSession.pytest_collection` returns `True`,
    `dsession.py:102-105`). Work done here cannot see the selection, so it would run for every
    invocation.
- **`pytest_xdist_setupnodes(config, specs)`** **[doc: hookspec]**. Called before any remote node
  is set up (`workermanage.py:95`).
- **`pytest_configure_node(node)`** **[doc: hookspec]** (`newhooks.py:74`). It is called per node
  at `workermanage.py:342`, after `node.workerinput` is built (`:308-311`) and before it is sent
  (`:349`). Keys a conftest adds to `node.workerinput` arrive as `config.workerinput` on the worker
  (`remote.py:424`). This is the supported channel for passing a controller-built identity, such
  as a database name, to workers.
- **`pytest_xdist_node_collection_finished(node, ids)`** **[doc: hookspec]** (`newhooks.py:89`).
  The controller calls it synchronously in `worker_collectionfinish` (`dsession.py:287`) before
  `sched.add_node_collection` and scheduling.
  - It is the earliest controller point that knows the selection.
  - It sees node IDs only, not fixture names. Under `loadgroup` the IDs carry the `@group` suffix.
  - Building a resource here would block scheduling until the build finishes.
- **Controller teardown.** `DSession.pytest_sessionfinish` tears down the nodes
  (`dsession.py:94-100`). By then all workers have finished. A controller-side
  `pytest_sessionfinish(trylast=True)` or `config.add_cleanup` is a single owner for cleanup. A
  hard kill of the controller still leaves orphans.
- **Precedent in the repository.** `scripts/qualification_plugin.py:192` already implements
  `pytest_xdist_setupnodes`, so this plugin already has a controller-side hook.

## 2. pytest-xdist scheduling (3.8.0)

Common to all modes **[doc + src]**:
- The number of workers is fixed in `pytest_cmdline_main` **before collection**
  (`plugin.py:305-325`). `-n auto` calls the first-result hook `pytest_xdist_auto_num_workers`.
  The default implementation (`plugin.py:16-54`) honours `PYTEST_XDIST_AUTO_NUM_WORKERS` and
  otherwise uses `psutil.cpu_count(logical=False)`; `-n logical` uses logical CPUs. `--maxprocesses`
  caps the result.
- **All N workers start and each performs a full collection** **[doc]** ("Each worker is
  responsible for performing a full test collection", `how-it-works.rst`). The controller checks
  that the collections are identical (`loadscope.py:409`, `load.py:309`).
- So **`-n auto` spawns 16 workers, and 16 collections run, even for a 1-test selection**.
  - `loadscope`, `loadfile` and `loadgroup` shut down surplus nodes only after collection
    (`loadscope.py:385-393`).
  - `load` with fewer than `2*nodes` tests sends one test per node round-robin
    (`load.py:274-282`), and nodes that get nothing are shut down.
- **A repository hook could size the pool.** A root `conftest.py` is loaded before
  `pytest_cmdline_main`, so it could implement `pytest_xdist_auto_num_workers(config)`. It would
  see only `config.args` (paths and node IDs), not the collected selection.
- **Managed runs clear the environment override.** `scripts/test_receipts.py:323-330` removes
  `PYTEST_XDIST_AUTO_NUM_WORKERS` from the environment for managed runs.

Mode semantics:
- **`load`** (`scheduler/load.py`).
  - Initial distribution sends **consecutive** chunks of `max(2, min(len//nodes//4, maxschedchunk))`
    tests (`:286-294`).
  - Refills come from the head of the pending list, in collection order (`check_schedule`,
    `:179-207`).
  - The code comment says this is meant to keep pytest's fixture-optimal order per worker.
  - `--maxschedchunk` affects **only** this mode (grep: the option is read only in `load.py`).
- **`loadscope`.** The scope is `nodeid.rsplit("::", 1)[0]` (module, or class). Each scope is one
  work unit sent whole to one worker. The work queue is sorted by unit size, descending, unless
  `--no-loadscope-reorder` is given (`loadscope.py:374-381`).
  - Each node gets one unit, then one more if it has `≤2` pending tests (`_reschedule`,
    `:313-336`).
- **`loadfile`.** The same machinery with scope = file (`loadfile.py`, `nodeid.split("::",1)[0]`).
- **`loadgroup`** (the repository default, `pyproject.toml` addopts) is a subclass of
  `LoadScopeScheduling` (`loadgroup.py`).
  - On the worker, under loadgroup, `pytest_collection_modifyitems` appends
    `@<sorted group names joined by _>` to `item._nodeid` (`remote.py:236-254`).
  - `_split_scope` returns the group name when the `@` comes after the last `]`, and otherwise the
    **full nodeid**.
  - Consequences [src]:
    - **Ungrouped tests: one test per unit.** Each ungrouped test, including each member of a
      parametrized family, is its own one-test work unit. Units are handed out one at a time as a
      worker's pending count drops to `≤2`. The documentation says ungrouped tests are
      "distributed normally as in `--dist=load`" **[doc]**, but the dispatch granularity is the
      loadscope one (single units). It is not load's consecutive chunks.
    - **No locality for module and class fixtures of ungrouped tests.** Consecutive tests of one
      module or one parametrized family can land on different workers. Each receiving worker
      builds that module- or class-scoped fixture.
    - **Repeated setup on one worker.** If a worker receives A1, then B3, then A5, pytest tears
      down module A's fixtures before B3 and rebuilds them for A5 (`SetupState` with `nextitem`).
    - **Whole groups.** A group is one unit and is sent whole to one worker, largest groups first.
    - **Combined groups.** A test carrying two different groups lands in a **new combined group**
      (documented: "joined together into a new group"). It does not share a worker with either
      parent group.
    - **Group marks from fixture parameters** are honoured [doc].
- **`worksteal`** (`scheduler/worksteal.py`). The initial pending list is split into contiguous
  blocks, one per node. Idle nodes (`MIN_PENDING = 2`) steal half of the longest queue
  (`:196-240`). The documentation claims "similar or better reuse of fixtures" than `load`
  **[doc]**. `xdist_group` is ignored: the `@` suffix is added only under loadgroup.
- **Placement of parametrized families.** No mode assigns a family to a worker by parameter. A
  family stays together only if it shares a loadscope or loadfile scope, or an `xdist_group`
  (possibly via `pytest.param(..., marks=pytest.mark.xdist_group(...))`). Under `load` and
  `worksteal` a family stays together only through consecutive chunking.
- **`pytest_xdist_make_scheduler(config, log)`** is a supported first-result hook in 3.8.0
  (`newhooks.py:95-100`). It is called at `dsession.py:130`, with built-ins as the `trylast`
  fallback (`dsession.py:107-126`). The scheduler protocol is `xdist/scheduler/protocol.py`.
  - The documentation names the hook as the way to implement custom distribution
    (`how-it-works.rst` step 6) **[doc]**.
  - The protocol is not documented as a stable API (inference: it is a `Protocol` class with no
    narrative documentation).
- **There is no `--group` option** in xdist 3.8.0 (searched the full option list in
  `plugin.py:64-225`). Group reuse comes only from `xdist_group` marks under loadgroup.

## 3. pytest 9.1.1: fixtures, parametrization, subtests, prerequisites

- **Reordering by parameter [doc]** (`how-to/fixtures.rst`, "Automatic grouping of tests by
  fixture instances").
  - pytest reorders items to minimise active parametrized higher-scope fixture instances. All
    tests using `mod1` run, its finalizer runs, then `mod2` is set up.
  - `@pytest.mark.parametrize(..., scope="module")` gives direct (non-fixture) parameters the same
    grouping and overrides the fixture's scope **[doc]** (`_pytest/python.py:1308-1312`
    docstring).
  - With `indirect=True` (or a list of argument names), the value reaches the fixture as
    `request.param` **[doc]** (`example/parametrize.rst`).
  - **Limit:** this reordering runs in each worker's own collection. Under xdist the dispatch
    granularity in §2 decides whether the reordered neighbours run in the same process.
- **Fixture caching [src]** (`_pytest/fixtures.py:1171-1209`).
  - The cache key is the parameter. When a different parameter is requested, the current instance
    is finalized before the new one is built.
  - **Exceptions are cached.** A higher-scope fixture that raised, including through
    `pytest.skip`, re-raises the cached exception for every later request in that scope without
    re-executing. A session-scoped prerequisite check is therefore evaluated **once per worker**.
- **`skipif` / `skip` marks [src].** They are evaluated in `_pytest/skipping.py:247-251`
  (`pytest_runtest_setup`, `tryfirst=True`). That runs before the runner's `pytest_runtest_setup`
  calls `item.session._setupstate.setup(item)` (`_pytest/runner.py:168-170`), so **a mark-based
  skip prevents all fixture setup for that item**.
  - Correction to the brief's premise: string conditions are evaluated at setup time, not at
    collection. Boolean conditions are evaluated when the decorator expression is evaluated, at
    import.
  - `pytest_collection_modifyitems` can add skip marks, or deselect via `config.hook.pytest_deselected`,
    before any setup. A conftest `pytest_runtest_setup` with `tryfirst` also runs before fixtures.
- **Subtests are built in to pytest 9.1.1** (`_pytest/subtests.py`; the `subtests` fixture is at
  `:135-142`). No `pytest-subtests` plugin is installed.
  - Reporting [doc] (`how-to/subtests.rst`): each `with subtests.test(msg=..., **kw)` block
    reports separately, and failures do not stop the test. Failures show as `SUBFAILED` and the
    parent test is reported last. Progress shows `u`.
  - Subtests are not known at collection time, cannot be selected individually, and "plugins that
    handle test execution cannot target individual subtests" [doc].
  - Serialization [src]: `SubtestReport._to_json` writes `_report_type: "SubTestReport"` and
    `_subtest.context` (`subtests.py:80-108, 345-360`), so they cross xdist.
    `pytest-reportlog` rewrites `_report_type` to `$report_type` (`pytest_reportlog/plugin.py:93`).
  - Consequence for receipts (inference): several `call` reports share the parent node ID. Any
    receipt logic keyed on one report per node ID would need to admit them.

## 4. PostgreSQL 18: database copy and drop

- **`CREATE DATABASE … TEMPLATE t STRATEGY {WAL_LOG|FILE_COPY}`** [doc] (PostgreSQL 18
  `sql-createdatabase.html`).
  - **`WAL_LOG`** is the default. It copies block by block and writes each block to WAL. It is
    "most efficient … where the template database is small".
  - **`FILE_COPY`** writes one WAL record per tablespace but "forces the system to perform a
    checkpoint both before and after the creation".
  - [src-18] Both checkpoints are `CHECKPOINT_IMMEDIATE | CHECKPOINT_FORCE | CHECKPOINT_WAIT`, and
    the first one also has `FLUSH_ALL`. They are cluster-wide.
  - The repository's create sites name no `STRATEGY`, so they use WAL_LOG:
    `cli/db.py:114`, `scripts/native_test_support.py:200`, `tests/semantic/test_native_fixtures.py:209,379,414`,
    `tests/db/test_cli_db.py:98` (grep for `CREATE DATABASE` across `python/corpus-structure/{src,tests}`,
    `scripts`, `tests`).
- **`file_copy_method = copy | clone`** (new in PG 18) [doc] (`runtime-config-resource.html`).
  - It affects only `STRATEGY=FILE_COPY` and `ALTER DATABASE … SET TABLESPACE`.
  - `CLONE` uses `copy_file_range()` on Linux and gives "the kernel the opportunity to share disk
    blocks".
  - **This cluster's data directory is on ext4.** ext4 has no reflink, so `clone` would at most
    copy in the kernel, without sharing blocks [ext]. Block sharing needs XFS with reflink or
    btrfs, which would be a host change.
  - The page does not state the setting's GUC context (whether a session can set it). I did not
    establish this.
- **What a template copy carries.** [doc] Database-level `ALTER DATABASE … SET` settings and
  database `GRANT`s are **not** copied. [src-18]:
  - `datacl` is deliberately set to NULL.
  - `datdba` comes from the `OWNER` option, otherwise from the executing user.
  - `datconnlimit`, `datistemplate` and `datallowconn` come from the command options or defaults,
    not from the template.
  - Shared comments and `pg_db_role_setting` (the store for `ALTER ROLE … IN DATABASE … SET`) are
    not copied by `createdb()`. `dropdb()` deletes them.
  - `dathasloginevt` is copied.
  - Objects inside the database are copied: schema, data, extensions, in-database `GRANT`s and
    `COMMENT`s.
- **No other connections to the template.** [doc] `CREATE DATABASE` "will fail if any other
  connection exists when it starts"; after that, new connections to the template are locked out
  until the copy completes.
  - [src-18] The check uses `CountOtherDBBackends` and fails with "source database … is being
    accessed by other users".
  - The template is taken with `ShareLock`, and "ShareLock allows two CREATE DATABASEs to work
    from the same template", so **parallel workers can clone one template concurrently**.
  - Precedent: `cli/db.py:102-112` disposes its probe engine on the template before cloning.
  - Any pooled idle connection to the template, from any process, breaks cloning.
- **`CREATE DATABASE` and `DROP DATABASE` cannot run inside a transaction block** [doc].
- **`DROP DATABASE … WITH (FORCE)`** [doc] (`sql-dropdatabase.html`).
  - It terminates connections the caller may `pg_terminate_backend`, including background
    workers.
  - It does not proceed if prepared transactions, active logical replication slots or
    subscriptions exist, and it fails if any connections remain.
  - Only the owner may run it, and not while connected to the target.
  - **Cost found in the source** [src-18]: every `dropdb()` calls `DropDatabaseBuffers(db_id)` and
    then `RequestCheckpoint(CHECKPOINT_IMMEDIATE | CHECKPOINT_FORCE | CHECKPOINT_WAIT)`, an
    **immediate cluster-wide checkpoint per database drop**.
    - [ext] `DropDatabaseBuffers` scans every shared buffer header: 8 GB / 8 kB, about 1 M
      headers here.
    - Every dropped test database therefore forces a checkpoint that flushes dirty pages of all
      databases, including `corpus_structure_dev`.
    - `checkpoint_timeout` and `max_wal_size` do not prevent these checkpoints.

## 5. Durability settings for disposable data

[doc] PostgreSQL 18 §14.5 "Non-Durable Settings" lists, for sites that do not need durability:
RAM-disk data directory; `fsync = off`; `synchronous_commit = off` ("risk transaction loss
(though not data corruption) in case of a crash of the database"); `full_page_writes = off`;
larger `max_wal_size` and `checkpoint_timeout`; unlogged tables ("non-crash-safe"). Except where
the page notes otherwise, these keep data safe across a database software crash; "only an abrupt
operating system crash creates a risk of data loss or corruption".

| Setting | `ops/postgresql/corpus.conf` | Scope and constraint |
|---|---|---|
| `synchronous_commit` | `off` (line 30, "data is regenerable (operator, 2026-10-28)") | Already relaxed cluster-wide. Can also be set per database, role or session |
| `max_wal_size` / `checkpoint_timeout` | `8GB` / `15min` (lines 26, 28) | Already raised. Does not affect the forced checkpoints from DROP DATABASE or FILE_COPY (§4) |
| `fsync` | not set (default `on`) | Cluster-wide only (postgresql.conf / sighup). Turning it off risks unrecoverable corruption on an OS crash for **every** database on the cluster, `corpus_structure_dev` included. The operator records the data as regenerable (auto-memory note), but the decision belongs to the operator |
| `full_page_writes` | not set (default `on`) | Cluster-wide. The documentation pairs it with `fsync = off` |
| `wal_level` | not set (default `replica`) | `minimal` would let a transaction that creates or rewrites a table skip WAL for it. It needs a restart and `max_wal_senders = 0`, and removes base backups and replication for the dev database [ext] |
| unlogged tables | n/a | A per-table DDL change. In tests it would make the schema differ from production, which is a fidelity question for the reviewer |

Interpretation, not established: with `synchronous_commit` already off and checkpoint spacing
already wide, the remaining cluster-level write amplification that tests cause is most plausibly
the per-drop forced checkpoints (§4). A `fsync = off` decision would make those checkpoints
cheaper but not remove them. Avoiding the drops altogether (reusing databases, or deferring the
drop to one controller-side sweep) does not depend on any durability trade-off.

## 6. Transaction rollback as test isolation

- **SQLAlchemy 2.1.6 recipe [doc]** (`orm/session_transaction.rst`, "Joining a Session into an
  External Transaction").
  - Open `engine.connect()` and `conn.begin()`, then bind
    `Session(bind=conn, join_transaction_mode="create_savepoint")`. The Session's
    commit and rollback become SAVEPOINT operations. Teardown is `trans.rollback()`.
  - The documentation says it is "part of SQLAlchemy's own CI".
  - **It is an ORM `Session` recipe.** The product uses **Core connections only**: grep found 0
    `Session(` or `sessionmaker` hits in `python/corpus-structure/src`.
- **Core limits [doc + src].**
  - `Connection.commit()` "only acts upon the primary database transaction … does not operate
    upon a SAVEPOINT" (`sqlalchemy/engine/base.py:1009-1016`). Code that commits on a passed-in
    Core connection would commit the outer test transaction. Grep found 6 `.commit()` lines in
    product `src`.
  - Code that opens its own connections (`engine.begin()` / `engine.connect()`; 125 grep hits in
    `src`) or runs subprocesses cannot see the outer transaction's uncommitted data.
- **Isolation level.**
  - `isolation_level` "may only be established before … begin()" (`base.py:345-351`) [doc].
  - Setting it on a connection inside a transaction raises `InvalidRequestError`
    (`engine/default.py:912-925`) [src].
  - PostgreSQL itself allows `SET TRANSACTION ISOLATION LEVEL` only before the first query of the
    top-level transaction [ext]. SERIALIZABLE or REPEATABLE READ code paths (17 grep hits in
    `src`) cannot run nested in an outer READ COMMITTED test transaction.
- **PostgreSQL savepoint semantics.**
  - **Ordinary locks** [doc §13.3.1]: "if a lock is acquired after establishing a savepoint, the
    lock is released immediately if the savepoint is rolled back to".
  - **Session-level advisory locks** [doc §13.3.5]: they "do not honor transaction semantics", so
    a lock taken in a transaction that is later rolled back is still held, and an unlock takes
    effect even if the transaction later fails.
  - **Transaction-level advisory locks** (`pg_advisory_xact_lock`) [doc] "behave more like regular
    lock requests". The documentation does not spell out whether they are released at savepoint
    rollback. Not established.
  - Repository usage (grep in `src` and `semantic_alembic`): mostly `pg_advisory_xact_lock`, plus
    `pg_try_advisory_lock` and `pg_advisory_unlock` (2 each).
  - **Sequences** [doc §9.17]: `nextval` values are "not reclaimed … if the calling transaction
    later aborts", and `setval` changes "are not undone if the calling transaction rolls back".
    Identity values therefore leak across rolled-back tests. Assertions on absolute IDs would
    become order-dependent.
  - **`SET LOCAL ROLE`** (used in `semantic/native_candidate.py:1900-2006`): it lasts until the
    end of the transaction, and rolling back to an earlier savepoint undoes it [ext; §SET page not
    fetched]. Inside a long outer transaction, a missing restore persists for the rest of the test.
  - **Time:** `now()` / `transaction_timestamp()` stay frozen at the start of the outer
    transaction, while `clock_timestamp()` advances; rollback does not rewind either [ext].
    Product code uses `clock_timestamp()` heavily (86 grep lines), so leases computed that way
    keep advancing inside an outer transaction.
  - **`LISTEN` / `NOTIFY`**: notifications are delivered only on commit and `LISTEN` takes effect
    at commit [ext], so neither works inside a never-committed transaction. Grep found 0 uses in
    `src`.
  - **Not allowed in a transaction block:** `CREATE DATABASE`, `DROP DATABASE`,
    `CREATE INDEX CONCURRENTLY` and `VACUUM` [doc / ext].

## 7. Hypothesis 6.170.12

- **Profiles [doc + src]** (`hypothesis/_settings.py`).
  - Built-in `default`: `max_examples=100`, `deadline=200ms`, all phases.
  - Built-in `ci`: `derandomize=True`, `deadline=None`, `database=None`, `print_blob=True`,
    `suppress_health_check=[too_slow]`. It is auto-loaded when a CI environment variable such as
    `CI` is present (`:394-416, :1235-1239`).
  - `register_profile(name, parent=None, **kw)` **overwrites** an existing profile
    (`:1120-1176`). `load_profile` sets the default.
  - Per-test `@settings(...)` takes precedence over the profile [doc].
- **Repository profiles.**
  - `python/corpus-structure/tests/conftest.py:65-69` replaces `ci` with `max_examples=300`,
    `deadline=None`, `derandomize=True`, `database=None`, `print_blob=True`. It does not carry
    forward the built-in `too_slow` suppression.
  - It registers an empty `dev` profile and loads `HYPOTHESIS_PROFILE` (default `dev`).
  - **Managed runs force `HYPOTHESIS_PROFILE=ci`** (`scripts/test_receipts.py:334`), so
    qualification runs use 300 examples per `@given` test without an explicit per-test count,
    where the default is 100.
  - With `derandomize=True` and `database=None`, every qualification run executes the **same**
    example sequence [inference from the documented meaning of derandomize].
- **Repository usage** (grep, both test trees).
  - 27 `@given` lines across 11 files.
  - Explicit per-test overrides: `core/test_shapes.py:193` (`max_examples=40`) and
    `semantic/test_native_closure.py:530-531` (`max_examples=16, deadline=None,
    suppress_health_check=[function_scoped_fixture]`, a database-backed property).
  - `math/test_property.py:125` and `llm/test_cascade.py:160` use
    `suppress_health_check=list(HealthCheck), deadline=None`.
- **Phases [doc]**: `explicit`, `reuse`, `generate`, `target`, `shrink`, `explain`. They can be
  narrowed per test or profile, for example `phases=[Phase.explicit]` to run only `@example`
  cases.
- **I/O-bearing examples [doc]**: `HealthCheck.function_scoped_fixture` is a **correctness** check.
  A function-scoped fixture resets once per test, not once per example, and the documentation
  recommends extra care before suppressing it. `deadline=None` is the documented way to stop
  timing-variance failures; the built-in `ci` profile does this.

## 8. Other mechanisms

- **`--import-mode=importlib` with `pythonpath` [src]** (`_pytest/pathlib.py:548-575, 761-790,
  847-888`).
  - When a test file's directory has no `__init__.py`, pytest names it
    `module_name_from_path(path, rootdir)`, for example `python.corpus-structure.tests.conftest`,
    and registers it in `sys.modules` under that name.
  - Because `python/corpus-structure/tests` is on `pythonpath` (`pyproject.toml`), an
    `import conftest` or `import test_x` from that directory would load the **same file a second
    time under a different name**. That second module object has its own module-level caches and
    side effects, and any fixtures it defines get their own `FixtureDef`, which means separate
    session caches.
  - Package directories (`tests/semantic/`, `tests/methods/` have `__init__.py`) resolve to
    `semantic.test_x` both ways, so they produce no duplicate.
  - **Search:** grep for `from conftest|import conftest|from test_|import test_` in `tests/` and
    `python/corpus-structure/tests` found only `scripts/test_receipts.py` imported by
    `tests/scripts/*`. That file is outside `testpaths`, so pytest does not import it itself, and
    no duplicate arises in normal runs.
  - Explicit `spec_from_file_location` loads (`core/test_references.py:202`,
    `fixtures/test_fixtures.py:36`, `ingest/test_managed_recognition.py:16`,
    `semantic/test_query_compatibility.py:186`) are deliberate separate modules.
  - **The risk is real as a mechanism, but I found no current instance.**
- **The stale `pytest-logging` 2015.11.4 plugin is inert [src].** It arrives transitively through
  `linkml → prefixcommons` (`uv.lock:3910-3912`). Its `pytest11` entry point is named `logging`,
  and pluggy skips entry points whose name is already registered (`pluggy/_manager.py:513-520`).
  Because pytest's built-in `logging` plugin is registered first, the module is never imported.
  Its import-time `logging.root.setLevel(1)` therefore does not fire. No action indicated; noted
  so the reviewer does not chase it.
- **Maintenance connections [src].**
  - `cli/db.py:53-60` already uses `NullPool` with `isolation_level="AUTOCOMMIT"` for admin
    engines.
  - `core/db/store.py:132-156` uses one psycopg `ConnectionPool` (`check=ConnectionPool.check_connection`,
    `close_returns=True`) behind SQLAlchemy `NullPool` via `creator=pool.getconn`.
  - `check_connection` runs an empty query on **every** checkout, flipping autocommit if needed
    (`psycopg_pool/pool.py:554-573`): one extra round-trip per borrow.
  - Changing this only in tests would make the test configuration differ from production, which
    is the reviewer's call.
  - Any pool holding an idle connection to a template database blocks cloning (§4).

## Not established

- The GUC context of `file_copy_method` in PostgreSQL 18; the PostgreSQL documentation page does
  not say.
- Whether `pg_advisory_xact_lock` taken inside a subtransaction is released at
  `ROLLBACK TO SAVEPOINT`.
- How the WAL_LOG strategy treats unlogged relations in a template; the fetched source excerpt
  was silent.
- Exact `CountOtherDBBackends` wait behaviour in PostgreSQL 18 (I recall a short retry; not
  verified).
- All PostgreSQL source citations are `REL_18_STABLE` head, not the 18.6 tag.
- No probes, collection, test runs or database connections were made, per the brief.
