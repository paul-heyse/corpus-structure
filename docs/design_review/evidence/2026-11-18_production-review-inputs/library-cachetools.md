# cachetools 8.0 capability brief and reference cache architecture

Prepared 2026-11-18 as library research for the production design review. This is the
prioritized report. The repository was read-only.

## Sources and labels

**Evidence labels:**

- **D**: documented. Sources are the cachetools stable documentation (the page header read
  "cachetools 8.0.1 documentation" on 2026-11-18), the 8.0.x `CHANGELOG.rst`, and the repository
  overview `snap5/docs/libraries/analytical_infrastructure/cachetools.md`.
- **S**: observed in upstream source. The 7.2.7, 8.0.0 and 8.0.1 sdists were downloaded from PyPI
  into the scratchpad (`…/scratchpad/dl_cachetools8/`) and read at `src/cachetools/*.py`.
- **P**: observed in a probe on 2026-11-18 under CPython 3.14.10, importing the extracted 8.0.0 or
  8.0.1 source, with synthetic workloads only.
- **U**: unconfirmed.
- **I**: design inference, not a library statement.

**Reading coverage:**

- The overview, `cachetools.md` (2,105 lines including the technical addendum), was read in full.
- At 8.0.0 I read in full `__init__.py` (the `Cache`, `LRUCache`, TTL and `cached` factories),
  `_decorator.py`, `_cached.py`, `_cachedmethod.py`, `_descriptor.py`, `keys.py` and `func.py`.
- `LFUCache`, `RRCache` and `TLRUCache` internals were only skimmed.
- Diffs read: 7.2.7 against 8.0.0 for `__init__.py`, `_cached.py` and `_cachedmethod.py`, and the
  full source diff of 8.0.0 against 8.0.1.

**Project grounding.** Pointers into the baseline snapshot, which I sampled without reviewing:

- `semantic/selected_query_cache.py:17–86` is the only cachetools user.
- `semantic/archive_reader.py:425–433` is the archive open cache.
- `methods/math/grammar.py:966–993` holds the grammar memos.
- `methods/native_host.py:666–731` is native-host residency with an idle timer.
- `serve/rich_queries.py:71–92` puts the installed `cachetools` version into a read-basis identity.

All paths are under `snap5/python/corpus-structure/src/corpus_structure/`.

## Summary

1. **Release facts.**
   - 8.0.0 was published 2026-11-07, Python ≥ 3.11.
   - **8.0.1 followed on 2026-11-17** (S, PyPI metadata). It fixes copying and deep-copying of
     `@cached` wrappers around `functools.partial`, and LFU pickling. It adds proper shallow
     `copy()` for caches and gives a clearer error for a wrong decorator order. Target **8.0.1**,
     not 8.0.0.
   - The 7.x line continues (7.3.2, 2026-11-14), but nothing requires it.
2. **What cachetools is.** It supplies storage policy (`LRUCache`/`TTLCache`/`TLRUCache` with
   `getsizeof` byte bounds), memoization wrappers (`cached`, `cachedmethod`), and in-process
   same-key single-flight (`condition=`).
   - It does **not** supply cross-process sharing, persistence, async support, dependency-aware
     invalidation, a single removal callback, or exception sharing between waiters.
3. **`lock` protects the mapping, not the computation** (D, S `_decorator.py:37–63`). With a
   lock alone, five concurrent misses ran the loader five times. All five callers received the
   first stored object, because the store uses `setdefault`, so first stored wins (P).
4. **`condition` gives per-key single-flight inside one wrapper.**
   - 8 callers for key 1 and 4 for key 2 ran the loader twice in total, in 0.22 s against a
     0.2 s loader (P).
   - **When the loader raises, waiters do not receive the exception. They retry one after
     another**: 5 callers produced 5 sequential executions in 0.51 s (P; S `_decorator.py:85–96`).
   - All waiters share one `Condition` and wake on every completion (`notify_all`). Gating is per
     key; waking is global.
   - A same-key reentrant call deadlocks (P).
   - `cache_clear()` during an in-flight load is followed by the load re-inserting its old value
     (P).
5. **Removal paths differ** (S, P).
   - `LRUCache.popitem()` evicts through `del self[key]`, so overriding `__delitem__` sees both
     eviction and explicit `del`/`pop`.
   - `clear()` bypasses both.
   - `TTLCache.expire()` bypasses both and returns the expired pairs.
   - A resource holder must therefore hook `__delitem__`, `clear` and (for timed caches)
     `expire`, and must not close a resource that a caller is still using.
