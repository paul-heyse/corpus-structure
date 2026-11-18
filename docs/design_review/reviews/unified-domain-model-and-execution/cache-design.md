# Cache design for the production package (supporting document)

**Role.** This document holds the cache design of the design review of the production package
(principal document: [review.md](../design_review_unified-domain-model-and-execution_2026-11-18.md), recommendation R09). It carries no separate verdict
and no disposition ledger; dispositions are in [dispositions.md](dispositions.md) and the
overall judgment is in the principal review.

**Revision note, 2026-11-18.** An independent recommendation audit from input revision
`b4eb74f67` reviewed this design for the operator's concern about intentional flexibility and
found the cache design untouched by it. Two clarifications follow from the revised review: a
served query that declares no reuse basis uses `cut` (§4 T4), and the compiled model's
declaration validator also yields the list of unclassified declarations (§4 T1, review R16). See the
[audit companion](../audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md).

**Revised to current source, 2026-11-18.** An independent reviewer revised the principal review
against source `5139eaba3` from input revision `c25cada3f`, consuming the diagnostic audit as
updated at that source (its rebuilt [cache inventory](../../audit/model-and-execution.md#cache-inventory)
and [identity inventory](../../audit/model-and-execution.md#identity-inventory)). This design was
checked against that update and **stands**: no key, bound or invalidation premise below moved,
because the owners it migrates (the query cache, the archive cache, the grammar memos, the spaCy
holder, `semantic/metadata.py`, the wire caches apart from one line shift) have no change of
substance in the range, and cachetools is still pinned at 7.2.7. The deltas are recorded where they
fall, marked "Revision of 2026-11-18": a new content-keyed holder for the companion projection
(§4 T1, §8), the removal of the per-request CPU global (§8), a larger native capture with the same
rebuild pattern (§1, §4 T2), and no new tier candidate from the rebuilt inventory (§8). The judgments
recorded with that mark are the revising reviewer's.

**Baseline.** Source facts are from the frozen snapshot of commit `d78c98765`, Interface-checked
by source inspection on 2026-11-18; facts marked "Revision of 2026-11-18" are from `5139eaba3`. Paths omit `python/corpus-structure/src/corpus_structure/`.
Every design statement is **Proposed**. No speedup is claimed anywhere; where a tier removes
work, the work removed is named, and whether its removal is material is left unmeasured.

**Library basis.** cachetools 8.0.1 (the project pins 7.2.7 today). Library facts are labelled
**[doc]** (cachetools 8.0.1 documentation and changelog, as read by the library contributor on
2026-11-18), **[src]** (read by this reviewer in the 8.0.1 sdist at
`src/cachetools/_decorator.py`, 2026-11-18), or **[probe]** (run by this reviewer on synthetic
data, recorded in [review.md, Probes](../design_review_unified-domain-model-and-execution_2026-11-18.md#probes)). The contributor report
[cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) holds further probes; where this document relies on one of them it says so.

## 1. What the design has to achieve

The workload premise: book-scale processing with many operations per run; repeated focused
reads from a long-lived MCP server (one process, tool calls on worker threads) and from the `ci`
command line, which starts a new process per command and per page; model changes previewed,
replayed and deployed; one operator with several agents.

What exists today (verified in source, with the cache inventory helper's map):

- one `cachetools` cache (`semantic/selected_query_cache.py:15–86`), about 94 `functools`
  caches (about 55 of them cheap lookups), about 75 `cached_property` sites and about a dozen
  hand-built holders (`semantic/archive_reader.py:34–38, 396–434`; `methods/math/grammar.py:309–327,
  966–993`; `semantic/file_custody.py:79, 96`; `_query_custody.py:134–135`;
  `semantic/metadata.py:32–50`; `methods/native_host.py:646–944`;
  `orchestrate/execution_host.py:186–272`; `semantic/cpu_execution.py:148–228`);
- bounded caches built four ways (a `cachetools.LRUCache` with a hand entry cap, `lru_cache`,
  hand `OrderedDict` LRUs, plain dicts), and some unbounded holders in long-lived processes
  (`methods/math/grammar.py:309–327`; `ingest/sentences.py:58`, an unbounded `functools.cache`
  holding a spaCy pipeline; `semantic/constructions/forest.py:36`);
- no coordination of concurrent identical misses anywhere;
- invalidation only by new key, which is sound only where the key is complete;
- every cache process-local, so the command line gets no reuse across commands or pages
  (`cli/selected_results.py:90–130`);
- the most expensive derived artifact, the native program capture, with no holder at all, rebuilt
  twice per `require_data_operation_native` call on the execution path
  (`semantic/data_operation_storage.py:1116–1131`) and three times per definition admission
  (`:1535–1558`) ([DA-083](../../audit/execution-fit.md#da-083));
  (revision of 2026-11-18: unchanged at `:1127–1142` and `:1561, 1571`; each rebuild is larger,
  99 captured modules and about 46 generator invocations);
- the physical model compiled at import as a module global in every importing process
  (`semantic/metadata.py:32–50`), not reused by the capture, which compiles it again
  (`semantic/data_operation_storage.py:123–136`);
- tool calls on MCP worker threads reaching unlocked mutable memos
  (`methods/math/grammar.py:966–993`) (review finding F02).

The design's job is therefore less "add caches" than: give the expensive derived artifacts one
holder each, keyed by the identity the model and the program set declare; make concurrent
misses coalesce; bound everything that lives in a long-lived process; and give the command line
a cross-process route for the two kinds of work it repeats (generated program sets during
authoring, and served result pages during paging).

## 2. Rules the design follows

1. **A key is a declared identity, never a carrier object.** Every key is built from a
   model-derived or content identity (a model-sources identity, a program identity, a release id,
   a cut or content stamp, a derived code identity). A key function ignores non-determinants that
   travel with the call (connections, engines, acquisition objects). cachetools supports this
   directly: `cached(cache, key=...)` with a key function whose signature equals the wrapped
   function's **[src]**, ignoring arguments as needed ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §C, probed).
2. **In-process keys omit process constants; disk keys include them.** Inside one process the
   installed library versions and the imported code are constant (code custody refuses drift),
   so an in-process key need not repeat them. A key written to disk must include them, with a
   format version.
3. **Preparation reuse and result reuse are separate tiers** (heuristic H12, DP-09). A compiled
   model or a program set is preparation; a served page is a result. They have different keys,
   bounds and failure handling.
4. **Invalidation is identity first.** A new identity makes old entries unreachable everywhere at
   once. Event clears exist only to give memory back, and are published after the new identity
   is visible, so an in-flight load lands under a dead key (cachetools has no generation fence:
   a `cache_clear()` during a load is followed by the load re-inserting its value **[probe]**).
5. **Drift in Python code refuses; drift in declarations rebuilds.** File custody and query
   custody keep refusing when imported Python changes underneath a process (the process cannot
   reload code safely). Model sources are data: when their bytes change, the model-sources
   identity changes and a new compiled model is built beside the old one, without a restart.
   This changes a current rule (review RC09).
6. **One owner module, no framework.** One module registers the process-wide caches, sizes them
   from settings, lists them, and clears them on a closed set of events. A separate small module
   owns the on-disk store. Neither offers decorators beyond one `declare` helper.
7. **What has no identity is not cached** ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §G rule 1).

## 3. The tiers at a glance

| Tier | Holds | Key (identity) | cachetools class and bound | Coordination | Invalidation | Owner |
|---|---|---|---|---|---|---|
| T0 Custody | File and code custody records (not a cache; the premise check other tiers rely on) | Path and digest | Unchanged hand dicts under one `RLock` | Lock | Stat change re-hashes; changed bytes refuse | `semantic/file_custody.py`, `_query_custody.py` (generalized to code custody) |
| T1 Compiled model | One `CompiledModel` per model-sources identity, with lazily derived projections | Model-sources identity | `LRUCache(maxsize=4)`, count | `cached(..., condition=Condition(RLock()), info=True)`; deterministic compile errors cached as values | Identity; event `model` | Model compiler module |
| T2 Program set | One `ProgramSet` per model identity and generator code identity | Model-sources identity (plus explicit candidate sources) | `LRUCache(maxsize=2)`, count | As T1 | Identity; event `model` | Program registry module |
| T3 Releases and archives | Prepared releases, opened archive projections, prepared PDF lowering sources | Release inputs or `(database identity, release id, archive header digest)` | `LRUCache(maxsize=bytes, getsizeof=retained artifact bytes)` | `condition` | Identity; header re-read per call as premise check; event `release` | Release module |
| T4 Served results | Derived row entries; shared per-product indexes; change-impact comparisons | `(query id, selection digest, implementation identity, authorization scope, reuse basis)` | `SizedLRU`, an `LRUCache` subclass with `getsizeof` plus an entry cap | Future-based single-flight that shares failures | Identity; events `release`, `kernel` | Serving module (today `semantic/selected_query_cache.py`) |
| T5 CPU runtimes | Loaded CPU pipelines, matchers, compiled packs (not GPU residency) | `(artifact digest, configuration, runtime version)` | `LRUCache(maxsize=bytes, getsizeof=declared footprint)` | `condition` | Artifact digest via custody | Method runtime modules; native host and execution host keep their own lifecycles |
| T6 Memos | Grammar parsers, parse memos, small pure derivations | Normalized call arguments | `cachetools.func.lru_cache(maxsize=n)` or `functools.lru_cache` | Built in | None, or `cache_clear()` on event `model` where a memo depends on model content | The owning module |
| D2 Program store (disk) | Rendered program bytes, program identities, manifest | Model-sources identity, generator code identity, library versions, format version | Directory bounded by a byte budget, pruned oldest first | Write-once, atomic replace | Identity | `cache_store` module |
| D4 Result pages (disk) | Encoded rows of a served result | As T4 with the cut as basis, plus library versions and format version | Byte budget, pruned oldest first | Write-once, atomic replace | Identity | `cache_store` module |

Tiers T1 to T6 are in-process; D2 and D4 cross processes. An optional D1 (materialized model
schema on disk) is discussed in §6 and not recommended until per-command model compile is
observed to matter after T1 makes it lazy.

## 4. Tier by tier

### T0 — Custody (kept; generalized)

File custody (`semantic/file_custody.py:20–140`) authenticates a file once per process and
re-checks its stat identity on each use, re-hashing on change or inside a two-second racy window,
and refusing changed bytes. Query custody (`_query_custody.py:130–200`) compiles exactly the
hashed bytes of listed query helpers and refuses a reload. Both are sound and are the premise
check that makes held in-process tiers safe while the working tree changes.

**Change.** Generalize query custody into *code custody* for every package whose code determines
an identity (served read helpers, program generators, PDF lowering entry modules), with the list
of covered modules derived from the static import closure of declared entry modules instead of
being hand-kept (review R05). The loader mechanism, the restart semantics and the shared
`observed_file` primitive stay. The derived closure replaces `_query_custody.py:17–127`,
`semantic/demand_queries.py:117–124`, `semantic/pdf_lowering.py:33–104` and the capture's fresh
disk reads (`semantic/data_operation_storage.py:184–191`), and so also removes DA-083's
hermeticity gap (generated SQL and recorded module bytes from different code).

T0 records are finite (one per file) and stay unbounded. They register with the owner module for
listing only.

### T1 — Compiled model

**Holds.** A `CompiledModel` built from one model-sources capture: the merged LinkML
`SchemaView` of the released model closure, built by the one composer that replaces the
per-consumer routines (`semantic/prepare.py:350–373`, `semantic/native_call_sources.py:95–117`,
`semantic/projection_analysis_products.py:85–107`, `semantic/companion_projection.py:552`, and the
single-purpose views in `semantic/rule_views.py:402`, `semantic/conditional_rules.py:178`,
`semantic/ontology.py:159, 260, 626`, `semantic/source_value_native.py:56`). Its projections are
derived lazily on the immutable object: physical `MetaData` and read `MetaData`
(today `semantic/metadata.py:32–50`), the prepared wire protocol and its validators (today
`semantic/data_operation_wire.py:46–485`), expanded value sets (through the project's one
`expand_enum`; LinkML's `induced_enum` does not expand `inherits`, `include` or `minus`,
[data-model library report](../../evidence/2026-11-18_production-review-inputs/library-data-model.md) F6), the field-kind type map, Arrow schemas for model relations and views, the
role and grant matrix, the support-edge traversal table, the operation-declaration validator
(with its warnings and list of unclassified declarations, review R16),
and the scientific policy recipe (review R14).

**Key.** The model-sources identity: a framed SHA-256 over the sorted `(name, bytes)` of the
captured closure (LinkML schemas including the pinned `linkml:types` bytes, the native protocol,
the logical catalogs, and a pack when a release supplies one) plus a compiler interpretation
version constant. The physical sub-identity stays as today's `physical_sources_id`
(`schema/physical.py:142–151`) and becomes one projection of the capture. Excluded on purpose:
paths, stat metadata (custody's job), release id and runtime (a release *uses* a model; it does
not change it), and installed library versions (process constants in memory; included on disk).

**cachetools.** `LRUCache(maxsize=settings.cache.model_entries)` with a default of 4 (current
checkout, a model-change candidate, the previous model, one spare), bounded by count because
entries are few, large and not cheaply measurable (`sys.getsizeof` is useless for object graphs,
[cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §A). The builder is wrapped with
`cached(cache, key=lambda sources: hashkey(sources.identity), condition=threading.Condition(threading.RLock()), info=True)`.
The condition gives per-key single-flight inside the wrapper **[src, probe]**: nine threads over
two keys ran the loader twice. Compile failures (`ModelError`) are deterministic for given
bytes, so the builder returns them as values and the accessor re-raises them (negative caching
of deterministic absences, [cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §D); otherwise every waiter would recompile the
failure in turn, because cachetools does not share a loader's exception with its waiters
**[probe]**.

**Projections.** Derived with `functools.cached_property` on the immutable `CompiledModel`. Since
Python 3.12 `cached_property` takes no lock, so two threads may compute the same projection
once each; the result is identical, so this is waste, not error. The two projections nearly
every consumer needs (physical `MetaData` and the merged view) are built inside the
single-flight builder, so only rarely used projections can be computed twice.

**Resolving "the current model".** `current_model()` builds the model-sources capture of the
checkout through `observed_file` for each closure file (one stat per file per call after the
first hash), computes the identity and looks it up. A changed YAML file yields a new identity
and a new entry without restarting the MCP server; the old entry stays valid for anything pinned
to it and ages out. A release opened from its archive supplies its captured closure and gets its
own entry. `semantic/metadata.py`'s module globals (`metadata`, `tables`, `table()`,
`PHYSICAL_MODEL_ID`) become accessors over `current_model()`, so a command that never touches
the physical model no longer compiles it at import.

**Invalidation and events.** Identity in the key. The event `model` (published after a model
change is applied, `schema/model_change.py` apply path) clears the tier to give memory back.

**Revision of 2026-11-18.** The companion projection now holds its captured inputs and its
projections in two `lru_cache`s keyed by the PDF domain contract, whose captured sources are its
content identity (`semantic/companion_projection.py:561–617, 620`). That is the T1 key premise
applied to one consumer, and it is sound; it also composes its own view and compiles the physical
model once more (`:587`). In the target it becomes a projection of the T1 entry for the same
captured sources, so the separate compile goes and the key stays content. Its `target_metadata`
argument is keyed by object identity; under T1 the metadata is itself a projection of the entry, so
that argument disappears from the key.

**Repeated work removed.** The import-time double compile in every importing process
(`semantic/metadata.py:32–50`); the physical compile inside every capture
(`semantic/data_operation_storage.py:123–136`); eight separately composed `SchemaView`s; the
protocol caches keyed by the whole capture tuple, which hit only after hashing every artifact
(`semantic/data_operation_wire.py:52, 261, 414`; DA-083 adjacent fact); the scientific recipe
rebuilt at three comparison sites (DA-077).

**Test seam (one line).** Tests that import the module-global `semantic.metadata.metadata` move
to the accessor; the test review owns that change.

### T2 — Program set

**Holds.** A `ProgramSet`: the program declarations collected by the typed program registry
(review R04), the rendered bytes of each program, each program's identity (digest of its
rendered bytes), the kernel identity (digest over the sorted `(program name, program identity)`
of the programs that are installed), each validity family's validator identity (review R05),
the rendered Python facades, and the generator provenance (code-closure identity of the
registered generator modules, the per-module digests and the versions of the distributions they
import).

**Key.** In process: the model-sources identity of the `CompiledModel` the generators read, or
the identity of explicitly supplied candidate sources. The generator code identity is constant
in a process because code custody refuses drift, so it need not be in the in-process key. On
disk (D2): model-sources identity, generator code identity, versions of the distributions the
generator closure imports (pglast, sqlalchemy, linkml-runtime and so on, derived from the
closure rather than listed), and the store format version.

**cachetools.** `LRUCache(maxsize=settings.cache.program_sets)`, default 2 (running and candidate),
count-bounded, wrapped with `cached(..., condition=Condition(RLock()), info=True)` and negative
caching of deterministic generation errors, as in T1.

**Who uses it.** Only authoring paths: preparation (`semantic/data_operation_preparation.py:261`,
`semantic/primary_operations.py:403`, `semantic/regeneration.py:331`), candidate definitions
(`semantic/data_operation_storage.py:1844`), the model-change preview (`schema/model_change.py:603`
and the facade rendering at `:525–552`) and the compilation fingerprint. **The execution path
does not use T2 at all**: `require_data_operation_native` stops regenerating and compares the
installed descriptor with the kernel identity the prepared release already records (review R06,
finding F01). The demand export reads its wire schema from T1's protocol projection instead of
regenerating the capture (`serve/demand_export.py:281`).

**Repeated work removed.** On the execution path, all of DA-083's rebuilds (two per port
acquisition, two per cached-port recheck and publication-port acquisition, three per definition
admission). On authoring paths, the second and third full rebuild inside one preview command, and
one rebuild per export.

### T3 — Releases and archives

**Holds.** Immutable prepared releases (`semantic/prepare.py:599`, today `lru_cache(maxsize=8)`
retaining up to eight full artifact sets), opened archive projections
(`semantic/archive_reader.py:396–434`, today a per-engine `WeakKeyDictionary` of hand-built
`OrderedDict` LRUs capped at eight), PDF boundary releases (`semantic/pdf_contracts.py:55`) and
prepared lowering sources (`semantic/pdf_lowering.py:168`).

**Key.** For preparation, the existing determinants (bundle, resolved dependencies, profile,
installed stack), which already identify the release. For opened archives,
`(database identity, release id, archive header digest)`, where the database identity is the
cluster's system identifier with the database name, read once per engine. The engine object
leaves the key, so per-call engines no longer defeat the cache (the residual recorded for
PE-F16, which the DDO plan owns; this design affects it and does not re-own it).

**cachetools.** `LRUCache(maxsize=settings.cache.release_bytes, getsizeof=lambda r: r.retained_bytes)`,
bounded by bytes, where `retained_bytes` is the sum of the release's artifact byte lengths,
recorded by the builder. A value larger than the bound is not admitted and is returned uncached
(cachetools swallows the `ValueError` on insert **[src]**). `condition` single-flight on the
builder.

**Invalidation.** Identity. The per-call re-read of the archive header against the cached entry
stays: it is the premise check, and it is cheap. Event `release` clears for memory.

**Left with their owners.** The execution host's verified bases and capsules
(`orchestrate/execution_host.py:186–272`) and the CPU workers' hydrated releases
(`semantic/cpu_execution.py:148–228`) have lifecycles fixed by ADR-0125 (reference counts, a byte
budget, idle eviction, quarantine). They register with the owner module for listing only.

### T4 — Served results

**Holds.** The existing immutable `DerivedRows` entries (`semantic/selected_query_cache.py:22–56`),
plus two shared derived structures the audit identified as rebuilt per query: the rich graph
index over a whole selected admission (`semantic/rich_queries.py:196–260`; the audit's lead
"one validated graph index shared by every query on that product") and the change-impact
comparison rebuilt for every page (`semantic/change_impact.py:687–777`).

**Key.** A typed `ServedKey`:

- the query identity: the served query's declared id and the digest of its normalized selection
  and budgets;
- the implementation identity of the served read: the derived code-closure identity of its
  entry modules plus the identities of the native read programs it calls (review R05; replaces
  the hand lists of DA-076);
- the authorization scope: the principal or purpose role under which native authority was
  acquired, unless the query is shown to be authority-independent;
- the reuse basis, declared per served query and `cut` when undeclared: `cut` (the cut identity, as today, sound now) or
  `content` (frontier content stamp, release and runtime, without the read instance), which a
  query may declare only after the native owner has established that its derived rows are a
  function of frontier content (DA-075's open premise). Until then every query except the
  identity-exclusion comparison keeps `cut`.

**cachetools.** Keep the existing byte-accounted `LRUCache(maxsize=32 MiB, getsizeof=...)` but
move the hand entry cap into a small subclass, `SizedLRU`, whose `__setitem__` also pops entries
while the count exceeds the cap (one cache has one capacity measure in cachetools, so two
simultaneous bounds need a subclass, [cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §A). Per-entry limits stay (8 MiB, 4,096
rows). Hits keep returning fresh decoded rows from immutable bytes.

**Coordination.** The serving path uses the cache through explicit `get` and `put` around
`bounded_rows`, not through a decorator, and its loaders can fail for reasons the waiters should
share (an authority refusal, a cancelled read). So T4 uses the future-based single-flight recipe
([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §J.2): an in-flight map from key to `concurrent.futures.Future`, guarded by
the tier lock; the first caller derives and sets the result or the exception; the others wait on
`future.result(timeout=...)` and receive the value or the exception. Every caller still
re-acquires native authority *before* looking up the cache, exactly as today
(`semantic/selected_query_cache.py:1–10` docstring); only the derivation is coalesced, never the
authority check, and the authorization scope is part of the key.

**Statistics.** cachetools' `CacheInfo` exists only on decorated wrappers, so T4 keeps its own
counters: hits, misses, coalesced waits, refused admissions (too large), and evictions.

**Invalidation.** Identity. Events `release` and `kernel` clear for memory.

### T5 — CPU runtimes

**Holds.** Loaded CPU pipelines and matchers that today live in unbounded or ad-hoc caches in
long-lived processes: the spaCy pipeline (`ingest/sentences.py:58`, unbounded `functools.cache`),
spaCy vocabularies and matchers (`semantic/constructions/retained_rules.py:32, 191, 257, 1216`),
compiled native packs (`methods/native_host_adapters.py:111`, nested `lru_cache`), Lark grammar
prototypes (`semantic/constructions/forest.py:83`).

**Key.** `(artifact digest from custody, configuration, runtime version)`.

**cachetools.** `LRUCache(maxsize=settings.cache.runtime_bytes, getsizeof=declared footprint)`
with `condition`. The footprint is declared by the loader (for example the summed model-file
sizes), because process memory is not visible to cachetools. These values hold native memory
but no OS handle that needs explicit closing, so dropping the reference on eviction is enough; the
lease-and-retire `ResourceLRU` pattern of [cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §H is needed only if a runtime with
handles joins the tier (its hooks must cover `__delitem__` and `clear`, because `clear()`
bypasses `__delitem__` **[probe]**).

**Not in T5.** GPU residency (`methods/native_host.py:646–944`) is a lifecycle state machine with
active-call tracking, quarantine, suspension and an idle timer; cachetools has no idle expiry and
no lease, so it stays its own owner ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §H). The Chandra runtime of DA-058 would
belong here (held across rounds, checkpoints authenticated through `verified_file`), but Chandra
is outside scope by operator direction; see the deferral in [dispositions.md](dispositions.md).

### T6 — Memos

**Holds.** Grammar parsers and parse memos (`methods/math/grammar.py:309–327, 966–993`) and the
remaining small pure derivations.

**cachetools.** The macro-class parser families, unbounded dicts today, become
`cached(LRUCache(maxsize=settings.cache.parser_entries), key=..., condition=Condition(RLock()))`,
because an Earley parser is expensive to build and is requested from tool threads. The 8,192-entry
parse memo, a hand `OrderedDict` mutated without a lock today, becomes
`cachetools.func.lru_cache(maxsize=8192)`, which is locked and single-flight by default
(`cached(..., condition=Condition(), info=True)` **[src, [cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §B]**). Whether eviction
of parsers is safe depends on rebuild cost against memory; the bound comes from settings and is a
tuning value, not a correctness one.

## 5. The owner module

One plain module, `corpus_structure/caches.py`, about sixty lines:

```python
# Sketch only. Names are proposals.
EVENTS = frozenset({"model", "release", "kernel"})

def declare(name, tier, *, key, events=(), cls=LRUCache, getsizeof=None):
    """Build the tier's cache sized from settings.cache[tier], a Condition(RLock()),
    and return cached(cache, key=key, condition=cond, info=True). Registers the entry."""

def register(name, tier, cache, *, lock, events=(), counters=None):
    """For explicitly used caches (T4) and lifecycle owners listed for statistics only."""

def snapshot() -> list[CacheRow]:
    """name, tier, len, currsize, maxsize, hits, misses (from cache_info() or counters)."""

def clear(event: str) -> None:
    """For each entry listening to event: with entry.lock: entry.cache.clear()."""
```

- Sizes come from one typed settings object, `CacheSettings`, read once at `declare`; a resize
  builds a new cache and swaps it under the lock, because `maxsize` is fixed after construction
  ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §I).
- Events are a closed vocabulary. Publishers call `clear(event)` after their new identity is
  visible; keys carry that identity, so an in-flight load lands under a dead key.
- `snapshot()` is exposed through one MCP diagnostic tool for the long-lived server and through
  `ci cache stats` (which also reports the disk tiers). `ci cache prune` trims the disk tiers.
- Worker processes are started with spawn or forkserver contexts
  (`semantic/cpu_execution.py:688`; `semantic/pdf_publication.py:662`; `ingest/pdf_worker.py:141`;
  `ingest/pdf_chandra.py:258`), so children start with empty caches and fresh locks; no
  `os.register_at_fork` hook is needed unless a fork context is introduced.
- The same module wires `AnalyticsSettings` (threads, memory limit, scratch path) into DuckDB
  connection configuration, so those settings stop being unread (DA-080, review F03).

## 6. Crossing processes

cachetools provides no persistence or cross-process sharing **[doc]**. What must cross processes
is decided by who repeats the work:

| Work | Repeated across processes? | Crossing route |
|---|---|---|
| Generated program set | Yes: preview, candidate preparation and deployment preparation are separate `ci` commands | **D2**, content-addressed files |
| Served result pages | Yes: each CLI page is a new process | **D4**, content-addressed files for continuation pages |
| Compiled model | Yes: every CLI command that touches the model | Not now. First make it lazy (T1); revisit D1 if per-command compile is observed to matter |
| Opened releases, runtimes, resources | Per process by nature | None; they are rebuilt from durable inputs |

**The store.** A small module, `corpus_structure/cache_store.py`:

- Layout: `<cache root>/<tier>/<format version>/<key digest>/` holding a JSON manifest that lists
  each content file with its digest, plus the content files. The cache root comes from settings
  (default under the user cache directory), created with mode 0700.
- Write: build in a temporary directory beside the target, then `os.replace` (atomic on POSIX).
  Entries are write-once and keyed by content identity, so two concurrent builders write the
  same bytes and the second replace is harmless; no lock file is needed.
- Read: verify each content file's digest against the manifest (a cheap re-hash of bytes about to
  be used); on mismatch delete the entry and rebuild.
- Format: JSON manifests, raw `.sql` bytes for programs, canonical JSON lines with an offset index
  for result pages (the same encoding the CLI emits). **Never pickle**: the pickle stream format
  of caches is not stable across releases **[doc]**, and a pickled file is a code-execution trust
  boundary.
- Bound: a byte budget per tier from settings, enforced at write time by deleting the oldest
  entries (by access time) and by `ci cache prune`. Deleting an entry another process is reading
  is safe on POSIX (an open file stays readable).

**D2, program store.** The key is described under T2. A preview, a candidate preparation and a
deployment preparation then compute the generator code identity (a static import closure and an
AST hash of the generator modules) and read the stored program set instead of running about 45
generators again. Whether that exchange matters is unmeasured; the in-process T2 already removes
the duplicates inside one command, so D2 is the second step, adopted when authoring latency is
observed to matter.

**D4, result pages.** For a continuation page the CLI already carries the cut identity in its
cursor. The key is the T4 key with basis `cut`, plus the served implementation identity, the
authorization scope and the format version. The first page's process derives the bounded entry
(at most 8 MiB and 4,096 rows, as today) and writes it; the next page's process re-acquires
native authority for the cut through the existing per-request recheck, then reads the stored
rows at the cursor's ordinal instead of re-reading support, reopening the release, binding the
model and re-validating the graph (`serve/rich_knowledge.py:118–130`;
`semantic/demand_results.py:431–473`). This is sound today, because a cut pins the frontier,
trust snapshot and visibility, and a revocation between pages still refuses at the authority
recheck. Fresh identical requests from separate CLI processes would need the `content` basis and
wait on DA-075's premise. The files hold rows the principal was authorized to read; they are
readable by the OS user that runs the agents, which can already read anything those agents read.

**Rejected crossing routes.** A daemon that the CLI talks to (keeps memory tiers warm, but brings
lifecycle, versioning and staleness on model change, H25; revisit if the lazy T1 still leaves
per-command model compile material). A PostgreSQL results table (right for multiple hosts or for
results that must honour row-level security without a native recheck; on one host, with an
authority recheck per call, files are simpler). `diskcache` 5.6.3 (pickles by default; last
release 2023). Persisting cachetools caches by pickling them.

## 7. What stays `functools` and `cached_property`

- About 55 cheap pure caches (enum and lookup tables, `TypeAdapter`s, regular expressions,
  `importlib.metadata` versions, Typer registration; for example `semantic/types.py:163`,
  `semantic/refusals.py:70`, `serve/rich_queries.py:66`, `cli/app.py:25`). `functools.lru_cache` is
  implemented in C and thread-safe in its structure; a duplicate computation under a race is
  harmless for cheap pure functions.
- Content-keyed parsers and compilers that are pure and bounded
  (`semantic/alias_policy.py:113`, `semantic/reference_positions.py:31`,
  `semantic/comparison_projection.py:176`, `semantic/projection_analysis.py:454`,
  `semantic/m1_products.py:47`, `semantic/python_module_projection.py:110`,
  `semantic/data_operation_model.py:1206`, `semantic/data_operation_static_preparation.py:66`,
  `semantic/execution_admission.py:284–419`). Their keys are content and their bounds are set.
- `cached_property` on immutable per-object state, including per-result decoded views
  (`semantic/native_source_view.py:128–212`, `semantic/demand_results.py:86`). They die with the
  object.
- Per-instance `lru_cache` wrappers on readers (`semantic/pdf_record_reader.py:268`,
  `semantic/pdf_payload_validation.py:32`): instance lifetime, fine.

## 8. Migration of existing caches and holders

| Today | Becomes | Note |
|---|---|---|
| `semantic/metadata.py:32–50` module globals compiled at import | T1 projections behind `current_model()` | Removes import-time compile from commands that do not need it |
| Per-consumer `SchemaView` composition (eight sites, §4 T1) | T1 merged view and projections | One composer |
| `semantic/data_operation_wire.py:46, 52, 261, 414, 450, 485` | T1 protocol projection; validators keyed by protocol content digest | The whole-capture tuple leaves every key |
| `semantic/companion_projection.py:547` (`SchemaView(str(MODEL))` from disk, keyed by a `MetaData` object); revision of 2026-11-18: also `:561–617, 620`, content-keyed holders over the captured PDF domain sources | T1 projection keyed by model identity | The new holders already key by content; they lose their separate physical compile |
| `semantic/pdf_contracts.py:81`, `semantic/pdf_lowering.py:107, 259`, `semantic/operation_reporting.py:63, 93, 118`, `semantic/pdf_records.py:33, 159, 165, 198` (no-argument process singletons reading package files) | T1 projections keyed by model identity, with custody for the files they read | Ends "first read in the process wins" for declarations |
| No holder: `native_protocol_sources()` | T2 (authoring only) and D2 | Execution path stops calling it (R06) |
| `semantic/prepare.py:599`; `semantic/pdf_contracts.py:55`; `semantic/pdf_lowering.py:168` | T3, bytes-bounded | |
| `semantic/archive_reader.py:34–38, 396–434` (`_OPEN_CACHE`) | T3 keyed by database identity, not engine | Affects the PE-F16 residual |
| `semantic/selected_query_cache.py` | T4 `SizedLRU` with future single-flight; D4 for CLI continuation | Byte accounting and immutable entries kept |
| Rich graph index per query; change-impact comparison per page | T4 entries | Keys per T4 |
| `ingest/sentences.py:58`, `semantic/constructions/retained_rules.py:*`, `methods/native_host_adapters.py:111`, `semantic/constructions/forest.py:36, 83` | T5, bytes-bounded | Bounds unbounded holders in long-lived processes |
| `methods/math/grammar.py:309–327, 966–993` | T6 (`cached` with `condition`; `cachetools.func.lru_cache`) | Removes unlocked mutation from tool threads (F02) |
| `semantic/scientific_evidence.py:192–255`, `semantic/rich_policy_binding.py:22–30` recipe per call | T1 projection derived from the policy declaration (R14) | Correctness fix first, caching follows |
| File custody, query custody | T0, generalized to derived code custody | Registered for listing |
| Execution host bases, CPU worker releases, native host residency | Unchanged owners (ADR-0125) | Registered for listing. Revision of 2026-11-18: cancellation is now bound per CPU invocation and the shared per-request global beside the worker releases is gone (`semantic/cpu_execution.py:359`, `5c5443d16`); worker releases stay unbounded within a worker's life, one entry per distinct capsule, which ADR-0125's lifecycle owns |
| About 55 cheap `functools` caches, content-keyed parsers, `cached_property` | Unchanged | §7 |
| Revision of 2026-11-18, rebuilt inventory: CPU call descriptors (`semantic/data_operation_cpu.py:189`, per worker, 64 entries); per-object `semantic_id` memos (`semantic/formal_products.py:150` and siblings); deployment expectation caches (`semantic/execution_admission.py`) | Unchanged | Each is content- or object-keyed and bounded or object-lived; none is a new tier candidate |
| Revision of 2026-11-18, repeated work with no holder: release-content re-proof in the generated guard; frozen catalog verification rebuilt from the frozen guard (`semantic/native_admission.py:85–110`); a full native revision for a digest-only change | Not caches | The first is carried assurance (review R11), the second is off the acquisition path and low consequence, the third is identity (review R05, RC15) |

## 9. cachetools 8.0: what the design relies on, and the limits

Relied on, with the API used:

- `LRUCache(maxsize, getsizeof=None)`: count or weight bound; on insert, `popitem()` runs until
  the item fits; a value larger than `maxsize` raises `ValueError`, which `cached` swallows and
  returns the value uncached **[src]**.
- `cached(cache, key=..., lock=None, condition=None, info=False)` **[src]**: with `condition`
  only, the condition is also the lock; a miss marks the key pending, computes outside the lock,
  stores with plain assignment and `notify_all()`s **[src `_decorator.py:66–100`]**. Wrapper
  attributes `cache`, `cache_key`, `cache_lock`, `cache_condition`, `cache_clear()`,
  `cache_info()` (public `cachetools.CacheInfo` in 8.0) **[doc]**.
- `cachetools.keys.hashkey`: in 8.0 keys are plain tuples; positional and keyword calls produce
  different keys, so identities are passed positionally ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §C, probed).
- `cachetools.func.lru_cache(maxsize)`: `cached(..., condition=Condition(), info=True)` **[src]**.
- Subclass hooks: eviction goes through `popitem` and then `__delitem__`; `del` and `pop` go
  through `__delitem__`; `clear()` bypasses both **[probe]**.

Limits the design works around:

- `lock` alone protects the mapping, not the computation: concurrent misses all compute, and
  the first stored value wins **[src]**. Hence `condition` for expensive loaders.
- `condition` gating is per key but waking is global (`notify_all`), so one condition per wrapper
  keeps wake-ups local **[src]**.
- A raising loader's exception is not shared; waiters retry one after another **[probe]**: four
  waiters ran a failing loader four times. Hence negative caching for deterministic failures
  (T1, T2) and the future-based single-flight where failures are transient or must be shared
  (T4).
- No waiter timeout and a same-key reentrant call deadlocks ([cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §B, probed).
  Loaders must not call their own key; T4's futures add timeouts.
- No generation fence: a clear during a load is followed by the load's insert **[probe]**.
  Hence identity keys plus clear-after-publish.
- No async support, no persistence, no dependency tracking, no idle expiry **[doc]**.
- Version change: 8.0 refuses `cached(cache=None)`, removes `cache_info` when `info=False`,
  forbids `cachedmethod` on `__slots__` classes and class methods, and makes the decorated
  wrapper a callable object **[doc, [cachetools report](../../evidence/2026-11-18_production-review-inputs/library-cachetools.md) §K]**. The project's only current use
  (`LRUCache` with `getsizeof`, `get`, `popitem`, `clear`, `__setitem__`) is unaffected. The bump
  changes the served-read identity once, because that identity includes the installed
  cachetools version (`serve/rich_queries.py:66–92`); outstanding cursors refuse once.
- Target 8.0.1, not 8.0.0 (copy and pickling fixes, clearer decorator-order error) **[doc]**.

## 10. Scenarios

| Scenario | Today | With this design |
|---|---|---|
| An identical read repeated from the CLI and from the MCP server | MCP hits only on continuation, `resource_handle` replay or pinned re-request; the CLI never hits (new process per page) | Continuation pages hit across CLI processes through D4 (sound now); MCP hits continuation in T4; fresh identical requests hit once the native owner certifies the `content` basis for a query |
| Two concurrent identical cold reads in the MCP server | Both derive | Both re-acquire authority; one derives, the other waits on the future and receives the same value or the same failure |
| A model YAML change published while caches are warm | `semantic/metadata.py` keeps the import-time model until restart | The next `current_model()` sees the stat change through custody, re-hashes, builds a new T1 entry; T2 keys move with it; T3 and T4 entries for old releases stay valid for reads pinned to them; event `model` frees memory |
| A generator module edited while the MCP server runs | The next port acquisition regenerates the capture, sees a different digest and refuses until a kernel revision is deployed | Code custody refuses on the next use of the edited generator (restart, as today for served code); execution paths do not regenerate and keep working against the installed kernel |
| A captured Python helper that shapes no program is edited (revision of 2026-11-18; observed at N29) | The digest moves; a native revision is authored and deployed although it changes only digest literals; receipts replay | No program's bytes change; T2 regenerates the same bytes; no identity moves |
| A library the generators import is bumped | Kernel digest, release id and every key built on them change | D2 key changes and the set regenerates; if no program's bytes change, kernel identity, validator identities and releases are unchanged |
| An interrupted run is resumed | Request identity reuse decides (sound) | Unchanged; disk tiers are write-once with atomic replace, so an interrupted write leaves only a temporary directory that prune removes |

## 11. Open premises for the cache design

- Whether derived rows are a function of frontier content for each served query (DA-075). It
  gates the `content` basis, not the rest of the design.
- How much time the per-command model compile, the program generation and a cold served page
  take. The design removes repeated work by structure; whether each removal is material is
  unmeasured, which is why D2 and the optional D1 are second steps.
- Footprints of CPU runtimes for T5 bounds, and the distinct macro-table count for T6 bounds.
- Whether any T4 query result is authority-independent (which would let its key drop the
  authorization scope). The default keeps the scope in the key.
