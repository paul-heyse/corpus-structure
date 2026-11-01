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

# Addendum — Docling and Nemotron 3.5 Parse: Advanced Capabilities and Integration Semantics

Companion to `docling_nemotron_triple_pass_reference.md` · Research date: November 1, 2026

Scope. This addendum covers functionality not fully developed in the original reference, emphasizing native multipass execution, NVIDIA's public orchestration APIs, merge semantics, postprocessing, structured evidence, execution scheduling and additional serving options. Existing descriptions of model architecture, OCR behavior, coordinate transformations and repository contracts are not repeated.

Version baseline. Docling 2.145.0 is the original reference's pinned release. Newer Docling functionality is explicitly identified as upstream `main` functionality rather than attributed to that release. NVIDIA's public Python interfaces are described for `nemotron-parse` 3.5.0.post7, with earlier post-release changes noted where consequential. The NVIDIA NIM interface is a separate product, version 2.4.

## A. Native multipass support in Docling

Extends original §§9.1–9.6 and §13.1

### A.1 Version distinction and execution model

Docling's `nemotron_parse_v3_5` preset originally implemented a single full-page parse. Subsequently, upstream Docling added model-specific double- and triple-pass orchestration to the VLM conversion stage.

The newer implementation is available in upstream `main`, but is not part of the pinned Docling 2.145.0 release. The release boundary matters: the original reference's single-pass description remains valid for that version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



The new capability is configured through `VlmConvertOptions.nemotron_parse`, using `NemotronParseOptions`:

| Option            | Values                             | Semantics                                                 |
| ----------------- | ---------------------------------- | --------------------------------------------------------- |
| `passes`          | `"single"`, `"double"`, `"triple"` | Selects the parsing stages; default remains single        |
| `triple_regions`  | `"detector"`, `"union"`            | Controls the Table/Chart region source in triple mode     |
| `crop_batch_size` | Positive integer                   | Bounds the number of crop predictions submitted per batch |

Both the Transformers engine and OpenAI-compatible API engine support multipass execution. The in-process vLLM engine remains unsupported for this preset because NVIDIA's model requires its external vLLM plugin.

An illustrative configuration for upstream `main`:

```
from docling.datamodel.pipeline_options import (    NemotronParseOptions,    VlmConvertOptions,    VlmPipelineOptions,)from docling.datamodel.vlm_engine_options import AutoInlineVlmEngineOptionsopts = VlmPipelineOptions(    vlm_options=VlmConvertOptions.from_preset(        "nemotron_parse_v3_5",        engine_options=AutoInlineVlmEngineOptions(            trust_remote_code=True,        ),        nemotron_parse=NemotronParseOptions(            passes="triple",            triple_regions="union",            crop_batch_size=8,        ),    ),)
```

The multipass setting is exposed through the Python SDK, not the preset's ordinary CLI selection, which retains single-pass behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md](https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md?utm_source=chatgpt.com)

### A.2 Multipass behavior and bounds

Docling implements the same broad stage decomposition as NVIDIA's reference: page parse; optional independent detection; Table/Chart crop parsing; and structural merge.

The important additional contracts are:

- Crop budget and geometry: At most 80 regions per page; crops have a 12-pixel plus 4% margin and are skipped if their padded width or height is below 8 pixels. Crop predictions are remapped to page coordinates.
- Stage-specific sampling: For multipass operation, full-page and detection stages use temperature 0.2 and repetition penalty 1.05; crops use temperature 0.1 and repetition penalty 1.0. All use `top_k=50` and `top_p=1.0`, with 4,096 detection tokens versus 8,744 parse tokens.
- Single-pass compatibility: Selecting single-pass preserves the original preset's generation configuration rather than silently applying the multipass defaults.
- API parameter precedence: Explicit API-engine `params` override stage parameters, so an override can change or defeat the stage-specific sampling contract.
- Failure tolerance: Failed, empty, truncated or invalid crop output leaves the full-page result unchanged. Invalid detection output prevents that detection-derived crop stage from contributing refinements.

These are upstream implementation behaviors, not independent evidence that the same page will receive the same predictions as NVIDIA's reference runner.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### A.3 Docling's guarded merge

Upstream Docling implements guarded structural refinement only, not NVIDIA's alternative-preserving default merge.

A crop-derived table replacement requires a valid grid, compatible column count, bounding-box intersection-over-union of at least 0.5 and text similarity of at least 0.65. Successful replacements preserve the original page-region box and reading-order position. New structural objects cannot overlap an existing object of the same class.

The result is a more conservative `DoclingDocument`: incompatible refinements are rejected instead of inserted as conflicting parallel alternatives. This reduces ambiguous duplicate structures, but can retain an inferior full-page prediction.

The distinction matters because NVIDIA's published multipass scores use an alternative-preserving merge, not this guarded policy. Those scores cannot be transferred directly to Docling's implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### A.4 Retained multipass provenance and request accounting

Upstream Docling records multipass execution details in the VLM prediction and copies them into exported document metadata at:

`body.meta.docling__nemotron_parse.pages`

The page-number-keyed metadata includes mode, model request counts, rejected crop requests, aggregate token counts and per-stage provider usage where available.

These counters have specific meanings:

