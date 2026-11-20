# Cachetools and diskcache-community functional extension review

**Proposed · 2026-11-20.** Keep cachetools as the process-retention owner. Adopt
diskcache-community behind the existing persistent store contract for bounded served
populations first. Move generated program sets to the same store implementation only
after proving the larger file-backed path against the actual rendering and hydration
workload. Ship each cutover with one active persistent backend per tier. Improve cache
diagnostics independently of either cutover. Workload identity and native authority
continue to govern reuse.

## Scope and evidence

The review covers product reads, offline authoring, spawned workers, retained MCP readers,
and the operator's cache controls. The repository baseline is `2614de56f`. The comparison
uses the supplied `docs/libraries/analytical_infrastructure/diskcache-community.md` briefing,
the [cachetools overview](../libraries/analytical_infrastructure/cachetools.md), the
[UDM cache companion](../plans/unified-domain-model-and-execution/cache-system.md),
[serving custody](../adr/0137-serving-code-and-model-custody.md), and the [execution
host](../adr/0125-process-owned-execution-host.md). The design judgment applies FP-04,
FP-07, DP-04, DP-09 and G6 with H12–H20 from the [design standard](../design_review/design_principles/standard.toml).

**Interface-checked · 2026-11-20.** diskcache-community **5.8.5** was read from
[`6c48b163`](https://github.com/secondwindoss/diskcache-community/tree/6c48b163bcdcfb6e82d4ec6068045c295b4f2d1c)
and cachetools **8.0.1**, the lockfile pin, from
[`498bd83c`](https://github.com/tkem/cachetools/tree/498bd83c1938d9dd5d9aaf4dab3043fb15fb1e42).
Context7 resolved the original DiskCache project for the fork query and found cachetools
documentation without a version-matched 8.0.1 index. It helped locate the transaction,
writer-contention and memoizer-condition interfaces. The tagged code, tests, release notes
and linked official documentation establish the selected contracts. One important correction
to the overview is that `FanoutCache.transact()` acquires *all* shard transactions and forces
retry. Its `ExitStack` exits distinct SQLite transactions, leaving separate commit outcomes
under process failure. A single `Cache` has one database transaction.
[Sharded transaction source](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/fanout.py#L99)

**Tested · 2026-11-20.** A scratch probe imported the tagged fork source on Python
3.14.10 and SQLite 3.53.1. Two spawned writers produced one winning value under
`add`. A fresh read-only opener returned that value and refused deletion. A contending
`add(retry=False)` raised `Timeout` and left its key absent. A file-backed byte value
round-tripped through an explicitly closed stream. These are storage observations with
synthetic values. Production identity, throughput, and cutover remain unverified by this
probe. [Probe and result](../design_review/evidence/2026-11-20_cache-backend-contracts/README.md)

## What is deployed

| Workload | Owner and existing behavior | Useful opportunity |
|---|---|---|
| T1 compiled model, T2 program sets, T3 releases and archives, T5 CPU preparation, T6 grammar memos | [Process owner](../../python/corpus-structure/src/corpus_structure/caches.py) uses namespaced, count- or byte-bounded `LRUCache` and `cached` with synchronized wrapper-local conditions. Spawned processes start cold. CPU and GPU workers retain separately owned runtime resources. | Keep existing retention. Explain which namespace was evicted or skipped. Investigate serialized preparation only where actual consumers repeatedly pay meaningful cold work. |
| T4 served rows and rich graph preparation | [Selected query owner](../../python/corpus-structure/src/corpus_structure/semantic/selected_query_cache.py) combines byte and entry limits, per-key futures, bounded waiting, shared failures, and request-local streaming. MCP holds process retention and exposes a bounded process observation. | Keep the future and bounded row contracts. Use persistent retention for portable data where a command benefits across invocations. |
| D4 bounded served populations | A CLI request opts into disk storage. Native acquisition, support and disclosure checks precede lookup. Disk stores derived metadata, typed rows and offsets under a query key, enabling later pages without retaining a connection or iterator. The rich index is excluded from persistence. | Replace directory mechanics under the typed codec. Preserve query-specific cut or content witness and the distinction between cursor compatibility and storage format. |
| D2 generated program sets | [Program store](../../python/corpus-structure/src/corpus_structure/semantic/native_program_store.py) uses a typed artifact keyed on exact captured inputs and authenticated renderer identity. It checks and hydrates the artifact using newly compiled physical metadata. | Reuse the same persistent implementation if large-value verification and hydration remain economical and safe. Keep PostgreSQL revision registration and deployment separate. |
| Published products, acknowledged drafts, PDF checkpoints, leases and managed evidence | Native publication, recovery and managed-result owners establish authority and exact recovery. | Keep these lifecycles with their owners. Cache eviction may discard replaceable work without retiring a worker, deleting an acknowledged draft or withdrawing evidence. |

[Qualification](../plans/unified-domain-model-and-execution/qualification.md#code-closure-and-real-reuse-qualification)
records the exact open prerequisites. Strict D2 reproduced 620 expected N36 objects while
both processes rendered and neither hydrated. T4 and T14 require complete determining
code in the actual serving path. Backend adoption does not supply those identities.
The bounded CUDA recovery and unchanged repeat already use native receipts to avoid
new publication. The earlier book restart illustrates why committed output and
recoverable drafts need durable, authenticated uptake even if every disposable cache
is lost. [Recovery owner](../plans/unified-domain-model-and-execution/operation-reuse-and-recovery.md)

## Recommended extensions

<a id="O01"></a>
### O01 · Share verified served populations between CLI processes

**Proposed.** Replace D4's directory implementation with one local unsharded
`Cache` behind its current owner. Store canonical digest keys and a single bounded,
versioned binary envelope for the metadata, row bytes and offsets, keeping the existing
typed row encoding. Keep D4 rows small enough for inline SQLite storage, with
`disk_min_file_size` above the largest admitted envelope. Admit against an explicit
payload bound and provision a separate store budget with room for SQLite pages and
journaling. The default D4 store budget is 1 MiB today, so the existing entry and
total limits need to be reconciled with real envelope and database overhead. An
unsharded database and one envelope avoid assembling a result across transactions,
and inline storage avoids temporary value files for the serving hot path.

A CLI continuation can acquire fresh native authority, select its exact key, and load
the same bounded population in a second process. A revoked principal, changed support,
different role or unknown implementation still follows the existing refusal or fresh
derivation rules. The envelope authenticates key correspondence and checks byte
integrity, size, inventory and codec. Existing value handling preserves exact Decimal
scale and signed zero, float type, row order and cursor ordinals. Byte checks detect
accidental damage within the trusted cache. They do not authenticate an arbitrary writer
who can replace both an envelope and its digests.

Use explicit `Cache.get` and `Cache.add(retry=False)` with a short configured SQLite
wait, a separate missing-value sentinel, and an explicit unavailable result on
contention or I/O failure. `add` installs one winner under the SQLite transaction.
On false, re-read and compare the verified winner. If culling or another reader's
maintenance removed it, keep serving the freshly derived answer. A conflicting
winner is a diagnostic and an unusable entry. Remove it only with a recheck of the exact
observed row under the writer transaction, so a newer replacement survives. An
insertion can be followed by culling even within the same library call. It establishes
neither retention nor once-only derivation. Keep duplicate cross-process cold derivation
tolerable until an observed workload warrants explicit bounded coordination.
[Add path](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L2503)
· [Transaction handling](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L2178)

The SQLite connection timeout applies to the established connection. The constructor
and setting changes use separate per-statement lock retries of up to 60 seconds in
the source. Keep one fixed configuration per namespace and arrange initialization or
changes at an explicit maintenance boundary. Verify same-settings reopen during
contention in a fresh CLI process. Adopt the backend only if the complete optional
cache route can meet the request's wait contract, including open and reconnect.
[Constructor](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L1796)
· [Initialization retry](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L2103)

Use `SafeDisk` explicitly at every opener and store only primitive keys and bytes.
The configured disk class is external to stored rows. The private local root still
needs owner and mode validation, a fresh backend namespace, and a deployment contract
for its parents. `SafeDisk` restricts deserialization and checks value-file paths
using `realpath` and `commonpath`. These checks do not supply the existing directory
descriptor and no-follow race guarantees under a writable parent. If the private
directory boundary cannot be maintained, keep the existing store for that environment.
`SafeJSONDisk` excludes pickle modes but using its JSON object representation here
would introduce a second typed codec. Class and module allowlists and `with_numpy`
add import and version coupling. Keep default `on_error` behavior and classify
failures at the owner, where actions and counters can distinguish unusable content,
busy storage and unsupported format. A generic miss-and-delete policy can delete
entries valid under a different reader configuration.
[SafeDisk](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L839)
· [Path checks](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L1136)
· [Entry-error tests](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/tests/test_entry_errors.py)

**Acceptance example.** Run authorized T4 across two fresh processes and repeat with
revoked support. Compare rows and continuation to independent expectations. Count
reuse after successful decode, and verify refusal occurs before either cache lookup.
Exercise busy, corrupt, disabled, over-budget, missing and read-only stores on an eligible
query. Fresh authorized derivation should keep working, and a duplicate add attempt
should leave the same winner. A synthetic exact key establishes storage behavior only.

<a id="O02"></a>
### O02 · Extend the persistent owner to offline program artifacts

**Proposed, after O01 and verified D2 custody.** Use a second unsharded database/directory
with its own budget. Keep the generator's existing input capture, release and predecessor
checks, exact `ProgramSetArtifact`, and its typed validation. The shared store should take
opaque encoded artifacts from both workload owners. Use native file-backed bytes for D2
payloads above `disk_min_file_size` if the current large JSON artifact remains appropriate.
`add(..., read=True)` can write a binary reader in chunks and `get(..., read=True)`
can return a file handle for a file-backed value. Inline values can still return bytes.
The consumer must own the handle and validate the bounded complete artifact. Streaming
helps only when the producer or decoder avoids a second full buffer. The existing JSON
validator and physical compilation still perform meaningful work on a hit. Compare the
whole hit path with the current file store before retiring it.
[Binary storage and fetch](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L307)
· [Fast-path retrieval](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L2784)

Here file storage occurs before the metadata transaction. A process crash can leave an
unreferenced value file. `check(fix=True)` can remove that file while a live writer is
between the file write and the SQL transaction, even though the check holds a database
writer lock. Keep repair out of routine pruning. Run it on a quiesced disposable store,
or replace that store as a maintenance action. A concurrent eviction between row
selection and opening a value file is a miss and must be recoverable.
[Integrity check implementation](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L3643)

**Alternatives and cutover.** The current file store has exact per-entry content checks,
private directory descriptors and coordinated writer cleanup. Keep it for D2 until the
fork both preserves the required boundaries and removes enough storage machinery to
justify the transition. `FanoutCache` divides the total limit across shards, which can
starve one large artifact even when total capacity is ample. Its explicit mutation
methods can translate timeouts to false and its retrying mappings obscure failure
classification. Reconsider sharding only if distinct-key write contention is observed
after isolating D2 and D4. A disk-only design would charge SQLite and decoding on
warm in-process hits. A process-only design would repeat eligible rendering and
derivation after each CLI exit. The intended end state keeps both lifetimes where each
avoids real work and keeps one active persistent implementation per tier.
[Shard layout and retry behavior](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/fanout.py#L61)

**Acceptance example.** Under the exact offline D2 entry point, a fresh process renders
and publishes once and a second process validates and hydrates without rendering. A
material renderer or input change misses. Frozen output, prerequisite checks and
`no_native_change` agree with independent native parity. Kill a writer before
publication and check that a later process can derive and install safely. Demonstrate
that the size of legitimate program sets fits the real disk and memory policy, including
encoded bytes and hydrated values. Start the adopted tier cold in a new format namespace
and remove the superseded active read/write path and its mechanism-only tests. Remove
the shared file-store publication, temporary writer leases, locking, and pruning code
after its last consumer migrates. Old cache data is disposable and can be reclaimed
under the cache owner, independently of retained products and evidence.

<a id="O03"></a>
### O03 · Make the process and disk tiers cooperate explicitly

**Proposed.** Keep the cachetools owners and place the persistent fetch beneath the
existing T2/T4 loader. After the consumer establishes eligibility and acquires any
required native authority, a process hit returns an inert value. A process miss checks
a verified persistent result and promotes it within the process budget. Both misses
lead to derivation, optional persistent publication, and local retention. A failure to
retain at either tier leaves the successful result usable for that request. Disk eviction
does not change the semantic validity of an already verified process value. Incompatible
identity never reaches the old entry. Preserve the independent protocol/codec format
version on disk and cursor semantics above it.

`cached` can accept a general mapping, but giving it a diskcache mapping would
mix local metadata locking with SQLite and blur storage admission, decoding and
derivation faults. Its insertion path also catches `ValueError`. Keep explicit disk
calls and the process coalescer. T4 futures share failures, handle nested requests and
bound waiting. A cachetools condition is wrapper-local, waits without a deadline and
wakes its peers after a failed or oversized load, allowing recomputation. Keep it for
the pure T1/T2/T3/T5/T6 loaders where the existing discipline fits. A consumer that
needs a new lifetime should register through the existing owner before introducing
another cache mechanism. [Cachetools wrapper implementation](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/_decorator.py#L174)
· [Thread tests](https://github.com/tkem/cachetools/blob/v8.0.1/tests/test_threading.py#L96)

Keep MCP process-first. Consider opening D4 for its existing selected-reader scope
only if repeated server starts or CLI/MCP reuse justify it and both acquire the same
validated basis independently. Do not share across mismatched role scopes for the sake
of a hit. Retain only encoded rows, immutable derived values and owned preparation,
with explicit lifetime for graph objects, request streams, device allocations and
connections. The in-process pickle used internally by `DerivedRows` never becomes
the persistent format. [Serving implementation](../../python/corpus-structure/src/corpus_structure/semantic/selected_query_cache.py)

<a id="O04"></a>
### O04 · Explain admission, eviction and usable hits through current tools

**Proposed, independent of migration.** Extend the typed observations behind
`ci cache stats`, `ci cache prune` and the process-scoped MCP observation.
Differentiate a process hit, verified disk hit, fresh derivation, oversize skip and
unavailable or corrupt store. Keep request reuse explanations with the request owner.
An observed cache hit must denote a value the consumer could actually use. Per-wrapper
`cache_info` is lookup accounting and already supports process diagnostics. Use an
`LRUCache.popitem` hook for capacity removals on shared weighted tiers, attributed
to the namespace of the displaced entry. Account for rejected weights at admission.
`popitem` has a separate lifecycle from `clear`, explicit deletion and timed
`expire`. Keep process counters labeled by process/generation and avoid treating
a fresh CLI snapshot as historical hit rate. [Capacity implementation](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/__init__.py#L62)

For disk, prefer least-recently-stored eviction to avoid updating each hit, and keep
SQLite's own persistent statistics off in ordinary requests. Enabling `stats` or
selecting disk LRU/LFU promotes ordinary reads to writes. An inspection should neither
materialize a missing store nor toggle shared statistics. Report library
`volume()` as an estimate of database pages and recorded external values. WAL,
staged files, orphans and physical free space have separate meanings. Keep explicit
per-value admission limits and interpret `size_limit` with `cull_limit` as best-effort
retention. Use explicit `cull` or `expire` in the owning prune path with attributable
partial results on contention. Use a tag/index only for a concrete group-wise cleanup
such as retiring a format within a store. Versioned directories are simpler when
cleanup always retires the whole format. Fork options for tag-filtered `iterkeys`
and stored timestamps can support bounded diagnostics without decoding entries.
[Eviction policy](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L123)
· [Stats and volume](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L4083)

**Acceptance example.** With deliberately small budgets, run an eligible reuse,
induce one capacity removal and one oversize skip, and inspect typed results. Pruning
a selected tier reports attributable removals without touching another cache or any
managed result. An empty or read-only view explains availability without initializing
a writable store or resetting counters.

<a id="O05"></a>
### O05 · Tune cachetools policy where workload evidence supports it

**Proposed.** Keep weighted LRU for revision-oriented preparation, including T3 and
T5, and the dual bound for T4. `getsizeof` charges on insertion. Retained values
therefore need stable weights and explicit accounting for backing allocations where
those matter. Archive and worker preparation should assess the combined live set
of byte buffers, decoded projections and other references before raising limits.
Do not attach resource retirement to eviction. A native handle or GPU worker keeps
its lifecycle owner throughout. Use ordinary small pure memos for cheap grammar
and lookup helpers whose consumers already fit that contract.

Use `TTLCache` only for an identified age-based retention policy and `TLRUCache`
with a `ttu` and controlled clock only when values have a meaningful individual
deadline. Expiration is lazy and a reclaiming `expire` call returns removed pairs.
The domain identity and authorization continue to govern freshness. None of the
current versioned artifacts has a deadline that warrants changing its cache class.
LFU's least-recently-used tie handling could be useful for a stable hot parser
population if observed churn warrants a change. FIFO and random replacement lack
a benefit for the inspected workloads. Use `cachedmethod` for future genuinely
instance-owned state with a mutable instance dictionary. A weak mapping can avoid
extending object lifetime but cannot promise reuse or a byte bound. Keep explicit
semantic key functions. `hashkey` distinguishes positional and keyword calling
shapes, and `methodkey` excludes the instance. Version 8 callable wrappers and
descriptors require following `__wrapped__` and the declared loader during code
custody, even when the wrapper itself is an implementation detail.
[Timed caches](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/__init__.py#L694)
· [Descriptor](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/_descriptor.py#L29)
· [Key functions](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/keys.py#L22)

<a id="O06"></a>
### O06 · Revisit offline packs and portable numerical preparation when demanded

**Proposed, conditional.** A developer repeatedly authoring offline from one frozen
release could benefit from a prebuilt, read-only cache of disposable artifacts. The
fork's `Cache(read_only=True)` disables hit/access writes and requires an existing
database. Its nonwritable-directory route may opt into SQLite immutable mode, which
assumes the underlying files stay fixed. A distributed snapshot would need to capture
committed SQLite state and its external values together. Start with ordinary private
D2 reuse, and reconsider this variant when operators actually need repeated handoffs or
immutable mounts.

Repeated archive hydration for separate commands and spawned CPU preparation are
plausible next candidates if T3/T5 traces show the same portable preparation dominating
cold start. Keep release archive authorization and artifact provenance. Cache a typed
serializable intermediate, with a distinct byte budget, only when reading it avoids
material work after validation. Avoid persisting live pipelines and the compiled-model
object by default. Consider `SafeDisk.with_numpy()` for a demonstrated expensive
pure CPU array derivation that has no already published domain output. A candidate
must preserve dtype, shape and versioned identity. E5 vectors already have native
publication and retrieval; another persistent embedding holder would need a distinct
consumer and a complete key. Existing Arrow/typed artifact formats remain the baseline
for portable arrays. [Read-only route](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L1882)
· [NumPy implementation](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/core.py#L953)
· [NumPy tests](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/tests/test_safedisk_numpy.py)

<a id="O07"></a>
### O07 · Keep local coordination subordinate to managed execution

**Proposed disposition.** Use atomic `add` to publish reusable values. Decline
`Cache.memoize` for D2/D4 because argument keys do not establish the project's
semantic identity or current authority. `memoize_stampede` can refresh expiring
external data probabilistically in a daemon thread, with duplicate cold calls and
hidden work on an otherwise usable hit. A real time-sensitive, expendable external
observation would be a reason to revisit it. `Lock`, `RLock`, `BoundedSemaphore`
and throttling use local persistent coordination with eviction and expiry requirements.
For example, a lock that expires while a worker is active can admit a successor, and
a later unconditional release can delete the successor's key. These primitives cannot
establish exact ownership, bounded waits or physical retirement of the execution host.
[Recipes](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/recipes.py)

`Deque`, `Index`, `push`/`pull`/`peek`, atomic counters and named shard
collections can support expendable local prefetch or cross-process collection when
there is a named consumer. A destructive pull has no acknowledgement or leased
redelivery, so authoritative corpus work, operator tasks and managed test-result
custody remain with their existing owners. The present operator tools need clearer
diagnostics rather than another queue. Django integration has no consumer here.
Both libraries are synchronous, so use existing thread/worker boundaries if an async
consumer gains a persistent lookup. [Persistent collections](https://github.com/secondwindoss/diskcache-community/blob/v5.8.5/diskcache_community/persistent.py)

## Recommended sequence

1. Improve typed observations with O04 and retain the cachetools policies in O05.
   Continue UDM-10 determining-workload closure as the prerequisite for actual D2, T4
   and T14 reuse. Qualify existing semantics independently from the backend choice.
2. Select O01 as the first persistent cutover and integrate O03 at the authorized
   serving owner. Retire the old D4 path at cutover. Recheck real T4/T14, including
   storage-only change versus semantic cursor compatibility.
3. Select O02 after exact D2 identity and comparison of full-size hydration, storage
   use, interruption and repair. Move D2 only if the simpler implementation meets
   its existing correctness and lifecycle contracts. Keep O06 and O07 conditional
   on the identified consumer or workload trigger.

Later implementation planning should carry these opportunity IDs, library contracts
and consumer acceptance examples. This review proposes the deployment; the UDM
coordinator owns current implementation and qualification status.
