# oxrdflib — Comprehensive Python Library Overview

Target: oxrdflib 0.5.0 · Research date: October 29, 2026 · Ecosystem: RDFLib 7.x, pyoxigraph 0.5.x, Oxigraph (Rust)

## 1. Purpose and architectural positioning

oxrdflib integrates RDFLib's Python graph API with Oxigraph's Rust-based RDF database and SPARQL execution engine. It is a relatively small but architecturally consequential adapter: it allows applications to retain RDFLib's extensive graph-manipulation ecosystem while replacing its default storage and query implementation with Oxigraph.

Its principal capabilities are:

1. Native RDF storage: Persistent or in-memory RDF triple/quad storage backed by Oxigraph.
2. Native SPARQL execution: SPARQL 1.1 queries, dataset operations, and supported updates executed by Oxigraph rather than RDFLib's Python evaluator.
3. High-performance RDF I/O: Oxigraph parsers and serializers exposed as independently selectable RDFLib plugins, including optimized direct import/export paths.
4. RDFLib interoperability: Conventional RDFLib graph objects, terms, namespaces, graph operations, SPARQL results, and ecosystem integrations.
5. Advanced database access: Direct integration with `pyoxigraph.Store` for native operations not represented in RDFLib's store abstraction.

The architectural significance is that RDFLib can remain the semantic and application-facing interface while Oxigraph becomes the execution and persistence substrate. This can eliminate substantial custom graph-storage, query-processing, serialization, and interoperability machinery.

### 1.1 Version status

| Component    | Verified version                   | Role                               |
| ------------ | ---------------------------------- | ---------------------------------- |
| `oxrdflib`   | 0.5.0, released September 13, 2025 | RDFLib integration layer           |
| `pyoxigraph` | 0.5.13, released October 22, 2026  | Python bindings to Oxigraph        |
| `rdflib`     | 7.6.0, released February 13, 2026  | Python RDF graph API and ecosystem |
| Oxigraph     | 0.5-series through pyoxigraph      | Rust RDF engine and storage        |

Oxrdflib 0.5.0 declares `pyoxigraph~=0.5.0` and `rdflib>=6.3,<8.0`. These constraints permit newer compatible patch releases of pyoxigraph and RDFLib 7.x. Its declared Python minimum is 3.8, although the current pyoxigraph release requires Python 3.9 or newer, establishing a higher effective minimum for that dependency combination.

Sources:

- Package and release history: `https://pypi.org/project/oxrdflib/`
- Version-specific release notes: `https://github.com/oxigraph/oxrdflib/releases/tag/v0.5.0`
- Dependency declarations: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/pyproject.toml`
- Pyoxigraph: `https://pypi.org/project/pyoxigraph/`

## 2. Capability map

| Capability family          | What oxrdflib provides                                        | Main value or distinction                                                           |
| -------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| RDFLib store integration   | `OxigraphStore`, registered as `Oxigraph`                     | Reuses RDFLib interfaces with a different execution backend                         |
| Graph and dataset storage  | Triples, quads, contexts, named graphs                        | Native RDF datasets instead of application-managed graph partitioning               |
| RDF querying               | SPARQL 1.1 through Oxigraph                                   | Relational-style joins, filters, aggregations, graph traversal, and dataset queries |
| RDF updates                | Native SPARQL Update for supported contexts                   | Database-side mutations; RDFLib fallback remains for some graph contexts            |
| RDF parsing                | Native Turtle, TriG, N-Triples, N-Quads, N3, RDF/XML, JSON-LD | Avoids Python-level parsing and per-triple insertion on optimized paths             |
| RDF serialization          | Native Rust serializers exposed to RDFLib                     | Efficient graph and dataset export                                                  |
| Persistence                | Oxigraph memory or RocksDB-backed stores                      | Durable, indexed RDF storage                                                        |
| Advanced store operations  | Injection of `pyoxigraph.Store`                               | Access to backup, optimization, bulk operations, and read-only opening              |
| Ecosystem interoperability | RDFLib `Graph`, `Dataset`, terms, results, namespace APIs     | Compatibility with RDFLib-oriented tools and algorithms                             |
| Extension boundary         | RDFLib plugin protocol plus direct pyoxigraph access          | Choice between conventional Python abstractions and native capabilities             |

The most important distinction is between the capabilities of Oxigraph itself and those exposed by oxrdflib's RDFLib adapter. The underlying engine provides more functionality than the adapter automatically forwards; the boundary affects transactions, custom SPARQL functions, RDF-star, bulk loading, and database maintenance.

## 3. RDFLib integration and graph model

### 3.1 Store plugin and execution architecture

Oxrdflib implements RDFLib's `Store` interface through `OxigraphStore`. Installation registers the store under both `Oxigraph` and `oxigraph`, allowing ordinary RDFLib graph objects to use it without a separate registration procedure.

