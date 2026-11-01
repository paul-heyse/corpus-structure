# `adbc-driver-postgresql` — Comprehensive Python Library Reference

Research date: October 28, 2026 | Target: Python package 1.13.0 · ADBC Libraries 25 · Stable

## 1. Purpose, architecture, and capability map

`adbc-driver-postgresql` is Apache Arrow's PostgreSQL connectivity package for Python. It provides bidirectional, Arrow-native data exchange with PostgreSQL, combining conventional SQL execution with efficient columnar result retrieval, streaming, bulk ingestion, database metadata inspection, and transaction management.

The package is a Python binding to the native ADBC PostgreSQL driver, which is implemented in C/C++ and uses PostgreSQL's `libpq` client library. It is not a wrapper around psycopg, nor does it depend on SQLAlchemy for query execution.

Version 1.13.0 is the latest stable PyPI release as of October 28, 2026, published October 26. It corresponds to ADBC Libraries 25, released October 21. The package requires Python 3.11 or newer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Primary references:

- Driver capabilities: [https://arrow.apache.org/adbc/current/driver/postgresql.html](https://arrow.apache.org/adbc/current/driver/postgresql.html?utm_source=chatgpt.com)
- Python package API: [https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html?utm_source=chatgpt.com)
- Shared Python driver-manager API: [https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html?utm_source=chatgpt.com)
- Source repository: [https://github.com/apache/arrow-adbc](https://github.com/apache/arrow-adbc?utm_source=chatgpt.com)
- Release history: [https://github.com/apache/arrow-adbc/releases](https://github.com/apache/arrow-adbc/releases?utm_source=chatgpt.com)

### 1.1 Architectural layers

Python consumers

PyArrow · Polars · pandas · SQL applications · Data processing systems

Arrow batches, SQL, parameters, metadata

`adbc_driver_postgresql`

Driver-specific connection entry points and options

`adbc_driver_manager`

DBAPI facade, Arrow interfaces, ADBC lifecycle and metadata APIs

Native ADBC PostgreSQL driver (C/C++)

Arrow conversion · PostgreSQL binary COPY · type resolution · transaction handling

libpq → PostgreSQL wire protocol → PostgreSQL server

The native driver and Python driver manager are separate components, but normally work together. The former implements PostgreSQL-specific behavior; the latter supplies reusable Python abstractions, including most of the methods used for Arrow data access.

### 1.2 Main capability families

| Capability                       | Important mechanisms                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------------------- |
| Arrow-native query results       | Binary PostgreSQL COPY, Arrow record batches, streaming readers, PyArrow tables                   |
| High-throughput data ingestion   | Arrow bulk ingestion, binary encoding, table creation, append and replacement                     |
| SQL execution                    | DBAPI 2.0, native PostgreSQL positional parameters, batch binding, prepared statements            |
| Schema and type interoperability | PostgreSQL-to-Arrow conversion, arrays, composites, JSON, temporal values, numeric representation |
| Database introspection           | Catalog/schema/table discovery, Arrow schemas, constraints, metadata and type annotations         |
| Connection and execution control | Transactions, autocommit, isolation, COPY configuration, batch sizing, native options             |
| Ecosystem interoperability       | Arrow C Data Interface, PyArrow, Polars, pandas, ADBC driver-manager abstractions                 |

Central architectural distinction: this library is a database connectivity and data-transfer layer, not a query execution engine or a complete PostgreSQL administrative framework. PostgreSQL remains responsible for query planning, indexing, storage, constraints and transaction enforcement. ADBC specializes in translating database operations and results to and from columnar data structures.

## 2. Python interfaces and connection model

The Python distribution exposes two levels of access.

| Interface                          | Responsibility                     | Distinctive capabilities                                                                  |
| ---------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------- |
| `adbc_driver_postgresql.dbapi`     | High-level DBAPI-compatible facade | SQL execution, cursors, Arrow retrieval, bulk ingest, transaction methods                 |
| `adbc_driver_postgresql.connect()` | Driver-specific low-level factory  | Returns an `AdbcDatabase` handle, not an active DBAPI connection                          |
| `adbc_driver_manager`              | Native ADBC object management      | `AdbcDatabase`, `AdbcConnection`, `AdbcStatement`, metadata, typed options, Arrow streams |
| `adbc_driver_manager.dbapi`        | Shared Python DBAPI implementation | Arrow-specific cursor extensions, adapters, error classes, connection cloning             |

The DBAPI path is the usual Python entry point. It takes a PostgreSQL connection URI, optional database-level and connection-level option dictionaries, and `autocommit=False` by default. The low-level API exposes ADBC's separate database → connection → statement lifecycle, useful where multiple connections should share driver-level state or where options need explicit control.

The distribution is available through PyPI and conda-forge. PyPI provides the `dbapi` optional extra and prebuilt platform wheels; Arrow support in the high-level interface depends on PyArrow, while Polars and pandas integrations introduce their own dependencies. Python wheels bundle the native driver and PostgreSQL client libraries, whereas conda-forge uses its environment's `libpq`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Source: [https://arrow.apache.org/adbc/current/python/quickstart.html](https://arrow.apache.org/adbc/current/python/quickstart.html?utm_source=chatgpt.com)

### Connection reuse is more important than it initially appears

An `AdbcDatabase` is not equivalent to a PostgreSQL network session. It owns driver configuration and, critically, the type-resolution state described in Section 6. A connection created against that database uses a separate PostgreSQL session.

The DBAPI's `adbc_clone()` creates another connection sharing the underlying database object. Consequently, connection cloning can reuse type-discovery work while still providing separate database sessions. It does not implement pooling by itself; the project documents combining it with SQLAlchemy's `QueuePool`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



Source: [https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)

## 3. Query execution and Arrow result delivery

### 3.1 Binary COPY as the default query transport

The PostgreSQL driver normally executes compatible result-producing queries by rewriting them into PostgreSQL's binary COPY protocol:

`COPY (<query>) TO STDOUT (FORMAT binary)`

This is architecturally different from receiving traditional PostgreSQL row-oriented results and building Python tuples one by one.

The native driver reads the PostgreSQL binary representation, decodes each field according to its resolved PostgreSQL type, and constructs Arrow arrays and record batches. This provides a columnar consumption path while avoiding Python-object creation for every result row.

Its performance benefits arise from bulk transfer, native conversion and amortized batch processing. It is not an end-to-end zero-copy transport: PostgreSQL's binary wire representation and Arrow's in-memory buffers require conversion, allocation and, for some types, reformatting.

The mechanism also creates a compatibility boundary. Queries unsupported inside `COPY (...)`—for example `SHOW`—require disabling the optimization. This is controlled by `adbc.postgresql.use_copy` and is also relevant to PostgreSQL-wire-compatible databases with incomplete binary COPY support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



### 3.2 Result consumption pathways

| API                                       | Result form                              | Important distinction                                                    |
| ----------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| `cursor.fetch_record_batch()`             | `pyarrow.RecordBatchReader`              | Stream-oriented consumption without materializing an entire result table |
| `cursor.fetch_arrow()`                    | Arrow PyCapsule-compatible stream handle | Interoperation through Arrow's standard stream interface                 |
| `cursor.fetch_arrow_table()`              | `pyarrow.Table`                          | Materializes the complete result into an Arrow table                     |
| `cursor.fetch_polars()`                   | Polars DataFrame                         | Materializes results in Polars                                           |
| `cursor.fetch_df()`                       | pandas DataFrame                         | Materializes results in pandas                                           |
| `fetchone()`, `fetchmany()`, `fetchall()` | Python rows                              | DBAPI interoperability; incurs row/object conversion                     |

These conveniences belong principally to `adbc_driver_manager.dbapi`, rather than bespoke PostgreSQL Python bindings. The native driver supplies the Arrow result stream.

The distinction between a `RecordBatchReader` and a materialized `Table` is consequential: streaming permits downstream batchwise transformations and bounded application-side buffering, whereas full materialization retains the result in memory. Actual memory consumption still depends on driver batch sizes, PostgreSQL execution, consumer behavior and any buffering in intermediate libraries.

`fetch_arrow()` transfers the result's stream into an Arrow-compatible consumer; it is not a second independent result set that can safely be fetched again through the same cursor.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



### 3.3 Batching and backpressure-related controls

The driver-specific statement option `adbc.postgresql.batch_size_hint_bytes` influences target result batch size. It is explicitly a best-effort hint: the driver estimates batch sizes, so actual batches may exceed or undershoot the specified number of bytes.

This option affects the representation of results delivered to the consumer, not PostgreSQL's query-plan memory, execution strategy or database-side row count. It is therefore useful for Arrow pipeline granularity and downstream memory management but not a general-purpose SQL resource limit.

The driver also supports normal cursor closing and cancellation at the statement and connection levels, with the native implementation invoking libpq cancellation. This allows a client to request termination of a running query, although cancellation is not a guarantee that the server will stop before completing the operation.

Sources:

[https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html?utm_source=chatgpt.com)

[https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc?utm_source=chatgpt.com)

### 3.4 SQL parameter binding: an important limitation

For PostgreSQL, the supported placeholder convention is native positional syntax (`$1`, `$2`, etc.), not the `%s` syntax used by psycopg.

The upstream PostgreSQL recipe additionally states that, in this release, parameter binding is supported for statements that do not produce result sets. For example, parameterized inserts are documented, but parameterized `SELECT` queries are not an established supported pathway. This is a material distinction from general-purpose PostgreSQL DBAPI drivers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



Binding mechanisms include Python values and Arrow-backed batches:

- `execute()` for individual statement execution.
- `executemany()` for repeated parameter bindings, including PyArrow batches.
- `adbc_prepare()` for explicit statement preparation through the common ADBC API.
- `adbc_execute_schema()` to obtain a prospective Arrow result schema without executing the statement.

The PostgreSQL-specific DBAPI source reports `paramstyle="pyformat"` but explicitly notes that PostgreSQL does not fit the standard Python parameter styles. The documented actual placeholder behavior—`$n` only—takes precedence over interpreting that metadata as support for psycopg-style substitutions.

Sources:

[https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)

[https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_postgresql/adbc_driver_postgresql/dbapi.py](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_postgresql/adbc_driver_postgresql/dbapi.py?utm_source=chatgpt.com)

## 4. Arrow bulk ingestion and table creation

### 4.1 Native Arrow-to-PostgreSQL ingestion

`cursor.adbc_ingest()` accepts Arrow-compatible tabular data and writes it to PostgreSQL through the native driver's bulk ingestion machinery, which includes PostgreSQL binary COPY encoding.

The main accepted Python inputs include PyArrow `Table`, `RecordBatch`, `RecordBatchReader`, and objects exposing the appropriate Arrow stream interface. The documented recipes also ingest PyArrow datasets and scanners, including CSV, Arrow IPC/Feather and Parquet sources. Those file formats are read by PyArrow; ADBC receives the resulting columnar data rather than independently interpreting the files.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



### 4.2 Ingestion modes

| Mode            | Behavior                                            | Consequence                                                                                   |
| --------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `create`        | Create a new table and ingest                       | Fails if the target table already exists                                                      |
| `append`        | Insert into an existing table                       | Relies on compatibility with the existing PostgreSQL schema                                   |
| `create_append` | Create if absent; otherwise append                  | Convenient for repeated loads, but not a schema migration mechanism                           |
| `replace`       | Replace the existing table with a newly created one | Not equivalent to preserving an existing table's indexes, constraints, grants or dependencies |

The API also exposes `db_schema_name`, `catalog_name` and `temporary`. Schema qualification can target a PostgreSQL schema, while temporary ingestion produces session-scoped PostgreSQL tables. PostgreSQL connections cannot transparently use these arguments to write into another database in the same server.

The additional ADBC ingestion controls are not interchangeable with SQLAlchemy migrations or PostgreSQL DDL management. Auto-creating a table from an Arrow schema selects corresponding PostgreSQL types but does not automatically construct relational constraints, application indexes, generated columns or trigger definitions.

### 4.3 Bulk ingestion versus parameterized DML

Bulk ingestion and `executemany()` solve overlapping but different problems:

| Concern                    | `adbc_ingest()`               | Parameterized `executemany()`                        |
| -------------------------- | ----------------------------- | ---------------------------------------------------- |
| Primary operation          | Bulk columnar table loading   | Repeated execution of SQL                            |
| Transport                  | Binary COPY ingestion         | PostgreSQL parameter binding                         |
| SQL flexibility            | Ingestion-oriented            | Arbitrary supported non-result-producing DML         |
| Target table handling      | Creation, append, replacement | Governed by supplied SQL                             |
| Row-by-row transformations | Not directly expressed        | SQL expressions may be incorporated in the statement |
| Conflict handling          | No built-in upsert mode       | Can use PostgreSQL `ON CONFLICT` in supported DML    |

For a plain, high-volume table load, ingestion eliminates the need to construct large collections of Python parameter tuples and repeated insert calls. For updates, conditional writes and conflict handling, PostgreSQL SQL remains necessary. A staging-table load followed by server-side SQL is a possible composition, not an additional native ingestion mode.

Source: [https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)

## 5. PostgreSQL–Arrow type system and semantic fidelity

Type interoperability is one of the most consequential parts of the driver. PostgreSQL and Arrow overlap substantially, but neither type system is a strict subset of the other.

The driver supports both ordinary scalar conversion and some nested/extension types. It also preserves selected PostgreSQL type information in Arrow field metadata, which is important when the Arrow storage type alone does not completely describe the database type.

### 5.1 PostgreSQL → Arrow result mapping

| PostgreSQL type                 | Arrow representation                   | Important qualification                                                       |
| ------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------- |
| `SMALLINT`, `INTEGER`, `BIGINT` | `int16`, `int32`, `int64`              | Direct signed-integer mappings                                                |
| `REAL`, `DOUBLE PRECISION`      | `float32`, `float64`                   | Standard floating-point mappings                                              |
| `BOOLEAN`                       | `bool`                                 | Arrow bit-packed Boolean representation                                       |
| `TEXT`, `VARCHAR`, `CHAR`       | `string`                               | Database string length constraints are not inherent in the Arrow storage type |
| `BYTEA`                         | `binary`                               | Binary payloads                                                               |
| `DATE`                          | `date32`                               | Day-resolution date                                                           |
| `TIME`                          | `time64[us]`                           | Microsecond-resolution time                                                   |
| `TIMESTAMP`                     | `timestamp[us]`                        | No timezone designation                                                       |
| `TIMESTAMPTZ`                   | `timestamp[us, UTC]`                   | UTC instant; original session timezone is not retained                        |
| `INTERVAL`                      | `month_day_nano_interval`              | Retains calendar-month and duration components                                |
| `NUMERIC`                       | `string`                               | Arbitrary-precision decimal value represented textually                       |
| `JSON`, `JSONB`                 | `string` + `arrow.json`                | Semantically marked JSON, not an automatically parsed Arrow struct            |
| `UUID`                          | `fixed_size_binary[16]` + `arrow.uuid` | Canonical extension representation added in 1.13                              |
| PostgreSQL arrays               | `list`                                 | Element conversion and array-shape qualifications apply                       |
| PostgreSQL composite types      | `struct`                               | Requires suitable server-derived type resolution                              |
| Unknown or unsupported types    | `binary` + `arrow.opaque`              | Raw PostgreSQL binary representation, not generic text                        |

The published driver matrix documents the ordinary mappings. The UUID and composite implementations are additionally verified against the release 25 native source.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



Version-specific source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h?utm_source=chatgpt.com)

### 5.2 PostgreSQL `NUMERIC`: intentionally asymmetric

PostgreSQL `NUMERIC` may express precision and scale combinations that cannot be represented losslessly by a particular Arrow decimal type. The driver therefore returns the value as a UTF-8 decimal string, rather than silently narrowing precision.

This is significant for numerical and financial data: a result column may be Arrow `string` while semantically remaining a PostgreSQL decimal.

The reverse direction differs. The native type resolver and binary COPY writer contain mappings and encoders for Arrow `decimal128` and `decimal256` into PostgreSQL `NUMERIC`; release 25 also fixes an ingestion problem involving certain negative decimal values. Therefore, the ability to write decimals must not be confused with a guarantee that reading them returns Arrow decimals.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



Version-specific writer: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h?utm_source=chatgpt.com)

The practical architectural consequence is that schema fidelity and physical storage fidelity are separate concerns. A conversion layer may need to interpret the PostgreSQL type metadata and explicitly construct a decimal Arrow array if a typed decimal is required downstream. That conversion must account for representable precision, scale and exceptional numeric values.

### 5.3 JSON and JSONB: semantic metadata, not automatic decomposition

`JSON` and `JSONB` are returned in a string storage representation carrying the canonical `arrow.json` extension name.

This retains the fact that the field contains JSON rather than arbitrary text, allowing Arrow-aware consumers to distinguish the two where they preserve extension metadata.

However:

- It does not parse JSON into Arrow `struct`, `list` or `map` values.
- PostgreSQL JSON indexing and query operators remain server-side functionality.
- A consumer expecting nested Arrow data must perform explicit parsing or use PostgreSQL SQL to project the desired fields.
- JSON extension metadata can be lost in transformations that drop Arrow field metadata.

The driver's input mapping also recognizes `arrow.json`. In particular, generic Arrow strings and explicitly JSON-marked strings are not necessarily assigned the same PostgreSQL type when creating tables.

Source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h?utm_source=chatgpt.com)

