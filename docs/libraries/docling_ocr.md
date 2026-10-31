# Docling OCR — Comprehensive guide for born-digital PDFs

Docling 2.145.0 · October 31, 2026 · Focus: PDFs with native text, layout and embedded content → structured `DoclingDocument` JSON

## 1. Executive conclusions

OCR can add significant value even when a PDF already has an embedded, selectable text layer. In Docling, OCR is not limited to recovering text from scanned pages. It can complement native PDF extraction, recover visually rendered content missing from the text layer, replace corrupted text, and provide an independent recognition result for quality verification.

The important distinction is between three uses of OCR:

1. Content recovery: Extract additional text from embedded images, vector-drawn glyphs, diagrams and regions absent from the native PDF text.
2. Corrective OCR: Replace unusable native text—particularly defective font-to-Unicode mappings—with visually recognized text.
3. Independent verification: Compare one or more OCR recognizers against the native text to identify disagreements and possible errors, without automatically treating the OCR result as authoritative.

Docling provides native functionality for the first two. The third is possible through additional OCR passes and integration with Docling's intermediate representations, but Docling does not provide a general-purpose, automatic multi-engine OCR voting and reconciliation system as part of its standard PDF pipeline.

### Recommended operating model

For PDFs with embedded text, the strongest general starting point is:

Preserve native PDF text where it is reliable; selectively OCR regions where it is incomplete; use additional OCR engines to validate or repair specific uncertainties.

That is preferable to simply replacing every page with OCR-generated text. The native layer can preserve exact characters, punctuation, Unicode, and source geometry that raster recognition may degrade.

| Processing strategy                         | Principal purpose                                                    | Expected value for born-digital PDFs                           |
| ------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------- |
| Native PDF text only                        | Recover embedded text exactly as encoded                             | Strong when font mappings and source geometry are correct      |
| Native text + PDF-aware selective OCR       | Recover missing visual text without replacing valid native text      | Best general baseline                                          |
| Native text + broken-text repair            | Automatically correct detectably corrupted text layers               | High-value reliability enhancement                             |
| OCR of all detected layout regions          | Prefer visual recognition within detected document regions           | Useful for targeted troubleshooting and alternative extraction |
| Full-page OCR                               | Reconstruct text from the rendered appearance                        | Fallback for severely unreliable text layers                   |
| Independent second OCR engine               | Detect disagreements and provide alternate candidates                | Useful for precision-sensitive content                         |
| OCR + specialized code/formula/chart models | Recover semantic structures ordinary OCR cannot represent adequately | Useful for technical, scientific and financial PDFs            |

Docling's source confirms that its default OCR mode is already PDF-aware selective OCR, rather than indiscriminate full-page OCR. It also confirms that the default merging policy favors native PDF cells in overlapping regions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary sources:

[https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py?utm_source=chatgpt.com)

## 2. How Docling combines native PDF text and OCR

The key architectural point is that Docling combines text at the page text-cell layer, before assembling the final semantic document.

A conventional born-digital PDF conversion follows this approximate sequence:

PDF text and OCR integration

Conceptual standard PDF pipeline. OCR recognition and cell merging happen before the final structured document is assembled.

This is important for your JSON objective. Docling does not ordinarily store native text and OCR transcriptions as two parallel, independent alternatives in `DoclingDocument.texts[]`. It resolves competing text cells before the semantic object is constructed.

Consequently, changing the OCR mode can change not only the recognized text but also the reconstructed paragraphs, tables, reading order and source spans.

### 2.1 The PDF-first merge policy

Docling's OCR implementation defines two merge priorities:

- `PDF_FIRST`: retain native visible text cells; add OCR cells only where they do not overlap existing native cells.
- `OCR_FIRST`: retain OCR cells; add native visible cells only where they do not overlap OCR cells.

The overlap test is geometric, using bounding boxes. It is not a text-quality comparison between two candidate strings.

That distinction has two important consequences.

A native text cell containing an incorrect but plausible string can prevent a correct OCR candidate from being used when PDF-first precedence applies.

Conversely, OCR-first precedence can replace correct programmatic text with a visually misrecognized result.

The source also distinguishes visible native text from invisible PDF text cells, such as hidden OCR layers or clipping-only text. Invisible cells are handled separately to avoid treating them like ordinary visible text during merging.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 2.2 Why multiple OCR engines are a separate concern

`PdfPipelineOptions.ocr_options` selects one OCR engine configuration for the standard pipeline. The engine can internally use multiple detection, classification and recognition models, but that is not the same thing as running several independent OCR engines and reconciling their outputs.

Likewise, `OcrAutoOptions` chooses one available engine, rather than running all available engines.

To compare RapidOCR, Nemotron-OCR and Tesseract on the same source, one can use separate conversions or specialized custom processing. The resulting candidate texts require alignment, evidence comparison and a deliberate selection policy before being incorporated into a canonical JSON representation.

This is potentially valuable, but running more recognizers does not automatically produce more accurate information.

## 3. All OCR region-selection modes

Docling 2.145.0 exposes four `OcrMode` values. These determine which page regions are sent to the selected OCR engine and how the OCR results compete with embedded PDF text.

| Mode                       | OCR coverage                                                                   | Overlap precedence               | Suitability for structured PDFs                        |
| -------------------------- | ------------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------ |
| `DEFAULT`                  | Currently PDF-aware selective regions                                          | PDF-first                        | General-purpose baseline                               |
| `PDF_AWARE_LAYOUT_REGIONS` | Regions with bitmap content, missing native text, or unexplained vector shapes | PDF-first                        | Explicit version of the baseline                       |
| `LAYOUT_REGIONS`           | Every detected layout region                                                   | OCR-first                        | Alternative recognition where native text may be wrong |
| `FULL_PAGE`                | Entire rendered page                                                           | OCR replaces native visible text | Severe corruption or controlled fallback               |

### 3.1 `DEFAULT` and `PDF_AWARE_LAYOUT_REGIONS`

Preferred baseline for born-digital PDFs

These two modes currently execute the same selection logic in Docling 2.145.0.

The PDF-aware selector starts from layout-detected regions and sends a region to OCR when at least one of these conditions is met:

- The region overlaps a bitmap, which may contain rasterized text.
- It contains no visible native PDF text, even though content may have been drawn as vector outlines.
- It contains visual shapes not adequately explained by the programmatic text already present.

The third condition is a particularly valuable capability.

Consider a technical diagram drawn with vector graphics. Most of the PDF page has ordinary embedded text, but a few labels inside a schematic are rendered as filled vector paths rather than as PDF character objects.

Those labels have no usable programmatic text. Docling's PDF-aware logic can recognize that the geometry is not explained by the native text layer and attempt OCR on the corresponding region.

It is also careful not to treat every vector object as missing text. Rules, underlines, table borders, background fills and highlighted text are common in digital PDFs.

The current implementation distinguishes rule-like geometry and checks whether programmatic text plausibly accounts for the shape. This helps avoid unnecessary OCR and protects correct native text from being replaced.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



