# LinkML ecosystem: Six complementary Python libraries

Technical capability reference | Researched October 28, 2026

The six projects form a complementary toolkit for developing, enriching, governing, transforming, and reasoning over semantically structured data models. They are not interchangeable extensions of LinkML: each operates at a different level of the modeling lifecycle, and several provide capabilities that core LinkML does not implement itself.

## 1. Ecosystem orientation and verified versions

| Library               | Current version | Primary responsibility                                                                     |
| --------------------- | --------------- | ------------------------------------------------------------------------------------------ |
| valuesets             | 0.4.2           | Reusable, ontology-linked enumerations and controlled vocabularies                         |
| oaklib                | 0.7.4           | Ontology access, graph operations, semantic matching, validation and ontology manipulation |
| schema-automator      | 0.5.7           | Schema induction, importation and semantic enrichment                                      |
| linkml-map            | 0.5.4           | Declarative schema-to-schema and instance-data transformations                             |
| linkml-datalog        | 0.2.0           | Datalog inference and constraint checking using Soufflé                                    |
| linkml-project-copier | 0.5.0           | Reusable project scaffolding, build tooling, tests, documentation and template updates     |

Versions reflect the latest published releases identified from PyPI or, for project-copier, GitHub releases. In particular, `linkml-datalog` 0.2.0 dates from January 31, 2022, and remains explicitly designated experimental/alpha. The project-copier is primarily a Copier template, not a conventional Python runtime library.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+6



For context, core LinkML itself is at version 1.12.1, released October 13, 2026. Its version does not determine the release versions or completeness of these companion projects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### Their architectural roles

| Concern                     | Main library            | What it adds beyond a LinkML schema                                                |
| --------------------------- | ----------------------- | ---------------------------------------------------------------------------------- |
| Semantic vocabulary         | `valuesets`             | Curated, reusable enums with ontology identifiers and metadata                     |
| Ontology intelligence       | `oaklib`                | Backend-independent querying, traversal, mappings and reasoning-related operations |
| Schema discovery            | `schema-automator`      | Inferring models from existing structures and observations                         |
| Model interoperability      | `linkml-map`            | Executable, declarative transformations and derived target models                  |
| Rule-based inference        | `linkml-datalog`        | Recursive derivations, logical rules and inference over instances                  |
| Model engineering lifecycle | `linkml-project-copier` | Reproducible project organization and automated schema engineering                 |

Three distinctions govern how the libraries fit together.

First, semantic definitions differ from semantic execution. `valuesets` primarily supplies curated definitions; `oaklib` provides ontology operations. Declaring an ontology-backed dynamic enumeration does not necessarily mean that every LinkML validator dynamically resolves it.

Second, schema generation differs from data transformation. `schema-automator` derives LinkML schemas from existing evidence. `linkml-map` specifies how instances of one model become instances of another, potentially deriving the target schema as a separate result.

Third, declarative capability differs from implemented execution. The LinkML ecosystem contains expressive metamodels that exceed the currently supported execution paths. This is particularly important for `linkml-map`'s experimental SQL compiler and `linkml-datalog`'s alpha implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

linkml.io+3



## 2. `valuesets` — reusable semantic enumerations

Version: 0.4.2\
Role: A reusable vocabulary library whose LinkML definitions connect familiar enumerated values to standardized semantic identifiers.

Primary documentation: `https://linkml.io/valuesets/`\
Source: `https://github.com/linkml/valuesets`

### 2.1. Semantic enums as reusable model components

`valuesets` maintains LinkML enumeration definitions across biological sciences, clinical research, spatial modeling, statistics, materials, computational methods, laboratory automation, and related domains.

Its conceptual contribution is to separate three properties that ordinary language-level enums often collapse:

| Property                 | Meaning                                | Example                  |
| ------------------------ | -------------------------------------- | ------------------------ |
| Permissible value        | The canonical value serialized in data | `CRYO_EM`                |
| Human-facing description | Explanation of the value               | Cryo-electron microscopy |
| Semantic meaning         | Identifier in an external ontology     | `CHMO:0002413`           |

The library distributes generated Python enum classes and metadata accessors, including `get_meaning()`, `get_description()`, `get_annotations()`, and lookup by ontology meaning through `from_meaning()`. The additional annotations can carry domain-specific metadata beyond a simple label and identifier.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



The distinction is important for interoperability: two systems may use different strings for a concept yet reference the same ontology identifier. Conversely, similarly spelled values can represent different concepts. Semantic identifiers help make the intended meaning explicit; they do not automatically establish a safe conversion between arbitrary vocabularies.

### 2.2. Static and ontology-defined value sets

The library supports two substantially different styles of enumeration.

Explicit enumerations enumerate permitted values directly in LinkML and can be represented as conventional Python enums. These are appropriate for finite, curated vocabularies and provide predictable membership without runtime ontology access.

Dynamic enumerations use LinkML's `reachable_from` construct, identifying a `source_ontology`, one or more `source_nodes`, permitted `relationship_types`, and whether to `include_self`. Instead of explicitly enumerating every disease, cell type, or anatomical structure, the schema specifies a graph-derived set of admissible terms.

This is more expressive than an ordinary enum because the permitted domain can follow an upstream ontology's hierarchy. However, its meaning depends on the ontology version, traversal predicate, root selection, and whether inferred relationships are available.

Execution boundary: The valuesets documentation explicitly states that runtime expansion is still under development. The existence of `reachable_from` in a LinkML definition must therefore not be interpreted as a guarantee that generated Python enum classes or a generic validator resolve ontology membership automatically.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

valuesets+2



