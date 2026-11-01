# Singular integrated document consumers

## Structured-data amendment — PDF-24 integration

**Accepted planning target,2026-11-01; new implementation not_run.** [PDF-27/28](structured-payload-model-and-validation.md)
own family placement and persisted validation; I23/24 shape this reader migration. Existing exact
metadata decoding and single-cursor exports remain strengths to retain, not unimplemented N+1 fixes.

Extend the pinned reader contract with page/group and requested-field intent, selecting relational
page/kind/pointer/outcome keys before payload decode. Keep native graph hydration explicit for actual
native behavior. `native_product_values()` currently materializes the document and candidate/report
families: migrate page-local discovery/alignment/diagnostic callers to scoped reads rather than wrap
that whole-product function in a batch API. Own batch/buffer/cursor lifetimes through early exit and
cancellation; cross into native models or JSON only for consumers that require them.

Assess `IpcReadOptions.included_fields` for top-level Arrow decode selection; it does not reduce
PostgreSQL bytea transfer or prune arbitrary nested children. Retain `RecordBatchReader`/arrays
through useful DuckDB/Acero or `compute.struct_field`, `list_flatten`, `list_parent_indices` work
where semantics fit. Preserve word identities/null/ordering when deriving views; no unconditional
`to_pylist` or full-document hydration inside a small-read contract.

Reuse PG-06 protected companion projections, detached snapshot capture/manifest and PG-10
selected-source semantic membership/context/event machinery. Extend their contracts with
payload-family/page/group/field locators under the same pin/source/schema/recipe and declared
projection. A page intersecting two sections is retrieval context, not authority to select both
sections' bodies. Preserve qualified outside references and explicit omissions; missing demanded
content returns the existing `AdditionalContextRequired`/input-required outcome. Do not force
columnar consumers through JSONL or call a selected package a complete DoclingDocument.

Consolidate `pdf_record_reader_native.py::pdf_record_context_sql` and
`sql/pdf_record_context.sql` into one owned selection before adding payload closure. Derive
paged, streamed and scoped convenience outputs from that set, including ancestor/page-range
coverage, all endpoints, input supports and mappings. Preserve occurrences/multiplicity; do not
reschedule the already-fixed PG membership forwarding. Whole-document coverage remains context.

Propagate the existing PG-05 operation cancellation handle through selected export's raw query,
Result closure, transaction settlement and pre-publication check. Its reader-local registration
does not cover another raw query automatically. Reuse driver-specific ADBC/Psycopg ownership;
CPU decoding/native validation has separate finite cancellation. No late cancel may hit a later
borrower. State whether batches own detached buffers or borrow a live context; no lazy reader
may silently outlive its source/snapshot. Local analysis follows database-session release.

Verify one diagnostic, shuffled pages, an intact section with contained cells, cross-page content,
repeated occurrences, outside references and partial/nested coverage, plus full current export.
Exercise cancellation during selection, sink writing and immediately before rename. Native/full
and selected/analytical exports keep distinct completeness contracts. PDF-10/11 retain actual
external/provider qualification. RC12 removes mandatory old-pin reader/layout support; exact
source/raw evidence remains retained. PDF-26 remains conditional.


> **Structural target revision — 2026-11-01:** PDF-17–25 extend this series with lossless relational
> document records, versioned identity, bounded Arrow transport, private staging and atomic seal.
> See the [coordinator](../pdf-docling-pipeline_2026-10-31.md),
> [record/identity owner](relational-document-model-and-identity.md),
> [publication owner](staged-publication-and-validation.md) and
> [streaming owner](streaming-processing-and-arrow.md). Requirements below for mandatory whole
> native JSONB/canonical envelopes describe the implemented baseline, not the go-forward physical
> target. Historical receipts keep their scope. Docling logical content, evidence fidelity, intact
> sections and qualified PDF reuse remain required. PDF-26 progressive scopes are conditional.


> **Operator correction — 2026-10-31:** Historical HTML-derived output compatibility is retired
> by ADR-0040. Historical-read/replay acceptance below is superseded for HTML; retain current PDF
> source reuse and generic analytical behavior. Existing data/frozen migrations/evidence remain inert.


