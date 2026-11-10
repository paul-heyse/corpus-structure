# Released types and faithful exchange

**Status: CA01 repaired; PTD-01/08 scoped delivery verified; investigations decided · 2026-11-10.** Selected package delivery is Tested at the scope recorded by the coordinator; conditional targets remain Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. The coordinator records execution and native delivery separately from original authoring.

## Basis, foundations and target

Consumes [O01/O02/O08](../../functional_reviews/postgresql-typed-domain_2026-11-09.md). LinkML/released operation definitions remain semantic authority;
SQLAlchemy is derived relational realization and PostgreSQL the instance authority. The existing
[schema renderer](../../../python/corpus-structure/src/corpus_structure/schema/relational.py)
reduces Core columns to python_type, nullable primitives and JsonValue. In contrast,
[operation-call generation](../../../python/corpus-structure/src/corpus_structure/semantic/operation_call_generation.py)
already carries semantic_type-derived IDs and closed members. Extend its existing binding facts
into selected Core/companion surfaces; do not create another independently authored ID vocabulary.
Column.info's enum/pattern/bounds are useful but do not themselves supply every semantic reference.

The initial consumer scope is generated native calls, their read/staging projections, the seven
existing TYPED_RELATIONS and four companion families (input/relation/coverage/mapping_report).
Inventory which of their fields already have authoritative semantic bindings. Leave genuinely
unbound Text/JSON fields generic; do not infer an ID from spelling. Distinguish semantic release,
physical identity, published occurrence and content digest only where their declarations do.

The existing `_operation_ids.py` already supplies ReleaseId, RealizationId, ProjectId, RunId,
TaskId, ProductKey, ContentDigest, CutId, RuntimeId and SourceViewId, among others. Initial bindings
are data.occurrence release/realization in analytics and the companion six-part pins plus producer
release; derive companion family/relation/coverage closed values from cp:source enums. FactId and
OccurrenceId do not yet exist there: add them only through explicit authoritative correspondences
with a selected callable, not from column names. Typed artifact identity must include semantic as
well as physical determinants when it begins consuming semantic bindings.

ValidityInterval can have symbolic/partial Value bounds and unknown inclusivity. A PostgreSQL range
cannot replace that complete released value contract; selected narrower native invariants must not
silently narrow admissible source meaning. Preserve SQL_NULL versus decoded JSON null.

## PTD-01 · Extend one generated typed boundary

**Input:** current bound model/call declarations and compiled physical metadata. **Output:** generated
semantic aliases/closed-value types and selected callable/column/result surfaces derived from the
same facts. Reuse the existing semantic-ID generator and reference projection. Adapt column rendering
to receive explicit bindings in addition to physical types; retain Named/TypedColumns plus narrowed
protocols. Companion materializers consume that same binding source. Preserve nullable literals and
structured released values; patterns and relational constraints remain runtime obligations.

NewType-style annotations have no runtime validation and SQLAlchemy's broad operator API may accept
wrong joins. Acceptance promises consequential call/result checking, not universal static SQL proof.
Choose representative existing distinct call parameters and demonstrate Pyrefly refusal of swapping
them, with a valid corresponding call accepted. Test nullable closed values and a declaration change
through regeneration. If a particular type distinction cannot be checked by the selected API, report
that exact limit rather than add hand-written runtime checking to make the static claim appear true.

Migrate generated call constructors, current selected relational writers/readers and companion
materializers together, replacing duplicate handwritten annotations only where superseded. Generator
outputs keep their complete source/physical/compiler determinants. A static-only change does not
need native schema migration; changed semantic behavior does. The existing model-generation check
and directly affected call/companion tests establish consistency; independent negative type examples
must not merely compare generated text to itself.

## PTD-08 · Faithful companion exchange

**Selected initial consumer:** operator/developer use of the four published companion families in
an independent Arrow/Parquet analysis and offline comparison. Extend current export/compare owners;
no universal importer or new instance store. Preserve PublishedSourcePin's six components, family
keys, logical schema metadata, SQL-null versus JSON-null, original payload/source fields, logical
and file identity and completeness. The existing independent Parquet consumer is the delivery route,
not a new wrapper that simply reads and rewrites the same generated schema.

