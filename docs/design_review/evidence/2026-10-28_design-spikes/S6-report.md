# S6 · Storage smoke — report

**Run:** 2026-10-28, by executor W-S3 (Claude Opus 5.5). **Brief:** [S6-storage-smoke.md](S6-storage-smoke.md); plan
[S6](../../../plans/design-spikes-s0-s1/S6-storage-smoke.md). **Status:** passed.

## Answer

D3's DDL applies on PostgreSQL 18.6 with pg_textsearch 1.5.1 and vector 0.8.7, as a non-superuser in a database
cloned from the template. It needs one error fix, a `::regconfig` cast in the BM25 partial-index predicate, and one gap
fix, the `kb.segment.kind` CHECK its comment promises. The v1 trace and golden rows fit, with one reference misfit (OPEN-D1-5).
All 420 of 420 constraint cases behave as expected. Every D8 §5.3 trace question
returns its expected claims. BM25 works with the named index and the repeated, cast predicate, but D3's kind list
counts 6552 of 54826 non-space characters twice. The queue's claiming and
`attempt` fencing hold under a kill and a stall. Under the revised statement key (ADR-0019), claim-key agreement on the
70 aligned A/B pairs rises from 21 to 38 of 70, and with the label rule to
51 of 70 against 54 of 70
meaning keys. No fact is restated across the twelve units, so nothing calls for a stored meaning key yet (OPEN-D3-4 goes to
phase 1 goldens).

## What was run

All commands are `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/…`, run from this folder.