Its architecture has three layers:

| Layer                 | Responsibility                                                                                         | Consequential boundary                              |
| --------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| RDFLib                | Public `Graph` and `Dataset` APIs, RDF terms, namespace management, graph traversal, RDFLib extensions | Many operations remain Python-level                 |
| oxrdflib              | Store plugin, term conversion, SPARQL dispatch, parser/serializer integration                          | Determines which operations reach the native engine |
| pyoxigraph / Oxigraph | Indexed RDF storage, graph operations, SPARQL execution, parsing, serialization, persistence           | Supplies performance and database semantics         |

Store-level RDFLib operations implemented by oxrdflib include `add`, `addN`, `remove`, `triples`, `contexts`, `add_graph`, `remove_graph`, `query`, `update`, and namespace operations.

The adapter translates RDFLib's triple and context operations into Oxigraph's quad-oriented representation. This matters because multiple RDFLib `Graph` views can share a single physical RDF dataset.

Performance consequence: Python graph operations that call `Store.triples` repeatedly still perform Python/native conversions. SPARQL queries execute inside Oxigraph instead, generally making complex joins and graph-pattern operations more attractive to express as SPARQL than as Python loops.

Primary implementation: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/store.py`

### 3.2 Graphs, datasets, and contexts

The store declares `context_aware=True` and `graph_aware=True`.

A context corresponds to the graph component of an RDF quad. Oxrdflib supports named graphs identified by IRIs or blank nodes and maps RDFLib's dataset default-graph sentinel to Oxigraph's `DefaultGraph`.

This enables RDF data to be partitioned semantically without separate databases or application-maintained tables. For example, source documents, revisions, provenance layers, or ontology partitions can occupy distinct named graphs while remaining queryable together.

The distinction between RDFLib graph types is consequential:

| RDFLib abstraction                                | Meaning with oxrdflib                                                    |
| ------------------------------------------------- | ------------------------------------------------------------------------ |
| `Graph`                                           | A view of one graph identified by its `identifier`                       |
| `Dataset`                                         | An RDF dataset with a default graph and multiple named graphs            |
| `ConjunctiveGraph`                                | Legacy multi-context abstraction; supported, but RDFLib favors `Dataset` |
| `Graph` obtained from `Dataset.graph(identifier)` | A named-graph view sharing the dataset's underlying store                |

A newly constructed `Graph` without an explicit identifier normally receives a blank-node identifier. That is not automatically the same graph as the dataset's default graph. Persistent applications that recreate graph views should use stable graph identifiers or work through `Dataset.default_graph`.

### 3.3 Default-graph versus union semantics

SPARQL graph scope is governed by RDFLib's query context and Oxigraph's dataset parameters.

For `Graph.query`, oxrdflib passes the graph identifier as the native query's `default_graph`. For a dataset configured to use union semantics, it passes `use_default_graph_as_union=True`.

Consequently:

- A normal default-graph query does not necessarily inspect every named graph.
- A union-default-graph query treats the combined graph contents as the default query graph.
- A `GRAPH <iri>` clause accesses a specific named graph.
- Explicit dataset specifications inside SPARQL, including `FROM` and `FROM NAMED`, interact with these choices.

This is particularly important for provenance-sensitive data. A union view is convenient for finding statements regardless of origin, but it does not preserve the same distinctions as a query explicitly returning graph identities.

Oxigraph can also preserve the existence of empty named graphs. Their lifecycle is available through RDFLib's `add_graph`/`remove_graph` operations and native Oxigraph graph-management methods.

References: `https://rdflib.readthedocs.io/en/latest/apidocs/rdflib.graph/` and `https://pyoxigraph.readthedocs.io/en/stable/store.html`

## 4. SPARQL execution capabilities

### 4.1 Native query evaluation

The most consequential functional benefit is that SPARQL is evaluated by Oxigraph rather than RDFLib's Python evaluator.

Oxigraph implements SPARQL 1.1 Query, including graph-pattern joins, `OPTIONAL`, `UNION`, `FILTER`, `BIND`, `VALUES`, property paths, subqueries, aggregates, grouping, ordering, projection, and named-graph queries. It also supports federated queries using `SERVICE`, subject to engine-specific limitations.

This supports several higher-level operations without bespoke graph algorithms:

| Problem                                | Native SPARQL capability                               |
| -------------------------------------- | ------------------------------------------------------ |
| Traverse variable-length relationships | Property paths such as `+`, `*`, and alternative paths |
| Combine multiple semantic relations    | Basic graph patterns and joins                         |
| Handle incomplete records              | `OPTIONAL` and `COALESCE`                              |
| Extract derived values                 | `BIND`, expressions, string and datatype functions     |
| Perform grouped analysis               | `GROUP BY`, `HAVING`, aggregates                       |
| Query provenance partitions            | `GRAPH`, `FROM`, `FROM NAMED`                          |
| Build a derived RDF graph              | `CONSTRUCT`                                            |
| Check a logical condition              | `ASK`                                                  |
| Inspect remote RDF services            | Federated `SERVICE` queries                            |

