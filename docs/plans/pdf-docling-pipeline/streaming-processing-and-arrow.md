# Streaming PDF processing and Arrow execution

**Status:** Planned, 2026-11-01. [Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns PDF-22/23 and I14/I18. Basis: [review O03/O04](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O03), [target §§5–6](../../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) at `1c6fc710`. [PDF-18–21](relational-document-model-and-identity.md) own record/identity and [publication contracts](staged-publication-and-validation.md).

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

**Completion:** independently expected cases for cross-page paragraphs, headings, captions, footnotes, repeated provenance, cell/formula enrichment and reference mapping; differential native behavior over bounded representative inputs. Cancellation, phase shutdown and required crop retention/re-render outcomes are explicit. Then replay retained book structure to assess the real remaining global working set; do not infer memory bounds or speed from queue configuration.

<a id="PDF-23"></a>
## PDF-23 — Incremental Nemotron reconciliation and shared Arrow execution

**Input:** PDF-18/19 agreed model/identity, I18 execution/type profile, working PDF-20 admission; PDF-22 finalized Standard records for assembled acceptance. **Output:** finite recognition/reconciliation stage graph producing qualified record streams rather than an accumulated book envelope.

Retain public Nemotron true A page parse/B layout/C union Table–Chart crop interpretation. Preserve raw/full HTTP outcomes, exact submitted images, frames, prompts, seed/effective decoding, primary/recovery recipes and valid zero-C states. Reuse finite page workers; public HTTP `parse_many` eagerly prepares its input and the reference driver gathers whole passes. Bounded input groups are necessary even if upstream calls are labeled batches.

Preserve pinned reference add-only crop insertion, then guarded replacement, then deduplication/repair; a crop may participate in both stages. Repository content selection remains separately governed policy with alternatives preserved. Adaptation must not turn the reference sequence into exclusive replace-or-add logic or correlated recognition into independent evidence.

Reconcile page-local candidates and emit decisions/occurrences/relations incrementally. Keep qualified deferred links and only required cross-page indexes. Resolve headings/references under explicit global finalization; no mutable native pointers escape publicly before address mapping freezes. Replace `_selected_occurrences`/companion list construction and `publication_payload` whole-book transport with their PDF-18/19 record realization. Shared policy/comparison context becomes qualified references while per-occurrence decisions remain independent.

Use schema-bound `RecordBatchReader.from_batches` for stage handoffs and readers, Arrow compute for suitable batch-local predicates/projections, Acero `Declaration.to_reader` for supported compositions and existing DuckDB views/readers for eligible global relational operations. An Arrow `Table`, `read_all` or `to_pylist` is explicit requested hydration, not a required streaming stage. PDF-20 removes the old `AppendPublication` full-table freeze/canonical-body requirement; changing only its COPY loop is insufficient.

Select IPC `new_stream/open_stream` for sequential movement and IPC file `new_file/open_file` with `memory_map` for seekable replay. Arrow C Stream is in-process interoperability, not interprocess transport; owned IPC/spool paths cross processes. Incremental `ParquetWriter.write_batch`, `ParquetFile.iter_batches` and Dataset scanner `to_batches` reuse existing durable capture for compressed selective scans. Avoid redundant permanent IPC+Parquet copies without actual consumers.

I18 must establish exact native/Arrow/pgpq/PostgreSQL type profiles. Preserve presence/null/empty distinctions, lexical decimals, timestamp semantics, multiplicity and order. Flatten unsupported arbitrary nested wire structures into model-owned child rows, not lossy strings. Buffer slices may retain larger allocations; keep each source/mmap/reader alive through its last borrower and release it deliberately. Arrow allocator bytes exclude GPU/parser/mmap/other process state.

Do not route external sorting through Acero order-by, which accumulates input without larger-than-memory support. DuckDB spilling is operator-specific: streaming result delivery and `memory_limit` are not strict total-memory guarantees; giant `list`/`string_agg` is not structural document assembly. Prefer ordered producers or eligible external SQL sorts under the existing scratch/memory controls.

Default device scheduling remains phase-sequential durable progress: Standard finishes/releases CUDA ownership before Nemotron wakes. Compare interleaved page groups only for demonstrated benefit with correct shared capacity/model lifetime. Bound the combined decoded pages/crops, queued outputs, retained batches, workers, model/backend state, connections and spool usage. Row limits alone are insufficient. Spool exhaustion, corrupt files, cancellation and abandoned readers need explicit owned cleanup/refusal; protective limits cannot substitute for a feasible normal-book path.

**Completion:** stage output/replay is invariant under batch grouping and delivery order; no required full-book table/JSON handoff remains. Independently expected decisions preserve raw alternatives and native pointers through final mapping. Test finite pending work, disk failure, retained buffer ownership, exact retry and phase cancellation. Reuse actual retained recognition for integration; new source inference is run only when the producer contract changes or actual composed producer acceptance requires it. Quantitative resource/performance claims need representative end-to-end measurements; no arbitrary SLA or estimator is added.

## Sources and handoff

[PyArrow](../../libraries/pyarrow.md) §§2/4–9/14, [DuckDB](../../libraries/duckdb_2.md), [Docling](../../libraries/docling.md), [OCR](../../libraries/docling_ocr.md), [triple-pass reference](../../libraries/docling_nemotron_triple_pass_reference.md) §§7/9/12/14 and the review's pinned/primary-source map provide the concrete mechanisms. Follow Context7 then exact installed/primary source for implementation uncertainties. PDF-24 consumes the same reader/record contract; PDF-25 and PDF-10/11 own retained-book migration, actual journeys and final qualification. Package-local checks are targeted, not recurring integrated campaigns.
