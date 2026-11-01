# Docling OCR: comprehensive capability reference

Target: Docling 2.145.0 (code in `docling-slim` 2.145.0; `docling` is the meta package), docling-core 2.105.0,
docling-parse 7.24.2 | Research date: October 31, 2026

This reference covers every route by which Docling turns pixels into text: the OCR engines that run inside
the standard PDF pipeline, the rules that decide which page regions they read, how their output is merged
with a native PDF text layer, the whole-page vision-language OCR models, plugin engines, and the signals
that survive into the converted document. It is written for engineers designing a document pipeline who
need to know what each mechanism actually does, where it silently loses information, and which knobs
exist. The emphasis is on born-digital technical PDFs (papers, standards, reports with mathematics, tables
and vector graphics), but scanned and mixed documents are covered too.

It complements the general Docling reference (`docling.md`). Where the two disagree on OCR behaviour, this
document was checked against tagged 2.145.0 source and should be preferred.

## 1. Orientation and research basis

### 1.1 Four routes from pixels to text

Docling has four distinct OCR-shaped mechanisms. They differ in what they read, what they produce and
where their output lands.

```text
                         PDF / image input
                                |
        +-----------------------+---------------------------+
        |                                                   |
  StandardPdfPipeline                                  VlmPipeline
        |                                                   |
  preprocess: render, native cells,                 (2) whole-page VLM OCR
  parse_score, broken-layer test                    page image -> DocTags / Markdown /
        |                                           HTML / JSON with or without boxes
  layout model -> clusters                                  |
        |                                                   |
  (1) page-stage OCR engine                                 |
  reads selected regions, output                            |
  merged with native text cells                             |
        |                                                   |
  layout postprocess -> tables -> assemble                  |
        |                                                   |
  (3) enrichment models read crops of                       |
  assembled items (formula -> LaTeX, code,                  |
  picture description)                                      |
        +-----------------------+---------------------------+
                                |
                         DoclingDocument
                                |
  (4) region OCR outside conversion: render a crop, call an engine
      directly, keep the result in your own record
```

1. **Page-stage OCR** (sections 2 to 11): a `BaseOcrModel` subclass (RapidOCR, Tesseract, EasyOCR,
   Nemotron OCR, macOS Vision, KServe v2, or a plugin) runs on regions of the rendered page between layout
   detection and layout post-processing. Its text cells are merged with the native PDF text cells.
2. **Whole-page VLM OCR** (section 12): `VlmPipeline` with a `VLM_CONVERT` preset sends each page image
   to a vision-language model that emits text and structure together.
3. **Item enrichment** (section 13): the code/formula model and picture description read crops of items
   after assembly. The formula model is the only built-in route that turns rendered mathematics into LaTeX
   inside the standard pipeline.
4. **Region OCR outside conversion** (section 16): calling an engine directly on chosen crops. Docling
   has no built-in hook for this after conversion, but its backends expose what you need.

### 1.2 Evidence labels

Each consequential claim carries one label.

| Label | Meaning |
|---|---|
| **[doc]** | Stated in official documentation, a model card or a field description. |
| **[src]** | Read in the tagged release source (Docling `v2.145.0`, docling-core `v2.105.0`, RapidOCR `v3.10.0`, plugin wheels) or in a bundled model artifact. |
| **[issue]** | Reported in a GitHub issue or pull request; status given as of the research date. |
| **[inf]** | The author's inference from source or documentation; not executed. |

Nothing in this document was executed against a PDF. Code blocks are illustrative sketches and were not
run. The one measurement is a count of characters in a bundled model file (section 7.6).

### 1.3 Versions and packages

| Package | Version researched | Role |
|---|---|---|
| `docling-slim` | 2.145.0 (2026-10-29) | All pipeline and OCR adapter code |
| `docling` | 2.145.0 | Meta package; extras pull engines (`easyocr`, `tesserocr`, `rapidocr`, `onnxruntime`, `ocrmac`, `vlm`, `remote-serving`, ...) |
| `docling-core` | 2.105.0 | `TextCell`, `PdfTextCell`, `SegmentedPdfPage`, `ProvenanceItem`, `DoclingDocument` |
| `docling-parse` | 7.24.2 (2026-10-29) | Native PDF parsing, shape geometry, page rendering |
| `rapidocr` | 3.10.0 (2026-10-08) | PP-OCR runtime; bundles PP-OCRv6 small det/rec and a v2 classifier |
| `tesserocr` | 2.12.0 (2026-10-22) | Python binding to libtesseract |
| `easyocr` | 1.7.2 (2024-09-24) | CRAFT detector plus CRNN recognisers |
| `ocrmac` | 1.0.1 | macOS Vision wrapper |
| `nemotron-ocr` | 2.0.2 | Nemotron OCR v2 runtime (Python 3.11 to 3.13 by its metadata; Docling requires 3.12) |
| `docling-ocr-onnxtr` | 0.3.1 (2026-10-09) | Plugin: OnnxTR engine |
| `docling-surya` | 0.1.0 (2025-11-02) | Plugin: Surya engine (stale, see section 11.3) |
| `docling-eval` | 1.4.2 | Evaluation harness |

Source paths in links below are relative to
`https://github.com/docling-project/docling/blob/v2.145.0/docling/`. Line anchors were checked against the
2.145.0 wheel, which is byte-identical to the tag for the files cited.

### 1.4 Capability map

| Problem | Mechanism | Section |
|---|---|---|
| Decide which page areas get OCR | `OcrOptions.mode` (`OcrMode`), PDF-aware region selector | 3 |
| Combine OCR with a native text layer | `post_process_cells`, PDF-first / OCR-first merge | 4 |
| Detect and replace garbage text layers | `replace_broken_text_layer`, `is_broken_text_layer` | 5 |
| Pick recognition languages and scripts | `lang`, `iso:` BCP-47 tags, `OcrLanguageResolver` | 6 |
| Fast local CPU OCR | RapidOCR (PP-OCRv6 via ONNX Runtime / OpenVINO / Paddle / Torch) | 7 |
| Mature, configurable OCR with word output | Tesseract CLI / tesserocr | 8 |
| PyTorch OCR with many language packs | EasyOCR | 9 |
| GPU OCR with reading-order grouping | Nemotron OCR v2 | 10.1 |
| Platform OCR on macOS | `OcrMacOptions` | 10.2 |
| Served OCR | `KserveV2OcrOptions` | 10.3 |
| Third-party engines | pluggy plugins (`ocr_engines`), OnnxTR, Surya | 11 |
| Page-to-markup OCR with layout and math | `VlmPipeline` presets | 12 |
| Mathematics | native text, region OCR, formula enrichment, VLM | 13 |
| Tables containing OCR text | TableFormer token assembly | 14 |
| Quality signals and provenance | `TextCell.from_ocr`, `confidence`, `ConfidenceReport` | 15 |
| Targeted re-reading of regions | Backend rendering and shape APIs | 16 |
| Cross-checking engines | Engine agreement patterns | 17 |
| Throughput, offline assets, reproducibility | Threads, batches, artifacts, determinism issues | 18 |
| Measuring and choosing | Benchmarks, born-digital self-labelling, configuration table | 19 |

## 2. Where OCR sits in the standard PDF pipeline

### 2.1 Stage order

