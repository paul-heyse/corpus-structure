---
id: ADR-0083
title: Characterization execution owns verified preparation and bounded workers
status: accepted
date: 2026-11-11
supersedes: []
superseded-by: null
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: A supported kernel cannot preserve exact source, bounded state, main-thread deadlines or native completion ownership through this execution boundary.
---

## Context

The full retained book executes primary characterization across316 natural SourceViews and518
pages. Full load_release verification currently repeats for each regional demand and final
composition; dependency reconstruction repeats across stage readers. Current provider sessions
use ambient exclusive borrower refusal, and parser-bearing work has main-thread deadline
constraints. These physical choices obstruct independent progress without supplying new source
or semantic authority. The operator explicitly accepted source-review RC01–04 on2026-11-11 and
authorized BEP-00–03 plus the required early07a slice. D3 owns storage/admission, D4 method seams,
D6 invocation/lifecycle and D8 caller/read boundaries. [Target review](../design_review/reviews/design_review_book-execution-foundations_2026-11-11.md)
accepts the bounded Proposed design; the [BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
owns implementation and qualification.

## Options

1. Retain sequential demands and repeated verification. This has least migration burden but
   repeats stable preparation and leaves primary CPU work constrained by the current driver.
2. Wrap entire demands in threads or globally cache prepared objects. This reduces call-site
   changes but entangles connection ownership, main-thread deadlines, ambient borrowers and
   preparation/admission validity. A cache hit alone is not current authorization.
3. Own verified structural preparation and bounded regional state per invocation, move pure
   kernels into warm spawned workers and retain durable effects in the parent (selected).
   Explicit byte packets add serialization but isolate real resource/semantic boundaries and
   allow later ready scheduling without another kernel implementation.
4. Adopt a general durable DAG/distributed runtime now. No cross-run or multi-host requirement
   justifies a second scheduler; existing task/claim/native publication remains sufficient.

## Decision

**Proposed accepted target.** One invocation owns verified preparation, regional lifetimes,
physical admission and worker/provider scopes. Independent units and inference branches may
advance when real dependencies permit; stage-wide terminal barriers are not semantic prerequisites.
The existing parent coordinator retains durable claims, renewal, completion preparation,
settlement and coherent publication. Private workers own no database effects or task lifecycle.

Full verification creates an internal context whose exact release/compiler/runtime validity is
carried through internal execution. Historical archive hydration and arbitrary prepared objects do
not confer that status. Current DB admission, permissions, source authorization and attempt fences
remain live. Each artifact reuses only inputs affecting it; source text and unrelated placement
settings do not force structural release recompilation. Workers hydrate local usable preparation
from authenticated immutable capsules and matching runtime inputs; no live PreparedRelease,
reader, callback or connection crosses processes.

A bounded regional owner supplies exact source/projection/recipe/native values, immutable layer
views/indexes and established validation under original release/source/closure premises.
Public LayerReport.payload remains fresh. New or untrusted results validate before publication;
a digest is not proof. Large bodies leave after their last consumer, while compact pins remain
for final composition.

CPU execution uses Python3.14 ProcessPoolExecutor, explicit spawn context, initializer and finite
submission. Formal/construction/contextual-evaluation kernels execute on process main threads,
with exact immutable input/result envelopes. Parent adapters initially await real futures under
claim checks; later ready dispatch reuses that seam. Operation-owned cancellation stops admission,
cooperatively signals kernels, discards late results and drains under deadlines with pool-wide
termination fallback. Future cancellation alone does not stop an executing kernel.

One shared physical policy bounds regional bodies, queued packets and completed replies until
consumed. Capacity-one uses this same implementation. Final counts/devices belong to BEP-07b.
Provider residency becomes explicit operation/lane admission rather than ambient refusal in
BEP-04; one compatible resident per profile is the starting topology. BEP-06 owns native batch
member authentication and deterministic projection. Result-affecting device/precision/batch
semantics keep their appropriate provenance; physical concurrency does not select fewer families
or smaller semantic contexts.

## Consequences

Preparation and physical placement can change without duplicating language meaning or completion
authority. Ingest, standalone demands and books share one execution route. Packets, validity,
bounded state and stop/drain become explicit implementation obligations. Source-specialized grammar
preparation remains per input; no generic parser may erase protected lexical/source conditions.
No global verification cache, shared connection-bound reader, inline legacy backend or universal
resource estimator is selected.

This accepts no weakened source/choice/coverage contract, cross-run DAG change, arbitrary layer
upload or knowledge admission. The run610 native layer-size failure is preserved separately;
worker transport limits neither change nor repair the8MiB publication contract. Implementation,
actual-provider checks, independent semantic assessment and whole-book qualification remain open
under their respective owners. No measured performance improvement follows from this decision.
