# PDF/Docling foundations and capability investigations

**2026-10-31 · partial investigation result.** Consumer:
[PDF coordinator](../../../plans/pdf-docling-pipeline_2026-10-31.md), PDF-00/01 and I01–I08.
ADR-0038 accepts the target; these probes do not deploy it.

## Environment and reproduction

The isolated `pyproject.toml`/`uv.lock` installs full
`docling[asr,easyocr,htmlrender,ocrmac,onnxruntime,rapidocr,remote-serving,tesserocr,vlm,xbrl]==2.145.0`.
No application manifest/lock/database/default was changed. `.venv` and external model caches are
ignored; no weights are committed. The environment physically lives at
`build/evidence-envs/pdf-docling-foundations`, with an ignored `.venv` symlink here to keep
third-party Markdown outside documentation discovery. For a fresh reconstruction, use
`UV_PROJECT_ENVIRONMENT="$PWD/build/evidence-envs/pdf-docling-foundations" uv sync --project docs/design_review/evidence/2026-10-31_pdf-docling-foundations`
and use the same explicit environment selection for probe commands, or recreate the ignored symlink. `raw/install.log` retains the actual uv add resolution;
`raw/inventory.json` records installed packages, extra imports, model snapshot IDs and source hash.
Host: Python 3.14.10, RTX5090 32GiB, CUDA13.2 Torch; available ONNX providers are not proof that
RapidOCR used CUDA. Native runs emitted CUDA-provider registration warnings: OCR GPU qualification
remains open. ocrmac is platform-inapplicable on Linux, not an omitted requested extra.

Commands (run from repository root):

```sh
uv run --project docs/design_review/evidence/2026-10-31_pdf-docling-foundations python docs/design_review/evidence/2026-10-31_pdf-docling-foundations/probe.py --pages 20:45
uv run --project docs/design_review/evidence/2026-10-31_pdf-docling-foundations python docs/design_review/evidence/2026-10-31_pdf-docling-foundations/probe.py --layout egret --pages 20:20,33:33,85:85,595:595
uv run --project docs/design_review/evidence/2026-10-31_pdf-docling-foundations python docs/design_review/evidence/2026-10-31_pdf-docling-foundations/health_probe.py
uv run --project docs/design_review/evidence/2026-10-31_pdf-docling-foundations python docs/design_review/evidence/2026-10-31_pdf-docling-foundations/math_probe.py
```

Each conversion exports native JSON, options, health summary and pinned layout/formula model
revisions. `probe.py` explicitly selects PDF-only StandardPdfPipeline, native-text-aware English
RapidOCR, table ACCURATE/cell matching, CodeFormulaV2 and heading hierarchy. The first native
model request failed DNS resolution; the successful retry is separate. Early probe filenames
used only a start page and a one-page comparison overwrote the initial 20–45 artifact; its log
is retained but that overwritten artifact gets no identity/preservation credit. The corrected
`heron-20-45.document.json` rerun has unambiguous range identity. I04 copied and hashed that input.

## Decisions and observed limits

| Item | Result and downstream consequence |
|---|---|
| I01 | Full installation resolved 204 packages; native selected stages ran, extras imports checked, snapshot/package identities retained. Hermetic offline model reconstruction and actual OCR CUDA provider remain unqualified; advertised providers are insufficient. |
| I02 | Both layouts converted pages20/33/85/595. `raw/comparison.json` preserves native outputs/counts; Egret gives no demonstrated reason here to replace Heron and loses a formula item on page33. Counts alone are not fidelity metrics. Retain Heron baseline; no crop-margin tuning was justified by observed contamination/repetition. |
| I03 | Native displayed formulas recognized. Controlled failing engine returns unchanged formula text, confirming label/text cannot certify recognition. Actual page85 table cells retain flattened `n k`, `n+k−1 k`, etc., rather than FormulaItems/rich references. Source rendering is `raw/source-85-table.png`; inspection establishes the four math-bearing cells, not whole-corpus quality. `cell_probe.py` successfully enriches one real cell from `n k` to `n ^ { k }`, creates its table-parented FormulaItem and rich-cell reference, and validates the derived document. See `raw/cell-result.json` and `cell-derived.document.json`. This proves one native mechanism, not complete table coverage or protected publication. Attributable production health and complete inline/table coverage remain PDF-04 work. |
| I04 | Native 26-page output has heading levels but zero SECTION groups. Public native grouping validates/reloads while preserving1093 original node references and all-layer reading order. Repeated Proof/Answer labels need domain qualification. See [I04](I04.md). |
| I05 | Bounded native SymPy probes retain actual recognized strings, native results and exceptions in `raw/math-results.json`. Most sampled strings include prose, sets or matrix-like notation unsupported by the default grammar. Direct LaTeX input is possible, but wholesale frontend retirement is not justified; PDF-06 must qualify required grammar/statement/occurrence capabilities. Native parser return alone is not mathematical correctness. |
| I06 | Actual Core/JSONB native roundtrip and independent malformed-reference/label/geometry/image controls. Validation-mode schema and native tree checks are required; serialization schema alone is insufficient. Scratch DBs were removed. See [I06](I06.md). |
| I07 | Representative conversion and document release ran; no full-book/live-memory/cancellation qualification. Finish with PDF-09; limits do not prove feasibility. |
| I08 | Document-level split requires dev-only calibration for this original; selected whole-section journeys and independently authored PDF references specified. Actual pointers/provider/evaluator/default adoption remain later. See [I08](I08.md). |

Native PdfPipelineOptions JSON is **not an executable replay ABI**. Revalidating the saved options
for the cell prototype loses a concrete picture-options type (`kind` missing); that failure remains
in `raw/cell-initial-failed.log`. Reconstruct options through explicit admitted typed recipes and
presets, archive exact values/classes/model revisions, and qualify replay. Do not pickle native
objects or assume a Pydantic serialization roundtrip preserves every polymorphic configuration.

## Evidence strength and remaining work

All raw failures remain failures, including the initial DNS, scratch teardown marker lookup,
hidden-layer hierarchy indexing and cell-prototype setup attempts. Native model successes,
controlled failure behavior, structural validity, datatype storage and source fidelity are
separate claims. No mocked/failing inference engine is credited as successful recognition.

No full-book conversion, production migration/publication, real packet or CLI/MCP product journey,
new reference/grade, throughput comparison or universal source-fidelity result was run here.
I01/I03/I05/I07 retain named unresolved integration obligations. Full installed breadth does not
mean every model/runtime has been exercised, nor that conditional capabilities are now selected.

## Additional prototype failures and remedies

`raw/cell-initialize-failed.log` records that `initialize_pipeline()` initializes the converter
cache but returns None; use the actual cached pipeline, not its return value.
`raw/cell-parent-failed.log` records native rejection of a rich-cell formula parented to body;
the corrected prototype parents it to the table. The actual successful receipt is `raw/cell.log`.
The supported enrichment stage is composed from native objects in an isolated probe; production
adapter admission, per-item health and full scope support remain PDF-02/04 obligations.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [PDF-native Docling foundation investigations](records/pdf.foundations.json) | PDF-01 | partial | PDF-00, PDF-01, I01, I02, I03, I04, I05, I06, I07, I08 | 2026-10-31 |
<!-- evidence-index:end -->
