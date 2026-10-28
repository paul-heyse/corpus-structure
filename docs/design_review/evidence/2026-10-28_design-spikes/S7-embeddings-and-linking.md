# S7 · Embeddings and linking

**Brief, 2026-10-28.** GPU. Run after S1 and S2 (mentions) and S0 (reference entities).

## Question

Which embedding model and dimension should pgvector store, and how well does concept linking
(D4 M14) resolve mentions of global entities across Siegrist pages: by alias normalization alone,
with fuzzy matching, and with vectors? Do segment embeddings retrieve useful prompt examples?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D3-2 | Embedding model and stored dimension |
| D4 M14 | Which candidate-generation steps earn their place, and the thresholds |
| D4 §4.2 | Whether nearest-unit retrieval gives relevant examples |
| OPEN-D6-2 | Memory of the embedding model beside vLLM and GLiNER2 |

## Inputs

- S1 segments for the 78 first-pass pages.
- S2 mentions of global classes (`DistributionFamily`, `FamilyConstruction`, `Concept`,
  `FamilyParameter`) on the spike pages.
- S0 reference global entities (canonical labels) and the page titles as seed entities.
- Qwen3-Embedding-0.6B and Qwen3-Embedding-8B from the local Hugging Face cache.

## Procedure

1. **Embed** all `unit` and `paragraph` segments of the 78 pages, and every alias of the seed
   and reference entities with its class description, with: 0.6B at 1024; 8B at 1024, 2048 and
   4096 (Matryoshka truncation, then L2 normalization). Use the model card's query instruction for
   mentions and aliases.
2. **Link gold.** Label each S2 global mention on the spike pages with its reference entity, or
   "new" if none (use S0 references; label the rest by hand, recording that you did).
3. **Linking variants.** (a) exact normalized alias; (b) plus lemma, head-word removal and
   adverb rules (D4 M14); (c) plus `rapidfuzz` `token_set_ratio`; (d) plus vector nearest
   neighbours for each embedding configuration. Report accuracy@1, accuracy@5, and new-entity
   precision and recall at three thresholds.
4. **Retrieval.** For each core unit, the five nearest units among the 78 pages (excluding its own
   page). Label each neighbour relevant if it shares the statement kind and the main entity or
   construction (by S0 reference or inspection). Report precision@5 per configuration.
5. **Cost.** Throughput (segments per second) and peak GPU memory per model; whether 0.6B fits
   beside vLLM in co-resident mode (with S3's settings).

## Data to collect

| File | Content |
|---|---|
| `results/s7/link_gold.tsv` | mention, reference entity or new, labeled by |
| `results/s7/linking.tsv` | variant × embedding × threshold: acc@1, acc@5, new P/R |
| `results/s7/retrieval.tsv` | unit × embedding: precision@5, neighbours |
| `results/s7/perf.tsv` | model × dimension: throughput, memory |

## How to interpret

| Finding | Reading |
|---|---|
| (b) alone reaches most of the accuracy | Phase 1 linking without vectors; vectors in phase 2 only if a gap appears |
| Vectors fix adjectival and paraphrased forms that (c) misses | Keep vector candidates in M14 from phase 1 |
| 0.6B within a few points of 8B | 0.6B at 1024; `OPEN-D3-2` closed; co-resident mode stays feasible |
| Retrieval precision@5 low | Choose prompt examples by statement kind and entity overlap instead of embeddings |

## Report

`S7-report.md` from the [template](report-template.md), with the embedding choice, the M14
configuration and thresholds.
