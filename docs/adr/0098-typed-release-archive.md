---
id: ADR-0098
title: Release archives use model-owned binary staging and atomic native finalization
status: accepted
date: 2026-11-13
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: An archive column cannot use the existing typed COPY boundary or a supported archive cannot be atomically staged and validated.
---

## Context

Actual DDO original-source qualification failed before admission: the complete release was
hex-encoded into one JSONB argument and exceeded PostgreSQL's 256 MB JSONB object limit
(`7aec18be673345d1b3804674864fc53e`). The largest underlying model artifact was approximately
104 MB; the transport combined and expanded binary values. Removing model detail would weaken
the accepted functional target and would not repair the transport contract.

The persistent development database remains unchanged. The DDO coordinator owns migration,
actual qualification and eventual DDO-11 adoption separately from this decision.

## Options

1. Compress, split or trim the semantic model to fit the old envelope. Trimming loses required
   information; bespoke archive compression changes the durable format to accommodate an
   incidental transport representation. Multiple transport paths add recovery and testing burden.
2. Stream binary columns through temporary typed staging, then finalize through the native
   archive owner. Selected. Existing ArrowWriteProfile/COPY support supplies the binary encoder;
   native validation and atomic visibility stay with the current publisher.
3. Give the client direct writes to permanent archive relations. This reduces staging but
   weakens closed inventory, manifest correspondence and immutable-publication enforcement.

## Decision

The physical domain model marks actual archive relations with `ph:archive_role` (header, input,
artifact or projection). This inventory drives Python stream preparation and native scratch and
publication generation. Intrinsic relations such as runtime bindings remain separate protocols;
immutability alone does not identify an archive relation.

`sem.prepare_release_archive(text)` takes the existing transaction advisory lock and creates or
reuses publisher-owned typed temporary tables with ON COMMIT DROP. The admitting client receives
only the necessary staging privileges. Trusted physical columns derive ArrowWriteProfile schemas
and existing binary COPY encoders. BYTEA stays binary; only actual JSONB columns use JSON text.
The caller performs one existing transaction/savepoint and does not own a new durable staging log.

`sem.publish_release_archive(text)` reauthenticates scratch ownership, exact schema and relation
inventory, release scope and key uniqueness. It inserts in foreign-key order and checks exact
staged/permanent typed row correspondence for publication and replay, including binary bytes.
Digest, manifest, complete archive closure and execution projection checks precede finalization.
Failure rolls back the complete operation. Existing archive bytes, manifests and readers retain
their meanings. The JSONB publication overload is retired through the normal explicit native
inventory delta; it is not retained as a size-dependent fallback.

## Consequences

The replacement removes whole-archive hex expansion and the aggregate JSONB transport limit
while preserving complete model content and one authoritative publication path. Typed temporary
staging adds a bounded SQL ownership/schema responsibility and a second physical copy within one
transaction. It reuses the existing COPY implementation and needs no persistent progress store,
archive codec, provider registry or client-side publication authority.

Eight pure transport/schema controls passed on 2026-11-13 (`cb2a18e138c8476bad054d1079be5d65`).
The combined frozen successor, restricted-role replay/refusal controls and the formerly failing
complete original-source target remain in execution. Improved throughput is an expected qualitative
benefit; neither that size nor full DDO qualification is established by those pure controls.
