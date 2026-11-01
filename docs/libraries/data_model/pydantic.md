# Pydantic — Comprehensive Python Library Capability Reference

Target version: 2.14.1 (latest stable, released October 11, 2026) Research date: October 20, 2026 Official documentation: [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/?utm_source=chatgpt.com) Source repository: [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic?utm_source=chatgpt.com)

Pydantic is a Python data validation, parsing, serialization, and schema-generation library built around Python type annotations. Its distinguishing architectural feature is the compilation of declarative Python type definitions into executable validation and serialization schemas backed by `pydantic-core`, a Rust implementation.

Pydantic is substantially more than a convenient way to validate dictionaries or deserialize API payloads. It offers a composable runtime type system that can define and enforce data contracts, transform external representations into typed Python objects, generate machine-readable schemas, adapt third-party types, and provide consistent validation and serialization across multiple application boundaries.

Version 2.14.1 is the current stable release, supporting Python 3.10–3.15. Version 2.14 introduces additional core schema capabilities and drops Python 3.9 support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



## 1. Conceptual model and capability map

Pydantic's central abstraction is a type-driven executable schema, not the model class itself.

A Python type definition is interpreted and converted into an intermediate representation known as a core schema. That schema describes parsing, type checking, constraints, conversion, composition, custom validation, and serialization behavior. The Rust-backed execution engine subsequently applies that schema to data.

Conceptual execution architecture. JSON Schema generation is a separate translation from the Pydantic core schema, not the runtime validation engine.

This separation has important consequences:

- Type declarations are reusable executable contracts. Validation need not be tied to a particular API framework, ORM, configuration system, or application layer.
- Schemas compose recursively. Models, containers, unions, constraints, custom types, and validators combine into a single validation structure.
- Validation and serialization are related but distinct operations. Input acceptance, internal representations, and output representations need not be identical.
- Schema generation happens separately from runtime execution. Building and compiling schemas has a cost; repeated validation can reuse the resulting machinery.
- Python remains extensible. Custom Python validation and serialization functions can participate in the engine, although crossing back into Python has performance implications.

