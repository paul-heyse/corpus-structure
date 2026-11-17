# **cachetools (Python) — Comprehensive Library Overview**

Research date: November 17, 2026 | Target version: 8.0.0 | Python 3.11–3.15 | MIT License

## **1. Executive overview**

`cachetools`**&#x20;is an extensible, pure-Python caching library that combines size-bounded mutable mappings, configurable eviction algorithms, time-based expiration, and function/method memoization.**

Its principal advantage over Python's standard `functools.lru_cache` is the separation of three concerns:

1. **Storage and eviction policy:** Which cached entries are retained, how capacity is measured, and which entries are removed under pressure.
2. **Cache identity and lifecycle:** How function arguments are transformed into keys, where cached results live, and how entries are invalidated or expired.
3. **Computation and concurrency:** How cached functions are executed, how access is synchronized, and whether concurrent callers can share an in-progress computation.

The underlying cache classes implement `collections.abc.MutableMapping`. Consequently, caches can be used independently as ordinary mappings or composed with decorators that turn function calls into cache lookups.

This architecture permits capabilities that are difficult to achieve with a conventional `@lru_cache` alone: weighted memory budgets, value-dependent expiration, custom eviction policies, explicit cache ownership, selective invalidation, and per-key suppression of redundant concurrent computations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **Version baseline**

The current stable major release is **8.0.0**, published on November 7, 2026. Version 7.3.2 was subsequently published on November 14 as part of the older release line, but is not the latest major version.

Version 8.0.0 raises the minimum Python version to 3.11 and introduces several API and decorator changes. These are important when interpreting older examples or integrating with reflection and instrumentation frameworks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Official documentation: `https://cachetools.readthedocs.io/en/stable/`

PyPI: `https://pypi.org/project/cachetools/`

Source repository: `https://github.com/tkem/cachetools`

### **Capability map**

| Capability family         | Primary APIs                                          | Principal function                                                                      |
| ------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Bounded storage           | `Cache`, `getsizeof`, `maxsize`, `currsize`           | Enforce entry-count or weighted capacity limits                                         |
| Eviction policies         | `FIFOCache`, `LFUCache`, `LRUCache`, `RRCache`        | Control which entries leave under capacity pressure                                     |
| Time-based validity       | `TTLCache`, `TLRUCache`, `expire`                     | Make entries inaccessible after fixed or calculated deadlines                           |
| Function caching          | `cached`                                              | Memoize synchronous functions using an independently selected mapping                   |
| Object-method caching     | `cachedmethod`                                        | Support per-instance caches, dynamically selected storage, and method-specific controls |
| Cache-key construction    | `hashkey`, `methodkey`, `typedkey`, `typedmethodkey`  | Define argument identity and cache-sharing behavior                                     |
| Compatibility decorators  | `cachetools.func`                                     | Provide thread-safe, `functools.lru_cache`-style caching interfaces                     |
| Concurrency coordination  | `lock`, `condition`                                   | Synchronize cache access and suppress duplicate in-flight work                          |
| Observability and control | `CacheInfo`, `cache_info`, `cache_clear`, `cache_key` | Inspect usage, invalidate entries, and manage cache state                               |
| Extensibility             | Subclassing, `popitem`, `expire`, custom mappings     | Implement specialized policies and lifecycle hooks                                      |

The most consequential architectural distinction is that **the cache policy is not intrinsically coupled to the computation being cached**. A cache can be supplied, shared, inspected, replaced, extended, or manipulated independently of the decorated callable.

## **2. Cache storage, capacity, and eviction**

### **2.1.&#x20;**`Cache`**: the underlying storage abstraction**

`cachetools.Cache` is a bounded mutable mapping and the superclass of all built-in cache implementations.

```
Cache(maxsize, getsizeof=None)
```

Its principal properties and operations are:

| Interface            | Semantics                                                  |
| -------------------- | ---------------------------------------------------------- |
| `maxsize`            | Configured maximum aggregate cache size                    |
| `currsize`           | Current aggregate size, according to `getsizeof`           |
| `getsizeof(value)`   | Calculates the size charged for each value                 |
| `cache[key]`         | Retrieves a cached value, or raises `KeyError`             |
| `cache[key] = value` | Inserts or replaces an entry, evicting others if necessary |
| `del cache[key]`     | Explicitly removes an entry                                |
| `popitem()`          | Removes an entry according to the cache's eviction policy  |
| `clear()`            | Removes cached entries                                     |
| `__missing__(key)`   | Optional subclass-defined behavior for missing keys        |

On insertion, `Cache.__setitem__` calls `popitem()` repeatedly until the new value fits. This is important for weighted caches: storing one large value may evict several existing entries.

`Cache` itself is a usable mapping, not merely an abstract interface. Its default eviction behavior is arbitrary rather than optimized for recency or frequency.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **2.2. Capacity can represent much more than entry count**

By default:

\\[ \operatorname{getsizeof}(v)=1 \\]

Therefore:

\\[ \operatorname{currsize}=|\text{cache}| \\]

A custom `getsizeof` changes the meaning of capacity:

\\[ \operatorname{currsize}=\sum\_{k\in\text{cache}}\operatorname{getsizeof}(v_k) \\]

The insertion condition becomes:

\\[ \operatorname{currsize}+\operatorname{getsizeof}(v\_{\mathrm{new}}) \leq\operatorname{maxsize} \\]

For example, a cache can enforce an approximate 512 MiB budget for NumPy arrays using their payload sizes:

```
from cachetools import LRUCachearrays = LRUCache(    maxsize=512 * 1024 * 1024,    getsizeof=lambda array: array.nbytes,)
```

This is illustrative, not a measured implementation. It counts NumPy array payload bytes, not necessarily their complete resident-memory footprint.

**The important capability is user-defined resource accounting.** A cache can represent serialized bytes, memory estimates, weighted computational cost, or another nonnegative quantity, rather than simply a number of objects.

Important constraints:

- `getsizeof` receives the **value**, not the key.
- It is called at insertion or replacement, not continuously.
- Mutating a cached object does not automatically update its accounted size.
- A value larger than `maxsize` raises `ValueError`.
- Negative item sizes and negative `maxsize` are rejected.
- `maxsize=math.inf` allows effectively unbounded capacity.
- Zero-weight entries do not consume the configured budget, so a weight budget alone may not constrain their number.

This makes size-aware caching valuable when result sizes differ substantially, but the sizing function must be chosen carefully. Neither `len(value)` nor `sys.getsizeof(value)` universally represents retained process memory. Keys, eviction metadata, referenced objects, and external allocations can all contribute additional consumption.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+2



### **2.3. Eviction policies**

The library implements four principal non-time-based policies, all inheriting from `Cache`.

| Policy      | Eviction criterion        | Relevant behavior                                    |
| ----------- | ------------------------- | ---------------------------------------------------- |
| `FIFOCache` | Oldest inserted entry     | Overwriting an entry moves it to the newest position |
| `LFUCache`  | Least frequently accessed | Ties are resolved by least-recently-used order       |
| `LRUCache`  | Least recently used       | Reads and writes influence recency                   |
| `RRCache`   | Randomly selected entry   | Replacement selection can be customized              |

All accept `maxsize` and optional `getsizeof`; `RRCache` additionally accepts `choice`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



#### **FIFO: insertion-order eviction**

```
FIFOCache(maxsize, getsizeof=None)
```

FIFO retains entries based on when they were added, rather than how useful they have subsequently been.

A subtle but documented behavior is that **overwriting an existing key counts as reinsertion**. Its position in the eviction order is reset.

FIFO is useful when insertion order corresponds reasonably well to retention priority or when a policy should not reward repeated reads.

It does not implement time-based freshness. An entry can remain cached for an arbitrarily long period if capacity pressure does not remove it.

#### **LFU: frequency-based retention**

```
LFUCache(maxsize, getsizeof=None)
```

LFU tracks access frequency and preferentially retains frequently requested values.

In version 8.0, ties are broken using recency: among entries with the same access count, the least recently used is evicted first. This change originated in version 7.3.

Inserting and updating an entry also count as uses.

This implementation provides an exact LFU-style policy rather than an approximate popularity estimator. Such a policy is useful when access frequency predicts future reuse, but it can retain previously popular entries even after their relevance has declined.

The public API does not expose configurable frequency aging, a TinyLFU admission filter, or a separate frequency-decay policy. Those would require additional mechanisms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



#### **LRU: recency-based retention**

```
LRUCache(maxsize, getsizeof=None)
```

LRU discards entries that have gone longest without use.

Its principal advantage is adaptation to changing working sets. Recently requested results remain candidates for reuse, whereas older results gradually lose their priority.

LRU does not track computational cost, frequency over the entire cache lifetime, or the predicted value of future reuse. A large one-time scan can displace a useful working set.

The combination of **LRU plus custom&#x20;**`getsizeof` is more interesting than either feature individually: eviction is ordered by access recency, while admission and eviction pressure are governed by weighted capacity.

#### **Random replacement**

```
RRCache(    maxsize,    choice=random.choice,    getsizeof=None,)
```

Random replacement delegates victim selection to `choice`, which accepts a nonempty sequence of candidate keys and returns one key.

This provides an unusual extension point without requiring a new cache subclass. For example, a deterministic choice function can make victim selection reproducible in tests, while a specialized selector can implement another candidate-selection heuristic.

`RRCache.choice` exposes the configured selector.

Random replacement does not maintain historical recency or frequency priorities. It may be useful where that bookkeeping is undesirable, although its effectiveness depends strongly on the workload.

The implementation also maintains an additional sequence of keys for replacement selection. This trades extra metadata for more efficient random candidate selection.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **2.4. Policy choice is orthogonal to capacity accounting**

The interaction between policy and `getsizeof` is particularly consequential:

| Workload characteristic                  | Relevant native capability  | Tradeoff                                     |
| ---------------------------------------- | --------------------------- | -------------------------------------------- |
| Strong temporal locality                 | `LRUCache`                  | May suffer under large sequential scans      |
| Stable, repeatedly popular items         | `LFUCache`                  | Historical popularity can become stale       |
| Retention based on insertion sequence    | `FIFOCache`                 | Does not reward repeated access              |
| Low-policy-complexity replacement        | `RRCache`                   | Useful entries may be evicted randomly       |
| Highly variable result sizes             | Any policy with `getsizeof` | Requires credible size estimates             |
| Mixed freshness and recency requirements | `TTLCache` or `TLRUCache`   | Expiration metadata and cleanup add overhead |

Crucially, **eviction and expiration are distinct operations**. An entry may be evicted while still valid because capacity is exhausted, or it may expire while ample capacity remains.

That distinction governs the two time-aware cache classes.

## **3. Time-aware caching and expiration**

The most distinctive time-aware facilities are `TTLCache` and `TLRUCache`.

