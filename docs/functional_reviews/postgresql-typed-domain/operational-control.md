# Operational control through existing owners

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`. The
[lifetime discovery](../../library_leverage/libraries/postgresql/discovery/transactions-pools-and-outcomes.md)
retains selected-release qualifications. Benefits are qualitative; no new runtime probe was needed.

<a id="O12"></a>
## O12 — Consistent ADBC acquisition with explicit operation policies

An operator should receive the configured native driver consistently across description, capture
and export, and retain the original refusal when cleanup also fails. Description calls adbc.connect
directly; analytics honors the configured path but fixes resolver mode to builtin.
[owned_adbc_read](../../../python/corpus-structure/src/corpus_structure/core/db/adbc_lifetime.py)
already independently attempts rollback and physical close, preserving primary failures.

Recommend a small acquisition factory at the existing database infrastructure boundary, accepting
configured driver path and explicit resolver mode. Compose it with owned_adbc_read. Keep capture's
builtin policy and description's server-aware type discovery distinct. Close readers/cursors inside
the owned lifetime. Migrate capture, companion/CLI export and description; retire direct acquisition
duplicates and the analytics-owned factory. No extra pool or generic connection manager is needed.
A description-only patch leaves configuration ownership split; clones share database/type-cache
state rather than snapshots or transaction state and are not a substitute.

Acquisition failure owns no returned session; later failures attempt rollback and close independently.
Cancellation remains explicit where supported. Delivery includes configured-driver parity, retained
numeric metadata and an original error accompanied by both cleanup failures. Prioritize alongside O10.
Sources: [analytics](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py),
[description](../../../python/corpus-structure/src/corpus_structure/serve/database_description.py),
[ADBC lifecycle addendum](../../libraries/postgresql/adbc-driver-postgresql.md).

<a id="O13"></a>
## O13 — Bounded operational workflows

[Store](../../../python/corpus-structure/src/corpus_structure/core/db/store.py) already owns pool
inventory, Core borrowing, extension admission and cause/phase/effect diagnosis. Extend operation
contracts there rather than add another subsystem. The following conditional capabilities have
credible consumers; selection depends on their stated premise, not on an adoption quota.

**Provisional inspection.** A maintainer could run a transactional transformation, inspect its rows
and native refusals, then discard it. Core-owned work uses begin_nested and explicit rollback;
standalone Psycopg work can use transaction(force_rollback=True) or Rollback(target). Avoid competing
transaction owners. Preview completion differs from publication and cannot promise rollback of
external/nontransactional effects. Activate for a transformation that static preview cannot explain;
deliver unchanged retained rows after both successful and refused previews. Reuse existing candidate
authoring rather than introduce a general execution sandbox.

**Session-generation replacement.** A resident service recreating a named type or rotating credentials
could settle old borrowers while new borrowers receive the new binding. Compose connection-scoped
adapters, configure/callable parameters and pool.drain. Replace owning ADBC database objects when
resolver caches are invalidated; cloning is insufficient. Drain does not instantly retire active
borrowers: strict cutover needs paused admission, settlement and readiness. Deliver an old borrower
completing and a new borrower receiving the new type/credential. Process restart remains simpler
for short CLI commands. This capability is conditional on actual type recreation or rotation.

**Intermittent capacity.** A resident occasional-use service could release idle sessions using a
zero-minimum regular pool and resize declared capacity. Keep bounded acquisition and explicit
connectivity/extension checks: wait can succeed with no connection at min_size=0. NullConnectionPool
in selected3.3.3 forces close_returns=False and cannot transparently replace the regular pool under
Core close-based return. Deliver cold acquisition, pressure refusal and clean shutdown. Adopt only
for an actual resident-session burden or changing workload, not as a universal CLI default.

**Large interactive reads.** An operator could stop a large read early without collecting its full
response. Prefer current pinned keyset pages for resumable navigation; choose ServerCursor for a
continuous session-owned read or capability-qualified stream(size) where appropriate. Consumer
abandonment closes iteration, settles transaction and releases borrowing. Held/scrollable/refcursors
remain alternatives for actual navigation/procedure consumers because they add session affinity and
possibly materialization. Deliver early stop followed by clean borrowing. Bound ADBC result streams
are not bounded COPY buffering.

**Prompt wakeups.** A resident worker could react to committed tasks through a dedicated autocommit
LISTEN/NOTIFY listener and bounded notifies(timeout, stop_after), then claim through the durable task
owner. Reconnect rescans durable state; missed/duplicate signals cannot lose/duplicate work. Keep
polling until prompt reaction matters. Deliver reconnect recovery and competing claimers without
another queue or notification log.

**Actionable diagnosis and remote deployment.** Add native transaction status/capability information
to existing failure reports only where it distinguishes acquisition, execution or capability refusal.
Physical status cannot settle uncertain commit acknowledgement. Bounded opt-in protocol tracing is
appropriate for an unresolved incident, with controlled sensitive output. A remote deployment could
use libpq services/TLS/multihost through the current settings owner; manifests/profiles must not add
an independent configuration authority. Demonstrate a useful diagnosis rather than a telemetry census.

**Async/distributed participants.** A future interactive service with many waits could migrate to
AsyncConnectionPool with coherent cancellation/settlement; one session still does not execute commands
independently. An external-publication workflow should first compose PostgreSQL receipts with staged,
idempotent publication. Two-phase commit needs a real second transactional participant and durable
coordinator capable of recovery/resolution. Those participants are unspecified today; async/gevent,
PgBouncer and two-phase infrastructure are unselected, with actual deployment/participant adoption
as revisit conditions. Partitioning/sharding/global top-k similarly require a complete distributed
query/identity contract rather than merely a library option.

Concrete APIs/limits: [Psycopg](../../libraries/postgresql/psycopg.md),
[pool](../../libraries/postgresql/psycopg-pool.md), [ADBC](../../libraries/postgresql/adbc-driver-postgresql.md).
Independent delivery examples above belong to later selected scope; tests/native probes are not_run
for this source-based review.
