# PDF conversion and intact document hierarchy

**Status:** Planned target, 2026-10-31; no conversion or hierarchy qualification claimed.
[Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns PDF-04/05 state and opportunity disposition.
Basis: review [O01](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O01),
[O03](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O03),
[O04](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O04) and
[O08](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O08), revision `2c33372`.

## Foundation and responsibility

`ingest/html.py`, `source_capture.py`, `profile.py` and root `sources/siegrist.yaml` currently
own DOM repair, CSS roles, rendered markers, macro acquisition and canonical text. Replacing
just the parser call would retain those assumptions and discard much of Docling's value.
Replace the active ingress adapter and introduce native document products; PDF-05 supplies
qualified views for existing text consumers. PDF-02 owns shared semantics, PDF-03 storage and
PDF-09 coherent publication/lifetime. No producer may bypass their native integrity contracts.

<a id="PDF-04"></a>
## PDF-04 — PDF-only conversion and attributable recognition

**Owner:** ingest/native adapter. **Inputs:** immutable PDF original and admitted resolved
conversion specification, PDF-02 prepared contract, I01/02/03 conclusions. **Outputs:** native
DoclingDocument plus separate health/coverage, versioned dependency and artifact bindings.
Production persistence requires PDF-03/09; pure adapter preparation need not wait for deployed DDL.

Use `DocumentConverter(allowed_formats=[InputFormat.PDF], format_options={InputFormat.PDF:
PdfFormatOption(pipeline_cls=StandardPdfPipeline, pipeline_options=...)})` and `convert()`.
Enforce PDF-only applicability at registration/dispatch as well as the adapter; an HTML input
must not reach an alternate active parser through a generic converter. Retain bytes through
existing original custody before conversion so failure does not lose evidence. The title,
metadata and physical pages belong to the PDF original/conversion, not former HTML page IDs.

### Initial recipe and selection rules

| Stage | Mechanism | Meaning and qualification |
|---|---|---|
| PDF backend | `docling-parse` through the selected PdfFormatOption | Native cells/geometry feed StandardPdfPipeline; pin actual backend/options. |
| OCR | `RapidOcrOptions(backend="onnxruntime", lang=["iso:en"], model_size="small", mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS, replace_broken_text_layer=True)` with `do_ocr=True` | Native-text-preserving baseline; resolves missing raster/vector text and detectably broken pages, not independent rereading of every character. |
| Layout | `LayoutObjectDetectionOptions.from_preset("layout_heron_default")`, compared with `layout_egret_large` | I02 selects on actual formula/heading/table-region detection, preserving tradeoffs; no automatic largest-model choice. |
| Tables | `TableStructureOptions(mode=TableFormerMode.ACCURATE, do_cell_matching=True)` with `do_table_structure=True` | V1 baseline; native cell matching and inferred grid/header roles remain distinct. |
| Formulas | `do_formula_enrichment=True`, `CodeFormulaVlmOptions.from_preset("codeformulav2", scale=2.0, expansion_factor=0.18, stop_on_repetition=True)` | Native enrichment inside StandardPdfPipeline, not whole-document VlmPipeline. |
| Hierarchy | `HeadingHierarchyOptions(enabled=True)` | Resolve bookmark/numbering/style signals; PDF-05 ensures actual containment. |

Archive effective options, exact model revisions/artifacts, selected engines and actual provider/
device per stage. A CUDA accelerator setting does not establish ONNX CUDA execution. Do not
use auto-engine selection for the admitted baseline. OCR `scale`, retained-image `images_scale`
and formula crop `scale` have different roles; changing one does not promise improvement in another.

If I02 reveals crop contamination/repetition, compare `expansion_factor=0.08` with the baseline
on adjacent text/equation numbers and clipped formula parts. Preserve `max_size` and `engine_options`
when selected; repetition stopping is protection, not correctness. Granite Docling is a conditional
formula-stage alternative for an observed gap. Whole-document VLM alternatives need a changed
explicit recommendation, not a silent adapter fallback.

### Health and mathematical coverage

`ConversionResult.status/errors/confidence` are outside native document JSON. Map conversion
success/partial/failure through the application contract, retain available diagnostics, and keep
schema validity and fidelity separate. Confidence is a signal, not a calibrated correctness verdict;
missing table confidence is not a successful table check.

The tagged formula stage catches batch exceptions and yields unchanged text items. I03 must
select an attributable stage-result route; neither `FORMULA`, nonempty `text`, nor `text != orig`
proves successful LaTeX recognition. Capture actual stage success/failure when available through
supported integration; otherwise expose unknown. Do not classify source text as invalid because
the model runtime failed. A returned native document cannot satisfy stronger required health by
itself.

Keep detected-formula, inline-prose-math and table-cell-math coverage separate. Ordinary PDF
TableCells are a known enrichment gap. If actual corpus cases require recovery, use a supported
cell-aware extension reusing cell geometry/page backend and creating FormulaItem/rich-cell links
in a **derived** document, with original text and recognition evidence retained. I03 must settle
that route; it is not assumed available. Jumbled cell text is not recoverable spatial LaTeX by
string cleanup. Keep unresolved required support open, not closed by recording partiality.

Optional independent OCR requires an actual consequential uncertainty/selected precision consumer.
Use another recognizer on the affected region rather than repeat full layout/table assembly for
the whole book. Retain candidates, geometry, configuration, alignment and unresolved outcomes.
No voting framework or automatic correction is baseline scope. A correction creates a derived
product and does not mutate native conversion JSON.

**Acceptance:** real native/image/vector/broken-text cases with recorded source coverage;
explicit formula-stage failure; inline/display/table formula cases; malformed/unsupported input
and cancellation preserve original custody. Stronger formula requirements refuse or report
unavailable honestly. Pure checks cannot replace actual I01/I03 corpus/runtime conclusions.

<a id="PDF-05"></a>
## PDF-05 — Sections, subsections and derived source views

**Owner:** document organization/projection. **Inputs:** PDF-04 native document, I04, PDF-02
identity/relationship/selection agreement; PDF-03 for persistence. **Outputs:** intact hierarchy,
ordered section/item membership, source-qualified text/region views consumed by PDF-06–08.

Use native body-tree reading order through `iterate_items()` and reference resolution, preserving
non-body layers separately. Do not infer order from `texts[]` or sort by PDF coordinates. Heading
levels do not establish full section containers. First inspect actual conversion output; preserve
it unchanged. Where necessary, construct a versioned derived DoclingDocument using
`GroupLabel.SECTION`/`CHAPTER`, `add_group(parent=...)` and supported item references. Map every
derived occurrence to its original conversion pointer and declare grouping/heading inference.

Preserve sections/subsections, ordered lists, formulas, tables, captions and figures. The
organization operation must not convert group names into invented author text or mark visual
inference as author-supplied markup. Tree/reference validation precedes identity; validation
that normalizes geometry must finish before publication. An item with several source regions
retains them all. Repeated equations or paragraphs in separate sections remain separate occurrences.

**No chunking:** no HybridChunker, token windows, section splitting or chunk rows. Methods select
an intact section/subsection or typed items under it. Declare direct-content versus descendant
selection per method so parent/child analysis does not duplicate observations. Ancestor context
is referenced without copying the whole book into each work unit. Physical pages and transport
pagination do not become section boundaries. Reopen splitting only after a real required-consumer
failure; any future parts must be lower-level child groups in this derived hierarchy.

Project ordered content once for spaCy sentence/token consumers. Preserve native item/cell/formula
mapping, codepoint units, synthetic separators and contextual heading insertions separately.
Do not flatten to Markdown and parse it again. Where formula symbol offsets are needed, their
space is recognized LaTeX, not PDF bytes or implied character geometry. Keep table spans/header
flags and caption relationships natively available beside text views. PDF-06/07 consume those
views rather than rebuild hierarchy or scope from global text scans.

**Acceptance:** nested hierarchy survives page breaks, source and derived trees reload with
resolvable links, furniture stays distinguishable, direct/descendant selection preserves intended
multiplicity, and identical text under two sections cannot alias identities. Sentence/token views
reconstruct their declared projected text and expose synthetic material. A one-section read does
not hydrate every page/item of the book.

## Sources and boundary conditions

Read [Docling](../../libraries/docling.md), [OCR technical guidance](../../libraries/docling_ocr.md),
and the review's [source map](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#13-source-map).
Use Context7 first for newly uncertain API details, then pinned tagged source. Important sources:
[2.145.0 options](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py),
[standard pipeline](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/standard_pdf_pipeline.py),
[core document API](https://github.com/docling-project/docling-core/blob/v2.103.1/docling_core/types/doc/document.py),
and [table-formula issue](https://github.com/docling-project/docling/issues/3828).

The tagged release retains needed heading lines internally; do not enable all parsed-page
retention merely for style-based hierarchy. Raw glyph/annotation retention, interactive forms,
charts and generative picture descriptions remain conditional at the coordinator, not omitted
mandatory conversion scope.