This is a significant alternative to repeatedly enumerating triples and implementing joins, traversals, and filtering in Python.

Oxigraph also documents some extensions beyond SPARQL 1.1, including SPARQL-star and experimental `LATERAL` functionality. Its public wiki discusses additional calendar and duration operations. These are engine-level capabilities, not necessarily complete RDFLib-level guarantees, and some documentation predates the current engine release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



SPARQL reference: `https://github.com/oxigraph/oxigraph/wiki/SPARQL`

### 4.2 Query dispatch, bindings, and results

Oxrdflib's native query method accepts a SPARQL string, RDFLib namespace mappings, initial variable bindings, and the querying graph context.

It forwards namespace declarations to Oxigraph's `prefixes` parameter and maps `initBindings` to native `substitutions`.

The substitution mechanism is a meaningful 0.5.0 improvement: earlier implementations injected trailing `VALUES` clauses, whereas the current implementation uses Oxigraph's native variable-substitution model. The upstream README still contains the old explanation; the 0.5.0 changelog and tagged source establish the current behavior.

The result conversion differs by query form:

| Query form  | Native result                 | RDFLib-facing result                          | Materialization                                   |
| ----------- | ----------------------------- | --------------------------------------------- | ------------------------------------------------- |
| `SELECT`    | `QuerySolutions`              | RDFLib `Result` with variables and bindings   | Bindings generated lazily as results are consumed |
| `ASK`       | `QueryBoolean`                | RDFLib boolean result                         | Scalar                                            |
| `CONSTRUCT` | `QueryTriples`                | RDFLib `Result` holding a newly built `Graph` | Graph populated in Python                         |
| `DESCRIBE`  | Native graph-producing result | Adapted through the same triple-result branch | Graph populated in Python                         |

The implementation labels the graph-producing result branch `Result("CONSTRUCT")`, including native triple results originating from `DESCRIBE`; code depending on the exact RDFLib result type should account for this distinction.

Laziness is particularly important for large `SELECT` outputs. Oxigraph can produce result rows incrementally and oxrdflib converts terms as they are consumed. Conversely, a large `CONSTRUCT` result incurs construction of a Python RDFLib graph, potentially reducing the memory and performance advantages of native query execution.

Source: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/store.py`

### 4.3 Prepared queries and fallback execution

Oxrdflib does not support RDFLib's already parsed `Query` objects in its native execution method. It raises `NotImplementedError`.

However, RDFLib's `Graph.query` catches this exception and can fall back to its own SPARQL processor. Consequently, a query succeeding against an Oxigraph-backed graph does not necessarily establish that Oxigraph evaluated it.

RDFLib also exposes `use_store_provided=False`, explicitly bypassing the store's query implementation.

This creates a useful but potentially surprising dual execution model:

| Invocation                                            | Expected execution                                     |
| ----------------------------------------------------- | ------------------------------------------------------ |
| `graph.query("SELECT ...")`                           | Native Oxigraph, under supported parameters            |
| `graph.query(prepared_query)`                         | RDFLib fallback                                        |
| `graph.query("SELECT ...", use_store_provided=False)` | RDFLib                                                 |
| `store.query(...)` with an unsupported keyword        | Raises `NotImplementedError`                           |
| Direct `pyoxigraph.Store.query(...)`                  | Native Oxigraph, with its full documented argument set |

Both performance and semantics can vary across these paths, including treatment of extensions, custom functions, graph scope, and error behavior.

References: `https://github.com/oxigraph/oxrdflib/issues/26` and `https://rdflib.readthedocs.io/en/latest/apidocs/rdflib.graph/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rdflib.readthedocs.io\&sz=32)

RDFLib



### 4.4 Custom functions and aggregates

Pyoxigraph 0.5.13 supports `custom_functions` and `custom_aggregate_functions` directly on native `Store.query`, allowing application-defined scalar functions and aggregate accumulators to participate in SPARQL evaluation.

Oxrdflib 0.5.0 does not forward these parameters. Its store-level query method rejects additional keyword arguments.

RDFLib's custom SPARQL functions are also not automatically transferred into the Oxigraph evaluator. Native functions and RDFLib functions belong to different execution systems.

An open upstream request documents the missing integration. Until such functionality is released, the direct pyoxigraph interface is the supported route to native custom functions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Reference: `https://github.com/oxigraph/oxrdflib/issues/87`

### 4.5 SPARQL Update and atomicity

