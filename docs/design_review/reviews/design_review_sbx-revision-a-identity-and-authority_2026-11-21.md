# Revision A partition identity and authority

**Design tier · target purpose · 2026-11-21.** Independent review for SBX-00 and SBX-01 with
the operator's identity and authority focus. Subject is the proposed partition boundary and its
immediate consumers at committed source `cc64bde7c`. The goal is independent admission and
bounded access to one population, with reuse keyed by what changes its meaning. Standard is
core 3.3, efficiency heuristics 1.0, code-intelligence 1.4 and the repository binding. Design
judgments are **Proposed** and current interfaces are **Inspected**. Concurrent implementation,
database behavior, provider output, and final release qualification are outside this evidence.

[SBX coordinator](../../plans/set-based-execution_2026-11-21.md) ·
[Populations, rules and proofs](../../plans/set-based-execution/populations-rules-and-proofs.md) ·
[References and projection keys](../../plans/set-based-execution/references-and-projection-keys.md)

## Decision and diagnostic basis

Preserve the partition architecture and revise the placement commitment and keyed disclosure
contracts before claiming the new boundary. One immutable body per partition fits the workload
and removes the need to reconstruct a population from independently admitted member packets.
The proposal needs to explain separately what makes content equal, what makes its occurrence
equal, and who may see the occurrence. The approved execution plan points in this direction.
The revision must make it executable. Wider proof reuse and projection-keyed derivations retain
their own acceptance in SBX-02 and SBX-06.

