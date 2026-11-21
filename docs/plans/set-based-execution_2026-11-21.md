# Set-based execution

**Status:** In implementation. SBX-00 and SBX-01 are authorized. This series owns the pivot to
partition-unit storage, declared rules and proofs, projection-keyed reuse, owner-resolved reads
and the single-derivation PDF path. **Created:** 2026-11-21.

**Basis.** The [execution outside PostgreSQL review](../functional_reviews/columnar-execution-outside-postgresql_2026-11-21.md)
at revision `b8109d423` (T1–T9, O01–O19, six defects). Nine investigations and one independent
design advice read production source at `7a415d18d` on 2026-11-21; source facts below are
**Inspected** at that commit unless a sentence says inferred. Every design statement is
**Proposed**. Nothing was executed against PostgreSQL and no timing was taken, so no benefit is
quantified. `cs/` means `python/corpus-structure/src/corpus_structure/`.

**Framing (operator, 2026-11-21).** This is a hard pivot in the design phase. The series goes
directly to the target design and validates it once. There is no compatibility layer, no dual
shape and no preserved identity; all derived data is regenerated. Existing plan series are not
edited by this series and will be superseded separately.

## Outcome

After this series, what executes outside PostgreSQL rests on one modelled basis.

- **A homogeneous population is stored once, as partitions.** Tokens, sentences and HanLP units
  live as one tagged body per block with its own digest; the product keeps a header and a root.
- **Rules are model declarations.** Each names what it reads and its scope. PostgreSQL evaluates
  declared forms at admission, one partition at a time; rules it cannot evaluate are attested by
  their producer.
- **A proof is a content-addressed fact** keyed on a rule fingerprint and the digest of what the
  rule was evaluated on. There is no invalidation step: a proof stops matching only when the model
  facts the rule reads change or the content changes. A point check is three keyed lookups.
- **A consumer is keyed on what it reads.** Each consumer role declares its read projection; its
  request key carries the digest of that projection, so a change to fields or blocks it does not
  read leaves its key and its result untouched.
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
| Direct cutover: regenerate, no compatibility, no preserved identities | Accepted | ADR (cutover policy for this series) |
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

## Shared contracts

Each contract has one owning document. Other documents link to it and do not restate it.

