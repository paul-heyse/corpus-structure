# MinerU 4.0.12 — Comprehensive Python Library Overview

Research date: October 28, 2026 | Target: MinerU 4.0.12, released October 11, 2026 | Python 3.10–3.14

MinerU is a document-understanding and conversion framework that transforms PDFs, scanned documents, images, and Office files into machine-readable, structurally organized representations suitable for information extraction, search, retrieval-augmented generation (RAG), and agentic workflows.

MinerU 4.0 represents a substantial architectural expansion beyond a PDF-to-Markdown converter. It combines multimodal document understanding, configurable inference engines, a structured document representation, a persistent document library, and programmatic parsing services.

Its distinguishing characteristic is the integration of three capabilities:

1. Document understanding: Layout analysis, OCR, mathematical expression recognition, table extraction, and vision-language-model inference.
2. Structured representation: A shared document model preserving semantic blocks, page context, reading order, geometry, and assets, with multiple rendering formats.
3. Document infrastructure: Python SDK, local searchable document library, agent-oriented incremental reading, asynchronous processing, and distributed inference services.

The current stable release is 4.0.12. This overview focuses on the 4.x architecture; tutorials and API examples written for MinerU 2.x or 3.x can be materially incompatible.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary sources:

- Repository: `https://github.com/opendatalab/MinerU`
- Documentation: `https://opendatalab.github.io/MinerU/`
- Release history: `https://github.com/opendatalab/MinerU/releases`
- PyPI: `https://pypi.org/project/mineru/`

## 1. Architectural orientation

MinerU occupies the space between low-level document parsers and higher-level document intelligence systems.

Unlike libraries that primarily expose raw text, character positions, or PDF objects, MinerU attempts to reconstruct the semantic organization of a document.

Input documents

PDF · Images · Office · OpenDocument · EPUB · HTML · OFD · CSV

Flash

Native extraction

Basic

Small models

Standard

Hybrid + VLM

Advanced

More inference

Shared structured document model

Pages · Blocks · Text · Tables · Equations · Images · Metadata · Geometry

Rendering

Markdown, JSON, HTML, LaTeX, DOCX, PDF, EPUB

Document library

Cache, search, locators, incremental reading

Services

Python SDK, HTTP API, Router, WebUI

### Capability map

| Capability family        | Native MinerU functionality                                                         |
| ------------------------ | ----------------------------------------------------------------------------------- |
| Document ingestion       | PDFs, scanned images, Office formats, EPUB, HTML, OFD, and tabular document files   |
| Visual understanding     | Layout classification, reading-order reconstruction, image and chart identification |
| Content recognition      | Native text extraction, OCR, formula recognition, table extraction                  |
| Multimodal inference     | Specialized models combined with VLM-based parsing                                  |
| Structured outputs       | Versioned intermediate JSON, semantic blocks, positional data, generated assets     |
| Rendering                | Markdown, HTML, LaTeX, DOCX, EPUB, PDF, and structured content representations      |
| Document management      | Persistent local library, search, caching, indexing, citation locators              |
| Programmatic integration | Synchronous/asynchronous Python parsing, HTTP API, batch conversion                 |
| Inference infrastructure | ONNX, PyTorch, llama.cpp, vLLM, LMDeploy, routing, concurrency controls             |

An important architectural distinction is that parsing tier, inference runtime, document representation, and delivery interface are separate choices. MinerU supports different combinations rather than requiring all consumers to operate through one model or one service.

Sources: `https://opendatalab.github.io/MinerU/usage/tiers/` and `https://opendatalab.github.io/MinerU/reference/output_files/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



## 2. Document ingestion and source interpretation

MinerU distinguishes between documents whose text and structure can be extracted from an existing digital representation and documents requiring visual recognition.

| Input family           | Supported formats                        | Primary approach                                                           |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------------------------- |
| PDFs                   | Native-text, mixed-content, scanned PDFs | Native text extraction, page rendering, layout analysis, OCR, optional VLM |
| Images                 | Common raster image formats              | Visual page analysis and OCR                                               |
| Office                 | DOC/DOCX, PPT/PPTX, XLS/XLSX             | Native document conversion through Flash                                   |
| OpenDocument           | ODT, ODP, ODS                            | Native document parsing                                                    |
| Publishing and web     | EPUB, HTML, MHTML, RTF                   | Native structural extraction                                               |
| Other document formats | OFD, CSV, TSV                            | Format-specific Flash parsing                                              |

The first major distinction is source structure versus inferred structure.

A digitally generated PDF may contain selectable text, but the text stream alone does not reliably express the logical order of multi-column content, the boundaries of a table, or the association between an image and its caption. Conversely, a scan has no usable source text and requires recognition from pixels.

MinerU's architecture can combine native text, detected visual regions, and model-generated content. This is more sophisticated than extracting characters and concatenating them in page order.

### 2.1 Parsing controls

For PDF and image inputs, the core controls are:

- Tier: How much recognition and multimodal inference to perform.
- OCR mode: Whether to favor native text, OCR, or automatic selection.
- Page range: Which pages are processed; user-facing page ranges are one-based.
- Image analysis: Additional visual interpretation, where supported by the selected inference path.

`ocr_mode` supports `auto`, `txt`, and `ocr`. These are not interchangeable. For example, Flash with `txt` is suitable when source text is usable but should not be treated as a guaranteed OCR fallback for a scanned page.

Office, EPUB, HTML, and comparable native formats are Flash-only in the local 4.x parser. Their conversion applies to the whole document; the PDF page-range mechanism does not directly transfer to these inputs.

The underlying native-format functionality is also associated with DocVortex, a separate dependency. MinerU orchestrates parsing and downstream representation; it should not be confused with the underlying format converters themselves.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



Sources: `https://opendatalab.github.io/MinerU/usage/tiers/`, `https://opendatalab.github.io/MinerU/usage/cli_tools/`

