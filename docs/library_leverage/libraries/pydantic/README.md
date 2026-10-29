# Pydantic

**Realization assessed:** Pydantic 2.14.1 with pydantic-core 2.50.1.

**Researched:** 2026-10-29 by the R4 cluster.
- The [overview](../../../libraries/pydantic.md) was read end to end.
- Context7 was consulted at `/pydantic/pydantic/v2.14.1`, which matches the installed release.
- Installed source was read: `type_adapter.py`, `json_schema.py`, `networks.py` and
  `_generate_schema.py`.
- One probe ran against the real release compiler, profile `semantic-2`
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-pydantic/README.md)).

## Reusable opportunity types

<a id="pydantic-field-adapter-from-model"></a>

### `pydantic/field-adapter-from-model`

**Need.** A validator for one field, or one collection item, of a model class. The class may be
generated at runtime. The validator must keep the model's policy and be built once.

**Recognize.**
- `TypeAdapter(...)` constructed inside a per-item function.
- Reads of `adapter._type`. `TypeAdapter` has **no public type attribute** in 2.14.1.
- `field.rebuild_annotation()` or `get_args(field.annotation)` used to reach item types.

**Mechanism.**
- Keep the model classes themselves.
- `model_fields[name].rebuild_annotation()` restores `Annotated[T, *metadata]`. After
  `model_rebuild`, `.annotation` holds resolved types.
- Build `TypeAdapter(annotation, config=ConfigDict(...))` once per field, and reuse it. Reuse is the
  documented guidance.
- `config=` raises `PydanticUserError` (`type-adapter-config-unused`) when the annotation, with
  `Annotated` stripped, is a `BaseModel`, dataclass or `TypedDict`. It is allowed for
  `tuple[Model, ...]`, `dict[str, Model]`, unions and scalars (source and probe).

**Discharged.** Field constraint metadata travels with the annotation. Nested models keep their own
config.

**Residual.** Model-level config does **not** travel with an extracted annotation. This covers
`allow_inf_nan`, `strict` and `extra`. Re-supply it, or attach it per field.

**Semantic condition (probe-observed).** A bare float `TypeAdapter` accepts NaN and inf, even with
`strict=True` per call. Per-call strict covers strictness only.

**Comparative review additions (2026-10-29; scratch-checked on 2.14.1).**
- **A per-field fix.** Putting the constraint on the field type itself, as
  `Annotated[float, Field(allow_inf_nan=False)]`, makes extracted adapters refuse NaN and inf. The
  generated JSON Schema does not change.
- **NaN serializes as null.** By default (`ser_json_inf_nan='null'`), Pydantic writes NaN to JSON as
  `null`. A NaN that passes validation is therefore emitted as null rather than refused.

<a id="pydantic-presence-preserving-dump"></a>

### `pydantic/presence-preserving-dump`

**Need.** A plain Python projection that recursively keeps only explicitly supplied fields.

**Mechanism.** `model_dump(exclude_unset=True)`, or `TypeAdapter.dump_python(value, exclude_unset=True)`
for adapter outputs. Python mode is the default.

**Discharged (probe-observed on compiler output).**
- Recursive presence filtering.
- `MISSING` fields auto-excluded.
- Decimal scale kept.
- Dates stay native, and tuples stay tuples.
- Keys are field names unless `by_alias=True`.

**Conditions.**
- The dump follows the declared schema, not runtime subclasses.
- Custom serializers and computed fields change the output.
- JSON mode stringifies values.
- `model_copy(update=)` bypasses validation.

<a id="pydantic-shared-defs-json-schema"></a>

### `pydantic/shared-defs-json-schema`

**Need.** One JSON Schema document covering many models or adapters, with each class defined once.

**Mechanism.**
- `models_json_schema([(Model, mode), …])` accepts model classes only.
- `TypeAdapter.json_schemas([(key, mode, adapter), …])` also accepts union adapters.
- Both return a `$ref` map plus one shared `$defs`.

**Discharged.**
- Definition sharing and naming.
- Model-level `__get_pydantic_json_schema__` fragments land on their definition (probe: shared
  definitions equal the per-class schemas minus their local `$defs`).

**Conditions.**
- The version policy allows `$ref`/`$defs` naming to change in minor releases.
- Validation and serialization schemas can differ.
- Hooks should use `handler.resolve_ref_schema`.

<a id="pydantic-annotated-marker-positions"></a>

### `pydantic/annotated-marker-positions`

**Need.** Find positions in a typed value tree that play a domain role, by declared type rather than
by key name.

**Mechanism.** A marker object in `Annotated[T, MARKER]` metadata, read back through
`model_fields[name].metadata` while recursing through `get_origin`/`get_args`.

**Residual.**
- The visitor itself.
- Collision and refusal policy.
- Rebuilding instances.
- Caching per class.

**Limits.**
- Core-schema traversal is not a stable public contract.
- A contextual `WrapSerializer` can rewrite but cannot *collect*, and only one serializer is allowed
  per field.

<a id="pydantic-stdlib-dataclass-wire-adapter"></a>

### `pydantic/stdlib-dataclass-wire-adapter`

**Need.** Wire validation plus a JSON Schema for an existing stdlib dataclass request type.

**Mechanism.** `TypeAdapter(DC)` builds a dataclass schema and calls `__post_init__`. Config goes
through `__pydantic_config__` or `@with_config`; `config=` is refused for dataclasses.

