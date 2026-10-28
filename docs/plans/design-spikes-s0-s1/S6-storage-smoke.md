# S6 · Storage smoke: plan

**Status: Proposed (2026-10-28).** Part of the [spike plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions (§3.5), the execution queue (row 28) and spike-execution findings. The
question is the [S6 brief](../../design_review/evidence/2026-10-28_design-spikes/S6-storage-smoke.md)'s;
this document says how each brief step now runs after the store research and the D3 revision of
2026-10-28, and which phase 0 package each result feeds.

## 1. What S6 must establish now

D3 was revised on 2026-10-28 from the [store note](../../design_review/evidence/2026-10-28_library-store/README.md):
BM25 through pg_textsearch on one partial index over non-overlapping block kinds, always named in
the query (D3 §5); extensions provisioned once in a template database, not by migrations (D3 §3);
the queue's partial indexes, claiming statement and `attempt` fencing (D3 §8,
D6 §3); golden passes as tasks of a `golden` run; run deletion keeps `ops.run` and its tasks; JSONB
indexes only with a consuming query. Everything there is source-read or reasoned, none of it run.

S6 runs it: the DDL applies, the v1 trace rows fit, the D3 §9 and D8 §5.3 queries answer, the
search and vector indexes are used by the planner, the queue claims correctly under concurrency,
and the revised statement key's agreement figures exist. Its evidence decides whether ADR-0016
(PostgreSQL as single authority) is accepted, and it is the dry run of the phase 0 foundations
store packages.

**Prerequisites.** pg_textsearch 1.5.1 is installed (package `postgresql-18-pg-textsearch`,
[overview](../../libraries/postgresql-18-pg-textsearch.md)) but loads only through
`shared_preload_libraries`, and neither it nor `vector` is a trusted extension. The operator adds it
to `shared_preload_libraries`, restarts, and creates both extensions as `postgres` in
`cs_spike_s6`; alternatively S6 runs in a throwaway cluster from `pg_virtualenv -o
shared_preload_libraries=pg_textsearch`, where the spike's role is superuser (store note §1). S6
records free disk space at start. Steps 9–10 wait on I-R2 (row 24), because
formula keys use the token form it revises.

## 2. Brief steps as they now run

| Step | Now |
|---|---|
| 1 Database | `cs_spike_s6` with `pg_textsearch` and `vector` (§1); versions recorded |
| 2 DDL | Extract D3's current blocks by script, including the partial BM25 index, the per-row `ts_config`, the queue indexes, the `golden` run kind and `golden_unit` unit type, and the run-index additions; fixes recorded in a copy, never in D3 |
| 3 Rows | As the brief, plus a `golden` run with `golden_unit` tasks for passes `a` and `b` and one pass `c` created after both; a run-deletion check that removes one run's materialized rows, keeps its `ops.run` row and tasks, and uses the new indexes (`EXPLAIN`) |
| 4 Queries | As the brief; D3 §9's `@?` qualifier query checked to be carried by `claim_pred` now that the GIN index is gone |
| 5 BM25 | The brief's five queries as `ORDER BY text <@> to_bm25query($1, 'kb.segment_bm25') LIMIT 5` with the index predicate repeated; check with `EXPLAIN` that the partial index is used (the implicit string form skips partial indexes); one Boolean and one phrase filter through `@@ to_tsquery('english', …)`; check the kind list does not overlap on the four pages (no token counted twice); record the top five per query and the syntax that worked (OPEN-D3-1) |
| 6 Vectors | As the brief at 1024 and 2048 dimensions, with one partial HNSW index per `target_type` and `hnsw.iterative_scan` on a filtered query (D3 §5) |
| 7 Volume | Binary COPY with `Copy.set_types` of 100,000 observations and 20,000 claims; the per-unit "why a method ran" query; no GIN timing (the index is gone) |
| 7b Queue (new) | Two worker processes claiming from 10,000 `pending` tasks with the D6 §3 statement; one worker killed mid-batch; check no task is claimed twice, the expired lease is taken by the next claim, and the dead worker's late terminal write commits nothing (`attempt` fencing); `LISTEN`/`NOTIFY` wake-up with a timeout and re-query |
| 8 Size | As the brief, including the BM25 index (OPEN-D3-3 is answered by mechanism; this gives the size) |
| 9 Keys | As the brief, after I-R2, with statement keys computed as ADR-0019 states them (anchored by locators, not by segment keys); within one rendition the figures are comparable, and the report says so |
| 10 Meaning key | As the brief, after I-R2 |

