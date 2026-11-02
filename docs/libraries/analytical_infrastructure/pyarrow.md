# PyArrow 26.0.0 — Comprehensive Library Capability Reference

Apache Arrow Python bindings | Stable release: 26.0.0 | Research date: October 20, 2026

Primary documentation: [https://arrow.apache.org/docs/python/](https://arrow.apache.org/docs/python/?utm_source=chatgpt.com)

Release notes: [https://arrow.apache.org/blog/2026/10/08/26.0.0-release/](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com)

Source repository: [https://github.com/apache/arrow](https://github.com/apache/arrow?utm_source=chatgpt.com)

## 1. Executive orientation

PyArrow is the Python interface to Apache Arrow's native columnar data structures, computational kernels, data access facilities, serialization protocols, and interoperability mechanisms.

Its significance extends well beyond converting between pandas DataFrames and Parquet files. PyArrow provides a substantial foundation for constructing high-performance data systems around a common, strongly typed, columnar representation, with much of the execution performed by native C++ implementations.

In particular, PyArrow combines:

- A rich data model: Typed, nullable, potentially nested and dictionary-encoded arrays, schemas, tables, record batches, extension types, and tensor representations.
- Native computation: Vectorized compute kernels for arithmetic, comparison, strings, temporal operations, aggregation, sorting, selection, hashing, and more.
- Relational execution: Expression trees, projection and filtering, grouping and aggregation, joins, ordered operations, and access to the Acero execution engine.
- Dataset processing: Lazy scanning of partitioned, potentially remote datasets, predicate and projection pushdown, fragment-level pruning, parallel scanning, and incremental batch delivery.
- Storage and interchange: Parquet, Arrow IPC, Feather V2, CSV, JSON, ORC, memory-mapped files, and native filesystem interfaces.
- Interoperability: NumPy, pandas, Arrow C Data and C Stream interfaces, the DataFrame Interchange Protocol, DLPack, and Arrow-aware databases and execution engines.
- Transport and extensibility: Arrow Flight RPC, custom extension types, user-defined compute functions, and interfaces to native code.

These capabilities can be composed into pipelines that avoid repeated Python-object materialization, minimize unnecessary data copying, and share consistent data representations between storage, computation, database access, and application logic.

The important architectural distinction is that PyArrow is both a data interchange substrate and a computational toolkit, but not a complete general-purpose database management system. It offers native relational operators and streaming execution mechanisms, while leaving responsibilities such as SQL planning, transactions, database catalog management, and durable multi-writer coordination to other systems.

### Version baseline

Apache Arrow 26.0.0 was announced on October 8, 2026, with the PyArrow package published to PyPI on October 9. It is the current stable release verified for this reference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Version 26 introduces meaningful advances in DLPack interoperability, native compute functionality, run-end encoding support, and Acero integration. It also changes compatibility requirements: Python 3.10 is no longer supported, NumPy 2.x is required, and pandas versions earlier than 2.2.2 are no longer supported by the integration. Python 3.15 wheels, including free-threaded builds, are available. These points are discussed further under version-specific changes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow



## 2. Columnar data model and type system

The data model is foundational to almost every other PyArrow capability. Understanding the distinction between buffers, arrays, record batches, and tables is particularly important because it determines where operations can share memory, where they must allocate, and how computation can proceed incrementally.

### 2.1 Core objects and their roles

| Abstraction            | Responsibility                                              | Important property                                      |
| ---------------------- | ----------------------------------------------------------- | ------------------------------------------------------- |
| `pa.DataType`          | Specifies the logical and physical interpretation of values | Types are explicit, not inferred anew at each operation |
| `pa.Field`             | Associates a name, type, nullability, and metadata          | Useful for schema contracts and nested structures       |
| `pa.Schema`            | Defines an ordered collection of fields and metadata        | Can be compared, transformed, and serialized            |
| `pa.Buffer`            | References a region of memory                               | Supports shared ownership and zero-copy slicing         |
| `pa.Array`             | Represents a single typed, contiguous sequence of values    | Typically backed by validity, offset, and value buffers |
| `pa.ChunkedArray`      | Represents one logical column as several arrays             | Avoids requiring a large column to be consolidated      |
| `pa.RecordBatch`       | Groups equally sized arrays under one schema                | Natural unit for streaming and incremental execution    |
| `pa.Table`             | Represents a complete logical table with chunked columns    | Convenient for materialized relational operations       |
| `pa.RecordBatchReader` | Exposes a sequential stream of record batches               | Allows consumption without materializing a whole table  |

The distinction between a `RecordBatch` and a `Table` has architectural consequences. A record batch is a concrete unit of columnar data, while a table can concatenate logical columns across many separately allocated arrays.

Consequently, batches can flow through readers, compute stages, and writers without first creating one large contiguous allocation. This can reduce peak memory consumption and allow processing to begin before the entire input has been read.

Similarly, slicing an Arrow array or table can often reuse existing buffers. Filtering, gathering rows, type conversions, sorting, and certain transformations generally require new buffers.

Primary reference: [Data types and in-memory data model](https://arrow.apache.org/docs/python/data.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 2.2 Rich and semantically precise types

PyArrow's type system is more expressive than a conventional set of NumPy numerical dtypes or loosely typed Python dictionaries.

Numerical and temporal types

These include signed and unsigned integers of several widths, floating-point types including `float16`, decimal types with explicit precision and scale (`decimal32`, `decimal64`, `decimal128`, `decimal256`), dates, timestamps with time units and optional time zones, durations, and time-of-day values.

Explicit schemas help prevent accidental narrowing, temporal-unit changes, or implicit conversion of exact decimal values to binary floating point.

Nested and structured types

Arrow supports `Struct`, `List`, `LargeList`, fixed-size lists, list views, `Map`, and dense or sparse unions. Nullability can be expressed at multiple levels, such as a nullable struct containing a separately nullable field.

For example, a list of structured measurements need not be exploded into Python objects or flattened into a wide collection of relational columns simply to move it through a pipeline.

Dictionary and run-end encoding

`DictionaryArray` represents values using integer indices referencing a dictionary of distinct values. It is particularly useful for repetitive strings and categorical data, although dictionary unification and decoding may be necessary when combining independently encoded columns.

`RunEndEncodedArray` represents consecutive runs of repeated values through run-end positions and associated values. It can be effective for highly repetitive ordered data. Unlike dictionary encoding, its advantage depends strongly on the sequence of values, not just their cardinality.

Version 26 extends support for run-end encoded operations, including nested values and searching sorted data.

View and semantic types

Binary and string view types (`binary_view`, `string_view`) allow variable-length values to reference underlying byte storage differently from conventional offset-based arrays. The type system also includes fixed-shape tensor, UUID, JSON, and opaque extension representations.

These facilities create opportunities for richer domain semantics without necessarily requiring custom storage layouts. However, a type being representable does not imply that every compute kernel or file-format reader supports it.

Sources: [PyArrow data types](https://arrow.apache.org/docs/python/data.html?utm_source=chatgpt.com), [Python API reference](https://arrow.apache.org/docs/python/api.html?utm_source=chatgpt.com), and [Arrow 26 release notes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 2.3 Schemas as executable contracts

`pa.schema`, `pa.field`, `pa.type_for_alias`, `pa.unify_schemas`, and array or table casting facilities provide mechanisms for defining, inspecting, normalizing, and reconciling data representations.

A schema can carry field-level and schema-level metadata, while its explicit types determine how values are interpreted by Arrow operations.

This supports several architectural patterns:

- Making type definitions first-class rather than repeatedly inferring them from untyped input.
- Representing nested, nullable, and precision-sensitive data consistently across processing stages.
- Reconciling compatible schemas when reading multiple files or constructing combined tables.
- Preserving selected semantic metadata across Arrow-aware interfaces.

There are important qualifications. `unify_schemas` does not implement arbitrary business-level schema evolution. Metadata does not automatically enforce domain invariants, foreign keys, units, or every downstream interpretation. Casts can reject values, lose information when explicitly made unsafe, or require a physical conversion.

### 2.4 Null, NaN, missing, and validity semantics

Arrow generally represents missingness through a validity bitmap rather than by assigning one special numeric value to every missing element.

This allows null to remain distinct from IEEE floating-point NaN. It also permits nullable integers, booleans, temporal values, and nested data without relying on Python `None` objects for each element in memory.

However, several semantic distinctions require care:

- Arrow null and floating-point NaN are not interchangeable.
- Scalar arithmetic, comparisons, boolean combinations, and aggregations have operation-specific null behavior.
- Three-valued logical functions such as `and_kleene` and `or_kleene` are distinct from ordinary boolean operations.
- Aggregations may expose `skip_nulls`, `min_count`, or related policies.
- Conversion from pandas or Python objects can map sentinel values into Arrow nulls, depending on the conversion path.

The resulting benefit is a stronger, more explicit representation of missingness, not an automatic guarantee of identical missing-value semantics in every adjacent library.

References: [Compute functions](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com) and [pandas integration](https://arrow.apache.org/docs/python/pandas.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



## 3. Native computational capabilities

`pyarrow.compute`, conventionally imported as `pc`, exposes Arrow's native computation engine to Python. Many operations execute on entire arrays or chunks in compiled code rather than iterating through individual Python objects.

The most consequential distinction is between executing an operation on already materialized data and expressing that operation as part of a larger scan or execution plan.

### 3.1 Main compute families

| Family                      | Representative capabilities                                                          | What it can replace or simplify                   |
| --------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| Arithmetic and comparison   | Checked arithmetic, comparisons, bitwise operations, mathematical functions          | Python loops and repeated NumPy conversions       |
| Boolean and null operations | `is_null`, `is_valid`, `fill_null`, `if_else`, Kleene logic, `coalesce`              | Custom missing-value handling                     |
| Selection                   | `filter`, `take`, `drop_null`, `indices_nonzero`                                     | Per-row selection logic                           |
| Ordering and ranking        | `sort_indices`, `select_k_unstable`, `rank`, array sorting                           | Bespoke sorting and top-k routines                |
| Scalar aggregation          | Sum, mean, extrema, variance, quantiles, count-distinct, skewness, kurtosis          | Custom reduction loops                            |
| Grouped aggregation         | Hash-grouped sums, counts, means, and other supported aggregate kernels              | Common `GROUP BY`-like operations                 |
| Strings and binary          | UTF-8 transformations, substring search, pattern matching, splitting, parsing, regex | Python string operations over large columns       |
| Temporal                    | Extract, parse, format, difference, rounding and calendar-oriented operations        | Per-record date/time manipulation                 |
| Nested data                 | List-element operations, struct-field access, list flattening, map lookup            | Repeated nested Python-object traversal           |
| Encoding and categorization | Dictionary encoding/decoding, run-end encoding/decoding, unique and value counts     | Custom categorical and run-length representations |
| Type transformation         | Casts and reinterpretation where supported                                           | Ad hoc data normalization                         |

Some functions operate element by element; others consume an entire array, compute statistics, reorder values, or require cross-row state. These differences matter when considering streaming and expression pushdown.

The library also exposes function registries, kernel metadata, and option objects. These are valuable when generating typed operations programmatically or inspecting what kernels and signatures an Arrow build supports.

References: [Compute user guide](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com) and [complete compute API](https://arrow.apache.org/docs/python/api/compute.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 3.2 Expressions and declarative computation

`pyarrow.compute.Expression` provides a representation of computations referencing fields and scalar values.

A typical expression can combine predicates and projections:

```
import pyarrow.compute as pcpredicate = (    (pc.field("status") == "active")    & (pc.field("amount") > 100))adjusted_value = pc.field("amount") * 1.05
```

Illustrative example; not executed.

The expression is not itself an array calculation. It can be supplied to a dataset scanner or other compatible execution interface, allowing the calculation to take place when the underlying data is processed.

This distinction enables several important combinations: projecting computed fields during a scan, filtering before data is fully materialized, and reusing native expression representations across different Arrow execution interfaces.

Expressions are not arbitrary Python syntax trees. They represent Arrow-supported operations with specific type and execution constraints. In particular, projection expressions must produce one output per input row; global aggregation and order-dependent transforms are different computational categories.

Reference: [Compute expressions and projection](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 3.3 Grouped aggregation and analytical reductions

`Table.group_by(...).aggregate(...)` exposes native grouping and aggregate execution without requiring SQL or another DataFrame library.

The available aggregate kernels cover common reductions, with support for configurable null-handling behavior. Other compute capabilities include approximate median via T-Digest and exact quantile functionality with selectable interpolation.

The difference between exact and approximate aggregates is important. They are not interchangeable when an application requires reproducibility, specific numerical error behavior, or exact statistical definitions.

Grouped results should not be assumed to preserve input order. Hash-based grouping, parallel execution, and later sorting can have different ordering and memory characteristics.

Reference: [Grouped aggregations](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 3.4 Extending compute with user-defined functions

PyArrow exposes an experimental Python UDF registration system covering several function categories:

| API                              | Role                                  |
| -------------------------------- | ------------------------------------- |
| `pc.register_scalar_function`    | Row-aligned scalar computation        |
| `pc.register_vector_function`    | Batch-oriented vector functions       |
| `pc.register_aggregate_function` | Custom aggregate computation          |
| `pc.register_tabular_function`   | Functions that produce tabular output |

This capability is easily overlooked because the introductory compute documentation emphasizes scalar examples. The complete API reference exposes a broader registration surface.

These extensions can make custom operations visible through Arrow's function registry, but registration does not turn Python implementations into optimized native C++ kernels. Python execution, callback overhead, type constraints, and the experimental status of these interfaces remain material considerations. Some UDF categories have specific aggregation or batching limitations.

For performance-sensitive operations already covered by native kernels, expressing the operation through the existing compute system is generally a more compelling architectural opportunity than replacing it with Python callbacks.

References: [Scalar/vector UDF documentation](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com), [vector UDF API](https://arrow.apache.org/docs/python/generated/pyarrow.compute.register_vector_function.html?utm_source=chatgpt.com), [aggregate UDF API](https://arrow.apache.org/docs/python/generated/pyarrow.compute.register_aggregate_function.html?utm_source=chatgpt.com), and [tabular UDF API](https://arrow.apache.org/docs/python/generated/pyarrow.compute.register_tabular_function.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+3



## 4. Relational operations and streaming execution

PyArrow's relational capabilities are substantial enough to support more than isolated array transformations.

There are three different interfaces to distinguish:

1. Direct `Table` operations, which return materialized results.
2. Dataset scans, which can defer reading and stream filtered or projected batches.
3. Acero execution declarations, which compose native operators into an execution plan.

They overlap in functionality but differ in their execution model, stability, and resource requirements.

### 4.1 Relational operations on tables

`pa.Table` provides native operations for column selection, casting, filtering, sorting, aggregation, and joins.

In particular, `Table.join` supports:

- Inner, left outer, right outer, and full outer joins.
- Left/right semi joins and left/right anti joins.
- Different key names on either input.
- Key coalescing and suffix handling.
- Residual filtering of matching rows.
- Multithreaded execution.

Semi and anti joins are especially useful because they express existence and nonexistence relationships directly, avoiding the need to construct and later discard columns from an ordinary join.

`Table.join_asof` supports a different problem: matching observations against nearby values on an ordered key. It can combine exact grouping keys with temporal or numerical proximity, and it requires sorted inputs. The sign of the tolerance controls whether matches are taken from the past or future relative to the left-hand key.

These facilities are useful for event alignment, time-series enrichment, reference-data matching, and other relational operations that do not inherently require a SQL engine.

However, a table join returns a new table. Hash joins and sorting may require considerable working memory, and output ordering should not be inferred merely from the input order.

Primary reference: [Table API, including joins and as-of joins](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 4.2 Acero: the native streaming execution engine

`pyarrow.acero` exposes Apache Arrow's Acero engine, allowing native operators to be assembled into execution plans through `acero.Declaration`.

The documented Python node options include:

| Node                                 | Function                                |
| ------------------------------------ | --------------------------------------- |
| `TableSourceNodeOptions`             | Reads from an existing Arrow table      |
| `RecordBatchReaderSourceNodeOptions` | Streams from a record-batch reader      |
| `ScanNodeOptions`                    | Scans an Arrow dataset                  |
| `FilterNodeOptions`                  | Applies an expression-based filter      |
| `ProjectNodeOptions`                 | Derives or selects output columns       |
| `AggregateNodeOptions`               | Executes global or grouped aggregations |
| `OrderByNodeOptions`                 | Orders results                          |
| `HashJoinNodeOptions`                | Joins two data streams                  |

The engine can consume input batches, apply supported operations in compiled code, and expose output through a reader instead of always collecting a complete result table.

This creates an opportunity to express a multistage relational calculation directly over Arrow data, avoiding intermediate DataFrame conversions and reducing Python orchestration.

Important limitation: The Python Acero interface is explicitly designated experimental, and its API stability is not guaranteed. It is not equivalent to a complete SQL query optimizer, and neither every operator nor every combination of operators has constant-memory streaming behavior. Joins, grouping, and global ordering can retain state or require substantial materialization.

The reader-source node was newly exposed in PyArrow 26, broadening the ability to connect an existing record-batch stream directly to an Acero plan.

Sources: [Acero Python API](https://arrow.apache.org/docs/python/api/acero.html?utm_source=chatgpt.com) and [Apache Arrow 26 release notes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 4.3 Substrait: portable relational plan representations

`pyarrow.substrait` introduces an additional integration layer for representing schemas and expressions in the Substrait format and executing supported Substrait query plans through Arrow's native execution facilities.

Relevant interfaces include:

- `serialize_schema` and `deserialize_schema`
- `serialize_expressions` and `deserialize_expressions`
- Substrait-based query execution facilities

The architectural significance is the possibility of exchanging structured relational logic, not merely exchanging the data produced by that logic.

For example, an upstream planner could produce a standardized query representation that is consumed by an Arrow-based execution system, subject to the supported operators, function declarations, and type mappings.

This is distinct from PyArrow acting as a SQL planner. Substrait interoperability requires both producer and consumer to agree on the relevant plan semantics and supported extensions.

Reference: [Substrait integration](https://arrow.apache.org/docs/python/integration/substrait.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



## 5. Dataset discovery, scanning, and writing

`pyarrow.dataset` is one of PyArrow's most architecturally consequential components.

It treats a collection of files or in-memory fragments as a logical dataset that can be inspected and scanned without first loading all its rows.

### 5.1 Dataset abstraction and discovery

A dataset provides a unified interface over fragments, which may reside across multiple files and partitions.

Important components include `Dataset`, `FileSystemDataset`, `UnionDataset`, `Fragment`, `Scanner`, `FileFormat`, and the dataset factory interfaces.

Discovery can:

- Locate files across directory trees.
- Interpret Hive-style, directory-based, or filename-based partitioning.
- Inspect and construct a dataset schema.
- Associate partition expressions with fragments.
- Combine compatible dataset sources under a common logical interface.

The important optimization is that constructing a dataset ordinarily performs discovery and metadata work rather than immediately reading all file contents.

However, discovering a dataset is not free. Directory listing, schema inspection, partition enumeration, and remote filesystem metadata requests can become significant overhead for large collections of small files.

The default discovery path can infer a schema from the first file, so heterogeneous datasets may require an explicitly supplied schema or more controlled factory inspection. Dataset discovery is not a general-purpose automatic schema-evolution system.

Reference: [Dataset user guide](https://arrow.apache.org/docs/python/dataset.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 5.2 Scanner execution, pushdown, and incremental consumption

A `Scanner` binds an input dataset to projection, filtering, and execution options.

A concise example illustrates the interface:

```
import pyarrow.dataset as dsdataset = ds.dataset("data/", format="parquet", partitioning="hive")scanner = dataset.scanner(    columns={        "entity_id": ds.field("entity_id"),        "adjusted": ds.field("amount") * 1.05,    },    filter=ds.field("status") == "active",    batch_size=65_536,)for batch in scanner.to_batches():    consume(batch)
```

Illustrative example; `consume` represents application-defined batch handling.

This combines several operations that otherwise might need separate stages: file discovery, partition pruning, selective column reading, native filtering, calculated projection, and incremental output.

The scanner supports:

| Option               | Consequence                                                           |
| -------------------- | --------------------------------------------------------------------- |
| `columns`            | Reads only required columns; also supports expression-derived columns |
| `filter`             | Applies predicates with pushdown where supported                      |
| `batch_size`         | Controls the maximum number of rows in emitted batches                |
| `batch_readahead`    | Overlaps reading and processing of batches within a file              |
| `fragment_readahead` | Allows multiple files/fragments to be read ahead                      |
| `use_threads`        | Controls threaded scanning                                            |
| `cache_metadata`     | Allows reuse of scan metadata                                         |
| `memory_pool`        | Selects allocation tracking and policy                                |

A filter may eliminate entire partitions or Parquet row groups before their data is decoded. If a predicate cannot be pushed down, it is evaluated after the relevant data has been read.

This is a crucial distinction: expression-based filtering is supported, but eliminating physical I/O depends on the format, metadata, predicate, and file organization.

The scanner also exposes special projection fields such as `__filename`, `__fragment_index`, `__batch_index`, and `__last_in_fragment`. These can supply provenance and processing context without separately reconstructing them from directory traversal code.

Sources: [Scanner API](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html?utm_source=chatgpt.com) and [Dataset API](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 5.3 Fragments and explicit scan control

Fragments expose a useful intermediate granularity between the entire dataset and individual batches.

`Dataset.get_fragments(filter=...)` provides a way to inspect or selectively operate on the fragments that can satisfy a predicate. Parquet-specific fragments additionally expose row-group-oriented functionality.

This opens up possibilities for:

- Discovering which files participate in an operation.
- Producing fragment-level diagnostics.
- Inspecting partition and row-group boundaries.
- Applying distinct scan settings to separate data sources.
- Building processing flows that retain file provenance.

The ability to preserve fragment identity is useful beyond performance; it can also simplify data lineage and operational diagnostics.

### 5.4 Dataset formats and their asymmetries

PyArrow 26 exposes dataset file-format interfaces for Parquet, Arrow IPC, CSV, ORC, and JSON.

These should not be treated as fully interchangeable. For example, the dataset writer supports Parquet, IPC/Feather, and CSV, while ORC is documented as read-only through the dataset layer. The 26.0.0 API also exposes `JsonFileFormat`, even though the dataset introductory guide has not been fully updated to enumerate it.

An individual format's reader and writer may expose additional functionality beyond its dataset integration.

Sources: [Dataset format classes](https://arrow.apache.org/docs/python/api/dataset.html?utm_source=chatgpt.com) and [dataset writer supported formats](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.write_dataset.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 5.5 Incremental and partitioned dataset writing

`ds.write_dataset` accepts tables, batches, record-batch readers, dataset objects, and iterables of record batches. It can therefore write a dataset directly from an incremental producer rather than requiring an entire output table.

The writer controls partitioning, output naming, per-format options, parallel execution, ordering, file limits, row-group sizing, and the treatment of existing data.

Particularly significant controls include:

- `max_open_files`, which bounds concurrently open output files.
- `max_rows_per_file`, limiting file sizes by row count.
- `min_rows_per_group` and `max_rows_per_group`, governing row-group formation.
- `preserve_order`, which trades performance for row-order preservation.
- `file_visitor`, exposing output paths and Parquet metadata as files are written.
- `existing_data_behavior`, with error, overwrite/ignore, and matching-partition deletion behaviors.

These options can replace substantial custom logic for routing batches into partitions and producing manageable columnar output.

The most important qualification is that `write_dataset` is a file-writing mechanism, not a transactional dataset catalog. Its overwrite and deletion options do not provide atomic multi-file commits, consistent snapshots for concurrent readers, or general-purpose update/delete transaction semantics.

References: [Dataset writer API](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.write_dataset.html?utm_source=chatgpt.com) and [partitioned Parquet datasets](https://arrow.apache.org/docs/python/parquet/parquet_datasets.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



## 6. Parquet as a storage and query-optimization layer

PyArrow's Parquet integration is considerably richer than `read_table` and `write_table`. It exposes file layout, encoding, metadata, row-group control, selective reads, encryption, and advanced writer options.

### 6.1 Reader and writer interfaces

The primary interfaces are `pyarrow.parquet.read_table`, `write_table`, `ParquetFile`, `ParquetWriter`, and the Parquet-specific dataset facilities.

`ParquetFile` allows examination of file and row-group metadata, schema, compression, statistics, and individual row groups. It also supports incremental iteration over batches.

The writer can control:

- Row-group size and data-page size.
- Compression codecs and levels, globally or per column.
- Dictionary encoding and alternative encodings, including byte-stream split and delta variants.
- Per-column statistics.
- Timestamp precision and compatibility conversion.
- Nested-type conventions and logical Parquet format versions.
- Page indexes and page checksums.
- Bloom filters.
- Schema metadata and modular encryption.
- Content-defined chunking.

These are independent tuning dimensions: a configuration favorable for compact archival storage may be different from one favorable for selective analytical queries.

Source: [Parquet writer API](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 6.2 Reading fewer bytes and decoding fewer values

Parquet is organized into row groups containing column chunks, with separately encoded and usually compressed pages.

PyArrow can use column projection to avoid reading irrelevant columns and row-group statistics to skip groups that cannot satisfy a predicate.

The effectiveness depends on data distribution and physical layout. For instance, a file ordered by a commonly filtered key may present narrow per-row-group minimum/maximum ranges, enabling useful pruning. Randomly distributed keys may produce overlapping ranges that offer little benefit.

Fragment scan options provide additional controls for remote and local I/O. `pre_buffer`, for example, can coalesce and issue reads in parallel on high-latency filesystems, trading additional memory for better I/O utilization. Buffered reads, cache options, and page-checksum verification are separately configurable.

References: [Parquet reading and filtering](https://arrow.apache.org/docs/python/parquet/parquet.html?utm_source=chatgpt.com) and [Parquet fragment scan options](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.ParquetFragmentScanOptions.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 6.3 Bloom filters and page indexes: important reader limitations

Two features warrant special attention:

Bloom filters. PyArrow can write per-column, per-row-group Bloom filters using `bloom_filter_options`, with configurable expected distinct values and false-positive probability. They can help compatible Parquet readers reject row groups for equality predicates.

However, the PyArrow 26 Parquet reader does not currently use these Bloom filters for filtering. Their immediate benefit may therefore accrue to another engine that reads the same files.

Page indexes. PyArrow can write Parquet page indexes via `write_page_index`, enabling page-level statistics to be stored in a structure intended for more efficient filtering. But the PyArrow reader likewise does not yet use the page index for its own filtering.

These capabilities are still relevant to interoperability and file-layout design, but their existence on the writing side should not be interpreted as evidence of corresponding PyArrow read-side acceleration.

Sources: [Bloom filter documentation](https://arrow.apache.org/docs/python/parquet/parquet.html?utm_source=chatgpt.com) and [Parquet page index option](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 6.4 Schema fidelity and Parquet compatibility

Arrow and Parquet have related but distinct logical type systems. A Parquet encoding may not natively represent every detail of the original Arrow type.

PyArrow can store an Arrow schema in Parquet key-value metadata using the `ARROW:schema` key, improving round-trip fidelity for cases such as time zones and duration types. It can also interpret certain Parquet logical types as canonical Arrow extension types when explicitly enabled.

The Parquet logical format version (`1.0`, `2.4`, or `2.6`) should be distinguished from the data-page version and from the PyArrow package version. Newer logical types can improve fidelity but constrain interoperability with older readers.

Timestamp coercion, precision truncation, decimal representation, and nested list conventions therefore deserve explicit attention when files will be exchanged across engines.

Reference: [Parquet writer format and type controls](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 6.5 Modular Parquet encryption

PyArrow implements Parquet modular encryption with configurable file/column encryption and key-management integration.

Its Python interfaces include `CryptoFactory`, `KmsClient`, `EncryptionConfiguration`, `DecryptionConfiguration`, and file encryption/decryption properties.

This allows encrypted Parquet files to be produced and consumed with externally managed keys, rather than requiring a bespoke encryption wrapper around the entire file.

It does not eliminate the operational requirements of key management, credential security, key rotation, or recipient compatibility.

A consequential security change in Arrow 26 is that KMS URLs supplied from Parquet file metadata are no longer forwarded to a pluggable KMS client by default. Opting into that behavior requires validating those URLs.

References: [Parquet modular encryption](https://arrow.apache.org/docs/python/parquet/parquet_encryption.html?utm_source=chatgpt.com) and [Arrow 26 security changes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 6.6 Shared Parquet metadata files

PyArrow supports the `_metadata` and `_common_metadata` conventions used by some analytical processing frameworks.

`_common_metadata` can provide a shared schema, while `_metadata` can additionally aggregate row-group metadata and file paths.

These files can reduce repeated directory discovery and metadata inspection, particularly on remote object stores with high per-request latency.

They are ecosystem conventions, not transactional manifests or the Parquet file-format standard itself. Writers do not always produce them automatically, and they must remain synchronized with the actual data files.

Reference: [Parquet dataset metadata conventions](https://arrow.apache.org/docs/python/parquet/parquet_datasets.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



## 7. Arrow IPC, Feather, CSV, JSON, and ORC

PyArrow supports several distinct storage and interchange formats. Their differing physical layouts are as important as their shared ability to produce Arrow tables.

### 7.1 Arrow IPC: native columnar interchange

The Arrow IPC format serializes schemas and record batches in a layout closely aligned with Arrow's in-memory representation.

Two IPC variants serve different requirements:

| Format     | Python interfaces                         | Main distinction                                                                       |
| ---------- | ----------------------------------------- | -------------------------------------------------------------------------------------- |
| IPC stream | `pa.ipc.new_stream`, `pa.ipc.open_stream` | Sequential delivery of batches; suitable for pipes, streams, and incremental producers |
| IPC file   | `pa.ipc.new_file`, `pa.ipc.open_file`     | Seekable format with a footer enabling random access to record batches                 |

For compatible uncompressed buffers, an IPC reader can reconstruct Arrow arrays by referencing existing memory rather than decoding values into a separate representation.

Combined with `pa.memory_map`, an IPC file can therefore serve as a persistent, memory-mapped representation of Arrow data. This enables low-overhead reuse of large arrays and operating-system-managed sharing of file-backed pages across processes.

This differs materially from Parquet. Although a Parquet file can be memory-mapped at the I/O level, its compressed and encoded column pages usually require decoding and new Arrow allocations before computation.

IPC's benefits come with tradeoffs: it is not generally a replacement for Parquet's selective analytical storage features, and zero-copy behavior depends on the actual source, compression, data layout, and ownership of the referenced memory.

Reference: [Arrow IPC streams, files, and memory mapping](https://arrow.apache.org/docs/python/ipc.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 7.2 Feather V2 and the IPC relationship

Feather V2 is the Arrow IPC file format, exposed through the convenience interface `pyarrow.feather`.

It supports LZ4 and ZSTD compression, and `feather.write_feather` defaults to LZ4 when available. By contrast, `pa.ipc.new_file` does not enable compression by default.

A significant version distinction is that legacy Feather V1 is deprecated, not Feather V2. The official documentation describes using the IPC module directly as the long-term interface for Feather V2 files.

Reference: [Feather format and migration to IPC](https://arrow.apache.org/docs/python/feather.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 7.3 CSV and JSON ingestion

`pyarrow.csv` offers native parsing, type inference, column selection, explicit conversion rules, null-token handling, optional dictionary encoding, and CSV output.

The two primary reading paths are not identical:

- `csv.read_csv` can use multiple threads and materializes the input as a table.
- `csv.open_csv` supports incremental batch consumption but is currently single-threaded. Its schema inference occurs on the initial block, after which inferred types are fixed.

The latter distinction matters with heterogeneous or evolving input: a type that appears only later in the file may be incompatible with the initially inferred schema.

`pyarrow.json` provides native reading of line-delimited JSON, including recursive inference of arrays as Arrow lists and nested JSON objects as structs. Both complete-table and incremental reading are available.

It should not be treated as a general-purpose parser for arbitrary JSON documents containing one top-level array or deeply customized application-specific serialization structures.

Version 26 also exposes additional CSV writer controls for line endings and null representations.

References: [CSV reader and writer](https://arrow.apache.org/docs/python/csv.html?utm_source=chatgpt.com), [JSON reader](https://arrow.apache.org/docs/python/json.html?utm_source=chatgpt.com), and [26.0.0 changes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+2



### 7.4 ORC and compression utilities

`pyarrow.orc` supports reading and writing ORC files, including columnar access through the ORC file interface. ORC also participates in dataset scanning, but the Dataset layer's ORC support is read-only in the documented 26.0 API.

Separately, PyArrow provides `pa.Codec` and compressed I/O wrappers for supported codecs such as ZSTD, LZ4, gzip, Brotli, and others according to the build.

These compression facilities are useful beyond Parquet—for example, to work with compressed streams or files—but generic compression of an entire IPC payload does not preserve IPC's normal random-access and zero-copy advantages.

References: [ORC support](https://arrow.apache.org/docs/python/orc.html?utm_source=chatgpt.com) and [Memory and I/O APIs](https://arrow.apache.org/docs/python/memory.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



## 8. Memory ownership, allocation, I/O, and concurrency

The ability to avoid unnecessary memory copies is a defining feature of Arrow, but it is not automatic. Understanding the conditions for buffer reuse is essential.

### 8.1 Buffer ownership and zero-copy operations

`pa.Buffer` wraps memory referenced by Arrow's native C++ implementation. It can refer to Arrow-managed memory, Python-owned memory, memory-mapped files, or externally managed memory.

Key interfaces include:

| API                     | Role                                                                     |
| ----------------------- | ------------------------------------------------------------------------ |
| `pa.py_buffer`          | Creates an Arrow view of a Python buffer-protocol object without copying |
| `pa.foreign_buffer`     | Wraps an external memory address and size, with lifetime handling        |
| `pa.allocate_buffer`    | Allocates Arrow-managed memory                                           |
| `pa.BufferReader`       | Reads an in-memory Arrow buffer through the native I/O interface         |
| `pa.BufferOutputStream` | Produces an in-memory Arrow buffer through a stream                      |
| `pa.OSFile`             | Exposes native filesystem I/O                                            |
| `pa.memory_map`         | Creates memory-mapped file access                                        |

A zero-copy slice or view must keep its underlying allocation alive. Arrow's ownership mechanisms normally accomplish this through references to parent buffers or owning objects.

`foreign_buffer` deserves particular care: it is a low-level interface for referencing externally allocated memory, not a mechanism for making arbitrary raw pointers safe. The external memory's lifetime and mutability must remain valid.

Native Arrow I/O objects also allow C++ components to access streams without repeatedly entering Python-level file methods or acquiring the Python GIL.

Reference: [Buffers, memory pools, and NativeFile](https://arrow.apache.org/docs/python/memory.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 8.2 Memory pools and observability

Arrow's memory pool abstraction enables allocation tracking and, depending on build configuration, different allocator backends.

Relevant APIs include `pa.default_memory_pool`, `pa.set_memory_pool`, `pa.total_allocated_bytes`, `pa.logging_memory_pool`, and `pa.proxy_memory_pool`.

A memory pool can report current allocation, peak allocation, and cumulative allocation statistics where supported.

These facilities are useful for isolating Arrow-controlled allocations and distinguishing data-buffer growth from other process activity.

However, memory-pool statistics are not equivalent to process resident memory. They do not necessarily include:

- Python interpreter objects and non-Arrow extension allocations.
- Memory owned directly by other native libraries.
- Memory-mapped pages or externally owned NumPy buffers.
- Allocator-retained memory that affects RSS differently from live allocations.
- Every native allocation made outside the selected pool.

Memory accounting therefore benefits from both Arrow-specific statistics and operating-system-level measurements.

### 8.3 Execution parallelism and thread control

PyArrow provides native CPU and I/O thread pools, with controls including:

- `pa.cpu_count` and `pa.set_cpu_count`
- `pa.io_thread_count` and `pa.set_io_thread_count`
- Operation-specific `use_threads` settings
- Dataset scanner batch and fragment readahead
- Parallel file writing where supported

Many C++ operations can execute without holding the Python GIL. This creates opportunities for parallel scanning, decoding, compression, computation, and I/O.

The effective parallelism nevertheless depends on the workload and interfaces involved.

A Python UDF or an fsspec-backed filesystem can reintroduce Python-level execution and GIL contention. Native operators may compete for memory bandwidth. Multiple independent engines can oversubscribe CPU cores if each manages its own parallel execution.

Increasing readahead is particularly consequential: it may improve utilization of high-latency storage while increasing peak memory and outstanding I/O.

Reference: [PyArrow API—thread and resource controls](https://arrow.apache.org/docs/python/api.html?utm_source=chatgpt.com) and [Scanner configuration](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



## 9. Interoperability and conversion boundaries

PyArrow's role as a common representation is most valuable when adjacent systems can exchange data without unnecessary serialization, copying, or conversion to Python objects.

There are several interoperability mechanisms, and they solve different problems.

### 9.1 NumPy integration

PyArrow can create arrays from compatible NumPy arrays and expose suitable Arrow arrays to NumPy.

A zero-copy NumPy view is possible when the underlying representation is compatible—for example, a primitive, fixed-width Arrow array without nulls. `Array.to_numpy(zero_copy_only=True)` can be used to require a view rather than silently accepting a copy.

Zero-copy conversion becomes more complicated or impossible for nullable arrays, variable-length strings, nested structures, noncontiguous layouts, and multi-chunk logical columns.

Other semantic differences matter as well. NumPy datetime representations do not retain Arrow's complete time-zone semantics, and NumPy does not natively represent Arrow's full nested and extension type system.

Reference: [NumPy integration](https://arrow.apache.org/docs/python/numpy.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 9.2 pandas integration and Arrow-backed columns

`Table.from_pandas` and `Table.to_pandas` provide explicit conversion between pandas and Arrow.

Important controls include `types_mapper`, `zero_copy_only`, `split_blocks`, and conversion options governing dates, maps, and categorical values.

There are two conceptually different modes:

Materialized conversion: An Arrow table is converted into traditional pandas/NumPy or object-backed columns. This may allocate substantial memory, reconstruct Python objects, or alter the representation of nulls and types.

Arrow-backed pandas columns: pandas `ArrowDtype` can retain data in Arrow-backed extension arrays. This preserves access to Arrow's richer type representations and may reduce copies, depending on the pandas operation.

Arrow-backed pandas should not be confused with PyArrow executing a complete pandas query plan. pandas remains responsible for its DataFrame API and operation semantics; individual operations may delegate to Arrow kernels.

Some conversion options are deliberately aggressive. In particular, `Table.to_pandas(self_destruct=True)` attempts to release Arrow memory during conversion and can make subsequent use of the source Arrow object unsafe, potentially causing a crash. It is not a generally safe memory-optimization toggle.

References: [pandas integration](https://arrow.apache.org/docs/python/pandas.html?utm_source=chatgpt.com) and [Table conversion parameters](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 9.3 Arrow C Data, C Stream, and PyCapsule interfaces

The Arrow C Data Interface and C Stream Interface are among the most powerful integration mechanisms in the ecosystem.

They standardize the exchange of array schemas, memory references, and streams through C-compatible structures, allowing language bindings and independent libraries to share Arrow data without requiring a common high-level object model.

The Python PyCapsule protocol exposes these mechanisms through interfaces including:

- `__arrow_c_schema__`
- `__arrow_c_array__`
- `__arrow_c_stream__`

This allows an Arrow-compatible producer to provide data directly to a consumer such as PyArrow, using the agreed protocol instead of implementing a bespoke conversion API for every library pair.

`pa.table` can consume supported Arrow-compatible objects, while `RecordBatchReader.from_stream` provides a useful entry point for streaming producers.

The C Data and C Stream interfaces are in-process interchange protocols. They do not by themselves serialize data for network transport or transfer ownership between independent processes. Those use cases require IPC, shared-memory coordination, Flight, or another transport mechanism.

Lifetime guarantees depend on each participant following the protocol's ownership and release rules. PyCapsule objects are also consumable according to protocol-defined semantics rather than being unrestricted reusable containers.

References: [Arrow PyCapsule Interface specification](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html?utm_source=chatgpt.com), [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html?utm_source=chatgpt.com), and [Extending PyArrow](https://arrow.apache.org/docs/python/extending_types.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+2



### 9.4 DataFrame Interchange Protocol

PyArrow also implements the Python DataFrame Interchange Protocol through `Table.__dataframe__` and `RecordBatch.__dataframe__`.

This protocol supports primitive and dictionary-encoded types, missing-value information, and chunked data.

It addresses interoperability between DataFrame implementations more generally, but its supported type surface is narrower than Arrow's complete data model.

The PyArrow documentation now explicitly recommends the Arrow PyCapsule interface when the participating DataFrame libraries support it, rather than treating the DataFrame Interchange Protocol as the preferred universal path.

Reference: [DataFrame Interchange Protocol](https://arrow.apache.org/docs/python/interchange_protocol.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 9.5 DLPack: numerical arrays and tensors

PyArrow 26 introduces DLPack export support for `pa.Array`, `pa.Tensor`, and fixed-shape tensor arrays and scalars, enabling direct exchange with compatible scientific-computing frameworks.

DLPack addresses a different representation problem from Arrow's tabular C Data Interface: its purpose is numerical array and tensor interchange.

In PyArrow 26:

- Regular Arrow arrays are limited to compatible one-dimensional contiguous numerical tensors.
- `pa.Tensor` can represent multidimensional tensor shapes and strides.
- `FixedShapeTensorArray` can expose fixed-shape tensor elements as a multidimensional tensor.
- Supported value types are numerical.
- Arrow arrays containing nulls cannot be exported directly through DLPack.
- PyArrow's DLPack implementation currently supports CPU memory only.

A nullable numerical array can be converted to a tensor with `allow_nulls=True`, but the memory positions corresponding to null values then have unspecified contents. That is a meaningful information-loss boundary, not a null-preserving conversion.

The new capability is significant for NumPy, PyTorch, JAX, and other tensor-oriented consumers, but it does not make all Arrow structures interchangeable with numerical tensors, nor does it expose PyArrow CUDA buffers through its DLPack implementation.

Reference: [PyArrow DLPack protocol support](https://arrow.apache.org/docs/python/dlpack.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



## 10. Extension types, tensors, and custom native integration

### 10.1 Extension types as semantic representations

`pa.ExtensionType` allows a logical type to be represented over an existing Arrow storage type while retaining an independently named semantic identity.

A custom extension type defines its storage representation and serialized parameters through interfaces such as:

- `__arrow_ext_serialize__`
- `__arrow_ext_deserialize__`
- `__arrow_ext_class__`
- `__arrow_ext_scalar_class__`

`pa.ExtensionArray` and `pa.ExtensionScalar` can provide custom behavior, while `pa.register_extension_type` enables deserialization of registered extension types.

This is useful for values whose representation can be expressed using Arrow's existing buffers but whose meaning is more specialized—for example, a rational number represented by a struct of two integers, a spatial coordinate, or a domain-specific encoded quantity.

The benefit is the ability to preserve semantic types across portions of the Arrow ecosystem without inventing an entirely new columnar storage format.

There are important boundaries. Extension-type metadata is not a universal semantic contract across all consumers. A library that does not recognize an extension may access its storage representation, reject it, or preserve it without understanding its meaning.

Custom extensions also do not automatically receive specialized compute kernels. Operations may need to work on their underlying storage representation or use explicitly implemented extensions.

Reference: [Extending PyArrow](https://arrow.apache.org/docs/python/extending_types.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 10.2 Canonical extension types

Apache Arrow defines canonical extension types intended to support more consistent interchange of selected semantics across implementations.

Relevant PyArrow representations include:

| Type                   | Purpose                                                                    |
| ---------------------- | -------------------------------------------------------------------------- |
| `FixedShapeTensorType` | Represents tensor-valued elements with a known shape                       |
| `JsonType`             | Identifies strings with JSON semantics                                     |
| `UuidType`             | Provides a canonical UUID representation                                   |
| `OpaqueType`           | Carries a named opaque application-defined type                            |
| `Bool8Type`            | Represents booleans as byte-sized values in specified interchange contexts |

Canonical extension types can be preferable to inventing proprietary metadata conventions for equivalent representations.

However, they still require compatible implementations for full semantic fidelity. For example, storing a JSON value using a canonical extension type does not imply that all Arrow consumers will validate or query its JSON contents.

Reference: [Canonical extensions and Python representations](https://arrow.apache.org/docs/python/extending_types.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



### 10.3 Dense and sparse tensors

Besides one-dimensional Arrow arrays and record batches, PyArrow provides tensor representations, including `pa.Tensor` and sparse tensor structures such as COO and CSR.

These are useful for interfacing with numerical and scientific libraries without treating every multidimensional object as a collection of Python lists.

The distinction between tabular arrays and tensors is substantial:

- A `Table` has named, potentially heterogeneous columns, nullability, and chunking.
- A `Tensor` describes homogeneous multidimensional numerical data with shape and strides.
- A `FixedShapeTensorArray` embeds a fixed-shape tensor representation within Arrow's columnar array model.

The DLPack capabilities introduced in version 26 make this bridge considerably more useful.

One format-level caveat: Arrow 26 deprecates the Tensor and SparseTensor IPC message types. This is a deprecation of those serialization messages, not a wholesale removal of PyArrow's tensor objects or the new DLPack support.

Sources: [Tensor types in the Python API](https://arrow.apache.org/docs/python/api.html?utm_source=chatgpt.com) and [Arrow 26 format changes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow



### 10.4 Native C++ and Cython extensions

PyArrow includes integration facilities for native extension code, including Cython declarations and package-discovery utilities such as `pa.get_include`, `pa.get_library_dirs`, and `pa.get_libraries`.

These can be useful when custom compiled implementations need to operate directly on Arrow structures rather than crossing the Python object boundary for every value.

There are two general integration strategies:

Protocol-level integration uses C Data/C Stream and PyCapsule interfaces. This can reduce coupling to PyArrow's internal C++ ABI.

Direct C++ integration uses Arrow's native libraries and types. This allows deeper access to native functionality but introduces build, linking, compiler, and binary-compatibility obligations.

These approaches are complementary. A small adapter exchanging Arrow C structures may be more maintainable than exposing an entire native extension API, while a deeply specialized native kernel may need more direct integration.

Reference: [Using PyArrow from C++ and Cython code](https://arrow.apache.org/docs/python/integration.html?utm_source=chatgpt.com).

## 11. Filesystems, Flight RPC, and device memory

### 11.1 Native filesystem integration

`pyarrow.fs` provides a common abstraction for local and remote file operations.

Native implementations cover local filesystems, Amazon S3, Google Cloud Storage, HDFS, and Azure Blob Storage.

Relevant capabilities include filesystem discovery, recursive listing, file metadata, input and output streams, ranged reads, and explicit filesystem instances passed to Dataset and Parquet APIs.

Additional mechanisms include:

- `FileSystem.from_uri` for supported URI-based construction.
- `SubTreeFileSystem` for exposing a restricted subtree through a filesystem interface.
- `PyFileSystem` and `FSSpecHandler` for adapting fsspec-compatible Python filesystems.
- `fs.copy_files` for copying between supported filesystem implementations.

A common filesystem abstraction allows dataset scanning and writing logic to remain largely independent of the underlying storage provider.

Nevertheless, native Arrow filesystems and Python/fsspec adapters need not exhibit identical parallelism, buffering, metadata-request behavior, or throughput.

For high-latency remote storage, parallel scanning, readahead, request coalescing, and reducing metadata requests may matter as much as the performance of the numerical compute kernels.

Version-specific native linking change: Arrow 26 separates the S3 implementation into `libarrow_s3`, rather than keeping it in the base C++ `libarrow` library. This affects native linking and component packaging; it does not mean PyArrow's S3 filesystem interface was removed.

References: [Filesystem interface](https://arrow.apache.org/docs/python/filesystems.html?utm_source=chatgpt.com) and [Arrow 26 C++ filesystem changes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 11.2 Arrow Flight: columnar network transport

`pyarrow.flight` exposes client and server bindings for Arrow Flight, an RPC protocol oriented toward transporting Arrow data.

It is designed around record-batch streams rather than requiring a complete result to be serialized into a conventional Python response object.

Core interfaces include `FlightClient`, `FlightServerBase`, `FlightDescriptor`, `FlightInfo`, `FlightEndpoint`, and `Ticket`.

| Operation         | Function                                           |
| ----------------- | -------------------------------------------------- |
| `list_flights`    | Discover available data streams                    |
| `get_flight_info` | Retrieve metadata and endpoints for requested data |
| `get_schema`      | Retrieve schema information                        |
| `do_get`          | Download a record-batch stream                     |
| `do_put`          | Upload a record-batch stream                       |
| `do_exchange`     | Establish bidirectional streaming exchange         |
| `do_action`       | Execute custom service-defined actions             |

The Python implementation provides facilities for authentication, TLS, middleware, and per-call options.

The more advanced opportunity is `do_exchange`: a client and server can exchange data incrementally in both directions, making Flight suitable for streaming computational services as well as dataset download and upload.

Flight is a transport and service protocol, not a database server. The application still defines the meaning of datasets, requests, permissions, persistence, and computational actions.

Reference: [Arrow Flight user guide](https://arrow.apache.org/docs/python/flight.html?utm_source=chatgpt.com), [FlightServerBase API](https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightServerBase.html?utm_source=chatgpt.com), and [FlightClient API](https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightClient.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0

+1



### 11.3 Flight SQL and ADBC are distinct layers

Flight SQL standardizes database-oriented operations over Flight, including SQL query execution and associated metadata.

ADBC, the Arrow Database Connectivity project, is a separate driver API and implementation family that enables columnar database access.

The distinction is:

- Flight provides transport primitives.
- Flight SQL specifies SQL-oriented behavior over those primitives.
- ADBC provides database connectivity interfaces and drivers, including a Flight SQL driver.
- PyArrow supplies the Arrow representation and lower-level Python interfaces; it is not itself the ADBC driver manager.

These components can be combined without conflating their responsibilities.

Reference: [ADBC Python documentation and drivers](https://arrow.apache.org/adbc/current/python/index.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

ADBC 24 Documentation



### 11.4 CUDA memory and GPU boundaries

Optional `pyarrow.cuda` facilities provide access to CUDA device memory, device buffers, host/device copies, CUDA IPC handles, and integration with Numba.

They are useful for moving or sharing data with GPU-aware native code.

However, they should not be interpreted as providing a GPU implementation of the general PyArrow compute engine.

Most Arrow CPU kernels expect host-accessible buffers. The CUDA documentation explicitly warns that some Arrow functions do not check whether a buffer is CPU-accessible and can crash if given a CUDA buffer.

The distinction from DLPack is also important: PyArrow 26's DLPack implementation is currently CPU-only, even though DLPack itself is a device-aware protocol.

Reference: [CUDA integration and its limitations](https://arrow.apache.org/docs/python/integration/cuda.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



## 12. Boundaries with adjacent analytical engines

One of PyArrow's strongest architectural roles is to provide shared data representations to libraries that offer capabilities outside its own scope.

| Technology        | Primary responsibility                               | Relationship to PyArrow                                          |
| ----------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| Apache DataFusion | SQL planning, optimization, and relational execution | Separate Rust-based query engine operating with Arrow data       |
| DuckDB            | Embedded analytical SQL database                     | Independent engine with Arrow interchange capabilities           |
| Polars            | DataFrame-oriented analytical execution              | Separate DataFrame/query engine that can exchange Arrow data     |
| pandas            | Python DataFrame API and ecosystem                   | Converts or retains Arrow-backed columns through extension types |
| ADBC              | Database connectivity and Arrow-native retrieval     | Separate driver framework that produces and consumes Arrow data  |
| Arrow Flight      | Columnar RPC and streaming                           | Transport protocol with Python bindings exposed through PyArrow  |
| nanoarrow         | Lightweight Arrow interchange integration            | Separate implementation useful where full PyArrow is unnecessary |
| Parquet           | Columnar persistent file format                      | Read and written by PyArrow and many independent engines         |

These technologies should not be treated as interchangeable merely because they support Arrow.

For instance, `pyarrow.compute` and Acero provide substantial native relational functionality, but DataFusion additionally offers a SQL frontend, a query optimizer, window functions, catalog integration, and a broader query-execution environment.

Similarly, DuckDB can consume Arrow data while making its own decisions about execution, vectorization, memory management, and query planning.

A particularly valuable integration pattern is to use Arrow's common representation as the boundary between specialized engines rather than replicate one engine's distinctive functionality in another.

This may eliminate serialization or custom adapters, but it does not guarantee that a complete computation remains zero-copy: joins, sorting, aggregation, casting, null normalization, and engine-specific conversions can allocate new memory.

Primary external references: [DataFusion Python](https://datafusion.apache.org/python/?utm_source=chatgpt.com), [ADBC Python](https://arrow.apache.org/adbc/current/python/index.html?utm_source=chatgpt.com), and [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://datafusion.apache.org\&sz=32)

Apache DataFusion in Python documentation

+2



### Gandiva: a less common Arrow-native option

Gandiva is a distinct LLVM-based expression compiler within the broader Apache Arrow project.

Rather than simply invoking predefined vectorized kernels, Gandiva compiles expression trees into native code for processing Arrow record batches. It is specialized for projections and filters, not a general query engine.

Its design can amortize compilation costs when the same expressions execute repeatedly over many batches. Conversely, compilation overhead and its narrower operation set can make it less attractive for short or dynamic workloads.

Gandiva should be distinguished from `pyarrow.compute` and Acero. It is an optional Arrow component, with availability dependent on distribution and build configuration.

Reference: [Apache Arrow Gandiva expression compiler](https://arrow.apache.org/docs/cpp/gandiva.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



## 13. PyArrow 26.0.0: release-specific changes and availability

Version 26 is especially noteworthy because several improvements expand how Arrow data can participate in native computation and interoperability.

### 13.1 Major changes compared with earlier versions

| Area             | Version 26 change                                                                                                | Consequence                                                   |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| DLPack           | Export from arrays, tensors, fixed-shape tensor arrays and scalars; updated protocol support                     | Stronger integration with numerical frameworks                |
| Acero            | `RecordBatchReaderSourceNodeOptions` exposed                                                                     | Easier construction of plans consuming existing Arrow streams |
| Compute          | `search_sorted` for primitive and run-end encoded arrays                                                         | Native insertion-point searches                               |
| Run-end encoding | Encoding and decoding of nested list, map, and struct values                                                     | Broader applicability of compressed run-based representations |
| NumPy            | Conversion from NumPy `StringDType`                                                                              | Improved handling of modern NumPy string arrays               |
| IPC              | `RecordBatchFileReader.count_rows()`                                                                             | Row counting without collecting a complete table              |
| CSV              | Additional writer controls for null strings and line endings                                                     | Greater export-format control                                 |
| Native compute   | New remainder/modulo operations; grouping support for string/binary views; temporal rounding for duration inputs | Expanded C++ kernel coverage                                  |
| Parquet security | More restrictive handling of KMS URLs supplied from file metadata                                                | Safer default behavior for externally supplied files          |

The last two rows include changes in the underlying C++ libraries and should not be interpreted as a guarantee that every C++ interface is exposed identically in Python.

Reference: [Apache Arrow 26.0.0 release notes](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow

+1



### 13.2 Python compatibility and packaging

The release notes identify these compatibility changes:

- Python 3.10 support is dropped.
- NumPy 2.x is the supported integration baseline.
- pandas releases earlier than 2.2.2 are no longer supported.
- Python 3.15 support and wheels were added.

One documentation discrepancy remains: the general installation page's compatibility summary still enumerates Python 3.11 through 3.14, while the 26.0 release notes explicitly announce Python 3.15 wheels. For that specific change, the dated release notes provide the stronger evidence.

The distribution channel also changes what functionality is installed.

On PyPI, PyArrow is published as a single `pyarrow` package. On conda-forge, it is split into several configurations:

| conda-forge package | Included capability scope                                     |
| ------------------- | ------------------------------------------------------------- |
| `pyarrow-core`      | Core types, compute, memory, IPC, filesystems, CSV, JSON, ORC |
| `pyarrow`           | Core plus Parquet, Dataset, Acero, and Substrait              |
| `pyarrow-all`       | Above plus Flight, Flight SQL, and Gandiva                    |

The optional nature of some native components matters when using PyArrow as a dependency for another library or exposing selected capabilities in a constrained runtime.

Reference: [Installing PyArrow and conda-forge package variants](https://arrow.apache.org/docs/python/install.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow

+1



### 13.3 Released, experimental, deprecated, and separate

To avoid confusing capability availability with API stability:

| Capability                                                            | Classification in this reference                               |
| --------------------------------------------------------------------- | -------------------------------------------------------------- |
| Arrow arrays, tables, schemas, IPC, Parquet, datasets, native compute | Established                                                    |
| Arrow C Data/C Stream and PyCapsule interchange                       | Established protocols                                          |
| DLPack export from supported Arrow arrays and tensors                 | Released in 26.0.0, subject to documented restrictions         |
| Python Acero declaration interface                                    | Available but explicitly experimental                          |
| Python compute UDF registration interfaces                            | Available but experimental                                     |
| Legacy Feather V1                                                     | Deprecated since 25.0.0                                        |
| Tensor/SparseTensor IPC message format                                | Deprecated in 26.0.0                                           |
| ADBC and DataFusion                                                   | Separate projects, not bundled PyArrow functionality           |
| Flight, Flight SQL, Gandiva, CUDA                                     | Availability depends on packaging or optional build components |

These distinctions are relevant both to system design and to compatibility expectations.

## 14. Architectural synthesis: where PyArrow creates the most value

PyArrow's individual capabilities are useful, but the larger opportunity lies in their composition.

### 14.1 A common typed execution substrate

A native Arrow pipeline can take the conceptual form:

Typed input

Parquet · IPC · Arrow C Stream · ADBC · memory

Dataset scanner

Partition pruning · projection · predicate evaluation · batch streaming

Arrow native execution

Compute expressions · relational operators · Acero

Incremental output

Record batches · Dataset writer · IPC · Flight · Arrow-aware consumer

This is a conceptual composition of documented mechanisms, not a claim that every possible operator combination streams without buffering or copies.

The principal advantage is that each stage can operate on Arrow representations without repeatedly constructing dictionaries, Python tuples, or traditional object-backed DataFrames.

Native operators can perform decoding, filtering, transformation, and output generation while minimizing Python control flow over individual rows.

For sufficiently suitable workloads, this can reduce custom data movement, intermediate materialization, and the number of distinct representation layers that must be maintained.

### 14.2 Important limits to the compositional benefit

Several constraints determine whether these advantages are realized.

Streaming is not synonymous with constant memory. A scan can deliver small batches, while a downstream hash join, aggregation, or full sort still accumulates substantial state.

Zero-copy applies to compatible memory layouts, not arbitrary transformations. Filtering, sorting, casting, decoding, and numerical conversions frequently allocate.

A common physical representation does not eliminate semantic translation. Timestamp precision, time zones, decimal types, null handling, dictionary identity, and extension metadata may still need reconciliation.

Predicate pushdown is conditional. An expression accepted by a scanner may be evaluated after physical data has been read. File and row-group pruning depend on layout, available statistics, and supported readers.

Memory-mapped storage differs from compressed analytical storage. IPC and Parquet offer different benefits and cannot be substituted without considering query selectivity, compression, write patterns, and interchange requirements.

Native execution does not imply global optimization. PyArrow has substantial compute and relational facilities, but specialized SQL engines and query planners may optimize combinations of operators more comprehensively.

Typed schemas are not transactional database constraints. PyArrow represents and validates types and structures, but it does not automatically enforce relational integrity, coordinate multi-writer commits, or manage consistent database snapshots.

These are not shortcomings that invalidate PyArrow's role. They define the boundary at which another native library, database, scheduler, or specialized engine may be more appropriate.

### 14.3 Less obvious capabilities deserving particular attention

For advanced engineering work, several parts of PyArrow merit investigation beyond the familiar pandas/Parquet interfaces:

| Capability                              | Why it is consequential                                                                |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| Dataset projection expressions          | Enables derived fields during scanning rather than in a separate materialization stage |
| Fragment-level metadata                 | Supports provenance, pruning inspection, and more precise work decomposition           |
| RecordBatchReader integration           | Provides a composable interface for incremental processing                             |
| Acero declarations                      | Enables relational execution directly over Arrow streams and datasets                  |
| Semi/anti/as-of joins                   | Covers useful relational operations without another DataFrame or SQL layer             |
| Arrow C Stream/PyCapsule                | Enables integration with independent execution engines without bespoke row conversion  |
| Run-end and dictionary encoding         | Provides native compressed representations that may be useful beyond file storage      |
| Custom extension types                  | Preserves semantic type identity over established physical layouts                     |
| Parquet row-group and metadata controls | Makes file structure part of analytical I/O optimization                               |
| Memory pools and native I/O             | Enables better allocation observability and avoids certain Python I/O overheads        |
| Substrait                               | Offers a structured boundary for exchanging relational plans rather than only results  |
| Flight bidirectional exchange           | Enables streamed computational services over Arrow data                                |
| DLPack and fixed-shape tensors          | Bridges columnar processing with numerical and tensor-oriented systems                 |

The common theme is that PyArrow can replace more than serialization code. Its native kernels, typed model, execution interfaces, and interchange protocols can also reduce the amount of custom infrastructure needed to move, transform, validate structurally, and coordinate columnar data.

## 15. Primary documentation resource map

The following links provide a compact navigation map into the official documentation. They are intended as independently reusable source URLs.

| Topic                             | Primary URL                                                                                                                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Complete Python API               | [https://arrow.apache.org/docs/python/api.html](https://arrow.apache.org/docs/python/api.html?utm_source=chatgpt.com)                                                                         |
| Data model and type system        | [https://arrow.apache.org/docs/python/data.html](https://arrow.apache.org/docs/python/data.html?utm_source=chatgpt.com)                                                                       |
| Compute functions                 | [https://arrow.apache.org/docs/python/compute.html](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com)                                                                 |
| Full compute API                  | [https://arrow.apache.org/docs/python/api/compute.html](https://arrow.apache.org/docs/python/api/compute.html?utm_source=chatgpt.com)                                                         |
| Acero execution interface         | [https://arrow.apache.org/docs/python/api/acero.html](https://arrow.apache.org/docs/python/api/acero.html?utm_source=chatgpt.com)                                                             |
| Dataset scanning and discovery    | [https://arrow.apache.org/docs/python/dataset.html](https://arrow.apache.org/docs/python/dataset.html?utm_source=chatgpt.com)                                                                 |
| Dataset API                       | [https://arrow.apache.org/docs/python/api/dataset.html](https://arrow.apache.org/docs/python/api/dataset.html?utm_source=chatgpt.com)                                                         |
| Dataset writer                    | [https://arrow.apache.org/docs/python/generated/pyarrow.dataset.write_dataset.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.write_dataset.html?utm_source=chatgpt.com) |
| Parquet file access               | [https://arrow.apache.org/docs/python/parquet/parquet.html](https://arrow.apache.org/docs/python/parquet/parquet.html?utm_source=chatgpt.com)                                                 |
| Parquet writer options            | [https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?utm_source=chatgpt.com)     |
| Parquet encryption                | [https://arrow.apache.org/docs/python/parquet/parquet_encryption.html](https://arrow.apache.org/docs/python/parquet/parquet_encryption.html?utm_source=chatgpt.com)                           |
| IPC and memory mapping            | [https://arrow.apache.org/docs/python/ipc.html](https://arrow.apache.org/docs/python/ipc.html?utm_source=chatgpt.com)                                                                         |
| Memory and native I/O             | [https://arrow.apache.org/docs/python/memory.html](https://arrow.apache.org/docs/python/memory.html?utm_source=chatgpt.com)                                                                   |
| File systems                      | [https://arrow.apache.org/docs/python/filesystems.html](https://arrow.apache.org/docs/python/filesystems.html?utm_source=chatgpt.com)                                                         |
| Arrow extension types             | [https://arrow.apache.org/docs/python/extending_types.html](https://arrow.apache.org/docs/python/extending_types.html?utm_source=chatgpt.com)                                                 |
| Arrow C Data Interface            | [https://arrow.apache.org/docs/format/CDataInterface.html](https://arrow.apache.org/docs/format/CDataInterface.html?utm_source=chatgpt.com)                                                   |
| Arrow PyCapsule Interface         | [https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html?utm_source=chatgpt.com)             |
| DLPack interoperability           | [https://arrow.apache.org/docs/python/dlpack.html](https://arrow.apache.org/docs/python/dlpack.html?utm_source=chatgpt.com)                                                                   |
| pandas integration                | [https://arrow.apache.org/docs/python/pandas.html](https://arrow.apache.org/docs/python/pandas.html?utm_source=chatgpt.com)                                                                   |
| NumPy integration                 | [https://arrow.apache.org/docs/python/numpy.html](https://arrow.apache.org/docs/python/numpy.html?utm_source=chatgpt.com)                                                                     |
| Substrait integration             | [https://arrow.apache.org/docs/python/integration/substrait.html](https://arrow.apache.org/docs/python/integration/substrait.html?utm_source=chatgpt.com)                                     |
| Arrow Flight                      | [https://arrow.apache.org/docs/python/flight.html](https://arrow.apache.org/docs/python/flight.html?utm_source=chatgpt.com)                                                                   |
| CUDA integration                  | [https://arrow.apache.org/docs/python/integration/cuda.html](https://arrow.apache.org/docs/python/integration/cuda.html?utm_source=chatgpt.com)                                               |
| Installation and package variants | [https://arrow.apache.org/docs/python/install.html](https://arrow.apache.org/docs/python/install.html?utm_source=chatgpt.com)                                                                 |
| Release 26.0.0 notes              | [https://arrow.apache.org/blog/2026/10/08/26.0.0-release/](https://arrow.apache.org/blog/2026/10/08/26.0.0-release/?utm_source=chatgpt.com)                                                   |
| Upstream source                   | [https://github.com/apache/arrow](https://github.com/apache/arrow?utm_source=chatgpt.com)                                                                                                     |

### Overall assessment

PyArrow 26.0.0 is best understood as a typed columnar data substrate with substantial native computation, relational processing, storage, and interoperability capabilities.

Its most distinctive strength is the combination of a common memory representation with mature Parquet and IPC implementations, vectorized kernels, increasingly capable streaming interfaces, and language-independent interoperability protocols.

It occupies a valuable position between low-level memory handling and full analytical database engines: capable enough to perform substantial processing itself, but sufficiently interoperable to let specialized engines handle SQL optimization, database connectivity, tensor computation, or durable transaction management.

For advanced systems, the important question is therefore not merely where PyArrow can replace a serializer or improve a file reader. It is which combinations of its data model, compute kernels, batch execution, dataset facilities, and interchange protocols allow entire layers of custom data-processing machinery to be avoided, while retaining the specialized responsibilities of the surrounding engines.

# PyArrow 26.0.0 — Advanced Capability Addendum

Apache Arrow Python bindings | Research date: November 1, 2026 | Baseline: PyArrow 26.0.0

Companion to: PyArrow 26.0.0 — Comprehensive Library Capability Reference (October 20, 2026)

This addendum documents advanced functionality that was absent or insufficiently developed in the original reference. It supplements the existing discussions of Arrow's data model, native computation, datasets, Parquet, IPC, memory management, interoperability, and Flight without reproducing their foundational explanations.

The capabilities described here have been checked against the released PyArrow 26.0.0 documentation and relevant upstream source. Version 26.0.0 remains the current stable Apache Arrow C++/Python release as of this research date.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow



## A. Physical data representations, validation, and schema composition

Supplements original §§2.1–2.3 and 8.1.

### A.1 Constructing and interpreting arrays from physical buffers

PyArrow exposes mechanisms for working directly with Arrow's physical memory layouts, beyond constructing arrays from Python or NumPy values.

`pa.Array.from_buffers()` constructs an Arrow array from a declared `DataType`, logical length, physical buffers, and—where necessary—nested child arrays. Its inputs can include a validity bitmap, values buffer, offsets, logical offset, and null count, depending on the type.

Complementary methods include `Array.buffers()`, which exposes the buffers underlying an existing array, and `Array.validate(full=True)`, which performs more extensive structural checks than the default inexpensive validation.

These facilities make it possible to construct Arrow representations around memory produced by native libraries, specialized parsers, or externally managed data structures without first materializing every value as a Python object.

The critical distinction is between constructing a valid Arrow representation and verifying the semantic correctness of its contents. Buffer lengths, offsets, validity bitmaps, and child-array layouts must satisfy Arrow's physical invariants. Structural validation does not establish application-specific constraints such as numerical ranges, units, referential integrity, or domain consistency.

Two other methods make the physical-versus-logical distinction explicit:

- `Array.view(target_type)` reinterprets existing buffers as another compatible type without performing ordinary value conversion. It requires a compatible physical layout.
- `Array.copy_to(destination)` copies array buffers, including nested child buffers, to a supported device or memory manager. This is a data-movement capability, not a guarantee that Arrow's normal CPU compute kernels can execute on the destination device.

An ordinary cast and a physical view therefore solve different problems. Casting expresses a value-level type conversion, potentially allocating new storage; viewing changes the interpretation of compatible existing storage.

These interfaces are particularly relevant to native interoperation, binary-format integration, and memory-layout inspection, although incorrect buffer construction can lead to invalid arrays and unsafe downstream behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.Array.html](https://arrow.apache.org/docs/python/generated/pyarrow.Array.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/data.html](https://arrow.apache.org/docs/python/data.html?utm_source=chatgpt.com)

### A.2 Concatenation with controlled schema promotion

`pa.concat_tables()` provides a more expressive schema-reconciliation mechanism than simple concatenation of identically typed tables.

Its `promote_options` parameter distinguishes three behaviors:

| Mode           | Behavior                                                                      | Consequence                                       |
| -------------- | ----------------------------------------------------------------------------- | ------------------------------------------------- |
| `"none"`       | Requires matching schemas, apart from permitted metadata differences          | Zero-copy concatenation of existing column chunks |
| `"default"`    | Promotes null-typed fields and creates null-valued columns for missing fields | Supports limited structural evolution             |
| `"permissive"` | Extends default behavior with compatible type promotion toward a common type  | Supports broader schema heterogeneity             |

The distinction matters because schema reconciliation can be separated from expensive reconstruction of an entire table. With identical schemas, concatenation can preserve existing chunks. With promotion, PyArrow may need to cast values or allocate null arrays.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



A related capability, `Dataset.replace_schema()`, creates a dataset view over the same fragments with a compatible replacement schema. Unlike permissive table concatenation, it does not implement arbitrary type evolution; incompatible replacement schemas are rejected.

Taken together, these interfaces provide distinct mechanisms for schema adjustment depending on whether data is already materialized or remains represented as dataset fragments.

Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.concat_tables.html](https://arrow.apache.org/docs/python/generated/pyarrow.concat_tables.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html?utm_source=chatgpt.com)

## B. Advanced native analytical computation

Supplements original §§3.1–3.3.

### B.1 Grouped collection, selection, and pivot operations

The grouped-aggregation interface supports several capabilities beyond conventional sums, counts, and statistical summaries.

| Native aggregation                           | Additional functionality                                           |
| -------------------------------------------- | ------------------------------------------------------------------ |
| `hash_list`                                  | Collects group members into list-valued results                    |
| `hash_distinct`                              | Collects distinct values for each group                            |
| `hash_count_distinct`                        | Counts distinct values within groups                               |
| `hash_first`, `hash_last`, `hash_first_last` | Selects boundary values according to the aggregation's input order |
| `hash_one`                                   | Selects one value from each group                                  |
| `hash_pivot_wider`                           | Pivots key/value categories into a structured wider representation |
| `hash_tdigest`                               | Computes approximate distributional quantiles within groups        |

The collection operators are particularly significant. A grouped result need not consist solely of scalar reductions: it can retain multiple values as an Arrow nested array.

For example, flat observations can be organized into groups whose values are list arrays, allowing subsequent Arrow operations to work with the grouped representation without constructing Python lists or dictionaries for each entity.

This is different from a scalar aggregate, which deliberately collapses each group to one numerical or categorical result. It also differs from a relational join, which retains relationships across rows through a combined table.

Grouped pivoting deserves special attention. `hash_pivot_wider` uses `PivotWiderOptions`, including explicit `key_names`, to establish the expected output categories. The output is a struct with fields corresponding to those categories. Unexpected keys can be ignored or rejected.

The pivot operation does not silently aggregate arbitrary duplicate cells. When more than one non-null value appears for the same pivot key in a group, it raises an error. This preserves a useful distinction between pivoting uniquely keyed values and aggregating multiple observations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



These operations expand the native options for reshaping and organizing records. However, hash-based grouping and parallel execution should not be assumed to preserve source order. Order-sensitive selection and list aggregation require particular care when deterministic sequencing is important.

Primary references:

[https://arrow.apache.org/docs/python/compute.html](https://arrow.apache.org/docs/python/compute.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.compute.PivotWiderOptions.html](https://arrow.apache.org/docs/python/generated/pyarrow.compute.PivotWiderOptions.html?utm_source=chatgpt.com)

### B.2 Prefix computations and state-dependent transformations

PyArrow provides native cumulative kernels that operate on ordered input sequences:

- `cumulative_sum` and `cumulative_sum_checked`
- `cumulative_prod` and `cumulative_prod_checked`
- `cumulative_mean`
- `cumulative_min` and `cumulative_max`

These calculate progressively accumulated results rather than independent element-wise transformations.

The checked arithmetic variants are consequential for integer correctness. For example, `cumulative_sum` can wrap on integer overflow, whereas `cumulative_sum_checked` raises an error rather than silently producing a wrapped result.

The cumulative kernels also expose null-handling policies. For `cumulative_sum`, the default `skip_nulls=False` causes nulls to propagate from the first encountered null; setting `skip_nulls=True` changes that behavior. Optional starting values allow some computations to incorporate an initial state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Additional state-dependent operations include:

| Function                               | Purpose                                                                       |
| -------------------------------------- | ----------------------------------------------------------------------------- |
| `pairwise_diff`                        | Computes differences between values at specified relative positions           |
| `fill_null_forward`                    | Propagates preceding valid values into null positions                         |
| `fill_null_backward`                   | Uses subsequent valid values to fill null positions                           |
| `rank_normal`                          | Computes normal-score ranks                                                   |
| `rank_quantile`                        | Computes quantile ranks                                                       |
| `partition_nth_indices`                | Performs nth-element partitioning without requiring a complete ordering       |
| `top_k_unstable` / `bottom_k_unstable` | Selects extreme elements without promising stable ordering                    |
| `winsorize`                            | Limits extreme values according to specified bounds or quantile-based options |

These functions cover useful portions of ordered analytical processing without requiring Python-level iteration. Their behavior nevertheless depends on which sequence is supplied and, for applicable operations, how ties, nulls, and NaNs are handled.

These kernels do not constitute a general SQL window-function system.

An array-level cumulative function calculates over its supplied sequence. It does not automatically partition by entity, sort by timestamp, maintain state across independently processed input batches, or implement arbitrary SQL window frames.

Likewise, availability in `pyarrow.compute` does not establish that a function can be embedded in a dataset scanner's row-aligned projection expression.

The architectural opportunity is therefore strongest when the desired ordering and grouping have already been established, or when the surrounding execution system explicitly supplies them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



Primary reference:

[https://arrow.apache.org/docs/python/api/compute.html](https://arrow.apache.org/docs/python/api/compute.html?utm_source=chatgpt.com)

## C. Dataset-level relational operations and scan composition

Supplements original §§4.1–4.2 and 5.1–5.3.

### C.1 Relational operations directly on datasets

The `pyarrow.dataset.Dataset` abstraction supports relational operations in addition to scanning and fragment discovery.

Its native methods include:

| Method                 | Capability                                                 |
| ---------------------- | ---------------------------------------------------------- |
| `Dataset.join()`       | Performs equality joins against another dataset            |
| `Dataset.join_asof()`  | Matches records by proximity along an ordered key          |
| `Dataset.filter()`     | Produces a dataset with an additional filtering expression |
| `Dataset.sort_by()`    | Sorts records by one or more fields                        |
| `Dataset.count_rows()` | Counts rows, potentially exploiting source metadata        |
| `Dataset.head()`       | Retrieves an initial subset of rows                        |
| `Dataset.take()`       | Retrieves rows by positional index                         |

`Dataset.join()` supports inner, outer, semi, and anti joins, together with differing left/right key names, suffixes, and key coalescing. This allows relational operations to be initiated from a file-backed dataset without an explicit application-level `to_table()` conversion.

`Dataset.join_asof()` supports proximity-based matching on integer, date, or timestamp keys. Both inputs must be sorted by the ordered key, and optional `by` keys constrain matching to equivalent groups.

Its tolerance is directional: a negative tolerance searches backward, a positive tolerance searches forward, and zero requires an exact ordered-key match. The allowed difference is calculated as the right key minus the left key, in the key's units.

The materialization boundary is essential. In PyArrow 26, `Dataset.join()`, `Dataset.join_asof()`, and `Dataset.sort_by()` return an `InMemoryDataset`. They are not deferred relational-plan nodes that automatically preserve the original dataset's lazy file-scanning behavior.

By contrast, `Dataset.filter()` returns a filtered dataset abstraction that can subsequently be scanned. `count_rows()` may exploit metadata and pruning, but a filtered count is not guaranteed to be metadata-only. `take()` and `head()` avoid requesting a complete result table, although the underlying access may still require reading preceding data.

These distinctions make the dataset API useful for relational composition while preserving a clear understanding of when execution and materialization occur.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html?utm_source=chatgpt.com)

### C.2 Scanner construction from existing streams

`Scanner` provides several construction and consumption interfaces that are not covered by the original scanner discussion.

`Scanner.from_batches()` creates a scanner from an existing record-batch source, including an appropriate `RecordBatchReader` or batch iterator. The resulting scanner can use familiar projection and filtering options.

The most important lifecycle characteristic is that a scanner created from batches is single-use. This reflects the fact that its underlying stream or generator may be consumed only once. It is not an independently restartable dataset definition.

This is consequential when connecting custom producers to native dataset writing: the producer can supply record batches without constructing a full table, but replay and retry behavior remain the responsibility of the surrounding system.

`Scanner.from_fragment()` creates an independently configured scan for a single fragment, while `Scanner.from_dataset()` builds one over an existing dataset.

On the consumption side:

- `to_reader()` exposes the scan as a `RecordBatchReader`, facilitating integration with other Arrow streaming APIs.
- `scan_batches()` yields `TaggedRecordBatch` objects associating each emitted batch with its source fragment.
- `projected_schema` exposes the schema after calculated projections, while `dataset_schema` describes the source-side schema.
- `head()` and `take()` provide selective materialization from a configured scanner.

The distinction between `to_batches()` and `scan_batches()` is particularly valuable for provenance. A plain `RecordBatch` contains its schema and values but not an explicit association with its originating dataset fragment. A tagged batch preserves that relationship in the scanner's output.

This can make file-level lineage, partition attribution, diagnostic grouping, and fragment-aware downstream processing more straightforward.

Source tags identify the fragment, not necessarily a permanently stable row identifier. Batch boundaries and fragment enumeration should not be treated as durable identities across independent scans unless the surrounding system establishes that guarantee.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html?utm_source=chatgpt.com)

### C.3 Parquet fragments as units of independent processing

`ParquetFileFragment` exposes row-group-level operations that provide more precise control than scanning an entire file as one indivisible source.

`split_by_row_group()` creates separate fragments for individual row groups. An optional filter can exclude row groups whose statistics prove that they cannot satisfy the predicate.

`subset()` instead constructs a fragment covering selected row groups, specified either through row-group identifiers or a compatible predicate.

`ensure_complete_metadata()` explicitly populates the fragment's Parquet metadata, making information such as the row-group structure available for inspection.

These operations permit a dataset's physical processing units to be decomposed more precisely than its file boundaries. They can support workload partitioning, selective rereads, and metadata-driven processing decisions without first decoding all the row values.

Crucially, splitting a Parquet fragment does not split or rewrite the physical file. It constructs fragment descriptions identifying which existing row groups should be read. Likewise, statistics-based filtering is conservative: a row group is excluded only when its metadata establishes that it cannot match.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



The complementary constructor `ds.parquet_dataset()` can build a dataset directly from a Parquet `_metadata` file containing aggregated row-group metadata and file paths.

This can avoid some repeated filesystem discovery and metadata reads, particularly when the data occupies many files in remote storage. The metadata file must nevertheless correspond to the actual dataset contents; PyArrow does not turn it into a transactional catalog.

Together, these capabilities offer a progression from dataset-level discovery to file-level fragments to row-group-level work units, while remaining within native PyArrow interfaces.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.dataset.ParquetFileFragment.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.ParquetFileFragment.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.dataset.parquet_dataset.html](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.parquet_dataset.html?utm_source=chatgpt.com)

## D. Storage configuration and ingestion semantics

Supplements original §§6.2–6.4 and 7.1–7.3.

### D.1 Parquet sortedness metadata and canonical logical types

Parquet writer options include `sorting_columns`, which records that a file's row groups follow a specified column ordering.

This option is a declaration, not an execution mechanism. It does not sort the input rows or independently validate their ordering.

Consequently, accurate sorting metadata can describe a useful property of an existing physical layout, but incorrect metadata does not become correct merely because the writer was instructed to emit it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Parquet also carries logical-type annotations that can be interpreted as Arrow extension types.

PyArrow 26 recognizes several important mappings:

| Parquet logical type | Arrow representation            |
| -------------------- | ------------------------------- |
| JSON                 | `arrow.json`                    |
| UUID                 | `arrow.uuid`                    |
| Geometry             | `geoarrow.wkb`, when registered |
| Geography            | `geoarrow.wkb`, when registered |

`arrow_extensions_enabled` controls this interpretation in relevant Parquet readers. The default is enabled; setting it to `False` requests the corresponding storage types.

Geometry and Geography require special care. Their extension representation requires a registered `geoarrow.wkb` type, which can be supplied by the separate `geoarrow-pyarrow` package. PyArrow itself does not thereby acquire a complete spatial query engine.

These distinctions are important when interpreting what survives a file-format boundary: the Parquet annotation, the Arrow extension representation, and the library implementing semantic operations over that representation are separate capabilities.

Serialized Arrow schema metadata may also affect type reconstruction, so the effective interpretation is not determined by the Parquet logical annotation alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/parquet/parquet_type_handling.html](https://arrow.apache.org/docs/python/parquet/parquet_type_handling.html?utm_source=chatgpt.com)

### D.2 IPC dictionary evolution and serialization control

`ipc.IpcWriteOptions` exposes several controls that materially affect IPC compatibility and representation.

Among them:

- `emit_dictionary_deltas`, allowing dictionary updates to be expressed as deltas where supported.
- `unify_dictionaries`, consolidating dictionary-encoded columns into a compatible common dictionary.
- `compression`, supporting IPC body compression with supported LZ4 or ZSTD codecs.
- `metadata_version`, controlling the IPC metadata representation.
- `use_legacy_format`, for compatibility with older IPC consumers.
- `allow_64bit`, governing serialization of structures requiring 64-bit lengths.

Dictionary evolution is the most important conceptual addition.

Arrow dictionary arrays can use different dictionaries across batches. IPC streams have mechanisms for communicating dictionary updates, while IPC files impose more restrictive rules about dictionary replacement. Writer-side dictionary unification can reconcile batches for file serialization, potentially remapping indices and allocating new data.

This means preserving dictionary encoding across batch boundaries is not simply a matter of serializing each batch independently. The surrounding IPC representation imposes additional constraints.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



On the reading side, `ipc.IpcReadOptions` includes `included_fields` for top-level field selection, together with controls for native endianness, alignment, and threaded decompression.

Field selection can avoid materializing unwanted fields. Alignment correction or endianness conversion can introduce copies even when the underlying IPC data would otherwise be shareable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcWriteOptions.html](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcWriteOptions.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html?utm_source=chatgpt.com)

### D.3 Message-level Arrow IPC interfaces

PyArrow also exposes interfaces beneath its ordinary IPC file and stream readers.

`ipc.Message` represents an IPC message with its metadata and body. `ipc.MessageReader` iterates over messages in an IPC stream, while functions such as `ipc.read_message()` and `ipc.read_record_batch()` support lower-level message processing.

These interfaces are useful for inspecting serialized data structures, implementing specialized transports, and diagnosing message boundaries or dictionary/schema coordination.

Unlike a high-level `RecordBatchReader`, a message reader exposes the framing layer instead of immediately abstracting it away.

The additional control comes with additional obligations. A record-batch message cannot always be interpreted independently of its schema and relevant dictionaries. Likewise, serializing individual messages is not automatically equivalent to constructing a valid, complete IPC stream or file.

For specialized interchange implementations, this message-level access can avoid rebuilding Arrow IPC framing logic from scratch while still allowing deliberate control over the transport and message lifecycle.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+2



Primary references:

[https://arrow.apache.org/docs/python/api/ipc.html](https://arrow.apache.org/docs/python/api/ipc.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.ipc.MessageReader.html](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.MessageReader.html?utm_source=chatgpt.com)

### D.4 CSV and JSON input policies

Beyond native parsing and type inference, PyArrow provides explicit policies for handling selected categories of structurally unexpected input.

For CSV, `csv.ParseOptions.invalid_row_handler` allows an application callback to determine whether a row with an unexpected number of columns should be skipped or treated as an error.

This supports selective rejection of malformed records without replacing the native CSV parser.

The handler's scope is deliberately limited: it is not a universal recovery callback for arbitrary type-conversion failures, invalid values, or business-level validation errors.

Other CSV parsing controls, such as allowing newlines inside quoted values, influence how the parser interprets record boundaries.

On the output side, `csv.CSVWriter` provides a stateful writer capable of accepting successive record batches, so CSV output need not first be assembled into one complete table.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



For JSON, `json.ParseOptions` exposes an explicit schema and an `unexpected_field_behavior` policy:

| Policy   | Behavior                                          |
| -------- | ------------------------------------------------- |
| `infer`  | Includes unexpected fields through type inference |
| `ignore` | Omits fields not present in the supplied schema   |
| `error`  | Rejects unexpected fields                         |

This is particularly consequential when an ingestion process needs to distinguish schema evolution from unexpected input.

The behavior is not merely a performance option. It determines whether newly encountered structure is incorporated, discarded, or treated as an error. As with CSV, these are parsing and structural policies, not a complete application validation system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.csv.ParseOptions.html](https://arrow.apache.org/docs/python/generated/pyarrow.csv.ParseOptions.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.csv.CSVWriter.html](https://arrow.apache.org/docs/python/generated/pyarrow.csv.CSVWriter.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.json.ParseOptions.html](https://arrow.apache.org/docs/python/generated/pyarrow.json.ParseOptions.html?utm_source=chatgpt.com)

## E. Native memory allocation, runtime diagnostics, and observability

Supplements original §§8.2–8.3.

### E.1 Allocator backends and allocation-lifecycle diagnostics

PyArrow exposes multiple native memory-pool backends, subject to how the underlying Arrow libraries were compiled.

The principal interfaces include:

- `pa.jemalloc_memory_pool()`
- `pa.mimalloc_memory_pool()`
- `pa.system_memory_pool()`
- `pa.supported_memory_backends()`
- `pa.jemalloc_set_decay_ms()`

This functionality makes allocator choice an explicit part of the native Arrow runtime rather than a property determined exclusively by the operating system's default allocator.

Different allocators can exhibit different behavior under repeated allocation, release, fragmentation, and concurrent access. However, the availability of a particular allocator does not establish that it will improve performance for every workload.

`MemoryPool` exposes further diagnostic information:

| Interface                 | Information or operation                                           |
| ------------------------- | ------------------------------------------------------------------ |
| `backend_name`            | Identifies the allocator implementation                            |
| `bytes_allocated()`       | Reports currently live allocations tracked by the pool             |
| `max_memory()`            | Reports peak tracked allocation, where supported                   |
| `num_allocations()`       | Counts allocations and reallocations                               |
| `total_bytes_allocated()` | Reports cumulative allocated bytes                                 |
| `print_stats()`           | Provides allocator-specific statistics                             |
| `release_unused()`        | Attempts to release retained unused memory to the operating system |

The distinction between current live allocation and cumulative allocation volume is particularly useful. A pipeline can have stable live memory while repeatedly allocating and releasing substantial intermediate buffers.

`release_unused()` should not be treated as a routine memory-management requirement. The upstream documentation describes it as best-effort and potentially expensive, with benchmarking and debugging as its main uses. It cannot guarantee that fragmented or allocator-retained pages will be returned to the operating system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



Primary references:

[https://arrow.apache.org/docs/python/api/memory.html](https://arrow.apache.org/docs/python/api/memory.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.MemoryPool.html](https://arrow.apache.org/docs/python/generated/pyarrow.MemoryPool.html?utm_source=chatgpt.com)

### E.2 Build, SIMD, and component introspection

PyArrow exposes runtime inspection facilities that help establish which capabilities are actually present in a deployed native build.

Important interfaces include:

- `pa.show_versions()` — reports PyArrow and Arrow C++ version/build information.
- `pa.show_info()` — reports platform, memory allocator, SIMD, optional components, filesystems, and available compression codecs.
- `pa.runtime_info()` — provides runtime CPU capability information, including detected and selected SIMD levels.
- `pa.is_opentelemetry_enabled()` — reports whether the linked Arrow libraries were built with OpenTelemetry support.

These facilities are more informative than checking `pa.__version__` alone. Two installations of the same PyArrow version can differ in their native components, allocator configuration, CPU instruction support, and optional features.

Arrow also recognizes runtime environment variables that affect operational behavior:

| Variable                    | Purpose                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| `ARROW_DEFAULT_MEMORY_POOL` | Selects an available default allocator backend                   |
| `ARROW_DEBUG_MEMORY_POOL`   | Enables basic native allocation-overflow diagnostics             |
| `ARROW_USER_SIMD_LEVEL`     | Limits runtime-selected SIMD dispatch on supported x86 platforms |
| `ACERO_ALIGNMENT_HANDLING`  | Controls behavior when Acero encounters unaligned buffers        |
| `ARROW_S3_LOG_LEVEL`        | Adjusts native S3 client logging verbosity                       |

For `ACERO_ALIGNMENT_HANDLING`, the options include warning, ignoring, rejecting, or reallocating unaligned buffers. Reallocation can make the operation safer with respect to alignment but introduces copying overhead.

`ARROW_USER_SIMD_LEVEL` is useful for investigating differences between CPU-dispatched execution paths. It does not disable instructions that the native binary requires because of its compile-time configuration.

Similarly, Arrow's debug memory-pool checks are not a substitute for comprehensive memory-safety instrumentation such as AddressSanitizer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Primary references:

[https://arrow.apache.org/docs/cpp/env_vars.html](https://arrow.apache.org/docs/cpp/env_vars.html?utm_source=chatgpt.com)

[https://github.com/apache/arrow/blob/apache-arrow-26.0.0/python/pyarrow/\_\_init\_\_.py](https://github.com/apache/arrow/blob/apache-arrow-26.0.0/python/pyarrow/__init__.py?utm_source=chatgpt.com)

### E.3 OpenTelemetry tracing in native Arrow execution

Apache Arrow's C++ implementation contains OpenTelemetry instrumentation that can expose aspects of execution below the Python call boundary.

This capability is distinct from Python-level profilers and memory-pool statistics. It can provide traces of instrumented native operations rather than merely observing the invocation of a Python method.

Arrow 24.0.0 enabled OpenTelemetry support in official PyArrow wheels. For custom Arrow C++ builds, tracing support is controlled by the `ARROW_WITH_OPENTELEMETRY` build option.

Once tracing support is compiled in, exporting traces requires an appropriate tracer configuration. Arrow supports configuration through `ARROW_TRACING_BACKEND`, including:

- `ostream` for textual output.
- `arrow_otlp_stdout` and `arrow_otlp_stderr` for structured JSON output.
- `otlp_http` for exporting traces to an OpenTelemetry-compatible HTTP endpoint.

An existing OpenTelemetry tracer provider can also be used in applicable native integrations.

Three conditions must be distinguished:

1. OpenTelemetry support is compiled into the native libraries.
2. Trace export is configured and active.
3. The operation being investigated is actually instrumented.

The first does not imply the second or third. `pa.is_opentelemetry_enabled()` checks build availability, not completeness of tracing coverage or successful delivery of exported traces.

This mechanism can provide valuable visibility into native execution that is otherwise difficult to infer from Python stack traces or wall-clock timings. It does not, however, automatically establish complete tracing across Python application code, external databases, and other execution engines.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



Primary references:

[https://arrow.apache.org/docs/cpp/opentelemetry.html](https://arrow.apache.org/docs/cpp/opentelemetry.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/cpp/env_vars.html](https://arrow.apache.org/docs/cpp/env_vars.html?utm_source=chatgpt.com)

## F. Additional conversion and interchange protocols

Supplements original §§9.3–9.5 and 10.4.

### F.1 Bidirectional DLPack integration

PyArrow 26's DLPack functionality extends beyond exporting Arrow data to numerical frameworks. It also provides native import interfaces:

| Interface                                | Accepted representation                                          |
| ---------------------------------------- | ---------------------------------------------------------------- |
| `pa.Array.from_dlpack()`                 | One-dimensional contiguous numerical data                        |
| `pa.Tensor.from_dlpack()`                | Multidimensional numerical tensor data                           |
| `pa.FixedShapeTensorArray.from_dlpack()` | Multidimensional tensor data represented as Arrow array elements |

These methods consume objects implementing the DLPack protocol without copying the underlying data when the documented requirements are met.

For example, `Tensor.from_dlpack()` preserves a multidimensional tensor representation, including shape and strides. `FixedShapeTensorArray.from_dlpack()` instead treats the outermost dimension as the Arrow array length and the remaining dimensions as each element's tensor shape.

This distinction allows the same general numerical memory representation to participate either as a standalone tensor or as a column of tensor-valued elements.

DLPack interoperability remains constrained by the representation involved. It does not preserve Arrow null bitmaps, heterogeneous fields, arbitrary nested structures, or application-specific extension semantics.

In PyArrow 26, the implementation is CPU-only. The fact that DLPack is a device-aware protocol generally does not establish that PyArrow can import or export arbitrary GPU-resident DLPack objects.

The import interfaces are nevertheless an important complement to the existing NumPy, pandas, and Arrow C Data integrations, particularly when the source already owns numerical buffers in a compatible layout.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/dlpack.html](https://arrow.apache.org/docs/python/dlpack.html?utm_source=chatgpt.com)

### F.2 Device-aware Arrow C interchange

The Arrow C Device Interface extends Arrow's language-independent data interchange model to device-resident arrays and streams.

The corresponding Python PyCapsule protocols include:

- `__arrow_c_device_array__`
- `__arrow_c_device_stream__`

These complement the existing CPU-oriented `__arrow_c_array__` and `__arrow_c_stream__` protocols.

The device-aware forms exchange `ArrowDeviceArray` and `ArrowDeviceArrayStream` structures, retaining Arrow's schema-based representation while identifying device-resident storage and its ownership requirements.

This capability is fundamentally different from DLPack.

DLPack is primarily designed around homogeneous numerical tensors. The Arrow C Device Interface retains Arrow's structured array model and is designed for interchange between implementations that understand the corresponding device-aware Arrow layouts.

A producer implementing the device-aware protocol does not need to pretend that its non-CPU memory is host-accessible. Conversely, a CPU-only export method must provide valid CPU-accessible pointers or decline the operation.

The protocol is intended to avoid unnecessary device transfers during interchange, but whether a particular exchange is zero-copy depends on the cooperating implementations and their memory-management obligations.

Protocol support should not be confused with device-native computation. Exchanging an Arrow structure that references device memory does not mean that PyArrow's ordinary compute kernels can safely operate on that memory.

This distinction is especially important when combining independently developed Arrow-compatible libraries with GPU-oriented native systems.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary references:

[https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/format/CDeviceDataInterface.html](https://arrow.apache.org/docs/format/CDeviceDataInterface.html?utm_source=chatgpt.com)

### F.3 Custom Python conversion through `__arrow_array__`

PyArrow supports a Python-specific conversion hook for third-party array-like objects.

An object implementing `__arrow_array__(self, type=None)` can control how `pa.array()` converts it into an Arrow array. The method may return a `pa.Array` or `pa.ChunkedArray`, and the optional `type` argument allows the caller's requested Arrow type to influence conversion.

This mechanism can integrate specialized Python containers, domain-specific collection classes, and alternative array implementations without requiring each caller to implement bespoke conversion logic.

Its architectural role is distinct from the Arrow PyCapsule protocol:

| Mechanism                  | Principal responsibility                                               |
| -------------------------- | ---------------------------------------------------------------------- |
| `__arrow_array__`          | PyArrow-specific conversion of custom Python array-like objects        |
| `__arrow_c_array__`        | Standardized Arrow array interchange across compatible implementations |
| `__arrow_c_stream__`       | Standardized interchange of Arrow record-batch streams                 |
| `__arrow_c_device_array__` | Device-aware Arrow array interchange                                   |

`__arrow_array__` may perform real conversion work and does not independently guarantee zero-copy results.

For broader interoperability, particularly where a producing library should not depend on PyArrow, the standardized Arrow PyCapsule interfaces provide a less Python-implementation-specific contract.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/extending_types.html](https://arrow.apache.org/docs/python/extending_types.html?utm_source=chatgpt.com)

### F.4 Consuming the DataFrame Interchange Protocol

The original guide identifies the outward-facing `Table.__dataframe__()` and `RecordBatch.__dataframe__()` methods. The corresponding input capability is `pyarrow.interchange.from_dataframe()`.

This function constructs an Arrow table from a DataFrame implementation that exposes the Python DataFrame Interchange Protocol.

It provides an additional route for interoperability when a producer implements `__dataframe__()` but not Arrow's C Data/PyCapsule interfaces.

This is useful as a compatibility mechanism, though the protocol's type representation is less expressive than Arrow's complete type system. The upstream PyArrow documentation recommends using Arrow PyCapsule interchange where supported.

The distinction is not merely about performance. A conversion route with a narrower type vocabulary may be unable to represent certain nested structures, extension semantics, or other Arrow-specific information without translation or loss.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/interchange_protocol.html](https://arrow.apache.org/docs/python/interchange_protocol.html?utm_source=chatgpt.com)

## G. Transport metadata and cloud-storage operational control

Supplements original §§11.1–11.2.

### G.1 Metadata-aware Arrow Flight streams

Arrow Flight supports application-defined metadata alongside streamed record batches.

The writer interfaces include:

| Interface                                  | Additional capability                                                        |
| ------------------------------------------ | ---------------------------------------------------------------------------- |
| `FlightStreamWriter.write_with_metadata()` | Writes a record batch with associated metadata                               |
| `FlightStreamWriter.write_metadata()`      | Sends metadata independently of a record batch                               |
| `FlightStreamWriter.done_writing()`        | Closes the outgoing direction while leaving the incoming direction available |
| `FlightStreamWriter.stats`                 | Exposes current IPC write statistics                                         |

On the receiving side, `FlightStreamReader.read_chunk()` returns a `FlightStreamChunk` containing a batch and its associated metadata, where present.

`FlightStreamReader.cancel()` allows an active read to be cancelled. Its `to_reader()` method adapts a Flight stream into a conventional `RecordBatchReader`, although this conversion can fail if the schema cannot be obtained from the remote endpoint.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0+1



These capabilities expand Flight from a mechanism for delivering batches into one capable of carrying application-defined information alongside a data stream.

That information can be used to express acknowledgments, progress, sequence markers, or other service-specific coordination semantics.

However, Flight itself does not interpret these metadata values as durable acknowledgments or transactional guarantees. Those semantics must be implemented by the communicating applications.

The distinction between `done_writing()` and closing the whole exchange is particularly consequential for bidirectional operations: the sender may have completed its input while still expecting the remote service to produce additional results.

Primary references:

[https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightStreamWriter.html](https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightStreamWriter.html?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightStreamReader.html](https://arrow.apache.org/docs/python/generated/pyarrow.flight.FlightStreamReader.html?utm_source=chatgpt.com)

### G.2 Native S3 operational configuration

`pyarrow.fs.S3FileSystem` exposes substantially more control than the basic ability to access S3 paths.

Its configuration covers several operational families:

Identity and credentials. The filesystem supports explicit credentials, automatic credential discovery, and role assumption through `role_arn`, `session_name`, and `external_id`. Temporary role credentials can be refreshed according to `load_frequency`.

Endpoint and transport configuration. `endpoint_override`, `scheme`, connection and request timeouts, proxy configuration, TLS settings, and virtual-host addressing controls support different S3-compatible endpoints and network environments.

I/O scheduling and error behavior. `background_writes`, `allow_delayed_open`, and retry strategies influence when network operations occur and how failures are surfaced.

Filesystem mutation controls. Explicit flags govern whether bucket creation and deletion are permitted.

`allow_delayed_open` illustrates a consequential tradeoff. It can reduce initial request latency by allowing an open operation to return before all remote checks have completed. However, failures such as nonexistent remote locations may then be reported only during later I/O or closure.

These controls make the native filesystem more than a uniform wrapper around object-store APIs. They allow connection, authentication, retry, and write behavior to be configured within Arrow's own I/O layer.

They do not turn S3 into a conventional transactional filesystem, and operational differences across storage providers remain important.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow v26.0.0



Primary reference:

[https://arrow.apache.org/docs/python/generated/pyarrow.fs.S3FileSystem.html](https://arrow.apache.org/docs/python/generated/pyarrow.fs.S3FileSystem.html?utm_source=chatgpt.com)

## H. Version-status correction: Gandiva Python bindings

Corrects the lifecycle classification in original §§12–13.

Apache Arrow 24.0.0 explicitly deprecated `pyarrow.gandiva`, stating that the Python binding will be removed in a future version.

This status remains relevant to a PyArrow 26.0.0 capability reference.

The original discussion of Gandiva as an optional LLVM-based native expression compiler remains conceptually useful. However, it should distinguish the native Gandiva component from the lifecycle status of its Python bindings.

The appropriate classification is:

- Native Gandiva: A separate, optional LLVM-based expression-compilation component within the Arrow C++ ecosystem.
- `pyarrow.gandiva`: Deprecated Python binding, not a recommended stable interface for new long-lived integrations.
- `pyarrow.compute` and Acero: Distinct native computation and execution interfaces, not replacements that necessarily reproduce every Gandiva implementation detail.

Deprecation does not mean that the Python binding has already been removed from every PyArrow 26 distribution. It means that continued availability and API compatibility should not be assumed indefinitely.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arrow.apache.org\&sz=32)

Apache Arrow



Primary references:

[https://arrow.apache.org/blog/2026/04/21/24.0.0-release/](https://arrow.apache.org/blog/2026/04/21/24.0.0-release/?utm_source=chatgpt.com)

[https://arrow.apache.org/docs/cpp/gandiva.html](https://arrow.apache.org/docs/cpp/gandiva.html?utm_source=chatgpt.com)

## Addendum synthesis

The additional capabilities extend PyArrow's usefulness in several architectural directions that are not fully apparent from its most familiar APIs.

Native relational processing is accessible at more levels than tables alone, but the distinction between dataset abstractions, scanner execution, and in-memory relational results determines whether an operation preserves incremental execution.

Native computation also encompasses more than row-wise kernels and scalar aggregates. Grouped collections, pivots, cumulative functions, and ordered transformations can eliminate bespoke calculations, provided their ordering, grouping, and state requirements are respected.

Storage interfaces expose more than file serialization. Parquet fragments and metadata enable finer-grained physical work decomposition; IPC options govern dictionary evolution, buffer compatibility, and serialized message handling; and parser policies make selected ingestion decisions explicit.

Interoperability is bidirectional and increasingly device-aware. DLPack import, custom Python conversion hooks, DataFrame interchange consumption, and the Arrow C Device protocols each address a different integration boundary. Their guarantees should not be conflated.

Finally, the native runtime provides more operational visibility and control than memory allocation totals alone. Allocator statistics, build inspection, SIMD configuration, OpenTelemetry, and transport-specific diagnostics can reveal implementation behavior that would otherwise require additional custom instrumentation.

These additions complete the most consequential capability gaps identified in the original PyArrow 26.0.0 reference while preserving its distinction between Arrow's native functionality, experimental or deprecated interfaces, and the responsibilities of adjacent execution and storage systems.