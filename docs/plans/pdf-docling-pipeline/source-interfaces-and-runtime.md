# Source interfaces, runtime and publication

**Status:** Planned target; no PDF implementation or qualification is claimed.
**Created:** 2026-10-31. The [coordinator](../pdf-docling-pipeline_2026-10-31.md) owns
PDF-08/09 status, investigation outcomes and review O06/O07/O08 disposition.
Consumes the [review](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O06) at
`2c33372` and its [target](../../functional_reviews/pdf-docling-pipeline_2026-10-31_target-model.md).
RC01–RC05 are operator-selected; PDF-00 owns their decision/architectural implementation route.

## Foundation assessment and intended execution shape

`serve/source.py`, `cli/source.py` and `semantic/parsing_queries.py` already provide pinned,
bounded source reads shared by CLI/MCP. Their scalar extents and canonical defaults cannot
implicitly become PDF boxes. `methods/llm/cascade.py` provides exact/normalized placement plus
RapidFuzz candidate/alignment witnesses. Reuse those algorithms where needed; document item
references can eliminate much of the ordinary search instead.

`semantic/parsing_requests.py` owns on-demand source-ready cuts, not completed/graded runs.
`semantic/operations.py`, parsing-product publication and current reuse resolution already own
attempt fences, coherent source completion and producing-task identity. Extend these mechanisms
for new products; do not add another job service, retry owner, database queue or workflow engine.
Native conversion is expensive preparation outside publication transactions, followed by short
fenced instance publication. One book, conversion, page, section, item and request are distinct
units; semantic distinctions do not mandate separate tasks or transactions for each instance.

<a id="PDF-08"></a>
## PDF-08 — Pinned source inspection, placement and exports

**Owner:** query/serve and proposal-placement integration. **Requires:** PDF-02 source-address
variants, PDF-03 indexed products, PDF-04/05 native items/hierarchy and PDF-07's proposal evidence
contract. I06 settles usable artifact/geometry fidelity; I08 identifies actual adoption journeys.
Pure read/transport design can use agreed schemas; native-read acceptance requires deployed rows.

Extend existing source `products`, `inspect`, `trace`, `export` and `request` operations and
read-only MCP `inspect_source` through the shared semantic boundary. Add typed selectors/results
for section ancestry/membership, native item pointer, formula, table/cell and PDF region. A selector
binds a conversion/build, not just an unqualified `#/texts/3` or mutable project default.
Representation/text offsets remain typed ranges; regions retain page number, bounding box,
coordinate origin and page dimensions, with multiple regions per item where supported.

Implement the SQLAlchemy Core `select`/join/predicate path over shared fixed metadata for
requested sections/items/cells. Use explicit reading-order ordinals and deterministic continuation
bindings; ordered content is not `texts[]` array order or sorting boxes by top-left coordinates.
Projection/version/release pins belong in continuation identity where they affect answers.
Retain existing ambiguous-build refusal, producing-task reuse resolution, corruption refusal and
explicit missing-capability results. Do not select the latest equal-text build or silently
reconvert a corrupt historical product during a read.

A formula inspection exposes untreated text, recognized LaTeX, recognition health, interpretation
status and PDF-region evidence together. A table-cell inspection preserves row/column/header
structure and source relationships. Region rendering is a demanded derived artifact, not a
reason to serialize all page images for an ordinary hierarchy query. Missing referenced image
payload and absence of a picture are different outcomes. I06 selects trusted artifact resolution
and supported geometry; exact recognized-text offsets cannot claim exact PDF transcription.

Keep CLI/MCP registration light: load conversion/Torch/OCR models only inside the demanded
operation. Service startup and read-only inspection must not initialize a converter, download
weights or compile all semantic inputs. Use existing typed caller-refusal versus database
retry/fencing/defect boundaries; cancellation and programming failures preserve their identity.
Actual MCP acceptance includes fresh external stdio registration and multiple pinned tool calls,
not just a method invocation or mocked provider.

Carry source item/cell/formula references from the packet into proposals and place them directly
against the immutable selected product. Keep exact/normalized text and RapidFuzz
`extract_iter`/`partial_ratio_alignment` plus edit witnesses only as needed within an explicit
section/item candidate universe. Preserve ties, ambiguous selection, failed placement and
normalization distinctions; a convenient match is not evidence that an unseen global search
was complete. No ordinary full-book fuzzy recovery or fuzzy cross-build identity is introduced.

Derive Arrow batches/Parquet exports from the same declared item/table projections. Preserve
conversion pointer, section, geometry, original lexical spelling and null/absence distinctions.
DuckDB can query those analytical projections for concrete consumers; it does not become a
second editable document authority. Reuse existing streaming/spooled export lifetime, no-overwrite
and partial-output behavior. No separate graph projection or new analytical engine is selected.

**Acceptance:** actual CLI and external MCP journeys inspect a section, formula, cell and region;
traces resolve to the retained PDF/conversion. Competing builds require selection, stale/wrong
pins refuse, partial coverage stays partial and bounded reads do not transfer whole-book JSON.
Exports preserve ordered relationships, occurrence multiplicity and lexical numeric precision.
Direct placement consumes the real packet reference; fuzzy fallbacks retain independent witnesses.