The official architectural explanation is at [https://docs.pydantic.dev/latest/internals/architecture/](https://docs.pydantic.dev/latest/internals/architecture/?utm_source=chatgpt.com).

### Major capability families

| Capability                 | Principal mechanisms                                                       |
| -------------------------- | -------------------------------------------------------------------------- |
| Structured data modeling   | `BaseModel`, `RootModel`, generics, nested models, dynamic models          |
| General-purpose validation | `TypeAdapter`, `validate_call`, Pydantic dataclasses                       |
| Declarative constraints    | `Field`, `Annotated`, constrained types, reusable validators               |
| Structural variation       | Unions, discriminators, recursive types, `TypedDict`, named aliases        |
| Validation behavior        | Strictness, coercion, validator ordering, model configuration              |
| Serialization              | Field/model serializers, computed fields, inclusion/exclusion, aliases     |
| Schema interoperability    | JSON Schema, custom schema generators, core schema hooks                   |
| Extension mechanisms       | Custom type schemas, `GetPydanticSchema`, functional validators            |
| Operational integration    | Configuration, APIs, static analysis, observability, code generation       |
| Specialized capabilities   | Partial JSON validation, dynamic schema rebuilding, experimental pipelines |

Pydantic should be understood primarily as an in-process data-contract and conversion engine. It does not itself provide database persistence, database constraints, query optimization, service orchestration, or a general-purpose incremental computation system.

## 2. Data modeling and schema surfaces

Pydantic provides several ways to associate an executable schema with a Python type. These are complementary interfaces over the same underlying validation architecture, rather than entirely different validation systems.

### 2.1 BaseModel: rich structured objects

`BaseModel` defines classes with typed fields, defaults, validators, serializers, configuration, and generated introspection metadata.

Key functionality includes:

- Recursive construction of nested model instances from mappings.
- Inheritance, model composition, abstract base classes, generic parameterization, and structured pattern matching.
- `model_validate()`, `model_validate_json()`, and `model_validate_strings()` for distinct input forms.
- `model_dump()` and `model_dump_json()` for output representation.
- `model_fields` and `model_computed_fields` for runtime schema introspection.
- `model_fields_set` for tracking explicitly provided fields.
- `model_extra` and `__pydantic_extra__` for retained additional fields.
- `model_rebuild()` for resolving incomplete or deferred schemas.
- `model_post_init()` and `PrivateAttr` for initialization logic and non-field state.

A useful distinction is that Pydantic models are validated representations of data, not immutable proofs that the data will remain valid.

By default, assigning a new attribute value does not revalidate it. `validate_assignment=True` adds assignment-time validation, while `revalidate_instances` controls revalidation of existing model/dataclass instances when encountered as input. Neither mechanism establishes deep, persistent immutability of mutable objects held in fields.

Similarly, `frozen=True` prevents ordinary reassignment but does not recursively freeze nested mutable structures.

Validation bypasses matter:

`model_construct()` creates objects without running validation, and `model_copy(update=...)` does not validate its updates. These are explicitly different from constructing a freshly validated model. `model_construct()` is not necessarily faster for simple models in Pydantic V2.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



Source: [https://pydantic.dev/docs/validation/latest/concepts/models/](https://pydantic.dev/docs/validation/latest/concepts/models/?utm_source=chatgpt.com)

### 2.2 TypeAdapter: validation without a model class

`TypeAdapter` is one of Pydantic V2's most consequential architectural capabilities.

It constructs validation, serialization, and schema-generation machinery for an arbitrary supported type expression:

```
from typing import Annotatedfrom pydantic import Field, TypeAdapterPositive = Annotated[int, Field(gt=0)]adapter = TypeAdapter(list[Positive])values = adapter.validate_json(b"[1, 2, 3]")schema = adapter.json_schema()output = adapter.dump_json(values)
```

Illustrative, unexecuted example.

The adapter can work with `list[T]`, `dict[K, V]`, unions, `TypedDict`, standard dataclasses, primitive types, and nested combinations of these.

Important implications:

1. Validation does not require an object-oriented model. Existing structural types can become runtime-enforced data contracts.
2. Container-level validation becomes reusable. An entire collection can be validated under one schema instead of explicitly constructing and validating each element.
3. Data can remain in native Python structures. `TypedDict` validation, for example, produces dictionaries rather than model objects.
4. Validation and serialization remain available together. An adapter exposes `validate_python`, `validate_json`, `dump_python`, `dump_json`, and `json_schema`.
5. Compilation can be amortized. Reusing an adapter avoids repeatedly preparing the same schema.

A subtle API distinction: `TypeAdapter.dump_json()` returns `bytes`, whereas `BaseModel.model_dump_json()` returns `str`.

`TypeAdapter` also supports schema rebuilding and, in modern releases, improved static return-type inference through `TypeForm`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Source: [https://pydantic.dev/docs/validation/latest/concepts/type_adapter/](https://pydantic.dev/docs/validation/latest/concepts/type_adapter/?utm_source=chatgpt.com)

### 2.3 Additional modeling interfaces

| Interface                   | Distinct capability                                                                                                          |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `RootModel[T]`              | A named model whose root is a list, scalar, mapping, union, or another supported type, rather than a mapping of named fields |
| Pydantic `@dataclass`       | Runtime validation integrated with standard dataclass-oriented object design                                                 |
| `TypedDict` + `TypeAdapter` | Typed mapping validation without allocating custom model instances                                                           |
| `NamedTuple`                | Validated tuple-like structured values                                                                                       |
| `@validate_call`            | Runtime validation of annotated function arguments, with optional return validation                                          |
| `create_model()`            | Runtime creation of complete model classes from dynamic field definitions                                                    |
| Generic `BaseModel`         | Parameterized reusable contracts, with support for both traditional generics and PEP 695 syntax                              |

Dataclasses are not BaseModel substitutes with identical semantics. Pydantic dataclasses retain much of the standard dataclass object model but do not inherit `BaseModel`'s instance methods. `TypeAdapter` supplies validation, serialization, and JSON Schema operations where required.

Dynamic models are actual model types. `create_model()` can include a base class, field definitions, configuration, and class behavior. Version 2.14 adds `__namespace__` for attaching validators, methods, and computed fields through a general class namespace; it is intended to supersede the narrower `__validators__` parameter in a future major version.

Generic specialization has runtime consequences. Unparameterized type variables fall back to bounds, defaults, or `Any`, as appropriate. In some cases this loses type information or results in a different serialization representation; generic types are not merely static type-checker decorations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/dataclasses/](https://pydantic.dev/docs/validation/latest/concepts/dataclasses/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/concepts/validation_decorator/](https://pydantic.dev/docs/validation/latest/concepts/validation_decorator/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/concepts/models/](https://pydantic.dev/docs/validation/latest/concepts/models/?utm_source=chatgpt.com)

## 3. Type semantics, constraints, and declarative validation

### 3.1 Standard-library and specialized type support

Pydantic understands a broad selection of standard Python and `typing` types, including:

- Scalars such as `int`, `float`, `str`, `bool`, `Decimal`, `Fraction`, and `complex`.
- Temporal values such as `date`, `datetime`, `time`, and `timedelta`.
- Containers including mappings, sequences, tuples, sets, deques, ordered dictionaries, and counters.
- `Enum`, `Literal`, `UUID`, `Path`, `IP address`, `TypedDict`, dataclasses, named tuples, and generics.
- `Union`, `Annotated`, recursive named aliases, and other compound type expressions.

Pydantic also defines richer domain-oriented types, including `EmailStr`, `NameEmail`, network URLs, secret strings and bytes, encoded bytes, JSON values, string constraints, UUID version aliases, and base64 representations.

The companion `pydantic-extra-types` package adds types for domains such as currency, country and language identifiers, colors, payment cards, coordinates, and time zones.

This provides a reusable vocabulary of data semantics that would otherwise require application-specific parsing and validation classes.

Version 2.14 moves several previously Python-validated types—`Fraction`, named tuples, `deque`, `OrderedDict`, and `Counter`—to native Rust core schemas, improving their integration with constraints and reducing Python validation overhead.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources:

- [https://pydantic.dev/docs/validation/latest/api/standard_library_types/](https://pydantic.dev/docs/validation/latest/api/standard_library_types/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/api/types/](https://pydantic.dev/docs/validation/latest/api/types/?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic-extra-types](https://github.com/pydantic/pydantic-extra-types?utm_source=chatgpt.com)

### 3.2 Annotated types as reusable semantic contracts

Python's `Annotated` construct is especially important because it enables constraints, validators, serializers, and metadata to be attached to types without creating a new runtime Python subclass.

For example:

```
from typing import Annotatedfrom pydantic import AfterValidator, Fielddef normalize_code(value: str) -> str:    return value.strip().upper()Code = Annotated[    str,    Field(min_length=2, max_length=20),    AfterValidator(normalize_code),]Codes = list[Code]
```

The `Code` type carries reusable semantics into any model, container, or adapter that references it.

The associated mechanisms include `Field`, `StringConstraints`, `Strict`, `BeforeValidator`, `AfterValidator`, `PlainValidator`, `WrapValidator`, and schema metadata utilities such as `WithJsonSchema`.

This can eliminate duplicated field definitions and validation functions across otherwise unrelated model types.

`Field` supports numeric bounds, multiplicity, decimal precision, string length/patterns, collection constraints, immutability, exclusion behavior, and documentation metadata.

A consequential limitation is that static type checkers do not interpret every `Annotated` metadata item. In particular, defaults, default factories, and aliases that influence synthesized constructors are better expressed using standard field assignment syntax when static constructor fidelity matters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/concepts/fields/](https://pydantic.dev/docs/validation/latest/concepts/fields/?utm_source=chatgpt.com)

### 3.3 Coercive validation versus strict type enforcement

Pydantic defaults to a permissive conversion model. For example, a numeric string may be accepted as an integer.

Strict mode narrows allowable conversions and can be applied:

- Per validation invocation, through `strict=True`.
- Per field, through `Field(strict=True)` or strict type metadata.
- Per model, through `ConfigDict(strict=True)`.

It is important not to interpret strict mode as a universal prohibition of conversion. Python-input and JSON-input validation have different type representations. A JSON string representing a date, for example, may be accepted in strict JSON validation even though a Python `str` would be rejected in strict Python validation.

The library publishes a detailed type-by-type conversion table, including accepted sources, validation modes, and strictness behavior. This is the authoritative source for conversion decisions rather than assumptions based on Python subclass relationships.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/strict_mode/](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/concepts/conversion_table/](https://pydantic.dev/docs/validation/latest/concepts/conversion_table/?utm_source=chatgpt.com)

### 3.4 Missing, null, defaulted, and explicitly provided values

Pydantic distinguishes several concepts that are often conflated in application code.

| Concept                      | Meaning                                                           |
| ---------------------------- | ----------------------------------------------------------------- |
| Required field               | No default; the caller must provide a value                       |
| `T \\| None`                 | A nullable type, not automatically a non-required field           |
| `T \\| None = None`          | A non-required field with a null default                          |
| `Field(default_factory=...)` | Computes a default, potentially using previously validated fields |
| `model_fields_set`           | Records which fields were explicitly supplied                     |
| `MISSING`                    | Represents a genuinely missing value independently of `None`      |

`MISSING` became a stable API in Pydantic 2.14.

This supports a genuine three-state representation: absent, explicitly null, and populated.

```
from pydantic import BaseModel, MISSINGclass Patch(BaseModel):    timeout: int | None | MISSING = MISSINGPatch().model_dump()                 # {}Patch(timeout=None).model_dump()     # {'timeout': None}Patch(timeout=30).model_dump()       # {'timeout': 30}
```

Pydantic automatically excludes `MISSING` values from serialization, and the sentinel is omitted from the corresponding JSON Schema type representation.

This is particularly valuable for partial updates, overlays, and configuration inheritance, where absence and explicit null have different meanings.

Another easily overlooked distinction: default values are not validated by default. `validate_default=True` enables that behavior. Factories may receive already validated preceding fields, making field ordering significant.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/types/](https://pydantic.dev/docs/validation/latest/concepts/types/?utm_source=chatgpt.com)
- [https://pydantic.dev/articles/pydantic-v2-14-release](https://pydantic.dev/articles/pydantic-v2-14-release?utm_source=chatgpt.com)

## 4. Structural composition, unions, and recursive contracts

### 4.1 Union matching and discriminators

Pydantic supports several approaches to union validation, with consequential differences.

| Mechanism              | Behavior                                                   | Important distinction                                               |
| ---------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------- |
| Smart union            | Scores candidate matches and selects a preferred result    | Default; matching algorithm may change across minor releases        |
| Left-to-right union    | Tries members in declaration order                         | Predictable order, but coercion can produce surprising matches      |
| Discriminated union    | Selects a branch using a discriminator                     | Typically more efficient and clearer for explicitly tagged variants |
| Callable discriminator | Computes a tag from input, using `Discriminator` and `Tag` | Handles heterogeneous variants and nonuniform tag fields            |

A discriminated union can act as a runtime representation of a tagged algebraic data type. It can encode alternative object shapes in a single reusable type and often produce cleaner errors and machine-readable discriminator metadata.

The smart union algorithm considers matching exactness and, for structured types, the number of valid fields set. It is explicitly not guaranteed to remain identical across Pydantic minor versions. Systems that depend on precise branch selection therefore need explicit discriminator semantics or controlled union ordering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/concepts/unions/](https://pydantic.dev/docs/validation/latest/concepts/unions/?utm_source=chatgpt.com)

### 4.2 Recursive types and named schema definitions

Pydantic supports self-referential models, forward annotations, recursive named type aliases, and recursive generic types.

Important mechanisms include:

- `model_rebuild()` for models whose referenced types were not available at initial definition.
- `TypeAdapter.rebuild()` for deferred adapter schema completion.
- Named recursive aliases using `TypeAliasType` or modern Python type-alias syntax.
- Recursive schema references and definitions in core schemas.
- Detection of cyclic input structures, producing validation errors instead of uncontrolled recursion.

Pydantic also supports Python 3.15's lazy-import machinery for cross-module references in version 2.14.

The important distinction is between recursive schemas, which are natively supported, and cyclic runtime object graphs, which require deliberate treatment. Recursively nested data structures do not imply that arbitrary object identity and reference sharing will be preserved by validation or serialization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/forward_annotations/](https://pydantic.dev/docs/validation/latest/concepts/forward_annotations/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/concepts/types/](https://pydantic.dev/docs/validation/latest/concepts/types/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/internals/resolving_annotations/](https://pydantic.dev/docs/validation/latest/internals/resolving_annotations/?utm_source=chatgpt.com)

## 5. Validation pipelines, control flow, and custom semantics

Pydantic has several distinct extension mechanisms for validation. Understanding their differences is important because they affect execution order, built-in validation guarantees, performance, and schema generation.

### 5.1 Validator execution modes

| Mode        | Mechanism                                          | Distinguishing behavior                                                                 |
| ----------- | -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| After       | `AfterValidator`, `@field_validator(mode="after")` | Receives an already validated value; useful for additional invariants                   |
| Before      | `BeforeValidator`, `mode="before"`                 | Transforms or inspects raw input before ordinary validation                             |
| Plain       | `PlainValidator`, `mode="plain"`                   | Takes responsibility for validation; bypasses ordinary validation of the annotated type |
| Wrap        | `WrapValidator`, `mode="wrap"`                     | Controls whether, when, and how the underlying validation handler executes              |
| Model-level | `@model_validator`                                 | Applies before, after, or around validation of the complete model                       |

Wrap validators are particularly flexible. They can run the normal validator, inspect its errors, retry with a transformed value, or bypass the handler entirely.

Their flexibility also means that wrapping may introduce additional Python calls and complex control flow that could have been represented more efficiently using built-in schema constraints.

Plain validators require particular care: they can accept and return values that would fail the declared type's usual validation.

### 5.2 Cross-field and contextual validation

Model-level validators express relationships between fields, such as mutual exclusivity, ordering, or conditional requirements.

`ValidationInfo` provides access to relevant runtime information:

- `info.data`: previously validated fields in a field validator.
- `info.context`: caller-supplied contextual data.
- `info.mode`: whether the current input is being validated in Python or JSON mode.
- `info.field_name`: relevant field identity when available.
- Configuration information associated with validation.

The `context` argument is especially useful because it permits contextual validation without embedding runtime context into the model definition.

For example, a caller can provide a policy, locale, supported identifier set, or conversion convention during validation.

However, that contextual dependency affects reproducibility: the same input may validate differently under different contexts. It is therefore meaningful external input to the validation operation, even though it is not part of the serialized model.

Validator ordering is also defined. Within `Annotated`, before and wrap validators execute from right to left; after validators execute from left to right. Decorator validators participate in the same underlying metadata ordering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



### 5.3 Specialized validator utilities

Several additional abstractions offer narrower capabilities without requiring custom core schema implementations:

| Utility               | Purpose                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| `InstanceOf[T]`       | Require an instance of a specified Python class                                                     |
| `SkipValidation[T]`   | Deliberately bypass validation of a value                                                           |
| `ValidateAs`          | Validate through a supported intermediary type/model and transform into a custom class              |
| `PydanticUseDefault`  | Signal that a configured default should be used                                                     |
| `PydanticCustomError` | Raise a structured custom validation error with a stable error code and contextual parameters       |
| `FailFast`            | Stop validation of a supported iterable at its first error rather than accumulating all item errors |
| `OnErrorOmit`         | Omit invalid values in supported validation contexts                                                |

`ValidateAs` is particularly useful for adapting domain objects composed of multiple values. It enables an intermediate Pydantic model to handle parsing and constraints while a conversion function constructs the desired domain object.

`FailFast` provides a meaningful performance/error-reporting tradeoff: it can avoid examining the remaining elements after a failure, but sacrifices comprehensive error aggregation.

Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/validators/](https://pydantic.dev/docs/validation/latest/concepts/validators/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/concepts/types/](https://pydantic.dev/docs/validation/latest/concepts/types/?utm_source=chatgpt.com)

### 5.4 Structured validation errors

`ValidationError` offers more than a formatted error message.

Its structured details include the error location, classification, explanatory message, original input information, and sometimes contextual parameters and documentation URLs.

The `errors()` and `json()` interfaces make these diagnostics machine-readable.

Nested validation paths identify where an error occurred within models, lists, mappings, and union alternatives. Custom validators can introduce structured error codes through `PydanticCustomError`.

This provides a consistent diagnostic vocabulary for rejecting records, constructing user-facing feedback, classifying data-quality failures, and testing contracts.

A distinction worth retaining: validation exceptions reflect what was rejected under a particular schema. They do not independently establish that accepted data satisfies every application-level invariant.

Source: [https://pydantic.dev/docs/validation/latest/errors/errors/](https://pydantic.dev/docs/validation/latest/errors/errors/?utm_source=chatgpt.com)

## 6. Serialization as a separate programmable contract

Pydantic's serialization capabilities are substantial enough to treat as a distinct system rather than a side effect of validation.

### 6.1 Python and JSON output modes

`model_dump()` and `TypeAdapter.dump_python()` produce Python representations, while `model_dump_json()` and `TypeAdapter.dump_json()` produce JSON-encoded output.

Python mode can preserve non-JSON-native values such as `datetime` objects. JSON mode applies the relevant conversion rules.

Serialization can handle nested models, collection types, aliases, and configured representations of decimals, bytes, temporal values, and other special types.

### 6.2 Custom serializers and computed output

Serialization extensions include:

- `PlainSerializer` and `WrapSerializer`, attached to reusable annotated types.
- `@field_serializer`, targeting one or more model fields.
- `@model_serializer`, customizing complete model output.
- `@computed_field`, including properties and cached properties in serialized representations.
- `SerializationInfo`, exposing mode, contextual information, and serialization parameters.
- Return-type annotations or `return_type`, which can establish additional serialization validation expectations.

Wrap serializers can delegate to the native serializer and then modify its output. Plain serializers replace the normal serialization behavior.

An important constraint is that only one serializer can be defined for a given field or model. Unlike validators, serializers are not arbitrary chains of independently composed plain and wrap handlers.

`@computed_field` adds a computed value to serialization and, in serialization-mode JSON Schema, can expose it as a read-only property. It does not automatically provide cache invalidation, dependency tracking, or validation of the property calculation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



### 6.3 Selective, contextual, and policy-driven output

Pydantic supports deeply structured `include` and `exclude` specifications, as well as:

| Mechanism               | Function                                                    |
| ----------------------- | ----------------------------------------------------------- |
| `exclude_unset`         | Exclude fields that were not explicitly supplied            |
| `exclude_defaults`      | Exclude fields equal to their defaults                      |
| `exclude_none`          | Exclude null-valued fields                                  |
| `Field(exclude=True)`   | Permanently omit a field under ordinary field serialization |
| `Field(exclude_if=...)` | Conditionally exclude a field based on its value            |
| `@computed_field`       | Include derived or cached properties                        |
| `context`               | Supply runtime context to custom serializers                |
| `by_alias`              | Emit the configured external naming representation          |

The inclusion and exclusion mechanisms support nested selections rather than only top-level field names.

Contextual serializers can express transformations such as redaction, localization, or representation policy without mutating the underlying model.

However, serializer context is not a security mechanism by itself; callers must supply the correct context, and all possible output paths must honor the intended information boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



### 6.4 Schema-based versus duck-typed serialization

A particularly important V2 behavior concerns subclass serialization.

Suppose a field is annotated with a base `User` model, but its runtime value is an instance of `UserWithPassword`, which has additional fields.

By default, Pydantic V2 serializes the fields declared by the annotated base type, not every field present on the runtime subclass.

This makes serialized shapes more predictable and helps prevent accidentally exposing newly added subclass fields.

Where polymorphic output is required, Pydantic provides:

- `SerializeAsAny[T]` for type-level duck-typed serialization.
- `serialize_as_any=True` for runtime duck-typed serialization.

These options change the output contract and potentially its sensitive-data exposure. They are not merely performance settings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/concepts/serialization/](https://pydantic.dev/docs/validation/latest/concepts/serialization/?utm_source=chatgpt.com)

## 7. JSON Schema generation and machine-readable contracts

Pydantic can translate its executable type definitions into JSON Schema compatible with JSON Schema Draft 2020-12 and OpenAPI 3.1.

This makes its schemas usable outside Python for API descriptions, client generation, documentation, editor integration, schema-driven forms, and interoperability.

The generation APIs include:

- `BaseModel.model_json_schema()`
- `TypeAdapter.json_schema()`
- `TypeAdapter.json_schemas()` for generating definitions across multiple adapted types
- `models_json_schema()` for generating schemas across multiple models

### 7.1 Validation versus serialization JSON Schema

A major distinction is that Pydantic can generate two schema representations:

- `mode="validation"` describes the expected incoming representation.
- `mode="serialization"` describes the output representation.

For example, a `Decimal` field can accept numeric and string inputs in validation mode, while its JSON serialization representation is a string.

Similarly, field serializers and computed fields can affect output schemas without changing the accepted input contract.

This distinction is central when the same type participates in both inbound and outbound interfaces. A single schema is not necessarily sufficient to describe both directions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



### 7.2 Schema customization mechanisms

Pydantic provides customization at multiple levels:

| Scope                    | Mechanism                                         |
| ------------------------ | ------------------------------------------------- |
| Individual field         | `Field(title=..., description=..., examples=...)` |
| Model metadata           | `model_config`, `json_schema_extra`               |
| Reusable type metadata   | `WithJsonSchema`, `SkipJsonSchema`                |
| Custom Python type       | `__get_pydantic_json_schema__`                    |
| Global generation policy | Subclass `GenerateJsonSchema`                     |
| Naming and references    | `ref_template`, schema and field title generators |
| Direction                | Validation or serialization mode                  |

`GenerateJsonSchema` exposes overridable methods for controlling translation from core schemas into JSON Schema, rather than requiring complete replacement of the generator.

This is useful when numerous models must conform to common documentation conventions, schema dialect requirements, or compatibility rules.

### 7.3 Limits of schema equivalence

JSON Schema is not a complete representation of every Pydantic runtime behavior.

For example, an arbitrary Python callback used in a validator does not necessarily translate into an equivalent portable JSON Schema constraint.

A before validator that accepts additional input types may require `json_schema_input_type` to represent the accepted values accurately.

Likewise, custom serializers may produce outputs whose schema differs from the underlying annotated type unless suitable return metadata is supplied.

The architectural consequence is that Pydantic can serve as a highly capable schema authority, but the externally generated schema may be an approximation of the full executable contract when Python-specific behavior is involved.

Version 2.14 also changes some JSON Schema output details, including `Decimal` patterns and propagation of adapter configuration. Therefore, generated JSON Schema is a version-sensitive artifact even when model declarations have not changed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



Source: [https://pydantic.dev/docs/validation/latest/concepts/json_schema/](https://pydantic.dev/docs/validation/latest/concepts/json_schema/?utm_source=chatgpt.com)

## 8. External representations, aliases, and model configuration

### 8.1 Input and output naming are independent

Pydantic can map between external field naming conventions and internal Python identifiers.

The relevant mechanisms are:

- `Field(alias=...)`: a general field alias.
- `Field(validation_alias=...)`: an input-specific alias.
- `Field(serialization_alias=...)`: an output-specific alias.
- `AliasPath`: extract an input value from a nested mapping or indexed structure.
- `AliasChoices`: accept multiple alternative input locations, with ordered precedence.
- `AliasGenerator`: define separate systematic naming transformations for input and output.
- `alias_priority`: control precedence between explicit and generated aliases.

`AliasPath` is more capable than simple renaming: it can extract a field from a nested source structure, including indexed list elements. `AliasChoices` can combine flat and nested alternatives, supporting multiple inbound representations through one model definition.

These mechanisms can reduce custom mapping code, particularly when multiple external versions or naming conventions must map to the same internal contract.

However, aliases are not a general-purpose bidirectional transformation language. A nested `AliasPath` defines where a value is read; it does not automatically reconstruct the same nested source structure during serialization. More complex output projections still require serializers or explicit representation models.

Pydantic also separates configuration-time alias behavior from runtime choices such as validating by name or alias and serializing with `by_alias`. Explicit field aliases normally override generated aliases unless priority rules change that behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



Source: [https://pydantic.dev/docs/validation/latest/concepts/alias/](https://pydantic.dev/docs/validation/latest/concepts/alias/?utm_source=chatgpt.com)

### 8.2 ConfigDict: control over validation policy

`ConfigDict` defines model-level or adapter-level behavior, including:

| Policy area               | Representative controls                                            |
| ------------------------- | ------------------------------------------------------------------ |
| Unknown input fields      | `extra='ignore'`, `'forbid'`, or `'allow'`                         |
| Type conversion           | `strict`, `coerce_numbers_to_str`, string normalization settings   |
| Mutation behavior         | `validate_assignment`, `frozen`                                    |
| Existing object handling  | `revalidate_instances`                                             |
| Attribute extraction      | `from_attributes`                                                  |
| Naming                    | Alias generators, alias/name validation and serialization policies |
| Defaults and enums        | `validate_default`, `use_enum_values`                              |
| Arbitrary Python types    | `arbitrary_types_allowed`                                          |
| Representation            | JSON serialization settings, error configuration                   |
| Schema construction       | `defer_build`                                                      |
| Observability integration | `plugin_settings`                                                  |

Two distinctions are especially significant.

Unknown-field handling changes the contract. With `extra='ignore'`, unexpected keys are silently discarded. With `extra='forbid'`, the same inputs produce errors. With `extra='allow'`, they are retained, and the optional `__pydantic_extra__` annotation can specify their value type for validation.

`from_attributes=True` changes the input interface. It allows model validation to obtain field values from object attributes rather than only mappings. That can simplify conversion from ORM instances or other Python objects, but it does not automatically make attribute access side-effect-free or prevent lazy-loading behavior in an external ORM.

Configuration inheritance also requires attention:

- Subclasses of a Pydantic model inherit and merge model configuration.
- Nested Pydantic models and Pydantic dataclasses form configuration boundaries; the parent model's configuration does not simply propagate into them.
- Standard dataclasses and `TypedDict` types can receive configuration through `__pydantic_config__` or `@with_config`, with different propagation behavior.
- Passing configuration directly to a `TypeAdapter` wrapping a type that already owns its configuration is not permitted.

The official documentation also notes a multiple-inheritance caveat: Pydantic's configuration merge behavior does not fully follow the Python method-resolution order.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/config/](https://pydantic.dev/docs/validation/latest/concepts/config/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/api/config/](https://pydantic.dev/docs/validation/latest/api/config/?utm_source=chatgpt.com)

## 9. Lower-level schema extensibility

Pydantic's higher-level validators and field metadata cover many requirements, but its most powerful extension point is the ability to participate directly in core schema construction.

### 9.1 Custom core schema hooks

The principal interface is:

`__get_pydantic_core_schema__(source_type, handler)`

This can be implemented on a custom type or on an object used as `Annotated` metadata.

The handler represents the next stage of schema generation. An implementation may delegate to it, wrap its result, or provide a schema built from other core schema components.

Using `pydantic_core.core_schema`, advanced extensions can compose mechanisms such as:

- Primitive and container schemas.
- Union and tagged-union schemas.
- Instance checks.
- Validator functions before, after, or around native validation.
- Chains of intermediate validation stages.
- Separate Python-input and JSON-input schemas.
- Custom serialization functions.
- Recursive references and shared definitions.

This enables a third-party Python type to acquire Pydantic-native validation and serialization without requiring the third-party class to inherit `BaseModel`.

For instance, an adapter can accept an existing instance of a custom type when validating Python objects, accept an integer when validating JSON, construct the custom type from that integer, and serialize the result back into a scalar.

A matching `__get_pydantic_json_schema__` hook can define the externally visible JSON Schema.

The important architectural distinction is that custom core schemas are compositions of schema node kinds already understood by `pydantic-core`. The extension mechanism does not allow users to introduce arbitrary new Rust validator node kinds. Pydantic's internal `GenerateSchema` implementation is also not presented as a general public extension interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



### 9.2 Extension hierarchy and tradeoffs

| Extension level                                             | Capability                                                   | Relative considerations                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `Field`, `Annotated`, standard constraints                  | Declarative behavior                                         | Usually simplest; maximizes native engine use                                 |
| Functional validators and serializers                       | Custom Python transformations                                | Expressive, with callback overhead                                            |
| `ValidateAs` and annotated type composition                 | Adapt external objects through existing schemas              | Reuses well-supported validation semantics                                    |
| `GetPydanticSchema`                                         | Define a reusable custom core-schema transformation          | Reduces boilerplate for schema customization                                  |
| `__get_pydantic_core_schema__`                              | Full composition of supported core-schema nodes              | Greater power, complexity, and compatibility sensitivity                      |
| Direct `pydantic_core.SchemaValidator` / `SchemaSerializer` | Execute a manually assembled schema without a Pydantic model | Useful for specialized engines, but more low-level maintenance responsibility |

There is an important performance distinction between a core schema that invokes Python callbacks and one that represents an operation entirely through Rust-native schema nodes. Both use the same engine, but the former still incurs Python execution costs.

Custom schema hooks are powerful but intentionally lower-level than standard Pydantic field APIs. The official documentation cautions that their interface may change more readily than mainstream validation APIs.

Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/types/](https://pydantic.dev/docs/validation/latest/concepts/types/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/internals/architecture/](https://pydantic.dev/docs/validation/latest/internals/architecture/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/api/pydantic_core_schema/](https://pydantic.dev/docs/validation/latest/api/pydantic_core_schema/?utm_source=chatgpt.com)

### 9.3 Plugin interception and validation observability

Pydantic also exposes a separate plugin mechanism around compiled validators.

Plugins can intercept `validate_python`, `validate_json`, and `validate_strings` operations, observing inputs, outcomes, and errors. This operates at a different layer from custom field validators: it is designed for cross-cutting instrumentation rather than expressing domain constraints.

`plugin_settings` provides per-model plugin configuration.

Pydantic Logfire uses this capability to instrument validation behavior without requiring individually instrumented model calls. The observability service and its recording behavior belong to the separate Logfire package, not to Pydantic's core validation functionality.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources:

- [https://pydantic.dev/docs/validation/latest/internals/architecture/](https://pydantic.dev/docs/validation/latest/internals/architecture/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/integrations/logfire/](https://pydantic.dev/docs/validation/latest/integrations/logfire/?utm_source=chatgpt.com)

## 10. JSON parsing, partial data, and experimental capabilities

### 10.1 Native JSON parsing

Pydantic uses the Rust-backed `jiter` JSON parser through `pydantic-core`.

The primary interfaces are:

- `BaseModel.model_validate_json()`
- `TypeAdapter.validate_json()`
- `pydantic_core.from_json()`

JSON validation is not equivalent to parsing JSON into ordinary Python objects and then invoking Python-mode validation. The two paths can apply different conversion rules because JSON has fewer native types than Python.

For example, strict JSON validation can accept ISO-formatted date strings or JSON arrays representing tuples, whereas strict Python-mode validation would reject equivalent Python strings or lists.

The parser also supports nonstandard numeric values such as `NaN` and infinity. These behaviors are relevant when the expected data format is more restrictive than Pydantic's accepted representation.

`jiter` supports string caching, controlled through `cache_strings`, which can reduce repeated string allocation under suitable workloads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/concepts/json/](https://pydantic.dev/docs/validation/latest/concepts/json/?utm_source=chatgpt.com)

### 10.2 Partial JSON parsing

`pydantic_core.from_json(..., allow_partial=True)` can parse the completed portion of an incomplete JSON document.

This is distinct from ordinary schema validation: it parses a JSON prefix, potentially producing a Python value that can subsequently be validated.

Its useful application shapes include incrementally received JSON and incomplete generated outputs. But its output should not be confused with a complete, validated original document.

### 10.3 Experimental partial validation

Pydantic additionally provides `experimental_allow_partial` on relevant `TypeAdapter` validation methods.

Supported modes include:

- `False` or `"off"`: ordinary validation.
- `True` or `"on"`: permit partial validation.
- `"trailing-strings"`: additionally retain incomplete trailing string content.

This can validate the usable portion of a partially received collection. It is especially relevant to streaming JSON generation.

However, its documented limitations are substantial:

1. Partial behavior currently works for selected collection validators, including lists, sets, mappings, and certain `TypedDict` cases.
2. `BaseModel` does not generally propagate partial-validation behavior throughout nested model fields.
3. Validation can ignore errors in the final field or element.
4. Consequently, some invalid but complete inputs can be accepted.

The fourth point means experimental partial validation is inappropriate as the sole authoritative validation step for a complete record. It is better understood as a provisional validation mechanism for incomplete data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+2



### 10.4 Experimental pipeline API

The experimental `pydantic.experimental.pipeline` API offers a declarative composition language for validation and transformation.

The principal `validate_as()` mechanism supports chaining operations such as:

- Validation against an intermediate type.
- Constraints on numeric values, strings, and lengths.
- Transformations and predicates.
- Alternative branches using `|`.
- Composed stages using `&`.

Conceptually, it provides a pipeline representation for operations that might otherwise require several annotated validators.

This is valuable because it makes transformations and constraints explicit in a reusable expression. However, it remains experimental in version 2.14.1, and its API is not covered by the ordinary stability expectations of established Pydantic features.

A related experimental facility, `generate_arguments_schema()`, constructs an executable core schema for a callable's arguments without invoking the callable. This differs from `@validate_call`, which validates arguments when the decorated function is executed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Source: [https://pydantic.dev/docs/validation/latest/concepts/experimental/](https://pydantic.dev/docs/validation/latest/concepts/experimental/?utm_source=chatgpt.com)

## 11. Performance characteristics and design tradeoffs

Pydantic's performance model follows from the separation of schema preparation, Rust-native execution, Python callbacks, and Python object construction.

### 11.1 Where performance advantages originate

| Mechanism                | Potential advantage                                                          | Qualification                                             |
| ------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------- |
| Rust-native core schemas | Reduces repeated Python-level parsing and type-checking operations           | Python callbacks still execute in Python                  |
| Reused compiled adapters | Amortizes schema construction costs                                          | Repeated adapter creation can erase the advantage         |
| Direct JSON validation   | Avoids a separate Python JSON object-construction pass                       | Before/wrap validators can alter the relative performance |
| Discriminated unions     | Avoids trial validation of many alternatives                                 | Requires a reliable discriminator                         |
| `TypedDict` schemas      | Validates structured dictionaries without nested model-instance construction | Does not provide model methods or object semantics        |
| Concrete container types | Avoids general abstract-protocol checks and multiple candidate paths         | Less flexible than `Sequence` and `Mapping`               |
| `FailFast`               | Stops at the first invalid item                                              | Reports fewer errors                                      |
| `Any` / `SkipValidation` | Omits unnecessary validation work                                            | Explicitly reduces validation guarantees                  |

The official performance guidance generally favors `model_validate_json()` over `json.loads()` followed by `model_validate()`, but identifies circumstances involving model-level before or wrap validators where the two-step approach can be faster.

It also emphasizes reusing `TypeAdapter` instances. Every newly created adapter constructs validation and serialization machinery; instantiating one within a frequently executed function can turn a reusable setup cost into repeated overhead.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+1



Source: [https://pydantic.dev/docs/validation/latest/concepts/performance/](https://pydantic.dev/docs/validation/latest/concepts/performance/?utm_source=chatgpt.com)

### 11.2 The distinction between model objects and typed data

`BaseModel` provides rich object behavior, model inheritance, configurable state, custom methods, assignment controls, and introspection.

`TypedDict` plus `TypeAdapter` provides structural validation while retaining ordinary dictionaries.

These are different abstraction choices. A validated dictionary does not have to become a custom model instance merely because Pydantic is used.

Conversely, omitting model objects can sacrifice useful object semantics, encapsulation, and method organization.

For large collections of nested records, object allocation and representation choice can be consequential. Pydantic's documentation explicitly identifies `TypedDict` as a performance alternative to nested models, but does not imply it is universally preferable.

### 11.3 Validation frequency and data boundaries

An important architectural inference follows from Pydantic's execution model:

The value of validation depends on where it is performed, not simply how quickly one validation invocation runs.

A system can validate external input once, represent it in a known internal form, and subsequently operate under that contract. Repeatedly revalidating the same trusted data introduces work without necessarily increasing meaningful assurance.

Conversely, data modified outside Pydantic's assignment-validation mechanisms can invalidate assumptions established during initial parsing.

The tradeoff is therefore between:

- Validating at trust boundaries.
- Validating mutable intermediate state.
- Validating only modified fields or changed records.
- Revalidating complete structures at defined checkpoints.

Pydantic supplies useful mechanisms for these choices but does not provide a general incremental validation engine that automatically tracks dependencies and rechecks only affected substructures.

### 11.4 Startup and schema-generation performance

Runtime validation is only one part of total cost. Applications with numerous or complex model definitions can spend significant time generating schemas during import or startup.

`defer_build` can postpone some schema construction, shifting work to the first use rather than eliminating it.

Pydantic 2.14 includes several schema-generation optimizations. The release announcement reports 5–20% reductions in model-build time for individual optimizations in the project's benchmarks. These are upstream schema-building measurements, not general claims about application throughput or end-to-end validation performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

pydantic.dev



Source: [https://pydantic.dev/articles/pydantic-v2-14-release](https://pydantic.dev/articles/pydantic-v2-14-release?utm_source=chatgpt.com)

## 12. Integration ecosystem and capability boundaries

Pydantic's usefulness is amplified by adjacent tools, but the responsibilities of these packages should be distinguished from those of Pydantic itself.

### 12.1 Settings, configuration sources, and CLI integration

`pydantic-settings` is a separate package that uses Pydantic models to define validated application configuration.

Beyond basic environment-variable parsing, it provides:

- Environment prefixes, aliases, nested environment variables, and case-sensitivity policies.
- `.env` files and secrets directories.
- Source precedence and configurable source ordering.
- Custom configuration sources through `settings_customise_sources()`.
- YAML, JSON, TOML, and other file-source options.
- Integrations with AWS Secrets Manager, AWS Systems Manager Parameter Store, Azure Key Vault, and Google Cloud Secret Manager.
- CLI argument parsing, subcommands, help generation, and connections to existing parsers.

The CLI functionality is particularly significant: settings models can describe command-line interfaces as well as consume CLI overrides of configuration.

Custom source implementations can access data collected from earlier sources, enabling configuration composition without a separate application-specific aggregation framework.

The boundary is clear: Pydantic validates the resulting values; `pydantic-settings` obtains and combines configuration values from external sources.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

+3



Sources:

- [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings?utm_source=chatgpt.com)

### 12.2 Web APIs and contract generation

Frameworks such as FastAPI use Pydantic for request validation, response serialization, and schema generation.

Pydantic contributes the typed data-contract machinery. The web framework contributes routing, dependency injection, HTTP status handling, authentication integrations, and application lifecycle management.

The combination can eliminate custom request parsing, response mapping, and portions of API schema maintenance.

However, validating an API request does not itself enforce authorization, transaction integrity, or database state invariants.

Source: [https://fastapi.tiangolo.com/tutorial/body/](https://fastapi.tiangolo.com/tutorial/body/?utm_source=chatgpt.com)

### 12.3 Static typing and developer tooling

Pydantic's annotations participate in Python static analysis, although its runtime capabilities extend beyond what ordinary type checkers can infer.

Important integrations include:

| Tool                        | Relevant capability                                                                                  |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| `mypy` with `pydantic.mypy` | Pydantic-aware constructor signatures, settings, frozen models, and field behavior                   |
| Pyrefly                     | Built-in Pydantic-aware analysis and IDE support, without an additional plugin                       |
| Pyright                     | Type inference for Pydantic APIs through their public type annotations and supported typing features |
| IDE integrations            | Constructor completion, field discovery, navigation, and type-aware diagnostics                      |

Pydantic 2.14 adopts `TypeForm`, enabling improved inference of `TypeAdapter` results for complete type expressions such as unions and `Annotated` types, rather than just simple classes. The release notes identify corresponding minimum type-checker versions for that support.

This narrows the gap between runtime schema expressiveness and static inference, but does not eliminate it. Dynamically generated models, arbitrary Python validators, and context-dependent validation can still express behavior beyond static verification.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

pydantic.dev

+2



Sources:

- [https://pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/](https://pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/?utm_source=chatgpt.com)
- [https://pydantic.dev/docs/validation/latest/integrations/dev-tools/pyrefly/](https://pydantic.dev/docs/validation/latest/integrations/dev-tools/pyrefly/?utm_source=chatgpt.com)

### 12.4 Schema-first and contract-first tooling

`datamodel-code-generator` is a separate library and CLI that can generate Pydantic model definitions from OpenAPI, JSON Schema, JSON/YAML/CSV data, Python dictionaries, and GraphQL schemas.

This complements Pydantic's own JSON Schema generation:

- Pydantic can generate JSON Schema from Python models.
- `datamodel-code-generator` can generate Python model definitions from external schema sources.

The two directions are not guaranteed to form a perfect round trip, especially where schemas contain constructs or semantics that do not map directly to Python validation behavior.

The generator can substantially reduce manually maintained model definitions when an external schema is authoritative.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources:

- [https://pydantic.dev/docs/validation/latest/integrations/dev-tools/datamodel_code_generator/](https://pydantic.dev/docs/validation/latest/integrations/dev-tools/datamodel_code_generator/?utm_source=chatgpt.com)
- [https://github.com/koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator?utm_source=chatgpt.com)

### 12.5 Additional adjacent packages

| Package or technology   | Relationship to Pydantic                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `pydantic-core`         | Rust-backed runtime engine for validation and serialization                                                              |
| `pydantic-extra-types`  | Additional reusable domain types                                                                                         |
| `pydantic-settings`     | Configuration sourcing and validated settings                                                                            |
| Pydantic Logfire        | Validation observability and broader application telemetry                                                               |
| Pydantic AI             | Separate framework for typed AI-agent workflows                                                                          |
| `bump-pydantic`         | Automated assistance with V1-to-V2 code migration                                                                        |
| Hypothesis              | Separate property-based testing framework; its former built-in Pydantic plugin is not included in V2                     |
| ORMs such as SQLAlchemy | Database object mapping and persistence, with Pydantic providing separate data validation or representation capabilities |
| JSON Schema consumers   | External tooling that can consume Pydantic-generated portable schemas                                                    |

A noteworthy limitation is the Hypothesis integration: Pydantic V2 explicitly removed the integrated Hypothesis plugin. Hypothesis can still work with ordinary Python typing constructs and manually defined strategies, but the old built-in Pydantic-specific integration should not be assumed available.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



## 13. Version 2.14.1: relevant changes and compatibility

The latest stable line includes several changes worth recognizing independently of Pydantic's long-established capabilities.

| Change                          | Status in 2.14.1    | Significance                                                    |
| ------------------------------- | ------------------- | --------------------------------------------------------------- |
| `MISSING` sentinel              | Stable since 2.14.0 | First-class absent-value semantics                              |
| Python 3.15 support             | Released            | Compatibility with new Python language capabilities             |
| Python 3.9 support              | Removed             | Minimum supported Python becomes 3.10                           |
| Python 3.15 lazy imports        | Released support    | Enables additional cross-module model-reference patterns        |
| `TypeForm` support              | Released            | Stronger static inference for `TypeAdapter`                     |
| Python 3.15 `frozendict`        | Released support    | Native validation of the new immutable mapping type             |
| More native core schemas        | Released            | Reduces Python-level validation for selected standard types     |
| `create_model(__namespace__)`   | Released            | More general dynamic-model class construction                   |
| Schema-building optimizations   | Released            | Reduced preparation costs under the measured conditions         |
| Experimental partial validation | Experimental        | Useful for incomplete data, with significant acceptance caveats |
| Experimental pipeline API       | Experimental        | Composable validation pipelines without stable-API guarantees   |

Version 2.14.1 additionally addresses specific validation correctness issues, including Decimal digit limits, `timedelta` integer bounds, inherited `TypedDict` field semantics, and named tuples within sequence validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



### 13.1 V1 versus V2

Pydantic V2 is a substantial architectural change rather than a routine major-version API refresh.

Important differences include:

- Replacement of the V1 validation implementation with `pydantic-core`.
- General-purpose validation through `TypeAdapter`.
- New `model_*` method naming conventions.
- `RootModel` replacing V1's `__root__` pattern.
- Expanded serializer support.
- New validator modes and `Annotated`-oriented customization.
- Different union selection, equality, coercion, and subclass serialization behavior.
- Extraction of settings management and selected extra types into separate packages.

Pydantic V2 retains the `pydantic.v1` compatibility namespace for staged migration. That does not make V1 and V2 models interchangeable, nor does it eliminate semantic differences between their validation systems.

The migration guide identifies `bump-pydantic` as a beta migration utility.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/get-started/migration/](https://pydantic.dev/docs/validation/latest/get-started/migration/?utm_source=chatgpt.com)

### 13.2 Compatibility policy

Pydantic's V2 version policy states that intentional breaking changes should not occur in minor releases and that deprecated functionality is retained until V3.

However, the policy explicitly permits changes to certain observable details, including:

- JSON Schema reference formatting.
- Some fields of structured validation errors.
- Internal core schema representations.
- Repr output.
- Corrections to previously undocumented behavior.

For machine-readable error handling, the documentation recommends relying on the stable error `type` rather than formatted messages.

The policy also identifies the potential incorporation of standalone `pydantic-core` into Pydantic itself as an expected future V3 change. That is a stated future direction, not a feature of version 2.14.1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/get-started/version-policy/](https://pydantic.dev/docs/validation/latest/get-started/version-policy/?utm_source=chatgpt.com)

## 14. Architectural implications and important limits

The most consequential feature of Pydantic is not any individual validator or model API. It is the ability to define a structured contract once and reuse its semantics across parsing, object construction, serialization, error reporting, and schema generation.

Several combinations are especially significant.

| Combination                                              | What it can make possible                                                     | Principal limitation                                                           |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `Annotated` + `TypeAdapter`                              | Reusable typed contracts without custom model classes                         | Static typing and runtime metadata may not express identical semantics         |
| `TypedDict` + `TypeAdapter`                              | Validated relational or dictionary-oriented records without object conversion | No automatic database or columnar execution model                              |
| Discriminated unions + generics                          | Reusable structured variants and polymorphic data contracts                   | Ambiguous or unstable discriminators complicate compatibility                  |
| `MISSING` + field-set tracking + selective serialization | Accurate partial-update and patch semantics                                   | The receiving system must preserve the distinction between absent and null     |
| Custom core schemas + JSON Schema hooks                  | First-class integration of third-party domain types                           | Portable JSON Schema may not capture arbitrary Python behavior                 |
| Separate validation/serialization aliases + serializers  | Distinct inbound, canonical, and outbound representations                     | Complex transformation semantics are not inherently reversible                 |
| Dynamic models + JSON Schema generation                  | Runtime-generated data contracts and metadata-driven interfaces               | Schema preparation, caching, typing, and compatibility become more complicated |
| Native schema execution + reused adapters                | Efficient repeated validation of supported structures                         | Python callbacks and allocation costs remain                                   |
| Pydantic validation + `pydantic-settings`                | A common typed configuration model across multiple input sources              | Source ordering, external access, and lifecycle belong to the settings layer   |
| Plugin interception + structured errors                  | Centralized validation diagnostics and observability                          | Instrumentation introduces overhead and data-governance obligations            |

### Limits that should remain explicit

Pydantic is not a static proof system. Runtime validation establishes that a value satisfied the configured schema at a particular moment, under particular inputs and context. Mutable state, arbitrary Python callbacks, and subsequent operations can invalidate those assumptions.

Pydantic is not a relational constraint engine. It can validate rows, mappings, and collections, but native database uniqueness constraints, foreign keys, transactional consistency, and query execution remain the responsibilities of database or relational engines.

Pydantic is not a zero-copy Arrow or NumPy validation engine. The Rust implementation can make individual parsing and validation operations efficient, but that does not establish native vectorized evaluation over columnar arrays or zero-copy conversion between arbitrary Python objects and external memory formats.

Pydantic is not a complete schema-interchange standard. Its executable Python validation semantics can exceed what JSON Schema expresses. Portable schema consumers must be understood as operating on a generated representation of the contract, not necessarily its complete runtime behavior.

Pydantic is not intrinsically immutable. Frozen models, assignment validation, and instance revalidation are useful controls, but their actual guarantees depend on nested values, mutation paths, and validation settings.

Pydantic is not automatically the cheapest representation for every internal value. Repeated validation, model-object allocation, schema construction, or Python callback execution can be substantial compared with working directly on trusted native or columnar data.

These are architectural boundaries, not deficiencies relative to Pydantic's stated purpose. They distinguish where native Pydantic machinery can replace custom code from where a different computational engine or persistence system is responsible.

## 15. Primary source map

The following sources collectively provide the most useful entry points for deeper, version-conscious investigation. URLs are included in full for independent reuse.

| Topic                                        | Primary reference                                                                                                                                                                                 |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Release/version confirmation                 | [https://pypi.org/project/pydantic/2.14.1/](https://pypi.org/project/pydantic/2.14.1/?utm_source=chatgpt.com)                                                                                     |
| Version 2.14 enhancements                    | [https://pydantic.dev/articles/pydantic-v2-14-release](https://pydantic.dev/articles/pydantic-v2-14-release?utm_source=chatgpt.com)                                                               |
| Complete Pydantic documentation              | [https://pydantic.dev/docs/validation/latest/](https://pydantic.dev/docs/validation/latest/?utm_source=chatgpt.com)                                                                               |
| Internal architecture and schema compilation | [https://pydantic.dev/docs/validation/latest/internals/architecture/](https://pydantic.dev/docs/validation/latest/internals/architecture/?utm_source=chatgpt.com)                                 |
| BaseModel, generics, dynamic models          | [https://pydantic.dev/docs/validation/latest/concepts/models/](https://pydantic.dev/docs/validation/latest/concepts/models/?utm_source=chatgpt.com)                                               |
| Fields, Annotated, constraints               | [https://pydantic.dev/docs/validation/latest/concepts/fields/](https://pydantic.dev/docs/validation/latest/concepts/fields/?utm_source=chatgpt.com)                                               |
| Custom types and named aliases               | [https://pydantic.dev/docs/validation/latest/concepts/types/](https://pydantic.dev/docs/validation/latest/concepts/types/?utm_source=chatgpt.com)                                                 |
| General-purpose TypeAdapter                  | [https://pydantic.dev/docs/validation/latest/concepts/type_adapter/](https://pydantic.dev/docs/validation/latest/concepts/type_adapter/?utm_source=chatgpt.com)                                   |
| Validators and execution order               | [https://pydantic.dev/docs/validation/latest/concepts/validators/](https://pydantic.dev/docs/validation/latest/concepts/validators/?utm_source=chatgpt.com)                                       |
| Serialization and subclass semantics         | [https://pydantic.dev/docs/validation/latest/concepts/serialization/](https://pydantic.dev/docs/validation/latest/concepts/serialization/?utm_source=chatgpt.com)                                 |
| JSON Schema generation and customization     | [https://pydantic.dev/docs/validation/latest/concepts/json_schema/](https://pydantic.dev/docs/validation/latest/concepts/json_schema/?utm_source=chatgpt.com)                                     |
| Model configuration and propagation          | [https://pydantic.dev/docs/validation/latest/concepts/config/](https://pydantic.dev/docs/validation/latest/concepts/config/?utm_source=chatgpt.com)                                               |
| Alias systems                                | [https://pydantic.dev/docs/validation/latest/concepts/alias/](https://pydantic.dev/docs/validation/latest/concepts/alias/?utm_source=chatgpt.com)                                                 |
| Unions and discriminators                    | [https://pydantic.dev/docs/validation/latest/concepts/unions/](https://pydantic.dev/docs/validation/latest/concepts/unions/?utm_source=chatgpt.com)                                               |
| Strictness and conversion                    | [https://pydantic.dev/docs/validation/latest/concepts/strict_mode/](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/?utm_source=chatgpt.com)                                     |
| Input conversion table                       | [https://pydantic.dev/docs/validation/latest/concepts/conversion_table/](https://pydantic.dev/docs/validation/latest/concepts/conversion_table/?utm_source=chatgpt.com)                           |
| JSON parsing and partial parsing             | [https://pydantic.dev/docs/validation/latest/concepts/json/](https://pydantic.dev/docs/validation/latest/concepts/json/?utm_source=chatgpt.com)                                                   |
| Experimental capabilities                    | [https://pydantic.dev/docs/validation/latest/concepts/experimental/](https://pydantic.dev/docs/validation/latest/concepts/experimental/?utm_source=chatgpt.com)                                   |
| Core schema API                              | [https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core_schema/](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core_schema/?utm_source=chatgpt.com) |
| Performance guidance                         | [https://pydantic.dev/docs/validation/latest/concepts/performance/](https://pydantic.dev/docs/validation/latest/concepts/performance/?utm_source=chatgpt.com)                                     |
| Settings source machinery                    | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com)                         |
| Structured errors                            | [https://pydantic.dev/docs/validation/latest/errors/errors/](https://pydantic.dev/docs/validation/latest/errors/errors/?utm_source=chatgpt.com)                                                   |
| Version policy                               | [https://pydantic.dev/docs/validation/latest/get-started/version-policy/](https://pydantic.dev/docs/validation/latest/get-started/version-policy/?utm_source=chatgpt.com)                         |
| V1-to-V2 migration                           | [https://pydantic.dev/docs/validation/latest/get-started/migration/](https://pydantic.dev/docs/validation/latest/get-started/migration/?utm_source=chatgpt.com)                                   |
| Upstream source and tagged releases          | [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic?utm_source=chatgpt.com)                                                                                               |
| Extra domain types                           | [https://github.com/pydantic/pydantic-extra-types](https://github.com/pydantic/pydantic-extra-types?utm_source=chatgpt.com)                                                                       |
| Settings companion package                   | [https://github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings?utm_source=chatgpt.com)                                                                             |
| External schema-to-model generation          | [https://github.com/koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator?utm_source=chatgpt.com)                                                               |
| Static analysis integration                  | [https://pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/](https://pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/?utm_source=chatgpt.com)                       |

The central architectural insight is that Pydantic's most valuable reusable unit is the executable type contract, not necessarily the model object. `BaseModel`, `TypeAdapter`, `Annotated`, custom core schemas, serializers, and JSON Schema generation are different interfaces onto that contract. Understanding their composition—and where execution semantics cease to be portable—is what unlocks the library's broader capabilities while avoiding unnecessary validation, conversion, and bespoke mapping machinery.

# Pydantic — Advanced Capabilities Addendum

Companion to: Pydantic — Comprehensive Python Library Capability Reference\
Target version: Pydantic 2.14.2\
Research date: November 1, 2026\
Scope: Additional capabilities, advanced semantics, configuration mechanisms, and version-sensitive distinctions not fully developed in the original reference.

Official documentation: [https://pydantic.dev/docs/validation/latest/](https://pydantic.dev/docs/validation/latest/?utm_source=chatgpt.com)\
Source repository: [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic?utm_source=chatgpt.com)

## 1. Orientation and version update

This addendum extends the original Pydantic reference without restating its foundational treatment of `BaseModel`, `TypeAdapter`, `Annotated`, validators, serializers, core schemas, or JSON Schema generation.

The additional capabilities fall into several related areas:

| Capability family            | Additional functionality                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| Structural data contracts    | PEP 728 `TypedDict` semantics, runtime extra-field policies, lazy iterable validation       |
| Polymorphic representations  | Native subclass-aware serialization, distinctions from `SerializeAsAny`                     |
| Serialization fidelity       | Round-trip representations, computed-field exclusions, fallback handlers, error policies    |
| Schema interoperability      | Required-field semantics, mode overrides, schema omission, union representation             |
| Semantic type adapters       | Encoded values, generic secrets, imported objects, byte sizes, temporal and URL constraints |
| Validation policy            | Regex engines, alias acceptance, binary and temporal formats, diagnostic controls           |
| Model and callable lifecycle | Private factories, equality semantics, callable validation, dataclass schema rebuilding     |
| Low-level extension surfaces | Additional `SchemaValidator`, `SchemaSerializer`, and `pydantic-core` operations            |

### 1.1 Current stable release: 2.14.2

Pydantic 2.14.2 was released on October 29, 2026, superseding the original document's target version, 2.14.1. It retains Python 3.10–3.15 compatibility and introduces correctness, security, packaging, and performance improvements rather than a new major API family.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Two security fixes are especially relevant to the contract-enforcement semantics discussed throughout this addendum.

GHSA-qpmf-fgh3-ff25 — JSON validation of additional properties. In affected releases (2.13.0 through 2.14.1), the JSON validation path could bypass validation of extra-property keys against the key type declared on `__pydantic_extra__`. Python-mode validation did not share this particular defect. Version 2.14.2 restores the intended behavior. The related JSON field-lookup changes also ensure that unused field names or aliases are treated as extra input rather than silently discarded.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



GHSA-3r8g-cqwr-jr29 — Aliased fields and extra properties in structural types. In affected V2 releases before 2.14.2, `TypedDict` and Pydantic dataclasses configured to allow extra properties could accept both a field's alias and its Python name, with an unvalidated value overwriting the validated field value. `BaseModel` was not affected by this specific overwrite mechanism because it stores extra fields separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



These fixes illustrate an important boundary: Pydantic's declarative validation rules are enforced through specific execution paths. Differences between JSON and Python input, alias resolution, and extra-field storage can matter to the resulting contract.

Primary sources:

- [https://github.com/pydantic/pydantic/releases/tag/v2.14.2](https://github.com/pydantic/pydantic/releases/tag/v2.14.2?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic/security/advisories/GHSA-qpmf-fgh3-ff25](https://github.com/pydantic/pydantic/security/advisories/GHSA-qpmf-fgh3-ff25?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic/security/advisories/GHSA-3r8g-cqwr-jr29](https://github.com/pydantic/pydantic/security/advisories/GHSA-3r8g-cqwr-jr29?utm_source=chatgpt.com)

## 2. Structural contracts and validation boundaries

### 2.1 PEP 728: closed `TypedDict` types and typed extra items

Pydantic has supported PEP 728's `TypedDict` extensions since version 2.12. The extensions introduce two type-level declarations that materially expand what structural dictionaries can represent:

- `closed=True` prohibits undeclared keys.
- `extra_items=T` permits undeclared keys but requires their values to conform to `T`.

This provides three distinct structural contract shapes: conventional open dictionaries, fully closed dictionaries, and dictionaries with named fields plus a validated extensible region.

```
from typing_extensions import TypedDictfrom pydantic import TypeAdapterclass ClosedRecord(TypedDict, closed=True):    identifier: str    revision: intclass ExtensibleRecord(TypedDict, extra_items=float):    identifier: strclosed_adapter = TypeAdapter(ClosedRecord)extensible_adapter = TypeAdapter(ExtensibleRecord)record = extensible_adapter.validate_python({    "identifier": "sample",    "confidence": 0.95,    "weight": 12.5,})
```

The `ClosedRecord` adapter rejects unknown keys, whereas `ExtensibleRecord` validates additional values as floats. The latter need not define an individual field for each possible metric.

Unlike untyped `extra='allow'` behavior, the extensible region is part of the static type definition.

Pydantic translates these semantics into JSON Schema's `additionalProperties`:

| Declaration       | JSON Schema behavior                                                        |
| ----------------- | --------------------------------------------------------------------------- |
| `closed=True`     | `additionalProperties: false`                                               |
| `extra_items=int` | `additionalProperties` contains an integer schema                           |
| `extra_items=Any` | Additional properties are permitted without further value-type restrictions |

The Python 3.15 typing features can be accessed through `typing_extensions` on earlier supported Python versions. Pydantic 2.14.1 additionally fixed inheritance handling for `closed` and `extra_items` declarations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

pydantic.dev+1



Architectural significance. Typed additional properties allow a single mapping type to represent both a known structural core and an open-ended collection of consistently typed attributes. This can replace custom dictionary preprocessing, dynamic model generation, or runtime field enumeration when the unknown keys share a common value contract.

There remain important limits. `extra_items=T` constrains the values of additional keys; it is not a general dictionary-key validation language. Constraints on dynamically named keys, relationships between keys, and policies depending on other fields may require additional validation. The ability to retain extra data also makes careful alias handling consequential, as demonstrated by the 2.14.2 security fixes.

Source: [https://pydantic.dev/articles/pydantic-v2-12-release](https://pydantic.dev/articles/pydantic-v2-12-release?utm_source=chatgpt.com)

### 2.2 Per-invocation extra-field policies

Beginning in Pydantic 2.12, validation interfaces gained an `extra` argument that overrides the corresponding model-level configuration for an individual validation operation.

This is available through `BaseModel.model_validate()`, `model_validate_json()`, `model_validate_strings()`, and the equivalent `TypeAdapter` validation methods.

```
from pydantic import BaseModel, ConfigDict, ValidationErrorclass Record(BaseModel):    model_config = ConfigDict(extra="allow")    identifier: str    revision: intinput_data = {    "identifier": "sample",    "revision": 2,    "unexpected": "value",}permissive = Record.model_validate(input_data)try:    strict = Record.model_validate(        input_data,        extra="forbid",    )except ValidationError as exc:    print(exc.errors()[0]["type"])    # extra_forbidden
```

A model may therefore have a default interpretation while a caller imposes a different unknown-field policy at the input boundary.

This capability works alongside other runtime validation controls: `strict`, `context`, `by_alias`, `by_name`, and, for appropriate Python inputs, `from_attributes`.

The distinctions are useful:

| Control           | Governs                                                              |
| ----------------- | -------------------------------------------------------------------- |
| `extra`           | Whether unexpected properties are rejected, discarded, or retained   |
| `strict`          | Whether specified input-type conversions are permitted               |
| `by_alias`        | Whether field aliases are recognized during field lookup             |
| `by_name`         | Whether Python field names are recognized during field lookup        |
| `context`         | External information available to custom validators                  |
| `from_attributes` | Whether supported structures can be populated from object attributes |

Together, these controls separate the declared data shape from the policy under which a particular input is interpreted.

Architectural significance. The same reusable type can serve multiple validation boundaries without requiring duplicate model hierarchies merely to vary unknown-field handling or strictness. For example, an external ingestion boundary may forbid unrecognized properties while an intermediate compatibility boundary may deliberately retain them.

This does not imply that all policy differences can be represented through runtime arguments. Distinct field requirements, schema versions, semantic invariants, and irreversible transformations may still warrant separate types or adapters.

Sources:

[https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/](https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/validation/latest/api/pydantic/type_adapter/](https://pydantic.dev/docs/validation/latest/api/pydantic/type_adapter/?utm_source=chatgpt.com)

### 2.3 Lazy validation of `Iterable[T]`

Most concrete collection annotations eagerly validate their elements. An annotation of `collections.abc.Iterable[T]` instead enables a different execution model.

Pydantic checks that the supplied value is iterable and returns an internal validating iterator. Individual elements are subsequently validated as they are consumed.

```
from collections.abc import Iterablefrom pydantic import BaseModel, ValidationErrorclass StreamRecord(BaseModel):    values: Iterable[int]record = StreamRecord(values=[1, 2, "invalid"])iterator = iter(record.values)assert next(iterator) == 1assert next(iterator) == 2try:    next(iterator)except ValidationError as exc:    print(exc.errors())
```

Crucially, construction of `StreamRecord` succeeds even though a later element is invalid. This is not equivalent to `list[int]`, whose elements are ordinarily validated before the model is returned.

The capability introduces several consequences:

Validation completeness is consumption-dependent. Successful model creation establishes that a valid iterator was obtained, not that every future value is valid. Unconsumed elements have not been validated.

Errors can occur long after construction. An invalid element may raise an exception during downstream processing rather than at the original input boundary.

Iteration has state. The resulting validating iterator is not necessarily a reusable collection. Consumption, exhaustion, and underlying generator side effects must be accounted for.

Memory and termination behavior can differ. An unbounded or infinite iterator cannot be eagerly materialized safely. Lazy validation makes such inputs representable without validating or allocating an entire collection upfront.

The official documentation recommends concrete collection types unless the lazy semantics are genuinely needed, particularly for infinite iterators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Architectural significance. This is Pydantic's native mechanism for attaching a typed validation contract to an iterable while retaining deferred consumption. It is not a general streaming orchestration framework or an asynchronous incremental parser, but it can eliminate bespoke element-by-element validation wrappers.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/standard_library_types/#iterables](https://pydantic.dev/docs/validation/latest/api/pydantic/standard_library_types/?utm_source=chatgpt.com#iterables)

### 2.4 Selective validation failure and information retention

The original reference identifies `OnErrorOmit` and `FailFast`, but a fuller distinction between their effects is useful.

`OnErrorOmit[T]` supports a retain-valid-elements policy for specific collection positions:

```
from pydantic import OnErrorOmit, TypeAdapteradapter = TypeAdapter(list[OnErrorOmit[int]])result = adapter.validate_python([1, "bad", 2, 3])assert result == [1, 2, 3]
```

It can be used for the element type of lists and tuples, mapping keys or values, and non-required `TypedDict` fields. An invalid mapping key or value causes the entire mapping entry to be omitted. It cannot be used to silently remove a required `TypedDict` field or as a general top-level invalid-value suppression mechanism.

A significant limitation is that omitted values are discarded without reporting which items failed. Pydantic's documentation recommends a wrap validator when failure provenance must be retained.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



The three mechanisms therefore offer different guarantees:

| Mechanism                      | Result on an invalid element                    | Information consequence                                          |
| ------------------------------ | ----------------------------------------------- | ---------------------------------------------------------------- |
| Ordinary collection validation | Raise a validation error                        | Failure is explicit; no accepted result for the collection       |
| `FailFast`                     | Stop checking further elements after failure    | Retains explicit failure, but not all possible errors            |
| `OnErrorOmit`                  | Drop invalid elements and retain valid elements | Produces a potentially incomplete result without an error ledger |
| Lazy `Iterable[T]`             | Raise when the invalid element is consumed      | Acceptance of the enclosing model precedes complete validation   |

The important architectural distinction is that tolerant parsing, early rejection, lazy validation, and complete validation are different policies. A usable partial result does not prove that the original collection was valid or complete.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/types/#onerroromit](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#onerroromit)

## 3. Native polymorphic serialization

### 3.1 Polymorphic serialization versus serialize-as-any

Pydantic 2.13 introduced `polymorphic_serialization` to support subclass-aware serialization without adopting the broader runtime-type behavior of `SerializeAsAny`.

In ordinary V2 serialization, a field annotated with a model type is serialized according to that declared type's schema. Subclass-only fields are therefore omitted.

Polymorphic serialization changes the selection rule for Pydantic models and Pydantic dataclasses: the concrete instance's serialization schema is used instead.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



```
from pydantic import BaseModel, ConfigDictclass Event(BaseModel):    event_id: strclass DetailedEvent(Event):    source: str    confidence: floatclass Envelope(BaseModel):    event: Eventenvelope = Envelope(    event=DetailedEvent(        event_id="E-1",        source="sensor",        confidence=0.98,    ))assert envelope.model_dump() == {    "event": {"event_id": "E-1"}}assert envelope.model_dump(    polymorphic_serialization=True) == {    "event": {        "event_id": "E-1",        "source": "sensor",        "confidence": 0.98,    }
```

Pydantic offers two activation scopes.

Type-level configuration. `ConfigDict(polymorphic_serialization=True)` is declared on the type that should behave polymorphically. In the example, that would be `Event`, not `Envelope`. This makes subclass-aware serialization part of the base type's behavior when encountered as a nested field.

Runtime configuration. Passing `polymorphic_serialization=True` to `model_dump()`, `model_dump_json()`, or the corresponding adapter serialization methods enables it for the relevant nested values in that operation. Passing `False` overrides type-level configuration for that call.

The differences among serialization mechanisms are substantial:

| Mechanism                          | Schema used                                       | Scope                                                         |
| ---------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| Default schema-based serialization | Declared field type                               | Predictable output restricted to the annotated model contract |
| `polymorphic_serialization=True`   | Concrete Pydantic model/dataclass subclass schema | Subclass-aware structured serialization                       |
| `SerializeAsAny[T]`                | Runtime-value-oriented serialization              | Specific annotated field and its supported nested behavior    |
| `serialize_as_any=True`            | Runtime-value-oriented serialization              | Broadly applied during that serialization operation           |

The last two mechanisms apply more broadly than Pydantic model subclasses. In serialize-as-any mode, Pydantic can serialize many standard-library values, objects with Pydantic serializer machinery, and values handled by an explicit fallback function.

### 3.2 Architectural possibilities and boundaries

Polymorphic serialization allows a hierarchy of related models to retain a common declared interface without discarding subtype-specific state when exported.

This can be useful when a base contract is intentionally extensible and its concrete implementations carry additional machine-readable properties.

It can also reduce custom branching serializers that would otherwise inspect every runtime subtype and manually construct its output representation.

However, enabling polymorphic serialization alters the outbound data contract, not the validation rules for accepting the corresponding input. A field typed as a base class does not automatically become a tagged union capable of reconstructing every subclass from serialized data.

There are also important limitations:

- Sensitive fields: Subclass-only fields may be emitted even when they were absent from the declared base contract. Polymorphic serialization is not an information-flow security mechanism.
- Standard-library dataclasses: Native polymorphic serialization supports Pydantic models and Pydantic dataclasses, but not ordinary standard-library dataclasses. This remains a documented limitation in 2.14.2.
- Schema interoperability: A JSON Schema generated for a field annotated as a base type should not be presumed to enumerate every possible runtime subclass shape. The runtime output may be broader than the declared schema.
- Version evolution: Adding fields to a subclass can change polymorphic output without changing the field annotation in a containing model.

For fixed external variant contracts, explicit discriminated unions remain more suitable when both input reconstruction and JSON Schema must describe the possible alternatives.

Source: [https://pydantic.dev/docs/validation/latest/concepts/serialization/#polymorphic-serialization](https://pydantic.dev/docs/validation/latest/concepts/serialization/?utm_source=chatgpt.com#polymorphic-serialization)

## 4. Serialization fidelity, recovery, and conditional output

### 4.1 `Json[T]`, `JsonValue`, and round-trip serialization

Pydantic distinguishes between a field whose input is JSON-encoded text and a field whose value is a JSON-compatible structure.

`Json[T]` expects an encoded JSON string, bytes, or bytearray. It first decodes that representation and then validates the decoded result as `T`.

`JsonValue` instead expresses a recursively JSON-compatible value: null, Boolean, number, string, list, or dictionary with string keys containing other JSON-compatible values.

```
from pydantic import BaseModel, Json, JsonValueclass Payload(BaseModel):    encoded: Json[list[int]]    metadata: JsonValuepayload = Payload(    encoded="[1, 2, 3]",    metadata={"source": "example", "valid": True},)assert payload.encoded == [1, 2, 3]
```

Ordinary serialization emits the decoded representation of `Json[T]`. This is often desirable but is not necessarily valid input for the same field, because the original field expects encoded JSON rather than an already-decoded list.

The `round_trip=True` option changes this:

```
normal = payload.model_dump()round_trip = payload.model_dump(round_trip=True)assert normal["encoded"] == [1, 2, 3]assert round_trip["encoded"] == "[1,2,3]"
```

Pydantic's round-trip mode is intended to produce representations that can be used again as input for non-idempotent types such as `Json[T]`. It does not guarantee preservation of the original bytes, whitespace, key ordering, or textual formatting of the source.

The distinction is between semantic revalidation compatibility and byte-for-byte reversibility.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



This capability is useful when a contract contains embedded structured payloads that must remain encoded within a larger object, or when values pass repeatedly through validation and serialization boundaries.

Sources:

[https://pydantic.dev/docs/validation/latest/api/pydantic/types/#json](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#json)

[https://pydantic.dev/docs/validation/latest/api/pydantic/types/#jsonvalue](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#jsonvalue)

### 4.2 Serialization failure policy and fallback handlers

Pydantic serialization methods provide explicit controls for values that cannot be serialized according to the available machinery.

The relevant arguments are `warnings` and `fallback`, available on model and adapter serialization interfaces.

| Setting             | Behavior                                                                 |
| ------------------- | ------------------------------------------------------------------------ |
| `warnings='none'`   | Suppresses serialization warnings                                        |
| `warnings='warn'`   | Reports serialization warnings without turning them into errors          |
| `warnings='error'`  | Raises `PydanticSerializationError` for supported serialization failures |
| `fallback=callable` | Invokes the supplied function for otherwise unsupported values           |

The Boolean forms `False` and `True` correspond to suppressing and reporting warnings.

```
from typing import Anyfrom pydantic import BaseModelclass Envelope(BaseModel):    payload: Anyvalue = Envelope(payload=object())serialized = value.model_dump(    mode="json",    fallback=lambda obj: {        "unsupported_type": type(obj).__name__    },)
```

Here, the fallback provides a deliberate representation for an otherwise unsupported Python object.

This is more explicit than allowing arbitrary objects to fail unpredictably during JSON encoding. It can also avoid duplicating unsupported-type handling across numerous serializers.

However, a fallback is not necessarily an inverse transformation. Returning a string, marker, or dictionary for an unsupported object does not make the result sufficient to reconstruct that object.

A significant distinction is that `warnings` is an error-reporting policy, while `fallback` is a recovery mechanism. Suppressing a warning does not provide a meaningful representation of an otherwise unencodable value.

Architectural significance. Pydantic allows output boundaries to declare how serialization defects should be handled: fail explicitly, report nonfatal problems, or apply a defined fallback. This can replace separate exception-handling layers around ordinary JSON encoding, provided the fallback's information-loss semantics are acceptable.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/#model_dump](https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/?utm_source=chatgpt.com#model_dump)

### 4.3 Computed-field exclusions and round-trip behavior

Pydantic provides `exclude_computed_fields=True` to omit computed properties during serialization.

This is distinct from `exclude_unset`, `exclude_defaults`, and `exclude_none`, because computed fields are not ordinary input fields whose presence is determined by construction.

```
from pydantic import BaseModel, computed_fieldclass Measurement(BaseModel):    length: float    width: float    @computed_field    @property    def area(self) -> float:        return self.length * self.widthm = Measurement(length=2.0, width=3.0)assert m.model_dump() == {    "length": 2.0,    "width": 3.0,    "area": 6.0,}assert m.model_dump(    exclude_computed_fields=True) == {    "length": 2.0,    "width": 3.0,}
```

This matters when generated output is used as input for another validation pass. A computed field included in the exported dictionary may be treated as an unexpected input field by a model expecting only its declared inputs.

Pydantic's API documentation recommends the broader `round_trip=True` option when the objective is revalidation compatibility, rather than relying exclusively on computed-field exclusion.

Starting in 2.13, `@computed_field` also supports `exclude_if`, allowing exclusion to depend on the computed value:

```
from pydantic import BaseModel, computed_fieldclass Totals(BaseModel):    a: int    b: int    @computed_field(        exclude_if=lambda value: value == 0    )    @property    def total(self) -> int:        return self.a + self.b
```

The computed property remains accessible in Python, but is omitted from serialized output when the predicate evaluates to true.

This enables optional derived output without changing the underlying model's validated state. It does not turn computed properties into validated, persisted, or automatically invalidated fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

pydantic.dev+1



Sources:

[https://pydantic.dev/articles/pydantic-v2-13-release](https://pydantic.dev/articles/pydantic-v2-13-release?utm_source=chatgpt.com)

[https://pydantic.dev/docs/validation/latest/concepts/serialization/](https://pydantic.dev/docs/validation/latest/concepts/serialization/?utm_source=chatgpt.com)

### 4.4 JSON encoding details and `ensure_ascii`

`model_dump_json()` and `TypeAdapter.dump_json()` expose `ensure_ascii`.

With the default `False`, non-ASCII characters can be emitted directly. With `True`, they are escaped into ASCII-compatible JSON character sequences.

This governs textual encoding representation, not the semantic type of the value. It can matter for interfaces requiring ASCII-only JSON text or consistent escaping conventions.

It is separate from the `ascii_only` validation constraint discussed later: `ensure_ascii=True` does not reject non-ASCII input strings.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/type_adapter/#dump_json](https://pydantic.dev/docs/validation/latest/api/pydantic/type_adapter/?utm_source=chatgpt.com#dump_json)

## 5. Specialized semantic types and representation adapters

Pydantic's less prominent built-in types are important because they combine validation and representation behavior in reusable annotations. Several address recurring data-contract needs that would otherwise require custom parsing functions.

### 5.1 Pluggable encoding through `EncodedBytes`, `EncodedStr`, and `EncoderProtocol`

`EncodedBytes` and `EncodedStr` associate a Python bytes or string field with a specified encoding protocol.

An `EncoderProtocol` implementation supplies `decode()`, `encode()`, and `get_json_format()` methods.

```
from typing import Annotatedfrom pydantic import BaseModel, EncodedBytes, EncoderProtocolclass PrefixEncoder(EncoderProtocol):    @classmethod    def decode(cls, data: bytes) -> bytes:        prefix = b"encoded:"        if not data.startswith(prefix):            raise ValueError("Missing encoding prefix")        return data[len(prefix):]    @classmethod    def encode(cls, value: bytes) -> bytes:        return b"encoded:" + value    @classmethod    def get_json_format(cls) -> str:        return "prefixed-bytes"EncodedPayload = Annotated[    bytes,    EncodedBytes(encoder=PrefixEncoder),]class Message(BaseModel):    data: EncodedPayload
```

The annotation describes a relationship between the external encoded representation and the internal decoded value. The custom protocol controls both conversion directions.

This goes beyond ordinary value validation. It allows an encoding convention to travel with the type into nested models, collections, and reusable adapters.

Built-in Base64 types are specializations of this machinery, including URL-safe Base64 variants. Standard and URL-safe Base64 representations are not interchangeable in every circumstance, so the specific encoder matters.

Architectural significance. An encoding protocol can be defined once instead of repeating pre-validation decoding and post-validation encoding across numerous models. It is particularly useful when a field's representation format is intrinsic to its data contract.

The encoder must still define a coherent, appropriately reversible transformation. Pydantic does not independently guarantee that `decode(encode(value))` preserves every possible value or that the encoding is secure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/types/#encodedbytes](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#encodedbytes)

### 5.2 Generic secrets with `Secret[T]`

In addition to `SecretStr` and `SecretBytes`, Pydantic provides the generic `Secret[T]` type.

This makes it possible to associate secret-handling behavior with arbitrary supported underlying types while retaining their validation constraints.

```
from typing import Annotatedfrom pydantic import BaseModel, Field, SecretPositiveSecret = Secret[    Annotated[int, Field(gt=0, strict=True)]]class Credentials(BaseModel):    access_code: PositiveSecretcredentials = Credentials(access_code=42)assert credentials.access_code.get_secret_value() == 42
```

The secret wrapper masks ordinary display and default JSON serialization. The underlying value remains accessible through `get_secret_value()`.

The type can also be subclassed to customize its display representation through `_display()`.

An important security distinction concerns equality: `SecretStr` and `SecretBytes` implement constant-time equality comparison using `secrets.compare_digest()`. Arbitrary `Secret[T]` specializations do not automatically inherit an equivalent constant-time guarantee for arbitrary underlying types. A custom subclass can provide its own equality behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



These wrappers help prevent inadvertent disclosure through ordinary representation and serialization paths, but they do not provide encryption at rest, secure memory handling, access control, or comprehensive secret redaction across custom validators and logging code.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/types/#secret](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#secret)

### 5.3 Importable Python objects with `ImportString`

`ImportString` validates references to importable Python objects.

It can accept a Python object directly or resolve a string such as `"math.cos"` or `"math:cos"` into the referenced callable.

```
from pydantic import BaseModel, ImportStringclass PluginReference(BaseModel):    implementation: ImportStringreference = PluginReference(    implementation="math.cos")assert reference.implementation(0) == 1.0
```

JSON serialization can emit a corresponding import path.

The important distinction from ordinary strings is that validation performs Python import resolution. The result is an executable Python object, not a normalized textual identifier.

This can avoid custom import-path parsing and resolution logic for declarative references to installed Python functions and classes.

However, imports can execute module-level code. `ImportString` is therefore not a safe sandbox for arbitrary user-supplied plugin paths.

Another subtle behavior concerns defaults. Because Pydantic does not validate defaults by default, declaring an `ImportString` field whose default is a string does not necessarily perform import resolution. `validate_default=True` can be necessary to obtain the resolved object.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/types/#importstring](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com#importstring)

### 5.4 Additional domain-oriented semantic types

Several built-in types deserve explicit recognition because they enforce semantics more specific than their primitive Python representations.

| Type or family                                             | Native functionality                                                                        | Important distinction                                                  |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `ByteSize`                                                 | Parses size strings with units and exposes `human_readable()` and `to()` conversion helpers | Decimal `KB` and binary `KiB` have different multipliers               |
| `AwareDatetime` / `NaiveDatetime`                          | Enforces timezone-awareness requirements                                                    | Timezone-aware and naive values represent different temporal contracts |
| `PastDate`, `FutureDate`, `PastDatetime`, `FutureDatetime` | Constrains temporal values relative to the validation time                                  | A valid result can become temporally outdated without mutation         |
| `FilePath`, `DirectoryPath`                                | Checks that a path currently refers to a file or directory                                  | Validation depends on external filesystem state                        |
| `NewPath`                                                  | Checks that a path does not already exist and that its parent directory exists              | Validation does not reserve the path or prevent later races            |
| `SocketPath`                                               | Checks for an existing socket path                                                          | Does not establish connectivity or operating-system permissions        |
| `UuidVersion`                                              | Applies UUID-version constraints through `Annotated` metadata                               | More specific than validating only that a value is some UUID           |
| `UrlConstraints`                                           | Constrains schemes, hosts, length, defaults, and path normalization                         | URL parsing and normalization do not establish network reachability    |

`ByteSize`, for example, interprets `1KB` as 1,000 bytes and `1KiB` as 1,024 bytes. It retains an integer-like representation while enabling human-readable or explicit-unit conversion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



The filesystem-related types introduce an especially consequential distinction: validation can consult external state. Their successful validation means that the condition was satisfied when checked, not that it will remain true. They do not replace file-descriptor-based operations, locking, or race-safe resource acquisition.

Similarly, the temporal constraint types encode conditions whose truth may change as time advances. They are useful boundary validations, but not persistent guarantees.

Sources:

[https://pydantic.dev/docs/validation/latest/api/pydantic/types/](https://pydantic.dev/docs/validation/latest/api/pydantic/types/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/validation/latest/api/pydantic/networks/](https://pydantic.dev/docs/validation/latest/api/pydantic/networks/?utm_source=chatgpt.com)

### 5.5 URL normalization and preservation of empty paths

Pydantic 2.12 added `url_preserve_empty_path` at configuration level and `UrlConstraints(preserve_empty_path=True)` for individual annotated URL types.

By default, supported URL parsing may normalize a URL without a path by adding `/`. Enabling empty-path preservation allows an input such as `https://example.com` to retain its empty path instead.

```
from typing import Annotatedfrom pydantic import AnyUrl, TypeAdapter, UrlConstraintsPreservingURL = Annotated[    AnyUrl,    UrlConstraints(preserve_empty_path=True),]adapter = TypeAdapter(PreservingURL)url = adapter.validate_python("https://example.com")assert str(url) == "https://example.com"
```

This illustrates that Pydantic's network types are not always passive wrappers around the original string. Validation can parse, normalize, and reconstruct a URL, potentially changing its textual representation.

Preservation matters when different textual forms have distinct protocol, signature, cache-key, or application semantics.

The original release announcement identifies the possibility of changing the default in V3; that is a future compatibility consideration, not a change to the 2.14.2 default.

Source: [https://pydantic.dev/articles/pydantic-v2-12-release](https://pydantic.dev/articles/pydantic-v2-12-release?utm_source=chatgpt.com)

## 6. Advanced JSON Schema generation policies

### 6.1 Required fields in serialization schemas

`ConfigDict(json_schema_serialization_defaults_required=True)` changes the treatment of defaulted fields when generating a serialization-mode JSON Schema.

Ordinarily, a field with a default is not required for model validation. However, a normally serialized model instance will contain that field because the default has been applied during construction.

The setting makes that distinction explicit in the generated serialization schema.

```
from pydantic import BaseModel, ConfigDictclass Record(BaseModel):    model_config = ConfigDict(        json_schema_serialization_defaults_required=True    )    identifier: str    revision: int = 1
```

For this model, `revision` is not required in validation-mode JSON Schema, but is marked required in serialization-mode JSON Schema.

This provides more accurate representation of the model's ordinary emitted structure when its defaults are included.

However, output policies such as `exclude_unset`, `exclude_defaults`, or explicit field exclusion can still omit otherwise present fields. Therefore, the setting should not be interpreted as a guarantee that every possible serialization call produces the same set of properties.

Architectural significance. Pydantic can represent different notions of requiredness depending on whether the schema describes accepted input or expected output. This supports schema consumers that distinguish optional input parameters from populated response properties.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#json_schema_serialization_defaults_required](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#json_schema_serialization_defaults_required)

### 6.2 Forcing schema-generation modes

`ConfigDict(json_schema_mode_override=...)` can force validation or serialization schema generation regardless of the mode requested by a schema consumer.

The available values are `"validation"`, `"serialization"`, and `None`.

When the setting is not `None`, the chosen mode takes precedence over the mode passed to the generation function.

This can be valuable when downstream tooling cannot accommodate separate input and output definitions for the same model. Pydantic documentation specifically discusses cases in which distinct definitions receive `-Input` and `-Output` suffixes to avoid reference conflicts.

A forced mode removes that distinction for the affected model.

The tradeoff is important: suppressing distinct schemas does not make the model's validation and serialization representations equivalent. It merely makes the schema generator produce the selected representation consistently.

This can simplify schema naming and references while potentially misrepresenting one direction of a bidirectional interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#json_schema_mode_override](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#json_schema_mode_override)

### 6.3 Primitive union representation

JSON Schema generation supports the `union_format` parameter.

The two options are:

| Mode                   | Generated representation                                                         |
| ---------------------- | -------------------------------------------------------------------------------- |
| `any_of`               | An `anyOf` containing the schemas for individual alternatives                    |
| `primitive_type_array` | A `type` array when the union consists of eligible unconstrained primitive types |

For example, a simple `str | None` union may be represented as:

```
{
  "type": ["string", "null"]
}
```

rather than:

```
{
  "anyOf": [
    {"type": "string"},
    {"type": "null"}
  ]
}
```

The primitive-type-array mode falls back to `anyOf` when a member is not an eligible primitive type or carries constraints or metadata that cannot be represented by a simple type array.

This is a JSON Schema representation choice, not a change to Pydantic's runtime union-matching algorithm.

It can reduce unnecessary schema nesting for consumers that prefer compact primitive unions. It is not a general schema minimizer or a way to flatten arbitrary discriminated or structured unions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/json_schema/](https://pydantic.dev/docs/validation/latest/api/pydantic/json_schema/?utm_source=chatgpt.com)

### 6.4 Omitting unrepresentable types with `PydanticOmit`

Custom JSON Schema generation can encounter executable Pydantic types whose runtime behavior has no useful JSON Schema equivalent.

Pydantic exposes `PydanticOmit` for deliberately omitting such schema elements rather than failing the entire generation operation.

A `GenerateJsonSchema` subclass can override `handle_invalid_for_json_schema()` and raise `PydanticOmit`:

```
from pydantic_core import PydanticOmit, core_schemafrom pydantic.json_schema import (    GenerateJsonSchema,    JsonSchemaValue,)class OmitUnrepresentable(GenerateJsonSchema):    def handle_invalid_for_json_schema(        self,        schema: core_schema.CoreSchema,        error_info: str,    ) -> JsonSchemaValue:        raise PydanticOmit
```

The resulting JSON Schema can describe the representable subset of a Pydantic contract.

This differs from `SkipJsonSchema`, which is an explicit annotation-level mechanism for excluding selected schema representations.

`PydanticOmit` is useful when a schema-generation policy needs to deal systematically with constructs that cannot be described externally, rather than requiring every individual type to carry exclusion metadata.

There is a significant completeness tradeoff: omitting a field from a generated schema may cause external consumers to believe that the field does not exist, even though it remains part of the executable Python contract.

The generated schema should therefore be understood as an intentionally partial projection, not a fully equivalent description of validation behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/concepts/json_schema/](https://pydantic.dev/docs/validation/latest/concepts/json_schema/?utm_source=chatgpt.com)

## 7. Additional validation and representation policies

### 7.1 Regular-expression engine selection

Pydantic's `pattern` constraints support two regular-expression execution engines, selected through `ConfigDict(regex_engine=...)`.

The default `rust-regex` engine uses Rust's non-backtracking `regex` crate. The alternative `python-re` uses Python's `re` implementation.

These engines differ in both expressive power and computational behavior.

The Rust engine is designed to avoid pathological backtracking behavior and therefore provides stronger resistance to regex-based denial-of-service scenarios. Python's regex engine supports additional constructs, including lookarounds and backreferences, but is not generally subject to the same non-backtracking guarantee.

```
from pydantic import BaseModel, ConfigDict, Fieldclass Identifier(BaseModel):    model_config = ConfigDict(regex_engine="python-re")    value: str = Field(pattern=r"^abc(?=def)")
```

The positive lookahead in this example is supported by Python's engine but not by the default Rust regex engine.

An important exception is that supplying a compiled Python `re.Pattern` causes Pydantic to use the Python engine regardless of `regex_engine`. This preserves the compiled pattern's Python-specific flags and behavior.

Architectural significance. Regex selection is a tradeoff between richer pattern syntax and stronger worst-case execution characteristics. It should be treated as part of a validation contract's behavior, not merely as a performance optimization.

The Rust engine remains the more appropriate default when its supported syntax is sufficient, especially for patterns applied to untrusted input.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#regex_engine](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#regex_engine)

### 7.2 ASCII-only string validation

Pydantic 2.13 introduced `ascii_only` to `StringConstraints`.

```
from typing import Annotatedfrom pydantic import StringConstraints, TypeAdapterASCIIString = Annotated[    str,    StringConstraints(ascii_only=True),]adapter = TypeAdapter(ASCIIString)
```

The constraint rejects non-ASCII characters using the native string-validation machinery, without requiring a custom validator or a handwritten regex.

It composes with other supported string constraints, such as length, whitespace handling, and case conversion.

This is distinct from `ensure_ascii` during JSON serialization. An ASCII-only validation contract restricts the accepted string value; ASCII-escaped JSON serialization can represent Unicode values without restricting their semantic content.

Source: [https://pydantic.dev/articles/pydantic-v2-13-release](https://pydantic.dev/articles/pydantic-v2-13-release?utm_source=chatgpt.com)

### 7.3 Independent alias acceptance and serialization policies

Pydantic 2.11 introduced finer-grained alias configuration through:

- `validate_by_alias`
- `validate_by_name`
- `serialize_by_alias`

These controls distinguish the input names a model accepts from the output names it emits.

```
from pydantic import BaseModel, ConfigDict, Fieldclass Record(BaseModel):    model_config = ConfigDict(        validate_by_alias=True,        validate_by_name=True,        serialize_by_alias=True,    )    record_id: str = Field(alias="recordId")
```

With this configuration, both `record_id` and `recordId` can populate the field, while normal serialization emits `recordId`.

The defaults are intentionally asymmetric:

| Configuration        | Default in 2.14.2 |
| -------------------- | ----------------- |
| `validate_by_alias`  | `True`            |
| `validate_by_name`   | `False`           |
| `serialize_by_alias` | `False`           |

Pydantic prevents disabling both alias-based and name-based field population, since that would make fields impossible to populate through either mechanism.

The older `populate_by_name` configuration is no longer recommended as of 2.11 and is expected to be deprecated in V3. Enabling both `validate_by_alias` and `validate_by_name` reproduces its intended behavior.

Pydantic also states that the default for `serialize_by_alias` is expected to change to `True` in V3. This is a planned direction, not the released V2 default.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Architectural significance. Input compatibility and output canonicalization can be configured independently. A contract can accept multiple naming conventions while consistently producing one preferred representation.

However, accepting multiple names for the same field raises questions of precedence and ambiguity when several accepted names occur in one input. Alias priority and extra-field policy remain relevant, rather than being eliminated by permissive alias acceptance.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com)

### 7.4 Temporal input and output units

`ConfigDict` exposes two distinct families of temporal representation controls.

Input interpretation: `val_temporal_unit`. This governs numeric input for supported datetime-like types, notably `datetime` and `date`, and accepts:

- `seconds`
- `milliseconds`
- `infer`

The default `infer` applies a magnitude-based heuristic to decide how to interpret numeric timestamps. Explicitly choosing a unit avoids relying on that heuristic.

Output representation: `ser_json_temporal`. Introduced in 2.12, this governs JSON serialization of date, datetime, time, and timedelta values, and accepts:

- `iso8601`
- `seconds`
- `milliseconds`

The default is `iso8601`.

```
from datetime import datetimefrom pydantic import BaseModel, ConfigDictclass Timestamped(BaseModel):    model_config = ConfigDict(        val_temporal_unit="seconds",        ser_json_temporal="milliseconds",    )    timestamp: datetime
```

This makes it possible to interpret numeric incoming timestamps under one unit convention while producing an explicit outgoing representation.

The older `ser_json_timedelta` setting remains available, but Pydantic 2.12 recommends `ser_json_temporal` instead. The older setting is expected to be deprecated in V3.

Architectural significance. Unit ambiguity is a semantic validation problem, not simply a parsing detail. Pydantic can encode this policy centrally rather than requiring independent timestamp-conversion code at each input boundary.

The configuration does not itself solve time-zone policy, daylight-saving ambiguity, or the meaning of arbitrary epoch conventions. Those considerations remain distinct from the accepted unit.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#val_temporal_unit](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#val_temporal_unit)

### 7.5 Binary and nonfinite-number JSON policies

Several additional `ConfigDict` settings control binary values and floating-point special values.

| Setting            | Available values               | Function                                                         |
| ------------------ | ------------------------------ | ---------------------------------------------------------------- |
| `ser_json_bytes`   | `utf8`, `base64`, `hex`        | Encoding used when serializing bytes into JSON                   |
| `val_json_bytes`   | `utf8`, `base64`, `hex`        | Decoding applied when interpreting JSON representations of bytes |
| `ser_json_inf_nan` | `null`, `constants`, `strings` | Serialization of NaN and infinities                              |

For bytes, matching validation and serialization formats enables compatible round trips for supported values.

The distinction between these settings and `EncodedBytes` is important. `ser_json_bytes` and `val_json_bytes` are general configuration policies for bytes representations. `EncodedBytes` associates a specific encoding protocol with an individual annotated type.

Nonfinite numbers introduce different tradeoffs:

- `null` is the default output representation for NaN and infinity, but loses their distinction from an actual null value.
- `constants` emits tokens such as `NaN` and `Infinity`, which are not valid numeric literals in strict standard JSON.
- `strings` emits quoted representations, preserving a textual distinction while changing the output type.

These settings control serialization representation. They do not independently determine whether nonfinite numbers are accepted during validation; `allow_inf_nan` is a separate validation policy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs



Architectural significance. These controls can make numeric and binary wire formats explicit, avoiding ad hoc encoders and inconsistent treatment across models. The choice still needs to match the contract of any consuming system.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com)

## 8. Model lifecycle, equality, and contract metadata

### 8.1 Private-attribute factories with validated model data

Since Pydantic 2.13, `PrivateAttr(default_factory=...)` can receive the model's validated field data.

Previously, accessing validated fields during private-attribute initialization generally required a separate `model_post_init()` implementation or another initialization mechanism.

```
from pydantic import BaseModel, PrivateAttrclass Measurement(BaseModel):    length: float    width: float    _initial_area: float = PrivateAttr(        default_factory=lambda data: (            data["length"] * data["width"]        )    )measurement = Measurement(length=2.0, width=3.0)assert measurement._initial_area == 6.0assert measurement.model_dump() == {    "length": 2.0,    "width": 3.0,}
```

The factory receives validated model fields and any previously initialized private attributes. The returned value initializes private state but does not become part of the model's declared schema.

This is useful for derived internal metadata, initialization snapshots, auxiliary indexes, and other non-field state that depends on already validated input.

Several distinctions remain important.

Private attributes are not validated fields. A type annotation on a private attribute does not establish ordinary field-validation behavior.

Derived private state is not automatically recomputed. If `length` or `width` subsequently changes, `_initial_area` retains its initial value unless application logic explicitly updates it.

Initialization and serialization are separate. Private attributes do not ordinarily appear in `model_dump()` or generated JSON Schema, although they may influence custom validators, serializers, methods, and model equality.

Factory execution may have side effects. As with ordinary defaults, calling a factory is an operation, not merely reading declarative metadata.

This mechanism can eliminate some uses of `model_post_init()`, but does not supersede it for more elaborate initialization procedures requiring multiple ordered operations or lifecycle checks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/validation/latest/concepts/models/#private-model-attributes](https://pydantic.dev/docs/validation/latest/concepts/models/?utm_source=chatgpt.com#private-model-attributes)

[https://pydantic.dev/docs/validation/latest/api/pydantic/fields/#privateattr](https://pydantic.dev/docs/validation/latest/api/pydantic/fields/?utm_source=chatgpt.com#privateattr)

### 8.2 Model equality and state identity

Pydantic V2 changed the semantics of `BaseModel.__eq__()`.

Two model instances are equal only when their relevant state agrees, including:

- Model type, with special treatment for instances sharing a generic model's origin.
- Declared field values.
- Permitted extra-field values.
- Private-attribute values.

Models are no longer equal to ordinary dictionaries containing equivalent public field values.

```
from pydantic import BaseModel, PrivateAttrclass Record(BaseModel):    identifier: str    _revision_token: str = PrivateAttr(default="a")first = Record(identifier="R1")second = Record(identifier="R1")assert first == secondsecond._revision_token = "b"assert first != secondassert first.model_dump() == second.model_dump()assert first != {"identifier": "R1"}
```

This reveals a consequential distinction between model equality and serialized equivalence.

Two objects may produce identical ordinary serialized representations but compare unequal because their private states differ. Conversely, two generic model instances need not have precisely identical parameterizations to compare equal when they share the same generic origin and otherwise equivalent state.

Model equality is therefore not intrinsically a test of JSON contract equivalence, nor is it a substitute for explicit comparison of canonical exported representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/get-started/migration/](https://pydantic.dev/docs/validation/latest/get-started/migration/?utm_source=chatgpt.com)

### 8.3 Explicit-field tracking and `RootModel` copy semantics

Pydantic 2.13 introduced two further behavior changes worth recording because they affect state tracking and object identity.

Extra fields and `model_fields_set`. For models permitting extra fields, properties assigned after model construction are now included in `model_fields_set`, rather than tracking only extra properties supplied during initial validation.

```
from pydantic import BaseModel, ConfigDictclass Record(BaseModel):    model_config = ConfigDict(extra="allow")    identifier: strrecord = Record(identifier="A")record.new_property = 10assert "new_property" in record.model_fields_set
```

This affects operations that distinguish explicitly populated values from unset values, including `exclude_unset` serialization.

Shallow copying of `RootModel`. Since 2.13, a shallow `model_copy()` of a `RootModel` also creates a shallow copy of the root value. For a list root, the copied model no longer shares the same list object with the original.

```
from pydantic import RootModelclass Numbers(RootModel[list[int]]):    passoriginal = Numbers([1, 2])copied = original.model_copy(deep=False)assert copied is not originalassert copied.root is not original.root
```

The elements of more complex root collections may still contain shared mutable objects because the operation is shallow, not recursive.

The identity distinction is material for mutation-sensitive operations: a shallow model copy does not always mean every internal object is shared, nor does it imply deep independence.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

pydantic.dev



Source: [https://pydantic.dev/articles/pydantic-v2-13-release](https://pydantic.dev/articles/pydantic-v2-13-release?utm_source=chatgpt.com)

### 8.4 Deprecated fields and source-derived schema documentation

Pydantic supports field deprecation metadata through `Field(deprecated=...)`.

The declaration can use a Boolean, a deprecation message, or an appropriate warning object. It marks the field as deprecated in generated JSON Schema and can emit a deprecation warning when the field is accessed.

```
from pydantic import BaseModel, Fieldclass Record(BaseModel):    current_name: str    legacy_name: str | None = Field(        default=None,        deprecated="Use current_name instead",    )
```

This provides a native way to communicate field lifecycle status to both Python callers and downstream schema consumers.

Deprecation metadata does not automatically reject old fields, translate them to replacements, or remove them during serialization. Such behavior must be specified separately.

A related metadata mechanism is `ConfigDict(use_attribute_docstrings=True)`, which can derive field descriptions from string literals immediately following attribute declarations:

```
from pydantic import BaseModel, ConfigDictclass Measurement(BaseModel):    model_config = ConfigDict(        use_attribute_docstrings=True    )    pressure: float    """Absolute pressure in pascals."""
```

This can reduce duplication between source-level field documentation and generated schema descriptions.

It depends on the class's source code being available at runtime. Pydantic documents limitations for certain `TypedDict` and standard-library dataclass patterns, especially with inheritance or ambiguous class names. Explicit descriptions supplied through `Field(description=...)` take precedence.

These mechanisms distinguish metadata governing contract documentation and lifecycle from the executable acceptance and conversion rules governing validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/validation/latest/concepts/fields/#deprecated-fields](https://pydantic.dev/docs/validation/latest/concepts/fields/?utm_source=chatgpt.com#deprecated-fields)

[https://pydantic.dev/docs/validation/latest/api/pydantic/config/#use_attribute_docstrings](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#use_attribute_docstrings)

## 9. Callable and dataclass validation capabilities

### 9.1 Complete callable signatures and validated return values

`@validate_call` can handle a broader range of Python callable signatures than ordinary fixed positional arguments.

Supported patterns include positional-only parameters, keyword-only parameters, variadic positional arguments, variadic keyword arguments, asynchronous functions, and typed keyword expansion through `Unpack[TypedDict]`.

It also supports opt-in return-value validation.

```
from typing_extensions import TypedDict, Unpackfrom pydantic import validate_callclass Coordinates(TypedDict):    x: float    y: float@validate_call(validate_return=True)def squared_distance(    **coordinates: Unpack[Coordinates],) -> float:    return (        coordinates["x"] ** 2        + coordinates["y"] ** 2    )result = squared_distance(x=3, y=4)assert result == 25.0
```

The `TypedDict` determines the accepted keyword names and their value types. This is more expressive than a generic `**kwargs: Any` signature and allows an existing structural type contract to be reused as the callable's argument contract.

Return validation is disabled by default. Enabling `validate_return=True` adds a further boundary after the function has executed, potentially coercing or rejecting its returned value.

The decorator also exposes the original callable through its `raw_function` attribute:

```
raw = squared_distance.raw_functionresult = raw(x=3.0, y=4.0)
```

Calling the raw function bypasses the decorator's Pydantic validation, including its return-validation behavior.

This establishes two distinct execution paths: one with runtime contract enforcement and one relying on the caller's existing guarantees.

The bypass is useful when the same callable is used through both untrusted and already validated inputs. However, static type checkers may not recognize `raw_function` even though the normal decorated signature is preserved.

There are also exception-semantic differences. An invalid function call, including a missing required argument, generally raises Pydantic's `ValidationError` rather than the ordinary Python `TypeError` that an undecorated function would raise. The wrapper also introduces per-call validation overhead, even though signature analysis and schema construction are reused.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Architectural significance. Typed callable contracts can be enforced without constructing separate request-model classes for every function. Reusing `TypedDict`, `Annotated`, and custom types allows a function signature to participate directly in the same validation vocabulary as structured records.

Source: [https://pydantic.dev/docs/validation/latest/concepts/validation_decorator/](https://pydantic.dev/docs/validation/latest/concepts/validation_decorator/?utm_source=chatgpt.com)

### 9.2 Dataclass lifecycle and schema rebuilding

Pydantic dataclasses have an explicit schema-rebuilding interface:

```
from pydantic.dataclasses import (    dataclass,    rebuild_dataclass,)@dataclassclass Node:    name: str    child: "Node | None" = Nonerebuild_dataclass(Node)
```

`rebuild_dataclass()` is analogous to `BaseModel.model_rebuild()` and is particularly relevant when forward annotations could not be resolved during initial schema construction.

It accepts controls including `force`, `raise_errors`, and an explicit `_types_namespace` for resolving referenced symbols.

This capability is useful where dataclass definitions are generated, declared across modules, or contain references unavailable at initial class creation.

Pydantic dataclasses also differ from `BaseModel` in their initialization lifecycle:

- Their `__post_init__()` executes after validation.
- They do not inherit `BaseModel`'s validation and serialization methods.
- A `TypeAdapter` supplies appropriate external validation, serialization, and schema-generation operations.
- Extra-data behavior is not identical to that of `BaseModel`, including limitations around representation and validation of additional attributes.

A particularly important boundary is that dataclass-specific behavior should not be inferred solely from model configuration examples. The two interfaces share the core validation engine but expose different Python object semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/validation/latest/api/pydantic/dataclasses/#rebuild_dataclass](https://pydantic.dev/docs/validation/latest/api/pydantic/dataclasses/?utm_source=chatgpt.com#rebuild_dataclass)

[https://pydantic.dev/docs/validation/latest/concepts/dataclasses/](https://pydantic.dev/docs/validation/latest/concepts/dataclasses/?utm_source=chatgpt.com)

## 10. Diagnostics, error privacy, and exception provenance

### 10.1 Input exposure in validation errors

Pydantic's structured validation errors can include original input values. This is valuable for diagnostics but can expose sensitive content when validation failures are logged or returned externally.

`ConfigDict(hide_input_in_errors=True)` suppresses input values and input types in the formatted error message:

```
from pydantic import BaseModel, ConfigDictclass Credentials(BaseModel):    model_config = ConfigDict(        hide_input_in_errors=True    )    token: str
```

This configuration should not be treated as comprehensive redaction of the underlying exception.

Machine-readable diagnostic extraction has separate controls:

```
try:    Credentials(token=123)except Exception as exc:    if hasattr(exc, "errors"):        sanitized = exc.errors(            include_input=False,            include_url=False,        )
```

The `include_input=False` argument prevents original input values from appearing in the returned error details. `include_url=False` omits documentation URLs.

For `ValidationError`, these parameters provide a more explicit boundary when constructing externally visible diagnostics.

This distinction matters because formatting an exception, inspecting its structured details, retaining the exception object, and sending it to an observability system are different operations. Suppressing values in one representation does not guarantee their removal from every diagnostic path.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/validation/latest/api/pydantic/config/#hide_input_in_errors](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#hide_input_in_errors)

[https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/?utm_source=chatgpt.com)

### 10.2 Error-location policy

`ConfigDict(loc_by_alias=...)` determines whether validation error locations use the external key or alias that appeared in the input, rather than the Python field name.

The default is `True`.

This is distinct from enabling aliases during validation. Alias resolution controls which input names populate fields; `loc_by_alias` controls how failures are identified in error paths.

For example, a model field named `record_id` with validation alias `recordId` may report a failure at `recordId` when alias-based locations are enabled.

This can improve correspondence between a rejected external payload and its machine-readable error location.

However, consumers should not assume error locations are immutable identifiers across all possible input representations and versions. An alias-policy change can affect the path used to describe the same logical field.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#loc_by_alias](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#loc_by_alias)

### 10.3 Preserving Python exception causes

`ConfigDict(validation_error_cause=True)` exposes underlying Python exceptions involved in validation failures as an exception group attached to the validation error's cause.

This is particularly useful when custom Python validators raise exceptions that Pydantic converts into structured validation failures.

The setting preserves additional information for traceback inspection without replacing Pydantic's ordinary validation error reporting.

Two limitations are explicit in the upstream documentation.

First, Python 3.10 requires the `exceptiongroup` backport to provide the relevant exception-group functionality.

Second, Pydantic does not guarantee the exception group's internal structure as a stable machine-readable interface. The facility is intended primarily for debugging, rather than durable programmatic classification of validation errors.

Consequently, stable error classification should continue to rely on documented structured error types, not traceback formatting or exception-group nesting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic/config/#validation_error_cause](https://pydantic.dev/docs/validation/latest/api/pydantic/config/?utm_source=chatgpt.com#validation_error_cause)

## 11. Additional low-level `pydantic-core` operations

The original guide introduces direct `SchemaValidator` and `SchemaSerializer` usage. Several capabilities of those classes deserve additional coverage because they expose operations that are not merely aliases for ordinary model construction.

### 11.1 Schema-based acceptance testing

`SchemaValidator.isinstance_python()` returns a Boolean indicating whether a Python value satisfies a compiled validation schema under the supplied validation options.

```
from pydantic_core import SchemaValidator, core_schemavalidator = SchemaValidator(    core_schema.list_schema(        core_schema.int_schema()    ))assert validator.isinstance_python([1, 2, 3])assert not validator.isinstance_python(["invalid"])
```

Despite the method's name, this is not equivalent to Python's `isinstance()`.

It evaluates whether the input can pass the compiled Pydantic schema, potentially including conversion rules, constraints, and custom validators. Its behavior can therefore depend on strictness and context.

The method returns `False` for ordinary validation failures instead of raising a `ValidationError`. Internal or unexpected exceptions may still propagate.

It is useful when only an acceptance decision is required, but should not be substituted for `validate_python()` when the validated or transformed result is needed.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/#pydantic_core.SchemaValidator.isinstance_python](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/?utm_source=chatgpt.com#pydantic_core.SchemaValidator.isinstance_python)

### 11.2 Assignment validation through the core engine

`SchemaValidator.validate_assignment()` exposes assignment-time validation directly against a compiled model schema.

It receives the object, field name, and replacement value, alongside relevant validation options.

This is the lower-level operation behind assignment-validation behavior, rather than an independent incremental dataflow engine.

It is useful for advanced integrations that need to drive model-schema validation explicitly. However, its return structures and interaction with model state are more specialized than ordinary field assignment through a configured `BaseModel`.

It does not establish recursive change tracking for arbitrary mutable objects already held inside fields.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/#pydantic_core.SchemaValidator.validate_assignment](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/?utm_source=chatgpt.com#pydantic_core.SchemaValidator.validate_assignment)

### 11.3 Schema defaults without constructing a model

`SchemaValidator.get_default_value()` retrieves a default from the compiled schema.

It returns `None` when no default is available, or a `Some` wrapper containing the default value.

The wrapper is important because a valid schema default may itself be `None`; the interface must distinguish the absence of a default from a default whose value is null.

The operation can perform default-value validation and accepts strictness and validation context.

This enables inspection or execution of default behavior without constructing a complete `BaseModel` instance.

It is particularly relevant to lower-level schema consumers that need to distinguish required values from values supplied by a schema-defined default.

Source: [https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/#pydantic_core.SchemaValidator.get_default_value](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/?utm_source=chatgpt.com#pydantic_core.SchemaValidator.get_default_value)

### 11.4 Direct serialization and JSON-compatible conversion

`SchemaSerializer` exposes `to_python()` and `to_json()` for executing a compiled serialization schema.

Separately, `pydantic_core` provides standalone conversion functions:

| Function               | Purpose                                                                     |
| ---------------------- | --------------------------------------------------------------------------- |
| `to_json()`            | Serialize supported Python values directly into JSON bytes                  |
| `to_jsonable_python()` | Convert supported Python values into JSON-compatible Python objects         |
| `from_json()`          | Parse JSON into Python representations, including supported partial parsing |

`to_jsonable_python()` is especially useful where a JSON-compatible Python structure is needed without immediately producing encoded JSON bytes.

This is distinct from validating a value against a declared `TypeAdapter` or model schema. A generic JSON-compatible conversion does not by itself establish that the input satisfied a particular typed contract, nor should it be assumed to apply all of that contract's custom serialization policies.

The distinction is between schema-directed serialization, which interprets values according to a compiled contract, and general JSON-compatible conversion, which operates on the supplied Python values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/](https://pydantic.dev/docs/validation/latest/api/pydantic-core/pydantic_core/?utm_source=chatgpt.com)

### 11.5 Composing core schemas for serialization

Pydantic 2.14 expanded low-level serialization-schema composition so that supported `CoreSchema` structures can be used as serialization schemas.

This makes some custom serialization definitions more composable: existing schema components can be reused instead of defining a separate serialization callback for every operation.

The capability is particularly relevant to advanced custom types that already construct their validation behavior using `pydantic_core.core_schema` nodes.

It preserves the fundamental boundary identified in the original reference: composition is limited to node kinds supported by the Rust engine and its Python callback interfaces. Supplying a core schema does not introduce new arbitrary native Rust operations.

The feature also belongs to the lower-level extension surface, where compatibility sensitivity and implementation complexity are greater than for standard validators and serializers.

Source: [https://github.com/pydantic/pydantic/pull/13680](https://github.com/pydantic/pydantic/pull/13680?utm_source=chatgpt.com)

### 11.6 Source-repository and package boundaries

One ecosystem detail has changed since earlier Pydantic V2 documentation.

In Pydantic 2.13, the `pydantic-core` source repository was incorporated into the main `pydantic` repository to simplify maintenance. However, `pydantic-core` continues to be distributed as a separate Python package.

This distinction matters for source inspection and package architecture: repository consolidation does not imply that the compiled Rust engine has been eliminated as a separately installed distribution.

Source: [https://pydantic.dev/articles/pydantic-v2-13-release](https://pydantic.dev/articles/pydantic-v2-13-release?utm_source=chatgpt.com)

## 12. Cross-cutting architectural distinctions

The added capabilities expose several consequential distinctions that are easy to miss when considering Pydantic features independently.

| Distinction                                          | Consequence                                                                                                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input validity versus output fidelity                | `round_trip`, encoding protocols, and serialization policies govern reusability of representations; they do not guarantee byte-for-byte preservation |
| Declared type versus runtime subtype                 | Polymorphic serialization can emit richer objects than the declared field's ordinary JSON Schema describes                                           |
| Closed structure versus extensible structure         | PEP 728 distinguishes rejecting unknown keys from accepting additional keys whose values remain typed                                                |
| Eager validation versus deferred validation          | `Iterable[T]` defers some guarantees until consumption, unlike eagerly validated collections                                                         |
| Complete rejection versus tolerant acceptance        | `OnErrorOmit` can return a usable value while silently discarding information from the original input                                                |
| Model state versus serialized state                  | Private attributes participate in model equality but are not ordinarily exposed in serialized output                                                 |
| Validation errors versus safe diagnostics            | Structured errors may retain input data even when formatted error output is configured to hide it                                                    |
| Executable schema versus portable schema             | JSON Schema customization can omit, simplify, or reinterpret aspects of Python runtime behavior                                                      |
| Schema-aware serialization versus general conversion | Direct JSON-compatible conversion does not replace contract-specific serialization rules                                                             |

Together, these distinctions refine the core architectural model established in the original guide.

Pydantic provides not one indivisible validation contract, but a collection of interoperating mechanisms controlling accepted representations, normalized Python values, object state, deferred execution, error handling, and serialized output. These mechanisms can be composed, but their guarantees are not always identical or automatically preserved across boundaries.

The most valuable additional functionality is therefore not necessarily the ability to impose more constraints. It is the ability to express these different boundaries precisely, reuse the same underlying type semantics where appropriate, and avoid bespoke conversion or validation machinery without obscuring information loss, runtime behavior, or contract compatibility.