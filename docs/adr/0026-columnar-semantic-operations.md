---
id: ADR-0026
title: Semantic projections share snapshots and compose analytical operations in DuckDB
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: An actual operation requires a representation or engine capability unavailable through the declared analytical profile.
---

## Context

The operator authorized SP-04/SP-05 and selected foundation plus existing set kernels, retaining
full consolidation/evaluation/interface migration in SP-07/SP-08. Existing native SQL kernels cross
repeatedly through Arrow tables, Python objects and JSON. A realization revision counter does not
reconstruct historical selections. New instance storage and protected publication already exist.

## Options

1. Keep table-in/table-out kernels and independent SQLAlchemy/ADBC reads. Least initial change,
   but retains repeated conversion and cannot establish a shared snapshot.
2. Replace DuckDB with DataFusion or introduce both. DataFusion's extensible plans are valuable,
   but no inspected operation requires that additional integration. Wider decimals are not a
   requirement: the operator explicitly selected rounded DuckDB-compatible analysis.
3. Compose operations in one DuckDB scope over release-compiled Arrow relations, sharing the
   PostgreSQL snapshot and protected publisher. Selected; reuses native libraries while retaining
   semantic authority and making resource lifetime explicit.

## Decision

PostgreSQL owns instances, visibility and admission. SQLAlchemy Core binds selections and result
mappings to the same release; pglast remains the authored PostgreSQL SQL boundary. PyArrow owns
columnar representation; DuckDB is the one local relational engine. Normalized value/role,
occurrence/fact, evidence/support and coverage relations preserve meaning. Operation-shaped nested
views are derived, not a second editable semantic catalog. No per-domain DDL is introduced.

Analytical decimal defaults are precision 38, scale 12 and HALF_EVEN, explicitly selected by the
operator. Original values, source report qualifications and canonical identities remain intact.
A release-bound profile governs rounding and output types; runtime settings govern resources only.
Overflow and unavailable operations are explicit. Approximate floating outputs are not relabelled
as exact decimal results.

SQLAlchemy owns a read-only REPEATABLE READ snapshot; ADBC imports it before data reads. Inputs
needed for replayable local operations are materialized before releasing database transactions.
Continuations bind the observed realization revision and refuse changes rather than pretending
that a counter provides historical replay. ADBC is a read transport, not a second writer/pool.
The pinned bundled driver is the default; an explicitly configured system driver must be qualified
and cannot silently fall back to a different driver.

Arrow publication uses pgpq 0.12 to encode fixed staging schemas and psycopg COPY on the existing
SQLAlchemy SERIALIZABLE connection. The protected publisher retains exact canonical content checks,
semantic identity and retry receipts. A final canonical serialization pass is retained; no claim
of zero Python conversion is made. No pgpq-generated DDL or unrestricted admitted-table write is
introduced. Analysis requiring current state fences the source revision in the enforcing transaction;
stale analysis is recomputed outside that transaction, not refreshed by blind transaction retry.

## Consequences

Prepared projection products can be reused; connection-bound relations cannot outlive their owner.
One-shot readers, materialized inputs and engine scratch are closed by the operation scope.
PostgreSQL pushdown and native DuckDB composition reduce avoidable representation crossings; no
performance or capacity benefit is claimed without measurements. Specialized finite algorithms
retain their owners. Full consumer migration and assembled qualification remain later packages.

Implementation and native acceptance are recorded in the existing pivot coordinator and package
owners. Acceptance of this record does not establish those outcomes.