Both combine expiration with LRU replacement, but differ fundamentally in how expiration deadlines are established.

### **3.1.&#x20;**`TTLCache`**: uniform time-to-live**

```
TTLCache(    maxsize,    ttl,    timer=time.monotonic,    getsizeof=None,)
```

Each insertion establishes a deadline:

\\[ t\_{\mathrm{expires}}=t\_{\mathrm{insert}}+\mathrm{ttl} \\]

An entry is valid while:

\\[ \operatorname{timer}()\<t\_{\mathrm{expires}} \\]

For example:

```
from cachetools import TTLCachecache = TTLCache(    maxsize=1000,    ttl=300,)
```

Every inserted entry receives a five-minute lifetime.

**TTL expiration is measured from insertion or replacement, not from the last read.** Accessing an entry changes its LRU position but does not extend its deadline.

This distinguishes `TTLCache` from sliding-expiration caches that reset an idle timeout after each access.

#### **Non-numeric timers and expiration domains**

The timer interface is more flexible than a simple integer or floating-point timestamp.

For example:

```
from datetime import datetime, timedeltafrom cachetools import TTLCachecache = TTLCache(    maxsize=100,    ttl=timedelta(hours=12),    timer=datetime.now,)
```

The required relationship is that `timer() + ttl` produces an expiration value comparable with subsequent results of `timer()`.

This supports datetime-based deadlines, controlled virtual time, and other ordered time domains.

The default `time.monotonic` is generally more appropriate for elapsed-time expiration than wall-clock time because it avoids discontinuities caused by clock adjustments.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **3.2.&#x20;**`TLRUCache`**: value-dependent expiration**

```
TLRUCache(    maxsize,    ttu,    timer=time.monotonic,    getsizeof=None,)
```

Rather than assigning a common duration, `TLRUCache` calls:

```
ttu(key, value, now)
```

The return value is an **absolute expiration deadline in the timer's time domain**.

For example:

```
from cachetools import TLRUCachedef expiration(key, result, now):    return now + result.valid_for_secondscache = TLRUCache(    maxsize=1000,    ttu=expiration,)
```

This permits cache lifetimes to depend on entry characteristics, such as freshness metadata, result category, or source-specific validity periods.

The important distinction is that `ttu` is called at insertion time. It is not a continuously evaluated callback or a sliding-expiration mechanism.

An entry whose calculated deadline is already expired is not retained; when the key already exists, the old cached value is removed.

Potential uses include:

- Retaining responses according to server-provided expiration information.
- Assigning different lifetimes to different result categories.
- Honoring business-domain validity deadlines.
- Rejecting cache admission for values that are already stale.
- Combining custom expiration with weighted capacity limits.

The ability to derive validity from the cached value itself is a meaningful advantage over decorators that accept only a single constant TTL.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **3.3. Expiration is lazy, but expired values are inaccessible**

For both timed caches, an expired item is no longer considered a cache hit. However, the underlying object may remain physically retained until cleanup occurs.

Relevant operations include:

| Operation            | Behavior                                                  |
| -------------------- | --------------------------------------------------------- |
| `cache[key]`         | Expired entry behaves as missing                          |
| `key in cache`       | Returns `False` for expired entries                       |
| `cache[key] = value` | Triggers expiration cleanup                               |
| `cache.expire()`     | Removes expired entries and returns their key-value pairs |
| `cache.expire(time)` | Removes entries expired by the supplied time              |
| `len(cache)`         | Triggers cleanup                                          |
| `cache.currsize`     | Triggers cleanup before reporting size                    |
| `repr(cache)`        | Triggers cleanup before representation                    |
| `cache.popitem()`    | Clears expired entries before choosing an LRU victim      |

These behaviors are supported by the version 8 implementation. In particular, even apparently observational operations such as querying `len(cache)` or `currsize` can perform cleanup work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



#### `expire()`**&#x20;is also a lifecycle hook**

```
expired = cache.expire()
```

The return value contains the expired `(key, value)` pairs removed by that call.

This enables explicit cleanup at controlled points, such as after a processing batch or during a scheduled maintenance operation.

It also enables instrumentation of expiration events without reimplementing expiration tracking.

However, expiration is not proactive: `cachetools` does not independently run a background timer or cleanup thread. If no suitable operation occurs, expired objects may continue occupying memory.

This is a distinction between **logical cache validity** and **physical memory reclamation**.

### **3.4. Expiration data structures and their implications**

The two timed caches use different internal organization.

`TTLCache` maintains LRU bookkeeping and expiration links. Because all entries receive the same TTL, expiration order can follow insertion/update order, allowing expired entries to be removed efficiently from the oldest end.

`TLRUCache` uses an `OrderedDict` for LRU behavior and a min-heap for expiration ordering. This is necessary because value-dependent expiration deadlines need not follow insertion order.

When entries are replaced or removed, old heap records are marked as removed rather than immediately deleted from the middle of the heap. The implementation periodically rebuilds the heap to discard these obsolete records.

These are implementation details rather than public complexity guarantees, but they explain important qualitative differences:

- `TTLCache` is simpler when all entries share the same lifetime.
- `TLRUCache` supports nonuniform deadlines at the cost of additional heap maintenance.
- Workloads with frequent replacements can create additional expiry-bookkeeping work in `TLRUCache`.
- Both caches incur expiration checks and metadata overhead beyond ordinary LRU storage.

The internal timer context also freezes time during nested cache operations, giving related checks a consistent timer value within an operation. This is useful for deterministic behavior around expiration boundaries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### **3.5. What timed caches do not implement**

Neither timed cache provides an automatic background refresh, stale-while-revalidate policy, or stale-if-error fallback.

A cache miss after expiration invokes whatever retrieval logic the caller or memoization decorator supplies.

Likewise, there is no native sliding inactivity timeout that updates expiration on every read. A specialized subclass or a wrapper that reinserts accessed values would be required, with associated changes to write frequency and concurrency behavior.

The library therefore provides **freshness-based invalidation**, not a full cache-refresh or revalidation system.

## **4. Function memoization and cache composition**

The `cached` decorator is the main integration layer between arbitrary synchronous computations and cache storage.

### **4.1.&#x20;**`cached`**: externally supplied cache storage**

```
@cachetools.cached(    cache,    key=cachetools.keys.hashkey,    lock=None,    condition=None,    info=False,)
```

A cached invocation conceptually follows this sequence:

**Function arguments**

**Generate cache key**

**Look up key in cache mapping**

CACHE HIT

Return stored result and update policy metadata as applicable

CACHE MISS

Execute function, attempt admission, return result

Optional synchronization operates around cache access and in-flight computation coordination.

Unlike decorators that allocate and own their cache internally, `cached` accepts a caller-created object.

For example:

```
from cachetools import cached, LRUCacheresults = LRUCache(maxsize=500)@cached(cache=results)def compute(x, y):    return expensive_operation(x, y)
```

The cache can subsequently be inspected, mutated, cleared, or shared with other functions.

The mapping does not need to be a `cachetools.Cache`. The official documentation explicitly supports ordinary dictionaries and `weakref.WeakValueDictionary` instances.

This makes the decorator a general mapping-based memoization adapter. It is not intrinsically tied to any one eviction policy or to even having an eviction policy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **4.2. Non-**`Cache`**&#x20;mappings and alternative ownership models**

Several useful configurations follow directly from accepting arbitrary mutable mappings.

| Storage configuration  | Behavior                                                            |
| ---------------------- | ------------------------------------------------------------------- |
| `dict`                 | Unbounded memoization unless manually controlled                    |
| `LRUCache`             | Bounded memoization with recency eviction                           |
| `TTLCache`             | Bounded memoization with expiration                                 |
| `WeakValueDictionary`  | Values can disappear when no strong references remain               |
| Custom mutable mapping | Delegate caching storage and policy to application-defined behavior |

Weak-reference caching is particularly interesting for object-heavy applications.

A weak-value mapping avoids keeping an object alive solely because it appears in the cache. However, values must support weak references, and entries can disappear between accesses as garbage collection occurs.

This offers **lifetime-sensitive retention** rather than conventional capacity-bounded retention. It is distinct from the explicit expiration offered by timed caches.

An arbitrary custom mapping may also provide another storage abstraction, but `cachetools` does not automatically make such mappings thread-safe, persistent, or distributed.

### **4.3. Shared caches across multiple functions**

Multiple functions can use the same mapping.

```
from functools import partialfrom cachetools import LRUCache, cachedfrom cachetools.keys import hashkeyshared = LRUCache(maxsize=1000)@cached(shared, key=partial(hashkey, "feature_a"))def feature_a(x):    return compute_a(x)@cached(shared, key=partial(hashkey, "feature_b"))def feature_b(x):    return compute_b(x)
```

The namespaces `"feature_a"` and `"feature_b"` prevent calls with identical argument values from colliding.

The result is a common capacity budget across multiple computations.

This enables two useful architectural properties:

**Shared resource governance.** Multiple functions compete for the same cache capacity, rather than independently retaining their maximum allotments.

**Independent memoization identity.** Each function can have its own key namespace while using the same eviction algorithm and storage lifetime.

A shared cache does not inherently partition capacity fairly. One high-volume function can evict entries belonging to another. If independent quotas or priorities are necessary, the built-in shared mapping does not enforce them.

The official documentation explicitly demonstrates namespaced shared caches using `functools.partial` and `hashkey`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **4.4. Cache-key construction**

The `cachetools.keys` module provides four principal key functions.

| Key function                            | Key includes `self`? | Separates argument types? |
| --------------------------------------- | -------------------- | ------------------------- |
| `hashkey(*args, **kwargs)`              | If passed explicitly | No                        |
| `typedkey(*args, **kwargs)`             | If passed explicitly | Yes                       |
| `methodkey(self, *args, **kwargs)`      | No                   | No                        |
| `typedmethodkey(self, *args, **kwargs)` | No                   | Yes                       |

All produce hashable tuple-like keys when their constituent values are hashable.

`typedkey` distinguishes values such as `3` and `3.0`, which may otherwise compare equal and have equal hashes. This matters when the function's behavior depends on input type.

Keyword arguments are incorporated into the generated key with deterministic ordering. However, positional and keyword forms are not automatically canonicalized against the function signature.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



#### **Argument equivalence is not semantic equivalence**

Consider:

```
@cached(LRUCache(maxsize=100))def f(a=1):    return expensive_operation(a)
```

The calls below may occupy three different cache entries:

```
f()f(1)f(a=1)
```

All compute the same logical argument, but their supplied argument representations differ.

This is an important issue for applications that need canonical memoization.

A custom key function can use `inspect.signature(...).bind(...).apply_defaults()` or another explicit normalization strategy before constructing a key.

Such canonicalization is not performed automatically by the built-in key functions.

#### **Handling unhashable inputs**

Ordinary dictionaries, lists, arrays, and other mutable containers generally cannot be used directly as hashable cache-key components.

