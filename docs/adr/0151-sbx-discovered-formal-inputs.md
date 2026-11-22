---
id: ADR-0151
title: Bind independent formal-evidence products as a set
status: accepted
date: 2026-11-22
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: A supported construction policy requires precedence between independent formal producers.
---

## Context

Construction receives eligible formal-evidence products discovered for an exact source scope.
Two independent producers can publish from that scope and both publish their scalar result at
position zero. Discovery carries that emitted position. The current sequence binder requires
unique positions and refuses the pair. The products may also use the same local graph member
identifier. Citing either member requires an address within the original producing binding.
[SBX-05 reference contract](../plans/set-based-execution/references-and-projection-keys.md#sbx-05)

## Options

1. Require a single formal product. This keeps simple scalar references and excludes evidence
   from another independently eligible producer.
2. Declare precedence across formal producers. This would be meaningful for an authority policy
   that selects one result ahead of another. It would require a rank and tie policy, and that
   policy would affect binding identity and construction results.
3. Bind an unordered set and use the already recorded role-local input address to cite each parent.
   This admits independently supported products without assigning them precedence. The resolver
   can reuse the native binding's input projection and exact selected-use checks.

## Decision

The operator selected the set on 2026-11-22. The native attachment and derivation owners use the
same role-local input address for the exact frozen producing inputs. The product's emitting
position retains its producer-local meaning. Formal evidence retains its internally ordered
structures and source positions. The source scope determines eligibility. Multiple distinct
reports for the same eligible source can coexist and bind in one operation.

A citation to a discovered member names its role, the original input position and member key.
A consumer finds the parent through the original binding and checks the exact product, member
and multiplicity in its current selected use. Adding or reordering other current set members
can change the current rank while leaving the old citation's meaning intact. Existing frozen
source sets continue to supply their declared labels.

## Consequences

Construction can combine independent formal evidence even when emitting positions and local
member keys coincide. The change uses the existing derivation input ledger. Effective model
compilation, authenticated acquisition, native completion and live and detached readers must
agree on the address and on where current support is required. The [SBX-05 plan](../plans/set-based-execution/references-and-projection-keys.md#sbx-05)
owns implementation and installed acceptance.
