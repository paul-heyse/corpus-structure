# Book-processing efficiency and parallelism

**Functional-extension review · 2026-11-11. Recommendations and benefits: Proposed.**

## Conclusion and scope

Adopt a local hybrid execution design: one book coordinator owns durable work and publication; a bounded pool of warm CPU processes performs parser-bearing computation on process main threads; persistent provider lanes serve compatible inference requests. Advance independent source units and independent provider branches as their prerequisites become available. Combine this with operation-scoped release preparation, bounded immutable input reuse and native batching.

This is a substantial execution improvement, rather than a worker-count adjustment. The current code serializes both natural source units and much independent work inside them. It also repeats preparation and reconstructs immutable dependencies. These are source-established opportunities; their contribution to elapsed time and the best worker counts remain unmeasured.

The proving workload is the current Grinstead–Snell characterization: 316 direct SourceViews over the retained 518-page native document, all selected linguistic/formal/contextual families, regional views and one combined document view. The review covers preparation, inference, validation, publication, composition and recovery. PDF recognition is already complete for this run; its existing concurrency is relevant integration context, not work to repeat.

Preserve the maximally characterized enriched-document target, natural context boundaries, source fidelity, declared coverage, provider attribution and independently assessed semantics. Increased throughput must carry those guarantees. The operator chose to leave the live book running unchanged. This review changes no production code, dependency, native migration, source reference or execution setting.

## Baseline, sources and evidence

Inspected source: clean main at **4d0ca7eb75ffb4dd14ed969a3cbb584af073424e**, 2026-11-11. TC-E06's dependency/production indexes and TC-E07's source-control escaping are already implemented; they are not new recommendations.

The governing standard is [standard.toml](../design_review/design_principles/standard.toml): core3.3, [efficient-architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md), code-intelligence profile1.4 and repository binding. The strongest criteria here are FP-07/A4; DP-09/10/19/20; H2/5/8/9/12/14–24/26–28. This is a functional opportunity review, without a broad diagnostic audit prerequisite.

Architectural owners are [D6 orchestration](../design/D6-orchestration-metrics-policies.md), [D3 storage/publication](../design/D3-database.md), [ADR-0081](../adr/0081-enriched-document-analysis-layers.md) and [ADR-0082](../adr/0082-explicit-analysis-selection.md). The [TC coordinator](../plans/text-characterization_2026-11-10.md) continues to own existing implementation and qualification scope; this review does not amend it.

The supplied [Python concurrency reference](../libraries/analytical_infrastructure/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md) was read end to end. Its Python3.15 baseline supplies discovery leads; repository suitability is judged against installed CPython3.14.10, GIL enabled, spaCy3.8.18, Lark1.3.1, PyTorch2.15.0 and threadpoolctl3.7.0. Provider environments retain their own interpreter boundaries.

Read-only host inspection found 16 physical/32 logical CPUs, approximately188GiB visible RAM and an RTX5090 with approximately32GiB device memory. Process observations showed native provider multicore activity. Thus serialized outer orchestration and native multithreading coexist; one utilization snapshot cannot identify the critical path or establish a speedup.

Three focused contributions informed this account: execution/dependency mapping, preparation/batching assessment, and independent architectural comparison. They agreed on the hybrid direction. No model experiment, profiler attachment, benchmark or new provider execution was performed for this review. Existing implementation tests retain their original scope and are not performance evidence.

### Source-established execution shape

Paths below are relative to the source package linked in the table; line numbers identify the inspected revision.

| Responsibility | Current behavior and evidence |
| --- | --- |
| Regional orchestration | [orchestrate/characterization.py](../../python/corpus-structure/src/corpus_structure/orchestrate/characterization.py), lines710–885: constructs natural-unit demands, executes them sequentially at810–824, then composes the document from retained layers. Each public demand calls full release loading at604. |
| Source scheduler | [orchestrate/semantic.py](../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py), lines761–784/1006–1040/1527–1551: singleton execution groups dominate; one claimed method executes synchronously. Native and formal evidence have no analytical predecessor edge, but run serially. |
| Release preparation | [semantic/releases.py](../../python/corpus-structure/src/corpus_structure/semantic/releases.py), lines491–584: open_release reads historical products without establishing admission; load_release rederives and compares inputs, archives, artifacts and projections. |
| Resident resources | [methods/characterization_resources.py](../../python/corpus-structure/src/corpus_structure/methods/characterization_resources.py), lines66–94/181–259: one session slot per provider, ContextVar ownership and nonblocking refusal of concurrent borrowers. |
| Parser deadlines | [methods/math/grammar.py](../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py), lines467–519: process-main-thread SIGALRM deadlines. [Construction recognition](../../python/corpus-structure/src/corpus_structure/semantic/constructions/forest.py), lines652–678, reports unsupported off the main thread. Formal and scientific kernels share this constraint. |
| Durable concurrency | [execution_projection.sql](../../python/corpus-structure/src/corpus_structure/semantic/sql/execution_projection.sql), lines72–103: dependency-aware claims, SKIP LOCKED, attempt/holder/lease fencing. [Characterization publication](../../python/corpus-structure/src/corpus_structure/semantic/sql/characterization.sql), lines508–560, preserves coherent visibility and stale-owner protection. |

