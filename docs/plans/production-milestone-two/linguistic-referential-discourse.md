# Linguistic, referential, and discourse observations

**Private execution · 2026-11-08.** This plan develops PM2-03–06 for
[HanLP O02](../../functional_reviews/production-milestone-two_2026-11-08.md#O02),
[Maverick O03](../../functional_reviews/production-milestone-two_2026-11-08.md#O03), and
[Dipo O04](../../functional_reviews/production-milestone-two_2026-11-08.md#O04).
The [coordinator](../production-milestone-two_2026-11-08.md) owns sequence and disposition.
The 2026-11-08 native results cover the bounded private scopes below.
Qualification at selected downstream consumers remains open.

## Shared integration boundary

Consume PM2-01's release-qualified source view and native product, prepared layout,
canonical token and sentence IDs, and ordered source mapping with each piece's retained
field choice. Use the runtime and artifact custody from PM2-02. Keep one adapter
per native contract. Each adapter emits typed, attributed observations under the existing
contribution machinery. Each input scope records coverage and terminal outcome independently.
A model or mode that fails, cannot run, or emits no result leaves other methods' observations
available. PM2-08 consumes the retained observations and witnesses and owns domain selection
and assembly. It can nominate context or alternatives without reparsing an already retained
scope. [Source context owner](../../../python/corpus-structure/src/corpus_structure/semantic/source_contexts.py) ·
[Contribution owner](../../../python/corpus-structure/src/corpus_structure/semantic/contributions.py)

The interfaces are domain agnostic. Eligibility depends on capabilities such as supported
language, canonical sentences, coherent running text, and available layout or speaker provenance.
The parser outputs keep their native semantics. Task definitions, terminology, allowed roles and
domain relationships enter through versioned released schemas and policies. A statistical proof
and a procedure use the same mapping, candidate, and partial-result path. Grinstead–Snell
supplies milestone assessment, and authored transfer controls exercise the same path with a
different domain configuration. Model limitations such as English checkpoint coverage or lack of
layout evidence are profile conditions.

### Shared located candidates

**Proposed.** Reuse [WCE03](../witnessed-corpus-enrichment/witness-and-parser-composition.md#wce03--native-candidate-collections-and-named-bindings)
and the retained annotation view. Prepare released, named `Matcher`, `PhraseMatcher` and
`DependencyMatcher` patterns once per compatible vocabulary/rule identity where this avoids
repeated work. Preserve overlapping contiguous candidates in native span groups and keep
all generating bases on the existing typed located products. Discontinuous roles retain their
ordered pieces and relations retain directed endpoints. The raw and reconciled groups and
unused preset suggester do not provide learned output. Retained column availability determines
each rule's prerequisites; an unavailable dependency rule does not erase valid phrase/token
work. Use a separately versioned annotation recipe for a demonstrated `AttributeRuler`
correction; do not mutate incumbent witness annotations or equate a token attribute change
with arc repair.
[Native rule owner](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) ·
[spaCy rule and span mechanisms](../../libraries/parsing/spacy.md#4-rule-based-matching-and-structured-extraction)

Compare retained spaCy syntax, then HanLP syntax/constituency, then added SRL at the same
consumer. Map roles by explicit released bindings; HanLP UD, Penn tags and SRL roles do not
become spaCy dependency labels. Preserve the retained `definition-scope-1` witness route.
HanLP alternatives can improve a candidate without replacing its independently required basis.
For the inherited positive-variance premise, compare a named exact cue and a bounded
cross-sentence/layout host policy before adding a head. The local UD marker path does not
cover that construction. Preserve the incumbent anchors, formula seam and alternative hosts;
reuse the [cross-block attachment pattern](../../../python/corpus-structure/src/corpus_structure/methods/predicate_cross_block.py)
only where its contract fits. Verify reported and conditional definitions, passives,
coordination, discontinuous roles and competing hosts as separate cases.

Use Maverick mentions or Dipo context only for named referent and attachment questions.
Preserve local scope, native labels and proposal identity; a cluster or rhetorical edge is
not an asserted corpus identity or semantic relation. On the fair-coin host and gambler
referent cases, reviewed alternatives did not fix d1 selection. Compare the existing scoped
deterministic route on the same candidates before broadening discovery. Refer residual
label or binding errors to the [learned extraction companion](learned-extraction-investigations.md).

<a id="PM2-03"></a>

## PM2-03 · Sentence structure and frame candidates with HanLP

**Input and realization.** Given authenticated sentences with canonical token IDs, use
`hanlp==2.1.7` and `EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_LARGE` with the
official `20250107_181612` archive and separately staged ModernBERT config and tokenizer
at `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`. Verify the archive digest and the
completeness of state-dict loading at provisioning. Start with the current Torch 2.15.0
and Transformers 5.22.1 as compatibility candidates. PM2-02 records the qualified runtime,
configuration, and effective limits. Call the model on lists of canonical tokens using
`tasks=["lem","pos","dep","srl","con"]` and `skip_tasks="tok"`. Select supplementary
`ner` in the same invocation for a consumer that uses it. The checkpoint declares the
tokenizer as a dependency and the explicit skip preserves caller tokenization.
[HanLP reference](../../libraries/parsing/HanLP.md) ·
[Release wheel](https://pypi.org/project/hanlp/2.1.7/#files) ·
[Large archive](https://ftp.hankcs.com/hanlp/mtl/en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612.zip) ·
[Backbone snapshot](https://huggingface.co/answerdotai/ModernBERT-large/tree/45bb4654a4d5aaff24dd11d4781fa46d39bf8c13)

**Contract and consumers.** Map one-based UD heads through the sentence token map with
zero as the native root sentinel. Retain Penn Treebank tags separately from UPOS and
morphology. Preserve native SRL argument spans, continuation and reference roles, and
validate the ordered constituency yield before producing located phrase or clause
intervals. Require both mapped endpoints and exact source evidence. Preserve discontinuous
extents through source pieces. Refuse a partial protected atom as support for a whole atom.
HanLP's flat NER and generic SRL roles remain evidence. SRL emits a predicate marker
only when an argument survives decoding and its configured argument width is 30 tokens.
Build a versioned UD-aware path into the existing frame, cue and witness contracts,
including alternatives for coordinated hosts. Existing spaCy `prep`, `pcomp`,
`obl:agent` and `neg` assumptions require explicit tests against the new evidence.
Keep the current spaCy route for every consumer until the replacement is qualified for
its actual role and scope. Reuse `PhraseMatcher` and unfiltered `SpanRuler` for overlapping
terminology. A reviewed dictionary override remains a separately attributed observation.
[Native output conventions](https://hanlp.hankcs.com/docs/data_format.html) ·
[Predicate frames](../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py) ·
[Rule preparation](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)

**Strong definition witness.** Identify consumers that mint or use a
`DefinitionBasisWitness`. The current `definition-scope-1` route binds the exact
retained `extract.m1_annotations/2` task, source and rule, and requires complete
`DEP`, `POS`, `SENT_START`, `LEMMA` and `TAG` columns. Preserve the spaCy-backed
route for these consumers. HanLP can contribute separately located evidence. Any
replacement strong witness needs a released scheme-aware contract and equivalent
producer, native and detached checks. Exercise a qualification inside defining
content versus a qualification of the defining act, reported and conditional
acts, competing bindings, and unresolved demonstratives.
[Definition witness owner](../domain-model-alignment/semantic-admission.md#DMA-05) ·
[Portable witness replay](../../../python/corpus-structure/src/corpus_structure/serve/model_observation_replay.py)

**Execution and closure.** Use actual subword lengths and sentence boundaries to form
outer batches. The checkpoint's 8192 sequence setting and first-task sampler settings
of 128 examples and 12,800 tokens are inspected defaults. The native call shares encoder
work within an internal batch, and the selected first task owns the dataloader. Arbitrary
prediction kwargs do not alter that sampler in 2.1.7. Compare observed resource behavior
at the proposed envelope with the corresponding Base checkpoint using the same scopes and
heads. Mark unsupported sentences explicitly and preserve available results. Cutting a
sentence around a protected atom removes the possibility of observing relations across the
cut. Use existing spaCy, then HanLP syntax and constituency, then the additions of SRL,
NER or terminology as matched comparison arms as relevant. Close the initial package when
native anchored frames and host candidates reach the retained consumer with correct
argument and qualifier distinctions, and protected atoms, repeated tokens, missing SRL
predicates, nested clauses, modal and passive constructions, and coordinated hosts behave
as declared. Report native and transformed errors separately. [Multitask execution](https://github.com/hankcs/HanLP/blob/master/hanlp/components/mtl/multi_task_learning.py)

### Located modifiers and clause scope

**Proposed · [Structuring I03](../../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I03).** Reuse HanLP 2.1.7 retained
dependency, SRL and constituency results to project temporal, purpose, manner and causal
modifier candidates and clause containment where it changes a consumer's answer. Keep
native scheme, predicate member, exact extent and scope. Do not promote a temporal
phrase to a deadline or an SRL causal label to an admitted causal claim. Compare the
existing spaCy named rules and bounded dependency/conjunct traversal with HanLP syntax
and the incremental SRL evidence on the same release question. PM2-08 owns the
selected association, not the parser adapter.

For the definition path, the later
[native HanLP chain](../../design_review/evidence/2026-11-09_pm2-native-definition/README.md)
passed bounded private transport. Independently grade the released declaration-to-use
binding with competing declarations and the constant-density control. Separate that
question from the earlier sentence-split recovery. PM2-06 may compare a pinned HanLP
sentence detector or a separate SDP/AMR head only after isolating a residual boundary
or relation failure and checking label and exact-map fit.

<a id="PM2-04"></a>

## PM2-04 · Mention inventories and coherent-section coreference with Maverick

**Input and realization.** Start with `maverick-coref==1.0.7`, staged
`sapienzanlp/maverick-mes-ontonotes` at `087a90f0380ec1f20ed19732b657f53fd3542c81`,
weight SHA-256 `b42053ce171ea904d10d92de5458dce2e8189ef1050e1705e7fced50d2479c1f`,
and staged `microsoft/deberta-v3-large` configuration and tokenizer at
`64a8c8eab3e352a784c658aef62be1662607476f`. Resolve the backbone artifact alongside
the checkpoint because the public model-name loader cannot pin the weight revision and
resolves the backbone separately. Start with isolated CPython 3.12 for the pinned
SentencePiece 0.2.0 and protobuf 3.20 dependencies. Qualify the exact Torch, Lightning,
and Transformers bundle by staged checkpoint deserialization and native execution.
Use `Maverick.predict` with nested canonical sentence tokens and a bounded coherent
section. Keep the native forward seam for the mention inventory in the same invocation
as clustering. [Maverick reference](../../libraries/parsing/maverick-coref.md) ·
[Package declarations](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/setup.py) ·
[Checkpoint](https://huggingface.co/sapienzanlp/maverick-mes-ontonotes/tree/087a90f0380ec1f20ed19732b657f53fd3542c81) ·
[Backbone](https://huggingface.co/microsoft/deberta-v3-large/tree/64a8c8eab3e352a784c658aef62be1662607476f)

**Contract and consumers.** Project both inclusive endpoints into the canonical token
map and then into source extents. Reject missing, inverted, injected, or out-of-source
endpoints. Preserve overlapping and nested mentions with stable identities. Keep the
ordinary MES `mention_idxs` detection inventory distinct from cluster membership and
unassigned mentions. Public clusters, including `singletons=True`, do not establish
the inventory or exhaustive singleton coverage. Represent coherence and examined scope
explicitly. Exact shared mentions can nominate cross-section links without establishing
transitive identity. A competing cluster remains an alternative. Frame composition can
use a selected local referent and its evidence. Event reference, acronym or concept
equivalence, and broader identity have distinct operation questions.
[Public wrapper](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/maverick_model.py#L48-L208) ·
[Endpoint mapping](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/common/util.py#L91-L107)

**Execution and closure.** Set a post-tokenizer admission envelope in PM2-02 and split
an unsupported larger scope on coherent source boundaries with explicit unexamined
cross-boundary pairs. Run ordinary prediction and `predefined_mentions` on the same
scope as controlled assessment arms. That mode substitutes the candidate spans after
extraction, so report mention detection separately from antecedent or cluster errors.
Validate mapping, preservation of nested mentions, false merges and split chains,
and the affected participant binding. Include a genuine local antecedent, a competing
mention, a cross-section unassessed case, and a bound refusal. Compare exact boundaries
and downstream contribution against the current local-reference route. Treat all
diagnostic scores as model scores and apply independent controls to metric wrappers.
The initial package closes with anchored mention inventory and supported section
membership available to PM2-08, including honest noncoverage of pairs outside scope.
[Native MES scoring and inventories](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L129-L451)

### Informative local referent candidates

**Proposed · [Structuring I03](../../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I03).** Reuse retained Maverick mention
and cluster products. Compare the current nearest earlier located member with a name
or nominal selected from retained syntax, with the nearer mention retained separately
if it helps the same question. Preserve scope, cluster provenance and the representative
decision. Do not infer global identity. Use supplied mentions only to distinguish
inventory from clustering errors; they do not bypass all native detection. Probe a
segmented joint mode under PM2-06 only for demonstrated cross-partition misses, with
exact boundary, false-merge and resource controls. A d1 disagreement does not erase
the independently inspectable local proposal.

<a id="PM2-05"></a>

## PM2-05 · Source-aligned discourse observations with Dipo

**Input and realization.** Use `dipo==0.2.1` by distribution metadata and `DMRSTParser`.
Stage `larc-iu/dmrst-ettin-400m-gum-12.1.0` at
`e33906a27f89b2703df8ab19e471aa82141d62cb`, weight SHA-256
`85a2590374d2d3bd82a04dcfa474869a8ae2ee6a64074e61b41540aed6633f24`, and
`jhu-clsp/ettin-encoder-400m` at `7662476d60abb071a5bd319c9f3074f3072c062d`.
Start with isolated Python 3.12, FP32, the checkpoint LoRA configuration and stride 100.
Qualify exact Torch, Transformers, tokenizer and PEFT dependencies. The native loader
uses `weights_only=False` and resolves the backbone and tokenizer separately from parser
weights. PM2-02 provisions verified artifacts and qualifies both cold start and inference.
[Dipo reference](../../libraries/parsing/dipo.md) ·
[Checkpoint](https://huggingface.co/larc-iu/dmrst-ettin-400m-gum-12.1.0/tree/e33906a27f89b2703df8ab19e471aa82141d62cb) ·
[Backbone](https://huggingface.co/jhu-clsp/ettin-encoder-400m/tree/7662476d60abb071a5bd319c9f3074f3072c062d) ·
[Tagged loader](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/inference.py#L72-L88)

**Contract and consumers.** Feed coherent retained running text to
`predict_from_text(..., break_at_paragraphs=False)`. The existing BIE/CRF stage
predicts boundaries. The native default `True` also adds blank-line and heuristic
heading boundaries. Compare on the same raw text and enable layout forcing for
qualified layout semantics. Capture final post-merge EDU token and character
boundaries at the native recovery seam, with learned, forced, coincident and merged
provenance. Map through normalization to ordered retained source extents, preserving
unmapped leading gaps and synthetic separators as coverage or diagnostic details.
Retain native binary ordered child ranges, nuclearity, relation and singleton units
once, together with exact source coordinates. PM2-08 uses range references to bounded
context and can point outside the immediate package. Derived subtree extraction, RS4
export and debinarized views can drop distinctions, prefixes or singleton coverage.
A rhetorical condition can nominate a qualifier host. Rhetorical evidence, ordering
and attribution have their own scope and do not establish a verified support
relationship, procedural dependency or an endorsed assertion.
[Boundary recovery](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L66-L144) ·
[Native inference](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L682-L818) ·
[Tree ranges and exports](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py#L374-L518)

**Execution and closure.** Begin with bounded logical sections. Qualify independent
window and EDU limits because the tagged encoder batches overlapping windows ahead
of global decoding. Test the actual boundary near the tokenizer's 8192 positions
and backbone's configured 7999, along with cold-start and active-scope resource use.
Section fallback exposes the actual coverage and leaves cross-section discourse
attachments unresolved. Use `predict_both()` to pair supplied and model-predicted
EDUs over an EDU-reconstructed input with shared encoding and both mappings.
Separate that control from the raw layout comparison. Test repeated text, Unicode
and whitespace normalization, merged empty units, singleton trees, hard wraps,
cross-block extents and oversize fallback. Score boundaries, parent yield, child
split, relation and nuclearity separately. Close the package when the native and
projected output supports a bounded context consumer without invented anchors and
the paired assessments can isolate boundary errors from structural errors.
[Window execution](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/encoding.py#L417-L474)

### Discourse alignment for a conditional context comparison

**Conditional · [Structuring I06](../../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I06).** Preserve focal EDU, ordered
child split, parent yield, relation, nuclearity, eligible sibling ranges and omissions
for PM2-09. Compare raw end-to-end and reviewed EDU paths separately:
`predict_both()` uses reconstructed inputs. Attribute missing child, wrong split and
label or nuclearity errors only where exact alignment allows that judgment. A valid
tree or constrained decode does not prove source fidelity. A wider or generative mode
stays under PM2-06 until diagnosed loss requires it.

## Parser execution

**Implemented · 2026-11-08.** `ci run parsers --request FILE` takes an admitted
private release and input realization, exact completed-source references, bounded
half-open character scopes, and locked provider profiles. All three operations
share the source-view preparation, claim, contribution and Reader paths. The
runner verifies the source pins and uses the selected view's canonical tokens and
sentences for HanLP and Maverick. It preserves the exact projected text for Dipo.
Multiple results for a method and view are addressed by selected task ID.
[Execution evidence](../../design_review/evidence/2026-11-08_pm2-parsers/README.md)

**Tested private scope · 2026-11-08.** Run 416 completed 18 requested book
scopes and two smaller scopes after an oversized request, sealing cut 520.
Run 417 reused two exact HanLP scope origins at cut 521. The Reader retained
distinct HanLP frame populations, the Maverick ordinary and supplied inventories,
and eight Dipo operations with ten ordered trees. Source-only and changed-projection
pins refused authentication. An alternate released vocabulary retained all
three native product families and an intentionally failed profile in one run.
Development admitted the parser release on `semantic_pm2_parser_methods`.
Postmigration checks recovered the same 29 views in cuts 514 and 517 and read
the retained HanLP task from cut 520. A fresh two-scope HanLP run sealed cut 522.
The [qualification account](../../design_review/evidence/2026-11-08_pm2-parsers/README.md#development-deployment-and-qualification)
records the passing private parser checks and the original repository-wide failures.
The [completion audit](../production-milestone-two_2026-11-08.md#completion-audit)
records the current scoped rerun and the still-open qualification union.
PM2-11 owns paired release-level assessment.
[Native execution receipt](../../design_review/evidence/2026-11-08_pm2-parsers/records/pm2.private-parser-stage.json) ·
[Alternate vocabulary receipt](../../design_review/evidence/2026-11-08_pm2-parsers/records/pm2.alternate-vocabulary.json) ·
[Development deployment receipt](../../design_review/evidence/2026-11-08_pm2-parsers/records/pm2.parser-development-deployment.json)

| Package | Implemented private scope | Qualification boundary |
| --- | --- | --- |
| PM2-03 | Located UD and SRL predicate frames, constituency spans and candidate qualifier hosts. spaCy remains the producer for the released strong definition witness. | The matched M1 → HanLP syntax → SRL comparison at the released consumer is open. The expanded variance case still missed the cue. Additional heads and consumer migration belong to PM2-06. |
| PM2-04 | Separate detection, supplied mentions and local cluster memberships. A supplied-only unclustered mention remains inspectable. The common scope path preserves a limited parent when smaller scopes run. | The native competing-mention, cross-section coverage and Maverick-specific bounded fallback journey and local-reference comparison remain open. The retained book fallback was HanLP. Local clusters do not establish broader identity or calibrated ranking. |
| PM2-05 | Ordered native trees, post-merge boundary provenance, reviewed-EDU pairing and a bounded context selector used by private reads and contextual query rendering. | The named cases distinguish segmentation, ordered split and labels. Native coherent-scope fallback and independent downstream improvement remain open. PM2-08 owns the typed composed context product. |

The [parser design review](../../design_review/reviews/design_review_pm2-parsers_2026-11-08.md)
owns the reviewed reasoning. The execution disposition is here.

| Review finding | Execution disposition |
| --- | --- |
| F01 | Release-owned parser payload contracts bind HanLP, Maverick and Dipo fields to their operation question. Lowering, composition and contextual consumers passed 22 targeted checks (`6fbd3ce315fa406a9a4b9ad5ae556838`). Protected native admission refused malformed payloads, wrong questions and generic fallback, then accepted the valid payload (`22812341406048d68cd6eb089c3fcd02`). Full composition, selection and admission still need their native journey. Strong definition witness migration remains conditional in PM2-06. |
| F02 | Authenticate the exact finished source and select parser results by task. A coherent split creates distinct scope inputs. |
| F03 | Keep the native Dipo encoder window and decoder EDU guards separate. Validate both reconstructed arms and retain source gaps and unmapped items in the scope result. |

<a id="PM2-06"></a>

## PM2-06 · Qualify extended parser modes only for demonstrated gaps

**Disposition · 2026-11-09.** Keep the ordinary bounded profiles. The observed
variance passage exposes a missing cue in the expanded HanLP scope, but does
not establish that a new head repairs the premise or its attachment. Retain the
separate strong definition witness. The supplied Maverick arm adds “her capital”
as a distinct unclustered candidate; no independently supported downstream
participant gain has qualified the mode. Retain Dipo's learned, layout and
supplied arms as controlled diagnostics; no paired result yet shows that a larger
scope improves an accepted reading. Revisit each mode when a frozen operation
case isolates the respective failure and the proposed mode changes the consumer's
answer within the operating bounds below.

PM2-06 consumes the ordinary provider profile and the relevant operation-level
comparison. Record the unmet source opportunity or operating need and its present
failure mode before choosing a challenger. A failed or unavailable investigation
keeps the ordinary bounded profile and leaves the corresponding operation's gap
visible. Prefer source-faithful repair and released native primitives to a new
decoder or model. The coordinator owns conditional activation and disposition.

| Investigation | Evidence that changes the selected profile |
| --- | --- |
| HanLP extra heads and decoding | Add one SDP formalism per arm and compare incremental correct frame or attachment candidates. Keep DM, PAS and PSD separate. At the inspected settings, the paths return threshold-decoded arcs with `apply_constraint` disabled. Qualify each requested constraint against actual graph semantics. Supplementary NER, `hanlp_trie.Trie.parse`, and dictionary overrides require an identified limitation of current evidence or rules. Use standalone parsing, custom heads, nested NER training, or distillation only for a persistent diagnosed quality, coverage or resource gap. [HanLP reference](../../libraries/parsing/HanLP.md) |
| Maverick segmented encoding and joint clustering | Reuse MES encoder, mention detection and clustering with sentence-respecting segment preparation, stable document mention coordinates and a joint inventory. Apply limits to segment subtokens and to projected mention count before dense pair/category allocation. The `naive` branch retains quadratic masking and unsafe boundaries, and `proper` is a stub. Qualify a narrow adapter with one-segment parity, exact multi-subtoken endpoints, real cross-boundary gain, a false-merge control, dense fallback and bounded native resource use. A coherent-section route remains valid. [Native long-document paths](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L394-L588) |
| Maverick controlled repair and diagnostics | Require a validated union of names, nominals and pronouns for production `predefined_mentions` repair, then test downstream participant gain. Where actual speaker provenance is present, validate exact speaker/token cardinality and mapped endpoints before use. Retain only bounded eligible-antecedent diagnostics, including the winner, runner-up, native null heuristic and useful MES category, with masked candidates excluded. Seed only a reviewed disjoint partition over stable members and keep before/after views. Model proposals cannot be passed as gold. Compare MES PreCo before retraining for a demonstrated singleton gap. Consider LitBank for a diagnosed narrative gap. S2E and Incremental require their own adapter and qualification where evidence warrants a different scoring architecture. [Native scoring and seeds](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L129-L387) |
| Dipo broader context and alternatives | Enable larger coherent scopes after demonstrated context gain within the qualified window, EDU and residency envelope. Default to bounded d1 interpretation of candidate hosts alongside the original tree. Recurring reviewed label errors can justify instrumenting the joint label/nuclearity readout on a fixed split. Topology repair requires complete ordered alternatives or controlled redecoding with branch-specific state. The greedy path supplies neither calibrated edge confidence nor n-best trees. Consider LoRA or DoRA only after controlled EDU comparisons identify a persistent learned-model error and independent training and assessment cases are available. Grammar-constrained or ICL parsers remain separate research for a persistent gap. [DMRST decoder](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L638-L679) |

The controlled comparison uses fixed eligible populations and explicit unavailable
outputs. For Maverick, qualify any low-level MUC, B³, CEAF or LEA use against
independent singleton conventions and asymmetric precision/recall. The bundled
recall accessor and Lightning argument order need special scrutiny. For Dipo,
adapt the cascade decomposition to DMRST because the tagged script omits that path.
Use the paired metric primitive only with explicit failures and grouping appropriate
to the fixed source population. A single exposed book does not provide multiple independent document replicates. The stock comparison's intersection of available outputs
would hide lost cases. Parser diagnostics support improvement decisions without becoming
the authority for an accepted semantic relation.
[Maverick metrics](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/common/metrics.py#L38-L68) ·
[Dipo paired metric](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/metrics.py#L181-L241) ·
[Dipo comparison selection](https://github.com/larc-iu/dipo/blob/v0.2.1/scripts/compare_runs.py#L86-L127)