## 3. Parsing tiers and multimodal document understanding

### 3.1 Four public quality tiers

| Tier       | Processing approach                            | Principal capabilities                             | Important tradeoff                                     |
| ---------- | ---------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| `flash`    | Native parsing; lightweight OCR when required  | Fast document conversion, previews, indexing       | Less semantic reconstruction                           |
| `basic`    | Dedicated smaller models                       | Layout detection, OCR, formulas, tables            | No VLM-level interpretation                            |
| `standard` | Smaller models combined with a VLM             | Improved complex-layout and multimodal extraction  | Greater memory and inference cost                      |
| `advanced` | Standard model stack with additional inference | More demanding visual or structural interpretation | Higher inference cost; no universal accuracy guarantee |

`standard` is the default for local PDF parsing. `advanced` is explicitly selected and does not require a separate Advanced model bundle. It increases inference computation using the Standard deployment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



### 3.2 Specialized-model pipeline

The smaller-model path performs several different operations rather than asking one generative model to produce an entire document.

Layout detection and classification. MinerU identifies and classifies regions such as text, headings, images, tables, equations, captions, headers, footers, footnotes, and page numbers. The resulting regions provide a structural map that informs subsequent extraction and ordering.

Text recognition. Where usable native PDF text exists, it can be retained rather than regenerated by a visual model. OCR is used for image-based content or regions requiring recognition. This distinction matters for accuracy, latency, and avoiding unnecessary text reconstruction.

Formula recognition. Specialized mathematical formula recognition can generate representations suitable for LaTeX rendering. Formula detection and formula transcription are separate concerns: identifying a formula's location does not establish that its mathematical content was recognized correctly.

Table recognition. Dedicated table processing attempts to recover table structure rather than treating a table as ordinary paragraph text. Difficulties remain with merged cells, nested headers, borderless tables, and visually complex layouts.

Reading-order reconstruction. MinerU assembles detected regions into a logical sequence, accounting for layout elements that do not follow simple top-to-bottom character ordering.

The consequence is that the Basic path provides meaningful document understanding without requiring a generative VLM, potentially avoiding its additional model-loading and token-generation costs.

### 3.3 Hybrid VLM processing

Standard and Advanced retain the smaller-model capabilities but integrate a vision-language model into content interpretation.

The implementation distinguishes two major inference patterns:

- Standard: VLM content extraction guided by precomputed layout regions, using the `batch_extract_with_layout` path.
- Advanced: A more computationally intensive `batch_two_step_extract` path that can perform additional visual interpretation.

The internal code uses effort labels such as `medium`, `high`, and `xhigh`, whereas the public-facing API uses `basic`, `standard`, and `advanced`. These internal labels should not be mistaken for the current public API values.

The VLM is therefore not simply a replacement for OCR. It works within a wider analysis pipeline, and different recognition components can be used depending on the source and parsing configuration.

This design provides a useful quality–cost separation: simpler documents can be parsed without deploying the complete multimodal stack, while difficult layouts can receive more model inference.