The consumed [diagnostic account](../audit/README.md#update-2026-11-18-5139eaba3) is
`568d70596`, audited source `5139eaba3`. The current scoped reconciliation covers these
diagnoses. The published broad baseline retains its original date and coverage.

- DA-068 remains material to installed-kernel integrity. The current canonical value routine
  separately frames individual content identities, giving the partition implementation a
  narrower fact it can reuse. Containment of proof invalidation is a proposed later change.
  [Identity implementation](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_value_native.py#L597)
- DA-071's description of three wholly hand-written realizations has changed. Native traversal
  now reads declared edge names and checks binding endpoints against the declarations. The
  reviewed reader nevertheless still reads a request field that the export omits. It needs the
  exact observed use's selection and must preserve native validity and bounded disclosure.
  [Declared traversal](../../../python/corpus-structure/src/corpus_structure/semantic/support_edges.py#L304) ·
  [Selected contribution reader](../../../python/corpus-structure/src/corpus_structure/semantic/selected_contribution_input.py#L168) ·
  [Selected-support model](../../../python/corpus-structure/src/corpus_structure/model/semantic/selected-support.yaml)
- DA-074 still matters at the new table. Current native projections already distinguish
  static disclosure eligibility from the dynamic kind check. Extend this boundary to keyed
  partitions through the parent and the acquired selection. DA-085/086 point toward compiling
  effective slot declarations once and consuming that result in admission and both carriers.
  [Existing disclosure predicates](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L98) ·
  [Effective kind compilation](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_compilation.py#L310)

## Ownership, fidelity and execution

| Fact or operation | Owner and conditions |
| --- | --- |
| Item shape, field groups, addresses, collection unit | Effective kind compiler over induced LinkML slots. PostgreSQL and Python consume the compiled paths and shape. Key uniqueness and canonical ordering are part of the contract. |
| Partition body and placement | A writer submits relative content and bound placement. Native admission recomputes both commitments, validates the parents and shape, then admits the set in the product transaction. Retry uses exact correspondence. |
| Keyed read | Native read acquisition supplies cut, purpose and visibility. One keyed partition may be decoded after authorization on its parent and occurrence. An undisclosed partition supplies no evidence of absence to that caller. |
| Selected support | The exact fulfilled use supplies current support within the acquired cut. The producing derivation supplies original role inputs for a published body's role-relative addresses. A reused derivation can participate in multiple uses. |
| Proof or reusable result | The later rule or read compiler owns its actual premise. A content digest attests to content correspondence. A proof or reuse decision must additionally bind every fact observed by the rule or projection. |

The existing generated product admission checks subject, kind universe and release, then uses
canonical content identity, exact comparison and one transaction. Extend that owner. An
ordinary reader has no independent authorization to browse the new physical relation. A point
read should fetch one body and keyed metadata. Admission can scan the submitted collection
once, including declaring an empty population where its schema permits it. This separates
feasibility for a selected partition from feasibility for a large publication packet.

[Native admission](../../../python/corpus-structure/src/corpus_structure/semantic/data_product_admission_native.py#L349) ·
[Selected-use projection](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L1597)

## Change scenarios and findings

<a id="F01"></a>

**F01 · Movement and order are real identity premises.** An unchanged block moves with the
same stable key when text is inserted before it. Its relative content, group digests, and
content root stay equal. A reader of the absolute offset observes a new position. Likewise,
reordering two partitions changes an ordered traversal even when the sorted content root is
equal. The written proposal puts extent in the partition header and defines the root only over
key/digest pairs. Complete the contract with a separate authenticated commitment to keyed
placement and ordinal order under the product header. Compare declared ordering and
presence-aware group projections with canonical tagged values in both languages. Record
whether real block keys survive the proposed relocation. Treat unknown correspondence as
unknown until SBX-03 can establish it. Closure for SBX-01 needs move, reorder, corrupt placement
and shuffled transport controls. FP-02/04/07, A1/A2, G2/G6.

<a id="F02"></a>

**F02 · Indexed access requires an admitted and disclosed occurrence.** A caller who knows a
protected product and partition key can otherwise probe existence, receive data, or observe
differences that disclose it. The parent's kind, scope and current visibility govern the
addressed partition; content and group hashes confer no access. Serve the body only after
checking those premises in the acquired cut. Preserve the distinction between an exact retry
and a conflicting publication or partial write. Closure for SBX-01 needs authorized and
unauthorized keyed cases, an unrelated partition control, and failed admission readback
showing atomicity. FP-01/04/05, A2/A4, G1/G3/G5, CI-G2/CI-G3.

<a id="F03"></a>

**F03 · Subsequent proofs and projections need complete read premises.** A placement-sensitive
rule keyed solely on a partition digest keeps matching after a move even though the rule can
observe the new offset. A position- or order-sensitive consumer underkeys in the same case. A
lexical-only rule keyed on the entire body digest over-invalidates when only geometric fields
change. SBX-02 and SBX-06 need a premise derived from the declared rule or projection's groups,
membership, placement, order and external pinned facts to the extent each observes them.
Include order when interpreting a collection through its ordered traversal and include
membership when asserting absence. Keep this premise separate from the rule or projection's
model fingerprint. An opaque or unproven dependency needs a conservative larger premise.
Use two downstream examples for closure: a move that keeps a local lexical proof and changes
an absolute-position key, and an optional field edit that moves only the rules and projections
that observe it. FP-04/07, A1/A2/A4, G2/G6, CI-G1.

<a id="F04"></a>

**F04 · Use, derivation and target roles remain distinct.** Two uses can attach to a single
derivation with different admitted selections. A use-facing reader should consume only its
recorded use selection. A published positional reference still resolves against the original
producing derivation's inputs. A role that admits multiple input occurrences needs a declared
occurrence discriminator or a unique address within its declared domain. Neither first match
nor union of the candidate uses can establish support. Exercise the two-use case through the
actual exported projection for the existing defect. Keep that control through role-relative
reuse and reference resolution in SBX-05 and SBX-06. FP-02/04/06, A2/A3, G1/G2/G6, CI-G1/CI-G2.

## Alternatives and verification

Keep the existing Python canonical encoder and PostgreSQL's generated admission and keyed
relation. A JSON array in the parent would couple access and authentication to scanning and
decoding sibling partitions. Token-per-row storage would purchase per-token database joins,
but the reviewed immediate consumers request blocks and the tagged population carries distinctions
including omission and explicit null. A second authoritative representation would incur a
correspondence obligation. Preserve the declared physical relation and typed program path;
keep engine substitution outside this identity and authority decision.

At admission compare claimed leaf and collection commitments to independently expected
canonical byte fixtures with non-ASCII text, float, decimal, omission and null. Include
duplicate keys or ordinals, inconsistent counts, a one-byte altered body, wrong declared
unit shape, exact retry, and protected or out-of-cut reads. The examples above are proposed
controls. Database commands, tests, providers, and timings are **not_run** for this source
review. Use the rollback-only candidate or test fixture for SBX-01 before the later revision
registration. Review evidence establishes no throughput or whole-book guarantee.

## Gate and architecture judgments

| Gate | Judgment on the proposed boundary |
| --- | --- |
| G1 · Authority | Revise. Keyed read inherits the parent and acquired cut. F02 and F04 settle the affected ownership. |
| G2 · Fidelity | Revise. Authenticate placement and order separately and preserve absence and null. F01 and F04 carry the controls. |
| G3 · Validity | Credible owner. Native admission recomputes claimed structure before settlement. Real native refusal controls remain open. |
| G4 · Hidden behavior | Satisfied in the design boundary. Keyed disclosure is a read; publication and regeneration are separately authorized. |
| G5 · Consistency and recovery | Unresolved in implementation. Verify atomic publication and exact replay under F02. |
| G6 · Transformation and reuse | Revise. F01 and F03 identify omitted or excess determinants. |
| G7 · Capability claims | Satisfied at proposed maturity. The synthetic admission cannot substantiate provider, corpus or downstream reuse claims. |
| G8 · Library leverage | Satisfied in the design. Reuse native authorization, generated relational declarations and the canonical identity primitive. |
| CI-G1 · Fidelity | Revise. A current use, a producing derivation, and an address remain distinct under F03/F04. |
| CI-G2 · Evidence closure | Unresolved in implementation. Pin the selected disclosure and test with exported rows under F02/F04. |
| CI-G3 · Evaluation integrity | Unresolved in implementation. Verify protected-kind access at the inherited purpose boundary under F02. |

A1 has a credible locality route once content, placement and declared reads are distinct.
A2 needs revision for the partition authority and for exact use versus derivation ownership.
A3 is credible inside one compiler and publication authority; the wider role population and
lookup paths have separate acceptance. A4 has a credible bounded point route. Work per point
read depends on the maximum real partition size, and a secondary split may be needed if the
retained census shows dominant blocks. FP-01/03 are
supported by the ownership and composition described above. FP-02/04/05/06/07 retain the
specific fidelity, refusal, locality and workload obligations in F01–F04. Rules and engine
changes outside these obligations were outside the selected focus.

<a id="RC01"></a>

**RC01 · Partition realization and identity.** The partition contract needs a separate
placement/order commitment, block-relative item addresses and fail-closed address resolution.
The coordinator's accepted partition and offset decisions supply the authority route.
Keeping the prior absolute-offset identity would cause a move to invalidate content.

<a id="RC02"></a>

**RC02 · Read and reference authority.** A keyed read requires the existing acquired
visibility authority. Role-relative output and projection reuse change what recorded inputs
establish under the operator's accepted decisions. Keeping current embedded references and
whole product request keys would keep their stronger invalidation and avoid the new binding
obligations. SBX-05/SBX-06 own enactment. Existing native visibility is the preservation
constraint for the SBX-00 repair.

**Disposition.** Revise the scoped target through F01–F04. The corrections preserve the
selected partition architecture and accepted pivot. The [SBX coordinator](../../plans/set-based-execution_2026-11-21.md#execution-queue)
owns follow-up and acceptance. SBX-01 can proceed with the corrected content, placement, and
disclosure contracts while later packages retain their dependent cases.
