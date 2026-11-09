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
| PM2-12 | Stage selected full-book derivations privately from the authenticated Standard and Nemotron source. [DMA-13](domain-model-alignment_2026-11-08.md#dma-13) requires useful, source-faithful improvement and operational qualification before selection. Evaluations 42 and 43 remain regression evidence. Full-book staging and selection have not run; no new recognition is indicated. Chandra is excluded. |

| Review opportunity | Proposed disposition and closure owner |
| --- | --- |
| PM2-R01 | The mapper, private adapter and Reader separate an exact selected projection from physical occurrence. [PM2-01](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence) owns remaining coverage-state qualification. PM2-08 owns the composed admission journey. |
| PM2-R02 | Isolated worker identity is checked before reuse. [PM2-02](production-milestone-two/source-contracts-and-model-execution.md#foundation-execution-evidence) owns the remaining per-profile operating qualification. |
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
| [I01](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I01) | Scheduled repair | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#completed-empty-interpretation) | PM2-01/08 bindings and delivery; mixed/all-empty parity, native refusal and ordinary readback. |
| [I02](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I02) | Scheduled repair | [PM2-11](production-milestone-two/textbook-assessment-and-adoption.md#paired-state-readback) | Existing frozen grades; CLI and review views distinguish persistent failure, regression and non-comparability. |
| [I03](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I03) | Scheduled composition | [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#compose-retained-parts) | PM2-03/04/07 retained evidence; independent role fidelity, partial delivery and public admission when claimed. |
| [I04](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I04) | Bounded investigation | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#packed-boundary-and-attribute-comparisons) | PM2-11 independent frames; discriminate proposal, role and decoder loss. Learned modes stay conditional. |
| [I05](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I05) | Bounded investigation | [PM2-07](production-milestone-two/gliner-and-d1-interpretation.md#fixed-candidate-rendering-and-quantity) | Exact fixed inputs and PM2-11 grades; source-backed gain or retain incumbent. |
| [I06](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I06) | Conditional investigation | [PM2-09](production-milestone-two/retrieval-composition-and-delivery.md#discriminating-context-comparison) | PM2-05/06 mapped discourse and PM2-11 matched eligible frame; retain /10 unless benefit is demonstrated. |
| [I07](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I07) | Scheduled qualification | [PM2-12](production-milestone-two/textbook-assessment-and-adoption.md#named-workflow-qualification) | PM2-11 named workflow evidence on staged source, material controls, authorized target and operational checks. |
| [I08](../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I08) | Diagnostic; numerical change conditional | [PM2-08](production-milestone-two/retrieval-composition-and-delivery.md#dependence-and-finite-support) | PM2-11 duplicate and independent-support controls; grouped treatment only for demonstrated effect. |
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
  the same authenticated Standard and Nemotron product. Derived run 482 is
  active under the current runtime. At the 2026-11-09 handoff, `uv run ci status
  482 --project nce-grinstead-snell-full-book --json` reported 39 of 58 derivation
  tasks done, one running and 18 pending, with no completed cut. Finalize the
  private run after settlement and grade the existing set 34 as a regression
  check. No Chandra, new recognition, activation or selection ran. The named
  workflow comparisons and final applicable test union remain open.

## Completion audit

**2026-11-09 · Inspected source `c86e5c90a`, clean before audit edits.** Two
independent reviewers traced the claimed results in PM2-00–12 against the
coordinator and all five companions, including bounded results in open
packages and the decisions to leave optional modes off.

The private development slice delivers native products from all four providers,
exact replay at the tested scopes, and inspectable unresolved interpretations
alongside retained useful parts. PM2-00 is complete for the frozen development
baseline. PM2-06 and PM2-10 meet their conditional disposition criteria; their
revisit triggers and the separate p151 manifest control still apply. PM2-01
and PM2-02 retain the Reader coverage and isolated runtime identity gaps
above. The private parser products are implemented. Release-owned payload
validation, bounded parser controls and the intended composed admission
journeys remain open at their existing owners.

The established semantic gain is exact normalization of the fair-coin
probability as `0.125` under v2 on the paired frame. The definition control held;
roulette loss, condition host and local referent remained unsupported. That
does not qualify wider interpretation, retrieval, or selection. The native
repair exercised in run 438/cut 539 uses a shared SQLAlchemy Core lookup for
the exact dependency, parsed by pglast and bound by PostgreSQL through the
existing candidate workflow. It restored the bounded producer
journey; it did not supply eligible definition targets or the missing affine
carriers. v10 remains the current Phase 0 route. The richer v11 recipe has no
paired ranking result or exact detached replay.
[Paired interpretation](../design_review/evidence/2026-11-09_pm2-interpretation-pair/README.md) ·
[Retrieval and native repair](../design_review/evidence/2026-11-09_pm2-adoption/README.md)

The following readbacks ran on 2026-11-09:

| Check | Outcome and boundary |
| --- | --- |
| `uv run ci db status --maintenance --json`; `uv run ci source views 404 --json` and `uv run ci source views 407 --json` | `passed`: development is at `semantic_pm2_def_scope_vars`; the two runs resolve identical inventories of 29 views and the same integrated source. Cut 514 is the source-only reference; cut 517 is the completed private M1 comparator. |
| `uv run ci release check --project nce-grinstead-snell-full-book --target development --json` | `blocked` as expected: the development project has no active release. |
| `uv run ci contributions list` with run 416/task 2079 and run 431/task 2128; `uv run ci review inspect --result dddb654819ed4e73a31a733ad17d377d --json` | `passed`: the exact retained HanLP and d1 tasks remain readable as private contributions. The detached quantity resolves one exact selected-source closure. |
| `uv run ci eval operation-compare --baseline 38 --revised 40 --project nce-grinstead-snell-full-book --json`, and the same command for 39/41 | `passed` as readbacks: one corrected result, one preserved supported result and three unchanged unsupported results in the protected pair. |
| `uv run ci test --json --` scoped to `test_structural_source_annotations.py::test_named_rule_availability_is_preserved_per_variant` and `test_typed_realization.py::test_generated_surface_is_current_and_attaches_existing_table` | `passed`: all three cases from the parser retry's recorded ordinary failures pass at this baseline, in managed result `6136a128024d42268e5e5a5e1c415dc8`. |
| `uv run ci test coverage` for the retained parser campaign and scoped retries | `failed`: the original fault receipt has empty files after a restart. The original campaign and exact ordinary retry retain their failed outcomes, and the later fault, opt-in and 78-test native repair results retain their narrower scope. The passing three-node rerun does not establish the required final-source union. [Parser qualification history](../design_review/evidence/2026-11-08_pm2-parsers/README.md#development-deployment-and-qualification) |

The audit's remaining work is carried forward in the [remediation execution](#remediation-execution)
and the package owners above.

Reuse the authenticated Standard and Nemotron source to stage selected derivations
across the book, then qualify the workflows proposed for selection. The current
evidence supplies no reason to repeat recognition;
Chandra stays excluded. PM2-12 also requires the assembled review, final
applicable functional, native and repository qualification, and the authorized
selected-reader journey. Fresh provider campaigns, the full-book derived run,
and activation and selection were `not_run` in this audit.

## Remediation execution

**2026-11-09.** The bounded [development execution](../design_review/evidence/2026-11-09_pm2-contract-remediation/README.md)
deployed typed parser payloads, verified scope outcome reporting on retained
Standard and Nemotron source, and verified exact HanLP reuse. An authored
native Reader fixture preserves exact selected spelling without minting an
occurrence. A cancelled scope remains distinct from a completed empty scope.
The shared local condition-to-host path has matched private textbook and
business controls. The v11 detached fixture verifies the retained frame input;
native paired ranking and d1 consumption are still untested.

**Formula and definition follow-up · 2026-11-09.** [PM2-11's exact affine assessment](production-milestone-two/textbook-assessment-and-adoption.md#exact-affine-qualification)
keeps mathematical agreement distinct from capture and source binding. The
[bounded HanLP comparison](../design_review/evidence/2026-11-09_pm2-definition-hanlp/README.md)
recovered the final parameter role only under a separately identified diagnostic layout.
The [ordered affine declaration probe](../design_review/evidence/2026-11-09_pm2-affine-ordered-source/README.md)
found the `Z` source pieces under the retained layout owner. Neither diagnostic
supplies a released witness or makes the retrieval inventory eligible.

PM2-03 and PM2-07 own the next definition-target work: qualify a bounded layout
and released declaration chain with equivalent native and detached checks.
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
workflow gains. Full-book derivation, activation and selection remain `not_run`.

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
