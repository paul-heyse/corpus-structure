# Execution outcomes and resource lifetimes

**Proposed target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-02/05 status and source O02/O03/O09 disposition. This document owns their technical explanation.

## Foundation and intended behavior

`core/db/store.py::classify_error` and `semantic/publication.py::_publish` currently infer connection loss from `OperationalError` without SQLSTATE. The consequence is more than duplicated code: acquisition pressure, administrative closure and an uncertain commit require different actions. The target carries native cause, execution phase and known effect separately. Do not turn each axis into a durable registry; a typed operation result or exception context is sufficient unless an existing consumer must persist it.

Use three connected responsibilities:

- Storage translates native exception/SQLSTATE/invalidation into an observed cause: admission pressure, checkout deadline, closed inventory, transport loss, serialization/deadlock, cancellation, constraint/fence refusal or defect. Unknown stays unknown.
- The operation knows whether it had acquired a connection, begun effects, attempted commit or lost acknowledgement. That knowledge qualifies possible effects; it cannot be inferred solely from the last exception.
- Publication/replay/read owners choose retry, receipt lookup, refusal or cancellation settlement. Native reconnect backoff repairs inventory; it never retries a domain operation.

The externally useful outcome includes operation identity/pin, phase, native code when available, whether effects are absent/rolled back/committed/uncertain, and the existing remediation action. It need not expose connection credentials, raw SQL or provider internals. Migrate `semantic/refusals.py` and affected CLI/MCP error reports with this meaning. No path may label fencing or user cancellation retryable merely because both interrupt execution.

## PG-02 — Phase-aware outcome integration

Replace both lost-connection heuristics with one native-cause translation consumed by the actual operation policy. Preserve immutable publication input and the existing receipt lookup. A failure before checkout must not cause ambiguous-commit lookup; loss during commit can require resolving the original identity rather than republishing a new one. Serialization/deadlock retries repeat the transaction with its original input; no local retry bypasses task authority. A savepoint-local failure can recover locally only where the operation's declared effects permit it.

Keep lower-level original exceptions available as causes. Add the minimum typed context needed to avoid interpreting formatted messages downstream. This deliberately changes external failure categories; update consumers and independent expectations in the same package rather than retaining a misleading compatibility alias indefinitely.

**Closure:** exercise native pool closure/timeout/pressure separately, pre-checkout failure, mid-write rollback, post-commit lost acknowledgement, stale holder, cancellation and unclassified exception. Verify actual receipt semantics with PostgreSQL for effect claims. Pure fabricated exceptions only establish translation branches, not ambiguous-commit recovery. No duplicated classifier remains in publication/refusals.

## PG-05 — Owned resources and useful native diagnostics

Retain one regular Psycopg pool per current process/principal and SQLAlchemy `creator=pool.getconn`/`NullPool` with `close_returns`. Core owns checkout/transaction; COPY borrows its checked Psycopg connection. Do not substitute Psycopg NullConnectionPool based on its constructor resemblance. Configure connection-local JSON/adapters, keep callbacks idle and light, and retain actual connectivity/principal checks on opening. A minimum-zero pool's `wait()` is not connectivity evidence.

Expose queue admission (`max_waiting`) and acquisition deadlines through the existing database/runtime settings when needed by simultaneous analytical capture, append and heartbeat operations. Use the concrete initial defaults below and reassess them against actual concurrent consumers in PG-00; do not multiply limits independently at each layer. Do not add another queue around the native pool. Session adaptation, prepared statements and temporary state must have a declared reset/reuse boundary; indiscriminate resets can discard useful preparation.

Long database operations retain a cancellation handle at their actual owner. Use Psycopg `cancel_safe(timeout=...)` for Psycopg work and ADBC cancellation for its own statements/connections; neither cancels another driver's session. Request cancellation, observe actual completion, close/drain cursor/reader, then rollback or resolve uncertain commit before return. A pool close does not settle a borrower. Give the claim-renewal operation an effective statement/acquisition deadline so joining its worker does not depend on an indefinitely blocked query. Do not invent a hard total shutdown promise unless it is actually established.

Use native `get_stats`/`pop_stats` and `psycopg.pool` logging for demanded diagnostics, with one consumer of destructive counter reads. Manual `getconn` borrowers are outside `pool.connection()` usage timing. Add timing at the borrower only if an operator question requires that missing observation. Copy selected Psycopg `Diagnostic` fields inside notice callbacks; report SQLSTATE, constraint/table/column and hint where available. Structured ADBC fields may be incomplete. Unknown does not become zero.

