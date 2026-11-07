# Witnesses, definitions and actual-mention composition

> Execution reading route,2026-11-06: The baseline table below describes the pre-WCE source. Current named recipes use M1v8 and retained-annotation-rules-2; token-only authoring and unnamed-only adaptation have been retired. WCE04 consumes these named products.

**Accepted target; selected implementation Tested · 2026-11-06.** This companion develops WCE03–WCE05.
The [WCE coordinator](../witnessed-corpus-enrichment_2026-11-05.md) owns all package state,
finding disposition, rule decisions, evidence and completion. This document owns the bounded
design explanation; selected realized behavior and its evidence limits are described at the end.
Target requirements alone do not establish verification or corpus-wide benefits.

> Current GS120 execution checkpoint — **Implemented; bounded Tested, 2026-11-06**:
> `structure.definition_components/5` retains 35 named components in run160 and 44
> model components in run161 over the same 48 original source views / 120 pages.
> [Final model delivery](../../design_review/evidence/2026-11-06_wce-gs120/current-model-delivery/delivery-index.json)
> preserves all 97 accepted raw task bodies, source context and partial/zero-output
> operation states; transport does not establish semantic correctness or recall.
> [Actual term/contextual delivery](../../design_review/evidence/2026-11-06_wce-gs120/current-contextual-journey/contextual001/summary.json)
> projects the 14 declared definitions into 14 private `defined-by` edges, with all
> witness support still unassessed. The 21 explanations and 38 views without eligible
> emitted definitions remain visible in their own inventory. This is coupled
> term-to-own-component construction, not independent usage-applicability evidence.
> Canonical current registrations and shared consumer ports are integrated at
> `66feb47ab`; the coordinator owns qualification and benefit conclusions. The earlier
> selected realization below retains its original evidence scope, including method4.

The input is the integrated [production-enrichment review](../../design_review/reviews/design_review_production-enrichment-improvements_2026-11-05.md),
consumed at `6487c486` (542 lines), especially §§2–4.2, 7–12 and F01–F03. The
[recommendation-audit companion](../../design_review/reviews/audits/design_review_production-enrichment-improvements_2026-11-05_audit.md)
explains the revision; it is not another target or progress ledger. RC01–RC06 were explicitly
accepted for planning by the operator on 2026-11-05. WCE00 records and routes those changes
before dependent implementation. The separate test-audit resolution plan is assumed ready as
a target foundation; neither its repairs nor its actual qualification are claimed here.

## Purpose and boundary

The useful result is a located, inspectable definition or relationship whose successful parts
survive an unresolved larger reading. A target may define arithmetic mean while the usage's
sense remains uncertain. A passage may define X, explain Y and merely mention Z. Each decision
therefore binds particular occurrences and roles, rather than assigning one meaning to a whole
passage. The producer emits attributable private products. Independently supported components
may reach their own narrow admission policies; component support never authorizes a complete
definition-applicability statement.

WCE03 prepares named linguistic candidates; WCE04 constructs definition components and separate
usage-applicability judgments; WCE05 composes actual mentions with contextual retrieval and
domain-constraint relationship selection. [Typed composition and dossiers](typed-relations-comparison-and-dossiers.md)
consume their qualified products. WCE08 consumes real ambiguous attachments, without making
candidate-relative probabilities a new source of authority. WCE11 assembles journeys after
each package has migrated its actual consumers; it is not a place to postpone those migrations.

## Current foundation and focused assessment

Source inspection at `6487c486`, 2026-11-05, establishes the following implemented baseline.
Its historical execution receipts retain their original scope and dates.

