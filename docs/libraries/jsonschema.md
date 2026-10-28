# Python `jsonschema` — Comprehensive Library Capability Reference

Target version: 4.26.0 (latest stable) · Research date: October 28, 2026 · Python ≥3.10 · License: MIT

`jsonschema` is a Python implementation of the JSON Schema specification, providing a declarative, extensible validation engine for structured data. Its distinguishing capabilities extend beyond checking data against schemas: it supports multiple schema dialects, compositional and recursive validation, programmable reference resolution, structured error diagnostics, custom validation semantics, and integration with independently maintained schema registries.

Version 4.26.0 was released January 7, 2026. The upstream development changelog contains entries for 4.27.0, but that version is not included in this reference because it has not been published as a stable PyPI release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary sources:

- Official documentation: `https://python-jsonschema.readthedocs.io/en/stable/`
- Upstream repository: `https://github.com/python-jsonschema/jsonschema`
- Release history: `https://github.com/python-jsonschema/jsonschema/releases`
- Package metadata: `https://pypi.org/project/jsonschema/`

## 1. Architectural model and capability map

`jsonschema` separates five concerns that are frequently conflated in conventional validation systems:

1. Schema semantics: JSON Schema dialects define which constraints, composition rules, references, and annotations mean what.
2. Validation execution: A draft-specific validator evaluates Python instances against those constraints.
3. Reference resolution: The companion `referencing` library locates and interprets referenced schemas, including across documents and drafts.
4. Diagnostics: Validation failures retain their structural context, enabling machine-readable analysis rather than dependence on exception messages.
5. Semantic extension: Custom validators, type checkers, and format checkers can adapt the standard engine without replacing its infrastructure.

### Capability map

| Functional area        | Native mechanisms                                                  | Architectural significance                                                        |
| ---------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| Schema validation      | `validate`, `is_valid`, `iter_errors`, `Validator.validate`        | Declarative validation, with short-circuit or complete-error modes                |
| Schema dialects        | `Draft202012Validator`, `Draft201909Validator`, earlier validators | Version-specific semantics and compatibility                                      |
| Schema integrity       | `check_schema`, `META_SCHEMA`, `validator_for`                     | Validate schemas before using them to validate data                               |
| Composition            | `$ref`, `allOf`, `anyOf`, `oneOf`, `not`, `if`/`then`/`else`       | Reusable, conditional, and recursive structural constraints                       |
| Schema references      | `referencing.Registry`, `Resource`, `Specification`                | Decoupled schema identity, storage, resolution, and retrieval                     |
| Structured diagnostics | `ValidationError`, `ErrorTree`, `best_match`                       | Precise field attribution, nested failure analysis, and diagnostic prioritization |
| Domain-specific types  | `TypeChecker`, `redefine`, `redefine_many`                         | Adapt Python-object-to-JSON-type semantics                                        |
| Custom constraints     | `validators.extend`, `validators.create`                           | Add or replace assertion keywords and validator behaviors                         |
| Format validation      | `FormatChecker`, `.checks`, optional dependencies                  | Optional specialized string and primitive-value checks                            |
| Validator reuse        | `evolve`, reusable validator instances                             | Preserve validation configuration across related schemas                          |

The central boundary is that `jsonschema` validates instances; it is not primarily a parser, data coercion layer, serializer, schema compiler, or Python model generator. JSON Schema annotations can describe defaults and metadata, but those annotations do not inherently transform the validated data.

This separation makes the library particularly relevant where independently maintained, portable schemas must govern heterogeneous Python data producers and consumers.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/validate/` and `https://python-jsonschema.readthedocs.io/en/stable/referencing/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



## 2. Validation execution, lifecycle, and schema integrity

### 2.1 Validation entry points and execution modes

The library provides distinct interfaces for validating once, validating repeatedly, collecting errors, and checking schema correctness.

| Interface                                        | Behavior                                                                 | Important distinction                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `jsonschema.validate(instance, schema, cls=...)` | Selects a validator, checks schema validity, then validates the instance | Convenient but repeats schema validation on each call                        |
| `Draft202012Validator(schema)`                   | Constructs a validator bound to a schema                                 | Assumes the schema is valid; does not independently enforce that assumption  |
| `validator.validate(instance)`                   | Raises `ValidationError` on an invalid instance                          | Appropriate when a failure should interrupt execution                        |
| `validator.is_valid(instance)`                   | Returns a Boolean validity result                                        | Avoids building an external diagnostic collection                            |
| `validator.iter_errors(instance)`                | Lazily yields validation errors                                          | Suitable for collecting multiple failures and analyzing nested errors        |
| `ValidatorClass.check_schema(schema)`            | Validates a schema against the class's meta-schema                       | Separates schema correctness from instance validation                        |
| `validator.evolve(**kwargs)`                     | Creates a related validator with changed configuration                   | Preserves unspecified configuration, including reference-resolution behavior |
| `validators.validator_for(schema, default=...)`  | Determines a validator class from `$schema`                              | Enables dialect-aware processing without hardcoding a single draft           |

Consequential lifecycle distinction: `jsonschema.validate()` checks the schema on every invocation. When schemas are trusted and repeatedly applied, a reusable validator avoids that recurring schema check. This is a documented efficiency mechanism, not evidence of compiled validation or a particular throughput improvement.

`iter_errors()` yields errors incrementally, but their order is not a stable public guarantee. Consumers needing deterministic diagnostics should impose their own ordering using structural properties such as instance and schema paths.

`evolve()` is particularly useful for sharing a registry and format-checking configuration across related schemas. It can also return a different concrete validator class when the replacement schema declares a different dialect.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/validate/` and `https://python-jsonschema.readthedocs.io/en/stable/faq/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



### 2.2 Schema validation and meta-schemas

JSON Schema is self-describing: a meta-schema specifies the structure of valid schemas.

`jsonschema` exposes:

