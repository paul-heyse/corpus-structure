# Production milestone two functional extension review

**Proposed · 2026-11-08.** The recommendation is a four-model release that adds useful
structure even when one provider, attachment, or complete-record interpretation is unavailable.
Start with HanLP over canonical sentences, Maverick over budgeted coherent sections, Dipo over
source-aligned discourse scopes, and d1-2B for routine source discovery and bounded
interpretation. Keep document-wide coreference as a milestone target behind a qualification
gate. Begin with a section profile so that useful reference evidence reaches frame consumers
before the internal document adapter is ready. Use existing GLiNER extraction and classification
as scoped comparators and contributors. Keep a separate GLiNER Decide deployment conditional
on a demonstrated operation-specific advantage.

The baseline is the [supplied M2 design](../target-pipeline-design/production-milestone-two.md),
including the revision beginning at line 410, and the four supplied library guides and addenda
linked in the profiles below. The later revision governs conflicts. The repository source
baseline is `22cd44aaf`. The supplied design and guides inspected from the working tree
are recorded in `4c71fa3f4`. The [crosswalk](#baseline-disposition) reconciles both passes.
The recommendations use the [selected design standard](../design_review/design_principles/standard.toml),
particularly scoped semantic authority, precise attributed relations, independent assurance,
and qualitative execution fit (FP-04, FP-06, FP-07, CI-01–06).

**Evidence boundary.** “Interface-checked” below denotes dated source inspection of the cited
release, artifact, or revision. Repository examples retain their original Tested scope.
M2 checkpoint inference and corpus qualification are `not_run`. The four candidate model
assets were unavailable in the inspected local caches, and the first three packages were
absent from the application environment. On 2026-11-08, `nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader`
failed with an NVML driver/library mismatch. The installed PyTorch CUDA availability check
returned true. Neither observation establishes model execution, capacity, or performance.
The checkout supplies retained statistics material and authored controls, including
[ownership fixtures](../../fixtures/toy/README.md). It supplies no identified representative
enterprise evaluation corpus. The business scenarios below are authored expectations.
No corpus quality, calibration, or throughput benefit is claimed.

## Current reuse and authority

| Current boundary | Consequence for M2 |
| --- | --- |
| Atom-preserving sentence and annotation preparation, with block-local token heads, named columns and availability. The retained predicate consumer reconstructs spaCy-shaped dependencies and optional morphology. [Annotation producer](../../python/corpus-structure/src/corpus_structure/ingest/annotations.py) · [Predicate frames](../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py) | Share the prepared layout and its source maps. Add HanLP as a parallel observation profile. Bind new transformations explicitly to UD and its available heads before migrating any spaCy consumer. |
| Ordered projection addresses, exact formula witnesses and typed visual location sit under DMA. The selected source, native pieces and synthetic separators have distinct meanings. [Projection owner](../plans/domain-model-alignment/source-projection.md) · [Visual evidence owner](../plans/domain-model-alignment/visual-evidence.md) | Compose each model's native coordinates with the selected projection. Where a prediction touches only part of a protected atom, retain the diagnostic and withhold the unsupported semantic attachment. Visual questions use exact retained regions. |
| The live baseline has scoped predicate and qualifier work, witnessed links, operation-event assessment, and rooted delivery. The full-book development successor reached source-ready cut 512. The DMA cutover still has an evaluated GLiNER caller-path obligation. [Checkpoint](../../STATUS.md) · [DMA-13](../plans/domain-model-alignment_2026-11-08.md#dma-13) · [Witnessed enrichment owner](../plans/witnessed-corpus-enrichment_2026-11-05.md) | Use the retained examples as regression controls and the caller-side literal-only proposal as an input to comparison. M2 does not establish that the GLiNER blocker is closed. Keep source and completed independent contributions usable across provider failures. |
| Named contribution reads distinguish operation outcome, private contribution, interpretation, and public standing. [D8 contribution inspection](../design/D8-agent-and-query-interfaces.md#independent-contribution-inspection) · [Assessment and comparison](../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py) | Expose M2 through the same selection and witness path. Add a product or relation only where its meaning and consumer require it. Keep protected grades outside producer inputs. |

<a id="O01"></a>

## O01 · Source-faithful observations that can be recomposed

**Proposed.** Give the operator and agent a durable answer to “where did this part come from,
and which operation could improve it?” Use the selected source view and ordered projection
pieces as common input custody. Canonical token/sentence IDs belong to the prepared layout.
Each native scope carries an ordered map, which may include gaps, synthetic boundaries, and
more than one retained source extent. An adapter can normalize text for its model and preserve
that normalization separately. A guessed occurrence from a substring search has no place in
the exact mapping. A legitimate discontiguous result uses multiple source extents. A result
whose mapping is ambiguous may remain a private diagnostic.

Bind the operation to its source, scope, effective runtime, exact artifacts, task definitions,
effective configuration and declared alignment. Retain native labels, coordinate shape and
available scores, plus typed normalized observations and the actual scope covered. Distinguish
ineligible, eligible but unscheduled, unsupported scope, partial coverage, failure/cancellation,
successful empty, and successful nonempty. Follow the existing operation vocabulary and
use reason and coverage detail where those distinctions already fit. Model-level output
availability is separate from task settlement. A rejected d1 candidate, a missing supplied
candidate, and an extraction pointer with no result therefore remain distinguishable.

Reuse native observations when a mapping from already retained native coordinates, a composition
rule, or a downstream acceptance policy changes. A different effective sentence/window,
tokenizer, requested head, prompt, question set/order, candidate set/order, media,
or inference setting creates a new inference input. Reuse exact immutable provider work when
its determinants match and bind its findings to each occurrence independently. A new admission
policy rechecks eligibility against its own assessed evidence. This keeps qualification and
publication local to the affected results and avoids reprocessing a full document for every
changed qualifier. Use the existing method, retained task, semantic release and admission
owners (DESIGN §B1–B2, §B4–B6). [D6 lifecycle and reuse](../design/D6-orchestration-metrics-policies.md) · [DMA semantic admission](../plans/domain-model-alignment/semantic-admission.md)

<a id="O02"></a>

## O02 · Build clause and participant candidates with HanLP

**Proposed profile.** Qualify `hanlp==2.1.7` with
`EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_LARGE` first. Use the official
`20250107_181612` checkpoint archive and pin its digest at provisioning. Stage the separately
resolved ModernBERT configuration and tokenizer from the candidate snapshot
`45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`. The inference path constructs the encoder
from its configuration and loads the archive's state dict. Check weight-load completeness.
Use the corresponding Base checkpoint as a matched smaller
comparison, particularly for CPU or latency-sensitive work. Start with a compatible candidate
built from the workspace's Torch 2.15.0 and Transformers 5.22.1. The published package minimum
and model minimum differ, and neither establishes that the 5.22.1 load, encoder, and decoder
work together. Qualify the exact bundle. [HanLP guide and addendum](../libraries/parsing/HanLP.md) ·
[HanLP 2.1.7 distribution](https://pypi.org/project/hanlp/2.1.7/#files) ·
[Checkpoint catalog](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/mtl.html) ·
[Backbone snapshot](https://huggingface.co/answerdotai/ModernBERT-large/tree/45bb4654a4d5aaff24dd11d4781fa46d39bf8c13)

**Interface-checked, 2026-11-08.** The official Large archive exposes
`tok, lem, pos, ner, srl, dep, sdp/dm, sdp/pas, sdp/psd, con`. Use the callable model on
a batch of lists of canonical tokens with
`tasks=["lem","pos","dep","srl","con"]` and `skip_tasks="tok"`.
The explicit skip matters because task resolution adds the tokenizer dependency. Request
supplementary `ner` in the same invocation when a consumer needs it. The encoder is shared
within an internal batch. The first selected task owns the inference dataloader and the 2.1.7
path does not apply arbitrary prediction kwargs as batch settings. The inspected Large
config records an 8192 sequence setting, disabled long-sequence truncation, and a sampler
configuration of 128 examples and 12,800 tokens with effective padded-token accounting
disabled. Treat these as inspected settings. Bound outer batches by actual subword length
and qualify the longest eligible inputs, including decoder work and any sliding-window
behavior. If an input falls outside the profile, report scope and preserve other model outputs.
Avoid cutting around a formula and claiming that concatenated parses recover relations
across the cut. [Large checkpoint archive](https://ftp.hankcs.com/hanlp/mtl/en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612.zip) ·
[Native multitask execution](https://github.com/hankcs/HanLP/blob/master/hanlp/components/mtl/multi_task_learning.py)

The native `pos` is Penn Treebank tagging for this checkpoint. It cannot populate the
existing universal POS or morphology columns directly. Translate UD roots and sentence-local
one-based heads through the canonical map. The native label vocabulary includes `case`,
`obl` and `nsubj:pass`. Existing `prep`, `pcomp`, `obl:agent` and `neg` rules require
different evidence on the new route. Preserve native SRL predicates and argument spans,
including continuation/reference labels. The decoder emits a predicate marker only when
an argument survives decoding, with a configured argument-width limit of 30 tokens.
Check exact ordered constituency leaves before
emitting phrase and clause intervals. The selected NER is flat. Keep dictionary matches as
separate overlapping located evidence and apply any reviewed override as a separate observation.
Use the existing `PhraseMatcher` and unfiltered `SpanRuler` first. HanLP's
`hanlp_trie.Trie.parse` is an alternative for overlapping matches if the existing route
has a concrete limitation. [Existing rule preparation](../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)

The inspected SDP paths return graph arcs and use threshold decoding with `apply_constraint`
disabled. Retain DM, PAS and PSD as separate formalisms. Require a reviewed recovery case for
an additional head or a decoding change. A graph label, SRL argument, or generic NER type alone
establishes no domain role. [Native output formats](https://hanlp.hankcs.com/docs/data_format.html)

A frame consumer gains full argument extents, subordinate qualification, and alternatives for
coordinated hosts. Use the existing frame identity and witness vocabulary where compatible,
with a new versioned UD-aware transformation. Compare the current spaCy cue owner, HanLP
syntax and constituency, and the incremental value of SRL and terminology on identical
source opportunities. Keep spaCy tokenization, matchers and proven rules in service until
each consumer migrates. Test passive and modal constructions, coordinated predicates, native
sentence boundaries, protected atoms and ambiguous attachments before removing any redundant
statistical work. An optional standalone parser, custom head, nested NER training or
distillation earns consideration when a concrete coverage, quality or operating gap remains.

<a id="O03"></a>

## O03 · Enrich frames with local referents through Maverick

**Proposed profile.** Qualify `maverick-coref==1.0.7` and
`sapienzanlp/maverick-mes-ontonotes` at `087a90f0380ec1f20ed19732b657f53fd3542c81`,
with a staged local `weights.ckpt`
and separately pinned DeBERTa backbone and tokenizer. The reference backbone candidate is
`microsoft/deberta-v3-large` at `64a8c8eab3e352a784c658aef62be1662607476f`.
Use an isolated CPython 3.12 worker as the first environment candidate. The package fixes
SentencePiece 0.2.0, whose available CPython wheels end at 3.12, and also fixes protobuf
3.20. Select the exact Torch, Lightning and Transformers bundle by trusted checkpoint
loading and CPU/GPU native execution. The public model-name loader has no revision argument
for the weights and upstream backbone loading is separate. Verify the local weight SHA-256
`b42053ce171ea904d10d92de5458dce2e8189ef1050e1705e7fced50d2479c1f`
from Hub metadata and the full dependency resolution. [Maverick guide and addendum](../libraries/parsing/maverick-coref.md) ·
[Package declarations](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/setup.py) ·
[Checkpoint snapshot](https://huggingface.co/sapienzanlp/maverick-mes-ontonotes/tree/087a90f0380ec1f20ed19732b657f53fd3542c81) ·
[Backbone snapshot](https://huggingface.co/microsoft/deberta-v3-large/tree/64a8c8eab3e352a784c658aef62be1662607476f)

**Interface-checked, 2026-11-08.** Pass nested canonical sentence tokens to `Maverick.predict`
for the ordinary clustering route. This bypasses raw-text preprocessing and its reconstructed
character positions. Convert both inclusive endpoints from the aligned token map and reject
special-token, missing, inverted, or out-of-source endpoints. Use a narrow adapter on ordinary
MES forward output for the detected mention inventory. Public clusters do not expose that
inventory or the full logits, even with `singletons=True`. Record native mention detection
separately from valid cluster membership and unassigned mentions. OntoNotes's training
conventions do not establish exhaustive singleton detection. Preserve overlapping/nested
mentions. For genuinely attributed messages or transcripts, check exact speaker/token
cardinality before the wrapper can truncate the sequence through `zip`, and verify
both subtoken endpoints after speaker insertion. Enable the speaker-aware production mode
only on that qualified input profile. [Wrapper and public API](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/maverick_model.py#L48-L208) ·
[Token and speaker mapping](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/common/util.py#L91-L107)

Process a complete coherent scope when qualified. Otherwise use logical sections and expose
which spans and cross-boundary pairs the run could examine. Exact shared mentions can
nominate cross-section links. Preserve incompatible memberships as alternatives. A selected
local referent enriches a frame participant and carries its member anchors. Distinct operations
handle event references, acronym or concept equivalence, and identity across documents.

Keep segmented encoding with joint clustering in M2 as a gated extension. Reuse MES encoder,
mention extraction and clustering functions with sentence-respecting segments, gather the
needed mention representations and map them into one ordered document inventory. Apply a
subtoken limit before encoding and a mention-count limit before dense pair or category
allocation. The inspected `longdoc="naive"` branch retains quadratic mask work and fragile
boundary indexing, and `proper` is a stub. A public flag would inherit those behaviors.
Qualify a narrow adapter with one-segment parity, a true cross-boundary chain and a false merge,
nested and multi-subtoken mentions, real speaker changes and dense-section fallback.
Set the budgets from that sweep. The advertised encoder positions and the research window
setting are inputs to the sweep. [MES modes and scoring](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L394-L588)

Use `predefined_mentions` immediately for the paired diagnostic, with independent reviewed
mentions on the identical scope. The path replaces mention candidates after extraction.
Allow targeted production repair only with a validated union that includes names, pronouns
and descriptions. A bounded score diagnostic should retain mention boundaries, the eligible
earlier candidates, winner, runner-up, native null heuristic and MES category where useful.
Exclude masked pairs from ranking and label the quantities as model scores. That enables
category-stratified false-merge and false-split review without retaining a dense matrix.
Keep `add_gold_clusters` conditional on reviewed seeds in the scoring inventory, stable
member identity and disjoint output partitions. The inspected decoder can leave duplicated
membership when seeds connect. Preserve before/after views and keep model-proposed repairs
outside the gold seed input. If singleton coverage becomes a priority, compare the released
MES PreCo checkpoint on the same declared mention policy before changing training or
architecture. [MES mention extraction and clustering](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/model_mes.py#L129-L387)

<a id="O04"></a>

## O04 · Turn Dipo trees into source-backed context

**Proposed profile.** Use `dipo==0.2.1`, `DMRSTParser`, and
`larc-iu/dmrst-ettin-400m-gum-12.1.0` at
`e33906a27f89b2703df8ab19e471aa82141d62cb`, with the separately resolved
`jhu-clsp/ettin-encoder-400m` snapshot
`7662476d60abb071a5bd319c9f3074f3072c062d` as the qualification candidate.
Use a pinned isolated Python 3.12 environment with compatible Torch, Transformers,
PEFT and tokenizer dependencies. The package's compatibility floor does not establish that
arbitrary newer versions interoperate. Qualify both exact snapshots, including trusted
deserialization and cold-start peak. The loader hydrates a Torch object with
`weights_only=False` and the backbone and tokenizer are loaded separately by name.
Verify the parser weight SHA-256
`85a2590374d2d3bd82a04dcfa474869a8ae2ee6a64074e61b41540aed6633f24`
from Hub metadata. Start with the checkpoint's FP32, LoRA, and stride-100 settings.
Use distribution metadata to identify the package. The wheel's internal version string
is stale. [Dipo guide and addendum](../libraries/parsing/dipo.md) ·
[Checkpoint](https://huggingface.co/larc-iu/dmrst-ettin-400m-gum-12.1.0/tree/e33906a27f89b2703df8ab19e471aa82141d62cb) ·
[Backbone](https://huggingface.co/jhu-clsp/ettin-encoder-400m/tree/7662476d60abb071a5bd319c9f3074f3072c062d) ·
[Loading and encoding](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/inference.py#L72-L88)

**Interface-checked, 2026-11-08.** The checkpoint already has BIE/CRF segmentation
and a GUM relation inventory. Start from coherent retained running text with
`predict_from_text(..., break_at_paragraphs=False)` as the learned-boundary arm.
Compare the same text with `break_at_paragraphs=True`, the native default, which unions
heuristic paragraph/heading breaks. Qualify forced breaks only for known layout meanings.
Expose the final post-merge EDU token/character boundaries from the native segmentation seam,
then map them to ordered source pieces. Record learned, forced, coincident and merged
boundary outcomes, plus exact source slices and normalized display text. Returned EDU text
alone cannot recover positions when a line repeats or normalization joins regions.
`predict(RstTree)` and `predict_both()` consume an EDU-reconstructed input.
Use `predict_both()` to share encoding between supplied and predicted boundary arms and
retain both mappings. Treat this as a controlled diagnostic distinct from the raw-text
layout comparison. [Boundary reconstruction](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L66-L144) ·
[Native inference routes](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L682-L818)

The pinned encoder batches all overlapping windows before global EDU/tree decoding.
Start with bounded logical sections and enable whole documents when the encoder-window
and EDU budgets qualify. Verify the effective window boundary, including the observed
8192 tokenizer limit versus 7999 backbone position setting. Measure cold load and active
window memory at the proposed bounds before turning on larger scopes. A section fallback
publishes its exact coverage and leaves cross-section attachments unresolved.
[Window implementation](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/encoding.py#L417-L474)

Retain the original binary structure with ordered child ranges, native relation and
nuclearity and exact EDU coordinates. Use tree range queries to nominate context for a
statement or action. The package is a bounded selection with links to retained EDUs,
including singletons and relevant external context. Keep normalization and unsupported
attachments visible. Native subtree extraction can drop singletons and reconstructed
metadata. Debinarization and RS4 export can omit distinctions or metadata. These are
derived inspection/export routes. An anchored RST condition nominates a qualifier host.
Purpose, means, attribution, evidence, concession, sequence, elaboration and background
can likewise nominate context. The assembly owner interprets each relation within its
scope. Rhetorical support differs from independent verification, and rhetorical sequence
does not entail an operational dependency. [Tree and serialization](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py#L374-L518) ·
[Subtree extraction](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py#L894-L943)

Use d1 to choose among bounded host alternatives while preserving the original tree.
Only recurring independently assessed label errors justify instrumenting the native
joint label/nuclearity readout for a fixed split. Attachment or split repair needs complete
ordered alternatives or controlled redecoding with branch-specific state. The released
greedy decoder gives neither calibrated per-edge confidence nor an n-best tree API.
The Dipo generative grammar and ICL paths have distinct runtime and output contracts from
d1 typed decisions. Keep them for a separate gap-driven investigation.
[DMRST decoder](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py#L638-L679)

<a id="O05"></a>

## O05 · Use d1 for source discovery, interpretation, and targeted completion

**Proposed profile.** Use `LiquidAI/d1-2B` at
`652f920e544ea37f81e4b0ce89b81d4ed0da90b1`, with the exact custom code, tokenizer,
processor, configuration and `calibration.json` from that snapshot. Qualify
`transformers==5.22.1`, `torch==2.15.0`, `torchvision==0.29.2` and
`pillow==13.0.0` as the first lock candidate on CPython 3.14.10, with the workspace
CUDA build as an explicit runtime input. The official minimum is Transformers 5.19.
Use `AutoModel.from_pretrained` with reviewed pinned code, CUDA BF16 eager as the
target and FP32 CPU as a smoke/reference profile. CPU use for a production fallback
requires its own operating evidence. Stage the reviewed files once, require their
expected digests, and load offline for routine execution. Qualify compilation on
actual repeated batch shapes before enabling it. The documented GGUF endpoint
omits typed reads and multilabel answers. Keep ONNX, GGUF and other runtimes as
capability-specific challengers with their own parity and calibration obligations.
[d1 guide and addendum](../libraries/parsing/Liquid_AI_d1-2B.md) ·
[Official runtime and readouts](https://docs.liquid.ai/lfm/models/d1-2b) ·
[Pinned snapshot](https://huggingface.co/LiquidAI/d1-2B/tree/652f920e544ea37f81e4b0ce89b81d4ed0da90b1) ·
[Revision-aware model wrapper](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/modeling_d1.py#L26-L73)

### Task catalog for the first release

**Proposed.** Name and version the question, candidate criteria, rendering, scope,
answer decoding, and acceptance rule under the existing operation/release owner.
These names describe distinct operation questions, with compatible versions eligible to
share a physical request. Candidate choice uses stable identifiers and clear definitions.
Text spans retain their source identity even if two candidates have identical wording.

| Task | Trigger, state and native question | Result and consumer |
| --- | --- | --- |
| `passage_function_v1` | Source-only eligible prose scope, heading and source-owned layout context. Use `choice` with `multiple=True` for independent functions such as requirement, definition, example, exception, explanation and attribution. Run on eligible passages even with no GLiNER or parse result. | Retain per-label probabilities and examined scope. Nominate structure for bounded recovery. An omitted label leaves its source opportunity unestablished. |
| `frame_interpretation_v1` | Located predicate or clause with its source and candidate frame, HanLP arguments and available GLiNER roles. Ask orthogonal Choice or multilabel questions for statement kind, normative force, polarity, epistemic status and explicit domain roles. | A versioned interpretation per dimension. Retain native linguistic roles and abstain on unsupported roles. Compare present GLiNER classification, deterministic cues and d1 on the same source cases. |
| `qualification_scope_v1` | Located condition, exception, temporal restriction, attribution or negation with nearby host IDs and optional Dipo context. Use Choice for exclusive candidates, including a qualified combined-host alternative when the source supports it. Use per-host decisions where several compatible attachments can hold independently. | Proposed host, kind, scope, direction and alternatives. Keep “none of these”, “insufficient source”, and policy abstention distinct. Composition checks compatibility and retains unselected hypotheses. |
| `local_referent_choice_v1` | A structurally important unresolved mention with grounded earlier candidates, scoped discourse context and an explicit no-match option. Ask Choice, followed by a targeted text request if the right candidate appears to be missing. | Candidate member ID or unresolved. Feed a witnessed local resolution candidate to the existing selection owner. Track event and entity references as distinct targets. |
| `relation_interpretation_v1` | Two anchored statements or frames and the possible meanings for one relation family. Use Choice for exclusive alternatives or `noul` for one declared source-reading proposition. Supply affirmative and negative criteria for hard distinctions such as attributed rationale versus asserted cause. | Typed relationship proposal and answer probabilities. Assembly admits only a relation with the declared semantics and witness. Compare explicit source cues with interpretation on implicit and misleading rhetorical cases. |
| `literal_completion_v1` | A missing field nominated by a frame or source discovery. Read a bounded clause with `text`, `number` or `date`, using source-backed unit or locale context where available. Schedule dependent questions in a subsequent call. | Source-grounded phrase, optional normalized value and parse status, or unresolved. Repeated fields use separate declared scopes. Retain comparison operator, relative event, applicable action, time unit and calendar semantics when supported. |
| `contextual_link_assessment_v1` | Existing lexical/embedding retrieval supplies pairs, pinned source contexts and type/scope metadata. Ask a named question about identity, concept equivalence, or another declared relationship family. | Retain retrieval rank and candidate availability separately from semantic choice. Apply existing relation and support eligibility. Include same-name different entity, different document versions and no-compatible-candidate cases. |
| `visual_location_v1` | Conditional. Exact retained image/crop and a named ambiguity for which text or geometry is insufficient. Use Choice or `box`/`boxes` against the qualified single-image route. | Retain native normalized coordinates, presence and localization values separately, the crop-to-source transform, and explicit maximum count where used. A box is a candidate location for the declared inspection. |

### Make the native API observable at the right boundary

**Interface-checked, 2026-11-08.** `system_one` and `system_one_batch` accept independent
questions per state. Use the trained group size of 16, group questions only when they share
the same permitted context, and batch different states by rendered length. The pinned runner
splits larger question sets into groups and repacks them, so a call may involve several
forwards and repeat a state's work. Its 65,536 padded-token budget forms batches. The source
can still emit an oversized single row, and `engine.tokens` describes the largest individual
question rather than the full grouped row. Bound the fully packed state before worker
dispatch, including question suffixes and media. Start qualification at a one-paragraph
source scope or one focal clause plus its named context, with a **provisional** 4,096-token
packed-row limit for text. Compare larger bounds on omissions, semantic yield, cold/warm
memory and latency before changing the profile. An over-limit request splits only at
a justified source boundary or returns explicit unsupported coverage.
[Native batching and limits](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/runner.py#L151-L226) ·
[Padded batches and token estimation](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/runner.py#L305-L369)

For source discovery, pass an immutable source-only state with a reversible map. For a
candidate-centered decision, keep distinct `source` and `candidates` fields. The decoder can
point to any eligible text in the rendered state, including a candidate paraphrase. Prefer a
source-only follow-up when locating literal evidence, especially when a candidate could copy
the evidence. For mixed-state reads, require a half-open span wholly inside one allowlisted
source string with its JSON Pointer, then validate the decoded text against the exact mapped
source slice. Require the analogous exact check on plain text. Reject cross-field spans, a
path or offset mismatch, and ambiguous spans. Record the immutable state or its exact
reconstructible representation, the renderer and state offsets. Use `engine.render(state,
engine.ask(question))` for prompt inspection, and the pinned state text and JSON string
map for offset interpretation. A prompt-rendering escape for structural tokens does not make
untrusted document instructions authoritative.
[State serialization](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/prompt.py#L481-L544) ·
[Pointer readout](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/pointer.py#L14-L98)

Typed reads return at most one contiguous span per question, with native caps of 512 tokens
for text and 32 for numbers or dates. The pinned implementation can suppress the span in
the pointer decoder before answer calibration, and can also hide it in typed postprocessing.
An application threshold can withhold a returned span. It cannot recover endpoints the
native path already discarded. Keep absence of an anchored result, invalid mapping,
normalization failure with valid source text, and a supported judgment that the source
does not state the field as separate outcomes. Numeric and date parsing uses the rendered
context, so source-grounded locale cues, attached units and reference events must be
distinguished from metadata or candidate suggestions. A native parsed date or numeric
unit is a candidate normalization. Keep the exact literal and use existing typed
validation for application semantics. Prefer deterministic arithmetic and counts.
[Typed answer conversion](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/api.py#L84-L140) ·
[Pointer gate](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/pointer.py#L148-L166)

Keep the checkpoint's calibration identity with its native outputs. Closed answers
use checkpoint temperature scaling and typed outputs have separate transformations.
Record a Choice distribution, independent multilabel probabilities, binary probability,
extraction presence and ordinal distribution with their meanings. The optional engine-level
`abstain_below` recognizes specific English unknown descriptions and compares the largest
substantive share after removing the abstention candidate. Use explicit semantic
unknown options and application-owned selective thresholds initially. Compare native
abstention as a targeted diagnostic, preserving the distinction between a class answer
and policy withholding. For any ordinal use, keep the full distribution. The default
level is the median and the native confidence is the mode's mass. Author calibration
and acceptance cases per task and source population. Vendor calibration does not
establish transfer to M2.
[Abstention and score readouts](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/api.py#L35-L81) ·
[Checkpoint calibration](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/calibration.py)

<a id="O06"></a>

## O06 · Deliver qualified statements and useful partial workflow structures

**Proposed.** Extend the existing typed contribution and consolidation route. Shared
preparation supplies HanLP, GLiNER, Maverick, Dipo and the d1 source-only pass independently.
The candidate stage joins by exact occurrence, typed source scope and evidence role.
Run dependent d1 decisions after their candidate inventory is frozen. Select compatible
results under the released domain model and keep independently valid fields visible.
Expose a bounded statement-and-context view as a consumer of the same contribution
and witness records, with references to full context on demand. A successful stage
settles its own output. A failing, unscheduled, or unsupported downstream task cannot
erase the located predicates, arguments, mentions, qualifiers or EDUs already retained.

| Product | Observable behavior |
| --- | --- |
| Entity or concept occurrence | Exact mention, separately attributed lexical, HanLP NER and GLiNER evidence, optional local referent and separately typed corpus candidate links. |
| Predicate or action frame | Located predicate, native argument roles and extents, optional domain-role interpretations, participant alternatives and missing fields. |
| Qualified statement | Explicit local scope for polarity, normative force, condition, exception, attribution and temporal meaning. Each attachment has its own source basis and assessment standing. |
| Partial workflow | Source-supported actor, action, responsibility, prerequisite, ordering or output when found. Unsupported links and branches remain gaps. |
| Statement-and-context package | Focal contribution with bounded related source, rhetorical organization, referents, unresolved attachments, and links to omitted or external context. |

One intended journey starts with the baseline's authored purchase example. For “If a purchase
request exceeds $10,000, its department manager must approve it before Procurement issues the
purchase order,” HanLP nominates approve and issue frames and the initial condition. GLiNER
and terminology nominate the role and artifacts. Maverick may link “it” to the request.
Dipo may nominate the condition's discourse host. d1 interprets the obligation, candidate
host and relative order and can request the source-backed threshold. The application retains
the operator `>` and source literal separately from the normalized amount. “The approver
must record that decision in the request” contributes another action. A useful recording
obligation survives an unresolved event reference to “that decision.” The independent
“unless Compliance records a supplier exception” clause attaches to the hold requirement
only if the source and scope support that host. A Reader or MCP contribution read can show
the exact hold action, its alternatives, what was selected, and why a reference remains
unresolved. Public support appears only after the existing eligibility check.

The [retained p289 qualification and local antecedent examples](../examples/README.md)
supply current consumer controls. Use the existing exact source, contribution and
contextual relationship reads for the M2 journey. Start with contribution inspection and
bounded context references before adding a standalone public workflow query. Add a new
query only when the user needs a typed traversal that those reads cannot supply.
Use context selected by the task: a local clause for modality, adjacent discourse
for a scoped exception, retrieved source for identity. Passing a document to every
decision or eager model cascades would obscure coverage and repeat unrelated work.

**Proposed uncertainty handling.** Keep raw scores, distributions, hard shape checks,
semantic assessment and publication standing separate. Shared HanLP representations,
Maverick channels, d1 reading upstream candidates, and multiple observations of the
same source all introduce dependence. Agreement is a feature, and cannot be multiplied
as independent evidence. Keep ranking scores as ranking scores until a named event
and reference population support fitting. Use the existing finite interpreter only
when the alternatives and joint support have defined meaning. An event sums the
mass of distinct assignments that satisfy it, with displayed-support bounds for a
partial view. pgmpy or Pyro would require a concrete joint or hierarchical inference
question beyond that route. Splink remains a challenger for declared identity linkage.
[D5 consolidation](../design/D5-consolidation-identity-confidence.md) ·
[DMA displayed-support consistency](../plans/domain-model-alignment/semantic-admission.md#DMA-04)

<a id="O07"></a>

## O07 · Diagnose which operation improved the result

**Proposed.** Use the existing operation reference, assessment and paired diff routes
to trace source opportunity → native observation → candidate → selection → consumer
result. Freeze source opportunities and assessed exposures before comparing arms.
Keep unsupported and failed cases visible, with the reason and attempted scope.
An empty success stays separate from an unavailable prediction. Use independent
reviewed source expectations for the comparison. Keep fitting and acceptance
separate when claiming transfer beyond the development population.
[D7 granular assessment](../design/D7-evaluation-goldens-outer-loop.md#granular-assessment-and-operation-fitting)

| Comparison | Required separation and representative cases |
| --- | --- |
| Source and execution | Preserve exact formula, caption, native-piece and source-order controls, including p416 and p151 where relevant. Exercise repeated text, Unicode, JSON escaping, protected atoms, synthetic separators, scope limits, cancellation and single-provider failure. Verify no fabricated anchor or false negative coverage and verify a surviving contribution through Reader and fresh MCP. |
| Existing syntax versus HanLP | Pair the current spaCy/GLiNER route, HanLP core heads, and one added head or transformation at a time. Score predicate discovery, native argument boundaries/roles, domain-role projection and qualifier host separately. Include implicit or missing arguments, passive agency, coordinated negation, nested if/unless, and a qualifier crossing an atom. Compare ModernBERT Base and Large on the same source opportunities. |
| Maverick predicted versus reviewed mentions | Pair mention boundaries and clustering on the identical document population. Distinguish false merges, split chains, ambiguous/null antecedents, and useful downstream participant changes. Reuse low-level MUC, B³, CEAF or LEA only under explicit singleton conventions and independent asymmetric precision/recall cases. The bundled recall accessor and Lightning evaluator argument order are unsuitable as an unchecked oracle. Category-level strata and exact-span antecedent controls can reveal whether a repair helps a recurrent construction. |
| Dipo raw and controlled segmentation | Pair learned versus layout-forced raw input, then use supplied and predicted EDUs within `predict_both()`. Score boundary errors, parent yield, exact child split, nuclearity and relation separately. Adapt the cascade idea to DMRST with child-availability strata. The tagged script does not directly run this path. Reuse the paired metric primitive only over a prespecified population with explicit failures and document-level grouping. The stock comparison intersects available outputs. |
| d1 source discovery versus candidate interpretation | Pair source-only discovery, current upstream candidates, and supplied reviewed candidates. Distinguish candidate availability, selection, abstention, source location, and normalized value. Include repeated candidate text, plausible but unsupported options, order/wording perturbations, misleading attribution, modal negation, ambiguous relative dates, and all-upstream omission. d1 may prioritize review cases. Independent references establish its accuracy. |
| Composition and corpus linking | Compare incremental correct and distinct qualified parts, unsupported merges, and full-record correctness. Check whether a Reader can recover the useful part when one attachment fails. Measure retrieval availability separately from d1 or policy selection. Pair the same documents and versions and record the scope of any semantic or calibration claim. |

Use the 518-page Grinstead–Snell frame for current-method development and regression,
with the retained WCE results at their original smaller scope. Toy ownership and controlled
policy, procedure and message examples can exercise transfer contracts immediately.
Independent in-domain references from available policies, engineering documents, incident
reports, tickets and genuine attributed messages are required for claims about those genres.
Freeze the available populations when planning. An unavailable genre blocks only its claim
and any release route that requires it. Public dataset examples or authored cases do
not establish performance on the operator's production population. Compare failures
and source opportunities before summarizing any aggregate quality. [Current benchmark decision](../adr/0070-full-book-method-development.md) ·
[Maverick metrics](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/common/metrics.py#L38-L68) ·
[Maverick evaluation source](https://github.com/SapienzaNLP/maverick-coref/blob/5c1fa627021b190101b4893751fa9836e85474b1/maverick/models/pl_modules.py#L38-L99) ·
[Dipo paired metric](https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/metrics.py#L181-L241) ·
[Dipo comparison selection](https://github.com/larc-iu/dipo/blob/v0.2.1/scripts/compare_runs.py#L86-L127)

<a id="O08"></a>

## O08 · Keep the four profiles operable on the shared host

**Proposed.** Reuse the existing task attempt, provider boundary and artifact
custody. Start with separately locked worker environments where needed for compatibility
and cancellation. Prefer a local worker lifecycle over a new network service. A startup
capability report should identify the actual artifact and library versions, supported heads
and modes, input conventions, decoding settings and qualified operating bounds. Derive
it from the effective profile and runtime. Retain it with the existing profile/invocation
custody rather than introducing another authority for accepted capabilities.

Qualify a one-resident-GPU-profile scheduling policy as the starting operating envelope.
Group reusable work by loaded profile and bounded length. Share device admission with
existing recognition work, release residency at the existing lifecycle boundary, and
keep database transactions outside inference. Start with eager reference runtimes.
Compare warm and cold use for the same scope and use native diagnostics to choose
HanLP sentence/subword budgets, Maverick subtoken and mention budgets, Dipo window/EDU
budgets, and d1 packed tokens and question grouping. Check actual input and physical work
separately. An oversized single input cannot be remedied by reducing batch count alone.
Keep separate flags for execution-relevant optimizations and for eligibility to publish
a resulting semantic product. [D6 workers, reuse, and GPU sharing](../design/D6-orchestration-metrics-policies.md)

An operator can retry only a failed eligible scope after recovering an asset, timeout or
device failure. A bounded retry may reduce the physical batch or use a separately qualified
fallback. When it changes context, device, runtime or effective settings, retain the new
request identity and prior outcome. Partial work remains reusable where its original
premises hold. An unsupported semantic scope remains a distinct gap. Quantization,
compilation and additional concurrent residents are candidates when actual operating
results justify the change. Check native output parity or relearn the applicable thresholds
where score/decision semantics change. The check depends on the proposed capability.

<a id="O09"></a>

## O09 · Inspect visual evidence only for a named ambiguity

**Proposed, conditional.** Use d1 with a retained page crop when a statement depends
on a specific location or visual distinction. Start with one named question over one
exact crop and compare the existing Reader/geometry and Chandra candidate routes.
For example, a disputed legend marker may need a located visual candidate before a
statement can cite the right series. Keep the render identity, region and inverse
transform, native image-relative box and distinct confidence quantities. Check clipped
coordinates and wrong-crop refusal. Maintain attributable proposals when visual
recognition and source projection disagree. The existing visual owner retains source
selection and publication authority. Require a reviewed case where this yields correct
distinct evidence before enabling a new production route. Video, general visual parsing,
and whole-page replacement have distinct source and assessment obligations.
[Existing visual owner](../plans/domain-model-alignment/visual-evidence.md) ·
[Chandra opportunity review](chandra-2-post-nemotron_2026-11-08.md) ·
[d1 box implementation](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/box.py)

## Baseline disposition

**Proposed.** This crosswalk carries the supplied design into the target and the planning
handoff. Conditional recommendations retain a route to qualification.

| Baseline | Review disposition |
| --- | --- |
| Part I §§1–2 and §7 model set, canonical HanLP inputs, common annotations, spaCy migration and deployment | Retain the common linguistic profile and Large/Base comparison. Correct native task names, POS semantics and batch controls. Reuse atom-preserving preparation and qualify each migrated rule. [O01](#O01) · [O02](#O02) · [O08](#O08) |
| Part I §§3–4 coherent coreference scopes, overlapping windows, source-aligned DMRST and conditionality | Retain section coverage and local referents. Supersede independent chunk reconciliation as the long-document target with qualified joint MES, preserving a section fallback. Preserve Dipo source-mapped binary structure and explicit raw/forced profiles. [O03](#O03) · [O04](#O04) |
| Part I §5 GLiNER classification and optional Decide | Retain deployed GLiNER extraction and applicable classification. The revised scope makes d1 the primary new semantic decision profile. Compare a separate Decide deployment only on a named operation with a measured gap. [O05](#O05) |
| Part I §6 worker contract, partial results, confidence and assembly example | Retain immutable source and runtime binding, native labels and honest coverage. Extend with typed coordinates, explicit candidate-relative outcomes and separate admission. [O01](#O01) · [O06](#O06) |
| Part II §1 four-model architecture, retained streams, candidate assembly and direct d1 source path | Retain all four additions and the independent source route. Keep failures scoped and preserve upstream contributions. Treat broad whole-document modes as qualification-dependent. [O01](#O01) · [O06](#O06) |
| Part II §2 task families, independent discovery, exact extraction, values and batching | Retain and specify the task catalog. Correct rendered-state offsets, native pointer withholding, question grouping and token budget semantics. Add source-only follow-up reads, explicit abstention and task-event calibration. [O05](#O05) |
| Part II §3 constituency, role projection, SDP, terminology and actual checkpoint tasks | Retain constituency, SRL and UD as ordinary evidence. Preserve POS schemes and native role labels. Compare SDP formalisms per operation. Use existing overlapping terminology first and keep dictionary overrides conditional. [O02](#O02) |
| Part II §4 mention inventory, joint clustering, supplied mentions, speakers, seeds and scores | Retain all inquiries. Qualify ordinary mention inventory separately from public clusters, joint mode behind parity and resource checks, reviewed supplied mentions for diagnostics, and seeds or score visibility behind scoped qualification. [O03](#O03) |
| Part II §5 anchored discourse, RST mappings, context, interpretation and redecoding | Retain all four. Separate layout and supplied-EDU experiments. Keep original topology, compose context by references, and defer edits until a demonstrated attachment or label gap. [O04](#O04) |
| Part II §§6–7 product families, source admission, dependence and finite inference | Retain partial qualified structures and use current admission. Keep event definitions and corroboration scope explicit. Use current finite support where appropriate. Revisit specialized numerical libraries for specific unresolved inference or linkage requirements. [O06](#O06) |
| Part II §8 granular operations, controlled inputs, paired comparisons and d1 independence | Retain and extend with anchored denominator accounting, native metric corrections, separate source-only recovery cases, and release evidence by genre. [O07](#O07) |
| Part II §9 full d1 runtime, adapter work, isolated environments, manifests and reusable inference | Retain native reference runtimes and source-aligned adapters. Pin downstream backbone/tokenizer assets as well as top-level checkpoints. Qualify environment and device bounds. Reuse current custody, selection and invalidation rules. [O01](#O01) · [O08](#O08) |
| Part II §10 milestone and advanced-capability dispositions | Include normal constituency and task selection, exact source alignment, coreference and discourse diagnostics, and the d1 text task catalog. Qualify SDP, constraints, joint MES, scores, speaker mode and visual grounding by use. Keep seeds, tree revision, ordinal scoring and estimation narrowly conditional. Revisit custom heads, nested training, distillation, alternative coreference or discourse checkpoints and Dipo LoRA/DoRA only after the responsible operation is understood. Keep d1 typed fine-tuning, generative RST and video as separate research. [O02](#O02) · [O03](#O03) · [O04](#O04) · [O05](#O05) · [O09](#O09) |
| Part I introductory UltraBERT and KNIV candidates | Preserve as adaptation leads. Compare learned transformations or extra heads only for a measured gap that survives alignment, deterministic transformation, context and task definition fixes. Keep their runtime and training outside the initial four-provider profile. |

## Handoff to detailed planning

1. **Source and runtime first.** Specify the small shared coordinate and retention contracts
   from O01, with exact scoped worker pins from O02–O05 and lifecycle from O08. A native
   load and shortest successful grounded output establish the reference environment for each
   family. Before promotion choose exact locks and budgets through the boundary, dense-input
   and cold/warm cases in the profiles. Preserve named existing source, observation and
   Reader behavior through a limited comparison.
2. **Build one usable composition before broad routing.** Select a condition or exception
   attached to a real frame, a useful local referent and bounded discourse context, and a
   d1 source-first recovery case. Carry exact source and occurrence identities from provider
   through private Reader/MCP. Exercise the route with one missing provider result.
   Expand to the remaining d1 tasks and product families under the same contracts.
3. **Assess increments before admission.** Use the existing operation assessment owner and
   independently reviewed paired cases from O07. Compare against current scoped behavior.
   A correct added part must remain independently inspectable even when a complete record
   fails. Resolve the adopted semantic release and any genuine owner or rule changes through
   existing decision routes. The current DMA cutover retains its own acceptance.
4. **Gate heavier and conditional modes by their consumer evidence.** Joint MES qualifies
   only after parity and cross-boundary cases. Whole-scope Dipo qualifies within demonstrated
   bounds. Require incremental value for extra heads, score instrumentation, typed visual
   read, runtime exports and any specialist challenger. Keep supported section and eager
   profiles available as independently named routes.

Detailed planning should carry forward the proposed configuration and concrete source
links with each selected opportunity. Required locks, operating bounds, per-operation
eligibility thresholds, and business genre claims retain the prerequisites above.
