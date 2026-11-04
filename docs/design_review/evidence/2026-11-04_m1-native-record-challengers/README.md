# M1 native record challengers

**Tested (bounded metadata only), 2026-11-04.** Native GLiNER2 2.1.0 can express the actual frozen C definition fragments as distinct list values, and can retain complete coincident-predicate record targets in `latent` or `anchorless` mode. These are feasible native representation candidates, not production replacements or learning/inference results.

The assignment owns this new evidence folder only. Production runtime remains frozen at native128/129; no runtime, tests, plans, configuration, dependencies, database, PDF, heldout inputs, model construction, model forward, training, head resize, or commits were performed. Only the local tokenizer, native schema/processor, native target builder, and pure formatter helpers execute. The Transformers configuration warning is retained in both logs; it arose while loading the local tokenizer, with no extraction model instantiated.

## Baseline and documentation

The sole semantic input is `../2026-11-04_m1-contextual-targets/attempt-002/feature-fit-protected.json`, original C passes23/24, `feature_fit` only. Source text/intervals, full released packs, routing diagnostics and prior annotation-scope judgments come from that same frozen attempt. All five selected contexts have `scope_errors=[]` in that attempt's request or routing audits. This probe enumerates every same-family C record whose natural literal anchor overlaps the selected context, maps every declared field or refuses the entire sample, and never emits a target set after a mapping failure. It does not requalify source preparation, choose new runtime routes, or solve other families' blockers in those contexts.

`context7-receipts.json` preserves resolve plus two focused queries against `/fastino-ai/gliner2`: list/span fields and native record formation. Context7 references upstream main, so consequential conclusions use the installed 2.1.0 implementation, not an assumed tag equivalence. `source-receipts-002.json` binds installed source files, checkpoint config and frozen inputs by SHA256. The checkpoint remains `fastino/gliner2.5-base-v1@54785d51df8d86a0d8f2eb212fec15871aad2c4d`, with `record_instance_queries=32`, `max_gold_per_query=64`, candidate budget192 and records enabled. No weight files are loaded.

Primary topic sources:

- [Schema API](https://github.com/fastino-ai/gliner2/blob/main/gliner2/inference/schema.py): `Schema.from_dict`, `structure(mode=..., anchor=...)`, field `dtype`, `cardinality`, `exclusive`.
- [Record target builder](https://github.com/fastino-ai/gliner2/blob/main/gliner2/processing/boundary_preprocessing.py): installed `_build_record_field_target` lines196–218 makes scalar spans alternatives for one value, while list spans become separate values. `build_boundary_batch_metadata` and packed record masks retain each complete record.
- [Record head and decoding](https://github.com/fastino-ai/gliner2/blob/main/gliner2/models/boundary/records.py): installed lines604–641 and727–750 distinguish natural, latent and anchorless formation; lines968–978 deduplicate latent/anchorless complete records by all field spans.
- [Native formatter](https://github.com/fastino-ai/gliner2/blob/main/gliner2/models/boundary/engine.py): installed `_decode_records` lines1221 onward maps selected spans to source offsets, strips span surfaces, finalizes spans and formats lists. `_format_structure_field` lines919–950 preserves separate span dictionaries when `include_spans=True`.
- [Overlap policy](https://github.com/fastino-ai/gliner2/blob/main/gliner2/inference/overlap.py): installed `resolve_overlaps` lines56–83 explicitly ranks by descending score then ascending start/end; list order is not source order.

## Controls and receipts

`uv run python docs/design_review/evidence/2026-11-04_m1-native-record-challengers/probe.py` — **passed**, 2026-11-04; raw output `probe-002.log`, full native specs, targets, masks, source mappings and exact boundaries in `controls-002.json`. The two expected scalar controls are **blocked**, because their bounding spans include intervening genuine source pieces; no incomplete sample is built. They are negative representation controls, not failed program execution.

| Frozen context ID | Challenger | Complete native records | Source codepoints / schema-conditioned subwords |
|---|---|---:|---:|
| `3d3ba1ccebede0b5e0f547bcbcc5837c707e832427b272065513de1de0979de9` | definition natural, defining_text list | 2 | 603 / 1215 |
| `d65748886a0bee8303bead0a154c6f77a887646aeb6d122d84950a38aafcd759` | definition natural, defining_text list | 3 | 2174 / 2788 |
| `9340ff327cf641ee71ca40d8943a857ba409d5fd575ba4781c1f0dba69977429` | assertion natural / latent / anchorless | 2 each | 398 / 1615 |
| `ea98f1e3e9f499a3e9608ad78c9d3503e61150c191246bcee9412f8f090f3061` | assertion natural / latent / anchorless | 2 each | 459 / 1676 |
| `ca2eaf6bd0ff20822690ea17e9da75593f7a31c3ca5e13a744ea56730332be62` | assertion natural / latent / anchorless | 15 each | 2669 / 3888 |

Both source words and subwords remain <=4096, with no truncation. Strict capacity64 and `on_capacity_exceeded='raise'`, `ignore_missing_entities=False`, `error_policy='raise'` are retained. Containment deduplication is explicitly disabled in the direct builder so no exact fragment target is silently removed. Every native field value and record mask is compared to the independently constructed expected spans, including every state choice, classified value, cue and ABSENT field. No models or scores select the examples.

The first definition challenger preserves the five original `defining_text` pieces of `record:20b0e176a9e38ea308f4e7196c22ccc0ddb9a3392322024f585a940a4ee076b4`; the second preserves the thirteen original pieces of `record:60962e5dafa8b2daefd03ca8c4cc9530e392a68b42afed50119c0794b5d57d49`. Neighbor definitions are included, not omitted as false negatives. Each fragment retains its full original anchor, exact model character span, native word span and source reread. Original piece order is checked before building, and every source→word→source equality is asserted. The only schema change is `defining_text.dtype='list'`, `cardinality='zero_or_more'`; field order, other cardinalities, choices, states and cues remain unchanged.

The smaller assertion contexts preserve `record:0a93507930c4ceb58bd83687222ffc7aa1b8e468a5893c4d935a5a1eccacbafd` and `record:4083ce776ff1afb19ccce5afa50751d58f1154aaa900056d8a409b3675205217`, sharing precisely the same predicate span. The wider context includes both originally unresolved assertion readings `record:1b5902fedde17689021ece9b4523f6c011c54ccfc72790281a13da2bd80b90b3` and `record:3a24889c27d1b434036cf96791170a3b33c42284bcf11e8264ba5ffc63686d87` among all15 complete overlapping C records. Here `record:1b590…` shares predicate with `record:c34005…`; all15 remain supervised together. Mode controls change only mode and remove the declared fixed anchor for latent/anchorless. No field, cardinality, state, cue or choice is removed to evade a collision.

**Target admission is weaker than realizable natural grouping.** The builder also accepts the two/fifteen records in natural mode. Installed natural decoding seeds one instance per detected predicate anchor; duplicate anchor gold acceptance cannot establish simultaneous natural output. Latent instead chooses seeds from all field candidates; distinct subjects/objects can supply additional candidates. Anchorless uses learned queries. Candidate survival, correct grouping, matching and successful learning remain untested.

## Literal fragments and the formatter bridge

`formatter-control-002.json` — **passed**, pure native helper control with deliberately unequal synthetic confidences: source-first span0–5 at0.6 is returned after span10–16 at0.9. This demonstrates confidence ordering, without predicting any model outcome.

`actual-fragment-formatter-002.json` — **passed**, repeats the pure helper control for every actual definition target's pieces, retaining exact text and offsets, with explicitly synthetic increasing scores. Sorting the returned span dictionaries by verified source-context offsets restores exactly the original ordered fragments for these source-monotone cases. This is a proposed bridge demonstration, not native ordered-sequence output or runtime integration. It performs no string joining or normalization.

The native list denotes multiple values of one field; the domain `TextSequence` denotes one logical field value made from ordered source pieces. Native list supervision does not itself teach an arbitrary order or one logical sequence boundary. Native formatting can reorder by confidence, collapse duplicate exact boundaries, or suppress overlaps under the checkpoint's flat policy; its surface `.strip()` also requires exact text/offset verification before source authority accepts it. The tested fragments are distinct, nonoverlapping, source-monotone and have token-exact boundaries. Arbitrary reordered/repeated/overlapping logical sequences are not covered.

Current runtime consumers are not a drop-in bridge: `methods/gliner.py:173` explicitly permits natural packs only, and `methods/record_assembly.py:578` and645 require literal decoder values to be single coordinate dictionaries. Its existing `literal_anchors` helper at408 can already consume multiple `LiteralSpan`s and validates source ordering, but the public field branches must deliberately accept a list, validate each span, derive the one logical `TextSequence` with its original ordered pieces, and preserve state/cue/proposal distinctions. Native classification prefix outputs in non-natural mode may carry offsets0,0 because there is no fixed anchor; those are label tokens, not source cues. Retain the separately extracted cue field as the located evidence.

## Integration recommendation

**Proposed, 2026-11-04:** carry a bounded native-list challenger for `definition.defining_text`, plus a narrow explicit literal-fragment bridge. Keep `zero_or_more` so absent values remain representable and independent state claims continue to govern absence; validate nonempty exact fragments when present. Do not flatten the list into a scalar or describe it as native `TextSequence` support. For these actual contexts the missing machinery is confined to field-value adaptation and source attribution, rather than bespoke model heads or fabricated concatenated source spans (FP-01/FP-02, H1/H4).

**Proposed, 2026-11-04:** compare latent and unchanged-capacity anchorless challengers for assertion grouping at a separately authorized model/training boundary. Prefer latent as the first native candidate when real distinguishing source candidates exist; it preserves the full schema without choosing a surrogate semantic anchor. Retain anchorless as a distinct alternative when grouping cannot rely on a unique source seed. **The32 learned instance queries belong to anchorless, not latent.** Fifteen complete targets fit within32, but that config fact is only structural capacity; metadata preparation does not exercise the head or prove trained capacity. Do not resize heads, silently repurpose subjects as predicates, remove records, or assert that latent training succeeds.

Before any adoption, the coordinator must decide explicit pack/profile support, preserve frozen source/conditioning and required full-target coverage, wire formatter/assembly shape and exact ordering, then separately assess candidate/matching feasibility and functional behavior. No numerical quality, loss, efficacy, speed, operational acceptance, or full M1 qualification claim follows here.

## Files and retained attempts

Files written only here: `README.md`, `context7-receipts.json`, `probe.py`, `probe-001-executed.py.txt`, `probe-001.log`, `controls.json`, `formatter-control.json`, `source-receipts.json`, `probe-002.log`, `controls-002.json`, `formatter-control-002.json`, `actual-fragment-formatter-002.json`, `source-receipts-002.json`. Attempt001 is retained unchanged and covers the two definition contexts and two small assertion contexts; attempt002 adds the wider15-record context and actual-fragment formatter control. The final source is `probe.py`, bound by `source-receipts-002.json`. Broad tests, provider inference, training, qualification and root maintenance are **not_run** within this assignment.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Native fragment-list and coincident-anchor record metadata controls](records/m1.native-record-challengers.json) | M1-07 | passed | M1-INT-F23 | 2026-11-04 |
<!-- evidence-index:end -->