Sources: `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/mineru/backend/analysis/pdf/window.py`, `https://opendatalab.github.io/MinerU/usage/tiers/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 3.4 Semantics and failure modes

MinerU's output should be understood as a reconstructed interpretation of the source, not a guaranteed lossless transformation.

Particularly consequential distinctions include:

- Text correctness versus reading-order correctness: Recognized words can be correct while appearing in the wrong semantic sequence.
- Table appearance versus table semantics: A recognizable table image does not imply correct row/column or merged-cell recovery.
- Formula presentation versus mathematical equivalence: Generated LaTeX can contain symbol or grouping errors.
- Layout classification versus true document semantics: Visual headings, captions, footnotes, and citations are inferred, and ambiguous cases can be misclassified.
- VLM extraction versus source fidelity: Generative inference can omit, alter, or introduce content.

These are inherent risks of document recognition, not guarantees about a specific failure rate. When exact source fidelity is critical, native text and positional outputs may provide more appropriate verification evidence than Markdown alone.

## 4. Structured document representation and rendering

MinerU 4.x's most important architectural feature is its shared intermediate document representation. Parsing, rendering, document indexing, and API delivery can operate on the same semantic result rather than independently reconstructing a document.

### 4.1 Two levels of intermediate JSON

| Representation       | Purpose                            | Important characteristics                                                          |
| -------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- |
| `ModelJson`          | Analysis-stage results             | Model output, analyzed pages, original page-index mapping                          |
| `MiddleJson`         | Postprocessed document             | Ordered semantic blocks, nested content, metadata, extensions, page context        |
| `Structured Content` | Simplified consumer representation | Easier-to-consume text and block data; not the intermediate serialization protocol |
| `Content List` V1/V2 | Flattened or page-grouped content  | Convenient downstream extraction and positional processing                         |

The two intermediate JSON types are explicitly identified through their serialized `schema` and `schema_version` fields:

- `docvortex.model`
- `docvortex.middle`

Both use protocol schema version `2.0` in MinerU 4.0.12. Crucially, the schema version is not the same thing as the MinerU package version.

A simplified MiddleJson document has the following shape:

```
{
  "metadata": {
    "producer": {
      "name": "mineru",
      "version": "4.0.12"
    }
  },
  "extensions": {
    "mineru": {
      "tier": "standard",
      "parse_mode": "txt"
    }
  },
  "pages": [
    {
      "page_idx": 0,
      "blocks": [
        {
          "type": "text",
          "index": 0,
          "content": [
            {
              "type": "text",
              "content": "Example content"
            }
          ]
        }
      ]
    }
  ],
  "is_full_document": true,
  "schema": "docvortex.middle",
  "schema_version": "2.0"
}
```

This is an illustrative subset, not a complete schema fixture. Real results can include bounding boxes, nested structure, images, tables, equations, and additional extensions.

`metadata.producer.version` records the producing package version, while `extensions.mineru` records the actual parsing tier and parse mode. The distinction allows consumers to reason about both data contract compatibility and the provenance of the generated data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



### 4.2 Geometry and source traceability

MinerU retains spatial information alongside textual content.

For PDFs, its `extensions.docvortex_layout` records source-page geometry, including page dimensions in PDF points and relevant orientation information. The current output contract preserves this data in both analysis-stage and postprocessed results.

This creates opportunities that plain Markdown cannot support:

- Mapping extracted statements to source regions.
- Cropping and reviewing an individual detected block.
- Preserving source-page identity when parsing only selected pages.
- Reconstructing documents with approximate original positioning.
- Distinguishing body text from headers, footers, equations, tables, and figures.

Coordinate conventions require attention. Serialized `page_idx` is zero-based, while CLI ranges and document-library page locators are one-based. Content List positional fields also use a different normalized coordinate convention from PDF point measurements.

This matters when joining MinerU outputs with independent PDF or image tools: identifiers and coordinates need explicit interpretation, not merely matching field names.

### 4.3 Nine rendering targets

The `mineru.render` layer supports more formats than the individual command-line interfaces expose.

| `RenderFormat`       | Result type        | Principal application                                   |
| -------------------- | ------------------ | ------------------------------------------------------- |
| `MARKDOWN`           | `str`              | Human/LLM-readable text, sections, and embedded content |
| `HTML`               | `str`              | Rich document display and HTML processing               |
| `LATEX`              | `str`              | Mathematical and scientific document output             |
| `DOCX`               | `bytes`            | Editable Word document generation                       |
| `EPUB`               | `bytes`            | Reflowable publication output                           |
| `PDF`                | `bytes`            | Reconstructed PDF export                                |
| `STRUCTURED_CONTENT` | `dict`             | Structured downstream processing                        |
| `CONTENT_LIST`       | `list[dict]`       | Flat content extraction                                 |
| `CONTENT_LIST_V2`    | `list[list[dict]]` | Page-grouped extraction                                 |

For PDF export, the renderer exposes distinct layout policies:

- `PdfLayout.ORIGINAL` positions reconstructed content within original page/block geometry where sufficient geometry exists.
- `PdfLayout.REFLOW` produces a semantically reflowed document.
- `PdfLayout.AUTO` selects original-layout rendering when the prerequisites are present and otherwise falls back to reflow.

This does not imply pixel-identical round-tripping. Tables and charts can use image fallbacks, and reconstruction differs from preservation of the original PDF object graph.

A particularly useful architectural consequence is that document understanding and output representation can be separated. A parsed document can be rendered for multiple downstream consumers without rerunning every recognition model, provided the intermediate document and its referenced assets are preserved.

Sources: `https://opendatalab.github.io/MinerU/reference/output_files/`, `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/docs/en/reference/output_files.md`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



### 4.4 Asset packaging and preservation

`ParseResult.save(writer)` writes a materialized result package containing Markdown, MiddleJson, Structured Content, and referenced images. Raw model output is also written when available.

An important limitation: `ParseResult.to_json()` and `to_dict()` do not necessarily preserve embedded image bytes. Structural JSON alone is therefore not a complete substitute for the document plus its extracted assets.

For durable storage or transport, the package/ZIP output is often the more meaningful unit. Asset paths should be read from the produced references rather than reconstructed from guessed filenames.

