---
id: ADR-0104
title: Bind discovery child inputs to explicit parent members
status: accepted
date: 2026-11-14
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A discovery target requires a declared relationship other than one exact parent product/member per child input role.
---

## Context

The reopened DDO foundation journey publishes two scoped selected-source discovery members, then
profiles each child. A source-profile role accepts original-source and computed inputs with scalar
cardinality. The frozen original view and discovery member can both qualify in that context while
retaining different product/member references. Discovering a child context does not itself declare
which input representation that child selected. Equal source bodies cannot erase that distinction.
The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md#foundation-execution-receipt--2026-11-14)
owns the actual failing journey, implementation and verification; D6 owns demand semantics.

## Options

1. Prefer computed or original inputs, or globally narrow the source-profile origin contract.
   Simpler locally but hides selection authority or removes the direct-original capability.
2. Deduplicate equal bodies across different qualified products/members. This changes declared
   cardinality and support semantics; no universal value-equivalence inference is accepted.
3. Explicitly associate a discovery target input role with the selected parent product/member.
   Selected. It localizes the choice in frozen demand intent and reuses existing population
   membership, bindings and witnesses, without a new table, selection registry or workflow engine.

## Decision

DiscoverySelection can name the target input role that consumes its selected discovered member.
When present, freezing and native registration validate the target role and producer/member kind.
The planner restricts that role to the authenticated population's exact parent product/member
before checking cardinality. Native admission independently checks that same association, context,
producer and valid support. Unrelated matching computed/original candidates cannot substitute for
an explicitly selected member. Other input roles retain their declared semantics.

An absent association preserves existing frozen intent meaning and unassociated discovery behavior;
it does not infer a role or select an origin. The source-profile operation retains its declared
original/computed capability. Its discovery caller explicitly selects its source-role association.
No body-level deduplication, implicit origin preference or manufactured custody is introduced.

## Consequences

Frozen demand intent owns the additional selection while existing data populations own membership.
Filtering before cardinality narrows the eligible role candidates without a second selection
authority. Native admission remains a separate trust boundary. Expected simplification and bounded
work are qualitative, unmeasured; no benchmark or new assurance framework follows.

Implementation touches demand freezing/planning, binding compilation and native registration/
admission together. Existing registered SQL is immutable; changed native behavior needs a forward
successor. Targeted role-validation, unchanged-absence, wrong-member and actual scoped-child checks
establish only this slice; provider journeys and full series qualification remain separate. This
accepted decision alone does not close the journey or establish implementation.
