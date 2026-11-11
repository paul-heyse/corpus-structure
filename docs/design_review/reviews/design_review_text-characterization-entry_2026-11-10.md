# Enriched-document foundation target review

## Judgment and scope

**Design / target · combined enriched-document model, source semantic fidelity and
storage/publication/read focus · 2026-11-10. Decision: Accept scoped, Proposed.**
The TC-01–02 foundation has a coherent domain and physical realization when source custody,
analysis standing and knowledge admission retain their separate owners. This decision enables
the model, protected retention and readers. It does not qualify producers, linguistic quality,
native deployment or the enclosing characterization pipeline.

The inspected source is `8318ff74a016c6f9e68b81a0607a41b309f33a78`; proposed inputs are the
[TC coordinator](../../plans/text-characterization_2026-11-10.md),
[model/retention design](../../plans/text-characterization/model-and-retention.md),
[functional review O01/O03/O05](../../functional_reviews/text-characterization_2026-11-10.md)
and the approved execution design supplied to this reviewer. No other plan was consumed.
The audit input is the co-published
[entry refresh](../audit/README.md#text-characterization-entry-refresh) at that exact source;
earlier audit entries retain their own limits. Concurrent production edits are excluded.
Core3.3, efficient-architecture heuristics1.0, code-intelligence1.4 and repository binding apply.
Test assessment informs the independent-evidence boundary only; test architecture is not reviewed.

The functional target is a source-preserving enriched document with inspectable, attributed
analysis layers. The workload includes all518 physical Grinstead–Snell pages, repeated bounded
page/group inspection, cross-page membership, overlapping annotation families and complete
detached export on the existing single-operator PostgreSQL host. Layer growth and high-degree
groups matter even when a requested display is small. NLP producers TC-03 onward, their full
profiles, later consumer migration and knowledge-policy changes are outside this acceptance.

## Meaning and authority

**Proposed.** The base is a full `PublishedDocumentBinding`, not one selected SourceView.
Its native product, placement and original release remain exact. A SourceView is a selected
projection beneath that base, retaining its own membership and projection recipe. Immutable
layers and composed views use the existing generic `ProductReference` triple: producing task,
product key and content digest. A layer-local annotation/term identifier is qualified by that
product externally; embedding the final product digest in its own hashed payload is prohibited.

| Fact or relationship | Semantic owner | Fidelity and consumer constraint |
| --- | --- | --- |
| Original document and native address | Published-document/source owner, D1/D3 | Reading order, pages, items, tables, figures and formula locations remain source facts; a layer cannot rewrite them |
| Source occurrence | Released characterization model, D1/D2 | Identity binds exact base, projection and ordered real native/projection extents independently of the producing analysis; equal text does not merge occurrences |
| Annotation and group membership | Released characterization model; producer supplies attributed instances | Group/member/role/order/support/premises keep their own identity; overlapping groups do not become source containment |
| Semantic term or role | Released typed model and named construction/provider operation | Binder, operator, role, attribution and basis are explicit; native syntactic labels do not silently become semantic roles or scientific truth |
| Analytical alternative | Choice group/member/dependency owner | Requires its explicit premises and compatible choices; source-level semantic disjunction is a different term kind |
| Family availability | Attributed family operation and examined scope | Successful empty, unsupported, unexamined, partial and failed remain distinguishable; view assembly does not improve their standing |
| Layer/view publication | Protected task completion and source guards, D3/D6 | Valid private analysis becomes readable coherently; it gains no admitted knowledge standing |
| Bounded reading and export | Pin-native domain reader, D8 | Exact view/base/layer closure and explicit omissions survive continuations; read performs no NLP inference |

This is an adequate model for the supported foundation because construction, native completion,
query and export must consume the same distinctions. Plain output records with free-form JSON
semantics would not suffice. The new trusted characterization module is explicitly acquired and
archived with release inputs; ordinary pack authors cannot replace its meaning under a reserved
module name. Released operation declarations own inputs, produced families, result determinants
and supported outcomes. Existing archive and runtime guards remain effective.

## Realization and alternatives

**Interface-checked, 2026-11-10.** Existing `semantic/product_reference.py`,
`published_document.py`, `source_views.py`, `observations.py`, released
`model/semantic/observations.yaml`, `physical.yaml` and
`semantic/sql/native_task_completion.sql` supply the selected integration surfaces. Their
existing behavior is not claimed as TC implementation. PostgreSQL transactional statements and
indexed relations, SQLAlchemy typed set selections, generated model boundaries and the existing
protected task protocol compose the physical route. No new graph service, workflow runtime,
constraint solver or dependency is required for TC-01–02.

**Proposed.** Extend `physical.yaml` for actual stored layer/view and relationship projections;
derive ordinary bounded reads from the same model. Keep one canonical immutable payload and
native checks that normalized projections agree with it, rather than independently writable
payload and relation authorities. Native completion authenticates original source placement,
selected inputs, every endpoint and source reference, family scope, local IDs, term/choice closure
and claimed released support constraints before any read relies on them. It independently checks
source and declared premises; it does not rerun linguistic recognition or invent a second grammar.
Term-dependency cycles are invalid; cyclic discourse relations require an explicitly permitting
kind. Contradictory or unknown choice compatibility cannot produce a supported reading.

Prepare privately outside publication locks. Use existing task/run/attempt/holder fencing and
transactional completion for coherent visibility of canonical product, inventories and projections.
An actually failed task remains failed under the existing terminal-outcome correspondence.
A successfully published, structurally valid layer may record a failed/partial/unavailable family
under its actual status; that status does not invalidate useful independent siblings or establish
full-profile completion. Sealed products remain immutable; changed dependencies create new products.

| Alternative | Judgment |
| --- | --- |
| Add arbitrary analysis JSON to the current report and scan it at read time | Simplest initial write, but callers independently reconstruct operators/choices, a group query requires broad decoding, and native support cannot authenticate meaningful endpoints. Rejected for this target |
| Copy the complete document into each layer or keep one mutable latest document | Easy local navigation, but duplicates native custody and permits mixed revisions; repeated full-book copies buy no required capability. Rejected |
| Separate generic graph database/framework | Could express edges, but creates a second transactional/publication lifecycle and adapters without a current graph-analysis requirement. Rejected for this foundation |
| Immutable canonical products plus generated indexed relational projections | Selected: existing release, transaction, ACL, source and task owners remain authoritative; set retrieval and compact payloads serve both bounded inspection and complete export |

For ordinary inspection, select relevant inventory/membership in sets before hydrating native
items and semantic dependencies. Retrieve a cross-page group's complete recorded membership,
then distinguish visible fragments from outside-selection references. Bound examined relations,
hydration and response bytes separately; a return-row bound does not justify decoding a book.
Complete export streams source order and inventories using explicit continuation/dependency
references. It can deliberately traverse the whole selected closure once. The export is independent
of whole-run completion: it reproduces a settled view's actual scope and statuses, without claiming
that unfinished families are complete. Shared nodes are serialized by ID rather than recursively
expanding every alternative. These choices satisfy A4 qualitatively (H5/8/10/15/18/23/27); no
latency, memory ceiling or throughput improvement is measured here.

## Changes, failure cases and independent assessment

**Proposed.** A new negation/quantifier construction adds a typed term/role interpretation in
its semantic owner and creates a new layer; source occurrence identities and native capture remain
reusable. Another vocabulary supplies kinds and rule bindings through those operations, with no
statistics branch in generic storage/read code. A tokenizer/model/prompt revision invalidates its
inference layer; a pure construction change can reuse suitable retained native evidence under
complete dependency pins. A replacement provider supplies its actual scheme rather than relabelled
relations; unsupported mapping remains explicit. These are distinct domain and mechanism scenarios.

A source-only composed view is a real released production method over authentic existing document
pins. It truthfully advertises no attempted analysis families. It provides operational value and
exercises the actual composition route without pretending TC-03 producers exist. Independently
authored test-only layers may use an admitted test producer through protected native completion;
there is no ordinary user-upload route for arbitrary layers. Fixtures cannot qualify NLP quality.

TC-01–02 acceptance must independently specify repeated equal-text occurrences, cross-page and
overlapping groups, discontinuous roles, `not(all(...))` versus `all(not(...))`, disjunction versus
uncertainty, incompatible choices, dangling/mixed-source references and explicit unknown/empty
outcomes. Detached replay must match authored extents, memberships and choices, not just agree with
the encoding implementation. Stale attempt/cancellation and payload/projection tampering controls
challenge native protection. Shared production validators are appropriate for consumers; expected
semantic meaning must remain independently authored (CI-12). This review runs no product tests.

## Acceptance, findings and rule impacts

**Proposed judgments.** A1 satisfied: model/source/publication/read owners bound the selected
changes. A2 satisfied: source facts, attributed proposals, terms, choices and coverage govern
operations with explicit enforcement points. A3 satisfied: generated boundaries, protected
completion and set readers compose without a second lifecycle. A4 satisfied for the stated
single-host full-book and bounded-inspection scenarios through indexed selection, shared payloads,
factorized semantics and streaming export; high-degree groups retain explicit work limits.
FP-01–07 are satisfied for this proposed boundary, with DP-01–05/07–10/12–16/18–24 supported by
the ownership, lifecycle, alternatives and evidence limits above. No exception is requested.

| Gate | Judgment and basis |
| --- | --- |
| G1 | Satisfied: released semantic model and canonical products govern generated projections |
| G2 | Satisfied: typed coordinates, relation kinds, choices and coverage retain their meanings |
| G3 | Satisfied: constructor/release checks plus protected native source/closure/projection checks reject invalid products before visibility |
| G4 | Satisfied: private computation and effectful publication are explicit; readers do no analysis |
| G5 | Satisfied: existing attempt fencing, coherent transaction and immutable pins; limits/partial families are explicit |
| G6 | Satisfied: complete input dependencies, compatible choices and exact view closure govern reuse/readings |
| G7 | Satisfied: source-only delivery and planned linguistic producers have distinct claims |
| G8 | Satisfied: existing PostgreSQL/SQLAlchemy/model-generation capabilities cover generic responsibilities |
| CI-G1 | Satisfied: original schemes, attribution, unknowns and heuristic standing survive |
| CI-G2 | Satisfied: retained view and served references close over their exact source/layer pins |
| CI-G3 | Satisfied: independently authored expectations remain outside production inputs |

No new blocking finding or RC-numbered rule reversal is established. Private analysis publication
extends the accepted observation/contribution boundary; it does not reverse §B2 consolidation-only
knowledge writing, source custody or protected evaluation. TC-09's eventual language-policy
migration requires its own actual consumer/native reconciliation and is not authorized by this
review. ADR-0081 and D1/D2/D3/D4/D6/D8 record the accepted foundation. The TC coordinator owns
implementation state and any discovered conflict; a new actual rule conflict is escalated before
dependent behavior. An assembled review remains due for completed scope under the existing cadence.

Product/provider/database tests and benchmarks: **not_run** (static target review). Documentation
publication and ADR lint are separate checks reported by the coordinator. This review establishes
neither runtime qualification nor English completeness nor a measured benefit.