The key callback can transform them into stable hashable representations.

For example, a dictionary containing hashable elements may be transformed into a sorted tuple of items.

For arrays, an application might use an immutable content digest together with shape and dtype information, provided this corresponds to the desired semantics.

The key design must account for mutation, normalization, and accidental collisions. The library does not provide a general serialization-based content-addressing system.

#### **Key functions can define semantic cache identity**

Custom keys are not limited to making arguments hashable. They can also encode:

- Explicit namespaces for shared caches.
- Version identifiers for algorithm or data revisions.
- Selected subsets of function arguments.
- Canonicalized configuration representations.
- Input content digests.
- Domain-specific equivalence relationships.

This can eliminate the need for a separate invalidation layer when a changed input version naturally produces a new cache key.

The distinction is important: `cachetools` provides **key construction hooks**, but it does not establish whether two inputs are semantically equivalent. That remains the key function's responsibility.

### **4.5. Exception behavior and negative caching**

By default, a function invocation that raises an exception is not cached.

Consequently, repeated calls that fail will generally repeat the underlying computation.

The library documentation describes a pattern for caching selected failures: catch specific exceptions inside the memoized function, return them as ordinary results, and raise them again in an outer wrapper.

This is a form of **negative caching**.

It can be useful for repeatable failures such as a known missing resource, although transient failures usually require a short expiration or should remain uncached.

Returning `None` normally is different from raising an exception: `None` is a valid cache value.

The decorator also handles insertion failures due to an oversized value by returning the computed value without retaining it. Thus, ordinary memoization need not fail simply because a result exceeds its configured size budget. This specific behavior applies to the built-in cache's `ValueError` admission path; it should not be generalized to arbitrary failures from custom mappings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **4.6.&#x20;**`cachedmethod`**: explicit per-instance cache ownership**

```
@cachetools.cachedmethod(    cache,    key=cachetools.keys.methodkey,    lock=None,    condition=None,    info=False,)
```

Unlike `cached`, the `cache`, `lock`, and `condition` arguments are callable accessors receiving the instance.

```
from cachetools import LRUCache, cachedmethodclass Processor:    def __init__(self, capacity):        self.cache = LRUCache(maxsize=capacity)    @cachedmethod(lambda self: self.cache)    def transform(self, item):        return expensive_transform(item)
```

This design allows each instance to own an independent cache.

Importantly, the cache accessor is evaluated when the method is used, enabling the instance to replace its cache without redefining the decorated method.

```
processor.cache = LRUCache(maxsize=2000)
```

Subsequent calls use the replacement mapping.

`cachedmethod` can also reference a shared cache, but then the developer must construct keys that distinguish the relevant methods and, where appropriate, instances.

#### **Why&#x20;**`methodkey`**&#x20;excludes&#x20;**`self`

The default `methodkey` deliberately ignores the receiver.

This enables caching for instances that are unhashable, and is natural when the cache itself is already scoped to the instance.

However, if multiple instances share one cache, ignoring `self` can produce incorrect cross-instance hits.

Using `hashkey` to include the receiver is an available alternative, provided the instance is hashable and its identity or equality semantics are suitable.

#### **Descriptor behavior and instance requirements**

Since version 7.0, `cachedmethod` has been implemented using descriptors. Version 8.0 makes previously deprecated restrictions mandatory:

- Instances require a mutable `__dict__`.
- Classes using `__slots__` without a suitable `__dict__` are incompatible.
- Decorating `classmethod` with `cachedmethod` is no longer supported.
- Descriptors assigned after class creation without normal descriptor initialization can raise `TypeError`.

These restrictions matter for slotted dataclasses, dynamic class generation, descriptor composition, and frameworks that construct or modify classes after their definition.

Access through an instance exposes the cache-management attributes and optional statistics. Access through the class remains possible, but does not expose the same instance-bound controls.

The implementation also resets per-instance hit/miss statistics when decorated instances are pickled and restored or deep-copied.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+2



## **5. Concurrency, synchronization, and cache stampedes**

`cachetools` distinguishes synchronized access to cache storage from synchronization of the computation being cached.

This is one of its more important advanced capabilities.

### **5.1. Cache classes are not inherently thread-safe**

The built-in cache mappings are explicitly documented as not thread-safe.

Concurrent modifications can affect both the stored values and the eviction bookkeeping, so sharing a cache across threads requires coordination.

The `cached` and `cachedmethod` decorators provide optional synchronization facilities, but an undecorated cache object does not acquire thread safety simply because it is a `Cache` instance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **5.2.&#x20;**`lock`**: protect shared cache state**

A `lock` is used around cache accesses.

```
import threadingfrom cachetools import cached, LRUCachelock = threading.RLock()@cached(    cache=LRUCache(maxsize=1024),    lock=lock,)def calculate(x):    return expensive_calculation(x)
```

The important implementation behavior is that **the wrapped computation executes outside the cache lock**.

This permits different cache misses to compute concurrently without forcing all computation through a single critical section.

However, two threads can simultaneously miss on the same key and execute the same computation.

A lock therefore protects the mapping and its internal structures, but does not necessarily eliminate redundant work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **5.3.&#x20;**`condition`**: coordinate identical in-flight computations**

The optional `condition` parameter addresses this redundant-work problem.

```
import threadingfrom cachetools import cached, LRUCachelock = threading.RLock()condition = threading.Condition(lock)@cached(    cache=LRUCache(maxsize=1024),    lock=lock,    condition=condition,)def calculate(x):    return expensive_calculation(x)
```

When multiple threads request the same absent key, the condition-based implementation coordinates them.

Concurrent calls for the same key

Thread A

Key = K

Thread B

Key = K

Thread C

Key = K

**Shared cache lookup and pending-key coordination**

Computes K

Outside cache lock

Waits

Pending K

Waits

Pending K

**Store result, clear pending state, notify waiters**

Waiting callers can retrieve the newly cached result.

This is an in-process form of **single-flight coordination**.

It is especially valuable when cache misses are expensive and heavily concurrent, such as repeated queries, model inference requests, or expensive data transformations.

The mechanism is scoped by cache key. Different keys can still compute concurrently.

There are several important qualifications:

- If a computation raises or its result cannot be cached, the waiting callers cannot simply obtain a successful stored result. Subsequent execution may be necessary.
- A lock and condition supplied separately must refer to the same underlying synchronization lock.
- Reentrant computation of the same pending key can create a waiting cycle; the condition mechanism should not be assumed to handle recursive same-key calls safely.
- This is synchronization within the Python process, not a distributed single-flight protocol.
- `cache_clear()` does not, by itself, cancel computations already in progress.

Conditions can be supplied without a separate lock, provided the condition implements the context-manager protocol and can itself guard cache access.

The feature was introduced in cachetools 6.0 and remains documented in version 8.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **5.4. Concurrency models compared**

| Configuration                      | Cache synchronization                  | Duplicate concurrent work  |
| ---------------------------------- | -------------------------------------- | -------------------------- |
| Bare shared cache                  | Caller-managed                         | Caller-managed             |
| `@cached` without lock             | None provided                          | Possible                   |
| `@cached(lock=...)`                | Cache operations protected             | Still possible             |
| `@cached(condition=...)`           | Condition also guards cache            | Coordinates same-key work  |
| `@cached(lock=..., condition=...)` | Explicit associated lock and condition | Coordinates same-key work  |
| `cachetools.func` decorators       | Built-in thread synchronization        | Condition-based mitigation |

The use of condition variables has a coordination cost. It is not always beneficial when cache misses are cheap or contention is negligible.

Moreover, the decorator's synchronization guarantees do not make an inherently unsafe wrapped function thread-safe. The function may still be executed simultaneously for different keys.

## **6. The&#x20;**`cachetools.func`**&#x20;compatibility layer**

The `cachetools.func` module offers decorators modeled after `functools.lru_cache`.

Unlike the more general `cached` interface, these decorators allocate their own cache and provide a standardized API.

### **6.1. Supported decorators**

| Decorator    | Parameters                                                | Policy             |
| ------------ | --------------------------------------------------------- | ------------------ |
| `fifo_cache` | `maxsize=128, typed=False`                                | FIFO               |
| `lfu_cache`  | `maxsize=128, typed=False`                                | LFU                |
| `lru_cache`  | `maxsize=128, typed=False`                                | LRU                |
| `rr_cache`   | `maxsize=128, choice=random.choice, typed=False`          | Random replacement |
| `ttl_cache`  | `maxsize=128, ttl=600, timer=time.monotonic, typed=False` | TTL + LRU          |

Each also supports direct decoration of a callable, using default parameters where applicable.

For example:

```
from cachetools.func import lfu_cache, ttl_cache@lfu_cache(maxsize=2048)def analyze(value):    return expensive_analysis(value)@ttl_cache(maxsize=512, ttl=120)def lookup(identifier):    return fetch_resource(identifier)
```

All `cachetools.func` decorators are documented as thread-safe, and the implementation has used condition-based cache-stampede mitigation since version 6.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **6.2. Differences from&#x20;**`functools.lru_cache`

The compatibility API includes:

- `cache_info()` for statistics.
- `cache_clear()` to clear cached results.
- `cache_parameters()` for configuration introspection.
- `typed=True` to distinguish argument types.
- `maxsize=None` to disable the capacity limit.

With `ttl_cache(maxsize=None)`, expiration remains active even though the entry-count limit is removed.

The `cache_parameters()` result is informational. Modifying the returned dictionary does not reconfigure the cache.

Unlike `cached`, the compatibility decorators do not expose `getsizeof` as a decorator parameter. They are oriented toward entry-count limits, not custom weighted budgets.

Likewise, there is no corresponding built-in `cachetools.func.tlru_cache` documented in version 8.0. A `TLRUCache` can instead be supplied to `cached`.

These distinctions make `cachetools.func` convenient for familiar function-level memoization, while `cached` is more flexible when cache identity, resource accounting, or ownership must be controlled independently.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **6.3. Comparison with standard-library caching**

| Capability                          | `functools.lru_cache` | `cachetools.func`          | `cachetools.cached`   |
| ----------------------------------- | --------------------- | -------------------------- | --------------------- |
| LRU caching                         | Yes                   | Yes                        | Yes, with `LRUCache`  |
| FIFO/LFU/random replacement         | No                    | Yes                        | Yes                   |
| TTL expiration                      | No                    | Yes                        | Yes                   |
| Per-value expiration                | No                    | No direct facade           | Yes, with `TLRUCache` |
| Custom weighted capacity            | No                    | No direct parameter        | Yes                   |
| Caller-supplied mapping             | No                    | No                         | Yes                   |
| Custom cache-key callback           | No                    | No direct parameter        | Yes                   |
| Thread synchronization              | Yes                   | Yes                        | Optional              |
| Same-key single-flight coordination | Not guaranteed        | Condition-based mitigation | Optional condition    |
| Statistics                          | Built in              | Built in                   | Opt-in                |

