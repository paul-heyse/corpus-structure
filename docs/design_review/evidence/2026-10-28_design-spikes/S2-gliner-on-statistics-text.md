# S2 · GLiNER2.5 on statistics text

**Brief, 2026-10-28.** Run after S0 has adjudicated references for the core units and S1 has
canonical text. GPU (CPU for the throughput comparison).

## Question

What do GLiNER2.5's compiled schemas actually find in Siegrist's math-dense prose: entity
mentions, span attributes, record structures, independent and joint relations, and segment
classifications? Should math be passed raw or masked (`OPEN-D2-2`)? This sets what the encoder
tier contributes in phase 1 and how much the LLM tier must carry.

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D2-2 | Raw LaTeX or masked placeholders in GLiNER2 input |
| OPEN-D5-4 | Mention-cluster overlap rule around math ("normally distributed with mean \(\mu\)") |
| D4 M05–M07 | Which surfaces (combined `extract`, `JointIE`, `Classifier`) earn their place, at which thresholds |
| D0 tiers | Whether encoder core candidates are good enough to absorb into LLM claims and to measure coverage |

## Inputs

- S1 canonical text and segments (`results/s1/`), `sample.json`.
- S0 adjudicated references (`results/s0/reference/`).
- [D2 §7.2](../../../design/D2-schema-and-guidelines.md#72-to-gliner2-schemas) and §9: write the
  GLiNER2 schema dict and the joint schema **by hand** from statistics schema v0 (or take S4's
  compiled output if S4 has run). Record which keys `Schema.from_dict` accepted.
- Checkpoint `fastino/gliner2.5-base-v1` from the local Hugging Face cache; `gliner2==2.1.0`.

## Procedure

1. **Environment.** Add `gliner2==2.1.0` (and torch as its extra requires) to the spike
   environment; record whether Python 3.14 wheels install (`OPEN-D9-1`).
2. **Combined extraction (M06).** On every paragraph and list item of the core units, run one
   `extract` with entities, attribute groups (`ParameterRole` on parameter mentions) and the
   `distribution statement` structure; `include_spans`, `include_confidence`. Two variants:
   **raw** (LaTeX as is) and **mask** (each inline math span replaced by `⟨mN⟩`, mapped back).
3. **Relations.** Same units, two surfaces: independent relations in the combined schema, and
   `JointIE` with the joint schema (`unique_head` for functional predicates, `no_self_loops`,
   beam 32). Record `feasible` for every joint call.
4. **Classification (M05).** `Classifier` with `StatementKind` on units and paragraphs, and
   `ClaimModality` on the sentences that hold S0 evidence spans.
5. **Score against S0.** Mentions: a reference entity is found if a mention of the same class
   overlaps any of its evidence anchors or symbol occurrences. Relations: a reference core claim
   (subject, predicate, object) is found if a relation's head and tail overlap the reference
   subject's and object's mentions in the claim's evidence sentence. Report precision, recall and
   F1 per class and predicate, per variant, over thresholds 0.3, 0.4, 0.5, 0.6, 0.7.
   Classification: accuracy against S0 statement kinds and modalities, and against the block-class
   and section-title hints for statement kinds (D2 §12.1).
6. **Description sensitivity.** For the two weakest classes, try two rewritten descriptions and
   one added example each; report the change. (Schema authors need to know how much wording
   moves results.)
7. **Overlap rule.** For mentions adjacent to or containing math, list cases where IoU ≥ 0.5 and
   head-sharing rules (D5 §3.1) disagree; propose the rule.
8. **Throughput.** Units per second on GPU at batch 1, 8, 16, and on CPU at batch 8; peak GPU
   memory.
9. **Errors.** Twenty misses and twenty false positives with the sentence, grouped by cause
   (math adjacency, adjectival family forms, symbols, coordination, "respectively").

## Data to collect

| File | Content |
|---|---|
| `results/s2/schema.json`, `results/s2/joint_schema.py` | The hand-compiled schemas as run |
| `results/s2/mentions_{raw,mask}.jsonl` | One mention per line: unit, start, end, text, label, score, attributes |
| `results/s2/relations_{independent,joint}_{raw,mask}.jsonl` | One relation per line, with head and tail spans, score, `feasible` |
| `results/s2/scores.tsv` | surface × variant × threshold × label: tp, fp, fn, precision, recall |
| `results/s2/classification.tsv` | task × label: accuracy against S0 and markup |
| `results/s2/descriptions.tsv` | class × description variant: precision, recall |
| `results/s2/throughput.tsv` | device × batch: units/s, peak memory |
| `results/s2/errors.md` | Grouped misses and false positives |

## How to interpret

| Finding | Reading |
|---|---|
| Mask beats raw on recall without losing precision | Configure M06/M07 with masking; `OPEN-D2-2` closed |
| `JointIE` raises relation precision at similar recall | Relations come from M07 only; drop independent relations from M06 |
| `has_distribution` core recall ≥ 0.6 | Encoder cores are useful for coverage metrics and as confidence sources |
| Core recall < 0.3 for most predicates | The LLM tier carries claims in phase 1; encoders serve mentions and linking only. Not a failure: it sets the phase 1 policy |
| Statement kind accuracy close to the markup hint | M05 is needed only where markup is absent (paragraphs outside units) |
| Large description sensitivity | Schema descriptions are a tuning surface; experiments must version them (they do: descriptions are in the schema hash) |

## Report

`S2-report.md` from the [template](report-template.md), answering `OPEN-D2-2` and `OPEN-D5-4`
and stating the recommended M05–M07 configurations.
