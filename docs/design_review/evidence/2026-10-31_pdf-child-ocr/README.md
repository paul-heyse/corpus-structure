# Native child OCR and recognized word geometry

2026-10-31. **Tested**, bounded to the fixed sources below. This record covers the
finite native child, RapidOCR word output, and the selected PDF-aware OCR/replacement
behavior. It makes no whole-book or universal OCR/source-fidelity claim.

`prepare_sources.py` independently fixes two raster lines before inference:

- `Controlled raster input 314159.`
- `A second independent line.`

The raster is 1400×500 pixels in a 700×250-point PDF. The visible broken-layer
case adds white-filled, visibly rendered text without changing the rendered pixels;
the invisible-layer case uses an invisible text rendering mode. PDFium/Docling
extract the deliberately wrong Helvetica encoding as 80 `ÿ` characters. Docling's
visible-layer quality function flags the visible case; it excludes invisible text
from that decision. The three source render hashes agree. See
[the input manifest](inputs/manifest.json) for hashes, expected text, font identity,
and native visibility/quality assessment.

The retained initial 40-character fixtures and failed preparation log show the first
attempt did not reach Docling's 50-letter wrong-Latin threshold. They were superseded
by separately retained 80-character fixtures. This was a source-preparation failure,
not an OCR/provider failure. Source preparation now refuses a nonempty destination;
use `--output` with a new directory to reproduce it.

`probe_words.py` passed a direct CPU RapidOCR comparison with/without
`return_word_box=True`: identical recognized lines and eight provider word boxes.
The receipt records CPUExecutionProvider for detection/classification/recognition.
An initial import refusal is retained: the installed `RapidOCROutput` is exported
from `rapidocr.utils.output`, not RapidOCR's top-level package.

`qualify_child.py` passed three actual StandardPdfPipeline conversions through one
spawned `PdfWorker` (PID2298436), reusing its native models and then closing/joining
that child. Each native document contains both independently fixed lines exactly,
eight observed OCR words, complete recognized-line word coverage, and successful
conversion status. The page quality is `broken` only in the visible corrupt-layer
case; other cases are `not_flagged`, which records a library assessment rather than
truth about the original source. Actual selected OCR crops have nonzero page offsets
and scale3, qualifying the raster-to-PDF transform in the real native stage. Layout,
table, and formula stages report CUDA; OCR reports CPU. An initial preparation-field
refusal occurred before native child creation and is preserved separately.

Each report retains the source/recipe/native identity, package versions, effective
providers and candidate inventory; native JSON and schema are separate files. The
triplet script did not retain the entire effective-options/confidence objects from
the conversion, so it does not establish their complete external publication. Those
remain covered by the separate serialization/publication path and root integration.
The local PDF output schema is upstream-owned; the application's OCR companion
admission is separately qualified after its model/guard integration.

Recognized word boxes are estimates returned by RapidOCR's recognition machinery,
not original PDF glyph coordinates. Their original crop raster AABB, scale, offset,
orientation0 and transformed PDF AABB remain explicit. Word start/end coordinates
refer to the recognized OCR line. Native font/glyph evidence is not inferred from
OCR output. Missing or malformed word output produces partial/unknown discovery;
usable native content is retained. Full inline completeness is scoped by admitted
candidate policy and local source membership, and is never universal glyph absence.

Commands (from the runtime worktree with the shared application environment):

```sh
UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/.venv PYTHONPATH=$PWD/python/corpus-structure/src uv run python docs/design_review/evidence/2026-10-31_pdf-child-ocr/probe_words.py
UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/.venv PYTHONPATH=$PWD/python/corpus-structure/src uv run python docs/design_review/evidence/2026-10-31_pdf-child-ocr/qualify_child.py
UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/.venv PYTHONPATH=$PWD/python/corpus-structure/src uv run pytest tests/test_pdf_conversion.py tests/test_pdf_runtime.py tests/test_pdf_process.py tests/test_pdf_ocr.py -q
```

The focused functional union passed40 cases under the repository's strict/importlib
configuration. Six focused word/geometry controls also passed after adding the invalid-box
negative case; they cover omitting invalid provider words with partial local discovery.
The initial coverage control caught a real issue: deriving required
pages after inline decomposition omitted parents with children. Production now fixes
the source-page universe before mutation. The failed receipt is retained. Scoped
Pyrefly passed with0errors; its environment warning reports the explicitly selected
worktree PYTHONPATH. These controls use deliberate test doubles where necessary and
do not turn those into provider evidence; actual provider evidence is the native
triplet and direct CPU probe above.

Replays require fresh output destinations (`--output`) to preserve retained receipts.