The standard-library implementation remains attractive for conventional memoization because it provides a compact, well-integrated interface and uses a C-implemented wrapper on CPython.

`cachetools` provides greater control and a broader policy vocabulary, but its pure-Python implementation and additional bookkeeping can create more overhead for inexpensive functions.

No general speedup over `functools.lru_cache` should be inferred. The benefit depends on whether improved retention, expiration, or avoided computation outweighs the additional cache-management work.

For comparison, the Python standard-library reference is:

`https://docs.python.org/3/library/functools.html#functools.lru_cache`

## **7. Introspection, statistics, and invalidation**

### **7.1. Wrapper introspection**

For `cached`, the resulting callable exposes these attributes:

| Attribute or method | Purpose                                               |
| ------------------- | ----------------------------------------------------- |
| `cache`             | Access the underlying cache mapping                   |
| `cache_key`         | Access the argument-to-key function                   |
| `cache_lock`        | Access the configured synchronization lock            |
| `cache_condition`   | Access the configured condition variable              |
| `cache_clear()`     | Clear stored values, using configured synchronization |
| `cache_info()`      | Report hit/miss statistics when `info=True`           |
| `__wrapped__`       | Access the original undecorated callable              |

This is particularly useful because **selective invalidation can use exactly the same key construction as memoization**.

```
key = compute.cache_key(x, y)with compute.cache_lock:    compute.cache.pop(key, None)
```

The example assumes that `compute` was decorated with a non-`None` lock.

The explicit key accessor removes the need to duplicate internal key-generation logic in invalidation code.

For `cachedmethod`, similar facilities are exposed on the instance-bound method, including `cache_clear` and optional per-instance `cache_info`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **7.2.&#x20;**`CacheInfo`**&#x20;and statistics semantics**

With `info=True`:

```
@cached(LRUCache(maxsize=100), info=True)def calculate(x):    return x * xinfo = calculate.cache_info()
```

The returned public `CacheInfo` named tuple contains:

```
CacheInfo(    hits=...,    misses=...,    maxsize=...,    currsize=...,)
```

`CacheInfo` is a public API in version 8.0.

The meaning of `maxsize` and `currsize` depends on the mapping:

| Mapping                          | `maxsize`             | `currsize`            |
| -------------------------------- | --------------------- | --------------------- |
| Built-in `Cache` subclass        | Configured size limit | Current weighted size |
| Ordinary dictionary              | `None`                | Number of entries     |
| Other compatible mutable mapping | `None`                | `len(cache)`          |

Custom mappings must therefore support `len()` when used with `info=True`.

A useful distinction is that hit/miss counters describe the decorated callable, while `currsize` describes the underlying cache.

When multiple functions share one mapping, their hit/miss statistics can be separate even though each observes the same shared cache size.

For `cachedmethod`, statistics are per instance. This makes it possible to inspect memoization effectiveness across independently configured object instances without maintaining a separate metrics dictionary.

Statistics are opt-in for `cached` and `cachedmethod` because instrumentation adds overhead. In version 8.0, `cached` does not install a `cache_info=None` attribute when instrumentation is disabled.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation+1



### **7.3. Explicit invalidation versus expiration**

Several kinds of cache lifecycle control can be implemented without rewriting the cache:

| Required action                            | Native mechanism                            |
| ------------------------------------------ | ------------------------------------------- |
| Invalidate one memoized result             | `cache_key(...)` followed by `pop` or `del` |
| Invalidate all results                     | `cache_clear()`                             |
| Remove entries past a deadline             | `expire()`                                  |
| Prevent an old input version from matching | Include a version in the cache key          |
| Replace an instance's cache configuration  | Replace the mapping used by `cachedmethod`  |
| Inspect cache effectiveness                | `cache_info()`                              |
| Observe entry-count or weighted occupancy  | `len(cache)` / `currsize`                   |

One subtle concurrency limitation is that invalidating an entry does not necessarily invalidate an already running computation.

For example, clearing a cache while a cache miss is still executing does not, by itself, prevent that computation from inserting its result afterward.

If invalidation must provide strong generation or consistency guarantees, generation-aware keys or additional coordination may be necessary.

This follows from the separation between cache operations and execution of the underlying function.

## **8. Extension mechanisms and customized caching behavior**

`cachetools` exposes a relatively small set of extension surfaces, but their combinations are powerful.

### **8.1. Subclassing to observe or change eviction**

All built-in cache classes use `popitem()` to make space under capacity pressure.

A subclass can intercept eviction:

```
from cachetools import LRUCacheclass ObservedCache(LRUCache):    def popitem(self):        key, value = super().popitem()        self.on_eviction(key, value)        return key, value    def on_eviction(self, key, value):        pass
```

This enables eviction notifications, custom accounting, or release of associated resources.

For policies that need different access behavior, subclasses can also override `__getitem__`, `__setitem__`, and `__delitem__`.

This makes `Cache` a reusable foundation for specialized eviction algorithms rather than requiring a completely independent mutable-mapping implementation.

### **8.2. Distinguishing eviction, expiration, and explicit deletion**

Overriding `popitem()` is not a universal removal callback.

An entry can disappear through several paths:

| Removal mechanism         | `popitem()` involved?             | Relevant extension point     |
| ------------------------- | --------------------------------- | ---------------------------- |
| Capacity-driven eviction  | Yes                               | Override `popitem()`         |
| Timed expiration cleanup  | No                                | Override `expire()`          |
| Explicit key deletion     | No                                | Override `__delitem__`       |
| Bulk clearing             | Not through per-entry eviction    | Override `clear()` if needed |
| Weak-reference collection | Managed by weak-reference mapping | Mapping-specific behavior    |

This distinction is important for instrumentation and resource lifecycle management.

For example, a cache subclass that releases external resources only from `popitem()` will not necessarily release them when entries expire or are explicitly cleared.

An expiration-aware subclass can separately override `expire()`:

```
from cachetools import TTLCacheclass ObservedTTLCache(TTLCache):    def expire(self, time=None):        expired = super().expire(time)        for key, value in expired:            self.on_expiration(key, value)        return expired    def on_expiration(self, key, value):        pass
```

The library explicitly documents both eviction and expiration subclass hooks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **8.3.&#x20;**`__missing__`**: read-through cache behavior**

Subclasses can implement:

```
def __missing__(self, key):    ...
```

This supports a cache that loads a missing value itself and optionally stores it before returning.

It resembles `collections.defaultdict` behavior, but can implement expensive retrieval rather than merely constructing a default value.

The important qualification is that a cache with `__missing__` is no longer simply a passive mapping of previously stored results.

In fact, the official documentation warns that this may produce surprising behavior when combined with memoization decorators.

For example, a decorator may interpret a value loaded by `__missing__` as a cache hit, even if a separate retrieval operation occurred internally.

This capability is most natural when using the cache object directly as a read-through mapping, rather than wrapping another function that implements the same loading behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cachetools.readthedocs.io\&sz=32)

cachetools 8.0.0 documentation



### **8.4. Extension points beyond subclassing**

The library also supports customization through dependency injection and callbacks:

| Extension surface | What can be customized                 |
| ----------------- | -------------------------------------- |
| `getsizeof`       | Resource accounting                    |
| `choice`          | Random-replacement candidate selection |
| `timer`           | Time source and clock domain           |
| `ttu`             | Value-specific expiration deadline     |
| `key`             | Memoization identity                   |
| `cache`           | Storage implementation and ownership   |
| `lock`            | Cache synchronization                  |
| `condition`       | In-flight computation coordination     |
| `cache(self)`     | Dynamic per-instance cache lookup      |

These interfaces can frequently be combined without subclassing.

For example, a `TLRUCache` can use all of the following simultaneously: a custom memory budget, a value-dependent expiration function, and a controlled clock. Supplying that cache to `cached` then adds custom keying and optional concurrency coordination.

This illustrates the library's fundamental architectural strength: **composition of independently configurable cache concerns**.

There are limits to this composition. For example, using an LFU eviction policy with native per-item TTL behavior is not accomplished merely by passing parameters to an existing class. The built-in timed caches specifically use LRU replacement. A genuinely different combined policy requires custom implementation or careful subclassing.

## **9. Integration boundaries and architectural implications**

### **9.1. Asynchronous Python**

The standard `cachetools` memoization decorators are designed for synchronous functions.

Directly decorating an `async def` function with `cached` is problematic because calling an asynchronous function produces a coroutine object rather than its completed result.

Caching that coroutine object can result in a subsequent attempt to await an already-consumed coroutine.

This is an established limitation discussed in the upstream issue tracker. The version 8.0 public API does not document native asynchronous memoization decorators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



The separately maintained `asyncache` project offers asynchronous adapters around cachetools:

```
from asyncache import cachedfrom cachetools import TTLCache@cached(TTLCache(maxsize=1024, ttl=60))async def fetch_async(identifier):    return await retrieve(identifier)
```

The wrapper and cache policy come from different packages. `asyncache` provides the asynchronous memoization behavior; `cachetools` provides the underlying cache storage and expiration policy.

The original `asyncache` project has been described as unmaintained by downstream maintainers, so its maintenance status and compatibility with cachetools 8 should be verified before relying on it.

A separate asynchronous cache implementation may be preferable when concurrent task coordination, cancellation, asynchronous locking, and async storage are central requirements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Sources:

`https://github.com/hephex/asyncache`

`https://github.com/tkem/cachetools/issues/222`

### **9.2. Multiprocessing and distributed systems**

`cachetools` is fundamentally a local Python caching library.

Its built-in cache objects reside in the memory of the Python process that creates them. Separate processes do not automatically share their contents or synchronize eviction and invalidation.

Similarly, a `threading.Lock` or `threading.Condition` used by a decorator provides synchronization within a process; it does not establish coordination across multiple workers, processes, or machines.

A custom mutable mapping could delegate storage to another system, but the basic mapping interface does not automatically supply distributed atomicity, cross-process locking, serialization, or consistency guarantees.

This distinction matters when comparing cachetools with persistent or distributed caching systems.

### **9.3. Data processing, numerical arrays, and object retention**

For data-intensive Python applications, the important interaction is between cache ownership and memory accounting.

Potential applications include expensive parsing results, numerical transformations, compiled intermediate representations, query results, and reusable derived objects.

Several concerns remain with the caller:

**Large external allocations.** Objects backed by NumPy, PyTorch, Arrow, or other memory systems may hold allocations whose real retention cost differs from Python object size. A custom `getsizeof` can approximate the appropriate budget, but it cannot automatically discover and account for every external allocation.

**Mutable data.** Cached arrays, dictionaries, and other mutable values may be modified after insertion. This changes the logical result returned by later cache hits and may invalidate any previous size measurement.