- `requests` counts full-page, detection and crop requests, including unsuccessful crop requests. It does not count inference batches or simply the number of logical stages.
- `rejected_crop_requests` counts unsuccessful or invalid crop generations before merging; it is not a complete accounting of every merge-policy rejection.
- Provider token usage is retained when returned by the engine, but does not imply the availability of calibrated extraction confidence.

Consequently, the metadata can establish how much multipass inference occurred, but does not constitute a complete candidate-by-candidate merge audit.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### A.5 Broader Transformers completion handling

The same upstream work also extends incomplete-generation detection across Transformers VLM presets. Reaching the generation token limit without EOS is treated as incomplete, with the conversion reported as `PARTIAL_SUCCESS`; reaching EOS at the token cap remains complete.

This improves the distinction between a successful model invocation and a completed document extraction. It does not establish that an EOS-terminated response is semantically complete or factually correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source files:

[https://github.com/docling-project/docling/blob/main/docling/datamodel/pipeline_options.py](https://github.com/docling-project/docling/blob/main/docling/datamodel/pipeline_options.py?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/blob/main/docling/pipeline/vlm_pipeline.py](https://github.com/docling-project/docling/blob/main/docling/pipeline/vlm_pipeline.py?utm_source=chatgpt.com)

## B. NVIDIA's public multipass parsing and backend APIs

Extends original §§4, 7.10 and 13.1

### B.1 `DocumentParser` as a reusable orchestration layer

The `nemotron_parse.inference.DocumentParser` API provides a general image-to-document parsing interface covering the same broad workflow as the standalone ParseBench driver. It operates on model predictions and page images; benchmark reference answers, labels and scorer logic are not part of its runtime dependencies.

Its capability surface is broader than the reference driver's command-line workflow:

| API                                             | Capability                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| `parse(image)`                                  | Single-page inference and structured document rendering                         |
| `parse_double(image)`                           | Full-page parse plus parser-selected Table/Chart crops                          |
| `parse_triple(image, triple_regions=...)`       | Independent detection and crop parsing, with detector or union region selection |
| `parse_many(images, mode=..., concurrency=...)` | Multiple documents/pages with shared inference concurrency                      |
| `prepare(images, workers=...)`                  | Reusable, decoded and encoded image batch                                       |
| `parse_prepared(batch, mode=..., schedule=...)` | Dependency-aware batch execution, structured documents and execution metrics    |

The wrapper handles crop creation, region selection, coordinate remapping, merging and document postprocessing. Crops are generated in memory rather than through the reference driver's intermediate crop-file layout.

The public `max_regions` parameter controls the region budget, which defaults to 80 per page. Crop margins are configurable; the reference geometry uses 4% of the region dimensions plus 12 pixels.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co+2



A compact interface example:

```
from nemotron_parse.inference import DocumentParserwith DocumentParser(    base_url="http://localhost:8000/v1",    model="nemotron-parse",    merge_policy="alternatives",) as parser:    page = parser.parse_triple(        "page.png",        triple_regions="union",    )    batch = parser.prepare(page_images, workers=8)    result = parser.parse_prepared(        batch,        mode="triple",        concurrency=128,        postprocess_workers=8,        schedule="pipelined",    )
```

The image interface accepts PIL images and image paths; it does not itself render a PDF. Image-to-PDF-page correspondence, including the relevant crop and rotation transformations, remains an upstream responsibility.

Source: [https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/6cbbc638b8fdb1d94d76d5b9830d43e55da290ad/POSTPROCESSING.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/6cbbc638b8fdb1d94d76d5b9830d43e55da290ad/POSTPROCESSING.md?utm_source=chatgpt.com)

### B.2 Per-stage inference configuration

`GenerationSettings` provides independent decoding configuration for the full-page, detection and crop stages:

```
from nemotron_parse.inference import (    DocumentParser,    GenerationSettings,)parser = DocumentParser(    fullpage=GenerationSettings(        temperature=0,        top_k=1,        repetition_penalty=1.1,    ),    detection=GenerationSettings(        temperature=0,        top_k=1,        max_tokens=4096,    ),    crop=GenerationSettings(        temperature=0,        top_k=1,        repetition_penalty=1.0,    ),)
```

The public wrapper defaults are aligned with NVIDIA's reference sampling regime: full-page and detection temperature 0.2, repetition penalty 1.05; crop temperature 0.1, repetition penalty 1.0; `top_k=50`, `top_p=1.0`, seed 0; token limits 8,744 for parsing and 4,096 for detection.

This is separate from the Docling single-pass preset's greedy defaults. A pipeline can therefore make an explicit distinction between model revisions, sampling policy, region-selection policy and structural merge policy. These are independent contributors to the resulting document.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### B.3 `TransformersBackend`: multipass without vLLM

NVIDIA exposes a backend adapter for an already-loaded Transformers model:

```
from nemotron_parse.inference import (    DocumentParser,    TransformersBackend,)backend = TransformersBackend(    model,    processor,    generation_config=generation_config,)with DocumentParser(backend=backend) as parser:    document = parser.parse_triple(image)
```

The adapter reuses the same multipass image, crop and merge orchestration without an HTTP inference server.

Its documented behavior includes serialized model calls, inference mode, application of stage generation settings, and restoration of CPU/current-GPU random-number-generator state after generation. The caller retains ownership of the model and processor.

This reveals an important distinction:

- Execution capability: Triple-pass orchestration is available with the Transformers backend.
- Inference scalability: The shared Transformers model is serialized; the adapter does not provide the vLLM server's continuous batching or MTP acceleration.
- Compatibility: An existing Transformers model must still load and generate correctly under its runtime. The adapter does not remove model dependency constraints or prove compatibility with an arbitrary installed Torch/Transformers combination.

The public API additionally supports custom callable inference backends with the contract:

`backend(image, *, prompt, stage, settings)`

A backend may return `{"raw_out": ..., "finish_reason": ..., "usage": ...}` or just a string. The structured form supports stronger completion accounting; string-only backends must handle truncation detection themselves.

Custom backends used with `parse_many()` need concurrent-call safety, or concurrency should be limited to one.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### B.4 CLI and output artifacts

The installed `nemotron-parse` command supports single, double and triple modes:

```
nemotron-parse \
  --image-dir pages \
  --mode triple \
  --triple-regions union \
  --output parsed-pages
```

The default artifact set contains `documents.jsonl.gz` and `metrics.json`. Individual Markdown and JSON page files can be enabled with `--write-page-files`.

The compressed document output retains processed blocks, raw model stages, settings and timing metadata. Output files are written after the batch finishes; a partially completed batch should not be assumed to provide durable, incrementally written results.

The equivalent source invocation is `python -m nemotron_parse.inference`. The CLI consumes images rather than native PDFs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



Library boundary. `DocumentParser` can replace custom machinery for staging requests, cropping, parsing and combining predictions. It does not replace Docling's native PDF text extraction, table-cell provenance, document hierarchy model or source-to-product relationships.

## C. Merge policies, structural hypotheses and benchmark interpretation

Extends original §§7.7–7.8, 10.3 and 13.5

### C.1 Two different semantics for multipass output

The NVIDIA public package exposes two merge policies. `alternatives` is the default from package `3.5.0.post5` onward, including the guide's post7 baseline. `guarded` remains explicitly selectable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



| Property                                                     | `alternatives`                                    | `guarded`                                                |
| ------------------------------------------------------------ | ------------------------------------------------- | -------------------------------------------------------- |
| Overlapping but materially different Table/Chart predictions | May retain both                                   | Rejects competing same-class additions                   |
| Near-identical predictions                                   | Geometric/text deduplication                      | Conservative structural selection                        |
| Table refinement                                             | May preserve alternatives alongside direct blocks | Replacement subject to validity and compatibility guards |
| Output interpretation                                        | Multiple structural hypotheses can coexist        | More compact selected representation                     |
| Consequential risk                                           | Duplicate or contradictory content                | Discarding a correct crop alternative                    |

The distinction is representational rather than merely algorithmic.

With `alternatives`, the result can legitimately contain different textual or structural readings of the same page region. This can preserve evidence useful for independent reconciliation, but a consumer treating every emitted block as canonical content may count the same table twice.

With `guarded`, the merger favors a single accepted reading for overlapping same-class regions. This simplifies downstream interpretation but makes the acceptance policy responsible for suppressing alternative evidence.

Neither policy establishes the correctness of an accepted table. Both rely on model predictions and syntactic/geometric checks, not on externally verified ground truth.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### C.2 Why this affects accuracy measurements

NVIDIA's accuracy-restoration evaluation replayed saved model responses with different merge policies, thereby isolating the effect of merging from inference.

ParseBench overall scores (%), 2,078 pages; same saved responses within each row

| Response set      | Guarded | Alternatives | Difference |
| ----------------- | ------- | ------------ | ---------- |
| Double, staged    | 73.25   | 74.88        | +1.63      |
| Double, pipelined | 73.28   | 74.96        | +1.68      |
| Triple, staged    | 73.51   | 75.23        | +1.72      |
| Triple, pipelined | 73.48   | 75.23        | +1.75      |

Source: NVIDIA's official scorer replay recorded in `POSTPROCESSING.md`. Figures are vendor-reported, not independently reproduced here.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



The evaluator can credit the best-matching structural alternative in a prediction set. Consequently, a larger alternative set can improve the measured score without demonstrating that any particular selected table is equally accurate.

This creates three separate quantities:

1. Hypothesis coverage: Whether a correct interpretation appears among the emitted candidates.
2. Selection correctness: Whether the interpretation chosen as canonical is correct.
3. Representation consistency: Whether the final document has unambiguous, internally coherent structures.

The published alternatives scores primarily establish performance under the benchmark's evaluation semantics. They should not be interpreted as direct measurements of the other two quantities.

### C.3 Relationship to the original reference driver

The original document's detailed account of `build_direct_plus_ordered_structural_addonly()` and `replace_guarded()` remains useful because it describes the low-level reference implementation.

The public package adds a more explicit choice of the final structural semantics. That choice is absent from a description that treats add-only merging and guarded replacement as a single universal processing policy.

The distinct implementations should therefore remain identifiable:

- NVIDIA's reference-driver algorithms and their recorded benchmark configuration.
- NVIDIA's public `DocumentParser`, with configurable `merge_policy`.
- Docling upstream's native multipass implementation, with guarded merging only.

Even when all three use the same model, crop geometry and nominal stage settings, they are not guaranteed to produce equivalent final documents.

### C.4 Source evidence versus selected output

The public parser retains raw stage predictions under `stages`, regardless of the selected merge policy on successful completion. This preserves access to candidate evidence even when `guarded` omits an alternative from the final rendered document.

However, retaining raw responses is not identical to retaining a complete merge-decision trace. A complete audit of structural adjudication may additionally require the candidate-to-final-block correspondence, accepted/rejected decisions, transformation reasons and the exact merge-policy version.

That is a distinction between available source evidence and a fully materialized adjudication history; it does not imply that NVIDIA already supplies a complete decision ledger.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



## D. Public document postprocessing, tables and charts

Extends original §§7.9–7.10 and §§8–9

### D.1 `postprocess_document()` separates recognition from rendering

NVIDIA provides a reusable postprocessing interface that accepts an existing model response without requiring additional inference:

```
from nemotron_parse import (    PostprocessOptions,    postprocess_document,)options = PostprocessOptions(    infer_headers=True,    render_charts=True,    split_chart_value_percent=True,    relocate_chart_captions=True,)document = postprocess_document(    raw_model_output,    image_size=(width, height),    options=options,)
```

The returned representation includes:

| Field                  | Information preserved                                              |
| ---------------------- | ------------------------------------------------------------------ |
| `raw_out`              | Cleaned model block serialization                                  |
| `blocks[]`             | Individual structural blocks                                       |
| Block class and `text` | Original semantic class and literal predicted body                 |
| Block `content`        | Postprocessed presentation of that block                           |
| `bbox`                 | Normalized geometry                                                |
| `bbox_pixels`          | Clipped, ordered pixel geometry when image dimensions are supplied |
| `markdown`             | Rendered complete-page output                                      |
| `warnings`             | Detected structural or conversion problems                         |

The distinction between `text` and `content` is important: a structural block can preserve its model transcription even when the renderer converts tables, transforms captions or changes formatting.

This allows recognition and presentation to be evaluated separately. For example, a malformed table can be retained as model evidence with a conversion warning rather than silently turned into an apparently valid but incorrect grid.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### D.2 Cleanup controls and preservation behavior

The postprocessor exposes independent switches for:

- `normalize_text`: normalization of supported textual content.
- `deduplicate`: exact duplicate block removal.
- `infer_headers`: structural inference of table headers.
- `render_charts`: chart-specific presentation conversion.
- `split_chart_value_percent`: separation of consistently predicted numerical value/percentage pairs.
- `relocate_chart_captions`: geometric association and relocation of captions.

The documented cleanup handles incomplete serialization prefixes, internal continuation markers, soft hyphens and list markers. It preserves empty table cells, merged spans, nested inline formatting, escaped literals and line breaks where applicable.

Importantly, normalization is sensitive to semantic roles. Code and mathematical content receive protection against text-oriented cleanup that could change operators, identifiers or LaTeX content. Literal tabular LaTeX in prose is not indiscriminately converted as though it were a predicted `Table` block.

These transformations are best understood as syntax and presentation processing, not independent recognition or verification. The postprocessor does not determine whether a visually ambiguous digit was correctly read.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### D.3 Table export fidelity

The existing `postprocess_text(..., cls="Table", table_format=...)` interface supports multiple representations with materially different preservation guarantees.

| Format            | Distinctive behavior                                         | Information-loss consideration                      |
| ----------------- | ------------------------------------------------------------ | --------------------------------------------------- |
| LaTeX             | Preserves the original tabular notation                      | May retain malformed or ambiguous markup            |
| HTML              | Represents merged cells through table structure              | Does not supply original PDF cell geometry          |
| Markdown          | Readable tabular presentation                                | Limited native representation of complex spans      |
| Record JSON       | Tabular records with named columns                           | Flattens merged-cell topology                       |
| Hierarchical JSON | Adds `body_cells` with explicit text, spans and header roles | Still lacks model-predicted per-cell bounding boxes |
| CSV               | Flat interchange format                                      | Loses merged-cell structure and presentation roles  |

NVIDIA's converter applies several important safeguards:

Span handling. Flat exports expand merged cells, whereas HTML and hierarchical JSON preserve structural information about spans. `body_cells` supplements the familiar `headers`, `columns` and `data` fields.

Headerless tables. When there is no defensible header, the converter uses neutral column names instead of consuming the first data row as a header.

Duplicate column names. Headers are disambiguated without overwriting corresponding data values.

Malformed markup. Invalid LaTeX is preserved and reported rather than passed through a lossy row-splitting fallback.

Header inference. Inference uses predicted cell-span topology and formatting evidence such as bold text, not an English vocabulary list. It can still misclassify headers and is therefore optional.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



These features can avoid custom table normalization machinery. They do not recover spatial information that the underlying model never predicted.

In particular, a hierarchically preserved Nemotron table is not equivalent to a Docling TableFormer table with individual PDF-coordinate cell boxes. Structural completeness and geometric grounding remain separate capabilities.

### D.4 Chart semantics and presentation

NVIDIA's chart rendering recognizes chart-related titles, panels and associated data tables. It supports two additional transformations that change the output representation.

Value/percentage splitting applies to consistently formatted values such as `32 (16.6%)`. When at least two nonempty cells match the expected pattern, the renderer can construct distinct Value and Percent columns. This operation separates existing predicted values; it does not recalculate percentages.

Caption relocation can move an adjacent plain caption above a chart when geometric and text-preservation checks pass. Notes below charts remain separate. Disabling relocation retains the caption in its original sequence.

These operations matter when document structure is later used to associate charts with captions, panels or tabular series. A presentation transform can alter relationships or reading order without changing the underlying recognized characters.

The public CLI provides explicit opt-outs, including `--no-split-chart-value-percent` and `--no-relocate-chart-captions`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co+1



### D.5 Chart-panel identity in Docling

Docling's model catalog specifies that the Nemotron 3.5 mapping represents recognized charts as pictures with chart-classification metadata and data tables, creating a separate picture for each chart panel where applicable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This is more specific than a one-chart-to-one-picture assumption.

Consequences for document representations:

- One source chart region can produce several document objects.
- Panel-level object identity is not necessarily equivalent to page-level chart identity.
- Captions, charts and data tables may have different grouping semantics in NVIDIA's rendered output and Docling's mapped document.
- Model-predicted chart values are not automatically equivalent to values obtained through a geometric reconstruction of the plotted marks.

These distinctions are consequential for provenance, cross-layer comparison and downstream consumers that expect one chart object per visible chart.

Sources:

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/6cbbc638b8fdb1d94d76d5b9830d43e55da290ad/POSTPROCESSING.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/6cbbc638b8fdb1d94d76d5b9830d43e55da290ad/POSTPROCESSING.md?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md](https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md?utm_source=chatgpt.com)

