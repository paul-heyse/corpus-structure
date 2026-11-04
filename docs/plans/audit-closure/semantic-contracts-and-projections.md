# Released semantic contracts and projections

**Completed selected AC scope; Tested2026-11-04.**
This companion develops AC01, AC02 and AC05 of the
[audit-closure coordinator](../audit-closure_2026-11-03.md). The coordinator alone owns package
status, execution queue and new-review-work disposition. Source DA findings keep their existing
disposition owner; the correspondence below supplies implementation routes, not copied status.

Current accepted source71a78774/native105 and complete selected functional/native/provider/
nonfunctional evidence are owned by coordinator §15. Original dated grounding and target detail
below are retained; they do not reopen completed AC work or qualify M1.

The operator accepted principal-review RC01–RC12 on 2026-11-03. No reapproval is needed.
ADR-0054 realizes the accepted changes at their architectural owners;
this document neither changes accepted ADRs nor applies the target to production.
M1 documentation is reconciled after the completion audit and targeted amendments; resumed execution retains AC prerequisites.

## Basis and focused foundation assessment

**Implemented source, inspected 2026-11-03 at `75db93e1`; assembled qualification open.**
The principal review at `fd4ea601` supplies the accepted target; its original source diagnoses
are historical inputs rather than a description of today's missing implementation. ADR-0054
realizes RC01–RC12 through D2/D5/D6/D7/D8. The coordinator owns the current audit conclusion.
Paths below are relative to `python/corpus-structure/src/corpus_structure/`.

`semantic/types.py`, `property_roles.py`, `statement_types.py` and `prepare.py` now carry released
source subsets, display/behavior roles and method dimensions into preparation, admission and
consumers. Semantic compiler16 and readers14–16 have distinct production/reading responsibilities.
The bound execution24 product owns operational `reference_splits`; a domain-only release uses
its explicitly declared vocabulary. An operational vocabulary need not be imported into the domain
namespace. `rule_views.py` supplies complete RuleValue ABI2 and shared source addressing;
operation-owned reasons reach actual reading/condition/comparison/preparation assessments.
Programming, infrastructure and native admission errors retain their failure meanings.

Retain the target and counterexamples below as acceptance requirements. Remaining work is to
account for their assembled native/provider/consumer applicability, including independently authored
subset overrides and stored-reason consumption; existing source integration is not work to rebuild.
[D2](../../design/D2-schema-and-guidelines.md) and
[D5](../../design/D5-consolidation-identity-confidence.md) remain architectural owners.

## AC01 — Effective subsets, roles, display policy and method dimensions