| Step | Command | Outcome | Records |
|---|---|---|---|
| 1–2 Database, DDL | `s6_extract_ddl.py`; `s6a_ddl.py --sql s6_ddl.sql`; `s6a_ddl.py` | passed | [s6.ddl](records/s6.ddl.json) |
| 3 Rows, constraints, run deletion | `s6b_rows.py` | passed | [s6.constraints](records/s6.constraints.json) |
| 4–5 Queries, BM25 | `s6c_queries.py` | passed | [s6.queries](records/s6.queries.json), [s6.bm25](records/s6.bm25.json) |
| §3 Joint dry run (S6-D) | `s6d_dry_run.py --suffix _2` | passed | [s6.dry-run-2](records/s6.dry-run-2.json) (supersedes s6.dry-run; identical figures) |
| 6 Vectors | `s6e_vectors.py` | passed | [s6.vectors](records/s6.vectors.json) |
| 7, 8 Volume, sizes | `s6e_volume.py` | passed | [s6.volume](records/s6.volume.json), [s6.sizes](records/s6.sizes.json) |
| 7b Queue | `s6e_queue.py --log-dir <scratch>` | passed | [s6.queue](records/s6.queue.json) |
| 9–10 Keys, restated facts | `s6f_keys.py` | passed | [s6.keys](records/s6.keys.json), [s6.restated](records/s6.restated.json) |
| Corrected DDL as a diff | `s6g_diff.py` | passed (D3's SQL blocks unchanged since extraction) | `results/s6/ddl.diff` |
| 11 Drop the database | `DROP DATABASE cs_spike_s6`, `DROP ROLE cs_s6_app` | passed | — |

**Environment.** PostgreSQL 18.6 (Ubuntu 18.6-1.pgdg24.04+2) on the project-local interim cluster (`just db-up`,
`build/pg/`, socket `build/pg/run`, port 5440, `shared_preload_libraries = pg_textsearch`, developer superuser;
shared_buffers 160 MB, work_mem 4 MB, maintenance_work_mem 64 MB, raised to 1 GB for the HNSW builds). The system cluster
on 5432 and the new `18/corpus` cluster (5434) were not used. The DDL and every row were written as `cs_s6_app`, a NOLOGIN
non-superuser with CREATEDB (`SET ROLE`), in `cs_spike_s6` cloned from `cs_template`. Python 3.14.10, psycopg 3.3.6
(binary), pgvector-python 0.5.1 (record [e4.env-cpu](records/e4.env-cpu.json)); instruments I-R2
([s0.instruments-ir2](records/s0.instruments-ir2.json)). Free disk was 109 GB at the start and 106 GB at the end.

## Results

### DDL (`results/s6/ddl_fixes.md`)

Applied as written, 1 of 73 statements fail: `CREATE INDEX segment_bm25` raises
`22P02 invalid input syntax for type oid: "english"`. `regconfig` has no `=` operator of its own, so `ts_config = 'english'`
resolves to `oid = oid` and reads the literal as an oid. The applied copy has 0 of 73
errors. The extension premises of D3 §3 hold: 42501 permission denied (both), and the migration's
assertion fails with P0001 with the provisioning instruction in a database without pg_textsearch. The B7 columns
were already in D3.

The corrected DDL as a diff against D3's blocks:

```diff
--- D3 §3–§8 DDL (code/s6_ddl.sql)
+++ S6 applied copy (code/s6_ddl_applied.sql)
@@ -221,5 +221,8 @@
   key          text NOT NULL UNIQUE,             -- 'seg:…'
   parent_id    bigint REFERENCES kb.segment,
-  kind         text NOT NULL,                    -- D1 §3.2; checked against a list in the migration
+-- S6 fix F2: kb.segment.kind checked against the D1 §3.2 list
+  kind         text NOT NULL CHECK (kind IN ('document','section','unit','paragraph','list','list_item','details',
+                    'math_display','math_inline','heading','table','table_row','table_cell','caption','footnote',
+                    'figure','sentence','email_message','quoted_block','signature')),   -- D1 §3.2
   ordinal      integer NOT NULL,                 -- position among siblings
   depth        integer NOT NULL,
@@ -240,5 +243,6 @@
 -- on the corpus by S6
 CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english')
-  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english';
+-- S6 fix F1: regconfig literal in the BM25 index predicate
+  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english'::regconfig;
 
 CREATE TABLE kb.span (
```

### Rows and constraints (`constraints.tsv`, `rows.json`, `run_deletion.md`)

- T3's C2 stores both restrictions (True). T4 has 17 of 17 claims.
  U12's premise cites `c1` outside its unit, and the evidence query returns it (True).
- The golden run has passes a = SV, b = HV and c = the v1 reference. Pass c is created after a and b for
  True of 12 units; there are 163 pass-c items,
  and the Weibull page is `reserved`.
- `kb.run_observation` resolves a reused task and excludes a task finished after the run's `finished_at`
  (True).
- The sweep has 420 of 420 cases: the brief's three bad rows, one mutated copy
  of an existing row for every CHECK, NOT NULL, FK, UNIQUE and composite PK, and six invariants the database does not
  express. Those six (INV-10 span bounds, span and segment text, cross-rendition evidence, distinct pass sessions, items
  only on pass c) insert without error, as expected: they are repository checks.
- Misfit: U6's `e_last_result` is a `Statement`-typed entity without a kind and fails `entity_check`, so it and its
  claim `c_follows` were not loaded (OPEN-D1-5: an external reference, `unsupported` until `extref`).
- Run deletion keeps the run row and its tasks. `kb.claim_link` has no `run_id` index, but the claim cascade removes
  links through `claim_link_to` and the unique index. The RI checks on `kb.claim.subject_id`, `object_entity_id` and
  `statement_id` reach their `(run_id, …)` indexes only through PostgreSQL 18's skip scan. At volume the whole delete took
  260.80 ms.

### Queries (`queries.md`)

Every D3 §9 pattern returns its rows in under 2 ms on the trace data. Each D8 §5.3 question returns all its expected
trace claims (0 missing); the extra rows come from other
core units in the run, and from the derived D1 that D3 §10 describes. Three corrections:

- D3 §9's `family_profile` pattern returns 1 row for the
  normal family. T2's answer lives on the `FamilyParameter` entities whose identity names the family, so the pattern
  needs that branch.
- The evidence query's `unit_id` is null, because a span's smallest containing segment is a sentence.
- `statement(page#unit)` cannot reach a lead-in assumption outside the unit (T1's C1).

The `@?` qualifier query is carried by `claim_pred` (True).

### BM25 (`bm25.md`, OPEN-D3-1)

- **Working form:** ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25') LIMIT :k with s.kind IN (…) AND s.ts_config = 'english'::regconfig repeated. It gives an ordered `Index Scan using segment_bm25`, and the
  forced generic plan of a prepared statement uses it too (True).
- **What fails:** D3 §5's query as written fails with 22P02: invalid input syntax for type oid: "english". The implicit string
  form fails with 42704: no BM25 index found for text <@> text expression, and the unqualified index name with
  42704: index "segment_bm25" does not exist.
- **Silent fallback:** with the predicate omitted, or written so the planner cannot prove it, the query falls back to
  standalone scoring over every row, including rows the index does not hold (index scan:
  False).
- **Boolean and phrase filters:** `@@ to_tsquery('english', …)` filters work. Served by the index alongside BM25 ordering:
  False; the filter is applied first, and its matches are scored and sorted.
- **Overlap:** the kind list is not non-overlapping. `math_display` segments nested in indexed paragraphs and list items
  put 6552 of 54826 non-space characters in the index twice. With
  `('paragraph','heading','list_item','caption')` the overlap is 0
  and no character is left out on the four pages.
- **Size and order:** the index holds 587 of 2335 segment rows; all five brief queries use it
  (5 of 5), with negative scores ascending.

### Joint dry run (`dry_run_2.md`, S6-D)

S4-B's tables register as schema version 0.2.0. The content hash recomputes (True),
as do the artifact bodies (4 of 4). 148 of 148
compiled rows insert. The trace rows inserted against the version agree on predicates
(0 without a slot) and on types and value kinds
(0 disagreements). Naming does not join:
6 entity types and
5 qualifier keys match only once prefixed, and
43 `domain_class`/`range` values in the compiled rows are bare while class
names are prefixed. Value-class attributes are 29 slot rows named
`<prefix>:<Class>.<attr>`. Last: ParseStatus has 'ambiguous'; kb.segment/kb.rendition CHECKs do not. The rerun against the final S4
tables reproduces s6.dry-run exactly.

### Vectors (`vectors.tsv`, phase 1)

At 10,000 rows the planner chooses exact scan (no HNSW), recall 1.0, about 0.7 ms for the selective filtered join.
The table below forces the HNSW scan:

| dim | index | iterative scan | median ms | p95 ms | recall@10 |
|---|---|---|---|---|---|
| 1024 | global hnsw (D3) | off | 0.5 | 0.764 | 0.15 |
| 1024 | global hnsw (D3) | relaxed_order | 2.496 | 3.252 | 0.868 |
| 1024 | global hnsw (D3) | strict_order | 3.198 | 3.843 | 0.464 |
| 1024 | partial hnsw per target_type | off | 0.448 | 0.693 | 0.162 |
| 1024 | partial hnsw per target_type | relaxed_order | 1.6 | 2.134 | 0.84 |
| 1024 | partial hnsw per target_type | strict_order | 1.878 | 2.439 | 0.466 |
| 2048 | global hnsw (D3) | off | 0.753 | 1.026 | 0.146 |
| 2048 | global hnsw (D3) | relaxed_order | 3.428 | 4.731 | 0.842 |
| 2048 | global hnsw (D3) | strict_order | 4.488 | 5.371 | 0.406 |
| 2048 | partial hnsw per target_type | off | 0.771 | 0.978 | 0.224 |
| 2048 | partial hnsw per target_type | relaxed_order | 2.619 | 3.521 | 0.802 |
| 2048 | partial hnsw per target_type | strict_order | 3.188 | 4.025 | 0.448 |

HNSW builds took 3670.20 ms at 1024 dimensions and
7190.50 ms at 2048, with indexes of 27320320
and 81928192 bytes. These are random vectors, a worst case for recall; S7 decides the
dimension with real embeddings.

### Volume and sizes (`volume.tsv`, `sizes.tsv`)

| step | rows | ms |
|---|---|---|
| copy ops.task | 12500 | 103.4 |
| copy kb.observation | 100000 | 1109.7 |
| copy kb.entity | 5000 | 38.5 |
| copy kb.claim | 20000 | 228.6 |
| copy kb.claim_support + kb.claim_evidence | 40000 | 213.7 |
| query: claims with qualifier param_values.variance (`@?`, no GIN) | 1410 | 1.001 |
| query: why a method ran (one unit) | 5 | 0.559 |
| query: effective observations of one task (kb.run_observation) | 1 | 0.559 |
| query: observations of the run by kind (kb.run_observation) | 5 | 17.931 |
| query: claims of one subject | 1 | 0.037 |
| delete materialized rows (entities, claims, cascades) | 25000 | 260.8 |

- **Binary COPY types:** a `real` column refuses `float8` (22P03: incorrect binary data format), so
  D6 §3's float4 note holds. A `str` sent into a declared `jsonb` column is accepted:
  it is stored as a JSON string, so pass dicts.
- **Segment text:** 2552 bytes per author unit, against about 11.6 kB of
  observation payload per unit at run scale. The database totals 77283328 bytes
  after the volume load. OPEN-D3-3 stays answered, and the sizes support keeping the column.

### Queue (`queue.md`, P0-O-1)

- **Exactly once:** 10200 of 10200 tasks were done exactly once with one
  observation, and 0 claims were made while a lease was live.
- **Kill and stall:** the 100 re-claimed tasks are exactly the killed worker's
  in-flight batch and the stalled worker's batch. The stalled worker's late fencing UPDATE matched
  0 of 50 rows and it committed nothing.
- **Wake-ups:** NOTIFY in the inserting transaction woke the waiting worker below the client timer's resolution (0 s).
  Tasks inserted without a notification were found by the timeout re-query after 0.69 s.
- **Claim plan:** BitmapOr of task_pending and task_lease, then a sort of every qualifying row before LIMIT.

### Keys under the revised statement key (`keys.tsv`, `key_pairs.tsv`; B3, OPEN-D3-4)

| variant | aligned pairs | claim keys equal | meaning keys equal | S0 record (claim / meaning) |
|---|---|---|---|---|
| raw (D1 §10.1 as in S0) | 70 | 21 | 41 | 21 / 41 |
| statement keyed by covering segment (S0 --anchors) | 70 | 35 | 41 | 35 / 41 |
| global label from identity (S0 --labels) | 70 | 21 | 54 | 21 / 54 |
| both (S0) | 70 | 48 | 54 | 48 / 54 |
| revised statement key (ADR-0019) | 70 | 38 | 41 | — |
| revised statement key + label rule | 70 | 51 | 54 | — |

- **Reproduction:** this driver reproduces the four S0 rows exactly (last column).
- **What the revised key leaves:** with the label rule, 3 pairs still
  differ by statement alone: in U6, pass B splits one paragraph into two statements where pass A has one. The other
  16 differing pairs disagree about the fact itself (conditions,
  modality, a parameter value's LaTeX), so their meaning keys differ too.
- **Comparability:** every pass is on one rendition per page, where locators and segments correspond one to one, so the
  figures are comparable with the S0 rows.
- **Restated facts:** 0 of 71 facts are restated across units (also
  0 of 71 under the label rule). Only
  23 of 71 facts have a global subject that could recur.

## Assumptions

- **Cluster.** The project-local interim cluster, in place of the system cluster or a throwaway one: it was the one where
  the role is superuser with pg_textsearch preloaded at the time (coordinator). Timings are relative to its small default
  memory settings.
- **Roles.** The DDL was applied by a non-superuser (`cs_s6_app`) to test D3 §3's privilege story. Under peer
  authentication that meant `SET ROLE` from the superuser.
- **Keys in S6-B–E.** The rows use placeholder keys (sha256 of item parts), unique per run, with global entities merged
  across units. The D1 §10.1 keys are S6-F's subject.
- **Golden passes.** a = SV (Sonnet 5.5), b = HV (Haiku 5.5), c = the v1 reference (model-facing, with its decisions).
  Items were derived only for pass c, as D3 §7 has them (the brief's "pass SV with its items" predates that).
- **Synthetic payloads.** The volume payloads are synthetic in the D3 §6.2 shapes, with proposals the v1 reference
  batches cycled: no S2 or S3 output exists yet.
- **Queue timings.** Lease 2 s and wait timeout 1 s in the queue test (production: 5 min and 30–60 s), so expiry happens
  within the test.
- **Statement anchors.** In S6-F the anchor outside units is the nearest paragraph or list item. Alignment ran on the
  batches as stored (or label-normalized); only the keys use the revised anchor, so every variant has the same 70 pairs.
- **Context-premise rule.** S6-F implements it (an assumption inside another statement's anchor takes that statement's
  part); no S0 batch triggered it.

## Design implications

| Design item | Proposed change or answer | Evidence |
|---|---|---|
| D3 §5 `segment_bm25`, §5 BM25 query (F1) | Cast the literal in the index predicate and in every query repeating it: `ts_config = 'english'::regconfig` | [s6.ddl](records/s6.ddl.json), [s6.bm25](records/s6.bm25.json) |
| D3 §5 `kb.segment.kind` (F2) | Add the CHECK with the D1 §3.2 kinds that the column comment promises | [s6.ddl](records/s6.ddl.json), [s6.constraints](records/s6.constraints.json) |
| D3 §5 BM25 kind list (OPEN-D3-1) | `('paragraph','heading','list_item','caption')`: no overlap and full coverage on the four pages; drop `math_display`, whose segments nest in paragraphs and list items (orphan display formulas are already paragraphs). Repeat the predicate always: without it the query silently scores rows the index does not hold. OPEN-D3-1 closed with this syntax | [s6.bm25](records/s6.bm25.json) |
| D3 §9 `family_profile`; D8 §5.2–§5.3 | Add the branch over `FamilyParameter` entities whose identity names the family (`attrs ->> 'family'`) | [s6.queries](records/s6.queries.json) |
| D3 §9 evidence query | `unit_id` from the span's nearest `unit` ancestor (range or `parent_id` walk), not from the span's own segment | [s6.queries](records/s6.queries.json) |
| D8 §5.3 T1 `statement(LocationScale#dfn1)` | A unit locator cannot reach the lead-in assumption; use the composite locator, or rely on premises reached through conditions | [s6.queries](records/s6.queries.json) |
| D3 §3 `meta.schema_*` naming; D2 §7.1; P0-F-4 | One naming convention across compiled rows, `kb.entity.type` and `kb.claim.qualifiers` keys (prefixed everywhere, or bare classes and qualifiers): as stored, class and qualifier joins fail, and the compiled `domain_class`/`range` are bare while class names are prefixed | [s6.dry-run-2](records/s6.dry-run-2.json) |
| D3 §3 `meta.schema_slot` PK; D2 §7.1 | Value-class attributes (`v` of several value classes) need the class in the key: a `domain_class` key column, or the `<prefix>:<Class>.<attr>` names S4 uses | [s6.dry-run-2](records/s6.dry-run-2.json) |
| D3 §5 `parse_status` CHECKs; D1 §3.2 `ParseStatus` | The compiled enum has `ambiguous`, which `kb.segment`/`kb.rendition` refuse; align one with the other | [s6.dry-run-2](records/s6.dry-run-2.json) |
| D6 §3 claiming; P0-O-1 | The claim statement holds as written. Its `OR` across pending and expired rows plans as a BitmapOr plus a full sort before `LIMIT`; for larger queues split it into two branches (pending through `task_pending`'s order, expired through `task_lease`), e.g. `UNION ALL` of two `LIMIT`ed `SKIP LOCKED` selects | [s6.queue](records/s6.queue.json) |
| D3 §4 `ops.task` indexes | Add `(run_id, unit_key)` for "why a method ran" and per-unit reads; without it the query scans the run's tasks (under 1 ms at 12,500 tasks, linear in a run's tasks) | [s6.volume](records/s6.volume.json) |
| D3 §8 run deletion | Delete claims first (links cascade); consider `kb.claim_link (run_id)` only if links are deleted directly; the RI checks rely on skip scan over `(run_id, …)` indexes | [s6.constraints](records/s6.constraints.json), [s6.volume](records/s6.volume.json) |
| D6 §3 binary COPY | Confirmed: `real` needs `float4`; pass JSONB as dicts (a `str` becomes a JSON string) | [s6.volume](records/s6.volume.json) |
| D3 §5 `kb.embedding` (phase 1) | halfvec at 1024 and 2048 builds and serves; filtered queries need `hnsw.iterative_scan` (`relaxed_order`) as D3 plans; the dimension waits on S7 | [s6.vectors](records/s6.vectors.json) |
| OPEN-D3-3 | Stays answered: segment text is small beside a run's observations | [s6.sizes](records/s6.sizes.json) |
| OPEN-D3-4, STMT-01, D1 §10.1 (B3) | The revised statement key brings claim keys to within 3 pairs of meaning keys, all from one statement-segmentation disagreement. No restated facts across the twelve units: no meaning-key column in 0001; phase 1 goldens decide | [s6.keys](records/s6.keys.json), [s6.restated](records/s6.restated.json) |
| OPEN-D1-5; the v1 reference | A `Statement`-typed entity for an external reference fails D3's statement-kind CHECK; keep such references `unsupported` until `extref`, and correct U6 in the reference | [s6.constraints](records/s6.constraints.json) |

## Follow-ups

- Restated facts and the meaning key: rerun on phase 1 goldens drawn across pages (OPEN-D3-4).
- BM25 kind list: confirm no overlap and full coverage on the 78-page corpus (tables, footnotes, figures beyond one caption).
- Vector recall with real embeddings and the chosen dimension (S7), with `iterative_scan` and `ef_search`.
- Queue: measure the two-branch claim against the single statement at 10⁵ pending tasks per stage.
- Rerun the volume figures on `18/corpus` (io_uring, larger buffers); the figures here are from the interim cluster.

<!-- generated by `just evidence render S6-report.md.j2` on 2026-10-28; records: 2026-10-28_design-spikes/s6.bm25, 2026-10-28_design-spikes/s6.constraints, 2026-10-28_design-spikes/s6.ddl, 2026-10-28_design-spikes/s6.dry-run-2, 2026-10-28_design-spikes/s6.keys, 2026-10-28_design-spikes/s6.queries, 2026-10-28_design-spikes/s6.queue, 2026-10-28_design-spikes/s6.restated, 2026-10-28_design-spikes/s6.sizes, 2026-10-28_design-spikes/s6.vectors, 2026-10-28_design-spikes/s6.volume -->
