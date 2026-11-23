---
id: ADR-0145
title: Carry validation between unchanged custody boundaries
status: superseded
date: 2026-11-21
supersedes: []
superseded-by: ADR-0154
design: [§B5, §B6]
evidence: Proposed
revisit: A supported mutation or process boundary cannot preserve the established carrier premises.
---

## Context

The source trace found immutable bytes repeatedly decoded, validated and hashed within one
process. Existing public wrappers also allow construction without admission, which makes their
type alone insufficient evidence. Loaded-code verification remains necessary because a
function-local import can first occur during computation.

[Validated values owner](../plans/set-based-execution/validated-values-and-handoff.md) ·
[Execution review](../functional_reviews/columnar-execution-outside-postgresql_2026-11-21.md)

## Options

1. Retain validation at every property access. This protects unchecked construction but repeats
   work over unchanged bytes and scatters ownership.
2. Add isolated caches to each existing wrapper. This reduces some repetitions but leaves
   unchecked construction and duplicate source carriers in place.
3. Close construction and carry one frozen admitted view through the process. Named worker
   acceptance and a computation verification bracket cover the boundaries that can change it.

## Decision

Source and product carriers enter through their validating constructor or a named worker
acceptance path bound to sealed bytes. A carrier retains its bytes, frozen decoded value and
memoized derived views through the existing process-owned lifetime. Hydration, ports and
kernels share that admitted value.

Prepare each loaded-code slice once and verify it before computation submission and after
reply collection. The post-computation check covers imports that first occur during the call.
Process replies remain bound to request digests, and native claim, current support, publication
and recovery checks retain their owning authority. Each removed repeat must name the unchanged
premises carried by its replacement.

## Consequences

The expected benefit is less repeated acquisition and reconstruction with one local
construction contract. The implementation must migrate all callers that directly build or
replace carriers and preserve mutation isolation. SBX-08 through SBX-10 own implementation and
focused checks. This decision establishes an accepted target and makes no claim that today's
wrappers already satisfy it. Revisit if a supported mutation or process boundary cannot carry
the premises required by its consumer.
