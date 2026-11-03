# Released semantic contracts, identity and attribution

**Proposed, 2026-11-03.** Fresh semantic-reviewer contribution to the
[principal review](../design_review_audit-closure-target_2026-11-03.md).
Consumes audit90ed25c4, source90ed25c4 plus identified dirty M1. Source and interfaces inspected;
no tests, database operations, probes or product qualification. Paths omit
python/corpus-structure/src/corpus_structure unless prefixed docs/ or domains/.

## Author context-specific membership and behavior once — DA-002/003/012/040

Extend existing effective bindings, resolved vocabulary and property-role products. Reuse
PreparedRelease.enum_members(name, subset=...) (semantic/types.py:279–306), property_roles
(property_roles.py:13–35) and effective statement/reference bindings (statement_types.py:54–100).
No second catalogue or registry is needed.

The full Establishment vocabulary legitimately includes derived for inference/storage, while
source assertion admits stated/agent_asserted. Author that source-admissible subset once on released
members. Derive AgentClaim producer/stored-report boundaries, SourceItem construction, native
source publication checks, guidance and exported schema from it. Reject unsupported source
establishment before report publication; keep assembly defense from the same prepared subset for
direct callers. Do not narrow the broader occurrence/inference storage constraint to a source-only
subset. Current late refusal is consolidation.py:242–246; AgentClaim currently admits the full enum.

Similarly derive agent statement/evidence role membership from canonical released definitions or
explicit named subsets. ReferenceSplit.reserved need not become executable: declare the actual
reference-set subset once and derive authoring/native restrictions. Remove competing authored
lists after consumers move. Enforcement at two trust boundaries is not two semantic authorities.

Expose conceptual semantic operations display_properties(class_id) returning ordered applicable
properties, member_has_behavior(vocabulary_id,member,behavior_id), and source_establishments().
They belong to existing prepared products. Label lookup must consume the class-bound display
policy instead of names label/aliases/name/canonical_name (serve/read.py:151–158). Specify order,
multivalued aliases and missing-label behavior; display values stay exact, while matching follows
its declared case policy. Property membership alone is insufficient to decide one preferred label.

Replace premise/example/formula/assumption literals (domain_operations.py:3020–3026,3260) with
released behavioral memberships such as supplies-binding-symbol and participates-as-premise.
Pack declarations bind current members. A new spelling of existing behavior needs no new consumer
classifier; genuinely new behavior needs an admitted implementation, not a magical annotation.

For DA-012 move active semantic-runtime observation/result dimensions off older core.vocab imports
onto their corresponding method/release contracts. Each method binding declares admitted families,
outcomes and confidence provenance as appropriate; not every provider string needs one global
enum. Extend existing validate_result_dimension/compiled adapters (operation_results.py:25–87)
to validate before publication and derive native dimensions. Operation outcome, observation outcome
and confidence-source remain distinct. Remove displaced constants/imports only after live consumers
migrate; do not delete unrelated older model consumers.

## Complete rule-value projection — DA-005

Keep the archived rule-view schema and strict public accessor boundary. One domain operation
project_rule_value(prepared, declared_property_or_value_binding, validated_value, optional_reading)
serves both root claim values and nested qualification/parameter-map values. Its versioned RuleValue
must distinguish value_kind, declared_range, enum_id, expression_form, lexical/expression content,
reading and defined_symbol where applicable. Resolve each through the effective release; preserve
unsupported, missing and failed-reading distinctions rather than one indistinguishable null.

Current rule_views.py:189–204 sets enum=None and slot_kind=value kind; :129–131 recognizes only
formula, although ExpressionValue uses expression. domain_operations.py:3194 builds a second view.
Replace these projections with one owner; expression carrying formula form must not lose symbol
meaning simply because the discriminator differs. State allowed omissions and reject rules that
require unavailable view meaning. Version the rule-view ABI, compiler and dependent rules together;
never silently reinterpret an old archived ABI under new defaults.

