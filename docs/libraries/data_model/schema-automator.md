# Schema Automator — Comprehensive Python Library Overview

Target version: 0.5.7 (latest stable PyPI release, August 27, 2026)\
Research date: October 29, 2026\
Ecosystem: LinkML · Python ≥3.10 · BSD-3-Clause

## 1. Architectural orientation

Schema Automator (`schema-automator`) is a Python toolkit for automatically constructing, importing, inferring, and semantically enriching data models, with LinkML as its principal intermediate representation.

Its distinctive value is not simply generating schemas from existing data. It establishes a common modeling representation through which heterogeneous sources—tabular datasets, JSON documents, relational databases, ontologies, and other schema languages—can be converted into structured, semantically enriched models.

It is part of the LinkML ecosystem, but is a separate package from the core LinkML framework. Its primary responsibilities are schema discovery, reverse engineering, and enrichment; the core LinkML framework provides schema representation, validation, and downstream generators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



Primary documentation: `https://linkml.io/schema-automator/`

Repository: `https://github.com/linkml/schema-automator`

Package: `https://pypi.org/project/schema-automator/`

### 1.1 Capability map

| Capability family                     | Core functionality                                                                                                                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Instance-data generalization          | Infer LinkML classes, slots, datatypes, enumerations, optionality, and potential relationships from observed data.                                     |
| Schema import and reverse engineering | Convert JSON Schema, SQL databases, OWL, SHACL, and several specialized model formats into LinkML.                                                     |
| Semantic annotation                   | Discover vocabulary and ontology mappings for classes, slots, and enumeration values.                                                                  |
| Model enrichment                      | Add descriptions, definitions, controlled-vocabulary identifiers, constraints, units, and other metadata.                                              |
| Data dictionary interoperability      | Represent variable definitions in a canonical tabular/structured format, adapt external dictionaries, and reconcile declarations with inferred models. |
| Programmatic composition              | Invoke generalizers, import engines, and annotators as Python objects, not solely CLI commands.                                                        |
| Downstream model generation           | Use the resulting LinkML schema with core LinkML generators for JSON Schema, SQL DDL, SHACL, OWL, Pydantic, and other representations.                 |

### 1.2 The central architecture

Input representations

CSV/TSV · JSON/YAML · RDF · SQL databases · JSON Schema · OWL · SHACL · data dictionaries

Generalizers

Infer from instances

Importers

Translate existing models

Annotators

Enrich semantics

LinkML SchemaDefinition

Classes · slots · ranges · enumerations · relationships · constraints · semantic identifiers

Core LinkML ecosystem

Validation · code generation · schema serialization · downstream representations

The architectural benefit is that schema inference, ontology annotation, and format conversion need not each produce their own incompatible data structures. They can converge on LinkML, where subsequent enrichment or generation can operate on the same conceptual model.

Important distinction: Schema Automator is an assisted modeling system, not a general-purpose, semantics-preserving compiler between arbitrary schema languages. Inference is heuristic; importers may be incomplete or lossy; ontology annotation can produce incorrect matches. This distinction is fundamental to evaluating its output.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



## 2. Inferring schemas from instance data

The generalizers operate on observed values rather than declared constraints. They infer an initial LinkML model through type classification, structural analysis, cardinality heuristics, and, in some cases, relationship discovery.

Primary documentation: `https://linkml.io/schema-automator/packages/generalizers.html`

### 2.1 Tabular schema inference: `CsvDataGeneralizer`

`CsvDataGeneralizer` is the central tabular inference engine. It accepts delimited files, lists of row dictionaries, and pandas DataFrames, allowing schema discovery to be incorporated into Python data-processing pipelines without first serializing everything to TSV.

| Mechanism                | Behavior and significance                                                                                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Type inference           | Recognizes integer, float, boolean, date, datetime, string, and certain structured identifier or measurement patterns.                                                                      |
| Enumerations             | Infers `EnumDefinition` and permissible values from low-cardinality columns; configurable distinct-value ratio, maximum enum size, maximum string length, explicit inclusion and exclusion. |
| Integer-coded categories | `infer_enum_from_integers` allows low-cardinality integers to be interpreted as categories rather than numeric measurements.                                                                |
| Missingness              | `infer_optional` marks columns with observed missing values as not required; this is not equivalent to proving that fully populated columns are mandatory.                                  |
| Heterogeneous values     | `infer_mixed_types` uses LinkML `any_of` to preserve inferred alternative types instead of always collapsing to a single string range.                                                      |
| Identifier inference     | Detects uniqueness, can identify the first unique column as an identifier, and records other unique columns as unique-key candidates.                                                       |
| Multivalued values       | Recognizes list-like values, including pipe-delimited strings, and can mark slots `multivalued`.                                                                                            |
| Schema hints             | Supports known identifier slots, source-schema descriptions, header normalization, embedded data-dictionary rows, and selected ROBOT template conventions.                                  |

