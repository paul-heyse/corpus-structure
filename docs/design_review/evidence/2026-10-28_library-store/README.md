# Library evidence: the store (how the product writes and reads PostgreSQL)

**Date:** 2026-10-28. **Lane:** library research for the store group, briefed by the design
authority ahead of the phase 0 build plan and D3's library realization. **Evidence, not authority:**
every recommendation here is **Proposed**; the coordinator decides adoption.

## Question

Which library mechanisms should phase 0 use for D3 and the D6 queue, from migration 0001 through
bulk writes, the work queue, pooling, BM25 and vectors? The brief asked for seven decisions, the
D3 simplifications that library features allow, and `Library proposal` blocks where a contract
should change.

## Baseline and method

- Repository at `71bb064`. The working tree changed while this ran: D3 now moves `kb.embedding`
  to the phase 1 migration, and `docs/plans/phase-0_2026-10-28.md` §3 item 4 makes golden passes
  queue tasks. The note was reconciled with both.
- Overviews read end to end: `docs/libraries/PostgreSQL_System_Tooling_for_Ubuntu.md`,
  `psycopg.md` (3.3.6), `psycopg-pool.md` (3.3.3), `sqlalchemy.md` (2.1.5), `alembic.md` (1.20.0),
  and `pgevector.md`. That last file is untracked and its name is misspelled; it covers the pgvector
  Python package 0.5.1 and the server extension 0.8.7, and the coordinator made it the primary
  pgvector source mid-task.
- **pg_textsearch 1.5.1 has no overview.** Every pg_textsearch finding below is marked
  *re-check against the overview*.
- After the overviews: Context7 (`/timescale/pg_textsearch`, `/websites/sqlalchemy_en`,
  `/psycopg/psycopg/3.3.6`, `/websites/alembic_sqlalchemy_en`), then the tagged upstream sources and
  the PostgreSQL 18 manual for the consequential details. Tagged clones and files were read only,
  never executed; they sit outside the repository, in the session scratchpad.
- The local server (PostgreSQL 18.6, `18.6-1.pgdg24.04+2`, cluster `18/main`, port 5432) was
  inspected **read-only**: `pg_settings`, `pg_roles`, `pg_available_extensions`, `pg_get_keywords()`,
  the extension control and SQL files, and `strings` on `pg_textsearch.so`. Nothing was created
  and no DDL was executed. Whether D3 *applies* is still S6's question.

Evidence strength tags: **Doc** is a documented guarantee at the target version. **Src** means read
in the tagged source or tests. **Obs** means observed on this machine, read-only, on 2026-10-28.
**Inf** is an inference that S6 or P0.3 should confirm.

### Sources

| Library | Version examined | Primary sources |
|---|---|---|
| PostgreSQL | 18.6 installed | Manual 18: `release-18.html`, `sql-copy.html`, `sql-createtable.html`, `sql-createdatabase.html`, `sql-select.html` (locking clause), `sql-notify.html`, `datatype-json.html` §8.14.4, `ddl-generated-columns.html` |
| pg_textsearch | 1.5.1 installed (`/usr/share/postgresql/18/extension/pg_textsearch--1.5.1.sql`) | `github.com/timescale/pg_textsearch` tag `v1.5.1`: `README.md`; `src/planner/hooks.c` (`transform_text_text_opexpr`, l. 785); `src/index/resolve.c` (`tp_resolve_index_name_shared`, l. 69); `src/mod.c` l. 484–489; `test/sql/implicit.sql` l. 118–154, `schema.sql`, `text_config.sql`, `partial_index.sql` |
| pgvector (server) | 0.8.7 installed (`vector.control`) | Overview `docs/libraries/pgevector.md`; `github.com/pgvector/pgvector/blob/v0.8.7/README.md` l. 252–253, 440–456, 480–545, 831–850, 935–949 |
| pgvector (Python) | 0.5.1, the PyPI latest on 2026-10-28 | Overview §3–§4, §8.1; `pgvector-python` v0.5.1 README |
| psycopg | 3.3.6, PyPI latest; binary wheels include cp314 | Overview; tag `3.3.6`: `docs/basic/copy.rst`, `psycopg/_copy_base.py` l. 113–138, `_py_transformer.py` l. 164–167, `types/json.py` l. 199–262 and 303–314, `_typeinfo.py` l. 95–108, `connection.py` l. 372–383 |
| psycopg-pool | 3.3.3, PyPI latest | Overview; `psycopg_pool/pool.py` (constructor defaults l. 49–70; `configure` state check l. 634–639) |
| SQLAlchemy | 2.1.5 pinned in D9. **2.1.6 has been on PyPI since 2026-10-21; not evaluated** | Overview; tag `rel_2_1_5`: `dialects/postgresql/base.py` (uuidv7 `monotonic` l. 116–151; `IDX_USING` l. 2002; `_prepare_withclause_opts` l. 2848–2859; `visit_create_index` l. 2868–2950; `visit_computed_column` l. 3052–3074; `use_insertmanyvalues` l. 3646), `dialects/postgresql/psycopg.py` l. 424–461, `sql/ddl.py` (`CreateView`); Context7 for JSONB comparators, `on_conflict_*`, `returning(sort_by_parameter_order=)`, `driver_connection` |
| Alembic | 1.20.0 pinned in D9. **1.20.1 is now on PyPI; not evaluated** | Overview; tag `rel_1_20_0`: `alembic/ddl/postgresql.py` l. 315–379 (`compare_indexes`) |

## 0. Environment findings that block S6 and P0.3 (Obs, 2026-10-28)

These are prerequisites the operator has to supply. They are recorded first because S6 step 1 and
D3's first two statements fail without them.

1. **pg_textsearch is not preloaded.** `shared_preload_libraries` is
   `pg_stat_statements,auto_explain` on both local clusters, 5432 and 5433. The 1.5.1 install
   script raises *"pg_textsearch library not loaded. Add pg_textsearch to shared_preload_libraries
   and restart"*, and the library refuses a late `LOAD` (`src/mod.c` l. 484–489, Src). So
   `CREATE EXTENSION pg_textsearch` fails until `pg_textsearch` is added to the preload list and the
   cluster restarts.
2. **Neither extension is trusted, and role `paul` is not a superuser.** `paul` has CREATEDB.
   `vector.control` and `pg_textsearch.control` carry no `trusted = true`; `pg_trgm` and
   `btree_gin` do. A superuser must therefore run `CREATE EXTENSION vector` and
   `CREATE EXTENSION pg_textsearch` once per database or template (Doc: CREATE EXTENSION rules;
   Obs: control files). D3 §3's `CREATE EXTENSION IF NOT EXISTS` fails as `paul` on a fresh
   database. It is a harmless no-op once the extension already exists, because the
   existence check happens before the privilege check (Inf from PostgreSQL behaviour).
3. **The data filesystem is full.** `/` is ext4 and 100% used, with about 3.5 GB free. The
   PostgreSQL data lives there. Test databases, S6's 100k-row volume step and its HNSW builds all
   need room. Because the filesystem is ext4, `file_copy_method = clone` cannot help.