A separate companion, `linkml-term-validator`, documents a `DynamicEnumPlugin` for evaluating ontology-backed enumeration constraints, including composition through `concepts`, `include`, `minus`, and `inherits`. Its documented `matches` handling is more limited. That functionality belongs to the companion validator, not to `valuesets` itself.

Documentation: `https://linkml.io/linkml-term-validator/validation-types/`

### 2.3. Schema synchronization and metadata preservation

An easily overlooked capability is the repository's enum-to-slot generation tooling.

`auto_slot_injector.py` can generate a LinkML slot corresponding to an enum—for example, an enum `FooBarEnum` yields a slot `foo_bar` with that enum as its range.

The more advanced `smart_slot_syncer.py` supports three synchronization modes: `update`, `refresh`, and `conservative`. It attempts to preserve manual changes such as `required`, `identifier`, patterns, additional slot metadata, and explicitly marked comments. This makes it possible to keep reusable enumerations and their slot declarations synchronized without replacing every manually curated constraint.

These are documented repository utilities; they should not be confused with a guaranteed stable public Python API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

valuesets



Documentation: `https://linkml.io/valuesets/slot-generation/`

### 2.4. Governance and evolution

`valuesets` distinguishes mirrored value sets, whose authoritative definitions belong to an external steward, from community value sets maintained within the repository.

Its governance model defines maturity states such as `DRAFT`, `WORKING_DRAFT`, `CANDIDATE_RECOMMENDATION`, `STANDARD`, `SUPERSEDED`, and `WITHDRAWN`. Importantly, the project reports that most current value sets remain in `DRAFT`: they are usable but have not undergone formal review and can change materially.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

valuesets



Architecturally, `valuesets` is valuable as a versioned semantic vocabulary layer. It does not replace an ontology query service, an ontology reasoner, or data-value normalization logic.

Documentation: `https://linkml.io/valuesets/governance/`

## 3. `oaklib` — Ontology Access Kit

Version: 0.7.4\
Role: A backend-independent Python interface to ontology terminology, graph structure, mappings, semantic similarity, annotation, enrichment, and selected ontology editing operations.

Documentation: `https://incatools.github.io/ontology-access-kit/`\
Source: `https://github.com/INCATools/ontology-access-kit`

### 3.1. Interface-first architecture

OAK's most important architectural mechanism is the separation of ontology operations from the underlying representation or service.

The central entry point, `get_adapter()`, resolves resource selectors such as `sqlite:obo:cl` into an adapter. Operations can then be invoked against common Python interfaces instead of embedding assumptions about a SQLite database, an OBO file, a SPARQL endpoint, or a remote ontology portal.

The implementation families include local SQLite/OBO resources, Pronto, OBO Graph, SPARQL, Ontology Lookup Service, BioPortal, Ubergraph, Ontobee, Gilda, aggregating adapters, and additional specialized backends. The CLI, `runoak`, exposes many corresponding operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+2



Adapter portability is conditional, not universal. Backends implement different subsets of OAK's interfaces. A local indexed ontology may support extensive traversal while a remote terminology service may specialize in text annotation and search. Calling an operation through a common interface does not guarantee identical availability, result completeness, or performance across adapters.

Interface reference: `https://incatools.github.io/ontology-access-kit/packages/interfaces/index.html`\
Implementations: `https://incatools.github.io/ontology-access-kit/packages/implementations/index.html`

### 3.2. Terminology, identity, and graph traversal

OAK provides a much richer ontology interface than a basic term-label lookup.

| Capability             | Important APIs or interfaces                                 | Architectural significance                                                     |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Term identity          | `curie_to_uri`, `uri_to_curie`, prefix maps                  | Keeps ontology identifiers independent of display labels                       |
| Terminology            | `label`, `definition`, `entity_aliases`, multilingual labels | Supports discovery, normalization, and human-readable representations          |
| Ontology state         | `obsoletes`, ontology versions, metadata, subsets            | Makes deprecated concepts and ontology provenance inspectable                  |
| Graph traversal        | `ancestors`, `descendants`, `paths`, graph extraction        | Enables ontology-defined classification and hierarchy queries                  |
| Entailed relationships | `RelationGraphInterface`                                     | Exposes relationships already inferred or materialized by a supporting backend |
| Logical descriptions   | `logical_definitions`, disjoint class expression axioms      | Provides access to selected richer OWL/OBO semantics                           |
| Subsetting             | `SubsetterInterface`, gap filling                            | Extracts focused ontology regions rather than requiring complete graphs        |

The distinction between asserted edges, transitive graph closure, and reasoner-derived entailments is crucial. A subclass graph traversal answers a different question from evaluating arbitrary OWL restrictions. Likewise, `is_a` and `part_of` have different semantics: treating both as unrestricted subclass relationships can produce incorrect classifications.

OAK exposes these primitives, but the intended interpretation depends on the ontology and adapter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+1



### 3.3. Mappings and semantic normalization

`MappingProviderInterface` provides ontology cross-references and mappings using the SSSOM ecosystem, with operations such as `sssom_mappings()`, `sssom_mappings_by_source()`, normalization, and transitive mapping lookup.

This is particularly valuable when data is described using multiple identifier systems. The library can supply candidate correspondences and normalized identifiers without requiring a bespoke database of ontology crosswalks.

However, mapping predicates matter. An exact match, close match, broad match, and related match do not carry identical substitutability guarantees. Transitive propagation is also only safe under the appropriate relation semantics.

OAK therefore offers machinery for mapping discovery and interpretation, rather than making every returned mapping an unconditional equivalence.

### 3.4. Graph-based similarity, embeddings, and set comparisons

OAK provides both classical ontology-based similarity and embedding-based operations.

`SemanticSimilarityInterface` exposes information-content calculations, common ancestors, most recent common ancestors, pairwise comparisons, and all-by-all similarities. These methods exploit ontology structure rather than merely comparing text labels.

