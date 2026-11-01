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

Expose queue admission (`max_waiting`) and acquisition deadlines through the existing database/runtime settings when needed by simultaneous analytical capture, append and heartbeat operations. Pick defaults from actual concurrency in PG-00 rather than multiplying limits independently at each layer. Do not add another queue around the native pool. Session adaptation, prepared statements and temporary state must have a declared reset/reuse boundary; indiscriminate resets can discard useful preparation.

Long database operations retain a cancellation handle at their actual owner. Use Psycopg `cancel_safe(timeout=...)` for Psycopg work and ADBC cancellation for its own statements/connections; neither cancels another driver's session. Request cancellation, observe actual completion, close/drain cursor/reader, then rollback or resolve uncertain commit before return. A pool close does not settle a borrower. Give the claim-renewal operation an effective statement/acquisition deadline so joining its worker does not depend on an indefinitely blocked query. Do not invent a hard total shutdown promise unless it is actually established.

Use native `get_stats`/`pop_stats` and `psycopg.pool` logging for demanded diagnostics, with one consumer of destructive counter reads. Manual `getconn` borrowers are outside `pool.connection()` usage timing. Add timing at the borrower only if an operator question requires that missing observation. Copy selected Psycopg `Diagnostic` fields inside notice callbacks; report SQLSTATE, constraint/table/column and hint where available. Structured ADBC fields may be incomplete. Unknown does not become zero.

Deliver one operator-visible diagnostic result through the existing database CLI/report conventions, including actual failure cause and meaningful pool state; use existing application logging interfaces rather than importing unrealized logging-plan scope. Optional rotation/wakeups/progress extensions remain deferred at the coordinator.

**Closure:** real concurrent pressure, cancellation during query/COPY, abandoned row/batch iteration, connection reuse after settlement, heartbeat stop, absent diagnostic fields and manual-borrow metric interpretation. Query cancellation does not establish absence of committed effects. Native statistics do not establish task success. Keep typed outcomes and cleanup independently testable without starting inference.

## Library basis and design fit

[Psycopg original §§3–13 and addendum §§1–8](../../libraries/postgresql/psycopg.md), [pool original §§3–11 and addendum A1–A8](../../libraries/postgresql/psycopg-pool.md), and [SQLAlchemy execution/pooling](../../libraries/postgresql/sqlalchemy.md) supply native mechanisms. FP-01/04/05/06 and H4/H21/H23–25 favor delegating inventory while retaining domain effect policy. The explicit phase context removes independent reinterpretation without creating a generic resilience framework.