Source: `https://opendatalab.github.io/MinerU/reference/output_files/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



## 5. Advanced document postprocessing

In addition to first-pass page extraction, MinerU provides mechanisms that interpret structure across blocks and pages.

### 5.1 Cross-page content continuity

A long table may span several pages, with repeating headers, split rows, or cells whose content continues on the next page. Detecting a table on each page does not itself resolve whether those segments are part of the same logical table.

MinerU includes cross-page table-processing logic and can optionally invoke an external LLM to determine whether corresponding boundary-row cells should be merged.

The distinction is significant:

Table detection → cross-page table association → cell-continuation interpretation are separate semantic operations, with different opportunities for error.

### 5.2 LLM-aided heading hierarchy

MinerU also provides optional `title_leveling` to classify paragraph titles into hierarchy levels 2–6, grouped according to document-title boundaries.

This feature requires `MiddleJson.is_full_document` to be true; a partial-page selection does not provide the required full-document context and skips this operation.

### 5.3 Optional external LLM configuration

These two features are controlled through `llm_aided` configuration:

```
llm_aided:
  api_key: ${MINERU_LLM_API_KEY:-}
  base_url: https://example-llm-service/v1
  model: example-model
  max_concurrency: 16
  features:
    title_leveling: false
    cross_page_table_cell_merge: false
```

The example endpoint and model above are placeholders.

Both features are disabled by default. When enabled, they share an asynchronous model client with a configurable concurrency limit. They require an appropriate OpenAI-compatible LLM service and introduce additional inference cost and potential data transmission.

These capabilities should not be conflated with the VLM used to recognize pages. The VLM interprets visual document content; LLM-aided postprocessing interprets already-extracted structure.

Source: `https://opendatalab.github.io/MinerU/usage/quick_usage/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



## 6. Python SDK and execution interfaces

MinerU offers three programmatic interaction patterns with different state-management responsibilities.

| Interface         | State ownership                           | Main purpose                                                    |
| ----------------- | ----------------------------------------- | --------------------------------------------------------------- |
| `mineru.parser`   | Caller-managed, stateless per parse       | Direct Python parsing and structured results                    |
| `MinerUApiParser` | Remote V1 service owns jobs and inference | Python access to a separate parser deployment                   |
| `DoclibClient`    | Persistent document-library service       | Document identity, caching, search, jobs, and incremental reads |

### 6.1 Direct Python parsing

The public Python SDK includes `parse`, `parse_async`, `MinerUParser`, `ParseResult`, and `MinerUApiParser`.

A representative SDK interaction:

```
from mineru.parser import parsefrom mineru.parser.writer import FileBasedDataWriterfrom mineru.render import render, RenderFormatresult = parse(    "document.pdf",    tier="standard",    ocr_mode="auto",    page_range="1-3",)markdown = result.markdown()structured = result.structured_content()middle_json = result.to_json()html = render(result.middle_json, RenderFormat.HTML)result.save(FileBasedDataWriter("parsed-output"))
```

The SDK returns a reusable `ParseResult`, allowing different renderers to consume the same parsed document.

Other relevant interfaces include `ParseResult.from_json()` for current-protocol result restoration and `parse_async()` for asynchronous execution.

`parse_async()` provides an awaitable interface, but this is not a guarantee that all underlying models are nonblocking or that every inference engine supports the same concurrency behavior.

A direct Python parse also does not automatically register the document in MinerU's persistent document library. The SDK and Doclib are separate facilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



Source: `https://opendatalab.github.io/MinerU/usage/sdk_api/`

### 6.2 Remote Python parsing

`MinerUApiParser` exposes a similar result-oriented interface while placing model execution behind a V1 HTTP service.

```
from mineru.parser import MinerUApiParserparser = MinerUApiParser(    api_url="http://127.0.0.1:8000",    tier="standard",    include_images=True,)result = parser.parse("document.pdf")markdown = result.markdown()
```

The client manages service discovery, uploading, job submission, polling, and result retrieval.

This separates Python applications that consume parsed documents from environments that install GPU-dependent inference engines. However, remote parsing involves transfer of the original document and result assets, so service trust, data handling, and operational latency become part of the design boundary.

### 6.3 Two command-line interfaces

MinerU 4.x deliberately separates stateless conversion from persistent document interaction.

| Command tree                                  | Responsibility                                                     |
| --------------------------------------------- | ------------------------------------------------------------------ |
| `mineru-kit parse`                            | Stateless single-file and batch conversion                         |
| `mineru-kit models`                           | Model download, verification, effective-runtime inspection         |
| `mineru-kit api-server`                       | Local HTTP parsing service                                         |
| `mineru-kit webui`                            | Gradio user interface                                              |
| `mineru-kit router`                           | Routing across inference workers                                   |
| `mineru-kit vlm-server`                       | OpenAI-compatible VLM inference service                            |
| `mineru parse/read/search/find`               | Persistent library and agent-oriented document interaction         |
| `mineru scan/watch/config/invalidate/cleanup` | Document discovery, indexing policy, cache and library maintenance |

