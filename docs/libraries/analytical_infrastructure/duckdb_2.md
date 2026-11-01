# DuckDB 2.0.0 — Comprehensive Python Library and Engine Capability Reference

Version: DuckDB 2.0.0 LTS (“Cinnamon Teal”) Release date: October 21, 2026 Research date: October 21, 2026 Scope: Python API, DuckDB SQL and execution engine, storage, extensions, interoperability, and associated tooling

## 1. Executive orientation

DuckDB is an embedded, high-performance analytical database system that exposes a full SQL execution engine directly inside Python. Unlike a conventional database client library, the `duckdb` Python package incorporates the database engine itself: it can execute complex analytical queries, process external files, maintain transactional persistent databases, transform in-memory columnar data, and interoperate with other database systems without requiring an independently managed server.

DuckDB 2.0.0 substantially expands that model. Its October 21 release introduces a new default storage format, asynchronous I/O, a more extensible SQL parser, comprehensive integration of the `VARIANT` type, triggers, additional relational operators, and a mature version of DuckDB's emerging client-server functionality. The Python integration also exposes a substantial programmatic relational algebra interface, allowing sophisticated query construction without depending exclusively on handwritten SQL.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



The release is an LTS version, with support scheduled through October 2027. The Python package is published on PyPI as `duckdb==2.0.0`, requires Python 3.11 or later, and does not currently support free-threaded CPython builds.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Primary references:

- Release announcement: `https://duckdb.org/2026/10/21/announcing-duckdb-200`
- DuckDB 2.0 documentation: `https://duckdb.org/docs/2.0/`
- New features documentation index: `https://duckdb.org/docs/2.0/whats_new_in_the_docs`
- Python API: `https://duckdb.org/docs/2.0/clients/python/overview`
- Release notes: `https://github.com/duckdb/duckdb/releases/tag/v2.0.0`
- PyPI package: `https://pypi.org/project/duckdb/2.0.0/`

### 1.1 The five architectural roles of DuckDB

DuckDB's capabilities are easiest to understand by separating five roles that can coexist within the same Python process.

| Role                                       | Main mechanisms                                                                       | Architectural significance                                                     |
| ------------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Analytical execution engine                | Vectorized SQL, optimizer, parallel execution, joins, window functions, aggregations  | Performs complex relational computation without Python-level row processing    |
| Embedded relational database               | Persistent tables, transactions, indexes, constraints, views, catalogs                | Provides structured, transactional state alongside analytical execution        |
| Data interchange and transformation engine | Arrow, Pandas, Polars, Parquet, CSV, JSON, `COPY`                                     | Connects in-memory data, external datasets and persistent storage              |
| Federated query engine                     | `ATTACH`, external database extensions, Quack, object storage, lakehouse integrations | Allows SQL to operate across multiple storage systems and execution boundaries |
| Programmable relational framework          | Relations, expression API, macros, UDFs, table functions, extensions                  | Exposes composable transformations and reusable domain-level query logic       |

A distinguishing property is that DuckDB can combine these responsibilities inside a single query. For example, a Python program can construct a relation from an Arrow dataset, join it with a persistent DuckDB table and a remotely attached PostgreSQL table, aggregate the results, and export them as partitioned Parquet.

Whether every part of that query executes locally depends on the connectors, supported pushdown capabilities and optimizer decisions. DuckDB does not guarantee that every external source or Python object can be manipulated without copying data.

### 1.2 Important scope distinctions

The Python library is not a thin database driver. It embeds DuckDB and provides both a DB-API interface and a higher-level relational API. Most computationally expensive query processing runs in the native engine rather than in Python.

DuckDB is not limited to operating on its own database files. It can query files, objects already resident in Python, and supported remote sources. Persistent storage is optional.

DuckDB 2.0 is no longer exclusively an in-process deployment model. The Quack protocol offers server-based access, although this functionality belongs to the DuckDB engine and its `quack` extension, not to a separate Python server framework.

DuckDB remains primarily an analytical system. Transactional tables, triggers, constraints and remote serving increase its versatility, but they do not automatically make it equivalent to a purpose-built high-concurrency OLTP database such as PostgreSQL.

## 2. What fundamentally changes in DuckDB 2.0

The following changes are particularly consequential for understanding what DuckDB 2.0 enables beyond previous releases.

| Capability                 | DuckDB 2.0 significance                                                                                          |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Quack native protocol      | Stabilization and optimization of a server capability introduced in 1.5.3; new `CONNECT`/`DISCONNECT` operations |
| Asynchronous I/O           | Read requests operate independently of query execution, improving I/O concurrency for remote and local storage   |
| `VARIANT`                  | Previously introduced in 1.5, now fully integrated with shredded columnar storage, execution and Parquet         |
| SQL triggers               | `CREATE TRIGGER` enables database-side mutation reactions, auditing and some forms of incremental maintenance    |
| New SQL parser             | Extensible PEG-based grammar becomes the default, with an optional legacy-parser fallback                        |
| SQL expressiveness         | `NEAREST` joins, data-modifying CTEs, nested schemas, JSON mutations and additional SQL-standard syntax          |
| Storage format 69          | New databases gain updated compression, metadata-loading and validation capabilities                             |
| C API v2                   | Broader interfaces for native extensions, including file systems and table functions; not yet declared stable    |
| Extension repositories     | Support for private, signed extension distribution with trusted repositories                                     |
| SQL execution enhancements | Recursive CTE improvements, row-group pruning and other optimizer/runtime improvements                           |
| Python API evolution       | Expanded expression construction, relational operations, results lifecycle and appender capabilities             |
| CLI agent mode             | Structured, concise output and execution safeguards designed for AI-driven tooling                               |

Some of these capabilities are wholly new to 2.0. Others originated in 1.x and became more complete, better integrated or documented in 2.0. This distinction matters when comparing functionality or determining whether a particular API requires a major-version upgrade.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



The sections below examine both the release-specific additions and the broader mature feature set that makes them useful.

## 3. Python API: connections, relations and execution semantics

DuckDB 2.0 has two principal Python programming interfaces, supported by a third layer for constructing typed expressions.

| Interface      | Main objects                                                   | Primary purpose                                                                       |
| -------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| DB-API         | `DuckDBPyConnection`, `execute()`, `fetchone()`, `fetchmany()` | Imperative SQL execution, transactions, parameter binding and row-oriented processing |
| Relational API | `DuckDBPyRelation`, `sql()`, `table()`, `filter()`, `join()`   | Composable, lazy relational transformations and columnar results                      |
| Expression API | `col()`, `lit()`, `fn()`, `when()`, expression operators       | Programmatic construction of SQL-compatible expressions                               |

These are interfaces to the same underlying engine, not separate execution systems.

### 3.1 Connections and database instances

The central object is `DuckDBPyConnection`.

```
import duckdb# Independent in-memory databasecon = duckdb.connect()# Persistent databasepersistent = duckdb.connect("analytics.duckdb")# Explicit read-only accessreader = duckdb.connect("analytics.duckdb", read_only=True)# Engine configurationcon = duckdb.connect(    ":memory:",    config={"threads": "8", "memory_limit": "8GB"})
```

Connections expose SQL execution, transaction management, table registration, data readers, relations, application-defined functions, extensions and configuration.

An important distinction is that `duckdb.sql(...)` uses a module-level default in-memory database. Explicitly created connections provide better isolation of database identity, configuration, extensions and connection lifetimes.

For applications that operate on multiple databases, DuckDB also supports `ATTACH` and `DETACH`, allowing one connection to address more than one catalog.

### 3.2 SQL execution and prepared parameters

`execute()` provides the familiar imperative interface:

```
con.execute("""    CREATE TABLE events (        id BIGINT PRIMARY KEY,        category VARCHAR,        magnitude DOUBLE    )""")con.executemany(    "INSERT INTO events VALUES (?, ?, ?)",    [(1, "A", 2.5), (2, "B", 3.7)])rows = con.execute(    "SELECT * FROM events WHERE magnitude > $minimum",    {"minimum": 3.0}).fetchall()
```

DuckDB supports positional `?` parameters, `$1`-style numbered parameters and named `$parameter` references. Parameters are passed separately to the prepared statement rather than interpolated into SQL text.

`executemany()` is useful for modest quantities of data but is not the preferred high-throughput bulk ingestion mechanism. Appenders, Arrow ingestion and set-based `INSERT ... SELECT` are more suitable for substantial datasets.

### 3.3 The relational API as a native query construction layer

`DuckDBPyRelation` is one of the Python package's most valuable and easily overlooked features.

A relation represents a relational computation, not necessarily a materialized table or a currently executing query.

In DuckDB 2.0, a read-only relation is bound to discover its schema, while its query is executed when a result is requested. Subsequent reads execute the query again. This makes relations reusable query definitions rather than traditional stateful result cursors.

The API can compose operations such as:

| Operation family                 | Representative methods                                                       |
| -------------------------------- | ---------------------------------------------------------------------------- |
| Creation                         | `sql`, `table`, `view`, `values`, `from_arrow`, `from_df`, `read_parquet`    |
| Projection and expression        | `project`, `select`, `with_columns`, `apply`                                 |
| Filtering                        | `filter`, `limit`, `offset`, `head`, `sample`                                |
| Joins and relational composition | `join`, `union`, `intersect`, `except_`                                      |
| Grouping and aggregation         | `aggregate`, `group_by`, `sum`, `avg`, `count`, `median`                     |
| Reshaping                        | `pivot`, `unpivot`, `unnest`, `distinct`, `drop`, `rename`                   |
| Ordering                         | `order`, `sort`                                                              |
| Persistence                      | `create`, `create_view`, `insert`, `write_parquet`, `write_csv`              |
| Inspection and execution         | `sql_query`, `explain`, `show`, `materialize`, `fetchall`, `to_arrow_reader` |

The relational API allows reusable query-construction functions to operate on relations rather than assembling SQL strings. This can eliminate some bespoke SQL-generation code while preserving native query optimization.

Unlike Python dataframe transformations, relation methods generally extend a SQL expression tree and leave execution to DuckDB.

Official reference: `https://duckdb.org/docs/2.0/clients/python/relational_api`

### 3.4 Composable transformations using Python expressions

DuckDB 2.0's expression helpers make relational composition more explicit.