| Existing owner | Observed boundary | Planned use and necessary correction |
|---|---|---|
| [PreparedAnnotationRules](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) | Matcher, PhraseMatcher and DependencyMatcher compile once; matches retain nodes, source extents, pieces and annotation digest; complete DEP is required. | Reuse preparation and retained annotations. Add variant identity and semantic role mapping rather than infer names from extents. |
| [M1 source producer](../../../python/corpus-structure/src/corpus_structure/methods/m1_source.py) | `M1Config.annotation_token_rules` is the only configured rule family; the caller prepares only token rules. | Wire versioned phrase/dependency configuration and declared bindings through this existing producer. |
| [Contribution adapter](../../../python/corpus-structure/src/corpus_structure/methods/contribution_adapter.py) | `adapt_annotation_matches` emits located `source_rule.*` proposals; dependency extents remain noncontiguous. | Extend this lowering to named roles and attachment proposals while preserving raw match provenance. |
| [Definition producer](../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py) | `pair_input` and `decode_applicability` classify a fixed usage/passage pair, returning a category, passage evidence and generic reason. | Replace the pair-only classifier and its production/control bridge with located target components and separately qualified applicability; literal controls use current contracts. |
| [Contextual candidates](../../../python/corpus-structure/src/corpus_structure/methods/contextual_candidates.py) | `SuppliedMention` isolates retrieval. `denotation_contribution` takes `alternatives[0]` after singleton selection. | Compose actual located contributions; migrate to authenticated actual occurrences and retire the supplied-input production bridge. |
| [Contextual links](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py) and [storage](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_storage.py) | `source-supported-scoped-links-1` accepts explicit-source-cue witnesses; more than one distinct target/relation is ambiguous. Storage reconstructs that exact policy. | Add a versioned compatibility/selection meaning and reconstruct it through its own policy; retire historical singleton decoding after the current-only data cutover. |
| [Structural products](../../../python/corpus-structure/src/corpus_structure/semantic/structural_products.py), [admission](../../../python/corpus-structure/src/corpus_structure/semantic/structural_admission.py) | Finite private reports have exact original source closure; existing policies assess complete structural statements. | Reuse common native lifecycle, source binding and atomic publication. New independently admitted components need their own exact question and eligibility contract. |

The architectural owners are [D1](../../design/D1-knowledge-representation.md),
[D5](../../design/D5-consolidation-identity-confidence.md) and
[D8](../../design/D8-agent-and-query-interfaces.md), with
[ADR-0062](../../adr/0062-progressive-contributions.md),
[ADR-0064](../../adr/0064-local-semantic-admission.md) and
[ADR-0065](../../adr/0065-cross-source-structural-products.md).
WCE00/WCE01 own prospective authority changes; accepted ADRs and frozen result bytes are not
edited in place.

**Proposed foundation judgment.** The existing release, contributions, source contexts and
native custody provide an adequate integration home. The missing semantic decisions are role
binding, attachment, applicability and compatibility, not another scheduler or witness store.
FP-01/03/04 favor domain functions behind these meanings and one adapter to their physical
products. FP-02/05 and CI-02/03 require distinguishing compatible selected edges from mutually
exclusive alternatives, including in storage reconstruction. FP-06 favors local retained-view
checks before database/provider journeys. FP-07/A4 favor preparing matchers once, sharing a
bounded annotation view, deduplicating physical occurrences and batching native validation.

Keeping the old classifier alone is a cheap control but cannot locate which component is wrong.
Demanding complete applicability before retaining any definition would discard useful structure.
A general witness/workflow framework adds independent lifecycle machinery without a present
consumer. Those alternatives are not selected. This assessment is focused plan authoring,
not a fresh audit, subsystem certification or a measured performance claim.

## Shared contracts consumed here

The [semantic/native companion](semantic-contracts-publication-and-consumers.md) owns WCE00/WCE01/WCE11.
The [source/assessment companion](assessment-source-expansion-and-qualification.md) owns WCE02/WCE12.
Its early source/question/rubric slice precedes producer development; later output-first freezing
follows actual products. Producers do not depend on labels for future outputs.

WCE01 supplies executable released definitions, preparation/native lowerings and reader versioning
for the distinctions below. WCE02 supplies frozen original-source opportunities and independent
operation-specific questions, with exposure and group boundaries. An agreed schema alone does
not establish either prerequisite's implemented readiness.