There is an easy-to-miss completeness difference:

- `mineru-kit parse` and local Python `parse()` select all PDF pages by default.
- `mineru parse` defaults to the first 10 PDF pages, and stdout is further bounded by a 30,000-character soft reading limit.

Those defaults support interactive reading, but a successful bounded response is not evidence that the entire document was exported.

For complete file export with the library CLI, specify `--pages all` and an output path.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



Source: `https://opendatalab.github.io/MinerU/usage/cli_tools/`

## 7. Persistent document library and agent-oriented reading

MinerU 4.x includes a local document library designed for repeated interactions with documents rather than repeated isolated conversions.

This is an important architectural distinction: the document can become a managed, reusable resource, with a stable identity and cached interpretations at different quality levels.

### 7.1 Library responsibilities

The library manages:

- File discovery and document identity.
- Parsing requests, status, and result reuse.
- Cached results associated with parsing tiers.
- Searchable content derived from indexed documents.
- Page-level and block-level reading.
- Persistent reading locators and continuation.
- Watching directories and refreshing document indexes.
- Cache invalidation and cleanup.

`DoclibClient` exposes these functions programmatically, including parsing requests, content reads, search, and document operations.

### 7.2 Stable page and block locators

MinerU returns document locators rather than requiring applications to reference only filenames and unstructured output text.

A locator can have the form:

```
doc:ab12cd3/tier:standard/page:18/block:4/char:120
```

The components identify the document, quality tier, page, block, and optional character offset.

Page and block numbers are one-based in these locators; character offsets are zero-based within a block.

This provides two important capabilities:

Precise follow-up access. An application can request the specific page or block relevant to an earlier result without rereading the complete document.

Source-grounded answers. A downstream agent can retain an explicit location reference alongside an extracted statement, and inspect the original page or block image if needed.

The locator is meaningful within the document library's identity and cache system; it should not be assumed to be an immutable global identifier independent of that library.

### 7.3 Progressive, bounded reading

Long documents can exceed the practical output budget of an interactive agent or model. MinerU supports incremental reads with limits and continuation information.

For example:

```
mineru parse report.pdf --pages 1-10 --limit 12000 --json
mineru search "revenue recognition" --min-tier basic --json
mineru read "doc:ab12cd3/tier:standard/page:18" --json
```

The document ID is illustrative.

Responses can include a `next_request` or continuation command so the consumer can retrieve the next segment rather than parsing or emitting the entire document again.

For PDF documents, cached page images and block-region images can also be retrieved. Block-image extraction requires usable region geometry.

This allows a document-reading system to combine search → targeted reading → visual confirmation, using MinerU's own source locators rather than inventing a parallel navigation format.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.4 Search, discovery, and indexing are different operations

`mineru find` searches known filenames and paths; `mineru search` searches already-indexed content.

The latter is not equivalent to a full semantic retrieval system. MinerU's core document library is not documented as a vector database or end-to-end RAG framework, and the search interface should not be assumed to provide embeddings, hybrid retrieval, reranking, or grounded answer generation.

MinerU can supply high-quality text, structural context, and locators to those systems, which may be implemented using separate libraries or services.

Folder management includes one-time `scan`, persistent `watch`, path-based parsing and exclusion rules, and re-indexing. Watch-based indexing normally uses Flash for relatively inexpensive discovery; higher-quality active reading can invoke Basic, Standard, or Advanced parsing when needed.

Two practical distinctions follow:

1. Discovery does not necessarily mean parsing or indexing has completed.
2. A Flash index entry is not equivalent to a high-quality full-document parse.

MinerU also distinguishes `--force` reparsing from cache invalidation. Maintenance commands can remove obsolete library metadata or parsed assets without deleting the source documents.

Sources: `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/skills/mineru/SKILL.md`, `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/mineru/doclib/client.py`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 8. HTTP services, asynchronous jobs, and distributed inference

MinerU's service layer supports both standalone model execution and access through a shared network API.

### 8.1 V1 document parsing API

The V1 HTTP interface separates document upload, inference job execution, and result retrieval.

The underlying job lifecycle is:

```
Upload registration
    → File-byte upload
    → Parse-job submission
    → Status polling
    → Result and asset retrieval
```

The API includes endpoints for upload registration, file content, parse jobs, service health, supported tiers, and usage information.

The most consequential service behaviors are:

- Parsing can continue after a client disconnects or a synchronous HTTP wait expires.
- A job can have per-file results and partial success.
- Clients can request different artifact formats, subject to service capabilities.
- Existing `file_id` references and SHA-256 checks can reduce redundant uploads.
- Clients can discover supported capabilities before submitting work.

These are useful for large-document processing because HTTP request lifetime need not equal document processing lifetime.

### 8.2 MinerU 4.0.12 convenience endpoints

Version 4.0.12 introduced two additional endpoints for self-hosted API servers and Routers:

