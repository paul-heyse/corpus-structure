# PDF structured payloads and PostgreSQL capability integration

**2026-11-01 · Proposed plan-improvement review · Combined library, domain-model and efficiency focus.**
Reviews [PDF-27/28](../plans/pdf-docling-pipeline/structured-payload-model-and-validation.md) and
materially affected PDF-18–25 against the concurrent [PostgreSQL series](../plans/postgresql-capability-leverage_2026-11-01.md).
Recommendations are not adopted plan changes, accepted ADRs or product qualification.

## Combined judgment

The two targets are complementary, but their Arrow contracts are different. Reuse the PostgreSQL
work's model-derived relational projections, directional transfer preparation, borrower lifetimes,
selected-source context and native migration authoring. Add nested page payloads as another
physical realization of governed native/application meaning. Do not turn their interiors back
into SQL-shaped JSON strings to fit the new helper, or mistake a static column declaration or
COPY profile for their complete logical schema and validator.

The main structural improvement is a composition of **one semantic authority, operation-shaped
representations and existing lifecycle owners**. PostgreSQL owns custody and relational invariants;
native/application contracts own payload interpretation and complete validation. SQL/Arrow/Parquet/
selected-source projections expose only their declared meanings. Their identities and explicit
mappings permit reuse without pretending all representations are interchangeable.

Prioritize the shared contract/identity and persisted-validation amendments first, then selective
consumer integration. Native authoring and borrower mechanics should be consumed rather than
reimplemented. Broader native payload conversion, additional engines, services and a generic
interchange framework are unnecessary prerequisites. Performance benefits remain hypotheses;
this review identifies work that can be removed, not measured savings.

## Baseline, evidence and coverage

Main is `524c5a732af06a869375616d05bc087194aa0d78`. The implementation worktree is
`/home/paul/corpus-structure-postgresql-capability-leverage`, branch
`work/postgresql-capability-leverage`, HEAD `977eb8b13778f01926786f4fd2908c84fb3be242`.
It includes main's new PDF plans. During inspection its HEAD advanced through `2f5e01a6` to
`24b227566e5b64c12f86d760b7b24093212570d7` (clean worktree at final refresh);
material contracts were rechecked as described below. Most shared implementation initially inspected here was dirty or untracked,
not an available main integration. Commits made concurrently do not establish main integration. Its checkpoint reports scoped checks and incomplete final-source
qualification; those reports were not rerun or promoted into this review's evidence.

The committed branch adds SQLAlchemy2.1.6/Alembic1.20.1 and database-description work. Initially dirty work, now committed on that branch,
includes compiler18 native admission, migration0066 (`semantic_pg_20261101`), shared COPY preparation,
companion projections, selected-source export, reader/context and cancellation changes. Its private
PostgreSQL instance on55434 was not used. Main's deployed PDF baseline remains0060; this review
performed no deployment query, migration, inference, provider grading or worktree merge.

All seven expanded PostgreSQL library references were read from **main**: their uncommitted
addenda are absent from the worktree copies. The PostgreSQL plan/review and both checkouts'
current target/owner text were reconciled separately from code. [Original PostgreSQL review](../functional_reviews/postgresql-capability-leverage_2026-11-01.md)
O01–O15 and [structured-data review](pdf-docling-structured-data_2026-11-01.md) I01–I09 remain their
source identities; existing coordinators retain scheduled disposition. This is not their completion audit.

Criteria are core3.3, efficient-architecture heuristics1.0, profile1.4, repository binding and the
test-assessment companion for acceptance reasoning. FP-04/A2 require governed operations and
relations, not merely typed outputs; FP-07/A4/H2–4/H12/H15–24 guide execution placement and reuse.
No audit baseline or premise was refreshed. Two independent source assessments covered payload/
publication and consumer/lifetime composition; recommendations below integrate those perspectives.

