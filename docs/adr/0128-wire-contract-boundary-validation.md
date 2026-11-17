---
id: ADR-0128
title: Matching native contract digests place request checks at SQL and result checks at clients
status: accepted
date: 2026-11-17
supersedes: [ADR-0106]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A supported call cannot validate its result before transaction commit or faithfully derive its structural view from the captured protocol.
---

## Context

Accepted PE-S26/27 removes redundant wire checks while retaining both actual authorities: the
client's captured protocol and the contract installed with the release. PE-S01 prepares validators
once per process; PE-S00 established that pg_jsonschema constructs validators per SQL call.
Repeated validation supplies no stronger guarantee when the authorities are known equal. The
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md) owns N2 implementation and
qualification. This record changes validation placement and carries ADR-0106's structural typing,
renewal, notices, invalidation and compiler-retirement decisions without changing §B4/§B5.

## Options

1. Keep both request and result checks at both boundaries. Correct but repeatedly validates the
   same payload without establishing any extra authority correspondence.
2. Keep SQL result validation and remove the client check. This can miss a result inconsistent
   with the actual client's captured contract and weakens the consumer's ingress boundary.
3. Compare installed and client contract digests, then validate SQL requests and client results,
   selected. The result check precedes commit, preserving refusal atomicity while removing work.
4. Replace exact transport with generated runtime Pydantic models. This duplicates Draft7's
   conditional semantics and needs extra absent/default/number tracking; static derived views
   already supply useful type knowledge without another runtime authority.

## Decision

**Proposed accepted target.** PostgreSQL validates every externally callable DDO request against
its installed contract at the security-definer boundary, before effects. A set-form call validates
the complete set once; admitted internal calls do not repeat wire validation. Domain, authorization,
trust, fence and per-item semantic checks remain. Generated wrappers lower one schema constant
per operation and return the installed contract digest in every native envelope.

The client compares that digest with its prepared captured protocol and validates the result
before the calling transaction commits. A mismatch or off-contract result rolls effects back.
Under contract equality it does not repeat its own request-schema validation, and native code
omits redundant result-schema checks. Any path that commits inside its call retains SQL result
validation. Non-DDO generated calls adopt this placement only where SQL input validation exists;
other calls keep both client checks. Exact JSON encodability, absent/null and scope-number meaning,
captured-source custody and original-schema archive decoding remain authoritative. No fallback or
contract negotiation silently accepts a different installed interface.

Captured schemas derive TypedDict/Required/NotRequired/Literal views, explicit model-owned NewType
bindings and fixed named storage methods through existing generation/correspondence custody.
Physical JSON parameters/results remain JSON; Draft7 governs conditional/dependent constraints.
Returned mappings are detached snapshots. SQLAlchemy typed columns/named relational rows remain
static integration mechanisms, not authorization. Set entries reference item operations in that
same protocol; generated item-list/result-or-refusal types introduce no second transport catalogue.

The existing writer pool owns inventory. Reserve one renewal-thread checkout before foreground
admission, keep it transaction-idle between cycles and return it only after its owner stops using
it. Foreground driver/port admission uses explicit remaining capacity; unmanaged/shared engines
need a stated capacity contract. Foreground ports hold no checkout during inference waits. No
extra renewal pool, raised limits or transparent replay of uncertain renewal commits is selected.

Store connections make equal notice registration idempotent through Psycopg's public add/remove
APIs. SQLAlchemy's public invalidate event finishes the borrowed libpq handle so close-returns
cannot reuse a physically invalid session; Psycopg replaces it. SQLAlchemy retains full dialect
initialization. Pool sanitation, extensions, JSON adapters and primary failure/cleanup attribution
keep their existing owners.

Installed legacy relational/interchange compilation retires with its actual helper consumers.
Historical declaration logs retain original producing compiler maps; current identity validation
compares label/content/key scheme, and current artifacts record actual current compiler identities.
This realizes ADR-0024's current interpretation without rewriting historical facts or restoring
installed-only coupling. Current native changes use frozen forward authoring; generation and
registration do not imply deployment. Historical generated bytes do not justify a compatibility
execution path; preservation obligations keep their existing explicit owners.

## Consequences

The two boundaries establish authority equality explicitly and check each incoming payload at its
actual consumer, while preserving rollback on malformed results. Static type views and named
methods remain derived rather than independently maintained interfaces. Renewal and driver
invalidation keep their narrow ownership contracts. N2 must verify malformed input, mismatched
contracts, off-contract results with rolled-back effects, captured paths and applicable set
failure isolation. Native/provider integration and final qualification remain open; acceptance
alone establishes no measured speedup or completed finding.
