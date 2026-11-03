# Generated typed domain operations

> Current execution (2026-11-02): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator. **Created:** 2026-11-01.
**Target:** Implemented/Tested only for the bounded slices below; the current-only transition and nested-ID corrections are integrated; final acceptance remains open. Consumes review [R05](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R05)
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

### Maintained consumer migration inventory

**Execution snapshot, 2026-11-02; implementation inventory, not package qualification.**
The current catalog has 76 generated native fixed-call correspondences and eleven fixed Core
boundaries, including the existing operator instruction capability now named `record_direction`. A bounded AST/source pass identified and
migrated the maintained constant native calls in the families below, plus the finite append versus
snapshot-derived publication branch. Catalog introspection SQL remains an owned native probe;
the two retained generic document-writer helpers are excluded from current approved operation
implementations and refuse current use. The fixed registration/source-custody family now has model-derived Core request/value/result
boundaries. Named selection, replay, hashing and segment traversal algorithms remain ordinary
Python/Core implementations. This inventory does not require every internal DML statement to
become an executor contract. The coordinator owns acceptance.

| Consumer family | Current implementation disposition | Remaining acceptance boundary |
|---|---|---|
| Task/run operations (`semantic/operations.py`) | Generated creation, claiming, completion, held submission, cut, renewal/release, source-artifact and input/run fences. Creation factories retain semantic IDs. | Public task/run/method-configuration identifiers and attempt counters propagate through maintained callers; CutId now survives cut capture/consolidation. Focused public typing and runtime controls passed, while final native/integrated acceptance remains open. |
| Registration and source custody (`operations.py`) | Eleven `backend: core` variants derive strict requests, insert/replay values, fixed physical projections and positional result materializers for method/config registration, original descriptor/artifact reads, document registration and rendition content/build/selection/segments. Physical value kinds and semantic IDs come from field references. Named algorithms and dynamic configuration/content adapters remain. | Actual registration/replay/source-custody controls must cover the final wrappers; old producing archives remain outcome authority, separate from an explicitly selected current projection context. |
| PDF staging/publication (`pdf_staging.py`, `pdf_publication.py`) | Fixed envelopes, scalar/optional/one/many results and bounded companion executemany derive from the catalog. Existing Arrow/profile validation, frozen assembly and transaction/cancellation owners remain. | Actual native producer and publication controls must apply to the final source and current admitted head. |
| Published record and selected-source reads (`pdf_record_reader.py`, `pdf_storage.py`, `serve/selected_source.py`) | Generated bound `prepare_*` statements and per-row materializers retain bounded pages and live cursor scopes. Nine selected Core ports require explicit consumer context; existing byte ports retain producer-archive decoding. Required JSON text and explicit shared decoding preserve transport presence. | Actual selected-document, frame, renderer, byte fidelity and abandonment/cancellation journeys; existing record/profile validators remain the dynamic family authority. |
| Source views and native requests (`source_views.py`, `native_requests.py`) | Generated view/artifact publication, capture and both reused/single view-selection effects carry the same exact publication binding. | Composite native FK and replay negatives, actual current caller journeys and selected-body correspondence. |
| Evaluation, inference and publication (`domain_operations.py`, `inference.py`, `publication.py`, `arrow_publication.py`) | Generated workspace, stage, evaluation and append/derived publication envelopes. Named policy/fixed-point algorithms, checked bulk transfer and caller transactions remain their existing owners. | Actual snapshot/revision/refusal and publication replay controls; fixed Core registration/source custody is separately listed below the task family; named inference/policy algorithms retain their checked extension boundaries. |
| Release/runtime/admission (`releases.py`, `runtime.py`, `authored_sql.py`, `contracts.py`, `execution_admission.py`) | Generated archive/activation/selection/SQL admission calls and finite bootstrap principal/release/operation helpers. Runtime purpose derives from the model; maintenance remains an explicit separate route. | Helper success is not whole-release admission. Preserve native capability checks and strict archived meaning without re-executing archived Python. |
| Other current entrypoints | Project initialization, finalization locking, original PDF retention and run-bound authored directions use their named generated envelopes. Direction remains provenance, not a model assertion or a global/admission operation. | Direction's new honest model/native support binding requires its forward native successor and actual positive/negative caller controls. |

The checked extension boundaries already include prepared class/property adapters, declared PDF
record/payload profiles, captured/candidate analytical inputs and selected query output contracts.
Those mechanisms preserve dynamic content; they do not by themselves close a wrapper's fixed
native arguments or result materialization. Pure conversion, comparison, source projection and
analysis remain named typed implementations with model-derived boundaries; a universal SQL or
algorithm language is not required. Reconcile remaining concrete callers before claiming UM-03
or UM-14 complete, including public CLI/MCP and internal rollback/cancellation paths.

### Fixed Core protocol and archived readers

Execution compiler23 records the finite `native` versus `core` backend distinction in each call.
Closed20–22 readers default absent backend metadata to native and reject an explicit backend field;
original bytes are not rewritten or readmitted against the current catalog. The Core branch emits
no SQL executor or native-function identity. Trusted implementation symbols identify the existing
named owner. The same physical fields derive requests, insert/replay values, typed column classes,
closed column protocols, projections and positional materializers. `Table.with_cols` retains known
column types but still allows unknown attributes through its dynamic collection fallback; the
compiler-derived closed protocol supplies the missing static-name boundary. Its narrowing is at
that compiler boundary, not a claim that an arbitrary runtime table has been checked. Existing
physical-model/native admission still owns installed relation compatibility. Nullable JSON-to-text
CAST has one narrow generic adjustment because SQL CAST preserves SQL NULL while SQLAlchemy's
Text expression type drops the nullable generic. Native/Core scalar TypeAdapters are prepared once
at generated module lifetime.

