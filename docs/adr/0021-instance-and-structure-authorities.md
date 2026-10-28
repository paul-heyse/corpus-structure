---
id: ADR-0021
title: PostgreSQL is the transactional authority for instances, the model for structure and meaning; set-based steps run in an in-process engine
status: accepted
date: 2026-10-28
supersedes: [ADR-0016]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: Path queries come to dominate, write volume exceeds one database, or many corpora or tenants need separate stores; or the in-process engine cannot be kept set-equal with the Python reference implementation, or a pass's pool no longer fits in process memory on this host.
---

## Context

ADR-0016 made PostgreSQL 18 the single authority for knowledge, operations and evaluation, with
JSONB payloads, pgvector and BM25 in one planner, and DuckDB "only for analytics and exports". S6
tested it (2026-10-28): D3's DDL applies after two corrections, the trace rows and queries run, BM25
and `halfvec` search work, and the queue runs each task once through a killed and a stalled worker
([S6 report](../design_review/evidence/2026-10-28_design-spikes/S6-report.md), records `s6.*`).

The [domain-model alignment review](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
(R05, R09; rule change RC02) found that "single authority" joins two different things. PostgreSQL
is and should stay the authority for **instances**: one transaction links a task, its observations
and the claims they change. But the **structure and meaning** of those instances (tables, closed
sets, relationships, invariants, payload classes) were stated by hand in D3, `vocab.py` and the
Pydantic shapes; ADR-0020 moves them into one model. Separately, the clause "DuckDB only for
analytics" excludes an engine for consolidation's set-based steps. D5 §1 already builds an in-memory
pool and runs steps as functions over it, but as Python loops that restate join keys; from phase 1
slot and alternative grouping, conflict self-joins, pack `views:`, noisy-OR, run diffs and
evaluation pairs are set-based work.

The expected changes: the phase 1 final pass over about 2,500 units (about 10⁵ observations and
10⁴–10⁵ claims per run, D3 §11, an estimate) while agent completions arrive; a business pack; and
two mechanism substitutions the review names, the pool as Python objects or as relations, and bulk
writes through psycopg or Arrow encoders. The operator accepted RC02 on 2026-10-28 and directed that
the relational pool and its engine be built in phase 0 ([coordinator §9.2](../plans/phase-0_2026-10-28.md#92-rule-changes-of-the-domain-model-alignment-review),
decisions 9 and 22).

Owners amended: DESIGN §B4; D3 header and §1. Consumers: consolidation (D5), evaluation's run diffs
and scoring (D7), exports (D8 §6), the bulk writer and loader (phase 0 pool and interchange).

## Options

1. **Keep ADR-0016 as accepted** (the simplest viable alternative): PostgreSQL as the one authority,
   pool steps in Python, DuckDB for analytics and exports only. It works at phase 0's scale, and a
   relational pool contract could still serve exports. But the set-based rules stay hand-coded loops
   restating join keys, `views:` stay builder code, and the structure of instances keeps an
   ambiguous owner. Rejected.
2. **Everything in PostgreSQL**, consolidation's steps as SQL. One engine, but fixture-local testing
   without a server is lost (FP-06), and identity forms would split between Python and SQL.
   Rejected; PostgreSQL keeps the transactional set work.
3. **DuckDB as the authority.** A single writer and no row-level queue semantics. Rejected, as in
   ADR-0016.
4. **A graph database, an RDF store, or a separate vector or search engine.** Each adds a second
   authority to synchronize; ADR-0016's reasons stand (qualifiers and evidence fit relational rows,
   RDF stays a generated export, vectors and text must join with segments). Rejected.
5. **Files as the payload store** (Arrow IPC or Parquet referenced by rows). Schema-free evolution,
   but a file write is outside the PostgreSQL transaction and files can be orphaned. Rejected for
   authoritative data; accepted for exports and analytic snapshots of finished runs.
6. **Instances in PostgreSQL, structure in the model, set-based pool steps in an in-process engine
   beside a Python reference implementation** (chosen).

Option 6 adds a dependency and a second implementation of the phase 0 set steps over option 1. It
keeps what option 1 lacks: set rules declared once as queries over model-named columns, `views:`
compiled to joins, and a tested seam for substituting the pool's mechanism. A speed benefit is a
hypothesis until measured (DP-22).

## Decision

- **PostgreSQL 18 is the transactional authority for instances** (carried forward from ADR-0016):
  one database with the schemas `meta`, `kb`, `ops` and `eval` holds knowledge, operations and
  evaluation; one transaction links a task, its observations and the claims they change; pgvector
  `halfvec` serves embeddings from phase 1 and BM25 through pg_textsearch serves lexical search, in
  the same planner.
- **The model is the authority for structure and meaning** (ADR-0020). The tables, columns, closed
  sets, relationships, invariants and payload classes are projections of the `system` and `core`
  modules; the database enforces what the generated projection declares (CHECKs, FKs, NOT NULL) and
  the physical overlay owns access paths. Every relationship a query joins on or an invariant
  constrains is relational; decision-relevant scalars are columns; other values are typed JSONB
  governed by the payload-schema registry (ADR-0022).
- **The consolidation pool is a set of model-typed Arrow relations** loaded as of the run's cut
  (the cut's semantics are D6's). Its set-based steps run in an **in-process DuckDB 2.0 engine with
  no persistent state**, beside a **Python reference implementation**; on the same inputs the two
  must be set-equal. Results return as relations to the bulk writer. Fixtures are Arrow tables, so
  the steps are tested without a server.
- **Identity stays in Python.** Canonical forms, digests, keys, label and token forms, locators, the
  quote cascade, TeX, SymPy, z3 and inference run in Python and reach the engine as data, because
  identity must have one implementation (no engine-side casefold, differing Unicode tables, key
  reordering in VARIANT and JSONB).
- **Transactional set work stays in PostgreSQL SQL:** materialization, deletion, fates, the run
  views, coverage and the typed queries.
- **Determinism:** relational step results are sets; any output whose order or floating-point value
  matters carries an explicit `ORDER BY` key, ordered aggregates and tie-breaks by key.
- **DuckDB also serves analytics and Parquet exports** of finished runs. Neither DuckDB nor files
  hold authoritative data.
- **Bulk writes** stay psycopg binary COPY; an Arrow-native encoder (pgpq) is adopted only if probe
  Q-5 shows absent versus null, JSONB, numeric and `timestamptz` survive.
- **Deployment settings are outside the model.** The model governs the structure and meaning of
  stored data; deployment settings (`settings.py`, hand-written pydantic-settings) are result-neutral,
  never stored, hashed or recorded as configuration, and no model-projected class is a settings class
  (coordinator decision 26).

## Consequences

- **Easier:** "why did this run on that unit, and what did it cost" stays a query; set-based rules
  are written once over model-named columns; pack `views:` compile to joins; the pool's mechanism can
  be substituted behind a tested contract; exports carry registry ids and need no PostgreSQL DDL for
  payload analytics.
- **Harder:** DuckDB 2.0 becomes a product dependency, pinned at 2.0.0 with a hold (a week-old major
  release whose Python result lifecycle changed); two implementations of the phase 0 set steps must
  stay set-equal; the `postgres` extension maps unconstrained NUMERIC to DOUBLE, so the pool reads
  through ADBC or psycopg, never through that extension; Arrow has only null, so the model declares a
  null policy per field.
- **Evidence:** the PostgreSQL parts are Tested and, where stated, Measured in S6 on the interim
  cluster (2026-10-28; rerun on `18/corpus` pending, D3 §11). DuckDB 2.0.0's lack of casefold,
  `USING KEY` components and VARIANT round trips are Interface-checked by a review contributor on
  scratch data (2026-10-28). The pool contract, the engine and the set-equality are Proposed.
- **Not yet built:** the pool contract and loader (P0-P-1), the engine and the set-equality harness
  (P0-P-2), the writer and export (P0-P-3), probes Q-4, Q-5 and Q-7. Disposition of the review's
  findings is in the [phase 0 coordinator's §11](../plans/phase-0_2026-10-28.md#11-findings-disposition);
  acceptance of this record closes none of them.
- **Revisit** (front matter).