### 5.4 PostgreSQL composite types → Arrow structs

PostgreSQL has genuine structured relational types, including named composite types and row types associated with tables.

The native driver can resolve composite type definitions using PostgreSQL catalog information and convert them into Arrow `struct` fields with recursively typed children.

This is an important capability because it avoids flattening every composite into unstructured strings or JSON. For example, a named PostgreSQL composite containing an integer, a Boolean and a text field can be represented as an Arrow struct with those field types.

But the direction is asymmetric:

- Reading: resolved PostgreSQL composite records can become Arrow structs.
- Writing: the driver's generic Arrow-to-PostgreSQL type inference does not establish a corresponding automatic `CREATE TYPE` mechanism for Arrow structs.
- Schema management: defining and managing PostgreSQL composite types remains a database DDL responsibility.
- Resolution: `builtin` type-resolver mode cannot resolve these custom definitions.

This distinction matters when using nested Arrow schemas as a representation of relational objects. An Arrow `struct` is a structured in-memory value; it does not, by itself, create a PostgreSQL composite type, define storage constraints or provide indexing behavior.

Sources:

[https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h?utm_source=chatgpt.com)

[https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h?utm_source=chatgpt.com)

### 5.5 Arrays and nested structures

PostgreSQL arrays can be converted to Arrow list arrays, including recursively decoded element types.

There are subtleties in the native COPY reader:

- The source array's declared number of dimensions is read, but the implementation builds a single Arrow list of the flattened elements. It therefore does not generally preserve a multidimensional PostgreSQL array's shape.
- PostgreSQL array lower bounds of 0 and 1 are accepted; other lower bounds are rejected by the checked implementation.
- Array element types need an available compatible decoder.
- Array order and null elements can be represented, but the original PostgreSQL dimensional indexing semantics are not fully carried into the Arrow schema.

These are consequential information-model distinctions, particularly when arrays are used as multidimensional scientific data rather than ordinary lists.

Source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h?utm_source=chatgpt.com)

### 5.6 Unknown, custom and extension types

The driver does not necessarily fail when PostgreSQL returns an unfamiliar type. Its fallback is to expose the raw binary wire representation with `arrow.opaque` extension metadata describing the vendor and original type.

This can preserve access to data that the driver does not know how to interpret, including types implemented by PostgreSQL extensions. It is not equivalent to automatically supporting their logical operations or layouts.

For example, a custom spatial type may arrive as opaque bytes rather than a typed geometry object. Correct interpretation would require an appropriate decoder or a SQL projection into a supported representation.

The older `ADBC:postgresql:typname` metadata key is deprecated in favor of canonical opaque extension metadata. New integrations should avoid depending on the deprecated key.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



### 5.7 Arrow → PostgreSQL ingestion considerations

The documented ingestion matrix includes signed integers, Boolean values, floating-point numbers, strings, binary values, supported timestamps, date32, intervals and selected dictionary representations.

