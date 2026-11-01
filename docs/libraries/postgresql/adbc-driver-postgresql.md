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