- `META_SCHEMA`: the validator class's associated meta-schema.
- `check_schema()`: validates a candidate schema against that meta-schema, raising `SchemaError` on failure.
- `$schema`: identifies the dialect governing interpretation of a schema.
- `validators.validator_for()`: resolves known dialect identifiers to validator classes.
- `jsonschema_specifications.REGISTRY`: companion-package access to official meta-schemas and vocabulary documents.

A valid schema is not necessarily a useful or appropriately constrained schema. For example, an empty schema is valid yet imposes no restrictions; a custom keyword not understood by the validator may also have no effect.

Meta-schema validation therefore establishes syntactic and dialect-level schema validity, not whether a schema expresses the intended business or domain requirements.

`jsonschema_specifications.REGISTRY` is useful when schema definitions themselves are treated as first-class resources. It exposes the official JSON Schema support documents through the same registry abstraction used for instance-schema references, avoiding copying meta-schema files or depending on private package data.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/creating/` and `https://jsonschema-specifications.readthedocs.io/en/stable/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+1



## 3. Schema dialects and advanced constraint semantics

### 3.1 Multi-draft support

`jsonschema` 4.26.0 provides complete documented support for six JSON Schema drafts.

| Dialect       | Validator              | Distinctive capabilities or compatibility considerations                                                                                |
| ------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Draft 2020-12 | `Draft202012Validator` | `$dynamicRef`, `$dynamicAnchor`, `prefixItems`, modern unevaluated semantics, vocabulary-based specification structure                  |
| Draft 2019-09 | `Draft201909Validator` | `$recursiveRef`, `$recursiveAnchor`, `$defs`, `dependentSchemas`, `unevaluatedProperties`, `unevaluatedItems`                           |
| Draft 7       | `Draft7Validator`      | `if`/`then`/`else`, `const`, `contains`, `content*` annotations                                                                         |
| Draft 6       | `Draft6Validator`      | `const`, `contains` absent until Draft 7, but introduces modern constructs including `propertyNames` and `exclusiveMinimum` as a number |
| Draft 4       | `Draft4Validator`      | Older `$ref`, `id`, integer, and exclusive-bound semantics                                                                              |
| Draft 3       | `Draft3Validator`      | Legacy syntax and behavioral rules, substantially different from modern drafts                                                          |

The version boundaries matter beyond keyword availability. They can affect how references are interpreted, which keywords may coexist with `$ref`, numeric type rules, and how array schemas are expressed.

For example, Draft 2020-12 separates tuple position validation (`prefixItems`) from validation of remaining elements (`items`). Earlier drafts use different representations.

The package version and JSON Schema dialect version are independent. Upgrading from `jsonschema` 4.25 to 4.26 does not change a schema explicitly declaring Draft 7 into Draft 2020-12.

Sources: `https://json-schema.org/draft/2020-12/release-notes` and `https://python-jsonschema.readthedocs.io/en/stable/validate/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

json-schema.org+2



### 3.2 Functional families of assertions and applicators

The following capabilities are implemented through the dialect-specific validator keyword mappings. Keyword availability and detailed behavior remain draft-dependent.

| Constraint family                   | Key mechanisms                                                                       | Advanced significance                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Value typing                        | `type`, `enum`, `const`                                                              | JSON-level type and value constraints independent of Python class definitions |
| Numeric                             | `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`           | Inclusive/exclusive bounds and divisibility requirements                      |
| Strings                             | `minLength`, `maxLength`, `pattern`, `format`                                        | Length, regular-expression and optional semantic-format constraints           |
| Object structure                    | `properties`, `required`, `patternProperties`, `propertyNames`                       | Fixed fields, dynamic name matching and key-name constraints                  |
| Object cardinality and dependencies | `minProperties`, `maxProperties`, `dependentRequired`, `dependentSchemas`            | Cross-field presence and schema-level conditional constraints                 |
| Object closure                      | `additionalProperties`, `unevaluatedProperties`                                      | Control of unspecified fields, including after compositional validation       |
| Arrays and tuples                   | `prefixItems`, `items`, `minItems`, `maxItems`, `uniqueItems`                        | Positional versus homogeneous validation and uniqueness                       |
| Array content selection             | `contains`, `minContains`, `maxContains`, `unevaluatedItems`                         | Existential/count-based constraints and residual-item validation              |
| Logical composition                 | `allOf`, `anyOf`, `oneOf`, `not`                                                     | Intersection, alternative branches, exclusive alternatives and negation       |
| Conditional logic                   | `if`, `then`, `else`                                                                 | Data-dependent schema application                                             |
| Reusable definitions                | `$defs`, `$ref`, `$anchor`                                                           | Modular, named and recursive schema structures                                |
| Dynamic references                  | `$dynamicRef`, `$dynamicAnchor`                                                      | Dynamic-scope-based recursive schema extension                                |
| Annotations                         | `title`, `description`, `default`, `examples`, `deprecated`, `readOnly`, `writeOnly` | Metadata available to schema consumers without inherently imposing assertions |

The underlying specification's distinction between assertions, applicators, and annotations is important: not every keyword is a Boolean constraint, and applicability is often conditional on the instance's JSON type.

Primary keyword reference: `https://json-schema.org/understanding-json-schema/keywords`\
Draft 2020-12 core specification: `https://json-schema.org/draft/2020-12/json-schema-core`\
Draft 2020-12 validation specification: `https://json-schema.org/draft/2020-12/json-schema-validation`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

json-schema.org+2



### 3.3 Composition and conditional validation

Four structural mechanisms warrant particular attention.

Logical schema composition

`allOf`, `anyOf`, `oneOf`, and `not` combine validations. `oneOf` requires exactly one matching branch rather than merely one or more, so it may entail evaluating multiple candidate branches even after one succeeds. It is therefore different from simply selecting the first matching variant.

`allOf` is a logical conjunction, not object-oriented inheritance. It does not merge schemas into a single object definition with inherited properties.

Conditional schemas

