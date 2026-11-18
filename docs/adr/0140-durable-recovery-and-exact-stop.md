---
id: ADR-0140
title: Recover acknowledged work and stop an exact managed invocation
status: accepted
date: 2026-11-18
supersedes: []
superseded-by: null
design: [§B1, §B2, §B4]
evidence: Proposed
revisit: A supported operation cannot preserve acknowledged work or prove exact invocation retirement within its existing custody boundary.
---

## Context

The operator accepted the private-recovery and managed-stop rule impacts I02 and I07 in the
[UDM coordinator](../plans/unified-domain-model-and-execution_2026-11-19.md).
The book reached a settlement timeout after expensive computation and needed a manually
attributed interruption. Current process, native task, and managed receipt owners already
distinguish custody, claim authority, and publication.

## Options

1. Repeat completed computation after any failed handoff and locate the process manually.
   This keeps fewer intermediate artifacts but loses paid work and leaves attribution to the operator.
2. Introduce a parallel job controller and a general result cache. That would duplicate native
   ownership and make recoverable correctness depend on cache retention.
3. Add a bounded private handoff and an exact managed stop request at the existing owners.

## Decision

Select option 3. A custody owner can acknowledge an authenticated private draft before native
settlement. Check for an existing exact intent or publication before consuming the draft. A
currently authorized claim can adopt compatible durable work with proof of original producer
retirement where transfer requires it, retaining original producing evidence and current support
checks. Only native settlement confers publication. Failed and late unacknowledged results
follow existing refusal and discard rules. UDM-20's bounded diagnosis selects the durable handoff
mechanism for UDM-25.

An authenticated local caller can request cooperative stop of the exact managed invocation
after its identity, including process-start identity, is verified. The owning host decides
drain, quarantine and retirement. Stop request, demand detachment and physical retirement have
distinct outcomes. Independent native interest remains useful when one demand detaches.
Neither a lease expiry nor a successful cancellation request proves physical retirement.

## Consequences

The [recovery companion](../plans/unified-domain-model-and-execution/operation-reuse-and-recovery.md)
and [CLI companion](../plans/unified-domain-model-and-execution/operational-cli.md) own delivery.
The process and terminal-outcome decisions of ADR-0125 and ADR-0126 continue to govern their
respective boundaries. UDM-27 establishes the authenticated control route. This record confirms
the scoped target and leaves implementation and qualification open.
