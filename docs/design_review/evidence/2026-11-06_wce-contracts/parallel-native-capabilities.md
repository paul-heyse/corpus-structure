# Native parallel execution: library contracts and bounded choices

**Source-inspected and bounded native-tested, 2026-11-06.** This is task-specific capability evidence for the WCE execution increment, not a new test-architecture review or authorization to resume the separately stopped qualification plan.

## Actual failure and correction

The unchanged23-case contribution/operation native selection failed during concurrent bootstrap with PostgreSQL `OutOfMemory: out of shared memory` and the explicit `max_locks_per_transaction` hint. `parallel-native-002.log` preserves23 setup errors in10.53seconds. The single-case `-n auto` diagnostic passed, isolating concurrent bootstrap as the material difference.

The root provisioned dedicated18/corpus with max_connections256 and max_locks_per_transaction1024, preserving32 pytest workers. `parallel-native-003.log` then records **23 passed**,96warnings,87.63seconds for the unchanged selection under `uv run pytest -n auto python/corpus-structure/tests/semantic/test_contributions_native.py python/corpus-structure/tests/evaluate/test_operation_assessment_native.py --tb=short`. No test infrastructure or product implementation change was needed to make this route pass. This is a bounded native result, not full application qualification.

`parallel-native-003-monitor.jsonl` retains ten read-only samples with settings and lock/session counts during the later test phase: up to43 sessions,949 lock rows and zero waiting locks in that sampling window. It does not capture the bootstrap peak. An earlier exploratory snapshot during bootstrap observed277557 `pg_locks` rows,41 sessions and16 active head-template databases. Row counts are observations, not a general lock-capacity model or throughput claim.

## psycopg-pool3.3.3: already selected at the correct owner

Context7 was resolved first to `/psycopg/psycopg`, then queried for SQLAlchemy integration and lifecycle semantics. Current official documentation confirms `close_returns=True` with `creator=pool.getconn` and SQLAlchemy `NullPool`; installed exact-version `psycopg_pool/pool.py` confirms the3.3.3 constructor, check/return/reset behavior. Sources: [pool integration](https://www.psycopg.org/psycopg3/docs/advanced/pool.html#pool-sqlalchemy), [pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html), [process ownership](https://www.psycopg.org/psycopg3/docs/advanced/async.html#concurrent-operations).

The production `core/db/store.py` already implements that composition:

- `ConnectionPool(open=False, close_returns=True)` is opened explicitly and supplied to `create_engine(..., creator=pool.getconn, poolclass=NullPool)`. There is one connection inventory, not two competing pools.
- `configure` sets adapters/notice handling without opening a transaction. Startup extension compatibility is checked after opening, so a deterministic incompatibility is not converted into repeated connection retries and a pool timeout.
- `ConnectionPool.check_connection` checks borrowed connections; pool min/max/queue/checkout bounds are explicit. `Store.diagnostic` reads nondestructive `get_stats`, and its timing scope explicitly excludes generic SQLAlchemy getconn usage.
- The store owns engine disposal and pool closure, including both cleanup attempts. Connections are created within the process/invocation lifetime, not passed between pytest workers.

No additional pool integration is required by the observed bootstrap failure. A pool cannot release relation locks legitimately held until a migration transaction commits. The test administration path intentionally uses direct SQLAlchemy `NullPool` connections rather than the production store: `PgAdmin.connect` physically closes each connection, and `PgAdmin.lease` relies on that close to release session advisory locks. Applying a pool there without changing the lease contract would retain those locks across checkouts. It would also require rechecking session `SET ROLE`, transaction, owner/ACL replay and database-drop cleanup. That is a semantic lifecycle change, not a safe performance switch; no such change is selected here.

## pytest-xdist3.8.0: avoiding redundant bootstrap without serializing tests

Context7 was resolved to `/pytest-dev/pytest-xdist/v3.8.0`; [tagged how-to documentation](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/how-to.rst) confirms that session fixtures run separately in each worker. It shows `tmp_path_factory.getbasetemp().parent` with `FileLock` for publishing expensive data once, and `testrun_uid` for cross-worker run identity. The recipe coordinates initialization; it does not require serial test execution.

The current `semantic_head_template` in package `tests/conftest.py` uses PID/UUID naming and `PgAdmin.semantic_template`, so each participating worker cold-bootstraps its own complete head deployment. Function-scoped semantic consumers then clone that worker's sealed template, replay database policy, and own separate cleanup. Bare/revision fixtures deliberately retain bootstrap and historical-upgrade coverage.

A bounded future improvement is one **run-scoped sealed head template** shared by workers while preserving a distinct database per functional test. It can remove repeated head bootstrap rather than serializing native tests. The complete integration must include:

1. A unique test-run identity and an exact head/source context; no cross-run mutable cache adoption.
2. Once-only creation/publication under a cross-worker lock, using existing acknowledged database ownership and policy metadata. A name or JSON file alone is not disposal authority.
3. A template lifetime extending until every worker has finished cloning. The example's FileLock alone does not solve teardown: if the creating worker exits first, its current context manager would otherwise drop the template while siblings still need it. Controller-owned cleanup or a reconciled shared-lease owner must close that gap.
4. Independent per-test clones, exact owner/ACL/role-setting replay and failed-acquisition cleanup; existing bare and historical-revision routes remain actual execution paths.
5. A multi-worker test proving one bootstrap, concurrent independent clones, early worker completion, creation failure and final cleanup. Do not infer lifetime correctness from a file's existence.

This improvement is **not implemented or required for the corrected23-case route**, which now passes with the intended32-worker scheduler and provisioned cluster capacity. It remains a concrete option if repeated bootstrap becomes an execution bottleneck worth the ownership/lifecycle change. No unused cache, process-global pool, worker cap or duplicate resource manager was introduced for this inquiry.