What this mode does not do: it does not independently re-read every clean native text region to verify the characters. Therefore, a seemingly valid native string such as `O.05` where the page visibly says `0.05` may survive unchanged.

### 3.2 `LAYOUT_REGIONS`

This mode passes all detected layout clusters to the OCR engine without first excluding regions already served by native PDF text.

It then gives the OCR cells precedence over overlapping native PDF cells.

This is useful when the PDF text layer looks plausible but is known to be unreliable, or when investigating whether the visible document differs from the programmatic text.

Unlike `FULL_PAGE`, layout-region OCR operates on the detected regions rather than treating the entire page as one OCR input. This can improve crop focus, although it also makes OCR coverage dependent on layout detection.

The main disadvantage is that visually recognized text may displace perfectly correct native text. Small characters, mathematical notation, punctuation, and dense tables are common areas of risk.

Use it as an alternative extraction path, not as an unconditional upgrade from PDF-aware mode.

### 3.3 `FULL_PAGE`

This mode OCRs the entire rendered page and replaces the visible native text-cell representation with the OCR result.

A less obvious implementation detail: Docling can skip native text-cell decoding in this mode because the ordinary native cells would be discarded anyway. This can substantially avoid parser work on extremely vector-dense documents. It also means full-page OCR is not automatically an appropriate way to preserve all native PDF semantics.

Full-page OCR is most suitable when the text layer is broadly unusable or when a complete visual transcription is specifically wanted.

For a structured PDF, using it indiscriminately can discard the advantages of accurate embedded text, particularly precise symbols, character codes, and native text geometry.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.4 Deprecated full-page control

`force_full_page_ocr=True` remains supported as a compatibility alias for full-page mode, but is deprecated.

Use:

```
from docling.datamodel.pipeline_options import OcrModeocr_options.mode = OcrMode.FULL_PAGE
```

rather than setting the older `force_full_page_ocr` property.

The four modes and their current behavior are defined in the version-tagged pipeline options and OCR implementation:

[https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py?utm_source=chatgpt.com)

## 4. Automatic repair of broken native PDF text layers

`replace_broken_text_layer` is particularly relevant for your use case because it addresses a failure mode specific to PDFs containing ostensibly valid embedded text.

### 4.1 What constitutes a broken text layer?

Some PDFs render correctly but their internal font encoding does not map glyphs to the intended Unicode characters.

For example, the reader sees a word correctly, but programmatic extraction returns an unrelated sequence of characters.

Docling can detect several patterns associated with this problem:

- Unicode replacement characters (`�`) and certain control or private-use characters.
- Unmapped or incorrectly encoded font glyphs.
- Text that appears to be a different script misdecoded as accented Latin characters.
- Latin-script text with suspiciously low vowel frequency.
- Extensive corruption across multiple text lines.

The detector considers the visible page text rather than relying exclusively on a confidence score from one cell.

### 4.2 How repair operates

When enabled:

1. Docling evaluates the page's native visible text layer during preprocessing.
2. Pages identified as having a broken text layer are marked for replacement.
3. The OCR stage performs full-page recognition for those pages, even if the configured mode normally selects only limited regions.
4. The resulting OCR text replaces the page's visible native text cells, with invisible PDF cells handled separately.
5. Other pages follow the usual configured OCR policy.

A useful property is that `replace_broken_text_layer` is available across Docling's OCR engines, not tied to RapidOCR or Tesseract.

The associated `parse_score` remains low (zero on a page flagged as broken), because it measures the source PDF text quality, not the correctness of the replacement OCR result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 4.3 What it cannot repair automatically

This is where multiple OCR engines can become valuable.

The detector is not a universal text-correction system. It can miss errors where the extracted characters are individually legitimate but incorrect.

For example:

| Native extraction                                | Visually intended           | Automatic repair likely? |
| ------------------------------------------------ | --------------------------- | ------------------------ |
| Invalid glyph mappings or replacement characters | Ordinary readable text      | Potentially              |
| Severely garbled text across a page              | Correct page text           | Potentially              |
| `O` substituted for `0`                          | `0`                         | Not reliably             |
| `l` substituted for `1`                          | `1`                         | Not reliably             |
| A plausible but incorrect word                   | Another legitimate word     | Not reliably             |
| Misplaced decimal separator                      | Correct numeric value       | Not reliably             |
| One corrupt symbol in otherwise good text        | Correct mathematical symbol | Not necessarily          |

Docling explicitly notes that a single broken cell on an otherwise good page does not ordinarily trigger whole-page replacement.

The appropriate role of automatic repair is recognizing and correcting substantial text-layer corruption—not silently correcting every possible character error.

