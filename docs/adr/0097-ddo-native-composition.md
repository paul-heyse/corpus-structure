---
id: ADR-0097
title: Declared nominal refinements and document paths preserve concrete input identity
status: accepted
date: 2026-11-13
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A consumer needs substitutability beyond captured nominal inheritance or an identifier association through a non-scalar/non-inline relationship.
---

## Context

DDO-07 document composition consumes several concrete characterization families, potentially
from several original projections of the same document. An exact-kind-only role cannot express
that common interface. Replacing concrete kinds with an untyped JSON union would lose nominal
validation; relabelling products as the interface would lose their actual semantic identities.
A source projection's own subject must also survive association with its original document.

This realizes the composition and authentic-support contracts of ADR-0092–0096. The DDO
coordinator owns implementation and qualification; acceptance here does not establish adoption.

## Options

1. Enumerate every family as a separate input role and repeat the document identifier in every
   product. This is workable for a closed family list but couples composition to every producer
   and introduces a second representation of the same original document.
2. Erase products into generic dictionaries or reinterpret concrete products as their common
   parent. This loses the actual kind, concrete body validation or lineage and is rejected.
3. Derive input substitutability from captured nominal inheritance and associate identifiers
   through declared owned property paths. Selected. The extra compilation/native correspondence
   supports one common interface without a family registry or duplicated source facts.

## Decision

An input role's declared kind denotes its nominal interface. Its accepted concrete kind contracts
are derived from the captured `inherits` graph, excluding abstract kinds and refusing unresolved,
incomplete, cyclic or category-changing inheritance. NetworkX uses an explicit core-backend
inheritance projection, with parent-to-child edges, DAG validation and descendant reachability.
The native admission projection records the derived contracts; native admission independently
reconstructs the same set from the authenticated archived model. Request-time binding consumes
that admitted projection rather than reparsing inheritance for every candidate product.

Queries, population selection, binding decoding and request identity projection accept actual
concrete contracts through that interface. Actual product/member kind contracts remain unchanged
in selected facts, semantic request inputs, native bodies and lineage. Outputs remain governed by
their declared exact publication contracts. Each selected concrete body is validated as its own
kind; an abstract adapter must not strip subtype properties or authorize another purpose universe.
Actual source/evaluator purpose checks remain with the native candidate and publication owners.

`subject_field` keeps its existing single owned-property meaning and may also contain an RFC 6901
property pointer, for example `/source/document`. Preparation validates every owned nominal
property; intermediate records must be scalar and inline, and the leaf must be an identifier.
Python projection and native binding traverse the same canonical tagged body. Missing values do
not establish an association. This associates several projections with the actual original
document without changing their own subjects, offsets, selectors, product identities or provenance.
Arrays and inferred relationships are outside this identifier-projection contract.

## Consequences

New characterization families can compose through a declared common marker while retaining their
own concrete schemas and identities. There is no handwritten provider/kind map and no duplicate
document-key property. This adds compiler, fixed native projection and binding responsibilities;
those are shared semantic mechanisms with real document-composition consumers.

Pure relational and identity controls passed on 2026-11-13 (`e01d3b0e4212488b9417349bbe5dbf1f`,
78 selected). The combined native successor, nested-path controls and actual family composition
remain in execution. These are bounded checks, not final DDO-03/07 qualification or cutover.