Some less conventional conversions are handled internally—for example, unsigned integer widening, decimal encoders and Arrow list mappings—but an internal type inference path does not guarantee every resulting combination is supported by the complete ingestion writer.

The published support matrix explicitly marks `date64` and `large_binary` unsupported. Dictionary ingestion has restrictions, and Arrow dictionary encoding is not automatically preserved as a corresponding PostgreSQL encoding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



A key distinction: compatibility with an existing PostgreSQL column type is not the same as choosing that type during automatic table creation. For example, plain Arrow `string` ordinarily maps to `TEXT`; a pre-existing PostgreSQL column may impose different length, domain or type constraints.

The PostgreSQL server continues to enforce its own casts, constraints and value validity.

### 5.8 PostgreSQL field metadata

ADBC 1.13 adds or extends:

| Metadata                              | Information retained                                                                           |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `POSTGRESQL:type`                     | Original PostgreSQL type name, such as `int4` or `numeric`                                     |
| `POSTGRESQL:typmod`                   | PostgreSQL type modifier for a top-level numeric field, represented as a signed decimal string |
| `ARROW:extension:name = arrow.json`   | JSON semantics over a UTF-8 storage representation                                             |
| `ARROW:extension:name = arrow.uuid`   | UUID semantics over fixed-size binary                                                          |
| `ARROW:extension:name = arrow.opaque` | Unknown PostgreSQL value represented using an opaque binary payload                            |

For `NUMERIC`, the type modifier provides a route to recovering declared precision and scale. A value of `-1` indicates no modifier is available.

This metadata makes Arrow schemas more informative than raw physical types alone. It does not guarantee lossless reconstruction of every PostgreSQL database schema characteristic: constraints, collations, defaults, domains, indexes and database privileges remain separate relational metadata.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



## 6. Type discovery, OID resolution and connection startup

The PostgreSQL driver must interpret type OIDs supplied by `libpq`. Built-in types have known identities, but PostgreSQL also supports dynamically created domains, composites and extension types.

ADBC therefore has a type-resolution subsystem based on a cached mapping of PostgreSQL OIDs to supported Arrow representations.

### 6.1 Two released resolution modes

| Property                            | `server`                              | `builtin`                                         |
| ----------------------------------- | ------------------------------------- | ------------------------------------------------- |
| Availability                        | Existing default                      | Added in 1.13                                     |
| Type discovery                      | Queries PostgreSQL system catalogs    | Uses a preinitialized built-in OID table          |
| Startup cost                        | Can be substantial with large schemas | Avoids broad catalog type-discovery queries       |
| Built-in type support               | Yes                                   | Yes, subject to fixed mapping                     |
| Composite and user-defined types    | Resolved where supported              | Cannot resolve them                               |
| Compatibility with PG-wire variants | Depends on actual catalogs and types  | Assumes known PostgreSQL OIDs                     |
| Typical tradeoff                    | Better dynamic type awareness         | Faster initialization and reduced catalog traffic |

The `server` mode queries `pg_type` and `pg_attribute`, builds a type resolver and caches the result. Because PostgreSQL creates a composite type for tables, databases with many relations can make this initialization unexpectedly expensive. The official documentation reports some user experiences of startup taking minutes.

The `builtin` mode skips those broad catalog queries. This can substantially reduce connection establishment work where schema inspection dominates startup, but it sacrifices the ability to interpret dynamic composite and user-defined types. It does not eliminate all initialization activity or network communication.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



The database-level option is `adbc.postgresql.type_resolver_mode`, with documented values `server` and `builtin`.

An intended third mode that would begin with built-ins and resolve other types on demand is described as future work; the version 1.13 tagged implementation explicitly rejects `auto` as not implemented. It should not be treated as a released capability.

Source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/database.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/database.cc?utm_source=chatgpt.com)

### 6.2 Cache consistency and sharing

The type resolver is constructed when the ADBC database object is initialized. Connections sharing that object can reuse its type information.

This has two opposing implications:

Efficiency: cloned or pooled connections can avoid duplicating type-catalog discovery work.

Schema freshness: a long-lived type cache may not reflect newly created or altered user-defined types. The native implementation explicitly treats the resolver as a cache of PostgreSQL's dynamically mutable catalog.

Consequently, connection sharing and schema evolution are related architectural concerns. The driver is not a general-purpose continuously synchronized PostgreSQL schema registry.

Source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/type_resolver_init.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/type_resolver_init.cc?utm_source=chatgpt.com)

## 7. Database introspection and statistics

Beyond SQL data transfer, the driver provides substantial metadata discovery. These capabilities are particularly useful for systems that need database information in structured Arrow form rather than ad hoc parsing of PostgreSQL catalog queries.

### 7.1 Schema and object metadata

| API                                  | Functionality                                                                |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| `Connection.adbc_get_info()`         | Driver and database information, including vendor and version-related fields |
| `Connection.adbc_get_objects()`      | Hierarchical discovery of catalogs, schemas, tables, columns and constraints |
| `Connection.adbc_get_table_schema()` | Arrow schema for a named PostgreSQL table                                    |
| `Connection.adbc_get_table_types()`  | Supported table classifications                                              |
| `Cursor.adbc_execute_schema()`       | Prospective Arrow schema of a SQL query without executing it                 |

`adbc_get_objects()` supports adjustable depth and filters for catalogs, schemas, tables, table types and columns. Results are expressed as nested Arrow structures, allowing structured consumers to navigate the database hierarchy without assembling separate per-table metadata queries.

The PostgreSQL implementation includes introspection of regular tables, views, materialized views, foreign tables and partitioned tables, along with column descriptions and supported constraint information such as primary keys, foreign keys, unique constraints and check constraints. It also includes temporary schemas in the current release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



Source: [https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html?utm_source=chatgpt.com)

PostgreSQL catalog limitation: the driver can identify databases at the catalog level, but detailed table and schema introspection operates within the database to which the connection belongs. A PostgreSQL connection does not natively traverse other databases as if they were schemas.

### 7.2 Schema-only query analysis

`adbc_execute_schema()` provides a way to ask PostgreSQL to determine a query's result schema before executing it.

That can support schema negotiation, output validation and planning of downstream Arrow transformations without fetching result data.

However, schema prediction has limits. If a query contains an untyped parameter, PostgreSQL may only infer a provisional type; the official recipe illustrates such a parameterized expression returning a string-typed schema. The returned schema should not be mistaken for a guarantee about every possible later binding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



### 7.3 Approximate data-distribution statistics

A significant, easily overlooked feature is `Connection.adbc_get_statistics()`.

The Python driver manager exposes the standardized ADBC statistics API, and the tagged PostgreSQL native implementation supports a useful subset of it by querying `pg_stats` and `pg_class`.

| Statistic          | Native source                         | Interpretation                                                                      |
| ------------------ | ------------------------------------- | ----------------------------------------------------------------------------------- |
| Row count          | `pg_class.reltuples`                  | Estimated table cardinality                                                         |
| Null count         | `pg_stats.null_frac` × estimated rows | Approximate null cardinality                                                        |
| Average byte width | `pg_stats.avg_width`                  | Estimated average column width                                                      |
| Distinct count     | `pg_stats.n_distinct`                 | Estimated distinct cardinality, including PostgreSQL's negative-fraction convention |

These values are returned through ADBC's nested Arrow statistics schema, including the statistic key, value and approximation flag.

Important restrictions verified in the 1.13 native source:

- `approximate=True` is required; exact statistics are not implemented.
- A specific PostgreSQL schema must be provided.
- Statistics apply to the current database.
- The data depends on PostgreSQL planner statistics, their freshness and the underlying catalog's visibility rules.
- `adbc_get_statistic_names()` returns an empty stream because the driver does not define additional custom statistic keys beyond the standard statistics.

This makes the interface useful for approximate data characterization and metadata-aware query planning, without confusing estimates with exact counts or full dataset profiling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



Version-specific source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc?utm_source=chatgpt.com)

## 8. Transactions, connection state and execution control

### 8.1 Transaction semantics

PostgreSQL transactions are supported through the DBAPI `commit()` and `rollback()` operations and the native ADBC transaction interface.

The DBAPI defaults to `autocommit=False`. In this mode, the driver defers beginning a PostgreSQL transaction until an operation requires one. This avoids unnecessarily opening a transaction immediately when a connection is created.

With `autocommit=True`, ordinary statements are committed individually. Explicit transaction lifecycle methods should therefore be understood in terms of the selected mode.

The PostgreSQL-specific `adbc.postgresql.transaction_status` option allows inspection of libpq's transaction state. The native implementation exposes states corresponding to `idle`, `active`, `intrans`, `inerror` and `unknown`.

An operation error can leave a PostgreSQL transaction in an aborted state requiring rollback before further SQL can execute. The driver handles this explicitly rather than silently continuing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



The driver also implements the ADBC standardized transaction isolation option, mapping supported levels to PostgreSQL session isolation settings, including read committed, repeatable read and serializable.

Source: [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc?utm_source=chatgpt.com)

### 8.2 Principal configuration controls

| Scope                           | Option/API                                    | Purpose                                                        |
| ------------------------------- | --------------------------------------------- | -------------------------------------------------------------- |
| Database                        | `adbc.postgresql.type_resolver_mode`          | `server` versus `builtin` type resolution                      |
| Database, connection, statement | `adbc.postgresql.use_copy`                    | Enable/disable binary COPY result optimization                 |
| Statement                       | `adbc.postgresql.batch_size_hint_bytes`       | Approximate output batch size target                           |
| Connection                      | `adbc.postgresql.transaction_status`          | Inspect native PostgreSQL transaction status                   |
| Connection                      | `adbc.connection.autocommit`                  | Transaction commit mode                                        |
| Connection                      | `adbc.connection.transaction.isolation_level` | PostgreSQL isolation setting                                   |
| Connection                      | `adbc.connection.db_schema`                   | Current PostgreSQL schema/search-path setting                  |
| DBAPI connection                | `adbc_clone()`                                | Open a new session sharing the underlying ADBC database object |

The distinction between database, connection and statement configuration matters. A database-level option can affect many derived connections; a statement-level option controls a particular execution path.

The Python option enums do not expose every native option as a dedicated symbol. Driver-specific string keys can also be supplied through the relevant low-level option interfaces.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation+1



