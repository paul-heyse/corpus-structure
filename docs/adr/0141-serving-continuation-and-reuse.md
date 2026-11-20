---
id: ADR-0141
title: Separate continuation compatibility from cache reuse
status: accepted
date: 2026-11-20
supersedes: [ADR-0137]
superseded-by: null
design: [§B3]
evidence: Proposed
revisit: Repeated native rendering or bounded page reconstruction materially obstructs the operator's working loop.
---

## Context

The installed readers currently suppress continuation and resource handles whenever their
code analysis cannot establish complete determining closure. The same analysis gates disposable
program and row caches. This couples required navigation to a difficult optional optimization.
The operator approved a bounded replacement on 2026-11-20. The
[focused target review](../design_review/reviews/design_review_serving-continuation-compatibility_2026-11-20.md)
compares authority, continuation compatibility and execution cost. The
[UDM qualification owner](../plans/unified-domain-model-and-execution/qualification.md#continuation-compatibility-amendment)
owns execution and final acceptance.

## Options

1. Continue proving every selected initializer, compiler hook and dynamic receiver before
   exposing continuation. This can authorize finer reuse but delays ordinary pagination and
   imposes substantial proof maintenance on a single-operator application.
2. Use a conservative managed-installation fingerprint for continuation compatibility and
   rederive bounded rows after current native authorization. This preserves navigable pinned
   reads with broader invalidation when application code changes. Selected.
3. Materialize durable result snapshots or introduce a constrained compiler worker. These
   add storage, lifecycle and enforcement responsibilities for benefits not required here.

## Decision

Continuation compatibility and cache eligibility have distinct meanings. A stable continuation
identity binds the query/profile contract, selected immutable model, sorted relative source and
resource paths and their content digests, actual Python runtime and resolved managed dependency
inventory. File-set additions and removals enter that inventory. Imported first-party source
correspondence and observable file/module drift are checked through shared custody primitives.
Unsupported drift requires restart. Dependency installation is deliberately managed, and runtime
monkeypatching of third-party libraries is outside this compatibility contract.

Each continued read reacquires current native authority and validates its cut, exact selection,
root support, ordering, ordinal and applicable data/response bounds before delivering rows.
Rows may be rebuilt after eviction or in another process. An incomplete reuse proof remains
attributed and can withhold a cache hit while a valid continuation remains available. The
conservative identity never marks a partial determining-code analysis complete.

Persistent generated-program reuse (D2), persistent served-row reuse (D4), and the one-derivation
across fresh entity acquisitions target are deferred. Their dedicated unused paths are retired.
Native authoring renders and compares exact program bytes through the existing route. Retained
programs and row data carry no native authorization. Bounded process caches retain their own
stronger eligibility checks. Their storage format remains separate from continuation semantics.

One captured model-source identity still owns one compiled model and its lazy projections.
Changed model content selects a new immutable capture on the next observation. Producer code
identity and acknowledged PDF/checkpoint/draft compatibility retain their existing conservative
rules, original attribution and native publication checks.

## Consequences

CLI and MCP pagination can finish while stronger result-reuse proofs remain partial. Application
edits may invalidate more cursors, and a later page can repeat bounded support loading, graph
preparation and prefix traversal. Those costs are explicit. This decision grants no prediction
of latency or speedup. Durable provider work, recovery and the whole-book zero-new-provider-work
repeat retain their qualification obligations.

This record accepts the target. Implementation and observed qualification remain with the UDM
coordinator, including migration of change-impact and every installed-read consumer. The deferral
is reconsidered when repeated preparation materially impedes an actual operator workflow.
