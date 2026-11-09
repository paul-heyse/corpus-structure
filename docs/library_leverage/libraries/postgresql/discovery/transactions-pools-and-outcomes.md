# Transactions, pools and outcomes

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Current ownership

[Store](../../../../../python/corpus-structure/src/corpus_structure/core/db/store.py) owns one Psycopg ConnectionPool per opened store, JSON/notice
configuration, checkout checks, admission bounds and extension admission after pool readiness.
Core borrows using creator=pool.getconn and NullPool with close_returns=True. Extension refusal
outside configure avoids hiding a domain failure behind reconnect attempts and PoolTimeout.
Store diagnostic data distinguishes cause, phase and known effects.
[Borrower cancellation](../../../../../python/corpus-structure/src/corpus_structure/core/db/lifetime.py) and
[ADBC cleanup](../../../../../python/corpus-structure/src/corpus_structure/core/db/adbc_lifetime.py) retain cancellation through transaction settlement
and independently attempt rollback/physical close. These are deliberate existing obligations.

## Research shortlist

| State | Mechanism and seam | Proposed value | Countercondition; next question |
| --- | --- | --- | --- |
| Conditional, tied to type adoption | Scoped adapters/custom typed connections, pool drain and replacement | Retire sessions with obsolete OID/adapter state without a second pool manager | Current initialization may already suffice. Does a selected new native-type lifecycle require generation invalidation, and can existing store ownership supply it? |
| Candidate underuse | Existing transaction characteristics/savepoints/force_rollback/Rollback(target) in provisional work | Delegate rollback semantics rather than hand-coordinating cleanup | Core already owns the transaction. Which actual provisional operation can use a native scope without confusing savepoint release with commit? |
| Candidate underuse | Existing cause/phase/effect diagnostics plus native transaction status/capability flags | Improve diagnosis where physical status provides genuinely new information | Library status cannot decide durable idempotency or unknown commit settlement. What current failure is ambiguous and what native observation distinguishes it? |
| Conditional | Zero-minimum persistent pools, resize/drain/readiness and callable connection parameters | Fit intermittent use or changing credentials with existing mechanisms | No demonstrated idle-session/rotation burden was established. Would the complete lifecycle be simpler than current settings? |

## Concrete ADBC acquisition inconsistency to assess

serve/database_description.py opens adbc.connect(uri) directly, whereas analytics can honor the
configured native driver path and owned_adbc_read cleanup. A shared existing acquisition/lifetime
boundary could remove inconsistent selection and cleanup. Blindly reusing analytics would impose
its builtin resolver; description needs richer server type resolution. Assess whether one owner can
accept explicit resolver policy and preserve primary exceptions while independently attempting
rollback and close. Cancellation is not currently a description input; it is separate scope.

The analytical decimal/hex-float scalar loops also have owned rounding, overflow, signed-zero and
source-column contracts. No simpler native replacement was established; keep them rather than
calling all Python conversion underutilization.

## Release-specific constraints worth retaining

Pool3.3.3 NullConnectionPool forces close_returns=False; it cannot transparently replace the regular
pool under Core's close-based return. Zero-minimum wait can succeed without proving connectivity.
Acquisition timeout is not operation timeout. putconn rolls back leftover transactions; it does not
commit them. Reset/check/growth share maintenance capacity, max_lifetime applies at reuse boundaries,
and resize/shrink do not synchronously replace the whole inventory. Existing SET LOCAL practice
reduces the need for aggressive reset logic.

Manual borrowing does not have the same usage-timing coverage as pool context borrowing; queue
counters count events rather than unique requests. Do not invent telemetry to prove efficiency.
Async drain exists in selected3.3.3; that does not imply meaningful null-pool drain semantics.
Psycopg SQLSTATE classes are not a hierarchy suitable for inferring every rollback class; keep
explicit classification and operation-owned retry scope.

ADBC context managers close rather than establish commit/rollback policy. Database-object cloning
shares resolver/database state, not snapshots, temporary tables or session settings. Changing
autocommit or executescript can commit active work. Arrow reader ownership is part of the operation,
not a guarantee supplied by its type. Prepared sessions, snapshots and caches have distinct lifetimes.

## Conditional territory and sources

LISTEN/NOTIFY is signaling rather than durable replay; inspect only for a wakeup consumer.
Async/gevent, dynamic credentials, PgBouncer, DNS/multihost/TLS/service configuration, driver
profiles/manifests, protocol tracing and two-phase commit remain contingent on an actual participant
or diagnostic need. Current explicit settings/driver path should not gain a competing authority.

[psycopg overview](../../../../libraries/postgresql/psycopg.md), [psycopg-pool overview](../../../../libraries/postgresql/psycopg-pool.md) and [adbc-driver-postgresql overview](../../../../libraries/postgresql/adbc-driver-postgresql.md) lifecycle
sections and addenda. Selected sources:
[pool3.3.3 null pool](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/null_pool.py),
[pool async drain](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool_async.py),
[ADBC25 DBAPI](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/python/adbc_driver_manager/adbc_driver_manager/dbapi.py).

Retain current outcome/cancellation machinery unless a concrete replacement discharges its full
contract. No fault campaign or new operational subsystem is justified solely by this discovery.