### 8.3 Errors, cancellation and resource lifecycle

The Python facade uses familiar DBAPI error categories, including `ProgrammingError`, `IntegrityError`, `OperationalError` and `NotSupportedError`, with native ADBC status information underneath. The 1.13 release improves PostgreSQL SQLSTATE mapping, which makes error classification more useful.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



The driver supports cancellation requests at the connection and statement levels using libpq's cancellation facilities. This is useful for interactive or interruptible query execution, but application code still needs to handle the resulting error and transaction state.

For lifecycle and concurrency, the relevant boundaries are:

- Close or fully consume Arrow result readers before reusing their underlying connection for incompatible operations.
- Do not assume a single PostgreSQL connection can execute multiple independent concurrent queries.
- Use distinct connections when operations require separate sessions or concurrency.
- Treat Python Arrow consumers and their underlying native stream ownership as part of the resource lifecycle.
- Avoid assuming that `executescript()` is transaction-neutral: the shared DBAPI implementation commits a pending transaction before executing the script.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

  ADBC 25 Documentation



## 9. Integration pathways and ecosystem boundaries

### 9.1 PyArrow and columnar data pipelines

PyArrow is the primary high-level Arrow integration.

`RecordBatchReader` and Arrow stream interfaces allow query results to feed directly into columnar transformations, file writers and other Arrow-aware components without requiring intermediate Python row materialization.

In the opposite direction, Arrow datasets and scanners can feed bulk ingestion. The official cookbook demonstrates streaming from Parquet and CSV datasets and using Parquet batch iterators.

The library supplies the database endpoint; PyArrow supplies file scanning, dataset partition discovery and format-specific decoding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



### 9.2 Polars

Polars has direct ADBC integrations for PostgreSQL connectivity:

- `polars.read_database_uri(..., engine="adbc")` for reading.
- `DataFrame.write_database(..., engine="adbc")` for writing.
- The lower-level ADBC DBAPI also exposes `fetch_polars()`.

The benefit is that ADBC can return Arrow data suitable for constructing Polars data frames without necessarily taking a Python-row conversion route.

Polars remains the dataframe execution layer. ADBC does not make PostgreSQL queries execute inside Polars, or vice versa.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



### 9.3 pandas

pandas supports ADBC connections in `read_sql()` and `DataFrame.to_sql()`.

This can avoid some Python object conversions associated with conventional DBAPI paths, particularly for tabular reads and bulk writes. Nevertheless, pandas dtype conversion and materialization remain important parts of the total pipeline cost.

Source: [https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)

### 9.4 SQLAlchemy

The documented SQLAlchemy integration is specifically connection pooling, using `sqlalchemy.pool.QueuePool` with the DBAPI's `adbc_clone()` factory.

This is distinct from having a fully compatible PostgreSQL SQLAlchemy dialect with all of SQLAlchemy's SQL compilation and ORM assumptions. ADBC's PostgreSQL-specific placeholder behavior and query-binding limitations are material reasons not to assume ordinary psycopg dialect behavior.

The pooling composition is useful because it separates:

- ADBC database initialization and shared type metadata.
- Independently managed PostgreSQL connections.
- Pooling policy, capacity and session reuse.

Source: [https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)

### 9.5 Integration with analytical SQL engines

Because ADBC exposes Arrow record batches and streams, it can participate in data flows involving analytical engines that consume Arrow, including DuckDB and DataFusion-based systems.

There are two distinct mechanisms here: materialized ingestion of PostgreSQL data into an Arrow-aware engine, and streamed consumption of PostgreSQL results through that engine's Arrow interfaces.

Neither means ADBC itself supplies query federation, predicate pushdown into PostgreSQL, distributed planning or automatic cross-engine optimization. Those capabilities belong to the surrounding execution engine, connector or planning layer. Arrow compatibility is the interchange mechanism, not a guarantee of zero-copy transfer or shared query planning.

### 9.6 Comparison with adjacent PostgreSQL libraries

| Library or layer         | Primary responsibility                                       | Important distinction                                                                      |
| ------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `adbc-driver-postgresql` | Arrow-native PostgreSQL transfer, ingestion, metadata        | Binary COPY-centered result and load paths                                                 |
| `psycopg` 3              | General PostgreSQL client and DBAPI interface                | Broader traditional PostgreSQL client operations and SQL parameterization                  |
| SQLAlchemy               | SQL construction, ORM, connections and pooling               | May use an underlying DBAPI driver; pooling can be combined with ADBC                      |
| PyArrow                  | Columnar memory, datasets and formats                        | Supplies Arrow processing; not a PostgreSQL wire-protocol driver                           |
| Polars                   | DataFrame execution                                          | Uses ADBC as one possible database transfer mechanism                                      |
| PostgreSQL extensions    | Server-side types, operators, indexes and execution behavior | ADBC can access their SQL-facing results but does not implement extension semantics itself |

These are complementary technologies rather than mutually exclusive replacements. ADBC is particularly distinctive when the central operation is moving substantial tabular data between PostgreSQL and Arrow consumers.

## 10. Deployment compatibility and important limits

### 10.1 PostgreSQL and wire-protocol variants

The upstream documentation identifies testing against PostgreSQL 14–18 and various compatible systems, including Citus, CockroachDB, CrateDB, AlloyDB Omni, Materialize, ParadeDB, TimescaleDB and YugabyteDB.

Testing does not mean identical feature support. Some systems implement the PostgreSQL wire protocol while differing in type OIDs, catalog structures or binary COPY behavior.

The docs explicitly flag that certain vendors may not support COPY query execution. They also identify CedarDB compatibility constraints and state that Amazon Redshift is not supported by this driver; a separate third-party Redshift ADBC driver exists.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



PostgreSQL authentication and TLS are principally handled through libpq's connection mechanisms. The ADBC driver does not replace PostgreSQL's server security model.