`if`/`then`/`else` selects additional constraints based on whether the instance satisfies an `if` schema. `dependentSchemas` instead applies a schema to the entire containing object when a named property is present. `dependentRequired` specifies relationships between property presence rather than validating values directly.

These features can represent numerous structural cross-field rules without custom validation callbacks.

Composition-aware object closure

`additionalProperties` operates relative to properties recognized by the applicable `properties` and `patternProperties` definitions in its own schema object. Consequently, closing a base schema with `additionalProperties: false` can prevent an `allOf` extension from introducing otherwise valid fields.

`unevaluatedProperties` addresses a different problem: it can constrain properties left unevaluated by applicable schema branches, allowing the overall schema to be closed after composing multiple definitions.

This is a major capability for extensible contracts. A schema can define a reusable core, permit extensions through compositional schemas, and enforce closure at the appropriate outer boundary without manually duplicating every property declaration.

Array remainder constraints

The same principle extends to `unevaluatedItems`. In Draft 2020-12, the relationship between `prefixItems`, `items`, `contains`, and the annotation of evaluated indices determines which elements remain subject to a residual constraint. This differs from simply applying a fixed index cutoff.

Sources: `https://json-schema.org/draft/2020-12/json-schema-core` and `https://json-schema.org/understanding-json-schema/reference/combining`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

json-schema.org+2



### 3.4 Recursive schemas and dynamic scope

Ordinary `$ref` enables references to reusable schemas, including recursive definitions. Draft 2020-12 adds an important architectural mechanism through `$dynamicRef` and `$dynamicAnchor`.

Unlike a conventional fixed reference, a dynamic reference can be rebound according to the dynamic scope of schema evaluation. This makes it possible to define a recursive schema in a reusable base document and extend its constraints in another schema without having to reconstruct every recursive relationship manually.

Typical problem classes include recursive trees, nested document grammars, and extensible hierarchies in which a constraint introduced at an outer level must also apply to recursively nested elements.

Important distinctions:

- `$ref` targets a schema URI and fragment according to the ordinary reference rules.
- `$dynamicRef` supports dynamic-anchor resolution under Draft 2020-12.
- `$recursiveRef` and `$recursiveAnchor` belong to Draft 2019-09, with different semantics.
- Correct operation depends on retaining schema-resource identity and evaluation scope; naïvely replacing references with dictionary contents is not equivalent.

The `referencing` companion library provides the underlying resolution machinery; `jsonschema` applies it during validation.

Sources: `https://json-schema.org/draft/2020-12/release-notes` and `https://python-jsonschema.readthedocs.io/en/stable/referencing/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

2020-12 Release Notes+2



Draft clarification: Draft 6 already introduced `contains`, alongside `const` and `propertyNames`; Draft 7 retained these and added conditional validation and other capabilities. See `https://json-schema.org/draft-06/json-schema-release-notes`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

Draft-06 Release Notes



## 4. Reference resolution and schema registries

The separation of JSON Schema validation from reference management is one of the library's most consequential architectural features.

Since the 4.x transition, the preferred mechanism is the independently maintained `referencing` library. Its registry is supplied to a `jsonschema` validator through the `registry=` constructor argument.

### 4.1 Core referencing objects

| Object                                                     | Responsibility                                              | Important capabilities                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `referencing.Registry`                                     | Collection of addressable schema resources                  | Immutable additions, merging, removal, lazy discovery, optional retrieval    |
| `referencing.Resource`                                     | Schema contents associated with a referencing specification | Explicit dialect interpretation, resource identity and subresource discovery |
| `referencing.Specification`                                | Version-specific reference rules                            | Defines how resource identifiers, subresources and anchors are interpreted   |
| `referencing.Resolver`                                     | Resolves URI references against a registry and base URI     | Relative references, JSON Pointers, anchors, dynamic scope                   |
| `referencing.Anchor`                                       | Named location within a resource                            | Enables references to named schema locations                                 |
| `referencing.jsonschema.DRAFT202012` and related constants | Predefined JSON Schema referencing specifications           | Avoids manually recreating version-dependent resolution rules                |

The separation is meaningful: a schema's identity, storage location, retrieval mechanism, and interpretation rules need not be the same thing.

For example, a schema with no `$id` can be registered under an external `urn:` identifier, and a schema containing `$id` can be assigned additional aliases. Its URI does not inherently require an HTTP resource.

### 4.2 Registry composition and lifecycle

`Registry` supports a relatively sophisticated set of operations:

| API                            | Capability                                                 |
| ------------------------------ | ---------------------------------------------------------- |
| `with_resource(uri, resource)` | Register one resource under an explicit URI                |
| `with_resources(pairs)`        | Add multiple URI/resource associations                     |
| `with_contents(pairs, ...)`    | Add deserialized contents with specification detection     |
| `combine(*registries)`         | Compose multiple registries                                |
| `remove(uri)`                  | Produce a registry without a particular resource           |
| `crawl()`                      | Discover embedded subresources and anchors ahead of lookup |
| `get_or_retrieve(uri)`         | Resolve a resource, possibly discovering or retrieving it  |
| `contents(uri)`                | Inspect already available resource contents                |
| `resolver(base_uri)`           | Obtain a reference resolver with an explicit base URI      |
| `resolver_with_root(resource)` | Create a resolver rooted at a specific resource            |

Immutability is a defining property: operations adding or removing resources return new registries rather than modifying the original registry in place. Resource discovery is otherwise lazy, unless explicitly performed with `crawl()`.

This supports composable registries for independently distributed schema packages and reuse of known schema-resource sets. It does not imply that the underlying Python dictionaries are deeply immutable.

A companion `referencing` feature is support for schema packages: Python distributions can expose collections of reusable schemas through a ready-to-use registry. `jsonschema-specifications` is an official example.

