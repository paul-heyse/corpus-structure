# Grinstead–Snell whole-book development

The [NCE coordinator](../../../plans/next-corpus-enrichment_2026-11-07.md#full-book-execution)
owns current execution and the audit findings. [ADR-0070](../../../adr/0070-full-book-method-development.md)
selects the original 518 physical pages as one shared development origin. The
[original GS120 benchmark](../2026-11-06_wce-gs120/README.md) preserves its own
source selection, outputs and assessment.

The input is the exact parent `Introduction_to_probability_grinstead_and_snell.pdf`
with SHA-256 `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
Place a verified copy under `WORK/corpus/`. Use a copy within the selected corpus
directory so the native original registration's containment check applies.

```sh
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/intake.py WORK --release RELEASE
uv run ci run finalize RUN --output-realization nce-gs518-source-result:RUN --json
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/enrich.py RUN WORK/baseline --release RELEASE --phase inventory
```

The intake uses the existing registered graph with one explicit original, then
runs the annotation method over its selected views. The generic `ci project init`
route selects the pack's default original, so the evidence runner supplies the
existing project registration function with the exact one-file method configuration.
The inventory checks the native page membership and freezes source-only samples.
It reports physical coverage and text projection separately.

The Standard arm uses Docling's CUDA layout and formula models with in-page
RapidOCR on CPU. RapidOCR examines PDF-aware regions. For the combined arm,
start the [verified Nemotron service](../../../../services/nemotron-parse/README.md)
and bind the published Standard product from the same original:

```sh
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/recognition.py WORK
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/intake.py WORK \
  --release RELEASE --realization nce-gs518-source-integrated \
  --native-product TASK KEY SHA256
```

The integrated arm retains separate managed Nemotron Parse 3.5 parse, detect and
applicable Table/Chart crop responses across the exact page inventory. It reuses
the Standard product and retains its own selected reconciliation and annotations.
The optional first command prefills the same primary recognition receipts while
the Standard product settles. Integrated publication adopts those receipts and
performs the recipe's eligible recovery in its owned task.

On 2026-11-07 local time, primary recognition passed for all 518 physical pages.
The [primary recognition record](records/nce.gs518-primary-recognition.json)
accounts for one full-page parse and one layout detection per page, plus 210
applicable crop responses. All responses identify the same managed generation.
The host's installed NVML library did not match its loaded NVIDIA kernel driver.
The successful launch used process-local libraries extracted from the matching
NVIDIA 615.71.10 package. The launch command otherwise follows the verified service
route. This receipt establishes recognition coverage. Integrated publication and
the assessment of the selected content have their own acceptance boundaries.

On 2026-11-08 local time, the [Standard source record](records/nce.gs518-standard-source.json)
completed run 297 at cut 413. One organized native product retained all 518
physical pages. All 518 had a native region and projected content. All 29 selected
views finished annotation and the cut finalized 11,280 reports. The source-only
sample froze 78 occurrences across prose, cross-references, formulas, tables,
captions and headings.

Native validation took 706.7 seconds on the raw native product and 939.8 seconds
on the organized product, measured by the two completed `ops.validate_pdf_build`
calls. The initial finalizer was interrupted after a live stack sample found
repeated view loads for the 11,280 reports across 29 views. The process had about
29.6 GiB resident at the captured sample. Reusing each view within its existing
repeatable-read snapshot allowed an exact retry of the original sealed cut.

Combined attempt 298 refused a shared method version with a different configuration
schema. Fresh intake now uses version 3. Its retry, run 299, admitted all 1,246
managed recognition responses and reached correspondence staging. Two complete
relation envelopes exceeded the native inline representation limit. These attempts
retain their original status and exact recognition receipts.

Run `enrich.py` on the same pinned input with phases `scoped`, `model`, and
`artifact`. The scoped phase selects source-conditioned table correspondence.
The model phase selects the released bare/flat definition arm with the named
producer enabled. The artifact phase consumes the full eligible source inventory.
`contextual.py` consumes the exact scoped phase receipts and uses the book's
complete selected heading inventory for its eligible cue views. Each phase retains
its actual task scope and independent completion state.

Use the managed installed Reader and exact closure for evidence delivery. Keep
protected authoring and assessment material separate from source-only packets and
ordinary review bundles.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**next-corpus-enrichment**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Full Grinstead–Snell Nemotron primary recognition](records/nce.gs518-primary-recognition.json) | full-book | passed | ADR-0070 | 2026-11-07 |
| [Complete Standard full-book source and frozen opportunity inventory](records/nce.gs518-standard-source.json) | full-book | passed | ADR-0070 | 2026-11-08 |
<!-- evidence-index:end -->
