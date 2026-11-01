# PyOxigraph — Comprehensive Python Library Capability Reference

Version 0.5.13 · Released October 22, 2026 · Researched October 29, 2026

PyOxigraph is an embedded RDF graph database and semantic-query toolkit for Python, built on the Rust-based Oxigraph engine through PyO3. It provides native RDF data structures, indexed graph storage, SPARQL query and update execution, RDF parsing and serialization, and extensibility through custom query functions.

Its principal architectural value is that it combines a standards-based graph data model, native graph-query execution, and persistent storage within a single Python-accessible engine. Applications can use relational-style querying over arbitrary RDF relationships without implementing their own graph traversal, indexing, or query execution infrastructure.

Official documentation: `https://pyoxigraph.readthedocs.io/en/stable/`

Upstream repository: `https://github.com/oxigraph/oxigraph`

PyPI: `https://pypi.org/project/pyoxigraph/`

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph.readthedocs.io+1

## 1. Architecture and capability orientation

PyOxigraph has five principal capability families:

| Capability                   | Native mechanisms                                                                   | Architectural role                                                                        |
| ---------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| RDF data modeling            | Named nodes, blank nodes, typed literals, triples, quads, datasets                  | Standards-based representation of entities, relationships, attributes, and graph contexts |
| Graph storage                | In-memory and persistent stores, indexed quad operations, graph management          | Embedded graph database with local query execution                                        |
| Graph querying               | SPARQL 1.1 query/update, property paths, joins, aggregation, query-level controls   | Declarative relationship exploration and transformation                                   |
| RDF interoperability         | Streaming parsers, serializers, multiple RDF formats, SPARQL result formats         | Exchange with semantic-web tooling and external datasets                                  |
| Advanced engine capabilities | Custom SPARQL functions/aggregates, bulk loading, dataset canonicalization, backups | Extension, efficient ingestion, reproducibility, and operational management               |

### 1.1 Three distinct levels of functionality

RDF model and dataset layer: Native Python objects represent RDF terms and graph relationships. These can be used independently of a database and support semantic processing or data exchange.

Embedded database layer: `Store` provides efficient indexed access, SPARQL evaluation, persistence, and mutations. The underlying engine is Rust; Python remains the orchestration and extension language.

Ecosystem layer: The related `oxrdflib` package integrates Oxigraph-backed storage and querying with RDFLib's APIs. The separate Oxigraph server and Rust crates expose additional capabilities not necessarily available directly through PyOxigraph.

This separation matters: PyOxigraph is considerably more than a parser or graph-object package, but it is not equivalent to the complete Oxigraph server distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 2. RDF data model and in-memory graph operations

### 2.1 RDF terms, identity, and typing

PyOxigraph represents relationships using the RDF subject–predicate–object model rather than conventional property-graph vertices and edges.

| Type           | Semantics and notable capabilities                                                             |
| -------------- | ---------------------------------------------------------------------------------------------- |
| `NamedNode`    | IRI-identified resource; validates IRIs against RFC 3987                                       |
| `BlankNode`    | Anonymous RDF resource with explicit or automatically generated identifier                     |
| `Literal`      | Lexical value with datatype, optional language tag, and optional text direction                |
| `Triple`       | RDF statement comprising subject, predicate, and object; also represents embedded triple terms |
| `Quad`         | Triple associated with a graph name, allowing multiple distinct graph contexts                 |
| `DefaultGraph` | Explicit representation of the unnamed/default graph                                           |
| `Variable`     | Validated SPARQL variable used in query substitutions and results                              |

Typed literals are particularly important. `Literal` accepts Python strings, integers, floats, and booleans, with Python primitive inputs mapped into appropriate RDF typed literals. It also supports explicitly supplied datatype IRIs and language-tagged strings.

However, `Literal.value` returns a string lexical form, not a Python object automatically reconstructed from the RDF datatype. A typed integer, date, or decimal therefore retains RDF lexical and datatype semantics even when downstream Python code wants a native numeric or temporal representation.

The distinction preserves important information: an RDF term is not simply a Python value. Equality, language, lexical representation, and datatype can matter independently.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+2



### 2.2 Quads and named graphs

A quad comprises `(subject, predicate, object, graph_name)`.

The graph component can provide structured separation by source, version, tenant, provenance context, or logical dataset partition without requiring new tables or alterations to a physical schema.

The same relationship can occur in multiple named graphs. In RDF dataset semantics, these are distinct quads, and the graph names participate in query matching.

Useful consequences:

- Schema flexibility: New predicates and relationships can be inserted without physical column migrations.
- Context separation: Different relationship sets can coexist while remaining queryable together.
- Provenance organization: Graph membership can preserve a dataset's source or processing context.
- Graph-scoped operations: Insertion, querying, clearing, and removal can operate on selected graphs.

