# Private PDF streaming and staged custody — 2026-11-01

**Implemented; scoped Tested; retained-book lowering Measured.** The
[PDF coordinator](../../../plans/pdf-docling-pipeline_2026-10-31.md) owns package and investigation
state. This execution delivers private PDF-22/23 and the selected minimum PDF-20 prerequisite.
Source baseline `da808db2`, integrated ABI16/relational compiler4/core0.6.4, frozen forward0064.
Owned `corpus_pdf_20261031` stays at0060;0061–0064 are undeployed. No defaults changed.

## Functional regression and diagnostics

**passed:** the selected314-case regression union is covered by312 initial passes and the affected
file's14-case passing rerun after repairing two test-only assumptions. Twelve rerun cases overlap;
counts are not summed. The two failures were a missing newly imported `pdf-staging.yaml` in the
counterfactual model fixture and an expected0063 head that now correctly reads0064. No production
code changed for these repairs. Initial failures and the collection-name collision are retained.

Assembled command, all files relative to `python/corpus-structure/tests/`:

```sh
uv run pytest \
 python/corpus-structure/tests/orchestrate/test_pdf_private_execution.py \
 python/corpus-structure/tests/orchestrate/test_pdf_streaming_integration.py \
 python/corpus-structure/tests/ingest/test_pdf_streaming.py \
 python/corpus-structure/tests/ingest/test_pdf_recognition.py \
 python/corpus-structure/tests/ingest/test_pdf_recognition_methods.py \
 python/corpus-structure/tests/ingest/test_pdf_capacity.py \
 python/corpus-structure/tests/semantic/test_pdf_staging.py \
 python/corpus-structure/tests/semantic/test_pdf_stream_reconciliation.py \
 python/corpus-structure/tests/semantic/test_pdf_reconciliation.py \
 python/corpus-structure/tests/semantic/test_pdf_integrated.py \
 python/corpus-structure/tests/semantic/test_pdf_records.py \
 python/corpus-structure/tests/semantic/test_pdf_record_identity.py \
 python/corpus-structure/tests/semantic/test_pdf_record_native.py \
 python/corpus-structure/tests/semantic/test_native_closure.py \
 python/corpus-structure/tests/semantic/test_archive_reader.py \
 python/corpus-structure/tests/semantic/test_schema_product_cli.py \
 python/corpus-structure/tests/semantic/test_arrow_publication.py \
 python/corpus-structure/tests/schema/test_relational.py \
 -q -o addopts='' --maxfail=3
uv run pytest python/corpus-structure/tests/semantic/test_pdf_record_native.py -q -o addopts='' --maxfail=2
```

- **passed:** warning-inclusive global `just types`, zero Pyrefly diagnostics; no suppressions added.
- **passed:** `just model check`, revision0.6.4; `uv run ruff check python/corpus-structure`.
- **passed:** focused discovery, mdBook render and link resolution for the five changed owning/
  status/evidence pages; `just evidence`115records,0errors/38historical warnings. The previous
  whole-site docs failure on unrelated moved/retired links retains its original scope.
- **passed:** actual PostgreSQL private stage/retry/fence controls13 and frozen-forward reproduction7
  (overlap with the assembled union). SQLAlchemy transactions, Psycopg/pgpq COPY and independent
  native constraints were exercised in disposable fixture databases. Final product guards are unchanged.
- **passed:**41 recognition/reconciliation worker controls, one baseline publication case deselected;
  that publication case is included in the assembled union. Do not add these counts to314.
- **passed:** parent claim maintenance, Arrow reader cleanup and native child/source settlement controls.
- **failed:** initial collection used two same-basename modules under pytest's existing import mode;
  parent tests were renamed `test_pdf_private_execution.py` before executing the assembled union.
- **not_run:** `just test-all`, fresh whole-book integrated inference/publication, external serving/
  extraction/reference/grading journeys, default adoption or a performance comparison.

Warnings in the assembled union are upstream pandas/LinkML deprecations, a deliberate invalid-bbox
clamping refusal case and existing SQLAlchemy cyclic-table sorting. They are not Pyrefly diagnostics.