4. **What is already set up and useful.** `io_method = io_uring` on 5432 (PG18 asynchronous I/O);
   `maintenance_work_mem` 16 GB, which suits HNSW and BM25 builds; `work_mem` 256 MB;
   `max_connections` 100; `max_prepared_transactions` 0; data checksums on;
   `default_text_search_config = pg_catalog.english`, which matches D3's BM25 `text_config`;
   `pg_stat_statements` and `auto_explain` already loaded, so S6 can read plans and statement
   statistics without extra setup.
5. Both clusters hold dozens of leftover `*_test_tpl_*` template databases from another project.
   The test fixtures in §1 should drop what they create and sweep stale names.

**Provisioning recipe (operator, once):**

- Add `pg_textsearch` to `shared_preload_libraries` and restart `18/main`.
- As `postgres`:

  ```sql
  CREATE DATABASE cs_template OWNER paul;
  \c cs_template
  CREATE EXTENSION vector;
  CREATE EXTENSION pg_textsearch;
  ```
- `ci db init` and the test fixtures then create databases `TEMPLATE cs_template`. The owner, or
  any CREATEDB role once the template is `IS_TEMPLATE true`, may clone it (Doc: CREATE DATABASE,
  `ISTEMPLATE`).
- Installing the extensions in `template1` would also work, but it changes every new database on a
  shared cluster.

## 1. Migration 0001 and test databases

**Recommendation: write the metadata first; render migration 0001 from it once, then freeze it.**

`core/db` defines every D3 table as SQLAlchemy Core `Table` objects (schema-qualified, with a
naming convention). Migration 0001 comes from those objects:

- Run `alembic revision --autogenerate` against an empty database cloned from `cs_template`, then
  review the output by hand.
- The result is a frozen script of `op.create_table`, `op.create_index` and
  `op.create_foreign_key` calls. Like every migration, it never imports `core/db`: the cookbook
  rule is that historical migrations carry their own table constructs.
- `op.execute` holds only what metadata cannot express or Alembic does not compare:
  - `CREATE EXTENSION IF NOT EXISTS …`, as an assertion that provisioning happened;
  - the four `CREATE SCHEMA` statements;
  - the `kb.run_observation` view, as frozen SQL text.

**Why this rather than raw DDL in `op.execute`:**

- The table metadata has to exist and be exact anyway: D9 §1 puts it in `core/db`, and every
  typed query and upsert is built from it.
- Raw DDL would make two hand-kept copies of D3. Of their divergence, `alembic check` would see
  only part.
- Alembic renders dialect index options from metadata (`postgresql_using`, `postgresql_with`,
  `postgresql_ops`, `postgresql_where`), so 0001 costs nothing extra to produce, and later
  migrations come from autogenerate diffs.

**Metadata details:**

- **Identity.** `Column("id", BigInteger, Identity(always=True), primary_key=True)` matches D3's
  `GENERATED ALWAYS`. Leaving it implicit would give a different default form.
- **Constraint names.** `MetaData(naming_convention={"pk": "pk_%(table_name)s", "uq": "uq_%(table_name)s_%(column_0_N_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s"})`.
  Every CHECK is given an explicit name (`CheckConstraint(t.c.status.in_(TASK_STATUSES), name="status")`).
  Stable names are what Alembic relies on to drop or compare constraints (alembic overview §6.5).
- **One source for closed value sets.** Build each CHECK's list from the same Python `Literal` or
  `StrEnum` the Pydantic core types use. Prefer `Text` plus a named CHECK over `sa.Enum(native_enum=False)`:
  that type renders `VARCHAR` and has had duplicate-CHECK issues (Alembic 1.20.0 changelog).
- **The circular key.** `meta.project.promoted_run_id` uses `ForeignKey("ops.run.id", use_alter=True, name=…)`.
- **Vectors.** `pgvector.sqlalchemy.HALFVEC(n)` for the phase 1 `kb.embedding`. Importing it also
  registers reflection of the type.

**Alembic `env.py` settings:**

- `include_schemas=True`, and `include_name` restricted to `meta`, `kb`, `ops`, `eval`.
- `include_object` skips the view.
- `compare_server_default=True`.
- `autogenerate_plugins=["alembic.autogenerate.*", "alembic.ext.checkconstraint_byname"]`.
- `transaction_per_migration=True`. PostgreSQL DDL is transactional, so 0001 applies atomically;
  BM25 and HNSW index creation on empty tables happens inside the transaction.
- `alembic_version` stays in `public`, so a downgrade that drops the four schemas does not drop it.
- For tests, the connection is shared through `config.attributes["connection"]` (alembic overview §8.2).

**Limit: what `alembic check` does not see** (Src, `alembic/ddl/postgresql.py` l. 315–379 at 1.20.0).
On PostgreSQL, index comparison covers uniqueness, the indexed expressions and
`nulls_not_distinct` only. Changes to `USING`, `WITH` (HNSW `m`, BM25 `text_config`), operator
classes and partial `WHERE` predicates are invisible. CHECK constraints are compared by name only,
and only with the opt-in plugin; a changed expression under an unchanged name is not detected
(overview §4.2). Two checks are therefore needed:

1. `command.check(cfg)` for tables, columns, types, nullability, foreign keys and index columns.
2. **Optional:** one session-level test that builds one database with `upgrade head` and another
   with `metadata.create_all()` (plus the view text), then compares two sets drawn from the
   catalogs: `pg_get_constraintdef` over the four schemas, and `pg_indexes.indexdef`. This
   covers what Alembic cannot see, at the cost of one extra template clone per session. It is a
   migration test inside D9 §4's database layer, not a lint.

**Downgrade test.** Run `command.upgrade(cfg, "head")`, then `command.downgrade(cfg, "base")`.
Assert with `inspect(conn).get_table_names(schema=…)` that the four schemas are empty or gone,
then upgrade again; the round trip catches a downgrade that leaves objects behind. 0001's
downgrade is `DROP SCHEMA eval, kb, ops, meta CASCADE`. It does **not** drop the extensions: they
are provisioned, and `paul` could not recreate them. The data-loss caveat on downgrades in the
alembic overview (§10.6) does not matter for 0001.

