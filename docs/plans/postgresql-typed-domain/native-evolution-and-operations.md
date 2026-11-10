# Native evolution and bounded operational control

**Status: PTD-09 implemented and scoped tests passed; I06 decisions recorded, selected PTD-10 delivery remains coordinator-owned · 2026-11-10.** Selected package delivery is Tested at the scope recorded by the coordinator; conditional targets remain Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. The coordinator records execution separately from original authoring.

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

## PTD-09 selected mechanism · 2026-11-09

Retain the explicit operation walk at Alembic1.20.1. Public Rewriter.rewrites/chain supports recursive
replacement but does not remove shared created-table/privilege context or global retirement order;
callback conversion adds machinery for this selected workload. Retain defaults/ARRAY/index adapters
and independent actual-state observation. This closes the rewrite lead by assessed retention.

Add bounded typed inspect-candidate --view operations from verified frozen native JSON, retaining
sequence, qualified overload/trigger identity, create/change/retire/recreate, owner/ACL/property
differences and available dependency facts. Missing dependency/source detail stays unavailable.
Share inspection ownership with PTD05; large bodies are not emitted by default. Deliver the actual
composed overloaded-function/dependent-trigger/retirement journey under a restricted principal,
stale-state/ACL and recreation refusals, and successful/refused rollback-only authoring. Existing
isolated controls remain useful but do not substitute for that composed acceptance.

## PTD-I06 investigation decisions · 2026-11-09

**Decision basis: source-inspected at `baea0ed8e`; selected library interfaces checked locally,
2026-11-09.** Conclusions settle the bounded investigation, not runtime qualification. The
coordinator owns scheduled disposition. No I06 branch selects a new PTD-10 implementation:
existing operations supply applicable behavior, or the examined workflows lack the concrete
participant/lifecycle required by the alternative. Deferred cases name specific revisit conditions.

### Actual consumers and compared responsibilities

- **Store and borrowing:** `core/db/store.py:116–157` creates the regular Psycopg pool with
  configurable minimum, bounded acquisition, a real extension-check checkout and `close_returns=True`;
  Core borrows through SQLAlchemy NullPool. `semantic/runtime.py:69–95` owns the Store inside each
  `open_runtime_engine` context. `settings.py:41–62` already permits a zero minimum. A long-lived MCP
  process does not itself establish a long-lived database inventory: its tools delegate to semantic
  operation owners.
- **Cancellation and failure:** `core/db/lifetime.py:16–99` scopes cancellation through settlement
  and invalidates ACTIVE/UNKNOWN sessions. `core/db/store.py:190–224,245–395` retains phase/effects,
  cause, safe native fields and notices; `native_status` represents ADBC status, not PostgreSQL
  transaction status. `core/db/adbc_lifetime.py` independently attempts rollback and close;
  acquisition selects the configured resolver.
- **Workers:** `orchestrate/semantic.py:662–739` drains a scheduled batch and exits without more
  claims; `orchestrate/pm2_stage.py:1080` processes a finite admitted wave. These are not resident
  queue-polling loops. `semantic/sql/execution_projection.sql:72–90` owns durable lease/attempt claims
  with `FOR UPDATE SKIP LOCKED` and dependency predicates.
- **Reads/outputs:** `semantic/query.py:435,1209–1300` owns snapshots and qualified keysets.
  `serve/review_source_projection.py:91–121` and `serve/selected_source.py:412` already use `yield_per`.
  Selected-source export (`:325–354`) stages output in a temporary sibling, closes readers and settles
  its snapshot before no-replace publication. Companion Parquet/IPC custody is not a second
  transactional database participant.
- **Native evolution:** `semantic/native_candidate.py:1313–1380,1804–1846` already uses rollback-only
  savepoints, including catalog normalization. `semantic/migrations.py:30–76` requires one current
  head and caller-owned transaction, fenced with a transaction advisory lock.
  `semantic_alembic/env.py:31–55` refuses offline execution, accepts the caller connection, installs
  current native/default/index plugins and records applied revisions. Generated expressions already
  have independent catalog normalization; another DDL constructor would not add that lifecycle.

Locations above are under `python/corpus-structure/src/corpus_structure/`, except
`semantic_alembic/env.py` under `python/corpus-structure/`. The inquiry also covered settings,
the current MCP entry, O11/O13 review, lifetime/evolution discovery and relevant D3 decisions.
These are conclusions for examined workflows, not claims that library capabilities are absent.

### Branch decisions and revisit conditions

