# Oaklib (Ontology Access Kit) — Python Library Capability Reference

Target release: 0.7.4, published August 3, 2026\
Research date: October 29, 2026\
Package: `oaklib`\
Maintainer: INCATools\
License: Apache-2.0

Primary sources:

- Project repository: `https://github.com/INCATools/ontology-access-kit`
- Documentation: `https://incatools.github.io/ontology-access-kit/`
- Package releases: `https://pypi.org/project/oaklib/`
- Architecture: `https://incatools.github.io/ontology-access-kit/packages/architecture.html`

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1

## 1. Architectural orientation

Oaklib provides a unified, extensible interface for accessing, querying, analyzing, transforming, and managing biomedical and other structured ontologies. Its principal value is not a new ontology storage format or reasoning engine. It is an abstraction layer that makes substantially different ontology representations and services accessible through a common set of Python interfaces and the `runoak` command-line tool.

Its conceptual architecture has four layers:

1. Ontology interfaces: Contracts for entity lookup, graph navigation, search, mappings, logical axioms, validation, annotation, similarity, enrichment, editing, and other operations.
2. Adapters: Implementations backed by local ontology files, SQL databases, RDF stores, remote ontology services, or specialized analysis systems.
3. Semantic models: Shared representations for ontology entities, identifiers, relationships, mappings, annotations, changes, and graph structures.
4. Workflows and extensions: CLI expressions, extraction and conversion utilities, ontology quality checks, terminology matching, and plugins.

The key architectural distinction is that an interface being defined does not mean every adapter implements it fully or with identical semantics. Certain operations depend on capabilities of an underlying engine, precomputed database, remote service, or companion package. Some methods have generic fallback implementations; others are unavailable or considerably more expensive for particular backends.

This separation allows an application to retain a relatively stable ontology-facing API while choosing different backends for different performance, fidelity, or operational requirements. It does not make those backends semantically interchangeable.

Sources: `https://incatools.github.io/ontology-access-kit/packages/architecture.html` and `https://incatools.github.io/ontology-access-kit/packages/interfaces/index.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+1



## 2. Data sources, adapters, and execution boundaries

Oaklib exposes a primary factory, `get_adapter(...)`, which resolves a source descriptor into an implementation. Descriptors can identify local files, cached ontology distributions, databases, or named remote services. Many workflows can therefore use the same operation against different sources without embedding format-specific parsing or service-specific HTTP handling.

The most consequential backend families are:

| Backend                              | Typical selector                              | Capabilities and distinctions                                                                                                        |
| ------------------------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Pronto / OBO                         | `pronto:path.obo`                             | Local OBO loading, metadata, relationships, aliases, traversal, and supported mutations; built on Pronto/fastobo.                    |
| Semantic SQL / SQLite                | `sqlite:path.db`, `sqlite:obo:go`             | SQL-backed querying, indexed statements and edges, precomputed entailed relationships, and access to Semantic-SQL distributions.     |
| OWL / py-horned-owl                  | `owl:path.owl`                                | Access to native OWL class expressions and axioms, retaining logical structures that a simplified edge model cannot fully represent. |
| OBO Graphs                           | OBO Graph JSON source                         | Graph-oriented interchange, node/edge operations, logical definitions, and subgraph extraction.                                      |
| RDF / SPARQL                         | `sparql:...`                                  | Queries against RDF graphs and SPARQL endpoints; behavior depends on graph conventions and service capabilities.                     |
| Ubergraph                            | `ubergraph:`, `ubergraph:uberon`              | Specialized SPARQL access to multiple ontologies, including precomputed relationship closures and information-content data.          |
| OLS / BioPortal                      | `ols:hp`, `bioportal:...`                     | Remote ontology discovery, terminology lookup, search, mappings, and metadata, subject to endpoint support.                          |
| Gilda / PantherDB / related services | Service-specific                              | Specialized entity grounding, associations, enrichment, or mappings rather than comprehensive ontology editing.                      |
| Aggregator                           | Python `AggregatorImplementation` or CLI `-a` | Federates calls to multiple adapters and combines their results.                                                                     |

Source: `https://incatools.github.io/ontology-access-kit/packages/implementations/index.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+1



### 2.1 Semantic SQL is more than ontology storage

Oaklib's SQLite implementation uses the companion Semantic-SQL (`semsql`) representation, which layers relational views over RDF-level statements. The representation distinguishes:

- Statements: Source-level RDF triples.
- Edges: Ontologically meaningful relationship edges, including projections of more complex axioms.
- Entailed edges: Derived relationships materialized for efficient graph and entailment-aware queries.

This distinction matters because an OWL existential restriction can require several source triples while representing one useful relationship in a graph view. Accessing the right derived representation can eliminate repeated parsing and traversal, while preserving a route back to source-level statements when needed.

The documented SQL implementation targets SQLite; its API documentation identifies PostgreSQL support as planned rather than released. The SQLAlchemy model provides an additional escape hatch for complex, backend-specific queries, but that is not a guarantee that all SQL dialects are usable.

