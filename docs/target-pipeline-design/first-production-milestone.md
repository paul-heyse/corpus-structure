# First production milestone

**Proposed · 2026-11-03.** M1 adds a shared CPU semantic assembly path downstream of the existing Docling and Nemotron 3.5 intake. Release five bounded families of qualified source records through existing custody and publication owners. Acceptance means a faithful reading under a released annotation guideline. Scientific truth, causal validity and proof verification are separate tasks. [Milestone proposal](https://app.notion.com/p/40d141b58369818ca7cff992a52c7d6e)

## Products and scope

| Family | Initial supported shape | Attachment and evidence obligations |
| --- | --- | --- |
| Definitions and concepts | Explicit definitions, aliases/abbreviations and stated hierarchy or instance relations | Keep term and defining passage separately anchored. Resolve local sense and scope. Treat proposed global identity or ontology changes as reviewable. |
| Qualified local assertions | Explicit typed relations or predicate/argument frames with recoverable local arguments | Preserve condition, exception, modality, polarity, attribution, quantification and applicable time/scope. A meaning-changing unresolved qualifier prevents unqualified acceptance. |
| Measurements and comparisons | Entity/property/value/unit with a stated value role, comparator, bounds and uncertainty when applicable | Preserve the numeric string, normalized value, role and all conditions. Record unit conversions as deterministic derivations with premises. |
| Table assertions | Tables with recoverable rows, columns, full header paths and note inheritance | Anchor each field to native cells and applicable caption, notes and units. Preserve blank/missing semantics and report ambiguous layouts. |
| Formula and symbol context | Existing formula occurrence linked to explicit local symbol declarations, meanings, assumptions or definition/result text | Keep formula coordinates distinct from nearby prose and respect symbol scope. |

Also emit a source coverage and routing ledger, multi-label content roles, typed mentions and attributes with alternatives, and a source-grounded gap ledger. Preserve unknown, unstated and inapplicable states independently. Simple ordered procedures are shadow evaluation using grouped action/input/output/condition fields. Promotion is conditional on the same family gates and delivery of the five core families. [Milestone products](https://app.notion.com/p/40d141b58369818ca7cff992a52c7d6e) · [GLiNER2.5 deployment](gliner-deployment.md)

## Source preparation and routing

1. Consume a **pinned selected view** with source ancestry, projection/recipe digests, recognition health, selection lineage and native item, table and formula addresses. Keep original PDF material, admitted intake and schema-eligible material as separate populations.
2. Extend the existing sentence preparation into one reusable linguistic product containing tokens, sentences, lemmas, POS, morphology and needed dependencies. Retain exact reconstruction, formula/reference atoms, block boundaries and pinned model versions. Use spaCy initially. Stanza is a measured comparison.
3. Construct bounded typed contexts. Local prose uses a sentence or paragraph, neighbors and section ancestry. Definitions preserve term and defining passage. Formula context pairs native formula occurrences with declarations and prose. Table context combines native cells, row keys, header paths, units, captions and notes. Targeted references record the retrieval reason, candidates and all consumed inputs. Every context keeps reversible coordinate maps, including when model input is normalized or a table is serialized.
4. Run a coverage pass on all selected views and record applicability and outcomes, including an empty result. Use a modest high-recall role, anchor and mention schema with structural checks. The focused pass routes compact packs from structure, rules and classification. Table, formula and list cues can independently trigger a pack. Mixed and unknown units receive bounded fallback or explicit pending status. Audit units omitted by routing.
5. Resolve missing roles through bounded context widening, explicit declaration or note retrieval, larger candidate budgets or a measured specialist. Capture each action, its inputs, resource cost and terminal reason.

Use existing sentence and [native frame](../../python/corpus-structure/src/corpus_structure/semantic/proposals.py) preparation as the starting seam. Native frames currently support primary evidence and bounded direct ancestors. Neighbor, table-note and general reference contexts require an explicit extension. [Architecture and contracts](https://app.notion.com/p/40d141b58369819eb958e952d47b0301) · [Sentence preparation](../../python/corpus-structure/src/corpus_structure/ingest/sentences.py)

## Observation and publication contracts

Extend `SourceObservationBatch` and the existing result binding path. Preserve producer and operation versions, checkpoint and tokenizer revision, schema and configuration digests, normalization and context inputs, and consumed ontology/calibration versions. Store raw alternatives with stable IDs, source anchors, score meaning and available suppression reasons. Carry invocation/window and shared upstream dependency groups, feasibility and constraint violations, search limits, truncation/exactness and unresolved reason. Record scope actually inspected and coverage in the observation contract. Keep scheduling, skips and `not_run` in the routing ledger. Measure CPU and wall time, peak memory, batch/window/schema size, candidate counts and cache outcome.

Multi-anchor evidence is a proposed extension. Use named, role-labelled anchor sets with explicit coordinate spaces, including noncontiguous text, native item pointers, cells and formula occurrences. A source occurrence has a different identity from a normalized fact. Mark each field as extracted, normalized or derived and preserve coherent alternatives, calibration status, policy version, derivation lineage and all computation dependencies. Rejected candidates remain inspectable alongside immutable observations. [Observation model](../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml) · [Architecture and contracts](https://app.notion.com/p/40d141b58369819eb958e952d47b0301)

The phase-0 policy at the source baseline uses `agent.opus` for claim extraction. Add a CPU policy runnable with general LLM extraction disabled. Reuse the domain-policy and `consolidate_cut` publication boundary. Keep local meanings and qualified source disagreements intact when consolidating occurrences. Apply finite inference over admitted premises with proof witnesses. Review ontology proposals before publishing a new version and replaying affected interpretations. [Phase-0 orchestration](../../python/corpus-structure/src/corpus_structure/orchestrate/phase0.py) · [Statistics policy](../../domains/statistics/policies.yaml)

## Bounded interpretation

Start with value–property–referent–condition, then reuse the contracts for mention identity–type–relation and table header–row identity–cell value–unit–note. Definition and formula records reuse these decisions plus their native source context. Use deterministic joins when keys and premises are established, a fitted independent/stacked baseline for uncertain decisions, and coupled inference where measured gains justify it. GLiNER's local decoder supplies observations and candidates. The outer interpreter owns cross-context source identity, units, qualifiers, scope and whole-record acceptance. [Inference contract](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

Every uncertain decision includes an unresolved alternative and a separate reason such as missing retrieval, conflicting candidates, insufficient context or resource limit. Identity can also resolve to a genuine new/local entity. Record candidate search scope, exclusions and truncation. Apply hard constraints to complete interpretations under established premises. Structural invariants can be hard. Unit/type compatibility is hard only under the meanings selected in the assignment. Typical values and uncertain ontology expectations remain soft or diagnostic.

For a bounded connected component with assignment (z), observations (e) and ontology (O), the proposed conditional model is

```math
P_\theta(z\mid e,O)
= \frac{\exp[\sum_g f_{\theta,g}(z_g,e_g)+\sum_j w_j\psi_j(z_j,O)]\,\mathbf{1}[z\ \text{is feasible}]}{Z_\theta(e,O)}.
```

Evidence potentials group correlated observations. Compatibility potentials connect related decisions. Fit grouped features where supported, or document a conservative feature/representative policy and keep the result provisional. A binary calibrated posterior can supply an LLR by subtracting the matching prior log-odds from the posterior log-odds under matching conditioning assumptions. Candidate-versus-rest scores do not automatically define a coherent multiclass distribution. Shared GLiNER heads, duplicate windows, reused constraints and common OCR errors belong in dependency accounting. The reference prototype's effective-count discount is a heuristic.

Start exact enumeration with a configurable 65,536-state guard plus time and memory limits. Independent components can be solved independently. Over-budget and infeasible results carry explicit dispositions. Approximate splitting and variable elimination require their own justification. Exactness is relative to the declared model and retained candidates. For a whole-record event \(\Phi_r\), sum assignment probabilities over the event rather than multiplying field marginals. Model marginals require held-out evidence to be called calibrated. Keep a small number of coherent alternatives and unresolved mass where the model defines it.

Use proof-bearing deterministic acceptance where applicable and evaluated policy for model-resolved candidates. Under the stated utility assumptions, accepting a record with value \(v_r\) when correct, cost \(c_r\) when wrong and zero utility for abstaining gives threshold \(c_r/(c_r+v_r)\). The illustrative 0.75 is a decision-model example. Select actual thresholds by family with held-out precision/coverage evidence.

### Ambiguous pressure reference

> At a suction pressure of 2 bar, P-101 delivered 120 m³/h; its rated flow was 100 m³/h. Below this pressure, cavitation may occur.

If OCR retains both `2 bar` and `2 h`, resolve the unit, antecedent, value roles and condition scope together. A duration or flow-rate interpretation cannot fill a pressure reference under the specified dimensions. The `bar` reading can satisfy it, and unresolved remains available. Preserve the distinction between delivered and rated flow, and retain **may** and **below this pressure** on the cavitation assertion. The prototype's early hard choice of dimension must be replaced so that a slightly higher raw OCR score for hours cannot eliminate the correct reading before joint interpretation. [Worked inference example](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

### Lineage and corpus support

Derivation lineage tracks premises and rules that establish a result. Computational dependencies include every relevant input to candidate construction and acceptance, including counterevidence and the context consumed by rejected alternatives. Evidence withdrawal recomputes affected components and descendants. Semiring lineage can represent conjunctive and alternative derivations. Probability needs the corresponding event under a probability model.

Keep qualified support/opposition in a ledger with citation groups, source types and known shared origins. Separate author modality, interpretation confidence, source reliability and corpus support. A general mixture likelihood ratio is the ratio of the two mixtures of observation likelihoods, weighted by their respective hypothesis-conditional reading priors. A parser posterior already conditioned on the observation cannot serve as the prior in that mixture. The earlier weighted ratio, uniform correlation discount and latent-truth proposals require separate assumptions and evaluation. Conformal sets, corpus-wide inference, full attribution analysis and learned escalation are later options. [Mathematical assessment](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

## Delivery and exit evidence

| Package | Deliverable and exit evidence |
| --- | --- |
| WP0 | Freeze the source cut, family guidelines, supported subsets, sample denominators and isolated references and splits. |
| WP1 | Shared linguistic and context products with exact alignment on prose, formulas and tables, stable occurrence identities and replay. |
| WP2 | Qualified GLiNER CPU operations and schema registry with actual CPU runs, reproducible caching and explicit empty/infeasible/truncated/failure cases. |
| WP3 | Five record assemblers with a deterministic baseline and complete located candidates on retained sources. |
| WP4 | Three reusable inference templates with dependency, calibration and acceptance evidence, paired comparisons and invalidation/replay. |
| WP5 | Frozen per-family gates, CPU/memory fit, restart/resume, traceable publication, no general LLM extraction and coverage/gap report. |
| WP6 | Ranked source-grounded gaps and bounded CPU experiments with incremental complete-record results, regression and route/adopt/defer decisions. |

The release manifest states supported languages and source types, per-family subsets, all deployment/schema versions, resource bounds, acceptance policy, calibration standing and unsupported cases. Operational cases include Unicode/repeated strings, nested/long spans, formula atoms, table notes, truncation, qualifier retention, changed inputs, retry/idempotence, interruption/resume and atomic publication. Full M1 requires a released supported subset in each core family. [Delivery plan](https://app.notion.com/p/40d141b58369819eb958e952d47b0301) · [Rollout and evaluation](rollout-and-evaluation.md)
