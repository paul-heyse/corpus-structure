---
id: ADR-0030
title: Semantic consumers select completed results and protect independent references
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: Multiple concurrent operators require reference authorization or scheduled deployment beyond the current single-operator model.
---

## Context

SP-08–SP-10 must join the current semantic producer, query, export and grading interfaces.
The completed knowledge `EvaluationResult` already owns sealed consolidation output. Calling an
independent-reference grade the same result would conflate scientific construction with its
assessment. A default query also needs an immutable selected answer, rather than rebinding an
old result to whichever interpretation is active now. DESIGN §B5 owns these boundaries.

## Options

1. Extend the old knowledge tables and golden stores alongside semantic persistence. This
   preserves old call signatures but retains two editable meanings and incompatible identity.
2. Use a new generic workflow/query system to govern every consumer. That adds dispatch and
   state machinery without a second supported execution engine or operational consumer.
3. Extend the trusted LinkML companion model and existing protected PostgreSQL kernel, while
   retaining the existing pure matching, mathematical and source-processing algorithms.
   This keeps native transactions, existing snapshots and batch access paths available.

## Decision

Use option 3. `ReferenceSet`, `ReferenceUnit`, authored `ReferencePass`, versioned citation frames,
reference items, document splits and `ReferenceEvaluation` have separate LinkML definitions and
fixed relational storage. Independent-reference grading binds the exact completed prediction,
pass-C and citation-frame snapshot, preserving undecided mathematical outcomes. Authored bytes
and previous grades remain immutable. An evaluator login accesses reference data; the source
writer has no reference access. Grading and adjudication are automated and need no human input.

A project's selected completed result is independent of its active interpretation. Both pointer
changes use the existing generation CAS. Current queries, explanations and full relational
Arrow exports bind the selected result's archived release and revision. Exports publish through
atomic directory completion and retain qualified value/provenance relations.

CLI/MCP entry points use restricted semantic credentials on one declared database endpoint.
Purpose-specific URLs supply authentication, never a second storage target. Regeneration archives
explicit pack inputs, registers actual source bytes, runs the existing source methods and invokes
a fresh run-bound stdio MCP extractor. The extractor receives source packets without reference
credentials, builtin filesystem tools or inherited project customizations. Resumption uses the
archived run binding. The existing MCP process and old databases remain untouched.

## Consequences

There is one current semantic storage interpretation and no automatic legacy-row migration or
upcaster. Useful named queries and alignment algorithms stay; replaced legacy persistence APIs,
entry-point branches and their old-schema harnesses retire together. Indexed rendition text
prefilters source search before exact segment matching. Columnar exports reuse the existing
qualified projection rather than inventing a flattened interchange authority.

The fresh deployment requires actual source/provider journeys before acceptance. Decision
acceptance does not establish their success. The semantic pivot coordinator and regeneration
plan own implementation, native/provider evidence and unresolved obligations; an already-running
MCP process will use its original code until the operator elects to refresh it.
