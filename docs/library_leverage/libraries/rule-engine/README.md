# rule-engine

**Realization assessed:** rule-engine 5.1.0, pinned.

**Researched:** 2026-10-29 by the R6 cluster.
- The [overview](../../../libraries/scientific_compute/rule-engine.md) was read end to end.
- Context7 (`/zerosteiner/rule-engine`) documents master, so decisions rest on the installed 5.1.0
  source: `engine/context.py`, `types/datatype.py`, `types/dataclass.py` and
  `ast/expression/access.py`.
- One probe was run
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-interfaces/README.md)).

## Reusable opportunity types

<a id="rule-engine-typed-schema-from-python-types"></a>

### `rule-engine/typed-schema-from-python-types`

**Need.** Derive a rule language's typed symbols and OBJECT schemas from existing Python types,
instead of keeping a parallel, hand-written type map.

**APIs.**
- Derivation: `DataType.from_type(hint)`, `DataType.OBJECT.from_dataclass(name, cls, strict=)` and
  `type_resolver_from_dataclass(cls, strict=)`.
- Public constructors: `type_resolver_from_dict(mapping)`, `OBJECT(name, attributes=, accessor=)`,
  `NULLABLE(T)`, `ARRAY(T)`, `MAPPING(K, V)` and `FUNCTION(…)`.

**How hints map** (probe-observed):

| Hint | Result |
|---|---|
| `str`, `X \| None`, `list[T]`, `dict[K, V]` | Map correctly |
| `Annotated[T, …]` | Maps to `T`; constraints are dropped |
| `tuple[T, ...]` | Maps to `ARRAY(UNDEFINED)`; the element type is lost |
| `Literal[...]` | Raises `TypeError` |
| Enum and `StrEnum` | Raise `ValueError` |
| Union of more than one non-None type, including discriminated unions | Raises `ValueError` |
| Pydantic `BaseModel` | Rejected by `from_type` and by `type_resolver_from_dataclass` |

A Pydantic *dataclass* is accepted. With `strict=True` an enum field fails; with `strict=False` it
maps to `UNDEFINED`.

**Residual.** The caller still owns enum and closed-vocabulary semantics (rule-engine has no enum
type), sum types and constraints.

**Semantics.**
- OBJECT compatibility is nominal.
- `FLOAT` is backed by `Decimal`.
- `NULLABLE` is enforced when a rule is compiled: attribute access, arithmetic and ordering on a
  nullable value are refused at that point. A schema's declared nullability therefore decides which
  rule texts compile.

<a id="rule-engine-logical-view-over-physical-records"></a>

### `rule-engine/logical-view-over-physical-records`

**Need.** Keep a stable rule vocabulary (names, types, nullability) while the underlying record
representation changes.

**APIs.** `DataType.OBJECT(name, attributes=…, accessor=fn(obj, name))` declares the logical schema,
and the accessor reads the physical record. Use it with
`Context(type_resolver=…, mapping_attribute_lookup=False, default_value=…)`.

**Discharged.**
- Unknown attributes are rejected at parse time, with a suggestion.
- The schema stays separate from storage.

**Residual.**
- Accessor values are coerced but **not** checked against the declared type (`verify_type=False`).
- An accessor that raises `AttributeError` or `KeyError` becomes `ObjectAttributeError`, or the
  context's `default_value`. The accessor must therefore never turn "unknown" into a null or false
  value that a rule would read as a pass.
- The accessor runs on every attribute access.

<a id="rule-engine-compile-time-rule-introspection"></a>

### `rule-engine/compile-time-rule-introspection` (mostly a negative result)

**Public surface.**
- `Context.symbols`.
- Error classes in `rule_engine.errors` that carry attributes.
- `Builtins.from_defaults(...)`.

**No public typed traversal exists in 5.1.0.** Upstream documentation says `rule_engine.ast` "should
be treated as private… breaking changes may not cause a major version bump".

**Narrowest private route.** `DataType.NULLABLE.unwrap(node.object.result_type)`, which uses
non-underscore slots, matched private `GetAttributeExpression._object_type` in every probed case:
plain access, `&.` access and comprehension variables. It still depends on the private module and
needs an OBJECT guard.

**Comparative review refinement (2026-10-29).** In the installed 5.1.0 source,
`ExpressionBase.result_type` carries a docstring: "The data type of the result of successful
evaluation". A scratch probe matched it to `_object_type` across five access forms. The attribute is
documented, but it lives in a module upstream marks private. This narrows the negative result
without overturning it: the route reads a documented attribute of a private module, and a
regression test over the pack's rules guards it.

**Search scope.** The installed package was grepped for walk, visitor and children; the 5.1.0
`ast/__init__` exports and the Context7 docs were checked.

## Applicability at source `d739b88`

<a id="applicability-cbo-005"></a>

### CBO-005 — rebasing the released rule policy off the retiring environment: **rule-view rebase fits with conditions; derivation from Pydantic is ruled out; no public AST route**

**Opportunity:** [CBO-005](../../codebase/consumers-and-operations.md#cbo-005).
**Types:** all three above.

1. **Deriving the schema from release-generated types: ruled out (5.1.0).** The compiler's models
   use `Literal`, enums, discriminated unions, `tuple[T, ...]` and `Annotated` constraints, and
   rule-engine's extractors refuse or degrade every one of them (probe). What does fit is building
   `DataType` objects directly from the LinkML-derived definitions with the public constructors. That
   drops the string type notation and its parser, removing a round trip.
2. **Public traversal replacing `_object_type`: none exists.** The narrowed `object.result_type`
   route is still private. The pin reduces drift risk, and a regression test over the pack's rules is
   the guard.
3. **Smallest stable rule view: the logical-view type.**
   - Declare `Claim`, `Entity`, `Value` and the others as OBJECT schemas whose accessors read
     semantic records.
   - The legacy view dataclasses and projections can then retire while the authored names stay
     ([LOP-X001](../../assessment-patterns.md#lop-x001)).
   - **Consequential premise:** the view's declared types and nullability are part of the archived
     contract. A change makes archived rule text fail to compile, so it needs the `VERSION` bump and a
     recompile of every archived rule set.

**What the codebase still owns.**
- Vocabulary admission and the literal walk.
- Refusing `$now`, `$today` and `$random` through `Context.symbols`.
- Refusing regex on formulas.
- Ensuring undecided never becomes a pass.
- The type correctness of accessor values.

**Premise notes.**
- `type_resolver_from_dict` is already used.
- `ReleasedRulesPolicy` evaluates `when`/`check` `Rule` pairs, not a `Chain`. `Chain` is used in
  `orchestrate/policy.py`, so it should be confirmed which surfaces ADR-0018 binds.

## Coverage limits

- No walker over Pydantic `model_fields` was assessed; that question belongs to the
  [Pydantic account](../pydantic/README.md).
- Context7 tracks master, not 5.1.0.