Graph membership itself does not provide access control, automatic provenance verification, or version-history management. Those require additional semantics or enforcement.

### 2.3 `Dataset`: a separate in-memory indexed RDF collection

One of PyOxigraph's less obvious capabilities is the standalone `Dataset` class.

`Dataset` provides an in-memory RDF quad collection without requiring `Store`. Its primary operations include:

| Operation                               | Capability                                                            |
| --------------------------------------- | --------------------------------------------------------------------- |
| `add`, `remove`, `discard`, `clear`     | Set-like mutation of quads                                            |
| `quads_for_subject`                     | Subject-oriented lookup                                               |
| `quads_for_predicate`                   | Predicate-oriented lookup                                             |
| `quads_for_object`                      | Object-oriented lookup                                                |
| `quads_for_graph_name`                  | Graph-oriented lookup                                                 |
| `canonicalize`                          | Deterministic blank-node relabeling according to a selected algorithm |
| Iteration, membership, length, equality | Python collection-style interaction                                   |

The documentation describes suitability for datasets containing up to a few million quads, although actual practical limits depend on graph structure and available memory.

Important limitation: `Dataset` interns strings without garbage-collecting unused terms. Repeated insertion and removal of many distinct RDF terms can therefore produce retained memory growth.

`Dataset` also does not provide `Store`'s SPARQL execution or on-disk persistence. This makes it a distinct data structure, not simply a faster variant of the database.

Source: `https://pyoxigraph.readthedocs.io/en/stable/model.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+2



### 2.4 RDF dataset canonicalization

`Dataset.canonicalize(algorithm)` is an unusually valuable native capability for applications that must compare or identify RDF content despite arbitrary blank-node identifiers.

Supported algorithms:

| Algorithm                                    | Distinction                                                         |
| -------------------------------------------- | ------------------------------------------------------------------- |
| `CanonicalizationAlgorithm.RDFC_1_0`         | W3C RDF Dataset Canonicalization 1.0                                |
| `CanonicalizationAlgorithm.RDFC_1_0_SHA_384` | Canonicalization variant using SHA-384                              |
| `CanonicalizationAlgorithm.UNSTABLE`         | PyOxigraph's alternative, non-standard-stability-oriented algorithm |

Canonicalization renames blank nodes so that equivalent graph structures can be compared under a consistent labeling scheme.

This can support graph equivalence testing, content-addressed representations, deterministic exchange, and preparation for RDF signing workflows.

Two significant qualifications:

1. Canonical identifiers are graph-dependent. Adding one quad may change the canonical identifiers of many existing blank nodes. Canonicalization is not inherently a good basis for incremental structural diffs.
2. Worst-case complexity is exponential in the number of blank nodes. Highly symmetric or adversarial graphs can be expensive.

Also, producing a standardized canonical representation is not equivalent to implementing digital signatures or cryptographic verification. Those remain separate operations.

Source: `https://pyoxigraph.readthedocs.io/en/stable/model.html#pyoxigraph.Dataset.canonicalize`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+1



## 3. Embedded graph storage and transaction semantics

### 3.1 Two storage modes through one API

PyOxigraph exposes both memory-resident and persistent database operation through `Store`.

| Mode             | Construction            | Characteristics                                               |
| ---------------- | ----------------------- | ------------------------------------------------------------- |
| In-memory        | `Store()`               | No durable data files; data lifetime follows the store object |
| Persistent       | `Store(path)`           | RocksDB-backed indexed storage in a directory                 |
| Static read-only | `Store.read_only(path)` | Opens existing persistent data without permitting mutations   |

The persistent backend uses RocksDB, a log-structured merge-tree key-value engine. It is optimized around multiple indexed representations of RDF quads.

The in-memory mode is a genuine database capability: it supports SPARQL querying and mutation, rather than merely holding Python lists of triples.

### 3.2 Transactional behavior and isolation

PyOxigraph documents repeatable-read isolation for `Store`:

- Reads observe committed state rather than partial writes.
- A read operation sees a stable database snapshot throughout its execution.
- SPARQL updates execute atomically.
- `Store.extend()` and `Store.load()` are explicitly documented as transactional.

This makes it possible to express multiple related graph changes using one SPARQL update while avoiding externally visible intermediate states.

Important boundary: Repeatable read should not be interpreted as a universal guarantee of serializable concurrency. Upstream describes cases in which conflicting concurrent writes are not detected by the persistent engine.

The Rust Oxigraph API has lower-level explicit transaction functionality, but PyOxigraph 0.5.13 does not expose an equivalent general-purpose Python transaction object in its documented `Store` API. Atomic multi-step operations therefore need to use the supported transactional entry points rather than assuming a Python `begin`/`commit` interface.

### 3.3 Native graph operations

Beyond SPARQL, `Store` supports direct indexed operations:

| Functional area        | Methods                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Quad mutation          | `add`, `remove`, `extend`, `bulk_extend`                                           |
| Quad retrieval         | `quads_for_pattern`, iteration, membership                                         |
| Graph lifecycle        | `add_graph`, `remove_graph`, `clear_graph`, `contains_named_graph`, `named_graphs` |
| Dataset lifecycle      | `clear`, `load`, `bulk_load`, `dump`                                               |
| Persistence management | `flush`, `optimize`, `backup`                                                      |

`quads_for_pattern(subject, predicate, object, graph_name)` accepts `None` for wildcard components, enabling direct indexed retrieval without constructing a SPARQL query. To restrict matching to the default graph, callers pass `DefaultGraph()`; `graph_name=None` means match any graph.

That distinction is consequential for correctness: an omitted graph constraint is not equivalent to selecting the default graph.

The named-graph lifecycle APIs also preserve empty graph identity. `clear_graph()` removes graph contents while retaining the graph; `remove_graph()` removes the named graph itself.

### 3.4 Snapshot backups, durability, and maintenance

`Store.backup(target_directory)` creates an independently usable copy of a persistent database. On the same filesystem, the implementation can use hard links to immutable snapshot files instead of fully copying the contents.

`Store.flush()` ensures pending writes reach disk; background flushing otherwise occurs automatically.

`Store.optimize()` performs storage optimization intended to improve subsequent workloads, particularly after substantial ingestion.

Operational limitations:

- Backups require an on-disk `Store`.
- Backup target directories must not already exist.
- Backups are physical Oxigraph database copies, not portable RDF interchange files.
- Opening a read-only database while another process writes to that same database is explicitly documented as undefined behavior.
- Persistent storage has RocksDB-specific layout and compatibility considerations; RDF export is the portable boundary.

The engine's isolation and storage mechanisms are substantial advantages over custom Python dictionaries and adjacency structures, but their write-amplification, disk usage, and concurrency costs remain workload-dependent.

Sources: `https://pyoxigraph.readthedocs.io/en/stable/store.html` and `https://github.com/oxigraph/oxigraph/wiki/Architecture`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+3



## 4. SPARQL query execution and graph computation

### 4.1 Declarative relationship processing

`Store.query()` executes SPARQL queries directly against the indexed RDF dataset.

The supported SPARQL 1.1 functionality encompasses:

| Query family             | Capabilities                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| Graph pattern matching   | Basic graph patterns, joins across arbitrary relationships, `GRAPH`, `OPTIONAL`, `UNION`, `MINUS`     |
| Graph traversal          | Property paths, including sequences, alternatives, inverse paths, and transitive paths                |
| Relational operations    | `FILTER`, `BIND`, `VALUES`, projections, subqueries, `DISTINCT`, ordering, limiting                   |
| Aggregation              | `GROUP BY`, `HAVING`, standard aggregates such as `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `GROUP_CONCAT` |
| Existence and negation   | `EXISTS`, `NOT EXISTS`, optional matches, anti-joins                                                  |
| Result construction      | `SELECT`, `ASK`, `CONSTRUCT`, `DESCRIBE`                                                              |
| Dataset-aware operations | Named graph matching, graph-specific datasets, union default graphs                                   |
| Federation               | SPARQL `SERVICE` operations targeting remote endpoints                                                |

Property paths are especially consequential. A query can follow variable-length relationships without an application-managed recursive loop or a precomputed transitive-closure table. This is useful for hierarchical containment, dependency reachability, taxonomy traversal, and semantic connectivity.

The tradeoff is that complex traversal remains subject to SPARQL semantics and execution-plan costs; the existence of property paths does not imply availability of specialized shortest-path algorithms, PageRank, community detection, or weighted graph optimization.

### 4.2 Query-scoped dataset configuration

PyOxigraph exposes controls beyond ordinary SPARQL query text:

| `Store.query()` argument     | Architectural significance                                                      |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `default_graph`              | Select one or multiple graphs to contribute to the query's active default graph |
| `named_graphs`               | Restrict the named graphs available to `GRAPH` matching                         |
| `use_default_graph_as_union` | Make default-pattern matching include all dataset graphs                        |
| `prefixes`                   | Supply namespace prefix mappings without repeating declarations in every query  |
| `base_iri`                   | Resolve relative IRIs in the query                                              |
| `substitutions`              | Supply RDF terms for query variables                                            |
| `custom_functions`           | Extend scalar SPARQL expression evaluation                                      |
| `custom_aggregate_functions` | Extend aggregate evaluation                                                     |

These features make it possible to reuse one graph-query definition across several logical graph contexts.

The default graph versus union default graph distinction is material. By default, an unqualified triple pattern searches the active default graph; it does not silently scan every named graph. Activating `use_default_graph_as_union=True` changes that behavior, potentially changing both results and query cost.

Likewise, `named_graphs` is a query dataset restriction, not an authorization mechanism. Applications requiring tenant or user isolation need enforcement beyond merely choosing a named graph.

### 4.3 Structured variable substitution

`substitutions` accepts mappings from `Variable` objects to RDF terms, including named nodes, blank nodes, literals, and supported triple terms.

This allows application-provided terms to be bound structurally instead of manually concatenating escaped values into query strings.

The mechanism follows the RDF development community's SEP-0007 substitution proposal.

It is valuable for reusable queries, safe term handling, and avoiding repeated query-text construction. However, it should not be confused with a documented server-side prepared-statement cache or a general-purpose SQL-style parameter protocol. Query parsing and optimization costs are not necessarily eliminated.

### 4.4 Custom scalar and aggregate functions

A particularly important extension point is Python-defined computation within SPARQL execution.

`custom_functions` maps function IRIs (`NamedNode`) to Python callables. The callables receive RDF terms and return an RDF term or `None`.

`custom_aggregate_functions` maps aggregate-function IRIs to zero-argument factories. Each factory returns an accumulator implementing:

- `accumulate(term)` — incorporate an input term.
- `finish()` — return the aggregate RDF term.

Both extension mechanisms are supported by the query and update interfaces.

They enable domain-specific calculations, normalization, matching, and aggregate logic to participate inside native SPARQL expressions, rather than requiring all query results to be materialized for a subsequent Python processing pass.

The important execution boundary is that Python callbacks cross back out of the Rust engine. A scalar callback invoked for every candidate binding can dominate runtime even if graph matching itself is efficient. Custom functions may also have side effects, while SPARQL itself offers no general rollback mechanism for those external effects.

Where a function can be expressed through standard SPARQL operators, native execution generally avoids this callback overhead. Where functionality requires external libraries or domain-specific computation, Python extension functions provide a more expressive alternative.

Source: `https://pyoxigraph.readthedocs.io/en/stable/store.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+1



