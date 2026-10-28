# Apache DataFusion for Python — Comprehensive Capability Overview

Target: DataFusion Python 55.0.0 · Research date: October 20, 2026 · Package: `datafusion` · Underlying engine: Apache DataFusion (Rust)

Apache DataFusion for Python is an embedded, Arrow-native analytical query engine that combines SQL, composable relational DataFrames, an optimizing query planner, multithreaded execution, and extensible data-access and computation interfaces.

Unlike traditional Python DataFrame libraries, it is designed around a relational query plan rather than an eagerly manipulated table. Python specifies sources, expressions, and transformations; the Rust engine performs optimization and executes vectorized operations over Apache Arrow record batches.

Its distinctive architectural value extends well beyond executing SQL against Parquet files. It can serve as:

- An embedded SQL and relational execution engine.
- A common computational layer over heterogeneous Arrow-compatible data.
- An optimizer and logical-plan representation system.
- A streaming, parallel analytical processing engine.
- A foundation for extensible data systems, including custom providers, catalogs, functions, and query-planning components.
- An interoperability layer for PyArrow, Pandas, Polars, external storage formats, and distributed execution frameworks.

The current stable Python release is 55.0.0, published October 12, 2026, independently of the underlying Rust engine's earlier 55.0.0 release. Version 55 also supports Python 3.10+, with published CPython 3.14 free-threaded builds alongside conventional wheels.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



This overview targets the Python bindings. Where a capability originates in the Rust engine, the distinction between underlying functionality, Python exposure, and separately installed extensions is important.

Primary entry points:

- [Official Python documentation](https://datafusion.apache.org/python/?utm_source=chatgpt.com)
- [Python API reference](https://datafusion.apache.org/python/autoapi/datafusion/index.html?utm_source=chatgpt.com)
- [Python repository](https://github.com/apache/datafusion-python?utm_source=chatgpt.com)
- [Version 55.0.0 on PyPI](https://pypi.org/project/datafusion/55.0.0/?utm_source=chatgpt.com)

## 1. Architecture and capability model

The essential architecture is a separation of four concerns: data representation, logical computation, physical execution, and host-language orchestration.

Python control and composition

SessionContext · DataFrame · Expr · SQL · Functions · Extensions

Logical plans and session configuration

DataFusion Rust engine

SQL and logical planner

Logical optimizer

Physical optimizer

Parallel execution

Arrow batches · Vectorized operators · Resource management

Arrow data and provider interfaces

Files and object stores

Arrow and Python data

Custom table providers

The primary Python abstractions are:

| Abstraction                       | Responsibility                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `SessionContext`                  | Session state, catalogs, data registration, SQL entry points, configuration, and extensions |
| `DataFrame`                       | Lazy relational query construction and execution                                            |
| `Expr`                            | Typed expression trees used by queries and optimizers                                       |
| `datafusion.functions`            | Built-in scalar, aggregate, and window operations                                           |
| `SessionConfig`                   | Query-planning and execution configuration                                                  |
| `RuntimeEnvBuilder`               | Memory management, temporary storage, and spilling                                          |
| `LogicalPlan` / `ExecutionPlan`   | Plan inspection and execution diagnostics                                                   |
| Provider and extension interfaces | Integration with external tables, catalogs, functions, and planning systems                 |

A `DataFrame` does not ordinarily contain a materialized table. It describes a computation. This allows projections, filters, aggregations, joins, and other transformations to be optimized together before execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



This distinction enables an important architectural property: SQL and the Python DataFrame API are two interfaces to the same underlying relational engine, rather than independent execution implementations.

## 2. SQL and the relational DataFrame API

### 2.1 One relational engine, two complementary interfaces

DataFusion exposes two principal ways of constructing computations:

SQL is suited to declarative relational queries, complex joins, subqueries, CTEs, window calculations, grouping sets, and statements that are naturally expressed as relational algebra.

The DataFrame API represents those operations as Python objects and method calls, allowing queries to be assembled, parameterized, inspected, and transformed programmatically without generating SQL strings.

Both ultimately produce logical plans consumed by DataFusion's optimizer.

The DataFrame API covers considerably more than basic projections and filters.

| Functional family          | Python mechanisms                                                                   |
| -------------------------- | ----------------------------------------------------------------------------------- |
| Projection and derivation  | `select`, `select_columns`, `with_column`, `with_columns`, `drop`, `rename`, `cast` |
| Row selection              | `filter`, `distinct`, `limit`, `head`, `tail`                                       |
| Relational combination     | `join`, `join_on`, `union`, `union_by_name`, `intersect`, `except_all`              |
| Aggregation                | `aggregate`, built-in aggregates, grouping sets                                     |
| Windowed computation       | `window`, window expressions, reusable `Window` definitions                         |
| Ordering and distribution  | `sort`, `sort_by`, `repartition`, `repartition_by_hash`                             |
| Nested-data transformation | `unnest_columns`, array and struct expressions                                      |
| Reusable computation       | `alias`, `transform`, `cache`, registered views                                     |
| Plan access                | `logical_plan`, `optimized_logical_plan`, `execution_plan`                          |

The expressive join API is particularly useful. `join()` handles ordinary equijoins with keys and join types, while `join_on()` accepts expression predicates, including inequalities. The supported join types include inner, left, right, full, semi, and anti joins.

`union_by_name()` is another useful distinction: it aligns fields by column name instead of requiring positional correspondence.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[DataFrame API reference](https://datafusion.apache.org/python/autoapi/datafusion/dataframe/index.html?utm_source=chatgpt.com)

### 2.2 An illustrative relational pipeline

```
from datafusion import SessionContext, col, litfrom datafusion import functions as Fctx = SessionContext()events = ctx.read_parquet("events/")result = (    events    .filter(col("status") == lit("complete"))    .aggregate(        [col("region")],        [F.sum(col("amount")).alias("total_amount")]    )    .sort(col("total_amount").sort(ascending=False))    .limit(20))# Execute and materialize the resulttable = result.to_arrow_table()
```

The filter, aggregation, sort, and limit form a single optimizable computation. The Python chain does not force materialization at each step.

Depending on the source, schema, statistics, and resulting physical plan, the engine can avoid reading unnecessary columns, eliminate rows early, select an appropriate aggregation strategy, and use a bounded TopK operator rather than a full sort.

The important point is not merely reduced Python overhead. It is that DataFusion can reason about the combined computation instead of executing each relational operation independently.

### 2.3 Advanced relational operations

DataFusion supports several mechanisms that often eliminate substantial bespoke relational code.

Semi and anti joins express membership and exclusion operations without constructing unnecessary output columns. They are often more natural than joining, filtering, and deduplicating manually.

Non-equijoins through `join_on()` allow predicates involving ranges or other supported comparisons. They are more expressive than key-only joins, although the physical join strategy and cost can differ substantially from an equijoin.

Grouping sets, ROLLUP, and CUBE calculate summaries at multiple levels of dimensional granularity in one relational query. `GroupingSet` exposes these in Python, while `grouping()` distinguishes actual null-valued grouping keys from nulls representing subtotal rows.

Approximate aggregation includes functions such as `approx_distinct`, `approx_median`, and `approx_percentile_cont`. These can be valuable where exact distinct counting or quantiles would impose disproportionate memory or computational costs.

Window expressions support ranking, offsets, aggregate windows, partitioning, ordering, and explicit window frames. Common functions include `row_number`, `rank`, `dense_rank`, `lag`, `lead`, and aggregate functions used with window definitions.

Nested-data operations include array, map, and struct functions, together with `unnest_columns()` for expanding array-valued columns into rows. The latter exposes null-preservation and recursion-depth controls.

These features make DataFusion useful for relational transformations that would otherwise require multiple passes, manually maintained dictionaries, intermediate tables, or Python iteration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+3



Relevant documentation:

- [Aggregation and grouping sets](https://datafusion.apache.org/python/user-guide/common-operations/aggregations.html?utm_source=chatgpt.com)
- [Joins](https://datafusion.apache.org/python/user-guide/common-operations/joins.html?utm_source=chatgpt.com)
- [Window functions](https://datafusion.apache.org/python/user-guide/common-operations/windows.html?utm_source=chatgpt.com)
- [Expressions](https://datafusion.apache.org/python/user-guide/common-operations/expressions.html?utm_source=chatgpt.com)

### 2.4 Expression trees as first-class objects

`datafusion.Expr` is more than syntactic sugar over SQL. It is the representation of a typed expression within the engine's relational planning system.

Expressions can be composed through operators and functions, and can represent:

- Column references, literals, aliases, and casts.
- Boolean predicates and null checks.
- Conditional calculations, `CASE`, and `COALESCE`.
- Scalar function calls.
- Aggregate and window expressions.
- Array, map, and struct operations.
- Sorting definitions and window specifications.

Expressions can be constructed programmatically, retained, and reused within larger queries.

This enables conditional architectures in which a system represents computation as relational expressions rather than opaque Python callbacks or fragments of generated SQL.

That has several potential benefits:

1. Type and schema analysis can occur within the relational planning system.
2. Expression trees remain visible to the optimizer.
3. Expressions can be composed with different source relations.
4. Some expression and plan representations can be serialized for communication with other processes.
5. The computation can remain within native execution kernels rather than requiring a Python callback for each operation.

For example, an operation such as `(col("price") * col("quantity")).alias("value")` remains an arithmetic expression in a logical plan. Replacing it with a Python UDF would ordinarily obscure that arithmetic from some of the optimizer's reasoning.

The expression API is therefore one of DataFusion's most consequential mechanisms for building compact, reusable, relationally defined computational systems.

[Expression API reference](https://datafusion.apache.org/python/autoapi/datafusion/expr/index.html?utm_source=chatgpt.com)

### 2.5 SQL construction, parameterization, and generated queries

`SessionContext.sql()` supports both ordinary SQL and parameterized query construction.

There is an important distinction between its two parameter mechanisms:

| Mechanism        | Behavior                                                                                       | Important consequence                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `**named_params` | Performs textual substitution of Python objects; DataFrames receive temporary registered views | Useful for dynamic SQL construction, but not inherently safe typed parameter binding           |
| `param_values`   | Binds scalar values after SQL parsing using Arrow-compatible values                            | Preserves scalar typing more reliably and avoids the problems of converting values to SQL text |

For example:

```
df = ctx.sql(    "SELECT * FROM measurements WHERE value > $threshold",    param_values={"threshold": 100.0},)
```

For scalar values, `param_values` is the stronger abstraction. Text substitution remains useful for generated SQL and DataFrame references but requires appropriate control over substituted identifiers and fragments. It should not be treated as equivalent to a database driver's bound parameters.

DataFusion also exposes `SQLOptions`, including controls for allowing DDL, DML, and other statements. These are statement-level validation controls, not a complete security sandbox.

The SQL interface supports session-local table and view management, external tables, and data modification operations where the corresponding provider implements them. DataFusion is not, by itself, a transactional database with a universal writable storage implementation.

[Cite refs=turn640365view3turn863156view3turn101779view0/>

[SQL guide](https://datafusion.apache.org/python/user-guide/sql.html?utm_source=chatgpt.com)

## 3. Apache Arrow interoperability and data movement

Arrow interoperability is among the most important reasons to consider DataFusion in a broader Python data-processing environment.

### 3.1 The Arrow C Data and C Stream interfaces

The Python bindings expose standard Arrow interfaces for importing and exporting data.

In particular:

- `SessionContext.from_arrow()` accepts compatible Arrow C Stream and C Array exporters.
- `DataFrame.__arrow_c_stream__()` allows another compatible library to consume query results.
- `collect()` returns PyArrow `RecordBatch` objects.
- `to_arrow_table()` produces a PyArrow `Table`.

These mechanisms allow DataFusion to participate in data pipelines without requiring serialization to CSV, JSON, or Python row objects.

The Arrow C interface permits sharing Arrow buffers without copying their contents. Importantly, zero-copy interoperability does not mean every operation is copy-free: constructing Arrow data from Python objects, converting to NumPy-backed representations, casting types, and performing computations can still allocate new buffers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



### 3.2 Interoperability with other Python libraries

| Library or data representation  | Integration mechanism                         | Distinction                                                              |
| ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| PyArrow `Table` / `RecordBatch` | `from_arrow`, `to_arrow_table`, `collect`     | Direct Arrow-native exchange                                             |
| PyArrow `RecordBatchReader`     | Arrow C Stream import                         | Can supply batches incrementally                                         |
| PyArrow Dataset                 | `register_dataset`                            | Delegates source access through the Dataset interface                    |
| Pandas                          | `from_arrow` where supported, `to_pandas`     | Conversion semantics depend on the DataFrame's types and backing storage |
| Polars                          | `from_arrow`, `from_polars`, `to_polars`      | DataFusion and Polars remain separate execution engines                  |
| Raw Python dictionaries/lists   | `from_pydict`, `from_pylist`                  | Convenient ingestion with Python-to-Arrow conversion costs               |
| Partitioned Arrow batches       | `create_dataframe`, `register_record_batches` | Exposes source partition structure explicitly                            |

An important architectural distinction is that Arrow provides the shared data representation, not a shared query optimizer.

Passing a Polars result to DataFusion, for example, creates a boundary between two optimizers. DataFusion cannot automatically push its complete logical plan into the preceding Polars computation merely because both exchange Arrow buffers.

Likewise, using a PyArrow Dataset does not necessarily preserve every optimization available through DataFusion's native Parquet provider or a specialized table provider.

### 3.3 Incremental and partitioned results

Materializing a full result is not always appropriate.

DataFusion provides several execution interfaces with different ownership and memory consequences:

| Interface                      | Result                                              |
| ------------------------------ | --------------------------------------------------- |
| `collect()`                    | All batches collected into a Python list            |
| `collect_partitioned()`        | Batches grouped by execution partition              |
| `execute_stream()`             | Incrementally consumed record-batch stream          |
| `execute_stream_partitioned()` | One stream per physical output partition            |
| `__arrow_c_stream__()`         | Interoperable Arrow stream for downstream consumers |
| `to_arrow_table()`             | Materialized Arrow table                            |
| `to_pandas()` / `to_polars()`  | Materialized library-specific DataFrame             |

Streaming permits downstream consumers to process batches without holding the complete output in memory. Partitioned streams additionally preserve parallel output channels.

However, streaming output does not guarantee bounded total execution memory. A query with a sort, hash join, window, or other blocking operator may need significant state before it can emit results.

This distinction separates streaming data transfer from the stronger guarantees of a fully incremental processing algorithm.

[Cite refs=turn291251view0turn374785view0turn101779view1/>

[Arrow interoperability guide](https://datafusion.apache.org/python/user-guide/io/arrow.html?utm_source=chatgpt.com)

## 4. Data sources, storage, and materialization

### 4.1 File-backed analytical relations

DataFusion can query files directly, without first loading them into a Pandas DataFrame or database table.

Its Python interfaces support Parquet, CSV, JSON, and Avro sources. There are two useful patterns:

- `ctx.read_parquet(path)` constructs a DataFrame directly.
- `ctx.register_parquet(name, path)` registers a table that SQL and other DataFrames can reference.

Comparable interfaces exist for the other supported formats, subject to their individual read and registration options.

These sources can represent individual files or larger datasets, including directories of files. Source configuration can control schema interpretation, partition columns, and other format-specific behavior.

The distinction between reading a source and registering it is organizational rather than computational: registration gives the source a stable relation name within a session, enabling multiple queries and views to share its definition.

For file-backed analytics, DataFusion's most valuable feature is the integration of source scanning with relational optimization. Column selection, filters, and file metadata can influence how much input is actually read. The effect varies by file format and by the metadata available in the source.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



### 4.2 Parquet as an optimized source and output format

Parquet has a particularly close relationship with DataFusion's execution engine.

Relevant mechanisms include:

Projection pushdown. When a query requires only a subset of columns, DataFusion can avoid decoding other columns.

Predicate and row-group pruning. Parquet metadata may permit skipping row groups that cannot satisfy a predicate, reducing decompression and decoding work.

Page-level filtering and pushdown. Additional configuration and file metadata can permit more selective decoding within row groups.

Partition discovery. Hive-style directory partitions can become logical columns that participate in query filtering.

Parallel scans. Multiple files and file ranges can provide independent work units for execution partitions.

Source ordering. File-ordering information, when correctly declared or discovered, can sometimes reduce downstream sorting requirements.

These optimizations are complementary. A query that uses a small fraction of both rows and columns can benefit substantially more than one that necessarily reads and processes every field.

A practical limitation is that pruning quality depends on the layout and statistics of the Parquet files. A filter's appearance in a SQL query does not prove that the corresponding file scan skipped data; the physical plan and execution metrics are the relevant evidence.

Version 55 of the underlying engine also introduced file-oriented expressions such as `file_row_index()` and `input_file_name()` for source-aware Parquet queries. These provide ways to retain source provenance without separately reconstructing it from filenames or row counters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion Blog

+2



[Parquet I/O guide](https://datafusion.apache.org/python/user-guide/io/parquet.html?utm_source=chatgpt.com)

### 4.3 Object stores

The Python package exposes object-store integrations for:

| Backend                           | Python object                      |
| --------------------------------- | ---------------------------------- |
| Amazon S3 and compatible services | `datafusion.object_store.AmazonS3` |
| Google Cloud Storage              | `GoogleCloud`                      |
| Microsoft Azure Blob Storage      | `MicrosoftAzure`                   |
| HTTP-backed objects               | `Http`                             |
| Local filesystem                  | `LocalFileSystem`                  |

An object store is registered with the session using `register_object_store()`. A file-backed table can then reference locations using the corresponding URI scheme.

For example, the same SQL relational pipeline can be applied to an S3-backed Parquet dataset rather than a local file.

Object stores are storage interfaces, not query engines. DataFusion still plans and executes the query, while the object-store implementation handles object access.

For remote workloads, the key tradeoff is between computation and data transfer. Parquet pruning and selective scans can reduce bytes retrieved, but request latency, network bandwidth, object layout, authentication, and available I/O concurrency still influence performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[Object-store integration examples](https://datafusion.apache.org/python/user-guide/data-sources.html?utm_source=chatgpt.com#object-store)

### 4.4 Delta Lake and Apache Iceberg

One of the more easily overlooked features of DataFusion Python is that it can query lakehouse tables through compatible external table providers, rather than treating the underlying directories as unstructured collections of Parquet files.

Delta Lake integration is exposed through the `deltalake` package:

```
from deltalake import DeltaTabledelta_table = DeltaTable("path_to_table")ctx.register_table("delta_data", delta_table)df = ctx.table("delta_data")
```

A compatible Delta table provider presents the table's own snapshot and file-selection semantics to DataFusion. This is preferable to blindly globbing Parquet files when the Delta transaction log determines which files belong to the current table.

The official documentation highlights an important performance distinction: older Delta Lake integrations that fall back to a PyArrow Dataset may lack filter pushdown available through the native provider interface.

Apache Iceberg integration is documented through `pyiceberg` and `pyiceberg-core`, with supported versions supplying the DataFusion table-provider interface. The documentation specifies `pyiceberg >= 0.10.0` or `pyiceberg-core >= 0.5.0`.

Its behavior depends on the underlying Iceberg Rust implementation used by the provider. It should not be assumed to expose every feature available elsewhere in the PyIceberg ecosystem.

These integrations do not turn DataFusion into the transaction coordinator or full management implementation for either table format. Metadata management, transactions, catalog services, and write guarantees remain responsibilities of the relevant table-format stack.

The current API favors `SessionContext.register_table()`. The older `register_table_provider()` remains documented but is explicitly deprecated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[Delta Lake and Iceberg integrations](https://datafusion.apache.org/python/user-guide/data-sources.html?utm_source=chatgpt.com)

### 4.5 Writing and persistence

DataFrames also expose output operations, including CSV, JSON, and Parquet writers.

The Parquet writer supports format-specific options for compression, row groups, and column-level behavior through interfaces such as `ParquetWriterOptions` and `ParquetColumnOptions`.

This allows DataFusion to function as both a reader and writer in an analytical transformation pipeline, including queries that generate partitioned datasets or intermediate materialized results.

There are three distinct kinds of materialization worth separating:

| Mechanism                             | Resulting lifetime and responsibility                                                 |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| `df.cache()`                          | Materializes a computation in the session's working environment for subsequent reuse  |
| `df.write_parquet(...)`               | Persists data as files managed by the caller                                          |
| `df.write_table(...)` / SQL insertion | Writes through a registered table, subject to the table provider's write capabilities |

A cached DataFrame, a registered view, and a persistent table are not interchangeable. A view primarily preserves a query definition; a cache preserves a materialized result; persisted files and provider-backed tables require explicit storage and lifecycle management.

Provider-specific write support must be verified before treating SQL DML as a general-purpose persistence interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[DataFrame writer options and methods](https://datafusion.apache.org/python/autoapi/datafusion/dataframe/index.html?utm_source=chatgpt.com)

## 5. Catalogs, schemas, views, and relational namespaces

DataFusion's catalog hierarchy is more capable than a flat mapping from table names to DataFrames.

The standard relational naming model has three levels:

`catalog.schema.table`

A default session normally provides the `datafusion` catalog and `public` schema. These are in-memory catalog structures, but the interfaces also support external providers.

The Python API exposes:

- `Catalog` and `Schema` abstractions.
- In-memory catalog and schema implementations.
- `register_catalog_provider()` for attaching catalog implementations.
- Registration of tables within particular schemas.
- `register_view()` for exposing a DataFrame's logical definition as a named relation.
- `information_schema`, when enabled, for introspection.

This creates a useful separation between a query's relational names and their backing implementations.

For example, one catalog can expose locally registered tables, another can use a custom provider, and both can participate in queries within the same session, provided their table implementations can produce compatible DataFusion plans.

This is a significant integration capability: systems with heterogeneous data sources can present them through one relational namespace without necessarily copying everything into one database.

However, the existence of a shared namespace does not imply that joins are remotely executed, pushed into a source database, or automatically optimized across remote systems. Those capabilities depend on the table providers and planner extensions involved.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[Catalog APIs](https://datafusion.apache.org/python/autoapi/datafusion/catalog/index.html?utm_source=chatgpt.com)

## 6. Query optimization, parallel execution, and resource control

### 6.1 Optimizing relational plans

The Python package inherits DataFusion's logical and physical optimizers. This is an important distinction from a library that simply dispatches DataFrame operations to independent computational kernels.

A typical query moves through these stages:

1. SQL parsing or Python expression construction.
2. Logical planning and schema/type resolution.
3. Logical-plan optimization.
4. Physical-plan generation and optimization.
5. Partitioned execution over Arrow batches.
6. Streaming or materialization of the result.

Consequential optimization families include predicate and projection pushdown, expression simplification, constant folding, join simplification, aggregate planning, repartitioning, sorting, and exploitation of source metadata.

DataFusion 55 introduced improvements of particular interest:

- TopK and sort pushdown: Dynamic thresholds can enable additional Parquet row-group pruning during an ordered, limited query.
- Join simplification: Certain joins can be converted to semijoins or eliminated when equivalent.
- More efficient group-by paths: Improvements to columnar grouping include native handling of additional key types such as fixed-size binary fields.
- Faster expression kernels: Specialized handling for small `IN` lists and dictionary-encoded strings can avoid unnecessary generic processing.
- Improved nested-field scans: Parquet nested fields excluded from the declared schema need not be decoded unnecessarily.
- Improved memory-pressure behavior: Aggregations and external sorting gained additional protections and more effective spill behavior.

These are capabilities of the DataFusion 55 engine used by the Python package. Their application is determined by the query's physical plan, source support, and data characteristics, not simply by the engine's availability.

The release announcement reports substantial improvements on particular benchmark cases. Those figures are not general speedup guarantees for Python workloads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion Blog

+1



[DataFusion 55 engine improvements](https://datafusion.apache.org/blog/2026/08/25/datafusion-55.0.0/?utm_source=chatgpt.com)

### 6.2 Multithreading and partitioning

DataFusion's physical operators execute across partitions. Within one Python process, the Rust engine can use multiple CPU cores.

`SessionConfig` controls several relevant settings:

- `with_target_partitions(n)` sets the execution partition target.
- `with_repartition_joins(...)` permits or disables repartitioning for joins.
- `with_repartition_aggregations(...)` does the same for aggregation.
- `with_repartition_windows(...)` controls window-related repartitioning.
- `set(...)` exposes additional named engine options, including batch-size settings.

On individual DataFrames:

- `repartition(n)` requests round-robin redistribution.
- `repartition_by_hash(expr, num=n)` requests hash-based redistribution.

The distinction between requested and actual partitioning is critical.

These calls do not impose an immutable execution strategy. The optimizer can eliminate a redundant exchange, insert another redistribution, or collapse partitions because a downstream operation has different distribution requirements.

The Python `ExecutionPlan.output_partitioning` interface reports the resulting partitioning scheme and count.

DataFusion 55's Rust engine also introduced native range partitioning, but the standard Python DataFrame API does not expose a `repartition_by_range()` equivalent. Python can inspect or execute range-partitioned plans supplied through supported extension or serialization paths.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



This distinction matters when an application already has partitioned or sorted data. Existing distribution metadata can be a computational asset, but DataFusion must know about it and preserve it through the plan for the benefit to materialize.

### 6.3 Memory pools and spilling

`RuntimeEnvBuilder` configures the runtime resources used by execution.

The Python API exposes multiple memory-pool strategies:

| Configuration                   | Behavior and tradeoff                                                                                    |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `with_greedy_memory_pool(size)` | Allows operators to compete for available memory; useful when relatively few operators need to spill     |
| `with_fair_spill_pool(size)`    | Distributes memory reservations more deliberately among spillable operators, potentially spilling sooner |
| `with_unbounded_memory_pool()`  | Avoids an explicit pool limit; shifts greater responsibility for memory safety to the host process       |

Disk management can be configured using `with_disk_manager_os()`, `with_disk_manager_specified(...)`, or disabled entirely.

This is more than a limit on final DataFrame size. Hash aggregations, joins, sorts, and other stateful operators may need working memory substantially different from the eventual result size.

Spilling permits certain operators to transfer working state to temporary storage under memory pressure. It does not imply that arbitrary queries can execute with arbitrarily little RAM: some structures are not spillable, and operator-specific minimum memory requirements still exist.

The underlying DataFusion 55 Rust runtime introduced pluggable spill backends through traits such as `TempFileFactory`. The documented standard Python `RuntimeEnvBuilder` exposes conventional temporary-directory and memory-pool controls, not an equivalent direct Python API for implementing arbitrary spill backends.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[Runtime configuration](https://datafusion.apache.org/python/user-guide/configuration.html?utm_source=chatgpt.com)

### 6.4 Plan inspection and execution diagnostics

DataFusion Python exposes unusually useful query-planning and diagnostic surfaces for an embedded analytical library.

A DataFrame can provide:

```
logical = df.logical_plan()optimized = df.optimized_logical_plan()physical = df.execution_plan()print(physical.display_indent())
```

The physical plan is a traversable tree, rather than just opaque textual output.

After executing the DataFrame, `ExecutionPlan.collect_metrics()` exposes per-operator execution statistics:

```
df.collect()for operator, metrics in df.execution_plan().collect_metrics():    print(        operator,        metrics.output_rows,        metrics.elapsed_compute,        metrics.spill_count,        metrics.spilled_bytes,    )
```

Metrics include output row counts, computation time, spill counts, spill bytes, and other operator-specific observations. They can also be examined per partition rather than only as totals.

This enables several forms of diagnostic reasoning:

| Diagnostic question                            | Useful evidence                                          |
| ---------------------------------------------- | -------------------------------------------------------- |
| Was a filter pushed into the file scan?        | Physical scan node and its predicate/pruning annotations |
| Did the optimizer introduce a costly exchange? | `RepartitionExec`, partitioning metadata                 |
| Is one partition disproportionately expensive? | Per-partition row counts and compute metrics             |
| Is an aggregation spilling?                    | Spill count, bytes, and relevant operator metrics        |
| Did a query actually avoid sorting?            | Presence or absence of physical sort operators           |
| Where is data volume expanding?                | Output-row counts across consecutive operators           |

A vital detail: these metrics are populated by execution. Merely constructing a plan or displaying a preview does not necessarily populate meaningful execution statistics. Reexecuting a DataFrame may create a fresh plan and replace the most recently observed metrics.

`EXPLAIN` and `EXPLAIN ANALYZE` are also available through SQL and the DataFrame interfaces. Version 55 adds richer SQL explain options and PostgreSQL-style JSON output, allowing structured analysis rather than only manually parsing plan text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[Execution metrics guide](https://datafusion.apache.org/python/user-guide/dataframe/execution-metrics.html?utm_source=chatgpt.com)

[Plan API](https://datafusion.apache.org/python/autoapi/datafusion/plan/index.html?utm_source=chatgpt.com)

## 7. Built-in functions, user-defined functions, and computational extensibility

### 7.1 Built-in scalar, aggregate, and window functions

DataFusion supplies an extensive catalog of native functions via SQL and `datafusion.functions`.

Major families include:

| Family                     | Representative capabilities                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| Numeric                    | Arithmetic, trigonometry, rounding, logarithms, statistical primitives                      |
| String and binary          | Matching, extraction, replacement, parsing, encoding and hashing                            |
| Temporal                   | Date arithmetic, extraction, timestamp processing and intervals                             |
| Conditional                | `CASE`, `COALESCE`, null checks, conditional expressions                                    |
| Collection and nested data | Arrays, maps, structs, indexing, containment and construction                               |
| Aggregation                | Sums, counts, averages, extrema, covariance, variance, approximate distinct and percentiles |
| Window                     | Ranking, offsets, ordered/windowed aggregation                                              |
| Source metadata            | File provenance functions supported by relevant sources                                     |

A key design principle is that expressions built from native functions remain visible to the optimizer. Where a computation can be expressed natively, DataFusion can often use optimized Arrow kernels and apply transformations that would be impossible or harder with an opaque callback.

[Function reference](https://datafusion.apache.org/python/autoapi/datafusion/functions/index.html?utm_source=chatgpt.com)

### 7.2 Scalar Python UDFs

The `udf()` API permits custom scalar functions to participate in SQL and DataFrame expressions.

A Python UDF is typically declared using:

- An Arrow-based input type signature.
- An Arrow-compatible return type.
- A function or callable accepting Arrow arrays.
- A volatility declaration, such as `immutable`, `stable`, or `volatile`.

A significant characteristic is that Python UDF callbacks normally receive batches rather than individual Python rows.

This makes it possible to implement a UDF through PyArrow Compute or other vectorized libraries, avoiding explicit row-by-row conversion.

Nevertheless, two costs remain distinct:

1. The engine must cross the Rust/Python callback boundary.
2. Computation that converts Arrow values into ordinary Python objects can become especially expensive.

A UDF also reduces optimizer visibility. A predicate expressed with native comparisons may be pushed into a Parquet scan and used for row-group pruning. An equivalent Python UDF predicate is opaque to those source-level rewrites.

The official guide includes precisely this comparison, showing how a Python UDF can prevent an otherwise eligible Parquet pruning operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



Consequently, built-in expressions, Arrow Compute, Python UDFs, and Rust-backed UDFs serve different performance and extensibility needs rather than being interchangeable implementations.

### 7.3 User-defined aggregates

`udaf()` exposes custom aggregate computation through the `Accumulator` interface.

A typical accumulator implements:

- `update()` to incorporate incoming Arrow batches.
- `state()` to expose mergeable intermediate state.
- `merge()` to combine partial accumulation results.
- `evaluate()` to produce the final scalar result.

The important abstraction is a mergeable aggregate state, not merely a function from an entire column to a scalar.

This permits partial aggregations to be calculated over independent partitions and subsequently merged. It can avoid bespoke manual reduce phases and makes custom aggregators compatible with DataFusion's broader execution structure.

That benefit depends on the aggregate having a correct merge operation. Nonassociative operations, order-sensitive calculations, floating-point accumulation, and state representations all require appropriate care.

Potential applications include specialized summary statistics, domain-specific accumulators, approximate sketches, or composite aggregates that maintain multiple sufficient statistics.

[UDAF documentation](https://datafusion.apache.org/python/user-guide/common-operations/udf-and-udfa.html?utm_source=chatgpt.com#aggregate-functions)

### 7.4 User-defined window functions

`udwf()` accepts a `WindowEvaluator` implementation.

Unlike ordinary scalar functions, window functions operate over ordered and partitioned sequences of rows. The evaluator interface distinguishes several execution patterns:

- `evaluate()` for a row or window frame.
- `evaluate_all()` for computing an entire partition's output.
- `evaluate_all_with_rank()` for calculations that can use rank information.

The evaluator also exposes flags such as `uses_window_frame`, `supports_bounded_execution`, and `include_rank`.

These details matter because not all window calculations have the same resource requirements. A function that must examine an entire partition is fundamentally different from one that can maintain bounded state and produce incremental results.

They make the window extension interface more expressive than an ordinary `groupby().apply()` callback.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



### 7.5 User-defined table functions

`udtf()` and `SessionContext.register_udtf()` extend SQL with functions that return relations rather than scalar values.

This can represent operations such as parameterized data-source discovery, generating derived tables, or exposing structured external computations as relational inputs.

The documented interface accepts literal expressions as arguments and returns a compatible table provider. This is more constrained than a general lateral, per-row table function accepting arbitrary column expressions.

The Python documentation also describes an opt-in `with_session=True` mode, allowing pure-Python table functions to access the calling session's registrations. The supplied session wrapper shares table and function registries, although configuration changes through it have different propagation semantics.

This feature makes table functions capable of acting as controlled relational entry points rather than requiring callers to construct every provider manually.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



### 7.6 Spark-compatible function semantics

DataFusion Python provides a distinct `datafusion.functions.spark` namespace, backed by Spark-compatible functions.

These are not merely aliases for the ordinary DataFusion functions: some intentionally differ in semantics.

For example:

- Spark-compatible `concat` propagates null arguments, while the default DataFusion equivalent can ignore them.
- Spark-compatible `substring` uses Spark's indexing and negative-position conventions.
- Spark-compatible `round` uses `HALF_UP` semantics.

Functions from the Spark namespace can be called directly in DataFrame expressions.

`SessionContext.enable_spark_functions()` registers them for SQL, overriding default functions with matching names for the session's lifetime.

This is an important capability for interoperability, but also a potential source of behavioral changes. Enabling Spark functions is a semantic choice, not merely a request for additional functions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



[Spark-compatible functions](https://datafusion.apache.org/python/user-guide/common-operations/spark-functions.html?utm_source=chatgpt.com)

## 8. Native extensions: providers, catalogs, planners, and codecs

DataFusion Python's extension architecture is considerably broader than its UDF support. It permits independently distributed native libraries to supply new data sources and, in some cases, change how queries are planned and executed.

### 8.1 Why the FFI architecture matters

The underlying Rust query engine exposes powerful native traits, but directly sharing Rust trait objects between separately compiled Python extension modules is unsafe without a compatible binary interface.

Rust does not guarantee a stable native ABI across independently compiled libraries.

DataFusion addresses this with the `datafusion-ffi` infrastructure and Python `PyCapsule` protocols. Compatible native components can be exposed by one Python package and consumed by DataFusion Python without recompiling the entire Python query engine.

This separates three architectural roles:

- Host: `datafusion-python`, which owns the session and standard execution infrastructure.
- Provider: An extension that supplies tables, catalogs, functions, or external sources.
- Planner: An extension that may alter physical planning or delegate execution to another runtime.

These roles can be implemented by different libraries and combined in a session.

This is particularly consequential for higher-performance extensions, since a Rust-backed table provider or UDF can keep its computational implementation outside the Python callback path while remaining accessible through Python SQL and DataFrames.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[Why the Python FFI exists](https://datafusion.apache.org/python/extension-guide/why-ffi.html?utm_source=chatgpt.com)

### 8.2 Custom table providers and relational sources

A custom `TableProvider` is the central interface for adding a new source of relational data.

Conceptually, a provider can supply:

- Schema and other table metadata.
- Scan implementations.
- Relevant filter, projection, and limit pushdown behavior.
- Physical plans for reading its data.
- Supported write operations, where implemented.

The Python package permits registering FFI-backed providers using `SessionContext.register_table()`.

This is a stronger abstraction than implementing a Python generator that returns Arrow batches. A well-integrated provider can allow source-specific operations to participate in DataFusion's optimizer.

For example, a provider backed by a remote relational database could translate eligible filters or projections into source-side queries. An indexed provider could take advantage of its storage system's access paths. A custom columnar provider could avoid decoding columns that a query does not require.

These are architectural possibilities enabled by the provider contract, not automatic behaviors of every custom provider. The implementation must explicitly support the optimizations it advertises.

Importantly, the native table-provider interface is primarily implemented in Rust and exposed to Python through FFI. Ordinary Python classes do not automatically become full-featured native `TableProvider` implementations simply by yielding Arrow arrays.

The extension protocol includes five provider-related hooks:

| FFI hook                                | What it contributes                                             |
| --------------------------------------- | --------------------------------------------------------------- |
| `__datafusion_table_provider__`         | One relational table                                            |
| `__datafusion_table_provider_factory__` | A factory for SQL `CREATE EXTERNAL TABLE`                       |
| `__datafusion_schema_provider__`        | A schema containing tables                                      |
| `__datafusion_catalog_provider__`       | A catalog containing schemas                                    |
| `__datafusion_catalog_provider_list__`  | A replacement or custom implementation of the catalog namespace |

This allows a data-source integration to operate at the appropriate granularity.

A provider factory is particularly interesting: it enables SQL source definitions to construct corresponding native providers, rather than requiring bespoke Python registration code for every table.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



[Native providers and catalogs](https://datafusion.apache.org/python/extension-guide/table-providers.html?utm_source=chatgpt.com)

### 8.3 Native function extensions

The same FFI architecture supports independently compiled implementations of scalar, aggregate, window, and table functions.

These expose dedicated hooks such as:

- `__datafusion_scalar_udf__`
- `__datafusion_aggregate_udf__`
- `__datafusion_window_udf__`
- `__datafusion_table_function__`

They are wrapped using `udf()`, `udaf()`, `udwf()`, or `udtf()` and registered through the corresponding session methods.

This permits custom computational kernels to remain native while participating in the SQL and expression system.

The value is not only performance. A native function can carry declared typing and behavioral metadata that allows better integration with planning, although the full set of metadata features available in the Rust engine is not necessarily exposed through pure-Python UDF constructors.

[Native function extension protocols](https://datafusion.apache.org/python/extension-guide/functions.html?utm_source=chatgpt.com)

### 8.4 Physical optimizer rules and query planners

DataFusion Python exposes two different levels of execution customization.

Physical optimizer rules modify the physical plan produced by DataFusion. These are installed using `SessionContext.add_physical_optimizer_rule()` and the `__datafusion_physical_optimizer_rule__` capsule protocol.

They are appropriate when an extension wants to change a particular plan pattern, exploit specialized ordering or partitioning information, or substitute a more suitable native operator.

Custom query planners are more comprehensive. Through `SessionContext.set_query_planner()` and `__datafusion_query_planner__`, a native extension can participate in translating logical plans into physical execution plans.

This potentially enables alternative execution engines, specialized runtimes, and distributed planners.

The distinction is one of ownership:

| Mechanism               | Scope of customization                                            |
| ----------------------- | ----------------------------------------------------------------- |
| Built-in configuration  | Choose among options already supported by DataFusion              |
| Physical optimizer rule | Rewrite part of an existing physical plan                         |
| Custom query planner    | Take responsibility for constructing or delegating physical plans |

A session has one active query planner. Installing another planner directly replaces the previous one, but compatible planners can be composed through explicit delegation or extension bundles.

This is a powerful mechanism, although it is more involved than writing SQL or ordinary DataFrame transformations. The principal extension implementation remains native code, with Python acting as the registration and orchestration interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[Physical optimizer extensions](https://datafusion.apache.org/python/extension-guide/other-components.html?utm_source=chatgpt.com)

[Custom query planners](https://datafusion.apache.org/python/extension-guide/query-planners.html?utm_source=chatgpt.com)

### 8.5 Logical and physical extension codecs

A provider or planner that creates custom plan nodes introduces another problem: how can those nodes be serialized, transferred, and reconstructed?

The answer is extension codecs.

DataFusion Python provides integration mechanisms for `LogicalExtensionCodec` and `PhysicalExtensionCodec`.

These can encode the information required to reconstruct provider-owned nodes, functions, or plans in another session or process.

Codecs are added using interfaces such as:

- `SessionContext.with_logical_extension_codec()`
- `SessionContext.with_physical_extension_codec()`

They can also be supplied through extension bundles.

A noteworthy capability is that codecs compose through a chain with stable identifiers, rather than forcing each new extension to replace the codec installed by another library.

This permits plans containing objects from multiple independently developed extensions to be serialized together.

A codec should encode enough metadata to reconstruct an object on the receiving side. Serializing a pointer or process-local lookup token is not equivalent to portable serialization, even if it works in a single-process test.

Codec identifiers also become part of the interoperability contract. Both ends must agree on which implementation handles the encoded extension.

These mechanisms can reduce the need to develop an application-specific plan-serialization framework when extending DataFusion's execution model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



[Extension codecs](https://datafusion.apache.org/python/extension-guide/codecs.html?utm_source=chatgpt.com)

### 8.6 Extension bundles and session lifetimes

`SessionContext.with_extensions()` provides a higher-level way to install a collection of codecs and planners.

Its setup is deliberately staged:

1. Collect and install codecs from the supplied extensions.
2. Compose their planners after the complete codec set is available.

This avoids subtle incompatibilities caused by constructing a planner before a required codec has been installed.

A typical pattern is:

```
ctx = SessionContext().with_extensions(    source_library.Extension(),    planner_library.Extension(),)
```

The actual extension implementations are external packages; those names are illustrative.

There is a particularly important lifetime distinction: `with_extensions()` returns a new Python session handle backed by shared underlying session state.

Retain the returned handle. Discarding it can leave different Python handles associated with different codec-chain configurations even while they share the same native session.

Also retain a live `SessionContext` for the lifetime of DataFrames and extension-backed plans that may require session-bound codec or task-context services. A DataFrame alone should not be assumed to keep all such native services alive.

The documentation describes these behaviors explicitly and treats them as part of the extension contract rather than incidental implementation details.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[Extension bundles](https://datafusion.apache.org/python/extension-guide/bundles.html?utm_source=chatgpt.com)

[Session and lifetime rules](https://datafusion.apache.org/python/extension-guide/sessions.html?utm_source=chatgpt.com)

## 9. Query-plan representation, serialization, and cross-engine integration

### 9.1 Logical and physical plans are exposed in Python

DataFusion exposes `LogicalPlan` and `ExecutionPlan` objects through the Python API.

These offer several opportunities beyond diagnostics.

A logical plan can be inspected, serialized, and used to construct another DataFrame through `SessionContext.create_dataframe_from_logical_plan()`.

A physical plan can expose its children, partitioning, metrics, and a serialized representation.

These objects are useful when the query itself is an important program artifact: for example, when plans must be inspected by tooling, transmitted to another process, compared, or handed to an extension.

However, plan APIs should not be confused with a completely general public Python interface for writing every Rust planner transformation. Some extension operations require Rust and the native FFI contracts.

### 9.2 DataFusion-native plan serialization

`LogicalPlan`, `ExecutionPlan`, and `Expr` expose serialization mechanisms.

For example, the plan API provides methods such as:

- `ExecutionPlan.to_bytes(ctx)`
- `ExecutionPlan.from_bytes(ctx, data)`
- Corresponding logical-plan serialization and deserialization.
- `Expr.to_bytes()` and `Expr.from_bytes()`.

Serialization can preserve native plan structures and, where appropriate, route custom nodes through installed codecs.

A particularly useful detail is that certain physical scans backed by registered record batches can serialize their batches within the execution-plan representation. Such a plan may be reconstructible without independently registering an identical in-memory table.

That behavior should not be generalized to all providers. File-backed and external-resource-backed plans may refer to resources that must remain accessible to the receiving environment.

Compatibility also depends on engine versions, extension protocols, registered functions, and installed codecs.

[Cite refs=turn881771view1turn446074view2/>

[Logical and physical plan APIs](https://datafusion.apache.org/python/autoapi/datafusion/plan/index.html?utm_source=chatgpt.com)

### 9.3 Substrait interoperability

DataFusion Python includes the `datafusion.substrait` module.

Substrait is a cross-engine representation of relational plans. It is distinct from DataFusion's own native serialization.

The Python API includes:

| Component                             | Purpose                                           |
| ------------------------------------- | ------------------------------------------------- |
| `Producer.to_substrait_plan()`        | Converts a DataFusion logical plan to Substrait   |
| `Consumer.from_substrait_plan()`      | Converts Substrait into a DataFusion logical plan |
| `Serde.serialize_bytes()`             | Produces a serialized Substrait plan from SQL     |
| `Serde.deserialize_bytes()`           | Reconstructs a Substrait plan from bytes          |
| `Plan.to_json()` / `Plan.from_json()` | JSON representations for exchange and inspection  |

This opens opportunities for systems to represent computations independently of a particular execution engine.

For example, a planner could produce a Substrait representation for another compatible engine to interpret. Conversely, DataFusion could be used as an execution target for supported externally produced relational plans.

Substrait compatibility is not universal semantic or feature compatibility. Engine-specific functions, unsupported relation types, extension metadata, or differing type and null semantics can prevent an arbitrary plan from being portable.

It is therefore best viewed as an interoperability contract for supported relational constructs, not a guarantee that every DataFusion plan can run unchanged on any Substrait consumer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



[Substrait Python API](https://datafusion.apache.org/python/autoapi/datafusion/substrait/index.html?utm_source=chatgpt.com)

[Substrait specification](https://substrait.io/?utm_source=chatgpt.com)

### 9.4 SQL unparser and dialects

DataFusion provides the inverse of a SQL parser through `datafusion.unparser`.

`Unparser.plan_to_sql()` produces a SQL representation of a logical plan.

The API includes dialect settings for PostgreSQL, MySQL, SQLite, DuckDB, and DataFusion's default dialect.

This makes DataFusion potentially useful as part of a SQL analysis or transformation system:

- Parse SQL into a typed logical plan.
- Apply supported planning or optimization operations.
- Generate SQL for a selected dialect.

This is a consequential capability because it gives the engine a role even when DataFusion itself is not the final executor.

But the unparser should not be mistaken for a comprehensive SQL transpiler that guarantees executable, semantically identical SQL on every target database. Dialect-specific functions, capabilities, identifiers, and type systems still require validation.

The PyPI project description also mentions experimental transpilation of SQL queries into Polars, Pandas, and cuDF operations. That is an adjacent integration capability, not a general stable replacement for the engine's normal SQL execution path.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



[SQL unparser API](https://datafusion.apache.org/python/autoapi/datafusion/unparser/index.html?utm_source=chatgpt.com)

### 9.5 Shipping expressions to Python workers

One of the most distinctive Python-specific features is expression serialization for multiprocessing and distributed task frameworks.

A DataFusion `Expr` can be pickled and sent to another Python process, where it is evaluated against locally available data.

This supports workloads where the caller already knows how to divide work, such as independent file transformations, parameter sweeps, or partition-local calculations.

The serialization behavior depends on the functions present in the expression:

| Expression content                       | How it is transferred                                           |
| ---------------------------------------- | --------------------------------------------------------------- |
| Built-in DataFusion expressions          | Native serializable expression representation                   |
| Python scalar, aggregate, or window UDFs | Can be included using `cloudpickle`                             |
| FFI-backed native functions              | Commonly referenced by name; worker needs matching registration |

`datafusion.ipc` provides `set_sender_ctx()`, `set_worker_ctx()`, and corresponding cleanup functions to control encoding and reconstruction context.

An important interoperability distinction is that a Python UDF serialized through `cloudpickle` depends on a compatible Python runtime. The documented format checks Python major/minor version compatibility, and referenced imported modules must exist on the worker.

`SessionContext.with_python_udf_inlining(enabled=False)` permits a stricter model in which functions must be registered independently rather than shipping Python callback implementations inside serialized expressions.

There is also a significant security implication: deserializing embedded Python callables can execute code. Do not accept pickled expressions or Python-UDF-bearing serialized data from untrusted sources. Disabling inlining narrows that particular deserialization path but does not make Python `pickle.loads()` safe on untrusted data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[Shipping expressions to workers](https://datafusion.apache.org/python/user-guide/distributing-work/expressions.html?utm_source=chatgpt.com)

### 9.6 Distributed query execution is a separate layer

Parallel execution within a process and distributed execution across a cluster are different capabilities.

Standard DataFusion Python can run a query using multiple local CPU cores. It can also serialize expressions for user-managed workers.

It does not automatically distribute an arbitrary SQL query across machines merely because `execute_stream_partitioned()` or `repartition()` is used.

The project identifies distributed query engines such as `datafusion-distributed` and Ballista as related ecosystem work. The current Python distribution guide explicitly states that the new automatic query-engine integration is still under development and not yet usable through its described Python extension workflow.

The recent native planner-extension capabilities provide a foundation for this architecture, but should not be confused with a fully integrated distributed service shipped in the `datafusion` wheel.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



[Distributed execution boundaries](https://datafusion.apache.org/python/user-guide/distributing-work/query-engines.html?utm_source=chatgpt.com)

## 10. Semantic boundaries and important limitations

The following distinctions are especially important because they affect correctness or architecture, not merely execution speed.

### 10.1 DataFusion is an execution engine, not a transactional database

DataFusion can parse and plan SQL statements, register tables, and write results, but those features do not imply that it provides a PostgreSQL-like transactional storage engine.

In particular, DataFusion does not independently provide the complete set of services normally associated with a durable database server: transactional concurrency control, WAL-based recovery, multi-user access management, durable catalogs, and universally supported mutation semantics.

The distinction is illustrated by `MERGE INTO`.

DataFusion 55's underlying Rust engine added SQL planning and a `TableProvider::merge_into` extension hook. The release notes explicitly state that built-in table providers do not yet implement the operation. An appropriate custom provider must supply the execution behavior.

Therefore, support for a SQL statement in the planner does not guarantee that every table provider can execute it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion Blog



### 10.2 SQL nulls, ordering, and type semantics require care

DataFusion implements SQL-like relational semantics, which differ from ordinary Python collection semantics in several ways.

Null values are distinct from missing Python dictionary entries and are not equivalent to ordinary equality-comparable values. SQL three-valued logic applies to predicates.

Relational results are also unordered unless the query specifies an ordering. An apparent ordering from a source file or one execution should not be assumed to survive joins, repartitioning, aggregation, or later executions.

Other semantic differences worth verifying include:

- Null placement in sorts.
- String comparison and case sensitivity.
- Timestamp types, time zones, and conversions.
- Decimal precision and rounding.
- Integer overflow and casts.
- NaN behavior and floating-point aggregation order.
- Nested arrays and structs, including empty versus null values.
- Approximate aggregate error characteristics.

There is a concrete version-sensitive example: the rolling Python documentation contains a 56.0.0 upgrade guide changing default null placement for certain sorting interfaces from `NULLS FIRST` to `NULLS LAST`. That change should not be silently attributed to the currently released Python 55.0.0 package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



For exact, portable behavior, specify the relevant ordering and conversion semantics explicitly.

### 10.3 Optimizer benefits depend on visibility

DataFusion's optimizer can only exploit facts represented in a form it understands.

| Representation                  | Optimizer visibility                                                  |
| ------------------------------- | --------------------------------------------------------------------- |
| Native `Expr` predicate         | Can inspect and potentially push down the predicate                   |
| Python UDF predicate            | Usually opaque to source-level pruning                                |
| Native Parquet provider         | Can exploit supported Parquet metadata and scan capabilities          |
| Generic Arrow batches           | Already materialized; upstream file pruning opportunities have passed |
| Custom table provider           | Depends on provider-declared capabilities                             |
| Materialized external DataFrame | Earlier computation generally remains outside DataFusion's optimizer  |

This explains why minimizing unnecessary Python UDFs and premature materialization can improve more than the immediate computational kernel: it preserves optimization opportunities across the entire query.

Conversely, a specialized external engine may still be more appropriate when it offers an algorithm, storage implementation, or numerical kernel that DataFusion does not provide.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



### 10.4 Python and native-code boundaries

The substantial computations executed by DataFusion's native operators take place in Rust, but a DataFusion Python application still has Python-specific overhead.

Important cases include:

- Constructing very large expression trees through repeated Python calls.
- Invoking Python UDF callbacks.
- Converting Arrow arrays into ordinary Python lists or row dictionaries.
- Moving data between independently managed computational engines.
- Serializing Python closures or transferring data between worker processes.

CPython 3.14 free-threaded wheels are available for Python 55.0.0, but the availability of a free-threaded build is not proof that arbitrary Python UDF workloads scale without contention or that all dependencies are free-threading-safe.

The most reliable performance approach is to preserve native Arrow-backed relational computation where appropriate and measure the actual physical execution plan.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



### 10.5 Native extensions have version and lifetime contracts

The extension ecosystem is powerful but requires tighter version compatibility than ordinary pure-Python packages.

DataFusion Python 55 documents runtime checks for mismatched native FFI versions, giving clearer errors when an extension was built against an incompatible DataFusion major version.

These checks do not constitute a universal binary compatibility guarantee. Some FFI structures cannot be version-checked, and extension protocols still impose ABI, codec, resource-lifetime, and registration requirements.

For reusable extensions, those contracts are part of the package's public integration surface, not optional implementation details.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+1



## 11. Relationship to adjacent Python data libraries

DataFusion can coexist productively with several adjacent libraries, but their responsibilities differ.

| Technology           | Primary role                                                          | Relationship to DataFusion Python                                                                                             |
| -------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| PyArrow              | Columnar representation, compute kernels, file and dataset interfaces | Provides core interoperability and a common data representation                                                               |
| Polars               | High-level DataFrame engine with its own lazy optimizer               | Can exchange Arrow data, but does not share DataFusion's optimizer                                                            |
| DuckDB               | Embedded analytical SQL database                                      | Overlaps in local analytical execution, with different database, storage, and integration abstractions                        |
| SQLAlchemy           | SQL construction, database access, dialects, ORM infrastructure       | Primarily organizes interactions with external database systems rather than serving as DataFusion's physical execution engine |
| SQLGlot              | SQL parsing, rewriting, and dialect transformation                    | Complements SQL-oriented tooling; DataFusion additionally offers native relational planning and execution                     |
| Delta Lake / Iceberg | Table formats, metadata, and table lifecycle                          | Compatible providers can expose their tables to DataFusion queries                                                            |
| Substrait            | Portable representation of relational computation                     | Provides an interchange mechanism for supported plans                                                                         |

DataFusion is particularly distinctive where a system needs an embedded relational optimizer and execution engine that remains extensible through native providers and planners.

PyArrow alone provides the columnar data structures and kernels but not the same complete SQL optimizer and execution pipeline. Polars and DuckDB provide substantial overlapping query-processing functionality, but have different extension models and integration priorities.

No one of these is universally preferable. The consequential question is which system should own relational planning, source access, native computation, materialization, and persistent state.

One architectural possibility enabled by DataFusion is to make the relational plan itself the reusable computational abstraction, with Arrow as the exchange format and specialized providers or engines supplying capabilities when necessary.

That can reduce bespoke query orchestration, manual data transformations, unnecessary materialization, and custom diagnostic infrastructure.

## 12. Version, installation, and documentation reliability

The verified current stable package as of October 20, 2026 is:

```
python -m pip install "datafusion==55.0.0"
```

DataFusion Python 55.0.0 requires Python 3.10 or newer, with published wheels for major Linux, macOS, and Windows environments. The package also publishes CPython 3.14 free-threaded builds.

The separate `pyarrow`, `pandas`, `polars`, `deltalake`, or `pyiceberg` packages are relevant when their respective integration paths are used; they are not all prerequisites for basic SQL execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Documentation version caveat: The main online API documentation tracks the active documentation branch. At the research date, its upgrade guide already contained a 56.0.0 section despite PyPI identifying 55.0.0 as the latest stable Python release. Consequently, individual behaviors that are being actively changed should be cross-checked against the pinned release or tagged source before relying on them as a contractual guarantee.

For native extensions, that verification is particularly important around the FFI capsule signatures, codecs, query planners, and serialization behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation



## 13. Primary-source reference map

The following links are organized to support deeper investigation by engineering agents. Full URLs are included explicitly.

| Area                                  | Primary reference                                                                                                                                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Official Python documentation         | [https://datafusion.apache.org/python/](https://datafusion.apache.org/python/?utm_source=chatgpt.com)                                                                                             |
| Python package and release files      | [https://pypi.org/project/datafusion/](https://pypi.org/project/datafusion/?utm_source=chatgpt.com)                                                                                               |
| Upstream Python repository            | [https://github.com/apache/datafusion-python](https://github.com/apache/datafusion-python?utm_source=chatgpt.com)                                                                                 |
| Complete Python API                   | [https://datafusion.apache.org/python/autoapi/datafusion/index.html](https://datafusion.apache.org/python/autoapi/datafusion/index.html?utm_source=chatgpt.com)                                   |
| SessionContext and configuration APIs | [https://datafusion.apache.org/python/autoapi/datafusion/context/index.html](https://datafusion.apache.org/python/autoapi/datafusion/context/index.html?utm_source=chatgpt.com)                   |
| DataFrame API                         | [https://datafusion.apache.org/python/autoapi/datafusion/dataframe/index.html](https://datafusion.apache.org/python/autoapi/datafusion/dataframe/index.html?utm_source=chatgpt.com)               |
| Expression representation             | [https://datafusion.apache.org/python/autoapi/datafusion/expr/index.html](https://datafusion.apache.org/python/autoapi/datafusion/expr/index.html?utm_source=chatgpt.com)                         |
| Functions                             | [https://datafusion.apache.org/python/autoapi/datafusion/functions/index.html](https://datafusion.apache.org/python/autoapi/datafusion/functions/index.html?utm_source=chatgpt.com)               |
| Data-source integrations              | [https://datafusion.apache.org/python/user-guide/data-sources.html](https://datafusion.apache.org/python/user-guide/data-sources.html?utm_source=chatgpt.com)                                     |
| Arrow interoperability                | [https://datafusion.apache.org/python/user-guide/io/arrow.html](https://datafusion.apache.org/python/user-guide/io/arrow.html?utm_source=chatgpt.com)                                             |
| Execution configuration               | [https://datafusion.apache.org/python/user-guide/configuration.html](https://datafusion.apache.org/python/user-guide/configuration.html?utm_source=chatgpt.com)                                   |
| Execution metrics                     | [https://datafusion.apache.org/python/user-guide/dataframe/execution-metrics.html](https://datafusion.apache.org/python/user-guide/dataframe/execution-metrics.html?utm_source=chatgpt.com)       |
| Physical and logical plans            | [https://datafusion.apache.org/python/autoapi/datafusion/plan/index.html](https://datafusion.apache.org/python/autoapi/datafusion/plan/index.html?utm_source=chatgpt.com)                         |
| Python-defined functions              | [https://datafusion.apache.org/python/user-guide/common-operations/udf-and-udfa.html](https://datafusion.apache.org/python/user-guide/common-operations/udf-and-udfa.html?utm_source=chatgpt.com) |
| Provider and catalog extensions       | [https://datafusion.apache.org/python/extension-guide/table-providers.html](https://datafusion.apache.org/python/extension-guide/table-providers.html?utm_source=chatgpt.com)                     |
| Native function extensions            | [https://datafusion.apache.org/python/extension-guide/functions.html](https://datafusion.apache.org/python/extension-guide/functions.html?utm_source=chatgpt.com)                                 |
| Query-planner extensions              | [https://datafusion.apache.org/python/extension-guide/query-planners.html](https://datafusion.apache.org/python/extension-guide/query-planners.html?utm_source=chatgpt.com)                       |
| Extension codecs                      | [https://datafusion.apache.org/python/extension-guide/codecs.html](https://datafusion.apache.org/python/extension-guide/codecs.html?utm_source=chatgpt.com)                                       |
| Extension bundles                     | [https://datafusion.apache.org/python/extension-guide/bundles.html](https://datafusion.apache.org/python/extension-guide/bundles.html?utm_source=chatgpt.com)                                     |
| Sessions and resource lifetimes       | [https://datafusion.apache.org/python/extension-guide/sessions.html](https://datafusion.apache.org/python/extension-guide/sessions.html?utm_source=chatgpt.com)                                   |
| Substrait serialization               | [https://datafusion.apache.org/python/autoapi/datafusion/substrait/index.html](https://datafusion.apache.org/python/autoapi/datafusion/substrait/index.html?utm_source=chatgpt.com)               |
| SQL unparser                          | [https://datafusion.apache.org/python/autoapi/datafusion/unparser/index.html](https://datafusion.apache.org/python/autoapi/datafusion/unparser/index.html?utm_source=chatgpt.com)                 |
| Expression distribution               | [https://datafusion.apache.org/python/user-guide/distributing-work/expressions.html](https://datafusion.apache.org/python/user-guide/distributing-work/expressions.html?utm_source=chatgpt.com)   |
| Python upgrade guides                 | [https://datafusion.apache.org/python/user-guide/upgrade-guides.html](https://datafusion.apache.org/python/user-guide/upgrade-guides.html?utm_source=chatgpt.com)                                 |
| Underlying engine's v55 release notes | [https://datafusion.apache.org/blog/2026/08/25/datafusion-55.0.0/](https://datafusion.apache.org/blog/2026/08/25/datafusion-55.0.0/?utm_source=chatgpt.com)                                       |

## Overall architectural perspective

The most consequential capability of DataFusion Python is not simply fast SQL execution. It is the ability to combine typed relational expressions, optimization, Arrow-native processing, extensible source providers, structured execution plans, and operational diagnostics in one computational system.

Several combinations deserve particular attention:

Relational expressions + optimizer + Arrow execution. Complex Python-orchestrated data transformations can be represented as one optimizable computation, reducing intermediate materialization and manual execution machinery.

Custom table providers + catalogs + SQL. Heterogeneous data sources can be integrated into a unified relational namespace without requiring every source to be copied into a common persistent database.

Logical/physical plans + diagnostics + configurable execution. The library can expose both what the engine intends to execute and what happened during execution, supporting unusually detailed inspection of partitioning, data movement, spilling, and operator-level costs.

Native FFI extensions + codecs + planner composition. Independent libraries can contribute sophisticated storage and computational capabilities while remaining interoperable through DataFusion's Python session and query APIs.

Expression serialization + Substrait + SQL unparsing. Relational computation can become a transferable and inspectable artifact, opening possibilities beyond executing each query immediately in the same process.

These mechanisms collectively make Apache DataFusion Python a substantial foundation for embedded analytical and extensible relational systems. Its most important limitations arise where those systems require transactional persistence, cross-cluster coordination, arbitrary Python computation inside hot execution paths, or native engine functionality not yet exposed by the Python API.

This reference is based on the official Python documentation, Python package metadata, upstream extension documentation, and DataFusion 55 release materials. It describes documented capabilities and architectural implications; it is not a runtime validation or benchmark of a particular installation.