The `Dataset` abstraction can use Oxigraph's native SPARQL Update engine. This supports operations such as `INSERT DATA`, `DELETE DATA`, `DELETE/INSERT WHERE`, and graph-management statements.

At the native engine level, each `Store.update` call is transactional: the documented guarantee is that the complete operation succeeds or no changes are written.

However, oxrdflib's implementation rejects update requests with initial bindings, pre-parsed `Update` objects, unsupported keyword arguments, or a query context other than RDFLib's dataset default-graph identifier.

This is why updates issued through `Graph` or `ConjunctiveGraph` commonly fall back to RDFLib's processor, whereas `Dataset.update` can reach Oxigraph directly.

That distinction matters for both atomicity and performance:

- Native `Dataset.update` can leverage Oxigraph's transactional update engine.
- RDFLib-fallback updates execute through RDFLib's SPARQL update processor and its operations on the store.
- Neither provides a general-purpose RDFLib transaction spanning an arbitrary sequence of application operations.

Reference: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/CHANGELOG.md`

## 5. RDF parsing and serialization

### 5.1 Registered native formats

Oxrdflib's parser and serializer plugins are independently selectable from the backing store. They use the `ox-` prefix to distinguish Oxigraph implementations from RDFLib's standard plugins.

| RDF format        | Plugin identifiers                | Principal use                                            |
| ----------------- | --------------------------------- | -------------------------------------------------------- |
| N-Triples         | `ox-nt`, `ox-ntriples`, `ox-nt11` | Line-oriented triple interchange                         |
| N-Quads           | `ox-nq`, `ox-nquads`              | Line-oriented dataset interchange preserving graph names |
| Turtle            | `ox-ttl`, `ox-turtle`             | Compact, human-readable RDF graphs                       |
| TriG              | `ox-trig`                         | Compact RDF datasets with named graphs                   |
| N3                | `ox-n3`                           | Notation3 syntax                                         |
| RDF/XML           | `ox-xml`                          | XML-based RDF interchange                                |
| JSON-LD           | `ox-json-ld`                      | JSON-based linked-data interchange                       |
| Streaming JSON-LD | `ox-streaming-json-ld`            | Alternative parser with restricted JSON-LD processing    |

The streaming JSON-LD parser has distinct behavior. In the serializer registry, `ox-streaming-json-ld` is simply another name for the regular Oxigraph JSON-LD serializer, not a separate streaming serializer implementation.

Oxrdflib 0.5.0 introduced the JSON-LD plugins. Its release README describes streaming JSON-LD as JSON-LD 1.0-limited; newer pyoxigraph 0.5 releases have developed the standard JSON-LD implementation further. The compatibility profile should therefore be distinguished by parser and underlying pyoxigraph version rather than treating both JSON-LD plugins as identical.

Source: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/pyproject.toml`

### 5.2 Optimized native ingestion

A particularly valuable optimization occurs when both the parser and the store are supplied by Oxigraph.

The `ox-` parser detects `OxigraphStore` and calls native `pyoxigraph.Store.load` or `Store.bulk_load` directly. It does not convert every parsed quad into RDFLib objects and feed them back through the Python store interface.

This removes a potentially substantial cross-language overhead in large ingestion workloads.

By contrast, an Oxigraph parser operating against an ordinary RDFLib store still has to create RDFLib terms and insert them through that store. It may benefit from Rust parsing, but not from the full direct-to-native-storage pathway.

### 5.3 Transactional versus bulk ingestion

The parser exposes a consequential `transactional` parameter:

| Mode                           | Underlying operation | Advantages                                                      | Constraints                                                             |
| ------------------------------ | -------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `transactional=True` (default) | `Store.load`         | Atomic import; failure does not leave a partially imported file | Native documentation warns that the complete file is loaded into memory |
| `transactional=False`          | `Store.bulk_load`    | Designed for large files without keeping all content in memory  | Not atomic; partial ingestion can remain after failure                  |

The second path is more than an ordinary Python batch-size optimization. It uses Oxigraph's specialized bulk-loading mechanism, which can write data efficiently into the underlying storage system.

This distinction helps separate workloads requiring all-or-nothing ingestion from workloads prioritizing throughput and bounded memory.

Native reference: `https://pyoxigraph.readthedocs.io/en/stable/store.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation



### 5.4 Parser configuration boundaries

The wrapper accepts the parser's encoding and transactional settings and derives an RDF base IRI from the RDFLib input source.

At the native pyoxigraph level, additional parsing capabilities include `lenient` validation, blank-node renaming for standalone parsing, and control over named-graph handling.

These options should not be assumed to pass through `Graph.parse(format="ox-...")`. Oxrdflib's parser has a narrower signature than pyoxigraph's parsing APIs.

Native pyoxigraph therefore remains relevant when ingestion requires specialized parsing controls.

Reference: `https://pyoxigraph.readthedocs.io/en/stable/io.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation



### 5.5 Native serialization

Oxrdflib's serializer has a corresponding fast path: with an Oxigraph-backed RDFLib object, it invokes native `Store.dump` rather than iterating and converting every stored RDF term through Python.

Its scope depends on the RDFLib object:

- A `Graph` serializes its identified graph.
- A `Dataset` uses dataset-level export.
- A non-Oxigraph store uses pyoxigraph serialization but still requires conversion of RDFLib terms.

For datasets, TriG and N-Quads are especially important because they preserve named-graph structure. Turtle and N-Triples represent RDF graphs rather than arbitrary quad datasets.

The serializer supports UTF-8; non-UTF-8 encodings are rejected. Its implementation also does not forward arbitrary RDFLib serializer keyword arguments into native pyoxigraph serialization.

Source: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/serializer.py`

## 6. Persistence, consistency, and database operations

### 6.1 Memory and persistent storage

Oxrdflib can instantiate the underlying Oxigraph store lazily. Without an explicit persistent directory, the engine manages a temporary, non-durable store.

Calling RDFLib's `open` with a directory initializes persistent storage backed by Oxigraph's RocksDB-based implementation.

This makes the same application-facing graph abstraction usable for ephemeral computations, cached working datasets, and durable RDF repositories.

The backing store supplies indexed quad access, matching-pattern enumeration, and a native SPARQL engine. It is not equivalent to storing RDF as unindexed Python objects.

Oxrdflib's `open(configuration, create=True)` also has a notable implementation detail: it rejects an already existing target directory when `create=True`. Its `destroy(configuration)` implementation removes the specified directory tree.

### 6.2 Native consistency versus RDFLib transaction support

There are two distinct transaction concepts:

| Scope                                    | Supported behavior                          |
| ---------------------------------------- | ------------------------------------------- |
| Native pyoxigraph read/query             | Repeatable-read isolation for the operation |
| Native pyoxigraph `update`               | Atomic update                               |
| Native pyoxigraph `load`                 | Atomic import                               |
| Native pyoxigraph `extend`               | Atomic batch insertion                      |
| Oxrdflib `Store.commit()` / `rollback()` | Not implemented; both are no-ops            |
| Multiple arbitrary RDFLib operations     | No wrapper-managed transaction boundary     |

Oxigraph guarantees that readers do not observe partial committed writes during a read operation. That guarantee should not be confused with a Python-level transaction context that batches arbitrary RDFLib method calls.

The native distinction is valuable: some operations remain atomic without oxrdflib exposing a generic transaction API.

Reference: `https://pyoxigraph.readthedocs.io/en/stable/store.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation



### 6.3 Injecting an existing pyoxigraph store

`OxigraphStore` accepts an existing `pyoxigraph.Store` object through its keyword-only `store` parameter.

This is the most important advanced integration extension point because it allows RDFLib to operate over a store whose lifecycle and special configuration are managed through pyoxigraph.

It supports, among other things, a native read-only store, a previously initialized persistent store, or a store on which direct Oxigraph administrative operations are required.

The store must be injected at construction; calling oxrdflib's `open()` after injecting an already initialized store is rejected.

For use cases that mix both interfaces, the application can retain the native `pyoxigraph.Store` reference while RDFLib accesses the same database through the adapter.

### 6.4 Operations available through pyoxigraph

Several useful native capabilities are not separately elevated into oxrdflib's public RDFLib abstraction.

| pyoxigraph operation      | Functionality                                      | Architectural significance                               |
| ------------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| `Store.bulk_load`         | Large RDF file ingestion                           | Efficient loading without a full in-memory transaction   |
| `Store.bulk_extend`       | Streaming insertion of quads                       | Avoids buffering an entire Python quad collection        |
| `Store.backup`            | Independent snapshot backup of an on-disk database | Storage-level backup without RDF reserialization         |
| `Store.flush`             | Flush pending buffers to disk                      | Explicit durability coordination                         |
| `Store.optimize`          | Optimize database after batch-intensive work       | Native storage maintenance                               |
| `Store.read_only`         | Open existing persistent data read-only            | Separates readers from mutation operations               |
| `Store.quads_for_pattern` | Direct indexed quad lookup                         | Avoids RDFLib conversions when native terms are suitable |
| `Store.query`             | Native SPARQL execution with extended parameters   | Enables custom functions and dataset controls            |
| `Store.update`            | Atomic native SPARQL mutation                      | Supports operations beyond wrapper dispatch restrictions |

On-disk backups can use hard links for immutable files when the destination is on the same filesystem, making them comparatively inexpensive. Backups are unavailable for temporary in-memory stores.

