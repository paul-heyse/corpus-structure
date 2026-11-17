---
id: ADR-0130
title: Certify PDF output at the producer and qualify reconstruction per lowering identity
status: accepted
date: 2026-11-17
supersedes: [ADR-0045]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A reader or oracle reveals a shape-specific lowering defect, the captured lowering identity omits a determinant, or a consumer requires independent reconstruction of every publication.
---

## Context

The record path currently reconstructs each frozen publication in a separate child and performs
its complete output certification there. PE-S36 moves that certification to the producer, where
the document and exact encoded payload already exist, while PostgreSQL keeps stored-byte,
structural and correspondence checks. The accepted target deliberately changes independent
reconstruction assurance; this record preserves every other ADR-0045 contract below.

## Options

1. Keep independent reconstruction for every publication. It gives the strongest routine
content-specific round-trip check, but repeatedly transfers, reconstructs and callback-validates
a document whose producer already holds it. Retain this as the explicit oracle, not the ordinary
publication path.
2. Producer certification alone removes that repetition but never establishes reconstruction
fidelity. Rejected.
3. Producer certification on every publication, database checks on the frozen stored content,
and a reconstruction oracle per captured lowering identity/kind preserve a concrete fidelity
check without a second complete routine materialization. Selected. A content-specific lowering
defect outside the oracle's shapes can remain until a reader, explicit verification or DDO-12
finds it. This is an accepted assurance weakening (DP-23), not an equivalence claim.

## Decision

**Accepted target; implementation and qualification Proposed.** The producer performs native
callbacks over its actual output document and validates payload interiors, metadata and integrated
meaning over the exact encoded bytes it stages. It derives access/region projections from that
same document before freeze and computes the logical digest with the existing Python frame fold.

PostgreSQL checks stored bytes against staged roots, frozen membership, structural closure,
producer-derived access correspondence, native identity/projection and metadata schemas. Seal
requires its logical identity to equal the producer's attested logical digest. Freeze, validate,
then seal remains the only publication lifecycle; producer success does not permit mutable frozen
membership.

The publication receipt states producer-certified versus round-trip-verified basis, the lowering
identity, attested logical digest and any passed oracle receipt relied on. The lowering identity
is a release-captured contract over the record lowering/reconstruction sources and their actual
schema/codec/library determinants. A current-checkout digest or unrelated release identity is
insufficient. Establish the complete captured source closure before using it as an oracle key.

The existing reconstruct-from-frozen-rows child runs before the first sealed publication of each
kind under a lowering identity lacking a passed oracle receipt. Explicit `ci` verification and
DDO-12 also run it. Failed/interrupted oracle records remain truthful and cannot supply a passed
receipt. Subsequent ordinary publications with that exact qualified identity/kind use producer
certification plus the independent database checks. A shape-specific defect can invalidate that
qualification and requires investigation and correction under the owning DDO plan.

The following surviving decisions remain in force:

Docling owns native content. Application releases own payload schemas, finite mappings, presence,
validation, relationships and operations. Selected OCR/candidate pages use self-contained Arrow IPC
in existing bounded artifact custody; reports without columnar consumers remain exact JSON.
PostgreSQL enforces custody, release/source/attempt binding, relational integrity and atomic visibility.
The model-bound producer validates actual immutable payload interiors and required closure,
then derives access projections as specified above. This deliberately changes independent server interior assurance.
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

Ordinary publication avoids a second complete reconstruction while retaining exact producer
certification and database checks. Reconstruction assurance is qualified by the stated oracle
coverage; no fresh-GPU byte equality, provider fidelity, linguistic accuracy or performance amount
is promised. No generic certificate registry or system service is added. Existing publication,
validation and managed-result custody own receipts and their lifecycle.

[DDO PE-S36](../plans/declared-data-operations/operations-and-adapter-cutover.md#pe-s36--producer-certification-and-the-round-trip-oracle-pe-f26-pe-rc06)
owns implementation, actual stored-byte/tamper controls, first-oracle/explicit verification,
consumer migration and retirement of unconditional read-back certification. Acceptance of this
record does not establish that those changes are implemented or qualified.