```
from duckdb import col, litsource = con.table("events")filtered = source.filter(col("magnitude") > lit(2.0))enriched = filtered.with_columns(    magnitude_squared=col("magnitude") ** 2,    source_name=lit("simulation"))result = enriched.to_arrow_table()
```

Illustrative API composition; not an executed benchmark or test.

The expression system supports arithmetic, comparisons, Boolean operators, function calls, conditional expressions, casts and aggregate/window expressions.

The important distinction is between expressions referencing columns and expressions containing literal values. In 2.0, ordinary Python strings used in expressions mean literal strings. Explicit `col("name")` and `lit("value")` remove ambiguities.

Other significant helpers include:

- `fn("function_name", ...)` for calling DuckDB SQL functions.
- `when(condition).then(value)` for conditional expression construction.
- `star(exclude=...)` for star projections.
- `sql_expr(...)` for inserting a SQL expression into the expression system.
- `coalesce(...)` for null-handling expressions.
- Python lambdas for supported lambda-capable SQL expressions.

This approach supports a hybrid style: Python can construct relational logic, while DuckDB performs its native typed binding, SQL optimization and execution.

Expression reference: `https://duckdb.org/docs/2.0/clients/python/expression`

### 3.5 Materialization, result conversion and streaming

DuckDB exposes several distinct result representations.

| Method              | Result                       | Important characteristics                                               |
| ------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| `fetchall()`        | Python tuples                | Convenient, but creates Python objects for every returned value         |
| `iter_rows()`       | Python row iterator          | Relation-oriented row access; not equivalent to streaming Arrow batches |
| `to_dicts()`        | Python dictionaries          | Useful at object/API boundaries                                         |
| `df()`              | Pandas DataFrame             | Materializes the result in Pandas                                       |
| `fetchnumpy()`      | NumPy arrays                 | Column-oriented numeric interoperability                                |
| `to_arrow_table()`  | PyArrow Table                | Materializes columnar results                                           |
| `to_arrow_reader()` | Arrow RecordBatchReader      | Supports incremental Arrow batch consumption                            |
| `pl()`              | Polars DataFrame             | Arrow-based integration                                                 |
| `pl(lazy=True)`     | Polars LazyFrame             | Returns a lazy Polars representation                                    |
| `torch()` / `tf()`  | Tensor structures            | Integration with machine-learning frameworks                            |
| `materialize()`     | Materialized DuckDB relation | Executes once and retains the rows in memory                            |

A major distinction is that Arrow conversion and Arrow streaming are not equivalent.

`to_arrow_table()` creates an Arrow table containing the complete result. `to_arrow_reader()` provides a stream of batches, allowing a consumer to avoid retaining the entire query result in Python memory.

Similarly, `materialize()` is not the same as creating a persistent DuckDB table. It retains computed rows for reuse, but does not provide durable database persistence.

Important 2.0 difference: Arrow and Polars results should be obtained through relations. The previous `con.execute(...).fetch_arrow_table()`, `.fetch_record_batch()`, `.arrow()` and `.pl()` methods are removed from DB-API results. Arrow conversion methods remaining on `execute()` results involve copying and should not be confused with relation-based Arrow streaming.

References:

`https://duckdb.org/docs/2.0/clients/python/conversion`

`https://duckdb.org/docs/2.0/clients/python/migration`

### 3.6 Result lifecycle is a substantive 2.0 change

DuckDB 2.0 makes active result ownership more explicit.

When a query is executed using `con.execute()`, its result remains open until exhausted or explicitly terminated.

`con.complete()` finishes an open result without returning its remaining rows. `con.abort()` cancels it. Other queries on that connection can encounter `ResourceInUseException` while the result remains active.

Relations have different semantics: ordinary read relations can be evaluated repeatedly, whereas partially consumed DB-API results maintain execution state.

Consequently, the appropriate interface depends on whether the consumer requires a reusable logical query, a streaming sequence of rows, or a materialized result.

DuckDB also changes error behavior inside explicit transactions: a failed `execute()` statement aborts the transaction, and further statements require a rollback.

Reference: `https://duckdb.org/docs/2.0/clients/python/dbapi`

### 3.7 Concurrency within Python

DuckDB supports parallel execution inside individual SQL queries and concurrency among connections in the same process.

The Python connection model is important:

- Separate calls to `cursor()` produce connections that can be used independently for concurrent operations against the same database.
- Concurrent operations through one connection are not the same as concurrent operations through separate cursors.
- In 2.0, attempting to use a busy connection from another thread raises `ResourceInUseException` rather than silently waiting.
- Multiple Python processes cannot generally open the same native DuckDB database for simultaneous writing under the conventional embedded-file model.

DuckDB uses multiversion concurrency control and optimistic concurrency mechanisms, enabling readers and writers to coexist within the supported concurrency model. Conflicting writes can still produce transaction errors requiring appropriate retry or rollback behavior.

The Quack protocol introduces a separate remote-access deployment model, discussed later.

References:

`https://duckdb.org/docs/2.0/connect/concurrency`

`https://duckdb.org/docs/2.0/guides/python/multiple_threads`

### 3.8 Python type construction and schema introspection

The `duckdb.sqltypes` module and `DuckDBPyType` expose programmatic logical type representations.

These cover conventional scalar types as well as constructed types such as `LIST`, fixed-size `ARRAY`, `STRUCT`, `MAP`, `UNION` and `DECIMAL`.

Representative constructors include:

```
from duckdb.sqltypes import INTEGER, VARCHARitem_type = duckdb.struct_type({    "id": INTEGER,    "name": VARCHAR})map_type = duckdb.map_type(VARCHAR, INTEGER)array_type = duckdb.array_type(INTEGER, 3)decimal_type = duckdb.decimal_type(18, 6)
```

Type objects expose their logical identity and nested children. They can also be constructed from SQL type expressions or certain Python typing constructs, including parameterized lists, dictionaries and unions.

This supports schema-driven software, generic conversion systems, UDF registration, structured records and domain-aware relational abstractions without implementing an entirely separate type-description system.

Python's `int`, `float`, `Decimal`, dates, datetimes and container types still have specific conversion rules, which may differ from their apparent types in a NumPy or Arrow representation.

Reference: `https://duckdb.org/docs/2.0/clients/python/types`

## 4. Advanced Python interoperability and extensibility

### 4.1 Apache Arrow as the main columnar interchange boundary

DuckDB has deep Arrow interoperability. A relation can be created from Arrow tables, record batches, datasets, scanners and readers, as well as objects exposing the Arrow PyCapsule stream interface.

This matters because Arrow supplies a common columnar representation across multiple systems without requiring conversion through Python lists, dictionaries or Pandas objects.

DuckDB can use Arrow as both an input and an output representation, enabling native SQL transformations between Arrow-capable systems.

For suitable Arrow datasets, projection and predicate operations can be pushed toward the underlying scanner. However, Arrow tables and streaming readers do not all support the same pushdown mechanisms.

Zero-copy behavior is possible for some interchange paths, but it is not a universal guarantee: query execution, casting, compression and result construction can allocate or transform buffers.

Reference: `https://duckdb.org/docs/2.0/guides/python/sql_on_arrow`

### 4.2 Pandas, Polars and replacement scans

DuckDB can directly query supported Python objects by their variable names:

```
import pandas as pdcustomers = pd.DataFrame({    "customer_id": [1, 2, 3],    "spend": [100.0, 250.0, 75.0]})result = con.sql("""    SELECT customer_id, spend * 1.1 AS adjusted_spend    FROM customers    WHERE spend > 90""")
```

This uses replacement scans: when SQL refers to a name that is not a registered database object, the Python integration can resolve it to an appropriate Python object.

Explicit registration is also available:

```
con.register("customers_input", customers)
```

The resulting object is queryable but is not automatically copied into a persistent DuckDB table. The registered object must remain valid for the required execution lifetime.

With Polars `LazyFrame` sources, DuckDB can push compatible selections and filters into Polars. With materialized Polars DataFrames, the interface reads the available frame and filters subsequently.

DuckDB is therefore able to act as a SQL optimization and transformation layer around existing data structures, with the physical execution boundary depending on the source.

Reference: `https://duckdb.org/docs/2.0/clients/python/data_ingestion`

### 4.3 User-defined scalar functions

Python functions can be registered as SQL scalar UDFs through `create_function()`.

Two execution models are supported:

Native Python UDFs operate using Python values. They are flexible but introduce Python function-call and object-conversion overhead.

Arrow UDFs operate on Arrow arrays in batches, enabling more efficient execution and better interoperability with vectorized libraries.

UDF configuration includes declared parameter and return types, null handling, exception handling, and a `side_effects` flag that informs DuckDB whether the function can safely be treated as deterministic.

A function declared without side effects may be evaluated or optimized differently from a function that produces random values, changes external state or depends on mutable external data.

Returning `NULL` for exceptions and allowing custom null handling are explicit behaviors rather than inherent properties of arbitrary Python functions.

For performance-sensitive transformations, built-in SQL functions and expressions can be preferable because the optimizer understands their semantics more deeply and their execution avoids Python callbacks.

Reference: `https://duckdb.org/docs/2.0/clients/python/function`

### 4.4 Python appender interface

DuckDB 2.0 provides a Python appender for efficiently inserting rows produced by Python code.

```
with con.appender("events") as appender:    appender.append_row(3, "A", 5.2)    appender.append_rows([        (4, "B", 7.1),        (5, "A", 2.0)    ])
```

The appender buffers rows and flushes them as a set, avoiding much of the overhead of repeatedly executing individual `INSERT` statements.

`query_appender()` extends this concept to custom SQL statements.

It is particularly relevant for producers that naturally generate individual records or batches of Python values. Data already present in Arrow or Pandas can generally be loaded more efficiently using native bulk paths.

Reference: `https://duckdb.org/docs/2.0/clients/python/appender`

### 4.5 Additional Python integration boundaries

The Python ecosystem offers several higher-level interfaces:

| Integration          | Role                                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------- |
| Ibis                 | Backend-independent relational expression system capable of generating DuckDB queries                |
| Polars               | Arrow-oriented DataFrame processing with interoperability between lazy and materialized computations |
| SQLAlchemy           | SQL construction, connectivity and ORM integration through a separately maintained DuckDB dialect    |
| ADBC                 | Standardized Arrow-oriented database connectivity interface                                          |
| PyTorch / TensorFlow | Conversion of query results into tensor-oriented structures                                          |
| fsspec               | Integration with Python-defined filesystem backends                                                  |
| Jupyter / marimo     | Interactive analytical environments using embedded SQL execution                                     |
| Spark-compatible API | Experimental PySpark-compatible interface built over DuckDB relations                                |

