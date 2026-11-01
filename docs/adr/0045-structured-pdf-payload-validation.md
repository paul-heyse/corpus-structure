---
id: ADR-0045
title: Validate model-governed PDF page payloads over immutable stored bytes
status: accepted
date: 2026-11-01
supersedes: [ADR-0042, ADR-0044]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A selected payload needs SQL interior operations or its codec cannot preserve declared meaning.
---

## Context

Confirmed PDF RC10/11/12 select scoped runtime interior validation and current-product rebuilding.
The merged PostgreSQL realization supplies typed COPY, frozen publication and native authoring.
Arrow structural validation cannot establish OCR geometry, word spans or complete coverage.

## Options

1. Universal SQL scalar lowering and per-row JSON Schema repeats representations and cannot
   interpret arbitrary nested Arrow directly.
2. One opaque whole-book value loses selective retrieval and risks large-value limits.
3. Model-derived page payloads with relational custody and actual frozen semantic validation
   retain explicit meaning and remove unnecessary translations. Selected.

## Decision

Docling owns native content. Application releases own payload schemas, finite mappings, presence,
validation, relationships and operations. Selected OCR/candidate pages use self-contained Arrow IPC
in existing bounded artifact custody; reports without columnar consumers remain exact JSON.
PostgreSQL enforces custody, release/source/attempt binding, relational integrity and atomic visibility.
The model-bound finite runtime validates actual immutable payload interiors and required closure,
then derives access projections. This deliberately changes independent server interior assurance.
Unchanged JSON families retain their applicable native checks; no blanket extension removal follows.

Exact bytes, typed logical content and exports have separate identities. Runtime recomputation binds
logical payload digests to actual stored bytes. Frozen membership and the admitted validation contract
bind schemas/codecs/projections/dependencies; finalized projection membership cannot change except
identical replay. Existing freeze/validate/seal and recovery remain the only publication lifecycle.

All surviving ADR-0042 semantics remain: one logical integrated document, ordered memberships,
qualified distinct occurrences/references, input/coverage/decision closure, native fidelity and
finite global native callback checks. Unsupported native changes refuse; no semantic section chunks.
ADR-0043 original/raw/logical/export identity distinctions remain. Rebuild current products from
compatible retained evidence; mandatory historical runtime readers/old-layout migrations retire.
Original/raw evidence, exact artifacts, receipts and all committed migrations remain retained.
Independent automated grading and provider fidelity are separate from payload validity.

## Consequences

New writers/readers and native successor revisions must agree on profiles and validation scope.
No system service, generic schema registry or new certificate framework is introduced. Native global
Docling state remains materialized. Acceptance is not implementation; the PDF coordinator owns
actual codec, frozen validation, consumer and adoption evidence.
