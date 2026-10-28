# S6 · Storage smoke: plan

**Status: Proposed (2026-10-28).** Part of the [spike plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions (§3.5), the execution queue (row 28) and spike-execution findings. The
question is the [S6 brief](../../design_review/evidence/2026-10-28_design-spikes/S6-storage-smoke.md)'s;
this document says how each brief step now runs after the store research and the D3 revision of
2026-10-28, and which phase 0 package each result feeds.

## 1. What S6 must establish now

D3 was revised on 2026-10-28 from the [store note](../../design_review/evidence/2026-10-28_library-store/README.md):
built-in full-text search replaces pg_textsearch, which could not be installed (D3 §5); no
extension in phase 0; the queue's partial indexes, claiming statement and `attempt` fencing (D3 §8,
D6 §3); golden passes as tasks of a `golden` run; run deletion keeps `ops.run` and its tasks; JSONB
indexes only with a consuming query. Everything there is source-read or reasoned, none of it run.

S6 runs it: the DDL applies, the v1 trace rows fit, the D3 §9 and D8 §5.3 queries answer, the
search and vector indexes are used by the planner, the queue claims correctly under concurrency,
and the revised statement key's agreement figures exist. Its evidence decides whether ADR-0016
(PostgreSQL as single authority) is accepted, and it is the dry run of the phase 0 foundations
store packages.

**Prerequisites.** The operator frees disk space (3.3 GB free on 2026-10-28); S6 records free space
at start. The vector steps need `vector` created by a superuser: either the operator creates it as
`postgres` in `cs_spike_s6`, or S6 runs those steps in a throwaway cluster from `pg_virtualenv`,
where the spike's role is superuser (store note §1). Steps 9–10 wait on I-R2 (row 24), because
formula keys use the token form it revises.

## 2. Brief steps as they now run

| Step | Now |
|---|---|
| 1 Database | `cs_spike_s6`; no extension for steps 2–5 and 7–10; `vector` only for step 6 (§1) |
| 2 DDL | Extract D3's current blocks by script, including the generated `text_tsv` column, the partial GIN, the queue indexes, the `golden` run kind and `golden_unit` unit type, and the run-index additions; fixes recorded in a copy, never in D3 |
| 3 Rows | As the brief, plus a `golden` run with `golden_unit` tasks for passes `a` and `b` and one pass `c` created after both; a run-deletion check that removes one run's materialized rows, keeps its `ops.run` row and tasks, and uses the new indexes (`EXPLAIN`) |
| 4 Queries | As the brief; D3 §9's `@?` qualifier query checked to be carried by `claim_pred` now that the GIN index is gone |
| 5 Search | Replaced: the brief's five queries through `websearch_to_tsquery('english', …)` ranked by `ts_rank_cd`, with the block-kind predicate; check the planner uses the partial `segment_fts` index; check that the kind list does not overlap on the four pages (no token counted twice); record the top five per query (OPEN-D3-1) |
| 6 Vectors | As the brief at 1024 and 2048 dimensions, with one partial HNSW index per `target_type` and `hnsw.iterative_scan` on a filtered query (D3 §5) |
| 7 Volume | Binary COPY with `Copy.set_types` of 100,000 observations and 20,000 claims; the per-unit "why a method ran" query; no GIN timing (the index is gone) |
| 7b Queue (new) | Two worker processes claiming from 10,000 `pending` tasks with the D6 §3 statement; one worker killed mid-batch; check no task is claimed twice, the expired lease is taken by the next claim, and the dead worker's late terminal write commits nothing (`attempt` fencing); `LISTEN`/`NOTIFY` wake-up with a timeout and re-query |
| 8 Size | As the brief, including the `text_tsv` column and the partial GIN (OPEN-D3-3 is answered by mechanism; this gives the size) |
| 9 Keys | As the brief, after I-R2 |
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
| DDL fixes | D3 (X2), then phase 0 foundations (metadata and migration 0001) |
| Constraint and run-deletion results | phase 0 foundations (repository checks for what the database cannot express) |
| Query and search results | phase 0 consolidation and queries (typed queries, `find`); D8 §5.3 corrections for the design-phase plan |
| Queue results | phase 0 orchestration (claiming, fencing, the agent barrier) |
| Vector results | phase 1 (`kb.embedding` migration; S7 picks the dimension) |
| Key agreement, restated facts | OPEN-D3-4 and STMT-01 in the design-phase plan |

## 5. Packages

| Package | Scope | Outputs | Done when |
|---|---|---|---|
| S6-A | Steps 1–2 | `results/s6/ddl_fixes.md`, the applied copy | The DDL applies; every fix has a reason |
| S6-B | Step 3 | `constraints.tsv`, the run-deletion check | Every constraint fires on its bad row; the golden-run rows fit; deletion behaves as D3 §8 says |
| S6-C | Steps 4–5 | `queries.md`, `fts.md` | Every query returns its rows with plans recorded; D8 §5.3 differences listed |
| S6-D | §3, after S4-B | `dry_run.md` | Trace rows insert against the compiled schema version, or each mismatch is listed |
| S6-E | Steps 6, 7, 7b, 8 | `vectors.tsv`, `volume.tsv`, `queue.md`, `sizes.tsv` | Each measured, or `blocked` naming the missing extension or disk space |
| S6-F | Steps 9–10, after I-R2 | `keys.tsv`, `restated.tsv` | The revised-key rows beside the four S0 rows; differing pairs explained |
| S6-G | Report | `S6-report.md`, records `s6.*` | The template is satisfied; the corrected DDL as a diff against D3 |

Records: `s6.ddl`, `s6.constraints`, `s6.queries`, `s6.fts`, `s6.dry-run`, `s6.queue`, `s6.volume`,
`s6.vectors`, `s6.sizes`, `s6.keys`, `s6.restated`; `consumed_by` names the phase 0 package (or
phase 1 for vectors) and the OPEN item.

## 6. Choices left to execution

- Whether the queue test uses processes or threads with separate connections, as long as each
  worker has its own connection and the kill is abrupt.
- The synthetic payload mix for step 7 when S2 and S3 outputs do not yet exist.
