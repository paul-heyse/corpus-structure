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


## Integrated foundation checks — 2026-10-31

These checks establish bounded foundations, not completed PDF-02–PDF-11:

- **passed:** `just ready` after dependency integration.
- **passed:** `just types` (warning-inclusive Pyrefly, zero diagnostics, no suppressions).
- **passed:** `uv run pytest python/corpus-structure/tests/semantic/test_native_documents.py tests/test_pdf_contracts.py tests/test_pdf_conversion.py tests/test_pdf_math.py -x --tb=short`:
  43 controls at that source. The subsequent whole-document-demand control passed in the
  separate final contract run below. Restricted actual PostgreSQL publication exercises original
  retention in a prior transaction, native JSONB, geometry, replay, no rendition dependency and
  independent omitted/forged projection rejection. Independent fixtures are functional controls,
  not recognition-fidelity evidence.
- **passed:** `uv run pytest tests/test_pdf_contracts.py -x --tb=short`: 17 controls, including
  explicit page-range scope refusing a whole-document demand.
- **passed:** `uv run pytest python/corpus-structure/tests/semantic/test_archive_reader.py python/corpus-structure/tests/semantic/test_parsing_contracts.py python/corpus-structure/tests/semantic/test_contracts.py -x --tb=short`: 59 controls.
- **passed:** `uv run pytest python/corpus-structure/tests/core/test_text_structure.py python/corpus-structure/tests/math/test_prepared.py -x --tb=short`: 19 controls.
- **passed:** `uv run python docs/design_review/evidence/2026-10-31_pdf-production-adapter/projection_probe.py`:
  current native publication payload, archived schema and retained original prepared successfully,
  37 items/33 regions. The new `raw/page85.qualified-projection.payload.json` retains explicit
  page-range scope and corrected layer values; earlier outputs remain unchanged.
- **failed (interrupted, no acceptance credit):** broader selection of the entire math directory,
  core text structure and the three semantic files above entered the legacy 78-page HTML corpus
  fixture; interrupted after 103 seconds with no tests completed. Owned subprocesses drained.
  This does not undo the bounded passing invocations above.
- **not_run:** full-book conversion, final-input-path native inference, operational cutover,
  complete provider/evaluation journeys, `just test-all` and complete hygiene.

Initial native integration attempts failed on deployment descriptor hash correspondence, fixture
construction/project custody, a layer enum encoding and SQL aliases. Corrected restricted tests
passed; initial attempts are not relabeled as passes. No historical operational database was
upgraded. Source compiler ABI12 and native0047 support these foundations; active consumer migration
and full qualification remain with the coordinator. Formatting-only maintenance does not invalidate
unaffected passing test/type evidence.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Native PDF production foundations](records/pdf.production-foundations.json) | PDF-02 | partial | PDF-01, PDF-02, PDF-03, PDF-04, PDF-05, PDF-06, PDF-08, PDF-09 | 2026-10-31 |
<!-- evidence-index:end -->
