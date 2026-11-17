---
id: ADR-0123
title: Physical calls reserve before hydration and reduce to measured ownership
status: accepted
date: 2026-11-17
supersedes: []
superseded-by: null
design: [§B2]
evidence: Proposed
revisit: A physical request cannot retain one bounded reservation through hydration, computation, reduction and settlement without a capacity deadlock.
---

## Context

The accepted production-efficiency plan separates planner pages, live claims and physical
memory ownership. The earlier fixed pre-hydration charge unnecessarily limits progress after
small inputs are hydrated. PE-S23/PE-RC03 specifies the replacement; D6 owns physical execution
and §B2 preserves parent-owned observation production and settlement. This records that settled
design, rather than introducing another review or changing semantic identity.

## Options

1. Keep worst-case reservations until settlement. Ownership stays simple but small hydrated
   inputs unnecessarily retain capacity needed by independent ready work.
2. Hydrate before reserving, or add authored size estimators. The former permits concurrent
   hydration to exceed the budget; the latter adds another authored authority without reliably
   representing actual bytes.
3. Reserve conservatively before hydration, then reduce the same owned reservation using
   measured hydrated bytes (selected). This reuses existing byte accounting and lifecycle owners;
   it requires an explicit one-way reservation transition and no additional scheduler.

## Decision

Admission still precedes claim, hydration, serialization and queueing. Stage A reserves twice
the physical packet bound plus three times the reply bound. After hydration, its sole owner
may reduce that same reservation to twice the measured hydrated bytes plus three times the
reply bound. The charge never grows and lasts through the final consumer. Inputs above the
packet bound refuse and release their reservation.

A batch is one physical call and is charged once; split batches before their packet bound is
exceeded. Logical members remain bounded by max_claims. CPU admission requires credit for the
actual packet plus reply bound. Planner page size is independent of both limits. One bounded
ReadyFrontier per sweep supplies compact ready manifests; binding runs on the existing driver
between ticks. No thread, durable queue or scheduler is added. Publications become visible on
the next sweep. ADR-0084's cancellation, retirement, parent reduction and native settlement
contracts remain in force, including admission before hydration.

## Consequences

Small inputs can release excess reservation without weakening pre-hydration bounds. The driver
must drain replies/reductions before waiting for new admission, preserve one owner at every
transfer and bound ready manifests and claims independently. These are encoded-state bounds,
not an RSS guarantee or a measured speedup. Implementation and functional verification remain
open under [PE-S23](../plans/declared-data-operations/demand-planning-and-execution.md#pe-s23--two-stage-byte-admission-pe-f11-pe-rc03).
