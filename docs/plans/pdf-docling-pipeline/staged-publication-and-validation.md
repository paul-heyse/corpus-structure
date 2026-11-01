# Bounded staging, native validation and atomic document publication

## Structured-data amendment — PDF-20/21 integration

**Accepted planning target,2026-11-01; new implementation not_run.** [PDF-27](structured-payload-model-and-validation.md#PDF-27)
owns payload/schema/codec authority; [PDF-28](structured-payload-model-and-validation.md#PDF-28)
owns complete persisted semantic validators. Coordinator RC10/11 qualify the earlier mandatory
server-interior JSON-schema realization. Dated receipts below retain their original scope.

PDF-20 adopts bounded page payloads and necessary projections through the existing SQLAlchemy
transaction and PG-04 `ArrowWriteProfile`/`copy_arrow_stream` mechanics with a fresh pgpq encoder
per stream. Keep nested IPC bytes separate from the SQL envelope schema. Use existing artifact/byte-fold custody, exact replay,
release/source/attempt checks and short uptake transactions. ADBC/pgpq remain selected transport
options, not automatic nested-SQL types or a second transaction/pool owner. Compare actual grouped
uptake with executemany that still invokes scalar schema compilation; replace unnecessary work.

PDF-21 requires PDF-28 results over actual frozen OCR/candidate/report payloads and their required
inputs/projections, not merely producer drafts or the reconstructed native graph. Preserve independent
PostgreSQL relational/byte/custody enforcement and atomic public visibility. Bind results to immutable
membership, exact bytes, schema/release and validator contract; changed premises, missing results,
bad candidate geometry/offsets or false coverage refuse seal. Reuse task/holder, heartbeat, finite
worker and existing result lifecycle. Extend the validation-derived access/projection phase to
produce required page projections from exact persisted payloads, with bounded typed adoption.
A trusted child/result-registration bridge is judged by its enforced contract, not merely by
whether its SQL parameters include a boolean; no detached caller assertion or certificate state
machine replaces complete bound validation.

Inventory all pg_jsonschema consumers before removing its requirement for selected interiors.
Retain necessary SQL-used validation, and remove the dependency only when no remaining contract
requires it. PDF-27 schedules successor ADR/owner changes before dependent behavior; PDF-25 owns
new forward revisions against the actual integrated PG-08/11 head; committed history stays immutable. Use actual PostgreSQL catalog compilation for
generated routines: pglast AST parsing does not compile PL/pgSQL bodies. Verify stale results,
projection mismatch, conflicting replay and interruption around append/freeze/seal with actual
stored members; full book/provider acceptance remains PDF-25/10/11. Consume PG-02 phase/effect
outcomes and PG-05 borrower cancellation through cursor closure and transaction settlement;
keep native/CPU child cancellation distinct. Use the existing validation-derived projection
adoption, not an additional producer mirror/coordinator. RC12 uses current-product rebuild from
compatible retained evidence instead of old-layout compatibility.


**Status:** PDF-20/21 mechanisms implemented with scoped native verification, 2026-11-01; integrated whole-book publication and complete failure/concurrency acceptance remain open. [Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns PDF-20/21 and I17/I18 state. Consumes [review O02/O04/O05](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O02) and [target §§2–4/6](../../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) at `1c6fc710`; schema/identity owners are [PDF-18/19](relational-document-model-and-identity.md).

## Implemented publication boundary — 2026-11-01

Forward0065 implements model-owned frozen/native/integrated kinds, immutable private candidate
records, actual-row logical identity, required finite native callback outcomes and a short final
published-revision bridge. Preparation and validation do not retain task locks that block lease
heartbeats. Stage recipes bind original source/root recipes without rewriting original custody.
Explicit inspection/resume distinguishes open, frozen and published progress; a newly computed
draft cannot silently replace a frozen result. Freeze/seal and typed replay controls run against
actual PostgreSQL. The coordinator and [receipts](../../design_review/evidence/2026-11-01_pdf-publication-adoption/README.md)
retain their bounded scope; no deployed whole-book product follows from fixture controls.

Fixed companion fields retain oversized/NUL text and all native metadata values as independently
verified byte parts, while envelope identifiers and lookup projections remain queryable.
Native `pg_jsonschema`0.3.4 validates actual metadata JSON under the released class schema and
projection constraints. Its raw-JSON interface avoids PostgreSQL's NUL-rejecting JSON traversal;
there is no sanitization or client-only schema assertion. Exact Python reads/exports retain float
bits, negative zero, explicit nulls and text. [ADR-0044](../../adr/0044-native-pdf-metadata-jsonschema.md)
owns this mechanism; ADR-0043 owns verified byte folds versus optional serialization SHA.

The installed extension has no compiled-schema handle API. Current admission validates each
metadata row; existing bounded uploads and Psycopg executemany remain intact. PDF-27/28 and
I22/I24 now decide selected validation replacement. Assess compilation amortization only for
remaining families whose SQL-used contract retains pg_jsonschema; it is not a prerequisite to
qualify the superseded interior route. Actual integrated endpoints/coverage, cancellation/crash
recovery and the complete publication union remain required.
0065 is authored but undeployed;0060 remains the owned application baseline.

## Improvement integration — review I05/I06/I09

[Library improvement review](../../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md) at `5d7a72c4` refines this target. PDF-18/19 remain
implemented foundations; the source/replay, request-outcome and live admission obligations below
are planned PDF-20/21 integration, not claims covered by the prior394-test receipt.

## Result and existing strengths

Persist useful document progress without holding a whole-book transaction or making partial content authoritative. PostgreSQL retains independent instance enforcement, immutable input custody and final visibility; the model governs the lifecycle. Extend existing task/attempt/holder fences and protected native functions rather than adding another lease owner or workflow engine.

`semantic/arrow_publication.py::stage_arrow` already uses pgpq/Psycopg COPY on SQLAlchemy's driver connection. Its `AppendPublication` constructor still freezes full tables through IPC bytes, `read_all`, `to_pylist`, global sorting and canonical JSON. Reusing only the COPY loop is useful; retaining that constructor as the required transport would defeat this plan. `sql/pdf_integrated.sql`/`native_documents.sql` enforce substantive inventories and custody;0061's set child join corrects an access pattern but still belongs to the old envelope realization.

<a id="PDF-20"></a>
## PDF-20 — Typed batch transfer, private durable records and artifact parts

**Input:** PDF-18/19 contracts, I17 begin/append ownership and replay slice, I18 exact wire profile, PDF-17 decision slice. **Output:** fenced, resumable bounded admission of actual records/bytes; staging remains unavailable to ordinary consumers.

Expose model-defined begin/append/artifact-part operations qualified by document revision, source/release, task attempt and holder. Bind exact schema and replay keys. Identical replay is idempotent; changed content under the same key refuses. Delivery order is independent of native membership order. Admit complete records only and enforce cross-project/source isolation.

Use a schema-bound `RecordBatchReader` producer and immutable replay owner. `RecordBatchReader.from_batches` consumes an iterator once; retries read the owned durable spool. Batches are constrained by actual bytes/values and total live state, not row count alone. Exact profile validation covers decimals, lexical strings, presence/null, nested structures, metadata and column order. pgpq is not a universal arbitrary-nesting bridge; unsupported nested structures lower into modeled child relations or explicit bounded extension data.

On one SQLAlchemy-owned `Connection`, obtain the existing Psycopg driver and run `cursor.copy(... FORMAT BINARY)` with pgpq `ArrowToPostgresBinaryEncoder.write_header/write_batch/finish` and `Copy.write`. COPY targets session-local scratch; a protected function independently validates/adopts the upload into durable private relations within that same short transaction. No direct authoritative-table write grant is added. SQLAlchemy owns commit/rollback and checkout lifetime; inference never holds a connection.

Temporary tables are not durable cross-session progress. Define atomic adoption from scratch, immutable membership keys and artifact-part correspondence. A client checksum or successful COPY cannot substitute for native validation. Reject malformed casts/types, stale owners and conflicting retries before their records become build members. Abort/disconnect leaves either an adopted private batch or no batch; resume checks the actual inventory.

Reuse `capture_storage.py::store_relation` and its incremental `ParquetWriter.write_batch` ownership where suitable. IPC file `new_file/open_file` plus `memory_map` is appropriate for exact seekable Arrow replay; Parquet provides compression/projection with decoding allocations. Do not persist both without distinct consumers. Backing-file deletion follows the last borrower and existing failure-evidence rules.

ADBC `fetch_record_batch`/existing exported-snapshot reads remain useful to PDF-24. ADBC ingestion on its own connection cannot silently share Psycopg's transaction/temp tables. Retain the existing regular Psycopg physical pool lending through SQLAlchemy NullPool; Core owns the publication transaction, and COPY borrows its checked driver. No second pool or writer session is selected.

### Source/replay admission and bounded evidence

Bind the producer's owned seekable source and replay descriptor to actual original digest,
source/frame recipe, release and attempt. PDF-22 owns native source/crop lifetime; PDF-20 adopts
actual records/artifact parts into durable private custody before a producer may discard required
replay input. File paths and claimed checksums alone are not custody. Do not serialize live backend,
Docling or connection handles across IPC or hold a connection while waiting for inference.

For relational COPY families derive exact schemas from `record_arrow_schema`; selected nested
payloads instead use PDF-27. Keep field order, nullability, presence/scalar
profiles, JSON wire metadata and overflow-stream references. Retire `AppendPublication`'s required
full-table IPC freeze, `read_all`, `to_pylist`, global sort and canonical-body construction from this
new write path. Reuse only the suitable scratch COPY/adoption components. Do not remove the older
mechanism from unrelated consumers before their replacement is integrated.

Request/page/stage/crop outcomes and optional provider metadata use fixed modeled relations or
bounded extension/parts under declared contracts. Missing usage is unavailable, not zero or success;
failed/partial/unrequested and valid zero-C are different. A growing page metadata map must not
reintroduce the JSONB limit. Exact raw output precedes cleanup/rendering. Shape validation, content
identity and independent native correspondence remain different obligations.

I14's assembly inputs and I20's receipt identifiers are early contract dependencies; working
producer acceptance is later. Scratch adoption has independent expectations for source replacement,
incorrect replay/recipe pins, failed-stage artifacts, changed duplicate uploads and disconnect.
Keep one SQLAlchemy transaction owner and a checked Psycopg driver for COPY; no second pool or
ADBC writer is introduced merely for streaming.

**Completion:** typed COPY controls check exact wire profiles and independent expected rows, including empty/reordered batches and large individual values. Exercise duplicate/conflicting retry, failed scratch adoption, cross-project artifacts, stale holder, disconnect and bounded replay. Verify no staging read path bypasses visibility. Product output is private progress, not published document or completed knowledge.

### Implemented PDF-20 prerequisite slice — 2026-11-01

`semantic/pdf_staging.py` supplies typed build/receipt references, generated family schemas and
protected begin/adopt/progress/resume/abandon adapters. `model/semantic/pdf-staging.yaml` owns the
fixed stage families, artifact/companion profiles and byte/row limits. Raw private tables deny
ordinary reads. Immediate final-record endpoint FKs are not weakened: distinct private stage
families enforce build scope and local constraints while retaining unresolved cross-batch references.
Final resolution and complete frozen-union conformance remain PDF-21.

The same-session scratch COPY/adoption transaction verifies actual values, exact duplicate/replay
content, source/release/schema/recipe custody and current task/attempt/holder. SQL also enforces the
modeled batch limits. Build state is mutable only through protected modeled operations; receipts
and adopted rows are immutable. Native descriptor generation consumes model immutability, rather
than applying an immutable trigger to every new relation. Protected scratch setup authenticates
its actual shape/ownership before reuse; NULL ownership arguments refuse rather than taking an
unknown comparison branch. These checks preserve existing lifecycle and native type obligations.

Execution ABI16 and forward0064 bind this slice. All committed earlier migrations remain frozen;
new candidate authoring uses current provenance while historical reproduction uses its retained
witness. No live migration was run. `PdfStageReceipt.content_digest` identifies an upload's actual
rows, not the historical document content digest or a sealed logical product pin.

The private parent executor adopts page replay/raster/candidate artifacts before acknowledging
backend release and adopts native/companion IPC later. Successful partial progress survives later
failure; explicit resume changes ownership under the existing task fence and replays exact retained
files. There is no source-ready/publication shortcut or terminal UnitResult for a private build.
[Runtime evidence](../../design_review/evidence/2026-11-01_pdf-streaming-runtime/README.md) owns
scoped native/fence/replay controls; PDF-20's later complete publication integration and PDF-21
freeze/seal are not credited by these receipts.

<a id="PDF-21"></a>
## PDF-21 — Freeze, complete native validation and atomic seal

**Input:** PDF-20 working admission, PDF-18 model invariants, PDF-19 identity/correspondence and I17 concurrency decision. **Output:** one immutable published document with truthful closure, recovery and selective-reader authority.

Author states and operation effects in the existing semantic execution model:

| State | Permitted behavior |
|---|---|
| Open/private | Fenced append, artifact adoption and exact retry; no completed-document readers. |
| Frozen/private | Inventory immutable; validation may inspect the entire fixed union. No outstanding writer may append or alter bytes. |
| Published/immutable | Selected pins and readers resolve the admitted product and companion. Changes create a successor revision. |
| Abandoned | No admission/seal; required failed evidence and independently committed valid native/recognition products survive. |

Freeze and append must serialize on the same ownership/membership boundary. Validate the fixed union outside long run/task publication locks, then seal in a short protected transaction that rechecks run/task/lease, immutable inputs, release/contract, exact frozen membership and validation premises. Record validation scope under the owning model; do not invent an independent certificate framework. If any premise can mutate, remove that mutation or repeat the affected validation. Ambiguous seal recovery reads the same revision instead of creating a replacement product.

Validate complete node/collection/occurrence/cell inventories, native reference mappings, order, tree containment, parent/backpointer agreement, frames/provenance, external inputs, raw artifacts, relation multiplicity/endpoints, decisions and coverage. Containment/product-input dependencies retain their declared acyclicity; ordinary document cross-reference/companion graphs may contain cycles. Private internal forward references are allowed until closure; external product dependencies must already be admitted immutable products, preserving existing cycle/self-reference protection.

Use indexed FK/unique/CHECK and set-based validation, including0061's child-target semantics, without building a giant JSON aggregate or repeatedly scanning full input per parent. Local record shape checking cannot establish global completeness. Reusable Pydantic `TypeAdapter`, JSON Schema `validator_for/check_schema`, prepared validators and pinned `referencing.Registry` support boundary diagnostics; PostgreSQL independently enforces actual values and relationships. Partial-validation omission and unvalidated construction do not satisfy admission.

Use existing pglast AST authoring and Alembic forward SQL/admission products. Current descriptor helper, body CHECKs, function inventory and native constraints must derive from their current semantic owners. Counterfactual changes to a governing declaration must change the realized guard/descriptor, without depending on stale frozen bodies. Never modify frozen0057–0061 or copy the duplicate physical-contract snapshot insertion into a new revision.

Cancellation/lease loss fences new work and drains owned producers/COPY/validation resources. Explicit resume/adopt verifies a frozen inventory across attempts; implicit mixture is forbidden. Cleanup removes only authenticated private staging after retention obligations are met. Preserve fixed protected-function search paths and restrict raw-table privileges and functions so ordinary reads cannot bypass publication by knowing an ID. Diagnostics name the revision, record/native address, violated invariant and existing resume/remap/rebuild action.

### Approved validation and identity placement — 2026-11-01

Freeze fixes the real typed inventory, including companion families and request outcomes. Final
rows and access projections are prepared privately before the short publication transaction;
immutable staging is not patched to resolve references. Validation uses the actual fixed candidate,
not a producer's claimed successful result. Parent-owned record capture supplies an authenticated
replay to a finite DB-free native-conformance child; its explicit full native hydration preserves
the selected global materialization boundary. PostgreSQL separately enforces actual field/type,
collection/reference/containment/frame/companion and artifact invariants through generated local
and set-shaped guards. Validation outcomes bind the immutable inventory and archived contract.

[ADR-0043](../../adr/0043-segmented-artifact-byte-identity.md) separates required native byte folds
and exact retained-byte correspondence from optional new export serialization SHA-256. There is
no submitted whole native export prerequisite. Readers generate that serialization explicitly
from admitted records. Existing original/raw/historical byte identities stay unchanged.

### Frozen interpretation and validation coverage

Freeze also fixes request-outcome inventories, transformation recipes and native-address mappings.
A successful detector/crop request does not establish full page coverage; a partial producer cannot
satisfy complete publication by omitting its failed stage. A declared successful recovery may satisfy its
qualified coverage contract while preserving the primary failure and distinct recovery recipe.
Native validation must consume the same
release-bound distinctions as readers and diagnostics. Protect actual bytes and record/artifact
correspondence independently of client folds. Existing PDF-19 primitives are not a complete
server-side correspondence proof for newly submitted arbitrary segmented streams.

Model enrichment as a pre-freeze transformation or a successor product with qualified source
relations. Reject silent validation repair. Ensure page metadata, native references and deferred
internal targets close without giant aggregates. Late callbacks or stale attempts cannot amend the
frozen union. Preserve public visibility and acyclicity rules while allowing legitimate ordinary
cross-reference cycles.

**Completion:** concurrent append/freeze, process crash/restart before and after freeze, stale validation owner, cancellation at each phase, missing/cross-product targets, contradictory backpointers, legitimate cross-reference cycles, missing decisions, wrong coverage, corruption and ambiguous commit have independent expectations. No partial completed document becomes visible. Valid independently committed inputs remain reusable after later failure. Final publication and reads are tested together; the coordinator/PDF-11 own assembled qualification, not each batch/package.

## Sources and adoption boundary

See [SQLAlchemy](../../libraries/postgresql/sqlalchemy.md), [Psycopg](../../libraries/postgresql/psycopg.md), [pgpq](../../libraries/postgresql/pgpq.md), [pool](../../libraries/postgresql/psycopg-pool.md), [ADBC](../../libraries/postgresql/adbc-driver-postgresql.md), [pglast](../../libraries/postgresql/pglast.md), [Alembic](../../libraries/postgresql/alembic.md) and the review's primary-source map. Exact pinned interfaces/types must be verified under I18 before implementation; no dependency change is premised merely by naming a capability. PDF-25 owns current-realization rebuild/adoption.0060 remains deployed and0061 undeployed at plan creation.
