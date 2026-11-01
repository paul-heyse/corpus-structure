# Storing complex PyArrow schemas and data inside PostgreSQL

Technical assessment · November 1, 2026 · PostgreSQL 18 (stable) and PyArrow 26.0.0

## 1. The central architectural distinction

PostgreSQL can serve as the transactional, durable storage engine for highly complex Apache Arrow structures without becoming the authority responsible for interpreting, validating, or enforcing their internal schemas.

This is a genuinely useful architectural distinction, particularly for evolving domain models, deeply nested data, intermediate computational results, heterogeneous records, and systems where the application has richer type semantics than the database.

There are three separate kinds of ownership:

1. Physical ownership: PostgreSQL stores the bytes, handles transactions, concurrency, WAL, recovery, replication, and lifecycle management.
2. Structural ownership: Arrow defines field names, nested types, nullability, metadata, and the representation of the stored values.
3. Semantic ownership: Your application decides what constitutes a valid domain object, which schema versions are compatible, and how data should be interpreted.

These responsibilities need not belong to the same system.

A particularly powerful pattern is to let PostgreSQL own the outer relational structure while Arrow retains authority over the internal typed structure.

PostgreSQL: transactional envelope

Identity · Versions · Relationships · Provenance · Indexes · Transactions

Stores and retrieves opaque binary payloads

Arrow: typed structural payload

Schema · Record batches · Nested values · Metadata

Struct / Map

List / Union

Dictionary

Decimal / Time

Extension types

Nested metadata

Interpretation delegated to Arrow-capable consumers

PyArrow / Rust Arrow / domain runtime

Type-aware computation · Domain validation · Transformations · Schema evolution

The qualification is that PostgreSQL does not natively understand Arrow IPC as a built-in SQL column type. Its standard `bytea` type can preserve an Arrow-serialized representation as ordinary PostgreSQL data, but SQL cannot directly traverse the enclosed Arrow fields without additional decoding machinery.

That difference between native PostgreSQL persistence and native PostgreSQL interpretation is important.

The analysis below focuses on built-in PostgreSQL storage first, then database extensions and alternative integration paths. PostgreSQL 18 is the current stable major version; PostgreSQL 19 remains in release-candidate status as of this research date.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+2



## 2. Available storage mechanisms

| Mechanism                                      | PostgreSQL understands | Arrow fidelity      | Main capability                                              |
| ---------------------------------------------- | ---------------------- | ------------------- | ------------------------------------------------------------ |
| `bytea` containing serialized `pyarrow.Schema` | Opaque bytes           | High                | Persist complex schema definitions                           |
| `bytea` containing Arrow IPC                   | Opaque bytes           | High                | Preserve structured Arrow data without translating its types |
| `bytea` containing Parquet                     | Opaque bytes           | Format-dependent    | Compressed analytical data and archival storage              |
| PostgreSQL Large Objects                       | Opaque byte stream     | High                | Large payloads with partial read/write operations            |
| Native composites and arrays                   | Fields and SQL types   | Partial             | Queryable nested SQL structures                              |
| `jsonb`                                        | JSON values and paths  | Partial             | Flexible SQL queries and indexing                            |
| Columnar PostgreSQL extensions                 | Depends on extension   | Extension-dependent | Analytical execution and native columnar storage             |

Here, high fidelity means that the serialized representation can preserve the supported Arrow information without first coercing it into PostgreSQL's type system. It does not imply that every possible Arrow extension or newly introduced type is readable by every version of every Arrow implementation.

### A. Schema-only persistence

A `pyarrow.Schema` can be serialized independently of any associated data:

```
import pyarrow as paschema_bytes = schema.serialize().to_pybytes()# Recover through the Arrow IPC schema-message reader.message = pa.ipc.read_message(pa.BufferReader(schema_bytes))restored_schema = pa.ipc.read_schema(message)
```

The resulting binary representation can be stored in an ordinary PostgreSQL `bytea` column.

It can preserve supported structural information such as nested fields, child-field nullability, type parameters, schema-level metadata, field-level metadata, and Arrow extension-type annotations.

This allows an Arrow schema registry to be maintained within PostgreSQL without creating corresponding SQL types or modifying table definitions every time the domain structure changes. A schema containing hundreds of deeply nested fields can still occupy one binary column.

The serialized schema does not contain any associated record values.

Source: PyArrow `Schema.serialize()` and IPC implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+2



### B. Complete Arrow IPC payloads

