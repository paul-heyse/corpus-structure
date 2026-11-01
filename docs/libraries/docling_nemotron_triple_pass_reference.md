# Docling + RapidOCR and Nemotron 3.5 Parse (triple pass): configuration, outputs and options

Scope: the facts needed to design a PDF pipeline in which Docling's `StandardPdfPipeline` with RapidOCR as
the in-page OCR is combined with Nemotron 3.5 Parse run in its triple-pass mode. This is a reference, not a
design: it records configurations, outputs, options, constraints and unknowns, and leaves every choice
to the design.

Versions: corpus-structure `main` at `1513b29` (2026-10-31) · Docling 2.145.0 (`docling-slim`),
docling-core 2.105.0, docling-parse 7.24.2, RapidOCR 3.10.0, onnxruntime(-gpu) 1.31.1, torch 2.15.0,
transformers 5.22.1, pypdfium2 5.14.0, httpx 0.28.1, rapidfuzz 3.14.6 (root `uv.lock`) · Nemotron 3.5
Parse (`nvidia/Nemotron-3.5-Parse`, package `nemotron-parse` 3.5.0.post7) · Research date 2026-10-31 ·
Nothing was run.

Companion: `docling_ocr.md` (Docling OCR internals), cited as **[OCR §n]**.

| Label | Meaning |
|---|---|
| **[src]** | Read in source: Docling 2.145.0 tag, repo `main`, NVIDIA Hugging Face repo files |
| **[doc]** | Vendor documentation or model card |
| **[ven]** | Vendor-reported measurement, not reproduced |
| **[inf]** | Inference from source or docs, not executed |
| **[unk]** | Not established; listed in §14 |

**Triple pass**, as NVIDIA defines it: (A) a full-page parse, (B) a separate layout-detection request,
(C) a re-parse of Table and Chart crops taken from the union of detector and parser boxes, followed by a
merge. Docling's `nemotron_parse_v3_5` preset implements (A) only **[src]**.

Contents: 1 Repository baseline · 2 Docling + RapidOCR: options and outputs · 3 Nemotron 3.5 Parse: model ·
4 Runtimes and serving · 5 Request and response contract · 6 Sampling configurations in circulation ·
7 Triple-pass reference pipeline · 8 Output format · 9 Docling's Nemotron integration surface ·
10 How the two layers' outputs relate · 11 Signals available for health and confidence · 12 Repository
constraints and extension points · 13 Design options and their trade-offs · 14 Unknowns · 15 Errata ·
16 Sources.

## 1. Repository baseline (what exists on `main`)

### 1.1 Native recipe (`ingest/pdf.py::PdfRecipe.options()`) **[src]**

| Stage | Configuration |
|---|---|
| Pipeline | `StandardPdfPipeline`; `ThreadedDoclingParseBackendOptions(parser_threads, max_concurrent_results)` |
| Layout | Heron, revision `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8` (`PdfRuntimeConfig.layout_revision`) |
| Tables | TableFormer ACCURATE, `do_cell_matching=True` |
| Formulas | CodeFormulaV2, revision `ecedbe111d15c2dc60bfd4a823cbe80127b58af4`; scale 2.0, `expansion_factor` 0.18, `stop_on_repetition` |
| OCR | `RapidOcrOptions(backend="onnxruntime", lang=["iso:en"], mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS, replace_broken_text_layer=True, rapidocr_params={"EngineConfig.onnxruntime.use_cuda", "Det/Cls/Rec.use_cuda": ocr_device == "cuda"})`, model size small; `ocr_device` default `cpu` |
| Headings | `HeadingHierarchy` enabled |
| Accelerator | `AcceleratorOptions(num_threads=parser_threads, device)`; stage batch sizes = `stage_batch_size` (default 4); `parser_threads` default 8 |
| Execution | One serial spawned child per owned recipe (`ingest/pdf_worker.py`), typed IPC, no database handles across it; cancellation terminates, joins, and kills if needed |

Hooks wired into the pipeline **[src]**:

- `CodeFormulaVlmModel` wrapped by `NativeObservedStage` / `ObservedFormulaStage` → attributable
  per-formula outcomes (`FormulaOutcome(pointer, outcome, error)`).
- `assemble_model` replaced by `CandidatePageAssembler`, which calls `pdf_candidates.capture_candidates`
  on each assembled page (inline-math candidates from fonts, tokens and vector islands).
- OCR stage replaced by `pdf_ocr.observed_rapid_ocr_type(...)` → `ObservedRapidOcr` (§2.4).
- `pdf_health.FormulaPageLifetime` raises if `generate_page_images`, `generate_picture_images`,
  `generate_table_images`, `generate_parsed_pages`, picture classification/description or chart extraction
  is enabled.

Hardware of record (evidence `2026-10-31_pdf-docling-foundations`): RTX 5090 32 GiB (Blackwell consumer,
sm_120), CUDA 13.2, 188 GiB RAM; layout/table/formula on cuda:0, RapidOCR on CPU. Corpus of record: a
1,589-page book with retained successful `native` and `organized` products (plan checkpoint 2026-10-31).

### 1.2 Products, methods and contracts **[src]**

| Method | Products (`product_key`) | Notes |
|---|---|---|
| `IngestPdf` (`ingest.pdf` v2, worker `encoder`) | `native` (no application metadata), `organized` (parent `native`) | Section organization; source views drafted from `organized` |
| `EnrichPdfMath` (`enrich.pdf_math` v1, worker `encoder`) | `math-enriched` (parent = the pinned source-view product) | Cell and inline formula recognition on PDF crops (`PdfRegionRenderer`, pypdfium2, scale 2.0, 0.75 pt padding); `derivation_mappings`; per-section `recognition_coverage`; replaces source views; needs database operation `enrich_pdf_math` |

- Identity: `ProductReference(task_id, product_key, content_digest)`; envelope class `PdfNativeEnvelope`
  in `model/semantic/pdf-products.yaml` (LinkML), validated by `semantic/pdf_contracts.prepare_pdf_product`,
  stored in `ops.native_document_product` with item and region rows; originals in `kb.source_artifact`.
- Envelope enums: `PdfRecipe` {`pdf-native-v1`}; `PdfCoverage` {complete, partial, unknown, unsupported};
  `PdfConversionOutcome` {success, partial_success, failure}; `PdfRecognitionUniverse` {display, inline,
  cell}; `PdfRecognitionPolicy` {`detected-native-display-v1`, `native-font-token-vector-v2`,
  `native-font-token-vector-ocr-word-v3`, `all-nonempty-selected-cells-v1`}; `PdfDerivationKind`
  {`native_text_range`, `vector_region_anchor`, `table_cell`}; `PdfDerivationSourceField` {text,
  cell_text}; `PdfNativeTextQuality` {broken, not_flagged, unassessed}; `PdfOcrInventoryOutcome`
  {complete, partial, unknown}; `PdfInlineAlignmentBasis` {ambiguous-native-items,
  unmatched-native-text}; `PdfOffsetUnit` {codepoint}; `PdfCoordinateOrigin` {top_left, bottom_left}.
- `publication_payload()` writes `recipe: "pdf-native-v1"`, `health.inline_coverage = "unknown"` and
  `cell_coverage = "unknown"`; `EnrichPdfMath` adds `recognition_coverage` rows per section × universe.
- Method protocol (`core/method.py`): `name`, `version`, `family`, `unit_type`, `tier`
  (`MethodTier`: deterministic, encoder, local_llm, agent, hosted_llm, human), `confidence_source`,
  `Config` (frozen Pydantic, hashed), `resources = Resources(worker ∈ {cpu, encoder, llm, agent},
  batch_size, max_concurrency)`, `select`, `input_digest`, `run`. `MethodSettings` holds result-neutral
  settings (data dir, model cache); its docstring says the LLM endpoint joins them in phase 1.
