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

## DA-002 — Cited independent-subset manifestations corrected

**Source-inspected 2026-11-05.** Consolidation consumes released source admissibility (`semantic/consolidation.py:225–228`);
proposal roles and evidence/source domains derive from released vocabularies
(`semantic/proposals.py:88–100`). Executable reference splits come from the exact companion
(`semantic/contracts.py:1734`; `semantic/types.py:326–343`). A remaining finite physical CHECK
alone does not demonstrate competing meaning or late rejection. The previous cited diagnosis
is removed; this is not exhaustive vocabulary-to-native correspondence qualification.

<a id="da-003"></a>

## DA-003 — Cited behavioral-role reconstruction corrected

**Source-inspected 2026-11-05.** Statement behavior consumes released subsets (`semantic/domain_operations.py:200–211`);
expression behavior does likewise (`semantic/rule_views.py:320–337`). Display lookup consumes
`prepared.display_properties()` (`serve/read.py:157–175`), whose ordered bindings are owned by
`semantic/types.py:352–385`. The earlier differently named display-property omission no longer
follows. This does not establish extension locality for every possible new behavioral role.

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
for a concrete consumer scenario. DA-005 records the subsequent correction of the previously demonstrated translation omissions.

<a id="da-005"></a>

## DA-005 — Rule-value and address translation omissions corrected

**Source-inspected 2026-11-05.** `semantic/rule_views.py:250–337` preserves declared range, enum identity, expression form and
language, missing reason, unavailable reading state and released symbol/binding behavior;
`:160–165` consumes the resulting behavior. The older evaluator now imports the shared address
owner (`evaluate/semantic.py:696,718`; `semantic/identity.py:34`). The prior demonstrated loss and
independent address-authoring premises are removed. Arbitrary future translations remain subject
to their own fidelity contract.

<a id="da-006"></a>

## DA-006 — Reference-kind diagnosis remains corrected

`semantic/reference_positions.py:24–29,104–147` distinguishes reference kinds/ranges;
`semantic/proposals.py:777–797` checks nested memberships. DA-007 records the later explicit identity-decision representation.

<a id="da-007"></a>

## DA-007 — Identity-decision state premise corrected

**Source-inspected 2026-11-05.** `semantic/domain_operations.py:1219–1251,1275–1313` retains resolved, ambiguous_anchor,
incomplete_key and ungrounded_cycle decisions, with candidates, dependencies and policy.
Publication carries EntityResolutionRow (`semantic/publication.py:79–90,381`;
`semantic/domain_operations.py:2215`); native closure requires the producing operation/version
and prevents provisional outcomes from claiming globally resolved identity
(`semantic/sql/closure.sql:774–795`). Ordinary discoverability of every identity decision was not
exhaustively examined; that limit is not a replacement established defect.

<a id="da-008"></a>

## DA-008 — Global case-erasure diagnosis remains corrected

`semantic/types.py:329–333,378–381` folds only properties that declare that policy.

<a id="da-009"></a>

## DA-009 — Unicode parity has a bounded qualification owner

**Source-inspected 2026-11-05.** `semantic/unicode_identity.py:99–160,233–246` compares the PostgreSQL-supported scalar folding
mapping and fences exact Python/PostgreSQL determinants and archived recipe. Activation invokes
that boundary (`semantic/execution_admission.py:75–79`); keys use its folding owner
(`semantic/types.py:409–412`). The earlier unowned-parity premise is corrected for the supported
pair. No universal runtime parity or fresh native execution is claimed.

<a id="da-010"></a>

## DA-010 — Explicit profile acquisition remains corrected

`semantic/regeneration.py:113–132` and `semantic/composed.py:22–60` archive explicit trusted
operation/query dependencies. DA-028 reassesses execution custody.

<a id="da-011"></a>

## DA-011 — Current compiler guidance supersedes dated descriptions

**Source-inspected 2026-11-05.** D2's current opening names compiler17/execution27 and routes current/readable authority to
source (`docs/design/D2-schema-and-guidelines.md:15–34`). Constants agree
(`semantic/types.py:17–19`; `semantic/contracts.py:28`). Earlier implementation paragraphs have
explicit dates; those historical numbers alone do not sustain the earlier present-tense conflict.
No whole architectural-document consistency certificate follows.

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
kinds. The cited formula/role manifestations were corrected under DA-003; whether reusable
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