This is the most relevant mechanism when the intent is to preserve both the complex schema and its data.

Arrow IPC defines two principal container representations:

| Characteristic                       | IPC Stream        | IPC File          |
| ------------------------------------ | ----------------- | ----------------- |
| Schema included                      | Yes               | Yes               |
| Multiple record batches              | Yes               | Yes               |
| Sequential reading                   | Yes               | Yes               |
| Random-access batch lookup           | No                | Yes               |
| Dictionary replacement               | Supported         | Restricted        |
| Compressed buffers                   | Optional LZ4/ZSTD | Optional LZ4/ZSTD |
| PostgreSQL can query internal values | No                | No                |

The IPC Stream is attractive for transactional payloads, event batches, and append-oriented processing. The IPC File adds footer-based batch offsets, so an Arrow reader can address specific batches without scanning the entire IPC container—provided the underlying byte source supports random access.

A critical distinction: storing an IPC File in `bytea` does not give PostgreSQL an Arrow-aware random-access interface. The application ordinarily retrieves the PostgreSQL value before using the IPC footer. For selective retrieval directly from the database, storing batches as separate rows may be more effective.

Arrow also provides `RecordBatch.serialize()`, but its encapsulated message does not include the schema. A complete stream is generally a less error-prone self-describing storage unit, particularly when dictionary-encoded fields are involved.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+3



### C. Parquet inside PostgreSQL

Parquet can also be serialized into a `bytea` field without giving PostgreSQL control over its schema.

Its different purpose matters, however. Parquet is an analytical storage format with column-oriented compression, encodings, row groups, and statistics that facilitate selective reads.

Compared with Arrow IPC, Parquet may provide more attractive storage economics for large, cold datasets. But Parquet's logical type system is not identical to Arrow's, and conversions can depend on Arrow schema metadata and reader capabilities.

For highly specialized Arrow types or representations where exact round-trip behavior is essential, IPC is the more direct representation. Parquet merits independent compatibility testing for the relevant types.

Source: Apache Arrow Parquet documentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



## 3. How PostgreSQL physically stores opaque Arrow payloads

The most important underlying feature is TOAST (PostgreSQL storage)—PostgreSQL's mechanism for storing oversized variable-length attributes.

For a normal `bytea` column, PostgreSQL can move a large value out of the heap row into an associated TOAST table. The heap retains a small pointer. PostgreSQL transparently retrieves the value when needed.

Main heap row

artifact_id

schema_id

metadata

TOAST pointer

Transparent PostgreSQL storage indirection

Associated TOAST table

Chunk 1

Chunk 2

Chunk 3

Chunk 4

Chunk 5

Illustrative physical chunks, not Arrow record batches

This gives opaque Arrow data several established PostgreSQL capabilities automatically: transactional storage, MVCC visibility, WAL-based recovery, ordinary database backups, and integration with PostgreSQL permissions and replication mechanisms.

Importantly, TOAST is an internal storage implementation. Its chunks are not exposed as individual Arrow objects and are not normally addressable independently through Arrow APIs.

### Storage characteristics

| Property                           | PostgreSQL 18 behavior                                                       |
| ---------------------------------- | ---------------------------------------------------------------------------- |
| Maximum `bytea` value              | Just under 1 GiB                                                             |
| Typical TOAST activation threshold | Heap tuple exceeds approximately 2 KiB                                       |
| Physical out-of-line chunk size    | Approximately 2 KiB by default                                               |
| Default storage strategy           | `EXTENDED`                                                                   |
| Alternative storage strategy       | `EXTERNAL`, which disables TOAST compression but permits out-of-line storage |
| Metadata-only row updates          | Normally preserve unchanged out-of-line payload values                       |
| Partial blob modification          | Generally requires reconstructing/replacing the value                        |

An easily overlooked benefit is that updating relational metadata need not rewrite an unchanged Arrow payload. PostgreSQL explicitly documents preservation of unchanged out-of-line values during updates.

That makes the combination of mutable metadata and relatively immutable structured payloads more attractive than a simplistic understanding of PostgreSQL row-oriented storage might suggest.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+1



### When `EXTERNAL` storage is advantageous

PostgreSQL supports:

```
ALTER TABLE arrow_payload
    ALTER COLUMN ipc_payload SET STORAGE EXTERNAL;
```

`EXTERNAL` allows large payloads to be TOASTed without PostgreSQL applying its own compression.