Source: `https://incatools.github.io/ontology-access-kit/packages/implementations/sqldb.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 2.2 Local versus remote adapters

Local file adapters concentrate loading and representation costs at initialization, after which many operations can execute without network requests. Pronto's fastobo-based parsing is relatively strict, so some nonconforming OBO files require the simpler OBO adapter or prior conversion.

Remote adapters avoid local ontology preparation and can access centrally maintained or integrated knowledge, but introduce latency, API limits, pagination, throttling, and endpoint-specific semantics. Ubergraph is explicitly optimized to combine work into larger SPARQL queries rather than repeated individual requests.

Federation through `AggregatorImplementation` can combine search results across ontologies—for example, searching two independently loaded vocabularies—without first merging their source files. Federation does not automatically establish consistent namespaces, resolve contradictory definitions, or supply cross-ontology equivalences.

Sources: `https://incatools.github.io/ontology-access-kit/packages/implementations/pronto.html`, `https://incatools.github.io/ontology-access-kit/packages/implementations/ubergraph.html`, and `https://incatools.github.io/ontology-access-kit/packages/implementations/aggregator.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+2



## 3. Core ontology model and metadata

Oaklib primarily identifies entities by CURIEs, such as `GO:0005634`, rather than requiring callers to manipulate raw IRIs throughout their application. It supports CURIE/URI conversion, configurable prefix maps, ontology identity and versions, and conventional entity properties.

The `BasicOntologyInterface` covers a substantial semantic surface:

| Capability                | Representative operations                                               | Important distinction                                                            |
| ------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Entity identity           | `entities`, `owl_type`, `defined_by`, `curie_to_uri`, `uri_to_curie`    | Existence, type, namespace, and identity are separate properties.                |
| Human-readable metadata   | `label`, `labels`, `definition`, `comments`, aliases                    | A primary label is not the same as a synonym or a globally unique identifier.    |
| Ontology organization     | `roots`, `leafs`, `singletons`, subsets, categories                     | Roots and leaves depend on the graph relation and representation being examined. |
| Relationship access       | `relationships`, incoming/outgoing relationships, relationship metadata | Directly represented relationships are not necessarily entailed relationships.   |
| Deprecation and migration | `obsoletes`, `obsoletes_migration_relationships`, dangling terms        | Obsolete, merged, replaced, and missing identifiers require different handling.  |
| Metadata and persistence  | Entity metadata, `create_entity`, `delete_entity`, `save`, `clone`      | Reading and editing support depends on the backend.                              |

Metadata normalization is an architectural feature. Oaklib can map differing ontology conventions—such as OBO-style definition properties, SKOS labels, and other annotation vocabularies—into common accessors through ontology metadata mapping. This reduces format-dependent branches in consuming systems, but normalization can obscure source distinctions unless the original predicates and annotations are retained.

Synonyms are typed information, not just alternative strings. Ontologies may distinguish exact, broad, narrow, and related synonyms. The distinction matters for text recognition, semantic alignment, and whether substituting one label for another preserves meaning.

Obsoletion is not deletion. Obsolete terms can remain identifiable, have replacements or suggestions for consideration, and possess alternate IDs associated with merging. An `alt_id` often preserves identifier resolution without preserving the old term's independent metadata or semantics.

Sources: `https://incatools.github.io/ontology-access-kit/guide/curies-and-uris.html`, `https://incatools.github.io/ontology-access-kit/guide/primary-labels.html`, `https://incatools.github.io/ontology-access-kit/guide/aliases.html`, and `https://incatools.github.io/ontology-access-kit/guide/obsoletion.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+3



## 4. Search, term selection, and declarative querying

### 4.1 Search is configurable by both syntax and semantic field

`SearchInterface` separates a query's textual syntax from the ontology metadata fields being examined.

`basic_search` and `multiterm_search` support configurations for exact, partial, prefix, and regular-expression matching. `SearchConfiguration` can restrict matching to labels, aliases, mapped identifiers, or other supported fields.

A particularly useful capability is searching mapping identifiers as an index into the ontology: a known external CURIE can resolve to terms carrying that cross-reference, without requiring a separate mapping pipeline.

Search results should nevertheless be understood as candidate identification, not semantic validation. Exact label equality does not prove concept equivalence; remote ranking, regular-expression support, and search-field coverage can vary by adapter.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/search.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 4.2 The OAK Expression Language is a compositional term-set query language

The `runoak` CLI includes a domain-specific expression language that can select ontology entities and feed the resulting set into many different commands. This is substantially more expressive than passing explicit term IDs.

| Expression family        | Representative syntax                               | Capability                                                       |
| ------------------------ | --------------------------------------------------- | ---------------------------------------------------------------- |
| Lexical selection        | `t=`, `t^`, `t~`, `t/`                              | Exact, prefix, substring, or regex search                        |
| Graph expansion          | `.anc`, `.desc`, `.parent`, `.child`, `.sib`        | Select relatives using configurable predicates                   |
| Graph reduction          | `.mrca`, `.nr`                                      | Find most recent common ancestors or eliminate redundant members |
| Set algebra              | `.and`, `.or`, `.not`                               | Intersection, union, subtraction                                 |
| Attribute filtering      | `.in`, `.is_obsolete`, `.non_obsolete`, `.dangling` | Subset membership and metadata-state restrictions                |
| Source/query integration | `.idfile`, `.query`                                 | File-based term sets or underlying SQL/SPARQL queries            |
| Sampling                 | `.rand`, `.sample`                                  | Random entities or a sample of an existing selection             |

Operators such as `.anc//p=i,p` parameterize relationship types; brackets support nested selections. The expression processor evaluates set operations in sequence, with prefix operators binding more tightly than infix operators. This makes operator order and grouping consequential, particularly for negation.

