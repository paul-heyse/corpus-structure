# SQLAlchemy

**Realization assessed:** SQLAlchemy 2.1.5, with the psycopg 3.3.6 dialect.
**Researched:** 2026-10-29 by the R1 relational cluster. The [overview](../../../libraries/sqlalchemy.md)
was read end to end. Context7 returned SQLAlchemy 2.0 pages, so 2.1 behaviour was confirmed in the
installed source. One compile-only probe was run, with no database connection
([evidence](../../../design_review/evidence/2026-10-29_library-leverage-relational/README.md)).

**Evidence marks:** **D** documented · **S** installed source inspected · **P** probe observed (compile
only).

## Reusable opportunity types

<a id="sqlalchemy-composable-predicate-lowering"></a>

### `sqlalchemy/composable-predicate-lowering`

**Need.** Validated consumer filters reach the database as SQL predicates, instead of being applied
in Python after the read.

**Recognize.** Request specs with a single fixed slot, Python filtering after `.all()`, filter
dictionaries, or SQL templates written separately for each surface.

**Mechanism.**
- Build `select()` incrementally with `.where()`, `and_`/`or_` and correlated
  `exists(select(1).where(...))` over child relations.
- Keyset paging: `col.collate("C") > :after`, with a matching `order_by(...collate("C"))` and
  `LIMIT n+1`.
- Type operands with `bindparam`/`type_coerce`/`cast`.
- A validation layer maps a closed set of (field, operator, typed operand) terms to `ColumnElement`
  builders.

**What the library discharges.** Syntax, quoting and binding, dialect rendering, and caching of
compiled statements keyed by structure. Predicates stay where the planner can see them (P).

**What remains with the caller.**
- The predicate vocabulary and its meaning, and operand validation.
- SQL three-valued `NULL` logic: `!=` excludes `NULL`.
- Collation choice and index availability.
- Authorization: query predicates are not security.

**Conditions.**
- Each predicate shape is its own cache key, so keep the vocabulary closed.
- Binds against `Text` render a `::VARCHAR` cast under psycopg; this is harmless (P).

<a id="sqlalchemy-array-membership-binding"></a>

### `sqlalchemy/array-membership-binding`

**Need.** Filter by a client-side set of keys of unbounded size.

**Mechanism.**
- `col.in_(seq)` expands to one bind per element (P). SQL text and parameter count therefore grow
  with the set.
- `col == any_(bindparam("ids", type_=ARRAY(Text)))` renders a single `::TEXT[]` parameter at any
  size (P). psycopg adapts lists to arrays, and `ANY` over an empty array is false (D).
- If the set can be derived in the database, `col.in_(select(...))` or a join keeps it there.

**Limits.**
- The libpq/protocol Bind message caps parameters at 65,535 (documented; not exercised).
- Varying statement text also defeats prepared-statement reuse.
- `NULL` elements compare as `NULL`, and the element type must match.

<a id="sqlalchemy-recursive-closure"></a>

### `sqlalchemy/recursive-closure`

**Need.** Transitive reachability over parent/child or reference graphs, evaluated in the database.

**Mechanism.**
- `select(...).cte(name, recursive=True)` extended with `.union(...)` deduplicates, so cycles
  terminate under set semantics.
- `.union_all(...)` needs its own cycle guard.
- **Graphs with mixed node kinds:** join a non-recursive `union_all` edge relation that carries
  explicit kind columns. This respects PostgreSQL's single recursive self-reference (P).
- `in_(select(closure.c.node))` feeds bulk reads without moving the set to the client.

**Remains with the caller.** Termination and depth policy, and edge semantics.

**Unverified.**
- Whether the planner pushes joins into each branch of a `UNION ALL` edge relation.
- No Core construct was found for PostgreSQL `SEARCH`/`CYCLE`; this was a negative search only.

<a id="sqlalchemy-streamed-core-results"></a>

### `sqlalchemy/streamed-core-results`

**Need.** Read a large result inside one snapshot without materializing it.

**Mechanism.** `execution_options(yield_per=N)`, or `stream_results=True` with
`Result.yield_per`/`.partitions()`. The psycopg dialect uses named server-side cursors (D, S).

**Conditions.**
- The cursor is WITHOUT HOLD, so it is bound to its transaction's snapshot.
- The connection stays occupied for the whole stream, which consumes pool capacity.
- Not compatible with pipeline mode; calling `.all()` defeats it.
- **Not supplied:** byte or character budgets.

<a id="sqlalchemy-transaction-characteristics"></a>

### `sqlalchemy/transaction-characteristics`

**Mechanism.**
- `execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True[, postgresql_deferrable=True])`,
  on a Connection or an Engine.
- psycopg itself composes `BEGIN ISOLATION LEVEL … READ ONLY` (S), so a hand
  `SET TRANSACTION READ ONLY` is unnecessary.

**Conditions.**
- Setting these after the transaction has begun raises `InvalidRequestError` (S).
- At checkin they are reset to *explicit* values, so `READ WRITE` overrides a role's
  `default_transaction_read_only`. This reset happens before `NullPool` closes the connection.
- An external psycopg pool does not reset these attributes (S).

<a id="sqlalchemy-ddl-text-emission"></a>

### `sqlalchemy/ddl-text-emission`

**Mechanism.**
- Compile `CreateTable`/`CreateIndex`/`AddConstraint`/`CreateSchema` offline with
  `.compile(dialect=postgresql.dialect())`.
