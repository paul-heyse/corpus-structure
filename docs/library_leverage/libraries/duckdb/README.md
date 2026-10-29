# DuckDB

**Realization assessed:** DuckDB 2.0.0 LTS (released 2026-10-21), the installed Python package.
**Researched:** 2026-10-29 by the coordinator. The [overview](../../../libraries/duckdb_2.md) was read
end to end. Decisive behaviour was then checked against the installed package's API and docstrings,
with one pure-Python probe ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-duckdb/README.md)).
Context7 did not yet cover 2.0. **Pin:** `docs/pins.md` holds duckdb 2.0.0.

## Reusable opportunity types

<a id="duckdb-scoped-relation-binding"></a>

### `duckdb/scoped-relation-binding` — bind operation-local inputs without rewriting SQL text

**Need.** Reusable SQL kernels run many times against different input relations on one connection.
Each run must see its own inputs under the kernel's generic names, without colliding with other
runs or leaving catalog residue.

**Recognize.**
- Regex or string substitution of relation names into SQL text.
- Per-run name prefixes (`op7_input`) spliced into kernels.
- Views created per run and dropped later.

**Mechanisms (installed 2.0.0).**
- **Single input:** `DuckDBPyRelation.query(virtual_table_name, sql)`. The installed docstring says
  the name is "a common table expression over the relation, and a catalog entry for the length of
  the call … Nothing of it is left afterwards." The returned read relation stays lazy and re-reads
  correctly (probe-observed).
- **Several inputs:** a `CREATE TEMP MACRO kernel(a, b) AS TABLE … FROM query_table(a) JOIN
  query_table(b)`.
  - Callers pass the per-run relation names as *values*; the macro text stays constant.
  - Inputs may be registered Arrow tables or views created from relations (probe-observed).
  - Temporary macros live for the connection, so they can be defined once per connection.
- **Other routes:** `create_view`/`register` with unique names (the current shape), schemas with
  `search_path`, and Python replacement scans. Replacement scans resolve names implicitly from the
  calling frame and suit interactive use rather than owned kernels.

**What it discharges.** Name scoping; binding by value rather than text rewriting; the planner
still sees the whole expanded query.

**Residual obligations.**
- Generate and validate per-run names: `query_table` takes identifiers as values, so normal
  identifier hygiene applies.
- Lazy relations re-execute their inputs, so registered objects and views must outlive every
  relation built on them.
- Table-macro overloads must be defined together.

**Conditions.**
- A busy connection raises `ResourceInUseException` when used from another thread (2.0 change).
- Only one call-scoped name is available per `query` call.
- Dynamic SQL brings its usual quoting concerns.

**Evidence.** Overview §3.3, §6.6, §6.7. Installed docstrings for `DuckDBPyRelation.query`,
`DuckDBPyConnection.sql` and `register`. Probe questions 1–2 (2026-10-29).

<a id="duckdb-parquet-export-with-metadata"></a>

### `duckdb/parquet-export-with-metadata` — export query results to Parquet with identity metadata

**Need.** Write a derived relation to Parquet with deterministic order and partitioning, carrying
key-value metadata that identifies its semantic and data context.

**Mechanisms.**
- `COPY (query) TO 'path' (FORMAT parquet, KV_METADATA {key: 'value', …})`. This writes file-level
  key-value pairs that both `parquet_kv_metadata()` and pyarrow `read_metadata` read back
  (probe-observed).
- `PARTITION_BY`, `ORDER_BY` and `PARTITION_PATH` (the latter two new in 2.0), `RETURN_STATS`,
  file-size targets and `overwrite`/`append` control the files written.
- `DuckDBPyRelation.write_parquet(...)` in 2.0.0 has **no** key-value metadata parameter (installed
  signature). Metadata needs the SQL `COPY` route.

**What it discharges.** Native, parallel, partitioned Parquet writing from the analytical engine,
without materializing results in Python.

**Residual obligations.**
- **Arrow schema-level and field-level metadata do not survive DuckDB.** A registered Arrow table
  read back through `to_arrow_table()` has neither (probe-observed). Identity metadata must be
  supplied explicitly as `KV_METADATA`, or re-attached on the Arrow side after the DuckDB hop.