| Branch | Decision, complete alternative and reason | Concrete revisit condition |
| --- | --- | --- |
| Preview | **Retain** native authoring's Core savepoint/rollback and static candidate inspection. These already expose provisional native behavior. Psycopg `transaction(force_rollback=True)` suits a standalone Psycopg owner but duplicates the current Core-owned scope. | A named transactional data transformation needs provisional result rows unavailable from candidate inspection. Specify result custody and unchanged retained rows after success/refusal; external effects remain outside preview. |
| Type/session replacement | **Retain** per-operation fresh acquisition/restart. I01 selects no recreated native type or hot-cutover consumer. Scoped adapters on newly opened sessions remain available; drain/admission pause/ADBC database replacement adds coordination without a current consumer. | A selected native type is recreated while a resident owner must continue across its qualified OID/layout change. Reopen with I01; strict cutover must settle old borrowers. |
| Credentials | **Defer** callable connection parameters and drain. Current purpose URLs/per-operation acquisition have no selected rotating credential provider. Fresh acquisition/restart is the current complete route. | An actual provider supplies expiring credentials to a resident Store and restart cannot meet its requirement. Define provider failure and evaluation at new physical connection creation. |
| Idle capacity/resize | **Retain** current regular-pool settings, bounds and zero-minimum support. Real extension checkout proves connectivity even when `wait()` has no minimum to fill. No examined resident owner requires a capacity controller. | A workload retains an idle Store or requires changing declared capacity. Use existing settings/`resize` first; qualify cold acquisition, pressure refusal and shutdown. |
| Null pool | **Reject transparent substitution.** Pool3.3.3 NullConnectionPool forces `close_returns=False`, violating current Core return-through-close. Zero-minimum regular pooling covers intermittent retention without another borrowing route. | A distinct direct-Psycopg operation owns explicit unpooled get/put/close semantics, or selected upstream behavior changes. |
| Continuous large reads | **Retain** keysets for resumable navigation and existing Core `yield_per`/owned ADBC capture for continuous exports. Direct server cursors add ownership without a missing behavior in examined consumers. | A named continuous consumer cannot use these routes. Select ServerCursor or capability-qualified `stream(size)` with early close, rollback and clean next borrow. |
| Held/scrollable/refcursors | **Defer each.** Current navigation uses qualified tokens; examined procedures return no portal. These alternatives add affinity/materialization or require an actual cursor-returning procedure. | A named UI needs backward/absolute session navigation, or an admitted procedure returns a cursor. Declare affinity, materialization, reconnect and cleanup. |
| Wakeups | **Defer** LISTEN/NOTIFY. Actual workers drain finite scheduled batches rather than wait for newly committed tasks. A listener introduces a resident lifecycle instead of removing polling. Durable claims remain authoritative. | A selected persistent worker accepts tasks after its initial batch and needs prompt reaction. Dedicated autocommit listening must rescan after reconnect and tolerate missed/duplicate signals. |
| Diagnosis/status/notices | **Retain** cause/phase/effect reports, safe notice fields and existing cancellation status checks. No examined failure needs an additional status to choose a recovery action. Detached status after returning a borrower could mislead; status cannot settle uncertain commit. | A concrete managed failure has ambiguous actions distinguishable by a live owner observation. Capture within that lifetime and preserve the current ADBC `native_status` meaning. |
| Tracing | **Defer** bounded opt-in protocol tracing. No unresolved incident in this inquiry needs it; always-on tracing adds sensitive output/lifetime work. | A reproducible protocol incident is unexplained by exceptions/receipts. Define bounded trace custody and termination for that incident. |
| TLS/services/remote | **Retain** one purpose-URL/settings authority and standard libpq configuration. Current deployment uses the dedicated local socket; a parallel driver manifest/profile authority adds no benefit. | A selected remote endpoint needs certificate verification, services or target-session attributes. Qualify its actual settings and acquired endpoint without another authority. |
| DNS/multihost | **Defer** extra resolver/failover machinery. Standard libpq host/hostaddr/host-list configuration remains available through current settings; private connection-attempt hooks have no local-endpoint consumer. | A named multi-endpoint/DNS environment has a failure mode standard configuration cannot handle. Specify endpoint identity and selection/failure semantics. |
| Async | **Defer** database-stack migration. Stdio MCP delegates synchronous operation owners and workers drain finite scopes; no required independent concurrent database waits justify migrating cancellation/borrowing/settlement. | A selected interactive service has concrete waits requiring async ownership across acquisition, use, settlement and shutdown. One session still serializes commands. |
| Gevent | **Defer.** Examined MCP/worker runtimes have no gevent scheduler requiring cooperative integration. | A selected caller adopts gevent and requires qualified Psycopg support at its pinned versions. |
| PgBouncer | **Defer.** Local purpose-role connections own physical sessions directly; there is no selected proxy mode. | A deployment selects PgBouncer. Qualify pooling mode, session state, preparation, type adapters and admission before reliance. |
| External publication/2PC | **Retain** staged idempotent/no-replace file publication and native settlement; **defer** two-phase APIs. Files are not a second prepared-transaction participant. `tpc_*` cannot make filesystem effects atomic or supply a durable coordinator. | Two real transactional participants require coordinated atomic outcome and a durable owner can recover/resolve prepared transactions. Compare staged/reconcilable publication first. |
| Sharding/global top-k | **Defer** distributed query machinery. The authenticated corpus/exact retrieval have one acquired database authority and no selected multi-server consumer. | A real multi-server consumer requires it. I04 owns eligible identity/score/merge/incomplete-result meaning; this owner supplies consistency and participant recovery. |
| NOT VALID/VALIDATE | **Retain** atomic validated forward migration; **defer** staged validation. No selected constraint/backfill needs an admitted interval with unvalidated historical rows. Admission already observes validation state. | A concrete retained-table backfill needs separated enforcement/validation. Define intermediate admission, independent observation, retry and failure handling. |
| Deferrable/exclusion/generated | **Retain** current explicit invariants and generated-expression observation. Deferrable timing has no selected valid write sequence requiring temporary violations; exclusion has no newly selected mutual-exclusion invariant; generated columns already have a native/catalog route with no new derived field proposed. | Respectively: an actual write sequence requires deferred checking; a declared domain invariant forbids overlap; or a model-owned derived field needs generation. Include comparison/history/roles/admission, not only DDL. |
| Concurrent indexes | **Retain** atomic builds. Existing transaction advisory fencing cannot protect an autocommit-spanning build; no selected index/workload justifies replacing this complete lifecycle. | A concrete build requires continued availability. Present the rule proposal, atomic alternative, replacement exclusion, invalid-index cleanup, admission and recovery before selecting. |
| Histories/dynamic arguments | **Retain** one semantic head, explicit frozen artifacts and current applied-revision callback. Existing separate physical/semantic histories already have ownership; no new independently deployed component needs bases/branches/templates/runtime kwargs. | A real independently deployed component needs another history or runtime parameter. Specify dependencies/merge ownership and frozen effect identity; equal revision IDs cannot hide different effects. |
| Offline SQL | **Retain** live-connection refusal. Deployment requires acquired predecessor, transactional fence, observed successor and admission. No external offline deployer supplies those obligations. | A named deployer needs an artifact and complete live observation/admission/recovery. Obtain the concrete rule decision first; generating SQL is not deploying it. |
| Batch reconstruction | **Retain** PostgreSQL native ALTER/frozen forward operations and destructive-downgrade refusal. PostgreSQL18 does not require a generic rebuild route for the examined changes. | A specific retained-data rebuild cannot use a complete native ALTER route. Include copy, FKs/constraints, dependencies, ACLs, atomicity and recovery. |
| Plugins | **Retain** PTD09's explicit walk and native/default/index adapters. pytest-alembic has no identified missing journey beyond predecessor/catalog/role tests; enum helpers lack a selected enum lifecycle; Alembic Utils remains explicitly excluded by D3 without a demonstrated complete-contract gap. Multi-database/async migration plumbing has no selected added participant. | Reopen each for its concrete missing test/native-family/deployment responsibility. Alembic Utils needs a conforming alternative and explicit exclusion decision before dependent selection. |