The DuckDB Spark-compatible API deserves particular qualification. DuckDB 2.0 documentation identifies it as experimental and bug-fix-only, with future deprecation expected. SQLFrame is identified as the preferred replacement, but the documented SQLFrame 4.5.0 does not yet support DuckDB 2.0. It should not be treated as a fully mature Spark replacement in this release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Reference:

`https://duckdb.org/docs/2.0/clients/python/spark_api`

## 5. Analytical execution engine and query optimization

DuckDB's query engine is designed around native, vectorized execution rather than Python iteration or tuple-at-a-time interpretation.

### 5.1 Columnar, vectorized execution

The fundamental execution unit is a `DataChunk` containing typed column vectors. The standard vector size is 2,048 rows, although not every operation necessarily emits a full chunk.

DuckDB supports different physical vector representations, including flat vectors, constant vectors, dictionary vectors and sequences. These representations allow some operators to manipulate references or compressed representations rather than copying every individual value.

The execution engine builds pipelines of operators and processes chunks through them. This architecture enables:

- Efficient CPU cache use and amortization of function-call overhead.
- Native evaluation of expressions across batches.
- Multithreaded scans, aggregations and joins.
- Reuse of internal buffers and intermediate columnar structures.
- Avoidance of Python object creation for intermediate query results.

The distinction between DuckDB's internal vectors and Apache Arrow is important: both are columnar, but they have different physical representations and ownership rules. Arrow is primarily an interchange interface, whereas DuckDB vectors are its internal execution representation.

Reference: `https://duckdb.org/docs/2.0/internals/vector`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 5.2 Optimizer and execution capabilities

DuckDB's optimizer and execution layer can apply several classes of transformation:

| Mechanism                               | Effect                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| Predicate pushdown                      | Filters rows closer to the scan rather than after expensive intermediate operations         |
| Projection pushdown                     | Reads or computes only the required columns when supported by the source                    |
| Join ordering                           | Chooses join sequences using available cardinality and cost information                     |
| Join algorithm selection                | Uses hash, merge, nested-loop or specialized joins according to the query                   |
| Filter and expression simplification    | Eliminates redundant conditions and simplifies computable expressions                       |
| Common subexpression and CTE processing | Reduces repeated computation where the planner can safely do so                             |
| Top-N optimization                      | Avoids complete sorting where an ordered, limited result admits a more specialized strategy |
| Late materialization                    | Defers some column access until rows have been narrowed down                                |
| Parallel execution                      | Distributes eligible work across engine threads                                             |
| Spill-to-disk execution                 | Allows several blocking operators to process datasets exceeding available memory            |

These optimizations operate across SQL generated from Python relations and handwritten SQL. That is a major benefit of expressing data operations relationally: the engine can optimize the combined computation rather than being forced to execute individual Python transformations in sequence.

However, not all operations can be fully streamed or spilled. Certain aggregate states, indexes, result materializations and extension-specific operations retain additional memory requirements.

### 5.3 Row groups, zonemaps and data skipping

DuckDB automatically maintains min/max indexes, commonly called zonemaps, for native columns with supported types.

When a query applies a selective predicate, DuckDB may skip entire row groups whose value ranges cannot satisfy the condition.

Physical clustering significantly influences effectiveness. For example, a timestamp column ordered approximately by time often yields more useful zonemap ranges than the same values randomly distributed across row groups.

Parquet similarly provides row-group statistics, enabling DuckDB to avoid reading irrelevant row groups and columns. File-level partition pruning can eliminate still larger portions of a dataset.

These are complementary mechanisms:

- Directory partitions eliminate whole files or partitions.
- Parquet row-group metadata eliminates groups within files.
- Native zonemaps eliminate internal database storage ranges.
- Predicate and projection pushdown avoid unnecessary decoding.

DuckDB 2.0 improves row-group pruning and related optimizer behavior, but the resulting benefit still depends on data layout, selectivity and the source format.

References:

`https://duckdb.org/docs/2.0/guides/performance/indexing`

`https://duckdb.org/docs/2.0/data/parquet/overview`

### 5.4 Beyond-memory execution

DuckDB can process datasets larger than physical RAM by spilling supported intermediate operations to disk.

The relevant controls include `memory_limit`, `temp_directory`, `max_temp_directory_size`, `threads` and `preserve_insertion_order`.

A crucial limit: `memory_limit` is not an absolute process-memory ceiling. It controls DuckDB's buffer manager, while some aggregation states, indexes, intermediate vectors and result objects may allocate memory outside it.

Consequently, a query can exceed the configured limit in total process usage. Excessive execution parallelism can also amplify simultaneous working-set requirements.

References:

`https://duckdb.org/docs/2.0/guides/performance/how_to_tune_workloads`

`https://duckdb.org/docs/2.0/guides/performance/oom`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 5.5 Profiling and execution diagnostics

DuckDB exposes several levels of introspection:

- `EXPLAIN` displays the planned physical operator tree.
- `EXPLAIN ANALYZE` executes a query and reports runtime metrics and actual cardinalities.
- JSON profiling provides machine-readable operator and query metrics.
- `SUMMARIZE` reports descriptive statistics for query output.
- `DESCRIBE`, `duckdb_columns()`, `duckdb_tables()` and related table functions expose schemas and catalog metadata.
- `duckdb_settings()` and `current_setting()` expose runtime configuration.
- `duckdb_external_file_cache()` inspects cached external data.
- Logging and progress reporting provide additional operational visibility.

Profiling can distinguish data transfer, scans, joins, aggregation, sorting, high-cardinality intermediates and spill-related overhead. It is also relevant for determining whether federation is actually reducing remote data movement.

In DuckDB 2.0, `max_execution_time` additionally provides a per-query wall-clock limit, expressed in milliseconds.

References:

`https://duckdb.org/docs/2.0/sql/statements/profiling`

`https://duckdb.org/docs/2.0/configuration/pragmas`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



## 6. Advanced SQL and relational expressiveness

DuckDB's SQL dialect is broader than conventional analytical SQL. Its advanced operators can often replace custom Python orchestration for data alignment, shape manipulation, recursion and iterative state computation.

### 6.1 Declarative query construction and friendly SQL

Established features include:

| Feature             | Significance                                                                   |
| ------------------- | ------------------------------------------------------------------------------ |
| `SELECT * EXCLUDE`  | Removes selected columns without explicitly enumerating the rest               |
| `SELECT * REPLACE`  | Updates expressions within a star projection                                   |
| `COLUMNS(...)`      | Selects sets of columns by name, pattern or expression                         |
| `GROUP BY ALL`      | Groups by all projected nonaggregate columns                                   |
| `ORDER BY ALL`      | Orders by every output column                                                  |
| `FROM`-first SQL    | Supports `FROM source SELECT ...`, or simply `FROM source`                     |
| Prefix aliases      | Allows `result: expression` syntax                                             |
| `QUALIFY`           | Filters results of window expressions without an extra subquery                |
| `FILTER`            | Applies conditions to individual aggregate computations                        |
| `PIVOT` / `UNPIVOT` | Performs relational reshaping                                                  |
| `UNION BY NAME`     | Combines relations according to column names instead of positions              |
| List comprehensions | Allows array transformations directly in SQL                                   |
| `TRY_CAST`          | Produces nulls for unsupported conversions rather than failing the whole query |

These mechanisms are particularly useful for building reusable transformations over wide or evolving schemas.

For example:

```
SELECT
    * EXCLUDE (raw_payload),
    magnitude * calibration_factor AS calibrated
FROM measurements
WHERE quality = 'valid';
```

This preserves most of the source schema while replacing a manually enumerated projection with a concise relational expression.

Reference: `https://duckdb.org/docs/2.0/sql/dialect/friendly_sql`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 6.2 Specialized join operators

Several DuckDB joins directly encode relationships that otherwise require additional SQL or Python logic.

| Join              | Semantics                                                                                  | Typical workload                                    |
| ----------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `SEMI JOIN`       | Returns left rows having a right-side match, without duplicating them                      | Existence filtering                                 |
| `ANTI JOIN`       | Returns left rows without a matching right row                                             | Set difference and data validation                  |
| `ASOF JOIN`       | Finds the closest qualifying row under an ordering inequality, with optional equality keys | Time-aligned observations, prices, state histories  |
| `POSITIONAL JOIN` | Aligns rows according to their physical order, outer-padding shorter inputs                | Combining aligned arrays or dataframe columns       |
| `LATERAL JOIN`    | Allows a subquery or table expression to depend on preceding rows                          | Dependent expansions and parameterized computations |
| `NEAREST JOIN`    | Finds top-k rows by distance or similarity                                                 | Nearest-neighbor and embedding matching             |

`ASOF JOIN` is particularly important because it makes temporal alignment a first-class relational operation.

```
SELECT
    observations.*,
    configuration.setpoint
FROM observations
ASOF LEFT JOIN configuration
    ON observations.unit_id = configuration.unit_id
   AND observations.timestamp >= configuration.effective_at;
```

This associates each observation with the most recent configuration satisfying the timestamp inequality, rather than requiring a window-function workaround.

`POSITIONAL JOIN` is different: it relies on order rather than relational keys, so its meaning depends on the input order being well-defined.

### 6.3 New in 2.0: `NEAREST` joins

DuckDB 2.0 introduces exact and approximate nearest-neighbor joins, including top-k matching.

```
SELECT
    q.query_id,
    c.candidate_id
FROM queries q
INNER JOIN candidates c
    NEAREST 3
    BY DISTANCE array_distance(q.embedding, c.embedding);
```

The corresponding approximate form places `APPROX` before `NEAREST`; similarity ranking is also available using `BY SIMILARITY`.

This expresses nearest-neighbor matching as part of the relational query rather than requiring a separate application-level search loop.

Exact and approximate forms carry different guarantees. Approximate search can trade retrieval completeness or ranking fidelity for reduced computation. The native `NEAREST` join should also not be confused with the separately available experimental `vss` extension and its HNSW indexing capability.

Reference: `https://duckdb.org/docs/2.0/sql/query_syntax/from`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 6.4 Window functions, ordered aggregates and statistical functions

DuckDB supports a broad family of analytical operations:

- Window frames, partitions, ranking, lead/lag, first/last values and windowed aggregates.
- `GROUPING SETS`, `ROLLUP` and `CUBE`.
- Ordered-set and ordered aggregates.
- Quantiles, medians and approximate quantile calculations.
- Approximate distinct counts and other approximate aggregation mechanisms.
- Statistical aggregates including correlation, covariance, regression statistics and moments.
- Arrays, list aggregation and transformations.
- Histograms and categorical summaries.

Many of these eliminate bespoke groupwise Python code or multiple intermediate SQL queries.

An important tradeoff is that some order-sensitive aggregates require explicit ordering for reproducibility. SQL aggregate results are not universally deterministic in the presence of parallel execution and unspecified input order.

References:

`https://duckdb.org/docs/2.0/sql/functions/aggregates`

`https://duckdb.org/docs/2.0/sql/functions/window_functions`

### 6.5 Recursive CTEs and keyed iterative state

DuckDB supports conventional recursive SQL with `WITH RECURSIVE`.

Its more advanced `USING KEY` mechanism enables mutable state inside recursive evaluation.

In an ordinary recursive CTE, successive iterations build an append-only union of generated rows. In a keyed recursive CTE, new rows update the retained value associated with their key.

A query can access both:

- The current iteration's frontier.
- The accumulated keyed state through `recurring.<cte_name>`.

DuckDB additionally supports aggregate payloads, for example `USING KEY (node, min(distance))`, allowing an iterative algorithm to retain the smallest known value for each key.

With `UNION`, unchanged keyed states need not be propagated into subsequent iterations. This can enable convergence for certain graph and dynamic-programming algorithms.

The mechanism is relevant to transitive closure, connected components, shortest paths, recursive propagation, iterative rule evaluation and other fixed-point computations.

Version distinction: keyed recursive CTEs predate 2.0; the 2.0 release improves their execution and probe behavior.

Reference: `https://duckdb.org/docs/2.0/sql/query_syntax/with`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 6.6 SQL macros, table macros and reusable logic

DuckDB's `CREATE MACRO` can define both scalar expressions and parameterized table-valued computations.

```
CREATE MACRO normalize(value, minimum, maximum) AS
    (value - minimum) / NULLIF(maximum - minimum, 0);

CREATE MACRO recent_records(cutoff) AS TABLE
    SELECT *
    FROM events
    WHERE occurred_at >= cutoff;
```

Macros support typed parameters, default values and overloads, including multiple signatures declared together.

Unlike a Python UDF, a SQL macro expresses its behavior in DuckDB's own language. The expanded expression or query remains visible to the SQL planner and avoids Python callback overhead.

This makes macros a substantive mechanism for encapsulating recurring relational operations while retaining composability.

Limits include restrictions on certain subquery-containing macros in table-function arguments, and the fact that overloads must be defined together rather than independently appended later.

Reference: `https://duckdb.org/docs/2.0/sql/statements/create_macro`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 6.7 Dynamic SQL and introspection-driven query construction

DuckDB also provides `query()` and `query_table()` for evaluating SQL strings and dynamically referenced tables. Combined with catalog introspection and macros, these enable schema-dependent or metadata-driven relational operations.

Their role differs from Python parameter binding:

- Bound SQL parameters represent values.
- The relational and expression APIs construct typed logical operations.
- Dynamic SQL generates statements or table references at runtime.

For schemas and identifier names, parameter binding alone is not sufficient. Dynamic identifiers need a separately controlled construction mechanism.

Dynamic SQL can support generic inspection and transformations but also introduces the usual quoting, validation, injection and reproducibility concerns.

Reference: `https://duckdb.org/docs/2.0/guides/sql_features/query_and_query_table_functions`

## 7. Structured types, semi-structured data and the 2.0 `VARIANT` model

DuckDB has an unusually capable native type system for analytical transformations.

### 7.1 First-class nested and constructed types

| Type family                | Representation                    | Important distinction                                         |
| -------------------------- | --------------------------------- | ------------------------------------------------------------- |
| `STRUCT`                   | Record with a known set of fields | Schema is explicit; fields have independently typed values    |
| `LIST`                     | Variable-length sequence          | Different rows may contain different numbers of elements      |
| `ARRAY`                    | Fixed-length sequence             | Length is part of the declared type                           |
| `MAP`                      | Key-value collection              | Dynamic keys of a declared key type                           |
| `UNION`                    | Tagged alternatives               | Value belongs to one of a declared set of member types        |
| `ENUM`                     | Finite categorical domain         | Encodes a constrained set of values                           |
| `JSON`                     | Semi-structured document          | Stored physically as JSON text                                |
| `VARIANT`                  | Dynamically typed binary value    | Type information travels with each value                      |
| `DECIMAL`                  | Fixed-precision numeric           | Exact decimal representation with precision/scale constraints |
| `TIMESTAMPTZ` / `INTERVAL` | Temporal values                   | Distinct instant, local-time and interval semantics           |

DuckDB supports nested field access, list comprehensions, higher-order list operations, `UNNEST`, struct transformation and construction, array operations, and many conversions between nested data and relational rows.

This can preserve complex data structures through native SQL rather than flattening every record into an application-specific schema.

### 7.2 `VARIANT`: what 2.0 adds

`VARIANT` was introduced in DuckDB 1.5. In 2.0 it becomes substantially more integrated.

A `VARIANT` value is binary and self-describing. Different rows can hold fundamentally different types without requiring a common static `STRUCT` schema.

```
CREATE TABLE events (
    event_id BIGINT,
    payload VARIANT
);

INSERT INTO events VALUES
    (1, {'name': 'alpha', 'score': 42}::VARIANT),
    (2, [1, 2, 3]::VARIANT),
    (3, 'message'::VARIANT);
```

DuckDB provides the `variant_*` function family, nested value extraction and type introspection.

The principal 2.0 enhancement is structural shredding:

1. DuckDB detects commonly recurring fields and their types.
2. It can store those fields as separately typed, columnar components.
3. Uncommon or incompatible structures can retain their dynamic representation.
4. Queries can access suitable components without treating every value as an opaque JSON string.

This provides a middle ground between completely rigid schemas and raw JSON documents.

Automatic shredding of native DuckDB storage has a minimum row-group threshold, defaulting to 30,000 rows. It does not necessarily activate for every small dataset.

Parquet read/write integration also supports shredded `VARIANT` representations. DuckDB can explicitly specify a shredding schema on export and read compatible shredded Parquet data, including Snowflake-produced representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



`VARIANT` is not a replacement for all `STRUCT` or JSON usage. Known schemas still provide clearer constraints and more predictable types; JSON remains useful for document interchange and broad compatibility. Dynamic variants have type-dependent extraction and conversion behavior that callers must handle.

Reference: `https://duckdb.org/docs/2.0/sql/data_types/variant`

### 7.3 JSON processing and 2.0 mutation functions

DuckDB's JSON functionality includes:

- Reading JSON and JSON Lines files.
- Extraction using JSONPath-like expressions and JSON pointers.
- JSON-to-typed-structure transformations.
- Validation and introspection.
- Creation and serialization of JSON documents.
- Exploding arrays and objects into relational form.

DuckDB 2.0 adds `json_set`, `json_insert`, `json_replace` and `json_remove`.

These construct modified JSON values. They do not imply that an external JSON file or an existing table row is modified in place; persistence still requires the relevant SQL update or export operation.

The combination of native nested types, JSON transformation functions and `VARIANT` offers several distinct representations of hierarchical information. Selection among them affects schema guarantees, interoperability and physical execution costs.

References:

`https://duckdb.org/docs/2.0/data/json/overview`

`https://duckdb.org/docs/2.0/data/json/json_functions`

### 7.4 Temporal semantics and precision

DuckDB supports dates, times, timestamps at different precision levels, intervals, timezone-aware timestamps, `time_bucket`, date arithmetic and temporal joins.

A significant distinction is that `TIMESTAMPTZ` represents an instant, while timezone-dependent display and calendar operations depend on the configured timezone. It should not be treated as permanently storing a timezone name alongside each individual timestamp.

DuckDB 2.0 also moves ICU-backed timezone, calendar and collation functionality to the `icu` extension, with native timezone data sourced from IANA. This is an implementation and packaging change rather than the removal of timezone functionality.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Reference: `https://duckdb.org/docs/2.0/sql/data_types/timestamp`

## 8. File processing, columnar datasets and data transformation

DuckDB supports direct SQL access to external datasets without first importing them into native database storage.

This is one of the most important characteristics of its Python integration: a DuckDB relation can represent a file scan, an in-memory Python object, a persistent table or a remote source, and these can participate in the same relational computation.

### 8.1 Parquet reading, writing and metadata

DuckDB's Parquet support includes:

- Direct querying through `read_parquet()`, `parquet_scan()` and file-path syntax.
- Reading many files through glob patterns or explicit path collections.
- Column projection and predicate pushdown.
- Row-group elimination using Parquet statistics.
- Parallel scans.
- Hive-partition discovery.
- Filename and row-number virtual columns.
- Schema reconciliation across files.
- Compression and row-group controls on writes.
- Parquet encryption support.
- Metadata introspection.
- Nested data and `VARIANT` integration.

The metadata functions are particularly useful for inspection and diagnostics.

| Function                  | Information returned                                              |
| ------------------------- | ----------------------------------------------------------------- |
| `parquet_metadata()`      | Row-group and column-chunk statistics                             |
| `parquet_schema()`        | Parquet's physical and logical schema                             |
| `parquet_file_metadata()` | File-level metadata                                               |
| `parquet_kv_metadata()`   | Custom key/value metadata                                         |
| `parquet_full_metadata()` | Combined nested metadata representation                           |
| `parquet_bloom_probe()`   | Tests supported Parquet Bloom filters for possible value presence |

New in 2.0, `file_row_group_number` exposes the row group from which each result row originated.

Also significant is the `schema` parameter to `read_parquet()`, allowing explicit mapping of fields by name or field ID, with renaming, casts and default values.

This provides a native mechanism for dealing with evolving file schemas. However, an explicitly supplied schema cannot be combined with `union_by_name=true` in the same read operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Reference:

`https://duckdb.org/docs/2.0/data/parquet/overview`

`https://duckdb.org/docs/2.0/data/parquet/metadata`

### 8.2 CSV ingestion, dialect inference and bad-record diagnostics

The CSV reader handles detection and configuration of delimiters, quoting, escaping, headers, newline conventions, types and date/time formats.