Sources: `https://referencing.readthedocs.io/en/stable/api/` and `https://referencing.readthedocs.io/en/stable/schema-packages/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://referencing.readthedocs.io\&sz=32)

referencing 0.37.0 documentation+1



### 4.3 Multi-draft resolution

`Resource.from_contents()` attempts to identify the appropriate specification from a resource's contents, particularly its `$schema` declaration.

Where the resource does not declare a recognizable dialect, an explicit specification can be supplied through `Resource(..., specification=...)` or `DRAFT202012.create_resource(contents)`.

This matters because references may cross resource boundaries governed by different drafts. The referencing implementation preserves the distinction between those documents rather than treating everything as an undifferentiated dictionary tree.

In addition to ordinary reference lookup, the underlying implementation supports:

- Canonical and externally assigned resource URIs.
- Relative references resolved against a base URI.
- JSON Pointer fragments selecting subschema locations.
- Named anchors.
- Embedded resources that introduce distinct base URIs.
- Dynamic reference scope used by modern recursive schemas.
- Specific resolution failures such as `NoSuchResource`, `NoSuchAnchor`, `PointerToNowhere`, and `CannotDetermineSpecification`.

A missing `$schema` in a resource is therefore not always harmless: automatic specification detection may fail even though a caller could have selected a dialect explicitly.

Source: `https://referencing.readthedocs.io/en/stable/intro/` and `https://referencing.readthedocs.io/en/stable/api/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://referencing.readthedocs.io\&sz=32)

referencing 0.37.0 documentation+2



### 4.4 Pluggable retrieval and storage

A registry can be configured with `Registry(retrieve=callable)`, where the callable receives a URI and returns a `Resource` or raises an appropriate missing-resource exception.

The official documentation demonstrates or explicitly describes several retrieval patterns:

| Backing source             | Supported approach                                           | Important boundary                                                     |
| -------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- |
| In-memory dictionaries     | Pre-register `Resource` objects                              | No external I/O required                                               |
| Local filesystem           | URI-to-path mapping in a retrieval callable                  | Path validation and filesystem access belong to the caller             |
| YAML schema files          | Deserialize with PyYAML, then create resources               | The schema still needs to conform to JSON Schema's data model          |
| HTTP/HTTPS                 | Retrieve with a client such as `httpx`                       | Explicit network access, security policy and resource handling         |
| SQLite or another database | Resolve URI to a stored schema                               | Persistence, version selection and authorization are external          |
| Multiple sources           | Compose registries or dispatch within the retrieval callable | Conflict resolution and source precedence require deliberate semantics |

The important design opportunity is not merely remote references. It is that a URI-addressable collection of schema resources can be backed by different storage systems without changing the validator's contract.

A registry may support local development, distributed schema packages, offline validation, or controlled access to centrally maintained schema definitions without embedding storage logic into validation keywords.

### 4.5 Reference security and deprecated resolution APIs

The modern `referencing.Registry` does not automatically fetch arbitrary remote resources. Retrieval has to be configured explicitly.

This avoids coupling the mere presence of `$ref` to network access. An explicitly enabled retrieval callback still introduces risks: server-side request forgery, local-file exposure, oversized responses, unexpected schemes, recursion and expensive resolution chains may require controls beyond those supplied by the library.

The older `jsonschema.RefResolver` and validator `resolver=` argument are deprecated in favor of `Registry`. Legacy behavior should not be treated as representative of the modern mechanism.

Finally, `referencing` is a separate dependency with its own release lifecycle and public-API stability policy; the documentation for its current 0.x series describes it as beta.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/referencing/` and `https://referencing.readthedocs.io/en/stable/compatibility/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



## 5. Structured validation diagnostics

`jsonschema` has unusually useful error-introspection capabilities for a schema validator. Invalidity is represented not only by a message but by a structured object recording which assertion failed and where.

### 5.1 `ValidationError` as a structured diagnostic

| Attribute                             | Meaning                                                     | Uses                                         |
| ------------------------------------- | ----------------------------------------------------------- | -------------------------------------------- |
| `message`                             | Human-readable failure explanation                          | Display                                      |
| `validator`                           | Failed keyword, such as `type` or `minimum`                 | Failure classification                       |
| `validator_value`                     | Constraint value associated with the failed keyword         | Constraint-specific reporting                |
| `instance`                            | Instance value at the failed validation location            | Inspect problematic data                     |
| `schema`                              | Applicable schema or subschema                              | Inspect the exact constraint context         |
| `path`, `relative_path`               | Path relative to the current validation context             | Local structural navigation                  |
| `absolute_path`                       | Path relative to the original instance                      | Field or element attribution                 |
| `json_path`                           | JSONPath-like textual path to the failing instance location | Human-readable navigation                    |
| `schema_path`, `relative_schema_path` | Location of the failed keyword in its schema context        | Link diagnostics to constraints              |
| `absolute_schema_path`                | Schema path relative to the original validation schema      | Root-relative constraint identification      |
| `context`                             | Nested errors arising from failed subschemas                | Diagnose alternative or composite validation |
| `parent`                              | Enclosing validation error                                  | Traverse nested failure relationships        |
| `cause`                               | Underlying non-validation exception, where available        | Inspect failures raised by format checkers   |

This enables significantly more reliable diagnostic processing than parsing exception strings.

For example, an `anyOf` failure can identify the failed alternatives through `context`, rather than merely reporting that none of the alternatives matched. Each suberror retains its own path and failed keyword.

Structural paths and textual paths should not be conflated. `json_path` is a convenience representation; `path` and `absolute_path` preserve the structural segments of the location. `schema_path` refers to schema structure, not to an instance location.