Producer/evaluator claims/N address construction should also use the existing source-address owner
(domain_operations.py:1499; evaluate/semantic.py:694–696). Sharing that mechanical encoder does not
justify sharing expected scientific answers. Preserve M1 record evaluation's distinct address ABI.

**Selected realization:** retain rule-engine5.1.0 DataType.OBJECT(name,attributes,accessor), OBJECT.reference,
ARRAY/MAPPING/NULLABLE and existing Language/Context/compiled Rule. Keep cached Pydantic2.14.1
TypeAdapter checks on accessor returns: OBJECT declaration alone does not prove runtime values.
Prepare schemas/adapters once per release, bind values per evaluation, never compile per primitive
access. Existing rule_views.py:207–231,339–405 already establishes these seams.

LinkML-map remains a candidate for substantial authored cross-model mapping; it is not selected
for this specialized mathematical/contextual view because less machinery or full semantic fit was
not established. No replacement evaluator, recursive visitor or generic transformation engine.

## Make resolution outcomes explicit — DA-007/009

Retain safe source-qualified fallback and refusal to merge ambiguous anchored labels
(domain_operations.py:923–953,1037–1042). Return the local-to-assigned mapping with typed per-entity
decisions: source/local identity, assigned identity, basis (declared_key/global_label/source_local),
outcome (resolved/ambiguous_anchor/incomplete_key/ungrounded_cycle), candidate identities,
key/label policy, dependency references and reason code as relevant. Source-local can be a legitimate
policy, not an error. A usable fallback must not claim globally resolved identity.

Store compact decisions with the cut's coherent projection, not duplicated full evidence payloads
or an event stream. Stable-local-reference consumers use assigned IDs; global grouping and
explanation consume outcomes. Preserve local versus known endpoint distinctions at the resolution
boundary rather than infer them from dictionary lookup success. Keep centralized compiled-position
reference traversal, collision checks and revalidation after actual mutation.

DA-009 has no demonstrated divergence. Define the recipe as Unicode default case folding for
properties selecting it, without an implicit normalization step. Bind effective Unicode/runtime/
collation compatibility to producing/admitting determinants; SQL currently selects pg_unicode_fast.
Qualify supported Python/PostgreSQL combinations and refuse unqualified ones rather than substitute
lowercase. Compare relevant folding mappings and independent identity cases at runtime changes;
a few examples do not prove universal parity. Retain independent native recomputation for its trust
boundary. No bespoke Unicode engine or per-fact parity checking is justified now.

## Separate attribute support and representative policy — DA-044

AgentAttribute currently has only predicate/value (model/semantic/agent.yaml:9–12), while projector
uses the first eligible claim's support and asserted/positive qualifiers
(domain_operations.py:1507–1512,1580–1589,1618–1620). Replace that implicit attribution with a released
SourceAttributeAssertion carrying predicate, value, qualification, source-admissible establishment
and located evidence. A reference to another assertion is acceptable only if its explicit contract
establishes this attribute, not merely the same entity. Preserve multiple supports/qualifications.

AgentEntity.label stays display metadata unless supplied as a supported assertion. Generated IDs
are structural assignments with operation/input lineage, not document-stated source occurrences.
Migrate producer/guideline/native shapes together. Unsupported older attributes remain metadata
or explicitly ungrounded; never silently promote them to satisfy graph shape. Attributed entity
declarations can still exist without accepted scientific claim evidence.

Three representative choices have different policies:

| Choice | Selected target |
|---|---|
| Storage form of one exact semantic fact | Declared total order on representation IDs; no source-quality/scientific preference claim |
| Display label/value | Class-bound ordered display policy with selected source/value identity and alternatives |
| Representative of scientifically equivalent accepted facts | Released deterministic view policy over eligible accepted members; stable fact-ID tie break, retained component membership/comparison evidence |

A simple minimum stable fact identity is an acceptable initial scientific-view policy if no
quality preference is required. Its value is explicit permutation-stable meaning, not superior
science. Do not relabel other equivalent accepted members as rejected or change exact fact identity.
Retain occurrence reports and qualified support (consolidation.py:258–260; serve/read.py:82–92),
while consumers needing proposition sets avoid duplicate counting.