Deliver one operator-visible diagnostic result through the existing database CLI/report conventions, including actual failure cause and meaningful pool state; use existing application logging interfaces rather than importing unrealized logging-plan scope. Optional rotation/wakeups/progress extensions remain deferred at the coordinator.

**Closure:** real concurrent pressure, cancellation during query/COPY, abandoned row/batch iteration, connection reuse after settlement, heartbeat stop, absent diagnostic fields and manual-borrow metric interpretation. Query cancellation does not establish absence of committed effects. Native statistics do not establish task success. Keep typed outcomes and cleanup independently testable without starting inference.

## Library basis and design fit

[Psycopg original §§3–13 and addendum §§1–8](../../libraries/postgresql/psycopg.md), [pool original §§3–11 and addendum A1–A8](../../libraries/postgresql/psycopg-pool.md), and [SQLAlchemy execution/pooling](../../libraries/postgresql/sqlalchemy.md) supply native mechanisms. FP-01/04/05/06 and H4/H21/H23–25 favor delegating inventory while retaining domain effect policy. The explicit phase context removes independent reinterpretation without creating a generic resilience framework.

## Concrete execution contract — PG-02

**Proposed, 2026-11-01.** The following names are interface sketches; the distinctions and ownership are selected. Implement the physical observation in `core/db/store.py`, with operation context supplied by publication/read/renewal owners. Do not make storage import semantic task models.

```python
@dataclass(frozen=True)
class DatabaseFailure:
    cause: DatabaseCause
    phase: DatabasePhase
    effects: EffectKnowledge
    sqlstate: str | None
    constraint: str | None
    invalidated: bool
    cancellation_requested: bool
```

`DatabasePhase` distinguishes acquiring, executing, committing and resolving. `EffectKnowledge` distinguishes no effects started, rollback confirmed, commit confirmed and uncertain. The initial value before checkout is no effects started; after execution begins it is uncertain until the owner observes rollback or commit. A locally returned receipt inside a transaction is not commit confirmation. Recovery action is chosen separately by the operation and is carried in its external failure report; it is not a field inferred by a native exception translator. Preserve the original exception with exception chaining. Existing task/publication identity stays in the operation report, without copying full immutable input into every physical failure.

| Native observation | Physical cause | Operation interpretation |
|---|---|---|
| `PoolClosed` | inventory closed | Refuse current lifecycle; no reconnect/retry loop against the same closed Store |
| `TooManyRequests` | admission pressure | Caller receives overload; no immediate hidden transaction retry |
| `PoolTimeout` | acquisition deadline | No checkout/effects for this acquisition; distinguish from statement timeout |
| SQLSTATE `40001` / `40P01` | serialization/deadlock | Retry the entire transaction only after its failed attempt is settled, within the existing attempts bound |
| SQLSTATE `57014` | query cancelled | Record native cancellation; distinguish operator-requested cancellation from statement deadline through operation context |
| SQLSTATE `23505` and the known observation fence constraint | fenced publication | Preserve authority refusal; never retry by minting another holder or identity |
| SQLAlchemy `DBAPIError.connection_invalidated`, or driver reports broken connection | unusable physical connection | Qualify effects by phase; invalidation is not proof that commit failed |
| `OperationalError` without SQLSTATE, without stronger observation | unknown operational failure | Preserve unknown; absence of a code does not establish transport loss |
| Other native constraint or unknown exception | constraint failure or unknown/defect | Preserve native fields and operation-specific refusal rules; no default replay |

Unwrap SQLAlchemy `DBAPIError.orig` once for native translation while retaining the wrapper's invalidation fact. Pool exceptions must be checked before broad Psycopg operational exceptions. Available ADBC status/vendor/detail fields are a separate adapter into the same observation meanings; do not invent SQLSTATE from a generic status or parse localized error messages. Only the execution owner has phase/effect context. The refusal boundary receives that context; it does not reconstruct it from `str(error)`.

### Publication transition and acknowledgement recovery

Replace `_publish`'s combined `with connection.begin()` commit ambiguity with explicit phase updates surrounding the same SQLAlchemy transaction lifecycle. Keep a single context responsible for rollback/close. An implementation can enter `connection.begin()` explicitly, invoke the publication function, set phase to committing immediately before `transaction.commit()`, and observe success before returning the receipt. Exception handling must settle the transaction before releasing the connection and before starting receipt resolution on another checkout. Do not nest an independently committing Psycopg transaction around the borrowed driver.