Trace the selected output direction through the protected PostgreSQL query, ADBC field/schema,
Arrow and Parquet representation. Compare its distinct Python materialization without forcing both
into one schema. This export does not use pgpq. If I01/I05 selects a write/input direction, trace
its native wire/profile obligations separately and retain fresh encoders and complete metadata checks.
Preserve numerical lexical columns, half-even/overflow/change flags and exact hex-float conversion
where an affected analytical path uses them; the initial companion families do not require adding
those projections. Generic safe casts must not silently replace owned normalization.

An independently specified Arrow/Parquet fixture must distinguish SQL/JSON null, empty/missing
nested values, ordered references and the declared integer/double/text/JSON field semantics.
Decimal or other normalization cases become required only if a selected changed direction declares
them; do not invent fields or native types to exercise a transport feature. The consumer verifies pins,
reads all selected families, and compares expected logical content after disconnection. Encoding or
constraint failure leaves no published partial product. Retire only consumer coercions this replaces.
A report of an unresolved mapping is not a silent string/float fallback.

## PTD-I01 · Structured values, adaptation and object editing

Decide each branch: (a) context-free scalar/row conversion, (b) native DOMAIN/enum/composite/range
invariant, (c) private ORM graph editing and associated loaders/UoW. Examine existing call and
companion conversion sites first. If a useful conversion exists, select the smallest released codec
or TypeDecorator with correct coerce_compared_value/cache_ok, or scoped Psycopg adapter/row factory.
Identity/admission/context-dependent interpretation stays an explicit operation. Existing native
vocabulary membership must not become a database enum merely because strings can be enums.

For a justified new native value, specify the whole declaration→construction→wire→native admission→
readback lifecycle, qualified OIDs, child nullability and source spelling. Range canonicalization
must not overwrite original occurrences. Composite dataclasses need construction and make_sequence;
registration does not update existing connections. Consume native lifecycle/session slices only
when selected. Missing OID/layout refuses; do not add a compatibility fallback.

For editing, evaluate a concrete draft semantic graph against imperative mappings/composite/Session
and the current explicit domain-operation route. Prefer explicit operations unless identity map,
cascades and loading simplify the complete workflow. Published products remain immutable. A general
ORM authority change is a rule decision, not permitted by choosing constructor factories.

**Bounded decision evidence:** current consumers, declared value/invariant and composed alternative;
a small round trip only if source contracts leave a consequential doubt. Every branch ends selected
with a PTD-10 delivery slice, retained with reasons, or deferred with a specific consumer/lifecycle
trigger. No obligation to invent an enterprise domain or graph editor to exercise an API.

## PTD-I05 exchange slice · New structured input

Choose a real external structured input only when the intended observation/knowledge owner and
source provenance are identifiable. Prefer existing observation/publication operations; a new file
loader cannot write knowledge directly. If selected, add input schema, exact value/normalization
rules, authenticated provenance, protected staging/publication, independent expected values and
rollback/post-migration readback to PTD-10. If no justified input emerges, close the input branch
with that evidence while delivering the selected companion output workflow above. Spatial, Rust
transport and arrow-json routes receive the same concrete consumer/fidelity decision.

## Pivotal mechanisms and evidence

