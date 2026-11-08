# Chandra OCR 2 after Nemotron 3.5

**Follow-up review · 2026-11-08.** Develop Chandra as a post-Nemotron structural enrichment stage. Repair losses from retained source evidence first. Deliver attributed structure through the existing evidence Reader, then qualify automatic routing in shadow. Direct selection remains conditional on a source-verified contribution that requires Chandra and a separately governed admission path.

The first review at `252a476da` compared the original 518-page Grinstead–Snell PDF, Standard cut 413 and integrated cut 431 with a bounded live panel. Its installed baseline was Docling 2.145.0 and Core 2.105.0. This follow-up inspects `10f67f9fb`, with Docling and Slim **2.148.0**, Core **2.106.0** and the pinned local checkpoint. The exact combined producer is run 309, task 1389, adopted by run 312 at cut 431. Use the prior case panel and the retained native NIST controls for diagnosis. A protected estimate of gain or recall needs an independently adjudicated population. [Full-book review](../design_review/evidence/2026-11-08_nce-full-book/review/README.md) · [Original probe evidence](../design_review/evidence/2026-11-08_chandra-post-nemotron/README.md) · [Chandra overview and addendum](../libraries/primary_intake/Chandra_2_OCR.md)

## Current ownership and the upgrade boundary

The current source product combines StandardPdfPipeline/RapidOCR with Nemotron A page parse, B layout detection and C Table/Chart crop recognition. It retains immutable request and response evidence, typed input pins, mapping, correspondence, selection and coverage. The independent Chandra request should use the original pixels, with routing and comparison informed by the preceding evidence. Give it its own producer, recipe and observation role. The incumbent selector admits A/B/C, its mapper calls `parse_nemotron_parse_v3_5`, and its selection kernel classifies a picture as a chart for this route. The installed release adds independent Chandra page and crop observation roles. Reusing request custody, geometry checks, native product construction, and readers is a better fit than expanding those Nemotron semantics to every new visual item. The selected product remains the authority for ordinary section consumers. [ADR-0040](../adr/0040-forward-pdf-only-contracts.md) · [Recognition and selection owner](../plans/pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md)

