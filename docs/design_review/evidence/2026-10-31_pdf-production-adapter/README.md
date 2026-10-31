# Production PDF adapter: bounded native conversion

**Outcome: partial. Verified 2026-10-31.** One real physical-page85 conversion passed using the
production adapter, current application environment and cached models in offline mode. This is
not whole-book, database publication, pipeline adoption, recognition fidelity or inline/cell
coverage qualification. The root owns record finalization and assembled applicability.

## Native execution

Command (from the producer worktree):

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=$PWD/python/corpus-structure/src /home/paul/corpus-structure/.venv/bin/python docs/design_review/evidence/2026-10-31_pdf-production-adapter/adapter_probe.py
```

The actual invocation redirected stdout/stderr to `raw/run.log`. `raw/result.json` preserves the
source/native identities, versions, stage providers and attributable formula outcomes. Source
scope is explicitly physical page85 of the retained original, not a complete book product.

- Docling 2.145.0 / core 2.105.0 / parse 7.24.2; native schema 1.10.0.
- Layout, table and formula execution observed on `cuda:0`.
- RapidOCR detection/classification/recognition sessions observed `CPUExecutionProvider`,
  matching the explicitly selected CPU-OCR recipe rather than an implicit GPU fallback.
- Native conversion status `success`, no reported errors; two formula inference outcomes
  `succeeded`, 37 indexed native nodes and 33 regions. Inference success does not establish fidelity.
- Raw native JSON, validation schema, recipe and concrete effective options retained. Formula
  text remaining unchanged is not used to infer success. Native model configuration warnings
  remain in the log.

The native call preceded the immutable-input-stream and final projection-order/derived-health
repairs. Its receipt establishes native options/enrichment/provider behavior only; it is not
qualification of the final input-custody path. Twelve focused controls subsequently passed on
the application interpreter, including input mutation during initialization, swallowed inference
failure, output-cardinality mismatch, native rich-cell links, wrong derived-health bindings,
intact section hierarchy and no-inference non-PDF refusal. Controls using a fake inference engine
are explicitly failure/contract controls, not native provider or model-fidelity evidence.

## Final-source projection replay

```sh
PYTHONPATH=$PWD/python/corpus-structure/src /home/paul/corpus-structure/.venv/bin/python docs/design_review/evidence/2026-10-31_pdf-production-adapter/projection_probe.py
```

This reuses retained native JSON without inference and writes
`raw/page85.final-projection.payload.json`. The initial payload remains alongside it. The final
projection uses body preorder, furniture preorder, then sorted unvisited pointers, and retains
per-formula health. Application/native SQL publication remains separately required.

Full-book conversion, complete replay asset custody (including table/OCR assets), inline and
ordinary-cell discovery, model-bound admission, independent evaluation and adoption remain open.
