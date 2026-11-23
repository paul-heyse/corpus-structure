---
id: ADR-0154
title: Carry SBX populations as typed relations through native item admission
status: accepted
date: 2026-11-23
supersedes: [ADR-0144, ADR-0145, ADR-0148]
superseded-by: null
design: [§B1, §B2, §B4, §B5, §B6]
evidence: Proposed
revisit: A supported population cannot preserve exact canonical identity, declared-rule authority or recoverable publication through the shared typed boundary.
---

## Context

The operator approved all five columnar rule changes on 2026-11-23. SBX already makes
partitions the unit of content identity, proof and reuse, and PostgreSQL owns transactional
admission and current support. The implemented population carrier still builds tagged
packets that producers, workers, native rules and readers expand and reconstruct. Native
rules and references consume item fields relationally, meeting the earlier storage decision's
revisit condition. The target moves acquisition, storage and consumers together.

The independent reviews and their reconciled plan establish the intended scope. Their
retained controls establish limited identity parity, typed transaction feasibility and
library behavior. The current registered root uses the preceding physical design.
[Reconciled findings](../plans/set-based-execution_2026-11-21.md#columnar-redesign-amendment) ·
[Typed population target](../plans/set-based-execution/common-analytical-basis.md#columnar-population-target) ·
[Focused target review](../design_review/reviews/design_review_sbx-columnar-target_2026-11-23.md)

## Options

1. Retain the current immutable packet carrier and optimize individual decoding and rule
   passes. It has established scoped evidence and improves sparse operations. Bulk routes
   continue to build tagged documents before later consumers recover columns.
2. Use a typed relation end to end for affected populations, generic native item rows and
   one controlled canonical encoding boundary. This removes those conversion stages and
   gives native rules and keyed readers direct access. It requires coordinated compiler,
   storage, wire, worker and consumer migration and renewed affected qualification.
3. Introduce independent per-family storage tables or a second durable analytical authority.
   These can offer specialized access, while adding schema ownership, registration or
   coordination that the present generic population responsibility does not require.

Select option 2. FP-04, FP-07 and DP-10 favor one model-derived representation with execution
units chosen for the workload. The design carries distinct authority and identity facts
through shared physical work. Exact behavior and recovery remain independently verified.

## Decision

**Partitions and storage.** A homogeneous collection declares its key, order, item address,
field groups and rules in the effective model. A partition remains the unit of identity,
proof and reuse. Generic logged item rows hold canonical item text and declaration-derived
rule and address fields under a retained parent keyed by completion intent and output
role/position, with collection and partition beneath it. That parent exists before product
visibility and remains distinct from the final logical product identity. Publication adds
the visible product/derivation association and promotes the same logged rows. Immutable keys and commitments are independent
of retained/published lifecycle state. The native authority admits each canonical item once
and derives its rule/address projections or verifies supplied projections exactly before
using them. It recomputes partition, field-group, count and root commitments from admitted
ordered items. Individually identified and bound graph members retain their addressed unit.
[Admission owner](../plans/set-based-execution/populations-rules-and-proofs.md#typed-item-admission)

Relative item coordinates and stable local content remain distinct from authenticated
absolute placement and ordinal order. A complete declared read projection determines a
consumer's input identity and the fields it receives. Current use records the selected
inputs while the producing derivation records the equivalent original inputs. Equal local
content permits computation reuse under its declared dependencies. It does not establish
occurrence correspondence across renamed, repeated, split or merged source pieces. A
reference names its declared producing input role and address, with an occurrence
discriminator where needed. Disclosure checks the exact current parent and use authority.
Unknown dependencies conservatively widen the premise.

**Wire and retention.** Population-bearing operations use model-derived typed upload and
result/refusal relations. Small control calls retain their document contracts. The native
boundary authenticates the actual session-private intake, resets it for the preparation,
checks its catalog shape and owner and rechecks the attempt after COPY. Psycopg and pgpq
use the existing SQLAlchemy transaction. A protected routine inserts admitted rows into
logged retained storage and binds request, attempt, release and commitments. Client and
installed contract correspondence and result validation precede commit. A typed refusal
must roll back that item's effects. Publication rechecks mutable support, claim fences,
references and proof standing at its effect boundary. Exact already-committed replay is
recognized under replay authority before requiring a fresh producing claim. Lost
acknowledgement and restart recover the retained identity without reconstructing payloads.

This qualifies ADR-0128's physical JSON parameter/result clause only for the affected
population-bearing operations. Its remaining request/result validation placement, renewal
checkout, pool lifecycle, invalidation, captured compiler and historical provenance rules
continue to govern. Generated typed wire shapes supply no independent authorization.

**Carrier and custody.** Derive Arrow schemas and acquired projections from the effective
model, including distinct optional-value states and exact canonical lexical scalars where
native types cannot preserve meaning. Validating constructors establish facts for an owned,
immutable typed value. Compatible in-process consumers share its buffers and derived views
for their actual lifetime. Applicable process boundaries use sealed Arrow IPC bound to
request, schema and logical commitments, with owned mappings and files retained through
acceptance and released on cancellation or completion. Transport bytes authenticate the
transfer, while canonical commitments establish logical identity. Prepare each loaded-code
slice once and verify before computation submission and after reply collection, including
late imports. Native current support, fencing and publication keep their effect owners.
[Custody owner](../plans/set-based-execution/validated-values-and-handoff.md#typed-worker-custody)

**Identity and engine.** Preserve the existing canonical identity definition and the Python
reference. For the affected SBX populations, model-generated engine expressions may frame
canonical item text and compute ordered aggregate commitments after exact parity is
established for every supported value form. Hard scalars enter as their exact canonical
spelling. The generator covers its admitted tag set or refuses generation. Expression text,
chunking, dictionary layout and IPC bytes are outside semantic content identity. This is
a scoped exception to ADR-0021's Python-only canonical production rule. Its PostgreSQL
instance authority, model authority, consolidation pool, deterministic set semantics,
reference parity and deployment-settings decisions continue to govern.

DuckDB owns composed local relational work through the existing analytical owner. Arrow
owns typed representation, IPC and appropriate direct column kernels. Acero is conditional
on a named stream responsibility with established buffering and cleanup. PostgreSQL
establishes declared-rule facts. Producers establish attested rules under their captured
checker identities. Independent rule conclusions and establishments remain distinct even
when their computation shares preparation. Eligible committed bulk reads use ADBC under
the existing exact exported/imported snapshot owner. Uncommitted and temporary archive
state is read through the owning PostgreSQL session.

**Adoption.** Bring the consumed SBX-18 fidelity, query-custody and resource prerequisites
forward for annotation through canonical publication and construction. Extend the shared
boundary to HanLP/declaration and affected member adapters, worker input, selected readback
and authentic finite/rich replay before authoring the replacement root. The complete
scoped-relations trial remains SBX-19 and ends in its own adopt, adjust or stop decision.
Its independent expected results, explicit order and phase semantics remain required.
Python text and identity operations stay with their existing owners outside the explicitly
approved population scope. Full PDF certification and general read programs retain their
later package ownership.

## Consequences

The same population can supply worker transforms, proof premises, native set admission and
keyed reads without reconstructing a tagged transport document at each boundary. Canonical
item validation still costs work at admission. Generic row storage and an explicit retained
parent add relational lifecycle decisions and exact field correspondence checks. Bounded
ordered digest aggregation must fit the supported partition shape. Reader output alone
does not bound joins, sorts, aggregates or retained backing buffers.

Implementation and qualification remain open. Acceptance of this record establishes the operator-approved target. It supersedes
ADR-0144, ADR-0145 and ADR-0148 and carries their surviving partition identity, reference,
projection, custody, verification and scoped-relations trial decisions above. It qualifies
only the SBX population wire clause of ADR-0128 and canonical production clause of ADR-0021.
Their other decisions remain in force. Referenced predecessors remain readable during
consumer-reference migration. The plan owns current finding disposition and the cutover sequence.
Qualification stays paused until its owner authorizes the bounded resumed cohort. Earlier
receipts retain source, root, harness and provider limits. No production performance claim
follows from this decision. The approved empty development reset follows integrated
acceptance under ADR-0150. [Execution and acceptance](../plans/set-based-execution/cutover-and-qualification.md#columnar-cutover-sequence)