This is worth investigating when Arrow IPC already uses LZ4/ZSTD compression. Avoiding an additional PostgreSQL compression attempt can reduce unnecessary CPU work.

Conversely, for uncompressed Arrow IPC, PostgreSQL's default `EXTENDED` setting may reduce storage significantly for compressible data. The better choice depends on payload characteristics and read/write frequency; the two options do not have a universal performance ranking.

### Large Objects: a distinct native mechanism

PostgreSQL Large Objects provide an alternative to `bytea`, with support for values up to approximately 4 TiB and efficient partial reading or updating.

The tradeoff is more complicated object lifecycle and permission management. A referencing table typically stores an OID, while Large Object creation, access, and deletion are handled separately. Deleting the referencing row does not automatically unlink the object.

For self-contained Arrow payloads below the `bytea` limit, ordinary `bytea` is generally simpler. Large Objects become more interesting when a payload is exceptionally large or true incremental byte-range operations are important.

Official PostgreSQL documentation:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+2



## 4. Why Arrow can be a better structural authority than PostgreSQL

The strongest argument for this approach is not merely that Arrow supports complex types. It is that the application can retain structural information that either has no equivalent PostgreSQL type or would require substantial schema translation and coordination to represent relationally.

### Type fidelity

| Arrow capability              | Native PostgreSQL representation                  | Benefit of retaining Arrow                                            |
| ----------------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| Deeply nested `struct`        | SQL composite types                               | No dependency on a matching hierarchy of SQL type definitions         |
| Nested variable-length `list` | Arrays or JSONB                                   | Retains child types, nesting, and Arrow offsets                       |
| `map`                         | JSONB or custom composite representation          | Preserves typed keys and entries rather than coercing to JSON objects |
| Dense/sparse `union`          | Discriminators with several columns or JSONB      | Preserves explicit variant encoding                                   |
| `dictionary`                  | Usually decoded into SQL values                   | Preserves Arrow dictionary representation                             |
| `decimal256`                  | PostgreSQL `numeric`, subject to limits           | Retains the original Arrow precision and scale specification          |
| Nanosecond timestamps         | PostgreSQL timestamps have microsecond resolution | Avoids conversion-related loss of temporal precision                  |
| Field-level metadata          | Additional tables or custom annotations           | Keeps semantic annotations attached to the field                      |
| Arrow extension types         | User-defined SQL types or separate metadata       | Preserves the extension's storage-type and annotation contract        |
| Run-end encoded arrays        | No directly equivalent SQL storage type           | Retains Arrow's encoded representation                                |

PostgreSQL does support substantial native structural complexity. Composite types can appear inside other composite types, and arrays may contain composite elements. It would therefore be inaccurate to characterize PostgreSQL as supporting only flat relational records.

However, composite types are catalog objects, and their structural definitions belong to PostgreSQL. They do not reproduce the complete Arrow type system or its metadata model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+2



### The important distinction for extension types

Arrow extensions are particularly interesting for domain-rich applications.

An extension type combines an underlying Arrow storage type with an extension name and serialized metadata. This can represent domain-specific semantics without defining a corresponding PostgreSQL type.

For example, an application could distinguish several kinds of identifiers, measurements, domain quantities, or symbolic references even when their underlying physical storage type is the same.

The IPC representation can retain the extension annotations, but a reader needs an appropriate extension implementation or registration to reconstruct the specialized behavior. Preserving extension metadata is not equivalent to preserving executable Python classes or arbitrary application objects.

That is a useful separation of durable information from executable interpretation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v27.0.0.dev39+1



### Why JSONB is not an equivalent substitute

PostgreSQL `jsonb` is valuable precisely because the database interprets JSON values, allows operators over their contents, and supports indexing. It does not generally enforce a fixed business schema.

But conversion to JSONB introduces a different semantic representation. JSONB does not preserve duplicate object keys or original object-key order, and it applies JSON-compatible numeric and value restrictions. Arrow's typed integers, decimals, dictionary arrays, unions, nested field metadata, and null representations are not automatically retained.

Thus JSONB is useful as a queryable projection, but is not generally an exact representation of an arbitrary Arrow structure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+1



## 5. A hybrid model: relational identity, Arrow structure

For the use case described, a particularly compelling arrangement is a PostgreSQL schema registry combined with opaque Arrow payload records and optional queryable projections.

The following is an illustrative design, not an assumption about your existing database.