6. **The 7.2.7 → 8.0 migration does not affect the project's current cachetools use.**
   `SelectedQueryCache` uses only `LRUCache(maxsize, getsizeof)`, `get`, `popitem`, `clear` and
   `__setitem__`. The bump does change the read-basis identity in `rich_queries.py:71–92`, because
   that identity includes the cachetools version string (S). That re-key is expected and harmless.
7. **Reference design (§H–§J).** Use six named tiers, each keyed by a model-derived identity.
   Bound them by count, or by bytes via `getsizeof` with Arrow `get_total_buffer_size()`. Use
   `condition` single-flight where misses are expensive, and invalidate by identity in the key
   plus clearing on events, through a ~60-line registry module. Cross-process reuse needs a
   different primitive: content-addressed files or PostgreSQL tables keyed by identity.

## Version facts and 7.2.7 → 8.0 differences (§K, needed first)

The 8.0.0 changelog (D, S `CHANGELOG.rst`) is confirmed by source and probes as follows:

| Change | 7.2.7 behaviour | 8.0 behaviour | Evidence |
|---|---|---|---|
| Python floor | 3.10+ | `requires-python >= 3.11` | S (pyproject); the project is on 3.14 |
| `@cached(cache=None)` | worked, with `DeprecationWarning` | `TypeError: cache must not be None` | P, both versions |
| `cache_info` when `info=False` | attribute set to `None` | attribute absent (`hasattr` → False) | P, both |
| `CacheInfo` | private `_CacheInfo` | public `cachetools.CacheInfo(hits, misses, maxsize, currsize)` | P, S `__init__.py:744` |
| `info=True` with a custom mapping | `maxsize/currsize` 0,0 for non-Mapping | requires `len()`; non-`Cache` reports `maxsize=None, currsize=len(cache)` | S |
| `@cached` result type | a plain function (closure) | a callable object (`_BasicWrapper`, …) with `__get__` binding, `__reduce__` returning `__qualname__` (pickles by reference) | P, S `_cached.py:26–46` |
| `cachedmethod` on `__slots__` instances | deprecated | `TypeError: No '__dict__' attribute …` | P |
| `cachedmethod` under `classmethod` | deprecated, with a warning | `TypeError: Decorating class methods is not supported` | P |
| `cachedmethod` descriptor without `__set_name__` | tolerated | `TypeError` | S `_descriptor.py:29–38` |
| LFU tie-break | arbitrary member of a set | oldest first, using an `OrderedDict` (from 7.3.0) | S diff |
| Key objects | — | plain tuples (`hashkey(1) == (1,)`); `_HashedTuple` kept only as the kwargs separator | S `keys.py`, P |
| 8.0.1 | — | `copy`/`deepcopy` of cached partials fixed (P: `deepcopy(p) is p`); LFU pickle; shallow `copy()`; message "@cachedmethod must be the outermost decorator…" | S, P |

Type stubs (`__init__.pyi`, `func.pyi`, `keys.pyi`, `py.typed`) ship in both 8.0.0 and 8.0.1 (S).

## A. Cache classes