**Residual.**
- Invariants checked only in `__post_init__` are invisible to the JSON Schema. Move them to
  `Annotated[int, Field(ge=…, le=…)]` to publish them.
- Context-dependent checks stay in code.
- Evidence: installed source only.

## Applicability at source `d739b88` (read through `3d97504`)

<a id="applicability-cbo-013"></a>

### CBO-013 — prepared-release contract: **fits with conditions; a correctness gap was found**

**Opportunity:** [CBO-013](../../codebase/release-preparation.md#cbo-013).
**Types:** field-adapter-from-model, shared-defs-json-schema.

**Public replacement for `_type`.** Preparation already holds the model classes. It can pass them, or
prebuilt per-field adapters (with `config=ConfigDict(strict=True, allow_inf_nan=False)`, and no
config for model-class annotations), into a non-identity slot on the `PreparedRelease` root.

**Identity trap.** `releases._products` archives definitions through `asdict`, and `compare=False`
does not stop that. Derived indices must therefore not be added to `ClassDefinition` or
`PropertyDefinition`; they belong on the root.

**Native range.** The Pydantic annotation collapses `float`/`double` and `string`/`uri`. The compiler
must emit the native range from its own type walk.

**Correctness gap (not a leverage claim).**
- `property_adapter` returns `TypeAdapter(annotation)` without model config. With `strict=True` it
  accepts **NaN** for scalar float properties and **inf** for multivalued float items, while the
  generated models refuse both (probe P1b/P1c; coordinator-verified source).
- Its docstring promises a "strict output boundary … including its constraints".
- Downstream identity code refuses non-finite floats later, as a `ValueError`.
- The query read path's cached adapter shares the gap.
- No production path reaching it was established at the assessment baseline. **Update
  (comparative review, 2026-10-29):** the serving Reader (`serve/read.py`) now builds field adapters
  through `property_adapter`, so the gap sits on the serving boundary. The review recommends the
  per-field annotation fix ([review](../../reviews/release-lifecycle.md#cbo-013)).

**Unsettled.** Whether per-field adapters should be built eagerly or memoized lazily per release
(unmeasured).

<a id="applicability-cbo-016"></a>

### CBO-016 — release-typed instance traversal: **fits for the plain projection; walkers fit with conditions**

**Opportunity:** [CBO-016](../../codebase/consumers-and-operations.md#cbo-016).
**Types:** presence-preserving-dump, annotated-marker-positions.

**Plain projection** (probe P2, on compiler output):
- `model_dump(exclude_unset=True)` equals `_native` exactly.
- With lists in place of tuples, it equals `_plain` and `consolidation.plain`.
- The only residual is the list-versus-tuple policy.

**Walkers.** The descriptor walkers carry domain policy that Pydantic does not discharge. A single
descriptor visitor owned by the release is library-neutral.

**Alternatives.**
- Compiler-attached `Annotated` role markers. The legacy `core/batch.py` already uses this for
  `CITATION`. It couples compiled metadata to domain roles.
- Rewriting through a serializer, and core-schema traversal, are ruled out.

**Missed site.** `conditional_rules.validate_rules` is another shallow projection.

<a id="applicability-cbo-003"></a>

### CBO-003 — library part: **capability fits; changing the archive is a design decision**

**Opportunity:** [CBO-003](../../codebase/release-preparation.md#cbo-003).
**Type:** shared-defs-json-schema.

- `TypeAdapter.json_schemas` fits because abstract boundaries are union adapters. Its definitions
  equal the per-class artifacts, conditional fragments included (probe P3).
- Replacing archived `json_schema/{name}` artifacts changes archive bytes and needs a compiler-version
  bump.
- `defer_build` only defers cost; laziness would require removing the artifacts from the archive.

<a id="applicability-cbo-006"></a>

### CBO-006 — comparator operand adapter: **unsettled; Pydantic is not the decisive lever**

**Opportunity:** [CBO-006](../../codebase/consumers-and-operations.md#cbo-006).

- The adapter already exists (`_comparison_value`/`_comparison_condition`), and its work is domain
  normalization.
- Pydantic could host a comparator-owned operand union using a callable `Discriminator`. Choosing
  between the legacy `core.values` and a new operand model is the
  [LOP-X001](../../assessment-patterns.md#lop-x001) decision.
- **Observed hazard.** `value.model_copy(update={unit, basis})` writes without validation.

<a id="applicability-informs"></a>

### Informs CBO-001, CBO-005 and CBO-017

- **CBO-001: fits with conditions.** `TypeAdapter(QuerySpec)` validates the nested handles, calls
  `__post_init__` and emits JSON Schema. The `page_size` range is invisible to the schema until it is
  moved into `Annotated`. Release-dependent handle resolution stays in code.
- **CBO-005.** Generated models expose a typed field tree. Unset fields read as `MISSING`, so a rule
  subject should be `model_dump(exclude_unset=True)`. The rule-engine side is in
  [rule-engine](../rule-engine/README.md#applicability-cbo-005).
- **CBO-017.** Validating directly into stdlib dataclasses with `TypeAdapter(ExecutionModelProducts)`
  is possible, but it contradicts the pivot's cattrs selection. It is recorded as a capability only.

## Coverage limits

- No abstract boundary with a `kind` discriminator was probed.
- No consumer route was changed or run.
- Nothing was timed.
