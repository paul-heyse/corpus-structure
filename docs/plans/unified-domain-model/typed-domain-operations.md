# Generated typed domain operations

**Status:** Planned; UM-03 is not implemented by this document. **Created:** 2026-11-01.
**Target:** Proposed. Consumes review [R05](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R05)
and the construction/serialization portions of R06/R09. The
[coordinator](../unified-domain-model_2026-11-01.md) owns mutable package state and acceptance.

**Planning snapshot:** committed source/review `370f0643` plus the specifically inspected dirty
PDF/model/native seams. The PDF series is still completing and may change those seams. This plan
does not continuously absorb that work or own its acceptance. A later update will reconcile the
then-current PDF snapshot as a discrete step before dependent execution.

## Baseline and boundary

Existing `claim_tasks(...) -> tuple[ClaimedTask, ...]` already gives callers a domain operation.
Its implementation still spells out a textual function call, bind dictionary and mapping-key
reconstruction (`semantic/operations.py:280–320` at the review baseline). Selected physical columns
and companion returns already have generated `TypedColumns`; this does not establish complete
parameter/result typing. Preserve these foundations and extend their continuity.

Ordinary application, orchestration, serving and CLI/MCP callers receive named domain operations.
They do not resolve physical relation names, build SQL bindings or interpret raw result keys.
Specialized behavior stays in ordinary typed functions behind its owned contract. Generate only
mechanical structural/binding code; do not duplicate an algorithm in an editable schema or expose
a generic `execute(operation_name, dict)` façade.

## UM-03 — One definition to callable, bind and result

For each maintained operation, resolve a complete contract from effective semantic concepts and its
trusted implementation binding: named parameters, semantic value types/codecs, requiredness,
nullability, result fields/cardinality, relevant outcome dimensions, dependencies and effect owner.
Where current declarations identify concepts but not concrete parameter/result correspondence,
extend the owned declaration with that mapping before generating code. Refer to existing model
properties rather than independently declaring the same field type.

Generate static Python request/result declarations or explicit callable signatures, a typed native
function/selectable invocation, its private parameter materialization and result constructor from
that resolved product. Semantic identifiers remain distinct where confusing them changes behavior;
a common `str` or `int` encoding does not establish interchangeability. Preserve strict runtime
validation where external/dynamic input enters, and catalog/actual-result checks before relying on
native return compatibility. A generated annotation or cast cannot establish those properties.

Use explicit positional selections and generated positional materializers for known fixed results.
Generate `__row_pos__` when whole-table selectable result typing is required. Keep genuinely dynamic
extension records within a declared checked boundary; unknown structure must not silently leak as
`Any` through a supposedly fixed domain API. A mapped native result can use runtime validation at
one external boundary, but must have a concrete typed result immediately afterward.

Cardinality is part of each operation: scalar/optional scalar/ordered collection and paged stream
are not interchangeable. No returned row means the operation's declared absence/outcome, never an
implicit cast or a guessed empty successful result. Preserve ordering only where promised and
explicitly expressed in the implementation. Native guarded effects remain in their caller-owned
transaction; generated adapters must neither commit nor choose retry independently.

## Library functionality and why it is selected

| Selected mechanism | Composition and material limit |
|---|---|
| Pydantic 2.14.1 `create_model`, `Annotated`, `Field`, discriminated unions, `model_rebuild`, reusable `TypeAdapter` | Existing effective model generation supplies strict construction and validation. Reuse prepared model/field adapters rather than reconstructing per item; field metadata and relevant finite-value policy must survive extraction. Python and JSON modes differ. |
| Existing `MISSING`, `model_fields_set`, `model_dump(exclude_unset=True)` | Preserve omitted versus supplied fields in boundary/serialization products. Custom serializers, aliases, computed fields, tuples, Decimal/date values and subclass behavior constrain equivalence. |
| SQLAlchemy 2.1.6 `TypedColumns`, `Named`, `with_cols`, typed selects and scalar/table-valued functions | Derive implementation surfaces from the same effective fields. `with_cols` returns the object without runtime validation; `GenericFunction[T]` principally types a return, not domain arguments. |
| Explicit typed projection and result materializer | Avoid relying on `RowMapping`, whose values are `Any`, or general execution parameter mappings as static proof. Emit `__row_pos__` where necessary; retain the existing narrow column protocols that reject unknown attributes. |
| Existing compiled reference-position visitor | Preserve class/fact reference kinds, paths, duplicate occurrences and declared keyed-collision behavior. Mechanical serialization must not replace reference rewriting or invent a new walker. |

