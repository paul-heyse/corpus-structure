---
id: ADR-0046
title: Generate domain operations and relational native products from unified contracts
status: accepted
date: 2026-11-02
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A required operation cannot preserve its admitted semantic, native or transport contract through the finite authoring profiles.
---

## Context

The unified-model review R01–R09 and O01–O03 identified remaining independently maintained
operation bindings, comparison annotations, relational expressions and native programs. The
operator accepted RC01–RC03, rejected client-only enforcement RC04, and authorized the
[UM series](../plans/unified-domain-model_2026-11-01.md). Existing effective LinkML models,
prepared boundaries, Core metadata, restricted publication and frozen native evolution are
working foundations. Their existence does not establish complete generated operation continuity.

## Options

1. Keep independent SQL/bind/result definitions and add correspondence checks. This is the
   smallest local change but repeats semantic decisions across maintained consumers.
2. Adopt a universal procedural language or SQLGlot execution intermediate. This adds another
   compiler/executor and does not establish complete PostgreSQL procedural generation.
3. Generate finite typed operation/projection/native products from resolved model contracts,
   with explicitly bound specialized implementations and independent native admission. Selected:
   shared structural decisions localize change while retaining set execution and database authority.

## Decision

Effective model references govern comparison roles, operation parameter/result correspondence,
relationship endpoints and invariant enforcement/diagnostic bindings. Generate concrete typed
callables, Core selections, materializers and directional Arrow products from those definitions.
Keep specialized algorithms in ordinary trusted implementations. Resources are invocation inputs;
release-owned scientific meaning remains distinct.

Core is the primary relational execution representation. pglast supplies structured PostgreSQL
native declarations and eligible SQL-standard bodies. Extend existing inventory, catalog,
comparison and Alembic frozen operations with explicit versioned profiles before admitting them;
old source-body profiles retain their exact semantics. Exact deployment bytes and server-normalized
comparison evidence have different purposes. No raw catalog OID tree is a portable identity.

SQLGlot provides qualified model-bound projection/dependency analysis for actual impact and
validation consumers. It neither authorizes effects nor establishes scientific provenance or
complete procedural equivalence. Native guard timing, owner/ACL/search-path, atomic publication,
transaction and cancellation guarantees remain in force under ADR-0031/0033.

Query execution resolves an admitted producing/installed compatibility binding before importing
an installed plugin. A query name/version or matching data fields cannot substitute for that
binding. New archived products are versioned; unsupported old named routes refuse rather than
execute arbitrary archived code or silently reinterpret their meaning.

This adds authoring and consumer contracts to ADR-0031/0033; it does not replace their restricted
writers, fixed relation/row variation, archive custody or qualified-kernel guarantees. Physical
binding changes preserve semantic product pins. Source publication and later consumer preparation
have separate outcomes; failed preparation alone does not invalidate a published document.

## Consequences

An operation change propagates through generated structural bindings and actual consumers.
Profile/ABI evolution, native comparison and independent tests remain necessary. Selective,
set-shaped preparation avoids reconstructing a book for section-only work; complete exports and
necessary global validation retain their scopes. No universal interpreter, alignment lint,
second catalog, mandatory benchmark or new resource framework follows.

This accepted decision establishes the target and authorization, not implementation or acceptance.
The UM coordinator owns package progress and evidence; the PDF coordinator retains its operational
book/provider/default-adoption obligations. D2, D3 and D8 own the corresponding architectural target.
