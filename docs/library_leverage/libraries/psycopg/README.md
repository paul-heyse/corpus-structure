# psycopg and psycopg-pool

**Realization assessed:** psycopg 3.3.6 (binary) and psycopg-pool 3.3.3.

**Research:** done 2026-10-29 by the R1 relational cluster.
- Overviews read end to end: [psycopg](../../../libraries/postgresql/psycopg.md) and [psycopg-pool](../../../libraries/postgresql/psycopg-pool.md).
- Follow-ups: Context7 for psycopg 3.3.6, the installed source, and a compile-only probe
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-relational/README.md)).
- The two libraries share one account. Each type keeps its own namespaced handle.

## Reusable opportunity types

<a id="psycopg-pool-sqlalchemy-delegated-pool-per-login"></a>

### `psycopg-pool/sqlalchemy-delegated-pool-per-login`

**Need:** several authenticated login principals in one process, each with admission control, all
used through SQLAlchemy.

**Mechanism:**

```python
ConnectionPool(
    conninfo,
    kwargs={"user": …, "application_name": …},
    close_returns=True,
    configure=…,
    check=ConnectionPool.check_connection,
)
create_engine("postgresql+psycopg://", creator=pool.getconn, poolclass=NullPool)
```

- `make_conninfo` merges `kwargs` over the conninfo, and kwargs win (source inspected and probed).
- A pool hands out any of its connections, so separately authenticated logins need separate pools.
- Shut down with `engine.dispose()`, then `pool.close()`.

**Negative result (3.3.3):**
- `NullConnectionPool` silently forces `close_returns=False`; the source comment reads
  "close_returns=True makes no sense".
- Behind SQLAlchemy `NullPool`, `close()` therefore physically closes the connection without
  `putconn`. From the source, this appears to leak the pool's admission slot. The leak was not
  exercised.
- So `NullConnectionPool` cannot serve as a `creator` behind `NullPool`.
- Two more 3.3.3 bugs, both fixed only in 3.3.4:
  - null pools never invoke `reconnect_failed`;
  - `check()` can grow a regular pool.

**Alternative:** `SET LOCAL ROLE` from one login. It requires that login to be a member of every
target role.

<a id="psycopg-offline-sql-composition"></a>

### `psycopg/offline-sql-composition`

**Mechanism:**
- `sql.SQL`, `Identifier`, `Literal`, `Placeholder` and `Composed`, combined with `.format`/`.join`.
- `as_string(None)` renders without a connection (probed).
- Suits SQL that cannot take parameters, such as DDL and PL/pgSQL bodies.
- Python 3.14 t-strings (`:i`, `:l`, `:q`) are an alternative in psycopg 3.3.

**Conditions:**
- `Identifier` always quotes. SQLAlchemy's preparer quotes only when required (probed), so
  byte-identical output depends on which one is used.
- `sql.SQL` fragments are trusted as-is and are not syntax-checked.

<a id="psycopg-sqlstate-error-classes"></a>

### `psycopg/sqlstate-error-classes`

**Mechanism:** named classes and helpers:
- `errors.SerializationFailure` (40001), `DeadlockDetected` (40P01), `StatementCompletionUnknown`
  (40003), `AssertFailure` (P0004);
- `errors.lookup(sqlstate)` and `diag.constraint_name`;
- SQLAlchemy exposes the underlying error as `DBAPIError.orig`.

**Condition:** these classes are *flat* subclasses of `OperationalError`. `TransactionRollback`
(class 40) is a sibling of `SerializationFailure`, not its parent (installed source;
`issubclass(SerializationFailure, TransactionRollback)` is `False`). Classify with explicit class
tuples or SQLSTATE sets, never by class-40 inheritance.

## Applicability at source `d739b88`, read through `6b2335a`

<a id="applicability-cbo-004"></a>

### CBO-004 — principals with the single-pool-owner rule: **fits with conditions**

**Opportunity:** [CBO-004](../../codebase/engineering-workflows.md#cbo-004).
**Type:** [delegated-pool-per-login](#psycopg-pool-sqlalchemy-delegated-pool-per-login).

**Premise corrections:**
- The publisher is `NOLOGIN` (`scripts/pg_semantic_roles.sh`) and is reached only through
  SECURITY DEFINER functions, so it is not a connection principal.
- The login principals are writer, reader, the evaluator added in `4de601c`, and the operator or
  migration owner.
- Since `3d97504`, `semantic/runtime.connection_settings(settings, purpose)` derives a URL for each
  purpose (write, read, evaluate, maintenance).

**Route:**
- For long-lived processes: one `ConnectionPool` plus one engine per login, using
  `kwargs={"user": principal}` (probed).
- For one-shot CLI commands: SQLAlchemy `NullPool` with a plain `psycopg.connect` creator. This
  gives up admission control.

**Ruled out for this context:**
- `SET LOCAL ROLE` from a single runtime login. It would collapse the authenticated boundary that
  ADR-0025 relies on.
- `NullConnectionPool` behind SQLAlchemy, on version 3.3.3.

**Residual decision (not a library fact):** whether "one psycopg-pool per process" (D3 §1, ADR-0025)
means one pool per login principal.

<a id="applicability-retry"></a>

### Retry classification and the `P0004` mapping (minor notes on storage-and-analytics): **fits**

- Explicit SQLSTATE sets are correct, because the class tree is flat.
- The duplicated literals could become one shared tuple, `(errors.SerializationFailure, errors.DeadlockDetected)`.
  The two owners legitimately differ on 40003 and on lost connections.
- `errors.AssertFailure` can replace the roughly seven `sqlstate == "P0004"` checks.

<a id="applicability-cbo-014"></a>

### CBO-014 (informs)

`psycopg.sql` can render the verify blocks' literals offline.
Quoting policy matters for byte compatibility with the frozen copies: see the
[SQLAlchemy applicability](../sqlalchemy/README.md#applicability-cbo-014).

## Coverage limits

- The `NullConnectionPool` slot leak is inferred from source, not exercised.
- The `SerializationFailure` hierarchy and `lookup('P0004')` were checked interactively; the
  coordinator re-verified both on 2026-10-29.