```
CREATE TABLE arrow_schema (
    schema_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_ipc      bytea NOT NULL,
    schema_sha256   bytea NOT NULL UNIQUE,
    registered_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE arrow_artifact (
    artifact_id     uuid PRIMARY KEY,
    schema_id       bigint NOT NULL REFERENCES arrow_schema(schema_id),
    kind            text NOT NULL,
    payload_format  text NOT NULL
        CHECK (payload_format IN ('ipc_stream', 'ipc_file', 'parquet')),
    payload         bytea NOT NULL,
    indexed_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX arrow_artifact_kind_created
    ON arrow_artifact (kind, created_at);

CREATE INDEX arrow_artifact_metadata_gin
    ON arrow_artifact USING gin (indexed_metadata);
```

Here, PostgreSQL governs the identity of an artifact, its relationships, timestamp, declared representation, and any explicitly exposed metadata.

Arrow governs the actual payload structure.

This creates two independent forms of schema evolution:

Relational schema evolution affects persistent identities, relationships, indexes, and query contracts. It can be relatively infrequent.

Arrow schema evolution affects internal fields, nested types, application semantics, and structured results. It can proceed without corresponding PostgreSQL migrations as long as the relational envelope remains suitable.

The database still validates the relational columns and foreign keys. It does not verify that the binary payload is valid Arrow IPC or that its embedded schema matches the referenced registry entry.

The `schema_sha256` shown above would be calculated by the application from serialized bytes. It identifies an exact serialization, not necessarily a canonical semantic schema identity across different writer versions or serialization settings.

### Keeping the schema registry separate

A separate registry is useful when multiple payloads share a schema, when schema definitions need independent version histories, or when software needs to inspect metadata without retrieving data.

However, complete Arrow IPC streams already embed their schema. Consequently, a registry plus self-contained IPC payloads deliberately duplicates some schema information.

That redundancy has a purpose: independent recovery and interoperability on one side, shared schema identity and catalog operations on the other.

For workloads with very many small payloads, the repeated schema overhead could become important. Standalone record-batch messages with separately managed schemas are another option, but they require tighter reader/writer contracts, especially around dictionaries.

### Selectively exposing queryable fields

A hybrid model need not require an all-or-nothing decision about which information PostgreSQL understands.

For example, the application could expose stable attributes such as `entity_id`, `object_kind`, `timestamp`, `status`, or selected domain references as PostgreSQL columns, while retaining the full Arrow payload.

Queries could then join, filter, order, authorize, and locate artifacts using ordinary PostgreSQL indexes, retrieving the Arrow bytes only for relevant results.

`indexed_metadata` serves a complementary purpose where selected attributes are flexible or sparse. Its JSONB contents should be understood as a deliberately maintained projection, not automatically the authoritative Arrow record.

This can keep the indexing surface relatively small while supporting much richer internal schemas.

## 6. Python and Rust interoperability

This approach does not require a specialized PostgreSQL driver or a custom PostgreSQL data type.

### PyArrow serialization

A compact, illustrative implementation using a self-contained IPC stream:

```
import pyarrow as paimport psycopgdef encode_arrow(table: pa.Table) -> bytes:    sink = pa.BufferOutputStream()    options = pa.ipc.IpcWriteOptions(compression="zstd")    with pa.ipc.new_stream(        sink, table.schema, options=options    ) as writer:        writer.write_table(table)    return sink.getvalue().to_pybytes()def decode_arrow(payload: bytes) -> pa.Table:    with pa.ipc.open_stream(        pa.BufferReader(payload)    ) as reader:        return reader.read_all()
```

Psycopg 3 adapts Python `bytes`, `bytearray`, and `memoryview` to PostgreSQL `bytea`, so normal parameterized inserts can store the serialized payload. No Arrow-specific PostgreSQL extension is required.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation+1



```
payload = encode_arrow(table)with psycopg.connect(dsn) as conn:    conn.execute(        """        INSERT INTO arrow_artifact            (artifact_id, schema_id, kind, payload_format, payload)        VALUES (%s, %s, %s, %s, %s)        """,        (artifact_id, schema_id, kind, "ipc_stream", payload),    )
```

In practice, application code would register the schema and establish the `schema_id` before this insert, typically within the same transactional operation.

The stored payload can be read back through Psycopg and decoded using the original Arrow schema and record batches embedded in the stream.

### Rust Arrow integration

The Rust `arrow-ipc` crate provides `StreamReader`, `StreamWriter`, `FileReader`, and `FileWriter` for the Arrow IPC formats.