Enum inference is particularly consequential. The implementation uses a configurable distinct-value ratio and value-size filters, with separate handling for integer-valued categories. A categorical enum inferred from one sample is a closed set based on observed values, not proof that other permissible values cannot occur. The code also records empirical distinct-value counts as annotations, which the newer data-dictionary enrichment logic can use when checking whether a declared code list is complete.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



Type inference has semantic limits. For example, a field containing numeric identifiers can resemble a measurement; date parsing can classify values in ways that fail subsequent validation; and the measurement detector uses `quantulum3` to recognize dimensional expressions but does not thereby establish a complete, canonical unit model.

Null and multivalue semantics also require care. The underlying engine treats pipe-separated text as multiple values, so a literal pipe in source data can be misinterpreted. Conversely, absence of observed nulls does not establish a business rule requiring the value.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



Source inspection: `https://linkml.io/schema-automator/_modules/schema_automator/generalizers/csv_data_generalizer.html`

### 2.2 Multi-table inference and relationship reconstruction

`convert_multiple()` merges the individually inferred schemas into a multi-class LinkML schema. With `infer_foreign_keys=True`, the Python engine also attempts to reconstruct relationships not explicitly declared in the source files.

Its foreign-key procedure begins with value-set inclusion: if values in one column are contained in a candidate key column of another table, the former may reference the latter. It then scores candidates using signals including identifier-like suffixes, column/table naming similarity, and cross-table relationships.

The resulting LinkML class range can represent the referenced class rather than a primitive string or integer. This is more valuable than merely detecting that two columns have similar names: it starts reconstructing the relational domain graph.

The distinction is that these are candidate semantic relationships, not validated referential constraints. Coincidental containment, incomplete datasets, reused identifiers, and overlapping code systems can all produce false positives. The published generalizer guide shows `schemauto generalize-tsvs --infer-foreign-keys`, although that flag does not appear in the currently generated CLI option listing. The Python constructor and `convert_multiple()` implementation do expose the behavior; the CLI discrepancy is worth treating as unresolved documentation drift.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+3



### 2.3 Hierarchical JSON, YAML, and TOML inference

`JsonDataGeneralizer` recursively decomposes nested structures into candidate classes and slots. A nested object may become a class; arrays can become multivalued relationships; and the generated container class is designated as a LinkML `tree_root`.

Less obvious controls include:

- `inline_as_dict_slot_keys`: treats keys of dictionary-shaped collections as identifiers of contained objects, allowing structures such as keyed object maps to be modeled as collections of entities with explicit IDs.
- Class-name depluralization: can convert plural collection keys into singular class names.
- `omit_null`: suppresses null-valued properties during inference, which changes the evidence used to construct the schema.
- Multiple serializations: supports JSON, YAML, compressed variants through the CLI, TOML, and a frontmatter-oriented CLI mode.

The implementation delegates tabular inference of the recursively extracted objects to `CsvDataGeneralizer`. Consequently, its type and enum behavior inherits the tabular engine’s heuristics. The source also explicitly rejects one dictionary-inlining case where dictionary values themselves are lists; this is not arbitrary JSON structural inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+3



Source: `https://linkml.io/schema-automator/_modules/schema_automator/generalizers/json_instance_generalizer.html`

### 2.4 Other generalization routes

`generalize-rdf` derives schema structure from RDF instance graphs; its documented CLI currently requires Turtle input and a directory argument. This differs from importing an existing RDFS, OWL, or SHACL vocabulary: RDF generalization learns from assertions about instances, whereas ontology/schema import translates declared modeling constructs.

`generalize-htmltable` extracts a selected HTML table and applies tabular inference, including configurable table selection. This can bootstrap a model from published tables without a manually curated CSV export.

The combination of tabular, hierarchical, RDF, and HTML generalizers provides several paths into LinkML, but does not imply that they infer equivalent semantics from equivalent underlying information.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



## 3. Importing existing schema languages and metadata models

Importers address a different problem: translating explicit source-model declarations into LinkML. They can preserve constraints that could never reliably be inferred from a small dataset, but are limited by the importer’s implemented subset of the source language.

Primary documentation: `https://linkml.io/schema-automator/packages/importers.html`

### 3.1 Importer coverage

