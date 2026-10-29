# C2 query access plans, 2026-10-29

**Tested (2026-10-29):** read `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for SQL emitted by all
six generic and six statistics queries. This is access-path evidence for P0-C-2 and F04, not a
throughput, capacity, or end-to-end semantic qualification claim.

## Method and environment

Run from the repository with its pinned Python environment:

```sh
uv run python docs/design_review/evidence/2026-10-29_c2-query-plans/code/inspect_plans.py
```

The script restores Q4's retained `p0q_fk_dataset.sql.gz` to its own `ci_c2plans_<pid>` database
on PostgreSQL cluster `18/corpus` (port 5434). It captures actual production SQL through SQLAlchemy's
execution event, then reads its native plan with the same bindings. Page demand is five rows plus
one lookahead (`QueryContext.row_batch=6`). No planner flags, disabled scan types, hints, or forced
indexes are used. `raw/plans.json` records SQL, bindings, full plans, server version, adaptations,
counts, and cleanup. `raw/inspection-summary.json` lists the observed indexes and scans per query.

The entire restored fixture retains 7,578 entities, 20,079 claims, 20,000 claim-reference edges,
and 80,000 entity-reference edges. Its selected volume run holds the 20,000 synthetic claims;
the extra 79 claims belong to Q4's original reference rows.

## Explicit current-projection adaptation

Q4 predates the implemented model. The script records every adaptation rather than treating its
old DDL or payloads as the current schema:

- Add nullable projection columns needed to read current generated tables; legacy values remain
  unknown. View declarations are preserved, not altered as tables.
- Create the generated `entity_identity` relation and its overlay index. For this physical workload,
  the synthetic volume's `RandomVariable` placeholders become global `FamilyParameter` entities,
  linked by `stat:family` to ten same-run distribution-family entities. Entity, claim and reference
  IDs/cardinalities remain unchanged. These synthetic identities are planner inputs, not accepted
  domain facts or independent answer expectations.
- Prefix the family and parameter class names. Legacy `Statement` names and their CHECK stay
  unchanged because this inspection does not claim model migration or semantic acceptance.
- Project legacy predicate-condition entity arguments from `{t: entity, ref}` to the generated
  `{ref}` shape without changing the reference values or relational rows.
- Add inherited ingest-task references to the volume run so the production `run_rendition` reader
  can locate its source renditions. This adds four setup tasks, not knowledge rows.
- Rebuild `segment_bm25` from the **current generated overlay**. Q4's old predicate indexed
  `math_display` instead of `caption`; it was inapplicable to the generated search-block query.
  The final result uses the current index, not an enlarged predicate or a forced access path.
- Omit dump comments on template-owned extensions; their installed definitions are unchanged.

Compiled schema lookup is supplied from the current statistics pack for this projection reading.
This is deliberately not a claim that the legacy fixture passes the current run/model registry
or that its artificial values are semantically valid production observations.

## Reading of the plans

- `find` uses the current `segment_bm25` index beneath native bounded ranking. The outer stable
  key ordering preserves score ties; `FETCH ... WITH TIES` is supported on this route.
- `transformations_of` uses `claim_ref_target` for the selective reverse-premise join and
  `claim_entity_ref_entity` for entity arguments. Its candidate sets are composed as indexed
  relational selections, without mixing unrelated alternatives into one broad predicate.
- Family and construction profiles use `entity_identity_value`. Forward edge hydration uses
  the reference relations' primary keys, preserving each reference path.
- Unrestricted `claims` expands the whole selected run's premise closure; its scan of that run's
  references is expected. A broad `families_where` request likewise examines the relevant identity
  population. These whole-set operations are distinguished from selective reverse lookups.
- Every generic/statistics query's emitted physical statements were inspected; the final run
  recorded zero execution or EXPLAIN errors. Small reference tables and reconstruction reads may
  use sequential scans where there is no useful selective index.

## Failed attempts and cleanup

Retained `raw/attempt*-plans.json` and restore logs preserve earlier failures: extension-comment
ownership, treating a view as a table during adaptation, a legacy statement CHECK, missing
identity/rendition projections, old condition shapes, and the obsolete BM25 predicate. Their
results receive no acceptance credit. Diagnostic BM25 variants in the final receipt also show
that changing LIMIT syntax or pre-binding renditions did not repair the obsolete predicate.

Early cleanup attempted a drop before disposing its own SQLAlchemy pool. The two authenticated
scratch databases (`ci_c2plans_873813`, `ci_c2plans_883136`) were subsequently dropped after those
processes exited. The corrected script disposes its pool before its final plain `DROP DATABASE`.
`raw/cleanup.json` confirms no database under this investigation's prefix remains. No shared
application database or other PostgreSQL cluster was changed.
