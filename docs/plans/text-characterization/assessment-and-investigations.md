# Independent assessment and conditional investigations

**Proposed · 2026-11-10.** This companion develops [TC-10](#TC-10) and the bounded
[TC-I01–TC-I09](#conditional-investigations) branches of the
[text-characterization coordinator](../text-characterization_2026-11-10.md).
The coordinator owns package state, scheduled dispositions and combined completion. The
[model and retention companion](model-and-retention.md) owns the enriched-document contract;
[contextual characterization](contextual-characterization.md) owns TC-07/08 task behavior.
This document supplies the assessment route and decisions that can change implementation,
without establishing another status ledger, evaluator database or mandatory experiment campaign.
It consumes [review O07 and feature dispositions](../../functional_reviews/text-characterization_2026-11-10.md#O07).
All new-task efficacy and benefit claims remain Proposed.

## Foundation assessment and preserved boundaries

Current [operation assessment](../../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py)
already distinguishes `OperationEvaluationFrameV2` source opportunities from frozen output-first
contribution membership. It retains source groups, exposure, exact questions/rubrics, source pins,
source state and independent expected structures. `OperationCase` can assess one narrow facet
with permissible alternatives and endpoint-role expectations. `_matches` compares declared
fields; it does not know the new characterization graph's semantics. Extend owned projections
and independent reference expectations for that graph rather than interpreting a successful
existing record grade as a role/scope/choice grade.

The separate [structural assessment source](../../../python/corpus-structure/src/corpus_structure/evaluate/structural_assessment.py)
already models multi-source groups and independently authored path expectations, but its operation
enumeration is finite and names current semantic products. It is not an existing universal
characterization evaluator. Reuse its source-group custody where a contextual question needs
multiple source pieces; extend an owning frame/product protocol deliberately when the current
one cannot express the question. Do not mislabel contextual annotations as a dossier or
`definition_components` merely to enter a current protocol.

[D7](../../design/D7-evaluation-goldens-outer-loop.md) and
[ADR-0070](../../adr/0070-full-book-method-development.md) govern the shared full-book development
population, source-only reference authoring and exposure provenance. Use all 518 physical pages
of Grinstead–Snell for development, debugging, regression and assessment; a newly imposed
held-out population or multiple-origin minimum is not a prerequisite. Protected reference custody
still prevents reference answers from entering production inference. Preserve existing historical
labels and their grain; a changed question needs suitable fresh operation-specific references,
not a renamed historical record answer. The authored second-vocabulary control exercises reusable
language behavior without claiming a second corpus qualified.

The focused foundation judgment is to retain source/reference custody, explicit native operation
identity and independent expected answers, while changing their consumed characterization
contracts. This serves FP-04/A2 and CI-01–04/11/12: the evaluator challenges the meaning rather
than recomputing the producer. FP-07/A4 and heuristics H2/H5/H12/H15/H20 favor shared source
packets, prepared native resources and selective read projections over a new task/store per facet
or repeated whole-book materialization. Source/output scopes and actual family outcomes remain
visible even when a compact report is requested. This is focused plan-authoring reasoning, not
a design-audit verdict on the enclosing evaluation subsystem.

<a id="TC-10"></a>

## TC-10 · Assess characterization independently at the operation grain

### Inputs, product and dependencies

Input consists of a declared question/rubric, immutable source scope/hierarchy and source-only
opportunities, followed independently by exact producing operation/layer identities and retained
outputs. Output is the existing managed assessment product extended with characterization facets,
source/output coverage, error attribution and exact evidence bindings. Assessment writes no
source interpretation, accepted knowledge or production selection. TC-11 consumes it for an
assembled adoption decision; TC-I branches consume diagnosed gaps for a bounded next choice.

| Dependency | Readiness and consequence |
| --- | --- |
| TC-01 | Question, occurrence, role/operator/choice and coverage meanings are declared. This permits reference protocol and rubric authoring before the producer exists. |
| TC-02 | Exact layer reads, source/analysis identities and replay codecs are available. Native/semantic retained fidelity can be assessed without rerunning inference. |
| TC-03 | Authenticated source/hierarchy and native evidence scope are available. Freeze source opportunities independently of emitted candidates and retain unalignable source regions. |
| TC-04–TC-06 | Their actual positioned/formal/construction/symbolic outputs are available at the assessed scope. Each can enter independent assessment when ready; the whole series need not finish first. |
| TC-07/TC-08 | Actual contextual/native question outputs, examined context and family outcomes are available. Candidate-centered assessment binds the precise ordinary candidate list. |
| TC-09 | A migrated consumer is available for the corresponding integration journey. Local characterization assessment can start earlier; consumer fidelity remains an assembled obligation. |

### Source-first and output-first assessment

Freeze source-first frames from authenticated source before looking at producer outputs.
Describe the opportunity in source terms: original ordered extents, hierarchy/context, facet,
source state and what was inspected. A clause rejected by token alignment or construction
recognition remains an opportunity. Keep stated, unstated, unresolved, uninspected and
inapplicable states distinct where the owning frame supports them; extend that contract where
needed rather than coerce inapplicable to false. Independently authored expected structures
can permit several readings or partial orders. They do not need one forced universal logical form.

Freeze output-first membership from exact retained annotations/assertions/groups and operation
identities. Ask whether each proposal's location, role, support, scope and claimed coverage are
valid. Extra unsupported structures and false unique resolutions need this direction; source-first
capture alone does not penalize every false positive. Source-first opportunities never acquire
an output identity just because a producer later emits a candidate. Keep the two denominators
and their conclusions separate.

Use fresh independent source-only authoring and adjudication through existing A/B/C custody
where required by the selected operation protocol. Supply original source and question context,
not the current producer's answer or packed tree as a reference template. Source-only authors
may inspect source/hierarchy; output-first support authors necessarily see the selected output,
and that exposure is recorded. Reuse a compatible reference only when source and question meaning
remain unchanged under the existing applicability contract. Preserve corrections and failed or
interrupted records; do not rewrite a prior answer to match a new producer.

Production task compilation, candidate nomination, retrieval and provider prompts cannot read
protected reference labels. Development knowledge/exposure is recorded honestly under the shared
book policy; it does not justify embedding page IDs, expected terms, gold candidates or
adjudicated host choices in production. Reviewed supplied spans/mentions/EDUs are diagnostic
ceilings with explicit exposure, not ordinary discovery quality.

### Facets and discriminating expectations

| Facet | Independent question and important countercase |
| --- | --- |
| Source/token/constituent capture | Did the operation retain the exact required occurrence and actual membership? Repeated spelling, a protected formula/reference atom, discontinuity and a parser-unmatched source clause expose first-match and bounding-box errors. |
| Native evidence fidelity | Are native labels, endpoints, root conventions, continuation/reference arguments, scores and availability preserved? UD/PTB/PropBank/spaCy schemes cannot be scored as synonyms. A valid projected structure does not prove the native prediction correct. |
| Predicate/role correctness | Are verbal/copular/nominal/adjectival predicates and their participants supported, and are local/inherited/implicit/unresolved roles distinguished? A passive subject is not automatically an actor; collective and distributive readings differ. |
| Operators and scope | Are negation, modal force, quantifiers, restrictor/body, attribution and nested targets represented? “Not every trial succeeds” challenges a sentence-wide polarity flag; reported necessity challenges author-endorsement conflation. |
| Attachment and contextual binding | Are qualifier hosts, antecedents, source-local binder identity, speaker/content and heading/list inheritance supported at the declared scope? A nearer wrong mention, intervening quotation and cross-section unexamined pair discriminate unsupported propagation. |
| Choice compatibility | Are correlated alternatives and prerequisites preserved without inventing combinations? Compare a permitted pair and an impossible crossed pair with the same local labels. Unknown compatibility is not coexistence. Source “or” must remain a semantic operator, separate from analytical uncertainty. |
| Provider question semantics | Did the actual new source-first task or frozen-candidate question run, with exact options and allowed source witnesses? Distinguish absent cue, insufficient source, none of these, missing candidate and policy withholding. A probability/event or category alone is not located semantic support. |
| Coverage and failure | Are selected families attempted over applicable book scopes, and are failed/limited/unattempted/unresolved outcomes retained? A completed empty answer can coexist with a source-first miss; an unavailable required provider cannot become a pass. |
| Retained and consumer fidelity | Do the same exact layer/source/choice identities reach native reads, CLI/MCP, exports and detached replay without fresh inference? A roundtrip must preserve memberships and support; a successful admitted record cannot establish all its component scopes. |

These facets define meaningful questions, not a requirement to generate every combination of
examples. Select revealing source opportunities and deliberate invalid controls at the owning
package. Preserve useful mathematical/formal reference cases independently of the new producer.
Grammar-generated strings (`hypothesis.extra.lark.from_lark`) can challenge recognition/positions;
they do not author correct natural-language roles or realistic ambiguity frequencies.

### Implementation and library route

Extend existing assessment projections to read TC-02 layer products, typed roles/operators,
choice dependencies and family coverage. Expose bounded reports by managed result ID through
the existing `ci` custody. A new missing view needed to answer a routine assigned question is
repaired in its owning CLI layer; exporting bulk payloads to scratch files is not the intended
inspection route. Keep actual source scope visible when reports filter the displayed output.

For compatible native tasks use spaCy `3.8.18`
[`Scorer`, `score_tokenization`, `score_spans`, `score_cats`, `score_deps`](https://spacy.io/api/scorer).
They supply task-specific native scores, not contextual operator/choice evaluation. Preserve
unalignable reference coverage and proposal recall rather than scoring only surviving spans.
Independently authored semantic structures assess the missing scope, binding and compatibility
meanings. Match a rubric-declared graph projection with explicit source/role identities;
do not demand irrelevant incidental node order, and do not normalize away a meaningful direction
or dependent choice. Native scorer agreement and semantic correctness remain separate claims.

If a TC-I branch adopts training, use spaCy `Example`/`Alignment`, `Corpus`/`JsonlCorpus` or
registered readers and `DocBin` exchange under the existing artifact owner:
[Example](https://spacy.io/api/example), [Corpus](https://spacy.io/api/corpus),
[DocBin](https://spacy.io/api/docbin). Train and score against actual atom-preserving runtime
segmentation and ordinary proposal generation. Gold preprocessing or reviewed candidates must
not silently replace that path. Entity `missing`/`outside`/`blocked`, exclusive textcat negatives,
multilabel masking and spancat candidate supervision have different contracts; sparse positives
are not universal negative labels. See the
[supervision discovery](../../library_leverage/libraries/text-characterization/models-supervision-and-evaluation.md#supervision-and-evaluation).
Native scoring/threshold tools may serve an actual selected task; the plan introduces no
universal numerical cutoff, mandatory score improvement or benchmark campaign.

### Acceptance and evidence boundaries

Unit qualification must show that independent expectations discriminate wrong role, wrong scope,
crossed choice, missed opportunity, unexamined crossing and corrupted retained identity. Codec
roundtrips establish preservation; they do not establish source interpretation accuracy. Mechanical
production validators can enforce invariants at the owning boundary, while independently authored
semantic expectations challenge those invariants and outputs. Do not call the producer again to
generate expected roles or support.

Actual native qualification runs each selected provider/family on authenticated applicable book
scopes and records its exact runtime/artifact/task/source identity and terminal outcome. Keep
the newly defined modal/scope/attribution/function and candidate host/referent questions separate
from older finite domain questions. Separate ordinary prediction from supplied-mention/EDU/span
diagnostics, raw from reconstructed input, and native errors from projection errors. Mocked
responses qualify only local compilation/projection behavior. A missing provider/device/artifact
is **blocked**, with that prerequisite named, for the affected native obligation.

Assess book source coverage across all 518 pages and the actual selected natural sections;
report family applicability and incomplete scopes before efficacy claims. Compare revisions on
the same source opportunities/question semantics, or state the unmatched scope explicitly.
No page-dispatch rules or full-record gate may hide missed local characterizations. TC-11 owns
final applicable functional/provider/nonfunctional union, consumer cutover and adoption. Required
integrated `uv run ci test` and `uv run ci check` wait for complete functional scope under the
repository's timing rules; focused package checks run during implementation. No new tests or
native commands are run by this plan-writing package.

<a id="conditional-investigations"></a>

## Conditional investigations · baseline first, triggered branches

The selected baseline remains the default. Triggered decisions can run as soon as their actual
inputs are available; completion of the whole baseline is not a barrier to a consequential inquiry.
The following branches preserve **every Conditional capability** in the review's feature
dispositions, including the conditional cases embedded in otherwise Selected rows. Supporting
APIs and rejected uses remain available guidance, not mandatory investigations. Each branch
names a concrete trigger, decision, settling evidence and affected TC packages. A trigger is a
required capability gap, justified replacement or actual operational/delivery need, not the
mere existence of an API. The default remains unchanged until a branch selects and qualifies
a replacement or addition. The coordinator records the disposition in the owning new plan;
there is no second findings ledger here.

An investigation consumes the diagnosed source/task cases and current retained ordinary outputs.
It produces a bounded decision with capability/support conditions and exact artifact/configuration
changes if selected. It does not mutate native source, erase rival evidence or silently widen the
full profile. Source inspection can settle feasibility/fit; use a bounded native comparison or
experiment only where the decision depends on actual behavior. Missing present gold is an
annotation investment question, not an automatic reason to reject a useful task. No invented
numeric threshold or general performance campaign is required.

<a id="TC-I01"></a>

### TC-I01 · Token boundaries, morphology and learned lemma alternatives

Consumes TC-03's exact source/atom map, required boundary/form population and independent
miss/error cases. Produces a selected token/morphology recipe or a reason to retain the current
one. A changed published tokenization creates a new analysis identity and regenerates all
affected token-bound products; no post-publication retokenization or approximate source rewrite.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| Whole `Tokenizer` replacement | Required technical/noisy boundaries cannot be expressed adequately with selected prefix/suffix/infix rules, `token_match`, `url_match` and `add_special_case`. Choose one replacement only if it preserves required atoms and coordinates. | Inspect `Tokenizer.explain()` and independently specified missed boundaries, then actual replacement projection on those cases; TC-03, downstream TC-04–TC-10. [Tokenizer API](https://spacy.io/api/tokenizer), spaCy3.8.18 baseline. |
| `DependencyParser(learn_tokens=True)` | Recurring useful population needs learned **merging** beyond stable exceptions. Decide whether supervised merging is the actual gap rather than splitting/general segmentation. | Aligned boundary supervision and native missed/negative atom controls establish merging behavior and actual downstream effect; TC-03/05/10. [Parser API](https://spacy.io/api/dependencyparser). |
| `morphologizer` alternative | Current tagger/AttributeRuler mapping lacks required morphology/quality on an identified construction population. Compare replacing the relevant recipe rather than add an automatic duplicate pass. | Independently labeled morphology and dependent-construction cases, source/annotation availability and native output; TC-03/05/10. [Morphologizer](https://spacy.io/api/morphologizer). |
| `trainable_lemmatizer` / `EditTreeLemmatizer` | Required recurring forms remain inadequately handled by lookup/rule modes. Decide whether learned edit trees plus annotation acquisition justify replacement. | Native original-form/lemma examples and downstream lexical/construction distinctions, runtime prerequisite/alignment checks; TC-03/05/10. [EditTreeLemmatizer](https://spacy.io/api/edittreelemmatizer). |
| Experimental character tokenizers (`experimental_char_tagger_tokenizer`, `experimental_char_ner_tokenizer`, `char_pretokenizer.v1`) | Useful boundary population requires learned character segmentation that the preceding routes cannot adequately express. Choose compatible isolated/adapted runtime or retain baseline. | Exact character predictions projected to protected atoms/source; package/model/runtime compatibility and independent boundary cases. Published spacy-experimental0.6.4 requires spaCy<3.8, so root3.8.18 use is unqualified; TC-03/10 and TC-I04. [Compatibility source](https://github.com/explosion/spacy-experimental/blob/v0.6.4/requirements.txt), [tokenizer family](https://github.com/explosion/spacy-experimental#trainable-character-based-tokenizers). |

<a id="TC-I02"></a>

### TC-I02 · Learned span boundaries, linguistic labels and passage functions

Consumes TC-05/07/08's actual candidate, label and scope gaps plus TC-10's independent cases.
Produces one explicit task/proposal realization, preserving ordinary source-first coverage and
original evidence. Span and passage predictions remain proposals under TC-01, not universal
correlated readings.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| `ner` / `EntityRecognizer` | A conventional non-overlapping entity taxonomy has useful missing coverage/quality, or a justified replacement task, beyond GLiNER/current providers. Choose its finite taxonomy and consumer; retain overlapping layers elsewhere. | Actual native boundary/label cases including nested/repeated competitors and negatives, compared on same question; TC-03/08/10 and TC-09 consumer. [EntityRecognizer](https://spacy.io/api/entityrecognizer). |
| `SpanFinder` | Required clause/term/qualifier **boundary** population is missing from rules, syntax, grammar and selected providers. Choose whether learned boundary nomination is the missing capability. | Independently frozen source spans, ordinary `predict()` start/end evidence, proposal recall and actual candidate amplification; keep length/threshold policy explicit; TC-05/08/10. [SpanFinder](https://spacy.io/api/spanfinder). |
| `spancat`, `spancat_singlelabel`, full candidate score matrix | Required overlapping modal/scope/function/span labels lack adequate existing realization, or a coherent trained replacement is preferable. Select label semantics, exclusive/multilabel output and proposal path. | Ordinary versus supplied candidate comparisons distinguish boundary from label loss; retained `predict()` candidates/full scores versus filtered `SpanGroup.attrs["scores"]`; independent source/scope cases; TC-05/07/08/10. [SpanCategorizer](https://spacy.io/api/spancategorizer). |
| `textcat`, `textcat_multilabel`, `Doc.cats`; new function labels/models | Current GLiNER/d1/Dipo/constructions lack a required region-level distinction. Decide whether a passage classifier or taxonomy extension supplies it, retaining located support separately. | Same source/function question, independent overlapping-function references and unresolved/negative cases; actual runtime context, correct exclusive/multilabel supervision; TC-07/08/10. [TextCategorizer](https://spacy.io/api/textcategorizer). |
| Learned contextual modal/evidential distinctions | Baseline d1 and construction/native evidence cannot distinguish a required force/type on identified source cases. Decide a span/passage task here or structured task in TC-I03; do not replace the requirement with cue detection. | Independent force **and target/scope** expectations on ambiguous and unambiguous cues, with source-only baseline comparison; TC-05–TC-08/10. [Review N3 disposition](../../functional_reviews/text-characterization_2026-11-10.md#feature-dispositions). |
| Implicit-role/ellipsis prediction | Required inherited/gapped binding is not expressed by selected providers/constructions. Decide whether existing heads can express the task or a structured TC-I03 head is needed. | Exact overt versus implicit/unresolved roles, collective/distributive/shared-argument and wrong-binding controls; TC-05/06/07/10. No positive label authorizes inventing an unsupported participant. |

If selected, use native preset/custom suggesters to union named rule/syntax/grammar nominations
with evidence identity. Keep proposal and classified keys distinct because `set_annotations()`
overwrites its group. Candidate recall bounds classification recall; independent label scores
do not supply complete-reading compatibility. spaCy3.8.18 is the baseline; experimental span
APIs and selected new model artifacts require actual native qualification.

<a id="TC-I03"></a>

### TC-I03 · Encoders, structured heads and adaptation

Consumes an adopted prediction task from TC-I02 or an independently justified structured gap.
Produces a pinned model/task training and inference realization using native lifecycle, with
independent assessment and ordinary runtime proposals. It does not select an encoder merely
because contextual interpretation is difficult.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| Floret `Vectors(mode="floret")` | An adopted task needs technical/subword representation coverage unavailable from selected resources. Choose a specific resource and downstream use. | Resource/model compatibility and independent affected task cases, not OOV counts alone; TC-03/08/10 or adopted head. [Vectors](https://spacy.io/api/vectors#init). |
| Custom `BaseVectors` | A selected useful resource cannot be served adequately by dense/floret storage. Choose a backend only for that concrete resource. | `get_batch`, device/ops conversion and persistence contracts plus actual task integration; TC-03/08/10. [BaseVectors](https://spacy.io/api/basevectors). |
| Curated/HF transformer encoders/listeners/windows | An adopted contextual task needs a representation better suited than current encoders. Compare compatible selected model/runtime and window semantics; longer input alone is insufficient. | Selected package/model revision, Python/device compatibility, exact subword/atom/window reconciliation and independent target task cases; TC-03/07/08/10. [CuratedTransformer](https://spacy.io/api/curatedtransformer), [Transformer](https://spacy.io/api/transformer). |
| `TrainablePipe` lifecycle/custom structured head | Required scope/modal/ellipsis/joint-reading output lacks adequate realization or a trained replacement is preferable, and simple span/passage labels cannot express its edges/correlations. Choose explicit output, loss and scoring. | Native `predict`, `set_annotations`, `get_loss`, `initialize/update/score` integration and independent role/scope/choice cases; TC-05–TC-08/10. [TrainablePipe](https://spacy.io/api/pipe); Thinc/`PyTorchWrapper` are supporting implementation options, not mandatory new runtime. |
| Orthographic/custom augmentation | An identified technical variation can be generated while preserving label meaning. Select only those transformations, repairing alignment when boundaries change. | Inspect changed source/labels and independent authentic target cases; synthetic efficacy is not authentic coverage; adopted training packages/TC-10. [Augmentation](https://spacy.io/usage/training#data-augmentation). |
| `PretrainVectors` / `PretrainCharacters` | An adopted supervised task has a representation mismatch that unlabeled domain adaptation could address. Choose objective/corpus and downstream initialization, or retain pretrained baseline. | Version-relevant native configuration, actual task comparison and preserved reference exposure; pretraining supplies no semantic gold; adopted head/TC-10. [Pretrain CLI](https://spacy.io/api/cli#pretrain), discovery's installed3.8.18 correction covers both objectives. |

For a selected head, first consider compatible `Tok2VecListener` sharing already demonstrated
by the installed English parser/tagger rather than a private encoder per property. Source/freeze/
annotating-component and listener-replacement configuration must preserve intended training
updates: a frozen head can still consume changing upstream weights. `Example`/readers, native
scorers, ordinary proposal paths and external artifact custody remain the training boundary.
No fixed new package version is invented here; the triggered choice establishes compatible exact
pins and artifact revisions before integration. Rehearsal, threshold optimization and native
model tooling are Supporting when they answer the selected task's concrete question.

<a id="TC-I04"></a>

### TC-I04 · Alternative linguistic, coreference, pretrained-task and LLM providers

Consumes a named language/task gap or justified replacement comparison, not a general desire
for more provider votes. Produces a selected provider substitution/addition with exact labels,
source projection, runtime/artifact custody and independent task evidence. Existing HanLP,
Maverick and Dipo remain baseline unless their actual promises are preserved by a qualified change.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| `spacy-stanza`, `load_pipeline`, `PipelineAsTokenizer.v1` | Required language/task quality supports changing the linguistic provider. Decide whether its tokenizer/analysis preserves the shared source contract and improves the needed task. | Version/model/runtime compatibility and exact atom/token/source mapping on independent affected cases; TC-03/05/10. [spacy-stanza](https://github.com/explosion/spacy-stanza). |
| `experimental_coref` / `CoreferenceResolver`, `SpanResolver` | A required mention/reference task fits this alternative better than Maverick. Choose compatible runtime/release or retain Maverick; do not run a default duplicate. | Same source/reference question, detection versus clustering/span expansion, false merges and cross-boundary noncoverage; published0.6.4 spaCy<3.8 restriction must be resolved explicitly; TC-07/10. [Coreference API](https://spacy.io/api/coref), [requirements](https://github.com/explosion/spacy-experimental/blob/v0.6.4/requirements.txt). |
| HF `hf_token_pipe`, `hf_text_pipe` | A specific pretrained task supplies missing useful characterization. Select task/model revision, aggregation, stride and strict/contract/expand alignment. | Actual selected model outputs and source projection plus independent task references; retain external weights separately because pipeline save does not include them; TC-03/08/10. [HF pipes](https://github.com/explosion/spacy-huggingface-pipelines). |
| `spacy-llm` task/model registries, sharding/cache | A specified grounded characterization or vocabulary-discovery task benefits beyond current d1/LLM realization. Decide whether composition removes work or simply duplicates provider ownership. | Exact question/model/source mapping/failure contract, compatible runtime and independent semantic cases; reuse [existing LLM owner](../../../python/corpus-structure/src/corpus_structure/methods/llm/producer.py), TC-08/10 and downstream vocabulary owner where applicable. [spacy-llm](https://github.com/explosion/spacy-llm). |
| Supplementary HanLP SDP heads | An identified required relation meaning is not preserved by selected POS/lemma/dependency/constituency/SRL evidence. Select only the head that supplies that meaning, preserving its native scheme. | Exact head/model compatibility and independently assessed relation identity/endpoints; TC-03/05/10. [Review O01](../../functional_reviews/text-characterization_2026-11-10.md#O01), [HanLP formats](https://hanlp.hankcs.com/docs/data_format.html). |

These companions have no qualified new release selected by this plan. Resolve exact versions,
platform support and artifact revisions at the triggered decision; do not infer compatibility
from package names or add a second observation/workflow owner.

<a id="TC-I05"></a>

### TC-I05 · Abbreviations and later vocabulary linking

Consumes a recurring abbreviation/long-form population or a separately authored stable vocabulary
with a contextual mention-to-ID requirement. Produces source-level abbreviation evidence or a
later vocabulary-layer operation. Vocabulary links remain downstream additions to the same
enriched-document view and cannot feed accepted conceptual answers into source interpretation.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| scispaCy models / `AbbreviationDetector` / linker | Recurring abbreviation-long-form needs, or a genuinely matching biomedical task, justify this component. Choose the narrow component and actual domain resource rather than assume a scientific model fits mathematics. | Exact source abbreviation/long-form pairs, ambiguity/negative controls, package/model compatibility and task fit; TC-03/05/08/10, TC-09 if later vocabulary consumer. [scispaCy](https://github.com/allenai/scispacy). |
| `EntityLinker`, `KnowledgeBase` / `InMemoryLookupKB`, candidate retrieval/loading | An authored vocabulary supplies stable IDs and a contextual mention-link question. Choose candidate generation/ranking/rejection and preserve occurrence-local identity. | Native candidate recall versus rank/rejection, homonyms, NIL, predicted versus gold boundaries, source links and independent vocabulary-task references; TC-09/10, with TC-01/02 layer extension as needed. [EntityLinker](https://spacy.io/api/entitylinker), [KB](https://spacy.io/api/inmemorylookupkb). |

Linker prior/context/window/threshold/overwrite controls are supporting tools after task selection;
top rank is not resolved scientific truth. Local variable binding remains TC-06/07 semantics,
not automatic alias merging. No new linker is required for ordinary term/cue proposals.

<a id="TC-I06"></a>

### TC-I06 · Lexical alternatives, parser semantics, recovery and ranking

Consumes a specific construction/normalization or selection policy that the baseline Lark1.3.1
route cannot express adequately. Produces a versioned family/policy decision under TC-01 with
retained original input and alternatives. It does not widen every prose grammar or introduce
a generic constraint solver.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| Earley `dynamic_complete` | A required meaningful shorter-regex/boundary alternative is missed by `dynamic`. Select the affected family only; do not enable exhaustive catch-all prose lexing. | Independent source reading whose derivation requires that alternative, protected atom integrity and actual family behavior; TC-04/05/06/10. [Example](https://lark-parser.readthedocs.io/en/stable/examples/advanced/dynamic_complete.html). |
| Fixed-point semantics for cyclic forests | A deliberately supported construction requires cyclic semantics rather than an authored non-consuming grammar error. Decide a terminating interpretation/domain or retain explicit unsupported-cycle outcome. | Exact cycle meaning, termination/finite representation argument and independent relevant cases; TC-01/05/06/07/10. `on_cycle` detects but does not solve it. [Lark1.3.1 forest source](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| Custom `prioritizer=ForestVisitor` | A concrete interpretation-selection policy requires evidence beyond native additive priority. Choose its event/features and permitted preference; retain admitted alternatives. | Independent selection expectations with conflicting/correlated readings, stable order and evidence fidelity; TC-06/07/10. Native weights are not probabilities. [Prioritizer example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/prioritizer.py). |
| `TemplateConf`, template match/search/apply/translator | A concrete authored equivalence/normalization benefits from structural templates. Choose equivalence premises and output provenance rather than silently rewrite original syntax. | Independent equivalent and non-equivalent structures with extents/choices preserved; TC-04/06/10. [Lark1.3.1 templates](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree_templates.py). |
| LALR `parse(..., on_error=...)` recovery | An explicitly supported noisy formal population needs authored repairs, beyond retaining failed recognition plus independent units. Choose allowed edits and repaired status. | Exact original/inserted/deleted source pieces and independent correct/incorrect repair cases; repaired grammatical acceptance is not source truth; TC-04/05/10. [Recovery example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/error_handling.py). |

Changing lexical priority can change recognition, not merely ranking. Separate declaration and
inference determinants accordingly. Packed symbolic retention remains primary; bounded tree
enumeration or selected projections do not replace it.

<a id="TC-I07"></a>

### TC-I07 · Execution placement, lexical lifetime and acceleration

Consumes a concrete normal-workload operating concern after unnecessary duplication has been
removed: actual device/runtime fit, coordinated provider residency, lexical-state growth or
material deterministic-parsing uncertainty. Produces a selected supported runtime/lifetime route
with explicit preservation/recovery scope. Resource switches are not performance evidence.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| Multiprocessing / CPU / GPU / CuPy | Selected models and ordinary supported scopes warrant a compatible coordinated route. Choose process/device ownership across the whole operation, avoiding nested pools and duplicated resident models. | Actual startup/inference/source-equivalence/failure behavior in the selected environment; a bounded performance experiment only for material uncertainty; TC-03/08/10/11. [spaCy processing](https://spacy.io/usage/processing-pipelines), [GPU](https://spacy.io/usage#gpu). |
| `Language.memory_zone` | A long-lived worker's lexical growth makes explicit lifetime control useful and all native references can remain inside the zone. Choose detach-before-exit lifetime or retain current ownership. | Inspect every escaping Doc/Token/Span/lexeme; actual lifetime/control cases and retention/readback after detachment; TC-02/03/10. Escaping native views can crash; [memory management](https://spacy.io/usage/memory-management). |
| `lark-cython` acceleration | Material LALR performance uncertainty on selected deterministic families could change acceptance/route. Decide compatibility and actual value; it cannot accelerate the selected Earley forest by assumption. | Native token semantics, unsupported postlex, exact selected plugin/release and focused normal-workload comparison if needed; TC-04/05/10. [lark-cython](https://github.com/lark-parser/lark_cython). |

`nlp.pipe`, prepared Docs/context and resident provider custody remain selected baseline tools;
`doc_cleaner` after the last tensor consumer and LALR caches remain supporting choices. Avoid
copying all book-native objects into long-lived retained state. Scope-wise success or safe
overload refusal does not establish feasibility of a declared ordinary book workload.

<a id="TC-I08"></a>

### TC-I08 · Layout composition and additional languages

Consumes a selected language requirement or demonstrated region/linguistic translation burden.
Produces a qualified language/layout integration retaining immutable native source and hierarchy.
No second PDF parse is introduced just to obtain a spaCy span container.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| spaCy language extras `ja` / `ko` / `th` | A selected source language requires its tokenizer dependencies. Choose compatible exact extras and actual trained/resource coverage, not merely successful package installation. | Independent source boundaries/atoms, actual selected model annotations and downstream construction availability; TC-03/05/07/08/10. [Language support](https://spacy.io/usage/models#languages). |
| `spaCyLayout`, `Doc.spans["layout"]`, layout/table extensions | Wrapper composition demonstrably removes meaningful translation while preserving native source identity. Decide narrow interoperability versus current region adapters. | Inspect exact page/item/character correspondence, table/heading membership, failure scope and removal of redundant machinery; TC-02/03/07/10. [spaCyLayout](https://github.com/explosion/spacy-layout). |

Language support is a declared profile condition. Unsupported families remain visible; English
provider behavior or source geometry cannot be relabelled as another language's characterization.

<a id="TC-I09"></a>

### TC-I09 · External grammar reuse, independent delivery and bounded experiments

Consumes an actual independent consumer, valuable existing grammar or experiment lifecycle need.
Produces a named delivery/import/experiment decision preserving TC-01 semantics and `ci`/`just`
operational custody. These are not prerequisites for Python full-profile characterization.

| Conditional capability | Concrete trigger and decision | Settling evidence; affected packages |
| --- | --- | --- |
| Lark standalone / compression | A fixed deterministic grammar needs independent delivery. Choose generated LALR artifact/regeneration rather than runtime composition only for that consumer. | Selected consumer contract, grammar/callback/position parity, compatible trusted artifact lifecycle; TC-04/05/09/10. Does not deliver Earley packed alternatives. [Standalone1.3.1](https://github.com/lark-parser/lark/blob/1.3.1/lark/tools/standalone.py). |
| spaCy Projects | A bounded adopted NLP experiment removes more local scripting than lifecycle duplication. Choose a contained project or existing route, preserving one repository workflow owner. | Concrete asset/checksum/command lifecycle and integration into existing custody; TC-I02/03/TC-10 as applicable. `project run` does not automatically execute every upstream dependency; [Projects](https://spacy.io/usage/projects). |
| Lark.js | An actual independent browser/client needs local deterministic parsing. Choose a qualified grammar boundary/port, not substitution for Python Earley. | Exact selected port/release and grammar/positions/callback parity; documented Python<=1.1.5 basis versus selected1.3.1 is unqualified; TC-04/05/09/10. [Lark.js](https://github.com/lark-parser/Lark.js). |
| Lerche | An actual Julia analytical consumer benefits from grammar reuse. Choose a compatible subset/translation with explicit lost capabilities. | Selected Julia consumer and exact grammar/semantic parity; partial0.11.1 basis lacks Earley/CYK/dynamic lexing; TC-04/05/09/10. [Lerche](https://github.com/jamesrhester/Lerche.jl). |
| Nearley import | A valuable existing Nearley grammar can replace authored syntax for a required family. Decide import and semantic-action migration, not a generic runtime bridge. | Exact grammar/license-independent technical fit, Js2Py action behavior, source positions and independent required meanings; TC-04/05/06/10. Export/templates unsupported and ES6 experimental in reviewed route; [import tools](https://lark-parser.readthedocs.io/en/stable/tools.html#importing-grammars-from-nearley-js). |

A broad universal prose grammar as the sole front end remains rejected for the present target.
A future concrete superior coverage proposition can reopen that complete architecture through the
coordinator's decision route; it is not disguised as an automatically triggered library probe.
Regex/atomic-cache extras, visualizers, diagnostics, model packaging/loggers and publication tools
are Supporting only for selected needs; no install, external publication or obligatory experiment
follows from this inventory.

## Completion meaning and plan-writing evidence

TC-10 completes when declared independent source/output assessments cover the actual implemented
characterization and migrated-consumer scope, retained reads preserve their meaning, and the
coordinator can distinguish implemented capability, native qualification and remaining gaps.
It does not promise every English interpretation or measured improvement. A triggered TC-I
branch completes with its bounded decision and applicable follow-through/evidence; an untriggered
branch remains a documented revisit condition, not an outstanding requirement to run it.

Source/reference inspection supports this proposed plan on 2026-11-10. New functional/provider
tests, inference, model fitting, compatibility installs, runtime probes and benchmarks are
**not_run** during authoring. The coordinator owns assembled publication checks and final
maintenance. Existing plans supply no scope, priority, status or prerequisite to this new series.