| Source                       | Entry point           | Distinctive capability or boundary                                                                                                |
| ---------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| JSON Schema                  | `import-json-schema`  | Properties, definitions/references, types, required fields, arrays, enumerations, selected unions; OpenAPI component-schema mode. |
| Kwalify                      | `import-kwalify`      | Existing YAML-oriented validation models into LinkML.                                                                             |
| SQL databases                | `import-sql`          | SQLAlchemy-mediated database introspection, including SQLite files and external SQL databases with appropriate drivers.           |
| SHACL                        | `import-shacl`        | Shape-derived classes, properties, datatypes, cardinalities, class references, and selected ontology-aware conventions.           |
| OWL                          | `import-owl`          | Schema-style ontologies supplied in OWL Functional Syntax.                                                                        |
| RDFS                         | `import-rdfs`         | RDF/RDFS class and property declarations, with optional metamodel mapping configuration.                                          |
| XML Schema (XSD)             | `import-xsd`          | XSD structures, with an option to preserve original element/attribute casing.                                                     |
| Frictionless Data Package    | `import-frictionless` | Dataset package schema metadata into LinkML.                                                                                      |
| Ecological Metadata Language | `import-eml`          | EML XML data-table and attribute descriptions into corresponding classes and slots.                                               |
| caDSR                        | `import-cadsr`        | NCI Common Data Element metadata, with CDEs mapped to LinkML slots.                                                               |
| DOSDP                        | `import-dosdps`       | Ontology Design Pattern templates into classes, template variables, mixins, and optionally enums.                                 |

These are separate import pathways with different semantic coverage; the existence of a command does not establish complete support for its source standard. The OWL and JSON Schema importers, for example, explicitly target subsets of their respective modeling languages.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+3



### 3.2 JSON Schema and OpenAPI: structural import

`JsonSchemaImportEngine` exposes `use_attributes` and `is_openapi`, in addition to schema conversion options.

Global slots versus class-local attributes: With `use_attributes=False`, imported fields use LinkML's global slots plus class-specific `slot_usage`; with `use_attributes=True`, field definitions are placed directly in classes as attributes. This is not just an output-format choice. Global slots favor shared semantic property identities across classes, while local attributes reduce unintended coupling when different classes reuse names with different meanings.

Reference and composition handling: The importer recognizes schema definitions and `$ref`, primitive/object types, arrays as multivalued slots, strings with enumerated permissible values, and selected reference-based `oneOf` class unions. It also supports importing directory-based projects containing multiple schema files.

Ontology-aware JSON Schema extensions: A less obvious source-code pathway recognizes a `graph_restriction` property and constructs LinkML semantic enums using `reachable_from` queries. This enables a JSON Schema carrying ontology restrictions to become a LinkML enum whose meaning is defined by ontology traversal rather than a fixed list of literals.

Translation limits: The documented source code does not implement general JSON Schema equivalence. In particular, `additionalProperties` is marked TODO, `allOf` is read without corresponding general inheritance translation, and `uniqueItems` is read without evident propagation. Moreover, the current generated API documentation describes numeric-bound translation that was not visible in the separately published source listing. Numeric/exclusive-bound fidelity therefore should not be assumed without verification against the exact installed release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+3



Source: `https://linkml.io/schema-automator/_modules/schema_automator/importers/jsonschema_import_engine.html`

### 3.3 SHACL and RDF modeling conventions

The SHACL importer has especially useful options for translating ontology-adjacent domain models.

SHACL graphs commonly express class membership in one of two ways: an explicit shape with `sh:targetClass`, or a class resource that is also an implicit node shape. Schema Automator supports both, with `--mode auto`, `--mode target-class`, and `--mode implicit`. Automatic mode chooses the prevailing convention; explicit selection matters for mixed or unusual graphs.

Other advanced mechanisms include:

- Namespace ownership: `--default-prefix` with `--model-uri` distinguishes local schema terms from imported vocabulary terms, helping avoid collisions between identical local names in different namespaces.
- Identity introduction: `--identifier` adds identifier slots to root classes when required. SHACL itself does not inherently provide LinkML-style object identity.
- Ontology-backed categories: `--enum-root` derives LinkML enums from an ontology subclass tree, including models that use OWL punning for category membership.

The translation is not lossless. SHACL SPARQL constraints, validation severity/messages, and sequence/alternative property paths are not imported; inverse paths receive a special `inverseOf_` representation rather than a general SHACL property-path equivalent. For a SHACL model used as a validator, these losses can materially weaken the semantics of the imported LinkML model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



### 3.4 Database and ontology import distinctions

SQL import reads database metadata through SQLAlchemy, rather than discovering a database's conceptual model through data profiling. Its strongest starting evidence is the database's declared structures. Database-specific types and constraints still have to survive both SQLAlchemy reflection and the LinkML translation.

OWL import expects schema-style OWL in Functional Syntax. The ability to parse OWL constructs is not equivalent to executing OWL reasoning or preserving every ontology axiom. RDFS import is a separate, RDF-serialization-based route with optional metamodel mappings.

DOSDP import is distinctive because an ontology design pattern is a template for structured terms, not an ordinary data instance or SQL table. A template becomes a LinkML class (typically a `TemplateClass` mixin derivative), with variables represented as slots and a configurable choice between class ranges and enums. This opens a modeling route for structured ontology-pattern authoring rather than only validating datasets.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



