# References and projection keys

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how one product refers to another and how a consumer is keyed on what it
reads. It owns SBX-05 to SBX-07. It consumes the collection, partition, field-group and proof
contracts of [Populations, rules and proofs](populations-rules-and-proofs.md). Source facts are
**Inspected** at `7a415d18d`; design statements are **Proposed**.

## Baseline

**References.**
- 75 model slots are typed as product or member references. One class,
  `DdoSemanticMemberReference`, serves every target; no slot declares what it points at. One
  slot, `external_premises`, points at tokens in one family and at graph members elsewhere.
- About 53 Python entry points resolve references: about 20 decode a whole product into a
  dictionary, 13 are keyed lookups in the SQLite index (three are copies of one function), the
  rest check equality or membership in the bound inputs. About 27 database-side sites touch
  references; no native program follows local body ids, HanLP's references to canonical items,
  or most declared references in reports.
- Fields with no check anywhere include a canonical token's sentence reference, HanLP child
  constituents and a report's primary member reference.
- The support model has thirteen edge kinds; none means "this body cites that member". A citing
  product is affected by revocation of a cited one only if the cited product was also a bound
  input. Whether every cited product is a bound input is an SBX-00 entry check.

**Request identity.**
- `SemanticRequestKey` (`cs/semantic/data_operation_identity.py`) hashes recipe, subject, context,
  inputs and parameters. An input contributes its product id, or, when a member is bound, the
  member's body identity computed by PostgreSQL at bind time. Member-granular keys therefore
  already exist.
- Product ids are content-addressed, so an unchanged body already gives an unchanged id from any
  derivation. The canonical projection exists to use that: a narrower product whose id does not
  move when unread labels change.
- A use keeps its own selection; a derivation keeps its recorded inputs. For operations whose
  provenance is value substitution, validity already accepts the use's own selected support as
  an alternative to the derivation's recorded support
  (`cs/semantic/support_edges.py`, `request_attachment_native.py`).
- Recipe and definition fingerprints include the whole rooted closure of each input kind, so
  adding any property to an input kind re-keys every consumer.

**What stands in the way of narrower keys.** Output bodies embed upstream product ids (dependency
lists, source pins, member references, local ids hashed over a pin). Offsets are absolute.
Several kernels validate the whole input or hand it whole to a library. Some bodies carry
batch-level digests (GLiNER), and the contextual encoder's output depends on its cohort.

## The reference model

**One carrier.** A reference is a discriminated value: a whole product; an identified or bound
member, by member id; or an item of a partitioned collection, by collection, partition key and
item key. One Python type, one generated wire type, one LinkML class family. The context copy
that declared references carry today is dropped from the reference and read from the target.

**Declared targets.** Every reference slot declares its target: the input role it refers into,
and the kind or collection within it. A polymorphic slot is split or carries a discriminator.
The compiler then knows every reference, and closure rules are generated from slots.

**Role-relative.** A reference names an input role of the producing operation and an address
within that input: "the token at this address in my `annotations` input". It does not embed the
upstream product id. The derivation's recorded inputs bind the role to a product. Three
consequences: a body is identical whenever the inputs it read are identical in the fields it
read; every citation is a bound input by construction, so existing episode-level support covers
revocation of a cited product with no new edge kind; and a body can be followed only together
with its derivation's inputs, which every reader of references must be given.

*Exceptions, stated.* A view that is an index of products (document composition) refers to
products by id because that is its content. Rich selection embeds support references and stays a
variant of the carrier. Source-set proofs and pins on bound inputs keep their existing native
checks.

**One resolver.** Python resolves any reference through one function over validated carriers:
the role gives the input; an item reference gives a partition, decoded once and memoised by
digest, then an index by the declared key. PostgreSQL resolves existence by key: a member row, or
a partition row.

**Closure.** Checked once, by whoever holds both ends. A reference within a partition, or from
one product's partition to another's, is a `refers_to` rule with the pair of digests as premise.
A reference from a graph member into a population is a product-scope rule on the citing body
with the cited partition's digest in the premise. Closures that need the source text, or
agreement of source and selectors between two products, are attested.

