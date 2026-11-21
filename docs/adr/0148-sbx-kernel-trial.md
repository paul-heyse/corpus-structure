---
id: ADR-0148
title: Trial set operations on one kernel family
status: accepted
date: 2026-11-21
supersedes: []
superseded-by: null
design: [§B2, §B5]
evidence: Proposed
revisit: The scoped-relations trial demonstrates a material fidelity mismatch or integration burden that defeats its functional benefit.
---

## Context

Most inspected kernel work remains procedural, but scoped relations repeatedly asks a
known set of range, containment, grouping and ordering questions. Its limited consumer set
makes it a useful trial of set execution. The operator accepted one trial ending in a recorded
decision about further adoption.

[Kernel trial owner](../plans/set-based-execution/kernel-trial.md) ·
[Library fidelity evidence](../design_review/evidence/2026-11-21_columnar-execution-review/README.md)

## Options

1. Keep the scoped-relations procedural implementation. It preserves familiar library
   semantics but retains repeated scans and separately implemented interval questions.
2. Rewrite several families at once. This could share machinery early but expands fidelity
   and integration uncertainty before one complete family is established.
3. Trial scoped relations through the existing analytical owner and decide from that complete
   replacement whether another family should follow.

## Decision

SBX-18 prepares the analytical owner's explicit ordering, null, collation, aggregate and
worker-lifetime contracts. SBX-19 rebuilds scoped relations with typed set operations over its
source, navigation, formal and predicate inputs. Preserve Python regular expressions, case
folding, identity encoding and other operations whose library semantics differ. Carry explicit
ordinals and phase order wherever they affect output meaning or identity.

The complete trial replaces its procedural implementation and validates representative
independent expected results and retained family fixtures. It ends in a recorded adopt,
adjust or stop decision for extension to further families. The trial does not automatically
authorize conversion of the other kernels.

## Consequences

A successful family can remove repeated scans and clarify reusable analytical operations.
The trial incurs conversion and fidelity work, and a poor result can justify stopping further
expansion. SBX-18 and SBX-19 retain implementation and qualification obligations in their owner.
Current synthetic library checks establish their stated behavior and no production timing
claim. Revisit when a material semantic mismatch or integration burden defeats the intended
benefit of the trial.
