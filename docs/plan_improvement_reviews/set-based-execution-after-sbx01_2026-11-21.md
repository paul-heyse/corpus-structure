# Set-based execution after SBX-01

**Inspected · 2026-11-21.** Source and plan baseline `d36e07594`, with a clean tracked tree at entry.
This review covers the remaining SBX-02 through SBX-22 footprint. It uses SBX-00 and SBX-01 as implemented
foundations. Published decisions, implementation, and qualification have separate standing. The retained
66-page census, native partition fixtures, finite and rich exports, and rollback candidate each cover their
recorded scope. No fresh provider or whole-book run was needed for this review. [Coordinator](../plans/set-based-execution_2026-11-21.md) ·
[Entry evidence](../design_review/evidence/2026-11-21_sbx-entry/README.md) ·
[Revision A review F01–F04](../design_review/reviews/design_review_sbx-revision-a-identity-and-authority_2026-11-21.md) ·
[Applicable standard](../design_review/design_principles/standard.toml)

The direct cutover and partition unit remain a coherent design. The highest-value amendments concern the
facts that make reuse sound and the work that has to happen to establish those facts. SBX-01 demonstrated
that content can stay stable while authenticated placement changes. The next packages need to distinguish
content, occurrence, proof, and current support in their actual interfaces. Prove the combined contract on
one real producer chain early in Revision A. Preserve the final integrated qualification and its independent
whole-book evidence. These recommendations apply FP-02, FP-04, FP-06, FP-07 and CI-04/CI-11 at the
affected boundaries. [Design principles](../design_review/design_principles/core/design-principles.md) ·
[Execution-fit heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) ·
[Test assessment](../design_review/design_principles/core/test-assessment.md)

## Identity, proof, and authority

<a id="I01"></a>
### I01 · Give block correspondence and publication context explicit owners