`EmbeddingProviderInterface` extends the concept to vector operations, including `entity_embeddings()`, pairwise similarity, nearest-neighbor search, text-to-entity search, and comparisons between sets of ontology terms.

One particularly useful feature is that OAK can represent ontology closure itself as an embedding:

| Representation     | Mechanism                                 | Consequence                                             |
| ------------------ | ----------------------------------------- | ------------------------------------------------------- |
| `closure`          | Multi-hot vector of reflexive ancestors   | Jaccard on vectors reproduces ancestor-set Jaccard      |
| `closure_ic`       | Ancestors weighted by information content | Weighted Jaccard corresponds to simGIC                  |
| Learned embeddings | Model-specific numerical vectors          | Can capture similarities beyond explicit ontology edges |

The documentation notes that OLS can serve precomputed embeddings, with caching, and that embedding spaces from different models are not directly comparable. Closure can also be configured to traverse predicates beyond `is_a`, which changes the semantics of the resulting similarity measure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



Documentation: `https://incatools.github.io/ontology-access-kit/packages/interfaces/embedding-provider.html`

This combination is especially consequential: a system can apply a common similarity-oriented interface to either deterministic graph-derived features or learned vector representations, while retaining control over the semantic assumptions.

### 3.5. Text annotation, association analysis, and enrichment

`TextAnnotatorInterface` supports annotation of free text and tabular files with ontology entities. Terminology search, lexical matching, and specialized services such as Gilda provide ways to identify candidate concepts from unstructured text.

Separately, `AssociationProviderInterface` handles subject-to-ontology associations, including retrieval, mapping, normalization, and counting. `ClassEnrichmentCalculationInterface` provides enrichment calculations over ontology classes.

These are different workloads: annotation associates passages or strings with concepts; associations represent existing concept relationships; enrichment tests which ontology classes are disproportionately represented in a set. They should not be reduced to the same generic entity-matching task.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation+2



### 3.6. Ontology comparison, subsetting, and controlled changes

OAK exposes `DifferInterface` for ontology comparisons and `PatcherInterface` for applying, reversing, and migrating ontology changes. Supported operations include grouped differences, `apply_patch()`, `migrate_curies()`, and `undo()`.

This creates possibilities for representing ontology evolution as identifiable changes rather than opaque file replacement. The KGCL-related editing functionality remains backend-dependent and partly experimental; support for all possible ontology changes must not be inferred merely from the interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



Reference: `https://incatools.github.io/ontology-access-kit/examples/Commands/Apply.html`

### 3.7. Performance and reasoning boundaries

Local indexed ontology representations and prepared relationship closure can avoid repeated remote requests or expensive graph reconstruction. Remote adapters introduce network latency, service availability, and potentially different data snapshots. Caching improves repeated queries but creates explicit freshness obligations.

Most importantly, OAK is not a universal OWL reasoner. Exposing precomputed entailed edges or OWL axiom structures is not equivalent to supporting arbitrary OWL reasoning natively. Its value is the shared access and operations layer, with full reasoning delegated to an appropriate backend or companion engine where necessary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://incatools.github.io\&sz=32)

oaklib documentation



## 4. `schema-automator` — schema induction, translation, and enrichment

Version: 0.5.7\
Role: Constructing LinkML schemas from existing data, data dictionaries, database structures, alternative schema languages, and semantic metadata.

Documentation: `https://linkml.io/schema-automator/`\
Source: `https://github.com/linkml/schema-automator`

The library offers three complementary operations: generalization from instance data, importation of existing schemas, and annotation/enrichment of resulting LinkML definitions. Its principal output is a LinkML schema; downstream JSON Schema, SHACL, SQL DDL, OWL, or Python generation is generally performed by the core LinkML framework.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



### 4.1. Schema induction from observed data

Generalizers infer classes, slots, ranges, permissible values, cardinality-related properties, and other schema information from representative data.

| Source                  | Capability                                                 | Consequential considerations                                      |
| ----------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------- |
| TSV/CSV                 | Column-to-slot inference, types, examples, enum candidates | Data values may not reveal true domain constraints                |
| Multiple TSVs           | Multiple classes and optional foreign-key inference        | Referential relationships are inferred heuristically              |
| JSON/YAML               | Nested object and collection structure inference           | Sample objects may not cover polymorphic or optional cases        |
| RDF/Turtle              | Generalization from graph instance data                    | Open-world semantics differ from closed-form records              |
| HTML tables             | Extraction from published tables                           | Headers, scraping artifacts and column encodings affect inference |
| TOML and related inputs | Additional source-specific generalization commands         | Coverage depends on the relevant importer/generalizer             |

The `CsvDataGeneralizer` family supports useful controls for enum selection, treatment of low-cardinality integer columns, optionality inferred from missing values, and representation of mixed types using LinkML's `any_of`.

The `generalize-tsvs --infer-foreign-keys` pathway can infer relationships across tables instead of treating every tabular source as an unrelated flat record. This can eliminate substantial initial schema-writing work, but an observed inclusion relationship between values does not prove a declared foreign key, uniqueness guarantee, or complete referential integrity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



Generalizers: `https://linkml.io/schema-automator/packages/generalizers.html`

### 4.2. Importing existing schema representations

Schema Automator includes importers for JSON Schema, Kwalify, schema-style OWL, SHACL, SQL databases, DBML, caDSR, and other metadata formats.

Several import paths have particularly useful capabilities and limitations.

SHACL import. The importer can recognize both explicit shapes with `sh:targetClass` and implicit shapes that also serve as RDFS classes. It can translate subclass-based enumeration trees using `--enum-root`. Identity generation is opt-in because SHACL does not intrinsically declare database-style identifiers.