| Required meaning | Producer obligation | Consumer obligation |
|---|---|---|
| Source occurrence | Preserve original project/run/cut/release/result revision, source view/native product, content/projection/recipe digests, coordinate version, exact pieces and lexical text. | Resolve through original custody; normalized offsets or a copied source do not replace physical identity. |
| Located role | Bind released role identifier to token head and declared expansion, retaining rule/variant, annotation/provider and source dependencies. | Separate correct location from correct role; syntax is a proposal basis. |
| Attachment | Name participants, kind/direction, source basis, scope/version and operation identity; retain unresolved alternatives. | Do not infer attachment from proximity, shared strings or a generic passage rationale. |
| Definition component | Bind term/expression to defining content with witnessed attachment; track component support separately from usage applicability. | May inspect or independently admit only the exact component claim its policy supports. |
| Relationship selection | Preserve domain relationship constraints, compatibility policy/version, candidate inventory/list, exclusions, selected edges and unresolved groups. | Do not flatten several compatible edges into one alternative or choose the first edge as denotation. |
| Operation coverage | Retain selected/inspected opportunity population and failed, empty, limited, unavailable or uninspected execution as distinct meanings. | Emission count and filtered candidates do not define source opportunity or absence. |

These are required semantics, not a demand for a class, table or transaction per row. Use typed,
versioned variants in existing SourceContribution/Structural products, with no parallel store.
Private production, independent assessment and public admission remain separate immutable
relations; no standing flag is overwritten to simulate promotion. Existing envelopes may carry
batched components. New meanings get
new operation/schema versions; reuse binds all relevant dependencies, including negative
premises and inventory membership. Producing semantic/runtime pins remain separate and exact.

## WCE03 — Native candidate collections and named bindings

**Contribution:** F02, with F01/F03 prerequisites. **Consumes:** implemented WCE01 located-role
and configuration contracts plus the WCE02 source-opportunity slice. **Delivers:** an executable
retained-annotation-to-named-candidate route, available to definition and actual-mention consumers.

### Behavior and implementation boundary

Extend `M1Config`, its effective configuration identity and `PreparedAnnotationRules` to accept
token, phrase and dependency rules with versioned authored role bindings. Each dependency pattern
variant receives a unique internal match ID. Maintain a prepared mapping from that ID to authored
rule, variant, ordered `RIGHT_ID` names and semantic bindings. On a result `(match_id, token_ids)`,
zip against that variant's ordered nodes, never the first pattern under an authored rule and never
surface-sorted tokens. Validate bound names exist and referenced attributes are available during
preparation. Two variants may express the same semantic construction while having different node
order and lexical realization.

For each role retain the matched head, bounded expansion rule, resulting source pieces and extent
status. The selected initial expansion vocabulary covers exact matched token/span, sentence-bounded
subtree and explicitly enumerated conjunct attachments. Stop at declared condition/exception or
scope boundaries. Do not fill gaps by making a noncontiguous dependency role one continuous quote.
An overlong, ambiguous or incomplete expansion yields an explicit partial/unresolved role rather
than an invented maximal phrase. Local `Token.subtree`, `conjuncts`, `ancestors`, `Span.root` and
span/sentence LCA queries may implement these policies; whole-document ancestry matrices are not
needed for these bounded questions.

Reconstruct `AnnotationView` with the same caller-owned vocabulary and retained annotation columns.
The current complete-DEP refusal remains for dependency matching. Token/phrase work whose own
requirements are available may still complete, with failed/unavailable dependency work visible.
Do not rerun tokenization or a statistical parser to hide missing retained annotations. Any future
annotation acquisition is a separately declared operation with its own provenance.

Use named overlapping `Doc.spans` groups as transient contiguous candidate collections. Select
`SpanRuler` with `spans_filter=None`, `annotate_ents=False` and explicit `spans_key`/`overwrite`.
Raw and reconciled groups have different keys; raw candidates survive reconciliation. A useful
binding can choose fresh-group replacement or explicit accumulation, but its configuration must
state which: factory-created SpanRuler defaults to overwrite while its direct constructor does not.
Keep noncontiguous roles in the existing located products. `Doc.ents` cannot represent the complete
overlapping universe. A side mapping in the existing component provenance binds each raw candidate
to every generating rule/variant/provider; identical span boundaries do not erase independent bases.