**Observed boundary.** SBX-01's keyed content root and placement root are distinct. The sentence producer
gets its block keys from source node pointers and adds cell suffixes for table blocks. A reconversion may
renumber those pointers. The request key also hashes the complete subject context, including original source
and analyzed scope, so equal input projections can still yield different request keys. The retained sample
supports whole blocks as a physical unit within that sample. It does not establish stable correspondence
between conversions. [Partition identity](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partitions.py#L152) ·
[Block producer](../../python/corpus-structure/src/corpus_structure/semantic/sentence_products.py#L407) ·
[Request identity](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_identity.py#L440) ·
[Subject context](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_model.py#L1168)

**Proposed.** In SBX-03 and SBX-05, let the source acquisition or lowering owner establish the occurrence and
any exact correspondence between source conversions. In SBX-06, keep project, source occurrence, and
publication authority explicit. If SBX-07 is adopted, let a kernel whose declared computation inputs permit
it reuse relative work and publish it under the newly acquired occurrence. This supports targeted reuse
without changing the meaning of an occurrence-bound request or giving the reference resolver a matching
policy. Start with source-local keys and regeneration where correspondence is unavailable. A cross-original
correspondence mechanism earns its cost only for a supported consumer that needs it. Content equality alone
leaves repeated paragraphs, cells with identical text, and split or merged blocks ambiguous.

**Closure.** Pair an unchanged block moved under its retained key with a reconversion that renumbers
pointers. Check relative content, absolute readback, and the identity and authority of the new publication.
Use a second control with repeated text or a split block where unsupported correspondence must regenerate.
State which of request attachment, partition computation reuse, and proof reuse each case establishes.
This refines the existing ADR-0144 revisit condition. [ADR-0144](../adr/0144-sbx-partitioned-products.md) ·
[Memo eligibility](../plans/set-based-execution/references-and-projection-keys.md#sbx-07)

<a id="I02"></a>
### I02 · Make the change scenarios an input to proof and projection design

The plan already says proofs and keys include observed premises. Its fixed three-probe check and its
four final change scenarios leave several of those premises implicit. Give SBX-02 and SBX-06 one shared
set of change scenarios before either package makes its premise selection executable. Derive each
premise from the checker or consumer boundary. A reusable metadata projection can supply the facts for
both paths, while each rule or consumer hashes what it actually reads. A whole-collection field-group
root computed on each request could still scan every partition's metadata. Prepare or retain an immutable
group root only for an actual repeated collection consumer that warrants its write and retention cost.
[Proof premises and lookup](../plans/set-based-execution/populations-rules-and-proofs.md#proofs) ·
[Read projections](../plans/set-based-execution/references-and-projection-keys.md#read-projections) ·
[Qualification scenarios](../plans/set-based-execution/cutover-and-qualification.md#sbx-22)

| Scenario | Expected effect to establish independently |
| --- | --- |
| Relocate a block under a known key | Content and relative-only premises stay stable. Observed placement changes. An absolute-position consumer or proof follows that placement. |
| Reorder unchanged blocks | The key-sorted content root stays stable. The placement/order commitment and an affected adjacency or ordered-read premise change. |
| Add or remove a block | Existing content digests stay stable. Population roots and affected completeness, absence, or neighbourhood premises change. |
| Edit a group or distinguish absent from explicit null | The affected group changes when its declared meaning observes the edit. An independent consumer or proof retains its identity. |
| Change one rule parameter or attach the first matching proof | A parameter edit changes the affected rule fingerprint. Establishing a previously missing proof can change a negative read result even with the same rule and content digests. |

Check keys, actual binding decisions, and attempts. This also supplies a focused case for SBX-12's cache.
For a reader that reports proof absence or completeness, establish the current relation membership on a hit
or omit that read shape from answer reuse. The existing per-call authority check is still required.
[Cache and continuation target](../plans/set-based-execution/owner-resolved-reads.md#target) ·
[ADR-0146](../adr/0146-sbx-content-validity.md)

<a id="I03"></a>
### I03 · Keep proof facts, producing inputs, and current support distinct

**Observed precedent.** The finite archive exposed a real mismatch when detached verification assigned
the export's demand to a nonreusable upstream request. The repaired verifier uses each retained use's
own demand and checks current frontier ownership independently. SBX-05 adds role-relative references
whose historical meaning comes from the producing derivation. SBX-06 permits a different current
selection on an equivalent projection. SBX-07 proposes following the first producing derivation for a
reused partition. The proposed proof table has a content key and also names an establishing derivation.
Those choices need a common authority contract before integration. [SBX-00 evidence](../plans/set-based-execution_2026-11-21.md#sbx-00) ·
[Detached request check](../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py#L984) ·
[Reference target](../plans/set-based-execution/references-and-projection-keys.md#the-reference-model)

**Proposed.** Give resolver and replay interfaces separate typed inputs for original derivation bindings
and current selected support. Clarify in SBX-02 and SBX-04 which native proof conclusions follow from
immutable content and which attested conclusions require an admissible establishment. Examine whether
existing derivation and support facts can carry multiple establishments for one conclusion. Keep the
content key and avoid making whichever derivation established a fact first its permanent authority.
When only an invalid or unavailable establishment exists, binding must follow the relevant rule's
failure policy. Resolve this before SBX-06 or SBX-07 can attach work on equivalent inputs.

**Closure.** Publish a role-relative body once, consume it through two uses with different selections, and
include one transitive input from another demand. Exercise revoked original support with valid equivalent
current support, revoked current support, and a required attestation with no admissible establishment.
Compare live and detached readings under their respective authority. Include revocation between live
pages and the protected issuer case. A detached reproduction establishes captured custody.
[SBX-06 substitution](../plans/set-based-execution/references-and-projection-keys.md#sbx-06) ·
[SBX-12 replay](../plans/set-based-execution/owner-resolved-reads.md#sbx-12)

<a id="I04"></a>
### I04 · Bound preparation and closure work as well as returned rows

The new exact-use lookup reads one index key. The adjacent graph-input path still builds an authority
map by enumerating authority leaves. The private partition routine acquires one body after checking
parent project and kind, and depends on its caller for selected-parent and current-cut authority. The
SBX-05 resolver sketch also needs to specify how a partition lookup establishes that a requested item
exists inside it. [Keyed use and support walk](../../python/corpus-structure/src/corpus_structure/semantic/selected_contribution_input.py#L169) ·
[Private partition read](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partition_native.py#L438) ·
[Reference resolver](../plans/set-based-execution/references-and-projection-keys.md#the-reference-model)

**Proposed.** For SBX-02, SBX-05 and SBX-11/12, define the sufficient facts for each access shape before
choosing the access path. Scope authority and support by the selected parents and traversed edges.
For item references, resolve the address inside one acquired partition or consume an applicable
membership proof that covers the address. Keep the whole required closure for genuine replay. In
partition admission, the current generator walks each item for two distinct schema checks,
then performs group extraction. Before adding rule evaluators, examine which acquired row
representations can be shared within the operation and which checks preserve distinct guarantees.
The current ordered aggregate approach is an existing mechanism to reuse. [Native partition admission](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partition_native.py#L108)

**Closure.** Make an existing partition lack one requested item. Add unrelated partitions, frontier
uses, and protected leaves to the fixture. Verify a point read, an empty answer, and a filtered
continuation with independent expected results and a narrow check for wider acquisition. Measure
decoded bodies or examined rows only where it verifies the intended bound. This promotes H5, H7,
H10, and H19 without adding a repository-wide gate.

## Integration, execution, and test feedback

<a id="I05"></a>
### I05 · Prove one real Revision A chain before converting whole families

SBX-01's managed candidate `4867ee4d101a4c9c86cd2209e2c5cb40` demonstrated rollback-only authoring.
Its 36-case receipt `a28f4c6e5c8d44328a780193e99d20ce` established the synthetic partition contract.
The real SBX-00 export found a cross-demand failure absent from synthetic controls. Bring one real
annotation-to-canonical path forward once the minimum SBX-02, SBX-03 and SBX-05 contracts are runnable.
Give it actual partition admission, a declared proof requirement at binding, one resolved reference,
and selected readback through the owning disclosure boundary. Use the shared contract to build a thin
rollback-only slice. If broader resolver support is required to express this path, do that prerequisite
first. Keep the single registered Revision A cutover in SBX-20. [Execution queue](../plans/set-based-execution_2026-11-21.md#execution-queue) ·
[Native fixture](../../python/corpus-structure/tests/semantic/test_data_product_admission_programs.py#L277)

**Closure.** Use one actual producer fixture with independently expected annotation meaning, one missing
proof or dangling address, and an unchanged repeat. Capture the exact prepared contracts and result
for later reader checks. A failed boundary on this small chain should be diagnosable before the
same assumptions are spread across the producer and consumer families. This moves feedback earlier
without introducing a permanent transitional shape.

<a id="I06"></a>
### I06 · Account for direct and shared effects of native revisions

**Observed coupling.** The generator embeds a global wire contract digest in operation wrappers and
descriptors, and storage rejects a mismatch. The SBX-01 rollback candidate recorded 55 native and
four ordinary operations. Its comparison identified 46 changed native objects, two descriptor
changes, and the partition table privilege change even for this bounded slice. Object diffs alone
cannot identify which products require regeneration. [Wire wrapper generation](../../python/corpus-structure/src/corpus_structure/semantic/native_protocol_authoring.py#L819) ·
[Storage wire check](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_storage.py#L125) ·
[Revision plan](../plans/set-based-execution/cutover-and-qualification.md#native-revisions)

**Proposed.** Keep A, B and C as development strands. Author candidates against exact predecessor
snapshots and attribute direct SQL, shared wire, privilege, application admission, and material
producer effects separately. The current global digest is part of the deployed boundary. Narrow
it only if the actual comparison demonstrates avoidable admission or receipt invalidation and an
independent contract can preserve checks. Keep final regeneration in the existing order from C's
PDF products to A's downstream products and B's reads. Extend the existing candidate inspection
views only where they cannot explain which effect requires capture, deployment, admission, or
regeneration. [Candidate inspection](../../python/corpus-structure/src/corpus_structure/cli/model.py#L1127)

**Closure.** Compare a read-only wire change and a material lowering change against their actual
predecessors. Explain the expanded object changes, verify producer and request identity behavior,
and reopen the interrupted transition through the existing managed commands on the same target.
Use the recorded rollback cleanup and stage evidence within their original scopes.

<a id="I07"></a>
### I07 · Bound validated carrier lifetime and seal PDF transforms before lowering

SBX-08 proposes sharing canonical bytes, a frozen value and lazy derived views. The current cache
charges a weight when it loads an entry. A view added afterwards can retain additional indexes,
Arrow buffers, or Docling objects. SBX-01 also means identical partition content can appear at
multiple placements. Share immutable payload interpretation by content and decoder contract.
Acquire each occurrence's placement, role and authority through its own boundary. Charge derived
state to the existing owner or tie its lifetime to the operation that needs it. Favor the existing
bounded cache and explicit invocation or worker ownership. [Carrier target](../plans/set-based-execution/validated-values-and-handoff.md#target) ·
[Cache insertion weight](../../python/corpus-structure/src/corpus_structure/caches.py#L194)

For SBX-14 through SBX-17, make the validated PDF lifecycle explicit. A transform receives an
acquired source, mutates a private draft, and seals the validated result before it can be reused
by lowering, certification, or access projection. Tie derived byte views to the sealed value.
Keep the captured policy, digest, and file-custody checks across parent, child, and adoption
boundaries. Preserve the stream writer's bounded path when consolidating document rebuild code.
Arrow batches can carry typed staged rows through the existing two-pass design. The existing SQLite
sort remains a candidate if it preserves canonical order with less total integration than the
analytical alternative. [PDF target](../plans/set-based-execution/pdf-path.md#target) ·
[Current transform](../../python/corpus-structure/src/corpus_structure/semantic/pdf_transforms.py#L541) ·
[PyArrow capabilities](../libraries/analytical_infrastructure/pyarrow.md)

**Closure.** Two independent placed uses share one payload decode and resolve different absolute
spans. Closing the owner releases retained views. An alias mutation after sealing cannot change
lowering input. Compare recovery, captured-policy reconstruction, and logical and inventory
digests under the planned file and row formats. Use a real recovered spool for cross-process
custody and the retained numeric fidelity cases for representation.

<a id="I08"></a>
### I08 · Require host-locality evidence and scope analytical resources by job

SBX-07 describes sentence and HanLP outputs as block-local. The newer entry evidence establishes
their input granularity and leaves independence from batch peers open. GLiNER authenticates a
batch commitment and the contextual encoder explicitly declares cohort and order dependence.
Record eligibility per actual host and numerical policy. Compare the same block with different
peers and order, and check bodies, observations, and receipts independently. Keep any observed
batch determinant in the corresponding key. If independence remains uncertain, keep that kernel's
whole-collection execution premise. This bounds SBX-07 to implementations with a demonstrated
benefit. [SBX-00 host evidence](../design_review/evidence/2026-11-21_sbx-entry/README.md#proof-boundary-and-model-host-peers) ·
[Contextual numerical policy](../../python/corpus-structure/src/corpus_structure/methods/contextual_embeddings.py#L46)

Keep SBX-19's scoped-relations trial. SBX-18 can share a worker connection while each job owns
its temporary relations, streams, and cleanup. The existing invocation connection already binds
cleanup to a private spill directory. The installed DuckDB 2.0.0 binding exposes
`DuckDBPyRelation.to_arrow_reader` and `DuckDBPyConnection.interrupt`. Arrow 26.0.0 exposes
`RecordBatchFileReader.get_batch`. The local capability check confirmed those names only. Compare
batch consumption with whole-table materialization for the actual operator and verify
cancellation and cleanup in the actual worker route before relying on them. Match engine threads
and memory to the existing worker policy. Preserve canonical encoding and text rules at the
existing Python seam. [Analytical owner](../../python/corpus-structure/src/corpus_structure/analytics.py#L131) ·
[Trial](../plans/set-based-execution/kernel-trial.md#sbx-19) ·
[DuckDB 2.0 reference](../libraries/analytical_infrastructure/duckdb_2.md)

**Closure.** Two jobs can share the connection while the second cannot reach the first job's
temporary relations or spill. Establish what happens to the current result and resources on
interruption. Judge trial adoption by semantic fidelity, scoped access, and a material reduction
in work or complexity. Replace the mandatory line-count comparison with qualitative reasoning.
Use a timed comparison only if it would decide between plausible implementations.

<a id="I09"></a>
### I09 · Reuse authentic setup and migrate the tests with the mechanism

The genuine finite and rich regression already uses one source. Its retained managed report
`55f6b07f94bb4ff1ab1ea376e9a4dbef` records about 313 seconds of setup and 209 seconds in the test call
for that attempt. Both exports were reused to verify the final keyed reader. That supports retaining
one real cross-boundary journey and using authenticated artifacts for reader-only changes where the
producer, release, wire, and authority premises still apply. Keep independent expected meaning,
malformed input and current-authority controls. A changed production or publication contract needs
affected production evidence again. [Actual native test](../../python/corpus-structure/tests/semantic/test_selected_use_export_native.py) ·
[Test shape inventory](../design_review/evidence/2026-11-21_sbx-entry/shape-baseline.md)

Apply this in SBX-11/12 and SBX-20/22. Move replay controls to the typed relations as SQLite and JSONL
retire. In SBX-13, retain independent evaluator coordinates and protected-reference controls when
removing duplicate preflight. In SBX-21, follow the last consumer of each retired surface and preserve
independent semantic checks through its replacement. Keep whole-book and provider claims with
their final managed runs. This limits recurring setup cost while preserving the observation that
exposed the cross-demand defect.

## Recommended order and decisions

- Settle I01–I04 before SBX-02, SBX-05 and SBX-06 make competing assumptions about premise selection,
  provenance, and keyed reads. I05 is the first integrated feedback once those contracts are
  expressible. The operator decision is whether cross-original work reuse warrants source
  correspondence in this series or remains conditional after source-local partition adoption.
- Align I06 and I09 with candidate integration. Keep one registered identity cutover. If a narrower
  wire closure is proposed, review it through the existing decision route after demonstrating a
  concrete effect. Keep the single native export journey as the regression for actual publication.
- Apply I07 in the carrier and PDF strands as they meet. Use I08 to decide each memo candidate and
  the existing analytical trial. Kernel expansion and an additional analytical storage tier lack a
  supported need in this footprint.

The five initial findings map to I01, I02, I03, I04 and I05 respectively. I06–I09 add rollout,
carrier lifetime, analytical execution, and test improvements. The earlier functional review's
T1–T9, O01–O19, and defect identifiers retain their dispositions in the coordinator. This review
supplies proposed amendments for a subsequent plan revision. [Existing dispositions](../plans/set-based-execution_2026-11-21.md#disposition-of-the-review)
