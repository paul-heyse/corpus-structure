# Released types and faithful exchange

**Status: PTD-01/08 implemented and scoped tests passed; investigations planned · 2026-11-09.** Selected package delivery is Tested at the scope recorded by the coordinator; conditional targets remain Proposed. The
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