### 4.5 SPARQL Update as a graph transformation language

`Store.update()` supports the SPARQL 1.1 Update family:

- `INSERT DATA` and `DELETE DATA`.
- `DELETE/INSERT ... WHERE` for transformations driven by graph-pattern matching.
- Graph lifecycle operations such as `CREATE`, `CLEAR`, and `DROP`.
- Graph transfer operations such as `COPY`, `MOVE`, and `ADD`.
- `LOAD` for importing RDF resources.

`DELETE/INSERT ... WHERE` can express multi-relationship transformations using the same declarative matching engine as ordinary graph queries.

This provides a native alternative to implementing graph matching in Python, collecting rows, then separately applying each mutation. The complete update is documented as transactional.

Two boundaries deserve attention. First, a SPARQL update's atomicity concerns database changes, not arbitrary effects produced by Python callbacks or external services. Second, `LOAD` and `SERVICE` can involve external resources; their use with untrusted queries or remote IRIs requires appropriate network and resource controls.

### 4.6 SPARQL 1.2 and RDF 1.2

Version 0.5 introduced preliminary support for the W3C RDF 1.2 and SPARQL 1.2 working drafts, enabled by default in the Python bindings.

Consequential functionality includes RDF triple terms and newer RDF semantics. This must be distinguished from the established SPARQL 1.1 baseline.

The earlier experimental RDF-star feature was replaced by RDF 1.2 support, with syntax and behavior changes. Applications relying on RDF-star or quoted-triple syntax from older releases should consult the migration guide rather than assuming direct compatibility.

The 0.5 migration documentation and current model type signatures are not perfectly consistent about the permitted placement of embedded triple terms. Where that distinction matters, the exact syntax and query behavior warrant verification against the target release.

Sources:

`https://github.com/oxigraph/oxigraph/releases/tag/v0.5.0`

`https://pyoxigraph.readthedocs.io/en/stable/migration.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 5. SPARQL result types and interoperability

PyOxigraph exposes three distinct result families.

| Query                    | Result object    | Native interaction                         |
| ------------------------ | ---------------- | ------------------------------------------ |
| `SELECT`                 | `QuerySolutions` | Iterate over `QuerySolution` rows          |
| `ASK`                    | `QueryBoolean`   | Convert to `bool`, serialize if needed     |
| `CONSTRUCT` / `DESCRIBE` | `QueryTriples`   | Iterate over RDF triples or serialize them |

### 5.1 Streaming solution iteration

`QuerySolutions` is an iterator rather than a complete Python list. Its `variables` property gives the ordered projected variables.

Each `QuerySolution` can be accessed by variable name, `Variable` object, or positional index, and supports tuple unpacking. Bindings retain RDF term objects rather than being automatically flattened to Python primitives.

This allows applications to process query results incrementally. It does not imply that all query operators execute without buffering: joins, sorting, aggregation, and distinctness may require significant internal state depending on the plan.

### 5.2 Result serialization

`QuerySolutions.serialize()` and `QueryBoolean.serialize()` support:

- SPARQL Results XML.
- SPARQL Results JSON.
- CSV.
- TSV.

`QueryTriples.serialize()` instead targets RDF graph serializations, because constructed triples are RDF data, not tabular variable bindings.

The inverse utility `parse_query_results()` supports XML, JSON, and TSV. CSV is supported for writing query results, but not for parsing them through this function. This asymmetry is important when designing round-trip exchanges.

`QueryResultsFormat` also supports format recognition by filename extension and media type, with metadata such as canonical media types and format IRIs. These are useful for interoperability with HTTP-based SPARQL services and result files, even though PyOxigraph itself is an embedded Python library.

Source: `https://pyoxigraph.readthedocs.io/en/stable/sparql.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+1