| Contract | Owner |
|---|---|
| Collection, partition, partition digest, root, field group, address | [Populations, rules and proofs](set-based-execution/populations-rules-and-proofs.md#collections-and-partitions) |
| Rule declaration, form, fingerprint, attested rule | [same](set-based-execution/populations-rules-and-proofs.md#rules) |
| Proof row, premise, establish routine, required proofs at binding | [same](set-based-execution/populations-rules-and-proofs.md#proofs) |
| Reference carrier, declared target, role-relative reference, resolver | [References and projection keys](set-based-execution/references-and-projection-keys.md#the-reference-model) |
| Read projection, projection digest, request identity, partition memo | [same](set-based-execution/references-and-projection-keys.md#read-projections) |
| Validated carrier, single constructor, verification bracket | [Validated values and hand-off](set-based-execution/validated-values-and-handoff.md) |
| Read programs, answer shapes, replay relations, cursor, cache key | [Owner-resolved reads](set-based-execution/owner-resolved-reads.md) |
| PDF rebuild, access derivation, verified carriers, build identifier | [The PDF path](set-based-execution/pdf-path.md) |
| Native revisions, regeneration order, assembled evidence | [Cutover and qualification](set-based-execution/cutover-and-qualification.md) |

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
Proof premises are digests of exactly the content evaluated. Projection digests are roots over
exactly the field groups and partitions a consumer reads. Each lookup is a primary-key probe.

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

## Execution queue

Packages are described in their companions. Prerequisites are stated as the contract or
capability consumed.

| Package | Delivers | Needs | Companion |
|---|---|---|---|
| SBX-00 | Complete. Decision records, entry evidence and fixture baseline are recorded. Exact selected-use readers and detached demand ownership passed genuine finite and rich export checks. | — | [Entry and reader evidence](#sbx-00) |
| SBX-01 | Complete for generic collection declarations, partition storage, content and placement identity, field groups and block-relative addresses. Managed rollback-only candidate passed. | SBX-00 decisions | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-01) |
| SBX-02 | Rule declarations, forms, fingerprints, admission evaluation, proof rows, establish routine, proofs required at binding | SBX-01 partitions | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-02) |
| SBX-03 | Sentence, canonical and HanLP products cut over; consumers read partitions; packet machinery retired | SBX-01, SBX-02, SBX-05 carrier | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-03) |
| SBX-04 | Existing validators as attested rules; one stance at hand-off; projection families and member-level outputs retired | SBX-02 | [PRP](set-based-execution/populations-rules-and-proofs.md#sbx-04) |
| SBX-05 | One reference carrier with declared targets; role-relative references; one resolver; closure rules | SBX-01 addresses | [RPK](set-based-execution/references-and-projection-keys.md#sbx-05) |
| SBX-06 | Read projections per role; projection-keyed request identity; kernels handed their projection | SBX-01 field groups, SBX-05 | [RPK](set-based-execution/references-and-projection-keys.md#sbx-06) |
| SBX-07 | Per-partition memo for block-local kernels; decision recorded | SBX-06, SBX-03 | [RPK](set-based-execution/references-and-projection-keys.md#sbx-07) |
| SBX-08 | Validated carriers with one constructor; decode once; residue removed | — | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-08) |
| SBX-09 | One verification bracket per computation on every route | — | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-09) |
| SBX-10 | Derived views computed once; one span vocabulary; producer-published contexts | SBX-08; SBX-03 for token views | [VVH](set-based-execution/validated-values-and-handoff.md#sbx-10) |
| SBX-11 | Read programs sharing one boundary; answer shapes; filters and paging by key | SBX-01 for partition reads | [ORR](set-based-execution/owner-resolved-reads.md#sbx-11) |
| SBX-12 | Replaying readers on typed relations from either source; export carries partitions and proofs; one cursor; substantive cache key | SBX-11 | [ORR](set-based-execution/owner-resolved-reads.md#sbx-12) |
| SBX-13 | Evaluation preflight reduced to what only Python can check | SBX-11 | [ORR](set-based-execution/owner-resolved-reads.md#sbx-13) |
| SBX-14 | One document rebuild routine; round-trip validation under the captured policy | — | [PDF](set-based-execution/pdf-path.md#sbx-14) |
| SBX-15 | Access columns derived at publication; region copy retired | SBX-14 | [PDF](set-based-execution/pdf-path.md#sbx-15) |
| SBX-16 | One document per process; verified page and file carriers; build identifier at load | — | [PDF](set-based-execution/pdf-path.md#sbx-16) |
| SBX-17 | Certification without round trips; typed validation capture; logical rows by column | SBX-16 | [PDF](set-based-execution/pdf-path.md#sbx-17) |
| SBX-18 | Analytical owner states the fidelity rules; worker-lifetime connection | — | [KT](set-based-execution/kernel-trial.md#sbx-18) |
| SBX-19 | Scoped relations rebuilt as set operations; recorded decision on other families | SBX-18, SBX-08, SBX-05 | [KT](set-based-execution/kernel-trial.md#sbx-19) |
| SBX-20 | Native revisions A, B and C registered; regeneration in order | packages they carry | [CQ](set-based-execution/cutover-and-qualification.md#sbx-20) |
| SBX-21 | Retirement sweep | all | [CQ](set-based-execution/cutover-and-qualification.md#sbx-21) |
| SBX-22 | Assembled qualification, including the change scenarios | SBX-20 | [CQ](set-based-execution/cutover-and-qualification.md#sbx-22) |

**One useful route.** Three strands are independent and can proceed together.

1. *Identity strand, revision A:* SBX-01, SBX-02, SBX-05, then SBX-03, SBX-04 and SBX-06. These
   change product bodies, kinds and request identity, so they are developed against private
   candidates and registered as one revision. SBX-05 is in this strand, not after it, because the
   reference carrier re-keys every family and should do so once.
2. *No-identity strand:* SBX-08 and SBX-09 first, since they change no published value and every
   later package is simpler on carried values; then SBX-10. The read strand SBX-11 to SBX-13
   follows SBX-01 and lands as revision B.
3. *PDF strand, revision C:* SBX-14 to SBX-17, independent of the others.

SBX-07 and the kernel trial follow the identity strand. SBX-20 to SBX-22 close the series.

**No interim forms.** The review's incremental items are not built where a package here deletes
their subject: memoising the derivation of token rows from annotations (the derivation goes in
SBX-03), cheaper lookups on the SQLite index for online readers (SBX-11 removes the index from
their path), and a proof contract for the sentence validator in today's receipt format (SBX-04
re-keys all proofs).

<a id="sbx-00"></a>
## SBX-00 — Decisions, entry checks and baseline

**Decisions recorded · 2026-11-21.** ADR-0143 through ADR-0148 record the accepted targets and
their governing design sections. The focused
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
and explicit null. Reconverted positional pointers still require established block correspondence
before cross-original reuse. SBX-05 owns citation-to-input gaps, SBX-02 checks proofs at binding
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
| O01 one Arrow schema derivation | Absorbed: SBX-12 derives replay relation schemas from the physical model; no general derivation is built without a consumer |
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
| Declined in the review | Stay declined: Arrow worker packet, second identity encoder, deriving the JSON access copy in SQL, a digest pass on transform input, byte-budget paging changes |

Added by this plan beyond the review: projection-keyed request identity and the partition memo
(SBX-06, SBX-07), block-relative addresses and field groups (SBX-01), and proofs keyed on rule
fingerprint and content in place of release and product (SBX-02).

## Completion

The series is complete when revision A, B and C are registered and deployed on the stage target;
the retained book is regenerated through the new path; SBX-22's assembled evidence is recorded,
including the four change scenarios; superseded machinery is gone with its tests; and the owning
design sections and decision records describe the implemented state. The kernel trial is complete
when its decision is recorded, whichever way it goes.

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