- GPU modes (D6 §5, `GpuMode`): co-resident or exclusive placement of the planned Qwen vLLM server and
  encoder workers on the 32 GB GPU.

### 1.3 Inline-math machinery already present **[src]**

- Candidates (`capture_candidates`): math fonts (`CMMI|CMSY|CMEX|MSAM|MSBM|Math|Symbol|STIX`), math
  tokens, `native-vector-gap-v1` vector islands (`_shapes.vector_boxes`; backgrounds and text-explained paths
  filtered; networkx components), OCR-word candidates (`ocr-word-text` basis with
  `ocr_region_index/ocr_line_index/ocr_word_index`). Each carries `before`/`after` context.
- `positioned_inline_candidates` binds candidates to exact native text offsets and raises
  `RecognitionUnavailable` on ambiguity; unresolved cases are kept as `PdfInlineAlignmentReport`
  (`outcome: unresolved`, page, candidate index, item pointers, basis, detail; no invented offsets).
- Plan checkpoint (2026-10-31): run 4 failed where a vector glyph overlapped a comma's metric box and
  broke native word order; native word-order recovery is in progress.

## 2. Docling + RapidOCR: options and outputs

Full detail in [OCR §2–§7, §15]. This section lists what matters when another recognizer's output has to
be related to this layer.

### 2.1 OCR options (Docling 2.145.0) **[src]**

| Option | Values / default | Effect |
|---|---|---|
| `OcrOptions.mode` (`OcrMode`) | `FULL_PAGE`, `LAYOUT_REGIONS`, `PDF_AWARE_LAYOUT_REGIONS` (repo), `DEFAULT` → PDF-aware | Which regions are rasterized for OCR [OCR §3] |
| `replace_broken_text_layer` | bool (repo: True) | A page with a broken native layer gets OCR text instead [OCR §5] |
| `scale` | 3.0 (216 DPI) | Crop render scale; RapidOCR caps the long side at 2000 px (`Global.max_side_len`) [OCR §7.4] |
| `RapidOcrOptions.lang` | default `["ch"]`; repo `iso:en` | Recognizer model choice |
| `backend` | onnxruntime (repo), openvino, paddle, torch | |
| `model_size` | tiny, small (repo), medium | PP-OCRv6 det/rec size |
| `text_score` | 0.5 | Minimum line score kept |
| `use_det` / `use_cls` / `use_rec` | `None` = RapidOCR defaults | Stage switches |
| `detect_orientation` | False | 90/180/270 re-reads; **refused** by the repo's `ObservedRapidOcr` |
| `rapidocr_params` | `{}` | Any RapidOCR dotted key, applied last [OCR §7.3] |

### 2.2 Merge rule that shapes everything downstream **[src]**

OCR runs after layout, on layout clusters. In PDF-first merging, an OCR line cell whose box touches any
native text cell is dropped. Consequence: glyphs drawn as vector paths on a line that also has native text
(inline mathematics, symbols) never enter the native text through OCR, whatever the engine [OCR §4.4].
A page-level parser (such as Nemotron) used *as* the OCR engine is subject to the same rule.

### 2.3 What the native `DoclingDocument` carries **[src]**

| Output | Present | Absent |
|---|---|---|
| Text items | label, `text`, `orig`, `prov` (page, bbox, `charspan`), content layer, parent/children | OCR origin and OCR confidence per item |
| Tables | `TableData` cells with grid indices, spans, header flags, per-cell `bbox` (TableFormer + cell matching) | Per-cell confidence |
| Formulas | `FormulaItem` with CodeFormulaV2 LaTeX (detected display formulas); cell/inline formulas only in the repo's `math-enriched` product | Inline math drawn as paths in the native product |
| Pictures | `PictureItem` with bbox, captions | Chart data, classification, description (forbidden by `FormulaPageLifetime`) |
| Headings | `SectionHeaderItem` levels from `HeadingHierarchy` | |
| Page-level | `ConversionResult.confidence` (`parse_score`, `layout_score`, `ocr_score`, `table_score` unimplemented, `mean_grade`, `low_grade`) — outside the JSON; the repo stores it in `runtime_report.confidence` | |

Provenance boxes may be BOTTOMLEFT; `bbox.to_top_left_origin(page_height)` converts (used throughout
`pdf_enrichment.py`).

### 2.4 RapidOCR word evidence retained by the repo (`ingest/pdf_ocr.py`) **[src]**

`ObservedRapidOcr` subclasses `RapidOcrModel`. For each non-empty OCR rect it calls the reader with
`return_word_box=True` and records, per page, in `inline_candidate_pages[p]`:

| Field | Content |
|---|---|
| `native_text_quality` | `broken` if the page's text layer was flagged broken, else `not_flagged` |
| `ocr_regions[]` | `region_index`, `engine: rapidocr`, `raster_width/height`, `scale` (raster px per pt), `orientation: 0`, region box in PDF TOPLEFT points, `outcome` (`complete` / `partial` / `unknown`) |
| `lines[]` | `line_index`, `text` |
| `words[]` | `word_index`, `text`, `confidence` (0–1), `start`/`end` (offsets in the line text), raster box, PDF box (mapped with `ocr_box_to_bounding_rectangle`) |

A region is `partial` when word results fail validation, a non-space character in a line is not covered by
a word, or a word box is invalid. Word boxes are CTC estimates, "never original PDF glyph custody"
(`PdfOcrWord` description). Native line output is unchanged by the subclass.

## 3. Nemotron 3.5 Parse: model

### 3.1 Facts **[doc][src]**

| Item | Value |
|---|---|
| Size | 630,800,496 unique trainable parameters, including 2,099,200 MTP parameters; BF16 weights ≈ 1.26 GB (arithmetic, [inf]) |
| Architecture | C-RADIOv4-SO400M vision encoder → 1D conv adapter → 10-layer mBART decoder; one-token MTP head (used by vLLM only); all tensors in `model.safetensors` |
| Tokenizer | 72,505 tokens; coordinate tokens `<x_…><y_…>`, class tokens `<class_…>`, task tokens are special tokens |
| Input | One RGB image (page or crop) per request; NaViT dynamic preprocessing; recommended maximum 1664×2048 |
| Coordinates | Normalized to the image **content** (no padding inverse needed): multiply x by width, y by height |
| Max new tokens | 8744 |
| Revisions in use | Docling preset pins `e7ea79242a87ea0ad3919b672bfedb429a683206`; the ParseBench reference ran `e5e0406c85ec241b164907bf41ebd648a54e4ea2` |

### 3.2 Task prompts

| Prompt | Text | Output | Source |
|---|---|---|---|
| Parse (full page or crop) | `</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>` | Boxes, classes and Markdown bodies, including text inside pictures | model card, serving.md, Docling preset, ParseBench `run.py` [doc][src] |
| Detect | `</s><s><predict_bbox><predict_classes><output_no_text><predict_no_text_in_pic>` | Boxes and classes, empty bodies | ParseBench `run.py` [src] |

The task tokens combine (bbox / classes / text output / text-in-picture); other combinations are
possible in principle but only these two are used by NVIDIA's reference pipeline **[src][inf]**.

### 3.3 Published quality and speed **[ven]**

ParseBench (2,078 pages, one H100, reference pipeline):

| Mode | Mean | Tables | Charts | Content faithfulness | Semantic formatting | Visual grounding | Pages/s |
|---|---|---|---|---|---|---|---|
| Single | 72.74 | | | | | | 15.42 |
| Double (crops from parser boxes) | 74.92 | | | | | | 11.65 |
| Triple + union | 75.20 | 84.67 | 64.40 | 87.96 | 68.28 | 70.67 | 10.62 |