## 6. RDF parsing, serialization, and high-volume ingestion

### 6.1 Supported RDF formats

PyOxigraph's standalone RDF I/O and store import/export interfaces support the following syntax families.

| RDF format  | Primary characteristics                                           |
| ----------- | ----------------------------------------------------------------- |
| `N_TRIPLES` | Line-oriented triple representation                               |
| `N_QUADS`   | Line-oriented quad representation with graph names                |
| `TURTLE`    | Compact, prefix-oriented triple representation                    |
| `TRIG`      | Turtle-family syntax with named graph support                     |
| `JSON_LD`   | JSON-oriented representation of linked data                       |
| `RDF_XML`   | XML-based RDF representation                                      |
| `N3`        | Notation3 syntax, including constructs beyond conventional Turtle |

Support for N3 as a serialization format should not be interpreted as a built-in N3 rules or logical-inference engine.

The distinction between graph formats and dataset formats is essential. Triple-only serialization formats cannot directly preserve a complete dataset containing multiple named graphs. When exporting from a `Store`, graph-only formats require an explicit `from_graph` selection. Dataset-capable formats can preserve quad graph membership.

### 6.2 Standalone parser and serializer

`parse()` reads RDF from strings, byte buffers, file-like objects, or paths. It returns an iterable `QuadParser` without requiring a database.

Key controls include:

- `format`: explicit syntax; otherwise inferred from a filename extension where available.
- `base_iri`: relative-IRI resolution.
- `without_named_graphs`: reject named graph contents.
- `rename_blank_nodes`: assign new blank-node identifiers to avoid collisions when combining datasets.
- `lenient`: relax selected parsing checks, including IRI validation.

`serialize()` writes RDF terms and statements to an output destination or returns encoded bytes. It supports syntax-relevant prefixes and base-IRI configuration.

Because these facilities are independent of `Store`, PyOxigraph can also act as a native-speed RDF ingestion, conversion, and serialization library without owning persistent graph state.

Blank-node renaming is especially important in ingestion pipelines. Blank-node identifiers are scoped to an RDF dataset or serialization context. Combining independently produced documents without handling their blank-node scopes can unintentionally equate otherwise distinct anonymous resources.

`lenient=True` is a performance and validation tradeoff, not a general repair facility. It may admit invalid data and should not be interpreted as ensuring standardized output.

### 6.3 Loading: transactional versus bulk-oriented paths

PyOxigraph deliberately separates small/atomic insertion methods from large-data ingestion paths.

| Method                     | Workload characteristics    | Key distinction                                            |
| -------------------------- | --------------------------- | ---------------------------------------------------------- |
| `Store.add(quad)`          | Individual statements       | Simple incremental mutation                                |
| `Store.extend(quads)`      | Small or moderate batches   | Transactional; gathers the input batch                     |
| `Store.bulk_extend(quads)` | Large quad streams          | Avoids holding all quads in memory; writes storage files   |
| `Store.load(...)`          | Small or moderate RDF files | Transactional; full input held in memory                   |
| `Store.bulk_load(...)`     | Large RDF files             | Stream-oriented ingestion designed for low memory overhead |

Bulk-oriented operations use storage-file generation rather than repeated fine-grained insertions. This changes memory pressure, file creation, and the amortization of indexing work.

A crucial nuance is that “bulk” does not mean “nontransactional.” The underlying engine's modern bulk-load path uses commit-based publication; in particular, the v0.5 series changed loader semantics from older releases. Nevertheless, the Python API's explicit guarantees and memory behavior should be considered separately for each method.

`bulk_load()` has `to_graph` for placing triple-format input into a specified graph. `Store.dump()` has the complementary `from_graph` control for exporting a single graph in triple-only formats.

These native paths may eliminate the need for custom batching, repeated string parsing, or Python-managed insertion loops.

Sources:

`https://pyoxigraph.readthedocs.io/en/stable/io.html`