## Structured semantic reasons — DA-013

Retain FailureContext, native cause/phase/effects, invariant identity and programming-failure
separation. Operation-owned reason variants carry code, operation/release, affected references and
expected/actual/detail where useful. Missing operands, unsupported interpretation, incompatible
bindings and failed preparation remain distinguishable while scientific outcome can stay undecided.
CLI/MCP/routing consume fields, never parse str(exc). Unknown programming exceptions must not
become successful undecided merely because they inherit ValueError. No universal taxonomy without
actual consumers is required.

## Retained design and authority guidance — DA-004/011/027/046/048

DA-004: typed validation followed by mutable/serializable mappings is legitimate; no semantic loss
or unchanged-premise repeated work was established. reference_positions.py:168–221 validates typed
structure, uses compiled positions and revalidates after mutation. Reopen only a concrete operation;
do not force typed objects everywhere.

DA-027: keep existing declarations, compiler diagnostics and native guard enforcement. Inspect/test
the invariants a correction changes. Unexamined exhaustive correspondence is not a defect or a
requirement for a proof registry/universal SHACL pass.

DA-046/048: retain reusable mathematical types and single canonical-domain operational selection.
Move actual pack-specific behavioral memberships under DA-003. Equal-policy coalescing and conflict
refusal (regeneration.py:189–297) are strengths; multi-pack preparation is not simultaneous multi-pack
production support. A real consumer requiring that capability reopens its whole contract.

DA-011: rewrite current D2 guidance against the final accepted executable/compiler/reader owners;
remove competing present-tense compiler6/7/12 descriptions without introducing another mutable
prose version list. Preserve honest Proposed targets; history is Git or explicitly historical text.

## Library evidence and closure

Context7 resolution preceded queries; installed LinkML Runtime1.12.1 and current repository adapters
were inspected. Existing SchemaView.class_induced_slots performs contextual induction; induced_enum
only copies a definition and must not be assumed to expand all dynamic/inherited values. in_subset
is metadata: the repository compiler must deliberately lower its chosen restriction. Reuse current
resolved vocabulary rather than another YAML traversal. Pydantic create_model/discriminated unions
and cached strict TypeAdapter remain selected. No new dependency is proposed.

- [LinkML SchemaView](https://linkml.io/linkml/developers/schemaview.html) and [subsets](https://linkml.io/linkml/schemas/subsets.html); guides: ../../../libraries/data_model/linkml.md §§8.1/9.3/12.4 and linkml_extension_libraries.md §§2/5–6.
- [rule-engine OBJECT attributes](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/attributes.rst) and [custom accessors](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/types.rst); guide rule-engine.md includes5.1.0-specific boundaries.
- [Pydantic2.14.1 strict validation](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/strict_mode.md) and [union/TypeAdapter contracts](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/unions.md).
- [Python3.14 casefold](https://docs.python.org/3.14/library/stdtypes.html#str.casefold) and [PostgreSQL18 string functions](https://www.postgresql.org/docs/18/functions-string.html) support mechanisms, not complete cross-runtime parity proof.

These mechanisms are **Interface-checked**; the target remains **Proposed**. Alternatives rejected:
wholesale attrs/msgspec migration, new rule evaluator, second schema catalogue and global invariant
engine. They do not resolve the specific missing meaning with less total integration.

Future closure cases: a differently named display property; alternate premise member; one changed
source subset reaching generated/native consumers; reserved reference split refusal; early source
derived refusal with legitimate inference-derived acceptance; enum/expression/nested RuleValue;
missing/unsupported states; ambiguous anchored identities/incomplete keys/cycles/local-known/cannot-link;
non-ASCII folding compatibility; reordered claims with independent attribute support; exact facts
versus equivalence component/view representative; method-specific dimensions; structured reasons and
programming failures. Expected meaning must be independently authored, not the same projection
called twice. Pure projection tests should not need a database; native untrusted-write controls
retain real database enforcement obligations. None was run for this review.
