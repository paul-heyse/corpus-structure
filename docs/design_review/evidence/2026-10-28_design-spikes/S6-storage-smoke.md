# S6 · Storage smoke

**Brief, 2026-10-28; revised after S0, S1 and S0-R2.** Local PostgreSQL 18.6 with pgvector 0.8.7
and pg_textsearch 1.5.1. Ready and independent of the other spikes; trace rows use S1 offsets and
the v1 reference.

## Question

Does the DDL of [D3](../../../design/D3-database.md) apply as written, do the trace rows fit it
in their guideline v1 form, do the D3 §9 query patterns return what they should, and do the BM25
and vector indexes work with the syntax assumed? Does a stored meaning key earn its place once
statements are keyed by an explicit anchor segment?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D3-1 | pg_textsearch index and query syntax; indexing `kb.segment.text` in place |
| OPEN-D3-3 | Whether storing segment text is worth its space |
| OPEN-D3-4 | Whether a stored meaning key (claim key without `statement`) is needed |
| D3 §5–§7 | DDL correctness: types, constraints, foreign-key order, checks, including the golden-pass record (B7) |
| D1 §10.1 (B3) | Whether the revised statement key makes claim keys agree where the passes agree |
| D3 §11 | Bulk observation writes and index-backed queries at run scale |

## Inputs