Context7 was the first library lookup, followed by official documentation and source inspection.
[PyArrow26 reference](../libraries/analytical_infrastructure/pyarrow.md) was assessed across nested types/nulls, compute/Acero,
datasets/Parquet, IPC, memory/threading, C Stream and extension/interoperability capabilities.
No runtime probe was needed to settle these design recommendations; uncertain integration remains
explicit below. Latest/general docs are orientation, not a claim of installed support for every API.

## I01 — Extend the shared model realization; keep four contracts distinct
<a id="I01"></a>

**Alignment improvement; prerequisite. Owners:** PDF-27/18/19, PG-03/04/06.

Worktree `semantic/typed_generation.py::generated_source`, `companion_projection.py::projection`
and `schema/relational.py` already generate typed Core surfaces and SQL/Arrow companion projections.
`companion_projection.py::CompanionProjection.statement` uses table-valued functions and
`.with_cols`; `ArrowWriteProfile` binds ordered fields, SQL wire types and encoder behavior.
These are useful existing realizations, not a complete native/Pydantic→nested-Arrow bridge.

Amend PDF-27 to define the relationships between logical family schema, nested payload encoding,
queryable relational projection and directional transport profile. Extend the existing release/
compiler facilities and native/application definitions, with finite codecs for actual missing
mappings. Generate `TypedColumns`/`Named` and `.with_cols()` surfaces only for SQL-visible fields;
do not build a duplicate column generator or infer native semantics from destination SQL types.
One new OCR field should update its native/app declaration and required generated forms, without
separate hand-authored meaning in SQL, Arrow and consumers. [SQLAlchemy2.1 mechanism](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).

Keep schema/release, mapping/codec, projection and wire-profile identity distinct from content
identity. A dictionary choice or compression change need not change logical content; a field's
meaning, null/presence convention or projection selection can change interpretation even when
its physical type is unchanged. Bind preparation to the complete governing contract, not a live
connection or process-global assumption. Current `projection(family)` process caching is context
for reviewing future release use, not proof that every historical interpretation is supported.

**Challenge/closure:** add a field and separately change its semantics without changing its SQL
type; verify affected preparation/projections change and irrelevant payload layouts need not.
Native variants, computed fields and absent/default/null fidelity remain PDF-27 obligations.

## I02 — Compose nested IPC custody with unified COPY mechanics
<a id="I02"></a>

**Execution simplification. Owners:** PDF-27/20/23, PG-04; I21/I24.

Worktree `semantic/arrow_transfer.py::ArrowWriteProfile.prepare/new_encoder/validate_batch` and
`copy_arrow_stream` consolidate relational binary COPY, with fresh encoder state per stream.
`pdf_record_model.py::record_write_profile` and `pdf_staging.py` consume that route. Reuse it for
SQL envelopes, parts and projections where the profile fits. Preserve the nested payload as a
self-contained IPC unit in bytea/existing part custody; pgpq encoding that outer binary value
is different from asking pgpq to translate every nested value into native SQL arrays/composites.

