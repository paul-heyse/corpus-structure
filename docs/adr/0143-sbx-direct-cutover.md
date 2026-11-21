---
id: ADR-0143
title: Regenerate derived data at the set-based cutover
status: accepted
date: 2026-11-21
supersedes: []
superseded-by: null
design: [§B2, §B5]
evidence: Proposed
revisit: A derived-data obligation requires preserving a superseded executable or wire representation.
---

## Context

The operator accepted the set-based execution series as a direct design-phase cutover. The
population, reference and request-identity changes replace derived representations across many
families. Those values are generated and can be regenerated from retained originals. The
source review identifies redundant storage and reconstruction around them.

[SBX coordinator](../plans/set-based-execution_2026-11-21.md) ·
[Cutover owner](../plans/set-based-execution/cutover-and-qualification.md)

## Options

1. Regenerate affected derived data through the target path. This concentrates implementation
   and qualification on one authoritative representation and pays the cost of regeneration.
2. Preserve old data through adapters, dual writers or old readers. This can save individual
   retained results but prolongs the very mechanisms the series replaces and complicates
   every later consumer and qualification claim.

## Decision

Adopt direct cutover for the SBX series. Changed kinds, references and request identities are
regenerated through the target representation. Original source custody and the native
publication, current-authority and recovery guarantees continue to govern their effects.
Retained artifacts remain evidence with their original dates and scope. They do not require
current execution support for their superseded representations.

Revision A carries the coordinated identity strand, B its read programs and C its PDF changes.
Register each at its owning SBX-20 boundary after development against rollback-only candidates.
The recreated book binding and final assembled qualification belong to SBX-20 and SBX-22.

## Consequences

The target removes compatibility adapters and repeated qualification of intermediate shapes.
Regenerating affected products consumes real provider work and discards their old semantic
identities. SBX implementation and qualification remain pending in the coordinator, and this
accepted decision supplies no stage or book completion claim. Revisit when an independently
required durable-data obligation makes faithful conversion valuable enough to change this
series' cutover scope.