build.nvidia.com single-pass table (different harness):

| Model | Mean | Tables | Charts | Faithfulness | Formatting | Grounding | Pages/s |
|---|---|---|---|---|---|---|---|
| Nemotron 3.5 Parse | 69.05 | 72.60 | 49.89 | 86.83 | 65.56 | 70.26 | 14.21 |
| PaddleOCR-VL 1.6 | 67.43 | – | 54.24 | – | – | 77.80 | 3.09 |

Other: MOSCAR CER 1.46 (Nemotron Parse 2.0: 4.25), char-bag F1 99.51; IndicVision ANLS 82.00–83.73. No
OmniDocBench or olmOCR-bench figures published. None of these say anything about this corpus.

## 4. Runtimes and serving

### 4.1 Package and runtime constraints

| Component | Constraint | Label |
|---|---|---|
| `nemotron-parse` 3.5.0.post7 | `requires-python >=3.10`; `torch>=2.11.0,<2.14`; `torchvision>=0.26.0,<0.29`; `transformers>=5.14.1,<5.20`; `huggingface-hub>=1.24.0,<2`; `accelerate==1.12.0`; `timm==1.0.22`; `safetensors==0.8.0`; `beautifulsoup4==4.13.3` | [src] |
| Extras | `vllm = ["vllm>=0.25.0,<0.33"]`, `client = ["openai==2.30.0", "httpx==0.28.1"]`, `dev = ["pytest==9.0.2"]` | [src] |
| Entry points | `vllm.general_plugins`: `nemotron_parse_35 = "vllm_tied_patch.plugin:register"`; console script `nemotron-parse = "nemotron_parse.inference:main"` | [src] |
| Validated runtime (`reference/model/runtime_compatibility.json`) | vLLM 0.26.0, torch 2.11.0, transformers 5.14.1; attention "FlashAttention FA3" ("upstream default source pin for vLLM 0.26.0"); `one_token_mtp: true`; GPUs and CUDA not listed | [src] |
| serving.md | Python 3.12 fresh environment; reference H100 BF16; `pip install ".[vllm,client]"` then `pip check` | [doc] |
| Transformers-only route | Python 3.12 recommended with `transformers==5.14.1`, `torchvision==0.26.0`, `timm==1.0.22`; needs no Nemotron package (remote code) | [doc] |
| Repo root env | Python 3.14.10, torch 2.15.0, transformers 5.22.1: outside the package's torch and transformers bounds | [src] |
| Planned `services/vllm-native` (D9) | vLLM 0.31, torch 2.13 on Python 3.14; directory not present on `main` | [src] |

`vllm.general_plugins` entry points are loaded by every vLLM process started in an environment where the
package is installed, so the patch applies to any model that environment serves **[src][inf]**.

### 4.2 Reference serving command **[doc]**

```
vllm serve "$MODEL_REPO" --served-model-name nemotron-parse --trust-remote-code --dtype bfloat16 \
  --distributed-executor-backend uni --tensor-parallel-size 1 --data-parallel-size 1 \
  --max-model-len 16384 --max-num-seqs 192 --max-num-batched-tokens 16384 --no-enable-prefix-caching \
  --limit-mm-per-prompt '{"image":1}' --attention-config '{"flash_attn_version":3}' \
  --chat-template "$MODEL_REPO/chat_template.jinja" --host 127.0.0.1 --port 8000
```

| Flag / variable | Meaning | Notes |
|---|---|---|
| `--trust-remote-code` | Load the model's own code | Required |
| `--dtype bfloat16` | BF16 weights/activations | Reference precision |
| `--distributed-executor-backend uni`, TP 1, DP 1 | Single process, single GPU | |
| `--max-model-len 16384` | Context (image tokens + 8744 output) | |
| `--max-num-seqs 192` | Concurrent sequences | serving.md: "reduce it on GPUs with less memory"; no figure given |
| `--max-num-batched-tokens 16384` | Scheduler token budget per step | |
| `--no-enable-prefix-caching` | Each request is a new image | |
| `--limit-mm-per-prompt '{"image":1}'` | One image per request | |
| `--attention-config '{"flash_attn_version":3}'` | Selects FlashAttention 3 | FA3 kernels target Hopper (sm_90); the RTX 5090 is sm_120; behaviour there unknown [inf][unk U-1] |
| `--chat-template chat_template.jinja` | Model's chat template | |
| `NP_VLLM_MTP=0` (env) | Disable one-token MTP | serving.md: MTP is "enabled automatically in vLLM, along with the compatible FA3 scheduler"; startup log shows MTP with one speculative token; "SpecDecoding metrics" report acceptance |
| `--gpu-memory-utilization` (vLLM default 0.9) | Fraction of GPU memory vLLM claims for weights + KV cache | Not set in the reference; matters when sharing the GPU with Docling's CUDA stages or another vLLM server [inf] |
| Docker | `docker compose up --build` in the downloaded repo | No standalone image named |

Endpoints (vLLM OpenAI server): `GET /health`, `GET /v1/models`, `GET /version`,
`POST /v1/chat/completions` **[doc][inf]**. Verification receipts: `reference/validation/`,
`reference/model/runtime_compatibility.json`, `reference/package/README.md` **[doc]**.

### 4.3 Transformers route (in-process)

- Docling's Transformers engine for the preset: BF16, `min_engine_version` 5.14.1 (no upper bound),
  `requires_trust_remote_code` (must be set on engine options; default `trust_remote_code=False`),
  `repetition_penalty` 1.1 **[src]**.
- No MTP, no continuous batching; single-pass via Docling **[src][inf]**.
- Whether the remote code runs under the root env's transformers 5.22.1 / torch 2.15.0 is not verified
  **[unk U-2]**.

## 5. Request and response contract (OpenAI chat completions)

### 5.1 Request (`vllm_example.py`) **[src]**

```python
{
  "model": "nemotron-parse",
  "messages": [{"role": "user", "content": [
      {"type": "text", "text": PROMPT},                       # text part first
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<b64>"}},
  ]}],
  "max_tokens": 8744,
  "temperature": 0.0,
  # vLLM extensions (extra_body in the openai client):
  "top_k": 1, "repetition_penalty": 1.1, "skip_special_tokens": False,
}
```

- Image bytes are sent as read from file; MIME from extension (`image/jpeg`, `image/webp`, else
  `image/png`); no resizing in the example **[src]**.
- `skip_special_tokens: False` is required: the coordinate and class tokens are special tokens; with
  `True` the output loses its structure **[doc]**.
- Optional OpenAI/vLLM fields not used by NVIDIA's examples: `seed` (used by the ParseBench reference),
  `logprobs` / `top_logprobs` (not mentioned in NVIDIA docs; behaviour with MTP unknown, U-3) **[src][unk]**.

### 5.2 Response fields used

| Field | Meaning |
|---|---|
| `choices[0].message.content` | Raw block stream (§8) |
| `choices[0].finish_reason` | `stop` or `length` (hit `max_tokens`) |
| `usage.prompt_tokens`, `usage.completion_tokens` | Image+prompt tokens; generated tokens |
| `choices[0].logprobs.content[*]` | Per-token logprobs, only if requested and supported |

NVIDIA's example records content, `finish_reason` and usage; its predictions JSONL row has `raw_out` and
`"coordinate_frame": "content_normalized"` **[src]**.

## 6. Sampling configurations in circulation