Source: `https://python-jsonschema.readthedocs.io/en/stable/errors/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+1



### 5.2 `ErrorTree`: querying validation failures by structure

`jsonschema.exceptions.ErrorTree` converts a collection of `ValidationError` objects into a tree indexed by the keys and indices of the invalid instance.

Its principal capabilities include:

- Child lookup using property names or array indices.
- Presence checks for whether a particular instance element has errors.
- An `errors` mapping from failed keyword names to error objects at each tree location.
- `total_errors` for counting failures across the tree.
- Iteration over immediate child locations having errors.

The distinction between element-specific and container-level errors is preserved. For example, an invalid array element belongs to its child node, while a `minItems` violation belongs to the array node.

This structure is useful for programmatic validation reports, structured editing systems, diagnostic aggregation and automated analysis of which schema constraints failed in which parts of a document.

`ErrorTree` is a derived structure, not a different validation engine. It consumes errors produced by the validator.

Deprecation: Incremental population via `ErrorTree.__setitem__` is deprecated. The supported pattern is constructing the tree from the error collection.

### 5.3 `best_match` and configurable diagnostic relevance

`jsonschema.exceptions.best_match(errors)` attempts to identify one especially informative error.

Its associated mechanisms are `relevance()` and `by_relevance(weak=..., strong=...)`.

The stable 4.26.0 heuristic generally favors errors near the root of the instance, because those can indicate a broader structural mismatch. For `anyOf` and `oneOf`, it instead descends into nested failures where a more specific explanation may be available.

Custom relevance classifications can identify which keywords should be considered stronger or weaker for ranking purposes.

This is diagnostic ranking, not a guarantee of the true root cause. The heuristics can change between library releases, and the upstream documentation explicitly excludes exact error wording and error ordering from its compatibility promises.

Source: `https://python-jsonschema.readthedocs.io/en/stable/errors/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



## 6. Extending validation semantics

The extension surface is substantially broader than adding a custom check to an individual field. `jsonschema` exposes the machinery for implementing new assertion keywords, redefining what JSON Schema types mean for Python objects, registering formats, and creating entire validator dialects.

### 6.1 Custom validation keywords

`jsonschema.validators.extend()` produces a new validator class from an existing one, while `jsonschema.validators.create()` builds a class around a specified meta-schema and keyword implementation map.

Custom keyword implementations receive four arguments:

- The current validator instance.
- The keyword's schema value.
- The instance being evaluated.
- The schema containing the keyword.

They yield `ValidationError` objects when constraints fail. When applying nested subschemas, the documented `validator.descend()` mechanism preserves the instance and schema paths needed for accurate diagnostics.

This is significant because custom assertions can participate in the existing validation engine and its error infrastructure, rather than requiring a separate post-validation pass with unrelated error representations.

| Extension point                 | Native interface                                     | Important distinction                                                  |
| ------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------- |
| Add a keyword                   | `validators.extend(..., validators={...})`           | Reuses an established draft and adds a new evaluation function         |
| Replace a keyword               | Override the entry in `VALIDATORS`                   | The original implementation is replaced entirely                       |
| Augment a keyword               | Delegate to the parent class's `VALIDATORS[keyword]` | Retains standard behavior while adding checks                          |
| Create a validator dialect      | `validators.create(meta_schema=..., validators=...)` | Defines the keyword implementation and schema interpretation contract  |
| Register dialect selection      | `validators.validates(version)`                      | Makes a validator discoverable through `$schema` selection             |
| Customize schema identity       | `id_of=`                                             | Controls resource identification for a custom validator implementation |
| Customize keyword applicability | `applicable_validators=`                             | Can reproduce historic handling of keywords alongside `$ref`           |

A particularly important distinction is extending a validator versus extending the formal schema language.

Adding a keyword implementation makes it executable by the custom validator, but does not automatically make that keyword part of a publicly recognized JSON Schema dialect. A formal custom dialect may also require corresponding meta-schema constraints, vocabulary declarations and explicit agreement among schema producers and consumers.

When an extended class's `META_SCHEMA` needs modification, the original meta-schema must be copied first: `extend()` inherits it without an implicit copy. Otherwise, mutations can affect the original class.

Direct subclassing of the generated validator classes is not a supported public extension pathway and has emitted deprecation warnings since 4.12.0.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/creating/` and `https://python-jsonschema.readthedocs.io/en/stable/validate/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



### 6.2 `TypeChecker`: mapping JSON Schema types to Python semantics

The `type` keyword is evaluated through an associated `TypeChecker`, which maps JSON Schema's seven primitive type names to Python predicates.

The public transformation methods are:

- `redefine(type, fn)`: replace or add one type predicate.
- `redefine_many(definitions)`: apply several predicates at once.
- `remove(*types)`: produce a checker without specified type definitions.
- `is_type(instance, type)`: query the type mapping directly.

These operations produce new checkers. A customized checker can be supplied through `validators.extend(..., type_checker=...)`.

This is more flexible than simply checking `isinstance()` against a fixed class list. It permits adapting a validator to domain-native numerical objects, alternative mapping implementations, and custom Python value representations.

The built-in mappings are deliberately pragmatic rather than universally generic:

- `number` uses the broader `numbers.Number` abstraction.
- `integer` ordinarily uses `int` for efficient recognition.
- `object` ordinarily uses `dict`, rather than checking the more general `collections.abc.Mapping`.
- The built-in predicates retain JSON Schema-specific distinctions, including the difference between Boolean and numeric values.

Generalizing these checks can be desirable for application-native Python objects, but it introduces two independent considerations.

First, broad abstract-base-class checks may add overhead to frequently evaluated constraints. Second, accepting additional Python representations does not expand the interoperable JSON data model. For example, treating a custom object as a JSON Schema `object` does not automatically serialize it, normalize its keys, or ensure that all object-specific keywords can operate on it.

The strongest use of `TypeChecker` is therefore adapting the boundary between already-understood data semantics and a Python runtime representation—not silently redefining portable JSON Schema semantics.

Source: `https://python-jsonschema.readthedocs.io/en/stable/validate/#type-checking`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation



### 6.3 `FormatChecker`: independently extensible semantic checks

`FormatChecker` supplies a separate extension surface for the schema `format` keyword.

The notable APIs are `FormatChecker.checks(name, raises=...)`, `FormatChecker.check(instance, format)`, and `FormatChecker.conforms(instance, format)`.

