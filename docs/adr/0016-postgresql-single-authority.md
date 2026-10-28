---
id: ADR-0016
title: PostgreSQL 18 is the single authority for knowledge, operations and evaluation
status: proposed
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§B4]
evidence: Proposed
---

## Context

The old repository had almost no relational model of its operations: invocations, attempts,
lineage and custody lived in byte blobs, JSONL and runner state, with about nine authority concepts
and eight lock mechanisms ([design rationale](../design/rationale.md) §1.5, §2). The design makes
operations data (P5) and needs one transaction to link a task, its observations and the claims they
change. D3 specifies the schema. Spike S6 checks that the DDL applies, that the trace rows fit and
that full-text and vector search work.

## Options

1. **PostgreSQL 18 alone**, with four schemas (`meta`, `ops`, `kb`, `eval`), JSONB for variable
   payloads, pgvector and full-text search in the same planner.
2. **A graph database.** A second authority to synchronize; path-heavy queries are not the dominant
   workload; recursive CTEs and NetworkX projections cover traversal at this scale.
3. **An RDF triple store.** Qualifiers, evidence and statuses on statements are awkward in triples;
   RDF and JSON-LD stay LinkML-generated exports (D8 §6).
4. **DuckDB as the authority.** Single writer, no row-level queue semantics; it is the read-only
   analytics engine over PostgreSQL or Parquet (D3 §1, ADR-0010's catalog).
5. **A separate vector database or search engine.** Vectors and text must filter and join with
   segments and entities.

## Decision

Option 1, as D3 states it: one PostgreSQL 18 database holding knowledge, operations and evaluation;
pgvector `halfvec` for embeddings (from phase 1); built-in full-text search on segment text (pg_textsearch could not be installed; D3 §5);
DuckDB only for analytics and exports.

**Proposed until S6 reports** (operator decision, 2026-10-28). Acceptance follows S6's evidence and
the design/target review that precedes phase 0 execution.

## Consequences

- "Why did this run on that unit, and what did it cost" is a query (D3 §9), not a debugging session.
- Managed PostgreSQL hosting exists for the commercial product.
- **Depends on S6:** OPEN-D3-1 (full-text search on the corpus), OPEN-D3-3 (segment text), OPEN-D3-4 (meaning key) and
  the DDL corrections. Embeddings wait on S7 (OPEN-D3-2).
- **Revisit** if path queries come to dominate, write volume exceeds one database, or many corpora or
  tenants need separate stores.