| Source | Pass | temperature | top_k | top_p | repetition_penalty | max_tokens | seed |
|---|---|---|---|---|---|---|---|
| serving.md, `vllm_example.py` | parse | 0 | 1 | – | 1.1 | 8744 | – |
| Docling preset (API engine) | parse | 0.0 (`model_spec.temperature` default) | 1 | – | 1.1 | 8744 | – |
| Docling preset (Transformers override) | parse | – | – | – | 1.1 | 8744 | – |
| ParseBench `run.py` | A full page | 0.2 | 50 | 1.0 | 1.05 | 8744 | 20261012 |
| ParseBench `run.py` | B detection | 0.2 | 50 | 1.0 | 1.05 | 4096 | 20261012 |
| ParseBench `run.py` | C crops | 0.1 | 50 | 1.0 | 1.0 | 8744 | 20261012 |

[src] for all rows. Docling's API params are `{"model":"nemotron-parse","max_tokens":8744,"top_k":1,
"repetition_penalty":1.1,"skip_special_tokens":False}`; the engine then always sets
`temperature = input_data.temperature` (from `model_spec.temperature`, default 0.0) and `max_tokens`, and
finally applies user `params` on top **[src]**. The published 75.20 used the ParseBench row set. Greedy decoding (top_k 1) gives
repeatable output up to GPU numeric nondeterminism; sampling with a fixed per-request seed is repeatable
under the same conditions **[inf]**.

## 7. Triple-pass reference pipeline (`reference/parsebench/pipeline/`)

Files: `run.py` (driver), `serve.py`, `prepare_inputs.py`, `parse_results.py`, `postprocess.py`, `score.py`,
`engine/` (`merge.py`, `policies.py`, `regions.py`, `geometry.py`, `blocks.py`, …), fixtures
(`postprocessing_checks.json`, `expected_results.json`, `validation_metrics.json`,
`correction_comparison.json`), `requirements.txt`, `requirements-scorer-lock.txt`. Reference environment:
Python 3.12, one H100 80 GB, `serve.py` then `run.py --mode triple --triple-regions union`, model revision
`e5e0406c…` **[src]**.

### 7.1 Modes **[src]**

| Mode | Requests per page | Region source for crops |
|---|---|---|
| `single` | 1 (A) | none |
| `double` | 1 + crops | Table/Chart boxes from A's output |
| `triple` | 2 (A, B) + crops | `--triple-regions detector` (default): B's boxes; `union`: B's boxes plus A's boxes (§7.4) |

Driver defaults: concurrency 128, HTTP timeout 1800 s, 8 postprocessing workers **[src]**.

### 7.2 Input preparation **[src]**

| Item | Value |
|---|---|
| Page rendering | 150 DPI RGB, JPEG quality 92 |
| Crops | Cut from the page image; JPEG quality 95; file `f"{page.key}__pe_{element_index:03d}.jpg"`; existing non-empty files reused; manifest JSONL |
| Geometry args | `include_detector_labels='table,chart'`, `max_elements_per_page=80`, `crop_margin_px=12`, `crop_margin_ratio=.04`, `min_crop_size=8`, `canvas_width=1664.`, `canvas_height=2048.`, `pad_position='top-left'` |
| Merge config hints | `dedupe_overlap_threshold=.85`, `dedupe_text_threshold=.8`, `replacement_text_threshold=.8`, `structural_classes='Table,Chart'`, `output_coordinate_frame='content_normalized'` |

`PageImage` records key, name, path, width, height, category; no padded image is written. The canvas/pad
arguments matter only for `padded_grid`-style frames; `content_normalized`, `original_normalized` and
`navit_content` frames are treated as direct image-relative coordinates (`model_bbox_to_image_norm`).
`model_canvas_norm_to_image_norm` for padded frames: `scale = min(1, cw/W, ch/H)`, resized size
`W·scale × H·scale`, `top-left` pad = 0, `bottom-right` = remaining space, otherwise centred; inverse
`(norm·cw − pad_x)/resized_w` **[src]**.

### 7.3 Detection parsing (`engine/geometry.py::parse_model_detection_predictions`) **[src]**

- `for match in BLOCK_RE.finditer(raw_out)`: `x1, y1, _body, x2, y2, cls = match.groups()`.
- Coordinate scale: max coordinate in (1.5, 1000] → divide by 1000; > 1000 → divide by page width/height;
  else as-is. Clamp to [0, 1], sort corners; drop if `x2 ≤ x1` or `y2 ≤ y1`.
- Each detection: `score: 1.0` (no model confidence), normalized label, `model_order`; then
  `filter_detection_rows` (label filter, `max_elements_per_page` cap).
- Fallback (`fallback_full_page`): no detections → one element `{"label":"text","score":0.0,
  "bbox_norm":[0,0,1,1],"fallback":True}`.

### 7.4 Region union (`engine/regions.py::select_union_regions(primary, secondary)`) **[src]**

Docstring: "Optional detector/parser region union using the frozen overlap policy." Per page row:

1. `boxes = list(primary)` (detector boxes, original order).
2. For each secondary (parser) box: skip if some kept box has the same label and IoU ≥ 0.85; else append
   with `model_order = len(boxes)`.
3. `boxes = boxes[:80]` (cap over the whole list, primaries included).
4. Drop added boxes (index ≥ len(primary)) whose label equals a primary's and IoU ≥ 0.5 with it; applies
   to any label.

Labels are compared as exact strings (no normalization inside the function).

### 7.5 Crop geometry (`engine/geometry.py::build_crops`) **[src]**

`mx = crop_margin_px + (px2 − px1)·crop_margin_ratio`, `my` likewise; `left = max(0, floor(px1 − mx))`,
`right = min(W, ceil(px2 + mx))`, `top`/`bottom` likewise; skip if width or height < `min_crop_size`. No
extra padding. Crop → page mapping for content-normalized crop output (`merge.crop_box_to_page_canvas`):
`page_norm = ((left + c_x·crop_w)/W, (top + c_y·crop_h)/H, …)`; the default `crop_coordinate_frame` in
`merge.py` is `padded_grid`, so the frame argument must match how the model reports crop coordinates.

### 7.6 Per-page finalization (`parse_results.process` / `finalize`) **[src]**

1. Rows keyed by `renderer.key(row)`; duplicate keys raise.
2. Crop rows: `error` → logged under `crop_generation`, skipped; label filter; blocks rebuilt by
   `merge.rebuild_crop_row_blocks` and kept only if class ∈ `structural_classes` and area ≥
   `min_structural_area`; exceptions recorded as `crop_reconstruction`; per page sorted by
   `merge.reading_order_key` = `(y1, x1, y2, x2)`.
3. `finalize`: full-page `error` → `fullpage_generation`; `renderer.repair_empty_prefix`; unparsed text
   containing `<x_`, `<y_` or `<class_` → `IncompleteBlock` / `MalformedCoordinates`; classes outside
   `TEXT_BEARING_CLASSES` ∪ {Table, Formula, Picture} → `UnknownClasses`; `canonical_geometry` (original
   kept in `source_raw_out` if changed).
4. With candidates: `merge.build_direct_plus_ordered_structural_addonly(...)`, then `canonical_geometry`
   again; render via `renderer.finalize_one`.
5. Output row: `key`, `raw_out`, `source_raw_out`, `markdown`, `coordinate_frame: content_normalized`,
   `postprocessing_status` (`ok` | `partial` if any errors | `empty` | `raw_fallback` on exception),
   `postprocessing_errors`. Workers: fork-based `ProcessPoolExecutor`, `chunksize=8`.

### 7.7 Add-only merge (`engine/merge.py`) **[src]**

- Direct (A) block sequence is kept; crop structural blocks are inserted by bbox without reordering direct
  blocks (`insert_additions_preserving_direct_order`: "Keep the direct model's block sequence stable,
  inserting new blocks by bbox.").
- Duplicate test (`is_duplicate`): same class **and** IoU ≥ `dedupe_overlap_threshold` **and**
  `text_similarity` ≥ `dedupe_text_threshold`; `text_similarity` = Jaccard over lower-cased word tokens with
  HTML-like tags stripped. Duplicates are discarded.
- No replacement in this function: a crop Table/Chart either duplicates a direct block or is added; a crop
  table that differs in text from an overlapping direct table is added alongside it.
- Fallback: crop output with no parseable block → `crop_markdown()` text with the detector box
  (`page_bbox_to_page_canvas`) and `class_for_detector()`; origin `crop_element_fallback`.
- Crop rows dropped by `max_crop_output_chars`, `max_crop_output_blocks`, `include_detector_labels`.
- Only counters are kept: `hybrid_kept_direct_blocks`, `hybrid_added_structural_blocks`,
  `hybrid_skipped_duplicate_blocks`, `hybrid_added_detector_labels`. Empty merged text → `direct_raw` or
  structural prediction; no structural source and no element blocks → `SystemExit`.

### 7.8 Guarded table replacement (`engine/policies.py::replace_guarded`) **[src]**

Signature: `replace_guarded(raw, candidates, merger, similarity=.65, guard='valid', repair=False,
min_rows_ratio=0., iou_threshold=.5, protect_headers=False, emit_repair=True)`. Reference configuration uses
`guard='columns'`, `repair=True` (`replacement_text_threshold` .8 in the config hints).

- Targets: existing `Table` blocks (`merger.parse_blocks(raw)`); candidates: non-empty `Table`s.
- Rejected when: IoU < `iou_threshold`; candidate `native_grid` invalid; unequal `\begin{tabular}` /
  `\end{tabular}` counts; `guard=='columns'` and both grids valid with different `columns`;
  `min_rows_ratio` > 0 and new rows < old rows × ratio; `protect_headers` and header shape differs from a
  non-empty old shape; text similarity < `similarity`.
- Greedy one-to-one assignment by (overlap, similarity) descending. Only the body group is replaced via
  `merger.BLOCK_RE.sub`; coordinate tags are kept. `emit_repair=False` emits the unrepaired body.
- `native_grid(body, repair=False)` (`lru_cache(32768)`): exactly one `tabular` environment, else
  `(body, None)`; invalid with `unterminated_row` or `inconsistent_native_grid`; > 4096 rows or > 512
  columns → `grid_size`. Repair: if all rows share one total span width in [1, 512] that differs from the
  declared column count, rewrite the column spec (pad with `c` or truncate), `changed_column_declaration`.
- Regexes: `BLOCK = (<x_[^>]+><y_[^>]+>)(.*?)(<x_[^>]+><y_[^>]+><class_([^>]+)>)`; the stricter
  `merger.BLOCK_RE` is used for positional indexing because the broad pattern matches malformed
  coordinates.

Where `replace_guarded` runs relative to the add-only merge (in `postprocess.py` vs `parse_results.py`), and
whether one crop can be both added and used as a replacement, was not traced to the end **[unk U-4]**.

### 7.9 Other reference postprocessing policies **[src]**

| Function | Behaviour |
|---|---|
| `chart_render(raw, panels=False, compound=False)` (reference: `panels=True, compound=True`) | Converts Markdown tables inside `<chart …>` blocks to HTML; `title:` → caption; `panel:` lines and `table[...]:` markers attach tables to panels; skips tables with `\|` or backticks, < 3 rows, ragged rows or bad separator; `compound` splits "value (percent%)" columns into Value/Percent when ≥ 2 non-empty cells match; title removed only if all tables converted; unchanged text if nothing changes |
| `engine.chart_caption` | Chart caption transform (not read in detail) |
| `promote_bold_header_row` | First row → `<th>` when no `th`, ≥ 2 rows, 2–20 first-row cells, ≥ 2 next-row cells, all cells ≤ 100 chars, ≥ 60 % first-row cells non-numeric and non-empty, ≥ 60 % bold; asserts text/spans unchanged |
| `dedupe_exact_elements`, `repair_empty_prefix` | Exact-duplicate removal; repair of a missing leading coordinate |

### 7.10 NVIDIA postprocessing helpers (`nemotron_parse` package) **[doc]**

`postprocess_document`, `extract_classes_bboxes`, `transform_bbox_to_original`, `postprocess_text`,
`nemotron_parse.inference.DocumentParser`; `table_format` ∈ {latex, html, markdown, json,
json_hierarchical, csv}. Documented in `docs/postprocessing.md`.

## 8. Output format

### 8.1 Block grammar **[doc][src]**

`<x_X1><y_Y1>BODY<x_X2><y_Y2><class_CLASS>` repeated in reading order. Coordinates are decimal fractions of
the input image (Docling's `_COORD_TOKEN = <x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)>`;
`_CLASS_TOKEN = <class_([^>]+)>`). Artifact tokens seen in output: `<tbc>`, `\<|unk|\>`, `\unknown`.

### 8.2 Classes and bodies

| Class | Body |
|---|---|
| Text, Caption, Footnote, Bibliography, Page-header, Page-footer | Markdown (emphasis, inline HTML such as `<sup>`, `<sub>`, `<br>`), inline math `$…$` / `\(…\)`, display `$$…$$` / `\[…\]` |
| Title, Section-header | Markdown heading with `#` depth (or none) |
| List-item | Marker + Markdown |
| TOC | Text or LaTeX `tabular` |
| Table | LaTeX `tabular` (multirow/multicolumn spans, header rows) |
| Chart | `<chart type="…">` with `title:`, optional `panel:` lines, and Markdown tables (`table[...]:` markers) |
| Picture | Text found in the picture (with `predict_text_in_pic`) |
| Formula | LaTeX, possibly with delimiters and equation numbers |
| Code | Source text |

