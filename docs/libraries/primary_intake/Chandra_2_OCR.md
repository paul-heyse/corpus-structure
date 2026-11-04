# Chandra OCR 2 — Comprehensive Technical Reference and Docling Integration

Research date: November 3, 2026 | Scope: Chandra OCR 2, local inference, structured document understanding, and Docling integration

## 1. Executive orientation

Chandra OCR 2 is a 4-billion-parameter vision-language model for document transcription, layout reconstruction, and structured visual-content extraction. Released by Datalab on March 18, 2026, it goes considerably beyond conventional optical character recognition.

Its distinctive capability is converting document imagery into several complementary representations: readable text, hierarchical HTML, spatially located document components, reconstructed tables, mathematical notation, and structured descriptions of figures, charts, and diagrams. It can therefore serve as a document-understanding engine rather than merely a text-recognition component.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab+1



### Version and integration status

| Component                 | Verified status                                                       | Significance                                                         |
| ------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Chandra OCR 2             | Released open-weight 4B model                                         | Available for local inference                                        |
| Chandra Python package    | Public `chandra-ocr` package; GitHub release `v0.2.0`                 | Processing, postprocessing, CLI, and inference orchestration         |
| Chandra 2.5               | Released October 14, 2026, through Datalab's hosted API               | Newer structured image descriptions, improved robustness and latency |
| Docling                   | Current documentation explicitly supports Chandra HTML interpretation | Conversion into Docling's structured document model                  |
| Local Chandra 2.5 weights | No publicly released checkpoint verified                              | Do not confuse API model versions with downloadable model versions   |

The version distinction is consequential: Chandra OCR 2 is the verified public checkpoint for self-hosted deployment; Chandra 2.5 is the newer hosted product model. Datalab also offers commercial on-premises licensing, but the 2.5 announcement does not establish general public availability of its weights.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary sources:

- Chandra repository: `https://github.com/datalab-to/chandra`
- Chandra OCR 2 model: `https://huggingface.co/datalab-to/chandra-ocr-2`
- Chandra 2 announcement: `https://www.datalab.to/blog/chandra-2`
- Chandra 2.5 announcement: `https://www.datalab.to/blog/chandra-2-5`
- Docling vision model integration: `https://docling-project.github.io/docling/usage/vision_models/`

### Why the Docling integration matters

Docling now documents a Chandra-specific output parser using `ResponseFormat.CHANDRA_HTML` and `CHANDRA_OCR_LAYOUT_PROMPT`. This is more capable than treating Chandra's result as generic Markdown: Docling can interpret layout bounding boxes, nested document structures, complex tables, forms, mathematical content, and picture metadata.

The important architectural distinction is between using Chandra as the recognition/document-understanding model and using Docling as the document representation, enrichment, and serialization framework. Combining them can retain substantially more information than an OCR-to-plain-text pipeline, although some native Chandra information still requires care to preserve.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



## 2. Chandra's document-understanding model

Chandra 2 performs image-conditioned generation of document structure. Its central operation is not to recognize isolated glyphs and then infer the document hierarchy through separate OCR heuristics. Instead, it generates a structured representation of an entire page, including document components and their relationships.

A typical processing sequence is:

PDF / image

Page rasterization

Chandra 2

Vision + generation

Structured output

HTML + layout blocks

Postprocessing derives Markdown, typed layout chunks, extracted image crops, and metadata; Docling can subsequently map the HTML into its document object model.

This design changes the nature of the output. It can retain a table's structure, an equation's notation, a diagram's connectivity, or a figure's relationship to its caption—not merely the words appearing in those objects.

### 2.1 Capability map

| Capability family       | Native Chandra 2 representation                                        | Important distinction                                                                       |
| ----------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Text recognition        | Text in document order, including multilingual and handwritten content | Generative transcription, not a character-level OCR confidence stream                       |
| Document segmentation   | Semantic block labels with bounding boxes                              | Distinguishes content types and their approximate spatial extent                            |
| Layout and hierarchy    | Headings, lists, paragraphs, captions, footnotes, tables of contents   | Spatial and logical hierarchy are both represented                                          |
| Complex tables          | HTML tables, merged cells, hierarchical headers, nested structures     | Preserves topology rather than flattening cells into text                                   |
| Mathematics             | LaTeX-style mathematical transcription                                 | Equations are distinct document elements                                                    |
| Forms                   | Fields, entered values, checkboxes, radio controls                     | Represents form content and state, but downstream mapping may not preserve all associations |
| Figures and charts      | Image descriptions, chart data, axes, visual classification            | Moves beyond image captioning to data-bearing interpretations                               |
| Flowcharts and diagrams | Mermaid graph descriptions                                             | Can expose nodes, labeled edges, and flow direction                                         |
| Chemical structures     | Chemical blocks and molecular descriptions                             | Specialized scientific representation, not a general molecular validation engine            |
| Code and bibliography   | Separate code and bibliography blocks                                  | Preserves semantic type for downstream processing                                           |

Datalab documents 18 named content categories, including `Chemical-Block`, `Diagram`, `Form`, `Code-Block`, `Equation-Block`, `Complex-Block`, `Bibliography`, and `Table-Of-Contents`. These are especially relevant when processing technical literature, engineering drawings embedded in reports, scientific papers, and mixed-format operational documents.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab+1



### 2.2 Spatially grounded HTML

Chandra's layout prompt requests HTML elements carrying normalized bounding boxes and semantic labels. An illustrative response fragment is:

```
<div data-label="Section-Header" data-bbox="80 90 900 145">
  <h2>Experimental results</h2>
</div>

<div data-label="Table" data-bbox="80 170 900 580">
  <table>
    <tr><th>Condition</th><th>Yield</th></tr>
    <tr><td>Baseline</td><td>91.2%</td></tr>
  </table>
</div>
```

This is a schematic illustration of the format, not output from an executed model run.

The coordinates use a 0–1000 normalized page system rather than PDF points or an absolute image-pixel grid. Chandra's own postprocessor can transform those coordinates into pixels; Docling likewise scales them to the corresponding page.

The semantic label and the HTML content serve different purposes. A `Table` label identifies the kind of region, while the nested table markup describes its structure. Preserving both is substantially more useful than retaining only one.

Granularity limit: These coordinates identify document blocks. They must not be mistaken for separately grounded word-level, character-level, or cell-level bounding boxes. In Docling, those more granular coordinates are not synthesized merely because the parser knows the enclosing block.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

github.com+1



### 2.3 Advanced scientific and graphical extraction

Three capabilities are particularly distinctive.

Charts and plots. Chandra can identify chart categories, read axes and labels, recover data values, and provide descriptions of trends. For a line graph, this may produce series values and time coordinates; for a bar chart, category labels and numerical quantities. However, values reconstructed from graphical marks are estimates when underlying numeric data is not printed. They are not equivalent to accessing the original dataset.

Diagrams and flowcharts. Chandra can express graphical relationships as Mermaid, with nodes, edges, edge labels, and flow direction. This offers an intermediate representation for graph indexing or semantic querying. It does not guarantee that every connector, branch, or visual convention is recognized correctly. The output is a reconstructed interpretation of the source image, not a lossless vectorization.

Mathematical and chemical content. Printed and handwritten equations can be expressed in LaTeX; chemical structures can be identified as specialized blocks. These representations can support downstream symbolic processing, but transcription accuracy and scientific validity remain separate properties. A syntactically valid LaTeX expression or SMILES string need not be a faithful interpretation of the image.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab+1



### 2.4 Forms and document semantics

Chandra is capable of recovering checkboxes, handwriting, entered values, and portions of label–value structure. This is materially richer than detecting that a form contains text.

Nevertheless, three concepts should remain separate:

- Recognition: What characters, controls, and marks are present?
- Structural interpretation: Which fields, labels, and components belong together?
- Domain interpretation: What real-world entity, measurement, obligation, or technical condition does the content describe?

Chandra addresses the first two, with some domain-aware generation in diagrams, chemistry, and charts. It is not, by itself, a configurable ontology engine, a universal scientific classifier, or a guaranteed schema-constrained extractor for arbitrary business objects. Those functions may be built downstream from its richer output or supplied by additional extraction models.

## 3. Native Chandra 2 runtime and output interfaces

The open package exposes more than a command-line document converter. Its important boundary is between the model runtime, page-level inference results, and document-level serialization.

### 3.1 Native interfaces

| Interface          | Responsibility                                                    | When it is useful                              |
| ------------------ | ----------------------------------------------------------------- | ---------------------------------------------- |
| `chandra` CLI      | Load files, render pages, generate outputs, write artifacts       | Batch document processing                      |
| `InferenceManager` | Run page-image batches against HF or vLLM                         | Embedding recognition into Python applications |
| `BatchInputItem`   | Specify page image and prompt mode                                | Explicit layout vs basic OCR behavior          |
| `BatchOutputItem`  | Access HTML, Markdown, chunks, images, raw output, tokens, errors | Preserving multiple views of a result          |
| `chandra_vllm`     | Launch a configured vLLM serving environment                      | Multi-request GPU inference                    |
| `chandra_app`      | Local interactive application                                     | Visual examination of individual pages         |
| Output utilities   | Parse model HTML and crop detected figures                        | Semantic segmentation and image extraction     |

`InferenceManager.generate()` returns an output for each input page. The result exposes `markdown`, `html`, `chunks`, `raw`, `images`, `page_box`, `token_count`, and an `error` flag. This makes it possible to retain the original generated representation alongside the postprocessed forms, rather than losing information at the first serialization boundary.

The `ocr_layout` prompt requests spatially annotated, semantically classified HTML, while the simpler `ocr` mode serves a less spatially structured transcription use case. For integration with Docling's dedicated parser, the layout-aware prompt is the appropriate contract.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



### 3.2 Standalone local deployment

The vendor-documented execution paths are:

```
# Python package and vLLM-client-based workflow
pip install chandra-ocr

# Launch the vendor-configured local vLLM container
chandra_vllm

# Process a document using that server
chandra input.pdf ./output --method vllm
```

Or, to run the Hugging Face inference backend in the Python environment:

```
pip install "chandra-ocr[hf]"
chandra input.pdf ./output --method hf
```

The supported CLI includes PDF page ranges, batching, worker concurrency, maximum output tokens, figure extraction, and optional header/footer inclusion. Normal file outputs include Markdown, HTML, per-document metadata, and cropped images.

The default server endpoint is `http://localhost:8000/v1`; the default served-model alias in Datalab's launcher is `chandra`. These defaults become important when connecting Docling, because its preset uses a different API model identifier.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



### 3.3 Practical runtime characteristics

The reference deployment uses BF16 weights and a vLLM configuration with a model context limit of 18,000 tokens and a maximum image-processor pixel budget around 6.3 million pixels. Chandra's generation default is 12,384 output tokens per page.

This is a long-output, high-resolution vision-language workload. Performance depends on the input page's visual complexity, generated HTML length, image resolution, concurrent sequences, KV cache allocation, and GPU memory—not just parameter count.

