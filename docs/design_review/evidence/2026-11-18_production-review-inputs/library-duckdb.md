# DuckDB 2.0.0 capability brief for the design review

Prepared 2026-11-18 as library research for the production design review. The repository was
read-only. All probes ran on synthetic in-memory data from the scratch report directory, using the
project interpreter (`/home/paul/corpus-structure/.venv/bin/python`, CPython 3.14.10,
`duckdb==2.0.0`; the CLI reports `v2.0.0 (Cyanoptera) d54cbbe3df`). No project database or
project data was touched. Probes were run as stdin scripts, so no probe files were written.

**Evidence labels.** **D** means documented, in the 2.0 docs or the repository overview
`snap5/docs/libraries/analytical_infrastructure/duckdb_2.md`. **S** means observed in the installed
package source (`.venv/lib/python3.14/site-packages/duckdb/_relation.py`, `_expression.py`).
**P** means observed in a probe on 2026-11-18. **U** means unconfirmed.

**Reading coverage.** `duckdb_2.md` was read in full for §§1–16 and the addendum's §1, §2, §9 and
§11, and skimmed elsewhere (spatial, lakehouse, CLI). `duckdb_2_cli.md`, `pyarrow.md` and
`datafusion.md` were not read beyond their headings, because the questions did not need them. The
2.0 web pages for recursive CTEs and the postgres extension, and the DuckPGQ catalogue page, were
fetched.

**Project consumer context.** These are pointers only. DuckDB is imported in six modules under
`src/corpus_structure/`: `semantic/analytical_kernels.py`, `semantic/rich_relations.py`,
`semantic/artifact_identity.py`, `serve/companion_export.py`, `ingest/pdf_candidate_geometry.py`
and `ingest/pdf_stream_reconciliation.py`. I did not review how they use it.

## Summary

1. **The 2.0 relational API is a Python layer that renders SQL text internally.**
   `DuckDBPyRelation` lives in pure Python (`duckdb/_relation.py`, 4,647 lines). Every method
   emits SQL, which `rel.sql_query()` shows (S, P). Application code can still avoid writing SQL,
   but nearly every entry point also accepts raw strings, as conditions, orders, aggregates or
   `sql_expr`. A typed builder therefore has to refuse `str` itself to keep the "no SQL text"
   rule.
2. **Without SQL text you can express:** filter, project, join (inner, left, right, outer, full,
   semi, anti, cross, positional, natural and asof), aggregate and group_by, order and limit,
   distinct and `DISTINCT ON`, set operations, CASE, casts, `IN`, window functions with integer
   ROWS or RANGE frames, lag and lead, list functions with Python lambdas, struct and map
   construction, `* EXCLUDE`, pivot (explicit values), unpivot and `with_columns` (P).
3. **These still need SQL text:** recursive CTEs (plain and `USING KEY`), macros, `ATTACH`,
   `SET` and `INSTALL`, `NEAREST` and `LATERAL` joins, frames with interval or `GROUPS` units,
   and `read_parquet(schema=…)` (S, P).
4. **Set operations use bag semantics.** `union`, `except_` and `intersect` render as `UNION ALL`,
   `EXCEPT ALL` and `INTERSECT ALL` (S, P). This is a correctness trap for set-shaped model logic.
5. **Graph work: three routes work.**
   - A recursive CTE run through `rel.query(name, text)` terminated on a cyclic graph, and
     `USING KEY` produced correct shortest hop counts (P).
   - A recursion-free semi-naive loop built only from relations gave the same closure (P).
   - SQLGlot 30.27's DuckDB dialect builds and parses `WITH RECURSIVE … USING KEY` (P). It is the
     smallest typed route if recursion inside one statement is wanted.
   - DuckPGQ is a community research extension. Its 2.0.0 binary availability is unconfirmed (U).
6. **For PostgreSQL inputs, export Arrow from the application's own session; do not attach.** Use
   ADBC or psycopg binary `COPY` inside the application's own transaction. That keeps role,
   row-level security, snapshot and audit in PostgreSQL. `ATTACH … (TYPE postgres)` opens
   separate connections with separate credentials and pushes SQL text through
   `postgres_query`.