- D3 §3–§7 SQL blocks, extracted by a script into `code/s6_ddl.sql` (do not retype them).
- **The B7 columns** (B7 in the [design owner's review](design-owner-review-S0-S1.md)):
  `eval.golden_pass.model text NOT NULL`; `eval.golden_pass.inputs jsonb NOT NULL` (guideline
  version, reference hash, packet hash, the M13 version that chose the context); `reserved` in
  the `eval.document_split.split` CHECK; a `context` flag on `eval.golden_item`. If D3 does not
  have them yet when S6 runs, add them in the copy and record each as a fix.
- S1 segments of the four spike pages (`results/s1/segments/`).
- **Renditions.** M01 may produce renditions with html5lib (D4 M01). S0 and S1 used libxml2; on the
  seven pages S0 and S0-R2 use the two are content-identical and only keys differ
  ([s1.rendition-identity](records/s1.rendition-identity.json));
  take renditions, segment keys and offsets from `sample.json` and `results/s0r2/sample.json` as
  they stand.
- **Trace rows on v1.** D3 §10's T3 rows and the trace units' target claims, in their guideline v1
  form: the v1 reference `results/s0r2/reference_v1/T1.json`–`T4.json` (stored form). In
  particular, T3's C2 carries its restrictions `a ∈ ℝ` and `b ∈ ℝ ∖ {0}`; T4 runs to C17, with the
  standard normal and standard lognormal and the domains C11–C12; and context-premise claims cite
  `cN` sentences outside their unit as evidence.
- The S0 blind passes A and B in stored form (`results/s0/stored/pass_a`, `pass_b`), their
  alignment (`results/s0/compare/a_vs_b/`), and the S0 key-variant runs
  (`code/s0d_key_variants.py`, `results/s0/key_variants/`).
- [PostgreSQL tooling](../../../libraries/PostgreSQL_System_Tooling_for_Ubuntu.md).

## Procedure

1. **Database.** Create `cs_spike_s6` on the local server; `CREATE EXTENSION` for `vector` and
   `pg_textsearch`; record versions.
2. **DDL.** Apply the extracted SQL. Fix each error minimally in a copy and record the fix with
   its reason (`results/s6/ddl_fixes.md`). Do not edit D3.
3. **Rows.** Insert a project, schema version, configs, one finished run, the four spike pages'
   renditions and segments, and the trace units' entities, claims, evidence, supports (a fake
   task and observations) and links from the v1 reference. Check that T3's C2 stores its
   conditions, that T4's C1–C17 fit, and that evidence in a `cN` sentence outside the claim's unit
   is accepted and returned by the evidence query. Insert one golden pass (pass SV, with its model
   and inputs), its golden items with the `context` flag set on context-premise items, and a
   `reserved` document split for the Weibull page. Check every constraint fires on a
   deliberately bad row (object both entity and value; local entity without scope segment; a
   golden pass without a model). A span outside its rendition's text is a repository-layer check
   (INV-10), not a database constraint: note it, do not expect a database error.
4. **Queries.** Run each D3 §9 pattern and the four trace questions of D8 §5.3 in SQL; record
   rows returned and time. Where an expected answer in D8 §5.3 no longer matches the v1 rows
   (T2's `family_profile(normal)`, T4's claim list, T1's roles), record what the query returns
   and leave the correction to the design owner. Check `kb.run_observation` with a reused task.
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
9. **Key agreement under the revised statement key (B3).** S0 measured claim-key agreement on the
   70 aligned A/B pairs under four variants: as D1 §10.1 defines keys, 21 claim keys equal and 41
   meaning keys; statement keyed by its covering segment, 35 and 41; global label dropped when
   identity is complete, 21 and 54; both, 48 and 54 (record [s0.agreement](records/s0.agreement.json)).
   Recompute it under the revised statement key: a statement's anchor segment is the `unit` for
   statements inside a unit, the `details` block for proofs and solutions, and the paragraph
   outside units; its key is the anchor segment's key plus the ordinal of the statement's first
   sentence in it. A context-premise assumption whose sentences fall inside an existing
   statement's anchor is that statement. Add the variant to `code/s0d_key_variants.py` (or a new
   script), rerun `code/s0d_compare.py` on the normalized copies, and report claim-key and
   meaning-key agreement for the revised key alone and with the label rule, beside the four S0
   rows. List the pairs whose claim keys still differ and why.
10. **Meaning key.** Over the v1 reference batches, count facts restated in more than one unit
    (same subject, predicate, object and qualifiers, different statement). Twelve units may be too
    few to decide; if so, say so and leave the question to phase 1 goldens. Together with step 9
    this is the input to `OPEN-D3-4`.
11. Drop the database at the end; keep only results.

## Data to collect

| File | Content |
|---|---|
| `results/s6/ddl_fixes.md` | Each DDL error, the fix, the reason (including any B7 column added in the copy) |
| `results/s6/constraints.tsv` | bad row, expected error, observed |
| `results/s6/queries.md` | query, rows (abridged), ms; D8 §5.3 answers that differ from the v1 rows |
| `results/s6/bm25.md` | syntax used, top five per query |
| `results/s6/keys.tsv` | key variant: aligned pairs, claim keys equal, meaning keys equal (the four S0 rows and the revised-key rows) |
| `results/s6/restated.tsv` | fact, units, statements |
| `results/s6/vectors.tsv`, `results/s6/volume.tsv`, `results/s6/sizes.tsv` | timings and sizes |

## How to interpret

| Finding | Reading |
|---|---|
| DDL applies with only cosmetic fixes | D3 becomes migration 0001 (P0.3) with those fixes |
| A constraint cannot be expressed as written | Move the invariant to the repository layer's write checks and note it in D3 |
| Evidence outside a claim's unit needs a schema change | Record it for D3 §5 and the context-premise rule (D2 §7.3) |
| BM25 syntax differs from D3 | D3 corrected; `OPEN-D3-1` closed |
| Segment text is a small share of size | Keep it; `OPEN-D3-3` closed |
| The revised statement key brings claim-key agreement close to meaning-key agreement | Statement identity (B3) does the work; a stored meaning key is needed only for restated facts |
| Facts restated across units are common | Store a meaning key on claims (`OPEN-D3-4`) |

## Report

`S6-report.md` from the [template](report-template.md), with the corrected DDL as a diff against
D3's blocks and the key-agreement table as input to `OPEN-D3-4`.
