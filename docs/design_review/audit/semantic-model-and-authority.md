# Semantic model and authority

**Implemented source inspected, 2026-11-03.** [Baseline and limits](README.md#baseline).
Source paths below are relative to `python/corpus-structure/src/corpus_structure/` unless
prefixed `docs/` or `domains/`. Resolved diagnoses are removed; anchors preserve identity and
Git before this refresh preserves their dated evidence. No implementation-plan closure follows.

<a id="da-001"></a>

## DA-001 — Qualifier-projection diagnosis corrected

`semantic/comparison_projection.py:103–185,201–259` compiles and validates context/compared/evidence
partitions; preparation archives them and `domain_operations.py:2605–2614` consumes them.
Fact identity remains separately governed by `types.py:355–387`. Different equivalence keys
are legitimate when their contracts are explicit; the earlier opposite-default diagnosis is removed.

<a id="da-002"></a>

## DA-002 — Closed vocabularies retain independently authored subsets

**FP-04/05, DP-01/03/06; implemented.** Establishment is authored in core.yaml:595–599,
assembly's accepted subset in `semantic/consolidation.py:242–246`, and a physical CHECK in
physical.yaml:1596 (model paths are under model/semantic). Agent statement/evidence roles
are separately authored in agent.yaml:149–170. ReferenceSplit includes reserved
(reference.yaml:180–184) while the reference-set physical constraint excludes it
(physical.yaml:2030). Changes require independent semantic edits or can be admitted upstream
and rejected downstream. This is not a claim that every closed set is duplicated: effective
statement kinds and reference products now derive from released declarations. DA-040 owns the
concrete late-rejection consequence; these manifestations share the independently authored subset.

<a id="da-003"></a>

## DA-003 — Behavioral roles are reconstructed in consumers

**FP-04/A2, DP-01/06/08; implemented.** `semantic/domain_operations.py:3020–3026,3260` recognizes
literal premise/example_value/formula/assumption roles. `serve/read.py:151–158` finds display
labels through the name set label/aliases/name/canonical_name, despite explicit display roles
in `semantic/property_roles.py:13–35`. A differently named display property can affect identity
or reference handling yet disappear from label lookup. Adding that category therefore reaches
consumers outside its declared owner. Effective statement bindings and qualifier projections
correct several older manifestations; metadata alone does not automatically promise executable policy.

<a id="da-004"></a>

## DA-004 — Repeated representation conversion remains an unresolved question

**FP-04/06/07, DP-02/08/10; unresolved, no demonstrated semantic loss.** AgentStoredBatch is
validated and dumped (`semantic/domain_operations.py:838–845`), with later dictionary-based
transformations (`:1438–1506,1594–1623`). Proposal location validates/dumps/deep-copies
(`semantic/proposals.py:758–763,800`). These are observed conversions, not proof of lost meaning.
`semantic/reference_positions.py:31–52,94–103` consumes cached archived effective positions;
`:168–193` validates/walks typed models, and `:197–221` revalidates after actual reference mutation.
This is substantial counterevidence to independent semantic reconstruction. No cited distinction
was shown to be lost, and no redundant validation was established under unchanged premises.
The earlier established diagnosis is withdrawn; the locality/execution tradeoff remains a question
for a concrete consumer scenario. DA-005 owns the demonstrated translation omissions separately.

<a id="da-005"></a>

## DA-005 — Rule-value translations omit consequential meaning

**FP-04/A2, DP-02/07/08; implemented.** The rule schema now has an archived owner and public
accessors (`semantic/rule_views.py:207–231`), correcting the old private-schema claim.
The actual projection still assigns enum=None and slot kind=value kind (`:189–204`), while
ValueView.defined_symbol recognizes only literal formula (`:129–131`). Core ExpressionValue
therefore has different rule-visible meaning. This is a translation-contract gap, not the absence
of a rule schema. The older Agent evaluator also rebuilds claims/N addresses (`evaluate/semantic.py:695`)
independently of production (`semantic/domain_operations.py:1499`); current prediction reads do
filter to admitted occurrences. M1 record evaluation has a separate explicit address contract.

<a id="da-006"></a>

## DA-006 — Reference-kind diagnosis remains corrected

`semantic/reference_positions.py:24–29,104–147` distinguishes reference kinds/ranges;
`semantic/proposals.py:777–797` checks nested memberships. Remaining outcome uncertainty is DA-007.

<a id="da-007"></a>

## DA-007 — Unsettled identity state is not consistently exposed

**FP-04/05, DP-02/21, CI-04; implemented.** Ambiguous anchored labels become singleton
partitions (`semantic/domain_operations.py:923–953`), and ungrounded cycles exit with
source-qualified identities (`:1037–1042`), without a typed ambiguity result for those decisions.
Bare local/known identifiers still share fallback mapping (`semantic/reference_positions.py:125–131`).
ClaimCandidate.unresolved_references, recursive reference positions, membership checks and partial
coverage are material counterevidence. The surviving concern is discoverability of unresolved
identity meaning; no collision or false absence result was demonstrated.

<a id="da-008"></a>

## DA-008 — Global case-erasure diagnosis remains corrected

`semantic/types.py:329–333,378–381` folds only properties that declare that policy.

<a id="da-009"></a>

## DA-009 — Cross-runtime identity parity remains an unresolved question

**DP-04/09/24; unresolved, no demonstrated divergence.** Scientific/Python determinants now
have one owner (`semantic/determinants.py:24–45,79–91`); identity uses value_codec. Remove the
old missing-library-list/unversioned-recipe diagnosis. Python casefold (`types.py:379–381`) and
PostgreSQL casefold (`semantic/sql/identity.sql:61–62`) remain distinct runtime realizations;
this inspection did not establish their complete Unicode parity contract. Mirrors alone do not
establish a defect, and native recomputation has a real trust-boundary purpose.

<a id="da-010"></a>

## DA-010 — Explicit profile acquisition remains corrected

`semantic/regeneration.py:113–132` and `semantic/composed.py:22–60` archive explicit trusted
operation/query dependencies. DA-028 reassesses execution custody.

<a id="da-011"></a>

## DA-011 — Present-tense architecture guidance conflicts across compiler generations

**FP-06, DP-21/22/24; design text.** D2 describes compiler12, compiler7/semantic-1 support,
and compiler6 at `docs/design/D2-schema-and-guidelines.md:72,109,156`; current source declares
compiler15/boundary12 (`semantic/types.py:17–19`) and execution compiler23 (`contracts.py:28`).
An extension author cannot tell which present-tense contract governs from those descriptions.
Honest Proposed or explicitly historical detail is not the defect. The architecture map itself
is a route to owners, not a conformance certificate. Current-only ADR-0047 controls compatibility.

<a id="da-026"></a>

## DA-026 — Missing operation-product diagnosis corrected

`semantic/composed.py:64–113`, `contracts.py:794–875,1274–1295` and generated _operation_calls.py
bind executable operations and approved implementations. The old missing-product diagnosis is removed.

<a id="da-027"></a>

## DA-027 — Exhaustive invariant-to-enforcement correspondence remains unexamined

**FP-05, DP-03/21; unresolved.** Typed failure bindings (`contracts.py:339–361`), compile
validation (`invariant_failures.py:34–90`) and actual native-error classification (`:108–151`)
have real consumers in operations/source_views. Native execution projection checks operations,
transitions and effects; native guard bodies enforce attempt ownership and terminal publication.
This corrects the earlier suggestion that the execution model is decorative. Not every invariant
body was independently matched to its declared meaning. That is an explicit assurance limit,
not an established violation merely because a universal correspondence check was not found.

<a id="da-028"></a>

## DA-028 — Unpinned query-plugin diagnosis corrected

`cli/query.py:42–67` opens the producing release's registry. `semantic/query_compatibility.py:307–397`
checks archived contracts, source/runtime and installed compatibility before import; `:432–447`
checks continuation custody. Unsupported edits refuse instead of silently reinterpreting queries.

<a id="da-034"></a>

## DA-034 — Undeclared scientific-equivalence authority diagnosis corrected

Consolidation uses SemanticComparator and evaluation ReferenceComparisonScope from the shared
scientific_evidence owner (`domain_operations.py:2592–2595,2768–2778`; `evaluate/semantic_alignment.py:752`).
Different consolidation/reference policies are explicit and archived (`scientific_evidence.py:150–244,347–373`).
Different purposes need not use identical equivalence. Representative choice belongs to DA-044.

<a id="da-046"></a>

## DA-046 — Broad statistics-core diagnosis withdrawn; boundary question unresolved

Core mathematical vocabulary alone does not prove statistics coupling. The toy pack binds its
own statement enum (`domains/toy/semantic.yaml:36–40`) and proposal generation uses effective
kinds. Concrete generic formula/role interpretations remain under DA-003; whether reusable
mathematical core types exceed the intended boundary remains unresolved, not a second diagnosis.

<a id="da-048"></a>

## DA-048 — Missing pack-input diagnosis corrected; operational scope is explicit

`semantic/regeneration.py:189–297` coalesces equal policies/aliases and refuses conflicting
operation policies. Scientific/rule-view inputs are deliberately shared. Schema compilation
accepts multiple packs; regeneration and query context select one canonical domain
(`cli/schema.py:53–66`; `cli/regenerate.py:33,156–164`; `cli/query.py:54–67`). The earlier claim that
composition necessarily loses root rules is removed. A simultaneous multi-pack production
requirement was not established; the operational boundary is not silently promoted to a defect.

<a id="da-049"></a>

## DA-049 — Universal historical-lifetime diagnosis removed against current target

ADR-0047 selects current-only execution with explicit maintained-reader compatibility.
`semantic/archive_reader.py:243–304` checks readable boundary compatibility; full execution
verification retains exact producing determinants (`releases.py:511–600`). Native execution has
ABI/effect checks and explicit read-only exceptions (`sql/execution_projection.sql:7–23`).
Unsupported historical execution is an intentional support limit, not an accidental promise of
universal compatibility. Current archived query custody remains protected under DA-028.
