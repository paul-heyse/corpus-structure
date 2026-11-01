# Status
_Updated2026-11-01; PDF-27/28 implemented and targeted Tested; shared-book adoption remains open._

## Current checkpoint

- The [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) owns PDF-00–28 and
  investigation disposition. [PDF-27/28](docs/plans/pdf-docling-pipeline/structured-payload-model-and-validation.md)
  now delivers model-derived nested page IPC, typed logical identity, selected-page owning Arrow
  readers and candidate/OCR inventory kernels using existing transactional artifact custody.
- Frozen validation checks actual stored OCR/candidate/report bytes against captured release
  schemas and shared source/health/coverage rules, alongside native callbacks. Complete admitted
  dependencies and finalized access/region membership bind the result consumed by seal.
  Build-row locking closes finalization races while preserving independent task heartbeats.
- ADR-0045 supersedes affected ADR-0042/0044 placement clauses and preserves their surviving
  fidelity/relationship/evidence obligations. Compiler19 archives payload model/codec/validator.
  Current native head `semantic_pdf_20261101` (0067) preserves all ten prior managed objects
  within23 objects/18 native transitions; frozen historical migrations remain unchanged.
- SQL NUMERIC projections retain exact Decimal/Core boundaries, separated from Arrow uploads
  by model declarations. Native Docling global state is still explicitly materialized; report
  families without columnar consumers retain exact JSON. Broader native replacement is conditional.
- The [PostgreSQL coordinator](docs/plans/postgresql-capability-leverage_2026-11-01.md) retains
  completed PG-00–12/O01–15 and its separate319-case receipt `pg-series-final-c5394eaa`.
  The merged implementation supplies these PDF prerequisites; that older receipt does not
  qualify subsequent PDF changes. SQLAlchemy2.1.6/Alembic1.20.1 pins are unchanged.
- Shared book `corpus_pdf_20261031` remains0060/compiler14/core0.6.2; no shared upgrade occurred.
  Owned disposable authoring/test databases were disposed; no auxiliary worktrees remain.
  Private validation PostgreSQL on55434 remains stopped. Raw evidence and receipts are retained.

## Verification

- **passed (2026-11-01):**283-case targeted functional union across20 files. Receipt
  `build/test-receipts/qualification/pdf-payloads-final-20261101` has282passed/1stale assertion;
  that sole test was corrected and passed in `pdf-payloads-final-native-control-20261101`.
  No production change followed the final union. Exact `scripts/test_receipts.py run --python-only`
  commands/selections are in each `invocation.json`; overlapping cases are not added.
- **passed:** `uv run pyrefly check --min-severity warn --summary=none` (zero errors/warnings),
  `uv run ruff check .`, `just model check`, `just adr-lint`, `git diff --check`, root `just turn-end`.
- **failed, retained:** first `pdf-payloads-20261101` attempt279passed/4failed (stale assertions
  and native provenance before final source freeze); all four obligations subsequently passed.
  Earlier interrupted repository/PG records keep their original scope in the PG coordinator.
- **failed:** `just docs-check` on existing moved-library/retired-profile links elsewhere;
  no changed package plan/architecture/ADR page errors. No blanket publication pass is claimed.
- **not_run:** whole-book rebuild/inference, external provider/evaluator journeys, default adoption,
  Rust tests or whole-repository qualification. No measured speed/memory benefit is claimed.

## Next

PDF-25 owns current-realization book rebuild/publication from compatible retained evidence through
0067; PDF-10/11 own actual consumer/default adoption and complete provider/evaluator qualification.
I24 quantitative comparison, I25 effective-options/image lifetime and conditional consumers retain
explicit owners/triggers in the PDF coordinator. No historical reader/layout obligation is added.