**Shared references.** Two cache values may reference the same underlying memory. Counting both independently can overestimate unique retained storage; failing to count their backing objects can underestimate it.

**External resource ownership.** A cache holding objects associated with file handles, devices, or other resources may need explicit lifecycle handling. Cache eviction does not automatically implement arbitrary resource-release contracts.

The library's configurable size accounting and extension hooks are relevant to these problems, but they do not amount to a complete memory-management subsystem.

### **9.4. Key versioning and dependency-aware caching**

The library does not maintain a dependency graph of cached computations.

It cannot automatically infer that changing an upstream dataset, schema, model, or configuration invalidates a particular set of downstream cached results.

Nevertheless, key construction enables a useful alternative to global invalidation: encode relevant source versions or content identities into cache keys.

For example, a function's key could incorporate a schema version, input digest, or computation revision.

When that identity changes, the computation no longer matches the old cache entry.

This makes cachetools suitable as a **cache-policy and memoization layer beneath a separately defined dependency or content-identity system**, without making it a dependency-tracking engine itself.

The distinction between identity-based invalidation and explicit deletion is useful:

- Identity-based invalidation causes future calls to miss without requiring immediate removal of old entries.
- Explicit deletion reclaims or frees entries, but requires knowing which keys are affected.
- TTL can eventually remove stale entries, but does not determine whether source data has changed before the deadline.

These mechanisms can coexist.

## **10. Operational constraints and consequential limitations**

The following limitations are particularly important when treating cachetools as an architectural component rather than just a decorator package.

| Area              | Constraint or distinction                          | Consequence                                                                      |
| ----------------- | -------------------------------------------------- | -------------------------------------------------------------------------------- |
| Thread safety     | Built-in caches are not thread-safe                | Shared access requires synchronization                                           |
| Process sharing   | Built-in storage is process-local                  | No native cross-process cache coherence                                          |
| Async execution   | Core decorators are synchronous                    | Coroutine results need separate handling                                         |
| Freshness         | TTL is insertion-relative                          | No automatic sliding expiration                                                  |
| Refresh           | No built-in background revalidation                | Expired values require recomputation                                             |
| Error caching     | Exceptions are not cached automatically            | Repeated failures can repeat work                                                |
| Memory accounting | `getsizeof` is insertion-time accounting           | Mutation and shared memory complicate budgets                                    |
| Cache identity    | Default keys reflect call arguments                | Equivalent calls may generate distinct entries                                   |
| Invalidation      | No dependency tracking                             | Source changes require explicit keying or invalidation                           |
| Observability     | Built-in statistics are limited                    | Latency, eviction reasons, and memory metrics require additional instrumentation |
| Persistence       | No stable cross-version cache serialization format | Pickled caches cannot be relied upon across versions                             |
| Eviction          | Policy metadata adds overhead                      | Retention quality and runtime costs depend on workload                           |
| Admission         | No general independent admission-policy API        | Advanced admission strategies require custom logic                               |
| Combined policies | Timed caches use LRU                               | Native arbitrary combinations of eviction policies are unavailable               |

### **10.1. Persistence and pickling**

The official documentation states that the provided cache classes can generally be pickled, but that their serialized representation is an implementation detail.

Importantly, **cross-version unpickling compatibility is not guaranteed, even across bugfix releases**.

Consequently, pickled cache objects should not be treated as a stable durable storage format.

For durable storage, it is more appropriate to persist the underlying application data using a versioned serialization format and reconstruct cache state separately, rather than persist the internal eviction structures.

Source: `https://cachetools.readthedocs.io/en/stable/#cachetools.Cache`

### **10.2. Caching requires coherent function semantics**

Memoization is most straightforward when the result is determined by the cache key.

Functions that depend on hidden mutable state, changing external resources, nondeterministic behavior, or caller identity can produce incorrect hits unless those dependencies are incorporated into keying or handled through invalidation.

The library deliberately does not enforce function purity. It provides mechanisms for storing and retrieving results, not semantic validation of whether a result remains appropriate.

### **10.3. Cache-management overhead is not uniform**

Different policies have different costs.

LRU tracks recency. LFU tracks use counts and frequency ordering. Random replacement maintains candidate-key metadata. TTL requires expiration bookkeeping, and TLRU additionally maintains a heap of expiration records.

Custom `getsizeof`, key functions, locks, conditions, and instrumentation also introduce work.

Conversely, cachetools includes implementation optimizations that are easy to overlook, such as efficient bulk `clear()` methods, specialized replacement bookkeeping, and conditional statistics collection.

The correct performance question is therefore not whether caching is fast in isolation, but whether its **avoided computation cost and improved retention outweigh lookup, allocation, bookkeeping, and coordination costs** for a specific workload.

No universal performance ranking is justified without representative measurements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



## **11. Version 8.0 changes and compatibility considerations**

Version 8.0.0 is more than an increment to the library's supported Python versions.

The upstream changelog identifies several consequential changes:

| Change                                             | Previous behavior                       | Version 8.0 behavior     |
| -------------------------------------------------- | --------------------------------------- | ------------------------ |
| Minimum Python                                     | Python 3.10 supported                   | Python 3.11 required     |
| `@cached(cache=None)`                              | Previously permitted, later deprecated  | Raises `TypeError`       |
| `cachedmethod` with `classmethod`                  | Deprecated                              | Unsupported              |
| `cachedmethod` without mutable instance `__dict__` | Deprecated                              | Unsupported              |
| Custom cache + `info=True`                         | More permissive handling                | Requires `len()` support |
| `CacheInfo`                                        | Internal implementation detail          | Public class             |
| `cached` wrapper representation                    | Function-based wrappers                 | Callable wrapper objects |
| `cache_info` when `info=False`                     | Previously set to `None`                | No longer installed      |
| Descriptor assigned without `__set_name__`         | Previously tolerated in some situations | Can raise `TypeError`    |

The new callable-object wrappers are particularly relevant to tooling that inspects decorated functions using concrete Python function types, descriptor behavior, serialization assumptions, or attributes added by other decorators.

Although standard callable invocation remains supported, the result should not be assumed to be a `types.FunctionType`.

Version 8.0 also includes performance and documentation improvements. The changelog does not provide a general benchmark establishing a specific speed advantage.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### **Important earlier changes still relevant to version 8**

Several capabilities and incompatibilities originated before version 8.0:

| Version     | Consequential development                                                          |
| ----------- | ---------------------------------------------------------------------------------- |
| 6.0         | Added condition-based stampede mitigation; removed `MRUCache` and `func.mru_cache` |
| 6.2         | Improved random-replacement performance using additional key-sequence bookkeeping  |
| 7.0         | Reworked `cachedmethod` as a descriptor; introduced per-instance cache statistics  |
| 7.0.2       | Optimized bulk clearing of supported cache classes                                 |
| 7.1         | Added maintained type stubs                                                        |
| 7.1.5–7.1.8 | Improved size validation, overwrite handling, and negative-capacity rejection      |
| 7.3         | Changed LFU tie-breaking to least-recently-used order                              |
| 8.0         | Removed deprecated APIs and tightened wrapper/descriptor behavior                  |

The inclusion of type stubs since version 7.1 improves the library's usefulness in statically analyzed Python code, including generic cache value and key types. However, code that depends on detailed decorator typing should still be checked against the version 8 stubs.

The removal of MRU is worth emphasizing: older tutorials may still show `MRUCache`, but that class is not part of the current API.

Source: `https://github.com/tkem/cachetools/blob/v8.0.0/CHANGELOG.rst`

## **12. Architectural capability combinations**

The highest-value applications of cachetools often involve combining several native mechanisms rather than relying on a single eviction algorithm.

| Capability combination               | What it enables                                                    | Important qualification                               |
| ------------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------- |
| `LRUCache` + `getsizeof`             | Recency-based retention under a weighted resource budget           | Weights are estimates established at insertion        |
| `TTLCache` + custom timer            | Expiration in a controlled or domain-specific clock                | Caller controls clock semantics                       |
| `TLRUCache` + `getsizeof`            | Value-specific deadlines with weighted memory constraints          | Additional expiration-heap overhead                   |
| `cached` + custom keys               | Semantic memoization and input-version-aware identity              | Key correctness is caller-defined                     |
| `cached` + shared mapping            | A common capacity budget across multiple functions                 | No automatic fairness between functions               |
| `cachedmethod` + per-instance caches | Object-scoped caching with independent lifecycle and statistics    | Requires mutable instance `__dict__`                  |
| `cached` + condition                 | Suppression of redundant concurrent same-key work                  | In-process, synchronous coordination                  |
| `cached` + weak-value mapping        | Results that do not remain alive solely because of caching         | Lifetime is garbage-collector-dependent               |
| `popitem` + `expire` overrides       | Distinct eviction and expiration observability                     | Explicit removal and clearing may need separate hooks |
| `cachetools.func` + TTL              | Familiar memoization with automatic expiration and synchronization | Less configurable than `cached`                       |

These combinations can replace custom memoization dictionaries, manual expiration checks, duplicated LRU bookkeeping, and per-function cache-management scaffolding.

Conversely, they should not be mistaken for a complete generalized caching platform. Cachetools supplies policy-bearing mappings and memoization controls; persistent storage, distributed coherence, dependency discovery, refresh orchestration, and asynchronous execution remain separate concerns.

## **13. Primary source reference map**

The following links are version-aligned primary sources, with topic-specific entry points for further investigation.

| Subject                            | Direct source                                                                                            |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Complete public API                | `https://cachetools.readthedocs.io/en/stable/`                                                           |
| Cache sizing and mapping semantics | `https://cachetools.readthedocs.io/en/stable/#cachetools.Cache`                                          |
| LRU and LFU policies               | `https://cachetools.readthedocs.io/en/stable/#cache-implementations`                                     |
| TTL expiration                     | `https://cachetools.readthedocs.io/en/stable/#cachetools.TTLCache`                                       |
| TLRU expiration                    | `https://cachetools.readthedocs.io/en/stable/#cachetools.TLRUCache`                                      |
| Extending cache classes            | `https://cachetools.readthedocs.io/en/stable/#extending-cache-classes`                                   |
| Memoization decorators             | `https://cachetools.readthedocs.io/en/stable/#memoizing-decorators`                                      |
| Key-generation functions           | `https://cachetools.readthedocs.io/en/stable/#cachetools-keys-key-functions-for-memoizing-decorators`    |
| Standard-library-style decorators  | `https://cachetools.readthedocs.io/en/stable/#cachetools-func-functools-lru-cache-compatible-decorators` |
| Version 8 core implementation      | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py`                              |
| Version 8 decorator implementation | `https://github.com/tkem/cachetools/tree/v8.0.0/src/cachetools`                                          |
| Version 8 changelog                | `https://github.com/tkem/cachetools/blob/v8.0.0/CHANGELOG.rst`                                           |
| PyPI distribution                  | `https://pypi.org/project/cachetools/8.0.0/`                                                             |
| Upstream async discussion          | `https://github.com/tkem/cachetools/issues/222`                                                          |