7. **Typing traps (P):**
   - Arrow dictionary columns arrive as `VARCHAR`, not `ENUM`.
   - `TIMESTAMPTZ` output takes the session time zone, which was `America/New_York` here, inherited
     from the machine.
   - JSON output loses its JSON-ness and comes back as a plain Arrow string.
   - A union of `BIGINT` with `VARCHAR` silently widens to `VARCHAR`.
   - `duckdb.enum_type` raises `NotImplementedException` at 2.0.0.
8. **Execution traps (P):**
   - One connection shared across threads raises `ResourceInUseException`. Use `cursor()` per
     thread.
   - An open Arrow reader blocks every other query on its connection.
   - A `RecordBatchReader` source can be read only once.
   - Relations re-execute on every read.
   - An in-memory database spills to `temp_directory='.tmp'`, relative to the working directory.

## A. Relational and expression API without SQL strings

Entry points (S): `con.from_arrow(obj)`, `con.read_parquet(path, *, file_row_number, filename,
hive_partitioning, union_by_name, compression)` and `con.table/view/values`.

- `from_arrow` accepts tables, batches, readers, datasets, scanners and PyCapsule streams. It
  registers the object and "reads where it lives when the relation runs" (S docstring,
  `_relation.py:4320`).
- `from_parquet` exists as the older alias name; `read_parquet` is the current one.

Expression helpers (S): `col`, `lit`, `fn`, `when(…).then(…).otherwise(…)`, `star(exclude=…)`,
`coalesce` and `sql_expr`. Expression methods include `.cast`, `.try_cast`, `.isin`,
`.between`, `.is_null`, `.alias`, `.asc/.desc/.nulls_first`, aggregate methods (`.sum()`,
`.count()` and others), `.where(pred)` (aggregate `FILTER`), `.over(partition_by, order_by, *,
rows=(a,b) | range=(a,b))`, `.ignore_nulls()`, and the namespaces `.str`, `.dt`, `.list` and
`.json`. The legacy class names `ColumnExpression`, `ConstantExpression`, `FunctionExpression`,
`CaseExpression`, `StarExpression`, `SQLExpression`, `LambdaExpression` and `DefaultExpression`
remain as factory functions (S, `_expression.py:1805–1967`).

### Probe results (P, duckdb 2.0.0)

Rendered SQL is abbreviated.

| Construct | Call | Outcome |
|---|---|---|
| filter / project | `n.filter(col("score") > lit(1.0)).project(col("id"), (col("score")*lit(2)).alias("s2"))` | correct |
| join with an expression condition | `n.join(e, col("n","id") == col("e","src"))` | correct; qualified names via `col(rel, column)` |
| USING join | `n.join(e.rename(src="id"), ["id"])` | correct |
| semi / anti | `how="semi"`, `how="anti"` | correct |
| aggregate | `n.aggregate([col("kind"), fn("count", star()).alias("c"), col("score").sum()], col("kind"))` | correct |
| group_by | `n.group_by(col("kind")).agg(col("id").count().alias("c"))` | correct |
| union | `a.union(b)` | renders `UNION ALL` (count 8 for 4+4) |
| except_ | `(a∪a).except_(a)` | renders `EXCEPT ALL`; returned 4 rows, so bag semantics |
| intersect | `a.intersect(b)` | `INTERSECT ALL`; duplicates retained |
| DISTINCT ON | `n.distinct(col("kind"))` | correct |
| CASE | `when(col("score").is_null()).then(lit("missing")).otherwise(lit("ok"))` | correct |
| window frame | `col("score").sum().over(order_by=[col("id")], rows=(-1, 0))` | `ROWS BETWEEN 1 PRECEDING AND CURRENT ROW` |
| ranking | `fn("rank").over(partition_by=[…], order_by=[col("id").desc()])` | correct |
| list and lambda | `fn("list_transform", col("ids"), lambda x: x*10)`, `fn("list_filter", …)` | correct; Python lambda rendered as `lambda "x_…": …` |
| struct / map | `fn("struct_pack", col("id").alias("i"), …)`, `fn("map", …)` | correct |
| star exclude | `n.project(StarExpression(exclude=["score"]))` | correct |
| pivot | `n.pivot(col("kind"), ["a","b"], fn("count", col("id")))` | correct; the value list is mandatory (S docstring) |
| unpivot | `rel.unpivot("score")` | correct |
| asof / positional joins | `how="asof"` with `>=`; `how="positional"` | correct |
| try_cast / isin | `col("kind").try_cast("INTEGER")`, `col("id").isin(lit(1), lit(3))` | correct |