## 4. Canonical data dictionaries and metadata reconciliation

This is one of the most important newer capability families. Version 0.5.6 introduced a common data-dictionary representation and adapters for bringing external metadata into the schema construction process.

Rather than choosing between a schema inferred from observed data and a separately maintained data dictionary, Schema Automator can combine their information. The inference result contributes empirical structural evidence; the data dictionary contributes declared meaning, constraints, and code definitions.

The distinction is architectural: schema construction becomes a synthesis of observed data and declared metadata, rather than a one-source conversion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zenodo.org\&sz=32)

Zenodo+1



### 4.1 The canonical data-dictionary model

The canonical format is itself defined by a LinkML metamodel at `schema_automator/metamodels/data_dictionary.yaml`. It uses one record per data variable, with YAML as the richer structured form and TSV/CSV as convenient tabular forms.

Documentation: `https://linkml.io/schema-automator/data_dictionary_format.html`

| Metadata category    | Canonical fields                     | Intended semantics                                                                |
| -------------------- | ------------------------------------ | --------------------------------------------------------------------------------- |
| Identity             | `name`, `uri`                        | Physical variable name and, where known, semantic identity.                       |
| Human interpretation | `label`, `description`               | Concise display name versus substantive definition.                               |
| Data type            | `type`                               | Constrained vocabulary of ten logical categories, including `permissible_values`. |
| Controlled values    | `codes`                              | Literal codes, human-readable labels, and optional individual code metadata.      |
| Numeric constraints  | `unit`, `min`, `max`                 | Declared measurement unit and permitted bounds.                                   |
| Value constraints    | `required`, `multivalued`, `pattern` | Presence, collection cardinality, and lexical restrictions.                       |
| Supporting evidence  | `see_also`, `example_values`         | External references and illustrative values.                                      |

Its fixed type vocabulary comprises `string`, `integer`, `decimal`, `boolean`, `date`, `datetime`, `time`, `uri`, `curie`, and `permissible_values`. It deliberately does not expose LinkML's complete metamodel or arbitrary composite types.

An important semantic convention distinguishes an absent declaration from an explicit `none` value for unit or numeric bounds. An empty cell means the metadata has not been supplied; `none` expresses an affirmative judgment that the property is inapplicable or unbounded. That prevents omission from being mistaken for a meaningful constraint.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



The format's documentation specifies recommended and optional fields, along with warn-only and strict conformance semantics. It also describes content-quality checks that keep units, coded values, and ranges out of free-text descriptions. These are useful specification-level expectations, but the published CLI does not separately document a `validate-dd` subcommand, so the availability of every described validation mode should not be inferred from the prose alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



### 4.2 Structured permissible values and information preservation

An enum code is not just a string. The YAML representation can retain separate `code`, `label`, `description`, and `uri` values for each member.

For example, a code `"1"` can be distinguished from its label `"Current smoker"` and its associated SNOMED CT URI. The distinction lets the data retain an original encoded value while the schema records its intended meaning and external semantic identity.

TSV uses a compact `code, label | code, label` serialization, including escaping rules for literal commas, pipes, and backslashes. This serialization is explicitly lossy: individual code descriptions and semantic URIs do not survive a YAML-to-TSV-to-YAML round trip.

The practical consequence is that YAML is the richer interchange representation within the canonical DD format; TSV is principally an authoring and interchange convenience for its smaller metadata subset.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



### 4.3 Adapters: external metadata into a shared dictionary

| Adapter              | Supported direction                       | Important distinction                                                                                      |
| -------------------- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `adapt-frictionless` | Frictionless Table Schema ↔ canonical DD  | Also accepts a Data Package and can select its first resource schema.                                      |
| `adapt-redcap`       | REDCap data dictionary CSV ↔ canonical DD | Bridges REDCap's data-collection-oriented field metadata and the common variable representation.           |
| `adapt-dbgap`        | dbGaP XML → canonical DD                  | Can combine the variable digest with a separate variable report for empirical bounds and calculated types. |

The bidirectional adapters are useful for model interoperability, but bidirectional support does not imply complete preservation of every source-specific attribute. External formats can encode UI controls, conditional collection rules, or other information outside the canonical DD vocabulary.

The dbGaP adapter illustrates the difference between declared and empirical information: a `data_dict.xml` supplies variable definitions, while an optional `var_report.xml` contributes observed numeric bounds and a calculated-type fallback. Those are different kinds of evidence and should not be conflated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



The released EML importer is a related, but distinct, route: `import-eml` directly produces a LinkML schema from Ecological Metadata Language XML, with classes derived from `<dataTable>` elements and slots from `<attribute>` elements. It is not merely another canonical-DD adapter.