Current regional order is native/formal → constructions → contextual → model characterization → contextual evaluation → local composition. The two initial producers are independent. Different regional demands have no cross-request analytical dependency in this implementation; final document composition needs their settled selected products. Within contextual work, Maverick and DiPO run sequentially. Within model characterization, D1 precedes GLiNER although their inference branches warrant independent execution.

D1's question-stage dependencies and candidate populations are real dependencies. Context used for a provider request is also semantic input. Parallelism or batching must not concatenate independent passages into a different model context.

## Opportunities and dispositions

<a id="O01"></a>
### O01 · Prepare the exact execution release once per operation

**Recommend first.** The book loop repeatedly calls a loader whose purpose is full offline rederivation. Existing pure compilation caches do not eliminate all archive/input hashing, reconstruction and projection comparisons in that route.

Perform full load_release once at the outer book execution boundary. Supply that exact PreparedRelease through private demand execution. Standalone demands retain their own preparation boundary. A CPU worker needs its own usable prepared state, initialized once from exact immutable inputs; compiled objects and callbacks must not be assumed picklable.

Carry this preparation through internal stage/reader construction as well as the outer demand call. Hoisting one call while another execution layer rederives the same release would leave the amplification in place.

Do not replace execution preparation globally with open_release. Its existing engine-local finalized-archive cache serves reading, not admission. Keep database state, permissions, current execution admission and publication fences live; [execution_admission.py](../../python/corpus-structure/src/corpus_structure/semantic/execution_admission.py), lines44–50, explicitly separates uncached database admission.

The validity scope includes selected release, compiler/runtime, configuration and relevant immutable inputs. A changed context creates new preparation. This purchases shorter repeated execution paths without weakening authority. Delivery must show one full preparation per stable operation/address-space scope and correct refusal after consequential context changes. H12/H18–20.

<a id="O02"></a>
### O02 · Carry bounded authenticated regional state across producers

**Recommend with O01.** [LayerReport](../../python/corpus-structure/src/corpus_structure/semantic/characterization.py), lines225–245, decodes on every payload access and hashes for reference access. Stage selection repeatedly requests payloads. [BoundReader.characterization_layers](../../python/corpus-structure/src/corpus_structure/semantic/operations.py), around1075, reloads upstream reports; new validation contexts recursively reconstruct dependency validity.

Own a bounded preparation for each admitted region: authenticated source values, immutable decoded views, exact dependency pins, source/occurrence indexes and scoped validation results. Reuse sufficient source hydration and dependency preparation across its consumers. Release large bodies after their last consumer; retain compact manifests/pins for document composition.

Keep today's fresh-value public payload API: exposing a cached writable dictionary would change ownership. A digest or publicly constructible LayerReport is not evidence of prior validation. Reuse established properties only for protected admitted products under exact content/release/closure premises. New results, imported/untrusted bytes, source authorization and native publication retain their enforcement boundaries.

Source reads are already selective; the change is lifetime and ownership, not whole-book hydration. Prefer bounded immutable regional state to a global cache retaining all book layers. Delivery includes mutated/untrusted dependency refusal, cross-release correctness and eviction without recomputation of unrelated regions. H5/H14–20.

<a id="O03"></a>
### O03 · Advance independent units through a bounded dependency pipeline

**Recommend as the concurrency foundation.** Replace whole-unit serial coordination with a bounded ready frontier. Admit several natural units and advance each when its actual prerequisites settle. Native work for one region can overlap formal, construction or contextual work for others. Slow units should not hold unrelated completed work behind input-order consumption.

