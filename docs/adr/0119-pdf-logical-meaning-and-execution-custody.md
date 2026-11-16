---
id: ADR-0119
title: Keep PDF logical meaning independent of execution custody
status: accepted
date: 2026-11-16
supersedes: [ADR-0043]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: A supported PDF input kind cannot express its meaning through the current typed logical-reference projection, or a consumer needs a distinct semantic identity rather than exact qualified execution evidence.
---

## Context

The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md#current-consumer-integration-and-discovered-defects--2026-11-16)
owns current PDF integration and reuse. Its target separates canonical result meaning from actual
producing/support episodes. Inspection on2026-11-16 found that the existing logical-record fold
includes application release and physical input/endpoint task addresses. Recognition observations
also retain physical input pins in their exact envelope digest. Equal results under an unrelated
application release or a reclaimed producer therefore need not have equal canonical PDF values.
Simply deleting task-looking fields recursively would erase meaningful unknown metadata.

[D3](../design/D3-database.md#relational-document-realization-and-publication) owns the single
record realization and qualified publication proof. It already retains exact release, task,
build, claim, frozen inventory, publication receipt and input/endpoint foreign-key custody
separately from logical identity. Those protections remain required.

## Options

1. **Keep the current fold.** This is the smallest edit, but execution addresses remain implicit
   semantic determinants and obstruct the accepted current DDO substitution boundary.
2. **Add a second DDO-normalized document/digest.** This could leave the old fold unchanged, but
   would duplicate record interpretation and require every reader, witness and validation callback
   to distinguish two authorities for the same document meaning. No consumer requires that split.
3. **Version the existing logical-record profile and normalize only declared typed references.**
   Selected. One frame owner serves publication and proof reads; exact physical evidence remains
   with its current owners. The integration work reaches writers, native validation and consumers,
   while avoiding another normalized document, store, receipt or compatibility reader.

## Decision

The current-only logical-record profile excludes application release and physical execution
addresses from result meaning. Qualified pins still carry and authenticate their exact release.
Typed input and external endpoint frames bind the authenticated target's actual logical meaning,
including its kind, source, schema and retained recipe qualification where applicable. Preserve
input role, ordinal and multiplicity; relation/occurrence roles and identities; exact source
coordinates, ordering, precision, absent/null distinctions and every meaningful companion value.
Do not recursively strip arbitrary metadata or replace input meaning with original PDF SHA alone.
Each supported input kind needs its actual finite lowering. Recognition inputs consume the one
captured observation-meaning contract together with their authentic raw-source binding; an exact
envelope hash containing physical input pins cannot stand in for that meaning. Existing publication,
selected-support, project/original/scope, endpoint/input correspondence and acyclicity checks remain.

The frozen PDF recipe qualification remains part of the declared publication value. This decision
does not establish equivalence across different numerical/model/recipe policies. Native content
and schema, mapping/coverage semantics and actual recognition/provider observation facts remain
meaning-bearing. The existing private staged record and published-proof owners compute the same
versioned frames. No caller-supplied target hash acquires authority by matching a claim.

Carry forward ADR-0043's separate exact-byte contract unchanged: new segmented streams require
actual immutable parts, contiguous inventory, lengths, encoding profile and independently verified
canonical byte folds. Conventional export serialization SHA is separately scoped; supplied values
are checked against actual emitted/read bytes and are never called PostgreSQL-attested solely
because a fold matched. Original/raw/historical digest custody remains exact. Publication continues
to admit typed records and companions without requiring a whole native JSON serialization.
The scalar/block byte-fold algorithm remains unchanged; the logical-record profile is versioned.

Older publications are never reinterpreted with the new frame profile. Current unsupported profiles
refuse and can be regenerated; immutable frozen migrations, historical evidence and inert data keep
their original meaning. No permanent historical interpreter, migration bridge or fallback is added.

## Consequences

Equal qualified PDF meaning can be reused across different authentic executions without merging
their provenance or laundering revoked support. This is a qualitative expected benefit; no timing
or capacity claim is made. Typed reference normalization adds bounded work to the existing frame
fold instead of introducing a second document materialization. Complete physical custody remains
available for disclosure and independent verification of the selected producing episode.

Acceptance records the target, not completed implementation or qualification. Python/native frame
correspondence, every accepted input kind, exact byte fidelity, independent equality/change/refusal
cases, normal successor capture and actual current consumer/recovery qualification remain with
the DDO coordinator. The older byte-identity decision is superseded with its surviving obligations
restated here; Git preserves its exact original record.