## E. Prepared batches, pipelined scheduling and inference diagnostics

Extends original §§4, 5, 11 and 13.8

### E.1 Prepared image batches

`DocumentParser.prepare(images, workers=...)` converts input images into a reusable in-memory batch containing decoded RGB pixel data and encoded inference payloads.

Existing compatible RGB JPEG, PNG and WebP payloads can be retained without an additional lossy encoding pass; other inputs are encoded as PNG.

Preparation is separated from inference timing, allowing the same prepared images to be used across different parsing modes without conflating initial image decoding with model-serving performance.

The tradeoff is retained memory. NVIDIA explicitly warns that thousands of prepared pages can occupy several gigabytes. This is an in-memory batch facility, not a persistent content-addressed cache. Reusing prepared inputs does not reuse model predictions; each parse invocation generates its own responses.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### E.2 Dependency-aware `pipelined` versus `staged` execution

`parse_prepared()` exposes two scheduling semantics:

| Scheduling mode | Execution model                                                                                 |
| --------------- | ----------------------------------------------------------------------------------------------- |
| `staged`        | Stage-barrier execution, useful for controlled comparisons                                      |
| `pipelined`     | Overlaps independent work and dispatches dependent crops as soon as prerequisites are available |

In pipelined triple-pass execution, full-page parsing and detection can proceed independently. Detector-derived crops can begin when their regions are ready. Parser-only regions are subsequently added according to the union policy. In double-pass mode, crops can start as individual page predictions finish rather than requiring the entire batch of pages to complete first.