Architectural significance: a complex ontology selection can be represented as a concise, inspectable query expression and reused for definitions, mappings, visualization, enrichment, or other operations. This can remove repeated, task-specific Python set-processing logic. Its power remains constrained by the selected adapter and its implementation of the underlying operations.

Source: `https://incatools.github.io/ontology-access-kit/howtos/use-oak-expression-language.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 5. Graph navigation, entailment, and OWL semantics

This is one of Oaklib's most important capability families—and a major source of potential semantic errors if its operations are treated as ordinary graph traversal.

### 5.1 Asserted edges, graph projection, and entailed relationships are different

Oaklib distinguishes three relevant representations:

| Representation         | Meaning                                                              | Typical access                                       |
| ---------------------- | -------------------------------------------------------------------- | ---------------------------------------------------- |
| Asserted relationships | Relationships explicitly represented or projected from source axioms | `relationships`                                      |
| Graph reachability     | Nodes connected by paths over selected predicates                    | `ancestors`, `descendants`, `paths` using `HOP`      |
| Entailed relationships | Semantically derived relationships under supported inference rules   | `ENTAILMENT`, relation-graph queries, entailed edges |

A straightforward OWL axiom such as A SubClassOf part-of some B can be projected to the edge `A —part_of→ B`. This projection is useful for analysis but is not a lossless representation of the original logical axiom.

`HOP` versus `ENTAILMENT` is a fundamental choice.

- `HOP` follows graph connections, optionally restricting predicates. It can discover paths even when no meaningful named relation between endpoints has been established.
- `ENTAILMENT` relies on derived relationships. Property hierarchies, transitivity, and property chains can yield relationships not obtainable by following only edges with the requested predicate.
- `ENTAILMENT` support is primarily supplied through precomputed Relation Graph data in the Semantic-SQL and Ubergraph backends, rather than a universally available interactive OWL reasoner.

For example, given `A has_part B`, `B part_of C`, and a property-chain axiom defining the composition as `overlaps`, the entailed relation `A overlaps C` can be recovered without treating every mixed-predicate path as a meaningful relation.

Conversely, blindly following all ontology predicates can produce misleading “ancestors” across relationships such as location, characteristic, development, or adjacency. The default reflexive behavior of ancestor operations also means a term can occur in its own ancestor result.

Source: `https://incatools.github.io/ontology-access-kit/guide/relationships-and-graphs.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 5.2 OBO Graph interface: richer graph operations

`OboGraphInterface` exposes the OBO Graph data model rather than only flat relationship tuples. Its functionality includes:

Graph construction and extraction: `node`, `nodes`, `edges`, `direct_graph`, `ancestor_graph`, `descendant_graph`, `extract_graph`, and `as_obograph`.

Navigation and analysis: `ancestors`, `descendants`, `descendant_count`, `paths`, `chains`, and `non_redundant_entailed_relationships`.

Selective subgraph generation: `subgraph_from_traversal` with `TraversalConfiguration` permits distinct upward and downward traversal depths and relationship restrictions.

Logical structure: `logical_definitions` and `disjoint_class_expressions_axioms` retain selected constructs that cannot be adequately described by generic edges alone.

The `RelationGraphInterface` complements this with entailed incoming/outgoing relationships and relationship queries between selected entities.

These capabilities support ontology slicing, semantic neighborhood construction, dependency analysis, graph visualization, and reducing redundant relationship output. They also make it possible to avoid implementing independent traversal and closure machinery when the adapter already supplies suitable semantics.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/obograph.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib  documentation+1



### 5.3 Native OWL axiom inspection

`OwlInterface` operates closer to OWL's logical representation. In release 0.7.4, local OWL handling uses py-horned-owl, despite historical implementation naming that still refers to FunOWL.

Its significant operations include:

- Inspecting `SubClassOf`, equivalent-class, annotation-assertion, and disjointness axioms.
- Filtering axioms and determining the entities referenced by an axiom.
- Examining property characteristics, transitive properties, and simple subproperty-chain structures.
- Working with OWL class expressions rather than only their graph projections.

The distinction is consequential: graph projection may erase qualifiers, logical operators, quantifiers, annotations, or the distinction between axioms with superficially similar edge patterns.

Reasoning boundary: this access to OWL structures is not equivalent to a complete description-logic reasoner. Oaklib's documented approach relies primarily on preclassified ontologies, precomputed relation graphs, and optional integrations. Full consistency checking, classification, and unsatisfiable-class detection require a suitable reasoning backend; the `oakx-robot` plugin is an example of an external route.

Sources: `https://incatools.github.io/ontology-access-kit/packages/interfaces/owl.html` and `https://incatools.github.io/ontology-access-kit/faq/general.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+1



## 6. Ontology mappings, alignment, and identity normalization

Oaklib treats ontology mappings as a distinct semantic concern rather than merely another graph relationship.

### 6.1 Lightweight cross-references versus qualified SSSOM mappings

The basic interface exposes simple mapping identifiers and relationships. `MappingProviderInterface` provides richer mappings using SSSOM (Simple Standard for Sharing Ontological Mappings).

SSSOM records can distinguish subject, predicate, object, labels, sources, and mapping justification, thereby carrying information absent from a simple pair of identifiers.

Relevant methods include `sssom_mappings`, `get_transitive_mappings_by_curie`, `get_mapping_clusters`, `normalize`, and `create_normalization_map`.

Mapping predicates must retain their meaning. `skos:exactMatch`, `skos:broadMatch`, `skos:narrowMatch`, `owl:equivalentClass`, and OBO `hasDbXref` do not establish the same relationship. In particular, a cross-reference can be an uncommitted link rather than evidence of logical or conceptual equivalence. Transitive mapping or canonicalization operations need appropriately constrained predicate semantics to avoid collapsing distinct concepts.

Mappings are source-dependent. A mapping recorded in ontology A may be retrievable when querying either endpoint within A, yet entirely absent from ontology B. Query direction and the ontology that actually supplies the mapping are separate concerns.

Oaklib supports SSSOM representations and export; the standalone `sssom` Python package remains the more direct companion for independently managed SSSOM files and their specialized processing.

Sources: `https://incatools.github.io/ontology-access-kit/guide/mappings.html` and `https://incatools.github.io/ontology-access-kit/packages/interfaces/mapping-provider.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+1



