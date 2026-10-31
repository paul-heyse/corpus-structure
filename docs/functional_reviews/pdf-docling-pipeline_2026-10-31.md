# PDF-only Docling pipeline — functional opportunity review

**Proposed · 2026-10-31.** Review of the PDF-only pivot, not a production implementation,
completion audit, or change to existing plan scope. Scheduled O01–O08 execution disposition
and investigations now belong to the [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md);
this review retains the recommendations and evidence, not a second progress ledger. Companion: [target model](pdf-docling-pipeline_2026-10-31_target-model.md).

## 1. Outcome, baseline and evidence boundary

Replace active HTML ingestion with PDF conversion through `StandardPdfPipeline`, retain native
`DoclingDocument` JSON in PostgreSQL, and make its structure useful throughout analysis and
knowledge extraction. The initial original is
`docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf`.
Upstream rendering of other formats into PDF is outside this capability.

**Operator requirements incorporated:** preserve sections/subsections as the organizing hierarchy;
**no section chunking in the proposed scope**. A real consumer failure on an actual oversized
section is the revisit trigger. Processing batches and bounded query pages are transport/execution
units, not new document sections or persistent semantic chunks.

Inspected production baseline: `5a6045f4813769af5706c2530b6c6da398450b91`, with current
`STATUS.md` and completed PP-00–PP-10 coordinator. Concurrent modifications to the supplied
`docs/libraries/docling.md` and untracked `docs/libraries/pdf_rendering_libraries.md` are operator
inputs, not review-authored changes. The 1,601-line Docling reference and [OCR guide](../libraries/docling_ocr.md), including the added technical-PDF guidance at lines 867–1044, were reviewed.
The standard is core 3.3, efficiency heuristics 1.0, applicable code-intelligence fidelity and
relationship guidance 1.4, and the repository binding. This functional inquiry requires no
broad diagnostic audit; no audit premises were changed.

**Evidence checked 2026-10-31:** source inspection of production producers/consumers; Context7
Docling/core and SymPy documentation; tagged Docling 2.145.0 and core 2.103.1 source;
installed SymPy 1.14.0 API signatures. `pdfinfo` reports 1,589 pages, 211,502,518 bytes,
untagged, unencrypted, no interactive forms. These are file metadata, not extraction quality.
Docling, docling-core, Torch and RapidOCR were not installed in the project environment.
**not_run:** PDF conversion, model inference, corpus fidelity evaluation, runtime benchmarks,
and product tests. None is necessary to publish a Proposed design. Actual formula coverage,
OCR behavior, hierarchy quality and whole-book resource feasibility remain investigation items.
A read-only independent consumer review informed O03–O07; its conclusions were reconciled here.

## 2. Recommendation and corrected premises

Adopt Docling as the sole active source-interpretation adapter. Make its native structured JSON
the source-structure product, rather than attach it to the old HTML-shaped rendition and leave
consumers unchanged. Derive text and relational access views for operations that need them.
Keep original PDF bytes, conversion diagnostics, and domain knowledge distinct.

This removes substantial *classes of work*: DOM repair instrumentation, CSS role matching,
browser-text insertion, HTML math delimiter discovery and page macro acquisition. It does not
establish a latency improvement: layout/OCR/table/formula inference introduces different work,
and this book is much larger than the previous 78-page HTML selection.

Four important distinctions qualify the proposition:

1. Formula enrichment writes recognized LaTeX to an item's `text`; `orig` is the untreated
   extracted representation. Neither establishes recovery of the author's original TeX source.
   The PDF remains the original evidence. [Tagged enrichment source](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/code_formula/code_formula_vlm_model.py).
