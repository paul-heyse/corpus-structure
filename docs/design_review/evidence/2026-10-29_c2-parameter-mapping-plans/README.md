# Parameter-mapping access-plan recheck, 2026-10-29

**Tested (2026-10-29).** The final C2 correction restricts `member_of_construction` answers to the
requested family and construction. An independent native-store control first demonstrated that
another member family's mapping leaked into the answer, then passed after the correction.

This record rechecks only that affected query's physical statements after commit `8cfc1f6`.
The other eleven queries retain the scope of `c2.query-plans`; this supplement does not rewrite
its accepted source or raw outputs.

```sh
uv run python docs/design_review/evidence/2026-10-29_c2-parameter-mapping-plans/code/recheck.py
```

The small wrapper reuses the frozen Q4 restoration/adaptation and actual-SQL inspection script
from the [C2 query-plan inspection](../2026-10-29_c2-query-plans/README.md), selecting only
`parameter_mapping` and writing here. Its explicitly documented synthetic current projection,
cluster, cardinalities, native planner settings and evidence limits remain the same.

The final run captured seven physical SELECT statements, with zero query or EXPLAIN errors.
The predicate and identity paths remain indexed. This establishes access-plan applicability
for the changed query, not semantic-answer correctness or a performance claim. The independent
control is `tests/db/test_queries.py::test_parameter_mapping_excludes_other_members_of_requested_construction`.
The owned `ci_c2plans_<pid>` database was dropped; `raw/plans.json` records cleanup.