Evidence routes: [boundary applicability](../../library_leverage/libraries/unified-model-boundaries_2026-11-01.md),
[PostgreSQL applicability](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md),
[SQLAlchemy 2.1 typing](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html), and
[Pydantic 2.14.1 models](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/models.md).
Installed review evidence includes `sqlalchemy/sql/selectable.py:671–677`, `engine/base.py:1402–1417`,
`engine/row.py:331–361` and `_annotated_cols.py:157–176`. It is Interface-checked, not a generated
callable test result. Pydantic guide addenda for later patches are separate candidate realizations.

## Delivery sequence and consumers

First derive one complete operation seam: protected task claiming with fixed result and held-progress
variant, using the existing `ClaimedTask` semantics. Include wrong-release/config/holder cases, not
just successful SQL execution. This establishes signature/native/result generation and validation.
The companion projection/export seam then exercises ordered multi-row/Arrow correspondence.

These first seams are representative acceptance controls, not the total migration boundary. Before
closing UM-03, inventory and migrate maintained domain-operation callers in orchestration, serving,
intervention, evaluation and CLI/MCP. Bind each fixed shape to the generated contract or record an
explicitly supported dynamic extension boundary. Retire replaced manual parameter/row mappings in
the same consumer slice. Do not leave both as writable definitions or wait for a final cleanup phase
to connect an already changed public operation.

UM-03 can begin with existing stable contracts. The early error/projection products from
[semantic contracts](semantic-contracts-and-policies.md) unlock affected operations; actual native
support and generated relational implementations arrive through the corresponding companions.
The root coordinates shared model/generator files. Independent caller migrations can proceed once
their actual contracts and implementations work; the whole native document is not a barrier.

### Published document operation continuity

Add source preparation, selected-context reads and rendering to the maintained domain-operation
inventory. Their requests reuse effective product-reference and address/membership definitions;
their generated result contracts describe ordered selected values, source views or retained render
artifacts with explicit absence/failure outcomes. Physical build/revision identifiers remain private
bindings resolved from the selected pin. Do not add them to `PdfProductReference`, logical content
identity or ordinary request JSON. Use the [UM-05 shared binding/projection](relational-implementations-and-projections.md#published-document-consumers)
for parameter correspondence, Core selection and materialization, rather than a second handwritten
schema. Existing generated types are foundations; complete static call generation remains UM-03 work.

Migrate actual source-view/render callers with their adapters, including frame/evaluator consumers.
Rendering must stop choosing the old region relation directly. Preserve caller-owned transactions,
runtime result admission, exact producer pin and operation implementation provenance. A parameter
or result-shape change must propagate to callable, native invocation and materializer together;
negative typing controls include incompatible semantic identifiers and exposed placement fields.
This required integration case supplements task claiming and the four companion families; it does
not replace those existing delivery obligations or make their unrelated work wait for PDF readiness.

## Bounded execution investigations

**UM-I02 — Static continuity.** Run the repository's Pyrefly route against generated positive and
negative call sites: wrong semantic identifier, wrong parameter type/name, missing required field,
incorrect nullable result use, absent column and incompatible result shape. Tests must exercise
real generated callable/type products, not just inspect annotations. A failure changes generator
or adapter design; it does not justify ignores, casts or replacing typed results with mappings.

**UM-I03 — Presence serialization.** Compare the selected existing `_plain`/`_native` behavior with
prepared `model_dump`/`TypeAdapter` output on independently expected omitted/null, aliases,
Decimal/date, tuple/list and nested-reference cases. Replace mechanical dumps only when equivalent;
otherwise retain the small necessary conversion and explain its contract. The reference visitor
remains the shared semantic owner in either outcome.

## Acceptance, preservation and handoff

A model field/parameter/result change updates callable types, Core/native correspondence and result
materialization together. Stale incompatible consumers fail typing/preparation/admission at their
correct boundary; an invalid raw native value fails runtime validation even when Python callers
are typed. Independent expected results must detect a generator that selects or labels the wrong
field. Archive/reload and producing-release semantics remain stable for supported historical reads.

Check the real domain caller and downstream result consumer, including failure reporting. Selected
constructors must preserve result dimensions and structured invariant outcomes from UM-02. A passing
signature fixture does not establish concurrency, native effects or migration completion. Qualified
runtime/provider/native obligations and final acceptance are owned by
[integration](integration-adoption-and-qualification.md). No tests or probes ran during plan authoring.
