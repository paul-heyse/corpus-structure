# Status
_Updated 2026-11-01; private PDF streaming/staging implemented; whole-book publication/adoption incomplete._

## Current checkpoint

- [PostgreSQL capability review](docs/functional_reviews/postgresql-capability-leverage_2026-11-01.md): two-pass audit integrated; O01–O15 Proposed, O12 mechanism selection unresolved. Latest-stable upgrades settled; breaking target changes permitted. PDF plan revision remains separate.
- Review/audit links/anchors and `just turn-end` passed (2026-11-01); `just docs-check` failed on ADR-0043 §B4 link. Maintenance is not a lint/product pass; see audit for moving-source limits.

- [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) owns package/O/I disposition.
  PDF-13–16 implement one Docling content graph with mandatory multi-input lineage, governed
  selection, scoped coverage and singular downstream readers. PDF-17–19 foundation plus private
  PDF-22/23 and the minimum PDF-20 staging prerequisite are implemented. PDF-21/24/25 remain planned.
- ADR-0040 governs full Standard+RapidOCR/Nemotron3.5 true triple pass and retirement of historical
  HTML runtime/read/replay compatibility. Frozen migrations, historical data and evidence remain inert.
- Owned `corpus_pdf_20261031` is at0060;0061–0064 are undeployed. Source ABI16/relational
  compiler4/core0.6.4, deployed compiler14/core0.6.2; full Docling2.145/core2.105 and
  native schema1.10.0 are bound. Isolated Python3.12/vLLM0.26 runs actual RTX5090 MTP/effectiveFA2;
  stable model/environment remain retained; the dedicated inference service is shut down.
- Actual all-page recognition passed:1589 A,1589 B,261 C,1433 valid zero-C pages. Two primary
  length/repetition failures recovered under a separately bound repetition1.3 recipe; originals stay failed.
- Fresh composed toy publication passed in run7/task70. Native list/cell/lexical and shared chart
  provenance corrections retain their earlier receipts; whole-book failed/interrupted attempts remain.
- Book attempt6/run13/task86 reached protected publication but its270447 relations exceeded
  PostgreSQL's JSONB array limit. Exact558190320-byte prepared replay and native field-cast results
  are retained. ADR-0041/0060 implements JSON-text decomposition into existing normalized rows.
  Attempt7 passed that cast, then was cancelled during child validation; no integrated product committed.
  Committed0061 replaces the correlated child check with one shared set join; book-scale validation is open.
- New explicit native-stream recipe retains page assemblies/raster/candidates, streams verified IPC
  and adopts private modeled rows under maintained claims; completion-driven recognition and
  Arrow/DuckDB reconciliation preserve native selection. Native global finalization remains
  materialized by operator selection; strict I14 stays open. No source/public default changed.
- [Logging plan series](docs/plans/structured-logging-observability_2026-11-01.md): LOG-00 bounded
  choices settled: structlog/stdlog + scoped Logbook + direct OTel; no production runtime installed. I01–I03 probes passed; I04 primitive direction selected, integrated lifecycle still open.
  I05 partial: hard cleanup deadline unestablished. I06 local contract passed; live read blocked
  by missing endpoint/read token/test scope. Six finalized records retain failures and boundaries. Earlier `just evidence` and `just ready` passed (2026-11-01).

## Verification

- **passed:** streaming/private-stage functional union314cases:312 passed initially, two stale
  fixture assumptions repaired, affected file14 passed (overlap, not summed). Global `just types`,
  `uv run ruff check python/corpus-structure` and `just model check` passed. [Runtime receipts](docs/design_review/evidence/2026-11-01_pdf-streaming-runtime/README.md).
- **passed:** actual two-page native inference/differential; controlled-provider IPC with actual
  PostgreSQL custody. Retained1589-page native graph lowered/verified into83 IPC files, largest
  batch2885993bytes. This is not fresh whole-book inference, final seal or bounded global memory.
- **passed:** earlier PDF-17–19 foundation/schema union394tests retains its dated scope. [Foundation receipts](docs/design_review/evidence/2026-11-01_pdf-record-foundations/README.md).
- **passed:** `just test-all`0060 baseline2643 Python tests/10warnings, complete reporting and stable source.
  Receipt `build/test-receipts/qualification/20261101T042650Z-4190256`; zero listed Rust tests establish
  no Rust functional coverage. This broad pass precedes0061 and is not whole-book acceptance.
- Earlier0060/0061 bounded, typing/lint and lifecycle receipts retain their original scope; failed/interrupted broad records remain archived. Cosmetic formatting does not invalidate them.
- **not_run:** current external MCP/render/export journey, actual five-section extraction,
  independent full-section A/B/C authors, registration/grading and completed-result/default selection.
- **failed:** `just docs-check` on existing parsing-profile and moved logging-library links;
  product typing/lint results above are passed. Own plan links are checked separately.

## Next

Continue [PDF-21 freeze/seal/publication](docs/plans/pdf-docling-pipeline/staged-publication-and-validation.md),
then PDF-24 selected readers/exports and PDF-25 deployment/adoption. Private producer/staging
mechanisms are implemented and scoped-tested; actual book publication and consumer journeys remain
open. Acceptance still requires five-section extraction, independent references and automated grading.