`https://pyoxigraph.readthedocs.io/en/stable/store.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+3



## 7. Companion libraries and ecosystem integration

### 7.1 `oxrdflib`: RDFLib compatibility backed by Oxigraph

`oxrdflib` is the most directly relevant Python companion package. It exposes an RDFLib-compatible storage backend named `"Oxigraph"` and registers PyOxigraph-based parsers and serializers as RDFLib plugins.

This allows RDFLib's graph abstraction to use Oxigraph's underlying storage and query engine.

| Capability                   | Integration behavior                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| RDFLib `Graph` and `Dataset` | Can use the `"Oxigraph"` storage backend                                                     |
| Persistent storage           | RDFLib graph/dataset `open()` connects to the underlying store directory                     |
| Existing PyOxigraph store    | Can be injected through `oxrdflib.OxigraphStore`                                             |
| SPARQL execution             | Delegated to PyOxigraph for supported graph operations                                       |
| Parsing and serialization    | Additional plugins using `ox-` identifiers                                                   |
| Direct parser-to-store path  | Can bypass Python-level term conversions when Oxigraph parsers and storage are used together |

The last capability is particularly significant. Combining an Oxigraph parser with an Oxigraph store can avoid routing each parsed RDF term through ordinary RDFLib Python objects. This is a native integration optimization rather than merely substituting a storage engine.

However, the compatibility layer is not behaviorally identical to RDFLib's default store:

- RDFLib contexts are supported, but RDFLib formulas are not.
- RDFLib's explicit transaction interface is not implemented by the adapter.
- SPARQL updates on certain RDFLib graph classes can still use RDFLib's evaluator because of context-management constraints.
- Namespace bindings established through RDFLib's `Graph.bind()` are not persisted to the database.
- There are differences in parser behavior, including handling of relative IRIs.

`oxrdflib` provides broader RDFLib ecosystem compatibility. Direct PyOxigraph use provides a smaller abstraction surface and more explicit control over native Oxigraph functionality.

Source: `https://github.com/oxigraph/oxrdflib`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.2 Oxigraph server and CLI

The wider Oxigraph project also distributes a standalone command-line application capable of managing RDF data and exposing HTTP interfaces implementing the SPARQL Protocol and SPARQL Graph Store Protocol.

These network-service capabilities belong to the Oxigraph CLI/server distribution, not to PyOxigraph's documented Python `Store` API.

The distinction permits two different deployment models:

- Embedded execution through PyOxigraph, with Python controlling the database lifecycle and queries.
- Separate server execution, with clients communicating through standards-based SPARQL HTTP protocols.

The embedded model avoids an additional service boundary. The server model offers standardized remote access but introduces service configuration, request handling, and network concerns.

Source: `https://github.com/oxigraph/oxigraph`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.3 Underlying Rust components

Oxigraph is modular internally. The relevant Rust crates include:

| Rust crate     | Responsibility                                  |
| -------------- | ----------------------------------------------- |
| `oxrdf`        | RDF terms and fundamental data structures       |
| `oxrdfio`      | Unified RDF parsing and serialization interface |
| `oxttl`        | Turtle, TriG, N-Triples, N-Quads, and N3        |
| `oxrdfxml`     | RDF/XML                                         |
| `oxjsonld`     | JSON-LD                                         |
| `spargebra`    | SPARQL syntax parsing and algebra               |
| `spareval`     | SPARQL evaluation                               |
| `sparopt`      | SPARQL optimization                             |
| `sparesults`   | SPARQL result parsers and serializers           |
| `oxsdatatypes` | XML Schema datatype functionality               |
| `spargeo`      | Partial GeoSPARQL functionality                 |

These components explain why PyOxigraph combines several capabilities that are often separate Python dependencies.

However, the existence of a Rust crate does not establish that its entire API is accessible from Python. In particular, `spargeo` is a separate, partial implementation of GeoSPARQL, not evidence that installing PyOxigraph automatically exposes a complete geospatial query engine.

Source: `https://github.com/oxigraph/oxigraph`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.4 Interoperability with relational and columnar systems

PyOxigraph can complement relational and analytical systems, but its documented Python interface is RDF-term-oriented rather than Arrow- or DataFrame-native.

Integration typically crosses one of three boundaries:

| Boundary                         | Mechanism                                                | Consequence                                                                           |
| -------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| RDF quads to application objects | Iterate over `Quad` or `QuerySolution`                   | Preserves RDF semantics; incurs per-object conversion overhead                        |
| SPARQL `SELECT` to tabular data  | Result bindings or CSV/TSV export                        | Useful for analytical consumption; requires explicit term and datatype interpretation |
| External tables to RDF           | Construct quads or produce a supported RDF serialization | Requires mapping rows, column names, and identifiers into RDF entities and predicates |

This distinction is important for systems that use both relational and graph representations. PyOxigraph offers graph-oriented query semantics and named-graph organization, while SQL and Arrow-oriented engines offer different strengths in typed columnar computation, vectorized numerical operations, and tabular interchange.

No native zero-copy Arrow interface or DataFusion execution integration is documented in the PyOxigraph 0.5.13 public API. Such interoperability therefore remains an integration concern rather than an inherent library capability.