All classes are `MutableMapping`s and all are **not thread-safe** (D: "all these classes are
*not* thread-safe").

| Class | Signature at 8.0 | Eviction / expiry | Notes |
|---|---|---|---|
| `Cache` | `Cache(maxsize, getsizeof=None)` | no ordering policy; `popitem` comes from `MutableMapping` | base class |
| `LRUCache` | `(maxsize, getsizeof=None)` | least recently *read or written*; `key in c` does not touch recency | the default choice |
| `LFUCache` | `(maxsize, getsizeof=None)` | lowest use count, oldest within a tie (7.3+) | no aging |
| `FIFOCache` | `(maxsize, getsizeof=None)` | insertion order; overwrite counts as re-insertion | |
| `RRCache` | `(maxsize, choice=random.choice, getsizeof=None)` | `choice(keys)` | a deterministic `choice` helps tests |
| `TTLCache` | `(maxsize, ttl, timer=time.monotonic, getsizeof=None)` | LRU plus a fixed TTL from insertion; reads do not extend it | `expire(time=None)` returns the removed pairs |
| `TLRUCache` | `(maxsize, ttu, timer=time.monotonic, getsizeof=None)` | LRU plus a per-item deadline `ttu(key, value, now)` computed at insertion | an already-expired value is refused admission and removes the old value (D, overview addendum §4.3) |

There are no new cache classes in 8.0. `MRUCache` was removed in 6.0 (D).

**Capacity.** On insert, `Cache.__setitem__` calls `self.popitem()` until
`currsize + size ≤ maxsize` (S `__init__.py:60–92`).

- With a custom `getsizeof`, a value larger than `maxsize` raises `ValueError("value too large")`,
  and a negative size raises `ValueError`.
- A replacement is charged only the size difference.
- Sizes are measured once, at insert, so later mutation of a value is invisible to the cache.
- There is only one capacity dimension. Enforcing bytes *and* a count, as `SelectedQueryCache`
  does by hand (`selected_query_cache.py:71–79`), needs a subclass, or keeping a manual loop.

**Measuring Arrow and model objects.**

- For Arrow values use `table.get_total_buffer_size()`, not `nbytes`. A 10-row slice of a
  1,000,000-row table reports `nbytes=150` but retains 15,000,004 buffer bytes (P). `nbytes`
  undercounts slices; `get_total_buffer_size` overcounts buffers shared by several entries
  (I: safe in the conservative direction).
- `sys.getsizeof` is useless for this purpose: it returned 214 bytes for that slice (P).
- For loaded models, use a declared or measured footprint that the loader records next to the
  value.

**Removal hooks.** Verified paths for an `LRUCache` subclass (P):

- eviction: `popitem` → `__delitem__`;
- explicit removal: `del c[k]` and `c.pop(k)` → `__delitem__`;
- `c.clear()`: neither hook fires.

For `TTLCache`, `expire()` removes through `Cache.__delitem__` directly, so neither an overridden
`popitem` nor `__delitem__` fires; only the return value of `expire()` reports the removal (P, S
`__init__.py:558–580`). `clear()` is optimized per class and never calls per-entry hooks (S).

The documented pattern (D) is "override `popitem()`" for evictions and "override `expire()`" for
expiry. For resource holders the complete set is `__delitem__` + `clear` (+ `expire` on timed
classes), shown in §H.3.

**Expiry semantics.**

- Expiry is lazy, and there is no background thread.
- `len()`, `currsize`, `repr`, `__setitem__` and `popitem` trigger cleanup.
- Iterating a timed cache is not a stable snapshot (D, overview addendum §4.2).
- `timer` may be any ordered clock. Injecting a counter made the tests deterministic (P:
  `timer=lambda: now[0]`).
- There is no sliding (idle) expiry. TTL and TLRU deadlines are fixed at insertion (D).

## B. Decorators

**Signatures (S `__init__.py:757–785`):**

- `cached(cache, key=keys.hashkey, lock=None, condition=None, info=False)`
- `cachedmethod(cache, key=keys.methodkey, lock=None, condition=None, info=False)`. For
  `cachedmethod`, the `cache`, `lock` and `condition` arguments are functions of `self`.

**`lock`** (D: "Any access to the cache will then be nested in a `with lock:` statement … The
underlying wrapped function will be called outside the *with* statement").

- It protects lookup and store only.
- A store after a race uses `cache.setdefault(key, val)`, so the first stored value wins and is
  returned to every racer (S `_decorator.py:52–59`; P).
- Duplicate execution is not prevented: 5 runs for 5 concurrent misses (P).

**`condition`** (D: "will mitigate these situations [cache stampede], but will incur a
performance penalty"). From source, `_ConditionMixin` (`_decorator.py:66–100`):

- Each **wrapper** owns a `pending` set.
- A miss adds the key to `pending` and computes outside the lock.
- On completion it stores `cache[key] = val`; this is plain assignment, not `setdefault`.
- In `finally` it removes the key and calls `notify_all()`.
- A caller that finds its key pending loops `while key in pending: cond.wait()`, then re-reads
  the cache.

Consequences:

- **Gating is per key.** Different keys load concurrently (P: keys 1 and 2 both finished within
  0.22 s).
- **Waking is global.** Every completion wakes every waiter on that condition. Many distinct
  pending keys behind one condition therefore cost spurious wakeups (I; the source comments that
  this loop beats `wait_for`).
- **Scope is the wrapper.** Two functions sharing one cache and one condition do not coalesce
  each other's work (D, overview addendum §1.2). `cachedmethod` keeps the pending set per bound
  instance wrapper (S).
- **A raising loader does not share its exception.** The pending key is released, each waiter
  re-checks the cache, misses, and becomes the next loader, so retries are serialized (P: 5
  executions, 0.51 s). The same happens when the value is too large to admit.
- **No timeouts.** `cond.wait()` has none (S). A loader that hangs blocks all of its key's
  callers indefinitely. A same-key recursive call blocks forever (P).
- **No generation fence.** A `cache_clear()` during a load does not stop the load re-populating
  the cache with a pre-clear value (P).

**`condition` without `lock`.** The condition is then also used as the lock (S
`_cached.py:89–90`). Passing both requires the condition to be built on that lock, as in
`Condition(lock)` (D).

**Introspection on the wrapper (S `_cached.py:26–46`):** `cache`, `cache_key`, `cache_lock`,
`cache_condition`, `cache_clear()`, `cache_info()` (only when `info=True`) and `__wrapped__`.

- `cache_parameters()` exists only on the `cachetools.func` decorators (S `func.py:29`).
- Use `wrapper.cache_key(*args)` with `wrapper.cache_lock` to `pop` a single entry (D).

**Statistics.**

- `CacheInfo(hits, misses, maxsize, currsize)` (P).
- Counts are of lookup outcomes. A waiter that later hits counts as a hit. Admission failures and
  duplicate computations are invisible (S; D, overview addendum §1.4).
- `cachedmethod` statistics are per instance (P: `CacheInfo(hits=1, misses=1, maxsize=4,
  currsize=1)`).

**Edge cases.**

- **Unhashable arguments.** A mutable dataclass argument raises `TypeError: cannot use 'tuple' as
  a dict key` (P). Normalize in the key function.
- **`cache=None`.** Raises `TypeError` in 8.0 (P).
- **Async.** No support. A cached `async def` stores the coroutine, and the second `await` raises
  `RuntimeError: cannot reuse already awaited coroutine` (P). The 8.0.1 documentation does not
  mention coroutines (D, fetched).
- **Oversized values.** A `ValueError` on insert is swallowed and the value returned uncached
  (S; P: `CacheInfo(hits=0, misses=2, maxsize=100, currsize=0)` after two calls).

**`cachetools.func`.** `lru_cache`, `lfu_cache`, `fifo_cache`, `rr_cache` and `ttl_cache` are all
`cached(..., condition=Condition(), info=True)`, so they are single-flight by default (S
`func.py:22–32`).

- With `maxsize=None` they use a plain `dict`, except `ttl_cache` (S).
- There is no `getsizeof` parameter and no `tlru_cache`.

## C. Key functions

All key functions are in `cachetools.keys` (S `keys.py`):

- `hashkey(*a, **kw)` returns `a` itself, or `a + (_HashedTuple,) + sorted(kw.items())`.
  `f(1)` and `f(a=1)` give different keys: `(1,)` versus `(_HashedTuple, ('a', 1))` (P).
- `typedkey` appends the argument types. `hashkey(1) == hashkey(1.0)` is True, while
  `typedkey(1) == typedkey(1.0)` is False (P).
- `methodkey` and `typedmethodkey` drop `self`, which is correct only when the cache is per
  instance.

**Recommended key discipline (I, with P support):**

- **Key on a model-derived identity value, never on carrier objects.** Make a frozen dataclass or
  `NamedTuple` identity, for example `(kind, content_digest, model_digest)`.
- **Ignore non-determinants.** Pass them through and have the key function ignore them:
  `@cached(cache, key=lambda ident, acquisition: hashkey(ident))`. Two calls with different
  acquisition objects returned the same cached result (P).
- **Keep the key function's signature identical to the wrapped function's.** `cache_key`
  receives exactly the call arguments.
- **Namespace a shared cache:** `key=functools.partial(hashkey, "tier.op")` (D).
- **Keep keys small.** A key retains whatever it references (D, overview addendum §2.2). Never
  put a connection, session, Arrow table or ORM object in a key. Use its identity digest. A
  `cached` method on a shared cache keeps `self` alive through the key.
- **Normalize positional and keyword forms** with `inspect.signature(f).bind(*a, **kw)` plus
  `apply_defaults()`, or adopt a project rule that identities are passed positionally (D,
  overview §4.4).
- **Dataclass identities** must be `frozen=True`, or define `__hash__`. `eq=True` and
  `frozen=False` makes an object unhashable (P). Equality is value equality, so two distinct but
  equal objects share an entry. That is correct exactly when the dataclass *is* the identity.

## D. Invalidation patterns that are real designs

| Pattern | Mechanism | Guarantees and limits |
|---|---|---|
| Identity in the key | a key containing `model_digest`, `publication_id` or `snapshot_xid` | **Strongest.** Old entries become unreachable at once, in every process, with no coordination. Memory is reclaimed later by LRU. Use it everywhere a determinant has an identity |
| Generation counter in the key | a process-local `generation[domain]` read inside the key function; an event increments it | fences in-flight loads, since an old-generation insert lands under a dead key. Only process-local; use it when the determinant has no identity |
| Event clear | registry `clear(domain)` on a publication or model-change event | reclaims memory. **Alone it is unsafe** against in-flight repopulation (P), so pair it with one of the two rows above |
| Targeted pop | `with w.cache_lock: w.cache.pop(w.cache_key(*args), None)` (D) | precise, when the affected keys are known |
| TTL | `TTLCache(ttl=…)` | bounded staleness only. It cannot detect change. Use it only for answers whose staleness the product accepts, such as catalog counts |
| TLRU | `TLRUCache(ttu=lambda k, v, now: v.valid_until)` | per-value validity, for example from source metadata; refuses admission of already-stale values (D) |
| Layered | small per-request dict → process LRU → persistent store (§E) | each layer keyed by the same identity. cachetools covers the middle layer only |
| Negative caching | return a sentinel or an exception object from the loader and re-raise outside (D) | only for deterministic absences, such as "no such release digest". Never cache transient errors |

**Left to the application (D):** dependency tracking, refresh-ahead and
stale-while-revalidate, cancellation of in-flight loads on invalidation, and admission policy.

## E. What cachetools does not provide, and the fitting primitive

| Need | Primitive | Notes |
|---|---|---|
| Reuse across CLI invocations, which are new processes and today never hit | **content-addressed files**: `<root>/<tier>/<identity-digest>.<fmt>`, written to a temp file in the same directory, then `os.replace` (atomic on POSIX), optionally with a `filelock` 4.2.12 lock file to avoid duplicate builders | best for model and schema compilations and generated programs. Use a stable, versioned format such as JSON, Arrow IPC or Parquet, **never pickled caches**: "the byte stream format is an implementation detail that *any* release may change, even a bugfix release" (D). Include library and format versions in the identity |
| Shared derived results across processes and machines, with authority | **PostgreSQL tables keyed by identity** | ordinary tables are durable. `UNLOGGED` tables are faster, but are truncated after a crash and are not replicated (PostgreSQL docs, not verified here). Good for served derived rows that must respect row-level security and snapshots |
| A disk cache library | `diskcache` 5.6.3 | last release 2023-08-31 (S, PyPI). Mature but quiet. Values are pickled by default, so files are a code-execution trust boundary (I) |
| Warm caches across commands | a **long-lived local process**, such as the serving process or a daemon the CLI talks to; or on-disk results | a daemon keeps memory tiers warm but brings lifecycle, versioning and staleness on model change. On-disk identity-keyed artifacts give most of the benefit for compile-type work |
| Process pools | `concurrent.futures.ProcessPoolExecutor` | the Linux default start method on 3.14 is **`forkserver`** (P), so workers start with empty module caches. Warm them in an `initializer` from the on-disk tier |
| Shared memory | `multiprocessing.shared_memory` or Arrow IPC files with `memory_map` | for large read-only Arrow tables shared by worker processes. cachetools can index handles to them |
| Memory accounting | `getsizeof` returning `get_total_buffer_size()` for Arrow, or declared model sizes | process RSS is not visible to cachetools. Use one byte budget per tier, sized from settings |
| Async | none in cachetools. `asyncache` 0.3.1 is from 2022-11 (S, PyPI) and is stale | see §J.5 |

## F. functools versus cachetools; migration pitfalls

**Keep `functools`:**

- **`functools.cache` / `lru_cache`** for cheap, pure, process-lifetime memos with small hashable
  arguments: enum and lookup tables, regex compilation, parsed constants.
  - It is C-implemented, so hits are faster than a pure-Python wrapper.
  - Its structure is thread-safe, but it may run the function twice under concurrency (Python
    docs). That is harmless for cheap pure functions.
- **`functools.cached_property`** for derived values on immutable per-object state. Since Python
  3.12 it takes no lock, and the value dies with the object.

**Switch to cachetools when any of these holds:**

1. the value is large (bytes bound);
2. the loader is expensive and requested concurrently (`condition`);
3. entries hold resources needing release (hooks);
4. invalidation must be by event or clear, or observed (`info`, registry);
5. an `OrderedDict` LRU is being maintained by hand (`archive_reader.py:425–433`,
   `grammar.py:966–993`).

The grammar memos mutate `OrderedDict`s with no lock (`grammar.py:980–993`, S). They are unsafe if
reached from several threads; whether they are is U.

**Pitfalls (P unless noted):**

- **Decorator order.**
  - `@cached` in a class body *binds* like a method: `A().plain()` returned the instance as `x`.
    Use `@staticmethod` outermost (`@staticmethod @cached(...)` works).
  - `@cachedmethod` must be outermost. `@cachedmethod @staticmethod` mis-binds, and
    `@property @cachedmethod` raises `TypeError: … @cachedmethod must be the outermost
    decorator`, the 8.0.1 message.
  - Class methods are unsupported.
- **`cachedmethod` and garbage collection.** The bound wrapper is stored in `obj.__dict__` and
  references `obj`, which forms a cycle. The instance survived `del` until `gc.collect()` (P), so
  per-instance caches are freed only by the cyclic collector. Keep large per-instance caches
  rare.
- **`__slots__` classes**, including `@dataclass(slots=True)`, cannot use `cachedmethod` (P).
  Use a module-level `cached` keyed by the instance's identity value instead.
- **Dataclass identities:** see §C.
- **Pickling across processes.**
  - Decorated functions pickle by reference (P: `loads(dumps(f)) is f`), so they can be submitted
    to pools.
  - Locks do not pickle (P).
  - Caches pickle (P), but the format is unstable (D). Never ship or persist them.
- **Shared cache plus `methodkey`.** This gives cross-instance false hits (D). Use `hashkey` or an
  identity key.

## G. Decision rule

Given a result, its determinants, its size, its compute cost and its consumers:

1. **Some determinant has no identity** (hidden mutable state, wall clock, caller authority not
   in the key): **do not cache**, or add the determinant to the key first.
2. **Consumers in other processes** (CLI, workers, other hosts):
   - if the result is durable and rebuildable, use the content-addressed file tier;
   - if it must honour PostgreSQL authority or snapshots, use a PostgreSQL table;
   - optionally add a process tier above either.
3. **Within one process:**
   - cheap, small, pure, small arguments: `functools.cache`/`lru_cache`, or `cached_property`
     for per-object state;
   - expensive *and* concurrently requested: `cached(…, condition=Condition(lock))`;
   - expensive, single-threaded consumers: `cached(…, lock=…)`;
   - variable or large size: add `getsizeof` with a byte budget from settings;
   - holds an OS resource or native memory: a resource tier with release hooks and leases
     (§H.3);
   - staleness acceptable but change undetectable: `TTLCache`;
   - per-value validity: `TLRUCache`.
4. **Invalidation:** always identity in the key, plus registry clear for memory. Add a generation
   counter only when no identity exists.
5. **Failures:** do not cache them unless the absence is deterministic. If waiters must share a
   failure, use §J.2.

## H. Reference architecture: process-wide cache tiers on cachetools 8.0.1

This architecture is inference (I), built only from the verified mechanics above. The tier
names are suggestions. Byte figures are placeholders that settings supply.

| Tier | Holds | Class and bound | Key (model-derived) | Coordination | Invalidated by | Stats |
|---|---|---|---|---|---|---|
| **T1 model** | compiled LinkML schema views, derived Arrow and Pydantic schemas, enum tables | `LRUCache(maxsize=N≈8)`, by count. Items are few and large, but sized by the model | `(model_digest, generator_versions)` | `condition` (startup stampede) | a new model digest gives a new key; `clear("model")` | `info=True` |
| **T2 programs** | generated SQLAlchemy Core statements and compiled forms, pglast output, native program artifacts, DuckDB relation *builders* (not relations) | `LRUCache(maxsize=N≈512)`, by count | `(model_digest, program_id, compiler_version, dialect)` | `condition` | as T1 | `info=True` |
| **T3 resources** | opened archives, file handles, memory maps, prepared reader objects | `ResourceLRU` subclass (below), count bound by file-descriptor budget (≈8–64) | `(engine/db identity, release_id, content_digest)` or `(st_dev, st_ino, st_size, st_mtime_ns)` with a content digest confirmed on hit | `condition` for opening; **leases** for use | a digest mismatch on confirmation leads to `pop`; `clear("publication")` | `info=True` + release count |
| **T4 results** | acquired read snapshots' derived rows, served query results, comparisons, exports | `LRUCache(maxsize=bytes, getsizeof=…)`, by bytes; optional count cap via subclass | `(query_identity, publication_or_snapshot_identity, authorization_scope)` | `condition` | identity; `clear("publication")`; `TTLCache` only for explicitly stale-tolerant views | `info=True` |
| **T5 runtimes** | loaded CPU models and tokenizers; *not* GPU or native-host residency | `ResourceLRU(maxsize=bytes, getsizeof=declared_footprint)` | `(model_artifact_digest, device_class, runtime_version)` | `condition` | artifact digest; `clear("runtime")` | `info=True` |
| **T6 memos** | grammar and parse memos, small pure derivations | `cachetools.func.lru_cache(maxsize=…)` (already single-flight and locked), or `functools.lru_cache` when the computation is cheap | the call arguments (normalized) | built in | none, or `cache_clear()` on a model change if a macro table depends on it | `cache_info()` |

**Tier notes:**

- **T2.** Prepared statements are per connection. psycopg prepares server-side per connection,
  and SQLAlchemy has its own engine-level compiled cache, `query_cache_size` (SQLAlchemy docs; U
  here). T2 should hold the model-generated *statement objects* and let the driver handle
  per-connection preparation. A DuckDB relation is a re-executing query bound to one connection,
  so do not cache relations across connections. Cache the function that builds them.
- **T3.** The existing archive cache stores an immutable `prepared` object, not a handle
  (`archive_reader.py:416–433`), and already does first-wins under a lock. Move it to T3, and add
  count statistics and event clearing.
- **T4.** `authorization_scope` belongs in the key unless the result is proven
  authority-independent. The existing `SelectedQueryCache` already re-acquires native authority
  per caller (docstring, `selected_query_cache.py:1`). Keep that, and the byte budget.
- **T5.** The native host has active-call tracking, quarantine, suspension, GPU hand-off and
  idle-timer retirement (`native_host.py:666–731`). That is a lifecycle state machine, and
  cachetools has no sliding or idle expiry. Keep it as its own owner. At most, use cachetools as
  the index of which runtimes are resident.

**T3 / T5 resource tier (I; hooks verified in §A).** Releasing on removal is safe only if no
caller still holds the object, so removal *retires* the entry and the last lease closes it:

```python
class ResourceLRU(LRUCache):                       # all calls under the owner's lock
    def __delitem__(self, key):                    # eviction (via popitem) and del/pop
        value = Cache.__getitem__(self, key) if key in self else None  # no LRU touch
        super().__delitem__(key)
        if value is not None: value.retire()       # closes now if unleased, else on last release
    def clear(self):
        values = list(self.values()); super().clear()
        for v in values: v.retire()
# value.retire()/lease() are a small refcount on the held object; keep close() cheap,
# or hand it to a background closer, because it runs inside the cache lock.
```

`LRUCache.popitem` reads the value through `Cache.__getitem__` and then calls `del self[key]`
(S `__init__.py:317–326`), so the override above sees evictions.

## I. One owner module: register, measure, clear, size from settings

This is a plain module, not a framework (I).

```python
# caches.py (single owner)
_lock = threading.Lock()
_entries: dict[str, Entry] = {}        # Entry(name, tier, cache, lock, events, wrapper|None)

def register(name, tier, cache, *, lock, events=frozenset(), wrapper=None) -> MutableMapping: ...
def declare(name, tier, *, events, key=hashkey, single_flight=True, cls=LRUCache, **bounds):
    """Build cache sized from settings[tier], Condition(RLock()), and return the @cached decorator."""
def snapshot() -> list[dict]:          # name, tier, len, currsize, maxsize, hits, misses
def clear(event: str) -> None:         # for each entry listening to event: with entry.lock: cache.clear()
def reset_after_fork() -> None:        # new locks/conditions, empty caches; os.register_at_fork(after_in_child=…)
```

Rules that keep it small:

- **Only process-wide caches register.** Per-instance `cachedmethod` caches follow their owner's
  lifetime.
- **Sizes come from one typed settings object**, a byte or count budget per tier read once at
  `declare`. `maxsize` cannot be changed after construction (S: `__maxsize` is private), so a
  resize means building a new cache and swapping it under the lock.
- **`snapshot()` reads `wrapper.cache_info()`** when present, otherwise `len` and `currsize`. It
  takes each entry's lock, because `currsize` on timed caches triggers cleanup (D).
- **Events are a closed vocabulary** derived from the model: `"model"`, `"publication"`,
  `"runtime"`. Publishers call `caches.clear(event)` *after* their new identity is visible, and
  keys carry that identity, so in-flight old loads land under dead keys (§D).
- **No decorators beyond `declare`**, no metrics backend, and no persistence. The on-disk tier
  (§E) is a separate small module keyed by the same identities.

## J. Concurrency recipes verified at 8.0

1. **Single-flight under threads.**
   `@cached(cache, key=…, condition=threading.Condition(threading.RLock()), info=True)`.
   - Verified: 12 callers over 2 keys ran the loader twice in 0.22 s (P).
   - Use one condition per wrapper when many keys are usually pending at once. That keeps the
     global wake-up cost (`notify_all`) local.
2. **Loader raises.** Waiters retry serially (P). When failures are costly, such as timeouts to
   PostgreSQL or a native host, put a future-based single-flight in front of the cache (I):

   ```python
   _inflight: dict[Key, Future] = {}           # guarded by the tier lock
   def get(key, load):
       with lock:
           if key in cache: return cache[key]
           fut = _inflight.get(key); owner = fut is None
           if owner: fut = _inflight[key] = Future()
       if not owner: return fut.result(timeout=T)        # shares value *or* exception
       try: val = load(); fut.set_result(val)
       except BaseException as e: fut.set_exception(e); raise
       finally:
           with lock:
               _inflight.pop(key, None)
               if fut.exception() is None: cache[key] = val   # ValueError → skip admission
       return val
   ```

   This also adds waiter timeouts, which cachetools lacks.
3. **Per-key versus global blocking.**
   - The lock is held only for lookup and store. Computation runs outside it, and different keys
     compute concurrently (S, P).
   - Waits are per key, but wake-ups go to everyone.
   - Never call the same key reentrantly from inside its loader: that deadlocks (P).
   - Keep `close()` and hooks cheap, because they run inside the lock.
4. **Thread pools.**
   - Waiters occupy pool threads. A loader that submits subtasks to the *same* bounded pool and
     waits on them can starve the pool (I). Run loaders on the caller's thread, or on a separate
     pool.
   - CPU-bound loaders gain nothing from threads under the GIL. Free-threaded CPython 3.14 is not
     available here, and DuckDB 2.0 does not support it.
5. **asyncio.**
   - cachetools 8.0.1 has no async support (D silent; P coroutine reuse error).
   - Pattern (I): cache *results*, not coroutines. Hold an `asyncio.Task` per pending key in a
     dict, which needs no lock on a single event loop. Waiters `await asyncio.shield(task)` so one
     cancelled waiter does not cancel the shared load. Store the result into a cachetools cache
     when the task finishes.
   - Alternatively, call a sync `cached` function through `asyncio.to_thread`.
   - `asyncache` is stale (2022).
6. **Processes.**
   - *forkserver/spawn* (the 3.14 default on Linux, P): children import modules fresh, so caches
     are empty and locks are new. Rebuild warm state from the on-disk tier in the pool
     `initializer`.
   - *fork*: children inherit cache contents *and lock states*. A child forked while a parent
     thread held the cache lock could not acquire it (P: `lock.acquire(timeout=0.5)` → False).
     If fork is used, register `os.register_at_fork(after_in_child=caches.reset_after_fork)`.
   - Never rely on inherited T3 or T5 resources, such as file offsets or native handles, after a
     fork.

## Not resolved

- Whether the grammar memos and the archive cache are reached from several threads in
  production (U; the review should check callers).
- SQLAlchemy and psycopg statement-cache parameters are cited from memory of their documentation
  and were not re-verified here (U).
- No measurement of cachetools wrapper overhead against `functools`. This is qualitative only:
  pure-Python versus C wrapper (D).
- `TLRUCache` internals were skimmed only. The admission-refusal claim rests on D (overview
  addendum §4.3) and was not probed.

Files written: this report and `LIB_DUCKDB.md`, both in the scratchpad `audit/prod/` directory.
Scratch downloads (untrusted, read-only use) are in `…/scratchpad/dl_cachetools8/`.
