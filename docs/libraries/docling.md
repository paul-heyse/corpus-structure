# Docling (Python) — Comprehensive Library Capability Reference

Target: Docling 2.143.1 (stable, released October 27, 2026) | Research date: October 28, 2026

Docling is an open-source, AI-assisted document understanding and conversion framework. It transforms heterogeneous documents into a unified, structured representation that preserves substantially more information than conventional text extraction: document hierarchy, reading order, tables, figures, captions, page geometry, and provenance.

Originally developed at IBM Research and now hosted by the LF AI & Data Foundation, Docling combines conventional file parsers, PDF layout analysis, OCR, table-structure recognition, vision-language models (VLMs), and structured serialization. It provides a Python SDK, command-line tools, and a broader ecosystem for serving, information extraction, and integration with AI applications.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary sources:

- Repository: [https://github.com/docling-project/docling](https://github.com/docling-project/docling?utm_source=chatgpt.com)
- Documentation: [https://docling-project.github.io/docling/](https://docling-project.github.io/docling/?utm_source=chatgpt.com)
- Version 2.143.1: [https://github.com/docling-project/docling/releases/tag/v2.143.1](https://github.com/docling-project/docling/releases/tag/v2.143.1?utm_source=chatgpt.com)
- Technical report: [https://arxiv.org/abs/2408.09869](https://arxiv.org/abs/2408.09869?utm_source=chatgpt.com)

## 1. Architectural orientation

Docling's defining architectural characteristic is its separation of document parsing, semantic understanding, document representation, and downstream transformations.

Its fundamental abstraction is `DoclingDocument`, a typed, structured document model implemented by the companion `docling-core` package. This model acts as a common intermediate representation across diverse source formats and processing methods.

Document inputs

PDF · Office · HTML · XML · Markdown · images · audio · video · specialized formats

Format backends

Decode files and recover native structures

Processing pipelines

OCR · layout · tables · VLM · enrichment

DoclingDocument

Typed content · semantic hierarchy · reading order · spatial provenance · annotations

Export

JSON · Markdown · HTML · DocTags

Transform

Serialization · chunking · extraction

Integrate

RAG · agents · search · services

Conceptual architecture: backends and pipelines are selected by input format; their results are normalized into a common document model. Different pipelines are alternatives rather than mandatory sequential stages.

The main distinction is between:

- Backends: Format-specific readers that recover source structure and content.
- Pipelines: Configurable processing strategies that orchestrate parsing, recognition, and enrichment.
- Document model: A persistent typed representation that separates content semantics from the original format.
- Transformations: Exporters, serializers, chunkers, and downstream extractors that operate on the resulting document.

This enables a single downstream processing system to consume documents from multiple file formats without implementing a separate semantic data model for each format. It also allows model selection, export behavior, and chunking strategies to evolve independently.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+3



Architecture documentation: [https://docling-project.github.io/docling/concepts/architecture/](https://docling-project.github.io/docling/concepts/architecture/?utm_source=chatgpt.com)

## 2. Capability map

| Capability family          | Important mechanisms                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| Document conversion        | `DocumentConverter`, format-specific backends, pipeline selection, batch conversion         |
| PDF understanding          | Layout analysis, reading-order reconstruction, table recognition, text and image extraction |
| OCR                        | Multiple local OCR engines, multilingual recognition, selective versus full-page OCR        |
| Vision-language processing | Local and remote VLM inference, page-image interpretation, model-specific pipelines         |
| Structural representation  | `DoclingDocument`, hierarchy, typed elements, provenance, spatial coordinates               |
| Enrichment                 | Code, mathematical formulas, picture descriptions, chart interpretation, custom models      |
| Serialization              | Markdown, HTML, JSON, DocTags, DocLang, text, custom serializers                            |
| Semantic chunking          | `HierarchicalChunker`, `HybridChunker`, `LineBasedTokenChunker`, contextual metadata        |
| Information extraction     | Schema-oriented extraction from converted documents                                         |
| Extensibility              | Plugin factories, configurable backends, custom pipelines, processing models                |
| Execution optimization     | Device selection, CPU/GPU inference, batching, concurrency, model caching                   |
| Deployment and integration | Python SDK, CLI, API service, MCP, AI-framework integrations                                |

A consequential distinction throughout this reference is that native extraction, AI-inferred document understanding, and structural serialization provide different guarantees. Docling unifies their outputs, but the resulting document cannot be assumed to preserve every source detail or to contain only deterministic, lossless extraction results.

## 3. Input formats and native structural recovery

Docling supports substantially more than PDF-to-Markdown conversion. Its backends normalize documents with very different internal representations into the same output model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



| Source family                       | Supported formats and consequential characteristics                                                      |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------- |
| PDF and images                      | PDF; PNG, JPEG, TIFF, BMP, WebP. OCR and layout understanding can recover content from raster documents. |
| Microsoft Office                    | DOCX, XLSX, PPTX; legacy DOC, XLS, PPT and RTF through LibreOffice.                                      |
| OpenDocument and Apple iWork        | ODT, ODS, ODP; Pages, Numbers, Keynote. iWork needs the `format-iwork` extra.                            |
| Web and textual markup              | HTML, XHTML, MHTML, Markdown, AsciiDoc, LaTeX, plain text, CSV.                                          |
| Publishing and scientific documents | EPUB, JATS XML, USPTO patent XML, DocLang XML and bundled DocLang archives.                              |
| Enterprise and specialized content  | IBM AFP, EBCDIC/COBOL-formatted content, Box Notes, email, XBRL and other specialized backends.          |
| Audio and video                     | Common audio/video formats using speech-recognition and media pipelines.                                 |
| Native structured interchange       | Docling JSON and other Docling-compatible structured formats for re-import or downstream processing.     |

The significant architectural distinction is native structure versus inferred structure.

A DOCX file may already expose paragraphs, lists, heading styles and table boundaries. A PDF typically supplies geometric drawing operations and text spans but not a dependable semantic document tree. An image may provide only pixels. Docling uses different extraction strategies in each case, so the final `DoclingDocument` has a common schema but not necessarily equivalent information quality.

Several native-format features deserve attention:

- Office equations: PowerPoint equations represented using Office Math (OMML) can become LaTeX formula items while retaining their position among text elements.
- Chart datasets: PowerPoint and Excel charts can preserve their underlying category/series data in `PictureItem.meta.tabular_chart`, rather than only their rendered appearance.
- Document annotations: Some backends preserve comments, presenter notes, footnotes and related content in separate document layers, preventing these from being silently mixed with the main reading order.
- Scientific and business XML: Schema-aware processing can retain more semantic context than treating XML as arbitrary text.

These features are backend-dependent. They are not universal guarantees across every input type.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Documentation: [https://docling-project.github.io/docling/usage/supported_formats/](https://docling-project.github.io/docling/usage/supported_formats/?utm_source=chatgpt.com)

## 4. Document conversion and pipeline selection

### 4.1 `DocumentConverter` is the primary orchestration API

`DocumentConverter` resolves source formats, selects a compatible backend and pipeline, applies format-specific options, and returns a `ConversionResult`.

Its inputs include local paths, HTTP sources and in-memory streams. It supports conversion of multiple documents through `convert_all()`, bounded file sizes and page counts, page-range selection, progress reporting, and structured handling of failed conversions.

The result is more than an exported string: it contains the parsed document, conversion status, error information and available diagnostic information.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



A representative SDK configuration:

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.pipeline_options import PdfPipelineOptionsfrom docling.document_converter import (    DocumentConverter,    PdfFormatOption,)pdf_options = PdfPipelineOptions(    do_ocr=True,    do_table_structure=True,)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(            pipeline_options=pdf_options,        )    })result = converter.convert("document.pdf")document = result.documentmarkdown = document.export_to_markdown()structured = document.export_to_dict()
```

Illustrative SDK example, based on the documented API; not executed in this review.

The format mapping is configurable. Different document families can use different backends and processing policies under one converter, avoiding the need for a separate application-level conversion interface for each format.

API reference: [https://docling-project.github.io/docling/reference/document_converter/](https://docling-project.github.io/docling/reference/document_converter/?utm_source=chatgpt.com)

### 4.2 Three distinct PDF-processing strategies

These alternatives serve materially different purposes.

| Pipeline              | Mechanism                                                                                                                      | Important tradeoff                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `NativePdfPipeline`   | Uses `docling-parse` to recover native PDF text cells and embedded bitmap objects, without OCR, layout models or table models. | Avoids model inference but does not reconstruct a fully semantic reading order, heading hierarchy or table structure.                  |
| `StandardPdfPipeline` | Combines native parsing with optional OCR, learned layout detection, table-structure recognition and enrichments.              | Richer structural recovery, with additional model cost and inference error modes.                                                      |
| `VlmPipeline`         | Uses a vision-language model to interpret page imagery and generate a document representation.                                 | Can understand visually complex pages but introduces model-generation behavior, compatibility differences and potential hallucination. |

`NativePdfPipeline` is particularly noteworthy: it allows the same Docling document interface to be used as a lightweight native PDF content-extraction layer, without requiring an AI model for that operation. Conversely, the standard pipeline enables progressively richer semantic processing using independent components.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



These approaches are not strictly ordered by quality. For digitally authored files with reliable text layers, native extraction can preserve text without recognition errors. For scans, OCR or VLM interpretation may be indispensable. For visually complex scientific publications, layout and table recognition often matter more than plain text extraction.

Pipeline details: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 5. PDF understanding: layout, reading order, tables and provenance

### 5.1 Layout detection and reading-order reconstruction

The standard PDF pipeline uses a document layout model to detect semantic regions such as paragraphs, section headings, tables, pictures and other page elements.

This enables downstream consumers to distinguish what a region represents, rather than merely where text appears on the page.

Reading-order recovery is a separate problem. Multi-column documents, marginal annotations, headers, footers, captions and floating figures can all disrupt naïve position-based text traversal.

Docling combines structural and geometric information to reconstruct an ordered document. It can also use visible PDF rules as reading-order separators, with `use_reading_order_separators=False` available when those rules cause unwanted segmentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



One easily overlooked limitation concerns heading depth: standard layout detection can identify a section heading without reliably assigning its level. The conventional PDF result therefore places headings at level 1 unless hierarchy inference is enabled.

`HeadingHierarchyOptions(enabled=True)` can infer depth from bookmarks, outline numbering and font styling. The font-based signal additionally requires `generate_parsed_pages=True`. This is an inference over available document evidence, not guaranteed reconstruction of the author's original outline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Heading hierarchy documentation: [https://docling-project.github.io/docling/usage/pdf_heading_levels/](https://docling-project.github.io/docling/usage/pdf_heading_levels/?utm_source=chatgpt.com)

### 5.2 Table-structure recognition

PDF tables require two separate recoveries: recognizing the logical cell grid and associating text with those cells.

Docling's TableFormer-based recognition provides both faster and more accurate operating modes:

- `TableFormerMode.FAST`: lower-cost structural recognition.
- `TableFormerMode.ACCURATE`: more expensive recognition intended for challenging tables.

The `do_cell_matching` option governs association of predicted table cells with PDF text cells. This matters because recovering a grid and obtaining correct cell content are related but different tasks.

The structured representation can include row/column spans, cell locations and header annotations. This allows downstream table operations to use an actual cell model rather than reverse-engineering Markdown pipes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Tables remain a significant source of ambiguity: multi-level headers, borderless layouts, dense scientific tables, nested-looking structures and mixed OCR/native text can defeat structural recognition. Native Office spreadsheet/chart extraction and PDF table recognition should not be treated as equivalent operations.

### 5.3 Form-field recovery and complex cells

With `PdfPipelineOptions(extract_form_fields=True)`, Docling can extract native interactive PDF form widgets (AcroForm) into format-neutral `FieldItem` objects, containing `FieldValueItem` children.

Field labels are associated using nearby printed text and geometric relationships. Checkbox and radio-option labels can also be recovered.

This is distinct from visually detecting a blank line or checkbox in a scanned form. If a document has been flattened into ordinary page graphics, the original form-widget metadata is no longer available to the native form extractor.

Rich table cells can additionally represent content more complex than a single text string.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



PDF form extraction: [https://docling-project.github.io/docling/usage/advanced_options/#extract-native-pdf-form-fields](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com#extract-native-pdf-form-fields)

### 5.4 Images, cropped regions and spatial grounding

Docling can retain page imagery, individual picture imagery and spatial information about extracted items.

Relevant options include `generate_page_images`, `generate_picture_images` and `images_scale`. The document model associates items with page provenance and, where available, bounding boxes.

Together, these capabilities support a useful pattern: a downstream system can operate on the semantic document while retaining enough page location information to retrieve a corresponding visual region.

For example, an extraction or retrieval result can carry both the text of a table and the page coordinates needed for visual inspection. Such grounding depends on the source format, pipeline and retained image assets; it is not inherent to every export format.

Figure-export example: [https://docling-project.github.io/docling/examples/export_figures/](https://docling-project.github.io/docling/examples/export_figures/?utm_source=chatgpt.com)

## 6. OCR subsystem

Docling treats OCR as a pluggable recognition stage rather than requiring a single OCR engine.

Its documented engines include RapidOCR, EasyOCR, Tesseract through CLI or `tesserocr`, macOS Vision through `ocrmac`, and Nemotron-OCR. Remote inference is available through a KServe v2-compatible interface. Additional implementations can be registered as external plugins.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 6.1 Selection considerations

| Engine family | Distinguishing considerations                                                                                |
| ------------- | ------------------------------------------------------------------------------------------------------------ |
| RapidOCR      | Local OCR with configurable model/backend choices, including Torch and ONNX Runtime configurations.          |
| EasyOCR       | Neural multilingual OCR; language coverage and model provisioning depend on the selected recognition models. |
| Tesseract     | Mature configurable OCR with native language packs and both executable and Python-binding integration paths. |
| macOS Vision  | Delegates recognition to Apple's platform OCR facilities; platform-specific.                                 |
| Nemotron-OCR  | Model-based recognition with its own dependencies and supported execution configurations.                    |
| KServe v2     | Separates OCR model serving from the Docling worker through an inference-server interface.                   |

The common `OcrOptions.lang` field accepts either engine-native language identifiers or BCP-47-style identifiers prefixed with `iso:`. Engine-specific mapping still matters: script distinctions or unsupported language combinations may not survive conversion to the engine's native language set.

### 6.2 Selective OCR, full-page OCR and broken text layers

Docling can combine native PDF text extraction with OCR, rather than treating every PDF page as an image.

This creates three distinct situations:

1. Native text available and reliable: Text-layer extraction can avoid OCR.
2. Scanned or raster content: OCR is needed to recover text.
3. Text layer present but corrupted: OCR may be needed to replace apparently valid but unusable extracted characters.

The `replace_broken_text_layer` mechanism targets detectable encoding/text-layer corruption. It is not a general semantic spell-checker, and it cannot guarantee correction of plausible but incorrect recognized text.

Full-page OCR can be forced, but it may discard useful distinctions from a high-quality native text layer while increasing processing cost.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



OCR documentation: [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

## 7. Vision-language models and model backends

### 7.1 VLM conversion versus specialized document models

Docling supports vision-language models at more than one level:

- Whole-page conversion: A VLM interprets page imagery and produces structured document content.
- Selective enrichment: A VLM interprets a particular element, such as a figure, formula or chart, after document conversion.
- Model-specific recognition: Specialized models may implement a particular subtask, such as structured table or formula recognition.

These are different architectural roles. A VLM need not replace native text extraction, OCR and layout recognition merely because it can perform end-to-end page interpretation.

`VlmPipeline` accepts model outputs such as DocTags, Markdown or HTML. DocTags is the preferred native structured-output representation, while Markdown/HTML paths have different structural and parsing constraints.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.2 Supported model ecosystem

The documented catalog includes Docling-oriented models such as Granite-Docling and SmolDocling, plus broader model families and specialized integrations. Recent adapters include options associated with MinerU, Chandra and other document-oriented VLM processing.

Docling provides predefined model specifications and configurable inference settings through `VlmPipelineOptions`, `InlineVlmOptions` and related engine options.

Important backend distinctions include:

| Inference path            | Role                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------ |
| Hugging Face Transformers | Local inference on supported CPU/GPU accelerators.                                   |
| MLX                       | Local inference for supported Apple Silicon model implementations.                   |
| OpenAI-compatible APIs    | Remote or locally hosted inference via servers such as vLLM or compatible endpoints. |
| Specialized adapters      | Model-specific output parsing, multi-step inference or recognition behavior.         |

A model being listed does not imply every model supports every backend, device, output representation or enrichment stage. Model weights, model adapters, inference engines and the Docling package have separate compatibility and licensing considerations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Model catalog: [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)

VLM configuration: [https://docling-project.github.io/docling/usage/vision_models/](https://docling-project.github.io/docling/usage/vision_models/?utm_source=chatgpt.com)

### 7.3 Why output representation matters

A VLM that returns Markdown may appear interchangeable with one that returns DocTags, but Markdown can omit information necessary to recover cell spanning, bounding geometry or typed structural relationships.

A model-generated structured format can preserve more of these distinctions, although structural completeness still depends on what the model actually predicts.

Consequently, an end-to-end VLM pipeline is a potentially powerful alternative for difficult visual documents, not a general guarantee of greater fidelity than a native-text-plus-layout pipeline.

## 8. `DoclingDocument`: the canonical structured representation

The most architecturally consequential capability in Docling is its document model, implemented in `docling-core`.

`DoclingDocument` is a Pydantic-based, typed representation with explicit support for content identity, document hierarchy, content layers, page geometry and provenance.

Unlike Markdown, which primarily expresses a linear sequence of text and formatting, the Docling model preserves relationships among document objects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 8.1 Content objects and document structure

The model separates content storage from structural organization.

| Component         | Semantics                                                                                             |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| `texts`           | Paragraphs, titles, section headings, list items, code blocks, formulas and other text-bearing items. |
| `tables`          | Structured `TableItem` objects with grids, cells and optional semantic annotations.                   |
| `pictures`        | `PictureItem` objects with image references, captions and optional enrichments.                       |
| `key_value_items` | Key-value relationships represented as typed content.                                                 |
| `form_items`      | Form-specific content and field/value structures where supported.                                     |
| `groups`          | Logical containers such as lists and chapters, including relationships among elements.                |
| `body`            | Root of the principal document content tree.                                                          |
| `furniture`       | Content outside the main body, such as page headers and footers.                                      |
| `pages`           | Page-level information, including dimensions and relevant image/provenance data.                      |

Content elements can be associated with parent and child nodes through JSON-pointer references. Consequently, the model supports both a collection-oriented view of elements and a hierarchical view of the whole document.

Reading order is represented structurally, principally through the order of children in the body tree. It is not merely a sort over page coordinates. This is important for layouts where reading order and geometric ordering diverge.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 8.2 Content layers preserve distinctions that text export usually erases

The `ContentLayer` mechanism distinguishes principal body content from supplemental material.

For example, an Apple Pages document may contain headers and footnotes in `furniture`, while comments are stored in `notes`. Keynote presenter notes and annotations can likewise be represented separately from slide content.

Export methods can explicitly include additional layers:

```
from docling_core.types.doc import ContentLayermarkdown = document.export_to_markdown(    included_content_layers={        ContentLayer.BODY,        ContentLayer.FURNITURE,        ContentLayer.NOTES,    })
```

The default export behavior generally emphasizes the body. Including other layers is a semantic decision, not merely a formatting option: comments, running headers and speaker notes have different roles from the substantive document text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 8.3 Provenance, geometry and reusable document identity

Document items can carry provenance records linking them to source pages and bounding boxes. This permits operations such as source-aware extraction, page-specific filtering and visual grounding.

The value of this representation extends beyond conversion:

- A single document can be exported differently for human reading, indexing, model input or structural analysis.
- Downstream systems can retain object-level identifiers and source locations instead of treating the entire document as an undifferentiated string.
- Applications can construct, modify or enrich a document programmatically using `docling-core` without invoking the conversion pipeline again.

These are architectural possibilities enabled by the model, not guarantees that every source element has a precise location or stable identity across different conversion runs.

Document model: [https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/?utm_source=chatgpt.com)

Core source: [https://github.com/docling-project/docling-core/tree/main/docling_core/types/doc](https://github.com/docling-project/docling-core/tree/main/docling_core/types/doc?utm_source=chatgpt.com)

## 9. Serialization and fidelity-preserving export

Serialization is a separate subsystem rather than a fixed final stage inside document conversion.

Docling provides a hierarchy of serializers, including `BaseDocSerializer`, text/table/picture serializers, serializer providers and `MarkdownDocSerializer`. A serializer can return both a textual result and information about which document components contributed to it.

This makes export policies extensible at the level of individual content types rather than requiring complete replacement of the document conversion process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 9.1 Output formats have materially different information capacity

| Output                    | Principal characteristics                                                             | Fidelity consideration                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Docling JSON              | Structured schema serialization of the document model.                                | Strongest general-purpose interchange representation for retained Docling information.        |
| DocTags                   | Structured text representation for document elements, including OTSL table structure. | Suitable for structured model interactions; not a replacement for all original file metadata. |
| DocLang / DocLang archive | Structured document representation, optionally including associated page imagery.     | Supports richer round-trip exchange than plain text.                                          |
| HTML                      | Text, images, formatting and HTML table spanning.                                     | Preserves some structural relationships that Markdown cannot.                                 |
| Markdown                  | Human-readable linearized document, headings, lists and tables.                       | Simplifies or loses some geometry, cell spanning and annotation relationships.                |
| Plain text                | Textual content without rich structure.                                               | Appropriate where structure is irrelevant.                                                    |
| LaTeX                     | Mathematical and textual representation.                                              | The current serializer does not reconstruct every source-format feature.                      |
| WebVTT                    | Time-aligned transcription/subtitle output.                                           | Audio/video-specific; not a general document serialization format.                            |

One documented example is merged table cells.

`TableData.grid` records `row_span`, `col_span` and grid offsets. JSON, DocTags, DocLang and HTML can preserve these relationships. Markdown cannot represent merged cells natively, so Docling places content at the originating grid position and leaves covered positions empty. The current LaTeX serializer similarly flattens spans rather than emitting complete `\multirow`/`\multicolumn` structures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



This yields an important distinction:

Lossless serialization of a `DoclingDocument` does not mean lossless reconstruction of the original document. Some original features may already have been discarded, approximated or inferred during conversion.

### 9.2 Custom serialization

A system requiring specialized representations can customize serializers for document elements, particularly tables, pictures and text.

For example, a custom table serializer could emit nested JSON, a typed table schema or a domain-specific representation instead of Markdown. This is a narrower extension than creating a new file parser.

Image persistence is also a separate concern: image-reference modes, external image files, embedded assets and local-image loading policies affect whether a serialized document is self-contained and how it can be safely reloaded.

Serialization documentation: [https://docling-project.github.io/docling/concepts/serialization/](https://docling-project.github.io/docling/concepts/serialization/?utm_source=chatgpt.com)

## 10. Structure-aware and tokenizer-aware chunking

Docling provides chunking directly over its structured document representation, rather than requiring export to Markdown followed by generic text splitting.

This is especially valuable when section hierarchy, captions, list relationships or table headers are important to retrieval quality. The actual chunking abstractions are also available in `docling-core`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 10.1 Three principal chunking strategies

| Chunker                 | Mechanism                                                                                                  | Distinguishing value                                                 |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `HierarchicalChunker`   | Splits at document-element boundaries, carrying relevant heading/caption metadata; can merge list items.   | Preserves semantic structure without a tokenizer-driven target size. |
| `HybridChunker`         | Starts with hierarchical chunks, splits token-oversized chunks and can merge smaller compatible neighbors. | Combines semantic boundaries with model context-budget constraints.  |
| `LineBasedTokenChunker` | Uses tokenizer limits while trying to preserve whole lines.                                                | Useful for tabular text, code, logs and line-sensitive formats.      |

`BaseChunker` defines two particularly useful operations:

```
chunker.chunk(document)chunker.contextualize(chunk)
```

The first returns structured chunks with metadata. The second creates a potentially metadata-enriched text representation suitable for embedding or generation.

This distinction allows the stored chunk representation and the embedding input to differ: headings and captions can be supplied as retrieval context without necessarily changing the underlying content elements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 10.2 Hybrid chunking has important advanced behavior

`HybridChunker` applies tokenizer-aware refinement to hierarchical chunks.

Its behavior includes splitting oversized content, optionally merging neighboring chunks sharing compatible heading/caption context (`merge_peers=True`), and controlling table-header repetition when a table must span multiple chunks.

The `repeat_table_header=True` option is especially consequential: splitting a table into multiple chunks without its column headers can make individual rows unintelligible. `omit_header_on_overflow` offers an alternative when repeated headers prevent otherwise valid rows from fitting within the token budget.

`LineBasedTokenChunker` separately supports repeated prefixes and overflow handling without unnecessarily breaking lines.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



A concise example:

```
from docling.chunking import HybridChunkerchunker = HybridChunker()for chunk in chunker.chunk(document):    text_for_embedding = chunker.contextualize(chunk)
```

For a production embedding pipeline, the tokenizer and token limit should correspond to the downstream model. When using `docling-core` independently, the Hugging Face and OpenAI tokenizer integrations are exposed through different optional extras.

Limit: Chunking can preserve the hierarchy Docling recognized; it cannot repair an incorrect heading tree or missing table semantics automatically.

Chunking documentation: [https://docling-project.github.io/docling/concepts/chunking/](https://docling-project.github.io/docling/concepts/chunking/?utm_source=chatgpt.com)

## 11. Content enrichment and schema-oriented extraction

### 11.1 Enrichment operates on selected document elements

Docling offers optional enrichment stages that analyze already recognized content. Most are disabled by default because they introduce additional model inference.

| Enrichment             | Configuration               | Added capability                                                                           |
| ---------------------- | --------------------------- | ------------------------------------------------------------------------------------------ |
| Code understanding     | `do_code_enrichment`        | Recognition of code content and programming-language metadata.                             |
| Formula understanding  | `do_formula_enrichment`     | Converts detected mathematical formulas into LaTeX representations.                        |
| Picture classification | `do_picture_classification` | Adds semantic classifications to picture elements.                                         |
| Picture description    | `do_picture_description`    | Produces natural-language descriptions using local or remote vision models.                |
| Chart extraction       | `do_chart_extraction`       | Attempts to recover chart information and underlying structured data from rendered charts. |

Formula enrichment can be combined with HTML serialization that renders mathematical content using MathML. Picture descriptions and classifications can improve the semantic accessibility of figures that otherwise contribute little searchable text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



These enrichments are not equivalent to original-document metadata. A model-generated description of a scientific plot, for example, is an interpretation of visual evidence and may contain errors.

### 11.2 Two fundamentally different chart extraction paths

Docling has a particularly useful distinction between native chart-data recovery and visual chart interpretation.

Native Office chart recovery reads series/category data that the source format stores explicitly. This can yield structured values without estimating them from pixels.

Visual chart extraction instead analyzes a rendered chart image, using model-based interpretation. It can be applied to charts found in PDFs or images, but extracted values depend on whether the visual data are readable and accurately interpreted.

The two approaches can share a downstream `PictureItem` representation, yet they have different provenance, error profiles and opportunities for validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Enrichment documentation: [https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)

### 11.3 `DocumentExtractor`: schema-guided information extraction

Docling also provides `DocumentExtractor` for turning unstructured PDF or image content into fields defined by a template.

Templates can be supplied as a string, dictionary, Pydantic model class or Pydantic model instance. The extractor returns page-oriented results containing extracted data, raw model output and errors.

The documented interface supports nested Pydantic schemas, making it more expressive than flat key/value extraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



A simplified illustration:

```
from pydantic import BaseModelfrom docling.datamodel.base_models import InputFormatfrom docling.document_extractor import DocumentExtractorclass Invoice(BaseModel):    invoice_number: str    total: floatextractor = DocumentExtractor(    allowed_formats=[InputFormat.PDF, InputFormat.IMAGE])result = extractor.extract(    source="invoice.pdf",    template=Invoice,)
```

Maturity and scope: This is a model-based information-extraction facility, documented through the VLM-enabled extraction examples, not a general-purpose deterministic schema parser. The documented extractor targets PDF and image sources rather than the full range of `DocumentConverter` inputs. It should be considered a more specialized, evolving interface. Pydantic validation can establish conformity to a schema; it does not establish that a generated value is factually correct.

Information-extraction example: [https://docling-project.github.io/docling/\_generated/examples/extraction/](https://docling-project.github.io/docling/_generated/examples/extraction/?utm_source=chatgpt.com)

## 12. Audio and video document understanding

Docling's common document representation also encompasses time-based media.

### 12.1 Audio transcription

`AsrPipeline` transcribes supported audio formats into structured text items with timing metadata.

The default speech-recognition family is Whisper, with backends including native PyTorch Whisper and MLX Whisper on supported Apple Silicon systems. WhisperS2T offers an additional, explicitly selected CTranslate2-based path using batching and voice-activity segmentation; it is documented as experimental.

Additional Transformers-based speech-model presets cover selected Granite Speech, Nemotron Speech and Parakeet checkpoints. These models do not all produce equivalent timing or segmentation representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 12.2 Video processing

The video pipeline combines audio transcription with sampled visual frames.

Its frame-selection approaches include fixed-interval sampling and scene-change sampling. Optional speaker diarization is supported for video through additional dependencies.

The resulting `DoclingDocument` can contain timed transcript segments and visual content, supporting unified search, summarization and export across the media modalities.

Video processing requires FFmpeg for relevant media operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 12.3 Limitations

The audio-only pipeline does not provide built-in speaker diarization. Standard subtitle export supports WebVTT rather than SRT, and word-level timing information is not generally exposed through current standard export formats, even where some speech backends can return finer-grained timing data.

These limits make the media pipelines better characterized as document-oriented transcription and media understanding than as comprehensive professional subtitle-editing tools.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Media documentation: [https://docling-project.github.io/docling/usage/processing_audio_media/](https://docling-project.github.io/docling/usage/processing_audio_media/?utm_source=chatgpt.com)

## 13. Extensibility architecture

Docling exposes several extension boundaries, each suitable for a different kind of change.

### 13.1 Plugin factories

External plugins are registered through Python package entry points using `pluggy`.

The documented plugin categories include:

| Factory                   | Extension contract                          | Purpose                                           |
| ------------------------- | ------------------------------------------- | ------------------------------------------------- |
| `ocr_engines`             | `BaseOcrModel` and `OcrOptions` derivatives | Add alternative recognition engines.              |
| `layout_engines`          | `BaseLayoutModel` and layout options        | Replace or extend page-layout recognition.        |
| `table_structure_engines` | `BaseTableStructureModel` and table options | Introduce different table-recognition approaches. |

Plugins can expose language capabilities, inference settings and model choices as typed configuration rather than requiring Docling to know their implementations in advance.

A particularly useful detail is the OCR-language mapping contract: external engines can declare which languages and scripts they support and reject unsupported combinations explicitly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Third-party plugins are disabled unless enabled through `allow_external_plugins=True` or the corresponding CLI switch. This is a meaningful code-execution boundary because registering a plugin loads externally supplied Python implementation code.

### 13.2 Backends, pipelines and enrichments are distinct extensions

A backend is appropriate when supporting a new source representation or parser.

A pipeline is appropriate when changing the orchestration of parsing, recognition and enrichment stages.

A model/plugin extension is narrower: it can replace a specific OCR, layout or table-recognition component.

An enrichment model can operate on an existing document object without reimplementing source-file parsing. A serializer or chunker can change downstream behavior without touching conversion at all.

This separation provides an opportunity to avoid large custom conversion frameworks when the required variation is limited to one pipeline stage or output representation. It does not eliminate the need to understand the data contracts at each extension boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Plugin documentation: [https://docling-project.github.io/docling/concepts/plugins/](https://docling-project.github.io/docling/concepts/plugins/?utm_source=chatgpt.com)

## 14. Execution model, performance and operational controls

### 14.1 Device selection and inference optimization

Docling offers accelerator configuration, including CPU and supported GPU paths such as CUDA and Apple MPS.

Actual device availability depends on the selected model, backend and installed dependencies. For example, GPU support for a particular OCR engine may require its own GPU-enabled runtime rather than merely setting Docling's accelerator to CUDA.

The standard PDF pipeline exposes batching controls through `ThreadedPdfPipelineOptions`, including `ocr_batch_size`, `layout_batch_size` and `table_batch_size`. The documentation notes that table-stage GPU batching is not equivalent to layout-stage batching in the current implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



There are several separate performance levers:

| Mechanism              | What it changes                                                                        |
| ---------------------- | -------------------------------------------------------------------------------------- |
| Native PDF extraction  | Avoids recognition-model inference entirely where source content is already available. |
| Pipeline feature flags | Avoids unnecessary OCR, table recognition or enrichment.                               |
| GPU acceleration       | Offloads supported model inference to accelerators.                                    |
| Model batching         | Amortizes inference overhead over more pages or elements when supported.               |
| PDF parser threading   | Controls `docling-parse` work independently of model inference threading.              |
| VLM inference servers  | Can centralize model execution and support server-side batching and concurrency.       |
| Model prefetching      | Removes first-use weight downloads from the conversion path.                           |
| Document limits        | Prevents unexpectedly large inputs from monopolizing resources.                        |

Model quality, rendering resolution, batch size, memory consumption and concurrency interact. Larger batches can increase throughput but also increase accelerator-memory pressure. There is no single configuration that can be assumed optimal for all documents.

Performance and GPU documentation: [https://docling-project.github.io/docling/usage/gpu/](https://docling-project.github.io/docling/usage/gpu/?utm_source=chatgpt.com)

### 14.2 Model provisioning and offline execution

Docling automatically downloads some model artifacts on first use. `docling-tools models download`, `artifacts_path` and `DOCLING_ARTIFACTS_PATH` support explicit provisioning and offline use.

Not every model family is included in the same download command. In particular, ASR, VLM and backend-specific artifacts may require separate model selection and provisioning.

Local inference does not necessarily mean zero network activity on first execution. Once the required artifacts are available, local inference and document processing can be kept separate from externally hosted inference services.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 14.3 Resource constraints and robustness

Document conversion exposes several important resource-management controls.

`max_file_size` and `max_num_pages` bound source workload size. Image backends also enforce pixel-count limits. Archive-based formats such as DOCX, XLSX and EPUB have decompressed-byte and member-count checks intended to constrain unexpectedly large embedded data.

Generic ZIP archives can be expanded through `convert_all()`, with `raises_on_error=False` allowing later members to be processed even when some members fail. The API also supports in-memory `DocumentStream` input.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Progress reporting and per-document callbacks provide visibility into conversion stages without requiring a separate monitoring framework for basic execution progress.

### 14.4 Explicit remote-service boundaries

Docling's local model path is designed to avoid transmitting document data to external inference providers.

Remote model calls require explicit opt-in through `enable_remote_services=True`, including supported remote OCR, VLM and picture-description configurations. This control concerns outbound document data; model-weight downloads are governed separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



For web content, remote image fetching is also separately configurable. The HTML backend includes protections around destination addresses, redirects, image size and forwarding of authorization headers. Those protections depend on network configuration; for example, an external proxy has separate responsibility for its forwarding behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Operational configuration: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 15. Packaging and companion libraries

Docling has evolved into a modular package family. Understanding package boundaries is important because they influence dependency size, supported operations and deployment topology.

### 15.1 `docling` versus `docling-slim`

The `docling` distribution is now a standard-feature meta-package built on `docling-slim`.

`docling-slim` contains the actual Python SDK implementation and exposes opt-in extras for individual formats, OCR systems, model runtimes, chunking, CLI functionality and service connectivity. Its release number tracks the Docling distribution. Both have a verified 2.143.1 release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Representative installation profiles:

| Goal                              | Package configuration                        |
| --------------------------------- | -------------------------------------------- |
| Standard SDK and CLI              | `docling`                                    |
| Core PDF support without local ML | `docling-slim[format-pdf,cli]`               |
| Office processing                 | `docling-slim[format-office]`                |
| Local model-based conversion      | `docling-slim[format-pdf,models-local]`      |
| Lightweight PDF OCR               | `docling-slim[format-pdf,feat-ocr-rapidocr]` |
| Remote service client             | `docling-slim[service-client]`               |
| Structure-aware chunking          | `docling-slim[feat-chunking]`                |

The principal architectural benefit is that applications using only native format parsers or a remote conversion server need not necessarily pull an entire PyTorch-based model stack into their local runtime.

Some extras have narrow platform requirements. Nemotron-OCR, for instance, is documented for Linux x86_64, Python 3.12 and CUDA 13.x; it should not be assumed portable across every environment supported by the base library.

`docling` itself requires Python 3.10 or later, with platform-specific dependency considerations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Packaging reference: [https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/references/slim-packaging.md](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/references/slim-packaging.md?utm_source=chatgpt.com)

Installation: [https://docling-project.github.io/docling/getting_started/installation/](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)

### 15.2 Companion libraries

| Package or project   | Responsibility                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `docling-core`       | `DoclingDocument`, foundational types, construction, serialization and chunking transforms. |
| `docling-parse`      | Native PDF parsing, extraction and rendering capabilities used by PDF pipelines.            |
| `docling-ibm-models` | Implementations and integration of specialized Docling model families.                      |
| `docling-slim`       | Modular Python SDK distribution with optional feature dependencies.                         |
| `docling-serve`      | HTTP conversion service, deployment tooling and API interface.                              |
| `docling-mcp`        | MCP-facing document-processing tools for AI agents.                                         |
| `docling-jobkit`     | Batch/distributed job orchestration and source/target connectors.                           |

These are separate distributions with their own release histories. It would be incorrect to infer a `docling-core`, `docling-serve` or `docling-parse` version solely from `docling==2.143.1`.

This package separation also creates useful integration boundaries. Consumers needing the document schema but not document conversion can use `docling-core`; distributed processing can use service/job components without requiring every caller to load models locally.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 16. Services, agents and downstream AI integration

### 16.1 CLI and REST serving

The `docling` CLI exposes conversion, output-format selection, pipeline configuration and model-related controls.

`docling-serve` is the separate service implementation. It provides a stable v1 REST API, with deployment and UI options. Its API version is not the same as the Python library's major version.

This creates a useful decoupling: an application can use the local Python SDK directly or delegate conversion to a separate process or server with its own inference runtime.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Serve source: [https://github.com/docling-project/docling-serve](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)

REST API: [https://docling-project.github.io/docling/usage/api_server/rest_api/](https://docling-project.github.io/docling/usage/api_server/rest_api/?utm_source=chatgpt.com)

### 16.2 MCP for agent-accessible document conversion

`docling-mcp` exposes Docling functionality to MCP clients.

Its documented operation supports local document conversion and delegation to `docling-serve` through a remote service URL. A configured local fallback is also available with appropriate optional dependencies.

This provides an agent tool boundary for conversion and related functionality, rather than requiring agents to invoke arbitrary Python code inside their own runtime. The MCP interface is a companion package; it is not an intrinsic property of `DoclingDocument`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



MCP documentation: [https://docling-project.github.io/docling/usage/mcp/](https://docling-project.github.io/docling/usage/mcp/?utm_source=chatgpt.com)

MCP source: [https://github.com/docling-project/docling-mcp](https://github.com/docling-project/docling-mcp?utm_source=chatgpt.com)

### 16.3 Batch and distributed jobs

`docling-jobkit` supports local processing and execution with Ray or Kubeflow Pipelines.

It supplies source and destination connectors for HTTP, S3-compatible stores, Google Drive and Google Cloud Storage.

This moves beyond the `DocumentConverter` iterator API into orchestration of document-processing jobs and external storage. The important distinction is that the Jobkit package handles job execution and connector integration, while Docling remains responsible for conversion semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Jobkit documentation: [https://docling-project.github.io/docling/usage/jobkit/](https://docling-project.github.io/docling/usage/jobkit/?utm_source=chatgpt.com)

### 16.4 Retrieval and AI framework integration

Docling provides examples and integrations with LangChain, LlamaIndex, Haystack and other retrieval or agentic frameworks, alongside examples for vector stores and search engines.

Its role is usually document understanding and preparation, not embedding generation, vector indexing or retrieval execution.

A typical capability composition is:

`DocumentConverter` → `DoclingDocument` → structure-aware chunking → model-specific contextualization → external embedding/indexing system.

This design keeps document semantics independent of the retrieval framework. It can also reduce the need to repeat parsing and restructuring when changing embedding models or vector databases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Integrations: [https://docling-project.github.io/docling/integrations/](https://docling-project.github.io/docling/integrations/?utm_source=chatgpt.com)

## 17. Confidence, limitations and important architectural decisions

### 17.1 Conversion confidence is useful but not proof of correctness

`ConversionResult.confidence` exposes quality assessments at page and document levels.

The documented categories include `POOR`, `FAIR`, `GOOD` and `EXCELLENT`, with component assessments for layout, OCR and native text parsing, plus summary fields such as `mean_grade` and `low_grade`.

The numerical scores are implementation-dependent and may change. The documentation explicitly indicates that `table_score` is not yet implemented. Therefore, a high overall confidence grade should not be interpreted as verified accuracy of every table, formula or generated figure description.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Confidence documentation: [https://docling-project.github.io/docling/concepts/confidence_scores/](https://docling-project.github.io/docling/concepts/confidence_scores/?utm_source=chatgpt.com)

### 17.2 Important distinctions when selecting Docling capabilities

| Question                                                   | Consequential distinction                                                                                |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Is the source digitally structured or visually rendered?   | Native-format parsing may recover precise structure that layout/OCR must otherwise infer.                |
| Are original text bytes or semantic layout more important? | Native PDF extraction avoids recognition inference; standard/VLM pipelines add semantic processing.      |
| Must table spans survive?                                  | JSON, HTML, DocTags and DocLang offer stronger structural preservation than Markdown.                    |
| Must annotations and notes be retained?                    | Content layers must be understood and explicitly selected for export.                                    |
| Are numbers from charts required?                          | Native chart datasets and VLM-extracted visual values have different accuracy characteristics.           |
| Is deterministic extraction required?                      | OCR, layout models, VLM interpretation and enrichment are probabilistic stages.                          |
| Is the workload large or GPU-intensive?                    | Model selection, batching, parallelism, preprocessing and memory limits materially influence throughput. |
| Is a remote service acceptable?                            | Separate client/server deployment, privacy boundaries and model provisioning requirements matter.        |
| Is the output destined for retrieval?                      | Chunk directly from the structured document when hierarchy and contextual metadata are important.        |
| Is only the data model needed?                             | `docling-core` avoids importing full conversion responsibilities.                                        |

### 17.3 Principal limitations

Docling does not guarantee perfect preservation of original files. Source-specific features may be omitted, simplified or translated into a semantically related but different representation.

Its PDF hierarchy and reading order are reconstructed from available signals; layout recognition can make errors. OCR output depends on scan quality, model and language. VLM-generated content can be incomplete or hallucinated. Markdown and some other exporters discard structure that exists in `DoclingDocument`.

Some specialized capabilities are optional, backend-specific or still evolving. Availability in the live documentation does not imply identical maturity across all models and platforms.

Finally, Docling is not, by itself, a complete document-management, search, vector-database, workflow or governance system. The companion ecosystem supplies some of those adjacent functions, but durable storage, retrieval, validation and application-specific semantics remain external concerns.

## 18. Architectural synthesis

Docling's greatest value is not simply that it can convert PDFs to Markdown. It provides three mutually reinforcing capability layers:

1\. Heterogeneous-source normalization. Multiple parsers, OCR engines and recognition pipelines can produce one typed document representation. This reduces format-specific processing logic downstream.

2\. Structural intelligence and provenance. Document hierarchy, content layers, table grids, spatial coordinates, figures and enrichments preserve information that plain-text conversion would discard. That information can support more precise extraction, grounding, indexing and inspection.

3\. Independent downstream transformations. Serialization, chunking, schema-guided extraction, model enrichment and service integration are separable mechanisms. An application can compose these functions without rebuilding the entire document-processing pipeline each time an output requirement changes.

The central design opportunity is to treat `DoclingDocument` as a structured intermediate representation for document information, with Markdown or other text formats as deliberately chosen projections of that representation.

That approach is most valuable when document semantics, heterogeneous sources or multiple downstream consumers matter. Where only inexpensive extraction of native text is required, the native pipeline or a narrower PDF parser may be simpler. Where the primary requirement is interpreting rasterized visual complexity, OCR/VLM approaches become more important.

Source/version qualification: The overview targets the verified 2.143.1 release of October 27, 2026. Primary documentation was researched as of October 28, 2026. Docling's public documentation and model catalog are updated continuously, and companion packages have independent versions; consequential deployment-specific behavior should be checked against the corresponding tagged implementation and model configuration.