### 4.4 Baseline repair configuration

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.pipeline_options import (    OcrMode,    PdfPipelineOptions,    RapidOcrOptions,)from docling.document_converter import DocumentConverter, PdfFormatOptionoptions = PdfPipelineOptions(    do_ocr=True,    ocr_options=RapidOcrOptions(        backend="onnxruntime",        lang=["iso:en"],        mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS,        replace_broken_text_layer=True,    ),)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(pipeline_options=options)    })result = converter.convert("report.pdf")document_json = result.document.export_to_dict()
```

This preserves native text precedence in ordinary regions, performs OCR where the page contains otherwise inaccessible visual text, and replaces the visible native text on pages with detectably broken encodings.

It is a good reference configuration for understanding how these features compose, although the best engine and language selection depend on the documents being processed.

Source:

[https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

## 5. Shared OCR options and defaults

All built-in OCR engines inherit the base `OcrOptions` configuration. These settings are generally more consequential for structured-PDF fidelity than changing OCR engines alone.

| Option                                 | Default            | Effect                                                  | Guidance for born-digital PDFs                                             |
| -------------------------------------- | ------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| `PdfPipelineOptions.do_ocr`            | `True`             | Enables OCR stage                                       | Keep enabled for selective recovery, even with native text                 |
| `PdfPipelineOptions.ocr_options`       | `OcrAutoOptions()` | Chooses the OCR engine and its configuration            | Select explicitly when reproducibility matters                             |
| `OcrOptions.mode`                      | `DEFAULT`          | Selects regions and text merge behavior                 | Prefer PDF-aware selection                                                 |
| `OcrOptions.lang`                      | Engine-specific    | Selects recognition language or model                   | Specify expected languages instead of relying on unrelated engine defaults |
| `OcrOptions.scale`                     | `3.0`              | OCR rasterization at 72 × scale DPI, normally 216 DPI   | Tune for small labels and recognition cost                                 |
| `OcrOptions.replace_broken_text_layer` | `False`            | Repairs detectably broken native PDF text, page by page | Valuable for unreliable PDF encodings                                      |
| `force_full_page_ocr`                  | Deprecated         | Compatibility control for full-page mode                | Use `mode=OcrMode.FULL_PAGE`                                               |

`scale` controls OCR input resolution and is separate from `PdfPipelineOptions.images_scale`, which concerns retained document images. Likewise, `generate_page_images=True` is useful for preserving visual evidence in JSON, but is not required merely to execute OCR.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.1 The importance of explicit languages

Docling accepts either an engine-native language code or a BCP-47 language tag prefixed with `iso:`.

Examples:

| Language input                                      | Meaning                                                                    |
| --------------------------------------------------- | -------------------------------------------------------------------------- |
| `RapidOcrOptions(lang=["iso:en"])`                  | Select RapidOCR's model for English                                        |
| `TesseractCliOcrOptions(lang=["eng"])`              | Use Tesseract's English trained data                                       |
| `TesseractCliOcrOptions(lang=["iso:de", "iso:en"])` | German and English, mapped to installed trained data                       |
| `EasyOcrOptions(lang=["en", "fr"])`                 | Recognize both languages when a compatible recognition model supports them |
| `NemotronOcrOptions(lang=["english"])`              | Select Nemotron's English recognizer                                       |

A subtle but important limitation is that a list of languages does not mean the same thing for every engine.

Tesseract can use several language models in one invocation. EasyOCR supports multiple compatible languages. RapidOCR and Nemotron-OCR select only the first specified language or recognition model and warn about additional entries.

For remotely hosted KServe OCR, Docling forwards the first language string verbatim; it does not apply the normal language-code translation.

The engine also matters when `lang=[]`: RapidOCR defaults to Simplified Chinese, while Nemotron-OCR and EasyOCR default to English. Tesseract uses orientation/script detection and requires appropriate `osd` data. Consequently, leaving the language list empty is not a reliable universal strategy for English-language PDFs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Source: [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

## 6. All built-in OCR engines

The current release exposes seven built-in choices, counting Tesseract's two interfaces separately, plus automatic engine selection and third-party plugins.

| Engine / option class    | Main characteristics                                                             | Potential role for structured PDFs                               |
| ------------------------ | -------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `OcrAutoOptions`         | Selects one available engine based on platform, hardware and language support    | Convenient defaults, but results can vary by environment         |
| `RapidOcrOptions`        | PaddleOCR-family models with ONNX Runtime, OpenVINO, Paddle or PyTorch execution | Strong configurable baseline and secondary recognizer            |
| `NemotronOcrOptions`     | NVIDIA model with word/sentence/paragraph granularity                            | Alternative recognition on supported CUDA systems                |
| `EasyOcrOptions`         | Neural OCR with multilingual support and configurable confidence threshold       | Independent recognition and multilingual content                 |
| `TesseractOcrOptions`    | Tesseract through Python's `tesserocr` bindings                                  | Independent engine, extensive language-trained-data options      |
| `TesseractCliOcrOptions` | Tesseract through an external executable                                         | Similar recognition family with different deployment boundary    |
| `OcrMacOptions`          | Apple Vision OCR                                                                 | macOS-native alternative                                         |
| `KserveV2OcrOptions`     | Remote KServe v2-compatible inference service                                    | Externally hosted OCR models and shared inference infrastructure |

### 6.1 Automatic engine selection: `OcrAutoOptions`

Docling's automatic selection order in 2.145.0 is:

1. OcrMac on macOS.
2. Nemotron-OCR on Linux with CUDA, where its dependencies are available.
3. RapidOCR with ONNX Runtime.
4. EasyOCR.
5. RapidOCR with PyTorch.

Unavailable or language-incompatible engines are skipped. Tesseract is never automatically selected.

This has an important consequence: an unchanged Docling configuration can select a different OCR model on different machines.

For exploratory use, `auto` is convenient. For stable JSON extraction where differences must be attributable to configuration and document content, explicitly selecting an engine is preferable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 6.2 RapidOCR

`RapidOcrOptions` provides the most extensive set of controls for local OCR in Docling.

| Option               | Default       | Meaning                                                       |
| -------------------- | ------------- | ------------------------------------------------------------- |
| `backend`            | `onnxruntime` | `onnxruntime`, `openvino`, `paddle`, or `torch`               |
| `lang`               | `["ch"]`      | One PP-OCR language/model per run                             |
| `model_size`         | `small`       | `tiny`, `small`, or `medium` for PP-OCRv6-supported languages |
| `text_score`         | `0.5`         | Minimum confidence threshold for retained text                |
| `use_det`            | `None`        | Use or bypass text detection; `None` inherits engine defaults |
| `use_cls`            | `None`        | Enable text-line direction classification                     |
| `use_rec`            | `None`        | Enable text recognition                                       |
| `detect_orientation` | `False`       | Retry uncertain OCR regions at alternative rotations          |
| `det_model_path`     | `None`        | Custom text detector checkpoint                               |
| `cls_model_path`     | `None`        | Custom orientation classifier checkpoint                      |
| `rec_model_path`     | `None`        | Custom recognition checkpoint                                 |
| `rec_keys_path`      | `None`        | Custom character vocabulary                                   |
| `rapidocr_params`    | `{}`          | Additional RapidOCR engine parameters                         |
| `print_verbose`      | `False`       | Diagnostic output                                             |
| `font_path`          | `None`        | Font used for rendering/visualization                         |
| `rec_font_path`      | `None`        | Deprecated alternative to `font_path`                         |

Model selection is more subtle than model size. The language may route to PP-OCRv6 or to older script-specific PP-OCRv5/v4 models. In the latter case, changing `model_size` does not necessarily change the recognition model. Unsupported combinations produce errors rather than silent substitutions.

The main fidelity controls are `lang`, the detector/recognizer checkpoints, `text_score`, orientation handling and the common `scale` and `mode` settings. Changing `backend` primarily affects the inference implementation and available model combinations; it should not be treated as automatically introducing a substantially different independent OCR recognizer.

For precision-sensitive comparison, running the same model weights on ONNX Runtime and PyTorch provides less model diversity than comparing different OCR model families.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Rotation handling: `use_cls` can correct the direction of individual text lines, principally through 180-degree flips. `detect_orientation=True` can retry regions at quarter-turn rotations when initial recognition is insufficiently confident. This is useful for rotated annotations and labels in otherwise normally oriented PDF pages, although it increases processing on affected regions.

RapidOCR documentation: [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

Upstream engine: [https://github.com/RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR?utm_source=chatgpt.com)

### 6.3 Nemotron-OCR

`NemotronOcrOptions` provides a separate recognition family with relatively few but important configuration parameters.

| Option        | Default       | Effect                                                 |
| ------------- | ------------- | ------------------------------------------------------ |
| `lang`        | `["english"]` | English or multilingual model selection                |
| `merge_level` | `sentence`    | Output granularity: `word`, `sentence`, or `paragraph` |
| `batch_size`  | `8`           | Number of OCR regions processed together within a page |

The documented Nemotron-OCR v2 model selection distinguishes an English recognizer from a multilingual recognizer covering Chinese, Japanese, Korean and Russian.

Other Latin-script languages may be routed to the English model on a best-effort basis, but this does not imply validated accuracy for those languages.

`merge_level` is especially relevant to multi-OCR reconciliation: word-level output provides smaller comparison units, whereas sentence- or paragraph-level output may make detection/recognition more efficient but can complicate alignment against native PDF text cells.

Nemotron's installation requirements are substantially narrower than RapidOCR's: the documented extra targets Linux x86-64, Python 3.12 and CUDA 13.x. Its CUDA availability does not mean it runs on arbitrary Python/CUDA combinations.

A different model family makes Nemotron potentially useful as an independent recognizer, but the sources do not establish that it systematically outperforms RapidOCR or Tesseract on all born-digital PDF regions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 6.4 EasyOCR

`EasyOcrOptions` exposes:

| Option                    | Default                    | Effect                                                 |
| ------------------------- | -------------------------- | ------------------------------------------------------ |
| `lang`                    | `["en", "es", "fr", "de"]` | Language set, subject to compatible recognition models |
| `use_gpu`                 | `None`                     | Automatic GPU selection, or explicit CPU/GPU choice    |
| `confidence_threshold`    | `0.5`                      | Filter low-confidence recognized text                  |
| `recog_network`           | `standard`                 | Recognition model selection                            |
| `model_storage_directory` | `None`                     | Checkpoint storage                                     |
| `download_enabled`        | `True`                     | Permit checkpoint downloads                            |
| `suppress_mps_warnings`   | `True`                     | macOS MPS diagnostic behavior                          |

EasyOCR provides a genuinely different recognition implementation from Tesseract and RapidOCR, making it a reasonable candidate for independent validation.

The language set must remain compatible with its available recognition models. Specifying several languages is not equivalent to enabling an unrestricted universal multilingual recognizer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Documentation discrepancy: Docling's `recog_network` description mentions `craft` as a recognition option, but upstream EasyOCR treats CRAFT as a text detector, while `recog_network` controls recognition. This appears inconsistent. I would retain `recog_network="standard"` unless a different recognition network is confirmed against the installed EasyOCR version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Upstream EasyOCR: [https://github.com/JaidedAI/EasyOCR](https://github.com/JaidedAI/EasyOCR?utm_source=chatgpt.com)

### 6.5 Tesseract: Python bindings and CLI

Docling exposes the same Tesseract OCR family through two interfaces:

- `TesseractOcrOptions` uses the `tesserocr` Python bindings.
- `TesseractCliOcrOptions` invokes the external Tesseract executable.

Both expose `lang`, `path` (trained-data directory), and `psm` (page-segmentation mode). The CLI variant additionally exposes `tesseract_cmd` for selecting the executable.

The default language set is `["eng", "spa", "fra", "deu"]`; the corresponding trained data must be available.

Tesseract offers particularly useful recognition controls through its language models and page segmentation modes. Examples include:

| `psm` | Tesseract interpretation    | Potential use                      |
| ----- | --------------------------- | ---------------------------------- |
| `3`   | Automatic page segmentation | General document crops             |
| `6`   | Assume a uniform text block | A bounded paragraph or text region |
| `7`   | Assume a single text line   | Line-level verification            |
| `8`   | Assume a single word        | An isolated label or value         |
| `11`  | Sparse text                 | Diagram labels or dispersed text   |

These are Tesseract engine behaviors. Docling supplies regions to Tesseract according to its own OCR mode; the Tesseract segmentation setting then governs recognition within the supplied images.

For multi-engine verification, the Tesseract CLI and `tesserocr` bindings should not be counted as two fully independent recognizers when they use the same Tesseract models and similar settings. Their primary differences concern process integration and deployment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Tesseract: [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract?utm_source=chatgpt.com)

`tesserocr`: [https://github.com/sirfz/tesserocr](https://github.com/sirfz/tesserocr?utm_source=chatgpt.com)

### 6.6 Apple Vision: `OcrMacOptions`

OcrMac uses Apple's Vision framework and exposes `recognition="accurate"` or `"fast"`, `lang`, and `framework="vision"`.

It can recognize multiple supported languages, and `lang=[]` delegates language choice to Vision.

For macOS applications, it is a useful native alternative. It does not apply to Linux-based execution, and the precise languages supported depend on the running macOS version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 6.7 Remote OCR: `KserveV2OcrOptions`

The KServe v2 integration sends OCR inputs to a compatible remote inference service, such as a Triton-based deployment.

Its distinguishing options include `model_name`, `lang`, `scale`, and connection settings inherited from `KserveV2OptionsMixin`, covering the server address, transport, authentication-related metadata, timeouts and model-version selection.

Its OCR scale defaults to `2.0` rather than the usual `3.0`.

The remotely deployed model determines recognition capabilities. Docling does not validate its supported languages; it sends the first language string unchanged.

Remote inference requires explicitly permitting remote services in the PDF pipeline configuration. This changes the data-handling boundary because document-derived images are transmitted to the inference server.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



For structured PDFs, remote OCR is best understood as a deployment option, not a separate accuracy guarantee.

## 7. External OCR engines, custom models and plugins

Docling's built-in OCR choices are not the complete universe of recognizers it can use.

Its plugin architecture uses `pluggy` and the `docling` package entry-point group. External OCR implementations register an `ocr_engines()` factory and implement `BaseOcrModel`, with configuration derived from `OcrOptions`.

External model loading must be explicitly enabled using `PdfPipelineOptions.allow_external_plugins=True`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.1 SuryaOCR

The official Docling example uses the separate `docling-surya` integration, with `SuryaOcrOptions` imported from `docling_surya`.

Surya is an additional OCR implementation, not one of the built-in OCR option classes in Docling 2.145.0.

This can be useful as a third independent recognition family. However, the integration adds model dependencies and separate versioning, and the official example identifies GPL-related licensing considerations.

Source: [https://docling-project.github.io/docling/\_generated/examples/suryaocr_with_custom_models/](https://docling-project.github.io/docling/_generated/examples/suryaocr_with_custom_models/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.2 OnnxTR

The installation documentation identifies `docling-ocr-onnxtr`, which exposes `OnnxtrOcrOptions` through the plugin system.

It adds another neural OCR implementation and its own detector/recognizer configuration choices. As with Surya, the package's actual compatibility and model requirements are separate from the built-in Docling OCR engines.

Source: [https://docling-project.github.io/docling/getting_started/installation/](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.3 Custom RapidOCR checkpoints

An additional OCR engine is not always necessary to obtain a second recognition model.

RapidOCR allows substituting its detector, recognizer, classifier, and recognition vocabulary through model paths. Docling provides an official example showing this arrangement with externally downloaded ONNX checkpoints.

This creates two kinds of comparison:

| Comparison                                       | What changes                                | Independence            |
| ------------------------------------------------ | ------------------------------------------- | ----------------------- |
| Same RapidOCR model, different inference backend | Runtime implementation                      | Low model diversity     |
| RapidOCR with different recognition checkpoints  | Recognition weights / possibly architecture | Potentially meaningful  |
| RapidOCR versus Tesseract                        | Recognition model family                    | Substantially different |
| RapidOCR versus Nemotron-OCR or SuryaOCR         | Recognition model family                    | Substantially different |

The general objective should be complementary error behavior, not simply a larger number of invocations. Two systems that make the same mistakes add limited independent evidence.

Custom-model example: [https://docling-project.github.io/docling/\_generated/examples/rapidocr_with_custom_models/](https://docling-project.github.io/docling/_generated/examples/rapidocr_with_custom_models/?utm_source=chatgpt.com)

## 8. Using multiple OCR engines on structured PDFs

This is the area where I would distinguish Docling's native capabilities from additional architecture.

### 8.1 Three different multi-OCR strategies

| Strategy                      | What it does                                                                                   | How well Docling directly supports it                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Recovery cascade              | Use native text, then OCR missing regions, then retry failures with another recognizer         | Initial selective recovery is native; additional retries need orchestration |
| Parallel verification         | Independently OCR text that already exists in the PDF and compare readings                     | Requires an alternative pass and custom comparison                          |
| Evidence-based reconciliation | Select or flag competing text candidates using geometry, engine confidence and source evidence | Requires custom reconciliation logic                                        |

The recovery cascade minimizes unnecessary work. Parallel verification maximizes independent evidence. Reconciliation is the crucial step that determines whether having multiple OCR results actually improves the final JSON.

Simply enabling `do_ocr=True` does not perform all three.

### 8.2 A useful multi-pass architecture

Primary extraction with independent verification

Architectural option, not a built-in Docling ensemble. Reconciliation and retained comparison evidence require additional logic.

The critical principle is that an independent OCR pass should initially act as a source of evidence, not as an automatic replacement for the primary extraction.

This matters especially for technical PDFs, where one wrong digit or symbol can be more consequential than several ordinary word-recognition errors.

### 8.3 How to align competing OCR outputs

Text arrays from different conversions should not be compared by positional index. Changing OCR mode can alter text segmentation, table reconstruction and reading order.

A more robust comparison uses the available structural information:

| Matching level | Alignment evidence                         | Typical comparison                             |
| -------------- | ------------------------------------------ | ---------------------------------------------- |
| Page           | `page_no`                                  | Restrict candidates to the same page           |
| Region         | Bounding-box overlap and proximity         | Match corresponding text regions               |
| Semantic item  | Heading, paragraph, table or picture label | Avoid comparing unrelated structures           |
| Table cell     | Table region plus row/column position      | Compare individual numeric/text cells          |
| Text span      | Normalized string and geometric sequence   | Detect substitutions, omissions and insertions |

There are several limitations.

OCR engines may return word boxes, line boxes or paragraph boxes, so the candidate boundaries can differ. Text normalization is useful for matching but must not erase meaningful distinctions such as decimal separators, minus signs, superscripts, or units.

It is also unsafe to assume that two overlapping boxes identify the same semantic element. A superscript, table border label, or footnote marker can overlap neighboring elements without being equivalent to them.

Therefore, a practical reconciliation system benefits from preserving both the original and alternative recognition strings, together with their source locations and the comparison decision.

### 8.4 How agreement should be interpreted

| Native PDF     | OCR A      | OCR B      | Reasonable interpretation                                       |
| -------------- | ---------- | ---------- | --------------------------------------------------------------- |
| `0.05`         | `0.05`     | `0.05`     | Strong corroboration, though not absolute proof                 |
| `O.05`         | `0.05`     | `0.05`     | Native text is suspicious; visual correction candidate          |
| `0.05`         | `O.05`     | `0.05`     | Native and one recognizer agree; OCR A may be mistaken          |
| `0.05`         | `0.5`      | `0.05`     | High-value numerical disagreement; examine rendering            |
| `α`            | `a`        | `α`        | Preserve the native symbol unless other evidence contradicts it |
| No native text | `P = 12.4` | `P = 12.4` | Likely successful recovery of missing visual text               |
| `1.25`         | `1.25`     | `1.28`     | Unresolved; do not silently select by majority                  |

The final two rows illustrate a key distinction: OCR agreement can be useful when recovering otherwise absent content, but disagreements involving existing exact digital text should be interpreted more conservatively.

Also, two OCR models trained on overlapping data or using similar preprocessing can make correlated errors. A 2-to-1 majority is not inherently a calibrated confidence measure.

### 8.5 Multi-OCR can improve coverage and confidence, but not every kind of semantic richness

Ordinary OCR primarily recovers recognized character sequences and their locations. It does not automatically recover all the information represented by the document.

For example, two OCR engines reading a scientific plot may both transcribe its axis labels correctly while providing no information about the plotted series.

Likewise, correctly recognizing the text inside a table does not establish correct row/column membership, merged headers or cross-page continuity.

For those tasks, Docling's layout, table recognition, chart extraction and formula enrichment capabilities remain separate and complementary to OCR.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



## 9. How to leverage OCR for different structured-PDF content

| Source condition                            | Appropriate Docling mechanism                     | Role of a second OCR                                                              |
| ------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| Correct embedded body text                  | Native text with PDF-aware selective OCR          | Usually unnecessary unless independent verification matters                       |
| Embedded text with invalid Unicode mappings | `replace_broken_text_layer=True`                  | Useful for validating the replacement                                             |
| Plausible but incorrect native characters   | Alternative `LAYOUT_REGIONS` OCR pass             | Important for detecting silent differences                                        |
| Rasterized text inside figures              | PDF-aware selective OCR                           | Useful if the first recognizer misses labels                                      |
| Vector-outlined lettering                   | PDF-aware shape-aware OCR                         | Useful for uncertain labels or mixed graphical text                               |
| Rotated annotations                         | RapidOCR `detect_orientation=True`                | Alternative recognizer for difficult rotations                                    |
| Multilingual material                       | Appropriate engine/language models                | Useful where one recognizer cannot cover all scripts                              |
| Mathematical formulas                       | `do_formula_enrichment=True`                      | General OCR can act as a check, but is not a substitute for formula recognition   |
| Code blocks                                 | `do_code_enrichment=True`                         | May help identify symbol and indentation errors                                   |
| Financial or scientific tables              | TableFormer and cell matching, plus OCR as needed | Compare cell values independently of table structure                              |
| Graphs and plots                            | Chart extraction and picture understanding        | OCR adds label transcription, not the complete data series                        |
| Native interactive PDF forms                | `extract_form_fields=True`                        | OCR only complements visible labels; it cannot reconstruct native widget metadata |

### 9.1 Mathematical and scientific notation

General OCR can recover conventional text but is less suitable as the sole interpreter of dense mathematical notation.

Examples include Greek symbols, subscripts, superscripts, multi-line equations, matrices, integral bounds, and distinctions such as `−` versus `-`.

Docling offers `do_formula_enrichment=True`, using a specialized formula model to produce a mathematical representation. The documented model exposes configurable formula cropping and repetition controls through `code_formula_options`.

The resulting `FormulaItem` is part of the structured document, rather than an independent plain-text OCR transcript.

The useful composition is native text for ordinary content, specialized formula recognition for detected formulas, and optional OCR agreement checks for uncertain symbols.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 9.2 Tables and exact numeric values

For born-digital tables, a particularly valuable strategy is separating table structure from cell transcription.

TableFormer determines the table grid, spans and inferred header associations. Native PDF text cells supply content where available. OCR can recover missing visual values or provide an independent reading of a cell.

Running another OCR engine does not automatically improve the grid. An incorrect row boundary can remain incorrect even if every cell's characters are recognized perfectly.

For precision-sensitive data, a second recognizer can be applied to selected table-cell bounding boxes and compared against the existing `TableData.table_cells` values.

This region-level approach is an architectural possibility; Docling does not provide a built-in automatic cell-by-cell voting facility.

### 9.3 Figures and embedded graphics

OCR is valuable for figure labels, legends, map annotations and text appearing inside screenshots.

But the result needs semantic association. Recognizing `Pressure`, `150`, and `kPa` somewhere inside a diagram does not establish whether they belong to the same measurement, a nearby chart axis, or different graphic objects.

Picture classification, description, and chart extraction can add information beyond the character sequence. These enrichments also use different models and have different reliability characteristics.

Sources:

[https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 10. Quality measurement and the structured JSON boundary

### 10.1 Docling's confidence scores are not an ensemble verdict

Docling's `ConversionResult.confidence` includes `ocr_score`, `parse_score`, `layout_score`, and an as-yet-unimplemented `table_score`.

`parse_score` reflects the quality of the programmatic PDF text layer, with the documented measure emphasizing the lower-quality text cells through a 10th-percentile statistic.

`ocr_score` summarizes OCR recognition quality. In the standard OCR implementation it is derived from OCR cells that survive selection and merging.

Neither is a calibrated probability that a particular JSON string is correct.

An important subtlety: if OCR is skipped because the PDF text layer is present, the lack of OCR disagreement is not positive verification of that text.

The documentation emphasizes quality grades rather than treating raw scores as stable thresholds or guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Source: [https://docling-project.github.io/docling/concepts/confidence_scores/](https://docling-project.github.io/docling/concepts/confidence_scores/?utm_source=chatgpt.com)

### 10.2 OCR evidence is not automatically retained in document JSON

A standard `DoclingDocument` stores the selected semantic content and its provenance. It does not automatically retain a full audit trail containing every native cell, every rejected OCR cell, each engine's candidate strings, and its individual confidence values.

Those details belong to intermediate representations or to a separately constructed evidence model.

`generate_parsed_pages=True` can preserve some intermediate PDF page data in the `ConversionResult`, but saving `result.document` does not serialize all that intermediate state.

For a JSON-only system that uses several OCR passes, there are therefore two distinct representations:

Canonical document JSON — the normalized `DoclingDocument`, containing the final document's typed semantic structure.

Recognition evidence JSON — an additional record of engine configurations, candidate strings, locations, disagreements, and resolution decisions.

If both must be in one JSON artifact, a containing application can define a wrapper with the canonical Docling JSON and its evidence records. That wrapper should not be mistaken for the native `DoclingDocument` schema.

### 10.3 Quality controls worth distinguishing

| Quality signal                 | What it can establish                                     | What it cannot establish                                  |
| ------------------------------ | --------------------------------------------------------- | --------------------------------------------------------- |
| PDF text parse score           | Detect some native-text degradation                       | Every character is correct                                |
| OCR model confidence           | Recognition model's own confidence                        | Cross-engine calibrated correctness                       |
| OCR engine agreement           | Corroboration between recognizers                         | Independence or factual correctness                       |
| Bounding-box agreement         | Candidate text refers to a similar location               | Exact semantic equivalence                                |
| Structured document validation | JSON model and reference consistency                      | Faithful extraction from the PDF                          |
| Table-cell consistency rules   | Values satisfy declared structural constraints            | The source document actually contained those values       |
| Visual verification            | Whether the selected text matches visible source evidence | Whether a figure's higher-level interpretation is correct |

The optimal validation policy depends on the consequences of error. Numerical and symbolic fields may justify more independent checks than ordinary prose.

## 11. Example: two independent Docling OCR passes

This illustrates a baseline conversion that preserves native text and a separate verification conversion that deliberately OCRs text-bearing layout regions.

The example assumes the relevant RapidOCR dependencies and a system Tesseract installation with English trained data are available. It is illustrative and has not been executed.

```
from docling.datamodel.base_models import InputFormat, ConversionStatusfrom docling.datamodel.pipeline_options import (    OcrMode,    PdfPipelineOptions,    RapidOcrOptions,    TesseractCliOcrOptions,)from docling.document_converter import DocumentConverter, PdfFormatOptiondef convert_pdf(source: str, ocr_options):    pipeline_options = PdfPipelineOptions(        do_ocr=True,        do_table_structure=True,        ocr_options=ocr_options,    )    converter = DocumentConverter(        format_options={            InputFormat.PDF: PdfFormatOption(                pipeline_options=pipeline_options,            ),        },    )    result = converter.convert(source, raises_on_error=False)    if result.status not in {        ConversionStatus.SUCCESS,        ConversionStatus.PARTIAL_SUCCESS,    }:        raise RuntimeError(f"PDF conversion failed: {result.status}")    return resultsource = "report.pdf"
```

Here the second `DoclingDocument` is an alternative interpretation of the PDF, not automatically a set of individual corrections to the first.

`psm=6` asks Tesseract to treat each supplied image as a uniform block. This is a reasonable illustrative configuration for text-region crops but may not suit sparse labels, tables or mixed-format regions; a different segmentation mode can be evaluated for those cases.

The two JSON outputs can be compared using the page, geometry and structure information described earlier. That comparison and any resulting corrections are intentionally not represented as a nonexistent native Docling API.

A separate conversion also entails a second layout, table, and document assembly pass. Where only a small number of suspicious regions need verification, using independently rendered crops with an OCR engine can avoid recomputing the entire semantic document.

## 12. Performance and deployment considerations

For structured PDFs, the main opportunity is to minimize the amount of material requiring visual recognition while retaining sufficient independent evidence.

| Lever                                     | Expected effect                                 | Main tradeoff                                                         |
| ----------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| PDF-aware mode                            | Avoid OCR of clean native text                  | Cannot verify plausible native-text mistakes                          |
| `replace_broken_text_layer`               | Automatically repair certain corrupted pages    | Page-wide replacement may affect otherwise correct text               |
| Larger `scale`                            | More pixels for small characters                | Higher rasterization/inference cost; not always better recognition    |
| RapidOCR `model_size`                     | Adjust supported PP-OCRv6 model capacity        | Larger models require more resources; no universal accuracy guarantee |
| RapidOCR `text_score` / EasyOCR threshold | Control recognition acceptance                  | Higher thresholds risk omitting real faint text                       |
| RapidOCR orientation retries              | Recover rotated content                         | Additional inference on uncertain regions                             |
| OCR-stage batching                        | Improve throughput under suitable loads         | Higher memory pressure                                                |
| Selective secondary OCR                   | Limit independent checking to uncertain regions | Requires a way to identify and align those regions                    |
| Whole-document second pass                | Simple independent comparison                   | Repeats layout, OCR and table processing                              |

Docling's pipeline also exposes `ocr_batch_size` for threaded OCR execution. This is separate from the `NemotronOcrOptions.batch_size` governing that engine's processing of multiple OCR crops within a page.

The performance effects depend on OCR engines, model sizes, page complexity, hardware and the percentage of regions actually sent to OCR. The sources do not establish a universal fastest or most accurate engine for born-digital PDFs.

### Important extraction interactions

Native PDF forms: if interactive AcroForms matter, preserve the native parser pathway and enable `extract_form_fields=True`. Full-page OCR can replace native text but cannot recover the underlying PDF widget objects. Its interaction with form extraction should be assessed separately.

`force_backend_text`: this is a native-text precedence/selection control, not another OCR engine. It should not be used as a substitute for secondary recognition or broken-text repair.

VLM pipelines: Docling's `VlmPipeline` is a distinct document-conversion architecture, not another selectable OCR engine inside the standard OCR stage. Running a VLM alongside a conventional PDF pipeline is another form of independent interpretation, but it has different output and provenance characteristics.

Image retention: preserving page and figure images in the JSON can support later verification, but increases payload size substantially. The images need not be embedded merely because OCR ran during conversion.

Sources:

[https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 13. Recommended OCR leverage for born-digital PDFs

For the stated scope—structured PDFs with existing text, producing structured JSON—I would distinguish three levels of processing rather than assume that more OCR is always better.

| Level                              | Processing policy                                                         | Purpose                                                          |
| ---------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1. Primary extraction              | Native text + `PDF_AWARE_LAYOUT_REGIONS` + broken-layer repair            | Preserve exact PDF text while recovering missing visual content  |
| 2. Independent verification        | Different OCR model on regions with detected or consequential uncertainty | Identify silent substitutions and provide alternative candidates |
| 3. Specialized semantic enrichment | Formula, code, table, figure and chart models                             | Recover structures and meanings that ordinary OCR cannot express |

The second level is the most relevant opportunity beyond Docling's built-in behavior. It is also where custom machinery becomes necessary, because Docling's standard OCR pipeline resolves candidate text geometrically rather than through multi-engine quality arbitration.

For normal prose, native PDF text should usually remain authoritative unless there is evidence of corruption. For critical numerical values, units, formula symbols and table cells, independent OCR can be valuable even when the native text looks valid. For text embedded in images or drawn as vectors, selective OCR is a recovery mechanism rather than merely a quality checker.

The guiding principle is preserve the source's exact programmatic information, use vision to recover what the source representation omits, and retain disagreements as evidence until they can be resolved.

### Most relevant primary references

| Subject                                           | Direct URL                                                                                                                                                                                                              |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OCR engines, language behavior, text-layer repair | [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)                                                                               |
| Full OCR options API                              | [https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)                                                   |
| Version-specific OCR options                      | [https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/pipeline_options.py?utm_source=chatgpt.com) |
| OCR-region selection and text-cell merging        | [https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/models/base_ocr_model.py?utm_source=chatgpt.com)           |
| OCR plugins                                       | [https://docling-project.github.io/docling/concepts/plugins/](https://docling-project.github.io/docling/concepts/plugins/?utm_source=chatgpt.com)                                                                       |
| Engine installation                               | [https://docling-project.github.io/docling/getting_started/installation/](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)                                               |
| Custom RapidOCR checkpoints                       | [https://docling-project.github.io/docling/\_generated/examples/rapidocr_with_custom_models/](https://docling-project.github.io/docling/_generated/examples/rapidocr_with_custom_models/?utm_source=chatgpt.com)        |
| SuryaOCR integration                              | [https://docling-project.github.io/docling/\_generated/examples/suryaocr_with_custom_models/](https://docling-project.github.io/docling/_generated/examples/suryaocr_with_custom_models/?utm_source=chatgpt.com)        |
| Conversion confidence                             | [https://docling-project.github.io/docling/concepts/confidence_scores/](https://docling-project.github.io/docling/concepts/confidence_scores/?utm_source=chatgpt.com)                                                   |
| Specialized enrichment models                     | [https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)                                                                     |

Bottom line: The most useful multi-OCR architecture is not three recognizers competing to rewrite an entire born-digital PDF. It is a primary native-text-preserving conversion, followed by selective, independent recognition where the source is incomplete, suspicious or accuracy-critical, with the resulting evidence and decisions kept traceable in structured JSON.

# Best Docling configuration for complex PDFs with mathematical formulas

For a well-structured, born-digital PDF containing equations, tables, symbols and complex layouts, I would favor Docling's standard PDF pipeline with selective OCR, a strong layout model, and specialized formula enrichment rather than using a more powerful OCR engine indiscriminately.

The key distinction is that ordinary OCR recognizes text; specialized formula models recognize mathematical expressions; layout and table models recover document structure. These are complementary capabilities.

## 1. Recommended model combination

| Processing stage      | Preferred configuration                       | Why                                                                |
| --------------------- | --------------------------------------------- | ------------------------------------------------------------------ |
| Native PDF extraction | `docling-parse` through `StandardPdfPipeline` | Preserves programmatic text and geometry                           |
| OCR engine            | RapidOCR, `onnxruntime`, `small`              | Flexible, efficient baseline for text missing from the PDF layer   |
| OCR selection         | `PDF_AWARE_LAYOUT_REGIONS`                    | Avoids replacing good embedded text                                |
| Text repair           | `replace_broken_text_layer=True`              | Recovers text from PDFs with corrupt Unicode mappings              |
| Layout recognition    | Heron default, or Egret Large for comparison  | Recovers headings, paragraphs, figures, tables and formula regions |
| Formula recognition   | CodeFormulaV2                                 | Converts recognized equations into LaTeX representations           |
| Table structure       | TableFormer `ACCURATE`                        | Reconstructs rows, columns, merged cells and cell contents         |
| Heading hierarchy     | `HeadingHierarchyOptions(enabled=True)`       | Improves the structured document tree                              |
| Execution             | CUDA for supported model stages               | Accelerates model inference where supported                        |

This is a proposed quality-oriented configuration based on the available capabilities, not a measured claim that this exact combination is globally optimal.

The most important additional model is CodeFormulaV2, not a second general-purpose OCR engine. Docling's formula enrichment targets detected formula elements and produces LaTeX; it is disabled by default.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



## 2. Which components actually add information?

| Component                           | Additional information beyond PDF-native text                                                             |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| RapidOCR / Nemotron-OCR / Tesseract | Missing characters or text in raster/vector-drawn regions                                                 |
| CodeFormulaV2                       | Mathematical syntax: fractions, exponents, subscripts, operators, matrices and other expression structure |
| Heron / Egret layout models         | Semantic element types, bounding boxes and reading-order evidence                                         |
| TableFormer                         | Cell boundaries, spanning cells, row/column structure and inferred header relationships                   |
| Heading hierarchy recovery          | Relative section depth within the document                                                                |
| Chart extraction VLM                | Inferred chart type, series, labels and numerical values                                                  |
| Full-page document VLM              | Alternative interpretation of layout, text, equations and complex visual regions                          |

For complex technical PDFs, the combination of layout detection and formula recognition can add much more useful structured information than replacing RapidOCR with a larger general-purpose OCR engine.

The limitation is that formula enrichment operates on elements identified as formulas. It cannot enrich an equation that was never detected or was flattened into ordinary paragraph text. This becomes important for inline equations and formulas inside tables, discussed below.

## 3. Performance and accuracy tradeoffs

The largest performance difference comes from which regions and models are invoked, not simply which OCR engine is chosen.

| Option                               | Relative computational cost                  | Structural contribution                         | Assessment                                                                       |
| ------------------------------------ | -------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------- |
| Native text + selective RapidOCR     | Low OCR overhead when native text is good    | Recovers otherwise missing text                 | Best baseline                                                                    |
| RapidOCR `medium` instead of `small` | Potentially higher                           | None beyond recognition                         | Worth comparing for small or difficult text; no verified universal accuracy gain |
| Nemotron-OCR v2                      | GPU-oriented; runtime dependent              | Text recognition, with configurable granularity | Alternative recognizer, not a formula/structure model                            |
| Egret Large instead of Heron         | Higher model cost                            | Potentially better layout detection             | Particularly worth testing for complex documents                                 |
| CodeFormulaV2                        | Additional inference for detected formulas   | LaTeX mathematical representation               | High-value enrichment                                                            |
| TableFormer `ACCURATE`               | More expensive than `FAST`                   | Better reconstructed table structure            | Prefer for complex tables                                                        |
| Granite-Docling formula enrichment   | Separate VLM model                           | Alternative formula interpretation              | Useful comparative option                                                        |
| Full-page VLM conversion             | Potentially substantial additional inference | End-to-end visual document reconstruction       | Alternative for pages the standard pipeline handles poorly                       |

The official model catalog specifically identifies `layout_egret_large` and `layout_egret_xlarge` as higher-accuracy options for complex documents, but it does not establish that every document benefits from their additional computational cost.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



### The most consequential formula-model options

`CodeFormulaVlmOptions` has several useful controls:

- `scale=2.0` — image resolution multiplier for the formula crop.
- `expansion_factor=0.18` — default crop margin around each equation.
- `stop_on_repetition=True` — protects against repetitive generated output.
- `max_size` — optional maximum image dimension.
- `engine_options` — controls the inference backend.

Docling explicitly documents that a wide formula crop can include a neighboring equation number or text and cause the formula model to generate repeated filler. It demonstrates reducing `expansion_factor` to `0.08` to mitigate this.

This is worth paying attention to on papers with dense, closely spaced equations. However, a crop that is too tight can omit useful parts of a formula.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Source: [https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)

## 4. Recommended Python configuration

This configuration prioritizes the quality of the structured JSON for complex technical PDFs, assuming a compatible CUDA installation.

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.accelerator_options import (    AcceleratorDevice,    AcceleratorOptions,)from docling.datamodel.pipeline_options import (    PdfPipelineOptions,    RapidOcrOptions,    OcrMode,    LayoutObjectDetectionOptions,    TableStructureOptions,    TableFormerMode,    CodeFormulaVlmOptions,    HeadingHierarchyOptions,)from docling.document_converter import DocumentConverter, PdfFormatOptionoptions = PdfPipelineOptions(    # Hardware    accelerator_options=AcceleratorOptions(        device=AcceleratorDevice.CUDA,    ),    # Preserve native PDF text and recover missing regions    do_ocr=True,    ocr_options=RapidOcrOptions(        backend="onnxruntime",        lang=["iso:en"],        model_size="small",        mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS,        replace_broken_text_layer=True,    ),    # Higher-capacity layout recognition    layout_options=LayoutObjectDetectionOptions.from_preset(        "layout_egret_large"
```

