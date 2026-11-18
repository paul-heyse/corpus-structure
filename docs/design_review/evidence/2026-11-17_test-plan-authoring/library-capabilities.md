# LIB_TEST: library capabilities for the test-system target design

Research date 2026-11-17. Read-only. `SP` = `/home/paul/corpus-structure/.venv/lib/python3.14/site-packages`.
Evidence labels: **Doc** = documented guarantee (URL); **Src** = observed in installed source (path:line),
not a promise; **Unconfirmed** = stated from general knowledge, not verified here.

## Pinned versions (verified 2026-11-17)

| Package | Pin | Where declared |
|---|---|---|
| pytest | 9.1.1 | root `pyproject.toml` dev group |
| pytest-xdist | 3.8.0 (execnet 2.1.2 transitive) | root dev group |
| hypothesis | 6.170.12 | root dev group |
| cachetools | 7.2.7 (`SP/cachetools/__init__.py:15`) | `python/corpus-structure/pyproject.toml:65` |
| psycopg[binary] / psycopg-pool | 3.3.6 / 3.3.3 | package pyproject:21-22 |
| sqlalchemy | 2.1.6 | package pyproject:33 |
| filelock | 4.2.4 | **transitive only** (uv.lock:1710); not declared. Direct use needs `UV_LOCKED=0 uv add filelock==4.2.4` |
| PostgreSQL server | 18.7 (`/usr/lib/postgresql/18/bin/postgres --version`) | cluster 18/corpus |

Current pytest config already: `--strict-markers --strict-config -n auto --dist=loadgroup --max-worker-restart=0`.

---

## A. pytest 9.1.1

**A1. The fixture graph is available at collection, per item.**
- `item.fixturenames` (public attribute of `pytest.Function`) is set to `fixtureinfo.names_closure`
  (Src `SP/_pytest/python.py:1219,1654`): the transitive closure of argnames + `usefixtures` + autouse,
  sorted highest scope first (Src `SP/_pytest/fixtures.py:1853-1898`).
- `item._fixtureinfo` (`FuncFixtureInfo`: `argnames`, `initialnames`, `names_closure`, `name2fixturedefs`)
  gives the resolved `FixtureDef` chain per name, last = closest override (Src `fixtures.py:390-418`).
  **Private** (underscore). `pytest.FixtureDef` is exported (`SP/pytest/__init__.py:114`) but "only explicitly
  documented fields and methods are considered public" (Src `fixtures.py:1050-1055`); `argname`, `scope`,
  `func`, `params`, `argnames` exist (Src `fixtures.py:1104-1131`).
- **Limit (Doc in source docstring, `fixtures.py:399-401,412`):** fixtures requested dynamically via
  `request.getfixturevalue()` are not in the closure. Any grouping/identity derived from the graph is blind
  to them; the design must forbid or declare dynamic requests for preparation fixtures.
- **Limit (Src `fixtures.py:1776-1803`):** in 9.1.1 conftest fixtures are parsed only when their
  `Directory` is collected (`_pending_conftests`). So "all fixture definitions" exists only after collection
  and only for the collected subtree.
- Hook point: `pytest_collection_modifyitems(session, config, items)`; also `pytest_collection_finish(session)`.
  pytest's own `FixtureManager.pytest_collection_modifyitems` calls `reorder_items` to cluster items by
  higher-scoped (parametrized) fixtures (Src `fixtures.py:255,1945-1947`).
