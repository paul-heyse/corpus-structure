# Retained dense-table preparation

This bounded probe reads the existing run10/task27 source view and retained linguistic
annotations. It tests POLICY3 context preparation at the actual task's character and
piece bounds. It performs no PDF conversion, OCR, GLiNER or general model execution.

Run `uv run python docs/design_review/evidence/2026-11-04_m1-dense-table-preparation/probe.py`.
Pass an unused output path to retain another result. The original `result.json` is
**partial**: 104 of 182 eligible cells were targeted; the omitted targets depended on
rich headers whose summary text was not their canonical projection. `inspect_cells.py`
and `cell-shape.json` retain the native shape investigation.

On 2026-11-04, **passed**:
`uv run python docs/design_review/evidence/2026-11-04_m1-dense-table-preparation/probe.py docs/design_review/evidence/2026-11-04_m1-dense-table-preparation/result-002.json`.
The retained table has 189 native cells and 182 eligible data cells. The revised
preparation targets every eligible cell once across 26 contexts, with no missing,
duplicate or foreign targets. The largest serialized context uses 189 characters and
39 intervals against the actual task's 2048-character and 64-interval limits. Rich
header text and child addresses come from the existing canonical native projector.
Preparation coverage does not establish extraction success or knowledge-capture accuracy.
