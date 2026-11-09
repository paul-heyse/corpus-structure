# Production milestone two implementation plan

**Status: Private parser execution · 2026-11-08.** This coordinator owns PM2-00–PM2-12, shared decisions,
scheduled M2 review disposition and milestone qualification. The [functional review](../functional_reviews/production-milestone-two_2026-11-08.md)
at `971111baf` governs the recommendation baseline. Its [two-pass design input](../target-pipeline-design/production-milestone-two.md)
was recorded at `4c71fa3f4`. The five model guides were inspected at
`c55b1873e`. The current integration baseline was inspected at `fc111e466`.
The Transformers and Sentence Transformers guides were recorded at
`f6b8612be`. Consuming packages cite their mechanisms and source. This
series records the operator's corpus and design boundary. The foundation receipts
record the qualified scope of PM2-00–02. The [parser execution account](production-milestone-two/linguistic-referential-discourse.md#parser-execution)
owns the implementation and scoped assessment for PM2-03–05. PM2-06 onward remains proposed.

## Target and foundation

Deliver a reusable pipeline for located linguistic structure, local reference resolution,
discourse context, and bounded semantic decisions. A reader should be able to inspect
an independently useful part of a statement, understand what remains unresolved, and
follow the result to the precise source, provider output, candidates and decision.
Preserve the ordinary distinction between private proposals and admitted knowledge.

**Domain-agnostic implementation.** The same operations, result contracts, provider
adapters, and admission and read paths apply to a theorem premise, an instruction in a
worked example, or a requirement in a business document. Domain declarations supply
the vocabulary, argument signatures, criteria, applicable operations and policy.
Source profiles supply representation and layout. Neither a book title, page number,
document genre nor a particular pack name selects a different implementation. Native
linguistic labels remain in their own annotation scheme. Allow two domain releases to
bind the same operation to different concepts or criteria through the existing released
LinkML and execution model. Keep cross-corpus adoption, business qualification and
cross-document identity for later selection. Use a small second-vocabulary contract
fixture to demonstrate reuse without another corpus or provider path.

**Qualification scope.** Develop and qualify on the authenticated 518-page
Grinstead–Snell parent. Use its existing source views and natural section scopes.
The reference corpus provides opportunities and independent expectations, not semantic
or routing rules. Earlier WCE, NCE and DMA evidence keeps its scope. Successful results
on this exposed source establish textbook behavior within the tested release.
[Full-book authority](../adr/0070-full-book-method-development.md)

| Inspected foundation | Design consequence |
| --- | --- |
| Current v10 selected source views, ordered native fields, atom-preserving layouts and authenticated projection proofs | Use these coordinates for provider maps and the existing native and detached completeness checks. A provider rendering can supply a candidate while an ambiguous mapping withholds an exact witness. [Source projection owner](domain-model-alignment/source-projection.md) |
| M1 literal-only GLiNER extraction and retained predicate-frame qualification, with the released `definition-scope-1` witness guard | Use scoped M1 execution evidence as a comparator. Preserve the strong retained-annotation route and qualify a scheme-aware HanLP route before migrating a consumer that relies on it. [Definition admission](domain-model-alignment/semantic-admission.md#DMA-05) |
| Released operation/dependency model, immutable native task receipts, shared PostgreSQL admission, and protected references | Use these owners for effective profiles, operation outputs, retained witnesses and assessment. Keep observation, selection and admission separate. Maintain the current-only producer/consumer rule with supported archived reads. [Current-only decision](../adr/0067-witnessed-current-only-cutover.md) · [Semantic admission](domain-model-alignment/semantic-admission.md) |
| E5 and Qwen role-aware encoders, frozen candidate inventories, typed relationship selection, and contribution and dossier reads | Extend anchored context and candidate availability through the same pipeline. A model score or extra candidate does not confer semantic standing. Make a separate consumer only if existing typed reads cannot deliver the required product. [Architecture map](../design/README.md) |

**Development readiness, 2026-11-08.** Development reached
`semantic_pm2_parser_methods` and admitted the private parser release.
Run 404 at cut 514 supplies the source-only view used to write expectations.
Private run 407 at cut 517 selected the same retained views and settled all 29
annotation and 29 candidate tasks. It supplies the authenticated completed-source
references for parser execution and M1 execution evidence at those scopes.
Its grading attempt paired the full selected
view's predictions with a one-sentence reference and produced no evaluation.
The project has no active release or selected result. Final qualification and
evaluated cutover remain with DMA-13 after the explicit-only Chandra change.
[Parser development deployment](../design_review/evidence/2026-11-08_pm2-parsers/records/pm2.parser-development-deployment.json) ·
[M1 deployment, private runs and grading](domain-model-alignment_2026-11-08.md#audit-repair-execution) ·
[Qualification pause](domain-model-alignment_2026-11-08.md#qualification-pause--2026-11-08)

## Shared decisions and sequencing

Start with native HanLP ModernBERT Large, Maverick MES on coherent sections, Dipo
DMRST on bounded scopes and d1-2B text interpretation. Retain GLiNER and the existing
dense and lexical routes. Keep source-first d1 discovery independent of other providers
so it can recover missed structure. Start independent providers as soon as the exact
source and their worker profile are ready. Freeze candidates before dependent
interpretation. Select and publish only with their exact dependency and source closure.
Use ordinary typed outcomes when a provider fails, hits a scope limit, or returns
empty. Independent settled observations remain available.

Use one initially resident M2 GPU profile under the shared host policy. Provider
limits bound the work examined, including a single oversized request, and remain
distinct from the number of items displayed. Preserve the semantic profile when
reducing a physical batch. Record new effective inputs when a fallback changes
coverage, context, or execution semantics. Use exact retained products to rerun only
the affected operation. An independent source-only reference inventory can proceed
alongside native profile work. One early integrated journey consumes only the minimal
working slices, while later adoption requires every selected package and its evidence.
[Execution and source contracts](production-milestone-two/source-contracts-and-model-execution.md)

Apply the [selected standard](../design_review/design_principles/standard.toml) to scoped
authority, typed fidelity, locality, recoverable evidence, and execution fit. Use focused
assessment inside these packages. Schedule the binding's design/target reviews before
the substantial stage and at assembled scope, with adjacent consumers. No binding
rule change is assumed. Any proposal to change a rule is an explicit decision for the
operator before dependent design or work relies on it. [Review cadence](../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository)

## Execution queue

The foundation and private parser entries have execution dispositions in their owning sections. The availability column names the earliest dependency for
implementation or evidence, rather than making a whole companion a prerequisite.

| Package | Consumes | Delivers and closes when |
| --- | --- | --- |
| [PM2-00](#PM2-00) · Baseline and release boundary | Current tree, DMA development receipts and cut 514 source | Exact source and scoped comparators recorded, with adoption readiness separately identified. |
| [PM2-01](production-milestone-two/source-contracts-and-model-execution.md#PM2-01) · Source and result contracts | PM2-00 source identity | Exact typed maps, outcomes and same-release reuse through retained reads. |
| [PM2-02](production-milestone-two/source-contracts-and-model-execution.md#PM2-02) · Worker qualification | PM2-00 target access, provider artifacts | Each initial provider has an executable locked profile and bounded attempt/failure evidence. |
| [PM2-03](production-milestone-two/linguistic-referential-discourse.md#PM2-03) · HanLP | PM2-01 and own PM2-02 profile | Located frame candidates with native labels and no semantic regression on migrated consumers. |
| [PM2-04](production-milestone-two/linguistic-referential-discourse.md#PM2-04) · Maverick | PM2-01 and own PM2-02 profile | Mention inventory, section-local candidates and supplied-mention diagnostic pass. |
| [PM2-05](production-milestone-two/linguistic-referential-discourse.md#PM2-05) · Dipo | PM2-01 and own PM2-02 profile | Source-aligned ordered binary trees, section coverage and reviewed-EDU diagnostic. |
| [PM2-06](production-milestone-two/linguistic-referential-discourse.md#PM2-06) · Extended parsing modes | Relevant PM2-03–05 route and independent error cases | Conditional mode is qualified or disposition records why it remains off and when to reconsider. |
| [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#PM2-07) · GLiNER and d1 | PM2-01 and own PM2-02 profile. Candidate-dependent tasks need the relevant producer or PM2-09 inventory. | Versioned task outputs, source-first recovery, grounded typed reads and exact candidate alternatives. |
| [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#PM2-08) · Composition and delivery | Minimal PM2-03–05 and PM2-07 outputs, current admission and read contracts | Early partial product through private Reader/MCP. Extend to selected product families and qualified admission. |
| [PM2-09](production-milestone-two/retrieval-composition-and-delivery.md#PM2-09) · Contextual retrieval | PM2-01, current retrieval and anchored upstream context | Existing and richer contexts compared. Typed link candidate path feeds PM2-07 interpretation and PM2-08 selection. |
| [PM2-10](production-milestone-two/retrieval-composition-and-delivery.md#PM2-10) · Visual inspection | Exact visual custody, PM2-07, named ambiguity | Conditional typed location or classification with incremental utility and crop mapping, or an explicit reason to leave off. |
| [PM2-11](production-milestone-two/textbook-assessment-and-adoption.md#PM2-11) · Operation assessment | PM2-00 source-only frame. Predictions join as package results settle. | Paired native comparisons, independent dispositions and release-eligible event evidence. |
| [PM2-12](production-milestone-two/textbook-assessment-and-adoption.md#PM2-12) · Adopt selected scope | PM2-08–11 outputs as selected, eligible predecessor, required union and effect authority | Qualified textbook release through normal entry points, with retry, preservation and verified selection. |

<a id="PM2-00"></a>

### PM2-00 · Freeze the comparable baseline

Reconcile the acquired target, release, and source identities with STATUS and DMA-13
at execution time. Start source-contract work, provider qualification, and independent
reference preparation on the available development foundation. Use cut 514 for source
preparation and cut 517 as the private M1 execution comparator where the selected
source and operation scope correspond. Use the qualified predecessor for release
comparisons once the owning evidence supplies it. Preserve historical WCE and NCE
comparators at their original extent and require exact source and semantic
correspondence before pairing. Close PM2-00 once the source opportunities can be
frozen without predictions and each comparator's available scope and outstanding
prerequisite are identified. PM2-12 requires an eligible predecessor, applicable
qualification and effect authority. DMA-13 retains the grading and cutover obligations.

**Passed · 2026-11-08.** The [frozen baseline](../design_review/evidence/2026-11-08_pm2-foundation/README.md#frozen-development-baseline)
names the target, release, source product, exact reference and multi-sentence scopes,
and two v10 original-spelling controls. An explicit archived-release check passed.
Selection lookup refused because the project has no active release. The source-only
frame and private M1 comparator are available within their recorded scopes. Run 407
against sentence-only set 32 remains a refused grading attempt with no evaluation.
DMA-13 owns the eligible predecessor for PM2-12.

## Foundation execution

The [combined design and target review](../design_review/reviews/design_review_pm2-foundation_2026-11-08.md)
accepted the private foundation scope against the refreshed audit at `9bdb0996e`.
The source projection and physical occurrence have separate proof requirements.
The existing task, result and host GPU owners retain their custody.

| Package | Current disposition |
| --- | --- |
| PM2-00 | Passed for the frozen development source and explicitly scoped comparisons. |
| PM2-01 | Implemented and tested. [Source mapping, private Reader and reuse](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence). |
| PM2-02 | Passed for the initial development profiles, including mixed-profile claim reassignment. [Profile and operating evidence](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence). |

## Review disposition

| Review opportunity | Proposed disposition and closure owner |
| --- | --- |
| PM2-R01 | Addressed by PM2-01. Retain exact selected projection separately from physical occurrence and test the admitted result path. |
| PM2-R02 | PM2-02 native profile and shared custody controls passed within the retained scope. The mixed-profile Reader and exact reassignment control passed. Provider packages own expanded scopes. |
| [O01](../functional_reviews/production-milestone-two_2026-11-08.md#O01) | Initial PM2-01. Exact source, identity and availability survive inference, composition and reads. |
| [O02](../functional_reviews/production-milestone-two_2026-11-08.md#O02) | Initial PM2-03 retained frames, cues and constituency. Extra heads and migration evidence remain under PM2-06. |
| [O03](../functional_reviews/production-milestone-two_2026-11-08.md#O03) | Initial PM2-04 retained separate mention and cluster products with a supplied-mention diagnostic. PM2-06 owns conditional joint mode, score access, speaker and seeding. |
| [O04](../functional_reviews/production-milestone-two_2026-11-08.md#O04) | Initial PM2-05 retained ordered trees and paired EDU diagnostics. PM2-08 owns composed context use. PM2-06 owns larger scopes and tree revision decisions. |
| [O05](../functional_reviews/production-milestone-two_2026-11-08.md#O05) | Initial PM2-07 with source-first and candidate-centered paths. PM2-09 supplies scoped relation candidates. Optional tasks and challengers retain triggers. |
| [O06](../functional_reviews/production-milestone-two_2026-11-08.md#O06) | Initial PM2-08 and PM2-09. Product meaning, scope, model dependence and admission remain explicit. |
| [O07](../functional_reviews/production-milestone-two_2026-11-08.md#O07) | Initial PM2-11 and assembled PM2-12. Compare independent results and report coverage before claims. |
| [O08](../functional_reviews/production-milestone-two_2026-11-08.md#O08) | Initial PM2-02. Wider residency, compilation and runtime substitution have explicit prerequisites. |
| [O09](../functional_reviews/production-milestone-two_2026-11-08.md#O09) | Conditional PM2-10. Use exact visual custody and a reviewed unresolved source ambiguity. |

The [review's baseline crosswalk](../functional_reviews/production-milestone-two_2026-11-08.md#baseline-disposition)
is the trace for both design passes. The companions carry its controls and distinctions:
the model roster, GLiNER classification, optional heads and parsing modes, d1 readouts,
composition, finite inference, independent evaluation and operating choices. Keep
UltraBERT, KNIV, custom heads, retraining and alternate parser families as gap-driven
alternatives after alignment, deterministic composition, and task/context comparisons.
Keep generative discourse parsing, d1 fine-tuning, video, additional numerical engines
and cross-corpus adaptation deferred until their own concrete capability is selected.
[Composition and specialized alternatives](production-milestone-two/retrieval-composition-and-delivery.md)

Completion requires a qualified four-profile release within the declared textbook scope,
a useful independently inspectable partial result and evidence of better named operations
with preservation on their paired controls. The assessment companion owns exact
release criteria and separates qualification, measured benefit, and live selection.
PM2-07 is the next independent provider package. The parser execution account identifies
the remaining evidence for PM2-03–05 and the boundary with PM2-06, PM2-08 and PM2-11.