| Endpoint              | Purpose                                          |
| --------------------- | ------------------------------------------------ |
| `POST /v1/file_parse` | Synchronous convenience wrapper for file parsing |
| `POST /v1/tasks`      | Asynchronous, one-request task submission        |

They share the existing V1 parse-job lifecycle and identifiers; they do not create a separate inference subsystem.

For the synchronous endpoint, the default wait is 300 seconds. When a request times out, a `202` response can provide the task identifier and follow-up URLs while the job continues.

The documented convenience API limits are 200 MiB per file and 100 files per task. These are interface constraints, not guarantees that every such workload will fit an inference worker's available memory.

The new routes belong to self-hosted deployments. Their availability on a particular hosted cloud service must be checked separately.

Version-specific source: `https://github.com/opendatalab/MinerU/releases/tag/mineru-4.0.12-released`

API reference: `https://opendatalab.github.io/MinerU/usage/http_api/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 8.3 Router and worker orchestration

`mineru-kit router` supplies a shared V1 endpoint across multiple parsing workers.

It supports locally managed GPU workers and connections to independently deployed V1 services. Scheduling considers worker health, supported parsing capabilities, and outstanding workload, with rotation among similarly loaded workers.

An important limitation is that a submitted batch remains assigned to one worker. A batch is not automatically decomposed across all available GPUs. Multiple independent jobs can provide additional worker-level parallelism.

The Router therefore addresses multi-service coordination and unified access, not every form of document-internal parallel processing.

Source: `https://opendatalab.github.io/MinerU/usage/http_api/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



### 8.4 Three distinct remote model/service connections

MinerU supports three different types of remote interaction:

| Service                          | What it does                                                   | Configuration boundary              |
| -------------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| V1 document parsing service      | Parses entire documents and returns structured results         | `MinerUApiParser`, `MINERU_API_URL` |
| Remote VLM inference service     | Supplies vision-language inference to a local parsing pipeline | `model.vlm.server_url`              |
| LLM-aided postprocessing service | Improves heading hierarchy and cross-page table continuation   | `llm_aided` configuration           |

These endpoints are not interchangeable.

In particular, a remote VLM endpoint allows local document orchestration and smaller-model processing to remain local while offloading the VLM. It does not replace the entire parsing service.

The remote VLM path uses an OpenAI-compatible inference interface, with configurable model name, credentials, timeout, and concurrency.

Source: `https://opendatalab.github.io/MinerU/usage/model_source/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



## 9. Model runtimes, deployment, and performance controls

MinerU 4.x has two largely independent inference-runtime decisions:

1. The backend used for dedicated smaller models.
2. The runtime used for the VLM.

### 9.1 Available inference engines

| Component      | Options                         | Architectural significance                                    |
| -------------- | ------------------------------- | ------------------------------------------------------------- |
| Smaller models | ONNX Runtime, PyTorch           | Different acceleration support and model execution paths      |
| Local VLM      | llama.cpp, vLLM, LMDeploy       | Different memory, platform, and throughput characteristics    |
| Remote VLM     | OpenAI-compatible HTTP service  | Separates document processing from VLM-serving hardware       |
| Model source   | Hugging Face, ModelScope, local | Independent model-distribution and offline deployment choices |

The default selection is environment-dependent.

For example, the official 4.x documentation describes ONNX on CPU when an appropriate Torch accelerator runtime is unavailable, llama.cpp as a broadly accessible VLM runtime, and vLLM or LMDeploy for supported accelerated environments.

An explicit engine selection with missing dependencies fails rather than silently selecting an unrelated alternative. This is important for predictable deployments: `auto` is convenient, but an explicitly configured runtime makes the performance and dependency contract clearer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



### 9.2 Installation variants

| Package form    | Scope                                                                                  |
| --------------- | -------------------------------------------------------------------------------------- |
| `mineru`        | Base package, ONNX small-model runtime, llama.cpp, SDK/API and WebUI                   |
| `mineru[torch]` | Adds PyTorch-based smaller-model execution                                             |
| `mineru[full]`  | Adds supported higher-throughput inference engines; vLLM on Linux, LMDeploy on Windows |

The base package is not simply a minimal text parser: it includes substantial parsing and serving functionality.

The Python package accepts versions `>=3.10,<3.15`, but the optional runtime packages have their own compatibility requirements. The 4.0 documentation lists Torch `>=2.7,<3`, Transformers `>=5.10.1,<6`, Linux vLLM `>=0.19.1,<0.29.0`, and Windows LMDeploy `>=0.17,<0.18`. Hardware, Python-wheel, CUDA, and operating-system compatibility must still intersect.

For a version-pinned Python environment:

```
uv pip install "mineru==4.0.12"
```

For a supported Linux accelerated deployment, the `full` extra can be used where its runtime dependencies are compatible.

Sources: `https://opendatalab.github.io/MinerU/quick_start/`, `https://opendatalab.github.io/MinerU/quick_start/extension_modules/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



### 9.3 Configuration and model assets

The default configuration lives in `$MINERU_HOME/config.yaml`, with `MINERU_HOME` defaulting to `~/.mineru`. `MINERU_CONFIG` can select another configuration file.