**Status:** Consumer mechanisms implemented and targeted-tested; current external/provider/reference journeys and assembled adoption remain open in the coordinator. **2026-10-31.**
[Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns package/O/I state.
Consumes [review O07](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O07)
and its target at `d25fff8`, with O02–05 evidence semantics supplied by PDF-13/15.
PDF-10/11 retain operational adoption and assembled qualification; this is not another acceptance ledger.

## Implemented consumer mechanisms — 2026-10-31

**Relational reader integration — Implemented, scoped Tested (2026-11-01).** Published revision
pins now gate selective node/collection/context reads and complete streamed native/integrated
exports. Native hydration and companion exports use ordered cursors; companion field parts are
decoded and verified without one query per metadata value. The same relational source-context
constructor serves Python readers and native frame guards. Source readers borrow connections
for each operation rather than share one connection across analysis workers.

Exact metadata JSON and external occurrence text survive decoding/export, including embedded NUL,
binary64 details and explicit null. Scoped formula health contains pointer/outcome and qualified
references to exact retained diagnostics. This is a governed projection, not discarded error text.
The [publication receipts](../../design_review/evidence/2026-11-01_pdf-publication-adoption/README.md)
cover selected controls. Full retained-book reconstruction/export and current CLI/external MCP,
render, source views and provider journeys remain PDF-24/25/10/11 acceptance obligations.

One selected-product reader supplies native and integrated SourceViews, frame-v3 packets, scientific
methods and current CLI/query/MCP consumers. Companions retain scoped decisions and input ancestry;
paged manifests and pin-authorized 64KiB artifact reads expose retained raw evidence. Integrated JSON
includes its companion; JSONL/Parquet carry resolvable bindings, while content-only Docling export
explicitly declares omissions. Retained reads use the qualified archived ABI/schema rather than
initializing models or comparing unrelated helper-file hashes. Historical HTML runtime/read/replay
routes and direct application-only HTML dependencies are retired under ADR-0040.

The coordinator and [integrated evidence](../../design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md)
retain the exact verification boundary. Controlled/component checks establish their selected behavior;
actual external attachment/render, five-section provider extraction, independent grading and adopted
completed-result/default selection remain PDF-10/11 obligations.

**Closeout, 2026-11-01.** The selected-document header read now avoids fetching the unused full
item JSON, with17 scoped checks passed. Shared chart provenance is inverse-transformed once per
distinct provenance object, with25 chart/reconciliation checks passed; this corrects the reproduced
page170 collapsed panel while retaining coarse precision. The0060 source-stable broad functional
baseline passed2643 tests/10warnings. The subsequent0061 guard has focused verification only.
Actual external attachment/export, five-section extraction, independent references/grading and
completed result selection remain not_run; helper/preflight readiness establishes none of them.

## Foundation and consumer boundary

Existing SourceViews, native frames, scientific M09/M11/M13, packets, query/CLI/MCP and native region
rendering already support useful pinned PDF access. Extend those boundaries to consume **one integrated
document**, not introduce provider-specific readers in each method. The Docling content graph and
mandatory companion relations form one product/reader contract; content-only Docling export is a
separately named projection. Retained reads must still avoid model initialization.

<a id="PDF-16"></a>
## PDF-16 — Migrate methods, evidence journeys and public interfaces

**Inputs:** agreed PDF-13 reader/address contracts for early design; working PDF-15 integrated products
and PDF-13 publication/ancestry for functional integration. **Output:** every active downstream consumer
uses the selected integrated contract with correct input identity and full evidence reachability.

| Consumer | Required resulting behavior |
|---|---|
| SourceView selection and preparation | Select exact integrated product plus role/scope/policy/release, preserve intact sections and direct ancestor context. No ambient latest-provider product or consumer-local merge. |
| M09/M11 scientific methods | Consume selected recognized LaTeX and its text/region precision, retain occurrence context and parse/ambiguity states; remain lazy about strong symbolic assessment. |
| M13/domain recognition | Use integrated containment, statements and table/chart context as attributed structure; headings/recognizer labels never establish semantic truth by themselves. |
| Extraction packets and proposals | Include selected rich content, health/coverage and retrievable alternatives with bound decision/source handles. Packet and dependency identity changes when selection changes. |
| Consolidation and claim evidence | Claims resolve through selected occurrence and integration decision to admitted observations and original pixels. Correlated recognizer agreement is not independent corroboration. |
| Source frames/evaluation | Bind integrated product and multi-input evidence ancestry; regenerate new independent frames from the new consumer, never relabel run6 or use extraction output as reference truth. |
| CLI/MCP/query/placement | Same typed inspection contract, explicit precision/unknown states, multi-input trace, selective source rendering and pinned continuations. No model service required for retained reads. |
| JSON/JSONL/Parquet interchange | Integrated export includes companion relations or explicit resolvable bindings sufficient for its declared contract. A content-only native Docling export advertises its omissions; no silent evidence loss. |

Extend `selected_native_ancestry` and trace reads to traverse admitted direct inputs, scoped to run,
project and selected product. Do not grant access to unrelated ambient products just because they
share an original digest. Derived item/relationship refs bind representation and archived contract.
The same selected table value can link to TableFormer geometry and generated crop text only through
an explicit correspondence; missing fine geometry stays coarse/unknown.

Model diagnostic outcomes and remediation: retry failed recognition under a named recipe, remap
retained raw output, or integrate under a named policy. Use existing CLI lifecycle operations or
extend them narrowly; do not add a separate diagnostic policy engine. A changed reconciliation
policy creates new product/frame/dependent extraction identity but reuses identical inference.
Changes in a result-neutral endpoint/cache location must not needlessly invalidate semantic results.

### Migration and preservation

Migrate all actual callers, source request types, approved implementations, dependency recipes,
current reader admission, continuation/export contracts and model-generated surfaces together.
Under RC12 preserve historical products/citations as exact evidence; mandatory historical runtime
readers are retired. Rebuilt inputs must not falsely claim dual recognition. Version changed reader/source-frame contracts explicitly.

Retain exact native OCR/word anchors and useful existing math enrichment until the integrated route
supplies their required coverage/precision. Determine overlap by consumer demand, not by keeping every
model eagerly active. Replace obsolete candidate/enrichment passes only with demonstrated replacement
and update bindings; no hidden Standard-only fallback when the selected combined route is unavailable.
Existing operational defaults remain unchanged until PDF-10 publishes a qualified completed selection.

### Local verification and integrated handoff

Exercise one intact section containing a disputed formula/table: inspect selected content and the
alternative, render original pixels, run scientific/extraction consumers, and trace a resulting claim
back through the decision and both provider inputs. Also cover repeated occurrences, partial coverage,
missing/unavailable raw evidence, wrong project/run and old citations after a new selection.
Verify integrated export preserves decision/endpoint identity and content-only export remains labeled.

CLI/component checks do not establish actual external MCP attachment. PDF-11 requires the real stdio
MCP/render journey, actual configured extraction provider and independent automated authoring/grading
on exact new frames. The prior run6 tasks/frames remain prior scoped records, not qualification of
this target. Do not complete the obsolete intermediate pipeline as a prerequisite for the integrated
journey; preserve and reuse its applicable receipts instead.

## Adoption and knowledge-outcome boundary

PDF-10 owns current-realization adoption, actual completed-result/default cutover and retired registrations;
PDF-11 owns the required functional/provider/nonfunctional union. Extend their concrete journey scope
with I13 before running providers. Full-book source execution demonstrates source/lifecycle capability,
not all-book extraction or universal transcription fidelity. Reuse already admitted Standard products
where valid; only new recognition must run. Select useful independent source challenges before seeing
results. No human grading, historical regrading, grading-policy tuning or reference leakage is included.

<a id="PDF-24"></a>
## PDF-24 — Streaming selected readers and lossless exports

**Planned, 2026-11-01.** Consumes [streaming review O06](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O06) at `1c6fc710`. PDF-16's implemented reader/consumer mechanisms remain the baseline; this package migrates them to the new [record/identity](relational-document-model-and-identity.md) and [publication](staged-publication-and-validation.md) contracts. Early interface work uses agreed PDF-18/19 schemas; acceptance needs working PDF-21 publication and PDF-23 stream production.

Extend the shared selected-product reader with selective native record/relation and Arrow batch iteration over one immutable product pin. SourceViews, M09/M11/M13, extraction packets, source frames, reference/evaluation, consolidation evidence, CLI/MCP, rendering and exports use that same authority. Reuse compatible retained evidence for current products under RC12 without requiring historical-pin runtime readers; current small reads do not initialize models. A small item query must not fetch complete native content, parse the original envelope, run symbolic work or invoke inference.

Bind cursor/continuation identity to immutable selection and contract; reject wrong pins and prohibit staging visibility, including raw-table/function bypasses. Needed scientific/ancestor context may exceed requested output scope: selective reads must not silently reduce analytical input. Keep coordinate/precision, failed/partial/unrequested coverage and evidence ancestry explicit.

Stream complete native JSON and integrated content+companions to a sink in deterministic collection/record order, hashing bytes incrementally. Avoid mandatory full `DoclingDocument.model_dump`, Python all-row lists or SQL `jsonb_agg` over the book. Explicit whole-model hydration remains available as a requested materialization with its resource cost. Native-only export declares companion omissions; integrated export preserves the complete contract. JSONL/Parquet maintain resolvable product/schema/lineage bindings. Exact retained-byte replay and value-equivalent reconstructed native JSON remain different guarantees under PDF-19.

Reuse existing ADBC exported/imported snapshot capture and `fetch_record_batch`, `CapturedPacket.iter_batches`, spooled Parquet and DuckDB readers. A separate ADBC connection does not inherit the publisher transaction; imported snapshots and pinned revisions supply consistency. Borrowed reader/buffer/spool lifetime covers the last consumer, including cancellation and abandoned iterators. Do not introduce a second reader engine or implicit `to_table`.

**Completion:** independent item/cell/reference/precision expectations, wrong-pin/staging refusal, stable continuations, native reload/tree validation on representative reconstructed content, exact original/raw retained-byte custody and complete current streamed companion inventories. Actual external stdio MCP attachment/render/export and real scientific/extraction/reference consumers belong to PDF-11's assembled union, not component-test inference. No compatibility for retired HTML output is reintroduced.

### PDF-24 library improvement integration — I06/I07/I08/I09

Consume [review I06–I09](../../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I06) at `5d7a72c4`; the coordinator owns scheduled disposition.
Use the same model-bound records for item/cell/formula/relation and source/frame context. A small
query must not hydrate the whole native document to call a convenient serializer or profiler.
Use native `iterate_items(root=..., with_groups=..., included_content_layers=...,
traverse_pictures=...)` on already demanded bounded native values; record-backed views preserve
equivalent declared traversal, multiplicity and order. Include picture-nested OCR, furniture and
groups when the view's semantics require them. HybridChunker's default picture exclusion is not
a reason to adopt chunking or silently omit recognized content.

Native `replace_item`, `delete_items`, table row operations and `validate_tree`/`validate_document`
are candidates where they actually handle required relationships. Compare with current indexed
bulk removal and pointer-preserving hierarchy organization; do not replace them with repeated
whole-document copying. `filter`, `concatenate` and subtree insertion can readdress objects.
Transformations must preserve source-qualified old citations and publish explicit new mappings;
structural validity alone cannot preserve identity or prevent normalization on read. Existing
PDF-18 callback-refusal semantics remain required.

Keep serializers' selected layers and companion omissions explicit. Retained raw responses,
recognized text/structure, normalized or postprocessed output, descriptions and derived summaries
are separately attributed. A chart value or code language is not automatically a knowledge claim.
If optional enrichment is selected, migrate its real packet/frame/evidence consumers with its
producer, rather than exposing a result only through a new local diagnostic. Existing mathematical
methods remain lazy; requested output scope must not discard necessary scientific input context.

Use ADBC exported/imported snapshots and `fetch_record_batch` for the existing columnar capture
route; for Core row queries where capture adds no value, use a closed streaming `Result` with
`execution_options(yield_per=...)` on the owning connection. Neither route inherits another
connection's transaction implicitly. Continuations bind immutable product/selection/release and
projection; iteration cancellation closes cursor/reader and retains backing files through the
last borrower. No new reader engine or double pooling is selected.

Counts and coverage diagnostics derive from records. `DocumentProfiler.profile_document` is an
explicit hydrated diagnostic, not a required reader stage; collection distribution arrays still
consume memory. Native page/reading-order visualizations are demanded artifacts. Progress events
may arrive late/out of order and cannot commit records or change authoritative completion.

**Additional completion:** nested picture OCR, missing referenced image versus absent picture,
body/furniture/group selection, rich cell/header/caption context, repeated references, ambiguous
transformation mapping and old citations after successor publication have independent expected
membership/precision. Exercise slow/abandoned reads, wrong snapshots, late callbacks and selected
export omissions. Actual external MCP/render and extraction/grading remain PDF-11 obligations.

<a id="PDF-26"></a>
## PDF-26 — Conditional progressive sealed scopes

**Conditional, not required for initial atomic-document completion.** Source: [streaming review O07](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O07); depends on I19 and working PDF-18–24 scope/publication primitives. Plan creation schedules the investigation, not automatic activation of progressive analysis.

I19 must identify an actual early-consumption workflow and a defensible closure policy for heading boundaries, membership/order, selection outcomes, required ancestor/scientific context, cross-scope references, native address mappings and coverage. End-of-page/section detection alone is not closure. If global heading inference or enrichment can still change the scope, keep it private until those dependencies close.

If justified and explicitly selected after I19, publish an immutable scope snapshot with its own admitted pin, distinct from the unfinished document's unknown final digest. It references the same document/records, not a fabricated original or semantic chunk. Named unresolved dependencies remain typed unknown/pending; consumers requiring global completeness wait. Separate structural closure from recognition/integration completeness and from completed knowledge.

Late corrections create a successor scope/product and invalidate affected dependent work through existing modeled dependencies. Never mutate cited content. External interfaces, SourceView selection and evaluator frames must share that scope authority rather than invent local partial-result interpretations. Changes beyond confirmed RC08/09 follow the existing explicit rule-decision route before activation.

**Conditional completion:** a closed section can be consumed while an unrelated section fails, a necessary late target prevents sealing, no partial book appears complete, and successors leave prior citations immutable. If I19 does not establish value/closure, record the deferral and trigger in the coordinator; do not leave this as a blocker to PDF-10/11 atomic-document acceptance.