See [review realization](../../functional_reviews/postgresql-typed-domain/domain-realization.md)
and [exchange](../../functional_reviews/postgresql-typed-domain/analytical-exchange.md).
[SQLAlchemy custom types](https://docs.sqlalchemy.org/en/21/core/custom_types.html),
[Psycopg3.3.6 composites](https://github.com/psycopg/psycopg/blob/3.3.6/psycopg/psycopg/types/composite.py),
[pgpq selected source](https://github.com/adriangb/pgpq/tree/306cdf8cf2b8450a3162a9cd467422cb0849af5a).
Selected versions and precise limitations are inherited from the dated review, reconciled at PTD-00.

## PTD-01 concrete execution mechanisms · 2026-11-09

Use one pure qualified binding resolver for calls, all seven TYPED_RELATIONS and selected companion
projections. Existing semantic_type anchors own nominal names; cp:type_source supplies missing
compatible type correspondences without changing local physical constraints (ADR-0073).
Collect closed aliases across parameters/results/nested records/columns; coverage_family remains
open str, while nullable normalization retains its literal union plus None. Add fixed call
variants for the four existing protected companion batch functions under read_pdf_product,
retaining six-part pins, result ordering and json-text-v1 materialization. Arrow export remains
native JSONB, without Python hydration.

Selected SQLAlchemy2.1.6 Named/TypedColumns/with_cols retain the same Core objects; narrowed
protocols reject unknown names. with_cols performs no runtime validation. NewType is runtime
primitive identity and Pydantic2.14.1 validates its supertype. Real Pyrefly positive/negative
consumers establish nominal checking; existing runtime constraints and SQL_NULL handling remain.
Reference: [selected SQLAlchemy metadata source](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/metadata.rst).

Version typed products with semantic/physical/renderer determinants without injecting their static
identity into companion runtime identities. Preserve current source hashing; annotations can
change existing source IDs. Regenerate affected bindings and inspect candidate effects; preserve
compiler27 retained readability if execution compilation changes for identical inputs.

## PTD-08 execution contract · 2026-11-09

Retain current exporter/profiles unless independent consumption reveals an actual contract gap.
An independently specified four-family fixture supplies full expected fields/values/metadata;
after actual protected export and disconnect, a separate isolated Python process importing only
PyArrow/DuckDB consumes Parquet and manifest IPC schema. Check repeated/ordered references,
original payloads, complete pins, multiset differences and metadata independently of generated
materializers. Whole-field JSON null remains forbidden where the model forbids it; transport
SQL-null/JSON-null controls stay separate. Existing atomic/cancellation/tampering tests retain scope.

## PTD-I01 decision account · 2026-11-09

**Source-inspected at `baea0ed8e`; design judgments Proposed.** The inquiry covered the value codec,
generated call/result boundary, protected publication, directional Arrow writes, draft proposals and
PDF visual geometry. These are complete branch decisions for the current consumers, not a claim
that native adaptation or object mapping is generally unavailable. O02/O08 disposition remains in
the coordinator. No PTD-10 value/native/ORM slice is selected by I01.

| Branch | Decision and complete alternative considered | Evidence and revisit condition |
| --- | --- | --- |
| Context-free scalar conversion | **Retain the explicit shared codec.** `decimal_text`, `value_meaning` and `observed_representation` distinguish meaning from observable spelling; identity, consolidation and method configuration already reuse them. A TypeDecorator would move only Core binding/result processing, leaving protected row COPY and native semantic validation outside it. A driver dumper would likewise not replace release/context-dependent interpretation. | `semantic/value_codec.py:15–70`, `identity.py:10–21`, `consolidation.py:71–73`, `methods/model_observation.py:62–76`. Revisit when one newly declared scalar has the same context-free conversion at multiple actual SQL boundaries; migrate all affected Core/COPY/read consumers together rather than introducing two codecs. |
| Row construction | **Retain generated positional materializers.** The generator knows the operation, result fields, nominal types, JSON direction and cardinality, and invokes strict native-result construction. `class_row`, `args_row`, `kwargs_row` or a RowFactory can construct an object but do not remove this released result/admission responsibility. | `semantic/operation_call_generation.py:945–998`; `publication.py:362–368,694–725`. Revisit for a driver-owned read that repeats only mechanical construction and has no generated result owner. |
| SQLAlchemy type/comparator machinery | **Retain existing generated types and library types.** No additional bind/result conversion was identified after tracing the above consumers. `comparator_factory`, `bind_expression` and `column_expression` would add expression meaning without a corresponding released operation. Do not use them to disguise domain admission as a column property. | Selected SQLAlchemy2.1.6 `sql/type_api.py`, TypeDecorator documentation/source: JSON/ARRAY comparison coercion is not inherited automatically; `cache_ok` requires stable behavior/key state. A future decorator must delegate underlying index coercion and cover Core and COPY independently. |
| Native DOMAIN | **Retain generated column CHECK/FK and protected validation for current fields.** A reusable native scalar domain could help a future repeated scalar invariant, but the inspected identity/value fields already carry release-qualified constraints and model-derived meanings. A DOMAIN must not become a second nominal-ID generator. | `schema/relational.py`, `semantic/boundary.py`, `semantic/sql/validation.sql`. Revisit when a named repeated invariant can be expressed independently of release/context and its construction, null behavior, catalog comparison and evolution are specified. |
| Native enum and enum adapters | **Retain model-owned closed members and native membership enforcement.** Model vocabularies can evolve under released declarations; introducing PostgreSQL enums would add OID/type evolution without replacing that authority. `EnumInfo`/`register_enum` remain valid tools for an actual native closed enum. | Current generated call aliases and model vocabulary route; Psycopg3.3.6 `types/enum.py:38,126`. Revisit for a selected stable native enum whose complete declaration/evolution route is preferable to current membership. |
| Native composite and composite adapters | **Defer to an actual structured native value declaration.** Current rich proposal/reason payloads have model-bound JSON/row contracts, while publication already converts `SemanticReason` explicitly and COPY borrows its protected transaction. Replacing these with a dataclass/composite would require a new native layout, not just a constructor. | `publication.py:362–368,694–725`; Psycopg3.3.6 `register_composite(info, context=None, factory=None, *, make_object=None, make_sequence=None)`. Trigger: a selected structured field for which named native components and bidirectional typed reads remove a demonstrated JSON/row conversion. Qualified OIDs, layout generation, child nulls, `make_sequence`, catalog admission and I06 connection replacement become required then. |
| Native range/multirange and exclusion invariants | **Retain current representations.** General released `ValidityInterval` permits symbolic/partial Value bounds and unknown inclusivity, so range canonicalization would narrow meaning. The actual narrower spatial consumer already uses native `numrange` overlap for source X/Y extents; adding another range layer does not supply a missing operation. | Basis above; `serve/pdf_visual_evidence.py:679–720`. Revisit a selected concrete interval/multirange field or cross-row non-overlap invariant with exact endpoint/inclusivity semantics, preserving original source representation separately; share exclusion/deferral lifecycle with I06. |
| Direct pgvector binary adaptation | **Retain the current pgvector SQLAlchemy bind route.** The selected VECTOR type has its own bind processor; registering Psycopg codecs alone does not remove that text conversion. Current contextual queries already receive typed vectors. A binary route would need an actual direct driver/COPY consumer and complete profile/dimension/normalization checks. | pgvector-python0.5.1 `sqlalchemy/vector.py:21`; current contextual storage/retrieval. Revisit if a selected operation naturally owns direct Psycopg vector transport, coordinated with I03 and I06; make no transport-speed claim from registration alone. |
| Private ORM graph editing, loaders and UoW | **Retain explicit proposal operations.** The concrete draft workflow binds an authored batch to served packet/schema hashes, complete packet reading, source placement, checked-object identity and live task fencing before append/settlement. Imperative mappings, composites, associations, identity map, loaders, cascades, versioning or custom collections would not discharge those operations; they would add a second mutable object lifecycle. | `intervene/semantic.py:58–150`. Trigger for a new inquiry: an actual multi-step graph editor needing object identity, coordinated navigation and staged graph mutation beyond packet check/commit. General mutable ORM authority still requires the coordinator's rule decision; constructor factories alone do not authorize it. |

The negative scope is bounded to these current paths; no conclusion rests on an empty ORM or adapter
search. Native SQL validation mirrors canonical meaning as an independent instance-admission
responsibility, not redundant Python conversion to delete. This comparison applies FP-01/FP-02 and
heuristics H4/H19/H27: preserve authority, carry established meaning and judge the whole lifecycle.
No uncertain pivotal contract required a new round-trip probe. Product/native tests are **not_run**
for this source-based decision work; earlier PTD-01/08 receipts retain their original scope/date.

<a id="i05-input-decisions"></a>
### I05 input-family decisions · 2026-11-09

These conclusions feed the I05 account in [inspection/research](inspection-and-research-access.md#ptd-i05-decisions).

| Branch | Decision, investigated consumer and trigger |
| --- | --- |
| External structured data / target-aware ingestion | **Retain existing source-bound observation and protected publication routes.** `ingest/annotations.py:56–103` binds annotations to immutable native pieces and verifies their partition/source atoms; `publication.stage_batch` then borrows the caller's Core/Psycopg transaction. `ArrowWriteProfile` also already supplies a target-authenticated directional COPY path. ADBC append could serve an independently owned staging operation, but none of these current consumers can surrender same-session publication to a separate ADBC connection. Revisit when an actual external dataset supplies source ownership and a complete independent admitted transaction; append/create/replace/temp modes must be judged there. |
| Nested list/struct transport | **Defer new native array/composite input profiles to a selected nested field.** Current companion JSON/text distinctions and annotation payloads have explicit model/provenance contracts; positional pgpq compatibility does not replace them. Trigger: a declared nested input where array dimensions/lower bounds or composite fields preserve the intended meaning and remove conversion. Extend the existing profile, with qualified nested OIDs, child nullability, exact wire types, fresh encoders and failure rollback. |
| arrow-json | **Retain current explicit JSON-text/JSONB direction.** `ArrowWriteProfile.prepare/new_encoder` already distinguishes UTF-8, LargeUtf8 and string-view JSONB builders. A generic nested JSON bridge would introduce top-level JSON-null/Arrow-null and precision choices without a missing current operation. Revisit when the selected nested input requires JSON decoding into Arrow structures and declares those mappings. |
| Spatial adapters | **Retain typed source regions, raster/affine custody and native range overlap.** `semantic/pdf_visual_mapping.py:33–120` qualifies physical page, coordinate origin, crop bounds and rotation; the Reader converts admitted regions to numeric range predicates. Geographic adapters or PostGIS would not replace those source transforms. Trigger: an actual polygon/topological/geographic operation that the current rectangular range route cannot express, with an explicit coordinate-space/precision contract. |
| Rust transport | **Defer to a real Rust producer/consumer.** The inspected workspace crate is still a starter (`crates/corpus-structure/src/lib.rs`); annotation, publication and export consumers are Python-owned. pgpq Rust encoder/buffer APIs would add a second integration without removing a current handoff. Trigger: a selected Rust responsibility delivering an actual Arrow stream or consuming COPY bytes, with buffer/error ownership, schema/OIDs and publication custody specified. |

Selected pgpq is the locked Python distribution0.12.0; the discovery's commit pointer is capability
source evidence, not a replacement for that installed dependency selection. Existing profile checks
and same-session COPY remain the enforcement route. No dependency or native schema change follows
from these decisions, and no new input slice is selected for PTD-10.


## Completion audit · 2026-11-09

At the audit baseline, PTD-01's generated boundary reached its intended consumers, but anchored
correspondence validation was incomplete: source_bindings returns nominal anchors and skips their cp:type_source edges before
checking cycles, encoding or conflicting anchors. Preserve naming authority while validating those
edges, with independent anchored negative examples. PTD-08 retains its bounded directional and
independent post-disconnect delivery; shared child-error custody is owned by PTD-02. The coordinator's
[completion audit](../postgresql-typed-domain_2026-11-09.md#completion-audit) owns CA01/02 and the
implementation/qualification distinction. No input/ORM/native investigation was reopened.


## Repair execution · 2026-11-10

The [coordinator delivery receipt](../postgresql-typed-domain_2026-11-09.md#completion-repairs-and-ptd-10-delivery--2026-11-10)
closes the local audit obligations at the scoped boundary and owns current disposition. Historical
audit descriptions above identify the inspected baseline, not an unrepaired current claim.
Shared correspondence validation now includes explicit anchored and schema-level/physical-ancestor
edges. Positive model-to-physical backreferences preserve shipped nominal output. Independent
compilation, column/companion generation and real typing consumers cover the repaired boundary.