Version 0.5.6 also introduced a reusable schema-driven XML loader used by these XML pathways. The release notes describe hardened `lxml` parsing that disables external/DTD entity resolution and network access; that is a security-relevant implementation detail rather than a guarantee about every XML-related operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zenodo.org\&sz=32)

Zenodo



### 4.4 Projecting LinkML schemas back to data dictionaries

`schemauto extract-dd` is the reverse bridge: it takes a LinkML schema and produces the canonical dictionary format.

It can project a selected class with `--class`, or generate one dictionary for each concrete class in batch mode. The projection can reuse LinkML's slot metadata, enum definitions, required/multivalued properties, bounds, units, and related variable descriptors.

This is significant because any supported importer can first produce LinkML, after which `extract-dd` exposes the result to DD-oriented workflows. For example, an XSD-, SQL-, or EML-derived schema can yield a tabular data dictionary without a dedicated XSD-to-DD or SQL-to-DD converter.

The projection is intentionally one-way and structurally lossy. A flat data dictionary cannot faithfully represent class inheritance, mixins, complex class relationships, rules, or all nested object structures. It is a variable-oriented view of a richer model, not a replacement for that model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



### 4.5 Enriching an inferred schema with declared metadata

`schemauto enrich` overlays one or more canonical dictionaries onto an existing LinkML schema. It can populate descriptions, titles, semantic URIs, units, declared permissible values, minimum and maximum constraints, requiredness, multivaluedness, and regex patterns.

Three behaviors deserve particular attention.

First, enrichment is keyed by global slot name. It does not currently offer class-specific DD targeting. If two classes use an identically named slot with different meanings, a dictionary entry can affect the wrong semantic property. This is a significant consequence of LinkML's global-slot model when applied to heterogeneous datasets.

Second, overlays are ordered. Multiple dictionaries can be supplied and processed sequentially; later overlays encounter metadata already assigned by earlier ones. Ordering and conflict semantics are therefore part of the operation, not an incidental implementation detail.

Third, disagreements are not silently equivalent to successful validation. The tool emits warnings for selected conflicts, including type disagreement or declared enum codes that do not cover observed values. Its empirical distinct-count annotations help avoid replacing a broader inferred value set with an obviously incomplete code list. But warnings are not a full reconciliation report with provenance and disposition decisions.

The dedicated reconciliation-report feature remains separately tracked from the released enrichment mechanism.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



Command reference: `https://linkml.io/schema-automator/cli.html`

## 5. Semantic annotation and model enrichment

Schema Automator supports three different forms of semantic enhancement: ontology-based term matching, context-derived URI assignment, and LLM-generated descriptions. They have different evidence models, correctness properties, and operational dependencies.

### 5.1 Ontology annotation through OAK

`SchemaAnnotator` integrates with the Ontology Access Kit (OAK) (`oaklib`) to search ontology terms corresponding to LinkML schema elements.

It can examine class names, slot names, aliases, and enum permissible values. Name normalization, including splitting camel case, helps convert programming-style identifiers into search terms. Optional description mining can expand the candidate text.

The annotator can add mappings and, under explicit configuration, semantic URIs for schema elements and meanings for enum permissible values. Its principal configuration controls include:

| Setting                   | Role                                                          |
| ------------------------- | ------------------------------------------------------------- |
| `ontology_implementation` | OAK backend used for ontology search and lookup.              |
| `mine_descriptions`       | Include free-text descriptions when searching for concepts.   |
| `allow_partial`           | Control acceptance of partial rather than whole-text matches. |
| `curie_only`              | Restrict accepted identifiers to CURIE-like representations.  |
| `assign_element_uris`     | Optionally assign semantic URIs to schema elements.           |
| `assign_enum_meanings`    | Optionally assign meanings to enum permissible values.        |

OAK provides the ontology-access abstraction; Schema Automator contributes the traversal of LinkML elements and assignment of returned mappings. Supported ontology sources depend on the selected OAK adapter, with documented possibilities including local OBO/OWL/RDF files, BioPortal, OLS/ZOOMA, Ubergraph, Wikidata, and LOV.

A match is not a proof of semantic identity. An ordinary-language term may correspond to several ontology concepts, and mapping errors can have downstream consequences if they are promoted into authoritative identifiers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



Documentation: `https://linkml.io/schema-automator/packages/annotators.html`

OAK documentation: `https://incatools.github.io/ontology-access-kit/`

### 5.2 Mapping versus URI assignment versus definition enrichment

These operations are related but not interchangeable.

Ontology mapping records a relationship between a schema element and an ontology concept, typically as an exact mapping candidate. URI assignment associates an element directly with an external identifier. Ontology enrichment uses existing URI/mapping information to retrieve descriptions or definitions from the ontology.