2. Formula recognition and mathematical interpretation are different. Native SymPy LaTeX input
   can remove custom conversion, but ambiguity, assumptions, occurrence identity, unsupported
   syntax and definedness still need owned outcomes. [SymPy parsing](https://docs.sympy.org/latest/modules/parsing.html).
3. Heading detection alone yields flat levels. Enable `HeadingHierarchyOptions`; then use its
   levels to build/verify section containment. A heading level is not itself a section container.
   In 2.145.0, full `generate_parsed_pages=True` is **not required** for style-based hierarchy;
   the pipeline temporarily retains the necessary heading lines. This corrects the supplied
   overview's older premise. [Tagged options](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py).
4. Pydantic-valid native JSON is structurally useful, not proof of correct OCR, complete inline
   mathematics, table continuity, or recovered author semantics. Conversion health is separate
   from model consistency and source fidelity.

<a id="O01"></a>
## 3. O01 — One PDF conversion authority with explicit health

**Value:** one source pipeline, richer document evidence, and reuse of conversion across all
consumers. Replace `ingest.html` with an admitted PDF operation behind the existing method/adapter
boundary. Retain original bytes before conversion; run expensive native work outside publication
transactions; publish a coherent immutable conversion and diagnostic report through existing
protected operations.

**Concrete mechanisms:** `DocumentConverter(allowed_formats=[InputFormat.PDF], format_options=...)`,
`PdfFormatOption(pipeline_cls=StandardPdfPipeline, pipeline_options=...)`, `convert()` and
`ConversionResult`. Select OCR explicitly rather than inherit environment-dependent auto selection.
The recommended starting candidate is RapidOCR/ONNX with native-text-aware region processing and
broken-text-layer recovery. Keep `do_ocr=True`; do not force full-page OCR over reliable text.
Enable `do_table_structure=True`, established TableFormer V1 `ACCURATE` with cell matching,
`do_formula_enrichment=True`, and heading hierarchy. Record the resolved engines/models/options.

Default formula candidate is `CodeFormulaVlmOptions.from_preset("codeformulav2")` using a local
supported runtime. This is a formula enrichment model inside StandardPdfPipeline, not adoption
of `VlmPipeline` for whole-document conversion. A selected pipeline does not forbid its own
native enrichment stages.

For this mathematical corpus, prioritize **layout detection plus formula enrichment before
adding general OCR passes**. Explicitly bind
`LayoutObjectDetectionOptions.from_preset("layout_heron_default")` as the starting layout
candidate and compare `layout_egret_large` on representative dense equations, inline mathematics,
headings and formula-bearing tables. The tagged API recommends Egret Large/Xlarge for complex
documents, but no Siegrist-specific quality/throughput advantage is established. Evaluate element
detection separately from transcription: a stronger formula recognizer cannot repair a formula
region that layout never exposes. Select the layout after this focused comparison rather than
silently inherit the default or mandate the largest model.

Make formula crop policy part of the archived conversion specification:
`CodeFormulaVlmOptions.from_preset("codeformulav2", scale=2.0,
expansion_factor=0.18, stop_on_repetition=True)`, with `max_size` and `engine_options` explicit
when selected. For dense equations or equation-number contamination, compare a reduced margin
such as `0.08`; do not adopt it globally without checking clipped bounds, subscripts and neighboring
content. Repetition stopping limits pathological generation; it does not prove faithful math.
`granite_docling` is a native alternative **formula-stage** preset to investigate for demonstrated
CodeFormulaV2 failures, separate from replacing the whole document pipeline.

**Material uncertainty:** the tagged formula enrichment catches inference-batch exceptions,
logs them, and yields original items unchanged. A formula label or nonempty `text` therefore
cannot certify successful LaTeX enrichment. Inspect model-stage diagnostics/extensions and provide
an honest recognition-health result; absent an attributable result, record unknown rather than
pretend the backend text is successful LaTeX. Do not infer success from `text != orig` either.
This is a producer-boundary investigation, not a reason to write a second formula recognizer.

**Alternatives:** NativePdfPipeline lacks the selected semantic/layout capabilities; whole-document
VLM conversion changes fidelity/execution premises and is not the selected entry. Docling Serve,
Jobkit and a second MCP server add unnecessary operational owners for this local application.
Use the library in the existing owned worker path first.

**Delivery scenario:** a failed or partial conversion retains original bytes and diagnostics;
no active complete result is published by merely returning a document object.

<a id="O02"></a>
## 4. O02 — Native JSON with governed relational access

**Value:** preserve native tables, formulas, pictures and relationships without reconstructing
separate private representations in each consumer.

Docling/core owns its versioned Pydantic document vocabulary. The application LinkML model owns
conversion identity, configuration, operations, states, dependencies, domain recognition and
cross-product relationships. Import/reference the upstream schema as a qualified artifact rather
than hand-author a competing LinkML copy of every Docling class. PostgreSQL owns instances;
SQLAlchemy Core metadata and current migration/publication machinery realize their storage.

Use `export_to_dict(mode="json", by_alias=True, ...)` and a native JSONB product, with the exact
serialization policy and schema version archived. `model_validate_json`/`load_from_json` support
reload; use reference/tree validation at the trust boundary. Core 2.103.1 `validate_document()`
clamps bounding boxes, so finalize the returned validated representation **before** computing its
identity and publication. Never mutate a stored product during a read. JSONB preserves JSON
meaning, not formatting/key order or the original PDF bytes; distinct physical hashes must not
be substituted for semantic product identity.

Build operation-shaped item, ordered edge, page-region and table-cell access projections once
per immutable product. Reuse existing normalized parsing relations when their meanings fit;
extend the model for geometry and upstream references where they do not. An integer `Extent`
is not a bounding box. Keep projection-to-native-pointer provenance, schema/recipe versions,
referential checks, ordering and occurrence multiplicity. Do not use a pair of endpoints as an
edge identity or repeatedly hydrate the entire book for a one-formula read.

**Images:** native JSON may contain supported image references backed by immutable artifacts;
keep retained PDF bytes sufficient for later region rendering. Avoid embedding all rendered pages
as base64 in a giant JSONB value by default. Preserve figure objects/captions regardless of image
payload policy. Referenced images need owned artifact custody and explicit reload behavior,
not ephemeral local paths. Exact image retention/resolution is an implementation investigation
against actual consumers, not an excuse to discard document structure.

**Alternatives:** JSONB-only traversal is simplest for whole-document reload but poorly matches
repeated bounded joins; relational-only re-authoring loses native interchange. Native JSON plus
purposeful derived indexes preserves both. No generic new graph engine is needed to traverse a tree.

<a id="O03"></a>
## 5. O03 — Intact sections and subsections as real document structure

**Value:** section-grounded extraction, stable contextual navigation, and faithful organization.
Use Docling hierarchy inference and body reading order, not `texts[]` order or page-coordinate
sorting. Core supports `GroupLabel.SECTION`/`CHAPTER`, `GroupItem`, `add_group(parent=...)`,
item parent/children references and `iterate_items()`.

Preserve raw conversion JSON. Where the converter supplies heading levels without full section
groups, construct a versioned **derived DoclingDocument** with section/subsection containers.
Retain native item identity mappings and ordered membership; validate parent/child consistency.
Distinguish inferred source sections from application-created containers. Do not silently rewrite
source labels or represent organizational groups as author text.

**No section chunking is selected.** Do not introduce HybridChunker, arbitrary token windows,
peer merges, or durable chunk rows. A section/subsection is the structural analysis unit;
method-specific item selections are bounded views over that hierarchy. Ancestors supply context
without flattening the book. A parent-section analysis must declare whether descendant sections
are included; avoid duplicate extraction through accidental parent/child overlap.

Only an observed required-consumer failure on an actual large section reopens chunking. If later
selected, parts must be lower-level child groups within the same derived Docling hierarchy,
with ordered source membership, parent-section identity and explicit derivation. This is a
future constraint, not a current feature or prerequisite.

**Principal regression risk:** `sources/siegrist.yaml` currently supplies theorem/definition/exercise
CSS hints, proof/solution containment, author IDs and rendered references. Docling section labels
do not automatically recover these domain distinctions. Replace them with explicit attributed
recognition rules over native structure/content; uncertain recognition remains uncertain. Do not
promote visual containment directly into `proves` claims.

<a id="O04"></a>
## 6. O04 — Formula items directly into lazy mathematical interpretation

**Value:** stop rediscovering formula boundaries from a reconstructed prose stream. Iterate formula
items and feed their recognized LaTeX directly to native SymPy parsing. Preserve `orig`, recognized
text, formula occurrence, recognition health and PDF provenance separately.

Preferred starting adapter: SymPy 1.14.0 `parse_latex(..., backend="lark")`, or a prepared
`LarkLaTeXParser` where runtime grammar/transformer customization is necessary. Installed signature
is `(print_debug_output=False, transform=True, grammar_file=None, transformer=None)`; Context7's
suggested `local_dict/global_dict` constructor is not this installed API. The native parser is
experimental; Lark detects ambiguity and rejects malformed trailing input, whereas ANTLR can
accept a prefix. Do not treat the default ANTLR backend as an interchangeable safety fallback.

Retire HTML delimiters, MathJax macro acquisition and rendering-oriented TeX reconstruction for
new PDF products. Compare the native grammar against actual Docling output before deleting
extensions needed for supported sets, membership, relations, binders and mathematical operators.
Retain only a demonstrable contract gap through native grammar/transformer extension points,
not the full historical frontend by default.

M09 still needs distinct symbol occurrences/positions; native SymPy values can merge or simplify
occurrences. Locate any retained lexical positions within recognized formula text, not PDF byte
coordinates. M11 retains contextual interpretation, simplification and assessment. M13 retains
scope/binding reasoning across section/item relationships. `Dummy`, `Q`, `ask`/`refine` and source
definedness remain useful; no unqualified cancellation or rewrite establishes a domain premise.
Recognition availability is independent of lazy symbolic demand.

**Investigations before deletion:** inline mathematics left inside ordinary prose, multi-line
formulas, equation numbers, matrices/sets/relations, recognition failures, and `f(x)` ambiguity.
An absent formula item does not establish absence of mathematics. In particular, formulas
inside ordinary PDF table cells are a **specific known enrichment gap**, not merely another
inline-text edge case. [Upstream issue #3828](https://github.com/docling-project/docling/issues/3828)
is open as checked 2026-10-31; tagged 2.145.0 enrichment admits code/formula text items, not
ordinary `TableCell` text. Core's rich-cell references can represent a formula relationship,
but that capacity does not establish that PDF conversion populates it.

Before retiring supported table-math handling, inspect actual Siegrist formula-bearing cells.
If the gap is encountered, prefer a supported cell-aware enrichment extension that reuses the
existing cell bounding box/page backend and produces a `FormulaItem` linked through a rich-cell
reference in a derived DoclingDocument. Preserve original cell text, new recognition evidence,
cell/section ancestry and health; do not attempt to reconstruct lost two-dimensional notation
from jumbled plain cell text. If no suitable supported extension exists, record the unresolved
capability and compare Docling-supported `mineru2_pro` (MinerU2.5-Pro) or Nemotron 3.5 Parse on
the affected pages as **investigative alternatives**, not additional selected entry pipelines.
Any eventual replacement of StandardPdfPipeline needs an explicit revised recommendation and
native-text/provenance comparison. Nemotron Parse is distinct from Nemotron-OCR.

Formula coverage must distinguish ordinary detected formulas, inline prose math and table-cell
math, with explicit unassessed/unsupported regions. A successful document conversion or a
nonempty formula list cannot close all three. Preserve unsupported/unknown coverage and a
source-region inspection/reconversion remedy. Do not add a second recognizer
preemptively; resolve actual selected-adapter coverage first.

<a id="O05"></a>
## 7. O05 — Domain consumers actually use the richer structure

**Value:** improve grounding and remove repeated reconstruction. Existing `ProposalPacket.parts()`
exposes sentence text and a small context set; JSON storage alone does not deliver Docling benefits.
Version packet and native source-frame contracts together to include section ancestry, ordered
item references, formula text/health, relevant table structure/headers, captions, page regions
and scope coverage. The packet hash must commit to the actual supplied context.

Derive a reusable text projection for spaCy sentence/token operations from ordered native items.
Keep synthetic separators and prompt-added ancestor headings distinct from source text; never
parse exported Markdown to reconstruct native structure. Preserve intact section identity while
sending bounded item details on demand. Transport pagination does not create semantic chunks.

Replace M13 interval assumptions with declared section ancestry and local statement membership;
physical page breaks do not terminate a logical scope. Preserve each declaration's source position
and forward applicability extent: a mid-section declaration cannot retroactively govern earlier
formulas or leak into sibling units. Heading depth alone does not establish a
symbol binding. Failed inline/formula recognition must prevent false complete-absence conclusions.

Tables remain `TableData.table_cells` with offsets, spans, header roles and item references;
`grid` is a derived view. A cell can be evidence without being turned into a paragraph. Formula,
figure and caption evidence should be eligible for domain operations rather than disappear as
uncovered non-prose. Cross-page table continuation remains a recognized limitation, not an assumed
capability. Proposed recognition/continuation relations must retain their evidence and uncertainty.

**Boundaries:** document structure supplies source observations; only consolidation produces
knowledge claims. No changes to independent automated grading policy or human grading workflows.

<a id="O06"></a>
## 8. O06 — Structural placement, visual inspection and bounded serving

**Value:** direct citation placement and inspectable evidence. Carry packet item/cell/formula
references into proposals and resolve directly against the pinned conversion. Use existing
RapidFuzz alignment only when necessary within an explicit section/item candidate universe;
retain ties, edits and failed placements. Full-book fuzzy matching is not the ordinary route.

Extend source CLI/MCP inspection with hierarchy, item, page-region, table and formula views;
keep explicit pins and bounded results. A formula response can expose recognized LaTeX, untreated
text, interpretation status and source-region reference together. Render a PDF region only for a
real inspection/image consumer. Keep MCP construction lazy so reading a source record does not
load Torch, OCR models or compilers.

Use shared relational metadata to derive Arrow/Parquet exports for concrete table/item analyses;
DuckDB can analyze those views without becoming a competing document authority. Preserve pointer,
conversion, section and geometry columns. No new analytical engine or graph projection is selected
merely because the document model is a graph.

<a id="O07"></a>
## 9. O07 — Book-scale operation and complete HTML retirement

**Value:** reuse conversion, bound live memory and remove obsolete policy paths. One PDF original,
one conversion, 1,589 physical pages and many sections are different units; do not inherit
one-HTML-page-per-task assumptions. Archive exact package/model/configuration identities, including
model revisions and resolved device/runtime choices. A package version with model `main` is not
sufficient reproducibility. Reuse products by complete dependencies; request only demanded math.

Use StandardPdfPipeline's native bounded stage queues/batching before adding document-level
pools. Coordinate parser threads, OCR/inference threads and GPU memory with existing worker
ownership. `ThreadedDoclingParseBackendOptions` exposes `parser_threads`, `max_concurrent_results`
and `release_native_memory_every_n_pages`; `PdfPipelineOptions` exposes stage batch sizes.
Formula enrichment retains native backends for crops, so disabled page-image export alone does
not establish bounded peak memory. Use owned cleanup including `InputDocument.release()` and
review actual long-book lifecycle before claiming feasibility. Page-range conversions are partial
products with their own coverage; concatenation cannot be assumed equivalent to full-book heading
inference or cross-page structure. No arbitrary page-sharding architecture is selected here.

**Dependency selection (operator, 2026-10-31):** use full
`docling[asr,easyocr,htmlrender,ocrmac,onnxruntime,rapidocr,remote-serving,tesserocr,vlm,xbrl]`,
superseding the initial narrow-extra recommendation. Install breadth does not automatically
activate additional source formats or models. The foundation evidence environment resolved this
full distribution independently of the application's held pylatexenc 3.0b2. Application dependency
migration, actual provider selection and lifecycle qualification remain explicit plan obligations.
The [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) owns current execution status.

Delete active HTML producer/repair hooks, CSS-based profiles, HTML macro acquisition and browser
insertion rules. Update admitted operations, archived implementation manifests, defaults,
source indexing, domain method inputs, query capabilities and documentation together. Remove
html5lib/cssselect2/lxml/pylatexenc only after the actual remaining dependency/caller analysis;
transitive library use is different from retaining the application HTML pipeline. Do not delete
frozen migrations, old plans or historical evidence. Minimal archived-record readers preserve
old meanings without retaining active HTML conversion or promising to rerun old adapters.

<a id="O08"></a>
## 10. O08 — Explicit OCR recovery, with targeted verification as a distinct capability

**Value:** recover image/vector text and broken encodings while preserving useful native text.
Use `RapidOcrOptions(backend="onnxruntime", lang=["iso:en"],
mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS, replace_broken_text_layer=True)` as the recommended
initial recipe, with `model_size="small"`, subject to corpus/runtime qualification. Compare
`medium` only for observed difficult text; larger general OCR is not a replacement for layout
or formula structure. Archive model weights/revisions,
`scale`, thresholds, language, orientation and runtime configuration. RapidOCR's default
language is not English, so explicit language is material. A pipeline CUDA accelerator setting does not establish that
RapidOCR/ONNX actually uses a CUDA execution provider. Record the resolved provider/device per
stage and verify availability rather than assume every model shares the same accelerator.
`OcrAutoOptions` selects one
available engine, not an ensemble, and can change results with installed packages.

Tagged `base_ocr_model.py` confirms PDF-aware selection uses PDF-first geometric merging.
It fills missing image/vector regions; it does not independently reread every valid native
string. Broken-text detection can escalate an affected page to full-page replacement without
turning all pages into OCR. The detector can miss plausible wrong digits/symbols, and the
source parse score is not a correctness score for replacement OCR. `LAYOUT_REGIONS` instead
uses OCR-first precedence; `FULL_PAGE` discards ordinary native visible text cells. Prefer
`OcrMode` over the deprecated `force_full_page_ocr` flag. OCR `scale` is distinct from retained
image `images_scale`; retaining page rasters in JSON is not required simply to run OCR.

For consequential numeric/symbol disagreements, recommend **conditional targeted independent
verification**, not a mandatory whole-book second conversion. A different recognizer on the
same rendered region can provide an attributed alternative. Tesseract CLI is a concrete local
candidate; select page segmentation for the crop rather than blindly use a uniform-block mode
for tables. EasyOCR, Surya/OnnxTR plugins and alternative RapidOCR checkpoints are other
candidates when they offer complementary errors. Licenses are not a technical rejection reason.
Nemotron's tagged extra targets Python 3.12/Linux/CUDA; it is not the current Python 3.14
baseline. A future isolated runtime is an alternative only if its benefit warrants the boundary.

**No automatic voting or correction is selected.** Docling's native JSON holds merged selected
content, not every discarded native/OCR candidate. If verification is activated, use separate
recognition-evidence records with page/region, strings, recognizer/configuration, alignment and
resolution outcomes. Match geometry and structure, not array indices; preserve minus signs,
decimal spelling and superscripts. Agreement is corroboration, not proof; unresolved alternatives
remain unresolved. An adopted correction produces a new derived document with provenance,
never an in-place edit to the retained native conversion.

Trigger: an observed missing/corrupt region, unresolved symbol/value, or a separately selected
precision-sensitive consumer needing independent evidence. Do not run all OCR engines or add
custom reconciliation machinery to ordinary conversion without that need. Specialized formula
and table stages remain distinct from character recognition. This opportunity deepens the
scoped semantic model while avoiding a new universal OCR arbitration framework.

Primary mechanism: [tagged OCR selection and merge implementation](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py).

## 11. Alternatives, priority and decision impacts

The coherent sequence is O01/O02/O03 foundation with O08's explicit primary OCR recipe,
O04/O05 consumer redesign, then O06/O07 integration/retirement. These are recommendation dependencies, not a new execution plan.

| Candidate | Disposition in this review | Trigger or reason |
|---|---|---|
| Native Docling JSON plus purpose-built projections | Recommended | Delivers native model and bounded operations under scoped authority. |
| Old HTML-shaped primary model with attached JSON | Rejected | Retains complexity and leaves real consumers blind to structure. |
| Section/subsection hierarchy without chunking | Required by operator | Preserve rich document structure; no demonstrated oversized-section need. |
| Hierarchical/Hybrid/token chunkers | Deferred, not planned | Actual required consumer fails on a measured large section; preserve child hierarchy if reopened. |
| Figure/page-region evidence | Recommended capability | Source-grounded inspection; exact retained raster policy needs consumer choice. |
| Chart extraction/picture descriptions/code enrichment | Conditional | Named analysis consumer and attributable uncertainty; not baseline enrichment. |
| Heron versus Egret Large layout | Focused comparison recommended | Formula/heading/table-region detection on actual dense Siegrist pages; not an assumed global accuracy gain. |
| Formula-stage Granite Docling | Conditional comparison | Demonstrated CodeFormulaV2 transcription failure; retains StandardPdfPipeline entry. |
| TableFormer V2 preview / whole-document VLM | Not baseline | Material corpus limitation; `mineru2_pro` or Nemotron 3.5 Parse are diagnostic candidates, not approved parallel pipelines. |
| Native widget extraction | Deferred | A supported corpus containing native forms; this PDF reports no forms. |
| Raw glyph/font/annotation inventory | Conditional | Concrete evidence or geometry requirement not served by native JSON/original PDF. |
| New graph/service/workflow system | Not selected | No consumer requiring machinery beyond current Core/native operations. |

**Proposed rule impacts for later planning:** RC01 replaces HTML5/DOM source semantics and
profile assumptions; RC02 replaces original-TeX/canonical offset assumptions with qualified PDF
regions and recognized formula text; RC03 versions section units, packet/source-frame and native
source APIs; RC04 scopes upstream Docling schema authority and derived projections; RC05 replaces
old parser/demand/dependency bindings where unnecessary. Reconcile ADR-0036/0037 and affected
D1–D8 owners through the existing ADR route during implementation planning. Accepted records
remain immutable; this review changes no architectural authority or prior completion status.

## 12. Investigation and delivery scenarios

Before production commitment, resolve the following through narrow real-PDF cases in an isolated
probe environment if needed. Do not substitute broad synthetic tests for these uncertainties.

| Question | Sufficient next investigation / required behavior |
|---|---|
| Corpus hierarchy | Sections/subsections on representative book regions; establish level-to-container mapping, no automatic chunks. |
| OCR selection and repair | Native/image/vector cases plus detectably broken text; preserve native precedence and distinguish unverified from verified content. |
| Layout/formula composition | Compare Heron/Egret Large on missed/misclassified regions, then crop margins/repetition controls on transcription; distinguish detection from recognition. |
| Formula coverage/health | Inline/display/table-cell math, inference failure and equation numbers; successful LaTeX distinguished from unchanged fallback text and unsupported cells. |
| Table-math structure | Actual formula-bearing cells retain cell→formula and section relationships; unresolved enrichment is an explicit gap, not complete coverage. |
| Per-stage acceleration | Resolved ONNX provider and model device recorded; CUDA configuration alone is not execution evidence. |
| Direct mathematical input | Feed actual recognized formulas to native SymPy; characterize ambiguity, unsupported constructs and occurrence needs. |
| Table/figure structure | Cell/header/caption evidence and page transition; no false exact numerical/chart recovery or table-continuation claim. |
| Native round trip | JSONB reload and tree/reference consistency, geometry precision, artifact availability, original PDF integrity. |
| Actual consumer use | Small intact section packet reaches source-context hashes, scope, claims and direct citation placement; no whole-book payload. |
| State and reuse | Partial conversion, retry/cancellation and stale publication fences; conversion reuse does not imply symbolic work. |
| Long-book execution | One real full-book conversion after representative cases; assess combined live state before selecting concurrency. |
| Retirement | Fresh PDF-only production journey and historical read without HTML conversion; references/grades are not silently re-anchored. |

These are capability-delivery examples and investigations, not completed qualification. Product
functional checks and independent fidelity assessment remain separate. Existing automated
references may need explicitly versioned PDF anchoring or new independently authored source
references; preserve old answers and grades and never compare mismatched anchors as regression.

## 13. Source map

Production pointers are relative to `python/corpus-structure/src/corpus_structure/`:

- `ingest/html.py`, `ingest/source_capture.py`, `ingest/profile.py`, and repository-root
  `sources/siegrist.yaml`: current repair, CSS, canonicalization and hints.
- `core/locators.py:272`, `ingest/sentences.py:75`: whole-rendition locator and shared text layout.
- `methods/math/{spans,prepared,grammar,scope}.py`: occurrences, native staging, grammar and scope.
- `semantic/proposals.py:519`, `source_frames.py`, `source_projection.py`: actual packet and source evidence.
- `methods/llm/cascade.py:350`, `serve/source.py`, `semantic/parsing_queries.py`: placement and bounded reads.
- `semantic/{parsing_products,parsing_requests,contracts,archive_reader,metadata}.py`: custody,
  demand, implementation archive, historical decoding and physical authority.

Primary library sources (read 2026-10-31; technical-PDF guidance reconciled in place):

- [Docling 2.145.0 pipeline/options](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/standard_pdf_pipeline.py),
  [backend controls](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py),
  [PDF/ML extras](https://github.com/docling-project/docling/blob/v2.145.0/pyproject.toml).
- [Core 2.103.1 document API](https://github.com/docling-project/docling-core/blob/v2.103.1/docling_core/types/doc/document.py),
  [group labels](https://github.com/docling-project/docling-core/blob/v2.103.1/docling_core/types/doc/labels.py).
- [Enrichment usage](https://docling-project.github.io/docling/usage/enrichments/),
  [hierarchy usage](https://docling-project.github.io/docling/usage/heading_levels/),
  [SymPy parsing](https://docs.sympy.org/latest/modules/parsing.html).

The linked tagged sources settle version-sensitive claims where rolling documentation or Context7
snippets disagree. No upstream model quality, source coverage or performance claim is adopted
without corpus evidence.