An important read-only constraint: pyoxigraph explicitly states that opening a read-only store while another process is writing the database has undefined behavior. Read-only mode is not an automatically safe multi-process reader/writer architecture.

Primary source: `https://pyoxigraph.readthedocs.io/en/stable/store.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation



### 6.5 Storage compatibility and migration

Oxrdflib's upstream README warns that the underlying database storage format may change between releases. Its history includes a substantial 0.2-to-0.3 transition from Sled-based stores to RocksDB-based storage, requiring RDF export and reload.

A durable interchange format such as N-Quads or TriG is therefore more portable across storage-engine changes than depending exclusively on physical database files.

This matters for archival and long-lived data systems. Native backups and RDF exports solve different problems: a backup preserves the native database representation; RDF serialization provides an engine-independent logical representation.

Reference: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/README.md`

## 7. Semantic differences and important limitations

This section captures distinctions that can affect correctness even when the RDFLib-facing API appears compatible.

| Area                        | Specific behavior                                                                             | Consequence                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Relative IRIs               | Oxigraph does not store relative IRIs as RDF terms                                            | Relative references require appropriate base-IRI resolution during parsing |
| Namespaces                  | Bound prefixes are maintained by oxrdflib in memory, not persisted                            | Reopened databases may need prefixes rebound                               |
| Parsed prefixes             | The `ox-` parser may not propagate declared document prefixes into RDFLib's namespace manager | RDF data can parse correctly while original abbreviations are lost         |
| Formulas                    | `formula_aware=False`; quoted formula insertion is rejected                                   | RDFLib Notation3 formula semantics are not available through the store     |
| RDF-star                    | Native pyoxigraph supports quoted triple terms, but adapter conversion is incomplete          | RDF-star cannot be assumed to round-trip through RDFLib graph APIs         |
| Prepared SPARQL             | Native store rejects already-parsed query/update objects                                      | RDFLib fallback may change execution behavior                              |
| Custom SPARQL functions     | Not exposed by oxrdflib's native query method                                                 | Direct pyoxigraph access is needed                                         |
| Transactions                | `commit` and `rollback` are no-ops                                                            | No generic RDFLib-level transaction batching                               |
| `addN`                      | The implementation materializes converted quads into a list                                   | Not an unbounded streaming-bulk API                                        |
| Serialization compatibility | Rust and Python RDF serializers are not identical                                             | Prefixes, ordering, formatting, and output details may differ              |
| Graph identity              | A `Graph` without an explicit identifier normally receives a blank-node ID                    | Persisted graph retrieval depends on identifier choice                     |
| Dataset export              | Graph formats and dataset formats have different representational scopes                      | Preserve quads using an appropriate dataset format                         |

### 7.1 Namespace handling is a substantive integration detail

An open issue filed in May 2026 documents that parsing Turtle with `format="ox-ttl"` does not populate RDFLib's namespace manager with the prefixes declared in the input.

The RDF terms themselves can be ingested correctly. The missing information is the correspondence between the source document's prefix names and their namespace IRIs.

This may affect subsequent abbreviated serialization, query-prefix convenience, and tools that inspect the namespace manager.

Bindings made explicitly through RDFLib's `bind()` method are separate from document prefix declarations and remain non-persistent across store reopenings.

Source: `https://github.com/oxigraph/oxrdflib/issues/86`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.2 RDF-star is not full adapter-level RDF-star support

Oxigraph's underlying term model can represent a triple as a term. However, in oxrdflib 0.5.0, `_converter.from_ox` maps a native `ox.Triple` to an ordinary Python three-element tuple.

The reverse conversion does not establish a corresponding full RDFLib quoted-triple term representation.

Therefore, support at the native query or serialization level does not imply that RDF-star values can safely pass through every conventional RDFLib operation.

This is a consequential boundary for statement annotations, provenance modeling, and metadata about relationships.

Source: `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/_converter.py`

### 7.3 Literal identity and datatype semantics

The Oxigraph SPARQL documentation describes native normalization and numeric handling for typed literals, including integer, decimal, boolean, date/time, and duration values.

For example, it documents canonicalization of numeric lexical forms, which can distinguish Oxigraph behavior from workflows relying on preservation of the exact source lexical representation.

The same documentation describes bounded native numeric representations and certain arithmetic limitations. Because the wiki page was last edited in January 2023, its detailed numeric limits should be treated as historical upstream documentation requiring version-specific confirmation for Oxigraph 0.5.x.

The practical distinction is between RDF term value semantics and lexical-form preservation. Applications that rely on exact lexical forms, unusual datatypes, or specific ordering/comparison rules warrant equivalence checks.

Source: `https://github.com/oxigraph/oxigraph/wiki/SPARQL`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 8. Performance characteristics and capability composition

