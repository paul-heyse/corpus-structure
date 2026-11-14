---
id: ADR-0105
title: Archive effective identity headers without repeated canonical witnesses
status: accepted
date: 2026-11-14
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: An archive consumer requires independently persisted canonical identity witnesses, or the complete governing model remains infeasible at the native archive boundary.
---

## Context

The actual definition-demand journey failed while PostgreSQL converted the effective model to
JSONB (`2950f7ac49574c4a970e491119d89972`). This occurs after ADR-0098's binary staging;
it is a separate representation problem. The captured-input
[archive-shape investigation](../design_review/evidence/2026-11-14_ddo-model-archive-shape/README.md)
measured a 223,217,117-byte model, including 204,671,906 bytes of identities. Each effective kind
identity repeats its complete rooted canonical witness, duplicating governing facts already in the
same archive. Current native and Python consumers use effective identity owner, domain and key.
Generic canonical identity callers do use their witness and retain that contract.

D2 owns compilation and archive interpretation. The DDO coordinator owns implementation,
bounded qualification and eventual adoption separately from this decision.

## Options

1. Read the existing blob through PostgreSQL JSON rather than JSONB. This avoids one physical
   limit but retains repeated construction, storage and parsing, and changes multiple native
   consumers around an unnecessary representation.
2. Persist effective identity headers and the complete governing graph once. Selected. Existing
   fingerprint functions reconstruct an exact witness when required. This removes redundant
   work at its owner without changing semantic information or introducing a cache lifecycle.
3. Compress or separately deduplicate witnesses. This retains an unused derived archive product
   and adds codecs or reference resolution to compilation, native validation and historical reads.

FP-07/A4 and the efficient-architecture heuristics favor removing repeated derived material over
optimizing its transport. Historical interpretation remains necessary; current execution does not
need multiple interchangeable representations.

## Decision

Effective model format v5 stores only owner, domain and key for effective identities. Compilation
computes canonical input transiently for hashing; canonical framing, tagging and hash algorithms
are unchanged. Complete governing kinds, nodes, edges, bindings, projections and implementation
slices remain archived. Existing fingerprint functions can reconstruct witnesses from that frozen
model; no new lazy cache, witness registry or parallel publication path is introduced.

Generic CanonicalIdentity retains canonical_input. Exact v2/v3/v4 archive readers retain their
original witness-bearing representation and feature rules, solely for historical custody.
Current model admission, native projection and Python execution ports require v5. Frozen migrations
are unchanged; native adoption uses an explicit successor. ADR-0098's typed binary staging and
atomic finalization remain authoritative.

## Consequences

The current model has one authoritative governing representation with smaller expected archive
construction, retention and parsing work. A caller requiring a witness must run the existing pure
fingerprint computation rather than read a duplicate field. Historical readers carry a small
explicit DTO distinction; historical content is not silently rewritten or admitted for execution.

The baseline size is measured; reduced size and runtime benefits are not yet measured. Acceptance
does not establish completed implementation or native/provider qualification. The
[current DDO execution owner](../plans/declared-data-operations_2026-11-12.md#current-integrated-implementation-and-scoped-evidence--2026-11-14)
retains those obligations, the prior failed receipts and DDO-11 deployment boundaries.