`StandardPdfPipeline` is a threaded pipeline of stages connected by bounded queues. The wiring is
**[src]** ([standard_pdf_pipeline.py#L859](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/standard_pdf_pipeline.py#L859)):

```text
preprocess -> layout -> ocr -> layout_postprocess -> table -> (form_field) -> assemble
```

then document-level enrichment (formula/code, picture classification and description) runs on the
assembled `DoclingDocument`.

| Stage | What it does that matters for OCR |
|---|---|
| preprocess | Renders the page image cache (scale 1.0 plus `images_scale`), decodes native text cells into `page.parsed_page` (`SegmentedPdfPage`), rates each cell's text quality into `parse_score`, and, when enabled, runs the broken-text-layer test. In `FULL_PAGE` mode the native cell decode is skipped entirely ([page_preprocessing_model.py#L27](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/page_preprocessing/page_preprocessing_model.py#L27)). **[src]** |
| layout | Predicts clusters (text, section header, formula, table, picture, list item, caption, ...) from the page image. It sees vector glyphs and raster text because it reads pixels. **[src]** |
| ocr | Chooses OCR rectangles from the clusters (section 3), renders each rectangle at `scale`, runs the engine, merges the cells with native cells (section 4) and writes them back to `page.parsed_page.textline_cells`. **[src]** |
| layout_postprocess | Assigns the merged text cells to clusters (a cell belongs to a cluster when at least 20% of the cell's own area lies inside it) and resolves overlaps. Cluster text comes from these cells. **[src]** |
| table | TableFormer predicts structure and fills cells from word and OCR tokens (section 14). **[src]** |
| assemble | Builds document items; each item's text is the concatenation of its cells' text, and provenance is the cluster box. **[src]** |

### 2.2 Consequences of the ordering

- **OCR cannot read what layout did not detect.** Outside `FULL_PAGE` (and broken-layer replacement),
  OCR input rectangles are derived from layout clusters. Text in an area with no cluster is never
  OCR'd. **[src]**
- **OCR runs once, before tables and enrichment.** No later stage re-runs a page-stage engine. The
  formula model reads its own crops of the page image, independently of OCR. **[src]**
- **Item text is cell text.** Whatever the merge keeps is what the document says. There is no later
  reconciliation between OCR text and native text. **[src]**
- **Rendering is required.** OCR crops come from `page._backend.get_page_image(scale, cropbox)`. A
  docling-parse backend configured with `render_pages=False` raises when asked for an image, so OCR cannot
  run on it ([docling_parse_backend.py#L277](https://github.com/docling-project/docling/blob/v2.145.0/docling/backend/docling_parse_backend.py#L277)). **[src]**
- **Image inputs** (PNG, TIFF, JPEG) travel through the same pipeline with no native text, so every
  cluster qualifies for OCR in the PDF-aware mode. **[inf]**

### 2.3 Batching and threads

`ocr_batch_size`, `layout_batch_size` and `table_batch_size` default to 4; `batch_polling_interval_seconds`
is 0.5 and `queue_max_size` is 100 **[src]**. A stage collects up to its batch size or until the polling
interval expires. The built-in engines (except Nemotron) then process the pages of a batch one after
another and the rectangles of a page one after another; only Nemotron buffers crops across pages into
model batches (`batch_size`, default 8) **[src]**. Batch assembly is timer-based, and an open issue reports
that conversion results can depend on machine load because of it
([#4274](https://github.com/docling-project/docling/issues/4274), open) **[issue]**.

### 2.4 Switching OCR off

`PdfPipelineOptions.do_ocr` defaults to `True` **[src]**. With `do_ocr=False` the OCR stage passes pages
through untouched, so clusters whose text is not in the native layer (scans, vector-outlined glyphs,
text inside pictures) produce empty or missing text **[inf]**. The broken-text-layer test only runs when
both `do_ocr` and `replace_broken_text_layer` are on **[src]**.

## 3. Region selection: what OCR actually reads

### 3.1 Modes

`OcrOptions.mode` takes an `OcrMode`
([pipeline_options.py#L107](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py#L107)) **[src]**:

| Mode | OCR input | Merge priority | Native cells |
|---|---|---|---|
| `DEFAULT` | Wired to `PDF_AWARE_LAYOUT_REGIONS` | PDF first | Kept |
| `PDF_AWARE_LAYOUT_REGIONS` | Layout clusters that fail the "text layer accounts for this" test (3.3) | PDF first | Kept |
| `LAYOUT_REGIONS` | Every layout cluster, deduplicated | OCR first | Kept where no OCR cell overlaps |
| `FULL_PAGE` | One rectangle covering the page | OCR only | Not decoded at all |

The deprecated constructor keyword `force_full_page_ocr=True` is still accepted and maps to
`mode=OcrMode.FULL_PAGE` with a deprecation warning **[src]**. The `bitmap_area_threshold` option that
older material mentions no longer exists, so there is no built-in way to OCR only scanned pages
([#4834](https://github.com/docling-project/docling/issues/4834), open); restoring a page-level threshold is
proposed in [PR #4999](https://github.com/docling-project/docling/pull/4999) (open) **[issue]**.

### 3.2 `FULL_PAGE`

The page is OCR'd as one image and the native decode is skipped
(`resolve_skip_cell_extraction`, introduced for vector-dense pages that cost gigabytes to decode,
[#4058](https://github.com/docling-project/docling/issues/4058),
[PR #4061](https://github.com/docling-project/docling/pull/4061)) **[src][issue]**. Consequences:

- No native words or characters, fonts, or rendering modes exist for the page; `word_cells` and
  `char_cells` hold OCR cells only. **[src]**
- Heading-level inference from fonts and any consumer of native glyph metadata lose their input. **[inf]**
- With RapidOCR, a full page rendered at the default scale 3.0 is usually larger than RapidOCR's
  `max_side_len` of 2000 px and is shrunk before detection and recognition (section 7.4). An A4 page is
  about 1785 by 2526 px at scale 3.0, so it is resized to roughly 2000 px tall, an effective 170 DPI. This
  is arithmetic from the configuration, not a measurement. **[inf]**

### 3.3 `PDF_AWARE_LAYOUT_REGIONS` (and `DEFAULT`)

`_find_pdf_aware_layout_ocr_rects`
([base_ocr_model.py#L394](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py#L394))
keeps a cluster for OCR when any of these holds **[src]**:

1. **It overlaps a bitmap.** Any embedded image touching the cluster, however small or decorative,
   sends the whole cluster to OCR.
2. **It contains no visible native text.** Visible means the text rendering mode paints ink (not
   `INVISIBLE` or `ONLY_CLIPPING`). Vector-outlined text and empty regions fall here.
3. **It contains native text and a shape the text does not account for.** The test, per connected shape
   that touches the cluster:
   - Shapes are the page's *connected shape bounding boxes* from the backend
     (`get_connected_shape_bounding_boxes()`), read lazily once per page.
   - A shape whose extent is rule-like (long side at least `RULE_LIKE_ASPECT_RATIO = 12.0` times its
     thickness, or zero thickness) is ignored as a rule, underline or border.
   - Otherwise the shape is **clipped to the cluster** and the clipped probe is tested again for being
     rule-like.
   - The probe is "accounted for" when native text lies on it and either the probe is no thicker than
     `THIN_SHAPE_LINE_HEIGHTS = 2.0` times the median height of the text lines on it, or text covers at
     least `TEXT_BACKED_MIN_COVERAGE = 0.1` of its area.
   - One unaccounted shape sends the whole cluster to OCR.

Text geometry is the visible **text-line** cells. When the backend implements `has_content_in`
(docling-parse does), bitmap and text presence are answered by native queries; otherwise Docling builds
R-tree indexes **[src]**.

The selected cluster boxes are then **deduplicated by rasterisation**: drawn into a binary page-sized
mask, dilated with a 20 px kernel (`DEFAULT_DILATION_SIZE`, at page-point resolution), labelled into
connected components, and replaced by each component's bounding box; boxes contained in another are
dropped ([base_ocr_model.py#L533](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py#L533),
[PR #4748](https://github.com/docling-project/docling/pull/4748)) **[src][issue]**. Selected clusters within
about 10 points of each other therefore become one OCR rectangle, and that rectangle can cover parts of
clusters that were not selected. OCR text read there is subject to the merge rules of section 4. **[inf]**

### 3.4 What the PDF-aware selector misses, and why

The selector is tuned to avoid OCR on good native text (the history:
[#4174](https://github.com/docling-project/docling/issues/4174), closed, reported a fourfold CPU slowdown in
2.123.0, and the source cites it, with #4139, for OCR of rule-crossed native text being slow and lossy; [#4209](https://github.com/docling-project/docling/pull/4209), merged 2026-10-09, brought back OCR for
clusters mixing filled-path glyphs with real text). It errs towards skipping in these cases **[inf]**:

| Pattern | Why it is skipped |
|---|---|
| A paragraph with a few inline symbols or a short formula drawn as filled paths | Native text in the paragraph easily covers 10% of the clipped probe, so the shape counts as accounted for. Section 4.4 shows that OCR could not insert those glyphs even if the cluster were selected. |
| A one-line display equation drawn as paths, with a native equation number such as "(3)" in the same cluster | The probe is at most two line-heights tall and has native text on it, so the thin-band rule accounts for it. |
| Glyph paths fused with a large background fill | docling-parse merges visible shapes whose *bounding boxes* overlap into one connected box. A page-wide fill or frame therefore fuses everything on the page into one box; clipped to a text-heavy cluster, it is accounted for by coverage. |
| Text hidden under an opaque object, or white-on-white | Visibility is decided by rendering mode, not by occlusion ([#4566](https://github.com/docling-project/docling/issues/4566), open). |
| Areas outside all clusters | Never candidates. |

And towards OCR in these cases **[inf]**:

| Pattern | Effect |
|---|---|
| Any cluster touching any bitmap (logos, icons, tiny masks) | OCR runs on the cluster; with PDF-first merge, its output is mostly discarded where native text exists, so the cost buys little. |
| Charts and diagrams drawn as paths with native labels | Thick shapes with sparse text fail the coverage test, so the whole figure cluster is OCR'd. Since 2.121 this has been reported as an 8 to 12 times slowdown on vector-heavy documents ([#4489](https://github.com/docling-project/docling/issues/4489), open). |
| Rasterised text regions under the threaded parser | Reported regressions in [#4139](https://github.com/docling-project/docling/issues/4139) (open). |

A scanned page carrying an invisible text layer from an earlier OCR tool is treated as having no
visible text: docling-parse's `intersects_with` answers for *visible* content only (its docstring says so),
and the fallback path uses `get_visible_text_cells`. Its clusters are therefore OCR'd, and the invisible
cells are added back afterwards wherever no OCR cell overlaps them (4.1) **[src][doc]**.

### 3.5 `LAYOUT_REGIONS`

Every cluster box is OCR'd after the same deduplication, and OCR cells take priority over native cells
([base_ocr_model.py#L289](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py#L289)) **[src]**.
This reads everything the layout model found, including clusters with perfect native text, so it is the
expensive mode. Because of the OCR-first merge it replaces native text wherever an OCR line touches it,
losing font identity and exact characters there. It is useful as a measurement tool (section 19.2) and
for documents whose text layer is untrustworthy but not detectably broken. **[inf]**

## 4. Merging OCR output with the native text layer

### 4.1 Algorithm

`post_process_cells`
([base_ocr_model.py#L619](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py#L619))
**[src]**:

1. If the mode is `FULL_PAGE`, or the page's text layer was found broken and
   `replace_broken_text_layer` is on, the result is the OCR cells only. A broken-layer page also keeps its
   **invisible** native cells (added where they overlap no OCR cell); a `FULL_PAGE` page keeps none.
   `word_cells` and `char_cells` are filtered to OCR cells (plus invisible ones for a replaced page).
2. Otherwise native cells are split into visible and invisible
   (`segregate_by_visibility`; invisible = rendering modes `INVISIBLE` and `ONLY_CLIPPING`; cells with no
   mode, and mode `UNKNOWN`, count as visible).
3. With **PDF first** (`DEFAULT`, `PDF_AWARE_LAYOUT_REGIONS`), every visible native cell is kept and an OCR
   cell is added only if its box overlaps **no** visible native cell. With **OCR first**
   (`LAYOUT_REGIONS`), the roles swap.
4. Invisible native cells are then added where they overlap nothing already kept.
5. The result replaces `page.parsed_page.textline_cells`; `page.cells` reads that list.
6. The page's `ocr_score` is the mean `confidence` of the OCR cells that **survived** the merge.

The overlap test is a plain bounding-box intersection through an R-tree, with no area or IoU threshold
(the code calls it "a weak criterion but it works") **[src]**. Rounding of OCR boxes has caused cells to be
dropped by strict intersection before ([#1644](https://github.com/docling-project/docling/issues/1644))
**[issue]**.

### 4.2 Granularity decides what survives

Native cells are **text lines** (`textline_cells`), and most engines emit **lines** too (table below). Under
PDF-first, one OCR line touching one native line anywhere is dropped entirely, even if most of it covers
text the native layer lacks. Under OCR-first, one native line touching an OCR line is dropped entirely.
**[src][inf]**

| Engine | Cell granularity emitted to Docling |
|---|---|
| RapidOCR | Lines (detector boxes); word boxes not requested |
| tesserocr | Text lines (`GetComponentImages(TEXTLINE)`) |
| Tesseract CLI | Words (TSV level-5 rows) |
| EasyOCR | Detector text boxes after CRAFT grouping (usually word groups or line fragments) |
| Nemotron OCR | Word, sentence or paragraph (`merge_level`, default sentence) |
| macOS Vision | Recognised text observations (typically lines) |
| KServe v2 | Whatever the served model returns; the reference RapidOCR graph gives lines |
| OnnxTR plugin | Words |
| Surya plugin | Lines |

Word-level output does not help with gaps *inside* a native line (the native line box covers the gap),
but it lets OCR words beside native text survive where a whole OCR line would have been rejected
**[inf]**.

### 4.3 Where OCR text can and cannot enter

| Situation | Outcome under PDF first |
|---|---|
| Cluster with no native text (scan, outlined text, empty frame) | OCR text enters. |
| Native text present, OCR reads the same words | OCR is discarded. |
| OCR reads text in a gap between native lines, not touching them | OCR text enters as an extra cell; its reading order within the cluster depends on later ordering. |
| Missing glyphs inside a native text line | **Cannot enter.** See 4.4. |
| Broken layer replaced | OCR replaces all visible native text on the page. |

### 4.4 Inline vector glyphs: an engine-independent gap

A born-digital line such as "the energy E = mc² is ..." where `E = mc²` is drawn as filled paths and the
surrounding words are real text produces a native line cell (or two cells) whose box spans the whole
line, and no characters for the path glyphs. Two rules combine **[src][inf]**:

1. **Selection**: the paragraph cluster has native text covering far more than 10% of the clipped
   shape, so the shape counts as accounted for and the cluster is usually not OCR'd at all (3.3).
2. **Merge**: if the cluster is OCR'd anyway (because a bitmap touches it, or a custom engine passes
   `priority=PDF_FIRST` to `post_process_cells`), any OCR line covering the formula overlaps the native
   line box and is dropped under PDF first.

So no choice of engine, scale or language makes the standard pipeline insert inline path-drawn glyphs
into native lines. Only `FULL_PAGE`/`LAYOUT_REGIONS` with OCR priority (which replace good native text),
a whole-page VLM (section 12), or region OCR with your own reconciliation (sections 13.5, 16) recover
them. **[inf]**

### 4.5 What OCR-first costs

OCR-first discards native line cells that touch an OCR line. The document then carries OCR spelling,
OCR confidences, no font names, and OCR boxes for those lines; hyphenation, ligature and symbol handling
follow the engine, not the PDF. **[inf]**

## 5. Broken text layers

### 5.1 Two separate mechanisms

Docling judges native text in two ways, and only the second acts **[src]**:

| Mechanism | Input | Output | Acts? |
|---|---|---|---|
| Per-cell `rate_text_quality` | Each text-line cell | Page `parse_score` = 10th percentile of cell scores | No; a signal only |
| Page-level `is_broken_text_layer` | All visible cell text of the page, joined by newlines | `page._broken_text_layer = True`, `parse_score = 0` | Yes, when `do_ocr` and `replace_broken_text_layer` are both on: the page is OCR'd in full and its visible native text replaced |

`replace_broken_text_layer` defaults to `False` on every engine's options **[src]**. The field description
states that a low `parse_score` alone never replaces a page **[doc]**. The feature arrived in
[PR #4654](https://github.com/docling-project/docling/pull/4654) (merged 2026-10-27) **[issue]**.

### 5.2 Per-cell quality score

`rate_text_quality`
([page_preprocessing_model.py#L194](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/page_preprocessing/page_preprocessing_model.py#L194))
**[src]**:

- **Hard zero** for a cell containing U+FFFD, a `GLYPH<hex>` placeholder, two or more `/G<digits>` in a
  row, or text that *starts* with two or more `/token` sequences.
- **Penalty** of 0.1 per "fragmented word" match (`x/ab.cd/ef.gh` shapes), applied only once there are at
  least three.
- Otherwise 1.0.

docling-parse emits U+0000 for glyphs it cannot map; Docling replaces it with U+FFFD so these rules see it
([PR #5070](https://github.com/docling-project/docling/pull/5070)) **[issue]**. Because the page score is the
10th percentile, a page where more than about a tenth of the lines contain one unmapped glyph (for
example an unmapped bullet or a ligature) scores 0 even though most of its text is fine **[inf]**.

### 5.3 Page-level test

`is_broken_text_layer`
([text_quality.py#L96](https://github.com/docling-project/docling/blob/v2.145.0/docling/utils/text_quality.py#L96))
returns `True` only when confident, and `False` when unsure **[src]**:

1. Fewer than 20 non-space characters: not broken (`_MIN_CHARS`).
2. A lone junk character followed by a space at the start of a line (an unmapped bullet) is ignored.
3. **Junk share**: control (other than whitespace), surrogate, private-use or U+FFFD characters make up at
   least 3% of the page's non-space characters.
4. **Junk lines**: lines with U+FFFD or a control character after their first character number at least
   max(3, 10% of lines). Private-use characters do not count here (icon fonts use them legitimately).
5. **Wrong Latin** (`_is_wrong_latin`, applied after removing `GLYPH<...>` placeholders), with at least 50
   Latin letters:
   - accented Latin letters (U+00C0 to U+024F) at least half of them: a non-Latin 8-bit font read as
     Latin-1;
   - or, with at least 200 letters in 3 to 20-letter lowercase-bearing tokens, vowels (base letters, plus
     æ œ ø ı ə) under 25%: a shifted ToUnicode map or a legacy font placing another script on ASCII.

### 5.4 What it catches and what it does not

| Catches **[src][inf]** | Misses or mishandles **[issue][inf]** |
|---|---|
| Fonts whose glyphs map to nothing, control codes or the private-use area | A layer broken in a few clusters only: the decision is per page, and the fix is whole-page OCR; replacing only the broken clusters is proposed in [#5059](https://github.com/docling-project/docling/issues/5059) (open) |
| Unmapped ligatures repeated across many lines | Indian scripts ([#5088](https://github.com/docling-project/docling/issues/5088), open) and partially mapped CJK layers ([#4083](https://github.com/docling-project/docling/issues/4083)) |
| Cyrillic or Greek 8-bit fonts decoded as Latin-1 | Text that is wrong but plausible, such as a math font whose Greek glyphs map to Latin letters |
| Caesar-shifted or scrambled Latin text | Pages under 20 characters, or with too few Latin letters for the statistical tests |

A math-dense page set in a symbol font that maps its glyphs into the private-use area can reach the 3%
junk share. The page is then replaced by full-page OCR, losing the good native text of its prose along
with the bad symbols **[inf]**. The `parse_score` of a replaced page stays 0 and keeps describing the
native layer, not the OCR result **[doc]**.

## 6. Language handling

### 6.1 The `lang` field

Every engine's options carry `lang: list[str]`, in order of preference **[doc]**
([pipeline_options.py#L230](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py#L230)):

- A **bare code** is the engine's native code (`deu`, `ch`, `script/Cyrillic`, `en-US`) and is passed
  through untouched.
- A tag behind **`iso:`** is BCP-47 and is canonicalised by `OcrLanguageResolver`
  ([ocr_language.py#L131](https://github.com/docling-project/docling/blob/v2.145.0/docling/utils/ocr_language.py#L131))
  to a language-script pair, so `iso:deu`, `iso:ger`, `iso:de` and `iso:de-DE` all become `iso:de-Latn`,
  then mapped to the engine's code.
- `iso:mul`, `iso:und` and `iso:zxx` are refused **[src]**; a script-qualified `zxx-Latn` slips through
  ([#5105](https://github.com/docling-project/docling/issues/5105), open) **[issue]**.
- An empty list means the engine's default: the Chinese/English PP-OCR model for RapidOCR, per-crop
  script detection for Tesseract, and engine-specific defaults elsewhere **[doc]**.
- A language the engine has no model for raises `OcrLanguageNotSupportedError` instead of silently
  falling back **[doc]**.

Some bare codes collide with BCP-47 meanings: `ch`, `ang`, `frk`, `tab`, `ka` (PP-OCR Kannada versus
BCP-47 Georgian) and `mah` **[src]**. Using `iso:` tags avoids the ambiguity. Canonicalisation was the
subject of [#4075](https://github.com/docling-project/docling/issues/4075) **[issue]**.

### 6.2 Per-engine behaviour

| Engine | Languages per run | Default `lang` | Notes |
|---|---|---|---|
| RapidOCR | One; extras dropped with a warning | `["ch"]` (Chinese + English model) | PP-OCRv6 serves about 52 codes with one multilingual recogniser; other languages route to PP-OCRv5 script models (onnxruntime, openvino, paddle) or PP-OCRv4 (torch) **[doc]** |
| tesserocr / Tesseract CLI | Several, joined with `+` | `eng, spa, fra, deu` | Empty list: OSD picks a script per crop and the matching traineddata is used if installed **[src]** |
| EasyOCR | Several, within one compatible recogniser family | `en, es, fr, de` | No universal multilingual model; some combinations are incompatible **[doc]** |
| Nemotron OCR | One recogniser | `english` | `english` or `multilingual` (zh-Hans, zh-Hant, ja, ko, ru); other Latin languages best-effort on english **[doc]** |
| macOS Vision | Several (preference list) | `en-US, es-ES, fr-FR, de-DE` | `fast` recognition supports fewer languages than `accurate` **[doc]** |
| KServe v2 | First entry, sent verbatim | `english, chinese` | `canonicalize_lang = False`; no mapping **[src]** |
| Auto | Forwarded to the chosen engine | `[]` | Engines lacking the language are skipped during selection **[doc]** |

RapidOCR and Nemotron read one language per run, so a document mixing scripts needs either the
multilingual recogniser or several conversions **[inf]**.

## 7. RapidOCR

RapidOCR packages the PaddleOCR PP-OCR models for ONNX Runtime, OpenVINO, PaddlePaddle and PyTorch. It is
the default engine that Auto selection reaches on Linux without a CUDA-capable Nemotron setup **[src]**.

### 7.1 Model chain

| Stage | Model chosen by Docling | Notes |
|---|---|---|
| Detection | PP-OCRv6 multilingual detector at `model_size` (`tiny`, `small` default, or `medium`) | DB-style text detector: a probability map thresholded into polygons **[doc][src]** |
| Classification | PP-OCR mobile 0/180 line classifier (`ch_ppocr_mobile_v2.0_cls_mobile.onnx`), unaffected by `model_size` | Labels `["0", "180"]`, threshold 0.9; flips whole line crops only **[src]** |
| Recognition | PP-OCRv6 multilingual recogniser at `model_size`, or PP-OCRv5 / v4 script models for languages outside v6 | CTC head; one model covers about 50 languages **[doc][src]** |

PP-OCRv6 (PaddleOCR documentation) uses a PPLCNetV4 backbone, a RepLKFPN detection neck and an
EncoderWithLightSVTR recognition neck with a CTC head, from 1.5M to 34.5M parameters across sizes. Small
and medium cover 50 languages, tiny 49 (no Japanese). Its published figures are from PaddleOCR's own
benchmark: detection Hmean / recognition accuracy of 86.2 / 83.2 (medium), 84.1 / 81.3 (small) and
80.6 / 73.5 (tiny) **[doc]**. They make no claim about mathematics.

The rapidocr 3.10.0 wheel bundles `PP-OCRv6_det_small.onnx` (9.9 MB), `PP-OCRv6_rec_small.onnx`
(21.2 MB) and the classifier, so the default small configuration needs no download **[src]**. Other sizes
and languages are fetched on first use, or prefetched with
`docling-tools models download rapidocr --rapidocr-backend-lang onnxruntime:<lang>`; when
`artifacts_path` is set, Docling expects them there and runs offline **[src]**.

### 7.2 Docling fields

`RapidOcrOptions`
([pipeline_options.py#L372](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py#L372))
**[src]**:

| Field | Default | Effect |
|---|---|---|
| `lang` | `["ch"]` | One language; see 6.2 |
| `backend` | `onnxruntime` | `onnxruntime`, `openvino`, `paddle`, `torch`; torch limits non-v6 languages to v4 models |
| `model_size` | `small` | PP-OCRv6 size; unsupported combinations raise `RapidOcrModelSizeNotSupportedError` |
| `text_score` | 0.5 | Minimum recognition score kept |
| `use_det`, `use_cls`, `use_rec` | `None` (RapidOCR defaults) | Disable stages, for example `use_det=False` to recognise a crop as one line |
| `detect_orientation` | `False` | Re-read poorly read regions at 90/180/270 degrees (7.5) |
| `det_model_path`, `cls_model_path`, `rec_model_path`, `rec_keys_path` | `None` | Custom checkpoints and character dictionaries |
| `font_path` | `None` | Visualisation font only |
| `rapidocr_params` | `{}` | Any RapidOCR config key in dotted form; applied last, overriding Docling's settings |
| `scale` (inherited) | 3.0 | Render scale for crops (216 DPI) |

Docling itself sets `Global.text_score` (0 when `detect_orientation` is on, filtering afterwards), the
onnxruntime `intra_op_num_threads` from `AcceleratorOptions.num_threads`, `use_cuda` from the accelerator
device and `use_dml` when the device is `AUTO` **[src]**.

### 7.3 RapidOCR configuration worth knowing

From rapidocr 3.10.0
[`config.yaml`](https://github.com/RapidAI/RapidOCR/blob/v3.10.0/python/rapidocr/config.yaml), all
reachable through `rapidocr_params` **[src]**:

| Key | Default | Meaning |
|---|---|---|
| `Global.use_preprocess_img` | true | Resize the input within `[min_side_len, max_side_len]` |
| `Global.min_side_len` / `max_side_len` | 30 / 2000 | Bounds on the input image's short and long side, in pixels |
| `Global.use_vertical_padding`, `min_height`, `width_height_ratio` | true, 30, 8 | Letterbox very short or very wide inputs vertically |
| `Det.limit_side_len` / `limit_type` | 736 / `min` | Upscale so the short side reaches 736 px before detection |
| `Det.thresh` / `box_thresh` | 0.3 / 0.5 | Pixel and box score thresholds |
| `Det.unclip_ratio` | 1.6 | How far detected polygons are expanded |
| `Det.max_candidates` | 1000 | Box cap per image |
| `Det.use_dilation`, `score_mode` | true, `fast` | Map dilation and box scoring method |
| `Rec.rec_img_shape` | `[3, 48, 320]` | Line crops are resized to height 48 |
| `Rec.rec_batch_num` | 6 | Recognition batch size |
| `EngineConfig.onnxruntime.enable_cpu_mem_arena` | false | ONNX Runtime arena allocator off |
| `EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_algo_search` | `EXHAUSTIVE` | Reported to make CUDA slower than CPU ([#4167](https://github.com/docling-project/docling/issues/4167); fix proposed in [PR #4168](https://github.com/docling-project/docling/pull/4168), open) **[issue]** |

OpenVINO, Paddle, Torch and TensorRT engine sections exist in the same file **[src]**.

### 7.4 Image geometry: what resolution the model really sees

Three resizes happen inside RapidOCR, on the crop Docling rendered at `scale` **[src]**:

1. `resize_image_within_bounds`: a crop whose long side exceeds 2000 px is shrunk to 2000 (sides rounded
   to multiples of 32); a crop whose short side is under 30 px is enlarged to 30.
2. Vertical letterboxing: a crop no taller than 30 px, or wider than 8 times its height, is padded
   above and below until its height is about a quarter of its width.
3. Detection resize: with `limit_type: min`, the detector input is enlarged until its short side is 736
   px.

Detection and the line crops passed to recognition both come from the image after step 1, so step 1
caps the effective resolution of recognition too. Consequences **[inf]**:

- Raising `scale` above 3.0 does not help regions whose long side already exceeds 2000/scale points
  (667 pt at scale 3.0, more than a full page width); the pixels are discarded again.
- Small regions are cheap to recognise but step 3 enlarges them a lot for detection, so many small
  clusters can cost more detection work than their size suggests.
- `Global.max_side_len` can be raised through `rapidocr_params` for full-page or large-region OCR, at a
  memory and time cost.
- An open issue reports silent downscaling by the detector's input limit
  ([#4131](https://github.com/docling-project/docling/issues/4131)) **[issue]**.

### 7.5 Output, orientation and confidence

- **Cells are lines.** Each RapidOCR result is a quadrilateral, a string and a score. Docling builds an
  axis-aligned box from corners 0 and 2 and maps it back to page coordinates
  ([rapid_ocr_model.py#L777](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/rapid_ocr_model.py#L777)).
  RapidOCR can also return word and single-character boxes (`return_word_box`, `return_single_char_box`
  call arguments) but Docling does not request them **[src]**. Rotated lines get loose boxes **[inf]**.
- **Confidence** is RapidOCR's recognition score for the line, filtered at `text_score` **[src]**.
- **Orientation.** `use_cls` flips individual line crops by 180 degrees. `detect_orientation` handles
  regions turned by 90 or 270 degrees: when a region yields at least 3 lines and fewer than half score
  0.8 or more, Docling re-reads it at 90, 180 and 270 degrees and keeps the first orientation that reads
  well with at least twice as many confidently read characters
  ([rapid_ocr_model.py#L862](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/rapid_ocr_model.py#L862),
  [PR #4709](https://github.com/docling-project/docling/pull/4709), merged 2026-10-29) **[src][issue]**.
  Tall line crops are rotated a quarter turn by RapidOCR itself before recognition, which is why rotated
  regions can read upside down **[src]**.
- **Spacing.** Missing spaces between words have been reported ([#2887](https://github.com/docling-project/docling/issues/2887)) **[issue]**.

### 7.6 Character coverage of the bundled recogniser

The character dictionary embedded in `PP-OCRv6_rec_small.onnx` (rapidocr 3.10.0) has **18,708 entries**,
counted on 2026-10-31 by reading the dictionary stored in the model file **[src]**. It includes:

- all printable ASCII;
- 64 Greek letters, including α β γ δ ε θ λ μ σ π Σ Ω;
- operators and relations ∑ ∫ ∂ √ ∞ ≤ ≥ ≠ ± × ÷ − ∈ ∉ ⊂ ∪ ∩ ∀ ∃, many arrows (→ and others);
- primes and degree ′ ″ ° ‰;
- superscripts ¹ ² ³ ⁰ ⁿ ⁺ ⁻ ⁼ and subscripts ₀ ₁ ₂ ₊ ₋ ₌, but not ⁱ or ₙ.

A CTC recogniser reads a line as one left-to-right sequence. It can emit a superscript digit only if it
recognises the small raised glyph as that precomposed character; it has no notion of a baseline shift,
fractions, radicals spanning content, or two-dimensional layout **[inf]**. Section 13 discusses what this
means for mathematics.

### 7.7 Known problems

- Latin language selection crashing in some configurations ([#3840](https://github.com/docling-project/docling/issues/3840), open) **[issue]**.
- GPU crash reports ([#4886](https://github.com/docling-project/docling/issues/4886)) and CUDA slower than CPU ([#4167](https://github.com/docling-project/docling/issues/4167)) **[issue]**.
- Model-size selection was requested in [#4020](https://github.com/docling-project/docling/issues/4020) and added by [PR #4500](https://github.com/docling-project/docling/pull/4500) **[issue]**.

## 8. Tesseract: tesserocr and CLI

Docling has two Tesseract adapters with the same options and different mechanics **[src]**:

| | `TesseractOcrOptions` (`kind="tesserocr"`) | `TesseractCliOcrOptions` (`kind="tesseract"`) |
|---|---|---|
| Binding | `tesserocr.PyTessBaseAPI` in-process | `tesseract` executable via `subprocess` |
| Orientation | OSD on every crop with a dedicated OSD reader, then rotate by `orient_deg` | `tesseract --psm 0 -l osd` on every crop, then rotate |
| Recognition | `GetComponentImages(TEXTLINE)`, then per line `SetRectangle` + `GetUTF8Text` | `tesseract <png> stdout tsv` once per crop |
| Cells | **Text lines** | **Words** (TSV rows with text) |
| Confidence | `MeanTextConf() / 100` per line ([PR #4534](https://github.com/docling-project/docling/pull/4534)) | TSV `conf / 100` per word |
| Text | stripped `GetUTF8Text` | kept verbatim, read with pandas `QUOTE_NONE` and no NA conversion, so "N/A" or "007" survive ([PR #4536](https://github.com/docling-project/docling/pull/4536)) |
| Concurrency | A lock serialises use of the shared readers ([PR #4941](https://github.com/docling-project/docling/pull/4941)) | One process per call |
| Resolution | Image passed in memory | PNG written with its DPI ([PR #5031](https://github.com/docling-project/docling/pull/5031)) |

Shared fields: `lang` (default `eng, spa, fra, deu`), `path` (tessdata directory), `psm` (page
segmentation mode; `None` means `PSM.AUTO`), and for the CLI `tesseract_cmd`. Arguments passed to the CLI are
sanitised and `psm` is cast to `int` **[src]**. OEM is `DEFAULT` **[src]**.

With an empty `lang`, OSD picks the script for each crop, the matching traineddata is loaded on demand,
and crops whose OSD fails are skipped; this needs `osd.traineddata` **[src]**. With explicit languages, an
OSD failure is logged and recognition proceeds **[src]**.

**Page segmentation modes** (Tesseract documentation) **[doc]**: 0 OSD only; 1 automatic with OSD; 3 fully
automatic (default); 4 single column of variable sizes; 6 single uniform block; 7 single line; 8 single
word; 10 single character; 11 sparse text; 12 sparse text with OSD; 13 raw line. Docling crops are
usually single layout regions, so 6 (block) or 7 (line) can fit better than automatic segmentation for
small regions **[inf]**.

**Model families** **[doc]**: `tessdata` (legacy plus integer LSTM models), `tessdata_best` (float LSTM,
most accurate and slowest), `tessdata_fast` (integer LSTM, fastest). OEM 0 and 2 (legacy engine) are not
supported by the best and fast sets.

The in-process adapter's per-line `SetRectangle` calls re-run recognition for each line rectangle after
the layout pass, so it does more work than the CLI's single TSV pass **[inf]**. The CLI's word cells are
the finest built-in granularity, which matters for the merge (4.2) and for table tokens (14) **[inf]**.
A reliability rework is open ([PR #4942](https://github.com/docling-project/docling/pull/4942)) **[issue]**.

## 9. EasyOCR

EasyOCR uses a CRAFT text detector and CRNN-family recognisers, one per language group, on PyTorch
**[doc]**.

`EasyOcrOptions`
([pipeline_options.py#L569](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py#L569))
**[src]**:

| Field | Default | Effect |
|---|---|---|
| `lang` | `en, es, fr, de` | Languages for one `Reader`; they must share a recogniser family |
| `use_gpu` | `None` | Derived from the accelerator device when unset |
| `confidence_threshold` | 0.5 | Cells below are dropped |
| `model_storage_directory` | `None` | Model directory |
| `recog_network` | `standard` | Recogniser variant; the field description's mention of `craft` is wrong, CRAFT is the detector |
| `download_enabled` | `True` | Allow model downloads |
| `suppress_mps_warnings` | `True` | Silence an Apple MPS warning |

Docling calls `reader.readtext(image)` with **no further arguments**, so EasyOCR's own defaults apply
([easyocr_model.py#L308](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/easyocr_model.py#L308))
**[src]**. Those defaults, from EasyOCR 1.7.2 **[doc][src]**: `decoder="greedy"` (alternatives
`beamsearch`, `wordbeamsearch` with `beamWidth=5`), `allowlist`/`blocklist`, `paragraph=False`,
`min_size=10`, `rotation_info=None`, `contrast_ths=0.1`, `adjust_contrast=0.5`, `text_threshold=0.7`,
`low_text=0.4`, `link_threshold=0.4`, `canvas_size=2560`, `mag_ratio=1`, `slope_ths=0.1`,
`ycenter_ths=0.5`, `height_ths=0.5`, `width_ths=0.5`, `add_margin=0.1`. Changing any of them needs a
subclass or plugin **[inf]**. Making the canvas size configurable is proposed
([PR #4342](https://github.com/docling-project/docling/pull/4342), open), as is CUDA cache handling
([PR #4725](https://github.com/docling-project/docling/pull/4725), open) **[issue]**.

Cells are EasyOCR's detector boxes after its horizontal grouping (`width_ths`, `ycenter_ths`), so their
size varies between words and line fragments; boxes come from corners 0 and 2 of each quadrilateral
**[src][inf]**. There is no orientation handling beyond what `rotation_info` would offer, which Docling
does not pass **[src]**.

## 10. Nemotron OCR, macOS Vision, KServe v2 and Auto selection

### 10.1 Nemotron OCR v2

`NemotronOcrOptions` (`kind="nemotron-ocr"`) wraps NVIDIA's `nemotron-ocr` 2.x
([nemotron_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/nemotron_ocr_model.py))
**[src]**:

- **Runtime gate.** `validate_runtime` requires Linux on x86_64, Python 3.12, a CUDA accelerator device,
  `torch.cuda.is_available()` and a torch build for CUDA 13.x; otherwise it fails with a message naming
  the missing piece **[src]**. Install hint: `docling[feat-ocr-nemotron]` **[src]**.
- **Fields.** `lang` (default `["english"]`; see 6.2), `merge_level` (`word`, `sentence` default,
  `paragraph`), `batch_size` (8).
- **Cross-page batching.** Unlike the other engines, crops are buffered across the pages of a pipeline
  batch and sent to the model in groups of `batch_size`; pages are post-processed and released in input
  order once all their crops are done **[src]**. The field description still says "within the same page",
  which the code no longer matches **[src]**.
- **Model.** Model card for `nvidia/nemotron-ocr-v2` (commit `0e83e83`) **[doc]**: a RegNetX-8GF detector
  (45.4M parameters), a pre-norm Transformer recogniser, and a relational model that predicts reading order
  and groups words into lines and paragraphs. The English variant totals 53.8M parameters with an
  855-character set and 32-token maximum sequence; the multilingual variant 83.9M with 14,244 characters
  and 128 tokens. The card describes evaluation on 23,378 OmniDocBench crops and SynthDoG without
  publishing scores.

The relational model is the distinguishing capability: `merge_level` lets the engine return words for
fine-grained merging, or sentences/paragraphs with its own reading order **[doc][inf]**.

### 10.2 macOS Vision (`OcrMacOptions`)

`kind="ocrmac"`; uses the `ocrmac` package over Apple's Vision framework **[src]**. Fields: `lang` (default
`en-US, es-ES, fr-FR, de-DE`), `recognition` (`accurate` default, or `fast` with fewer languages),
`framework` (`vision`, the only value Docling documents) **[doc]**. Cells are Vision's text observations
mapped back by `scale` **[src]**. macOS only; Auto selection prefers it on Darwin **[src]**.

### 10.3 KServe v2 remote OCR

`KserveV2OcrOptions` (`kind="kserve_v2_ocr"`) sends crops to a KServe v2 / Triton endpoint
([kserve_v2_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/kserve_v2_ocr_model.py))
**[src]**:

- Requires `enable_remote_services=True` on the pipeline options
  ([PR #4418](https://github.com/docling-project/docling/pull/4418)) **[src][issue]**.
- Connection fields from `KserveV2OptionsMixin`: `url`, `model_name` (default `ocr`), `model_version`,
  `transport` (`grpc` default, or HTTP), `headers`, `grpc_metadata`, `grpc_use_tls`,
  `grpc_max_message_bytes` (64 MiB), `grpc_channel_args`, `use_binary_data`, `timeout` (60 s),
  `request_parameters` **[src]**.
- `scale` defaults to **2.0** (144 DPI), unlike the 3.0 of local engines **[src]**.
- `lang` is not canonicalised; the first entry is sent as is (default `["english", "chinese"]`) **[src]**.
- Image preprocessing matches a RapidOCR model graph deployed on Triton, so the reference server is
  RapidOCR behind KServe **[src][inf]**.

Use case: separate GPU OCR serving from CPU conversion workers, or share one OCR deployment across
workers **[inf]**.

### 10.4 Auto selection (`OcrAutoOptions`)

`kind="auto"`. At model construction, Docling tries engines in this order and keeps the first that
imports and accepts the language
([auto_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/ocr/auto_ocr_model.py))
**[src]**:

1. macOS: `ocrmac`.
2. Linux: Nemotron OCR, if installed and `validate_runtime` passes.
3. RapidOCR with ONNX Runtime.
4. EasyOCR.
5. RapidOCR with PyTorch.

Tesseract is never chosen automatically. Only `mode`, `lang` and `replace_broken_text_layer` are
forwarded; `scale`, engine fields and thresholds take the chosen engine's defaults **[src]**. The engine
therefore depends on the machine (installed packages, OS, GPU), so the same configuration can produce
different text on a laptop and a GPU server **[inf]**. Pin a concrete engine wherever results must be
comparable.

## 11. Plugin engines

### 11.1 Mechanism

OCR engines are loaded through a pluggy-based factory
([base_factory.py#L94](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/factories/base_factory.py#L94))
**[src]**:

- A plugin package declares an entry point in the group **`docling`** whose module exposes
  `ocr_engines()` returning `{"ocr_engines": [MyOcrModel, ...]}`; the built-ins are registered the same way
  ([plugins/defaults.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/plugins/defaults.py)).
- Each model class's options type has a unique `kind` string; passing an instance of those options as
  `ocr_options` selects the engine.
- External plugins load only with `allow_external_plugins=True` on the pipeline options (and the CLI
  flag of the same name); the decision is made from entry-point metadata before importing the module
  **[src]**.

### 11.2 OnnxTR (`docling-ocr-onnxtr` 0.3.1)

Wraps OnnxTR, an ONNX export of the docTR model zoo **[src][doc]**:

| Field | Default |
|---|---|
| `lang` | `["en", "fr"]` |
| `confidence_score` | 0.5 |
| `objectness_score` | 0.3 |
| `det_arch` | `fast_base` |
| `reco_arch` | `crnn_vgg16_bn` |
| `reco_bs` | 512 |
| `auto_correct_orientation`, `preserve_aspect_ratio`, `symmetric_pad` | engine options |
| `paragraph_break` | 0.035 |
| `load_in_8_bit` | 8-bit model variants |
| `providers`, `session_options` | ONNX Runtime execution providers and session settings |

Detection architectures include `db_resnet34`, `db_resnet50`, `db_mobilenet_v3_large`, `linknet_*` and
`fast_tiny/small/base`; recognition includes `crnn_*`, `sar_resnet31`, `master`, `vitstr_small/base`,
`parseq` and `viptr_tiny` **[doc]**. Its cells are **words**, the finest granularity available to the
merge **[src]**. It is the most complete alternative CPU engine available as a plugin **[inf]**.

### 11.3 Surya (`docling-surya` 0.1.0)

Published 2025-11-02 and not updated since **[doc]**. In the wheel **[src]**:

- `SuryaOcrOptions`: `lang` (`["en"]`, ignored by the adapter), `use_gpu`, `model_storage_directory`,
  `download_enabled`; the render scale is hard-coded to 3.
- It calls `self.post_process_cells(all_cells, page)` without `conv_res`, but the 2.145.0 signature is
  `post_process_cells(self, ocr_cells, page, conv_res, priority=None)`. That call should raise a
  `TypeError` on current Docling **[inf]**; it was not run.
- It references an undefined `ImportOcrError` on its import-failure path.
- It targets the surya-ocr ≥0.17 API. Surya 2 (`surya-ocr` 0.23.0, released 2026-10-29) changed its output
  to HTML with KaTeX-compatible `<math>` LaTeX, so compatibility is unknown **[doc][inf]**.

Surya 2 reports 92.3% for English on its own 91-language benchmark **[doc]**. To use Surya with
current Docling, write a small plugin against the current Surya API (11.4), or run Surya as region OCR
(16).

### 11.4 Writing an engine

Illustrative sketch, not executed:

```python
from typing import ClassVar, Iterable, Literal, Type

from docling.datamodel.pipeline_options import OcrOptions
from docling.models.base_ocr_model import BaseOcrModel
from docling_core.types.doc import BoundingBox, CoordOrigin
from docling_core.types.doc.page import BoundingRectangle, TextCell


class MyOcrOptions(OcrOptions):
    kind: ClassVar[Literal["my-ocr"]] = "my-ocr"
    lang: list[str] = ["iso:en"]


class MyOcrModel(BaseOcrModel):
    def __init__(self, enabled, artifacts_path, options, accelerator_options):
        super().__init__(enabled=enabled, artifacts_path=artifacts_path,
                         options=options, accelerator_options=accelerator_options)
        self.engine = ...  # load the recogniser once

    def __call__(self, conv_res, page_batch: Iterable):
        for page in page_batch:
            if not self.enabled or not page._backend.is_valid():
                yield page
                continue
            cells = []
            for rect in self.get_ocr_rects(page):          # honours OcrMode
                if rect.area() == 0:
                    continue
                image = page._backend.get_page_image(scale=self.options.scale, cropbox=rect)
                for i, (x0, y0, x1, y1, text, conf) in enumerate(self.engine.read(image)):
                    box = BoundingBox(
                        l=x0 / self.options.scale + rect.l, t=y0 / self.options.scale + rect.t,
                        r=x1 / self.options.scale + rect.l, b=y1 / self.options.scale + rect.t,
                        coord_origin=CoordOrigin.TOPLEFT,
                    )
                    cells.append(TextCell(index=i, text=text, orig=text, confidence=conf,
                                          from_ocr=True,
                                          rect=BoundingRectangle.from_bounding_box(box)))
            self.post_process_cells(cells, page, conv_res)   # merge rules of section 4
            yield page

    @classmethod
    def get_options_type(cls) -> Type[OcrOptions]:
        return MyOcrOptions


def ocr_engines():
    return {"ocr_engines": [MyOcrModel]}
```

Register `ocr_engines` under `[project.entry-points.docling]` in the plugin's packaging metadata. Emit
**word** cells where the engine can, because the merge and the table token assembly both work better with
fine cells (4.2, 14) **[inf]**. Engines that also need language mapping implement
`supported_ocr_languages` and `map_ocr_language` like the built-ins **[src]**.

## 12. Whole-page OCR with vision-language models

### 12.1 What changes

`VlmPipeline` replaces layout, OCR and table models with one model that reads the page image and writes
markup. A `VLM_CONVERT` preset names the model, prompt, response format and inference engine
([stage_model_specs.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/stage_model_specs.py))
**[src]**. Inference engines include Hugging Face Transformers, MLX, vLLM, and OpenAI-compatible APIs such
as Ollama, LM Studio or a remote server (the API route needs `enable_remote_services=True`) **[doc]**.

### 12.2 Presets relevant to OCR in 2.145.0

| Preset | Model | Response format | Boxes |
|---|---|---|---|
| `smoldocling` | docling-project/SmolDocling-256M-preview | DOCTAGS | Yes |
| `granite_docling` | ibm-granite/granite-docling-258M | DOCTAGS | Yes |
| `deepseek_ocr` | DeepSeek-OCR 3B (Ollama `deepseek-ocr:3b`) | DEEPSEEKOCR_MARKDOWN | Yes |
| `granite_vision` | Granite Vision 2B | MARKDOWN | No |
| `pixtral` | Pixtral 12B | MARKDOWN | No |
| `got_ocr` | stepfun-ai/GOT-OCR-2.0-hf | MARKDOWN | No |
| `phi4` | microsoft/Phi-4-multimodal-instruct | MARKDOWN | No |
| `qwen` | Qwen/Qwen2.5-VL-3B-Instruct | MARKDOWN | No |
| `nanonets_ocr2` | nanonets/Nanonets-OCR2-3B | MARKDOWN | No |
| `nemotron_parse_v2` | nvidia/NVIDIA-Nemotron-Parse-2.0 (0.9B) | NEMOTRON_PARSE_V2 | Yes, with classes |
| `nemotron_parse_v3_5` | nvidia/Nemotron-3.5-Parse (0.6B; tables and charts) | NEMOTRON_PARSE_V3_5 | Yes |
| `mineru2_pro` | opendatalab/MinerU2.5-Pro-2604-1.2B (two-step) | MINERU2 | Yes |
| `gemma_12b`, `gemma_27b` | google/gemma-3-12b-it / 27b-it | MARKDOWN | No |
| `dolphin` | ByteDance/Dolphin | MARKDOWN | No |
| `glm_ocr` | zai-org/GLM-OCR (0.9B) | MARKDOWN | No |
| `falcon_ocr` | tiiuae/Falcon-OCR (0.3B) | MARKDOWN | No |
| `lightonocr` | lightonai/LightOnOCR-2-1B | MARKDOWN | No |
| `unlimited_ocr` | Baidu Unlimited-OCR (3.34B MoE; OpenAI-compatible API by default) | UNLIMITED_OCR_MARKDOWN | Yes |
| `chandra_ocr2` | datalab-to/chandra-ocr-2 (5.3B) | CHANDRA_HTML | Yes |
| `dots_ocr`, `dots_mocr` | rednote-hilab dots.ocr family (3B; vLLM by default) | DOTS_JSON | Yes |

Most presets render pages at scale 2.0 **[src]**. Merged after 2.145.0 and therefore unreleased at the
research date: LightOnOCR-3 presets with grounding ([PR #4789](https://github.com/docling-project/docling/pull/4789))
and Unlimited-OCR 2 ([PR #5107](https://github.com/docling-project/docling/pull/5107)) **[issue]**. A
PaddleOCR-VL helper module exists (`utils/paddleocr_vl_utils.py`) but no preset; support is requested in
[#2495](https://github.com/docling-project/docling/issues/2495) **[src][issue]**.

### 12.3 Grounding, provenance and `force_backend_text`

- **Grounded formats** (DOCTAGS, DEEPSEEKOCR_MARKDOWN, UNLIMITED_OCR_MARKDOWN, CHANDRA_HTML, DOTS_JSON,
  NEMOTRON_PARSE_V2/V3_5, MINERU2, DOCLANG) yield items with bounding boxes. **MARKDOWN and HTML**
  responses become items with zero-size, page-level provenance **[src]**.
- **`force_backend_text`** is consumed only by `VlmPipeline`
  ([vlm_pipeline.py#L260](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/vlm_pipeline.py#L260)):
  for each predicted item box it replaces the VLM's text with the native text under that box **[src]**. It
  therefore needs a grounded format, and it reintroduces exactly the inline-glyph gap of 4.4 inside those
  boxes **[inf]**. `PdfPipelineOptions` also declares a `force_backend_text` field, described as bypassing
  the layout model, but `StandardPdfPipeline` never reads it **[src]**.

### 12.4 Trade-offs against page-stage OCR

| | Page-stage OCR (standard pipeline) | Whole-page VLM |
|---|---|---|
| Native text | Kept exactly where present | Regenerated by the model unless `force_backend_text` |
| Mathematics | Linear strings at best; formula enrichment for display formulas | Many models emit LaTeX inline and display math |
| Reading order and structure | Layout model plus rules | Model output |
| Failure mode | Missing text (selection and merge) | Hallucinated, dropped or repeated text |
| Hardware | CPU-friendly | GPU or Apple silicon in practice for anything above ~1B parameters |
| Confidence | Per-cell engine scores | None per token in Docling's output |

Using a VLM as the OCR engine *inside* the standard pipeline (keeping layout and native text) is requested
in [#2711](https://github.com/docling-project/docling/issues/2711) but not built in; a plugin engine (11.4)
can do it **[issue][inf]**.

## 13. Mathematics and technical notation

### 13.1 How mathematics reaches a PDF page

| Form in the PDF | What Docling gets natively | Which OCR route can help |
|---|---|---|
| Glyphs in fonts with correct ToUnicode maps | Characters, often with italics and sizes, but flattened: no fraction or script structure | None needed for characters; structure needs formula enrichment or a VLM |
| Glyphs in fonts with broken or private-use maps | Junk or private-use characters | Broken-layer replacement (whole page, 5) or region OCR |
| Glyphs drawn as filled paths (common from some TeX and office pipelines, and in figures) | Nothing for those glyphs | Selected clusters only (3.4); never inside native lines (4.4) |
| Rasterised equations (images) | Nothing | Page-stage OCR (cluster touches a bitmap), formula enrichment, VLM |

### 13.2 Page-stage engines and mathematics

All page-stage engines output plain strings per line or word **[src]**. At best they produce linear text
such as `E = mc2` or `E = mc²`; superscripts, subscripts, fractions, radicals, matrices and alignment are
lost or garbled **[inf]**. RapidOCR's v6 dictionary covers many mathematical symbols (7.6), which helps
operators and Greek letters but not structure **[src][inf]**. Native text has the same flattening; a
proposal to infer super- and subscripts from glyph size and baseline is open
([PR #4815](https://github.com/docling-project/docling/pull/4815)) **[issue]**. Mathematical content is
also an open request ([#5097](https://github.com/docling-project/docling/issues/5097)) **[issue]**.

### 13.3 Formula enrichment

`do_formula_enrichment=True` runs the code/formula model (`codeformulav2` by default; `granite_docling`
alternative) on items labelled as formulas by layout, reading its own crop of the page image (scale 2.0,
with an expansion factor around the box) and writing LaTeX to the item **[src]**. It reads pixels, so it
works for path-drawn and rasterised formulas alike **[inf]**. Limits:

- It covers only regions the layout model labels as formulas; inline mathematics inside a text cluster
  is not a separate item and is not enriched **[inf]**.
- Formulas inside table cells are not enriched
  ([#3828](https://github.com/docling-project/docling/issues/3828), open) **[issue]**.
- It runs after assembly, independently of page-stage OCR; its LaTeX does not alter the cell text of
  surrounding paragraphs **[src]**.

### 13.4 Whole-page VLMs

Several presets (for example `granite_docling`, `mineru2_pro`, `chandra_ocr2`, `dots_ocr`, `glm_ocr`,
`nanonets_ocr2`) are trained to emit LaTeX for inline and display mathematics **[doc]**. They recover the
structure page-stage OCR loses, at the cost of regenerating native text (12.4).

### 13.5 Targeting the gap

A design that needs inline mathematics from born-digital PDFs can combine native text with targeted
reading **[inf]**:

1. Find candidate regions from the backend: clusters or line boxes that intersect visible shapes that are
   not rule-like (`get_connected_shape_bounding_boxes`, `get_shape_lines`, `get_thin_shape_boxes`, or the
   individual painted paths through docling-parse's page decoder `get_page_shapes`), or lines whose native
   text has suspicious gaps between glyph boxes.
2. Render those regions at a resolution suited to the reader (section 16).
3. Read them with a formula model or a VLM for structure, or with a symbol-rich OCR recogniser for
   linear text.
4. Reconcile with native text in your own record (section 15.4), keeping both readings and their origin.

Shape boxes fuse through overlapping bounding boxes (3.4), so a page frame or background fill can merge
everything into one box. Per-path geometry from the page decoder avoids that **[src][inf]**.

## 14. Tables and OCR

TableFormer predicts the cell grid and then fills cells with **tokens**, matched by position when
`do_cell_matching=True` **[src]**. Tokens are assembled by `_words_and_ocr_cells`
([table_structure_model.py#L53](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/stages/table_structure/table_structure_model.py#L53))
**[src]**:

- native **words** not covered by a surviving OCR line;
- plus OCR **words** (only engines that emit word cells) not lying on a kept native word;
- plus OCR **lines** not covered by any OCR word.

This arrived in [PR #5022](https://github.com/docling-project/docling/pull/5022) (merged 2026-10-27) so that
scanned forms with a few native words keep their OCR text **[issue]**. Consequences **[inf]**:

- With a line-level engine (RapidOCR, tesserocr), one OCR line can span several columns and land as one
  token in one cell, or be split wrongly; word-level engines (Tesseract CLI, OnnxTR, Nemotron at `word`)
  give TableFormer finer tokens.
- In a born-digital table, native words dominate and OCR rarely contributes.
- OCR'd text in table clusters disappearing from Markdown export was reported in
  [#3473](https://github.com/docling-project/docling/issues/3473); related table/OCR work is open in
  [PR #4634](https://github.com/docling-project/docling/pull/4634) **[issue]**.

## 15. Signals, scores and provenance

### 15.1 Cell-level signals

docling-core `TextCell`
([page.py#L281](https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/page.py#L281))
carries `rect` (a rotatable `BoundingRectangle`), `text`, `orig`, `text_direction`, `confidence` and
`from_ocr` **[src]**. Native cells are `PdfTextCell`
([page.py#L364](https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/page.py#L364)),
which adds `rendering_mode`, `widget`, `font_key` and `font_name` and fixes `from_ocr=False`; their
`confidence` is 1.0 **[src]**. OCR cells have `from_ocr=True` and the engine's score in `confidence`
**[src]**.

Engine confidences are not comparable **[inf]**: RapidOCR reports a recognition score for the line;
tesserocr the mean word confidence of a line; the Tesseract CLI per-word confidence; EasyOCR its own
recogniser score after a 0.5 cut-off; Nemotron and Vision their own scales. Calibrate per engine before
combining them.

### 15.2 Conversion confidence

`ConversionResult.confidence` is a `ConfidenceReport` with per-page `PageConfidenceScores`
([base_models.py#L694](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/base_models.py#L694))
**[src]**:

| Score | Page value | Document value |
|---|---|---|
| `parse_score` | 10th percentile of per-cell `rate_text_quality` (5.2); 0 for a broken layer | 10th percentile over pages |
| `layout_score` | From layout cluster confidences | Mean over pages |
| `ocr_score` | Mean `confidence` of OCR cells that survived the merge; NaN when none | Mean over pages |
| `table_score` | Not implemented (NaN) | NaN |
| `mean_score` | NaN-mean of the four | |
| `low_score` | 5th percentile of the four | |

Grades: below 0.5 `POOR`, below 0.8 `FAIR`, below 0.9 `GOOD`, otherwise `EXCELLENT` **[src]**. Caveats
**[inf]**:

- `ocr_score` ignores OCR output the merge discarded, and is NaN on pages where no OCR text survived, so
  it says nothing about whether OCR was needed but skipped.
- `parse_score` judges encoding damage, not completeness: a page missing all its path-drawn glyphs can
  score 1.0.
- A per-page confidence breakdown was the subject of
  [#4233](https://github.com/docling-project/docling/issues/4233) (closed) **[issue]**.

### 15.3 What survives into `DoclingDocument`

A document item's provenance is `ProvenanceItem(page_no, bbox, charspan)`
([reference.py#L205](https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/common/reference.py#L205))
**[src]**. Nothing records whether the text came from OCR, which engine produced it, or its confidence.
Exported JSON therefore cannot distinguish OCR text from native text **[src]**.

To keep cell-level evidence, set `generate_parsed_pages=True` so that each `ConversionResult.pages[i]`
keeps its `parsed_page` (`SegmentedPdfPage` with the merged `textline_cells`, `word_cells`, `char_cells`
and their `from_ocr`/`confidence`), and write what you need into a side record keyed by page and box before
discarding the result **[src][inf]**. A post-OCR hook for layout plugins is requested in
[#4458](https://github.com/docling-project/docling/issues/4458) **[issue]**.

### 15.4 A side record that keeps OCR evidence

Illustrative sketch, not executed:

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

options = PdfPipelineOptions(
    do_ocr=True,
    ocr_options=RapidOcrOptions(
        lang=["iso:en"],
        mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS,
        replace_broken_text_layer=True,
    ),
    generate_parsed_pages=True,
)
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
)
result = converter.convert("report.pdf")

evidence = []
for page in result.pages:
    scores = result.confidence.pages[page.page_no]
    for cell in page.parsed_page.textline_cells:
        if cell.from_ocr:
            box = cell.rect.to_bounding_box()
            evidence.append({
                "page": page.page_no,
                "bbox": box.as_tuple(),
                "origin": box.coord_origin.value,
                "text": cell.text,
                "confidence": cell.confidence,
            })
    print(page.page_no, scores.parse_score, scores.ocr_score, scores.low_grade)
```

### 15.5 Debugging aids

- `settings.debug.visualize_ocr = True` draws OCR rectangles and resulting cells for each page **[src]**.
- `settings.debug.profile_pipeline_timings = True` records stage timings, including an `ocr` entry, in
  `ConversionResult.timings` **[doc]**.
- Logs: the selector logs when a broken layer triggers full-page OCR **[src]**.

## 16. Region OCR outside a full conversion

Docling exposes the pieces needed to read chosen regions after (or instead of) a conversion **[src]**:

| Need | Mechanism |
|---|---|
| Page image at a known scale | `generate_page_images=True` with `images_scale`, then `doc.pages[n].image.pil_image`; or a backend's `get_page_image(scale, cropbox)` |
| Regions | Item provenance boxes (bottom-left origin in PDF points), cluster boxes from `ConversionResult.pages[i].predictions.layout`, or backend shape queries (13.5) |
| Coordinate conversion | `BoundingBox.to_top_left_origin(page_height)`, then multiply by the image scale |
| Engine | Any engine called directly, for example `rapidocr.RapidOCR` with `return_word_box=True` |

Illustrative sketch, not executed:

```python
import numpy as np
from rapidocr import RapidOCR

engine = RapidOCR(params={"Global.max_side_len": 4000})


def read_region(doc, item, scale):
    prov = item.prov[0]
    page = doc.pages[prov.page_no]
    image = page.image.pil_image                          # rendered at `scale`
    box = prov.bbox.to_top_left_origin(page.size.height)
    crop = image.crop((box.l * scale, box.t * scale, box.r * scale, box.b * scale))
    out = engine(np.asarray(crop), return_word_box=True)
    return list(zip(out.txts or [], out.scores or [])), out.word_results
```

Rendering at a higher `images_scale` than OCR's 3.0 helps small symbols; RapidOCR's `max_side_len`
must then be raised or the crop is shrunk again (7.4) **[inf]**. Fonts that are not embedded are rendered
with system fallbacks, so the same PDF can render differently on different machines
([#4995](https://github.com/docling-project/docling/issues/4995), open) **[issue]**.

## 17. Using several engines

Docling runs one page-stage engine per conversion **[src]**. Multi-engine designs are built around it
**[inf]**:

| Strategy | How | Value |
|---|---|---|
| Second reading of selected regions | Run region OCR (16) with a different engine on low-confidence cells, clusters with unaccounted shapes, or pages graded `POOR`/`FAIR` | Catches single-engine errors where they are likely |
| Two conversions | Convert twice with different `ocr_options`, align items by provenance box | Simple, but doubles layout and table cost; layout may differ between runs |
| Plugin engine that wraps two engines | Read each rectangle with both and emit the agreed or better-scoring text | One conversion; full control of the merge |

Comparing readings needs normalisation (Unicode NFKC, whitespace, ligatures, hyphenation, quote and dash
variants) and alignment at word or character level, with confidences calibrated per engine (15.1).
Agreement between engines that share architecture or training data (for example two PP-OCR variants) is
weaker evidence than agreement between unrelated engines **[inf]**. On born-digital pages, native text is a
third, usually more reliable, witness wherever it exists **[inf]**.

## 18. Performance, assets and determinism

### 18.1 What drives OCR cost

Qualitatively **[inf]**:

- **Selected area.** Pixel count grows with the square of `scale`; the selector (3.3) decides how much of
  the page is read. Vector-heavy pages can send whole figures to OCR (#4489).
- **Region count.** Each rectangle is a separate engine call (except Nemotron's batching); RapidOCR's
  detection upscaling (7.4) makes many small regions relatively costly.
- **Full-page mode** reads everything, but skips the native decode, which on extremely vector-dense pages
  is itself the dominant cost (#4058).
- **Shape queries.** The PDF-aware selector reads connected shape boxes only when a cluster has both text
  and shapes, once per page **[src]**.
- **Orientation passes.** RapidOCR `detect_orientation` and Tesseract OSD add extra passes per region
  **[src]**.

### 18.2 Threads and devices

`AcceleratorOptions(device, num_threads)` sets the device for all models and, for RapidOCR on ONNX
Runtime, `intra_op_num_threads` **[src]**. The threaded pipeline runs stages concurrently, so OCR threads
compete with layout, table and parser threads; total CPU use is the sum **[inf]**. `ocr_device`-style
per-stage device choices are not part of `PdfPipelineOptions`; the accelerator device applies to all stages
**[src]**.

### 18.3 Model assets and offline use

| Engine | Where models come from | Offline route |
|---|---|---|
| RapidOCR | Bundled small v6 det/rec and classifier in the wheel; others downloaded | `docling-tools models download rapidocr ...` into `artifacts_path`; or `det/cls/rec_model_path` |
| Tesseract | System traineddata (`tessdata`, `tessdata_best`, `tessdata_fast`) | Install traineddata; set `path` |
| EasyOCR | Downloaded on first use | `model_storage_directory` with `download_enabled=False` |
| Nemotron | Hugging Face download | Model directory resolution in `_resolve_model_dir`; `download_models` |
| VLM presets | Hugging Face, Ollama or a remote server | Pre-pulled weights; `artifacts_path` |

**[src]**

### 18.4 Determinism

Sources of run-to-run or machine-to-machine variation **[issue][inf]**:

- Timer-based batch assembly ([#4274](https://github.com/docling-project/docling/issues/4274), open).
- Auto engine selection depends on the machine (10.4).
- Font fallback rendering ([#4995](https://github.com/docling-project/docling/issues/4995), open).
- GPU kernel selection, for example RapidOCR's `cudnn_conv_algo_search: EXHAUSTIVE`, can choose different
  kernels per machine and run.
- Thread counts can change floating-point summation order on CPU; whether that alters RapidOCR output
  was not checked.

Pinning engine, model files, `scale`, thread count and fonts removes most of these; batch timing needs
the fix tracked in #4274.

## 19. Evaluation, choosing a configuration, open issues and sources

### 19.1 Public benchmarks

| Benchmark | Content | Metrics | Caveat |
|---|---|---|---|
| [OmniDocBench](https://arxiv.org/abs/2412.07626) (CVPR 2025) | 981 pages, 9 document types, 19 layout categories | Normalised edit distance for text and reading order; CDM, NED and BLEU for formulas; TEDS for tables | Page-level end-to-end; mixes OCR with layout and structure |
| [olmOCR-bench](https://github.com/allenai/olmocr) | 1,403 PDFs, 7,010 unit tests: math 3,385, reading order 1,061, text absent 823, text present 721, tables 1,020 | Pass rate of unit tests | Math tests come mostly from arXiv (522 PDFs / 2,927 tests) and old scans (36 / 458); ground truth partly model-assisted |
| PP-OCRv6 figures | PaddleOCR internal benchmark | Detection Hmean, recognition accuracy | Vendor benchmark |
| Surya 2 | 91-language benchmark by Datalab | Accuracy | Vendor benchmark |

**[doc]** These rank systems on their own datasets; none transfers to a specific corpus.
[`docling-eval`](https://github.com/docling-project/docling-eval) (1.4.2) provides dataset builders and
evaluators for running Docling configurations against such datasets **[doc]**.

### 19.2 Born-digital pages as free ground truth

On pages with a good native layer, the native text is ground truth for an OCR engine's reading of the
same regions **[inf]**. Converting a sample with `LAYOUT_REGIONS` (OCR first) and comparing OCR cells
with the native cells of a PDF-aware run, region by region, measures each engine's character error rate,
symbol handling and spacing on the corpus's own fonts and layouts, without labelling. It does not measure
recognition of degraded scans or of path-drawn glyphs (which have no native text by definition).

### 19.3 Choosing a configuration

| Document population | Starting configuration | Why |
|---|---|---|
| Born-digital, good text layer, few images | `PDF_AWARE_LAYOUT_REGIONS`, `replace_broken_text_layer=True`, a fixed engine | OCR only where native text is absent; broken pages repaired **[inf]** |
| Born-digital with path-drawn mathematics | As above, plus formula enrichment, plus region reading of shape-bearing lines (13.5), or a grounded VLM for affected pages | Page-stage OCR cannot insert inline glyphs (4.4) **[inf]** |
| Vector-heavy figures and diagrams | PDF-aware, accept figure OCR cost, or lower the scale for figure clusters through a plugin | #4489 slowdown **[issue][inf]** |
| Scans | PDF-aware reads every layout cluster of a text-less page; `FULL_PAGE` also reads text the layout model missed. Raise RapidOCR `max_side_len` for full pages | 3.2, 7.4 **[inf]** |
| Mixed scans with old OCR layers | PDF-aware; invisible layers are treated as absent and kept as fallback | 3.4 **[src]** |
| Rotated pages | RapidOCR `detect_orientation=True`, or Tesseract (OSD) | 7.5, 8 **[src]** |
| Non-Latin or mixed scripts | `iso:` tags; RapidOCR v6 multilingual, Tesseract with several languages, or Nemotron multilingual for CJK and Russian | 6.2 **[doc]** |
| Tables from scans | Word-level engine (Tesseract CLI, OnnxTR) | 14 **[inf]** |
| GPU available, Linux | Nemotron OCR, or a grounded VLM preset | 10.1, 12 **[doc]** |
| Reproducible batch processing | Never `OcrAutoOptions`; pin engine, models, scale, threads | 18.4 **[inf]** |

### 19.4 Open issues and pull requests to watch

| Number | Topic | Status (2026-10-31) |
|---|---|---|
| [#4489](https://github.com/docling-project/docling/issues/4489) | PDF-aware OCR of every cluster touching a vector shape, 8 to 12 times slower | Open |
| [#4139](https://github.com/docling-project/docling/issues/4139) | Threaded parser regresses OCR on rasterised regions | Open |
| [#5059](https://github.com/docling-project/docling/issues/5059) | Replace only broken clusters, not whole pages | Open |
| [#5088](https://github.com/docling-project/docling/issues/5088) | Broken-layer detection for Indian scripts | Open |
| [#5105](https://github.com/docling-project/docling/issues/5105) | `zxx-Latn` accepted as an OCR language | Open |
| [#4274](https://github.com/docling-project/docling/issues/4274) | Results depend on machine load | Open |
| [#4995](https://github.com/docling-project/docling/issues/4995) | Rendering depends on system fonts | Open |
| [#4131](https://github.com/docling-project/docling/issues/4131) | Detector input limit downscales silently | Open |
| [#4566](https://github.com/docling-project/docling/issues/4566) | Occluded text counted as visible | Open |
| [#3828](https://github.com/docling-project/docling/issues/3828) | Formula enrichment in table cells | Open |
| [#4146](https://github.com/docling-project/docling/issues/4146), [PR #4148](https://github.com/docling-project/docling/pull/4148) | Tagged-PDF structure tree ingestion | Open |
| [PR #4815](https://github.com/docling-project/docling/pull/4815) | Super/subscript from glyph size and baseline | Open |
| [PR #4168](https://github.com/docling-project/docling/pull/4168) | RapidOCR CUDA algorithm search | Open |
| [PR #4942](https://github.com/docling-project/docling/pull/4942) | Tesseract reliability | Open |
| [PR #4342](https://github.com/docling-project/docling/pull/4342), [PR #4725](https://github.com/docling-project/docling/pull/4725) | EasyOCR canvas size, CUDA cache | Open |
| [#4458](https://github.com/docling-project/docling/issues/4458) | Post-OCR hook for layout plugins | Open |
| [#2711](https://github.com/docling-project/docling/issues/2711), [#2495](https://github.com/docling-project/docling/issues/2495) | VLM as OCR engine; PaddleOCR-VL | Open |
| [PR #4789](https://github.com/docling-project/docling/pull/4789), [PR #5107](https://github.com/docling-project/docling/pull/5107) | LightOnOCR-3 and Unlimited-OCR 2 presets | Merged after 2.145.0 |

Statuses were taken from GitHub search results on the research date; check before relying on them.

### 19.5 Resource map

- OCR concept page: <https://docling-project.github.io/docling/concepts/OCR/>
- Pipeline options reference: <https://docling-project.github.io/docling/reference/pipeline_options/>
- Plugins: <https://docling-project.github.io/docling/concepts/plugins/>
- Base OCR model (selection and merge):
  <https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py>
- Engine adapters:
  <https://github.com/docling-project/docling/tree/v2.145.0/docling/models/stages/ocr>
- Text-quality heuristics:
  <https://github.com/docling-project/docling/blob/v2.145.0/docling/utils/text_quality.py>
- Language resolver:
  <https://github.com/docling-project/docling/blob/v2.145.0/docling/utils/ocr_language.py>
- VLM presets:
  <https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/stage_model_specs.py>
- docling-core page types:
  <https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/page.py>
- RapidOCR configuration: <https://github.com/RapidAI/RapidOCR/blob/v3.10.0/python/rapidocr/config.yaml>
- PP-OCRv6: <https://www.paddleocr.ai/>
- Tesseract page segmentation and models: <https://tesseract-ocr.github.io/tessdoc/>
- EasyOCR API: <https://www.jaided.ai/easyocr/documentation/>
- Nemotron OCR v2: <https://huggingface.co/nvidia/nemotron-ocr-v2>
- OnnxTR plugin: <https://github.com/felixdittrich92/docling-OCR-OnnxTR>
- Surya: <https://github.com/datalab-to/surya>
- OmniDocBench: <https://github.com/opendatalab/OmniDocBench>
- olmOCR-bench: <https://github.com/allenai/olmocr>
- docling-eval: <https://github.com/docling-project/docling-eval>
