---
id: ADR-0029
title: Evidence-backed exclusions constrain semantic identity resolution
status: accepted
date: 2026-10-29
supersedes: [ADR-0028]
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: A required identity operation needs scored must-links, split judgments or mutable identity history.
---

## Context

This record preserves ADR-0028’s decision and corrects its unresolved architectural reference.
No semantic clause or implementation guarantee changes; the original is recoverable in Git.

SP-07 names cannot-links, while the implemented resolver applies exact declared keys and global
label policy. The operator explicitly selected modeled exclusions during execution planning.
The source, native publisher and current readers must agree on those constraints without adding
a second identity authority. Automated extraction and adjudication remain unchanged.

## Options

1. Retain only exact-key resolution and defer exclusions. Simpler, but does not deliver the
   explicitly selected capability.
2. Add a general scored merge/split system. This introduces new inputs and policy machinery
   beyond current operations and the approved scope.
3. Model source-backed exclusions and constrain the current resolver. Selected: reuse source
   evidence, entity_source/entity_input, finite domain algorithms and protected publication.

## Decision

LinkML owns typed exclusion endpoints, declarations, evidence and the executing contract.
Endpoints refer to local source declarations or the bound known-input snapshot. Exclusions are
operational identity constraints, not unqualified negative domain facts or scientific judgments.
Located primary evidence makes an exclusion eligible; uncertain reports remain explicit.
Mandatory declared-key equivalence conflicting with an exclusion refuses evaluation atomically.
Label-only candidate merges are vetoed deterministically, preserving distinct source identities.
Existing source assignments and input lineage resolve endpoints; no parallel assignment store,
workflow engine or fuzzy matching subsystem is introduced.

PostgreSQL enforces scoped endpoints, source/evidence custody and required-cut completeness.
Source reports remain immutable; protected publication cannot omit an eligible exclusion or
collapse its endpoints. Current query, qualified graph and Arrow projections retain the
constraint and producing provenance. Reasons and citations do not erase independent declarations.

## Consequences

The current source-to-result path can represent identity exclusions without broad legacy
migration. New relations represent actual constraints and supporting evidence, not event history.
The compiler/operation binding and frozen migration change deliberately; old artifacts are not
silently upcast. Workload-fit choices retain batched crossings and existing pooled transactions.
Acceptance of this ADR is not implementation or qualification. The
[domain-operations plan](../plans/semantic-model-pivot/domain-operations.md) and its coordinator
own delivery, passing evidence and remaining obligations.