The API exposes this last operation as `SchemaAnnotator.enrich()`. Its documented implementation currently copies textual definitions/descriptions; it does not broadly import all ontology axioms or transform an ordinary LinkML model into a fully reasoned ontology.

The CLI supports `annotate-schema` and `enrich-using-ontology`; the latter can optionally annotate first with `--annotate`. The tabular generalizer also has a documented `--annotator` option, allowing inference and ontology enrichment to be combined in one entry point.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



### 5.3 JSON-LD context-driven annotation

`JsonLdAnnotator.annotate(schema, jsonld_path)` uses an existing JSON-LD context to derive URI and prefix information.

This is a different problem from ontology text mining. A context provides explicit declared identifier mappings, while ontology matching attempts to infer appropriate identifiers from names and descriptions. When an authoritative JSON-LD context exists, context-driven mapping can avoid some of the ambiguity inherent in free-text search.

It still depends on the context's scope and quality; it does not automatically reconcile incompatible semantic definitions across vocabularies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation



### 5.4 LLM-based annotation

`LLMAnnotator` provides a separate enrichment mechanism, available through the optional `llm` extra and `schemauto enrich-using-llm`.

As documented for the current release, the supported task is adding missing descriptions. The CLI explicitly refers to broader future enrichments; those should not be treated as released functionality.

Its value is generating readable explanatory metadata for otherwise sparsely described models. Its boundaries are equally important: model-generated prose is not authoritative metadata, output may be incorrect, and external models introduce request costs and possible data-disclosure considerations. The upstream documentation specifically cautions about expense on large schemas.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+1



## 6. Python API, composition, and integration boundaries

### 6.1 The programmatic model

The library is not limited to CLI-based file conversion. Its major processing engines can return the LinkML runtime's `SchemaDefinition` objects, enabling subsequent transformations through normal Python object APIs.

| API                                           | Principal role                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| `CsvDataGeneralizer.convert()`                | Delimited file to a single-class schema.                                     |
| `CsvDataGeneralizer.convert_dicts()`          | Python row dictionaries to a schema.                                         |
| `CsvDataGeneralizer.convert_from_dataframe()` | pandas DataFrame to a schema without intermediate TSV serialization.         |
| `CsvDataGeneralizer.convert_multiple()`       | Multiple tabular datasets to one multi-class schema.                         |
| `CsvDataGeneralizer.infer_linkages()`         | Heuristic detection of implicit foreign-key relationships.                   |
| `JsonDataGeneralizer.convert()`               | Nested instance documents or Python dictionaries to a schema.                |
| `JsonSchemaImportEngine.convert()`            | JSON Schema or OpenAPI-style definitions to LinkML.                          |
| `SchemaAnnotator.annotate_schema()`           | Apply ontology mappings across schema elements and enum members.             |
| `SchemaAnnotator.enrich()`                    | Retrieve ontology definitions for existing semantic identifiers or mappings. |
| `JsonLdAnnotator.annotate()`                  | Apply context-derived semantic identifiers.                                  |
| `LLMAnnotator.enrich()`                       | Generate missing descriptions.                                               |

These operations can be composed through shared `SchemaDefinition` objects, although not every engine exposes exactly the same input/output conventions.

A useful extension boundary is the LinkML runtime object model, particularly `SchemaView`. It provides an alternative to repeatedly editing serialized YAML and enables class/slot inspection, induced slot resolution, and schema manipulation. This is core `linkml-runtime` functionality, not a separate Schema Automator inference engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+3



Direct API references:

`https://linkml.io/schema-automator/packages/generalizers.html`

`https://linkml.io/schema-automator/packages/importers.html`

`https://linkml.io/schema-automator/packages/annotators.html`

### 6.2 Composition with companion libraries

| Component        | Responsibility and boundary                                                                                                                                                       |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `linkml-runtime` | Defines `SchemaDefinition`, classes, slots, enums, `SchemaView`, and runtime schema utilities.                                                                                    |
| Core `linkml`    | Provides generators, schema tooling, validators, and downstream representation support.                                                                                           |
| `oaklib`         | Provides ontology backends, concept search, and ontology metadata retrieval.                                                                                                      |
| `linkml-map`     | Supplies mapping infrastructure used within parts of the canonical data-dictionary adapter implementation; it should not be confused with Schema Automator's complete public API. |
| SQLAlchemy       | Supplies database connectivity and reflection for SQL import.                                                                                                                     |
| pandas / Pandera | Supports tabular processing and an optional alternative inference route.                                                                                                          |
| `lxml`           | Handles XML parsing for relevant importers and adapters.                                                                                                                          |

The core LinkML generator family includes JSON Schema, SHACL, OWL, SQL DDL, Pydantic, Python, Rust, TypeScript, GraphQL, and other formats. Those generation capabilities belong to LinkML, not to Schema Automator's own importer/generalizer package.

