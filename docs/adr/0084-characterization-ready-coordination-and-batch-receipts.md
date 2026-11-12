---
id: ADR-0084
title: Coordinate ready characterization work with exact versioned batch receipts
status: accepted
date: 2026-11-11
supersedes: []
superseded-by: null
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: Independent ready work, per-member cancellation or a historical/current receipt cannot retain exact source, inference identity and native settlement through these boundaries.
---

## Context

ADR-0083 establishes verified invocation preparation, bounded regional values and real CPU
computation. BEP-04–06 now needs incremental ready coordination, persistent admitted provider lanes
and compatible native batches. The current serial driver and ambient provider borrower refusal
cannot provide those capabilities; GLiNER whole-batch request hashes conflict with singleton-only
projector authentication. Source-review RC01–04 were explicitly accepted2026-11-11. The operator
authorized the concrete CPU scope below; CUDA and final operating counts remain later07b work.
The [scoped target review](../design_review/reviews/design_review_book-ready-coordination_2026-11-11.md)
accepts the Proposed design; the [BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
owns implementation, investigation and qualification. D3/D4/D6/D8 retain their respective
publication, semantic method, execution and caller/read responsibilities.

## Options

1. Keep the serial driver and singleton adapters. It is simple but fails the intended capability
   to progress independent regions/providers and underfills existing native batching.
2. Thread whole demands or duplicate model residents per task. This minimizes seam changes but
   entangles readers/builders/deadlines or multiplies model/native-thread state.
3. Use a bounded parent incremental coordinator, one resident per compatible provider/profile,
   private asynchronous CPU/inference results and versioned batch/member receipts (selected).
   This changes method seams and all affected authentication consumers, but preserves one
   semantic authority and existing native lifecycle with explicit physical ownership.
4. Add a broker, general DAG or batch ledger. Existing invocation state and task history suffice;
   a second durable scheduler/service adds recovery/identity machinery without a requirement.

## Decision

**Proposed accepted target.** The parent coordinator advances ready natural-region/stage work
incrementally using exact settled predecessor pins and completion-driven futures. It owns readers,
mutable builders, stable reductions, task registration, claims/renewal and native settlement.
Keep actual stage-run boundaries and current cross-run restrictions. Register dependent tasks only
after their immutable input identity exists. No placeholder products or general cross-run DAG.

Methods expose one incremental parent-owned plan generator yielding lazy PreparedWork and
receiving private replies. PreparedWork.try_submit is a parent admission callback returning a
WorkHandleProtocol with future/collect/cancel/retire. The synchronous driver consumes the same
plan. Physical slots release after terminal/drained future collection, not whole-method settlement;
reply credit persists through reduction and draft credit transfers to the parent claim/region
through settlement/retirement. This permits later D1 questions without holding all intermediate
slots. Drain completions/reductions before waiting for capacity for new work.

The early CPU operating slice admits two natural regions, two CPU workers in one spawn
ProcessPoolExecutor, two stage runs and four logical claims, one foreground DB operation and
independently owned renewal/bounded dedicated supervisors. Retain256MiB encoded-state,64MiB CPU
input and8MiB CPU result bounds. Provider/profile lanes own one compatible resident, one live
exchange and at most one pending native batch. PM2 CPU children explicitly apply four native/
intra-op threads and one inter-op thread before native work. GLiNER retains supported profile
controls. These values are initial delivery settings, not optimal counts, RSS bounds or CUDA
qualification. Capacity-one uses the same implementation. Admission/reservations precede hydration
and queueing; replies retain capacity through consumption and reduction.

CPU requests use fixed shared cancellation slots and generations, cooperative checks and existing
parser deadlines. Retain physical occupancy until an old future is terminal or successfully
cancelled before execution; cancelled logical claims cannot create an unbounded physical queue.
Generation mismatch makes stale output unusable. Ordinary per-request cancellation preserves the
useful sibling's pool. Terminate the whole pool only for invocation stop or broken-pool recovery.

Provider/profile compatibility includes frozen runtime/artifacts/device/options. One sender/
receiver owner routes each native exchange. Capacity waiting backpressures rather than becoming
provider failure. One stale member loses completion rights while useful batch siblings continue;
a physical exchange stops when all borrowers lose usefulness or the invocation stops. Never reuse
an ordinal for another request. All teardown owners run, preserving existing custody and retry/
uncertain-settlement authority. Provider callbacks cannot mutate regional builders.

Preserve native spaCy prepared-Doc pipe batching and detach positioned annotations before crossing
compute boundaries. Preserve D1 native length packing and per-question prerequisites. HanLP bulk
admission uses actual native lengths; its mandatory investigation chooses supported prepared-sample
reuse or explicitly retains native inference preparation. Independent Maverick/DiPO lanes need no
unproven multi-document API to overlap.

GLiNER v2 uses one compact normalized header, ordered exact member-request digests and member
ordinal. Batch identity commits to header/population/order. Observation identity binds batch,
ordinal, own member digest, raw output and effective profile. Shared validation serves admission,
cue/classification projection, PM2 reconstruction and retained/detached replay. Whole-batch checks
use actual admitted requests; later member checks reconstruct that member's exact source/context
and validate its commitment. Other-member hashes are not claimed as reconstructed source. Full
cohort reconstruction, when claimed, needs exact source/context references and exported closure,
not repeated complete texts in each annotation.

Use explicit request/observation format tags, released model-observation policy and affected
producer/operation versions for changed semantics. SourceValue can carry the compact native receipt;
it does not convert a request-meaning change into runtime-only provenance. Current producers emit
v2. Historical v1 products keep read-only authentication under their original recorded contracts;
no rewritten hashes, invented membership or installed-current-policy reinterpretation. All
source-prefix/suffix, literal-coordinate, requested/effective profile/runtime/device checks remain.

Actual selected CPU batch qualification precedes cross-region task formation. If grouping affects
meaning or remains materially uncertain, form stable compatible cohorts from actual ready inputs
and predecessor pins and bind their identity before registration/reuse selection. Never change a
claimed task. If that cannot preserve the lifecycle yet, keep the provider scalar and its batching
obligation open. Qualified member-level equivalence must state its scope; actual batch provenance
remains retained. CUDA/device-specific batches require their own later qualification.

## Consequences

Independent useful work can progress without a second scheduler, reader/claim authority or model
replica fleet. Cancellation and provenance become per-request/member without weakening native
fences. Method preparation/inference/reduction, all GLiNER consumers and public/book/ingest callers
must migrate coherently; obsolete serial/ambient production paths are removed. Historical read-only
receipt handling serves a real durable-data obligation and is not another inference backend.

No source/family/context truncation, changed knowledge standing, arbitrary upload, protected-reference
input, full-book restart or publication-limit repair is authorized here. The known run610 native
layer-size failure remains separate. Actual I1–I4 provider decisions, working integration,
assembled review and qualification remain open under BEP. Acceptance records the target and its
rationale, not implementation, native provider passage or a measured speedup.