The executor uses one shared bounded concurrency window across all stages. Crop preparation can execute on separate CPU threads, and completed pages can be merged and rendered while other pages continue inference.

This is an important architectural distinction from launching three separately bounded request pools. The shared request window constrains total submitted work and avoids introducing independently competing inference queues.

The `postprocess_workers` setting controls output-side parallelism. Large batches may use spawned processes for rendering; ordinary standalone Python scripts therefore need the usual process main guard, or `postprocess_workers=1` where process spawning is unsuitable.

A Transformers backend wrapping a single shared model remains serialized even when the surrounding orchestration supports concurrent work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### E.3 Throughput metrics have different denominators and time boundaries

Beginning with `nemotron-parse` 3.5.0.post6, NVIDIA distinguishes model prediction throughput from complete pipeline throughput.

| Metric                                | Interpretation                                                          |
| ------------------------------------- | ----------------------------------------------------------------------- |
| `inference_seconds`                   | First model request start through last model response across all stages |
| `inference_pages_per_second`          | Processed pages divided by inference wall time                          |
| `complete_inference_pages_per_second` | Fully completed pages divided by the same inference wall time           |
| `pipeline_seconds`                    | Broader processing wall time, including final merge/render work         |
| `processed_pages_per_second`          | Complete pipeline's processed-page rate                                 |
| `request_service_seconds`             | Sum of request service durations, including server queue wait           |
| `peak_inflight_requests`              | Peak client-side request window occupancy                               |

