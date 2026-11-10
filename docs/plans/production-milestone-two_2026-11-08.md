# Production milestone two implementation plan

**Status: Private development; adoption open · 2026-11-09.** This coordinator owns PM2-00–PM2-12, shared decisions,
scheduled M2 review disposition and milestone qualification. The [functional review](../functional_reviews/production-milestone-two_2026-11-08.md)
at `971111baf` governs the recommendation baseline. Its [two-pass design input](../target-pipeline-design/production-milestone-two.md)
was recorded at `4c71fa3f4`. The five model guides were inspected at
`c55b1873e`. The current integration baseline was inspected at `fc111e466`.
The Transformers and Sentence Transformers guides were recorded at
`f6b8612be`. Consuming packages cite their mechanisms and source. This
series records the operator's corpus and design boundary. The foundation receipts
record the verified scope of PM2-00–02 as of 2026-11-08. The [parser execution account](production-milestone-two/linguistic-referential-discourse.md#parser-execution)
owns the implementation and scoped assessment for PM2-03–05. The
[adoption qualification account](../design_review/evidence/2026-11-09_pm2-adoption/README.md)
records the paired scope and the limits on qualification. The [completion audit](#completion-audit)
reconciles the delivered private scopes with the remaining acceptance work. The project remains unselected.

**Proposed extraction amendments · 2026-11-09.** This revision consumes the
[GLiNER2 and spaCy improvement review](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md)
at `d4a40cd6e`, the clean source baseline for the revision. It develops the remaining
work within PM2-00–12. The [improvement disposition](#extraction-improvement-disposition)
distinguishes proposed work from conditional and outside-scope alternatives. It does
not change the verified development scope or the adoption gates.

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
| WCE named rules and overlapping candidates; NCE release-bound model observations and replay | Reuse the retained annotation view and NCE execution and replay rather than adding another candidate engine. The preset suggester does not establish learned classification; native GLiNER2 proposals, decoded observations and semantic support need separate comparisons. [Located candidates](production-milestone-two/linguistic-referential-discourse.md#shared-located-candidates) · [Interpretation](production-milestone-two/gliner-and-d1-interpretation.md#same-question-extraction-and-interpretation) |
| Released operation/dependency model, immutable native task receipts, shared PostgreSQL admission, and protected references | Use these owners for effective profiles, operation outputs, retained witnesses and assessment. Keep observation, selection and admission separate. Maintain the current-only producer/consumer rule with supported archived reads. [Current-only decision](../adr/0067-witnessed-current-only-cutover.md) · [Semantic admission](domain-model-alignment/semantic-admission.md) |
| E5 and Qwen role-aware encoders, frozen candidate inventories, typed relationship selection, and contribution and dossier reads | Extend anchored context and candidate availability through the same pipeline. A model score or extra candidate does not confer semantic standing. Make a separate consumer only if existing typed reads cannot deliver the required product. [Architecture map](../design/README.md) |

**Development readiness, 2026-11-08.** Development reached
`semantic_pm2_parser_methods` and admitted the private parser release.
Run 404 at cut 514 supplies the source-only view used to write expectations.
Private run 407 at cut 517 selected the same retained views and settled all 29
annotation and 29 candidate tasks. It supplies the authenticated completed-source
references for parser execution and M1 execution evidence at those scopes.
The first grading attempt paired the full selected view's predictions with a one-sentence
reference and produced no evaluation. A new exact full-view reference graded two views
successfully as an evaluation operation, but the semantic result missed both adjudicated
Preface readings. It does not qualify run 407 for adoption.
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

**Extraction amendment sequence.** Establish the PM2-01/02 source, outcome and reuse
contracts and the released parser payload boundary first. PM2-03/07 can compare located
candidates and same-question interpretation as their inputs become available; the PM2-11
independent frame can be authored in parallel. Recover definition targets and affine
occurrence carriers independently. PM2-08 can build its typed producer and selector
against retained private inputs while those producers are being repaired. A positive
admission journey needs a qualified contribution and witness. The p289 path has one
qualified control. PM2-09 consumes the eligible inventory and exact carriers relevant
to each comparison before ranking; PM2-07 only needs that frozen list for the
contextual-link question. Keep ordinary discovery independent of the retrieval arm.
Use the [learned extraction companion](production-milestone-two/learned-extraction-investigations.md)
only when the bounded diagnostics isolate an error that justifies a challenger.

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
| [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#PM2-07) · GLiNER and d1 | PM2-01 and own PM2-02 profile. Candidate-dependent tasks need the relevant producer; only contextual-link interpretation needs the PM2-09 list. | Versioned source-first and candidate-centered outputs, including completed empty questions; matched capture and fixed-candidate comparisons. |
| [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#PM2-08) · Composition and delivery | Minimal PM2-03–05 and PM2-07 outputs, released payloads and current admission and read contracts | Typed producer and selector deliver a qualified attachment and preserve a useful part with a failed sibling. Extend to selected families. |
| [PM2-09](production-milestone-two/retrieval-composition-and-delivery.md#PM2-09) · Contextual retrieval | PM2-01, eligible definition targets and exact affine carriers, current retrieval and anchored upstream context | Compare v10 with each applicable enriched recipe after coverage. Deliver an authenticated bounded list to PM2-07 and preserve qualified selection and detached replay. |
| [PM2-10](production-milestone-two/retrieval-composition-and-delivery.md#PM2-10) · Visual inspection | Exact visual custody, PM2-07, named ambiguity | Conditional typed location or classification with incremental utility and crop mapping, or an explicit reason to leave off. |
| [PM2-11](production-milestone-two/textbook-assessment-and-adoption.md#PM2-11) · Operation assessment | PM2-00 source-only frame. Predictions join as package results settle. | Paired native comparisons, independent dispositions, final-state readback and claim-specific eligibility evidence. |
| [PM2-12](production-milestone-two/textbook-assessment-and-adoption.md#PM2-12) · Adopt selected scope | Authenticated source and compatible contracts for private staging; scoped PM2-08–11 evidence, applicable qualification and effect authority for selection | Privately staged derivations, separately qualified named workflows and verified selection where authorized; retry and preservation at the exact effect boundary. |

<a id="PM2-00"></a>

### PM2-00 · Freeze the comparable baseline

Reconcile the acquired target, release, and source identities with STATUS and DMA-13
at execution time. Start source-contract work, provider qualification, and independent
reference preparation on the available development foundation. Use cut 514 for source
preparation and cut 517 as the private M1 execution comparator where the selected
source and operation scope correspond. Use the best compatible retained comparator for
each release comparison, whether or not it was selected. Preserve historical WCE and NCE
comparators at their original extent and require exact source and semantic
correspondence before pairing. Close PM2-00 once the source opportunities can be
frozen without predictions and each comparator's available scope and outstanding
prerequisite are identified. PM2-12 separates private staging from evidence-based selection.
DMA-13 retains the grading and cutover obligations.

**Passed · 2026-11-08.** The [frozen baseline](../design_review/evidence/2026-11-08_pm2-foundation/README.md#frozen-development-baseline)
names the target, release, source product, exact reference and multi-sentence scopes,
and two v10 original-spelling controls. An explicit archived-release check passed.
Selection lookup refused because the project has no active release. The source-only
frame and private M1 comparator are available within their recorded scopes. Run 407
against sentence-only set 32 remains a refused grading attempt with no evaluation.
DMA-13 owns the assessment criteria for PM2-12.

## Foundation execution

The [combined design and target review](../design_review/reviews/design_review_pm2-foundation_2026-11-08.md)
accepted the private foundation scope against the refreshed audit at `9bdb0996e`.
The source projection and physical occurrence have separate proof requirements.
The existing task, result and host GPU owners retain their custody.

| Package | Current disposition |
| --- | --- |
| PM2-00 | Passed for the frozen development source and explicitly scoped comparisons. |
| PM2-01 | Exact maps, settled private outcomes and exact reuse are implemented. A differing original spelling and unattempted scope outcomes passed the native Reader controls. Integrated coverage and composed admission remain bounded by the [source contract evidence](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence). |
| PM2-02 | The runner verifies isolated runtime identity before scheduling or reusing a task. Native startup refusal, cancellation and exact recovery passed at recorded scopes; Maverick and Dipo also passed exact bounded fallback. Integrated operating qualification remains with [the source and runtime owner](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence). |

## Review disposition

| Package | Current execution disposition · 2026-11-09 |
| --- | --- |
| PM2-06 | Ordinary bounded parser modes remain selected for development. The [optional-mode disposition](production-milestone-two/linguistic-referential-discourse.md#PM2-06) records the observed gaps and the evidence needed to revisit them. |
| PM2-07 | Private CUDA execution and located typed reads are implemented. The v2 pair verified exact fair-coin normalization. On the competitive frame, both sets of d1 proposals recovered binomial and normal density, missed exponential density and declined the negative-binomial link. Broader interpretation and the like-for-like GLiNER/spaCy comparison remain open. |
| PM2-08 | The public condition and assumption contracts are deployed in development. Native textbook-style and business controls passed atomic admission, partial delivery, Reader, CLI, fresh MCP and exact detached verification. The real p289 variance statement passed native admission and agreed across all four consumers at run 477/cut 594. |
| PM2-09 | The protected competitive `/11` pair found all three expected definitions at rank 1 in both arms; the negative remained unlinked. Dipo context rendered on two cases and enriched detached replay passed. Keep `/10`; wider interpretation and book export remain open. |
| PM2-10 | Visual interpretation remains off. No selected case justifies an additional visual question. The [revisit trigger](production-milestone-two/retrieval-composition-and-delivery.md#PM2-10) requires a named material ambiguity on an authorized region. |
| PM2-11 | The prior protected d1 pair improved exact fair-coin normalization. The new competitive frame preserved all four protected retrieval outcomes and found no gain. Native d1 missed the exponential-density link in both arms. Native exact affine assessment passed. Wider interpretation remains open. |
| PM2-12 | Private full-book staging was attempted from authenticated Standard and Nemotron source. The [closure execution](#closure-execution--2026-11-09) owns the failed attempt, successor and remaining qualification. [DMA-13](domain-model-alignment_2026-11-08.md#dma-13) requires useful, source-faithful improvement for selection. Evaluations 42 and 43 remain regression evidence. Chandra is excluded. |

| Review opportunity | Proposed disposition and closure owner |
| --- | --- |
| PM2-R01 | The mapper, private adapter and Reader separate an exact selected projection from physical occurrence. [PM2-01](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence) owns the open typed refusal for an authenticated pin with invalid extent. Live scope controls passed at their recorded bounds; PM2-08 owns composed admission. |
| PM2-R02 | Isolated worker identity is checked before reuse. [PM2-02](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence) records scoped startup, recovery and fallback; assembled operating qualification remains open. |
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

The four initial profiles remain the milestone engineering target. Per-profile
obligations close on their own scoped evidence. Private staging uses the authenticated
full-book source and compatible execution contracts. [DMA-13](domain-model-alignment_2026-11-08.md#incremental-acceptance)
qualifies an increment for a named workflow only after paired evidence shows useful
source-faithful improvement and preserves material controls. Verify the operational
contracts for the profiles and consumers that workflow actually uses before authorized
selection. Staging, workflow qualification, selection and milestone completion are distinct:
selection does not close unrelated packages or imply complete knowledge coverage.
Milestone completion reconciles all scheduled obligations and the applicable final-source
evidence; conditional work can close with an explicit disposition at its own trigger.
The [assessment companion](production-milestone-two/textbook-assessment-and-adoption.md#PM2-12)
owns the exact selection and effect boundary.

## Extraction improvement disposition

These dispositions govern the amendments and their remaining qualification. The
source review owns the rationale and [deferred or low-fit capability families](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#capability-dispositions-beyond-the-recommended-first-slice). WCE03, NCE-M03/M06
and DMA-05/13 retain their existing authority and receipts.

| Review | Plan disposition and owner |
| --- | --- |
| [I01](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I01) | Exact affine carrier selection is implemented and both frozen locations reproduced. The [PM2-09 coverage gate](production-milestone-two/retrieval-composition-and-delivery.md#producer-coverage-before-ranking) now has bounded private definition and affine producer controls; wider ranking still needs an independently reviewed competitive inventory and exact carriers. |
| [I02](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I02) | Release-owned role payloads and the local attachment safeguard are implemented. The [definition annotation comparison](../design_review/evidence/2026-11-09_pm2-definition-prerequisite/README.md) recovered one sentence boundary but left the opening declaration unbound in that diagnostic. A later private chain passed transport; independent semantic and matched spaCy/HanLP comparisons remain open. |
| [I03](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I03) | [Exact GLiNER2 boundary diagnostics](../design_review/evidence/2026-11-09_pm2-gliner-boundary/README.md) ran the six retained windows. The target term was proposed but not decoded; one partial premise aligned only when supplied. No attachment was selected. |
| [I04](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I04) | The [same-question comparison](production-milestone-two/gliner-and-d1-interpretation.md#same-question-extraction-and-interpretation) still needs equivalent released operations: the exact overlapping d1 windows ask about passage function, quantity or host, while I03 asks about definition endpoints. |
| [I05](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I05) | Conditional [span modeling](production-milestone-two/learned-extraction-investigations.md#span-labeling-and-proposal-recall) for independently demonstrated label or proposal loss. |
| [I06](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I06) | Conditional [typed binding modeling](production-milestone-two/learned-extraction-investigations.md#typed-binding-scorer) for recurring errors with the correct candidates already present and usable supervision. |
| [I07](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I07) | [PM2-08 partial delivery](production-milestone-two/retrieval-composition-and-delivery.md#typed-partial-delivery) exposes distinct worklist outcomes. A missing or incompatible released local attachment contract preserves valid sibling frames and cues. The bounded p289 public and detached journey passed; broader cross-provider qualification remains open. |
| [I08](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I08) | Conditional [PM2-02 execution challengers](production-milestone-two/source-contracts-and-model-execution.md#conditional-context-and-execution) for measured operating need or a named scope-coverage loss. PM2-09 owns contextual retrieval recipes. |
| [I09](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I09) | Conditional [GLiNER2 specialization](production-milestone-two/learned-extraction-investigations.md#gliner2-specialization) after alignment, proposal and configuration remedies, with NCE-M03/M06 and PM2-07/11. |
| [I10](../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md#I10) | Outside PM2 beyond existing declared products and the alternate-vocabulary control. Revisit broader insight discovery only for a named consumer; a canonical linker needs stable independently owned IDs, scoped candidates, an explicit NIL outcome and separate qualification. |

## Structuring improvement disposition

**Plan amendment · 2026-11-09.** Consumes the
[structuring and DMA-13 review](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md)
at `09b172d32`. These are the current dispositions for that review; its IDs are
qualified by the review path and do not replace the earlier extraction-review IDs.

Start I01 and I02 alongside PM2-12 private staging preparation. I03 starts with
compatible retained observations. I04 and I05 isolate errors before changing a
shared consumer or fitting a model. Freeze PM2-11 references before inspecting
challenger results. Conditional context, numerical, runtime, proof and learned
changes are not prerequisites for staging or unrelated workflow selection.
The package owners below define inputs, decisions and evidence.

| Review recommendation | Disposition | Primary owner | Dependency and closure |
| --- | --- | --- | --- |
| [I01](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I01) | Implemented and scoped Tested | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#completed-empty-interpretation) | PM2-01/08 bindings and delivery; mixed/all-empty parity, native refusal and ordinary readback. |
| [I02](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I02) | Implemented and scoped Tested | [PM2-11](production-milestone-two/textbook-assessment-and-adoption.md#paired-state-readback) | Existing frozen grades; CLI and review views distinguish persistent failure, regression and non-comparability. |
| [I03](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I03) | Private facets implemented; qualification open | [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#compose-retained-parts) | PM2-03/04/07 retained evidence; independent role fidelity, partial delivery and public admission when claimed. |
| [I04](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I04) | Scoped diagnostic settled; incumbent retained | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#packed-boundary-and-attribute-comparisons) | PM2-11 independent frames; discriminate proposal, role and decoder loss. Learned modes stay conditional. |
| [I05](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I05) | Scoped diagnostic settled; incumbent retained | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#fixed-candidate-rendering-and-quantity) | Exact fixed inputs and PM2-11 grades; source-backed gain or retain incumbent. |
| [I06](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I06) | Conditional investigation | [PM2-09](production-milestone-two/retrieval-composition-and-delivery.md#discriminating-context-comparison) | PM2-05/06 mapped discourse and PM2-11 matched eligible frame; retain /10 unless benefit is demonstrated. |
| [I07](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I07) | Scheduled qualification | [PM2-12](production-milestone-two/textbook-assessment-and-adoption.md#named-workflow-qualification) | PM2-11 named workflow evidence on staged source, material controls, authorized target and operational checks. |
| [I08](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I08) | Scoped diagnostic settled; remedy conditional | [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#dependence-and-finite-support) | PM2-11 duplicate and independent-support controls; grouped treatment only for demonstrated effect. |
| [I09](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I09) | Conditional measurement | [PM2-02](production-milestone-two/source-contracts-and-model-execution.md#staged-workload-operating-comparisons) | PM2-08/12 own smaller exact proof; stage workload evidence first, select only on parity and measured benefit. |
| [I10](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I10) | Deferred outside immediate PM2 | [PM2-08 (revisit only)](production-milestone-two/retrieval-composition-and-delivery.md#artifact-identity-revisit) | Reviewed title/alias identity miss and a selected linkage question; no staging or selection dependency. |

### Structuring execution · 2026-11-09

The [execution evidence](../design_review/evidence/2026-11-09_pm2-structuring-execution/README.md)
records the current scoped work. The structuring review's dispositions above remain
the owner of the package boundaries.

- **I01/I02 · Implemented and scoped Tested.** Native d1 v3 run 481/cut 596
  retained provider `empty` with successful projection of one private unresolved
  question, no answer anchor or occurrence, and matching CLI and fresh MCP. The
  maintained-claim native and interpretation selection passed seven tests
  (`bdb7cf2b077a44bb9d243f3747069b7e`). The protected evaluator selection passed
  65 tests (`ba17547dabd14dda8f663dbf33ce65af`). Evaluations 39 and 41 still report
  two unchanged transitions and now also show two persistent unsupported cases.
- **I03 · Implemented private projections.** Returned GLiNER assertion associations,
  HanLP qualifier-host and modifier facets, and local Maverick candidate facets
  preserve exact members and producer attribution. The scoped composition tests passed
  57 (`14e1fc8a8aa44da590f446ffb0f7750d`), with 12 follow-up tests
  (`e19e1be54cdf4af09d747322000bfd15`). Independent workflow gain remains open.
- **I04/I05 · Diagnostics settled at their recorded scope.** Packed GLiNER scoring
  preserved authored score identity under reversal where admissible; protected
  source and native alignment guards refused other populations. The predicate
  attribute challenger did not recover the intended spans. The native d1 screen
  left the fixed-offer misses and lost the fair-coin control in the split quantity
  arm. Keep the incumbent. Neither result establishes a protected structure gain.
- **I06/I08/I09/I10 · Incumbents retained.** No new discriminating discourse
  frame or selected identity-linkage question was established. The repeated-support
  fixture exposes the effect of duplicate factors; no staged production decision
  is shown to consume them. Batching failed exact native output parity, and
  compression preserved exact offline proof with smaller transport only. Do not
  change numerical policy, retrieval defaults or logical proof completeness.
- **I07 · Private source-ready.** Run 478/cut 595 resolved all 29 views under
  the same authenticated Standard and Nemotron product. The [closure execution](#closure-execution--2026-11-09)
  records the outcome of derived run 482 and its successor. The named workflow
  comparisons and final applicable test union remain open.

### Closure execution · 2026-11-09

The [closure evidence](../design_review/evidence/2026-11-09_pm2-closure-execution/README.md)
records the exact attempts and preservation checks.

- **PM2-01/02 and PM2-03–05 · Scoped native verification.** Reader, CLI and
  fresh MCP agreed on p416 and p418 originals and bounded p151 manifest
  coverage. Parser run 485/cut 598 settled 17 successful, two empty, one
  limited, one ineligible and one unscheduled scope. Reader, CLI and fresh
  MCP agreed on all 11 worklist rows for the exercised view. This does not grade
  frames, referents, discourse structure or downstream usefulness.
- **PM2-07 · Implemented opt-in loss questions.** Release declarations separate
  the exact number, unit and source cue without changing ordinary requests.
  Native run 486/cut 599 kept fair-coin normalization and located the loss
  cue, but did not isolate amount or unit. Native GLiNER likewise failed
  to separate the amount and unit under the same questions. One protected definition case
  matched between GLiNER and d1; broader equivalence and an ordinary managed
  GLiNER arm remain open.
- **PM2-08/09 · Scoped implementation and preservation.** Interpretation
  preparation reuses repeated exact retained references within one read
  snapshot; coverage refuses a different task view. The historical cross-chapter
  citation remains readable; its detached export refused an incompatible
  archived source recipe. Run 486's exact loss proposal bundle verified
  offline at internal consistency standing. Current cross-chapter replay,
  detached worklist proof and the
  assembled ordinary release journey remain open. Keep `/10`.
- **PM2-11/12 · Private staging and source-only expectations.** The
  [source-only references](../design_review/evidence/2026-11-09_pm2-workflow-references/README.md)
  freeze five decisions with exact anchors, two readings and source-only
  adjudication. Protected arm registration and
  grading remain open. Run 482 settled 44 tasks and cancelled 14 after refusing
  the changed runtime; it has no completed cut and set 34 could not grade it.
  Private successor run 487 uses the same source with the newly admitted
  runtime. It is active without a cut. Finalize on settlement and grade set
  34 as a regression check; assemble the selected parser and interpretation
  dependencies separately.
  No workflow selection, live activation or retirement ran.

**Scoped tests.** The ordinary managed selection
`dd8884976e304744813c5346e649a96a` failed on a fixture's logical source key.
The exact retry `df94eeb83a4946108fe266e05ef1aab9` passed that case and
retained the opt-in provider block. With locked assets, the affected native
read and alternate-vocabulary parser controls passed in
`8ea5699ffa504463a59e34be051dac37` and `547a0868c4874807a7d36ac6d5952724`.
`uv run ci test coverage` accounted for 13 selected nodes with zero unresolved;
source differs by the fixture correction. `uv run ci check --only types` passed.
The assembled review and full applicable qualification remain open.

## Completion audit

**2026-11-09 · Inspected clean source `51b3c28de` (product changes at `fc72eb61f`).**
Two independent reviewers checked the claimed completion in PM2-00–12 against the
coordinator, its six companions, the accepted review dispositions and the actual
producer and consumer paths. Bounded successes inside open packages were in
scope. This audit supersedes the earlier account at `c86e5c90a`; original dated
receipts and the prior wording remain available.

**Implementation.** PM2-00 remains complete for the frozen development baseline:
cut 514 supplies source-only expectations and cut 517 is the completed private
M1 comparator over corresponding views. The refused sentence-only grade did
not create an evaluation. PM2-06 and PM2-10 remain complete as conditional
dispositions with optional modes off; their reopen triggers remain in force.
The initial provider routes, private products, scoped read surfaces and the
released condition/assumption admission path are implemented. PM2 as a whole
is not complete or selected.

| Owner | Retained closure and remaining obligation |
| --- | --- |
| PM2-01/02 · PM2-R01/R02 | Scoped native proof now covers original-versus-physical spelling, distinct worklist outcomes, exact HanLP reuse, missing-artifact refusal, provider-specific cancellation and recovery, and Maverick/Dipo fallback. Run 478/cut 595 preserves p416/p418 originals and p151 partial manifest coverage through ordinary reads; run 485/cut 598 confirms worklist parity for view 383. The latter does not prove detached scope custody: the exporter explicitly refuses a worklist selection. PM2-R01 still needs the [typed invalid-extent refusal](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence) before admission. Assembled operating and delivery qualification stays open. |
| PM2-03–05 · PM2-07 | Private payload validation, HanLP frames, Maverick mentions and clusters, Dipo trees, and the locked parser panel have scoped native receipts. The v3 d1 projector preserves completed provider `empty` as an unresolved question without an answer anchor; CLI and fresh MCP agreed on run 481. The new loss questions are opt-in. Scoped parser results and diagnostics do not close downstream semantic comparisons or the ordinary managed GLiNER arm. |
| PM2-03/07–09/11 · Witness/composition F01–F03 | F01 definition-chain and F02 ordered-affine witnesses have bounded private native and detached checks. F01 still needs independent semantic comparison; F02 preserves unlinked X and witnessed Z without establishing ranking or public admission. F03 is closed for the released condition/assumption contract: the textbook-style and business fixtures use the same native path, including failed-sibling preservation. The p289 result at run 477/cut 594 is valid on its own retained Standard source and protected set 18. Broader composition and qualification do not follow. |
| PM2-09 | The historical empty inventory and one-target preflight retain their scopes. Later protected evaluations 44/45 and 46/47 compared distinct registered literal and Dipo `/11` arms. Enriched detached replay passed on that frame, while the separate historical cross-chapter export refused its incompatible archived recipe. Regenerate the latter case on compatible source for current portable delivery. Keep the ordinary `/10` route. |
| PM2-11/12 · Witness/composition F04 | Persistent unsupported is now visible independently of transition counts; unrecorded causes remain unknown. Source-only workflow references are not protected grades. Request-local reuse and separately completed private parser/interpretation cuts do not establish ordinary assembled release delivery. Finish exact dependency assembly, the named paired comparisons, final applicable qualification and authorized selection through the existing owners. |

**Verification and qualification.** The fresh readbacks below inspect existing
results; no new provider campaign or broad product qualification ran. The
13-node closure union is bounded and differs by the reported fixture correction.
It does not replace the [earlier parser qualification record](../design_review/evidence/2026-11-08_pm2-parsers/README.md#development-deployment-and-qualification),
whose interrupted fault and other failed attempts keep their original standing.
The assembled review and applicable final-source union remain open.

| Readback · 2026-11-09 | Outcome |
| --- | --- |
| `uv run ci db status --maintenance --json`; `uv run ci release check --project nce-grinstead-snell-full-book --target development --json` | Database read `passed` at `semantic_pm2_condition_admission`. Active-release check `blocked`: the development project has no active release. |
| `uv run ci status 487 --project nce-grinstead-snell-full-book --json` | Readback `passed`: active, 35 of 58 derivation tasks done at inspection, with no completed cut. Run 482 remains failed with no completed cut. Successor finalization and set 34 grading were `not_run` in the audit. Even a completed successor would cover annotation and GLiNER extraction only. |
| `uv run ci eval operation-compare` for 38/40, 39/41 and 46/47 | Readbacks `passed`: one corrected probability case with definition preserved and loss still unsupported; two persistent unsupported host/referent cases; four unchanged supported retrieval outcomes. |
| `uv run ci review inspect --result 7d72cf7fc14e49c1a8bc2118492c3b8f --json` | `passed` for the retained loss bundle's selected-source closure. The earlier offline verification has internal consistency standing; it does not qualify the proposed amount or unit. |
| `uv run ci test coverage` for the four [closure receipts](#closure-execution--2026-11-09) | Readback `passed`; aggregate campaign status remains `failed`. The original failure and blocked retry remain visible; 13 selected nodes are covered, zero unresolved. |

**Demonstrated benefit.** The protected d1 pair establishes the bounded
fair-coin normalization correction to `0.125`. The definition case is
preservation; the later split-loss runs do not establish complete loss
structure. The protected retrieval comparison tied on eight eligible targets:
three correct targets ranked first in both arms, the negative stayed unlinked,
and both d1 arms missed the exponential-density link. This does not demonstrate
top-10 recall improvement or broader interpretation gain. The exact affine
check is a bounded mathematical analysis, separate from ordinary source fidelity.
Apply [DMA-13](domain-model-alignment_2026-11-08.md#incremental-acceptance) to
named workflow selection; an active or completed private run is not selection
evidence by itself.

### Post-audit execution checkpoint · 2026-11-09

- **Private book staging.** `uv run ci status 487 --project
  nce-grinstead-snell-full-book --json` read back an active supervisor, 55 of
  58 extraction tasks done and no completed cut. Leave the executing checkout
  and runtime inputs in place through managed settlement and finalization.
  The earlier run 482 refusal remains a terminal record. Set 34 grading and
  the assembled parser and interpretation journey are separate obligations.
- **PM2-R01 · Candidate ready off main.** Commit `bb035e57d` on
  `pm2/refusal` returns a structured refusal for invalid extents and canonical
  boundaries in the shared PM2 preparation path. The isolated native-backed
  CLI controls passed and checked that refusal creates no run or task.
  The installed command also returned `Pm2ScopeRefused` with
  `invalid_source_extent` for a retained pin. Integration on `main` waits
  for run 487 settlement and finalization under its pinned runtime.
  The committed-source managed rerun `1de606f99be44f75ab9e0e9c7c1e3281`
  passed both focused controls; its receipt is in the refusal worktree.
- **PM2-01/08 · Detached worklist candidate ready off main.** Commits
  `8c4e5b561` and `e1409ebac` on `pm2/detached-worklist` add exact-cut worklist export
  and shared coverage replay. Managed export and bound receipt inspection
  `c17fee3f00274e32b26aa11b97f40b80` passed for the 11 rows in run 485/cut 598,
  view 383. The earlier default-budget refusal is preserved; the successful
  export used a 384 MiB bound. The independent manifest receipt is needed
  for worklist completeness. The candidate does not establish assembled
  coverage or workflow qualification.
- **PM2-07/12 · Isolated product integration.** `pm2/integration` at
  `e46a8eabd` combined the typed refusal, detached worklist, exact ordinary
  scheduler dependency, and opt-in managed GLiNER passage-function producer.
  The targeted `uv run ci test` receipt `99b7271de688406a8a9de7c371106527`
  passed all 26 selected checks. `uv run ci schema check --domain statistics`
  compiled the integration branch; four calls to `ops.pdf_companion_body`
  remained unassessed in the static report. The ordinary scheduler now reads the
  declared producer in preparation and execution and keys reuse to the exact
  origin. F04 still requires the ordinary assembly to select archived PM2
  stages under their exact cut, question and runtime. The
  [native GLiNER control](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/gliner-worker-control.json)
  passed the real CPU worker and projection for the frozen definition passage.
  The [managed run 488/cut 600](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/managed-gliner-control.json)
  then settled one task under the isolated admitted release; Reader, CLI and
  fresh MCP delivered the same private `definition` choice. The [detached
  verification](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/managed-gliner-detached.json)
  passed against the held manifest digest. A test-only typing repair passed
  Pyrefly and its 10-test retry `274f3c939d364b90829e1fb3ac5ea62e`.
  The protected same-release comparison remains open.
- **PM2-09/11 · Exact source and comparator preparation.** The
  [Section 5.1 source read](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/cross-chapter-current-source.json)
  binds a corresponding cue and the section heading on the current integrated
  product. The cue is on a different native item; do not copy the historical
  citation identity. The [native heading inventory](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/cross-chapter-inventory-preflight.json)
  resolved a single exact Section 5.1 target among 33 headings from 29 views
  using completed cut 517 and the corresponding integrated cue. The source-only
  cut 595 cannot supply a completed structural dependency. In the [first ordinary
  replay](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/cross-chapter-current-replay-first.json),
  the annotation overlaps the citation extent but names a different block.
  The cue stays unsupported. Run 489 then exposed a separate failure to settle
  a contextual task with zero contributions. Commit `35f4c2eed` on the isolated
  integration branch records an empty result while retaining its operation
  report; 30 focused controls passed (`bfc014a77c72428da13e28e03383e340`).
  [Run 490/cut 602](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/cross-chapter-empty-retry.json)
  confirmed that outcome through the installed Reader path. The retained
  annotation's explicit native piece map proves that both citation tokens belong
  to the correct native item. The operator selected that mapping as the proof
  boundary for joined annotation blocks. The isolated `pm2/integration` at
  `9fbd5c7dc` implements it in scoped method `/12`, named-link `/4`, with native
  and detached checks preserving both identities. The [real-cue control](../design_review/evidence/2026-11-09_pm2-closure-execution/raw/cross-chapter-mapped-cue.json)
  recovered the exact `see` cue and `Section 5.1` on the retained item while
  `/3` remained unsupported. The 65 selected test identities are covered by
  `1df13f4a90f34676afd9cc1c200c54bb` and exact retry
  `4f83a2c163b54e85b8323c722562f0ba`; the original two formula failures remain
  visible. Native model candidate `d1eef86361c94c83810c48ad52d53f1d` was
  authored with rollback and registered as `semantic_pm2_named_pieces`.
  Development deployment, the full citation selection, and detached citation
  export remain open pending run 487 finalization.
  The [ordinary-baseline inventory](../design_review/evidence/2026-11-09_pm2-workflow-references/ordinary-baselines.md)
  found no exact completed ordinary predictions for the new definition and
  nested-condition cases. Reproduce the bounded incumbents on the same final
  release and selected views as the challengers before protected grading.

## Remediation execution

**2026-11-09.** The bounded [development execution](../design_review/evidence/2026-11-09_pm2-contract-remediation/README.md)
deployed typed parser payloads, verified scope outcome reporting on retained
Standard and Nemotron source, and verified exact HanLP reuse. An authored
native Reader fixture preserves exact selected spelling without minting an
occurrence. A cancelled scope remains distinct from a completed empty scope.
The shared local condition-to-host path has matched private textbook and
business controls. The v11 detached fixture verifies the retained frame input;
native paired ranking and d1 consumption were untested at that checkpoint. See
[the later competitive follow-up](#adoption-follow-up-execution).

**Formula and definition follow-up · 2026-11-09.** [PM2-11's exact affine assessment](production-milestone-two/textbook-assessment-and-adoption.md#exact-affine-qualification)
keeps mathematical agreement distinct from capture and source binding. The
[bounded HanLP comparison](../design_review/evidence/2026-11-09_pm2-definition-hanlp/README.md)
recovered the final parameter role only under a separately identified diagnostic layout.
The [ordered affine declaration probe](../design_review/evidence/2026-11-09_pm2-affine-ordered-source/README.md)
found the `Z` source pieces under the retained layout owner. Neither diagnostic
supplies a released witness or makes the retrieval inventory eligible.

At that checkpoint PM2-03 and PM2-07 needed a bounded layout and released
declaration chain. The [witness execution](#witness-and-runtime-execution)
records the later bounded private native and detached checks.
PM2-08 and PM2-11
need a qualified attachment and surviving useful part through the assembled
cross-provider Reader and fresh MCP journey, and independent same-question
comparisons. PM2-09 keeps ranking behind the definition inventory and fresh
affirmative source witness for the selected link. This limits the affected retrieval
scope. DMA-13 permits private staging of the full-book derivations and governs
selection of the supported workflows.

### Witness and runtime execution

**2026-11-09.** The [independent target review](../design_review/reviews/design_review_pm2_witness_composition_2026-11-09.md)
accepts the bounded implementation approach. F01 belongs to PM2-03/07/08 (definition
chain); F02 to PM2-09/11 (ordered declaration); F03 to PM2-08/11 (independent public
admission); and F04 to PM2-12 (exact dependencies and ordinary release assembly).
None of these findings is closed by the review.

The [native recovery probe](../design_review/evidence/2026-11-09_pm2-runtime-recovery/README.md)
refused startup with missing artifacts on all four locked CUDA profiles. HanLP,
Maverick and Dipo cancelled admitted native requests, reaped their workers, restored
the incumbent service and reproduced the earlier result on a fresh worker. Earlier
provider bounds and d1 cancellation keep their recorded scope. The probe does not
supply missing composed Reader or assessment evidence.

The [native scope fallback](../design_review/evidence/2026-11-09_pm2-scope-fallback/README.md)
retains the Maverick token-limited parent and both successful sentence-aligned children.
Dipo's two runs retain the distinct tokenizer and EDU limits and all successful leaf scopes.
Each fallback scope has a fresh input identity bound to its exact parent. This is bounded
runtime evidence; it does not qualify combined book interpretation.

The [declaration-chain replay](../design_review/evidence/2026-11-09_pm2-definition-chain/README.md)
reused the genuine retained HanLP reply after independently reconstructing its
exact repaired inputs. Both local parameter bindings and the unique constructed
antecedent were found; an alternate predicate was refused and the punctuation
preservation case was unchanged. The [native verifier](../design_review/evidence/2026-11-09_pm2-native-definition/README.md) passed isolated PostgreSQL checks on that input, then deployed at `semantic_pm2_definition_chain`.
A separately admitted private release settled HanLP at run 444/cut 546 and the exact
definition at run 445/cut 548. Native and detached readers accepted the exact chain
and refused the same altered binding. The native registry accepted one eligible target.

The [ordered witness guard](../design_review/evidence/2026-11-09_pm2-ordered-native/README.md)
accepts the exact retained Z population in a rollback transaction and rejects
altered anchors, omitted eligible rows and mismatched scope. The distinct /11 producer was
privately deployed at `semantic_pm2_ordered_witness`. It settled Z on run 443/cut 545
and preserved the unlinked X. The exact symbolic assessment passed on that retained
result. Historical source and witness identities are preserved. Definition admission
and ordered affine producer coverage have settled at their private scopes.

The [bounded retrieval deployment](../design_review/evidence/2026-11-09_pm2-bounded-retrieval/README.md)
leaves the ordinary `/10` schema and release intact. The two private binomial arms
found the same sole target at rank 1 and selected no retrieval edge. d1 consumed each
authenticated list and proposed that same target. The enriched result passed offline
verification. The affine retries passed the exact two-carrier read using a bounded
SQLAlchemy projection of the retained producer. Both arms preserved X and Z, with
no selected link to the unrelated sole target. A ranking gain needs a competitive
eligible inventory and independent same-question judgments. This bounded result did
not settle public partial delivery or qualification for selection.

The [private condition Reader](../design_review/evidence/2026-11-09_pm2-condition-composition/README.md)
resolves the directed qualifier and host under their exact retained scope. Controlled textbook
and business cases preserve competing frames and the cue when admission is refused. The
authentic textbook condition passed the existing CLI and fresh MCP journey. Public eligibility
requires an independently adjudicated role-bound statement and matching native admission.

**Scoped verification · 2026-11-09.** The managed `uv run ci test --json --` contextual
candidate, native workflow and detached replay selection passed 39 tests
(`36fcdd64387b47f8a05118d6786a5c28`). The broader affected selection passed 122 and
reported one blocked opt-in provider test (`1d4ead3890ee4c2db39fb6aec04da42b`). That
exact alternate-domain parser test passed with the locked model assets
(`c0c9d41241494580aff3d4fb7e63f9a4`). `uv run ci check --only types` passed.
These selections cover the stated changes; the applicable full qualification union
remains with PM2-12.

### Adoption follow-up execution

**Tested · 2026-11-09.** The [competitive retrieval frame](../design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md)
froze four exact source cases and eight reviewed competing targets, with separate registered
configuration hashes for the two `/11` arms. Protected evaluations 44 and 45 found no change;
the three supported targets ranked first in both arms and no negative-binomial edge was selected.
All eight native d1 requests ran. Both arms missed the exponential-density link, while recovering
the other two positive concepts and declining the negative. The enriched closure passed offline.
Keep `/10` as the ordinary route. The frame does not establish recall gain or wider interpretation
quality.

The same [preflight](../design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md#dma-13-origin-availability)
found no registered fit, calibration or final-assessment group in the milestone project.
The capture repairs recover bounded private candidates, with formula recognition still
unresolved. Under the revised [DMA-13 criteria](domain-model-alignment_2026-11-08.md#dma-13),
these are limits on the affected outputs and claims. Stage selected derivations from the
retained Standard and Nemotron source, and use the candidate to assess source fidelity and
workflow gains. Full-book derivation, activation and selection were `not_run`
in that preflight. See [current staging](#closure-execution--2026-11-09).

The [condition admission revision](../design_review/evidence/2026-11-09_pm2-adoption-preflight/records/pm2.condition-admission-development.json)
passed managed rollback authoring, registration and development deployment. Two isolated
native condition journeys passed (`8918df5ec9c940fcbe9e4021c88040eb`): textbook-style and
business inputs used the same atomic publication route, Reader, CLI, fresh MCP and exact
detached verification. They refused a stale or wrong protected case and altered or omitted
public proof rows, and preserved an independently admitted part with a failed sibling.
The [actual p289 journey](../design_review/evidence/2026-11-09_pm2-public-condition/README.md)
admitted the complete premise and lexical host at run 472/cut 586, with matching ordinary
Reader, CLI and fresh MCP. The archived v8 projection could not supply current detached proof.
A separate v10 view from the compatible retained Standard product (run 474/cut 588/view 410)
matched the complete independently reviewed passage and both physical role anchors without
recognition. Its public admission passed at run 477/cut 594 against protected set 18.
Ordinary Reader, CLI and fresh MCP agreed with offline `ci review verify` on the same
assertion and claim from exact-closure export `96b92b4b1d01478a90e52fe736a050b0`.
The original publication retains its original source custody. This closes F03 for the
released condition and assumption contract; it supplies no book-wide qualification.

**Scoped regression · 2026-11-09.** `uv run ci test --json --` on the native operation
assessment, opt-in M1 capture and scoped relation selections passed 41 tests
(`582764e1c2cb4ec0beedde6e1decd8ab`) after the managed revision registered.
`uv run ci check --only types` and `uv run ci check --only lint` passed. The complete final
qualification union was `not_run` in that execution.