That means a payload written by PyArrow can be consumed by an Arrow-compatible Rust implementation without converting its contents into PostgreSQL composite values or JSON first.

Compatibility still depends on the specific Arrow features, extensions, IPC version, and codecs supported by the participating implementations.

This is a potentially important way to retain a common data representation across Python and Rust components.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.rs\&sz=32)

Rust+2



## 7. Performance and operational considerations

There are meaningful benefits, but the storage boundary introduces tradeoffs that should not be obscured.

| Consideration             | Consequence                                                                           |
| ------------------------- | ------------------------------------------------------------------------------------- |
| Schema migrations         | Internal Arrow schema changes need not cause PostgreSQL DDL migrations                |
| Transactional consistency | Arrow payloads and relational metadata can participate in one transaction             |
| PostgreSQL query planning | Planner statistics and predicates do not automatically operate on opaque Arrow fields |
| Payload transfer          | Reading a `bytea` value generally retrieves the full value                            |
| Memory use                | PostgreSQL-to-client transfer is not an end-to-end Arrow zero-copy operation          |
| Compression               | Arrow IPC compression and PostgreSQL TOAST compression may overlap                    |
| Frequent updates          | Replacing large payloads generates new stored values and associated WAL activity      |
| Indexing                  | Only relational columns and separately exposed projections can be indexed directly    |
| Backup and replication    | Payload bytes participate in normal PostgreSQL persistence and replication machinery  |
| Validation                | Application or Arrow readers must establish structural and semantic correctness       |

### Chunking is particularly important

For large Arrow datasets, storing one enormous IPC payload is not always the most useful design.

An alternative is to store multiple self-contained Arrow IPC chunks, each as a PostgreSQL row, indexed by artifact identity and sequence number.

This yields a different unit of transactional storage, retrieval, compression, and garbage collection.

For example, if a dataset is logically partitioned into 100 independent batches, the application can retrieve only the relevant batch rows rather than an entire monolithic payload. It also avoids approaching the `bytea` size limit.

The tradeoff is more rows, indexes, schema duplication, and chunk lifecycle coordination. Splitting at meaningful Arrow batch or partition boundaries is usually more useful than arbitrary byte slicing.

### Compression and read behavior

For read-heavy payloads, the choice between IPC stream, IPC file, compression codec, and PostgreSQL TOAST configuration can affect whether operations are dominated by disk I/O, network transfer, decompression, or application computation.

Arrow IPC can expose arrays without copying their data buffers when the source memory and representation permit it. But obtaining those bytes from PostgreSQL still requires the database and client protocol to transfer the payload. An in-process zero-copy Arrow view should not be mistaken for zero-copy database retrieval.

PyArrow's IPC readers additionally support top-level field selection using `IpcReadOptions.included_fields`. This can reduce the work performed during Arrow deserialization, but it does not by itself make PostgreSQL fetch only the selected columns from an opaque `bytea` payload.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



## 8. Relationship to existing PostgreSQL/Arrow tooling

The relevant libraries are complementary, but several address a different problem.

| Library or extension | Actual role                                                      | Implication                                                                                                                     |
| -------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Psycopg 3            | PostgreSQL client and binary parameter adaptation                | Straightforward persistence of opaque Arrow IPC bytes                                                                           |
| SQLAlchemy           | SQL data modeling and persistence abstraction                    | `LargeBinary` can represent the opaque column; Arrow serialization remains outside the ORM                                      |
| ADBC PostgreSQL      | Arrow-oriented database access and bulk ingestion                | Converts between Arrow and PostgreSQL's supported types; does not automatically preserve arbitrary nested schemas as opaque IPC |
| pgpq                 | Converts Arrow values into PostgreSQL binary COPY representation | Useful for loading typed SQL columns, not for preserving an arbitrary Arrow schema unchanged                                    |
| pg_duckdb            | Adds DuckDB-based analytical execution to PostgreSQL             | Does not automatically make arbitrary IPC bytes inside `bytea` SQL-queryable                                                    |
| pgColumnar           | Alternative PostgreSQL columnar table access method              | Stores data in its own native columnar format, not a general-purpose opaque Arrow schema store                                  |

Two distinctions are especially consequential.

ADBC PostgreSQL is not the same as Arrow-native PostgreSQL persistence. Its type mapping explicitly converts Arrow values into supported PostgreSQL representations, with limitations for certain types. That is ideal for other workloads, but potentially counter to the goal of retaining Arrow's own structural authority.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 26 (dev) Documentation