`read_csv()` can infer its format from samples or operate with explicitly supplied schemas and parser settings. `sniff_csv()` allows inference to be inspected separately.

Important mechanisms include `all_varchar`, `types`, `columns`, `sample_size`, `null_padding`, `ignore_errors` and `union_by_name`.

DuckDB also supports retaining rejected records rather than silently losing them.

With `store_rejects=true`, the reader can populate temporary tables containing:

- Scan configuration and file information (`reject_scans`).
- Invalid lines, byte offsets, column names and parser/conversion errors (`reject_errors`).

In 2.0, `rejects_line_size_limit` additionally bounds stored error-line length.

This lets native file parsing double as a structured validation and ingestion-diagnostics engine, although downstream completeness still depends on explicitly inspecting the rejected records.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Reference: `https://duckdb.org/docs/2.0/data/csv/reading_faulty_csv_files`

### 8.3 Combining evolving files and partitioned datasets

DuckDB can scan multiple files as one relation, with either positional schema assumptions or name-based reconciliation.

Hive-style partitioning recognizes directory paths such as:

```
dataset/
  year=2026/
    month=09/
      data.parquet
    month=10/
      data.parquet
```

The directory values become queryable partition columns.

A filter on those columns can prune files without opening every Parquet row group.

`union_by_name` is useful when files have different column sets, but it must not be mistaken for a full semantic schema migration system. Missing columns become null, and incompatible or ambiguously related types may still need explicit handling.

References:

`https://duckdb.org/docs/2.0/data/multiple_files/overview`

`https://duckdb.org/docs/2.0/data/partitioning/hive_partitioning`

### 8.4 `COPY` as a programmable export engine

DuckDB's `COPY` statement can transform a SQL result into files, including partitioned and parallel output.

```
COPY (
    SELECT
        year,
        month,
        event_type,
        count(*) AS event_count
    FROM events
    GROUP BY ALL
)
TO 'output/events'
(
    FORMAT parquet,
    PARTITION_BY (year, month),
    ORDER_BY (event_type),
    RETURN_STATS true
);
```

The output system supports configurable filename patterns, approximate file-size targets, per-thread output, partitioning, appending and exported file/statistics reporting.

DuckDB 2.0 adds two particularly useful mechanisms:

- `PARTITION_PATH`: compute custom directory names from partition columns instead of being constrained to Hive's `column=value` layout.
- `ORDER_BY`: specify sorting during export, including sorting within partitions.

For remote object storage, overwriting directories is not generally equivalent to local-file overwrite behavior. Partitioned writes also have file-count and memory implications for datasets with very high partition cardinality.

`COPY FROM DATABASE ... TO` is a different operation: it copies database schemas and data between attached DuckDB databases, including supported schema objects.

Reference:

`https://duckdb.org/docs/2.0/sql/statements/copy`

`https://duckdb.org/docs/2.0/data/partitioning/partitioned_writes`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 8.5 Remote object storage and secrets

With `httpfs` and associated cloud extensions, DuckDB supports reading remote data over HTTP(S) and accessing S3-compatible storage.

Supported integrations include AWS S3, Google Cloud Storage, Azure Blob Storage, S3-compatible services and other endpoints supported by the installed extensions.

DuckDB's secrets system allows credentials and endpoints to be defined separately from query text. For AWS-compatible sources, options include explicit credentials, profiles and credential chains.

For example, the `aws` extension can use the AWS SDK's credential-chain mechanisms, including role-based and temporary credentials.

Scoped secrets are especially important when a query touches multiple buckets or endpoint configurations.

Version-specific security change: DuckDB 2.0 disables legacy per-request S3 credential parameters embedded in URLs by default. Scoped secrets are the preferred alternative.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Reference: `https://duckdb.org/docs/2.0/core_extensions/httpfs/s3api`

### 8.6 Asynchronous I/O in DuckDB 2.0

Before 2.0, remote reads could constrain analytical execution through synchronous request handling.

The new asynchronous I/O subsystem separates I/O progress from query-processing worker threads. It allows multiple read requests to remain in flight while query operators continue processing previously retrieved data.

The engine uses two thread pools:

- Regular execution threads, controlled by `threads`.
- I/O threads, controlled by `async_threads`, with the documented default of four times the system's thread count, capped at 256.

Read-ahead behavior can be controlled through related settings.

This can improve utilization of network connections where remote latency, rather than CPU throughput, limits scan performance. The benefit is workload-dependent and does not imply that every operation becomes asynchronous.

Important documentation discrepancy: The 2.0 release announcement states that asynchronous reads cover Parquet, CSV and native DuckDB storage. However, the versioned 2.0 I/O reference explicitly lists Parquet and uncompressed, seekable UTF-8 CSV as supported, while describing JSON and native DuckDB database storage as synchronous. For format-specific behavior, the narrower documentation is the safer basis until that discrepancy is resolved.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



Reference: `https://duckdb.org/docs/2.0/data/io`

## 9. Native persistence, transactions and storage format

DuckDB's native database storage is more than a cache for analytical queries. It supports persistent relational structures, transactional mutations, indexes, constraints, views, macros and database-level operations.

### 9.1 Storage structure and compression

DuckDB stores persistent data in column-oriented row groups.

The engine provides several compression techniques, including dictionary encoding, run-length encoding, bit packing, frame-of-reference encoding, FSST string compression and floating-point methods such as ALP, Chimp and Patas.

Compression selection depends on data types, distribution and available storage-format features.

Columnar storage makes scanning a small subset of many columns efficient, particularly when combined with zonemaps.

However, it has different performance characteristics from row-oriented OLTP storage. Small, frequent row mutations may incur more overhead than large scans or set-based changes.

### 9.2 New default storage format in 2.0

Storage version 69 is the new default for database files created in DuckDB 2.0.

The format introduces:

- Lazy loading of column metadata, reducing initialization work for large or wide databases.
- `DICT_FSST` string compression enabled by default.
- More compact representation of row deletions.
- Stronger corruption checks when reading.

Backward compatibility is asymmetric. DuckDB 2.0 can read and modify older database files while preserving their storage version. DuckDB 1.x cannot read a database created with the new default 2.0 format.

The `STORAGE_VERSION` attachment option and `storage_compatibility_version` configuration allow explicit control of the format used when creating files.

```
con = duckdb.connect(    "shared.duckdb",    config={"storage_compatibility_version": "v1.5.0"})
```

This is a compatibility facility, not a guarantee that every new DuckDB 2.0 capability is representable in an older format.

Reference: `https://duckdb.org/docs/2.0/internals/storage`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 9.3 Transactions, MVCC and write concurrency

DuckDB supports ACID transactions, explicit `BEGIN`, `COMMIT` and `ROLLBACK`, multiversion concurrency control and optimistic write conflict detection.

The embedded-file concurrency model is:

- One process may open a database in read-write mode.
- That process may use multiple connections and writer threads.
- Multiple processes may access the same database in read-only mode.
- Conventional file-backed access does not allow independent processes to write the same database concurrently.

Transactions provide atomicity for supported database operations, but this should not be extended without qualification to arbitrary external systems or multi-source federated transactions.

For example, modifying a PostgreSQL database through an extension and modifying a local DuckDB table does not by itself establish a distributed transaction with a globally atomic commit.

Reference: `https://duckdb.org/docs/2.0/connect/concurrency`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 9.4 Indexes and constraints

DuckDB has two principal native indexing mechanisms:

Zonemaps are automatic min/max indexes, intended to skip irrelevant storage ranges during scans.

Adaptive Radix Tree (ART) indexes are explicitly created or automatically associated with certain constraints, helping point lookups and uniqueness enforcement.

The difference is consequential. ART indexes do not turn DuckDB into a general OLTP-oriented system, and they consume storage and memory while increasing update and load costs.

An indexed-column update may be implemented as deletion and reinsertion, amplifying write costs.

DuckDB also supports primary-key, unique, not-null and check constraints, with limitations in schema alteration and mutation behavior compared with some traditional relational databases.

Reference: `https://duckdb.org/docs/2.0/sql/indexes`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 9.5 New 2.0 triggers and incremental maintenance

DuckDB 2.0 introduces database triggers using `CREATE TRIGGER`.

Triggers support `BEFORE` and `AFTER` timing, statement-level operation, and supported row-level `AFTER` operations. Statement-level triggers can use `REFERENCING OLD TABLE` and `NEW TABLE` to operate on sets of affected rows.

This is especially valuable when the side effect itself is relational:

```
CREATE TRIGGER track_changes
AFTER UPDATE ON source
REFERENCING
    OLD TABLE AS old_rows
    NEW TABLE AS new_rows
FOR EACH STATEMENT
    INSERT INTO change_log
    SELECT
        n.id,
        o.value AS old_value,
        n.value AS new_value
    FROM old_rows o
    JOIN new_rows n USING (id);
```

The transition-table model allows set-based processing rather than requiring one callback per affected row.

Triggers can also maintain derived aggregate tables incrementally. For example, statement-level insert and delete triggers can update grouped sums and counts rather than recomputing them from all source rows.

This is not yet a native, automatically managed materialized-view subsystem. The correctness of an incrementally maintained table depends on the trigger definitions, mutation coverage and handling of edge cases.

DuckDB 2.0 has explicit limits:

- No `BEFORE ... FOR EACH ROW` triggers.
- No `UPDATE ... FOR EACH ROW` triggers.
- No triggers on views or `INSTEAD OF` triggers.
- No temporary triggers.
- `RETURNING` is not supported on tables with row-level triggers.

Reference: `https://duckdb.org/docs/2.0/sql/statements/create_trigger`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 9.6 Mutations, `MERGE`, CTEs and database lifecycle

DuckDB supports `INSERT`, `UPDATE`, `DELETE`, `MERGE INTO`, upsert-related conflict handling and `RETURNING` for supported statements.

DuckDB 2.0 additionally allows data-modifying CTEs containing `INSERT`, `UPDATE`, `DELETE` and `COPY`, enabling chained mutations and data operations within a SQL statement.

For dependencies that require one modification to complete before another part of the query observes it, the documentation advises marking the modifying CTE `MATERIALIZED`.

This is a more compact way to express certain transactional pipelines, though it requires care about ordering and execution semantics.

Database lifecycle operations include:

- `ATTACH` / `DETACH` and `USE` for catalogs.
- `CHECKPOINT` and `VACUUM`.
- `EXPORT DATABASE` and `IMPORT DATABASE`.
- `COPY FROM DATABASE` between attached databases.
- Schema creation, modification and catalog introspection.
- Database encryption with AES-256-GCM by default, including WAL and temporary files.

DuckDB 2.0 also allows expressions in paths and options of `ATTACH`, making it possible to derive catalog locations from session variables or other scalar expressions.

References:

`https://duckdb.org/docs/2.0/sql/statements/attach`

`https://duckdb.org/docs/2.0/sql/query_syntax/with`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



## 10. DuckDB 2.0 as a remote SQL and federated execution engine

This is one of the most significant changes in DuckDB's overall architectural position.

### 10.1 Quack protocol: DuckDB as a server

The Quack remote protocol was introduced in DuckDB 1.5.3 and receives major performance and stability improvements in 2.0.

With the `quack` extension, one DuckDB process can serve a database to other DuckDB clients over the network.

A representative server:

```
CALL quack_serve(token = 'example-token');
```

A client can attach to that server:

```
ATTACH 'quack:localhost'
    AS remote_db (TOKEN 'example-token');

CONNECT remote_db;

SELECT *
FROM events;

DISCONNECT;
```

The server owns database execution and shared state. Clients send requests to it rather than independently opening the same native file as writers.

This is important because it creates a distinct concurrency architecture from the conventional one-writer-process embedded-file model.

The Python API can use the same underlying DuckDB SQL and extension functionality, but Quack is implemented by the engine extension; it is not a Python web-server package.

References:

`https://duckdb.org/docs/2.0/quack/overview`

`https://duckdb.org/docs/2.0/core_extensions/quack`

### 10.2 `CONNECT` and remote execution pushdown

DuckDB 2.0 introduces `CONNECT` and `DISCONNECT`, which direct session execution to a supported attached remote database.

The feature applies to Quack and also supports PostgreSQL and MySQL through their integrations.

This creates an important distinction between two query patterns:

Federated local execution: DuckDB scans remote tables, transfers required data to its own process, then performs local joins and aggregations.

Remote session execution: Compatible SQL is pushed to a remote database, allowing its own engine to perform the work.

The second model can avoid transferring large intermediate relations to DuckDB. However, it cannot be assumed to retain all DuckDB-specific SQL capabilities when those capabilities are unsupported by the remote backend.

DuckDB's existing remote scan integrations also have their own filter and projection pushdown features, which are distinct from routing an entire session to the remote engine.

References:

`https://duckdb.org/docs/2.0/sql/statements/connect`

`https://duckdb.org/docs/2.0/core_extensions/postgres/overview`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 10.3 PostgreSQL, MySQL and SQLite integration

DuckDB's core database connectors allow external databases to become SQL-addressable sources.

| Extension  | Main capabilities                                                                                | Important boundary                                                                                   |
| ---------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `postgres` | Attach PostgreSQL catalogs, scan tables, insert or update supported data, remote query execution | Type conversion, remote connection management and pushdown capability depend on PostgreSQL semantics |
| `mysql`    | Attach and query MySQL, supported writes and remote session routing                              | SQL dialect and transaction semantics are those of the remote backend when execution is pushed down  |
| `sqlite`   | Read and write SQLite databases through DuckDB                                                   | Separate storage engine, locking model and type behavior                                             |

These extensions can reduce custom extraction code and allow SQL transformations to directly consume relational data from existing systems.

However, a remote scan is not the same as replicating the source database into a transactionally synchronized local snapshot. Cross-system consistency, failure handling and update coordination require explicit consideration.

References:

`https://duckdb.org/docs/2.0/core_extensions/postgres/overview`

`https://duckdb.org/docs/2.0/core_extensions/mysql`

`https://duckdb.org/docs/2.0/core_extensions/sqlite`

### 10.4 Quack security is not equivalent to PostgreSQL role-based access control

Quack has distinct authentication and authorization hooks.

By default:

- Authentication uses a server token.
- Authorization permits every query once the client is authenticated.
- The server listens on localhost unless configured otherwise.

The documentation recommends placing remotely accessible deployments behind a TLS-terminating reverse proxy.

Custom authentication and authorization callbacks can be implemented, including SQL macros and native extension functions. But a basic shared-token setup does not provide granular user, schema or statement permissions.

One less obvious integration boundary is that ordinary connection-scoped Python UDFs cannot serve as Quack authentication/authorization callbacks: the server invokes those hooks on fresh connections. Globally registered native extension functions are required for that purpose.

Reference: `https://duckdb.org/docs/2.0/quack/security`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



## 11. Lakehouse formats: DuckLake, Iceberg, Delta and Lance

DuckDB's native Parquet support is only one layer of its lakehouse functionality.

Parquet is a file format. Lakehouse table formats add catalogs, snapshots, transactional metadata, schema evolution and other table-level semantics.

DuckDB 2.0 supports several of these systems through distinct extensions, each with different capabilities.

### 11.1 Capability comparison

| Format         | DuckDB integration   | Important characteristics                                                                       |
| -------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| DuckLake 1.1   | `ducklake` extension | SQL-catalog-based lakehouse, snapshots, changes, metadata inspection and maintenance            |
| Apache Iceberg | `iceberg` extension  | Reads tables and supports writes through REST catalog integrations                              |
| Delta Lake     | `delta` extension    | Reads, creates and appends to Delta tables; time travel and deletion-vector-aware scans         |
| Lance          | `lance` extension    | Reads and writes Lance datasets, including remote datasets and append operations                |
| Plain Parquet  | Built into DuckDB    | Direct files, partitioned datasets and metadata scanning, without a transactional table catalog |

The central distinction is that ability to read a format does not imply support for its full mutation, transaction or metadata specification.

Reference: `https://duckdb.org/docs/2.0/lakehouse_formats`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 11.2 DuckLake 1.1

DuckLake is a lakehouse format associated with DuckDB that uses a SQL-based metadata catalog alongside columnar data files.

DuckLake 1.1 was released alongside DuckDB 2.0.

The `ducklake` extension allows a DuckLake catalog to be attached as a database:

```
ATTACH 'ducklake:metadata.ducklake'
AS lake (DATA_PATH 'data_files');
```

A DuckLake catalog exposes native SQL operations over its tables and a separate set of metadata functions.

Notable functions include:

| Function                          | Capability                                                 |
| --------------------------------- | ---------------------------------------------------------- |
| `ducklake_snapshots()`            | Lists snapshot history and associated changes              |
| `ducklake_table_info()`           | Reports table metadata, file counts and storage statistics |
| `ducklake_table_insertions()`     | Returns rows inserted between snapshots                    |
| `ducklake_table_deletions()`      | Returns rows deleted between snapshots                     |
| `ducklake_table_changes()`        | Represents inserted/deleted changes between snapshots      |
| `ducklake_expire_snapshots()`     | Expires selected historical snapshots                      |
| `ducklake_cleanup_old_files()`    | Removes eligible obsolete files                            |
| `ducklake_merge_adjacent_files()` | Consolidates adjacent data files                           |

The change-query functionality is particularly notable. It allows table history to be inspected relationally, rather than relying exclusively on external log parsing or custom snapshot-difference logic.

DuckLake's catalog/database and data-file storage are separate concepts, so its snapshot and retention semantics should not be confused with native DuckDB file checkpoints.

References:

`https://duckdb.org/docs/2.0/core_extensions/ducklake`

`https://ducklake.select/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 11.3 Apache Iceberg

DuckDB's Iceberg integration supports two distinct models.

Direct table access uses `iceberg_scan()` to read an Iceberg table from its metadata or table location. This is read-only and does not require a live catalog.

REST-catalog integration attaches a managed Iceberg catalog, allowing tables to be queried and modified using supported SQL operations.

The catalog path supports table creation, insertion, updates, deletes, merges, schema changes and time travel, subject to the specific Iceberg extension and catalog capabilities.

DuckDB 2.0 also improves REST catalog attachment options and metadata-location resolution.

The key design distinction is that a standalone Iceberg metadata file is not equivalent to a writable catalog. Writing requires coordination of Iceberg metadata transactions through the supported catalog mechanism.

References:

`https://duckdb.org/docs/2.0/core_extensions/iceberg/overview`

`https://duckdb.org/docs/2.0/core_extensions/iceberg/writing`

### 11.4 Delta Lake

The `delta` extension uses Delta Kernel and supports local and remote Delta tables.

Documented functionality in DuckDB 2.0 includes:

- Parallel reading of Delta tables.
- Data skipping using file statistics and Parquet row-group information.
- Projection pushdown into nested structures, including supported `VARIANT` fields.
- Deletion vectors and column mapping.
- Time travel using versions or timestamps.
- Creating Delta tables.
- Appending records, including idempotent appends.
- Checkpoints.
- Cloud storage with supported secrets.

Its write capabilities are substantially narrower than the full Delta Lake specification.

DuckDB 2.0 does not support `UPDATE`, `DELETE`, `MERGE INTO`, `ALTER TABLE` or `DROP TABLE` on Delta tables. It also does not support `CREATE TABLE AS SELECT` directly for Delta tables; creation followed by insertion is the supported pattern.

Consequently, Delta can be an efficient native source and append target without necessarily serving as a fully mutable relational store under DuckDB.

Reference: `https://duckdb.org/docs/2.0/core_extensions/delta`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 11.5 Lance

The `lance` extension supports reading and writing Lance datasets, a format oriented toward machine-learning and AI data.

In DuckDB 2.0 it supports path-based scans and `COPY` exports, including overwrite and append modes.

Its integration is useful where tabular and multidimensional data need to participate in SQL transformations before or after being stored in Lance format.

Lance's dataset model is separate from DuckDB's `VARIANT`, native HNSW indexes and Quack protocol. Availability of all those components does not imply they share a unified indexing or transaction implementation.

Reference: `https://duckdb.org/docs/2.0/core_extensions/lance`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



## 12. Extension system and associated tooling

DuckDB's extension architecture is unusually broad for an embedded analytical database.

Extensions can introduce new file readers, catalogs, storage backends, types, scalar or table functions, indexing mechanisms, and execution capabilities.

### 12.1 Major extension families