Datalab calls the model 4B parameters, whereas Docling's preset metadata identifies it as 5.3B. The examined sources do not reconcile the counting convention. Consequently, neither number should be used alone to derive a precise memory requirement. BF16 weights for a nominal 4B-parameter model would occupy about 8 GB before runtime overhead, but this is only a lower-bound illustration, not a verified deployment memory requirement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab+1



## 4. Docling integration architecture

### 4.1 Chandra is a native VLM conversion preset, not a conventional OCR backend

In Docling 2.146.0, Chandra 2 is registered as `chandra_ocr2`. Its source-defined configuration includes:

| Preset property               | Value                                                       |
| ----------------------------- | ----------------------------------------------------------- |
| Preset identifier             | `chandra_ocr2`                                              |
| Model repository              | `datalab-to/chandra-ocr-2`                                  |
| Response format               | `ResponseFormat.CHANDRA_HTML`                               |
| Prompt                        | `CHANDRA_OCR_LAYOUT_PROMPT`                                 |
| Maximum generated tokens      | `12384`                                                     |
| Default engine                | `AUTO_INLINE`                                               |
| Transformers configuration    | Image-text-to-text, BF16, chat-style prompting              |
| In-process vLLM configuration | Includes eager execution override                           |
| API integrations              | Generic/OpenAI-compatible, Ollama, LM Studio configurations |
| Model-code requirement        | Preset declares `trust_remote_code=True`                    |

This is a fully registered model configuration, not merely a documentation suggestion. The preset is defined in `docling/datamodel/stage_model_specs.py`, and the Chandra-specific parser is documented as part of the VLM pipeline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

github.com+2



Source: `https://github.com/docling-project/docling/blob/main/docling/datamodel/stage_model_specs.py`

The critical distinction: Selecting `chandra_ocr2` means selecting `VlmPipeline`, not passing Chandra as a drop-in option to the standard PDF pipeline's `ocr_options`.

|                             | Docling standard PDF pipeline                           | Docling + Chandra VLM pipeline                               |
| --------------------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| Primary text source         | PDF text layer and/or specialized OCR                   | Generated interpretation of rendered page                    |
| Layout recognition          | Dedicated layout detection model                        | Chandra's structured output                                  |
| Table reconstruction        | Dedicated table-structure recognition                   | Chandra-generated table markup                               |
| Equations, charts, diagrams | Separate recognition or enrichment stages as configured | May be expressed by Chandra within the initial page response |
| PDF text fidelity           | Can preserve backend-extracted text where available     | Retranscribes the page visually                              |
| Native result               | `DoclingDocument`                                       | `DoclingDocument`                                            |
| Typical constraint          | Coordination among specialized stages                   | VLM generation cost and output-format reliability            |

A VLM is not inherently superior for all PDFs. Born-digital documents with reliable text layers can benefit from direct text extraction, while difficult scanned documents, mixed handwriting, scientific figures, and intricate layouts are situations in which Chandra's page-level interpretation is more distinctive.

### 4.2 Conversion to `DoclingDocument`

Docling maps Chandra's generated structure into its Pydantic-backed document model. The resulting object can contain text, tables, pictures, groups, document hierarchy, source-page provenance, and separate main-body and document-furniture content.

This establishes a reusable representation for later serialization, enrichment, and chunking. The representation is independent of whether a specialized OCR engine or a VLM created the content.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



The Chandra parser handles several nontrivial cases:

| Chandra source                          | Docling interpretation                                |
| --------------------------------------- | ----------------------------------------------------- |
| Nested HTML lists                       | Structured list/group hierarchy                       |
| Table with merged cells                 | Table with row and column spans                       |
| Rich formatting inside a cell           | `RichTableCell`-based structured content              |
| Mathematical markup                     | Mathematical content retained in its document context |
| Image `alt` description                 | `PictureItem.meta.description`                        |
| Chart table within picture              | Content nested beneath the picture                    |
| Mermaid diagram content                 | Diagram content associated with the picture           |
| `<chem>` content                        | SMILES-related molecular metadata                     |
| Forms with checked or selected controls | Form elements and states                              |
| Page headers and footers                | Document-furniture semantics where represented        |

Some qualifications are central to interpreting this mapping correctly.

Form labels and values: Docling preserves explicit form structure, but its Chandra parser does not invent key–value links based on visual proximity. A relationship Chandra may have expressed through surrounding HTML can therefore require inspection of the nested structure rather than assuming it appears as a canonical key-value object.

Captions: Nested captions can be associated with their containing table or picture. Independent caption blocks are not automatically attached based on spatial proximity.

Table continuations: Two separately generated tables are not automatically recognized as one logical table spanning multiple pages.

Figures: Chart data and Mermaid descriptions may remain nested below picture objects. A consumer that reads only paragraph text or top-level tables can miss them entirely.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 4.3 Output preservation is an architectural choice

A practical distinction exists among the available output forms.

| Output                 | Main strengths                                                     | Potential losses                                                  |
| ---------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| Raw Chandra HTML       | Original layout labels, HTML structure, normalized boxes           | Not a canonical Docling object model                              |
| Native Chandra chunks  | Label, bbox, content, page-level extraction detail                 | Separate from Docling's cross-page hierarchy                      |
| `DoclingDocument` JSON | Document objects, hierarchy, metadata, provenance, figure children | Some model-specific raw generation detail may not be represented  |
| Docling Markdown       | Readable text and tables, suitable for common downstream uses      | Rich metadata and nested figure content may be omitted by default |
| Plain text             | Fast text-oriented consumption                                     | Most layout, graphical, and structural semantics                  |

For high-fidelity document intelligence, JSON is generally the more expressive Docling serialization. Markdown remains valuable but should not be treated as an exhaustive representation of everything the model recognized.

Docling explicitly recommends using `traverse_pictures=True` when exporting Markdown if picture children need to be included, and retaining page or picture images if subsequent pixel-level inspection is required.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



## 5. Deploying Chandra 2 inside Docling

The following configurations are source-grounded implementation examples, not commands executed or benchmarked in this research.

### 5.1 Simplest local Docling deployment

Install Docling with the VLM dependencies:

```
pip install "docling[vlm]"
```

Run its Chandra preset against a PDF:

```
docling convert input.pdf \
  --pipeline vlm \
  --vlm-model chandra_ocr2 \
  --trust-remote-code \
  --to json
```

The CLI flag enables execution of code supplied by the model repository, a relevant consideration because the Chandra preset declares that requirement. Review and pin trusted model code before allowing it in an untrusted environment.

For native-output troubleshooting, Docling also exposes `--debug-vlm-native-output`, which writes the underlying page responses for inspection.

The `chandra_ocr2` preset must be explicit; Docling's default VLM preset is `granite_docling`, not Chandra.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



### 5.2 Python: local Transformers execution

