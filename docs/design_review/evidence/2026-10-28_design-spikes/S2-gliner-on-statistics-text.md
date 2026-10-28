# S2 · GLiNER2.5 on statistics text

**Brief, 2026-10-28; revised after S0, S1 and S0-R2.** Ready: S0 has a reference for the core
units, S0-R2 has conformed it to guideline v1, and S1 has canonical text. GPU (CPU for the
throughput comparison).

## Question

What do GLiNER2.5's compiled schemas actually find in Siegrist's math-dense prose: entity
mentions, span attributes, record structures, independent and joint relations, and segment
classifications? Should math be passed raw, masked or rendered to Unicode (`OPEN-D2-2`)? This
sets what the encoder tier contributes in phase 1 and how much the LLM tier must carry.

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D2-2 | Raw LaTeX, masked placeholders or Unicode-rendered math in GLiNER2 input |
| OPEN-D5-4 | Mention-cluster overlap rule around math ("normally distributed with mean \(\mu\)") |
| D4 M05–M07 | Which surfaces (combined `extract`, `JointIE`, `Classifier`) earn their place, at which thresholds |
| D4 M06 | Whether `extract_long` handles units over the backbone's 512 tokens |
| D0 tiers | Whether encoder core candidates are good enough to absorb into LLM claims and to measure coverage |

## Inputs

- S1 canonical text and segments (`results/s1/`). Take unit, sentence and span offsets from
  `sample.json` as it stands.
- **Renditions.** M01 may produce renditions with html5lib (D4 M01). S0 and S1 used libxml2; on the
  seven pages S0 and S0-R2 use the two are content-identical and only keys differ
  ([s1.rendition-identity](records/s1.rendition-identity.json));
  use the renditions and offsets `sample.json` records, and note its
  `adapter_config.parser` in the report.
- **References.** The v1 reference, `results/s0r2/reference_v1/` (stored form), is the primary
  reference. The v0 reference, `results/s0/reference/`, is a second reference: report both.
- **Contested items.** Reference items whose adjudication decision is marked as a guideline gap:
  kind `guideline-gap` in `results/s0/adjudication.md`, and `guideline_gap` in the S0-R2
  adjudicator's decision tables (`results/s0r2/adjudication_v1/decisions/`). Take their union and
  write the list to `results/s2/contested.tsv`.
