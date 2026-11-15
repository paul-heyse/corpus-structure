---
id: ADR-0112
title: CPU execution receipts bind actual reply bytes for native admission
status: accepted
date: 2026-11-15
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: An admission boundary requires independent proof of worker execution beyond the existing trusted runtime, or a declared CPU reply cannot be related to native inputs and outputs without retaining unnecessary private data.
---

## Context

Rich admission must apply the actual numerical reading policy and publish only its justified
lowering. Existing CPU execution receipts retain the request digest and actual process/thread
facts, but have no reply digest. A genuine receipt can therefore accompany a different accepted
body without establishing correspondence to the child result. Retaining an application-result
JSON string alone would leave that gap.

ADR-0109 selects current contracts without legacy compatibility. ADR-0110 preserves native
policy authority and actual library numerical semantics. D6 owns prepared CPU execution; D3 and
DESIGN §B4/§B5 own native publication and the single captured contract. The DDO coordinator
owns implementation and qualification. The receipt is execution evidence outside product identity;
it is not an independent cryptographic attestation of the worker's honesty.

## Options

1. Retain the request-only receipt and trust a parent-supplied acceptance flag or probability.
This is locally simple but does not bind the accepted body to the actual computation. Rejected.
2. Recompute numerical policy application in PostgreSQL. Rejected: a second implementation of
Python/SciPy numerical behavior would add another semantic authority and could disagree on exact
floating-point results. Existing CPU/library ownership is retained.
3. Add signing, a separate attestation service or a general computation-proof protocol. Rejected:
this addresses a different trust requirement and adds operational machinery without a consumer in
this single-operator trusted-runtime design.
4. Extend the existing receipt with the digest of the actual reply, then verify the admission's
finite input/result/output correspondence at its existing native boundary. Selected. This composes
with the current worker, frozen binding, typed body and publication receipt without another queue,
table, registry or evaluation authority.

## Decision

The current `CPUExecutionReceipt` requires `result_digest`, computed from the exact bytes of the
actual `CPUReply.content`. The original request digest and process/thread facts remain unchanged.
The generated execution-evidence schema, structural wire types, captured native sources and real
producer/consumer routes use this one contract. There is no default digest or receipt upgrade from
historical body bytes.

An admission that relies on a CPU decision retains the actual child reply through its declared
result contract and verifies its byte digest against the original execution receipt. The reply
also binds the actual typed inputs processed by the child. Native admission independently derives
the same finite tagged-semantic basis from its frozen binding and actual product/member, context
and support facts, then checks the declared exact projection from that reply to the published
result. Genuine receipts cannot establish a different input basis or a substituted accepted body.
The rich owner defines its typed reply/projection; this decision adds no generic relationship DSL.

The approved CPU implementation remains responsible for numerical application. Native admission
still checks actual factories, recipes, source/reading/issuer lineage, complete populations,
evidence, alternatives, current trust and publication fences. A digest does not replace those
checks or confer authority from possession of bytes. No PostgreSQL numerical approximation,
caller-supplied accepted flag or fabricated receipt substitutes for the actual child result.

## Consequences

The receipt adds a digest rather than a body copy. Hashing traverses the already bounded owned
reply; boundaries that require exact result correspondence retain their actual reply and release
it through their existing custody. Other CPU operations need no additional result archive. The
qualitative benefit is Proposed; no numerical performance or quality improvement is claimed.

The current-only receipt/schema change deliberately refuses missing result digests. Old receipts
remain authentic historical evidence of their original, weaker contract; they are not silently
qualified for current admission. No persistent deployment, activation or conversion is authorized
by this decision.

Shared receipt propagation, real worker checks, substituted-result/basis refusals and complete
rich admission/public/native qualification remain with the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md). Acceptance records the contract
in force and does not close those implementation obligations.
