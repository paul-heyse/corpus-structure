# S7 · Embeddings and linking

**Brief, 2026-10-28; revised after S0, S1 and S0-R2.** GPU. Waits on S2 (mentions); S1 segments
and the v1 reference's entities are available.

## Question

Which embedding model and dimension should pgvector store, and how well does concept linking
(D4 M14) resolve mentions of global entities across Siegrist pages: by alias normalization alone,
with fuzzy matching, and with vectors? Do parameter mentions link to the parameter their family's
defining unit names, across units? Do segment embeddings retrieve useful prompt examples?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D3-2 | Embedding model and stored dimension |
| D4 M14 | Which candidate-generation steps earn their place, and the thresholds |
| D2 §10.4, RG-7 | Whether linking keeps a family's canonical parameter names stable across units |
| D4 §4.2 | Whether nearest-unit retrieval gives relevant examples |
| OPEN-D6-2 | Memory of the embedding model beside vLLM and GLiNER2 |

## Inputs

- S1 segments for the 78 first-pass pages.
- **Renditions.** M01 may produce renditions with html5lib (D4 M01). S0 and S1 used libxml2; on the
  seven pages S0 and S0-R2 use the two are content-identical and only keys differ
  ([s1.rendition-identity](records/s1.rendition-identity.json));
  take renditions, segment keys and offsets from `sample.json` and `results/s0r2/sample.json` as
  they stand.
- S2 mentions of global classes (`DistributionFamily`, `FamilyConstruction`, `Concept`,
  `FamilyParameter`) on the spike pages.
- **Gold entities.** The v1 reference's global entities (`results/s0r2/reference_v1/`, stored
  form) with their canonical labels and identity attributes, and the page titles as seed
  entities.
- **Parameter names (B2).** A family parameter's canonical name is the role word in the phrase that
  first names the symbol a parameter of the family, otherwise the symbol; a role stated later is a
  `parameter_role` claim, not the name. Where the v1 reference and this rule differ, the rule
  decides the gold, and the difference is recorded.
- Qwen3-Embedding-0.6B and Qwen3-Embedding-8B from the local Hugging Face cache.

## Procedure

1. **Embed** all `unit` and `paragraph` segments of the 78 pages, and every alias of the seed
   and reference entities with its class description, with: 0.6B at 1024; 8B at 1024, 2048 and
   4096 (Matryoshka truncation, then L2 normalization). Use the model card's query instruction for
   mentions and aliases.
2. **Link gold.** Label each S2 global mention on the spike pages with its v1 reference entity, or
   "new" if none (label the rest by hand, recording that you did). Name family parameters under
   B2.
3. **Cross-unit parameter cases (RG-7).** Collect, as their own linking cases, the parameter
   mentions in units other than their family's defining unit: the normal's parameters across T2,
   T3, U5 and U6; the lognormal's in U9 against T4; the gamma's across U10–U12; and any others on
   the spike pages. Each links to the `FamilyParameter` entity of the defining unit, whatever
   symbol or role word the mentioning unit uses. Report them separately in step 4.
4. **Linking variants.** (a) exact normalized alias; (b) plus lemma, head-word removal and
   adverb rules (D4 M14); (c) plus `rapidfuzz` `token_set_ratio`; (d) plus vector nearest
   neighbours for each embedding configuration. Report accuracy@1, accuracy@5, and new-entity
   precision and recall at three thresholds, overall and on the cross-unit parameter cases.
5. **Retrieval.** For each core unit, the five nearest units among the 78 pages (excluding its own
   page). Label each neighbour relevant if it shares the statement kind and the main entity or
   construction (by the v1 reference or inspection). Report precision@5 per configuration.
6. **Cost.** Throughput (segments per second) and peak GPU memory per model; whether 0.6B fits
   beside vLLM in co-resident mode (with S3's settings).

## Data to collect

| File | Content |
|---|---|
| `results/s7/link_gold.tsv` | mention, unit, reference entity or new, cross-unit parameter case (yes/no), labeled by |
| `results/s7/linking.tsv` | variant × embedding × threshold × case set (all, cross-unit parameters): acc@1, acc@5, new P/R |
| `results/s7/retrieval.tsv` | unit × embedding: precision@5, neighbours |
| `results/s7/perf.tsv` | model × dimension: throughput, memory |

## How to interpret

| Finding | Reading |
|---|---|
| (b) alone reaches most of the accuracy | Phase 1 linking without vectors; vectors in phase 2 only if a gap appears |
| Vectors fix adjectival and paraphrased forms that (c) misses | Keep vector candidates in M14 from phase 1 |
| Cross-unit parameter mentions link poorly under every variant | Linking cannot stand in for a family's parameterizations; RG-7 needs the representation (D2 §9), and the annotator reference should list each family's parameters once defined |
| 0.6B within a few points of 8B | 0.6B at 1024; `OPEN-D3-2` closed; co-resident mode stays feasible |
| Retrieval precision@5 low | Choose prompt examples by statement kind and entity overlap instead of embeddings |

## Report

`S7-report.md` from the [template](report-template.md), with the embedding choice, the M14
configuration and thresholds, and the cross-unit parameter result.
