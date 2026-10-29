---
id: ADR-0027
title: Domain operations bind immutable releases and preserve qualified support
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B2, §B5]
evidence: Proposed
revisit: A required operation exceeds the finite qualified inference or current source custody contracts.
---

## Context

SP-06/SP-07 replace installed-model interpretation in current producers and domain operations.
Semantic persistence exists; current orchestration still binds legacy schema versions and keys.
The operator authorized this replacement, including focused parsing improvements, and selected
positive source-supported asserted/defined facts as the initial inference seeds.

## Options

1. Preserve old orchestration interpretation beside the new publisher. This reduces initial
   migration work but permits two semantic authorities and incomplete dependency-sensitive reuse.
2. Replace parsing and inference with new generalized engines. This adds integration without
   establishing source-location fidelity, exact values or qualified proof provenance.
3. Retain useful parsing algorithms and queue protections, bind them to immutable semantic
   products, and use scoped relational operations. Selected; migration must connect actual consumers.

## Decision

Runs bind release, source inputs, applicable operation dependencies and input snapshots once.
Source content, rendition content and build provenance remain separate. Operational surrogate
IDs are not reproducible observation identity. Terminal writes retain task-attempt fencing;
passes capture immutable effective task-output cuts, including reused origins.

Occurrences preserve independent source items; facts group qualified meaning. Establishment,
confidence and scientific assessments do not replace source records or enter proposition identity.
Meaning-bearing scope is typed and uses stable source locators. Missing scope is not global.

Positive ontology rules use admitted hierarchy/inverse/symmetric/transitive declarations. Initial
binary-entity premises are positive accepted source-supported asserted/defined facts or grounded
derivations, with identical canonical context. Closure deduplicates conclusions, not proof paths.
Protected publication verifies direct proofs and authorization grounded in source supports;
cycles cannot authorize themselves. Negative and absence reasoning remain outside this profile.

Automated extraction, grading and adjudication require no human input. This change neither
regrades prior results nor changes their evidential status. Full evaluation migration remains SP-08.

## Consequences

One PostgreSQL store and model-derived metadata connect sources, tasks, occurrences, assessments
and derivations. Additional tables capture real provenance and lifecycle dependencies rather than
per-domain DDL. Existing HTML5, spaCy, regex and Lark mechanisms remain; local improvements remove
avoidable representation work without replacing source semantics. No performance claim follows.

Acceptance of this decision is not implementation or qualification. The domain-operations package
and pivot coordinator own actual progress, explicit remaining migration work and native receipts.
