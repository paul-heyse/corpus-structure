# Coordinator and provider lanes

**Captured-region and ordinary completion-driven frontiers are implemented at scoped evidence; shared GPU host cutover integrated; assembled qualification remains open (checkpoint2026-11-12).** Owns BEP-04/05. [Coordinator](../book-processing-efficiency-and-parallelism_2026-11-11.md) owns scope and O03/O04/O07 disposition.

## Operator closeout checkpoint · 2026-11-12

The [coordinator checkpoint](../book-processing-efficiency-and-parallelism_2026-11-11.md#audit-repair-execution)
owns integrated delivery, scoped evidence and remaining execution. GPU-default production cutover and audit functional repairs are integrated;
combined final qualification and full-book acceptance remain open. Historical receipts retain their
original source/context. The coordinator owns the current evidence and remaining qualification.

## Current approved execution boundary · 2026-11-12

**Implemented; focused controls Tested2026-11-12; combined qualification open.** The
[coordinator's approved closure](../book-processing-efficiency-and-parallelism_2026-11-11.md#approved-audit-closure-and-gpu-pivot)
and [ADR-0091](../../adr/0091-gpu-native-environment-boundaries.md) govern the GPU-default pivot, shared
runtime hosts, explicit workflow intent and changed initial counts. D1 remains CUDA/BF16; other
selected learned NLP targets CUDA/FP32. This supersedes CPU-hybrid/default-device and per-provider
exclusive GPU-custody assumptions in the original design below. CPU parser deadlines/spawn remain;
spaCy learned annotation moves to GPU with tokenizer-only preparation staying CPU. GPU phase
custody begins after capture. Historical scoped receipts retain their dates/source/profile limits.

BEP-E04/E06–14 retain qualification/cutover obligations; implemented/scoped-tested repairs are distinguished in the coordinator. Bounded qualification is authorized after implementation and custody
readiness; the full book, book interruption/resume and full-book consumers remain deferred.
E05 does not authorize speculative memory diagnosis. This companion is not a second status ledger.

## Shared execution contract and BEP-00 foundation work

Before dependent implementation, record acceptedRC01–04 through the ADR route and amend the owning architecture as accepted target. The binding's applicable target review occurs before substantial boundary implementation and again at assembled scope; focused authoring advice is not a full-system qualification.

Settle operation-owned preparation, CPU input/result, provider request/member and completion ownership contracts. Conceptual names need not create a service or durable record each. A physical request carries sufficient exact run/task/attempt/holder, source, method/profile/runtime and predecessor identities to reject stale or misrouted completion. Exchanged kernels contain no live readers, connections or mutable builders.

The coordinator is the sole owner of durable claims, renewal, completion preparation/application and publication. Worker/provider work remains private. Existing semantic operation definitions retain authority over language meaning; placement is separately configurable. BEP-07a supplies policy/admission semantics early, avoiding a dependency cycle with later resource qualification.

## BEP-04 · Persistent admitted provider lanes

Input: working prepared state and finite admission policy. Output: provider/profile-compatible resident children serving owned requests, with explicit pending/active/completed/closed state and scoped teardown. Begin with one resident per provider/profile; keep the current one-live-IPC-exchange guarantee inside each child.

Replace the ContextVar exclusive-borrower/refusal coordination with an explicit invocation-owned lane owner. Queue waiting is normal capacity state, not provider failure. A full queue backpressures upstream admission. Validate profile/runtime/artifact compatibility before borrowing; replace a resident only after its owned work drains or is cancelled. Model state does not move with each region.

Native IPC work may be driven by small I/O threads; parser-bearing work stays in BEP-03 process main threads. Each lane has one sender/receiver owner so responses cannot cross borrowers. [pm2_worker.py](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py) owns actual process groups/framing; [characterization_resources.py](../../../python/corpus-structure/src/corpus_structure/methods/characterization_resources.py) is the replaced lifetime implementation.

Separate private inference from regional builder mutation. Maverick/DiPO and D1/GLiNER branches may overlap once their inputs are ready; apply their returned results in declared provider/scope/question order. D1 candidate populations and question depends_on barriers remain true dependencies. A branch failure preserves independently valid siblings and explicit family outcomes.

Acceptance: compatible reuse, incompatible profile replacement, backpressure, response routing, branch-order permutations, teardown failure and independent provider crash. Retire old ambient borrower paths with affected callers; avoid a compatibility fallback that preserves a second authority.

## BEP-05 · Ready frontier and fenced completion

Input: working CPU kernels, provider lanes and early capacity contract. Output: bounded independent regional progress through the existing semantic dependencies, with exact task/run history and a single final composed view.

Replace the sequential regional comprehension and synchronous claim/execute barriers in [characterization orchestration](../../../python/corpus-structure/src/corpus_structure/orchestrate/characterization.py) and [source execution](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py). Preserve ordinary standalone source execution through shared owned primitives rather than forking a book-only scheduler with duplicate semantics.

Keep actual stage-run boundaries initially. A coordinator registers dependent tasks only after exact immutable predecessor pins exist and determine their configuration/input identity. Current same-run dependency admission does not implement a general cross-run DAG; no placeholder products or new durable queue are selected.

Use submit plus wait(FIRST_COMPLETED) or as_completed for completion-driven progress, with a bounded submission window. Avoid ordered result consumption as a barrier for unrelated units. The [Python3.14 futures contract](https://docs.python.org/3.14/library/concurrent.futures.html) supplies completion coordination; it supplies neither byte admission nor project publication semantics.

Admit only a finite ready set; claim work near actual execution rather than leasing the remaining book. Count inputs, queued requests, active kernels, replies awaiting reduction and pending completion together. Preserve fairness for large/slow regions without sacrificing source context or splitting sentences to fit a queue.

Retain existing claim renewal and PreparedUnitCompletion preparation/application. Independent source/project authorization and native source/role/choice/payload checks remain. Publication stays outside inference and commits atomically under run/task/attempt/holder fences. Reserve connection availability for renewal; bound simultaneously active supervisors as well as ordinary pool borrowers.

A shared batch can have several logical borrowers. Cancellation/stale-claim handling discards only the affected member while useful survivors continue; stop the physical exchange when no live borrower remains or the invocation is cancelled. BEP-06 supplies exact member attribution. Global cancellation stops admission, drains/cancels owned CPU/lane work, attempts every closer and retains settled products. Existing outcome/retry policy remains the sole retry owner.

Compose after the declared regional outcomes settle, using manifests and exact selected closure in original source order. Partial/unavailable family state remains explicit. Already settled regional views remain readable even if another unit fails. Capacity-one execution uses this same coordinator, enabling controlled verification without retaining the superseded implementation.

Acceptance includes independent-unit overlap, simultaneous native/formal readiness, slow early region with later completion, stale writer refusal, renewal under read/publication contention, uncertain completion replay and final view fidelity. Conditional run/projection restructuring remains BEP-I11, not a prerequisite.

## Delivered second increment

ADR-0084 records the accepted realization. `core/work.py` supplies PreparedWork/ReadyGroup and
one parent driver for standalone and captured-document execution. `orchestrate/ready.py` owns
invocation-local stage/claim admission; existing native task ownership remains authoritative.
The regional loop and ordinary source methods share private CPU/provider work primitives.
Captured regions and independent provider branches progress while builders reduce in stable
order. Ordinary multi-unit source execution still uses fixed claim groups, so completion-driven
replenishment remains E09. All registration/publication stay in the parent; capacity-one uses
the same implementation.

ProviderExecution owns persistent lane threads, resident compatibility, one active exchange and
one pending compatible batch. Production lazy intents reserve lane and maximum request/reply
credit before serialization, then shrink to actual bytes. Saturation waits without materializing
an uncharged request. Submission, cancellation, collection, reduction and teardown have explicit
ownership. Invocation teardown attempts every closer and preserves cleanup errors.

The [assembled review](../../design_review/reviews/design_review_book-ready-coordination_2026-11-11.md#assembled-ready-execution-assessment--2026-11-11)
accepts this scope at Interface-checked strength. The coordinator owns actual functional/native
receipts and final applicability; neither this delivery nor its review closes full-book BEP-09,
final operating counts/CUDA or the existing oversized-layer finding BEP-E01.


Historical second-increment acceptance2026-11-11 was **scoped-qualified** at its recorded source
in the coordinator. It does not close the later completion-audit obligations:
236 functional/managed-admission controls,186 adjacent controls and4 actual native document-path
checks passed after final source freeze. The CUDA D1 ordered-question/cohort/source/custody panel
also passed. BEP-E02/E03 are closed there; BEP-E01 and other07b/08/09 scope remain open. The
coordinator owns exact commands, receipt IDs and source/context applicability.


## Completion audit boundary · 2026-11-12

The [coordinator audit](../book-processing-efficiency-and-parallelism_2026-11-11.md#completion-audit)
found no additional local delivery gap in the selected resident-lane/private-branch implementation.
BEP-05 remains incomplete for ordinary same-method multi-unit progress and claim replenishment
(BEP-E09). It also depends on shared read admission and bounded CPU teardown (E07/E08).
Existing claim/renewal/publication fences and historical component evidence remain; maximum-state,
interrupted-book and enclosing qualification are still open. The coordinator owns current status;
this audit ran no tests or providers.