- [D2 §7.2](../../../design/D2-schema-and-guidelines.md#72-to-gliner2-schemas) and §9: write the
  GLiNER2 schema dict and the joint schema **by hand** from statistics schema v0 (the spike copies
  in `code/schema/` equal D2), or take S4's compiled output if S4 has run. Record which keys
  `Schema.from_dict` accepted.
- The Unicode rendering of S1's math variant (d): `code/s1_sentences.py`.
- S1 sizes (`results/s1/sizes.tsv`): the 153 units over 512 GLiNER2 backbone tokens.
- Checkpoint `fastino/gliner2.5-base-v1` from the local Hugging Face cache; `gliner2==2.1.0`.

## Procedure

1. **Environment.** Add `gliner2==2.1.0` (and torch as its extra requires) to the spike
   environment; record whether Python 3.14 wheels install (`OPEN-D9-1`).
2. **Combined extraction (M06).** On every paragraph and list item of the core units, run one
   `extract` with entities, attribute groups (`ParameterRole` on parameter mentions) and the
   `distribution statement` structure; `include_spans`, `include_confidence`. Three variants:
   **raw** (LaTeX as is), **mask** (each inline math span replaced by `⟨mN⟩`, mapped back) and
   **unicode** (math rendered to Unicode as `code/s1_sentences.py` does for variant (d), mapped
   back).
3. **Long units.** Run the combined extraction with `extract_long` on the 153 units over 512
   GLiNER2 tokens, raw and masked. Record the chunking used, whether any mention or relation is
   lost or duplicated at chunk boundaries, and how many units masking brings under 512 tokens.
   These units have no reference; count and inspect only.
4. **Relations.** Core units, two surfaces: independent relations in the combined schema, and
   `JointIE` with the joint schema (`unique_head` for functional predicates, `no_self_loops`,
   beam 32). Record `feasible` for every joint call.
5. **Classification (M05).** `Classifier` with `StatementKind` on units and paragraphs, and
   `ClaimModality` on the sentences that hold reference evidence spans.
6. **Score against the references.** Mentions: a reference entity is found if a mention of the
   same class overlaps any of its evidence anchors or symbol occurrences. Relations: a reference
   core claim (subject, predicate, object) is found if a relation's head and tail overlap the
   reference subject's and object's mentions in the claim's evidence sentence. Report precision,
   recall and F1 per class and predicate, per variant, over thresholds 0.3, 0.4, 0.5, 0.6, 0.7;
   against the v1 and the v0 reference; with and without the contested items. Context-premise
   claims, whose evidence is a `cN` sentence outside the unit, are out of a unit encoder's reach:
   count them separately, not as misses. Classification: accuracy against the reference
   statement kinds and modalities, and against the block-class and section-title hints for
   statement kinds (D2 §12.1).
7. **Description sensitivity.** For the two weakest classes, try two rewritten descriptions and
   one added example each; report the change. (Schema authors need to know how much wording
   moves results.)
8. **Overlap rule.** For mentions adjacent to or containing math, list cases where IoU ≥ 0.5 and
   head-sharing rules (D5 §3.1) disagree; propose the rule.
9. **Throughput.** Units per second on GPU at batch 1, 8, 16, and on CPU at batch 8; peak GPU
   memory; `extract_long` on the long units separately.
10. **Errors.** Twenty misses and twenty false positives with the sentence, grouped by cause
    (math adjacency, adjectival family forms, symbols, coordination, "respectively").

## Data to collect

| File | Content |
|---|---|
| `results/s2/schema.json`, `results/s2/joint_schema.py` | The hand-compiled schemas as run |
| `results/s2/contested.tsv` | Contested reference items: unit, item, source decision |
| `results/s2/mentions_{raw,mask,unicode}.jsonl` | One mention per line: unit, start, end, text, label, score, attributes |
| `results/s2/long_units.jsonl` | `extract_long` output on the 153 long units, with chunk boundaries |
| `results/s2/relations_{independent,joint}_{raw,mask,unicode}.jsonl` | One relation per line, with head and tail spans, score, `feasible` |
| `results/s2/scores.tsv` | reference (v1, v0) × contested (with, without) × surface × variant × threshold × label: tp, fp, fn, precision, recall |
| `results/s2/classification.tsv` | task × label: accuracy against the references and markup |
| `results/s2/descriptions.tsv` | class × description variant: precision, recall |
| `results/s2/throughput.tsv` | device × batch × call (`extract`, `extract_long`): units/s, peak memory |
| `results/s2/errors.md` | Grouped misses and false positives |

## How to interpret

| Finding | Reading |
|---|---|
| Mask (or Unicode) beats raw on recall without losing precision | Configure M06/M07 with that variant; `OPEN-D2-2` closed |
| `JointIE` raises relation precision at similar recall | Relations come from M07 only; drop independent relations from M06 |
| `has_distribution` core recall ≥ 0.6 against the v1 reference | Encoder cores are useful for coverage metrics and as confidence sources |
| Core recall < 0.3 for most predicates | The LLM tier carries claims in phase 1; encoders serve mentions and linking only. Not a failure: it sets the phase 1 policy |
| Scores move much when contested items are dropped | The encoder's misses sit where the guideline is still open; read its recall against the uncontested set |
| `extract_long` loses or duplicates items at chunk boundaries | M06 needs masking or a chunk-overlap setting before long units; record it for D4 M06 |
| Statement kind accuracy close to the markup hint | M05 is needed only where markup is absent (paragraphs outside units) |
| Large description sensitivity | Schema descriptions are a tuning surface; experiments must version them (they do: descriptions are in the schema hash) |

## Report

`S2-report.md` from the [template](report-template.md), answering `OPEN-D2-2` and `OPEN-D5-4`
and stating the recommended M05–M07 configurations. Report figures against the v1 reference
first and the v0 reference beside them.