### 6.2 Lexical alignment and mapping generation

The `runoak lexmatch` workflow compares ontology terms through labels and synonyms, optionally across separately supplied ontology sources. It builds a lexical index and can emit candidate matches as SSSOM mappings.

Advanced capabilities include lexical normalization, configurable matching rules, transformations, and rule-weighted confidence construction. The associated lexical-index and mapping-rules data models make these decisions more explicit than a single opaque string-similarity threshold.

This provides an intermediate option between exact string equality and embedding-driven alignment: a reproducible, domain-configurable lexical matching process with structured candidate output.

Its limitation is equally important: lexical matching can propose alignments but does not prove OWL equivalence, identity, or contextual substitutability.

Sources: `https://incatools.github.io/ontology-access-kit/datamodels/lexical-index/index.html`, `https://incatools.github.io/ontology-access-kit/datamodels/mapping-rules/index.html`, and `https://incatools.github.io/ontology-access-kit/cli.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+2



## 7. Text annotation, entity grounding, and lexical processing

`TextAnnotatorInterface` supports recognizing ontology concepts in unstructured text and structured documents, with operations such as `annotate_text`, `annotate_file`, and `annotate_tabular_file`.

The built-in lexical approach constructs a vocabulary from ontology labels and synonyms, applies matching/normalization rules, and produces structured annotations containing identified entities and, where applicable, text spans and offsets.

Its value extends beyond simple term recognition:

- Ontology-controlled grounding: recognized mentions resolve to ontology identifiers rather than remaining plain strings.
- Lexical rule reuse: synonym normalization and term-matching rules can be shared with lexical mapping workflows.
- Structured provenance: annotation results can distinguish the recognized text span, matched entity, and selected source or method.
- Alternative providers: adapters for Gilda, BioPortal annotation services, and LLM-assisted annotation expose other matching strategies, each with different evidence and predictability characteristics.

The built-in mechanism is most naturally understood as ontology-aware lexical matching, not comprehensive linguistic parsing or context-sensitive entity disambiguation. Homonyms, negation, complex phrasing, and overlapping candidates can require additional logic or specialized grounding services. An LLM-supported annotation is also not inherently deterministic.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/text-annotator.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 8. Curated associations and ontology-aware enrichment

### 8.1 Associations are distinct from ontology axioms

An ontology relationship generally describes a relationship between concepts or classes. A curated association records a statement connecting an entity—such as a gene, protein, disease, or specimen—to an ontology term, frequently accompanied by evidence, references, qualifiers, provenance, or negation.

`AssociationProviderInterface` can query and manipulate association sets using `associations`, `association_counts`, `associations_subjects`, `add_associations`, `map_associations`, and normalization operations.

Oaklib can parse several established association representations, including GAF, GPAD, HPO annotation files, KGX-style associations, and specialized association tables. Association data can be supplied independently of the ontology, allowing an ontology backend to provide hierarchy and labels while a separate file or service supplies annotations.

An important option is annotation closure: an association to a specific term can also be considered an association to selected ancestors. `object_closure_predicates` controls the relationships used for that propagation, and `add_closure_fields` can preserve closure-related information.

That propagation is not automatically valid for every predicate. In particular, ontology membership, gene annotation, causal relationships, and negated annotations should not be treated as interchangeable logical assertions.

Sources: `https://incatools.github.io/ontology-access-kit/guide/associations.html` and `https://incatools.github.io/ontology-access-kit/packages/interfaces/association-provider.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib  documentation+1



### 8.2 Enrichment integrates statistics with ontology structure

`ClassEnrichmentCalculationInterface` provides ontology-aware over-representation analysis through `enriched_classes` and related operations.

The essential mechanism combines a study set, background population, associations, and an ontology hierarchy:

1. Propagate annotations along selected ontology predicates.
2. Calculate over-representation, principally with a hypergeometric/Fisher-style framework.
3. Apply statistical significance treatment and optionally reduce redundant results through ontology relationships.

The advanced capabilities are the composition and controls rather than the underlying statistical test alone:

| Capability                      | Consequence                                                                                           |
| ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Configurable closure predicates | Determines which annotated descendants contribute to a broader class                                  |
| Custom background sets          | Makes the comparison population explicit                                                              |
| Redundancy filtering            | Limits closely related ancestor/descendant results                                                    |
| Pseudo-enrichment               | Treats ontology terms as self-associated when external associations are unavailable                   |
| Cross-ontology analysis         | Allows associations and target ontologies to be combined when identifiers and mappings are compatible |
| Graph visualization of results  | Makes significant terms inspectable in their hierarchical context                                     |

