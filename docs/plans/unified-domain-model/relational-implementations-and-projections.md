# Relational implementations and projection analysis

> Current execution (2026-11-02): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator. **Created:** 2026-11-01.
**Target:** Implemented for the selected scope; Tested only within recorded checks. The [coordinator](../unified-domain-model_2026-11-01.md) owns package state,
source disposition and the execution queue. This companion owns UM-05 and UM-08 design.
**Basis:** integrated review at `370f0643`, [R06/R08](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md),
and [PostgreSQL applicability](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md).
RC01–RC03 were accepted on 2026-11-01; RC04 was rejected. Existing plans are unchanged.
**Additional input:** the [SQLGlot Advanced Capabilities Addendum](../../libraries/postgresql/sqlglot.md#sqlglot--advanced-capabilities-addendum),
lines 1121–2724 as supplied on 2026-11-01, was read in full after the principal review. The
assessment below extends UM-08 and its consumers without changing Core's execution ownership.

## Outcome and foundation assessment

Ordinary callers request named domain operations. Their implementations construct relational
operations from authoritative model references and typed values; callers do not author SQL,
physical relation names or bind dictionaries. SQLAlchemy Core is the primary executable
relational representation. SQLGlot supplies prepared projection analysis for a concrete consumer,
not a second writable model or a mandatory execution hop.

**Implemented source baseline, inspected at `370f0643`:** shared physical metadata already
comes from LinkML; `schema/relational.py:906–977` emits selected `TypedColumns`/Protocol surfaces.
`semantic/companion_projection.py:117–178` derives return columns, Arrow fields, keys and Core
function selections, but obtains expression meaning independently from `cp:sql`.
`semantic/companion_projection_native.py:53–84` adds handwritten joins/casts/function bodies.
`semantic/inference.py:59–160` combines Core rule conclusions with textual seed/update statements.
Source paths here are relative to `python/corpus-structure/src/corpus_structure/`.

These are reuse foundations, not complete typed or SQL-free execution. Projection/native seams
describe the inspected snapshot while the concurrent PDF series continues. A later discrete
update will reconcile that series' changes; this plan does not absorb its completion or chase
ongoing edits. Existing historical qualification does not qualify these proposed replacements.

## Selected projection contract

Use one finite, model-owned projection recipe for current companion families: `input`, `relation`,
`coverage` and `mapping_report`. Each field identifies its semantic/physical source, output role,
requiredness and exact representation. Expression operations cover resolved fields, declared
operation parameters, constants, JSON paths, casts, conditional selection and admitted helper
calls. Joins identify endpoint roles, keys, multiplicity and preserved universe explicitly.

Resolve all references against the effective model/native signatures before publishing prepared
products. A missing input, ambiguous join, undeclared helper or unsupported coercion is a located
preparation refusal; it is not repaired with inferred strings or an arbitrary SQL escape.
Keep declared routine parameters distinct from driver placeholders. LinkML remains the semantic
owner; the expression recipe describes the application operation, not a general SQL language.

The same resolved recipe produces Core statements, generated result/parameter shapes and Arrow
schemas, plus the SQLGlot analysis tree. Core and SQLGlot are derived realizations, never two
independently edited definitions. Typed transformation functions remain ordinary application
implementation where forcing algorithms into declarations would add machinery.

Preserve three separate states when the operation distinguishes them: absent field, JSON null
and SQL NULL. Preserve lexical numeric meaning, exact versus bounded projections, qualified
relationship identity, parallel occurrences, ordering, provenance, source pin and completeness.
Cast success is not evidence that a stronger domain assertion is valid.

## Published document consumers

**Additional required UM-05/03 integration case; Proposed, reconciled 2026-11-01.** Extend the
selected projection contract beyond the initial four companion families to source-view preparation,
selected native context and render-region selection/persistence. The [coordinator reconciliation](../unified-domain-model_2026-11-01.md#pdf-consumer-reconciliation)
records the current failure and ownership boundary. UM-02 owns the invariant's meaning; this
section is the single technical owner of its physical binding and section projection.

Resolve the existing `PdfProductReference` `(task_id, product_key, content_digest)` to the exact
published row. Its build/revision is an internal placement binding, not a new public product
identity. Use model-owned `native_build_id` and `native_revision_id` on the consuming source-view
and rendered-artifact records, with the current representation's equality constraint. Declare a
UNIQUE key on published revision `(build_id, task_id, product_key, logical_digest)` and one composite
consumer FK to that key. Independent product and build FKs would permit a mismatched pair.
Reference section addresses through `(native_build_id, native_revision_id, section_pointer)` to
record access `(product_id, revision_id, pointer)`; rendered regions additionally bind `region_index`
to the corresponding record-region key. The semantic product-pin FK remains useful but cannot
replace this joint publication/address binding. Published read joins must include the revision
binding, not assume equality from today's writer. Preserve original/raw archives and frozen history;
no compatibility rows, duplicate native JSON or additional identity registry are required.

Derive read joins and effect-side correspondence from this same resolved relationship binding.
The domain reader resolves the placement from the exact pin; native publication resolves/checks it
independently under its existing transaction/owner fences. Callers cannot supply an unrelated build.
Read projection typing alone cannot establish that an insert's FK references the same authority.
This case consumes a working PDF publication/read foundation; it does not give UM ownership of PDF
deployment, current-book acceptance or provider/default adoption.

For section preparation, declare pin, direct/descendant membership, body order, ancestors,
evidence coordinates, selected native values, health and output cardinality once. Use existing
published-item/context ports and set-based Core selection for the semantically sufficient closure,
including required ancestors. A shared typed constructor projects text and rich cells/charts,
inline content and synthetic separators with the existing evidence/health semantics. Keep that
specialized algorithm in ordinary code behind its bound implementation contract. Do not construct
a fake partial DoclingDocument, hydrate the whole book merely to prepare selected sections, or
perform one item query per pointer. Explicit full-native exports and necessary global native
validation retain their own complete-document contracts.

Use LinkML effective field/relationship resolution, SQLAlchemy Core `select`/`join`/`cte` and
explicit ordering, and prepared Pydantic adapters under UM-03. Emit grouped
[`ForeignKeyConstraint`](https://docs.sqlalchemy.org/en/20/core/constraints.html#defining-foreign-keys),
`UniqueConstraint` and `CheckConstraint` through existing shared metadata/DDL generation. The cited
Core contract establishes composite pairing; execution still reconciles the selected installed
version under UM-00. Existing native descriptors already represent FK targets/ordered columns;
reuse their admission route and verify the changed consumer relations. SQLGlot output lineage is
not proof of FK correctness, publication visibility or native guard behavior. UM-12 combines
declared relationship dependencies with qualified query analysis and retains unknown coverage.

Delivery includes source preparation, selected-frame capture, rendering's current published-region
reader, artifact persistence, inserts with explicit fields and replay of the same resolved binding.
Downstream reference/evaluation links must consume those actual source views. Consume applicable
PDF repairs if they land first; inspect their actual contracts instead of implementing a parallel
route. Required independent controls are owned by [UM-14/15](integration-adoption-and-qualification.md#published-document-consumer-acceptance).

**Implemented, 2026-11-02; qualification follows the owning coordinator.** Ancillary cell,
derivation and unresolved-inline reports retain their original byte-owned companion fields;
arbitrary strings never pass through PostgreSQL JSONB reconstruction. Single-pointer cell and
derivation reads use the existing exact kind/pointer byte selector. Inline selection, and bulk
selection of a known diagnostic family, stream that family once per reader in bounded pages,
retaining only pointer-to-local-id references and ordering plus an LRU of at most 256 decoded
reports. Inline matches include the exact published item's ancestor closure. The retained index
grows with diagnostic address references, while report bodies stay in their original streams;
neither a whole native document nor a whole family of decoded bodies is retained. The reader's
existing connection, snapshot and cancellation lifetime still owns every read. An absent retained
diagnostic profile is unavailable, distinct from an assessed empty match. Original prose addresses
remain qualified by the product's structural input pin.
Candidate-basis presentation reads only the selected page/candidates Arrow columns using IPC
field projection, after immutable artifact-byte verification and complete schema-header checks.
It extracts basis scalars without decoding OCR regions or revalidating the admitted whole page;
response decoration leaves cached original report bodies unchanged.

**UM-14 current document API retirement, Implemented Python boundary, 2026-11-02.** Terminal
`UnitResult.native_products` / `integrated_products` and generic context document retainers are
removed. Current document producers publish through owned record ports before terminal completion;
recognition observations retain a separate observation-only publication port. Historical document
reads remain explicit. Organized record adoption uses the selected constructor; only its typed
`NoQualifiedSections` signal permits the already-declared global organization recovery phase.

The former aggregate-writer projection negatives in `test_native_documents.py` now map to current
record controls, rather than repeatedly testing an already-removed argument:

| Former aggregate-writer input | Current independent control/disposition |
|---|---|
| Missing item projection | `test_native_projection_refuses_independent_deviation`: delete a `kb.pdf_record_access` occurrence. |
| Missing regions | The same current control: delete `kb.pdf_record_region` rows. |
| Forged ordinal | The same current control: independently change the selected access ordinal. |
| Forged content layer | The same current control: independently change `content_layer` to `forged-layer`. |

`test_native_documents.py` retains one explicit retired-terminal-argument refusal, original
schema/null rejection, record publication before later preparation failure, and independent pinned
text/region expectations. Current immutable replay and attempt custody remain covered by
`test_freeze_prepare_validate_seal_and_replay`,
`test_private_typed_copy_exact_replay_and_changed_duplicate` and
`test_reclaimed_attempt_requires_explicit_resume_and_preserves_progress`. These are scoped control
owners, not a claim that the enclosing plan is qualified.

Current inline/OCR publication controls in `test_pdf_inline_reports.py` and
`test_pdf_ocr_contracts.py` submit independent invalid candidate, scope, raster transform,
word-address and incomplete-inventory inputs through real record staging and final validation.
`test_source_views.py` retains the independent complete-cell negative; the existing released
metadata validator now rejects unresolved classifications, failed math recognition and missing
meaningful-cell assessments within the declared direct/descendant scope.
The current `test_pdf_integrated.py` fixture uses the production record draft publisher and the
observation-only retainer, carrying actual sealed logical pins into lineage and read assertions.
Its direct malformed companion cases still reach current record admission; removed aggregate-body
arguments are not a second current document API. Artifact paging now derives custody from an
actual retained observation response input. The explicit `semantic_0055` historical read/migration
control remains separate. These migrated native cases await the coordinated forward-head run.

The record-backed read identity path checks the producer's retained release, native schema and
supported `read_pdf_product` binding before exposing its version-2 descriptor. Its product contract
is the immutable native projection-validation receipt identity, distinct from the PDF schema-source
digest. The protected receipt read links the exact publication, build, frozen and logical digests,
passed native callbacks and original native validation contract. It never recomputes an old
publication's validation epoch through installed functions. Older producer archives need not
declare the newly added receipt-read call: this bounded metadata read follows the producer read
fence without relabelling its archive as the current consumer. Selected
projections continue to use their separate consumer release. Helper implementation byte changes
do not redefine the stored read ABI. Generated statement constructors and per-row materializers
now own the fixed byte-envelope calls; the reader retains bounded pages, live cursor batch sizes,
borrower cancellation and result closure, without eagerly materializing a streamed family.

Published item/region reads dispatch to the exact record port before the legacy selected-product
header and installed-schema digest gate. They share the producer identity/read-ABI authority and
verify retained schema bytes, digest and supported mapping before projection. Schema custody or
profile failure in that bound route refuses explicitly; it does not fall through to legacy reads.
The installed digest qualification remains only on the historical aggregate route. Contrary
controls use differently serialized retained schema bytes with the same supported schema meaning:
both published ports succeed despite the different installed hash, while missing artifacts,
changed bytes and unsupported schema shape refuse before projection.

**Exact occurrence and cell detail, Implemented, 2026-11-02; bounded native acceptance and remaining obligations are assessed below.**
An explicit occurrence read and its trace use the indexed protected endpoint selector for that
occurrence ID. Relationship selection also checks the complete normalized target product pin;
another product's equal local ID is not a relationship to the selected occurrence. Exact relation
and input byte reads compose the resulting context under the existing aggregate row budget.
Only named scoped coverage/mapping metadata families use their existing metadata context port;
the implementation does not obtain and postfilter table-wide occurrence or relation bodies.
The first wrapper implementation filtered outside the protected SQL context function, which
could still decode unrelated bodies inside that function. PostgreSQL 18 refuses SRF inlining
for `SECURITY DEFINER`/configured functions ([planner source](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/optimizer/util/clauses.c#L4905-L4913));
outer filtering cannot establish the required avoidance. The corrected renderer reuses the
same marked SQL selector inside the existing paginated function and materializes the requested
family/continuation/limit page before calling the body decoder. Function identities and the
public eight-argument ABI stay unchanged. The concrete isolated PostgreSQL decoder-instrumentation
control `test_context_family_filter_precedes_unrelated_body_decoding` **passed**: the selected
coverage read skipped a live unrelated-body decoder branch. This is component SQL evidence;
the coordinated forward-head publication/admission batch remains pending.
An explicit cell detail demand resolves its nested table/chart cell record address and decodes
that value through the byte reader, without hydrating the table or document. Its decoder retrieves
the retained schema artifact, verifies its SHA-256 against the revision and producing archive,
and prepares the explicitly supported schema mapping; it does not substitute installed schema
bytes when retained custody is absent or incompatible. Version-2 descriptors read the bounded
native/assessment health inventory through byte fields. Missing assessment stays missing and
ambiguous health refuses; conversion success never fabricates source-fidelity assessment.

The maintained integrated fixture now checks full native state with schema-owned computed fields
excluded, and separately checks independent item fields, exact region inventory, occurrence IDs,
the cell value and original cell box, and both observation/input product pins. Its observation
callback control feeds retained request files through `_retain_page`, archived `BoundReader`
preparation and the real observation-only retainer, without invoking a provider. Current JSON
publication controls distinguish strict envelope preparation from actual per-record native
admission; no current aggregate document writer is restored for those tests. Explicit historical
read/migration and retained descriptor witnesses remain separate.

Scoped receipts below are component evidence, not additive counts or assembled qualification.
The coordinated forward-head batch still owns current publication/read acceptance.

| Receipt under `build/test-receipts/` | Outcome and scope, 2026-11-02 |
|---|---|
| `um05-projected-candidate-cell-controls-attempt-00002.jsonl` | passed: 40 database-free Arrow projection, diagnostic and complete-cell controls. |
| `um05-fixed-byte-reader-lifetime-attempt-00001.jsonl` | passed: 20 database-free byte-reader and cancellation/lifetime controls. |
| `um05-fixed-native-event-cursor-attempt-00001.jsonl` | passed: 2 actual PostgreSQL small/large native export cursor controls; no release admission or forward replay. |
| `um14-integrated-prepared-controls-attempt-00001.jsonl` | passed: 27 database-free prepared integration/observation controls. |
| `um14-record-reader-producer-profile-attempt-00002.jsonl` | passed: 11 database-free producer ABI/custody and diagnostic controls. |
| `um14-record-descriptor-health-attempt-00001.jsonl` | passed: 3 database-free missing/present/ambiguous health controls. |
| `um05-exact-occurrence-reader-controls-attempt-00001.jsonl` | passed: 35 database-free exact relationship, reader and lifetime controls. |
| `um05-exact-cell-byte-detail-attempt-00003.jsonl` | passed: 2 database-free exact cell/foreign-ID and real record-codec detail controls, including NUL/Unicode preservation. |
| `um05-context-family-before-decode-attempt-00001.jsonl` | passed: 1 actual isolated PostgreSQL family-before-decode control with unchanged rows and an instrumented decoder; no head replay or release admission. |
| `um14-native-retained-schema-route-attempt-00002.jsonl` | passed: 21 database-free diagnostic/profile controls, including both published ports with supported different-hash retained schema and missing/changed/unsupported schema refusals. |
| `um87-callback-authority-00002.jsonl` | failed: 82 passed / 1 failed across frozen meaning, receipt/profile and prepared integration controls; the policy-only fixture lacked newly required selected input/container meaning. |
| `um87-callback-policy-00004.jsonl` | passed: corrected policy-only fixture exercises full frozen callback validation while retaining its captured-policy and invalid runtime metadata assertions. |
| `um87-optional-supports-00001.jsonl` | passed: 19 database-free frozen meaning controls, including raw disk bodies with omitted/empty supports accepted for partial coverage, explicit null refused, and omitted supports still insufficient for integrated complete coverage. Retained bodies are unchanged by validation. |
| `um90-native-consumer-endpoint-00003.jsonl` | passed: 48 database-free candidate-capture, published diagnostic/header and source CLI controls. Candidate cases prepare real composed models and retain producer schema/receipt meanings; shared semantic admission is not patched out. |
| `um90-cli-catalog-public-marker-00004.jsonl` | passed: 2 final CLI catalog controls after replacing the private publication-table discriminator with the existing public-view payload-null discriminator; no body bytes are transferred. |

**Implemented; current native83–90 rehearsal evidence is scoped separately, 2026-11-02:** the frozen callback now captures
input, occurrence, relationship, coverage and mapping-report families in existing bounded pages.
Repeatable disk-backed views invoke the same local integrated-product validator as envelope
preparation. It enforces occurrence identity/kind/precision/native spelling and geometry, the
complete item/cell address universe, relationship endpoints and governing decisions, and local
coverage declarations. Only compact identity/address summaries and a bounded indexed-input cache
survive scans; decoded occurrence/relationship families are never collected as tuples. Declared
large occurrence text is reconstructed from checked byte fields and retains NUL/Unicode spelling.
External input pins, occurrence custody and cross-product coverage support remain independent
native guard obligations. The expanded native support control separately requires exact support
scope/family, rejects partial-only evidence for integrated complete coverage, and accepts native
complete seeds plus mixed/weaker supported assessments under the existing rule.

The coordinated86 consumer batch failed16 / passed40 / deselected2
(`um86-integrated-consumers-00001/reportlog.jsonl`), exposing the wrong read-contract authority,
missing frozen local-meaning callback and cross-product support enforcement. Those results do not
establish current closure. The corrected source has scoped warning-inclusive Pyrefly0 and Ruff0
(`build/um87-callback-types-00002.log`, `build/um87-callback-lint-00003.log`); the coordinated87
publication/read run is still required. Failed callback-policy attempts00002/00003 remain retained.

**Implemented; current native acceptance has bounded evidence, 2026-11-02:** the strict inline-report SQL observer
subsequently exposed an actual unconditional legacy runtime-table join in source inspection.
Published header routing now resolves the exact record pin first and reads at most three health
rows and two requested runtime reports through existing byte ports. Missing/ambiguous native
health refuses; missing runtime metadata stays absent. Only the separately qualified historical
route reads the legacy runtime relation. The native-products CLI keeps set-shaped catalog/pin
selection, distinguishes the public view's required historical aggregate payload from its null
record payload without transferring either body, and reuses the same bounded metadata reader.
It batches legacy runtime lookup only for historical keys. Existing byte ports are single-pin;
catalog metadata therefore uses bounded reads per published product, with no per-occurrence or
whole-document hydration and no new cross-pin query capability or private-table ACL widening.
The current strict observer remains unchanged; its affected native rerun belongs to the next
coordinated product batch. The latest scoped five-file Pyrefly/Ruff checks passed
(`build/um90-native-header-types-00004.log`, `build/um90-native-header-lint-00004.log`).

Failed/interrupted predecessors remain retained. Projection attempt 1 lacked a report log; its
command/failure summary is retained as `um05-projected-candidate-cell-controls-attempt-00001.log`
and the traceback remains in the tool transcript. Producer-profile attempt 1 and cell-detail
attempts 1/2 exposed fixture schema/alias errors and remain alongside the corrected results.

## Library realization and conditions

| Mechanism | Role and why selected | Material condition / evidence |
|---|---|---|
| LinkML `SchemaView.class_induced_slots` / `induced_slot` | Resolve effective output and referenced property definitions once. | Preserve closed import resolution and contextual constraints; a raw YAML name is not a checked reference. [LinkML runtime guide](../../libraries/data_model/linkml.md), effective-resolution sections. |
| SQLAlchemy 2.1.6 `select`, typed columns, joins, `cte`, `lateral`, `case`, `cast`, typed JSON access, `func` / `GenericFunction[T]` | Construct reusable relational implementations with optimizer-visible set intent. | Helper return typing does not supply a static domain argument signature; UM-03 owns that boundary. |
| `Insert.from_select`, PostgreSQL conflict DML, correlated update/delete, ordered aggregates | Replace inference seed/update and scoped mutation fragments without hydrating/reinserting rows. | Preserve conflicts, qualification context, order and NULL behavior; `DO NOTHING` is not a conflict validator. |
| `TypedColumns`, narrow column Protocols, explicit positional projections / `__row_pos__` where needed | Generate static consumer surfaces from the same fields. | `with_cols` performs no runtime validation; `RowMapping` values are `Any`; runtime result validation remains required. |
| SQLGlot candidate 30.27.0 `exp` constructors and `MappingSchema` | Build analysis expressions and schema/UDF metadata from the resolved projection. | No handwritten parallel catalog; runtime AST typing is not static Python/domain typing. |
| `qualify(..., dialect="postgres", validate_qualify_columns=True)`, scopes, `annotate_types`, `lineage` | Validate supported references, report known output types and model-identified dependencies. | Strict qualification precedes lineage: its default internal pass disables column validation. Unknown types/functions remain explicit. |
| `exp.DataType` / `DType`, `build_scope`, `find_tables` and model-bound source expansion | Preserve nested/parameterized type descriptions and analyze output-value versus relational dependencies across supported definitions. | Derived from the same admitted signatures; unresolved UDT names are not PostgreSQL overload or domain validation. Expansion/coverage conditions below apply. |

Detailed versions and exact installed/tagged interfaces are retained in the applicability account.
Primary SQLAlchemy evidence: [2.1 typed Core](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).
Exact SQLGlot evidence: [builders](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/builders.py),
[qualification](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/qualify.py),
[type annotation](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/annotate_types.py)
and [lineage](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/lineage.py).
Execution must verify the exact selected SQLGlot release before pinning; no dependency was added
by creating this plan. Routine dependency movement follows the existing exact-pin policy.

## UM-05 — Model-bound relational implementations

**Inputs:** current effective definitions and physical metadata; UM-01 comparison semantics where
used; UM-02 invariant scope for enforcement-sensitive predicates; UM-03 request/result contract.
Initial recipe/lowering work needs those contract slices, not completion of every upstream package.
Actual generated-call integration requires the working UM-03 adapter and required native profile.

Replace `cp:sql` with the finite recipe above, then migrate all four companion-family producers
and consumers. Generate Core expression trees, parameter layouts and output shapes together.
The existing selected-product and lineage universe remains authoritative; preserve guarded pin
selection rather than making a projection query independently decide publication visibility.

Use the same construction discipline for inference workspace seeds and context normalization.
Retain the common qualified fixed point, direct proof materialization and revision fence. The
engine selection remains SQL/PostgreSQL; its maintained query strings are not a required part
of that choice. Pure read statements can integrate before native-body changes; protected wrappers
requiring UM-06/07 remain explicitly unavailable until their admission is working.

Consumers include `companion_projection`, `companion_projection_native`, companion Parquet export,
selected-source products where they share these projections, analytics and inference callers.
Execution must enumerate actual maintained entrypoints before closure; the four families are the
required first vertical migration, not permission to omit other affected callers.

Retire active `cp:sql` parsing and replaced handwritten expression/join fragments after every
maintained consumer uses the replacement. Keep frozen predecessor artifacts byte-exact. Retain
specialized domain algorithms and semantic reference visitors; serialization does not replace them.

**Acceptance:** add a nullable nested JSON property and independently specify absent/null/value
results through Core, native return and Arrow consumer; include an invalid path/type and a join
with parallel endpoints. Verify a changed parameter cannot reuse stale preparation, deterministic
ordering remains, and conflicting inference input is not silently deduplicated. Run meaningful
negative typing cases plus actual query/result checks; checking annotations alone is insufficient.

## UM-08 — Companion projection analysis consumed by semantic impact

**Inputs:** one settled UM-05 companion recipe plus generated schema/native helper metadata.
A single supported family is enough to begin qualification. Delivery covers all supported current
companion recipes and the real O02 impact/diagnostic consumer; it does not depend on unrelated
native generation or every typed operation being migrated.

Prepare SQLGlot analysis once per immutable projection/release product. Resolve aliases, qualified
columns and helper results under PostgreSQL dialect, then expose model-identified output/source
dependencies and known/unknown output type information. O02 consumes this evidence alongside
semantic definitions; it must not describe SQL column lineage as scientific provenance or
complete behavioral impact. Return model/path locations for unresolved analysis to O03.

Use two complementary dependency views. Output lineage describes value derivation; qualified
scope traversal and structural accessors also retain row-selection, join, grouping, ordering and
helper dependencies. A field used only in WHERE can change the result without appearing in an
output's value lineage. Bind each dependency kind to resolved model/operation identities and its
declared coverage; this still does not discover arbitrary Python or native procedure behavior.

Where a supported projection refers to another model-owned query/view definition, reuse
`exp.expand` with a finite, release-pinned source map, rather than writing recursive SQL substitution.
Resolve external sources versus local CTE bindings deliberately; refuse missing required definitions,
cycles in the expanded source graph and ambiguous shadowing. Preserve logical source identity and
do not expand stored/materialized objects as if their execution, authorization and snapshot semantics
were necessarily interchangeable. Expansion is for the qualified analysis profile, not a change to
Core execution. Avoid repeatedly expanding shared definitions or caching many duplicated trees;
an unsupported closure remains explicitly incomplete rather than silently losing dependencies.

Compose required source expansion → strict qualification → type annotation → reusable `build_scope`
→ lineage. For the qualified profile, reuse `lineage(None, ..., scope=...)` with a scope built from
the final strictly qualified tree and uniquely named outputs, rather than repeating qualification
per field. `on_node` / `Node.payload` can attach resolved model identities; convert those results
to the typed dependency product instead of maintaining a parallel lineage graph. These mutable
payloads are annotations, not authority or persistent identity. Model-owned `DataType`/`DType` products preserve relevant
precision/scale, nested fields and helper result types; unknown named types stay unknown. Runtime
overload, collation, nullability, exact-value and transport obligations remain with their owners.

The analysis product identifies model/projection identity, library/version, analysis profile and
coverage. A missing UDF type or unsupported PostgreSQL construct produces an explicit incomplete
result or preparation refusal according to whether that fact is required for admission. Never
accept an inferred UNKNOWN as a satisfied output-type obligation. Unsupported generation uses
strict failure rather than warnings. No optimizer rewrite is adopted merely because available.

Admit only understood structure: inspect for `exp.Command`, unresolved structural placeholders and
opaque/unsupported nodes required by the selected profile. Parser success and strict generation
are insufficient because command fallback can retain unparsed text. Use `exp.Expr` as the common
adapter boundary and narrower `Query`/`Selectable` capabilities only where supported. Construct SQL
predicates with `.eq()`/`.neq()`; Python `==` compares structure. Prepared analysis must not mutate
a shared AST or use mutable expression hashes as persistent compatibility identity. Copy trees for
mutating passes and cache the immutable resolved products/results at their valid release lifetime.

Carry model/member/path origins in programmatic `.meta` and preserve/rebind them across transforms.
Use available SQL positions (`update_positions`) and structural `error_messages()` as diagnostic
inputs, with the model path as the reliable fallback for generated nodes. Neither positions nor
structural validation establish semantic validity. Source comments/directives cannot grant model
authority, supply compatibility identity or bypass completeness checks.

**UM-08-I1:** exercise the actual JSON/cast/CASE/join/helper shapes against exact SQLGlot and
PostgreSQL behavior. Independently specified output/dependency examples settle usable scope.
If a selected construct cannot be analyzed faithfully, preserve the required capability through
an explicit narrower supported projection or revised realization; report the affected obligation
to the coordinator. Do not quietly drop R08 or make a new universal query backend.

**Acceptance:** an added source dependency appears in actual O02 output; an invalid column fails
strict qualification; an unknown function remains unknown; a domain-level policy change without
SQL-column change still appears through the semantic diff owner. Include correlated/aliased
references and JSON null/missing cases relevant to the supported profile. Server acceptance is a
separate check from SQLGlot inference, and neither establishes Python static signature safety.
Also exercise WHERE-only and join-only dependencies, nested model-owned sources, local CTE/source
name collision, a source cycle, missing source, invalid nested type, opaque command, unresolved
placeholder and directive-bearing source. Verify independent expected dependency kinds, located
diagnostics and explicit unknowns through actual O02/O03 consumers; they must survive AST copying.

## Added SQLGlot capabilities: disposition and limits

The addendum's full capability range was assessed against this target on 2026-11-01. Selected
mechanisms above remain Proposed; exact-source inspection is Interface-checked, not server-tested.

| Addendum family | Disposition for this series |
|---|---|
| §1 traits / concrete nodes | Use `Expr` versus `Expression` correctly and capability-specific interfaces; trait membership alone does not establish analysis support. |
| §2 source expansion / table utilities | Select bounded pinned-source composition and `find_tables`/normalization. `replace_tables` needs an actual remapping consumer; never infer object authority from a name. |
| §3 AST templates | Candidate only for a justified structural adapter. `replace_placeholders` is not driver binding and can leave holes; direct constructors remain selected. Replacing `cp:sql` with handwritten templates would retain SQL authorship. |
| §4 structural extraction | Select dependency kinds beyond output lineage, including predicates and joins, consumed by O02. |
| §5 non-query syntax | Consider supported DDL/DML/privilege nodes in UM-06-I2. Keep pglast/catalog ownership; generic command fallback and procedural generation gaps prevent blanket adoption. |
| §6 rich types | Select model-derived nested/parameterized types. `udt=True` does not resolve a PostgreSQL type's semantics. |
| §7 PIVOT/UNPIVOT | No current recipe requires it. Revisit `Pivot.output_columns` for a named pivot consumer; output names alone are not full typing/lineage. |
| §8 expression DSL / identity | Select structured builders and explicit predicates; AST equality/hashing is not persistent domain identity. |
| §9 comments/directives | Use programmatic attribution; no new comment configuration authority. `exp.Anonymous` is an eligible explicit model-owned UDF representation when built-in recognition collides. |
| §10 diagnostics / chaining | Select origin metadata, available positions and structural diagnostics. `assert_is`, `pipe` and `apply` are local conveniences, not new architecture. |
| §11 generator rewrites | No general rewrite pipeline. A named cross-dialect need must justify collection/CTE/aggregate/struct/identifier rewrites and their changed NULL, ordering, temporal or materialization semantics. |
| §12 pipe SQL | No current fit: another authored query language supplies no required domain-contract benefit. |
| §13 temporal utilities | `format_time` requires a real formatting-language translation need; `subsecond_precision` is not exact timestamp normalization. Preserve UM-10 temporal contracts. |
| §14 SQLFrame | Separate library/backend, not SQLGlot's included DataFrame API. No current execution/typing/lifetime benefit justifies another adapter. |
| §15 composition / completeness | Select explicit analysis sequencing and opaque-structure refusal; ordinary transpilation does not automatically qualify or type-check. |

Exact v30.27.0 evidence: [builders and expansion](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/builders.py),
[lineage and scope reuse](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/lineage.py),
[type representations](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/datatypes.py),
[core metadata/diagnostics](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/core.py)
and [parser command fallback](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/parser.py).
The [native companion](native-authoring-and-evolution.md) records the PostgreSQL generation limit.

## Alternatives, execution fit and handoff

A central SQLGlot IR would provide broader shared analysis but require new driver/bind/result/DDL
bridges and still not provide full PL/pgSQL generation. It is not selected. Parsing generated SQL
for a bounded analysis can be useful, but an automatic Core→text→SQLGlot→text→pglast execution
chain is not required. Selective ORM mapping remains eligible only for a named editable aggregate;
immutable releases and bulk processing remain Core-oriented.

Keep prepared shapes independent of invocation values. Apply selective predicates/projections
before transfer when the declared universe permits; retain intermediate nodes needed for closure
and absence claims. Preserve coarse set execution and avoid a Python row loop or physical stage
per semantic field. Benefit claims are qualitative until measured.

UM-05 supplies typed relational products to [native authoring](native-authoring-and-evolution.md)
and UM-03. UM-08 supplies projection evidence to O02/O03. The coordinator owns global current
state and whole-series acceptance. No product verification was run while authoring this document.

## Execution evidence — 2026-11-02

**Tested, bounded inference slice:** `semantic.inference` now constructs seed insertion with
Core `Insert.from_select`, typed table-valued seed columns, qualification `text[]` arguments,
and grouped canonical contexts. Context representative normalization uses Core `UPDATE FROM`
over the grouped minimum; both run set-wise on the existing protected private workspace.
The fixed point, direct proof materialization, scope/qualification semantics, protected workspace
lifetime and revision-fenced publication remain under their existing owners.

`uv run python -m pytest python/corpus-structure/tests/semantic/test_inference.py -q
--report-log=build/test-receipts/um05-inference-00001.jsonl` **passed 13 cases**, including actual
native publication, interacting rules, cycles, canonical contexts, ungrounded proofs and stale
analysis refusal. Scoped Pyrefly and Ruff for `semantic/inference.py` passed. This establishes
that inference slice, not completion of UM-05, UM-08 or assembled qualification. The companion
recipe, publication/read binding and actual impact-consumer work continues under this package.

**Implemented / bounded tested analysis slice:** `projection_analysis` constructs SQLGlot `exp`
nodes directly from the checked recipe; it does not parse a second handwritten query. Strict
`MappingSchema` qualification precedes type annotation, one scope preparation and all-output
lineage. The retained `projection_analysis.json` product records output model origins/types,
physical value dependencies, actual accessed sources, predicate/join/group/order dependencies,
qualified expressions, relationships and model-declared native/export consumers. Helper result
metadata supplies known types; helper bodies remain explicitly unassessed. Model paths survive
without pretending generated expressions have authored SQL source spans.

`projection_analysis_products` receives only explicit retained dependency bytes. Its closed
LinkML import map never borrows installed schema sources; current metadata is reusable only for
an exact supported retained physical identity. Missing or unsupported physical inputs produce an
incomplete product, and old archives without this product remain unknown. A reusable strict
Pydantic `TypeAdapter` reads immutable archived products for UM-12. No archived source is executed.
The source identity and analysis profile are separate from native enforcement and domain meaning.

The focused analysis/report union passed12 cases, followed by four retained-product/impact cases
(`build/test-receipts/um-report-analysis-00003.jsonl`, `um08-retained-impact-00001.jsonl`). These
controls include real four-family recipes, qualified output and relational dependencies, unused
available relations, malformed columns/products, unsupported physical inputs and downstream
impact/unknown preservation. Later expression-product additions have their own affected receipt;
CLI/MCP, native recipe parity and assembled acceptance are still open. No performance benefit or
arbitrary SQL/procedural completeness is claimed.

## Completion audit — 2026-11-02

**Baseline:** `fb84eb8f`; independent source/consumer and library-mechanism inspection, with no new
product tests, provider runs or database mutations. The coordinator owns all current disposition.

Checked recipes actually lower to typed Core binds/JSON/CTE/join/set DML. SQLGlot MappingSchema, strict qualify, annotate_types, reusable scope/lineage and non-output dependencies reach impact analysis. Unknown helper semantics remain unknown. Prior API-use and consumer gaps are corrected; complete semantic equivalence/provenance is not claimed. I05 in the separate review proposes additional known class dependencies without relabelling conservative unknown as a defect.

See the [coordinator audit](../unified-domain-model_2026-11-01.md#completion-audit--2026-11-02)
for combined judgment, UM-CA evidence and remaining obligations. Library tables above retain their
accepted mechanisms and limits. New improvement proposals are separately published and unadopted.

## Test-architecture reconciliation — 2026-11-02

**Target amendment:** Proposed; inspected TA foundations are implemented only within their stated
scope. The coordinator owns state; this section does not close TA or UM qualification.

[Review I06](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md#I06) selects a bounded preparation correction. Captured `libraries.json`
already includes SQLGlot; validate its required producer/runtime tuple before new projection
preparation and before warm cache reuse. Extend the existing determinant owner and relevant
cache keys with analysis runtime identity; incompatible/missing required provenance refuses
with deliberate reacquisition/new-release advice. Supported archived products remain readable
without rerunning or installing their original analyzer. Do not widen every runtime boundary.

Use the existing MappingSchema → strict qualification → type annotation → scope → lineage
composition. A cold composed semantic-2 recipe case must independently expect output types,
value versus WHERE dependencies and exact retained analysis contents, with changed-source and
captured/runtime mismatch controls before warm reuse. Preserve the existing semantic-1 cold
case and read-only archived-analysis paths. This work does not change Core execution ownership,
SQLGlot authority, native enforcement or procedural-generation support.
