---
id: ADR-0063
title: Semantic releases retain data meaning while immutable runtimes pin execution provenance
status: accepted
date: 2026-11-05
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A runtime-only repair changes semantic identity, a meaning-bearing asset escapes semantic preparation, or execution can reuse a result without its producing runtime compatibility.
---

## Context

A two-line source-read budget repair changed the statistics semantic release from `caa1093…`
to `6357cce…`, despite unchanged data contracts, parsing and output meaning. Executable bytes
were included in both execution-model identity and the semantic dependency manifest. The
operator directed correction on2026-11-05: operational repairs must not manufacture new data
meaning or require reference/data regeneration solely because code bytes changed.

ADR-0031 already distinguishes byte-producing determinants from runtime/deployment compatibility.
The implementation mixed those responsibilities in one immutable archive. The
[PCE coordinator](../plans/progressive-corpus-enrichment_2026-11-04.md) owns this correction and
its actual integration/qualification; this decision accepts the target, not completed behavior.

## Options

1. Exclude the budget function or filter Python ASTs. Rejected: neither establishes semantic
   equivalence through imports, grammar/model data and package behavior. A one-file exception
   leaves the governing identity mistake in place.
2. Append alternate executable bytes to release-keyed inputs/artifacts. Rejected: those sets
   are closed and intrinsically immutable. Changing their membership for an unchanged release
   creates competing writable meanings and breaks archive verification.
3. Separate semantic determinants and immutable runtime bindings. Selected: one additional
   intrinsic relation and a run pin preserve reproducible execution without changing the semantic
   archive for an operational repair. Store each runtime archive once; start/claim compare compact
   identities rather than repeatedly transferring the source archive.

## Decision

The semantic release owns data definitions, vocabularies, constraints, source/output contracts,
operation/effect compatibility versions and positively declared parsing grammar/model assets.
`contracts.SEMANTIC_IMPLEMENTATION_NAMES` declares the existing mixed-input assets that actually
belong to this responsibility. A new asset needs an explicit role. Executable Python/SQL source
provenance belongs to the runtime binding, including the complete owned executable package.
Content produced by an operation still has its own source/result identity; a new result does not
by itself imply a new model. A changed interpretation/output contract requires its declared
semantic revision rather than relying on an incidental source-file hash to version meaning.

`runtime_bindings` prepares a versioned exact manifest and source archive, authenticates its
semantic determinants against the supplied release, and derives an independent runtime identity.
`sem.runtime_binding` stores that immutable binding once under the same release. New runs pin
`ops.run.runtime_id` through a same-release foreign key. Owned native registration authenticates
the archive and contract, and native run creation requires its registered pin. Existing exact
native deployment, ownership, ACL and operation/effect support checks remain authoritative.

Execution compares the installed runtime with the producing pin at its start/claim boundary.
Task reuse also respects runtime identity; separating semantic identity does not authorize reuse
across changed executable bytes. Analysis context/cache and renderer provenance retain runtime
identity independently of semantic identity. Selected readers/exports preserve the actual producing
runtime; a current interpreter never rewrites that provenance. A source archive establishes
attributable custody, not a proof that its code executed or that its outputs are correct.

Semantic compiler17/execution compiler27 introduce this identity scheme. This is a one-time
forward format/model transition; existing release IDs, archives, reports, grades and runs remain
unchanged. Old runs retain exact embedded executable provenance in their historical release
archive and are readable through that owner. They are not backfilled from current code or
automatically authorized for new execution. New runtime storage/pins use a forward migration;
frozen predecessors remain immutable. ADR-0031's archive opening and ADR-0047's current-runtime
and explicit compatibility constraints remain in force.

## Consequences

Budget/transport/lifecycle repairs can create a new execution fingerprint without changing the
meaning or identity of data. Schema, grammar, model and declared behavior changes still invalidate
semantic identity where they affect interpretation. Exact runtime mismatch refuses execution and
reuse until a compatible runtime is explicitly selected; no universal equivalence engine is added.

The split requires coherent compiler, storage, run, cache, renderer and provenance-reader changes.
Independent acceptance must demonstrate the actual budget repair's identity invariance, distinct
runtime pins for one unchanged semantic archive, rejection of altered/incompatible runtime custody,
proper cache/reuse invalidation and faithful old archive reading. Actual PCE assessment resumes
after this correction; earlier completed/failed attempts retain their original scope. Implementation
and testing are tracked by the PCE coordinator, not inferred from this accepted decision.