A representative model configuration is:

```
model:
  source: auto
  base_dir: ~/.mineru/models
  small_backend: auto
  vlm:
    engine: auto
```

Model distribution is separate from the Python package release. The dedicated smaller-model bundles include `MinerU-4_models_torch` and `MinerU-4_models_onnx`; the original VLM weights and llama.cpp variants are distinct model artifacts.

MinerU provides model-management commands:

```
mineru-kit models download --tier standard
mineru-kit models verify --tier standard
mineru-kit models show
```

`models show` reports effective runtime selection and readiness, whereas `models verify` can signal missing assets through its exit status. Neither is a substitute for actually parsing a representative document.

Setting the model source to `local` enforces use of ready local model assets rather than silently downloading missing weights during inference.

Source: `https://opendatalab.github.io/MinerU/usage/model_source/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



### 9.4 Performance mechanisms

MinerU provides several complementary performance mechanisms, each relevant to a different cost center.

| Mechanism               | Cost it can reduce                 | Main condition                            |
| ----------------------- | ---------------------------------- | ----------------------------------------- |
| Flash native extraction | OCR and generative inference       | Usable native document structure          |
| Basic tier              | VLM loading and generation         | Dedicated models are sufficient           |
| Page selection          | Number of pages analyzed           | Only part of the document is required     |
| Content-aware caching   | Repeated parsing                   | Same document and suitable cached tier    |
| Processing windows      | Peak document-analysis working set | Large documents                           |
| ONNX/Torch selection    | Model execution cost               | Compatible hardware and wheels            |
| vLLM/LMDeploy           | VLM-serving overhead under load    | Suitable accelerated runtime and batching |
| Remote VLM              | Local VLM memory footprint         | Reliable network and inference service    |
| Router                  | Worker coordination and scheduling | Multiple available workers                |

For long PDFs, `MINERU_PROCESSING_WINDOW_SIZE` controls the processing-window size. PDF rendering also has timeout and worker-count settings. The 4.x implementation can avoid rendering native-text Flash pages that lack visual regions requiring analysis.

On Linux, `MINERU_MALLOC_TRIM` can optionally attempt to return free glibc heap pages after certain processing stages. It does not release live allocations or GPU memory, so it should not be interpreted as a general memory-management guarantee.

No universal speedup or memory saving can be inferred from these mechanisms without controlling for document complexity, selected tier, model checkpoint, GPU, batching, and runtime configuration.

Sources: `https://opendatalab.github.io/MinerU/usage/cli_tools/`, `https://opendatalab.github.io/MinerU/usage/tiers/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU+1



## 10. Integration boundaries and architectural opportunities

MinerU can substantially reduce the amount of bespoke document-processing infrastructure required by other systems, but the distinction between its native responsibilities and downstream systems remains important.

| Problem family           | MinerU provides                                   | Usually belongs elsewhere                                           |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------------------------- |
| PDF understanding        | Layout, OCR, reading order, content extraction    | Domain-specific semantic validation                                 |
| Scientific content       | Equations and table representations               | Symbolic verification and numerical interpretation                  |
| Document rendering       | Multiple output formats from MiddleJson           | Pixel-perfect source preservation or advanced document editing      |
| Repeated document access | Cache, identity, locators, incremental reading    | Enterprise-wide knowledge governance                                |
| Text search              | Indexed document search                           | Embeddings, vector search, reranking                                |
| RAG ingestion            | Structured source text, pages, references, assets | Retrieval strategy, grounding evaluation, answer generation         |
| Agent document tools     | CLI/SDK, bounded reads, source locators           | Task-specific agent reasoning and orchestration                     |
| Inference operations     | Service API, worker Router, model backends        | General distributed job durability and infrastructure observability |

Several combinations are particularly consequential.

Structured parsing plus direct rendering can avoid independently implementing OCR extraction, semantic reconstruction, and document conversion for each output format.

Content-addressed caching plus quality tiers can separate inexpensive discovery from higher-cost interpretation. A system can recognize the existence of a document before deciding how thoroughly it needs to be parsed.

Locators plus visual region retrieval enable evidence-oriented workflows: extracted text can be paired with the page/block image used for review, without requiring a custom citation-navigation system.

Remote VLM plus local smaller models enables partial inference offloading rather than a binary choice between fully local and fully remote document processing.

Intermediate JSON plus downstream analytical systems allows a parser to supply semantic blocks and geometry while other components provide relational querying, domain-specific interpretation, embeddings, or validation.

These are architectural possibilities, not guarantees that MinerU's internal schema directly matches the consuming system's semantics. Tables, equations, reading order, and spatial information may still require explicit conversion.

## 11. Important limitations and version boundaries

### 11.1 Structural output is not validated truth

MinerU does not eliminate the uncertainty introduced by OCR, visual classification, or VLM inference. The meaning of a generated table, formula, or heading can diverge from the original source even when the rendered output appears plausible.

It is therefore useful to preserve the original document, extracted assets, parsing tier, package/model provenance, and source locators when the result must be audited.