The full resulting pipeline can therefore move from an unfamiliar external model to a LinkML representation and then to multiple downstream artifacts. However, the correctness of each output still depends on what semantics survived the initial import or inference and what the selected generator can represent.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

linkml documentation+2



Core generator documentation: `https://linkml.io/linkml/generators/index.html`

Generator capability matrix: `https://linkml.io/linkml/generators/dashboard.html`

Core validation documentation: `https://linkml.io/linkml/data/validating-data.html`

### 6.3 Extensibility mechanisms

The most consequential extension mechanisms are conventional Python-level composition rather than a general declarative plugin registry.

Inference customization: `CsvDataGeneralizer` exposes named parameters for enum thresholds, optionality, mixed-type handling, identifier hints, data-dictionary rows, and other behavior. Custom processing can also work directly with its in-memory row and DataFrame interfaces.

Ontology backend substitution: `SchemaAnnotator` accepts an OAK interface instance. A change in ontology source need not require changing the surrounding schema traversal logic, provided the selected backend implements the necessary ontology-access/search interface.

Dialect and metadata adaptation: SQL import depends on SQLAlchemy-compatible database connectivity. Canonical DD adapters normalize selected external formats before enrichment, while custom transformations can operate on the canonical DD model or resulting LinkML objects.

Source-model mapping customization: The RDFS importer exposes `--metamodel-mappings`, and the JSON Schema importer offers the global-slot versus local-attribute distinction. Those controls are valuable when the source's modeling conventions differ from the desired LinkML representation.

There is also an optional `--pandera` inference route in the CLI. Its semantics are not identical to the default inference engine: the CLI explicitly notes that `--infer-optional` is ignored in Pandera mode.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



## 7. Operational characteristics and version history

### 7.1 Current release and dependencies

Stable release

## 0.5.7

Released

August 27, 2026

Python requirement

≥3.10

License

BSD-3-Clause

Published optional extras

docs

duckdb

llm

mariadb

postgres

The published extras affect dependency availability. The `llm` extra is specifically required for LLM enrichment; database-related extras provide dependencies for corresponding database integrations. They do not change every importer into a full-featured implementation for the named database engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 7.2 Significant recent additions

| Release | Material change                                                                                                                                                                     |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.5.4   | XSD importer, optionality and mixed-type inference enhancements, and selected additional OWL import functionality.                                                                  |
| 0.5.5   | Low-cardinality integer-to-enum inference and import/startup improvements.                                                                                                          |
| 0.5.6   | Canonical data-dictionary metamodel; REDCap, Frictionless, and dbGaP adapters; EML import; schema-to-DD projection; ordered DD enrichment; hardened XML parsing.                    |
| 0.5.7   | Dependency compatibility fixes, notably a `linkml-map` minimum version that permits fresh Python 3.14 installations, and maintenance of compatibility with evolving LinkML imports. |

Version 0.5.7 is principally a compatibility and packaging release; the major new capability family is the data-dictionary infrastructure introduced in 0.5.6.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zenodo.org\&sz=32)

Zenodo+1



Version-specific release references:

`https://zenodo.org/records/22134611` — v0.5.7

`https://zenodo.org/records/21418998` — v0.5.6

### 7.3 Performance and execution behavior

The library is primarily an offline schema-development and transformation toolkit, rather than an optimized runtime schema registry or streaming validation engine.

Its performance characteristics follow from the underlying operations:

- Tabular inference: In the documented implementation, a delimited file is read into row objects; DataFrame input is converted with `df.to_dict("records")`. Distinct-value tracking, enum detection, and possible cross-table comparisons can impose substantial memory and processing costs on large datasets.
- Relationship inference: Candidate key and foreign-key discovery may require examining values across multiple tables. It is not a substitute for database catalog introspection when declared constraints are already available.
- Ontology annotation: Runtime depends strongly on OAK backend choice, ontology availability, indexing, and possibly network access. Local indexed ontologies and remote ontology services have materially different execution characteristics.
- LLM enrichment: Work scales with the number of elements to be described and the chosen model's latency and cost, not merely the size of the final schema.
- Schema conversion: Importer complexity depends on source-model features, hierarchy, references, and semantic translation—not simply the number of lines in a document.

These are mechanisms and likely scaling considerations, not benchmark guarantees. I found no suitable upstream measurements establishing general throughput, peak memory, or comparative scaling claims for version 0.5.7.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

Schema Automator documentation+2



## 8. Consequential limitations and capability maturity

The following distinctions are particularly important when deciding what can be derived automatically and what remains an explicit modeling concern.