Inference wall time includes HTTP transfer, server queueing, model work and delays waiting for crop dependencies. It excludes initial preparation, startup/warmup, final rendering after inference and file writing.

Because request execution overlaps, summed request times are not wall-clock GPU compute. Similarly, the client in-flight count is not a direct observation of vLLM's active decoder slots. Server-side scheduling and actual GPU utilization require separate instrumentation.

These definitions prevent several superficially plausible but invalid performance comparisons.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### E.4 Interpreting NVIDIA's throughput measurements

NVIDIA's reported prediction-throughput measurements for prepared ParseBench pages used one H100 80 GB GPU, the specified vLLM uni/FA3/MTP serving profile and 2,078 pages.

The restored-quality configurations reported 15.42 pages/s single-pass, 11.65 double-pass and 10.62 triple-pass. The triple-pass run had 2,038 fully completed pages out of 2,078; its processed-page rate includes token-limited pages.

These measurements do not include complete PDF ingestion, model startup or output-file serialization. They are also not measurements of single-page latency or maximum attainable hardware throughput.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



The earlier scheduler comparison found a substantial triple-pass pipelining benefit under a guarded merge, but also lower benchmark accuracy under that policy. Throughput and quality must therefore be compared using compatible merge semantics and sufficiently comparable inference settings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co+1