- Public hooks seeing `FixtureDef` at run time: `pytest_fixture_setup(fixturedef, request)`,
  `pytest_fixture_post_finalizer(fixturedef, request)` (Doc https://docs.pytest.org/en/9.1.x/reference/reference.html#pytest_fixture_setup).
- CLI inspection (no code): `--fixtures-per-test`, `--setup-plan`, `--setup-show`.

**A2. Dynamic scope.** `@pytest.fixture(scope=callable)`; callable signature `(*, fixture_name, config)`
returning a scope string, evaluated **once at fixture definition** (Doc
https://docs.pytest.org/en/9.1.x/how-to/fixtures.html#dynamic-scope; Src `fixtures.py:1027-1047,1110-1116`).
It cannot vary per item or per key; it only selects a scope from config/options. Note: pytest caches one
instance of a fixture at a time per scope (Doc, same page "Fixture scopes" note), so a session fixture is an
in-process memo, not a keyed cache.

**A3. Dead fixture names: what pytest does and does not check.**
- A test parameter naming an undefined fixture fails only at **setup**, not collection: `getfixturedefs`
  returns None and the closure carries the name on ("will error during runtest", Src `fixtures.py:1873-1877`);
  error text "fixture 'x' not found" (Src `fixtures.py:950`).
- `--strict-markers` / `strict_markers` covers only **marker** names registered in `markers`; `strict = true`
  (ini) enables strict_config, strict_markers, strict_xfail, strict_parametrization_ids (Src `SP/_pytest/main.py:85-116`).
  There is **no** strict-fixture-name option and nothing that validates a user-maintained table of fixture names.
- Marks cannot carry metadata on fixtures: "Marks cannot be applied to fixtures" is an error since 9.0
  (Doc https://docs.pytest.org/en/9.1.x/deprecations.html#applying-a-mark-to-a-fixture-function; Src
  `fixtures.py:1366`, `mark/structures.py:492`). Exception: `pytest.param(..., marks=...)` in fixture `params`
  does propagate marks such as `xdist_group` to items (Doc, xdist distribution page below).
- Consequence for (5): a declarative name table can be checked only (a) after collection, (b) relative to the
  collected subtree (A1 limit), and (c) via private `session._fixturemanager.getfixturedefs(name, node)` /
  `_arg2fixturedefs` (Src `fixtures.py:2135-2154`). A check on the union of `item.fixturenames` is public but
  gives false "dead" verdicts under `-k`/path selection. **The route that removes the problem by construction**
  is to attach the group/identity to the fixture definition itself (a project decorator that wraps
  `pytest.fixture` and registers `{fixture_name: PreparationSpec}` in a module-level registry at import), then
  derive groups from `item.fixturenames ∩ registry`. No table exists to go stale; a renamed fixture carries its
  spec with it. Raise `pytest.UsageError` from `pytest_collection_modifyitems` for structural violations
  (e.g. an item needing two incompatible preparations), which aborts before any test runs.

**A4. `pytest.Cache` (`config.cache`).** (Src `SP/_pytest/cacheprovider.py`)
- `cache.mkdir(name) -> Path`: persistent directory under `.pytest_cache/d/<name>`, "to e.g. store/retrieve
  database dumps across test sessions" (`:163-182`). Persists across sessions; shared by all xdist workers
  (same rootdir). `--cache-clear` wipes it; `-p no:cacheprovider` disables it.
- `cache.get(key, default)` / `cache.set(key, json_value)`: JSON values; `get` swallows read errors and returns
  default (`:187-204`); `set` opens with `"w"` and writes in place, **not atomic, no locking** (`:206-235`).
  Unsuitable as the authority for prepared-state identity under concurrency; usable as a location.
- pytest itself uses the build-in-tempdir-then-`rename` pattern for its cache dir, with the loser of a
  concurrent rename discarding its copy (`:59-80`). That is the pattern to copy for content-addressed dirs.

**A5. `tmp_path_factory` and the xdist shared-session pattern.** `tmp_path_factory.getbasetemp().parent` is
the directory shared by all workers of **one run**; documented pattern is `FileLock(path + ".lock")` around
"if file exists read else produce and write" (Doc https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/how-to.rst
"Making session-scoped fixtures execute only once"). Limits: basetemp is per run (`pytest-of-<user>/pytest-N`,
retention via `tmp_path_retention_count`/`_policy`, Src `SP/_pytest/tmpdir.py:95-111`), so it gives
cross-worker reuse but **not** cross-session reuse; the doc example writes the payload non-atomically inside
the lock and has no key/invalidation. It is a starting point, not identity management.

**A6. Stash.** `pytest.StashKey[T]()`; `config.stash`, `session.stash`, `item.stash` (typed, plugin-private
storage) (Doc https://docs.pytest.org/en/9.1.x/how-to/writing_hook_functions.html#storing-data-on-items-across-hook-functions).
Fits: carry a computed `PreparationKey` from collection hooks to fixtures, replacing ad hoc module globals and
hand-rolled holders. In-process only.

## B. pytest-xdist 3.8.0

**B1. Modes and actual guarantees** (Doc https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst;
Src `SP/xdist/scheduler/`):

| Mode | Guarantee | What it does not give |
|---|---|---|
| `load` | none on order/affinity | |
| `loadscope` / `loadfile` | all tests of a module/class (file) run on one worker | no affinity between different scopes sharing a session fixture |
| `loadgroup` | all tests with the same `xdist_group` name run on one worker; ungrouped tests behave as `load` | group is one indivisible work unit (a big group serializes on one worker); different groups needing the same session fixture may each build it on different workers |
| `worksteal` | even split + stealing | **ignores groups/scopes entirely** (no scope logic in `worksteal.py`) |

- **Multi-group union:** a test with several `xdist_group` marks gets a **new joined group** (names sorted and
  joined with `_`) (Doc above; Src `SP/xdist/remote.py:242-253`). So "test needs fixtures A and B" lands in
  group `A_B`, not with A-only tests. A fixture-derived scheme must map each item to **one** group key (e.g. the
  preparation identity it needs), not emit one mark per requested fixture.
- **Mechanism (Src):** the worker plugin rewrites `item._nodeid` to `nodeid@group` in its
  `pytest_collection_modifyitems` (`remote.py:236-253`); `LoadGroupScheduling._split_scope` splits on the last
  `@` (`loadgroup.py:24-60`). Work units are dispatched whole; a node gets another unit when it has ≤2 pending
  tests; extra workers beyond the number of units are shut down (`loadscope.py:313-408`). `--loadscope-reorder`
  (default True) sorts units by size, largest first (`plugin.py:130-155`); within a unit, collection order is kept.
- **Hook ordering hazard (Src, not documented):** `WorkerInteractor` is registered after config/initial
  conftests are loaded (`remote.py:420-427`, register at `:122`), and pluggy calls later-registered impls first.
  A root-conftest hook that adds `xdist_group` marks should therefore be `@pytest.hookimpl(tryfirst=True)`, or
  the marks can be added after xdist has already read them.
- **Collection must be identical on all workers** or the run aborts (`loadscope.py:409+`); group derivation must
  be deterministic (no worker-dependent or time-dependent keys).

**B2. Custom scheduler.** `pytest_xdist_make_scheduler(config, log) -> Scheduling | None` (firstresult;
Src `SP/xdist/newhooks.py:96-100`; default impl `dsession.py:107-126`). The controller **never collects**
(`dsession.py:103-105`), so a scheduler sees only node ids (`_split_scope(nodeid)`), never fixtures. Any
graph-derived grouping must therefore be computed on workers and encoded into the nodeid (which `loadgroup`
already does via the mark). A subclass of `LoadScopeScheduling` overriding `_split_scope` is possible but
those internals are undocumented; prefer marks + built-in `loadgroup`.

**B3. Identity and controller-to-worker data.**
- `worker_id` fixture ("gw0".. or "master" without xdist), `testrun_uid` fixture (shared by all workers of a
  run; overridable with `--testrunuid`), env `PYTEST_XDIST_WORKER`, `PYTEST_XDIST_WORKER_COUNT`,
  `PYTEST_XDIST_TESTRUNUID` (Src `remote.py:415-418`), helpers `xdist.is_xdist_worker`,
  `is_xdist_controller`, `get_xdist_worker_id` (Src `plugin.py:342-404`; Doc how-to.rst "Identifying the worker").
- `pytest_configure_node(node)` runs on the controller before the worker starts; `node.workerinput[...]` values
  arrive as `config.workerinput` on the worker (Src `workermanage.py:308,342,349`; Doc how-to.rst "Accessing
  sys.argv from the controller node in workers"). Fit: compute a selection-independent key once (e.g. migration
  digest) on the controller and ship it, instead of each worker hashing.
- Controller `DSession.pytest_sessionstart` is `trylast` (`dsession.py:82-92`), so a conftest
  `pytest_sessionstart` runs on the controller **before workers spawn**: a place to build selection-independent
  prepared state (the migrated base template) exactly once with no lock. Limit: the controller does not know
  which items were selected, so only always-needed preparations belong there.
- `testrun_uid` names per-run resources; it is the wrong key for cross-session reuse (changes every run).

## C. PostgreSQL 18 isolation

**C1. `CREATE DATABASE name TEMPLATE tpl STRATEGY = WAL_LOG | FILE_COPY`** (Doc
https://www.postgresql.org/docs/18/sql-createdatabase.html):
- `WAL_LOG` (default): block-by-block copy with every block WAL-logged; "most efficient when the template is small".
- `FILE_COPY`: directory-level copy, small WAL record, but **forces a checkpoint before and after**.
- **`file_copy_method` exists in 18 (verified):** values `copy` (default) | `clone`; affects only
  `STRATEGY=FILE_COPY` and `ALTER DATABASE SET TABLESPACE`; `clone` uses `copy_file_range()` on Linux, "giving the
  kernel the opportunity to share disk blocks" (Doc https://www.postgresql.org/docs/18/runtime-config-resource.html#GUC-FILE-COPY-METHOD;
  release note https://www.postgresql.org/docs/18/release-18.html; present in this host's
  `/etc/postgresql/18/corpus/postgresql.conf:181`, commented). **Host fact:** the data directory
  `/var/lib/postgresql/18/corpus` is on `/` = **ext4**, which has no reflinks, so `clone` would at best give an
  in-kernel copy, not block sharing; real block sharing needs XFS(reflink)/Btrfs. Effect not measured.
- **No other connection to the template** may exist when `CREATE DATABASE` starts, and new connections are locked
  out during the copy (Doc same page, Notes; https://www.postgresql.org/docs/18/manage-ag-templatedbs.html).
  Use `ALTER DATABASE tpl IS_TEMPLATE true ALLOW_CONNECTIONS false` once built (`datistemplate` lets any
  `CREATEDB` role clone; `datallowconn=false` blocks new sessions but does not kill existing ones).
- **Unconfirmed:** several concurrent `CREATE DATABASE ... TEMPLATE same_tpl` from different workers are permitted
  (the source DB is share-locked); measure before relying on parallel clones.
- `CREATE DATABASE` cannot run in a transaction block (needs autocommit in psycopg). `DROP DATABASE ... WITH (FORCE)`
  terminates sessions (PG13+).
- Composition for (1) (Proposed): name the template by key digest (`tpl_<hex>`, ≤63 bytes), build into a
  scratch DB, then `ALTER DATABASE build_x RENAME TO tpl_<hex>` + `IS_TEMPLATE true`; serialize builders of one
  key with `pg_advisory_lock(<key-hash bigint>)` on a maintenance-DB connection (session-level advisory locks
  survive rollback and end with the session; Doc https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS).
  Existence in `pg_database` is then the cross-worker, cross-session cache lookup; a changed key is a different
  name, so invalidation is by key; old names need explicit GC. This is the DB analog of content-addressed dir +
  atomic rename and needs no file lock.

**C2. What each isolation route cannot isolate.**

| Route | Cost | Cannot isolate |
|---|---|---|
| Clone per test (C1) | one `CREATE DATABASE` per test (+checkpoints if FILE_COPY) | **cluster-global** objects: roles and role memberships, `GRANT ... ON DATABASE`/database ownership (in shared `pg_database`), tablespaces, `ALTER SYSTEM`/server settings, `ALTER ROLE ... SET`, replication slots, connection-count limits |
| Outer transaction + rollback (psycopg `conn.transaction(force_rollback=True)`, Src `SP/psycopg/connection.py:352-354`; SQLAlchemy `Session(bind=conn, join_transaction_mode="create_savepoint")`, Src `SP/sqlalchemy/orm/session.py:1738-1750`) | cheapest | **sequences** (`nextval`/`setval` never roll back, Doc https://www.postgresql.org/docs/18/functions-sequence.html); work on other connections (pools, background workers, separate engines) and anything the code commits itself unless every nested scope maps to SAVEPOINT; session-level advisory locks (survive rollback); `NOTIFY` (delivered only at commit, so never observed); `now()` frozen at transaction start; non-transactional DDL (`CREATE DATABASE`, `CREATE INDEX CONCURRENTLY`, `VACUUM`); code that asserts on commit-time effects (deferred constraints, commit triggers) |
| Schema per test (`search_path`) | cheap DDL | extensions (one per DB), event triggers, publications, DB-level settings, roles; any SQL with schema-qualified names (migrations usually are); `pg_catalog` queries that span schemas |

Advisory lock keys are per database (`pg_locks.database`; Unconfirmed from source, not re-read here), so
clones isolate advisory locks taken inside them; the maintenance-DB lock in C1 is deliberately shared.

## D. Determinant-perturbation testing (refuse when any key determinant changes)

- **Plain pytest (stdlib):** `@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(Key)])`
  plus a hand-authored `PERTURB: dict[str, Callable[[Key], Key]]` built with `dataclasses.replace`, and one
  completeness test `assert {f.name for f in fields(Key)} == PERTURB.keys()`. Adding a field fails until someone
  authors its perturbation: no lint needed. Deterministic, no generated-history state.
- **Hypothesis 6.170.12:** `st.builds(Key)` / `st.from_type(Key)` (dataclass annotations), `st.sampled_from(fields(Key))`,
  `st.data()` + `data.draw(st.from_type(f.type).filter(lambda v: v != getattr(base, f.name)))`, then
  `dataclasses.replace`. Stateful: `hypothesis.stateful.RuleBasedStateMachine` with `@initialize`, `@rule`,
  `@precondition`, `@invariant`, `Bundle`; expose as `TestX = Machine.TestCase` or `run_state_machine_as_test`
  (Src `SP/hypothesis/stateful.py:287,549`); `settings(stateful_step_count=..., max_examples=...)`. A machine with
  rules warm / perturb(field) / restore / query and an invariant "hit iff current key == a warmed key" exercises
  warm→stale→rewarm sequences and shrinks failures (Doc https://hypothesis.readthedocs.io/en/latest/stateful.html).
  The example database (`.hypothesis/`) is a cross-run failure history; if the project's no-history stance applies,
  register a profile with `database=None` (and optionally `derandomize=True`) (`settings` keys Src `SP/hypothesis/_settings.py:51-54`).
- **Which gives independent evidence:** neither, if the test perturbs `Key` fields and recomputes the expectation with
  the key function under test. Independent evidence comes from perturbing the **determinant sources** (a migration
  file's bytes, a seed recipe, a model source, a library version) in a temp copy and asserting the **observable
  refusal** (new template name / rebuild / skip refused) against a hand-written expectation. That also catches the
  failure field-perturbation cannot: a determinant missing from `Key` entirely. The parametrize route is the better
  default for a closed, small set of determinant kinds; Hypothesis adds value for the stateful sequence (cache
  lifecycle ordering) and for value-shaped fields, not for completeness.

## E. cachetools 7.2.7 (and 8.0.0)

- API at 7.2.7 (Src `SP/cachetools/__init__.py:750-801`, `_cached.py`): `cached(cache, key=keys.hashkey, lock=None,
  condition=None, info=False)`, `cachedmethod(cache, key=keys.methodkey, lock=None, condition=None, info=False)`;
  wrapper attributes `cache`, `cache_key`, `cache_lock`/`cache_condition`, `cache_clear`, `cache_info`
  (`_cached.py:57-63,278-283`). `condition` (a `threading.Condition`) makes concurrent callers for the same key wait
  for one computation (stampede guard) (`_cached.py:20-32,157-169`). Keys: `keys.hashkey`, `typedkey`, `methodkey`,
  `typedmethodkey` (`keys.py:48-75`). Caches: `Cache`, `LRUCache`, `LFUCache`, `FIFOCache`, `RRCache`, `TTLCache`,
  `TLRUCache` (ttu called at insertion). `cachetools.func.*_cache` mirror `functools.lru_cache`.
- 8.0.0 (per repo overview `docs/libraries/analytical_infrastructure/cachetools.md` §11, not independently verified):
  public `CacheInfo`, callable wrapper objects, `cache_info` absent when `info=False`, `cached(cache=None)` → TypeError,
  `cachedmethod` needs mutable instance `__dict__`. **No new cross-process or persistence capability.**
- **Does not provide** (Doc/overview, consistent with source): cross-process sharing, persistence, file/DB-backed
  storage, cross-process locking, dependency-driven invalidation. Everything is a per-process `MutableMapping`.
  Under xdist each worker has its own copy. Fit: replace hand-rolled in-process holders (with `cache_key`/`cache_clear`
  for targeted invalidation and `info=True` for hit/miss assertions in tests). Not a fit for (1).
- **Cross-process / on-disk prepared state, fitting primitives:**
  - Content-addressed directory: `<root>/<sha256(canonical key)>/`, build in `tempfile.mkdtemp(dir=root)`, then
    `os.rename(tmp, final)`; on `ENOTEMPTY`/`EEXIST` the loser deletes its copy and uses the winner (same pattern as
    `SP/_pytest/cacheprovider.py:59-80`; atomic only within one filesystem). Root may be `config.cache.mkdir("prep")`
    (persists across sessions) or a project-owned directory.
  - `filelock.FileLock(path, timeout=...)` (4.2.4; also `SoftFileLock`, `ReadWriteLock`) to avoid duplicate builds;
    stdlib `fcntl.flock` is an equivalent zero-dependency option on Linux. With rename-publish, the lock is only an
    efficiency measure, not a correctness one.
  - For DB-resident state, `pg_advisory_lock` + `pg_database` lookup (C1) replaces both.
  - Canonical key bytes: hash a canonical serialization (sorted JSON or `repr` of a frozen dataclass of primitives)
    with `hashlib.sha256`; for files, `hashlib.file_digest`.

## F. Other capabilities with a clear fit

- **pytest-postgresql 9.x** (repo overview `docs/libraries/postgresql/pytest-postgresql.md` §2-3, §9; not installed):
  `postgresql_noproc` + `DatabaseJanitor` create a `<db>_tmpl` template per session, clone per test with
  `CREATE DATABASE ... TEMPLATE`, drop at session end; xdist support only suffixes names with the worker id, "not a
  globally unique namespace across independent pytest invocations" (§9). It owns per-session template handling, **not**
  key-addressed cross-session reuse or migration-identity; it would replace only the clone/drop step. Weak fit given (1).
- **Selection-independent preparation on the xdist controller** (B3) plus **`pytest_configure_node`** to ship the key:
  the cheapest exact-once route for the migrated base, needing no lock at all.
- **pytest `reorder_items`** already clusters items by higher-scoped parametrized fixtures within a worker; a
  parametrized session fixture over preparation keys (`params=[pytest.param(k, marks=pytest.mark.xdist_group(k))]`)
  gets both worker affinity and in-worker ordering from built-ins (Doc xdist distribution.rst example).
- Not recommended here: `--lf`/`--ff`/`--nf`, `pytest-randomly`, flaky/rerun plugins and the Hypothesis example
  database are history features outside this project's stance.

## Could not confirm

- Concurrent clones from one template (C1) and `file_copy_method=clone` behavior on ext4: not run.
- Advisory-lock database scoping: stated from knowledge of `pg_locks`, not re-read in docs.
- cachetools 8.0.0 change list: taken from the repo overview, not upstream changelog.
- Whether pluggy ordering already puts a root-conftest hook after xdist's worker hook in this repo: inferred from
  source registration order, not executed.