### What cannot be expressed without SQL text at 2.0.0

The join kinds are the closed set `inner, left, right, outer, full, semi, anti, cross,
positional, natural, asof` (S, P: `duckdb._relation._JOIN_KINDS`).

| Feature | Status | Typed alternative |
|---|---|---|
| `WITH RECURSIVE` (incl. `USING KEY`) | no relation method. The `_WithClause` parser only passes through `WITH RECURSIVE` text given to `sql()` or `query()` (S, `_relation.py:93–160`) | semi-naive loop over relations (§B), or a SQLGlot-built statement |
| `QUALIFY` | no method | project the window into a column and then `.filter` it (same result, one extra projection) |
| `NEAREST` and `LATERAL` joins | not in `_JOIN_KINDS` | SQL only |
| Window frames | integer offsets only. `Over.fragment` renders `ROWS/RANGE BETWEEN n PRECEDING/FOLLOWING` (S, `_expression.py:1590–1625`); no interval `RANGE`, `GROUPS`, `EXCLUDE` or named windows | SQL only for those |
| `CREATE MACRO` / table macros | statements | not needed: Python functions that return relations are the typed macro |
| `ATTACH`, `SET`, `INSTALL/LOAD` | statements | `duckdb.connect(config={...})` covers settings (D) |
| ENUM type objects | `duckdb.enum_type(...)` raises `NotImplementedException` (P) | cast with the type string `"ENUM('a','b')"` (P); this is short text that can be derived from the model |
| `read_parquet(schema=…)` | not in the Python `read_parquet` signature (S). The SQL function has it (D, overview §8.1) | `con.table_function("read_parquet", …)` (U, untested), or cast after reading |

### Escape hatches that weaken the no-SQL-text rule (S)

- `filter`, `order`, `aggregate`, `join(condition=…)` and `project` all accept `str`.
- `sql_expr`, `SQLExpression`, `rel.query(view, sql)` and `con.sql(...)` accept arbitrary text.
- Plain Python strings inside expressions are literals in 2.0 (D, migration table). Explicit
  `col` and `lit` therefore remove ambiguity, and the library warns when a literal resembles a
  column name (S, `_warn_on_literal_names`).

A project-side relation builder should accept only `Expression` objects, plus names that it
resolves from the model.

### Keeping recursion model-typed

Options in order of preference:

1. **No recursion in SQL.** Use a semi-naive loop built only from relations and Arrow (§B). There
   is no text at all.
2. **SQLGlot builder with `dialect="duckdb"`.** SQLGlot is already pinned at 30.27.0.
   - A probe built `select(...).with_("reach", as_=base.union(step, distinct=True),
     recursive=True)`. `q.sql(dialect="duckdb")` produced a statement that ran through
     `e.query("e", sql)` and returned the correct closure (P).
   - SQLGlot's DuckDB dialect round-trips `USING KEY`, which it represents as
     `exp.CTE.args["key_expressions"]`. It also round-trips `QUALIFY` and `ASOF JOIN` (P).
   - The generated text is an artifact of a typed tree. Application code never concatenates it.
   - Caveat: when transpiling from SQLGlot's default dialect, it appended `NULLS FIRST` to an
     `ORDER BY` to preserve generic semantics (P). Build directly in the duckdb dialect, and test
     the generated statement once.