Select the native optional classifier seam now: `spacy.preset_spans_suggester.v1` reads the retained
raw group, while SpanCategorizer writes a separate output key. Its learned activation requires
suitable independent labels and explicit training provenance. `set_candidates` can inspect the
suggested population when diagnosing candidate loss. Do not enumerate every n-gram merely to feed
a classifier or allow its output assignment to overwrite the raw group. Missing/outside/blocked NER
annotations and `incorrect_spans_key` retain their component-specific training meanings; they do
not become universal semantic states. Unalignable source opportunities survive assessment.

Extend `adapt_annotation_matches` once to lower authored named roles, exact match/expansion evidence
and candidate identity into existing contribution custody. Remove independently interpreted role
dictionaries and unnamed-only production adaptation after all replacement consumers work. Keep
raw matches as evidence and supported current result readers; remove replaced historical decoders. Wire initial defining/calling, local-symbol declaration
and condition/exception constructions; use active/passive actor/action/obligation and coordination
cases to expose role-order assumptions without expanding into a general enterprise parser.

### Library realization and conditions

| Selection | Precise mechanism and source | Maturity and boundary |
|---|---|---|
| spaCy `==3.8.18`; installed `en_core_web_sm` artifact `3.8.0` when that annotation recipe is used | Existing `Matcher(validate=True)`, `PhraseMatcher(attr="LOWER", validate=True)`, `DependencyMatcher(validate=True)` over retained `Doc`; [DependencyMatcher API](https://spacy.io/api/dependencymatcher). | Matcher and per-variant named output are implemented and focused Tested within the selected current recipe. Model artifact, recipe and retained-column revision remain pinned; no model execution follows from constructing a Doc. |
| Raw overlapping candidate groups | [SpanRuler API](https://spacy.io/api/spanruler); installed `spacy/pipeline/factories.py:263–275` and `span_ruler.py:128–139` settle explicit configuration and constructor/factory default difference. | Interface-checked source, 2026-11-05; no new efficacy test. The attempted upstream `v3.8.18` source URL did not resolve, so installed exact-version source is the version-specific reference. |
| Conditional learned classification over retained candidates | [SpanCategorizer API](https://spacy.io/api/spancategorizer), installed `spacy/pipeline/spancat.py` preset suggester and output assignment. | Composition seam selected; fitting/activation conditional. The classifier cannot recover absent raw candidates. |

The [spaCy guide addendum §§2–5](../../libraries/parsing/spacy.md) provides capability orientation
and partial-annotation caveats. It was an operator-owned dirty input, read without modification.
Context7 `/explosion/spacy` confirmed pattern-node-order and overlapping-group contracts on
2026-11-05; current documentation is orientation, exact installed source governs pinned details.

### Integration and discriminating verification

Deliver producer configuration → retained view → match → named role → contribution → ordinary
inspection/export as one usable path. Update release preparation, identity/reuse determinants,
native source validation, result decoders and affected Reader/CLI/MCP projections with the
new representation. Consumers must see role names, variant and partial expansion without
reconstructing them from token order. Authentic old raw matches remain evidence; current production reads only the current named-match contract, with no historical decoder.

Use independent literal role/source expectations for two variants with different node order,
passive reversal, nested/coordinated expressions, overlapping candidates and noncontiguous pieces.
Exercise complete versus missing DEP, normalized text whose length differs from source and
unalignable source spans. Confirm reconciliation and optional classification preserve the raw
population/provenance, and that an unsupported role does not acquire semantic standing from a
matcher score. These focused functional checks precede any fresh efficacy comparison; original
provider outputs and failed attempts remain controls/evidence. Full union qualification is WCE12.

## WCE04 — Witnessed definitions and separate applicability

**Contribution:** F01 and F02 integration. **Consumes:** WCE03 named candidates, WCE01 component
and native-policy contract, WCE02 fixed and fresh reference questions. **Delivers:** automatic
target-local definition components and independently scoped usage-applicability decisions, including
their native/read consumers.

### Definition behavior

For each selected target passage/window, propose the defined term or expression, defining
text/formula/structural element, attachment basis and scoped meaning. A matched cue, layout/geometry
group, model reading and admitted derivation are distinct bases. A match such as “we call Y X”
binds term X to expression Y even when surface order reverses the more familiar “X is defined as Y”.
“X is useful” and “X is discussed below” are counterexamples; a copula or mention alone supplies
neither definition nor attachment. If no selected cue matches, record no such proposal under that
operation's coverage; do not assert the passage has no definition.

Keep target term location, content location, role, attachment and scope support separately
assessable. A correctly located term with wrong role keeps its location success. An ambiguous
attachment retains its alternatives. Build usage applicability only from a particular usage
occurrence and proposed sense/binding plus a particular target component. Compare scope, parent
concept, parameterization, convention and effective version where material. Distinguish applicable
definition, explanation, example, mention, incompatibility and unresolved support in the released
operation; do not reinterpret the historical six-way pair result silently.

Use the existing fixed inventory, lexical/dense channels and immutable target-vector reuse to
nominate targets. Similarity does not supply definition support. Stage retrieval, target extraction,
attachment and usage compatibility so a failed later stage retains successful earlier products.
An encoder/model failure is not semantic abstention. Bounded windows, cancellation and actual
stage outcomes remain in immutable result details. Capture source closure in a short read before
CPU/model work; recheck changed premises at common native completion/publication.

### Complementary GLiNER realization

Select target-local located entity/expression and role extraction as a complementary producer,
using the existing `GlinerPack`/`GlinerProfile`/`GlinerWorker` route and contribution adapter.
The direct dependency is `gliner2[local]==2.1.0`; GLiNER2.5 names a checkpoint family, not a
substitute package version. Bind exact checkpoint revision, five qualified artifact hashes,
tokenizer/splitter, schema order, windows, thresholds, runtime profile and original-coordinate
mapping. Do not migrate whole-pair labels into a new component event or treat returned confidence
as calibrated correctness.

`AutoExtractor.from_pretrained`, schema `.entities(...)`, `.entity_attributes(...)` with
`AttributeGroup(..., applies_to=..., qualify_labels=True)` and `extract(..., include_spans=True)`
are the recognizable native located-attribute composition. The
[tagged v2.1.0 schema source](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py)
and installed `gliner2/inference/schema.py` contain `AttributeGroup`; the
[GLiNER guide](../../libraries/parsing/gliner2.md) distinguishes package and checkpoint capacities.
Context7 `/fastino-ai/gliner2` returned current-main examples on 2026-11-05. That documents the
intended seam, not a qualification of every call against the selected local snapshot.

Before exposing a new native route, check the exact package public API, checkpoint head/config
and output shape. Verify each returned source slice against the actual selected input, then its
mapping to original pieces; prompt prefixes or concatenated usage/target text are not original
source coordinates. Extend the owned runtime profile only when its contract needs it. If this
checkpoint cannot supply the intended located attribute, retain supported entity spans and
rule-based role proposals with explicit unavailability; resolve a concrete checkpoint/API choice
before declaring the selected extraction obligation complete.

Caller-supplied span scoring and JointIE remain conditional challengers. Trigger JointIE only
when independent errors show present endpoints combined with recurring invalid type/direction/
relationship combinations; missing endpoints instead require discovery/window/span correction.
Confirm exact public API/checkpoint capability and require a matched-candidate comparison before
activation. Neither a bigger encoder nor joint decoding repairs an absent target or proves an
attachment. No new external model or dependency is selected by this companion.

### Native admission and consumer migration

WCE01 provides the native component-policy foundation; WCE04 instantiates its exact term/content/
attachment question, expected effect and independently judged evidence. Native eligibility binds
component identity/version, original source closure, current selection and upstream dependencies.
Only the exact independently supported component can enter common `PublicationBatch`. Keep
whole-report ADR-0065 policies with their original meaning. A supported definition component plus
an unresolved usage relation must refuse the whole applicability statement.

Extend `semantic/structural_products.py`, released declarations/preparation, prospective migrations,
native structural validation/publication and `serve/structural_products.py` for the new finite meaning.
Move actual definition readers, named `structural_definitions`, `ci structure list`, registered MCP
and review-bundle/export decoding with it. They must show private components, their partial support
and any separate admitted assertion without upgrading the report standing. Follow returned evidence
and continuations under the same producing source/runtime pins. Only the go-forward report contract remains supported. Faithfully migrate sufficient existing
data; remove and regenerate derived products that lack required witnessed evidence.

Remove the old pair classifier, its registration, pair-only rationale and old result readers.
Recorded outputs may supply development comparisons; executable legacy controls do not survive
the operator-directed cutover. Original evidence and PCE conclusions retain their recorded limits.

### Verification that can distinguish the target

On the same exposed F37 fixed candidates, compare old whole-pair classifier, linguistic/geometry
witnesses, target-local GLiNER and composition. Account for each corrected wrong positive,
preserved supported positive/explanation, newly lost result, spurious result and unresolved case.
This is development evidence; freeze fresh WCE02 source-first and output-first groups before
claiming feedback-driven benefit. Do not use supplied/manual PCE statements as passing evidence
for a new automatic producer.

Independent cases include one passage defining X and mentioning Y, an explanation that is not a
definition, legitimate definition without selected cue, correct target with ambiguous usage,
parent-scoped parameterization and changed source version. Native negatives cover wrong component,
foreign source, changed current selection, invented witness, missing upstream dependency and
component support presented for whole-report admission. Reader/export round trips must preserve
named roles, alternatives, source pieces and exact eligible assertion scope. WCE12 owns assembled
qualification; no provider execution is authorized by writing this plan.

## WCE05 — Actual mentions and compatible scoped relationships

**Contribution:** F03, with F01/F02 consumers. **Consumes:** actual WCE03/WCE04 located products,
WCE01 domain relationship-constraint contracts and native compatibility lowerings, and WCE02
relationship/source opportunities. **Delivers:** discovered occurrence → candidate list → typed
selection → retained contribution/publication/read journey without a supplied-mention prerequisite.

### Actual occurrence route

Accept selected, source-authenticated occurrence/role contributions from the producer cut instead
of constructing a second list of `SuppliedMention` values by hand. Preserve overlapping/nested
occurrences and merged proposal bases. Deduplicate the same physical source occurrence for query
work without merging different contextual roles, source versions or coordinate spaces. Encode the
owned local context once per complete input identity and reuse unchanged inventory vectors; target
inventory membership/scope and negative premises participate in invalidation.

Also implement authenticated target bindings for newly extracted WCE04 components. The current
[curated registry](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_registry.py)
constructs `RegistryTarget` representations with curator-owned `source_binding`; that is not a
source-backed definition inventory. Lower a selected retained definition component to the existing
target descriptor/`TargetRepresentation` and frozen inventory through a distinct authenticated
binding, retaining component/operation identity and actual original project/run/cut/release/result,
source/native product, projection/recipe/content digests, producing runtime and dependencies.
Validate those bindings at native completion and read/replay boundaries. Labels/descriptions may
be derived from located component content, but cannot be relabelled curator text or invented
quotations. Include exact target binding/representation and inventory membership in vector reuse
and candidate identities. The local WCE04 component slice is sufficient for this route; it does
not wait for stronger whole usage-applicability success. Keep curated targets as a separate control.
Verify source substitution, stale component, foreign origin and missing dependency refusal as well
as a real retained component → target inventory → actual mention → relationship journey.

Remove the supplied-mention production bridge; exercise retrieval isolation with current-contract
fixtures. Grade actual discovery
boundary/type errors, inventory gaps, retrieval misses, relation interpretation and admission
separately. A correct target outside the returned budget is retrieval loss; a wrong relation with
the target present is interpretation loss. The historical 14 additional independently identified
relationships are development leads, not a fresh efficacy population.

### Relationship-constraint selection

Replace blanket singleton interpretation under a new policy/version. The released relationship constraint and
participant roles declare which choices compete. A denotation constraint may have one selected
sense or an unresolved alternative group; “specializes” and “compared-with” may both be supported
for the same occurrence. Return compatible selected edges separately from unresolved groups,
with edge-specific endpoints, kind/direction, qualifiers, basis and reason. A decision may retain
useful compatible selections while another constraint remains unresolved. Duplicated evidence for
one edge is corroborating provenance, not another relationship or an independent likelihood.

Apply exact source/scope/version and candidate-membership checks before selection. Preserve
`relationship_compatible` exclusion meaning: denied identity/denotation does not automatically
forbid a comparison between distinct concepts. Preserve explicit exclusions and genuine incompatible
senses; do not make every edge compatible to increase output. Unknown applicable version withholds
the relevant version-specific selection and records its reason. Local-sense/new-concept proposals
remain distinct outcomes; a missing retrieved target alone cannot establish global novelty.

Qualified witness bases include explicit cue, producer-group proposal, geometry, model reading
and admitted derivation, with separate support state. Generalizing the basis field must not admit
model proposals as if they were existing explicit-source witnesses. Only premises/rules admitted
under their applicable policies enter the finite inference owner. More edges confer neither
transitive truth nor identity-merging authority.

### Implement and migrate together

Change `semantic/contextual_links.py` policy and its released preparation/native realization;
update `semantic/contextual_storage.py` to reconstruct only the go-forward report contract.
Store enough declared candidates, relationship constraints, selected edges, alternatives and exclusions for exact
replay. Identity binds the complete semantic decision. Do not regenerate a multi-edge decision by
feeding only selected edges through the historical singleton policy.

Replace `methods/contextual_candidates.py:denotation_contribution` first-alternative behavior with
an owned projection of explicitly selected denotation edges. Multiple compatible non-denotation
edges neither authorize nor hide a denotation. Migrate all callers expecting `outcome == selected`
to imply exactly one edge, including native validation/admission, enrichment decoders, Reader/query
projections, MCP/CLI and detached review/export. Search these assumptions through the affected
source tree during implementation; the two named sites are known obligations, not an exhaustive
consumer claim. Publish only exact supported edge assertions under their declared policies.

Bound local composition by source/region, participant type, role, scope/version and declared join
depth before hydration. WCE06 adds table/symbol/procedure joins using this contract. The operation
must distinguish forced under exhaustive premises, preferred among candidates and unresolved.
No search result can silently supply an exhaustive premise. Avoid full-corpus graph expansion per
mention; reuse prepared inventory/context work across a coherent batch and settle readers before
model execution. A cancelled batch retains actual stage outcomes without partial public visibility.

### Verification and completion contribution

Use known-answer cases with two compatible kinds, two incompatible denotation senses, parallel
edges with distinct witnesses, exclusions, absent/version-unknown targets and reordered candidates.
Assert selected-set and alternative-group membership independently of ordering, and verify exact
policy replay after storage. Check that selecting “compared-with” cannot become “denotes”, and that
ordinary consumers never manufacture a selection from the first alternative.

Run fixed-endpoint A/B/A+B comparisons before actual discovery, then the actual producer → linker
journey on the same independently specified source opportunities. Include false bridges and missing
relations as well as newly supported edges. Native negative controls and Reader/CLI/MCP/export
round trips belong to this package. WCE11 later composes cross-package journeys, and WCE12 alone
accounts for final assembled qualification and production retirement.

## Completion boundary and checks

Package readiness and F01–F03 disposition exist only in the coordinator. WCE03–WCE05 contribute
implemented semantics, migrated producers/consumers, truthful partial-state behavior, focused native/
provider results where required and current-only consumer paths with obsolete readers and controls removed. They do not establish
all WCE efficacy, released-corpus support, default activation or broad model capacity.

For implementation, use relevant targeted Python method/semantic/native tests and actual provider
checks for the changed route; protect independent source/role expectations. Commands and outcomes
must be recorded with their exact selected scope at execution time. Final functional union and
applicable hygiene follow WCE12 after final-source maintenance. No new lints, generic alignment
framework or duplicate validator is scheduled.

Plan-authoring execution, 2026-11-05: read-only source/documentation inspection and Context7 lookup
performed. Product tests, probes, model/provider/database execution, training, benchmarks and
integrated qualification: **not_run**. The root owns publication checks and `just turn-end`.


## Selected WCE04–05 realization — 2026-11-06

The [completion audit](../witnessed-corpus-enrichment_2026-11-05.md#completion-audit) retains the implemented candidate, definition and linking
mechanisms. The F37 fixed comparison preserves the recorded old cells and current source facets.
It leaves whole usage-target applicability unassessed. The actual retained-mention journey
establishes transport of private own-component edges. WCE05 still requires independently
specified fixed-endpoint arms and assessment of actual linking, including missed relations and
false bridges.

The coordinator owns completion and unresolved findings. [Final scoped evidence](../../design_review/evidence/2026-11-06_wce-definition-linking/records/wce04-05.final-union.json)
covers the current-only implementation. Method4 `structure.definition_components` composes named
rules/native geometry and optional located GLiNER extraction. Its explicit linguistic-only mode
requires named candidates and no model profile; default model mode is preserved. This is a genuine
producer-mode configuration change, separate from runtime-only window budgets. The statistics
`witnessed` recipe adds constructive copula + content constructor + operation descendant. Shared
attachment construction excludes explicit local dependency negation while retaining raw matches
and negation extents. Controlled and actual mean cases establish construction, not scientific truth.

Original annotation lookup authenticates selected original cut, method/version, input/configuration,
release and native source before reading current columns. Missing or authenticated unsupported
annotations yield typed unavailability; no historical decoder runs. Per-variant availability and
per-window location/attachment outcomes remain visible. Models execute outside owned read snapshots.

Source-role projection and authenticated component inventories feed relationship constraints.
Equivalent source-resolved target meanings share an inventory-local semantic group; every original
component/vector/candidate/witness remains retained. Different content/source/parent/scope/version
continues to compete. Physical occurrence dedup saves query work without merging contextual roles;
each edge chooses its own deterministic qualified carrier. Private vector/candidate budgets still
count private representations, so no unique-meaning capacity or speed benefit is claimed.

Current component/edge public statements contain source-resolved meaning and qualifiers, excluding
query wording, retrieval diagnostics and opaque private IDs. Complete decision identity retains
provenance. Native replay binds selected relationships, exact original source/dependencies and all
six applicability dimensions. Same defining-occurrence introduction is distinct from transfer;
unknown material premises withhold transfer applicability. Common independent eligibility qualifies
only the exact component/edge statement, leaving private report standing unchanged.

Actual normal component120/publication121, relationship127/applicability130 and mean136 have scoped
native/read/export evidence. Fresh CLI/MCP validates the first three selected retained populations.
The fixed exposed F37 source comparison preserves all20 old cells and reports one new private mean
component, zero model attachments and remaining gaps; it does not count missing whole-app outputs
as corrected old judgments. Fresh efficacy and assembled multi-package qualification remain WCE02/12.

**Tested, 2026-11-07.** Contextual method5 keeps label and alias matching in retrieval.
Private denotation can use the coincident original definition span, and other
relationships still require their own producer witnesses. The actual formula X
continues to retrieve the unrelated red-ball candidate and now abstains. The exact
formula Z and eligible standard-normal target were missed. The
[composition receipts](../../design_review/evidence/2026-11-06_wce-completion-repair/composition/README.md)
preserve the before and after judgments.
