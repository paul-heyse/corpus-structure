# Populations, rules and proofs

**Status:** SBX-01 and SBX-02 have scoped native evidence. SBX-03 and SBX-04 are in progress.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md),
which owns package state, decisions and the disposition table. **Created:** 2026-11-21.

This companion owns the central contracts of the series: how a homogeneous population is stored
and identified, how rules are declared and checked, and what a proof is. It owns packages
SBX-01 to SBX-04. Source facts are **Inspected** at `7a415d18d`; design statements are
**Proposed**. `cs/` is `python/corpus-structure/src/corpus_structure/`.

The [post-SBX-01 amendment](../set-based-execution_2026-11-21.md#post-sbx-01-review-amendment)
integrates review [I01–I04](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I01).
The contracts below are the planned target; they do not expand SBX-01's completed native scope.

## Baseline

- A product body is a tagged value stored once in `kb.data_product.canonical_body`. A field read
  in PostgreSQL (`ddo_field`, `cs/semantic/data_operation_value_native.py`) is a linear scan;
  nothing inside a body can be read by key.
- `members[]` is a sequence in the body, one `kb.data_product_member` row per packet, and a third
  copy in the wire completion. Identity is over the body only; rows are checked equal to it.
- A member is a packet of exactly four fields. `members` is a property name the compiler treats
  specially (`cs/semantic/data_operation_member_contracts.py`, `derive_member_kinds`); a
  collection under any other name is a plain list and needs no admission change.
- `DdoSourceAnnotations` already holds tokens and sentences twice in its body: typed lists per
  block under `blocks[].annotation`, and packets derived from them and rejected on mismatch
  (`cs/semantic/sentence_products.py`, `source_annotation_packets`,
  `validate_source_annotations`). `DdoCanonicalSentences` and `DdoHanlpInventory` hold them only
  as packets.
- Offsets are absolute in the source projection (`cs/ingest/annotations.py`), so text inserted
  before a block changes that block's body and every later one.
- Admission checks shape, identity, kind membership and member-id uniqueness. Every set rule
  lives in Python and is repeated by consumers.
- The only proof is one `ProductValidation` receipt per whole body, keyed on release id,
  validator asset digest and body id, stored inside the completion payload
  (`cs/semantic/established_validity.py`). PostgreSQL checks its correspondence, not that
  validation ran. On an ambiguous validator revision the producer silently emits no proof.
- Kind identity is already substantive: `kind_fingerprint` is a rooted closure over the model
  graph (`cs/semantic/data_operation_identity.py`, `SemanticGraph.rooted_record`), and the graph
  has property nodes.
- Five typed member projection tables exist with admission checks and two readers; no kind
  declares them and no typed producer can feed them.

## Collections and partitions

A kind declares **collections** on its multivalued slots. A collection declares its unit
(partitioned, identified or bound), and for a partitioned collection its partition key, its item
order, the fields that form an item's address, and its **field groups**.

**Storage.** `kb.data_product_partition(product_id, collection, partition_key, ordinal,
partition_digest, item_count, group_digests, placement, body)`, primary key on the first three, with an
index for ordinal order. `body` is the tagged value of one partition. `group_digests` is a
mapping from field-group name to the digest of that group's values in item order.

**Identity.** `partition_digest = ddo_identity('partition', body)`, with its Python twin through
`canonical_identity`. The existing identity function already takes its domain as a parameter, so
no new hashing protocol is introduced. In the product header the collection property becomes a
record of content root, placement root, partition count and item count. The content root is the
identity of key-sorted `(partition_key, partition_digest)` pairs. The separate placement root
authenticates key, ordinal and absolute extent. Both enter the header and its product identity.
A field group's root is computed the same way over `(partition_key, group digest)`
pairs when a projection needs it ([read projections](references-and-projection-keys.md#read-projections)).

**Field groups.** A field group is a named set of an item's fields that is read together: for
tokens, for example, geometry (`start`, `end`, `space`), sentence membership, lexical labels
(`lemma`, `pos`, `tag`, `morphology`), dependency (`head`, `dependency`) and layout
(`piece_indices`). Groups are declared in the model because they are the granularity at which a
consumer's key can ignore a change. Too many groups cost digests; too few forfeit reuse. SBX-01
fixes the first populations' groups from the read sets the consumers actually have.

For the first cutover, annotation and canonical token groups separate span and segmentation,
sentence membership, lexical labels, dependency and layout. Sentence spans and membership supply
HanLP batching and construction matching. HanLP groups separate token alignment, dependency,
constituency and semantic roles, keyed to the canonical sentence in its block of origin. Whole
coverage and outcome remain product facts. SBX-03 binds these groups to the executable slots and
SBX-06 binds consumer projections. Group rows preserve omitted fields and explicit nulls.

**Block-relative addresses.** Offsets stored in a partition are relative to the block's start.
Absolute extent is stored as keyed placement and authenticated by the placement root. A token's address is
`(collection, block_id, start, end)` with relative offsets. The address is what today's hashed
id is computed from, left unhashed and stable for an unchanged block key. An absolute offset is
the block start plus the relative offset. A consumer that observes order or absolute position needs
the corresponding placement premise. Text content and body-relative geometry are independent of
page placement when neither reads that placement. The same declared-premise contract governs
reads, proof matching and computation invalidation; complete local projections can remain equal
after the source identity or page position changes.

**Occurrence and equivalence.** Acquisition and lowering in SBX-03 identify the exact current
block occurrence; SBX-05 carries it through reference resolution. Reconversion can rename
positional source pointers. Equal complete projections can establish computational equivalence
without a cross-source occurrence map, but they do not identify which repeated paragraph or
identical table cell is a particular occurrence. Locating or rebinding an occurrence after
renumbering, splitting or merging needs its own correspondence evidence. Acquire current
partitions afresh where correspondence is unknown; do not infer it from equal text. SBX-06
separates reusable computation from authenticated occurrence binding, and SBX-07 uses
source-local keys where sufficient. The shared [change scenarios](cutover-and-qualification.md#change-scenarios)
distinguish these claims.

**Normalization before rules.** The token-to-sentence link is stored one way, as the sentence's
ordinal on the token. `token_ids`, `sentence_ref`, `head_ref` and the separate `lexemes` list are
not stored; lexeme columns merge into tokens. "A token is in at most one sentence", "the two
directions agree" and "lexeme count equals token count" then cease to be rules.

**The other units.** Identified and bound collections keep `kb.data_product_member`. For an
identified collection the member's content-hash id is the unit digest. Nothing about the four
bound kinds changes.

*Alternatives rejected.* A typed list inside the body: no keyed access, and the only premise for
any rule is the whole body. One typed row per token: no PostgreSQL consumer, a table and revision
per record type, and reconstruction of tagged values from columns with an absent-against-null
hazard. Generic member rows without the wrapper: keeps per-item rows and the row-against-body
equality check and adds no set semantics. Building on the five projection families: they were a
second copy with an equality check, opt-in, in fixed shapes; here the partition is the only
store and a collection kind cannot be published any other way.

*What would reopen it.* A PostgreSQL consumer of token-level joins: add typed rows as a
projection derived from partitions. Blocks so uneven that one partition is most of a product: a
secondary split, decided at SBX-00.

## Rules

A rule is a declared node in the model graph with: an identity; the collection it belongs to; a
scope (`partition`, `partition-pair`, `product`); a **form** with parameters; the fields it
reads, as typed paths; and a checker, `admission` or `producer`.

**Forms.** Five set forms: `unique`, `dense_ordinal`, `ordered_by`, `span_within`, `refers_to`.
Row-local predicates reuse the closed expression vocabulary already compiled for physical tables
(`PhysicalExpression`, `cs/schema/relational.py`), generalized from a table to a selection over a
partition body's items. Paths reuse the output-witness path language
(`cs/semantic/data_operation_output_witnesses.py`), which already resolves paths against property
nodes and refuses unknown fields.

**Where a rule is checked.** A rule in a declared form is evaluated once, by PostgreSQL at
admission, over one partition (or one pair). There is no Python interpreter for forms, so there
is one semantics, and no producer precheck. A rule PostgreSQL cannot evaluate is an **attested**
rule: its producer runs it and the result is recorded as a proof bound to the derivation. The
rules that read the source text are attested (a block's text equals the source slice; native
pieces equal the selected pieces). Consumers check nothing; binding looks proofs up.

**Fingerprint.** A rule's fingerprint is the identity of its form, parameters, scope, the rooted
records of the property nodes it reads, and its checker determinant. Edges run from the rule to
the properties, so kind fingerprints and product ids do not move when a rule changes. For an
attested rule the checker determinant is the code identity rooted at that rule's own function,
which the existing analysis already narrows to determining definitions
(`cs/semantic/code_identity.py`).

**Reads are derived, not authored.** A form's reads follow from its parameters. An attested
rule's reads are the field groups its function is handed
([enforcement by construction](references-and-projection-keys.md#read-projections)).

*Guard on the vocabulary.* A rule that fits no form is attested until two rules want the same
form. Of about twenty rules written out for the first populations, the ones that read the source
and the product-level summaries do not fit; the rest are per row, per block, per sentence or per
reference. If more than about a third fail to fit after normalization, SBX-02 stops and reports.

## Proofs

The content conclusion in `kb.data_validity` has key `(rule_fingerprint, premise)` and is
written only by security-definer programs. `sem.data_rule(release_id, rule_id, fingerprint, …)` holds each
release's current fingerprints. Its establishment provenance is a separate relation: one
conclusion can have multiple establishments. SBX-02 settles whether existing derivation and
support facts can carry them or whether a dependent establishment table is needed. A single
`established_by` or `derivation_id` on the content-keyed row must not make its first producer
the conclusion's permanent authority.

**Premise.** Use the digest of the facts the rule observes. A rule over all relative partition
content can use the partition digest directly. Narrower rules use the relevant group digests.
Rules that observe placement, order, selected source text or membership include those premises.
Pair and cross-product rules combine the required digests in declared order. A product-scope rule
that observes the whole header can use the body digest. A roll-up binds the corresponding
collection premises after every partition has its proof.

SBX-02 derives these facts from the actual checker boundary, with SBX-06 deriving consumer
premises from the values supplied to kernels. Both consume the same keyed metadata projection,
but hash only their own observed facts. The [change scenarios](cutover-and-qualification.md#change-scenarios)
are input to these contracts before either package makes its selection executable: movement,
reorder, membership changes, field-group edits, absent versus explicit null, rule edits and a
first matching proof must have independently stated effects. A completeness, absence or halo
read includes the membership facts it observes; stable existing partition digests alone cannot
represent those reads.

**Content matching.** A proof conclusion is an immutable fact about content. Whether it matches is a
join: a release whose rule reads an unchanged closure computes the same fingerprint, and every
existing proof still matches; a changed closure gives a new fingerprint under which no proof
exists. Re-establishing evaluates only the missing rule and partition pairs, set-wise, with the
same routine admission calls. Neither the release nor the product is in the key.

**Establishment and authority.** SBX-02 and SBX-04 distinguish deterministic native conclusions
over immutable content from attested conclusions that require a currently admissible
establishment. A matching content key does not by itself confer current authority. Binding
checks the required establishment policy alongside current selected support, revocation and
publication fences, outside the support-validity fixpoint, as required by
[ADR-0146](../../adr/0146-sbx-content-validity.md). A different admissible establishment may
sustain the same conclusion; when none exists, the rule's declared failure policy governs
binding. Resolve this classification and its storage before SBX-06 or SBX-07 attaches reused
work. Replay and resolvers preserve original producing inputs separately from exact current
selection; the [reference contract](references-and-projection-keys.md#the-reference-model)
owns that distinction. Detached reproduction establishes captured custody; a live read checks
current authority, including between pages.

**Scoped lookup.** A point check acquires the selected parent's project, kind and current-cut
authority before obtaining its partition metadata and the required rule conclusions and
establishments. Its work is bounded by those selected facts and required premises, rather than
a universal number of probes. Pair and halo checks acquire their declared related partitions;
whole-collection checks acquire the membership and roots they actually observe. Retain an
immutable whole-group root only where an actual repeated collection consumer warrants its
preparation, write and retention lifecycle; otherwise account for the metadata scan needed
to derive it. An item-existence check resolves the item address inside one acquired partition
or consumes an applicable membership proof; a partition row proves no item's existence.

The same bound includes support and authority setup, not just returned bodies. Unrelated
partitions, frontier uses and protected leaves must not widen a point lookup. Genuine replay
still acquires its whole required closure. A cached answer reporting proof absence or
completeness must acquire current proof-relation membership on a hit, or that read shape is
excluded from answer reuse; current authority is checked independently on every call.

**At binding.** A consumer role declares the rules it requires of an input. Binding performs the
lookups and refuses a candidate that lacks one. Python treats a bound value as valid for those
rules.

**Fail closed.** A producer that cannot determine its checker determinant refuses; it does not
publish without a proof.

*Stopping short.* An attested rule's key is code-derived. It is narrower than today's (one
function's determining definitions, not a validator's whole closure and not the release), and it
is not a model fact. The refinement is to express the rule as a form.

<a id="sbx-01"></a>
## SBX-01 — Collections and partitions

**Vision.** The model can declare a collection; the compiler derives collections beside member
kinds; PostgreSQL has the partition table and admits partitions, recomputing each partition
digest, each group digest and the root from the bodies it receives; Python computes the same
values. An operation's completion carries a header and partitions. No kind uses it yet.

**Owns.** The collection annotation and its compile pass; the partition table and its place in
the physical model; admission of partitions inside the existing product admission program;
disclosure for partition rows, which follows the product's kind; the Python twin and the
completion wire shape; the field-group mechanism; the address type for partitioned items.

**Failure behaviour.** A partition whose recomputed digest differs from the header's root
contribution refuses the product. A collection declared partitioned that arrives as a list in the
body refuses. A duplicate partition key refuses.

**Evidence.** A product with three partitions is admitted and its root, digests and group digests
equal values written by hand in the test from the canonical bytes. Changing one item changes
exactly one partition digest, one or more of that partition's group digests, and the root. A
partition body one byte off its declared digest is refused. Python and PostgreSQL agree on every
digest for bodies containing non-ASCII text, a float, a decimal and an absent optional field.

**Verified · 2026-11-21.** Managed selection `a28f4c6e5c8d44328a780193e99d20ce` passed 36
compiler, generated-wire and PostgreSQL cases. It exercised the compiled header and item
schemas, digest parity with tagged non-ASCII/numeric/absent/null values, group isolation,
placement and reorder isolation, exact and shuffled replay, malformed population rollback,
and keyed parent-project and kind custody. The private keyed routine assumes its caller has
already acquired the selected parent. SBX-11 owns the public read shape. Item order and address
paths compile in SBX-01. Set-wise rule enforcement belongs to SBX-02.

The managed model preview `e5ab8d360fcf4954a55e55b5d4f4ff34` bound the N47 stage. Rollback-only
authoring `4867ee4d101a4c9c86cd2209e2c5cb40` used canonical N29 as its acquired authoring base and
replayed the registered predecessor under the authoring transaction. The operation recorded
established cleanup. Public producer declarations and final Revision A registration belong to
SBX-03 and SBX-20.

The acquired catalog in the candidate grants partition lookup only to the native publisher
owner. Post-authoring maintenance readback found canonical N29 and stage N47.

<a id="sbx-02"></a>
## SBX-02 — Rules and proofs

**Vision.** Rules are declared, compiled to graph nodes and fingerprints, and stored per release.
Admission evaluates the declared forms for each admitted partition and writes proof rows. One
establish routine does the same for existing content. Binding can require rules.

**Owns.** The rule declaration and form vocabulary; the generated evaluator for each form; both
tables; the establish routine; the attested-rule path, which re-keys what
`ddo_require_product_validations` binds today; the binding-side lookup; refusal in place of the
silent no-proof.

**Integration and preparation.** Settle the premise and establishment contracts above with
SBX-05/06 and the shared change scenarios before executable keys and proof selection diverge.
Inspect the existing partition admission's plain-schema check, tagged-schema check and group
extraction before adding evaluator walks. Share an interpreted row representation and existing
ordered aggregate work where their guarantees agree; preserve distinct checks where plain and
tagged schemas enforce different facts. This is operation-local reuse, not a second validation
framework. The [early Revision A chain](cutover-and-qualification.md#early-revision-a-integration)
tests these contracts in a real producer-to-reader route before whole-family conversion.

**Failure behaviour.** A partition that violates an admission rule refuses the product, naming
the rule, the partition key and the first violating item. An attested rule without a derivable
determinant refuses publication. Binding names the rule and partition it found unproved.

**Evidence.** For each form, a partition that satisfies it yields a proof row and one that
violates it is refused, with the expected violation written by hand. Editing a rule's parameter
changes that rule's fingerprint and no other; kind fingerprints and product ids are unchanged.
Editing a field one rule reads changes that rule's fingerprint and leaves a rule that does not
read it unchanged. After such an edit the establish routine evaluates only the affected rule, and
only on partitions without a row: the count of evaluations is asserted. A consumer role that
requires an unestablished rule is refused at binding.

The shared scenarios also cover movement and reorder without relative-content re-evaluation,
membership edits affecting completeness/absence/halo, and first-proof establishment changing
a previously negative read. Use two establishments for one conclusion: revocation of one does
not silently revoke an independently admissible one, while a required attestation with no
admissible establishment follows its failure policy. Check an existing partition missing a
requested item and add unrelated protected leaves and uses to expose accidental wider
acquisition. Count decoded bodies or examined rows only where that settles the intended bound.

**Implementation · 2026-11-21.** The captured release lowers rule records into `sem.data_rule`
and carries required rule IDs on native input roles. Native publication and retained
establishment share the evaluator. The retained command binds a particular read, fulfilled use,
derivation, product and rule before acquiring its premise. The conclusion and attested
establishment have separate tables. The latter records an exact derivation output and its
visibility stamp. Publication validates typed attestations against the admitted output and
current release, and binding checks admissible witnesses within the locked support scope.

The compiler covers native paired references and producer attestations over a whole product or
partition. The producer attestation builder derives the same premise from a fresh output
packet. It supports observed fields, explicit source/context pins and declared selected input
role paths. Native settlement reconstructs the selected path values from the producing role
bindings. SBX-04 still owns broader checker and consumer adoption, including any attestation
that needs an exact pair of input partitions. Existing validator families retain their receipt
path for the uncovered checks. SBX-03 exercises the first real converted producer chain.

**First-population fit · Inspected 2026-11-21.** Unique addresses, dense ordinals, ordering,
local spans, and exact item membership fit the declared forms. A required nonempty span can
also use a row predicate. Comparing actual source slices and native pieces, checking a token
against its referenced sentence's extent, and judging family coverage need explicit premises
from the converted shapes. SBX-03 checks those cases against the normalized declarations before
retiring the existing validators. [Sentence validator](../../../python/corpus-structure/src/corpus_structure/semantic/sentence_products.py#L311) ·
[Canonical membership](../../../python/corpus-structure/src/corpus_structure/semantic/canonical_sentences.py#L150) ·
[HanLP source inputs](../../../python/corpus-structure/src/corpus_structure/semantic/hanlp_products.py#L55)

**Targeted tests · 2026-11-21.** `uv run ci test` passed all 235 selected compiler, captured
projection, partition admission, required-rule binding, producer-attestation and legacy validity
cases (`778e77ca9bc749a8be49bb9beed946c5`). The native controls exercise exact item membership,
selective re-establishment, cut and role refusal, alternate witnesses, and Python/PostgreSQL
premise parity. A reused request must satisfy the current demand release's rule fingerprint.
The earlier selection exposed a stale legacy test setup missing required definition columns
(`773d810b42b2435680a1bd8dc5238ecb`). The passing selection verifies the repaired fixture.
`uv run ci check --only types`, `uv run ci check --only lint`, and `just model check` passed
(`c9fd6b5637584348a534823960106c3e`, `839160d519ad4b50b40eb0630a317a86`, and the generated-model
check respectively). The selected native fixtures exercise generated PostgreSQL logic with
controlled support-owner decisions. Whole-book and provider acceptance belong to SBX-22.
`uv run ci schema check --json` prepared the statistics pack. Its projection analysis reports
`unassessed` (`projection_analysis_unavailable`).

**Rollback candidate · 2026-11-21.** `uv run ci model change preview` verified the N47
predecessor (`b2f0548a7904464fb7222091d780ab6c`). `uv run ci model change candidate` passed
rollback-only authoring (`d1f4a4a8e60e478ea31e4c59b29829c9`) from the development N29 base.
The comparison accounts for the SBX-01 partition relation and the SBX-02 rule, conclusion and
establishment relations, native routines and privileges, and effects of the shared wire and
descriptor changes. `uv run ci model change inspect-candidate` confirmed the N47 predecessor
and candidate identity. Maintenance readback verified development N29 and stage N47 after
authoring. SBX-20 owns registration of the integrated Revision A, including subsequent changes.

<a id="sbx-03"></a>
## SBX-03 — The first populations

**Selected placement · 2026-11-22.** The [annotation-fork pilot decision](common-analytical-basis.md#pilot-implementation-and-evidence)
retains immutable annotation blocks and acquired contextual rows. Primary construction uses the
already admitted blocks. The real fork passed on its private current-source root. Those receipts
establish their captured source and selected use. Final integrated acceptance remains open.

**Installed successor · Proposed · 2026-11-22.** Finish the canonical, HanLP, declaration and
primary construction migrations on that route. Use the ordinary installed successor shared by
SBX-05/06/07 to exercise an unread edit, an actual producer attempt settling an equal downstream
projection, and a changed read field. Check local computation, eligible proof and exact current
attachment independently. Move or rename a block, then reconvert with independent provenance.
Repeated text and split or merged blocks must retain occurrence meaning when local bytes can
share computation. Compare exact addressed results after ordinary publication and selected
readback. [Shared successor scenarios](cutover-and-qualification.md#change-scenarios) ·
[Review I01](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I01)

**Installed occurrence readback · Tested · 2026-11-22.** One private current-source target
ran native PDF source acquisition and real annotation/canonical production over controlled
captures for stable-key movement, renumbered pointers, repeated text and split/merged blocks.
The fixture names each capture and exact original source pin. Readback checked historical
producing input, current addresses and literal relative and absolute spans. Equal local
annotation bodies retained their digest across changed placements. The provider selection
passed (`uv run ci test --native-host private --providers-only`,
`1eb8f7c7162843dd8a93538c787bba46`). The earlier concurrent-source attempt refused custody
(`4ef73b18ff2f4d79a9acccecf3ce56b1`). The eight sentence partition and declaration controls
passed on the stable retry (`b0b1393a3bf04a73a4418bf5cf5e06a6`).
This is installed current-source evidence for the selected occurrence cases. Governed
propagation and the registered-root rerun retain their own acceptance.

**Declaration ingress · Tested by selected identity · 2026-11-22.** The declaration
kernel acquires its canonical and HanLP rows through the same immutable partition
decoder and verifies their commitments. It resolves frozen keys through the shared
reference parser and compares the exact source frame bytes. Fifteen declaration
controls passed in the selected ordinary result `55bcda07dd68490fa772ac8f1b2dcad0`
(`uv run ci test`). Native move, split and reconversion coverage remains with the
ordinary canonical adoption journey.

The annotation-to-canonical chain supplies the runnable occurrence addresses and population
observations for [SBX-06's early propagation slice](cutover-and-qualification.md#early-revision-a-integration).
Keep the declared membership and closure observations usable for first matches, removals and
empty populations. The existing chain receipts establish their captured producer, binding and
readback scope. SBX-06 adds evidence for delivery from the originating native commit.

**Implementation checkpoint · 2026-11-21.** Source annotations publish one block-local rows
partition and a compact manifest for composition. Canonical projection consumes the authenticated
partition envelope, preserves block-local offsets, and emits role-relative references to the
annotation rows. HanLP emits token, constituent, semantic-role and alignment rows with canonical
sentence and token references. PostgreSQL restricts partition hydration to admitted whole-product
inputs and enforces packet capacity. Selected support export carries partition rows under the
parent body disclosure check, and detached verification checks partition content, field groups,
placement and parent commitments. Graph inspection displays one node per partition with its
metadata.

`uv run ci test` passed 232 compilation, detached, hydration, product admission, reference and rule
cases (`85e9b6137e904489b262743b66ceb23c`). The 12-case source and partition selection
(`2cefd312d45b4d16822bb520034c9f77`) passed, including the independently expected moved-block
coordinates and unchanged partition digest. All 20 HanLP checks passed, including CUDA inference
and typed partition output (`18ead9268aae45fcab445899402e7089`). Twelve scoped M1 checks passed
(`d7e24115befc4cc59b74be87d72828ce`).
After placing partition rows and the shared carrier in the private product model, all 47
source, canonical, HanLP and independent interpretation checks passed
(`902a1c284eac4c68822d1ed1652042af`).
The [early real chain](cutover-and-qualification.md#early-revision-a-integration) owns integration
acceptance.

Construction row readers and some prepared/generic consumers use the new annotation envelope.
M1 reads the annotation partitions and requires the row-span and exact-source-scope rules.
Declaration syntax reads canonical and HanLP partitions, verifies the HanLP producer's exact
canonical input, and emits typed references to HanLP rows. Definition replay consumes the admitted
syntax term evidence and no longer binds a separate HanLP role. Fifteen independent syntax and
definition cases passed (`ea29fc34aa564baba414dc14b0d2465b`), along with seven compiled-workflow
and CPU authority cases (`075365d01bed4d3ca79febc23861cdd8`).
The real HanLP-to-declaration syntax chain passed under native settlement
(`ce9ecaff99cb4d2c9ce00cfdd29fdc05`).
The later private PostgreSQL and CUDA selection verified annotation-to-canonical production,
the authorized native/Python projection digest comparison on actual admitted annotation
metadata, the unchanged repeat, and construction's exact partition references
(`uv run ci test --providers-only`, `a6e497e3d88a413895eb8b59461cfe1e`, passed).
Source validation decodes the annotation row view once and locates the native-piece range from
indexed source offsets. Maverick groups the selected block's token spans by sentence ordinal.
The retired packet producer, native block/token/sentence member kinds, synthetic token and sentence
IDs, and their revalidation reader have been removed. The annotation source witness now checks the
actual `block_layouts` path on the admitted header. The compact manifest is the only member kind.
Clause classification reads canonical sentence rows and publishes the focal and selected neighbor
addresses through the `canonical` role. The native annotation scorer takes an exact retained block
partition address and restores the selected block once across cases. The 21 controlled clause and
protected-reference cases passed (`e3f0c9e2f4ac457a9756939665de3866`). The full prepared downstream
profile compiled the clause target (`c0c23e138edf443a9077e66bde8bbce3`).
All 20 direct annotation, Maverick projection, native establishment and role-relative reference
cases passed (`52868352c55f4aa0ac1b768beeb69f6b`).
The real protected scorer passed on a fresh native target with CUDA annotations. It authenticated
the output-first partition pin, restored one selected block for multiple judgments, and refused a
substituted partition (`75226d5da21e475b87376d96b712d38d`).

The primary construction producer records annotation premises separately from its polymorphic graph
members. A declared link names the graph owner, use, position and its item under the producing
`sentences` role. Working native documents read token and dependency ordinals directly. Named
definition and characterization graph readers recover the actual producing input before following
these addresses. The 33 assessment graph controls passed, including hidden, missing and
substituted input cases (`9a85fcc81b4c4f9dbb4a5e36ed4ac37c`).
The real primary construction operation published the links on a fresh PostgreSQL target and
selected readback matched a published address to its admitted row
(`c4eb6a263e694c1cbf3103f22f0d1929`). The two named producer-to-reader roundtrips and the source
geometry control passed (`cbc3b1a85fee409f9ff34b925c4dd540`). The named definition capture
selected its actual dependencies without the learned provider configuration
(`43857f99949d45f8b98f016ee39cfe92`).
External extraction uses the admitted header as its CPU input basis and carries rows in a
separate authenticated packet envelope. The child checks packet digests and the recorded content
and placement commitments before constructing prompt-local labels. Its annotation roles now
require the ordinal, span, order and source-scope proofs. The focused controlled CPU and rich
extraction selections passed the original authority split (`4d9dcb0626254a6d9abd2ae7d352e4fa`).
The 19 proof-backed CPU, external and MCP checks passed (`8577445596f3403eb4f83311a1d232a0`).
Rich source and context references remain in SBX-05.
The fresh PostgreSQL T1 journey populated the actual external task queue and passed claim and
packet readback. Its controlled response then failed authored-wire validation on Python tuples
(`0e31723c3fe9466d928033c1903d4d2b`). The next run checked sentence text against its exact
native addresses and committed the external submission. Placement then refused duplicate local
identifiers generated by the fixture (`5e11e12b8cf94fe4b5f81235c94c443d`). The corrected fixture
assigns claim IDs their own prefix. The next run published the rich admission and reached the
production query. Retained rich readback lacked the local entity source context already checked
by the native producer (`2ab6fb4e448b4dccb9863d4f116a2184`). The typed selected read now supplies
the exact native admission and verifies its body and contextual identity before using the source
context established at publication. The 29 offline controls passed, including rejection of
substituted content and context (`14a13641b7ad4824be77c2e40ec5e8e8`). Native T1 then served
its published query rows and exact source derivation support. The fixture expected a statement
reference on entity attributes, whose evidence is carried directly
(`26a687055c11446a8e5f256e616efada`). It now checks each occurrence's evidence and requires the
authored statement on claim occurrences.
The final native T1 control passed with CUDA annotations, controlled external authorship, native
publication, and production query readback of the construction formula and qualification
(`90973e6f093a4e8ea75fb4eb4a8ef3ed`). This is one representative external statistics journey.
The focused renumbered duplicate case preserves each current address and placement even with
equal row digests (`d140ca92e7a94a0780f9f022b344ee60`). The split and merged population control
lowers both acquisitions to their independently expected current row addresses and absolute
geometry (`318ce1adf27f4ce98132af63d8e494ee`). An exact cross-source correspondence used by a
consumer still needs independent evidence when reusable computation is adopted in SBX-06 and SBX-07.
Primary construction's admitted ingress uses the selected partition envelope and requires dense
ordinals, row spans, source order and exact source scope. Synchronous execution reuses the checked
inputs. Seven prepared-port controls passed, including omission of the selected packets and
agreement of controlled synchronous and CPU output (`304947549821441cb0bf020139410c60`). Whole
annotation validation still covers construction's native pieces, token-to-sentence membership
and sentence coverage. Declare those premises before retiring the check from admitted construction,
and migrate predicate and learned ingress. Standalone input continues to have its own validation
boundary.
The same native provider selection as the T1 run passed the actual construction publication and
its selected citation to an admitted annotation row (`2ab6fb4e448b4dccb9863d4f116a2184`).

**Admitted annotation consumers · 2026-11-21.** The admitted construction, predicate and
learned paths use selected binding and declared annotation layout, membership and coverage
proofs according to what they read. Canonical projection now binds membership and coverage.
Producer and standalone validation retain their own boundaries. The combined projection,
annotation and reference selection passed 36 cases (`670d348f1f4e4a2489a47780987193f1`).
The integrated CUDA annotation-to-canonical chain passed on owned PostgreSQL
(`uv run ci test --providers-only`, `ae8d693ab805499d8f6ae39848f1708e`), including exact
partition references and an unchanged demand repeat with zero new receipts.
The owned native CUDA construction test stopped before proof publication at the exact sentence
runtime/parser custody check (`55c2cfb4141c4534abbbf069e87550f3`). A stable-source retry
with artifact-specific refusal details passed actual CUDA construction publication and exact
row readback (`uv run ci test --providers-only --native-host private`,
`5a5f8110626c4902837727f780b750ca`). The initial mismatch did not recur.

HanLP now declares partition ordinals and publishes selected-source and canonical
attestations for token order, constituent and role spans, and native coverage. Declaration
syntax requires them. Sixteen focused controls, including CUDA HanLP, passed
(`uv run ci test`, `7427680d824e4032ae0ec2548f7579cb`). The integrated HanLP-to-declaration
journey passed on private PostgreSQL at `0d6055488` (`uv run ci test --providers-only`,
`0647a867060f46dca5fdc64a2f88c6d4`). The previous invocation reached an upstream sentence
execution-custody refusal (`394183cc420b46daaeb0cb6da3a82edb`). An additional hard link
reproduced a file-stamp change with identical model bytes. The passing retry used an
isolated copy of the same spaCy model files and preserved launch-time custody checks.
The integrated canonical and HanLP cases passed together again with the exact source-proof
correction (`uv run ci test --providers-only`, `cee750ab2b274d66bed4bf20f3ee3cff`).

The refreshed native T1 journey passed on the source with the separate computation basis.
It exercised CUDA annotation acquisition, the native external task handoff, controlled
authorship, publication and rich query readback
(`uv run ci test --providers-only`, `676b3e680be74fd5a2e0daaeb13cdcad`).

**Vision.** Sentence annotation, canonical projection and HanLP publish partitions. Their
consumers read partitions through one row view and name tokens and sentences by address.

**What changes for each product.** *Annotations:* blocks become partitions; the native packets
and their recompute-and-compare go, since the population was already in `blocks`. *Canonical:*
token and sentence packets become partitions holding the projected field groups; the manifest
stays a bound member. *HanLP:* tokens, constituents and semantic-role groups become partitions
keyed by the block of their sentence, each unit addressed by sentence address, kind and ordinal
or path.

**Rules for these populations.** Declared forms: block id unique; item spans within the block;
sentence spans within the block; a token within its sentence; token ordinals dense per block;
sentences ordered by start; HanLP units refer to an existing canonical sentence; role spans
within their unit. Attested: block text equals the source slice and native pieces equal selected
pieces; HanLP tokens equal the canonical sentence's non-whitespace tokens, which needs the source
text. Product-scope: coverage and outcome.

**Consumer scope.** The modules listed as group B and the sentence consumers in the
[reference migration scope](references-and-projection-keys.md#migration-scope): the
constructions library's matching, naming, navigation, math-scope and retained-rules modules;
construction, predicate, clause, declaration and definition products; learned primary and
external extraction; the characterization assessment evaluator. Each reads the row view and
stops re-running `validate_source_annotations`.

**Removes.** `source_annotation_packets` and the members comparison; the native, canonical and
HanLP packet classes; `source_annotation_member_values` as a repeated derivation, replaced by one
memoised row view over partitions; the hashed token id and its translation back to an ordinal;
member rows for these kinds in the support export.

**Decided here.** What graph inspection shows for a partitioned kind (a node per partition is the
proposal); how the detached verifier treats partitions, with the
[read companion](owner-resolved-reads.md#sbx-12).

Acquisition/lowering also owns exact occurrence identification and any correspondence needed
after conversion. Pair a moved block with a retained key and a reconversion with renumbered
pointers; repeated-text and split/merge controls must leave ambiguous correspondence unknown.
This does not prevent equal complete projections from sharing computation or content proofs.
The early chain exercises current-occurrence readback before the remaining group B migration.

**Evidence.** For a fixture document, the tokens, sentences and HanLP units read back through the
row view equal the values the current code produces, compared field by field with absolute
offsets recomputed from block starts. Inserting a paragraph before a block changes that block's
extent in the header and leaves its partition digest unchanged. Each of the six consumer sites
that re-ran the sentence validator now binds with required proofs and contains no validator call.
A constructions result on the fixture equals today's after mapping token ids to addresses.

<a id="sbx-04"></a>
## SBX-04 — One stance on validity

**Proof boundary · Proposed · 2026-11-22.** Establish construction and contextual navigation
against the exact selected producing role, member, occurrence and logical slot. Name the output
navigation and coverage facts and the annotation layout, address and token facts actually read.
The intrinsic navigation proof over construction members does not by itself establish all those
cross-input premises. Keep ingress and atomic native publication as the admission boundaries.
[Review I02](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I02)

**Remaining execution · Proposed · 2026-11-22.** Use the declared dependency-member rules and
release-owned attachment-policy witness. Construction and contextual evaluation publish those
attestations and address their external premises and packed choices through producing roles.
Retire the two parent dependency rosters at the binding and acquisition boundary before
qualifying the registered root. Use the existing
establishment reader over declared role header paths and the observed output fields. Annotation
headers carry distinct body and placement commitments. Bind each commitment only where the rule
observes its facts. A whole-collection header is the initial conservative premise. Narrow to a
role, collection or field-group premise only if a concrete reuse case needs it and producer and
current consumer can derive the same fact. Preserve contextual annotation support when the
interpretation independently reads it. A historical proof requires an eligible current
establishment or admissible substitute and exact current input access before use.
[Header commitments](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partitions.py#L152) ·
[Establishment reader](../../../python/corpus-structure/src/corpus_structure/semantic/rule_establishment_native.py#L74)

Reuse the admitted primary or retained characterization block views through SBX-08. Sparse
address consumers acquire only the requested authorized partitions. Claims over a closed or
complete domain still inspect their full declared scope. Remove repeated acquired checks only
when the proof covers the omitted facts and each migrated consumer binds that proof. Native
publication and projected adoption already validate declared reference addresses. SBX-05 owns
reuse or grouping of that exact authorized partition lookup. Keep the existing native grouped
uniqueness, anti-join, rank, ordering and extent checks in their transaction owner. On a dense
already typed input, Arrow or DuckDB can supply an independent relational comparison if it
resolves an uncertain result. Building another production validator would introduce extraction
and duplicate semantic ownership on this path.
[Native rule owner](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_rule_native.py#L563) ·
[Reference work](references-and-projection-keys.md#sbx-05) ·
[Carrier work](validated-values-and-handoff.md#sbx-08)

Use the installed successor for move and reconversion acceptance. Include equal content at
changed placement, duplicate occurrences, malformed ordinals and extents, token membership and
order, partial versus complete coverage, missing versus withheld addresses, and an ineligible or
revoked premise. Recheck selective establishment, fingerprint isolation, alternative admissible
establishments and body-only binding on the final root. Publication and adoption must remain
atomic when any required reference or proof refuses. Retain independent expected addresses and
coverage facts in the tests. [Shared scenarios](cutover-and-qualification.md#change-scenarios)

**Cross-input construction proof · Tested by selected identity · 2026-11-22.** The construction
producer emits `text.constructions/selected-annotation-support` against observed navigation
and the exact selected annotation header. The compact `rows` header supplies the body and
placement commitments. Its terminal path works with the existing compiler, which rejects
dotted traversal through the logical multivalued collection. The binding requires this proof on contextual construction inputs.
The normalized checker compares the actual block and token together and verifies the released
layout digest. A token ordinal valid in a different block is refused. The three focused
prepared, navigation and actual named-construction identities passed (`4719e52fcc664084ac7ef000bc7e81f7`).
Native establishment parity passed (`93d2544f51cd4b9981c4f7d0d75e22d4`).
The actual construction provider passed private selected token readback
(`19646ada88614bffb3e5428b4620cbf3`). The retained carrier now preserves its admitted decoded
annotation blocks across rebinding. The admitted contextual reader consumes the producer
attestation and keeps the exact `supporting` input requirement. Standalone construction still
checks the addressed rows and layout at its admission boundary. The focused construction,
contextual and annotation selection passed all 45 cases (`55e2ea9c1ce44b90b668e0124ca08d01`),
including exact retained acquisition without repeating the annotation proof and refusal when
the retained dependency is missing. The final registered-root qualification exercises the
same proof through original ledger acquisition and the current selected support.

**Shared observed premises · Tested by selected identity · 2026-11-22.** Native settlement
calculates one observed premise per admitted product, partition and matching premise specification.
Claims still match each rule's exact fingerprint, output and partition. The private regression
verified that two rules can share a premise and each requires its own attestation before binding
(`uv run ci test --native-host private`, `bdc253d62cfb415eaeb9be40b7dd25c4`). A larger
candidate-conditioned provider run hit the completion statement limit during native premise
construction before this change (`cd503bd25d994d528fecafc4177c9b03`). The provider workload
has separate qualification.

**Construction rule uptake · Tested by selected identity · 2026-11-22.** Contextual
interpretation requires the construction selected-primary-members establishment. Predicate and
scoped-relation construction inputs require the declared geometry, topology and coverage their
consumers read. The retained construction check no longer replays the established selected
dependency membership. The focused declaration selection passed (`uv run ci test`,
`e62817278eb546bf9cc36f0c4de8db83`). The independent navigation proof attempt failed to close
its captured determinant (`6ebce29ae5ef47f3bc2595daf0528106`). The construction producer now
separately attests its intrinsic navigation fields from the admitted members. Contextual binding
requires this proof, while exact token and annotation-partition custody still runs at ingress.
All six affected compilation and construction/contextual controls passed on the revised checker
(`uv run ci test`, `de8fa4fa92bd428e81eb8e6961cba369`). The cross-input navigation proof and full
role-addressed dependency conversion remain open.

Supply the applicable establishment and support facts at the native binding boundary for
[SBX-06 readiness delivery](references-and-projection-keys.md#readiness-delivery). An additional
admissible establishment or a support revocation can change readiness with unchanged proof
premises and unchanged computational input. SBX-06 owns delivery to affected waiters.

**Implementation checkpoint · 2026-11-21.** Producer attestations can name selected input role
paths. Native settlement reconstructs those paths from the producing bindings, preserving their
order and multiplicity, and binding checks an applicable establishment at the acquired read.
Canonical projection requires annotation row spans and the exact source/scope attestation.
Formal coverage-family uniqueness and ordered lexicon bounds have named intrinsic rules.
`uv run ci test` passed 42 rule and admission cases (`d1cf0aec9979403e92838a7364d43b2f`).
Formal production also attests literal source geometry and exact packed choice members. The 39-case
formal and native rule selection checks both retained rule claims (`49d22639b4eb4ea7ad5cd3812e7aaeae`).
Formal completion also emits separate checks for examined source scope and coverage, lexical links,
and positioned symbols and their containment. The shared 113-case selection passed on stable source,
including the prepared formal CPU route and native rule cases
(`481f8700fa034696b5b6ef45229dc986`).
Annotation and canonical admissions declare separate dense ordinal groups for sentence and token
rows. Annotation admission also checks source ordering. The 32-case native program, rule and
annotation selection passed the grouped acceptance and refusal controls
(`19796fc2da3e47ee8f14df1935b978bf`).
Construction and contextual completions emit a literal occurrence proof tied to the original
source coordinate, selectors and text. Contextual evaluation requires it on the construction
input. Prepared completions and changed-source refusal passed (`50c88d3a39334a0390c18a85f980a58d`).
Construction and contextual evaluation require formal lexical and coverage proofs alongside
source and symbol geometry. Predicate and scoped-relation operations require the latter group.
A native control established that a body-only consumer can bind independently of the
source-dependent proof (`21d285c2d8214b5a977b029eefc0eae4`). The consumer role assertions passed
with the full acquired primary declarations and numerical policy (`1bbf7aa1e5ac40f2aa8fa64e4344f72c`).
Formal completion also attests actual native occurrence pointer, page, projection and positioned
selector membership. Primary construction requires that proof. The formal port and two named
roundtrips passed with that rule (`4f02fe32b1e94034aac3e1c041f77cfa`).
Formal completion declares independent attestations for the exact ordered family roster and local
member addresses. The latter checks packet/body identity, duplicate packet IDs, and collisions with
packed choice members. Primary construction declares both requirements. Three controls passed,
including prepared completion emission and independently authored invalid inputs
(`6ec9873a380e4d27b92bc3b922163032`). The compiled consumer confirmed both requirements
(`07cba3252a7348aaa3a1bcc0f92921f0`).
Construction and contextual completion now attest body coverage independently of their source
selectors. The checker binds family uniqueness, the coverage of analytical members, the
reported availability and examined status, and empty and complete claims. Contextual
evaluation requires the resulting proof on construction inputs. All 25 focused identities
passed across the initial selection and the exact retry with its domain configuration restored
(`uv run ci test`, `c118b876f3bc4e46b9e891cac5168d82` and
`bea3f24ffba445cd8b64a3ba58d3f601`).
Lexical and contextual mathematical analysis, mathematical occurrence extraction, and the
learned and contextual native producers now bind the formal conclusions they use. Seventeen
math, acquired downstream, learned and standalone structural cases passed
(`uv run ci test`, `7cf958a121414ee48ba9908fb4b4ed9b`). The first standalone structural
attempt failed because the model imported the formal kind without the attested rule owner
(`bb4ecad88ae545febe3c3771097be183`). Standalone preparation now acquires that producer's
captured rule declarations. The optional formal role still uses only its explicit frozen
source set. Five private native and preparation controls passed
(`uv run ci test`, `91bf7cab9fd046f18f9ea0bc386ebdf1`). They covered the standalone
model and comparison without formal inputs. The integrated comparison with a selected formal
source set reached native publication after the selected-output proof correction. Its
`threshold_unit` dimension returned an empty left group (`uv run ci test`,
`452918a0eccd49ef951b7ea1103ee2a9`, failed). The formal producer found the threshold. The parser
attached the conditional marker to a nominal subordinate that lacked a separately recognized
predicate. Primary construction now uses the exact selected formal threshold inside the complete
marked clause together with the parser's direct nominal attachment. The real private provider
journey read both 25,000 and 50,000 through formal, construction, predicate and structural
publication. The scientific outcome remained unknown (`uv run ci test`,
`5e006ef3c6e0412db7e223434d2667f4`, passed).

Removed the coordinate, role, endpoint, coverage and choice side tables from the target compiler
and generated wire. The generated successor passed rollback-only candidate authoring against N47
(`27c37c0e9aaa403ebbb53817d6cee671`). Native binding uses derivation output position and
multiplicity. Native product admission still checks exact nominal member rows. Formal, construction and contextual graph topology and canonical occurrence addresses now
have separate checker declarations. The remaining exact cross-product checks and consumer
declarations are open. Resolve member-level output
retirement against the actual output declarations and native consumers before deleting that path.

The omnibus `ProductValidation` field and its producer, settlement, projection and generated
wire branches have been deleted. Existing independent producer and retained-value validation
continues for premises that have not yet moved to a scoped checker. Formal numeric normalization
now has a closed attested rule acquired by structural binding. The scoped receipt and numeric
controls passed (`uv run ci test`, `3c8ed29eb3834b1a82450d0591a469ba` and
`76a3d670f83c427c9a0d72d67b96af0b`). Construction and contextual completion also declare
complete or empty family coverage over actual selected source ranges, ancestry and pieces.
Contextual binding requires the construction establishment. Independent graph and cross-input
authority still needs its corresponding scope before dependent validation can be removed.

**Checker capture · Inspected 2026-11-21.** The attempted formal split hit unresolved source
and callable determinants in the graph, normalization and occurrence checkers
(`uv run ci test`, `5cc6e93778fa4a5dbedd7df433ca8243`,
`2f3eb050d9974a7c8835c3775c415fb3` and `18a251456152429aa96e7c7cb1419e14`, failed).
The attempted declarations were withdrawn. The closed numeric rule above resolved the
normalization slice. The later topology and occurrence checks closed their captured code and
codec premises. The native occurrence checker uses the acquired finite standard JSON codec and
exact source addresses. A named CUDA construction publication resolved its exact annotation row
(`uv run ci test --native-host private --providers-only`, `4ef3459bb032443da522db1e8f0c28b9`,
passed). The cross-input and released attachment-policy checks now have separate producer
declarations. Their final-root verification follows the roster retirement above.

**Vision.** Every existing semantic validator becomes one or more rules. Consumers accept proofs
and no hand-off differs in stance.

- The three `ProductValidation` contracts become product-scope attested rules keyed on
  fingerprint and body digest, without the release.
- The formal and construction validators are split along the groups already visible in them:
  body-internal, source-reading, cross-product. Body-internal groups that fit a form move to
  admission; the others stay attested, each with its own fingerprint, so a consumer requires
  only the groups it relies on.
- For each migrated rule, state whether its conclusion follows from immutable native content
  or needs a currently admissible attested establishment. Migrate that provenance with the
  rule; neither release independence nor a content-key match removes required authority.
- Consumers that check identity only (predicate, scoped relations, view composition, the math
  extract) declare required rules; products with no validator (math, predicate and scoped
  reports) declare that explicitly as an empty rule set, so the absence is a model fact.
- The five projection families, their admission checks and their two readers are retired, with
  member-level outputs if SBX-00's baseline confirms no role uses them.

**Evidence.** A consumer that requires only a formal product's body-internal rules binds when the
source-reading proof is absent and refuses when a body-internal proof is absent. A release that
changes a model fact no rule reads leaves every proof matching, observed as zero evaluations by
the establish routine. The receipt format and its reader are gone and no completion carries one.
