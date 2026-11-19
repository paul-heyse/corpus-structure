# The cache system: one owner module, six in-process tiers and two on-disk tiers

**Status:** UDM-13 complete for the bounded N34 increment. UDM-14 and UDM-15 have scoped implementation and explicit rendering and read projection boundaries. Entry-point reuse qualification remains open.
**Created:** 2026-11-19. **Amended:** 2026-11-19 from the code dependency closure review at `1982a20c3`. Production reuse qualification remains open.

This companion owns the designs of **UDM-13** (the cache owner module, cachetools 8.0.1 and the
six in-process tiers), **UDM-14** (the two on-disk tiers: generated program sets and continuation
pages) and **UDM-15** (served-result reuse across fresh requests, once its premise is settled).
It contributes to review recommendations R09 and R10, to review finding F02, to rule impacts RC09
and RC13, which the operator accepted on 2026-11-19, and to audit findings
[DA-075](../../design_review/audit/execution-fit.md#da-075) and
[DA-083](../../design_review/audit/execution-fit.md#da-083). Package state, the queue, finding
dispositions, the shared contracts and the decision records are the
[coordinator's](../unified-domain-model-and-execution_2026-11-19.md).

The [code dependency closure review](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md)
I02 and I03 supply the remaining D2 and D4 amendments below. I01's authenticated initialization
and callable contract is owned by [UDM-10's code-closure follow-up](programs-identity-and-revisions.md#udm-10-code-closure).
The retained N33/N34 observations establish the implemented baseline. The review's probe
establishes that a syntax scan can both include an uncalled dynamic site and miss an indirect
load, so that scan alone cannot authorize reuse for an arbitrary workload. Each adopted cache
consumer needs the determining code and captured-input contract its owner can establish.

**The design of record.** The cache system was designed in the review's supporting document, the
[cache design](../../design_review/reviews/unified-domain-model-and-execution/cache-design.md)
(recommendation R09 of the
[design review of 2026-11-18](../../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md)).
This companion does not redesign it. It turns the design into packages with exact migration scope
for each tier, and it resolves five matters that the design left open and that the
[cache and retirement map](../../design_review/evidence/2026-11-19_udm-plan-authoring/caches.md)
brought to light. Those five resolutions are design choices made in authoring; the coordinator
lists them under [design choices](../unified-domain-model-and-execution_2026-11-19.md#design-choices)
for the operator, who may revisit any of them when reading the plan. Section references such as
"design §4" mean the cache design.

**Baseline and evidence.** The plan was authored against commit `cb4e09667`, whose production
source is identical to the review's baseline `5139eaba3`. Source facts are **Interface-checked by
source inspection, 2026-11-19** at `cb4e09667`; they come from the cache and retirement map, and
the lines cited here were re-read for this draft. Library facts about cachetools 8.0.1 come from
the [cachetools report](../../design_review/evidence/2026-11-18_production-review-inputs/library-cachetools.md)
and are quoted from it with its labels (documented, read in upstream source, or probed on
2026-11-18); they were not re-observed here. Nothing was run. Every design statement is
**Proposed**. No speedup is claimed: where a tier removes work, the work is named and whether its
removal is material is left unmeasured. Paths omit `python/corpus-structure/src/corpus_structure/`
unless they begin with `docs/` or `tests/`.

The shared contract **cache tier** (one named class of held result with its key, bound,
invalidation, coordination of concurrent misses, release rule and statistics) is defined in the
coordinator's [shared contracts](../unified-domain-model-and-execution_2026-11-19.md#shared-contracts),
as are **compiled model**, **program declaration**, **program identity** and the other identity
layers, and **the flexibility frame**. This document uses those names.

Terms of the system used below (a release, a read cut, a read instance, a native revision, the
stage, canonical development) are in the coordinator's
[glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary). Three
terms are local: a **read** is one acquisition of read authority; the **frontier** is the
published state visible to a read, which its cut pins; and a **served result** is the bounded set
of rows derived for one query under one cut.

## Why this work exists

The package holds derived results in about two hundred places built four different ways, and it
has no holder at all for its most expensive derived artifact.

- There is one cachetools cache, 96 `functools` cache decorators (23 of them unbounded), 78
  `cached_property` sites and about a dozen hand-built holders.
- Nothing coordinates concurrent identical misses. Two tool calls that need the same cold result
  both derive it.
- Several holders in long-lived processes are unbounded: the grammar's parser families, a spaCy
  pipeline, a grammar resource.
- Every cache is local to one process, and each `ci` command and each page of a paged read is a
  new process, so the command line never reuses anything.
- The generated program set has no holder. It is rebuilt on the execution path and several times
  within one authoring command (DA-083).
- The physical model is compiled when a module is imported, in every importing process, and
  compiled again by other consumers.

The design's job is therefore less to add caches than to give each expensive derived artifact one
holder, keyed by the identity that the model and the program set declare; to make concurrent
misses coalesce; to bound everything that lives in a long-lived process; and to give the command
line a route across processes for the two kinds of work it repeats.

**What this companion consumes.** The held compiled model and its identity from UDM-01. The
program registry's product from UDM-09. From UDM-10
([programs, identity and revisions](programs-identity-and-revisions.md)): the code identity, which
its first slice delivers with no prerequisite and no revision; the program identity function,
which needs UDM-09 only; and, once the transition revision exists, the read-closure identity. UDM-08, which takes
generation off the execution path, so that no execution-path caller needs a program-set holder.
File custody and query custody ([ADR-0137](../../adr/0137-serving-code-and-model-custody.md)) and the
process-owned execution host ([ADR-0125](../../adr/0125-process-owned-execution-host.md)), which
are kept.

**What it produces.** One owner module that registers, sizes, lists and clears the process-wide
caches; the six in-process tiers on cachetools 8.0.1 with the holders they replace migrated; a
small on-disk store with two tiers; a typed key for served results with a declared reuse basis;
and, gated on its premise, reuse of served results across fresh requests.

**Where its responsibility ends.** The composer and the compiled model object are UDM-01's; this
companion supplies the tier that holds them. The generalization of query custody into derived code
custody, and every identity used as a key, are UDM-10's. The derivation of the scientific policy
recipe is UDM-18's. Wiring the unread analytics settings into DuckDB connections, which the cache
design mentions in its owner-module section, belongs to UDM-16 and is not done here; UDM-13 and
UDM-16 share only the file `settings.py`.

## What the investigation adds to the design of record

Where the cache and retirement map corrects the design or the review, its verified fact governs.

1. **No in-process event exists for a long-lived process to hear.** The design clears tiers on
   three events, published "after the new identity is visible". Release activation
   (`semantic/releases.py:569`), model-change apply (`schema/model_change.py:1106`), deployment
   (`schema/model_deployment.py:678`) and archive publication (`semantic/archive_native.py:72`) all
   run in the `ci` process that performs the command, and that process then exits. The long-lived
   MCP server runs none of them. No production code calls any `cache_clear()` today.
2. **Every worker pool uses spawn.** The four pools all request the spawn context
   (`semantic/cpu_execution.py:697`; `semantic/pdf_publication.py:662`; `ingest/pdf_worker.py:141`;
   `ingest/pdf_chandra.py:258`), so a child starts with empty caches and fresh locks.
3. **F02 is a bound-and-lock tidy, not an active race.** The math grammar refuses to run off the
   main thread (`methods/math/grammar.py:517–519`), and every reader of its four module-level
   holders that was traced sits under that guard. The review's "tool threads reach them" is
   therefore not observed in source. The holders are still unlocked, and the two parser families
   are unbounded (`:309–310`).
4. **In-process entries are pickle-encoded.** The served-result entry stores each row with
   `pickle`, and its docstring says why: the public JSON codec normalizes Decimal scale and float
   kinds and cannot be a lossless cache representation (`semantic/selected_query_cache.py:24–31`).
   The design's disk tier forbids pickle. The disk tier therefore needs a codec of its own.
5. **There are no cache settings.** `settings.py` has no cache section, and six fields of
   `AnalyticsSettings` are read nowhere (`settings.py:129–139`).

## Baseline at `cb4e09667`

The cache and retirement map lists every holder with its key, bound, callers and thread or
process context. The table below is the part the packages need.

| Tier | Holders today | Callers and context |
|---|---|---|
| Custody | File custody records under one lock (`semantic/file_custody.py:79, 96`); query custody's executed-module map (`_query_custody.py:134`) | 28 references in 16 files; any thread; a worker receives a receipt |
| Compiled model | Module globals compiled at import (`semantic/metadata.py:32–58`); six wire protocol caches (`semantic/data_operation_wire.py:47, 53, 262, 489, 525, 560`); four companion projection holders (`semantic/companion_projection.py:71, 547, 561, 620`); fifteen no-argument process singletons that read package files, in nine modules | About 64 importing files, 19 of them at module scope (re-counted at entry); every process |
| Program set | None. `native_protocol_sources()` has 9 call sites with no argument and `native_source_digest()` has 3 | Execution path and authoring |
| Releases and archives | `_prepare_release_cached`, 8 entries (`semantic/prepare.py:600`); the PDF boundary release, 16 (`semantic/pdf_contracts.py:55`); prepared lowering sources, 4 (`semantic/pdf_lowering.py:168`); the archive open cache, a weak map from engine object to a hand-built LRU of 8 under a lock (`semantic/archive_reader.py:34–40, 394–434`) | `prepare_release` is called from 14 files. The command line creates one engine per command, so the archive cache never hits across commands; the MCP server holds one engine per purpose |
| Served results | `SELECTED_QUERY_CACHE`: a cachetools `LRUCache` of 32 MiB with a hand entry cap of 128 under a lock; entries of at most 8 MiB and 4,096 rows (`semantic/selected_query_cache.py:17–20, 58–86`) | 12 `get` and `put` references in 6 files; MCP worker threads and the command line; no coordination of misses |
| CPU runtimes | The spaCy pipeline, unbounded (`ingest/sentences.py:58`); vocabularies and matchers (`semantic/constructions/retained_rules.py:32, 191, 257, 1216`); the Lark prototype, 64, and its grammar resource, unbounded (`semantic/constructions/forest.py:83, 36`); the compiled pack, 64, inside the native host subprocess (`methods/native_host_adapters.py:111`) | One to three callers each; long-lived processes |
| Memos | Two parser dictionaries, unbounded and unlocked (`methods/math/grammar.py:309–310`); the parse memo and the standalone contexts, hand-built ordered dictionaries of 8,192 entries, unlocked (`:966, 980`) | Main thread only, by the grammar's own guard |

MCP tools are synchronous functions that FastMCP runs on worker threads
(`intervene/mcp_observations.py:11`), which is why coordination of misses matters in that process.
Each page of a command-line read opens a new engine, snapshot and release
(`cli/selected_results.py:99–112`). Seven test files call `cache_clear()` or `cache_info()` on
holders this plan replaces, and `tests/conftest.py:103–111` clears the served-result cache for
each test.

## Target: the design of record in brief

The cache design's seven rules stand. A key is a declared identity and never a carrier object such
as a connection or an engine. In-process keys omit process constants, and disk keys include them
with a format version. Preparation reuse and result reuse are separate tiers. Invalidation is by
identity first. Drift in Python code refuses, and drift in model declarations rebuilds (RC09). One
owner module, no framework. What has no identity is not cached.

| Tier | Holds | Key | Bound | Coordination of misses |
|---|---|---|---|---|
| T0 Custody | File and code custody records; the premise check the other tiers rely on | Path and digest | Finite, one per file; unchanged | The existing lock |
| T1 Compiled model | One compiled model per model-sources identity, with lazily derived projections | Model-sources identity | Count, default 4 | Single-flight; deterministic compile errors held as values |
| T2 Program set | One generated program artifact and its exact provenance | Shared immutable generator input capture and authenticated determining code | Count, default 2 | As T1 |
| T3 Releases and archives | Prepared releases, opened archives, PDF boundary releases, prepared lowering sources | Release inputs, or database identity with release id and archive header digest | Retained artifact bytes | Single-flight |
| T4 Served results | Derived row entries; the shared rich graph index; change-impact comparisons | Query identity, implementation identity, authorization scope, reuse basis | Bytes and an entry count | A future per key that shares failures |
| T5 CPU runtimes | Loaded CPU pipelines, matchers, compiled packs | Artifact digest, configuration, runtime version | Declared footprint in bytes | Single-flight |
| T6 Memos | Grammar parsers and parse memos | Normalized call arguments | Count | Built in |
| D2 Program store | Rendered programs, prerequisites, identities, manifest and captured provenance | T2's generator input and code basis, with format and effective runtime versions | Byte budget, oldest pruned first | Single-winner installation |
| D4 Result pages | Encoded rows of a served result | Semantic served key with its supported cut or content basis, plus cache storage and codec versions | Byte budget, oldest pruned first | Single-winner installation |

T1 to T6 are in-process; D2 and D4 cross processes. The numbering of the disk tiers follows the
in-process tier each one extends. An on-disk compiled model (the design's optional D1) stays
unadopted. GPU residency, the execution host's verified bases and the CPU workers' hydrated
releases keep their own lifecycles under ADR-0125 and register with the owner module for listing
only.

## Resolutions of what the design left open

Each subsection below is a design choice made in authoring and recorded for the operator in the
coordinator. Each names the alternatives rejected and what would reopen it.

### How a long-lived process notices a changed generation or release

It notices on next use, because the value that names each generation is read from its authority
at the start of every request, and that value is in the key. No message is sent and none is
needed.

- **A changed model.** The accessor for the current model observes each file of the model closure
  through file custody, which costs one `stat` per file after the first hash and re-hashes only a
  file whose stat identity changed. A changed file gives a new model-sources identity and a new
  T1 entry beside the old one, without a restart. The observation is made once per request scope,
  meaning one MCP tool call or one `ci` command, and the model resolved there is used for the
  whole request. A request therefore never sees two models, and the per-access cost inside a
  request is a lookup. Outside any request scope, for example in a spawned worker, the model is
  resolved on first use and held.
- **A changed release.** Which release a read uses is a database fact that every request reads
  when it acquires its cut; the cut pins the release id. Keys built from the cut or the release id
  therefore move with the next request. An opened archive is keyed by database identity, release
  id and archive header digest, and the header is read again on each call as the premise check,
  as today.
- **A changed kernel.** Every acquisition reads the installed descriptor and compares it with the
  kernel the release records (UDM-08). Served-result keys carry the implementation identity, which
  includes the read programs' identity.
- **Changed Python code.** Custody refuses and names a restart, as today.

**Consequence for the design's events.** The design's three events (`model`, `release`, `kernel`)
existed only to return memory early, and its rule already said that correctness never depends on
them. Since no publisher runs in a process that outlives the publication, this plan builds **no
event publishers**. Memory is returned by the bounds: a least-recently-used cache evicts first
exactly the entries of a superseded generation, because nothing reads them again. Each registered
cache still declares which generation its keys carry, for the listing, and the owner module keeps
one grouped `clear`, whose callers are the test fixtures that today call `cache_clear()` on
individual holders.

Alternatives rejected: a PostgreSQL `LISTEN`/`NOTIFY` channel that the server subscribes to (a new
connection lifecycle and a second source of truth beside the identities); a generation marker file
under the cache root that each request stats (the same information the request already reads from
its authority); a timer that clears periodically (it cannot detect change and discards live
entries). What would reopen the choice: the listing from a long-running server showing a
byte-bounded tier holding large entries of a superseded generation for long periods while the
process is short of memory. The remedy then is one function in the owner module that clears a
generation's entries the first time a request presents a new token for it; it needs no publisher.

### Which holders stay on `functools`

The rule is the cachetools report's: a holder moves to cachetools when its value is large, when
its loader is expensive and requested concurrently, when it must be listed or cleared as a group,
or when an ordered dictionary is being maintained by hand. Everything else stays.

- **Stay as `functools.lru_cache` or `functools.cache`:** the cheap pure memos (enum and lookup
  tables, type adapters, regular expressions, distribution versions, command registration), for
  example `semantic/types.py:165`, `semantic/refusals.py:70`, `serve/rich_queries.py:66`,
  `cli/app.py:25, 51`; and the content-keyed, bounded parsers and compilers, for example
  `semantic/alias_policy.py:113`, `semantic/reference_positions.py:31`,
  `semantic/python_module_projection.py:110`, `semantic/data_operation_model.py:1206`,
  `semantic/execution_admission.py:270, 348, 378, 405`. The map spot-checked about 35 of roughly
  55 such memos; these paths are examples, and the complete rule is "every `functools` decorator
  not named in a migration list below".
- **Stay as `functools.cached_property`:** all 78 sites. They hold derived values on immutable
  per-object state and die with the object. The eleven on the earlier model's view go with that
  model (UDM-04).
- **Stay as they are, by name:** the grammar's three small pure memos
  (`methods/math/grammar.py:181, 227, 235`); the formal grammar's memos
  (`semantic/structural_parsing.py:57, 94, 104, 175`; `semantic/formal_evidence.py:295, 313, 350,
  374`); the per-instance report cache and validator (`semantic/pdf_record_reader.py:268, 587–625`;
  `semantic/pdf_payload_validation.py:32`), which have instance lifetime; the external-packet
  holder, which is already locked (`semantic/data_operation_external.py:148–150`); the CPU call
  descriptors, 64 entries per worker (`semantic/data_operation_cpu.py:189`); the installed policy
  memo (`methods/model_observation.py:36`); and the CPU encoder, which is bounded at one entry and
  keyed by artifact hashes (`methods/contextual_embeddings.py:356`).

A duplicate computation under a race is harmless for these: `functools.lru_cache` is thread-safe
in its structure and the functions are pure.

### Spawned workers start cold, and nothing is warmed

Because every pool uses spawn, a child imports modules afresh. No fork hook is needed; if a fork
context is ever introduced, the owner module must register a reset after fork, because a child
forked while a parent thread held a cache lock cannot acquire it (cachetools report, probed).

Nothing is warmed in an initializer. The reasoning is by case. A CPU worker already receives its
prepared release through a shared-memory capsule and holds it for its life
(`semantic/cpu_execution.py:150–226`); that is the designed warm path under ADR-0125 and it stays.
Pools are persistent, so a cold start is paid once per worker and not once per task. With T1 lazy,
a worker compiles a model only if its task touches one, and then once. PDF workers load their own
weights. A warm start for the compiled model would need the on-disk model tier, which is not
adopted. Whether to adopt it is settled before final source by the
[bounded observation of UDM-13](#the-bounded-observation-that-sets-the-defaults), and not by the
final runs.

A child does not inherit the parent's configured sizes. Where a pool already has an initializer
that receives settings, UDM-13 passes the cache section through it; elsewhere the section's
defaults apply, which is correct because sizes are tuning values and never correctness values.

### The codec for the on-disk result tier

In-process entries keep their pickle encoding. They are created and consumed inside one process,
which is the only condition under which pickle is acceptable, and the encoding preserves every
value kind a row can hold.

The disk tier uses a **typed canonical JSON lines** codec, owned by the serving module beside the
entry type. One line holds one row, written with the project's canonical JSON conventions (sorted
keys, exact decimal digits). The codec admits a closed set of value kinds: null, boolean, integer,
string, decimal, float, list, tuple, and mapping with string keys. The controlled entity read
exposed tuples in the actual typed response, so the store gives tuples their own reversible tag.
Decimal text preserves scale and signed zero. Float hexadecimal text preserves its exact value
and kind. Tags also distinguish user mappings and collections. A separate file holds the row offsets,
and the manifest names the codec version.

A result that contains any other value kind (bytes, a date, a set) is **not written to
disk**. It is still derived, served and held in process. This follows the rule the identity
companion applies to incomplete code identity: where reuse cannot be made exact, reuse is withheld
and service is not refused. Reading a disk entry yields the same row values as reading the
in-process entry, kind for kind; that equality is the codec's acceptance.

Alternatives rejected: pickle on disk (the stream format is not stable across releases, and a
pickled file is a code-execution trust boundary); the public JSON wire codec (lossy, by the
entry's own documentation); Arrow IPC (rows are heterogeneous nested mappings, not columns); a
third-party binary codec (a new dependency for one consumer). A later simplification that this
plan does not schedule is to adopt the typed codec for in-process entries as well, which would
make a disk entry a file copy of a memory entry; it becomes attractive if premise K1 shows that
every served row is within the closed set.

### Where sizes are declared

A new settings section, `CacheSettings`, joins the sections of `Settings` in `settings.py`, with
the environment prefix `CORPUS_CACHE__` under the existing convention. It is frozen and forbids
unknown fields, like every other section.

| Field | Default | Governs |
|---|---|---|
| `root` | `build/cache`, resolved from the working directory like the other path settings | The on-disk store |
| `model_entries` | 4 | T1 |
| `program_sets` | 2 | T2 |
| `release_bytes` | 256 MiB based on the bounded stage observation | T3 |
| `served_bytes`, `served_entries` | 32 MiB, 128 (today's constants) | T4 |
| `runtime_bytes` | 16 MiB based on the bounded CPU preparation | T5 |
| `parser_entries`, `parse_memo_entries` | 8 and 8,192 | T6 |
| `program_store_bytes`, `page_store_bytes` | 67 MiB and 1 MiB from the observed program artifact and controlled entity page. Zero disables the named tier | D2, D4 |
| `wait_seconds` | 1 second | The longest a T4 waiter waits for an in-flight derivation |

The per-entry limits of a served result (8 MiB, 4,096 rows) stay constants of the serving module.
They are part of a query's examined-input bound, not a tuning value: a cache populated under a
larger budget must not let a request bypass its own (`semantic/demand_queries.py:197–198`).

The cache root follows the project's existing convention of state under `build/`
(`settings.py:102–103`; the managed result store under `build/ci`) and not a user cache
directory, which the design proposed and for which the project has no convention. Disk keys carry
every determinant, so pointing two checkouts at one root by setting is sound.

Settings are built once at an entry point and passed down, and module-level caches are declared at
import, before any settings exist. The owner module therefore builds each cache on first use from
the configured section: the two entry points (the `ci` callback and the MCP lifespan) call
`configure` once, and a process that never does gets the defaults. Because a cachetools cache's
bound is fixed at construction, a later resize builds a new cache and swaps it under the lock.

<a id="the-bounded-observation-that-sets-the-defaults"></a>
**The bounded observation that sets the defaults.** Three defaults need a number that only an
observation gives. UDM-13 takes each from one bounded run on the stage, before final source, and
records the figures in an evidence record; each settles one decision.

- The retained artifact bytes of the releases prepared on the stage settle `release_bytes`, with
  the condition that today's behaviour of holding eight prepared releases is not reduced.
- The summed model-file sizes of the CPU runtimes loaded by a bounded stage demand settle
  `runtime_bytes`.
- The count of distinct macro tables seen in that demand, or in the bounded reproductions of
  UDM-20 where they exercise the math grammar, settles `parser_entries`, together with a parser's
  rebuild cost against its memory, which decides whether evicting one is acceptable.

The same run records the duration of one command's model compilation and of one worker start
against the bounded task they serve. That settles whether the on-disk model tier is adopted and
anything is warmed; the series default is that it is not, and an adoption would be added to
UDM-14's scope before final source. The two store budgets are set in UDM-14
in the same way, from the bytes of one stored program set and of one stored result.

The final runs observe and do not tune. UDM-22 and UDM-23 retain the `ci cache stats` listing as
an observation and are not a source of defaults. If either run shows that a default or a placement
must change, the change is made within the series and the affected evidence is gathered again.

### F02

The four grammar holders move to bounded, locked caches because unbounded and hand-maintained
holders in a long-lived process are a defect in themselves, and because the guard that keeps them
on the main thread is a property of today's callers, not of the holders. No race is being fixed
and no acceptance check claims one. The finding closes by inspection of the migrated holders.

## cachetools 8.0.1: the API each tier uses, and its limits

The facts in this section are quoted from the cachetools report and the cache design's probes;
their labels there are documented, read in source, or probed on 2026-11-18.

| Tier | API | The limit that shapes the use |
|---|---|---|
| T1, T2 | `LRUCache(maxsize=n)` wrapped by `cached(cache, key=…, condition=threading.Condition(threading.RLock()), info=True)` | With `condition`, a miss marks its key pending and computes outside the lock, so identical misses run the loader once. A raising loader does not share its exception: each waiter retries in turn. Deterministic compile and generation errors are therefore returned as values and re-raised by the accessor |
| T3, T5 | `LRUCache(maxsize=bytes, getsizeof=…)` with the same `cached(…, condition=…)` | The size is measured once at insert. A value larger than the bound raises `ValueError` inside the cache, which `cached` swallows; the value is returned uncached. cachetools cannot see process memory, so the loader declares the footprint |
| T4 | A subclass `SizedLRU(LRUCache)` whose `__setitem__` also evicts while the entry count exceeds its cap; explicit `get` and `put` under the tier lock; an in-flight map from key to `concurrent.futures.Future` | One cache has one capacity measure, so two bounds need a subclass. `CacheInfo` exists only on decorated wrappers, so T4 keeps its own counters. The future recipe is application code, not a cachetools feature |
| T6 | `cachetools.func.lru_cache(maxsize=…)` for the parse memo and standalone contexts; `cached(LRUCache(…), key=…, condition=…)` for the parser families | `cachetools.func.lru_cache` is `cached(…, condition=Condition(), info=True)`, so it is locked and single-flight; it takes no `getsizeof` |
| All keys | `cachetools.keys.hashkey` | In 8.0 a key is a plain tuple, and a positional and a keyword call give different keys, so identities are passed positionally. A key function has the same signature as the wrapped function and ignores non-determinants |

Limits that hold for every decorated tier:

- A lock alone protects the mapping and not the computation, hence `condition` wherever a loader
  is expensive.
- Gating is per key but every completion wakes every waiter on the condition, hence one condition
  per wrapper.
- A waiter has no timeout, and a loader that calls its own key deadlocks. Loaders must not
  re-enter their own key. T4's futures add the timeout that `wait_seconds` sets.
- There is no generation fence: a clear during a load is followed by the load's insert. This is
  why keys carry identity and why nothing depends on a clear.
- `clear()` bypasses `__delitem__`. No tier in this plan holds a handle that needs closing, so no
  removal hook is written; a runtime with handles would need hooks on both.
- There is no persistence, no cross-process sharing, no asynchronous support and no idle expiry.
  The first two are why the disk tiers are a separate module; the last is why GPU residency keeps
  its own lifecycle.
- Version changes from 7.2.7: `cached(cache=None)` is refused; the `cache_info` attribute is
  absent unless `info=True`; `cachedmethod` refuses classes with `__slots__` and class methods; a
  decorated function is a callable object. The project's one current use is unaffected. The
  target is 8.0.1 and not 8.0.0, for its copy and pickling fixes.

References: the [cachetools report](../../design_review/evidence/2026-11-18_production-review-inputs/library-cachetools.md)
(sections A, B, C and J, and its table of version differences), and the
[cachetools documentation](https://cachetools.readthedocs.io/en/stable/) for 8.0.1.

For the pinned 8.0.1 behavior use the [storage implementation](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/__init__.py)
and [wrapper implementation](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/_decorator.py).
The [local capability overview](../../libraries/analytical_infrastructure/cachetools.md) describes
8.0.0 as well; its examples are orientation. Use immutable or exclusively owned values with known
retained weights; external allocations are declared estimates, not process RSS. The standard
library [`Future`](https://docs.python.org/3.14/library/concurrent.futures.html#future-objects)
supplies T4's shared failure and result. Neither eviction nor a waiter timeout retires an owner.

For the code-closure amendment, retain `cached(..., condition=Condition(RLock()), info=True)`
over `LRUCache` for T2. T4 retains `SizedLRU` with its explicit lock, pending futures and timeout.
Their keys consume the authoritative captured basis and eligibility. Cachetools 8.0.1 supplies
expendable process retention, with application-owned coordination where T4 needs it.
D2/D4 persistence remains with the existing disk-store owner. Its version belongs to entry
compatibility when storage behavior alone changes. Derivation semantics, imported code custody
and native authorization remain inputs supplied by their owners. The pivotal source-analysis
APIs and their pinned versions are owned by [UDM-10](programs-identity-and-revisions.md#udm-10-code-closure),
so this package consumes that captured analysis without introducing another parser or resolver.


## What this supersedes

| Passage | What it says | What replaces it |
|---|---|---|
| `docs/plans/declared-data-operations/interfaces-and-evaluation.md:390–400` (PE-S42), and the coordinator row for PE-F17 at `docs/plans/declared-data-operations_2026-11-12.md:1604` | Continuation pages come from a small per-process cache keyed by cut identity, implementation identity and root reference | The process cache becomes tier T4 with a typed key and a declared reuse basis, and continuation pages also cross processes through D4 (RC13). The rule that the cache holds derived content only and never an authenticated cut or authority result is kept |
| `docs/plans/declared-data-operations/postgresql-realization-and-retirement.md:336–338`, and the row for PE-F16 at `docs/plans/declared-data-operations_2026-11-12.md:1603` | "The archived-release cache stays keyed on the engine, because engine lifetime bounds database authority" | The archive entry is keyed by database identity, release id and archive header digest. Authority is not carried by the entry: every caller still acquires it, and the header is read again as the premise check |
| [ADR-0124](../../adr/0124-serving-code-custody.md), Decision | Drift refuses and requires a restart | Kept for Python code. For model declarations, a changed source yields a new compiled model (RC09). UDM-00 writes a superseding record that carries the decision forward |

The design's event publishers are not a superseded passage of any plan; they are the one element
of the design of record that this plan does not build, for the reason given above, and the
coordinator records that as a design choice. ADR-0125 is unchanged. The DDO plan is not edited by this series; UDM-24 records the superseded items.

## Packages

### UDM-13 — The owner module, cachetools 8.0.1 and the six in-process tiers

**Implemented against N34 · 2026-11-19.** A budget owns its holders and clearing it releases
completed entries. Archived releases use the acquired database identity, protected header and
boundary runtime. A private PostgreSQL activation control reused an immutable archive while
observing the new release and generation on the next reader snapshot
(`5026c6e769704cf5a7b74244179423b5`). Serving uses only typed keys after acquiring native
authority. The real serving scans still report the same 33 diagnostic sites at four roots, matching the
N33 baseline. The code-closure follow-up accounts for their root-specific effect and verified
dynamic contracts before changing production eligibility. Reads under that standing return a fresh page with no reuse handles. The complete-code
control exercises authorized retained rows, continuation ordering and concurrent requests.

The stage archive working set and CPU preparation determined the three retention defaults. The
separate CLI, spawned worker and MCP observations supported retaining lazy compilation. The disk
model tier and warming remain unadopted. [Bounded observations](../../design_review/evidence/2026-11-19_udm13-cache-bounds/README.md)

**Tested · 2026-11-19.** The final `ci test` selection passed all 209 model, archive, CLI,
PDF, runtime and serving checks (`be2952456037438093905160b12094d6`). The witnessed source-link
regression passed all six selected cases (`bce82089ce024e3e9f62881dcbfccb73`). Offline
`ci schema native-candidate` compared 617 installed objects and reported `no_native_change`
(`3d5afd411ee4496f8a0b1be1c4ed08f2`). The stage project readback still matched generation 31 after
cache qualification. UDM-22 and UDM-23 own the integrated provider and book qualification.

**Implementation vision.** A plain module, `corpus_structure/caches.py`, owns the process-wide
caches. It offers `configure` (take the settings section once), `declare` (build, on first use, a
cache sized from settings with its own condition, and return the `cached` wrapper), `register`
(for the explicitly used T4 cache and for the lifecycle owners that are listed only), `snapshot`
(name, tier, generation, length, current size, bound, hits and misses) and one grouped `clear`.
It offers no other decorator, no metrics backend and no persistence. The listing is exposed
through `ci cache stats` and through one MCP diagnostic tool for the long-lived server. The
package also makes [the bounded observation that sets the defaults](#the-bounded-observation-that-sets-the-defaults).

**Attributable maintenance (I04).** Associate each process snapshot with its process/owner,
generation and observation lifetime. A fresh CLI call can observe its own counters and disk tiers;
the long-lived MCP or worker owner's snapshot establishes that process's counters. Expose a retained
snapshot through managed evidence where the invocation already records it. Hits, misses,
admission skips and evictions are present only when attributed by that tier. Show bytes and the
tier affected by prune. Keep held evidence and UDM-25's acknowledged handoffs under their own
custody. Run a cold CLI command, spawned worker and long-lived MCP journey to check attribution.

The tiers are then migrated one at a time. Each migration replaces named holders, keeps each
holder's callers unchanged where the holder was a function, and moves the tests that reached into
the old holder. The decisions the package owns are each tier's key function and the footprint a
loader declares. Failure behaviour is the tier table's: a deterministic build error is a held
value in T1 and T2; a transient failure is never cached; a T4 waiter receives the owner's value
or the owner's exception, or times out and derives for itself.

**The cachetools move.** The pin at `python/corpus-structure/pyproject.toml:65` moves from 7.2.7
to 8.0.1, with the lockfile entry for that one distribution. The single import
(`semantic/selected_query_cache.py:12`) remains usable. Today `serve/rich_queries.py:71–100` hashes
the cachetools version into the served-read basis. Move that storage determinant to the cache
entry with UDM-10's semantic continuation basis. If the old opaque format cannot be interpreted,
report the one-time transition refusal. Check a later storage-only version change with a valid
continuation and unchanged ordered rows, including a fresh derivation on a cache miss. Keep the
native read check. The commit names the pin move. No hold is recorded in `docs/pins.md`.

**Exact migration scope, by tier.** These lists are complete at the baseline; UDM-00's re-read
confirms them at the entry commit.

- *T0.* The two custody holders register for listing and no holder migrates; replacing the hand
  lists with a derived closure is UDM-10's. One consumer is added: companion file verification
  (`serve/companion_export.py:319, 403`), which today verifies each path once per inventory and
  twice per comparison, carries its verified status per file identity in the custody tier (row X2
  of the review's DuckDB judgment table, §5).
- *T1 (after UDM-01).* The tier replaces the single module-level reference in which UDM-01 holds
  the running model, without touching consumers, and adds the per-request observation described
  above. The caches that become projections of the compiled model are: the six wire protocol
  caches of `semantic/data_operation_wire.py`, so that the whole captured-artifact tuple leaves
  every key; the scientific recipe holders (`semantic/scientific_evidence.py:58, 66, 133, 333`),
  for which UDM-18's derivation of the recipe is a prerequisite of that part alone; the semantic
  graph built from the model's records (for example `semantic/data_operation_model.py:967`; its
  builders are listed at entry), held with the compiled model (row G4 of the same table); and
  those of the fifteen no-argument singletons that read model
  declaration files (`semantic/pdf_contracts.py:81`; `semantic/pdf_lowering.py:107, 259`;
  `semantic/operation_reporting.py:63, 93, 118`; `semantic/pdf_records.py:33, 159, 165, 198`;
  `semantic/pdf_staging.py:118`; `serve/selected_source.py:39`;
  `semantic/declared_math_analysis.py:68`; `semantic/data_operation_model.py:1219`;
  `semantic/data_operation_admission.py:99`). The cache design names the first ten; the last five
  have the same shape by the map and each is confirmed by one test when it is migrated: a holder
  that reads a declaration file becomes a projection, and one that does not stays on `functools`.
  The metadata module globals and the companion projection holders are UDM-01's scope.
- *T2 (after UDM-09).* A new holder for the registry's generated program set, used only by
  authoring: preparation (`semantic/data_operation_preparation.py:261`), primary operations
  (`semantic/primary_operations.py:403`), regeneration (`semantic/regeneration.py:331`), native
  products (`semantic/native_products.py:110`), candidate definitions
  (`semantic/data_operation_storage.py:1857, 1865`) and the model-change preview
  (`schema/model_change.py:525–552, 603`). The five `if sources is None` fallbacks inside
  `semantic/data_operation_storage.py` (`:707, 713, 764, 883, 1018`) read the holder. The
  execution path does not use T2; UDM-08 removed its callers.
- *T3.* `_prepare_release_cached` (`semantic/prepare.py:600`), `_boundary`
  (`semantic/pdf_contracts.py:55`) and `_prepared_lowering_sources` (`semantic/pdf_lowering.py:168`)
  move to one bytes-bounded tier whose builder records the summed artifact bytes of what it
  retains. `_OPEN_CACHE` (`semantic/archive_reader.py:34–40, 394–434`) is replaced by a tier entry
  keyed by database identity (the cluster's system identifier with the database name, read once
  per engine), release id and archive header digest; the engine object leaves the key.
- *T4.* `SelectedQueryCache` becomes the `SizedLRU` with the future-based single-flight and its
  own counters. All six key builders move to one typed served key: `semantic/demand_queries.py:198–212`,
  `serve/rich_queries.py:224`, and the builders in `serve/identity_exclusion_comparison.py`,
  `serve/contribution_facets.py`, `serve/interpretations.py` and `serve/structural_products.py`
  (12 `get` and `put` references in the six files). The key gains the authorization scope, which no key carries today,
  and the reuse basis. Queries default to `cut`. The N34 correction keeps exclusion comparison
  on two exact cuts. UDM-15 qualifies the scoped direct entity content witness. Other variants
  retain their declared cut while their broader content premise remains open. Two derived structures that are rebuilt today become entries: the rich graph index, shared
  by every query on one selected product (`serve/rich_queries.py:222–262`), and the change-impact
  comparison, rebuilt for every page (`semantic/change_impact.py:506–510, 687–777`). Every caller
  still acquires native authority before it looks anything up; only the derivation is coalesced.
- *T5.* The spaCy pipeline (`ingest/sentences.py:58`), the four vocabulary and matcher holders of
  `semantic/constructions/retained_rules.py`, the Lark prototype and its grammar resource
  (`semantic/constructions/forest.py:83, 36`) and the compiled pack
  (`methods/native_host_adapters.py:111`) move to a tier bounded by declared footprint. The
  compiled pack lives in the native host subprocess, so its tier instance and its statistics are
  that process's; the parent's listing does not include it.
- *T6.* The four grammar holders (`methods/math/grammar.py:309–310, 966, 980`) and nothing else.

**Tests that follow.** The seven test files that call `cache_clear()` or `cache_info()` on a
replaced holder (`tests/semantic/test_data_operation_wire.py`, `test_operation_reporting.py`,
`test_prepare.py`, `test_data_operation_ports.py`, `test_definition_cpu_authority.py`,
`test_construction_grammar_custody.py`, and the fixture in `tests/conftest.py:103–111`) move to
the owner module's grouped clear or to the wrapper's own `cache_clear`, which 8.0 keeps. A test
that asserts hit and miss counts needs `info=True`, which `declare` always passes.

**Removes.** The hand-built LRUs (`_OPEN_CACHE`, the two grammar ordered dictionaries, the entry
cap loop in `SelectedQueryCache.put`), the unbounded holders named above, and the per-engine
weak map.

**Prerequisites.** The owner module, the pin move and tiers T3, T4, T5 and T6 need nothing and
can start at once. T1 needs UDM-01's compiled model object and its identity, and its scientific
recipe projection also needs UDM-18. T2 needs UDM-09's registry product. The bounded observation
needs the stage. The served key carries the implementation identity from
`installed_read_implementation`. Eligible T4 and D4 production reuse also requires UDM-10's
complete authenticated determining-code contract. A typed key alone supplies no such evidence.
The owner can retain process entries and derive fresh pages while that prerequisite is open.

**Native revision.** None. Nothing installed changes.

**What this keeps open.** A new or exploratory served query needs no cache declaration: it gets
the `cut` basis and a key that includes the authorization scope, which are the safe defaults. A
model edit beside a running server produces a new compiled model on the next request without a
restart, so trying a declaration is cheap. Anything without an identity is simply not cached. The
package closes nothing in the declared behaviour space; the only closed set it introduces is the
list of tiers, which is internal structure.

**Acceptance evidence.**

- *Coalescing.* Several threads request one cold key of a T1-style declared cache whose loader
  counts its calls and blocks on an event: the count is one. The same for T4, with the loader
  raising: every waiter receives that exception and the count is one. The expectations are the
  counts the test states.
- *Failure handling.* A deterministic build error requested twice is built once; a transient
  failure in T4 is not held, so the next request derives again.
- *Noticing on next use.* In one process, a model source file is rewritten with different bytes
  between two request scopes: the second scope resolves a different model identity, and an object
  pinned to the first identity is still served from its entry. Rewriting with identical bytes
  changes nothing. Inside one request scope, a rewrite is not observed.
- *Keys.* Two requests that differ only in their engine or connection object share an archive
  entry. Two requests that differ only in authorization scope do not share a served entry. A
  served query with no declared basis is keyed by its cut.
- *Bounds.* An entry larger than a byte bound is returned and not held. Filling T4 past its entry
  cap evicts by count while under its byte bound. After the migration, no module-level mutable
  dictionary remains in `methods/math/grammar.py`, by inspection (F02).
- *The pin move.* A cache storage version change preserves the semantic implementation identity
  and ordered continuation rows. An incomplete producing identity continues to permit a fresh
  page and withholds continuation and cached results where that standing applies.
- *Defaults.* Each of the three observed defaults is traceable to a figure in the evidence record
  of the bounded observation, and the record states the decision taken on the on-disk model tier.

### UDM-14 — The two on-disk tiers

**Boundary implementation · 2026-11-19.** Native authoring acquires one generator input value
before reaching the holder. Rendering compiles from that value and uses its captured model to
resolve integrity roles and its Docling schema for PDF lowering. Served queries declare shared
semantic pagination and family projections. The rich route prepares validation and projection
state from acquired body and reference bytes. Shared contribution readers seal their existing
request-local support index after acquisition. PostgreSQL JSONB binding is owned by the storage
adapter. The strict D2 journey recorded one fresh render in each process, with zero hydrations.
The next reuse work is the remaining determining initialization and library contracts, plus the
family-specific cursor and diagnostic callbacks retained by the serving entry points.

**Custody implementation · 2026-11-19.** T2 and D2 now consume the same immutable generator
capture, including model bytes, runtime and exact copied artifact sources. The old package-wide
T2 source fallback and independent D2 key sweep are removed. Installed readers pass explicit
callable roots. Served-row retention requires an active complete implementation matching the
key. Actual D2/D4 reuse remains withheld while the determining initializer and import contracts
are incomplete. [Workload and offline comparison evidence](../../design_review/evidence/2026-11-19_udm-workload-custody/README.md)

**Implemented against N34 · 2026-11-19.** The shared store publishes verified immutable entries,
tracks active writers with a scoped lease, and prunes its own namespace under lock. `ci cache
stats` includes disk occupancy and `ci cache prune` reports disk removals. D2 rehydrates a typed
program artifact on a T2 miss, while the authoring owner retains the captured model and predecessor
checks. D4 reads and writes bounded served rows in the two CLI routes after native authorization.
The exact Decimal payload uses canonical text inside a typed tag to preserve signed integral zero.
The graph preparation remains process-local.

**Qualification boundary.** The four actual entry scans share the same 33 diagnostic sites.
Their module populations overreach into unrelated function bodies, while the retained probe also
shows an indirect load omitted by syntax discovery. The shared code-closure follow-up must
establish the actual determining initialization, calls and verified dynamic boundaries for each
workload. The shipped eligibility checks continue to withhold reuse under their incomplete basis. Controlled complete-identity tests
exercise the disk hit path. The bounded stage remains on generation 31. The private entity
journey was blocked at PDF fixture execution and did not reach the cache. [Execution evidence](../../design_review/evidence/2026-11-19_udm14-15-disk-cache/README.md)

**Scoped Tested · 2026-11-19.** The final focused selection passed all 80 cases
(`256e2b81c133422997936660628e365e`). Separate-process store hits, codec and ordinal behavior,
controlled complete-identity authoring and serving, and cache-owner fault controls passed.
Actual entry-point qualification remains pending.

**Implementation vision.** A small module, `corpus_structure/cache_store.py`, owns a
content-addressed store under the cache root. An entry is a directory
`<root>/<tier>/<format version>/<key digest>/` that holds a JSON manifest listing each content
file with its digest, and the content files. The store reuses the managed result store's
conventions (`cli/managed.py:178–190, 490–506`): the root is created with mode 0700 and refused
if it is not owned by the caller or is writable by group or others. Create a private exclusive
temporary directory under the tier and finish its files and manifest there. Under the tier lock,
inspect the final key. If absent, install by atomic rename within that directory; if present,
verify the immutable winner and drop the temporary directory. A checksum mismatch or different
content at the purported same key is a diagnostic and an unusable entry. Recover under the tier
lock or derive through the authoritative route. Use owned directory descriptors and avoid following
symlinks. Read and verify under the shared tier lock; install, corruption cleanup and pruning use
the exclusive lock. Prune only settled cache entries and abandoned temporary entries whose writer
ownership has been resolved. Each tier has a byte budget and `ci cache prune` reports its own
removals, never managed evidence or production work. `ci cache stats` reports those disk tiers
beside the process listing. This single-winner protocol avoids replacing a nonempty directory,
which Python refuses. [Python `os.replace`](https://docs.python.org/3.14/library/os.html#os.replace)
and [`fcntl.flock`](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock).

<a id="udm-14-generator-capture"></a>

*D2, the program store.* The authoring owner captures immutable generator inputs before computing
one basis used by both T2 and D2. The capture includes physical source bytes and LinkML types,
the effective compiled-model projections consumed by `running_model()`, logical sources,
action and PDF overrides, extra sources, named package resources such as
`operation-vocabularies.yaml`, and runtime/distribution identities used by PDF/schema preparation
and SQL rendering. `include_producer=False` still performs PDF lowering and Arrow schema
preparation. Explicit physical overrides coexist with the running model in today's builder.
Record each effective input or remove its ambient acquisition from the renderer before admitting
the basis. Inspect environment, locale, clock, working-directory and filesystem reads along this
bounded workload. A required input outside capture keeps D2 ineligible. The exact input capture
and authenticated generator initialization/callable identity compose the semantic key, with
D2's artifact format identity added for disk compatibility. [Review I02](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I02)

The stored `ProgramSetArtifact` includes rendered programs and prerequisites, their manifest,
physical identity and exact authoring/native/PDF source artifacts. Python modules copied by
`_capture_native_authoring_inputs` and `_native_protocol_sources` are determining artifact bytes
even where their functions never execute during generation. Capture those bytes before keying
and pass the same immutable capture into rendering. An edit outside SQL rendering may therefore
move the full artifact identity because it changes recorded provenance. An edit outside both
execution determinants and copied provenance should preserve reuse. Keep normalized executable
meaning distinct from exact bytes recorded in the artifact. Splitting rendered output and
provenance into separately retained products is conditional on recurring source changes making
that distinction useful enough to warrant a replay-format change.

T2 consults D2 on a miss and writes a validated artifact after a build. Preview, candidate and
deployment preparation consume that same capture. Hydration verifies physical-model identity,
manifest/program agreement and retained source correspondence. Preserve ordinary predecessor,
SQL verification, authorization and authoring checks after hydration. Loaded bytes require the
shared source-custody guarantee as well as a closed determining identity. A complete module
population alone establishes neither. [Shared code contract](programs-identity-and-revisions.md#udm-10-code-closure)

If a finite generator capture with enforced code, initialization, resources and ambient-input
limits can be established before the narrower callable projection, the authoring owner may use
that broader bounded capture for D2. Document its wider invalidation and exact supported boundary
at G1 before enabling it. A new completeness flag on the current scan cannot establish this
contract. A restricted worker is a conditional response to a material acquisition boundary that
cannot be enforced in-process. Creating a worker by itself supplies no closed input contract.
The default is typed acquisition followed by identified in-process rendering.

*D4, continuation pages.* The key extends the supported semantic served key with cache storage
and codec versions. Native acquisition supplies typed authorization, cut, selection and support
references before any lookup. Complete authenticated code identity covers row derivation and
its query/profile contract, cursor interpretation, ordering, diagnostics, limits and examined
inputs. The production route must establish that context explicitly, including when lower-level
`reusable_serving_code` callers otherwise allow an absent context. A retained entry contains
bounded derived rows and no acquired native authority. [Review I03](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I03)

On a hit, consume the bounded entry at the cursor ordinal after reacquiring current authority.
On a miss, acquire and confirm the native body under the selected cut and support reference,
then pass the typed immutable body into derivation. Preserve diagnostic population, whole-support
requirements and encoded-width bounds when extracting that derivation boundary. Reuse therefore
avoids reloading whole support and rebuilding the graph only where the selected contract allows
it. A revocation between pages refuses before the disk entry is consulted. A required field that
the selected cut or supported content witness does not determine keeps that query ineligible.

Demand, contribution and other rich profiles retain their exact cuts. Exclusion comparisons
retain two cuts. UDM-15's direct entity witness can supply a content basis after its own premise
is established. Keep semantic continuation identity separate from storage/codec/cachetools
compatibility. A storage-only change may discard an entry and derive again under a valid cursor.
A changed semantic interpretation produces an explicit incompatible-continuation refusal.

The two CLI entry points opt into D4. MCP routes share the derivation and authenticated code
contract while retaining their existing T4 process lifetime. Move affected CLI/MCP consumers
and their error/reporting paths together. The files are private to the operating-system user
that runs the agents. Budget settings continue to use the retained bounded program/page
observations. This amendment introduces no new retention tier or warming policy.

**Complete consumer scope.** For D2: the T2 holder alone. For D4: the two command-line entry
points that page served results with a cut-bearing cursor, `ci query NAME` and the contributions
command (`cli/selected_results.py:25–135` and its second command near `:350–413`), through the six
served key builders of UDM-13. The other paged commands (`cli/demands.py`, `cli/status.py`,
`cli/orchestrate.py`, `cli/visual_route.py`, `cli/source.py`) pass a native continuation and are
not served-result pages; they are outside D4.

**Removes.** After consumer migration, retire the package-wide T2 source fallback and the
separate exact-module D2 sweep in favor of the shared input/custody basis. Remove duplicate
page eligibility and digest paths replaced by the shared serving contract. Keep the ordinary
derivation path for misses, unavailable storage and unknown determining inputs.

**Prerequisites.** UDM-13 supplies the T2 holder, the typed served key and the settings section.
D2 needs the shared generator capture and [UDM-10 code closure](programs-identity-and-revisions.md#udm-10-code-closure),
plus UDM-09's typed program identities. D4 needs the authenticated serving closure from that
same follow-up and its typed native acquisition/derivation contract. D2 and D4 can proceed
independently once their own contracts are closed. UDM-15 additionally needs a query-specific
content witness and actual native fixture qualification.

**Native revision.** None expected for input capture, Python derivation and custody. Compare
the N34 candidate through the existing offline route. If required native program bytes change,
route that change through the coordinator's revision decision before claiming qualification.

**What this keeps open.** Reuse on disk is always optional: an incomplete code identity, a row
outside the codec's closed set, an unreadable entry or a missing cache root each lead to the
ordinary derivation and never to a refusal. The store closes the codec's set of value kinds, which
is internal consistency of a file format and constrains no knowledge content, because a result
outside it is still served.

**Acceptance evidence.**

- *The codec.* For a table of values written by hand in the test, including decimals that differ
  only in scale, an integer, a float and a decimal of equal value, negative zero, and nested
  mappings, decoding the encoding gives a value equal in kind and in content. A row holding a
  bytes value is reported as not storable and nothing is written. Rich tuples round-trip in kind.
- *A continuation across processes.* Two installed `ci query` invocations in fresh processes
  serve page one and page two using actual code custody. Include demand and rich entry paths
  and the contributions command's shared consumer. The second performs no whole-result support
  read on a hit. Its ordered rows, ordinal and limits agree with independently expected values
  and the uncached page. Changed selection, support, runtime or implementation rejects stale
  reuse. A storage-only codec change can miss while a compatible cursor still succeeds.
- *Authority first.* With a stored entry present, a revocation between the pages makes the second
  page refuse; the entry is not consulted.
- *Tampering.* A content file altered on disk is detected by its digest, the entry is deleted and
  the page is derived.
- *The program store.* Two fresh `ci schema native-candidate` processes with an isolated cache
  root, unreachable database endpoints and actual identity discovery render once between them.
  The second rehydrates equivalent validated artifacts and manifests without rendering. Verify
  rendering-code, effective-model, named-resource, runtime and copied-provenance changes
  separately. Each material change moves its basis. A demonstrated unrelated edit preserves it.
  Retain wrong-model, manifest-disagreement and predecessor controls. Compare N34 installed
  bytes through the existing offline `no_native_change` route.
- *Permissions.* A cache root writable by group is refused.
- *Concurrent publication and prune.* Two fresh writers to the same key leave one complete
  verified entry. A reader racing prune reads complete verified content or derives; no operation
  observes a partial entry. An interrupted writer cannot install an incomplete entry. A mismatching
  winner is reported. Pruning leaves managed receipts and recoverable work intact.

### UDM-15 — Served-result reuse across fresh requests

**N34 disposition · 2026-11-19.** Exclusion comparison uses two exact cuts. Its derived report
consumes whole-support rows and an examined-record count, while the existing frontier stamp only
names the frontier. The direct entity query over one immutable rich admission can use a scoped
content witness from the newly authorized frontier. The witness retains the whole native
projection, including trust, runtime, release, and disclosure-bearing fields. It replaces only
the three receipt strings with their encoded lengths, including their copies in the continuation,
to preserve the native body-envelope bound. The body is fixed by product identity and rechecked
for disclosure before either cache lookup. Each response carries its own native pins. Other
variants retain the cut basis while their dependencies remain open.

Native demand row pages derive under a particular acquired native frontier and continuation.
Contribution, interpretation, and structural pages consume whole-support projections. The
exclusion comparison consumes two of those closures. A frontier stamp establishes neither the
whole support bytes nor their disclosed population. Keep those paths keyed on their exact cuts.
The additional rich query variants retain their current basis pending a query-specific analysis of
the derived diagnostics and population semantics. The private authored fixture published and read
an entity successfully. T14 awaits real code identity and cross-process reuse qualification.

#### The premise that gates UDM-15

DA-075 observes that five of the six served-result keys include the read instance, a random
identifier created at each acquisition, so two identical fresh requests never share an entry. A
key built from content would let them. Whether that is sound is the premise, stated exactly:

> For a served query with a normalized selection, the derived rows depend on the read instance
> only through the frontier content stamp, the release, the runtime, the implementation identity
> and the authorization scope. They do not depend on `read_id`, `read_snapshot`, `frontier_at`,
> `owner_xid`, `access_universes`, `public_disclosure` or the census flags of the read row,
> except as those are functions of the content stamp.

**What settles it.** The native owner shows, for the closure of each read-page program, which
fields of the read row it reads, and that each such field is either in the content key or
determined by it. The registry's record of the model inputs each program reads (UDM-09) supplies
the enumeration. `public_disclosure` and `access_universes` are shaped by authorization, so for
most queries they must enter the key together with the authorization scope. The premise is
settled per query. The N34 analysis found that exclusion comparison needs two exact cuts,
including whole-support rows and examined counts. The direct entity request is the scoped
content candidate described above.

**What is delivered without it.** UDM-13 delivers the declared reuse basis with `cut` as the
default, and UDM-14 supplies the store and continuation machinery keyed by a supported read
cut. Their real reuse still requires complete authenticated code identity. Adopting the content
basis adds the query-specific premise to that shared requirement.

**Implementation vision, once the premise holds for a query.** That query declares the `content`
basis. Its served key replaces the cut identity by the frontier content stamp, the release and the
runtime; the rest of the key is unchanged. Two fresh identical requests then share a T4 entry, and
the disk tier accepts the content basis for that query so that separate command invocations share
it as well. Authority is still acquired per request before any lookup.

**Complete consumer scope.** Qualify the scoped direct entity query through the installed
selected-result CLI and its shared retained-reader derivation. Demand, contribution, exclusion
and other rich queries retain their stated cut basis. A further content variant joins scope
only after the native owner supplies its complete query-specific argument and the coordinator
records that adoption.

**Prerequisites.** UDM-13 supplies the declared basis, and UDM-10's code-closure follow-up
supplies complete authenticated derivation identity. The native owner settles the content
premise for the query. Qualify the authored entity fixture before using it to close T14.

**Native revision.** None expected for the existing scoped entity witness. If settling a further
premise requires changing a native read program, record it through the coordinator's current
revision route before enabling that variant. Keep qualification scoped to the native head that
actually supplied its read and disclosure contracts.

**What this keeps open.** The basis is declared per query and defaults to the safe one, so a query
whose dependence on the read instance is unknown stays correct without any decision being forced.
An undetermined premise withholds only the wider reuse.

**Acceptance evidence.** For the adopted direct entity request, two fresh native acquisitions
of one immutable admission share one derived entry while returning distinct current native pins.
Use actual code identity and independently expected entity rows. Changing the content witness,
release, runtime, authorization scope or disclosure premise prevents stale reuse. Refusal of a
revoked or wrongly scoped request occurs before entry lookup and leaves the hit counter
unchanged. Author the determinant expectations independently of the key function.

First assess the existing authored-publication fixture in
`tests/semantic/record_publication_native_support.py` against private N34. It creates typed entity
and proposition packets and commits through native publication. Extend the selected-reader
pagination journey in `test_record_publication_native.py` with an entity request, retain its
published root across two fresh processes, and verify one derivation and fresh per-request
pins through the installed CLI. This is a source-inspected feasibility lead. Prove its fixture
viability before using it for acceptance. Its outcome and any missing prerequisite remain
explicit. The separate upstream PDF fixture failure stays with its existing owner and is not a
prerequisite for this authored entity case. T14 and the applicable D2/D4 acceptance controls
join [UDM-22's final-source union](qualification.md#udm-22--the-managed-union-on-final-source).

## Open premises

| Premise | What settles it | Work it constrains |
|---|---|---|
| D1. A content-based served-result key is sound for a query (DA-075) | The native owner's per-program argument, stated above | UDM-15 only |
| K1. Which value kinds occur in served rows | The implementing package enumerates the kinds produced by the six served queries over the existing test corpus | How often D4 withholds a write; whether in-process entries could later adopt the typed codec |
| A1. Whether any served result is independent of authorization | The native owner, per query | Whether a key may drop the authorization scope; the default keeps it |
| M1. Whether per-command model compilation or worker start is material | The bounded observation of UDM-13 on the stage, before final source | Whether the on-disk model tier is adopted and anything is warmed; the default is that neither happens |
| S1. Footprints of CPU runtimes, retained bytes of releases, the count of distinct macro tables | The same bounded observation | The defaults `runtime_bytes`, `release_bytes` and `parser_entries` |
| G1. Exact generator artifacts depend only on captured input/provenance and authenticated executing code | UDM-14 captures named resources, runtime/model inputs and copied bytes before keying, then closes the bounded rendering workload under UDM-10. Any broader capture must enforce the same complete-input contract | D2 eligibility and the shared T2 basis. A missing input is captured or removed before enabling reuse |
| C2. The selected reader's determining initialization and call paths are closed | UDM-10's code-closure follow-up, including the review's 33 saved sites and indirect-load counterexample, with root-specific evidence | Actual T4/D4 reuse and the UDM-15 entity route |
| E1. The authored native entity fixture is viable on N34 | UDM-15 adapts the existing committed authored-publication case and exercises two actual entity acquisitions | T14 production qualification, independently of the upstream PDF fixture failure |

## State

The bounded stage observation opened eight releases under N34 generation 31 and retained
187,696,277 declared bytes. Immediate repeats produced eight hits in the same process. CPU
preparation retained 1,295,718 declared bytes, including tokenizer files, matchers, the prose
grammar, and a compiled pack fixture. Three macro tables exercised two parser classifications.
The configured bounds leave room for additional process work. The observed model compilation
and spawned-process start support retaining the process-local design and leaving warming and
disk model caching unadopted for this increment.

| Package | State |
|---|---|
| UDM-13 | Six process retention mechanisms are implemented. Typed policy projections and owner-scoped CLI and MCP diagnostics passed bounded qualification. The native-installation holder in `semantic/native_generation.py:128–129` is bypassed under incomplete generator custody. Selected serving likewise permits fresh pages while withholding custody-dependent reuse. |
| UDM-14 | Shared generator capture and explicit served-key eligibility integrated. The rich row derivation accepts a typed acquired index. Actual entry-point reuse still awaits complete workload custody. |
| UDM-15 | Two-cut exclusion basis corrected. Direct entity witness integrated. The private authored native entity fixture passed. Real reuse requires complete code custody and the strict cross-process run. Other query variants retain the cut basis. |