## **14. Overall assessment**

`cachetools` occupies a useful middle ground between Python's built-in memoization decorators and a full caching infrastructure.

Its defining capabilities are not merely its selection of eviction algorithms, but the way it combines **mutable mapping semantics, configurable resource accounting, expiration policies, cache ownership, key construction, and synchronous concurrency coordination**.

Three capabilities are particularly easy to underestimate.

First, `getsizeof` allows capacity to represent an application-defined resource budget rather than an entry count. This substantially expands the kinds of workloads for which an ordinary in-memory cache can be useful.

Second, `TLRUCache` supports expiration determined by the cached entry itself. Together with custom timers and weighted sizing, this provides a flexible foundation for validity-aware retention without separately implementing expiration data structures.

Third, the separation between `cached`, `cachedmethod`, and the underlying mapping allows cache identity and lifecycle to be controlled independently of the computation. This supports shared resource budgets, instance-specific caches, precise invalidation, custom key semantics, and explicit synchronization.

For conventional synchronous, process-local memoization, these capabilities can significantly reduce custom infrastructure. For workloads requiring asynchronous coordination, persistent state, distributed coherence, or dependency-driven invalidation, cachetools remains a useful component but not a complete solution.

**The central architectural value of cachetools is that caching becomes an independently configurable policy and storage abstraction, rather than incidental state hidden inside individual functions.**

# **cachetools 8.0.0 — Technical Addendum**

Research date: November 17, 2026 | Target: cachetools 8.0.0 | Supplements the original comprehensive overview

This addendum documents additional behaviors, implementation mechanisms, and semantic distinctions identified through examination of the version 8.0.0 documentation, source code, and upstream tests. It focuses on capabilities and constraints not sufficiently developed in the original reference.

## **1. Concurrency semantics: race resolution, single-flight scope, and result consistency**

### **1.1. Lock-based memoization implements a first-stored-result-wins policy**

The `cached` and `cachedmethod` decorators support synchronization using a lock, but their lock-based wrappers do more than protect the cache against concurrent mutations.

When a caller encounters a cache miss, the wrapped computation executes outside the lock. Afterward, the wrapper reacquires the lock and attempts to install the computed result using:

```
with lock:    return cache.setdefault(key, result)
```

This is a consequential choice.

If another thread has populated the same key while the computation was running, `setdefault()` returns the value already stored in the cache rather than replacing it with the later result.

Consider two concurrent calls with the same cache key:

| Event           | Thread A           | Thread B                 |
| --------------- | ------------------ | ------------------------ |
| Initial lookup  | Cache miss         | Cache miss               |
| Computation     | Produces `value_A` | Produces `value_B`       |
| Cache insertion | Stores `value_A`   | Finds existing `value_A` |
| Returned result | `value_A`          | `value_A`                |

Both computations execute, but their callers can receive the same result even when the underlying computations produced different values.

This differs from unsynchronized memoization, where each caller can return its own result and later cache writes can overwrite earlier values.

**Architectural significance:** A lock-only configuration provides serialized cache access and first-stored-result preference, not exclusive execution of a computation. This distinction matters when the wrapped function is nondeterministic, has side effects, or reads changing external state.

For a custom mapping, the behavior also depends on the mapping's implementation of `setdefault()`. The decorator relies on that operation being coherent under the supplied lock.

### **1.2. Condition-based coordination is local to each decorated wrapper**

Condition-based memoization introduces a private set of pending keys, maintained by the individual wrapper.

Conceptually:

```
pending = set()with lock:    while key in pending:        condition.wait()    try:        return cache[key]    except KeyError:        pending.add(key)try:    result = function(*args, **kwargs)    with lock:        cache[key] = result    return resultfinally:    with lock:        pending.remove(key)        condition.notify_all()
```

This is an illustrative simplification of the version 8 implementation.

The distinction is that **sharing a cache and condition variable does not necessarily mean sharing in-flight computation state**.

Suppose two independently decorated functions use the same cache:

```
import threadingfrom cachetools import cached, LRUCacheshared_cache = LRUCache(maxsize=100)condition = threading.Condition()@cached(shared_cache, condition=condition)def compute_a(x):    return operation_a(x)@cached(shared_cache, condition=condition)def compute_b(x):    return operation_b(x)
```

Each decorator creates its own wrapper and maintains its own pending-key set.

Consequently, concurrent calls to `compute_a(10)` and `compute_b(10)` can both begin executing, even if their cache keys are equal and their underlying cache and condition are identical.

The underlying storage is shared, but computation coordination is not global.

This yields four distinct scopes:

| Mechanism                    | Scope                                          |
| ---------------------------- | ---------------------------------------------- |
| Cache storage                | The supplied mutable mapping                   |
| Synchronization lock         | All operations that use that lock              |
| Pending-computation tracking | The individual memoizing wrapper               |
| Cache identity               | Values produced by the configured key function |

A system requiring coalescing across different functions must introduce a shared in-flight registry or another coordination mechanism. Sharing only the mapping and condition is insufficient.

The same principle applies to `cachedmethod`: each bound instance wrapper maintains its own pending-computation state, even when methods obtain a common cache.

### **1.3. Single-flight coordination depends on successful cache admission**

Condition-based memoization prevents concurrent execution for the same pending key, but it does not guarantee that every waiting caller receives the original computed result.

Consider a result whose measured size exceeds the cache capacity.

The first caller computes the result. The cache rejects insertion with `ValueError`, which the decorator suppresses, and the result is returned to that caller.

The pending state is cleared and waiting callers are notified. Because no result was stored, another caller encounters a miss and can begin a new computation.

The same general outcome occurs when the wrapped computation raises an exception: the pending state is released, but no successful result is available for reuse.

Therefore, the distinction is:

- **Concurrent duplicate suppression:** A condition can prevent multiple executions for the same key at the same instant.
- **Result sharing:** Waiting callers reuse a result only when it has actually been admitted to the cache.

This is not equivalent to a persistent future or promise that distributes a completed result or exception to every waiting caller.

The distinction is particularly important for expensive calculations producing large results that regularly exceed the cache's size limit.

### **1.4. Hit/miss statistics do not measure all computation outcomes**

The implementation increments miss counters when the initial cache lookup fails.

With lock-only memoization, two threads can both record misses, execute the computation, and subsequently return the first result admitted to the cache.

With condition-based coordination, a waiting thread that ultimately finds a stored result records a hit when it performs its successful lookup.

Therefore, the reported counters should not be interpreted directly as:

- The number of unique underlying computations.
- The number of results successfully admitted.
- The amount of computation avoided.
- The number of distinct cache keys requested.

They measure wrapper-level lookup outcomes under the selected synchronization strategy.

A more detailed performance model would distinguish invocation count, computation count, cache hit count, admission failures, and waiting time.

**Primary source:** Version 8.0 decorator implementation, including `_LockedMixin`, `_ConditionMixin`, and their instrumented variants.

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_decorator.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_decorator.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## **2. Method caching: object ownership, descriptor mechanics, and inheritance**

### **2.1.&#x20;**`cached`**&#x20;can decorate instance methods directly**

Although `cachedmethod` is the specialized method-memoization interface, `cached` also supports methods.

Version 8.0 returns callable wrapper objects implementing the descriptor protocol. When such a wrapper is accessed through an instance, it binds the instance as the method receiver.

For example:

```
from cachetools import cached, LRUCacheclass Analyzer:    @cached(LRUCache(maxsize=1000))    def analyze(self, data):        return perform_analysis(data)
```

This is a valid method-caching arrangement when the receiver and other key components are hashable.

The cache is created with the decorator and is shared across instances of `Analyzer`.

Because `cached` uses `hashkey` by default, the receiver becomes part of the cache key.

By contrast, a conventional `cachedmethod` configuration typically retrieves an instance-owned mapping and uses `methodkey`, which omits the receiver.

These approaches have different identity and lifetime implications.

| Property                      | `cached` on a method                           | `cachedmethod` with instance-owned storage |
| ----------------------------- | ---------------------------------------------- | ------------------------------------------ |
| Cache allocation              | Usually once at class definition               | Usually once per instance                  |
| Storage ownership             | Shared across instances                        | Owned by each instance                     |
| Default key                   | Includes `self`                                | Excludes `self`                            |
| Receiver hashability          | Required by default                            | Not required by default                    |
| Cross-instance identity       | Determined by receiver equality/hash           | Established through cache separation       |
| Capacity allocation           | Shared budget                                  | Independent budgets                        |
| Replacement of instance cache | Not built into the decorator's storage binding | Supported by dynamic `cache(self)` lookup  |

Neither method is universally preferable. They provide different cache-ownership models.

### **2.2. Cache keys can retain entire object graphs**

When `cached` uses `self` as part of a key, the shared cache retains a strong reference to that object.

This can prevent the object from being garbage-collected even after all other external references disappear.

For example, if a cached result has a key resembling:

```
(instance, argument)
```

the cached key retains `instance`, and the instance may in turn retain other large objects or resources.

Eviction, deletion, or clearing the cache releases that particular reference, but until then the entry can affect the object's lifetime.

This concern does not arise in the same way with an instance-owned cache using `methodkey`, because the receiver is not incorporated into the keys and the cache ordinarily follows the instance's lifetime.

There is also a subtle correctness distinction: `hashkey` uses normal Python equality and hashing, not guaranteed object identity.

Two different instances that compare equal and have the same hash can generate the same cache key. If their computations nevertheless depend on distinct internal state, sharing a result can be incorrect.

Conversely, an unhashable receiver, such as a mutable dataclass with equality enabled and hashing disabled, prevents default `cached` key construction.

These behaviors explain why per-instance caching can be useful for more than capacity isolation: it also provides lifecycle isolation and avoids dependence on receiver hashing semantics.

**Primary sources:**

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_cached.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_cached.py?utm_source=chatgpt.com)

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/keys.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/keys.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### **2.3.&#x20;**`cachedmethod`**&#x20;lazily creates and retains bound wrappers**

The `cachedmethod` implementation uses a custom descriptor rather than simply creating a new wrapper on every method lookup.

On the first ordinary instance lookup, the descriptor:

1. Creates a wrapper bound to the instance.
2. Attempts to store the wrapper in the instance's mutable `__dict__` under the method name.
3. Uses the stored wrapper on subsequent lookups.

This avoids repeatedly allocating bound wrappers and provides stable per-instance wrapper state.

That state includes enabled statistics and condition-based pending-computation tracking.

The approach also explains the mutable-`__dict__` requirement introduced as a strict constraint in version 8.0.

Instances defined with `__slots__` but without a compatible `__dict__` cannot support this storage mechanism.

