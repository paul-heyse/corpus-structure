---
id: ADR-0049
title: Release qualified CPU source records through existing semantic authority
status: accepted
date: 2026-11-03
supersedes: []
superseded-by: null
design: [§B1, §B2, §B5, §B6]
evidence: Proposed
revisit: The five source families cannot be faithfully lowered through the existing semantic release, or a selected CPU operation needs different lifecycle or evidence semantics.
---

## Context

The [M1 series](../plans/first-production-milestone_2026-11-03.md) extends the implemented and
validated UM baseline with five statistics-first source-record families, field-addressable evidence,
a CPU extraction policy and bounded uncertain interpretation. Existing observation binding and
occurrence/evidence relations do not by themselves define complete record/field/set membership.
The [initial combined assessment](../design_review/reviews/design_review_m1-initial-target_2026-11-03.md)
accepts this Proposed target within the stated source and qualification limits.

## Options

1. Flat independently extracted fields with one passage citation: simplest storage, but loses
   record grouping, field evidence and qualifier scope required by tables and repeated values.
2. Independent family schemas/stores/validators: can represent richer records, but duplicates
   semantic meaning, custody, publication and consumer interpretation.
3. Extend the effective semantic release and existing observation/publication spine: selected.
   It needs coordinated declared/native/query/evaluator evolution, but preserves one authority
   and makes family-specific extraction a profile rather than a separate data architecture.
4. Replace finite rule closure with a universal probabilistic runtime: unnecessary machinery and
   a different entailment contract. Keep bounded candidate interpretation upstream instead.

## Decision

The effective domain release owns qualified record occurrences, field roles/states, named evidence
sets, record-to-assertion membership, candidate outcomes and interpretation operations. Lower through
existing native instance/publication/read authorities; no opaque family side store. Native item,
text, cell and formula evidence retain their actual coordinates/precision and original source pin.
Classified enum values are not literal extracted evidence. Original, normalized and derived fields
remain distinguishable. The existing qualified occurrence/fact distinction remains unchanged.

A versioned context extension admits typed neighbors, notes and referenced declarations without
weakening the direct-ancestor invariant of existing NativeProposalFrame v2/v3. Synthetic input
pieces have no invented source locator. All consumed counterevidence/context participates in
computation invalidation separately from rule proof premises.

One explicit M1 CPU policy schedules registered methods and observations with no general LLM
extraction or hidden hosted fallback. Reuse task fencing/cancellation and implement coordinated
run-owned resident CPU admission/supervision. Parent ownership retains database connections and
leases; detached workers execute model work outside publication transactions. Library-native record
assignment and numerical kernels are preferred over duplicate generic machinery.

The uncertain candidate interpreter returns coherent alternatives/limits and whole-record event
standing. Existing finite positive inference continues over admitted premises with its witnesses.
Only the existing domain-policy/consolidate_cut boundary publishes accepted knowledge.

Reference/fitting/calibration/final populations remain isolated. Completion here authorizes the
selected target, not a model-quality, statistical, deployed or measured claim. Deliver a qualified
nondefault release and adoption/rollback procedure; changing operational defaults awaits review.

## Consequences

All five families can share preparation, evidence, publication and consumer semantics. A new family
or model profile extends owned roles and operations rather than changing unrelated consumers'
interpretation. The cost is coherent release/native/evaluator migration, exact coordinate mapping
and independently demonstrated actual CPU behavior. No old observations, grades or live UM agent
tasks are migrated or reinterpreted by this decision. Existing accepted ADRs are preserved.

[M1-02/03/06 and later consumers](../plans/first-production-milestone_2026-11-03.md)
own implementation and qualification. Prior UM code functionality and validation remain complete;
its remaining agent assessment and follow-up stay outside M1. Release gates and actual operations
remain open until their named evidence exists.
