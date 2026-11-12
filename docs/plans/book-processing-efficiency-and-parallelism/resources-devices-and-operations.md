# Resources, devices and operator workflows

**Status: Required BEP-07a and selected D1 CUDA slice scoped-qualified; other07b/08 remain planned · 2026-11-11.** This companion owns BEP-07 and BEP-08 in the
[book-processing series](../book-processing-efficiency-and-parallelism_2026-11-11.md).
Planning baseline is `f81a380cd`; inspected production source is `4d0ca7eb7`. The source
[functional review](../../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md#O06)
supplies O06, and [O08](../../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md#O08)
supplies the operational scope. RC01–RC04 were explicitly accepted by the operator on
2026-11-11; the coordinator owns their decision routes and current series disposition.
Neither that acceptance nor this document establishes implementation or qualification.

The intended result is one usable local execution policy: independent book work can progress
without multiplying native thread pools, model fleets, outstanding payloads or database
borrowers without a bound. The operator selects and inspects that policy through existing
operations, can explain a wait, and can cancel or resume retained work without managing workers.
The running book and the TC plans remain untouched by plan authoring. Protected reference sets,
source-first exposure boundaries and independent assessment remain under their existing owners.

## Baseline and responsibility boundaries

The hybrid target separates durable ownership from physical placement. BEP-03 owns process-main-thread
CPU kernels; BEP-04 owns resident provider lanes; BEP-05 owns dependency-ready coordination and
publication; BEP-06 owns native batch authentication and deterministic item projection. Those
packages consume the early BEP-07a contract below. BEP-07b subsequently selects concrete counts and
the supported device profile from the integrated implementation, before BEP-09 full qualification.
BEP-08 migrates all existing entry points and operator-facing reports to that same ownership.

The source-established constraints are:

| Existing owner | Consequence for this work |
| --- | --- |
| [Resources and MethodSettings](../../../python/corpus-structure/src/corpus_structure/core/method.py), lines806–831 | `Resources.max_concurrency` is a declaration, not the current scheduler's implemented dispatch policy. `MethodSettings` currently holds result-neutral paths/endpoints; do not hide an inference-changing choice in it merely because it is operational. |
| [Resource session](../../../python/corpus-structure/src/corpus_structure/methods/characterization_resources.py), lines66–94/175–225/244–259 | Current CPU residency is one provider slot with ContextVar/nonblocking borrower ownership. The replacement gives each resident an explicit operation/lane owner; a queue must not repeatedly trigger the old saturation refusal. |
| [PM2 launch](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py), lines378–465 | The child receives a constructed environment, explicit device and bounded IPC. Parent-only OMP settings do not reach this child automatically. CUDA startup and teardown already hold device/Nemotron custody. |
| [GLiNER worker](../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py), lines98–102/272–283/350–383; [model load](../../../python/corpus-structure/src/corpus_structure/methods/gliner.py), lines502–511 | GLiNER already uses spawn, profile-sized immutable batches, OMP/MKL limits and PyTorch intra/inter-op controls. Preserve those bounds and qualify the batch contract through BEP-06. |
| [Database settings](../../../python/corpus-structure/src/corpus_structure/settings.py), lines40–66; [store](../../../python/corpus-structure/src/corpus_structure/core/db/store.py), lines124–157 | The default ordinary pool has maximum4 connections and4 waiters. CPU/native computation must not create a pool per worker. Pool/admission selection must preserve renewal progress. |
| [Supervisor connection](../../../python/corpus-structure/src/corpus_structure/orchestrate/liveness.py), lines14–85 | Each active run supervisor holds a dedicated physical connection outside the ordinary writer pool. Counting only pool borrowers misses real connection state. |
| [Claim lifetime](../../../python/corpus-structure/src/corpus_structure/semantic/claim_lifetime.py), lines58–109/160–281 | Renewal and exact completion/replay already have owners. More physical concurrency must not starve them or install another retry policy. |

The review observed16 physical/32 logical CPUs, approximately188GiB visible RAM, an RTX5090 with
approximately32GiB device memory, and native multicore provider activity. These are dated
2026-11-11 observations, not a selected worker count, reserved capacity or acceleration result.
The root interpreter is CPython3.14.10 with the GIL enabled; provider services retain their own
locked interpreter boundaries. Native intra-operation parallelism exists even when outer
orchestration is serial.

<a id="bep-07a"></a>
## BEP-07a · Shared physical policy and admission contract

**Input:** BEP-00's accepted ownership/rule treatment and the hybrid responsibilities above.
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
## BEP-07b · Coordinated counts and mandatory device investigation

**Input:** BEP-07a plus working BEP-02–05 and the delivered/qualified CPU batch slice of BEP-06.
**Output:** a selected supported operating policy with reasoned concrete counts, scoped native-thread
coverage and an explicit CUDA qualification/adoption decision. BEP-09 consumes that final policy
for full qualification; an arbitrary32-worker default cannot substitute for this package.

The prerequisite order is CPU batch delivery/qualification, then BEP-07b device selection and
scoped device/runtime qualification, then BEP-06 qualification of batches for each newly selected
device. BEP-09 consumes the combined final evidence. This package does not require all
device-specific BEP-06 work to finish before selecting its device arrangements.

### Native threads, state and connection progress

Inspect actual selected child runtimes before fixing counts. PM2 currently disables HF tokenizer
parallelism but leaves corresponding OMP/MKL/PyTorch limits unspecified in its launch/profile path.
Apply supported controls inside each child before native work, and retain GLiNER's existing
profile treatment. Use
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

### CUDA is investigated, then explicitly selected or declined

The CUDA investigation is mandatory even if CPU remains the eventual supported selection. Its
question is which selected provider/profile can use the RTX5090 coherently, not whether all
providers must move to GPU. Inspect the locked service interpreter/wheels, actual device support,
required precision, model loading and exact output attribution before executing a bounded real
provider case. The existing d1 loader explicitly chooses CPUfloat32/CUDAbfloat16 and checks BF16
support in [pm2_native.py](../../../python/corpus-structure/src/corpus_structure/methods/pm2_native.py),
lines70–88; CUDA is therefore not assumed to be an invisible physical substitution. BEP-06 and
BEP-09 define the applicable semantic/numerical comparison and native-member qualification.

Device custody covers the **whole owned native lifetime**, from capacity acquisition through
startup, all admitted requests and final child teardown. Reuse the existing
[pdf_gpu_slot and suspend_resident_nemotron](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py),
lines21–46/129–159, and
[native_before_nemotron](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py),
lines49–126. They serialize participating local work across processes, authenticate the dedicated
local endpoint, sleep the configured resident service when needed and restore it on success,
failure or cancellation. Preserve PM2 process-group kill/join before releasing custody; a signal
sent is not confirmation that device users have exited.

RC02 permits replacing ambient ContextVar borrower ownership; it does not authorize bypassing the
cross-process device exclusion or repeatedly sleeping/waking Nemotron around each scalar request.
A single operation owner must hold and release custody on the correct execution context. Do not
send that ownership implicitly through arbitrary thread ContextVar copying. Initial CUDA support
may serialize GPU residents or explicitly replace one resident while CPU lanes continue. Concurrent
GPU residency is conditional on established combined memory, ownership and failure behavior; it is
not obtained by starting several existing exclusive contexts that wait on one another.

Investigate these outcomes and carry their consequences into the owning packages:

| Outcome | Required disposition and dependency |
| --- | --- |
| Suitable provider/profile qualified on CUDA | Select its explicit runtime/device/precision identity and supported residency arrangement; BEP-04 implements its ownership and BEP-06 qualifies applicable batching. BEP-09 includes it in the actual-provider union. |
| Technically compatible but a poor fit for the combined operation | Retain CPU for that provider, record the concrete residency/coexistence or fidelity tradeoff and revisit trigger; do not leave GPU adoption ambiguously pending. |
| Incompatible wheel/interpreter/device/profile or missing prerequisite | Name the blocker, supported CPU selection and affected qualification obligation. Resolve it before claiming the selected CUDA profile supported, or explicitly decline that profile with reason. An unperformed required investigation remains open. |

No inference error silently falls back to another device, precision or provider. Missing GPU
prerequisites do not erase useful CPU results or turn unavailable coverage into successful empty
output. The investigation may conclude that no CUDA profile is worth adopting; successful package
closure requires that explicit assessed decision, not GPU adoption by quota. Retain accepted probe
records under the existing evidence route when a probe is needed; BEP-09 owns the assembled
investigation/qualification account. Never inspect protected reference answers to tune scheduling,
thread counts, device selection or prompts.

**Acceptance:** the selected policy has concrete coordinated values; native thread-control coverage
and limits are explicit; maximum admitted state leaves renewal/completion progress; device custody
restores the dedicated service after success, error and cancellation; every selected profile has
its scoped actual-provider evidence or remains openly blocked. Numerical speedup is not a closure
condition. A changed final policy after qualification requires reassessing affected evidence.

<a id="bep-08"></a>
## BEP-08 · Existing commands, status, cancellation and direct cutover

**Input:** BEP-07a's shared policy, BEP-05's usable coordinator/publication interface and BEP-00's
decision routes. **Output:** the existing characterization, ingest and analytical-demand paths
all use the same operation-owned execution implementation, with usable progress and retained-work
recovery. BEP-07b's final operating selection must be in place before assembled BEP-09 qualification.

### Entry points and policy selection

Migrate these real consumers together; the examples describe existing routes, not final new flag
spellings that must be copied into every request format:

| Consumer | Required integration |
| --- | --- |
| [ci run characterize --request FILE](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py), lines599–632 | Keep typed `CharacterizationDemandRequest` and exact completed-source/layer pins. Select the shared physical policy at the operation boundary, validate it before admission, and report resolved values through the managed result. |
| [Ingest enrichment](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py), lines461–544 | Existing `--enrichment-options` retains semantic method choices. Ingest completes capture before the shared demand coordinator runs; selecting parallelism does not repeat PDF recognition. |
| [Default analytical demand](../../../python/corpus-structure/src/corpus_structure/orchestrate/commands.py), lines335–400 | Preserve capture → primary demand → exact-view binding, selected custom registry, freshness and consumer configuration authority. Supply the same physical policy through this path instead of recreating a serial loop. |
| Retained composition and explicit views | Preserve `run_missing=False`, source-only operation and exact selected active/closure pins. No inference lane starts for pure retained composition or a reader query. |

Use one validated settings/policy route and one resolved report representation. CLI overrides,
where useful, resolve through it rather than independently patching provider profiles. The
semantic demand remains portable independently of workstation capacity. Device/inference choices
retain their identity treatment from BEP-07a; recorded physical policy does not relabel archived
producer provenance. Reject unsupported combinations before starting workers where their
incompatibility is knowable; later genuine failures retain their actual outcomes.

### Explain work through current managed reporting

Extend [existing status/task operations](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py),
lines415–443/590–596, [status projection](../../../python/corpus-structure/src/corpus_structure/orchestrate/commands.py),
lines755–805, and
[observation logging](../../../python/corpus-structure/src/corpus_structure/cli/observation_logging.py).
Use existing invocation/run/task lineage and `on_created` correlation for the stage runs the
coordinator actually creates. Surface aggregate progress by unit/stage/provider and explain
prerequisite wait, capacity wait, active computation, reduction and publication. Keep source
capture readiness, family coverage and final-view readiness separate from physical activity.

Durable task outcomes remain authoritative. A transient lane state is a live observation, not a
new durable task status or a second progress database. Historical/last-observed diagnostics must
say when their live owner is gone; do not infer continuing activity from an old event. Reports
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
consumers continue to receive exact regional/final views; no compatibility decoder or progress
service is introduced merely for the transition.

**Acceptance:** explicit request, ingest enrichment and default analytical paths expose the same
resolved policy and coordinator behavior; capacity/prerequisite waits and out-of-order completion
are understandable through existing reports; cancellation reaches actual borrowers and restores
custody; retained recovery skips compatible settled work; source-only/retained composition performs
no inference; final views preserve exact selected closure. BEP-09 owns combined consumer/provider
qualification and protected-reference separation. No product/provider tests or operational changes
were performed while authoring this companion: **not_run**.

## Execution handoff

Deliver BEP-07a early, then let BEP-02–06 and BEP-08 consume its real contract. BEP-07b needs the
integrated state/worker lifetimes to choose counts and decide device support; its assessment
cannot be deferred until after full-book qualification. BEP-08 can develop reporting and entry
point integration alongside those owners, but closes only after all affected paths adopt the
replacement. The [coordinator](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-07)
owns current package disposition; this companion owns the detailed policy/operational contract.
Follow [BEP-09](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-09) for actual
investigation records, final-policy qualification and evidence reassessment rather than creating
another results ledger here.

## Delivered early admission and thread slice

The current integrated CPU defaults admit two regions, two CPU workers/submissions, two stage
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