- `@compiles` covers custom elements.
- Temporary tables: `Table(..., prefixes=["TEMPORARY"], postgresql_on_commit="DROP")`.
- `MetaData.naming_convention` gives stable constraint names.

**Discharges.** Types, keys, foreign keys, CHECKs, names, and quoting only where required.

**Remains.**
- Objects outside MetaData: functions, triggers, grants, and views unless `CreateView` is used.
- Statement ordering and the freeze/review workflow.
- Exact text is not stable across SQLAlchemy releases, so normalize whitespace and compare at the
  held version.

**Deterministic emitter.** It compiles constraints deterministically. Contrast Alembic's offline
`CreateTableOp`, whose constraint order varies between processes
([alembic](../alembic/README.md#alembic-structured-diff-to-reviewed-artifact)).

## Applicability at source `d739b88` (sources read through `6b2335a`)

<a id="applicability-cbo-001"></a>

### CBO-001 — composable semantic read boundary: **fits with conditions**

**Opportunity:** [CBO-001](../../codebase/consumers-and-operations.md#cbo-001).
**Types:** composable-predicate-lowering, array-membership-binding, recursive-closure,
streamed-core-results, transaction-characteristics.

**Predicate builder.**
- Core composes release-scoped correlated `EXISTS` over `value_role`/`typed_value` with the
  C-collated keyset in one SELECT (P). Release checking stays with the repository.
- **Three lowering gaps the opportunity did not record:**
  - Floats are stored as hexadecimal text, so float range predicates have no exact SQL lowering.
  - Decimals beyond PostgreSQL `NUMERIC` bounds have `NULL` `numeric_value`, so an exact predicate
    must report them as unknown, not absent.
  - The reader lacks EXECUTE on `data.value_matches` and `data.compare_decimal`, so reader queries
    cannot reuse native value meaning.

**Envelope.** SQLAlchemy supplies no response budget. Pages are already bounded (`page_size ≤ 10000`).
Streaming applies only to unbounded export inside one REPEATABLE READ, read-only snapshot.

**Set-oriented explanation: fits.** Each `explain` statement can be keyed by
`fact_id = ANY(:fact_ids)` as one array bind (P).

**Robustness.** `_values` and `_entities` use expanding `.in_()` and would hit the parameter ceiling
on large sets. `in_(select(closure.c.value_id))` removes that.

**Read-only option: fits.** `postgresql_readonly` can replace the hand
`SET TRANSACTION READ ONLY` in `query.py`, `domain_operations.py` and, since `7cfd7f8`,
`cli/export.py`.

**Concurrent evidence.** SP-08 commit `7cfd7f8`, which landed during this assessment, introduced
`serve/read.py` ("Composable, batched Core reads"). It uses a correlated recursive closure of this
type's shape.

**Unsettled.** Whether a closed, release-validated predicate vocabulary falls inside SP-08's ban on
a new query language.

<a id="applicability-cbo-014"></a>

### CBO-014 — generated transport SQL: **fits with conditions**

**Opportunity:** [CBO-014](../../codebase/storage-and-analytics.md#cbo-014). **Type:** ddl-text-emission
(and [`psycopg/offline-sql-composition`](../psycopg/README.md#psycopg-offline-sql-composition)).

- `CreateTable` over the shared MetaData reproduced the frozen `semantic_0027_exclusions.sql`
  `CREATE TABLE` text **exactly** for both tables, after whitespace normalization (P). Table DDL for
  a new staged relation can be emitted.
- **Premise refinement.** `STAGE_TYPES` already derives column types from MetaData. What is written
  by hand is the row dataclasses and the PL/pgSQL create/verify/content/insert blocks. No library
  writes PL/pgSQL, so that generator stays repository-owned templating.
- **Quoting.** The preparer's quote-only-when-required matches the existing frozen spelling;
  `psycopg.sql.Identifier` would change bytes (P).
- **Real lever.** The authoring-time route of [LOP-X002](../../assessment-patterns.md#lop-x002):
  emit the next frozen file and compare it with head.

<a id="applicability-cbo-020"></a>

### CBO-020 — reachability-driven known-input loading: **fits with conditions; premise corrected**

**Opportunity:** [CBO-020](../../codebase/consumers-and-operations.md#cbo-020). **Types:**
recursive-closure, array-membership-binding.

**Corrections.**
- Identity resolution needs memberships plus decoded identity-group and display-label values for
  every known entity. Decoding can only be narrowed *by property*.
- The reachable set is seeded from Python resolution output, so a database closure must be a second
  phase.
- Independently of reachability, the known-entity sets are sent as expanding binds (`in_(ids)` ×4).
  These would hit the 65,535-parameter ceiling. Deriving them in the database is a robustness gain on
  its own.

**Route.**
1. Phase 1 reads memberships plus facts restricted to identity and display properties.
2. Phase 2 runs a recursive closure over a `UNION ALL` edge relation (P).

**Unsettled.**
- Whether native `kind='entity'` traversal equals the release-typed `_entity_references` walk.
- Planner fit.

<a id="applicability-cbo-008"></a>

### CBO-008 (informs)

The DDL compiler reproduces 0027's tables exactly, so emitting the next revision's table DDL is
grounded. Comparison and blind spots are on the [Alembic account](../alembic/README.md#applicability-cbo-008).

## Coverage limits

- Probes were compile-only: nothing was established about PostgreSQL acceptance, plans or timing.
- The parameter ceiling is documented, not exercised.
- Not inspected: `entity_keys`, `_entity_references` and the serve-layer budgets.