| Extension or family                     | Capabilities                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------- |
| `httpfs`                                | HTTP(S) reads and S3-compatible object storage                                            |
| `aws` / `azure`                         | Cloud authentication, credentials and related storage integration                         |
| `postgres`, `mysql`, `sqlite`           | External database access and interoperability                                             |
| `ducklake`, `iceberg`, `delta`, `lance` | Lakehouse table formats                                                                   |
| `spatial`                               | Geometry, geographic transformations, spatial functions and spatial file interoperability |
| `fts`                                   | Full-text indexing, tokenization and BM25-based retrieval                                 |
| `vss`                                   | Approximate vector similarity search with HNSW indexes                                    |
| `excel`, `avro`, `encodings`            | Additional file formats and character encodings                                           |
| `icu`                                   | Timezones, calendars and collations                                                       |
| `quack`                                 | DuckDB's remote query protocol                                                            |
| `unity_catalog`                         | Unity Catalog connectivity                                                                |
| `vortex`                                | Vortex file-format interoperability                                                       |
| `tpch`, `tpcds`                         | Standard analytical benchmark data generation                                             |
| `ui`                                    | Browser-based local DuckDB interface                                                      |

Individual extensions have their own implementation, compatibility and release schedules.

For example, the spatial extension integrates substantial geospatial functionality into DuckDB, but these operations do not originate in the basic `duckdb` Python package's expression API. They become available to Python SQL execution when the extension is loaded.

Reference: `https://duckdb.org/docs/2.0/core_extensions/overview`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 12.2 Full-text search

The full-text search extension provides tokenization, stemming, stopword handling and BM25 retrieval.

It can create an index using `PRAGMA create_fts_index`, then expose a generated `match_bm25` function for ranked querying.

This functionality can combine lexical search scores with other SQL filters and relational metadata.

A consequential limitation is that FTS indexes are not automatically updated when the source table changes. They require explicit refresh or rebuilding when the underlying data is modified.

It is therefore closer to an analytical search index than a continuously maintained search-service index.

Reference: `https://duckdb.org/docs/2.0/core_extensions/full_text_search`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 12.3 Vector search and HNSW

The `vss` extension adds HNSW indexing over supported fixed-size array columns.

This is distinct from the new native `NEAREST` join syntax:

- `NEAREST` is an SQL join capability that expresses nearest-neighbor relationships.
- HNSW is an approximate indexing structure intended to accelerate supported vector-similarity queries.

The HNSW implementation remains explicitly experimental.

Persistent HNSW indexes are disabled by default because custom-index WAL recovery is incomplete. Enabling experimental persistence can create corruption or recovery risks after unexpected shutdowns; the official documentation advises against using it in production.

Reference: `https://duckdb.org/docs/2.0/core_extensions/vss`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 12.4 New default extensible SQL parser

DuckDB 2.0 makes its PEG-based SQL parser the default, replacing the older PostgreSQL-derived parser.

The new parser is designed to be extensible at the grammar level, allowing extensions to define additional SQL syntax rather than limiting them to existing function and statement constructs.

This is important for domain-specific languages and integrations whose native operations do not map cleanly to ordinary SQL function calls.

The PEG parser began as an opt-in feature in DuckDB 1.5. The 2.0 release makes it the default.

Compatibility fallback is available through the `legacy_parser` extension and `enable_legacy_parser` setting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 12.5 C API v2

DuckDB 2.0 expands the native extension interfaces with a revamped C API v2.

It provides broader access to mechanisms including file systems, table functions and other engine extension points.

The longer-term architectural opportunity is that sophisticated capabilities can be implemented once in a native extension and exposed consistently through Python, CLI, R and other DuckDB clients.

This can be preferable to implementing separate Python-specific integrations for each client environment.

Stability qualification: C API v2 is released in DuckDB 2.0 but has not yet been declared stable. Its availability should not be interpreted as a finalized long-term ABI guarantee.

Reference: `https://duckdb.org/docs/2.0/clients/c/overview`

### 12.6 Custom signed extension repositories

A new DuckDB 2.0 feature allows private extension repositories.

The mechanism supports:

- Declaring repository names and URL prefixes.
- Hosting repositories on local filesystems, HTTP(S) or compatible remote storage.
- Trusting signing keys rather than blindly loading arbitrary extension binaries.
- Pinning public-key fingerprints.
- Signing extensions using RSA keys.
- Auditing configured repositories with `duckdb_extension_repositories()`.

For example:

```
SET allow_extension_repositories = 'allowed';

CREATE EXTENSION REPOSITORY internal
WITH PREFIX 'https://extensions.example.org';

INSTALL AND LOAD custom_extension FROM internal;
```

The feature is explicitly marked work-in-progress, with syntax subject to change.

The repository trust mechanism also differs from DuckDB's default built-in extension repositories, which are managed by the project.

Reference: `https://duckdb.org/docs/2.0/extensions/extension_repositories`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 12.7 Extension versioning and compatibility

DuckDB extensions can have separate versions from the engine.

Core extensions may follow stable, prerelease or unstable versioning conventions. Extensions can also be installed from the `core_nightly` repository or pinned to explicit versions when available.

The extension binaries remain tightly bound to specific DuckDB engine builds, making engine and extension compatibility an independent consideration.

Useful SQL interfaces include:

```
SELECT extension_name, installed, loaded, extension_version
FROM duckdb_extensions();

UPDATE EXTENSIONS;
```

DuckDB can automatically install and load supported extensions upon first use, but that behavior depends on configuration, platform and repository accessibility.

Reference: `https://duckdb.org/docs/2.0/extensions/versioning_of_extensions`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



## 13. Operational behavior, observability and security boundaries

### 13.1 Principal configuration dimensions

DuckDB 2.0 exposes extensive runtime configuration through SQL and Python connection settings.

| Setting                         | What it controls                                            |
| ------------------------------- | ----------------------------------------------------------- |
| `threads`                       | Query execution parallelism                                 |
| `async_threads`                 | Concurrency of asynchronous blocking I/O                    |
| `memory_limit`                  | Buffer-manager memory limit                                 |
| `max_temp_directory_size`       | Spill-directory capacity                                    |
| `temp_directory`                | Location of temporary storage                               |
| `preserve_insertion_order`      | Whether eligible operations attempt to preserve input order |
| `max_execution_time`            | Per-query wall-clock timeout, new in 2.0                    |
| `operator_memory_limit`         | Intermediate-operation memory constraints                   |
| `parquet_metadata_cache`        | Caching of external Parquet metadata                        |
| `read_ahead_depth`              | Asynchronous read-ahead behavior                            |
| `enable_profiling`              | Query profiling                                             |
| `profiling_output`              | Profiling destination                                       |
| `storage_compatibility_version` | New database file format compatibility                      |
| `allow_extension_repositories`  | Permission to register private extension repositories       |
| `enable_external_access`        | Whether queries may access external resources               |

The key principle is that these settings manage different resource domains. Query execution threads, I/O threads, buffer-manager memory, externally allocated memory and spill capacity cannot be treated as interchangeable controls.

Reference: `https://duckdb.org/docs/2.0/configuration/overview`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 13.2 Determinism, ordering and reproducibility

DuckDB is a relational execution engine, so results are not inherently ordered without an explicit `ORDER BY`.

Certain operations may preserve insertion order under documented conditions, but optimizations, parallelism, joins and aggregations can change physical row order.

Order-sensitive aggregates and floating-point reductions can also exhibit differences arising from evaluation order.

For numerical reproducibility, it is important to distinguish:

- Deterministic relational result sets.
- Deterministic row ordering.
- Bitwise-identical floating-point results.
- Stable execution plans.
- Stable external-source snapshots.

These are separate guarantees.

Reference: `https://duckdb.org/docs/2.0/operations_manual/non-deterministic_behavior`

### 13.3 SQL introspection and agent-oriented tooling

DuckDB offers useful schema discovery and metadata functions, including `duckdb_tables()`, `duckdb_columns()`, `duckdb_functions()`, `duckdb_extensions()`, `duckdb_settings()` and the standard `information_schema` views.

The CLI receives an important 2.0 addition: agent mode.

It provides compact Markdown table output, explicit result limits, structured JSON errors on stderr, query-progress information, compact plans and cost estimates, and an order-independent result hash where appropriate.

Agent mode can be enabled with the CLI's `-agent` flag or through recognized execution environments.

This is a CLI output mode, not a transformation of Python's `DuckDBPyConnection` return types. An agent using the Python package directly should use its native DB-API, relation, schema and Arrow interfaces.

Reference: `https://duckdb.org/docs/2.0/clients/cli/agent_mode`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 13.4 Security model

DuckDB's native security model is fundamentally different from a server database with independently authenticated SQL users.

DuckDB runs inside a host process and inherits that process's privileges. The engine is not designed to be an isolation boundary for arbitrary untrusted SQL or untrusted data files.

SQL can access files, initiate network requests, install extensions and consume significant system resources, subject to configuration and operating-system permissions.

Therefore:

- Parameter binding reduces SQL-injection risk for values but does not turn arbitrary generated SQL into a safe sandbox.
- Database encryption protects supported files at rest; it does not isolate running queries from the host process.
- Quack authentication does not automatically provide fine-grained authorization.
- Extension signing establishes software provenance and trust, not a runtime confinement boundary.
- `SECURE VIEW`, introduced in 2.0, hides certain internal statistics and plan information, but does not establish a complete role-based authorization system.

DuckDB's own security guidance recommends an operating-system sandbox for untrusted SQL execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



References:

`https://duckdb.org/security`

`https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview`

`https://duckdb.org/docs/2.0/sql/statements/create_view`

## 14. DuckDB 2.0 Python migration and compatibility reference

The following table consolidates major incompatibilities between DuckDB 1.x and 2.0. It is not an implementation plan; it identifies semantic and API differences that materially affect code written against either version.

