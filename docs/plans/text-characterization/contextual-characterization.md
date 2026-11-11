# Contextual characterization and grounded proposals

**Implemented; bounded functional scope Tested · 2026-11-11.** This companion develops [TC-07](#TC-07) and
[TC-08](#TC-08) in the [text-characterization coordinator](../text-characterization_2026-11-10.md).
The coordinator owns authorization, package state, source-opportunity disposition and adoption.
The [model and retention companion](model-and-retention.md) owns the enriched-document model,
layer identities and durable contracts. This document consumes those meanings rather than
creating another mutable account of them. Its source is [review O04/O05/O07](../../functional_reviews/text-characterization_2026-11-10.md#O04).
The coordinator records functional closure, including actual-provider controls. Independent
semantic assessment and full-book qualification remain TC-10/11 scope.

## Authoring baseline and intended result · 2026-11-10

At the authoring baseline, the [Maverick projector](../../../python/corpus-structure/src/corpus_structure/methods/pm2_maverick_products.py)
retains detected, supplied and clustered mentions separately; its cluster is one native local
partition, not corpus identity. The [Dipo projector](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dipo_products.py)
authenticates ordered binary trees and located EDUs, including learned/forced boundary provenance.
The [d1 projector](../../../python/corpus-structure/src/corpus_structure/methods/pm2_interpretation_products.py)
binds typed answers to an archived question population and distinguishes native observations,
proposed options, unresolved results and policy withholding. The current
[GLiNER passage classifier](../../../python/corpus-structure/src/corpus_structure/methods/pm2_gliner_classification.py)
binds one exact source slice and a released multilabel question; its passage category does not
locate a literal witness. Those foundations did not implement the new full characterization profile.
The authoring-baseline [statistics question declarations](../../../domains/statistics/interpretation-questions.yaml)
supplied finite domain questions. The delivered
[characterization declarations](../../../python/corpus-structure/src/corpus_structure/model/semantic/characterization-questions.yaml)
now supply all eight baseline language families independently of those domain questions.

The target adds contextual layers to the **same enriched document**: immutable native source
and hierarchy remain the reference frame; independently pinned layers contain ID'd annotations,
ordered source pieces, cross-page/discontinuous memberships, typed roles, operators and choice
dependencies. Contextual products enrich that view without rewriting the source tree or replacing
native observations. Higher conceptual groups can later appear in the same view under their own
operation identities. Their accepted answers never become evidence for the earlier source reading.

Source-level reference, inherited-participant, scope and attribution **hypotheses** belong here.
TC-06 owns final contextual evaluation of symbolic terms under inherited environments. Cross-work
concept identity, scientific symbol resolution, domain predicate assignment and retrieval-based
conceptual links remain downstream. A linguistic declaration-to-use binding can support scientific
binding; the two operations retain distinct questions and premises.

## Prerequisite contracts and execution shape

| Prerequisite | Required slice and why it is needed |
| --- | --- |
| TC-01 | Versioned occurrence, analysis, role/operator/choice and coverage semantics; source identity independent of analysis identity. Define contextual products and question meanings before projecting provider answers. |
| TC-02 | Publish/read independently pinned layers, durable exact extents and evidence closure; contextual products must survive detached replay without live native objects or inference on read. |
| TC-03 | Immutable document hierarchy, atom-preserving positioned source, native sentence/token maps and provider evidence. These establish actual contextual membership and native origin. |
| TC-05 | Located constructions and authored inheritance/attachment rules. Use these rather than duplicate clause recognition in contextual consumers. |
| TC-06-A | Context-independent symbolic terms, explicit binder/scope sites and correlated choice graph. These supply candidate identities and premises; they do not already resolve inherited bindings. |

Source-only TC-08 question definitions and reference authoring can proceed once TC-01–03 supply
their contracts; they do not wait for every construction. Candidate-centered TC-08 tasks require
the exact relevant TC-05, TC-06-A symbols and TC-07 hypotheses, **not** final evaluated answers.
TC-07's initial native mention/discourse projections can proceed from TC-03; its scope/binding
hypotheses consume the relevant TC-05/06-A slice. TC-06-B then evaluates retained symbolic terms
with TC-07 hypotheses and TC-08 proposals. There is no automatic refinement/fixed-point loop:
remaining unknowns stay unknown unless a new explicit versioned demand schedules additional work.
This separates early usable slices from enclosing package completion and avoids a scheduling cycle.

Choose natural sections from retained hierarchy, heading/list/quotation structure and source order.
Each request declares focal output region, complete examined context, source pieces and actually
examined boundary pairs. A page break is not a discourse boundary; synthetic section separators
are not quoted source. A displayed focal slice never implies only that slice affected the answer.
If a provider cannot admit a section, use its already supported bounded scope route and mark the
unexamined crossings. Do not pretend independent windows establish whole-section reference or
discourse completeness. Full-book qualification covers all 518 physical Grinstead–Snell pages
with explicit applicable-family outcomes; it is not 518 independent sentence-only analyses.

Reuse the existing resident provider/task owners and preparation. A semantic family need not
create its own process, model load or transaction. Batch compatible source-only questions and
native scopes where their contracts allow it; questions depending on a preceding answer run
after that answer's immutable product exists. Release large provider state after its final
consumer; retain detached products rather than live Docs/forests for every book section.

<a id="TC-07"></a>

## TC-07 · Contextual reference, discourse and inherited interpretation

### Operation and library responsibilities

Input is the exact source/hierarchy scope, native syntax and mention/discourse evidence, and the
TC-05/06-A constructions/terms applicable to that scope. The operation owns native/structural
context evidence and source-level hypotheses: attribution chains, referential alternatives,
inherited grammatical participants/qualifiers, host attachments and contextual functions.
Its output is a pinned contextual evidence/hypothesis layer in the
enriched document, containing separately attributed assertions and choice dependencies plus
family-specific scope/coverage. It can produce useful local annotations with unresolved bindings.

Keep the selected provider contracts:

| Mechanism and pinned baseline | Supplied capability and application residual |
| --- | --- |
| `maverick-coref==1.0.7`, `Maverick.predict`, MES checkpoint `sapienzanlp/maverick-mes-ontonotes@087a90f0380ec1f20ed19732b657f53fd3542c81`; [wrapper source](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/maverick_model.py#L48-L208), [native inventory](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L129-L451) | Nested canonical sentence tokens support mention/cluster prediction over a coherent scope. Inclusive native endpoints need exact source mapping. Preserve detected/supplied/assigned populations and unassigned mentions; public clusters or `singletons=True` do not establish exhaustive detection. The application defines referent kind, inherited participant interpretation, cross-section noncoverage and source-level binding choices. Neither cluster membership nor nearest prior member establishes scientific entity identity. |
| `dipo==0.2.1`, `DMRSTParser.predict_from_text(..., break_at_paragraphs=False)`, checkpoint `larc-iu/dmrst-ettin-400m-gum-12.1.0@e33906a27f89b2703df8ab19e471aa82141d62cb`; [boundary seam](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L66-L144), [native prediction](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L682-L818) | Predicts EDU boundaries and ordered binary RST relations/nuclearity. Preserve exact token/character maps, native labels, child ranges, singleton coverage and boundary provenance. The application decides which located discourse evidence supports a condition host, function or attribution proposal; an RST relation is not automatically a logical connective or endorsed causal claim. `predict_both()` is a supplied/predicted-EDU diagnostic over reconstructed input, not an ordinary raw-source result. |
| Lark `1.3.1` positioned symbolic terms consumed from TC-06-A; [visitor APIs](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py), [forest implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py) | TC-07 attaches context evidence/hypotheses to retained binder/scope sites. TC-06-B alone owns `Interpreter` use for ordinary trees and environment-keyed evaluation of packed symbolic terms. Native `ForestTransformer`/`single_visit` caches do not supply inherited-context evaluation. TC-07 does not duplicate that evaluator or expand complete trees. |

Backbone/artifact/runtime custody remains with the existing
[native worker](../../../python/corpus-structure/src/corpus_structure/methods/pm2_native.py)
and [dispatched provider implementations](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dispatched.py),
with exact artifact digests in [the current manifest](../../../python/corpus-structure/src/corpus_structure/methods/pm2_artifacts.json).
Reuse compatible retained native observations rather than reload or rerun because a contextual
rule changed. Any changed provider profile has its own actual native compatibility obligation.
Experimental spaCy coreference and alternative discourse providers remain conditional challengers.

### Coherent implementation work

1. Extend the released contextual operation contracts and layer writer/read projections together.
   Preserve native mention and EDU identities; contextual assertions refer to them and their
   original schemes. Retain the exact observed population even when no contextual relation is
   emitted. An asserted relation has typed, directed endpoints and explicit support, not just
   equal text or enclosing bounds.
2. Implement structural-context construction over retained headings, lists, quotations and source
   hierarchy. Make inheritance conditions explicit: a heading may qualify a list; an exception
   may attach to one step or a group; intervening quotation/section boundaries can constrain
   propagation. Preserve alternative hosts and their premises. Avoid a generic “copy all prior
   qualifiers” rule or a page-number dispatch.
3. Produce source-level binding/host hypotheses keyed to TC-06-A binder/scope sites, retaining
   active attribution/quotation context, located witnesses and required prior choices. Supply
   these to TC-08's candidate-centered questions and TC-06-B's final contextual evaluator.
   The evaluator's node-plus-environment identity and reuse contract remain TC-06's sole
   responsibility. A hypothesis does not mutate symbolic terms, settle an unknown referent or
   merge rival readings. Unsupported cycles remain diagnostic/incomplete unless
   [TC-I06](assessment-and-investigations.md#TC-I06) deliberately adopts terminating semantics.
4. Compose Maverick and Dipo evidence with construction outputs to expose ordinary candidate
   hypotheses through the model's meanings. Keep disagreements attributed. A cluster can propose a source-local referent;
   a Dipo condition relation can nominate a host; neither overrides a conflicting exact
   construction witness without a declared interpretation policy owned by TC-06. Source semantic “or” remains
   an operator inside a reading; analytical alternatives remain choices between readings.
5. Expose contextual layers through TC-02 readers with their examined scopes, gaps and dependent
   choices. TC-09 migrates domain consumers to these shared answers and retires private
   cross-block interpretation where superseded. TC-07 must deliver located hypotheses with
   premises; TC-06-B delivers evaluated contextual products those consumers can use.

### Failure, reuse and acceptance

Provider failure, unsupported scope or missing syntax affects only dependent families. Preserve
sentence-local output, native observations, unresolved mentions and completed sibling scopes.
An empty cluster set cannot mean no reference; a context cutoff cannot mean no antecedent.
Unknown compatibility cannot become a supported Cartesian product. One located hypothesis need
not wait for a globally complete reading, but its use retains any unsatisfied premises.

Context hierarchy/selection, quotation boundaries, source membership, construction revisions,
upstream choices or contextual evidence changes invalidate affected hypotheses and dependent
TC-06-B evaluations under their respective reuse contracts. A
new conceptual link or higher group does not invalidate source interpretation merely by existing.
Reinterpretation from unchanged native evidence is distinct from new provider inference.

Unit checks independently author bindings/scope outcomes for a heading qualifying several items,
a competing intervening antecedent, quotation within reporting, cross-page/discontinuous roles,
context evidence attached to distinct binders, and incompatible local choices. TC-06 owns the
independent shared-node/different-environment evaluation control. Include deliberate
wrong endpoint, false cluster merge, missing source piece and unexamined cross-section controls.
Roundtrips/readback must preserve exact membership, evidence and choice correlations, not just text.

Actual native acceptance separately exercises Maverick and Dipo on authenticated book scopes,
including native detection versus supplied mentions and raw versus supplied-EDU diagnostics where
they isolate a concrete error. Keep native prediction errors distinct from projection and
contextual interpretation errors. TC-10 assesses independent source opportunities and output
support; TC-11 owns assembled full-book adoption. A mocked native response or valid tree alone
cannot qualify these tasks. Provider unavailability leaves the named family qualification open.

<a id="TC-08"></a>

## TC-08 · Baseline GLiNER and d1 characterization questions

### Explicit primary tasks

The full profile attempts the following selected families over applicable source scopes, whether
or not a record extractor emitted a definition or assertion. These are **new versioned definitions**,
not a relabeling of current statistics questions. TC-01 owns their executable release spelling,
label meanings, option compatibility and support requirements. Do not install an unselected
classifier as a hidden fallback when a required call fails.

| Baseline family | Input/question and result | Dependency and source-support limit |
| --- | --- | --- |
| d1 source-first modal force | Exact clause/passage plus permitted structural context; propose located modal cues, target and epistemic/deontic/other declared force alternatives, including unresolved/insufficient source. Preserve overt auxiliary meaning separately from a proposed contextual reading. | TC-01–03 source-only state; no requirement for another model's candidate. A passage label or native probability does not supply an operator target or prove necessity. |
| d1 source-first quantifier/negation scope | Exact clause/passage; locate quantifier/negative cues and nominate restrictor, body, bound participant and relative scope alternatives. Keep “not every” distinct from “every ... not”. | TC-01–03; TC-06-B subsequently evaluates nominations against retained symbolic nodes. If native typed reads cannot return a complete graph, use versioned staged located reads and bounded explicit scope choices, preserving unexpressed relations as unresolved. Do not claim a span response represents arbitrary scope. |
| d1 source-first attribution | Exact source including quoted/embedded context; propose reporter/source mention, content, stance and nesting support. | TC-01–03; source-local mentions are not externally resolved speakers. Author assertion versus reported content remains explicit. |
| d1 source-first sentence/passage function | Exact focal scope plus declared heading/list/quotation context; overlapping assertion/question/instruction/definition/naming/assumption/example/explanation/hypothesis/contrast/description proposals with located support or explicit missing support. | TC-01–03; a completed source-only question runs even with no candidates. Context and function scope are retained independently from final domain record kind. |
| d1 unresolved host choice | Exact located qualifier/operator plus ordinary typed host candidates and relevant source context; explicit compatible host sets or bounded exclusive choices, with no-compatible-host, missing-candidate and insufficient-source alternatives. | Actual TC-05 constructions, TC-06-A symbols and TC-07 hypotheses with frozen list identity. A never-offered host is not rejected; combinations must name their scope and compatibility rather than arise from independent selected labels. |
| d1 unresolved referent choice | Unresolved located mention, ordinary entity/event/other typed candidates and source context; propose source-level antecedent or unresolved alternatives. | Actual TC-07 mention inventory and frozen candidates. This is linguistic reference, not retrieved conceptual-link selection. Keep missing candidate distinct from choosing none. |
| GLiNER located term/cue proposals | Exact source and released literal-only span schema; overlapping term mentions and modal/negative/quantifier/attribution/discourse cues, each with source support and native scoring provenance. | TC-01–03; preserve exact ordinary proposal versus decoded populations where observable. A cue does not decide force, scope or canonical concept identity. |
| GLiNER passage-function proposals | Exact source scope and released function label criteria; multilabel function observations with separate follow-up located support when available. | TC-01–03 and current classification custody; categories alone are not literal evidence. Current single-slice classification must be explicitly extended or invoked on exact slices with declared context, not silently presented as arbitrary discontinuous-context classification. |

These families need no custom learned head to begin implementation. Source-first discovery and
candidate-centered interpretation are independent operations with distinct input determinants.
Candidate-only tasks can be inapplicable when no unresolved candidates exist; that does not
silently skip applicable source-first families. Extra challenger/repair calls remain conditional.

### Native API contract and application work

Use `gliner2[local]==2.1.0`, `AutoExtractor` with the existing `GlinerProfile` and resident
worker, and `fastino/gliner2.5-base-v1@54785d51df8d86a0d8f2eb212fec15871aad2c4d`.
The [schema API](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py)
and [processor](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processor.py)
support declarative extraction/classification. Application declarations supply task meanings,
allowed source fields, role projection, source mapping and evidence eligibility. Keep literal
anchors outside schema-prefix choices; GLiNER's internal punctuation must not become source.
Ordinary native proposals, supplied-span diagnostics and decoded assignments have different
coverage. `score_candidates(return_auxiliary_logits=True)` or `score_explicit_spans()` is a
targeted omission diagnostic, not an automatic second production pass or directed binding scorer.
The [GLiNER adapter](../../../python/corpus-structure/src/corpus_structure/methods/gliner.py)
owns current request/observation custody; the
[discovery extraction account](../../library_leverage/libraries/text-characterization/extraction-classification-and-normalization.md)
explains the boundary/proposal distinction.

Use d1 `LiquidAI/d1-2B@652f920e544ea37f81e4b0ce89b81d4ed0da90b1` through the existing
artifact-verifying runtime and native `system_one`/`system_one_batch` owner.
[Pinned API](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/api.py),
[runner](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/runner.py)
and [calibration](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/calibration.py)
define native typed reads/choices and batching. Retain calibration identity and answer event
meaning; extraction presence, exclusive/multilabel choice and binary probability are distinct.
These APIs supply bounded typed answers, not a linguistic logical-form model. Application
question definitions and projection provide that missing contract. Reuse the current native
worker's packing, source-bound mapping and request/reply correspondence rather than invent another runner.
Do not widen provider bounds or claim CPU/device qualification from source inspection.

Implementation must:

1. Declare each new question/schema, options, native answer kinds, rendering, source scope,
   context policy and interpretation version in the existing release system. Use ordinary
   domain modules/configuration; no second prompt registry or workflow authority. Separate
   source linguistic taxonomy from domain vocabulary data.
2. Compile immutable source-only states independently from candidates. Candidate states include
   exact typed IDs, offered alternatives, premise/source links and frozen list identity.
   Only allowlisted source fields yield a literal witness. A candidate paraphrase, JSON escape
   or ambiguous substring cannot be promoted to original text. Map reads through the exact
   native pointer/half-open extent and original source-piece correspondence.
3. Retain native answer, per-family completion, examined context, scores, observed/withheld
   alternatives and projected typed proposal. A schema-valid unsupported answer stays
   unsupported. Where a graph requires multiple typed questions, record their dependency
   identities and incomplete intermediate state rather than inventing absent edges.
4. Attach proposals to enriched-document layers and TC-06-A terms/TC-07 hypotheses through explicit assertions
   and choice premises. Conflicting answers coexist with origin and support. No provider score
   selects scientific truth or changes source custody. Support-compatible proposals can be
   reused by TC-06-B's final evaluation and several consumers without repeating inference per
   extractor. Do not feed TC-06-B answers back into TC-08 automatically; unresolved results
   require an explicit new versioned demand before another inference pass.
5. Update reader/replay dispatch for the new operation versions and preserve earlier archived
   question semantics. TC-09 handles affected active consumer cutover; historical provider results
   retain their original scope and do not become new-task efficacy evidence.

### Failure, reuse and acceptance

Changing source/context membership, task wording/options/schema order, renderer, model/artifact,
effective runtime or decoding policy changes the relevant inference determinant. Changing only
construction interpretation can reproject compatible retained native answers where the operation
contract permits. Missing or withheld answers are explicit; an unattempted question is never
a completed empty result. Failed required baseline calls leave incomplete family coverage while
other characterization layers remain usable.

Unit checks challenge new task compilation, source-only independence, repeated identical literals,
candidate-field copying, typed host/referent identity, unknown/missing-candidate distinctions,
probability-event preservation and detached read fidelity. Expectations are independently authored;
production projection cannot generate its own semantic expected answer.

Actual native acceptance exercises every new applicable baseline family, using authenticated
source opportunities including absence/unresolved cases and competing scope/host/referent cases.
Grade located capture, answer semantics, projection and contextual use separately. Compare
GLiNER and d1 only on the same declared question and source, and distinguish ordinary discovery
from supplied-candidate diagnostics. Historical fair-coin/definition controls can remain regression
evidence; they cannot alone qualify modal force, quantifier scope or attribution. TC-10 owns
independent assessment and triggers any TC-I02/03/04 branch; TC-11 owns adoption.

## Evidence boundary

Source/reference inspection informed plan authoring on 2026-11-10; product/provider tests were
**not_run** at that date. The coordinator’s 2026-11-11 functional union now covers contextual and
model characterization, actual selected providers, retained populations and repeated-demand reuse.
Maverick/Dipo mention/discourse populations remain attributed evidence; model answers and inherited
hypotheses remain private proposals. The functional result does not establish linguistic accuracy,
complete corpus coverage, training benefit or full-book qualification.