3. **SQLAlchemy Core.** There is no maintained DuckDB 2.0 dialect. `duckdb-engine` is at 0.17.0
   on PyPI, uploaded 2025-03-29, which predates 2.0. It is not installed.
   - A recursive CTE compiled with the PostgreSQL dialect happened to run on DuckDB (P).
   - Treat that as coincidence, not a contract.

`rel.query(view_name, sql)` refuses parameter markers (S, `_relation.py:2718–2725`: "Unexpected
prepared parameter"). Values such as seed nodes must therefore enter as relations, for example a
one-column Arrow table registered beside the edges, never by interpolation. This is also the
model-typed way to pass them.

## B. Graph-shaped work (closure, change impact, dependency walks)

**Recursive CTE semantics at 2.0 (D):**

- A plain recursive CTE must terminate by construction. There is no `CYCLE` or `SEARCH` clause,
  no mutual recursion and no documented maximum depth setting.
- Within `USING KEY`, `UNION` forwards only keys that are new or changed, so the recursion
  converges. `UNION ALL` forwards all candidates and can loop on cycles.
- `recurring.<cte>` reads the accumulated keyed table.
- Payload aggregates such as `USING KEY (node, min(d))` are allowed.
- `deprecated_using_key_syntax` was removed in 2.0.
- CTEs materialize by default unless referenced once.

**Probes (P):**

- **Plain `WITH RECURSIVE … UNION` on a cycle.** Node-set reachability over the edges
  `1→2→3→1`, `3→4`, `5→5` terminated with `[1, 2, 3, 4]`, because `UNION` de-duplicates node rows
  that have already been seen. A closure that carries paths would need explicit cycle checks.
- **`USING KEY (node)`** with a `LEFT JOIN recurring.dist` guard returned
  `[(1,0), (2,1), (3,2), (4,3)]`.

**Iterative semi-naive evaluation with relations only (P, correct):**

```text
frontier = seeds; visited = seeds
while frontier: frontier = (from_arrow(frontier) ⋈ edges on src).project(dst).distinct()
                            ⋉̸ from_arrow(visited)            # how="anti"
                visited  = concat(visited, frontier)
```

- Each round is a vectorized join plus an anti-join.
- The loop count equals the graph depth, which was 4 and 17 rounds below.
- It gives explicit control of per-round provenance, for example recording the round of first
  reach for change-impact depth.

**Indicative timings (P).** These are single runs on random graphs. They are not benchmarks; they
are reported only to set qualitative expectations.

| Graph | Recursive CTE | Python BFS (incl. adjacency build) | Relational loop |
|---|---|---|---|
| 200 nodes, 400 edges, 5 seeds | 6.0 ms | 0.2 ms | 26.4 ms (9 rounds) |
| 100,000 nodes, 300,000 edges, 5 seeds | 133.8 ms | 188.5 ms | 69.7 ms (17 rounds) |

Interpretation:

- On small graphs, Python is cheaper by one to two orders of magnitude, because fixed per-query
  overhead dominates.
- At around 10⁵ edges the engine routes are comparable or better than Python.
- The relational loop beat `UNION` recursion here. A likely reason is that `UNION` de-duplicates
  against the whole accumulated set on each step; this is not verified.

**DuckPGQ (SQL/PGQ, `GRAPH_TABLE`, `ANY SHORTEST`, pagerank, weakly connected components):**

- It is a community extension from a CWI research project, marked "some features may still be
  under development" (D).
- In 2.0 its grammar must be enabled with `SET active_grammar_extensions = ['duckpgq']` (D).
- The catalogue compatibility table for 2.0.0 had empty cells when fetched, so a 2.0.0 binary is
  unconfirmed (U). It is not installed here, and I did not install it.
- Its property-graph DDL and `GRAPH_TABLE` are SQL text. Treat it as unsuitable for a
  model-typed, pinned production path.

## C. Interchange

**Arrow in.**

- `from_arrow` registers the object and does not copy it at registration. The scan happens at
  each execution (S). Zero-copy at execution is not guaranteed (D, overview §4.1).
- A `RecordBatchReader` is single-pass. A second read raises `InvalidInputException: This
  RecordBatchReader has already been consumed…` (P). Call `read_all()` first when a relation is
  read more than once, including by `explain` or by a second consumer.
- Replacement scans also resolve Python variables by name: `con.sql("SELECT … FROM rel")` found a
  local relation variable (P). This is SQL text and is better avoided.
- The source must stay alive for the relation's lifetime (D).

**Arrow out.**

- `rel.to_arrow_table(batch_size=131072)` materializes the result.
- `rel.to_arrow_reader(batch_size=131072)` streams (S signature).
- The default batch size changed from 1,000,000 to 131,072 rows in 2.0 (D), confirmed by probe
  (P).
- **Reader-lifetime rule:** while a reader is open, every other query on that connection raises
  `ResourceInUseException: connection has an open result; drain or destroy it` (P). Use a
  dedicated `cursor()` per reader, or drain it.
- The DB-API `fetch_arrow_table`, `fetch_record_batch` and `.arrow()` were removed from `execute()`
  results. The remaining DB-API Arrow paths copy and warn (S, `_ARROW_TABLE_COPY_WARNING`).
- `iter_rows()` holds the whole result (D, addendum §11.5).
- `materialize()` executes once and keeps the rows in client memory (S docstring, P:
  `random()` stable after materialize, different on re-execution).

**Parquet.**

- Python write signature (S): `write_parquet(file, *, compression, field_ids,
  row_group_size_bytes, row_group_size, overwrite, per_thread_output, use_tmp_file, partition_by,
  write_partition_columns, append, filename_pattern, file_size_bytes)`.
- `overwrite=False` refuses an existing file with an `IOException` (P).
- Python read options are limited to those listed in §A (S).
- SQL-level `read_parquet(schema=…)`, `file_row_group_number`, and `COPY … PARTITION_PATH/ORDER_BY`
  are documented (D) but not exposed in the Python signature.
- Metadata functions such as `parquet_metadata()` and `parquet_kv_metadata()` are SQL table
  functions (D).

**`postgres` extension.** It is not installed in this environment
(`duckdb_extensions()`: `postgres_scanner NOT_INSTALLED`, P). Documented behaviour at 2.0 (D,
`docs/2.0/core_extensions/postgres/overview`):

- **Attaching:** `ATTACH '<libpq string>' AS db (TYPE postgres, READ_ONLY, SCHEMA 'x',
  ISOLATION_LEVEL 'REPEATABLE READ')`. REPEATABLE READ is the default.
- **Parallel scans:** `pg_use_ctid_scan` (default true) and `pg_pages_per_task` control them.
- **Filter pushdown:** `pg_enable_filter_pushdown` (default true).
- **Read mode:** `pg_query_mode` takes `AUTO`, `COPY_BINARY`, `PLAIN_QUERY_*`.
- **Raw access:** `postgres_query(db, 'sql text')` and `postgres_execute`.
- **Remote session:** `CONNECT` routes the session to run remotely.
- **`postgres_attach`** was removed in 2.0.

**What the docs do not say (U):**

- Whether one DuckDB transaction maps to one PostgreSQL transaction.
- Whether parallel ctid scans share an exported snapshot.
- How roles and row-level security apply.

**Inference.** DuckDB is an ordinary libpq client, so PostgreSQL enforces grants and row-level
security for whatever role the attach string names. `READ_ONLY` is a client-side guard, not a
role restriction.

**Authority comparison.**

| Route | Snapshot | Role, RLS, audit | SQL text in application | Copies |
|---|---|---|---|---|
| Application session exports Arrow (ADBC `adbc-driver-postgresql` 1.13.0 installed; or psycopg 3.3.6 binary `COPY`) inside its existing transaction, then `con.from_arrow` | the application's own transaction snapshot, coherent with its other reads | unchanged: the same role, policies and statement log | none beyond the already model-generated PostgreSQL select | one transfer into Arrow |
| `ATTACH … (TYPE postgres)` | separate connection(s); consistency across parallel scans undocumented (U) | a second credential path; RLS evaluated for the attach role | the attach string; `postgres_query` text for anything non-trivial | engine-internal |

The first route keeps authority and audit in PostgreSQL and fits the no-SQL-text preference. The
attach route makes sense only for ad-hoc analysis tooling.

## D. Typing from a model

Probes on 2026-11-18, mapping Arrow types to DuckDB types (P):

| Arrow type | DuckDB type | Round-trip | Consequence |
|---|---|---|---|
| `int64` (non-null) | `BIGINT` | `int64`; the nullability flag is not enforced | validate non-null yourself |
| `dictionary<int8,string>` | `VARCHAR` | `string` | the enum domain is lost on entry; cast to `ENUM('…')` explicitly, where a bad value raises `ConversionException` at execution |
| `decimal128(18,4)` | `DECIMAL(18,4)` | preserved | good |
| `timestamp[us, tz=UTC]` | `TIMESTAMPTZ` | **`timestamp[us, tz=America/New_York]`** | the instant is preserved but the zone label comes from the session `TimeZone`, which defaults from the environment. `SET TimeZone='UTC'` (or the connect config) restored `tz=UTC` (P). This is a determinism hazard for exported products |
| `list<string>`, `struct<k,v>` | `VARCHAR[]`, `STRUCT(k VARCHAR, v INTEGER)` | preserved | good |
| string with `arrow.json` extension | `JSON` | plain `string`, no field metadata (P) | JSON typing ends at the boundary; re-apply it from the model on output |

- **JSON null versus SQL NULL.** `'null'` stored as JSON is not SQL NULL: `json_type` returned
  `'NULL'` and `is_null` was false. A missing value was true SQL NULL (P). Keep the two distinct
  in model mapping.
- **Silent widening.** Unioning a `BIGINT` relation with a `VARCHAR` relation produced `VARCHAR`
  and executed without error (P).
- **Errors that do surface.** A missing column raises `BinderException … Candidate bindings` at
  bind time, before execution. Integer division by zero now raises (P; D, migration table).
- **Recommended boundary.** Derive an Arrow schema from the model. After building a relation,
  check `rel.columns` and `rel.types`, which are available without executing. Finish with
  `table.cast(model_schema)`; pyarrow's safe cast raises on overflow or unsafe casts. Build typed
  literals with `lit(x).cast(...)`, `duckdb.decimal_type`, `struct_type`, `list_type` and
  `map_type` (S, P).

## E. Execution

| Topic | Finding |
|---|---|
| Defaults (P) | `threads=32`, `memory_limit=150.6 GiB` (80 % of RAM), **`temp_directory='.tmp'`** (relative to the working directory for an in-memory database), `preserve_insertion_order=true`, `max_execution_time=0` |
| Settings | Set them explicitly per process with `duckdb.connect(config={"threads": …, "memory_limit": …, "temp_directory": <absolute>, "TimeZone": "UTC"})` (D). `memory_limit` bounds the buffer manager, not the process (D) |
| Threads | One connection used from 4 threads: three raised `ResourceInUseException`. One `con.cursor()` per thread: all four succeeded (P). Python 3.11+, and free-threaded CPython is unsupported (D) |
| Results | DB-API results stay open until drained, `complete()` or `abort()`. A failed statement inside an explicit transaction requires rollback (D) |
| Relations | Lazy and re-executed on every read; `materialize()` pins the rows (P). Build them per request or per operation; a relation is a query definition, not a cache |
| Processes | A file database allows one read-write process; many read-only processes are allowed (D). In-memory databases are per process. `:memory:name` shares one database between connections in one process (D) |
| Diagnostics | `rel.explain()` returns the plan text (P); `EXPLAIN ANALYZE` and `EXPLAIN (SQL)` exist (D). Profiling uses `enable_profiling`, `tracked_metrics` and `duckdb_available_metrics()` (D). `duckdb_memory()` gives buffer accounting only (D). These suit focused investigation only |
| Ordering | No order is guaranteed without `ORDER BY` (D, operations manual "non-deterministic behavior"). Two runs of the same GROUP BY returned the same first five groups (P), which shows nothing. Order-sensitive aggregates such as `list` or `string_agg` need `ORDER BY` inside the aggregate. Floating-point sums can differ in the last bits across thread counts (D) |
| 2.0 changes that matter (D) | plain strings are literals; `col("t","c")` for qualified names; DB-API Arrow methods removed; `ResourceInUseException`; Arrow batch size 131,072; `overwrite=False` now refuses; integer division by zero errors; `lambda x:` syntax; the PEG parser is the default; new files use storage version 69, unreadable by 1.x |

## F. Where DuckDB is the wrong tool

- **Point lookups and small keyed reads.** Every relation pays fixed costs: Python SQL rendering,
  binding and planning. On a 400-edge graph, a plain Python BFS was about 30× faster than a
  recursive CTE (P). Use PostgreSQL indexes or a Python dict.
- **Anything needing row locks, authorization or publication semantics.** DuckDB runs with the
  host process's privileges. `SECURE VIEW` is not a role system (D, overview §13.4).
- **Write paths and the system of record.** There is one writer process per file, and no
  distributed transaction with PostgreSQL (D).
- **Very small inputs.** For tens to hundreds of rows, a Python loop or comprehension over
  already-materialized model objects is cheaper. Moving such work to DuckDB also adds Arrow
  conversion.
- **Full-text ranking parity with PostgreSQL.**
  - DuckDB's `fts` extension is BM25 with its own stemmer and stopwords. Its index is not
    maintained automatically when the source changes (D).
  - PostgreSQL `ts_rank`/`ts_rank_cd` with its dictionaries will not match it.
  - Keep search ranking in PostgreSQL.
- **Read-side paging served to clients.** Joins, grouping and sorting over a live snapshot
  followed by keyset paging are better done in PostgreSQL in the same transaction that authorizes
  the read. Exporting a snapshot to DuckDB only to page it duplicates the authority boundary.
  - Exception: large derived products that are already exported, such as Parquet published for
    comparison or evaluation.

## G. Decision rule for each candidate computation

Move the computation to DuckDB **only when all of these hold**:

1. **Derived and authority-free.** Its inputs are an immutable, identified snapshot, such as a
   published product, an exported Arrow batch or Parquet. Its output is a derived artifact or a
   read-only answer, and it needs no locks, roles or row-level security.
2. **Relational in shape.** It is set-shaped: joins, grouping, windows, anti-joins, or iterative
   frontier expansion over at least about 10⁴–10⁵ rows or edges. Today it is either a Python loop
   over row objects, or a PostgreSQL program run outside the transaction that serves the read.
3. **Expressible from typed parts.** It can be built from `Expression` objects with model-derived
   names and an Arrow schema, with no `str` passed to relation methods. Recursion uses the
   relational loop, or failing that a SQLGlot-built statement.
4. **Bound to a typed boundary.** Arrow comes in from the PostgreSQL session that holds
   authority, and Arrow goes out after `cast(model_schema)`. The connection sets `TimeZone`,
   `threads`, `memory_limit` and an absolute `temp_directory`, and uses one cursor per thread.

Otherwise keep the computation where it is:

- PostgreSQL for transactional reads, paging, search and authorization.
- Python for tiny inputs or object-graph logic.

Tie-breaker: whether DuckDB removes a hand-maintained list of model facts, or only re-hosts it.
Prefer it only in the first case.

## Not resolved

- DuckPGQ 2.0.0 binary availability (U).
- `postgres` extension snapshot coherence across parallel scans and its row-level security
  behaviour; not documented at 2.0, not probed (no PostgreSQL connection permitted).
- `con.table_function("read_parquet", …)` with a `schema` argument (untested).
- Whether the `UNION`-recursion slowdown in §B is structural (one observation only).
