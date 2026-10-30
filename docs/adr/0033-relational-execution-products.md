---
id: ADR-0033
title: Release-scoped execution rows govern stable protected kernels
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Implemented
revisit: A required effect needs semantics outside the owned bounded operation profiles.
---

## Context

CA-06 and CA-12 expose disconnected effect declarations and incomplete native authoring.
Rebasing a model identity or body digest does not establish changed behavior. The operator
selected fixed PostgreSQL projections so supported variation can become additional release rows.
ADR-0031 retains semantic authority, immutable archives, restricted admission and complete atomic
operations; this decision specifies their physical realization without revising those contracts.

## Options

1. Regenerate global edge VALUES functions and carry opaque effect labels. This is smaller locally,
   but erases release/operation identity and couples finite model variation to deployed function bodies.
2. Interpret arbitrary effect programs or introduce a generic EAV/proof system. Current operations
   need neither a new language nor another lifecycle or evidence service.
3. Project finite operation, transition, edge and effect requirements into fixed typed relations,
   with stable owned consumers and explicit implementation support. Selected: one forward schema
   change and bounded adapters preserve scoped authority while allowing supported variation as rows.

## Decision

The trusted physical LinkML model defines seven fixed relations: execution operations, transitions,
finite edges, operation effects, transition effects, effective property roles and scientific
policy decisions. Existing exact-source preparation and protected complete archive publication
produce their immutable release-scoped rows; native checking compares exact row sets with archived
products. Effect identity/version requirements resolve against independent code-owned supported
profiles. A new requirement cannot acquire support merely by changing descriptor metadata.

Stable native guards consume release/operation/transition identity and those rows. Complete
protected operations retain attempt/holder, source/proof, terminal atomicity, replay and CAS
semantics. Writer lifecycle mutation grants are narrow; protected set-based claim and lock helpers
preserve current transaction and batching behavior. Detached analytical inputs carry their exact
execution recipe, and check resource contracts before acquiring resources. Cleanup remains unconditional.
Property roles reach actual Core filtering before hydration. Scientific decision rows constrain
persisted reference comparisons at the protected database boundary. The deployed supported traversal
layout derives from the trusted LinkML constructor model and is checked at native admission and
persistence before archived paths are used. Empty, partial or moved paths cannot attest their own
support. These checks do not establish that
observed evidence is scientifically correct or regrade historical output.

The existing schema authoring command emits complete transport fragments, Core table/index/
constraint/view DDL, stable native consumers, exact candidate row products and ordered deployment
metadata. It refuses an unmapped transport shape before creating output. New deployment uses
frozen semantic_0033 bytes; historical migration execution never imports current generators.
Compiler 13, execution compiler 4, retained boundary ABI 12 and archive envelope 3 remain distinct.
Old finalized archives are not backfilled or rewritten; supported historical reads retain their ABI,
while new write/admission compatibility is checked separately.

## Consequences

Finite edge and property/policy variation can use additional immutable rows without one function
or table per semantic kind. Existing indexes and set-based kernels keep work at complete-operation
scope. This adds five execution projections and two consumer projections, plus one forward
migration and bounded correspondence checks. It adds no universal interpreter, alignment lint,
proof registry or quantitative performance claim. Body hashes retain deployment custody only.

Implementation and qualification remain separate. The coordinator's CA-06/CA-12 dispositions and
remaining selected work are owned by [the pivot coordinator §14](../plans/semantic-model-pivot_2026-10-29.md#14-improvement-integration-2026-10-29).
The independent focused controls do not establish the enclosing required-union qualification.
