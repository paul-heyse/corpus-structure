---
id: ADR-0025
title: Semantic publication uses protected staging and release-bound native enforcement
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A required semantic constraint cannot be faithfully lowered, protected temporary staging cannot retain its ownership boundary, or the deployment needs crash-durable acknowledgements.
---

## Context

ADR-0024 selects release-bound semantic interpretation and PostgreSQL instance authority.
The operator authorized SP-02/SP-03 in the [PostgreSQL plan](../plans/semantic-model-pivot/postgresql-and-publication.md).
The selected legacy writer has database-owner privileges. Application-side validation alone
cannot protect admitted facts from concurrent writes or a caller bypassing that validation.
A release must also survive without its original source tree or mutable ontology services.

## Options

1. Validate in Python and COPY directly into admitted tables. This has the least deployment
   machinery, but grants callers the ability to bypass interpretation and state-dependent checks.
2. Let a protected function read caller-owned temporary staging tables. This avoids persistent
   staging cleanup, but an attacker can substitute views, triggers, rules or policies that run
   with the publisher's authority. Schema qualification alone does not establish trusted ownership.
3. Protect both staging ownership and publication. Selected. A fixed-schema definer creates native
   transaction-local tables; the writer receives column INSERT privileges. This adds a small
   reviewed routine companion, but preserves COPY, one transaction, automatic cleanup and native
   concurrency enforcement without a persistent staging service.

## Decision

The trusted physical LinkML module derives one SQLAlchemy MetaData. Candidate domain classes and
properties become immutable release rows, never new tables. An explicit Alembic history bootstraps
fresh databases without importing the selected legacy knowledge schema. Frozen revisions own
physical DDL and routine deployment; ordinary semantic extensions leave migration head unchanged.

Archive exact authored bytes, resolved dependencies, preparation profile and generated products.
Reload reparses only those archived inputs under the recorded supported compiler stack and compares
all products. Activation checks native lowering and atomically compares both the expected parent
and generation. Realizations retain their own release binding when the project pointer changes.

Separate the migration/operator role, NOLOGIN publisher, authenticated writer and authenticated
reader. The writer has no admitted-table DML, owner membership or generic temporary-table creation.
On the dedicated local cluster, peer mappings authenticate the restricted principals without
putting administrator credentials into application settings. Administrative provisioning is a
separate explicit command and never changes another cluster or existing run database.

SQLAlchemy owns SERIALIZABLE transactions. COPY borrows that connection's psycopg driver; it does
not acquire or commit another connection. Protected publication verifies staging ownership and
shape, recomputes exact batch and semantic identities, and validates candidate plus admitted state.
Evidence occurrences remain separate from semantic facts and accepted-value selection. Whole
transaction retry retains the immutable batch identity. A lost commit response is resolved through
its atomic receipt; it never invents new occurrence identities.

Authored SQL has a bounded pglast syntax/dependency boundary followed by PostgreSQL catalog/type
analysis under the actual restricted reader. Unapproved functions and constructs refuse before
planner evaluation. Raw SQL is a hashed release dependency; catalog admission is a separately
archived deployment product bound to that release and physical model, avoiding self-referential
release identities. Ordinary Core queries bypass this authored-feature boundary.

## Consequences

One existing psycopg pool lent to SQLAlchemy NullPool remains the connection owner. No second
pool, ontology acquisition, LLM call, background staging cleanup or historical compatibility path
is introduced. Native constraints and relational predicates own write integrity; PySHACL is an
independent semantic check, never a validation flag authorizing skipped database checks.

The implementation initially refuses semantic constructs without faithful native lowering. Such
refusals are limitations, not evidence that their intended capability is complete. The owning plan
records exact coverage and remaining obligations. Full consumer cutover and assembled qualification
remain later pivot packages.

The operator's regenerable-data configuration keeps synchronous_commit off. Successful receipt
lookup establishes committed visibility, not a promise that an acknowledged commit survives an
operating-system/server crash. ADBC owns a separate libpq connection and cannot replace the same-
transaction psycopg COPY path. Exact NUMERIC reads retain PostgreSQL type metadata over Arrow's
text storage; downstream numeric operations require explicit lossless lowering.
