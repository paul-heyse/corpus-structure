---
id: ADR-0152
title: Stage selected archive support keys within the acquiring transaction
status: accepted
date: 2026-11-22
supersedes: []
superseded-by: null
design: []
evidence: Proposed
revisit: The staged selected-support closure materially obstructs an actual export after repeated traversal has been removed.
---

## Context

The candidate-conditioned D1 test reached its watchdog during the detached archive's native
support read. Each archive page rebuilt the selected graph and sorted serialized records. It
also computed live validity explanations that the archive discarded. The
[read and export plan](../plans/set-based-execution/owner-resolved-reads.md#sbx-12) owns the repair.

## Options

1. Remove live explanations and enlarge support pages. That eliminates unused work and reduces
   round trips. Each page still rediscovers the same graph and renders records before selection.
2. Open a non-holdable PostgreSQL cursor. PostgreSQL can retain one query execution. The archive
   also needs a guarded fetch protocol for exact byte bounds and cut authority.
3. Stage the finite relation keys under the same acquiring transaction. Bounded native fetches
   can use indexed keys, hydrate exact records, and preserve the existing JSON transport and
   authority checks. The stage adds temporary relations and one explicit lifecycle.

## Decision

Choose transaction-local key staging. The publisher stages identities under the live selected
read and hydrates bounded batches from those identities. The archived relation contract and
source, release and execution evidence stay with the existing archive owner. Current validity
explanations remain a live-reader responsibility.

## Consequences

The design pays for one selected support walk and keeps payloads out of the key stage. It holds
that stage only within the acquiring transaction and uses existing disclosure policy for
protected evidence. The [D8 export contract](../design/D8-agent-and-query-interfaces.md#cross-source-structural-products)
owns the boundary. Provider-conditioned completion and replay require managed acceptance.