The decorator itself does not simply require that an instance be hashable, and its cache accessor can still select an entirely separate mapping.

### **2.4. Overridden methods and&#x20;**`super()`**&#x20;receive separate descriptor state**

A less obvious capability is correct handling of decorated methods in inheritance hierarchies.

Consider:

```
from cachetools import cachedmethod, LRUCacheclass Base:    def __init__(self):        self.cache = LRUCache(maxsize=100)    @cachedmethod(lambda self: self.cache)    def calculate(self, x):        return x * 2class Derived(Base):    @cachedmethod(lambda self: self.cache)    def calculate(self, x):        return super().calculate(x) + 1
```

Both `Base.calculate` and `Derived.calculate` are independently decorated.

The descriptor implementation distinguishes an ordinary lookup of the overriding method from access to the base method through `super()`.

For normal lookups, it stores the bound wrapper directly under the method name in the instance dictionary.

When accessing a descriptor through an inheritance path that must not reuse or replace the overriding wrapper, it stores separate wrapper state in an internal per-instance mapping.

This preserves the distinct wrappers required by the inheritance hierarchy.

However, **distinct wrappers do not imply distinct cached values or key namespaces**.

In the example, both methods obtain `self.cache`, and both default to `methodkey`, so the methods can produce identical keys for identical arguments.

That means the example demonstrates the descriptor behavior, but the underlying shared cache would still require separate namespaces to prevent accidental reuse of a base-class result as a derived-class result.

This is an important distinction between:

- Descriptor identity.
- Memoization-wrapper identity.
- Cache-mapping identity.
- Cache-key identity.

The implementation protects the first two; the caller remains responsible for the latter two when storage is shared.

### **2.5. Descriptor initialization, class access, and serialization**

The version 8 descriptor implements `__set_name__` to record its owning class and attribute name.

Dynamically assigning an already constructed descriptor after class creation without calling `__set_name__` results in `TypeError` when the descriptor is accessed.

The implementation also rejects assigning the same descriptor object under different attribute names.

Class-level access is supported through a special unbound callable that can accept the receiver explicitly. The implementation includes compatibility handling for `inspect.signature` and `unittest.mock.create_autospec`.

For serialization and copying, wrappers are reconstructed through the descriptor rather than by serializing their internal locks, closures, or other runtime state.

This supports pickling and copying of appropriately configured instances while allowing wrapper-local statistics to reset.

These are implementation-specific behaviors, not a general promise that arbitrary custom caches, locks, or decorated object graphs are serializable.

**Primary source:** Version 8.0 descriptor implementation.

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_descriptor.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_descriptor.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



## **3. Specialized mapping semantics and read-through cache behavior**

### **3.1.&#x20;**`Cache`**&#x20;overrides&#x20;**`get()`**,&#x20;**`pop()`**, and&#x20;**`setdefault()`

Although `Cache` inherits from `collections.abc.MutableMapping`, it supplies custom implementations of three standard mapping methods:

```
cache.get(key, default=None)cache.pop(key, default=...)cache.setdefault(key, default=None)
```

The implementation comment explicitly explains why these overrides exist: the inherited `MutableMapping` implementations assume that `__getitem__` raises `KeyError` for missing keys.

That assumption does not necessarily hold for a cache subclass implementing `__missing__`.

For example:

```
from cachetools import Cacheclass ReadThroughCache(Cache):    def __missing__(self, key):        value = load_value(key)        self[key] = value        return value
```

Here, `cache[key]` can trigger an expensive retrieval and populate the cache.

The behavior of other mapping operations is deliberately different.

| Operation on an absent key       | Invokes `__missing__`? | Outcome                              |
| -------------------------------- | ---------------------- | ------------------------------------ |
| `cache[key]`                     | Yes                    | Executes subclass-defined fallback   |
| `cache.get(key, default)`        | No                     | Returns default                      |
| `cache.pop(key, default)`        | No                     | Returns default or raises `KeyError` |
| `cache.setdefault(key, default)` | No                     | Stores and returns default           |
| `key in cache`                   | No                     | Tests physical membership            |

This distinction enables a cache to support both loading and non-loading access patterns.

An application can explicitly request a missing value through `cache[key]` while performing inexpensive existence checks or optional lookups through `get()` and membership tests.

The behavior also matters for memoization decorators. They access the cache through `cache[key]`, so a custom `__missing__` implementation can satisfy a lookup without executing the function decorated by `cached`.

Combining a read-through mapping and a memoization decorator therefore creates two potential computation paths. Their interaction must be intentional.

### **3.2. Membership tests and value reads affect eviction policies differently**

Another subtle distinction concerns LRU and LFU metadata.

For the built-in policies, membership testing generally checks whether the key is present without treating the test as an access.

A successful `cache.get(key)` retrieves the value and therefore exercises the cache's access bookkeeping.

Consequently:

```
if key in cache:    ...
```

does not necessarily change retention priority, whereas:

```
value = cache.get(key)
```

can refresh LRU recency or increase LFU frequency.

This matters for code that performs large numbers of existence checks. Treating every existence check as a use would change the statistical meaning of LFU frequency and the working-set behavior of LRU.

The built-in mapping semantics preserve that distinction.

**Primary source:** `Cache`, `LRUCache`, and `LFUCache` implementations.

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_\_init\_\_.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## **4. Expiration edge cases and observable cache state**

### **4.1. Logical expiration and physical deletion are separate events**

An expired entry is logically absent even when its underlying value and eviction metadata remain allocated.

The distinction becomes particularly important when examining different mapping operations.

| Operation on an expired entry | Observable behavior                                               |
| ----------------------------- | ----------------------------------------------------------------- |
| `cache[key]`                  | Treats the entry as missing                                       |
| `key in cache`                | Returns `False`                                                   |
| `cache.get(key, default)`     | Returns the default                                               |
| `cache.pop(key, default)`     | Treats the entry as absent; may leave physical storage intact     |
| `del cache[key]`              | Can remove the physically stored entry and still raise `KeyError` |
| `iter(cache)`                 | Skips expired entries without necessarily deleting them           |
| `len(cache)`                  | Performs expiration cleanup                                       |
| `cache.currsize`              | Performs expiration cleanup                                       |
| `cache.expire()`              | Explicitly removes expired entries and returns removed pairs      |

An especially counterintuitive behavior occurs with direct deletion.

Both timed cache implementations can physically delete an expired entry and then raise `KeyError`.

This happens because the method performs the underlying deletion and subsequently determines that the entry was already expired from the perspective of the public mapping interface.

Thus, catching a `KeyError` from deletion does not prove that no state was modified.

A separate subtlety is that unsuccessful reads of expired entries can update LRU bookkeeping before discovering expiration. Both timed cache implementations move a located key within their recency structure before checking its deadline.

This does not make the expired value accessible again, but it demonstrates that a cache miss is not necessarily free of internal side effects.

### **4.2. Timed-cache iteration does not provide a stable snapshot**

The timed cache iterators evaluate expiration during traversal.

For `TTLCache`, iteration follows the linked expiration structure. For `TLRUCache`, it traverses the internal expiration heap and filters out removed or expired entries.

The heap is not a sorted sequence, so `TLRUCache` iteration must not be interpreted as returning entries in increasing expiration order.

Similarly, neither iterator should be treated as a snapshot of all entries valid at the moment iteration began.

Time is frozen for individual iterator steps, not necessarily for the entire iteration.

An entry can therefore become expired between iterations.

For example, a traversal that performs substantial work between elements may skip keys that would have been valid when the traversal started.

If a consistent point-in-time view is required, that must be established separately through an appropriate locking and snapshot strategy.

This is a particularly important limitation for diagnostic tooling, inspection routines, and bulk operations that assume mapping iteration represents a stable collection.

### **4.3. Fixed-TTL and value-dependent expiration have different admission semantics**

`TTLCache` and `TLRUCache` differ in their treatment of values whose expiration deadlines are already reached when inserted.

With `TTLCache`, insertion computes the deadline and stores the value. A nonpositive TTL can make the resulting entry immediately inaccessible.

The value may still be physically present until an expiration cleanup occurs.

`TLRUCache` instead evaluates its `ttu` callback before admitting the value. If the resulting deadline is not in the future, it does not store that value.

If an unexpired value was already stored under the key, the old value is removed.

If the key is absent, no entry is created.

This behavior provides a useful form of **expiration-based admission control**.

Consider a cached result containing its own validity metadata:

```
from cachetools import TLRUCachecache = TLRUCache(    maxsize=1000,    ttu=lambda key, result, now: result.expires_at,    timer=current_time,)
```

Assuming `result.expires_at` is comparable with the timer's values, a result that is already stale is rejected at insertion time.

This can prevent an invalid replacement from leaving an older, still-readable value behind.

The behavior is especially relevant to credentials, externally supplied expiration metadata, and cached data whose validity is determined by its content rather than by an independently configured cache lifetime.

It is a distinct capability from ordinary eviction, because it determines whether a candidate value is admitted at all.

**Primary source:** `TTLCache.__setitem__`, `TLRUCache.__setitem__`, `__getitem__`, `__delitem__`, and `__iter__`.

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_\_init\_\_.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### **4.4. Clearing is not equivalent to expiring or individually deleting every entry**

The built-in `clear()` implementations are optimized to reset storage and policy metadata directly.

They do not simply invoke `popitem()` or `__delitem__()` repeatedly.

This matters when subclassing a cache to observe removals.

A subclass that overrides `popitem()` will observe capacity eviction, but not necessarily:

- Explicit deletion.
- Expiration cleanup.
- Bulk clearing.

Similarly, a subclass overriding only `__delitem__()` will not necessarily observe all removals performed by `expire()` or `clear()`.

The library deliberately bypasses some ordinary removal paths to avoid repeated bookkeeping and unnecessary work.

**Architectural consequence:** Custom resource cleanup or eviction instrumentation must be attached to the removal mechanisms whose events actually matter. There is no single universal removal callback guaranteed to observe every form of entry disappearance.

This distinction can affect caches storing objects associated with external resources, such as temporary files or native handles.

Source: `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py`

## **5. Capacity accounting, overwrite semantics, and insertion failures**

### **5.1. Replacing a value uses differential capacity accounting**

For a cache with custom size accounting, replacing an existing key is not equivalent to inserting another independent value.

Suppose:

\\[ S\_{\text{old}}=\operatorname{getsizeof}(v\_{\text{old}}) \\]

and:

\\[ S\_{\text{new}}=\operatorname{getsizeof}(v\_{\text{new}}) \\]

Then the size change associated with replacement is:

\\[ \Delta S=S\_{\text{new}}-S\_{\text{old}} \\]

The cache uses this difference when determining whether the replacement requires additional evictions.

For example, consider a cache with capacity 100 units and current occupancy 90 units. An existing entry costs 30 units and its replacement costs 35.

