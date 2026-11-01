# pgpq — Comprehensive Python Library Overview

Target version: 0.12.0 (released August 15, 2026) | Research date: October 24, 2026 | Python ≥3.10 | MIT license

## 1. Overview and architectural role

pgpq is a high-performance, Rust-backed library for encoding Apache Arrow data into PostgreSQL's native binary `COPY` format. Its principal purpose is to move structured, columnar data efficiently into PostgreSQL without converting it into intermediate CSV files, Python row objects, or sequences of parameterized SQL inserts.

The library provides a Python interface accepting PyArrow `RecordBatch` objects, while delegating binary serialization to a native Rust implementation.

Its most distinctive characteristics are:

- Arrow-native ingestion: Works with data already represented as Apache Arrow, including batches read from Parquet, Arrow datasets, and compatible analytical engines.
- PostgreSQL binary protocol encoding: Produces the binary representation consumed by `COPY ... FROM STDIN WITH (FORMAT BINARY)`.
- Schema-aware conversion: Translates Arrow types into PostgreSQL destination types, exposing the resulting PostgreSQL schema before loading.
- Streaming and batch-oriented execution: Encodes successive Arrow batches independently, allowing bounded-memory ingestion.
- Extensible column encoders: Supports selecting alternative PostgreSQL representations, notably `JSON` and `JSONB` for Arrow string data.
- Nested data support: Handles Arrow list layouts as PostgreSQL arrays and Arrow structs as PostgreSQL composite types.
- Driver independence: Encoding is separate from database transport, connection management, and transaction execution.
- Dual Python/Rust implementation: The same underlying project offers a Python package and a standalone Rust crate.

pgpq is therefore best understood as a typed data-format bridge, not a database driver, ORM, query engine, or PostgreSQL extension.

Its core architecture is:

Data sources and analytical engines

Parquet · PyArrow · Arrow-compatible computation

Arrow RecordBatches + schema

pgpq encoding layer

Type mapping · Binary serialization · Null handling · Arrays · Composites

PostgreSQL binary COPY bytes

Database driver

psycopg 3 or compatible COPY transport

COPY FROM STDIN

PostgreSQL destination

Tables · Temporary staging · Constraints · SQL transformations

The division of responsibilities is important: pgpq translates Arrow values into PostgreSQL's binary representations, but the calling application remains responsible for choosing the source, defining the destination, managing connections, and executing the load.

Version 0.12.0 is the latest release listed on PyPI at the research date. PyPI classifies the project as Alpha, although it has had multiple releases since its initial publication in 2023. The overview below distinguishes documented capabilities from implementation-dependent behavior and architectural implications.

Primary sources:

