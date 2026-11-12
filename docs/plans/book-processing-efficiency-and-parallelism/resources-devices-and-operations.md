# Resources, devices and operator workflows

**Status: GPU-default shared-host and common-request target accepted2026-11-12; BEP-07/08 implementation and qualification remain incomplete.** This companion owns BEP-07 and BEP-08 in the
[book-processing series](../book-processing-efficiency-and-parallelism_2026-11-11.md).
Original planning baseline is `f81a380cd`; the current focused source assessment inspected
`33085983a` on2026-11-12. [ADR-0088](../../adr/0088-gpu-default-native-hosts.md) records the
operator-approved replacement for ADR-0087's CPU/hybrid device selection. Historical receipts below
retain their original scope. This document schedules implementation; it establishes no provider pass.
The source [functional review](../../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md#O06)
supplies O06, and [O08](../../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md#O08)
supplies the operational scope. RC01–RC04 were explicitly accepted by the operator on
2026-11-11; the coordinator owns their decision routes and current series disposition.
Neither that acceptance nor this document establishes implementation or qualification.

The intended result is one usable local execution policy: independent book work can progress
without multiplying native thread pools, model fleets, outstanding payloads or database
borrowers without a bound. The operator selects and inspects that policy through existing
operations, can explain a wait, and can cancel or resume retained work without managing workers.
This companion edit itself runs no book, provider or product tests. Implementation and qualification
are authorized through the coordinator's approved execution sequence; native/book work follows its
later prerequisites. The TC plans remain untouched.
Protected reference sets, source-first exposure boundaries and independent assessment remain under
their existing owners.

## Operator closeout checkpoint · 2026-11-12

The [coordinator checkpoint](../book-processing-efficiency-and-parallelism_2026-11-11.md#audit-repair-execution)
owns integrated delivery, scoped evidence and remaining execution. GPU foundations remain
unselected; native/assembled qualification and full-book acceptance are not established here.

## Baseline and responsibility boundaries

The target separates durable ownership from physical placement. BEP-03 owns process-main-thread
pure CPU kernels; BEP-04 owns resident providers in two shared native hosts; BEP-05 owns
dependency-ready coordination and publication; BEP-06 owns native batch authentication and
deterministic item projection. Those
packages consume the early BEP-07a contract below. BEP-07b integrates the selected GPU profiles and
bounded host concurrency before BEP-09 full qualification.
BEP-08 migrates all existing entry points and operator-facing reports to that same ownership.

The source-established constraints are:

| Existing owner | Consequence for this work |
| --- | --- |
| [Resources and MethodSettings](../../../python/corpus-structure/src/corpus_structure/core/method.py) | MethodSettings carries paths/endpoints and execution policy; classify each setting by its semantic effect rather than treating every field there as result-neutral. Resource declarations do not independently implement dispatch. |
| [Provider execution](../../../python/corpus-structure/src/corpus_structure/methods/characterization_resources.py) | Existing explicit lanes retain one resident/exchange and bounded pending work; CUDA work currently shares one lane key. Replace that internal GPU-wide serialization with shared-host admission and narrow provider gates. |
| [PM2 launch](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py), lines378–465 | The child receives a constructed environment, explicit device and bounded IPC. Parent-only OMP settings do not reach this child automatically. CUDA startup and teardown already hold device/Nemotron custody. |
| [GLiNER worker](../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py), lines98–102/272–283/350–383; [model load](../../../python/corpus-structure/src/corpus_structure/methods/gliner.py), lines502–511 | GLiNER already uses spawn, profile-sized immutable batches, OMP/MKL limits and PyTorch intra/inter-op controls. Preserve those bounds and qualify the batch contract through BEP-06. |
| [Database settings](../../../python/corpus-structure/src/corpus_structure/settings.py), lines40–66; [store](../../../python/corpus-structure/src/corpus_structure/core/db/store.py), lines124–157 | The default ordinary pool has maximum4 connections and4 waiters. CPU/native computation must not create a pool per worker. Pool/admission selection must preserve renewal progress. |
| [Supervisor connection](../../../python/corpus-structure/src/corpus_structure/orchestrate/liveness.py), lines14–85 | Each active run supervisor holds a dedicated physical connection outside the ordinary writer pool. Counting only pool borrowers misses real connection state. |
| [Claim lifetime](../../../python/corpus-structure/src/corpus_structure/semantic/claim_lifetime.py), lines58–109/160–281 | Renewal and exact completion/replay already have owners. More physical concurrency must not starve them or install another retry policy. |

The review observed16 physical/32 logical CPUs, approximately188GiB visible RAM, an RTX5090 with
approximately32GiB device memory, and native multicore provider activity. These are dated
2026-11-11 observations, not a selected worker count, reserved capacity or acceleration result.
The root interpreter is CPython3.14.10 with the GIL enabled. The selected target groups providers
by compatible locked interpreter/runtime rather than retaining one process per model. Native
intra-operation parallelism exists even when outer orchestration is serial.

<a id="bep-07a"></a>
## BEP-07a · Shared physical policy and admission contract

**Input:** BEP-00's accepted ownership/rule treatment and the responsibilities above.
**Output:** one implemented, validated physical-policy/admission boundary consumed by BEP-02–06
and BEP-08, with its selected values recorded through the existing invocation/run reporting route.
This is an early slice of BEP-07, not closure of its device/count obligations.

Settle this contract before dependent packages independently choose limits, environment variables
or resource owners. It must express the following related decisions; the implementation may use
ordinary immutable values and existing settings rather than create a type/service per row.

| Policy responsibility | Required behavior |
| --- | --- |
| Admitted natural units and CPU submissions | Bound the operation's ready/in-flight units and submitted process work. Preserve actual focal/context boundaries; counts do not select smaller semantic inputs. |
| Native residency and thread allocation | Initially one resident per selected compatible provider/profile, with explicit native thread controls and supported device selection. Additional replicas require a demonstrated remaining lane-capacity need and an acceptable combined live set. |
| Input, reply and reduction capacity | Bound both items and bytes. Include completed replies waiting for reduction, prepared CPU packets, decoded dependencies and output drafts; release capacity after the last consumer, not merely after inference returns. |
| Database activity and supervisors | Coordinate reads, completion preparation, publication, renewal checkouts, pool waiters and active dedicated supervisors. Account for current stage-run granularity without silently replacing it. |
| Stop and drain | No new admission after operation cancellation. Each owner knows whether to discard queued work, drain useful in-flight work, stop a resident or release device custody. Existing claim/attempt fences decide publication. |

There is one operation-owned admission decision across these components. Do not add independent
unbounded executor submission behind a bounded provider queue, or let every lane allocate all
logical CPUs internally. Backpressure reaches the ready-unit coordinator: a saturated downstream
lane limits upstream hydration/submission. Waiting does not itself convert valid work to failed
coverage. Lease only admitted work or a short bounded queue, with BEP-05 retaining the durable owner.

Physical policy is distinct from semantic demand and inference identity. Unit windows, queue
limits and the number of database borrowers ordinarily describe placement/capacity. Source scope,
selected families, provider/runtime/artifact identity, dtype/precision, device and authenticated
batch interpretation retain their released/configured meaning. A changed setting is classified
by whether it can change produced meaning or its required authentication; it is not declared
result-neutral by location in a settings file. BEP-06 owns batch-member identity and any compatible
reuse treatment. Record the actual resolved policy, including selected device profiles and known
thread limits, without forcing every scheduling choice into semantic cache keys or allowing a
new inference profile to reuse an incompatible result.

For CPU execution, use the selected
[Python3.14 ProcessPoolExecutor APIs](https://docs.python.org/3.14/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor)
with explicit `multiprocessing.get_context("spawn")`, `initializer` and bounded completion-driven
submission. These provide worker lifecycle and per-process preparation; BEP-03 supplies the
transferable packet and main-thread kernel contracts. `submit()` alone is not a pending-byte
bound. `map(buffersize=...)` exists in3.14 but ordered delivery can hold a fast region behind a
slow input; this is why the coordinator uses `wait(..., return_when=FIRST_COMPLETED)` or
`as_completed` with separate stable reduction ordering. Do not assume Python3.15-only APIs from
the discovery overview. No interpreter upgrade, free-threaded migration or general resource
estimator is selected.

**Local acceptance:** dependent packages consume the same policy/admission values; deliberately
full downstream state stops further hydration/submission; completed replies remain charged until
reduced; cancellation drains the owned scope; semantic family/source selection is unaffected by a
pure placement change. These are focused behavioral checks at the integrated capability endpoint,
not an integrated gate after each edit. Actual count selection remains BEP-07b.

<a id="bep-07b"></a>
## BEP-07b · GPU-default shared hosts and coordinated admission

**Input:** BEP-07a plus working BEP-02–05 and the retained BEP-06 attribution contracts.
**Output:** the approved two-host GPU-default implementation, compatible frozen provider profiles,
finite shared admission and scoped current-device qualification. BEP-09 consumes the final policy.
Historical CPU batch evidence informs preservation; it does not qualify the new CUDA profiles or
require another CPU campaign before implementing the accepted target.

### Native threads, state and connection progress

Initialize each shared host before concurrent work. Existing provider loaders independently set
OMP/MKL/PyTorch controls; consolidate those process-scoped settings under one host owner instead
of invoking them again for every resident or request. Preserve compatible frozen profile treatment. Use
[PyTorch set_num_threads](https://docs.pytorch.org/docs/stable/generated/torch.set_num_threads.html)
before eager/JIT/autograd work and
[set_num_interop_threads](https://docs.pytorch.org/docs/stable/generated/torch.set_num_interop_threads.html)
once before inter-op work. Version relevance is the selected PyTorch2.15.0/provider environment,
not an assumed parent installation. Their process-scoped timing constraints favor child startup
initialization rather than per-request retuning by competing threads.

Use the already selected
[threadpoolctl3.7.0 capability](https://github.com/joblib/threadpoolctl/tree/3.7.0) for supported
BLAS/OpenMP runtime inspection and `threadpool_limits` where applicable. It does not control
Python executor size, all possible native runtimes, HF tokenizers or GPU residency. Inspect after
the relevant libraries load; document unsupported/multiple-runtime limitations. Do not claim a
thread bound solely from setting environment variables or from one library's thread count.

Choose CPU processes, concurrent native lanes and per-provider thread allocations together for
the observed host and representative skewed units. Include root CPU reduction, memory held by
resident models, source/dependency state, in-flight packets/replies and pending publication. Record
the supported values and why their combined route is credible; there is no required numerical
optimum or benefit benchmark. Use a bounded experiment only where actual contention, memory or
native numerical behavior leaves a consequential choice unresolved. A selected fixed operating
policy is sufficient; an adaptive controller or cost model is not required.

Choose pool/admission values with BEP-05 so short reads/publications and finite completion work
cannot occupy every path needed for renewal. Count dedicated supervisors separately. Existing
`psycopg_pool.ConnectionPool`/SQLAlchemy `NullPool` borrowing remains the connection owner; do not
pass engines to CPU workers or introduce a pool per lane. Verify checkout/renewal progress under
the maximum admitted state, preserving finite server deadlines and exact completion replay.

### Selected GPU profiles and compatible host groups

**Proposed accepted target · 2026-11-12; Interface-checked source basis, not native qualification.**
All six learned NLP providers default to GPU. Missing prerequisites refuse the selected GPU
profile; no runtime error, timeout or capacity pressure silently substitutes CPU, another model,
reduced precision, truncation or a different family. Lark/SymPy, source mapping, tokenization,
projection, validation and parent reduction remain CPU responsibilities.

| Provider / host | Selected execution and preservation | Actual migration obligation |
| --- | --- | --- |
| D1 / CPython3.14.10 | CUDA/BF16, existing checkpoint, set-size16 and ordered question/state/dependency semantics | Preserve its existing native profile; move residency into the shared host without changing input order or precision. |
| GLiNER / CPython3.14.10 | CUDA/FP32, existing GLiNER2.5 boundary checkpoint, standard attention and exact splitter/threshold recipes | Replace CPU-only loader/profile/authentication assumptions, including cue projection and supported direct workers; retain historical CPU authentication under its original identity. |
| HanLP / CPython3.14.10 | CUDA/FP32, existing ModernBERT MTL checkpoint, selected heads and canonical pretokenized inputs | Select the already device-aware adapter's CUDA route; preserve sentinel repair, whole sentences and actual native preparation. |
| spaCy / CPython3.14.10 | CUDA/FP32 learned components of en_core_web_sm3.8.0; unchanged tokenizer, rules, protected atoms and coordinates | Move learned annotation out of the pure CPU pool. Separate tokenizer-only source preparation from full pipeline residency, avoiding a parent GPU model or a model per CPU worker. |
| Maverick / CPython3.12.3 | CUDA/FP32, existing MES head and DeBERTa checkpoint | Retain native document semantics and exact token/mention mapping in the common3.12 host. |
| DiPO / CPython3.12.3 | CUDA/FP32, existing DMRST/CRF/Ettin selection, compile_encoder=False | Retain learned/forced boundary provenance and exact EDU mapping in the common3.12 host. |

The target has **two supervised shared provider hosts**, each with a small bounded thread pool,
one resident per selected compatible profile and explicit per-provider streams. The3.14 host
reuses the root environment with exact HanLP/hanlp-common and direct CuPy dependencies; the3.12
host combines Maverick/DiPO with deliberate compatible transitive pins. This retains real
interpreter/dependency boundaries while removing incidental per-model processes. Do not add
multi-document batching to Maverick/DiPO without a supported native semantic contract.

The full [Transformers overview](../../libraries/parsing/transformers.md) was read for the focused
assessment. It targets5.22.2; selected runtimes use5.22.1 and Torch2.15.0. Existing locks already
carry CUDA13 components and Linux CPython3.14/3.12 Torch wheels. No Torch/Transformers upgrade,
quantization, attention replacement, compilation, automatic offload or dtype change is selected
merely to move inference to GPU. FP32 dtype does not by itself declare CPU/GPU numerical equality
or a particular TF32/math mode; freeze consequential effective settings with their owner.

### Dependency prerequisites established by inspection

These are **Interface-checked2026-11-12**, not passed environment/native results. Reconcile exact
pins and regenerate only the intended lock footprint during implementation; never merge two
existing lock identities and claim the environment unchanged.

- Root/HanLP share their selected Python/Torch/Transformers versions but their locks differ,
  including huggingface-hub1.33.0/2.4.0. HanLP's installed metadata has broad compatible bounds;
  add its exact dependencies to the3.14 host and establish one actual runtime identity.
- spaCy3.8.18/Thinc8.3.14 require CuPy for CUDA. Select direct
  `cupy-cuda13x==14.2.0`; its ordinary CPython3.14 Linux wheel is published. The installed spaCy
  CUDA extras constrain CuPy below13, so do not use those extras as the installation recipe.
  Thinc/CuPy operation compatibility, root NumPy2.5.4 and actual backend/device execution remain
  explicit prerequisites. Use `spacy.require_gpu()` before loading the selected pipeline, never
  `prefer_gpu()` fallback. See [spaCy GPU setup](https://spacy.io/usage#gpu),
  [device API](https://spacy.io/api/top-level#spacy.require_gpu),
  [CuPy installation](https://docs.cupy.dev/en/stable/install.html) and
  [exact wheel release](https://pypi.org/project/cupy-cuda13x/14.2.0/#files).
- Maverick1.0.7 requires Protobuf3.20 and SentencePiece0.2.0. DiPO0.2.1 currently selects
  TensorBoard2.21.0 requiring Protobuf>=6.31.1, so the current locked sets cannot coexist.
  The selected scoped compatibility candidate is `tensorboard==2.18.0`, `protobuf==3.20.0`,
  `sentencepiece==0.2.0`, `setuptools==80.10.2`, retaining exact primary model libraries.
  [Official TensorBoard2.18 metadata](https://pypi.org/pypi/tensorboard/2.18.0/json) permits
  Protobuf>=3.19.6 except4.24.0, Setuptools>=41 and Python>=3.9; the selected Setuptools also
  satisfies DiPO<81 and Torch>=77.0.3. No TensorBoard/SummaryWriter use was found in the installed
  DiPO Python source or selected inference path. Resolution, imports and native fidelity remain
  required; metadata agreement is not a qualification pass. Further concrete incompatibilities
  return to the coordinator rather than prompting an arbitrary provider upgrade or CPU fallback.

### Different-model concurrency and narrow wrapper gates

Use bounded concurrent submission for **different** resident providers, each in its explicit
`torch.cuda.device`/`torch.cuda.stream` context. A CUDA-capable tensor runtime does not establish
reentrancy of a mutable wrapper. Current source gives these narrow protections:

| Owner | Source-established reason and selected protection |
| --- | --- |
| D1 | Retained attention.py installs/removes a request-capturing forward pre-hook for state/set attention. One active call per instance; preserve batched independent questions and actual prior-state dependencies. |
| Maverick | pm2_dispatched.py installs a per-request forward hook and shares a post-tokenizer counter. One active call per wrapper instance. |
| DiPO | pm2_dispatched.py temporarily replaces module-global EDU recovery/tokenization functions and instance prediction functions. One active DiPO module scope while those patches remain; two instance locks alone would not protect shared module functions. |
| HanLP | Selected MTL prediction changes BOS/EOS flags on the shared tokenizer transform; the sentinel repair is installed once. One active wrapper call with its native bulk population. |
| GLiNER | Extraction changes eval/processor mode and lazily creates a collator. Its tokenization LRU is thread-safe, but complete extractor reentrancy is unqualified. One active call per extractor, preserving local cohorts. |
| spaCy | Backend context and pipeline/vocabulary ownership require their own scope. One active call per resident pipeline; independent Torch models can overlap. |

These gates protect their named state; they are not a global GPU lock. Serialize model loading,
import-time registrations and loader patches, then serve independent residents concurrently.
Initialize Torch intra/inter-op controls, threadpool limits, offline/cache environment and other
host globals once, not by competing loader/request threads. Retain provider-aware gradient
contexts: **do not blanket-wrap the host in torch.inference_mode()**, because HanLP's constituency
CRF deliberately enables gradients for its marginal calculation. Other providers retain their
appropriate inference contexts.

Thinc's current operations use ContextVar/thread-local state; establish the selected backend in
each spaCy execution thread. CuPy's current stream is per-thread/per-device and defaults to the
legacy null stream. A Torch stream context does not select a CuPy stream: enter an explicit
CuPy device/non-default stream as well. See [CuPy stream semantics](https://docs.cupy.dev/en/stable/user_guide/basic.html#current-stream).
Preserve detached CPU packet/reply boundaries; no cross-library GPU tensor-sharing layer is needed.

The bounded selected-source scan found GLiNER current-stream synchronization for grouped CPU
readback and provider-local host readbacks in D1/Maverick/DiPO/HanLP. Those dependencies remain;
they do not justify a device-wide synchronization or global inference gate. No explicit
inference-path torch.cuda.synchronize/empty_cache or forced default-stream override was found
within the inspected adapters and selected implementations. This is a bounded source observation,
not absence of synchronization inside native kernels or guaranteed kernel overlap. Complete replies
and release memory against stream-local events/completion, never by assuming submission means done.

### Multiplexed protocol, custody and failure boundary

Replace single-provider synchronous request/reply transport with bounded multiplexed host framing.
Each request and reply binds host generation, request ID, provider/profile identity and the exact
logical population; replies may arrive out of order. Preserve ordered native JSON bytes and
existing provider codecs; do not let canonical hashing reorder computational input. Serialize
only small transport writes/shared updates, not inference. Admit before serialization/submission;
executor futures do not create an unbounded queue behind bounded provider lanes. Parent claims,
renewal, DB work, validation, deterministic reduction and publication retain their existing owners.

One operation owns GPU/Nemotron custody across both admitted hosts. Reuse the existing
[pdf capacity owner](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py)
for exclusion against unrelated operations and service suspension/restoration, but replace the
per-resident exclusive acquisition that would make internal providers wait on one another.
Do not copy ambient ContextVar ownership into arbitrary threads. Host generations and explicit
operation ownership correlate participants. Hold custody until both hosts have drained or
terminated; a sent signal or cancelled future does not establish native exit.

A shared host enlarges the failure boundary. Bound startup, drain and termination; a wedged native
thread can require terminating that host and fencing its unfinished replies. Preserve already
collected useful results, actual failed/interrupted attempts and other-host completion rights.
There is no provider-local retry loop or new durable scheduler. This is the tradeoff against
separate per-provider processes, accepted to remove redundant runtimes and permit independent
streams; no measured throughput, simultaneous-kernel or RSS guarantee is claimed.

**Acceptance:** compatible locked hosts, actual selected device/dtype/backend, bounded multiplexed
work, independent different-model submission, narrow wrapper protections, stream-local completion,
renewal progress and custody restoration must be established through the coordinator's later
qualification. Historical CPU receipts do not qualify the new profiles. Maximum-admitted-state
checks resolve progress/lifetime concerns; a speedup benchmark is not an additional closure gate.

<a id="bep-08"></a>
## BEP-08 · Existing commands, status, cancellation and direct cutover

**Input:** BEP-07a's shared policy, BEP-05's usable coordinator/publication interface and BEP-00's
decision routes. **Output:** the existing characterization, ingest and analytical-demand paths
all use the same operation-owned execution implementation, with usable progress and retained-work
recovery. BEP-07b's final operating selection must be in place before assembled BEP-09 qualification.

### One source-operation request and resolved selection

**Proposed accepted target · 2026-11-12.** E04/E06/E12 share a consequential boundary defect:
CLI and direct callers interpret the same source operation separately, while graph injection
stands in for intent. In inspected [commands.py](../../../python/corpus-structure/src/corpus_structure/orchestrate/commands.py),
`ordinary_graph = graph is None and registry_for is None` controls automatic characterization.
The normal CLI explicitly injects those very defaults and bypasses it. Public preparation also
precedes pure argument checks; registration independently reloads the same release. Fix these
owners and consumers together rather than omitting CLI arguments or renaming the boolean.

Use an immutable `SourceRunRequest` below CLI with project/target selection, source selection,
freshness and an explicit workflow. Ordinary functions and closed typed variants are sufficient:

| Workflow / primary input | Meaning |
| --- | --- |
| Phase0Analysis / EnsurePrimary | Default capture → shared primary demand → exact-view binding → analytical consumers. |
| Phase0Analysis / RetainedViews | Consume exact selected enriched-view pins and original source custody; no replacement capture or fresh NLP. |
| Capture / optional CharacterizationOptions | Capture only, or capture followed by explicit shared enrichment, as selected by ingest. |
| M1Candidate | Exact retained integrated product, named supported M1 configuration and applicable record policy. Preserve source-only/default/described/readings/contextual semantics without incidental phase0 preparation. |
| ConfiguredGraph / DeclaredInputs or RetainedViews | Deliberately execute supplied graph/registry authority as configured, or bind explicit retained views. Graph/registry are separate implementation dependencies, never an intent test. |

Do not add speculative custom-graph production strategies or a universal operation framework.
Represent source selection as PackDefault, NamedSlice, NamedScope or WholeDocument, with separate
native/integrated product roles and direct/descendants membership. Registration's corpus directory
is distinct from the retired run corpus selector. Preserve that selector's refusal and mutually
exclusive scopes. Existing method/configuration owners still define semantic consumers and their
required primary families.

Construct/validate the request before opening an engine or acquiring preparation. One shared pure
boundary owns selector/product completeness, M1/record-policy applicability, retained-pin/freshness
constraints and other knowable incompatibilities; Typer parses transport and presents refusals.
Valid direct callers supply complete typed MethodSettings; repair stale valid None fixtures while
preserving deliberately invalid-engine/no-effects controls. Parsing a file remains the adapter's
responsibility, not a second interpretation of its content.

Resolve once into `ResolvedSourceRun`: exact project/release/input realization/domain, source
records, selected workflow, configs and provider profiles. Reuse `resolve_source_binding`,
`resolve_source_domain`, `slices.records` and existing custody readers as the owning algorithms.
Omitted domain resolves from the selected release; an explicit domain constrains resolution.
Operator overrides/omissions remain distinguishable from this resolved selection. Execution must
not apply pack defaults a second time or silently reinterpret retained inputs.

Keep resolved intent separate from `VerifiedExecutionPreparation`: the latter is an invocation-local
capability established by full release verification and owns CPU/provider lifetimes. It is not
serialized authority, and neither historical open_release nor registry hydration grants it. Use one
public source-operation composition with optional registration, the resolved request, complete
MethodSettings and callbacks. After pure preflight and release admission, share one preparation
through registration, capture, enrichment and analysis. Initialization creating the source
realization occurs before resolving that resulting input. Internal registration consumes this
verified capability, retaining construct_project and live native checks; standalone project init
still owns its own full verification. Preserve renewal, attempts, current native admission and
publication fences rather than substituting an old verification token for live authority.

One application factory resolves settings plus typed policy overrides and complete MethodSettings;
the CLI reads an optional policy file and reports errors. Device/dtype/provider/thread semantics
freeze under their provider owner before tasks; counts, queue/byte limits and stream placement do
not become semantic identity merely because they occur in the same settings object. Reports show
resolved values, not just the override fragment.

### Actual consumer cutover and deletion obligations

| Current consumer | Required integration |
| --- | --- |
| [Normal CLI run](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py) and direct start_bound_run | Construct the same explicit workflow request and call the shared application owner. Remove graph-is-None inference and duplicated CLI policy checks. Preserve deliberate custom graphs/registries and explicit retained views. |
| [Ingest](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py) | Optional corpus-directory registration, capture and optional enrichment share one preparation and result. Remove adapter calls to private _start_bound_run/_characterize_captured_run. |
| [Regenerate](../../../python/corpus-structure/src/corpus_structure/cli/regenerate.py) and [project init](../../../python/corpus-structure/src/corpus_structure/orchestrate/project.py) | Combined registration/execution shares one verified preparation; standalone registration verifies once. Preserve admission, retained original custody and explicit activation/result-selection effects. |
| Explicit demand, retained captured-run characterization and characterization resume | Keep CharacterizationDemandRequest and the native frozen envelope as their actual semantic starting states, sharing execution/policy/result ownership rather than rebuilding source selectors or freshness. |
| Supported low-level methods/custom primary graphs | Share provider admission/custody, including E14 frozen GLiNER threads/inter-op compatibility before queueing/startup. High-level preflight reuses that check for earlier refusal. |
| Retained composition, CLI/MCP/query/export/detached readers | Continue exact pinned reads without fresh NLP. inspect_enriched_document is a read-only inspection consumer, not an inference entry point. Preserve purpose/project/run/target fences. |

Return a typed `SourceOperationResult` containing the actual capture/analytical reports, native
characterization anchor(s), created run IDs and settled exact view pins. It is a derived projection;
the first actual stage's native demand anchor remains durable authority. Do not create a synthetic
control run or progress database. Remove superseded parallel argument signatures/locals forwarding,
adapter workflow loops and mechanism-specific dispatch assertions after actual consumers migrate.

### Explain work through current managed reporting

Extend [existing status/task operations](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py),
lines415–443/590–596, [status projection](../../../python/corpus-structure/src/corpus_structure/orchestrate/commands.py),
lines755–805, and
[observation logging](../../../python/corpus-structure/src/corpus_structure/cli/observation_logging.py).
Use existing invocation/run/task lineage and `on_created` correlation for the stage runs the
coordinator actually creates. Normal run, standalone characterize and recovery must acquire the
actual observation bindings and storage target consumed by result inspection, including an
all-settled recovery that creates no run. record_characterization_run currently copies child IDs
and envelopes without establishing that native join; correct the shared reporting owner. Surface
aggregate progress by unit/stage/provider and explain
prerequisite wait, capacity wait, active computation, reduction and publication. Keep source
capture readiness, family coverage and final-view readiness separate from physical activity.

Durable task outcomes remain authoritative. A transient lane state is a live observation, not a
new durable task status or a second progress database. Historical/last-observed diagnostics carry
observation time and known owner availability; do not
infer continuing activity from an old event or absent native state from missing journal events.
Build the bounded aggregate from authentic anchors, actual child/task lineage and published views,
verify the acquired storage target before native joins, and remain usable after managed expiry. Reports
identify the selected policy, relevant run/task IDs, settled regional views, final combined pin
when present, and failed/unavailable scope without per-token output or duplicated payloads.

### Cancellation and retained-work recovery

[ci run cancel RUN](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py),
lines318–330, keeps its stated run scope. Integrate that durable cancellation with the actual
coordinator/lane borrower so queued work is removed, stale responses cannot publish and useful
surviving members of a shared batch can settle. Cancellation of the enclosing managed operation
stops all of its owned admission, drains or terminates its children under BEP-03–05 rules and
restores device custody. Do not silently widen a single-run cancellation to unrelated runs or
claim that native work stopped merely because its future was cancelled.

[ci run resume RUN](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py),
lines333–355, currently routes through retained regeneration. Make the supported recovery route
explicit for the new multi-stage coordinator: reconstruct exact source/release/view selections
from retained lineage or the frozen demand and reuse compatible settled products through existing
task rules. Recreate only transient queues/workers. A cancelled/failed terminal attempt stays
terminal; recovery creates the required new attempt/run under existing rules rather than mutating
old evidence. An operation interruption must report enough original binding and created-run
correlation for the operator to invoke that route without reconstructing source selectors manually.
Resume may choose a different result-neutral capacity policy; an inference/profile change follows
its ordinary invalidation and attribution contract. Preserve uncertain-publication exact replay.

### Direct adoption and retirement

Cut the affected entry points directly to the shared coordinator after local integration works.
Remove the superseded sequential natural-unit driver, per-method serial coordination that the new
dispatcher replaces, ambient session/refusal ownership, redundant physical settings and tests that
assert those obsolete mechanics. Do not remove independent semantic, source-custody, deliberately
invalid-input or lifecycle controls. A one-slot policy is the same implementation with less
admission, not a permanent legacy execution branch. Preserve natural scope/recovery, full requested
families, old source/evidence/plan records and independently settled products. Reader/CLI/MCP/export
consumers continue to receive exact regional/final views. Retain necessary historical profile/receipt
decoding without adding a second current execution implementation or progress service.

**Acceptance:** explicit request, ingest enrichment and default analytical paths expose the same
resolved policy and coordinator behavior; capacity/prerequisite waits and out-of-order completion
are understandable through existing reports; cancellation reaches actual borrowers and restores
custody; retained recovery skips compatible settled work; source-only/retained composition performs
no inference; final views preserve exact selected closure. BEP-09 owns combined consumer/provider
qualification and protected-reference separation. No product/provider tests or operational changes
were performed while authoring this companion: **not_run**.

### Focused acceptance journeys after implementation

The decisive E12 check invokes the real Typer run callback through the actual application owner
and default graph/registry, comparing workflow and native custody with a direct typed request.
Do not mock the former public helper and call that CLI parity. Exercise explicit retained views
with no recognition/NLP, deliberate custom graphs unchanged in intent, and pure invalid requests
refusing before engine/preparation. Combined registration+capture/enrichment and registration+
analysis establish one full verification while each actual operation retains live admission.

Adapt existing test_m1_cli, test_whole_document, test_m1_review_repairs, test_execution_preparation,
test_characterization_recovery and acceptance/test_regeneration controls. Preserve independent
preflight/no-effects/native-outcome assertions while removing obsolete dispatch mechanics.
Standalone characterization and all-settled recovery must acquire usable result-inspection native
bindings; aggregate checks challenge partial families, settled partial views, missing/expired
journals and timestamped historical activity. Shared low-level GLiNER checks refuse mismatched
threads/inter-op before startup even outside the main demand. GPU host controls cover wrong
actual device/dtype/backend, capacity-one progress, different-model submission, narrow gates,
out-of-order replies, stream-local completion and bounded host failure/custody. Existing actual
primary-demand/two-language-region/native replay controls supply their scoped provider obligations
under the new profiles; empty/image-only controls do not establish provider passage.

## Execution handoff

Deliver BEP-07a early, then let BEP-02–06 and BEP-08 consume its real contract. BEP-07b needs the
integrated state/worker lifetimes to establish the selected two-host GPU design and compatibility;
that implementation cannot be deferred until after full-book qualification. BEP-08 can develop
reporting and entry point integration alongside those owners, but closes only after all affected paths adopt the
replacement. The [coordinator](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-07)
owns current package disposition; this companion owns the detailed policy/operational contract.
Follow [BEP-09](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-09) for actual
investigation records, final-policy qualification and evidence reassessment rather than creating
another results ledger here.

## Historical early admission and thread slice · 2026-11-11

The provisional second-increment CPU defaults admitted two regions, two CPU workers/submissions, two stage
runs and four logical claims, with a256MiB shared canonical-body budget,64MiB CPU packets and
8MiB replies. Provider lanes allow one active exchange and one pending batch per compatible
resident. Lazy production admission reserves before envelope serialization; physical occupancy
ends after drained collection, reply credit after reduction and draft credit after durable
settlement. Parent foreground DB work stays serialized while existing renewal owners progress.

PM2 children receive explicit four-thread OMP/MKL/PyTorch intra-op controls and one inter-op
thread; GLiNER retains its existing four-thread policy. These are finite integration defaults,
not a measured optimum or final BEP-07b count/device selection. The root's scoped receipt union
owns actual implementation checks. CUDA investigation, supported device decisions, final counts
and remaining operator policy/status surfaces stay with BEP-07b/08.


Operator steering2026-11-11 requires current D1 to run on CUDA/BF16 by default and without a CPU
fallback. This selected D1 device slice now joins the current increment; other07b device/count
work remains later. The inherited120s inference limit remains while actual D1 CUDA question/batch
and captured-prose qualification is performed. The CPU600s proposal is withdrawn. BEP-E02's
single disposition and exact evidence remain in the coordinator.


Final second-increment acceptance2026-11-11 is **scoped-qualified** in the coordinator:
236 functional/managed-admission controls,186 adjacent controls and4 actual native document-path
checks passed after final source freeze. The CUDA D1 ordered-question/cohort/source/custody panel
also passed. BEP-E02/E03 are closed there; BEP-E01 and other07b/08/09 scope remain open. The
coordinator owns exact commands, receipt IDs and source/context applicability.


## Current operating selection and completion boundary

**Proposed accepted target · 2026-11-12; implementation/qualification outstanding.**
[ADR-0088](../../adr/0088-gpu-default-native-hosts.md) and the coordinator own the approved GPU-default
replacement. The approved initial target admits four regions and four stage runs, eight claims,
four outstanding jobs per compatible provider, and two CPU parser workers/submissions. Retain
2GiB encoded owned state,256MiB CPU inputs/64MiB replies and8MiB native frames. These configurable
initial bounds replace the historical two-region/four-claim/two-job selection; they are not optimal
counts or residency guarantees. Shared hosts add bounded thread submission under the same combined
admission, not another unbounded executor. CPU native threads1 and compatible host provider
threads4/inter-op1 remain selected; host globals initialize once. GLiNER's frozen thread profile
must match before any supported low-level admission. D1 uses CUDA/BF16; HanLP/GLiNER/Maverick/DiPO
and spaCy learned inference use CUDA/FP32. Provider-specific instance/module gates and stream-local
completion permit different models to progress without an internal GPU-wide lock.

The first actual stage owns the native frozen demand; children refer to its anchor.
`ci run characterize --captured-run RUN --release RELEASE --realization INPUT` reuses exact
retained capture under a current admitted target. `ci run resume RUN --characterization`
reconstructs native authority, preserves original freshness and compatible settled products, and
permits capacity-only changes. New GPU/runtime/profile identities require ordinary invalidation
and qualification; old CPU receipts remain truthful CPU evidence. SourceRunRequest resolves intent,
SourceOperationResult reports actual native identities, and neither replaces the retained envelope.

The [coordinator audit](../book-processing-efficiency-and-parallelism_2026-11-11.md#completion-audit)
and its findings table remain the single disposition owner. E04/E06/E12 require the common-request
and once-per-operation consumer cutover; E13 requires aggregate/native inspection; E14 requires
shared low-level compatibility. E07/E08/E11 and E05 remain dependencies with their existing owners.
Accepted decisions do not close any of those findings. Compatibility metadata/source observations
are Interface-checked only; resolver/import/actual-device/native qualification is outstanding.

Implement and migrate the complete selected scope before the coordinator's final qualification
union. Preserve original failed/interrupted receipts, historical device/numerical policy, protected
reference separation and the E05 test-memory/custody prerequisite. Documentation authoring runs no
product/provider tests or book work: **not_run**. Later authorized native qualification and the
actual retained book/CLI/MCP/export/detached journeys follow BEP-09; this text establishes no pass,
book completion, speedup or per-process explanation of the earlier group-level OOM.