| Area                             | Verified boundary or uncertainty                                                                                   |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Observed versus permitted values | Inferred enums contain observed categories; they do not establish complete domain vocabularies.                    |
| Identifier recognition           | Value uniqueness and identifier-like names are evidence, not proof of persistent entity identity.                  |
| Multi-class relationships        | Foreign keys are heuristic; source datasets can lead to incorrect relationship inference.                          |
| Shared slot semantics            | Same-named columns with different meanings can collide in multi-class models or global DD enrichment.              |
| Missingness                      | Observed optionality does not by itself establish the full intended cardinality contract.                          |
| Complex schema import            | JSON Schema, OWL, and SHACL mappings cover subsets, with known omissions.                                          |
| Flat data dictionaries           | Inheritance, nested structures, rules, and broader relationship semantics cannot all fit into the DD model.        |
| Semantic annotation              | Ontology text matching produces candidates, not automatically verified conceptual equivalence.                     |
| LLM enrichment                   | Released functionality is description generation, not verified automatic semantic modeling.                        |
| Downstream generation            | A generated artifact is limited by both the imported LinkML model and the target generator's own feature coverage. |

Several upstream issues help distinguish currently available behavior from unfinished or proposed capabilities:

Pattern inference: Adding `pattern` constraints from consistent observed formats is tracked separately. The fact that dictionary enrichment can import a declared pattern should not be confused with generalized pattern inference from values.

`https://github.com/linkml/schema-automator/issues/195`

Unit inference: The tabular code already has measurement-recognition logic using `quantulum3`, but automated derivation and population of canonical unit metadata is a separate tracked enhancement.

`https://github.com/linkml/schema-automator/issues/194`

Structured reconciliation: The released enrichment process logs selected warnings; a fuller inferred-versus-declared reconciliation report with organized discrepancies is separately tracked.

`https://github.com/linkml/schema-automator/issues/193`

Global naming collisions: Equal-named columns with different semantics are a documented multi-table modeling problem.

`https://github.com/linkml/schema-automator/issues/108`

JSON Schema numeric bounds: The upstream issue tracker includes a report that standard `minimum` and `maximum` constraints are not imported, consistent with the limitation visible in the inspected generated source. The newer API prose describes numeric constraint translation, so this is an area where checking the exact 0.5.7 tagged implementation matters.

`https://github.com/linkml/schema-automator/issues/226`

Empty tables: An upstream report identifies zero-row tables being dropped instead of yielding classes from headers alone.

`https://github.com/linkml/schema-automator/issues/225`

These issues are particularly relevant because they involve semantic completeness and correctness, not just optional convenience features. They also highlight that the continuously published documentation may describe a different implementation state than a particular tagged release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+5



## 9. Architectural synthesis

Schema Automator's principal capability is to connect three kinds of modeling evidence through one LinkML representation:

1. Empirical evidence: What data instances reveal about fields, values, types, optionality, and possible relationships.
2. Declared structure: What existing JSON Schema, SQL, SHACL, OWL, XSD, or domain metadata explicitly constrains.
3. Semantic knowledge: What data dictionaries, ontology mappings, definitions, and controlled vocabularies contribute about meaning.

The combination is more significant than any single importer or inference command. It makes possible schema development workflows in which structural discovery, external-model translation, declared-metadata enrichment, semantic annotation, and downstream generation operate around a shared schema object rather than a collection of independent conversion scripts.

At the same time, the library does not automatically establish that the resulting model is authoritative, complete, or semantically equivalent to all of its sources. Its highest-value role is reducing the mechanical effort of constructing and enriching LinkML models while retaining explicit control over semantic decisions.

### Primary source navigation

| Resource                                | Direct URL                                                       |
| --------------------------------------- | ---------------------------------------------------------------- |
| Official documentation                  | `https://linkml.io/schema-automator/`                            |
| Full CLI reference                      | `https://linkml.io/schema-automator/cli.html`                    |
| Generalizers and Python APIs            | `https://linkml.io/schema-automator/packages/generalizers.html`  |
| Importers and Python APIs               | `https://linkml.io/schema-automator/packages/importers.html`     |
| Annotators and Python APIs              | `https://linkml.io/schema-automator/packages/annotators.html`    |
| Canonical data-dictionary specification | `https://linkml.io/schema-automator/data_dictionary_format.html` |
| Upstream repository and issues          | `https://github.com/linkml/schema-automator`                     |
| Python package and release metadata     | `https://pypi.org/project/schema-automator/`                     |
| LinkML generator capabilities           | `https://linkml.io/linkml/generators/dashboard.html`             |

Bottom line: Schema Automator is best understood as a LinkML schema construction, reverse-engineering, and enrichment framework. Its major advanced strengths are heterogeneous source-model import, heuristic multi-table inference, ontology-backed semantic annotation, and—especially since v0.5.6—the canonical data-dictionary adapter and enrichment infrastructure. Its governing limitation is that automatic schema reconstruction and semantic enrichment produce useful structured evidence, not guaranteed semantic truth.