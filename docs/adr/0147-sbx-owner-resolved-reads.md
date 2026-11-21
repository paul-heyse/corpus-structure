---
id: ADR-0147
title: Resolve online reads at the native disclosure owner
status: accepted
date: 2026-11-21
supersedes: []
superseded-by: null
design: [§B3, §B4]
evidence: Proposed
revisit: A replaying consumer needs a distinct answer implementation or native answer construction repeatedly reconstructs the same closure.
---

## Context

Native reads already resolve output relationships, yet the local index strips answers and
readers reconstruct joins. Multiple cursor and projection mechanisms duplicate that work.
Some consumers deliberately replay the same logic over a detached export, so they need a raw
closure as well as online answers.

[Read owner](../plans/set-based-execution/owner-resolved-reads.md) ·
[Independent review F02 and F04](../design_review/reviews/design_review_sbx-revision-a-identity-and-authority_2026-11-21.md#F02)

## Options

1. Keep a generic local index for every read. It supplies one raw closure but makes online
   readers materialize and rebuild relationships already resolved in PostgreSQL.
2. Move every projection into native programs. This simplifies online reads but duplicates
   the replay implementation required for independent detached verification.
3. Supply native answer shapes for online readers and one shared relation interface for
   replaying readers. Each uses the representation its execution purpose requires.

## Decision

The native disclosure owner supplies selected outputs, keyed partitions, derivation facts
and proofs with filtering and keyset paging. Reuse its resolved answer at the consumer. Each
page reacquires current principal, cut, scope and kind visibility. A partition key or content
digest supplies no independent authorization or evidence of protected absence.

Readers that replay use one projection over typed relations from either live acquired rows
or authenticated exported rows. Their export includes the partitions and proof facts needed
for that calculation. Consolidate continuation and substantive cache key semantics through the
read owner while preserving current authority checks.

The exact consumed use supplies the selection for use-facing support. Role-relative body
references resolve through their producing derivation's original inputs. Distinct uses sharing
a derivation retain their own selections. Private SQLite stores remain only where an identified
invocation or replay consumer needs them. The existing five-store count describes the current
implementation and ceases to constrain the target count as their responsibilities retire.

## Consequences

The target removes online index reconstruction and duplicate cursors while preserving one
independently replayable projection. Native Revision B depends on A's partition and proof
relations. SBX-11 through SBX-13 own implementation and retirement, with the selected-support
field defect fixed in SBX-00. ADR-0141's separation of continuation compatibility and cache
eligibility remains applicable. Revisit when a replaying reader cannot share its projection
between sources or native answers repeatedly reconstruct the same unchanged closure.