One coordinator retains run supervision, task registration, claims, renewal, completion preparation and publication. Register dependent tasks only after their immutable predecessor pins exist: those pins determine actual task configuration/input identity. Keep existing stage-run boundaries initially; changing their number is not required to obtain cross-unit overlap.

Existing database claims enforce recorded dependencies, but this is not a general cross-run DAG already waiting to be enabled. Current [source dependency admission](../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql), lines498–519, admits specific same-run relationships. General placeholder products or cross-run blocked-task registration would be an additional contract extension, not part of this recommendation.

Use completion-driven readiness with stable source ordinals for final assembly. Transient physical dispatch belongs under existing durable work ownership; it does not need another database queue, broker or workflow engine. H2/H8/H21–25.

<a id="O04"></a>
### O04 · Place CPU kernels and independent inference at suitable boundaries

**Recommend the hybrid placement.** Use a bounded warm ProcessPoolExecutor with explicit spawn context for parser-bearing formal/construction/scientific kernels. One CPU operation runs on each process main thread, preserving process-wide deadline ownership. Initialize stable contracts/declarations once per worker.

Keep database engines, connections, borrowed readers, ContextVar sessions, method contexts and CUDA state out of process arguments. The coordinator prepares operation-shaped immutable inputs and receives private draft results. Return lightweight references where existing owned artifacts suffice; otherwise use bounded immutable payload transfer. Memory mapping is conditional on an actual transfer burden.

Existing source readers temporarily rebind connections under a lock. They cannot simply become shared concurrent method contexts. Extract pure computation seams from current methods while preserving their semantic owners, rather than wrapping complete demands in threads.

Give each provider/profile lane exclusive ownership of its resident child and one active IPC exchange. Bounded parent-side admission replaces nonblocking borrower refusal as ordinary scheduling behavior. Small I/O threads can service independent lanes while CPU workers compute.

Maverick/DiPO and D1/GLiNER should produce private branch responses concurrently where inputs are independent, followed by single-owner deterministic builder reduction. Candidate D1 questions still wait for their contextual populations. Completion callbacks must not mutate shared builders.

Python's [process executor](https://docs.python.org/3.14/library/concurrent.futures.html#processpoolexecutor) supports worker initialization and explicit process contexts. [Spawn](https://docs.python.org/3.14/library/multiprocessing.html#contexts-and-start-methods) avoids inheriting active parent resources. This does not establish transferability of project runtime objects. H3/H17/H22–24.

<a id="O05"></a>
### O05 · Batch compatible native requests with complete attribution

**Recommend bounded compatible batching; qualify cross-unit batching deliberately.**

| Provider | Existing capability / avoidable work | Recommended change and condition |
| --- | --- | --- |
| spaCy | Cached pipelines and nlp.pipe batching already exist in ingest/annotations.py. | Preserve batching. Consider n_process only for its actual native path and atom-preserving input contract; it is not a substitute for whole-pipeline scheduling. |
| HanLP | native_evidence.py179–264 performs prepare_only per sentence, then inference batches; pm2_hanlp.py175–203 prepares again through the model path. | Batch sentence admission first. Reuse prepared samples only through a supported installed HanLP contract; preserve unsplit sentences, protected atoms and actual subword/padded bounds. |
| D1 | model_characterization.py491–558 already batches independent ready questions; pm2_native.py117–156 repacks by length and scatters by ordinal. | Preserve question-stage barriers and exploit compatible ready requests from multiple admitted regions. Keep each question's exact context and options. |
| GLiNER | gliner_worker.py172–178 uses native batch_extract, but characterization submits singleton scopes for cues and functions. | Group compatible pack/profile/policy populations and update authentication/projection together. Exact batch envelope and member ordinal must survive. |
| Maverick / DiPO | Separate native branches currently run serially. | Overlap separate lanes; batch only where each provider's actual interface preserves document/context semantics. |

Sources: [native_evidence.py](../../python/corpus-structure/src/corpus_structure/methods/native_evidence.py), [pm2_hanlp.py](../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp.py), [model_characterization.py](../../python/corpus-structure/src/corpus_structure/methods/model_characterization.py), [pm2_native.py](../../python/corpus-structure/src/corpus_structure/methods/pm2_native.py), [gliner_worker.py](../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py), [contextual_characterization.py](../../python/corpus-structure/src/corpus_structure/methods/contextual_characterization.py).