`checks()` registers a format predicate on an individual checker. A checker can be restricted to a selected set of format names, allowing a narrower validation profile than every available checker.

A custom check may identify exception types through `raises=`. If one of those exceptions occurs, the resulting validation error can preserve the underlying exception in `ValidationError.cause`.

This permits format validation to remain a separate concern from the schema's structural `type` semantics. A value can be a valid string but an invalid domain-specific identifier, URI, or other format.

The older class-level `FormatChecker.cls_checks()` registration method is deprecated; per-instance registration avoids relying on process-wide changes affecting future checkers.

Crucial limitation: unrecognized formats return valid rather than failing closed. This is intentional. A schema containing an organization-specific format name is therefore not sufficient evidence that its constraints are being enforced by every consumer.

Source: `https://python-jsonschema.readthedocs.io/en/stable/validate/#validating-formats`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation



### 6.4 Limits of extensibility

The extension APIs preserve much of the existing validation infrastructure, but not every behavior can be added by writing a standalone keyword callback.

In particular:

- A keyword that evaluates subschemas needs to integrate correctly with diagnostic paths and evaluation context.
- New annotation-producing keywords may have interactions with `unevaluatedProperties` or `unevaluatedItems` that are not captured by a simple Boolean test.
- Changes to reference semantics require understanding `referencing` and the selected dialect.
- Instance mutation or coercion can make outcomes depend on evaluation order, conflicting with the ordinary assertion-oriented model.

For advanced custom dialects, the public extension facilities are an important foundation, but they are not a guarantee that arbitrary new vocabularies will automatically compose with every standard keyword.

## 7. Format validation and optional capabilities

### 7.1 Three independent conditions govern format enforcement

A schema may declare `format: "date-time"` without that value being validated as a date-time.

Enforcement depends on three distinct conditions:

1. A validator must receive a `format_checker`, because format assertions are disabled by default.
2. The checker must recognize the requested format.
3. Any optional dependency needed by that format must be installed.

The second and third points are easily overlooked: unknown formats, including formats lacking their optional checker dependencies, pass without a validation error.

The distinction follows JSON Schema's treatment of `format` as annotation-oriented unless an appropriate assertion capability is in use. Draft 2019-09 and 2020-12 formalize the separation between format annotation and format assertion.

### 7.2 Supported format families

| Family                    | Selected formats                               | Optional implementation requirements                                     |
| ------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------ |
| Date and time             | `date`, `date-time`, `time`, `duration`        | `rfc3339-validator`, `isoduration` for applicable formats                |
| URI and IRI               | `uri`, `uri-reference`, `iri`, `iri-reference` | `rfc3987`, `rfc3987-syntax`, or `rfc3986-validator`, depending on format |
| Network identifiers       | `hostname`, `idn-hostname`, `ipv4`, `ipv6`     | `fqdn`, `idna`, platform socket support where needed                     |
| JSON references           | `json-pointer`, `relative-json-pointer`        | `jsonpointer`                                                            |
| Templates and identifiers | `uri-template`, `uuid`                         | `uri-template` for URI templates                                         |
| Other text formats        | `regex`, `email`, `idn-email`, `color`         | `webcolors` for color; other checks vary                                 |

Two distribution extras are provided:

- `jsonschema[format]` — includes additional format-checking dependencies.
- `jsonschema[format-nongpl]` — provides an alternative intended to avoid GPL-licensed dependencies.

The extras have dependency and licensing implications, but they do not automatically activate format checking.

There are also portability distinctions:

- `regex` and schema `pattern` use Python regular-expression semantics, rather than guaranteeing full ECMA-262 compatibility.
- `email` validation is a pragmatic sanity check, not a guarantee of complete RFC conformity, mailbox existence or deliverability.
- An application-specific format definition may not be recognized by a different JSON Schema implementation.

For stricter domain-specific identifiers, a named custom `FormatChecker` implementation can make the semantics explicit for a controlled set of consumers. For universally portable schemas, ordinary JSON Schema assertions remain the more interoperable foundation where they can express the necessary rule.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/validate/#validating-formats` and `https://python-jsonschema.readthedocs.io/en/stable/faq/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



## 8. Semantic boundaries and correctness considerations

Several important distinctions determine whether validation results are portable, reproducible, and sufficient for a larger operation.

### 8.1 Python objects versus the JSON data model

Although its name refers to JSON, `jsonschema` generally operates on deserialized Python objects, not raw JSON documents.

Consequently, it can validate data parsed from YAML, TOML, or another format when the resulting Python values correspond to JSON's data model. It does not itself parse these formats.

The boundary becomes important with values JSON cannot represent directly:

- YAML permits non-string mapping keys; JSON Schema object-key constraints assume string property names.
- Python can represent non-finite floating-point values, complex numbers, arbitrary custom objects, and other values outside ordinary JSON.
- Python's equality and numeric behavior are not always identical to the abstract JSON data model.
- Custom `TypeChecker` predicates can intentionally accept additional Python representations, but do not guarantee their portability.

When the intended contract is interchange-compatible JSON, an explicit normalization or serialization boundary can be more important than expanding the set of Python types accepted by the validator.

Source: `https://python-jsonschema.readthedocs.io/en/stable/faq/#can-jsonschema-be-used-to-validate-yaml-toml-etc`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation



### 8.2 Missing values, null values, and structural conditions

Several common sources of apparent validation inconsistency are deliberate JSON Schema semantics.

| Distinction                                           | Consequence                                                                  |
| ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| Missing property versus `null`                        | `required` checks presence; `"type": "null"` checks a present value          |
| `properties` versus `required`                        | Declaring a property schema does not make the property mandatory             |
| `type` versus other type-specific keywords            | A numeric constraint does not inherently assert that the instance is numeric |
| `enum` versus `const`                                 | `enum` permits listed values; `const` requires one specified value           |
| `anyOf` versus `oneOf`                                | One or more matching branches versus exactly one                             |
| `pattern` versus full-string matching                 | Regex patterns need explicit anchors when full-string matching is intended   |
| `additionalProperties` versus `unevaluatedProperties` | Local property accounting versus composition-aware evaluation                |
| `default` versus data transformation                  | A default is an annotation, not an instruction to populate the instance      |