### E.5 Strict and partial-generation contracts

The public parser distinguishes inference failures from semantically uncertain but syntactically completed output.

By default, empty, failed, filtered and token-limited generations raise `GenerationError`. The exception exposes the failing stage and response. This makes failure visible at the inference boundary instead of silently accepting incomplete content.

With `allow_partial=True`:

- Token-capped raw responses can be retained.
- Affected documents are marked `complete=False`.
- `generation_warnings` describe incomplete generation.
- Truncated crops are excluded from structural refinement.
- Transport failures and empty responses still raise errors.

This is not an automatic continuation or retry framework. Successful stage responses and structured outputs remain available on successful completion, while errors expose the failed response; the API does not promise a fully assembled partial history for every exception.

The distinction is particularly important for downstream document processing: `finish_reason="stop"` means the generation terminated normally, not that the page was fully or correctly transcribed. Conversely, a page with `complete=False` may still contain useful partial evidence.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



### E.6 Structured inference evidence

NVIDIA's public document result contains two especially useful evidence families.

`stages` preserves original stage-level model responses and usage. This distinguishes source predictions from final postprocessed text.

`inference` records execution settings and derived operational information, including request counts, region configuration, sampling, crop configuration and rendering configuration.

The batch result adds aggregate metrics concerning request volume, generation completeness, timing and processing throughput.

These mechanisms provide more than the reference driver's final Markdown and merge counters, but they should not be confused with calibrated correctness estimates. Request counts, token limits, postprocessing warnings and model agreement describe different properties of a conversion.

Source:

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md?utm_source=chatgpt.com)

## F. NVIDIA NIM 2.4: a separate production serving interface

Extends original §4 and §13.2

### F.1 Document-oriented API rather than chat completions

NVIDIA released Nemotron Parse as a standalone NIM in version 2.4. This is separate from the `nemotron-parse` Python package and the model's vLLM plugin.

The NIM introduces a breaking serving interface relative to the earlier VLM NIM:

| Aspect                 | OpenAI-compatible vLLM server       | Standalone Parse NIM 2.4             |
| ---------------------- | ----------------------------------- | ------------------------------------ |
| Primary endpoint       | `POST /v1/chat/completions`         | `POST /v1/parse`                     |
| Image transfer         | Image in chat message               | Multipart `document` file            |
| Model prompt           | Caller can submit task prompts      | Fixed full-page parse prompt         |
| Detection-only request | Supported by the model-serving path | Not supported                        |
| Sampling configuration | API request parameters              | Owned by NIM                         |
| Per-request output cap | Generative model parameters         | `options.decoding.max_output_tokens` |
| Response content       | `choices[0].message.content`        | `content`                            |

The standalone NIM returns model-style content containing Markdown, bounding boxes and semantic class tokens. It does not directly return a `DoclingDocument` or NVIDIA's complete `DocumentParser` multipass result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA NIM for Nemotron Parse+1



### F.2 Input, output and preprocessing limits

The NIM accepts exactly one rendered page per inference request in PNG or JPEG form. It does not accept native PDFs or multi-page batches through `/v1/parse`.

Additional documented limits:

- Both source image dimensions must be at least 17 pixels.
- A complete multipart request cannot exceed 100 MiB.
- Preprocessing preserves aspect ratio while fitting content within 1,664 pixels wide by 2,048 pixels high, with padding as required.
- The default and maximum generation limit is 9,000 tokens.
- The response contains `content`, `finish_reason` and `usage.output_tokens`.
- `finish_reason="length"` indicates that the output limit was reached; no resume or continuation API is provided.

The 9,000-token NIM limit is distinct from the 8,744-token setting used in the reference vLLM pipeline. These service-specific limits should not be silently interchanged.

At the maximum output limit, a dense page may still be incomplete. Cropping and separate inference can address some such cases, but the standalone NIM does not perform the reference triple-pass detection and union workflow itself.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA NIM for Nemotron Parse+2



### F.3 Additional transport and service controls

The NIM also supports optional KServe V2 gRPC inference. The gRPC listener is disabled by default and can be enabled independently of the HTTP interface. This is a distinct transport contract, not an OpenAI chat-completions interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA NIM for Nemotron Parse



Its runtime exposes controls for:

| Control                         | Function                                                                     |
| ------------------------------- | ---------------------------------------------------------------------------- |
| `NIM_PIPELINE_MAX_BATCH_SIZE`   | Concurrent decoder-slot capacity, 1–256                                      |
| `NIM_PERFORMANCE_MODE`          | Raises default decoder-slot capacity to 128 when no explicit capacity is set |
| `NIM_SERVER_MAX_QUEUE_SIZE`     | Bounded waiting queue, default 1,024                                         |
| `NIM_SERVER_FAIL_FAST`          | Rejects new work when reserved/active capacity is exhausted                  |
| `NIM_SERVER_REQUEST_TIMEOUT_S`  | Work deadline including queueing and inference                               |
| `NIM_PIPELINE_TIMING_TELEMETRY` | Diagnostic timing logs                                                       |
| `NIM_PIPELINE_VRAM_TELEMETRY`   | Per-iteration process GPU-memory diagnostics                                 |

Queue capacity and decoder capacity are independent controls. Increasing the waiting queue does not increase the number of simultaneous decoding slots.

