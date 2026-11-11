# Enriched-document model and retained products

**Proposed · 2026-11-10.** Owns TC-01/02 design. [Coordinator](../text-characterization_2026-11-10.md)
owns execution state and O01/O03/O05 disposition. Inputs are current source, architecture, the
[functional review](../../functional_reviews/text-characterization_2026-11-10.md#O03) and
[representation mechanisms](../../library_leverage/libraries/text-characterization/representations-and-composition.md).
All implementation and acceptance below are planned, not verified behavior.

## Foundation and selected realization

`ingest/annotations.py` already stores immutable token/sentence columns and native source pieces;
`ingest/annotation_views.py` reconstructs native working Docs without inference. The released
[observations model](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml)
has attributed operations, coverage and independent contributions. Its finite PredicateFrame/Cue/
Reading vocabulary does not express the full operators, binder scopes, discontinuity and correlated
choice structure required here. Extend the executable model and generated projections rather than
put an untyped semantic object into `parse_detail` and call it the shared model.

The physical source is the existing immutable published document product. A new enriched view
references it and selected analysis layers; the view neither copies the complete source per layer
nor mutates native Docling hierarchy. The source's page/item geometry and text offsets remain
different coordinate spaces. A span is always qualified by its source projection; one enclosing
interval cannot replace actual discontinuous membership.

The design follows [D1](../../design/D1-knowledge-representation.md),
[D2](../../design/D2-schema-and-guidelines.md), [D3](../../design/D3-database.md) and
[D8](../../design/D8-agent-and-query-interfaces.md). An enriched document is a logical composed
product, not a requirement for another object per source token or a universal live Doc.

<a id="TC-01"></a>

## TC-01 · Executable model, identity and operation contracts

**Prerequisite:** TC-00 authority. Deliver released declarations, generated boundary types and
independent semantic examples before consumers depend on the new representation.

Use the following conceptual types under the existing semantic release; local implementation
names are discretionary, while these meanings are required:

| Concept | Required fields/relations and owned meaning |
| --- | --- |
| EnrichedDocumentView | Exact base-document pin; selected layer revision references; source selection/profile; dependency closure; per-family coverage. A source-only view is explicitly weaker. |
| AnnotationLayer | Producer operation/version, release/runtime/model/grammar/config/input identities, source/context scope, outcome, annotation inventory and dependencies. It is immutable after publication. |
| SourceOccurrence | Qualified source/projection and ordered real extents/native addresses. Repeated equal text has different occurrence identity; synthetic boundaries are not literal source. |
| Annotation/Construction | Kind and schema vocabulary, occurrence membership, native scheme or interpreted meaning, producing premises, rule/grammar identity and status. Unrecognized text retains located native evidence. |
| Membership/RoleAssertion | Own identity, owner/group, member, role, order where meaningful, source support, premises and scope. One member may belong to several groups. |
| SemanticTerm | Predicate, participant reference, operator, quantified binding, attribution or clause relation; typed children/roles and original evidence. Unknown/implicit roles remain explicit. |
| ChoiceGroup/ChoiceMember | Alternative identity, compatibility kind, required premises/choices and supported root. Semantic “or” is an operator inside a reading, not an analytical alternative. |
| FamilyCoverage | Operation, eligible/examined/unexamined scope, availability/outcome/reason and supported profile. Successful empty differs from unknown, unsupported, failed and partial. |

Persist occurrence IDs independently of annotation IDs. An annotation ID is deterministic within
its source/layer/semantic revision and canonical content; it is not a raw text hash, database row
number or live object address. Membership identity includes group, member, role, source and relevant
premises so parallel relations survive. Changing analysis creates a new layer; source occurrences
can remain referenced. Cross-layer equivalent proposals preserve their separate origins, with any
semantic grouping expressed explicitly. Group identity does not establish global concept identity.

A group spanning pages3 and4 references two source occurrences under one group ID. Indexing the
membership relation retrieves both fragments. A page-bounded export includes the visible fragment
and an explicit outside-selection member reference, not a claim that the group ends at the page.
Groups can overlap ordinary hierarchy and each other. Keep original containment/order untouched.

Terms form an immutable DAG with explicit alternative dependencies. Within a derivation, terms
compose together; alternative derivations are choice branches. A reading projection follows its
root and required choices. Unknown compatibility never authorizes a Cartesian product. Relative
scope can remain underspecified rather than enumerating every ordering. Structural cycles in
containment/term dependencies are invalid; referential/discourse edges can be cyclic where their
kind permits it. Non-consuming grammatical cycles are unsupported with diagnostics.

Binder terms identify variable/participant, quantifier, restrictor and body; binding references
are not equal-spelling merges. Negation/modality/attribution have target terms, overt cue extents
and interpreted type/status. Grammatical roles and normalized semantic roles retain different
schemes and support. A role suggested by a model is an attributed proposal, not scientific truth.

Each role/attachment assertion carries a declared basis: native prediction, released deterministic
construction or contextual proposal, with exact rule/premise/role/choice references. Native admission
must validate the released support constraints for a claimed witnessed attachment, not just its
producer and coordinates. Compile mechanical rule/premise checks from the owned declaration; do not
create a second linguistic policy. Model-only host proposals stay private/unresolved unless a
separately declared qualified support policy permits stronger standing.

Extend operation declarations to state produced families, exact required layers, examined source
and contextual scope, preconditions, outcomes, effects and result determinants. The full profile
includes all review-selected families. A boundary-only profile cannot satisfy a scope/role consumer.
One invocation may answer several separately attributed family questions without one task per term.

**Consumer integration:** provide construction and contextual code with typed constructors and
read interfaces, using shared production invariant validators. Enrichment consumers read typed
roles/operators instead of interpreting native labels themselves. An independent expected reading
is authored without running those constructors to derive its meaning.

**Acceptance:** distinct equal-text occurrences; cross-page group and overlapping memberships;
nonprojective/discontinuous roles; `not(all(...))` versus `all(not(...))`; semantic disjunction versus
uncertainty; incompatible choice combination refusal; dangling/wrong-source references; correct
explicit unknown and zero-output cases. A second vocabulary uses the same operations without
statistics-specific branches.

<a id="TC-02"></a>

## TC-02 · Storage, publication, combined reads and faithful codecs

**Prerequisite:** working TC-01 declarations. Extend model-generated relational projections and
existing protected operation publication. Keep the relational source records as the base; store
layer metadata, occurrence/member/role/term/choice relationships and family coverage in queryable
relations. Use bounded typed report/artifact payloads for larger native trees and semantic node
arrays; reference these from relations rather than duplicate full reports in every membership.

Publish layer inventories and endpoints coherently through existing task/attempt fencing after
private computation. Do not hold publication locks during inference. Failed/partial family outcomes
may publish their valid independently typed results under their actual status. A composed view can
reference settled layers even while another family is unavailable; it cannot advertise that family
as complete. No mutable single “latest document” silently mixes revisions. The caller selects a
view pin/profile; a convenience current selector resolves once to that exact closure.

Add indexes for qualified annotation/group membership, source occurrence lookup and layer/family
selection. Fetch all requested groups' memberships in sets; avoid one database call per fragment.
Bounded queries hydrate relevant native items, ancestors and semantic closure, not a full book
simply to display one annotation. Complete exports stream source order and layer inventories with
explicit continuation and dependency references. Display limits do not narrow analyzed coverage.

The selected reader operations are: inspect a document/view and family availability; enumerate
annotations by source region/kind; retrieve an annotation's complete recorded membership; inspect
roles/operators/alternative dependencies; project a supported bounded reading; and export/replay
an exact view closure. CLI/MCP and downstream algorithms consume the same domain read operations.
A read performs no tokenizer, parser, model inference or private linguistic reinterpretation.

Codec contracts retain exact text/ordered extents, native schemes, IDs, source maps, all choice
references, scores with their native meaning, unavailable states and provenance. Serialize shared
nodes by ID once. A decoder rejects dangling references, illegal cycles and incompatible source
pins. Do not use recursive full-tree expansion as the factorized result format.

Native formats have bounded roles. [Doc arrays](https://spacy.io/api/doc#to_array) expose numerical
columns (HEAD is relative, unlike constructor heads). [DocBin](https://spacy.io/api/docbin) supports
native training/evaluation exchange with selected attrs and optional user data; extension definitions
and external models remain separately identified. `Doc.to_json()` in inspected3.8.18 omits group
attrs/scores and span IDs; it cannot be the complete codec. Lark1.3.1
[Tree](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree.py)/
[Token](https://github.com/lark-parser/lark/blob/1.3.1/lark/lexer.py) generic copy/pickle does not
preserve all position/isolation properties. Freeze required metadata explicitly. A native SPPF
remains transient; retained semantic packing includes grammar/input/rule references sufficient to
inspect its supported derivation without rerunning recognition.

Changing model/tokenization/prompt/input context changes inference determinants. Changing a pure
construction recipe recomputes its semantic layer from retained native evidence. A changed view
selection creates a new composed view pin. Existing results are never rewritten; downstream
analytics bind the exact layer revisions they consumed. Reuse preserves original producer provenance
and does not create an independent evidence vote.

**Acceptance:** storage and detached replay agree with independently specified extents/choice
members/scores, not only a roundtrip through the same codec. A page query retrieves other-page
membership deliberately; malformed pins and mixed-source layers refuse. An incomplete layer
retains useful siblings. A rule update reuses native inference while replacing affected semantics;
a tokenizer/prompt change cannot reuse incompatible inference. Cancellation cannot publish a
partially committed complete view or leave readers holding private native objects.

## Execution fit and extension scenarios

Keep shared source buffers and model preparation at useful scope. Detach final immutable fields
before releasing native views; do not retain a complete Doc for each annotation. A layer is a
semantic boundary, not automatically a process. Relational memberships answer indexed lookups;
packed payloads avoid enumerating scope permutations. Large source regions remain supported through
existing ordered bounded reads and meaningful contextual scopes, with explicit partial outcomes
when an actual supported profile cannot examine the whole requested universe.

A new qualifier construction adds semantic terms/relationships to a layer and changes dependent
analytics; source capture stays reusable. A later topic grouping attaches identified memberships
across arbitrary source boundaries through the same view contract. A new provider supplies its
native scheme and mappings, then the shared construction owner consumes that evidence explicitly.
These scenarios justify the layer contract without requiring every future integration now.
