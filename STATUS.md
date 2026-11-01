# Status
_Updated 2026-11-01; integrated PDF mechanisms implemented, large-book admission/adoption in progress._

## Current checkpoint

- [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) owns package/O/I disposition.
  PDF-13–16 implement one Docling content graph with mandatory multi-input lineage, governed
  selection, scoped coverage and singular downstream readers. PDF-10/11 assembled acceptance is open.
- ADR-0040 governs full Standard+RapidOCR/Nemotron3.5 true triple pass and retirement of historical
  HTML runtime/read/replay compatibility. Frozen migrations, historical data and evidence remain inert.
- Owned `corpus_pdf_20261031` is at0059. Compiler14/core0.6.2, full Docling2.145/core2.105 and
  native schema1.10.0 are bound. Isolated Python3.12/vLLM0.26 runs actual RTX5090 MTP/effectiveFA2;
  stable model/environment remain outside temporary worktrees.
- Actual all-page recognition passed:1589 A,1589 B,261 C,1433 valid zero-C pages. Two primary
  length/repetition failures recovered under a separately bound repetition1.3 recipe; originals stay failed.
- Fresh composed toy source publication passed in run7/task70. Whole-book integration retains all
  failed/interrupted attempts. Native list, lexical demand, bulk deletion, picture-nullability and
  rich-cell projection defects were corrected. Shared chart provenance now transforms exactly once,
  fixing the independently reproduced page170 crop error while preserving both panels.
- Book attempt6/run13/task86 reached protected publication but its270447 relations exceeded
  PostgreSQL's JSONB array limit. Exact558190320-byte prepared replay and native field-cast results
  are retained. ADR-0041 selects JSON-text decomposition into existing normalized rows;0060 is being
  implemented in an isolated checkout. No integrated whole-book publication or selection is claimed yet.
- Obsolete logs/probe installations/scratch cleanup recovered about25GB. No abandoned authenticated
  test databases existed. Current environments, models, source inputs, receipts and databases remain.

- [Logging plan series](docs/plans/structured-logging-observability_2026-11-01.md) proposes complete
  Typer/Rich diagnostics, local archives/metrics, MCP parity and conditional remote integration.
  RC01–RC04 accepted2026-11-01; LOG-00 begins the bounded composition investigations.
  Seven new plan documents authored; no logging runtime/dependencies installed or qualified.
  Plan links/traceability and `just turn-end` passed; `just docs-check` failed on existing
  parsing-plan/source-review links (2026-11-01). Existing plans were not changed by this task.

## Verification

- **passed:** warning-inclusive `just types` on current main; no suppressions added. Native consumer
  affected union194; source read/reuse17; chart/reconciliation25. Exact receipts are in
  [integrated evidence](docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md).
- **passed:** `just test-all`0059 baseline2638 Python tests, complete reporting,0failed/error/skipped.
  Receipt `build/test-receipts/qualification/20261101T033536Z-3956304`; zero listed Rust tests establish
  no Rust functional coverage. The later read-projection/chart changes have their scoped passes above.
- **passed:** existing native0060 controls35 in isolation; remaining shape/head/integrated checks
  are in progress. Those controls are not actual full-book publication or assembled qualification.
- **failed/interrupted:** earlier broad records retain their outcomes; second stable run2527passed/
  95failed preceded the native fixture/consumer corrections. All three broad receipts are archived.
- **passed:** scoped Ruff, Clippy, agent/ADR lint, pinned dependencies, live parameter-log reload
  and `just ready`. Rules scan/tests are not_run because no rules exist. Cosmetic formatting does
  not invalidate applicable passing type/test evidence.
- **not_run:** current external MCP/render/export journey, actual five-section extraction,
  independent full-section A/B/C authors, registration/grading and completed-result/default selection.

## Next

Finish/review/merge0060, deploy to the owned PDF database and run normal cached book preparation.
Use the exact admitted integrated pin for current external interfaces, five intact-section provider
work and independent two-section references. Grade automatically; select the completed result and
change defaults only afterward. Complete affected final-source qualification, owning plans and
handoff; remove the active0060 worktree after integration. Defaults still target the historical deployment.
