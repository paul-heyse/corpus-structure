# Specialist extensions and scale

**Investigation dispositions and reopen conditions · 2026-11-08.** Companion to the [Chandra coordinator](../chandra-2-post-nemotron_2026-11-08.md). CH-09 adds attributed evidence delivery. This document owns the capability-specific limits and the conditions for stronger specialist products.

<a id="CH-05"></a>
## CH-05 · Chart values and diagram edges

**Chart consumer (O03).** Investigate an opt-in proposal read that lets a researcher inspect panel and series identity, axes, units and individually sourced values. Preserve author-supplied data, printed values and graphical estimates separately. The authored chart fixture has 60 printed and 40 and 30 visually inferred. Its child table supplies all three with identical standing. Test multi-panel, scale, direction, labels, series and units against independent source expectations. Include p301 and p334 as description cases where a plausible point series would be unsupported. A graph-read value remains an estimate even when it matches a hidden fixture value.

Compare the Chandra child `TableItem` with existing Nemotron chart evidence and the existing picture-addressed `PictureMeta.tabular_chart` read. Granite's `_needs_prompt` skips `<chart2csv>` when that metadata exists, while `<chart2summary>` can skip on a short existing alt description. Use one field-specific completion decision. If a demanded field lacks retained evidence for a supported bar, pie or line chart, compare `ChartExtractionVlmEngineOptions.from_preset("granite_vision_v4", chart2csv=True, chart2summary=False, chart2code=False)` on the qualified picture. Gate it before the stage because its presence checks do not see the nested Chandra table. Retain the provider CSV before `_extract_csv_to_dataframe` and `_dataframe_to_tabledata` infer scalar types and header roles. Retain child table and picture identity. Check a dual representation with both a nested table and chart metadata to prevent duplicate projection or numeric authority. [Granite preset](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/chart_extraction_options.py#L39-L146) · [CSV conversion](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/chart_extraction/granite_vision.py#L337-L412) Reopen delivery when a typed read and export preserve value standing, panel ownership and source locations without duplicate extraction or ingestion as ordinary text. [Picture mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L729-L783) · [Granite field selection](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/chart_extraction/granite_vision.py#L116-L143)