The following selects the Chandra preset and explicitly uses Docling's Transformers inference engine.

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.pipeline_options import (    VlmConvertOptions,    VlmPipelineOptions,)from docling.datamodel.vlm_engine_options import (    TransformersVlmEngineOptions,)from docling.document_converter import DocumentConverter, PdfFormatOptionfrom docling.pipeline.vlm_pipeline import VlmPipelinevlm = VlmConvertOptions.from_preset(    "chandra_ocr2",    engine_options=TransformersVlmEngineOptions(        trust_remote_code=True,        load_in_8bit=False,    ),)options = VlmPipelineOptions(    vlm_options=vlm,    generate_page_images=True,    generate_picture_images=True,)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(            pipeline_cls=VlmPipeline,            pipeline_options=options,        )    })result = converter.convert("input.pdf")print(result.status)
```

This example explicitly disables the Transformers engine's default 8-bit loading option to keep the model in its preset's intended BF16 configuration, subject to the selected runtime's support. Quantized deployments can be viable, but compatibility and quality should not be assumed solely from the existence of a quantization flag.

The main benefit of this configuration is deployment simplicity: Docling owns document conversion and VLM inference in one Python process. Its disadvantage is that model loading, GPU allocation, and inference are coupled to the document-processing process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 5.3 Python: local vLLM server with Docling as the client

For serving the model independently, the architecture is:

Docling process

PDF loading, rendering, page requests, Chandra HTML parsing, document assembly, export

vLLM server

Chandra model weights, GPU inference, model batching, OpenAI-compatible chat endpoint

Page images and generated HTML over local HTTP

First, start the Datalab-provided vLLM launcher with the model name Docling's preset expects:

```
VLLM_MODEL_NAME=datalab-to/chandra-ocr-2 chandra_vllm
```

Alternatively, serve the official checkpoint using a compatible vLLM installation and ensure that the exposed model identifier matches the client request. Datalab's launcher handles a number of Chandra-specific vLLM settings; a manually configured server should account for its context and image-resolution requirements.

Then configure Docling:

```
from docling.datamodel.base_models import InputFormatfrom docling.datamodel.pipeline_options import (    VlmConvertOptions,    VlmPipelineOptions,)from docling.datamodel.vlm_engine_options import (    ApiVlmEngineOptions,    VlmEngineType,)from docling.document_converter import DocumentConverter, PdfFormatOptionfrom docling.pipeline.vlm_pipeline import VlmPipelinevlm = VlmConvertOptions.from_preset(    "chandra_ocr2",    engine_options=ApiVlmEngineOptions(        engine_type=VlmEngineType.API,        url="http://127.0.0.1:8000/v1/chat/completions",        params={            "model": "datalab-to/chandra-ocr-2",            "max_tokens": 12384,        },        concurrency=4,        timeout=600,    ),)options = VlmPipelineOptions(    enable_remote_services=True,    vlm_options=vlm,    generate_page_images=True,    generate_picture_images=True,)converter = DocumentConverter(    format_options={        InputFormat.PDF: PdfFormatOption(
```

Several details are easy to overlook:

1. `enable_remote_services=True` is necessary for Docling's API inference path, even when the endpoint is on `localhost`.
2. The vLLM model alias must agree with `params["model"]`. Datalab's launcher ordinarily exposes `chandra`, while the Docling Chandra preset normally specifies `datalab-to/chandra-ocr-2`.
3. `VlmEngineType.API` selects the generic API path. The explicit endpoint avoids accidentally targeting a cloud provider's default endpoint.
4. Chandra needs a sufficiently large generation limit to return the complete annotated HTML. Setting a much smaller limit can turn otherwise valid pages into truncated or invalid document output.
5. API concurrency should reflect GPU serving capacity. More concurrent page requests do not imply better performance if image preprocessing, prefill, decoding, or memory utilization is already saturated.

These are the relevant current interfaces: `VlmConvertOptions.from_preset`, `ApiVlmEngineOptions`, `VlmPipelineOptions`, and `PdfFormatOption`. Older examples using `InlineVlmOptions` or the original `ApiVlmOptions` remain useful for understanding the history, but should not be combined casually with the newer preset-oriented configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



Direct source: `https://docling-project.github.io/docling/_generated/examples/vlm_pipeline_api_model/`

## 6. Advanced capability interactions

### 6.1 Chandra's figure extraction and Docling's enrichment stages

There are two complementary ways to derive information about charts, figures, and diagrams.

Chandra can generate interpretations while recognizing the page. Docling can subsequently classify and enrich picture objects using dedicated models. These operations overlap, but they are not identical.

| Function                        | Chandra 2                                    | Docling companion capability                                                    |
| ------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------- |
| Identify image regions          | Layout labels and bounding boxes             | Picture objects with provenance                                                 |
| Describe visual content         | Generated descriptions and `alt` text        | Picture-description enrichment                                                  |
| Categorize figures              | Generated semantic content and layout labels | Dedicated picture-classification model                                          |
| Extract chart values            | Generated chart data and axes                | Chart-extraction VLM stage                                                      |
| Reconstruct diagrams            | Mermaid and descriptive content              | Structured content retention; no general Mermaid-to-graph conversion guaranteed |
| Extract original picture pixels | Chandra crop utilities                       | Page/picture image retention and provenance-based cropping                      |

Docling's chart-enrichment pipeline classifies figures before attempting chart extraction and avoids re-extracting fields already present in the VLM output where supported. This is significant: recognizing a diagram or chart once does not necessarily require rerunning another complete document-understanding model, but additional specialized inference can be useful when the initial output is incomplete.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



A key limitation is that Docling does not automatically make every Chandra-generated scientific interpretation a first-class typed scientific object. For example, diagram code may be stored as content beneath a `PictureItem`, rather than as graph-node and graph-edge instances.

Likewise, a chart table stored beneath a picture is not necessarily equivalent to a top-level `TableItem`.

This means that the model may have recognized more information than a downstream consumer receives if that consumer examines only conventional text and table collections.

### 6.2 Document structure and semantic retrieval

Once Chandra's output enters a `DoclingDocument`, several Docling capabilities become available independently of the original OCR model:

Document hierarchy. Headings, nested groups, lists, page numbers, and reading order can supply context for downstream information retrieval.

Provenance. Source-page references and available bounding boxes can locate an extracted statement, chart, or table in its original document.

Structure-aware chunking. `HybridChunker` can operate on Docling's document objects instead of splitting an exported Markdown string. It can use document hierarchy and tokenizer constraints, and Docling provides table-aware chunking behavior such as repeated headers.

Framework integration. Docling's object model can feed retrieval, extraction, and generative AI systems through integrations and serializers without requiring each downstream tool to implement Chandra's HTML layout protocol.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+1



These capabilities make the Chandra–Docling combination especially relevant for technical documentation where a paragraph's meaning depends on its section, a table's column headings, or an adjacent figure.

The associated opportunity is architectural rather than automatic: preserving richer representations permits more sophisticated downstream processing, but the application must still select consumers capable of using that structure.

### 6.3 Structured diagrams, graph querying, and scientific knowledge

Chandra's Mermaid reconstruction provides a useful intermediate form for flowcharts and process diagrams.

For example, a recognized diagram containing a decision, two branches, and downstream actions may become:

\#chatgpt-mermaid-\_r_79g\_{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;fill:rgb(255, 255, 255);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_79g\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_79g\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_79g\_ .error-icon{fill:rgba(255, 255, 255, 0.03);}#chatgpt-mermaid-\_r_79g\_ .error-text{fill:rgb(255, 255, 255);stroke:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_79g\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_79g\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_79g\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_79g\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_79g\_ .marker{fill:rgba(255, 255, 255, 0.498);stroke:rgba(255, 255, 255, 0.498);}#chatgpt-mermaid-\_r_79g\_ .marker.cross{stroke:rgba(255, 255, 255, 0.498);}#chatgpt-mermaid-\_r_79g\_ svg{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;}#chatgpt-mermaid-\_r_79g\_ p{margin:0;}#chatgpt-mermaid-\_r_79g\_ .label{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .cluster-label text{fill:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .cluster-label span{color:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_79g\_ .label text,#chatgpt-mermaid-\_r_79g\_ span{fill:rgb(255, 255, 255);color:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .node rect,#chatgpt-mermaid-\_r_79g\_ .node circle,#chatgpt-mermaid-\_r_79g\_ .node ellipse,#chatgpt-mermaid-\_r_79g\_ .node polygon,#chatgpt-mermaid-\_r_79g\_ .node path{fill:rgb(26, 40, 61);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .rough-node .label text,#chatgpt-mermaid-\_r_79g\_ .node .label text,#chatgpt-mermaid-\_r_79g\_ .image-shape .label,#chatgpt-mermaid-\_r_79g\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_79g\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .rough-node .label,#chatgpt-mermaid-\_r_79g\_ .node .label,#chatgpt-mermaid-\_r_79g\_ .image-shape .label,#chatgpt-mermaid-\_r_79g\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_79g\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_79g\_ .root .anchor path{fill:rgba(255, 255, 255, 0.498)!important;stroke-width:0;stroke:rgba(255, 255, 255, 0.498);}#chatgpt-mermaid-\_r_79g\_ .arrowheadPath{fill:rgba(255, 255, 255, 0.498);}#chatgpt-mermaid-\_r_79g\_ .edgePath .path{stroke:rgba(255, 255, 255, 0.498);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .flowchart-link{stroke:rgba(255, 255, 255, 0.498);fill:none;}#chatgpt-mermaid-\_r_79g\_ .edgeLabel{background-color:rgb(24, 24, 24);text-align:center;}#chatgpt-mermaid-\_r_79g\_ .edgeLabel p{background-color:rgb(24, 24, 24);}#chatgpt-mermaid-\_r_79g\_ .edgeLabel rect{opacity:0.5;background-color:rgb(24, 24, 24);fill:rgb(24, 24, 24);}#chatgpt-mermaid-\_r_79g\_ .labelBkg{background-color:rgba(24, 24, 24, 0.5);}#chatgpt-mermaid-\_r_79g\_ .cluster rect{fill:rgba(255, 255, 255, 0.03);stroke:rgba(255, 255, 255, 0.082);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .cluster text{fill:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ .cluster span{color:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:12px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.082);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_79g\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(255, 255, 255);}#chatgpt-mermaid-\_r_79g\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_79g\_ .icon-shape,#chatgpt-mermaid-\_r_79g\_ .image-shape{background-color:rgb(24, 24, 24);text-align:center;}#chatgpt-mermaid-\_r_79g\_ .icon-shape p,#chatgpt-mermaid-\_r_79g\_ .image-shape p{background-color:rgb(24, 24, 24);padding:2px;}#chatgpt-mermaid-\_r_79g\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_79g\_ .image-shape .label rect{opacity:0.5;background-color:rgb(24, 24, 24);fill:rgb(24, 24, 24);}#chatgpt-mermaid-\_r_79g\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_79g\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_79g\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_79g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_79g\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_79g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_79g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_79g\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_79g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_79g\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(232, 232, 232);}#chatgpt-mermaid-\_r_79g\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(232, 232, 232);}#chatgpt-mermaid-\_r_79g\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_79g\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_79g\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(19, 19, 19);stroke:rgb(47, 47, 47);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .node rect,#chatgpt-mermaid-\_r_79g\_ .node circle,#chatgpt-mermaid-\_r_79g\_ .node ellipse,#chatgpt-mermaid-\_r_79g\_ .node polygon,#chatgpt-mermaid-\_r_79g\_ .node path{fill:rgb(24, 24, 24);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_79g\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_79g\_ .mermaid-decision .label-container{fill:rgb(19, 19, 19);stroke:rgb(47, 47, 47);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_79g\_ .edgePaths .flowchart-link{stroke:rgba(255, 255, 255, 0.498);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_79g\_ .marker{fill:rgba(255, 255, 255, 0.498);stroke:rgba(255, 255, 255, 0.498);}#chatgpt-mermaid-\_r_79g\_ :root{--mermaid-font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}Measure process variableWithin operating range?Continue operationInvestigate deviationYesNo

This example is illustrative, not generated from a document.

Mermaid makes the topology explicit, but it is still a representation of the model's interpretation. If a system needs to query graph relationships, it may parse the Mermaid into nodes and edges, retain the original image provenance, and associate each recovered relationship with the source document.

That conversion is not a native Chandra graph database, nor a graph-querying feature of Docling. It is an integration possibility enabled by the structured diagram output.

Similar distinctions apply to charts and scientific formulas. Chandra can produce machine-readable data and notation; establishing units, valid dimensions, chemical correctness, semantic equivalence, or relationships to a domain ontology is a separate validation and modeling concern.

### 6.4 Local model inference versus richer hosted processing

Datalab's hosted API advertises capabilities beyond the locally released model, including document extraction and classification workflows and optional processing enhancements. Its Chandra 2 announcement also describes API-specific features such as table-row bounding boxes, digital-PDF hyperlink extraction, and infographic-oriented processing.

Those extras belong to the Datalab API service, not necessarily to the public `chandra-ocr` Python package or to Docling's `chandra_ocr2` preset.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab



This boundary is important when evaluating feature descriptions: an API demonstration may use different weights, postprocessing, image enhancements, or classification services from the public checkpoint.

## 7. Correctness, failure handling, and information-loss boundaries

### 7.1 What happens when a Chandra response is imperfect?

Docling's dedicated Chandra parser has explicit recovery behavior.

| Condition                                       | Documented Docling behavior                               |
| ----------------------------------------------- | --------------------------------------------------------- |
| Valid Chandra HTML and bounding boxes           | Parse structure and scale spatial coordinates             |
| Recognizable HTML without layout blocks         | Recover content with a warning; do not invent coordinates |
| Invalid bounding box                            | Warn and retain the associated content                    |
| Nonempty prose or JSON instead of expected HTML | Record page-level inference error                         |
| Invalid page-level response                     | Can produce `PARTIAL_SUCCESS`                             |
| Explicitly labeled blank page                   | Empty page content is permitted                           |
| Separate table fragments                        | Preserve as distinct tables rather than guessing a merge  |
| CSS-only layout relationships                   | Not reconstructed into corresponding document primitives  |

These are meaningful failure semantics. They make incomplete conversions observable instead of silently treating every generation as a valid document.

However, syntactically valid output is not evidence that the page has been recognized faithfully. A VLM may produce plausible but incorrect text, a numerically wrong chart value, an omitted connector, or an incorrect table span while still generating valid HTML.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.2 Fidelity dimensions should be assessed independently

For technical and scientific documents, OCR accuracy alone is an incomplete measure.

| Dimension            | Example of a consequential failure                                      |
| -------------------- | ----------------------------------------------------------------------- |
| Transcription        | Misread numerical value, symbol, subscript, or Greek character          |
| Reading order        | Multi-column paragraphs interleaved                                     |
| Structure            | A heading interpreted as text or a caption attached to the wrong object |
| Table topology       | Wrong `rowspan`, `colspan`, or hierarchical header                      |
| Mathematics          | Correct-looking LaTeX with a missing exponent or operator               |
| Chart reconstruction | Estimated series values treated as exact observations                   |
| Diagram graph        | Missing decision edge or incorrect connection direction                 |
| Chemistry            | Invalid or chemically different SMILES string                           |
| Spatial alignment    | Bounding box placed over the wrong region                               |
| Completeness         | Output truncated before the final sections or table rows                |

The first five dimensions overlap with the model's general document-understanding benchmarks. Chart, graph, and scientific-semantic correctness require additional task-specific evaluation; an aggregate OCR score does not establish those guarantees.

### 7.3 Operational failure modes

Chandra's native inference manager has retry-related configuration for vLLM errors and repeated-token behavior, including retry settings and sampling changes.

Docling's generic VLM API integration is a different execution layer. It should not be assumed to reproduce every retry or recovery mechanism implemented inside Chandra's standalone `InferenceManager`.

Relevant operational distinctions include:

- Generation truncation: Dense pages can exceed the completion-token budget or the combined input/output context limit.
- Repetition: Generative OCR can enter repeated-text loops. Chandra 2.5 specifically reports improvements in this area compared with hosted Chandra 2.4.
- Page independence: The Docling VLM pipeline operates on page images, so multi-page table continuation and cross-page semantic relationships are not guaranteed to be reconciled.
- Image scaling: Resolution affects tiny text, diagrams, and formulas, but higher resolution increases vision-token and preprocessing costs.
- Partial success: A usable `DoclingDocument` may still contain page-specific errors or omitted regions.
- Lossy export: A successful conversion followed by an overly simple serialization can discard valid recognized information.

The safest interpretation of `ConversionResult.status` is as pipeline execution status, not a calibrated model-confidence measure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling+2



## 8. Performance and deployment tradeoffs

### 8.1 Published Chandra 2 performance

Datalab reports the following local-model measurements using vLLM on a single NVIDIA H100 80 GB, with documents sampled from the olmOCR benchmark and 96 concurrent sequences.

Measured throughput

# 1.44

Pages per second

Average page latency

# 60 s

156 s at p95

The vendor also estimates approximately 2 pages per second for more representative real-world workloads. That estimate and the measured 1.44 pages/sec benchmark are not interchangeable.

High aggregate throughput is achieved through concurrency. It does not mean an individual page takes half a second to complete.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 8.2 Chandra OCR benchmark results

Datalab reports the following for open Chandra 2:

| Evaluation                                | Reported result | Interpretation                              |
| ----------------------------------------- | --------------- | ------------------------------------------- |
| olmOCR-bench overall, original evaluation | 85.9%           | Aggregate document recognition              |
| ArXiv category                            | 90.2%           | Technical and mathematical documents        |
| Old scans math                            | 89.3%           | Mathematics from degraded material          |
| Tables                                    | 89.9%           | Table-related benchmark tests               |
| Multi-column                              | 83.5%           | Ordering/layout performance                 |
| Internal 43-language average              | 77.8%           | Multilingual evaluation                     |
| Internal 90-language average              | 72.7%           | Broader, more challenging language coverage |

Scores vary substantially by language: for example, the vendor's internal evaluation reports German at 94.8%, Arabic at 68.4%, and Urdu at 43.2%.

These are Datalab's published evaluations, with model-specific postprocessing and the methodologies described in its materials. They are not measurements of Chandra running through Docling, and they do not certify diagram connectivity, chart-value accuracy, or downstream semantic classification.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://app.datalab.to\&sz=32)

Datalab+1



### 8.3 Deployment choices

| Deployment form                          | Main benefit                                                 | Main cost or condition                                                   |
| ---------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Chandra CLI + Hugging Face               | Simple local batch execution                                 | Per-process model lifecycle and limited serving orchestration            |
| Docling + Transformers                   | Unified local document pipeline                              | Coupled model loading, memory, and conversion                            |
| Chandra vLLM server + Docling API client | Independent model serving and concurrency management         | GPU-server operations, network boundary, alias/configuration alignment   |
| Docling Serve wrapping VLM conversion    | Document-processing API for multiple clients                 | An additional service layer and resource scheduling                      |
| Datalab hosted API                       | Managed recognition and newer hosted capabilities            | External-service boundary, API-specific output schemas, commercial terms |
| Commercial on-premises Datalab offering  | Potential access to newer licensed deployment configurations | Availability and configuration depend on vendor agreement                |

The relative performance of these configurations has not been established by the reviewed public sources. In particular, there is no sound basis for multiplying the H100 Chandra benchmark by a Docling concurrency setting or transferring it directly to other GPUs.

An important model-specific point: Docling's Chandra preset has an in-process vLLM override (`enforce_eager=True`), while Datalab's separately launched vLLM service has its own serving configuration. These are different execution environments; their memory usage and throughput should not be presumed identical.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

github.com+1



## 9. Chandra 2 versus Chandra 2.5: capability and availability boundary

Chandra 2.5 is relevant because it sharpens exactly the advanced structured-extraction capabilities for which Chandra is distinctive.

### 9.1 Structured image descriptions in Chandra 2.5

Datalab's October 14 release introduces a consistent six-field representation for figures in the hosted API's JSON and chunks output.

| Field         | Semantics                                                      |
| ------------- | -------------------------------------------------------------- |
| `alt`         | Short classification/subject label, up to 20 words             |
| `text`        | Verbatim figure text not already represented elsewhere         |
| `axes`        | Axis titles and units                                          |
| `data`        | Chart data as HTML tables; approximated values marked with `~` |
| `mermaid`     | Diagram nodes, edges, and labels                               |
| `description` | Short description grounded in visible content                  |

Nonapplicable fields are `null`. Unlike an unstructured description, this provides a stable schema across charts, photographs, and diagrams.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.datalab.to\&sz=32)

Datalab



That distinction is especially useful for consumers that need to treat a diagram, chart, or scientific illustration as data rather than as prose.

For example, the explicit approximation marker in `data` communicates a scientifically consequential distinction: a value read off a graphical axis is not necessarily an exact underlying measurement.

### 9.2 What improved, and what has not been released

Datalab reports 38% fewer repetition loops compared with hosted Chandra 2.4 and a 40–43% reduction in median API latency across its three service modes. These are hosted 2.5 versus hosted 2.4 comparisons, not benchmarks of the downloadable Chandra 2 model on the same hardware.

The vendor also reports an olmOCR-bench result of 87.4 for 2.5 versus 86.2 for open Chandra 2 using LightOn PP3 postprocessing. With each model's own postprocessing, the figures are 86.9 and 85.8. The same methodology must be used to interpret a meaningful comparison.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.datalab.to\&sz=32)

Datalab



As of the research date, publicly confirmed availability is:

- Open Chandra OCR 2 weights: downloadable and self-hostable.
- Chandra 2.5: available through Datalab's hosted API, with on-premises access handled commercially.
- Docling `chandra_ocr2`: targets the public Chandra OCR 2 checkpoint, not 2.5.

No public Chandra 2.5 checkpoint was verified. Additionally, the Docling Chandra parser expects layout HTML; it should not be assumed to understand the new hosted API's six-field `image` objects automatically. A hosted-API integration would require a compatible response path or a separate adaptation layer to preserve that schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.datalab.to\&sz=32)

Datalab+1



## 10. Licensing, security, and compatibility

### Model licensing is separate from package licensing

The Chandra Python code is Apache-2.0 licensed, but the public model weights use a modified OpenRAIL-M license.

Datalab describes free use for research, personal use, and startups below its stated $2 million funding/revenue threshold; it also restricts uses competing with its API and offers broader commercial licensing. These are material terms to examine before commercial or service deployment.

Docling's MIT license does not supersede the separate Chandra model-weight license.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face+1



### Runtime security

The relevant boundaries include model-code execution, incoming document content, generated HTML, retained files, and model-serving endpoints.

The Chandra preset requires consideration of `trust_remote_code`, which permits Python code supplied by the model repository to execute in the local inference environment. Model revision pinning and code review are therefore meaningful safeguards.

Generated HTML and Mermaid content are also untrusted document-derived data. Validating or sanitizing content before rendering it in browsers or executing downstream transformations is a distinct security responsibility.

The presence of `enable_remote_services=True` permits network-based inference within Docling; it does not by itself mean the service is hosted externally. A local vLLM endpoint can retain inference on the same machine, while an actual remote service introduces its own data handling and access-control obligations.

## 11. Architectural synthesis

Chandra 2 and Docling combine two complementary abstractions:

Chandra supplies visual-to-structured interpretation. Its most distinctive value lies in recovering more than document text: layout categories, tables, mathematics, forms, graphical relationships, chart data, and scientific notation.

Docling supplies an interoperable document model. Its Chandra-specific converter maps supported structure into reusable typed objects, preserving hierarchy, provenance, figure metadata, and rich table content while providing serialization, enrichment, and chunking interfaces.

The major boundary is semantic completeness. Although the model can generate chart data, Mermaid, SMILES, and descriptive scientific content, Docling does not automatically transform these into fully validated domain objects, relational structures, or graph-queryable representations.

Consequently, the combination can eliminate substantial bespoke OCR, layout reconstruction, table parsing, document-hierarchy generation, and serialization machinery. It does not eliminate the need to distinguish exact versus inferred numerical data, verify scientific or diagram semantics, reconcile cross-page structures, or preserve model-specific information through export boundaries.

The decisive practical finding is that modern Docling already has a Chandra 2 preset and a dedicated Chandra HTML parser. A bespoke integration is not needed simply to use Chandra as a full-page document-recognition model. Custom extensions become relevant when the required output goes beyond Docling's current Chandra mapping—for example, canonical chart datasets, typed diagram graphs, specialized scientific classification, or the newer Chandra 2.5 hosted JSON schema.

## 12. Primary-source reference map

The most useful direct sources for further investigation are:

| Topic                                            | Primary URL                                                                                    |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Chandra 2 code, CLI, inference orchestration     | `https://github.com/datalab-to/chandra`                                                        |
| Chandra 2 model card, license, benchmarks        | `https://huggingface.co/datalab-to/chandra-ocr-2`                                              |
| Chandra Python package release                   | `https://pypi.org/project/chandra-ocr/`                                                        |
| Chandra's exact OCR prompts                      | `https://github.com/datalab-to/chandra/blob/master/chandra/prompts.py`                         |
| Chandra 2 capabilities and benchmarks            | `https://www.datalab.to/blog/chandra-2`                                                        |
| Chandra 2.5 changes and availability             | `https://www.datalab.to/blog/chandra-2-5`                                                      |
| Docling release 2.146.0                          | `https://pypi.org/project/docling/2.146.0/`                                                    |
| Docling VLM models and Chandra parsing semantics | `https://docling-project.github.io/docling/usage/vision_models/`                               |
| Docling Chandra preset definition                | `https://github.com/docling-project/docling/blob/main/docling/datamodel/stage_model_specs.py`  |
| Docling Chandra prompt                           | `https://github.com/docling-project/docling/blob/main/docling/datamodel/vlm_prompts.py`        |
| VLM engine configuration                         | `https://github.com/docling-project/docling/blob/main/docling/datamodel/vlm_engine_options.py` |
| Docling's API-backed VLM example                 | `https://docling-project.github.io/docling/_generated/examples/vlm_pipeline_api_model/`        |
| Docling pipeline options                         | `https://docling-project.github.io/docling/reference/pipeline_options/`                        |
| Docling document object model                    | `https://docling-project.github.io/docling/concepts/docling_document/`                         |
| Docling chunking model                           | `https://docling-project.github.io/docling/concepts/chunking/`                                 |
| Docling CLI reference                            | `https://docling-project.github.io/docling/reference/cli/`                                     |

Research boundary: The overview is based on current official documentation, published releases, primary model descriptions, and upstream source inspection. It does not claim that the illustrated deployment commands were executed or that performance was measured in a running Docling–Chandra environment.

# Chandra OCR 2 and Docling — Technical Addendum

Supplement to the original capability reference | Research date: November 3, 2026 (US Eastern)

Version scope: Chandra OCR 2 public checkpoint (`datalab-to/chandra-ocr-2`), `chandra-ocr` Python package 0.2.0, and Docling 2.146.0. The document distinguishes released functionality, experimental runtime features, and capabilities exposed by companion libraries.

This addendum addresses the previously identified gaps without repeating the original overview of OCR functionality, scientific content recognition, or the basic Chandra–Docling integration.

Its principal additions concern four areas: model architecture and inference, image and document preprocessing, fidelity of Docling's structured representation, and operational deployment and diagnostics.

## 1. Model architecture and inference mechanisms

### 1.1 Qwen3.5 multimodal foundation

Chandra OCR 2 is built on a Qwen3.5 multimodal architecture. Its published checkpoint identifies `Qwen3_5ForConditionalGeneration`, combining a vision encoder with a hybrid-attention language model.

The checkpoint configuration exposes several architectural characteristics relevant to document processing.

| Component                      | Published configuration                                            | Technical significance                                                  |
| ------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Language model                 | 32 transformer layers                                              | Autoregressive generation of document markup                            |
| Attention topology             | Three linear-attention layers followed by one full-attention layer | Hybrid treatment of contextual information                              |
| Hidden dimension               | 2,560                                                              | Affects model computation and activation size                           |
| Attention heads                | 16 query heads; 4 KV heads for full attention                      | Grouped-query attention characteristics                                 |
| Vision encoder                 | 24 layers, hidden dimension 1,024                                  | Visual feature extraction                                               |
| Vision patching                | Patch size 16, spatial merge size 2                                | Visual input is transformed into model tokens                           |
| MTP configuration              | One multi-token-prediction hidden layer                            | Support for assisted decoding                                           |
| Configured positional capacity | 262,144 positions                                                  | Architectural capacity, not a guarantee of practical OCR context length |
| Numerical precision            | BF16 specified for the text model                                  | Baseline precision for the published checkpoint                         |

The language model's attention pattern is explicitly represented in `config.json`: 24 linear-attention layers and eight full-attention layers, with full attention at every fourth layer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

datalab-to/chandra-ocr-2 at main



#### Architectural implications

Hybrid attention. Linear-attention mechanisms can reduce the growth of attention-state computation relative to conventional full attention, while periodic full-attention layers retain explicit token-to-token attention capabilities. This is valuable for document workloads that combine substantial visual input with long generated HTML.

However, the hybrid architecture does not establish that inference memory grows independently of sequence length. Full-attention KV state, other recurrent or convolutional state, vision tokens, activations, and implementation-specific buffers remain relevant.

Multimodal positional representation. The checkpoint uses multimodal rotary-position parameters alongside its vision configuration. The model is therefore not simply a text LLM receiving OCR text from an external detector; visual features participate directly in the generative inference process.

Practical sequence limits. The published positional capacity must be distinguished from runtime limits. Datalab's reference vLLM launcher uses `--max-model-len 18000`, imposing a much smaller configured execution window. Long, dense pages must accommodate both input and generated tokens within the serving configuration.

These distinctions explain why the same checkpoint can behave differently under Transformers, vLLM, and quantized inference engines, even if the output prompt is unchanged.

Primary sources:

`https://huggingface.co/datalab-to/chandra-ocr-2/blob/main/config.json`

`https://github.com/datalab-to/chandra/blob/master/chandra/scripts/vllm.py`

### 1.2 Multi-token prediction and speculative decoding

The Chandra checkpoint includes an MTP head, which can support speculative token generation.

Conventional autoregressive decoding ordinarily requires a sequential model step for each next token. MTP-based speculative decoding proposes additional tokens and uses verification to accept valid predictions, potentially reducing sequential decoding overhead.

This matters for Chandra because its outputs can be large. A page containing nested tables, detailed mathematical expressions, and annotated layout elements can require thousands of generated tokens.

The native launcher exposes an optional execution path:

```
chandra_vllm --mtp
```

Its current implementation supplies vLLM with the following configuration:

```
{
  "method": "mtp",
  "num_speculative_tokens": 1
}
```

This is experimental in the supplied launcher. Datalab disables MTP by default and explicitly identifies its vLLM integration as unstable. The existence of an MTP head does not establish that the installed vLLM build supports it correctly or that a particular workload will execute faster.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



The expected benefit depends on draft-token acceptance, verification overhead, implementation support, and batch characteristics. Highly repetitive document markup might offer opportunities for token prediction, but that is a workload-dependent inference rather than a published Chandra performance guarantee.

The distinction between native and Docling deployment is also important: enabling MTP in Datalab's standalone launcher does not automatically enable it in Docling's in-process vLLM backend. The two have separate engine configurations.

Source:

`https://github.com/datalab-to/chandra/blob/master/chandra/scripts/vllm.py`

### 1.3 Decoding behavior is not identical across inference backends

The model checkpoint, prompting, decoding, and postprocessing are separate components of recognition quality.

The native Chandra inference manager exposes decoding and execution controls including `temperature`, `top_p`, maximum output tokens, worker concurrency, request headers, and retry budgets.

Its vLLM path can detect certain repetition conditions and retry with adjusted sampling. The default temperature is zero, with higher values available during recovery. This provides an operational mechanism for escaping some repeated-generation failures rather than treating every initial response as final.

The Hugging Face path does not implement precisely the same API-request and retry behavior. Docling likewise supplies its own VLM execution machinery, which may handle completion limits and request errors differently.

Three properties must therefore be distinguished:

| Property                 | Determined by                                                       |
| ------------------------ | ------------------------------------------------------------------- |
| Model capability         | Checkpoint weights, architecture, learned behavior                  |
| Generation behavior      | Prompt, preprocessing, decoding settings, backend                   |
| Final extraction quality | Generated response, recovery, parsing, normalization, serialization |

Matching the checkpoint and prompt is necessary for meaningful deployment comparisons, but it is not sufficient to establish equivalent output or runtime behavior.

The native inference implementations are located under:

`https://github.com/datalab-to/chandra/tree/master/chandra/model`

In particular, `hf.py`, `vllm.py`, and `__init__.py` provide useful investigation points.

## 2. Image preprocessing, resolution, and spatial fidelity

### 2.1 Chandra's explicit image-size normalization

The native `scale_to_fit()` function performs model-oriented image normalization before inference.

Its default parameters are:

| Parameter                          | Value                  |
| ---------------------------------- | ---------------------- |
| Maximum reference image dimensions | 3072 × 2048            |
| Maximum pixel budget               | 6,291,456              |
| Minimum pixel budget               | 50,176                 |
| Dimension alignment                | Multiples of 28 pixels |
| Resampling method                  | Lanczos                |

The function calculates a scale factor to bring an image within its pixel budget, rounds dimensions to the model's 28-pixel grid, then reduces grid dimensions further if necessary to satisfy the maximum. Small images can be enlarged to the minimum pixel budget.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



A subtle point is that the maximum reference dimensions are used to establish a pixel-area budget, rather than independently enforcing an absolute width ceiling of 3072 and height ceiling of 2048 in every case.

This matters for pages with unusual aspect ratios, such as wide diagrams or long engineering illustrations.

### 2.2 Rasterization and normalization are different operations

When processing a PDF, there may be multiple image transformations:

1. PDF rendering converts vector text, embedded images, graphics, and visible annotations into a page image.
2. The document-processing pipeline chooses a page-image scale.
3. The model backend or processor normalizes images to its accepted visual-token budget.
4. Generated normalized bounding boxes are mapped back into page coordinates.

These operations are not equivalent, and the original high-resolution image need not be the image actually consumed by the model.

For example, rendering a page at 400 DPI cannot recover information lost in an original 100 DPI scan. Conversely, rendering vector text at a high resolution can preserve fine features before downscaling, but those details may still be lost when the model processor applies its pixel budget.

The important architectural boundary is between the retained source-page image and the effective model input.

An output bounding box correctly mapped to the original page does not establish that the underlying text was read at the original image's resolution.

### 2.3 Detail loss in scientific and engineering documents

The pixel budget becomes especially consequential for visually dense material:

| Content type          | Potential effect of downscaling                                   |
| --------------------- | ----------------------------------------------------------------- |
| Mathematical notation | Loss of small exponents, subscripts, primes, and fraction bars    |
| Scientific charts     | Reduced separation between overlapping curves and markers         |
| Flowcharts            | Thin connectors, arrowheads, or small edge labels may disappear   |
| Engineering diagrams  | Small equipment tags and annotations can become indistinguishable |
| Chemical structures   | Bond types and stereochemical marks may be harder to distinguish  |
| Dense tables          | Adjacent characters and gridlines may merge                       |

These are consequences of image-resolution reduction, not documented guarantees of model failure.

For unusually detailed regions, region-level inference can offer an architectural alternative: presenting selected image crops at an effective resolution that preserves more local detail. However, neither Chandra's default CLI nor Docling's `chandra_ocr2` preset should be presumed to implement an automatic high-resolution scientific crop-and-reconciliation pipeline.

An additional crop pass changes the operation. It introduces region detection, coordinate mapping, duplicate handling, and reconciliation of local results with the original full-page hierarchy.

### 2.4 Spatial coordinate transformations

Chandra's annotated HTML uses normalized coordinates on a 0–1000 scale. Its native `parse_chunks()` converts these to image-pixel coordinates.

Docling instead interprets the normalized boxes relative to its source-page coordinate frame when producing document provenance.

The critical distinction is that coordinates are associated with annotated content blocks. A table or picture can have a region while its individual cells, words, or nested children have no independent coordinates.

Consequently:

- A document block's provenance supports localization of the entire recognized region.
- It does not imply independently grounded coordinates for each semantic object beneath that region.
- Reconstructing cell-level or word-level grounding would require more spatial evidence than the enclosing block alone.
- Conversions between rendered-image coordinates and PDF page coordinates must account for resolution and coordinate-system conventions.

Primary sources:

`https://github.com/datalab-to/chandra/blob/master/chandra/model/util.py`

`https://github.com/datalab-to/chandra/blob/master/chandra/output.py`

`https://docling-project.github.io/docling/usage/vision_models/`

## 3. Native document loading and postprocessing

### 3.1 PDF rendering and annotation flattening

Chandra's standalone input pipeline uses `pypdfium2` to render PDF pages. Before rendering, it initializes PDF forms and invokes PDFium's page-flattening facility for visible annotations and form fields.

The rendering resolution is not simply a fixed DPI. The implementation considers both its configured DPI and a minimum rendered-page dimension, increasing scale for small pages where necessary.

This has two consequences.

First, visible handwritten annotations, filled form widgets, and other rendered content may become recognizable because they appear directly in the rasterized page.

Second, flattening does not preserve those PDF objects as independently editable or semantically typed source objects. Chandra sees their visual appearance rather than receiving native PDF object identities.

The standalone Chandra loader and Docling's PDF backends should also be distinguished. Selecting Docling's `VlmPipeline` changes which component is responsible for rendering the document; it does not necessarily invoke Chandra's standalone PDF loader.

A small implementation caveat: the inspected Chandra `parse_range_str()` returns numeric page indices directly, and `load_pdf_images()` compares them with zero-based PDF page indices. This can differ from the one-based page-number convention used in other document-processing CLIs, including Docling. The implementation should be consulted before assuming that the same page-range string selects identical pages in both interfaces.

Source:

`https://github.com/datalab-to/chandra/blob/master/chandra/input.py`

### 3.2 Native output transformations and their information content

The output utilities expose several independent operations:

| Operation          | Mechanism                                                       | Consequence                                                  |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------------------ |
| `parse_html()`     | Filters layout blocks and transforms generated HTML             | Produces cleaner content but can exclude selected components |
| `parse_markdown()` | Converts normalized HTML with mathematical and formatting rules | Readable output, generally less expressive than source HTML  |
| `parse_layout()`   | Extracts labeled regions and scales coordinates                 | Spatially located layout blocks                              |
| `parse_chunks()`   | Serializes layout blocks as dictionaries                        | Convenient programmatic representation                       |
| `extract_images()` | Crops original-page regions corresponding to recognized figures | Retains image pixels independently of generated descriptions |

An easily missed distinction is that Chandra's `parse_html()` operates on the generated top-level layout blocks and returns their processed contents. It is not a transparent copy of the raw layout-annotated response.

Its filtering behavior includes excluding `Blank-Page` blocks, dropping page headers and footers unless requested, optionally removing images, replacing image references with generated filenames, and normalizing certain paragraph-like content.

Markdown generation then applies another transformation, including mathematical delimiters, heading conventions, superscript/subscript treatment, and escaping.

The original layout annotations should therefore not be presumed to survive unchanged into cleaned HTML or Markdown. The separately returned `chunks` and `raw` fields are important when access to the original representation is required.

`extract_images()` is likewise selective. It searches image and figure chunks for image tags and crops their bounding boxes from the source image. It is not a universal exporter of every region labeled as a diagram, chart, chemical structure, or other semantic class.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source:

`https://github.com/datalab-to/chandra/blob/master/chandra/output.py`

### 3.3 Native result errors versus semantic correctness

`BatchOutputItem` exposes an `error` field, but the distinction between the HF and vLLM execution paths is important.

The native HF generation implementation returns decoded generations with `error=False`; it does not provide a calibrated assessment of their correctness. The vLLM implementation converts certain request failures into failed result objects and can retry those failures or detected repetition.

This means an apparently successful response may still contain truncated, hallucinated, incomplete, or incorrectly structured material. Conversely, a failed remote request can be identified without requiring a valid transcription.

For downstream consumers, execution success, valid HTML, valid document structure, and faithful source recognition remain four independent properties.

Source:

`https://github.com/datalab-to/chandra/blob/master/chandra/model/`

## 4. Docling model presets and additional inference backends

### 4.1 The Chandra preset defines more than a model name

Docling's `VlmModelSpec` and `StageModelPreset` abstractions separate the model's identity, generation protocol, and inference-engine configuration.

The `chandra_ocr2` preset in Docling 2.146.0 contains:

| Property                     | Configuration                              |
| ---------------------------- | ------------------------------------------ |
| Model repository             | `datalab-to/chandra-ocr-2`                 |
| Pinned revision              | `af93b47dba1b47b6640c86ccf487ed2260ab9a09` |
| Response parser              | `ResponseFormat.CHANDRA_HTML`              |
| Prompt                       | `CHANDRA_OCR_LAYOUT_PROMPT`                |
| Page image scale             | `2.0`                                      |
| Maximum new tokens           | `12384`                                    |
| Generation stopping          | `<\\|im_end\\|>`, `<\\|endoftext\\|>`      |
| Model-code trust requirement | `trust_remote_code=True`                   |
| Default execution selection  | `AUTO_INLINE`                              |

The model specification also contains engine-specific repository choices, numerical-precision settings, processor behavior, and API model-name overrides.

The pinned revision is operationally important because Chandra's local model integration uses repository-supplied code. Pinning a revision creates a stable reference for reviewing that code and reproducing its behavior, rather than silently following future model repository changes.

This does not guarantee complete reproducibility across different Transformers, PyTorch, CUDA, vLLM, or Docling versions. It does, however, remove a substantial source of model-code variability.

Tagged source:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/datamodel/stage_model_specs.py`

### 4.2 MLX deployment on Apple Silicon

Docling's Chandra preset includes a platform-specific MLX model export.

| Setting                 | Value                                                                 |
| ----------------------- | --------------------------------------------------------------------- |
| Repository              | `mlx-community/chandra-ocr-2-oQ8`                                     |
| Checkpoint revision     | `eafcb4c79468ff6cf8b76ecc3aedbffe0dd82282`                            |
| Representation          | Community 8-bit conversion                                            |
| Minimum MLX-VLM version | `0.6.17`                                                              |
| Selection behavior      | Older incompatible MLX engines are skipped during automatic selection |

This path is distinct from the official BF16 checkpoint used by the Transformers configuration.

Docling's source indicates that the minimum MLX-VLM version is necessary for compatibility with the checkpoint's vision implementation. The preset explicitly documents that the MLX model is an 8-bit conversion rather than an official BF16 MLX export.

Why this matters: MLX offers local inference on Apple Silicon without requiring an NVIDIA GPU or separate vLLM server. However, the converted checkpoint introduces an independent artifact, compatibility requirements, and potential quantization-related differences in output quality.

The availability of an MLX export does not imply identical mathematical transcription, table reconstruction, or diagram recognition accuracy to the official BF16 model.

Primary sources:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/datamodel/stage_model_specs.py`

`https://huggingface.co/mlx-community/chandra-ocr-2-oQ8`

### 4.3 Local vLLM and remote API integrations are distinct

Docling's preset supports several inference-engine configurations, including local Transformers, local MLX, in-process vLLM, and API-backed execution.

Its in-process vLLM configuration specifies `enforce_eager=True`. Datalab's standalone vLLM launcher instead uses `--no-enforce-eager`, permitting a different execution strategy.

Neither configuration is universally faster. Eager execution, compilation, CUDA graph behavior, available memory, and model compatibility can influence latency and throughput.

A separate point concerns API model identifiers:

| API integration                    | Docling preset's model identifier |
| ---------------------------------- | --------------------------------- |
| OpenAI-compatible API              | `datalab-to/chandra-ocr-2`        |
| Ollama                             | `chandra-ocr-2`                   |
| Datalab's standalone vLLM launcher | `chandra` by default              |

The model identifier is part of the serving protocol, not necessarily the checkpoint's canonical repository name.

For an independently served model, the API client and server must agree on that identifier. Changing a served-model alias does not change which weights the server has loaded.

The broader benefit of Docling's model specification is that model-specific prompting, output interpretation, and engine-specific settings can be maintained together rather than duplicated across conversion callers.

### 4.4 GPU-aware vLLM launcher configuration

Datalab's `chandra_vllm` command provides named GPU profiles and scales two principal serving parameters based on configured VRAM.

Its baseline is an 80 GB H100, with:

- Maximum batched tokens: 8,192.
- Maximum concurrent sequences: 64.
- GPU memory utilization: 0.85.

For another configured GPU profile, the launcher proportionally scales the two batching settings, rounding batched tokens down to a power of two and maximum sequences down to a multiple of eight, subject to minimum values.

The launcher recognizes selected H100, A100, L40S, A10, L4, RTX 4090, RTX 3090, and T4 profiles.

This is a configuration heuristic, not a measured optimal scheduler and not a comprehensive GPU compatibility matrix. An accelerator missing from the profile list may still support the checkpoint through a separately configured inference engine.

Other launcher characteristics include BF16, prefix caching, an 18,000-token serving context, a 6.3-million-pixel processor budget, and a pinned vLLM Docker image (`vllm/vllm-openai:v0.17.0` in the inspected source).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



The configuration also uses NVIDIA container execution, exposes port 8000, mounts the Hugging Face cache, and enables host IPC sharing. These choices simplify model serving but create container, memory-sharing, filesystem, and endpoint-security considerations that are separate from OCR behavior.

The launcher uses `sudo docker run`; it should not be assumed to match every locally managed container or rootless deployment environment.

Source:

`https://github.com/datalab-to/chandra/blob/master/chandra/scripts/vllm.py`

### 4.5 Package extras and application tooling

The published Chandra package defines separate optional dependency sets.

| Installation       | Added capability                        |
| ------------------ | --------------------------------------- |
| `chandra-ocr`      | Base package and vLLM-client workflow   |
| `chandra-ocr[hf]`  | Local Transformers/PyTorch inference    |
| `chandra-ocr[app]` | Streamlit-based interactive application |
| `chandra-ocr[all]` | Combined optional dependencies          |

Its registered console entry points include `chandra`, `chandra_vllm`, `chandra_app`, and `chandra_screenshot`.

The application is useful for visual inspection of page-level recognition and layout. It should not be confused with Docling Serve: the former belongs to Chandra's local tooling; the latter exposes Docling document conversion as a service.

Source:

`https://github.com/datalab-to/chandra/blob/master/pyproject.toml`

## 5. Docling's Chandra HTML parser: advanced semantics and limits

### 5.1 Direct conversion of existing Chandra output

Docling exposes a Chandra-specific utility:

```
docling.utils.chandra_utils.parse_chandra_html(    content,    original_page_size,    page_no,    filename="file",    page_image=None,    *,    normalize_heading_levels=True,)
```

This can construct a `DoclingDocument` from an existing Chandra HTML response without invoking the model through Docling's `VlmPipeline`.

That capability is distinct from selecting `chandra_ocr2` for inference.

It separates three operations that are often unnecessarily coupled: model execution, interpretation of the model's output format, and serialization into the Docling document model.

For example, Chandra can run under its native inference manager or an independent model-serving process, while Docling can subsequently interpret a stored layout-annotated response.

The direct parser accepts the source-page dimensions and optionally the original page image. The dimensions establish the coordinate frame for bounding boxes; the image allows source imagery to be associated with the resulting document.

This is a useful integration boundary when inference and document construction have different execution lifecycles.

Qualification: `parse_chandra_html()` operates at page scope. It does not by itself reproduce every document-level operation performed by the full VLM pipeline. In particular, heading-level normalization can be deferred so the complete document's heading hierarchy is normalized consistently.

The function is available in the inspected 2.146.0 source, but it is an internal utility module rather than an independently versioned public compatibility contract.

Source:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/utils/chandra_utils.py`

### 5.2 Rich HTML and typed document reconstruction

Docling's parser recognizes more than Chandra's top-level `data-label` categories.

Its mapping supports inline formatting, hyperlink information, script positioning, code, mathematical markup, nested lists, form controls, tables, pictures, and associated metadata.

Important details include:

| HTML construct                       | Docling behavior                                |
| ------------------------------------ | ----------------------------------------------- |
| `<strong>`, `<em>`, and related tags | Preserve corresponding formatting               |
| `<sup>`, `<sub>`                     | Preserve superscript and subscript semantics    |
| `<a href=...>`                       | Preserve valid hyperlink targets                |
| `<math>`                             | Recognize mathematical content                  |
| `<code>`                             | Retain code-related semantics                   |
| `<input type="checkbox">`            | Record selected or unselected state             |
| `<input type="radio">`               | Record selection state                          |
| Text-like input fields               | Produce field-value content                     |
| Nested table-cell elements           | Use `RichTableCell` references when appropriate |
| `<img alt=...>`                      | Populate picture-description metadata           |
| `<chem>`                             | Populate molecular metadata when supported      |

`RichTableCell` is particularly significant. A cell can refer to structured document content, rather than containing only a flattened text string. This allows nested paragraphs, lists, and formatted content inside cells to survive in the document model.

The parser also handles malformed markup in selected cases, including some omitted closing tags. It is not a fully general browser HTML engine, and it does not reconstruct CSS layouts into equivalent document primitives.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.3 Table topology and the 1,000-cell limit

Docling reconstructs HTML table geometry using row and column offsets, spans, and header information.

It understands `thead`, `tbody`, `tfoot`, `th`, `scope`, `rowspan`, and `colspan`, including the HTML convention where `rowspan="0"` extends to the end of the applicable row group.

However, the Chandra parser defines:

```
_MAX_TABLE_GRID_CELLS = 1000
```

This bounds the expanded grid's size, not simply the number of explicit `<td>` elements. Merged cells contribute to the grid geometry through their spans.

The limit prevents excessively large or malformed table descriptions from producing unbounded grid expansion. It can also affect legitimate scientific tables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



A correction to the earlier gap analysis is important: when the table grid exceeds the limit, Docling does not necessarily reject the entire page or document. The 2.146.0 parser catches the size exception, records a warning, and preserves an empty `TableItem` instead of the oversized cell grid.

This prevents a single excessive table from destroying the surrounding document conversion. The tradeoff is that the table's cell content is not reconstructed in the resulting table object.

There is a separate recovery path for tables that parse with no cells: Docling can preserve their contents through ordinary child traversal.

These two conditions should not be conflated. A table rejected for exceeding the grid limit is materially different from a table whose markup contains no recognizable cells.

Source:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/utils/chandra_utils.py`

### 5.4 Diagram, chart, and chemical representations

Chandra's generated content can contain multiple semantic representations nested within a single visual region.

Docling's parser creates `PictureItem` objects for recognized images, figures, diagrams, and chemical blocks. It can attach generated descriptions and retain nested content.

For a recognized chart or diagram, this means a picture may include:

- A description in picture metadata.
- A table containing reconstructed chart values.
- Text representing diagram structure, such as Mermaid.
- Captions or other explicitly nested content.

The picture is still the containing document object. Nested chart data is not necessarily promoted to an independent top-level table, and Mermaid content is not automatically converted into a graph data model.

For chemical content, the parser can construct `MoleculeMetaField` metadata from an explicit `<chem>` element. The implementation's direct molecular metadata assignment applies when it finds exactly one such element within the relevant picture structure.

This is a narrower capability than identifying and validating arbitrary collections of molecules within a scientific document.

The distinction among generated description, typed metadata, and validated scientific semantics remains consequential. Docling preserves supported representations; it does not establish that every scientific value or relationship generated by Chandra is correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 5.5 Document-wide heading normalization

Chandra operates on page imagery, but document headings need consistent levels across pages.

Docling addresses this through document-wide heading normalization. It distinguishes document titles and section headers using the recognized layout labels, then considers the source heading depths when building the final hierarchy.

The normalization accounts for whether the document already contains first-level section headings and avoids collapsing every page's heading structure into an independent outline.

The distinction between `Title` and `Section-Header` is especially important because visual prominence alone does not reliably identify a document's logical title.

Direct calls to the page parser can normalize heading levels locally. The full VLM pipeline can instead defer normalization until the pages have been assembled into a document, allowing consistent treatment across page boundaries.

This is a useful example of functionality supplied by Docling's document-level processing rather than Chandra's page-level recognition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 5.6 Associative semantics the parser does not infer

Several relationships are preserved only when they are explicit in the model-generated structure.

| Relationship                                    | Documented behavior                                                   |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| Caption nested under a picture                  | Can be associated with the picture                                    |
| Caption nested under a table                    | Can be associated with the table                                      |
| Independent caption block                       | Not automatically linked by proximity                                 |
| Footnote nested within a supported parent       | Can be associated with that parent                                    |
| Form label beside a value                       | No automatic semantic key–value association based on visual proximity |
| Table continued on another page                 | No automatic cross-page table merge                                   |
| Separate diagrams with visually connected edges | No automatic cross-figure graph reconstruction                        |

These are intentional semantic boundaries, not necessarily recognition failures.

For example, Chandra may identify both a form label and its filled value. Docling preserving them as distinct elements does not mean it has established an unambiguous field-key relationship.

Likewise, a page-level diagram may contain correct Mermaid code, but the document model does not automatically infer whether a node in a separate figure represents the same real-world entity.

## 6. PDF-native extraction versus visual reconstruction

Docling's standard and VLM pipelines can both produce `DoclingDocument`, but they do not inherit identical source-information capabilities.

The VLM path primarily uses image-based interpretation. The standard pipeline can combine a native PDF text layer, OCR, dedicated layout recognition, and specialized table extraction.

This distinction is material for interactive PDF forms, annotations, fonts, hyperlinks, and machine-readable text.

### 6.1 AcroForm extraction

Docling's `--extract-form-fields` capability can recover native PDF form widgets and their field values in the supported standard and legacy pipelines using the `docling-parse` backend.

The CLI documentation explicitly scopes this capability to those pipelines, rather than the Chandra VLM path.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Chandra can recognize the visible appearance of a filled form, including selected checkboxes. But visual interpretation and native widget extraction provide different information.

For example, the visible label might be reconstructed as text, while a PDF-native form extraction can expose field identity and widget state through the original document representation.

This also illustrates why a visually perfect transcription is not necessarily a lossless PDF extraction.

### 6.2 Distinguishing native text from regenerated text

A born-digital PDF may contain high-quality selectable text with exact Unicode characters, font data, and object-level positioning.

Chandra regenerates text from its visual representation. That can be useful when the PDF text layer is corrupt or misleading, but it introduces another recognition step even when the existing text layer is accurate.

Docling's standard pipeline can use native PDF information where appropriate, while the Chandra VLM pipeline relies on its model-generated interpretation for the document transcription.

Combining both representations for cross-validation is architecturally possible, but it is not an automatic guarantee of the `chandra_ocr2` preset.

Such a combination requires explicit rules for handling disagreements, duplicate content, reading order, coordinates, and source provenance.

This distinction applies equally to scanned PDFs with embedded OCR layers: the existing text layer and Chandra's transcription may disagree, and neither should be treated as ground truth merely because it is machine-readable.

Source:

`https://docling-project.github.io/docling/reference/cli/`

## 7. Preserving structured information through serialization and chunking

### 7.1 Document conversion and chunk generation are separate semantic boundaries

The original overview identified the importance of retaining Docling JSON. An additional consideration is that subsequent chunking can exclude information even when the document model contains it correctly.

Docling's standard `HybridChunker` serialization normally skips text nested inside `PictureItem` objects.

This default is intentional. Text detected inside photographs, diagrams, and other pictures can be noisy, poorly ordered, or semantically misleading when flattened into prose.

For Chandra, however, picture children may contain meaningful chart tables, diagram representations, or other extracted scientific content.

Consequently, the default can omit valuable information from text chunks even when the conversion itself was successful.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



### 7.2 Custom chunk serialization

Docling allows chunk serialization to be customized through `ChunkingSerializerProvider`.

A concise illustration, adapted from its official example:

```
from docling_core.transforms.chunker import HybridChunkerfrom docling_core.transforms.chunker.hierarchical_chunker import (    ChunkingDocSerializer,    ChunkingSerializerProvider,)from docling_core.transforms.serializer.markdown import MarkdownParamsclass TraversePicturesProvider(ChunkingSerializerProvider):    def get_serializer(self, doc):        return ChunkingDocSerializer(            doc=doc,            params=MarkdownParams(traverse_pictures=True),        )chunker = HybridChunker(    serializer_provider=TraversePicturesProvider())chunks = list(chunker.chunk(document))
```

This changes which nested content is made available to text-oriented chunk consumers. It does not change the underlying recognized document.

The tradeoff is substantial. Docling's own example shows how enabling picture traversal can dramatically increase the amount of emitted text and produce noisy chunks for ordinary OCR images.

The relevant choice is therefore not simply maximum inclusion versus minimum inclusion. It is whether picture-child content is semantically useful and sufficiently reliable to be promoted into the text stream.

Source:

`https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/`

### 7.3 Preserving image provenance and original pixels

Docling can retain rendered pages and extracted pictures separately from their semantic descriptions.

The relevant mechanisms include `generate_page_images`, `generate_picture_images`, and `picture.get_image(document)`, together with image-export modes.

| Export mode   | Behavior                                                 |
| ------------- | -------------------------------------------------------- |
| `embedded`    | Embed image data in supported output formats             |
| `referenced`  | Store images separately and reference them               |
| `placeholder` | Retain a positional placeholder without the image pixels |

The choice affects output size, portability, and reproducibility of later visual inspection.

A structured record of a diagram containing Mermaid code is not a substitute for its source image when the extracted edges or labels need to be checked. Retaining page imagery and provenance provides a route back to the evidence.

This is particularly relevant where the model has converted graphical quantities into numbers, because the transformation may contain approximation or recognition error.

Source:

`https://docling-project.github.io/docling/reference/cli/`

### 7.4 Additional chunking mechanisms

Docling's advanced chunking utilities also provide `TreeChunkExpander` and `PageChunkExpander`.

These mechanisms allow a chunk to be expanded to its containing document item or page, respectively.

They are useful for document structures where a small text fragment does not carry sufficient context independently.

For example, an extracted table cell may need the table's hierarchical headers, and a diagram description may need surrounding text to explain its purpose.

Chunk expansion operates on the existing structured document. It does not re-run Chandra or recover information that was lost during recognition or parsing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



## 8. Diagnostics, failures, and operational control

### 8.1 Docling's VLM completion states

Docling's VLM runtime tracks inference stop reasons rather than relying exclusively on whether a response string is nonempty.

The 2.146.0 pipeline explicitly handles:

| Condition                                | Consequence                                          |
| ---------------------------------------- | ---------------------------------------------------- |
| `INFERENCE_ERROR`                        | Page-level inference error                           |
| `LENGTH`                                 | Generation stopped because of completion length      |
| `CONTENT_FILTERED`                       | Incomplete response due to filtering                 |
| Missing VLM prediction                   | Page-level error recorded                            |
| Valid-looking but malformed Chandra HTML | Parser-level recovery or error depending on content  |
| Document timeout                         | Timeout-related conversion failure or partial result |

The pipeline records errors in `ConversionResult.errors` and can report `PARTIAL_SUCCESS` when some pages are affected.

When every processed page has an explicit inference error and no usable output, the implementation can return `FAILURE` instead of treating the document as partially successful.

This distinction supports error-aware downstream processing. It prevents partial output from being silently treated as a complete conversion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/pipeline/vlm_pipeline.py`

### 8.2 Native VLM response capture

Docling 2.146.0's executable CLI source defines the flag:

```
docling convert input.pdf \
  --pipeline vlm \
  --vlm-model chandra_ocr2 \
  --trust-remote-code \
  --debug-vlm-native-output \
  --to json
```

The implementation writes page responses into the configured debug output path, under a `debug_<document>` directory, with filenames of the form `vlm_response_page_00001.txt`.

This is a useful independent inspection mechanism: it allows the raw generated response to be compared with the parsed `DoclingDocument`.

Documentation discrepancy: The corresponding `docs/reference/cli.md` file for the same release still lists `--vlm-write-native-output`. The 2.146.0 executable source uses `--debug-vlm-native-output`. For this version, the executable implementation is the stronger evidence of the accepted option.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Source:

`https://github.com/docling-project/docling/blob/v2.146.0/docling/cli/main.py`

### 8.3 Process exit codes and partial documents

Docling's CLI also exposes `--fail-on`, which can distinguish whether only complete failures should produce a failing process exit code or whether partial conversions should also be treated as failures.

This matters in batch-processing environments because producing an output file does not mean the entire source document was successfully processed.

The CLI can retain partial results for inspection while still signaling an unacceptable conversion outcome to the calling process.

Other relevant controls include page ranges, document timeouts, VLM token limits, page batch size, profiling, and saved profiling output.

These controls operate at different layers. Page limits govern input processing; VLM token limits govern generation; document timeout governs the overall conversion lifecycle. Adjusting one does not automatically change the others.

### 8.4 Distinguishing error recovery from correctness evaluation

The combined Chandra–Docling stack has useful machinery for detecting request failures, invalid HTML, truncation, and certain malformed structures.

It does not provide a universal quantitative confidence score for the correctness of every recognized mathematical expression, chart value, molecular representation, or diagram connection.

This suggests a useful conceptual distinction among three kinds of validation:

| Validation class      | What it establishes                                               |
| --------------------- | ----------------------------------------------------------------- |
| Execution validation  | The inference operation completed successfully                    |
| Structural validation | The response could be represented in the expected document schema |
| Semantic validation   | The extracted content accurately represents the source's meaning  |

The first two benefit directly from existing Chandra and Docling machinery.

The third can require separate checks, especially for scientific content. For example, parsing Mermaid verifies a graph representation's syntax; it does not prove the graph's edges correspond to the original figure.

## 9. Scaling document conversion and model serving independently

### 9.1 Three distinct concurrency layers

A deployed Chandra–Docling workflow can contain multiple forms of concurrency.

| Layer                | Principal responsibility                             |
| -------------------- | ---------------------------------------------------- |
| Document scheduler   | Distribute files and conversion jobs                 |
| Docling VLM pipeline | Prepare pages and coordinate inference requests      |
| Model-serving engine | Schedule vision-language inference and GPU resources |

The standalone Chandra CLI also exposes page batching and parallel vLLM-client workers.

These controls interact, but increasing concurrency at one layer does not guarantee greater end-to-end throughput.

For example, a document-processing service can issue many parallel requests while a GPU server is already saturated. In that case, additional requests may increase queuing and memory pressure without improving overall throughput.

Conversely, insufficient page concurrency may leave model-serving capacity underutilized.

The performance relationship is governed by input preparation, prefill and decoding costs, image-token counts, KV-cache allocation, and available compute resources.

### 9.2 Docling Serve

Docling Serve provides the API and job-execution layer for document conversion.

Its documented deployment options include an in-process local execution engine and a Redis-backed RQ engine, allowing API processing and conversion workers to scale independently.

Configuration includes worker counts, model sharing, page/file limits, device selection, model artifact locations, and performance batch sizes.

The deployment documentation also describes Docker Compose arrangements, GPU-enabled containers, and cluster-level options.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



This service layer is distinct from the model server. One possible architecture is a Docling Serve deployment that calls an independently managed vLLM endpoint.

That separation can simplify model reuse across document-processing clients, but introduces network, service lifecycle, authentication, timeout, and scheduling concerns.

Source:

`https://docling-project.github.io/docling/usage/api_server/deployment/`

### 9.3 Docling Jobkit

Docling Jobkit addresses large-scale document-processing orchestration.

Its documented capabilities include local batch jobs, Kubeflow pipelines, Ray execution, and connectors for HTTP endpoints, S3, Google Drive, and Google Cloud Storage.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docling-project.github.io\&sz=32)

Docling



These capabilities belong to the Docling ecosystem, not to Chandra's recognition model.

They can be combined with a Chandra-backed conversion pipeline, subject to the job execution environment exposing the required model presets, dependencies, and inference endpoint configuration.

Source:

`https://docling-project.github.io/docling/usage/jobkit/`

## 10. Version and reproducibility qualifications

Several version boundaries deserve explicit preservation in a durable reference.

| Component           | Established scope             | Qualification                                                              |
| ------------------- | ----------------------------- | -------------------------------------------------------------------------- |
| Chandra checkpoint  | Public Chandra OCR 2          | Its model configuration identifies a Qwen3.5 architecture                  |
| Chandra package     | `chandra-ocr` 0.2.0           | Package version is independent of checkpoint revision                      |
| Docling integration | 2.146.0                       | Preset, parser, and executable behavior verified against its tagged source |
| MLX integration     | Community 8-bit checkpoint    | Separate model artifact and revision                                       |
| vLLM launcher       | Datalab source configuration  | MTP is experimental; GPU profiles are launcher presets                     |
| Docling Serve       | Documented companion service  | Independently versioned from Docling                                       |
| Docling Jobkit      | Document-processing companion | Orchestration capability, not OCR inference                                |

The parameter-count discrepancy also remains unresolved: Datalab describes Chandra 2 as a 4B model, while Docling's preset uses a 5.3B designation. The sources reviewed do not establish a single reconciled parameter-count convention.

Memory estimates should therefore distinguish actual checkpoint tensor sizes, numerical precision, runtime state, image-processing overhead, and concurrent workload allocations rather than relying on the model's short descriptive name.

The tagged Docling source is especially useful for resolving version-sensitive questions because mutable documentation may describe a newer development state or retain stale option names.

## 11. Additional primary-source references

These sources complement, rather than replace, those provided in the original overview.

| Subject                                      | Direct source                                                                                        |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Qwen3.5 checkpoint architecture              | `https://huggingface.co/datalab-to/chandra-ocr-2/blob/main/config.json`                              |
| Chandra model preprocessing                  | `https://github.com/datalab-to/chandra/blob/master/chandra/model/util.py`                            |
| Chandra native PDF loading                   | `https://github.com/datalab-to/chandra/blob/master/chandra/input.py`                                 |
| Native HTML, layout, and Markdown processing | `https://github.com/datalab-to/chandra/blob/master/chandra/output.py`                                |
| Hugging Face inference                       | `https://github.com/datalab-to/chandra/blob/master/chandra/model/hf.py`                              |
| vLLM-client inference                        | `https://github.com/datalab-to/chandra/blob/master/chandra/model/vllm.py`                            |
| vLLM serving and MTP                         | `https://github.com/datalab-to/chandra/blob/master/chandra/scripts/vllm.py`                          |
| Chandra package extras                       | `https://github.com/datalab-to/chandra/blob/master/pyproject.toml`                                   |
| Docling 2.146.0 model specifications         | `https://github.com/docling-project/docling/blob/v2.146.0/docling/datamodel/stage_model_specs.py`    |
| Chandra-to-Docling parser                    | `https://github.com/docling-project/docling/blob/v2.146.0/docling/utils/chandra_utils.py`            |
| Docling VLM execution/status handling        | `https://github.com/docling-project/docling/blob/v2.146.0/docling/pipeline/vlm_pipeline.py`          |
| Docling 2.146.0 CLI implementation           | `https://github.com/docling-project/docling/blob/v2.146.0/docling/cli/main.py`                       |
| Structured picture-aware chunking            | `https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/` |
| Docling Serve deployment                     | `https://docling-project.github.io/docling/usage/api_server/deployment/`                             |
| Docling Jobkit                               | `https://docling-project.github.io/docling/usage/jobkit/`                                            |

## 12. Architectural implications of the additional capabilities

The most consequential result of these additions is a clearer separation of responsibilities.

Recognition and generation: Chandra's multimodal architecture, image processor, generation settings, and inference backend determine what information can be extracted and at what computational cost. MTP and backend-specific optimizations can affect inference efficiency, while image resizing and long-output generation can affect fidelity.

Document interpretation: Docling's Chandra parser provides substantial native machinery for translating annotated HTML into typed document structures. Its support for rich table cells, figure metadata, form states, mathematical formatting, and hierarchical normalization can replace significant custom parsing logic. Its explicit limits—such as the table-grid bound and the absence of inferred cross-page associations—remain important.

Information preservation: The complete recognized information does not necessarily survive every export or downstream transformation. Raw Chandra responses, native chunks, Docling JSON, Markdown, picture children, and retrieval chunks have distinct representational properties. Docling's configurable serializers and chunking tools provide mechanisms to preserve more information where appropriate.

Deployment and observability: Docling's model preset registry, multiple inference engines, native-response capture, error reporting, and companion service infrastructure make it possible to separate model inference from document-processing and downstream information-consumption workloads. This can simplify architecture while preserving explicit control over execution and failure boundaries.

Together, these capabilities extend the Chandra–Docling combination from a document transcription pipeline into a more general structured document interpretation and preservation system. The principal remaining integration work is not basic OCR or HTML parsing; it is the domain-specific interpretation, validation, and reconciliation of richer extracted structures when those operations are required.

Verification note: This addendum draws on primary documentation and upstream source, including Docling's 2.146.0 tag. Commands and APIs were source-inspected, not executed. Experimental or backend-dependent behavior is identified separately from released parser and configuration functionality.