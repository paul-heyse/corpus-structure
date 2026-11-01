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