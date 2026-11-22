# References and projection keys

**Status:** SBX-05 through SBX-07 in progress.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how one product refers to another, how a consumer is keyed on what it
reads and how native changes reach those consumers. It owns SBX-05 to SBX-07. It consumes the
collection, partition, field-group and proof contracts of
[Populations, rules and proofs](populations-rules-and-proofs.md). The original baseline is
**Inspected** at `7a415d18d`. Push-propagation source observations use the
[amendment baseline](../set-based-execution_2026-11-21.md#push-propagation-amendment).
Design statements are **Proposed**.

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

**Selected route · Scheduled · 2026-11-22.** The [completed annotation fork](common-analytical-basis.md#pilot-implementation-and-evidence)
retains immutable acquired rows and exact original producing roles. Finish this contract on
the installed successor and remaining families. A retained projection carries admitted
membership while each lookup acquires its current authority. Keep authorized absence distinct
from a withheld parent. [Post-pilot review I02/I03](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I03)

**Native address reuse · Tested · 2026-11-22.** Ordinary publication and projected adoption
share the native validator. It now indexes each distinct admitted product, collection and
partition once per validation invocation. Every reference still checks binding and multiplicity.
The private regression reproduced three acquisitions for interleaved `b, a, b` on the earlier
source (`710e6a47b7874989811a3cb1c07ccbc6`). The replacement acquired two, reacquired both in a
second invocation and reported the first invalid slot in order. All 12 reference and structural
closure cases passed (`uv run ci test --workers 1 --native-host private`,
`0c35a442b72e46a1b185e727141016bb`). Final integrated publication and adoption evidence stays open.
[Native validator](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_reference_native.py#L124)

**Keyed live-read slice · Conditional · 2026-11-22.** Start with the scalar construction slot
in the installed successor. The existing `ReferenceResolver`, guarded exact-parent acquisition
and native `data_binding_partitions` reader supply the physical route. Capture original
producing bindings, exact current selected use and disclosure once under the same read cut,
then reuse the resolver and partition index while reauthorizing each lookup. The existing
`LiveReferenceAccess` single-binding contract needs explicit extension before use with labelled
or multiple occurrences. Keep exact product/member/kind matching and independently compare
current attachment with historical reference meaning.

**Placement · Inspected · 2026-11-22.** The fork test exercises the scalar construction
address. The production assessment reader uses that address within a wider witness graph, which
also uses partition placement and order. This baseline has no qualifying scalar production caller.
SBX-11 owns the optimization unless a later family migration supplies one.

Advance this slice within SBX-05 only if its actual ordinary caller uses the final reference
contract, avoids full selected-closure preparation and passes within the normal 8 MiB examined
budget. Otherwise SBX-11 owns the keyed migration. Preserve the genuine transitive and detached
closure paths until their owners replace them. Keep the scoped 64 MiB fork rerun at its
recorded request scope. The textbook MCP watchdog remains with SBX-11/12. Verify cached
lookup denial, admitted absence, wrong or stale selection, duplicate and ambiguous occurrence,
protected issuer access and independent ordered readback. The local resolver probe establishes
one partition acquisition across repeated lookups with authorization per call, with native
selection and budget acceptance still open. [Scoped probe](../../design_review/evidence/2026-11-22_sbx09-review/README.md) ·
[Live adapter](../../../python/corpus-structure/src/corpus_structure/semantic/live_reference_resolution.py#L50) ·
[SBX-11](owner-resolved-reads.md#sbx-11)

**Remaining family order · Proposed · 2026-11-22.** Complete construction and contextual
premises with SBX-04, then characterization and declaration nodes, artifact and contextual witness
reports, and contribution, facet and rich records. Each move includes the nominal declaration,
actual addressed target, native closure and ordinary, evaluation and detached readers. Resolve
original producing bindings separately from exact current support and retire the replaced
reference types and resolver at their last caller. Preserve genuine source pins and deliberate
composition and rich-support variants.

**Structural contribution facets · Tested by selected identity · 2026-11-22.** Selected
facets now follow the same structural-reference checks as direct structural reads
before yielding rows. A condition publishes a facet under its admitted original attachment
and refuses an equal-content replacement that does not authorize that attachment.
Twenty-six existing identities passed in `1be4a2f8a3554d01af9ebaac4f1d74c3`. The new
test passed after a test-fixture correction (`f57a12efaeef45cda8153c648e53ca8a`). The
rich support carrier still describes the exact selected support occurrences.

**Definition component addresses · Tested by selected identity · 2026-11-22.** Definition
component producers now publish components as admitted members. Statement admission,
evaluation, applicability, dossier preparation and selected extraction read that one member
population. The isolated managed selection passed 157 ordinary and captured model checks
(`9a4e81e2f79a4f50a03a3a1d8af72d52`). A retained pre-conversion witness archive replayed
through the generic verifier using its own captured schema. Current structural interpretation
uses the current admitted-member shape. The dependent component citations and contextual
relationship edge work have their own acceptance.

**Applicability and dossier inputs · Tested by selected identity · 2026-11-22.** Applicability
and dossier results address admitted definition components through their `components` roles.
Private applicability publication and reads verified applicable and unresolved readings. The
corrected native lineage dispatch refused an equal-content component from a different report
and kept settlement atomic (`5648243b38f9445385a31e236d11a84c`). The issuer-to-dossier journey
passed publication, structural reads, detached replay and exact revocation
(`3561ac986f8142b9bcfd077e88f43451`). Its dossier input had an empty applicability predecessor
set. Native origin controls exercised actual applicability predecessors separately.

**Discovery-derived reference roles · Inspected · 2026-11-22.** The remaining construction
and contextual dependency rosters include discovered `formal`, `constructions` and
`supporting` occurrences. Two admitted products can share source scope and a local member ID.
The current occurrence-bound declaration derives its label from a frozen source set.

**Accepted first use · implementation Proposed · 2026-11-22.** The operator selected an
unordered set for independent formal inputs. Use the original derivation's role-local input
position for construction's discovered `formal` role.
`ops.ddo_derivation_input_positions` already derives that address from frozen binding inputs.
A discovered sequence currently inherits producer output positions. Independent formal products
can both emit at position zero. Native and Python binding require unique sequence positions and
native admission checks the actual producer position. Project the existing ledger address through
authenticated acquisition, with the emitting position retained separately.
Resolve the original input at its recorded position, then authorize that role's exact product,
member and multiplicity in the current selected use.
A rank change among other members of a current unordered selection does not change the address
in the original binding. Exercise this case alongside same-member overlap, multiple exact uses
and unauthorized substitution before retiring the rosters.
[ADR-0151](../../adr/0151-sbx-discovered-formal-inputs.md) · [Native position owner](../../../python/corpus-structure/src/corpus_structure/semantic/binding_support_native.py)

**Primary construction formal set · Tested by selected identity · 2026-11-22.** Native
attachment supplies ledger addresses from the exact frozen request. Construction publishes
grammar-atom premises through the unordered `formal` role and resolves their original input
occurrences. Eighty ordinary controls passed, including two actual formal reports with one
source scope and overlapping local member IDs. Reversing their input order preserved byte-identical
construction output (`03dc639a6a88427c94ca37857900167f`). Private native controls checked both
emitting positions at zero, native settlement, live and detached resolution, current set rank
changes and unauthorized substitution (`cbf3eadd35d84ba2a2df73932291220d`). An actual private CUDA
construction with one formal report passed attachment, proof settlement and selected partition
readback (`74eb5f706a3840898e90148d6f84a75d`). Remaining work includes the adjacent contextual
sequence and supporting roles, whole dependency rosters, packed external-choice edges and the
integrated installed two-report producer journey.

**Bound contextual witness outputs · Tested by selected identity · 2026-11-22.** Published
carrier and cue references address exact admitted contribution members through the frozen
`cues` role and its occurrence labels. Authored request pins still govern acquisition.
The prepared witness suite passed 15 tests (`61a68b1c01084ab4931d6ccbe0917821`).
Native publication and detached replay passed in the selected current-source identity
(`f6887f3302c24cce9fa12cc67321c07a`). The stable three-case native selection also
passed (`2a7b52bc1af346598547f25f583c0741`), including receipt-backed tamper refusal
and the same-span workflow. The earlier parallel run
(`00f660a4a27744bdad5841f6191463bb`) refused changed source custody during setup.

**Selected relationship members · Tested by selected identity · 2026-11-22.** Witnessed
retrieval publishes selected relationship edges as nominal members. The decision reconstructs
its ordered meaning from that population. Applicability cites the relationship role and edge.
Dossier comparison checks its independently selected relationship against the applicability
predecessor's original exact relationship input and edge. The existing `specializes` semantics
use the admitted selected edge. Private native same-span publication and verified replay passed
(`3b4e981d48134065b98b2ab863cf2b07`). Seventeen final-source preparation, selected reader and
dossier controls passed (`cf489c7db81045fb9a5c6938aa158b7b`), including equal-edge and different-origin
refusal. The installed applicability and origin controls passed together on the combined
lineage and relationship source (`1f67d1b8507645d881f5e1070a00bbca`). They exercised the
actual admitted edge and refused another selected edge or a different component origin.
Actual live structural readback passed (`191e6dbaefbc4194912c3d56f36f3d68`). Thirty combined
dossier and admission controls passed (`ed2408d8fcad496fb06f4e93e6a4febc`).
Installed dossier publication with a populated applicability predecessor remains open.

**Contextual native graph proxies · Tested by selected identity · 2026-11-22.** The native
contextual report names formal and construction proxy endpoints through scalar nominal member
slots. Proxy identity follows the producing role and member key. Stored provider citations
retain their original meaning. D1 resolves the graph from its exact acquired binding. Product
readers authenticate a complete graph through one fulfilled use and its historical declaration.
They can show one meaning authorized by multiple uses. The graph refuses missing original
support, combined partial authority and conflicting authorized origins. All 26 selected
graph, learned and projection controls passed (`49ba2face1604acbbc5e6e486cdce3f9`). Six
focused selected resolver cases passed (`cc795bc39c484d8fb196768b9b805063`), including an
older release first and exact-plus-substituted support. Downstream capture passed
(`aa4752ebbb5e430799dbf24a76f63dd0`). Live provider acceptance for this graph migration stays open.

**Contextual witness references · Tested · 2026-11-22.** Witness bindings declare whole-role
references to the producing query and inventory. Retrieval requires exact original-to-current
support for those roles and publishes its witness input through the producing role. The
duplicate source, hypothesis and cue rosters are removed from the witness header. The
twenty-two targeted contextual and declaration controls passed (`uv run ci test`,
`78a69d5fc2ea458ca72d91d3d23849de`). Final installed native and detached acceptance is
tracked separately from the compiled and in-process controls.

The two fresh native witness and detached-workflow cases booted the current model and
reached actual publication. The result failed on the witness producer gate and downstream
selection (`uv run ci test --native-host private`, `28c74bb5e5d94b82b5865832c1d5c0de`).
The witness path now uses the scoring owner's producer check for exact frozen query and
inventory support. The corrected native run is still required for qualification.

The real witnessed-retrieval identity passed after that repair in
`e0b50b52c4d04f7aa4b6591bb1396ab3` (`uv run ci test --native-host private`). The
same-span detached workflow in that result still failed before export because it
obtained no witnessed report.

The next private run (`9cc7011aaedb42b28e8c59945ee0c18c`) reached genuine export on
the selected route and failed when the detached validator saw native tuple constraints
under a different schema dialect. The same-span path refused valid cues sharing an
ordinal. Cues now use exact set membership, and detached execution evidence uses the
native Draft 7 generator. The twenty-two witness and declaration checks and twenty
evidence leaf controls passed (`uv run ci test`, `f92c3b20769440bea1bc8ec6c414060c`,
`9addd92daefb4822b184a8a98b10d3b6`). The next native retry
`253b130a1a574022bfcf144a2a23a9d2` exposed that merging the native completion schema
dropped local leaf definitions. The support owner now preserves those definitions.
Twenty leaf controls passed again (`3a8e615dd88d445680585e5e47b4fa38`). The fresh two-case
native result `30d13215361b4aac9a2a819a7720ac8d` reached both detached archives and was
interrupted while the exported, generated completion union repeatedly traversed recursive
values. The export now composes the leaf with the existing native completion definition,
including its tag-directed value schema. All twenty leaf controls passed (`uv run ci test`,
`8a3e46010d7a44acae7b2dee881c4d5b`). The exact contract validated three selected execution
evidence rows from the retained same-span archive and four from witnessed retrieval.
The next fresh replay reached captured product meaning validation (`ae054eb03db94283b6d01725c3ce113d`,
interrupted). The generated native schema now dispatches on the field name or recursive tag before
validating its payload. Required fields check presence by name after the item schema accounts for
payload validity. Sixteen projection controls passed (`uv run ci test`,
`93a691c437e148009661f0cfd04daf74`), including valid deep nesting, invalid tags and missing fields.
The next private capture (`b566ee9f99d84de0bdd4a361fbbcb1bd`) produced both contextual archives.
The older in-process reader re-entered generic DTO validation, so that managed invocation was
interrupted after export. The validated native completion now carries through the typed leaf.
The detached reader also treats an omitted computational support kind as the native schema's
declared computation variant. All twenty leaf controls (`dd927263d1334f14bc7e571420dfb3a9`)
and fifty-two demand-result and manifest controls (`dcc08e9620e84c359dc1cc0a3378d01a`) passed.
Both freshly exported archives then passed direct `verified_demand_export` replay, including
the selected relation types and the exact query, inventory and witness references. Their
manifest digests are `f6a06f057656a83afa4ea839f0b56f75f51ebdf15edb07611a648af1bbcecc53`
and `96f35b886261f87da8e6f0e69e1567dbf63d414d865064db15ecfa3cc544e7f9`. The joined managed
journey on the final registered root remains open.

**Artifact sources · Tested by selected identity · 2026-11-22.** Artifacts verify their
exact source pins through the original binding and reference witness. The redundant
source and report rosters are gone. The nineteen passing identities in
`964cbda823c848449920eed08ac40adc` and the exact compiled profile retry
`22576b9e004c4f2e855c3402f819b521` cover this slice (`uv run ci test`).

**Artifact nomination occurrence · Tested by selected scope · 2026-11-22.** A nomination
set can include two scoped reports with the same source pin and contribution member. The
caller assigns a unique occurrence label when freezing each exact whole report. The producing
binding and sealed input carry that association. The body names the role, label and admitted
contribution member. Current and detached readers follow the same address using their acquired
authority. Set `occurrence_label` on the entries in `artifact-nominations` and use its value as
`report_occurrence` with `contribution_id` in `nomination_selections`. Thirty-six isolated
`uv run ci test --native-host private` controls passed
(`1ca7281ba20d4b95a72f143477bf7a55`), including overlap, duplicate-label refusal and native
and detached resolution. The final input basis selection covered 58 passing identities,
including relabel refusal and selected lookup (`8a43ad9b7d6a4ddb9e82aecbb3e600de`). Its native
parity fixture needed the current definition fields and passed on exact retry
(`d1e5922d71614b5dbc94de9b0b54080a`).

**Learned dependency custody · Tested · 2026-11-22.** Learned observation bodies and
manifests no longer copy dependency rosters. The concrete Maverick and D1 candidate manifests
name their required whole roles. Enriched composition and selected-context encoding obtain
those inputs from the exact producing use and require the selected closure. A declared
dependency-free kind has an empty set. An undeclared or unavailable input refuses affected
work. The CPU worker receives the acquired dependencies as sealed arguments for each logical
item. The 30 ordinary and private native controls passed (`uv run ci test --native-host private`,
`340cee91aaf348eca6c90d1aef34ed22`). An exact nested disclosure control passed
(`d885635ee7bd402085351bece202ebda`), as did the independent per-item batch control
(`15497e3ff1224cb1b6b023f5a0bf79f3`). All 29 final composition and contextual encoder controls
passed (`1431268ff2304ca88c15fe11c077c78c`).

The actual private D1 literal-operand journey passed by selected identity in
`8920778f3dbc4abe8e0ee28db5377622`. It compared the selected source operand with the retained
provider response and validated its exact selected product against the detached archive. The
combined result failed in the other selected identity, which reached fulfilled Maverick, HanLP
and Dipo publication. The next attempt confirmed the HanLP constituent in the admitted `rows`
partition and exposed an assertion that grouped the selected Maverick report with its members
(`88e9584720504b319f6727dd38923f67`). The exact corrected three-parser provider journey passed
(`d423aa9a82fe4d0eaa35c629976eba5c`), including the selected Maverick report in a verified archive
and an unchanged resume. The actual literal D1 fixture uses the fixed-question path.
Candidate-conditioned `text.d1_candidates/source-native` has separate acceptance.

The private candidate-conditioned D1 run passed contextual publication and returned a real
candidate with a nonempty proxy population. Its broad support read exceeded the 8 MiB page
bound before export (`2a421f4617134d5fb8223bdc7c9ff689`). This run used a shorter source and
an explicit 240-second completion bound. The focused retry uses separate keyed product
selections and an explicit 32 MiB archive page bound. Final-root provider and read qualification
remain with their owners.

**Named-definition cutover · 2026-11-21.** The named producer publishes a nominal refinement
of definition components. Each witness belongs to the producing report and is keyed by the
component ID. Annotation and construction addresses resolve through the actual bound roles.
Downstream components keep their reusable semantic fields and obtain witness evidence through
the original report. The superseded component-embedded witness is rejected. Fifty-six focused
cases passed across the selected results and the corrected empty-partition fixture
(`uv run ci test`, `f401d78025654b2f833ea9ccd8327f2b` and
`7fb452f8308a4b5f8512e5295afbabbe`). The actual native named publication and altered-body
refusal passed in the mixed result `cce6ea7526ff438daf6df1a70913a5b3`.

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
The fresh textbook route then admitted both releases, ran actual annotation and predicate
producers, and published the condition proposal with its role-relative attachment. The same
attempt stopped at the protected issuer's missing evaluator grant
(`01b7f38ece3c45e2a1a6b158485114b7`).
With the fixture grant in place, the protected issuer published its statement. Selected support
export then called the raising evaluator body-access guard on a redacted closure product
(`8f498d206f7647e2b92ffb6ce6783777`). The native export must apply the acquired disclosure
decision before calling the per-kind authority function.
The export now gates its body-access aggregate and partition read with the original disclosure
decision. All eight native disclosure controls passed, including public omission of evaluator
rows and refusal of protected bodies outside their allowed acquisition
(`325ce569e9f9483c9374ff91a252e91f`).
The next textbook run reached structural readback after protected publication and disclosure.
Its exact two roots exceeded the fixture's 8 MiB examined-closure capacity
(`9a32de37f2b54367b1a0c1dea616ba26`). The fixture now selects 32 MiB on the existing request,
with the same roots and 1 MB response limit. Direct serving completed and matched the exact
protected admission and authority. The CLI parity assertion then failed
(`8f9ffdfa6331410bab69a2a1a03db45a`). Complete CLI and MCP parity remains open. SBX-12 owns
reducing the amount transferred for selected support.
Structural delivery now converts the internal implementation value to its public string. The
transport control compares the full output in each existing JSON representation, including
nested arrays and its numeric profile. The regenerated operation-report schemas match the
current reference model. The controlled CLI and stdio MCP test passed
(`25a38114f1fa422f8d33d942468acfd7`).
The textbook rerun completed direct native readback and byte-exact CLI delivery. Its 15-minute
watchdog fired while the stdio MCP tool was rereading the selected closure
(`4247c76fb4fb4a9d991862f0f93ea7d4`). Full native MCP parity and the remaining refusal controls
are open. The scoped direct and transport results remain available separately.

The combined rule, disclosure and selected-reference run passed 15 controls. The authored
evaluator snapshot case stopped in the shared fixture because its installed N47 descriptor
differs from the target source (`ab9d7a128fb941e5bf547e178b05de29`). The snapshot control now
uses the owned current target and records the actual source subject definition in its authored
reference. It passed native publication, complete authored-reference readback and original
support lookup (`0599f05c6cb94a1fbc20a6962669aea6`). SBX-20 owns registered installation and
the matching shared fixture.

The primary construction annotation premises, named interpretation and assessment graph now use
declared partition addresses and producing input custody. Remaining characterization,
structural report, contribution/facet and rich reference slots still require migration. Several
legacy member references name nested graph nodes.
Give those nodes an actual declared addressed collection or a true admitted member before
converting references. Migrate affected serving and evaluation readers to supply the original
bindings and exact current support. Remove the old model types, native reference paths, and
producer checks after their consumers move.
Native settlement and the detached adapter can already consult a declared occurrence field on a
multivalued input. The live selected-use projection and resolver now use the declared slot's
occurrence field and exact current support, including address and multiplicity. Acquired body
authority gates discriminator reads. The selected CLI/native and reference tests cover missing
and repeated occurrence, hidden support and equal-content substitution refusal.
`uv run ci test` passed 13 targeted controls on the shared resolver slice
(`73b1d966a4d0429eb0fe1146f987a18f`, 2026-11-21). The remaining reference families still
need to adopt the shared carrier and their actual occurrence determinants.

Contextual and model characterization readers now resolve admitted graph member packets.
The focused suites passed 49 cases (`08d9c872f479491484d04da474735440`) and three addressed
packet corruption controls passed (`e382ddbd9e064444a382fc6a722c308e`).
Clause predicate-frame slots bind actual members of the exact `predicates` input.
Their 12 focused producer and read controls passed (`af5f5c74718442b995e8fdf972b8fcc6`).
The clause report's whole predicate-input anchor now uses the same producing role. Selected
readback checks the original whole input against current support, including when the report
inspected no frames. It acquires only the predicate metadata for that anchor. Nineteen
focused and compiled profile cases passed, alongside six private native closure controls
(`2a26d12c7cf14c8da0b845401e8efb87`, `d839653e6751473ba2d16cbc1044c523`).
Clause GLiNER and D1 witnesses now use distinct role-relative member targets and preserve
the selected observation-set occurrence. Forty-one focused controls passed in the implementing
checkout (`uv run ci test`, `8b52d7a4b39a4de482d040a0b2d5237a`,
`d476ce0657c34c6398c885a10dbc0cb8`). Provider and installed-path coverage for those
backends, the contextual carrier and the other structural, contribution and rich families
remain open.

The initial named-definition basis witness used nullable shared report fields. That schema
lowered the nullable objects to JSON, so native witness paths could not traverse them
(`uv run ci test`, `eef88ba16c1a4888b26057ccdfad1eea`, failed at model capture).
The named producer now has its own nominal report with annotation and construction roles.

**Vision.** Every reference in the model declares its target; bodies refer by role; one carrier
and one resolver serve all families; closure is a declared rule or an attested one.

**Consumer scope.** The model files that declare reference slots; the Python reference
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

The [completed common projection pilot](common-analytical-basis.md#pilot-implementation-and-evidence)
selected immutable acquired annotation rows. Use the installed successor to extend the scoped
native controls through actual governed changes, exact current support and downstream adoption.
The shared [change scenarios](cutover-and-qualification.md#change-scenarios) own the journey.
[Post-pilot review I01/I04](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I04)

**Remaining delivery sequence · Proposed · 2026-11-22.** Start from the direct scalar
settlement and pinned-read controls in `285ce76aa`. Use authoritative publication, attachment,
selection, activation, original admission, membership, closure, proof and trust writes. Match
selected and prospective roles and use the existing executor to settle bounded immediate
recipients. Reuse retained publication fulfillment and release activation facts for replay.
Add a transition fact only for an origin whose required change cannot be recovered from its
existing authoritative records. Finish exact-pin and first-match wake, same-generation joins, in-flight
coverage, supersession and lost-acknowledgement recovery before deleting their last recursive
watermark and sweep consumers. Preserve record-grade and pinned read authority. Exercise both
computation cutoffs on the actual canonical chain, including compatible release contexts and
current occurrence publication. SBX-07 retains the canonical worker-local memo and verifies
current placement, scoped proof and authority on that same journey.

**Exact waiter · Tested · 2026-11-22.** Exact source-set pins now compare keyed native
fulfilled uses with the retained waiting read. The ordinary planner rechecks binding once
when a matching use becomes visible. This origin no longer contributes to the recursive
scheduling watermark. In the installed private control, an unrelated product left the waiter
asleep, a new exact episode triggered one insufficient recheck without changing the watermark,
and the following exact episode allowed binding to all required uses
(`uv run ci test --native-host private`, `b7ae512c07654fbda060d649e43d17e1`,
isolated current-source installation). The other watermark origins remain open.

**Late original admission · Tested · 2026-11-22.** The ordinary planner compares committed,
newly visible original or authored admissions with the retained wait read and the role's
expected kind, origin and context. Body-dependent selectors can wake conservatively and
binding makes the exact decision. The planner uses the matching marker instead of including
all original admissions in the old watermark. In the private two-original collection control,
each first admission wakes only its matching waiter, leaves the unrelated obligation asleep and
binds the exact admission ID (`uv run ci test --native-host private`,
`33feb2a48a674b6a810484b3862f4d5b`). The direct scalar control passed by selected identity in
`035fc38a06244ba4acd2b48e5409804e`.

**Selected population wake · Tested · 2026-11-22.** The native read checks a newly visible,
valid selection for the exact waiting obligation. The private PostgreSQL control preserved both
watermarks and the old pinned read when a selected receipt was committed. The ordinary planner
attached the selected holder and left its peer waiting (`uv run ci test --native-host private`,
`14146e1598e1404cbc300283ea8fdaeb`). Base discovery closures and uncovered dependency wake routes
remain with the scheduling watermark.

**Local unpinned wake · Tested · 2026-11-22.** The native read compares eligible dependency-free
same-demand inputs against the waiting cut. The focused private PostgreSQL and SQL projection
controls showed an unrelated publication leaves the obligation waiting, a matching publication wakes
it once, and a later producer fate wakes it once when the candidate disappears. Both transitions
leave the scheduling watermark unchanged (`uv run ci test --native-host private`,
`355750c8b2b542509328604615716461`). Fulfilled prerequisite and base discovery routes still use the
watermark.

**Publication and trust replay · Tested · 2026-11-22.** The private publication-delivery
control passed (`uv run ci test --native-host private`, `cc2f8fa7b3444e14824fb44a68ca5235`).
It verified the exact selected recipient fence, ordered publication and enrollment, replay
under the same origin and binding reconsideration after revocation. This covers the selected
scalar publication route. Broader scoped settlement and proof establishments remain open.

**Actual canonical adoption · Tested · 2026-11-22.** Two genuine annotation captures
with different batch sizes prepare distinct releases and annotation recipes with the same
canonical recipe. A private real-provider run passed the initial chain and failed on the
successor's discovery attachment before adoption (`uv run ci test --native-host private
--providers-only`, `ac9812c001f94d349cd52164f2ae6de6`). The corrected native discovery
gate binds its retained admission-use ID to the current demand and obligation and separately
authenticates the producing episode and compatible released recipe. The CUDA-backed retry
passed (`fc1c520ca269452496679c52b1f3310d`). The successor had a distinct request and selected
the new annotation product, attached the earlier canonical derivation with zero new canonical
generations, and retained the original producing input. Substitution of the previous demand's
genuine use for the same discovery episode refused. This establishes reuse across distinct
release/runtime coordinates for equal effective canonical computation at one exact occurrence.
Move, reconversion and full scoped delivery acceptance remain open.

**Compiler checkpoint · 2026-11-21.** Input roles can declare whole, partition or bounded
halo reads. The compiler emits versioned projection identities and typed edges to the
observed fields and collection properties. Undeclared roles keep their whole-input contract.
`uv run ci test` passed the selected 148 compiler, rule and projection cases
(`85f2a8444bb443b4af48235b47887ef1`). The compiler slice preserves the existing request
determinant until native binding and the execution envelope use the same projection.

**Native and execution checkpoint · 2026-11-21.** The canonical port now supplies declared
geometry and observed header, membership, order and placement through the synchronous and
spawned CPU routes. `uv run ci test` passed 19 focused cases on that slice
(`51c6b3aec36b47e9b2fbcd3b867322d4`) and 36 projection, annotation and reference cases
after integration (`670d348f1f4e4a2489a47780987193f1`). Canonical code custody still rules
out cross-request reuse at that checkpoint. The later native lookup and canonical custody are
recorded below.

The private native projection digest uses the exact authorized binding and the selected
product's stored group commitments. A rollback-only fixture removed the partition body column
and still matched the independently constructed Python projection digest for its declared
header and metadata cases. The installed projection, partition admission and nearby tests
passed (`9329b0a2588f40d5854667a94a4ee054`). This establishes a scalar whole-product primitive
for the binding owner. The additional provider exercise on the isolated source stopped during
sentence-port asset custody (`91a74b75f09d465dabe2ff96e1d63e6a`).
The main checkout's private PostgreSQL and CUDA retry passed the authorized parity check
on the actual annotation and canonical chain and passed the construction reference journey
(`uv run ci test --providers-only`, `a6e497e3d88a413895eb8b59461cfe1e`).

`uv run ci test` passed the installed activation transition and selected support revocation
controls (`d34aeeee6ab14bd089f1ce96f792225b`). Native activation writes one immutable
transition with its compare-and-swap. An obsolete token leaves that history unchanged.
For eligible value uses, validity now requires selected support. The test withdraws current
support while the historical episode remains valid, and separately withdraws the historical
support while the current use remains valid. The output correspondence obligation remains open.
The structural comparison exposed an output-proof consumer that expected both validity
nodes in the closure seeded by the use. Exact source acquisition now checks current-use
validity first and evaluates historical episode and producing-use validity for the exact
disclosed support walk separately. Twelve source-acquisition and disclosure controls passed,
including authentic, foreign, forged and revoked support
(`uv run ci test`, `4ada684bcff24ce3abd10a7ac64ef204`).
`uv run ci test` also passed two effective operation change and reachability controls
(`675a6857ba37487396ed900081bb6114`). These changes do not yet deliver origin changes to
waiters or establish scoped settlement coverage.

The native admission owner now advances a named selection with exact prior demand and
generation, and retains every successor in immutable native history. The owned installed
controls exercised role refusal, cross-project and cancelled demands, same-name races,
independent-name progress, stale/ABA refusal and historical exact replay
(`uv run ci test`, `f863654ea0e64c138f78214996f192a0`, passed).
Selection advancement supplies a fence. Scoped readiness and settlement remain open.

Native publication records a pending receipt for each named head whose exact demand gained
a fulfilled use in the same statement. Rollback, exact publication replay, independent
demands and late publication against a superseded head passed in the installed target
(`uv run ci test`, `ee73278ea98e458bb317b762693ae7ff`). The exact demand, use and receipt
are also retained when the publication transaction cannot see a concurrent named enrollment.
The current generation can reconcile the missed receipt after both commits. Native controls
passed both transaction orders, retry, cancellation, supersession and rollback
(`uv run ci test`, `42816203f05147da97a75a6abf196566`). Readiness arising outside publication
and delivery from a pending origin to a recipient still require coverage.

The existing planner can now start from an exact native fulfilled use and check one direct,
same-source scalar recipient under the current named generation and acquired read. It uses
the declared output and input role occurrences, then delegates to existing native binding and
attachment. The private PostgreSQL control exercised a recipient with no prior request,
an independent selection, a superseded generation and a use created by reuse attachment
without a fresh publication receipt (`uv run ci test`, `374183446a6e4d7383321b1d28adcec0`).
The actual canonical input declaration was also lowered through the native definition owner.
The installed source guard accepted its selected original and refused a different one
(`778354f107084349bd55376509a957f5`).
The first combined provider run found that routing excluded the admitted source universe
(`5fcdb3933847449781ff7d5cd64cb3c4`). Routing now checks that the acquired cut authorizes
the universe before admitting the ordinary or source product. The live canonical chain,
its stored key and exact publication recipient, and the HanLP declaration chain passed
together (`uv run ci test --providers-only`, `0828f95372a34af7ab77c094850c6768`).
This covers directed binding preparation for that route. Automatic pending-origin selection
and durable successor settlement are still open.

The executor's explicit named-origin pass uses the same pinned page, preparation and claim
boundary. Its controlled test verified that only the selected recipient reached hydration,
claim and publication (`uv run ci test`, `9ce1c3847bd84ff6b9bc24ee94949752`, five passed).
When native attachment creates a successor, its `use_id` identifies the exact recipient's
retained use. The binding obligation in the attach result can identify another obligation
that shares that request. Before closing the origin, record the checked role occurrence
against the actual successor use and preserve pending status while that successor or a join
arm remains unresolved.

**Ordinary delivery checkpoint · 2026-11-21.** The normal planner queries current named
enrollment and admitted publication or reuse uses in one bounded native page. The real CUDA
annotation-to-canonical demand observed this route during ordinary execution
(`uv run ci test --providers-only`, `d98622743039499c92b89a692f736a4c`, passed). The exact route
record carries the selected name and generation, origin use and both role occurrences. The native
reader derives `pending`, `attached` and `fulfilled` from the actual latest recipient use and its
selected support. A current fulfilled use must pass native validity. The installed scalar and
publication controls passed (`uv run ci test`, `70f0850b5bf14af892a565d2a1499b29`). Collection,
readiness-only origins and complete scoped cut coverage remain open.

The explicit-origin executor entry point has been removed. The ordinary executor now asks the
native population owner to close only newly visible fulfilled discovery outputs for its pinned
page. The native owner checks existing closure before invoking the same authenticated settlement.
Private publication and request controls passed (`uv run ci test`,
`c2355bad832e4219b38a13f0a5c15fd9`). Cold-root authoring verified the generated discovery program
(`uv run ci model change candidate`, `ac0c58dfeee945d587966c7c69c29bda`).
The real CUDA annotation-to-canonical and HanLP journeys both passed in ordinary native
execution on that combined source (`uv run ci test --native-host private --providers-only`,
`0161fd2155dc4bf2b15455df24033138`).
Waiting uses now retain their acquired read identity. Native scalar delivery compares
origin visibility with that exact read and routes only current valid producer uses.
The installed control observed a late publication once, then retained the same pending
recipient without re-waking it at the next read (`9bb19eb0c42a497d8c8ec25cd5c0fc17`,
six selected cases passed).
For a required scalar original-source scan, the native binding owner delivers readiness from
the exact admitted source at the acquired read. This shape omits the recursive watermark.
The private installed control exercised own admission, cross-demand equal content, rollback,
retained earlier reads and current revocation
(`uv run ci test --native-host private`, `418cd9f8bc074e0396fa3e6523bb1bcb`, passed).
The native owner now handles eligible joins of required scalar computed arms with exact
original scans and zero-premise producers. Both installed original and join identities passed
in `4290f9f41f354ea0b5c0e8df35a188f2`. The join used an actually attached unchanged arm, excluded
an equal product outside the demand, and returned its current binding on one acquired read.
Three planner fixtures needed the required nullable native readiness field. The corrected
26-case planner run passed (`uv run ci test`, `9de533795136429598f16cbe56b5fadb`). Remaining
origin and settlement coverage stays open.

The native attachment owner records a project-scoped canonical computation key beside an exact
new request generation, leaving the retained request row and its execution-origin snapshot shape
intact. PostgreSQL and Python agree on the admitted recipe, parameters, inference and projected
input digest. An installed writer test scheduled distinct exact requests with the same computation
key inside one project and scheduled a distinct key for another project. It refused to use a
prior contextual result as the new request's publication
(`uv run ci test`, `8f55c7a9f62f4bf09480b12e70fc5c28`, three passed).
The execution eligibility and independent current-occurrence authority still govern any future
adoption of a retained result.

Native request attachment now looks up the indexed projection before admitting a new task. An
eligible same-occurrence, same-release result must have a valid producer and pass the consuming
definition. Declared output references are checked against the current binding. The selected use
keeps current support and the retained derivation keeps the producing support. On a private
target, different lexical material with the same observed value reused a retained derivation
under a distinct exact request. An equal key alone did not authorize an output from another
context, and another project had a distinct key (`uv run ci test`, `c2355bad832e4219b38a13f0a5c15fd9`).
Canonical preparation now declares its deterministic helper code, exact numeric policy and
acquired JSON codecs. The real spawned kernel passed with eligibility enabled in
`9bb19eb0c42a497d8c8ec25cd5c0fc17`. Cross-request adoption of an actual canonical
publication and relocation to a new contextual product remain open.

**Target · Proposed.** Consumer roles declare projections, kernels receive those projections,
and reusable computation uses their versioned specifications and digests. PostgreSQL acquires
the digest tuple from authenticated stored metadata before hydration. Python computes the same
identity from the same premises. Publication stores keyed field-group commitments once. Prepare
whole-group roots for repeated whole reads where they repay preparation and retention. The
read-set analysis advises the declarations, and the envelope enforces them on all three
execution routes. SBX-02 can share keyed metadata acquisition while rules and kernels hash
their own observations.

**Binding decision · accepted 2026-11-21.** [ADR-0149](../../adr/0149-contextual-requests-and-projected-computation.md)
supersedes the contextual identity decision for computation lookup. It separates reusable computation identity from
exact current occurrence binding and publication; project/original/analyzed-context custody
remains authenticated, and any context fact determining output remains in the projection.
The request row has a unique key and owns the exact project, release, runtime, subject context,
binding and generation. The computation basis has a separate project-scoped index over exact
request generations. The use authenticates its current selection and the derivation retains its
producing inputs. Retained-result adoption must follow the declared substitution policy and
ADR-0146's independent proof and authority requirements.
[Native attachment](../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1535) ·
[Validity decision](../../adr/0146-sbx-content-validity.md)

**Target review · 2026-11-21.** The accepted execution scope incorporates the selected
computation and native delivery contracts in RC01 and RC02.

| Finding | Current disposition |
|---|---|
| F01 | The canonical envelope and authenticated whole-role key have scoped evidence. The real cross-release CUDA case attached the retained canonical derivation with zero new generations. Integrated cutoff coverage across move, reconversion and the remaining declared input shapes stays open. |
| F02 | Native validity and the actual canonical adoption use separate current support and historical producer custody. The native discovery control refused an earlier demand's genuine use of the same episode. The remaining occurrence correspondence and cross-scope refusal controls stay open. |
| F03 | Activation and named selections have durable fenced transitions. Native tests cover direct scalar work and exact-pin, original, selected-population and dependency-free local input wakes. Automatic delivery from the remaining governed origins and broader enrollment recovery stay open. |
| F04 | Pending publication is visible at its selected generation. Continuous predecessor and successor settlement, unchanged branch evidence, joins and the scoped settled cut remain open. |

[Independent SBX-06 review](../../design_review/reviews/design_review_sbx06-computation-and-delivery_2026-11-21.md#F01)

<a id="change-origins"></a>
### Change origins and selectors

| Governed origin | Change basis |
|---|---|
| Evidence selection | An authorized transition makes evidence current for an explicitly named scope. A new immutable document registration affects a new or open inventory selector only where that selector observes registration. Exact frozen demands keep their release, originals and choices. A governed selection advances through its owner and an explicitly admitted successor when those choices change. |
| Release activation | Compare effective recipes and relevant policies for computation, and eligibility, membership and dependency declarations for discovery or binding. A new release identifier or descriptive edit can leave both determinants stable. Capture actual activation with old and new coordinates and the owning generation. |
| Native publication | Use the committed output role, addresses, collections, fields and scope, including membership and placement changes, as the basis for matching immediate consumers. |

Demand acquisition establishes exact pins. Native admission now holds the named selection of an
exact demand and its explicit successor. Review the scoped coverage and disclosure contract with
SBX-11 before fixing its read acquisition interface.

Derive reverse selectors from the effective model in PostgreSQL. Existing uses contribute
their actual selected addresses, including substitutions. Declared population and waiting
selectors cover additions, removals and first matches, including an input that had no address
when the waiter was recorded. Preserve distinct role and edge occurrences, partition scope,
and observed order and placement. Share determinant comparison with `changed_operations`.
Its conservative walk over old and new topology explains candidates. Native delivery advances
one dependency step at a time. An explicitly scoped NetworkX projection can order or explain
those dependencies from the same typed relationships. Support validity retains its own native
fixpoint and semantics.
[Original registration](../../../python/corpus-structure/src/corpus_structure/semantic/original_documents.py#L91) ·
[Frozen demand](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_service.py#L67) ·
[Activation](../../../python/corpus-structure/src/corpus_structure/semantic/closure_native.py#L560) ·
[Change-impact preview](../../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L157) ·
[Support validity](../../adr/0122-set-wise-support-validity.md)

<a id="settlement-coverage"></a>
### Settlement and coverage

Reuse the recoverable facts committed with governed transitions. The publication receipt
settles atomically with outputs, establishments and fulfilled uses, and native publication
already retains exact demand, receipt and use delivery identity. Activation already records
project, generation and old/new releases atomically with its compare-and-swap. Recover by that
exact transition after lost acknowledgement, retaining prospective selection opt-in and frozen
demand semantics. For other origins, inspect their authoritative records before adding the
smallest missing work reference in the same transaction.

**Ordinary recovery · Scheduled · 2026-11-22.** The overlap control currently repairs a pending
publication gap by replaying selection advancement. Make normal bounded executor resume or
drain reconcile the committed facts and feed immediate recipients without a second selection
call. Exercise event-before-enrollment and enrollment-before-event, interrupted delivery and
lost acknowledgement. Repeated resume must reuse the same delivery claim, and an obsolete
generation must never advance current coverage. Keep settlement in the existing native owners.
[Publication reconciler](../../../python/corpus-structure/src/corpus_structure/semantic/publication_delivery_native.py#L115) ·
[Overlap control](../../../python/corpus-structure/tests/semantic/test_publication_delivery_native.py#L209) ·
[Activation record](../../../python/corpus-structure/src/corpus_structure/semantic/closure_native.py#L558)
[Publication settlement](../../../python/corpus-structure/src/corpus_structure/semantic/data_derivation_native.py#L653) ·
[Durable recovery](../../adr/0140-durable-recovery-and-exact-stop.md)

Process affected immediate recipients in bounded sets through the existing executor's claims,
admission, retry and settlement. Coalesce repeated notifications for the same current binding
and generation while retaining every relevant reason. At a join, settle the combined key
after the relevant arms reach the same selection, including an arm that settles unchanged.
Fence advancement against the current selection so superseded work can retain a legitimately
published historical result without advancing the current selection. Computation remains
demand-driven. For an eligible current binding, equal observed input and operation
determinants preserve computation. A changed determinant can run the producer. Equal
declared output after it settles ends computational propagation toward that consumer.
Current-use attachment and readiness still settle through their native owners.

**Arm and discovery adequacy · Scheduled · 2026-11-22.** Extend generation-checked attached
scalar cuts with affected, unchanged and unavailable outcomes per relevant arm. Include an
interrupted join with an unchanged arm and a change between edges. Discovery's prior-closure
anti-join currently compares semantic product/derivation keys, while population validity also
requires the exact admitted use. Test a revoked or historical closure followed by a newly
admissible use of the same product and derivation. Distinguish incomplete, valid complete-empty,
first-member arrival, departure and closure, with independent expected uses and recipients.
Batch common population-close work only where the native owner preserves support locks,
active demand, current context/recipe, output authority, completeness, duplicate contexts and
atomic closure insertion. This investigation can choose a native set update or retain per-close
calls when their individual semantics require them. [Population close owner](../../../python/corpus-structure/src/corpus_structure/semantic/demand_registration_native.py#L1544)

Advance coverage for a governed selection only when all relevant committed changes and
upstream decisions for the scoped cut are accounted for, including branches that settle
unchanged. An empty local queue cannot establish coverage while a change is between edges.
Supply that scoped evidence to [SBX-11](owner-resolved-reads.md#sbx-11). A scope can settle
independently of unrelated work. A changed computation awaiting authorized demand leaves
the affected coverage pending. A resolved binding with no eligible result can establish
unavailability. Digest-only demand checks remain useful for a newly requested
or rarely read result. Durable push earns its keep by avoiding repeated discovery and work
where observed projections stabilize. Broad fan-out and whole-population or cohort premises
can still require broad work. Automatic refresh requires separately selected maintenance
interest and effect authority.

<a id="readiness-delivery"></a>
### Readiness delivery and retirement

Deliver a separate reason to reconsider binding when an exact waiter gains a usable episode
or fulfilled use, an exact original is admitted, discovery gains or loses members or closes,
applicable proof establishment changes, or trust changes. Attachment can make a use
available without a new publication, and an equally digested product can become bindable
through a second authentic producing episode. Use compact selector facts and let the
binding owner make the precise decision. Prefer faithful admitted metadata for matching.
For body-dependent predicates, allow a conservative wake followed by one scoped binding
check. Keep the computational digest comparison body-free.
[Exact-pin readiness control](../../../python/corpus-structure/tests/semantic/test_data_operation_pinned_reuse_native.py#L538) ·
[Native attachment](../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1778)

**Projection migration · Scheduled · 2026-11-22.** The shared native demand page computes
fallback watermark state when native readiness is absent. Grading reacquires exact obligations
and uses through that page, and export serializes its full native bytes. Give scheduling fields
a scheduler-owned projection. Preserve pinned identity and authorization, historical grade census
and completion, and public status, visual and interpretation answers when removing scheduler
material from shared reads. Test a genuine detached publication-to-export replay and preserve
already sealed pages under their recorded reader schema.

Migrate the planner's waiting gate to exact native readiness and scoped coverage. Finish normal
resume delivery for prerequisite fulfillment, original and population discovery, attachment,
closure, proof and trust changes, including first match without a prior address. Retire recursive
ancestry expansion, watermark hashing, obsolete wire fields and replaced repeated discovery
sweeps with their last consumers. SBX-21 checks their retirement. SBX-11 supplies keyed reads and
SBX-12 preserves exact pinned and detached evidence. An uncovered consumer keeps its required
wake or observation contract open. [Post-pilot review I04](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I04) ·
[Watermark call](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L2559) ·
[Record-grade read](../../../python/corpus-structure/src/corpus_structure/semantic/record_grade_native.py#L447) ·
[Export](../../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L208)

**Finite comparison · Conditional.** If selector semantics remain uncertain, compare the same
captured typed role/occurrence/generation relation with independent expected multisets using
DuckDB 2.0 `WITH RECURSIVE … USING KEY` and `EXCEPT ALL`. Include equal payloads on parallel arms
and changed support under an equal semantic key. Node-only keys can erase distinct arms, and
plain `EXCEPT` erases duplicate occurrences. The retained finite probe establishes these
behaviors. Native PostgreSQL retains enrollment, trust, generation and transactional settlement.
Use a small literal expected relation when it settles the same question. [Finite probe](../../design_review/evidence/2026-11-22_sbx09-review/README.md) ·
[DuckDB recursive CTEs](https://duckdb.org/docs/2.0/sql/query_syntax/with)

**Current consumers · inspected 2026-11-22.** The planner saves the remaining page watermark in
waiting-use selection and skips an unchanged `awaiting-inputs`, `awaiting-population` or
`awaiting-discovery` obligation. The remaining fingerprint covers fulfilled prerequisites and
base discovery populations. The native page separately supplies exact-pin, original, selected
population, local-input and authority changes. The executor repeats pinned, bounded sweeps to
see later publication and drive discovery from the producing episode. Keep each wait route until
its governed origin can wake the exact affected binding through resume, including a first match without
a prior address. The record-grade census also participates in native cut acquisition and
completion, so moving scheduler wakeups does not replace its historical cut and completion
authority. Demand result consumers for status, visual evidence and interpretation still
need their existing pinned page answers while the scheduler moves to native readiness.
[Waiting-use gate](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_demands.py#L739) ·
[Watermark components](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L2005) ·
[Discovery sweep](../../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L2327) ·
[Record-grade completion](../../../python/corpus-structure/src/corpus_structure/semantic/record_grade_native.py#L1439)

**Order within the package.** Settle the origin, selector and identity design together.
Confirm direct keyed replay versus a transactional reference per origin from the authoritative
write and its recovery behavior. If that inspection leaves a material gap, use a bounded
rollback-only commit/retry control on the affected origin before integrating delivery. Resolve
scope and coverage semantics with the SBX-11 read owner before the two packages fix their
interfaces. Enforce the declared envelope before enabling projection-based reuse. Use the
runnable SBX-03–05 slices and shared SBX-02 premises to prove native publication, cutoff and
readiness in the [early Revision A chain](cutover-and-qualification.md#early-revision-a-integration).
Extend writer and consumer adoption from that slice and close each replacement path before
retiring its old reader. SBX-20 owns the stage cutover.

**Failure behaviour.** A kernel that reads a field group outside its projection fails with the
group named, because the value is absent. A role with no declared projection defaults to whole
scope over all groups, which is today's behaviour.

**Evidence.** Changing only lexical labels of an upstream sentence product leaves the request key
of a consumer that reads geometry unchanged, and a second demand attaches the existing
derivation with no new attempt; changing a token span changes the key. The expectation in each
case is stated from the declaration, not computed by the code under test. Both change decisions
use stored digests and leave product and partition bodies unopened. A consumer declared to
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

Extend the [equal-output successor-demand control](../../../python/corpus-structure/tests/semantic/test_change_impact.py#L522)
through actual delivery from the publishing transaction. In the annotation-to-canonical
chain, lexical edits can leave the observed projection equal. Coverage, source, selectors,
placement, order and role-relative addresses enter wherever canonical forwards them. Use
the [propagation scenarios](cutover-and-qualification.md#propagation-scenarios) for native
stopping, join, supersession, lost acknowledgement and exact-pin wake evidence.
[Push-propagation review I01–I03](../../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I01)

<a id="sbx-07"></a>
## SBX-07 — Partition memo for block-local kernels

The [common projection contract](common-analytical-basis.md#projection-contract) carries
block-local meaning separately from observed placement and current address. Exercise that
distinction through the installed successor after the [recorded pilot decision](common-analytical-basis.md#pilot-implementation-and-evidence),
using one charged worker-local canonical memo and current occurrence assembly.

**Earlier canonical checkpoint · Tested · 2026-11-21.** The spawned canonical calculation memoizes the
local row transformation under the runtime-byte owner for its deterministic single-result policy.
The key includes project, acquired recipe, projection and effective parameters,
block address and projected row bytes. Current assembly supplies order, membership and placement.
Every request acquires its own authorized binding and proof premises, and the current CPU reply
and publication retain their own receipts. A focused test changed one block, moved and reordered
the other, and checked one memo hit, changed body and current placement against a direct
calculation. At that source revision, renaming the block caused a miss and produced its current address
(`uv run ci test`, `70f0850b5bf14af892a565d2a1499b29`, passed). Retention is local to a live worker
process. A different process reacquires its own memo.

**Pointer rename · Tested · 2026-11-22.** The canonical worker retains one charged immutable
frame for the local projection. Current assembly fills its exact reference addresses and hashes
the completed frame. Equal typed rows reuse after a pointer rename and retain the new addresses,
order and placement. A different project gets its own memo. Ten selected partition, source and
real spawned-worker controls passed (`uv run ci test`, `0f867b8b822d4391be68bbdbeb6a854f`), including
independent byte and digest comparison, escaped pointers, dates and decimals, the short-address
storage bound and invalid-address refusal. The installed canonical edit and reconversion journey
remains open.

Keep whole-result execution for the other current hosts. The spaCy and HanLP provider fixtures
establish partition addressing and typed publication without establishing identical results and
receipts across peer and order changes. Clause classification observes selected neighbors and
its learned-primary inputs. Learned primaries retain their selected cohort and replicate
authority. GLiNER and the contextual encoder have declared batch and cohort determinants.
Adopt a narrower key for any of those hosts only when evidence establishes its full locality
premise. [Conditions](#sbx-07)

**Vision.** For a kernel whose projection scope is `partition` or `halo`, the envelope computes a
key per output partition from the recipe, the parameters and the projection digests of that
partition's inputs, looks up a retained result, and runs the kernel only for partitions without
one. The product-level derivation, claim and receipt retain their roles. A change can limit
computation to affected partitions when the host and declared premises establish locality.
SBX-06 owns product-level change delivery, readiness and current settlement.

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

**Retention decision · Scheduled · 2026-11-22.** Keep the charged live-worker canonical memo
keyed on project, acquired recipe, declared projection, effective parameters and local projected
bytes. Current assembly renders and hashes exact references, order and placement. The 2026-11-22
rename-hit controls supersede the earlier address-in-key behavior. Apply SBX-02/06 proof and
support requirements independently of the computation hit. A historical valid proof gives no
access to an equal replacement input. Use fresh current acquisition where occurrence
correspondence is unknown. [Post-pilot review I01](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I01)

Persistent partition-result tables or cross-worker caches are deferred until a named consumer
requires reuse beyond this worker lifetime and can establish complete determinants, ownership,
eviction and current support. The worker-local memo supplies reuse through SBX-09.

**Installed acceptance.** In the shared successor, distinguish an unread edit from an actual
producer run settling an equal downstream projection. Test move/rename and reconversion with
independent provenance, repeated equal blocks and ambiguous split/merge, then a read-field and
eligibility change. Assert host-call reuse, exact canonical bytes and digest, proof applicability
and current selected attachment independently. Rebind all local addresses under the current
occurrence. Retain whole-result execution for hosts observing peers or cohorts. [Shared cases](cutover-and-qualification.md#change-scenarios)

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