**Fastest per-session test database** (D9 §4's `ci_test_<pid>`):

- **(a) Steady state, after the provisioning in §0.**
  - Once per migration state, build `cs_tpl_<hash of the alembic versions directory>` from
    `cs_template`, run `upgrade head` in it, and close every connection.
  - Each session: `CREATE DATABASE ci_test_<pid> TEMPLATE cs_tpl_<hash>`, on an autocommit
    connection to `postgres`.
  - The default `STRATEGY WAL_LOG` is documented as the efficient choice for small templates;
    `FILE_COPY` forces two checkpoints (Doc: CREATE DATABASE).
  - Teardown: `DROP DATABASE IF EXISTS … WITH (FORCE)`. Session start sweeps stale `ci_test_%`
    databases whose process is gone.
  - Two conditions to honour. No other session may be connected to a template while it is being
    cloned (Doc), so dispose of every engine first and serialize template building across xdist
    workers, for example with a file lock. The migration test itself clones `cs_template`, not
    the migrated template.
- **(b) No operator change needed.** `pg_virtualenv -o shared_preload_libraries=pg_textsearch -- uv run pytest …`.
  `/usr/bin/pg_virtualenv` is installed (Obs). It runs a throwaway cluster in which the invoking
  user is superuser, so `CREATE EXTENSION` works and the main cluster stays untouched. It costs
  one initdb and server start per invocation (not measured), and it uses the same full disk.
- **Isolation inside a session.** Most tests run inside an outer transaction rolled back at
  teardown: pass that SQLAlchemy `Connection` in, or use `Session(join_transaction_mode="create_savepoint")`
  where a session is used. Tests that need real commits must truncate the tables they touch or
  use their own clone. These are the queue tests with two connections and `SKIP LOCKED`,
  `NOTIFY` delivery (which happens at commit) and COPY followed by commit.

**Avoid:**

- `MetaData.create_all()` inside 0001: the migration would drift as the metadata moves on.
- Session-level `SET` on pooled connections in tests.
- Relying on `alembic check` alone for D3's CHECK-heavy design.

## 2. SQLAlchemy 2.1 Core for D3

**JSONB.**

- Columns are `sqlalchemy.dialects.postgresql.JSONB` with `server_default=text("'{}'::jsonb")`.
- Operators come as comparators:
  - `.contains(obj)` gives `@>`, which `jsonb_path_ops` GIN serves;
  - `.path_exists(path)` gives `@?`;
  - `.path_match(path)` gives `@@`;
  - `col["k"]` and `.astext` give `->` and `->>`;
  - `.has_key()` gives `?`, which **only the default `jsonb_ops` opclass serves** (Doc, Context7).
- The psycopg dialect wraps bound JSONB values in `psycopg.types.json.Jsonb` itself and renders
  bind casts (Src, `psycopg.py`).
- Index caveat (Doc, `datatype-json.html` §8.14.4). GIN serves `@?` and `@@` only by extracting
  `accessors_chain == constant` clauses. D3 §9's `qualifiers @? '$.param_values.variance'` has no
  equality, so with `jsonb_path_ops` it needs a full index scan. The existing b-tree on
  `(run_id, predicate, status)` carries that query instead (see §7 and L-S4).

**Key-idempotent writes.** Use `sqlalchemy.dialects.postgresql.insert(t)`. This replaces any
SELECT-then-INSERT logic and its races (sqlalchemy overview §9.2).

- **Content-hash versions** (`meta.schema_version`, `meta.guideline_version`,
  `ops.policy_version`, `ops.method`, `ops.method_config`, `kb.document`, `kb.rendition`):
  `.on_conflict_do_update(index_elements=[…], set_={"content_hash": stmt.excluded.content_hash}).returning(t.c.id)`
  returns the id whether or not the row is new.
  - Cost: a write to the existing row. Negligible for these low-volume tables.
  - On PostgreSQL 18, `RETURNING new.id, (old.id IS NULL) AS created` also tells `ci project init`
    what it created (Doc, release notes "OLD/NEW support to RETURNING"). In SQLAlchemy this needs
    `literal_column("old.id IS NULL")` or `text()`; no 2.1 construct for `old`/`new` was found.
- **High-volume keys** (`kb.span`, deduplicated by `(rendition_id, start_offset, end_offset)`): one statement.

  ```sql
  INSERT … SELECT FROM unnest(%s::int8[], %s::int4[], %s::int4[], …)
  ON CONFLICT DO NOTHING
  RETURNING …
  ```

  Then one SELECT for the rows that already existed. Under READ COMMITTED, a concurrent writer of
  the same span can make that lookup miss once, so re-query any keys still missing (Inf).
- **Per-run materialization** (`kb.entity`, `kb.claim`, links). Consolidation rebuilds each pass
  (D5 §1). The simplest correct write is set-based `DELETE … WHERE run_id = :run`, children first,
  then the bulk write of §3 in one transaction. **PG17 `MERGE … WHEN NOT MATCHED BY SOURCE … RETURNING merge_action()`**
  is the option if ids must stay stable across passes. No MERGE construct was found in
  SQLAlchemy 2.1, so it would use `text()`.

**`insertmanyvalues`** (Doc and Src: `use_insertmanyvalues = True`; sentinel options
`ANY_AUTOINCREMENT | USE_INSERT_FROM_SELECT`).

- `conn.execute(insert(t).returning(t.c.id, t.c.key), list_of_dicts)` becomes batched multi-VALUES
  INSERTs, 1,000 rows per page by default (`insertmanyvalues_page_size`), with RETURNING.
- `returning(..., sort_by_parameter_order=True)` correlates the returned rows with the input
  rows. It is not needed when `key` comes back.
- This is the right path for 10²–10⁴ rows that need their ids back. COPY (§3) is the path for
  10⁵ observations.

**When to drop to psycopg directly:**

- COPY;
- the `LISTEN` connection;
- `unnest`-array statements, which are easier to write as `text()`;
- the BM25 operator, which needs no special call: `segment.c.text.op("<@>", return_type=Float)(func.to_bm25query(bindparam("q"), literal_column("'kb.segment_bm25'")))`
  works in Core.

Within one transaction, take the driver connection with `sa_conn.connection.driver_connection`
(Doc). It is the same session and transaction, so a COPY on it commits with SQLAlchemy's
`engine.begin()`. Never call `commit()` on the raw connection.

**PostgreSQL index options from metadata** (Src, `visit_create_index`):

- `Index("segment_bm25", segment.c.text, postgresql_using="bm25", postgresql_with={"text_config": "'english'"})`.
  **`WITH` values are rendered verbatim**, so pass the quotes inside the string.
- `Index("embedding_hnsw", t.c.vec, postgresql_using="hnsw", postgresql_ops={"vec": "halfvec_cosine_ops"}, postgresql_with={"m": 16, "ef_construction": 64})`.
- The `USING` validator accepts any word (`IDX_USING`, l. 2002), so `bm25` and `hnsw` pass.
- A partial index takes `postgresql_where=`. An operator class on an expression needs a labelled
  expression in `postgresql_ops`; otherwise Alembic warns and skips the comparison (Src, Alembic
  `compare_indexes`).

**Version notes.**

- 2.1 defaults `postgresql://` to psycopg 3; write `postgresql+psycopg://` explicitly.
- 2.1 drops `greenlet` from the default install, so an async engine would need `sqlalchemy[asyncio]`.
- 2.1.5 supports PostgreSQL 18 virtual generated columns: `Computed(..., persisted=None)` renders
  no keyword, which means VIRTUAL on 18 (Src l. 3052–3074).
- `func.uuidv7(monotonic=True)` is new in 2.1 (Src l. 116–151). It is not recommended here
  (see §7).

## 3. psycopg 3.3: bulk writes, JSONB, transactions

**Binary COPY for observations, claims and evidence** (Doc and Src). This is the D6 §3.2 task
write.

```python
with engine.begin() as sa_conn:                      # one transaction: fence, rows, status, notify
    fenced = sa_conn.execute(update(task).where(task.c.id == tid, task.c.status == "running",
                 task.c.attempt == attempt).values(status=outcome, cost=cost,
                 finished_at=func.now(), lease_until=None, claimed_by=None).returning(task.c.id)).first()
    if fenced is None:
        raise LeaseLost                              # rolls everything back
    raw = sa_conn.connection.driver_connection       # same session, same transaction
    with raw.cursor() as cur, cur.copy(
        "COPY kb.observation (task_id, ordinal, kind, rendition_id, segment_id, span_id,"
        " payload, score, outcome) FROM STDIN (FORMAT BINARY)") as cp:
        cp.set_types(["int8", "int4", "text", "int8", "int8", "int8", "jsonb", "float4", "text"])
        for row in rows:
            cp.write_row(row)                        # payload may be a plain dict here
```

- **`set_types` is mandatory in binary mode.** PostgreSQL applies no cast rules to binary COPY
  (Doc, `copy.rst`). A Python int defaults to the narrowest integer type that fits, and a Python
  float defaults to float8, which fails against a `real` column. The D3 mapping is:
  - `bigint` → `int8`, `integer` → `int4`, `smallint` → `int2` (`ops.run.phase`);
  - `real` → `float4`, `double precision` → `float8`;
  - `text[]` → `text[]`, `halfvec` → `halfvec` (needs `register_vector`).
- **JSONB in COPY.** With `jsonb` declared, `JsonbBinaryDumper` dumps any object, not only
  `Jsonb` wrappers (Src, `_copy_base.py` l. 113–138, `_py_transformer.py` l. 164–167,
  `json.py` l. 236–243). Outside COPY, a dict parameter needs `Jsonb(obj)`: the default dumpers
  are registered only for `Json` and `Jsonb` (Src, `json.py` l. 303–314).
- **Never pass `Jsonb(None)` for an absent value.** It stores JSON `null`, which is not SQL NULL
  and defeats D3's `CHECK ((object_entity_id IS NULL) <> (object_value IS NULL))`.
- **Identity values.** COPY "will always write the column values provided … like `OVERRIDING SYSTEM VALUE`"
  (Doc, `sql-copy.html`; also `sql-createtable.html`).
  - Leave `id` out of the column list and it is generated. This is why D3 §6.3's `mention_ref` is
    `{task, ordinal}`, and that design already fits COPY.
  - Consolidation can **pre-allocate** ids with `SELECT nextval(pg_get_serial_sequence('kb.claim','id')) FROM generate_series(1, %s)`.
    It can then COPY claims and their `claim_evidence`, `claim_support` and `claim_link` rows in
    one pass, with no lookup from key back to id. Gaps on rollback are harmless.
- **COPY semantics.** CHECK constraints and triggers fire, including foreign-key triggers (Doc).
  `ON_ERROR ignore` and PG18's `REJECT_LIMIT` work only with text or CSV format (Doc). That is
  correct here: a bad row should abort the task's transaction.
- **Not FREEZE.** It applies only to a table created or truncated in the same subtransaction, and it
  breaks MVCC visibility (Doc).

**JSON serialization policy.**

- `set_json_dumps(fn, context)` and `set_json_loads(fn, context)` set the serializer at global,
  connection or cursor scope (Src).
- **Pitfall** (Src, SQLAlchemy `psycopg.py` l. 424–461). `create_engine(json_serializer=…)`
  reaches psycopg only through the adapters map that the dialect passes when *it* opens
  connections. When psycopg-pool creates the connections (§5), set the dumps in the pool's
  `configure` callback instead.
- jsonb does not keep key order or the text form of numbers. **Never derive keys or digests from
  `jsonb::text` or from a SQL generated column.** D1 §10.1's `canonical_json` stays in Python, and
  stored jsonb is only data.

**Transaction scoping.**

- `engine.begin()` (or `conn.transaction()` in raw psycopg) makes "task, its observations, its
  status change" one commit.
- Do the fencing `UPDATE` first, so a lost lease fails before any rows are copied (§4).
- A nested `conn.begin_nested()` or `transaction()` is a SAVEPOINT. Use it for an optional sub-step
  that may raise, such as re-querying a span after a race.
- `pg_notify(...)` inside the transaction is delivered only if the transaction commits (Doc).
- Classify retryable errors by SQLSTATE through `exc.orig`: `psycopg.errors.SerializationFailure`
  (40001), `DeadlockDetected` (40P01), and `OperationalError` for a lost connection. A
  `UniqueViolation` on `(task_id, ordinal)` is a fencing bug, not a transient failure.

**Pipeline mode: not recommended.** It is labelled experimental at 3.3, cannot carry COPY, and pays
off with network round trips, whereas here the server is on a local socket (overview §5).
`executemany` already pipelines automatically (Doc).

**Row factories.**

- On raw psycopg paths, `class_row(PydanticModel)` builds models directly, and `scalar_row` serves
  counts.
- **Do not set a connection-level `row_factory` on pooled connections that SQLAlchemy also uses.**
  SQLAlchemy expects tuple rows. Set factories per cursor.
- For SQLAlchemy results, use `Model.model_validate(row._mapping)` or a `TypeAdapter` over
  `.mappings()`.

**Prepared statements.** Automatic preparation (threshold 5) suits the repeated claim and queue
statements. With pg_textsearch, use the explicit `to_bm25query(…, 'index')` form: the implicit form
breaks under bound parameters (§6).

**Python 3.14 template strings** (`conn.execute(t"…")`; SQLAlchemy's `tstring()`) are available on
the target interpreter. They are optional for the few hand-written statements.

## 4. The work queue (D6 §3)

**Claim statement** (Doc: SKIP LOCKED "can be used to avoid lock contention with multiple
consumers accessing a queue-like table"):

```sql
WITH picked AS (
  SELECT id FROM ops.task
  WHERE run_id = $1 AND stage = $2 AND method_config_id = $3
    AND (status = 'pending' OR (status = 'running' AND lease_until < now()))
  ORDER BY priority DESC, id
  LIMIT $4
  FOR UPDATE SKIP LOCKED)
UPDATE ops.task t
SET status = 'running', claimed_by = $5, attempt = t.attempt + 1,
    lease_until = now() + interval '5 minutes', started_at = coalesce(t.started_at, now())
FROM picked WHERE t.id = picked.id
RETURNING t.id, t.unit_type, t.unit_id, t.unit_key, t.attempt;
```

The claim commits at once. The method then runs **without an open transaction**, and the results
are written in a second transaction (§3).

- **Fencing.** `attempt`, incremented at claim, is the fencing token. Every terminal write and every
  renewal is conditioned on `(id, attempt, status = 'running')`. A worker whose lease expired and
  whose task was re-claimed matches zero rows and rolls back.
- **No separate reaper.** Lease expiry is evaluated inside the claim (the `OR` branch above), so a
  dead worker's tasks return through normal claiming (L-S1).
- **Renewal.** A heartbeat thread runs, in its own short transaction on its own connection:

  ```sql
  UPDATE ops.task SET lease_until = now() + interval '5 minutes'
  WHERE id = ANY($1) AND status = 'running' AND claimed_by = $2;
  ```
- **Retry.** After a transient failure, the worker writes:

  ```sql
  SET status = CASE WHEN attempt < 3 THEN 'pending' ELSE 'failed' END, error = $err,
      claimed_by = NULL, lease_until = NULL
  WHERE id = $1 AND attempt = $2 AND status = 'running'
  ```

  That gives D6's "up to twice". A deterministic failure is written `failed` directly. An expired
  lease also counts as an attempt; halving the batch after an out-of-memory error is the worker's
  own business.
- **Read Committed caveats** (Doc). A row re-checked after waiting may fail the `WHERE`, so a claim
  can return fewer than `LIMIT` rows. With `ORDER BY` plus a locking clause, rows can come back out
  of order. Both are harmless here.
- **Agent tasks.** `queue_next` uses the same statement on
  `status = 'awaiting_agent' AND (lease_until IS NULL OR lease_until < now())`. It sets
  `claimed_by = 'agent:<session>'` and a 30-minute `lease_until`, **leaving the status at
  `awaiting_agent`**. Expiry then needs no action, and `release` just clears the lease. Golden-pass
  tasks (phase 0 plan §3 item 4) lease the same way.
  - For D8 §3's "units of one page" rule, pick the head task, then lock same-rendition siblings
    with a second `SKIP LOCKED` query in the same transaction.
  - A nullable `rendition_id` on `ops.task` would make that grouping and slice scoping one index
    lookup (optional).

**Indexes** (replacing D3's `task_queue`, whose leading `status` column does not match the claim's
`run_id, stage, method_config_id` predicate):

```sql
CREATE INDEX task_pending ON ops.task (run_id, stage, method_config_id, priority DESC, id) WHERE status = 'pending';
CREATE INDEX task_lease   ON ops.task (lease_until) WHERE status = 'running';
CREATE INDEX task_agent   ON ops.task (run_id, priority DESC, id) WHERE status = 'awaiting_agent';
CREATE INDEX task_cache   ON ops.task (method_config_id, input_hash) INCLUDE (id) WHERE status IN ('done','empty');
```

- The partial indexes stay small because terminal tasks leave them.
- `task_run (run_id, stage)` serves the stage-barrier count. Adding `status` would make that count
  index-only.

**Reuse at task creation (D6 §4) in one statement:**

```sql
INSERT INTO ops.task (...)
SELECT ...
FROM unnest(...) u
LEFT JOIN LATERAL (
  SELECT id FROM ops.task
  WHERE method_config_id = u.cfg AND input_hash = u.h AND status IN ('done','empty')
  ORDER BY id DESC LIMIT 1) c ON true
```

Status comes out as `'reused'` with `reused_task_id = c.id` where a match exists, `'pending'`
otherwise. `task_cache` serves the lateral lookup (Inf).

**LISTEN/NOTIFY: wake-up hints, never state** (Doc, `sql-notify.html`):

- Notifications are delivered only at commit.
- Identical channel and payload pairs within one transaction fold into one.
- Notifications from different transactions arrive in commit order.
- Payloads must be under 8,000 bytes.
- A full queue (about 8 GB) makes notifying transactions fail at commit.
- A listener that sits in a long transaction blocks queue cleanup.

How to use them:

- **One dedicated autocommit connection per listener**, outside any pool. Pool resets and
  `max_lifetime` would drop the `LISTEN`, and a returned connection would carry it to other
  borrowers (pool overview §11.5).
- psycopg's `conn.notifies(timeout=…, stop_after=…)` generator has existed since 3.2 (Src,
  `connection.py` l. 372–383). Do not mix it with notify handlers on one connection: psycopg warns
  that this is unreliable (Src).
- **To avoid lost wake-ups:** `LISTEN` first, then check the table, then wait with a timeout
  (30–60 s), and re-check after every wake or timeout. Re-`LISTEN` after a reconnect.
  Notifications sent while nobody listens are lost, so the table count stays the authority.
- Channels: `cs_agent_task_done` (payload `run_id`), sent by the MCP submission tools in their own
  transaction, and optionally `cs_task_ready`, sent by the orchestrator after it creates tasks.
- Committing transactions that `NOTIFY` are serialized by a database-wide lock. That is irrelevant
  at one operator's scale (a widely reported behaviour, not in the page).

**OPEN-D8-1: two processes** (L-S7).

- Nothing in the store needs one process. The MCP server is request-driven, so it **never needs
  to `LISTEN`**: it reads the table on each tool call and `NOTIFY`s when it commits a submission.
  Only the orchestrator's `agent_mode: wait` loop listens.
- The deciding factor is lifetime. A stdio MCP server is started by, and dies with, a Claude Code
  session. A run waiting at its barrier must outlive sessions: "the queue persists, so the agent
  works a run's tasks across as many sessions as it takes" (D6 §7.4, working tree; ADR-0015).
- The only coordination channel is the database, through the lease columns and NOTIFY.
- The one-process alternative is technically possible: an `AsyncConnection.notifies()` loop
  alongside FastMCP on one event loop. But it would tie a run's lifetime to a session.

**Considered and rejected:**

- **pgmq** (PostgreSQL overview §12.4). It would split the queue from the task record, which is a
  second authority over task state, against ADR-0015 and D6 §1.
- **Session advisory locks as leases.** They release instantly when a worker dies, but they are
  tied to one connection, survive pooled reuse, cannot express the 30-minute agent lease and leave
  no queryable state.

## 5. psycopg-pool for the orchestrator, workers and the MCP stdio server

**One owner of connections per process: a psycopg-pool `ConnectionPool`. SQLAlchemy borrows from
it.**

```python
pool = ConnectionPool(conninfo, min_size=1, max_size=4, max_idle=300, close_returns=True,
                      check=ConnectionPool.check_connection, configure=configure,
                      kwargs={"application_name": "cs-orchestrator"}, open=False)
pool.open(wait=True, timeout=15)
engine = create_engine("postgresql+psycopg://", creator=pool.getconn, poolclass=NullPool)
```

- This is the documented integration since pool 3.3.0: `close_returns=True` with SQLAlchemy's
  `NullPool` (pool overview §10).
- The raw paths share the pool's configuration: COPY through `driver_connection`, and `class_row`
  reads.
- `configure(conn)` runs once per physical connection. It must leave the connection idle; pool
  3.3.3 discards connections that `configure` leaves in a transaction (Src, `pool.py`
  l. 634–639). It does three things:
  - `set_json_dumps` and `set_json_loads` (§3);
  - from phase 1, `pgvector.psycopg.register_vector(conn)`. Its `TypeInfo.fetch` runs inside
    `conn.transaction()` and leaves the connection idle (Src, `_typeinfo.py` l. 95–108), so it is
    safe in `configure`;
  - nothing session-global beyond that.
- **Per-checkout `check=ConnectionPool.check_connection`** protects long-idle processes after a
  server restart: the MCP server between tool calls, the orchestrator waiting for the agent.
  **Do not schedule `pool.check()` periodically on 3.3.3:** it can grow the pool, which is fixed
  only in the unreleased 3.3.4 (pool overview §12.2).
- **Session state.** Use `SET LOCAL` inside the transaction (for example `hnsw.ef_search`,
  `statement_timeout` for MCP inspection tools), never session `SET` on pooled connections.
  Pooled connections keep session state across borrowers (pool overview §3.3).

**Sizing** (qualitative; `max_connections` is 100, Obs):

| Process | Pool | Extra connections |
|---|---|---|
| Orchestrator | `min 1, max 4` | 1 dedicated autocommit `LISTEN` |
| `cpu` workers (process pool) | each process opens its own `min 1, max 1` in the pool initializer. Connections are not process-safe (Doc), and Python 3.14's Linux default start method is `forkserver`, so nothing is inherited, but each process still has to open its own | — |
| `encoder` worker | `min 1, max 2` (completion plus heartbeat) | — |
| `llm` worker (async) | `AsyncConnectionPool(min 1, max 2, open=False)` then `await pool.open()`; opening in the constructor is deprecated for async pools (Doc). DB writes are serial; the 16 in-flight requests are HTTP, not database work | — |
| MCP stdio server | `min 1, max 3`, synchronous | — |

- The total is about 20 connections even with 8 CPU workers. Neither the pool limits nor
  `max_connections` is the constraint.
- `timeout` (30 s, the acquisition deadline) and `max_waiting` (0, unbounded) can stay at their
  defaults. `timeout` is not a query timeout (Doc).
- Logs go through the `psycopg.pool` logger. For the stdio server, logging must go to stderr,
  never stdout (Inf; the transport detail belongs to the interfaces group).

**MCP server: synchronous store functions.**

- D8 §1 requires that "the MCP server and the CLI call the same application functions". One
  synchronous `core/db` layer, called from FastMCP tools through a worker thread, avoids a second,
  async copy of every store function. That copy would also need `sqlalchemy[asyncio]` with
  `greenlet`.
- An async engine stays possible through `create_async_engine(…, async_creator=apool.getconn, poolclass=NullPool)`
  if the interfaces group needs it.

## 6. pg_textsearch BM25 (OPEN-D3-1) and pgvector (OPEN-D3-2, phase 1)

### pg_textsearch 1.5.1: *re-check against the overview*

**Index.** D3's statement is valid syntax for 1.5.1:

```sql
CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english');
```

- `text_config` is required, and qualified names such as `'pg_catalog.english'` are accepted
  (Doc README; Src `test/sql/text_config.sql`). `english` is installed (Obs).
- `k1` defaults to 1.2 (range 0.1–10) and `b` to 0.75 (range 0–1). Defaults are fine.
- The operator class is `text_bm25_ops`, the default for `text` (Src, install SQL l. 197–201).
- Expression and partial indexes are supported (Doc README).

**Query** (Doc README; Src):

```sql
SELECT s.id, s.key, -(s.text <@> to_bm25query($1, 'kb.segment_bm25')) AS bm25
FROM kb.segment s
WHERE s.rendition_id = ANY($2)
ORDER BY s.text <@> to_bm25query($1, 'kb.segment_bm25')
LIMIT $3;
```

- `<@>` returns **negative** BM25 scores, so ascending order ranks best first.
- **Always name the index.** The implicit `text <@> 'terms'` is rewritten only when the right-hand
  side is a `Const` (Src, `hooks.c` l. 785–810). psycopg and SQLAlchemy send a bound parameter,
  which is a `Param`, so the implicit form fails. Upstream tests confirm that
  `to_bm25query($1, 'idx')` works in prepared statements (Src, `test/sql/implicit.sql`
  l. 118–154). Schema-qualified names resolve (Src, `resolve.c` l. 69; `test/sql/schema.sql`),
  and partial indexes always need the explicit name (Doc).
- **Filtering.**
  - If PostgreSQL chooses the ordered BM25 scan, other conditions are post-filters, and the scan
    "automatically grow[s] its internal scoring batch until the LIMIT is filled".
  - With a selective b-tree prefilter, PostgreSQL may instead score the qualifying rows standalone
    and sort them. Standalone scoring uses the index's corpus statistics, so the ranking agrees (Doc).
  - On small tables the planner may prefer standalone scoring over a sequential scan. S6 should
    record `EXPLAIN` with and without `SET LOCAL enable_seqscan = off` (Doc).
- **Boolean and phrase filters** (since 1.5.0): `WHERE s.text @@ to_tsquery('english', 'a <-> b')`
  goes through the BM25 index. The session's `default_text_search_config` must match the index
  configuration. It does on this server (Obs), but a changed setting under a cached generic plan
  needs `DEALLOCATE` (Doc). Combining it with ranking evaluates the filter, scores and sorts, and
  works best when the filter is selective (Doc).
- **Limits** (Doc):
  - lexemes over 2,047 bytes are ignored;
  - inputs over 256 KB are split before tokenizing;
  - on partitioned tables, statistics are per partition;
  - `PREPARE TRANSACTION` is unsupported after creating a BM25 index (irrelevant at
    `max_prepared_transactions = 0`);
  - RLS term-frequency leakage (irrelevant here);
  - standalone scoring is `PARALLEL UNSAFE` (install SQL comment);
  - LWLock tranche ids 1001–1012;
  - PostgreSQL 17 and 18 only.
- **Maintenance** (Doc). The default `compaction = inline` needs no scheduler. Create the index
  after initial loads where possible; for D3 it is created by 0001 on an empty table and maintained
  incrementally, which suits this volume (Inf). `REINDEX` exists for fragmentation after heavy
  updates. The `bm25_*` maintenance functions need index ownership; `paul` owns the index.
- **Corpus statistics cover every indexed row** (Doc). D1 §3.2 segments nest (document → section →
  unit → paragraph → sentence), so an index over all kinds counts each token about five times.
  Queries would return a paragraph, its unit, its section and its document as competing hits.
  Index only a **non-overlapping block level** with a partial index (L-S3).
- **OPEN-D3-3 is settled by this mechanism.** A BM25 index, or an expression index, can only use
  columns of the same row, and PostgreSQL 18 generated columns "cannot … reference anything other
  than the current row" (Doc). The searchable text must therefore be stored on `kb.segment`; no
  generated substring of `kb.rendition.canonical_text` can feed the index. The cost is about five
  times canonical size at most, a few MB for the first pass (Inf; S6 step 8 measures it).
- **Alias search for D8 `find`:** `pg_trgm` is a *trusted* extension (Obs), so `paul` can create
  it. A GIN trigram index on `kb.entity_alias.normalized` gives fuzzy alias hits in SQL. This is
  optional; M14 uses rapidfuzz in Python.

### pgvector 0.8.7 / pgvector-python 0.5.1 (primary source: `docs/libraries/pgevector.md`)

- **Limits** (Doc, README v0.8.7 l. 252–253 and 374–375; overview §2.1). HNSW indexes `halfvec`
  up to **4,000 dimensions**, and `vector` only up to 2,000. Both S7 candidates, 1024 and
  Matryoshka-truncated 2048, are indexable as `halfvec`. The 8B model's native 4,096 dimensions
  are not; that would need truncation, `binary_quantize` (≤ 64,000 bits) with re-ranking, or
  subvector indexing (overview §6).
- **Index.** `USING hnsw (vec halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)` uses the
  defaults. Queries use `ORDER BY vec <=> $1 LIMIT k`, ascending distance with a `LIMIT`. A
  transformed similarity in `ORDER BY` defeats the index; compute `1 - distance` outside it
  (overview §8.3). If vectors are L2-normalized, `halfvec_ip_ops` with `<#>` is equivalent (Inf).
- **Filters are applied after the ANN scan** (Doc, README l. 450: "If a condition matches 10% of
  rows … only 4 rows will match on average"). `kb.embedding` mixes target types (segment, entity,
  alias) and model configurations in one index. Use **partial HNSW indexes per `target_type`**,
  and per model configuration if more than one is live (README l. 456), plus
  `SET LOCAL hnsw.iterative_scan = relaxed_order` with the materialized-CTE re-sort and its
  `distance + 0` note for PG17+ (README l. 500–515).
- **Dimension handling.** A fixed `halfvec(n)`, once S7 chooses n, is simplest. The undimensioned
  alternative, `halfvec` with `CAST`-expression partial indexes per model configuration
  (README l. 831–850), keeps one table across model changes at the cost of casts in every query.
- **Zero and NULL vectors** are not indexed for cosine distance (Doc, README l. 937), so reject
  zero vectors on write.
- **Writes.** Binary COPY with `register_vector` in the pool's `configure`, `set_types([..., 'halfvec'])`
  and `HalfVector`. Build the index after bulk loads and then run `ANALYZE` (overview §8.1).
  HNSW builds go fastest when the graph fits `maintenance_work_mem` (README l. 291); 16 GB here
  is ample.
- **Reads through SQLAlchemy.** `HALFVEC(n)` with `.cosine_distance(q)` renders `<=>`. Since 0.5.0,
  SQLAlchemy results are Python lists, while the raw driver returns `HalfVector` (overview §2.4).
- **Recall check.** Exact baseline via `SET LOCAL enable_indexscan = off` (overview §8.3).
- **Contract note.** Embeddings of entities and aliases keyed by run-scoped `target_id` with no
  foreign key leave orphans when non-promoted runs are deleted, and are recomputed per run
  (L-S6, phase 1).

## 7. PostgreSQL 18 features, and D3 statements that fail or are suboptimal

**PostgreSQL 18 (and 17) features worth using:**

- **`RETURNING old/new`** (18). Tells get-or-create whether the row was created, and lets lease
  transitions report the previous status (§2).
- **B-tree skip scan** (18). Composite `(run_id, x)` indexes become usable for `x = …` when
  `run_id` has few distinct values (Doc). That serves foreign-key checks on `subject_id`,
  `object_entity_id` and `statement_id` without extra single-column indexes. The planner decides
  (Inf).
- **Asynchronous I/O** (18). `io_method = io_uring` is already set on 5432 (Obs). It helps
  sequential and bitmap scans and vacuum; D3 needs no DDL for it.
- **`JSON_TABLE` / SQL/JSON** (17). Metrics over observation payloads in SQL, for example labels
  and scores from `classification` payloads for D6 §6, without moving payloads into Python.
- **`MERGE … WHEN NOT MATCHED BY SOURCE … RETURNING merge_action()`** (17). Optional sync of a
  run's claim set (§2).
- **`EXPLAIN ANALYZE` includes `BUFFERS` by default** (18). Useful for S6's timing records.

**PostgreSQL 18 features not to use:**

- **`uuidv7()`** for identity or keys: it is time-based, which breaks D9 §3's determinism. D1
  §10.1 keys stay content hashes. Storing a 128-bit key as `uuid` would halve key size but cost
  readability; at 10⁵ rows that is not worth it.
- **Virtual generated columns for keys or segment text**: canonicalization lives in Python, and a
  generated column cannot reference other tables. A virtual column also cannot use user-defined
  types or functions such as `halfvec` (Doc).
- **`NOT ENFORCED` constraints and temporal `WITHOUT OVERLAPS`**: no consumer.
- **COPY `ON_ERROR` / `REJECT_LIMIT`**: text and CSV only, and here bad rows should abort.

**D3 statements that would fail or are suboptimal:**

| # | Statement | Finding | Strength |
|---|---|---|---|
| F1 | `CREATE EXTENSION IF NOT EXISTS vector; … pg_textsearch;` | Fails as `paul` (untrusted extensions) and fails for `pg_textsearch` without preloading; see §0. Make extensions a provisioning step that 0001 only asserts (L-S5) | Obs + Doc |
| F2 | Run deletion "whole (cascade)" (D3 §8) | `ops.task.run_id` is `NOT NULL REFERENCES ops.run` with no cascade, and so are `kb.observation.task_id`, `ops.intervention.run_id` and `ops.experiment.*_run_id`. Deleting an `ops.run` row fails while its tasks exist, yet D6 §4 requires keeping the tasks that kept runs reuse. Delete the run's materialization and keep the `ops.run` row (L-S2) | Inf from the DDL |
| F3 | `task_queue (status, priority DESC, id) WHERE status IN (…)` | Does not serve the claim predicate `(run_id, stage, method_config_id)`, and nothing serves lease expiry. Replace with §4's indexes (L-S1) | Inf |
| F4 | `claim_qual … gin (qualifiers jsonb_path_ops)` | Does not serve D3 §9's `@? '$.param_values.variance'`, which has no `== constant`, and `jsonb_path_ops` cannot answer key-existence (Doc). Keep it only if a `@>` consumer exists; otherwise drop it, or switch to default `jsonb_ops` if key-existence queries matter (L-S4) | Doc |
| F5 | `observation_payload … gin (payload jsonb_path_ops)` | No D3 §9 or D6 consumer queries payloads by containment. It taxes every COPY of 10⁵ rows. D3 §1's own rule is "GIN where queried"; defer it (L-S4) | Inf |
| F6 | Foreign-key cascades without referencing-side indexes | Every deleted parent row makes PostgreSQL look up referencing rows. `kb.claim_link.to_claim_id` (cascade from claim), `eval.alignment.run_id`, `eval.result.run_id` (cascade from run), `kb.observation.rendition_id` and `kb.span.segment_id` (restrict checks) have no index. Add those indexes, or delete children set-based before parents (§2) | Inf (standard PostgreSQL behaviour) |
| F7 | Unnamed CHECK, UNIQUE and FK constraints | Valid, but unnamed constraints are invisible to Alembic's name-based handling. Name every one through the naming convention (§1) | Doc (Alembic) |
| F8 | `segment_bm25` over all segment kinds | Overlapping hits and inflated document frequencies; use a partial index on block kinds (L-S3) | Doc (statistics cover all indexed rows) + Inf |
| F9 | `ops.task.unit_type` CHECK; `ops.run.kind` CHECK; `ops.task.run_id NOT NULL` | Phase 0 plan §3 item 4 makes golden passes queue tasks (`golden.pass`, leased by `golden_next`). The `unit_type` list has no golden-unit value, and no run kind hosts golden authoring. **For the design authority to reconcile**: a contract gap, not a library question | Inf from the working tree |
| F10 | `kb.embedding (target_type, target_id)` (phase 1) | Polymorphic with no foreign key: orphans after run deletion; run-scoped ids force re-embedding per run (L-S6) | Inf |
| F11 | Column names `values`, `extract`, `text`, `range`, `type` | Valid. `values` and `extract` are column-name keywords ("cannot be function or type name") and are allowed as column names (Obs `pg_get_keywords()`); SQLAlchemy quotes as needed. No change | Obs |

## 8. What library features make unnecessary or simpler in D3 and D6

1. **No reaper process.** Lease expiry is part of the claim (`OR status = 'running' AND lease_until < now()`).
   Agent leases expire implicitly because the status stays `awaiting_agent` (§4).
2. **No key-to-id lookups in consolidation.** COPY honours supplied identity values, so pre-allocated
   `nextval` ids let parent and child rows go in one pass (§3).
3. **Reuse resolution is a single `INSERT … SELECT … LEFT JOIN LATERAL`** at task creation (§4).
4. **Get-or-create needs no SELECT-then-INSERT.** `insert().on_conflict_do_update().returning()`
   does it, with PostgreSQL 18's `old` to report creation (§2).
5. **Observation ids never need to be known in advance.** D3 §6.3's `{task, ordinal}` reference
   already fits COPY, so no change.
6. **One pool configuration** (`configure`) carries the JSON serialization policy and the vector
   adapters for both SQLAlchemy and raw psycopg (§5).
7. **OPEN-D3-3 closes without a spike decision.** BM25 needs the text on the same row (§6).
8. **The test database needs no migration replay per session.** Clone a migrated template (§1).

## 9. Library proposals

The numbers are provisional, prefixed `S` for this store note; the coordinator assigns final
`L-nn`.

> Library proposal (L-S1): **Queue indexes and lease fencing.** D3 §4 `ops.task` and D6 §3.2.
> Replace `task_queue` with three partial indexes: `task_pending` on
> `(run_id, stage, method_config_id, priority DESC, id) WHERE status = 'pending'`; `task_lease` on
> `(lease_until) WHERE status = 'running'`; and `task_agent`. Add `INCLUDE (id)` to `task_cache`.
> Define `attempt` as incremented at claim and use it as the fencing token on every renewal and
> terminal write. Evaluate lease expiry inside the claim, with no reaper. Agent and golden leases
> keep status `awaiting_agent` and set `claimed_by` and `lease_until`; `release` clears them.
> *Why:* the claim predicate is indexed, a dead or slow worker cannot commit stale results, and
> one fewer moving part.

> Library proposal (L-S2): **Run deletion removes the materialization, not the `ops.run` row.**
> D3 §8 and D6 §4. Deleting a run deletes its entities, claims, links, alignments, results and
> measurements set-based, and marks the run deleted (a status value or `deleted_at`). Its tasks
> and observations stay while any kept run reuses them. *Why:* `ops.task.run_id` and
> `kb.observation.task_id` must keep resolving for reused work. The current "delete the run row
> with cascade" contradicts the foreign keys.

> Library proposal (L-S3): **BM25 over a non-overlapping block level.** D3 §5 and OPEN-D3-1. Use
> `CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english') WHERE kind IN (<block kinds: paragraph, heading, list_item, caption, table_cell, footnote, math_display; the design authority chooses>)`.
> Every query names the index: `text <@> to_bm25query($q, 'kb.segment_bm25')`. *Why:* pg_textsearch
> statistics cover every indexed row, and nested kinds otherwise multiply term frequencies and
> return each passage at several levels. Partial indexes need the explicit name, and the store
> uses it anyway because bound parameters defeat the implicit form. *Re-check against the
> overview.*

> Library proposal (L-S4): **JSONB and foreign-key indexes by consumer.** D3 §5. Defer
> `observation_payload` until a containment query exists. Keep `claim_qual` (`jsonb_path_ops`)
> only for `@>` queries; D3 §9's `@?` existence query is carried by `claim_pred`. Add
> referencing-side indexes for the cascades: `kb.claim_link (to_claim_id)`,
> `eval.alignment (run_id)`, `eval.result (run_id)`, `kb.observation (rendition_id)`,
> `kb.span (segment_id)`.

> Library proposal (L-S5): **Extensions are provisioned, not migrated.** D3 §3 and D9 §4. The
> operator preloads `pg_textsearch` and creates `cs_template` with both extensions; `ci db init`
> and test fixtures create databases from it. Migration 0001 keeps
> `CREATE EXTENSION IF NOT EXISTS` as an assertion, its downgrade leaves the extensions in place,
> and `alembic_version` stays in `public`. *Why:* neither extension is trusted, `paul` is not a
> superuser, and pg_textsearch must be preloaded (§0).

> Library proposal (L-S6, phase 1): **Embeddings keyed by stable target keys, indexed per target
> type.** D3 §5 `kb.embedding`. Store `target_key` (segment, entity or alias key) instead of the
> run-scoped `target_id`. Use one partial HNSW index per `target_type`, and per model
> configuration if several are live. Queries use `SET LOCAL hnsw.iterative_scan = relaxed_order`.
> *Why:* entity keys are stable across runs (D1 §10.1), so embeddings survive run deletion and are
> not recomputed per run. ANN filtering is applied after the scan.

> Library proposal (L-S7): **OPEN-D8-1: two processes, coordinated by the database.** D8 §2 and
> D6 §2. The MCP server reads the queue per call and `NOTIFY`s `cs_agent_task_done` inside the
> submission transaction. The orchestrator alone `LISTEN`s, on a dedicated autocommit connection,
> with a timeout-and-recheck loop. *Why:* a stdio server's life is a Claude Code session's, while
> a waiting run spans sessions (D6 §7.4). NOTIFY is commit-transactional, so the wake-up is never
> earlier than the data.

## 10. Uncertainties and what S6 or P0.3 should confirm

- **Not executed anywhere:** D3's DDL, the BM25 and HNSW syntax on this server, and every
  query plan. S6 remains the test, and it is **blocked** on §0 items 1–2 (and constrained by
  item 3).
- **pg_textsearch planner choices:** BM25 index scan versus prefilter with standalone scoring on
  `kb.segment` at spike scale; behaviour of a partial BM25 index with `rendition_id = ANY(...)`
  post-filters. Record `EXPLAIN (ANALYZE)` (Inf).
- **jsonb_path_ops and `@?`:** confirm with `EXPLAIN` that D3 §9's existence query uses `claim_pred`
  and not the GIN (Inf from Doc).
- **Template clone time and `pg_virtualenv` start-up:** not measured, so no numbers are claimed.
- **Pins:** SQLAlchemy 2.1.6 and Alembic 1.20.1 are now on PyPI (2026-10-28). D9 pins 2.1.5 and
  1.20.0, the overviews' versions. Whether to move is a `pin-check` decision; these releases were
  not evaluated here.
- **FastMCP:** whether its tools run synchronous functions in threads, and how a subagent's tool
  calls reach the session's MCP server. Both belong to the interfaces group; §5 assumes
  synchronous store functions called from tools.

## Files written

- `docs/design_review/evidence/2026-10-28_library-store/README.md` (this file). No other repository
  file was written. Upstream sources were cloned for reading into the session scratchpad, outside
  the repository.