| Area                         | DuckDB 2.0 behavior                                                                           |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| Python compatibility         | Python 3.11 or later; free-threaded CPython builds unsupported                                |
| New database files           | Default storage version 69, unreadable by DuckDB 1.x                                          |
| Existing database files      | Older storage format retained when accessed and modified by 2.0                               |
| Arrow results                | Removed DB-API Arrow/Polars convenience methods; relations are the intended interface         |
| Relation reads               | `fetchone()`, `fetchmany()` and `execute()` removed from relation objects                     |
| Relation materialization     | `materialize()` replaces earlier eager relation execution patterns                            |
| Relation iteration           | `iter_rows()` and Arrow readers have distinct memory/streaming semantics                      |
| Arrow batch size             | Default changed from 1,000,000 to 131,072 rows                                                |
| Python expression strings    | Plain strings represent literal values instead of automatically naming columns                |
| Qualified column expressions | `col("table", "column")` instead of treating a dotted string as automatically qualified       |
| Dict conversion              | Non-string dictionary keys produce a `MAP`, rather than a struct with coerced field names     |
| Relation methods             | New names such as `pivot`, `offset` and `drop` may shadow column attribute access             |
| Open DB-API results          | Active results require completion, exhaustion or cancellation before certain connection reuse |
| Concurrent connection use    | Busy connections may raise `ResourceInUseException`                                           |
| Transactions                 | Failed execution in an explicit transaction requires rollback before reuse                    |
| File export                  | Explicit `overwrite=False` prevents replacement instead of permitting it                      |
| Decimal values               | Positive-exponent `Decimal` conversions use corrected numeric scale semantics                 |
| SQL lambdas                  | `lambda x: ...` is the default; legacy `x -> ...` is disabled unless explicitly re-enabled    |
| Arithmetic                   | Integer division/modulo-by-zero behavior changes to errors                                    |
| S3 credentials               | Legacy credentials encoded in object URLs disabled by default                                 |
| SQL parser                   | PEG-based parser becomes the default                                                          |
| Native extensions            | C API v2 expanded but not yet stable                                                          |

A particularly important pair of distinctions is:

1. Relations are reusable query definitions rather than partially consumed result cursors.
2. DB-API results now have a more explicit execution and resource lifecycle.

Code that previously mixed these two interfaces interchangeably requires more attention than a simple API rename.

Python migration guide:

`https://duckdb.org/docs/2.0/clients/python/migration`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Engine and SQL migration guide:

`https://duckdb.org/docs/2.0/operations_manual/migration`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



The upstream release notes also identify continued availability of DuckDB 1.5 through March 2027, while 2.0 receives LTS support. As of release day, the first 2.0 patch release is scheduled for November 18, 2026; that is a planned release, not a currently available version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



## 15. Architectural implications: how the capabilities compose

The most important property of DuckDB is not any individual API. It is the ability to combine powerful relational execution, external data access and Python interoperability without constructing a conventional database service or custom data-processing framework.

Several combinations are especially consequential.

### 15.1 Typed relational processing across Python and storage

The combination of Python relations, the expression API, nested logical types, Arrow ingestion and native SQL execution provides a foundation for typed data transformations.

Python can describe and compose the computation, DuckDB can optimize and execute it, and Arrow can carry the results to another columnar system.

This avoids repeatedly crossing a Python object-processing boundary for intermediate operations.

The approach is particularly effective where operations are naturally relational and data types have well-defined SQL representations. It is less suitable where behavior depends on arbitrary Python objects or imperative side effects that DuckDB cannot express natively.

### 15.2 External-file computation without an ingestion phase

Parquet/CSV/JSON scans, schema reconciliation, remote secrets, pushdown, asynchronous I/O and `COPY` can form a complete file transformation pipeline.

That pipeline can inspect, normalize, filter, join, aggregate and export datasets without requiring all source files to be loaded into persistent DuckDB tables.

Native storage remains useful when the workload benefits from transactions, indexes, repeated scans, compressed persistence or catalog-managed objects.

The choice between external files and native tables is consequently about access patterns and semantics, not simply whether DuckDB can read the file.

### 15.3 Data-quality and schema-management operations

CSV rejects, Parquet schema mapping, explicit casts, `TRY_CAST`, relational validation, constraints, catalog introspection and SQL macros can support comprehensive data-quality workflows.

These mechanisms offer alternatives to writing bespoke parsers and validation loops.

They do not, however, automatically define business-level invariants or ensure that every malformed source record is rejected; validation policies still determine which ambiguities are acceptable.

### 15.4 Stateful analytical workflows

Persistent tables, transaction control, macros, triggers, modifying CTEs, `MERGE`, keyed recursion and catalog introspection create a broader state-management toolkit than is usually associated with an analytical engine.

Of particular interest are:

- Derived tables maintained incrementally by set-based triggers.
- Recursive keyed state updated until convergence.
- Atomic sequences of supported SQL mutations.
- Metadata-driven relational transformations.
- Native storage as a durable working database.

These facilities can reduce custom orchestration code.

Their limits remain important: trigger coverage is incomplete, there is no automatically maintained materialized-view subsystem, and the embedded concurrency model differs from a multiwriter server database.

### 15.5 Federation and lakehouse composition

DuckDB can operate between SQL databases, Python columnar objects and open table formats.

The combined system has several possible execution locations:

- Local DuckDB execution over external scans.
- Remote SQL execution through `CONNECT`.
- Object-store data access through native readers.
- Transactional operations governed by a particular lakehouse catalog.
- Native transactions in DuckDB's own storage.

These boundaries determine where computation occurs, which system controls transactions, and whether data must cross network or memory interfaces.

The practical architectural opportunity is to use DuckDB as a common relational computation layer while leaving transaction ownership with the storage system best suited to each operation.

That is an architectural inference from the documented capabilities, not a guarantee that arbitrary federated operations share one optimizer, transaction boundary or consistency model.

### 15.6 Principal limits to retain in the mental model

| Constraint                    | Why it matters                                                                          |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| Embedded file-writing model   | Independent processes cannot conventionally write the same native database concurrently |
| OLAP-oriented storage         | Point updates and write-heavy OLTP patterns can be less efficient                       |
| External data consistency     | File scans and federated sources do not inherently share one transaction snapshot       |
| Python UDF boundary           | Python callbacks may constrain optimization and increase per-value overhead             |
| Memory accounting             | `memory_limit` does not constrain all process allocations                               |
| Arrow ownership               | Columnar interchange does not guarantee zero-copy execution                             |
| Extension compatibility       | Extension binaries, versions and operational maturity vary                              |
| Experimental HNSW persistence | Crash-recovery guarantees are inadequate for general production reliance                |
| Incomplete Delta mutations    | Native Delta support does not cover its full transactional API                          |
| Quack security                | Default authorization permits any query from an authenticated client                    |
| Storage version 69            | New files cannot be opened by DuckDB 1.x                                                |
| Emerging parser/C APIs        | Extension development interfaces may continue evolving after 2.0                        |

These constraints are not peripheral caveats. They help define which responsibilities DuckDB can take over and which remain with Python, a source database, a lakehouse catalog or surrounding infrastructure.

## 16. Primary-source reference map

The links below are direct, topic-specific entry points intended for deeper investigation. All describe DuckDB 2.0 unless otherwise identified.

| Topic                  | Official source                                                        |
| ---------------------- | ---------------------------------------------------------------------- |
| Release details        | `https://duckdb.org/2026/10/21/announcing-duckdb-200`                  |
| 2.0 feature index      | `https://duckdb.org/docs/2.0/whats_new_in_the_docs`                    |
| Python API             | `https://duckdb.org/docs/2.0/clients/python/overview`                  |
| Relational API         | `https://duckdb.org/docs/2.0/clients/python/relational_api`            |
| Python expressions     | `https://duckdb.org/docs/2.0/clients/python/expression`                |
| Python types           | `https://duckdb.org/docs/2.0/clients/python/types`                     |
| Python conversion      | `https://duckdb.org/docs/2.0/clients/python/conversion`                |
| Python UDFs            | `https://duckdb.org/docs/2.0/clients/python/function`                  |
| Python 2.0 migration   | `https://duckdb.org/docs/2.0/clients/python/migration`                 |
| SQL and joins          | `https://duckdb.org/docs/2.0/sql/query_syntax/from`                    |
| Recursive CTEs         | `https://duckdb.org/docs/2.0/sql/query_syntax/with`                    |
| SQL macros             | `https://duckdb.org/docs/2.0/sql/statements/create_macro`              |
| Variant type           | `https://duckdb.org/docs/2.0/sql/data_types/variant`                   |
| Triggers               | `https://duckdb.org/docs/2.0/sql/statements/create_trigger`            |
| Parquet                | `https://duckdb.org/docs/2.0/data/parquet/overview`                    |
| Export and COPY        | `https://duckdb.org/docs/2.0/sql/statements/copy`                      |
| Async I/O              | `https://duckdb.org/docs/2.0/data/io`                                  |
| Storage format         | `https://duckdb.org/docs/2.0/internals/storage`                        |
| Quack                  | `https://duckdb.org/docs/2.0/quack/overview`                           |
| Quack security         | `https://duckdb.org/docs/2.0/quack/security`                           |
| Lakehouse formats      | `https://duckdb.org/docs/2.0/lakehouse_formats`                        |
| Extensions             | `https://duckdb.org/docs/2.0/core_extensions/overview`                 |
| Extension repositories | `https://duckdb.org/docs/2.0/extensions/extension_repositories`        |
| Extension versions     | `https://duckdb.org/docs/2.0/extensions/versioning_of_extensions`      |
| Performance tuning     | `https://duckdb.org/docs/2.0/guides/performance/how_to_tune_workloads` |
| Configuration          | `https://duckdb.org/docs/2.0/configuration/overview`                   |
| CLI agent mode         | `https://duckdb.org/docs/2.0/clients/cli/agent_mode`                   |
| Engine migration       | `https://duckdb.org/docs/2.0/operations_manual/migration`              |

## Conclusion

DuckDB 2.0.0 moves the platform beyond its original characterization as an embedded analytical SQL engine.

It now combines mature vectorized analytics, programmable relational expressions, first-class Arrow interoperability, increasingly sophisticated native storage, rich nested-data capabilities, lakehouse and remote database integration, a growing extension ecosystem, and an emerging remote SQL deployment model.

The strongest opportunities arise from using these capabilities together rather than treating DuckDB merely as a faster alternative to Pandas or a convenient SQL reader for Parquet files.

The Python package is particularly significant because it exposes these capabilities within a familiar runtime while keeping the main analytical execution in native code. Its relation, expression, type and result interfaces make it possible to construct substantial data-processing systems with comparatively little Python-level execution machinery.

DuckDB 2.0's important qualifications concern transaction ownership, remote security, extension maturity, storage compatibility, memory behavior and the still-evolving client/extension APIs. Preserving those distinctions is essential to understanding both the breadth of what the library can now accomplish and where other systems remain necessary.

This reference is based on the DuckDB 2.0 release announcement and versioned upstream documentation available on October 21, 2026. Code fragments are illustrative; no runtime execution or benchmarks were performed.