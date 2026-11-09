# Improve PM2 and shared extraction with GLiNER2 and spaCy

**2026-11-09 · Inspected source and plan baseline `f3db8952c`, clean at intake.**
This review assesses the remaining [PM2 series](../plans/production-milestone-two_2026-11-08.md)
against its [completion audit](../plans/production-milestone-two_2026-11-08.md#completion-audit),
including the existing annotation, candidate, interpretation, retrieval, admission and delivery
paths that the remaining work would change. It draws on WCE and NCE extraction and DMA admission
where they share those paths. It does not reopen source recognition, visual inference, the choice
of PM2 parser families or independent DMA-13 predecessor eligibility. Chandra stays excluded.

**Judgment.** Start by repairing the production of useful candidates and the evidence for their
meaning. Make the exact definition target and exact in-equation occurrences available before
retrying retrieval. Use spaCy's retained syntax, configurable rules and overlapping candidates
as a stable, explainable baseline. Add bounded HanLP, Maverick and Dipo evidence to specific
operations where their native products answer a question the baseline cannot. Use GLiNER2 to
discover source spans and to score or group particular candidates; use learned spaCy components
where there is a recurring span or attachment error and suitable independent labels. These
interventions address different failure modes. A larger encoder, stricter graph, or lower
threshold cannot supply evidence that the producer never represented.

**Authority and evidence.** The [GLiNER2 guide](../libraries/parsing/gliner2.md) and
[spaCy guide](../libraries/parsing/spacy.md), including both addenda, were read
with the [selected standard](../design_review/design_principles/standard.toml):
core principles, execution heuristics, test assessment and repository binding. The
code-intelligence profile concerns code-analysis outputs; its typed-fidelity questions are
useful analogies here, but this document does not issue a code-intelligence gate verdict.
The package, profile and installed-source observations below are **Interface-checked** or
**Implemented** at this baseline. Historical **Tested** claims keep their original cases and
dates. All amendments are **Proposed**. No new training, model campaign or product qualification
was run for this review.

## What the current evidence separates

The [annotation producer](../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
already streams prepared Docs through a pinned spaCy pipeline, refuses changed layout, and
checks column completeness. Its [retained view](../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py)
is used by [named annotation rules](../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py):
validated token, phrase and dependency matches, named role expansion, per-variant availability,
raw and reconciled overlapping groups, and a preset suggester seam. The reconciled
group currently mirrors the raw contiguous spans; neither it nor the unused suggester
is evidence of a fitted classifier. The
[predicate frame consumer](../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py)
also uses native matchers and traversal; a review should compare their responsibilities before
consolidating any logic. spaCy is pinned at `3.8.18` with the `en_core_web_sm` `3.8.0` wheel.
Narrow segmentation and richer retained annotation use different component selections.

The [GLiNER profile and compiler](../../python/corpus-structure/src/corpus_structure/methods/gliner.py)
and [resident worker](../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py)
already provide strict declaration round trips, prepared input bounds, native `batch_extract`,
and exact request and report custody. The incumbent is `gliner2[local]==2.1.0`, GLiNER2.5 Base
at `54785d51df8d86a0d8f2eb212fec15871aad2c4d`, CPU FP32 standard whitespace. The separately
identified codepoint profile and bounded prepared windows already supply diagnostics. Combined
batch extraction is an ordinary route. Standalone `Classifier`, `JointIE` and explicit-span
rescoring are not ordinary replacements for that worker route. Selected NCE clause classification
uses its own bound observation operation; an API named in the method catalog is not evidence
that it is selected.

| Observed boundary | Consequence for the review |
| --- | --- |
| [PM2 target and carrier preflight](../design_review/evidence/2026-11-09_pm2-adoption/README.md): the located binomial and constant-density terms remained `explanation`; no eligible definition attachment populated the six-window target set. The query producer found the binomial use but missed the two prescribed in-equation occurrences. | Two producer gaps precede ranking. v10 was blocked and v11 retrieval and paired grading were `not_run`. A successful producer task or a preserved archived link does not establish current inventory membership. |
| [Protected d1 pairs and reviewed-candidate diagnostic](../design_review/evidence/2026-11-09_pm2-interpretation-pair/README.md): one exact normalization gain, a preserved definition control, three unsupported answers; exact reviewed host and referent alternatives still did not settle either decision. | Candidate discovery and interpretation must be assessed independently. The host/referent gaps cannot be attributed solely to absent candidates. The magnitude question also needs an exact literal/units contract, not a higher model score. |
| [NCE definition and clause arms](../plans/next-corpus-enrichment_2026-11-07.md): described and overlap variants returned more located proposals in bounded windows without recovering an expected definition attachment. Exact-focus classification supported one of four judged functions; adjacent context supported none. [WCE JointIE](../design_review/evidence/2026-11-06_wce-gs120/joint-ie-investigation001/README.md) yielded feasible graphs with unsupported definition-role edges. | Do not equate proposal count, extra context or graph feasibility with improved extraction. A new arm needs a different mechanism for the diagnosed error, or a distinct task with an independent comparison. |
| [Natural-anchor caller comparison](../design_review/evidence/2026-11-08_gliner-caller-routing/README.md): literal-only natural extraction recovered the located predicate; mixed inline choices reproduced the prefix offset failure; latent grouping returned records without predicates. Standalone clause classification also made confident errors. | Keep literal assertions and clause function separate. Preserve the current repair; any future mixed, latent or anchorless route needs its own source and grouping evidence. |
| [DMA predecessor grades](../design_review/evidence/2026-11-09_dma-predecessor/README.md) and the PM2 audit: neither private predecessor qualifies, and PM2 has private product reads without a successful typed attachment/admission journey. | Use the bounded M1/PM2 evidence for development comparisons. Neither evidence transport nor the proposals in this review qualify a replacement or settle DMA-13. |

## Recommended amendments

<a id="I01"></a>
### I01 · Recover definition targets and equation occurrences at their producers

**Proposed PM2 amendment — first priority.** PM2-03/07 supply candidates, PM2-08 owns
qualification and composition, and PM2-09 owns target and carrier eligibility. Reuse the current
[definition producer](../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)
and [term occurrence projection](../../python/corpus-structure/src/corpus_structure/methods/definition_terms.py).
The former can bind term and content via a retained named match but its qualified naming and
explanation branches can still produce an explanation rather than a definition. The latter
projects a retained role, so running it again cannot discover missing evidence. Preserve the
release-owned `definition-scope-1` witness and its
[native validation](../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql#L2166);
do not globally reinterpret naming, accept bare
coincidence, or weaken native and detached checks to fill an inventory.

- Compare the incumbent rule/GLiNER route with a bounded named construction that distinguishes
  a defining act from naming, exposition and reported or conditional use. Inspect exact term,
  content, cue, scope and witness separately on the binomial passage. If the form only supplies
  a plausible candidate, retain it privately for independent judgment. A genuinely useful
  standalone term can survive without becoming an eligible definition target.
- Recover the affine carriers from the retained formula/occurrence products and authenticated
  primary fields, using the existing math and source location path. Compare the current
  [carrier selection](../../python/corpus-structure/src/corpus_structure/methods/contextual_candidates.py)
  with the [retained formula route](../../python/corpus-structure/src/corpus_structure/methods/math/native.py)
  before asking prose NER to infer equation boundaries. Keep equal symbols in different scopes
  distinct. No exact map means an uncovered or unresolved occurrence, not a guessed span.
- **Decision evidence:** exact supported target enters the released eligible inventory; both
  carriers are present at their declared positions; the independently rejected `X` relation
  remains unselected and the witnessed `Z` relation is preserved. Then run v10 and each
  applicable v11 signal separately against the same target inventory and fixed top-10 frame.
  Rank only after coverage, keep witness-based selection separate, and verify the same-release
  bounded list reaching d1 and exact replay before recommending v11 for ordinary use.

This directly localizes the repair and avoids masking a missing producer with search tuning
(FP-04, DP-03/08, H3/H5). The comparison must retain a valid explanation, a supported strong
definition, and an ambiguous case to challenge overbroad promotion.

<a id="I02"></a>
### I02 · Share located candidate contracts across rules and parser evidence

**Proposed PM2 amendment and shared extraction improvement.** Use the named rule machinery over
the retained annotation view as the first deterministic comparator. Prepare release-declared
`Matcher`, `PhraseMatcher` and `DependencyMatcher` patterns once per compatible vocabulary
and rule identity where repeated preparation is material. Use tree traversal, coordination
and bounded noun/subtree expansions before building a separate syntactic graph. Compare explicit
named bindings and the predicate-frame helper on a common typed role output. Consolidate only
where they actually promise the same result; the existing frame-specific polarity, modal and
attachment checks remain with their owner.

Retain exact overlapping alternatives in separate native span groups for contiguous proposals.
Transfer typed located products, availability and provenance through the existing contribution
boundary. A discontinuous argument or relation remains a typed product with pieces and endpoints,
not a flattened spaCy span. Use native `Doc.has_annotation(require_complete=True)` and retained
availability for prerequisites; retain viable phrase or token candidates if dependency evidence
is unavailable. Only introduce `AttributeRuler` for a demonstrated contextual POS, lemma or
morphology correction that improves a consumer. Its mutation belongs in a separate versioned
annotation recipe, before dependent analysis with appropriate order; do not rewrite a restored
incumbent Doc and present it as original evidence. Keep exact dictionary IDs and bounded fuzzy
hits as separately attributed proposals.

Compare current spaCy syntax, HanLP UD/constituency, then added SRL on the same source and consumer.
Project only explicit role mappings; never feed HanLP dependency labels through spaCy-specific
`prep`/`pcomp` rules as if they were the same scheme. Use Maverick's bounded mention inventories
and Dipo's ordered context as additional inputs for named referent and attachment decisions,
with their native provenance. Preserve the current strong definition witness; a different parser
can support a separate proposal until there is a released equivalent witness contract.

For the inherited variance premise, a new HanLP head is not the first intervention:
the [current HanLP cue path](../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py#L313)
is based on local UD markers and hosts. Compare a declared cue over exact phrase pieces
and a bounded cross-sentence/layout host policy, reusing the
[existing attachment pattern](../../python/corpus-structure/src/corpus_structure/methods/predicate_cross_block.py#L79)
where its contract fits. Preserve the incumbent inherited-premise witness and exact
formula seam. In the fair-coin case HanLP already nominated the assignment host;
that is a selector control, not a reason to generate more spans.

**Decision evidence:** positive-variance premise, passive and coordinated frames, competing
hosts, embedded versus defining-act qualifications, repeated/nested spans, partial formula atom
and missing columns. Evaluate located candidates, role mapping and the final selected host
separately. PM2-01/03–05 and PM2-08 own source maps, parser payload and consumers; WCE03 already
owns reusable rule and overlapping-candidate foundations. No parallel registry, new graph store,
or universal matcher is justified (FP-03/04, DP-06/07/13, H4/H12).

<a id="I03"></a>
### I03 · Use GLiNER2 to distinguish missing spans from bad decisions

**Proposed PM2-07/11 investigation and shared extraction improvement.** Keep the incumbent
combined call as the normal discovery arm. Expose a bounded diagnostic of the proposal/score
surface where the public decoded report cannot explain a miss: installed 2.1.0
`score_candidates(..., return_auxiliary_logits=True)` can inspect native candidate scores
before later selection. Use the public `SchemaTransformer.transform_record` and current
`prepare_input` to locate losses at source-to-model alignment, proposal, threshold/overlap,
or assignment. Preserve prefilter candidates where needed for diagnosis. Do not store every
intermediate tensor or make this the normal Reader payload.

The pinned Base [checkpoint configuration](https://huggingface.co/fastino/gliner2.5-base-v1/blob/54785d51df8d86a0d8f2eb212fec15871aad2c4d/config.json)
uses a shared pool of 192, minimum 8 per query, pool boundary top-k 32 and
start/end top-k 24; optional
candidate/query attention layers are off. The null and count heads exist; adaptive count
selection is off. Change one meaningful input or decoding control per arm: schema description,
threshold, overlap, or bounded proposal budget. Only test count guidance for a diagnosed
post-proposal recall loss, with false-positive and no-evidence controls. Changing learned
architecture modules or switching pool architecture is a model construction decision, not an
inference toggle. A successful native zero and an uninspected or refused span remain different.

For a missed independently grounded span, compare ordinary discovery, a fixed set of exact
spaCy or HanLP candidates scored by `score_explicit_spans`, then their union as a proposal
input to the same role consumer. The [tagged boundary implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py)
uses half-open model-word indices in the same encoded text/schema/masks, injects spans into
the shared pool and returns logits. It does not return a finished record or certify confidence
parity. Establish parity or record score differences on natively nominated spans before sharing
any cutoff. Check capacity on the actual packed set (including retained native competition);
refuse or explicitly split compatible work if injected spans cannot fit. Never round an
unalignable span, infer its coordinates from a duplicate string, or treat overflow as a negative.
Schema prefix choices and synthetic punctuation may participate in encoding but cannot be source
witnesses. Leave the present word splitter in place unless a same-source diagnostic shows
that changing it solves the representability problem without breaking controls.

**Decision evidence:** exact recovery of a missing term/content or literal boundary on a
frozen scope, with nested and repeated occurrence, wrong endpoint, Unicode/formula, overflow,
and independently negative controls. Include a known case where the right candidate was already
present and scoring or assignment still fails. Compare incremental correct located products
reaching the consumer, not the size of the raw pool. Reuse the existing native worker and
observations if a challenger qualifies, rather than introducing a second cache or provider
protocol (DP-09/15, H7/H14).

<a id="I04"></a>
### I04 · Separate literal capture, function, and attachment in the GLiNER2/d1 comparison

**Proposed PM2-07/08/11 amendment.** Implement the missing like-for-like comparison as an
operation assessment, using the current natural literal assertion pack plus exact
[spaCy-backed qualification](../../python/corpus-structure/src/corpus_structure/methods/assertion_qualification.py)
as the incumbent. Reuse the existing [NCE release-bound clause operation](../../python/corpus-structure/src/corpus_structure/methods/clause_classification.py#L294)
for request, worker and replay custody; PM2 supplies its own declared question and labels.
Use separate native GLiNER2 classification for a genuinely equivalent passage
or clause question, with identical applicable scope, released label meanings and independently
graded output. Preserve source spans for literals and relation endpoints; a passage label
does not supply its own span. Expose when an operation cannot answer a comparator question
rather than scoring it as an empty match. For the roulette case compare a grounded quantity
candidate and the existing typed normalization path against d1 on the exact same question.
Use a named matcher for separately exact number and unit extents as a bounded comparator.
Keep amount, unit, loss role and original literal separate, and require a released conversion
rather than assuming a number found somewhere in a quantity string is the correct answer.

- For **condition/exception hosts and local participants**, start with explicit typed endpoints
  and deterministic constraints from I02. Compare released local structural selection, d1 on
  fixed candidates and, if labels support it, the pair scorer in I06. Preserve a complete
  independent part when no host or referent qualifies. Dipo neighbors may supply context and
  Maverick mentions may supply candidates; discourse nuclearity and local clusters do not
  establish causal, obligation or corpus identity relations.
- For **record formation**, keep natural anchored literal extraction as the baseline for
  explicit occurrences. Compare cardinality/exclusivity and explicit absent values on a case
  with two independent records and a repeated spelling that must not be assigned twice.
  Latent seeds or anchorless queries merit a separate arm only when a reviewed real record
  lacks a stable anchor; test record existence and field assignment separately. Do not
  recover a failed required field by assigning any available span. Avoid inline choices in
  the repaired natural assertion pack; no earlier latency or successful decode justifies
  restoring the known failure mode.
- For **classification and relations**, compare independent single or multilabel decisions
  first, with release-authored descriptions, activation semantics, thresholds and any examples.
  A native ordinary multilabel decode can fall back to argmax below the threshold; keep
  that output attributed and apply released withholding separately. Use span attributes
  only for a property of an already located mention (the definition pack already uses them),
  and independent relations for directional hypotheses with exact endpoints. Consider `Classifier.score` and
  bounded `decode` for a real cross-label constraint, with infeasibility, violations and
  approximation explicit. Consider `JointIE` only for a relation family that needs competing
  typed assignments to be jointly coherent. Bound the lattice/beam, retain candidate failures
  and compare against the existing semantic selector. Feasible empty, infeasible and
  semantically incorrect are different outcomes. The
  [NCE antecedent trial](../design_review/evidence/2026-11-07_nce-source-linguistics/README.md)
  also missed the frozen antecedent and produced a reversed control link.
  Neither native decoder becomes the
  semantic release or admission authority.

**Decision evidence:** reproduce the ordinary controls, demonstrate a protected correct gain
on the same question, keep exact fair-coin normalization and the strong definition control,
and retain alternate or incomplete records. Include a polarity reversal, swapped relation
endpoints, mixed attribution and unresolvable candidates. Require correct material selection,
not just a feasible decode or confidence above a threshold. PM2-08's typed result must remain
inspectable with the released operation and witness (FP-04/05, DP-02/05/07).

<a id="I05"></a>
### I05 · Add a stock spaCy span model only for an identified span task

**Proposed shared extraction investigation; integrates with PM2-03/07/11 if selected.**
The strongest first learned spaCy option is a small, separately configured
[SpanCategorizer](https://spacy.io/api/spancategorizer) over the existing preset group,
not a new parser. Example questions are which exact candidate is a defining-content span,
a qualifying clause, or an entity mention of a declared kind. Compare a named rule alone,
GLiNER2 on the same exact candidates, and spaCy scoring over the same candidates. Use
`spacy.preset_spans_suggester.v1`, explicit input and output keys, and
`set_candidates` for a bounded diagnosis. Use the single-label variant when labels are
exclusive with a negative class, multilabel only for legitimate overlapping meanings on
one span. Keep spans of different lengths that overlap. If scoring fails with the right
inputs, a registered encoder, reducer or scorer can improve the stock component before
changing its task contract. The input suggester carries only
token start/end; deduplicate geometrically for scoring while preserving every role, generator,
host alternative and occurrence binding in the owning located products. Do not overwrite
the raw group or imply that the reconciled group is already learned.

If candidate recall is low on alignable exact reference spans, compare richer named rules
or additional provider proposals before a learned [SpanFinder](https://spacy.io/api/spanfinder).
Compare bounded min/max length and start/end thresholds against a small bounded n-gram
control only where that control makes the recall ceiling visible. SpanFinder supplies
unlabeled contiguous spans, not a binding between them. It pairs thresholded starts and ends
within the input Doc; canonical bounded scopes and an exact remap must enforce sentence
and atom boundaries and keep excluded cases visible. Unrestricted spans increase
intermediate work without resolving the wrong host. Use standard NER for an explicitly flat
entity task, `Doc.ents` only when the non-overlap contract is appropriate. Compare
`textcat`/`textcat_multilabel` for passage or document routing as an attributed signal;
keep it out of source eligibility unless an independent coverage study supports gating.

**Decision evidence:** report exact candidate coverage on the complete independent frame,
including gold extents unrepresentable with the prepared token layout. Then grade labels
among offered spans and downstream value separately. Keep nested/repeated references,
wrong neighboring spans and alternate roles. Stock span categorization constructs negative
targets for absent labels on proposed spans; choose a fully judged operation slice or use
a model with an explicit supervision mask. spaCy NER's `Doc.set_ents` missing/outside/blocked
and `incorrect_spans_key` have NER-specific meanings; they are not generic span loss masks.
This is a bounded addition to the existing seam, with a native alternative to maintaining
custom classifier infrastructure (FP-03, DP-13/16, H4/H7).

<a id="I06"></a>
### I06 · Investigate a trainable spaCy binding scorer, with a staged fallback

**Proposed investigation, conditional on recurring fixed-candidate errors and sufficient labels.**
This is the more valuable advanced spaCy modeling direction when the missing product is a
*binding* rather than a span label. A single qualifier extent can be correct with one host
and incorrect with another. Stock `SpanCategorizer` cannot express that outcome by
changing its encoder. Compare the existing released deterministic selector and fixed-input
GLiNER2/d1 operations before fitting a model. If a recurring error remains and a released
pair task with reusable supervision is justified, build the smallest challenger that
scores a bounded, typed `(focal role, candidate role, relation)` alternative, including
a no-supported-choice outcome. Reuse native syntax paths, role/span features and explicit
scope. Handle discontinuous roles as ordered source pieces; the relation is a retained
typed output outside spaCy's contiguous span groups.

- Start with a regularized lightweight feature baseline on the frozen pairs. Compare a
  configurable [custom TrainablePipe](https://spacy.io/usage/processing-pipelines) using
  a registered Thinc model only if the task benefits from spaCy's shared annotations or
  trainable representations. Keep the factory and injected model separate: `predict` scores
  without mutation, `set_annotations` exposes private candidates or scores, `get_loss`
  consumes independently judged pairs with unknown labels masked, and the scorer evaluates
  exact binding and abstention. Keep release semantics and proof in the existing domain
  compiler, selection and contribution owners. A model answer never mints a witness.
- Compare independent lightweight `Tok2Vec` or the existing sourced encoder first; share a
  listener only across heads with a demonstrated need. Record which components are sourced,
  frozen or annotating during training. Use `replace_listeners` or freeze the shared upstream
  model where required to prevent a supposed frozen consumer from changing during training.
  Escalate to curated Transformers or the broader HF integration only if held-out errors
  justify extra dependencies and representation transfer. Test pinned companion, backbone,
  token-window alignment, packaging and existing GPU custody independently.
- Use `Example` alignment, `DocBin` where it preserves the supervised fields, and a registered
  corpus reader when typed endpoint labels require it. Keep exact source occurrence IDs and
  unknown/refused labels in the existing evidence owner. Use predicted upstream annotations
  on training inputs where inference sees them, with a gold-candidate diagnostic as a separate
  ceiling. Group holdout splits by source unit; retain nonalignable reference coverage, rather
  than letting the default token-aligned score hide it. Verify config and data with the native
  debug and scoring routes; save/load the artifact together with the registered code,
  tokenizer, effective config and dependency identities. A training harness is a follow-up
  if these requirements cannot yet be met, not a reason to fake supervised data.

**Decision evidence:** prespecified fixed-candidate host/referent accuracy and correct
abstention, directional/passive/coordination controls, and independently useful reader output
under ambiguity. Adopt only if it repairs a protected reading over simpler alternatives
without regressing protected controls and can run within the existing deployment and
replay boundary. Reusable outside PM2 for actions, prerequisites, attributions and scoped
references, if justified by those consumers; no domain-specific code path (DP-02/08/15,
FP-06/07, H3/H11).

<a id="I07"></a>
### I07 · Deliver partial analytical products through one typed seam

**Proposed PM2-01/08/11 amendment.** Current private facets prove custody for unresolved
alternatives and the exact quantity. Extend the owning producer and selector through released
payload and relation contracts before adding more read-side inference. Keep the provider's
native labels and scores, aligned proposals, evaluated scope, assessed answers and selected
standing separate. Publish a useful term, frame, quantity, reference or procedure part
whenever independently qualified, with the missing or failed related operation explicit.
Do not collapse skipped, ineligible, cancelled, budget-limited and completed-empty into the
same result. PM2-R01, PM2-R02 and parser F01 retain their existing owners; this is a better
integration path, not a replacement finding. Reuse Reader, CLI, fresh MCP and exact detached
proof rather than creating an export-only semantic interpreter.

Use one declared condition/host relation on a textbook premise (condition on an assertion)
and on an authored business instruction (for example, a condition on releasing a payment).
Use the same operation selector, adapters, candidate payload, witness gate and consumer;
replace only declarations and source. Fixed learned label sets require their own
release-compatible model qualification when their meanings change; the shared path
must still work without hardcoded vocabulary. Preserve a competing host, explicitly refuse an
incompatible or missing relation declaration, and preserve an independently qualified
contribution after a sibling fails. Treat this as configurability evidence, not a claim
about general business document performance. Widen to selected extraction families only
through their existing closure obligations. This yields a more useful analytical surface
than a fully populated but unsupported record (FP-03/04, DP-05/19/24, H1/H2).

<a id="I08"></a>
### I08 · Use sufficient context, then optimize the selected execution

**Proposed shared execution improvement; conditional on a material coverage or operating need.**
Retain source-aligned sentence, clause or coherent-section scopes as the default. Compare
a bounded neighboring sentence, one HanLP frame, a Maverick antecedent or a Dipo neighbor
only when the named question has evidence outside the focal scope. For genuine window loss,
compare GLiNER2 native long extraction with the existing prepared-scope route on the same
source. Check actual word/subword and schema-prefix budgets. Preserve overlapping windows
and deduplicate by occurrence, not surface text. Native long extraction merges local outputs;
it does not infer edges whose endpoints never share a window or guarantee cross-window record
grouping. Use the existing exact retrieval/attachment path for distant relations. A wider
window with no gain should not become the default.

Keep `Language.pipe(as_tuples=True)`, loaded component selection, and `batch_extract` as
first choices. Apply `make_doc`, component exclusion or sourcing only where the consuming
annotations permit; disabling is not equivalent to unloading. Prefer combined native extraction
for genuinely shared, compatible tasks over a separate durable hidden-state cache. Separate
failure isolation or different schemas may justify different calls. Candidate input, splitter,
schema order, profile, model/adapter, masks and effective runtime belong in reuse identity;
packing changes only physical execution when semantic parity is verified. Compare shape-aware
batching and size variants before GPU precision or attention backends. On an established
memory problem, evaluate `doc_cleaner` after the last tensor consumer and
`Language.memory_zone()` only if all zone-owned objects die before exit. Avoid multiprocessing
or more model residents merely to hide unnecessary work. Measure any claimed execution gain
on the actual scope while retaining exact replay and refusal; this review makes no new
throughput claim (FP-07, DP-09/20, H5/H10/H14).

<a id="I09"></a>
### I09 · Specialize GLiNER2 only after establishing the loss and usable supervision

**Proposed follow-up, with NCE-M03/M06 and PM2-07/11 as existing investigation owners.**
First repair the exact alignment, context and nomination gaps in I01–I03. For a persistent
role, record or relation error with sufficient independent training data, compare unchanged
zero-shot conditioning, a task-specific adapter, and full tuning only if the smaller
intervention leaves a material residual. Bind the adapter/checkpoint and PEFT runtime to
the operation; isolate active adapter state under concurrency instead of mutating a
shared resident across in-flight requests. Compare LoRA and DoRA only on the same diagnosed
question. Do not infer separate attribute-training supervision from the inference API.

Use exact character spans for repeated occurrences. Validate entity/field alignment and
relation consistency using native dataset utilities, then inspect nested labels, explicit
negatives, unknown cases, and the default contained-span deduplication. Use source-group
holdouts separate from prompts and training. Training-time gold-candidate injection can
teach a ranker; report proposal recall with injection off, including long/rare spans.
Keep capacity failures explicit, and adjust training losses for an identified proposal,
pair, abstention, assignment or relation error. Native diagnostics and strict training
are preferable to silently skipping samples. Distributed training, objective schedules,
pretraining or continual learning have no current delivery requirement; revisit them
when a bounded, simpler training comparison justifies that burden. Assess exact
consumer gain independently of vendor benchmarks (FP-02/07, DP-15/22/23).
[GLiNER2 training and addendum](../libraries/parsing/gliner2.md#8-training-and-model-specialization)

<a id="I10"></a>
### I10 · Improve reusable insight discovery without creating another identity system

**Proposed broader extraction opportunity.** Extend existing rule declarations and scoped
candidate products to cover recurring operations with a named consumer: terminology and
alias discovery, procedural actors/actions/prerequisites, qualified statements, source
attribution and links to exact section, table or definition targets. Reuse versioned
phrase/ruler patterns for known terminology, model discovery for novel spans, and an
attributed passage-function label to prioritize inspection. Never suppress eligible
source purely on that label without a separately evaluated routing policy. Prefer
opportunity-specific changes in I01–I07 that serve current consumers before a general
workflow extraction rollout.

Only consider spaCy `EntityLinker` for a real canonical identity task with independently
owned stable IDs, scoped aliases, sufficient candidates and an explicit NIL outcome.
Compare declared exact aliases, then current lexical/dense candidate retrieval, then a
learned linker using batched candidate hooks and separately tested prior/context choices.
Keep local Maverick coreference, a rule's alias/ID proposal, a retrieved target and
witnessed corpus identity separate. Do not add an in-memory shadow KB that becomes a second
authority. Cross-document linking, new domain corpora and language or specialist products
need separately selected populations, preservation controls and a current consumer.
Use existing extraction routes, rather than spaCy lexical similarity as a replacement for
Sentence Transformers retrieval (FP-04, DP-01/04/07, H3).

## Capability dispositions beyond the recommended first slice

The full [spaCy guide](../libraries/parsing/spacy.md) and [GLiNER2 guide](../libraries/parsing/gliner2.md)
inform the comparisons above. These remaining capability families are useful with the
stated triggers; none adds a requirement to close PM2.

| Capability family | Disposition and trigger |
| --- | --- |
| **spaCy representation and tokenization:** `Doc`/Span/Vocab, sentence parser vs senter/sentencizer, morphology/POS, lexical and edit-tree lemma, language-specific splitting, custom tokenizer, retokenization and experimental learned merging | Keep source-prepared Docs and existing annotation/segmentation profile choices. Use tokenization diagnostics and strict alignment first. Use expand/contract only for attributed approximate hints, never exact identity. Select a distinct recipe only for an independently observed sentence, alignment or morphology loss. Recheck offsets, all dependent rules and pretrained behavior. Formula atoms stay owned by preparation. |
| **spaCy interchange and extensibility:** extensions/hooks, factories, component metadata, `analyze_pipes`, arrays, bytes/JSON, `DocBin`, `Span.as_doc` / `Doc.from_docs` | Use native component metadata and actual annotation checks when a new component is selected. Local span groups and arrays can reduce transient translation; they are not evidence storage. Rebase transformed Docs through exact source maps, and explicitly preserve extensions when required. Avoid property hooks that obscure authority. Review `DocBin`/corpus utilities for training interchange, not native Reader storage or random access. |
| **spaCy modeling and operations:** custom Thinc layers, static/floret/BaseVectors, transformer integrations, pretraining, rehearsal, augmentation, CLI/projects/loggers/displaCy | I05–I06 choose stock heads, then injected architecture or custom task as required. Use debug config/data, evaluation and displaCy to explain failures. Use native packaging and benchmark tools only for their qualified artifact or measurement scope. No new lexical-vector backend without a diagnosed lexical gap; no vector substitution for contextual retrieval. Preserve exact supervision through any augmentation. Reuse existing evidence and workflow ownership rather than a second Projects/logging lifecycle. Rehearsal and external logging need separate demonstrated needs. |
| **spaCy companion ecosystems:** spacy-layout, experimental coreference/tokenization, spaCy-LLM, Stanza, scientific/language models, lookups, Hub tooling and optional hardware packages | Docling and retained layout already own source; Maverick and d1 own their scoped questions. Do not replace them with wrappers on API availability. The guide's documented `spacy-experimental` range excludes current 3.8.x; a new profile would need its own compatibility evidence. Stanza/scispaCy and language extras are challengers for a diagnosed linguistic gap with compatible annotations. A Hub or hosted path is a distinct deployment decision. |
| **GLiNER2 schema and native supervision:** Pydantic validation, schema serialization, `RegexValidator`, record/relational constraints, training-data validation and candidate objectives | Keep one release declaration and lower to the native schema. Use strict validation and round-trip checks at the existing pack boundary. Regex filtering earns scope for a declared literal shape and preserves prefilter evidence where needed; it does not validate identity or meaning. I03/I04/I09 cover candidate controls, record/pair evidence and training diagnostics. |
| **GLiNER2 inference and model lifecycle:** batch/long APIs, splitter, precision, FlashDeBERTa/DisentangledFlash, packing, compilation, cached states, native Transformers facade, save/export | I03/I08 preserve exact offsets and shared work. FP16/BF16 are floating-point conversions, not integer quantization. Optional kernels require pinned hardware/runtime parity and a workload benefit; the documented DisentangledFlash route is not combined with compilation. Internal streaming/vectorized export settings do not establish an ONNX or TensorRT route. The HF facade is a separate challenger; architecture metadata does not establish equivalent records, constraints, offsets or replay. Preserve all effective artifacts on save/load. |
| **GLiNER2 other models and hosted path:** Small/Base/Multi, Decide variants, GLiGuard, privacy and combined classifiers, hosted schemas, partial retries and packaging extras | Keep Base. Small for a measured resource need; Multi for a supported language frame; Decide only for a persisting classification problem after I04 (variants differ in architecture). Safety and PII are separate extraction workflows. Hosted partition/retry receipts do not provide the local model's exact schema/decoder/replay contract; no switch proposed. Pin the actual extras and transitive runtime for any future profile; do not infer import or accelerator compatibility from optional-package metadata. |

## Evidence and delivery order

1. **Freeze what would count as a gain.** Reuse PM2-11's protected source-first frame and
   output-first review. Use the retained Standard/Nemotron selections, exact question,
   release, source group and independently assessed expectations. Record prior exposure
   and inspected scope. Keep protected test data apart from schema examples and training.
   Compare the incumbent and challenger on the same eligible inputs; preserve explicit
   refused, unaligned, limited and uninspected cases. Distinguish proposal coverage, label
   or rank conditional on availability, exact attachment/normalization, and qualified
   consumer outcome. An oracle-candidate arm diagnoses a stage; it does not grade
   ordinary discovery. Grade new unsupported proposals even if admission refused them.
2. **Do useful upstream work first.** I01 and the targeted deterministic pieces of I02
   address named producer gaps. I07's typed boundary and outcome work can proceed against
   current private outputs; positive and failed-sibling journeys require the proposed
   selection producer. Run I03/I04 diagnostics on a frozen panel before picking a
   learned route. Where the evidence shows a contiguous span label error, try I05;
   where the correct candidates are present but a binding remains wrong, use I06's
   conditional ladder. Treat I08–I10 as scope-specific decisions, not a new milestone
   dependency or a model sweep.
3. **Keep acceptance at the owning operation.** Require an independently supported
   gain on the declared primary question, preservation of all supported controls and
   no new unsupported selection, as PM2-11 already requires. Insist on ordinary
   Reader/CLI, fresh MCP and exact detached delivery where required; do not claim
   transfer or performance without matching evidence. Only after target/carrier
   coverage retry v10/v11 and retain the simpler route if the comparison does not
   support change. Existing DMA-13, assembled review, final source qualification
   and full-book derivation/selection gates remain in PM2-12. No current plan,
   completion disposition, ADR, dependency pin or release selection is changed here.