## 8. Consequential semantics, performance mechanisms, and limitations

### 8.1 RDF semantics are not property-graph semantics

RDF models facts as globally identified predicates connecting RDF terms. This differs from labeled-property graph systems, in which nodes and edges commonly have directly attached mutable properties.

The distinction affects representation choices:

- A relationship with attributes may require a separately identified relationship resource, reification, or RDF 1.2 triple terms.
- Predicates are IRIs rather than fixed columns or informal edge labels.
- Repeated relationships are handled according to RDF graph-set semantics, not SQL bag semantics.
- Literals carry RDF datatypes and language metadata, not only native Python scalar values.
- Blank nodes represent existential or anonymous identity, not portable globally stable identifiers.

PyOxigraph's support for RDF terms and SPARQL is valuable when these semantics align with the data model. It should not be treated as a drop-in substitute for a Cypher/Gremlin property graph without a deliberate representation mapping.

### 8.2 Storage and indexing versus query optimization

The engine benefits from indexed quad storage and native Rust execution. But efficient indexed lookup does not automatically imply that every complex SPARQL expression has an efficient execution plan.

Query costs may be driven by:

- Join ordering and intermediate result cardinality.
- Selectivity of predicates and graph restrictions.
- `OPTIONAL` and anti-join evaluation.
- Variable-length property paths.
- Sorting, grouping, and duplicate elimination.
- Python callback frequency.
- External `SERVICE` latency.

The October 22, 2026 v0.5.13 release specifically improved join cost estimates and `OPTIONAL` planning to avoid quadratic scaling for certain foreign-key-like joins, and corrected binding propagation involving `LATERAL` subqueries.

That is useful evidence of ongoing optimizer development, but not a general benchmark-based performance guarantee.

Source: `https://github.com/oxigraph/oxigraph/releases/tag/v0.5.13`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.3 Python–Rust boundary costs

PyOxigraph moves substantial graph operations into Rust, reducing Python interpreter involvement in parsing, storage, and query execution.

The boundary remains relevant in three cases:

High-volume result iteration. Each row or quad exposed as a Python object incurs conversion and allocation overhead. A query producing millions of results may become Python-consumption-bound even when execution within Oxigraph is efficient.

Python-defined SPARQL functions. Custom functions or aggregates execute user-defined Python behavior. Their invocation cost and interactions with Python runtime concurrency can dominate expression-heavy queries.

Python-driven individual insertion. Repeatedly calling `Store.add()` introduces substantially more Python boundary crossings than using batch or bulk-oriented methods.

The tagged Python bindings demonstrate native operations that release Python's interpreter attachment during engine execution. That is beneficial, but it does not make every graph operation parallel, eliminate RocksDB synchronization, or guarantee that Python callbacks can run without interpreter coordination.

Source: `https://github.com/oxigraph/oxigraph/tree/v0.5.13/python`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 8.4 Important correctness and operational boundaries

| Concern                      | Documented behavior or implication                                                                                          |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Concurrency isolation        | Repeatable read; not a universal serializability guarantee                                                                  |
| Multi-operation transactions | Explicitly atomic SPARQL updates and selected batch methods; no documented Python transaction context object                |
| Unbound variables            | SPARQL bindings are partial; applications must not assume every projected variable has a value                              |
| Statement duplication        | RDF graphs have set semantics; duplicate quads are not independent records                                                  |
| Blank-node identity          | Identifier strings are not reliable global identifiers across unrelated RDF sources                                         |
| Graph provenance             | Named graphs preserve membership, but do not establish trust or authenticated provenance                                    |
| Canonicalization             | Potentially expensive on symmetric blank-node structures; not inherently incremental                                        |
| Persistent database format   | Physical storage compatibility is separate from portable RDF serialization                                                  |
| Read-only access             | Opening a read-only store while a different process writes to the same database is documented as undefined behavior         |
| Validation                   | RDF parsing checks syntax and term constraints; it does not automatically enforce domain schemas                            |
| Reasoning                    | RDF/RDFS/OWL inference and SHACL validation are not general native PyOxigraph store capabilities documented in this release |

