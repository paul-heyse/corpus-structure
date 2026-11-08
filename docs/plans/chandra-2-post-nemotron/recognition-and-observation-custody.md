# Recognition and observation custody

**Development path verified, recovery qualification open · 2026-11-08.** Companion to the [Chandra coordinator](../chandra-2-post-nemotron_2026-11-08.md). Owns O01's production boundary and O09's first local reference runtime.

<a id="CH-02"></a>
## CH-02 · Make a source-bound visual observation

### Request and result

Receive an explicit inspection request for a published integrated product pin and an original physical PDF page. The request may include a qualified page region. Authorize through the existing source/effect boundary. Resolve original bytes and verify the integrated ancestry. Use incumbent observations as scope and comparison evidence. Submit the selected original pixels. The output is a separately addressable Chandra observation with source, provider and recipe identity, attempt receipts, raw response, and bounded parsed evidence. The proposed output is visible only to an explicit evidence read.

Reuse the existing run/task attempt fence, request artifact retention and exact reuse owner. The current PDF observation model has A/B/C/native roles and the active mapper has Nemotron-specific behavior. Define a released provider-qualified Chandra page/crop role or additive evidence product under that owner after target review. Keep role meaning separate from the scheduled task and never relabel Chandra as an existing Nemotron pass. Assess semantic declarations, native publication guards and adjacent reads together. The role grants observation custody only. If a binding change is needed, resolve it through the coordinator's rule process. [PDF observation declaration](../../../python/corpus-structure/src/corpus_structure/model/semantic/pdf-products.yaml) · [Native fenced publication](../../../python/corpus-structure/src/corpus_structure/semantic/sql/pdf_observation.sql)

### Runtime, geometry and replay

- Use official checkpoint `datalab-to/chandra-ocr-2@af93b47dba1b47b6640c86ccf487ed2260ab9a09` with Docling 2.148.0 `VlmConvertOptions.from_preset("chandra_ocr2")`, `TransformersVlmEngineOptions(load_in_8bit=False)`, BF16, and pinned local artifacts. The preset selects `CHANDRA_OCR_LAYOUT_PROMPT` and `CHANDRA_HTML`. Verify the artifact and model-code trust before loading. Record effective device, kernel path, processor, prompt, render and decode settings. The probe used reference kernels and its timings describe that local panel. [Preset](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/stage_model_specs.py) · [Engine options](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/vlm_engine_options.py) · [Checkpoint](https://huggingface.co/datalab-to/chandra-ocr-2/tree/af93b47dba1b47b6640c86ccf487ed2260ab9a09)
- Reuse the PDF renderer and affine owners. Pin physical page, original geometry, CropBox/rotation and effective submitted pixels. Compose crop and resize transforms before admitting mapped boxes. Retain relevant raster or authorized artifact reference and the digest of the actual submitted image. Preserve missing or invalid geometry as unknown. An inherited region gives useful localization but does not create exact child geometry. [Current affine operations](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_recognition.py) · [Chandra image normalization](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/model/util.py)
- Retain the raw response before interpreting it. Replay through the exact `parse_chandra_html(..., normalize_heading_levels=False)` binding, with page or crop coordinates mapped through the recorded frame. Reuse existing document-wide hierarchy ownership when an assembled view actually needs normalization. Treat raw HTML and Mermaid as untrusted data for display. Chandra's `parse_layout` and `parse_chunks` are useful comparison views. Their malformed-box fallback and removal of nested geometry make raw custody necessary. [Tagged parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) · [Native output transforms](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/output.py)
- Keep inference completion, parseability, coverage, and fidelity separate. Preserve unspecified stop reason as unknown completion evidence even when parsing succeeds. Distinguish a blank source from missing output, truncation, repetition, filtered output, and error. Retain failed or interrupted attempts and resume exact pending work. A changed pixel or recipe invalidates inference reuse. A parser change can reuse raw bytes and must produce its own mapping identity. Use existing scheduler and cancellation semantics with one local GPU owner and release buffers outside publication locks. The native Chandra vLLM client returns a final retry result, so any future route must provide attempt-level custody independently. [Docling status handling](https://github.com/docling-project/docling/blob/v2.148.0/docling/pipeline/vlm_pipeline.py) · [Native retry behavior](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/model/vllm.py)

The raw payload is the exact text returned by the adapter after engine decoding and
stop-string handling. The submitted PNG is the render input to the checkpoint processor.
Neither records an independently resolved terminal token or the processor’s final grid.
Treat processor evidence as a scoped prerequisite where a higher-detail recipe needs it.
[Engine result conversion](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/vlm_convert/vlm_convert_model.py#L56-L82) ·
[Transformers completion handling](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/inference_engines/vlm/transformers_engine.py#L575-L643)

### Completion

Consume CH-01's qualified version and a real published source. Run a real bounded page and rotated crop. Check inverse coordinates against independently located source regions. Verify exact replay without model load, pinned-source mismatch and stale attempt refusal, reuse versus changed recipe, interruption and resume, valid blank, invalid boxes, malformed HTML, missing output, explicit length stop and unmarked repetition. Match the probe's raw and parsed standing separately. Demonstrate that an admitted observation is available to CH-03 and retains its raw evidence even if interpretation fails.

The coordinator retains F01 and F03 as open. [CH-10](automatic-routing-and-qualification.md#CH-10)
consumes the same fences and schedules the applicable recovery and handoff prerequisites
before automatic runtime qualification.
