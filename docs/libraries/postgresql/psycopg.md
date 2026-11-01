# Psycopg 3 — Comprehensive Python Library Capability Reference

Target version: 3.3.6 (current stable) · Research date: October 20, 2026 · Ecosystem: Python / PostgreSQL / libpq

Psycopg 3 is a PostgreSQL database adapter for Python that provides substantially more than conventional SQL execution. It is a protocol-aware database communication layer with native asynchronous I/O, customizable PostgreSQL type adaptation, high-throughput data transfer, automatic prepared statements, pipeline execution, transaction management, connection pooling, and access to PostgreSQL's underlying libpq client API.

Its architectural significance is that many mechanisms commonly implemented as bespoke database infrastructure—query batching, binary serialization, connection lifecycle management, typed result materialization, nested transactional operations, and asynchronous notifications—are already available as native, composable capabilities.

This reference covers the current Psycopg generation, distributed as the Python package `psycopg`, rather than the older `psycopg2` library.

The current stable release is 3.3.6, published September 18, 2026. The official online documentation currently identifies itself as `3.3.7.dev1`; consequently, this overview targets released 3.3.6 behavior and distinguishes unreleased changes. Psycopg 3.3 introduced significant capabilities, including Python template-string queries, more flexible composite adaptation, and richer result-set navigation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Primary project resources:

- [Official Psycopg 3 documentation](https://www.psycopg.org/psycopg3/docs/?utm_source=chatgpt.com)
- [Release notes and version history](https://www.psycopg.org/psycopg3/docs/news.html?utm_source=chatgpt.com)
- [Upstream source repository](https://github.com/psycopg/psycopg?utm_source=chatgpt.com)
- [PyPI distribution](https://pypi.org/project/psycopg/?utm_source=chatgpt.com)

## 1. Conceptual architecture and capability map

Psycopg sits between Python applications and PostgreSQL's native client/server protocol. It is not an ORM, SQL compiler, migration framework, or general-purpose relational execution engine. Its primary responsibility is to provide efficient, correct, and extensible communication with PostgreSQL while exposing the relevant semantics of the underlying database.

Python application / database abstraction

Direct SQL, SQLAlchemy, typed domain objects, async workflows

DB-API and native Psycopg interfaces

### Psycopg 3

Connections and transactions

Query execution and preparation

Type adaptation and row factories

COPY and pipeline execution

Async I/O and notifications

Connection pooling

libpq / PostgreSQL wire protocol

PostgreSQL server

Execution, types, constraints, MVCC, locks, transactions, storage

### Capability orientation

| Capability family      | Principal native mechanisms                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| SQL execution          | Parameter binding, SQL composition, prepared statements, multiple cursor models                          |
| Bulk data movement     | `COPY FROM`, `COPY TO`, text/binary formats, row and block transfer                                      |
| Execution efficiency   | Pipeline mode, `executemany()`, binary adaptation, statement reuse                                       |
| Type integration       | Dumper/Loader registry, PostgreSQL type metadata, custom composite, enum, range, JSON and array handling |
| Transactions           | Autocommit, isolation configuration, scoped transactions, nested savepoints                              |
| Concurrency            | Thread-safe connections, asyncio, query cancellation, connection-level serialization                     |
| Connection management  | Synchronous/asynchronous pools, null pools, lifecycle callbacks, queueing and statistics                 |
| Result handling        | Row factories, typed results, server-side cursors, streaming, multiple result sets                       |
| PostgreSQL integration | `LISTEN/NOTIFY`, server notices, SQLSTATE exceptions, libpq access                                       |
| Ecosystem integration  | SQLAlchemy dialects, PostgreSQL middleware, custom domain types, observability tooling                   |

An important distinction throughout this reference is that Psycopg exposes several independently selectable execution mechanisms. Prepared statements, pipeline mode, COPY, server-side cursors, asynchronous I/O, and connection pooling optimize different costs and are not interchangeable.

For example, a pool reduces the cost of repeatedly establishing connections, prepared statements reduce repeated parsing and planning, pipeline mode reduces communication round trips, and COPY changes the mechanism by which large datasets cross the PostgreSQL protocol boundary.

Those mechanisms can complement one another, but their combination is constrained by transaction semantics, cursor behavior, protocol requirements, and PostgreSQL server capabilities.

## 2. Installation, runtime architecture, and version requirements

### 2.1 Three implementations of the same adapter

Psycopg provides three implementations of its libpq integration, with a common high-level interface.

| Implementation     | Installation                    | Characteristics                                                                                                             |
| ------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Pure Python        | `pip install psycopg`           | Uses Python `ctypes` to call a separately installed libpq. No extension compilation required; higher Python-level overhead. |
| Locally compiled C | `pip install "psycopg[c]"`      | Cython-based extension linked against system PostgreSQL client libraries.                                                   |
| Precompiled binary | `pip install "psycopg[binary]"` | Distributes the compiled implementation and required client libraries in supported platform wheels.                         |

These are implementation choices, not different PostgreSQL drivers with unrelated functionality.

Psycopg selects an available implementation at import time. The `psycopg.pq.__impl__` attribute reports the selected backend, and `PSYCOPG_IMPL` can force one explicitly.

This distinction matters for performance, dependency management, security updates, and access to newer libpq capabilities. A locally compiled installation can follow the system's libpq version; a binary installation uses its bundled libraries. Conversely, a pure-Python installation avoids extension compilation but is not independent of libpq.

Source: [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html?utm_source=chatgpt.com) · [libpq implementation architecture](https://www.psycopg.org/psycopg3/docs/api/pq.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 2.2 Companion packages and optional functionality

The main adapter and its connection pool are separately distributed.

| Distribution     | Role                                                                |
| ---------------- | ------------------------------------------------------------------- |
| `psycopg`        | Core driver, SQL execution, adaptation, cursor and connection APIs  |
| `psycopg-c`      | Optional compiled extension                                         |
| `psycopg-binary` | Optional binary distribution                                        |
| `psycopg-pool`   | Independent synchronous and asynchronous connection pooling package |

Installation extras allow these to be combined. For example:

```
pip install "psycopg[binary,pool]"
```

As of October 20, 2026, the latest published `psycopg-pool` release is 3.3.3, distinct from the core driver's 3.3.6 release. Pool-specific release numbers in the pool documentation refer to `psycopg-pool`, not necessarily the core package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



### 2.3 Compatibility dimensions

Psycopg 3.3 supports Python 3.10 onward, with Python 3.15 support added in 3.3.6. The project's published feature matrix identifies PostgreSQL 10–18 as its supported server range for Psycopg 3.

However, server compatibility, client-library capability, and Python compatibility are separate dimensions.

For example, pipeline execution requires libpq 14 or later even when the PostgreSQL server itself is compatible with Psycopg. Some cancellation and streaming behaviors additionally depend on libpq 17.

The library exposes runtime capability checks, which are preferable to assuming support based solely on the Python package version.

Sources: [Release notes](https://www.psycopg.org/psycopg3/docs/news.html?utm_source=chatgpt.com) · [Feature comparison](https://www.psycopg.org/features/?utm_source=chatgpt.com) · [libpq capability API](https://www.psycopg.org/psycopg3/docs/api/pq.html?utm_source=chatgpt.com).

## 3. SQL execution, parameter binding, and query composition

One of Psycopg 3's most consequential architectural changes relative to Psycopg 2 is that parameters normally remain separate from SQL text until interpreted by PostgreSQL.

### 3.1 Server-side parameter binding

A conventional query uses DB-API-style placeholders:

```
conn.execute(    "SELECT * FROM measurements WHERE sample_id = %s",    (sample_id,),)
```

Psycopg normally uses PostgreSQL's extended query protocol, passing SQL and parameter values separately.

This has several implications.

Type-aware binding. Python values are converted through the adaptation machinery into PostgreSQL-compatible representations. PostgreSQL receives parameter type information and values rather than a Python-constructed SQL literal string.

Statement reuse. The same query structure can be executed repeatedly with different values, supporting automatic preparation.

Binary transfer. Parameters can be encoded in PostgreSQL binary format without first constructing their text representation.

Predictable SQL composition. Values are not concatenated into query text, reducing injection risks when used correctly.

The Python placeholder syntax remains `%s` or `%(name)s`, not PostgreSQL's `$1` syntax, when using ordinary Psycopg cursors.

The binding mechanism is not universally accepted in every SQL grammar position. Identifiers cannot be passed as ordinary values, and some statements—including many forms of DDL and administrative commands—cannot accept server-side parameters.

Source: [Passing parameters to SQL queries](https://www.psycopg.org/psycopg3/docs/basic/params.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 3.2 Safe composition of dynamic SQL

The `psycopg.sql` module provides a compositional representation of SQL fragments.

| Object            | Purpose                                                         |
| ----------------- | --------------------------------------------------------------- |
| `sql.SQL`         | Constant or explicitly constructed SQL syntax                   |
| `sql.Identifier`  | Properly quoted table, schema, column, or other SQL identifiers |
| `sql.Placeholder` | Parameter placeholders generated programmatically               |
| `sql.Literal`     | Properly adapted values embedded directly in SQL text           |
| `sql.Composed`    | Compound SQL assembled from composable objects                  |

For example:

```
from psycopg import sqlquery = sql.SQL(    "SELECT {cols} FROM {table} WHERE id = %s").format(    cols=sql.SQL(", ").join(        map(sql.Identifier, ["name", "value"])    ),    table=sql.Identifier("measurements"),)conn.execute(query, (record_id,))
```

This separates two operations that need fundamentally different treatment: constructing valid SQL syntax and binding runtime values.

It is useful for dynamic column selections, schema-qualified identifiers, programmatically constructed DDL, generated projections, and generic relational utilities.

The critical safety distinction is that `sql.SQL` does not automatically escape arbitrary SQL fragments. It is appropriate for trusted syntax, while `Identifier` and `Literal` are used for their respective data categories.

Source: [SQL composition API](https://www.psycopg.org/psycopg3/docs/api/sql.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 3.3 Python 3.14 template-string queries — new in Psycopg 3.3

Psycopg 3.3 supports Python's PEP 750 template strings, introduced in Python 3.14.

Unlike an f-string, a t-string preserves the structure of interpolations so that Psycopg can determine how each value should be incorporated into the query.

```
conn.execute(    t"SELECT * FROM samples WHERE sample_id = {sample_id}")
```

The interpolation normally behaves as a bound parameter, not direct text substitution.

This provides a significantly more compact representation of SQL while preserving type adaptation and server-side binding.

Template-string format specifiers select specific behaviors:

| Specifier      | Semantics                                   |
| -------------- | ------------------------------------------- |
| Default / `:s` | Automatically adapted server-side parameter |
| `:b`           | Binary parameter encoding                   |
| `:t`           | Text parameter encoding                     |
| `:i`           | Quoted SQL identifier                       |
| `:l`           | Adapted literal embedded client-side        |
| `:q`           | Trusted SQL fragment or nested template     |

For example:

```
conn.execute(    t"SELECT {column:i} FROM {table:i} WHERE id = {id}")
```

The `:i` expressions produce safely quoted identifiers, while `id` remains a bound parameter.

Nested templates and trusted SQL fragments can be composed to construct conditional predicates. This is especially interesting because it reduces the need for manual placeholder numbering, separate parameter lists, and bespoke query-string assembly.

There are still important boundaries: this is an SQL composition facility, not an SQL abstract syntax tree with semantic validation or a query optimizer. The `:q` pathway must only receive trusted SQL structure, and template strings require Python 3.14 or newer.

Source: [Template string queries](https://www.psycopg.org/psycopg3/docs/basic/tstrings.html?utm_source=chatgpt.com) · [Psycopg 3.3 release](https://www.psycopg.org/articles/2025/12/01/psycopg-33-released/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 3.4 Cursor classes represent different protocol strategies

Psycopg exposes distinct cursor types along two mostly independent dimensions: where parameters are bound and where query results are retained.

| Cursor            | Parameter binding | Result storage | Distinguishing purpose                                          |
| ----------------- | ----------------- | -------------- | --------------------------------------------------------------- |
| `Cursor`          | Server            | Client         | Standard execution; preparation and binary protocol support     |
| `ClientCursor`    | Client            | Client         | SQL requiring client-side substitution or simple query protocol |
| `ServerCursor`    | Server            | Server         | Partial fetching from PostgreSQL server cursors                 |
| `RawCursor`       | Server            | Client         | Native PostgreSQL `$1`, `$2` placeholders                       |
| `RawServerCursor` | Server            | Server         | Native placeholders with server-held results                    |

Each has an asynchronous counterpart.

A `ClientCursor` assembles the query and values before transmission. It can handle statements that cannot accept parameters through the extended query protocol, and it can communicate with interfaces such as the PgBouncer administrative console, which requires the simple query protocol.

The tradeoff is that client-side binding cursors do not support binary parameters/results or prepared statements.

A `RawCursor` is different: it retains server-side binding but accepts PostgreSQL-native placeholders directly. This can be useful for SQL already represented in PostgreSQL parameter syntax without requiring placeholder conversion.

A `ServerCursor` instead addresses result-storage behavior and memory footprint, rather than ordinary parameter syntax.

These distinctions allow database interaction to be selected according to protocol requirements without replacing the adapter.

Source: [Cursor types and execution strategies](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



## 4. Prepared statements and repeated-query execution

Psycopg automatically manages prepared statements on individual database connections.

A prepared statement lets PostgreSQL reuse statement processing across executions rather than repeatedly performing the complete parse/analyze/plan process from scratch. PostgreSQL may still choose between custom and generic plans, so preparation does not imply that a single fixed execution plan will always be reused.

### 4.1 Automatic preparation and cache management

By default, Psycopg prepares a statement after repeated execution on the same connection.

The main controls are:

| Control                  | Behavior                                                                         |
| ------------------------ | -------------------------------------------------------------------------------- |
| `prepare_threshold`      | Number of executions before automatic preparation; default 5                     |
| `prepare=True`           | Request preparation on the current execution                                     |
| `prepare=False`          | Suppress preparation for this execution                                          |
| `prepare_threshold=None` | Disable automatic prepared statements on the connection                          |
| `prepared_max`           | Bound on the prepared-statement cache, managed with least-recently-used eviction |

Preparation is implemented through PostgreSQL protocol operations rather than ordinary SQL `PREPARE` and `EXECUTE` commands.

A major architectural benefit is that query reuse can be managed by the driver rather than by a custom statement cache. This is particularly useful when workloads execute a bounded family of parameterized statements repeatedly.

However, highly dynamic query text can decrease cache reuse and increase preparation overhead. Preparation may also have different advantages depending on the query-planning cost and the effectiveness of PostgreSQL's custom versus generic plans.

### 4.2 Interaction with connection pooling

Prepared statements are associated with PostgreSQL server sessions, not globally with a database.

A pool of multiple physical connections therefore has separate preparation state on each connection.

Transaction-pooling middleware introduces another consideration: a logical client connection may not retain the same backend server session.

Psycopg documents compatibility with PgBouncer prepared statements subject to specific conditions, including PgBouncer 1.22 or newer, a positive `max_prepared_statements` configuration, and suitable client libpq support. Without compatible middleware behavior, automatic preparation should be disabled or separately configured.

The important general distinction is that a driver's prepared-statement cache cannot be evaluated independently of the session lifecycle established by the connection infrastructure.

Source: [Prepared statements and PgBouncer interoperability](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



## 5. Pipeline mode and batch execution

Pipeline mode is one of Psycopg's most important performance-oriented mechanisms.

Ordinary query execution is generally request/response-oriented: send a query, await its response, then send another query.

Pipeline mode allows multiple protocol commands to be sent before their individual responses have been received.

### 5.1 The underlying optimization

Conventional sequential execution

Pipelined execution

Conceptual illustration: the reduction is in client/server waiting and coordination, not in the amount of SQL execution required.

Psycopg exposes pipeline mode through `Connection.pipeline()` and the equivalent asynchronous interface.

```
with conn.pipeline():    for record in records:        conn.execute(            "INSERT INTO samples (id, value) VALUES (%s, %s)",            (record.id, record.value),        )
```

This can substantially reduce latency for many small, independent operations, particularly when the network has meaningful round-trip time.

The PostgreSQL server still executes commands in order. Pipeline mode does not transform a single database connection into multiple parallel server workers.

### 5.2 Relationship to `executemany()`

Since Psycopg 3.1, `executemany()` uses pipeline mode internally when supported by the client library.

Consequently, an explicit pipeline block is unnecessary merely to benefit from pipelined repeated execution of one parameterized statement.

Explicit pipeline contexts are valuable when a series of different statements should be transmitted and synchronized together.

The distinction between pipeline execution and bulk data operations matters:

| Mechanism         | Workload shape                                           | Primary benefit                                                              |
| ----------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `execute()`       | Individual query                                         | General SQL execution                                                        |
| `executemany()`   | Repeated statement with many parameter sets              | Reduces repeated execution overhead, automatically pipelines where supported |
| Explicit pipeline | Multiple statements sent without awaiting every response | Reduces latency and coordination                                             |
| `COPY`            | Large homogeneous data transfer                          | Uses a specialized bulk transfer protocol                                    |

### 5.3 Synchronization and failure semantics

Pipeline mode introduces a materially different timing model for errors.

An execution may be queued successfully but fail later when responses are processed. Synchronization boundaries determine when pending results and errors become visible to the client.

If a statement fails, subsequent statements before the next synchronization point may be skipped, producing `PipelineAborted` errors.

This requires careful reasoning about transaction boundaries, failure recovery, and the distinction between submitting an operation and knowing its outcome.

Pipeline mode also has substantive limitations. It does not support COPY, server-side cursors, or `Cursor.stream()`, and it does not allow multiple SQL statements within a single pipeline query operation.

Status: The Psycopg documentation explicitly labels pipeline mode experimental, including in the 3.3 documentation. It requires libpq 14 or newer and has more complex error and concurrency behavior than ordinary request/response execution. It should therefore not be represented as an unconditional substitute for standard querying.

Sources: [Pipeline mode](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html?utm_source=chatgpt.com) · [Cursor batch execution API](https://www.psycopg.org/psycopg3/docs/api/cursors.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 6. COPY: native high-throughput data movement

Psycopg supports PostgreSQL's COPY protocol, which is especially important for ingesting or exporting large amounts of relational data.

Unlike repeated SQL inserts, COPY is a PostgreSQL-native transfer operation with its own protocol handling.

### 6.1 Row-oriented COPY

Psycopg provides Python-level row adaptation during a COPY operation.

```
with conn.cursor() as cur:    with cur.copy(        "COPY measurements (id, value) FROM STDIN"    ) as copy:        for record in records:            copy.write_row((record.id, record.value))
```

This allows arbitrary Python iterables to be loaded without constructing individual SQL statements or manually serializing PostgreSQL's text COPY representation.

The adaptation machinery converts values to their PostgreSQL representations.

One important limitation is that row-oriented `write_row()` usage cannot be combined with COPY options such as `FORMAT CSV`, `DELIMITER`, or `NULL` that are intended for an already-formatted input stream.

### 6.2 Block-oriented COPY

For data already in a PostgreSQL-compatible format, the `Copy.write()` and `Copy.read()` interfaces support blocks of bytes or text.

This can avoid the cost of converting each row to Python objects and then back into PostgreSQL's transfer representation.

It is suitable for transferring PostgreSQL COPY output to files, object storage streams, transport buffers, or another PostgreSQL connection, provided the stream format and destination schema are compatible.

Unlike row-oriented adaptation, block-oriented COPY can use options such as `FORMAT CSV` and `FORMAT BINARY`.

### 6.3 Binary COPY and strict type compatibility

PostgreSQL binary COPY avoids much text serialization and parsing, but its contract is stricter than ordinary SQL parameter execution.

The database does not perform the usual implicit casting on binary COPY fields. A Python integer may be serialized as a narrow PostgreSQL integer type, which can be incompatible with the exact binary representation required by the destination column.

Psycopg's `Copy.set_types()` allows the expected PostgreSQL column types to be specified explicitly, making binary adaptation more predictable.

For `COPY TO`, PostgreSQL does not provide sufficient per-column type metadata for ordinary row adaptation. Without type declarations, received row values may remain strings or bytes.

Calling `set_types()` before reading allows Psycopg to apply appropriate loaders.

This is particularly significant when constructing reusable database export/import components, because it differentiates a typed row transfer from an opaque formatted byte stream.

### 6.4 Asynchronous COPY and extensible writers

`AsyncCopy` provides the corresponding asynchronous operations, including asynchronous iteration, reading, and writing.

The COPY API also supports writer abstractions, permitting handling of COPY output through alternative destinations rather than only the underlying database connection.

This creates useful integration possibilities with streaming I/O, file systems, and data-transfer pipelines.

Psycopg does not itself transform COPY output into an Apache Arrow table or Parquet file. Such conversions belong to adjacent libraries or application code. The potential efficiency advantage of block-oriented COPY depends on whether an intermediate format conversion is required.

### 6.5 Transactional semantics

COPY participates in PostgreSQL's ordinary transaction system. Imported rows are not automatically committed merely because the COPY operation finishes successfully, unless autocommit behavior applies.

An exception inside a COPY context interrupts that COPY operation. Ordinary transaction rollback behavior still determines the fate of the wider transaction.

Sources: [COPY guide](https://www.psycopg.org/psycopg3/docs/basic/copy.html?utm_source=chatgpt.com) · [COPY and AsyncCopy API](https://www.psycopg.org/psycopg3/docs/api/copy.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 7. PostgreSQL type adaptation and extensibility

Psycopg's adaptation system is one of its deepest architectural components.

Rather than treating all database values as strings requiring application-level parsing, Psycopg provides a configurable bidirectional mapping between Python objects and PostgreSQL types.

The system encompasses built-in Python types, PostgreSQL-specific structures, user-defined database types, text and binary wire representations, and custom Python domain objects.

### 7.1 The Dumper/Loader model

Psycopg separates adaptation into two complementary operations.

Dumpers convert Python objects into the text or binary representation expected by PostgreSQL. Loaders convert PostgreSQL results into Python objects.

The major supporting interfaces are:

| Component       | Responsibility                                                |
| --------------- | ------------------------------------------------------------- |
| `Dumper`        | Convert a Python value to PostgreSQL-compatible bytes or text |
| `Loader`        | Decode a PostgreSQL value using its type and format           |
| `AdaptersMap`   | Register and resolve suitable dumpers and loaders             |
| `AdaptContext`  | Associate adaptation rules with a scope                       |
| `Transformer`   | Coordinate the conversion process                             |
| `TypeInfo`      | Represent PostgreSQL type identity and catalog metadata       |
| `TypesRegistry` | Maintain known PostgreSQL type descriptions                   |

Dumpers and loaders can be specialized according to PostgreSQL type identity and the text or binary format used.

For example, a custom Python data type might have one binary dumper and another text dumper. Both can express the same logical value while offering different serialization costs or compatibility characteristics.

This arrangement provides a way to centralize domain-specific database conversion instead of repeating parsing, casting, and object construction throughout a program.

### 7.2 Scoped adapter registration

Adapter configuration supports multiple levels of scope.

Changes to the global adapter registry affect subsequently created connections. Connections inherit configuration from their adaptation context, and cursors inherit configuration from their connections.

A cursor can also use its own adapter configuration.

This creates a useful hierarchy:

Global adapter registry

Defaults for future connections

Connection adapter registry

Session-specific conversions

Cursor adapter registry

Operation-specific conversions

This can support different data representations for different consumers without requiring globally inconsistent conversion behavior.

For example, one cursor might decode a PostgreSQL value into a specialized numerical object while another uses a more generic representation.

An especially relevant Psycopg 3.3 enhancement allows cursor loaders to be changed after a query result has been returned, giving more flexibility in the timing of result-decoding configuration.

Sources: [Data adaptation configuration](https://www.psycopg.org/psycopg3/docs/advanced/adapt.html?utm_source=chatgpt.com) · [Adaptation interfaces](https://www.psycopg.org/psycopg3/docs/api/adapt.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 7.3 Built-in type families

Psycopg provides adaptation for the major PostgreSQL scalar types and a broad collection of specialized types.

| PostgreSQL family        | Principal Python representations and behavior                                     |
| ------------------------ | --------------------------------------------------------------------------------- |
| Boolean                  | Python `bool`                                                                     |
| Integer                  | Python `int`, adapted to an appropriate PostgreSQL integer/numeric representation |
| Numeric / floating-point | Python numerical types, including `Decimal` for numeric precision                 |
| Character/text           | Python `str`                                                                      |
| Binary data              | `bytes`, `bytearray`, `memoryview` to PostgreSQL `bytea`                          |
| Date/time                | `date`, `time`, `datetime`, `timedelta` with PostgreSQL-specific rules            |
| UUID                     | Python `uuid.UUID`                                                                |
| Arrays                   | Python lists and element-level adaptation                                         |
| JSON / JSONB             | Arbitrary JSON-serializable objects through explicit wrappers                     |
| Network addresses        | Python `ipaddress` types                                                          |
| Enumerations             | Python `Enum` classes                                                             |
| Ranges/multiranges       | Psycopg `Range` and `Multirange` objects                                          |
| Composite types          | Tuples, named tuples, and configurable Python objects                             |
| Hstore                   | Python dictionaries through registered adapters                                   |

The exact mapping depends on type registration and PostgreSQL metadata. Not every family is automatically adapted in both directions without configuration.

#### Important numerical and temporal semantics

Python integers do not map to one fixed PostgreSQL integer type. Psycopg can select different compatible representations based on value magnitude.

This is helpful for ordinary parameter binding but becomes significant with binary COPY, where the receiving field requires an exact binary type representation.

PostgreSQL dates and timestamps have a wider representable range than Python's standard `datetime` objects. PostgreSQL's `infinity` and `-infinity` are not transparently mapped to Python's maximum and minimum dates.

By default, unsupported date/time values produce conversion errors rather than silently collapsing distinct PostgreSQL values into one Python value. Custom loaders can implement alternative representations.

Psycopg also documents limitations around text-format loading under PostgreSQL `DateStyle` and `IntervalStyle` settings. Binary temporal decoding avoids some of those text-format dependencies.

These distinctions matter for systems requiring lossless temporal representation or exact cross-language round-tripping.

Source: [Built-in Python and PostgreSQL type adaptation](https://www.psycopg.org/psycopg3/docs/basic/adapt.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 7.4 JSON and JSONB adaptation

Psycopg offers `Json` and `Jsonb` wrappers to explicitly identify Python objects intended for PostgreSQL JSON storage.

```
from psycopg.types.json import Jsonbconn.execute(    "INSERT INTO events (payload) VALUES (%s)",    (Jsonb({"event": "completed", "count": 12}),),)
```

The explicit wrapper is important because a Python dictionary or list could legitimately represent several different PostgreSQL types.

Default JSON conversion uses Python's standard `json` module.

The functions `set_json_dumps()` and `set_json_loads()` allow replacement of the serializer and deserializer at global, connection, or cursor scope.

That makes it possible to integrate other JSON libraries and specialized serialization policies without duplicating conversions at every query site.

However, this mechanism is not a schema validation system. JSON serialization, PostgreSQL JSONB storage, and application-level structural validation remain distinct responsibilities.

### 7.5 PostgreSQL arrays

Psycopg maps PostgreSQL arrays to Python lists and supports element-level type adaptation.

This allows PostgreSQL array operators and predicates to operate directly on parameters constructed from Python collections.

For example:

```
conn.execute(    "SELECT * FROM measurements WHERE id = ANY(%s)",    ([10, 20, 30],),)
```

This is preferable to trying to pass one list as the contents of an SQL `IN` clause, which is not valid under the ordinary server-side binding model.

`ANY()` also handles empty arrays without constructing invalid `IN ()` syntax.

The conversion rules require attention to homogeneity and subtype inference. PostgreSQL array types have an element type, and arbitrary mixed Python lists are not automatically equivalent to heterogeneous database arrays.

### 7.6 Composite types

PostgreSQL composites are particularly interesting from a domain-model perspective.

They can represent typed records inside PostgreSQL, including standalone composite types and table row types.

Psycopg provides `CompositeInfo` and `register_composite()` for mapping those database types into Python objects.

Conceptually, this allows a database-defined record:

```
CREATE TYPE measurement AS (
    value double precision,
    unit text
);
```

to be associated with a Python representation such as a named tuple, dataclass, or other configured object.

Psycopg 3.3 expanded the composite adaptation model to support objects that are not simply sequences, including objects constructed with keyword arguments.

That substantially increases the usefulness of native PostgreSQL composites for structured domain values.

The relationship is bidirectional: configured Python objects can be serialized to PostgreSQL composite values, and PostgreSQL composite results can be materialized as Python objects.

This is not equivalent to an ORM mapping. The mechanism converts one PostgreSQL value whose type is composite; it does not manage object identity, relationships, or persistence lifecycles.

### 7.7 Enumerations

`EnumInfo` and `register_enum()` allow PostgreSQL enum types to map directly to Python enum classes.

Mappings between PostgreSQL labels and Python members can be configured explicitly.

This is particularly valuable where database constraints and Python representations should share semantic identity, because application code can receive enum objects rather than interpreting arbitrary strings.

It also introduces a schema lifecycle consideration: a database enum can evolve independently of the Python class, so application-level synchronization or regeneration of enum definitions may still be necessary.

### 7.8 Range and multirange types

Psycopg exposes `Range` and `Multirange` objects for PostgreSQL's native range families.

Ranges preserve semantics that ordinary Python tuples do not express explicitly: inclusive or exclusive bounds, unbounded endpoints, and empty ranges.

Multiranges represent collections of ranges and support PostgreSQL multirange serialization.

Relevant interfaces include `RangeInfo`, `MultirangeInfo`, and their registration functions.

Custom range types can be registered by obtaining their metadata from PostgreSQL's system catalogs.

These features make it possible to work with PostgreSQL's interval-style relational operators without inventing separate serialization formats.

The server remains responsible for range normalization and the associated database semantics.

### 7.9 User-defined types and type metadata

`TypeInfo.fetch()` queries PostgreSQL's catalogs for type identifiers and related metadata, including array type OIDs.

Registering this metadata can allow Psycopg to recognize arrays of a custom type, while a corresponding custom loader determines the Python representation of each element.

This is a powerful composition point:

Custom scalar adaptation + PostgreSQL type metadata → support for higher-order PostgreSQL structures containing that type.

For sophisticated typed database interfaces, this can replace substantial amounts of repetitive conversion logic.

The adaptation system does not create or migrate the PostgreSQL type definition. Type lifecycle management remains a separate concern.

Sources: [Other PostgreSQL types](https://www.psycopg.org/psycopg3/docs/basic/pgtypes.html?utm_source=chatgpt.com) · [Type metadata and registry API](https://www.psycopg.org/psycopg3/docs/api/types.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



## 8. Row factories, typed result materialization, and static typing

Psycopg distinguishes value decoding from row materialization.

Type adapters determine what Python value corresponds to each PostgreSQL field. A row factory determines how those decoded field values are assembled into a result object.

### 8.1 Built-in row factories

| Factory                | Materialization                                      |
| ---------------------- | ---------------------------------------------------- |
| `tuple_row`            | Plain Python tuple                                   |
| `dict_row`             | Dictionary keyed by column names                     |
| `namedtuple_row`       | Named tuple supporting attribute-style access        |
| `scalar_row`           | First column as a scalar                             |
| `class_row(Class)`     | Class constructed from column-name keyword arguments |
| `args_row(callable)`   | Callable receiving positional field arguments        |
| `kwargs_row(callable)` | Callable receiving keyword field arguments           |

`scalar_row` is a convenient example of reducing custom code: queries intended to produce scalar values do not require repeated extraction of the first tuple element.

`class_row()` can construct dataclasses or compatible domain objects directly.

```
from dataclasses import dataclassfrom psycopg.rows import class_row@dataclassclass Measurement:    id: int    value: floatwith conn.cursor(    row_factory=class_row(Measurement)) as cur:    cur.execute(        "SELECT id, value FROM measurements"    )    measurements = cur.fetchall()
```

The field names and constructor signature must be compatible.

### 8.2 Custom row factories

The factory system has two stages.

A `RowFactory` receives cursor metadata after a query is executed. It returns a `RowMaker`, which constructs an object for each sequence of decoded values.

This arrangement allows column metadata and construction logic to be prepared once per result set rather than recalculated for every row.

Custom factories can implement domain-specific object creation, selective materialization, validation hooks, or alternative lightweight result structures.

There is a performance tradeoff: dictionary construction, dataclass initialization, and validation can cost more than returning plain tuples. The preferable representation depends on whether downstream conversion would otherwise be necessary.

### 8.3 Generic typing

Psycopg has type annotations that propagate row-factory return types through connections and cursors.

A connection configured to produce dictionary rows can be represented differently by a static type checker from one producing tuples or domain objects.

The pooling classes also have generic typing support for their connection classes.

Psycopg 3.3 further made cursors true iterators, enabling `next(cur)` and asynchronous `anext(cur)`. This can be useful when an empty result should raise an iteration exception instead of producing the optional return value associated with `fetchone()`.

Static typing is not the same as runtime validation of an arbitrary SQL projection. A generic row type expresses the declared Python interface; Psycopg does not independently prove that a query's returned columns and types match that declaration.

Sources: [Row factories](https://www.psycopg.org/psycopg3/docs/advanced/rows.html?utm_source=chatgpt.com) · [Row factory API](https://www.psycopg.org/psycopg3/docs/api/rows.html?utm_source=chatgpt.com) · [Static typing](https://www.psycopg.org/psycopg3/docs/advanced/typing.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



## 9. Result retrieval, streaming, and cursor lifecycle

Psycopg offers several alternatives for consuming query results, with different resource-lifetime implications.

### 9.1 Ordinary client-side results

With a conventional `Cursor`, executing a query ordinarily transfers the complete result set into client-side cursor state.

Subsequent `fetchone()`, `fetchmany()`, and `fetchall()` calls operate on this stored result.

This provides efficient in-memory iteration after execution but makes large result sets potentially expensive in client memory.

Importantly, repeatedly calling `fetchmany()` on an ordinary client-side cursor does not necessarily mean PostgreSQL is producing only that many rows per network request. The cursor's result-storage strategy is the controlling distinction.

### 9.2 Server-side cursors

`ServerCursor` creates a PostgreSQL server-side cursor, generally backed by a named portal.

Rows can be fetched incrementally rather than transferring the complete result set immediately.

This is useful for processing datasets larger than practical application memory or for reading only a portion of a potentially large result.

The costs include additional server-side state, cursor lifetime management, and potentially more network operations.

Cursor lifetime interacts with PostgreSQL transactions: ordinary server cursors are generally bound to a transaction, with holdability options affecting behavior across commits.

Server-side cursors are not implemented for pipeline mode, and their API does not support all ordinary cursor operations.

### 9.3 `Cursor.stream()`

Psycopg also provides a streaming query interface using `Cursor.stream()` and its asynchronous equivalent.

Unlike ordinary client-side result retrieval, it can expose rows as the server produces them.

This is conceptually different from a named server-side cursor: streaming uses an active query result flow rather than a PostgreSQL cursor that can be fetched and navigated independently.

Streamed query execution can be useful for latency-sensitive consumption of large results.

The precise available chunking behavior depends on libpq capabilities; Psycopg documents an additional size-based stream mode requiring libpq 17.

Streaming also imposes connection lifecycle constraints: an in-progress result cannot simply be treated as an inert, completely materialized object.

### 9.4 Multiple result sets

Psycopg supports multiple result sets from compatible multi-statement or batch operations.

`nextset()` provides traditional result-set advancement.

Psycopg 3.3 added `Cursor.set_result()` and `Cursor.results()` to navigate results from supported `execute()` and `executemany()` operations more explicitly.

This is useful for commands that intentionally return several result sets, and for batch execution with `RETURNING`.

However, support for multiple result sets does not remove the extended query protocol restriction against binding parameters to several semicolon-separated SQL statements in one prepared operation.

Sources: [Cursor strategies](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html?utm_source=chatgpt.com) · [Cursor API and result navigation](https://www.psycopg.org/psycopg3/docs/api/cursors.html?utm_source=chatgpt.com) · [Psycopg 3.3 release notes](https://www.psycopg.org/psycopg3/docs/news.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 10. Transactions, savepoints, and distributed transaction support

Psycopg exposes PostgreSQL transaction semantics while providing several higher-level mechanisms to reduce manual transaction management.

### 10.1 Implicit transactions and autocommit

Psycopg connections ordinarily begin a transaction when a statement is executed, even if that statement is a `SELECT`.

This can be surprising for a long-lived connection: without a commit or rollback, the database session may remain idle in transaction.

Such sessions can retain snapshots or locks and interfere with database maintenance or concurrency.

A connection configured with `autocommit=True` avoids implicitly keeping every statement inside a Psycopg-managed transaction.

This can be useful for administrative commands, short independent statements, and notification consumers.

However, autocommit does not make a sequence of statements atomic.

### 10.2 Transaction context managers

`Connection.transaction()` provides explicitly scoped transactional execution.

```
with psycopg.connect(    conninfo, autocommit=True) as conn:    with conn.transaction():        conn.execute(            "UPDATE accounts SET balance = balance - %s "            "WHERE id = %s",            (amount, source_id),        )        conn.execute(            "UPDATE accounts SET balance = balance + %s "            "WHERE id = %s",            (amount, target_id),        )
```

On successful exit, the managed transaction is committed. On exception, it is rolled back.

A key semantic distinction is that a `transaction()` block opened inside an already active transaction cannot independently commit that outer transaction. Psycopg uses savepoints where appropriate.

This behavior lets transactional scopes compose without simply issuing unconditional `COMMIT` statements.

### 10.3 Nested transactions and savepoints

Nested `transaction()` contexts use PostgreSQL savepoints.

This supports a larger unit of work in which some subordinate operation is permitted to fail and roll back without forcing every preceding operation to be discarded.

Savepoints are not independent durable transactions. The enclosing transaction still controls final commitment.

Psycopg 3.3 added explicit transaction status information, enabling inspection of transaction-context state during and after execution.

### 10.4 Isolation characteristics

Psycopg exposes PostgreSQL transaction configuration, including:

| Setting           | Purpose                                              |
| ----------------- | ---------------------------------------------------- |
| `isolation_level` | Select PostgreSQL transaction isolation              |
| `read_only`       | Specify read-only transaction behavior               |
| `deferrable`      | Configure PostgreSQL deferrable transaction behavior |
| `autocommit`      | Control implicit transaction creation                |

Asynchronous connections expose corresponding setter methods.

These settings affect transactions managed by Psycopg, but PostgreSQL still determines the meaning of the isolation guarantees.

Higher isolation levels can lead to serialization failures. Psycopg exposes the database error but does not provide a universally safe automatic retry transaction mechanism.

Retries generally need to encompass the entire logical transaction and account for external side effects.

### 10.5 Two-phase commit

A less commonly recognized capability is Psycopg's support for PostgreSQL two-phase commit.

Available since Psycopg 3.1, the principal interfaces are:

| Method           | Role                                       |
| ---------------- | ------------------------------------------ |
| `xid()`          | Construct a transaction identifier         |
| `tpc_begin()`    | Begin a two-phase commit transaction       |
| `tpc_prepare()`  | Prepare transaction for commitment         |
| `tpc_commit()`   | Commit the prepared transaction            |
| `tpc_rollback()` | Roll it back                               |
| `tpc_recover()`  | Discover recoverable prepared transactions |

Two-phase commit enables coordination across resources where a transaction coordinator manages prepare and commit decisions.

Psycopg also provides transaction identifier handling compatible with PostgreSQL's prepared-transaction naming model.

This is a significant native capability, but it does not make Psycopg a complete distributed transaction coordinator.

The coordinator's durable decision logging, recovery after process failure, timeout policy, and handling of in-doubt transactions remain external responsibilities. PostgreSQL must also permit prepared transactions through its configuration.

Source: [Transaction management and two-phase commit](https://www.psycopg.org/psycopg3/docs/basic/transactions.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 11. Concurrency and native asynchronous operations

Psycopg supports synchronous multi-threaded workloads, native asyncio, and cooperative execution with gevent.

The most important distinction is between concurrent application tasks and parallel PostgreSQL command execution on separate connections.

### 11.1 Thread safety

Psycopg connection objects are thread-safe.

Multiple threads may use separate cursors on a shared connection.

However, this does not imply parallel SQL execution on that connection.

Queries issued through cursors sharing one connection are serialized, and all the cursors share the same PostgreSQL session and transaction.

Consequently, one cursor's transactional error can affect other cursors sharing the connection.

Individual cursor objects are not designed to be shared concurrently between threads.

### 11.2 Native asyncio

`AsyncConnection` and `AsyncCursor` expose asynchronous PostgreSQL operations.

```
import psycopgasync with await psycopg.AsyncConnection.connect(    conninfo) as conn:    async with conn.cursor() as cur:        await cur.execute(            "SELECT id, value FROM measurements"        )        async for record in cur:            process(record)
```

An `AsyncConnection` can be shared by multiple asyncio tasks, with its database operations coordinated and serialized on that connection.

Asynchronous operation is useful for overlapping database waits with other tasks. It does not bypass PostgreSQL's one-command-at-a-time session semantics.

Workloads seeking actual database parallelism generally require multiple physical connections.

Asynchronous COPY, connection pooling, result streaming, and notifications extend the async model beyond ordinary queries.

### 11.3 Connection establishment and name resolution

Since Psycopg 3.1, asynchronous connection establishment includes nonblocking DNS resolution.

This matters because an ostensibly asynchronous driver can still interfere with an event loop if parts of connection establishment perform blocking operations.

Client platform details remain relevant. The Psycopg documentation identifies limitations with Windows' default Proactor event loop and describes the supported alternative.

### 11.4 Gevent integration

Psycopg also supports gevent's cooperative execution model when the appropriate I/O functions are monkey-patched.

This eliminates the need for the `psycogreen` integration historically used with Psycopg 2.

Official gevent support dates from Psycopg 3.1.14.

### 11.5 Cancellation and interruption

Psycopg exposes query cancellation APIs, including `cancel()` and `cancel_safe()`.

The newer safe cancellation mechanism has client-library-dependent behavior, and Psycopg 3.3.6 improved interruption handling when an unresponsive server prevents normal query termination.

Cancellation should not be confused with transaction rollback or an application-level guarantee that a command had no externally observable effects.

The application must still understand the resulting transaction and connection state.

Psycopg connections are also not process-safe. They should not be inherited as active connections across forks or shared across process boundaries.

Source: [Concurrency, asyncio, interruption, and server notifications](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 12. Connection pooling and connection lifecycle management

The companion package `psycopg_pool` provides a substantially more capable pooling system than a basic connection cache.

It manages connection creation, concurrency limits, waiting clients, connection health, replacement, shrinking, lifecycle callbacks, and statistics.

### 12.1 Pool classes

`ConnectionPool` / `AsyncConnectionPool`

Maintain reusable physical connections, with configurable minimum and maximum sizes. Connection creation and maintenance are handled by background workers.

`NullConnectionPool` / `AsyncNullConnectionPool`

Expose the same general acquisition interface without retaining idle connections. They can still enforce concurrency limits and queue requests.

The null-pool distinction is easily overlooked. A null pool is not merely equivalent to calling `connect()` directly: with `max_size` configured, it can act as a concurrency-limiting gateway that admits only a bounded number of active database connections.

This can be useful alongside external connection pooling infrastructure.

### 12.2 Pool lifecycle mechanisms

The most important configuration features are:

| Mechanism              | Purpose                                             |
| ---------------------- | --------------------------------------------------- |
| `min_size`, `max_size` | Control maintained connection population            |
| `timeout`              | Bound acquisition wait time                         |
| `max_waiting`          | Limit the pending request queue                     |
| `max_idle`             | Retire surplus idle connections                     |
| `max_lifetime`         | Replace connections after a configured lifetime     |
| `reconnect_timeout`    | Bound a reconnection attempt period                 |
| `num_workers`          | Configure background maintenance worker count       |
| `configure`            | Initialize a newly created connection               |
| `check`                | Validate a connection before handing it to a client |
| `reset`                | Restore state after a connection is returned        |
| `reconnect_failed`     | Handle prolonged connection-establishment failure   |

The lifecycle callbacks provide substantial extension capability.

For example, `configure` can establish connection-specific settings, initialize custom type adapters, or apply appropriate session state.

`reset` can clean up application-specific session resources before reuse. The callback must leave the connection in an idle transactional state.

`check` can test the physical connection before it is handed to a caller, which is useful when the server or network may have disconnected an idle connection.

The tradeoff is that connection checks add an operation to acquisition latency.

### 12.3 Background creation, backpressure, and elasticity

Pool acquisition ordinarily follows this general sequence:

Connection requested

Available connection

Hand to caller after optional check

No connection available

Queue request; workers may grow pool

Connection returned or new connection ready

Queued client served, subject to timeouts and limits

A notable detail is that new connections are created by pool workers rather than synchronously by the requesting application thread. A waiting client may therefore receive an existing connection returned by another client before a newly requested connection finishes opening.

This is valuable for workloads consisting of many brief database interactions, where connection establishment would otherwise dominate execution time.

However, the pool is not a mechanism for making arbitrary server concurrency free. Increasing connections can increase PostgreSQL backend memory use and contention.

Pool sizing must respect both application demand and database-side capacity.

### 12.4 Pool statistics and monitoring

Psycopg provides `get_stats()` and `pop_stats()` for observing pool behavior.

The available statistics include current pool size, available connections, request counts, queued requests, wait duration, connection creation time, connection failures, and discarded connections.

These measurements can help distinguish database query latency from connection-acquisition latency.

For example, increasing `requests_wait_ms` with high pool utilization indicates potential acquisition contention. High `connections_ms` may indicate expensive connection establishment. Rising `connections_lost` may point toward network interruptions or database-side connection termination.

The documentation cautions that the exact statistics key set is not a permanently rigid interface.

### 12.5 Pool integration with SQLAlchemy — enhanced in 3.3

`psycopg_pool` 3.3 added `close_returns=True`.

This changes a pool-managed connection's `close()` behavior so that it returns the connection to its pool rather than physically closing it.

The feature matters for integration with SQLAlchemy, which ordinarily calls the underlying DB-API connection's `close()` operation as part of its lifecycle.

A SQLAlchemy engine can therefore be configured to use an external Psycopg pool with SQLAlchemy's own `NullPool`, avoiding two independent connection pools managing the same traffic.

This is distinct from SQLAlchemy's normal pooling implementation, which already provides a substantial pool feature set. Which system should own pooling depends on the desired lifecycle and operational characteristics.

Version-specific consideration: Opening an asynchronous Psycopg pool in its constructor is deprecated. Explicit `open()` or asynchronous context-manager lifecycle management is the documented forward-compatible approach.

Sources: [Pool architecture](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com) · [Pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com) · [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+3



## 13. PostgreSQL-specific functionality, diagnostics, and lower-level interfaces

Beyond query execution, Psycopg exposes numerous PostgreSQL-specific capabilities that can eliminate separate protocol integrations.

### 13.1 Asynchronous notifications: LISTEN/NOTIFY

PostgreSQL supports lightweight inter-session event notification through `LISTEN` and `NOTIFY`.

Psycopg exposes notifications as `Notify` objects, including their channel, payload, and originating backend process identifier.

Two consumption mechanisms are available.

Notification generators provide synchronous or asynchronous iteration over incoming notifications. They are useful when a connection is dedicated to receiving database events.

Notification handlers, registered with `add_notify_handler()`, invoke callbacks while normal operations on a connection process server messages.

These have different delivery behavior. Handler notifications may not be processed until the next database operation, whereas a dedicated generator can wait for them.

Autocommit is often appropriate for notification connections because transaction boundaries affect when notifications become visible.

Psycopg's 3.2 releases also refined notification buffering semantics. Mixing notification handlers with the generator is discouraged and produces a runtime warning in current versions.

LISTEN/NOTIFY provides event signaling, not a durable message queue. Persistent event history, replay, and delivery guarantees beyond PostgreSQL's notification semantics require other mechanisms.

Source: [Asynchronous notifications](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 13.2 Server notices and diagnostics

PostgreSQL can send informational messages, warnings, and notices separately from ordinary query results.

`Connection.add_notice_handler()` allows Psycopg to receive these messages.

Callbacks receive a `Diagnostic` object containing available PostgreSQL diagnostic fields.

These can include message severity, primary message text, details, hints, SQLSTATE, schema name, table name, column name, and constraint name.

This gives applications access to useful structured diagnostic information that otherwise may be lost or require parsing server output.

The diagnostic object supplied to a notice callback has a limited lifetime. If information must survive the callback, the relevant values should be copied before returning.

### 13.3 SQLSTATE-aware exceptions

Psycopg implements standard DB-API exception families and more specific exceptions corresponding to PostgreSQL SQLSTATE error codes.

For example:

```
try:    conn.execute("INSERT INTO records ...")except psycopg.errors.UniqueViolation:    handle_duplicate()except psycopg.errors.SerializationFailure:    handle_serialization_conflict()
```

This permits error handling based on database-defined conditions rather than matching text in exception messages.

`psycopg.errors.lookup()` also resolves exception classes from SQLSTATE values or PostgreSQL condition names.

The distinction is consequential because error messages may contain variable parameters or change with localization, whereas SQLSTATE codes are intended for machine interpretation.

For transaction systems, specific error classification enables more reliable distinction between constraint violations, serialization failures, missing objects, unavailable locks, and connection failures.

### 13.4 Connection information and connection string handling

`Connection.info` exposes details about the connected PostgreSQL session.

The related `ConnectionInfo` interface includes information such as server version, backend process identifier, connection status, transaction status, and connection parameters.

The `psycopg.conninfo` module provides `make_conninfo()` and `conninfo_to_dict()`.

These help construct and inspect libpq-compatible connection strings without manually parsing URI syntax or concatenating arbitrary keyword-value sequences.

PostgreSQL connection features such as SSL configuration, service files, timeout settings, application names, and host fallback behavior are primarily provided through libpq and the server environment.

Psycopg exposes access to these mechanisms rather than implementing an entirely separate connection configuration system.

Sources: [Error classes and diagnostics](https://www.psycopg.org/psycopg3/docs/api/errors.html?utm_source=chatgpt.com) · [Connection information](https://www.psycopg.org/psycopg3/docs/api/objects.html?utm_source=chatgpt.com) · [Connection string utilities](https://www.psycopg.org/psycopg3/docs/api/conninfo.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



### 13.5 Direct libpq access

`psycopg.pq` exposes low-level objects wrapping the PostgreSQL client library.

Important examples include `PGconn`, `PGresult`, libpq status enumerations, and capability-checking facilities.

This is a meaningful distinction from drivers that expose only a high-level DB-API abstraction.

Low-level access allows specialized components to inspect PostgreSQL protocol state, query result metadata, and connection capabilities.

The `PGconn.trace()` family can be used for libpq protocol tracing where supported.

The library also exposes the runtime libpq version, which helps determine whether optional protocol capabilities can be used.

In general, direct libpq access is most valuable when the high-level Psycopg API does not expose an operation or when specialized protocol diagnostics are required.

It is not a universal performance shortcut. Bypassing high-level abstractions may require explicit synchronization, resource ownership, error handling, or result decoding.

A crucial distinction is that capabilities can depend on both the libpq version used to build an extension and the libpq version actually loaded at runtime.

Source: [libpq wrapper and capability API](https://www.psycopg.org/psycopg3/docs/api/pq.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



## 14. Ecosystem integration and responsibility boundaries

Psycopg is particularly useful as a foundation for PostgreSQL-oriented systems because it remains compatible with higher-level tooling while providing direct access to database-specific mechanisms.

| Adjacent system              | Integration boundary                                                          |
| ---------------------------- | ----------------------------------------------------------------------------- |
| SQLAlchemy Core              | SQL compilation, schema metadata, expression modeling, engine integration     |
| SQLAlchemy ORM               | Object identity, relationships, persistence lifecycle                         |
| Alembic                      | Schema migration generation and execution using SQLAlchemy                    |
| PgBouncer                    | External connection management and multiplexing                               |
| PostgreSQL                   | SQL semantics, execution plans, MVCC, storage, constraints, indexes           |
| Pydantic/dataclasses         | Application object structure and validation                                   |
| Arrow / Polars / pandas      | Columnar representation and analytical computation                            |
| Custom PostgreSQL extensions | Database-specific types and server functions exposed through SQL and adapters |
| CockroachDB                  | PostgreSQL-protocol-compatible database with differing semantics              |

### 14.1 SQLAlchemy

SQLAlchemy provides a dedicated Psycopg 3 dialect supporting both synchronous and asynchronous operation.

```
from sqlalchemy import create_enginefrom sqlalchemy.ext.asyncio import create_async_engineengine = create_engine(    "postgresql+psycopg://user:pass@localhost/db")async_engine = create_async_engine(    "postgresql+psycopg://user:pass@localhost/db")
```

The appropriate driver interface is selected from the engine type.

SQLAlchemy Core adds a relational expression model and SQL generation capability that Psycopg itself does not attempt to provide.

SQLAlchemy's ORM adds an additional object persistence model.

These layers are complementary: SQLAlchemy generates and coordinates database operations while Psycopg handles the PostgreSQL communication and adaptation layer.

Recent ecosystem development: SQLAlchemy 2.1 changed its default PostgreSQL driver to Psycopg 3. SQLAlchemy 2.0 retains Psycopg 2 as the default for an unqualified `postgresql://` URL. Explicit `postgresql+psycopg://` URLs avoid ambiguity between the two SQLAlchemy release lines.

Source: [SQLAlchemy 2.1 PostgreSQL dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com) · [SQLAlchemy 2.1 migration guide](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation

+2



### 14.2 Alembic

Alembic builds on SQLAlchemy's schema metadata, inspection, and migration infrastructure.

Psycopg provides database connectivity underneath SQLAlchemy's engine and dialect, but it does not independently provide Alembic's migration revision graph, autogeneration, or schema migration lifecycle.

Psycopg's native transaction facilities, custom type handling, and PostgreSQL-compatible SQL execution can support migration operations, but schema evolution remains a responsibility of Alembic or another migration system.

### 14.3 Columnar data and analytical systems

Psycopg provides PostgreSQL-native row and block transfer facilities, not a native Apache Arrow database interface.

For data movement involving Arrow, Polars, or similar analytical libraries, the primary integration choices involve the representation crossing the database boundary.

Row factories can construct Python-level records, which analytical libraries may subsequently convert into their own structures.

COPY offers a potentially more efficient transfer mechanism for larger datasets, particularly where a matching PostgreSQL-compatible stream already exists.

However, using COPY does not automatically provide an Arrow-compatible, zero-copy transfer. PostgreSQL COPY framing, null handling, column encodings, and Arrow buffer layouts differ.

Consequently, the performance of a Psycopg-to-columnar workflow depends on the conversion stage as well as on the PostgreSQL transport mechanism.

### 14.4 CockroachDB compatibility

Psycopg contains a dedicated `psycopg.crdb` module for CockroachDB.

This provides specialized connection classes and type adaptation mappings reflecting CockroachDB's PostgreSQL-compatible protocol but different data model.

`CrdbConnection` and `AsyncCrdbConnection` are the primary specialized connection types.

The integration acknowledges important differences, including unsupported PostgreSQL type families and differences in server-side features.

For example, CockroachDB does not provide PostgreSQL's LISTEN/NOTIFY functionality, and its two-phase commit behavior is different.

This is a useful illustration of Psycopg's extensible connection and type architecture: protocol compatibility can be supported without pretending the underlying databases are semantically identical.

Source: [CockroachDB support](https://www.psycopg.org/psycopg3/docs/api/crdb.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



## 15. Performance mechanisms and architectural tradeoffs

Psycopg exposes several distinct optimization opportunities. The major question is which source of overhead a workload is actually paying.

| Cost or constraint                         | Relevant Psycopg mechanism         | Important qualification                                           |
| ------------------------------------------ | ---------------------------------- | ----------------------------------------------------------------- |
| Repeated connection establishment          | `ConnectionPool`                   | Consumes persistent server connections                            |
| Too many simultaneous connections          | Pool limits / `NullConnectionPool` | Requests may queue and experience backpressure                    |
| Repeated statement parsing/planning        | Prepared statements                | Benefits depend on repetition, query plans, and session retention |
| Repeated network round trips               | Pipeline mode, `executemany()`     | Does not parallelize SQL execution within one server session      |
| Large-volume inserts                       | COPY                               | Requires compatible transfer semantics                            |
| Text serialization overhead                | Binary adapters / binary COPY      | Exact type compatibility and format support matter                |
| Excessive client result memory             | `ServerCursor`, `stream()`         | Different server state and lifecycle characteristics              |
| Unnecessary result-object construction     | `tuple_row`, `scalar_row`          | Less expressive than rich object factories                        |
| Repeated application-level type conversion | Custom adapters and row factories  | Can introduce per-value or per-row overhead                       |
| Network I/O blocking other tasks           | Async interfaces                   | Same-connection SQL execution remains serialized                  |
| Excessively dynamic SQL construction       | `psycopg.sql`, template strings    | Query text variability may reduce statement reuse                 |

### 15.1 Optimization opportunities that compose well

Connection pooling + automatic preparation. Reused physical connections can retain prepared statements, allowing preparation benefits to accumulate across logical operations. Conversely, frequent connection replacement or transaction-pooling middleware may limit those benefits.

COPY + custom adaptation. Row-oriented COPY can ingest Python objects through registered dumpers, reducing bespoke serialization code. For already-formatted data, block-oriented COPY may eliminate even more Python-level processing.

Custom PostgreSQL types + type adaptation + row factories. Native PostgreSQL type definitions can be mapped into Python values and assembled directly into application objects. This can reduce intermediate dictionaries, manual casts, and repetitive field conversion.

Async execution + bounded pooling. Multiple asyncio tasks can make progress while waiting for PostgreSQL, and a pool can regulate the number of physical sessions exposed to the database.

SQL composition + prepared statements. Parameterized SQL with stable query structure can benefit from prepared-statement reuse. Dynamic identifiers and changing query structure should be separated from runtime values where possible.

### 15.2 Opportunities with important tradeoffs

Binary representation is not intrinsically superior for every value or workload. Adaptation overhead, type support, client implementation, and data volumes affect its benefit.

Prepared statements can add overhead for infrequently repeated queries and can be problematic if session affinity is absent.

Pipeline mode reduces waiting but increases the complexity of result synchronization and error propagation.

Server-side cursors reduce immediate client memory requirements but retain server resources and have transactional restrictions.

Rich row factories reduce application code but may allocate more Python objects than a tuple-oriented path.

These are not reasons to avoid advanced capabilities. They are reasons to distinguish what each capability actually optimizes.

## 16. Important limitations and design distinctions

The following distinctions are particularly important when using Psycopg as a foundation for a larger database architecture.

| Distinction                                                         | Consequence                                                                                  |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Thread-safe connection ≠ parallel SQL execution                     | Separate cursors on one connection share a serialized session                                |
| Async execution ≠ parallel execution                                | Async enables concurrent waiting; multiple connections enable independent database execution |
| Client-side result cursor ≠ client-side parameter binding           | These are independent design dimensions                                                      |
| `fetchmany()` ≠ incremental server execution                        | An ordinary cursor may already hold the complete result                                      |
| Prepared statement ≠ permanently cached execution plan              | PostgreSQL still controls plan selection and invalidation                                    |
| Pipeline ≠ distributed batch transaction                            | SQL order, transaction boundaries, and synchronization remain relevant                       |
| Binary representation ≠ universally compatible value                | Binary COPY requires exact type matching                                                     |
| Type adaptation ≠ schema validation                                 | Adaptation handles representation, not general domain correctness                            |
| `row_factory` ≠ ORM                                                 | Result object construction does not imply identity or persistence management                 |
| Null pool ≠ no connection control                                   | Null pools can still limit and queue concurrent requests                                     |
| COPY ≠ Arrow interoperability                                       | An explicit conversion or compatible bridge is generally necessary                           |
| Transaction context ≠ independent nested commit                     | Nested contexts use savepoints or participate in an enclosing transaction                    |
| Two-phase commit API ≠ distributed transaction coordinator          | Durable coordination and recovery policy remain external                                     |
| PostgreSQL-protocol compatibility ≠ PostgreSQL-semantic equivalence | CockroachDB and middleware integrations can differ materially                                |

Two additional operational issues deserve emphasis.

Prepared statements and schema changes: Prepared statements and type adapter registries interact with database schema state. DDL can invalidate prepared plans or alter type definitions. Psycopg includes mechanisms for handling some preparation-state changes, but an arbitrary schema change does not guarantee that every existing connection, custom loader, or long-lived application object remains semantically current.

Connection state leakage: Pooled connections are reused sessions. Session-level state—including settings, temporary resources, prepared statements, and other PostgreSQL objects—must be considered as part of connection lifecycle policy. Transaction rollback alone is not a universal reset of every possible session-level side effect.

## 17. Version-specific developments and feature maturity

The Psycopg 3.3 release family has several changes particularly relevant to advanced use.

| Release | Significant capability or change                                                                                                                 |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 3.1     | Pipeline mode, client-side-binding cursors, CockroachDB support, two-phase commit, enum adaptation, improved batch execution                     |
| 3.2     | Further pooling health-check support, expanded typing, additional cursor and adaptation enhancements                                             |
| 3.3.0   | Python template-string queries, expanded composite adaptation, cursor iterator behavior, enhanced multiple-result navigation, transaction status |
| 3.3.5   | Fixes for prepared-statement tracking, COPY data validation, adaptation, and related correctness issues                                          |
| 3.3.6   | Python 3.15 support, async query overhead improvements, stronger query interruption handling, additional prepared-statement and adaptation fixes |

As of the research date, 3.3.7 is not released. Its current development release notes should not be treated as stable functionality.

Pipeline mode remains labeled experimental by the project even though it has been publicly available since 3.1.

Source: [Psycopg release history](https://www.psycopg.org/psycopg3/docs/news.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 18. Primary-source research map

The following resources provide direct entry points for further technical investigation. Links are grouped by the capability they document.

| Area                                        | Official source                                                                                                                                             |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Installation and packaging                  | [https://www.psycopg.org/psycopg3/docs/basic/install.html](https://www.psycopg.org/psycopg3/docs/basic/install.html?utm_source=chatgpt.com)                 |
| Connection and cursor fundamentals          | [https://www.psycopg.org/psycopg3/docs/basic/usage.html](https://www.psycopg.org/psycopg3/docs/basic/usage.html?utm_source=chatgpt.com)                     |
| Server-side parameter binding               | [https://www.psycopg.org/psycopg3/docs/basic/params.html](https://www.psycopg.org/psycopg3/docs/basic/params.html?utm_source=chatgpt.com)                   |
| Template-string queries                     | [https://www.psycopg.org/psycopg3/docs/basic/tstrings.html](https://www.psycopg.org/psycopg3/docs/basic/tstrings.html?utm_source=chatgpt.com)               |
| SQL composition                             | [https://www.psycopg.org/psycopg3/docs/api/sql.html](https://www.psycopg.org/psycopg3/docs/api/sql.html?utm_source=chatgpt.com)                             |
| Cursor models                               | [https://www.psycopg.org/psycopg3/docs/advanced/cursors.html](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html?utm_source=chatgpt.com)           |
| Prepared statements                         | [https://www.psycopg.org/psycopg3/docs/advanced/prepare.html](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html?utm_source=chatgpt.com)           |
| Pipeline mode                               | [https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html?utm_source=chatgpt.com)         |
| COPY operations                             | [https://www.psycopg.org/psycopg3/docs/basic/copy.html](https://www.psycopg.org/psycopg3/docs/basic/copy.html?utm_source=chatgpt.com)                       |
| COPY API                                    | [https://www.psycopg.org/psycopg3/docs/api/copy.html](https://www.psycopg.org/psycopg3/docs/api/copy.html?utm_source=chatgpt.com)                           |
| Type adaptation architecture                | [https://www.psycopg.org/psycopg3/docs/advanced/adapt.html](https://www.psycopg.org/psycopg3/docs/advanced/adapt.html?utm_source=chatgpt.com)               |
| PostgreSQL type metadata                    | [https://www.psycopg.org/psycopg3/docs/api/types.html](https://www.psycopg.org/psycopg3/docs/api/types.html?utm_source=chatgpt.com)                         |
| Specialized PostgreSQL types                | [https://www.psycopg.org/psycopg3/docs/basic/pgtypes.html](https://www.psycopg.org/psycopg3/docs/basic/pgtypes.html?utm_source=chatgpt.com)                 |
| Row factories                               | [https://www.psycopg.org/psycopg3/docs/advanced/rows.html](https://www.psycopg.org/psycopg3/docs/advanced/rows.html?utm_source=chatgpt.com)                 |
| Static typing                               | [https://www.psycopg.org/psycopg3/docs/advanced/typing.html](https://www.psycopg.org/psycopg3/docs/advanced/typing.html?utm_source=chatgpt.com)             |
| Transactions and two-phase commit           | [https://www.psycopg.org/psycopg3/docs/basic/transactions.html](https://www.psycopg.org/psycopg3/docs/basic/transactions.html?utm_source=chatgpt.com)       |
| Async execution, notifications, concurrency | [https://www.psycopg.org/psycopg3/docs/advanced/async.html](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com)               |
| Connection pool architecture                | [https://www.psycopg.org/psycopg3/docs/advanced/pool.html](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com)                 |
| Pool API                                    | [https://www.psycopg.org/psycopg3/docs/api/pool.html](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com)                           |
| Error classification and diagnostics        | [https://www.psycopg.org/psycopg3/docs/api/errors.html](https://www.psycopg.org/psycopg3/docs/api/errors.html?utm_source=chatgpt.com)                       |
| Connection APIs                             | [https://www.psycopg.org/psycopg3/docs/api/connections.html](https://www.psycopg.org/psycopg3/docs/api/connections.html?utm_source=chatgpt.com)             |
| libpq wrapper                               | [https://www.psycopg.org/psycopg3/docs/api/pq.html](https://www.psycopg.org/psycopg3/docs/api/pq.html?utm_source=chatgpt.com)                               |
| CockroachDB adapter                         | [https://www.psycopg.org/psycopg3/docs/api/crdb.html](https://www.psycopg.org/psycopg3/docs/api/crdb.html?utm_source=chatgpt.com)                           |
| Psycopg release notes                       | [https://www.psycopg.org/psycopg3/docs/news.html](https://www.psycopg.org/psycopg3/docs/news.html?utm_source=chatgpt.com)                                   |
| SQLAlchemy integration                      | [https://docs.sqlalchemy.org/en/21/dialects/postgresql.html](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com)             |
| PostgreSQL libpq pipeline protocol          | [https://www.postgresql.org/docs/current/libpq-pipeline-mode.html](https://www.postgresql.org/docs/current/libpq-pipeline-mode.html?utm_source=chatgpt.com) |

These sources cover both the primary driver and the separately distributed connection-pooling package. The official Psycopg site currently builds documentation from a development revision, so version-specific claims should be checked against the release notes or the corresponding upstream tag where necessary.

## 19. Overall architectural significance

Psycopg's value extends well beyond providing a convenient DB-API implementation.

Three capability combinations are especially important.

First, its PostgreSQL protocol awareness provides multiple ways to change the cost structure of database communication. Prepared statements, pipelining, COPY, streaming, server-side cursors, and binary formats address different sources of overhead. Selecting among them can improve performance without creating a separate query transport or batching framework.

Second, its adaptation machinery provides a direct bridge between PostgreSQL's type system and Python's domain representations. Custom dumpers, loaders, catalog-based type registration, composites, enums, arrays, ranges, and row factories can be combined into a coherent, reusable type boundary. This is substantially more capable than treating database results as generic tuples and performing conversion throughout application code.

Third, its lifecycle and concurrency mechanisms can replace significant bespoke database infrastructure. Connection pools with queues, backpressure, health checking, background maintenance, and statistics integrate with explicit transactions, asynchronous execution, cancellation, and PostgreSQL diagnostics.

Its principal boundary is equally clear: Psycopg is a sophisticated PostgreSQL driver, not a general relational modeling or schema management framework. SQLAlchemy, Alembic, PostgreSQL itself, and columnar data libraries provide capabilities at different layers.

Taken together, Psycopg 3.3 provides a technically rich foundation for both direct PostgreSQL access and higher-level database abstractions. Its most distinctive capabilities are not individual convenience methods, but the ability to combine native PostgreSQL execution mechanisms, strongly controlled type adaptation, and explicit connection lifecycle management into systems that require less custom infrastructure while preserving detailed control over database behavior.

# Psycopg 3.3.6 — Advanced Capability Addendum

Target versions: `psycopg` 3.3.6 · `psycopg_pool` 3.3.3\
Research date: November 1, 2026\
Scope: Supplement to Psycopg 3 — Comprehensive Python Library Capability Reference, covering previously omitted functionality, advanced execution semantics, and version-specific qualifications.

Both target versions are the latest stable releases as of the research date. Current online documentation is generated from a development revision; the additions below concern functionality available in the specified releases unless explicitly identified otherwise.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 1. Dynamic connection configuration and operational pool management

Extends original §§12.2–12.4.

The `psycopg_pool` package provides controls beyond automatic connection creation and recycling. In particular, it supports dynamic configuration of new physical sessions, explicit replacement of existing sessions, runtime resizing, readiness validation, and distinct operational failure signals.

### 1.1 Connection configuration evaluated at creation time

Since `psycopg_pool` 3.3, pool constructor arguments `conninfo` and `kwargs` may be callables rather than static values. They are evaluated for each connection attempt, allowing newly created connections to use current credentials or routing information without reconstructing the pool.

The supported forms differ by pool class:

| Class                 | `conninfo` / `kwargs` providers                                 |
| --------------------- | --------------------------------------------------------------- |
| `ConnectionPool`      | Static values or synchronous zero-argument callables            |
| `AsyncConnectionPool` | Static values, synchronous callables, or asynchronous callables |

This can integrate a pool with a credential provider, service-discovery mechanism, or configuration service. The callable is evaluated when a physical connection is created, not on every acquisition of an existing connection. Consequently, updated connection parameters do not immediately change already-established sessions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 1.2 Explicit connection replacement with `drain()`

`ConnectionPool.drain()`, introduced in `psycopg_pool` 3.3, removes idle connections from the pool and schedules their replacement. Connections currently borrowed by clients remain in use until returned, at which point they are closed instead of being reused.

This provides a controlled session-generation boundary. It can be useful when refreshing connection credentials, reestablishing session configuration, or replacing connections whose adapter registries were initialized using older definitions.

The essential distinction is that dynamic configuration controls what new connections receive, whereas draining controls when existing connections are replaced. Together, they can support connection-state transitions without forcibly interrupting ongoing database operations.

The documented `drain()` API is provided on `ConnectionPool`; it should not be assumed to exist on `AsyncConnectionPool` or the null-pool variants without verification against the installed version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 1.3 Runtime management and readiness controls

Several operational methods deserve explicit treatment:

| API                          | Behavior and significance                                                                                               |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `wait(timeout=...)`          | Waits for the pool's minimum connection population to become ready; closes the pool and raises `PoolTimeout` on failure |
| `resize(min_size, max_size)` | Changes connection-capacity bounds at runtime                                                                           |
| `check()`                    | Tests connections currently held by the pool, replacing failed ones                                                     |
| `check_connection(conn)`     | Static health-check helper, also suitable as an acquisition-time `check` callback                                       |
| `open(wait=True)`            | Opens the pool and combines initialization with readiness waiting                                                       |
| `getconn()` / `putconn()`    | Explicit acquisition/release interface where context managers cannot be used                                            |

Ordinary pools and null pools differ. In particular, `NullConnectionPool.wait()` verifies connectivity by establishing a test connection without retaining it. Operational checks must not be interpreted as guarantees that future acquisitions or queries will succeed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+2



The lifecycle model also distinguishes between acquisition failures:

- `PoolTimeout`: no connection became available before the acquisition deadline.
- `TooManyRequests`: the configured waiting-queue limit was exceeded.
- `PoolClosed`: acquisition was attempted after the pool became unavailable.

All three derive from `OperationalError`. Distinguishing them allows callers to separate queue saturation, waiting-time exhaustion, and administrative shutdown instead of handling every failure as a database connectivity problem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 1.4 Operational logging and version-specific caveats

The `psycopg.pool` logger emits connection lifecycle and acquisition events through Python's standard `logging` infrastructure. These events complement `get_stats()` and `pop_stats()`: statistics provide numerical observations, while logs help inspect the sequence of connection creation, allocation, return, and replacement.

Exact log messages are not a stable machine-readable interface. Monitoring integrations should depend on documented pool metrics or structured instrumentation rather than parsing log text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Two release-specific distinctions matter:

Null-pool reconnection callbacks. In released `psycopg_pool` 3.3.3, `NullConnectionPool` accepts `reconnect_failed` but does not invoke it. The upstream release notes record a correction for unreleased 3.3.4. Additionally, connection attempts made directly for requesting clients are distinct from background reconnection attempts.

Asynchronous pool initialization. Opening an async pool in its constructor is deprecated. The forward-compatible pattern is explicit `await pool.open()` or an asynchronous context manager, rather than relying on constructor-side initialization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



Architectural implication: The pool can own much of the connection-replacement, readiness, bounded-admission, and failure-classification machinery that would otherwise require a separate lifecycle manager. It does not provide atomic credential rotation, guarantee uninterrupted access during database outages, or replace database-side capacity management.

Primary sources:

`https://www.psycopg.org/psycopg3/docs/api/pool.html`

`https://www.psycopg.org/psycopg3/docs/advanced/pool.html`

`https://www.psycopg.org/psycopg3/docs/news_pool.html`

## 2. Deliberate transaction rollback and observable transaction outcomes

Extends original §§10.2–10.3.

Psycopg provides additional transaction-control mechanisms that separate expected application-level rollback from unexpected failures. These are particularly useful in compositional transaction logic, validation operations, and workflows with nested savepoints.

### 2.1 `psycopg.Rollback` as structured control flow

Raising `psycopg.Rollback` inside a `Connection.transaction()` context causes the targeted transaction scope to roll back without propagating an exception beyond the corresponding context block.

With no target, the innermost transaction scope is rolled back. Passing a `Transaction` object allows an inner operation to abort an enclosing scope, including the intervening nested transaction blocks.

```
from psycopg import Rollbackwith conn.transaction() as outer:    perform_first_operation(conn)    with conn.transaction():        if operation_should_be_cancelled():            raise Rollback(outer)        perform_second_operation(conn)# Execution continues here.
```

This differs from simply calling `Connection.rollback()`: the `Rollback` exception integrates with Psycopg's transaction-context management and can target a particular active scope.

It also differs from swallowing an arbitrary database exception. The former represents an intentional decision to discard a scope; the latter may conceal a failed database operation requiring recovery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



### 2.2 `force_rollback=True`

`Connection.transaction(force_rollback=True)` creates a transaction scope that rolls back on normal exit even when no exception occurred.

```
with conn.transaction(force_rollback=True) as tx:    conn.execute(        "UPDATE measurements SET reviewed = true WHERE id = %s",        (record_id,),    )    inspect_provisional_result(conn)assert tx.status == tx.Status.ROLLED_BACK_EXPLICITLY
```

This provides a native mechanism for transactional dry runs, provisional transformations, and tests of database-mediated operations.

The guarantee is rollback of transactional database effects, not general reversal of every consequence. PostgreSQL sequences, external calls, and other nontransactional side effects may persist or otherwise remain observable. A forced-rollback scope should therefore not be treated as a universally side-effect-free sandbox.

The corresponding asynchronous transaction interface accepts the same configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 2.3 Explicit savepoint naming and transaction status

`transaction(savepoint_name=...)` allows a named savepoint to be used when the scope is nested. Normally Psycopg chooses savepoint names automatically, which avoids the need to coordinate them manually.

Explicit naming can be useful for interoperability with other transaction-aware components, although it also introduces the possibility of name collisions or mismatched ownership when several layers manipulate savepoints on one connection.

Psycopg 3.3 additionally exposes `Transaction.status` and `AsyncTransaction.status`. The available states include:

| Status                   | Meaning                                                      |
| ------------------------ | ------------------------------------------------------------ |
| `NON_STARTED`            | Transaction context created but not entered                  |
| `ACTIVE`                 | Context currently active                                     |
| `COMMITTED`              | Context successfully committed                               |
| `ROLLED_BACK_EXPLICITLY` | Rollback requested through `Rollback` or forced rollback     |
| `ROLLED_BACK_WITH_ERROR` | Rollback caused by an exception inside the context           |
| `FAILED`                 | Transaction failed because the connection became unavailable |

The status remains available after the context exits. For nested scopes, it describes the managed scope's outcome; successful release of a savepoint does not mean the outermost transaction has been durably committed.

These status values provide a structured basis for transactional diagnostics and outcome recording without inferring success from control-flow position alone. They do not replace PostgreSQL's connection-level transaction status, nor do they guarantee durability of a transaction whose surrounding context has not committed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



Primary sources:

`https://www.psycopg.org/psycopg3/docs/basic/transactions.html`

`https://www.psycopg.org/psycopg3/docs/api/connections.html`

`https://www.psycopg.org/psycopg3/docs/api/objects.html`

## 3. Additional type-adaptation capabilities and consequential type semantics

Extends original §§7.1–7.4 and §7.9.

### 3.1 Native PostGIS ↔ Shapely geometry adaptation

Psycopg includes an experimental adapter module, `psycopg.types.shapely`, for conversion between Python Shapely geometries and PostgreSQL PostGIS `geometry` values.

The integration is based on PostgreSQL type registration rather than hardcoded geometry type identifiers. Because PostGIS defines its types through a database extension, their OIDs must be discovered from the target database before the adapter can be registered.

```
from psycopg.types import TypeInfofrom psycopg.types.shapely import register_shapelyinfo = TypeInfo.fetch(conn, "geometry")if info is not None:    register_shapely(info, conn)
```

After registration, supported Shapely geometry objects can be passed as PostgreSQL parameters, and returned geometry values are converted into Shapely objects. Text and binary formats are supported.

This creates a native type boundary between spatial SQL and Python's geometry-processing ecosystem, reducing the need for manually converting Well-Known Text or Well-Known Binary at every query site. PostgreSQL and PostGIS remain responsible for spatial predicates, indexes, coordinate transformations, and server-side spatial operations; the adapter primarily handles representation.

Availability and limitations: PostGIS must be installed in the database, Shapely must be installed separately, and registration applies only to the selected adaptation context and subsequently created child contexts. The module is explicitly experimental, so its interface and supported behavior warrant closer version control than stable core adapters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/basic/pgtypes.html`

### 3.2 NumPy scalar adaptation

Since Psycopg 3.2, NumPy boolean, integer, and floating-point scalar values can be dumped directly through the normal parameter-adaptation system.

This is useful when relational writes consume values produced by NumPy operations. Explicitly converting every NumPy scalar into a built-in Python scalar is not generally necessary merely to bind it as a query parameter.

The capability does not establish native serialization of arbitrary NumPy arrays as columnar data or zero-copy exchange of NumPy memory layouts with PostgreSQL. Scalar adaptation, PostgreSQL array adaptation, and bulk/columnar transport remain separate mechanisms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/basic/adapt.html`

### 3.3 Value-dependent dumpers and PostgreSQL type selection

Custom dumpers have a more sophisticated dispatch mechanism than simple Python-class-to-PostgreSQL-type mapping.

`Dumper.get_key(obj, format)` and `Dumper.upgrade(obj, format)` permit selection of a more specialized dumper based on the actual value being serialized. This supports cases in which one Python class can require different PostgreSQL type representations.

Psycopg itself uses value-dependent specialization for operations such as selecting integer widths and adapting collection types.

The relevant mechanism is:

1. Resolve a dumper using the Python object's type and requested serialization format.
2. Obtain a more specific dispatch key where value-dependent specialization is required.
3. Reuse or instantiate the specialized dumper within the query's adaptation context.
4. Serialize values using the associated type identity and text or binary representation.

This can replace bespoke per-query serialization dispatch for domain types whose database representations vary according to their contents.

The adapter interfaces also permit `Dumper.dump()` to return `None`, representing SQL `NULL`. This behavior was introduced in Psycopg 3.2 and enables an adapter to centralize certain absence-to-null conversion policies.

The `Transformer` manages dumpers and loaders at query scope. Its caching and context inheritance mean that a registered dumper is not necessarily reconstructed for every value, although Python-level conversion work still occurs for each value.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



Sources:

`https://www.psycopg.org/psycopg3/docs/advanced/adapt.html`

`https://www.psycopg.org/psycopg3/docs/api/adapt.html`

### 3.4 Integer inference can change query plans

A particularly consequential behavior of Psycopg's integer adaptation is that Python's arbitrary-precision `int` can exceed PostgreSQL's `bigint` range.

When the value is too large for `bigint`, Psycopg can adapt it as PostgreSQL `numeric`. For a comparison against an indexed integer column, PostgreSQL may then cast the column to `numeric`, making the original integer index unusable.

```
# Validate the range before execution, or force the expected SQL type.cur.execute(    "SELECT * FROM measurements WHERE id = %s::bigint",    (record_id,),)
```

An explicit type cast causes an out-of-range value to fail rather than allowing type promotion to produce an unexpectedly expensive query plan.

This is especially important for dynamically generated predicates, identifier lookups, and user-controlled numeric inputs. Such values can affect database workload cost even when parameter binding eliminates SQL injection.

A related point concerns PostgreSQL function dispatch: Psycopg chooses narrow integer types where possible partly because PostgreSQL can widen integer types implicitly in contexts where narrowing is not available. Explicit casts may therefore be necessary to select a particular function signature or preserve expected operator resolution.

Architectural implication: Type adaptation is part of query planning behavior, not merely serialization. A generic database-access layer may require explicit type contracts for indexed identifiers and other performance-sensitive predicates.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/basic/adapt.html`

### 3.5 Reusable adaptation contexts and cursor factories

`Connection.connect(context=...)` accepts an adaptation context, including a configured `AdaptersMap`, whose configuration is copied to initialize a new connection.

This allows a consistent set of domain conversions to be reused across independent connections without mutating the global `psycopg.adapters` registry or repeating registration calls at every query site.

Separately, connections expose `cursor_factory` and `server_cursor_factory`. These configure the concrete cursor types returned by ordinary and named-cursor creation, respectively.

The two mechanisms serve different responsibilities: an adaptation context establishes how values are represented, while cursor factories establish how SQL is executed and results are managed.

Combined with `psycopg_pool.configure`, these facilities provide a natural way to initialize a population of connections with coherent domain-type and cursor behavior. Configuration changes still require attention to inheritance timing: objects created before adapter changes do not necessarily inherit them, which is one reason pool draining can matter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+2



Source: `https://www.psycopg.org/psycopg3/docs/api/connections.html`

### 3.6 Per-value JSON serialization

In addition to the scoped `set_json_dumps()` configuration described in the original reference, both `Json` and `Jsonb` support a `dumps=` argument on the individual wrapper.

```
from psycopg.types.json import Jsonbcur.execute(    "INSERT INTO events (payload) VALUES (%s)",    (Jsonb(event, dumps=custom_serializer),),)
```

The per-object serializer takes precedence over the context's default. Different JSON values in the same statement can consequently use different serialization policies.

This is useful when database operations mix ordinary JSON values with objects requiring specialized encoding, without establishing a new connection or cursor-wide policy.

The customization affects client-side serialization. It does not change PostgreSQL JSONB's storage and normalization semantics or provide runtime schema validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/basic/adapt.html`

### 3.7 Temporal decoding and session timezone identity

Psycopg's PostgreSQL temporal adaptation also exposes a distinction that matters for reproducibility.

PostgreSQL `timestamptz` represents an instant, not a stored timezone identifier. On retrieval, the value is converted into the connection's configured `TimeZone`, and Psycopg uses the associated Python `zoneinfo.ZoneInfo` representation where supported.

The active connection timezone is available through `Connection.info.timezone`.

By contrast, PostgreSQL `timetz` maps to Python `time` values with fixed-offset timezone information, because a time of day without a date cannot independently determine daylight-saving-time behavior.

Thus, the same `timestamptz` value can be returned with different local clock components and timezone objects on different sessions while representing the same instant. For pooled connections, timezone configuration is therefore meaningful session state rather than a purely cosmetic client-side setting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



Source: `https://www.psycopg.org/psycopg3/docs/basic/adapt.html`

## 4. Binary protocol control, statement preparation, and runtime capability detection

Extends original §§3.1, 4.2, 7.1, and 13.5.

### 4.1 Parameter encoding and result encoding are independent decisions

Psycopg permits explicit selection of the wire format used for individual input parameters:

| Placeholder | Encoding behavior                                         |
| ----------- | --------------------------------------------------------- |
| `%s`        | Automatic selection of an available text or binary dumper |
| `%b`        | Require binary parameter adaptation                       |
| `%t`        | Require text parameter adaptation                         |

A request for an unavailable format fails rather than silently using an arbitrary representation.

Result-format selection works differently. `Connection.cursor(binary=True)` and `Cursor.execute(..., binary=True)` request binary results, but PostgreSQL's extended query protocol selects the result format for the complete query result rather than independently for each column.

This has several consequences:

- Every returned PostgreSQL type must support the requested binary output format.
- Psycopg requires suitable loaders to produce decoded Python values; unknown types may instead arrive as raw strings or binary buffers.
- Binary result requests cannot be combined with executing several SQL statements in one query operation.
- Binary parameters do not require binary results, and binary results do not require binary parameters.

The selection of binary format is distinct from the selection of custom dumpers and loaders. The wire representation and the Python object representation are two stages of the same adaptation boundary.

Performance implication: Binary formats can reduce conversion overhead for suitable types, but the benefit depends on transfer size, the installed client implementation, adapter implementation, and downstream object creation. There is no general guarantee that enabling binary results makes all queries faster.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



Source: `https://www.psycopg.org/psycopg3/docs/basic/params.html`

### 4.2 Exact prepared-statement compatibility with PgBouncer

Prepared statement management is especially sensitive to whether a logical connection preserves the identity of a PostgreSQL backend session.

For Psycopg's documented PgBouncer prepared-statement support, the relevant conditions are:

| Component                | Requirement                                                         |
| ------------------------ | ------------------------------------------------------------------- |
| PgBouncer                | Version 1.22 or newer                                               |
| PgBouncer configuration  | `max_prepared_statements > 0`                                       |
| Client libpq             | Version 17+ for the required prepared-statement close functionality |
| Psycopg capability check | `psycopg.capabilities.has_send_close_prepared()`                    |

With an older libpq but a sufficiently recent and configured PgBouncer, Psycopg documents an alternative: set `Connection.prepared_max = None` to disable automatic deallocation of prepared statements.

This distinction is important because `prepared_max=None` does not disable automatic preparation. That is controlled independently by `prepare_threshold=None`.

A transaction-pooling deployment therefore needs to distinguish preparation eligibility, statement cache eviction, and middleware-managed backend statement identity. Treating all three as one setting can produce incorrect compatibility conclusions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/advanced/prepare.html`

### 4.3 Programmatic libpq feature detection

Psycopg provides a dedicated `psycopg.capabilities` object, which is more useful for feature negotiation than relying on a hardcoded libpq version comparison.

| Capability check              | Feature and minimum libpq version            |
| ----------------------------- | -------------------------------------------- |
| `has_pipeline()`              | Pipeline execution; libpq 14+                |
| `has_send_close_prepared()`   | Prepared-statement closure; libpq 17+        |
| `has_cancel_safe()`           | Improved cancellation; libpq 17+             |
| `has_stream_chunked()`        | Chunked `Cursor.stream(size > 1)`; libpq 17+ |
| `has_full_protocol_version()` | Full protocol-version inspection; libpq 18+  |
| `has_set_trace_flags()`       | Configurable libpq tracing flags; libpq 14+  |

These methods normally return booleans. Passing `check=True` causes an unsupported feature to raise `NotSupportedError` with a descriptive explanation.

This provides a reusable feature-negotiation mechanism for components distributed across environments where pure-Python, locally compiled, or bundled libpq implementations may expose different capabilities.

The check reports availability of a client-side capability, not a guarantee that every server version or middleware configuration supports the corresponding operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/api/objects.html`

## 5. COPY serialization and result-preserving batch execution

Extends original §§5.2, 6.4, and 9.4.

### 5.1 Generating COPY-formatted data without a database COPY command

Psycopg's COPY writer architecture supports a less obvious capability: generating PostgreSQL COPY-formatted data for offline transfer.

A `Copy` object can be instantiated directly with a `FileWriter`, without first executing a `COPY FROM STDIN` command on PostgreSQL.

```
from psycopg import Copyfrom psycopg.copy import FileWriterwith conn.cursor() as cur:    with open("measurements.pgcopy", "wb") as f:        with Copy(cur, writer=FileWriter(f)) as copy:            for record in records:                copy.write_row(record)
```

The resulting file contains COPY-formatted data prepared through Psycopg's adaptation machinery. This allows serialization and database ingestion to be separated into distinct operations.

The writer system includes:

| Abstraction        | Responsibility                                                       |
| ------------------ | -------------------------------------------------------------------- |
| `LibpqWriter`      | Default synchronous destination for a live PostgreSQL COPY operation |
| `FileWriter`       | Writes COPY-formatted data to a binary file-like object              |
| `Writer`           | Abstract synchronous destination with `write()` and `finish()`       |
| `AsyncWriter`      | Asynchronous destination interface                                   |
| `AsyncLibpqWriter` | Default asynchronous database destination                            |

A manually created `Copy` can also specify `binary=True`; binary transfer requires accurate PostgreSQL type representations, not merely serializable Python values.

Important boundary: Offline COPY generation avoids executing the database COPY command, but the illustrated API still uses a cursor and its adaptation context. It should not be confused with a completely standalone serializer requiring no Psycopg connection. Generated data must be compatible with the eventual target schema and COPY format.

The native writer interfaces can eliminate bespoke COPY framing and destination-plumbing code for buffered files or specialized streams, while leaving storage transport and schema compatibility to adjacent components.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/api/copy.html`

### 5.2 `executemany(returning=True)` and per-execution results

`Cursor.executemany()` supports an explicit `returning=True` option, introduced in Psycopg 3.1, for repeated commands that produce result sets.

```
with conn.cursor() as cur:    cur.executemany(        "INSERT INTO measurements (value) VALUES (%s) RETURNING id",        [(10.5,), (12.0,), (14.5,)],        returning=True,    )    ids = [cur.fetchone()[0] for _ in cur.results()]
```

The returned values are not represented as one combined result set. Psycopg retains separate result sets for each execution, navigable through `results()` or `nextset()`.

A single `fetchall()` therefore retrieves rows only from the currently selected result set. Similarly, `rowcount` has different meanings depending on the `returning` flag:

| Configuration     | `rowcount`                                      |
| ----------------- | ----------------------------------------------- |
| `returning=False` | Cumulative affected-row count across the batch  |
| `returning=True`  | Row count for the currently selected result set |

This supports batch writes that must retain database-generated identifiers, computed columns, or other `RETURNING` results without reverting to independent client/server execution for every row.

However, preserving all result sets creates client-side result state. It is not equivalent to the COPY protocol, and its memory and protocol costs should be assessed separately from a write-only bulk load.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/api/cursors.html`

## 6. Streaming results, server-side cursor navigation, and resource ownership

Extends original §§9.2–9.3.

### 6.1 Incomplete streaming can leave a connection unusable

`Cursor.stream()` has a stronger lifecycle requirement than ordinary client-side result iteration.

An ordinary cursor typically holds a completed query result. A streaming cursor instead exposes an active flow of results from PostgreSQL. If the consumer stops iterating before the stream finishes, the connection can remain in PostgreSQL transaction status `ACTIVE`.

While in this state, the connection may reject additional commands because the previous operation has not completed.

The returned generator exposes `close()`, and `contextlib.closing()` provides a reliable cleanup mechanism for partially consumed streams:

```
from contextlib import closingwith conn.cursor() as cur:    with closing(        cur.stream("SELECT * FROM measurements")    ) as records:        for record in records:            if should_stop(record):                break            process(record)
```

Closing the generator restores the connection's ability to progress beyond the active result operation, but it does not guarantee a clean transaction.

Depending on server progress, the resulting transaction status may be `INTRANS` or `INERROR`; an autocommit connection may instead return to `IDLE`. A connection left in an error state may still require an explicit rollback.

This distinction matters particularly for pooled connections, which must not be returned to shared use with unresolved streaming or transactional state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 6.2 Chunked streaming and continuous-result sources

The `size` parameter of `Cursor.stream()` controls how many rows may be retrieved per chunk from the server, while rows remain individually yielded to Python code.

Using `size > 1` requires libpq 17 or newer. Support can be checked through `psycopg.capabilities.has_stream_chunked()`.

Psycopg also documents streaming support for queries producing potentially endless result sequences, such as changefeed-style operations in certain PostgreSQL-compatible systems. This does not imply that ordinary PostgreSQL queries provide an equivalent endless-result facility.

The streaming API itself remains explicitly experimental in Psycopg 3.3.6. Its resource-lifetime and failure behavior should therefore be treated as part of the interface contract, not hidden behind ordinary cursor iteration abstractions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 6.3 Server cursor navigation, batching, and holdability

`ServerCursor` provides additional controls over PostgreSQL's named server-side portals:

| Feature                          | Behavior                                                                           |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| `scrollable=True`                | Requests a cursor supporting nonsequential navigation, including backward movement |
| `scroll(value, mode="relative")` | Moves relative to the current position                                             |
| `scroll(value, mode="absolute")` | Moves to an absolute position                                                      |
| `itersize`                       | Controls the number of rows fetched per batch during cursor iteration; default 100 |
| `withhold=True`                  | Requests a cursor that remains usable after its creating transaction commits       |

These controls have consequential server-side costs.

Ordinary iteration may fetch multiple rows per network operation using `itersize`, rather than issuing one PostgreSQL `FETCH` for each Python iteration. Increasing this value can reduce round trips but also changes the amount of result data buffered per fetch.

Scrollable cursors can require additional execution or storage work, especially when backward movement is not naturally supported by the query plan.

A held cursor (`WITH HOLD`) survives a successful commit but remains associated with the same PostgreSQL session. PostgreSQL may materialize its remaining rows in server memory or temporary files so that subsequent transactions can consume them. Holdability therefore does not eliminate resource-lifetime obligations; it changes which resources must remain available.

PostgreSQL also disallows `WITH HOLD` for queries containing `FOR UPDATE` or `FOR SHARE`, and backward scrolling has corresponding restrictions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



### 6.4 Adopting an existing PostgreSQL cursor

A less obvious capability is that `ServerCursor` can consume a PostgreSQL cursor created outside its own `execute()` call.

For example, a PL/pgSQL function may open a refcursor and return its name. Psycopg can create a matching named cursor object and begin fetching without issuing another `DECLARE`.

This permits server-side cursor ownership to originate in a stored procedure while Psycopg manages subsequent retrieval.

The limitation is that the cursor must exist in the same PostgreSQL session, and its lifetime remains governed by the server transaction and portal rules. This technique is not a means of transferring an open cursor between pooled connections.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Primary sources:

`https://www.psycopg.org/psycopg3/docs/api/cursors.html`

`https://www.psycopg.org/psycopg3/docs/advanced/cursors.html`

`https://www.postgresql.org/docs/current/sql-declare.html`

## 7. Pipeline synchronization and failure recovery

Extends original §5.3.

Pipeline mode has an important transactional property that is easy to miss: the absence of a Python-level wait between statements does not mean those statements have independent PostgreSQL transaction outcomes.

### 7.1 Synchronization versus result flushing

The principal synchronization points are:

| Operation                                    | Effect                                                                                       |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `Pipeline.sync()`                            | Sends pending commands, establishes a synchronization point, and processes available results |
| `Connection.commit()` / `rollback()`         | Establishes synchronization while managing transaction state                                 |
| Exiting a pipeline context                   | Synchronizes outstanding operations                                                          |
| Entering or exiting nested pipeline contexts | May establish additional synchronization boundaries                                          |
| `fetchone()` and related result consumption  | Can flush pending operations to obtain results without issuing a protocol `Sync`             |

The last distinction is especially significant. Receiving a result is not necessarily equivalent to completing a synchronization boundary.

If an earlier command has failed, fetching may expose the error without clearing the pipeline's aborted state. Subsequent queued commands may continue to fail with `PipelineAborted` until an actual synchronization point is processed.

Furthermore, the Python call at which an exception becomes visible is not necessarily the call that submitted the failing SQL. Errors can surface when Psycopg processes buffered server responses.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 7.2 Implicit transaction grouping in autocommit mode

Even when the connection uses `autocommit=True`, PostgreSQL groups pipelined commands between synchronization points into an implicit transaction.

A failing statement can therefore invalidate changes made by earlier statements in that group. Later queued statements may be skipped until synchronization occurs.

This has two important consequences.

First, an application cannot reason about pipelined autocommit commands as though every `execute()` were independently durable.

Second, a recovery boundary must be defined in terms of protocol synchronization and database transaction state, not simply a Python `try`/`except` around individual command submissions.

Where a group of operations requires an explicit atomic contract, Psycopg's transaction management facilities provide the appropriate boundary. Pipeline synchronization handles protocol completion and error propagation; it should not be mistaken for a complete transaction-design abstraction.

Pipeline mode remains labeled experimental in the 3.3 release family, particularly with respect to errors and concurrency.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Primary sources:

`https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html`

`https://www.postgresql.org/docs/current/libpq-pipeline-mode.html`

## 8. Cancellation, notifications, and independent protocol inspection

Extends original §§11.3, 11.5, 13.1, and 13.5.

### 8.1 Safe cancellation versus legacy cancellation

Psycopg exposes two cancellation mechanisms whose differences matter for asynchronous behavior and connection security.

| API                                      | Behavior                                                                       |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| `cancel()`                               | Uses legacy libpq `PQcancel`; may block, including on async connections        |
| `cancel_safe(timeout=...)`               | Uses improved nonblocking libpq cancellation when supported                    |
| `psycopg.capabilities.has_cancel_safe()` | Identifies whether the improved libpq cancellation implementation is available |

The improved cancellation implementation requires libpq 17 or newer.

With an older libpq, `cancel_safe()` falls back to the legacy cancellation mechanism. In that case, its timeout parameter does not take effect.

The original `cancel()` method also has a security distinction: its cancellation connection may not use the same secure transport properties as the original database session. The newer libpq mechanism addresses this limitation.

However, `cancel()` remains the documented choice for use as a Python signal handler; `cancel_safe()` should not be used in that context.

A successful cancellation request only indicates that the client successfully submitted the request. It does not guarantee that PostgreSQL interrupted the command before completion or that the command had no observable effects.

Therefore, cancellation must be separated into three events: requesting interruption, determining the command's actual outcome, and restoring a usable transaction/connection state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/api/connections.html`

### 8.2 Bounded notification consumption

`Connection.notifies()` and its asynchronous counterpart support bounded consumption using two parameters:

| Parameter    | Behavior                                                  |
| ------------ | --------------------------------------------------------- |
| `timeout`    | Bounds waiting for notifications                          |
| `stop_after` | Requests termination after a specified notification count |

These controls were added in Psycopg 3.2.

The count limit is not an exact packet-level guarantee: if multiple notifications arrive in the same network packet, the generator may yield more notifications than the requested `stop_after` value.

The generator may also be explicitly closed.

This provides a native mechanism for bounded notification observation, rather than requiring every listener to build a custom timeout and iteration loop.

As with the existing notification interfaces, these facilities do not establish a durable event log or replay protocol. Their behavior still follows PostgreSQL's notification-delivery and transaction semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Sources:

`https://www.psycopg.org/psycopg3/docs/api/connections.html`

`https://www.psycopg.org/psycopg3/docs/advanced/async.html`

### 8.3 File descriptors, raw results, and readiness integration

`Connection.fileno()` exposes the file descriptor associated with the PostgreSQL connection.

This makes it possible to integrate the connection with operating-system readiness mechanisms, including Python's `selectors` module, without independently opening or managing a second network socket.

Psycopg also exposes lower-level result and connection objects:

- `Connection.pgconn`: the underlying `PGconn` wrapper.
- `Cursor.pgresult`: the current result's `PGresult` wrapper, where available.
- `Connection.info`: structured connection metadata and server/session state.

These interfaces can support specialized inspection of protocol and result metadata beyond ordinary row fetching.

The important ownership boundary is that the high-level connection still manages its libpq object and protocol state. Obtaining a file descriptor or low-level wrapper does not give independent ownership of the connection or permit arbitrary concurrent protocol operations without coordinating with Psycopg.

For independently observing connection readiness, `fileno()` is generally a more specific interface than reaching directly into libpq. For specialized protocol introspection, the raw wrappers expose information that may otherwise require a separate C-level integration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+2



Sources:

`https://www.psycopg.org/psycopg3/docs/api/connections.html`

`https://www.psycopg.org/psycopg3/docs/api/cursors.html`

`https://www.psycopg.org/psycopg3/docs/api/pq.html`

### 8.4 Experimental connection-parameter transformation and DNS SRV resolution

Psycopg includes an explicitly experimental `psycopg._dns` module supporting connection-parameter transformation before connection establishment.

The module provides:

| Interface                                  | Purpose                                                                                         |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `_dns.resolve_srv(params)`                 | Perform DNS SRV lookups and transform connection parameters into resolved host/port information |
| `_dns.resolve_srv_async(params)`           | Asynchronous SRV resolution                                                                     |
| `Connection._get_connection_params()`      | Experimental subclass hook for altering connection parameters before connecting                 |
| `AsyncConnection._get_connection_params()` | Corresponding asynchronous hook                                                                 |

These mechanisms can integrate PostgreSQL connection establishment with DNS service discovery or custom parameter transformations.

The SRV utilities require the separately installed `dnspython` package, version 2.1 or newer. They are not automatically applied to ordinary connection creation. An application must explicitly invoke the utilities or use the documented experimental subclass hooks.

The module also exposes `resolve_hostaddr_async()`, but this function is deprecated and unnecessary for normal asynchronous connections because Psycopg already performs nonblocking hostname resolution.

The underscore-prefixed module and subclass hooks are explicitly marked unstable. They should be understood as experimentation and extension interfaces, not as a stable general-purpose service-discovery API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



Source: `https://www.psycopg.org/psycopg3/docs/api/dns.html`

## 9. Source-version and editorial qualifications

Applies across the original reference and this addendum.

The original guide correctly distinguishes released Psycopg 3.3 functionality from the development documentation. The same separation is necessary for the companion pooling package, whose release cycle is independent of the core driver.

For version-sensitive claims, the following distinction should remain explicit:

| Component                                 | Status as of November 1, 2026                                                           |
| ----------------------------------------- | --------------------------------------------------------------------------------------- |
| `psycopg` 3.3.6                           | Current stable core driver                                                              |
| `psycopg_pool` 3.3.3                      | Current stable pooling package                                                          |
| `psycopg` 3.3.7.dev1 documentation        | Development documentation; not itself evidence that every documented change is released |
| `psycopg_pool` 3.3.4 release-note section | Unreleased corrections, including the null-pool reconnection callback fix               |

The original document also contains formatting artifacts that should be corrected in the base reference rather than carried into this addendum: several Python examples have lost their line breaks, some source entries retain generated citation-card fragments, and URLs contain tracking parameters. These issues do not generally change the capability assessment, but invalid example formatting reduces the document's usefulness as an implementation reference.

For the stable driver, the tagged upstream documentation provides a version-specific reference independent of the development documentation:

`https://github.com/psycopg/psycopg/tree/3.3.6/docs`

Core release history:

`https://www.psycopg.org/psycopg3/docs/news.html`

Pool release history:

`https://www.psycopg.org/psycopg3/docs/news_pool.html`

Published package versions:

`https://pypi.org/project/psycopg/`

`https://pypi.org/project/psycopg-pool/`

This addendum completes the previously identified capability gaps without replacing the original document's descriptions of the primary Psycopg subsystems.