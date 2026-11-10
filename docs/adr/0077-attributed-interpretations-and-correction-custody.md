---
id: ADR-0077
title: Retain source interpretations separately and make correction custody explicit
status: accepted
date: 2026-11-10
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

DMC-07–16 adds independent review of source terminology and measurement meaning, bounded
correction workflows and offline structural preflight. Source records and corpus-local links
already have distinct authoritative meanings. Validator evidence may contain supplied values.

## Options

1. Add mandatory classified fields to all extracted record families and their producers.
2. Use typed private retained contributions referencing unchanged source records, with compact
query projections for explicitly selected review populations.
3. Merge external mappings into contextual denotes or infer them from lexical lookup.

For correction evidence, compare unconditional raw reports with safe presentations and explicit
opt-in raw custody. Raw engine messages and graphs can contain sensitive input values.

## Decision

Select option2 using the existing RetainedContributionSemantics and sealed task-result boundary.
Authenticate source-result, record/interpretation, field/span and vocabulary pins before native
projection. Source and review results are separately explicit; competing decisions require
selection rather than latest-wins. A lexical candidate establishes neither mapping equivalence
nor accepted knowledge. Unit recognition preserves source value, role and basis; numerical
conversion/classification are not selected.

Capture original validation errors once before flattening. Default correction reports are safe
presentations; exact original engine evidence requires explicit raw opt-in. Inline evidence,
markers and retained managed references have different custody. Retained reads borrow existing
artifact leases and verify content digests; report publication does not turn failed validation
into success. No second evidence store or validator authority is introduced.

Offline export consumes retained validation-schema bytes and promises structural preflight,
not source support, cross-reference truth or native admission. Pinned research comparisons use
authenticated declaration identities under a common released interpretation, never generated
RDF identifiers or endpoint labels. Existing native inference/conformance remains authoritative.

## Consequences

Original extraction can remain unchanged while independently reviewed interpretations evolve.
Compact derived indices select before full evidence hydration, purchasing useful query access
without storing full candidates twice. Typed contributions and their guarded projections require
coordinated native adoption. Safe detail cannot claim to be original raw bytes. Optional raw
custody retains its sensitivity and size constraints. Existing settings init/environment sources
and operation snapshots remain; explanations describe that snapshot rather than later ambient state.

D2/D8 and the DMC coordinator own delivery and qualification. These are accepted targets at
Proposed strength, not implementation claims. Revisit when new interpretation effects exceed
private contributions, a different inference theory is required, or a selected independent
consumer needs executable rather than structural fidelity.