The background population, annotation completeness, predicate selection, evidence policy, and multiple-testing correction materially affect statistical interpretation. Pseudo-enrichment is a useful ontology-structure analysis, but it is not a substitute for evidence-based population enrichment.

Version-specific API caution: the online enrichment guide contains a Python illustration using `calculate_enrichment`; the tagged 0.7.4 interface defines `enriched_classes`. The tagged API should take precedence over that illustrative snippet.

Source: `https://incatools.github.io/ontology-access-kit/guide/enrichment.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 9. Semantic similarity and embedding boundaries

### 9.1 Classic ontology-based similarity

`SemanticSimilarityInterface` supports comparing ontology terms and term sets without requiring learned vector representations.

Core capabilities include:

Ancestor-set overlap: Jaccard similarity measures the overlap between reflexive ancestor sets. Results depend on the graph relations chosen.

Most recent common ancestors: `most_recent_common_ancestors`, common-ancestor operations, and setwise variants identify the most specific shared ontological generalizations. Multiple incomparable common ancestors may exist.

Information content (IC): `information_content_scores`, `get_information_content`, and associated operations estimate term specificity using a corpus. The corpus can be the ontology's descendant structure or externally observed associations.

Pairwise scoring: `pairwise_similarity` can combine common-ancestor information, Jaccard, Resnik-style IC, and related measures such as Phenodigm.

Profile comparison: `termset_pairwise_similarity` and `all_by_all_pairwise_similarity` compare term collections, including best-match-average aggregation across pairwise term scores.

The largest semantic distinction is between structural IC and annotation-derived IC. Structural IC reflects the hierarchy's distribution of descendants; annotation-derived IC reflects empirical use and annotation frequencies. They can produce substantially different scores for exactly the same two ontology terms. IC scores are consequently not universal constants attached to ontology identifiers.

### 9.2 Semsimian as an acceleration backend

Oaklib can use the separate Rust-based Semsimian library for semantic similarity through a specialized adapter, including the `semsimian:` selector.

This offers an alternative execution engine for similarity-intensive workloads while retaining the ontology-oriented calling model. The potential performance benefit comes from specialized indexing and implementation, not from changing the semantics of the underlying ontology. It should not be assumed to support every Oaklib operation or to produce identical scores without matching predicate sets, corpora, IC definitions, and algorithm configuration.

Sources: `https://incatools.github.io/ontology-access-kit/guide/similarity.html`, `https://incatools.github.io/ontology-access-kit/packages/interfaces/semantic-similarity.html`, and `https://github.com/INCATools/semsimian`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib  documentation+1



### 9.3 Important version discrepancy: the expanded embedding API is not in 0.7.4

The current rolling Oaklib documentation describes a significantly expanded `EmbeddingProviderInterface`, including NumPy embedding matrices, named learned embedding models, text embeddings, cosine/Jaccard comparisons, nearest-neighbor retrieval, and ontology-closure pseudo-embeddings.

However, the tagged v0.7.4 source does not contain that interface. The 0.7.4 `EmbeddingProviderInterface` defines only the abstract `entities_vectors` operation, with an `embedding_strategy` attribute. It does not expose the documented `entity_embeddings`, `nearest_entities`, `text_embedding`, or embedding similarity methods.

Accordingly, those advanced vector operations should be treated as documented development-line capabilities, not verified 0.7.4 functionality. The rolling docs alone are insufficient to establish which later release will contain them.

Sources:

- Released interface: `https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/embedding_provider_interface.py`
- Expanded rolling interface: `https://incatools.github.io/ontology-access-kit/packages/interfaces/embedding-provider.html`

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation

## 10. Ontology validation, quality control, and repair

`ValidatorInterface` unifies several distinct kinds of ontology validation. Its scope is broader than structural schema checking, although actual coverage depends on the selected adapter.

| Validation family    | Mechanisms                                                                    | Principal limitation                                         |
| -------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Metadata schema      | `validate`, configurable ontology metadata schema                             | Primarily implemented through the SQL backend                |
| Lexical quality      | `validate_synonyms`, duplicate and consistency checks                         | Cannot establish conceptual correctness from text alone      |
| Definitions          | `validate_definitions`, missing-definition checks, reference checks           | Content validity may require external domain evidence        |
| Mappings             | `validate_mappings`, mapped-term existence/obsoletion and mapping constraints | Other ontology sources must be accessible                    |
| Graph and references | `validate_relationships`, external reference lookup                           | Validation completeness depends on available representations |
| Logical consistency  | `is_coherent`, `unsatisfiable_classes`                                        | Requires a suitable external reasoning implementation        |
| Repair               | `repair`, including a `dry_run` option                                        | Available repairs are implementation- and rule-dependent     |

### 10.1 LinkML-based ontology metadata validation

The principal schema-validation pathway uses the Ontology Metadata Ontology (OMO) schema, represented using LinkML. It can express constraints such as metadata cardinality, required or recommended properties, and permitted value structures.

The `validate(configuration=...)` interface allows a different metadata schema to be supplied. This separates ontology content from the metadata quality contract used to check it.

The official documentation explicitly identifies the SQL adapter as the main implementation of this pathway. This should not be interpreted as universal LinkML or SHACL validation support across every adapter.

### 10.2 Semantic and evidence-based checks

Mapping, synonym, and definition validation can go beyond schema compliance:

- Checking whether externally referenced concepts still exist or have become obsolete.
- Detecting inconsistent synonyms or incompatible mapping cardinalities.
- Checking missing or malformed definitions.
- Evaluating definition wording or mappings against retrieved information with optional AI-assisted mechanisms.

These are different evidence classes. Deterministic property checks and ontology relationship checks can be reproducible; LLM judgments or checks against external publications introduce additional source, model, and evaluation dependencies.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/validator.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 11. Ontology editing, differences, and controlled change

### 11.1 KGCL-based changes

Oaklib integrates Knowledge Graph Change Language (KGCL) representations for describing edits to ontologies.

`DifferInterface` supports `diff`, `grouped_diff`, `diff_summary`, and other comparison operations, producing typed changes rather than only raw text differences. These can identify events such as entity renames, relationship changes, and modifications to ontology structure.

This is valuable because a change like “replace an identifier” or “obsolete a term” can have implications extending beyond a single triple or file line.

However, Oaklib does not guarantee that its diff identifies every OWL axiom-level difference. The upstream interface explicitly acknowledges implementation-specific coverage.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/differ.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 11.2 Patch application and expansion

`PatcherInterface` provides operations including:

| Operation                         | Capability                                                  |
| --------------------------------- | ----------------------------------------------------------- |
| `apply_patch`                     | Apply a typed KGCL change to a mutable ontology             |
| `expand_changes`, `expand_change` | Convert complex semantic changes into more elementary edits |
| `migrate_curies`                  | Rewire identifier usages according to an identifier mapping |
| `reverse_changes`, `undo`         | Derive or apply inverse operations where supported          |
| `save`                            | Persist changes through the adapter                         |
| `add_contributors`, `set_creator` | Associate contributor/creator metadata with changes         |

Complex changes can expand to multiple concrete operations. For example, an obsoletion may require label changes, metadata updates, and edge rewiring; a name-to-synonym operation can become a rename plus synonym creation.

This creates an opportunity for semantic editing workflows in which the requested operation is represented at the domain level and the adapter manages its lower-level consequences.

The boundaries are important: editing support is backend-dependent; reversing a change is not necessarily equivalent to reconstructing every piece of deleted source information; and `save` is not a universal transaction or atomic commit guarantee.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/patcher.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 11.3 Merging ontology representations

The less-prominent `MergeInterface` supports merging information from multiple ontology adapters into a target adapter.

Its tagged implementation distinguishes an OBO Graph-based merge, when all participants provide the relevant interface, from a simpler entity-and-relationship merge.

A consequential detail is that `MergeConfiguration.allow_lossy_merge` defaults to `True`. The simpler merge pathway explicitly rejects a request for guaranteed non-lossy behavior.

The merge mechanism therefore provides a useful consolidation abstraction, but not an automatic logical union with guaranteed preservation of arbitrary OWL axioms, ontology provenance, or consistency.

Tagged source: `https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/merge_interface.py`

## 12. Subsetting, extraction, conversion, and visualization

### 12.1 Subsetting beyond selecting a list of entities

`SubsetterInterface` addresses a problem distinct from ordinary filtering: producing a meaningful ontology fragment around a chosen set of terms.

Its capabilities include `extract_subset_ontology`, `gap_fill_relationships`, and related graph extraction operations.

The particularly useful mechanism is relationship gap filling. Given a set of retained terms, `gap_fill_relationships` uses entailed edges to reconstruct non-redundant relationships connecting them. This can preserve meaningful hierarchical connections even when intermediate ontology classes are excluded.

The documented implementation selects relevant entailed relationships and performs a per-predicate transitive reduction. That reduction is not guaranteed to eliminate every formally redundant edge.

Two availability conditions matter:

- `gap_fill_relationships` depends on precomputed relation-graph entailment and is documented for SQLite and Ubergraph.
- `extract_subset_ontology` is explicitly marked experimental.

Source: `https://incatools.github.io/ontology-access-kit/packages/interfaces/subsetting.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib  documentation



### 12.2 Conversion and export

Oaklib exposes `DumperInterface` and a set of converters centered on the OBO Graph data model.

Significant conversion targets include:

- OBO Format.
- OWL/RDF-oriented representations.
- FHIR `CodeSystem` JSON.
- Cytoscape Exchange (CX), through an OBO Graph converter.

The general CLI export mechanism is `runoak ... dump`, with output-type and output-file controls. Conversion utilities provide options for CURIE handling, label rendering, and canonical ordering where implemented.

FHIR conversion is particularly distinctive. It provides a route from an ontology graph into healthcare terminology structures, with configurable representation of identifiers, URI stems, and ontology relationships.

It is not semantically equivalent to round-tripping unrestricted OWL through FHIR: FHIR `CodeSystem` and OWL support different logical and representational constructs.

### 12.3 Visualization

Graph visualization through `runoak viz` and associated tooling allows selected ontology terms, ancestor neighborhoods, extracted subgraphs, and analysis results to be rendered as diagrams.

Oaklib uses companion visualization tools, notably OBOGraphViz and Graphviz, for actual graph layout and rendering. Thus ontology extraction and visual rendering are separable operations with different dependencies.

Source: `https://incatools.github.io/ontology-access-kit/packages/converters/index.html` and `https://incatools.github.io/ontology-access-kit/howtos/fhir-conversions.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib  documentation+1



## 13. Less-prominent advanced interfaces

The 0.7.4 source contains several valuable interfaces that are comparatively easy to overlook in the main conceptual guide.