The importer does not preserve every SHACL construct: SPARQL constraints, severity, messages, and complex alternative/sequence property paths are among documented omissions. These losses are consequential when imported schemas are expected to reproduce the original validation behavior.

SQL import. It can inspect SQLite and other databases reachable through supported SQLAlchemy connection URLs. SQL structure can establish columns, native types, and some relationships, but does not by itself recover ontology meanings, richer domain constraints, or the intended conceptual hierarchy.

OWL import. This targets schema-like OWL representations and expects functional syntax, potentially following conversion with ROBOT. It is not an arbitrary bidirectional OWL-to-LinkML semantic equivalence engine.

caDSR import. Support for Common Data Elements provides a bridge from metadata registries, where a CDE maps naturally to a LinkML slot. This can preserve valuable conceptual metadata that raw data-file inference would miss.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



Importers: `https://linkml.io/schema-automator/packages/importers.html`

### 4.3. Canonical data dictionaries: a particularly important capability

Schema Automator now documents a canonical data dictionary specification intended to bridge human-maintained variable descriptions and machine-readable LinkML schemas.

The specification uses a row-per-variable representation, with TSV/CSV and structured YAML forms.

| Dictionary feature                   | Information preserved or expressed                          |
| ------------------------------------ | ----------------------------------------------------------- |
| `name`, `label`, `description`       | Machine identity, human-readable label, explanatory meaning |
| `type`                               | A controlled ten-type vocabulary                            |
| `codes`                              | Explicit permissible values and labels                      |
| `unit`, `min`, `max`                 | Numeric quantity semantics and constraints                  |
| `uri`                                | Semantic identity, mapped to LinkML `slot_uri`              |
| `required`, `multivalued`, `pattern` | Additional structural and validation declarations           |
| `see_also`, `example_values`         | Provenance and supporting evidence                          |

The distinction between a blank entry and the literal `none` is intentional. A blank field means its value has not been declared; `none` explicitly states that a property is inapplicable or unbounded. This allows the authoring format to distinguish missing documentation from a meaningful assertion.

The structured YAML representation is important for value sets because it can preserve richer metadata for individual codes. A compact TSV serialization can lose descriptions or semantic URIs attached to those individual permissible values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



Documentation: `https://linkml.io/schema-automator/data_dictionary_format.html`

The specification is described as a forward-looking, prescriptive format. It should not be mistaken for a guarantee that every imported legacy dictionary can be translated without intervention.

### 4.4. Data-dictionary adaptation and schema enrichment

The CLI exposes integration-oriented functionality beyond basic schema inference.

`adapt-dbgap` translates dbGaP variable dictionaries, with optional supplementary empirical reports. `adapt-frictionless` and `adapt-redcap` support conversion to and from the canonical dictionary representation. `extract-dd` projects LinkML classes and slots into corresponding data dictionaries, providing a route from a rich model back to a more accessible tabular description.

The `enrich` command then overlays one or more canonical dictionaries onto an existing LinkML schema. Metadata such as descriptions, units, semantic identifiers, code lists, numeric bounds, cardinality declarations, and patterns can be added to empirically inferred slots.

Important limitation: enrichment currently matches by global slot name, not by a class-specific slot identity. Multiple dictionaries are applied in order. Consequently, a `status` variable with different meanings in two source classes can be ambiguous without additional modeling discipline. The CLI reports certain inconsistencies as warnings rather than silently proving the combined schema correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



CLI: `https://linkml.io/schema-automator/cli.html`

### 4.5. Semantic annotation and ontology enrichment

`SchemaAnnotator` integrates with OAK to discover mappings for schema classes, slots, and enum permissible values. The public API includes options controlling whether element URIs and enum meanings are assigned.

`JsonLdAnnotator` derives URI/prefix annotations from JSON-LD contexts. `LLMAnnotator`, available with the `llm` extra, can generate descriptive metadata from language models.

A meaningful distinction exists between annotation and enrichment. Annotation proposes semantic correspondences; ontology enrichment can use known correspondences to copy metadata. The current documented ontology `enrich()` implementation primarily obtains text definitions, not arbitrary ontology axioms or all available annotation properties.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



Semantic enrichment is therefore best understood as a way to improve the quality and interoperability of a candidate schema, not as proof that every automatic match is ontologically correct.

### 4.6. Architectural implications

Schema Automator is most useful when existing information already encodes parts of the intended model, but that information is scattered between observed records, technical schemas, and human-authored dictionaries.

Its major benefit is to make that information recoverable as editable LinkML rather than requiring a hand-built schema from nothing.

The essential limitation is epistemic: observed constraints are not necessarily normative constraints. A column containing only three values in a sample might still have a much larger permitted domain. A nullable column in the source dataset might be required in a finalized domain contract. Schema inference therefore produces a defensible starting point, not a substitute for semantic curation.

## 5. `linkml-map` — declarative data and schema transformations

Version: 0.5.4\
Role: Describing and executing mappings between different LinkML-compatible data models.

Documentation: `https://linkml.io/linkml-map/`\
Source: `https://github.com/linkml/linkml-map`

### 5.1. The transformation specification as an intermediate representation

The central abstraction is `TransformationSpecification`, a declarative YAML-based mapping model with `ClassDerivation`, `SlotDerivation`, and `EnumDerivation` components.

Instead of embedding conversion behavior directly in application code, transformations can specify source-to-target relationships, renaming, expressions, enum remapping, unit conversion, schema changes, and related operations as inspectable metadata.

This enables three distinct kinds of output: transformed instance data, a derived target schema, or an alternative representation of the mapping specification. These outputs serve different purposes and have different completeness guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

linkml.io