The APIs and presets are documented for the targeted release. The exact combined configuration has not been benchmarked here. ONNX Runtime GPU acceleration also requires the CUDA execution provider to be available; merely selecting a CUDA accelerator does not guarantee that RapidOCR itself uses the GPU.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



For faster execution, the first change I would consider is switching Egret Large back to the default Heron layout model. For higher OCR capacity, the first comparison would be RapidOCR `small` against `medium`, rather than immediately replacing all native PDF text with OCR.

## 5. Two important limitations for mathematical PDFs

### 5.1 Formula recognition depends on region detection

CodeFormulaV2 operates on document elements already classified as formulas.

A formula embedded inside an ordinary paragraph may not be identified as a separate formula region. An equation that is never detected as such cannot benefit from the specialized formula stage.

Docling's recognized equations can carry LaTeX text in the structured document. This is valuable, but it is not the same as a validated symbolic mathematical expression tree. Formula recognition can still produce mathematically incorrect LaTeX.

### 5.2 Formulas inside PDF table cells are a known gap

This is especially significant for complex technical documents.

An upstream issue reports that formula enrichment does not traverse ordinary PDF `TableCell` content. Consequently, a table cell containing a complex equation can be reduced to visually ordered text instead of becoming a properly reconstructed LaTeX formula. The issue also discusses cells containing mixtures of prose and several equations.