### 13.1 Taxon constraint calculation

`TaxonConstraintInterface` supports ontology-based taxonomic constraints such as:

- `only_in_taxon`
- `never_in_taxon`
- `in_taxon`
- `present_in_taxon`

Its methods can propagate constraints from relevant ancestor terms, identify redundant constraints, calculate candidate presence constraints, and generate structured explanations and labels.

Representative methods include `get_term_with_taxon_constraints`, `get_terms_with_taxon_constraints`, `calculate_present_in_taxon_constraints`, and `get_direct_taxon_constraints`.

The released implementation explicitly uses graph-walking inference rather than complete logical reasoning. Its results therefore depend on the traversal predicates, ontology graph, available source constraints, and normalization of constraint predicates.

The associated datamodel preserves provenance distinctions such as asserted versus inferred constraints, intermediary terms, redundancy, and potential contradictions. This makes it substantially richer than a simple allowed-species lookup.

Sources:

`https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/taxon_constraint_interface.py`

`https://incatools.github.io/ontology-access-kit/datamodels/taxon-constraints/index.html`

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation

### 13.2 Term usage and dependency inspection

`UsagesInterface` provides `usages(...)`, returning structured records describing where and how an ontology identifier is used.

Usage contexts include:

| Usage context      | What can be identified                         |
| ------------------ | ---------------------------------------------- |
| Relationship       | Use as subject, predicate, or object           |
| Logical definition | Use as genus, restriction predicate, or filler |
| Association        | Use in curated annotations                     |
| Mapping            | Use as mapping subject or object               |

Results can be constrained by referencing entities or identifier prefixes. The `Usage` record includes the used identifier, referencing identifier, source, dataset/context fields, and optional axiom or description information.

This capability supports more than simple reverse-link lookup. It provides a foundation for ontology impact analysis, particularly when deciding whether an entity can be changed, renamed, or deprecated without affecting external definitions and annotations.

Its completeness is limited to the connected adapter's accessible data and the usage contexts implemented by that adapter.

Tagged source: `https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/usages_interface.py`

### 13.3 Summary statistics and structural characterization

`SummaryStatisticsInterface` includes:

- `global_summary_statistics`
- `branch_summary_statistics`
- `metadata_property_summary_statistics`

These supply standardized ontology-level, branch-level, and metadata-property characterization rather than requiring each analysis to independently count entity types, relationships, annotation coverage, and related statistics.

The results can support ontology inspection, quality assessment, comparison, and report generation. Their usefulness depends on clearly defined inclusion policies for imported entities, obsolete terms, and graph predicates.

Tagged source: `https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/summary_statistics_interface.py`

### 13.4 Annotated statements and metadata provenance

`MetadataInterface` includes `statements_with_annotations`, `definition_with_annotations`, `definitions_with_annotations`, `entities_contributors`, and `entities_creators`.

This is a different level of access from ordinary labels and definitions: it permits examination of annotations on statements, along with creator and contributor metadata.

Consequently, a definition can be retrieved together with its supporting metadata rather than reduced to just its text. This distinction matters for provenance, authorship, references, and auditing ontology curation.

Tagged source: `https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/metadata_interface.py`

### 13.5 Lower-level RDF and SKOS access

The tagged source also includes:

`RdfInterface`: `graph`, `triples`, `all_triples`, `all_rdflib_triples`, `objects`, and `extract_triples`. This provides a route into RDF statements when graph projections or high-level ontology accessors are insufficient.

`SkosInterface`: concept, broader, narrower, exact, and related operations corresponding to SKOS-style knowledge organization systems.

These expose alternative semantic representations without requiring every ontology to be modeled as an OWL class hierarchy.

Tagged sources:

`https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/rdf_interface.py`

`https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/skos_interface.py`

## 14. Extension architecture and companion-library boundaries

### 14.1 Plugin mechanism

Oaklib supports externally packaged adapters using Python entry points under `oaklib.plugins`.

A plugin can implement one or more ontology interfaces, provide a selector, and encapsulate connections to another service or execution engine.

This is an important extensibility mechanism because a specialized ontology provider need not reimplement every operation to participate in Oaklib's ecosystem. It can expose the capabilities it actually supports while inheriting or composing compatible common behavior.

The external `oakx-robot` project demonstrates this model for ROBOT-based reasoning. It is not equivalent to Oaklib shipping a complete native OWL reasoner.

Source: `https://incatools.github.io/ontology-access-kit/howtos/write-a-plugin.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



### 14.2 Native responsibilities versus companion libraries

| Component               | Responsibility relative to Oaklib                                          |
| ----------------------- | -------------------------------------------------------------------------- |
| Pronto / fastobo        | Parsing and manipulating OBO-oriented representations                      |
| Semantic-SQL (`semsql`) | Relational ontology schema, SQL views, and database distributions          |
| py-horned-owl           | Access to native OWL data structures and axiom representations             |
| Relation Graph          | Precomputation of entailed relationship edges                              |
| Semsimian               | Specialized, Rust-backed semantic similarity                               |
| SSSOM                   | Standardized ontology mapping representation                               |
| KGCL                    | Typed descriptions of knowledge-graph and ontology changes                 |
| LinkML / OMO            | Metadata models, schema constraints, and related validation infrastructure |
| OBO Graphs              | Portable graph-oriented ontology interchange model                         |
| ROBOT                   | External OWL processing and reasoning workflows                            |
| Graphviz / OBOGraphViz  | Graph visualization and layout                                             |

Oaklib's value lies in coordinating these representations and operations through an ontology-oriented API, not claiming ownership of the functionality implemented by every underlying project.

### 14.3 LLM-based ontology operations

Oaklib also offers an LLM adapter and integrations with LLM-based ontology tooling.

Documented applications include text annotation, suggesting definitions, checking definitions against supporting sources, and evaluating proposed mappings.

The important boundary is between generative semantic assistance and formal ontology inference. LLM outputs are candidate assertions or assessments that require appropriate evidence and validation; they do not acquire deductive guarantees by being exposed through an ontology interface.

Related projects such as OntoGPT and CurateGPT use Oaklib in broader knowledge extraction or curation workflows but remain separate systems.

Source: `https://incatools.github.io/ontology-access-kit/howtos/use-llms.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 15. Operational characteristics, performance, and version considerations