Oxrdflib's performance advantage is not uniform across all RDFLib operations. It depends on whether computation stays within Oxigraph or repeatedly crosses into Python.

### 8.1 Main performance levers

| Mechanism                       | Work avoided or changed                            | Limiting factor                                        |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| Native SPARQL                   | Python-side joins, filters, traversal, aggregation | Query planning, result size, RDF term conversion       |
| Indexed quad lookup             | Scanning arbitrary Python triple collections       | Access pattern and graph selectivity                   |
| Native parser + store           | Per-triple Python parsing and insertion overhead   | Validation and import atomicity settings               |
| Native serializer + store       | Per-triple Python iteration and formatting         | Output size and format                                 |
| Native `SELECT` result iterator | Eager construction of all RDFLib result rows       | Per-row conversion remains                             |
| Native `CONSTRUCT`              | Rust-based query processing                        | RDFLib output graph materialization                    |
| `bulk_load` / `bulk_extend`     | Full in-memory staging for large imports           | Weaker transaction behavior                            |
| Persistent Oxigraph store       | Bespoke on-disk RDF indexing                       | Storage footprint, compaction, operational constraints |

The major architectural opportunity is to keep high-cardinality graph operations inside the native execution engine, while using RDFLib for object-level manipulation and interoperability where those abstractions add value.

No general speedup factor is established by this overview. Performance is workload-sensitive, and published benchmark results should not be extrapolated to arbitrary RDF datasets or query structures.

### 8.2 When combinations are especially valuable

Native parsing + persistent storage + SPARQL. Data can move from RDF serialization into indexed storage and then into query evaluation without materializing all intermediate triples as RDFLib objects. This combines ingestion, persistence, graph indexing, and declarative querying.

Named graphs + SPARQL datasets. Multiple logical sources can coexist in one database. Graph identity becomes queryable metadata through the RDF dataset model, reducing the need to implement separate storage tables or manual graph partitioning.

RDFLib semantics + native backend. Existing RDFLib-based code can retain Python `URIRef`, `BNode`, `Literal`, `Graph`, and `Dataset` interfaces. More expensive operations can be pushed into SPARQL without introducing an entirely different public graph API.

Dual-interface access. A retained `pyoxigraph.Store` handle can expose native backup, maintenance, custom functions, and bulk ingestion while oxrdflib supplies the RDFLib compatibility layer. The benefit is flexibility, but ownership and operation ordering remain application responsibilities.

### 8.3 Cases where performance benefits diminish

Repeated calls to `Graph.triples()` in Python, object-by-object updates, conversions to large Python collections, and materialized `CONSTRUCT` results can reintroduce substantial Python overhead.

Likewise, using a normal RDFLib parser instead of an `ox-` parser with Oxigraph storage may prevent the optimized direct ingestion path.

RDFLib utilities, graph traversal methods, and third-party extensions do not automatically become native Rust algorithms merely because their backing graph uses oxrdflib.

These distinctions are useful for identifying which computation is actually accelerated, rather than treating a native store as a blanket speedup for the entire RDFLib ecosystem.

## 9. Ecosystem integration and adjacent capabilities

### 9.1 RDFLib

RDFLib is the application-facing RDF framework. It provides term classes, graph and dataset abstractions, namespace utilities, graph traversal, Python integration, plugin interfaces, and numerous companion libraries.

Oxrdflib replaces its backing store and selected parsing, serialization, and SPARQL execution components. It does not replace RDFLib itself.

Official documentation: `https://rdflib.readthedocs.io/`

### 9.2 pyoxigraph

Pyoxigraph is the direct Python binding to Oxigraph and exposes the fuller native engine API.

It is preferable at the integration boundary when an operation specifically needs native quads, storage maintenance, custom functions, specialized parsing controls, backup, or bulk insertion without RDFLib conversion.

It also provides standalone parsing and serialization functions, enabling native RDF I/O without constructing an RDFLib graph.

Official documentation: `https://pyoxigraph.readthedocs.io/en/stable/`

### 9.3 Oxigraph and its other interfaces

Oxigraph itself is the Rust RDF engine. Its Rust crate and command-line/server tooling are distinct from the Python packages.

The engine's capabilities include RDF data storage, SPARQL queries and updates, and RDF serialization. Oxrdflib does not itself provide an HTTP SPARQL server, authentication system, distributed database, or graph service deployment framework.

Official project: `https://github.com/oxigraph/oxigraph`

### 9.4 Validation, reasoning, and ontology tooling

An Oxigraph-backed RDFLib graph can be used as input for RDFLib-oriented libraries such as SHACL validators and ontology tooling, provided they operate through compatible RDFLib APIs.

However, oxrdflib is not itself a SHACL validation engine or OWL/RDFS reasoner. Nor does it transparently convert third-party RDFLib validation or reasoning algorithms into Oxigraph-native computation.

