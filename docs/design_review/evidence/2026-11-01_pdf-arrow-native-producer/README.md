# Fresh native page IPC producer qualification

**Tested, 2026-11-01:** actual pinned StandardPdfPipeline/RapidOCR execution on original physical
pages 20 and 1211 passed through the current finite `PdfWorker.stream` producer. This is selected
native provider qualification for PDF-22/23 and I25. The PDF coordinator owns assembled acceptance.

The worker received the captured logical page schema as bytes, prepared its codec without a database,
and wrote candidate IPC once. Its synchronous replay callbacks verified actual schema, logical
identity and exact file custody. Native page envelopes used the prepared Pydantic serializer and
explicit native assembly classes. After each child settled, replay restored those exact classes and
its raster; independent pixel indexing checked the 1.67-scale crop against the retained raster.
Requesting an uncaptured 2.0-scale raster refused. The runtime report records requested 2.0 versus
effective 1.67 formula scale, backend/options classes, image borrowers and Arrow resource settings.

| Original page | Candidates | Complete OCR regions | OCR words | Formula outcomes |
|---|---:|---:|---:|---|
| 20 | 16 | 5 | 45 | 2 succeeded |
| 1211 | 34 | 2 | 181 | None selected by native pipeline |

Page 1211 retained its `ContainerElement` and `Table` assemblies and lowered a native `TableItem`.
Both workers closed with no process handle; the owned source copy was released after all borrowers.
Read-only GPU inspection before and after found only the existing Sunshine process (500 MiB).
No process, endpoint, server or GPU phase controller was changed.

Run from the repository root:

```sh
uv run python docs/design_review/evidence/2026-11-01_pdf-arrow-native-producer/native_cases.py docs/design_review/evidence/2026-11-01_pdf-arrow-native-producer/raw/run-1
```

The actual run redirected stdout/stderr to `raw/native-run-1.log`. `raw/run-1/results.json` retains
source/schema/IPC identities, original class inventories, actual OCR/formula outcomes, exact raster
and crop pixel hashes, requested/effective profiles and replay descriptors. The folder retains actual
page assemblies, rasters, candidate IPC and lowered record IPC. `native-replay-crop.png` is the
post-child crop control. Run durations are raw observations, not comparative performance results.

Environment: x86_64 Linux, RTX 5090, Python 3.14.10; Docling 2.145.0, core 2.105.0, RapidOCR 3.10.0,
ONNX Runtime 1.31.1, PyArrow 26.0.0, Pydantic 2.14.1 and PyTorch 2.15.0. Layout/formula use CUDA;
OCR uses CPU under the existing recipe. Model files were resolved offline from the existing qualified
bundle and verified; the exact immutable revisions and file manifests are retained with the run.

This does not establish independent OCR transcription accuracy, page-global versus whole-book
semantic equivalence, bounded global graph memory, PostgreSQL adoption/seal, current public reader
or export behavior, Nemotron service execution, integrated recovery or full-plan qualification.
Native reading-order/heading finalization continues to materialize its selected global graph.

## Records

<!-- evidence-index:start -->
<!-- evidence-index:end -->
