# Cutover and qualification

**Status:** The early producer chain passed in a private target. The cold-root rehearsal
registered and installed the replacement on an empty database. Integrated acceptance remains open.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how the series lands: the native revisions, regeneration, retirement and the
assembled evidence. It owns SBX-20 to SBX-22 and the shared early integration and change scenarios
used by the preceding packages. Source observations below are **Inspected** at `d36e07594`.
Design and acceptance statements are **Proposed**. The [coordinator](../set-based-execution_2026-11-21.md)
owns current package state and review dispositions.

## Cutover policy

The operator authorized an empty development database for the hard cutover through SBX-09
on 2026-11-21. Discard the old development data, including source and derived rows. Work on
clean native targets with new fixtures and delete superseded runtime paths as their replacements
land. Development acceptance requires no backup, migration, restore, backfill or regeneration.
All originals, selections and derived rows in development are disposable. Managed evidence
keeps its recorded standing.
Stage installation belongs to [SBX-20](#sbx-20).

**Testing during development** follows the repository's rule: compile checks and targeted
functional tests for the scope just implemented. For this cutover, author a cold root from
the integrated source against an empty authoring target on the dedicated PostgreSQL cluster.

### Development reset through SBX-09

1. Decide the [typed population pilot](common-analytical-basis.md#typed-population-pilot),
   integrate its chosen route and affected consumers, and finish the functional changes through
   SBX-09. Run their scoped checks. Retire the active
   legacy Alembic chain and its predecessor-specific data-step code. Preserve generic successor
   authoring. Record the old stage predecessor and its Git baseline for SBX-20. Create an empty
   authoring database on `18/corpus` with `uv run ci db init --creation-only`. Bind the reader
   and maintenance settings to it. Run `uv run ci model change preview`, `candidate` and
   `inspect-candidate` for `semantic_sbx_current_root` with a null predecessor and zero data steps.
   Confirm captured source, descriptor, objects, grants and rollback. Register the inspected
   candidate with `uv run ci model change register` and install it with `uv run ci db init` on
   a separate fresh qualification target. Confirm the sole head, exact descriptor and purpose-role behavior.
2. Run `just turn-end` before final-source qualification. Run `uv run ci test` and
   `uv run ci check` for the applicable ordinary and shared fault scope. Use
   `uv run ci test --providers-only` for changed real annotation and canonical, HanLP
   declaration, construction, learned definition, contextual, protected reference and PDF
   provider paths. Use private native runs for isolated journeys, and the dedicated shared
   host for shared authentication and durability. Run the ordinary executor against fresh
   fixtures through the committed propagation, binding, recovery, memo and hand-off scenarios.
   Exercise the chosen annotation fork through publication and exact selected readback, including
   the relevant occurrence, support, provider and worker controls. Keep one authentic finite and
   rich publication-to-export replay. Record managed IDs,
   selected identities, exact source, revision and context. Preserve failed and interrupted
   results and reconcile retries by identity. Complete required acceptance before resetting.
3. Recheck the dedicated cluster and the exact `corpus_structure_dev` maintenance identity
   with `ci host status` and `ci db status --maintenance`. Drain its writers and sessions.
   Drop only that database from the verified cluster's maintenance database without force.
   Recreate with `uv run ci db init`. After interruption, reread acquired state and resume
   initialization on the same target. Verify the new database identity, installed native
   revision, descriptor, roles, and empty project, source, demand and product relations.
   Keep qualification fixture data on qualification targets. Stage installation belongs to
   SBX-20. Record the acceptance and reset in the coordinator and status checkpoint.

**Cold authoring checkpoint · 2026-11-21.** `uv run ci db init --creation-only` created
`corpus_structure_sbx09_author` on the dedicated cluster. Managed preview
`038a531859e443c19f46429255d4876f` and rollback-only candidate
`9d52c84a67124150a960535150fd60e5` passed for a null predecessor and zero data steps. Candidate
inspection identified the active N47 migration head as the remaining registration conflict for
this preliminary source. The exact integrated source needs its own candidate and cold install.

The follow-up `uv run ci model change candidate` passed rollback-only authoring on the same
empty target after native pending discovery, indexed adoption and construction source proofs
(`ac0c58dfeee945d587966c7c69c29bda`, preview `aa4c26a371534e2990b1eb911fc221e3`).

**Cold installation rehearsal · 2026-11-21.** The isolated checkout retired 256
frozen predecessor files, five revision data-step builders, and the native re-lowering entry
point used by the old data steps. Generic native successor authoring remains available.
`uv run ci model change candidate` passed (`8fa321fb099d4a5b9175279ba5dac76f`,
preview `42df5b1b7dd541d397f522020c8e2db2`).
`uv run ci model change register` registered the sole null-predecessor root in that
checkout (`3c8d0725d0b34912b5f2860699486a0d`).
`uv run ci db init` installed `semantic_sbx_current_root` on the empty
`corpus_structure_sbx09_cold` database. This rehearsal predates the remaining SBX-06
and SBX-08/09 integration. Main registration and the development reset stay open.

The next isolated build compared the native stored empty-collection default in online
inspection and detached export. Candidate `0b87567e253a4cb699ee9d3b22f1fdfc` and
registration `54656b69aedd4bfb9afa2fd20750778e` passed. `uv run ci db init`
installed the refreshed root on a second empty rehearsal database. The targeted native
run `037643e85d0a48daad9cfb3b0c35d2dc` passed 36 cases, including installed reader
correspondence, detached export replay and changed-child population reuse. One controlled
composition case reached an analytical provider before it could check the selected source
population. Its fixture now stops at the actual source-view publication boundary. Retry
that case against the next integrated root.

A subsequent isolated checkout containing the newer native demand and proof changes passed
preview `b7ee66f404f44834b5976bc30bb12768`, null-predecessor candidate
`7e1e964fbc534356b5bd6bf70b640d5a` and registration `3ae875080cb74428bb24e1ce1e21fa68`.
It retained one active root. The installed ordinary scope and later source changes still need
integrated evidence before replacing development.

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
managed result for applicable later reader checks. The initial rollback candidate
`4867ee4d101a4c9c86cd2209e2c5cb40` and 36-case result
`a28f4c6e5c8d44328a780193e99d20ce` covered authoring and synthetic partition behavior.

**Implementation checkpoint · 2026-11-21.** The generated N47 successor passed rollback-only
authoring (`c9a513040006422ebcb309693bc15ce5`). The owned source-to-canonical journey installed
the target schema and exercised initial source execution. Target release admission then refused a
shape constraint on an unowned graph class (`8772530274a94525bf9211e712cc4393`). Sentence
partition rows and their carrier now belong to private record products, so their constraints are
enforced by product and partition admission. `uv run ci test --providers-only` then passed the
real CUDA spaCy-to-canonical demand on the owned PostgreSQL target
(`e31433142bf1414ead8712101131dccd`). The proof-requiring canonical role consumed the admitted
annotation partitions. The test read both outputs through selected support disclosure and checked
the literal sentences, projected token offsets, and the role-relative addresses. An unchanged
repeat of the same demand produced zero new receipts. Focused native controls separately refuse a
missing or forged required proof and a dangling partition item
(`85e9b6137e904489b262743b66ceb23c`). Cross-selection reuse and complete family migration
remain separate obligations.

The chain passed again after adding current-use producing input metadata
(`c285558d8dc04e8a9256fe399e655bfb`). The successor candidate for that scope passed rollback-only
authoring against N47 (`27c37c0e9aaa403ebbb53817d6cee671`).
The extended real spaCy, canonical, HanLP and declaration syntax chain verified complete HanLP
output and admitted syntax coverage. The same demand repeated with zero new receipts
(`ce9ecaff99cb4d2c9ce00cfdd29fdc05`).
The extended chain passed again after retiring the annotation packet types and moving the source
witness to the actual block layout path (`b487ae1c0fc340c983cff21339a58c1c`).
The successor with grouped ordinal admission, scoped construction proofs, and clause and condition
references passed preview and rollback-only authoring against N47
(`87857b59d542418f862b1636429cac00`, `345c61ef93b247d09e166540a72d6191`).
Rollback-only authoring after the construction reference and annotation packet changes passed
against N47 (`eafcec5626fc4f11a652f2cc835b8714`). Maintenance readback reported development N29 and
stage N47.
The successor with disclosure-aware support export passed preview and rollback-only authoring
(`1df6637ca17049f492bfbac36b011a44`, `d36ce26f134c4fa3b08001c29f9ee61b`).
The candidate also passed with formal roster and member-address attestations and the new
construction input requirements (`d27bda9ca1db47f7891adf4964bef7a4`,
`6ef50175ca1b4243b1621a6f78cf06c7`).
The successor with the regenerated report schemas and selected rich read authority passed
preview and rollback-only authoring (`e144d0867344411ab6fe1b96eef1c015`,
`31a8c3350bfa478da58f8a4caf3bab85`).

**Projection and activation checkpoint · 2026-11-21.** The partial integrated source at
`2375de39b` passed managed rollback-only authoring against the exact N47 predecessor
(`uv run ci model change candidate`, `359a2c8ce289405cb53ee328fa894b38`). The authoring
database was the dedicated development target at N29. The earlier attempt
(`f93d402290d84b2e89575bb2235725f6`) refused the missing explicit retirement list.
The retry named only the recorded immutability triggers on the five retired projection
families. The result describes the captured source and authoring boundary. Later program
and schema changes require their own candidate comparison.

The next checkpoint at `38c12391d` passed rollback-only candidate authoring with immutable
canonical computation bases and the exact named publication and reconciliation relations
(`uv run ci model change preview` `ec360bd003474cae84c83ad42a6eea0e` and
`uv run ci model change candidate` `e8564e0d615340cdb66544dca5d7492a`).
`uv run ci model change inspect-candidate` confirmed N47 as the predecessor. Maintenance
readback confirmed the stage remains at N47.

The source at `3f413bbac` also passed rollback-only authoring with the native one-hop
recipient routine and its writer grant, the role-relative clause anchor and broader
formal rule consumers (`uv run ci model change preview` `110674f50a8241f59d5f02d2e00e4bae`,
`uv run ci model change candidate` `8db1a135ce6b41c48ada8895b0b00d2e`).
The inspected candidate retained the exact N47 predecessor.

The authorized source-universe routing correction at `fadf20e0f` passed rollback-only
authoring (`uv run ci model change candidate` `d7916674edf74a5d97a9c293f47eb49d`) and
both exact canonical and HanLP provider cases on private PostgreSQL
(`uv run ci test --providers-only` `0828f95372a34af7ab77c094850c6768`).
The exact selected-output validity correction at `ba5a17c10` passed rollback-only
authoring against N47 (`uv run ci model change preview` `e02b3da039824e3d83598f94d8751a46`,
`uv run ci model change candidate` `2b9add969deb46b08cc02aa638337831`).
The same source passed all 13 selected native source-proof, publication, computation-key and
executor controls (`uv run ci test`, `ada90cfedcbe4a878b1e7563c80d4415`).
The live canonical and HanLP cases passed on that source
(`uv run ci test --providers-only`, `cee750ab2b274d66bed4bf20f3ee3cff`).
Maintenance readback reported development N29 and stage N47.

The consolidated CPU and executor selection passed 39 tests (`uv run ci test`,
`8dee86b4b0ba425aaf2b3aa418cae2ac`). Some earlier isolated receipts stopped being
queryable when their worktrees were removed. Current retained results supply new verification
for the covered slices. The 45-case private run `924a287626da4b85b8f4243e181ec265` retained
its failed outcome when a synthetic fixture left temporary source files. Recovery settled
process custody and `uv run ci test coverage` found all 45 selected tests passed. The fixture
lifetime repair passed all five private executor controls with clean teardown
(`6a67b97f41344d459afeed333fd7972d`). The wider fixture run also cleaned up and reported
two executor collaborator failures against fixtures that use the older preparation interface
(`59f7534a27d848d88e07b031de4bb3b9`).

These results establish the early partition, proof and reference path for the tested chain.
The development reset above establishes the fresh SBX-09 baseline. SBX-20 owns stage installation
and SBX-22 owns the assembled required union.
[Review I05](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I05)

**Next early slice · Proposed.** Extend the same annotation-to-canonical chain after the
relevant SBX-03–05 contracts are runnable. On a fresh target, drive a governed commit through native
delivery, current binding and settlement. Check that an unread lexical edit preserves canonical
computation and that a materially changed producer can settle an equal declared output with no
downstream attempt. Contrast the local-geometry case with a moved block whose observed placement
changes the assembled canonical projection. Use native coverage and selected readback for this
slice. Revision B supplies the public freshness read. Establish the publication-to-consumer
stopping behavior before broad propagation adoption. The recorded unchanged repeats exercise
the same frozen demand and leave these change and recovery cases open.
[SBX-06](references-and-projection-keys.md#sbx-06) · [Propagation scenarios](#propagation-scenarios)

## Native revisions

A revision is needed when installed programs, the physical model, privileges or descriptors
change. A change to the model and Python alone needs the release re-prepared, not a revision.
The current generator embeds a global wire digest in wrappers and descriptors, and application
storage checks that digest. Treat this as part of the deployed boundary when authoring and
comparing candidates.

| Revision | Carries | Why together |
|---|---|---|
| A, identity and propagation | Partition table and admission; rule and proof tables, form evaluators, establish routine and required proofs in binding; reference carrier; projection digests in binding and attachment; durable change delivery, readiness and scoped settlement coverage; retirement of the projection family tables, their checks and readers | Land material product and request identity effects once. Carry the native owner of settlement coverage with the transition it governs. |
| B, reads | The outputs, partitions, derivation-facts and proofs programs; the public freshness observation for a governed selection; the support export's relation list and read closure membership | Group read and export changes. Check their producer identity and receipt effects separately from shared wire and descriptor changes. |
| C, PDF | The paged row read for the rebuild; access derivation and the reduced checker; staging without build columns and the adopt program; typed capture reads | Lowering identity and the standard producer contract move once. |

A, B and C are development strands. A and C can be developed independently. B consumes A's
partition and proof contracts. Its freshness slice also consumes A's native settlement coverage.
Other read design can proceed while coverage is under development. Author each candidate against
its exact predecessor snapshot and register the resulting chain in dependency order. Candidate
effects, including shared descriptor admission, determine whether a development strand can be
installed independently.
[Coverage contract](references-and-projection-keys.md#settlement-coverage) ·
[Public read](owner-resolved-reads.md#sbx-11)

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
## SBX-20 — Register the revisions and install stage

Attribute installed effects from the selected [population and analytical routes](common-analytical-basis.md#decision-routes)
and the [replay contract](owner-resolved-reads.md#sbx-12) to the revisions that carry them.
Use the existing exact predecessor, candidate and stage checks for changes to native types,
programs, descriptors, grants or wire contracts.

**Order for fresh qualification inputs.** Start with PDF capture and publication under
revision C, then exercise the operation chains under A in dependency order, each product admitted
with its partitions and proofs. Exercise reads and exports under B. Establish coverage for the
newly governed selection from those facts. A newly selected scope needs an established position
before a current read can report it as settled.

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
Registration, application admission and fresh production results require their own managed
receipts.

For A, include a committed change and a native settlement or recoverable pending outcome on
the registered chain. For B, exercise the authorized freshness read against A's scope and
coverage, including a pending upstream change and subsequent unchanged settlement. Retain the
separate selected-read and export evidence. Attribute any producer, admission or receipt effects
of the new read wire through the existing predecessor comparison.

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
- Confirm that adopted population and scoped-relations routes removed the repeated preparation,
  conversions and validation they replaced. Follow their worker, publication and selected-reader
  consumers. Confirm the frozen archive no longer rebuilds its covered JSONL/SQLite closure.
  Preserve independent refusal and semantic tests in the respective owners.
- Confirm retirement of covered recursive readiness watermarks, stored wait hashes and repeated
  discovery sweeps after SBX-06 validates their replacement. Follow consumers in the planner,
  execution, demand reads, record grading and retained evidence. Preserve ordinary pinned reads,
  bounded scheduling and waiting-owner reports. Keep any unresolved coverage with SBX-06 until
  its owner migrates. A covered recursive path with a remaining caller is an open retirement
  obligation. [Readiness delivery](references-and-projection-keys.md#readiness-delivery)

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

On final source, include the adopted population route, the scoped-relations producer through
exact artifact nomination, and live and detached selected structural replay. Reuse independent
expectations from the owning packages. Include interruption and recovery where the chosen
worker or archive lifecycle changes. The historical DuckDB and Arrow fixture results establish
their recorded library behavior. Use managed final-source results for installed qualification.

Qualify the native stopping cases, readiness-only wake, join, supersession, recovery and read
visibility on the registered source and appropriate targets. Keep the textbook MCP closure
timeout as an open structural read obligation under SBX-11/12. Digest-only freshness work and
structural body or replay acquisition establish separate acceptance claims.
[Textbook condition evidence](references-and-projection-keys.md#sbx-05)

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

<a id="propagation-scenarios"></a>
### Propagation scenarios

Use the existing placement, order, membership, pointer, proof and authority scenarios above
through the delivery path. For the additional cases below, assert native decisions, selected
bindings, attempts or receipts and the read outcome as applicable. A small controlled fixture
can distinguish execution paths. Use the actual native boundary for durability and authority.
[Push review I01–I04](../../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I01)

| Scenario | Independent expectation |
|---|---|
| Register unrelated original bytes, then explicitly replace the evidence for a named selection | Registration leaves the existing selection's computation and coverage alone. Replacement affects the selected scope and preserves previously frozen demands. A newly acquired all-inventory selection can observe its own membership change. |
| Add or remove the first eligible population member, including return to empty; route a change to parallel roles that observe different fields | Declared selectors wake the affected bindings even when there was no prior selected address. Role identity and observed field groups determine which computations change. Confirm closure and distinguish an authorized empty result from unresolved coverage. |
| Activate a release with a material producer edit and a descriptive edit | The material determinant puts its operation in scope. The descriptive edit preserves computation identity. Eligibility edits can affect binding or discovery. An activation alone leaves the release pinned by an existing frozen demand intact. |
| Change an unread annotation field, then separately change the producer recipe and settle equal canonical input projections | An unread field leaves the consumer computation reusable. The material recipe change creates a producer attempt. Equal declared output projection creates no downstream attempt once the owner settles it. Compare with a changed observed span or placement, and verify the exact current attachment independently. |
| Publish another usable episode for the same exact pinned product; exercise late discovery, original admission, proof establishment and support revocation | An unrelated episode leaves the waiter waiting. Applicable support can wake the exact waiter with a stable computational digest. Native binding establishes its decision and revocation can refuse unchanged content. Revisit settled work and check that a covered request avoids the recursive watermark scan. |
| Settle a diamond where one arm changes and one ends unchanged | The join sees both current arms before comparing its combined key. The unchanged arm contributes settlement without another provider attempt at its downstream boundary. |
| Supersede a selection during execution; lose acknowledgement after a native commit | A late valid publication retains its historical meaning but cannot advance the superseding selection. Replay recovers committed change delivery and settles it without duplicate attempts or publication. |
| Pause delivery between edges after the upstream commit, while the immediate read target has no queued work | The authorized freshness-aware read reports pending for the affected scope, the pinned read retains its selected cut subject to current authority, and an independently covered scope stays available. After unchanged settlement, the governed scope advances without a new provider attempt. Check unavailable or unknown where coverage cannot be established, and confirm digest acquisition stays body-free alongside explicit body and export requests. |

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
