# Populations, rules and proofs

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md),
which owns package state, decisions and the disposition table. **Created:** 2026-11-21.

This companion owns the central contracts of the series: how a homogeneous population is stored
and identified, how rules are declared and checked, and what a proof is. It owns packages
SBX-01 to SBX-04. Source facts are **Inspected** at `7a415d18d`; design statements are
**Proposed**. `cs/` is `python/corpus-structure/src/corpus_structure/`.

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
partition_digest, item_count, group_digests, body)`, primary key on the first three, with an
index for ordinal order. `body` is the tagged value of one partition. `group_digests` is a
mapping from field-group name to the digest of that group's values in item order.

**Identity.** `partition_digest = ddo_identity('partition', body)`, with its Python twin through
`canonical_identity`. The existing identity function already takes its domain as a parameter, so
no new hashing protocol is introduced. In the product header the collection property becomes a
record of root, partition count and item count; the root is the identity of the sorted
`(partition_key, partition_digest)` pairs. Body digest and product id keep their formulas over
that header. A field group's root is computed the same way over `(partition_key, group digest)`
pairs when a projection needs it ([read projections](references-and-projection-keys.md#read-projections)).

**Field groups.** A field group is a named set of an item's fields that is read together: for
tokens, for example, geometry (`start`, `end`, `space`), sentence membership, lexical labels
(`lemma`, `pos`, `tag`, `morphology`), dependency (`head`, `dependency`) and layout
(`piece_indices`). Groups are declared in the model because they are the granularity at which a
consumer's key can ignore a change. Too many groups cost digests; too few forfeit reuse. SBX-01
fixes the first populations' groups from the read sets the consumers actually have.

**Block-relative addresses.** Offsets stored in a partition are relative to the block's start;
the block's own extent is in the partition's header fields. A token's address is
`(collection, block_id, start, end)` with relative offsets. The address is what today's hashed
id is computed from, left unhashed and made stable under edits elsewhere in the source. An
absolute offset is a derived value: block start plus relative offset.

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

`kb.data_validity(rule_fingerprint, premise, established_by, derivation_id)`, primary key
`(rule_fingerprint, premise)`, written only by security-definer programs. `sem.data_rule(release_id,
rule_id, fingerprint, …)` holds each release's current fingerprints.

**Premise.** For a partition rule, the partition digest. For a pair or cross-product rule, the
identity of the digests in declared order. For a product-scope rule, the body digest. A roll-up
row with the collection root as premise is written when every partition of the collection has
its proof.

**No invalidation step.** A proof is an immutable fact about content. Whether it is current is a
join: a release whose rule reads an unchanged closure computes the same fingerprint, and every
existing proof still matches; a changed closure gives a new fingerprint under which no proof
exists. Re-establishing evaluates only the missing rule and partition pairs, set-wise, with the
same routine admission calls. Neither the release nor the product is in the key.

**The point check.** "Is rule R established for partition X of product P under release L" is
three primary-key probes: the fingerprint from `sem.data_rule`, the digest from
`kb.data_product_partition`, the row in `kb.data_validity`. For a whole collection the root is
read from the header.

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

<a id="sbx-02"></a>
## SBX-02 — Rules and proofs

**Vision.** Rules are declared, compiled to graph nodes and fingerprints, and stored per release.
Admission evaluates the declared forms for each admitted partition and writes proof rows. One
establish routine does the same for existing content. Binding can require rules.

**Owns.** The rule declaration and form vocabulary; the generated evaluator for each form; both
tables; the establish routine; the attested-rule path, which re-keys what
`ddo_require_product_validations` binds today; the binding-side lookup; refusal in place of the
silent no-proof.

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

<a id="sbx-03"></a>
## SBX-03 — The first populations

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

**Consumer scope (complete).** The modules listed as group B and the sentence consumers in the
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

**Evidence.** For a fixture document, the tokens, sentences and HanLP units read back through the
row view equal the values the current code produces, compared field by field with absolute
offsets recomputed from block starts. Inserting a paragraph before a block changes that block's
extent in the header and leaves its partition digest unchanged. Each of the six consumer sites
that re-ran the sentence validator now binds with required proofs and contains no validator call.
A constructions result on the fixture equals today's after mapping token ids to addresses.

<a id="sbx-04"></a>
## SBX-04 — One stance on validity

**Vision.** Every existing semantic validator becomes one or more rules. Consumers accept proofs
and no hand-off differs in stance.

- The three `ProductValidation` contracts become product-scope attested rules keyed on
  fingerprint and body digest, without the release.
- The formal and construction validators are split along the groups already visible in them:
  body-internal, source-reading, cross-product. Body-internal groups that fit a form move to
  admission; the others stay attested, each with its own fingerprint, so a consumer requires
  only the groups it relies on.
- Consumers that check identity only (predicate, scoped relations, view composition, the math
  extract) declare required rules; products with no validator (math, predicate and scoped
  reports) declare that explicitly as an empty rule set, so the absence is a model fact.
- The five projection families, their admission checks and their two readers are retired, with
  member-level outputs if SBX-00's baseline confirms no role uses them.

**Evidence.** A consumer that requires only a formal product's body-internal rules binds when the
source-reading proof is absent and refuses when a body-internal proof is absent. A release that
changes a model fact no rule reads leaves every proof matching, observed as zero evaluations by
the establish routine. The receipt format and its reader are gone and no completion carries one.
