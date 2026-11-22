# Set-based execution

**Status:** Implementation is paused through SBX-09. The efficiency amendment is scheduled.
SBX-00 through SBX-02 have package evidence. SBX-03 through SBX-09 have partial implementation and
scoped verification. This series owns the pivot to
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
native attribution and qualification after the pause.
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

- **A homogeneous population is stored once, as partitions.** Tokens, sentences and HanLP units
  live as one tagged body per block with its own digest; the product keeps a header and a root.
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
| Model-derived relation projections, early population pilot, PostgreSQL placement and transfer | [Common analytical basis](set-based-execution/common-analytical-basis.md#projection-contract) |
| Read programs, answer shapes and freshness disclosure, replay relations, cursor, cache key | [Owner-resolved reads](set-based-execution/owner-resolved-reads.md) |
| PDF rebuild, access derivation, verified carriers, build identifier | [The PDF path](set-based-execution/pdf-path.md) |
| Early integration, development reset, native revisions, shared scenarios, assembled evidence | [Cutover and qualification](set-based-execution/cutover-and-qualification.md) |

## The design in one page

**Unit.** A product is a header plus collections. A collection declares its unit:

| Unit | Families | Unit identity | Storage |
|---|---|---|---|
| partitioned | tokens, sentences, HanLP units | partition digest | `kb.data_product_partition` |
| identified | formal, construction, contextual and rich graph members; candidate records | the content-hash id | `kb.data_product_member` |
| bound | source views, manifests, contextual target members, candidate contributions | member id with its context | `kb.data_product_member` |

Rules and proofs use the same tables for all three. One model, not two.

**Why partitions and not rows per token.** Nothing in PostgreSQL consumes tokens relationally;
every consumer is Python reading a block. A typed row per token would need a table and a revision
per record type and a second identity protocol. A list inside the body cannot be read by key at
all. If a consumer of token-level joins appears (the kernel trial, a read program), typed rows are
added as a projection derived from partitions, never as the authority.

**Why this meets the two tests.** Rule fingerprints are computed from the model facts a rule
reads, through the same rooted-closure mechanism that already makes kind identity substantive.
Proof premises and projection digests commit to the facts the rule or consumer observes.
A point lookup uses keyed metadata, required support, and at most the addressed body when
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

A change that would reopen the design: a consumer that needs keyed access to items across
partitions inside PostgreSQL at a rate partitions cannot serve, or evidence that blocks are so
uneven that a partition is in practice the whole product.
The [early pilot](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)
selected the acquired immutable carrier for the actual annotation consumers. A change to authoritative
layout follows the [decision route](set-based-execution/common-analytical-basis.md#decision-routes).

## Execution queue

Packages are described in their companions. Prerequisites are stated as the contract or
capability consumed.

| Package | Delivers | Needs | Companion |
|---|---|---|---|
| SBX-00 | Complete. Decision records, entry evidence and fixture baseline are recorded. Exact selected-use readers and detached demand ownership passed genuine finite and rich export checks. | — | [Entry and reader evidence](#sbx-00) |
| SBX-01 | Complete for generic collection declarations, partition storage, content and placement identity, field groups and block-relative addresses. Managed rollback-only candidate passed. | SBX-00 decisions | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-01) |
| SBX-02 | Implemented and tested for the native forms, retained establishment, product and partition attestations, and binding. Rollback-only candidate passed. | SBX-01 partitions; shared premise and scenario contract | [PRP and remaining adoption conditions](set-based-execution/populations-rules-and-proofs.md#sbx-02) |
| SBX-03 | In progress. Migrated annotation consumers bind layout, membership and coverage proofs. The registered checkpoint passed governed CUDA canonical adoption after a different real annotation capture, and selected readback of moved, renamed, repeated, split and merged blocks. Final-root acceptance stays open. The pilot selected the acquired immutable annotation carrier. | SBX-01 partitions, SBX-02 proof binding, SBX-05 resolver and SBX-08 acquired carriers | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-03) · [Pilot decision](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence) |
| SBX-04 | In qualification. Construction binds the original selected annotation block, token and layout. Contextual acquisition consumes that establishment and the exact supporting input. External premises and packed choices use original roles. Released attachment-policy witnesses have declared attestations. | SBX-02 | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-04) |
| SBX-05 | In qualification. Construction, contextual discovery, declaration, artifact, comparison and contribution reports declare original role addresses for computational evidence. The two remaining parent dependency lists are retired. Selected complete graph readers acquire one authentic original binding. SBX-11 owns the keyed read. | SBX-01 addresses | [RPK](set-based-execution/references-and-projection-keys.md#sbx-05) |
| SBX-06 | In qualification. Registered controls passed ordinary committed-gap recovery, both cross-demand commit orders, exact pins, original and selected population wakes, scalar and closed collection unavailability, and terminal empty discovery. Recursive readiness state and repeated readiness scans are retired. Proof-uncertain and nonempty qualified-context scopes retain pending standing until authoritative settlement. | SBX-01 field groups and SBX-02 shared premises, plus runnable SBX-03–05 address, proof and binding slices | [RPK](set-based-execution/references-and-projection-keys.md#sbx-06) |
| SBX-07 | In progress. Canonical retains deterministic local rows across pointer renames and assembles current addresses and placement. The governed CUDA move, rename and split/merge control passed on the registered checkpoint. The other current hosts keep whole-result execution. Final-root acceptance stays open. | SBX-06, SBX-03 | [RPK](set-based-execution/references-and-projection-keys.md#sbx-07) |
| SBX-08 | In progress. Acquired source frames and immutable partition, formal, interpreted and composed payloads have scoped evidence. The pilot selected their existing annotation hand-off. All five native stream checks passed on a registered checkpoint. The live-page and witness changes are scheduled. Final integrated native acceptance stays open. | SBX-04/05 proof and address contracts | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-08) |
| SBX-09 | In progress. CPU, canonical, PDF and learned paths carry acquired verification. PDF region and visual workers verify after encoding, and the late-import and encoding-time tamper controls passed. Final registered-root provider and custody verification stays open. | Integrated SBX-03–08 behavior and final-source correspondence to the registered root | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-09) · [CQ](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09) |
| SBX-10 | Derived views computed once; one span vocabulary; producer-published contexts | SBX-08; SBX-03 for token views | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-10) |
| SBX-11 | Read programs with scoped authority acquisition, answer shapes, filters, keyset paging and explicit freshness disclosure | SBX-01 for partition reads; SBX-02 for proof answers; SBX-06 settlement coverage for the freshness slice | [ORR](set-based-execution/owner-resolved-reads.md#sbx-11) |
| SBX-12 | Selected structural Parquet replay, partition and proof export, unified cursor and substantive cache with current authority | SBX-11; SBX-02 proof and SBX-05 reference contracts for affected relations; projection contract from the pilot | [ORR](set-based-execution/owner-resolved-reads.md#sbx-12) |
| SBX-13 | Evaluation preflight reduced to what only Python can check | SBX-11 | [ORR](set-based-execution/owner-resolved-reads.md#sbx-13) |
| SBX-14 | One document rebuild routine; round-trip validation under the captured policy | — | [PDF](set-based-execution/pdf-path.md#sbx-14) |
| SBX-15 | Access columns derived at publication; region copy retired | SBX-14 | [PDF](set-based-execution/pdf-path.md#sbx-15) |
| SBX-16 | One document per process; verified page and file carriers; build identifier at load | — | [PDF](set-based-execution/pdf-path.md#sbx-16) |
| SBX-17 | Certification without round trips; typed validation capture; logical rows by column | SBX-16 | [PDF](set-based-execution/pdf-path.md#sbx-17) |
| SBX-18 | Fidelity, captured authoring and job resource contracts for the analytical trial | — | [KT](set-based-execution/kernel-trial.md#sbx-18) |
| SBX-19 | Complete scoped-relations comparison through exact artifact nomination and a recorded adoption decision | SBX-18, SBX-08, SBX-05; SBX-06 to qualify projection-keyed reuse | [KT](set-based-execution/kernel-trial.md#sbx-19) |
| SBX-20 | Native revisions A, B and C registered after applicable comparisons and installed on stage | packages they carry | [CQ](set-based-execution/cutover-and-qualification.md#sbx-20) |
| SBX-21 | Retirement sweep, including confirmation of SBX-06 watermark and sweep removal | replacement paths and migrated consumers | [CQ](set-based-execution/cutover-and-qualification.md#sbx-21) |
| SBX-22 | Final-source qualification, including the shared change scenarios | SBX-20, SBX-21 | [CQ](set-based-execution/cutover-and-qualification.md#sbx-22) |

**One useful route.** Development can overlap at the contract boundaries below.

1. *Identity strand, revision A:* Build on the installed collection and proof foundations and
   the chosen annotation carrier. Use the [installed successor](set-based-execution/cutover-and-qualification.md#early-revision-a-integration)
   to integrate remaining proof, address, settlement and memo behavior. The SBX-09 development
   reset installs its sole cold root. SBX-20 owns stage registration and installation.
2. *Carriers and custody:* Finish SBX-08/09 hand-off and verification work alongside settlement
   once the shared proof and reference contracts are available. Prepare SBX-11 to SBX-13 against
   those contracts. Integrate governed freshness when SBX-06 supplies native coverage.
   Register B after A.
3. *PDF strand, revision C:* SBX-14 to SBX-17 can develop alongside the other strands. Candidate
   comparisons account for shared installed effects, and fresh qualification starts with PDF capture.

SBX-07 follows the runnable identity and population contracts. The kernel trial follows its
own input, carrier and reference dependencies. SBX-20 to SBX-22 close the series.

### Remaining execution through SBX-09

**Scheduled execution sequence · 2026-11-22.** Use the recorded
[typed-population decision](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)
and the [efficiency amendment](#validation-postgresql-efficiency-amendment).

1. Establish [stable source, verified fixture preparation and required test identities](set-based-execution/cutover-and-qualification.md#sbx-efficiency-qualification)
   before new diagnostics. Promote the [live-page handoff](set-based-execution/validated-values-and-handoff.md#sbx-live-page-handoff)
   and [metadata-only summary correction](set-based-execution/owner-resolved-reads.md#sbx-live-summary-correction)
   together through scoped verification before broad retry.
2. In parallel on a stable registered root, attribute the slow [native read](set-based-execution/owner-resolved-reads.md#sbx-native-read-attribution)
   and [attachment and completion](set-based-execution/references-and-projection-keys.md#sbx-native-attachment-and-completion)
   paths. Apply the [pre-reset selection criteria](set-based-execution/cutover-and-qualification.md#sbx-efficiency-qualification)
   to any correction. SBX-05 supplies the scalar construction caller and exact occurrence contract.
   SBX-11 owns both its conditional early read slice and the later read program.
3. Close remaining family and governed-change acceptance in SBX-03–07 through the
   [installed successor](set-based-execution/cutover-and-qualification.md#early-revision-a-integration).
   Exercise ordinary resume and scoped coverage on the current settlement route. Recursive
   readiness state and repeated scheduler scans are retired in source. Use the remaining
   reference and proof work to identify any needed upstream corrections.
4. Finish [carrier and witness handoffs](set-based-execution/validated-values-and-handoff.md#sbx-witness-handoff)
   and verify current worker custody on the installed route. Preserve the implemented
   post-encoding checks for PDF regions and visual mapping. Include the affected ordinary,
   native, worker and detached consumers in targeted verification.
5. Reuse the registered sole root when it corresponds to final source. Renew authoring,
   registration and installation when captured native artifacts change. Qualify the final
   source and installed root on newly admitted data, then reinstall development empty on
   the dedicated cluster. [Reset and acceptance](set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

**No interim forms.** The review's incremental items are not built where a package here deletes
their subject: memoising the derivation of token rows from annotations (the derivation goes in
SBX-03), cheaper lookups on the SQLite index for online readers (SBX-11 removes the index from
their path), and a proof contract for the sentence validator in today's receipt format (SBX-04
re-keys all proofs).

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

**Pilot decided · 2026-11-22.** SBX-03/08 retain the acquired immutable annotation carrier.
Primary construction now uses its admitted row blocks directly. The combined real provider
fork passed on a private current-source root. The final registered root and remaining SBX-09
acceptance stay with the cutover owner. [Pilot evidence and decision](set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)

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
| [I01](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I01) | [SBX-08 live-page handoff](set-based-execution/validated-values-and-handoff.md#sbx-live-page-handoff) and [SBX-11 summary correction](set-based-execution/owner-resolved-reads.md#sbx-live-summary-correction) are scheduled together before broad retry. Tag-directed raw validation remains conditional. |
| [I02](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I02) | [SBX-11 native read attribution](set-based-execution/owner-resolved-reads.md#sbx-native-read-attribution) owns the early keyed decision and later online migration. SBX-05 supplies the reference caller and occurrence contract. SBX-12 carries cursor and replay effects. |
| [I03](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I03) | [SBX-06 native attachment](set-based-execution/references-and-projection-keys.md#sbx-native-attachment-and-completion) owns attribution and selection of invariant sharing. SBX-05 supplies exact role and occurrence authority. |
| [I04](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I04) | [SBX-06 completion attribution](set-based-execution/references-and-projection-keys.md#sbx-native-attachment-and-completion) owns seal and retention alternatives. SBX-04 owns proof identity and SBX-08/09 own acquired values and worker fences. |
| [I05](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I05) | [SBX-08/09 witness handoff](set-based-execution/validated-values-and-handoff.md#sbx-witness-handoff) schedules scoped preparation and selects the checking route by correspondence and diagnostic parity. |
| [I06](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06) | [Common analytical basis](set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer) owns shared placement and fidelity. SBX-11/12 use them for selected reads and finite replay. SBX-18/19 retain the named whole-route trial. |
| [I07](../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I07) | [Qualification](set-based-execution/cutover-and-qualification.md#sbx-efficiency-qualification) owns stable source, bounded cohorts, preparation reuse and evidence reconciliation. SBX-22 uses the same applicable safeguards. |

Apply the [documented decision routes](set-based-execution/common-analytical-basis.md#decision-routes)
before any later alternative changes a binding rule. Required qualification and the empty
development reset retain their existing sequence and scope.

## Completion

The series is complete when revision A, B and C are registered and deployed on the stage target;
the whole-book qualification input runs through the new path; SBX-22's assembled evidence is recorded,
including the [shared change scenarios](set-based-execution/cutover-and-qualification.md#change-scenarios)
and the applicable native propagation and read coverage;
superseded machinery and its mechanism-specific tests are gone, with independent semantic
expectations carried to the replacement; and the owning design sections and decision records
describe the implemented state. Record the annotation-fork decision and qualify its integrated
route at the SBX-09 reset. Record the scoped-relations adoption decision in SBX-19 and qualify the
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
- **One large identity revision.** Revision A is developed against private candidates with
  rollback-only authoring and is registered once. Its packages have their own acceptance, so a
  failure is located before registration.
- **Work in the same tree.** Other work is editing production source. Each package re-reads its
  baseline at entry and records drift.