## 3. The joint dry run (S6-D)

Before inserting the trace rows, load S4-B's compiled schema-table rows into `meta.schema_*` and
register the pack's schema version from its hash, then insert the trace rows against that version.
This exercises the path the phase 0 foundations and schema packages will build (pack → compiled
rows → migration-0001 tables → typed queries) on real artifacts, and shows whether the table rows
and the trace rows agree on class and predicate names.

## 4. Consumers

| Output | Feeds |
|---|---|
| DDL fixes | D3 (X2), then P0-F-4 (metadata and migration 0001) |
| Constraint and run-deletion results | P0-F-4 (repository checks for what the database cannot express) |
| Query and search results | P0-F-4 (the BM25 index and query syntax) and P0-C-2 (typed queries, `find`); D8 §5.3 corrections for the design-phase plan |
| Dry run (S6-D) | P0-F-4 (compiled schema rows against the tables) |
| Queue results | P0-O-1 (claiming, fencing, `LISTEN`/`NOTIFY` wake-up) |
| Volume and sizes | P0-F-4 (COPY and size readings) |
| Vector results | phase 1 (`kb.embedding` migration; S7 picks the dimension) |
| Key agreement, restated facts | P0-F-4 and P0-C-1 (statement keys); OPEN-D3-4 and STMT-01 in the design-phase plan |

## 5. Packages

| Package | Scope | Outputs | Done when | Consumer |
|---|---|---|---|---|
| S6-A | Steps 1–2 | `results/s6/ddl_fixes.md`, the applied copy | The DDL applies; every fix has a reason | P0-F-4 |
| S6-B | Step 3 | `constraints.tsv`, the run-deletion check | Every constraint fires on its bad row; the golden-run rows fit; deletion behaves as D3 §8 says | P0-F-4 |
| S6-C | Steps 4–5 | `queries.md`, `bm25.md` | Every query returns its rows with plans recorded; D8 §5.3 differences listed | P0-F-4, P0-C-2 (OPEN-D3-1) |
| S6-D | §3, after S4-B | `dry_run.md` | Trace rows insert against the compiled schema version, or each mismatch is listed | P0-F-4 |
| S6-E | Steps 6, 7, 7b, 8 | `vectors.tsv`, `volume.tsv`, `queue.md`, `sizes.tsv` | Each measured, or `blocked` naming the missing extension or disk space | P0-O-1, P0-F-4, phase 1 |
| S6-F | Steps 9–10, after I-R2 | `keys.tsv`, `restated.tsv` | The revised-key rows beside the four S0 rows; differing pairs explained | P0-F-4, P0-C-1 (OPEN-D3-4) |
| S6-G | Report | `S6-report.md`, records `s6.*` | The template is satisfied; the corrected DDL as a diff against D3 | X2, ADR-0016 |

Records: `s6.ddl`, `s6.constraints`, `s6.queries`, `s6.bm25`, `s6.dry-run`, `s6.queue`, `s6.volume`,
`s6.vectors`, `s6.sizes`, `s6.keys`, `s6.restated`; `consumed_by` names the phase 0 package (or
phase 1 for vectors) and the OPEN item.

## 6. Choices left to execution

- Whether the queue test uses processes or threads with separate connections, as long as each
  worker has its own connection and the kill is abrupt.
- The synthetic payload mix for step 7 when S2 and S3 outputs do not yet exist.