## Distinct provider and composition scopes

**passed:** actual cached native model inference on toy PDF pages1–2 using CUDA native stages and
explicit CPU RapidOCR: success,2pages,5text items,6verified IPC files, no conversion errors.
These pages contain no formula item; this receipt makes no actual formula-inference claim.
The exact original invocation bodies are retained as `native-provider.sh` and
`native-differential.sh`; run either with `bash` from the repository root. They use cached assets
in offline mode. Original outputs are archived in `raw/checks.tar.gz`.

**passed:** native baseline versus streaming differential on those same pages: complete export,
tree/order/provenance equality with no field exclusions; five independently authored fixture text
values also matched. Separate pixel/crop, late-enrichment, heading/list, cross-page structure and
release controls exercise deliberate inputs rather than infer semantic fidelity from equal outputs.

**passed:** the parent/native IPC/reconciliation/private PostgreSQL composition control. Its external
Docling provider is scripted; application preparation, stream hooks, IPC, companion artifacts,
claim lifetime and actual protected database adoption are real. It establishes the composition
contract, not actual-provider end-to-end qualification. The preceding actual native provider run
has its separate scope. No live Nemotron/vLLM service was started for this execution.

## Retained actual book replay

The retained native Docling product at run2/task2 is read **without database writes**, hydrated and
lowered through the new record/IPC writer. The retained28,420,729-byte native JSON text has SHA256
`73766f6ffb5bd2bae3097ee38b6d4455b3db72ce49196aa39442dd7d992a7cd1`.
Exact source/release/recipe/schema/content pins are in `retained-book-replay.json`.

```sh
/usr/bin/time -v uv run python docs/design_review/evidence/2026-11-01_pdf-streaming-runtime/replay_retained_native.py build/pdf22-retained-book-replay
```

Use a fresh output directory on replay; the recorded directory is intentionally retained.
`replay_retained_native.py` requires the owned local database's historical native product and the
current project environment; it does not download models or invoke inference.

**passed:**1589pages,44636texts,101tables,4829pictures,3419groups. The resulting635469rows occupy
83verified IPC files/191199382bytes. Exact metadata/schema and every replay checksum were checked;
largest batch2885993bytes is below the model's8388608-byte maximum. Native records include6342
FormulaItems. This is record preservation, not a claim about recognized formula accuracy.

**Measured:** native hydration/GC2.86s; lowering/verification81.19s; script84.18s, process86.26s.
PeakRSS874080KiB was already reached at hydration. This is a single retained-graph replay, without
a comparative baseline or fresh inference, page assembly/raster capture, PostgreSQL adoption,
reading-order construction or integrated companion graph. The native graph is materialized.
It establishes neither bounded book-size memory nor a speedup. The operator selected this global
finalization boundary; strict end-to-end streaming I14 remains open.

## Files and consumers

`raw/checks.tar.gz` retains command logs, including failed/interrupted attempts, with member hashes
in `raw/checks.json`. Raw replay logs are under `raw/`; the receipt and probe source stay ordinary
text. Large replay IPC files remain under ignored `build/`, not in Git. The existing PDF-17–19
[foundation receipts](../2026-11-01_pdf-record-foundations/README.md) keep their original scope.

[Private streaming owner](../../../plans/pdf-docling-pipeline/streaming-processing-and-arrow.md)
and [staging owner](../../../plans/pdf-docling-pipeline/staged-publication-and-validation.md)
retain implementation mechanisms. PDF-21 must still freeze, validate native/reference/companion
closure and publish atomically. PDF-24 must migrate public readers/exports; PDF-25 owns live
migration/adoption. Private progress, a verified upload digest and native finalization are separate
from a sealed logical document, published source or evidence-backed knowledge claim.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**pdf-docling-pipeline**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Retained actual native book record and Arrow lowering](records/native.retained-book-lowering.json) | PDF-22 | partial | PDF-22, I14 | 2026-11-01 |
<!-- evidence-index:end -->
