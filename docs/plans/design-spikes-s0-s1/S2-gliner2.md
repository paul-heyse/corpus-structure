# S2 · GLiNER2: plan

**Status: Proposed (2026-10-28).** Part of the [spike plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions (§3.5), the execution queue (row 30) and spike-execution findings. The
question is the [S2 brief](../../design_review/evidence/2026-10-28_design-spikes/S2-gliner-on-statistics-text.md)'s;
this document says how each brief step now runs against the v1 reference and gliner2 2.1.0, which
variants could change the phase 1 encoder configuration, and which phase 1 method, OPEN item or
package each result feeds.

## 1. What S2 must establish now

Phase 0 has no encoder tier; M05–M07 enter in phase 1 with schemas compiled from the pack (D2 §7.2).
The roadmap's phase 1 entry waits on S2 for four answers: whether GLiNER2 carries `has_distribution`
at useful recall on math-dense text; raw, masked or Unicode math (OPEN-D2-2); the mention-overlap
rule near math (OPEN-D5-4); and whether the spaCy → GLiNER2 candidate-scoring method enters the
catalogue (D4 §3, the candidate paragraph). Two of the brief's premises are corrected by the
checkpoint and the installed package (inspected 2026-10-28):

- **No 512-token window.** `fastino/gliner2.5-base-v1` is a boundary model with `max_len` 4,096
  word tokens and a relative-position DeBERTa encoder (`relative_attention`, no absolute position
  input); the runtime truncates only when `max_len` is passed (`gliner2/inference/runtime.py`). The
  longest unit has 1,201 words and 2,497 subword tokens (`results/s1/sizes.tsv`). The 153 units over
  512 subword tokens are a length question (does recall fall on long inputs under the fixed
  proposal budget, `candidate_budget` 192, `start_top_k`/`end_top_k` 24), not a truncation one.
  `extract_long` chunks by GLiNER2 word tokens (384 by default), and its splitter makes every
  non-word character a token, so raw LaTeX chunks more units than the 17 over 384 words.
- **Loader.** `GLiNER2.from_pretrained` is the span-architecture class; boundary checkpoints load
  through `AutoExtractor.from_pretrained` ([GLiNER2 overview](../../libraries/parsing/gliner2.md) §2.4;
  `gliner2/inference/engine.py`), which `JointIE.from_pretrained` also uses. D4 M06's realization
  line is corrected through the report.

**Mention-level scoring (instrument revision I-R3).** The instruments name a mention-level
alignment for S2 ([instruments](comparison-instruments.md) §7) that no revision holds yet. It is a
revision package of the coordinator (§3.5), I-R2 plus one module. Before S2-C scores, its derived
occurrences are compared with those a fresh labeller marks by hand on T1–T4, as I-B's aligner was
compared with a hand alignment (instruments §9):

- *Occurrences.* For each reference entity of a unit: global classes, every word-bounded match of
  its label or an alias under D1 §6.2 normalization and the D2 §12.1 alias rules (the aligner's
  `alias_norm`); local entities and parameter symbols, every occurrence of the symbol in the unit's
  math (`mathgrammar.api.occurrences_in_span`, I-R1). An entity with none keeps its primary
  evidence spans, marked `anchor_only` and counted apart.
- *Alignment.* Per unit and class, mentions and occurrences match one-to-one
  (`linear_sum_assignment` on span IoU), at overlap > 0 and at IoU ≥ 0.5, both reported. An entity
  is found when one of its occurrences is matched; precision is over all mentions of the class.
- *Unmatched mentions* are not all errors, because the reference lists claim-bearing entities, not
  every mention. They are labelled `valid_unlisted`, `wrong_class`, `wrong_span` or `spurious`
  (§3.5 labelling independence), once per unit, span and class whichever variants produced them,
  and precision is given with and without `valid_unlisted`.
- *Contested items* (C1's `results/s0r2/contested.tsv`): "without" removes contested entities and
  claims from the denominators and makes mentions and relations that match them neutral.
- *Relations and records.* A reference core claim of `has_distribution` or `has_parameter` is found
  when a relation or record of that predicate has its head aligned to an occurrence of the claim's
  subject and its tail to one of its object, inside the claim's primary evidence sentence.
  Context-premise claims (evidence in a `cN` sentence outside the unit) are out of reach and
  counted apart.

**The phase 1 question.** GLiNER2 carries `has_distribution` when its core recall on the
uncontested, in-reach v1 claims is at least 0.6 on the core units and holds on H1–H6, on the better
relation surface (V2) at the threshold that gives it, with that threshold's precision stated; below
0.3 the LLM tier carries claims and encoders serve mentions and linking (brief). The denominators
are small (21 core and 8 held-out `has_distribution` claims before contested and out-of-reach items
are removed), so counts lead and intervals follow.

## 2. Brief steps as they now run

| Step | Now | Mechanism (owner) |
|---|---|---|
| 1 Environment | E4 builds `build/spike-gpu-venv` and the OPEN-D9-1 evidence for gliner2; S2 records device, checkpoint revision and `results/environment*.json` | §3.5 environments |
| 2 Combined extraction | On every paragraph and list item of the 12 core and six held-out units: one `batch_extract` per variant and threshold with entities, the `ParameterRole` group (`AttributeGroup`, `applies_to` the parameter class, `qualify_labels=True`), independent relations and the hand-written `distribution statement` structure (`mode="natural"`, `anchor="variable"`); `include_spans`, `include_confidence`. Schema from S4-D's dicts, or hand-written from D2 §9 with the `Schema.from_dict(d).to_dict() == d` check. Mask and Unicode texts from S1's `masked` and `rendered` (`code/s1_sentences.py`), mapped back by `back`. One run per threshold: flat decoding chooses among overlapping candidates, so filtering a low-threshold run is not equivalent | overview §3.5–§3.6, §6.1; D2 §7.2; D4 M06 |
| 3 Long units | Replaced: the 153 units run as whole units, as their paragraphs (step 2's unit) and through `extract_long` (384/64 word-token chunks, policy recorded) where they exceed one chunk; differences listed by position (lost, added, duplicated at a chunk edge), raw and mask; the long core units are also scored under each form | §1; overview §5.2–§5.4 |
| 4 Relations | As the brief; `JointIE` schema: the entity types of (a), `.relation("has distribution", head="random variable", tail="distribution family", unique_head=True)`, `has parameter` with the domain's mention classes as head, `.no_self_loops()`; `JointIEConfig(optimizer="beam", beam_size=32)`; `feasible` recorded per call, an infeasible call never counted as empty | overview §4.2; D2 §7.2 (b); D4 M07 |
| 5 Classification | As the brief; `Classifier` with one `.single()` task per enum, `ClassificationConfig(decoder="auto", on_infeasible="min_violations")`, `feasible` and `violations` recorded; scored against v1 statement kinds and modalities and the D2 §12.1 `block_hints`/`section_hints` | overview §4.1; D4 M05 |
| 6 Score | With I-R3 (§1): v1 on core and held-out units apart, v0 beside it on the core units; with and without contested items; per class, predicate, variant, surface and threshold. Thresholds are chosen on the core units and checked on H1–H6. Attribute accuracy on matched parameter mentions against the canonical name where it is a `ParameterRole` value. `unit.encoder_coverage` beside the share of sentences holding reference core claims | instruments §5.1, §7; D6 §6 |
| 7 Descriptions | As the brief; rewritten descriptions and added examples come only from pages outside the scored units | D2 §7.2 |
| 8 Overlap rule | Replaced by a pairwise test near math. Mentions: GLiNER2 under `flat` and `nested` policies, math-side mentions from `mathgrammar` symbol occurrences (standing in for M09) and the reference occurrences; a pair should cluster when both denote one reference entity. Rules scored on pair precision and recall: IoU ≥ 0.5; containment with a shared spaCy head (M03's adopted merged-math `en_core_web_sm`, run in the CPU environment); either (D5 §3.1 now); a math-aware rule (a text mention containing exactly one math span clusters with that span's math mention when the classes are compatible) | D5 §3.1; overview §2.3, §5.3 |
| 9 Throughput | As the brief, exclusive on the card, with `quantize`, `compile` and attention backend recorded; peak memory by `torch.cuda.max_memory_allocated`; G1's input | §3.5 GPU; overview §7.3–§7.4 |
| 10 Errors | Grouped by the labellers who label unmatched mentions, not by the root | §3.5 labelling independence |
| 11 Candidate scoring (new) | spaCy candidates written by the CPU environment to `results/s2/candidates/`: noun chunks, each inline math span, `X-ly distributed` token patterns, a `PhraseMatcher` gazetteer from the 78 page titles and the schema's `examples` (never the reference's labels). Scored per entity type with `score_explicit_spans` on the batch from `encode` (`EncodedBatch`; `indices` `[B, Q, C, 2]`, half-open word-token positions from the processor's offset maps; a candidate off word-token boundaries is recorded as unalignable). First, explicit scores are checked to reproduce the ordinary path's confidences on its own output spans, so one threshold scale serves both; then the candidates' recall ceiling (share of occurrences any candidate covers) and scored recall and precision against the proposal path | overview §6.3; `gliner2/models/boundary/model.py` (2.1.0); D4 §3; rationale §4.8 |
| 12 Page mentions (new) | The adopted configuration over every paragraph, list item and unit of the four spike pages; one file per page with label, class, offsets in the stored libxml2 renditions, score and configuration hash | §4 contract to S7 |

## 3. Variants

| Variant | Alternatives | What it would change |
|---|---|---|
| V1 math form | raw · mask (`⟨mN⟩`, mapped back) · Unicode (S1 variant d) | OPEN-D2-2: `math` in `extract.gliner_schema` and `extract.gliner_joint` (D2 §12.1 holds `mask` provisionally) |
| V2 relation surface | independent relations in `extract` · `JointIE` · `distribution statement` record | Whether M06 keeps relations, whether v0 gains a structure (D2 §3.2: none), or relations come from M07 only |
| V3 unit of work | paragraph and list item · whole unit · `extract_long` chunks | M06's segment kinds (now "short unit ≤ 384 words") and whether `extract_long` is needed at all |
| V4 span proposal | GLiNER2's proposals · spaCy candidates scored by `score_explicit_spans` · union | Whether the candidate method enters D4 §3 as conditional: only if M06's recall gap is a span-proposal problem |
| V5 schema form | compiled by S4-D · hand-written from D2 §9 (both when both exist) | Whether D2 §7.2's description rule (LinkML description plus examples) serves GLiNER2, or the pack needs its own encoder descriptions |
| V6 thresholds | global 0.3, 0.4, 0.5, 0.6, 0.7 · per class | `ci:threshold` per class or the method default 0.5 (D4 M06) |
| V7 overlap policy | `flat` (the checkpoint default) · `nested` | Whether nested mentions ("mean \(\mu\)" and `\mu`) reach mention clustering; the input to OPEN-D5-4 |

V1 × V6 run in full at step 2's unit of work under `flat`; the other variants run at the best V1
form and every threshold.

## 4. Consumers

| Output | Feeds |
|---|---|
| Math form, thresholds, overlap policy, unit of work | phase 1 M06/M07 configurations (`extract.gliner_schema`, `extract.gliner_joint`); OPEN-D2-2 |
| Relation and record scores, `has_distribution` recall | roadmap phase 1 entry (what the encoder tier carries, so how much M10 must); D5 §5.4 core absorption; D6 §6 `unit.encoder_coverage` and its escalation threshold (D6 §7.5) |
| Classification against markup | phase 1 M05: classify only where markup gives no statement kind, or everywhere |
| Candidate-scoring result | D4 §3 candidate method: enters as conditional or stays out |
| Schema form, accepted `from_dict` keys, description sensitivity | phase 1 GLiNER2 compiler (D2 §7.2); OPEN-D2-1 confirmation |
| Overlap rule | OPEN-D5-4; D5 §3.1 |
| Throughput, memory | G1 (OPEN-D6-2); D6 §5 budget row for GLiNER2 |
| Page mentions | S7 (linking cases and gold) |
| Loader and window facts | D4 M06/M07 realization lines, through X2 |

## 5. Packages

| Package | Scope | Outputs | Done when | Consumer |
|---|---|---|---|---|
| S2-A | Inputs: schema dicts (S4-D's or hand-written, round-trip check), mask and Unicode texts with offset maps, spaCy candidates and heads (CPU environment); I-R3's T1–T4 occurrence check | `results/s2/schema.json`, `joint_schema.py`, `variants/`, `candidates/`, `occurrence_check.md` | Every word boundary of each variant text maps back to its canonical offset on the scored units; derived occurrences agree with the hand-marked ones or each difference is explained | phase 1 GLiNER2 compiler (D2 §7.2; OPEN-D2-1 confirmation) |
| S2-B | Steps 2–5, 9 and 11 (runs), exclusive on the GPU | `mentions_{raw,mask,unicode}.jsonl` per threshold and policy, `long_units.jsonl`, `relations_*.jsonl`, `records_*.jsonl`, `classification.jsonl`, `explicit_scores.jsonl`, `throughput.tsv` | Every call recorded with its configuration; infeasible joint calls counted; the explicit-path reproduction check passes or its difference is recorded | phase 1 M05–M07; G1 (OPEN-D6-2) |
| S2-C | Steps 6–8 and 10, with I-R3 | `scores.tsv`, `classification.tsv`, `descriptions.tsv`, `overlap.tsv`, `errors.md`, `labels/` with transcripts | Every figure has its denominator, with and without contested items; unmatched mentions labelled by two independent labellers, disagreements by a third, agreement reported | phase 1 M05–M07 configurations; OPEN-D2-2, OPEN-D5-4 |
| S2-D | Step 12 and the report | `results/s2/mentions/<page>.jsonl`, `S2-report.md`, records `s2.*` | Page mentions exist at the adopted configuration; the template is satisfied; OPEN-D2-2 and OPEN-D5-4 answered or left open with the evidence still needed; M05–M07 configurations recommended | S7 (page mentions); phase 1 M05–M07; X2 |

Records (`consumed_by` names the phase 1 method, the OPEN item, G1 or S7): `s2.schema`,
`s2.mentions`, `s2.long-units`, `s2.relations`, `s2.classification`, `s2.candidates`,
`s2.descriptions`, `s2.overlap`, `s2.throughput`, `s2.page-mentions`.

## 6. Choices left to execution

- The hand-written descriptions, step 7's rewrites and the gazetteer's contents, as long as no
  scored unit's text is their source.
- How per-class thresholds are chosen on the core units (best F1, or recall at a precision floor),
  stated before H1–H6 are scored.