For example, `minimum: 0` without `type: "number"` does not prohibit strings. Numeric keywords apply to numeric instances; additional typing constraints are needed to disallow other kinds of values.

These are properties of the specification, not exceptional behavior of the Python implementation.

Sources: `https://json-schema.org/draft/2020-12/json-schema-validation` and `https://json-schema.org/understanding-json-schema/reference/object`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://json-schema.org\&sz=32)

json-schema.org+1



### 8.3 Annotations are not transformations

JSON Schema includes metadata useful for documentation, user interfaces, schema evolution and downstream processing.

Examples include `title`, `description`, `default`, `examples`, `readOnly`, `writeOnly`, and `deprecated`.

`jsonschema` does not automatically transform instance data based on these annotations.

Two advanced consequences deserve attention.

Default values: The documentation shows how to extend the `properties` validator to insert defaults, but this creates a mutating validation operation. Nested defaults require containing objects to exist, and mutation may interact poorly with schema checking or alternative validation branches. The standard non-mutating behavior avoids these complications.

String-encoded content: The Draft 2020-12 keywords `contentEncoding`, `contentMediaType`, and `contentSchema` describe encoded content and its interpretation. They are not automatic instructions for the Python library to decode base64, parse embedded JSON, verify a media type, or validate a nested document.

A system requiring those operations needs an explicit decoding and content-validation capability in addition to ordinary structural validation.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/faq/` and `https://json-schema.org/draft/2020-12/json-schema-validation`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+1



### 8.4 Resource consumption and untrusted inputs

`jsonschema` is a general-purpose validation engine, not a resource-isolation mechanism.

Potentially expensive work includes:

- Deeply nested schemas and instances.
- Extensive or overlapping `anyOf`, `oneOf`, and `allOf` branches.
- Regex evaluation with pathological input patterns.
- Repeated validation of large arrays or complex uniqueness constraints.
- Recursively referenced schemas.
- Large diagnostic collections produced by `iter_errors()`.
- Reference retrieval from untrusted or insufficiently constrained sources.
- Custom keyword and format-checker execution.

Some of these costs arise from the logical complexity of the schema rather than inefficiency in the implementation.

The practical distinctions are validity-only versus comprehensive diagnostics, known schemas versus untrusted schemas, and bounded local resources versus arbitrary reference retrieval.

For high-volume repeated validation, class selection, schema checking, registry construction and dependency setup can be performed separately from individual instance evaluations. That reduces repeated setup work, but does not turn `jsonschema` into an ahead-of-time compiled validator or guarantee a specific performance level.

The specifications also explicitly discuss security implications of automatic processing of string-encoded content.

Sources: `https://python-jsonschema.readthedocs.io/en/stable/validate/`, `https://python-jsonschema.readthedocs.io/en/stable/referencing/`, and `https://json-schema.org/draft/2020-12/json-schema-validation`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-jsonschema.readthedocs.io\&sz=32)

jsonschema 4.26.0 documentation+2



## 9. Companion libraries and ecosystem boundaries

The broader `python-jsonschema` ecosystem is worth understanding because several capabilities commonly associated with `jsonschema` actually belong to separate packages.

| Library                     | Role                                                                     | Relationship and boundary                                                               |
| --------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `referencing`               | Schema-resource registries, resolution and URI/anchor interpretation     | Core dependency; handles reference infrastructure independently of assertion validation |
| `jsonschema-specifications` | Official JSON Schema meta-schemas and vocabulary resources               | Core dependency; provides reusable reference resources                                  |
| `rpds-py`                   | Python bindings for Rust-backed persistent data structures               | Core dependency; supports persistent collection infrastructure                          |
| `attrs`                     | Python class/declarative object infrastructure                           | Core dependency; not a model-validation substitute                                      |
| `check-jsonschema`          | CLI, file validation, pre-commit integrations, configuration-file checks | Separate command-line tooling that builds on JSON Schema validation                     |
| `hypothesis-jsonschema`     | Generation of Hypothesis strategies from JSON Schemas                    | Separate test-data generation package, with its own draft coverage and constraints      |
| `PyYAML`, TOML parsers      | Deserialize non-JSON source formats                                      | External parsing layer; `jsonschema` validates resulting Python instances               |

The first four are declared runtime dependencies of `jsonschema` 4.26.0. Their versions are independently resolved by package management.

Verified dependency definitions: `https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/pyproject.toml`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 9.1 `check-jsonschema`: the recommended CLI layer

The `jsonschema` distribution still includes a `jsonschema` executable, but that built-in CLI is deprecated and its upstream source explicitly directs users to `check-jsonschema`.

`check-jsonschema` supports file-oriented validation workflows, including pre-commit hooks and checks for common configuration formats and schemas. This is a different role from the Python library's in-process validation APIs.

It adds workflow capabilities such as managing schema selection, validating files and presenting command-line diagnostics; it does not redefine the underlying JSON Schema specification.

Sources:

- `https://github.com/python-jsonschema/check-jsonschema`
- `https://check-jsonschema.readthedocs.io/en/stable/`
- `https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/jsonschema/cli.py`&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

  GitHub+1



### 9.2 `hypothesis-jsonschema`: schema-driven test-data generation

`hypothesis-jsonschema.from_schema()` converts supported JSON Schemas into Hypothesis strategies that generate conforming data.

This creates a complementary direction of use:

- `jsonschema`: instance → validation result.
- `hypothesis-jsonschema`: schema → generated candidate instances.
- Hypothesis: generated instances → repeated property-based test execution.

The combination can help exercise consumers of a schema and investigate how they behave across valid input variations.