| Failure point | Known effects | Required action |
|---|---|---|
| Checkout fails | No effects started | Report acquisition cause; no receipt lookup |
| Statement/encoding fails, rollback confirmed | Rolled back | Apply existing attempt policy for retryable causes; discard failed encoder |
| Connection lost during statements, commit never invoked | Not acknowledged; transaction cannot be replayed until settled | Close/invalidate the unusable borrower; preserve original input for a permitted retry; no newly minted publication identity |
| Commit invoked, acknowledgement lost | Uncertain | Resolve the original immutable publication identity with the existing receipt lookup |
| Receipt exists and exactly matches original input | Commit confirmed through durable lookup | Return existing receipt without executing publication again |
| Receipt absent while earlier commit outcome remains unresolved | Uncertain | Absence alone is not proof of abort; use the existing idempotent/fenced native publication protocol for any permitted replay |
| Resolution itself cannot connect | Uncertain | Return unresolved acknowledgement outcome with original identity; do not call it a rollback |

A successful lookup must retain the existing content-equivalence checks. The same identity with changed bytes is a conflict, not a retry. User cancellation arriving during acknowledgement recovery does not authorize abandoning a potentially committed identity as absent. Resolve when possible; otherwise return the uncertain effect explicitly.

### Actual migration footprint

Move `classify_error` consumers and `semantic/publication.py::_publish` together. Change `semantic/refusals.py::database_failure_code` and `tool_refusals` so reports distinguish physical cause from semantic refusal and carry phase/effects when available. Calls without operation context report unknown effect rather than guessing. Follow callers of `tool_refusals` into their current CLI/MCP rendering boundaries; migrate every use of the former flat `ErrorClass`, not only publication's two representative transports. Preserve deliberate user-facing refusal messages without exposing SQL, credentials or raw payloads.

**Independent controls:** a saturated actual pool produces overload without receipt lookup; a deliberately closed pool stays closed; rollback leaves zero public rows; an actual committed publication followed by controlled loss of acknowledgement resolves to its original receipt; changed duplicate content refuses; a cancelled operation does not enter serialization retry. Fault injection may control the client acknowledgement boundary, but PostgreSQL contents and receipt identity must independently establish effects. Fabricated driver exceptions qualify only translation logic.

## Borrower lifecycle and settings — PG-05

**Source-inspected, 2026-11-01:** `Store.open_store` defaults to min 1/max 4/checkout timeout 30 seconds, with explicit open/wait and extension checking after configuration. `settings.DatabaseSettings` currently supplies URLs/template rather than queue/deadline controls. `maintained_claims` joins its renewal thread without a query deadline. Those facts identify migration seams, not current operational qualification.

Expose `pool_min_size=1`, `pool_max_size=4`, `checkout_timeout_seconds=30` and `pool_max_waiting=4` through the existing database settings. These are selected initial defaults for the single-operator workload, not capacity claims. Validate min ≤ max and positive timeout/queue bound. Existing explicit `open_store` arguments remain deliberate call-level overrides during migration; move production callers to the settings once consumers are identified. `0` means unlimited waiting in the pool API, so it is not the selected queue default. Batch jobs and heartbeat checkouts share the same inventory and bound rather than acquiring independent queues.

