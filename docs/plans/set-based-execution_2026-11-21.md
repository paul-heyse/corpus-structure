# Set-based execution

**Status · 2026-11-23.** Development runs `semantic_sbx_pdf_report_address`. The accepted
typed producer and reader design through SBX-10 has its original development acceptance.
The [read and evaluation checkpoint](set-based-execution/owner-resolved-reads.md#sbx-through-13-checkpoint)
and [PDF checkpoint](set-based-execution/pdf-path.md#sbx-through-16-checkpoint) record
implementation and selected native and provider results through SBX-16. The execution
queue and package owners retain the open implementation and qualification obligations.
[Installed revision](set-based-execution/cutover-and-qualification.md#native-revisions) ·
[Verified development reset](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

This series owns the pivot to
partition-unit storage, declared rules and proofs, projection-keyed reuse, native change
propagation, owner-resolved reads and the single-derivation PDF path. **Created:** 2026-11-21.

**Basis.** The [execution outside PostgreSQL review](../functional_reviews/columnar-execution-outside-postgresql_2026-11-21.md)
at revision `b8109d423` (T1–T9, O01–O19, six defects). Nine investigations and one independent
design advice read production source at `7a415d18d` on 2026-11-21. The
[post-SBX-01 amendment](#post-sbx-01-review-amendment) and the
[push-propagation amendment](#push-propagation-amendment) use later source and evidence baselines.
The [common analytics amendment](#common-analytics-review-amendment) schedules the annotation-fork
pilot and expands the analytical and replay comparisons. The
[efficiency amendment](#validation-postgresql-efficiency-amendment) orders the live-read correction,
native attribution and qualification.
The [columnar redesign amendment](#columnar-redesign-amendment) reconciles the independent
columnar-basis and efficiency redesign reviews and sets out the proposed replacement sequence.
Design changes are **Proposed** unless marked accepted. Implementation and measured results
carry their own evidence and dates. `cs/` means `python/corpus-structure/src/corpus_structure/`.

**Framing (operator, 2026-11-21).** This is a hard pivot in the design phase. The series goes
directly to the target design with one active representation and execution path. Through SBX-09,
discard the old development data and install the cutover in an empty database. Qualify with
fresh fixtures. Originals, selections and derived results all go. No development data needs a
backup, conversion, backfill, restoration or regeneration. Stage
installation remains with SBX-20. [Development reset](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

## Outcome

After this series, what executes outside PostgreSQL rests on one modelled basis.

- **A homogeneous population is stored once, in declared partitions.** The proposed physical
  replacement stores generic item rows under each partition identity and carries model-typed
  Arrow populations through bulk execution. The product keeps its header and roots.
  [Columnar redesign](#columnar-redesign-amendment)
- **Rules are model declarations.** Each names what it reads and its scope. PostgreSQL evaluates
  declared forms at admission, one partition at a time; rules it cannot evaluate are attested by
  their producer.
- **A proof is a content-addressed fact** keyed on a rule fingerprint and the digest of its
  evaluated premises. A matching conclusion can be reused subject to the rule's establishment
  requirements. Point checks acquire keyed facts sufficient for the declared rule and address.
- **A computation is keyed on what it reads.** The same model declaration determines what a
  consumer receives and which facts affect its key. The text body and its body-relative spans can
  stay identical when its page placement changes. Attachment and publication separately bind
  the current occurrence, selected inputs, and authority.
- **Governed commits publish changes for demand-driven settlement.** Immediate consumers
  compare declared projections, and equal inputs or outputs can stop computational propagation.
  Readiness can change independently. An explicitly selected current read can report freshness
  from scoped native settlement evidence.
- **References have one model.** Every reference slot declares its target, bodies refer to their
  inputs by role, and one resolver serves every family.
- **A validated value stays validated**, each relationship is resolved by its owner, and the PDF
  path has one derivation of each thing.

The two tests every package is held to (operator, 2026-11-21): **no proof or reuse key flips on a
change that cannot affect the result**, and **no point check validates a whole structure**. Where
a package stops short of either, it says so and why.

## Decisions and rule changes

Accepted by the operator on 2026-11-21. Each is recorded by a decision record in SBX-00 before
dependent work.

| Change | Decision | Route |
|---|---|---|
| Direct cutover to an empty development database with one current shape | Accepted | [ADR-0150](../adr/0150-sbx-empty-development-cutover.md) |
| Product body and identity: populations stored once and validated as sets; derived addresses | Accepted | ADR; native revision A |
| Custody mechanisms simplified, ends kept | Accepted | ADR; edits to the stated custody comments with the code |
| Proof of validity generalized | Accepted | ADR; native revision A |
| Read programs and scratch stores | Accepted | ADR; native revision B; DESIGN §2 store statement |
| One kernel family rebuilt as set operations, as a gated trial | Accepted | Package SBX-19 ends in a recorded decision |

The operator also confirmed these changes before execution of SBX-00 and SBX-01:

| Change | Consequence | Depends |
|---|---|---|
| Request identity keyed on a declared read projection instead of the input product id | A consumer's key no longer changes with every upstream change; support records the selected input while the derivation records the equivalent one it was computed from | SBX-06 |
| Bodies refer to inputs by role, not by embedded product id | Product ids of nearly every family change once; a body can be followed only together with its derivation's inputs | SBX-05 |
| Offsets inside a block are block-relative | Every span in the first populations changes representation; a block's content no longer changes when text before it changes | SBX-01 |
| One reference carrier replaces the shared reference classes | Every family whose closure reaches them is re-keyed once | SBX-05 |

Standing guidance (operator, 2026-11-21): custody rules, accepted rules and library choices are
means. A proposal is judged by whether it still prevents the failure a rule exists to prevent,
and DuckDB, PyArrow, PostgreSQL and plain Python are named as today's carriers of stated needs.

The operator confirmed that the model must express the exact input-to-output dependencies,
including the independence of text and body-relative spans from page placement. SBX-06 must
implement the scoped successor [ADR-0149](../adr/0149-contextual-requests-and-projected-computation.md)
before enabling projected computation lookup. It preserves qualified occurrence binding,
project custody and publication identity. The [independent target review](../design_review/reviews/design_review_sbx06-computation-and-delivery_2026-11-21.md)
records the scope, acceptance and remaining native obligations.

The operator selected an explicit freshness-aware read for a named, authorized selection on
2026-11-21. The selection owner advances it explicitly, using an admitted successor demand
when frozen choices change. The target preserves native activation and selection authority,
exact pinned reads and demand-driven execution. Record any additional rule impact discovered
in authoring through operator confirmation and the relevant D3, D6 or D8 decision route
before dependent work. Apply the existing design-review cadence where the chosen design
changes a binding decision or substantial ownership or dependency boundary.

<a id="columnar-rule-confirmation"></a>
### Columnar rule decisions

The operator accepted all five rule changes on 2026-11-23. Complete the focused design/target
review and record the decision in the governing ADR and design sections before dependent
production adoption. Approval establishes scope. Implementation and qualification have
their own evidence.

| Rule | Disposition | Consequence and owning route |
|---|---|---|
| [ADR-0128](../adr/0128-wire-contract-boundary-validation.md) | Accepted | Give the affected population calls one model-derived set wire contract with typed input and result/refusal rows. Keep small JSON controls. Preserve installed request validation, client result validation before commit and exact release correspondence. Route through DESIGN §B4/B5 and D3. |
| [ADR-0144](../adr/0144-sbx-partitioned-products.md) | Accepted | Replace the tagged partition body with generic logged item rows. Retain partition commitments, field groups, placement and role-relative addresses. Route through DESIGN §B1/B4/B5 and D3. |
| [ADR-0145](../adr/0145-sbx-custody-boundary.md) | Accepted | Replace the frozen decoded population carrier with an admitted typed value and sealed IPC across applicable process boundaries. Keep the validating construction and loaded-code verification obligations in the custody owner. |
| [ADR-0021](../adr/0021-instance-and-structure-authorities.md) | Accepted | Permit model-derived canonical item framing and ordered aggregate commitments in the engine for the affected SBX populations, once exact parity is established. Keep the Python definition and independent reference and preserve canonical identity and exact scalar spelling. Route through the identity and analytical owners. |
| [ADR-0148](../adr/0148-sbx-kernel-trial.md) | Accepted | Bring forward the relevant SBX-18 analytical prerequisites and authorize the bounded annotation-family adoption ahead of the scoped-relations trial. Keep SBX-19's adoption decision for scoped relations. Route through the analytical owner and DESIGN §B2/B5. |

The proposal uses the existing [typed authoring rule](../adr/0135-declared-facts-and-typed-database-programs.md)
and the [empty development cutover](../adr/0150-sbx-empty-development-cutover.md).

[ADR-0154](../adr/0154-sbx-columnar-populations.md) records the accepted target.
The [focused target review](../design_review/reviews/design_review_sbx-columnar-target_2026-11-23.md)
cleared it for implementation. Its F01 retained-parent choice and the underlying DA-087
diagnosis are scheduled through [typed item admission](set-based-execution/populations-rules-and-proofs.md#typed-item-admission)
and the [consumer migration](set-based-execution/cutover-and-qualification.md#columnar-cutover-sequence).

## Shared contracts

Each contract has one owning document. Other documents link to it and do not restate it.

| Contract | Owner |
|---|---|
| Collection, partition, partition digest, root, field group, address | [Populations, rules and proofs](set-based-execution/populations-rules-and-proofs.md#collections-and-partitions) |
| Rule declaration, form, fingerprint, attested rule | [same](set-based-execution/populations-rules-and-proofs.md#rules) |
| Proof conclusion, evaluated premise, establishment, required proofs at binding | [same](set-based-execution/populations-rules-and-proofs.md#proofs) |
| Reference carrier, declared target, resolver, original and current bindings | [References and projection keys](set-based-execution/references-and-projection-keys.md#the-reference-model) |
| Read projection, computation identity and occurrence binding, partition memo | [same](set-based-execution/references-and-projection-keys.md#read-projections) |
| Native change origins, reverse selectors, readiness and scoped settlement coverage | [same](set-based-execution/references-and-projection-keys.md#change-origins) |
| Validated carrier, single constructor, verification bracket | [Validated values and hand-off](set-based-execution/validated-values-and-handoff.md) |
| Model-derived relations, typed carrier and engine policy, early pilot, PostgreSQL transfer | [Common analytical basis](set-based-execution/common-analytical-basis.md#columnar-population-target) |
| Read programs, answer shapes and freshness disclosure, replay relations, cursor, cache key | [Owner-resolved reads](set-based-execution/owner-resolved-reads.md) |
| PDF rebuild, access derivation, verified carriers, build identifier | [The PDF path](set-based-execution/pdf-path.md) |
| Early integration, development reset, native revisions, shared scenarios, assembled evidence | [Cutover and qualification](set-based-execution/cutover-and-qualification.md) |

## The design in one page

**Unit.** A product is a header plus collections. A collection declares its unit:

| Unit | Families | Unit identity | Storage |
|---|---|---|---|
| partitioned | tokens, sentences, HanLP units | partition digest | Partition headers and generic logged item rows in the proposed layout |
| identified | formal, construction, contextual and rich graph members; candidate records | the content-hash id | `kb.data_product_member` |
| bound | source views, manifests, contextual target members, candidate contributions | member id with its context | `kb.data_product_member` |

Rules and proofs use the same tables for all three. One model, not two.

**Why partitions with generic item rows.** PostgreSQL uses item fields for declared rules and
address lookup. Indexing those fields on the admitted rows replaces repeated tagged-body
expansion and supports both sparse reads and population scans. The generic row layout uses the
same declaration for each family. The partition header and ordered item text preserve the
identity and reuse boundary.

**Why this meets the two tests.** Rule fingerprints are computed from the model facts a rule
reads, through the same rooted-closure mechanism that already makes kind identity substantive.
Proof premises and projection digests commit to the facts the rule or consumer observes.
A point lookup uses keyed metadata, required support, and the addressed item when
needed. A collection claim can require collection-level premises. The
[shared scenarios](set-based-execution/cutover-and-qualification.md#change-scenarios) specify
which changes affect which results.

**Where it stops short.** Attested rules are keyed on the code of the rule's own function, which
is narrower than today but is not a model fact; moving a rule into a declared form is the route
to remove that. Kernels that hand a whole value to spaCy, HanLP or GLiNER cannot have their reads
derived statically; their projections are declared and enforced by what they are handed. Some
kernels are not block-local and key on a whole collection.

## Credible future changes

- *A new population* (for example cells of a table): one collection declaration with its
  partition key, field groups and rules. No new table, program or resolver.
- *A new rule on an existing population*: one declaration. Preparing the release gives it a
  fingerprint; admission establishes it for new content and the establish routine for existing
  content, per partition. No other proof moves.
- *A new consumer of an existing population*: a read projection on its role. It is keyed on that
  projection and receives only it.
- *A model edit to a field one rule reads*: that rule's fingerprint changes and its proofs are
  re-established; consumers whose projections exclude the field keep their keys.
- *A kernel family rewritten as set operations*: tables built in process from partitions and
  graph members; storage and identity are unaffected.

Revisit the physical layout if the generic item projection cannot express a required indexed
address or exact rule comparison, or if a skewed partition materially defeats the proposed
grouping and working-set contract. The [early pilot](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)
selected the immutable carrier for the earlier annotation path. The replacement addresses
acquisition and publication together, beyond the comparison covered by the pilot.

## Execution queue

Packages are described in their companions. Prerequisites are stated as the contract or
capability consumed.

| Package | Delivers | Needs | Companion |
|---|---|---|---|
| SBX-00 | Complete. Decision records, entry evidence and fixture baseline are recorded. Exact selected-use readers and detached demand ownership passed genuine finite and rich export checks. | — | [Entry and reader evidence](#sbx-00) |
| SBX-01 | Complete. Typed item COPY, retention, promotion, indexed readback and authenticated Parquet replay passed. Native partition body storage is retired. | SBX-00 and columnar rule decisions | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-01) |
| SBX-02 | Complete. Native rule evaluation, retained establishment, product and partition attestations, and selected binding passed valid and refusal cases. | SBX-01 partitions and shared premises | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-02) |
| SBX-03 | Complete. The real typed annotation fork binds layout, membership and coverage. Annotation and canonical publications passed authenticated Parquet replay and exact reads after occurrence changes. | SBX-01 partitions, SBX-02 proof binding, SBX-05 resolver and SBX-08 acquired carriers | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-03) |
| SBX-04 | Complete. Construction binds the original selected annotation block, token and layout. Contextual acquisition checks the exact supporting input, original roles and released attachment-policy witnesses. | SBX-02 | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-04) |
| SBX-05 | Complete. Selected graph readers bind authentic original role addresses. Typed references, contextual witness and detached replay passed. SBX-11 retains the wider keyed and online read scope. | SBX-01 addresses | [RPK](set-based-execution/references-and-projection-keys.md#sbx-05) |
| SBX-06 | Development baseline complete. Its later qualified freshness change is installed and has selected analyzed-context and historical-read evidence. SBX-11 owns combined read acceptance. | SBX-01 field groups and SBX-02/03–05 proofs, addresses and binding | [RPK](set-based-execution/references-and-projection-keys.md#sbx-06) · [Qualified reads evidence](set-based-execution/owner-resolved-reads.md#sbx-qualified-reads-checkpoint) |
| SBX-07 | Complete. Governed canonical reuse passed across occurrence edits and separate annotation captures, with exact placement and revocation. Other current hosts use whole-result execution. | SBX-06, SBX-03 | [RPK](set-based-execution/references-and-projection-keys.md#sbx-07) |
| SBX-08 | Complete. Acquired source frames and immutable typed, formal, interpreted and composed payloads passed the named provider, handoff and malformed-input checks. | SBX-04/05 proof and address contracts | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-08) |
| SBX-09 | Complete. Sealed output and reply custody, registered-root use, deployment recovery, both PDF reuse journeys, and applicable ordinary, provider and shared fault qualification passed. The development database was recreated empty on the verified sole root. | Integrated SBX-03–08 behavior, the brought-forward PDF producer slice, and final-source correspondence to the registered root | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-09) · [Verified reset](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09) |
| SBX-10 | Complete for development. Consumed-runtime custody and the installed math occurrence, normalization, scope, exact readback and resume checks passed. | SBX-08 and SBX-03 token views. Selected math readback uses the early SBX-12 reader. | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-consumed-runtime-custody) |
| SBX-11 | Implemented indexed output-prefix paging, typed partition and derivation windows, bounded proof aggregation, catalog frontier batches and shared exact-reference acquisition. Installed output paging, sibling freshness, exact and absent partition items, and first matching proof passed. Physical attribution, protected partitions, combined cross-source coverage and remaining finite snapshot lifetimes stay open. | SBX-01 partitions, SBX-02 proofs, SBX-06 qualified settlement and the early SBX-12 reader for structural consumers | [ORR](set-based-execution/owner-resolved-reads.md#sbx-11) |
| SBX-12 | Implemented typed v4 replay, atomic archive publication, current reacquisition for proof-sensitive readers and retirement of the selected-record SQLite index. Installed interruption controls and genuine candidate-conditioned D1 export and replay passed. Remaining proof-sensitive reader and whole-route acceptance stays open. | Early contract uses SBX-02 proofs, SBX-05 references and shared typed projections. Full live and detached integration uses SBX-11 acquisition. | [ORR](set-based-execution/owner-resolved-reads.md#sbx-12) |
| SBX-13 | Implemented separate acquired evaluation cuts, scoped Arrow facts, DuckDB event slot checks and independent evaluation after reader release. Installed grade/fitter custody, event scoring, selected authored references, known empty output, and restricted event-frame refusals passed by selected identity. | SBX-11 native binding facts and the early SBX-12 reader slice | [ORR](set-based-execution/owner-resolved-reads.md#sbx-13) |
| SBX-14 | Implemented shared ordered row reconstruction for transforms, full exports and validation with captured lowering. Installed native transforms and forced revalidation under incompatible ambient defaults passed by selected identity. | — | [PDF](set-based-execution/pdf-path.md#sbx-14) |
| SBX-15 | Implemented publication-derived item relations, exact report-occurrence lookup, bounded native reads and a derived region view. Sparse formula diagnostics passed on the installed revision, including NUL and forged-pointer controls. Larger combined visual qualification remains open. | SBX-14 rebuild contract | [PDF](set-based-execution/pdf-path.md#sbx-15) |
| SBX-16 | Implemented verified replay custody, load-time physical bindings, atomic document adoption, projected candidate reads and publication sealing. Different-build adoption and genuine missing-page GPU recovery passed. Whole-transformation snapshot cleanup and validation counts remain open. | — | [PDF](set-based-execution/pdf-path.md#sbx-16) |
| SBX-17 | Typed certification, logical rows by column and retirement of duplicate certifier storage | SBX-15 relationship projections, SBX-16 carriers and consumed SBX-18 job contract | [PDF](set-based-execution/pdf-path.md#sbx-17) |
| SBX-18 | Shared fidelity, one analytical job allocation and bounded comparisons for physical batching and durable output | Existing typed population and worker custody | [KT](set-based-execution/kernel-trial.md#sbx-18) |
| SBX-19 | Complete scoped-relations comparison through exact artifact nomination and readback, with a recorded adoption decision | SBX-18, SBX-08, SBX-05 and SBX-10 indexes. Complete comparison consumes installed math integration. Projection-keyed qualification consumes SBX-06. | [KT](set-based-execution/kernel-trial.md#sbx-19) |
| SBX-20 | Attribute the A, B and C effects against exact predecessors, register the resulting chain and install stage | Packages the candidates carry and the observed stage predecessor | [CQ](set-based-execution/cutover-and-qualification.md#sbx-20) |
| SBX-21 | Retirement sweep, including confirmation of SBX-06 watermark and sweep removal | replacement paths and migrated consumers | [CQ](set-based-execution/cutover-and-qualification.md#sbx-21) |
| SBX-22 | Final-source qualification, including the shared change scenarios | SBX-20, SBX-21 | [CQ](set-based-execution/cutover-and-qualification.md#sbx-22) |

**Dependencies across the later packages.** SBX-09 supplies typed population, reference and
custody contracts. Confirm qualified coverage with SBX-06 and prepare the early SBX-12 reader
contract for the remaining SBX-11 migrations. The full archive follows its live acquisition
prerequisites and stable-file verification precedes warm rereads. PDF access and certification
design can progress in parallel with the shared job allocation and consumed-runtime custody.
Those shared contracts inform the physical carrier choices and the complete scoped-relations
comparison. Start predecessor comparison early enough to inform stage authoring.
[Post-SBX-09 amendment](#post-sbx-09-review-amendment)

<a id="remaining-execution-through-sbx-09"></a>
### Execution through SBX-09

**Execution sequence · 2026-11-23.** The prior registered root and pilot retain their evidence.
The [typed implementation checkpoint](set-based-execution/cutover-and-qualification.md#sbx-columnar-implementation)
owns current implementation and qualification evidence. Follow the
[accepted rule decisions](#columnar-rule-confirmation) and focused target review for the replacement.

1. Settle the coupled carrier, identity and storage design, then bring forward the model schema,
   custody, engine and resource prerequisites from SBX-18. Preserve the installed control
   contracts that remain in scope. [Shared target](set-based-execution/common-analytical-basis.md#columnar-population-target)
2. Reopen the SBX-01/02 physical foundation. Deliver annotation → canonical → construction
   through typed acquisition, worker dispatch, native retention and settlement, indexed selected
   readback and the required read and replay slice. Verify proofs, projection keys and current
   occurrence across the integrated SBX-03–09 route. [Cutover sequence](set-based-execution/cutover-and-qualification.md#columnar-cutover-sequence)
3. Extend to affected HanLP, declaration and member producers and migrate their authoritative
   readers, detached consumers and workers. Retire the superseded carriers and producer paths
   as their consumers move. Bring forward the SBX-11/12 slice needed by the affected SBX-09
   routes. Keep the general read program and archive work with SBX-11/12.
4. Integrate the approved [PDF producer custody slice](set-based-execution/pdf-path.md#pdf-producer-custody)
   and author and install one fresh replacement root. Apply the existing qualification conditions
   and reconcile prior receipts by exact applicability. Run remaining cohorts through one bounded
   owner. Reset development empty after integrated acceptance. Stage remains with SBX-20.
   [Reset and acceptance](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

Apply scoped efficiency improvements where they survive the replacement or directly support a
required journey. Unresolved timing attribution retains its existing owner.

<a id="sbx-00"></a>
## SBX-00 — Decisions, entry checks and baseline

**Decisions recorded · 2026-11-21.** ADR-0144 through ADR-0148 and ADR-0150 record the accepted
targets and their governing design sections. The focused
[Revision A target review](../design_review/reviews/design_review_sbx-revision-a-identity-and-authority_2026-11-21.md)
set the acceptance for F01–F04. It separated content from placement and ordering, required
parent authority before fetching partition bodies, and distinguished current-use selection
from the producing derivation's recorded inputs.

**Entry checks.** Each settles a premise a package depends on, by reading or a focused existing
test, not a campaign.

| Check | Decides | If it fails |
|---|---|---|
| Canonical sentences and HanLP units never cross a block | Block as the partition for all three kinds (SBX-01) | The partition for the failing kind is the sentence's block of origin, or the kind keeps a whole-collection premise |
| No token field distinguishes explicit null from absent | Field-group encoding (SBX-01) | A presence mask per field group |
| Spread of block sizes on the retained book | Whether a partition is a useful unit (SBX-01, SBX-11) | A secondary split of oversized blocks, decided before SBX-03 |
| Every product a body cites is a bound input of its derivation | Role-relative references are total (SBX-05) | The citing operations gain the missing input roles |
| `ddo_valid_closure` behaviour with proof lookups in binding | Where required proofs are checked (SBX-02) | Proofs are checked in the binding program only, outside the validity fixpoint |
| Which model hosts make a block's output depend on its batch peers | Which kernels can be memoised per partition (SBX-07) | Those kernels stay whole-collection |

**Entry evidence · 2026-11-21.** The authenticated retained 66-page sentence answer contained
1,002 blocks, 25,543 tokens and 1,842 sentences. Its largest serialized block was 100,614 bytes.
Containment held throughout this sample and the canonical and HanLP paths preserve block origin
on inspection. Whole-block partitions are the working unit. Group projections preserve absence
and explicit null. Reconversion can rename positional pointers. Resolving a particular occurrence
across conversions requires exact correspondence, while equal declared projections can establish
computation equivalence. SBX-05 owns citation-to-input gaps, SBX-02 checks proofs at binding
outside the validity fixpoint, and cohort and batch dependencies remain with SBX-07.
[Entry evidence and fixture inventory](../design_review/evidence/2026-11-21_sbx-entry/README.md)

**Defect 1.** `actual_graph_inputs` and the grouped interpretation projection read
`request["binding"]`, which the support export omits. The repaired readers use the exact consumed
use's authenticated `selection` and verify its derivation. Detached verification now recomputes a
nonreusable request with the retained use's owning demand and separately checks current frontier
ownership. The initial genuine finite export exposed the mismatch
(`e338c1bc055f479f8a357a7d1edc1622`). Replaying its original bytes after the fix verified the
archive and produced two groups and one finite universe. The selected graph and grouped controls
passed 28 cases on main, including refusal of a frontier scan for the keyed use selection
(`96405d064ed74bbd9f16a97d9e4f526c`). Detached manifest and partition parity controls passed
27 cases after the verifier change (`4763dfba58ca4e8dafa4a60fa4ed6e57`).
The single-source native regression published actual finite and rich outputs and exercised both
readers through verified detached exports (`55f6b07f94bb4ff1ab1ea376e9a4dbef`). Both exported
results were replayed through the final keyed reader on main.

**Checks · 2026-11-21.** `uv run ci check --only types`
(`d23e8b229a6a48c3afa196ab769ea5cf`), `uv run ci check --only lint`
(`aae1c3d436494f66adb713a11a82b84f`) and `just model check` passed. `uv run ci schema check`
compiled the statistics pack and reported projection analysis unassessed. Native package evidence
comes from the rollback-only candidate and the specific native controls.

## Disposition of the review

| Review item | Disposition |
|---|---|
| T1 population stored once, validated as a set | SBX-01, SBX-02, SBX-03 |
| T2 address when addressed | SBX-01 (addresses), SBX-05 |
| T3 one reference model, closure checked once | SBX-05 |
| T4 one proof per boundary; validated values carried | SBX-08, SBX-09 |
| T5 validity established once and accepted | SBX-02, SBX-04. Strengthened: keyed on rule fingerprint and content, not on release |
| T6 derived data computed once | SBX-10; SBX-03 removes the largest case |
| T7 relationships resolved by their owner | SBX-11, SBX-12 |
| T8 one derivation, one algorithm | SBX-14, SBX-15 |
| T9 every real boundary has a proof | SBX-05 (reference closure), SBX-14 (captured policy) |
| O01 one Arrow schema derivation | The SBX-03/08 pilot and SBX-12 derive the projection schemas their consumers use from the model. [Shared contract](set-based-execution/common-analytical-basis.md#projection-contract) |
| O02 certify without round trips; O03 typed capture | SBX-17 |
| O04 node relation | SBX-15 |
| O05 cheaper lookups on the present store | Not built; SBX-11 supersedes it. Defect 1 is fixed in SBX-00 |
| O06 typed relations for selected records | SBX-12 |
| O07 one span vocabulary | SBX-10 |
| O08 decode once | SBX-08 |
| O09 logical rows by column | SBX-17 |
| O10 fidelity rules in the analytical owner | SBX-18 |
| O11 populations as sets | SBX-01 to SBX-03 |
| O12 one reference model | SBX-05 |
| O13 carry validated values | SBX-08, SBX-09 |
| O14 one stance on validity | SBX-04 |
| O15 compute derived data once | SBX-10 |
| O16 keep the answer, ask more | SBX-11, SBX-12 |
| O17 access columns, one rebuild | SBX-14, SBX-15 |
| O18 one document, decode and hash per boundary | SBX-16 |
| O19 evaluation preflight | SBX-13 |
| The broader direction | SBX-19 trial and decision |
| Defect 1 binding field | SBX-00 |
| Defect 2 unvalidated references | SBX-05 |
| Defect 3 default policy in round-trip validation | SBX-14 |
| Defect 4 construction consumers check identity only | SBX-04 |
| Defect 5 code without production callers | SBX-21 |
| Defect 6 smaller items | SBX-21 |
| Arrow worker packet | The [SBX-03/08 pilot](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence) established scoped parity and selected the existing immutable carrier for the ordinary annotation worker route. |
| Other declined items | Second identity encoder, deriving the JSON access copy in SQL, a digest pass on transform input, and byte-budget paging changes remain declined. |

Added by this plan beyond the review: projection-keyed request identity and the partition memo
(SBX-06, SBX-07), block-relative addresses and field groups (SBX-01), and proofs keyed on rule
fingerprint and content in place of release and product (SBX-02).

<a id="post-sbx-01-review-amendment"></a>
## Post-SBX-01 review amendment

This amendment integrates the [post-SBX-01 review](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md)
at revision `a242675c6`, inspected against source `d36e07594` on 2026-11-21. Each row gives the
planned disposition. Conditional choices keep the evidence and default in their owning package.

| Finding | Planned disposition and owner | Acceptance or decision |
|---|---|---|
| [I01](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I01) | [SBX-06](set-based-execution/references-and-projection-keys.md#sbx-06) keys computation on declared inputs. SBX-03/05 own exact correspondence where required for a specific occurrence, and SBX-07 consumes the distinction. | Equal local projections survive a move or pointer rename. Changed observed placement changes the key. Publication uses the current occurrence. Ambiguous correspondence cannot retarget it. |
| [I02](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I02) | SBX-02 and SBX-06 use the [shared change scenarios](set-based-execution/cutover-and-qualification.md#change-scenarios) for premise design. SBX-12 and SBX-22 consume them. | Independent checks distinguish stable keys, invalidated keys, proof availability and new attempts. Retain collection group roots only for a supported repeated access. |
| [I03](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I03) | [SBX-02/04](set-based-execution/populations-rules-and-proofs.md#proofs) separate conclusions and admissible establishments. SBX-05–07 and SBX-12 preserve producing inputs and current use support. | Two selections, transitive and protected support, revocation and missing-attestation cases exercise live binding and detached custody. |
| [I04](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I04) | SBX-02/05 and [SBX-11/12](set-based-execution/owner-resolved-reads.md#sbx-11) scope premise preparation, item membership, admission work and authority acquisition. | Point, empty and continued reads with unrelated state, a missing item inside a valid partition, and revocation across pages establish the access bounds. |
| [I05](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I05) | [Early Revision A integration](set-based-execution/cutover-and-qualification.md#early-revision-a-integration) uses the runnable SBX-02/03/05 slices. | A real producer chain passes rollback-only admission, proof binding, reference resolution, and selected readback with independent expectations and an unchanged repeat. |
| [I06](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I06) | [SBX-20](set-based-execution/cutover-and-qualification.md#sbx-20) attributes direct and shared installed effects before one registered identity cutover. | Compare read-only wire and material lowering changes against exact predecessors and resume the same target. Keep the current wire scope unless a bounded comparison justifies narrowing. |
| [I07](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I07) | [SBX-08/10](set-based-execution/validated-values-and-handoff.md#target) own payload and view lifetime. [SBX-14–17](set-based-execution/pdf-path.md#target) own sealing, streaming and recovery. | Decode shared payload once, resolve distinct placements, release owned views, and exercise alias mutation, captured policy, numeric fidelity and a genuinely recovered spool. |
| [I08](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I08) | [SBX-07](set-based-execution/references-and-projection-keys.md#sbx-07) decides memo eligibility per host. [SBX-18/19](set-based-execution/kernel-trial.md#sbx-18) own job resources and the scoped-relations trial. | Compare batch peers and orders. Exercise cleanup between jobs and on interruption. Decide the trial on fidelity, scoped work, and material simplification. |
| [I09](../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I09) | SBX-11–13 and [SBX-20–22](set-based-execution/cutover-and-qualification.md#sbx-20) reuse authentic setup within its evidence scope and migrate the independent tests with their replacements. | Keep one genuine finite/rich export regression, typed replay and refusal controls, and final-source whole-book and real-provider evidence. |

<a id="push-propagation-amendment"></a>
## Push-propagation review amendment

This amendment integrates the [push-propagation review](../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md)
at `95496dd4d`, inspected against `3ceeadfbc` on 2026-11-21. The intervening commit added
the review and its index entry. The dispositions below are planned. Existing package
receipts retain their recorded scope, including the distinction between unchanged demand
repeat and native delivery from a governed commit.

| Finding | Planned disposition and owner | Acceptance |
|---|---|---|
| [I01](../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I01) | [SBX-06](set-based-execution/references-and-projection-keys.md#change-origins) owns typed native origins and reverse selectors for selected and prospective inputs. | Distinguish immutable registration, explicit evidence replacement, material release changes and descriptive changes. Cover first and removed members and parallel roles. |
| [I02](../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I02) | [SBX-06](set-based-execution/references-and-projection-keys.md#settlement-coverage) owns recoverable immediate settlement and both computational cutoffs. SBX-07 uses eligible locality. | Confirm both cutoffs on the early chain, current arms at a join, current selection fencing and idempotent recovery after lost acknowledgement. |
| [I03](../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I03) | [SBX-06](set-based-execution/references-and-projection-keys.md#readiness-delivery) owns readiness migration with the executor. SBX-11/12 consume observations and preserve pinned evidence. SBX-21 checks residual consumers. | Exact-pin equal-content wake, late discovery, membership and closure, proof, source and trust controls establish coverage before removing recursive discovery of those changes. |
| [I04](../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I04) | SBX-06 supplies coverage. [SBX-11/12](set-based-execution/owner-resolved-reads.md#freshness-aware-reads) own freshness disclosure and pinned or detached evidence. | Scope stays pending across an in-flight upstream edge. An unchanged branch can settle without computation. Independent scopes and authorized pinned reads keep their meaning. |

SBX-20–22 consume the [propagation scenarios](set-based-execution/cutover-and-qualification.md#propagation-scenarios).
Automatic refresh remains a possible later extension, triggered by an identified maintenance
interest and explicit effect authority.

<a id="common-analytics-review-amendment"></a>
## Common analytics review amendment

This amendment incorporates the [common analytical basis review](../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md)
at `8fab53dd5`, which inspected `d884fa8a2`. The [pinned-build probe](../design_review/evidence/2026-11-22_sbx-common-analytics/README.md)
establishes fixture behavior for Arrow and Parquet, typed windows, result lifetime and selected scan plans.
The decisions below are scheduled. Production behavior, authority changes and qualification have their
own acceptance routes.

| Finding | Planned disposition and owner | Decision and acceptance |
|---|---|---|
| [I01](../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I01) | [SBX-03/08 pilot](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence) compared the whole annotation fork, including the worker hand-off. SBX-04/05 own proofs and use, SBX-06/07 consume stable local and current-placement distinctions, and SBX-09 owns executable custody. | The ordinary immutable carrier removes the repeated primary admission work. Carry it through the remaining consumers and final-root readback. |
| [I02](../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I02) | [SBX-18/19](set-based-execution/kernel-trial.md#sbx-18) compare typed expressions and captured owner SQL with complete scoped-relations and artifact coverage. | Invocation ownership is the baseline. Compare worker reuse under actual cleanup and interruption. Route any selected rule change before production adoption. |
| [I03](../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I03) | [Placement and transfer](set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer) retains the pilot's comparison of native sets, current transfer and exact-snapshot ADBC for use in SBX-19. | Try the connector only under the purpose, exact-cut and work-removal conditions. A simpler operational authority requires a separate architecture proposal. |
| [I04](../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04) | [SBX-11/12](set-based-execution/owner-resolved-reads.md#sbx-12) own current authorization and frozen selected-review Parquet replay. [SBX-16/17](set-based-execution/pdf-path.md#sbx-16) keep PDF recovery custody. | Verify sealed closure and genuine first replay and reread. Persist a derived dossier or reconsider PDF transport only when the named consumer justifies the full change. |

The later trial uses the [existing decision routes](set-based-execution/common-analytical-basis.md#decision-routes).
The full scoped-relations trial and archive work keep their downstream dependencies. The development
cutover remains empty and stage installation remains with SBX-20.

**Pilot decision at that checkpoint · 2026-11-22.** SBX-03/08 retained the acquired immutable annotation carrier.
Primary construction now uses its admitted row blocks directly. The combined real provider
fork passed on a private current-source root. The final registered root and remaining SBX-09
acceptance stay with the cutover owner. The [columnar amendment](#columnar-redesign-amendment) reopens the carrier choice for the proposed replacement. [Pilot evidence and decision](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)

<a id="post-pilot-review-amendment"></a>
## Post-pilot review amendment

**Scheduled · 2026-11-22.** This amendment integrates the [review through SBX-09](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md)
published at `8d2a8013e` against implementation `6834339f6`. Package owners retain scheduled
work and closure evidence. The [boundary controls](../design_review/evidence/2026-11-22_sbx09-review/README.md)
establish their dated finite relation, local resolver and projected payload results. Installed
authority, settlement and final-root qualification have their own acceptance.

| Finding | Disposition |
| --- | --- |
| [I01](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I01) | [Installed successor](set-based-execution/cutover-and-qualification.md#early-revision-a-integration) ties SBX-03/05/06/07 to actual governed changes. SBX-07 retains the worker-local canonical memo. |
| [I02](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I02) | [SBX-04](set-based-execution/populations-rules-and-proofs.md#sbx-04) binds the exact premises. SBX-05 owns grouped native addresses and SBX-08 carries admitted blocks. |
| [I03](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I03) | [SBX-05](set-based-execution/references-and-projection-keys.md#sbx-05) supplies exact reference meaning and the scalar caller. [SBX-11](set-based-execution/owner-resolved-reads.md#sbx-native-read-attribution) owns any early keyed read and the broader online path. SBX-12 owns replay. |
| [I04](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I04) | [SBX-06](set-based-execution/references-and-projection-keys.md#sbx-06) extends native resume, discovery and scope settlement, separates scheduler state from shared reads and retires obsolete machinery. |
| [I05](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I05) | [SBX-08/09](set-based-execution/validated-values-and-handoff.md#sbx-08) finish carrier and executable custody. [SBX-16](set-based-execution/pdf-path.md#sbx-16) owns projected candidate replay. |
| [I06](../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I06) | [Cutover and qualification](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09) owns registered-root acceptance, fixture reuse and the empty reset. |

The [common analytical basis](set-based-execution/common-analytical-basis.md#projection-contract)
owns placement, fidelity and investigation criteria. SBX-12, SBX-16 and SBX-18/19 name the
library APIs used by their consumers. The existing decision routes govern any later selection
that changes a binding rule.

<a id="validation-postgresql-efficiency-amendment"></a>
## Python validation and PostgreSQL efficiency amendment

**Scheduled · 2026-11-22.** Consume the [efficiency review](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md)
at `c518715fe`, inspected at `d1a917c68`. The [isolated evidence](../design_review/evidence/2026-11-22_python-postgresql-efficiency/README.md)
establishes feasibility for the live draft and identifies expensive native endpoints.
The actual event internals require separate attribution. Each receipt retains its original
source and scope. The amendments preserve current authority, custody and cutover decisions.

| Finding | Disposition |
| --- | --- |
| [I01](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I01) | Implemented and tested by selected identity. [SBX-08 live-page handoff](set-based-execution/validated-values-and-handoff.md#sbx-live-page-handoff) reuses admitted interpretation. [SBX-11 summary](set-based-execution/owner-resolved-reads.md#sbx-live-summary-correction) projects metadata. Tag-directed raw validation remains conditional. |
| [I02](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I02) | Tested the guarded read and current purpose checks on the stored-body route. [SBX-11 native read attribution](set-based-execution/owner-resolved-reads.md#sbx-native-read-attribution) retains the conditional keyed online slice and later migration. SBX-12 carries cursor and replay effects. |
| [I03](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I03) | [SBX-06 native attachment](set-based-execution/references-and-projection-keys.md#sbx-native-attachment-and-completion) stages per-item support scopes once. Held lock order, exact occurrence and savepoint refusals have selected native evidence. |
| [I04](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I04) | [SBX-06 completion](set-based-execution/references-and-projection-keys.md#sbx-native-attachment-and-completion) encodes canonical completion once for its distinct intent and payload digests. The event journey passed with the existing renewal limit after stored-body authorization reused shape admission. The public completion schema and seal checks remain authoritative. |
| [I05](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I05) | [SBX-08/09 witness handoff](set-based-execution/validated-values-and-handoff.md#sbx-witness-handoff) prepares only used roles and exact addresses. Keep the scoped Python input check for its malformed-value diagnostics. Native positive and refusal controls passed by selected identity. |
| [I06](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06) | [Common analytical basis](set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer) owns shared placement and fidelity. SBX-11/12 use them for selected reads and finite replay. SBX-18/19 retain the named whole-route trial. |
| [I07](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I07) | [Qualification](set-based-execution/cutover-and-qualification.md#sbx-efficiency-qualification) owns stable source, bounded cohorts, preparation reuse and evidence reconciliation. SBX-22 uses the same applicable safeguards. |

Apply the [documented decision routes](set-based-execution/common-analytical-basis.md#decision-routes)
before any later alternative changes a binding rule. Required qualification and the empty development reset retain their scope. The [columnar amendment](#columnar-redesign-amendment) proposes the order for the replacement root.

**Execution priority · 2026-11-22.** Land bounded work reductions that help a required journey
before broad qualification, including journeys that already pass their watchdog. Distinguish
routine scoped corrections from the later SBX-11/12 and SBX-18/19 trials.
[Qualification and selection criteria](set-based-execution/cutover-and-qualification.md#sbx-efficiency-qualification)

<a id="columnar-redesign-amendment"></a>
## Columnar redesign amendment

**Proposed · 2026-11-22.** Reconciled the independent
[columnar-basis review](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md)
published at `ed6076db5` and the
[efficiency and analytical redesign review](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md)
published at `b5ff78b22`. The proposal selects a whole producer-to-consumer replacement
before another SBX-09 cold root. PostgreSQL keeps transactional authority and partitions keep
their identity, proof and reuse semantics. Arrow carries the working population and DuckDB
owns local relational work. The existing immutable pilot established a useful improvement on
the earlier path. A probe of that path had tagged input conversion and Python output
reconstruction on either side of Arrow. The new target removes those surrounding stages where
the typed population serves the actual consumers. [Shared target](set-based-execution/common-analytical-basis.md#columnar-population-target)

The retained probes establish synthetic identity parity, typed set-call feasibility and
specific library behavior. The later [cutover qualification](set-based-execution/cutover-and-qualification.md#sbx-columnar-implementation)
covers production type fidelity, composed COPY, grants and recovery. Stopping concurrent
runs released memory. Source inspection identified avoidable passes and duplicated fixture work.
Relative native cost and lock attribution remain with SBX-06 and SBX-11. Preserve earlier
receipts and judge applicability to the particular source, root, harness and provider scope.
[Columnar probes](../design_review/evidence/2026-11-22_sbx-columnar-basis/README.md) ·
[Composition probe](../design_review/evidence/2026-11-22_sbx-analytical-redesign/README.md)

| Source finding | Proposed disposition and owner |
|---|---|
| [Columnar I01](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I01) | Select the typed population and sealed IPC for affected SBX-01/03/08/09 producers and workers. [Shared carrier](set-based-execution/common-analytical-basis.md#columnar-population-target) |
| [Columnar I02](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I02) | Select canonical item text and ordered commitments preserving current identities. Native validation and all supported value-state parity belong with [SBX-01/02](set-based-execution/populations-rules-and-proofs.md#typed-item-admission). |
| [Columnar I03](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I03) | Select generic logged item rows, protected COPY intake and typed refusal outcomes for population calls. Defer direct COPY into retained storage pending an attempt-scoped permission design. [Admission](set-based-execution/populations-rules-and-proofs.md#typed-item-admission) |
| [Columnar I04](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I04) | Select common member context, canonical member bodies and typed references with affected producers. [SBX-04/05](set-based-execution/references-and-projection-keys.md#columnar-reference-and-binding) |
| [Columnar I05](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I05) | Select DuckDB for local relational plans and exact detached join checks. Keep declared rule establishment native and attestation with the producer. Preserve the specific SBX-19 trial decision. [Analytical ownership](set-based-execution/kernel-trial.md#columnar-analytical-prerequisites) |
| [Columnar I06](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I06) | Select typed table acquisition, sealed IPC, fused relational plans and Arrow reader egress where composed. Acero, diagnostic COPY CTEs, federation and broader features stay conditional on a named consumer. [Engine mechanisms](set-based-execution/common-analytical-basis.md#columnar-population-target) |
| [Columnar I07](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I07) | Select typed PDF certification within SBX-14–17. Pull forward only a useful SBX-09 custody or shared-stream slice. [PDF](set-based-execution/pdf-path.md#columnar-pdf-certification) |
| [Columnar I08](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I08) | Select scoped binding reuse and indexed item access. Retain actual producer decisions as explicit inputs. [SBX-05/06](set-based-execution/references-and-projection-keys.md#columnar-reference-and-binding) · [SBX-11](set-based-execution/owner-resolved-reads.md#columnar-selected-read) |
| [Columnar I09](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I09) | Select authenticated hydration keys and one acquired interpretation for affected paths. Limit residual JSON and draft cleanup to the replacement boundary. [SBX-08](set-based-execution/validated-values-and-handoff.md#typed-worker-custody) |
| [Columnar I10](../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I10) | Select shared engine and worker resource policy and exact fixture reuse before qualification. [Cutover](set-based-execution/cutover-and-qualification.md#columnar-cutover-sequence) |
| [Redesign I01](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I01) | Select one preparation of each admitted premise projection and reuse acquired construction views. [SBX-02/04](set-based-execution/populations-rules-and-proofs.md#typed-item-admission) |
| [Redesign I02](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I02) | Select annotation through canonical publication and construction as the first complete replacement. [Shared target](set-based-execution/common-analytical-basis.md#columnar-population-target) |
| [Redesign I03](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I03) | Select the early point and bulk/replay slice for SBX-09. General read programs, cursors and Parquet verifier retirement follow in SBX-11/12. [Read owner](set-based-execution/owner-resolved-reads.md#columnar-selected-read) |
| [Redesign I04](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I04) | Keep current shared attachment and completion seal reuse. Select residual mutation changes only after distinguishing work that survives the typed boundary. [SBX-06](set-based-execution/references-and-projection-keys.md#columnar-reference-and-binding) |
| [Redesign I05](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I05) | Select columnar certification and verified-byte custody in the PDF owner. [SBX-14–17](set-based-execution/pdf-path.md#columnar-pdf-certification) |
| [Redesign I06](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I06) | Select one lifetime for admitted values and coordinated engine settings. Verify complete backing-buffer, reader and spill release. [SBX-08/09](set-based-execution/validated-values-and-handoff.md#typed-worker-custody) |
| [Redesign I07](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I07) | Select exact committed-cut ADBC bulk reads and same-session Psycopg/pgpq writes. Defer ADBC ingestion and direct federation unless a whole owned operation warrants them. [Transfer](set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer) |
| [Redesign I08](../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I08) | Select stable-source receipt reconciliation and one managed bounded qualification owner. [Cutover](set-based-execution/cutover-and-qualification.md#columnar-cutover-sequence) |

The [rule changes](#columnar-rule-confirmation) were accepted on 2026-11-23. The replacement
and its applicable verification are complete through the
[development reset](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09).
Historical findings and receipts retain their dates and exact scope.

<a id="post-sbx-09-review-amendment"></a>
## Post-SBX-09 review amendment

**Scheduled · 2026-11-23.** Integrate the two post-cutover reviews at `c1d834921` and
`afb63f87a`. PostgreSQL owns scope, current authority, settlement and committed effects.
Arrow carries finite acquired facts. DuckDB composes local relational work over those facts.
Detached replay reuses verification only within acquired custody of the verified bytes.
Keep the installed development checkpoint and the existing evidence distinctions. The
retained Parquet probe establishes pathname-replacement behavior on its fixture.
[Development checkpoint](../../STATUS.md) ·
[Parquet custody probe](../design_review/evidence/2026-11-23_sbx-parquet-scan-custody/README.md)

| Finding | Scheduled owner and closure |
|---|---|
| [I01](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I01) | [SBX-11](set-based-execution/owner-resolved-reads.md#sbx-address-led-reads) seeks first and batches references. Exercise unrelated support inside the selected obligation, oversized unselected bodies and revoked continuation. |
| [I02](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I02) | [Early SBX-12 reader](set-based-execution/owner-resolved-reads.md#sbx-acquired-reader) supplies the common live and detached interpretation. Establish protected-issuer and ordinary-report parity before removing displaced indexes. |
| [I03](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I03) | [SBX-12](set-based-execution/owner-resolved-reads.md#sbx-verified-archive) verifies cold closure and reuses it inside stable custody. Compare point and full replay from sorted row groups before considering page or side indexes. |
| [I04](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I04) | [SBX-14–17](set-based-execution/pdf-path.md#columnar-pdf-certification) check typed relationships and preserve canonical frames on genuine recovery. [SBX-20](set-based-execution/cutover-and-qualification.md#native-revisions) attributes split producer effects. |
| [I05](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I05) | [SBX-18](set-based-execution/kernel-trial.md#sbx-durable-analytical-output) compares the sealed output route through transactional COPY. Require exact commitments, safe failure and recovery, and reduced overlap of whole results. |
| [I06](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I06) | [SBX-19](set-based-execution/kernel-trial.md#sbx-19) compares one complete typed relational candidate with the current acquired route. Decide after publication, exact nomination and selected readback. |
| [I07](../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I07) | [SBX-20](set-based-execution/cutover-and-qualification.md#sbx-20) compares direct, shared and material effects before stage. Any narrower admission or receipt boundary remains conditional. |
| [I08](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I08) | [SBX-06 coverage](set-based-execution/references-and-projection-keys.md#settlement-coverage) and [SBX-11 freshness](set-based-execution/owner-resolved-reads.md#freshness-aware-reads) follow qualified dependencies. Exercise sibling and cross-source coverage, historical authorization and current membership. |
| [I09](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I09) | [Typed acquisition](set-based-execution/owner-resolved-reads.md#sbx-acquired-reader) covers change impact and phased interpretation. [SBX-13](set-based-execution/owner-resolved-reads.md#sbx-13) preserves distinct evaluation cuts and independent controls. |
| [I10](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I10) | [SBX-12](set-based-execution/owner-resolved-reads.md#sbx-verified-archive) binds verification and lazy scans to the same stable bytes. Exercise path replacement and in-place mutation across the consumption window. |
| [I11](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I11) | [SBX-15](set-based-execution/pdf-path.md#sbx-pdf-sparse-access) publishes sparse access relations for readers and certification. Verify authorized selection, report order, and exact oversized refusal before transfer. |
| [I12](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I12) | [SBX-16](set-based-execution/pdf-path.md#sbx-pdf-payload-layout) compares actual bytes acquired and decoded on a recovered sparse page. Layout and Acero remain conditional decisions. |
| [I13](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I13) | [SBX-18](set-based-execution/kernel-trial.md#sbx-durable-analytical-output) compares physical cohorts and byte-aware folding with independent commitments. [SBX-19](set-based-execution/kernel-trial.md#sbx-19) uses the installed handoff and complete trial boundary. |
| [I14](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I14) | [SBX-18 allocation](set-based-execution/kernel-trial.md#sbx-analytical-job-allocation) exercises concurrent admitted jobs, a partial reader, cancellation and scratch cleanup. |
| [I15](../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I15) | [SBX-10 runtime custody](set-based-execution/validated-values-and-handoff.md#sbx-consumed-runtime-custody) verifies consumed nodes and installed math. [SBX-20–22](set-based-execution/cutover-and-qualification.md#sbx-20) account for registered effects, last-consumer retirement and final evidence. |

The existing [decision routes](set-based-execution/common-analytical-basis.md#decision-routes)
govern any rule change revealed by a comparison. Conditional alternatives from the reviews
have decision criteria in their owning packages. Each decision retains the baseline when the
candidate cannot preserve semantics and custody or remove material end-to-end work. Timing is
reserved for comparisons where it can change a choice.

## Completion

The series is complete when the registered chain carrying A, B and C effects is deployed on stage;
the whole-book qualification input runs through the new path; SBX-22's assembled evidence is recorded,
including the [shared change scenarios](set-based-execution/cutover-and-qualification.md#change-scenarios)
and the applicable native propagation and read coverage;
superseded machinery and its mechanism-specific tests are gone, with independent semantic
expectations carried to the replacement; and the owning design sections and decision records
describe the implemented state. SBX-09 delivered the development baseline for that work.
Record the scoped-relations adoption decision in SBX-19 and qualify the
adopted read, replay and analytical routes at the applicable final-source boundary.

SBX-00 records the focused Revision A target review and its disposition. Revision A registration
and assembled qualification retain their package acceptance.

## Risks

- **The form vocabulary grows into a language.** A rule that fits no form is attested until two
  rules want the same form. If more than about a third of the first population's rules do not
  fit after normalization, the vocabulary is wrong and SBX-02 stops to say so.
- **An under-declared read gives unsound reuse.** Reads are derived from form parameters and
  enforced by what a kernel is handed; they are never authored separately from the mechanism.
- **Role-relative references make a body unreadable without its inputs.** Readers that follow
  references without a derivation (serving, evaluation, detached verification) are migrated in
  the same strand; SBX-05 lists them.
- **Exact identity across a physical replacement.** Compile and compare independent vectors
  for the supported model values before native registration. Verify the composed producer,
  admission and consumer route on the intended purpose roles before authoring the integrated root.
- **Work in the same tree.** Other work is editing production source. Each package re-reads its
  baseline at entry and records drift.
