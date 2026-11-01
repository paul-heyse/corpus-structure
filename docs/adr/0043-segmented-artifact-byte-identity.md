---
id: ADR-0043
title: Separate admitted segmented byte identity from export serialization digests
status: accepted
date: 2026-11-01
supersedes: []
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: A consumer requires PostgreSQL to attest conventional whole-stream SHA-256 for arbitrary new segmented artifacts.
---

## Context

ADR-0042 distinguishes logical record identity, exact retained bytes and export serialization.
Its initial artifact model nevertheless requires conventional serialization SHA-256 for every
new segmented stream. PostgreSQL's current verifier checks actual parts, lengths and canonical
byte folds; it independently verifies conventional SHA-256 only against already admitted bytea.
The operator selected the existing verified byte identity rather than adding a server hashing
facility while approving remaining PDF execution on2026-11-01.

## Options

1. Use the existing model-owned byte-fold identity for new segmented artifacts, preserving exact
   original/raw/historical SHA-256 and computing requested serialization digests incrementally.
   This realizes independent native byte integrity without reconstructing large values.
2. Require an additional vetted PostgreSQL incremental hashing facility for every new artifact.
   No current functional consumer requires this additional deployment and maintenance burden.
3. Label a fold as conventional SHA-256, trust a client claim or concatenate a whole large value.
   These fail the declared identity or streaming contract and are rejected.

## Decision

New segmented streams require actual immutable parts, contiguous inventory, lengths, encoding
profile and independently verified canonical byte folds. Conventional serialization SHA-256 is
optional separately scoped metadata; a supplied value is checked by the exact-byte reader and
must never be represented as PostgreSQL-attested merely because the fold matched. Original/raw
and historical digest custody remains unchanged. Exact retained-byte correspondence compares
actual bytes with admitted custody, not merely matching claimed digests.

Publication admits typed native records and companions; it does not require a submitted whole
native JSON serialization. Explicit exports serialize admitted records and hash emitted bytes.
The root identity protocol remains pdf-record-sha256-fold-v1; this refines optional serialization
metadata, not its framing or historical pins. Implement through new forward migrations and
release-bound contracts; all committed earlier migrations remain frozen.

## Consequences

The new pipeline can publish verified segmented data without another server extension or giant
containers. Consumers distinguish native byte identity from a requested export digest. The
[PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) owns implementation/qualification;
acceptance of this decision alone does not establish publication or deployment.