Use the regular `ConnectionPool(open=False, close_returns=True, configure=configure, check=check_connection)` with `create_engine(..., creator=pool.getconn, poolclass=NullPool)`. The returned Core Connection owns the transaction and closes the checkout. A raw COPY helper receives `connection.connection.driver_connection` only within that borrow; it neither closes it nor calls `pool.putconn`. A standalone `pool.connection()` scope is permitted for the existing readiness check because that scope owns its transaction and return. Do not mix that committing scope with an already-owned Core transaction. See [pool integration](https://www.psycopg.org/psycopg3/docs/advanced/pool.html#pool-sqlalchemy) and [pool parameters](https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.ConnectionPool).

Configuration retains connection-local JSON adaptation and leaves the connection idle. Extension/principal validation stays after opening so a semantic mismatch is not converted into pool reconnection attempts. Preserve `SET LOCAL` application state. Add no global `DISCARD ALL` reset: it destroys prepared state and is unnecessary when operation-local state is correctly scoped. If a future selected adapter requires reset, document its exact state and ensure callback entry/exit is idle. Callback work and pool return may execute in maintenance workers; successful `close()` is not a domain completion receipt. The [local pool addendum A1–A8](../../libraries/postgresql/psycopg-pool.md) explains return scheduling and counter limitations.

### Cancellation sequence and ownership race

The operation exposes a cancellation request to its own borrower owner. Retain a live cancellation handle only while that checkout is registered to the operation. A request marks cancellation before dispatch; deregistration/return synchronizes with dispatch so a delayed request cannot cancel the next borrower's query. This can be a small lock-protected owner scope, not a connection registry. Do not share a normal cursor concurrently; cancellation uses the driver's cancellation facility while the execution owner observes its running call settle.

1. Stop producing batches/starting statements after cancellation is requested.
2. Request `driver.cancel_safe(timeout=cancel_request_timeout_seconds)` for this Psycopg session; select a 5-second request timeout initially. Check the installed libpq capability when exercising this path: the timeout applies to modern libpq cancellation, not a total operation-cleanup promise. Do not use it in a signal handler.
3. The executing owner observes the query result/error, exits COPY/reader scope and settles its transaction. SQLSTATE `57014` alone does not say who requested cancellation or that earlier work committed nothing.
4. Inspect native transaction status only as a cleanup observation: `ACTIVE` still has work in flight; `INERROR` needs rollback; `INTRANS` needs the owner's rollback; `IDLE` means no open transaction, not proof of a particular domain result; `UNKNOWN` is unusable. Return only settled healthy connections. Invalidate/discard an unusable borrower through the actual driver/Core ownership route; calling `close()` with `close_returns=True` is a return request, not an unconditional socket kill.
5. Deregister the cancellation handle before returning the borrower. Resolve uncertain commit as specified above. Perform all independent owned cleanup even if another cleanup fails, preserving the primary failure and secondary cleanup diagnostics.

`cancel_safe` and its libpq limitation are described in [connection cancellation](https://www.psycopg.org/psycopg3/docs/api/connections.html#psycopg.Connection.cancel_safe); transaction status meanings are in [connection information](https://www.psycopg.org/psycopg3/docs/api/objects.html#psycopg.ConnectionInfo.transaction_status). ADBC-owned operations must use their own native cancellation and close their readers/cursors/connection; no Psycopg handle can settle an ADBC session. Their exact capture scope is owned by [typed transfer](typed-realization-and-transfer.md).

For renewal, use checkout's finite native deadline and transaction-local `statement_timeout` and `lock_timeout` through the existing Core transaction. Select initial renewal limits of 10 seconds statement and 5 seconds lock; a lock timeout cannot exceed the statement budget in this default. Renew all selected claims in the owned transaction, propagate the first renewal failure through `check_active`, and stop scheduling renewals when the context exits. A stop request interrupts the wait and requests cancellation of an active renewal via its scoped handle before joining. Retain the thread until it exits; do not silently detach it or claim a hard join deadline from server timeouts. Network failure can outlive a server-side deadline. Ordinary long validation does not inherit the heartbeat's short timeout; its operation owns an explicit deadline/cancellation policy.

### Useful operator report

Add `DatabaseDiagnostic(observed_at, application_name, lifecycle, pool_stats, failure)` to the existing CLI/report path for the invocation that owns the Store. Its shared collector receives that live Store and optional current `DatabaseFailure`; it does not open another pool to diagnose the first one. Include observed lifecycle (open/closed), gauges/counters returned by `get_stats()`, and that invocation's failure context. Commands without a managed Store report pool statistics unavailable. Human and JSON failure reporting use this same bounded value; retained historical logs remain separate and no last-error registry is added. Select non-destructive `get_stats()` for on-demand reports; leave `pop_stats()` to a single explicitly selected interval consumer if one exists. Report unavailable keys as unavailable, never zero. `usage_ms` does not represent ordinary Core checkout duration in this manual `getconn` integration. Do not create a timing subsystem merely to populate that field.

Copy the selected `Diagnostic` fields inside `add_notice_handler` callback lifetime: SQLSTATE, primary message, constraint/schema/table/column and hint when present. Avoid internal query/context payloads by default. Notices and pool counters never establish task success. Use existing report/logging conventions; do not import unfinished logging-series work. [Server messages](https://www.psycopg.org/psycopg3/docs/advanced/async.html#server-messages) and [pool statistics](https://www.psycopg.org/psycopg3/docs/advanced/pool.html#pool-stats) are the source routes.

### Package delivery and closure

PG-02 first delivers the shared observation plus publication phase transitions and refusal consumers. It can be checked before new export services exist. PG-05 then moves current store settings, claim renewal, existing long operations and reader owners onto the cancellation/settlement scope. New PG-06/10 consumers adopt the same semantics as they are implemented. No package closes merely because a helper exists.

Run actual pressure/timeout/closed-pool cases, slow query and active COPY cancellation, early iteration abandonment, cancellation-versus-return race and renewal stop with independent native observations. A subsequent borrower must execute a clean transaction without receiving the earlier operation's late cancellation. Cover rollback failure and absent diagnostics. Large output must not require retaining whole result batches merely for cleanup. Keep the standard's FP-04/05/07 distinction between semantic effect knowledge, physical resource state and credible execution fit; neither native pooling nor application outcome typing replaces the other.