- Field-level Parquet metadata through `COPY` was not examined.
- Row order needs an explicit `ORDER BY`.
- Atomic publication of the output files remains the caller's.

**Conditions.**
- Remote overwrite semantics differ from local.
- High-cardinality partitioning multiplies files and memory use.
- Default storage version 69 affects only DuckDB database files, not Parquet.

**Evidence.** Overview §8.1, §8.4, §14 (`overwrite=False` semantics). Installed `write_parquet`
signature. Probe questions 3–4 (2026-10-29).

## Applicability at source `d739b88` (checked against the tree at `3d97504`)

<a id="applicability-cbo-018"></a>

### CBO-018 — DuckDB composition renames relations by regex: **fits with conditions**

**Opportunity.** [CBO-018](../../codebase/storage-and-analytics.md#cbo-018).
**Type:** [`duckdb/scoped-relation-binding`](#duckdb-scoped-relation-binding).

`AnalysisScope._compose` registers or creates per-operation names (`op{n}_{name}`) and then uses
`re.sub` to rewrite each generic kernel name into them.
- Single-input kernels such as `fuse` can use `relation.query("candidate_input", sql)`. The name is
  then call-scoped and no SQL text is rewritten.
- The multi-input `views` kernel (six inputs) and `operation_disagreements` can become temporary
  table macros taking `query_table` name parameters. The per-operation names become argument values
  instead of rewritten text. The macros can be defined once per `AnalysisScope` connection, which
  suits preparation reused over the scope's lifetime.

**Remains with the codebase.**
- **Kernel ownership.** The kernels currently live as private constants in the retiring
  `pool.duckdb_engine`. Moving them is a relocation question
  ([LOP-X001](../../assessment-patterns.md#lop-x001)), not a DuckDB capability.
- Per-operation name generation and lifetime, which `AnalysisScope` already owns through
  `_registered` and `_views`.
- Explicit ordering.

**Unsettled.**
- Whether expanding the macro changes the kernels' plans or cost. This was not measured.
- Whether `views`' `ViewSpec` inputs are better passed as Arrow tables (current) or as macro
  parameters.

**Ruled out for this context.** Replacement scans, because name resolution from the Python frame is
implicit. A connection-level `search_path` switch, because it is mutable state while lazy relations
re-execute later.

<a id="applicability-cbo-007"></a>

### CBO-007 — exports and analytical capture: **DuckDB export route fits with conditions**

**Opportunity.** [CBO-007](../../codebase/consumers-and-operations.md#cbo-007).
**Type:** [`duckdb/parquet-export-with-metadata`](#duckdb-parquet-export-with-metadata).

An export computed inside an `AnalysisScope` can be written natively with
`COPY (…) TO … (FORMAT parquet, KV_METADATA {…}, ORDER_BY …, PARTITION_BY …)`. The release,
realization, revision and projection identities go in as file-level key-value metadata.

**Conditions.**
- The `cs.*` Arrow schema metadata that capture attaches is **dropped** once rows pass through
  DuckDB. The exporter must restate the identity explicitly: as `KV_METADATA` on this route, or by
  re-attaching schema metadata if the export is written with pyarrow from `to_arrow_reader()`
  output.
- Field-level metadata is visible only to Arrow readers, through the `ARROW:schema` blob (see
  [pyarrow](../pyarrow/README.md#pyarrow-parquet-metadata-carriage)).
- Order must be explicit.
- Files must be published atomically.

**Choice of route.** DuckDB `COPY` and the pyarrow writer
([pyarrow applicability](../pyarrow/README.md#applicability-cbo-007)) are both viable. Which one,
and whether exports derive from the whole-spine packet or from the query path, are comparative-review
questions.

**Not assessed.** DuckDB's `postgres` extension as a capture route.
[ADR-0026](../../../adr/0026-columnar-semantic-operations.md) chose a read-only ADBC import of an
exported snapshot. The extension would need network installation and separate snapshot semantics
research.

## Coverage limits

- Probes used small synthetic relations; no performance claim follows.
- Concurrency of macro use on one connection was not exercised.
- The `postgres` and `quack` extensions, triggers and keyed recursive CTEs were read in the overview
  only. No current opportunity needs them.