<a id="PDF-09"></a>
## PDF-09 — Owned conversion execution and coherent publication

**Owner:** orchestration/native-operation integration. **Requires:** PDF-02 admitted behavior and
lifecycle, PDF-03 native persistence, PDF-04 converter and health results, PDF-05 derived products;
I01 runtime compatibility and early I07 lifetime constraints. I07 full-book evidence finishes
with this package before adoption; it does not block constructing the first owned converter.
PDF-06/07/08 integrate incrementally
once their required products are available, rather than form a mandatory global preparation barrier.

Own the converter/model resources at the existing worker/operation lifetime. `StandardPdfPipeline`
already provides bounded stage queues and batching. Coordinate `PdfPipelineOptions.ocr_batch_size`,
`layout_batch_size` and `table_batch_size` with parser/inference threads and GPU allocations;
these are independent controls, not multipliers to maximize simultaneously. Inspect actual
`ThreadedDoclingParseBackendOptions.parser_threads`, `max_concurrent_results` and
`release_native_memory_every_n_pages` behavior under the selected backend before assigning limits.
Do not add a nested document-level pool or recreate native stage scheduling without a demonstrated
failure/throughput need. Batches do not create document chunks or change section boundaries.

For the 1,589-page source, assess the combined live set: native parser/page backends, formula
crops, rendered images, model caches, conversion result, native JSON, access projections and
publication transport. Formula enrichment can retain backends even when retained page images
are disabled. `InputDocument.release()` and supported native cleanup belong after the last
required use; releasing a document is not a promise to unload cached model/GPU memory.
I07 must establish a credible whole-book route; cancellation limits alone do not establish one.

Archive package versions, model revisions/content, OCR language/options, layout/formula/table
presets, serialization/grouping recipes, actual execution providers/device and relevant source
implementation artifacts. A model repository named `main`, an accelerator set to CUDA, or an
unchanged package pin does not establish identical execution. Native inference is not declared
byte-deterministic without evidence; immutable actual outputs retain their own identities.

Reuse successful conversion and derived products by complete dependencies. Section/item
inspection reuses conversion rather than repeat inference. Mathematical requests reuse compatible
products by formula/context/demand; conversion readiness does not force symbolic work. Share
prepared native state only within its declared lifetime, not through serialized live handles.
Use existing durable request/state mechanisms only where recovery or consumer behavior needs them.

Complete native computation privately, then publish immutable original/specification/document,
health and required derived products under the existing run/task attempt and source fences.
PDF-03 supplies native custody/invariant enforcement; this package integrates atomic visibility,
replay and conflict recovery. The old active result remains coherent until a qualified replacement
is selected. Partial or failed conversion may retain diagnostic products but cannot satisfy a
required complete-result contract. Conversion success, source-ready cut, completed knowledge
run and persisted independent evaluation are distinct states.

Cancellation stops/drains owned work and prevents late/stale attempts from publishing. Retry
has one application owner: it repeats the failed necessary unit and reuses successful immutable
work. A caught formula-enrichment failure cannot be retried implicitly during serialization,
normalized away into success, or hidden by broad document completion. State guards consume
admitted model contracts rather than independent handwritten stage classifications.

Do not split the PDF into arbitrary page-range conversions and assume concatenation preserves
full-book hierarchy, cross-page text/table relations or identical item pointers. A page-range
probe is a partial product with declared scope. Section chunking is excluded; an observed actual
oversized-section failure returns to the coordinator as a future decision, not an automatic
runtime fallback.

Conditional independent OCR verification uses an explicit demanded region and attributable
recognizer/configuration/alignment evidence. Preserve competing strings and resolution outcomes;
no multi-engine voting or new universal reconciliation framework is part of ordinary execution.
An accepted correction creates a new derived document and does not mutate the retained conversion.

**Acceptance:** native source completion/replay, restricted publication, stale attempt/source
fencing, cancellation and failure recovery preserve coherent selected products. Full-book source
conversion is separately exercised after representative cases, with no inference on ordinary
reads and no hidden stronger math. Failed/partial attempts and unsupported recognition stay
visible. PDF-11 owns assembled qualification and applicability of these receipts.

## Sources and scope boundaries

Mechanisms come from review O06–O08 and tagged
[standard pipeline](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/standard_pdf_pipeline.py),
[backend options](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py),
[pipeline options](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py),
and local [SQLAlchemy](../../libraries/sqlalchemy.md), [PyArrow](../../libraries/pyarrow.md),
[DuckDB](../../libraries/duckdb_2.md), [FastMCP](../../libraries/fastmcp.md),
[Typer](../../libraries/typer.md), [RapidFuzz](../../libraries/rapidfuzz.md) and
[concurrency guidance](../../libraries/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md).
I01/I06/I07 qualify unresolved runtime/API details. These packages promise no measured speedup,
universal recognition coverage or full-plan qualification. No production tests, model downloads,
conversion, database changes or dependency changes were performed during plan authoring.
