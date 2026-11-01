# Status
_Updated 2026-11-01; relational PDF publication/readers scoped-tested; deployed book adoption remains incomplete._

## Current checkpoint

- [Structured-data plan](docs/plans/pdf-docling-pipeline/structured-payload-model-and-validation.md)
  adds planned PDF-27/28; RC10/11 confirmed, I21–I25 and amendments integrated in the coordinator.
  Product implementation/deployment is not established by plan authoring.

- [PostgreSQL leverage plan](docs/plans/postgresql-capability-leverage_2026-11-01.md): PG-00–12 design expanded with concrete library APIs, contracts, migration paths and consumer acceptance from review O01–15. Product work not started; latest-stable upgrades settled, alembic-utils excluded. Existing series unchanged.

- [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) owns package/O/I disposition.
  PDF-20/21 publication and PDF-24 selected readers/exports are implemented with scoped controls.
  PDF-25 exact-envelope migration/explicit resume adapters are ready; actual cutover remains open.
- Owned `corpus_pdf_20261031` remains0060/compiler14/core0.6.2;0061–0065 are undeployed.
  Source ABI17/relational compiler4/core0.6.4 binds full Docling2.145/core2.105/schema1.10.0.
  Reviewed0065 authoring, native actual-record identity, freeze/validate/seal and pinned readers
  preserve private progress and atomic published visibility. No source/knowledge default changed.
- ADR-0043 separates verified byte folds from optional export SHA. ADR-0044 uses model-derived
  native JSON Schema for exact metadata; pinned pg_jsonschema0.3.4 is provisioned in the dedicated
  templates/owned database. This did not migrate the application's semantic schema.
- Native global replay passed over1589retained pages; fresh current pages20/1211 passed.
  Explicit native-class replay and actual1.67formula raster scale correct prior failures.
  Global graph finalization remains materialized; strict streaming is deferred under I14.
- Actual prior all-page recognition and exact558190320-byte integrated witness remain retained.
  The new storage derivation verified192computed grids across107tables/85chart tables.
  No whole-book integrated product or new completed knowledge result was committed.
- OCR evidence is retained (24.1MB region JSON;35.7MB candidate files). Empty-region warnings
  retain qualified diagnostics; no universal harmlessness/Nemotron recovery claim is made.
- Owned jobs/worktrees are settled; Nemotron service remains down with model/environment retained.
- [Logging plan series](docs/plans/structured-logging-observability_2026-11-01.md): LOG-00 bounded
  choices settled: structlog/stdlog + scoped Logbook + direct OTel; no production runtime installed. I01–I03 probes passed; I04 primitive direction selected, integrated lifecycle still open.
  I05 partial: hard cleanup deadline unestablished. I06 local contract passed; live read blocked
  by missing endpoint/read token/test scope. Six finalized records retain failures and boundaries. Earlier `just evidence` and `just ready` passed (2026-11-01).

## Verification

- **passed:** selected121-case union117initial passes plus four repaired affected controls
  (overlapping, not125). Actual publication/readers/staging, producer/grid, closure and source
  controls are detailed in [new receipts](docs/design_review/evidence/2026-11-01_pdf-publication-adoption/README.md).
- **passed:** `uv run pyrefly check --min-severity warn --summary=none`, `uv run ruff check .`,
  `just model check`, `just ready`; corrected fixture scopes also passed Pyrefly/Ruff.
- **passed:** `just evidence`: three new finalized records;0errors/38existing warnings globally.
- **partial:** full-book fresh native worker failed, retained assembly/enrichment replay passed;
  fresh corrected selected-page workers passed. This is not a rerun of the full corrected worker.
- **passed:** earlier0060 `just test-all`2643Python tests/10warnings retains its original scope;
  receipt `build/test-receipts/qualification/20261101T042650Z-4190256`. No new full union is claimed.
- **not_run:** current full `just test-all`,0065 deployment, book migration/seal/read/export,
  external MCP/render, five-section extraction, independent references/grading and default selection.
- **passed (plan authoring):** focused publisher/link/anchor/coverage check and independent review;
  `git diff --check`. **failed:** `just docs-check` on existing moved-library/retired-profile links.
  Product checks not_run for docs-only changes; earlier scoped types/tests remain applicable.

## Next

Start [PDF-27](docs/plans/pdf-docling-pipeline/structured-payload-model-and-validation.md#PDF-27):
successor authority decisions and I21/I23 contract choices, then PDF-20/28/21 validation integration
and PDF-24 consumers. PDF-25 determines forward migration prerequisites; PDF-10/11 retain actual
adoption/qualification. Do not qualify a superseded0065 representation solely before replacing it.