### 8.3 Granularity

Blocks are paragraph/region granularity; no line, word or character boxes and no per-block confidence.
Inline math has no separate box. Table cells have no boxes **[doc][src]**.

## 9. Docling's Nemotron integration surface

### 9.1 Preset `nemotron_parse_v3_5` (`datamodel/stage_model_specs.py`) **[src]**

| Field | Value |
|---|---|
| Repo / revision | `nvidia/Nemotron-3.5-Parse` @ `e7ea79242a87ea0ad3919b672bfedb429a683206` |
| Prompt | parse prompt (§3.2) |
| Response format | `ResponseFormat.NEMOTRON_PARSE_V3_5` |
| `max_new_tokens` | 8744 |
| Supported engines | TRANSFORMERS, API (in-process vLLM needs NVIDIA's out-of-tree plugin) |
| `default_engine_type` | AUTO_INLINE |
| Transformers override | BF16, `min_engine_version` 5.14.1, `requires_trust_remote_code`, `repetition_penalty` 1.1 |
| API override params | `{"model":"nemotron-parse","max_tokens":8744,"top_k":1,"repetition_penalty":1.1,"skip_special_tokens":False}` |
| Image | `scale` 2.0, `max_size` 2048 |

### 9.2 Options classes **[src]**

| Class | Fields |
|---|---|
| `VlmConvertOptions` (`pipeline_options.py` L1148) | `model_spec`, `engine_options`, `scale` (2.0), `max_size` (preset 2048), `batch_size` 1, `force_backend_text`; `from_preset(name, engine_options=…)` |
| `VlmPipelineOptions` (L1596) | `vlm_options`, `enable_remote_services` (must be True for API), `generate_page_images` (default True), `images_scale` |
| `ApiVlmEngineOptions` | `engine_type=VlmEngineType.API`, `url`, `headers`, `params`, `timeout` (60.0), `concurrency` (1) |
| Transformers engine options | `trust_remote_code` (default False), device/dtype settings |

### 9.3 API engine behaviour (`api_openai_compatible_engine.py`, `utils/api_image_request.py`) **[src]**

- Parameter precedence: preset API params are applied **only if user `params` is empty**
  (`if not self.user_params: api_params.update(self.model_api_params)`); then `temperature` and
  `max_tokens` from the request; then user `params`. Any user `params` therefore drops `model`, `top_k`,
  `repetition_penalty`, `skip_special_tokens` from the preset unless restated.
- Image sent as PNG base64 data URL, content order **image then text** (NVIDIA's example sends text then
  image).
- Concurrency: thread pool over `predict_batch`; pages arrive in batches of `settings.perf.page_batch_size`
  (default 4), so in-flight requests ≤ min(`concurrency`, page batch size).
- Logprobs: collected from the response (also when streamed) into `VlmPrediction.generated_tokens` when the
  server returns them; Docling does not request them by default.
- Stop reasons: INFERENCE_ERROR, LENGTH, CONTENT_FILTERED → per-page error and conversion
  `PARTIAL_SUCCESS`; all pages failed → `FAILURE`; missing prediction → error (`_determine_status`).

### 9.4 Mapping (`utils/nemotron_parse_v3_5_utils.py::parse_nemotron_parse_v3_5`) **[src]**

Signature: `parse_nemotron_parse_v3_5(content, original_page_size, page_no, filename="file",
page_image=None, *, normalize_heading_levels=True) -> DoclingDocument` (one page).

| Class | Result |
|---|---|
| Text, unlisted classes | `TextItem` TEXT (rich text via `_add_inline_text`) |
| Title / Section-header | `TitleItem` / `SectionHeaderItem` (`parse_markdown_heading`; level = `#` depth or 2) |
| List-item | `ListItem` in a `ListGroup` of consecutive blocks; marker parsed; enumerated for ordered markers |
| TOC | group `toc` with text or tables |
| Table | `TableItem` from LaTeX (`latex_tabular_to_html` / `_add_latex_table`; spans, header flags; grid cap `_MAX_TABLE_GRID_CELLS`) |
| Chart | `PictureItem` + `PictureClassificationMetaField` (chart type) + `TabularChartMetaField` (from the Markdown tables) |
| Picture | `PictureItem`; body text as child `TextItem`s **without prov** |
| Formula | `add_formula(text=strip_math_delimiters(text), orig=text)` |
| Code | `CodeItem`, language from `detect_code_language` |
| Caption / Footnote / Bibliography | CAPTION / FOOTNOTE / REFERENCE; captions linked to one adjacent Table/Picture (`link_adjacent_captions`) |
| Page-header / Page-footer | FURNITURE content layer |

- Provenance: `ProvenanceItem(page_no, bbox=_page_bbox(...), charspan=(0, 0))`; bbox = clamped fraction ×
  `original_page_size`, `CoordOrigin.TOPLEFT`.
- Inline math: `markdown_math._MATH` matches `$$…$$`, `$…$` (not when the closing `$` precedes a digit,
  so currency survives), `\(…\)`, `\[…\]`; rendered as `<math>` / `<math display="block">`;
  `_add_html_fragment` emits `<math>` runs as `FORMULA`-labelled children of an inline group and block
  math as `add_formula`. Inline children carry **no prov** (prov is set to None once the parent exists).
- Silent drops (not reported): segments with fewer than two coordinate tokens; stray coordinate tokens
  inside bodies; artifact tokens; exact-duplicate blocks (same label, bbox, text).
- `page_image` given → embedded as `ImageRef` (DPI = 72·image width / page width); `None` → no image.
- `force_backend_text`: honoured only for DOCTAGS (`vlm_pipeline.py` L146); ignored for this format.

### 9.5 Whole-document assembly in `VlmPipeline` **[src]**

Per page: `parse_nemotron_parse_v3_5(..., page_image=page.image, normalize_heading_levels=False)`; then
`BasePipeline._concatenate_page_documents` (`DoclingDocument.concatenate`, page renumbering, provenance
page-number remap); then `normalize_section_header_levels(doc)` once. `VlmConvertModel.process_images(
image_batch, prompt)` runs the engine on raw images with no page metadata (usable for crops).

### 9.6 Single-pass Docling configuration (for reference)

```python
engine = ApiVlmEngineOptions(engine_type=VlmEngineType.API,
    url="http://127.0.0.1:8000/v1/chat/completions", timeout=600.0, concurrency=8,
    params={"model": "nemotron-parse", "max_tokens": 8744, "top_k": 1, "repetition_penalty": 1.1,
            "skip_special_tokens": False})                     # restated: params replace the preset's
opts = VlmPipelineOptions(enable_remote_services=True,
    vlm_options=VlmConvertOptions.from_preset("nemotron_parse_v3_5", engine_options=engine))
converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(
    pipeline_cls=VlmPipeline, pipeline_options=opts)})
```

## 10. How the two layers' outputs relate

### 10.1 Side-by-side

| Aspect | Docling `StandardPdfPipeline` + RapidOCR | Nemotron 3.5 Parse (triple pass) |
|---|---|---|
| Text source | Native PDF text cells; OCR lines only in OCR'd regions | Model-generated text for everything |
| Text granularity | Cells (lines/words) grouped into items; `charspan` into item text | Blocks (paragraph/region); `charspan=(0,0)` in Docling mapping |
| Geometry | Item boxes, table cell boxes, OCR word boxes (repo) | Block boxes only; crop pass gives tighter table/chart boxes |
| Confidence | Page scores; RapidOCR line and (repo) word confidences | None in output; token logprobs if requested |
| Reading order | Layout model + rules | Model order; crop blocks inserted by bbox |
| Tables | TableFormer grid with cell boxes and header flags | LaTeX `tabular` (spans, headers), re-read from crops in triple mode |
| Charts | Picture only (chart extraction off in repo) | Chart type + data tables |
| Display formulas | CodeFormulaV2 LaTeX on layout-detected formulas | LaTeX blocks |
| Inline math | Native glyph text; vector-drawn glyphs absent (repo enrichment recognizes candidates separately) | `$…$` inside text, mapped to inline FORMULA runs without boxes |
| Headings | `HeadingHierarchy` levels | Markdown depth, normalized per document |
| Furniture | Layout labels page header/footer | Page-header/Page-footer classes |
| Failure modes | Missing text (selection and merge), OCR misreads | Hallucinated, dropped or repeated text; truncation at 8744 tokens |
| Determinism | Deterministic given versions (batch-timing caveat [OCR §18]) | Greedy ≈ repeatable; sampled reproducible only with seed and same runtime |

### 10.2 Coordinate frames

| Layer | Frame |
|---|---|
| L0 provenance | PDF points, page size from the backend (`document.pages[n].size`); `coord_origin` TOPLEFT or BOTTOMLEFT per item |
| L0 OCR words (repo) | PDF TOPLEFT points (mapped), plus raster coordinates and `scale` |
| Nemotron raw | Fractions of the submitted image |
| Nemotron via Docling | Fractions × `original_page_size` (points), TOPLEFT |
| Crops | Fractions of the crop; page fraction = `(left + c·crop_w)/W` |

Rendering with pypdfium2 applies the page's CropBox and `/Rotate` by default; whether docling-parse page
sizes and cell coordinates use the same box and rotation for every page is unverified **[inf][unk U-5]**.
Resizing the image before submission does not change content-normalized fractions **[doc]**.

### 10.3 Correspondence characteristics

- Granularity mismatch is normal: one Nemotron block can cover several L0 items (and the reverse), so
  1:1 box matching is insufficient; containment ratios (`area(∩)/area(item)`) and text similarity are the
  usual complements **[inf]**.
- Inline formulas in Nemotron output can only be located inside their block by text position, because
  they have no boxes **[src]**. L0 inline candidates carry page boxes and `before`/`after` context words
  **[src]**, which are the natural join keys **[inf]**.
- L0 `PdfInlineAlignmentReport` rows (unresolved) name page, candidate and item pointers, without offsets
  **[src]**.
- RapidOCR word boxes and Nemotron block boxes overlap only coarsely; text-level comparison is the finer
  join **[inf]**.
- Docling's mapping keeps the raw block in `orig`; normalized `text` loses Markdown and math delimiters
  **[src]**.
- Useful libraries already in the root lock: rapidfuzz 3.14.6 (`Levenshtein.opcodes`,
  `normalized_similarity`), networkx (graph matching), the repo's positioned Lark LaTeX structure
  (`methods/math/native.py`), SymPy (formula equivalence, PDF-06) **[src]**.

## 11. Signals available for health and confidence

| Signal | Layer | Source | Notes |
|---|---|---|---|
| `parse_score`, `layout_score`, `ocr_score`, `mean_grade`, `low_grade` | L0 | `ConversionResult.confidence` (repo `runtime_report.confidence`) | [OCR §15] for blind spots; `table_score` unimplemented |
| Formula outcomes | L0 | `ObservedFormulaStage` → `formula_outcomes` | succeeded / failed / unknown / not_requested |
| OCR word confidence, region outcome, `native_text_quality` | L0 | `ObservedRapidOcr` | CTC scores, not calibrated |
| Inline candidate policy, coverage rows, unresolved alignment reports | L0 | `math-enriched` envelope | Per section × universe |
| `finish_reason` per request | Nemotron | API | `length` = truncated |
| `completion_tokens` vs `max_tokens` | Nemotron | API `usage` | |
| Token logprobs | Nemotron | API (`logprobs: true`) | Per token incl. special tokens when `skip_special_tokens=False`; with sampling = sampled-token logprob |
| `postprocessing_status`, `postprocessing_errors` (`IncompleteBlock`, `MalformedCoordinates`, `UnknownClasses`, `fullpage_generation`, `crop_generation`, `crop_reconstruction`, `page_rendering`) | Nemotron | reference `parse_results` | |
| Merge counters | Nemotron | reference `merge` | kept / added / skipped / detector-label additions |
| `replace_guarded` outcomes | Nemotron | reference `policies` | Only replacements visible unless instrumented |
| Silent mapping drops | Nemotron | Docling mapping | Countable with the same regexes before mapping |
| Docling conversion status | Nemotron via Docling | `_determine_status` | PARTIAL_SUCCESS on LENGTH etc. |
| MTP acceptance | Nemotron | vLLM "SpecDecoding metrics" log/metrics | Operational only |
| Cross-layer agreement (text, order, table shape, formula equality) | both | computed | No library provides it ready-made |

## 12. Repository constraints and extension points

### 12.1 Constraints stated in the repository **[src]**

| Source | Text / rule |
|---|---|
| ADR-0038 | `StandardPdfPipeline` with OCR, tables, formula enrichment and heading hierarchy; originals as bytea, native DoclingDocument JSON as JSONB; corrections/organization create derived products; native conversion never mutated; health separate from coverage; no chunking; no second scheduler or cache. Revisit trigger: "A required PDF capability cannot preserve source-qualified relationships or honest recognition health through StandardPdfPipeline" |
| Coordinator plan §7 | "Secondary OCR and reconciliation: Conditional, not ordinary conversion — Consequential unresolved region/value or selected precision-sensitive consumer; PDF-04/08 design the evidence if activated." · "MinerU / Nemotron Parse / whole-page VLM: Investigative alternatives, not selected production entry — Material unresolved selected-pipeline gap; revised recommendation/decision required." · "Chart/picture description/code enrichment: Deferred" |
| PDF-04 | "Optional independent OCR requires an actual consequential uncertainty/selected precision consumer. Use another recognizer on the affected region rather than repeat full layout/table assembly for the whole book. Retain candidates, geometry, configuration, alignment and unresolved outcomes. No voting framework or automatic correction is baseline scope. A correction creates a derived product and does not mutate native conversion JSON." |
| PDF-04 | "Confidence is a signal, not a calibrated correctness verdict; missing table confidence is not a successful table check." |
| Foundations plan | `mineru2_pro`/Nemotron Parse remain investigative alternatives for material failures; switching whole-document pipelines requires a revised decision |
| `FormulaPageLifetime` | Refuses page/picture/table images, parsed pages, picture classification/description, chart extraction in the native conversion |
| AGENTS.md | Exact pins; side environments as separate uv projects; Python 3.14 product; ADR when choosing between real alternatives (accepted ADRs immutable; supersede to pivot); probes in `docs/design_review/evidence/`; holds in `docs/pins.md`; quantitative claims need measurements; FP-07/A4 execution fit assessed qualitatively |
| D9 §3 | Settings via pydantic-settings, `CORPUS_` prefix; settings include the vLLM endpoint and GPU mode |

### 12.2 Extension points that exist **[src]**

| Point | What it allows |
|---|---|
| `PdfNativeEnvelope` and enums (`pdf-products.yaml`) | New product recipes, derivation kinds, coverage policies, evidence classes (LinkML → compiled Pydantic → SQL guards; forward migration after 0054) |
| `ProductReference` + `parent_*` fields | Product chains; `ops.native_document_product` keyed by task, product key, digest |
| `derivation_mappings` | Pointer-level provenance from derived items to origin items and offsets |
| `recognition_coverage` | Per section × universe × policy outcomes |
| `kb.source_artifact` | Content-addressed byte artifacts (originals, schema, recipes) |
| Method protocol + `METHODS` registry (`ingest/methods.py`) | New methods with their own unit type, worker kind, config hash and database operation grant (`execution-model.yaml`) |
| `_drafts(..., replacements=...)` | Replacing source views from a derived product (pattern in `EnrichPdfMath`) |
| `PdfRegionRenderer` | pypdfium2 page/region rendering from retained originals |
| `ops.measurement` (D6 §6) | Page/section/method metrics |
| `MethodSettings` | Result-neutral settings (an endpoint would be one; phase 1 note) |
| `services/` (D9, planned) | Side environments with their own lock |

## 13. Design options and their trade-offs

Neutral list of choices the design has to make, with the considerations each carries.

### 13.1 Where the triple pass is orchestrated

| Option | Considerations |
|---|---|
| NVIDIA reference pipeline as-is (`run.py --mode triple --triple-regions union`) in a side environment | Closest to the measured 75.20 configuration; separate process/driver with its own concurrency and file layout; outputs `raw_out` + `markdown` JSONL; Python 3.12 environment; counters-only merge evidence |
| Own client in the root env (HTTP to vLLM) reusing reference algorithms | Integrates with the method lifecycle; needs porting/vendoring of geometry, union and merge code; parity must be re-established |
| Docling engine abstraction (`VlmConvertModel.process_images` for crops + `parse_nemotron_parse_v3_5`) | Reuses Docling plumbing; API param precedence and PNG/image-first differences; no detection-pass support built in |
| Docling `VlmPipeline` preset | Single pass only |

### 13.2 Serving environment

| Option | Considerations |
|---|---|
| Dedicated environment at the validated runtime (Py 3.12, vLLM 0.26.0, torch 2.11.0, transformers 5.14.1) | Matches NVIDIA's validation; plugin isolated; one more environment to maintain |
| Shared with the planned `services/vllm-native` (vLLM 0.31, Py 3.14) | Within the package's declared bounds (vLLM < 0.33, Python ≥ 3.10) but outside the validated runtime; general plugin loads for every model served there |
| In-process Transformers in the root env | No server; versions outside package bounds (unverified); no MTP or batching |

### 13.3 Decoding

| Option | Considerations |
|---|---|
| Greedy (serving.md / Docling: T 0, top_k 1, rep 1.1) | Repeatable; vendor serving contract; not the configuration that produced the published triple-pass score |
| ParseBench reference sampling (T 0.2/0.2/0.1, top_k 50, rep 1.05/1.05/1.0, seed) | Matches the published score's setup; outputs depend on seed and runtime |

### 13.4 Inputs

| Choice | Options |
|---|---|
| Model revision | `e7ea7924…` (Docling preset) vs `e5e0406c…` (ParseBench run) |
| Page image | 150 DPI JPEG q92 (reference) vs Docling scale 2.0 PNG with max side 2048; resize bound 1664×2048 |
| Crops | Cut from the page image (reference) vs re-rendered from the PDF at higher DPI |
| Page scope | Every page vs pages/regions selected from L0 signals (PDF-04 currently says region) |

### 13.5 Merge

| Option | Considerations |
|---|---|
| Reference add-only + guarded replacement as published | Parity; ordering detail U-4; possible duplicate tables when text differs |
| Exclusive per-crop decision (replace, else add, else skip) | Avoids duplicates; departs from the reference |
| Keep chart Markdown vs apply `chart_render` | Docling's `_add_chart` parses Markdown tables into `TabularChartMetaField`; HTML conversion targets the reference renderer [src][inf] |
| Keep only counters vs every candidate and decision | PDF-04 text asks to retain candidates and unresolved outcomes |

### 13.6 Representation and storage

| Choice | Options |
|---|---|
| Nemotron document | DoclingDocument via `parse_nemotron_parse_v3_5` (fits the existing envelope machinery) vs raw blocks only |
| Raw outputs | Inline JSONB vs content-addressed artifact; raw per pass enables re-merging without inference |
| Relation to L0 | Separate product(s) with parent/pin references; derived reconciled document (only via derived products per ADR-0038) |
| Logprobs | Not requested / per-block summaries / full token arrays |

### 13.7 Use of the second layer

| Use | Note |
|---|---|
| Evidence only (alignment, diffs, alternatives) | Consistent with "no voting framework or automatic correction" |
| Gap filling in a derived document (inline vector math, chart data) | Adds content absent from L0; needs new derivation kinds and coverage policy wording |
| Coverage audit (math/tables seen by Nemotron but absent from L0 candidates) | Needs whole pages; changes the plan's region-only wording |
| Replacement of L0 text | Excluded by current plan text |

### 13.8 Placement and capacity factors (qualitative)

- Requests per page: 2 + one per Table/Chart region (prose pages have none) **[src]**.
- Vendor throughput: triple+union 10.62 pages/s on an H100 at high concurrency **[ven]**; no RTX 5090
  figure exists; the non-FA3 attention path and smaller memory change it in unknown ways **[unk]**.
- GPU sharing: L0's CUDA stages (spawned child), a Nemotron vLLM server and the planned Qwen vLLM server
  all compete for 32 GB; vLLM claims `--gpu-memory-utilization` × total at start-up **[inf]**.
- Output volume: up to 8744 tokens per parse request, raw text per page per pass **[src]**.
- Book size: 1,589 pages **[src]**.

## 14. Unknowns

| ID | Unknown | How it can be settled |
|---|---|---|
| U-1 | vLLM 0.26.0 + plugin on RTX 5090 (sm_120): which attention backend without FA3; whether MTP initializes | Start the server; read startup log; one round-trip |
| U-2 | Transformers route under root env versions (transformers 5.22.1, torch 2.15.0) | One in-process page |
| U-3 | Logprobs availability and shape with MTP speculative decoding | One request with `logprobs: true` |
| U-4 | Order of add-only merge vs `replace_guarded` in the reference; can one crop be both added and a replacement | Read `run.py` and `postprocess.py` end to end |
| U-5 | pypdfium2 vs docling-parse page frame (CropBox, `/Rotate`) | Synthetic PDFs with MediaBox ≠ CropBox and `/Rotate 90` |
| U-6 | Which revision (`e7ea7924…` / `e5e0406c…`) is newer and what changed | Hugging Face commit history |
| U-7 | Detection prompt output under greedy decoding (reference used sampling) | Same page under both |
| U-8 | Whether crop chart output always matches Docling's `_add_chart` expectations | Map raw crop outputs of chart pages |
| U-9 | Nemotron behaviour on rotated text (RapidOCR word observation refuses `detect_orientation`) | Rotated test pages |
| U-10 | Local quality on this corpus versus L0 | Evaluation on selected pages (inline math page 85, the run-4 page, tables, charts, OCR'd pages) |
| U-11 | GPU memory needed at a given `--max-num-seqs` | Observe KV cache capacity at start-up |

## 15. Errata to earlier deliverables

| Document | Erratum | Status |
|---|---|---|
| `docling_ocr.md` §12.3 | `force_backend_text` is honoured only for DOCTAGS (`vlm_pipeline.py#L146`), not for any grounded format | Corrected in the file (2026-10-31) |
| Notion "Docling configuration and health signals" | Recommended `generate_parsed_pages=True` to keep OCR cells; `FormulaPageLifetime` refuses it, and `main` retains OCR words through `ObservedRapidOcr` | Corrected in Notion (2026-10-31) |

## 16. Sources

Repository (`main` at `1513b29`): `ingest/pdf.py`, `pdf_methods.py`, `pdf_enrichment.py`,
`pdf_candidates.py`, `pdf_ocr.py`, `pdf_worker.py`, `pdf_health.py`, `pdf_hierarchy.py`, `methods.py`;
`model/semantic/pdf-products.yaml`; `semantic/pdf_contracts.py`, `operations.py`; `core/method.py`,
`core/vocab.py`; `docs/adr/0038-pdf-native-docling-products.md`; `docs/plans/pdf-docling-pipeline_2026-10-31.md`
and `docs/plans/pdf-docling-pipeline/*.md`; `docs/design/D6`, `D9`; `uv.lock`.

Docling 2.145.0 (tag): `pipeline/vlm_pipeline.py`, `pipeline/base_pipeline.py`,
`models/stages/vlm_convert/vlm_convert_model.py`, `models/inference_engines/vlm/api_openai_compatible_engine.py`,
`utils/api_image_request.py`, `datamodel/pipeline_options.py`, `datamodel/vlm_engine_options.py`,
`datamodel/stage_model_specs.py`, `utils/nemotron_parse_v3_5_utils.py`, `utils/markdown_math.py`,
`utils/dots_utils.py`, `utils/chandra_utils.py`, `utils/vlm_utils.py`, `models/base_ocr_model.py`;
docling-core 2.105.0 `types/doc/page.py`.

NVIDIA `nvidia/Nemotron-3.5-Parse` (Hugging Face): model card; `pyproject.toml`; `docs/serving.md`;
`docs/postprocessing.md` (referenced); `vllm_example.py`; `reference/model/runtime_compatibility.json`;
`reference/parsebench/pipeline/README.md`, `run.py`, `parse_results.py`, `postprocess.py`,
`engine/merge.py`, `engine/policies.py`, `engine/regions.py`, `engine/geometry.py`; build.nvidia.com model
page.