### 11.2 State and task durability differ across interfaces

The Python parser returns a result directly. The document library persists identities and caches. The V1 service manages asynchronous jobs. The Router distributes work among workers.

These are different state and failure domains.

A Router does not, merely by existing, guarantee durable recovery of every outstanding inference job after service failure. Likewise, a client wait timeout is not equivalent to failure or cancellation of the underlying parse.

### 11.3 MinerU 4.x is not API-compatible with 3.x

The 4.x release reorganized the command trees, package extras, tier selection, configuration, result protocol, and HTTP endpoints.

Consequential changes include:

- Previous backend names replaced by the four quality tiers.
- The `mineru` document-library CLI separated from `mineru-kit`.
- `config.yaml` replacing old configuration conventions.
- The current `docvortex.*` intermediate result protocol.
- HTTP `/v1/*` endpoints replacing legacy root-level routes.

Some recognizable historical Doclib caches can be read through a dedicated compatibility reader. That does not mean arbitrary old JSON files are valid current `ParseResult` payloads, nor that older results automatically gain new geometric data or assets.

Source: `https://opendatalab.github.io/MinerU/reference/migration_4/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



### 11.4 Hardware and deployment availability

The mainline 4.x packages support several CPU and GPU configurations, but the official Docker deployment is principally documented for Linux/NVIDIA GPUs. Apple Silicon uses direct local installation for MPS rather than that Docker path.

Some AMD and other vendor-accelerator adaptations remain associated with the older `mineru<4` ecosystem; they should not be assumed to be interchangeable with the current 4.x packages.

Source: `https://opendatalab.github.io/MinerU/quick_start/docker_deployment/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opendatalab.github.io\&sz=32)

MinerU



### 11.5 License is not unmodified Apache 2.0

MinerU 4.0.12 uses the MinerU Open Source License, based on Apache License 2.0 with additional terms.

The tagged license specifies that commercial use without a separate license is generally permitted, but a separate commercial license is required if consolidated usage with affiliates exceeds either:

- 100 million monthly active users; or
- USD 20 million in total monthly revenue.

It also imposes an attribution obligation when MinerU-based online services are provided to third parties, together with termination provisions.

This is a custom license, not an unrestricted Apache-2.0-only grant. Model weights and separate dependencies may have their own licensing obligations.

Authoritative license: `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/LICENSE.md`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 12. Primary-source reference map

The following references give direct entry points into the verified 4.x functionality.

| Topic                               | Primary source                                                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Current release                     | `https://github.com/opendatalab/MinerU/releases/tag/mineru-4.0.12-released`                               |
| Quick start and installation        | `https://opendatalab.github.io/MinerU/quick_start/`                                                       |
| Parsing tiers and runtime selection | `https://opendatalab.github.io/MinerU/usage/tiers/`                                                       |
| Python SDK                          | `https://opendatalab.github.io/MinerU/usage/sdk_api/`                                                     |
| CLI and document library            | `https://opendatalab.github.io/MinerU/usage/cli_tools/`                                                   |
| Advanced CLI controls               | `https://opendatalab.github.io/MinerU/usage/advanced_cli_parameters/`                                     |
| Output and document protocol        | `https://opendatalab.github.io/MinerU/reference/output_files/`                                            |
| HTTP service and task lifecycle     | `https://opendatalab.github.io/MinerU/usage/http_api/`                                                    |
| Models and remote VLMs              | `https://opendatalab.github.io/MinerU/usage/model_source/`                                                |
| Optional inference dependencies     | `https://opendatalab.github.io/MinerU/quick_start/extension_modules/`                                     |
| Docker deployment                   | `https://opendatalab.github.io/MinerU/quick_start/docker_deployment/`                                     |
| Migration from 3.x                  | `https://opendatalab.github.io/MinerU/reference/migration_4/`                                             |
| Document-agent skill and locators   | `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/skills/mineru/SKILL.md`                |
| PDF pipeline orchestration source   | `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/mineru/backend/analysis/pdf/window.py` |
| Licensing                           | `https://github.com/opendatalab/MinerU/blob/mineru-4.0.12-released/LICENSE.md`                            |

## Overall assessment

MinerU 4.0.12 is best understood as a multimodal document-understanding and document-infrastructure framework, rather than merely a Python OCR library or PDF-to-Markdown utility.

Its strongest architectural differentiators are the combination of configurable recognition tiers, hybrid specialized-model/VLM inference, a reusable structured document protocol, multiple rendering targets, source-addressable document blocks, persistent caching, incremental agent-oriented reading, and deployable inference services.

The most important boundaries are equally clear: parsed structure is probabilistic rather than inherently validated, rendering is not lossless preservation, the built-in library is not a complete RAG engine, distributed routing is not a universal durable job scheduler, and the 4.x result/API contracts differ materially from older releases.

Within those boundaries, MinerU provides a substantial native capability base for applications requiring rich document ingestion and reuse, including technically complex PDFs containing formulas, tables, figures, and irregular layouts.