- Project repository: [https://github.com/adriangb/pgpq](https://github.com/adriangb/pgpq?utm_source=chatgpt.com)
- Python package and current release: [https://pypi.org/project/pgpq/](https://pypi.org/project/pgpq/?utm_source=chatgpt.com)
- Upstream capability summary: [https://github.com/adriangb/pgpq/blob/main/README.md](https://github.com/adriangb/pgpq/blob/main/README.md?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2

## 2. Python API and encoding lifecycle

### 2.1 Primary API surface

The Python interface is deliberately small. Most functionality is concentrated in `ArrowToPostgresBinaryEncoder`, the PostgreSQL schema objects, and field-specific encoder builders.

| API                                                               | Responsibility                                                               |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `ArrowToPostgresBinaryEncoder(arrow_schema)`                      | Infer column encoders from an Arrow schema                                   |
| `ArrowToPostgresBinaryEncoder.infer_encoder(field)`               | Construct the default builder for an individual Arrow field                  |
| `ArrowToPostgresBinaryEncoder.new_with_encoders(schema, mapping)` | Construct an encoder using explicit field-name-to-builder mappings           |
| `encoder.schema()`                                                | Obtain the PostgreSQL schema matching the encoded binary values              |
| `encoder.write_header()`                                          | Produce the PostgreSQL binary COPY header                                    |
| `encoder.write_batch(batch)`                                      | Encode the rows of an Arrow `RecordBatch`                                    |
| `encoder.finish()`                                                | Produce the remaining buffered bytes and binary COPY trailer                 |
| `encoder.composite_type_names()`                                  | Discover generated composite type names                                      |
| `encoder.with_composite_oids(mapping)`                            | Supply database-assigned OIDs for nested composite encoding                  |
| `pg_schema.ddl(table_name, temp_table=True)`                      | Generate PostgreSQL table DDL, including required composite type definitions |

The Python package also exposes two groups of supporting classes:

- `pgpq.encoders`: Field-specific builders such as `StringEncoderBuilder`, `Int64EncoderBuilder`, `ListEncoderBuilder`, `FixedSizeListEncoderBuilder`, and `StructEncoderBuilder`.
- `pgpq.schema`: PostgreSQL type descriptors including `Text`, `Jsonb`, `Numeric`, `Timestamp`, `List`, `Column`, and `PostgresSchema`.

These are more than convenience objects: they form a declarative representation of how each Arrow field will be serialized.

### 2.2 Encoder state and binary stream construction

A complete COPY stream has three stages:

```
write_header()
    ↓
write_batch(batch_1)
write_batch(batch_2)
...
write_batch(batch_n)
    ↓
finish()
```

The underlying Rust implementation maintains explicit `Created`, `Encoding`, and `Finished` states. Calling its operations out of sequence returns an error rather than silently producing malformed data.

A significant implementation detail is that the Python encoder maintains its own output buffer. `write_batch()` may return empty bytes even after successfully encoding a batch; accumulated bytes are emitted once its internal buffer exceeds approximately 1 MiB. `finish()` provides the residual bytes and stream terminator.

Consequently, there is no guaranteed one-to-one correspondence between input Arrow batches and emitted output chunks. The caller should treat returned bytes as segments of one continuous stream.

For each batch, the Rust implementation constructs column encoders, estimates the required output capacity, reserves space, and writes rows directly from Arrow arrays. It avoids generating Python tuples or dictionaries for every row.

Sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs?utm_source=chatgpt.com)

### 2.3 End-to-end illustration with psycopg 3

The following is an illustrative, unexecuted example using native schema generation rather than manually assembling SQL column definitions.

```
import pyarrow as paimport psycopgfrom pgpq import ArrowToPostgresBinaryEncodertable = pa.table({    "id": pa.array([1, 2, 3], type=pa.int64()),    "name": pa.array(["alpha", "beta", None]),})encoder = ArrowToPostgresBinaryEncoder(table.schema)with psycopg.connect(dsn) as conn:    with conn.cursor() as cur:        cur.execute(            encoder.schema().ddl("staging", temp_table=True)        )        with cur.copy(            'COPY "staging" FROM STDIN WITH (FORMAT BINARY)'        ) as copy:            copy.write(encoder.write_header())            for batch in table.to_batches(max_chunksize=65536):                chunk = encoder.write_batch(batch)                if chunk:                    copy.write(chunk)            copy.write(encoder.finish())        # Optional: transform and insert into a final table        # cur.execute("INSERT INTO ... SELECT ... FROM staging")
```

The encoder's lifecycle is independent of the database connection's lifecycle. It can just as readily write its output to a binary file or another destination that accepts byte chunks.

The schema-matching requirement is strict: PostgreSQL binary `COPY` does not perform the implicit type coercions available in regular SQL expressions. A binary `INT2` value cannot simply be copied into an `INT8` column, even though PostgreSQL normally permits such a cast. This is why a staging table whose types match `encoder.schema()` is useful.

The Python implementation also exposes `PostgresSchema.ddl()`, which can emit quoted identifiers and `NOT NULL` declarations. Its implementation defaults `temp_table=True`; explicitly supplying the argument is preferable because the project's type stub currently differs on that default.

Sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/README.md](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/README.md?utm_source=chatgpt.com)

[https://www.psycopg.org/psycopg3/docs/basic/copy.html](https://www.psycopg.org/psycopg3/docs/basic/copy.html?utm_source=chatgpt.com)

[https://www.postgresql.org/docs/18/sql-copy.html](https://www.postgresql.org/docs/18/sql-copy.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2

## 3. Type system and schema translation

Type conversion is the most consequential part of pgpq's functionality. It determines both what the library can serialize and which PostgreSQL schema will accept the resulting bytes.

### 3.1 Supported scalar types

The following summarizes the 0.12.0 mappings verified against upstream documentation and the encoder implementation.

| Arrow type                                 | PostgreSQL representation | Important distinction                                    |
| ------------------------------------------ | ------------------------- | -------------------------------------------------------- |
| `Boolean`                                  | `BOOL`                    | Preserves boolean and null semantics                     |
| `UInt8`, `Int8`, `Int16`                   | `INT2`                    | Uses signed 16-bit PostgreSQL integer                    |
| `UInt16`, `Int32`                          | `INT4`                    | Widening where necessary                                 |
| `UInt32`, `Int64`                          | `INT8`                    | Uses signed 64-bit PostgreSQL integer                    |
| `UInt64`                                   | `NUMERIC`                 | Retains values beyond signed 64-bit range                |
| `Float16`, `Float32`                       | `FLOAT4`                  | Half-precision values widen to 32-bit                    |
| `Float64`                                  | `FLOAT8`                  | Double precision                                         |
| `Decimal32`, `Decimal64`, `Decimal128`     | `NUMERIC`                 | Encoded as PostgreSQL decimal values                     |
| `Timestamp[s, ms, us]`                     | `TIMESTAMP`               | Microsecond precision; timezone metadata not represented |
| `Date32`                                   | `DATE`                    | Adjusted to PostgreSQL's date epoch                      |
| `Time32[s, ms]`, `Time64[us]`              | `TIME`                    | Microsecond-based wire representation                    |
| `Duration[s, ms, us]`                      | `INTERVAL`                | Encoded as microsecond duration                          |
| `Utf8`, `LargeUtf8`, `Utf8View`            | `TEXT`                    | String encoders also support alternative representations |
| `Binary`, `LargeBinary`, `FixedSizeBinary` | `BYTEA`                   | Preserves bytes and nulls                                |
| `List`, `LargeList`, `FixedSizeList`       | PostgreSQL array          | Subject to element-type restrictions                     |
| `Struct`                                   | PostgreSQL composite type | Requires generated or matching composite definitions     |

The distinction between Arrow's signed and unsigned integer families matters. PostgreSQL has no native unsigned integer family, so pgpq widens smaller unsigned types and uses `NUMERIC` for `UInt64`.

Likewise, supporting Arrow decimals does not mean that decimal values are converted through floating-point intermediates. The Rust implementation explicitly serializes decimal values into PostgreSQL's `NUMERIC` binary representation.

### 3.2 Unsupported types and precision boundaries

Several Arrow types are deliberately rejected rather than silently coerced.

| Arrow representation            | Status / implication                                           |
| ------------------------------- | -------------------------------------------------------------- |
| `Timestamp[ns]`                 | Unsupported; conversion to microseconds required               |
| `Time64[ns]`                    | Unsupported; conversion to microseconds required               |
| `Duration[ns]`                  | Unsupported; conversion to microseconds required               |
| `Date64`                        | Unsupported                                                    |
| `Decimal256`                    | No native encoder in 0.12.0                                    |
| `Dictionary`                    | No automatic dictionary-decoding encoder                       |
| `Map`, `Union`, `RunEndEncoded` | No corresponding direct encoder                                |
| Nested Arrow lists              | Not representable through pgpq's one-dimensional array encoder |

For unsupported Arrow representations, transformations can be performed upstream using PyArrow compute kernels, dataset projections, or other Arrow-compatible processing engines.

Importantly, transforming a type to become encodable may change its semantics. Casting nanoseconds to microseconds, for example, requires an explicit precision decision.

### 3.3 Temporal semantics

pgpq converts Arrow timestamp values from Arrow's Unix epoch to PostgreSQL's timestamp epoch of January 1, 2000.

It supports Arrow timestamps with second, millisecond, or microsecond units, all encoded with PostgreSQL microsecond resolution.

However, the output type is `TIMESTAMP WITHOUT TIME ZONE`, not `TIMESTAMPTZ`. The Rust conversion matches timestamp units without preserving the Arrow timezone annotation.

This distinction has two implications:

1. Timezone annotations are not retained in the destination type.
2. The resulting value must not automatically be interpreted as preserving the original timezone-aware application's intended wall-clock semantics.

For timestamp workloads where timezone representation is material, an explicit normalization or destination conversion is necessary.

Arrow durations follow a different rule: PostgreSQL intervals support months, days, and microseconds, but pgpq encodes Arrow durations through the microseconds component. It does not invent calendar months or days from elapsed duration values.

### 3.4 Nullability and schema fidelity

The encoder maintains the distinction between null and non-null values through PostgreSQL's binary field-length representation.

- A null scalar is represented by the protocol's null marker.
- Empty strings and zero-length binary values remain different from null.
- Null arrays and empty arrays remain distinguishable.
- Null array elements are separately represented.
- `Column.nullable` is retained in the inferred PostgreSQL schema.

The generated DDL uses the nullable flag to determine whether to emit `NOT NULL`, but Arrow schema metadata beyond the exposed PostgreSQL type and nullability does not automatically become PostgreSQL constraints or database metadata.

One further distinction: the inferred PostgreSQL schema describes the bytes emitted on the wire, not necessarily the desired long-term table schema. Binary import into a compatible staging representation followed by SQL transformations can preserve that separation cleanly.

Sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/README.md](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/README.md?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/scalar.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/scalar.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs?utm_source=chatgpt.com)

## 4. Nested Arrow data: PostgreSQL arrays and composite types

Nested-type handling is one of pgpq's more distinctive capabilities. It provides native PostgreSQL representations for many structures that otherwise require custom serialization.

However, PostgreSQL arrays and composite types have different structural and type-identification rules from Arrow. Understanding these differences is essential.

### 4.1 Lists become PostgreSQL arrays

pgpq supports three Arrow list storage layouts:

| Arrow layout       | PostgreSQL output | Encoding behavior                     |
| ------------------ | ----------------- | ------------------------------------- |
| `List<T>`          | `T[]`             | Uses 32-bit Arrow offsets             |
| `LargeList<T>`     | `T[]`             | Uses 64-bit Arrow offsets             |
| `FixedSizeList<T>` | `T[]`             | Uses the fixed element count per list |

All three produce PostgreSQL's binary array representation.

The writer includes the array dimensions, element type OID, element count, lower bound, null-element indicator, and individual element values. It emits one-dimensional arrays with a lower bound of 1.

This preserves important distinctions:

- Null array versus empty array.
- Null elements versus non-null elements.
- Variable-length and fixed-size Arrow lists, although their original Arrow layout distinctions are not preserved in PostgreSQL's array type.

Nested lists are explicitly unsupported. PostgreSQL can represent multidimensional arrays, but pgpq's encoder only implements one-dimensional arrays and refuses `List<List<T>>` rather than flattening the structure.

This is a limitation of pgpq's current encoding implementation, not a claim that PostgreSQL lacks multidimensional arrays.

### 4.2 Structs become composite types

An Arrow `Struct` is represented as a PostgreSQL user-defined composite type.

For example, an Arrow column named `measurement` with fields `value: Float64` and `unit: Utf8` conceptually maps to:

```
CREATE TYPE "measurement_t" AS (
    "value" FLOAT8,
    "unit" TEXT
);

CREATE TABLE "observations" (
    "measurement" "measurement_t"
);
```

pgpq's DDL generator handles this translation, including nested composite definitions, quoted identifiers, and preservation of Arrow struct field names.

Unlike JSONB, this representation gives PostgreSQL individually typed composite fields with SQL-accessible field definitions.

### 4.3 Composite type OIDs

PostgreSQL identifies composite types through database-assigned object identifiers (OIDs).

pgpq cannot determine those OIDs from an Arrow schema alone, because PostgreSQL assigns them when the type is created.

The relevant distinction is:

| Composite location                      | OID handling                                         |
| --------------------------------------- | ---------------------------------------------------- |
| Top-level `Struct` column               | No explicit composite OID needed in the COPY payload |
| `Struct` nested inside another `Struct` | Requires the nested composite's actual database OID  |
| Top-level `List<Struct>`                | Requires the struct element's actual database OID    |
| `Struct` containing `List<scalar>`      | Supported using the built-in array type OID          |
| `Struct` containing `List<Struct>`      | Unsupported in the current implementation            |

The last distinction is easily overlooked. PostgreSQL assigns a separate array type OID to user-defined composite types. pgpq supports arrays of composites in top-level columns after the composite element OID is supplied, but its current implementation cannot resolve the composite-array OID required when that array is itself a composite field.

The normal lifecycle for database-assigned OIDs is:

1. Construct the encoder and obtain `encoder.schema().ddl(...)`.
2. Execute the generated type and table definitions in PostgreSQL.
3. Retrieve the resulting type OIDs from `pg_type`.
4. Supply them through `encoder.with_composite_oids(...)` before encoding.

The Python binding mutates the existing encoder in place:

```
encoder = ArrowToPostgresBinaryEncoder(arrow_schema)# Execute DDL before looking up server-assigned OIDs.cur.execute(encoder.schema().ddl("data"))names = encoder.composite_type_names()if names:    cur.execute(        "SELECT typname, oid FROM pg_type "        "WHERE typname = ANY(%s)",        (names,),    )    encoder.with_composite_oids(dict(cur.fetchall()))
```

This is a simplified illustration of the upstream test workflow. In an environment with multiple PostgreSQL schemas, type lookup should also resolve the intended namespace rather than assuming that `typname` is globally unique.

Generated composite names derive from Arrow field names, which can introduce name collisions or require explicit lifecycle management. The library generates type definitions, but does not provide a general-purpose schema migration or type namespace manager.

Sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/nested.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/nested.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/pg_schema.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/pg_schema.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/test_pgpq/test_pgpq.py](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/test_pgpq/test_pgpq.py?utm_source=chatgpt.com)

## 5. Custom encoders, JSONB, and the arrow-json companion

### 5.1 Schema inference versus explicit encoding

Normally, pgpq infers an encoder for every field. For example, an Arrow `Utf8` field gets a string encoder whose PostgreSQL output type is `TEXT`.

Explicit encoders can instead change the output representation, without changing the original Arrow field's storage type.

The principal mechanism is:

```
ArrowToPostgresBinaryEncoder.new_with_encoders(    arrow_schema,    encoder_mapping,)
```

A consequential API rule: the mapping must contain an encoder for every top-level field, not just fields whose behavior differs from the default.

The core implementation reports missing and unknown field names as errors. `infer_encoder(field)` is useful for constructing a complete mapping while changing only selected columns.

### 5.2 Encoding Arrow strings as JSONB

The most important non-default mapping is:

`Arrow Utf8 → PostgreSQL JSONB`

With the Python interface:

```
from pgpq import ArrowToPostgresBinaryEncoderfrom pgpq import encoders, schemaencoder_mapping = {    field.name: ArrowToPostgresBinaryEncoder.infer_encoder(field)    for field in arrow_schema}json_field = arrow_schema.field("payload")encoder_mapping["payload"] = (    encoders.StringEncoderBuilder.new_with_output(        json_field,        schema.Jsonb(),    ))encoder = ArrowToPostgresBinaryEncoder.new_with_encoders(    arrow_schema,    encoder_mapping,)
```

The underlying Rust encoder writes the JSONB binary format version byte followed by the UTF-8 JSON payload.

It does not parse arbitrary strings into JSON structures on the Python side. The strings must already contain valid JSON representations, and PostgreSQL's JSONB receiver ultimately validates them.

This lets callers select a structured PostgreSQL representation while keeping source values in an Arrow string column.

The Rust core also implements the PostgreSQL `JSON` type. In version 0.12.0, the documented Python-facing schema exports and type stubs expose `Jsonb` but not an equivalent public `Json` descriptor, so the practical Python interface is narrower than the underlying Rust implementation in this respect.

### 5.3 Custom encoding of array elements

Encoder customization can extend into lists, not just top-level scalar fields.

For example, an Arrow `List<Utf8>` column can be represented as PostgreSQL `JSONB[]`, rather than the default `TEXT[]`.

The relevant builders are:

- `ListEncoderBuilder.new_with_inner(...)`
- `LargeListEncoderBuilder.new_with_inner(...)`
- `FixedSizeListEncoderBuilder.new_with_inner(...)`

These accept a custom encoder for each list's element type.

This is significant because it permits compositions such as nullable arrays of JSON documents without inventing a separate per-element Python serialization path.

The library's Python tests explicitly exercise `List<Utf8>` encoded as `JSONB[]`.

### 5.4 Companion package: arrow-json

Package: `arrow-json` 0.10.0 | Separate distribution, same upstream repository

The companion package addresses a different problem: converting an Arrow array containing complex nested values into an Arrow string array containing serialized JSON.

Its primary API is:

```
from arrow_json import array_to_utf8_json_arrayjson_array = array_to_utf8_json_array(    nested_arrow_array,    large=True,)
```

`large=True` produces a large-string Arrow array; `large=False` produces a standard UTF-8 string array.

A useful composition is therefore:

Arbitrary nested Arrow array

Struct · List · Nested combinations

`arrow-json.array_to_utf8_json_array()`

Arrow Utf8 / LargeUtf8 containing JSON

`pgpq` JSONB string encoder

PostgreSQL JSONB

This pathway extends the practical ingestion surface beyond the nested structures that pgpq can encode as native PostgreSQL arrays and composites.

The tradeoff is that the intermediate data becomes JSON text rather than retaining directly addressable native Arrow child buffers or a PostgreSQL composite type.

The companion's source also explicitly identifies its current serialization procedure as inefficient: it writes Arrow JSON, parses that JSON back into values, and serializes values again into an Arrow string array. It should therefore not be assumed to have the same performance characteristics as pgpq's direct primitive encoders.

Sources:

[https://pypi.org/project/arrow-json/0.10.0/](https://pypi.org/project/arrow-json/0.10.0/?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/json/src/lib.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/json/src/lib.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/text.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/text.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/test_pgpq/test_pgpq.py](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/test_pgpq/test_pgpq.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

## 6. Integration architecture and complementary libraries

pgpq's small responsibility is an advantage when building data pipelines: it can sit between a variety of Arrow producers and PostgreSQL transports without requiring a particular ingestion framework.

### 6.1 PyArrow datasets, Parquet, and streaming

PyArrow's dataset scanner provides an especially natural upstream integration.

A scanner can perform projection, filtering, and batch-oriented reading before pgpq receives the data.

```
import pyarrow.dataset as dsdataset = ds.dataset(    "data/",    format="parquet",)scanner = dataset.scanner(    columns=["id", "timestamp", "value"],    batch_size=65536,)encoder = ArrowToPostgresBinaryEncoder(    scanner.projected_schema)for batch in scanner.to_batches():    encoded = encoder.write_batch(batch)    # Send encoded bytes through COPY
```

The important architectural distinction is that PyArrow owns source reading and columnar transformations; pgpq owns PostgreSQL serialization.

This makes it possible to ingest very large datasets without first constructing a complete `pyarrow.Table`.

The same pattern applies to `RecordBatchReader` instances and other producers of compatible Arrow batches. Where necessary, upstream Arrow compute operations can normalize unsupported types or arrange columns in the exact order expected by the destination.

Source: [https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 6.2 Database transport and SQL libraries

| Library or subsystem | Responsibility relative to pgpq                                                            |
| -------------------- | ------------------------------------------------------------------------------------------ |
| PyArrow              | Produces and transforms typed columnar data                                                |
| psycopg 3            | Provides PostgreSQL connections, transactions, and COPY transport                          |
| `psycopg_pool`       | Manages database connection pools; not used by the encoder itself                          |
| SQLAlchemy           | Models SQL schemas, transactions, and relational operations                                |
| Alembic              | Manages persistent PostgreSQL schema migrations                                            |
| DuckDB / Polars      | Can produce Arrow-compatible results for encoding                                          |
| PostgreSQL           | Validates and stores the binary values, enforces constraints, and executes transformations |

These are complementary integration boundaries rather than dependencies bundled into pgpq.

A particularly useful distinction is between `psycopg.Copy.write()` and `psycopg.Copy.write_row()`.

`write_row()` performs driver-level adaptation of individual Python values. `write()` accepts already encoded byte blocks and is therefore the appropriate integration with pgpq.

psycopg also provides asynchronous COPY operations. pgpq can produce the bytes supplied to an `AsyncCopy` object, although the encoding operation itself remains synchronous in the current Python interface.

Source: [https://www.psycopg.org/psycopg3/docs/basic/copy.html](https://www.psycopg.org/psycopg3/docs/basic/copy.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 6.3 Temporary staging and SQL-side conversion

An especially consequential composition is:

`Arrow transformation → pgpq → binary COPY → PostgreSQL staging table → SQL transformation`

The staging table can match pgpq's inferred types exactly, while the destination table can use a different long-term schema.

This allows PostgreSQL to handle operations that binary COPY intentionally does not perform:

- Type casts and timezone interpretation.
- Data normalization and validation expressed in SQL.
- Joins against existing relational data.
- Conflict handling through subsequent `INSERT ... ON CONFLICT`.
- Derivation of additional columns.
- Promotion into partitioned or indexed destination tables.

This is not functionality implemented by pgpq. It is an architectural option enabled by separating efficient binary loading from relational transformation.

For example, Arrow's `UInt64` can arrive as PostgreSQL `NUMERIC` even if the final model requires a narrower integer after validation.

Likewise, Arrow timestamps can first arrive as `TIMESTAMP` and then be interpreted explicitly according to the intended timezone semantics.

### 6.4 Relationship to foreign data wrappers

pgpq provides a different integration model from a PostgreSQL foreign data wrapper.

A foreign data wrapper exposes an external source through PostgreSQL's query system. pgpq instead transfers the data into native PostgreSQL storage.

That difference has several consequences:

| Property                          | pgpq + COPY                  | Foreign data wrapper                                  |
| --------------------------------- | ---------------------------- | ----------------------------------------------------- |
| Source access                     | External application         | PostgreSQL extension or server-side integration       |
| Transformation location           | Can occur outside PostgreSQL | May be delegated between PostgreSQL and remote source |
| PostgreSQL extension installation | Not required                 | Usually required                                      |
| Destination                       | Materialized PostgreSQL data | External data exposed as relations                    |
| Ongoing source synchronization    | Caller responsibility        | Depends on wrapper and source                         |
| Query pushdown                    | Not provided by pgpq         | Potentially supported by wrapper                      |

pgpq is well suited to materializing Arrow data into PostgreSQL when compute should remain outside the database or extension deployment is unavailable.

A foreign data wrapper may be preferable when ongoing external queries, query pushdown, or avoiding materialization are more important.

## 7. Performance characteristics and execution mechanics

pgpq's performance advantages arise from eliminating several avoidable representations and operations in conventional Python ingestion pipelines.

### 7.1 What pgpq avoids

A conventional ingestion path might involve:

`Arrow data → Python row objects → driver type adaptation → SQL inserts`

or:

`Arrow data → CSV serialization → CSV parsing in PostgreSQL`

pgpq instead performs:

`Arrow data → native Rust binary encoding → PostgreSQL binary COPY`

This can remove the costs of materializing large numbers of Python objects, formatting textual fields, escaping CSV content, parsing text on the PostgreSQL side, and repeatedly executing parameterized inserts.

However, this is not zero-copy all the way into PostgreSQL. The encoder constructs a row-oriented binary COPY representation, and the Python binding returns bytes that are subsequently handed to the database transport.

### 7.2 Important implementation optimizations

The Rust source exposes several performance-oriented mechanisms:

- Column encoder specialization: Different Arrow physical types have specialized encoding paths.
- Batch-level preparation: Column encoders are prepared once per `RecordBatch`, rather than rediscovering types for every row.
- Output capacity estimation: Encoders provide byte-size hints, allowing the output buffer to reserve capacity ahead of writes.
- Fixed-width binary writes: Specialized byte-writing routines reduce overhead on common scalar types.
- Buffered Python output: The Python wrapper accumulates encoded data internally before emitting byte chunks.
- No intermediate Python rows: Source values remain accessible through native Arrow arrays during encoding.

The implementation contains profiling-derived optimizations of fixed-width writes; these are meaningful evidence that its native encoding path has received targeted performance work, rather than merely being a straightforward Rust translation.

### 7.3 Benchmark interpretation

The project reports encoding approximately one million NYC Yellow Cab rows in less than one second in its benchmark notebook. It also reports a benchmark in which encoding plus PostgreSQL binary COPY is faster than a native CSV COPY comparison.

These are upstream benchmark observations, not general guarantees.

Actual end-to-end throughput will depend on the Arrow type distribution, nested or decimal values, input batch sizes, source reading costs, driver transport, network latency, PostgreSQL storage and indexing, and transaction characteristics.

The distinction between encoding throughput and completed database-load throughput is particularly important.

The Python binding also does not expose an explicit GIL-release mechanism around the encoder's main operation in the inspected source. Rust implementation alone should therefore not be taken as evidence that multiple Python threads can execute the encoder concurrently at full CPU parallelism.

Primary benchmark and implementation sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/benches/encode.ipynb](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/benches/encode.ipynb?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/benches/copy.ipynb](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/benches/copy.ipynb?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs?utm_source=chatgpt.com)

## 8. Correctness boundaries, error handling, and limitations

### 8.1 Type and column compatibility

The most important correctness requirement is that the byte stream produced by pgpq matches the PostgreSQL destination's binary receive formats.

The following can cause errors even when an equivalent SQL insert would succeed:

- Different integer widths.
- `TEXT` bytes targeting a `JSONB` column.
- Column order mismatches.
- Unsupported or incompatible nested type definitions.
- Incorrect composite type OIDs.

The encoder validates various Arrow-side conditions and checks the number of columns in each batch. PostgreSQL remains the authority for accepting values into the destination schema.

Explicit `COPY` column lists can be used to control destination mapping, but pgpq does not automatically reconcile the destination table's schema.

### 8.2 Important semantic and implementation constraints

| Concern                 | Consequence                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| Timezone metadata       | Arrow timezone annotations are not retained in pgpq's `TIMESTAMP` output                               |
| Nanosecond precision    | Unsupported by the native encoder                                                                      |
| Arbitrary Arrow nesting | Only supported structural combinations can use native arrays/composites                                |
| JSONB input             | Strings must contain valid JSON; pgpq does not validate the JSON document first                        |
| Field size              | PostgreSQL binary COPY uses signed 32-bit field lengths                                                |
| Schema changes          | Existing encoder mappings are not an automatic schema-evolution mechanism                              |
| COPY direction          | pgpq encodes Arrow into PostgreSQL; it does not decode PostgreSQL into Arrow                           |
| Portability             | PostgreSQL binary COPY is type-specific and less portable across PostgreSQL versions than text formats |
| Custom PostgreSQL types | No general registry of arbitrary user-defined binary encoders is exposed by the Python API             |

A subtle positive property: upstream roundtrip tests cover IEEE floating-point special values, including NaN, infinities, and signed zero, as well as numerous numeric and nested cases. The implementation also checks arithmetic overflow in several temporal conversions rather than permitting silent integer wrapping.

### 8.3 PostgreSQL constraints remain active

Binary COPY does not bypass PostgreSQL's database rules.

For example, PostgreSQL still invokes destination triggers and check constraints. Transaction rollback remains available through the database driver.

Other PostgreSQL restrictions also apply. `COPY FROM` is not supported for tables with row-level security enabled under PostgreSQL's documented behavior. PostgreSQL's `ON_ERROR ignore` mechanism is limited to text and CSV formats, so it cannot be treated as a general row-skipping facility for pgpq's binary stream.

For large imports, errors occurring late in a COPY operation can also leave physical dead tuples occupying space until PostgreSQL reclaims it, despite the rows not remaining visible.

These are PostgreSQL semantics, not pgpq-specific behavior.

Source: [https://www.postgresql.org/docs/18/sql-copy.html](https://www.postgresql.org/docs/18/sql-copy.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



### 8.4 Error model and testing

The Rust core defines structured error variants for:

- Unsupported Arrow types and incompatible encoder types.
- Missing or unknown explicit field encoders.
- Column-count mismatches.
- Field-length overflow and other encoding failures.
- Invalid encoder lifecycle operations.

The Python binding generally converts core failures into Python exceptions, commonly `ValueError`, while Arrow conversion errors may arise through the native bindings.

The upstream project includes actual PostgreSQL integration tests, property-based roundtrip tests, and structure-aware fuzz testing. Its fuzz target constructs valid Arrow schemas and batches and checks that the documented encoding sequence does not panic.

That is useful evidence of correctness testing, but it does not imply that every Arrow type or possible PostgreSQL destination schema is supported.

Sources:

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/error.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/error.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/tests/proptest_roundtrip.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/tests/proptest_roundtrip.rs?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/fuzz/README.md](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/fuzz/README.md?utm_source=chatgpt.com)

## 9. Rust crate, packaging, and version considerations

The project has two distinct pgpq distributions:

| Distribution      | Purpose                                                       | Version at research date |
| ----------------- | ------------------------------------------------------------- | ------------------------ |
| Python `pgpq`     | PyArrow-facing API backed by a native Rust extension          | 0.12.0                   |
| Rust `pgpq` crate | Direct Arrow-rs `RecordBatch` encoding into `bytes::BytesMut` | 0.12.0                   |

The Rust crate exposes `ArrowToPostgresBinaryEncoder::try_new`, batch encoding into caller-managed buffers, schema inspection, field encoder builders, and composite OID handling.

It can therefore serve native Rust applications without passing through Python or depending on psycopg.

Version 0.12.0 of the Rust workspace targets Arrow-rs 59 and declares Rust 1.85 as its minimum supported compiler version. Development on the main branch has subsequently advanced dependency versions, so its current manifests should not be used to infer the exact dependency requirements of 0.12.0.

For Python, the published requirement is PyArrow 11 or newer, with Python 3.10 or newer. The package uses maturin and PyO3 for native compilation and publishes `abi3` wheels for several supported Linux, Windows, and macOS configurations.

The project remains labeled Alpha on PyPI. That is worth accounting for when considering API stability, independent of its current correctness tests and supported capabilities.

Primary sources:

[https://pypi.org/project/pgpq/0.12.0/](https://pypi.org/project/pgpq/0.12.0/?utm_source=chatgpt.com)

[https://crates.io/crates/pgpq](https://crates.io/crates/pgpq?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/Cargo.toml](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/Cargo.toml?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/pyproject.toml](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/pyproject.toml?utm_source=chatgpt.com)

[https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

## 10. Overall capability boundary

pgpq is unusually focused: it is not trying to provide an entire data ingestion framework, but instead supplies a performant, typed encoding kernel that other systems can compose.

Its strongest capability combinations are:

| Workload or need                       | Native capability combination                                    | Main boundary                                                   |
| -------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------- |
| Large Arrow or Parquet ingestion       | PyArrow batch scanner + pgpq + binary COPY                       | Source scanning and database transport remain external          |
| Schema-aligned loading                 | Encoder inference + PostgreSQL schema inspection + generated DDL | Long-term schema evolution remains external                     |
| Structured relational values           | Lists and structs → arrays and composites                        | Unsupported nested layouts and OID dependencies                 |
| Semi-structured values                 | JSONB string encoder + optional arrow-json preprocessing         | Additional serialization and loss of original structural typing |
| Native Rust data movement              | Arrow-rs RecordBatch + Rust pgpq encoder                         | Caller owns transport and buffer lifecycle                      |
| Relational transformation after ingest | Binary COPY into typed staging + SQL operations                  | Not an SQL execution or transformation engine                   |

The central architectural opportunity is to retain a typed, columnar representation through source reading and transformation, then introduce PostgreSQL's row-oriented binary representation only at the ingestion boundary.

This can eliminate substantial bespoke serialization, Python row adaptation, CSV handling, and per-row database execution machinery while allowing specialized engines to retain responsibility for the parts of the data pipeline they implement best.

For deeper investigation, the most valuable upstream sources are the encoder implementation, field type-dispatch logic, nested encoders, PostgreSQL schema generator, and database-backed tests linked above. Together, they provide a more complete picture of version 0.12.0 than the introductory README alone.

# pgpq 0.12.0 — Technical Capability Addendum

Research date: November 1, 2026\
Target version: pgpq 0.12.0, released August 15, 2026\
Upstream release commit: `306cdf8cf2b8450a3162a9cd467422cb0849af5a`\
Companion package: arrow-json 0.10.0

This addendum supplements the existing pgpq library overview, focusing on additional functionality, schema fidelity, encoding guarantees, extensibility boundaries, and consequential PostgreSQL integration behavior. It does not restate the library's core Arrow-to-binary-COPY functionality.

The findings are based on the published 0.12.0 implementation and PostgreSQL 18 documentation. Implementation-derived behaviors are identified separately from PostgreSQL guarantees and architectural implications.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. PostgreSQL schema fidelity and generated-object lifecycle

Supplements original §§3.4, 4.2–4.3, and 8.1.

### 1.1 Encoded-value fidelity is not equivalent to schema-contract fidelity

`PostgresSchema` represents PostgreSQL types compatible with pgpq's emitted binary data. It is not a lossless representation of every constraint or metadata property in the originating Arrow schema.

Several distinctions deserve explicit recognition:

| Arrow characteristic        | pgpq/PostgreSQL behavior                                                                         | Consequence                                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Decimal precision and scale | Decimal32/64/128 values use PostgreSQL `NUMERIC`; generated DDL declares unconstrained `NUMERIC` | Values retain their numeric meaning, but the original precision/scale contract is not enforced by the generated table |
| Negative decimal scale      | Encoded exactly using PostgreSQL's numeric representation                                        | Negative Arrow scale does not require floating-point conversion or rounding                                           |
| Struct-child nullability    | Composite attributes are emitted as field names and types without `NOT NULL` constraints         | A non-nullable Arrow child does not become a database-enforced non-nullable composite attribute                       |
| List-element nullability    | PostgreSQL array elements can contain nulls, independently of Arrow child-field nullability      | Element-nullability constraints are not represented by the array type                                                 |
| Fixed-size list cardinality | The generated PostgreSQL array type has no corresponding fixed-length constraint                 | Arrow's fixed element count is not enforced after loading                                                             |

PostgreSQL's unconstrained `NUMERIC` has no declared precision or scale coercion. This is useful for ingesting heterogeneous decimal widths and `UInt64`, but means generated DDL cannot serve as a complete substitute for a domain schema that includes precision restrictions.

The 0.12.0 numeric encoder handles positive, zero, and negative decimal scales using integer arithmetic and PostgreSQL's base-10000 `NUMERIC` representation. Its tests cover extreme values and negative-scale behavior. This supports preservation of decimal values within the encoder's supported input range; it does not imply that destination typmods or Arrow schema metadata are preserved.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



PostgreSQL separately documents that standalone composite types cannot include attribute constraints such as `NOT NULL`. Such constraints require another enforcement mechanism, for example a domain over the composite type with an appropriate check.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



Architectural distinction: pgpq provides a compatible binary representation and a useful inferred relational type system. A full persistence contract—including precision, element validity, business invariants, and schema metadata—remains a separate concern.

Sources:

- Decimal implementation and numeric scale tests:\
  `https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/numeric.rs`
- Generated PostgreSQL types:\
  `https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/pg_schema.rs`
- PostgreSQL numeric types:\
  `https://www.postgresql.org/docs/18/datatype-numeric.html`
- PostgreSQL composite constraints:\
  `https://www.postgresql.org/docs/18/rowtypes.html`

### 1.2 Generated composite types do not inherit temporary-table lifetime

`PostgresSchema.ddl(table_name, temp_table=True)` generates ordinary `CREATE TYPE` statements for required composites, followed by `CREATE TEMP TABLE`.

The `temp_table` argument controls the table declaration, not the schema or lifetime of the generated composite types.

Consequently, in the usual search-path configuration:

- The temporary table is created in PostgreSQL's session-local temporary schema.
- Generated composite types are created in the current schema, which may be a persistent application schema.
- Dropping the temporary table or ending its session does not automatically drop those separately created persistent types.
- Recreating the same generated DDL can fail because the composite types already exist.

The exact destination namespace for `CREATE TYPE` is governed by PostgreSQL's current schema and search-path configuration. Therefore, it is not correct to assume generated types are always persistent, either: explicitly arranging creation in a session-local temporary namespace changes their lifetime. The important limitation is that pgpq does not coordinate the table and type lifecycles automatically.

For systems using repeated staging operations or pooled connections, composite type creation, reuse, cleanup, and namespace selection constitute distinct operations from COPY execution.

The generated DDL also does not include automatic type-existence reconciliation or migrations. Reusing a named composite type requires compatibility with its existing attribute order and types; matching the name alone does not establish compatibility.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+1



Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/pg_schema.rs`

`https://www.postgresql.org/docs/18/sql-createtype.html`

`https://www.postgresql.org/docs/18/sql-createtable.html`

### 1.3 Identifier generation, namespace collisions, and OID lookup

The DDL generator uses quoted identifiers and derives each composite type name from its Arrow field name using the suffix `_t`. Although quoting correctly escapes embedded double quotes, it does not solve all naming concerns.

Unqualified generated type names. Composite names are derived from the immediate field name, not a globally unique or fully qualified Arrow field path. Two structurally different nested fields with the same name can therefore produce conflicting `CREATE TYPE` declarations.

Table-name qualification. The DDL helper treats its `table_name` argument as one identifier. Supplying `analytics.events` generates `"analytics.events"`, not `analytics.events` or `"analytics"."events"`. The argument is not a parser for schema-qualified SQL names.

PostgreSQL identifier truncation. PostgreSQL normally limits identifiers to 63 bytes. An Arrow field name plus `_t` may exceed this limit. Distinct generated names can then become identical after truncation, and the actual database type name can differ from the untruncated name returned by `composite_type_names()`.

Namespace-aware type identity. A PostgreSQL type is identified by both its namespace and name, while a pgpq composite-OID mapping uses generated names as keys. Resolving OIDs by `pg_type.typname` alone can select the wrong type when multiple schemas contain identical names.

The catalog relationship needed for namespace resolution is `pg_type.typnamespace → pg_namespace.oid`. The returned database OID must correspond to the type actually used by the destination column, not merely another type with the same unqualified name.

For nested composites, the consequences of an incorrect OID are protocol-level: PostgreSQL checks the nested field's type identity when receiving binary composite values.

These concerns distinguish three separate identities:

1. The Arrow field and its structural position.
2. The generated PostgreSQL type name and namespace.
3. The server-assigned type OID used for binary reception.

pgpq supplies mechanisms for the second and third, but does not implement a comprehensive cross-database or namespace-aware type registry.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+1



Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/pg_schema.rs`

`https://www.postgresql.org/docs/18/sql-syntax-lexical.html`

`https://www.postgresql.org/docs/18/catalog-pg-type.html`

`https://www.postgresql.org/docs/18/catalog-pg-namespace.html`

### 1.4 PostgreSQL schema objects can be constructed independently

The Python API exposes `schema.Column`, `schema.List`, and `schema.PostgresSchema` as constructible objects, not only as results of `encoder.schema()`.

This allows applications to represent supported PostgreSQL scalar and array column definitions and generate their DDL without first constructing an Arrow encoder.

The distinction is limited but useful: the schema layer can be employed as a declarative description of compatible PostgreSQL types, independently from the binary serialization lifecycle. It does not make pgpq a general schema migration system or expose the complete PostgreSQL type system through Python.

The Python constructor for `Column` accepts the name, nullability, and PostgreSQL type, while `PostgresSchema` accepts a list of columns. Its `ddl()` method renders SQL rather than executing it.

Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/pg_schema.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/python/pgpq/_pgpq.pyi`

## 2. Batch validation, stream integrity, and resource behavior

Supplements original §§2.2, 7.2, and 8.1–8.4.

### 2.1 Batch compatibility is positional, not full-schema equality

The Rust `ArrowToPostgresBinaryEncoder::write_batch()` implementation performs a limited set of checks:

1. Verify that the encoder is in its `Encoding` state.
2. Verify that the incoming batch has the expected number of columns.
3. Pair the incoming column arrays with encoder builders by position.
4. Construct typed column encoders, rejecting incompatible physical Arrow array representations.
5. Estimate the output size and serialize the batch.

It does not compare the incoming `RecordBatch` schema to the original encoder schema using complete Arrow field equality. In particular, field names, metadata, and all logical type parameters are not independently reconciled.

For example, an encoder constructed for two `Int64` fields named `revenue` and `cost` can receive another batch containing physically compatible `Int64` columns in reversed semantic order. Its encoders cannot infer that the names have been swapped, and the emitted stream can remain valid despite incorrect column assignment.

Similarly, a decimal encoder operates on the actual incoming decimal array's precision and scale rather than enforcing equality with every parameter in the original field declaration.

The distinction is between:

| Validation level                                  | Responsibility                                      |
| ------------------------------------------------- | --------------------------------------------------- |
| Column count                                      | Checked by pgpq                                     |
| Concrete array representation                     | Checked by the relevant encoder                     |
| Column semantic identity and ordering             | Not comprehensively checked by pgpq                 |
| Full Arrow field equality                         | Not enforced by the batch-writing operation         |
| Compatibility with PostgreSQL destination columns | Ultimately enforced by PostgreSQL's binary receiver |

Explicit encoder mappings do not eliminate this distinction. `try_new_with_encoders()` uses the supplied field-name mapping to establish an ordered vector of builders during construction; batch execution subsequently uses that vector positionally.

Consequence: An encoding operation can complete successfully without proving that the source's logical schema is identical to the schema assumed when the encoder was created.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs`

### 2.2 Encoding errors do not guarantee output-buffer rollback

The Rust `write_batch()` method writes directly into a caller-provided `BytesMut` buffer. It does not construct a private, fully validated batch payload and append it only after the operation succeeds.

Column-encoder construction and byte-size estimation happen before the row-writing loop, so errors at those stages ordinarily occur before that batch's row bytes are appended.

However, once the loop begins, a later `encoder.encode()` error may occur after preceding rows or fields have already been written.

Accordingly:

- `Result::Err` does not guarantee that the output buffer is unchanged.
- A partially encoded row may remain at the end of the buffer.
- The encoder state may still be `Encoding`, despite its output buffer no longer representing a valid continuation of the COPY stream.
- Appending the footer after such a failure would not repair the partially written data.

The Rust caller owns the `BytesMut` buffer and can explicitly restore a known valid boundary where appropriate. The Python wrapper manages that buffer internally, without exposing an equivalent rollback mechanism.

For Python integrations, reconstructing the encoder and starting a new COPY stream is the safer recovery boundary following a failure that may have partially written a batch.

This is distinct from PostgreSQL transaction handling: rolling back the database transaction does not reset pgpq's in-memory encoder state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs`

### 2.3 A failed Python composite-OID update can invalidate the encoder

There is a separate error-state issue in the Python binding of `with_composite_oids()`.

The Rust core method consumes the encoder, applies OIDs, rejects unrecognized mapping keys, and returns a new encoder on success.

The Python wrapper implements its in-place interface by replacing the original native encoder with a temporary placeholder, then assigning the result of the fallible Rust operation back to the Python object.

If the supplied mapping contains an unrecognized composite type name, the Rust operation returns an error. On that path, the Python wrapper does not restore the original native encoder; the placeholder remains.

Consequently, catching that exception and retrying with a corrected OID mapping on the same Python object cannot be assumed to work. The encoder should be reconstructed.

This is a verified observation from the 0.12.0 source control flow, not an execution-tested runtime result. It is an implementation-specific limitation, rather than a guarantee intended by the API.

Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs`

### 2.4 The Python output threshold is not a maximum memory limit

The Python binding initially allocates a `BytesMut` buffer with a capacity of 1 MiB (`BUFF_SIZE = 1024 * 1024`). It emits accumulated bytes after `write_batch()` only when the buffer length exceeds that threshold.

The implementation first serializes the entire incoming batch into the buffer and only then checks whether the threshold was exceeded.

Therefore the threshold controls output-chunk emission, not the maximum intermediate buffer size.

A large batch may generate tens or hundreds of megabytes of binary output before pgpq returns a byte chunk. Peak process memory may simultaneously include:

- The source Arrow arrays.
- The native binary output buffer and any reserved excess capacity.
- The Python `bytes` object constructed from the buffer.
- Driver-side buffers associated with the COPY transport.

The Rust core also calculates a byte-size hint and reserves capacity before encoding. For large or heavily nested batches, this can be substantial even when the input's Arrow representation is comparatively compact.

One additional implementation characteristic matters for nested data: the list encoder's size-estimation procedure iterates over list rows and constructs element encoders to calculate their size hints before the actual serialization pass. This introduces workload-dependent preparation costs that do not exist for every fixed-width scalar column.

Thus pgpq supports streaming across batches, but its memory behavior is principally batch-bounded, not bounded by its Python output-flush threshold. There is no zero-copy guarantee between the native output buffer and the returned Python byte object.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/nested.rs`

## 3. String encoders, JSONB representation, and semantic preservation

Supplements original §§5.2–5.4 and 8.2.

### 3.1 JSONB customization covers three Arrow string layouts

The Python interface exposes three distinct string encoder builders, each supporting explicit PostgreSQL `TEXT` or `JSONB` output.

| Arrow physical type | Encoder builder             | Non-default output |
| ------------------- | --------------------------- | ------------------ |
| `Utf8`              | `StringEncoderBuilder`      | `schema.Jsonb()`   |
| `LargeUtf8`         | `LargeStringEncoderBuilder` | `schema.Jsonb()`   |
| `Utf8View`          | `StringViewEncoderBuilder`  | `schema.Jsonb()`   |

The three builders differ in how they access Arrow string buffers, not in the PostgreSQL JSONB representation they produce.

This distinction is particularly relevant to `arrow-json.array_to_utf8_json_array()`, whose default `large=True` returns `LargeUtf8`, rather than ordinary `Utf8`.

For that default output, the matching customization is:

```
from pgpq import encoders, schemajson_builder = encoders.LargeStringEncoderBuilder.new_with_output(    field,    schema.Jsonb(),)
```

Here, `field` is the Arrow field for the resulting `LargeUtf8` column. The builder is supplied through the complete field-to-builder mapping required by `new_with_encoders()`.

Alternatively, `arrow-json` can produce `Utf8` with `large=False`, in which case `StringEncoderBuilder` is appropriate.

This allows the `arrow-json` integration to retain its large-offset representation rather than requiring an additional Arrow cast merely to match the regular-string builder.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/python/pgpq/_pgpq.pyi`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/text.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/json/src/lib.rs`

### 3.2 JSON null and SQL NULL are different representations

A nullable Arrow string column configured for JSONB can produce two different PostgreSQL values:

| Source Arrow value                  | Encoded PostgreSQL value     |
| ----------------------------------- | ---------------------------- |
| Null Arrow slot                     | SQL `NULL`                   |
| Non-null string containing `null`   | JSONB scalar `null`          |
| Non-null string containing `"null"` | JSONB string scalar `"null"` |
| Non-null string containing `{}`     | Empty JSONB object           |

This is not merely a textual distinction. SQL `NULL` represents the absence of a SQL value; JSONB `null` is a JSON value within a non-null SQL datum.

The `arrow-json` companion introduces an additional semantic interaction. Its implementation converts a top-level `serde_json::Value::Null` result to an Arrow null slot rather than a non-null string containing `null`.

Therefore, the companion's conversion path can collapse a top-level JSON null into SQL NULL after subsequent pgpq JSONB encoding. It does not automatically preserve a distinction between those two representations.

Nested JSON null values inside serialized arrays or objects do not have the same top-level conversion behavior.

For workloads requiring that distinction, the source's null semantics and the companion's serialization behavior are material aspects of the data contract.

Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/json/src/lib.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/text.rs`

`https://www.postgresql.org/docs/18/datatype-json.html`

### 3.3 PostgreSQL imposes additional text and JSONB validity constraints

Arrow `Utf8`, `LargeUtf8`, and `Utf8View` guarantee valid UTF-8 storage, but this does not guarantee acceptance by a PostgreSQL text or JSONB column.

PostgreSQL character strings cannot contain the zero character (`U+0000`), even though it is a valid Unicode code point and can occur in an Arrow UTF-8 string.

Similarly, a string containing syntactically valid JSON may still be rejected by PostgreSQL JSONB because:

- A Unicode escape represents the zero character.
- Surrogate escapes are malformed or do not form valid pairs.
- Characters cannot be represented in the destination database's encoding.
- A JSON numeric literal falls outside PostgreSQL's supported `NUMERIC` range.

These checks are ultimately performed by PostgreSQL rather than pgpq's JSONB string encoder.

PostgreSQL JSONB also normalizes the document's representation, including eliminating insignificant whitespace, discarding object-key ordering, and retaining only the last value for duplicate object keys. Thus conversion from JSON text to JSONB can alter representational properties even when the logical JSON content remains usable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+1



This distinguishes three separate properties: Arrow string validity, JSON document validity, and PostgreSQL JSONB acceptability. None should automatically be assumed to establish the others.

Sources:

`https://www.postgresql.org/docs/18/datatype-json.html`

`https://www.postgresql.org/docs/18/datatype-character.html`

### 3.4 The exposed `Char` schema type is not an additional working Int8 encoding

The Python schema namespace exposes `Char`, and the Rust core contains a `PostgresType::Char` variant. However, this should not be interpreted as supporting an arbitrary Arrow `Int8` to PostgreSQL SQL `CHAR` conversion.

PostgreSQL distinguishes its internal one-byte `"char"` type (OID 18) from SQL `CHAR`, which resolves to the character-string type `bpchar`.

In pgpq 0.12.0, `Int8EncoderBuilder::new_with_output()` accepts `Int2` but rejects `Char`. Earlier attempts to use the latter declared a character-string destination while retaining a two-byte integer payload, leading to invalid binary COPY data.

The rejection is deliberate and covered by the Rust tests. It also illustrates why PostgreSQL type identifiers, SQL type names, and binary wire representations must be considered together when extending an encoder.

Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/scalar.rs`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs`

`https://www.postgresql.org/docs/18/datatype-character.html`

## 4. Rust and Python extension boundaries

Supplements original §§2.1, 5.1, 5.3, and 9.

### 4.1 Rust `build_encoders()` provides reusable default encoder construction

The Rust crate exposes the free function:

```
pgpq::build_encoders(
    fields: &arrow_schema::Fields,
) -> Result<Vec<(String, EncoderBuilder)>, ErrorKind>
```

It constructs the default encoder builder for every supplied Arrow field and returns the builders paired with their field names.

This is useful when employing `ArrowToPostgresBinaryEncoder::try_new_with_encoders()`, because that constructor requires a complete mapping for the source fields.

The helper enables an application to derive all standard encoders, selectively replace builders for non-default representations, and then construct the writer without duplicating the crate's Arrow type-dispatch logic.

Unsupported Arrow types cause the helper to return an error identifying the relevant field rather than a partial collection of successful builders.

The Python interface exposes the corresponding per-field concept through `ArrowToPostgresBinaryEncoder.infer_encoder()`, but not the Rust collection-level helper itself.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs`

### 4.2 Encoder traits are public, but the high-level encoder family is closed

The Rust implementation distinguishes two abstraction levels.

| Rust abstraction | Responsibility                                                             |
| ---------------- | -------------------------------------------------------------------------- |
| `BuildEncoder`   | Construct an array-bound encoder and describe its PostgreSQL output schema |
| `Encode`         | Encode an individual row's field value and estimate column output size     |
| `EncoderBuilder` | Enum of supported built-in encoder-builder implementations                 |
| `Encoder<'a>`    | Enum of supported array-bound encoder implementations                      |

The traits are public, and built-in implementations use generics and `enum_dispatch` to avoid repeating encoding logic across primitive families.

However, the high-level writer stores `Vec<EncoderBuilder>`, where `EncoderBuilder` is a closed enum. Its construction API does not accept arbitrary `Box<dyn BuildEncoder>` implementations or externally defined enum variants.

Consequently, implementing the public `BuildEncoder` or `Encode` traits in an external crate does not by itself make that implementation injectable into `ArrowToPostgresBinaryEncoder`.

The crate's supported customization model is primarily selection and configuration of existing encoder variants, not an unrestricted third-party encoder plugin system.

The distinction affects the extensibility boundary:

- Customizing built-in output representations can use the existing high-level writer.
- Adding an entirely new PostgreSQL binary representation may require modifying or extending the encoder dispatch implementation.
- The public traits remain useful for understanding or reusing lower-level encoding mechanisms, but do not remove the high-level enum boundary.

This explains how pgpq achieves specialized, statically dispatched encoding while retaining a relatively restricted public customization surface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs`

### 4.3 Nested customization is asymmetric between lists and structs

The public builder API exposes nested customization for list elements through:

- `ListEncoderBuilder.new_with_inner()`
- `LargeListEncoderBuilder.new_with_inner()`
- `FixedSizeListEncoderBuilder.new_with_inner()`

The Rust list-builder implementations additionally expose `inner_encoder_builder()`, returning a cloned builder suitable for inspection or modification before constructing a replacement.

However, `StructEncoderBuilder` does not provide the same public customization mechanism for arbitrary individual struct-child encoders.

Its default constructor recursively infers encoders for child fields. The Rust implementation exposes child-builder inspection, but its mutable traversal mechanism is restricted to internal use. The Python wrapper likewise exposes the default struct builder without a `new_with_inner()` equivalent accepting independently configured child encoders.

This distinction has a practical architectural consequence:

A top-level Arrow string or list of strings can be explicitly mapped to JSONB or JSONB[], but a string nested inside an Arrow struct cannot be independently remapped to a JSONB composite attribute through an equivalent public struct-child customization API.

The default struct-to-composite conversion remains available. For different nested representations, the public alternatives are more limited and can involve transforming the source Arrow representation before constructing the encoder.

Source:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/nested.rs`

### 4.4 Python's static typing and runtime argument contract differ

`ArrowToPostgresBinaryEncoder.new_with_encoders()` is annotated in the Python stub as accepting:

```
Mapping[str, EncoderBuilder]
```

The PyO3 runtime implementation, however, accepts a concrete Python `dict` through `PyDict` extraction.

A general object implementing the abstract `Mapping` interface is therefore not guaranteed to satisfy the native runtime argument contract.

For typed integrations, the documented static interface is broader than the runtime binding's actual accepted object representation. Converting an abstract mapping to a regular dictionary preserves the intended semantics without depending on undocumented conversion behavior.

The distinction does not affect the encoder-map contents: the mapping must still include every top-level field expected by the encoder.

Sources:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/python/pgpq/_pgpq.pyi`

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs`

## 5. Remaining Arrow-type boundaries and operational inspection

Supplements original §§3.2, 6.2, 7, and 8.2.

### 5.1 Additional unsupported Arrow representations

The original guide identifies the major unsupported numeric, temporal, dictionary, map, and nested representations. The following physical layouts also lack default encoder cases in the 0.12.0 type dispatcher.

| Arrow type      | Consequential distinction                                                                                              |
| --------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `Null`          | An all-null Arrow array has no PostgreSQL destination type inferable from its data alone; a typed null array is needed |
| `BinaryView`    | Not implemented, although `Binary`, `LargeBinary`, and `FixedSizeBinary` are supported                                 |
| `ListView`      | Not implemented, despite support for regular offset-based `List`                                                       |
| `LargeListView` | Not implemented, despite support for `LargeList`                                                                       |

The distinction between `Utf8View` and `BinaryView` is particularly easy to overlook. The former has a dedicated string encoder; the latter does not have a corresponding binary encoder in 0.12.0.

These are limitations of the default `EncoderBuilder::try_new()` dispatch. They do not mean the underlying values are fundamentally unrepresentable in PostgreSQL.

For example, an Arrow `Null` array can be converted upstream into an appropriately typed all-null array, and view-based binary/list layouts can be materialized into supported Arrow layouts where their semantics permit it.

The library does not provide automatic normalization for these representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source:

`https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/mod.rs`

### 5.2 Independent PostgreSQL COPY progress reporting

Although pgpq does not expose a complete ingestion-progress instrumentation interface, PostgreSQL provides server-side reporting through `pg_stat_progress_copy`.

For a running `COPY FROM STDIN`, PostgreSQL identifies the input as a `PIPE` and reports fields including:

| Field              | Interpretation                                   |
| ------------------ | ------------------------------------------------ |
| `pid`              | Backend process executing COPY                   |
| `relid`            | Destination relation OID                         |
| `command`          | `COPY FROM`                                      |
| `type`             | `PIPE` for standard-input COPY                   |
| `bytes_processed`  | Bytes processed by PostgreSQL                    |
| `tuples_processed` | Rows processed by PostgreSQL                     |
| `bytes_total`      | Known source-file size, or zero when unavailable |

For a streamed application-side source, `bytes_total` is generally unavailable because PostgreSQL has no direct knowledge of the total volume the application will encode and send.

Consequently, the view can establish server-side processing progress but does not provide a complete percentage of the original Arrow dataset unless a separate source-volume measurement is available.

This distinction is useful for observing the two halves of an ingestion pipeline independently:

Client side: Arrow scanning, pgpq encoding, memory consumption, and transport writes.

Server side: PostgreSQL COPY processing, rows received, and destination activity.

The facility belongs to PostgreSQL; pgpq does not require it, configure it, or automatically aggregate its statistics with encoder measurements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



Source:

`https://www.postgresql.org/docs/18/progress-reporting.html`

Scope of this addendum: All pgpq-specific API and implementation observations refer to release 0.12.0, not an unpinned development branch. PostgreSQL behavior is referenced against version 18. No runtime integration tests or independent performance benchmarks were executed for this addendum.