However, generation support must not be inferred from the validator's draft support. The companion project's documentation identifies its own tested dialects and limitations, including specific constraints around reference resolution. Its custom-format handling likewise involves generation strategies rather than merely importing `FormatChecker` behavior.

Source: `https://github.com/python-jsonschema/hypothesis-jsonschema`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 9.3 Relationship to Python-native validation systems

The central architectural choice is between a portable schema language and a runtime-native Python type/model system.

`jsonschema` is particularly expressive when schemas must remain independent of Python class definitions, be distributed as data, compose across URI-addressed resources, or support multiple JSON Schema dialects.

Python-native validation libraries instead often emphasize model construction, type-driven parsing, coercion, serialization and developer ergonomics around Python classes.

These capabilities are not mutually exclusive. One layer can normalize external data into a defined representation while JSON Schema governs a portable interchange contract. Conversely, validating the same constraints independently in two systems can introduce drift if their semantics are not deliberately aligned.

The important distinction is where the authoritative contract lives: in a JSON Schema document with implementation-independent meaning, or in an application-specific Python type and validation model.

## 10. High-value capability combinations

Individual API features become more significant when composed. Several combinations create general architectural options without requiring bespoke validation infrastructure.

| Combination                                    | What it enables                                                      | Main qualification                                               |
| ---------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `Registry` + `$id`/`$ref` + schema packages    | Modular, URI-addressable schema collections                          | Resource identity and retrieval policy must be controlled        |
| `Registry` + `evolve()`                        | Reusing reference and checker configuration across schemas           | Dialect changes can select a different validator class           |
| `check_schema()` + reusable validators         | Separate schema integrity checking from repeated instance validation | Schema and registry contents should remain stable                |
| `allOf` + `$defs` + `unevaluatedProperties`    | Composable object contracts with outer-level closure                 | Requires careful evaluation-aware schema design                  |
| `$dynamicRef` + `$dynamicAnchor`               | Extensible recursive data definitions                                | Requires Draft 2020-12 semantics and appropriate reference scope |
| `iter_errors()` + `ErrorTree` + `best_match()` | Rich field-level diagnostics and prioritized failure reporting       | Error ordering and heuristic ranking are not fixed guarantees    |
| `validators.extend()` + `TypeChecker`          | Domain-adapted assertions over Python-native data                    | May reduce portability or change performance                     |
| `FormatChecker` + explicit format dependencies | Opt-in semantic validation of identifiers and other primitives       | Unknown or unavailable formats pass                              |
| JSON Schema + `hypothesis-jsonschema`          | Contract-derived property-based test inputs                          | Generator draft coverage differs from validator coverage         |

These combinations illustrate the library's broader role: it can provide a shared, declarative validation language while delegating resource storage, data parsing, transformation, test generation and command-line orchestration to specialized layers.

## 11. Version, compatibility, and maturity

For `jsonschema` 4.26.0, the published metadata specifies Python 3.10 or later and includes Python 3.14 classifiers. The package is designated stable, but companion projects such as `referencing` and `hypothesis-jsonschema` maintain their own versioning and compatibility commitments.

The release's stated change is a reduction in import-time work through delayed importing of `urllib.request`; this should not be mistaken for a fundamental change in validation or reference-resolution semantics.

Important compatibility distinctions:

- Validator classes and public methods are part of the supported API; subclassing generated validator classes is not a supported extension interface.
- `RefResolver` and the legacy `resolver=` pathway are deprecated.
- The bundled CLI is deprecated in favor of `check-jsonschema`.
- Global `FormatChecker.cls_checks()` registration is deprecated.
- Exact validation-error messages, diagnostic ordering and command-line output representation are not covered by the same stability guarantees as public method signatures.
- JSON Schema draft compatibility is independent of Python package version compatibility.
- A schema lacking `$schema` relies on the library's default draft selection, making implicit dialect assumptions less durable.

Sources: `https://pypi.org/project/jsonschema/`, `https://python-jsonschema.readthedocs.io/en/stable/faq/`, and `https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/CHANGELOG.rst`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 12. Primary-source reference map

The following direct sources cover the most important implementation and semantic details:

| Topic                                 | Source URL                                                                   |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| Validation API and validator protocol | `https://python-jsonschema.readthedocs.io/en/stable/validate/`               |
| Creating and extending validators     | `https://python-jsonschema.readthedocs.io/en/stable/creating/`               |
| Structured error diagnostics          | `https://python-jsonschema.readthedocs.io/en/stable/errors/`                 |
| Reference-resolution integration      | `https://python-jsonschema.readthedocs.io/en/stable/referencing/`            |
| Referencing public API                | `https://referencing.readthedocs.io/en/stable/api/`                          |
| Schema package architecture           | `https://referencing.readthedocs.io/en/stable/schema-packages/`              |
| Official meta-schema registry         | `https://jsonschema-specifications.readthedocs.io/en/stable/`                |
| JSON Schema Draft 2020-12 core        | `https://json-schema.org/draft/2020-12/json-schema-core`                     |
| JSON Schema Draft 2020-12 validation  | `https://json-schema.org/draft/2020-12/json-schema-validation`               |
| Draft 2020-12 changes                 | `https://json-schema.org/draft/2020-12/release-notes`                        |
| Tagged implementation source          | `https://github.com/python-jsonschema/jsonschema/tree/v4.26.0`               |
| Changelog and release history         | `https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/CHANGELOG.rst` |

### Overall architectural significance

The most distinctive strength of `jsonschema` is its separation of portable, declarative schema semantics from Python-specific validation execution, reference management, diagnostics and extension mechanisms.

That separation permits substantially richer systems than one-off field validation: compositional contracts, recursive and dynamically extended schemas, reusable schema registries, schema-aware diagnostics and selectively customized validation semantics.

Its most important limitations arise from the same design: it deliberately does not own coercion, instance transformation, schema-driven model generation, arbitrary external resource retrieval or enforcement of every format annotation. Understanding those boundaries is essential to using its advanced capabilities correctly.