Start page OCR/candidates with `ipc.new_stream/open_stream`, explicit nested fields and archived
schema binding; avoid a whole-book value. Use `BufferReader`/native Arrow I/O for decoding, keeping
owned bytes alive. Compare IPC files plus `memory_map/get_batch` only for actual seekable local
replay; a fetched PostgreSQL bytea is not a remote Arrow range reader. Compression and TOAST must
be chosen together. ADBC `binary`→bytea support does not establish `large_binary` or arbitrary
nested ingest support. Directional type support must match the pinned driver/pgpq profile before
choosing a writer. [ADBC source](https://github.com/apache/arrow-adbc/blob/main/docs/source/driver/postgresql.rst).

Retain Psycopg `Copy.set_types/write_row` for existing Python rows and server `INSERT ... SELECT`
for resident relational transformations. Neither needs a conversion to Arrow solely for uniformity.
Compare complete ADBC-owned ingest only when a real operation justifies changing its session owner;
it cannot borrow another session's scratch state. Current same-session adoption is the simpler
supported composition. The native composite alternative remains useful for stable SQL-operated
values, with explicit OID/adaptation and constraint responsibilities, not universal payload storage.

**Challenge/closure:** wrong same-typed column order, metadata mismatch, oversized page/part,
encoder failure followed by fresh replay and exact NUL/float/presence round trips. Distinguish
Arrow buffer integrity from semantic validity; do not normalize a mismatch just to enter COPY.

## I03 — Make an owned batch stream the common computational boundary
<a id="I03"></a>

**Additional PyArrow leverage. Owners:** PDF-23/24/27, PG-03/06; I21/I23/I24.

The PDF plan asks for typed payload processing; the PG work supplies typed family capture. Join
these at `RecordBatchReader`/batch iteration with explicit schemas and ownership rather than a
new universal driver interface or repeated `to_pylist`/native-object reconstruction. Use
`RecordBatchReader.from_batches` to adapt an actual producer where useful; use existing Arrow C
Stream/PyCapsule interoperability for an actual compatible consumer. No custom FFI bridge is needed.

For page-local geometry/range checks and projections, assess `compute.struct_field`,
`list_flatten`, `list_parent_indices`, `filter`, `take`, `is_valid` and checked arithmetic against
the actual rules. Preserve original word indexes and qualified identity before flattening;
null lists emit no flattened values, so explicit empty/null/absence state must survive separately.
Kleene booleans and aggregate null options matter to partial coverage. Native/custom validators
remain for semantics not faithfully realized by kernels. This is not automatic Pydantic-to-kernel
compilation or a requirement to rewrite every short Python operation.

`RecordBatchReader.cast` can apply selected safe conversions lazily when names/order and the
profile permit them. It does not authorize schema evolution, metadata replacement or native
normalization; exact profiles should refuse before coercing incorrect input. Preserve separate
exact and analytical views. [Arrow reader](https://arrow.apache.org/docs/python/generated/pyarrow.RecordBatchReader.html),
[nested compute](https://arrow.apache.org/docs/python/compute.html).

Keep current DuckDB for relational comparison and queries. Acero expressions may remove a
concrete page projection/filter intermediate; compare that local composition rather than add a
second mandatory analytical engine. Substrait, Flight, tensor/GPU layouts and custom extension
types have no demonstrated additional consumer in this footprint and are not recommended now.

A concrete first optional derivative is coverage supports: worktree
`model/semantic/companion-projections.yaml` declares `PublishedCoverageRow.supports_json`, while
`companion_projection.py::_source/projection` maps structured/multivalued slots to JSONB and
`pa.json_()`. The logical `PdfCoverageSupport` already owns `input_index`/`coverage_id`.
For an actual coverage-analysis consumer, derive a typed list/struct view and retain parent
coverage identity with list kernels; where SQL joins supports, use its protected relational
projection. This removes JSON reparsing without inventing another support schema. Preserve
null/empty support distinctions; the current flat export is not thereby incorrect.

**Challenge/closure:** preserve repeated word/endpoint identities, null versus empty inventories,
explicit incomplete coverage and exact indexes across nested projection. Compare complete
retrieve/decode/validate/use work, including the Python crossings actually removed.

## I04 — Reuse protected relational and selected-context projections
<a id="I04"></a>

**Consumer consolidation and capability improvement. Owners:** PDF-24/27, PG-06/10; I23.

The worktree adds `companion_projection.py`, four protected companion read functions,
`serve/companion_export.py` and `serve/selected_source.py`. Its selected-source model and native
query govern semantic subtree membership, ancestors, frames, all relation endpoints, supported
inputs, coverage, diagnostics and qualified outside references. Reuse those contracts for
scientific/extraction preparation rather than invent PDF-only selection or companion serializers.

Extend that selection with payload-family/page/group demand and source-qualified payload
references. A section's semantic membership is neither physical record containment nor arbitrary
reference reachability; page intersections must not import unrelated section bodies. Keep
occurrence/endpoint/coverage joins available to SQL. Make exact required payload parts retrievable
under the same pin and policy, and make optional omitted content explicit. The current event
format's record/companion JSON parts do not automatically define a nested IPC payload event.
Version the affected contract if its meaning changes; preserve ordinary native/full exports as
different supported projections. A selected package is not a complete DoclingDocument.

For analytics, reuse one snapshot-bound typed capture and detached manifest, then DuckDB analysis
after database resources close. Selected-source context and four-family analytical inventory have
different completeness meanings; do not combine them under an ambiguous export label. The final worktree checkpoint reports its coverage repairs/scoped native and CLI checks passed;
those are reported receipts, not a test rerun here or whole-PDF closure.

There is an actual consolidation seam, beyond adding selectors: worktree
`semantic/sql/pdf_record_context.sql` supplies a shared set-shaped context selection with
ancestor/page-range coverage, while `pdf_record_reader_native.py::pdf_record_context_sql` still
authors separate paginated context rules. `PublishedPdfReader.context_rows` and `source_context`
therefore consume different accounts. Derive paged, streamed and convenience views from the same
owned selection before adding payload-aware closure. Preserve relation occurrence and endpoint
multiplicity. The older PG plan's missing-membership-forwarding diagnosis is already corrected
in live `pdf_storage.py`; do not reschedule that obsolete repair.

**Challenge/closure:** intact section with field-contained table/cell structures, cross-page
content, repeated occurrences, outside formula
and partial/nested coverage. A demanded missing value must return additional context required,
not a complete scientific result. Whole-document coverage must retain its original scope.

## I05 — Use manifest-bound selective scanning for detached analytical payloads
<a id="I05"></a>

**Further PyArrow opportunity, conditional on actual detached consumer. Owners:** PDF-24/25, PG-06.

`companion_export.py` already publishes manifest-listed Parquet family files; avoid another
wildcard dataset discovery/cache layer. An Arrow consumer can build `dataset` from the exact
verified file list and explicit schema, then use `scanner(columns=..., filter=...).to_batches()`
for required columns and rows. Column projection and Parquet row-group pruning can avoid decoding
unneeded data, unlike filtering a fully hydrated book. Keep the existing DuckDB direct-Parquet
route for consumers whose work is already SQL; do not insert an Arrow scan before it by default.

IPC `IpcReadOptions.included_fields` selects top-level decode fields, not PostgreSQL byte ranges
or arbitrary nested children. Parquet `ARROW:schema` metadata improves selected round trips but
does not make Parquet an exact substitute for every IPC union/extension/presence contract. Keep
IPC for exact payload custody and Parquet only for a distinct analytical consumer. No extra copy
is justified solely by format support. [Dataset scanning](https://arrow.apache.org/docs/python/dataset.html),
[IPC options](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html).

Bound batch/fragment readahead and thread use with the existing resource owner. Arrow slices can
retain large backing allocations; batch rows, Arrow-pool counters and response sizes do not bound
combined native/Python/mmap memory. Prefer local `use_threads`/scanner controls over repeatedly
changing process-global pools. No new memory-accounting service or benchmark program is needed.

**Challenge/closure:** one demanded field/page subset does not materialize unrelated families;
reader abandonment releases its owned buffers/files, and dictionary/null/schema metadata survives
the actual cross-engine route. Select this amendment only when an Arrow detached consumer exists;
otherwise retain the already useful DuckDB/Parquet route with the same binding obligations.

## I06 — Consume shared cancellation/outcome ownership through validation and readers
<a id="I06"></a>

**Structural lifecycle improvement. Owners:** PDF-20/21/24/28, PG-02/05.

`core/db/lifetime.py::BorrowerCancellation`, `adbc_lifetime.py::owned_adbc_read`, Store failure
translation and updated PDF operations already supply relevant source-present mechanisms.
Describe the composition accurately: one regular Psycopg physical pool lends through SQLAlchemy
`NullPool`; Core owns its transaction and COPY borrows its driver. A separate ADBC session owns
its imported snapshot. Replace vague plan language about an extra pool with this actual boundary.

Use existing handles for database work and the existing finite child lifecycle for CPU/native
payload validation. Database cancellation cannot terminate a CPU validator or an ADBC statement
on another session. Drain/close results, settle transaction effects and retire cancellation
registration before returning/reusing a connection. Preserve the primary failure and cleanup
failures. User cancellation, stale holder, confirmed rollback and unknown commit are different
outcomes; receipt resolution uses the original publication identity, never a fresh publication.

One source-inspected integration gap is `serve/selected_source.py::export_selected_source`:
it has no cancellation parameter, and its long raw selected-source query executes outside
`PublishedPdfReader._read_scope`. Extend the existing operation handle through that Result's
closure/transaction settlement and check cancellation before publishing output. The companion
exporter already accepts an ADBC cancellation handle; reuse that ownership pattern without
pretending it cancels a Psycopg query. No runtime cancellation failure was observed here.

Immutable payload fetch may finish and release a borrower before local validation/analysis;
keep the data owner, not an unnecessarily long database transaction. Where a consistency check
requires the frozen snapshot, explicitly keep it through that boundary, then release it.

**Challenge/closure:** cancel during COPY, after partial batch iteration, during validation and
at seal acknowledgement loss, plus selected-export sink writing and immediately before rename;
late cancellation must not hit a subsequent borrower. These are
future integration checks, not a new claim of hard shutdown deadlines or observed data loss.

## I07 — Preserve the exact frozen semantic validation obligation
<a id="I07"></a>

**Required correctness amendment retained from structured review I04. Owners:** PDF-28/21, PG-05.

Shared PG infrastructure does not close PDF-28 by itself. Current worktree
`semantic/pdf_publication.py::validate_pdf_build` still captures `header`, `native`, `membership`,
`artifact_stream`, `artifact_part` for native validation (family loop near572); its
`_native_validation_child` checks the native document. The added cancellation/transaction owner
improves execution but does not add the OCR/candidate/report semantic input set.

Extend the existing frozen validation scope/result, not a second publication state machine.
Validate exact immutable payload bytes under pinned native/app definitions and required
projections/dependencies; run page-local checks incrementally and whole-set reference/coverage
closure over its complete required scope. Separate byte/IPC checks, domain checks and relational
closure. Native JSON Schema and Arrow nullability metadata remain insufficient substitutes for
word offsets, geometry and candidate correspondence. This is the previously identified gap,
not a new assertion that malformed real corpus data was published.

Prepare/reuse model validators at release/profile lifetime and reuse results while actual
frozen premises remain unchanged. Final seal must refuse missing/stale/mismatched validation.
The PG outcome/cancellation contracts fit that sequence without weakening confirmed RC10/11.

The current child already derives native access/region projections after validation and the
parent adopts them in bounded batches (`pdf_publication.py`, child derivation near340–412 and
parent adoption near617–640). Extend this existing phase to derive necessary page projections
from the exact validated persisted payload, with typed batches where useful. Keep early custody/
locator fields and independent SQL constraints, but avoid another producer-owned mirror plus a
second projection coordinator. Do not force page payloads into the whole native graph to derive
page-local facts. Extend the existing validation contract/dependency binding and result scope;
a native-only success cannot establish the new payload contract. The existing trusted child/result
bridge is not invalid simply because its protected result-registration call includes a boolean.

**Challenge/closure:** structurally legal bad offsets, invalid geometry, missing targets, false
coverage and changed projections fail against persisted input before public visibility. A
producer-draft pass, byte digest or successful native callback alone cannot establish this result.

## I08 — Adopt the new native authoring route and choose transition scope explicitly
<a id="I08"></a>

**Delivery simplification plus unresolved policy choice. Owners:** PDF-27/25, PG-01/08/09/11.

Worktree `semantic/alembic_native.py` supplies Plugin comparison, `NativeTransitionOp`, renderer
and execution on `Operations.get_bind()`. `native_objects.py` supplies desired/observed identities,
catalog properties and admission; `prepared_sql.py` preserves authored source/slices and private
mutable ASTs. Reuse these for new payload envelope/projection/functions. A meaningful function
result change can require explicit recreation/dependency ordering rather than CREATE OR REPLACE.
Pglast parses syntax; actual PostgreSQL compilation and native admission still establish catalog
properties and protection. No second migration runner, generic drift lint or Alembic Utils is needed.
[Native plugin mechanism](https://alembic.sqlalchemy.org/en/latest/api/plugins.html).

Do not assign the next PDF revision as0066 or assume compiler18 is final. The live branch already
has committed0066 with predecessor0065 and frozen operation/admission artifacts; its final
checkpoint reports provenance refreshed. Integrate against the actual settled head and one authoring owner. Existing
committed migrations remain immutable; author new forward artifacts from accepted declarations.
The branch's upgrade/default workaround is its responsibility, not a reason to reimplement it.

The worktree's checkpoint explicitly omits historical/retained-data upgrade work under temporary
regenerable-data guidance. PDF-25 still schedules retained-data derivation. Do not silently erase
that obligation or import a historical compatibility framework. Recommend deciding at plan
revision whether new realization rebuild from retained original/native/recognition evidence is
sufficient, avoiding old-reader migration while preserving exact source evidence. If retained
published pins remain supported, schedule that actual consumer/derivation explicitly. This is a
proposed RC01 below; current PDF requirements stand until confirmed.

**Challenge/closure:** fresh owned realization admits the new contracts, an intentional function
result change uses explicit recreation, failed migration rolls back on its caller connection,
and selected retained/rebuilt inputs preserve exact bytes and qualified logical meaning. No
application deployment or evidence-store deletion follows from review publication.

## I09 — Reuse database description and authoring diagnostics for actionable mismatches
<a id="I09"></a>

**Bounded general enhancement. Owners:** PDF-27/24/25, PG-07/09.

`serve/database_description.py` and the committed `ci db describe` route expose actual visible
physical/query schema and estimates; native candidate authoring supplies comparison/admission
information. Use those existing operations in a PDF mismatch diagnostic to report the declared
payload/projection/profile binding, observed native contract and appropriate regeneration or
authoring command. Keep physical columns, query output, logical model and opaque IPC schema
separate. Database metadata cannot inspect an Arrow interior or certify domain validity.

Prefer reuse of current diagnostic surfaces over a new alignment gate or permanent capability
registry. This enhancement earns its scope when an actual codec/projection/native-version refusal
otherwise leaves the operator guessing. A broad automatic repair system or continual drift daemon
has no current consumer and is outside this amendment.

**Challenge/closure:** wrong projection/native version yields a located refusal and concrete
existing remediation; restricted visibility is reported as such, not absence. Catalog statistics
are estimates and never establish source completeness or pipeline success.

## Plan amendment map and remaining investigations

The map transfers no ownership and closes no implementation item. IDs in the first column are
from the [structured-data review](pdf-docling-structured-data_2026-11-01.md), not this review.

| Existing obligation | Net refinement and this review's recommendation |
|---|---|
| I01 placement/ownership | I01 shared realization contracts; I07 preserves enforcement; I09 useful diagnostics |
| I02 page payloads | I02 nested IPC plus shared outer COPY; I03 batch processing and I05 actual detached scans |
| I03 native/Pydantic bridge | I01 extends existing generators without replacing native schema; I03 preserves explicit conversion semantics |
| I04 persisted validation | I07 remains mandatory; I06 supplies lifecycle rather than claiming it supplies missing semantic checks |
| I05 relational access | I01/I04 retain typed SQL joins and qualified read-only projections |
| I06 scoped readers | I03–I06 reuse batch/capture/selected-context/ownership contracts |
| I07 publication simplification | I02/I06/I07 reuse transport and existing frozen result/seal; I08 supplies authoring |
| I08 effective options/images | Preserve PDF-22/23/I25 recipe and borrower/image work; I03/I05 add Arrow execution/readahead considerations, not new native algorithms |
| I09 duplication | I01–I04/I08 remove parallel generators/serializers/authoring; preserve native-aware envelope and owned-copy improvements already scheduled |

| PDF investigation | Revised decision focus |
|---|---|
| I21 type profile | Logical/native→nested Arrow mapping versus flat read/write profiles; metadata, presence, variants and real cross-engine type support |
| I22 validation coverage | Exact frozen OCR/report input set and result binding; shared cancellation is not validation equivalence |
| I23 selective access | Reuse PG protected projections/selected-source closure, add payload locators and true page/field demand |
| I24 operation comparison | Evaluate actual unified COPY and detached capture paths including encode/store/fetch/validate/compute, not old duplicated helpers or IPC-only timing |
| I25 options/images | Retain native effective recipe/image decision and materialized global scope; include composed Arrow thread/readahead/backing-buffer lifetime |

Recommended ordering is contract/identity agreement (I01/I02), persisted-validation and lifecycle
integration (I06/I07), affected reader/selection migration (I03/I04), then native authoring and
selected adoption (I08). Existing independent PG capabilities can become ready separately;
this is not a requirement to finish PG-12 before any PDF design work. Actual reuse requires the
relevant implementation/consumer evidence, not merely main incorporating its plan. I05/I09 are
conditional additions with concrete consumer triggers. Existing image/copy improvements can
proceed against agreed contracts. Final PDF-10/11 provider, independent grading, defaults and
whole-book acceptance remain at their owners, with no imported PG completion credit. At final refresh the five core source blobs
(`typed_generation`, `companion_projection`, `arrow_transfer`, `pdf_staging`, `pdf_publication`)
matched the independently inspected versions across the concurrent commits; consumer cancellation
and both context-selector seams were rechecked at `24b22756`.

### Proposed rule impacts

- **RC01 — Decide PDF adoption/retained-pin support under regenerable-data direction.** A rebuild
  from retained evidence can replace old-reader/old-layout migration machinery if supported read
  obligations are deliberately revised. Requires explicit operator confirmation and the existing
  decision/owner route before changing PDF-25 acceptance. Do not infer this from PG-only scope.
- Confirmed PDF RC10/11 remain applicable; no further relaxation of semantic validity, relationship
  identity, evidence closure or atomic visibility is recommended. Their successor ADR work remains.
- Preserve PDF-only input, one integrated content graph/companion, intact sections, independent
  automated grading, exact original/raw custody and immutable committed history. No section
  chunking, additional inference service, shared pool replacement or new audit machinery.

## Evidence limits and publication checks

**Source-inspected:** both plan targets, architectural owners, shared PG implementation and its
selected consumers, original/addendum library references and the Arrow capabilities above.
All recommendations are Proposed. **not_run:** runtime probes/product tests, broad qualification,
performance measurements, inference, DB changes, merges and operational adoption. No probe was
necessary to distinguish the inspected contract responsibilities; actual new-codec/type/execution
uncertainties remain explicit acceptance work, not claimed API impossibilities.

Independent source assessments and focused document/link checks are recorded at publication.
Existing failed/interrupted PG receipts and main's full-publication link failures retain their
original scope; this review grants no acceptance to the moving worktree.

**Publication checks,2026-11-01:** **passed:** inline `python` using existing
`scripts/docs.py::discover/rewrite_links`:15 local targets across review/index/STATUS resolved,
review discovery and unique I01–I09 anchors; STATUS remains within60 lines. **passed:**
`git diff --check`. Independent final consumer/lifetime reading found no remaining material
misstatement. **failed:** `just docs-check` on pre-existing moved-library/retired-profile targets
outside this review. No product checks were rerun for documentation-only publication.