### 5.2. Field, class, and enum derivation

The transformation language includes several mechanisms with different semantics.

| Mechanism               | Function                                                       |
| ----------------------- | -------------------------------------------------------------- |
| `populated_from`        | Derive a target class or slot from a source element            |
| `expr`                  | Compute target values using a Python-like expression           |
| `value`                 | Set constant target values                                     |
| `range`                 | Override the target value range used in derivation             |
| `value_mappings`        | Translate known source values into target values               |
| `unit_conversion`       | Convert measurement magnitudes between units                   |
| `stringification`       | Combine structured or multiple values into a textual form      |
| `joins`                 | Retrieve additional fields from another source class/table     |
| `source_schema_patches` | Supply missing source-schema relationship information          |
| `mint_ids`              | Generate deterministic identifiers from emitted record content |

The metamodel additionally defines constructs for aggregation, grouping, wide/long reshaping, offset calculations, missing-value handling, and richer mapping metadata.

Metamodel presence does not establish executor support. The project's own documentation warns that not every feature represented in the transformation model is implemented by its reference Python transformer. Advanced operations should be assessed against the specific execution backend and conformance tests, not simply against generated metamodel documentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+1



Specification: `https://linkml.io/linkml-map/schema/datamodel/`

### 5.3. Schema-aware type coercion and semantic enum normalization

An important capability in the current implementation is target-schema-aware output.

When a target schema is provided, the transformer can coerce values into integer, floating-point, decimal, boolean, or string ranges, including ranges derived from these built-in types. Decimal handling is designed to retain exact decimal representations and trailing zeros. Types such as dates and URIs do not receive equivalent automatic parsing and conversion.

For enumerations, it resolves incoming values in a documented order:

1. Exact permissible-value key
2. `meaning` identifier, with CURIE/URI normalization
3. Title
4. Aliases

For example, a source value `female` or `OMOP:8532` can be normalized to a target enum key `FEMALE`, provided that the target LinkML enum declares the corresponding alias or ontology meaning.

Unrecognized or ambiguous enum values generate warnings and pass through in the default mode; strict execution turns them into row failures.

Dynamic LinkML enums are not resolved by this pathway. Enums defined through `reachable_from`, `matches`, `concepts`, `include`, `minus`, or `inherits` are excluded from this static permissible-value resolution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map



Specification guide: `https://linkml.io/linkml-map/writing-specs/`

This mechanism is particularly useful where normalization and target-schema validation need to be coupled rather than implemented as separate, potentially inconsistent conversion procedures.

### 5.4. Expressions and controlled extensibility

Expressions normally run through `simpleeval`, using a restricted Python-like language. Documented functions include numeric and string conversions, arithmetic helpers, list aggregations, conditional `case()`, UUID5 generation, and naming conversions such as `slugify()`, `to_snake()`, `to_camel()`, and `to_pascal()`.

There are non-obvious data-shape semantics:

Null propagation. Referencing a field as `{field}` causes an expression to return `None` when that value is null. A bare field reference does not have that automatic behavior.

Collection distribution. Certain functions and nested attribute accesses distribute across lists, reducing the need for manually written loops.

Numerical comparisons. Numeric-looking strings from tabular input can be coerced during comparisons.

Additional expression functions can be registered using the documented `@safe_function` extension mechanism.

For more complex logic, `unrestricted_eval` enables an `asteval`-based pathway. This increases expressiveness but introduces substantial trust and security considerations when specifications originate outside the executing application.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+2



Expressions: `https://linkml.io/linkml-map/api/expressions/`\
Functions and units: `https://linkml.io/linkml-map/api/functions/`

### 5.5. Joins and nested relationship traversal

`linkml-map` supports transformations requiring more than one input class.

For tabular sources, `joins` declares the secondary source and the corresponding source/lookup keys. The `join_on` shorthand applies where both tables use a common key name.

For object-oriented or graph-like data, dot notation traverses linked objects or nested structures. Where relationships are represented by identifiers, source objects need to be indexed and the schema must describe the reference type. The `source_schema_patches` mechanism can supply such metadata without modifying an automatically generated source schema.

There is an explicit implementation limit: traversal through a multivalued inline list into a sibling class derivation is not currently supported as a general mapping operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map



These features allow a transformation specification to encode meaningful relational access patterns, rather than requiring every join to be performed by separate preparatory scripts.

### 5.6. Deterministic identifier generation

`mint_ids: true` generates a UUID5 derived from the target schema/class identity and the canonical serialized content of the resulting record.

The canonicalization process standardizes properties such as key order and numeric representation, with rules for null/empty values and ordered lists. Thus, identical emitted records receive the same identifier regardless of input row order, chunking, or parallel execution.

This is useful for content-addressed, otherwise unreferenced output entities. It is not a stable business identifier. If a meaningful content field changes, the resulting UUID can change; identical records can also share the same UUID. For records referenced by others, deriving an identifier from stable source identity is a fundamentally different mechanism.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map



### 5.7. Streaming data, formats, and columnar integration

The `map-data` CLI supports YAML, JSON, JSONL, TSV, CSV, Parquet, and DuckDB outputs. Tabular input can be processed in chunks, and multiple outputs can be written from a single transformation pass.

Parquet and DuckDB output are especially noteworthy because nested objects and collections are preserved as structured columns, rather than necessarily flattened into scalar TSV columns. Multiple runs can populate distinct named tables in a DuckDB database.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+1



This provides a useful bridge from semantically modeled nested data into analytical storage, while preserving more structure than an ordinary CSV export.

The important performance distinction is that writing DuckDB output does not mean DuckDB executes the transformation.

### 5.8. Execution backends, schema profiling, and reversibility

