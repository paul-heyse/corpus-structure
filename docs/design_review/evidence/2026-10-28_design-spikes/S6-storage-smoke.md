# S6 · Storage smoke

**Brief, 2026-10-28.** Local PostgreSQL 18.6 with pgvector 0.8.7 and pg_textsearch 1.5.1. Can run
now; trace rows use S1 offsets when available, otherwise hand offsets.

## Question

Does the DDL of [D3](../../../design/D3-database.md) apply as written, do the trace rows of D3 §10
fit it, do the D3 §9 query patterns return what they should, and do the BM25 and vector indexes
work with the syntax assumed?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D3-1 | pg_textsearch index and query syntax; indexing `kb.segment.text` in place |
| OPEN-D3-3 | Whether storing segment text is worth its space |
| OPEN-D3-4 | Whether a stored meaning key (claim key without `statement`) is needed |
| D3 §5–§7 | DDL correctness: types, constraints, foreign-key order, checks |
| D3 §11 | Bulk observation writes and index-backed queries at run scale |

## Inputs

- D3 §3–§7 SQL blocks, extracted by a script into `code/s6_ddl.sql` (do not retype them).
- S1 segments of the four spike pages (`results/s1/segments/`).
- The trace's T3 rows (D3 §10) and the other trace units' target claims (trace.md).
- [PostgreSQL tooling](../../../libraries/PostgreSQL_System_Tooling_for_Ubuntu.md).

## Procedure

1. **Database.** Create `cs_spike_s6` on the local server; `CREATE EXTENSION` for `vector` and
   `pg_textsearch`; record versions.
2. **DDL.** Apply the extracted SQL. Fix each error minimally in a copy and record the fix with
   its reason (`results/s6/ddl_fixes.md`). Do not edit D3.
3. **Rows.** Insert a project, schema version, configs, one finished run, the four spike pages'
   renditions and segments, and the trace units' entities, claims, evidence, supports (a fake
   task and observations) and links. Check every constraint fires on a deliberately bad row
   (object both entity and value; local entity without scope segment). A span outside its
   rendition's text is a repository-layer check (INV-10), not a database constraint: note it,
   do not expect a database error.
4. **Queries.** Run each D3 §9 pattern and the four trace questions of D8 §5.3 in SQL; record
   rows returned and time. Check `kb.run_observation` with a reused task.
5. **BM25.** Create the BM25 index on `kb.segment.text`; run five queries ("affine
   transformation normal", "location-scale family", "lognormal shape parameter", "sum of
   independent gamma", "standard score"); record the top five segments and the syntax that
   worked (`OPEN-D3-1`).
6. **Vectors.** Insert 10,000 random unit vectors as `halfvec(1024)` and as `halfvec(2048)`;
   build HNSW; time top-10 queries with a filter join on `kb.segment.kind`.
7. **Volume.** COPY 100,000 synthetic observations with realistic payload sizes (sample from S2
   and S3 outputs if available) and 20,000 claims; time the copy, the GIN-backed qualifier
   query, and the per-unit "why a method ran" query.
8. **Size.** Table and index sizes; the share taken by `kb.segment.text` (`OPEN-D3-3`).
9. **Meaning key.** Over the S0 reference batches (if available), count facts restated in more
   than one unit (same subject, predicate, object and qualifiers, different statement)
   (`OPEN-D3-4`). Twelve units may be too few to decide; if so, say so and leave the question to
   phase 1 goldens.
10. Drop the database at the end; keep only results.

## Data to collect

| File | Content |
|---|---|
| `results/s6/ddl_fixes.md` | Each DDL error, the fix, the reason |
| `results/s6/constraints.tsv` | bad row, expected error, observed |
| `results/s6/queries.md` | query, rows (abridged), ms |
| `results/s6/bm25.md` | syntax used, top five per query |
| `results/s6/vectors.tsv`, `results/s6/volume.tsv`, `results/s6/sizes.tsv` | timings and sizes |

## How to interpret

| Finding | Reading |
|---|---|
| DDL applies with only cosmetic fixes | D3 becomes migration 0001 (P0.3) with those fixes |
| A constraint cannot be expressed as written | Move the invariant to the repository layer's write checks and note it in D3 |
| BM25 syntax differs from D3 | D3 corrected; `OPEN-D3-1` closed |
| Segment text is a small share of size | Keep it; `OPEN-D3-3` closed |
| Facts restated across units are common | Store a meaning key on claims (`OPEN-D3-4`) |

## Report

`S6-report.md` from the [template](report-template.md), with the corrected DDL as a diff against
D3's blocks.