Source: `https://pyoxigraph.readthedocs.io/en/stable/store.html` and `https://pyoxigraph.readthedocs.io/en/stable/model.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyoxigraph.readthedocs.io\&sz=32)

pyoxigraph 0.5.13 documentation+2



### 8.5 Canonicalization is separate from serialization

A subtle distinction is worth preserving.

`Dataset.canonicalize()` addresses RDF graph equivalence under blank-node renaming. RDF serialization addresses the production of syntactically valid encoded statements.

Even when a serializer offers a canonical encoding of individual terms or statements, that does not necessarily mean it has computed the canonical identity of the complete RDF dataset.

For reproducible graph digests, signatures, and comparison across independently assigned blank-node identifiers, the dataset-level canonicalization algorithm is the relevant mechanism.

## 9. Selecting between overlapping native capabilities

The most important PyOxigraph design choices are not simply which API calls exist, but which semantics and execution guarantees each one supplies.

| Decision                                         | Prefer the first option when…                                              | Prefer the alternative when…                                                       |
| ------------------------------------------------ | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `Dataset` versus `Store`                         | In-memory manipulation, set operations, or canonicalization are sufficient | SPARQL execution, persistence, graph management, or database isolation is required |
| `quads_for_pattern` versus SPARQL                | A direct known-term quad lookup is sufficient                              | Joins, aggregation, paths, graph transformations, or declarative logic are needed  |
| `extend` versus `bulk_extend`                    | Moderate atomic batches and simple mutation semantics matter               | Input is very large and lower-memory ingestion is important                        |
| `load` versus `bulk_load`                        | Atomic file loading with bounded input sizes is appropriate                | Large serialized datasets need a bulk-oriented loading path                        |
| `Store.dump` versus `Store.backup`               | Portability and RDF exchange matter                                        | A physical copy of the same database implementation is wanted                      |
| `RdfFormat` versus `QueryResultsFormat`          | Transferring RDF statements or datasets                                    | Transferring SPARQL bindings or boolean answers                                    |
| Direct PyOxigraph versus `oxrdflib`              | Native API control and lower abstraction overhead matter                   | Compatibility with existing RDFLib APIs and plugins is valuable                    |
| Named graph selection versus union default graph | Graph membership should constrain query results                            | Default-pattern matching should operate over a combined dataset                    |

The architecture-level opportunity is to combine RDF identity, indexed storage, declarative SPARQL, and native serialization rather than maintaining separate custom representations and transformation engines.

Whether that is simpler or more efficient depends on the workload. Large-scale relational aggregations, numerical computation, shape validation, and graph analytics may still belong in complementary engines.

## 10. Version, packaging, and maturity

Target release

0.5.13

Release date

October 22, 2026

Minimum Python

3.9

Implementation

Rust / PyO3

Persistence engine

RocksDB

License

MIT OR Apache-2.0

The package is available from PyPI and conda-forge, with prebuilt wheels for multiple Python versions and platforms.

Installation is through the standard package name `pyoxigraph`, for example `uv add pyoxigraph` or `pip install pyoxigraph`.

Upstream currently classifies the package as Alpha on PyPI and describes Oxigraph as still under substantial development. That should not be interpreted as the absence of useful deployed functionality, but it does mean that database-format compatibility, evolving standards support, and version-sensitive behavior deserve attention.

The v0.5 line also represents a meaningful standards transition because RDF 1.2 and SPARQL 1.2 working-draft capabilities entered the Python distribution.

Sources: `https://pypi.org/project/pyoxigraph/` and `https://github.com/oxigraph/oxigraph/releases/tag/v0.5.0`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 11. Primary-source reference map

| Subject                                                     | Source                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------ |
| Complete Python RDF term model, `Dataset`, canonicalization | `https://pyoxigraph.readthedocs.io/en/stable/model.html`     |
| Store API, querying, updates, bulk operations, backup       | `https://pyoxigraph.readthedocs.io/en/stable/store.html`     |
| RDF parsing, serialization, format metadata                 | `https://pyoxigraph.readthedocs.io/en/stable/io.html`        |
| SPARQL result objects and query-result formats              | `https://pyoxigraph.readthedocs.io/en/stable/sparql.html`    |
| Python migration and compatibility differences              | `https://pyoxigraph.readthedocs.io/en/stable/migration.html` |
| Current release and wheel metadata                          | `https://pypi.org/project/pyoxigraph/`                       |
| Oxigraph source, architectural components, CLI              | `https://github.com/oxigraph/oxigraph`                       |
| Python binding implementation at v0.5.13                    | `https://github.com/oxigraph/oxigraph/tree/v0.5.13/python`   |
| v0.5.13 SPARQL optimizer changes                            | `https://github.com/oxigraph/oxigraph/releases/tag/v0.5.13`  |
| v0.5.0 RDF/SPARQL 1.2 transition                            | `https://github.com/oxigraph/oxigraph/releases/tag/v0.5.0`   |
| RDFLib integration                                          | `https://github.com/oxigraph/oxrdflib`                       |
| Oxigraph architecture notes                                 | `https://github.com/oxigraph/oxigraph/wiki/Architecture`     |

Overall capability assessment: PyOxigraph is particularly distinctive for embedding a complete RDF/SPARQL database engine into Python while retaining low-level term manipulation, graph-scoped storage, native parsers and serializers, canonicalization, and custom query functions. Its most consequential boundaries are the differences between RDF and property-graph semantics, Python and Rust execution surfaces, draft and stable standards, and native graph querying versus external validation, reasoning, and analytical systems