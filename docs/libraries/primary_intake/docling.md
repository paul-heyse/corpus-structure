# Docling — Comprehensive Python Library Overview

Target version: 2.145.0 (stable) · Released October 29, 2026 · Research date: October 31, 2026 · Python 3.10+ · MIT license

Official repository: [https://github.com/docling-project/docling](https://github.com/docling-project/docling?utm_source=chatgpt.com)

Documentation: [https://docling-project.github.io/docling/](https://docling-project.github.io/docling/?utm_source=chatgpt.com)

Release history: [https://github.com/docling-project/docling/releases](https://github.com/docling-project/docling/releases?utm_source=chatgpt.com)

Version verified against PyPI and upstream releases. The overview targets released functionality, with experimental and planned capabilities distinguished explicitly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 1. Executive orientation

Docling is a multimodal document-understanding and conversion framework that transforms heterogeneous source documents into a common, structured, provenance-aware representation.

Its defining capability is not merely extracting text from PDF or Office documents. Docling attempts to reconstruct document semantics: paragraphs, headings, reading order, tables, figures, formulas, code, lists, relationships, and their physical locations in the source.

It combines deterministic format parsers, document-layout models, OCR, table-structure recognition, vision-language models (VLMs), and semantic enrichment behind a unified Python interface.

The resulting `DoclingDocument` becomes a reusable intermediate representation for document analysis, structured extraction, retrieval-augmented generation (RAG), indexing, transformation, and serialization.

### 1.1 Capability map

| Capability family                | Principal mechanisms                                                | Architectural significance                                                 |
| -------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Multi-format ingestion           | `DocumentConverter`, format backends, conversion pipelines          | One conversion interface across PDFs, Office, HTML, XML, images, and media |
| PDF understanding                | PDF parsing, layout detection, reading-order reconstruction, OCR    | Recover logical structure beyond raw text extraction                       |
| Table reconstruction             | TableFormer, cell alignment, spanning cells, table export           | Preserve useful relational and tabular structure                           |
| Vision and multimodal processing | VLM pipelines, GraniteDocling, image classification, ASR            | Interpret content inaccessible to ordinary text parsers                    |
| Structured document model        | `DoclingDocument`, typed items, hierarchy, provenance               | Preserve document semantics independently of output format                 |
| Enrichment                       | Picture descriptions, code/formula recognition, chart understanding | Add machine-readable interpretation to visual content                      |
| Transformation and export        | JSON, Markdown, HTML, DocTags, DocLang, configurable serializers    | Support multiple consumers without reparsing                               |
| Semantic chunking                | `HierarchicalChunker`, `HybridChunker`                              | Respect document structure and model token budgets                         |
| Extension and orchestration      | Format backends, custom pipelines, stage plugins, batch processing  | Replace or specialize processing components                                |
| Ecosystem integration            | Python, CLI, REST services, MCP, RAG adapters                       | Embed document understanding into larger workflows                         |

### 1.2 Why Docling is architecturally distinctive

Three characteristics are particularly important.

First, it separates source-format interpretation from downstream representation. A PDF, Word document, spreadsheet, and HTML page can all be transformed into variants of the same logical document model. Downstream consumers therefore need not understand every original format.

Second, its conventional PDF pipeline is compositional. Layout analysis, OCR, table recognition, and enrichment are distinct concerns rather than one opaque model invocation. This permits selective execution, substitution, and performance tuning.

Third, the structured document is a first-class output, not an incidental intermediate artifact. A document can be inspected, modified, filtered, serialized, chunked, or enriched after conversion. That separates document understanding from retrieval, language-model prompting, and business-specific information extraction.

These are particularly consequential when document content must serve several different consumers, or when preserving page-level evidence and semantic relationships is more important than producing Markdown alone.

Architecture: [https://docling-project.github.io/docling/concepts/architecture/](https://docling-project.github.io/docling/concepts/architecture/?utm_source=chatgpt.com)

Document model: [https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2

## 2. Package architecture and conversion lifecycle

### 2.1 Distinct layers of the Docling ecosystem

Docling is organized around several packages with different responsibilities. The distinction matters because its conversion engine, document schema, models, and deployment services are not a single inseparable runtime.

| Component            | Responsibility                                                       | Important boundary                                                  |
| -------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `docling`            | Main distribution, Python API and CLI                                | User-facing installation and integration surface                    |
| `docling-slim`       | Modular conversion implementation with selectable extras             | Allows smaller installations and more explicit dependency selection |
| `docling-core`       | `DoclingDocument` types, transformations, serialization and chunking | Usable independently of heavyweight parsing and inference           |
| `docling-parse`      | Native PDF parsing, text cells, images, page geometry                | Does not itself perform semantic document understanding             |
| `docling-ibm-models` | Model implementations including TableFormer                          | Model infrastructure rather than the complete converter             |
| `docling-serve`      | HTTP API and remote conversion service                               | Separate deployment and service lifecycle                           |
| `docling-mcp`        | Model Context Protocol interface for agents                          | Exposes conversion capabilities rather than defining them           |
| `docling-jobkit`     | Large-scale job execution and source connectors                      | Orchestration around Docling conversions                            |

A particularly valuable separation is `docling-core` versus `docling`. Applications that only need to construct, manipulate, validate, serialize, or chunk an existing `DoclingDocument` do not necessarily need to load the full OCR/layout inference stack.

Conversely, installing the core schema package alone does not provide the full heterogeneous document converter.

The main `docling` distribution currently builds upon the modular `docling-slim` packaging arrangement. Optional capabilities may require extras, model downloads, external executables, or hardware-specific inference dependencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Installation documentation: [https://docling-project.github.io/docling/getting_started/installation/](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)

Core model repository: [https://github.com/docling-project/docling-core](https://github.com/docling-project/docling-core?utm_source=chatgpt.com)

PDF parser: [https://github.com/docling-project/docling-parse](https://github.com/docling-project/docling-parse?utm_source=chatgpt.com)

### 2.2 Conversion lifecycle

The central entry point is `DocumentConverter`, which associates supported input formats with a document backend and processing pipeline.

Conceptual conversion flow

Conceptual flow; actual stages depend on input format and pipeline configuration. Not every document passes through OCR or AI models.

Three mechanisms determine behavior:

Format backends decode native source representations. A DOCX backend can use the document's explicit XML structure, whereas a PDF backend must reconstruct much of its semantic organization from positioned content and page images.

Pipelines determine which processing operations run. `StandardPdfPipeline`, `NativePdfPipeline`, and `VlmPipeline` provide materially different capabilities rather than interchangeable execution backends.

Pipeline options select engines, models, enrichment stages, images, resource settings, and quality-versus-throughput behavior.

The API supports individual conversion through `convert()`, multiple inputs through `convert_all()`, and format-specific configuration using `PdfFormatOption` and related `FormatOption` types. A `ConversionResult` contains the resulting document along with status, errors, and other diagnostic information.

Converter API: [https://docling-project.github.io/docling/reference/document_converter/](https://docling-project.github.io/docling/reference/document_converter/?utm_source=chatgpt.com)

Pipeline configuration: [https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

## 3. Input formats and what their support means

Docling supports a substantially broader range of input formats than PDF-centric extraction libraries. The important architectural detail is that these formats do not all pass through the same mechanism.

| Format family               | Supported types and distinctive behavior                              |
| --------------------------- | --------------------------------------------------------------------- |
| PDF                         | Digital and scanned PDFs; page layout, OCR, table and figure analysis |
| Microsoft Office            | DOCX, XLSX, PPTX; legacy DOC/XLS/PPT via LibreOffice                  |
| OpenDocument                | ODT, ODS, ODP                                                         |
| Apple iWork                 | Pages, Numbers, Keynote with optional format dependencies             |
| Web and markup              | HTML, XHTML, MHTML, Markdown, AsciiDoc, LaTeX                         |
| Structured content          | CSV, XML JATS, USPTO patents, XBRL, DocLang                           |
| Images                      | PNG, JPEG, TIFF, BMP, WebP                                            |
| Publishing                  | EPUB, RTF                                                             |
| Collaboration and messaging | Box Notes, EML, Outlook MSG                                           |
| Enterprise and archival     | AFP/MO:DCA, EBCDIC-based content with appropriate configuration       |
| Audio and video             | Audio recordings, video containers, WebVTT subtitles                  |
| Native interchange          | Previously serialized Docling JSON, DocLang and related formats       |

### 3.1 Native structure versus inferred structure

This is a consequential distinction across formats.

A DOCX or HTML file may explicitly identify headings, paragraphs, hyperlinks, tables, and structural grouping. A PDF commonly exposes positioned glyphs or text cells rather than a reliable logical document tree. A scanned PDF might expose no meaningful text layer at all.

Therefore:

- Native structured formats can preserve source semantics without reconstructing everything visually.
- Digital PDFs often combine native text extraction with learned layout reconstruction.
- Scans require OCR or multimodal interpretation.
- Presentation and spreadsheet files introduce structures that do not map cleanly onto ordinary flowing text.

Supported conversion does not imply equal structural fidelity across source formats. A consistent `DoclingDocument` interface makes downstream processing uniform, but it does not make every source equally informative.

### 3.2 Less obvious format capabilities

The current format implementations include several notable capabilities beyond simple text extraction.

Office charts: PowerPoint and Excel chart objects can be represented as pictures carrying structured chart metadata, rather than only as a screenshot. Where supported, the converter can preserve chart series, labels, and related information. This is especially valuable when the downstream consumer needs chart data rather than a natural-language caption.

Scientific and financial XML: JATS and XBRL support makes it possible to ingest documents that already contain domain-specific structure. These pathways should be distinguished from extracting equivalent meaning heuristically from a PDF.

Email: MIME and Outlook message parsing can represent message content and selected attachment information. It does not itself amount to a comprehensive mailbox ingestion or attachment-processing system.

Re-import: Native Docling JSON allows a previously converted representation to be loaded again. This enables transformation and enrichment independently of repeated conversion from the original source.

Archives: Batch conversion supports ZIP inputs with decompression limits, helping avoid custom archive traversal for supported conversion workloads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Formats: [https://docling-project.github.io/docling/usage/supported_formats/](https://docling-project.github.io/docling/usage/supported_formats/?utm_source=chatgpt.com)

Advanced format behavior: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 4. PDF processing: three materially different paths

Docling's most technically significant decisions often involve the PDF pipeline.

| Pipeline              | Mechanism                                                       | Preserves or reconstructs                         | Principal tradeoff                                            |
| --------------------- | --------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| `StandardPdfPipeline` | Native PDF parser plus specialized layout, OCR and table stages | Programmatic text and inferred semantic structure | Several inference stages, memory and compute overhead         |
| `NativePdfPipeline`   | `docling-parse` without layout/OCR/table models                 | Native text cells and embedded bitmaps            | Limited semantic reconstruction                               |
| `VlmPipeline`         | Rendered-page interpretation using a vision-language model      | Model-generated structured document content       | Generative uncertainty, inference cost, model-specific output |

### 4.1 Standard PDF pipeline

The standard path combines deterministic and learned operations.

The PDF backend extracts available text cells, positions, and embedded images. Rendered page images support layout inference and OCR. A layout model detects regions such as text, titles, tables, and pictures. Table processing reconstructs cells and relationships. Post-processing resolves reading order and assembles the document representation.

The separation enables work to be selectively avoided. For example, when programmatic text is reliable, the system need not treat the entire page as an image transcription problem.

Similarly, table structure inference can operate on a detected table region rather than requiring a large model to interpret the entire document at once.

This pipeline is therefore more than a PDF-to-text converter: it performs a series of semantic reconstruction operations.

### 4.2 Native PDF pipeline

`NativePdfPipeline` uses `docling-parse` alone. Its documented output contains a text item for each native text cell and pictures for embedded bitmaps, without the standard pipeline's layout, OCR, or table models.

It is a useful alternative when the source has reliable digital text and the desired operation does not require inferred headings, tables, or reading order.

The limitation is fundamental: extracting text cells does not establish their logical relationships. Paragraph reconstruction, multi-column reading order, and table semantics may still be unresolved.

### 4.3 VLM pipeline

`VlmPipeline` feeds rendered pages to a selected vision-language model and interprets the generated DocTags, Markdown, HTML, or other supported model-specific representations.

It offers a different way of obtaining document structure, particularly for visually complex or image-heavy content.

However, VLM generation is not equivalent to deterministic extraction from a text layer. Results can be sensitive to model choice, prompts, output format, page resolution, and inference settings. Native text coordinates and text fidelity may have different characteristics from the conventional pipeline.

The two approaches are better understood as complementary capability families than as a simple quality ranking.

Source: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

VLM pipeline: [https://docling-project.github.io/docling/usage/vision_models/](https://docling-project.github.io/docling/usage/vision_models/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2

## 5. OCR, layout recognition, tables and structural recovery

### 5.1 OCR as a configurable subsystem

Docling integrates multiple OCR engines rather than relying on a single fixed recognizer.

| Engine family                | Distinctive property                                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------ |
| RapidOCR                     | Supports multiple inference backends, including ONNX Runtime, OpenVINO and PaddlePaddle variants |
| Tesseract                    | Established multilingual OCR, available through executable or Python bindings                    |
| EasyOCR                      | Neural OCR with its own language/model support                                                   |
| macOS Vision                 | Native Apple OCR integration                                                                     |
| SuryaOCR                     | Alternative learned OCR family                                                                   |
| Nemotron-OCR                 | Additional model-based OCR path                                                                  |
| Remote KServe-compatible OCR | Separates inference execution from the converter process                                         |

`PdfPipelineOptions.do_ocr` governs OCR participation, while `ocr_options` selects the engine and its configuration.

More subtle controls concern when OCR should replace, supplement, or ignore native PDF text. A PDF can contain a text layer that is present but corrupted. In that situation, simply detecting that text exists is not a sufficient extraction strategy.

Recent RapidOCR options include replacement of broken PDF text layers. The latest release also adds RapidOCR page-orientation detection, addressing another failure mode in scanned documents.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Language configuration is engine-specific. Docling documents native engine codes and `iso:`-prefixed language identifiers; language availability and supported combinations must be checked against the selected OCR engine. Unsupported languages should not be assumed to fall back automatically.

OCR documentation: [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)

### 5.2 Layout detection

Layout detection identifies semantic regions with bounding boxes and classes such as `TEXT`, `TABLE`, `PICTURE`, and `SECTION_HEADER`.

The model catalog documents the Heron and Egret object-detection families, including differing model sizes and inference characteristics. `LayoutObjectDetectionOptions` selects presets such as `layout_heron_default` or `layout_egret_large`.

This stage addresses where a document element is and what kind of element it appears to be. It does not, by itself, prove what every piece of content says or how it should be interpreted.

Useful consequences include isolating table crops, filtering page furniture, associating text with figures, and improving multi-column reading order.

Version distinction: `LayoutOptions` is deprecated in favor of `LayoutObjectDetectionOptions`. The older `docling-layout-v2` model is no longer supported as a native selectable layout model; older configuration paths may be translated or fall back to Heron.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 5.3 Table structure recognition

Table recognition is one of Docling's most consequential advanced features because tables are often damaged by simplistic PDF-to-Markdown conversion.

TableFormer reconstructs table rows, columns, cell membership, and spanning relationships. Its two principal operating modes are `FAST` and `ACCURATE`.

`TableStructureOptions` also controls cell matching. With `do_cell_matching=True`, predicted cell structure is reconciled against text cells from the PDF backend. Disabling matching can be useful where geometric alignment is misleading, although it changes how text is associated with cells.

A different supported approach uses the Granite Vision model family to generate structured table representations such as OTSL.

The resulting `TableData` can preserve `TableCell` structure, including `row_span` and `col_span`, rather than reducing everything immediately to a flat text table.

This distinction matters for header hierarchies, merged cells, financial statements, and tables where a cell's position carries meaning.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Model catalog: [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)

### 5.4 Heading hierarchy and reading order

An easily overlooked limitation is that detecting a heading does not automatically determine its correct depth.

The standard PDF layout model identifies section headers, but its default output does not establish a full heading hierarchy: detected headings can be emitted at level one.

Docling provides an opt-in heading hierarchy recovery mechanism, configured through `HeadingHierarchyOptions`. It uses combinations of PDF bookmarks, heading numbering, and visual style information to infer relative heading levels.

This has consequences well beyond Markdown formatting. Correct heading depth improves section grouping, navigation, and chunk metadata. It can also prevent downstream systems from incorrectly treating every detected heading as a top-level document section.

The inference remains heuristic where source semantics are ambiguous; it should not be mistaken for a guaranteed recovery of author-intended hierarchy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Heading levels: [https://docling-project.github.io/docling/usage/heading_levels/](https://docling-project.github.io/docling/usage/heading_levels/?utm_source=chatgpt.com)

### 5.5 Native PDF forms and page rules

Docling can extract interactive PDF form fields through `extract_form_fields=True`. This includes native field data such as AcroForm entries, with typed field/value items and geometric associations.

The distinction is between an actual PDF widget and a visually similar field printed or scanned onto a page. Native form extraction exploits information already present in the PDF; it is not general-purpose scanned-form understanding.

The advanced options also expose support for visible page rules as evidence for reading-order reconstruction, as well as low-level parsed-page retention when more detailed PDF structures are required.

These capabilities can replace specialized extraction logic for some document classes, but require the source PDF to contain the relevant structures.

Source: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling

## 6. Vision-language models and semantic enrichment

### 6.1 VLM model selection

Docling's VLM support spans several model families and execution mechanisms.

The model catalog includes GraniteDocling and SmolDocling, plus larger general-purpose or document-focused VLMs. Preset capabilities and output grammars vary: some generate DocTags, others Markdown, HTML, or specialized native outputs.

Supported inference arrangements include local Transformers-based models, MLX on supported Apple hardware, vLLM, and compatible remote model APIs such as Ollama, LM Studio, or OpenAI-style endpoints.

Crucially, model selection and inference-engine selection are different decisions. A model may be available only through specific runtimes, or a particular output grammar may be supported on one model path but not another.

DocTags-oriented models attempt to emit structured document tokens that can be mapped back into the document representation. Markdown-generating models may be simpler to integrate with text consumers but can expose fewer explicit structural relationships.

The model catalog is therefore the more reliable capability reference than assuming every VLM can be substituted into every pipeline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Vision models: [https://docling-project.github.io/docling/usage/vision_models/](https://docling-project.github.io/docling/usage/vision_models/?utm_source=chatgpt.com)

Model/engine compatibility: [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)

### 6.2 Enrichment stages

Docling supports optional enrichment operations over identified document elements.

| Enrichment             | Result                                                               | Important qualification                                  |
| ---------------------- | -------------------------------------------------------------------- | -------------------------------------------------------- |
| Code understanding     | Code text and language recognition                                   | Depends on detected code regions and recognition quality |
| Formula understanding  | Mathematical expression recognition, including LaTeX-oriented output | Visual recognition can misinterpret notation             |
| Picture classification | Figure categories such as charts, diagrams or photographs            | A category is not a complete semantic description        |
| Picture description    | Natural-language figure interpretations from a VLM                   | Generative output can omit or invent details             |
| Chart extraction       | Structured interpretations of chart content                          | Support depends on model, pipeline and source type       |

Several enrichments are disabled by default. Their compute cost, inference model requirements, and resulting metadata are separate from the base document parsing operation.

This distinction is useful because document conversion need not involve expensive semantic interpretation of every image. For example, a document can preserve figures and their source locations without automatically generating captions for them.

Chart understanding has two distinct mechanisms. Native Office chart objects can supply explicit series data, while image-based charts require visual interpretation. These mechanisms can yield similar-looking outputs but have different evidentiary strength.

The image-based path is an inference, not a recovery of original numerical chart data with guaranteed precision.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Enrichments: [https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)

### 6.3 Structured information extraction

Docling also includes a `DocumentExtractor` interface for extracting specified fields rather than converting an entire document into prose or markup.

Its documented extraction example accepts field templates expressed as strings, dictionaries, or Pydantic models. Outputs are organized by page, with extracted data, raw generated content, and error information.

This is a significant conceptual extension: the desired output can be a domain-specific structured object rather than a generic document.

However, the documented implementation is narrower than the general format converter. The official extraction example is focused on PDF and image inputs and requires VLM support. It should be treated as a model-dependent structured-extraction capability, not as a guarantee that every Docling-supported format can be transformed reliably into arbitrary schemas.

Pydantic validation adds schema and type checking; it does not establish that an extracted value is factually correct.

Extraction example: [https://docling-project.github.io/docling/\_generated/examples/extraction/](https://docling-project.github.io/docling/_generated/examples/extraction/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling

## 7. `DoclingDocument`: the central semantic intermediate representation

This is arguably Docling's most strategically important component.

`DoclingDocument`, defined in `docling_core.types.doc`, is a Pydantic-based structure that can contain typed content, parent-child relationships, reading order, page geometry, provenance, and annotations.

### 7.1 Content and structure are represented separately

The data model distinguishes content collections from structural organization.

| Data-model component | Semantic role                                                        |
| -------------------- | -------------------------------------------------------------------- |
| `texts`              | Paragraphs, headings, formulas and other text-bearing items          |
| `tables`             | Tables with structured table data                                    |
| `pictures`           | Figures, illustrations and other picture objects                     |
| `key_value_items`    | Structured key/value document elements                               |
| `body`               | Logical hierarchy of main document content                           |
| `furniture`          | Content outside the main body, such as headers and footers           |
| `groups`             | Non-content nodes grouping other items, including lists and sections |
| `pages`              | Page-level geometry and available page/image metadata                |

Content items and structural nodes reference one another through JSON-pointer-style links.

The order of children in the `body` tree expresses reading order. This is important: reading order is not simply the order of items in `texts` or a sort by page coordinates.

Content layers also allow some material, such as notes or page furniture, to be distinguished from the main narrative. That is materially richer than an unannotated concatenated text string.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 7.2 Provenance and physical grounding

Document items can carry a list of `ProvenanceItem` entries, relating an extracted element to its source page and bounding box.

This enables operations such as identifying the page where a retrieved passage originated, rendering source highlights, displaying the figure corresponding to a caption, or associating a table with the region from which it was reconstructed.

The provenance model is also a useful boundary between interpretation and evidence. A textual or semantic assertion can be associated with a source region for inspection.

Two important limitations: provenance availability depends on the source format and processing path; and an item's bounding box is evidence of its spatial origin, not proof that its recognized content is correct.

### 7.3 Table, image, and formula semantics

A `TableItem` retains structured table data rather than only a Markdown representation. Cell spans, row/column associations, and table annotations can survive conversion even when a particular serializer cannot express them.

A `PictureItem` can carry captions, annotations, images, and other metadata. Page images and cropped picture images can be retained when generation is enabled, making it possible to preserve a connection between the machine-readable representation and visual evidence.

Formulas are represented within the typed content system, including text-based formula items; optional recognition stages can supply machine-readable mathematical expressions.

### 7.4 Document transformation and construction

`docling-core` provides APIs for constructing and manipulating documents, not merely reading serialized conversion output.

This opens architectural possibilities:

- Normalizing content from different parsers into the same schema.
- Adding custom metadata and relationships after the initial conversion.
- Creating derived documents with selected content elements.
- Applying alternative serializers or chunkers without processing the source again.
- Retaining one canonical structured representation for several downstream outputs.

The value is the reduction in separate, incompatible document representations. A system can operate on typed document items, then choose how those items should appear as text, HTML, chunks, or other output forms.

Document model specification: [https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/?utm_source=chatgpt.com)

Core repository: [https://github.com/docling-project/docling-core](https://github.com/docling-project/docling-core?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling

## 8. Serialization and output fidelity

### 8.1 Multiple outputs from one document model

Docling offers document-level export methods and a more general serializer framework.

Common interfaces include:

```
doc.export_to_markdown()doc.export_to_html()doc.export_to_dict()doc.export_to_doctags()
```

These convenient methods delegate to serializer implementations. The framework also defines serialization behavior for subcomponents such as tables, pictures, lists, text, and inline elements.

This is a meaningful extension mechanism: output policy can be customized without modifying source parsing or duplicating the entire conversion pipeline.

### 8.2 Formats preserve different kinds of information

| Output                  | Strength                                          | Principal information-loss concern                                               |
| ----------------------- | ------------------------------------------------- | -------------------------------------------------------------------------------- |
| Docling JSON            | Detailed typed representation and relationships   | Only preserves what was reconstructed or recorded in the model                   |
| Markdown                | Readable text, headings and basic tables          | Limited representation of complex tables, geometry and object relationships      |
| HTML                    | Richer rendering semantics, including table spans | Not equivalent to the full provenance-aware model                                |
| DocTags                 | Model-oriented structured token representation    | Depends on the supported token vocabulary and serializer                         |
| DocLang                 | Structured document interchange                   | Different representational conventions from native Docling JSON                  |
| Plain text              | Broad compatibility                               | Loses most layout, structure and visual information                              |
| LaTeX / related outputs | Useful for some scientific-content workflows      | Formatting and mathematical fidelity depend on extraction and serializer support |

The official documentation is explicit that certain serialization formats cannot directly express all table cell spans. JSON, HTML, DocTags, and DocLang can preserve structures that may be flattened or approximated in Markdown or LaTeX.

The expression lossless JSON means lossless with respect to the `DoclingDocument` representation. It does not mean conversion from an arbitrary PDF into Docling JSON and back will reproduce the original source document or its entire layout.

### 8.3 Image serialization modes

Docling supports strategies for image references including embedded content, external references, and placeholders, depending on the serializer.

That choice affects document portability, payload size, and whether visual grounding remains accessible to downstream consumers.

When the use case requires source screenshots or figure retrieval, the image-generation options and serializer's image-reference mode must be considered together.

Serialization: [https://docling-project.github.io/docling/concepts/serialization/](https://docling-project.github.io/docling/concepts/serialization/?utm_source=chatgpt.com)

Figure extraction examples: [https://docling-project.github.io/docling/examples/](https://docling-project.github.io/docling/examples/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

## 9. Native chunking: document semantics before token limits

Docling's chunkers work directly on `DoclingDocument`. This is a substantial distinction from splitting the text of an exported Markdown document.

### 9.1 Three chunking strategies

| Chunker                 | Primary organizing principle                     | Distinctive capability                                            |
| ----------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| `HierarchicalChunker`   | Document element and hierarchy                   | Preserves headings, captions and element associations             |
| `HybridChunker`         | Hierarchy followed by tokenizer-aware refinement | Splits oversized chunks and merges compatible neighboring chunks  |
| `LineBasedTokenChunker` | Line boundaries plus token limits                | Preserves lines in code, tables, logs and similar structured text |

The common `BaseChunker` contract provides `chunk(document)` and `contextualize(chunk)`.

The separation is useful because a chunk's stored text and its contextualized text need not be the same. Section headings and captions can be added for retrieval or prompting without overwriting the original content representation.

### 9.2 Hierarchical chunking

`HierarchicalChunker` creates chunks based on document elements and their relationships. By default, it can merge list items rather than splitting every bullet into an isolated unit.

The result can include metadata identifying section headers, captions, and source document items.

This avoids a common problem with generic text splitters: a passage may be syntactically intact but semantically disconnected from the heading or table to which it belongs.

### 9.3 Hybrid chunking

`HybridChunker` starts with hierarchical chunks, then adjusts them against a tokenizer's token budget.

Its essential behavior consists of two passes:

1. Split chunks that exceed the permitted token size.
2. Merge successive small chunks when their structural context is compatible.

The merge behavior can be disabled using `merge_peers=False`.

The tokenizer should correspond to the downstream embedding or language model when token limits matter. The relevant interfaces can use tokenizers from the Hugging Face or `tiktoken` ecosystems with the appropriate `docling-core` extras.

A particularly useful advanced feature is repeated table headers. When a table spans several chunks, the header can be repeated to retain column meaning. `omit_header_on_overflow` helps when repeating a wide header would otherwise cause a chunk to exceed its token budget.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 9.4 Line-based chunking

`LineBasedTokenChunker` is designed to preserve entire lines where possible, only splitting a line if that line alone exceeds the token limit.

It can repeat a prefix, such as a table header, and supports overflow behavior when that prefix makes a line too large.

This is particularly relevant for code blocks, logs, structured records, and tabular material where arbitrary token splits can destroy local meaning.

### 9.5 Provenance-aware RAG

The most important interaction is between native chunking and the document model.

A chunk can retain references to the original `DocItem` objects and therefore inherit source-page and bounding-box information. A retrieval system can use the contextualized chunk for indexing while keeping the original item references for citation or visual inspection.

The pattern is:

Document structure → semantically informed chunk → contextualized retrieval text → original document item → source region.

That is substantially more informative than storing only a flat text string and a document filename.

However, Docling chunkers do not themselves supply an embedding model, vector database, retrieval optimizer, or semantic relevance guarantees. Those capabilities belong to downstream systems. Image content also requires appropriate visual or textual representations to become searchable through a text-only index.

Chunking: [https://docling-project.github.io/docling/concepts/chunking/](https://docling-project.github.io/docling/concepts/chunking/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

## 10. Audio and video as document inputs

Docling is not exclusively a text-and-page framework.

Its media pipelines can transform recordings and videos into the same broader document interchange model, with timed transcript information and, for video, image content associated with the timeline.

### 10.1 Audio processing

Audio conversion uses automatic speech recognition (ASR). The documented model and backend options include Whisper-based paths, native PyTorch execution, Apple MLX variants, and specialized backend options.

Outputs can include text segments with timestamps and be exported to formats such as WebVTT.

This gives transcripts access to the same general conversion and serialization ecosystem used for other document types.

The important distinction is that transcription is not the same as semantic interpretation of a meeting or conversation. Speaker identification, diarization, entity extraction, and summarization are separate capabilities or subsequent operations.

### 10.2 Video processing

Video conversion combines transcription of the audio track with selected visual frames.

The documented video pipeline supports fixed-interval and scene-oriented frame sampling. Depending on configuration and optional components, it can also provide speaker diarization.

This can support time-grounded retrieval over recordings without creating a bespoke media-to-document representation.

It is not a guarantee of complete temporal understanding: frame sampling can miss events occurring between samples, and the document model may represent only selected visual evidence rather than all video frames.

Media processing may require `ffmpeg`, ASR extras, specialized native dependencies, and model checkpoints.

Audio/video documentation: [https://docling-project.github.io/docling/usage/processing_audio_media/](https://docling-project.github.io/docling/usage/processing_audio_media/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling

## 11. Extension mechanisms and integration boundaries

### 11.1 Custom backends and pipelines

`DocumentConverter` supports per-format `FormatOption` configuration. A format option can select a backend, pipeline class, and associated pipeline options.

This supports specialization without rebuilding the entire conversion interface. For example, distinct PDF conversion paths can use different pipelines while other formats continue to use their default backends.

The extension boundary is significant: replacing a backend changes how native source structures are interpreted, whereas replacing a pipeline or inference stage changes how content is reconstructed or enriched.

### 11.2 External model plugins

Docling documents a plugin system for OCR, layout detection, and table-structure engines.

The plugin mechanism uses factories that allow external implementations and their options to be selected through supported configuration surfaces.

External plugins are not enabled by default. `PdfPipelineOptions.allow_external_plugins=True` explicitly permits external plugin loading. The CLI also exposes corresponding controls.

This is a useful trust boundary: choosing an alternative model distributed as an installed third-party plugin has different execution implications from choosing a bundled model preset.

Plugins: [https://docling-project.github.io/docling/concepts/plugins/](https://docling-project.github.io/docling/concepts/plugins/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling

### 11.3 API, CLI and remote execution

The Python library and CLI provide local conversion. The separate Docling Serve project exposes conversion through HTTP APIs and supports deployment as a service.

A service architecture can centralize large model weights, GPU utilization, model configuration, and worker lifetimes. Conversely, it introduces network transport, service concurrency, and document data-transfer considerations absent in a purely local process.

Docling also supports remote model inference, but that is distinct from remotely hosting the entire Docling conversion service.

Service: [https://docling-project.github.io/docling/usage/api_server/](https://docling-project.github.io/docling/usage/api_server/?utm_source=chatgpt.com)

CLI: [https://docling-project.github.io/docling/reference/cli/](https://docling-project.github.io/docling/reference/cli/?utm_source=chatgpt.com)

### 11.4 MCP and larger orchestration systems

The separate Docling MCP package exposes conversion functionality through the Model Context Protocol. It allows agents and MCP-compatible clients to invoke document processing, including arrangements backed by a remote Docling Serve instance.

`docling-jobkit` addresses higher-level job execution and ingestion, including source connectors such as S3, Google Drive, and Google Cloud Storage.

`docling-pipelines` is a further companion ecosystem for document processing workflows and integrations. Such orchestration should not be confused with the fundamental `DocumentConverter` API.

MCP: [https://docling-project.github.io/docling/usage/mcp/](https://docling-project.github.io/docling/usage/mcp/?utm_source=chatgpt.com)

Jobkit: [https://docling-project.github.io/docling/usage/jobkit/](https://docling-project.github.io/docling/usage/jobkit/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

### 11.5 External AI and retrieval integrations

The project documents integrations with LangChain, LlamaIndex, Haystack, CrewAI and multiple vector-search ecosystems.

The division of responsibilities is best understood as:

| System responsibility                              | Docling's role                |
| -------------------------------------------------- | ----------------------------- |
| Extract content from source files                  | Primary capability            |
| Infer layout and structured document meaning       | Primary capability            |
| Preserve item hierarchy, locations and annotations | Primary capability            |
| Create document-aware text chunks                  | Native capability             |
| Generate text embeddings                           | Typically external            |
| Store/search vector or hybrid indexes              | External                      |
| Resolve domain entities and ontologies             | External or custom enrichment |
| Execute domain workflows or agent reasoning        | External                      |
| Serve a document-processing API                    | Companion `docling-serve`     |

Docling reduces the need for custom content-ingestion and document-normalization code. It does not eliminate the need for domain semantics, retrieval architecture, provenance policies, or application-level validation.

Integrations: [https://docling-project.github.io/docling/integrations/](https://docling-project.github.io/docling/integrations/?utm_source=chatgpt.com)

## 12. Execution, performance and operational behavior

### 12.1 Hardware and model execution

Supported execution arrangements vary by stage. Docling can use CPU execution, CUDA, Apple MPS/MLX, and other supported inference runtimes, depending on the model and engine.

`AcceleratorOptions` provides controls over device selection and thread counts. Models may have different supported-device matrices, so a device setting that works for layout inference does not automatically establish support for table recognition or OCR.

The strongest general performance advantage of the standard pipeline is selective, specialized computation: native PDF text parsing avoids unnecessary visual recognition where usable text exists, while region-based models can focus inference on layout elements.

The opposite tradeoff is additional coordination among parsers, image renderers, and models.

### 12.2 Batching and threading

Docling provides configuration for model-stage batching and PDF parser threading.

Threaded PDF pipeline options expose batching controls for OCR, layout and table inference. PDF parsing can also have independent parser-thread configuration.

These settings influence different work:

- Parser threads affect native PDF extraction.
- Image resolution affects rendering cost and model input size.
- Stage batch sizes affect model inference efficiency and intermediate-memory pressure.
- Document-level concurrency affects how many conversions and model contexts are active simultaneously.

For GPU inference, sufficiently large batches can improve utilization, but may increase VRAM requirements. For large PDFs, retaining page images and detailed parsed-page state can substantially increase memory use.

The official GPU guide provides workload-specific tuning and benchmarks; its numerical results should not be generalized across arbitrary documents or hardware.

GPU support: [https://docling-project.github.io/docling/usage/gpu/](https://docling-project.github.io/docling/usage/gpu/?utm_source=chatgpt.com)

Advanced performance controls: [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

### 12.3 Models, installation and offline deployment

Docling can download model checkpoints on initial use and can prefetch artifacts through `docling-tools`. It supports configured model artifact locations for offline or controlled environments.

This creates an important distinction between local document execution and zero-network installation. A conversion may run locally after its dependencies and model weights are present, even though the installation or first initialization previously accessed external repositories.

Optional extras can alter the dependency set materially. OCR engines, native format helpers, video processing, VLM runtimes and remote-serving components do not all have the same installation requirements.

Moreover, the Python package's MIT license does not imply that every optional model checkpoint and external inference service shares that license.

Installation: [https://docling-project.github.io/docling/getting_started/installation/](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)

### 12.4 Input and network safety

The converter provides controls for allowed input formats, file-size limits, page-count limits, archive decompression limits, and remote-resource behavior.

`enable_remote_services` is an explicit control relevant to remote model inference and data egress. Separately, some document formats can refer to external resources—such as remote HTML images or XBRL taxonomies—which have their own fetching considerations.

For untrusted inputs, it is useful to distinguish:

Model artifact downloads: acquiring executable model dependencies or weights.

Document source fetching: retrieving a URL or embedded external resource.

Remote inference: transmitting document-derived content or images to a service.

These involve different permissions and data-governance implications.

### 12.5 Resource lifetime

Version 2.145.0 introduces `InputDocument.release()` and fixes handling of page backend references during unloading.

This is particularly relevant for long-lived processes and high-volume conversion workloads, because page objects, rendered images, native parser resources, and model objects have different lifetimes.

It should not be inferred that invoking `release()` unloads every cached model or reclaims all Python and accelerator memory; those are distinct resources.

Release notes: [https://github.com/docling-project/docling/releases/tag/v2.145.0](https://github.com/docling-project/docling/releases/tag/v2.145.0?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

## 13. Diagnostics, confidence and correctness boundaries

### 13.1 Conversion status and partial success

The conversion API exposes statuses and errors, including partial-success and failure cases.

This allows callers to distinguish an input that could not be parsed from one that produced a document with recoverable issues.

Batch conversion can continue despite individual failures when appropriately configured.

That is important because a returned document object alone does not establish complete or correct extraction.

### 13.2 Confidence reporting

Docling exposes conversion confidence through `ConversionResult.confidence`.

Its reported components include layout, OCR, and native text parsing assessments, together with aggregate grades. The documentation identifies `mean_grade` and `low_grade` as useful summary fields.

The numerical scores are informational and their computation can change. In particular, the table confidence component is documented as not yet implemented.

Confidence should therefore be used as a triage signal, not as a calibrated probability that every extracted character, cell, or inferred relationship is correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Confidence: [https://docling-project.github.io/docling/concepts/confidence_scores/](https://docling-project.github.io/docling/concepts/confidence_scores/?utm_source=chatgpt.com)

### 13.3 Important semantic limitations

| Issue                     | Consequence                                                                                  |
| ------------------------- | -------------------------------------------------------------------------------------------- |
| Reading-order ambiguity   | Multi-column layouts and floating elements may be ordered incorrectly                        |
| Source-format variability | Similar-looking content may have different recoverable semantics across PDF, HTML and Office |
| OCR uncertainty           | Recognition errors can propagate into tables, chunks, and extracted fields                   |
| Table misclassification   | Cell boundaries, merged spans and header relationships may require review                    |
| Heading inference         | Visual styling or numbering can suggest a hierarchy different from author intent             |
| Figure interpretation     | Generative captions may omit, distort or invent visual details                               |
| Geometry availability     | Provenance and bounding boxes are not uniformly available for all formats and pipelines      |
| Serialization differences | Markdown or plain text may discard structured information retained in JSON                   |
| Model-specific support    | A capability shown for one VLM or inference engine may not exist for another                 |

A central technical distinction is structural validity versus semantic accuracy. A `DoclingDocument` may validate perfectly against its Pydantic schema while containing incorrectly recognized text or an incorrectly interpreted table.

Similarly, valid JSON matching a requested extraction schema does not imply the values were read accurately from the source.

## 14. API composition examples

The examples below are concise illustrations of documented interfaces; they have not been executed here.

### 14.1 Configured PDF conversion

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.pipeline_options import PdfPipelineOptionsfrom docling.document_converter import DocumentConverter, PdfFormatOptionoptions = PdfPipelineOptions(    do_ocr=True,    do_table_structure=True,    generate_page_images=True,    generate_picture_images=True,    images_scale=2.0,)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(pipeline_options=options)    })result = converter.convert("report.pdf")document = result.documentmarkdown = document.export_to_markdown()structured = document.export_to_dict()
```

The architectural point is that the expensive source interpretation occurs once, after which multiple representations can be derived from the resulting document.

Converter examples: [https://docling-project.github.io/docling/examples/](https://docling-project.github.io/docling/examples/?utm_source=chatgpt.com)

### 14.2 Structure-aware chunking with source traceability

```
from docling.chunking import HybridChunkerchunker = HybridChunker(max_tokens=512)for chunk in chunker.chunk(document):    retrieval_text = chunker.contextualize(chunk)    source_pages = sorted({        provenance.page_no        for item in chunk.meta.doc_items        for provenance in item.prov    })    # retrieval_text: candidate for indexing    # source_pages: original source-page references
```

This demonstrates how native chunking can retain source-document relationships that would be lost if the document were converted immediately to a plain text string.

For precise token control, configure the chunker's tokenizer consistently with the model consuming the chunks.

Chunker API: [https://docling-project.github.io/docling/concepts/chunking/](https://docling-project.github.io/docling/concepts/chunking/?utm_source=chatgpt.com)

## 15. Version-specific observations and capability maturity

The overview targets the released 2.145.0 package. Several distinctions deserve special attention when consulting examples or older tutorials.

| Area                                      | Status and significance                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------------- |
| `DoclingDocument` / conversion pipelines  | Established core capabilities                                                          |
| Heron/Egret layout models                 | Current supported layout model families                                                |
| `LayoutOptions` / old layout-v2 model     | Deprecated or unsupported paths; prefer current `LayoutObjectDetectionOptions`         |
| PDF heading hierarchy recovery            | Released, but opt-in and heuristic                                                     |
| Native PDF form extraction                | Released; applies to actual interactive PDF structures                                 |
| RapidOCR orientation handling             | Added in 2.145.0                                                                       |
| Broken native PDF text replacement        | Recent OCR capability, with configurable behavior                                      |
| `InputDocument.release()`                 | Added in 2.145.0                                                                       |
| `DocumentExtractor`                       | Documented structured extraction with narrower PDF/image examples and VLM requirements |
| Object-detection-based table alternatives | Some approaches remain work in progress                                                |
| Table confidence score                    | Explicitly not yet implemented                                                         |
| Remote model execution                    | Available with supported engines/configuration; not universally interchangeable        |

The latest release also contains correctness fixes involving native VLM inline mathematical notation, spreadsheet numeric formatting, PDF unmapped glyphs, and a range of format-specific parsing cases. These illustrate that preserving semantic fidelity remains an actively evolving area, particularly for complex and unusual source documents.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Version-specific release: [https://github.com/docling-project/docling/releases/tag/v2.145.0](https://github.com/docling-project/docling/releases/tag/v2.145.0?utm_source=chatgpt.com)

## 16. Architectural implications

Docling's major capabilities reinforce one another. The most significant combinations are not isolated features but broader ways of organizing document processing.

Unified representation plus source provenance makes it possible to retain an auditable relationship between extracted knowledge and original document evidence.

Native structure plus token-aware chunking enables retrieval that respects section context, table headers, and source-item boundaries rather than depending entirely on character-count heuristics.

Format-aware backends plus interchangeable processing pipelines permit deterministic parsing where source structure exists and learned visual reconstruction where it does not, without requiring every consumer to implement its own document ingestion logic.

Selective enrichments plus reusable document serialization allow expensive semantic interpretation to be separated from the initial extraction and exposed to different consumers in different forms.

Plugin-based model selection plus service deployment makes it possible to change the inference arrangement without replacing the document model or all downstream integrations.

These capabilities also clarify the natural limitations of the library. Docling provides a strong document understanding and normalization layer; domain-specific ontologies, authoritative record reconciliation, relational data modeling, downstream retrieval, and business logic remain separate concerns.

The greatest general architectural opportunity is therefore not simply faster PDF-to-Markdown conversion. It is the possibility of a single typed, provenance-aware document representation supporting multiple processing and intelligence operations without repeatedly parsing or flattening the original source.

### Primary-source reference map

| Investigation topic               | Primary URL                                                                                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Converter API and result types    | [https://docling-project.github.io/docling/reference/document_converter/](https://docling-project.github.io/docling/reference/document_converter/?utm_source=chatgpt.com) |
| Pipeline and model options        | [https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)     |
| Input/output formats              | [https://docling-project.github.io/docling/usage/supported_formats/](https://docling-project.github.io/docling/usage/supported_formats/?utm_source=chatgpt.com)           |
| Detailed OCR behavior             | [https://docling-project.github.io/docling/concepts/OCR/](https://docling-project.github.io/docling/concepts/OCR/?utm_source=chatgpt.com)                                 |
| Model and engine compatibility    | [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)                   |
| VLM conversion                    | [https://docling-project.github.io/docling/usage/vision_models/](https://docling-project.github.io/docling/usage/vision_models/?utm_source=chatgpt.com)                   |
| Enrichment models                 | [https://docling-project.github.io/docling/usage/enrichments/](https://docling-project.github.io/docling/usage/enrichments/?utm_source=chatgpt.com)                       |
| Document schema                   | [https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/?utm_source=chatgpt.com)       |
| Serialization and table spans     | [https://docling-project.github.io/docling/concepts/serialization/](https://docling-project.github.io/docling/concepts/serialization/?utm_source=chatgpt.com)             |
| Native chunkers                   | [https://docling-project.github.io/docling/concepts/chunking/](https://docling-project.github.io/docling/concepts/chunking/?utm_source=chatgpt.com)                       |
| Plugins and extension factories   | [https://docling-project.github.io/docling/concepts/plugins/](https://docling-project.github.io/docling/concepts/plugins/?utm_source=chatgpt.com)                         |
| Operational and advanced settings | [https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)             |
| Python source and releases        | [https://github.com/docling-project/docling](https://github.com/docling-project/docling?utm_source=chatgpt.com)                                                           |

Overall: Docling is best understood as a modular document-semantic reconstruction framework whose enduring interface is `DoclingDocument`. Its advanced value comes from the combination of native parsing, selectable AI inference, explicit structural relationships, provenance, and reusable transformations—rather than from any individual OCR engine, PDF parser, or export format.

# Docling gap analysis — PDF parsing into structured JSON

Scope: Docling 2.145.0 · Research date: October 31, 2026 · PDF → `DoclingDocument` → JSON only

## 1. Overall assessment

The previous overview covered Docling's principal architecture, but it missed several important capabilities for extracting the richest possible structured JSON from PDFs.

The largest gaps are not additional output formats or integrations. They concern what information Docling can recover, how it represents that information, which processing controls affect structural fidelity, and what is lost before or during JSON serialization.

The most consequential findings from reviewing the official documentation and API reference are:

- The JSON schema is richer than I described. In addition to text, tables, pictures, groups, and page provenance, it includes dedicated form and field structures, typed references, annotations, content layers, and more detailed text and table metadata.
- Some extraction capabilities require explicit activation. Native PDF form fields, heading hierarchy recovery, certain enrichments, and image retention are examples. Default conversion does not mean maximum information extraction.
- Some PDF information never reaches the final `DoclingDocument`. Raw widget metadata, intermediate parser representations, and certain geometric signals can be used during conversion but are not automatically retained in JSON.

The last distinction is particularly important: Docling JSON is a lossless serialization of the constructed Docling document, not necessarily a lossless representation of the original PDF.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



The remainder of this review focuses on gaps worth addressing in a PDF-to-JSON technical reference. Chunking, Markdown, HTML, RAG integrations, media processing, and non-PDF input formats are outside the revised scope.

## 2. Ranked gap map

| Gap in the previous overview                 | Priority    | What was missing for PDF → JSON                                                                                        |
| -------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------- |
| Native PDF form fields                       | High        | `FieldItem`, `FieldValueItem`, field regions, checkboxes/radio buttons, and their relationship to tables               |
| Complete `DoclingDocument` schema            | High        | Typed item variants, reference resolution, content layers, formatting, hyperlinks, and schema/version fields           |
| JSON image and artifact handling             | High        | Embedded versus referenced images, image-generation flags, persistence, and safe reloading                             |
| Detailed table semantics                     | High        | Header flags, row/column offsets, rotation, rich cells, and the distinction between serialized cells and derived grids |
| OCR decision controls                        | High        | Region-based versus full-page OCR, recovery from broken PDF text layers, and implications for native data              |
| Structural reconstruction options            | High        | Heading hierarchy, PDF separators, layout postprocessing, and how they affect document trees                           |
| PDF chart data extraction                    | High        | Optional VLM-based reconstruction of chart data into typed picture metadata                                            |
| Raw PDF data versus normalized document data | High        | Which parser information does not survive into `DoclingDocument` JSON                                                  |
| Conversion diagnostics                       | Medium–high | Conversion status, errors, confidence and timings are not automatically part of the document JSON                      |
| Native text extraction granularity           | Medium      | Word/character/line-level alternatives to model-based semantic reconstruction                                          |
| PDF backend controls                         | Medium      | Parser selection, encrypted PDF support, font-boundary behavior, threading                                             |
| Advanced VLM strategies                      | Medium      | Model-specific structured outputs and multi-pass interpretation of tables or chart regions                             |

This is a gap analysis of the previous write-up, not an assertion that the library lacks these capabilities. Most are available in released Docling; several are configuration-dependent, and some represent information available only from intermediate parser objects.

The highest-value correction is to treat the JSON schema, extraction configuration, and raw-parser retention as three separate design surfaces. A schema may be capable of representing something that the selected pipeline never extracts, while the parser may observe information that the schema never stores.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



## 3. Missing depth: the actual structured JSON model

The original overview described the model conceptually but did not explain enough of its structure to support a consumer of Docling JSON.

### 3.1 Top-level collections

The current `DoclingDocument` schema includes these fields:

| JSON field                     | Meaning                                            |
| ------------------------------ | -------------------------------------------------- |
| `schema_name`, `version`       | Schema identity and compatibility version          |
| `name`, `origin`               | Document identity and available source information |
| `body`, `furniture`            | Root structural nodes                              |
| `groups`                       | Lists, sections and other grouping nodes           |
| `texts`                        | Typed textual items                                |
| `tables`                       | Typed tables                                       |
| `pictures`                     | Figures, images and charts                         |
| `key_value_items`              | Key/value representations                          |
| `form_items`                   | Graph-based form structures                        |
| `field_regions`, `field_items` | Native form-associated regions and fields          |
| `pages`                        | Page-level objects, geometry and optional images   |

The last three collections were inadequately covered previously. Importantly, `form_items` and `field_items` are not synonymous: they represent different structural models.

The schema also performs validation of references, version compatibility, tables, and field structures. Its version is a document-schema version, not necessarily the same number as the installed Docling distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 3.2 Document graph and typed items

The relationships matter as much as the collections.

An item can contain `self_ref`, `parent`, `children`, `label`, `content_layer`, `prov`, and `meta`. References use JSON-pointer-style paths, such as `#/texts/3` or `#/tables/0`.

The text collection supports typed variants including `TitleItem`, `SectionHeaderItem`, `ListItem`, `CodeItem`, `FormulaItem`, `FieldHeadingItem`, and `FieldValueItem`.

Text items can also hold `orig`, `text`, `formatting`, and `hyperlink` information. Formatting supports distinctions such as bold, italic, underline, strikethrough, and subscript/superscript where available. `SectionHeaderItem.level` supplies semantic heading depth.

`content_layer` distinguishes the main body from furniture, background, invisible content and notes where a backend populates those classifications.

JSON processing must resolve the reference graph. The order of `texts[]` is not a substitute for the reading order encoded in the `body` tree. Similarly, the existence of a `meta.language` or `meta.entities` field in a schema does not mean the PDF converter automatically populated it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



### 3.3 Provenance has more than a page and a box

The `ProvenanceItem` structure contains:

| Field                      | Meaning                         |
| -------------------------- | ------------------------------- |
| `page_no`                  | Source page number              |
| `bbox.l`, `.t`, `.r`, `.b` | Bounding-box coordinates        |
| `bbox.coord_origin`        | `TOPLEFT` or `BOTTOMLEFT`       |
| `charspan`                 | Zero-indexed character interval |

Page geometry uses PDF document points, nominally 72 points per inch; it is not inherently measured in pixels.

An item may have multiple provenance entries. Conversely, some generated or aggregated elements may have less precise spans than the schema permits. The presence of `charspan` does not guarantee character-by-character physical alignment for all content.

This suggests distinguishing item-level provenance, table-cell geometry, and native glyph/character geometry: Docling's structured JSON does not necessarily preserve all three at the same granularity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Primary references:

[https://docling-project.github.io/docling/reference/docling_document/](https://docling-project.github.io/docling/reference/docling_document/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/?utm_source=chatgpt.com)

## 4. Major omission: native interactive PDF forms

`PdfPipelineOptions(extract_form_fields=True)` is a richer feature than the previous overview suggested.

When enabled on the standard pipeline with the `docling-parse` backend, Docling can recognize native AcroForm widgets, including text inputs, checkboxes and radio-button choices, and turn them into typed field structures.

It associates the widgets with nearby printed labels using page geometry. The resulting JSON can represent field keys, contextual hints, fillable values and grouped field regions.

For a field inside a recognized table, Docling can use a `RichTableCell` pointing to the structured field object rather than discarding its identity or reducing it to a text string.

That is a significant capability interaction: PDF widget extraction + table structure recognition + typed JSON references.

There are important constraints. PDF internal field names are not the semantic keys used in this representation; Docling derives those from visible text. Scanned or flattened forms do not expose native interactive widgets. Full-page OCR also does not produce these native field items. Moreover, raw widget metadata is not copied wholesale into the final `DoclingDocument`.

`generate_parsed_pages=True` can preserve relevant intermediate parser information in the conversion result, but this is not the same as including that information in `save_as_json()`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Source:

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 5. Major omission: the complete JSON table representation

The previous overview emphasized row spans and column spans. It should have gone further.

A serialized `TableData` contains `table_cells`, `num_rows`, `num_cols`, and `orientation`. Each `TableCell` can contain row/column start and end offsets, `row_span`, `col_span`, text, bounding box, and semantic flags such as `column_header`, `row_header`, `row_section`, and `fillable`.

The structure also admits `RichTableCell` objects with references to separately modeled content.

One subtle distinction is especially relevant: `TableData.grid` is a derived access property, not the canonical serialized field. The JSON schema serializes `table_cells` and their offsets. A consumer can reconstruct the two-dimensional view from those fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



The practical capability differences are:

| Table information                  | JSON representation                 |
| ---------------------------------- | ----------------------------------- |
| Cells and their text               | `table_cells[]`                     |
| Table dimensions                   | `num_rows`, `num_cols`              |
| Merged cells                       | Spans and start/end offsets         |
| Header interpretation              | Row/column header flags             |
| Section or subtotal-like structure | `row_section` flag where recognized |
| Rotated tables                     | `orientation`                       |
| Cell physical grounding            | Cell-level `bbox`                   |
| Structured nested content          | `RichTableCell` references          |
| Captions, footnotes and references | Relationships on `TableItem`        |

Three processing choices affect the resulting JSON: TableFormer `FAST` versus `ACCURATE`; `do_cell_matching`, which governs matching inferred structure to native PDF text cells; and alternative VLM-based table recognition.

Header flags are inferred semantic labels, not guaranteed native PDF table-header declarations. The distinction becomes especially important for irregular financial and scientific tables.

Source:

[https://docling-project.github.io/docling/reference/docling_document/](https://docling-project.github.io/docling/reference/docling_document/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

## 6. JSON images: three distinct concerns

The earlier overview did not sufficiently separate image generation, image retention, and JSON storage.

### 6.1 Images must be attached before they can be serialized

Relevant PDF pipeline settings include `generate_page_images`, `generate_picture_images`, `generate_table_images`, and `images_scale`.

These govern whether rendered page images, figure crops, or table images are retained in the structured document. The resulting image references can appear on page, picture, and table objects.

`images_scale` influences rendering resolution and resource consumption. It does not improve the precision of already-extracted vector text.

### 6.2 JSON image strategies

The `DoclingDocument.save_as_json()` method provides `image_mode` using `ImageRefMode`:

| Mode          | Behavior                                                     | Consequence                                                    |
| ------------- | ------------------------------------------------------------ | -------------------------------------------------------------- |
| `EMBEDDED`    | Image data stored within the JSON representation             | Self-contained but potentially very large JSON                 |
| `REFERENCED`  | Images stored as separate artifacts and referenced from JSON | Smaller JSON, but external artifacts must accompany it         |
| `PLACEHOLDER` | Images not serialized as usable image payloads               | Preserves some structural context but loses the pixel evidence |

The default for `save_as_json()` is `EMBEDDED`. It also exposes `artifacts_dir`, `coord_precision`, `confid_precision`, and ordinary JSON-writing controls.

`export_to_dict()` provides the in-memory JSON-compatible dictionary with its own serialization controls, but not the same image-artifact writing interface.

For JSON-only processing, this difference is more relevant than the serializers for other output formats.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



### 6.3 Reloading referenced images

Docling deliberately does not load arbitrary local file references from untrusted JSON by default.

`DoclingDocument.load_from_json(..., allow_local_images=True)` is available for trusted documents. The `DocumentConverter` JSON backend has a separate explicit local-fetch configuration.

This means a structurally valid JSON file can be loaded while its separately referenced images are unavailable. A downstream parser should distinguish a missing image payload from an absent picture object.

Source:

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/reference/docling_document/](https://docling-project.github.io/docling/reference/docling_document/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

## 7. Missing PDF extraction and reconstruction controls

### 7.1 OCR operating modes and broken text layers

The previous overview identified OCR engines, but understated the importance of how OCR is applied.

`OcrOptions.mode` supports `default`, `full_page`, `layout_regions`, and `pdf_aware_layout_regions`. These represent different policies for presenting page regions to the recognizer.

Another important feature is `replace_broken_text_layer=True`, available through OCR options. It identifies pages whose native text layer contains likely character-mapping corruption and uses OCR instead. Other pages can retain their original native text.

This is different from full-page OCR applied indiscriminately.

The detector is heuristic. It can recognize certain encoding failures and nonsensical glyph mappings, but it cannot generally detect plausible-looking text containing the wrong letters. For those cases, explicit full-page OCR may still be necessary.

The choice matters for JSON because it changes the recognized `text`, its physical grounding, and potentially whether native PDF widgets can be recovered.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 7.2 Heading hierarchy is more configurable than described

The previously mentioned `HeadingHierarchyOptions` has useful individual controls: `use_bookmarks`, `use_numbering`, `use_style`, `use_font_style`, `numbering_schemes`, `max_level`, and `bookmark_match_threshold`.

The stage rewrites `SectionHeaderItem.level`, not merely a Markdown heading prefix. It can also promote a list item that was misclassified as a heading when a bookmark confidently identifies it.

It is disabled by default. The output can therefore contain flattened heading levels even when the PDF has a meaningful outline.

Source: [https://docling-project.github.io/docling/usage/heading_levels/](https://docling-project.github.io/docling/usage/heading_levels/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.3 Layout postprocessing and reading-order controls

The layout system exposes controls such as `create_orphan_clusters`, `keep_empty_clusters`, and `skip_cell_assignment`. These affect whether unassigned text becomes its own cluster and how detected content is associated with inferred structures.

That can affect completeness and grouping in the resulting JSON, not just visual layout accuracy.

The `use_reading_order_separators` option is particularly noteworthy. It is enabled by default and permits visible PDF vector rules to influence reading order. Yet those separator lines are not themselves added to the final `DoclingDocument`.

This is a concrete example of parsing evidence that influences semantic output while disappearing from that output.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 7.4 Source text versus learned reconstruction

`force_backend_text` allows PDF-native extracted text to take precedence in relevant conversion paths.

The distinction is useful where a PDF has reliable programmatic text and learned reconstruction might introduce textual differences. It does not eliminate the separate need for layout inference if the desired JSON contains semantic organization.

`NativePdfPipeline` offers another, more substantial distinction: its `text_cell_unit` can produce line-, word-, or character-granularity text items where supported by the backend.

The native pipeline can therefore provide a finer-grained geometric text representation, while the standard pipeline supplies a more semantic document representation. These are different outputs, not simply two quality levels of the same parser.

Sources:

[https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/usage/advanced_options/](https://docling-project.github.io/docling/usage/advanced_options/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1

## 8. Missing structured figure and chart capabilities

The original overview mentioned picture descriptions and chart understanding, but did not sufficiently describe their JSON-native structure.

### 8.1 Chart data, not just captions

`do_chart_extraction=True` activates an optional VLM-based chart-extraction stage, also enabling picture classification. The documented stage can turn supported bar, pie, and line charts into structured tabular information.

`ChartExtractionVlmEngineOptions` supports model presets including Granite Vision v4 and controls such as `chart2csv`, `chart2summary`, and `chart2code`.

This is particularly relevant for PDF-origin charts, which ordinarily lack the native underlying series data available in an editable Office chart object.

However, the extracted numbers are visual estimates or model interpretations and should not be treated as recovered source-data values with guaranteed precision.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 8.2 `PictureMeta` is substantially richer

The current schema exposes metadata families including `description`, `classification`, `tabular_chart`, `molecule`, and `code`, alongside more general summary, language, entity, keyword, and topic fields.

It also has typed chart representations for line, bar, stacked bar, pie, scatter, and tabular charts.

The previous overview did not explain the newer `PictureItem.meta` representation or distinguish it from the older `annotations` list. A migration validator exists for legacy annotations, so these fields should not be treated as two independent stores of entirely different picture content.

Again, this is representational capacity, not evidence that every PDF conversion populates every metadata family.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 8.3 More sophisticated VLM conversion paths

Docling's current model catalog also describes specialized document parsers such as Nemotron Parse and MinerU's two-step recognition approach.

Of particular interest, Nemotron Parse 3.5 provides optional multi-pass processing that can revisit table and chart regions after a page-level parse. MinerU's supported preset performs page-level layout detection followed by region-specific recognition.

These may produce structured document content through different mechanisms from the conventional PDF pipeline.

The presence of a model preset does not guarantee superior JSON fidelity. Each model has different recognition coverage, model runtime requirements, and limitations—for example, the documented MinerU preset does not perform cross-page table merging.

Source: [https://docling-project.github.io/docling/usage/model_catalog/](https://docling-project.github.io/docling/usage/model_catalog/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



## 9. Additional gaps: table-recognition alternatives and cross-page structure

### 9.1 TableFormer V2 was missing

The previous overview described TableFormer's `FAST` and `ACCURATE` modes but did not distinguish TableFormer V2, which is separately selectable.

`TableStructureV2Options` enables the newer model. Its architecture predicts table structure as OTSL tokens together with bounding boxes for individual cells. The resulting predictions are converted into the same `TableItem` / `TableData` representation.

The model card identifies TableFormer V2 as a preview release. It is not the default; the default remains TableFormer V1.

| Option                     | Status              | Structural JSON implications                                                                 |
| -------------------------- | ------------------- | -------------------------------------------------------------------------------------------- |
| TableFormer V1, `ACCURATE` | Established default | General table structure recognition                                                          |
| TableFormer V1, `FAST`     | Released            | Lower-cost alternative with an accuracy tradeoff                                             |
| TableFormer V2             | Preview             | Alternative cell and structure predictions, with compatibility and quality subject to change |
| VLM table recognition      | Model-dependent     | Generated table structure, with model-specific recognition behavior                          |

V2 retains the `do_cell_matching` option. The model's documentation specifically notes that disabling matching can help when native PDF text cells span multiple predicted columns.

This is a meaningful omission because choosing the table-recognition model changes the actual `TableData` stored in JSON, not merely presentation or serialization. But there is insufficient evidence to establish that V2 is universally more accurate.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face+1



Primary sources:

[https://huggingface.co/docling-project/TableFormerV2](https://huggingface.co/docling-project/TableFormerV2?utm_source=chatgpt.com)

[https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

### 9.2 Cross-page table continuation is a significant unresolved limitation

This is perhaps the most important limitation omitted from the original overview.

Docling has documented cases in which a single logical table spanning several PDF pages becomes multiple `TableItem` objects. The issue is reported for both the standard and VLM pipelines.

The resulting JSON may contain individually well-formed table objects while failing to represent their logical continuity. Consequences include repeated or incorrect headers, split records, and rows incorrectly interpreted as header rows.

The distinction from ordinary text is important: Docling's reading-order implementation can merge certain text elements across page boundaries while treating tables as separate objects.

An upstream proposal dated October 17, 2026 describes opt-in merging of continued tables. That proposal should not be treated as released functionality in 2.145.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Issue and proposal:

[https://github.com/docling-project/docling/issues/2976](https://github.com/docling-project/docling/issues/2976?utm_source=chatgpt.com)

The JSON schema can support an item with multiple provenance regions; the existence of that representational capability does not imply cross-page table reconstruction is automatically performed.

### 9.3 Another missing distinction: detecting versus preserving table content

There are three separate quality questions that should be investigated independently.

| Quality dimension        | Example failure                                                       |
| ------------------------ | --------------------------------------------------------------------- |
| Table detection          | A borderless table is recognized as ordinary paragraphs               |
| Structure reconstruction | Column boundaries, merged cells or header relationships are wrong     |
| Text-to-cell association | A correctly inferred grid is populated with text from the wrong cells |

Changing `do_cell_matching` primarily addresses the third concern. Switching TableFormer models affects structure reconstruction. Changing the layout model or using another pipeline may affect whether the table region is detected at all.

No single accuracy measure adequately captures all three.

## 10. Additional gap: what the PDF parser knows but Docling JSON does not preserve

### 10.1 Authored PDF semantics are not fully imported

The previous overview could have conveyed a misleading impression that Docling systematically preserves whatever semantics already exist in a PDF.

In reality, PDF documents can contain two different classes of structural information:

Visually inferred semantics include headings, paragraphs, tables, and reading order reconstructed from positioned text, geometry and rendered pages.

Authored PDF semantics may include a tagged structure tree, accessibility roles, language declarations, alternative text, link destinations, bookmarks, and table-header associations.

Docling currently exploits some authored PDF information—bookmarks can inform heading hierarchy, for example—but complete tagged-PDF semantic ingestion should not be assumed.

An upstream September 2026 proposal explicitly describes importing the PDF/UA-2 structure tree as authoritative, including heading levels, table relationships, alternative text, language, links and footnotes. It is labeled a proposal for discussion, not a completed stable feature.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source:

[https://github.com/docling-project/docling/issues/4146](https://github.com/docling-project/docling/issues/4146?utm_source=chatgpt.com)

This is consequential for born-digital and accessibility-tagged PDFs. Their native structural semantics may contain information more precise than visual inference, yet not all of it necessarily reaches `DoclingDocument`.

### 10.2 PDF metadata, bookmarks and annotation structures

The underlying `docling-parse` package exposes additional native PDF information, including document metadata, XML metadata, document outline/bookmarks and annotation-related structures.

For example, its `PdfDocument` interface provides `get_annotations()` and `get_table_of_contents()`. The documented annotation structure includes form information, language, metadata XML and the table of contents.

These are capabilities of the underlying parser, not evidence that Docling's standard JSON output includes all of those native structures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



The distinction matters for such data as:

| PDF information                 | Standard JSON consideration                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------------------------ |
| Document outline/bookmarks      | Can inform heading hierarchy, but the complete authored outline is not guaranteed to be retained |
| PDF title, author, subject, XMP | Not equivalent to the limited `DoclingDocument.origin` fields                                    |
| Interactive form widgets        | Can become normalized field objects, but raw widget dictionaries are not fully retained          |
| Annotations and comments        | Do not assume a complete native PDF annotation inventory                                         |
| Links and destinations          | Text-item hyperlinks may exist, but full native PDF link structures are a separate concern       |
| Vector paths and rules          | May influence reading order without appearing as explicit graphic objects in final JSON          |
| Font/glyph details              | Used in parsing; generally not a complete character/font trace in the semantic JSON              |

A major architectural implication follows: Docling's JSON is a semantic document representation, not a comprehensive PDF object model.

If the desired JSON must contain both interpreted document semantics and detailed native PDF objects, those are distinct information sources. The available evidence does not establish that Docling alone combines them into a single complete standard schema without additional transformation.

Parser source:

[https://github.com/docling-project/docling-parse/blob/main/docling_parse/pdf_parser.py](https://github.com/docling-project/docling-parse/blob/main/docling_parse/pdf_parser.py?utm_source=chatgpt.com)

### 10.3 Intermediate parsed pages

`PdfPipelineOptions.generate_parsed_pages=True` retains richer page-level parser data after assembly.

This is different from enabling more detail in `DoclingDocument.save_as_json()`.

The relevant distinction is:

| Object                         | Information retained                                              |
| ------------------------------ | ----------------------------------------------------------------- |
| `ConversionResult.document`    | Normalized semantic document                                      |
| `ConversionResult.pages`       | Page-stage data and intermediate parser information when retained |
| `docling-parse` native objects | Lower-level PDF-specific objects and metadata                     |
| Saved `DoclingDocument` JSON   | Serializable fields of the normalized semantic document           |

Retaining parsed pages increases memory consumption. Their availability in the conversion result does not automatically place their internal content into the document's JSON.

Source:

[https://docling-project.github.io/docling/reference/pipeline_options/](https://docling-project.github.io/docling/reference/pipeline_options/?utm_source=chatgpt.com)

## 11. Missing low-level PDF backend controls

Several controls were absent from the earlier discussion and are relevant to extraction correctness or memory usage.

| Control                               | Meaning                                             | When consequential                                   |
| ------------------------------------- | --------------------------------------------------- | ---------------------------------------------------- |
| `PdfBackendOptions.password`          | Supplies a password for supported encrypted PDFs    | Protected documents                                  |
| `enforce_same_font`                   | Determines whether text cells split at font changes | Diacritics and mixed-font text                       |
| `include_bitmap_images`               | Decodes native embedded bitmap image bytes          | Recovering source bitmaps rather than rendered crops |
| `parser_threads`                      | Controls PDF backend parsing parallelism            | Throughput on multi-page inputs                      |
| `max_concurrent_results`              | Bounds decoded-page buffering ahead of the pipeline | Peak memory on large PDFs                            |
| `render_pages`                        | Controls page rendering during threaded parsing     | Parsing paths that do not require page images        |
| `render_scale`                        | Sets parser-time page-image resolution              | Avoiding unnecessary rerendering                     |
| `release_native_memory_every_n_pages` | Periodic release of native parser memory            | Long documents and sustained workloads               |

One particularly non-obvious example is `enforce_same_font`. Its default is `True`, so the parser splits text cells where fonts change. Some PDFs use separate fonts for a base glyph and its diacritical mark; disabling this behavior can keep them in the same text cell.

Another is `max_concurrent_results`: reducing it can limit peak memory without changing the semantic output format, because each buffered page may carry both decoded content and a rendered image.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



`render_pages=False` is not a general optimization for the standard visual-analysis pipeline. Stages that need rasterized page images still require those images to be available.

The controls are defined in the 2.145.0 tagged source:

[https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py](https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py?utm_source=chatgpt.com)

Correction to §6 above: the current pipeline API marks `generate_table_images` as deprecated. Although the field remains present, it should not be presented as a preferred new configuration mechanism. `generate_page_images` and `generate_picture_images` are the more relevant retained-image settings, with table-image behavior checked against the selected model/pipeline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



## 12. A further important gap: conversion diagnostics are outside document JSON

The original overview described `ConversionResult` but did not emphasize its significance for the integrity of a JSON-only output.

`ConversionResult` carries information beyond the document itself:

| Conversion-result field | Significance                                            |
| ----------------------- | ------------------------------------------------------- |
| `status`                | Success, partial success, failure and processing states |
| `errors`                | Recorded failures during conversion                     |
| `confidence`            | Layout, OCR and native-text quality assessments         |
| `timings`               | Pipeline operation timings                              |
| `pages`                 | Per-page and potentially retained intermediate data     |
| `version`               | Conversion software version                             |
| `timestamp`             | Conversion metadata                                     |
| `document`              | The resulting `DoclingDocument`                         |

`has_parse_errors()`, `has_inference_errors()`, and `has_timeout_errors()` permit classification of errors.

Saving `result.document` as JSON does not automatically preserve the conversion report. This means two JSON documents might validate against the same schema even though one was created from a clean conversion and the other from a partially successful conversion.

Docling also exposes `ConversionResult.save(filename=...)`, which serializes the full `ConversionAssets` representation to JSON. That is a different JSON structure from `DoclingDocument.save_as_json()`, not a drop-in equivalent.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



API reference:

[https://docling-project.github.io/docling/reference/document_converter/](https://docling-project.github.io/docling/reference/document_converter/?utm_source=chatgpt.com)

### 12.1 Quality grades versus extraction correctness

Docling reports `layout_score`, `ocr_score`, `parse_score`, and `table_score` in its confidence model. However, the documentation explicitly notes that the table score is not yet implemented, and recommends treating the aggregate `mean_grade` and `low_grade` as assessment signals.

These metrics cannot establish exact cell-level correctness, faithful formula recognition, or complete extraction of a source document.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Source:

[https://docling-project.github.io/docling/concepts/confidence_scores/](https://docling-project.github.io/docling/concepts/confidence_scores/?utm_source=chatgpt.com)

### 12.2 Schema validation remains useful but has a different purpose

`DoclingDocument` exposes `validate_document()` and `validate_tree()`, as well as Pydantic serialization and validation capabilities.

These are relevant for checking structural consistency and reference integrity after transformations or reloads. They do not substitute for checking OCR accuracy, table quality, or content completeness.

The correct conceptual distinction is:

Conversion health → document-model consistency → source-content fidelity.

Each answers a different question.

## 13. A PDF-to-JSON configuration example

For illustration, this combines several of the previously underemphasized capabilities into a single Python conversion path.

```
from docling.datamodel.base_models import InputFormat, ConversionStatusfrom docling.datamodel.pipeline_options import (    HeadingHierarchyOptions,    PdfPipelineOptions,)from docling.document_converter import DocumentConverter, PdfFormatOptionfrom docling_core.types.doc import ImageRefModeoptions = PdfPipelineOptions(    do_ocr=True,    do_table_structure=True,    # Native PDF form widgets, where present    extract_form_fields=True,    # Recover semantic heading depth    heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),    # Retain visual evidence in the document    generate_page_images=True,    generate_picture_images=True,    images_scale=2.0,)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(            pipeline_options=options,        ),    },)result = converter.convert(    "document.pdf",    raises_on_error=False,)
```

This is a demonstration of composition, not a universal maximum-fidelity preset.

It intentionally does not activate every VLM enrichment, does not replace the default table model with experimental TableFormer V2, and does not force full-page OCR. It also makes embedded JSON substantially larger by retaining images.

The capability boundaries are important: native form widgets require suitable PDFs and the relevant backend; page images are not the same as native bitmap extraction; and a successful JSON write does not establish that the PDF was exhaustively understood.

## 14. Final assessment: what the revised reference needs to emphasize

For a Docling reference focused exclusively on PDF → structured JSON, the material can be organized much more effectively than in my original broad library overview.

| Capability cluster     | Importance   | Key technical concepts                                                                      |
| ---------------------- | ------------ | ------------------------------------------------------------------------------------------- |
| Semantic JSON contract | Foundational | Collections, typed items, hierarchy, references, validation, provenance and schema versions |
| PDF interpretation     | Foundational | Native text parsing, OCR, layout recognition, reading order and heading inference           |
| Complex structures     | Foundational | Tables, captions, formulas, forms, figures and chart data                                   |
| Fidelity controls      | High         | OCR policy, text-cell matching, model choice, bitmap handling and geometry                  |
| Retention boundaries   | High         | Normalized JSON versus raw parsed pages, PDF metadata and native objects                    |
| Quality assurance      | High         | Conversion status, confidence, validation, failure classification and provenance            |
| Alternative models     | Conditional  | TableFormer V2 preview, VLM parsers and specialized enrichment models                       |
| Execution efficiency   | Supporting   | Parser concurrency, batching, rendering and native-memory management                        |

The principal conclusion of this gap analysis is that the biggest missing dimension was not another parsing model; it was the relationship between PDF information, the semantic reconstruction pipeline, and the exact structured JSON that survives conversion.

Three details are especially consequential for a JSON-only consumer: `DoclingDocument` is a typed reference graph rather than a flat collection of extracted objects; model and pipeline configuration can materially change which graph structures exist; and detailed native PDF information or conversion diagnostics may remain outside the exported document even though Docling observed them during processing.

Those distinctions are now more important to the technical reference than its previous coverage of Markdown serializers, chunking, RAG integrations, and the broader document ecosystem.

# Docling 2.145.0 — Advanced Capabilities Addendum

Companion to: Docling — Comprehensive Python Library Overview (`docling.md`)\
Research date: November 1, 2026\
Version scope: Docling 2.145.0, released October 29, 2026; associated `docling-core` and companion packages\
Purpose: Document advanced functionality omitted or insufficiently developed in the original overview and its PDF-to-structured-JSON supplement.

This addendum covers capabilities that extend Docling beyond initial document conversion: programmable document transformations, selective ingestion, structural profiling, advanced chunk serialization, remote conversion, custom enrichment, format-specific processing, and diagnostic instrumentation.

It assumes familiarity with `DocumentConverter`, `ConversionResult`, `DoclingDocument`, the PDF pipelines, and the core document schema. Those concepts are not repeated here.

The principal architectural distinction is that conversion, document transformation, semantic enrichment, retrieval preparation, and service execution can be separate operations over a common document representation. Docling already supplies substantial machinery for each operation, reducing the need to manipulate serialized JSON directly or duplicate the original parsing process.

The version distinction matters: `docling`, `docling-slim`, `docling-core`, and `docling-client` are separately distributed packages. Docling 2.145.0 and `docling-core` 2.105.0 are verified published versions, but their version numbers are not interchangeable. APIs described in current documentation should be checked against the corresponding installed companion-package release when exact compatibility matters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 1. Programmable document transformations

### 1.1 `DoclingDocument` is a mutable structured-document model

Beyond defining a schema, `docling-core` provides operations for constructing, inserting, extracting, deleting, replacing, and composing document elements while retaining their typed identities and structural relationships.

The relevant distinction is between modifying a document's semantic graph and modifying one of its exported representations. Working through the document API allows transformations to operate on `TextItem`, `TableItem`, `PictureItem`, `GroupItem`, and other typed objects, rather than relying on the conventions of Markdown, HTML, or flattened JSON.

The API exposes several families of operations:

| Operation family         | Principal APIs                                                                                                    | Capability                                                       |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Construction             | `add_text`, `add_heading`, `add_table`, `add_picture`, `add_page`, `add_list_item`, `add_key_values`              | Create typed content with parents, provenance and other metadata |
| Ordered insertion        | `insert_text`, `insert_heading`, `insert_table`, `insert_picture`, `insert_code`, `insert_formula`, `insert_form` | Insert new elements relative to existing siblings                |
| Structural editing       | `append_child_item`, `insert_node_items`, `insert_item_before_sibling`, `insert_item_after_sibling`               | Manipulate parent-child relationships and reading order          |
| Replacement and deletion | `replace_item`, `delete_items`, `delete_items_range`                                                              | Replace or remove complete nodes and their descendants           |
| Document composition     | `concatenate`, `insert_document`, `add_node_items`                                                                | Combine document content without flattening individual objects   |
| Document extraction      | `extract_items_range`, `filter`                                                                                   | Derive smaller document objects from existing structure          |
| Table manipulation       | `TableData.add_row`, `insert_row`, `remove_row`, and their plural forms                                           | Modify tabular structure directly                                |

These are document operations, not generic JSON Patch operations. They understand aspects of the document's reference system and hierarchy that ordinary dictionary manipulation does not.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+3



### 1.2 Document composition and reference integrity

`DoclingDocument.concatenate(docs)` constructs a combined document from a sequence of documents. Its implementation uses internal indexing to reconstruct and rebase references and page numbering.

This is more substantial than concatenating the `texts`, `tables`, or `pictures` arrays. Those arrays contain objects referred to from the document hierarchy and potentially from other objects. Combining arrays without updating those relationships would produce ambiguous or invalid references.

`insert_document(doc, sibling, after=True)` addresses a different problem: inserting another document's body content at a selected position in an existing document.

`extract_items_range()` can create a new document from a contiguous range of top-level body nodes. It supports inclusive/exclusive boundaries and optional deletion from the source. `filter(page_nrs=...)` instead derives a document using a page-selection predicate. These are structurally different operations: a semantic section can span pages, while a page filter can cut across sections or multi-page items.

Important limitation: A successfully rebased structural graph does not automatically preserve the original interpretation of source identity. Concatenating documents changes page numbering within the resulting document; consumers retaining original source-page citations need an explicit mapping between combined-document positions and original sources.

### 1.3 Hierarchical traversal and controlled mutation

`iterate_items()` traverses the document structure and yields `(NodeItem, depth)` pairs. It supports:

- `root` to begin traversal at a selected subtree.
- `with_groups` to include grouping nodes.
- `page_no` for page-based traversal filtering.
- `included_content_layers` to select body, furniture, notes or other layers.
- `traverse_pictures` to traverse content nested inside picture items.

The yielded depth describes traversal hierarchy; it is not interchangeable with the semantic heading depth stored in `SectionHeaderItem.level`.

The distinction between traversal order and array order is particularly important during transformation. Processing `texts[]` sequentially may not respect the placement of tables, pictures, captions, list groups or nested document content.

For direct mutation, `replace_item` permits replacing one node with another, while deletion APIs remove subtrees. When inserting an existing subtree, the document-level insertion methods handle more of the relationship management than direct edits to `children` or `parent` references.

After structural transformations, `validate_document()` and `validate_tree()` provide consistency checks. `validate_tree()` verifies parent/child reciprocity and prevents duplicate traversal paths through the same tree. These checks establish graph integrity, not whether edited source text or provenance accurately represents the original document.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



### 1.4 Native table and document visualization

Two additional APIs extend the transformation model.

`TableData` provides direct row operations, allowing tabular content to be edited without first exporting to a DataFrame or reconstructing the complete table manually. Such operations are particularly valuable where cell boundaries, merged spans, or metadata need to survive the edit.

`DoclingDocument.get_visualization()` generates page-indexed PIL images representing the document's interpretation. It supports `reading_order` and `key_value` modes, optional labels, reading-order branch numbering, and cell identifiers for key/value visualization.

This provides a native way to inspect the constructed semantic graph spatially, complementing the separate PDF pipeline debugging visualizations discussed later. The visualizations depend on the page images and geometry available in the document; they are not a replacement for the original PDF or its low-level parser objects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 1.5 Architectural significance

The combination of typed insertion, structural extraction, provenance-aware traversal, validation and composition makes `DoclingDocument` usable as a document-transformation intermediate representation.

It can support corrections to inferred structure, insertion of derived metadata, assembly of composite documents and extraction of selected document regions without implementing a separate JSON graph editor.

The boundary remains important: these APIs maintain document structure; they do not automatically establish OCR correctness, resolve conflicting semantic interpretations, or provide a transactional document-editing database.

Primary reference:\
`https://docling-project.github.io/docling/reference/docling_document/`

Upstream implementation:\
`https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py`

## 2. Selective ingestion, input sources and conversion progress

### 2.1 Page selection and input limits

`DocumentConverter.convert()` and `convert_all()` expose controls that are more precise than selecting a source and a pipeline:

| Parameter           | Behavior                                                            | Consequential distinction                                                        |
| ------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `page_range`        | Selects an inclusive range of pages for conversion                  | Reduces work on excluded pages; not equivalent to a maximum document-size policy |
| `max_num_pages`     | Maximum acceptable source-document page count                       | Documents exceeding the limit are rejected rather than silently truncated        |
| `max_file_size`     | Maximum accepted source size                                        | Bounds admissible inputs, not inference memory                                   |
| `raises_on_error`   | Controls whether failed conversions raise or return failure results | `PARTIAL_SUCCESS` remains distinguishable from complete success                  |
| `headers`           | HTTP headers for URL-based source retrieval                         | Controls fetching the source, not remote inference authentication                |
| `progress_callback` | Receives structured events during conversion                        | Provides lifecycle observability independently of final results                  |

`page_range` is especially valuable when only selected portions of a long document need interpretation. The upstream example uses `(16, 16)` to convert a single page. These page numbers follow Docling's document-page convention, rather than Python's zero-based array indexing.

For batch conversion, a single `page_range` applies to the document inputs in that call; it is not an independent page-selection specification for each source.

A narrower page range can reduce extraction and inference work, but does not guarantee proportional savings in file loading, source validation, model initialization, or PDF backend startup.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 2.2 File streams, HTTP sources and direct text conversion

The converter supports several input representations:

- `Path` and string paths for local files.
- URL strings and `HttpSource` for HTTP-accessible documents.
- `DocumentStream` for binary document data held in memory.
- `convert_string()` for directly supplying supported textual formats, including Markdown, HTML and DocLang.

`DocumentStream` is useful when the document already exists as a byte stream. It carries a source name and a binary stream, allowing format detection and processing without first writing the input to a temporary file.

`HttpSource` carries a URL and headers in one source object. For `convert_all()`, per-source headers are merged with the call's common headers, with source-specific values taking precedence for matching keys. This allows documents requiring different retrieval credentials to participate in one conversion batch.

`convert_string()` is a distinct convenience interface for textual source representations. It should not be confused with passing arbitrary binary PDF bytes as a Python string.

The important boundary is source transport versus source interpretation. A `DocumentStream` changes how bytes reach the backend; it does not select a different OCR, layout, or table-recognition process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 2.3 Incremental batch results

`convert_all()` returns an iterator of `ConversionResult` objects.

This supports processing results incrementally instead of retaining an entire batch of converted documents. It is also compatible with handling failures individually when `raises_on_error=False`.

However, an iterable result is not evidence that each document uses bounded page memory or that model inference runs with arbitrary concurrency. Memory consumption within a conversion depends on the selected pipeline, page buffering, image retention and model resources.

Similarly, iteration does not by itself guarantee parallel execution. Document concurrency is a separate operational control.

### 2.4 Structured progress events

The progress callback API provides a more detailed processing lifecycle than a single percentage.

Docling defines progress events including:

| Event                       | Meaning                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------- |
| `DocumentStartedProgress`   | A document has been selected for processing, including subsequently skipped inputs |
| `PhaseStartedProgress`      | Processing enters initialization, build, assembly or enrichment                    |
| `PageCompletedProgress`     | A PDF/image page completes its page-level processing                               |
| `EnrichmentProgress`        | Reports processed item counts for enrichment stages                                |
| `DocumentCompletedProgress` | Reports the final document status                                                  |

Events include document identifiers suitable for correlating progress across a batch.

Two behaviors are worth preserving in an advanced reference. First, pages may finish out of order; `completed_pages` is the appropriate progress counter, not the largest page number observed. Second, completing all page-level operations does not necessarily mean the document is finished, because document-level enrichment can follow.

The VLM pipeline has different reporting semantics: enrichment performed during page processing can already be covered by the page completion event.

Callbacks are observational rather than a reliable mechanism for controlling conversion. Exceptions raised inside a callback are logged and ignored. Under document-level concurrency, callbacks may be invoked from multiple worker threads and must be safe for concurrent use.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 2.5 Example: selective, observable conversion

The following illustrates the combination of page selection, input limits and structured progress reporting. The example is based on documented APIs and has not been executed here.

```
from docling.document_converter import DocumentConverterfrom docling.datamodel.progress import ConversionProgressEventdef on_progress(event: ConversionProgressEvent) -> None:    print(event.model_dump_json())converter = DocumentConverter()result = converter.convert(    "large_report.pdf",    page_range=(10, 25),    max_num_pages=1000,    raises_on_error=False,    progress_callback=on_progress,)
```

The callback provides execution visibility; `ConversionResult` remains the authoritative source of final conversion status, errors and document output.

Primary references:

`https://docling-project.github.io/docling/reference/document_converter/`

`https://docling-project.github.io/docling/usage/advanced_options/`

Version-specific converter implementation:

`https://github.com/docling-project/docling/blob/v2.145.0/docling/document_converter.py`

## 3. Structural document and collection profiling

### 3.1 `DocumentProfiler` as a separate analysis subsystem

`docling-core` includes `docling_core.transforms.profiler.DocumentProfiler`, which calculates structural statistics over `DoclingDocument` objects.

This functionality is independent of the original conversion process. It can therefore operate on documents constructed manually, loaded from JSON, or produced by different Docling pipelines.

Its two principal interfaces are:

- `DocumentProfiler.profile_document(doc)` for one document.
- `DocumentProfiler.profile_collection(documents, include_individual_stats=...)` for aggregate analysis of multiple documents.

The returned objects use typed Pydantic statistics models and support ordinary serialization through `model_dump()` or `model_dump_json()`.

### 3.2 Single-document statistics

The profiler can report document characteristics including page count, text item count, table count, picture count, heading count, list items, code blocks and formulas.

Additional fields include aggregate item counts, average items per page, source MIME type and information about pictures potentially requiring OCR.

These measurements describe the constructed document representation. For example, `num_tables` counts recognized `TableItem` objects, not the number of logical tables necessarily present in the original file.

That distinction is useful when profiling alternative pipeline outputs. A document with fewer detected tables may reflect a simpler source, but it might also reflect recognition failures or differences in layout classification.

### 3.3 Collection-level distributions

`profile_collection()` aggregates document statistics and provides descriptive measures such as means, distributions, deciles and histograms. The official example exposes aggregate fields for document counts, total pages, total pictures, total tables and page-count distributions.

The interface accepts an iterator or generator of documents. With `include_individual_stats=False`, the profiler need not retain all individual-document statistics in its returned result.

This supports collection-level analysis without constructing a single list containing every document beforehand.

The memory benefit has a specific boundary: a document must still exist while it is being profiled, and the profiler's aggregate structures still consume memory. Generator input removes the need to retain the entire source collection simultaneously; it does not imply constant memory for arbitrary document complexity.

### 3.4 Structural profiling versus extraction-quality diagnostics

The profiler addresses a different question from `ConversionResult.confidence` or `ConversionResult.timings`.

| Mechanism                     | What it measures                                     |
| ----------------------------- | ---------------------------------------------------- |
| `DocumentProfiler`            | Characteristics of the resulting structured document |
| `ConversionResult.timings`    | Processing time spent in conversion stages           |
| `ConversionResult.confidence` | Available model/parser confidence assessments        |
| Document validation           | Internal schema and reference consistency            |

Structural profiling is useful for identifying documents with unusual representation patterns, including unexpectedly few text items, many small elements, very high picture density or inconsistent table counts.

It can also help characterize collection heterogeneity before selecting downstream chunking or serialization behavior.

But none of these structural statistics establishes that the contents of a recognized table or OCR text are correct. Profiling is descriptive, not an independent source-fidelity evaluation system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary reference and implementation example:

`https://github.com/docling-project/docling-core/blob/main/examples/document_profiling.py`

Package description:

`https://pypi.org/project/docling-core/2.105.0/`

## 4. Advanced chunk serialization and context expansion

### 4.1 Chunk serialization is independently configurable

The standard chunkers operate on structured documents, but their text representation is controlled by a separate serializer layer.

`ChunkingSerializerProvider` supplies a serializer for a given document, and `ChunkingDocSerializer` controls the conversion of individual document elements into chunk text.

This permits changing how tables, pictures and other components are represented without changing the chunker's structural traversal or token-management algorithm.

The official example illustrates replacing the default table serialization strategy with `MarkdownTableSerializer`. The default strategy represents certain table information in a key/value-oriented triplet format; the alternative produces a Markdown table.

The distinction affects downstream embedding behavior. Flattening a table into triplets can emphasize row-header/value relationships, while Markdown may preserve a more familiar grid representation. Neither serialization guarantees retention of every aspect of the original `TableData`.

A custom serializer can also include picture metadata and descriptions selectively, rather than treating all pictures as a single placeholder.

### 4.2 OCR text nested in pictures is excluded by default

This is a consequential interaction between document semantics and retrieval serialization.

OCR text recognized inside a picture can be retained as `TextItem` children of a `PictureItem`. Those children may be present in the document's reference graph and serialized JSON.

However, the default `HybridChunker` serializer uses `traverse_pictures=False`, so it does not normally include the picture's nested OCR text in generated chunks.

The purpose is to prevent low-quality recognition artifacts from overwhelming retrieval content. Diagrams containing numbers, dense symbols or graphical patterns can produce large amounts of noisy OCR output.

For documents containing meaningful text inside images, this default can also exclude relevant information from text-only retrieval.

The supported mechanism for changing this behavior is to provide a custom `ChunkingSerializerProvider` returning a `ChunkingDocSerializer` configured with `MarkdownParams(traverse_pictures=True)`.

This setting changes which document elements are traversed for serialization, not whether OCR runs during conversion.

The architectural implication is that extraction completeness and indexing completeness are different properties. A retained OCR item can be absent from the chunked retrieval representation without being absent from the source document model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 4.3 Expand retrieved chunks to larger structural units

The `docling_core.transforms.chunker.chunk_expander` module provides:

- `TreeChunkExpander`, which expands a chunk to the relevant containing document element or structure.
- `PageChunkExpander`, which expands a chunk to the content of the containing page.

Both operate using a source document and serializer rather than requiring arbitrary text-window reconstruction.

This supports an important distinction between retrieval granularity and consumption granularity.

A tokenizer-constrained chunk can be appropriate for indexing and nearest-neighbor search while being too narrow for subsequent interpretation. For example, a retrieved chunk from a table may contain only several rows, although interpreting it requires the full table and its headers.

Expanding that chunk using the original document structure can recover a larger semantic unit after retrieval.

Likewise, page expansion can provide surrounding page context for answering a question or inspecting source evidence.

The expansion is not guaranteed to respect the original chunk token limit. It may substantially increase prompt size, especially when an entire table or page is included. The expansion strategy also inherits the selected serializer's decisions about picture traversal and content layers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 4.4 Interaction with document hierarchy and metadata

`HierarchicalChunker` maintains heading ancestry as it walks document structure, and its emitted chunk metadata can reference contributing `DocItem` objects and document origin.

The serializer controls what text is emitted, while the chunker retains relationships needed to reconstruct context.

This separation permits several kinds of derived representations from one document:

- A concise, token-bounded representation for retrieval.
- A richer representation including nested image text or descriptions.
- An expanded semantic unit for a retrieved result.
- A page-level representation for source-grounded interpretation.

These are different views of the same document. Creating them need not require another PDF conversion, provided the structured document retains the required source information.

Primary reference:

`https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/`

Chunking architecture:

`https://docling-project.github.io/docling/concepts/chunking/`

## 5. Native client for remote Docling conversion

### 5.1 `DoclingServiceClient`

Docling provides a dedicated Python client for its companion `docling-serve` service.

The relevant installation surfaces are `docling-client` and the `docling-slim[service-client]` extra. The `docling-client` distribution is a convenience metapackage; its implementation is supplied through `docling-slim`.

The main client interface is `docling.service_client.DoclingServiceClient`. `AsyncDoclingServiceClient` provides asynchronous equivalents.

The high-level API deliberately resembles `DocumentConverter`, including `convert()` and `convert_all()`. A remote conversion can return a `ConversionResult` containing a normal `DoclingDocument`, so downstream document manipulation and export do not require adopting a different semantic representation.

The equivalence is at the document API boundary, not at every operational detail. Remote conversion uses Docling Serve's supported request schema, model configuration and installed server capabilities. Arbitrary locally defined Python pipeline classes cannot simply be transferred to a remote server through the conversion request.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 5.2 Conversion and job-management modes

The client supports several levels of interaction:

| Interface                   | Functionality                                                                                        |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| `convert()`                 | Submit and obtain a converted document through a high-level synchronous interface                    |
| `convert_all()`             | Convert multiple documents with client-side concurrency control                                      |
| `AsyncDoclingServiceClient` | Asynchronous conversion and job operations                                                           |
| `submit()`                  | Submit an explicit conversion job                                                                    |
| `watch()`                   | Observe an asynchronous job                                                                          |
| `result()`                  | Retrieve a completed job's result                                                                    |
| `submit_batch()`            | Submit batch-source processing requests                                                              |
| `chunk()`                   | Request server-side chunk generation                                                                 |
| Result targets              | Support service-compatible artifact targets, including object-storage and presigned-URL arrangements |

These interfaces serve different purposes.

High-level conversion minimizes the amount of service protocol machinery a caller must implement. Explicit job submission provides persistent task identifiers and control over result retrieval. Batch sources and result targets are relevant when processing data already held in storage accessible to the service.

The remote client also exposes typed exceptions, including `ServiceUnavailableError`, `TaskTimeoutError`, `UsageLimitExceededError`, and `ResultExpiredError`, with a common `DoclingServiceClientError` base family.

These failures are not necessarily equivalent to failures in local document parsing. A service can reject work, expire an artifact or become unavailable independently of whether the underlying document is parseable.

### 5.3 Artifact retrieval and security

The service supports result artifacts referenced through presigned URLs.

The client includes an important defensive restriction: it normally refuses artifact downloads from private, loopback and link-local network addresses. This helps prevent an untrusted or compromised service from directing the client to internal network resources.

`artifact_url_allowlist` permits explicitly authorized artifact-storage origins, including private-network services. The validation also considers redirects.

This is separate from authentication to the Docling Serve API. It controls where the client may retrieve service-produced artifacts, not who may submit conversion jobs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 5.4 Remote CLI

`docling convert-remote` exposes remote conversion from the command line.

Its configuration includes service URL, optional API key, selected input/output formats, concurrency, output paths and remote-job monitoring.

Unlike local `docling convert`, the remote command does not expose controls that only make sense for local execution, such as CUDA device selection, local model-thread counts or parser debug visualizers.

Remote conversion therefore removes the need to initialize conversion models in the calling process, but introduces HTTP transport, service compatibility, authentication, artifact retrieval, and service-lifetime dependencies.

Primary references:

`https://github.com/docling-project/docling/blob/main/packages/docling-client/README.md`

`https://docling-project.github.io/docling/usage/api_server/rest_api/`

`https://docling-project.github.io/docling/reference/cli/`

## 6. Custom enrichment and post-conversion interpretation

### 6.1 Enrichment as an extension mechanism

The original guide describes the built-in picture, code, formula and chart enrichments. A separate capability is developing new document-item enrichment models.

The relevant extension contracts include `BaseEnrichmentModel` and `BaseItemAndImageEnrichmentModel`.

`BaseEnrichmentModel` supplies an item-oriented processing interface. An implementation determines which document elements it can process through `is_processable()` and receives batches through its callable interface.

An enrichment can operate directly on `DoclingDocument` objects and populate the corresponding typed metadata.

For image-dependent processing, `BaseItemAndImageEnrichmentModel` provides the conceptual contract for models that require both an item and its image evidence.

This permits custom interpretation of already-detected elements rather than requiring a new page-layout model or source-format backend.

### 6.2 Custom stages in the standard PDF pipeline

The official picture-enrichment example demonstrates subclassing `StandardPdfPipeline`, supplying custom pipeline options, and adding an enrichment implementation through `enrichment_pipe`.

The example uses a dummy picture classifier that creates structured classification metadata on `PictureItem.meta`.

This demonstrates the extension interface, not a production classifier. An implementation must still provide its own inference or deterministic recognition logic, model loading, error handling and metadata semantics.

The distinction between the major extension points is:

| Extension point                | Responsibility                                                        |
| ------------------------------ | --------------------------------------------------------------------- |
| Format backend                 | Interpret source-format structures                                    |
| OCR/layout/table engine plugin | Replace or specialize a reconstruction operation                      |
| Custom conversion pipeline     | Define the processing sequence and model composition                  |
| `BaseEnrichmentModel`          | Add interpretation to recognized document elements                    |
| Post-conversion enrichment     | Interpret an existing document without reconstructing it from scratch |

Custom enrichment is especially useful when source parsing and layout reconstruction are already satisfactory but additional semantic interpretation is required.

### 6.3 Enriching a previously serialized document

Docling's official example demonstrates enriching an existing `DoclingDocument` loaded from JSON.

The process is conceptually:

1. Load the existing document and preserve its structural graph.
2. Identify eligible elements using `is_processable()`.
3. Obtain corresponding image crops from the original source using provenance coordinates.
4. Batch eligible elements and invoke the enrichment model.
5. Store derived annotations in the existing document representation.

The implementation uses `InputDocument`, `PyPdfiumDocumentBackend`, and `ItemAndImageEnrichmentElement` to re-access the PDF and construct element/image pairs.

This does not repeat the entire initial PDF-to-document semantic reconstruction. It does, however, reopen the original source to obtain visual evidence. Thus, it is not an entirely source-independent operation.

The source PDF must correspond to the document used to produce the saved JSON. If page numbering, page dimensions or provenance are inconsistent, an image crop may contain the wrong evidence even though the serialized document remains structurally valid.

The example also demonstrates batching as an independent control. Larger batches may improve model inference throughput but increase the memory consumed by image crops and intermediate model inputs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 6.4 Interaction with typed metadata

Enrichment can populate `PictureMeta` and other structured metadata rather than attaching arbitrary caption strings.

For example, a picture classifier can produce a `PictureClassificationMetaField` containing predictions with creator identifiers, class names and confidence values.

This is useful when different enrichment operations must coexist without overwriting each other. A picture may retain its original provenance and image reference while acquiring additional classification or description information.

There is nevertheless no automatic guarantee of semantic consistency across independently produced enrichments. Metadata supplied by custom models must be interpreted according to their own model contracts and confidence semantics.

Primary references:

`https://docling-project.github.io/docling/_generated/examples/develop_picture_enrichment/`

`https://docling-project.github.io/docling/_generated/examples/enrich_doclingdocument/`

`https://docling-project.github.io/docling/usage/enrichments/`

## 7. Browser-rendered HTML and geometry-aware ingestion

### 7.1 Parsing HTML versus rendering HTML

Docling's HTML backend supports two materially different processing approaches.

The default approach parses HTML source structure. `HTMLBackendOptions(render_page=True)` optionally invokes a headless browser to render the document and capture page images and element bounding boxes.

The latter is useful when the document's visual arrangement contains information not adequately conveyed by the markup tree alone.

It does not convert HTML ingestion into the standard PDF pipeline. The HTML backend still interprets the HTML document; the browser-rendering mode supplements its output with visual and geometric information.

This capability is exposed through the `htmlrender` optional dependency family, which introduces a Playwright/browser runtime rather than depending only on ordinary HTML parsing.

### 7.2 Rendering configuration

The v2.145.0 `HTMLBackendOptions` class includes:

| Control                                   | Functionality                                                              |
| ----------------------------------------- | -------------------------------------------------------------------------- |
| `render_page`                             | Activate headless-browser rendering                                        |
| `render_page_width`, `render_page_height` | Set rendered page dimensions in CSS pixels                                 |
| `render_page_orientation`                 | Portrait or landscape                                                      |
| `render_print_media`                      | Use print-media emulation                                                  |
| `render_wait_until`                       | Select Playwright's `load`, `domcontentloaded`, or `networkidle` condition |
| `render_wait_ms`                          | Additional delay after page loading                                        |
| `render_device_scale`                     | Device pixel scaling                                                       |
| `render_full_page`                        | Capture one full-height image rather than paginating                       |
| `render_dpi`                              | Output image DPI                                                           |
| `page_padding`                            | Apply padding to the HTML body                                             |

These settings can materially affect the resulting geometry. Viewport dimensions, font rendering, print styles, image loading and browser timing may change element positions or pagination.

Consequently, browser-derived coordinates are properties of a particular rendered representation. They should not be treated as intrinsic, device-independent coordinates of the HTML source.

### 7.3 HTML resource fetching and document furniture

The same backend exposes additional controls:

- `fetch_images` and `source_uri` govern retrieval and resolution of image resources.
- `headers` and `headers_allowed_origins` control where resource-fetch credentials may be sent.
- `add_title` can retain the HTML title as document furniture.
- `infer_furniture` controls whether content preceding the first header is treated as furniture.
- `max_image_data_base64_bytes`, `max_remote_image_bytes`, and `max_redirects` bound certain resource-fetching operations.

The header-origin restriction is important for authenticated document resources. By default, request headers are not indiscriminately forwarded to arbitrary image hosts. Explicit origin configuration is required where resource retrieval spans authorized domains.

The browser-rendering option and image-fetching option are separate concerns: rendering an HTML page does not imply that every externally referenced resource will be available or that every browser-side dependency is trusted.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 7.4 Architectural significance and limits

Browser-assisted HTML ingestion bridges authored semantics and rendered appearance.

It can reduce the need for a separate screenshot/DOM-coordinate extraction system when downstream document interpretation requires both structural HTML content and geometric information.

Its limitations are those of browser-derived evidence: layout is sensitive to rendering configuration, asynchronous resources may not have finished loading, and executing browser-based page rendering has different isolation and trust implications from parsing static markup.

Version-specific source:

`https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py`

Optional dependency information:

`https://pypi.org/project/docling-slim/2.145.0/`

## 8. Format-specific structural fidelity and extraction controls

A common `DoclingDocument` representation does not imply that every backend extracts equivalent information. Several native-format backends expose controls that affect which authored structures are recognized, how they are grouped, and whether their visual representation is retained.

### 8.1 Spreadsheet segmentation and selective worksheet ingestion

`MsExcelBackendOptions` and `OdsBackendOptions` expose three particularly useful controls:

| Option                    | Mechanism                                                                            | Consequence                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| `sheet_names`             | Case-sensitive selection of worksheets                                               | Restricts conversion to named sheets                                 |
| `gap_tolerance`           | Permits specified numbers of empty rows or columns between neighboring data clusters | Changes whether adjacent regions become one table or separate tables |
| `treat_singleton_as_text` | Represents isolated populated cells as `TextItem` rather than one-cell `TableItem`   | Avoids treating every isolated label or note as a standalone table   |

`gap_tolerance` is a structural interpretation parameter, not a missing-value imputation mechanism. Raising it can join table regions separated by intentional spacing, but may also incorrectly combine distinct tables.

Likewise, `treat_singleton_as_text` changes item type. That can affect later table-specific processing, even though the original cell text remains available.

Excel additionally exposes `parse_charts`, enabled by default in the tagged source, to recognize native workbook charts. Each supported chart becomes a `PictureItem` with classification and reconstructed tabular data. This is independent of `render_chart_images`, which optionally invokes LibreOffice to render chart images.

The separation matters: chart data extraction does not require chart-image rendering. A chart can have usable structured data while having no retained raster image. Conversely, rendering an image does not improve the accuracy of the extracted chart series.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 8.2 Office chart images and heading semantics

The DOCX and PPTX backends also expose `render_chart_images`. When enabled, they isolate native charts into temporary Office documents and use LibreOffice to render corresponding images.

Chart metadata and reconstructed data remain available independently of this setting. The image path introduces a LibreOffice dependency and additional processing cost.

For Word documents, `MsWordBackendOptions.use_outline_level_for_headings` provides another important semantic control.

Word paragraphs can indicate outline depth through `w:outlineLvl`, even when their style names are localized or do not follow conventional heading naming. Docling can use this authored signal to recover heading semantics.

The tradeoff is that Word styles may carry outline levels solely for table-of-contents participation. Treating every such style as a heading can promote content that was not intended to be a semantic heading. The option is enabled by default in the v2.145.0 source; disabling it prevents this fallback for otherwise unidentified heading styles.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.3 Apple iWork chart reconstruction

`IWorkBackendOptions` supports selective Numbers sheet conversion through `sheet_names` and optional chart rendering for Numbers and Keynote through `render_chart_images`.

This renderer differs from the native Office chart pathway. Numbers and Keynote do not store chart screenshots in the form Docling needs, so the backend rebuilds a chart from recovered data as a temporary Office chart and renders that through LibreOffice.

Consequently, the generated image can preserve the chart type, data and title while not necessarily retaining original colors, fonts or visual styling. Some chart classes, including mixed, dual-axis, bubble and interactive charts, cannot be rendered by this mechanism.

The backend can retain recognized chart classification and data even when rendering is disabled or unsupported. This is another case where data fidelity and presentation fidelity are separate dimensions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.4 Source comments, email attachments and text decoding

Additional format-specific behaviors are easily overlooked:

| Format             | Native capability                                                                       | Limitation or qualification                                                               |
| ------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| AsciiDoc           | `capture_comments` retains `//` comments and `////` blocks in the `NOTES` content layer | Enabled by default in v2.145.0, but normal exports omit that layer                        |
| AsciiDoc           | `fetch_images` and `source_uri` resolve and retrieve referenced images                  | Resource fetching is separately configurable                                              |
| EML / MSG          | `list_attachments` records attachment names and content types                           | Disabled by default; does not embed or recursively convert attachment binaries            |
| Text-based formats | `TextBackendOptions.encoding` selects an explicit Python codec                          | Without an explicit codec, decoding uses BOM detection, UTF-8, then CP1252 before failing |

Preserving comments in the document graph while omitting them from the default textual export is a meaningful example of how content-layer policy can change apparent extraction completeness.

The text-decoding option is also important for archival material. An explicit codec avoids heuristic fallback, but it does not repair text already corrupted by an earlier decoding operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 8.5 Declarative EBCDIC record parsing

The EBCDIC backend goes beyond converting character encodings.

`EbcdicBackendOptions` accepts an `EbcdicLayout` directly or through a JSON `layout_file`. The layout can describe fixed-format records, field positions and types, and optional record-type selectors for heterogeneous record streams.

Supported field concepts include character data, signed and unsigned integers, packed decimals and zoned decimals. The backend also allows codec selection, record-count limits and control-character stripping.

When a layout includes several record variants, a designated record-type field identifies which schema applies. The layout validator enforces distinct record names and selectors, preventing incompatible record classes from being silently merged.

This supplies a declarative route from legacy fixed-record data into Docling's document representation without first constructing a separate bespoke record parser.

It is fundamentally different from natural-language document extraction: the correctness of the result depends on an accurate record layout and codec, rather than learned page understanding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.6 Additional recognized source extensions

The supported-extension mapping also includes `.txt`, `.text`, `.qmd` and `.Rmd` / `.rmd` through Markdown-oriented ingestion paths.

This is worth noting because an accepted filename extension does not establish a wholly separate parser or full support for every source language's executable semantics. A Quarto or R Markdown document can be ingested as text/markup without Docling executing its embedded code or reproducing its rendering engine.

Primary sources:

`https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py`

`https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/base_models.py`

## 9. Selective serialization and portable document archives

### 9.1 Serialization of selected document views

`DoclingDocument.export_to_markdown()` and related exporters support considerably more than full-document export.

Important controls include:

| Parameter family                              | Functionality                                                |
| --------------------------------------------- | ------------------------------------------------------------ |
| `from_element`, `to_element`                  | Select a range of body elements                              |
| `labels`                                      | Restrict output by document item class                       |
| `page_no`                                     | Select content associated with a specific page               |
| `included_content_layers`                     | Include or exclude selected semantic layers                  |
| `traverse_pictures`                           | Include text nested within picture items                     |
| `enable_chart_tables`                         | Control the textual representation of available chart tables |
| `include_annotations`, `allowed_meta_names`   | Select which supported annotations and metadata are emitted  |
| `image_mode`, `image_dir`, `image_uri_prefix` | Determine image references and related artifact locations    |
| `compact_tables`                              | Select a more compact table serialization                    |

The filters operate against the document's structured representation, allowing different derived views without recreating the original document.

The important distinction is between selecting content for an export and removing content from the underlying document. Excluding a content layer or item label from Markdown does not necessarily delete its corresponding object from `DoclingDocument`.

Furthermore, body-element ranges and page filters are not interchangeable: body hierarchy can include items spanning several pages.

### 9.2 YAML as structured interchange

In addition to JSON, `docling-core` provides `save_as_yaml()` and `load_from_yaml()`.

YAML serialization exposes comparable controls for embedded versus referenced images, artifact paths and coordinate or confidence precision.

This is a structured interchange alternative, not a different extraction model. It preserves the semantics represented by the serialized document subject to serialization settings, but cannot recover source information that the conversion pipeline never captured.

For machine-oriented integrations, the underlying typed schema and its version remain more important than the choice of JSON versus YAML.

### 9.3 DocLang archives (`.dclx`)

`save_as_doclang_archive()` creates a packaged DocLang artifact rather than a loose markup file.

Its principal features include:

- DocLang markup inside an OPC-style archive.
- Page images retained under `pages/`.
- Referenced picture assets retained under `assets/`.
- `add_named_groups` to emit named grouping structures for compatible round-tripping.
- `include_namespace` and `validate` for namespace-aware DocLang validation where the required validation backend is available.
- `xsize` and `ysize` for the DocLang location-coordinate grid.

The default picture-image mode is `REFERENCED`, and `PLACEHOLDER` is also supported. `EMBEDDED` is not supported for the archive, because images remain separate from the markup. Page images are included independently of whether picture references are retained.

A `.dclx` file can therefore be a more convenient portable multimodal artifact than separate markup and image files.

However, it should not be treated as an identical alternative to complete native `DoclingDocument` JSON. DocLang is its own representation with different schema conventions and round-trip considerations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



### 9.4 Chunked JSONL as a separate output contract

The CLI supports `--to chunks`, with `--chunks-type`, `--chunks-max-tokens` and `--chunks-tokenizer` controlling chunk generation.

This is a retrieval-oriented output, not the canonical `DoclingDocument` reference graph serialized to JSON.

The distinction is significant for consumers expecting full document reconstruction. Chunk output may retain useful metadata and references, but should not be assumed to contain every source item, relationship, picture payload or provenance field needed to recreate the original structured document.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Primary references:

`https://docling-project.github.io/docling/reference/docling_document/`

`https://docling-project.github.io/docling/reference/cli/`

## 10. Conditional picture interpretation and inference metadata

### 10.1 Selective picture description

Docling's API-based picture description configuration provides `picture_area_threshold`, allowing the description stage to ignore picture regions below a configured relative area threshold.

This is useful because not every detected picture is worth the cost of a VLM call. Small icons, graphical decorations and minor page artifacts may offer little semantic value.

The threshold is geometric, not a semantic relevance classifier. A small diagram or symbol may still be important, while a large decorative background may not be. This is therefore a compute-selection mechanism, not a general guarantee that only informative pictures are processed.

### 10.2 Per-picture inference-usage payloads

`PictureDescriptionApiOptions.usage_response_key` specifies the response field from which the backend reads an API provider's usage payload.

When configured, this data can be retained in the picture's description metadata. The official example retrieves it through:

```
picture.meta.description.get_custom_part()
```

The example combines `do_picture_description=True`, `enable_remote_services=True`, and `usage_response_key="usage"`.

This creates a relationship between a picture's source identity, its generated description and metadata about the inference call that produced that description.

The usage payload is provider-specific. A returned token count or usage object does not establish standardized billing units, monetary cost, or attribution of all processing overhead. Nor does a picture-level usage entry measure the local layout/OCR work required to produce the picture object.

The supported mechanism is therefore best understood as preserving inference-provider accounting evidence alongside semantic output, rather than providing a complete cost-modeling subsystem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



Primary reference:

`https://docling-project.github.io/docling/_generated/examples/picture_description_api_usage/`

## 11. Pipeline diagnostics, profiling and failure control

### 11.1 Stage-specific visual diagnostics

Docling's CLI exposes visual diagnostics for intermediate PDF processing stages:

| CLI option                  | Inspected information  | Principal diagnostic purpose                                       |
| --------------------------- | ---------------------- | ------------------------------------------------------------------ |
| `--debug-visualize-cells`   | PDF-native text cells  | Identify parsing, text segmentation and native geometry problems   |
| `--debug-visualize-ocr`     | OCR-recognized cells   | Inspect OCR positioning and coverage                               |
| `--debug-visualize-layout`  | Layout clusters        | Investigate incorrect element classification or grouping           |
| `--debug-visualize-tables`  | Recognized table cells | Inspect table structure and text-to-cell association               |
| `--debug-vlm-native-output` | Unparsed VLM responses | Distinguish model-generation failures from output parsing failures |

These diagnostics provide visibility into the representation before it becomes the final structured document.

For example, a missing table may originate from several different failures: native text extraction may omit relevant cells, OCR may locate text incorrectly, layout detection may fail to identify the table, or table recognition may produce an invalid grid.

The final `TableItem` representation alone generally cannot distinguish all these causes.

Stage-specific visualization can therefore reduce the need to build independent instrumentation around parser, OCR, layout and table-model outputs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 11.2 Conversion profiling and timeout semantics

The CLI supports `--profiling` for conversion-stage timing summaries and `--save-profiling` for corresponding JSON output.

These measurements complement the structural `DocumentProfiler` described in §3. Conversion profiling measures execution behavior; document profiling measures characteristics of the resulting document.

`PipelineOptions.document_timeout` provides a per-document processing deadline. When the deadline is exceeded, Docling can return partial output with timeout errors rather than treating the timeout as an entirely opaque external exception.

The result's timeout classification and conversion status should be considered together:

- `PARTIAL_SUCCESS` can indicate that some useful document content was recovered.
- Timeout errors establish that the conversion was interrupted.
- Neither a partial result nor a completed progress bar establishes that every intended element was processed.

`ConversionResult.has_timeout_errors()` provides a direct way to identify timeout-related failures.

The CLI also supports `--fail-on` with `never`, `failure` and `partial` policies. This allows process exit status to distinguish fatal conversion failures from partially completed documents. It is operational behavior separate from the document's schema validity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 11.3 Operational interaction

Progress events, timeouts, profiling, conversion status and stage-specific debug output serve different purposes.

Progress reveals which work has completed; timeouts bound processing; profiling identifies where time was spent; debugging shows what intermediate representations looked like; and `ConversionResult` records the final outcome.

Together, they support a more informative extraction diagnostics model without requiring all observations to be embedded in `DoclingDocument` JSON.

Primary references:

`https://docling-project.github.io/docling/reference/cli/`

`https://docling-project.github.io/docling/reference/pipeline_options/`

`https://docling-project.github.io/docling/usage/advanced_options/`

## 12. Additional speech-recognition engines and their output semantics

### 12.1 Transformers-based ASR presets

Beyond the Whisper backends described in the original guide, Docling supports speech-recognition models through an optional Transformers integration.

The `docling-slim[feat-asr-transformers]` extra supplies this backend, with model presets exposed through `docling.datamodel.asr_model_specs`.

Documented model families include:

| Family                 | Presets                                   | Distinctive consideration                                     |
| ---------------------- | ----------------------------------------- | ------------------------------------------------------------- |
| IBM Granite Speech 5.0 | `GRANITE_SPEECH_5_0_2B`                   | Transformer-based speech transcription                        |
| Granite TurboCTC       | `GRANITE_SPEECH_5_0_470M_TURBOCTC`, `_NC` | Separate checkpoint variants and licensing                    |
| Granite Speech 4.1     | `GRANITE_SPEECH_4_1_2B`, `_PLUS`          | Additional model-native annotation capabilities               |
| NVIDIA Nemotron Speech | `NEMOTRON_SPEECH_STREAMING_EN_0_6B`       | Streaming-oriented checkpoint used through file transcription |
| NVIDIA Parakeet        | `PARAKEET_CTC_1_1B`                       | CTC-based transcription alternative                           |

Model availability is not equivalent to uniform output capabilities. Runtime, checkpoint, hardware and license requirements remain model-specific.

For example, the `TURBOCTC_NC` checkpoint carries a CC-BY-NC-SA-4.0 license, distinct from the main Docling Python package license.

On Apple MPS, the documented Granite and TurboCTC implementations use FP32 weights to avoid a BF16 normalization problem, increasing memory requirements relative to lower-precision execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 12.2 Important output limitations

Docling's Transformers-based ASR pathway currently produces one transcript segment covering the entire audio duration.

Consequently, these presets do not automatically provide the segment-level temporal structure associated with every Whisper configuration.

The Granite Speech 4.1 Plus checkpoint can have native speaker and timestamp annotations, but its current Docling integration does not map those annotations into structured document tracks.

Likewise, a checkpoint bearing streaming in its name does not establish that the Docling ASR pipeline exposes real-time streaming transcription. The documented integration performs file transcription.

This illustrates the difference between model-native capabilities and what a particular document-conversion adapter exposes.

For timed retrieval, subtitle production or speaker-grounded interpretation, the relevant integration's actual timestamp and segmentation behavior matters more than the model name alone.

Primary reference:

`https://docling-project.github.io/docling/usage/processing_audio_media/`

## 13. LaTeX TikZ rendering and execution-trust boundaries

### 13.1 Optional TikZ-to-image rendering

`LatexBackendOptions` supports optional rendering of TikZ diagrams through the Tectonic engine.

The main controls are:

| Option                           | Behavior                                                      |
| -------------------------------- | ------------------------------------------------------------- |
| `tikz_engine="tectonic"`         | Selects Tectonic-based diagram rendering                      |
| `tikz_engine_trusted_input`      | Explicitly permits rendering for trusted documents            |
| `tikz_engine_timeout`            | Bounds rendering time for an individual diagram               |
| `tikz_engine_allow_shell_escape` | Allows shell escape for trusted input when explicitly enabled |
| `parse_timeout`                  | Bounds LaTeX document parsing time                            |
| `source_uri`                     | Resolves relative source includes and graphics paths          |

When rendering succeeds, TikZ content can become an image in the resulting document.

When rendering is disabled, refused by the trust setting, or fails, Docling can preserve the original TikZ source as code rather than silently discarding the diagram.

This distinguishes source preservation from visual interpretation: retaining TikZ instructions is not equivalent to understanding the resulting diagram, and rasterizing the diagram does not automatically recover semantic relationships between its visual components.

### 13.2 Trust and resource implications

Tectonic can access files available to its process. The upstream source explicitly states that its source pre-check is not a security boundary.

Consequently, `tikz_engine_trusted_input=True` is an execution-trust declaration, not simply a fidelity or rendering-quality option.

`tikz_engine_allow_shell_escape` remains disabled by default and should be distinguished from the broader trusted-input setting.

For untrusted LaTeX sources, rendering in an appropriately isolated process is materially different from merely enabling a parser option in a privileged application process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 13.3 Distinct Docling security controls

Several advanced features introduce separate security decisions:

| Mechanism                   | Relevant control                   | What it permits                                                       |
| --------------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| Remote model inference      | `enable_remote_services`           | Transmitting document-derived data to configured remote services      |
| External processing plugins | `allow_external_plugins`           | Loading installed third-party processing implementations              |
| Model repository code       | `--trust-remote-code`              | Executing compatible locally loaded model repository code             |
| LaTeX rendering             | `tikz_engine_trusted_input`        | Running Tectonic over trusted source material                         |
| HTML resource fetching      | Fetch settings and allowed origins | Retrieving external content and determining where headers may be sent |
| Referenced JSON images      | `allow_local_images`               | Loading local file-based images associated with serialized documents  |
| Remote result artifacts     | `artifact_url_allowlist`           | Permitting additional artifact-download destinations                  |

These controls are not interchangeable.

Disabling remote inference does not mean locally loaded model code is trustworthy. Refusing external plugins does not eliminate the risks of browser execution or document-triggered native processing. Conversely, an authorized artifact destination does not establish the semantic correctness of its contents.

The useful architectural distinction is between data egress, code execution, resource retrieval and parser isolation. Each requires separate treatment because the relevant permissions and trust assumptions differ.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



Primary references:

`https://github.com/docling-project/docling/blob/v2.145.0/docling/datamodel/backend_options.py`

`https://docling-project.github.io/docling/reference/cli/`

## 14. Structured content transformation examples: PII and translation

Two official examples demonstrate a further consequence of the document model: source conversion can be followed by content rewriting while retaining the surrounding document structure.

### 14.1 PII detection and obfuscation

The PII example converts a PDF, runs a Hugging Face token-classification model or an optional GLiNER model, and replaces recognized entity strings inside text and table content with stable, type-based identifiers.

The example demonstrates several useful mechanisms:

- Reuse of converted `TextItem` and `TableItem` content.
- Entity detection as an operation separate from OCR and layout reconstruction.
- Consistent replacement identifiers for repeated recognized entities.
- Export of the modified document without re-running the original conversion.

The entity-recognition models are external dependencies. Docling supplies the structured content and transformation surface; it does not independently guarantee comprehensive PII identification.

The example is explicitly demonstrative. In particular, replacing recognized text does not establish that sensitive information has been eliminated from every other retained representation, such as images, original text fields, metadata, source files or intermediate objects.

Source:

`https://docling-project.github.io/docling/_generated/examples/pii_obfuscate/`

### 14.2 Translation while retaining document objects

The translation example traverses text and table items, updates their textual content, and preserves the surrounding document representation.

Its `translate()` function is a placeholder returning the original input. Actual translation requires an external implementation.

The capability demonstrated is therefore structured content rewriting, not a complete native machine-translation engine.

The distinction is consequential: replacing text in an existing graph can preserve tables, picture relationships and some provenance, but translated content may have different lengths, line breaks and spatial requirements. Original coordinates should not be interpreted as faithful geometry for a newly typeset translation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



Source:

`https://docling-project.github.io/docling/_generated/examples/translate/`

## 15. Capability interactions and architectural consequences

The additional capabilities form several important combinations.

Typed document editing + validation + serialization. A `DoclingDocument` can function as a mutable semantic intermediate representation. Document construction and correction can occur through native typed operations, with structural validation before producing different output formats. This avoids many failure modes associated with directly manipulating interconnected JSON arrays.

Selective ingestion + progress events + diagnostics. Page-range conversion, explicit input limits, progress callbacks, stage visualizations and timeout reporting make it possible to bound and inspect extraction work through Docling's own interfaces. These mechanisms remain distinct from model confidence and structural completeness.

Retained provenance + post-conversion enrichment. Existing document elements can be enriched using their original source geometry without repeating all semantic reconstruction stages. This separates initial extraction from later interpretations while making source availability and coordinate fidelity explicit dependencies.

Document-aware chunking + customizable serialization + expansion. Retrieval-sized chunks can use concise representations while later stages recover larger document units. This avoids treating the text used for indexing as the only available representation of the source. Picture traversal and content-layer configuration must nevertheless be chosen explicitly where completeness matters.

Remote conversion + the local document model. A Python client can delegate conversion and model execution to Docling Serve while returning a familiar structured-document interface. The resulting portability is strongest at the document-data boundary; deployment capabilities, artifact access, service failures and configuration remain separate.

Format-specific parsing + common semantic representation. Spreadsheet chart data, Word outline levels, AsciiDoc notes and declarative fixed-record layouts can enter a shared document model without losing the distinction between authored source semantics and visually inferred structure. That distinction remains essential for interpreting the fidelity of the result.

Taken together, these capabilities extend Docling's role from document ingestion into a broader structured-document processing substrate: conversion produces typed content, transformation changes its structure, enrichment adds interpretation, profiling characterizes it, serialization produces controlled views, and remote execution changes where those operations run.

The common `DoclingDocument` representation makes these operations composable. It does not by itself guarantee source fidelity, complete semantic preservation, lossless round-tripping, or correctness of externally supplied models. Those guarantees remain specific to each format backend, pipeline, transformation, and output representation.