The reference `ObjectTransformer` is the main supported execution path. It interprets the specification in Python and supports the documented richer derivations.

By contrast, the experimental `SQLCompiler`/`DuckDBTransformer` backend currently handles only straightforward `populated_from` renames. The documentation states that other slot derivations can compile into invalid SQL referencing nonexistent columns. It is therefore not a general production-capable SQL transformation engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

linkml.io



`derive-schema` uses a transformation specification to construct an implied target LinkML schema, enabling model profiles or derived representations. `validate-spec` checks mapping consistency against source and target schemas, including class and slot references, expressions, joins, enum mappings, and incompatible type overrides.

The framework also exposes specification inversion and compilation. Renames, unit conversions, and some stringification operations can be inverted; arbitrary expressions and information-losing transformations cannot. Python and Markdown compilation and mapping visualization are available through separate components.

For the Python API, `Session` is deprecated; current guidance is to use `ObjectTransformer`, `SchemaMapper`, `TransformationSpecificationInverter`, and `GraphvizCompiler` for their respective responsibilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+2



CLI: `https://linkml.io/linkml-map/cli/`\
Compiler APIs: `https://linkml.io/linkml-map/api/compiler/`

## 6. `linkml-datalog` — rule-based validation and inference

Version: 0.2.0, released January 31, 2022\
Status: Experimental/alpha\
Role: Compiling LinkML schemas and associated logical rules into Datalog, executing them through the external Soufflé engine, and incorporating derived facts into instance data.

Documentation: `https://linkml.io/linkml-datalog/`\
Source: `https://github.com/linkml/linkml-datalog`

### 6.1. Execution architecture

Unlike the preceding libraries, `linkml-datalog` is fundamentally a logic-execution integration rather than a modeling or conversion utility.

Its execution pipeline comprises four distinct mechanisms:

| Stage                 | Mechanism                                                        | Result                                         |
| --------------------- | ---------------------------------------------------------------- | ---------------------------------------------- |
| Schema compilation    | LinkML definitions become Soufflé Datalog declarations and rules | Executable logical model                       |
| Data translation      | Instance data is converted through RDF into relational facts     | `triple` relations and typed literal relations |
| Logic execution       | External Soufflé executable evaluates rules                      | Derived relations and constraint violations    |
| Result reconstruction | Generated facts are read back                                    | Validation report and enriched instance data   |

The package exposes these operations through the `linkml-dl` CLI and its Datalog engine implementation. Soufflé must be installed separately and available as an executable; installing the Python package alone does not provide the underlying reasoning engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-datalog+1



Implementation: `https://linkml.io/linkml-datalog/basics/`

### 6.2. Recursive inference from schema relationships

The library documents several important classes of inference.

Inheritance inference. A class declared as a subtype using `is_a`, or participating through a mixin, can result in derived membership in the more general category.

Inverse and symmetric relationships. If a relation has a declared inverse or symmetric characteristic, the engine can infer corresponding reversed assertions.

Transitive closure. The documented `transitive_closure_of` annotation derives reachability through a chain of edges. For example, a friendship network can be expanded from direct relationships into a connected-network relation.

Reflexive and transitive characteristics. Schema annotations can drive generation of further relationship rules.

Reified association interpretation. A relationship represented as a first-class object, with its own attributes, can be used to infer a direct relationship between its participants. This allows rich association records and simpler derived graph edges to coexist.

Classification rules. The documented `classified_from` mechanism can derive enumerated categories from numeric properties through expressions, such as assigning developmental categories from age values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-datalog



Translations: `https://linkml.io/linkml-datalog/translations/`

The architectural value is the ability to express recursive and relational derivations declaratively rather than implementing repeated graph traversals or imperative update loops.

### 6.3. Constraint validation through generated Datalog

The compiler can translate selected LinkML schema constraints into rules that generate validation results.

Examples include checking that a referenced individual belongs to the required class and that numeric values respect declared bounds.

Violations are represented through a validation-result relation with SHACL-style component identifiers. The execution pathway then reconstructs a LinkML validation report.

This differs from ordinary structural validation because the same underlying Datalog program can combine derived facts and constraint checking. A relationship might first be inferred and then participate in further rules or validations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-datalog+1



However, this should not be interpreted as complete coverage of the modern LinkML metamodel, SHACL specification, or OWL semantics. The demonstrated compiler implements a specific subset of these concepts.

### 6.4. Custom Datalog rules embedded in schemas

An easily overlooked extension is the ability to place custom Soufflé rules in schema-level annotations under `datalog`.

This supports logical derivations that are not expressible using ordinary LinkML slot declarations. For example, an embedded rule can define `grandparent_of` as the composition of two `parent_of` relationships, followed by more specialized derived relationships.

The engine appends these schema-level rules to the generated Datalog program. Consequently, the schema can act as a distribution point for both its structural data contract and related executable inference definitions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-datalog



Rules: `https://linkml.io/linkml-datalog/schema-rules/`

This increases expressiveness, but it also introduces an explicit dependency on Soufflé syntax, relational fact representation, and compilation compatibility.

### 6.5. Limits: maturity, semantics, and compatibility

There are substantial reasons to treat this package differently from the other five.

Maturity. Its latest PyPI release remains 0.2.0 from 2022, and the project explicitly describes itself as alpha. Publication metadata permits Python 3.9 through versions below 4.0, while the older installation guide specifically states Python 3.9. These are not evidence of successful integration with current Python or LinkML releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Documentation age. Some pages describe LinkML 1.2 capabilities as future developments. Because core LinkML is now substantially newer, those passages must be read as historical implementation documentation rather than as current LinkML roadmap statements.

Reasoning semantics. Datalog usually executes rules over available facts. This is not automatically equivalent to open-world OWL reasoning or to validating all possible graph models. Assumptions about absent facts, recursion, identifier representation, and how data becomes RDF can materially affect inferred results.

