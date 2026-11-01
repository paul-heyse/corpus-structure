# Status
_Updated 2026-11-01; integrated PDF mechanisms implemented; whole-book publication/adoption incomplete._

## Current checkpoint

- [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) owns package/O/I disposition.
  PDF-13–16 implement one Docling content graph with mandatory multi-input lineage, governed
  selection, scoped coverage and singular downstream readers. PDF-17–19 implement the record/identity foundation; PDF-20 onward remain planned. Acceptance is open.
- ADR-0040 governs full Standard+RapidOCR/Nemotron3.5 true triple pass and retirement of historical
  HTML runtime/read/replay compatibility. Frozen migrations, historical data and evidence remain inert.
- Owned `corpus_pdf_20261031` is at0060;0061–0063 are undeployed. Source ABI15/relational compiler3/core0.6.3, deployed compiler14/core0.6.2; full Docling2.145/core2.105 and
  native schema1.10.0 are bound. Isolated Python3.12/vLLM0.26 runs actual RTX5090 MTP/effectiveFA2;
  stable model/environment remain retained; the dedicated inference service is shut down.
- Actual all-page recognition passed:1589 A,1589 B,261 C,1433 valid zero-C pages. Two primary
  length/repetition failures recovered under a separately bound repetition1.3 recipe; originals stay failed.
- Fresh composed toy source publication passed in run7/task70. Whole-book integration retains all
  failed/interrupted attempts. Native list, lexical demand, bulk deletion, picture-nullability and
  rich-cell projection defects were corrected. Shared chart provenance now transforms exactly once,
  fixing the independently reproduced page170 crop error while preserving both panels.
- Book attempt6/run13/task86 reached protected publication but its270447 relations exceeded
  PostgreSQL's JSONB array limit. Exact558190320-byte prepared replay and native field-cast results
  are retained. ADR-0041/0060 implements JSON-text decomposition into existing normalized rows.
  Attempt7 passed that cast, then was cancelled during child validation; no integrated product committed.
  Committed0061 replaces the correlated child check with one shared set join; book-scale validation is open.
- Obsolete logs/probe installations/scratch cleanup recovered about25GB. No abandoned authenticated
  test databases existed. Current environments, models, source inputs, receipts and databases remain.

- [Logging plan series](docs/plans/structured-logging-observability_2026-11-01.md): LOG-00 bounded
  choices settled: structlog/stdlog + scoped Logbook + direct OTel; no production runtime installed.
  I01–I03 probes passed; I04 primitive direction selected, integrated lifecycle still open.
  I05 partial: hard cleanup deadline unestablished. I06 local contract passed; live read blocked
  by missing endpoint/read token/test scope. Six finalized records retain failures and boundaries.
  `just evidence` passed (0errors/38historical warnings); `just ready` passed (2026-11-01).

## Verification

- **passed:** PDF-17–19 final foundation/schema union394tests/4warnings; `just model check`;
  global `just types` and Ruff clean, no suppressions added. [Foundation receipts](docs/design_review/evidence/2026-11-01_pdf-record-foundations/README.md)
  preserve failures and limits; earlier native consumer194/read17/chart25 receipts retain their scope.
- **passed:** `just test-all`0060 baseline2643 Python tests/10warnings, complete reporting and stable source.
  Receipt `build/test-receipts/qualification/20261101T042650Z-4190256`; zero listed Rust tests establish
  no Rust functional coverage. This broad pass precedes0061 and is not whole-book acceptance.
- **passed:**0060 bounded controls68 and20;0061 focused controls9 plus exact reproduction1.
  Warning-inclusive `just types` and `uv run ruff check .` passed on merged main.
- **failed/interrupted:** earlier broad records retain their outcomes; second stable run2527passed/
  95failed preceded the native fixture/consumer corrections. Earlier receipts remain archived.
- **passed:** scoped Ruff, Clippy, agent/ADR lint, pinned dependencies, live parameter-log reload
  and `just ready`. Rules scan/tests are not_run because no rules exist. Cosmetic formatting does
  not invalidate applicable passing type/test evidence.
- **not_run:** current external MCP/render/export journey, actual five-section extraction,
  independent full-section A/B/C authors, registration/grading and completed-result/default selection.
- **failed:** `just docs-check` on existing parsing-profile and moved logging-library links;
  product typing/lint results above are passed. Own plan links are checked separately.

## Next

Continue the [structural streaming extension](docs/plans/pdf-docling-pipeline/relational-document-model-and-identity.md):
ADR-0042 and PDF-17–19 foundations implemented; begin PDF-20 live staging next. Acceptance still requires current external
journeys, five-section extraction, independent references and automated grading before default cutover.
All owned tasks/processes are concluded and worktrees removed. Defaults still target the historical deployment.
