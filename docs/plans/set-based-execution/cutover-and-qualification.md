# Cutover and qualification

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how the series lands: the native revisions, regeneration, retirement and the
assembled evidence. It owns SBX-20 to SBX-22 and the shared early integration and change scenarios
used by the preceding packages. Source observations below are **Inspected** at `d36e07594`.
Design and acceptance statements are **Proposed**. The coordinator owns current package state and
[review dispositions](../set-based-execution_2026-11-21.md#post-sbx-01-review-amendment).

## Cutover policy

Direct cutover (operator, 2026-11-21). No compatibility layer and no dual shapes. Products of
every changed kind are regenerated through the new path; retained products of the old shapes are
not read by the new code. Data is regenerable, and the cost of the pivot is regeneration and one
qualification.

**Testing during development** follows the repository's rule: compile checks and targeted
functional tests for the scope just implemented, no integrated gate after a slice. Native
candidates are authored against the working database with rollback-only authoring until a
revision is registered.

Keep one authentic cross-boundary producer, publication and export journey. Reader-only checks
can consume its authenticated artifacts while their producer, prepared release, wire and authority
premises remain applicable. Give these checks independent expected meaning, malformed-input and
current-authority controls. A changed producer or publication contract requires affected production
evidence again. The retained finite and rich result `55f6b07f94bb4ff1ab1ea376e9a4dbef`
establishes that attempt's journey and artifact reuse. It supplies neither final-source qualification
nor a general timing claim. This test allocation applies in SBX-11/12 and SBX-20/22.
[Review I09](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I09)

<a id="early-revision-a-integration"></a>
## Early Revision A integration

Bring one actual annotation-to-canonical chain forward once the minimum SBX-02, SBX-03 and
SBX-05 contracts can express it. Implement any necessary resolver prerequisite before running
the chain. Use the target partition, proof and role-relative reference contracts in the shared
rollback-only native fixture. The path must admit actual producer partitions, require a declared
proof at binding, resolve an item reference, and read the selected result through the owning
disclosure boundary. Later family conversions consume the same contracts.

Compare annotation meaning with an independent expected result. Exercise missing required proof
and dangling-address refusals, then an unchanged repeat. Record which request attachment, proof
and computation reuse behavior the repeat establishes. Retain the exact prepared contracts and
managed result for applicable later reader checks. The existing rollback candidate
`4867ee4d101a4c9c86cd2209e2c5cb40` and 36-case result
`a28f4c6e5c8d44328a780193e99d20ce` establish authoring and synthetic partition behavior only.
This real-chain acceptance remains work for the target contracts.

Run this focused integration before spreading its assumptions through whole producer and consumer
families. It closes the early shared-boundary uncertainty. SBX-20 still owns the single registered
Revision A cutover and SBX-22 the assembled required union.
[Review I05](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I05)

## Native revisions

A revision is needed when installed programs, the physical model, privileges or descriptors
change. A change to the model and Python alone needs the release re-prepared, not a revision.
The current generator embeds a global wire digest in wrappers and descriptors, and application
storage checks that digest. Treat this as part of the deployed boundary when authoring and
comparing candidates.

| Revision | Carries | Why together |
|---|---|---|
| A, identity | Partition table and admission; rule and proof tables, form evaluators, establish routine, required proofs in binding; the reference carrier in admission and completion programs; projection digests in binding and attachment; retirement of the projection family tables, their checks and readers | Each changes what a product body holds or what a request key hashes. Product ids and request keys move once. |
| B, reads | The outputs, partitions, derivation-facts and proofs programs; the support export's relation list; the read closure membership | Group read and export changes. Check their producer identity and receipt effects separately from shared wire and descriptor changes. |
| C, PDF | The paged row read for the rebuild; access derivation and the reduced checker; staging without build columns and the adopt program; typed capture reads | Lowering identity and the standard producer contract move once. |

A, B and C are development strands. A and C can be developed independently. B consumes A's
partition and proof contracts. Author each candidate against its exact predecessor snapshot and
register the resulting chain in dependency order. Candidate effects, including shared descriptor
admission, determine whether a development strand can be installed independently.

Attribute candidate differences to direct SQL or physical changes, shared wire and descriptor
changes, privileges, application admission, and material producer changes. One digest change can
alter otherwise unrelated wrappers. An object diff alone does not establish a need to regenerate
their products. Explain which effects require capture, deployment, admission, or regeneration
through the existing candidate inspection views. Extend those views only if they cannot supply
that answer.

Retain the global digest unless an actual comparison exposes avoidable admission or receipt
invalidation and a narrower contract can independently preserve the required checks. Resolve such
a change through the existing decision route before dependent installation. Compare a read-only
wire change and a material lowering change against their actual predecessors, checking producer
and request identity effects in each case.
[Review I06](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I06)

*Alternative rejected.* A revision per package: each identity-changing package would regenerate
and re-key everything downstream again, and outstanding receipts would be invalidated repeatedly.

<a id="sbx-20"></a>
## SBX-20 — Register the revisions and regenerate

**Order of regeneration.** PDF capture and publication under revision C; then the operation
chains under A in dependency order, each product admitted with its partitions and proofs;
reads and exports under B. The retained book's project binding is recreated, not migrated.

**Checks at each registration.** The repository's native candidate comparison accounts for direct
and shared changes against the exact predecessor. The release prepares under the new kernel,
application admission accepts the intended descriptor, and a fresh target installs from the chain.
Use the existing managed commands to reopen an interrupted transition on the same target. Keep
rollback cleanup and stage receipts within the scope they actually establish.

**Evidence.** For each revision, retain the managed candidate and comparison with attributed
effects, installation on a fresh target, and one run of the smallest
real unit the revision affects (one source view through one chain for A; one selected read and
one export with verification for B; one document's capture, publication, validation and a
recovery for C). Reuse applicable authentic artifacts for reader-only checks under the testing
policy above. Establish same-target interruption recovery for the registered transition. A
rollback-only candidate establishes its captured authoring and validation scope.
Registration, application admission and regenerated production results require their own managed
receipts.

<a id="sbx-21"></a>
## SBX-21 — Retirement sweep

Each package removes what it supersedes. This package removes what no single package owns and
confirms nothing was left behind. Follow the last live production or test consumer of each
retired surface. Migrate independent semantic checks to the replacement before deleting tests
specific to the old mechanism.

- Code with no production caller that the review recorded: `evaluate/record_statistics.py`;
  `evaluate/alignment_preparation.py` and `semantic_values.py` with the parts of
  `semantic_alignment.py` that only they reach; the per-frame identity read; the unused parts of
  `semantic/record_projection.py`, after a reader search at the execution head. The
  `select_pdf_integration` path stays while the streaming reconciliation tests use it as their
  independent check.
- Smaller items: the recognition replay's duplicated sort-key column; the stale duplicate of the
  duckdb hold in `docs/pins.md`; the served-row codec's reference to a disk tier.
- A search, made once and not added to the repository checks, for each retired name: the member
  packet classes, the reference classes, the SQLite read index, the receipt format, the
  projection family tables.
- Design sections and decision records that describe the retired mechanisms are updated in the
  commits that retire them; this package confirms the collection reads true.
- SQLite and JSONL replay controls move to the typed relations in SBX-11/12. SBX-13 keeps
  independent evaluator coordinates and protected-reference controls as duplicate preflight is
  removed. Preserve malformed input, interpretation and current-authority expectations through
  the corresponding replacements.

**Evidence.** Importing every production module succeeds. The searches find no reference to a
retired name outside history. The documentation check passes.

<a id="sbx-22"></a>
## SBX-22 — Assembled qualification

Qualification establishes that the assembled system works and that the design does what it was
built to do. The assembled campaign runs on final source after the revisions are registered.
Targeted development results and reused authentic artifacts contribute only for their applicable
scope and premises.

**Functional.** The repository's functional and check routes on final source, with results
accounted for by identity as the repository requires. Real providers are exercised where the
changed paths reach them: spaCy and HanLP for the first populations, Docling for the PDF path.
Record managed result identities, selected scope, source and context. Account for the required
union through the existing result facilities. Keep failed and interrupted results, and reassess
affected results when source, harness, environment or shared configuration changes. The final
provider and whole-book claims belong to their actual managed runs.

**The whole book.** The retained book is processed end to end through the new path, with a
controlled interruption and an unchanged repeat that produces no new work.

Use the shared [change scenarios](#change-scenarios) throughout implementation and retain their
applicable results for assembled qualification. Derive expected effects from the declarations
and observed checker or consumer boundary before executing a case. Preserve independent
expectations when testing the rule or projection mechanism itself.

<a id="change-scenarios"></a>
### Shared change scenarios

SBX-02 and SBX-06 use this table to select premises before compiling proof and projection
behavior. SBX-03 and SBX-05 supply actual partitions, occurrence acquisition and references.
SBX-07 uses the locality cases to decide host eligibility. SBX-11/12 exercise relation membership,
authority and cache applicability. SBX-20/22 integrate applicable results. The table preserves the
original four scenarios and adds the review's occurrence, population, negative-read and operator
controls. It specifies expected semantic effects rather than a mandatory test per row.
[Review I01–I04](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I02)

| Scenario | Expectation |
|---|---|
| A rule's parameter is edited and the release re-prepared | That rule's fingerprint changes and no other. The establish routine evaluates that rule on each partition once. No product id, request key or other proof moves. No operation re-runs. |
| A model field declaration read by one rule and no consumer is edited | The affected rule's fingerprint changes. Consumer projection identities and request keys remain stable, and no operation re-runs. |
| An upstream product changes only in a field group a consumer does not read | The consumer's request key is unchanged and its existing derivation attaches with no new attempt. A consumer that reads the group re-runs. |
| One block of a source document changes, with other blocks independently matched | Its content digest changes and the matched unchanged blocks retain their content digests. An eligible block-local producer runs for that block when SBX-07 is adopted. Proofs whose complete premises remain stable still match. A consumer that observes the changed whole-collection content re-runs. |
| A block moves under a known key | Content and relative-only premises stay stable. Placement changes. Absolute-position consumers and placement-sensitive proofs observe it. Readback resolves the current occurrence's absolute spans. |
| A reference's body-relative span changes within an unchanged text body | Full-text-only keys stay stable. Consumers of the chosen span get a different key because its position in the body changed. Page-coordinate premises stay stable when page placement is unchanged. |
| Unchanged blocks are reordered | The key-sorted content root stays stable. Placement and order commitments change, along with affected adjacency and ordered-read premises. |
| A block is added or removed, including the empty-population boundary | Existing content digests stay stable. Population membership and affected completeness, absence and neighbourhood premises change. |
| A field-group value changes, including omitted versus explicit null | The affected group changes when its declared meaning observes the distinction. Independent consumer and proof identities stay stable. |
| The first matching proof is attached after a negative read | Rule and content identities can stay stable while proof relation membership changes. A reader of absence or completeness obtains current membership on a cache hit, or that read shape is excluded from answer reuse. Current authority is checked for every call. |
| An equal complete material projection is acquired from another source occurrence | Computation reuse follows the declared operation, parameters, execution policy and read projection. Fresh attachment and publication bind exact current inputs, occurrence and project authority. Check request attachment, computation reuse and proof reuse separately. |
| Reconversion renumbers pointers, with repeated text or split and merged blocks as controls | Equal declared projections can permit computation reuse. A specific occurrence correspondence requires independent evidence. Fresh acquisition supplies current occurrence addresses when correspondence is unavailable. Readback follows the current occurrence without guessing a historical mapping. |
| One role-relative body is consumed through different selections and a transitive input from another demand | Interpretation uses original derivation bindings. Current support checks use the selected use's authority. Exercise revoked original support with valid equivalent current support, revoked current support, an attestation lacking an admissible establishment, revocation between live pages, and protected issuer refusal. Detached verification establishes captured custody. |
| The same block is run with different batch peers and order | Compare independently expected bodies, observations and receipts for the actual host and numerical policy. Keep any observed batch determinant in its key. Unsettled locality retains the whole-collection execution premise. |
| A read-only wire change is compared with a material lowering change | Attribute direct and shared candidate changes, then establish actual producer identity, request identity, admission and receipt effects. Regeneration follows material effects and the registered dependency chain. |
| An installed transition or book run is interrupted and resumed unchanged | Reopen through the existing managed route on the same target. Retain completed applicable work, complete required recovery, and establish that an unchanged repeat creates no new computation work. |

Inspect actual keys, binding decisions and attempts alongside independently expected results. For
proofs, include observed order, placement, membership, source and attestation premises as needed
by the checker. For consumers, include only premises read at the declared boundary. A metadata
projection can serve both paths while each hashes its own observations. Prepare or retain an
immutable whole-collection group root only for an actual repeated consumer whose avoided reads
justify its write and retention responsibility.

**The point check.** A partition-local rule and a single addressed-item lookup each decode at
most one body. Acquire needed metadata and authority through scoped keys. A rule that observes
multiple partitions follows its declared scope. Assert decodes or examined rows where needed to
establish the intended bound. Preserve the full required closure for genuine replay.

**Benefit claims.** Timing and capacity statements require measurements with their conditions.
Functional scenarios can establish avoided operations, evaluations and decodes. Qualitative
execution-fit reasoning is sufficient for expected gains unless a consequential uncertainty needs
a comparison.

**Completion.** The series is complete when the evidence above is recorded, the kernel trial's
decision is recorded, and the owning design sections and decision records describe the
implemented state.
