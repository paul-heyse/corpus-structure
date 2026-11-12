---
id: ADR-0089
title: Isolate native source-plan logging context while retaining committed creation notifications
status: accepted
date: 2026-11-12
supersedes: [ADR-0080]
superseded-by: null
design: [§2]
evidence: Proposed
revisit: A supported source consumer requires a separately acquired execution handle or observation context must cross an independently owned native worker boundary.
---

## Context

BEP audit closure's native regression checks preserve CLD-CA03's committed-run, failure,
interruption, diagnostic isolation and context-restoration assertions. They exposed missing
ambient source identity during graph selection, and characterization creation callbacks missing
managed/native observation bindings. The source operation now creates several actual runs and
interleaves independent plans. One CLI ExitStack retaining a changing run context across that
whole operation cannot correctly attribute each suspended/resumed plan.

[The BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md#approved-audit-closure-and-gpu-pivot)
owns current implementation/qualification. Earlier CLD receipts retain their original dated
source boundary, not qualification of this interleaved replacement. ADR-0079's safe observation
custody and ADR-0088's native effect/host-generation boundaries remain unchanged.

## Options

1. Drop ambient context assertions and report only manifest bindings. This loses anonymous log
   attribution promised by the accepted source lifecycle; changing a test would hide missing behavior.
2. Retain CLI-global run bindings. This preserves a single linear call but leaks or misattributes
   identity when another plan advances, and resets ContextVar tokens in a different context.
3. Give each prepared-work node its own copied context and bind native run identity in the source
   plan (selected). This localizes suspension/resumption/cleanup context alongside actual plan
   ownership and preserves useful library logging without a new scheduler or observation store.
4. Wrap source generators in another context proxy. That duplicates driver lifecycle and misses
   submission, collection, cancellation and cleanup callbacks unless recreated comprehensively.

## Decision

**Proposed accepted target · 2026-11-12; qualification remains open.** Preserve the immutable
SourceRunCreated notification containing actual native run/project/release identity. Each native
run notifies at most once after successful commit and supervisor adoption, within native cleanup
ownership and before graph selection/work. A composed application can notify for several actual
runs; no invented control run or effect permission follows from observing one.

The prepared-work driver owns a copied Context for each node. Run generator advancement, throwing,
submission, collection, retirement, flush and close under that node's context. Child nodes inherit
the parent's current context. Unwinding a child restores its parent; final unwind restores caller
context. Do not enter an already-entered Context recursively. This is an invocation-local execution
property, not another persisted observation identity or scheduling system.

The source plan establishes run/project/release logging scope after committed adoption and before
notification/graph/work. Its finally/reset executes in that same plan context. The CLI owns managed
association publication beside acquired storage and optional diagnostic isolation, not ambient
source context across interleaved plans. Characterization notifications also establish the actual
managed/native binding; successful anchor/stage metadata alone cannot replace that join.

Ordinary diagnostic binding/publication failures remain optional and must not replace native
success, failure or cancellation. Cancellation reaches native cleanup. Native execution does not
swallow arbitrary caller callback bugs, transfer resource ownership, infer identity from logs or
delegate settlement. Native commit and managed publication remain non-atomic across stores.
Child worker requests still carry explicit native identities; context copying grants no device,
database or publication authority and is not a substitute for detached worker envelopes.

## Consequences

This supersedes only ADR-0080's placement of source logging scope in the CLI ExitStack; its frozen
notification timing, existing resource owner, independent diagnostic/native outcomes and explicit
custody guarantees survive here. FP-01/04/05 and H19/H22/H25 favor carrying the correct current
identity through the existing complete execution lifecycle instead of global ambient state or
another context wrapper. Context copying adds a small in-memory lifetime per admitted plan;
it does not require persisted contexts, cost models or new telemetry machinery.

Qualify two interleaved native identities, anonymous logs, submission/collection/cleanup callbacks,
parent/caller restoration and native initial-source failure/interruption/binding-failure controls.
Do not weaken the prior independent assertions to pass. No production/GPU/throughput benefit is
established merely by accepting this decision; the current BEP findings own remaining delivery.