Source: [https://www.postgresql.org/docs/current/libpq-connect.html](https://www.postgresql.org/docs/current/libpq-connect.html?utm_source=chatgpt.com)

### 10.2 Consequential limitations at a glance

| Concern                         | Confirmed boundary                                              | Why it matters                                                   |
| ------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------- |
| Parameterized result queries    | Not supported in documented PostgreSQL binding path             | Cannot assume normal psycopg-style parameterized SELECT behavior |
| COPY result mode                | Incompatible with some SQL and wire-protocol variants           | Must select non-COPY execution when necessary                    |
| Distributed partition retrieval | PostgreSQL driver does not support ADBC partitioned result sets | No native multi-consumer result partition protocol               |
| Connection pooling              | Not built into ADBC                                             | Requires companion pooling infrastructure                        |
| Numeric results                 | PostgreSQL `NUMERIC` becomes string                             | Decimal reinterpretation may be required                         |
| JSON results                    | UTF-8 with JSON metadata                                        | No automatic structured Arrow parsing                            |
| Composite types                 | Require type resolution; asymmetric write support               | Arrow structs are not automatic PostgreSQL composite DDL         |
| Custom types                    | May fall back to opaque binary                                  | Domain-specific decoders may remain necessary                    |
| Array dimensionality            | Multidimensional shapes not fully preserved                     | Cannot assume general multidimensional round-trip fidelity       |
| Type catalog cache              | Initialized rather than continuously refreshed                  | DDL changes may outlive resolver knowledge                       |
| Auto-created tables             | Based on Arrow type mapping                                     | No automatic reconstruction of full relational DDL               |
| PostgreSQL statistics           | Approximate, scoped to a schema                                 | Not an exact profiler or complete catalog statistics API         |

The architectural opportunity is to combine three independently useful facilities: PostgreSQL executes the relational work; the ADBC driver handles native binary transfer and Arrow type conversion; Arrow-aware consumers perform downstream columnar processing.

This can eliminate considerable bespoke serialization, row conversion and bulk-loading code. Its suitability depends on the query shape, type fidelity required, PostgreSQL compatibility, metadata needs and connection lifecycle—not on a blanket assumption that an Arrow path is always faster.

## 11. Version-specific changes and authoritative references

### Release 1.13.0 / ADBC Libraries 25

The most important PostgreSQL changes in this release are:

| Change                                            | Significance                                                 |
| ------------------------------------------------- | ------------------------------------------------------------ |
| Built-in OID type resolver                        | Fast-start alternative to full catalog discovery             |
| `POSTGRESQL:type` and numeric `POSTGRESQL:typmod` | Improved database-type fidelity in Arrow schemas             |
| Canonical `arrow.uuid` support                    | Better typed UUID interoperability                           |
| COPY writer time-type support                     | Expanded temporal ingestion behavior                         |
| Database/connection COPY configuration            | More control over execution transport                        |
| SQLSTATE classification improvements              | More informative PostgreSQL error handling                   |
| COPY writer and result-draining fixes             | Improved behavior for specific ingestion and execution cases |
| Temporary-schema introspection improvements       | More complete metadata visibility                            |

These are released 1.13 capabilities, not development-branch proposals. The type resolver's planned automatic fallback mode is not included.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### Primary source navigation

For further investigation, the most useful documents and tagged source paths are:

| Subject                                                   | Source                                                                                                                                                                                                                                      |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Driver feature matrix, types, compatibility               | [https://arrow.apache.org/adbc/current/driver/postgresql.html](https://arrow.apache.org/adbc/current/driver/postgresql.html?utm_source=chatgpt.com)                                                                                         |
| PostgreSQL-specific Python API and options                | [https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html?utm_source=chatgpt.com)                                                         |
| Shared ADBC Python API and extensions                     | [https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html](https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html?utm_source=chatgpt.com)                                                               |
| PostgreSQL recipes and integration examples               | [https://arrow.apache.org/adbc/current/python/recipe/postgresql.html](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html?utm_source=chatgpt.com)                                                                           |
| Exact release changes                                     | [https://github.com/apache/arrow-adbc/releases/tag/apache-arrow-adbc-25](https://github.com/apache/arrow-adbc/releases/tag/apache-arrow-adbc-25?utm_source=chatgpt.com)                                                                     |
| Tagged PostgreSQL type conversion and metadata            | [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h?utm_source=chatgpt.com)             |
| Tagged COPY reader                                        | [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/reader.h?utm_source=chatgpt.com)                 |
| Tagged COPY writer                                        | [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h?utm_source=chatgpt.com)                 |
| Tagged connection, statistics, transaction implementation | [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc?utm_source=chatgpt.com)                 |
| Tagged type resolver initialization                       | [https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/type_resolver_init.cc](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/type_resolver_init.cc?utm_source=chatgpt.com) |
| Published Python distribution                             | [https://pypi.org/project/adbc-driver-postgresql/1.13.0/](https://pypi.org/project/adbc-driver-postgresql/1.13.0/?utm_source=chatgpt.com)                                                                                                   |

Overall: `adbc-driver-postgresql` is a substantial native PostgreSQL/Arrow integration layer, not merely a convenience connector. Its strongest differentiators are streaming columnar queries, binary bulk loading, structured database introspection, shared type-resolution state and Arrow schema metadata. The especially important areas for deeper technical investigation are its type-conversion asymmetries, SQL parameter limitations, PostgreSQL catalog behavior and native COPY execution paths.

# Addendum — `adbc-driver-postgresql` 1.13.0

Supplement to the Comprehensive Python Library Reference · Research date: November 1, 2026 · Apache Arrow ADBC Libraries 25

This addendum extends the original reference with additional capabilities, implementation-level distinctions, and integration mechanisms verified against ADBC 25 documentation and the `apache-arrow-adbc-25` source tag. It omits functionality already adequately described in the original.

One substantive correction: The original §3.4 and §10.2 incorrectly describe parameterized result-producing queries as unsupported. They are supported in 1.13.0. The relevant functionality was introduced in ADBC Libraries 14 (Python 1.2.0), and the PostgreSQL recipe's contrary statement remains outdated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://apache.googlesource.com\&sz=32)

apache.googlesource.com+1



## 1. Parameterized result queries and execution mechanics

### 1.1 Result-producing parameter binding

The PostgreSQL driver supports executing SQL containing native `$1`, `$2`, etc. placeholders and returning results through the same Arrow and DBAPI consumption interfaces used for unparameterized queries.

This includes ordinary parameterized `SELECT` statements, SQL expressions with typed parameters, and result-producing DML such as `INSERT ... RETURNING` where PostgreSQL accepts the statement.

```
import adbc_driver_postgresql.dbapi as pgwith pg.connect(uri) as conn:    with conn.cursor() as cur:        cur.execute(            "SELECT id, value FROM measurements WHERE site_id = $1",            parameters=(42,),        )        reader = cur.fetch_record_batch()        for batch in reader:            process(batch)
```

Illustrative, unexecuted example. `process` represents an application-provided consumer.

The input mechanisms are broader than a single tuple of Python values:

| Binding form                               | Execution semantics                                                                           |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| Python tuple or sequence                   | One parameter set, converted to Arrow-compatible input by the DBAPI backend                   |
| Arrow `RecordBatch`                        | One execution per parameter row                                                               |
| Arrow `Table` or `RecordBatchReader`       | Stream of parameter rows rather than necessarily materializing all bindings as Python objects |
| Arrow C Array / C Stream-compatible object | Direct binding through the standard Arrow interfaces                                          |
| `executemany()`                            | Repeated parameterized execution without exposing a result set                                |

The shared DBAPI also documents dictionary-based named binding, but this must not be assumed to work with PostgreSQL. In version 1.13, the PostgreSQL native statement implementation does not recognize the standard `adbc.statement.bind_by_name` option. The reliable PostgreSQL binding convention remains positional `$n` parameters.

The module's declared `paramstyle="pyformat"` is consequently not evidence of `%s` or `%(name)s` substitution support.

### 1.2 Bound queries bypass the normal COPY-result pathway

PostgreSQL's execution mechanism depends on whether the statement has bound parameters and whether a result stream is requested.

| Execution condition                             | Native pathway                          | Consequential behavior                                                                       |
| ----------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------- |
| Unparameterized query with result, COPY enabled | Binary `COPY (<query>) TO STDOUT`       | Incremental COPY decoding with the driver's approximate batch-size control                   |
| Parameterized query with result                 | `ExecuteBind()` → `PqResultArrayReader` | PostgreSQL result objects converted to Arrow; COPY batch-size hint does not govern this path |
| Query with COPY explicitly disabled             | `PqResultArrayReader`                   | Supports SQL forms incompatible with `COPY (...)`                                            |
| Execution without an output stream              | Native non-result execution             | Executes and reports affected rows where available                                           |

The bound-result implementation requests PostgreSQL's binary result format and converts values using the driver's PostgreSQL-to-Arrow field readers. It is therefore still Arrow-native at the consumer boundary, but does not use the same transport and buffering mechanism as streaming binary COPY.

In the tagged implementation, `PqResultArrayReader` builds an Arrow batch from an available `PGresult`. Its source contains a TODO noting that the COPY batch-size hint is not respected in this path.

Implication: An Arrow `RecordBatchReader` does not, by itself, guarantee bounded native buffering. Parameterized result execution can retain a complete PostgreSQL result for a binding before delivering its Arrow batch. For large-result workloads, choosing between server-side SQL filtering, unparameterized COPY-compatible queries, and bound result queries remains consequential.

### 1.3 Multiple parameter sets can yield one Arrow result stream

A single `cursor.execute()` can bind an Arrow batch or stream containing multiple parameter rows to a result-producing query. The native reader executes successive parameter sets and presents their results through the output Arrow stream.

This is distinct from Python DBAPI `nextset()` behavior. The Python manager does not implement independent result-set navigation; rows are delivered through one stream governed by a common Arrow schema.

Execution has an important lifecycle characteristic:

- The driver starts executing bound parameter rows when preparing the result stream.
- Additional parameter rows can be executed as the stream is consumed.
- Parameter sets yielding no rows may be advanced through internally to find the next available result.
- For bound streaming queries, affected-row information can be unknown (`rowcount == -1`).

Consequently, partially consuming a bound result stream must not be equated with executing every supplied parameter set. This matters particularly for SQL statements with side effects, such as DML using `RETURNING`.

By contrast, `executemany()` executes through the no-result pathway and exhausts the provided parameter bindings as part of that execution. It does not make returned rows available.

### 1.4 Preparation and parameter-schema negotiation

The PostgreSQL implementation exposes more parameter intelligence than the original reference develops.

`cursor.adbc_prepare(sql)` is available through the shared DBAPI and can return the prospective Arrow schema of the statement's parameters. At the native level, `PostgresStatement::GetParameterSchema()` uses PostgreSQL's statement description facilities to determine parameter types and maps them into Arrow schema fields.

However, `PostgresStatement::Prepare()` itself is deliberately deferred: it records preparation state without immediately preparing the actual statement on the PostgreSQL server. Native preparation is performed later when parameter types are known.

This separation provides two useful mechanisms:

Parameter-schema discovery. The system can determine how PostgreSQL expects a statement to be bound without executing its effects. This can support input-contract discovery and more precise Arrow parameter construction.

Null-type reconciliation. When a bound Arrow schema contains `NA`/null-only fields, the driver can first ask PostgreSQL to infer expected parameter types, reconcile them with the Arrow binding schema, and then prepare using concrete PostgreSQL type OIDs. This avoids treating every untyped null as an arbitrary text parameter.

The latter mechanism depends on PostgreSQL being able to infer the relevant type from the SQL expression. Ambiguous SQL parameters still require explicit typing, potentially through SQL casts.

Neither API should be confused with a promise of persistent, reusable server-side prepared-statement handles across arbitrary executions or connections.

Primary sources:

- PostgreSQL bound-result implementation: `https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc`
- PostgreSQL statement lifecycle and preparation: `https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc`
- Python DBAPI execution and binding: `https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_manager/adbc_driver_manager/dbapi.py`
- Historical addition of result-producing parameter bindings: `https://github.com/apache/arrow-adbc/pull/2065`

## 2. Target-aware bulk ingestion and native COPY encoding

### 2.1 Existing-table ingestion resolves destination types

For `append` and `create_append`, the driver does not simply encode Arrow values according to the types it would have inferred for a new PostgreSQL table.

The native implementation:

1. Resolves the destination relation.
2. Queries `pg_attribute` to identify destination column names and PostgreSQL type OIDs.
3. Matches incoming Arrow fields to destination columns by name.
4. Constructs an explicit `COPY table (column_list) FROM STDIN WITH (FORMAT binary)` command.
5. Configures field encoders using the destination types where supported.

This allows column-oriented ingestion into an existing relational schema without requiring the Arrow input fields to reproduce every destination column or appear in physical table order.

It also permits type-sensitive encoding that differs from default Arrow-to-PostgreSQL table creation.

For example, an Arrow integer column can be encoded for an existing PostgreSQL `NUMERIC` destination. The driver has a dedicated integer-to-PostgreSQL-numeric binary writer, rather than requiring the input column to be converted into Arrow decimal values first.

Similarly, a PostgreSQL `JSONB` target can use a dedicated JSONB binary writer when the incoming Arrow string carries the `arrow.json` extension annotation.

These capabilities reduce bespoke pre-ingestion casting and serialization, while leaving PostgreSQL responsible for enforcing constraints, applying defaults, and rejecting incompatible values.

### 2.2 Ingestion's type-dependent behavior

| Arrow source / PostgreSQL target                    | Native behavior                                                                        |
| --------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Arrow integer → existing `NUMERIC`                  | Dedicated integer-to-numeric binary encoding                                           |
| Arrow `decimal128` / `decimal256` → `NUMERIC`       | Native decimal encoding, with an optimized decimal128 path                             |
| Arrow `string` with `arrow.json` → new table        | Inferred PostgreSQL `JSON` column                                                      |
| Arrow `string` with `arrow.json` → existing `JSONB` | JSONB-specific binary encoding                                                         |
| Arrow `fixed_size_binary[16]` with `arrow.uuid`     | PostgreSQL UUID type inference and native UUID representation                          |
| Arrow `TIME32` / `TIME64`                           | COPY writers supporting the Arrow time units and PostgreSQL microsecond representation |
| Arrow list and fixed-size list                      | PostgreSQL array encoding within supported child-type and dimensionality constraints   |

There is an important distinction between type inference and destination-aware encoding. The presence of an encoder for an existing PostgreSQL target type does not imply that the driver automatically creates that same type from a generic Arrow schema.

For example, a generic Arrow string is normally inferred as PostgreSQL `TEXT`, whereas an `arrow.json`-annotated string is inferred as `JSON`. Appending to a pre-existing `JSONB` column uses destination-specific behavior.

### 2.3 Schema qualification, temporary relations and API maturity

The PostgreSQL ingest implementation resolves the current schema using `SELECT CURRENT_SCHEMA()` when the destination schema has not been supplied. It explicitly qualifies the persistent target to avoid an identically named temporary table shadowing it.

Temporary ingestion instead targets PostgreSQL's temporary namespace. The native implementation disallows combining an explicit target schema with temporary-table ingestion; the Python wrapper accommodates this by clearing the schema when enabling temporary ingestion.

The common Python API exposes `catalog_name`, `db_schema_name`, and `temporary`, but documents these arguments as experimental. Their availability in the Python signature is not proof of support in every driver.

In particular:

- PostgreSQL accepts a target database schema for ingestion.
- PostgreSQL's native statement implementation does not implement the ADBC target-catalog option.
- `create_append` uses `CREATE TABLE IF NOT EXISTS` and then resolves the target's actual column types; it does not perform schema reconciliation or migrations.
- Existing destination defaults, identity behavior, generated-column restrictions and constraints retain PostgreSQL semantics.

This combination provides a useful boundary between columnar loading and relational schema governance. ADBC can perform the transfer and adapt certain encodings to existing types; it does not replace DDL or schema-migration tooling.

Primary source:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc`

## 3. Additional PostgreSQL–Arrow type semantics

### 3.1 Less-common PostgreSQL types

The tagged native type resolver covers several PostgreSQL types beyond the main mapping table in the original document.

| PostgreSQL type              | Arrow representation                                                | Semantic consideration                                                                            |
| ---------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `ENUM`                       | UTF-8 string                                                        | Enum identity, permitted labels and ordering are not represented by Arrow's string storage type   |
| Domain over a supported type | Base type's Arrow representation                                    | Domain-specific checks, defaults and identity are not reconstructed from the Arrow physical type  |
| `money` / `cash`             | `int64`                                                             | Raw monetary binary value; currency and interpretation of monetary scale require external context |
| `oid`                        | `int32`                                                             | Object-identifier semantics are not retained by the integer type                                  |
| `regproc`                    | `int32`                                                             | PostgreSQL routine-identifier semantics are not retained by the integer type                      |
| `name`                       | UTF-8 string                                                        | Identifier-specific PostgreSQL semantics are not expressed by the Arrow storage type              |
| `int2vector`                 | `list<int16>`                                                       | Specialized PostgreSQL type decoded into a conventional Arrow list                                |
| Range types                  | Opaque binary representation where no explicit Arrow mapping exists | Range bounds, inclusivity and canonicalization require separate interpretation                    |

The domain behavior is particularly relevant. In `server` resolver mode, the native `PostgresTypeResolver` recognizes PostgreSQL domains and associates them with their underlying type representation while retaining PostgreSQL type-name information. A domain over an integer, for example, can be exposed as an Arrow integer without reconstructing its database-side validation rules.

Range types are recognized by the type resolver, but recognition is not equivalent to decoding them into Arrow interval or structured bound fields. In the tagged implementation, there is no corresponding general structured Arrow range mapping; they take the binary/opaque fallback path.

This creates three distinct notions of fidelity: the raw binary representation, the Arrow storage type, and the PostgreSQL semantic type. `POSTGRESQL:type` and opaque-extension metadata can preserve some of the third category even when the second is simpler.

Source:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h`

### 3.2 Timestamp binding and precision

The official PostgreSQL driver documentation states that when binding an Arrow timestamp, its timezone annotation, if present, is ignored. The value is converted to microseconds and adjusted to PostgreSQL's timestamp epoch of January 1, 2000.

Overflow or underflow during that conversion produces an error.

This is a materially different contract from simply transferring a timezone-aware Arrow timestamp into PostgreSQL while preserving all its associated semantics.

For ingestion into newly created tables, the driver's type inference distinguishes timestamps with and without timezone annotations when choosing PostgreSQL `TIMESTAMPTZ` versus `TIMESTAMP`. That type-selection behavior should not be confused with the conversion guarantees for the timestamp value itself.

The native COPY writer also accepts Arrow time values expressed in seconds, milliseconds, microseconds or nanoseconds. PostgreSQL's microsecond-resolution time representation means that nanosecond precision cannot be preserved as an independent sub-microsecond component.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



`https://arrow.apache.org/adbc/current/driver/postgresql.html`

### 3.3 Nested ingestion remains more restricted than nested decoding

The PostgreSQL COPY writer supports Arrow lists, large lists and fixed-size lists, but their representation maps to PostgreSQL's array encoding, not arbitrary nested Arrow schema preservation.

The tagged implementation's `PostgresCopyListFieldWriter` constructs one-dimensional PostgreSQL array payloads and includes a TODO concerning 64-bit offsets for `LARGE_LIST`.

The writer's factory explicitly documents restrictions on supported list child types. Support for Arrow `struct` on the PostgreSQL-to-Arrow reading path is not a guarantee of symmetrical struct ingestion.

The general limit is not just whether an Arrow type can be mapped to a PostgreSQL OID. The complete operation additionally requires a compatible writer, the correct PostgreSQL binary representation, and compatible target-column semantics.

### 3.4 Published support matrix versus implementation

There is an unresolved support discrepancy in version 1.13.0:

- The published PostgreSQL driver matrix marks Arrow `large_binary` unsupported for parameter binding and bulk ingestion.
- The tagged `PostgresType::FromSchema()` implementation maps `NANOARROW_TYPE_LARGE_BINARY` to PostgreSQL `BYTEA`.
- The native COPY writer also contains a `NANOARROW_TYPE_LARGE_BINARY` branch.

These observations establish that implementation-level support exists, but do not establish unrestricted, tested end-to-end compatibility for all lengths and execution paths. The Arrow representation permits 64-bit offsets, while PostgreSQL values and the driver's intermediate facilities have their own size limits.

The published `date64` restriction should likewise not be relaxed merely because a type-inference branch can map it to PostgreSQL `DATE`; the full COPY writer does not establish equivalent support.

Therefore, the published support matrix remains the conservative statement of officially documented support until runtime behavior and upstream tests resolve the discrepancy.

Primary sources:

`https://arrow.apache.org/adbc/current/driver/postgresql.html`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/postgres_type.h`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h`

## 4. Driver discovery, manifests and connection profiles

These capabilities belong primarily to `adbc_driver_manager`. They extend how the PostgreSQL driver can be deployed, configured and reused alongside other ADBC drivers without requiring custom connection-discovery infrastructure.

### 4.1 Driver manifests and portable loading

The manager can resolve an ADBC driver through a shared-library path, a driver name, or a TOML driver manifest.

A manifest can describe the driver identity, version, supported ADBC specification version, native initialization entry point, and platform-specific shared-library locations.

This separates application configuration from native library location. An application can identify a logical driver while the manager resolves the correct native binary for its platform.

On Unix-like systems, configured search locations include:

| Discovery source                 | Role                                                                                   |
| -------------------------------- | -------------------------------------------------------------------------------------- |
| `ADBC_DRIVER_PATH`               | Environment-specified driver directories                                               |
| `$VIRTUAL_ENV/etc/adbc/drivers`  | Python virtual-environment driver manifests, automatically added by the Python manager |
| `$CONDA_PREFIX/etc/adbc/drivers` | Conda-associated driver installation directory when supported                          |
| `$XDG_CONFIG_HOME/adbc/drivers`  | User-level driver configuration                                                        |
| `/etc/adbc/drivers`              | System-level driver configuration                                                      |

The exact search behavior depends on manager load flags, configured paths and platform. The manager can also derive a driver from an ADBC connection URI scheme where supported.

A manifest is not a replacement for the PostgreSQL driver itself; it provides discoverability and loading metadata for the native driver.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



`https://arrow.apache.org/adbc/25/format/driver_manifests.html`

### 4.2 Connection profiles

Connection profiles package a driver reference and database-level options into a reusable TOML configuration.

They are resolved by the driver manager during database initialization and can be referenced by name or a `profile://` URI.

A PostgreSQL profile can be structured as follows:

```
profile_version = 1
driver = "postgresql"

[Options]
uri = "postgresql://localhost:5432/analytics?sslmode=verify-full"
"adbc.postgresql.type_resolver_mode" = "builtin"
```

Illustrative configuration; driver discovery, certificates and connectivity must be configured separately.

The generic Python manager offers:

```
from adbc_driver_manager import dbapiconn = dbapi.connect(profile="analytics_pg")
```

This is different from `adbc_driver_postgresql.dbapi.connect(uri, ...)`, whose first argument is a PostgreSQL connection URI rather than a driver-manager profile name.

The profile manager provides several advanced behaviors:

- Option precedence: Application-supplied database options can override profile options.
- Environment substitution: Profile values support expressions such as `{{ env_var(VARIABLE_NAME) }}`. An unset variable substitutes an empty string; it is not treated as an automatic configuration error.
- Filesystem resolution: `ADBC_PROFILE_PATH`, Conda profile directories and user configuration directories provide discoverable profile locations.
- External providers: The C driver-manager API supports substituting a custom profile provider for filesystem lookup, permitting integration with externally managed connection configuration.

The custom provider mechanism belongs to the native manager; it should not be mistaken for a Python callback hook exposed by the PostgreSQL package.

An additional distinction is that profile option names must be supported by the selected driver. A generic option mentioned in the ADBC specification does not automatically become a valid PostgreSQL driver option.

These capabilities offer a configuration layer that can be shared across ADBC consumers, without embedding driver locations and PostgreSQL connection strings in every application component.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



`https://arrow.apache.org/adbc/25/format/connection_profiles.html`

`https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html`

## 5. Arrow interoperability without mandatory PyArrow materialization

### 5.1 Arrow C Stream and PyCapsule interfaces

The shared ADBC Python manager exposes a lower-level interchange boundary than the PyArrow `Table` and `RecordBatchReader` conveniences.

`cursor.fetch_arrow()` returns an Arrow-compatible stream handle implementing the Arrow PyCapsule interface. The handle can be imported by a consumer that understands the Arrow C Stream protocol.

Conversely, the manager accepts compatible objects implementing `__arrow_c_array__` or `__arrow_c_stream__` for parameter binding and ingestion.

This makes the Arrow interchange protocol, rather than a particular Python dataframe class, the central interoperability contract.

| Interface                | Data movement                                                   |
| ------------------------ | --------------------------------------------------------------- |
| `fetch_arrow()`          | Native ADBC result stream → Arrow PyCapsule-compatible consumer |
| `fetch_record_batch()`   | Native result stream → PyArrow reader                           |
| `fetch_arrow_table()`    | Native result stream → materialized PyArrow table               |
| `fetch_polars()`         | Native result stream → materialized Polars dataframe            |
| `adbc_ingest()`          | Arrow-compatible producer → native PostgreSQL ingestion         |
| Arrow-backed `execute()` | Arrow-compatible producer → parameter binding → result stream   |

A crucial ownership rule is that `fetch_arrow()` is a one-shot transfer. It must be called before another result-consuming method, and the cursor cannot independently fetch that same stream again after ownership has been transferred.

The result consumer must respect stream lifetime, and a PostgreSQL connection must not be reused for incompatible operations while a live result still owns its underlying execution resources.

### 5.2 Dependency and backend distinctions

The manager's high-level DBAPI documentation states that PyArrow is required for full functionality. However, the tagged implementation also provides a raw PyCapsule result pathway that can be used without constructing PyArrow data structures.

Its Python backend layer includes optional Polars support for Arrow-compatible parameter conversion and stream import. If PyArrow is installed, the PyArrow backend ordinarily takes precedence as the default backend.

Consequently:

- PyArrow-specific fetch methods require PyArrow.
- The raw stream interface can be consumed through compatible Arrow C interface implementations.
- Some operations can work with Polars without first materializing a PyArrow table.
- Full DBAPI behavior without PyArrow is not guaranteed, because other interfaces depend on backend-specific schema and Python-object conversion facilities.

This distinction can reduce unnecessary materialization and dependencies in columnar pipelines, while retaining the PostgreSQL-to-Arrow conversion that the native driver must perform.

It does not imply end-to-end zero-copy transfer from PostgreSQL's wire protocol.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



`https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_manager/adbc_driver_manager/_dbapi_backend.py`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_manager/adbc_driver_manager/dbapi.py`

## 6. Metadata completeness and schema introspection boundaries

### 6.1 The metadata APIs provide different kinds of information

ADBC supplies several metadata interfaces, but they are not interchangeable representations of the complete PostgreSQL schema.

| Interface                 | Native information source                               | Principal limitation                                                                            |
| ------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `adbc_get_objects()`      | PostgreSQL catalog queries                              | Covers selected hierarchy, columns, descriptions and constraints rather than all DDL properties |
| `adbc_get_table_schema()` | Relation's column names and type OIDs                   | Does not collect all column attributes or type modifiers                                        |
| `adbc_execute_schema()`   | PostgreSQL statement preparation and result description | Describes query output, not the complete underlying relations                                   |
| `adbc_get_info()`         | Native driver and connection information                | Does not guarantee a meaningful installed driver-version string                                 |

The tagged `adbc_get_objects()` implementation populates column names, ordinal positions, descriptions and `xdbc_type_name`, plus supported constraint relationships.

It does not reconstruct a complete PostgreSQL catalog model containing every index, generated expression, collation, default, role privilege, trigger or other relational property.

### 6.2 Type modifiers are not uniformly available

Version 1.13 introduces `POSTGRESQL:typmod` metadata for suitable numeric result fields. This is particularly useful for interpreting declared PostgreSQL numeric precision and scale.

However, the tagged native `adbc_get_table_schema()` implementation queries `attname` and `atttypid` from the catalog without collecting `atttypmod` or `attnotnull`.

Consequently, the table-schema API should not be assumed to provide either precise numeric type modifiers or PostgreSQL nullability constraints.

By comparison, query-result schema resolution can obtain type modifiers through PostgreSQL's result-field metadata, which is the pathway explicitly documented for the new metadata.

For example, the information available from a query equivalent to:

```
SELECT amount FROM public.invoices LIMIT 0
```

can differ from the information provided by `adbc_get_table_schema()` for the underlying relation.

This is an important architectural distinction for consumers that require high-fidelity domain schemas. The presence of a PostgreSQL type name in an Arrow field is not sufficient to reconstruct all PostgreSQL column semantics.

### 6.3 Driver information is not a package inventory

The tagged `PostgresConnection::GetInfo()` implementation provides vendor name, server version, driver name, native Arrow-library version and ADBC specification version.

However, `ADBC_INFO_DRIVER_VERSION` currently returns the literal string `"unknown"`.

Therefore, `adbc_get_info()` should not be treated as an authoritative source of the installed Python package version or native binary's release identifier. Distribution metadata or explicit native build provenance is needed for that purpose.

Primary source:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc`

## 7. Transaction, session and connection-lifecycle semantics

### 7.1 Context managers close resources; they do not manage transaction commits

The Python DBAPI's context-manager behavior is narrower than that of some other PostgreSQL clients.

In the tagged implementation, the common `_Closeable.__exit__()` calls `close()` directly. It does not:

- Automatically commit when a context exits successfully.
- Automatically issue an explicit rollback when an exception occurs.
- Implement a transaction scope that preserves the connection for reuse afterward.

For a connection operating with the default `autocommit=False`, successful DML therefore requires an explicit commit before the connection is closed. Uncommitted PostgreSQL transaction work is discarded when the database session terminates.

This distinction also applies to connection closure: the DBAPI `Connection.close()` closes its cursors, closes the underlying native connection and releases its reference to the shared ADBC database. It does not implement a commit-on-close policy.

The relevant abstractions are separate: a context manager governs Python resource lifetime, while PostgreSQL transaction commit and rollback govern the persistence of database changes.

### 7.2 Cloning shares database state, not PostgreSQL session state

`Connection.adbc_clone()` shares the underlying `AdbcDatabase` object but constructs a new native `AdbcConnection`.

The cloned connection shares database-level configuration and potentially costly metadata initialization, including PostgreSQL type-resolution information.

It does not duplicate the original PostgreSQL session's transient state.

| State                              | Shared by cloned connections?                               |
| ---------------------------------- | ----------------------------------------------------------- |
| ADBC database object               | Yes                                                         |
| Cached PostgreSQL type resolver    | Yes                                                         |
| Initial connection options         | Reapplied where specified in the original `conn_kwargs`     |
| Active PostgreSQL transaction      | No                                                          |
| Temporary tables                   | No                                                          |
| Session-local `SET` changes        | No, unless independently established on the new session     |
| Open statements and result readers | No                                                          |
| Current autocommit state           | Not copied; Python clones initialize with the DBAPI default |

The Python implementation constructs cloned connections with `autocommit=False` unless a different behavior is established subsequently.

This distinction is particularly relevant when using the clone factory with a connection pool. Shared metadata initialization can reduce startup overhead, but session-dependent behavior still requires appropriate connection initialization and lifecycle management.

### 7.3 Connection-option side effects

The native PostgreSQL implementation contains two additional details worth making explicit.

Autocommit transitions can commit active work. When switching an initialized connection from non-autocommit to autocommit, the driver issues `COMMIT` if the PostgreSQL connection is not idle. Changing the option is therefore potentially a transaction boundary rather than a purely local configuration update.

The current-schema option selects one schema identifier. Setting `adbc.connection.db_schema` causes the driver to escape the supplied value as a PostgreSQL identifier and execute `SET search_path TO <identifier>`. It is not an interface for passing an arbitrary comma-separated PostgreSQL search-path expression.

Reading the option returns `CURRENT_SCHEMA()`, which identifies the effective current schema rather than the complete `search_path` setting.

The standardized isolation option also accepts PostgreSQL's `READ UNCOMMITTED` level, but PostgreSQL implements that level with `READ COMMITTED` semantics. The driver exposes the accepted PostgreSQL configuration; it does not introduce dirty reads into PostgreSQL's MVCC implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



### 7.4 Concurrency and resource ownership

The shared Python DBAPI declares `threadsafety = 1`: the module can be shared across threads, but database connections should not be assumed thread-safe.

Distinct cloned connections can provide independent PostgreSQL sessions. Their shared database-level type resolver does not create concurrent-query support within a single `PGconn`.

A result stream also has lifecycle significance. A native result reader can retain resources associated with the connection and statement; consuming or releasing the reader is part of making the underlying session safely reusable.

The DBAPI maintains references to open cursors and attempts to close them before closing the underlying connection. Finalizers are a fallback rather than deterministic resource management. The manager can emit resource warnings under pytest or when `_ADBC_DRIVER_MANAGER_WARN_UNCLOSED_RESOURCE=1`.

Sources:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_manager/adbc_driver_manager/dbapi.py`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc`

`https://www.postgresql.org/docs/current/transaction-iso.html`

## 8. Structured diagnostics and additional native execution controls

### 8.1 ADBC errors expose machine-readable details

The shared driver manager's exception classes expose information beyond the DBAPI exception category or message string.

| Attribute     | Meaning                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| `status_code` | Standardized ADBC status classification, such as `INVALID_ARGUMENT`, `INTEGRITY`, `IO` or `NOT_IMPLEMENTED` |
| `vendor_code` | Optional driver- or vendor-specific numeric error code                                                      |
| `sqlstate`    | Optional SQLSTATE code identifying the underlying SQL/database error                                        |
| `details`     | Optional collection of additional named binary error-detail values                                          |

This enables diagnostics that retain both a cross-driver error category and database-specific information.

For example, PostgreSQL constraint violations and serialization failures can be differentiated using SQLSTATE when it is supplied, while the general ADBC status can provide an interoperability-level classification.

These attributes should be treated as available structured information, not as guarantees that every execution pathway populates every field. The tagged PostgreSQL non-COPY result reader still contains a TODO concerning integration of extended ADBC error details.

Version 1.13's SQLSTATE mapping improvements make this particularly relevant, but do not establish uniform diagnostic completeness across all operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 25 Documentation



Source:

`https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html`

### 8.2 Multiple SQL statements versus multiple result sets

The native PostgreSQL implementation supports executing multiple SQL commands through the non-result execution pathway, where it can use libpq's `PQexec()`.

That is different from supporting multiple independently navigable result sets.

The shared Python DBAPI's `Cursor.nextset()` remains unsupported, and `Cursor.executescript()` explicitly commits an existing transaction before executing the script.

Consequently, multi-statement execution should be understood as a SQL execution facility, not as a general procedure-result protocol or a way to preserve a previously active transaction boundary.

Source:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc`

### 8.3 Decimal fast-path control

The tagged native driver supports a PostgreSQL-specific statement option not included in the public Python PostgreSQL option enum:

`adbc.postgresql.disable_decimal_fast_path`

When enabled, it disables the optimized Arrow `decimal128` to PostgreSQL binary `NUMERIC` encoding path and uses the alternative decimal conversion implementation.

The relevant writer first attempts a specialized decimal128 encoder when permitted; unsupported fast-path cases can fall back to the general encoding path.

This option has diagnostic value because it provides a way to isolate the specialized representation conversion from the general implementation when investigating conversion behavior.

Its scope should remain precise:

- It is a statement-level native option.
- Its verified effect is on the COPY ingestion writer.
- The specialized fast path applies to `decimal128`, not a corresponding optimized `decimal256` routine.
- It does not alter the PostgreSQL-to-Arrow read mapping of `NUMERIC` as a string.
- The option is present in the tagged native source but not represented as a dedicated symbol in the published PostgreSQL Python `StatementOptions` enum.

It is therefore an implementation-level diagnostic mechanism rather than a general numerical-performance setting with published performance guarantees.

Sources:

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h`

### 8.4 Generic ADBC APIs do not imply PostgreSQL support

The shared Python manager exposes some interfaces whose implementations vary by driver.

| Generic ADBC facility         | PostgreSQL 1.13 boundary                                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `adbc.statement.bind_by_name` | Not recognized by the tagged PostgreSQL statement-option implementation                                          |
| `set_substrait_plan()`        | Not implemented by the PostgreSQL driver                                                                         |
| `adbc_execute_partitions()`   | PostgreSQL does not implement partitioned result retrieval                                                       |
| `adbc_read_partition()`       | No corresponding PostgreSQL partition-consumption capability                                                     |
| `Cursor.nextset()`            | Unsupported by the shared DBAPI                                                                                  |
| `Cursor.callproc()`           | Unsupported by the shared DBAPI; PostgreSQL procedure calls can still be expressed through SQL where appropriate |

This is important when writing code against generic ADBC interfaces: the presence of a method in the manager or DBAPI class is not proof that the selected native driver implements the underlying operation.

Where driver portability matters, unsupported-operation handling and capability detection must be distinguished from ordinary SQL execution failures.

Sources:

`https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html`

`https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc`

## 9. Direct integration with DuckDB's ADBC community extension

The DuckDB ecosystem provides a concrete analytical-engine integration beyond manually passing Arrow tables or batches between PostgreSQL and a local query engine.

The DuckDB community `adbc` extension uses installed ADBC drivers to expose remote database access through DuckDB SQL. This extension is independently maintained and versioned; its functionality should not be attributed to the Apache PostgreSQL driver itself.

### 9.1 Extension capabilities

The extension supports three primary remote-access mechanisms.

| Mechanism                        | Function                                                                  |
| -------------------------------- | ------------------------------------------------------------------------- |
| `ATTACH ... (TYPE adbc)`         | Expose a remote ADBC database through DuckDB's attached-catalog interface |
| `read_adbc(profile_uri, sql)`    | Execute explicit SQL remotely and consume its result as a DuckDB table    |
| `adbc_execute(profile_uri, sql)` | Send remote SQL commands, including supported administrative DDL          |
| `adbc_clear_cache()`             | Invalidate locally cached ADBC catalog/schema metadata                    |

For example:

```
INSTALL adbc FROM community;
LOAD adbc;

ATTACH 'profile://analytics_pg' AS pg (TYPE adbc);

SELECT *
FROM read_adbc(
    'profile://analytics_pg',
    'SELECT site_id, SUM(value)
     FROM measurements
     GROUP BY site_id'
);
```

Illustrative SQL; the named profile and native ADBC driver must be resolvable in the DuckDB process.

The execution model separates two engines:

- PostgreSQL evaluates SQL explicitly submitted through the remote driver.
- ADBC transfers the resulting data through Arrow.
- DuckDB performs additional local SQL processing over the received data.

The extension also supports operations such as `INSERT`, `COPY` and `CREATE TABLE AS` against attached databases, with streaming bulk ingestion rather than necessarily materializing complete datasets in application memory.

### 9.2 Pooling and execution boundaries

The extension includes its own connection-pooling and ingestion-buffer controls, including:

- `adbc_connection_pool_size`
- `adbc_insert_buffer_size`
- `adbc_materialize_insert_rows`
- `adbc_mix_reads_writes`

These controls belong to the DuckDB extension, not to `adbc-driver-postgresql`.

The documented extension behavior has consequential limitations:

No automatic predicate pushdown for attached tables. A DuckDB query over an attached remote table should not be assumed to move its filters, joins or aggregations to PostgreSQL. Remote computation can instead be expressed explicitly in SQL supplied to `read_adbc()`.

Autocommit-only operation. The extension documents operating in autocommit mode, so its behavior is not a substitute for the PostgreSQL DBAPI's explicit multi-statement transaction management.

Concurrency restrictions. The current extension documentation states that concurrent ADBC operations within one process are unsupported, and mixing ADBC reads and writes in one SQL statement is restricted by default.

Independent metadata caching. The extension's cached catalog state may need invalidation after remote DDL, separately from the PostgreSQL driver's own type-resolution cache.

Together, these features provide a substantial ready-made PostgreSQL-to-DuckDB access layer. Their value comes from composing a native transport with an analytical query engine, not from ADBC itself performing federated planning or guaranteeing that every expression is pushed down.

The extension documentation's general zero-copy claims should also not be transferred indiscriminately to PostgreSQL: its wire-level binary values still require decoding into Arrow buffers.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB Community Extensions



`https://duckdb.org/community_extensions/extensions/adbc`

## 10. Inherited `libpq` connection and security capabilities

The PostgreSQL driver delegates physical connection establishment to PostgreSQL's `libpq` library, using the connection URI supplied to the native driver.

This gives it access to a larger set of connection mechanisms than a simple hostname, port, username and password.

| Capability                    | Relevant libpq mechanisms                                                      |
| ----------------------------- | ------------------------------------------------------------------------------ |
| Local database connections    | Unix-domain sockets and socket-directory `host` settings                       |
| Multiple endpoints            | Multi-host connection strings and target-session selection                     |
| Connection lifecycle          | `connect_timeout`, TCP keepalive-related options                               |
| TLS                           | `sslmode`, root certificates, client certificates and keys                     |
| Authentication                | PostgreSQL server-supported methods implemented by the bundled or linked libpq |
| Credential configuration      | Password files, `passfile`, `PGPASSFILE`                                       |
| Named services                | `service`, `PGSERVICE`, service configuration files                            |
| Session identification        | `application_name`, `PGAPPNAME`                                                |
| Initial session configuration | libpq `options` parameter, including PostgreSQL server configuration arguments |

These capabilities require no corresponding Python API for every individual setting: the connection URI can express supported libpq parameters, while environment variables and configuration files supply defaults.

There are two useful distinctions.

ADBC profiles and libpq services operate at different layers. An ADBC connection profile selects a driver and its database options. A libpq service describes PostgreSQL connection parameters interpreted by libpq after the driver has been selected.

Credential handling is inherited, not redesigned. PostgreSQL's password-file and TLS facilities remain available through libpq. ADBC does not introduce an independent PostgreSQL credential vault or certificate-validation system.

PostgreSQL documents `PGPASSWORD`, but recommends password-file-based handling over environment-variable passwords where process-environment exposure is a concern. Filesystem permissions and the selected libpq version determine which client capabilities are available.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+2



Primary sources:

`https://www.postgresql.org/docs/current/libpq-connect.html`

`https://www.postgresql.org/docs/current/libpq-envars.html`

`https://www.postgresql.org/docs/current/libpq-pgpass.html`

## 11. Capability composition and architectural implications

Several of the added mechanisms have greater value in combination than in isolation.

| Composition                                                  | Native functionality combined                                                                 | Architectural consequence                                                               |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Prepared parameter-schema discovery + Arrow binding          | PostgreSQL type inference, Arrow parameter streams, result-producing queries                  | Database-driven parameter contracts without bespoke positional serialization            |
| Target-aware ingestion + PostgreSQL schema governance        | Column-name matching, target OID resolution, binary COPY                                      | Bulk loading into established relational schemas without recreating DDL                 |
| Shared type resolver + cloned connections + external pooling | Cached PostgreSQL OID metadata, independent sessions, pooling policy                          | Reuse of expensive initialization while preserving transaction independence             |
| Arrow C Stream + downstream analytical engines               | Native result conversion, Arrow interchange, external execution engines                       | Avoidance of Python-row intermediate representations                                    |
| PostgreSQL metadata + structured SQLSTATE diagnostics        | ADBC metadata hierarchy, type identity, error classifications                                 | Structured database introspection and diagnostics without parsing human-readable output |
| Driver manifests + profiles + libpq                          | Native driver discovery, logical connection configuration, PostgreSQL transport configuration | Separation of driver deployment, database configuration and session establishment       |

The main design distinction running through these combinations is that ADBC standardizes access to database operations and Arrow data, but does not erase the semantics of either PostgreSQL or the consuming execution engine.

Parameter binding, destination-type resolution, connection state, nested-type fidelity and Arrow stream lifetime all remain meaningful boundaries. The native capabilities can eliminate substantial custom connectivity code, provided those boundaries are preserved rather than hidden behind an overly generic adapter.

The addendum's source-verified functionality applies to `adbc-driver-postgresql` 1.13.0 / ADBC Libraries 25. Driver-manager profiles and DuckDB integration are companion facilities with their own implementations and compatibility requirements. No local database runtime tests or performance measurements were performed for this addendum.