`read_original` and `read_rendition` preserve their producing `prepared` argument as outcome authority.
Their distinct optional `projection_context` selects current fixed-call admission. An unselected
projection uses the explicit base fixed physical protocol with strict generated results and the
existing original-byte hash or `RenditionContent` validation. No installed release is inferred, and
a supplied incompatible current context is never conditionally skipped. Published PDF custody now
also has a fixed optional `read_pdf_published_validation` receipt projection: its three exact-pin
inputs and six existing `PdfBuildValidation` fields derive from the model. It transports the original
projection/native-validation receipt unchanged, including a supported historical native contract;
it does not substitute a PDF schema source digest or recompute a current validation epoch. Its
forward native helper and actual producer-guard integration are qualified separately. Current writes use their
selected `prepared` context. Compiler23's nullable rendition-build `text_layout=None` means SQL
NULL through the generated insert helper and `SQL_NULL` in decoded replay comparisons. Literal
JSON null remains a separate stored JSON value; the previous ad-hoc JSONB bind had encoded Python
None as JSON null. This versioned presence choice does not reinterpret historical unadmitted
producer writes, and historical reads retain their own outcome/profile context. Dynamic method configuration and rendition tree/content adapters
remain checked domain extension boundaries; they are not duplicated in the catalog.

Focused evidence on 2026-11-02: `build/um03-core-contract-controls-00004.log` passed 76 controls on the final generated
closed-column surface;
`build/um03-core-static-negative-00002.log` passed the real Pyrefly positive/negative call-site
control, including wrong IDs and an absent Core column. The initial with_cols-only negative failed
and remains in `build/um03-core-static-negative-00001.log`. Whole warning-inclusive Pyrefly passed
with no errors in `build/um03-core-integration-types-00004.log`; scoped Ruff passed in
`build/um03-core-lint-00003.log`. Earlier identifier controls passed 87 focused cases in
`build/um03-public-id-controls-00001.log`. These overlapping, bounded receipts are not a sum or
whole-package qualification. Final current-forward-native and assembled consumer acceptance remain open.

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

**UM-I03 disposition — tested 2026-11-02:** the small semantic `_plain`/`_native` visitors remain
necessary. Pydantic2.14.1 `model_dump(mode="python", exclude_unset=True, by_alias=False,
serialize_as_any=True, exclude_computed_fields=True)` preserves supplied native values, Decimal
scale, dates, nested subtype fields and tuple collections for ordinary prepared models. The
semantic list projection still intentionally converts tuples to lists; the native/reference
projection preserves them. A general dump also invokes presentation serializers, which can turn
a Decimal into display text; computed fields are not semantic supplied members. The visitors
therefore continue to read supplied values, and reference rewriting stays under the existing
compiled-position visitor. Two independent expected-value controls passed in
`build/test-receipts/um03-presence-lowering-00001.jsonl`, including omitted/null, aliases,
Decimal/date, tuples, nested reference text, subtype fields and presentation differences.
This retains semantic conversion with a specific reason. At the authored `SourceObject` wire
boundary, its released adapter's `model_dump(mode="json")` is selected explicitly, converting
its owned tuple containers for strict JSON transport.

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

## Completion audit — 2026-11-02

**Baseline:** `fb84eb8f`; independent source/consumer and library-mechanism inspection, with no new
product tests, provider runs or database mutations. The coordinator owns all current disposition.

Generated semantic identifiers, nested completion IDs, typed arguments/Core binds and strict scalar/JSON result materializers reach ordinary operations. The former generated-provenance/nested-ID gaps are corrected by source inspection and retained scoped evidence. Closed-column protocols do not replace runtime validation. No new material UM-03 implementation gap was confirmed; full consumer qualification remains at UM-CA10.

See the [coordinator audit](../unified-domain-model_2026-11-01.md#completion-audit--2026-11-02)
for combined judgment, UM-CA evidence and remaining obligations. Library tables above retain their
accepted mechanisms and limits. New improvement proposals are separately published and unadopted.

## Test-architecture reconciliation — 2026-11-02

**Selected amendment:** Current implementation and qualification are owned by the coordinator.
TA foundations retain their declared scope; their completion does not itself qualify UM.

Use the actual TA preparation and reference foundations described in [I02/I03](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md#I02).
Production constructors may supply valid setup, but wrong parameter/result/semantic-ID cases
must exercise generated callable products and retain independent expected values. Add one
materially distinct cold semantic-2 operation/projection product case where the semantic-1
cold example does not exercise it. Keep positive and negative Pyrefly cases, actual malformed
server-result admission, and exact object/presence/nested-reference semantics complementary.

New object-query lowering uses the shared semantic projection rather than another serializer;
[I05](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md#I05) requires its answer-affecting bytes in query custody. Reuse current preparation,
materializers and model-owned codecs; do not add a test-only schema, walker or generic dispatcher.

[Review I07](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md#I07)
selects UM-TA04: annotate the shared operation/agent/domain/reference scenario resource and
identity/result ports using existing Engine/Path/PreparedRelease/RunId/TaskId/CutId types and
small ordinary results. Follow their actual consumer imports in the same slice. Focused negative
type cases must catch exchanged IDs/resources; valid scenarios still use production operations,
and raw malformed cases still reach their intended validator/native boundary. This is a bounded
consumer migration, not another fixture schema or mandatory typing of every test dictionary.