## Read projections

**Declaration.** A consumer role declares its read projection of an input: the collections and
field groups it reads, and its scope: `partition` (the output for a block depends on that block
alone), `halo` (that block and a declared neighbourhood: adjacent sentences, the section, named
ancestors) or `whole`. The projection is a set of edges in the model graph from the role to
property nodes, so its specification has an identity by the same rooted-closure mechanism as a
kind.

**Enforced by construction.** The envelope hands a kernel only its declared projection: the
field groups it named, for the partitions in scope. A kernel cannot read what it is not keyed
on. This is the soundness mechanism. Validators that today read a whole input run on the
projection, or their rules have moved to admission.

**Derived and checked by introspection.** The existing code-identity analysis records code
reachability, not data access. A read-set pass is added beside it: constant-key subscripts and
`get`, attribute access on typed carriers, destructuring in loops, return paths. On two
dictionary-reshaping kernels a prototype resolved every read after about eight patterns; kernels
that hand a value to spaCy, HanLP or GLiNER are not resolvable and are declared. The pass
proposes projections and reports a declared group that is never read; it is never what makes
reuse sound.

**Projection digest.** For one input, the identity of the projection specification together with
the roots of the declared field groups over the partitions in scope. For `whole` scope over all
field groups it equals today's content address.

**Request identity.** An input contributes its projection digest in place of its product id. A
change to a field group or partition outside the projection leaves the key unchanged; the
existing request row is found and its derivation attached. The use records the product it
selected; the derivation records the product it was computed from. Validity uses the use's own
selected support, which is the existing value-substitution alternative, extended from equal
bodies to equal projections.

**Model changes.** A role's contribution to recipe and definition fingerprints becomes the
projection specification's identity, not the whole kind closure. Adding a property no consumer
reads then re-keys no consumer.

*Stopping short.* Kernels with `whole` scope key on every partition they read, though still only
on the field groups they name. Bodies that record a batch digest, or whose numbers depend on the
cohort, do not reproduce per block; those producers are declared whole until their output is
made batch-independent.

<a id="sbx-05"></a>
## SBX-05 — One reference model

**Vision.** Every reference in the model declares its target; bodies refer by role; one carrier
and one resolver serve all families; closure is a declared rule or an attested one.