Those capabilities have separate implementation and performance boundaries. In particular, Python-level validation traversals may continue to make many individual store calls, whereas validation logic expressible as SPARQL can use native query execution where the integration supports it.

### 9.5 Security boundary

Oxigraph's SPARQL support includes operations that can interact with external network resources, such as federated `SERVICE` queries and supported update loading operations.

RDFLib's documentation explicitly warns that SPARQL processing can access network resources indirectly. A native backend does not remove the need for appropriate file/network restrictions when evaluating untrusted queries or parsing untrusted linked-data documents.

Oxrdflib does not itself supply an authorization policy or sandbox for arbitrary SPARQL.

RDFLib security documentation: `https://rdflib.readthedocs.io/en/latest/security_considerations/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rdflib.readthedocs.io\&sz=32)

RDFLib



## 10. Choosing the appropriate abstraction

The useful question is not simply whether to use RDFLib or pyoxigraph, but which layer should own each operation.

| Requirement                                     | Natural interface                           | Reason                                         |
| ----------------------------------------------- | ------------------------------------------- | ---------------------------------------------- |
| Ordinary Python RDF graph manipulation          | RDFLib + oxrdflib                           | Existing graph API and ecosystem compatibility |
| Indexed persistent RDF dataset                  | RDFLib + oxrdflib                           | Native storage beneath RDFLib                  |
| Complex SPARQL over RDFLib graphs               | oxrdflib native query path                  | Rust execution with RDFLib result conversion   |
| Large atomic RDF file ingestion                 | Oxigraph parser + store, transactional mode | Direct ingestion with import-level atomicity   |
| Very large bounded-memory ingestion             | Oxigraph bulk-loading path                  | Specialized native loading                     |
| RDFLib-oriented third-party library integration | RDFLib + oxrdflib                           | Conventional graph interface                   |
| Custom SPARQL scalar/aggregate functions        | Direct pyoxigraph                           | Wrapper does not currently forward these       |
| Storage backup and optimization                 | Direct pyoxigraph                           | Native administration APIs                     |
| Read-only persistent data access                | Injected `pyoxigraph.Store.read_only`       | Supported native store configuration           |
| Full RDF-star term interoperability             | Investigate native pyoxigraph               | RDFLib adapter term conversion is incomplete   |
| SHACL validation or OWL reasoning               | Dedicated RDF tooling                       | Not supplied by oxrdflib                       |
| SPARQL HTTP service                             | Oxigraph server or another service layer    | Outside oxrdflib's responsibilities            |

The key architectural distinction is execution ownership. RDFLib defines a convenient semantic and Python integration surface; oxrdflib determines how much of that surface can delegate to the native Oxigraph engine; pyoxigraph provides the engine's wider Python-native capabilities.

For an RDF-centric Python system, this combination can be substantially more capable than relying only on RDFLib's default in-memory graph. But the greatest benefit comes from using the appropriate native execution paths rather than assuming every RDFLib method has been accelerated.

## 11. Primary source map

| Area                                                         | Source                                                                        |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Package overview, compatibility, examples, known differences | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/README.md`                  |
| Release-specific changes                                     | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/CHANGELOG.md`               |
| Dependencies and plugin registrations                        | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/pyproject.toml`             |
| RDFLib store implementation and SPARQL dispatch              | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/store.py`      |
| Native parser bridge and ingestion modes                     | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/parser.py`     |
| Serialization bridge and native export                       | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/serializer.py` |
| RDFLib ↔ Oxigraph term conversion                            | `https://github.com/oxigraph/oxrdflib/blob/v0.5.0/src/oxrdflib/_converter.py` |
| Native store, consistency, backup, bulk operations           | `https://pyoxigraph.readthedocs.io/en/stable/store.html`                      |
| Native parsing and serialization                             | `https://pyoxigraph.readthedocs.io/en/stable/io.html`                         |
| Oxigraph SPARQL implementation and extensions                | `https://github.com/oxigraph/oxigraph/wiki/SPARQL`                            |
| RDFLib graph and dataset behavior                            | `https://rdflib.readthedocs.io/en/latest/apidocs/rdflib.graph/`               |
| Namespace propagation limitation                             | `https://github.com/oxigraph/oxrdflib/issues/86`                              |
| Custom SPARQL function integration request                   | `https://github.com/oxigraph/oxrdflib/issues/87`                              |
| Prepared query limitation                                    | `https://github.com/oxigraph/oxrdflib/issues/26`                              |

The overview is based on the tagged oxrdflib 0.5.0 implementation and current published pyoxigraph documentation. Features attributed to pyoxigraph rather than oxrdflib have been distinguished explicitly; no local benchmarks or execution tests are implied.