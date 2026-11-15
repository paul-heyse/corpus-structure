# Rollback-only native authoring diagnosis

Bounded diagnosis of managed candidate failure `4cc4a7c038c344aea54d7b5032514614`.
The probe changes only the declared `ops.data_demand_read.scope` column inside a
rolled-back transaction; it never registers or deploys a candidate. It reports
only acquired database/principal and PostgreSQL's owned-DDL diagnostic fields.

**Tested, 2026-11-14.** The exact PostgreSQL diagnostic after restoring the frozen
registered base in the same rollback-only transaction was SQLSTATE `0A000`:
`cannot alter table "data_demand_read" because function ops.ddo_population_valid(ops.data_population,ops.data_demand_read) uses its row type`.
The original acquired development revision is `semantic_bep_located_v2`; authoring
restores `semantic_ddo_context_pdf_v1` only inside that rolled-back transaction.

The candidate owner now derives the affected declared native dependency closure
from its existing bounded PostgreSQL catalog graph. Exact frozen before-state
transitions retire dependents before the physical row change; declared desired
transitions restore them afterwards. Undeclared dependents retain PostgreSQL's
RESTRICT refusal. No installed definition is adopted as desired source, and final
native/catalog/privilege admission remains independent.

`uv run --no-sync ci test --workers 1 --json -- python/corpus-structure/tests/semantic/test_native_rowtype_evolution.py`
**passed** three native controls, managed result
`c7c6dc5628204b7fb0825a829ea07459`: actual refusal followed by exact rendered
upgrade, stale before-state refusal and undeclared dependent refusal.

`author_candidate.py` exercises full source-owned rollback-only preparation.
Its `author-result.json` is a bounded worker-context result, not registration,
deployment, or qualification of the coordinator's subsequently integrated source.
