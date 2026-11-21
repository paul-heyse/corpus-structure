# References and projection keys

**Status:** SBX-05 in progress. SBX-06 and SBX-07 proposed.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how one product refers to another and how a consumer is keyed on what it
reads. It owns SBX-05 to SBX-07. It consumes the collection, partition, field-group and proof
contracts of [Populations, rules and proofs](populations-rules-and-proofs.md). Source facts are
**Inspected** at `7a415d18d`; design statements are **Proposed**.

The [post-SBX-01 amendment](../set-based-execution_2026-11-21.md#post-sbx-01-review-amendment)
integrates review [I01–I04](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I01)
and [I08's memo conditions](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I08).
These are planned changes, not additions to SBX-01's completed native scope.

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
upstream product id. The derivation's recorded inputs bind the role to a product. A body can
be identical whenever its complete declared determining inputs and policy agree, and every
citation is a declared bound input. A role-relative body has meaning only together with its
original derivation bindings, which every reader of references must receive.

**Producing meaning and current support.** Resolver and replay interfaces take separate typed
inputs for original derivation bindings and exact current selected support. The former
interprets the published body's role-relative addresses; the latter determines whether a
particular use can currently rely on equivalent selected inputs. Neither a first match across
uses nor the union of their inputs supplies that meaning. Multiple inputs under one role need
a declared discriminator or unique address. A current selection may substitute only under its
declared policy and complete projection equivalence, with exact occurrence and authority
checks retained. A transitive upstream request keeps its own demand and selected support.
Existing support relations carry the required provenance; the proof owner distinguishes
[content conclusions and admissible establishments](populations-rules-and-proofs.md#proofs).

*Exceptions, stated.* A view that is an index of products (document composition) refers to
products by id because that is its content. Rich selection embeds support references and stays a
variant of the carrier. Source-set proofs and pins on bound inputs keep their existing native
checks.

**One resolver.** Python resolves any reference through one function over validated carriers:
the role gives the producing input; an item reference gives a partition, decoded once and
memoised by digest, then an index by the declared key. PostgreSQL resolves a member by its keyed
row; it resolves an item address inside one acquired partition or consumes an applicable
membership proof covering that address. An existing partition without that item must fail
resolution. Before body hydration or disclosure of existence, authorize the actual target
parent: project, kind and exact current selected cut for a live use; captured custody for
detached replay. An original producing binding supplies address meaning, never permission to
fetch a revoked or hidden original parent. An admissible equivalent current selection can
support a use under its declared substitution policy without granting access to the original;
if resolution requires an original body that cannot be acquired, it refuses. A hidden target
is not an absent target. Scope authority/support setup by the authorized parents and traversed
edges; enumerating
unrelated frontier uses or protected leaves is not a bounded point lookup. Genuine replay
retains its complete required closure.

**Occurrence identification.** SBX-03 acquisition/lowering identifies the current source-local
occurrence; SBX-05 preserves it in binding and resolution. Equal complete text and relative
span projections can establish computational equivalence across page movement or changed
source identity without an occurrence map. They cannot locate a particular repeated paragraph,
identical table cell or split/merged block. Establish correspondence only where a consumer
needs to locate or rebind that occurrence, and acquire current partitions afresh where it
remains unknown. The shared [change scenarios](cutover-and-qualification.md#change-scenarios)
keep computation reuse, proof reuse and occurrence attachment distinct.

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
projection, or their rules have moved to admission. Subject, source and placement facts made
available to the kernel are determining inputs too; unknown reads conservatively widen their
projection rather than removing context from a key while still exposing it to computation.

**Derived and checked by introspection.** The existing code-identity analysis records code
reachability, not data access. A read-set pass is added beside it: constant-key subscripts and
`get`, attribute access on typed carriers, destructuring in loops, return paths. On two
dictionary-reshaping kernels a prototype resolved every read after about eight patterns; kernels
that hand a value to spaCy, HanLP or GLiNER are not resolvable and are declared. The pass
proposes projections and reports a declared group that is never read; it is never what makes
reuse sound.

**Projection digest.** For one input, combine the projection specification with the roots of the
declared field groups over the partitions in scope and any observed membership, order, placement
or source premises. Relative-content consumers can omit placement. A consumer that emits
absolute spans or depends on adjacency includes the relevant placement or ordering facts.

This is also the premise contract used by [rules and proofs](populations-rules-and-proofs.md#proofs).
Both paths acquire a shared keyed metadata projection, then hash their actual reads. Existing
partition digests alone do not capture completeness, absence, neighbourhood or proof-relation
membership. Whole-group roots are prepared or retained only for an actual repeated collection
consumer that warrants their lifecycle; deriving a root on demand still scans the relevant
metadata and must be included in its access shape. Text and body-relative spans stay independent
of page placement unless the consumer actually reads that placement. This governs reads and
invalidation alike, rather than narrower hashing over a still-whole input.

**Computation identity and binding.** Reusable computation identity includes the operation,
declared input projection digests, parameters and relevant execution policy. A subject or
occurrence fact enters that identity only when the result depends on it. Editing an unread
field group, moving a block or changing source identity therefore need not change a
relative-only computation key. A placement-reading consumer includes the changed placement.
This replaces blanket subject-context salting of reusable computation; it does not remove
context from current binding or publication.

On a matching computation, attachment authenticates the exact current occurrence, project
authority and selected inputs. The use records its selection; the derivation retains its
original bindings. The declared value-substitution policy can extend from equal bodies to
equal complete projections. Current authority, revocation, selected support, required
admissible proof establishments and publication fences remain independent checks. A matching
content conclusion cannot authorize reads. Live reads recheck authority, including between
pages and for protected issuers; detached replay establishes the captured custody represented
by its own inputs, not current live permission.

**Model changes.** A role's contribution to recipe and definition fingerprints becomes the
projection specification's identity, not the whole kind closure. Adding a property no consumer
reads then re-keys no consumer.

*Stopping short.* Kernels with `whole` scope key on every partition they read, though still only
on the field groups they name. Bodies that record a batch digest, or whose numbers depend on the
cohort, do not reproduce per block; those producers are declared whole until their output is
made batch-independent.

<a id="sbx-05"></a>
## SBX-05 — One reference model

**Implementation checkpoint · 2026-11-21.** Operations declare the output slot, producing
input role, target variant, and collection when applicable. Compilation checks the nominal
reference paths in output bodies and partition items. Native settlement verifies whole-product,
member and partition-item references against the actual producing input set. The shared resolver
and detached adapter distinguish producing derivation bindings from read authority. The keyed
live adapter checks the acquired read before opening a partition. Targeted native reference and
partition cases passed (`36c68b2601894c31953c38f6270fa916`).

The carrier serializes each partition-key component as a nominal text or integer record. Python
exposes a tuple of the scalar values, and native closure compares those values in order.
Whole-product and member references omit the key. The prepared display and tagged schemas
reject fractional and boolean integer parts.

The live binding projection returns producing input metadata for declared scalar reference roles.
Each returned address must be an exact input of the producing derivation and appear in the
current fulfilled use. The PostgreSQL control verifies disclosure for the authentic pin and
excludes an equal-content substitute and hidden or undeclared siblings
(`1f79ee2c6e3f41f9988f6396f5a4f83d`). Symbolic normalization now publishes its occurrence
reference by role. Symbol scope compares that producing edge with its separately admitted
occurrence input. All five symbolic-math cases passed (`bbc42264ea9c4f528f0715db48d895a9`).
The resolver reuses a decoded index for the same authenticated digest and address paths, with
authorization checked for each occurrence (`481f8700fa034696b5b6ef45229dc986`).
Condition reports name the stored qualification contribution through their producing `report`
role. Clause reports name canonical sentence rows through their producing `canonical` role.
The same compiler checks the nominal member and partition-item shape in captured Python output
schemas. The condition producer and admission contract checks passed
(`d16c8bf496654f4eaae69a2b431f1cb8`, `b7eaddf0c4b444a79b6f4f7faed16775`).
An exact PostgreSQL condition member control and cross-demand selected-use refusal passed
(`b02e5d4666ce411dac16a3aef51ee5ea`). The full condition provider and protected issuer route
stopped during native release admission (`37d5e35585ed4893b7edb9821dde8b38`).
The captured integer key field shadowed the compiled integer primitive in native meaning-schema
lowering. Exact property and range IDs now drive lowering, preserving the existing equality guard.
All 15 projection tests passed after reproducing and correcting the conflict
(`08bb0b05b1b041baa7b19fb1b95d01dc`, `22d4ccc1773340f69ef6a42c40c43811`).

The primary construction annotation premises, named interpretation and assessment graph now use
declared partition addresses and producing input custody. Remaining characterization,
structural report, contribution/facet and rich reference slots still require migration. Several
legacy member references name nested graph nodes.
Give those nodes an actual declared addressed collection or a true admitted member before
converting references. Migrate affected serving and evaluation readers to supply the original
bindings and exact current support. Remove the old model types, native reference paths, and
producer checks after their consumers move.

**Vision.** Every reference in the model declares its target; bodies refer by role; one carrier
and one resolver serve all families; closure is a declared rule or an attested one.

**Consumer scope (complete).** The model files that declare reference slots; the Python reference
types (`data_product_reference.py`, `declared_structural_references.py`, the structural,
rich, source-set and interpretation reference classes) and the generated wire types; every
producer and resolver listed under [migration scope](#migration-scope); the output-witness
declarations that compare reference fields with bound inputs; the readers that follow references
without a derivation (the assessment evaluator, structural serving, detached verification), which
are handed both original producing bindings and exact current support in distinct typed inputs.

**Removes.** The shared untyped reference classes; the per-family resolvers and dictionaries; the
duplicated selected-body lookups; hashed local ids computed over an upstream pin; the context
copy inside references; producer-side dangling checks that a generated rule replaces.

**Failure behaviour.** A reference whose role is not an input of the operation is refused at
compile time. A reference that does not resolve refuses the product at admission, naming the
slot and address, where a declared rule covers it; an attested closure refuses at production.

**Evidence.** For each of the three carrier variants, a body with a dangling reference is refused
and one with a resolving reference is admitted, the expectation written by hand. The same source
processed through two different upstream product ids with equal read content yields byte-equal
construction and HanLP bodies. A required cited dependency is represented in support and its
revocation follows the declared substitution/establishment policy. An existing partition with a
missing item refuses resolution. Resolving one token reference decodes one partition, with
authority acquired first and unrelated partitions, uses and protected leaves excluded. Compare
two uses of one derivation with different selections and a transitive input from another
demand; verify historical address meaning and exact current support independently. Live page
revocation and the protected issuer case retain refusal; detached readback retains captured
custody. The [early Revision A chain](cutover-and-qualification.md#early-revision-a-integration)
exercises this interface before the remaining families migrate.

<a id="sbx-06"></a>
## SBX-06 — Projection-keyed request identity

**Vision.** Consumer roles declare projections; kernels receive them; request identity uses
projection digests; PostgreSQL computes them at binding from stored group digests and Python
computes the same.

**Owns.** The projection declaration and its graph edges; the read-set analysis and its report;
the envelope change that hands projections to kernels on all three execution routes; the request
key formula in both languages; attachment of an existing derivation whose recorded input differs
from the use's selection; the complete projection-equivalence basis used by authority ports,
with exact current authorization independent; the fingerprint change for recipes and
definitions. Shared metadata preparation also serves SBX-02 without forcing rules and kernels
to hash the same observations.

**Binding decision dependency.** [ADR-0100](../../adr/0100-ddo-contextual-identities.md) currently
requires the same complete SubjectContext in canonical request and native product identity.
Before changing request identity, SBX-06 must record a scoped successor through the ADR route
and update the owning architectural section. It separates reusable computation identity from
exact current occurrence binding and publication; project/original/analyzed-context custody
remains authenticated, and any context fact determining output remains in the projection.
This planned amendment does not itself supersede the accepted ADR or authorize implementation
under a conflicting identity formula. Preserve ADR-0146's independent authority requirements.

**Order within the package.** Declarations and enforcement first, with keys unchanged, so that a
kernel reading outside its projection fails in tests before any reuse depends on it. Keys change
last. Settle the shared premise and establishment contract with SBX-02/04/05 first, using the
[change scenarios](cutover-and-qualification.md#change-scenarios). Integrate the real
[early Revision A chain](cutover-and-qualification.md#early-revision-a-integration) before
whole-family conversion; final Revision A cutover remains SBX-20.

**Failure behaviour.** A kernel that reads a field group outside its projection fails with the
group named, because the value is absent. A role with no declared projection defaults to whole
scope over all groups, which is today's behaviour.

**Evidence.** Changing only lexical labels of an upstream sentence product leaves the request key
of a consumer that reads geometry unchanged, and a second demand attaches the existing
derivation with no new attempt; changing a token span changes the key. The expectation in each
case is stated from the declaration, not computed by the code under test. A consumer declared to
read geometry that touches a label fails. Where declared substitution permits the equivalent
current selection and every required attestation has an admissible establishment, revoking the
product a reused derivation was computed from leaves the use valid while its selected product
stands; revoking the selected product invalidates it. The surviving use does not authorize a
read of its revoked original parent. Adding an unread property to an input kind leaves
consumer recipe fingerprints unchanged.

For those substitution cases, distinguish a native content conclusion from an attestation
requiring current admissible establishment; no valid establishment follows the rule's failure
policy. Pair a retained-key relocation with renumbered source pointers and a repeated-text or
split-block control. Independently state which cases establish equal computation, matching
proofs and exact attachment. Check actual binding decisions and attempts as well as keys;
relative-only reuse must still read back under the current occurrence and authority.

<a id="sbx-07"></a>
## SBX-07 — Partition memo for block-local kernels

**Vision.** For a kernel whose projection scope is `partition` or `halo`, the envelope computes a
key per output partition from the recipe, the parameters and the projection digests of that
partition's inputs, looks up a retained result, and runs the kernel only for partitions without
one. The product-level derivation, claim and receipt are unchanged; work is proportional to what
changed.

**Conditions, checked at entry.** Eligibility is per actual host implementation and numerical
and replicate policy, not inferred from a block-shaped input. Compare the same block with
different peers and order and check bodies, observations and receipts independently. Sentence
annotation, canonical projection, HanLP, clause classification and learned primaries are
candidates; the entry evidence establishes input granularity, not peer independence. The
projection must include every observed batch determinant. The declared replicate policy must
permit retention of the selected result; "the first retained result stands" is used only where
that is already its meaning. GLiNER carries a batch commitment and the contextual encoder
declares cohort/order dependence. Keep their corresponding whole-collection premise, and do
the same for any candidate whose independence remains uncertain. Whole-source scoped
relations, composition and rich consolidation remain out.

**Open design, settled in the package.** Where retained partition results live (the proposal is
the partition table itself, addressed by a result key beside the digest); how a reused
partition's proof conclusions apply by matching complete premises; and how required
establishments and support sustain a reused partition under the current use. Follow the
SBX-02/06 distinction between immutable content and required admissible provenance. Do not
introduce an unconditional dependency on whichever derivation first produced equal content.
Use source-local keys where sufficient and fresh current acquisition where occurrence
correspondence is unknown; equal complete projections do not imply occurrence correspondence.

**Decision.** Record adoption per eligible host and policy after its determining scope is
established. A focused case must demonstrate skipped unchanged work; this creates no mandatory
provider benchmark, reuse-share target or broader measurement campaign. Uncertain candidates
retain the whole premise and execution route.

**Evidence.** For an eligible host, editing one block of a fixture re-runs that block (and any
declared halo) while unchanged eligible partitions reuse retained results, asserted by counting
host calls. Vary peers and order to expose a missing cohort determinant. A consumer keyed on
the changed block re-runs only its affected scope. Revoked original support with an admissible
equivalent current selection follows the declared substitution policy; revoked current support
refuses. A required attestation with no admissible establishment refuses even when its content
key matches. These cases share the SBX-02/06 authority contract and qualification scenarios.

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
