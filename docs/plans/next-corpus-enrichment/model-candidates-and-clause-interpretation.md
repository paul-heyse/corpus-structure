# Model candidates and clause interpretation

**Proposed · 2026-11-07.** Companion to the [next corpus enrichment coordinator](../next-corpus-enrichment_2026-11-07.md). Develops [O09](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O09) and the model-side recovery and
diagnostics in [O10](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O10). Preserve the distinction between a located candidate, a scored model
observation, and an admitted interpretation. The existing GLiNER worker owns bounded inference. The
source and linguistic companion owns exact source mapping and neutral frame identities, and
qualification remains with the admitted interpretation operation.

<a id="NCE-04"></a>
## NCE-04 · Improve definition declarations and add focused clause observations

**Outcome and dependencies.** Start the definition-description comparison on the existing located
definition windows. The clause-classification slice consumes the exact clause-focus and frame
reference delivered by [NCE-02](source-and-linguistic-composition.md#NCE-02). Run it as a separate operation with its own version and assessment so a
description change can be judged independently. Its output may be used by a later NCE-02
interpretation execution with the same authenticated focus. Deterministic framing, qualification and
[NCE-03](source-and-linguistic-composition.md#NCE-03) comparison can run without it. A first run of a neutral frame never depends on a classification
of that frame.

**Definition description arm.** Reuse `definition_pack` and the existing `Schema.from_dict` and canonical round-trip checks. The
current local pack passes bare term, content and relation labels and a term-scoped interpretation
attribute. Add versioned descriptions that distinguish the expression whose meaning is stated from
nearby examples or historical subjects, the exact text or formula conveying the meaning including
meaningful complements, and a directed attachment from the term occurrence to the content. Keep
label names, pack family, profile, checkpoint, selected windows, thresholds and overlap policy fixed
for the first comparison. The native 2.1.0 preprocessor conditions entity labels on descriptions and
uses relation descriptions as the relation prompt. Changes in the schema can affect encoded subword
count, so preserve every admitted/refused window identity and separate an unequal admitted
population from interpretation changes. Preserve the term attribute as a model observation. [Definition pack](../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py) ·
[Pinned schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py) · [Pinned preprocessor](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processor.py)

**Focused clause arm.** Reuse the resident worker and a versioned classification-only `native-combined-v2` pack. The
neutral frame supplies one exact focus, original passage/extent, and source context reference. Feed
the exact focus text for the first arm. A candidate context arm uses bounded, source-addressed
neighboring text and an explicit focus cue with a versioned mapping. Treat any generated delimiters
as synthetic model context. A native combined classifier classifies the whole input, so a clause
identity and focus-bearing input are required before its scores can be composed. Keep two axes.

- Clause function covers definition, explanation, assumption or restriction, prescribed action,
  described process, and unresolved. Permit reference where the admitted vocabulary and judgments
  distinguish it from explanation.
- Presentation context covers example, attribution/reporting, historical discussion and unresolved.
  Use the multi-label route for co-occurrence and preserve which labels were returned or withheld.

Start with label descriptions and a frozen context policy. Compare prompts, examples and decoding
changes one at a time after the baseline. Keep example cases separate from protected judgment cases.
The pinned combined path chooses argmax for single-label output and falls back to argmax if all
multi-label scores fail `cls_threshold`. Therefore keep a versioned application disposition for withheld,
conflicting or insufficient evidence, separate from the provider's semantic `unresolved` label and its raw
selected scores. Retain whatever scores the provider actually returns. Treat scores as model
observations and leave missing scores unavailable. No classification result supplies an exact source
extent or an independent witness. [Worker](../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py) · [Pinned native decoding](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/runtime.py)

**Custody and migration.** Retain frame, source and passage references, focus/context identity and
mapping, profile, checkpoint, worker operation, canonical pack and inference input digests,
threshold/overlap and context policy, output and outcome. Bind any decoded observations to their
exact retained envelope and selected source. Use the released observation/product contract and
native admission for any new observation role. Reuse the managed private inference, selective result
read and replay boundary. Interpretation consumers cite the particular authorized model observation
and remain usable on missing or failed model inference. Preserve existing selected observations and
earlier cuts. Regenerate the changed pack's output and dependent interpretations under the consuming
release. Keep provider work outside publication transactions. Match the existing request limits,
cancellation and refusal behavior.

**Acceptance.** On the same windows, compare term boundary and role, content completeness, directed
attachment, classification on each axis, and withholding. Include performed and reported
definitions, attributed historical examples, a mathematical “must,” a real instruction inside an
example, an embedded negative in a positive definition and discordant rule/model evidence. Compare
exact-focus and bounded-context results separately. Exercise class fallback with all multi-label
scores below the configured threshold, context refusal, missing/failed provider output, native
envelope binding, deterministic no-model output and replay. Use `test_definition_applicability.py`, `test_gliner.py`, existing worker controls
and applicable native/portable product checks via `uv run ci test -- PATH`. Assess live model outcomes under the actual
pinned profile on the declared selection. A local stub establishes contract handling only. [Prior JointIE findings](../../design_review/evidence/2026-11-06_wce-gs120/joint-ie-investigation001/README.md)

<a id="NCE-05"></a>
## NCE-05 · Diagnose candidate losses and recover independently valid roles

**Outcome.** Trace a source-authored opportunity through exact extent availability, token alignment,
nomination, scoring/overlap, record grouping and attachment. Recover a useful exact term or content
when grouping or attachment fails. Begin diagnostics and recovery with existing retained envelopes
and selected passages. NCE-04 provides matched new pack outputs for later comparison, while the
initial recovery does not require a changed checkpoint or a successful classification experiment.

**Realization.** Reuse the source mapping and current role/attachment decoder. The definition
component decoder currently requires matching roles and a directed attachment to form a complete
component, leaving unattached entities in the raw envelope. Expose independently valid, exactly
located role contributions using the current witnessed role path and verify each candidate against
source slices and envelope channel/index. A complete definition component still requires both roles
and an admitted attachment. Keep explicit refusal, unsupported semantics and unresolved grouping
with references to the source-bearing contributions. Inspect the retained record only when an
identified field could yield a useful exact component. Preserve `optional_one` and `zero_or_more` semantics and authentic
multiple occurrences. Identical strings at different source offsets remain distinct. Keep
grouping/version identity and original provider output available for replay. [Definition decoder](../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py) · [Record packs](../../../python/corpus-structure/src/corpus_structure/methods/record_packs.py) · [Record assembly](../../../python/corpus-structure/src/corpus_structure/methods/record_assembly.py)

Compare a matched bounded overlap challenger on independently located nested roles. The repository
worker admits only `flat`. Native GLiNER supports `nested` and `allow`. Introduce a versioned evaluation
operation/profile for the candidate policies and keep ordinary activated policy separate until the
assessment supports a change. Observe coverage and false additions, including nested roles and
crossing spans. No count-guided or threshold change enters this arm. Existing `GlinerReport` marks proposal
pool, suppression, count, abstention and feasibility unavailable because the high-level call does
not expose them. Report known checkpoints and the earliest evidenced failing layer. Keep unobserved
layers unavailable, including whether an absent span was ever nominated. An observed change between
matched overlap arms can narrow the explanation without claiming access to unreturned logits. [Report contract and preparation](../../../python/corpus-structure/src/corpus_structure/methods/gliner.py) ·
[Pinned overlap implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/overlap.py)

Use `SchemaTransformer.transform_record` as the pre-inference inspection route already used by `prepare_input`. Check codepoint word and subword
alignment, source indices, schema-conditioned input length and permitted synthetic punctuation. When
a concrete long-input miss warrants it, inspect tokenizer overflow/offset metadata with exact source
mapping. Use layout and clause selections first. Keep provider chunk/window metadata and adjudicate
overlaps by occurrence, preserving raw window outputs. A relation with endpoints never co-present
requires the ordinary witnessed linking path. Exact source-level anchors remain accessible where
model token alignment fails. [GLiNER guide](../../libraries/parsing/gliner2.md) · [Tokenizer Encoding](https://huggingface.co/docs/tokenizers/api/encoding)

**Acceptance and delivery.** Use a supported nested role, repeated identical surface text, an
independently useful unattached role, an ambiguous host, an unsupported relation target and a
malformed span. Exercise codepoint offsets around formula punctuation and combining marks and refuse
a synthetic suffix as a source location. Compare common candidates for decoding and report newly
reachable source opportunities separately. Verify that unresolved grouping does not erase a valid
role, a recovered role cannot imply an edge, and a failed native provider does not appear as an
empty result. Preserve out-of-scope windows and previously retained outputs. Expose affected
products through the authorized structural reads and replay, and pass the exact role/attachment
references to link and assessment consumers. Run focused GLiNER, record, source-mapping, native
product and replay controls. Upgrade ordinary selection only through the declared policy and
combined acceptance.

## Owned conditional investigations

| ID | Trigger and bounded investigation |
| --- | --- |
| <a id="NCE-M01"></a>NCE-M01 · Focused class challengers | After the first clause baseline, compare prompts and examples, context encoding, and class activation or selective thresholds on fixed cases. Consider dedicated `Classifier` only for a demonstrable valid label constraint, retaining feasible/violations/exactness, with explicit infeasible handling. If meaningful residual classification failures persist, compare pinned Decide variants with the current checkpoint on the same cases and qualify a separate worker/profile where architecture differs. [Classifier](https://github.com/fastino-ai/GLiNER2/tree/v2.1.0/gliner2/classification) · [Decide 1B](https://huggingface.co/fastino/GLiNER2.5-Decide-1B) |
| <a id="NCE-M02"></a>NCE-M02 · Structured instance assignment | Repeated source-backed records show a concrete anchor or assignment failure. Compare natural anchored and latent grouping in the released V2 contract, preserving partial records and shared qualifiers. Test exclusivity only for a genuinely single-instance field. Anchorless formation needs model support, qualified instance behavior and a separate contract expansion. Training occurrence policy does not replace runtime exact occurrence custody. [GLiNER guide](../../libraries/parsing/gliner2.md) |
| <a id="NCE-M03"></a>NCE-M03 · Boundary and scoring challengers | Loss diagnosis identifies an aligned span missing from native nomination or inappropriate ranking. Compare `score_explicit_spans` on authenticated spaCy/Lark proposals, per-role thresholds and budgets, and count/abstention behavior only in separate versioned arms. Verify input schema and token alignment, retain raw candidates before filtering, and report added spurious proposals as well as recovery. Count guidance cannot supply a missing boundary. `RegexValidator` is suitable for a released identifier shape when raw prefilter evidence remains available. [Boundary implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py) |
| <a id="NCE-M04"></a>NCE-M04 · JointIE | Improved candidate role/attachment coverage and the same frozen cases support an independent-versus-joint comparison. Use GLiNER2 2.1.0 `JointIEEngine.score` to inspect the scored lattice where available and `JointIEEngine.extract` for the bounded joint result. Retain typed endpoints and direction, thresholds, search bounds, and infeasible or incomplete outcomes. Require judged relationship benefit and preserve valid partial components in both arms. [JointIE source](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/joint_ie/engine.py) |
| <a id="NCE-M05"></a>NCE-M05 · Context and runtime variants | A measured context omission or physical execution limit makes a challenger useful. Compare layout-aware windows first, then native `batch_extract_long` on exact remapped overlaps, with window identities and cross-window custody. Compare warmed shared-schema batching before precision, compilation or accelerator variants. Hidden-state reuse needs the same complete effective encoded schema and inputs. Alternate runtime or deployment interfaces need separate parity and authority checks. [GLiNER guide](../../libraries/parsing/gliner2.md) |
| <a id="NCE-M06"></a>NCE-M06 · Trained or domain-specific alternatives | Persistent residual errors and sufficient protected exact labels justify comparing `SpanFinder`/`SpanCategorizer` or GLiNER fine-tuning and LoRA/DoRA. Use independent located labels, declared exposure and injection-free proposal recall. Use source isolation for a separate transfer claim. Preserve nested and repeated exact supervision and keep missing labels distinct from negatives. Isolate adapter state by execution. Multilingual, PII, safety or domain checkpoints need a matching workflow. Generic wrapper deployment and broad model training have no selected delivery role. [spaCy guide](../../libraries/parsing/spacy.md) · [GLiNER 2.1.0 release](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0) |
