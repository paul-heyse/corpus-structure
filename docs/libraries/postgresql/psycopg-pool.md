# psycopg-pool 3.3.3 — Comprehensive Python Library Capability Reference

Research date: October 20, 2026 | Target: psycopg-pool 3.3.3 (latest stable release)

Package: `psycopg-pool` Import namespace: `psycopg_pool` Ecosystem: Psycopg 3 / PostgreSQL / Python Requirements: Python 3.10+, Psycopg 3 License: LGPL-3.0-only

Primary sources:

- [Official connection pooling guide](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com)
- [Complete pool API reference](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com)
- [Pool release notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com)
- [Upstream source repository](https://github.com/psycopg/psycopg/tree/master/psycopg_pool?utm_source=chatgpt.com)
- [PyPI distribution and release history](https://pypi.org/project/psycopg-pool/?utm_source=chatgpt.com)

Version 3.3.3 was released September 22, 2026. The published documentation currently reflects ongoing development in parts, so this reference distinguishes capabilities available in 3.3.3 from changes documented for the unreleased 3.3.4. The `psycopg-pool` package has an independent release cycle from the core `psycopg` distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



## 1. Purpose and architectural model

`psycopg-pool` is the connection-pooling component of the Psycopg 3 PostgreSQL adapter. It manages the creation, allocation, reuse, validation, recovery, and retirement of database connections for synchronous and asynchronous Python applications.

Its significance extends beyond avoiding the overhead of repeated PostgreSQL connection establishment. It provides an integrated mechanism for regulating database concurrency, managing connection lifecycles, controlling request admission, recovering from connection failures, and observing database-resource pressure.

The library operates at the DBAPI/driver connection layer. It does not execute relational queries on behalf of callers, manage application object identity, provide ORM facilities, or replace a database-side connection proxy.

### 1.1 The four pool implementations

| Implementation            | Connection behavior                                                 | Principal role                                            |
| ------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------- |
| `ConnectionPool`          | Retains and reuses synchronous `psycopg.Connection` instances       | Threaded and synchronous workloads                        |
| `AsyncConnectionPool`     | Retains and reuses asynchronous `psycopg.AsyncConnection` instances | `asyncio` applications and concurrent tasks               |
| `NullConnectionPool`      | Creates connections on demand without retaining idle connections    | Connection admission control without persistent reuse     |
| `AsyncNullConnectionPool` | Async equivalent of the null pool                                   | Async admission control with no idle connection inventory |

The distinction between regular and null pools is particularly important. A null pool is not merely the absence of pooling infrastructure: it preserves the pool abstraction, configurable concurrency limits, request queues, timeouts, connection customization, and instrumentation while changing connection-retention behavior.

All four implementations support a common operational approach, allowing a program to change its connection-management strategy without substantially changing its database-access interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



### 1.2 Capability map

| Capability family        | Native mechanisms                                              | Architectural value                                                                       |
| ------------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Connection reuse         | Minimum/maximum pool sizes, idle inventory                     | Reduces repeated connection establishment                                                 |
| Concurrency control      | Checkout coordination, bounded capacity, waiting queue         | Regulates PostgreSQL resource consumption                                                 |
| Asynchronous execution   | Async pools and background tasks                               | Supports high-concurrency async services                                                  |
| Connection lifecycle     | Configuration, checkout validation, reset, retirement          | Centralizes connection management                                                         |
| Failure recovery         | Reconnection, exponential backoff, replacement                 | Handles transient loss of connections                                                     |
| Runtime reconfiguration  | `resize()`, `drain()`, dynamic connection parameters           | Changes capacity and connection configuration without rebuilding application abstractions |
| Admission control        | `timeout`, `max_waiting`, pool exceptions                      | Makes overload behavior explicit                                                          |
| Operational visibility   | `get_stats()`, `pop_stats()`, pool logging                     | Exposes contention, utilization, and failure signals                                      |
| External pooling         | Null pools, integration with PgBouncer                         | Supports layered pooling arrangements                                                     |
| Framework integration    | `close_returns`, SQLAlchemy connection creators                | Allows one pool to manage connections shared with higher-level abstractions               |
| Typing and customization | Generic connection types, custom connection classes, callbacks | Preserves typed driver extensions through the pool                                        |

The remainder of this reference examines the mechanisms, their interactions, and the semantic distinctions that matter when selecting or combining them.

## 2. Installation, dependencies, and execution model

The supported installation paths are:

```
# Psycopg with its connection-pooling component
pip install "psycopg[pool]"

# Include Psycopg's binary implementation
pip install "psycopg[binary,pool]"

# Install the pool distribution independently
pip install psycopg-pool
```

The separate `psycopg-pool` distribution depends directly on `typing-extensions >= 4.6`, while the pool implementations operate on Psycopg connection objects and therefore require the core driver at runtime.

The pool itself is implemented in Python. It does not supply a separate PostgreSQL wire-protocol implementation or a dedicated C extension. Driver-level implementation choices, including Psycopg's pure-Python, binary, and locally compiled C implementations, remain responsibilities of the core Psycopg distribution.

A useful architectural distinction: `psycopg-pool` manages when and how many PostgreSQL connections exist and how they are borrowed. Psycopg manages what happens over each connection, including SQL execution, adaptation, transactions, COPY, pipeline mode, and result processing.

Source: [Psycopg installation documentation](https://www.psycopg.org/psycopg3/docs/basic/install.html?utm_source=chatgpt.com) and [3.3.3 package metadata](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/pyproject.toml?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 2.1 Background workers versus client execution

A standard pool has two distinct execution paths.

Standard pool lifecycle

Conceptual illustration; individual operations can be asynchronous and connection handoff depends on availability and callbacks.

For regular pools, connection creation and much of the maintenance work occur in background workers. This decouples most establishment and cleanup work from the requesting thread or task. A caller receives an already prepared connection when one is available, or waits for one to become available.

The default `num_workers=3` controls the number of background maintenance workers. Synchronous pools use worker threads; asynchronous pools use asynchronous worker tasks.

Workers handle connection creation, failed-connection replacement, and maintenance such as custom reset processing. Per-checkout connection checks, when configured, contribute directly to acquisition latency.

This architecture provides the opportunity to overlap PostgreSQL connection establishment with application activity. It does not make connection creation instantaneous or eliminate contention when all connections are checked out.

Source: [Connection lifecycle](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#connections-life-cycle).

## 3. Connection ownership, borrowing, and transaction semantics

### 3.1 Context-managed checkout

The preferred interface is `pool.connection()`, which combines connection acquisition, a transaction-aware context, and deterministic return.

```
from psycopg_pool import ConnectionPoolwith ConnectionPool(    conninfo="postgresql://localhost/example",    min_size=2,    max_size=8,    open=False,) as pool:    pool.wait(timeout=10)    with pool.connection(timeout=5) as conn:        conn.execute(            "INSERT INTO events (kind) VALUES (%s)",            ("example",),        )
```

The database connection returned by the inner context is a normal Psycopg `Connection` instance, not a reduced-purpose pool proxy.

On normal context exit, an open transaction is committed. On exceptional exit, it is rolled back. The connection is then returned for reuse, subject to its health and lifecycle state.

Consequently, pool checkout is also a natural unit-of-work boundary for database operations whose transaction lifetime should match the borrow lifetime.

This can eliminate bespoke code for acquiring a connection, explicitly committing or rolling back, returning it, and replacing a connection that is no longer reusable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 3.2 Explicit ownership with `getconn()` and `putconn()`

The lower-level interface separates allocation and release:

```
conn = pool.getconn()try:    conn.execute("SELECT 1")finally:    pool.putconn(conn)
```

Both operations have asynchronous counterparts.

This is useful for integration with abstractions that require an explicitly acquired connection and control its lifetime themselves.

The distinction from `pool.connection()` is material: `getconn()` does not establish a context-managed transaction boundary. The caller or higher-level integration must account for transaction completion and connection return.

A forgotten `putconn()` holds one of the pool's capacity slots indefinitely until corrected by external intervention. The documentation explicitly recommends context management where possible.

### 3.3 Session lifetime is not borrow lifetime

A regular pool reuses the same underlying PostgreSQL session across successive borrowers. Transaction cleanup does not imply that all session state has been reset.

For example, a reused session may retain connection-level configuration, prepared statements, session-scoped settings, temporary database objects, or other state that survives transaction completion.

The practical distinction is:

| State or responsibility                        | Behavior                                                      |
| ---------------------------------------------- | ------------------------------------------------------------- |
| Active transaction on successful context exit  | Committed                                                     |
| Active transaction on exceptional context exit | Rolled back                                                   |
| Broken connection                              | Discarded and replaced                                        |
| Reusable connection                            | Returned to pool                                              |
| Persistent session state                       | Not automatically guaranteed to return to PostgreSQL defaults |
| Application-specific cleanup                   | Can be implemented using `reset`                              |
| Configuration for new connections              | Can be implemented using `configure`                          |

This matters especially when reusing connections across logically isolated operations. A pool provides connection reuse and transaction hygiene, but not complete session-state isolation by default.

Source: [Pool API: context behavior, configuration and reset](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com).

### 3.4 Synchronous versus asynchronous borrowing

For asynchronous code:

```
from psycopg_pool import AsyncConnectionPoolasync with AsyncConnectionPool(    conninfo="postgresql://localhost/example",    min_size=2,    max_size=8,    open=False,) as pool:    await pool.wait()    async with pool.connection() as conn:        await conn.execute("SELECT 1")
```

`AsyncConnectionPool` provides the same essential capabilities as the synchronous version while using `asyncio`-compatible acquisition, release, initialization, and maintenance.

Psycopg allows multiple asynchronous tasks to use a connection, but operations on the same connection are serialized and share a PostgreSQL session and transaction state. Multiple connections allow concurrent database operations to proceed independently.

Therefore the useful resource abstraction is generally a bounded collection of independent PostgreSQL sessions, rather than unlimited concurrent cursors multiplexed over one connection.

Connections are not safe to share across processes. In prefork or multiprocess environments, the connections should be established after worker processes are created. Likewise, asynchronous pool ownership should align with the lifetime of its event loop.

Sources: [Psycopg concurrent operations](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com) and [AsyncConnectionPool API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com#the-asyncconnectionpool-class).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 4. Pool sizing, capacity management, and admission control

Connection pooling introduces two related but distinct controls: the number of concurrent database sessions, and the number of client operations permitted to wait for those sessions.

These are governed by different parameters.

### 4.1 Fixed-size and elastic pools

The regular pool's principal sizing parameters are:

| Parameter      | Default        | Meaning                                             |
| -------------- | -------------- | --------------------------------------------------- |
| `min_size`     | `4`            | Target persistent connection inventory              |
| `max_size`     | `None`         | Maximum inventory; `None` means fixed at `min_size` |
| `max_idle`     | `600` seconds  | Idle time before excess connections are retired     |
| `max_lifetime` | `3600` seconds | Maximum intended connection lifetime                |
| `num_workers`  | `3`            | Background maintenance workers                      |

A fixed pool (`max_size=None` or `max_size=min_size`) maintains a persistent target inventory and does not grow in response to demand.

An elastic pool (`max_size > min_size`) can grow as concurrent demand increases and shrink back toward `min_size` when additional connections become unnecessary.

Illustrative capacity of an elastic pool

Concurrent connection requests

## 5

Checked out

## 5

Available

## 0

Waiting

## 0

Borrowed

Retained idle

Growth capacity

Simplified steady-state model with min_size=3 and max_size=8. Actual growth is asynchronous and may lag demand; this does not model connection creation time, checkout checks, or timed-out requests.

A regular pool attempts to replenish connections below `min_size`, including after broken connections are removed.

When demand increases, additional connections are established by background workers rather than by the client requesting a connection. A client can receive a previously borrowed connection before a newly requested connection finishes opening.

When an elastic pool contracts, it retires excess connections gradually after `max_idle`. It does not normally close an excess connection immediately upon each return.

Sources: [Sizing and elasticity](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#pool-connection-and-sizing), [constructor parameters](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com#the-connectionpool-class).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 4.2 Waiting queues and bounded admission

When no prepared connection is available, the pool queues a requesting client.

| Parameter                 | Default           | Behavior                                              |
| ------------------------- | ----------------- | ----------------------------------------------------- |
| `timeout`                 | `30.0` seconds    | Default maximum time to obtain a connection           |
| `max_waiting`             | `0`               | Maximum queued requests; `0` means unlimited          |
| `connection(timeout=...)` | Per-call override | Different acquisition deadline for one borrow         |
| `getconn(timeout=...)`    | Per-call override | Acquisition deadline for manually borrowed connection |

Three public exceptions distinguish failure conditions:

| Exception         | Meaning                                                                    |
| ----------------- | -------------------------------------------------------------------------- |
| `PoolTimeout`     | No connection was obtained within the acquisition deadline                 |
| `TooManyRequests` | The pool's waiting queue has reached `max_waiting`                         |
| `PoolClosed`      | A connection was requested after closure or while the pool was unavailable |

All three derive from Psycopg's `OperationalError`.

This is a meaningful alternative to implementing custom semaphores and queues around raw database connections. The pool combines the capacity limit, queuing, and connection lifecycle in one abstraction.

It is also important not to confuse acquisition with execution. `timeout` is a connection-acquisition timeout, not a SQL query timeout, PostgreSQL statement timeout, overall request deadline, or guarantee of execution cancellation.

Source: [Pool exceptions and connection acquisition](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com#pool-exceptions).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 4.3 Operational implications of capacity settings

Several distinctions materially affect performance and reliability.

The pool's upper bound is per pool instance. If multiple application processes each construct a pool with `max_size=10`, those instances do not coordinate a global database connection limit. Aggregate client connection capacity can approach the sum of all those limits.

Queue capacity is separate from database capacity. Even a small fixed connection pool can admit a large number of waiting client requests if `max_waiting=0`. A finite queue limit makes overload rejection explicit instead of allowing an arbitrary amount of pending work.

Connection demand is not equivalent to useful database parallelism. Increasing `max_size` may reduce waiting but also increase database memory consumption, active transactions, lock contention, and scheduling pressure. The correct limit depends on query characteristics and actual concurrency.

Holding connections during unrelated work reduces effective capacity. A database connection retained while a client performs CPU computation, network I/O, or other long operations remains unavailable to waiting clients.

The most useful sizing signals are therefore acquisition latency, queue depth, connection utilization, checkout duration, and PostgreSQL-side resource utilization—not simply the number of requests handled by an application.

## 5. Connection lifecycle customization

The callback system is one of the most valuable ways to centralize behavior that would otherwise be scattered throughout database-access code.

Three callbacks act at distinct stages of connection reuse.

| Callback          | When invoked                            | Principal responsibility               |
| ----------------- | --------------------------------------- | -------------------------------------- |
| `configure(conn)` | Once after creating a new connection    | Establish connection-level behavior    |
| `check(conn)`     | Before handing a connection to a client | Validate that it is usable             |
| `reset(conn)`     | After a connection has been returned    | Remove unwanted reusable session state |

All are optional. Regular synchronous pools use synchronous callbacks; async pools use awaitable callbacks.

### 5.1 `configure`: centralizing connection setup

`configure` runs when a new connection is created, including connections created after failures or as part of pool growth.

It provides an appropriate place for operations such as configuring adapters, custom connection behavior, or connection-specific session settings.

For example:

```
def configure(conn):    conn.autocommit = True    conn.execute("SET application_name = 'example-worker'")
```

This callback is illustrative; application names and configuration policies depend on the caller.

A critical constraint is that `configure` must leave the connection in PostgreSQL's idle transaction state. If it executes SQL that starts a transaction, it must commit or roll it back before returning.

The 3.3.3 implementation explicitly verifies this state and rejects a connection left in an active transaction by `configure`.

This enables connection setup to be expressed once for the pool rather than repeated at every query call site.

Source: [3.3.3 connection creation implementation](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 5.2 `check`: validating before checkout

By default, the regular pool does not actively probe every idle connection.

A PostgreSQL restart, server-side session termination, or network disruption can therefore leave a connection apparently available in the pool even though it no longer works.

The `check` callback addresses this problem. A supplied callback is invoked each time a connection is acquired. If it raises an exception, the pool attempts to obtain another usable connection rather than passing the rejected one to the caller.

Psycopg supplies a built-in callback:

```
pool = ConnectionPool(    conninfo="postgresql://localhost/example",    check=ConnectionPool.check_connection,    open=False,)
```

`check_connection()` is not merely an in-memory connection-status inspection. The 3.3.3 implementation issues a lightweight operation against PostgreSQL to test connectivity and avoids leaving a transaction open.

The tradeoff is straightforward: verification can reduce the chance of handing out a previously disconnected connection, but it adds network work to checkout. It also cannot guarantee that a connection will remain healthy after the check completes.

Source: [Connection quality](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#connection-quality) and [3.3.3 check implementation](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 5.3 `reset`: enforcing reusable session state

`reset` is invoked after a borrowed connection returns to the pool. It is intended for cleanup beyond basic transaction completion.

The pool guarantees that the callback receives the connection in an idle transaction state, and requires that it remain idle when the callback returns.

For instance, a reset function can restore selected session settings:

```
def reset(conn):    conn.execute("RESET application_name")    conn.commit()
```

This can be useful when borrowers modify persistent PostgreSQL session settings, but it has several subtleties.

First, the library already performs transaction cleanup. A custom reset function need not reproduce the entire default rollback mechanism.

Second, PostgreSQL session cleanup is not semantically uniform. Settings, temporary tables, advisory locks, prepared statements, and other session resources may require different operations.

Third, more aggressive cleanup can invalidate session-level optimizations, including prepared statements that are deliberately retained for subsequent queries.

Finally, the callback must not leave a transaction open. If it fails or leaves the connection in an unsuitable state, the connection is discarded rather than returned as reusable.

The architectural benefit is a centralized session hygiene policy, with substantially less risk of independent query paths implementing inconsistent cleanup behavior.

Sources: [Pool reset API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com) and [3.3.3 transaction-state and reset handling](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 6. Null pools: connection admission without persistent retention

The `NullConnectionPool` and `AsyncNullConnectionPool` classes are architecturally distinct from standard pools.

They create connections on demand and ordinarily close them when returned, instead of keeping idle connections available for later reuse.

They nevertheless retain the higher-level connection-management interface and many of the control mechanisms of the regular pool.

### 6.1 Why a null pool is more than a direct `connect()` wrapper

A direct call to `psycopg.connect()` creates a connection without coordinating the number of other clients trying to connect concurrently.

A bounded null pool can perform that coordination.

```
from psycopg_pool import NullConnectionPoolpool = NullConnectionPool(    conninfo="postgresql://localhost/example",    max_size=8,    max_waiting=32,    timeout=5.0,    open=False,)
```

With this configuration, the pool can regulate the number of simultaneously checked-out connections and queue additional requests.

When a borrower returns a connection, the null pool can hand that same connection to an already waiting client after transaction cleanup and any applicable reset. If there is no waiting client, it closes the connection.

This handoff is an easily overlooked capability: null pooling does not necessarily imply a new PostgreSQL connection for every request under continuous contention. It avoids retaining idle connections, rather than forbidding all reuse.

### 6.2 Important differences from a regular pool

| Behavior                                     | Regular pool                            | Null pool                                                       |
| -------------------------------------------- | --------------------------------------- | --------------------------------------------------------------- |
| Minimum retained connections                 | Configurable, default 4                 | Always 0                                                        |
| Create connections in advance                | Yes                                     | No                                                              |
| Reuse idle connections                       | Yes                                     | No                                                              |
| Reuse returned connection for queued request | Yes                                     | Yes                                                             |
| Limit concurrent connections                 | Yes                                     | Yes, if `max_size > 0`                                          |
| Default `max_size=None`                      | Fixed at `min_size`                     | No upper limit                                                  |
| Connection establishment                     | Primarily background workers            | Ordinarily paid by requesting client                            |
| `reset` callback                             | Applied on returned reusable connection | Applied only when handing returned connection to waiting client |
| `max_idle`                                   | Controls excess idle retirement         | Ignored                                                         |
| `check()`                                    | Examines idle inventory                 | No-op                                                           |
| `wait()`                                     | Waits for minimum inventory             | Tests connectivity without retaining connection                 |

Two subtleties deserve emphasis.

First, `max_size=None` means very different things for a null pool and a regular pool. For a null pool, it does not impose a concurrency bound. An unbounded null pool therefore does not, by itself, protect PostgreSQL from excessive simultaneous client connections.

Second, a null pool's low idle resource consumption is purchased at the cost of more connection creation and authentication work. It is particularly relevant when a downstream component provides connection reuse, or when holding client-side idle sessions is undesirable.

### 6.3 Relationship to PgBouncer

A null pool can serve as a client-side admission-control layer in front of PgBouncer.

In such an arrangement, psycopg-pool can limit application concurrency and provide a consistent API, while PgBouncer manages database-side connection reuse.

An important distinction is that closing a Psycopg client connection to PgBouncer does not necessarily close the corresponding reusable PostgreSQL server connection.

This separation allows application-side connection management and database-side connection multiplexing to be treated independently.

However, using a null pool is not automatically more efficient than retaining a small number of client connections to PgBouncer. Frequent client reconnection still entails setup and authentication work. Which approach is preferable depends on deployment topology and connection demand.

Sources: [Null connection pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#null-connection-pools) and [NullConnectionPool API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com#null-connection-pools).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 7. Failure recovery and connection health management

Connection pooling must handle a fundamental failure mode: a connection can become unusable independently of the Python object that refers to it.

`psycopg-pool` includes several mechanisms for detecting failures, replacing connections, and retrying establishment.

### 7.1 Replacement of broken connections

Connections can be discarded when they are discovered to be broken during borrowing, when returned in a broken state, or when checked explicitly.

For standard pools, replacement work is scheduled through background maintenance workers.

The pool also tries to replenish its inventory when connections are lost below the configured minimum.

This eliminates the need for each borrowing client to contain custom connection-replacement code.

It does not automatically retry an application SQL statement or restore a transaction interrupted by a failure. Those are separate responsibilities because repeating SQL can have correctness implications, especially if the outcome of a previous operation is uncertain.

### 7.2 Reconnection backoff and failure callbacks

Connection creation can fail because PostgreSQL is temporarily unreachable, credentials are invalid, the server is restarting, or the connection limit has been reached.

The pool supports a retry mechanism using exponential backoff with randomization to avoid synchronized reconnection storms.

| Mechanism           | Default     | Purpose                                                     |
| ------------------- | ----------- | ----------------------------------------------------------- |
| `reconnect_timeout` | 300 seconds | Retry window for failed background connection establishment |
| `reconnect_failed`  | `None`      | Callback after the retry window is exhausted                |
| `num_workers`       | 3           | Workers available for connection and maintenance tasks      |

After the reconnection window is exhausted, the regular pool invokes `reconnect_failed`, if provided. In the absence of a callback, it can initiate another reconnection cycle where minimum inventory still needs replenishment.

The callback can provide an operational escalation point—for example, recording an incident, updating a readiness condition, or requesting a supervised restart.

Async pools additionally support asynchronous `reconnect_failed` callbacks.

The important semantic boundary is that reconnection is recovery of the pool's connection inventory, not transparent recovery of arbitrary in-flight database operations.

Source: [Pool reconnection behavior](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#pool-connection-and-sizing).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 7.3 Timeouts serve different purposes

| Timeout                         | Scope                                            |
| ------------------------------- | ------------------------------------------------ |
| `pool.timeout`                  | Waiting to acquire a connection                  |
| Per-checkout `timeout`          | Override of acquisition deadline                 |
| `pool.wait(timeout)`            | Waiting for pool initialization/readiness        |
| `reconnect_timeout`             | Background connection-establishment retry window |
| Psycopg/libpq `connect_timeout` | Establishing one underlying database connection  |
| PostgreSQL `statement_timeout`  | Server-side execution duration                   |

These controls are complementary, not interchangeable.

For example, increasing the pool's acquisition timeout does not cause a broken PostgreSQL connection to recover more quickly. Similarly, changing `reconnect_timeout` does not prevent a client from reaching its own earlier acquisition deadline.

A resilient system can therefore distinguish connection establishment failure, capacity exhaustion, queue saturation, and slow query execution rather than treating all four as generic database timeouts.

### 7.4 Pool-wide health inspection

`check()` explicitly inspects the connections currently retained in a regular pool.

```
pool.check()
```

For each available connection, the pool checks whether it is usable, returns working connections to inventory, and discards or replaces unusable ones.

This differs from the constructor's `check` callback:

| Mechanism               | Invocation model                                                            |
| ----------------------- | --------------------------------------------------------------------------- |
| Constructor `check=...` | Checks each connection as it is borrowed                                    |
| `pool.check()`          | Checks currently retained idle connections when explicitly invoked          |
| `pool.wait()`           | Checks whether initialization has reached its required connection inventory |

The pool does not continuously probe all idle connections by default. A periodic explicit check is possible, but it adds database activity and cannot examine connections currently borrowed by clients.

`NullConnectionPool.check()` is a no-op because it has no retained idle inventory.

A noteworthy version-specific caveat is discussed in Section 12: the upcoming 3.3.4 release contains a fix for unintended pool growth during `check()`.

Source: [Pool health API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 7.5 Cancellation and exception safety

Asynchronous connection management is particularly sensitive to cancellation while acquiring, checking, cleaning up, or returning connections.

The 3.3 release series includes fixes to preserve pool accounting and propagate cancellation correctly, including changes in 3.3.1 and 3.3.2.

The 3.3.3 implementation distinguishes normal connection-check failures from exceptions such as task cancellation. Cancellation propagates rather than being silently treated as an ordinary failed health check, while the pool arranges the necessary connection return or cleanup.

This is important for async frameworks in which requests can be cancelled by clients, deadlines, or task-group shutdown.

It does not eliminate the need for application-level handling of uncertain SQL outcomes after cancellation.

Sources: [3.3 release notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com), [3.3.3 checkout implementation](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com), and [Psycopg async cancellation semantics](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



## 8. Runtime pool operations and reconfiguration

A persistent connection pool has operational responsibilities beyond normal checkout and return.

`psycopg-pool` exposes mechanisms to initialize connections deterministically, change capacity, replace the connection inventory, and terminate service cleanly.

### 8.1 Opening and readiness

A pool can be opened on construction or explicitly.

```
pool = ConnectionPool(    conninfo="postgresql://localhost/example",    open=False,)pool.open(wait=True, timeout=15)
```

`open(wait=False)` starts the pool and allows background workers to establish connections without requiring all minimum connections to be ready before returning.

`open(wait=True)` waits for the pool to reach its minimum inventory or raises `PoolTimeout`.

The separate `wait()` method provides the same readiness synchronization after an already opened pool:

```
pool.open()pool.wait(timeout=15)
```

If readiness is not achieved before `wait()` times out, the pool is closed and `PoolTimeout` is raised.

This distinguishes pool object initialization from database connectivity readiness—a valuable separation for application and service lifecycle management.

### 8.2 Explicit asynchronous startup

For asynchronous pools, explicit opening is particularly important:

```
pool = AsyncConnectionPool(    conninfo="postgresql://localhost/example",    open=False,)await pool.open(wait=True, timeout=15)
```

In version 3.3.3, `open=True` remains the documented constructor default, but implicit opening is deprecated for async pools. A future version is expected to change the default and reject constructor-based async opening.

Specifying `open=False` and opening within the correct running event loop avoids relying on this deprecated behavior.

Source: [Pool startup and opening APIs](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 8.3 Runtime resizing

`resize(min_size, max_size=None)` changes a standard pool's configured capacity without requiring callers to replace the pool object.

```
pool.resize(min_size=4, max_size=16)
```

This changes the pool's maintenance and admission targets. Additional connections can be created as needed, while excess connections are retired according to the pool's lifecycle.

A null pool also exposes `resize()`, but its `min_size` must remain zero; only its concurrency ceiling can change.

This native capability can avoid custom reconstruction and coordination logic when connection budgets need to change during an application's lifetime.

### 8.4 `drain()`: rotating the connection inventory

Introduced in version 3.3.0, `drain()` is particularly significant.

```
pool.drain()
```

It removes currently idle connections and causes replacement connections to be created. Connections that are currently checked out are not forcibly interrupted; instead, they are retired when eventually returned.

This gives the pool an explicit connection-generation replacement mechanism.

Examples of operations it can support include refreshing connections after adapter configuration changes, updating connection-level configuration, and replacing connections established with old credentials.

It is important to distinguish `drain()` from `close()`.

| Operation  | Effect                                                 |
| ---------- | ------------------------------------------------------ |
| `check()`  | Verify available connections and replace unusable ones |
| `drain()`  | Replace the current generation of connections          |
| `resize()` | Change capacity targets                                |
| `close()`  | Shut down the pool                                     |

`drain()` is not an immediate revocation mechanism for already borrowed connections, and replacement work still requires successful connection establishment.

The asynchronous pool provides an awaitable `drain()` counterpart.

Source: [Pool API — drain](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com), [3.3.3 tagged implementation](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+2



### 8.5 Dynamic connection parameters

Version 3.3 introduced support for making both `conninfo` and `kwargs` callable.

Instead of supplying a single immutable connection string, the caller can provide a function evaluated whenever the pool needs to create a new connection.

```
def current_conninfo() -> str:    return obtain_current_connection_string()pool = ConnectionPool(    conninfo=current_conninfo,    min_size=2,    max_size=8,    open=False,)
```

`obtain_current_connection_string()` is an illustrative application-defined function.

The same mechanism applies to `kwargs`, which can be a callable returning connection keyword arguments.

For async pools, these factories may also be asynchronous.

This provides a native integration point for rotating credentials, retrieving short-lived authentication tokens, updating TLS connection parameters, or changing connection endpoints.

The distinction is important: a callable refreshes parameters when a new connection is created. It does not mutate existing PostgreSQL connections.

Combined with `drain()`, however, it enables a coherent pattern:

Credentials or endpoint configuration changes

Connection factory supplies updated parameters

pool.drain() initiates connection replacement

New connections use updated configuration

Existing borrowed connections complete their work and are retired on return.

This combination can remove the need to reconstruct a pool object, distribute a replacement object to every caller, and coordinate a wholesale shutdown for ordinary connection configuration changes.

It does not itself provide credential discovery, secret storage, endpoint failover policy, or credential revocation. Those remain responsibilities of the corresponding external systems.

Source: [3.3.0 release notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com) and [ConnectionPool constructor](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 8.6 Closing and teardown

`close(timeout=5.0)` stops the pool from serving new clients. Pending and subsequent attempts to acquire a connection fail with `PoolClosed`.

Connections already borrowed are not immediately forcibly closed by the pool; they are disposed of upon return.

Calling `open()` on an already open pool is safe, but a pool that has been closed cannot be reopened in the documented 3.3.3 lifecycle.

Context-managed pool creation provides deterministic teardown. For applications where the pool survives across many request handlers, framework startup and shutdown hooks provide the appropriate ownership boundary.

Source: [Pool open/close behavior](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



## 9. Observability, instrumentation, and pool diagnostics

`psycopg-pool` provides two complementary forms of operational insight: structured statistics and lifecycle logging.

The structured statistics are especially useful because they expose the distinction between database connection scarcity, slow connection establishment, and long connection occupancy.

### 9.1 Built-in statistics

Both `get_stats()` and `pop_stats()` return dictionaries of integer measurements:

```
stats = pool.get_stats()# Retrieve statistics and reset accumulated counters.interval_stats = pool.pop_stats()
```

`get_stats()` reads statistics without resetting them. `pop_stats()` resets the accumulated counters, making it convenient for interval-based telemetry collection.

The documented metrics fall into four groups.

| Metric               | Interpretation                                                     |
| -------------------- | ------------------------------------------------------------------ |
| `pool_min`           | Current minimum connection target                                  |
| `pool_max`           | Current maximum connection capacity                                |
| `pool_size`          | Connections managed, including those checked out or being prepared |
| `pool_available`     | Connections currently idle and available                           |
| `requests_waiting`   | Clients presently queued for a connection                          |
| `requests_num`       | Total connection requests                                          |
| `requests_queued`    | Requests that could not be served immediately                      |
| `requests_wait_ms`   | Accumulated time spent waiting in the queue                        |
| `requests_errors`    | Failed acquisitions, including timeouts and full-queue errors      |
| `usage_ms`           | Accumulated time connections were borrowed                         |
| `connections_num`    | Database connection-establishment attempts                         |
| `connections_ms`     | Accumulated establishment time                                     |
| `connections_errors` | Failed establishment attempts                                      |
| `connections_lost`   | Connections found unusable by health checks                        |
| `returns_bad`        | Connections returned in a bad state                                |

These metrics are supplied by the pool itself; they do not require external instrumentation of every connection acquisition.

The documentation explicitly cautions that the metric schema is not a rigid, permanent interface. Keys with zero values may be omitted. Consumers should therefore handle absent keys and avoid depending on undocumented fields.

Source: [Official pool statistics reference](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#pool-stats).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 9.2 Deriving performance signals

The statistics are more valuable when interpreted together rather than viewed as isolated counters.

| Derived signal                     | Approximate expression                   | What it reveals                                  |
| ---------------------------------- | ---------------------------------------- | ------------------------------------------------ |
| Queueing incidence                 | `requests_queued / requests_num`         | Fraction of acquisitions experiencing contention |
| Mean queued-request wait           | `requests_wait_ms / requests_queued`     | Queue delay among requests that had to wait      |
| Mean connection-establishment time | `connections_ms / connections_num`       | Cost of opening connections                      |
| Mean checkout duration             | `usage_ms / completed checkout count`    | How long clients occupy connections              |
| Available capacity                 | `pool_available` relative to `pool_size` | Current spare inventory                          |

These are analytical interpretations, not additional built-in metrics. The denominators must be handled carefully, and counters should be compared over consistent observation intervals.

In particular, a mean wait time can conceal a small proportion of extremely slow acquisitions. The native statistics do not provide latency histograms or request-attributed traces. Applications requiring p95/p99 acquisition latency need additional instrumentation around checkout.

Several combinations are diagnostically useful.

High `requests_waiting` with low `pool_available`: clients are competing for limited available capacity. This may reflect insufficient connections, long transactions, excessive time spent holding connections, or database-side execution delays.

High `connections_ms` alongside pool growth: connection establishment is contributing appreciably to latency. Maintaining more prepared connections or investigating authentication/network overhead may change the tradeoff, depending on resource constraints.

High `returns_bad` or `connections_lost`: connections are frequently becoming unusable. The cause may lie in PostgreSQL restarts, server-side timeouts, network disruptions, or incorrect handling of connections.

High `requests_errors` but low `connections_errors`: acquisition failures are occurring without a corresponding increase in PostgreSQL connection-establishment failures. Capacity exhaustion or queue policy may be more relevant than connectivity.

These interpretations are conditional. The pool metrics describe the client-side connection lifecycle; PostgreSQL views such as `pg_stat_activity`, database wait events, and server-side metrics are needed to diagnose what the acquired connections are actually doing.

### 9.3 Logging

The library uses Python's standard `logging` infrastructure, including the logger named `psycopg.pool`.

```
import logginglogging.getLogger("psycopg.pool").setLevel(logging.INFO)
```

The logger can reveal connection requests and returns, maintenance activity, startup, and connection replacement behavior.

A pool can also be assigned a descriptive `name` to distinguish multiple instances in logs; otherwise, the library generates names such as `pool-1`.

However, logging messages are explicitly not a stable programmatic interface. They are better suited to debugging and contextual diagnostics than to metrics extraction through string parsing.

Source: [Pool operations logging](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#pool-operations-logging).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 9.4 Integration with monitoring systems

The statistics are plain Python dictionaries, so they can be adapted to Prometheus, OpenTelemetry-based application instrumentation, or other monitoring systems without modifying the pool's internals.

The library does not itself create a Prometheus exporter, trace database statements, or attach application request identities to individual connection checkouts.

One subtle operational consideration is that `pop_stats()` resets accumulated counters. If several independent consumers call it, each can affect the next consumer's interval. A single metrics collector, or non-resetting `get_stats()` with externally maintained deltas, avoids that coordination problem.

This makes the built-in statistics a useful foundation for observability while leaving telemetry collection, export, aggregation, and alerting to the application or monitoring stack.

## 10. SQLAlchemy integration: one connection manager, two abstraction layers

A major addition in psycopg-pool 3.3 was explicit support for using Psycopg's pool underneath SQLAlchemy.

This is significant because both systems can independently manage PostgreSQL connection reuse.

Without deliberate integration, they may introduce two layers of client-side pooling, making connection capacity, cleanup, and diagnostics harder to reason about.

### 10.1 The `close_returns` contract

Psycopg normally interprets `Connection.close()` as closing the physical connection.

SQLAlchemy's connection-management contract expects closing its checked-out driver connection to release that connection to the pool responsible for it.

`psycopg-pool` 3.3 introduced:

```
close_returns=True
```

When enabled, a borrowed connection's `close()` returns it to the Psycopg pool rather than immediately terminating the underlying PostgreSQL session.

This makes it possible to let SQLAlchemy handle relational operations and transaction abstractions while assigning connection inventory management to psycopg-pool.

### 10.2 Synchronous SQLAlchemy integration

```
from psycopg_pool import ConnectionPoolfrom sqlalchemy import create_enginefrom sqlalchemy.pool import NullPoolpgpool = ConnectionPool(    conninfo="postgresql://localhost/example",    min_size=2,    max_size=8,    close_returns=True,    open=False,)pgpool.open(wait=True)engine = create_engine(    "postgresql+psycopg://",    poolclass=NullPool,    creator=pgpool.getconn,)
```

There are two different `NullPool` concepts in this example:

- `sqlalchemy.pool.NullPool` disables persistent connection retention within SQLAlchemy so that psycopg-pool remains the connection manager.
- `psycopg_pool.NullConnectionPool` is an alternative Psycopg pool implementation that does not retain idle database connections.

They are unrelated classes and serve different architectural roles.

The result is a SQLAlchemy engine that continues to supply SQLAlchemy's SQL, ORM, and transaction facilities, while borrowing actual driver connections from `pgpool`.

### 10.3 Asynchronous SQLAlchemy integration

The async equivalent uses `async_creator`:

```
from psycopg_pool import AsyncConnectionPoolfrom sqlalchemy.ext.asyncio import create_async_enginefrom sqlalchemy.pool import NullPoolpgpool = AsyncConnectionPool(    conninfo="postgresql://localhost/example",    min_size=2,    max_size=8,    close_returns=True,    open=False,)await pgpool.open(wait=True)engine = create_async_engine(    "postgresql+psycopg://",    poolclass=NullPool,    async_creator=pgpool.getconn,)
```

`async_creator` is supported in SQLAlchemy 2.0.16 and later. It accepts an asynchronous callable returning a driver-level async connection.

As in the synchronous case, SQLAlchemy handles the database abstraction while Psycopg manages the connection inventory.

The lifecycles remain distinct. The SQLAlchemy engine must be disposed of appropriately, and the Psycopg pool must be closed separately after users of the engine have finished.

This also makes transaction-reset ownership important. SQLAlchemy may perform its own connection-level cleanup before the connection is returned, while Psycopg's pool still applies its own transaction-state checks and configured reset behavior.

Sources: [Psycopg SQLAlchemy integration](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com#integration-with-sqlalchemy), [SQLAlchemy Psycopg dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html?utm_source=chatgpt.com#module-sqlalchemy.dialects.postgresql.psycopg), and [SQLAlchemy pooling reference](https://docs.sqlalchemy.org/en/20/core/pooling.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+3



### 10.4 Why the integration can matter

Delegating pooling to psycopg-pool can expose mechanisms such as callable connection parameters, `drain()`, elastic pool shrinking, explicit initialization readiness, and its particular connection-health and queueing policies.

It can also eliminate bespoke adapters previously needed to make SQLAlchemy cooperate with Psycopg's connection ownership.

This is not a categorical improvement over SQLAlchemy's native pool implementations. SQLAlchemy already supplies mature pooling, disconnect handling, recycling, events, and instrumentation. Choosing one as the authoritative pool is an architectural tradeoff involving desired lifecycle semantics and which layer should control database resources.

The notable capability is that psycopg-pool 3.3 makes the integration a supported configuration rather than requiring an application-specific connection subclass.

### 10.5 Compatibility with custom connection classes

There is a version-specific detail worth preserving.

In the tagged psycopg-pool 3.3.3 implementation, the behavior of `close_returns=True` also depends on the core Psycopg version.

With core Psycopg older than 3.3, the pool can use a compatibility connection implementation for the standard connection class, but combining `close_returns=True` with a custom `connection_class` is restricted. The tagged implementation raises `TypeError` for that combination.

With the newer core Psycopg functionality, this compatibility restriction is not imposed in the same way.

This is a concrete example of why the versions of `psycopg` and `psycopg-pool` should be treated separately when evaluating an integration.

Source: [Tagged psycopg-pool 3.3.3 connection implementation](https://github.com/psycopg/psycopg/blob/pool-3.3.3/psycopg_pool/psycopg_pool/pool.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 11. Typed connections, customization, and composition with Psycopg

The pool returns actual Psycopg connection objects. Consequently, most capabilities of the core driver remain available without a special pool-specific execution interface.

This is an important design property: connection pooling does not require database operations to be expressed through a separate query abstraction.

### 11.1 Custom connection classes and generic typing

The `connection_class` parameter allows the pool to create subclasses of `psycopg.Connection` or `psycopg.AsyncConnection`.

Pool classes are also generic over the connection type, so static type information can survive checkout.

This became a documented capability in psycopg-pool 3.2.

For example:

```
from psycopg import Connectionfrom psycopg.rows import DictRow, dict_rowfrom psycopg_pool import ConnectionPoolpool = ConnectionPool(    connection_class=Connection[DictRow],    kwargs={"row_factory": dict_row},    open=False,)
```

With this configuration, type checkers can understand that the pool returns connections producing dictionary-shaped rows.

The second argument is important: specifying a generic row type in `connection_class` affects static typing, but the runtime row representation must be configured consistently using `row_factory`.

The same mechanism permits custom connection subclasses that encapsulate specialized connection behavior, while retaining pool-managed creation and ownership.

Source: [Psycopg static typing — generic pool types](https://www.psycopg.org/psycopg3/docs/advanced/typing.html?utm_source=chatgpt.com#generic-pool-types).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 11.2 Centralized adapter and session configuration

Because `configure` receives a genuine Psycopg connection, it can participate in the driver's broader customization mechanisms.

Examples include configuring type adapters, connection defaults, application-specific row handling, and session settings.

This can be preferable to separate wrappers applied independently at every database-access point: the configuration is established when a physical connection enters the pool, and replacement connections are configured through the same mechanism.

The distinction between `configure` and `kwargs` is useful:

- `kwargs` passes arguments to Psycopg's connection factory, including supported connection options.
- `configure` applies logic after the driver connection has been created.
- `reset` handles cleanup before a borrowed connection is reused.

Together, they cover connection construction, post-creation configuration, and return-time hygiene without requiring a custom connection lifecycle implementation.

Source: [Psycopg pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com) and [Psycopg type adaptation](https://www.psycopg.org/psycopg3/docs/advanced/adapt.html?utm_source=chatgpt.com).

### 11.3 Prepared statements and persistent connection reuse

One consequential interaction involves Psycopg's automatic prepared statements.

Psycopg can prepare frequently executed queries and retain their prepared form in a PostgreSQL session. The `prepare_threshold` and `prepared_max` settings govern when statements are prepared and how many are retained.

A regular pool can preserve those session-local prepared statements across multiple borrowers of the same connection.

A null pool, by contrast, ordinarily discards the session after a request when no other client is waiting. That reduces the opportunity to reuse statements prepared in the previous session.

Similarly, aggressive session resets, regular connection draining, and short connection lifetimes can reduce the benefits of retaining prepared statements.

These are interactions between the pool's connection lifecycle and Psycopg's prepared-statement implementation; preparation itself is not a feature implemented by psycopg-pool.

Source: [Psycopg prepared statements](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 11.4 Prepared statements behind PgBouncer

Adding PgBouncer introduces another session-identity boundary.

Under transaction pooling, a client connection may be assigned different PostgreSQL server sessions for different transactions. Features that assume stable server-session identity therefore require special consideration.

Current Psycopg documentation specifies support for protocol-level prepared statements through PgBouncer under these conditions:

| Requirement                                             | Documented condition                          |
| ------------------------------------------------------- | --------------------------------------------- |
| PgBouncer version                                       | 1.22 or newer                                 |
| PgBouncer configuration                                 | `max_prepared_statements > 0`                 |
| Client libpq for normal prepared-statement deallocation | PostgreSQL 17 or newer                        |
| Alternative for older libpq                             | Set `prepared_max=None` to avoid deallocation |

Where the relevant middleware does not support prepared statements, Psycopg can disable them by setting `prepare_threshold=None`.

It is therefore incorrect to assume either that prepared statements are universally incompatible with PgBouncer or that enabling them is universally safe. The compatibility depends on the middleware mode, configuration, and client-library behavior.

Sources: [Psycopg and PgBouncer prepared statements](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html?utm_source=chatgpt.com#using-prepared-statements-with-pgbouncer) and [PgBouncer pooling-mode capabilities](https://www.pgbouncer.org/features.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation

+1



### 11.5 Composition with COPY, pipeline mode, cursors, and transactions

A borrowed connection retains access to core Psycopg facilities such as:

| Psycopg capability                    | Interaction with psycopg-pool                                |
| ------------------------------------- | ------------------------------------------------------------ |
| `COPY FROM` / `COPY TO`               | Uses an acquired connection for bulk data transfer           |
| Pipeline mode                         | Supports pipelined execution within the borrowed connection  |
| Server-side cursors                   | Can stream query results while the connection is held        |
| Row factories                         | Determine the representation of fetched rows                 |
| Type adapters                         | Control Python/PostgreSQL value conversion                   |
| Transaction contexts                  | Define nested or explicit transactional work within a borrow |
| Parameterized SQL and SQL composition | Continue to function through the underlying driver           |

These capabilities can combine with pooling to avoid constructing special database execution wrappers.

However, a long-running `COPY`, server-side cursor, or open transaction occupies a connection for its duration. The pool cannot lend that same independent session to another borrower until it is returned.

Pipeline mode can reduce communication overhead for suitable sequences of operations, but it does not turn one PostgreSQL connection into multiple independent sessions.

A similar distinction applies to persistent `LISTEN/NOTIFY` subscriptions: a long-lived listener may need a dedicated connection rather than continuously occupying capacity intended for short database operations. PgBouncer transaction pooling also does not preserve the session affinity required by `LISTEN`.

The pool's abstraction is therefore especially natural for bounded units of database work, while session-persistent operations deserve explicit lifecycle treatment.

Sources: [Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html?utm_source=chatgpt.com), [pipeline mode](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html?utm_source=chatgpt.com), [concurrent operations](https://www.psycopg.org/psycopg3/docs/advanced/async.html?utm_source=chatgpt.com), and [PgBouncer feature compatibility](https://www.pgbouncer.org/features.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pgbouncer.org\&sz=32)

PgBouncer



## 12. Version-specific capabilities and current limitations

The 3.3 release series is particularly relevant because it expanded the pool beyond its established connection reuse and admission-control responsibilities.

### 12.1 Release history relevant to the architecture

| Version | Consequential change                                                                       |
| ------- | ------------------------------------------------------------------------------------------ |
| 3.2     | Added documented connection-quality and generic typing functionality                       |
| 3.3.0   | Introduced `drain()` for connection replacement                                            |
| 3.3.0   | Added callable `conninfo` and `kwargs`                                                     |
| 3.3.0   | Added `close_returns` for SQLAlchemy interoperability                                      |
| 3.3.1   | Fixed cancellation-related race conditions and synchronous opening coordination            |
| 3.3.2   | Corrected propagation of cancellation and other base exceptions during connection checking |
| 3.3.3   | Fixed synchronous background workers terminating after prolonged inactivity                |

These changes have different architectural significance. The three features introduced in 3.3.0 expand what the pool can do; the following maintenance releases improve lifecycle correctness under concurrency and long-running operation.

Source: [Official psycopg-pool release notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 12.2 Unreleased 3.3.4 fixes are not available in 3.3.3

The upstream release notes already document fixes planned for 3.3.4, but label that version unreleased.

Three are material for users of 3.3.3:

| Issue documented for 3.3.4                                                | Implication for 3.3.3                                                               |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `NullConnectionPool.reconnect_failed` callback accepted but never invoked | Do not depend on this callback for null-pool recovery notifications in 3.3.3        |
| Null-pool connection count can become negative after a failed `wait()`    | Null-pool accounting can be affected by this failure path                           |
| `check()` can unintentionally grow a regular pool                         | Explicit pool health inspection is not necessarily capacity-neutral in this version |

The third issue is particularly relevant where a strict connection budget is important. The documented fix establishes that the 3.3.3 implementation can behave differently from the intended no-growth semantics of `check()`.

These should be treated as known version-specific issues, not capabilities that have already been repaired in the current stable release.

Source: [Unreleased psycopg-pool 3.3.4 notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com#future-releases).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



### 12.3 Other consequential boundaries

There are several limits to what the pool guarantees.

It does not provide global connection coordination. Each process or pool instance has its own capacity and waiting queue. Aggregate limits across hosts or processes need a separate enforcement mechanism or appropriately allocated per-instance budgets.

It cannot guarantee an uninterrupted SQL operation. Health checks, connection replacement, and retrying establishment improve connection availability but cannot prevent an established connection from failing during use.

It does not retry arbitrary transactions safely. An application must distinguish failures before execution, failures during execution, and uncertain commit outcomes. Automatically repeating work may duplicate non-idempotent effects.

It does not provide complete session isolation by default. Persistent session settings or resources can survive return and reuse; the caller must decide what cleanup is necessary.

It does not replace database execution instrumentation. Pool metrics describe acquisition and connection management, not query plans, server execution time, locks, or statement-level resource consumption.

It does not multiplex arbitrary independent SQL operations over a single connection. Concurrent requests for independent PostgreSQL sessions still need enough available physical connections, a suitable external pooling layer, or a workload design that tolerates serialization.

These boundaries are central to evaluating what functionality can genuinely be delegated to psycopg-pool and what belongs to PostgreSQL, Psycopg, higher-level frameworks, or application semantics.

## 13. Architectural combinations and selection tradeoffs

The most valuable capabilities often emerge from combining several native mechanisms rather than evaluating them individually.

| Problem shape                         | Native capability combination                                            | Architectural opportunity                                              |
| ------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| High-volume short database operations | Persistent connections + bounded checkout + context-managed transactions | Avoid repeated establishment and custom borrow/return code             |
| Bursty concurrent demand              | `min_size`, `max_size`, `max_idle`, `max_waiting`, `timeout`             | Elastic capacity and explicit overload policy                          |
| Unreliable database connectivity      | `check`, `check_connection`, reconnection backoff, `reconnect_failed`    | Centralized connection health and replenishment                        |
| Credential or endpoint changes        | Callable `conninfo`/`kwargs` + `drain()`                                 | Replace connection generations without rebuilding the pool abstraction |
| Controlled session reuse              | `configure` + `reset` + transaction-aware checkout                       | Centralize configuration and session cleanup                           |
| Observability and performance tuning  | `get_stats`, `pop_stats`, named pools, logging                           | Diagnose contention and connection lifecycle costs                     |
| Database-side connection multiplexing | Null pool + PgBouncer                                                    | Separate application admission from server-connection reuse            |
| SQLAlchemy-based applications         | `close_returns=True` + SQLAlchemy `NullPool` + connection creator        | Use Psycopg as the authoritative connection manager                    |
| Typed database-access layers          | Generic `connection_class` + consistent row factories                    | Preserve connection and row-type information through checkout          |

These combinations are useful design possibilities, not universal recommendations. The suitability of each depends on the workload's transaction duration, database connection budget, availability requirements, and surrounding infrastructure.

### 13.1 Three distinctions that determine most design choices

Connection reuse versus connection admission. A regular pool does both. A bounded null pool can perform admission control without retaining idle connections. An external proxy can provide a different level of reuse. These mechanisms can be combined, but their independent queues and limits must be understood.

Connection availability versus operation reliability. Background reconnection and checkout validation improve the probability of obtaining a usable connection. Application-level transaction retry, idempotency, and handling uncertain execution outcomes remain separate correctness concerns.

Pool ownership versus database abstraction. A pool owns connection lifecycles. Psycopg owns driver-level execution behavior. SQLAlchemy, when present, owns additional SQL-expression, ORM, and transaction abstractions. Assigning these responsibilities clearly can avoid redundant pooling implementations and duplicated cleanup machinery.

## 14. Overall assessment of the library's capabilities

`psycopg-pool` is a relatively focused library, but it provides substantially more than a reusable collection of PostgreSQL connections.

Its distinctive strengths are the integration of asynchronous and synchronous pooling, connection admission control, background lifecycle management, customizable health and cleanup behavior, built-in operational statistics, and an API compatible across persistent and null-pool strategies.

The 3.3 additions broaden that role further. Callable connection parameters and `drain()` create a native mechanism for refreshing connection generations, while `close_returns` makes it practical to reuse Psycopg's pool beneath SQLAlchemy without maintaining a custom connection-close adapter.

The library can therefore eliminate several classes of bespoke infrastructure: connection creation and replacement loops, checkout queues, basic connection health orchestration, pool-level concurrency limits, common session-setup and reset plumbing, and simple connection-lifecycle telemetry.

Its boundaries are equally important. It is not a query engine, transaction retry framework, distributed connection coordinator, or complete session-isolation mechanism. It is most effective when those responsibilities are kept distinct, and when the interaction between persistent connections, PostgreSQL session state, and higher-level database tooling is understood.

For deeper investigation, the most authoritative starting points remain the [connection pooling guide](https://www.psycopg.org/psycopg3/docs/advanced/pool.html?utm_source=chatgpt.com), [full pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html?utm_source=chatgpt.com), [release notes](https://www.psycopg.org/psycopg3/docs/news_pool.html?utm_source=chatgpt.com), and the [tagged 3.3.3 implementation](https://github.com/psycopg/psycopg/tree/pool-3.3.3/psycopg_pool?utm_source=chatgpt.com).