pgColumnar is a different storage architecture. It has Arrow and Parquet integration, but its documented native on-disk format is PGCN. Its current published lineage remains pre-release, and the project explicitly cautions against using it as a production system of record for irreplaceable data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pgxn.org\&sz=32)

pgxn.org+1



For a design where the database deliberately should not understand or validate the internal schema, the simpler `bytea` approach may actually be more aligned with the intended division of responsibility than adopting a sophisticated columnar extension.

## 9. Limitations of intentionally opaque storage

The reduced validation burden is a genuine advantage, but it also changes where correctness must be established.

An opaque binary column accepts bytes regardless of whether they form valid Arrow IPC. A valid IPC stream can still contain a schema that differs from the claimed external schema identifier, and a structurally valid Arrow record may still violate domain rules.

The relevant architectural boundary is therefore validation by the appropriate consumer, rather than validation by every persistence layer.

This distinction also affects security. PostgreSQL can enforce permissions and row-level security on the containing records, but it cannot independently authorize or redact selected nested fields inside an opaque payload. If fine-grained access control is required inside an artifact, the application must supply it or expose the relevant boundaries relationally.

Likewise, a complex Arrow schema does not automatically give PostgreSQL knowledge of domain relationships. Referential integrity is available for relations explicitly represented in SQL, not for references hidden exclusively inside the IPC payload.

Finally, long-term durability needs attention to format and semantic compatibility. Arrow IPC is a documented interoperable format, but preserving the serialized bytes does not guarantee that an application-specific extension implementation will remain available indefinitely.

A durable system may therefore retain the writer's format version, domain-schema version, and extension identifiers alongside the data, rather than relying solely on the fact that the bytes can be stored successfully.

## 10. Overall assessment

For the characteristics you've described, I see three especially valuable architectural opportunities.

First, significantly greater independence between database schema evolution and domain-model evolution. A PostgreSQL schema could remain stable while Arrow structures evolve rapidly, including changes to deeply nested types, metadata, and specialized domain representations.

Second, PostgreSQL can remain the authoritative transactional and relational system without becoming the authoritative type system for every data object. This retains PostgreSQL's advantages for identity, provenance, concurrency, indexing, and integrity where those capabilities are appropriate, without imposing its data model everywhere.

Third, a common Arrow representation can survive the full persistence round trip between Python and Rust. Rather than repeatedly translating complex structures into SQL composites or JSON and back again, the storage boundary can preserve an Arrow IPC representation for Arrow-aware consumers.

The main architectural tradeoff is straightforward: schema fidelity and application-level flexibility are gained at the cost of SQL visibility into the opaque contents.

For self-contained artifacts, evolving domain records, intermediate structured outputs, and objects that primarily need transactional persistence and later reconstruction, that tradeoff can be highly favorable.

For large analytical datasets requiring frequent selective SQL predicates, aggregation, or projections over internal fields, a hybrid approach—opaque Arrow payloads plus indexed relational projections—or a separate analytical storage path may be more appropriate.

### Primary technical references

Apache Arrow

`https://arrow.apache.org/docs/python/ipc.html`

`https://arrow.apache.org/docs/python/generated/pyarrow.Schema.html`

`https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcWriteOptions.html`

`https://arrow.apache.org/docs/format/Columnar.html`

`https://docs.rs/arrow-ipc/latest/arrow_ipc/`

PostgreSQL

`https://www.postgresql.org/docs/18/storage-toast.html`

`https://www.postgresql.org/docs/18/datatype-binary.html`

`https://www.postgresql.org/docs/18/lo-intro.html`

`https://www.postgresql.org/docs/18/rowtypes.html`

`https://www.postgresql.org/docs/18/datatype-json.html`

Integration

`https://www.psycopg.org/psycopg3/docs/basic/adapt.html`

`https://arrow.apache.org/adbc/main/driver/postgresql.html`

`https://github.com/adriangb/pgpq`

`https://github.com/duckdb/pg_duckdb`

`https://commandprompt.github.io/pgcolumnar/limitations/`

The most interesting design question that follows is not whether PostgreSQL can persist these structures—it can—but where to draw the boundary between a queryable relational projection and an authoritative, potentially much richer Arrow object. That boundary can be chosen independently for different classes of data, rather than imposed uniformly across the database.