### Library contracts and evidence limits

Installed Psycopg3.3.6/pool3.3.3 source confirms `transaction(force_rollback=...)`, named cursor
`scrollable`/`withhold`, `Cursor.stream` and pipeline refusal, pool `drain()` and retirement on return,
and NullConnectionPool's forced `close_returns=False`. Inspected files: `psycopg/connection.py:217–255,353–364`,
`psycopg/transaction.py:114–148`, `psycopg/cursor.py:150–194`,
`psycopg_pool/pool.py:339–358,735` and `psycopg_pool/null_pool.py:53–65` in the installed environment.
ADBC clones are not a resolver-generation replacement; retain the selected-source constraint from
O13. Existing `BorrowerCancellation` already observes transaction status at a useful live boundary;
that does not establish a need to copy it into detached reports.

**Outcome:** I06 decision work is complete at this source boundary. No new public API, native object,
configuration, daemon, transaction participant or production rule is selected. Earlier runtime
receipts retain their original scopes. Product tests/native probes/benchmarks are **not_run**:
source contracts settled the decisions and no product/database state changed. Publication checks
remain root-owned. PTD-10 selections from other investigations and PTD-11 combined qualification
remain separate work.


## Completion audit · 2026-11-09

No additional material PTD-09 implementation gap was found at f6288f574. Frozen operation
inspection and the explicit traversal retain qualified identity, owner/ACL and global retirement
ordering. The composed restricted-principal overload/trigger/retirement controls cover rollback,
stale-state refusal and sibling preservation; direct candidate inspection freshly read verified
frozen facts without replaying deployment. Fresh current-source authoring checks passed27; native
results retain their original contexts. The coordinator's
[completion audit](../postgresql-typed-domain_2026-11-09.md#completion-audit) owns the bounded judgment.
I06 decisions and pending PTD-10/11 were excluded.


## Selected native delivery · 2026-11-10

semantic_ptd_completion_repairs is deployed on the acquired development target. Exactly three
frozen body changes preserve before/after owners and ACLs: inference workspace begin/end and the
execution contract descriptor. Both workspace functions now have explicit current-source custody
through the existing source-guard route. Temporary generation/index details do not create a second
migration lifecycle. The [coordinator receipt](../postgresql-typed-domain_2026-11-09.md#completion-repairs-and-ptd-10-delivery--2026-11-10)
owns exact IDs, qualification and remaining PTD-11 work; I06 choices remain unchanged.