The NIM also provides model download-only, CUDA precompile-only and persistent precompile-cache facilities, which separate checkpoint staging and kernel preparation from normal server startup.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA NIM for Nemotron Parse



### F.4 Observability boundaries

The service exposes `/v1/metrics` in Prometheus format, along with separate liveness and readiness endpoints.

Its metrics include request/error counters and sampled host, process and GPU statistics. NVIDIA explicitly documents that NIM 2.4 does not provide OpenTelemetry support, a Parse latency histogram or a built-in pages-per-second metric.

Operational tracing can use Rust-style logging filters through `RUST_LOG`, configurable log formats, and optional timing/VRAM telemetry. Detailed GPU memory telemetry adds diagnostic overhead and should not be mistaken for cost-free measurement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA NIM for Nemotron Parse



### F.5 Availability and integration boundaries

NIM 2.4's documented support matrix covers specified NVIDIA data-center and professional GPUs in BF16. Consumer GPUs not listed in that matrix should not be assumed to have validated NIM support, even if other Transformers or vLLM runtimes can serve the underlying model.

The key architectural constraint is protocol capability: the NIM fixes full-page parsing and does not expose detection-only requests, so it cannot directly satisfy the triple-pass stage contract without another detector or another serving route.

Its service-level batching, admission controls and diagnostics can be valuable independently of that restriction.

Sources:

