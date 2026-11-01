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