GLiNER's whole-request digest includes its input population, while [classification projection](../../python/corpus-structure/src/corpus_structure/methods/pm2_gliner_classification.py), lines156–180, and semantic cue authentication currently expect singleton digests. Changing the tuple length alone breaks the contract. Retain batch-level provenance plus item association and settle whether membership/order changes prediction. Stable grouping or an explicit inference-identity change is required where batch membership affects results.

Start with compatible scopes already available inside a method; extend across regions with the same contract. Never merge passages into a new language context to fill a batch. H8/H10/H12/H16.

<a id="O06"></a>
### O06 · Coordinate native threads, device residency and all admitted state

**Recommend one execution policy; CUDA qualification is a selected investigation.** The host has useful CPU and GPU capacity, but logical CPU count is not a suitable independent default for every pool.

Coordinate CPU processes, native intra/inter-op threads, provider residents, queued input/replies, decoded dependencies, connection borrowers and active run supervisors. GLiNER already sets OMP/MKL and PyTorch limits. The inspected PM2 launcher disables tokenizer parallelism but does not establish corresponding native thread limits. Set supported limits inside each child before native work; parent environment settings alone do not suffice because PM2 constructs its own child environment.

Use the existing [threadpoolctl](https://github.com/joblib/threadpoolctl) capability for supported BLAS/OpenMP runtimes and provider-specific PyTorch controls. It does not govern Python worker count or GPU residency. Select outer concurrency and inner thread allocations together, with finite item and byte admission; completed replies awaiting reduction also occupy capacity.

CPU is the current default for HanLP, contextual native providers and D1. CUDA configuration paths exist, but [pm2_worker.py](../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py), lines400–428, also owns Nemotron suspension and device custody. Qualify suitable provider/profile CUDA lanes on the RTX5090, including service interpreter/wheel compatibility, precision, output attribution, memory and coexistence. GPU placement is an explicit runtime selection; an inference error must not silently select a different device.

The initial target keeps one resident per selected provider/profile and increases useful work through overlap and batching. Additional replicas are conditional on a remaining saturated lane and acceptable combined memory/thread behavior. Exact counts need a bounded operating choice after actual thread and resident-state inspection; no numerical optimum or speedup is established here. H17/H21/H25/H28.

<a id="O07"></a>
### O07 · Keep publication efficient and recovery proportional

**Recommend integration with O03–O06.** Computation remains private and outside publication locks. Preserve canonical/projection agreement, source/role/choice validation and atomic visibility at the native boundary. Prepare reusable immutable data before entering publication, rather than weakening native enforcement.

The default writer pool has maximum4 connections and4 waiters. Review read/completion admission and renewal together; each active run supervisor also owns a dedicated connection outside that pool. More workers must not starve task renewal or multiply a separate pool per CPU worker.

Keep natural units and independently useful layers as recovery boundaries. Lease only work admitted to execution or a short bounded queue. Cross-unit batches need multiple logical cancellation owners: retire a stale/cancelled member and fence its completion while useful surviving members continue. Terminate shared inference when the invocation is cancelled or no live borrower needs it. A provider failure retires that lane and follows existing task outcome/retry policy; it does not create another retry owner.

CPU cancellation uses cooperative checks and existing deadlines; pool-wide termination is a contained fallback for database-free kernels. Future cancellation or a wait timeout is not an executing-task kill. Preserve uncertain completion replay, valid settled siblings, and explicit failed/unavailable family coverage.

Keep manifest-based final composition. Collapsing durable stage runs or changing projection inventories is conditional on a concrete remaining burden and consumer analysis; neither is necessary to adopt the preferred topology. H2/H18–24/H26–27.

<a id="O08"></a>
### O08 · Make execution policy and progress usable through existing operations

**Recommend a thin operational surface with the implementation.** Existing ci characterization/ingest operations should select one recorded execution policy covering admitted units, CPU/native threads, provider lanes, queue bounds and device profiles. Semantic family selection remains separate from physical placement.

Extend existing managed status/task inspection to distinguish waiting for prerequisites, waiting for capacity, active computation and publication. Use existing lineage and request/task correlation; aggregate routine progress by unit/stage/provider. Preserve exact run/task outcomes and avoid per-token diagnostics.

A cancel/resume uses existing operation ownership and retained products. The operator should be able to understand why work is waiting and resume the necessary remainder without manually coordinating several workers or reconstructing source selections. This needs no daemon, new dashboard, cost estimator or parallel progress database. H8/H24–27.

## Complete alternatives and library dispositions

| Realization | Judgment |
| --- | --- |
| Current serial path plus local caches | Useful immediate work reduction, but retains unnecessary unit and provider barriers. Insufficient as the overall parallelism target. |
| Warm full-unit process workers | Credible simpler alternative: process-main-thread deadlines and isolated readers work naturally. Each worker duplicates the model fleet and native pools, and residents sit idle during other phases. Choose only if a small replica population provides adequate throughput with acceptable total state. |
| Provider queues alone | Useful residency/batching foundation; incomplete for parser-bearing Python CPU computation. Turning every pure kernel into a model-style service adds unnecessary machinery. |
| **Coordinator + warm CPU processes + persistent provider lanes** | **Preferred.** Separates durable ownership, CPU execution and model residency. Requires real preparation/inference/reduction seams, but supports both inter-unit and intra-method overlap without model-fleet replication. |
| General distributed task engine | Deferred. This single-workstation workload has no established broker, cluster or remote recovery requirement. Revisit for actual multi-host operations, not merely because Dask/Ray/Celery exist. |

The overview's materially promising capabilities receive the following dispositions:

| Capability | Disposition / concrete role |
| --- | --- |
| submit, wait(FIRST_COMPLETED), as_completed | Select completion-driven dispatch within an explicitly bounded window; final ordering is a separate deterministic reduction. |
| Executor.map buffersize / chunksize | Available3.14 alternatives. Ordered map can delay delivery behind a slow input; chunksize concerns process dispatch, not semantic scope. Prefer completion-driven admission for skewed regions. |
| ProcessPoolExecutor initializer / explicit spawn context | Select for worker-local stable CPU preparation and main-thread kernels. |
| ThreadPoolExecutor / native GIL-releasing calls | Select only for suitable owned I/O/native branches. Whole-demand threading violates current parser deadline behavior. |
| asyncio TaskGroup / subprocess APIs | Conditional orchestration implementation if it simplifies existing supervision. Async wrappers alone do not make Python CPU work parallel or stop underlying executor work. |
| threadpoolctl / native thread controls | Select coordinated nested capacity; qualify supported runtime coverage. |
| SharedMemory / mmap / compact descriptors | Compact immutable transfer is selected; shared memory/mapping is conditional on substantial repeated movement. It needs explicit ownership and cleanup. |
| InterpreterPoolExecutor / concurrent.interpreters | Available3.14 research alternative for isolated suitable Python work. Defer the mixed NLP path pending extension compatibility, serialization and failure-containment evidence. |
| Free-threaded CPython | Defer runtime migration. The current build has an enabled GIL; extension compatibility, synchronization and deadlines remain obligations even with a different build. |
| Joblib/Loky | Conditional alternative if reusable executors, dispatch control or array memmapping removes a demonstrated gap. Standard executors plus existing residents currently cover the chosen responsibilities. |
| MPIRE | Conditional if worker-local state, affinity or lifecycle needs exceed the selected pool's simple initialization contract. |
| Pebble / AnyIO process cancellation | Conditional for a concrete per-call termination gap. Preserve existing process-group ownership rather than layering conflicting timeout/retry authorities. |
| Dask / Ray | Defer distributed graphs/actors/spill unless local composition proves insufficient or multi-host requirements arise. |
| Celery / MPI | No present broker-owned background workload or MPI deployment need; revisit on those requirements. |
| Diagnostics/profiling | Use existing timing/outcomes and selective inspection first. A bounded diagnostic may resolve uncertain bottlenecks; no standing benchmark or instrumentation project is selected. |

Version-sensitive contracts must use [Python3.14 futures](https://docs.python.org/3.14/library/concurrent.futures.html), [multiprocessing](https://docs.python.org/3.14/library/multiprocessing.html) and [interpreter documentation](https://docs.python.org/3.14/library/concurrent.interpreters.html). The overview's3.15-only leads, including the new sampling profiler and forkserver preload on_error option, are not assumed available. No runtime upgrade is selected.

## Recommended target and integration order

~~~mermaid
flowchart LR
    S[Exact retained source and verified preparation] --> C[Book coordinator and bounded ready units]
    C --> P[Warm CPU processes: formal and construction kernels]
    C --> N[Resident native provider lanes]
    P --> R[Owned deterministic regional reduction]
    N --> R
    R --> C
    R --> V[Existing fenced publication]
    V --> D[Manifest-based combined document]
~~~

The diagram is physical placement, not a replacement semantic stage graph. Inference requests retain original focal/context boundaries. Builders remain single-owner. Source/request/provider/batch ordinals control reduction; completion timing does not define annotation order. Separate executions may have different task IDs while preserving their declared semantics and provenance.

Prioritize O01/O02 first, then integrate O03/O04/O07 as one coherent execution change. Add O05 batching where its attribution contract is qualified; coordinate O06 throughout and qualify CUDA provider choices explicitly. Deliver O08 with the new execution behavior. Remove superseded serial coordination and implicit borrower ownership from the production path when the replacement is complete.

Keep current task/run identities and native claims initially. The coordinator binds newly ready work after real predecessor products exist, uses native readiness/fencing where applicable, and maintains only transient physical queues. A general persistent layer DAG, placeholder product identities and cross-run dependency rules are not selected.

### Architectural and interface implications

- **RC01 — D6 stage barriers:** permit overlap across independent units and independent producer branches. Keep genuine dependencies and final composition settlement explicit.
- **RC02 — Resource ownership:** replace implicit ContextVar borrower/refusal coordination with operation-owned admission and resident lane ownership. Preserve exact profile compatibility and process-group teardown.
- **RC03 — Prepared execution:** authorize scoped reuse of fully verified immutable preparation, without caching current database permissions/admission or treating read-only archive hydration as execution admission.
- **RC04 — Method seams and batching:** separate input preparation, inference and deterministic reduction; migrate GLiNER batch authentication/projectors together. Preserve one authoritative implementation and existing semantic operation ownership.
- **Conditional decision:** changing durable run granularity or admitting general cross-run blocked dependencies requires its own demonstrated benefit and contract treatment; the target can proceed without it.

These are proposed changes for later plan creation and applicable ADR/owner updates. This review neither amends accepted ADRs nor grants production adoption. Public request/configuration changes belong to the recorded physical execution policy; existing semantic source/layer pins and full-family demand remain authoritative.

## Delivery scenarios and remaining investigation

| Concern | Implementation acceptance evidence |
| --- | --- |
| Serial/parallel fidelity | Compare declared deterministic structure, native attributes, source coordinates, roles, choices, coverage and retained closure on the same inputs. Preserve permitted numerical variation explicitly; byte equality is not assumed across arbitrary device/batch changes. |
| Completion order and skew | Slow region, large formula, short text and out-of-order provider results produce stable supported assembly; ready work progresses without an unrelated input-order barrier. |
| Trust and reuse | Untrusted/mutated bytes, wrong source/release, changed runtime/configuration and stale prepared context refuse appropriately; compatible immutable preparation is reused within its scope. |
| Batch semantics | Mixed lengths, distinct contexts, partial/invalid members, order changes and GLiNER batch digests retain exact item attribution and provider limits. Test selected real providers. |
| Lifecycle | One stale/cancelled member in a useful shared batch, whole-book cancellation, CPU deadline expiry, provider crash and uncertain publication retain settled siblings and prevent stale completion. |
| Capacity and DB progress | Full admitted state, nested native threads, outstanding replies and supervisor connections remain bounded; renewal progresses while reads/publications contend. |
| Consumers | Independently settled regional views and final combined views preserve Reader/CLI/MCP/export/replay semantics and exact selected closure. |

Before fixing implementation counts and interfaces, settle the smallest transferable CPU input packet, installed HanLP prepared-sample support, PM2 thread defaults, GLiNER batch/member authentication, and CUDA compatibility/output behavior. These are bounded feasibility obligations attached to O04–O06, not reasons to defer the coherent target.

Performance claims need appropriate representative evidence across preparation, inference, movement and publication, including cold/warm conditions and concurrent workload context. Structural removal of repeated work and unnecessary barriers is established by source inspection; improvement magnitude remains Proposed. No full-book rerun or intrusive profiler attachment was required to reach this review's conclusions.

## Publication outcome

2026-11-11: review completed from source, installed-runtime/host observations, primary documentation and focused independent advice. Product/provider tests, runtime experiments and performance measurements for the proposed design: **not_run**. Current book processing continues under the existing implementation. Documentation validation **passed**, 2026-11-11: uv run ci docs check --json, result afeb8b2edfcc4566a5d74b9ee34df53c, 874 canonical pages and zero link errors. Independent final coherence checking found no material defect. Production/provider tests for this documentation-only engagement remain not_run.
