# Rollout and evaluation

**Proposed · 2026-11-03.** Use the first-release gates for M1. The nine-stage rollout is the broader reference decomposition. It maps model additions, combinations, decisions, prototypes and evaluation to stages. M1 delivers across those layers and gates each complete record family. [M1 evaluation and expansion](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf) · [Reference rollout](https://app.notion.com/p/40b141b5836981c5aa7cf562fe54fb4a)

## Freeze the populations and references

- **Record audit.** Independently sample eligible source regions and label all in-scope records, including regions with no candidate or accepted output. This supplies a recall denominator under the guideline.
- **Open coverage audit.** Sample original pages and regions beyond the supported schemas and emitted output. Record absent or unreadable intake, unrun routes and knowledge the representation cannot express. Audit unsupported content separately from supported-subset recall.
- **Challenge cohorts.** Track hard interactions, ambiguity and known failure modes separately from prevalence-weighted random audits. Include clean and degraded prose, mathematical passages, definitions, examples, tables and notes, lists, cross-references and empty outputs.

Freeze the source population, selected intake cut and digests, seed, strata and inclusion probabilities, guideline, schema and evaluator provenance. Reuse the protected evaluator and its core/full/evidence alignment tiers. Author references independently from sources. Keep evaluation assistance behind the evaluator boundary, and adjudicate disagreements and a quality sample. Isolate development, fitting/calibration and final assessment. Keep overlapping windows, copies, related editions and repeated tables together. Chapter/section groups in a single textbook establish within-book evidence only and require an explicit evaluator partition extension. Refresh final assessment if its errors enter development. [Repository evaluation design](../design/D7-evaluation-goldens-outer-loop.md) · [Semantic alignment](../../python/corpus-structure/src/corpus_structure/evaluate/semantic_alignment.py)

## Metrics and denominators

| Metric | Operational definition |
| --- | --- |
| Intake availability | Faithfully represented admitted regions divided by audited original regions |
| Routing coverage | Eligible targets scheduled divided by independently identified eligible targets |
| Candidate capture recall | Eligible gold records with all required alternatives generated divided by eligible gold records |
| Candidate retention | Required generated candidates surviving thresholds, overlap policy, budgets and decoding divided by those initially generated |
| Accepted full-record precision | Correct accepted complete records divided by accepted records |
| Accepted full-record recall | Correct accepted complete records divided by eligible gold records |
| Evidence correctness | Evaluated records with every required valid source anchor divided by evaluated records |
| Qualification correctness | Correct roles, modality, polarity, attribution, conditions and scope among cases where they apply |
| Unresolved/abstention rate | Eligible cases held unresolved by reason divided by eligible cases |
| Calibration | Proper scores, reliability curves and selective precision/coverage at acceptance thresholds |
| Resource cost | CPU/wall time, peak memory, latency, cache/replay and correct full records per resource unit |

Wrong unit, role, condition or negation is a full-record error even when other fields match. Report partial fields separately. Report per family and by source/quality stratum. Distinguish repeated source occurrences and consolidated facts. Reflect table, chapter and source-family dependence in uncertainty estimates. [M1 metrics](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf)

## Release gates

These are proposed policy targets. Refine on development data and freeze before final assessment. Record explicit approval and justification for a changed target.

| Gate | Initial policy |
| --- | --- |
| Source custody | Version-correct resolvable evidence for every required field. Zero accepted records with known broken mappings. |
| Coverage accounting | All selected targets have dispositions, including unsupported, partial, failed and skipped work. |
| Candidate recall | Working target ≥90% per core family in its supported subset. |
| Accepted precision | Working target ≥97% full-record precision, with a one-sided 95% lower bound ≥95% using a method appropriate for source clustering. |
| Useful recall | Predeclare a family-specific floor. Planning starts around 70% accepted full-record recall on supported subsets. |
| Subgroups | Restrict a release manifest when a language, layout or source stratum fails. |
| Calibration | Held-out evidence before labeling probabilities calibrated. Otherwise expose score/decision status and the evaluated acceptance policy. |
| Operations | CPU budget, replay, interruption/resume, invalidation and policy-controlled publication demonstrated. |
| Generative independence | Extraction assessment runs with general LLM extraction disabled. Record reference/evaluator assistance separately. |

Predeclare intervals and sample size from desired precision and independent source groups. Insufficient evidence leaves the gate unestablished even if the sample has zero errors. Report released, candidate-only and unsupported subsets per family. A canary can release fewer families. Full M1 requires released subsets for all five unless scope is explicitly revised. Procedure shadow candidates face the same gates for promotion. [M1 release policy](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf)

## Capacity and operating evidence

Measure on the actual Linux desktop with CPU, RAM, thread settings, workers, package/checkpoint, precision, schema and input lengths recorded. The pilot proposes up to 16 aggregate downstream NLP threads and a 32 GiB resident cap, subject to available memory and co-running work. These are proposed experiment controls. Record p50/p95 unit latency, pages/tokens and correct complete records per hour, cold/warm behavior, inference/decoding/persistence costs, cache and restart behavior. Include long contexts, dense schemas and tables. Choose the operating envelope from actual profiles and refresh requirements. If base exceeds the envelope, test small, schema routing, bounded coherent windows, batching and redundant-pass removal while preserving family gates. [CPU capacity](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf)

## Baselines and ablations

Compare independent union, deterministic rules/joins, a fitted independent or stacking method, and a bounded coupled template. Compare coupled variants with ontology and dependence handling removed where appropriate. Keep source cut, contracts and evaluation policy fixed. Compare at matched coverage to isolate gains from abstention or at matched precision to assess usable additional records.

- **Fixed evidence.** Hold candidate universe and observations constant while changing decision factors or decoding.
- **End to end.** Recompute dependent candidates, observations, windows and routes after a component changes. Cached masking is valid only for outputs that did not consume the removed component.

For GLiNER compare base/small, combined/separate packs, routed/broad execution, independent relations/JointIE and native grouping/span assembly. Report paired source-group uncertainty, additional correct full records, new errors, changes in qualification and evidence, and resource effects. A complex solver earns adoption when the record-level gain or error reduction warrants it. [M1 evaluation](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf) · [Reference baselines](https://app.notion.com/p/40b141b583698119a17ad60732732306)

## Gap-driven expansion

A gap record carries source/native anchors and intake cut, audit population, expected knowledge, observed outcome, earliest failing stage, reference and diagnostic evidence, estimated prevalence and semantic impact where defensible, proposed repair, comparison cohort and baseline, outcome and replay scope. Capture no-route, empty, partial, wrong, abstained, unsupported, failed and lost-after-publication outcomes separately. Sample random sources as well as uncertainty cases so agreement among parsers cannot hide shared omissions.

| Observed failure | First repair | Additional option if the gap persists |
| --- | --- | --- |
| Missing definition or qualifier span | Descriptions, nested-span policy, windows and budgets | Domain adaptation or dedicated extractor |
| Incorrect grouping | Anchored record mode, explicit roles and syntax | Joint interpretation or relation specialist |
| Distant reference | Target retrieval and bounded context expansion | Evaluated coreference |
| Unit/value role | Numeric grammar, domain units/Pint and role schema | CQE after offset/domain tests |
| Table gaps | Restore headers, rows, captions, units and notes | Table-role specialist for residual semantic loss |
| Formula binding | Local declarations, formula scope and assumption cues | Description-alignment specialist |
| Long-range condition or attribution | Retrieve context and explicit scope alternatives | Routed discourse/SRL |
| Missing entity identity | Ontology aliases, lexical/embedding retrieval and NIL | Domain linker or ReFinED where target universe fits |
| Weak citation lineage | Native markers and document-type rules | GROBID for scholarly references |
| Corpus conflict | Align qualifiers and retain support ledger | Validated NLI/support checker |
| Non-English gap | Language routing and schema validation | Multilingual GLiNER or language-specific syntax |
| Unrepresentable knowledge | Extend contract and guideline | Select extraction mechanisms for the new target |

Predeclare the intended semantic gain and minimum practical improvement, freeze the baseline, try the least costly repair, evaluate the gap cohort and broad regression sample, and record adopt, route, revise, defer or reject. Report paired changes in true and false positives, recall, resource use and dependency burden. Restrict gains observed in an identifiable stratum to that route. CQE has a spaCy rule substrate and may normalize text, so test offsets and compatibility. NLI and argument support require distinct evaluation. Rank candidate actions by gap prevalence, semantic impact, recoverability and cost as a heuristic. Learned value-of-information routing requires outcome evidence.

Expand from local records to difficult local coverage, document-level references and conditions, cross-document qualified support, then reviewed ontology growth as evidence warrants. Consider bounded generative assistance only on measured residual gaps with grounding, false-positive and cost checks. After release, monitor drift, truncation, infeasibility, unresolved reasons and reviewed precision. Version changed artifacts, replay affected inputs and retain the prior accepted cut for rollback. [Expansion design](https://app.notion.com/p/40d141b5836981f894d4e90a5e1ee9cf)

## Nine-stage reference rollout

The earlier rollout builds shared machinery at stage 1, then adds typed decisions, factors, rules and record types at each stage. Its reference components are the record-type registry and utility policy, immutable observation store, calibration table, decision registry, bounded factor templates, lineage, evaluation harness and seed ontology v0. Acceptance/escalation and corpus evidence contracts are defined early and used as needed. In M1, preserve those contracts where applicable and use the [corrected inference and evaluation semantics](first-production-milestone.md#bounded-interpretation). [Stage-1 machinery](https://app.notion.com/p/40b141b583698127bfb2c1a9c18e278b)

| Stage | Outcome | Reference gate or check |
| --- | --- | --- |
| 1 · Framing | Anchored units, sections, citations and editions | Gate precision, reliability calibration, extraction by grade, manual duplicates |
| 2 · Span inventory | Located mentions, quantities, units and attachments | Candidate recall, calibration and interaction of quantities with parse/ontology. Check about 100 numbers. |
| 3 · Identity | Grounded entities, clusters and typed NIL with reasons | Fixed versus end-to-end, ontology ablation and NIL reasons. Check about 50 clusters. |
| 4 · Propositions | Measurement/specification/comparison records and text–table checks | Complete table records, note/condition attachment and effect of refitting identity/type/relation. Review text–table conflicts. |
| 5 · Qualification | Fully qualified claims and numeric reference resolution | Assembly, disambiguation and candidate-coverage decomposition. Check about 200 sentences per qualifier. |
| 6 · Discourse and argument | Support/attack/none edges and citation functions | Pair-candidate recall and discourse/proximity interaction with NLI. Review edges on 10 documents in the reference design. |
| 7 · Corpus | Qualified equivalences, conflicts, provenance groups, drift and distributions | Contradiction/equivalence precision and support sensitivity. Check about 50 each of contradictions, equivalences and compliance findings. |
| 8 · Ontology | Reviewed proposals and a new accepted ontology version | Expert review and change in held-out utility from v0 to v1. |
| 9 · Records and control | Complete validated records and bounded escalation | Utility per CPU-second and independent completeness audit, with PPI where justified. |

The three reference prototypes run with generation disabled. P1, quantities and conditions, completes at stage 5. P2 spans stages 3–4 and jointly resolves clusters, type, links and relations. P3 assembles tables at stage 4. The source's 20-document labelled harness, passage recall sample and manual counts are historical design parameters. M1 sizes the assessment to its gate evidence needs. Reference stress tests include duplicated evidence, removed clues, flipped negation, moved conditions and plausible incorrect ontology expectations. [Stages register](registers/stages.md) · [Prototype plan](https://app.notion.com/p/40b141b583698119a17ad60732732306)

The longer-term loop writes versioned observations, generates candidates plus unresolved, performs bounded joint resolution and deterministic closure, accepts at evaluated thresholds, targets retrieval or reprocessing, records corpus support/conflict and reviews ontology proposals. The earlier plan envisages EVI-based escalation through targeted extraction, local CPU LLM and review, plus a post-stage-5 LLM comparison. It also envisages eight stream groups (layout, parse, mentions, quantities, identity, conditions, tables, ontology) and 256 subset evaluations, with corpus and LLM as later groups. Exact group Shapley/Möbius and paired interactions, within-group permutation sampling and fresh audit estimates are analytical extensions. Compute them against a fixed population and policy, with end-to-end dependency replay when measuring components. Model changes re-run affected evidence and a frozen benchmark. Review utility per CPU-second, per-family precision, candidate recall and calibration. Treat attribution as a diagnostic for further controlled experiments. [Finished loop and release checks](https://app.notion.com/p/40b141b5836981939830fb1a4f1aa16a) · [Mathematics](mathematics.md)


## Reviewed M1 evaluation and adoption boundary

**Proposed · 2026-11-03; [review O07](../functional_reviews/m1-target-design_2026-11-03.md#O07).**
Extend the existing protected evaluator beyond its current `agent_claims` family rather than
creating another scorer. Family guidelines must describe which core/full/evidence comparisons
apply, occurrence versus fact counting, qualifier applicability and field-to-anchor matching.
References are independently authored from sources; production validators establish conformance,
not reference correctness. A strict validator rejecting both sides is not evidence of fidelity.

The population is the statistics source cut with explicit supported subsets. Source-region audits
supply recall denominators, including eligible regions producing nothing. The larger original-page
coverage audit accounts for absent/unreadable intake and unrepresentable knowledge separately.
Engineering transfer cases must exercise the same shared operations with another domain profile;
they are contract challenges, not an engineering release or a population estimate.

Keep development, fitting, final-event calibration and final assessment isolated by credible
source-origin groups. Use explicit group splits for fitting tools. For paired comparisons,
resample groups and recompute aggregate ratios; pairing rows alone is insufficient. Do not let a
degenerate all-correct bootstrap certify the precision lower bound. Sampling and interval choice,
independent-group sufficiency and actual candidate component sizes remain pre-release prerequisites.
See [numerical evaluation details](mathematics.md#m1-numerical-realization). Working gate targets
above remain unchanged and unestablished by this review.

Required consumer challenges are the definition/alias, pressure ambiguity, table-note, scoped
formula, no-output/search-limit and invalidation/interruption cases in the
[milestone](first-production-milestone.md#worked-contract-challenges). Exercise actual extraction,
publication, pinned CLI/MCP inspection and export with general LLM extraction disabled. A mock
model or static walkthrough cannot establish the corresponding provider or release outcome.
Qualification also covers extreme numeric weights, empty feasible support, complete-record events
and state-order changes independently of production expectations.

Record aggregate CPU/thread settings and process RSS as well as engine settings. DuckDB's
`memory_limit` is not a process memory guarantee, and Arrow batch rows/readahead do not bound bytes.
Profile dense/long contexts and actual whole-record output before claiming the initial envelope.
Maintain the original failed/interrupted results and the prior accepted cut for rollback.
Broader O08–O11 opportunities stay in the review with promotion conditions; no all-stream ablation,
new specialist, runtime probe or benchmark campaign is required merely to finish this design.