[https://docs.nvidia.com/nim/ingestion/parse/latest/overview.html](https://docs.nvidia.com/nim/ingestion/parse/latest/overview.html?utm_source=chatgpt.com)

[https://docs.nvidia.com/nim/ingestion/parse/latest/use-the-api.html](https://docs.nvidia.com/nim/ingestion/parse/latest/use-the-api.html?utm_source=chatgpt.com)

[https://docs.nvidia.com/nim/ingestion/parse/latest/environment-variables.html](https://docs.nvidia.com/nim/ingestion/parse/latest/environment-variables.html?utm_source=chatgpt.com)

[https://docs.nvidia.com/nim/ingestion/parse/latest/observability.html](https://docs.nvidia.com/nim/ingestion/parse/latest/observability.html?utm_source=chatgpt.com)

[https://docs.nvidia.com/nim/ingestion/parse/latest/support-matrix.html](https://docs.nvidia.com/nim/ingestion/parse/latest/support-matrix.html?utm_source=chatgpt.com)

## G. Docling serialization fidelity and resource lifetime

Extends original §§2.3, 9.4 and 9.5

### G.1 Inline mathematics survives supported exports

Docling 2.145.0 includes the fix from PR #4908, Preserve native VLM inline math through exports.

The shared math-aware renderer improves conversion of model-generated inline LaTeX into document structures that survive serialization. In particular, mathematical subscripts, operators and other Markdown-sensitive characters no longer necessarily degrade into escaped or reinterpreted plain text during export.

The implementation distinguishes mathematical spans from literal text, including nearby currency expressions, and is shared across relevant VLM adapters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



This fixes an important preservation issue but does not add recognition capability to `StandardPdfPipeline`. It also does not supply individual PDF-coordinate boxes for inline formulas that the VLM predicted only as text embedded inside a larger block.

Source:

[https://github.com/docling-project/docling/pull/4908](https://github.com/docling-project/docling/pull/4908?utm_source=chatgpt.com)

### G.2 `InputDocument.release()`

Docling 2.145.0 adds a public release operation:

```
result.input.release()
```

This unloads the input backend and clears its reference while preserving input metadata and the converted document.

The documented behavior includes safe repeated calls and safe handling of inputs without an active backend. If unloading raises an exception, the reference remains available so cleanup can be retried.

This is a resource-lifecycle interface for conversion inputs, not a mechanism for modifying document structure or recognition results.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### G.3 Page-backend reference cleanup

The same release fixes retention of page-backend references after pipeline unloading.

Previously, some enrichment-enabled conversions could retain native page-backend objects in the returned conversion result even after calling `unload()`. The threaded PDF page backend's unload operation did not itself dispose of all referenced native parse structures.

The change clears `page._backend` references after unloading. Upstream validation reported unchanged output documents while eliminating retained page-backend objects in the tested workload.

This distinguishes two different resource-lifetime concerns:

- Releasing an input-document backend through the public `InputDocument.release()` method.
- Automatically dropping page-backend references retained by the conversion pipeline.

Neither operation is a general-purpose release mechanism for every externally retained page image or document-derived artifact.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Sources:

[https://github.com/docling-project/docling/pull/3600](https://github.com/docling-project/docling/pull/3600?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/pull/5089](https://github.com/docling-project/docling/pull/5089?utm_source=chatgpt.com)

[https://github.com/docling-project/docling/releases/tag/v2.145.0](https://github.com/docling-project/docling/releases/tag/v2.145.0?utm_source=chatgpt.com)

## H. Cross-layer capability distinctions

Supplement to original §§10–13

The additional functionality changes how the three software layers can be combined, but it does not eliminate their semantic differences.

### H.1 Raw block predictions versus rendered document content

The formats exposed by NVIDIA and Docling should be distinguished at three levels:

| Representation                       | Primary value                                                           | Limitation                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Nemotron raw coordinate/class stream | Original model-produced spatial and semantic predictions                | Requires grammar validation, normalization and mapping                      |
| NVIDIA postprocessed document        | Cleaned blocks, presentation content, table/chart conversions, warnings | May contain overlapping structural alternatives or transformed presentation |
| Docling `DoclingDocument`            | Hierarchical document objects and standardized serialization            | Mapping may normalize, combine or drop parts of the raw prediction          |

NVIDIA's complete-page `markdown` is not a substitute for its coordinate/class-tagged block stream when using Docling's Nemotron-specific parser. The Docling mapper depends on those structural annotations to construct items and provenance.

Conversely, simply mapping the raw stream into Docling does not reproduce every feature of NVIDIA's postprocessor, such as its alternative-hypothesis semantics, hierarchical table JSON or optional chart-caption transformations.

This is an inference from the two documented interfaces, not a claim that a particular combined implementation has been tested.

### H.2 Recognition evidence versus derived presentation

A parsing pipeline can retain several distinct representations of the same recognized content:

- Raw inference evidence, including model output and per-stage settings.
- Parsed structural elements and their coordinate frames.
- Normalized text/table/chart content.
- A selected or alternative-preserving merged document.
- Serialized Markdown, HTML, JSON or another consumer-facing format.

Each transformation introduces its own possibility of information loss or reinterpretation. Retaining only the final presentation can discard information necessary to understand whether an error originated in visual recognition, structural merging, normalization or serialization.

The public NVIDIA APIs supply several of these layers directly, reducing the need to rebuild prediction parsing and generic table/Markdown rendering logic. They do not automatically provide an independent provenance relationship to native PDF text, glyphs and vector graphics.

### H.3 Completion, confidence and agreement remain different concepts

The added interfaces increase observability without establishing calibrated extraction certainty.

`finish_reason`, `complete`, `generation_warnings`, postprocessing warnings, merge rejections and cross-model agreement answer different questions:

| Signal                               | What it establishes                                   | What it does not establish                                |
| ------------------------------------ | ----------------------------------------------------- | --------------------------------------------------------- |
| Generation completed                 | A request ended within its generation contract        | Every page element was recognized                         |
| Valid structural parse               | Output satisfies implemented syntax/geometry checks   | Text and values are visually correct                      |
| Guarded merge accepted               | A candidate meets the selected compatibility criteria | The selected candidate is better than alternatives        |
| Alternatives retained                | Multiple plausible predictions remain available       | One canonical interpretation has been identified          |
| Two recognizers agree                | Predictions are similar under a comparison measure    | Errors are independent or the agreed text is correct      |
| Full-page coverage by bounding boxes | Spatial regions received model output                 | Every visible glyph or semantic relationship was captured |

This distinction is particularly relevant to inline mathematics, table cells and charts, where semantic correctness can depend on a single character or structural relationship.

### H.4 Remaining boundaries of verified functionality

The newly verified capabilities do not resolve runtime-specific GPU compatibility, word-level localization of Nemotron predictions, source-qualified reconciliation with native PDF glyphs, or correctness of any particular PDF corpus.

Nor do the public multipass wrappers establish a universal table/chart adjudication method that converts alternative hypotheses into independently verified canonical content.

The existing reference's uncertainty treatment should therefore remain intact. These additions establish what the libraries can perform natively, not what any particular deployment will achieve.

## Additional primary-source reference map

The following are the most useful sources for the capabilities added above. URLs are provided in plain text for independent retrieval.

| Source                              | Coverage                                                                                  |
| ----------------------------------- | ----------------------------------------------------------------------------------------- |
| Docling upstream model catalog      | Current Nemotron preset, native multipass options, sampling, guarded merging and metadata |
| NVIDIA postprocessing documentation | Public parser, backend adapters, merge policies, rich table/chart conversion              |
| NVIDIA package declaration          | Released package version, dependency bounds, extras and entry points                      |
| NVIDIA NIM 2.4 documentation        | Separate REST/gRPC protocols, service controls and observability                          |
| Docling 2.145.0 release notes       | Released inline-math, backend-lifetime and cleanup changes                                |

Docling model catalog

[https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md](https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md?utm_source=chatgpt.com)

Docling pinned release

[https://github.com/docling-project/docling/releases/tag/v2.145.0](https://github.com/docling-project/docling/releases/tag/v2.145.0?utm_source=chatgpt.com)

NVIDIA public postprocessing and multipass API

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md?utm_source=chatgpt.com)

NVIDIA package metadata and version constraints

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/pyproject.toml](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/pyproject.toml?utm_source=chatgpt.com)

NVIDIA model card, licensing and benchmark scope

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/README.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/README.md?utm_source=chatgpt.com)

The model card identifies OpenMDW 1.1 as the model's governing license, with separate MIT tokenizer attribution and third-party notices. These boundaries matter when distinguishing model weights, independently installed runtime dependencies and redistributed tools.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

nvidia/Nemotron-3.5-Parse at main+1



NVIDIA standalone Parse NIM 2.4

[https://docs.nvidia.com/nim/ingestion/parse/latest/release-notes.html](https://docs.nvidia.com/nim/ingestion/parse/latest/release-notes.html?utm_source=chatgpt.com)

NVIDIA inference-throughput methodology

[https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/213eed554008e633b1150977049a8c66b7717852/POSTPROCESSING.md?utm_source=chatgpt.com)

Documentation status: This addendum is grounded in upstream documentation, tagged-release information and source descriptions available as of November 1, 2026. No inference workload, GPU compatibility test or independent benchmark reproduction was performed.