Operational overhead. Invoking a separate Soufflé executable, serializing facts, and reconstructing outputs adds stages compared with ordinary in-process LinkML validation. These costs may be justified for substantial recursive workloads, but no general speed advantage follows from the use of Datalog alone.

The most useful way to understand `linkml-datalog` is therefore as an experimental declarative inference capability with a concrete Soufflé implementation—not as the established, comprehensive reasoning layer for every LinkML schema.

## 7. `linkml-project-copier` — schema project lifecycle automation

Template version: 0.5.0, released May 27, 2026\
Role: Generating and maintaining a standardized LinkML project with validation, code generation, documentation, testing, and release infrastructure.

Source and usage documentation: `https://github.com/linkml/linkml-project-copier`\
LinkML guide: `https://linkml.io/linkml/howtos/linkml-project-copier.html`

### 7.1. A template rather than an application library

`linkml-project-copier` is built on Copier, a general project templating and update system.

It is therefore fundamentally different from the other packages: it does not supply a new schema metamodel or runtime ontology operation. Instead, it assembles a maintained environment for authoring LinkML schemas and running existing LinkML tools.

The template's generated project uses `uv` for Python dependency management, `just` as the command runner, Copier for template lifecycle management, and optional GitHub-centered automation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.2. Schema authoring and artifact generation

The generated structure keeps canonical LinkML schema YAML in a dedicated source location and provides configuration for running LinkML generators.

This establishes a meaningful distinction between authored schema source and generated representations, such as Python models, TypeScript definitions, OWL, documentation, or other configured targets.

Because the generator commands are centralized, multiple representations can be derived from the same schema without maintaining independent copies of the domain model.

The actual generation algorithms belong to LinkML and its generators; Copier primarily supplies the project organization and execution conventions.

### 7.3. Validation and test integration

The template's `just` tasks provide a compact interface to several development operations.

| Task           | Function                                           |
| -------------- | -------------------------------------------------- |
| `just setup`   | Establish project dependencies and tooling         |
| `just test`    | Generate artifacts and run Python/data-model tests |
| `just lint`    | Execute LinkML schema linting                      |
| `just testdoc` | Generate or preview project documentation          |

The generated tests exercise both valid and invalid example instance data. This is significant because a schema can be syntactically valid while accepting data that should be rejected—or rejecting data that should be valid.

The template also supplies pre-commit configurations involving `yamllint`, Ruff, `codespell`, and `typos`, reducing the amount of repetitive project-specific tooling configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.4. Documentation and publication workflows

The template includes support for generating schema documentation and publishing it through GitHub Pages, subject to the relevant repository settings and workflow configuration.

Version 0.5.0 includes changes involving MkDocs extensions, GitHub Actions, Python 3.14 CI support, dependency locking, and submissions to the LinkML community on Zenodo. It also adds more flexible handling of existing custom license files, while using Apache-2.0 as the default license for newly generated projects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Release history: `https://github.com/linkml/linkml-project-copier/releases`

These features make the template more than an initial directory generator: it can supply the surrounding machinery required to distribute and maintain a schema as a versioned software and documentation artifact.

### 7.5. Template evolution and migration

The key advantage over the older Cookiecutter-based LinkML project template is Copier's update mechanism.

`copier update --trust` can regenerate a project from a newer template version while retaining previous answers and attempting to reconcile local modifications. `--skip-answered` avoids prompting for configuration already recorded. A specific template revision can also be selected through `--vcs-ref`.

This is not a conflict-free migration guarantee. Template updates can overlap with manually modified files, generator configuration, lint rules, or GitHub workflows, and the resulting conflicts must be resolved.

Projects based on the earlier `linkml-project-cookiecutter` can migrate, with the repository documenting a staged approach and how to recover original configuration choices from `.cruft.json`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Security boundary: The supplied commands use `--trust` because the template includes Jinja2 extensions. This authorizes trusted template code and should be understood as more than simple substitution of inert text files.

### 7.6. Architectural implications

The template's strongest contribution is standardization of the schema engineering lifecycle.

Where core LinkML supplies model semantics and generators, project-copier creates a repeatable environment in which those tools can be executed, tested, documented, and released together.

It does not create a semantic registry, enforce ontology correctness, automatically resolve all schema migrations, or replace the dedicated schema transformation capabilities of `linkml-map`.

## 8. How the six libraries compose

The more interesting architectural opportunities arise from their combinations, because they address different sources of complexity.

### 8.1. From observed data to a semantically enriched canonical model

Existing data, database schemas, dictionaries, and ontologies

Source structures and semantic evidence

Schema Automator

Infer or import structural models and overlay dictionaries

OAK + valuesets

Resolve semantic concepts, curated enums and ontology relationships

Curated LinkML schema

Canonical classes, slots, ranges, meanings and constraints

LinkML-Map

Normalize and transform data into the target model

LinkML-Datalog

Experimentally derive logical facts and validate rule-based constraints

LinkML Project Copier

Build, test, document, package and release the resulting schema project

Conceptual composition, not an automatic end-to-end pipeline. Each connection requires explicit configuration and semantic review.

This architecture can reduce bespoke infrastructure in several distinct ways.

A. Structural inference and semantic authority can remain separate. Schema Automator recovers what is observable in existing data, while OAK and valuesets provide externally governed concepts and value definitions. This avoids treating sample-data frequencies as authoritative domain semantics.

B. Schema semantics can drive actual data conversion. The target-schema functionality in LinkML-Map can normalize enum aliases and ontology meanings during transformation, while schema-level typing controls output representation. It is important to preserve separate ontology validation for dynamic value sets.

