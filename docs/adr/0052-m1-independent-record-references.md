---
id: ADR-0052
title: Freeze source-only record references before extraction and isolate fitting access
status: accepted
date: 2026-11-03
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: Source-only reference membership cannot be frozen independently of producer output, or fitting needs another protected partition or authority.
---

## Context

[M1-01/13](../plans/first-production-milestone_2026-11-03.md) needs independent five-family
references before extraction succeeds. Existing reference tables and protected operations are
usable, but their completed-result foreign key and Agent frame assumptions cannot represent a
source-ready population with missing producers. Independent origin groups and isolated fitting
also need executable boundaries, rather than a convention that fitting code avoids held-out rows.

## Options

1. Wait for successful completed predictions, then select reference units. Simple, but excludes
   failed or unrouted units and makes population membership depend on extraction availability.
2. Add a second reference store and scorer. Reject: duplicates protected lifecycle, pass/frame
   custody and evaluator authority without a different scientific responsibility.
3. Extend the existing store with a distinct released record protocol, source-ready cut binding
   and restricted fitting capability. Selected: preserves existing authority and historical
   meanings while admitting independent preparation and explicit empty/missing denominators.
4. Give fitting the evaluator login and filter partitions in Python. Reject: accidental or
   indirect reads can expose calibration/final labels; filtering is not access isolation.

## Decision

Reuse `eval.reference_set/unit/pass/frame/reference_evaluation`. The new source-record protocol
freezes a named sealed source cut and actual selected-source membership at reference-set creation,
including views without record producers. It retains guideline text and digest, released family
meaning, independently declared source scope, logical source binding and immutable origin partition.
This is a creation-time snapshot, not a claim to reconstruct past membership at an earlier cut.
Legacy Agent reference operations retain their completed-result and frame contracts.

Relax the shared reference-set source-run foreign key only to the existing run relation. New
protected operations enforce source-ready membership; existing creation operations still enforce
completed output. Record grading requires immutable completed publication, the same frozen source
closure and compatible released meaning. Both the protected entry point and shared insert guard
validate the distinct protocol. Missing predictions remain empty evaluated inputs; an actual
contradictory producer binding refuses. Reference readings never grant production acceptance.

Origin assignment is immutable by project/source URI and credible origin group. Development,
feature fitting, final event calibration and final assessment are distinct partitions. Copies,
editions and overlapping windows do not create independent origins by being split into units.
A restricted actual `corpus_sem_fitter` login has no evaluator-table reads, role inheritance or
publisher/evaluator membership. Its only reference capability returns adjudicated feature-fit
sets through a protected function that checks the actual session principal and partition.
The evaluator retains authoring/grading authority. Extraction receives neither answers nor
fitting/evaluator credentials. Role provisioning remains a separate explicit host operation.

## Consequences

Independent authoring can start from source availability and retain omissions. Bulk public record
reads and one source frame per unit avoid producer-envelope hydration and per-record crossings.
The cost is a coordinated protocol/schema/native migration and one additional restricted login;
no universal partition service or second workflow/store is introduced. Native negative controls
must establish missing/empty preservation, source closure, immutable origins and held-out refusal.

The decision is accepted; implementation and actual database/authentication qualification remain
open at M1-13. Focused pure tests do not establish leakage isolation or a qualified release.
Prior grades, live native99 databases and operational defaults are unchanged.