### 15.1 Runtime and dependencies

For release 0.7.4, the published Python requirement is 3.10 through 3.14 (`>=3.10,<3.15`).

Published optional extras include `bioservices`, `docs`, `llm`, and `seaborn`. Optional specialized backends and external executables may have their own installation requirements; the existence of an adapter in the source tree does not establish that every optional service dependency is installed by default.

Oaklib uses pystow for local resource caching, with its default storage under `~/.data/`, subject to pystow configuration. The 0.7 release series increased the default cache refresh interval from one week to one month and added cache-management controls.

Sources: `https://pypi.org/project/oaklib/0.7.4/` and `https://github.com/INCATools/ontology-access-kit/releases`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



### 15.2 Consequential execution tradeoffs

| Concern                       | Mechanism                                          | Implication                                                                                                |
| ----------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Repeated graph traversal      | Indexed or precomputed SQL relation graphs         | Can avoid repeated recursive graph exploration, but entailments depend on preprocessing                    |
| Remote ontology access        | API or SPARQL calls                                | Saves local preparation at the cost of network latency, pagination, and availability dependencies          |
| Broad ontology iteration      | Iterator-oriented API, streaming where implemented | May reduce immediate materialization, but does not guarantee backend-side streaming or constant memory     |
| Repeated lookups              | Adapter caches and cached ontology downloads       | Can reduce redundant work, but require explicit freshness assumptions                                      |
| Federated lookup              | Aggregator adapter                                 | Avoids mandatory physical merging while potentially increasing requests and coordination                   |
| Similarity-intensive analysis | Semsimian or precomputed IC                        | May avoid expensive repeated Python computation, provided semantics and configuration align                |
| Rich OWL processing           | Native axiom representation                        | Preserves structures that graph projection may discard, with different computational and integration costs |
| Conversion between models     | OBO Graphs, RDF/OWL, OBO, FHIR                     | Expands interoperability but may discard distinctions unsupported by the target representation             |

There is no sound universal performance ranking of Oaklib adapters. The principal questions are where parsing occurs, whether indexes and closures are prepared, how much data is transferred, whether work can be batched, and which semantic representation the operation requires.

### 15.3 Important limitations and interpretation rules

Interface completeness is not universal. Check that the actual adapter implements the required operation and whether it uses a backend-native implementation or a generic fallback.

Reasoning is not graph walking. The distinction between HOP and ENTAILMENT affects correctness, not merely performance.

Representations can lose information. Flattening OWL axioms into graph edges, converting into terminology formats, or performing simple merges can discard logical or metadata distinctions.

Cross-references are not necessarily equivalences. Mapping predicates, justification, direction, and source provenance must be considered before normalizing identifiers.

Similarity and enrichment are corpus-dependent. Their results depend on annotation data, background populations, predicate choices, and statistical assumptions.

Cached ontologies and online services can represent different releases. An adapter selector alone does not guarantee identical ontology content across runs or providers.

The rolling documentation is ahead of the latest release in at least one important area. The embedding interface discrepancy identified in Section 9 demonstrates why version-sensitive APIs should be checked against the v0.7.4 source tag.

## 16. Capability synthesis

Oaklib is best understood as an ontology operations layer connecting several distinct capabilities:

- Semantic access: normalized identifiers, labels, definitions, relationships, annotations, and rich ontology structures.
- Semantic computation: graph traversal, precomputed entailment, mappings, lexical alignment, similarity, associations, taxonomic constraints, and enrichment.
- Semantic lifecycle: validation, editing, KGCL changes, usage analysis, extraction, merging, conversion, and provenance.

The most important architectural opportunity is the combination of these capabilities. A selected term set can be resolved and normalized, expanded through meaningful relationships, annotated with provenance, compared against another ontology, analyzed with external associations, validated, and exported—often without independently building parsers, mapping registries, graph algorithms, or file conversion utilities.

The qualification is that Oaklib unifies access more completely than it unifies execution semantics. For advanced applications, its strongest role is providing a common semantic vocabulary and a collection of reusable operations while leaving room for specialized backends when fidelity, reasoning completeness, or performance requirements differ.

For additional investigation, the two most useful entry points are the interface catalog and the exact tagged implementation source:

`https://incatools.github.io/ontology-access-kit/packages/interfaces/index.html`

`https://github.com/INCATools/ontology-access-kit/tree/v0.7.4/src/oaklib`

Those sources provide the clearest route from the conceptual capabilities described here to their concrete Python contracts and release-specific implementations.