C. Recursive derivation can be separated from transformation. LinkML-Map primarily constructs target objects; Datalog expresses derivations over relationships and facts. In principle, mapped data can subsequently participate in logic-based inference, although `linkml-datalog`'s experimental status makes this a capability to verify rather than a guaranteed integration.

D. Schema governance can encompass the resulting artifacts. Project-copier can provide the testing and publication infrastructure surrounding models built or enriched with the other libraries. It is the lifecycle wrapper rather than the central semantic engine.

### 8.2. Consequential distinctions between apparently similar capabilities

| Question                                                        | Correct distinction                                                                                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Is an enum the same as an ontology-derived value set?           | No. A static permissible-value collection and a dynamic `reachable_from` query have different execution and versioning requirements.       |
| Is an ontology mapping sufficient to normalize data?            | Not always. Mapping predicates and ambiguity determine whether substitution is valid.                                                      |
| Can data observations establish a canonical schema?             | They can suggest one, but cannot establish unobserved constraints or normative domain meaning.                                             |
| Does schema import preserve source-language validation exactly? | Not necessarily. Some SHACL, SQL, OWL, and JSON Schema constructs have no direct equivalent or are not imported.                           |
| Does LinkML-Map's DuckDB support mean SQL-based execution?      | No. DuckDB output is distinct from the experimental SQL transformation backend.                                                            |
| Is a deterministic UUID necessarily a stable entity identifier? | No. Content-derived identifiers change with content and cannot replace stable referenced identities.                                       |
| Does an ontology graph query perform full logical inference?    | No. Traversal, closure, materialized entailments, and OWL reasoning have different meanings.                                               |
| Does Datalog support eliminate ordinary validation?             | No. Its documented implementation covers selected constraints and logical derivations, with independent maturity and compatibility limits. |
| Does project-copier manage schema evolution automatically?      | It maintains template-generated project infrastructure, not semantic compatibility between arbitrary schema versions.                      |

### 8.3. Semantic and operational boundaries worth preserving

Canonical identities and versioning. Ontology CURIEs, external concept mappings, LinkML enum keys, source-record identifiers, and content-derived UUIDs are distinct types of identity. Conflating them creates subtle interoperability errors. An ontology snapshot or value-set version may also change what a concept means or whether it remains permissible.

Lossless versus lossy transformations. Moving between a rich ontology, LinkML schema, canonical data dictionary, relational database, or flat table is not automatically reversible. Identity, nested relationships, constraint expressions, code-level metadata, and provenance may not survive every projection.

Validation completeness. Static enum membership, ontology ancestry, schema structural constraints, and recursive domain rules answer different questions. The library carrying a constraint declaration may not be the library that executes it.

Performance boundaries. OAK can reduce repeated ontology infrastructure work through adapters, local indexes, and caches. LinkML-Map can reduce transformation memory through chunking and multiple-output streaming. Datalog may consolidate recursive logical operations, but incurs compilation and fact-conversion overhead. These are workload-dependent mechanisms, not blanket performance guarantees.

Extension trust. LLM-assisted annotation, unrestricted transformation expressions, externally supplied Datalog programs, and trusted Copier templates introduce different forms of executable or probabilistic behavior. A declarative interface does not necessarily make the underlying operation deterministic or safe for untrusted input.

## 9. Capability and maturity assessment

The six projects occupy materially different levels of implementation maturity and architectural responsibility.

| Library                 | Most distinctive advanced contribution                                                                                   | Principal caveat                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `valuesets`             | Shared semantic enumerations, ontology meanings, dynamic enum definitions, governance metadata                           | Most value sets are draft; automatic runtime expansion remains incomplete                         |
| `oaklib`                | Interface-based ontology operations across local/remote backends, semantic similarity, embeddings, mappings, graph diffs | Backend capability varies; not a universal OWL reasoner                                           |
| `schema-automator`      | Combining empirical schema inference, external schema import, canonical dictionaries, and semantic enrichment            | Inference is heuristic; translations and metadata overlays can lose or misassign semantics        |
| `linkml-map`            | Schema-aware data conversion, enum normalization, joins, deterministic IDs, structured columnar output                   | Mapping metamodel exceeds full executor support; SQL backend remains experimental                 |
| `linkml-datalog`        | Compiling schemas and embedded recursive rules to executable Soufflé programs                                            | Old alpha implementation; modern compatibility and completeness are not established               |
| `linkml-project-copier` | Versioned, updatable schema project infrastructure with integrated tests, documentation and release tooling              | Lifecycle template rather than runtime capability; updates can require manual conflict resolution |

The central architectural insight is that LinkML can act as a shared semantic representation across multiple specialized tools without requiring those tools to perform the same work.

`valuesets` provides reusable domain vocabulary, `oaklib` supplies ontology intelligence, `schema-automator` recovers and enriches model structure, `linkml-map` executes transformations into that structure, `linkml-datalog` explores declarative reasoning over its instances, and `linkml-project-copier` supplies the engineering lifecycle around the resulting schema artifacts.

The highest-value distinction is between declaring a semantic truth, discovering or proposing one, transforming data according to it, and validating that the truth is satisfied. These libraries collectively cover much of that territory, but they do not collapse the distinctions automatically.

For further technical investigation, the most substantive primary references are the OAK interface catalog (`https://incatools.github.io/ontology-access-kit/packages/interfaces/index.html`), Schema Automator's canonical data dictionary specification (`https://linkml.io/schema-automator/data_dictionary_format.html`), and LinkML-Map's transformation specification and execution documentation (`https://linkml.io/linkml-map/writing-specs/` and `https://linkml.io/linkml-map/`). These expose the greatest concentration of advanced capabilities and implementation boundaries among the six projects.