**Consumer scope (complete).** The model files that declare reference slots; the Python reference
types (`data_product_reference.py`, `declared_structural_references.py`, the structural,
rich, source-set and interpretation reference classes) and the generated wire types; every
producer and resolver listed under [migration scope](#migration-scope); the output-witness
declarations that compare reference fields with bound inputs; the readers that follow references
without a derivation (the assessment evaluator, structural serving, detached verification), which
are handed the derivation's inputs.

**Removes.** The shared untyped reference classes; the per-family resolvers and dictionaries; the
duplicated selected-body lookups; hashed local ids computed over an upstream pin; the context
copy inside references; producer-side dangling checks that a generated rule replaces.

**Failure behaviour.** A reference whose role is not an input of the operation is refused at
compile time. A reference that does not resolve refuses the product at admission, naming the
slot and address, where a declared rule covers it; an attested closure refuses at production.

**Evidence.** For each of the three carrier variants, a body with a dangling reference is refused
and one with a resolving reference is admitted, the expectation written by hand. The same source
processed through two different upstream product ids with equal read content yields byte-equal
construction and HanLP bodies. Revoking an upstream product invalidates a citing derivation
through its recorded inputs, for a citation that today would not be seen. Resolving one token
reference decodes one partition: asserted by counting partition decodes.

<a id="sbx-06"></a>
## SBX-06 — Projection-keyed request identity

**Vision.** Consumer roles declare projections; kernels receive them; request identity uses
projection digests; PostgreSQL computes them at binding from stored group digests and Python
computes the same.

**Owns.** The projection declaration and its graph edges; the read-set analysis and its report;
the envelope change that hands projections to kernels on all three execution routes; the request
key formula in both languages; attachment of an existing derivation whose recorded input differs
from the use's selection; the authority basis of authority ports, which becomes the projection;
the fingerprint change for recipes and definitions.

**Order within the package.** Declarations and enforcement first, with keys unchanged, so that a
kernel reading outside its projection fails in tests before any reuse depends on it. Keys change
last.

**Failure behaviour.** A kernel that reads a field group outside its projection fails with the
group named, because the value is absent. A role with no declared projection defaults to whole
scope over all groups, which is today's behaviour.

**Evidence.** Changing only lexical labels of an upstream sentence product leaves the request key
of a consumer that reads geometry unchanged, and a second demand attaches the existing
derivation with no new attempt; changing a token span changes the key. The expectation in each
case is stated from the declaration, not computed by the code under test. A consumer declared to
read geometry that touches a label fails. Revoking the product a reused derivation was computed
from, while the use's selected product stands, leaves the use valid; revoking the selected
product invalidates it. Adding an unread property to an input kind leaves consumer recipe
fingerprints unchanged.

<a id="sbx-07"></a>
## SBX-07 — Partition memo for block-local kernels

**Vision.** For a kernel whose projection scope is `partition` or `halo`, the envelope computes a
key per output partition from the recipe, the parameters and the projection digests of that
partition's inputs, looks up a retained result, and runs the kernel only for partitions without
one. The product-level derivation, claim and receipt are unchanged; work is proportional to what
changed.

**Conditions, checked at entry.** The kernel's output for a partition is a function of its
projection, as the locality census found for sentence annotation, canonical projection, HanLP,
clause classification and the learned primaries except GLiNER; batch composition does not reach
the body; the operation's declared replicate policy is the retained single result, which makes
"the first retained result stands" its existing meaning. Whole-source kernels (scoped relations,
contextual retrieval, composition, rich consolidation) are out.

**Open design, settled in the package.** Where retained partition results live (the proposal is
the partition table itself, addressed by a result key beside the digest); how a reused
partition's proof rows apply (they already match by premise digest); how revocation reaches a
reused partition (through the derivation that first produced it, which needs a support edge from
the reusing derivation).

**Decision.** The package ends by recording whether per-partition reuse is adopted for these
kernels, with the observed share of partitions reused when one block of a document changes.

**Evidence.** Editing one block of a fixture document and re-running sentence annotation runs the
model host for one block; the other partitions' digests are unchanged and were not recomputed,
asserted by counting host calls. A consumer keyed on the changed block re-runs for that block
only. Revoking the derivation that first produced a reused partition invalidates the product that
reuses it.

## Migration scope

Grouped as the reference investigation recorded it; each package takes the groups named.

| Group | Modules | Package |
|---|---|---|
| A, model and shape | reference classes in `cs/semantic/` and the model files under `cs/model/semantic/` that declare reference slots; generated wire types; output witnesses in `cs/methods/` | SBX-05 |
| B, token and sentence producers and consumers | `sentence_products.py`, `canonical_sentences.py`, `hanlp_products.py`, `constructions/{named,navigation,math_scope,matching,layers,retained_rules,retained_declarations,declared_named}.py`, `construction_products.py`, `external_extraction.py`, `learned_primary.py`, `proposals.py`, `declaration_products.py` | SBX-03 with SBX-05 |
| C, characterization family | `contextual_characterization.py`, `model_characterization.py`, `characterization.py`, `constructions/evaluation.py`, `declared_formal_readings.py`, predicate methods, `evaluate/characterization_assessment.py`, `evaluate/assessment_graph.py` | SBX-05 |
| D, declared reports | dossier, artifact, clause, definition, structural and contextual-witness products; structural serving; evaluation readers | SBX-05 |
| E, contributions and rich | `contributions.py`, facet modules, `rich_*` modules, `selected_contribution_*` | SBX-05 |
| F, PostgreSQL programs | admission, rich admission, request attachment, derivation, population acquisition, source sets, structural and definition admission, contextual witnesses, record grade, operation events, binding support, completion settlement, authority basis, projections, support edges | SBX-05, SBX-06 |

Tests that pin reference and key shapes are listed in the SBX-00 baseline.