That issue remained open in the retrieved upstream discussion. The existing rich-cell representation can support more complex content, but the standard PDF enrichment pipeline does not automatically populate it for all such cases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/docling-project/docling/issues/3828](https://github.com/docling-project/docling/issues/3828?utm_source=chatgpt.com)

This is one reason to investigate an alternative full-document VLM pipeline when formulas are especially dense or integrated into tables.

## 6. Which alternative models deserve investigation?

Two additional Docling-supported model families stand out.

MinerU2.5-Pro uses a two-stage architecture: page-level layout detection followed by region-specific recognition, including formulas and OTSL table structures. It is a particularly relevant alternative when the standard pipeline fails to identify or reconstruct mathematical regions.

Nemotron 3.5 Parse supplies another integrated document interpretation path, including native layout information, table representations and chart data. It is distinct from Nemotron-OCR, which serves the narrower text-recognition role.

Both are available through Docling's VLM model catalog. They should be evaluated as alternative document parsers, not as OCR engines swapped into `RapidOcrOptions`. Their ability to produce rich structures does not guarantee better fidelity for every document, and a generative document parser may sacrifice some of the exactness available from the PDF text layer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Source: [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)

## 7. Practical comparison

Default technical-PDF path

Standard pipeline + PDF-aware RapidOCR + Egret/Heron + CodeFormulaV2 + accurate TableFormer.

Primary

Formula-heavy or structurally problematic pages

Compare with `mineru2_pro`, particularly when formulas are inline, embedded in tables, or incorrectly classified.

Alternative

Critical numerical or symbolic transcription

Run an independent OCR or formula recognizer on the uncertain regions and retain disagreements rather than overwriting the native text automatically.

Validation

The single strongest distinction is this: a better OCR engine may recover more characters, but CodeFormulaV2 and a strong layout model can recover fundamentally different information—the structure of the equation and its place in the document.

For the kind of structured PDF described, I would prioritize formula enrichment and layout quality before spending additional inference on multiple general-purpose OCR engines.