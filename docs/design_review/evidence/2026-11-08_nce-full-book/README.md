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

Combined run 309 published the integrated native product after segmenting two
large relation endpoint fields and their two evidence fields. The product
retains 51,390 relations, 32,338 occurrences and 1,247 input pins. An edit to the
runtime package during run 309 changed the worker identity before its annotation
claims, so those claims could not continue. Run 312 adopted the exact published
product without repeating recognition or reconciliation. The [combined source
record](records/nce.gs518-integrated-source.json) retains cut 431, 29 completed
annotated views and 9,975 reports.

All 518 combined pages retain native regions. The page census directly joins
projection pieces to regions on 515 pages. The table of contents on page 4 and
the caption on page 119 project inline children whose containing nodes carry
the page regions. On page 506 the selected item is a running header and has no
body projection. The organized Standard source retains projected content on
all 518 pages. The two source products retain distinct output receipts.

To adopt the published combined product and continue annotation without inference,
pass `--integrated-product TASK KEY SHA256` to `intake.py`, then finalize the
adoption run and inventory it. Use `--native-product` when creating a new
combined product from the Standard source.

The [artifact record](records/nce.gs518-artifact-trigger.json) covers all 29
views at run 300/cut 417. It retained 596 records and nominated 530 pairs,
including 483 reference-only and 47 with unavailable namespaces. Zero pairs
qualified for same-lineage scoring. Managed exact review `878e1c7f363140ec9d7f7671b609716d`
passed detached verification and is held.

The bare/flat GLiNER 2.5 producer finished all four selected partitions at runs
301, 304, 305 and 306. Its located-extraction stages report 595 succeeded, 10
empty, 99 failed and seven `not_run`. Attachment stages report 32 succeeded,
541 empty, 61 failed and 99 `not_run`. These are stage dispositions, independent
of the four completed producer reports. Source support remains a separate
assessment. Old scoped run 302 reached the native 120-second completion deadline
on a report of about 50 MB. The dedicated contextual watcher was stopped after
that failure. The idle recognition service was stopped after retaining all
responses, releasing roughly 24 GiB of GPU memory.

Run `enrich.py` on the same pinned input with phases `scoped`, `model`, and
`artifact`. The scoped phase selects source-conditioned table correspondence.
The model phase selects the released bare/flat definition arm with the named
producer enabled. The artifact phase consumes the full eligible source inventory.
`contextual.py` reads the exact scoped phase receipts and uses the book's
complete selected heading inventory for eligible cue views. The ordinary
scheduler includes the selected sources and operation graph in the scoped
task's immutable reuse key. A standalone scoped run has a different key from
the contextual graph. The runner checks that prerequisite before scheduling
and reports a block rather than regenerating the scoped task.
`enrich.py --phase scoped --batch-index INDEX`
runs one batch in the same result directory used by the full scoped pass. The
full pass can resume completed batches from their receipts. Each phase retains
its actual task scope and independent completion state.

Scoped run 313 reached view 167 with a 50.6 MB report and refused a reading
after native admission began. The [task and refusal receipt](raw/scoped-predicate-refusal.txt)
records the terminal state. The read-only `predicate_parity.py` probe compared
2,082 readings from its exact retained annotation task and isolated one
[disagreement](raw/scoped-predicate-parity-before.json). The parser had tagged
“Suppose” as a noun. The SQL reading recognized its reporting lemma without
checking predicate eligibility. Current native admission uses the independently
reconstructed eligible hosts and prepares layout once per annotation block.
A live stack sample during report construction also exposed repeated decoding
of the same source context for each native anchor. Anchor resolution now uses
the source preparation's indexed pieces and native items.

On view 167, observed time from task start to native completion submission
fell from about 50 seconds in run 313 to 13 seconds in run 314. The
[second timeout](raw/scoped-negation-timeout.txt) occurred during PostgreSQL
negation reconstruction at the 120-second statement deadline. The validator
prepares the retained token text, independent negation states and relevant
native pieces per annotation block so its individual readings can reuse them.
Run 315 passed predicate validation and reached the named-link candidate
boundary after 62.2 seconds for the same task. After correcting the substring
boundary, run 316 reached the 120-second deadline in
`ops.named_link_expected_groups`. The rest of the book's scoped batches were
held at that boundary. The
[scoped capacity record](records/nce.gs518-scoped-capacity.json) retains each
attempt. The next bounded diagnostic is named-link candidate reconstruction
on the retained annotations for view 167.

Use the managed installed Reader and exact closure for evidence delivery. Keep
protected authoring and assessment material separate from source-only packets and
ordinary review bundles.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 5 current, 0 superseded.


**next-corpus-enrichment**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Whole-book scoped admission and execution costs](records/nce.gs518-scoped-capacity.json) | NCE-02 | partial | NCE-02-A2, NCE-06-A2 | 2026-11-08 |
| [Whole-book artifact nomination and same-lineage eligibility](records/nce.gs518-artifact-trigger.json) | NCE-08 | passed | NCE-08 | 2026-11-08 |
| [Combined whole-book source and page-projection limits](records/nce.gs518-integrated-source.json) | full-book | partial | ADR-0070 | 2026-11-08 |
| [Full Grinstead–Snell Nemotron primary recognition](records/nce.gs518-primary-recognition.json) | full-book | passed | ADR-0070 | 2026-11-07 |
| [Complete Standard full-book source and frozen opportunity inventory](records/nce.gs518-standard-source.json) | full-book | passed | ADR-0070 | 2026-11-08 |
<!-- evidence-index:end -->