**Diagram consumer (O05).** Investigate the question “Which printed branch leaves this node?” using the authored three-edge diagram and a natural PDF with independently verified branches, labels and repeated or ambiguous connectors. Retain generated Mermaid as attributed code under the located picture. The natural NIST controls misdirect a return edge and collapse two parallel arrows. Treat the candidate as text in the current scope. Assess parsing a bounded supported syntax into candidate nodes and directed edges, and using the existing graph tools for source-scoped traversal once the edges are qualified. Separate syntax validity from visual fidelity. Validate endpoints, direction, labels, multiplicity and ambiguous branches independently. Inspect original pixels for each returned edge and keep process or causal interpretation with its domain owner. On vector pages, consider docling-parse `ContentConfig.shapes_content_level=COMPUTE_AND_MATERIALIZE` for path candidates. Prove clipping, arrowheads, frame transforms and connector identity before treating paths as witnesses. [Native shape materialization](https://github.com/docling-project/docling-parse/blob/v7.24.2/docling_parse/pdf_parser.py#L688-L720) Reopen delivery only when the graph query preserves those witnesses and role distinctions. [Chandra layout prompt](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/prompts.py) · [Docling picture mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L729-L783)

<a id="CH-06"></a>
## CH-06 · Visual form state, molecular evidence and navigation

- **Forms (O06).** Compare visible values and checkbox or radio states with independent PDF widget identity and `/V` and `/AS` readings on a native interactive PDF, and with a scanned form. Include ambiguous label/value placement. In the live control, BX-71 and the marks were correct while widget identity and label associations were absent. Chandra's standalone PDFium loader flattens annotations for visibility. Docling can retain generated form items, but its visual radio and checkbox inputs map to the same selected/unselected labels and a mark can have empty text. Preserve raw control kind as attributed evidence and use the native Docling Parse widget path for native state. Reopen a typed form reader when it preserves native and visual state separately and shows unresolved associations. [Native input loader](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/input.py) · [Pinned HTML parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py)
- **Chemistry (O06).** Use the successful propan-2-ol fixture and a natural structure with an independently checked source, including an ambiguous or multiple-structure case. The parser maps a single `<chem>` element to `PictureMeta.molecule`. An output string supports an attributed molecular candidate. Compare structural equivalence, connectivity and stereochemistry when relevant before any stronger acceptance. Reopen a reader once a qualified candidate can be inspected with source pixels and unsupported children remain visible as such. [Pinned molecular mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L729-L783)
- **Navigation (O07, O02 discovery).** Check representative born-digital, scanned, natural handwritten, multi-column and multilingual PDFs. Compare literals, RTL order, outline and contents, nested lists, bibliography, code, footnotes and native links. The authored language fixture is evidence for typed script recognition and ordering. It uses a script font and does not qualify actual handwriting. Compare native text and PDF annotations before substituting a visual reading. Defer page-local normalization and use the document-wide owner. The joined h1/h2 fixture preserves levels that a lone h2 loses. Test the actual discovery path, since current text search uses English configuration. Reopen changes when the intended language and structure survive through a source-qualified query or packet. [Docling VLM assembly](https://github.com/docling-project/docling/blob/v2.148.0/docling/pipeline/vlm_pipeline.py) · [Current search](../../../python/corpus-structure/src/corpus_structure/serve/source_search.py)

Each capability gets a separate disposition and identifies the natural-source, consumer or semantic proof still missing. An unavailable representative case leaves that capability conditional.

<a id="CH-07"></a>
## CH-07 · Decide whether to expand runtime and routing

The original workload supports explicit requests. The [CH-10 package](automatic-routing-and-qualification.md#CH-10) owns the post-publication evaluator, managed grouping, comparison and activation criteria. Use real demand from CH-03 and the consequences seen in CH-04–06 to compare explicit requests, selective routing, and routine all-page recognition. Prefer existing incumbent observations for selection signals. Compare missing typed content, failed or incomplete recognition, disagreement and a requested visual capability against source truth and clean controls. Check both useful discoveries and routing misses. Preserve full-page context where captions or hierarchy matter and compare a crop only when effective resolution or rotation could change the result. An all-page proposal needs a representative source inventory and independently assessed benefit over targeted requests. The 20-case panel does not qualify prevalence, all-page capacity or production gain.

Compare model lifetime, shared GPU handoff, retained work reuse, page preparation, intermediate size and failure recovery. Start with CH-02's single local reference runtime. Test ordinary batching before MTP if there is demonstrated throughput demand. For an independent local server, examine `ApiVlmEngineOptions`, the actual endpoint and served model alias, input normalization and retry or stop semantics. Require equivalent meaning and retained attempt identity before allowing reuse across runtimes. Compare Docling's native multipass batching separately from Chandra and retain incumbent A/B/C receipt and decision custody. [Pinned engine options](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/vlm_engine_options.py) · [Chandra vLLM launcher](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/scripts/vllm.py) · [Native retry](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/model/vllm.py)

Classify MLX as a separate quantized artifact and Ollama or LM Studio as separate API profiles. Chandra CLI/app can support troubleshooting. Consider Docling Serve or Jobkit only for a demonstrated multi-client or scheduling need. Hosted Chandra 2.5 has a separate structured figure schema and service boundary. Evaluate it only under separately selected scope and data-handling authority. Record an adoption, retention or defer decision for the actual workload. Carry any quantitative comparison with its workload, hardware, effective runtime, and measured boundaries. [Docling preset engine variants](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/stage_model_specs.py) · [Docling Serve](https://docling-project.github.io/docling/usage/api_server/deployment/) · [Docling Jobkit](https://docling-project.github.io/docling/usage/jobkit/) · [Hosted 2.5 release](https://www.datalab.to/blog/chandra-2-5)

### Runtime follow-up · 2026-11-08

The resident Nemotron service's vLLM 0.26.0 level-one sleep and wake worked during the
two-page Chandra CUDA group. During the fresh Standard run's subsequent protected
publication, its `/metrics` reported zero running requests, zero waiting requests,
and zero generated tokens in the sampled service lifetime. The observed wait was
Standard's protected metadata publication while its outer GPU lease remained held.
The retained-only A/B/C replay releases that dependency for the comparator's CPU work.
[Grouped device and handoff evidence](../../design_review/evidence/2026-11-08_chandra-execution/records/chandra.grouped-development.json) ·
[Versioned vLLM sleep contract](https://docs.vllm.ai/en/v0.26.0/features/sleep_mode/) ·
[vLLM metric definitions](https://docs.vllm.ai/en/stable/usage/metrics/)

The observed Standard handoff couples the native child lifetime to the later
frozen-build validation. Investigate moving the handoff into the existing native
worker context so it restores Nemotron after child teardown and before frozen
validation. Qualify that change with a real provider handoff and the same protected
publication and retry controls.
[Standard handoff owner](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_methods.py) ·
[Native worker and protected publication](../../../python/corpus-structure/src/corpus_structure/orchestrate/pdf_streaming.py) ·
[Execution-fit heuristic H23](../../design_review/design_principles/core/efficient-architecture-heuristics.md#f-execution-coordination-and-recovery)

If the shadow measurement identifies Chandra decode or repeated model initialization
as material, compare the qualified Transformers group with a separately pinned local
vLLM recipe. Use identical submitted PNGs and compare effective multimodal resize,
finish reasons, and independently reviewed structures. Compare one in-flight request
and bounded concurrent requests before enabling MTP. Use the served alias, startup and
handoff time, and request queue and prefill/decode metrics to explain the result. The
repository overview describes vLLM 0.32.0. The pinned Chandra launcher selects a 0.17.0
container and disables MTP by default. Establish actual feature support and memory fit
for the selected runtime on this GPU before using it for qualification.
[vLLM capability overview](../../libraries/analytical_infrastructure/vllm.md) ·
[Pinned Chandra launcher](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/scripts/vllm.py)

### Comparator execution fit · 2026-11-08

**Measured · 2026-11-08.** During comparator run 373, PostgreSQL backend 3020393
ran `ops.validate_pdf_build` with no blocking sessions or parallel workers.
A two-second CPU-time sample measured 1.00 CPU equivalents on a 32-logical-CPU
host. The work was past A/B/C replay and selection. PostgreSQL already allows
four workers per gather. The protected validator and its logical identity
and access-check routines are parallel-unsafe in the installed catalog, and
the identity routine serially verifies byte streams, constructs canonical
records and folds them in order. The observation establishes the execution
boundary. It does not identify the most expensive nested statement.
[Protected validation owner](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_publication_native.py) ·
[Logical identity implementation](../../../python/corpus-structure/src/corpus_structure/semantic/sql/pdf_record_logical_identity.sql)

**Proposed.** Separate the comparator's two consumers before changing the
publication contract. A routing or discovery study can freeze the sealed
archive plus independently witnessed repair decisions and compare Chandra
against that view. A study using this route reports the source fixes as
incumbent gains and explicitly limits ordinary Reader conclusions to a
separately qualified published product.

For repeat publications under compatible contracts, qualify an incremental
derivation over one sealed predecessor. Reuse exact unchanged records, streams
and validation premises. Check the changed occurrences and all dependent
region, containment, order, projection and relation endpoints. If schema,
policy or identity mapping invalidates those premises, use the full path.
Determine whether the current graph can share physical storage and retain
the existing digest. A composable identity requires a separately versioned
contract and exact historical reads.

For full builds, first measure access correspondence, artifact verification,
canonical frame assembly and the final fold separately on representative
frozen inputs. Eliminate repeated lookups using joined inputs and bounded
batches. Parallelize independent read-only checks or frame preparation over
the same frozen snapshot. Keep document-wide order, relationship closure
and the ordered digest as final checks. Existing digests must match byte
for byte. Validate cancellation and refusal of a missing shard, stale
premise, or changed endpoint before using parallel output for publication.

In the reconciliation path, keep the existing page and geometry bounds.
Retain B's layout and coverage without building a correspondence index for
an empty mapping. Reuse a page index until a local selection changes it.
Resolve exact typed equality before edit alignment and avoid calculating
table/chart edit traces that the published evidence discards. Keep spans
and header paths in table equality. If page-local mapping becomes material,
prepare it in bounded independent workers and reduce in stable A-before-C
order under the existing document owner.
[Reconciliation selection](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py) ·
[Validation scope and identity](../../design_review/design_principles/core/design-principles.md#dp-09--one-reuse-mechanism-keyed-on-complete-dependencies) ·
[Execution-fit heuristics](../../design_review/design_principles/core/efficient-architecture-heuristics.md#f-execution-coordination-and-recovery)
