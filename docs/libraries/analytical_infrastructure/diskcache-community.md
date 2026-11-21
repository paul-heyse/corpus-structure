# diskcache-community — Comprehensive Python Library Overview

Research date: November 20, 2026 | Current stable release: 5.8.5 (November 11, 2026) | License: Apache-2.0

Package: `diskcache-community`\
Import namespace: `diskcache_community`\
Python compatibility: Python 3.8+; documented CI coverage includes CPython 3.10–3.14.\
Dependencies: Python standard library for core functionality; NumPy is optional for specialized serialization.

Primary sources:

- Repository: [https://github.com/secondwindoss/diskcache-community](https://github.com/secondwindoss/diskcache-community?utm_source=chatgpt.com)
- Documentation: [https://diskcache-community.readthedocs.io/en/latest/](https://diskcache-community.readthedocs.io/en/latest/?utm_source=chatgpt.com)
- API reference: [https://diskcache-community.readthedocs.io/en/latest/api.html](https://diskcache-community.readthedocs.io/en/latest/api.html?utm_source=chatgpt.com)
- Changelog: [https://github.com/secondwindoss/diskcache-community/blob/master/CHANGELOG.md](https://github.com/secondwindoss/diskcache-community/blob/master/CHANGELOG.md?utm_source=chatgpt.com)
- PyPI: [https://pypi.org/project/diskcache-community/](https://pypi.org/project/diskcache-community/?utm_source=chatgpt.com)

The version and compatibility information above is verified against the current PyPI release metadata and upstream changelog.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 1. Executive orientation

diskcache-community is a persistent, SQLite-backed caching and coordination library that combines a high-level Python cache interface with transactional key-value operations, disk-backed collections, cross-process synchronization, and customizable serialization.

It is a maintained community fork of Grant Jenks's original `diskcache` library, preserving its established architecture while addressing security, compatibility, connection lifecycle, and performance issues.

Its distinguishing architectural characteristic is that it provides many capabilities normally associated with a separately operated cache service, but implements them using local SQLite databases and filesystem storage, without requiring a Redis server, Memcached daemon, or dedicated cache infrastructure.

That makes it more than a mechanism for persisting Python dictionaries. It can also serve as:

- A bounded, persistent, multiprocess key-value cache.
- A durable memoization layer shared across Python processes and restarts.
- A local coordination substrate supporting atomic operations, locks, semaphores, and rate limiting.
- A disk-backed queue and collection engine.
- A filesystem-backed store for larger binary or structured objects.
- A Django caching backend.
- A lightweight transactional state store where a separately operated database or cache service would be unnecessary.

The last role is conditional: although it offers atomicity and persistence, it is not a general-purpose distributed database, message broker, or transactional workflow engine.

### Capability map

| Capability family      | Principal mechanisms                                  | Architectural significance                                           |
| ---------------------- | ----------------------------------------------------- | -------------------------------------------------------------------- |
| Persistent caching     | `Cache`, expiration, eviction, tags                   | Reusable cached results across processes and restarts                |
| Concurrent caching     | SQLite WAL, atomic operations, `FanoutCache`          | Shared cache access with reduced write contention through sharding   |
| Transactional state    | `transact`, `add`, `incr`, `pop`                      | Atomic read-modify-write and shared counters                         |
| Persistent collections | `Deque`, `Index`                                      | Disk-backed collection semantics across process boundaries           |
| Queue operations       | `push`, `pull`, `peek`                                | FIFO/LIFO-style work coordination and named queues                   |
| Function caching       | `memoize`, `memoize_stampede`                         | Persistent function-result caching with optional stampede mitigation |
| Synchronization        | `Lock`, `RLock`, `BoundedSemaphore`, `throttle`       | Coordination without a separate synchronization service              |
| Serialization          | `Disk`, `JSONDisk`, `SafeDisk`, `SafeJSONDisk`        | Control over object representation, security, and interoperability   |
| Operational control    | Size limits, stats, culling, checks, read-only access | Lifecycle, capacity, and maintenance management                      |
| Integration            | `DjangoCache`, configurable default disks             | Framework-level caching and centralized serialization selection      |

The most important architectural distinction is between individual cache operations, which can be atomic across processes, and higher-level multi-operation workflows, which require explicit transactions or additional coordination to preserve their intended invariants.

### What differentiates the community fork

Compared with the original `diskcache` 5.6.3, the community fork introduces several consequential improvements:

1. An independent import namespace: `diskcache_community` can coexist with upstream `diskcache` in the same Python environment.
2. Restricted deserialization: opt-in `SafeDisk` and `SafeJSONDisk` address risks associated with unrestricted pickle loading.
3. Improved process and connection handling: fixes for SQLite connection lifetimes, inherited connections after process forks, and read-only access.
4. Expanded serializer configuration: process-wide disk selection, explicit serialization allowlists, and supported NumPy serialization.
5. Additional metadata and data-access facilities: including stored timestamps, tag-filtered iteration, and configurable SQLite database filenames.
6. Updated maintenance and typing: new bug fixes, type stubs, and current Python support.

The fork retains the database schema and on-disk layout of the original project, which is particularly important for applications with existing persistent caches. However, compatible storage formats do not imply that every serializer or security configuration can interpret every stored object.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 2. Storage architecture and execution model

### 2.1 SQLite metadata combined with filesystem values

The storage engine uses two complementary mechanisms:

- SQLite manages keys, metadata, transactional state, indexes, and smaller values.
- Filesystem objects hold larger serialized values, with SQLite storing references to those files.

Python cache interface

Cache / FanoutCache / Deque / Index

Disk serialization layer

Keys, values, object encoding, file placement

SQLite database

Keys, small values, metadata, indexes, transactions

Value files

Large objects, binary payloads, file-backed reads

The database is normally named `cache.db`. As of 5.8.5, `Cache` also accepts a keyword-only `dbname` argument allowing a different SQLite filename within its directory.

Keys remain represented in SQLite, while values can be stored inline or outside the database. By default, `disk_min_file_size` is 32 KiB. The serializer and the kind of value influence actual placement; `read=True` can explicitly provide a binary stream and request file-backed storage.

Large value files use generated names and a two-level directory layout, avoiding enormous single directories. The result is a cache whose metadata operations benefit from SQLite indexes while large payloads need not be embedded in database rows.

This separation can reduce SQLite database growth and simplify access to large binary objects. It also means that a complete cache consists of the database and its associated value files, not just `cache.db`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation+2



### 2.2 Core SQLite mechanisms

DiskCache uses several SQLite features in combination:

| Mechanism                 | Role                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------- |
| Write-ahead logging (WAL) | Allows readers and a writer to proceed concurrently under normal operating conditions |
| SQLite transactions       | Atomic changes and consistency across multiple cache operations                       |
| Database indexes          | Accelerate key lookup, eviction order, expiration, and optional tag access            |
| Triggers                  | Maintain stored counts and size-related metadata                                      |
| Memory-mapped access      | Makes SQLite database pages available through memory mapping                          |
| Per-thread connections    | Avoids sharing a SQLite connection unsafely across threads                            |
| Multiple database shards  | Distributes writes across independent SQLite writer locks                             |

SQLite WAL is central to the concurrency model. Readers generally do not block writers, but writes to the same SQLite database remain serialized.

The library therefore has two distinct ways of improving throughput:

1. Optimize operations on a single database through indexes, short transactions, and efficient value representation.
2. Partition keys across multiple databases with `FanoutCache`, permitting independent writers to operate concurrently.

The second approach increases write concurrency but sacrifices the ability to transact atomically over arbitrary keys in the combined cache.

### 2.3 Serialization determines key identity

A particularly important semantic distinction is that DiskCache does not use Python's ordinary dictionary hashing and equality protocol for general key lookup.

Instead, the `Disk` serializer converts a key to its stored representation, and that representation determines identity.

Native SQLite-compatible key types include integers, floats, strings, and bytes. Other values are generally serialized.

Consequences:

- `1` and `1.0` can identify the same key, reflecting their numeric equality.
- Compound keys often depend on their exact serialized byte representation.
- Two structurally equal Python objects do not necessarily produce identical pickle bytes.
- Even tuples containing equal elements can serialize differently because pickle preserves aspects of object structure and identity.
- Custom serializers can implement more predictable canonicalization where necessary.

This distinction matters for memoization, deterministic artifact caching, and reusable results keyed by structured inputs. A key that appears equal in Python may still miss if its serialized form differs.

Architectural implication: cache-key construction is part of the data model, not merely an incidental use of Python's `__hash__` behavior.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#caveats](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#caveats)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



## 3. Core caching capabilities

### 3.1 Key-value operations

`Cache` presents a familiar mutable-mapping interface while exposing more expressive cache-specific operations.

| Operation              | Semantics                                                       |
| ---------------------- | --------------------------------------------------------------- |
| `get`, `set`, `delete` | Retrieval, insertion or replacement, and deletion               |
| `add`                  | Atomic insert only when a nonexpired key does not already exist |
| `pop`                  | Atomically retrieve and remove an entry                         |
| `incr`, `decr`         | Atomic updates to numeric values                                |
| `touch`                | Update the time-to-live of an existing entry                    |
| `peekitem`             | Inspect the first or last entry by iteration order              |
| `clear`                | Remove all cache entries                                        |
| `iterkeys`             | Ordered key traversal, optionally filtered by tag               |

The atomic `add` and `incr` operations are especially useful because they replace common multi-step patterns that would otherwise suffer from lost updates.

For example, a conditional insertion does not require an application to first check for the key and then attempt a separate write. Two competing processes can call `add`, but only one will successfully create the entry.

Similarly, `incr` and `decr` are safe for shared counters, subject to their stored numeric representation.

The standard mapping syntax remains useful, but explicit methods expose expiration, tags, stream handling, and retry behavior more precisely.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation



### 3.2 Expiration, tag metadata, and stored timestamps

An entry can carry additional metadata independently of its value:

- `expire`: relative lifetime in seconds.
- `tag`: a value used to group entries for inspection or deletion.
- Stored creation/update time, retrievable with `store_time=True`.
- Expiration timestamp, retrievable with `expire_time=True`.

A compact example of these interactions:

```
from diskcache_community import Cachecache = Cache("results", tag_index=True)cache.set(    ("model", 42),    {"score": 0.95},    expire=3600,    tag="evaluation",)value, expiry, tag, stored = cache.get(    ("model", 42),    expire_time=True,    tag=True,    store_time=True,)cache.touch(("model", 42), expire=7200)cache.evict("evaluation")
```

The four-element return tuple follows a defined metadata order: value, expiration time, tag, and storage time.

An important property is that expiration and physical deletion are separate operations.

An expired item behaves as absent during normal retrieval, but its database entry may remain until a later access, write-triggered culling, or explicit cleanup removes it.

This is why `len(cache)` and ordinary iteration can include expired entries. They are not guaranteed to represent the number of currently retrievable, unexpired values.

The `store_time` capability added by the fork is useful for observing cache age directly rather than maintaining separate application metadata.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+2



### 3.3 Tag-based selection and invalidation

Tags are a native metadata mechanism rather than something an application must encode into its keys.

`cache.evict(tag)` removes all entries associated with the tag.

`cache.iterkeys(tag=...)` retrieves matching keys without materializing their values. This iterator can operate in forward or reverse SQLite sort order.

When `tag_index=True`, the cache maintains an index to make tag-based operations more efficient.

The key distinction is that a tag provides a single grouping attribute per item, not an arbitrary multi-valued tagging or secondary-index system.

Nevertheless, tags can eliminate substantial custom bookkeeping in systems that need to invalidate groups of related cached outputs.

For example, versioned calculations, imported data batches, and generated artifacts can be grouped by provenance or logical generation and invalidated together.

Tag invalidation is also useful alongside memoization: a decorator can assign a tag to its cached results, which can subsequently be invalidated as a group without reconstructing every function argument combination.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#cache](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#cache)

### 3.4 Streaming large values

The library supports passing binary file-like objects with `read=True`, storing their contents in file-backed form.

It also provides `Cache.read(key)` for obtaining a binary file handle to a stored value.

This can avoid constructing an additional Python `bytes` object during retrieval and permits integration with APIs that consume file-like objects or filesystem paths.

The Django backend additionally documents use with `X-Sendfile` and `X-Accel-Redirect`, allowing a web server to serve cached files without the Python application sending the entire body itself.

There are important boundaries:

- An open file handle is a resource that the caller must close.
- The stored file belongs to the cache and may be removed by eviction or deletion.
- File-backed access does not automatically guarantee zero-copy processing or memory mapping.
- The exact benefit depends on whether the consumer can operate directly on the file or stream.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#djangocache](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#djangocache)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



## 4. Concurrency, transactions, and sharding

### 4.1 Thread-safe and process-safe caching

Multiple threads and processes can open the same cache directory and operate on the data concurrently.

Each thread uses its own SQLite connection. The community fork improves connection cleanup and addresses inherited SQLite connections when a process forks.

A `Cache` instance can be reused across threads, and independent `Cache` instances can share a directory across process boundaries.

This enables local multiprocess workers to share cached results and counters without a manager process that owns an in-memory dictionary.

However, process safety is ultimately provided by SQLite and the underlying filesystem. It does not imply safe concurrent operation across every kind of remote or shared filesystem.

### 4.2 Transactions and atomic multi-key operations

`Cache.transact()` provides a transaction context manager:

```
with cache.transact():    total = cache.incr("total", 125)    count = cache.incr("count")
```

The transaction makes the grouped changes atomic and allows code to establish invariants involving multiple entries.

It supports nested transaction contexts within a thread and avoids repeated transaction setup for each operation in a batch.

This can improve performance by amortizing transaction overhead, but it also means a long-running transaction holds a writer lock and delays other writers.

The upstream documentation reports potential improvements of two to five times for grouping bulk writes; this is a workload-dependent observation, not a general throughput guarantee.

Transactions are available on `Cache`, `Deque`, and `Index`, but not across an entire `FanoutCache`.

That distinction is essential whenever consistency spans multiple keys.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



### 4.3 FanoutCache: sharded SQLite storage

`FanoutCache` partitions keys among independent `Cache` instances, each with its own SQLite database.

```
from diskcache_community import FanoutCachecache = FanoutCache(    "shared-cache",    shards=8,    timeout=1.0,    size_limit=4 * 1024**3,)
```

The main advantage is reduced writer contention.

FanoutCache — key routing

Stable key-to-shard assignment

Shard 1

SQLite

Shard 2

SQLite

Shard 3

SQLite

Shard 4

SQLite

Illustrative four-shard layout; each database has its own writer lock.

For a fixed shard configuration, keys route consistently to their corresponding shard. Independent shards can write simultaneously, enabling better throughput when concurrent writes are distributed across them.

Important characteristics:

- Default shard count is eight.
- The overall configured size limit is divided across shards.
- Eviction operates within each shard's capacity.
- There is no cross-shard atomic transaction.
- Changing the shard count is not equivalent to simply adding capacity to one database; it changes key routing and requires consideration of existing data.

The per-shard size limit can matter for large objects. An object may be evicted because it exceeds its shard's capacity even though considerable space remains in other shards.

### 4.4 Timeout behavior and potential silent failures

`FanoutCache` has a notable behavioral difference from `Cache`.

A normal `Cache` operation can raise `diskcache_community.Timeout` when SQLite cannot acquire the required lock within its configured timeout.

`FanoutCache` generally catches these timeouts and aborts the operation. Consequently, methods such as `set` or `delete` can fail without raising an exception.

Its default database timeout is only 10 milliseconds, compared with the ordinary `Cache` default of 60 seconds.

Many methods accept a `retry` argument. Dictionary-style operations automatically retry relevant timeouts, but other operations may not.

This has substantial implications for correctness:

- A best-effort memoization cache can often tolerate a failed write.
- A shared counter, lock, or coordination record may not.
- A successful function invocation is not necessarily proof that a timed-out cache mutation took effect.

`FanoutCache` therefore should not be treated as a transparent substitute for `Cache` when write acknowledgment and transactional consistency are essential.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#fanoutcache](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#fanoutcache)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+1



### 4.5 Named subcaches and coordinated collections

`FanoutCache` exposes additional constructors:

```
fanout = FanoutCache("shared-root")metadata = fanout.cache("metadata")work_queue = fanout.deque("pending-work")state = fanout.index("state")
```

These create named, directory-backed child collections.

The useful distinction is that a named `cache()` provides an independently addressable `Cache` with transaction support; it is not a cross-shard transaction covering the parent `FanoutCache`.

This facility can simplify the organization of several related persistent data structures under one cache root.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#transactions](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#transactions)

## 5. Persistent collections and queues

The persistent collection interfaces are among DiskCache's most easily overlooked capabilities.

Unlike regular Python containers, they can be reconstructed from a directory and accessed by other processes without serializing and transferring the complete collection.

### 5.1 Deque: persistent double-ended sequences

`diskcache_community.Deque` implements disk-backed, double-ended queue semantics modeled on `collections.deque`.

Supported operations include appending, removing, and inspecting elements at either end, as well as familiar collection operations.

```
from diskcache_community import Dequequeue = Deque(directory="tasks")queue.append({"job": 1})queue.appendleft({"job": 0})job = queue.popleft()
```

Another process opening `Deque(directory="tasks")` can access the same persisted collection.

Significant properties include:

- Endpoint operations are atomic and usable across processes.
- Contents persist beyond the lifetime of the Python process.
- A `maxlen` parameter can impose bounded sequence semantics.
- The collection does not use ordinary cache expiration or eviction.
- Transactions can group compatible operations.
- It does not require loading all stored elements into Python memory.

A `Deque` is therefore useful for implementing persistent worklists, processing buffers, and communication between local workers.

However, `maxlen` deliberately discards older elements when the sequence exceeds its bound. That can be useful for rolling histories but unsuitable for a queue whose items must never be dropped.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+1



### 5.2 Index: persistent ordered mapping

`diskcache_community.Index` offers a disk-backed mutable mapping whose iteration follows insertion order.

It is conceptually similar to a persistent ordered dictionary, but with cross-process access and transactional support.

An `Index` provides mapping-style methods for retrieving, updating, removing, and iterating entries. Its documented interface also includes `popitem`, mapping views, and memoization.

Unlike an ordinary `Cache`, it disables eviction and expiration so that retained entries are not automatically discarded.

This makes it better suited to persistent mappings or small state registries whose lifetime should be controlled explicitly.

The distinction between `Index` and `Cache` is primarily retention semantics, not the underlying storage engine.

`Index` is not a general secondary-indexing engine: its name refers to its persistent ordered mapping interface.

### 5.3 Native queue operations on Cache

Even without constructing a `Deque`, `Cache` provides queue-oriented operations:

| Method | Behavior                                  |
| ------ | ----------------------------------------- |
| `push` | Append an item and generate its queue key |
| `pull` | Atomically remove and return an item      |
| `peek` | Inspect an item without consuming it      |

Queues can operate from the front or back, supporting FIFO- or LIFO-style access patterns.

The `prefix` argument permits multiple logical queues inside one cache. Queue keys are automatically generated in sortable form rather than requiring callers to coordinate their own sequence numbers.

```
cache.push({"task": "parse"}, prefix="jobs")cache.push({"task": "index"}, prefix="jobs")key, job = cache.pull(prefix="jobs")
```

These operations can also preserve cache metadata such as expiration and tags.

The queue model is based on ordered keys and transactional removal, not an independent message-broker subsystem.

### 5.4 Queue guarantees versus message-broker guarantees

Atomic dequeue is valuable, but it is not the same as reliable task delivery.

Suppose a worker calls `pull`, receives a job, and then crashes before completing it. The item has already been removed.

DiskCache does not automatically provide the full suite of broker semantics such as acknowledged delivery, visibility timeouts, redelivery, dead-letter routing, or consumer-group coordination.

These capabilities would require additional state and logic, or a dedicated job/messaging system.

The useful boundary: DiskCache natively solves safe persistent queue manipulation, but it does not automatically solve reliable distributed job execution.

Sources:

[https://diskcache-community.readthedocs.io/en/latest/tutorial.html#deque](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#deque)

[https://diskcache-community.readthedocs.io/en/latest/api.html](https://diskcache-community.readthedocs.io/en/latest/api.html?utm_source=chatgpt.com)

## 6. Memoization and cache stampede mitigation

### 6.1 Persistent function-result caching

Both `Cache` and `FanoutCache` expose the `memoize` decorator.

It automatically constructs cache keys from function identity and arguments, stores returned values, and returns previously computed results on subsequent matching calls.

```
@cache.memoize(    expire=600,    typed=True,    tag="calculations",    ignore={"session"},)def calculate(parameters, session):    ...
```

The significant parameters are:

| Parameter | Meaning                                                            |
| --------- | ------------------------------------------------------------------ |
| `name`    | Explicit cache namespace for the callable                          |
| `typed`   | Distinguish arguments by their types                               |
| `expire`  | Lifetime of cached results                                         |
| `tag`     | Associate results with an invalidation group                       |
| `ignore`  | Exclude selected positional or named arguments from cache identity |

The `ignore` capability is particularly useful for callables with nonsemantic dependencies such as session objects, connections, or clients.

In the current fork, naming a parameter in `ignore` excludes it whether the caller supplied it positionally or by keyword.

The wrapper also exposes `__wrapped__` to access the original function and `__cache_key__` to construct the key for given arguments. These enable explicit invalidation and instrumentation without independently recreating its key-generation logic.

The cache key is based on the decorator's key construction and serialized arguments. It does not automatically include source-code hashes, model versions, database dependency versions, or other external state. Such dependencies must be reflected in naming, arguments, tags, or explicit invalidation when they affect correctness.

Source: [https://diskcache-community.readthedocs.io/en/latest/api.html#cache](https://diskcache-community.readthedocs.io/en/latest/api.html?utm_source=chatgpt.com#cache)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation



### 6.2 Stampede protection

`memoize_stampede` goes beyond ordinary memoization.

A cache stampede occurs when many concurrent requests discover that a popular entry has expired and independently begin recomputing the same result.

The library provides:

```
from diskcache_community import memoize_stampede@memoize_stampede(cache, expire=300, beta=1)def expensive_result(key):    ...
```

Its mechanism is probabilistic early recomputation.

Rather than waiting for the exact expiration boundary, it probabilistically starts recomputation before expiration, using a background thread. This can distribute refresh work and reduce simultaneous cache misses for frequently requested results.

The algorithm is based on the work described in Optimal Probabilistic Cache Stampede Prevention by Vattani, Chierichetti, and Lowenstein (2015).

The `beta` parameter governs the early-recomputation behavior.

This is distinct from implementing a blocking single-flight lock around every miss. It aims to reduce stampedes statistically rather than guaranteeing that a given computation will execute exactly once.

That distinction matters in systems where result computation has side effects or must not overlap.

`memoize_stampede` is most naturally suited to expensive, repeatable computations whose results may safely be generated concurrently if necessary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation



### 6.3 Interactions with serialization and invalidation

Memoization inherits the semantics of both the cache and its serializer.

For example, two logically identical structured arguments may generate different keys if their serialized representations differ. `typed=True` also deliberately separates some otherwise equal numeric inputs.

Conversely, ignoring an argument that genuinely changes the function's result can cause incorrect cache hits.

The decorator's `tag` capability composes with `evict(tag)` to invalidate a group of memoized results. This can remove the need to enumerate and individually delete every derived key.

The community fork also corrected an interaction between `memoize_stampede` and `SafeDisk` involving an internal early-recomputation marker, making those features usable together.

## 7. Cross-process coordination primitives

DiskCache includes synchronization recipes built on the same persistent, atomic cache operations.

These are particularly relevant when several Python processes on the same host need to coordinate without a separately managed coordination server.

| Primitive          | Purpose                                            | Important distinction                                                 |
| ------------------ | -------------------------------------------------- | --------------------------------------------------------------------- |
| `Lock`             | Mutual exclusion                                   | Non-reentrant, implemented using cache keys                           |
| `RLock`            | Reentrant mutual exclusion                         | Tracks recursive acquisition                                          |
| `BoundedSemaphore` | Bound the number of concurrent entrants            | Uses a stored count                                                   |
| `throttle`         | Limit the rate of function calls                   | Coordinates calls using cache state                                   |
| `barrier`          | Gate execution through a synchronization primitive | Decorator-based synchronization, not necessarily a rendezvous barrier |
| `Averager`         | Maintain running average statistics                | Uses shared stored state                                              |

### 7.1 Locks and semaphores

A cross-process lock can be created using the supplied recipe:

```
from diskcache_community import Cache, Lockcoordination = Cache(    "coordination",    eviction_policy="none",)lock = Lock(coordination, "critical-section")with lock:    perform_critical_operation()
```

The implementation uses atomic cache operations and a spin-lock acquisition algorithm.

`RLock` permits reentrant acquisition, while `BoundedSemaphore` manages a fixed maximum number of available entries into a critical section.

The key operational requirement is that coordination entries must not be unexpectedly evicted.

The upstream documentation repeatedly recommends `eviction_policy="none"` for these recipes. Eviction of a lock or semaphore entry can invalidate the synchronization state while other processes are depending on it.

An expiration on a lock-like record also has lease-like consequences: if it expires before the guarded operation finishes, another participant may acquire it while the original operation is still running.

These recipes are useful coordination primitives, but the documentation does not establish the stronger guarantees of a fault-tolerant distributed lock service, such as fencing tokens, consensus, or automatic recovery from every form of process failure.

### 7.2 Throttling and execution gates

`throttle(cache, count, seconds)` decorates a callable to limit how frequently it is invoked across participants sharing the cache.

It also provides `time_func` and `sleep_func` parameters, enabling clock and waiting behavior to be substituted—for example, during testing.

`barrier(cache, lock_factory)` wraps function execution using a synchronization primitive such as `Lock`, `RLock`, or `BoundedSemaphore`.

With `Lock`, it can serialize calls across worker threads or processes. With a bounded semaphore factory, it can limit simultaneous execution.

This is different from a traditional `threading.Barrier` that requires a predefined number of participants to arrive before proceeding.

### 7.3 When these primitives are useful

These facilities can reduce the need to implement independent coordination infrastructure for operations such as restricting local concurrency, serializing conflicting tasks, maintaining shared counters, or enforcing a common rate limit.

They become less appropriate when workloads require coordination across machines that do not safely share the same SQLite database, strict lock fairness, robust crash recovery, or distributed consensus.

Source: [https://diskcache-community.readthedocs.io/en/latest/api.html#recipes](https://diskcache-community.readthedocs.io/en/latest/api.html?utm_source=chatgpt.com#recipes)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation+1



## 8. Eviction, capacity management, and performance tuning

### 8.1 Eviction policies and their read-path costs

DiskCache supports four eviction strategies.

| Policy                  | Selection criterion            | Read overhead              | Typical suitability                    |
| ----------------------- | ------------------------------ | -------------------------- | -------------------------------------- |
| `least-recently-stored` | Oldest storage timestamp       | No eviction-metadata write | General-purpose large caches           |
| `least-recently-used`   | Oldest access timestamp        | Updates access time        | Workloads where recency predicts reuse |
| `least-frequently-used` | Lowest access count            | Increments access count    | Workloads with stable popularity       |
| `none`                  | No automatic capacity eviction | No eviction-metadata write | Persistent state and coordination      |

The default is least-recently-stored, not LRU.

This is a consequential performance choice. LRS permits reads without maintaining an access timestamp, whereas LRU and LFU introduce write operations on reads.

That write amplification changes concurrency behavior: a workload that is logically read-heavy can generate significant SQLite writer contention when LRU or LFU is enabled.

For caches that must handle large read volumes, the difference can be more important than modest differences in which objects remain cached.

Eviction policies are reflected in the SQLite indexes maintained for cache entries. Changing the policy on an existing cache does not automatically remove all indexes associated with the old policy.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#eviction-policies](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#eviction-policies)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



### 8.2 Size limits and culling

The default size limit is approximately 1 GiB, but it should be understood as an operational target rather than a strict filesystem quota.

The `cull_limit` parameter controls how many items may be removed during ordinary insertion operations.

By default, that limit is ten. Setting it to zero disables automatic culling and allows cleanup to be managed separately.

Explicit maintenance operations include:

- `expire()` — delete expired entries.
- `evict(tag)` — remove entries with matching metadata.
- `cull()` — reduce storage toward the configured size limit.
- `clear()` — remove all entries.

These operations perform deletion incrementally. They are designed to coexist with other cache activity, and concurrent changes can occur between cleanup batches.

One useful architectural option is to decouple cleanup frequency from the write path. For write-sensitive workloads, background or periodically invoked culling may reduce insertion overhead at the cost of temporary excess disk usage.

`volume()` estimates the storage occupied by the cache database and value files, but it does not account for every aspect of filesystem consumption, such as directory metadata.

### 8.3 SQLite configuration

A substantial part of the library's performance configuration comes directly from SQLite.

| Setting               | Default     | Implication                                                 |
| --------------------- | ----------- | ----------------------------------------------------------- |
| `sqlite_journal_mode` | `wal`       | Concurrent readers and writer                               |
| `sqlite_synchronous`  | `NORMAL`    | Reduced synchronization overhead, with durability tradeoffs |
| `sqlite_mmap_size`    | 64 MiB      | Memory-mapped database access                               |
| `sqlite_cache_size`   | 8,192 pages | SQLite's per-connection page cache                          |
| `sqlite_auto_vacuum`  | `FULL`      | Database space reclamation                                  |
| `disk_min_file_size`  | 32 KiB      | Threshold for file-backed values                            |
| `statistics`          | Disabled    | Avoids writes and overhead for hit/miss recording           |
| `tag_index`           | Disabled    | Avoids maintaining an unused secondary index                |

These settings can be supplied when creating a cache and inspected or changed through `reset()`.

Settings are persisted in SQLite so that processes sharing the cache can coordinate configuration, but individual cached attributes may be stale until reloaded.

The option of using `sqlite_synchronous=FULL` deserves particular attention when a cache is used for persistent state rather than disposable results.

With WAL and `NORMAL` synchronization, SQLite preserves transaction consistency, but a recently committed transaction may be lost after a system crash or power failure. `FULL` strengthens durability by synchronizing the WAL at commit, at additional I/O cost.

Thus, atomicity during concurrent execution is not identical to durability across power loss.

Sources:

[https://diskcache-community.readthedocs.io/en/latest/tutorial.html#settings](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#settings)

[https://www.sqlite.org/pragma.html#pragma_synchronous](https://www.sqlite.org/pragma.html?utm_source=chatgpt.com#pragma_synchronous)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+1



## 9. Serialization, security, and custom storage

The `Disk` abstraction is one of the library's most significant extension points, particularly in the community fork.

It controls key encoding, value serialization, filesystem placement, deserialization, and portable key hashing.

### 9.1 Serialization choices

| Serializer                 | Representation                                      | Security and compatibility                                                         |
| -------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `Disk`                     | Native SQLite types plus pickle                     | Broad Python-object support; unrestricted pickle reading                           |
| `JSONDisk`                 | JSON with zlib compression                          | JSON-oriented writes, but inherited pickle reads are unsafe against crafted rows   |
| `SafeDisk`                 | Compatible pickle format with restricted unpickling | Built-in type allowlist and confined file paths                                    |
| `SafeJSONDisk`             | Compatible compressed JSON                          | Refuses pickle reads and confines file paths                                       |
| `SafeDisk.with_types(...)` | Restricted pickle with approved classes             | Allows selected application-defined types                                          |
| `SafeDisk.with_numpy()`    | Restricted pickle with `.npy`-encoded array data    | Supports selected NumPy representations without unsafe NumPy pickle reconstruction |
| Custom `Disk` subclass     | Application-defined                                 | Flexible but requires explicit compatibility and security design                   |

### 9.2 SafeDisk and CVE-2025-69872

The original DiskCache uses pickle for many Python values.

Pickle is not a safe format for data controlled by an untrusted party. A malicious serialized object can request execution of arbitrary Python code when deserialized.

CVE-2025-69872 concerns this behavior when an attacker can modify a cache directory that another process subsequently reads.

The community fork's `SafeDisk` addresses this attack path by restricting which types can be reconstructed, checking values before writing them, and preventing stored file paths from escaping the cache directory.

```
from diskcache_community import Cache, SafeDiskcache = Cache(    "secure-cache",    disk=SafeDisk,)
```

The crucial detail is that `SafeDisk` remains opt-in in version 5.8.5.

Installing the maintained fork alone does not change the default deserialization mechanism. `Disk` remains the default to preserve compatibility with existing caches containing arbitrary Python objects.

The community fork also creates new cache directories with `0700` permissions on systems that support POSIX mode bits. Existing directories retain their permissions.

This provides an additional security boundary but does not eliminate the need to account for shared volumes, untrusted cache artifacts, or other processes with write access.

Source: [https://diskcache-community.readthedocs.io/en/latest/fix-cve-2025-69872.html](https://diskcache-community.readthedocs.io/en/latest/fix-cve-2025-69872.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+1



### 9.3 Explicit allowlists for application types

`SafeDisk.with_types` extends the restricted serializer with approved types.

```
from diskcache_community import Cache, SafeDiskAppDisk = SafeDisk.with_types(    Result,    Metadata,    modules=("myapp.models",),)cache = Cache("results", disk=AppDisk)
```

The allowlist can refer to specific classes or classes defined in specified modules.

This mechanism is more restrictive than permitting arbitrary globals from an importable module.

The implementation verifies class identity and provenance, refuses certain unsafe module families, and does not import new modules while deserializing.

However, allowing application-defined classes expands the attack surface. Classes with dangerous reconstruction behavior or `__setstate__` methods can still be unsuitable for untrusted serialized data.

Therefore, the allowlist is best understood as a controlled deserialization mechanism, not as a universal sandbox for arbitrary Python objects.

### 9.4 NumPy serialization

The fork's NumPy support is unusually sophisticated for a general-purpose Python cache.

`SafeDisk.with_numpy()` creates a serializer subclass supporting NumPy data through `.npy` representations rather than relying on the unrestricted NumPy pickle reconstruction path.

```
import numpy as npfrom diskcache_community import Cache, SafeDiskArrayDisk = SafeDisk.with_numpy()cache = Cache(    "array-cache",    disk=ArrayDisk,)cache["embedding"] = np.arange(1024, dtype=np.float32)cache["result"] = {    "scores": np.array([0.1, 0.5, 0.9]),    "best": np.float64(0.9),}
```

Important capabilities include:

Nested array serialization. Arrays can appear inside other supported Python structures and approved custom classes. Repeated references to the same array within a value are preserved.

Array-aware cache keys. Version 5.8.4 expanded support for NumPy scalars and arrays as keys, including arrays nested inside structured arguments.

Canonical array representation. Arrays used as keys are serialized in C order. Equal arrays with the same dtype and shape can identify the same cache entry even when their original memory orders differ.

Typed scalar preservation. Supported NumPy numeric scalars, `datetime64`, and `timedelta64` preserve their representations, including relevant time units.

Special array types. Supported record arrays and masked arrays retain their types and selected metadata. Memory-mapped arrays are stored as ordinary arrays rather than preserving their original file mapping.

Restricted object arrays. Object-dtype elements must themselves satisfy the serializer's type restrictions. Unsupported array subclasses or unsafe object structures can be rejected.

The limitations are equally important.

`SafeDisk.with_numpy()` is not a general NumPy object graph serializer, a GPU tensor storage engine, or a transparent memory-mapped-array database.

Entries containing this specialized representation are not readable by the original DiskCache 5.6.3 or by an ordinary `SafeDisk`. Every participant sharing such a directory must use a compatible serializer.

There is also a subtle interaction with memoization: NumPy arguments used with `memoize(typed=True)` can be rejected because the memoization key includes NumPy class objects.

These distinctions make the feature valuable for array-heavy Python systems, but serializer compatibility must be treated as part of the persistent data contract.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#storing-numpy-arrays](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#storing-numpy-arrays)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation+1



### 9.5 JSONDisk versus SafeJSONDisk

`JSONDisk` is provided for JSON-oriented serialization with zlib compression.

However, its historical implementation inherits pickle-reading behavior from `Disk`.

This means that choosing `JSONDisk` does not, by itself, eliminate the security vulnerability associated with a crafted pickle-containing database row.

`SafeJSONDisk`, added in 5.8.2, addresses this distinction.

It preserves compatibility with the compressed JSON representation while refusing pickle reads and enforcing file-path confinement.

`SafeDisk` cannot simply replace an existing `JSONDisk`, because it does not decode the latter's compressed JSON representation.

This is an example of why serialization format compatibility and deserialization security are separate architectural properties.

### 9.6 Handling corrupt or unreadable entries

The fork adds `Disk.with_options(on_error='miss')`.

```
ResilientDisk = (    SafeDisk    .with_types(Result)    .with_options(on_error="miss"))cache = Cache("results", disk=ResilientDisk)
```

Normally, a corrupted pickle, missing class, or disallowed type can raise an exception during retrieval.

With `on_error="miss"`, supported deserialization failures cause the entry to be treated as unavailable.

The behavior includes removing the unreadable entry when the cache is writable, returning a default from `get`, and skipping unreadable entries during applicable iteration and queue operations.

There are consequential qualifications:

- The default remains `on_error="raise"`.
- Certain failures, including `MemoryError` and `RecursionError`, are not converted into cache misses.
- Missing value files already follow separate missing-data behavior.
- Read-only caches cannot delete unreadable entries.
- `len()` and membership checks can temporarily include entries that subsequent reads reject.
- A reader with a narrower allowlist can delete entries that another process would consider valid.

This feature is well suited to recomputable cache data, especially when object schemas or Python package versions change. It is not generally appropriate for authoritative data that must be recovered or investigated rather than discarded.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#unreadable-entries](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#unreadable-entries)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



### 9.7 Implementing a custom Disk

The `Disk` extension interface exposes methods including:

| Method     | Responsibility                             |
| ---------- | ------------------------------------------ |
| `put`      | Convert Python keys into stored key fields |
| `get`      | Reconstruct Python keys                    |
| `store`    | Serialize and place values                 |
| `fetch`    | Read and deserialize values                |
| `hash`     | Produce a portable hash for key routing    |
| `filename` | Select a filesystem location for a value   |
| `remove`   | Remove a value file                        |

Custom implementations can introduce canonical serialization, alternative compression, domain-specific object representations, or different file-placement policies.

The significant design obligation is to preserve consistency among all clients opening the same cache.

Changing the serialized key representation can make previously stored keys inaccessible or change their shard assignment. Changing value encoding without corresponding read compatibility can render existing entries unreadable.

A serializer is therefore not merely a performance plugin. It defines a portion of the cache's persistent storage semantics.

Source: [https://diskcache-community.readthedocs.io/en/latest/api.html#disk](https://diskcache-community.readthedocs.io/en/latest/api.html?utm_source=chatgpt.com#disk)

## 10. Read-only caches and operational lifecycle

### 10.1 Read-only access

The community fork introduced explicit and automatic read-only behavior.

```
snapshot = Cache(    "reference-cache",    read_only=True,)
```

An existing cache also opens read-only when the database or directory is not writable.

This is useful for immutable container layers, precomputed cache directories, repeatable fixtures, and read-mostly deployment environments.

Supported operations include reads, iteration, statistics inspection, integrity checks, and cache hits on memoized functions.

Mutating methods raise `ReadOnlyError`, which subclasses `sqlite3.OperationalError`.

Read-only operation has some nuanced implications:

- Hit/miss counters are not updated.
- LRU and LFU metadata are not updated.
- Expired entries are skipped rather than deleted.
- A memoization miss cannot successfully persist a newly computed result.
- Explicit read-only configuration is not stored in the database.

When the filesystem itself is nonwritable, the library uses SQLite's immutable mode, avoiding WAL shared-memory files and normal database locking.

That mode is only appropriate when the underlying files genuinely cannot change while readers are using them.

This capability makes a precomputed cache directory more useful as a portable, queryable artifact, but it does not turn the cache into a transactional snapshot system.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#read-only-caches](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#read-only-caches)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



### 10.2 Integrity checks and maintenance

`Cache.check(fix=False)` examines consistency between database metadata and filesystem state.

With `fix=True`, it can repair supported inconsistencies and reclaim unused space.

The operation is intended for validation and postmortem analysis. It can hold a database writer lock while checking file references and should not be assumed to have negligible overhead.

The library also exposes cache statistics, estimated volume, culling operations, and configurable settings.

This provides a useful maintenance surface without requiring applications to directly manipulate the underlying SQLite tables.

### 10.3 Connection lifecycle and process creation

A cache maintains SQLite connections for threads that use it.

The fork improves connection cleanup and supports process forking by ensuring child processes use their own connections rather than inheriting active connections unsafely.

`close()` closes the calling thread's connection and connections associated with exited threads; connections belonging to other active threads remain in use until their owners close them or the cache object is collected.

Transactions must not be shared between threads, and forking within a transaction is unsupported.

The documentation also notes a macOS-specific limitation when Python links against the system SQLite library: using `spawn` avoids the unsafe fork interaction.

An ordinary `Cache` can be used as a context manager. However, closing a cache does not delete its storage directory; permanent cleanup requires removing the directory separately.

### 10.4 Filesystem and deployment boundaries

DiskCache relies on SQLite filesystem locking and WAL behavior.

The project specifically warns against assuming safe behavior on NFS and certain shared-folder systems.

Its normal architecture is therefore best understood as a local-filesystem coordination and caching layer.

The fact that many processes can access one directory does not make that directory a distributed network service.

Further, if a disk fills up, writes can raise `sqlite3.OperationalError`. Even seemingly read-oriented operations may encounter errors if they update statistics or eviction metadata.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#caveats](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#caveats)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



## 11. Framework and ecosystem integration

### 11.1 DjangoCache

`diskcache_community.DjangoCache` implements a Django-compatible cache backend using the `FanoutCache` architecture.

```
CACHES = {    "default": {        "BACKEND": "diskcache_community.DjangoCache",        "LOCATION": "/var/tmp/django-cache",        "TIMEOUT": 300,        "SHARDS": 8,        "DISK": "diskcache_community.SafeDisk",        "OPTIONS": {            "size_limit": 4 * 1024**3,        },    },}
```

The integration supports Django's caching interface, including versioned keys, standard cache timeouts, grouped cache operations, and memoization-related functionality.

It also offers DiskCache-specific facilities such as file-backed reads.

The `DISK` option is a community-fork extension enabling an explicitly selected serialization implementation.

`DjangoCache` inherits important `FanoutCache` limitations, including lack of a transaction spanning all shards.

The backend generally suppresses database timeout exceptions, although its methods default to retrying relevant timeouts.

An additional compatibility consideration is that ordinary Django cache usage may involve arbitrary model instances, response objects, or custom Python classes. These may be rejected by plain `SafeDisk` unless an appropriate restricted serializer is configured.

Source: [https://diskcache-community.readthedocs.io/en/latest/tutorial.html#djangocache](https://diskcache-community.readthedocs.io/en/latest/tutorial.html?utm_source=chatgpt.com#djangocache)

### 11.2 Coexistence with the upstream distribution

From 5.8.0 onward, the fork uses its own `diskcache_community` namespace.

Both packages may therefore be installed in one environment:

```
import diskcacheimport diskcache_community
```

This is useful when different dependencies have not adopted the community fork.

However, their Python objects are not interchangeable merely because the APIs resemble one another.

A `diskcache_community.Cache` is not an instance of the upstream `diskcache.Cache`, and the packages define separate exception classes.

This matters for dependencies that perform explicit type checks.

The migration guide identifies Dash's `DiskcacheManager` as an example of an integration that expects the original package's cache class. Installing the community fork does not automatically redirect that dependency to use it.

The practical distinction is between storage compatibility and runtime class/API integration. The former is deliberately preserved; the latter requires the consuming library to import and use the intended distribution.

Source: [https://diskcache-community.readthedocs.io/en/latest/migrating.html](https://diskcache-community.readthedocs.io/en/latest/migrating.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.5 documentation



### 11.3 Process-wide serializer configuration

The fork also provides `configure()` and `default_disk()`.

```
import diskcache_community as dcdc.configure(dc.SafeDisk)
```

The default can alternatively be selected using:

```
DISKCACHE_DISK=safe python application.py
```

The precedence is:

1. Explicit `disk=` argument.
2. `configure()` selection.
3. `DISKCACHE_DISK` environment variable.
4. Default `Disk`.

Additional environment variables, `DISKCACHE_SAFE_TYPES` and `DISKCACHE_SAFE_MODULES`, can extend the allowlist for compatible safe serializers.

This mechanism is particularly useful when a library creates its own `diskcache_community` cache without exposing a serializer argument.

It does not affect libraries importing upstream `diskcache`, caches already constructed, or caches that explicitly select another serializer.

### 11.4 Asynchronous applications

DiskCache's normal API is synchronous.

It does not provide a native asynchronous SQLite execution interface equivalent to an `async` cache backend.

Operations can be dispatched through `asyncio.to_thread()` or an executor, but the SQLite and filesystem work still executes synchronously in the worker thread.

For occasional operations this can be a straightforward integration strategy. For high-concurrency async workloads, thread scheduling, connection lifetimes, contention, and cancellation semantics become additional concerns.

The library is not a substitute for an explicitly asynchronous distributed cache client where that architecture is required.

## 12. Performance evidence

The fork publishes a modern benchmark suite comparing it against original DiskCache 5.6.3, Memcached, Redis, LMDB, and other Python storage libraries.

The published benchmark run was performed on October 12, 2026 using diskcache-community 5.7.0, not the current 5.8.5 release. The project's PyPI description identifies an Apple M5 Pro machine.

This distinction matters because subsequent releases introduced further performance optimizations.

### 12.1 Published measurements

Upstream-reported measurements; not independently reproduced for this overview.

| Workload                              | diskcache-community 5.7.0 | Comparison                       |
| ------------------------------------- | ------------------------- | -------------------------------- |
| Classic mixed workload, median get    | 2.6 µs                    | Upstream DiskCache 5.6.3: 2.6 µs |
| Classic mixed workload, median set    | 19.2 µs                   | Upstream: 22.3 µs                |
| Classic mixed workload, median delete | 18.4 µs                   | Upstream: 20.5 µs                |
| 1 MiB value, median set               | 351.3 µs                  | Upstream: 676.4 µs               |
| Eight processes, `FanoutCache(8)`     | 291,478 ops/s             | Single `Cache`: 184,652 ops/s    |
| Eight threads, single `Cache`         | 188,028 ops/s             | `FanoutCache(8)`: 19,715 ops/s   |

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation+1

The thread-versus-process distinction is particularly revealing.

Sharding performed well for the multiprocess benchmark, but much worse for the multithreaded case in the same benchmark suite.

This reinforces that `FanoutCache` is not categorically faster than `Cache`. Its value depends on the workload's contention pattern, how shards are accessed, and overhead introduced by routing and synchronization.

### 12.2 Performance mechanisms rather than universal rankings

The most defensible conclusions from the implementation and measurements are:

Small cache reads: Native SQLite representations, indexes, connection reuse, and avoiding network round trips can make DiskCache very efficient.

Large values: File-backed storage separates large payload handling from ordinary database row retrieval.

Concurrent writes: Sharding can improve throughput when independent processes would otherwise contend on a single writer lock.

Large read-mostly datasets: LMDB may perform better. The published benchmark shows a 0.9 µs median LMDB read versus 3.2 µs for DiskCache on a 100,000-key working set with 95% hits.

Durability versus write latency: The LMDB comparison used defaults that synchronized data to disk more aggressively. Its much higher write latency is not a clean comparison of equally configured durability policies.

LRU/LFU: These eviction modes add write activity to reads, potentially changing the contention and throughput characteristics substantially.

The benchmark should therefore be treated as evidence about specific workload shapes, not as proof that DiskCache is universally faster than Redis, LMDB, or Memcached.

Source: [https://diskcache-community.readthedocs.io/en/latest/benchmarks.html](https://diskcache-community.readthedocs.io/en/latest/benchmarks.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://diskcache-community.readthedocs.io\&sz=32)

DiskCache 5.8.4 documentation



## 13. Important limitations and architectural distinctions

The following distinctions determine how far the library's capabilities can be extended.

| Dimension       | Native capability                                            | Boundary                                                                    |
| --------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Atomicity       | Individual operations and explicit `Cache` transactions      | No transaction across arbitrary `FanoutCache` shards                        |
| Persistence     | Disk-backed values across process lifetimes                  | Default settings do not guarantee every committed write survives power loss |
| Concurrency     | Thread- and process-safe access on supported filesystems     | No general distributed locking across remote hosts                          |
| Queuing         | Atomic persistent push/pull                                  | No built-in acknowledged delivery or redelivery protocol                    |
| Memoization     | Durable result caching and probabilistic early recomputation | No guaranteed exactly-once computation or automatic dependency tracking     |
| Serialization   | Custom `Disk`, safe serializers, NumPy support               | Serializer compatibility must be maintained between readers and writers     |
| Storage limits  | Size estimates, expiration, eviction, culling                | Not a strict physical disk quota                                            |
| Search          | Key lookup, ordering, tags                                   | Not a general SQL query, text search, or vector-search API                  |
| Async execution | Synchronous calls through worker threads                     | No native async cache engine                                                |
| Security        | Restricted deserialization with `SafeDisk`                   | Default pickle deserialization remains unrestricted                         |

These limitations do not diminish the library's utility; they identify where its native abstractions end.

For example, it can implement a persistent work queue, but it does not independently guarantee successful job completion. It can persist cached application objects, but it is not a schema-managed authoritative database. It can coordinate many local workers, but it is not a replacement for cross-machine consensus infrastructure.

## 14. Release evolution and maintenance considerations

The community fork's releases show a deliberate emphasis on compatibility while adding security and operational capabilities.

| Release | Main changes                                                                                                      |
| ------- | ----------------------------------------------------------------------------------------------------------------- |
| 5.7.0   | First community release; `SafeDisk`, stricter directory permissions, read-only caching, connection and fork fixes |
| 5.8.0   | Separate import namespace, configurable default disk, expanded type allowlists, unreadable-entry handling         |
| 5.8.1   | `py.typed` and API type stubs                                                                                     |
| 5.8.2   | `SafeJSONDisk`, NumPy serialization, read/write optimizations, Python 3.8 compatibility                           |
| 5.8.3   | Security restrictions and bug fixes discovered through downstream testing                                         |
| 5.8.4   | NumPy keys, broader NumPy data-type support, array serialization corrections                                      |
| 5.8.5   | Configurable SQLite filename through `Cache(dbname=...)`                                                          |

The release history is especially relevant to NumPy support. Some newer object representations cannot be decoded by older fork releases even though the main database schema remains compatible.

Version compatibility therefore has at least three dimensions: database schema, serialization representation, and Python-level API behavior.

The maintainers' security policy states that fixes are applied to the latest 5.x release rather than maintained across older release branches.

Sources:

[https://github.com/secondwindoss/diskcache-community/blob/master/CHANGELOG.md](https://github.com/secondwindoss/diskcache-community/blob/master/CHANGELOG.md?utm_source=chatgpt.com)

[https://github.com/secondwindoss/diskcache-community/blob/master/SECURITY.md](https://github.com/secondwindoss/diskcache-community/blob/master/SECURITY.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 15. Overall architectural significance

diskcache-community is distinctive because it combines several layers of functionality that are often implemented separately.

At the bottom is SQLite, which supplies transactions, locking, indexes, and a durable metadata store. The `Disk` abstraction adds Python-aware serialization and file-backed value storage. `Cache` builds a bounded key-value interface over those mechanisms.

`FanoutCache` then provides a concurrency-oriented sharding layer, while `Deque`, `Index`, memoization, and synchronization recipes reuse the same underlying storage and atomic operations.

The resulting composition supports several useful architectural patterns without introducing a separate service:

Persistent computational caches: Store expensive computation results, preserve them across process restarts, and apply expiration or group invalidation through tags.

Multiprocess processing systems: Share results, counters, task lists, and synchronization state across local workers using the same filesystem.

Read-only cache artifacts: Construct reference caches in advance, distribute them with an application or container, and query them without modifying the stored database.

Array-heavy Python workloads: Preserve selected NumPy arrays and structured results using restricted serialization rather than relying on unrestricted pickle loading.

Framework-level disk caching: Integrate persistent caching into Django while retaining control over sharding, serialization, and disk capacity.

The central tradeoff is that the library achieves broad functionality by building on SQLite and ordinary filesystem semantics, rather than introducing a separate networked storage engine.

This reduces operational complexity and can provide excellent local performance, but it also makes SQLite's filesystem, durability, and concurrency boundaries fundamental to the library's behavior.

### Final assessment

The most valuable aspects of diskcache-community extend beyond ordinary caching:

1. Atomic, persistent operations across processes provide a reusable coordination foundation.
2. Transactions and persistent collections allow richer local state management than conventional key-value cache interfaces.
3. Function memoization, tags, and stampede mitigation reduce the need for custom cache-management infrastructure.
4. Pluggable serialization, especially `SafeDisk.with_numpy`, enables structured and array-oriented caching while providing tighter security controls.
5. Read-only caches and configurable storage behavior make the library useful for reusable cache artifacts and constrained deployment environments.
6. The community fork's compatibility focus preserves much of the mature original implementation while addressing important operational and security shortcomings.

For systems whose shared state is naturally local to one machine and whose cache semantics permit bounded retention or recomputation, diskcache-community offers a particularly rich set of capabilities for its small dependency footprint.

Its primary limitations emerge when the system requires cross-host coordination, guaranteed message delivery, strict durable commits, sophisticated querying, or richer consistency guarantees than SQLite-backed caches and their supplied abstractions provide.

The key to using the library effectively is recognizing that it is simultaneously a cache, persistent collection layer, and local coordination toolkit, while remaining precise about which guarantees belong to each of those capabilities.