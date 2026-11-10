# Native evolution and bounded operational control

**Status: Planned; execution not started · 2026-11-09.** Target design is Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. No product or database changes were made while authoring.

## PTD-09 · Governed candidate transformations

Consumes [O11](../../functional_reviews/postgresql-typed-domain_2026-11-09.md). Keep NativeTransitionOp frozen before/after meaning, independent catalog
observation, ACL/ownership and dependency retirement. Refactor local nested operation transforms
using Rewriter.rewrites/chain only when the complete selected traversal is clearer and not dependent
on hidden mutable traversal state. Keep global FK/ACL/native retirement ordering explicit. The
selected workflow is existing candidate creation/preview/deploy for a changed overloaded function
and dependent trigger; do not introduce an alternate migration engine or regenerate old migrations.

Inventory manual nested transformations in native_candidate and directly affected renderer/operation
consumers. Compare a public Rewriter transformation with the existing explicit walk using independent
expected operations/order. If it adds machinery, retain the current walk and close that mechanism
choice with evidence; delivery still includes coherent candidate explanation and its existing native
drift/role checks, including PTD-05's diagnostic integration. Preserve frozen artifact identity rules.

Defaults/ARRAY and observed index collation adapters remain unless a supported hook at selected
versions demonstrably retains independent actual-state observation. Do not populate observed facts
from desired metadata. CreateView/DOMAIN/ENUM/Computed DDL does not supply comparison, ACLs or history.
A candidate must refuse stale before-state, unauthorized signature replacement and wrong ACLs; use
an actual restricted principal for its delivered native journey. Exact qualified OID/native object
lifecycle for any selected type is a prerequisite slice owned here, not a global gate on O01.

## PTD-I06 · Operational and broader native lifecycle decisions

Resolve all branches in the coordinator before completion:

- **Preview:** existing rollback-only authoring versus a reusable provisional transformation consumer.
  Select only database-transactional work with useful inspectable results; Core uses its own nested
  scope, standalone Psycopg can use force_rollback/Rollback(target). No competing owners or promise
  to roll back external effects. Acceptance: both successful/refused preview leave retained rows unchanged.
- **Session/type/credential replacement:** compare CLI restart with configure/scoped adapters/drain
  and replacement of ADBC database/type caches. A selected resident cutover pauses admission if needed,
  settles existing borrowers and checks new readiness. Drain does not instantly close active borrowers.
- **Intermittent capacity:** zero-minimum regular pool/resize only for identified resident workload.
  wait with min_size=0 does not prove connectivity. Keep admission/extension checks and current
  close_returns integration; selected NullConnectionPool is not a transparent replacement.
- **Large reads:** pinned keyset pages versus continuous ServerCursor/stream. Require consumer-owned
  early close, transaction settlement and clean next borrow. Held/refcursors need a real navigation
  or stored-procedure consumer and explicit affinity/materialization limits.
- **Wakeups:** resident task worker responsiveness via dedicated autocommit LISTEN/NOTIFY, followed
  by existing durable claims. Reconnect rescans; duplicate/missed signals cannot duplicate/lose work.
  Compare existing polling before selecting a new listener lifetime.
- **Diagnosis/remote operation:** add native status/capabilities only for useful failure distinctions;
  retain phase/effect knowledge and uncertain commit settlement. Opt-in tracing and TLS/services/
  multihost configuration stay under current settings with no credential/profile authority split.
- **Async/distributed:** identify actual interactive waits or transactional participants before async,
  PgBouncer, gevent, sharding/global top-k or two-phase machinery. Compare staged idempotent external
  publication first. A two-phase route requires a real durable coordinator and recovery obligations.
- **Native deployment variants:** NOT VALID/VALIDATE, concurrent indexes, multiple histories/offline
  SQL/batch rebuild and companion plugins each require a concrete lifecycle benefit. A concurrent
  deployment cannot rely on the existing transaction-scoped fence across autocommit boundaries.
  Any changed atomicity/fence, Core authority, publication authority or explicit plugin exclusion
  requires a concrete rule decision before a dependent target is fixed.

For each branch, identify actual workload, simplest complete route, prior mechanism retained or
removed, failure/recovery obligations and a decisive success/refusal case. Source reasoning can
close unsupported hypothetical variants without building them. No generic always-on operational
framework or mandatory fault/measurement campaign follows from covering these questions.

## PTD-10 · Selected branch delivery

This package is a family of bounded slices, not a blank implementation allowance. An investigation
must first add the selected slice's target, interfaces, consumed native/release contracts, affected
consumers, retirement, required checks and any actual operator decision to this series. Implement
and verify each selected slice before its dependent use; do not wait for all investigations as a
single barrier. A newly discovered obligation is owned here/coordinator rather than transferred to
PM2 or left as an unscheduled research note. No unresolved investigation counts as completion.

Sources: [native candidate](../../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py),
[migrations](../../../python/corpus-structure/src/corpus_structure/semantic/migrations.py),
[Alembic rewrite API](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html),
[pool3.3.3 source](https://github.com/psycopg/psycopg/tree/pool-3.3.3/psycopg_pool/psycopg_pool),
[operational review](../../functional_reviews/postgresql-typed-domain/operational-control.md).
