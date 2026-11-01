# Status
_Updated 2026-11-01; PostgreSQL leverage execution worktree; functional scope implemented; combined qualification starting._

## Current checkpoint

- Execution is isolated at `/home/paul/corpus-structure-postgresql-capability-leverage`,
  branch `work/postgresql-capability-leverage`. **Do not merge to main without operator go-ahead.**
- [PostgreSQL coordinator](docs/plans/postgresql-capability-leverage_2026-11-01.md) owns PG-00–12
  and O01–15 disposition. Runtime/native/typed/export implementations are committed through `2f5e01a6`;
  combined final-source qualification remains open.
- Design-phase execution guidance: all data is regenerable; prioritize the target and omit
  historical readers/retained-data upgrade work. This is temporary scope guidance, not an ADR
  or permanent product compatibility policy. No ADR was created for it.
- Main documentation changes through `524c5a73` are merged here (`977eb8b1`); no incoming
  production change has yet required reconciliation. Main's dirty work remains untouched.
- SQLAlchemy2.1.6/Alembic1.20.1 exactly pinned; other selected dependencies already current.
  Native upstream callable-default defect reproduced; narrow adapter retained. No alembic-utils.
- New native head `semantic_pg_20261101` carries compiler18 admission and this series' functions.
  Existing frozen migrations are unchanged. Final source provenance is frozen after maintenance.
- Private PostgreSQL18 only: `build/pg/data`, `build/pg/socket`, port55434; extension-only
  `cs_pg_template`, ordinary CREATEDB `paul`, restricted semantic roles. Lock capacity1024.
  Never use shared-cluster provisioning/start/stop recipes for this instance.
- Independent consumer review identified cross-product local-ID comparison and scoped/nested
  coverage omissions. Comparison and PG10 coverage repaired; actual native/CLI controls and independent
  focused reassessment passed. No audit documentation was changed.
- Concurrent PDF/logging work retains its own plans; this series imports none of their unrealized
  scope. [PDF coordinator](docs/plans/pdf-docling-pipeline_2026-10-31.md) remains their owner.

## Verification

- **passed:** `just ready` after dependency move; final native migration/adoption seven-case
  endpoint (`build/pg11-final-adoption-tests.log`) including recurring authoring.
- **passed:** final native lifecycle/companion CLI endpoint13 (`build/pg-native-final-qualified.log`),
  current contract35 (`build/pg-current-contracts-pure.log`), qualified comparison5
  (`build/pg06-qualified-comparison-pure.log`). These are scoped checks before final source.
- **passed:** `uv run pytest python/corpus-structure/tests/semantic/test_database_description.py
  python/corpus-structure/tests/orchestrate/test_pdf_cancellation_native.py -ra`; four actual
  native controls (`build/pg07-pdf-cancellation-current.log`, JUnit alongside it).
- **passed:** settled PG10 rich native/CLI (`build/pg10-coverage-settled.log`); whole-tree Ruff,
  Pyrefly and `just ready` (`build/pg-final-{ruff,types,ready}.log`). Failed attempts are retained.
- Earlier current typed union failures were repaired and scoped reruns passed; no credit is
  transferred from an interrupted run or from the acknowledged mid-run determinant change.
- **in progress:** final targeted PostgreSQL functional/native union and relevant hygiene.
  The broad run was interrupted normally; its pre-existing/out-of-scope failures are retained, not repaired as a migration gate. Prior component passes establish no whole-series completion or measured performance benefit.

## Next

Finish directly affected contract-test migration, run the final targeted PostgreSQL union and
relevant hygiene, then reconcile completion in the coordinator/checkpoint. A wholly green
repository suite is not required (operator,2026-11-01); existing PDF baseline failures remain external. Keep the worktree and receipts for later
operator-authorized main integration; never push.
