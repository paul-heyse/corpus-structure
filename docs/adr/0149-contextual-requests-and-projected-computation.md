---
id: ADR-0149
title: Keep contextual custody separate from projected computation and delivery
status: accepted
date: 2026-11-21
supersedes: [ADR-0100]
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A supported consumer needs cross-project reuse or a scope whose immediate change delivery cannot be bounded by the admitted dependencies.
---

## Context

DDO reconstructs subject context at native attachment and publication. A request row also
owns its exact binding and claim generation. Sharing that row by projection digest would
mix custody even where two computations read identical facts. The SBX-06 review also
found that readiness can change without a content change and that a settled read needs to
account for upstream changes still in flight.
[Identity and delivery review](../design_review/reviews/design_review_sbx06-computation-and-delivery_2026-11-21.md) ·
[SBX-06](../plans/set-based-execution/references-and-projection-keys.md#sbx-06)

## Options

1. Keep contextual computation keys and recheck readiness on demand. This retains one
   lookup and makes exact binding simple, while repeatedly acquiring unchanged premises and
   revisiting waiters under a common source.
2. Use one projection key for both reuse and claims. This makes reuse simple but conflates
   different occurrence, support or recovery requirements at the request owner.
3. Separate the computation lookup from exact custody and deliver native changes to
   immediate affected recipients. This requires durable origin and scope coverage. It
   preserves custody and can stop downstream work when observed projections stabilize.

## Decision

Use option 3. Exact requests, claim generations and publication retain authenticated project,
local subject, original source and analyzed scope. JSON scope numbers retain canonical
decimal meaning. Existing frozen historical interpretations retain their original identities.
A separate nonunique project-scoped lookup over admitted recipes, complete versioned read
projections, parameters and result-affecting policy selects retained computations.
A narrow projection must govern both the authenticated key and the execution envelope.
Undeclared or opaque reads retain conservative whole premises.

A current use must have its selected support and admissible proof establishments. Substituted
support is mandatory for a use that binds on that basis. A healthy historical support path
cannot substitute for that current support. Keep original producing inputs and result evidence
for authorized historical interpretation. Where the current output needs its own contextual
identity, admit it at the current occurrence with explicit retained-computation provenance.
Occurrence correspondence requires independent authority.

Native transitions commit replayable change facts and pending immediate work. A named
governed selection explicitly selects an authorized exact demand and an admitted successor
can advance it with a generation fence. Publication receipts anchor output events. Native
activation records the successful fenced old/new transition. Waiter enrollment reconciles
concurrent origins. The executor acquires bounded immediate work and settles the predecessor
and any affected successors together. Join decisions require current or established unchanged
arms. The native selection owner establishes coverage for its exact settled cut. Exact
pinned reads retain their own authority, and refresh computation requires demand.

## Consequences

SBX-06 migrates native and Python identity, binding, publication and readiness consumers as
one contract. It retires covered recursive wake discovery after native replacement evidence.
SBX-11/12 consume scoped coverage and own public freshness and pinned or detached reading.
Revision A is authored through the existing rollback-only route before registered cutover.
The decision accepts the target. The owning plan records implementation and test evidence.
[Settlement and coverage](../plans/set-based-execution/references-and-projection-keys.md#settlement-coverage)
