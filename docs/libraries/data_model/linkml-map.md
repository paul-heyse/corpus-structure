# linkml-map — Comprehensive Python Library Overview

Target: v0.5.4 (latest stable) · Research date: October 29, 2026 · Python ≥3.10 · Status: Active development; transformation specification evolving

Official documentation: [https://linkml.io/linkml-map/](https://linkml.io/linkml-map/?utm_source=chatgpt.com)

Source repository: [https://github.com/linkml/linkml-map](https://github.com/linkml/linkml-map?utm_source=chatgpt.com)

PyPI: [https://pypi.org/project/linkml-map/](https://pypi.org/project/linkml-map/?utm_source=chatgpt.com)

## 1. Executive orientation

`linkml-map` is a declarative, schema-aware data transformation framework in the LinkML ecosystem. Its central abstraction, `TransformationSpecification`, describes how to derive target classes, attributes, enumerations, and values from a source data model, independently of the execution mechanism or serialization format.

Its architectural significance is that mappings themselves become structured, inspectable, reusable data-model artifacts, rather than transformation logic dispersed across procedural Python code.

The library combines three related capabilities:

1. Semantic mapping: Express relationships between source and target schemas, including structural transformations, typed value derivations, enum translations, unit conversions, and cross-class relationships.
2. Transformation execution: Interpret mapping specifications against Python objects, structured documents, and tabular datasets, including joins, streaming, and structured or columnar output.
3. Transformation metaprogramming: Validate, normalize, compose, invert, visualize, and compile mappings; derive target schemas; and represent mapping metadata using the LinkML transformation metamodel.

### Capability map

| Functional area            | Principal capabilities                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------- |
| Mapping language           | `TransformationSpecification`, `ClassDerivation`, `SlotDerivation`, `EnumDerivation`   |
| Structural transformations | Rename, project, restructure, nest, flatten, copy, omit, reshape                       |
| Value transformations      | Expressions, constants, conditionals, stringification, unit conversion, value mappings |
| Relational operations      | Explicit/implicit joins, foreign-key traversal, indexed cross-class lookup             |
| Ontology and enums         | Permissible-value mappings, semantic identifiers, enum derivation                      |
| Schema engineering         | Target-schema derivation, schema patches, schema profiling                             |
| Execution                  | `ObjectTransformer`, streamed tabular mapping, DuckDB-assisted joins                   |
| Interoperability           | YAML, JSON, JSONL, CSV, TSV, Parquet, DuckDB                                           |
| Mapping governance         | Specification validation, metadata, composition, inversion, visualization              |
| Advanced integration       | Python extension functions, compiler interfaces, LinkML `SchemaView`                   |

### Version boundary

The current stable release is 0.5.4, published August 26, 2026. An important prerelease, 0.6.0-rc1, appeared October 23, 2026.

The upstream documentation already describes several 0.6 changes, so it should not be interpreted uniformly as documentation of 0.5.4. In particular, automatic target-schema type coercion, enum canonicalization, deterministic content-based identifier generation, and the deprecation of `Session` belong to the 0.6 release candidate, not the stable 0.5.4 baseline.

The mapping metamodel is explicitly described upstream as not yet fully stable, and not every declared feature is implemented in the Python execution engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 2. Conceptual model and architecture

The central separation is between the source schema, transformation specification, target schema, and execution engine. These are related but distinct artifacts.

Conceptual relationship; the specification can also be used to derive a target schema without executing a data transformation.

The source schema supplies structural and semantic information through LinkML's `SchemaView`: class definitions, inherited and induced slots, data types, collection cardinality, identifiers, enumerations, and units. The transformation specification declares how these elements should be interpreted and derived. A target schema can constrain the result or be inferred from the mapping.

The primary released execution implementation is `ObjectTransformer`, which recursively maps structured Python values. The model is designed to accommodate alternative executors, but the portability of the specification does not imply semantic equivalence across all available backends.

### Two-stage specification resolution

An important internal distinction is that the specification is not necessarily executed exactly as written.

| Stage                   | Mechanism                                              | Consequence                                                                                                       |
| ----------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Load-time normalization | `normalize_spec()`                                     | Normalizes compact YAML forms, legacy keys, references, and metamodel representation before Pydantic construction |
| Schema-bound induction  | `Transformer.derived_specification`                    | Infers source slots, source ranges, class relationships and eligible implicit joins using `SchemaView`            |
| Runtime evaluation      | `ObjectTransformer.map_object()` or `transform_spec()` | Resolves actual values, evaluates expressions and traverses structured or related records                         |

The derived specification is a cached, deep-copied form of the original. Source-schema patches are applied before semantic induction. This matters because a syntactically compact mapping can become a more explicit mapping after schema binding, including synthesized joins.

The separation also enables inspecting the resolved mapping independently from the original authoring form. However, specification resolution is not a substitute for validating transformed instances.

Primary source: [https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/transformer.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/transformer.py?utm_source=chatgpt.com)

## 3. Transformation metamodel: what can be expressed

The transformation language is itself modeled in LinkML, with generated Python classes under `linkml_map.datamodel.transformer_model`.

### Primary constructs

| Construct                                   | Responsibility                             | Important distinctions                                                                                                     |
| ------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `TransformationSpecification`               | Root transformation artifact               | Holds class and enum derivations, schema references, prefixes, mapping provenance, and copy directives                     |
| `ClassDerivation`                           | Derives a target class from a source class | May define joins, nested slot derivations, inheritance, target-class metadata, and pivot operations                        |
| `SlotDerivation`                            | Derives a target attribute                 | Supports source lookup, expressions, constants, value mappings, ranges, units, collections, and hidden intermediate values |
| `EnumDerivation`                            | Derives a target enumeration               | Supports permissible-value remapping, expressions, and pass-through behavior                                               |
| `PermissibleValueDerivation`                | Relates target and source enum values      | Multiple source values may map to one target value                                                                         |
| `AliasedClass`                              | Describes a cross-table join               | Distinguishes primary-side and lookup-side keys                                                                            |
| `CopyDirective`                             | Controls target-schema construction        | Applies to schema elements, not runtime records                                                                            |
| `SchemaReference`                           | Identifies a source or target schema       | Replaces the deprecated bare-string representation                                                                         |
| `PivotOperation`                            | Wide/long structural transformation        | Implemented for MELT/UNMELT in the Python engine                                                                           |
| `AggregationOperation`, `GroupingOperation` | Represent aggregate/group semantics        | Declared in the model; full execution support must not be assumed                                                          |

### Significant modeling capabilities

Class derivations as structural templates. A class derivation can rename a class, project selected fields, derive fields from unrelated source names, include nested derived objects, and attach class-level LinkML metadata. Inheritance and mixins can relate class derivations, permitting transformation definitions to reuse other derivations.

Slot derivations as semantic units. A slot declaration can be a passthrough, source-field reference, literal constant, expression, unit conversion, enum mapping, or nested object construction. A simple same-name slot can omit an explicit `populated_from` reference, allowing the normalizer to infer it.

Schema definitions embedded in mapping specifications. `target_definition` and `overrides` permit target class and slot characteristics to be established as part of a mapping, including `range`, `is_a`, `mixins`, or more general LinkML definition properties. This provides more than simple source-to-target field association.

Provenance and governance metadata. The root specification can carry `id`, `title`, `version`, `publication_date`, `license`, `creator`, `author`, `reviewer`, `mapping_method`, `documentation`, and `content_url`. This allows mappings to be independently identified and attributed, rather than surviving only as undocumented ETL code.

One qualification: several metamodel fields express intended semantics beyond what the stable executor implements. For example, `CopyDirective.add` is explicitly marked unimplemented, and `AggregationOperation` does not provide a general operational group-by engine in 0.5.4.

Primary source: [https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/datamodel/transformer_model.yaml](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/datamodel/transformer_model.yaml?utm_source=chatgpt.com)

Generated schema reference: [https://linkml.io/linkml-map/schema/](https://linkml.io/linkml-map/schema/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map



## 4. Expressions and derived-value computation

Expressions are one of the library's main mechanisms for combining declarative mapping with general computation.

### 4.1 Restricted expression evaluator

The default evaluator uses `simpleeval` with LinkML-specific semantics. It supports common Python-like arithmetic, Boolean expressions, comparisons, attribute references, collection traversal, function calls from an allowed namespace, and conditional expressions.

The library adds several consequential behaviors:

- Null propagation: `None` propagates through arithmetic, ordering, membership tests and many function calls. Equality retains Python's semantics, so `None == "x"` is false. Braced and bare slot references use the same underlying resolution.
- Collection traversal: Accessing an attribute through a list of structured objects can distribute the access over list members, returning a corresponding list.
- Numeric-string arithmetic: Numeric-looking strings can participate in numeric expressions instead of behaving as ordinary strings in cases such as multiplication.
- Cached expression evaluation: Parsed expression ASTs and evaluator machinery are reused, reducing repeated setup in row-oriented processing.
- Strict unresolved-reference handling: `strict=True` raises on unknown expression names; the default compatibility mode warns and supplies null in relevant cases.

These semantics reduce the amount of procedural code required for common data-cleaning expressions, but they are not equivalent to SQL's complete expression semantics or unrestricted Python.

### 4.2 Built-in expression functions

The stable expression namespace contains a substantial collection of helpers.

| Family                   | Functions and behavior                                                                                                       |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Numeric                  | `int`, `float`, `abs`, `round`, `floor`, `ceil`                                                                              |
| String                   | `upper`, `lower`, `title`, `capitalize`, `strip`, `replace`, `substr`, `contains`, `startswith`, `endswith`, `split`, `join` |
| Collection               | `len`, `sum`, `min`, `max`, `sorted`, `any`, `all`, `first`, `last`, `reversed`                                              |
| Conditional/null         | `case`, `coalesce`                                                                                                           |
| Type inspection          | `is_str`, `is_int`, `is_float`, `is_bool`, `is_list`, `is_numeric`                                                           |
| Identifier normalization | `slugify`, `to_snake`, `to_camel`, `to_pascal`                                                                               |
| Deterministic values     | `uuid5`                                                                                                                      |

Most scalar functions distribute across lists and propagate nulls. List-oriented functions instead operate on the collection as a whole. That distinction matters when an expression receives a multivalued source slot.

The `uuid5(namespace, name)` function provides deterministic name-based UUID generation in 0.5.4. This is distinct from the automatic content-derived identifier minting introduced in the 0.6 prerelease.

### 4.3 Dependencies between derived slots

A particularly useful capability is `slot("name")`, which accesses the value of a target slot already computed by the current class derivation.

Slot derivations execute in declaration order. This means an earlier slot can define an intermediate quantity that later derivations reuse.

Setting `hide: true` allows the intermediate value to participate in expressions without appearing in the output instance or derived schema.

This can eliminate duplicate calculations and avoid embedding complex logic repeatedly into downstream fields. The tradeoff is that dependency ordering is explicit: there is no general graph planner that automatically topologically sorts derived slots.

### 4.4 Unrestricted evaluation

`unrestricted_eval=True`, or CLI `--unrestricted-eval`, permits fallback to an `asteval` interpreter when the restricted evaluator cannot process an expression. It is used for more expressive Python-style transformations, including constructs outside the supported restricted subset.

This changes both expressiveness and the trust model. Unrestricted expressions should be treated as executable transformation logic rather than harmless declarative metadata. The 0.5.4 release specifically corrected enum expressions that previously bypassed this option.

Sources:

[https://linkml.io/linkml-map/api/expressions/](https://linkml.io/linkml-map/api/expressions/?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/eval_utils.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/eval_utils.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+1

## 5. Value mappings, enumeration semantics, and units

### 5.1 Literal and expression-based value mappings

`value_mappings` allows source values to be translated using a table of known correspondences. `expression_mappings` can evaluate an expression for a particular incoming value.

At runtime, literal value mappings take precedence over expression mappings for the same source key. If neither mapping has a matching key, the current slot-mapping path returns `None`; it does not implicitly preserve the input value.

Mapping keys are matched against the string representation of source values. Therefore numeric, Boolean, and other YAML-looking keys should be quoted to prevent YAML parsing from changing their types.

This mechanism is useful for deterministic classification, categorical recoding, and known vocabulary translations. Conditional expressions are more appropriate when the mapping depends on several fields or a computed predicate.

### 5.2 Enum derivation and permissible-value translation

`EnumDerivation` operates at the vocabulary level rather than merely recoding an arbitrary string slot.

A target permissible value can declare one or more source permissible values through `PermissibleValueDerivation.populated_from`. This supports many-to-one normalization, such as several legacy labels mapping to a canonical category.

An enum can also have an expression-based derivation. `mirror_source` provides pass-through behavior when an explicit mapping is absent.

The executor can recognize enum ranges referenced through `any_of` constraints and recurse through multivalued enum values.

The important distinctions are:

- Enum mapping concerns permissible-value semantics; slot-level mapping concerns the immediate derived value.
- Many-to-one mappings lose information and therefore do not possess a unique inverse.
- `expression_to_value_mappings` is present in the metamodel, but the 0.5.4 enum execution path principally handles `expr` and permissible-value derivations; the existence of a metamodel field alone is not evidence of runtime handling.
- Canonicalizing arbitrary values against target enum `meaning`, `title`, and aliases is a 0.6 prerelease capability, not the stable 0.5.4 behavior.

### 5.3 Unit conversion

Unit conversion is more substantial than a numeric multiplier.

`UnitConversionConfiguration` can specify explicit source and target units, unit schemes, and structured source/target value fields. It can infer the source unit from the source LinkML slot definition and compare it with any unit specified in the transformation.

The implementation uses `pint` and `ucumvert` for unit handling. Source declarations can include UCUM codes, IEC 61360 codes, or conventional symbols. Incompatible dimensions and undefined units raise conversion errors.

For structured measurements, the configuration can identify `source_unit_slot` and `source_magnitude_slot`, then emit a result using `target_unit_slot` and `target_magnitude_slot`. This allows transformations between scalar measurements and explicit magnitude/unit representations.

`none_if_non_numeric` offers an opt-in path for returning null when the magnitude is not numeric, instead of failing the transformation. A mismatch between a value's declared unit and the schema's expected unit remains a separate correctness concern.

Because unit conversion is declared in the mapping and reflected in derived schema metadata, it can serve as a reusable semantic contract rather than an undocumented arithmetic operation.

### 5.4 Offsets and contextual numeric transformations

`Offset` supports deriving a value from a source baseline plus or minus a scaled field from the same record:

\\[ \text{result}=\text{baseline}\pm (\text{offset\\\_value}\times\text{offset\\\_field}) \\]

This addresses a recurring problem in longitudinal, measurement, and relative-coordinate data. Unlike a generic expression, the computation has structured metadata describing the baseline relationship and direction.

Sources:

[https://linkml.io/linkml-map/api/functions/](https://linkml.io/linkml-map/api/functions/?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/functions/unit_conversion.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/functions/unit_conversion.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map

## 6. Structural transformations and collection representations

### 6.1 Recursive object transformation

`ObjectTransformer` maps objects recursively, using source-slot ranges and class derivations to determine whether a value is a scalar, enum, structured child, or multivalued collection.

Nested `class_derivations` can construct target objects rather than merely copying the source's nested dictionary. This is particularly useful for normalizing differently shaped source models into a common target hierarchy.

When multiple nested class derivations contribute to a multivalued target slot, their outputs are collected in a list. For a single-valued slot, the executor selects the first derived object.

A nested class derivation may also source its data from another table, in which case relational join resolution participates in object construction.

### 6.2 Collection cardinality and representation

The library distinguishes cardinality from collection shape.

`cast_collection_as` can request single-valued, multivalued, list-shaped, or dictionary-shaped representations. `dictionary_key` converts a list of structured objects into a keyed dictionary and supports the reverse direction when an appropriate identifier is available.

`stringification` can collapse a list into a single string using a delimiter or JSON/YAML serialization. Its `reversed` setting supports splitting or parsing the string back into multiple values.

| Transformation          | Primary use                                         | Information risk                                                 |
| ----------------------- | --------------------------------------------------- | ---------------------------------------------------------------- |
| Scalar → list           | Adapt a single occurrence to a multivalued contract | Generally straightforward                                        |
| List → scalar           | Adapt a list to a single-valued field               | Multiple values can raise errors unless stringified              |
| List → keyed dictionary | Build compact keyed object collections              | Duplicate keys overwrite earlier objects                         |
| Dictionary → list       | Restore object collections                          | Identifier restoration depends on schema metadata                |
| List → delimited string | Interchange with flat text formats                  | Delimiter collisions and escaping can destroy reversibility      |
| List → JSON/YAML string | Preserve a structured collection in a scalar field  | Retains serialized content but changes its type and queryability |

The system does not make these transformations automatically lossless. Inversion is only sound when the chosen representation retains enough information.

### 6.3 Wide/long pivoting

The stable implementation includes both directions of EAV reshaping:

MELT: A wide object with multiple attributes becomes a sequence of variable/value records, with optional identifier fields retained.

UNMELT: A record or collection of EAV-shaped records becomes a wide object, dynamically generating attribute names.

`PivotOperation` provides `direction`, `variable_slot`, `value_slot`, `source_slots`, `id_slots`, `unit_slot`, `slot_name_template`, `unmelt_to_class`, and `unmelt_to_slots`.

The optional unit field can participate in target slot naming, enabling measurement variables to distinguish different units.

The implementation has consequential limits: duplicate variables in an UNMELT collection are overwritten by the last encountered value, and target-schema slot checks can warn rather than strictly prohibit unknown generated names. This is a structural pivot facility, not a full relational pivot engine with aggregation.

The metamodel also declares `AggregationOperation` and `GroupingOperation`, but 0.5.4's `ObjectTransformer` does not implement a general configurable grouped-aggregation pathway for them.

Primary source: [https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/pivot.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/pivot.py?utm_source=chatgpt.com)

## 7. Relational joins, cross-class lookups, and reference resolution

This is one of the most architecturally significant capability families introduced and extended in recent releases.

### 7.1 Three reference mechanisms

| Mechanism             | Source shape                                            | Resolution                                                         |
| --------------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| Inline traversal      | Nested dictionaries/objects in the current record       | Dot-path traversal through already-present values                  |
| Foreign-key traversal | References to related objects in a structured container | `ObjectIndex` resolves referenced entities using the LinkML schema |
| Cross-table joins     | Separately loaded tabular files                         | Explicit or synthesized joins resolved through DuckDB              |

These pathways address different data representations and should not be conflated.

Inline traversal uses expressions such as `dataset.title` when the nested object is already within the source value. Multivalued inline traversals have limitations where an intermediate list needs a sibling class derivation.

Foreign-key traversal depends on schema relationships and an indexed source object graph. Python callers can populate the index using `ObjectTransformer.index()`. The framework can then traverse relationships by identifier instead of requiring manual dictionary-building.

Cross-table joins describe how separate classes or tables relate, using `joins`, `source_key`, `lookup_key`, or the equal-column shorthand `join_on`.

### 7.2 Implicit join synthesis

The normalizer can infer joins from cross-table references appearing in dotted `populated_from` values, expressions, and nested class derivations.

For example, when a target class derives from `Visit`, an expression referring to `Participant.birth_year` may cause a join to `Participant` to be synthesized if an unambiguous shared key is inferable from the schema.

This removes boilerplate for well-modeled relationships. It does not imply that any arbitrary pair of tables can safely be joined; ambiguous or missing relationships require explicit mapping information.

An important boundary is that joins can only be hosted by `ClassDerivation`. Cross-table references inside derivations without an enclosing class context cannot be treated as general relational queries.

### 7.3 Set-based DuckDB join engine

In 0.5.4, eligible file-based joins are executed through a DuckDB set-based engine.

The execution sequence is:

Primary table + related tables

CSV / TSV / JSON files

DuckDB set-based joins

Matched rows represented as nested STRUCT values

Python ObjectTransformer

Expressions, enum logic, units, recursive target construction

Streamed target records

This reduces repeated per-record lookup overhead, while retaining the Python transformation engine as the semantic executor.

However, its optimization is deliberately conservative. The set-based path requires file-loadable tables in supported DuckDB-readable formats, joins on keys available in the primary, and no unsupported multi-hop foreign-key chains. Other cases use the per-row lookup fallback.

The current join execution has an important cardinality limitation: a joined table is reduced to at most one matching row per key. It is not a one-to-many collection aggregation operation. The code does not impose a fully deterministic tie-breaking order on duplicate matches, so nonunique join keys can create ambiguous results.

Sparse join misses suppress absent nested objects instead of manufacturing empty child objects. A missing joined field may be null without the containing target object necessarily being created.

Architectural implication: linkml-map can delegate relational matching to DuckDB without having to compile every mapping expression into SQL. The cost is Python-side transformation for each resulting record.

Primary sources:

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/join_engine.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/join_engine.py?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/engine.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/engine.py?utm_source=chatgpt.com)

[https://linkml.io/linkml-map/writing-specs/](https://linkml.io/linkml-map/writing-specs/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+1

## 8. Execution interfaces, streaming, and data formats

### 8.1 Python execution

The stable programmatic interface is based on `ObjectTransformer`, with a loaded source `SchemaView` and mapping specification.

Key entry points include `load_source_schema()`, `load_transformer_specification()`, `load_transformer_specifications()`, `create_transformer_specification()`, `index()`, `derived_specification`, and `map_object()`.

The transformer accepts dictionaries, Pydantic objects, and LinkML runtime model instances in applicable paths. It constructs mapped dictionary results and can use LinkML-derived classes for recursive and typed transformations.

For tabular/directory processing, `transform_spec()` provides an iterator over transformed row dictionaries using `DataLoader`.

The declarative specification is therefore usable from Python code without shelling out to the CLI.

### 8.2 File-oriented execution

The `linkml-map map-data` command supports a single structured YAML/JSON object, individual CSV/TSV datasets, or a directory containing class-named data files.

For directory processing, source-file stems identify source classes. That convention is consequential: in 0.5.4 a mismatched filename/source-type combination can yield no matching class derivation and therefore empty output rather than a failure. The 0.6 prerelease explicitly addresses this behavior.

`--chunk-size` controls row batches for streaming output, with a default of 1,000. Streaming can bound output-side buffering; it should not be interpreted as a guarantee that joins, indexed objects, schema metadata, or intermediate DuckDB state consume constant memory.

The TSV/CSV loaders use LinkML's delimited input machinery and reuse a source `SchemaView` to select numeric fields appropriately. This avoids treating every numeric-looking identifier as a numeric measurement.

### 8.3 Output format capabilities

| Format    | Characteristic                                                         |
| --------- | ---------------------------------------------------------------------- |
| YAML      | Human-readable structured output, appropriate for model instances      |
| JSON      | Structured machine-readable records or collections                     |
| JSONL     | Stream-friendly record-per-line interchange                            |
| CSV / TSV | Flat tabular interchange; nested values require careful representation |
| Parquet   | Columnar output retaining nested `STRUCT` and `STRUCT[]` data          |
| DuckDB    | Database artifact with mapped records stored in a named table          |

Parquet and DuckDB output were added in 0.5.4. These are especially useful because output need not be flattened merely to remain accessible to a columnar analytical system.

Nested output in Parquet/DuckDB can retain structured fields rather than being converted to opaque serialized strings. Nevertheless, this is not a promise that every LinkML type, enum, union, or constraint will map losslessly to a specific Arrow schema. The implementation's writing and type-inference behavior remains relevant.

`-O/--additional-output` can create multiple output artifacts from a single transformation pass. DuckDB output supports `--table-name`, and separate runs can populate different tables in one database.

Boundary: The library has DuckDB-backed writers and readers, but it should not be assumed to expose a complete public PyArrow `Table` transformation API. Its principal mapping execution still passes through Python object representations.

### 8.4 Error handling

The default behavior is fail-fast on transformation exceptions. `--continue-on-error` allows row-level errors to be reported while other records are processed, and the command still indicates an unsuccessful run through a nonzero exit status when errors occurred.

`TransformationError` can carry class, slot, and row context. Programmatic streaming supports an `on_error` callback.

This provides useful failure isolation for batch operations, but is not transactional exactly-once processing or a full rejected-record database.

Sources:

[https://linkml.io/linkml-map/cli/](https://linkml.io/linkml-map/cli/?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/loaders/data_loaders.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/loaders/data_loaders.py?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/writers/output_streams.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/writers/output_streams.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map+1

## 9. Target-schema derivation, profiling, and model evolution

`SchemaMapper` generates a LinkML target schema from a source schema and transformation specification.

This is a distinctive capability: it lets the same declarative artifact describe both how instances change and what the transformed model should look like.

The mapper can construct target classes and attributes, change names and ranges, apply unit metadata, set collection representations, generate enum definitions, and adjust inheritance relationships.

### Schema profiling through copy directives

`CopyDirective` permits selective copying of source schema elements using `copy_all`, `exclude_all`, `include`, and `exclude`.

This supports schema specialization and profiling without rebuilding every class or field definition manually.

For example, a broad source schema could be mapped into a narrower schema that preserves selected classes and slots, renames several elements, and changes their representation.

`target_definition` and `overrides` offer further control over derived elements, including properties not otherwise exposed as dedicated transformation attributes.

### Inheritance rewriting and merged target classes

`SchemaMapper` tracks source-to-target class mappings to rewrite inheritance relationships when possible.

If multiple source class derivations target the same class name, the schema mapper merges the resulting target attributes. On conflicting attribute definitions, a later derivation wins with a warning.

This schema-level merging should not be mistaken for runtime merging of multiple records into one entity. Those are different operations.

Where a source class maps to multiple target classes, inference of a unique rewritten parent can become ambiguous.

### Source-schema patching

`source_schema_patches` can augment a source LinkML schema before mapping, particularly when schemas generated from tabular data lack foreign-key ranges or other semantic relationships.

The mapping can therefore carry locally required semantic refinements without changing the external schema document.

This is powerful for reproducible transformations, but the patch is still a substantive interpretation of the source model. A wrong foreign-key range can lead to wrong traversal or join behavior.

### Limits

Derived schemas can contain dangling references or other invalid LinkML constructions. The upstream CLI explicitly describes this pathway as incomplete, so successful derivation does not establish that the resulting schema is fully valid or that every mapped output conforms to it.

Source: [https://linkml.io/linkml-map/api/inference/](https://linkml.io/linkml-map/api/inference/?utm_source=chatgpt.com)

Tagged implementation: [https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/inference/schema_mapper.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/inference/schema_mapper.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map

## 10. Mapping inversion and reversibility

`TransformationSpecificationInverter` can derive a reverse transformation from a forward mapping.

It operates on mapping structure, not on observed output data. Consequently, it can invert only transformations whose information requirements and correspondence are sufficiently explicit.

Supported or partially supported inversion mechanisms include class renames, direct slot renames, simple variable-reference expressions, enum mappings with unique correspondences, compatible unit conversions, and reversible collection stringification configurations.

The inverter also considers source-schema collection metadata when reversing dictionary/list representation changes.

The critical limitation is semantic, not merely computational: arbitrary expressions are not algebraically inverted. Computations such as aggregations, information-losing string processing, conditional choices, and many-to-one enum mappings generally cannot be reversed uniquely.

In strict mode, unsupported inversion raises `NonInvertibleSpecificationError`. In non-strict mode, some noninvertible slot derivations can be omitted, producing an intentionally incomplete reverse mapping.

Hidden intermediate slots are excluded from inversion because they have no corresponding output field.

The existence of `invert()` therefore does not guarantee a round-trip identity transformation. It offers an explicit starting point for reversible mappings and helps expose information loss.

Primary source: [https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/inference/inverter.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/inference/inverter.py?utm_source=chatgpt.com)

## 11. Validation, normalization, and specification governance

### Structural validation

The `validate_spec()` and `validate_spec_file()` APIs validate the representation of mapping specifications against the transformation metamodel's JSON Schema.

Load-time normalization can also identify deprecated forms and migrate compatible legacy structures.

### Semantic validation

`validate_spec_semantics()` goes further by cross-referencing the mapping against the source and, when available, target schemas.

Its checks include unresolved class and slot names, invalid source references, expression dependencies, class inheritance relationships, and join configuration.

The CLI `validate-spec` provides a directly usable validation entry point, including `--source-schema`, `--target-schema`, `--strict`, `--merge`, `--entity`, `--emit-spec`, and `--list-entities`.

These features are especially useful for independently inspecting or automating mapping artifacts:

| Operation             | Purpose                                                                     |
| --------------------- | --------------------------------------------------------------------------- |
| `validate-spec`       | Detect structural and semantic errors before execution                      |
| `--strict`            | Promote warnings to errors                                                  |
| `--merge`             | Validate combined mapping specifications                                    |
| `--entity`            | Restrict mapping inspection/execution to selected derivations               |
| `--list-entities`     | Discover available class derivations without executing transformations      |
| `--emit-spec`         | Persist the resolved/merged/filtered specification for inspection           |
| `--continue-on-error` | Report record-level transformation failures without immediately terminating |

The `map-data` command also performs non-gating preflight validation. This is useful for diagnostics but is not equivalent to demanding validation success before processing.

### Specification composition versus merging

`load_transformer_specifications()` can merge files or directories of mapping specifications.

The merge strategy appends class derivations in order, unions enum and top-level slot derivations by name, rejects conflicting enum/slot entries, and takes the first non-null value for scalar metadata.

This is composition by specification aggregation, not arbitrary mathematical composition of functions \\(A \to B\\) and \\(B \to C\\). There is no general guarantee that chained transformations can automatically be collapsed into one equivalent optimized specification.

### Validation boundary

Static validation can reveal inconsistent names, missing references, and some type mismatches. It cannot prove that every input instance is valid, every expression succeeds, every join is unique, or every output instance satisfies all target constraints.

That distinction is important because the full LinkML validation ecosystem has its own instance-validation responsibilities.

Sources:

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/validator.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/validator.py?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/spec_merge.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/spec_merge.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

## 12. Extensibility and compilation

### 12.1 User-defined safe expression functions

The `@safe_function` decorator provides a supported extension surface for restricted expressions.

Tagged Python functions can be loaded through CLI `--functions` or programmatically supplied through `ObjectTransformer.extension_functions`.

The extension system includes collision detection, optional deliberate overriding of built-in functions, and a `distributes` option controlling whether a function broadcasts across lists.

This is valuable for extending a declarative mapping vocabulary with domain-specific normalization or calculation primitives, without switching the whole specification to unrestricted evaluation.

There are two important qualifications:

Safety is declarative, not verified. The decorator asserts that a function is appropriate for the restricted namespace; it does not prove purity, bounded execution, determinism, or absence of I/O.

Extension loading is executable Python import. An extension file itself must be trusted. This should not be confused with a secure sandbox for arbitrary third-party code.

Source: [https://linkml.io/linkml-map/api/extensions/](https://linkml.io/linkml-map/api/extensions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map



### 12.2 Compiler interfaces

The compiler subsystem exposes a `Compiler` abstraction for translating transformation specifications into alternative representations.

| Compiler           | Capability                                     | Maturity/boundary                                                                 |
| ------------------ | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| `PythonCompiler`   | Generates Python transformation code           | Available; generated-code semantics should be checked against `ObjectTransformer` |
| `MarkdownCompiler` | Generates human-readable mapping documentation | Useful for review and mapping documentation                                       |
| `GraphvizCompiler` | Produces mapping dependency/class diagrams     | Programmatic visualization capability                                             |
| `SQLCompiler`      | Produces limited SQL statements and schema DDL | Experimental, with substantial unsupported derivation semantics                   |

The CLI `compile` command supports Python and Markdown targets. Graphviz is exposed programmatically, while SQL compilation is not a full production-equivalent CLI target.

### 12.3 SQL compilation: important limitation

`SQLCompiler` currently handles relatively elementary source-to-target projections and some stringification. In the stable source it does not faithfully compile arbitrary `expr`, constants, value mappings, unit conversions, or complex recursive class derivations.

`DuckDBTransformer.map_object()` is also explicitly unimplemented.

This means the available SQL compiler cannot be treated as a complete SQL execution engine for the declarative language.

By contrast, the DuckDB join engine described earlier is a real and useful optimization because it performs joins and then delegates the remaining transformations to Python.

The underlying transformation model discusses potential compilation to SPARQL, R2RML, and other semantic mapping systems. These are architectural possibilities, not established comprehensive backends in 0.5.4.

Sources:

[https://linkml.io/linkml-map/api/compiler/](https://linkml.io/linkml-map/api/compiler/?utm_source=chatgpt.com)

[https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/compiler/sql_compiler.py](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/compiler/sql_compiler.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

LinkML-Map

## 13. Semantic and operational boundaries

The following distinctions have a large effect on the reliability of a transformation system.

| Area                        | Stable 0.5.4 behavior and consequence                                                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Target datatype enforcement | Explicit `SlotDerivation.range` influences coercion, but merely supplying a target schema does not comprehensively coerce constants and expression results to the target range |
| Null versus missing         | Unknown fields, absent join matches, declared missing-value sentinels, and expression null propagation are related but not identical cases                                     |
| Empty output                | A dataset that matches no class derivation can complete without producing records                                                                                              |
| Join cardinality            | File-based joins effectively take one matching secondary record, not a full one-to-many aggregate                                                                              |
| Join determinism            | Duplicate lookup keys do not have a guaranteed application-level tie-breaking rule                                                                                             |
| Expression security         | Restricted expressions are narrower than unrestricted Python, but extension code must still be trusted                                                                         |
| Runtime dependency ordering | `slot()` reads previously derived values; declaration order therefore matters                                                                                                  |
| Collection coercion         | Converting multivalued data into scalar or keyed forms can be lossy                                                                                                            |
| Enum translation            | Unmatched values may become null or pass through, depending on the derivation mechanism                                                                                        |
| Schema inheritance          | Single-object inheritance/mixin mapping is supported; tabular inheritance application is corrected in the 0.6 prerelease                                                       |
| Mapping inversion           | Only sufficiently invertible structures and operations can be reversed                                                                                                         |
| Schema derivation           | Generated target schemas are not guaranteed valid without subsequent schema validation                                                                                         |
| Compiler parity             | Python object execution covers substantially more mapping semantics than SQL compilation                                                                                       |
| Streaming                   | Row chunks reduce buffering, but joined/indexed datasets and writer state may still consume material memory                                                                    |

One particularly consequential detail is that `ObjectTransformer` is an interpreter of a structured specification rather than a cost-based query optimizer. The DuckDB path has its own eligibility checks, but no general mechanism turns arbitrary transformation expressions into an optimized relational plan.

This distinction sets realistic expectations for both performance and execution semantics.

## 14. The 0.6 prerelease: changes that must not be backported conceptually

As of October 29, 2026, 0.6.0-rc1 is a prerelease, dated October 23. Its changes are substantial enough to matter when reading the current documentation.

| Capability                      | Stable 0.5.4                                                             | 0.6.0-rc1                                                                                      |
| ------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Target range coercion           | Incomplete for expressions/constants and implicit target types           | Coerces to the target schema's range unless explicit spec range overrides                      |
| Target enum normalization       | Explicit mapping behavior                                                | Normalizes keys, aliases, titles, and meanings to permissible-value keys                       |
| Decimal handling                | No complete end-to-end exact-decimal guarantee                           | Exact decimal representation across transformations and serializers                            |
| Identifier minting              | Explicit expression-based generation, including `uuid5`                  | Opt-in deterministic content-derived identifiers via `mint_ids`                                |
| Python setup                    | `ObjectTransformer` plus explicit loading methods; `Session` also exists | Constructor accepts specs and schemas as paths, dictionaries, or objects; `Session` deprecated |
| Inheritance during tabular runs | Parent derivation application incomplete                                 | Parent slots and joins incorporated                                                            |
| No matching input dataset       | Can silently produce empty output                                        | Explicit error                                                                                 |
| Stream-writer legacy functions  | Deprecated but present                                                   | Removed                                                                                        |
| Validation                      | Structural and semantic checks                                           | Expanded target enum/range and join checks                                                     |

The automatic identifier mechanism is especially worth distinguishing from persistent entity identity. Content-derived IDs change if the content changes; they are appropriate for some derived artifacts but cannot universally replace stable natural or assigned identifiers.

Likewise, exact-decimal preservation and target-based type coercion can change output values, not merely improve validation diagnostics.

Source: [https://github.com/linkml/linkml-map/releases/tag/v0.6.0-rc1](https://github.com/linkml/linkml-map/releases/tag/v0.6.0-rc1?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 15. Ecosystem integrations and capability boundaries

The surrounding LinkML ecosystem contributes important capabilities that are not all implemented by linkml-map itself.

| Library/tool         | Relationship to linkml-map                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| LinkML               | Supplies the modeling language, schema definitions, generators, and broader validation ecosystem                         |
| linkml-runtime       | Supplies `SchemaView`, schema metamodel classes, object-model infrastructure, and schema introspection                   |
| schema-automator     | Can infer schemas from existing data sources; linkml-map can consume and patch those schemas                             |
| Pydantic             | Underlies generated transformation-model structures and supports typed Python model representations                      |
| simpleeval / asteval | Provide restricted and more permissive expression execution, respectively                                                |
| pint / ucumvert      | Supply underlying unit-conversion infrastructure                                                                         |
| DuckDB               | Executes supported joins and writes Parquet/DuckDB artifacts; not a complete alternative mapping executor                |
| Jinja2 / Graphviz    | Support code/documentation generation and mapping visualizations                                                         |
| SSSOM                | Related standard for sharing semantic correspondences, with some compatibility within the wider LinkML mapping ecosystem |

The SSSOM distinction deserves particular attention. A SSSOM mapping generally expresses a semantic correspondence between identifiers or entities, including relationship predicates and evidence metadata. A `TransformationSpecification` expresses executable transformations of data structures and values.

Those concepts can be related, and linkml-map's documentation identifies compatibility with SSSOM, but SSSOM correspondence metadata is not automatically an executable LinkML transformation, and linkml-map should not be assumed to provide a complete standalone SSSOM import/export backend.

Separately, the broader LinkML package has a `gen-sssom` generator for representing schema correspondences as SSSOM mappings.

Source: [https://linkml.io/linkml/generators/sssom.html](https://linkml.io/linkml/generators/sssom.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://linkml.io\&sz=32)

linkml documentation



### Architectural opportunities

Several interactions are particularly valuable beyond using the library as a simple data converter.

A mapping specification as a shared semantic contract. The same artifact can guide execution, document derivation logic, supply inferred target-schema information, and support static validation. This can reduce discrepancies between transformation code and schema documentation.

Schema-aware ETL without fully custom relational plumbing. LinkML relationships, explicit/implicit join derivation, DuckDB lookup execution, and recursive Python mapping can cover substantial transformation workloads without independently implementing every lookup/index and object-construction layer.

Declarative profiling and model evolution. `CopyDirective`, `target_definition`, class/slot derivations, inheritance, and `SchemaMapper` combine to support tailored target models while retaining traceability back to source elements.

Mapping introspection and governance. The transformation metamodel, metadata fields, normalization, validators, compiler representations, and `--emit-spec` make mappings amenable to external inspection and analysis. This is more structured than extracting transformation intent from arbitrary Python source.

These advantages remain conditional on the required operations being represented by the implemented semantics. Generalized aggregations, arbitrary SQL optimization, or fully reversible transformations require additional capabilities beyond the present stable executor.

## 16. Primary-source navigation

For precise future investigation, these are the most consequential primary sources. Each URL is provided as plain text.

| Subject                                  | Source                                                                                                                                              |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Documentation and architectural overview | [https://linkml.io/linkml-map/](https://linkml.io/linkml-map/?utm_source=chatgpt.com)                                                               |
| Authoring mapping specifications         | [https://linkml.io/linkml-map/writing-specs/](https://linkml.io/linkml-map/writing-specs/?utm_source=chatgpt.com)                                   |
| Command-line features                    | [https://linkml.io/linkml-map/cli/](https://linkml.io/linkml-map/cli/?utm_source=chatgpt.com)                                                       |
| Transformation metamodel                 | [https://linkml.io/linkml-map/schema/](https://linkml.io/linkml-map/schema/?utm_source=chatgpt.com)                                                 |
| Expression evaluator and semantics       | [https://linkml.io/linkml-map/api/expressions/](https://linkml.io/linkml-map/api/expressions/?utm_source=chatgpt.com)                               |
| Functions and unit conversion            | [https://linkml.io/linkml-map/api/functions/](https://linkml.io/linkml-map/api/functions/?utm_source=chatgpt.com)                                   |
| Extension functions                      | [https://linkml.io/linkml-map/api/extensions/](https://linkml.io/linkml-map/api/extensions/?utm_source=chatgpt.com)                                 |
| Schema inference and inversion           | [https://linkml.io/linkml-map/api/inference/](https://linkml.io/linkml-map/api/inference/?utm_source=chatgpt.com)                                   |
| Compiler infrastructure                  | [https://linkml.io/linkml-map/api/compiler/](https://linkml.io/linkml-map/api/compiler/?utm_source=chatgpt.com)                                     |
| Conformance suite                        | [https://linkml.io/linkml-map/specification/compliance/](https://linkml.io/linkml-map/specification/compliance/?utm_source=chatgpt.com)             |
| Stable v0.5.4 source                     | [https://github.com/linkml/linkml-map/tree/v0.5.4](https://github.com/linkml/linkml-map/tree/v0.5.4?utm_source=chatgpt.com)                         |
| Stable v0.5.4 release notes              | [https://github.com/linkml/linkml-map/releases/tag/v0.5.4](https://github.com/linkml/linkml-map/releases/tag/v0.5.4?utm_source=chatgpt.com)         |
| Development/prerelease changes           | [https://github.com/linkml/linkml-map/releases/tag/v0.6.0-rc1](https://github.com/linkml/linkml-map/releases/tag/v0.6.0-rc1?utm_source=chatgpt.com) |

### Synthesis

The most distinctive feature of `linkml-map` is not any individual conversion operation. It is the combination of a schema-aware transformation language, an executable Python reference engine, structural and semantic validation, target-schema derivation, and mapping introspection.

In stable 0.5.4, the strongest implemented capability territory is recursive structured-object transformation, vocabulary and unit normalization, explicit and inferred cross-table lookups, streamed file processing, and schema profiling. The recent DuckDB integration is consequential because it optimizes relational matching without sacrificing the richer Python mapping semantics.

The principal limitation is the difference between the breadth of the declarative metamodel and the breadth of its implemented execution backends. Treating that boundary precisely is essential to using the framework as a dependable semantic transformation layer rather than assuming it is already a general-purpose query planner, aggregation engine, or complete bidirectional schema compiler.

# linkml-map — Capability and Implementation Addendum

Research date: November 1, 2026\
Stable baseline: v0.5.4 (August 26, 2026)\
Additional version coverage: v0.6.0-rc1 (prerelease, October 23, 2026)

This addendum supplements the existing comprehensive LinkML-Map overview with additional implemented functionality, less obvious execution interfaces, operational mechanisms, and version-sensitive behavioral distinctions. It deliberately avoids repeating the architectural and capability discussions already covered in the main guide.

Unless explicitly marked otherwise, the capabilities described below are verified against the v0.5.4 tagged implementation, upstream tests, or release documentation. The 0.6 release-candidate features are treated separately and should not be attributed to the stable release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 1. Declarative normalization of missing-value sentinels

### `SlotDerivation.missing_values`

LinkML-Map can normalize source-specific missing-value codes directly within a slot derivation, avoiding a separate preprocessing layer for common sentinel conventions.

The `missing_values` property identifies source values that should be interpreted as absent rather than treated as meaningful data. It accepts a single sentinel or a collection of sentinels.

For example:

```
class_derivations:
  Measurement:
    slot_derivations:
      temperature:
        populated_from: raw_temperature
        missing_values: [-9, 999, 9999]
        range: float
```

When an incoming value matches a declared sentinel, the stable executor substitutes `None` before downstream processing.

The matching mechanism uses string equality rather than strict Python type equality. Consequently, a numeric sentinel declared as `999` can match either the integer `999` or the string `"999"` obtained from a delimited source. The comparison is still exact at the string level: `"999"` and `"999.0"` are not equivalent merely because they represent the same numeric quantity.

### Execution semantics and composition

In the supported source-value pathways, normalization occurs before value mappings, offset calculations, and range or datatype coercion.

This sequencing is consequential. A special code representing an unavailable measurement can be converted to null before arithmetic or a subsequent categorical mapping attempts to interpret it.

The feature works with explicitly named source slots through `populated_from`, implicitly sourced same-name slots, and slots defined inside nested class derivations.

It does not operate as a universal null-normalization pass over every possible derivation mechanism. In v0.5.4, the same sentinel handling is not automatically applied to arbitrary `expr`, constant `value`, or alternative `sources` branches, and the implementation does not recursively inspect each element of an arbitrary collection for sentinel matches.

This capability is distinct from `UnitConversionConfiguration.none_if_non_numeric`. The former encodes known source-data conventions for absence; the latter determines how unit conversion handles nonnumeric magnitudes.

Together with value mappings and null-aware expressions, `missing_values` allows source-specific data interpretation to remain part of a declarative, inspectable transformation specification rather than being scattered across custom preprocessing functions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary sources

`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/object_transformer.py`

`https://github.com/linkml/linkml-map/blob/v0.5.4/tests/test_transformer/test_slot_derivation_features.py`

## 2. Heterogeneous source-class unification

### Multiple derivations producing one target class

A transformation specification can contain multiple `ClassDerivation` instances sharing the same target class name, each populated from a different source class.

This enables independently modeled source types to converge on a common target representation without requiring separate procedural dispatch and mapping implementations.

An illustrative example:

```
class_derivations:
  - name: Event
    populated_from: Acquisition
    slot_derivations:
      event_id:
        populated_from: id
      event_type:
        value: acquisition
      timestamp:
        populated_from: started_at

  - name: Event
    populated_from: QualityCheck
    slot_derivations:
      event_id:
        populated_from: id
      event_type:
        value: quality_check
      timestamp:
        populated_from: checked_at
```

Both derivations produce records in the `Event` target model, despite using different source classes and source attributes.

The list representation of `class_derivations` is essential for this pattern. A dictionary keyed by target class name cannot preserve repeated names, whereas a list can hold several independently configured derivations targeting the same class.

This capability is explicitly tested upstream with `Acquisition`, `QualityCheck`, and `Assembly` source types mapping into one common event representation. It has been available since the v0.4 development series and is present in v0.5.4.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://data.safetycli.com\&sz=32)

data.safetycli.com



### Runtime unification versus entity consolidation

For each source record, the applicable class derivation constructs an instance of the shared target representation. Source-specific constants can introduce discriminator attributes, while field projections normalize differently named source attributes.

When processing multiple source datasets, these derivations can contribute records to the same logical target class.

This is not a relational union with automatic deduplication, an entity-resolution operation, or a many-to-one consolidation of records. Each input record remains independently mapped.

It is also distinct from `SchemaMapper` combining target-schema definitions. Schema-level merging creates a coherent class definition; runtime unification creates individual records conforming to that common model.

The combination supports declarative normalization of heterogeneous events, observations, activities, and transactions while preserving the provenance of each input category through explicit target attributes.

Primary source

`https://github.com/linkml/linkml-map/blob/v0.5.4/tests/test_transformer/test_multiple_derivations_same_target.py`

## 3. Namespace-aware identifier conversion

### CURIE expansion and URI compression

The base `Transformer` provides `curie_converter`, `expand_curie()`, and `compress_uri()` for converting identifiers between compact CURIE representations and full URIs.

The converter is constructed using prefix declarations from the source LinkML `SchemaView` and the transformation specification. It uses the underlying `curies` package rather than maintaining a separate implementation of prefix expansion and contraction.

Given a suitable prefix declaration, an identifier such as `EX:12345` can be expanded into its full namespace URI and converted back to compact form.

This differs fundamentally from `value_mappings` or `EnumDerivation`: prefix conversion changes an identifier's representation without intentionally changing the entity it denotes, whereas vocabulary mappings may express correspondences between distinct identifiers or permissible values.

### Primitive-type transformation

`ObjectTransformer.map_object()` additionally contains a datatype-level pathway for mapping recognized LinkML primitive types. When invoked with appropriate source and target types, it supports conversions involving `string`, `integer`, `float`, `double`, `uri`, and `curie`.

URI/CURIE conversion is therefore available as a direct transformation operation, not merely as an auxiliary namespace utility.

The important limitation is that these operations are not automatically applied to every ordinary class slot based only on an identifier-related target range. Primitive-type mapping and class-slot derivation follow different execution pathways.

This functionality can reduce bespoke namespace-normalization code when mappings involve identifiers represented differently across otherwise compatible data models.

Primary sources:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/transformer.py`

`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/object_transformer.py`

## 4. Typed target-object construction

### `ObjectTransformer.transform_object()`

In addition to dictionary-returning `map_object()` operations, LinkML-Map supports construction of instances of explicitly provided target Python model classes.

`transform_object()` accepts a source object represented by a LinkML `YAMLRoot` or Pydantic `BaseModel` and a target class of one of those model types.

The implementation obtains the source object's class name, transforms its attributes with `map_object()`, and instantiates the target class with the resulting dictionary.

Conceptually:

```
mapped = transformer.map_object(    source_obj,    source_type=type(source_obj).__name__,)result = target_class(**mapped)
```

This is an illustration of the method's internal sequence, not a separate required calling convention.

The capability creates a direct interface between declarative mappings and typed Python application models. A transformation need not terminate as an untyped dictionary or an intermediate serialized document when an appropriate target model class already exists.

However, `transform_object()` does not generate the target Python class. It requires one to be supplied. Nor should construction through a LinkML-generated class be assumed to enforce the same constraints as Pydantic validation; the resulting guarantees depend on the target class implementation.

This provides a useful distinction between target-schema derivation, which determines the target model's definition, and typed instance construction, which materializes transformed data using an existing Python model.

Primary source:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/object_transformer.py`

## 5. Programmatic streaming-writer architecture

The package exposes reusable streaming-writer interfaces under `linkml_map.writers.output_streams`. These are more than implementation details of the `map-data` CLI: they allow transformation results to be serialized and distributed through Python without invoking a separate command-line process.

### Writer abstractions

| Interface                       | Capability                                                           |
| ------------------------------- | -------------------------------------------------------------------- |
| `OutputFormat`                  | Enumerates available output representations                          |
| `make_stream_writer()`          | Constructs a format-specific writer                                  |
| `StreamWriter.write_chunk()`    | Serializes an individual batch of mapped objects                     |
| `StreamWriter.process()`        | Processes an iterator of record chunks                               |
| `StreamWriter.finalize()`       | Emits final format-specific content                                  |
| `StreamWriter.finalize_path()`  | Performs postprocessing for filesystem-backed outputs                |
| `MultiStreamWriter.write_all()` | Fans the same sequence of transformed chunks out to multiple writers |

For example, a single iterator of mapped records can produce JSONL and Parquet artifacts through the same writer coordinator:

```
from pathlib import Pathfrom linkml_map.writers.output_streams import (    MultiStreamWriter,    OutputFormat,    make_stream_writer,)writers = MultiStreamWriter([    (        make_stream_writer(OutputFormat.JSONL),        Path("records.jsonl"),    ),    (        make_stream_writer(OutputFormat.PARQUET),        Path("records.parquet"),    ),])writers.write_all(chunks)
```

Here, `chunks` is an iterator yielding lists of mapped dictionaries. The code illustrates the supported interface; it has not been executed as part of this research.

The architectural benefit is that serialization into multiple formats can share one transformation pass, rather than requiring independent source scans and repeated mapping execution.

### Dynamic tabular schemas

`TabularStreamWriter` contains a particularly useful mechanism for variable-shaped records.

It flattens nested dictionary attributes using a configurable separator, defaulting to `__`, and discovers tabular columns as records arrive.

When later records introduce previously unseen columns, the writer tracks the expanded header set. For filesystem-backed outputs, its finalization pathway can rewrite the file to include the complete headers and pad earlier records with empty values.

This permits tabular serialization of heterogeneous mapped records without requiring every possible output column to be discovered upfront.

There is an important distinction between filesystem-backed and externally supplied output streams. A file path allows the writer to repair headers after discovering new columns; a nonrewritable stream such as standard output cannot receive equivalent postprocessing through that mechanism.

### Columnar output materialization

The `ColumnarStreamWriter` base class underlies the Parquet and DuckDB output writers.

Its execution mechanism is a two-stage process:

1. Mapped objects are serialized into an intermediate JSONL file.
2. DuckDB reads that staged JSONL using `read_json_auto` and creates the final Parquet file or DuckDB table.

Nested objects can become DuckDB `STRUCT` values, and lists of structured objects can become `STRUCT[]` columns.

This preserves structured access in the resulting columnar artifact, rather than necessarily flattening every object into independent scalar columns.

However, the output path is not a direct Arrow batch transformation interface. It relies on intermediate serialization, DuckDB type inference, and subsequent materialization.

These mechanics affect disk requirements, finalization costs, and the handling of inconsistent field types across records.

For DuckDB output, the implementation uses `CREATE OR REPLACE TABLE`, with a table name supplied explicitly or derived from the output filename. Separate transformations can populate different tables in one database, while a repeated transformation targeting the same table replaces that table's contents.

### Legacy writer APIs

The stable v0.5.4 release retains deprecated function-based streaming interfaces, while the class-based writer system is the supported replacement.

The v0.6.0-rc1 release candidate removes these legacy functions, making `make_stream_writer()`, `StreamWriter.process()`, and `MultiStreamWriter` the relevant interfaces for both current and forward-compatible integrations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Primary source:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/writers/output_streams.py`

## 6. DuckDB resource configuration and index lifecycle

### Container-aware resource management

The DuckDB-assisted join and lookup infrastructure provides explicit controls for its connection resource configuration.

| Environment variable             | Function                                   |
| -------------------------------- | ------------------------------------------ |
| `LINKML_MAP_DUCKDB_MEMORY_LIMIT` | Overrides DuckDB's memory limit            |
| `LINKML_MAP_DUCKDB_THREADS`      | Controls the DuckDB execution thread count |
| `LINKML_MAP_DUCKDB_TEMP_DIR`     | Selects the temporary-file directory       |

When a memory limit is not explicitly supplied, the implementation can inspect Linux cgroup v1 and v2 memory constraints.

It derives a DuckDB memory budget from the detected container limit, reserving headroom for Python and other execution requirements. When no applicable container memory limit is detected, the connection may retain DuckDB's default memory configuration.

Thread configuration similarly accounts for process CPU affinity when available, rather than always relying on the physical machine's complete CPU count.

A writable temporary directory is configured for operations capable of spilling intermediate state to disk.

These mechanisms matter in constrained environments because DuckDB's resource requirements and the surrounding Python process's resource consumption must coexist.

They do not guarantee an absence of out-of-memory failures, particularly when Python objects, file loading, join results, and DuckDB execution simultaneously consume memory.

Scope limitation: These settings are used by the connection helper shared by the join engine and lookup index. The separate connections created by columnar output finalization should not automatically be assumed to inherit the same resource configuration.

### Lookup-index ownership and cleanup

`LookupIndex` implements context-manager methods and exposes explicit connection cleanup through `close()`.

The index can register file-backed tables, maintain keyed lookup structures, retrieve matching rows, and remove registered tables.

`transform_spec()` also tracks whether the lookup index was created internally or supplied by the caller. When it owns an index, the engine can release that resource after processing; externally supplied indexes remain under caller control.

Index creation is lazy. A class derivation executed entirely through the set-based DuckDB join pathway need not instantiate the separate per-row lookup index.

This distinction reduces unnecessary connection and index state while preserving the fallback mechanism for joins that cannot be executed through the set-based pathway.

The resulting design offers controlled resource ownership without requiring the caller to manually manage every internally created lookup structure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary sources:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/lookup_index.py`

`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/engine.py`

## 7. Directory-oriented transformation orchestration

### `MultiFileTransformer` and instruction models

The `linkml_map.utils.multi_file_transformer` module provides a utility for processing related transformation inputs organized within a filesystem directory.

Its model includes `Instructions`, `Transformation`, and `Step`, allowing a collection of schema references, transformation specifications, source files, and output artifacts to be represented together.

`MultiFileTransformer` can obtain its instructions from an explicit `instructions.yaml` file or infer them using an expected directory structure.

It supports configuration of directories for source schemas, transformation specifications, source data, target schemas, and output data.

During processing, it can invoke `SchemaMapper` to derive a target schema and write it when the target schema file is absent.

This functionality is especially relevant for transformation examples, mapping test suites, and collections of related schema/data conversion scenarios.

It is not equivalent to a general workflow engine, however. The implementation assumes particular directory and filename conventions and performs relatively straightforward sequential processing.

Another consequential detail is that the v0.5.4 utility constructs `ObjectTransformer(unrestricted_eval=True)` internally. The mapping specifications processed through this pathway therefore carry the trust implications of unrestricted evaluation.

The 0.6.0-rc1 release notes also identify a correction to the utility's handling of string-valued output-directory arguments, which could previously cause input paths to be resolved against the wrong directory.

Primary source:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/multi_file_transformer.py`

## 8. Additional expression evaluation semantics

### Combining `expression_mappings` with `slot()`

The `slot()` function can be used inside `expression_mappings` values, not just standalone slot expressions.

This allows source-value-specific expression mappings to reference previously computed target slots, including hidden intermediate values.

For example:

```
slot_derivations:
  _suffix:
    hide: true
    expr: "'_normalized'"

  category:
    populated_from: category_code
    expression_mappings:
      "A": "'alpha' + slot('_suffix')"
      "B": "'beta' + slot('_suffix')"
```

The earlier hidden slot is calculated once for the current record and can be reused by subsequent expression mappings without becoming part of the emitted target representation.

This makes the target-slot environment a compositional mechanism spanning different derivation types, rather than being restricted to ordinary `expr` declarations.

As elsewhere, declaration order controls availability; LinkML-Map does not automatically construct and topologically sort a dependency graph of derived slots.

### Missing source data versus invalid references

The evaluator distinguishes a schema-declared field that is absent from a particular source record from an expression referring to an unknown name.

A known but missing source field can legitimately resolve to `None`.

An unknown bare expression name can produce a warning and `None` in non-strict mode, while strict mode raises an error.

However, an attribute expression such as `UnknownTable.field` can raise even in non-strict mode when its root name is not recognized as a source slot, class, or join alias.

This differentiation reduces the risk of treating an invalid transformation reference as an ordinary missing observation.

The expression engine also rejects certain comprehension-bound attribute accesses. Constructing structured records directly inside comprehensions can bypass the range, cardinality, and datatype handling associated with class derivations. These expression restrictions therefore preserve a distinction between calculating values and constructing typed structured objects.

The stable function namespace additionally includes `str`, `bool`, `strlen`, `lstrip`, and `rstrip`, which supplement the helper inventory already provided in the original guide.

Primary sources:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/utils/eval_utils.py`

`https://github.com/linkml/linkml-map/blob/v0.5.4/tests/test_transformer/test_slot_derivation_features.py`

## 9. File input/output asymmetry

The available serialization formats are not interchangeable across loading, execution, and writing.

The v0.5.4 general-purpose `DataLoader` recognizes YAML, JSON, TSV, and CSV inputs.

By contrast, the streaming-writer system additionally supports JSONL, Parquet, and DuckDB output.

The optimized DuckDB set-based join pathway has a narrower set of supported input representations because it loads eligible tabular source files into DuckDB.

| Operation                    | v0.5.4 format support                        |
| ---------------------------- | -------------------------------------------- |
| General file-based input     | YAML, JSON, CSV, TSV                         |
| Streamed/file output         | YAML, JSON, JSONL, CSV, TSV, Parquet, DuckDB |
| Set-based DuckDB join inputs | CSV, TSV, JSON                               |

Consequently, the ability to generate a Parquet artifact does not imply that Parquet is a native source format for `DataLoader` or that the transformation executor provides a direct PyArrow `Table` interface.

It also does not imply that the DuckDB join optimizer can operate on every source format understood by the Python object transformer.

This distinction determines whether an existing source representation can be transformed directly or requires conversion through an adjacent data-processing layer.

Primary sources:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/loaders/data_loaders.py`

`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/join_engine.py`

## 10. Explicit datatype-coercion limitations in v0.5.4

The stable `_coerce_datatype()` implementation performs recursive conversion across lists and dictionaries for a limited set of explicitly declared target ranges.

Its conversion table includes Python's `int`, `float`, `str`, and `bool` constructors.

This has an important implication for Boolean fields: Python's built-in `bool()` constructor interprets nonempty strings as true.

Therefore:

```
bool("false")  # Truebool("0")      # True
```

If a textual Boolean reaches the v0.5.4 explicit Boolean-coercion path, the resulting value can differ from the intended interpretation of that text.

This is not a claim that every Boolean-looking source value is necessarily processed through that path. In the stable implementation, coercion depends on the applicable slot-derivation branch and explicit target range.

More generally, `_coerce_datatype()` is not a complete implementation of LinkML datatype parsing, and providing a target schema alone does not guarantee comprehensive coercion of constants and expression results in v0.5.4.

The v0.6.0-rc1 prerelease changes this behavior substantially by introducing target-schema-driven coercion when no explicit specification range overrides it, including the intended parsing of textual Boolean values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary source:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/transformer.py`

## 11. Declared transformation features without established general execution support

The transformation metamodel includes several constructs whose existence does not establish complete runtime handling in the stable Python implementation.

| Construct                                 | Meaning and implementation boundary                                                                                                                                          |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PrefixDerivation`                        | Describes target-prefix derivation but is explicitly identified in the metamodel as a placeholder                                                                            |
| `SlotDerivation.inverse_of`               | Represents inverse relationship or back-reference metadata for relational mappings; general automatic foreign-key insertion is not established in the stable object executor |
| `SlotDerivation.type_designator`          | Describes an attribute identifying an instance's class, analogous to LinkML's `designates_type`; its declaration does not establish automatic polymorphic runtime dispatch   |
| `StringificationConfiguration.over_slots` | Declares multiple source slots for string construction; a general multi-slot execution pathway is not established by the inspected stable implementation                     |
| `expression_to_expression_mappings`       | Defined in the metamodel but deprecated in favor of `case()` and Boolean operators                                                                                           |

The distinctions are particularly important when considering alternative execution backends.

A field may be structurally valid within a transformation specification and represent a meaningful intended operation without being interpreted by `ObjectTransformer`, incorporated into `SchemaMapper`, or supported by a compiler.

Executable semantics must therefore be established at the implementation level, rather than inferred from metamodel expressiveness alone.

Primary source:\
`https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/datamodel/transformer_model.yaml`

## 12. Additional v0.6.0-rc1 functionality and behavior changes

The October 23, 2026 prerelease introduces several changes beyond the major datatype, enumeration, inheritance, and validation improvements already discussed in the main guide.

These changes are relevant because they either extend the declarative language's effective capabilities or change the results produced by otherwise unchanged transformation specifications.

### Constant-only record generation

A class derivation containing no `populated_from` and consisting entirely of constant `value` slots can now produce one output record without reading input data.

Previously, such a derivation could generate copies associated with an input table's records.

This introduces a useful declarative mechanism for constant records, reference entries, or other outputs that do not correspond to an individual source instance.

### Complete execution of unrestricted statement blocks

The prerelease fixes multi-statement expressions executed under `--unrestricted-eval`.

The stable pathway could execute only the first statement while silently ignoring later assignments. The corrected implementation executes the statement block completely.

Source fields in that execution context must be referenced using `src.<slot>`; bare references or the `{slot}` notation used in ordinary restricted expressions are not interchangeable.

The change affects correctness because previously ignored statements may now execute, while formerly tolerated invalid references can produce explicit failures.

### Single-file source identification

In v0.6.0-rc1, an explicitly supplied `--source-type` determines the class associated with a single input file even when its filename stem differs from the class name.

For example, `people.tsv` can be treated as class `Person` when `--source-type Person` is provided.

The stable file-identification behavior could otherwise produce an empty output because no class derivation matched the filename-derived source identifier.

### Streaming YAML null handling

Streaming YAML output now omits null-valued slots, aligning its behavior more closely with the existing JSON writers.

This changes serialization semantics even if the underlying transformed object remains conceptually unchanged.

Downstream consumers that distinguish an absent key from an explicitly present null value can therefore observe different behavior.

### Corrected CSV serialization of collections

The prerelease corrects the handling of list and dictionary values written into CSV cells.

In the stable implementation, a complex value serialized as JSON could contain commas without receiving the full field quoting required by CSV.

For example, a list containing several values could unintentionally produce additional CSV columns.

The correction preserves the logical cell boundary for these serialized structures.

### Identifier-minting configuration hierarchy

The prerelease's `mint_ids` feature supports configuration at the specification level, within `class_defaults.<Class>`, or on an individual class derivation.

When enabled for a qualifying target class, identifiers are derived deterministically from canonical record content using UUIDv5.

These identifiers are content-derived rather than stable independently assigned identities. Changes to the canonicalized content can change the generated identifier, which matters when other records maintain persistent references to that entity.

### Removal of legacy streaming interfaces

The deprecated function-based writer APIs are removed, including `yaml_stream`, `json_stream`, `jsonl_stream`, `tsv_stream`, `csv_stream`, and `get_stream_writer`.

The deprecated `TabularStreamWriter.stream()` alias is also removed.

Their replacements are the class-based writer interfaces described in Section 5 of this addendum.

These changes establish a clearer public interface for programmatic streaming and multi-output generation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Official prerelease notes:\
`https://github.com/linkml/linkml-map/releases/tag/v0.6.0-rc1`

## 13. Architectural synthesis

The additional capabilities extend LinkML-Map's practical role beyond basic source-to-target field projection.

Source normalization can remain declarative. Sentinel handling, categorical mappings, expression dependencies, namespace conversion, and unit normalization can each encode a distinct aspect of how source values are interpreted. Their combination can reduce custom preprocessing logic while keeping transformation rules represented as inspectable artifacts.

Heterogeneous records can share a canonical target model. Multiple source-class derivations can populate one target class while preserving source-specific mappings and discriminator values. In conjunction with target-schema derivation and typed-object construction, this provides a native basis for normalizing structurally different record categories.

Execution and output interfaces can be composed independently. The reusable writer infrastructure allows mapped records to be distributed across several output representations, while DuckDB-assisted joins, lookup-index management, and resource configuration provide distinct mechanisms for controlling relational execution.

Implementation boundaries remain consequential. Native input formats differ from output formats; Parquet and DuckDB materialization proceeds through JSONL staging; explicit datatype coercion differs from comprehensive target-schema enforcement; and certain metamodel features are declarations rather than implemented operations.

The overall consequence is that LinkML-Map offers a richer set of reusable transformation mechanisms than its main executor interface alone suggests. Its strongest architectural value comes from combining these mechanisms within a common declarative specification, while preserving a precise distinction between what the specification can express, what the stable Python implementation executes, and what newer prerelease versions change.