The replacement requires only 5 additional units, not 35.

However, if the replacement cannot fit, eviction may remove other entries and, depending on the policy and ordering, may even remove the key being replaced.

The implementation accounts for this possibility by recalculating the required space if the original key disappears during eviction.

This makes cache replacement behavior more sophisticated than a naive delete-then-insert operation.

### **5.2. Default-size caching avoids per-entry size metadata**

When `getsizeof` uses the default constant-size behavior, version 8 does not allocate a separate dictionary to track every entry's weight.

It uses a specialized constant-size path in `Cache.__setitem__`, maintaining the current count without additional per-entry size records.

When a custom size function is supplied, the cache maintains a separate dictionary recording the size of each admitted entry.

This is necessary because a value can subsequently be replaced or removed, and the cache must know how much previously accounted capacity to release.

The distinction has performance implications:

| Configuration       | Accounting mechanism                               |
| ------------------- | -------------------------------------------------- |
| Default `getsizeof` | Constant increment/decrement per entry             |
| Custom `getsizeof`  | Value-size calculation plus per-entry size records |

The weighted configuration enables substantially more expressive resource accounting, but adds metadata and insertion/replacement work.

The additional overhead should be considered alongside the improvement in retention behavior.

### **5.3. Zero-weight entries create an important capacity edge case**

The size-validation logic allows nonnegative weights, including zero.

If a cache uses:

```
getsizeof=lambda value: 0
```

then the weighted capacity constraint does not limit how many such entries can be retained.

Consequently, a cache may report little or no `currsize` while containing many keys and values.

This is not necessarily incorrect: the chosen resource model explicitly assigned those entries no cost.

However, it demonstrates that a weight budget and an entry-count budget are different constraints.

If both must be enforced, the built-in cache does not provide two independent maximum-capacity dimensions. A custom cache or separate admission policy would be necessary.

### **5.4. Memoization suppresses insertion-time&#x20;**`ValueError`**&#x20;broadly**

The original overview's treatment of failed insertions requires a correction.

The memoization wrappers do not catch only a particular oversized-value exception.

They catch `ValueError` raised by the insertion operation.

For an ordinary wrapper:

```
result = function(*args, **kwargs)try:    cache[key] = resultexcept ValueError:    passreturn result
```

The lock-based variant similarly catches `ValueError` from its `setdefault()` operation.

This includes the usual case where a value exceeds the configured capacity, but it can also include other insertion failures:

| Failure source                                     | Decorator behavior                        |
| -------------------------------------------------- | ----------------------------------------- |
| Value exceeds `maxsize`                            | Returns result without successful caching |
| Custom `getsizeof` raises `ValueError`             | Suppresses error and returns result       |
| Negative weight rejected by the cache              | Suppresses error and returns result       |
| Custom mapping raises `ValueError` while inserting | Suppresses error and returns result       |
| Wrapped function itself raises `ValueError`        | Propagates exception                      |
| Key construction raises an exception               | Propagates exception                      |
| Cache insertion raises another exception type      | Generally propagates                      |

This behavior creates an important distinction between **successful computation** and **successful cache admission**.

The decorator can return a valid result even though the cache was unable to store it.

For custom mappings, however, the broad suppression means that a `ValueError` representing a genuine storage or validation problem can be silently hidden from the caller.

Furthermore, a custom mapping could partially mutate its state before raising `ValueError`. The decorator does not roll back such mutations.

This is an important consideration when using cachetools with mappings whose insertion semantics are more complicated than ordinary in-memory storage.

**Primary sources:**

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_\_init\_\_.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py?utm_source=chatgpt.com)

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_decorator.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_decorator.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



## **6. Additional&#x20;**`cachetools.func`**&#x20;and key-generation implementation details**

### **6.1. Unbounded function decorators change their storage implementation**

When `maxsize=None` is supplied to the non-expiring `cachetools.func` decorators, version 8 uses an ordinary dictionary.

For example:

```
from cachetools.func import lru_cache@lru_cache(maxsize=None)def compute(x):    return expensive_operation(x)
```

This configuration does not maintain an `LRUCache` with infinite capacity. It uses an ordinary dictionary because an eviction policy is unnecessary when there is no capacity-driven replacement.

The same behavior applies to unbounded `fifo_cache`, `lfu_cache`, and `rr_cache`.

The distinction removes bookkeeping that would have no eviction-related purpose.

`ttl_cache(maxsize=None)` is different.

It creates a specialized unbounded `TTLCache`, internally using infinite capacity while preserving expiration tracking.

The exposed `maxsize` property returns `None`, maintaining the expected compatibility-layer semantics.

Thus, the unbounded decorators are not all equivalent:

| Decorator with `maxsize=None` | Underlying storage               | Retention behavior                            |
| ----------------------------- | -------------------------------- | --------------------------------------------- |
| `fifo_cache`                  | `dict`                           | Indefinite until clearing or explicit removal |
| `lfu_cache`                   | `dict`                           | Indefinite until clearing or explicit removal |
| `lru_cache`                   | `dict`                           | Indefinite until clearing or explicit removal |
| `rr_cache`                    | `dict`                           | Indefinite until clearing or explicit removal |
| `ttl_cache`                   | Specialized unbounded `TTLCache` | Entries still expire                          |

Each remains wrapped in the compatibility layer's condition-based synchronization mechanism.

Source: `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/func.py`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### **6.2. Key functions use ordinary tuples and a keyword separator**

The implementation of `cachetools.keys` contains a small but consequential optimization.

The built-in key functions now return ordinary tuple objects rather than constructing instances of a custom tuple subclass.

An internal `_HashedTuple` class remains present primarily to serve as a distinctive keyword-argument separator and maintain compatibility with keys serialized by previous implementations.

For example, the key-generation logic conceptually follows:

```
def hashkey(*args, **kwargs):    if kwargs:        return (            args            + keyword_separator            + tuple(sorted(kwargs.items()))        )    return args
```

Typed variants additionally append the types of supplied positional and keyword values.

This provides deterministic keyword ordering and separates calls with positional arguments from calls using keyword arguments.

It does not provide full function-signature normalization.

The distinction matters for users implementing custom key functions or inspecting keys directly in a shared cache.

The returned object is a normal tuple, but its internal separator is deliberately distinct from ordinary application arguments.

It is generally preferable to use the public `hashkey`, `typedkey`, `methodkey`, and `typedmethodkey` functions rather than reproduce their private representation.

**Primary source:** `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/keys.py`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### **6.3. Callable-object wrappers affect introspection and composition**

Version 8.0 returns callable wrapper objects rather than plain Python functions for `cached` and `cachetools.func`.

The wrappers preserve familiar metadata using `functools.update_wrapper`, including `__wrapped__`, but they are not necessarily instances of `types.FunctionType`.

This can affect frameworks that:

- Inspect decorated callables using concrete runtime types.
- Discover methods through descriptor behavior.
- Combine multiple decorators.
- Serialize decorated callables.
- Use mock objects or automatic signature inspection.

In particular, `cached` implements `__get__`, allowing function wrappers to participate in normal method binding.

`cachedmethod` uses a separate descriptor implementation with additional per-instance wrapper behavior, as detailed earlier.

The version 8 changelog identifies the change to callable objects as potentially breaking, despite retaining ordinary call syntax.

A compatibility-sensitive integration should therefore distinguish whether it requires a callable object or a literal Python function object.

**Primary sources:**

[https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/\_cached.py](https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_cached.py?utm_source=chatgpt.com)

[https://github.com/tkem/cachetools/blob/v8.0.0/CHANGELOG.rst](https://github.com/tkem/cachetools/blob/v8.0.0/CHANGELOG.rst?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



## **7. Additional operational implications**

The newly documented mechanisms have several broader architectural consequences.

### **Cache identity and execution identity are independent**

A common cache key does not necessarily imply that only one computation is performed. Likewise, two separate wrappers can maintain independent execution state while writing to the same cache.

This matters for designs requiring stronger guarantees than ordinary memoization, such as exactly-once external side effects or globally coordinated computation.

Cachetools' lock and condition mechanisms provide useful local coordination, but neither establishes exactly-once execution semantics.

### **Cache ownership determines memory retention**

A class-level cache using instance-containing keys can extend instance lifetimes, while an instance-owned cache generally allows its lifetime to follow that of the object.

This means cache ownership affects garbage collection and object lifecycle, not merely performance or configuration.

For object-oriented systems that create large numbers of transient objects, the distinction can be as important as the eviction policy.

### **Cache removal is not a single unified operation**

Eviction, expiration, explicit deletion, and clearing are separate paths.

A cache subclass cannot assume that observing one path provides complete removal accounting.

When external resource management or comprehensive instrumentation is required, the implementation must account for all relevant removal mechanisms.

### **Cache statistics are not execution statistics**

Hit and miss counters provide a useful measure of lookup behavior, but they do not necessarily reveal the number of computations, suppressed duplicate executions, admission failures, or races.

In performance-sensitive environments, these quantities represent different aspects of cache effectiveness and may need separate instrumentation.

### **Dynamic cache behavior is not automatically semantic consistency**

Custom key functions, value-dependent expiration, and explicit invalidation provide substantial control, but they do not establish a transactionally consistent relationship between changing external data and cached results.

In particular, an in-progress computation may repopulate a cache after another caller has cleared it.

Where stale results must be excluded after an invalidation event, generation-aware keys or additional synchronization are necessary.

These are general architectural implications of the verified implementation, rather than additional guarantees made by cachetools.

## **8. Source and verification scope**

The additions above were verified against the version 8.0.0 upstream source and documentation. Implementation-level observations—including wrapper-local pending sets, descriptor storage, tuple-key representation, and differential size bookkeeping—describe that release rather than immutable API contracts.

The primary implementation files are:

| Area                                                    | Source                                                                           |
| ------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Core mapping, eviction, expiration, and size accounting | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/__init__.py`      |
| Memoization synchronization and insertion handling      | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_decorator.py`    |
| Function-wrapper descriptor behavior                    | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_cached.py`       |
| Method-wrapper behavior                                 | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_cachedmethod.py` |
| Descriptor lifecycle and inheritance                    | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/_descriptor.py`   |
| Compatibility decorators and unbounded storage          | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/func.py`          |
| Key generation                                          | `https://github.com/tkem/cachetools/blob/v8.0.0/src/cachetools/keys.py`          |
| Public documentation                                    | `https://cachetools.readthedocs.io/en/stable/`                                   |
| Release changes                                         | `https://github.com/tkem/cachetools/blob/v8.0.0/CHANGELOG.rst`                   |

Together with the original overview, these additions cover the previously identified gaps in concurrency semantics, method-wrapper lifecycle, specialized mapping behavior, expiration edge cases, admission and overwrite behavior, implementation-specific optimizations, and version 8 compatibility.