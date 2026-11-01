# Streaming PDF processing and Arrow execution

**Status:** Planned, 2026-11-01. [Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns PDF-22/23 and I14/I18/I20. Basis: [review O03/O04](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O03), [target §§5–6](../../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) at `1c6fc710`. [PDF-18–21](relational-document-model-and-identity.md) own record/identity and [publication contracts](staged-publication-and-validation.md).

## Library improvement basis and readiness

[Improvement review](../../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md) at `5d7a72c4` supplies I01–I11. This revision schedules
I01/02/03/05/06/08/09, I07's shared lifetime foundation and I11's corrected table premise;
additional recognizers and I10 caches remain conditional. The coordinator alone owns disposition,
I14/I18 and new I20. Source-inspected library seams are not delivered producer behavior.

Early I14 native finalization and I20 scheduler/custody decisions shape the producer interfaces
before substantial implementation. PDF-20 may proceed against agreed source/replay/record contracts;
actual publication acceptance still requires working producers and consumers. These are prerequisite
slices, not a requirement to finish all experiments before useful storage work. No new rule change
is selected: retain ADR-0042, full document semantics, alternatives and phase-sequential GPU ownership.

## Outcome and physical assessment

Separate bounded page processing from required global semantic finalization. Stream and retain heavy results as typed records; keep compact cross-page state and explicit deferred references. A generator, bounded page queue or batch COPY does not establish bounded whole-operation memory. No semantic section splitting is planned.

Installed Docling2.145/core2.105 StandardPdfPipeline already queues page stages but retains page results, then aggregates elements for reading order and hierarchy before enrichment. Existing `pdf_recognition.py::_parallel_pages` already bounds Nemotron page futures and durably retains outcomes. Existing `pdf_reconciliation.py::select_pdf_integration` uses page-local candidate indexes but builds the whole selected graph and companion collections. `analytics.py`/`capture_storage.py` already supply selective/spooled analytical readers; extend those foundations rather than add another engine.

<a id="PDF-22"></a>
## PDF-22 — Bounded Standard assemblies and native-equivalent finalization

**Input:** early PDF-17/I14 source investigation, agreed PDF-18/19 assembly/record contract; working PDF-20 for durable integrated storage. **Output:** owned Standard/RapidOCR producer adaptation, retained assemblies/crop custody and qualified global finalization.

Start with I14, before freezing dependent producer interfaces. Inspect exact native stage, reading-order, heading and enrichment implementations. Preserve cross-page paragraph merges, dehyphenation/charspans, caption/footnote attachment, list structures, document-wide numbering/bookmark/style inference and item order. Reuse native heading-relevant retained parsed lines rather than holding every parsed glyph when unnecessary. Page ranges followed by `DoclingDocument.concatenate` are not assumed equivalent.

Prefer one narrow pinned pipeline adapter using supported pipeline-class injection and native models. Any necessary private page-output/result-integration seam is confined to that adapter and tested against the exact version. `convert_all` yields documents; a progress callback reports progress, not a page payload. Do not invent a public per-page document API. Required provider/API changes are implementation prerequisites, not silent fallback behavior.

Persist/spool page assemblies and exact required crop/image custody, release heavy parser/backends after last required use and run global inference over the least sufficient state. Some enrichment occurs after document assembly and needs earlier page imagery. Either retain bounded required crops or re-render under an exact source/frame recipe. Moving inference earlier requires evidence that item selection, geometry, ordering/batching and attachment preserve meaning. Releasing all images at page completion is not correct by default.

Use one retained seekable source/spool and incremental byte custody where supported; PDF input is not presumed decodable from incomplete forward-only bytes. Avoid repeated full original byte strings across child/process boundaries when the backend can use an owned file. Define child/source/spool lifetimes under existing cancellation and claim-loss behavior.

Initial residual compact global state may grow with document structure. If full graph hydration remains necessary, name its supported boundary and required remedy in I14; do not close strict bounded end-to-end streaming on that basis. A private-seam adapter or smallest upstream extension is preferred to a bespoke replacement of native algorithms. Storage/reader work can proceed against agreed contracts while the exact producer integration is resolved; assembled acceptance cannot conceal that unresolved prerequisite.

### Concrete native finalization and capacity contract — review I01/I02

Use installed Docling2.145 `StandardPdfPipeline._release_parsed_page` →
`HeadingHierarchyModel.retain_parsed_lines` as the compact heading-input seam.
`assign_heading_levels(document, parsed_pages, outline)` preserves bookmark → numbering → style
precedence. Retain lines for list items bookmarks may promote, not only already labeled headings.
Spool page `AssembledUnit` content with order, dimensions, separators, container children,
text/geometry and rich-table associations needed by `ReadingOrderModel.__call__`.
Do not replace its caption/footnote/cross-page maps with coordinate sorting. Both native methods
still consume global structures; I14 must identify the remaining graph requirement and the smallest
pinned adapter/upstream seam needed to replay it. A compact input is not a proof of bounded output.

Separate parser CPU threads from decoded-result prefetch in the existing versioned recipe.
Resolve `ThreadedDoclingParseBackendOptions.max_concurrent_results`, `render_scale`,
`release_native_memory_every_n_pages` alongside `queue_max_size`, OCR/layout/table batch sizes
and downstream retained batches/crops. Keep existing defaults until a deliberate choice is justified;
do not invent numeric limits from this plan. Record effective options and capacity ownership,
including native/Arrow thread pools and scanner readahead. A blocked spool/database consumer must
constrain ready-output admission. Preserve the actual pixel/frame recipe when reusing renders;
parser render scale, OCR scale and output image scale are different controls.

### Owned source, crop and output lifetime — review I05/I07

Replace `ConvertRequest.original` and ordinary whole-`PdfConversion` IPC with an immutable,
digest-bound seekable source capability and bounded record/replay descriptors. The capability
binds source bytes, authorized owner and source/frame recipe; a mutable path alone is insufficient.
Acquire/verify the source before native work, retain it through deferred crop/enrichment demand,
and release it after the last borrower. Children remain DB-free; PDF-20 owns durable private
record/artifact adoption. A crashed child leaves resumable authenticated progress and required
failure evidence, not an implicitly published partial book.

Extend the existing `PdfRegionRenderer` and formula-specific lifetime policy to cover all admitted
crop consumers. Reuse exact retained crops or render under their explicit recipes; the existing
renderer has fixed0.75-point padding whereas native formula preparation uses different expansion.
Do not substitute one silently. `result.input.release()` already exists and does not unload cached
models; no work item adds it again. Define image/backend/spool ownership through cancellation,
claim loss, delayed demand and abandoned consumers. This shared foundation is required even while
extra recognizers remain disabled.

Keep existing inline/cell capture and qualified text-range mappings through global paragraph/address
finalization. New enrichment outcomes bind input product/occurrence, frame, implementation/options,
coverage and raw evidence in the release-owned operation/type model. Apply transformations before
freeze or create successor products; cited snapshots never change. Native schema upgrades must
update mapping, callback obligations and archived implementation bindings together. No registry,
new workflow engine or untyped metadata authority is introduced.

`BaseEnrichmentModel.is_processable` and batched invocation are enabling mechanisms for demanded
stages, not a universal eager pass. Conditional code recognition can reuse `CodeFormulaVlmModel`
with typed code text/language outcomes; picture interpretation and alternate table/chart stages
need an actual selected consumer or precision gap first. Preserve current inline/cell capabilities;
a display-formula or chart result does not prove their replacement. The coordinator records optional
activation, and PDF-24 owns any new consumer's actual migration.

I11 corrects the OCR addendum: `do_cell_matching=False` uses backend text in pinned V1/V2 branches,
not independent visual transcription. Keep the matching baseline; any selected table comparison
must include OCR-only scanned cells, broken native text, merged cells and geometry. Retain both
results and actual text-source attribution rather than claiming a symbol-recognition repair.

**Completion:** independently expected cases for cross-page paragraphs, headings, captions, footnotes, repeated provenance, cell/formula enrichment and reference mapping; differential native behavior over bounded representative inputs. Cancellation, phase shutdown and required crop retention/re-render outcomes are explicit. Then replay retained book structure to assess the real remaining global working set; do not infer memory bounds or speed from queue configuration.

<a id="PDF-23"></a>
## PDF-23 — Incremental Nemotron reconciliation and shared Arrow execution

**Input:** PDF-18/19 agreed model/identity, I18 execution/type profile, working PDF-20 admission; PDF-22 finalized Standard records for assembled acceptance. **Output:** finite recognition/reconciliation stage graph producing qualified record streams rather than an accumulated book envelope.

Retain public Nemotron true A page parse/B layout/C union Table–Chart crop interpretation. Preserve raw/full HTTP outcomes, exact submitted images, frames, prompts, seed/effective decoding, primary/recovery recipes and valid zero-C states. Reuse finite page workers; public HTTP `parse_many` eagerly prepares its input and the reference driver gathers whole passes. Bounded input groups are necessary even if upstream calls are labeled batches.

### I20 — Scheduler qualification and bounded admission — review I03/I04

The current worker already uses
`DocumentParser(merge_policy="alternatives").parse_triple(..., triple_regions="union")`.
Investigate public `prepare` + `parse_prepared(schedule="pipelined")` first, inside a finite owned
child and byte-aware bounded physical page group. The pinned3.5.0.post7 implementation eagerly
prepares inputs and returns accumulated group results; never pass the whole book. Qualify a shared
A/B/C request window, stable `(page, stage, crop)` correlation, exact submitted images and full HTTP
outcomes retained before later failures, and bounded terminate/join/kill settlement. Current mutable
`backend.crop` and process-global serial observers cannot be reused concurrently unchanged.

I20's decision output names the selected route, versioned recipe, receipt seam, failure/retry unit
and acceptance evidence. Prefer a narrow public/upstream observation seam over copying the scheduler.
If that seam cannot preserve the contract, implement completion-driven page replenishment in the
existing finite workers. `_parallel_pages` currently waits on the oldest future before refilling;
stage completed pages without letting a slow predecessor leave capacity idle or accumulate an
unbounded ready backlog. Physical completion order is independent of frozen membership/order.

Default batch HTTP crops use prepared JPEG; the custom backend receives decoded PIL crops, while
current custody submits JPEG95-then-PNG. Preserve that recipe or explicitly version a changed one.
Changed bytes/settings cannot reuse prior recognition as equivalent. Retained outcomes remain valid
under their old pins. Successful batch metadata cannot replace interrupted request history.

Do not substitute upstream Docling native multipass: it is not installed2.145 functionality and has
staged execution, guarded merge, optional-failure tolerance and different sampling/evidence semantics.
Keep it in the coordinator's conditional choices until a separately selected contract can support it.
No scheduling change may silently drop alternatives or turn an unsuccessful detector/crop into
complete recognition. Reuse valid zero-C outcomes distinctly from failures.

Preserve pinned reference add-only crop insertion, then guarded replacement, then deduplication/repair; a crop may participate in both stages. Repository content selection remains separately governed policy with alternatives preserved. Adaptation must not turn the reference sequence into exclusive replace-or-add logic or correlated recognition into independent evidence.

Reconcile page-local candidates and emit decisions/occurrences/relations incrementally. Keep qualified deferred links and only required cross-page indexes. Resolve headings/references under explicit global finalization; no mutable native pointers escape publicly before address mapping freezes. Replace `_selected_occurrences`/companion list construction and `publication_payload` whole-book transport with their PDF-18/19 record realization. Shared policy/comparison context becomes qualified references while per-occurrence decisions remain independent.

Use schema-bound `RecordBatchReader.from_batches` for stage handoffs and readers, Arrow compute for suitable batch-local predicates/projections, Acero `Declaration.to_reader` for supported compositions and existing DuckDB views/readers for eligible global relational operations. An Arrow `Table`, `read_all` or `to_pylist` is explicit requested hydration, not a required streaming stage. PDF-20 removes the old `AppendPublication` full-table freeze/canonical-body requirement; changing only its COPY loop is insufficient.

Select IPC `new_stream/open_stream` for sequential movement and IPC file `new_file/open_file` with `memory_map` for seekable replay. Arrow C Stream is in-process interoperability, not interprocess transport; owned IPC/spool paths cross processes. Incremental `ParquetWriter.write_batch`, `ParquetFile.iter_batches` and Dataset scanner `to_batches` reuse existing durable capture for compressed selective scans. Avoid redundant permanent IPC+Parquet copies without actual consumers.

I18 must establish exact native/Arrow/pgpq/PostgreSQL type profiles. Preserve presence/null/empty distinctions, lexical decimals, timestamp semantics, multiplicity and order. Flatten unsupported arbitrary nested wire structures into model-owned child rows, not lossy strings. Buffer slices may retain larger allocations; keep each source/mmap/reader alive through its last borrower and release it deliberately. Arrow allocator bytes exclude GPU/parser/mmap/other process state.

Do not route external sorting through Acero order-by, which accumulates input without larger-than-memory support. DuckDB spilling is operator-specific: streaming result delivery and `memory_limit` are not strict total-memory guarantees; giant `list`/`string_agg` is not structural document assembly. Prefer ordered producers or eligible external SQL sorts under the existing scratch/memory controls.

Default device scheduling remains phase-sequential durable progress: Standard finishes/releases CUDA ownership before Nemotron wakes. Compare interleaved page groups only for demonstrated benefit with correct shared capacity/model lifetime. Bound the combined decoded pages/crops, queued outputs, retained batches, workers, model/backend state, connections and spool usage. Row limits alone are insufficient. Spool exhaustion, corrupt files, cancellation and abandoned readers need explicit owned cleanup/refusal; protective limits cannot substitute for a feasible normal-book path.

**Completion:** retained-record logical identity and replay are invariant under physical batch grouping and delivery order; no required full-book table/JSON handoff remains. Independently expected decisions preserve raw alternatives and native pointers through final mapping. Test finite pending work, disk failure, retained buffer ownership, exact retry and phase cancellation. Reuse actual retained recognition for integration; new source inference is run only when the producer contract changes or actual composed producer acceptance requires it. New VLM inference is not assumed batch-invariant merely from a fixed seed; changed outputs retain their actual recipe/custody identities. Quantitative resource/performance claims need representative end-to-end measurements; no arbitrary SLA or estimator is added.

### Additional composition and acceptance obligations — review I06/I09/I10

Use `record_arrow_schema` and prepared boundary adapters as the shared wire definition. Apply batch
projection/predicates where semantics permit; include Dataset `batch_readahead`, `fragment_readahead`
and backing-buffer lifetime in the recipe's composed execution profile. Do not require resident
`Table` construction, whole-native serialization or all-row Python sorting between stages.

Represent raw response, finish reason, partial/error/zero-C state, effective generation settings,
usage availability, parsing and postprocessing as connected request/operation outcomes. Store page
metadata as bounded rows/parts, not a growing `body.meta.docling__nemotron_parse.pages` JSONB object.
Completion is not transcription confidence; optional token/logprob information is not calibrated
accuracy. `allow_partial` is not recovery. Preserve raw predictions before `postprocess_document`
or rendering, and independently retain failed-stage evidence.

Progress callbacks are observational, may run concurrently and may ignore raised exceptions. Route
them to existing logging consumers, never admission, page payload delivery or cancellation authority.
Use native visualizations on demand. Cheap counts come from records; native `DocumentProfiler`
hydration is explicit. Its collection mode retains distribution arrays even when individual results
are excluded, so it is not a constant-memory reducer.

I10 decoded/prepared image reuse and vLLM multimodal processor caching remain conditional on an actual
supported Nemotron/plugin path and demonstrated avoided work. A stable media key binds content,
frame and processor recipe; eviction falls back to retained bytes, never a missing-evidence success.
Do not add a book cache, interleaved device ownership or a serving service as a prerequisite.

Extend local controls with slow-output/high-resolution skew, bookmark list promotion, cross-page
attachments, late enrichment after parser release, out-of-order/failed A/B/C, concurrent crops,
spool exhaustion, source replacement and abandoned readers. Compare native behavior and independent
expected semantics separately. I14/I20 report actual limits and decisions; no source-only result
closes strict streaming or changes optional PDF-26. Quantitative claims require representative
measurement after structural integration, not arbitrary performance gates.

## Sources and handoff

[PyArrow](../../libraries/pyarrow.md) §§2/4–9/14, [DuckDB](../../libraries/duckdb_2.md), [Docling](../../libraries/primary_intake/docling.md), [OCR](../../libraries/primary_intake/docling_ocr.md), [triple-pass reference](../../libraries/primary_intake/docling_nemotron_triple_pass_reference.md) §§7/9/12/14 and the review's pinned/primary-source map provide the concrete mechanisms. Follow Context7 then exact installed/primary source for implementation uncertainties. PDF-24 consumes the same reader/record contract; PDF-25 and PDF-10/11 own retained-book migration, actual journeys and final qualification. Package-local checks are targeted, not recurring integrated campaigns.
