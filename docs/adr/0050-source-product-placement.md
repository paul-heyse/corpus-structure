---
id: ADR-0050
title: Separate private source-product constraints from knowledge graph realization
status: accepted
date: 2026-11-03
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A released source product needs direct graph realization, or another non-graph contract family needs the same placement distinction.
---

## Context

M1 source records require exact decimal spelling and full source/product/projection/recipe pins.
Their released JSON Schemas include bounded decimal/digest patterns. Existing native knowledge
publication deliberately refuses graph properties with regex constraints, whose graph-value
realization is unsupported. Its check already ranges only over graph property applicability;
Python release admission currently examines every definition. The private source-report contract
and the graph contract therefore need an explicit placement distinction before M1 can be admitted.

Focused independent source inspection at `f01784ba` plus the native custody changes found no
existing compiled placement category. `ClassDefinition` exposes hierarchy, identity and properties;
nonextractability prose or an annotation alone would not establish native enforcement. This is a
consequential realization choice under [ADR-0049](0049-m1-qualified-source-records.md), not a waiver
of the existing graph constraint profile. Advice is source inspection, not native qualification.

## Options

1. Remove source patterns and validate only in Python. Reject: private native ingress would not
   enforce the declared shape and a direct writer could bypass the application check.
2. Implement general graph regex realization now. Defer: M1 needs private report constraints,
   not a new graph constraint engine or a claim of regex equivalence across engines.
3. Add a general placement metamodel/category system. Defer: one finite distinction has a current
   consumer, while a general system adds migration and interpretation burden.
4. Declare a source-product ancestor, retaining schemas while fencing graph use. Selected.

## Decision

The released abstract `SourceRecordProduct` ancestor identifies the private source-record
product closure: record values, fields, evidence, family field contracts and their envelope.
Existing hierarchy interpretation supplies the closure. Preserve every class/registry definition,
generated adapter and archived JSON Schema. Exclude this closure only from graph property
applicability and graph identity-slot lowering. Python release admission uses the same distinction;
the native regex refusal remains unchanged because it already examines graph applicability.

A graph-eligible property cannot range into the product closure, whether inlined or referenced.
Protected native knowledge validation refuses both class membership and any typed-value datatype
naming the product closure, including empty, nested or disconnected values. Removing applicability
without these fences is not the selected design. Unsupported patterns on ordinary graph classes
continue to refuse release admission.

Private source completion retains generated-schema validation plus authenticated task/source/
product/projection/recipe and actual coordinate/text custody. It refuses accepted whole-record
standing. Qualification must challenge malformed decimal/digest payloads through actual native
ingress; this decision does not establish general Python/native regex equivalence.

M1-11 must derive queryable accepted record/field/evidence-set/assertion-membership projections
from the same released definitions through existing protected publication. It must not separately
author another family schema, publish private product class membership as knowledge, or claim
that an opaque report envelope is complete field-addressable publication.

## Consequences

Source products retain one declarative meaning and effective schema while the store enforces the
actual supported realization boundary. A finite ancestor marker and existing hierarchy operations
serve release lowering/admission and native publication, without a second store or generic engine.
The cost is coordinated preparation, metadata lowering, admission and protected native validation.
M1-02/03/11 own those obligations and their negative controls at the
[coordinator](../plans/first-production-milestone_2026-11-03.md). Native authoring/test databases
remain private; no live UM database/default is migrated by this decision.