**Adopted refinement I01:** composed operational vocabularies come from the bound execution
product, not a same-named domain enum. Carry supplied-subset and domain-collision cases through
actual native/reference consumers. For AC05, inspect the stored assessment and consuming response,
not only reason types or serializer round trips. See the [targeted review](../../plan_improvement_reviews/audit-closure_2026-11-03.md#I01).


**Correspondence:** DA-002/003/012/040. This is completion of existing released semantic authority;
AC00 supplies any necessary current-owner/version routes, rather than requiring a new approval.

Declare a named source-admissible subset on Establishment members. It initially admits stated
and agent_asserted. Derived remains legitimate in the full occurrence/inference storage vocabulary.
Prepared source operations, generated AgentClaim and stored-report adapters, producer schemas and
guidance, SourceItem construction and native source publication consume that one subset. Refuse
source-derived assertions before report publication; retain assembly defense for direct callers,
derived from the same prepared product. Never narrow general storage to the source-only subset.

Likewise derive statement/evidence role membership from canonical released definitions or explicit
named contextual subsets. Declare the executable reference-set subset separately from the full
ReferenceSplit vocabulary: reserved remains representable metadata without becoming executable.
Native reference-set admission and authoring adapters lower the same selected subset.

Expose operations on existing prepared products, with names chosen locally where useful:

| Operation | Owned behavior and actual consumers |
|---|---|
| `source_establishments()` | Effective source-admissible members; source/report constructors, native lowering and producer guidance |
| `member_has_behavior(vocabulary_id, member, behavior_id)` | Released behavioral membership used by premise selection and symbol suppliers, without string classifiers |
| `display_properties(class_id)` | Ordered applicable display properties; query label matching, entity display and AC04 representative presentation |

Display policy declares property order, multivalued aliases and missing-label behavior. Initially,
select the first property in that order with an eligible value, then apply its declared value order
(stable value identity breaks an otherwise unresolved tie). Retain all eligible alias values for
matching; alias membership alone does not override a preferred display property. With no eligible
display value, return an explicitly marked assigned-ID fallback, never a fabricated source label.
Matching uses the declared case policy; returned display values remain exact. A differently named
display property must work by declaration. Selected property/value/source identity and alternatives
are available to AC04/AC10 consumers; changes to this policy use a new released binding.

Replace premise/example_value/formula/assumption literal classifiers with released memberships
such as supplies-binding-symbol and participates-as-premise. Current packs declare their existing
members' behavior. Adding another spelling for existing behavior changes declarations and derived
products; adding a genuinely new operation still needs an admitted implementation. Do not turn
every behavioral membership into a runtime stage, table or generic plugin.

For DA-012, inventory live semantic-runtime imports from `core.vocab` (including rule views,
scientific evidence, native requests/analysis and operation admission). Move only dimensions
whose semantics belong to the current method/release contract. Each method binding declares
admitted families/outcomes/confidence provenance as appropriate. Operation outcome, observation
outcome and confidence-source stay distinct. Extend existing result-dimension adapters and native
products; validate before publication. Unrelated legacy consumers may keep their own vocabulary.

**Delivery and retirement:** change semantic declarations, prepare/boundary products, generated
Pydantic/JSON Schema, native guards and actual producer/reader consumers together. Retire displaced
authored lists and active runtime constants/imports only after those consumers migrate. AC13 owns
coordinated release/forward installation; its dependency is the changed product and enforceable
guard, not completion of every package in this companion.

**Acceptance:** independently specify an extended role/display member and its expected behavior;
exercise generated schema and real native refusal for source-derived and reserved split inputs,
while legitimate inference-derived storage succeeds. Verify a renamed display property, ordered
aliases and missing label. Check method-specific dimensions refuse wrong families before effects.
Pure membership/projection cases need no database; native untrusted writes need real PostgreSQL.

## AC02 — Complete rule-value ABI and shared source addresses

**Correspondence:** DA-005. RC02 is accepted, 2026-11-03. AC00 routes the D5 §8 ABI change
through its owning decision/section before activation; archived v1 products retain their meaning.

One operation, conceptually
`project_rule_value(prepared, declared_binding, validated_value, optional_reading)`, owns the
translation of claim-root values and nested qualification/parameter-map values. It receives the
effective property or value binding, rather than trying to recover a declared range from a
runtime discriminator. Its versioned RuleValue retains value_kind, declared_range, enum_id,
expression_form, lexical/expression content, reading and defined_symbol where applicable.
Missing, unsupported and failed-reading meaning remain distinguishable; allowed omissions are
declared. A rule requiring unavailable view meaning is refused, never supplied a false default.

An expression value with formula form retains mathematical/symbol meaning even though its
value discriminator says expression. Entity values, enum-valued qualifiers and nested parameter
entries follow the same owner. Both `_value_projection` and candidate-view construction consume
this operation; remove their competing interpretations. Preserve occurrence identity in rule
views separately from canonical fact identity and keep the complete declared rule universe.

Version the archived view schema, rule compiler and dependent authored rules together. Admission
chooses a supported ABI explicitly and refuses incompatible callers/releases. Do not read old
archives under new defaults or add a universal old-runtime compatibility promise. AC13 packages
the resulting artifact/compiler identity and native changes; exact migration names remain execution
choices now bound by frozen102 and the coordinator’s current source/compatibility account.

The selected mechanism remains rule-engine **5.1.0** `DataType.OBJECT(name, attributes, accessor)`,
`OBJECT.reference`, `ARRAY`, `MAPPING` and `NULLABLE`, plus existing Language/Context/compiled Rule.
Keep cached Pydantic **2.14.1** strict `TypeAdapter` validation on accessor returns: an OBJECT
declaration alone does not validate the actual accessor value. Prepare schemas/adapters once per
release and bind values per evaluation; do not compile on every primitive access. Relevant current
seams are `rule_views.py:207–231,339–405`. LinkML Runtime **1.12.1**
`SchemaView.class_induced_slots` supplies contextual induction; `induced_enum` does not expand all
dynamic/inherited membership, and `in_subset` metadata needs deliberate compiler lowering.

Producer and evaluator ordinary `claims/N` addressing move to the existing source-address owner
used at `domain_operations.py:1499` and `evaluate/semantic.py:694`. Share the mechanical encoder,
not expected scientific answers. Preserve M1 record evaluation's distinct source-address ABI and
qualified native addresses; this is not authorization to normalize them into claim-list addresses.

**Acceptance:** independently author expected enum/range/expression projections, including nested
parameter maps, defined-symbol cases, missing/unsupported/failed readings and invalid accessor
returns. An incompatible archived ABI refuses. Producer/evaluator address agreement is checked
against independently specified addresses; scientific expectations remain evaluator-owned.
This package needs AC01's effective binding/subset slice where consumed, not all role migrations.

## AC05 — Operation-owned semantic reasons

**Correspondence:** DA-013. Extend `semantic/refusals.py`, existing validation/operation reporting
and actual semantic operation owners. Retain FailureContext, invariant identity, native cause,
phase/effects and separation of programming failures from expected domain outcomes.

Represent the distinctions used by real consumers as operation-owned variants: missing operands,
unsupported interpretation, incompatible bindings and failed preparation. Each carries a stable
code plus trusted operation/release identity, affected references and expected/actual/detail where
useful. A scientific outcome may remain undecided while its cause remains typed. Human messages
are rendered from those fields; CLI/MCP/policy routing never parses `str(exc)`.

Migrate rule preparation, projection and scientific comparison paths together with CLI failure
rendering, `tool_refusals` and routing consumers. At expected library boundaries, translate only
known semantic exceptions into the owned reason. Unexpected ValueError/TypeError/programming
failures must propagate through failure reporting rather than become successful undecided output.
Native database/invariant diagnostics keep their own cause and effects; semantic reasons reference
them when needed rather than flattening the two contracts into a universal error taxonomy.

AC05 can establish the reason shape early; AC01/02/03/04/09 use it as their operations migrate.
Agreement on fields enables consumer implementation, while usable failure integration requires
the actual producers and renderers. No whole-document barrier is needed. If persisted result
shapes change, AC13 supplies the release/native product version and forward transition.

**Acceptance:** distinguish missing, unsupported, incompatible and preparation-failed cases through
CLI and MCP fields; verify stable reason identity despite changed human wording. Inject an
unexpected programming ValueError to establish it is failed, not an undecided scientific success.
Check native failure context survives and no credential/SQL payload is exposed by rendering.

## Composition, alternatives and completion evidence

The workload is repeated evaluation and reading over pinned releases/cuts with growing candidates.
Prepared membership and cached typed accessors remove repeated interpretation without adding a
second cache lifecycle. Specialized domain operations retain their meaning; stable compiled
products carry mechanical projections. Benefits are Proposed, with no latency or capacity claim.

The retained alternative of literal lists and v1-only restrictions would require explicit support
limits and still leave the selected new meanings unavailable. Wholesale attrs/msgspec migration,
a new evaluator, generic recursive mapping engine and another catalogue do not resolve these gaps
with less integration. LinkML-map remains a candidate for substantial cross-model authored maps;
it is not selected for this specialized mathematical/contextual translation.

Library API details above carry the review's **Interface-checked** evidence, not fresh runtime
qualification. Precise sources: [LinkML contextual induction](https://linkml.io/linkml/developers/schemaview.html),
[subsets](https://linkml.io/linkml/schemas/subsets.html),
[rule-engine OBJECT attributes](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/attributes.rst),
[custom accessors](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/types.rst),
[Pydantic 2.14.1 strict validation](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/strict_mode.md)
and [unions](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/unions.md).
The review inspected installed sources for version-specific seams; unpinned master links are
orientation and do not authorize assuming a later interface. No dependency change is selected.

RC12's accepted D2 present-tense guidance correction is scheduled through AC00/AC13: reconcile
compiler6/7/12 and compatibility descriptions against final executable/compiler/reader owners,
label historical material, retain honest Proposed targets and remove competing present-tense
definitions. Do not add a second mutable compiler-version list. DA-004/027 retain the review's
governed mappings and targeted invariant checks; no universal typed-object or proof-registry work.
The [consolidation companion](consolidation-and-inference.md) carries their reopening limits.

AC10 consumes display/standing semantics; AC11 consumes structured reasons and pinned evidence
identities; AC13 integrates changed releases/generated/native products. AC14 owns assembled
qualification after complete series scope. During implementation use relevant compile checks and
focused independent cases; do not run integrated gates after slices. Preserve native99, frozen
migrations and historical failed/interrupted evidence. Plan-authoring product tests, providers,
database operations and runtime qualification: **not_run**; no product edits are authorized here.