Docling 2.148.0 supplies the `chandra_ocr2` preset, `CHANDRA_OCR_LAYOUT_PROMPT`, `ResponseFormat.CHANDRA_HTML` and `parse_chandra_html`. The probe used checkpoint `af93b47dba1b47b6640c86ccf487ed2260ab9a09` in an isolated overlay. The release improves inline parser spacing, native superscript/subscript detection, and runaway TableFormer recovery. In a mapper-only comparison, the retained Nemotron responses from the selected book cases gave identical table, formula, caption and picture summaries through the old and new direct parsers. That comparison uses unchanged raw responses and a normalized frame. It establishes neither fresh Standard equivalence nor unchanged integrated publication. Qualify the upgraded Standard path, direct Nemotron mapper and existing consumers independently before attributing future gains to Chandra. [Target release](https://github.com/docling-project/docling/releases/tag/v2.148.0) · [Preset source](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/stage_model_specs.py) · [Replay receipt](../design_review/evidence/2026-11-08_chandra-post-nemotron/raw/nemotron-replay.json)

Docling 2.148.0 also ships its own Nemotron `NemotronParseOptions(passes="triple", triple_regions="union")`. It performs real A/B/C work, with different temperatures, crop ordering and guarded merging. It retains page summaries and merged debug text. A failed optional stage can leave page status successful. The existing raw per-pass observations are needed for routing and independent comparison, so treat the upstream route as a separate challenger. Its batching and guarded merge provide useful comparison mechanisms if their behavior is measured with the same pixels and requests. [Upstream multipass implementation](https://github.com/docling-project/docling/pull/4933) · [Crop and merge contracts](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/nemotron_parse_multipass.py)

## Opportunities

**Measured · 2026-11-08.** The local panel completed all 12 book pages, five supplemental cases and three crops. Live output shows both added value and regressions. Page 509 recovered upright table organization where both retained arms had transposed the table, yet Chandra displaced cells. Page 510 matched all 344 checked source data cells and corroborated the retained integrated result. The full case ledger distinguishes these from genuine marginal recovery. [Case outcomes](../design_review/evidence/2026-11-08_chandra-post-nemotron/README.md#executed-cases)

<a id="O01"></a>
### O01 · Inspect a new visual reading without republishing the source

**Delivered for the bounded development journey.** An operator reviewing an unreliable section can request a second reading of a figure, table, or difficult formula and see the original region beside each interpretation. The explicit request established the evidence route. High-value reasons for expanding it include failed or incomplete passes, conflicts between native and crop readings, a missing typed item, or a requested visual capability. Keep a full-page option for reading order, captions, and hierarchy. Crop for detail or orientation when the decision benefits, and retain the page reading if a crop removes context. Retain unselected and failed attempts, source PDF and physical page, original raster and effective submitted frame, checkpoint, prompt and decode settings, and independent request and parser dispositions. Archive raw HTML before deriving Docling objects. The native Chandra manager returns a final result after its retry loop, and its native chunk transform strips nested geometry. It also substitutes a box for malformed input. Neither representation alone is enough for the current custody standard. [Native output](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/output.py) · [Native retry behavior](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/model/vllm.py) · [Docling page status](https://github.com/docling-project/docling/blob/v2.148.0/docling/pipeline/vlm_pipeline.py)

The useful unit is an attributed interpretation or independently validated local addition. Compare three realizations: evidence-only review, qualified local promotion through a derived product, and routine all-page recognition. The first supports new inspection immediately, the second is warranted where a consumer needs an accepted object, and the third needs measured gains on representative clean and difficult material. Default keep/add/replace and crop precedence are lexical and recipe-specific. Provider agreement alone gives correlated evidence. It does not decide correctness. Preserve the current exact PDF frame and scoped blank, partial and unknown states. Any promoted result must close against a versioned observation and existing protected publication. A subset of pages cannot stand as a complete section product.

<a id="O02"></a>
### O02 · Make figures independently inspectable and searchable

**Pursue typed discovery and qualified associations.** Let a reader ask what a figure shows or which axes, units and labels are actually printed, then open the source image and see the printed caption, generated description and data proposals separately. Pages 108, 301 and 334 show the immediate gain. Page 108 recovers the shared Figure 3.5 caption and meaningful panel descriptions, but the caption remains a separate native item. Page 301 preserves both printed captions and describes both curves; page 334 describes symmetry without making the asymmetric numeric claim in the integrated product. The descriptions give useful navigation and inspection. They do not establish a data series.

Reuse existing artifact identities, region access and evidence reads. Evaluate an explicit caption association with supporting geometry, reading order and textual identifiers. Allow shared captions and distinct figure manifestations. The direct parser attaches an explicitly nested caption, while siblings stay separate. A generated title or descriptive number should not overwrite a printed caption or established value. Validate figure boundaries, typed parentage, and visible details independently. [Parser and caption behavior](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) · [Reader and work packet owners](../design/D8-agent-and-query-interfaces.md)

<a id="O03"></a>
### O03 · Offer chart data with explicit evidence precision

**Pursue as an opt-in proposal view.** A researcher can inspect panel and series identity, compare values against the plot, and export source-qualified printed values and graphical estimates separately. A Chandra HTML table nested under a picture survives as `TableItem`; it does not populate `PictureMeta.tabular_chart`. The existing projection therefore treats its cells as ordinary `cell_text`, and the existing picture-addressed chart cell API expects a different payload. Keep table child identity and chart value standing separate. A printed mark, a visually estimated ordinate and data supplied by the author have different meanings even when their numbers match.

Compare with the incumbent Nemotron chart observations and Docling Granite chart enrichment. Granite's field checks can repeat extraction for an existing nested table and skip summary when only short alt text exists. Use one selective enrichment decision for a missing field. Before promoting chart values, check axes, units, legend/series identity, scale direction, printed versus estimated status, and panel ownership. Retain values and source ranges as attributed observations where those checks cannot be met. [Chandra picture mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L729-L783) · [Granite field selection](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/chart_extraction/granite_vision.py#L116-L143)

The live chart fixture produced a nested 4×2 table with 60, 40 and 30 mL. Only 60 was printed above its bar. The table assigned all three values the same standing. The underlying image and source-qualified value types are therefore necessary even when a generated table looks exact.

<a id="O04"></a>
### O04 · Recover exact tables and formulas at the layer that lost them

**Pursue incumbent recovery first.** On page 151 Chandra supplies two native tables, with all four Table 4.2 fractions and a useful row/column structure. The existing Nemotron page and crop already contain the four fractions. The crop's geometry, extra row and selected output need separate reconciliation. First ask whether the incumbent raw evidence can supply the required product. Then compare the independent Chandra structure. Page 398 has a sound 21×13 Chandra grid and twelve rich Z headers, but the seventh data row's Z5 is wrong. A plausible topology and correct Profit values do not justify whole-table replacement.

Page 416 returns six complete formula items that survive the current projection routine. The existing Reader shows the source-derived `orig` already carries matrix content while selected `text` ends at the array opener. Prefer a qualified reading of that retained material when it meets the consumer's demand. Chandra can provide an independent alternative with its own attribution. Page 439 preserves the equal-probability term and recurrence, with the exercise and its conditions still needing association. Route candidate syntax through the existing positioned math grammar and stronger equivalence only on explicit demand with stated assumptions. Assess printed symbols, values, row and column labels and occurrence identity before promoting. Preserve rich-cell structure and captions. On a continued or oversized table, retain source parts and test header continuity before suggesting a merge. [Pinned parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) · [Current source selection](../plans/pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md#pdf-15--mapping-correspondence-and-governed-integration)

The current positioned grammar failed all six Chandra matrix strings on page 416. A readable source alternative is useful today. Machine-readable matrix interpretation needs a separate qualified reading or representation. [Reader and grammar evidence](../design_review/evidence/2026-11-08_chandra-post-nemotron/raw/matrix-consumer.json)

<a id="O05"></a>
### O05 · Query diagram edges with image evidence

**Retain generated graphs as attributed candidates.** A reader should be able to ask where a named node leads, or which branch carries a printed label, and see the original diagram and provenance. Preserve Chandra Mermaid as generated code attached to its picture. A syntax parse can make nodes and edges inspectable. Promotion requires endpoint identity, direction, edge label and multiplicity checked against the source. Restrict initial admission to simple directed diagrams with a clear visual witness, and keep uncertain connectors explicit. A bounded graph traversal can then consume qualified edges through existing graph tools. It should never promote an OCR graph to a factual procedure or causal relationship without the corresponding domain witness. [Chandra layout prompt](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/prompts.py) · [Docling picture handling](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L729-L783)

The live fixture preserved all three directed edges and both branch labels. The code item had no direct box and remained attached to a located picture. This supports an image-backed candidate view. On natural NIST pages 141 and 206, a return branch went to the wrong node and two distinct arrows collapsed into one. Defer authoritative edge queries until direction, labels and multiplicity can be witnessed independently. [Natural diagram findings](../design_review/evidence/2026-11-08_chandra-execution/investigations.md#ch-05--charts-and-diagrams)

<a id="O06"></a>
### O06 · Separate visual form state, native fields, and specialist readings

**Keep opt-in and qualify per consumer.** Visible checkmarks, scanned entries and annotations can support source inspection when interactive fields are absent or disagree with their appearance. Use the original PDF widget as the authority for native field identity and state. Keep Chandra's visible value and mark as a separate witness and allow ambiguity on label/value proximity. Docling emits selected/unselected form labels without reliably retaining control kind or widget identity. Its ordinary text projection can omit empty checkbox items. A form-specific typed read has a clearer contract than treating those marks as prose. Similarly, expose a chemical diagram's original pixels and generated SMILES as a candidate. Docling's single-`<chem>` molecular field is useful custody. Independent structural comparison and domain checks govern any stronger claim. [Chandra native PDF loader](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/input.py) · [Docling Chandra parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py)

The live form fixture recovered the value and both marks. It produced no native widget identity or label association. The chemistry fixture recovered propan-2-ol as `CC(C)O` and preserved it in `PictureMeta.molecule`. These are distinct evidence types with different downstream uses.

<a id="O07"></a>
### O07 · Improve source navigation for complex layout and multiple scripts

**Investigate on natural samples.** More legible native text, headings, table of contents, nested lists, references and captions can improve section retrieval and the evidence packets downstream extraction uses. Compare born-digital PDF text and annotations before overriding a good reading. For scanned or misleading text layers, an independent transcription is useful even when it remains an alternative. Evaluate multi-column order, multilingual literals and RTL order, handwriting, native hyperlink targets, inline code, bibliography and footnote association as separate properties. The current full-text search uses an English configuration, so multilingual OCR has a separate discovery test. Reassemble page observations under the existing document-wide heading owner. The controlled heading probe confirmed that page-local normalization can flatten a lone h2. Use `normalize_heading_levels=False` for page replay and normalize once over the intended document. [Docling VLM assembly](https://github.com/docling-project/docling/blob/v2.148.0/docling/pipeline/vlm_pipeline.py) · [Current source search](../../python/corpus-structure/src/corpus_structure/serve/source_search.py)

<a id="O08"></a>
### O08 · Preserve visual evidence without flattening it into prose

**Prerequisite for O02–O06.** Use bounded picture/region reads and a source-qualified packet view. The current repository projection traverses picture children, so a nested chart table or Mermaid code can enter the prose stream. Picture description and molecular metadata stay on the object and have no standard text-packet channel. Docling's default chunk serializer behaves differently and skips picture children. Controlled `ChunkingSerializerProvider` with `MarkdownParams(traverse_pictures=True)` demonstrated inclusion, but opening everything at once makes speculative figure prose look like source transcription. Compare a selected typed view and an explicit text rendering for inspection. `TreeChunkExpander` and `PageChunkExpander` can support bounded context inspection. Keep intact sections and existing identity as required by ADR-0040. Prefer existing authorized image access to embedding all rendered pages in each packet. [Repository projection](../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py) · [Docling serialization and expansion](https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/)

<a id="O09"></a>
### O09 · Route runtime work by observed benefit

**Use one local reference runtime first.** The isolated live probe used the official checkpoint, Transformers, BF16, explicit `load_in_8bit=False`, and one active inference stream. The host used the matching driver libraries already retained for Nemotron. Reference PyTorch implementations served the hybrid-attention kernels. Treat observed latency as local evidence for this panel. Prefer one GPU owner at a time, with page/crop work bounded, progress retained per case, exact resume, and distinct request, parser, admission, and quality outcomes. Use the Docling VLM route for integration parity and replay stored raw HTML through `parse_chandra_html` for CPU parser and consumer iteration.

If real demand warrants a separate server, compare explicit local `ApiVlmEngineOptions` with an isolated vLLM worker. Verify endpoint/model alias and backend-specific preprocessing, retry and stop behavior. Test ordinary batching before speculative decoding. Native MTP is optional and backend-dependent. MLX is a separate quantized artifact, while Ollama and LM Studio are separate API profiles. Chandra CLI/app can help local troubleshooting. Docling Serve and Jobkit need a demonstrated scheduling or multi-client requirement before adding an operational layer. Hosted 2.5 supplies a separate structured schema and service boundary, with no role in this local probe. [Preset and engines](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/stage_model_specs.py) · [Serving launcher](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/scripts/vllm.py) · [Docling Serve](https://docling-project.github.io/docling/usage/api_server/deployment/) · [Docling Jobkit](https://docling-project.github.io/docling/usage/jobkit/)

## Follow-up findings from the installed pipeline

**Tested · 2026-11-08.** Reopened the exact managed p151 whole-page result and p509
upright-crop result with `uv run ci source inspect 309 --producing-task 1389 --product integrated --native-digest … --native-view visual-evidence --evidence-run … --evidence-task … --evidence-product … --evidence-digest … --page PAGE --max-bytes 8388608 --json`.
The source and observation arguments are the exact `source` and `mapped` pins in the
receipt. Both scoped reads passed. Omitting page/item scope was refused. p151 returned
two tables, two caption candidates and 29 formulas. p509 returned one table candidate.
Both reads preserve coarse mapping, unassessed fidelity and unknown execution
completion despite having usable mapped content. These are repeat reads of existing
observations. Fresh Chandra inference and corpus-wide activation qualification were
`not_run` for the follow-up.
[Managed pins](../design_review/evidence/2026-11-08_chandra-execution/managed-journey.json) ·
[Original case dispositions](../design_review/evidence/2026-11-08_chandra-execution/investigations.md)

The follow-up distinguishes four actionable losses.

| Layer | Finding and opportunity |
| --- | --- |
| Raw to typed | On p108 the raw layout has one figure block, one description of two histograms and a detached caption. It contains no independently placed panel boxes. The pinned picture parser joins distinct nested image alt strings into one description and removes the image elements. Preserve raw and mapped data and use independent geometry for panel identities. |
| Typed to reader | The current mapper preserves cell offsets, spans and header flags but drops `RichTableCell.ref`. It assigns an attached caption to a single owner and leaves a detached one unassociated. Preserve the child reference and allow one caption with separately qualified panel associations. |
| Projection to consumer | The ordinary projection visits picture children and emits canonical chart metadata separately. Materializing a generated table in both places could duplicate estimates in ordinary text. Give interpretations a typed, source-scoped route and test the dual representation. |
| Shared mapping | Docling's Nemotron mapper imports the Chandra table limit and HTML table builder. Where both use that helper, agreement between typed outputs can preserve a shared mapping loss. Retain and inspect the original and raw observations before treating mapped agreement as evidence of fidelity. |

[Pinned picture parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L692-L783) ·
[Pinned Nemotron parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/nemotron_parse_v3_5_utils.py) ·
[Current visual mapping](../../python/corpus-structure/src/corpus_structure/semantic/pdf_visual_mapping.py) ·
[Current section projection](../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py) ·
[Retained p108 and p151 readings](../design_review/evidence/2026-11-08_chandra-post-nemotron/README.md#executed-cases)

### Specialist dispositions

**Proposed · 2026-11-08.** Carry O03 and O05 into attributed picture reads. On the
authored chart, only one of three reconstructed numbers is printed. Treat missing typed
chart data as its own requested field. Granite can be a fallback for a supported
bar, pie or line chart when the retained observations lack that field. Its presence
checks miss Chandra's child table and its CSV conversion infers types and headers.
Retain provider CSV and classify each value by source standing before a specialist
consumer can use it. Diagram syntax is useful for candidate presentation. Natural
graph traversal remains conditional on independently witnessed edges. Use bounded
source regions for verification and preserve parallel edges and cycles.
[Chart routing](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/chart_extraction/granite_vision.py#L116-L143) ·
[Chart CSV mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/chart_extraction/granite_vision.py#L337-L412) ·
[Natural graph controls](../design_review/evidence/2026-11-08_chandra-execution/natural-diagram.json)

Keep O06 and O07 per capability. A native field and its appearance can differ. The
HTML parser maps visual radio and checkbox marks to the same selected/unselected
labels, so preserve the raw distinction as evidence and require a qualified widget
or visual label/control binding. A single `<chem>` block can populate molecule metadata.
Reopen canonical chemistry with natural drawings and independent connectivity and
stereochemistry checks. For navigation, preserve raw heading depths until assembly
and compare the actual retrieval results across language and reading order. A native
link target can qualify a link where OCR only supplies a label. Raw `Table-Of-Contents`
and `Complex-Block` labels may nominate discovery features. The pinned parser has no
dedicated types for them. Reopen handwriting and multilingual discovery on natural
pages and a real query. [Pinned form and block mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) ·
[Heading normalization](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/vlm_utils.py) ·
[Specialist investigations](../design_review/evidence/2026-11-08_chandra-execution/investigations.md#ch-06--forms-chemistry-and-navigation)

<a id="O10"></a>
### O10 · Find pages with unmet structural demand automatically

**Pursue in shadow.** Compare qualified native text and OCR-region health, retained
Nemotron layout and crop decisions, integrated correspondences, and requested typed
outputs. A page with healthy text can still lack caption ownership, header paths or a
useful figure reading. Generic partial coverage and vector API availability lack the
specificity to trigger a pass. B's mapped document is intentionally empty, so inspect its
retained layout evidence. Treat the absence of direct text projection on book pages 4
and 119 as a locator issue, and p506 as a valid blank body. Route on concrete reasons
with exact source locators and keep incumbent recovery as a separate outcome.

The smallest fit is an evaluator after publication and a bounded managed enrichment
run. Existing visual requests require a published integrated pin and a selected item
pointer for a crop. A dropped object can require whole-page context. An unresolved
A/B/C request that prevented publication belongs to incumbent recovery. Prefer exact
raw replay, then local grouped inference. The pinned Transformers engine uses the
first input's settings for batch generation and does not reliably report EOS as a
terminal reason. Require homogeneous recipes, per-image receipts, and retained unknown
completion. Retain the submitted frame and account for the checkpoint processor when
a detail improvement depends on effective resolution.
[Full-book source receipt](../design_review/evidence/2026-11-08_nce-full-book/records/nce.gs518-integrated-source.json) ·
[Current visual request](../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py) ·
[Transformers batch and stop behavior](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/inference_engines/vlm/transformers_engine.py#L447-L643) ·
[Pinned image processor](https://huggingface.co/datalab-to/chandra-ocr-2/blob/af93b47dba1b47b6640c86ccf487ed2260ab9a09/preprocessor_config.json)

A frozen selective versus all-page shadow comparison is the first qualification of
activation. Adjudicate important differences and sample apparently clean pages because
shared omissions can be invisible to the router. Keep routing recall separate from
the precision of accepted field changes. The earlier panel is a development control.
[Routing and qualification package](../plans/chandra-2-post-nemotron/automatic-routing-and-qualification.md#CH-10)

<a id="O11"></a>
### O11 · Use native source geometry to qualify structure before another recognition pass

**Pursue for ruled tables and located literals.** On a suitable born-digital page,
Docling Parse's `get_shape_lines` and `get_segmented_page` expose ruling geometry
and positioned text. Use them to qualify boundaries and bindings when the source
supplies those marks. This can establish why a better-looking grid is faithful without
using the same model output as both candidate and witness. It also supports checking
caption identifiers and figure text before introducing new OCR text. Use a checked
crop on a scan where native text is absent or unreliable. Preserve unresolved spans
and scan associations when a witness cannot establish them.

Investigate native path data for plot axes or diagram connectors only when a concrete
consumer needs those fields and visibility, clipping, transforms and arrowheads can
be independently checked. Rectangular overlap can nominate evidence. It cannot
qualify edge direction or graph membership.
[Docling Parse backend](https://github.com/docling-project/docling/blob/v2.148.0/docling/backend/docling_parse_backend.py#L159-L246) ·
[Docling Parse content materialization](https://github.com/docling-project/docling-parse/blob/v7.24.2/docling_parse/pdf_parser.py#L688-L720)

## Recommendation and decision gates

First recover p108, p151 and p416 from independently qualified source and incumbent
evidence, and deliver richer figure, table and formula evidence through bounded
typed access. The former benefits ordinary readers and the latter supports search
within visual evidence and agent review without moving generated material into source
claims. Preserve physical occurrence identity, dependencies and existing immutable
selections. Qualify selective activation with the full-book and mixed-corpus shadow
arms. Adopt all-page inference only if the additional source-verified gains merit
the shared GPU work. Keep explicit operation when neither policy qualifies.

Direct Chandra-dependent promotion needs a specific useful selected result and an
operator decision on its input authority. The current Python and protected publication
paths reject Chandra inputs. A separate scoped effect can preserve the single selected
PDF and enforce source fidelity per field and dependent structure. Keep canonical chart
estimates, diagram edges, widget state, chemistry and multilingual navigation scoped to
their individual evidence and consumer obligations. [Selection packages](../plans/chandra-2-post-nemotron/source-recovery-and-governed-selection.md#CH-08) ·
[Typed delivery](../plans/chandra-2-post-nemotron/visual-evidence-and-delivery.md#CH-09) ·
[Combined target](../plans/chandra-2-post-nemotron_2026-11-08.md)
