# Interpretation components

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/b1966ebe48c6421f8ba6dc3d6446d431?pvs=204) · [First production milestone](../first-production-milestone.md)

Prototype statuses and code references reproduce the source register. See the milestone for the contract and runtime
scope proposed for the first deployment.

- [Record-type registry](#notion-40a141b5836981d98f29c170328a3ace)
- [Observation store](#notion-40a141b5836981f7a0d2deb300a375b5)
- [Calibration table](#notion-40a141b5836981989921fdd4f94c578d)
- [Decision registry](#notion-40a141b5836981658472ca2c89f9fe3b)
- [Factor-template library](#notion-40a141b58369816480a2c1c21ed0fd0f)
- [Lineage layer](#notion-40a141b5836981aaaed0e68becf62ffa)
- [Acceptance and escalation](#notion-40a141b5836981e58b7fe0b1125e359f)
- [Corpus support](#notion-40a141b583698168b58bcfd2a9183839)
- [Evaluation harness](#notion-40a141b5836981509450f6bec3fcad70)
- [Seed ontology v0](#notion-40a141b58369812f9465f7037d397d37)

<a id="notion-40a141b5836981d98f29c170328a3ace"></a>

## Record-type registry

**Status** Prototyped · **Order** 1 · [Notion record](https://app.notion.com/p/40a141b5836981d98f29c170328a3ace)

- **Responsibility** — Names each record type the pipeline can accept, with the value v of a correct record and the
  cost c of a wrong one.
- **Contract** — Record type → (required roles, v > 0, c > 0). The threshold is derived, never set by hand. Values
  are policy data, versioned with the run configuration.
- **Mathematics** — τ = c / (c + v). Accepting at posterior p has expected utility p v − (1 − p) c, positive exactly
  when p > τ.
- **Library option** — None needed.
- **Code reference** — `interpret/records.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [What are the value v and error cost c for each record
  type?](design-questions-and-decisions.md#notion-40a141b583698171b1fdd837ef91f2a6)

<a id="notion-40a141b5836981f7a0d2deb300a375b5"></a>

## Observation store

**Status** Prototyped · **Order** 2 · [Notion record](https://app.notion.com/p/40a141b5836981f7a0d2deb300a375b5)

- **Responsibility** — Holds every stream output as an observation, never as a record, and makes cached outputs
  reusable and maskable.
- **Contract** — Observation = (stream, group, model, version, config hash, input digest, document, decision,
  decision type, score kind, alternatives or explicit abstention, reliability grade, correlation group, provenance
  tags). Cache key covers stream, model, version, config hash, input digest and decision. A key names one output; a
  conflicting write is refused. With the PDF front end, the input digest is the PDF digest plus the Docling
  configuration, and spans carry page, bounding box and Docling element reference.
- **Mathematics** — The evidence e. Masking by stream group gives the restricted evidence e\_S used to compute V(S).
- **Library option** — Persist in the project PostgreSQL database once adopted; in-memory for prototypes.
- **Code reference** — `interpret/observations.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [Which Docling signals define the reliability grade q per
  block?](design-questions-and-decisions.md#notion-40a141b5836981b3aff0f76316a42fda), [What is the primary anchor
  for a span: canonical-text offsets or Docling element
  references?](design-questions-and-decisions.md#notion-40a141b5836981778930cbdc26e2b25a), [What happens to
  structure that conversion to PDF
  destroys?](design-questions-and-decisions.md#notion-40a141b5836981de810ef76dc4f8027c), [Model interfaces the
  design relies on were checked but not
  run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae), [Dependent signals make agreement
  look stronger than it is](design-questions-and-decisions.md#notion-40b141b5836981f0b5d8db31b59e34c2), [What schema
  holds conversion-time metadata, and how is each item joined to the Docling elements it
  describes?](design-questions-and-decisions.md#notion-40b141b58369817983f3f8f4951684d1), [An interpretation layer
  chooses readings: observation contract, candidate sets with an unresolved option, bounded joint inference,
  coherent record assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1), [Complete
  cache keys and targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76),
  [Only PDFs enter the pipeline: every source is converted to its published form, rendered to PDF and parsed by
  Docling](design-questions-and-decisions.md#notion-40b141b583698124bc73ee1447273e70)

<a id="notion-40a141b5836981989921fdd4f94c578d"></a>

## Calibration table

**Status** Prototyped · **Order** 3 · [Notion record](https://app.notion.com/p/40a141b5836981989921fdd4f94c578d)

- **Responsibility** — Turns each model's raw score into a log-likelihood ratio, per model, decision type and
  reliability grade.
- **Contract** — Key (model, decision type, grade) → fitted calibrator with its sample and date. An observation
  without a calibrator contributes no evidence and is reported as uncalibrated. Scores already in LLR form pass
  through.
- **Mathematics** — LLR(s) = logit P(z \| s) − logit(base rate of the calibration set). Platt scaling or isotonic
  regression. ECE above 0.05 triggers recalibration.
- **Library option** — scikit-learn IsotonicRegression or CalibratedClassifierCV could replace the hand-written
  fits.
- **Code reference** — `interpret/calibration.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [Is the labelling budget for the stage gates
  realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd), [How does the
  interpretation layer relate to the repository's existing confidence
  design?](design-questions-and-decisions.md#notion-40a141b58369811ca1eff277ad4edd45), [Which Docling signals define
  the reliability grade q per block?](design-questions-and-decisions.md#notion-40a141b5836981b3aff0f76316a42fda),
  [When does a shared-error model (Pyro) earn its
  place?](design-questions-and-decisions.md#notion-40a141b5836981d498a6c47dc7105a8a), [Dependent signals make
  agreement look stronger than it is](design-questions-and-decisions.md#notion-40b141b5836981f0b5d8db31b59e34c2),
  [What does the front end do when rendering fails, or when Docling fails or only partly
  succeeds?](design-questions-and-decisions.md#notion-40b141b583698101b5d1d1017d9ad33f), [Text quality:
  ocr-error-detection removed, replaced by a feature-based quality
  score](design-questions-and-decisions.md#notion-40b141b5836981679924dd95780edee3), [The qualified claim carries
  four separate kinds of confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e),
  [Only PDFs enter the pipeline: every source is converted to its published form, rendered to PDF and parsed by
  Docling](design-questions-and-decisions.md#notion-40b141b583698124bc73ee1447273e70)

<a id="notion-40a141b5836981658472ca2c89f9fe3b"></a>

## Decision registry

**Status** Prototyped · **Order** 4 · [Notion record](https://app.notion.com/p/40a141b5836981658472ca2c89f9fe3b)

- **Responsibility** — Declares each decision variable, its candidate set and the UNKNOWN option, and sizes
  candidate sets so candidate recall is a stated guarantee.
- **Contract** — Decision = (id, type, candidates, UNKNOWN). A record on an UNKNOWN outcome is never accepted.
  Candidate sets come from a generator filtered by a split-conformal threshold fitted per decision type.
- **Mathematics** — Nonconformity s = 1 − p(y \| x); q̂ = the ⌈(n+1)(1−α)⌉ / n quantile on labelled decisions;
  C\_α(x) = \{y : s(x, y) ≤ q̂\} contains the true option with probability ≥ 1 − α.
- **Library option** — MAPIE (already in the stack) for conformal sets.
- **Code reference** — `interpret/decisions.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [How should conformal candidate sets handle shift between document
  families?](design-questions-and-decisions.md#notion-40b141b5836981f4a673f85b47ee66e7), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [An
  interpretation layer chooses readings: observation contract, candidate sets with an unresolved option, bounded
  joint inference, coherent record
  assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1)

<a id="notion-40a141b58369816480a2c1c21ed0fd0f"></a>

## Factor-template library

**Status** Prototyped · **Order** 5 · [Notion record](https://app.notion.com/p/40a141b58369816480a2c1c21ed0fd0f)

- **Responsibility** — Builds and solves the local factor graph for each template instance, exactly, within a size
  budget.
- **Contract** — Variables with finite domains; log-space factors; hard constraints at −∞. Inference per connected
  component; a component above the budget (default 65,536 joint states) is refused, never approximated. Returns
  marginals, the joint MAP assignment and event probabilities.
- **Mathematics** — log P(z \| e, O) = Σ w\_a f\_a(z, e) + Σ u\_b g\_b(z, O) − log Z. Synergy lives only in factors
  spanning two or more decisions.
- **Library option** — pgmpy (named in the pipeline page) for variable elimination and junction trees; the prototype
  uses its own exact enumeration. See design questions.
- **Code reference** — `interpret/factors.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [Should templates use pgmpy or the prototype's own exact
  solver?](design-questions-and-decisions.md#notion-40a141b5836981689075d6d5d126d651), [Should the reference code be
  merged into the repository now?](design-questions-and-decisions.md#notion-40a141b583698157bd13c80f5b84f768),
  [Which method handles corpus-level coupling: probabilistic soft logic or Markov
  logic?](design-questions-and-decisions.md#notion-40b141b5836981fe87ddf60ddd1995e2), [Conditions rest on thin
  evidence](design-questions-and-decisions.md#notion-40b141b5836981ae9becc156c7c8ccff), [Bridging and abstract
  reference are unsolved in general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be),
  [Joint inference cost grows with template
  connectivity](design-questions-and-decisions.md#notion-40b141b5836981509d4de742300851e4), [Ontology expectations
  can coerce readings into existing
  categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020), [Conditions get an
  explicit route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit
  conditions](design-questions-and-decisions.md#notion-40b141b58369813196e2f5470bb81336), [An interpretation layer
  chooses readings: observation contract, candidate sets with an unresolved option, bounded joint inference,
  coherent record assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1)

<a id="notion-40a141b5836981aaaed0e68becf62ffa"></a>

## Lineage layer

**Status** Prototyped · **Order** 6 · [Notion record](https://app.notion.com/p/40a141b5836981aaaed0e68becf62ffa)

- **Responsibility** — Attaches a provenance polynomial to every derived record and evaluates it for validity,
  derivation count, best derivation, witnesses and probability.
- **Contract** — Polynomial in N\[X\] over observation, decision and rule variables. Join multiplies, alternative
  derivations add. Withdrawing an input sets its variable to 0; a record whose polynomial becomes 0 is invalidated.
- **Mathematics** — Boolean, counting, Viterbi and why-provenance semirings. Exact probability by Shannon expansion
  for independent variables, or from the factor posterior when correlated. Fréchet bounds when only marginals are
  known.
- **Library option** — No mature Python library; ProvSQL offers the same model inside PostgreSQL if lineage moves
  into the database.
- **Code reference** — `interpret/lineage.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [What is the primary anchor for a span: canonical-text offsets or Docling element
  references?](design-questions-and-decisions.md#notion-40a141b5836981778930cbdc26e2b25a), [Complete cache keys and
  targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76)

<a id="notion-40a141b5836981e58b7fe0b1125e359f"></a>

## Acceptance and escalation

**Status** Prototyped · **Order** 7 · [Notion record](https://app.notion.com/p/40a141b5836981e58b7fe0b1125e359f)

- **Responsibility** — Accepts records at their threshold and chooses further observations by value of information
  per unit cost.
- **Contract** — Accept iff p ≥ τ. An escalation (another parser, region re-conversion, CPU LLM, human check) is
  requested only when EVI > λ × cost; best ratio first; at most one action per decision.
- **Mathematics** — EU = max(0, p v − (1 − p) c). EVI(a) = E\_o\[max\_d EU(d \| e, o)\] − max\_d EU(d \| e) ≥ 0.
- **Library option** — None needed.
- **Code reference** — `interpret/acceptance.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [What is λ, the CPU-seconds worth one extra correct
  record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8), [Bridging and abstract
  reference are unsolved in general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be),
  [How are inline formulas drawn as vector paths
  recovered?](design-questions-and-decisions.md#notion-40b141b583698173a9cac652a89744dc), [Bridging and abstract
  anaphora go to the CPU LLM with candidate antecedents and a none
  option](design-questions-and-decisions.md#notion-40b141b5836981ed83b0c876eff6dc0e), [Which heavier reader re-reads
  pages that Docling grades low?](design-questions-and-decisions.md#notion-40b141b583698146965ffce689a21969), [An
  interpretation layer chooses readings: observation contract, candidate sets with an unresolved option, bounded
  joint inference, coherent record
  assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1), [Generative calls stay off
  until the stage-5 baseline is measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612)

<a id="notion-40a141b583698168b58bcfd2a9183839"></a>

## Corpus support

**Status** Prototyped · **Order** 8 · [Notion record](https://app.notion.com/p/40a141b583698168b58bcfd2a9183839)

- **Responsibility** — Combines evidence for one claim across sources without counting copies of one origin more
  than once.
- **Contract** — Sources grouped into provenance clusters; each with reliability π\_g and likelihood ratio r\_g;
  discount within clusters by ρ; clusters independent of each other.
- **Mathematics** — Λ\_g = π\_g r\_g + (1 − π\_g); k\_eff = k / (1 + (k − 1)ρ); log-odds = prior + (k\_eff / k) Σ
  log Λ\_g.
- **Library option** — Crowd-Kit or pgmpy Dawid–Skene to estimate π\_g.
- **Code reference** — `interpret/support.py`
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Questions** — [How does the interpretation layer relate to the repository's existing confidence
  design?](design-questions-and-decisions.md#notion-40a141b58369811ca1eff277ad4edd45), [Which method handles
  corpus-level coupling: probabilistic soft logic or Markov
  logic?](design-questions-and-decisions.md#notion-40b141b5836981fe87ddf60ddd1995e2), [How is the residual
  correlation ρ between provenance groups set before it is
  measured?](design-questions-and-decisions.md#notion-40b141b5836981468d31ce8deb070e18), [Do the corpus-support
  parameters in the reference code mean what the derivation
  defines?](design-questions-and-decisions.md#notion-40b141b5836981d794fafbde9626cc97), [Dependent signals make
  agreement look stronger than it is](design-questions-and-decisions.md#notion-40b141b5836981f0b5d8db31b59e34c2),
  [The qualified claim carries four separate kinds of
  confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e), [Provenance groups replace
  assumed independence in corpus support
  (7.5)](design-questions-and-decisions.md#notion-40b141b58369814fab5de71fe2849af1)

<a id="notion-40a141b5836981509450f6bec3fcad70"></a>

## Evaluation harness

**Status** Prototyped · **Order** 9 · [Notion record](https://app.notion.com/p/40a141b5836981509450f6bec3fcad70)

- **Responsibility** — Measures what each stream group contributes and what only groups together contribute, on the
  same frozen sample at every stage.
- **Contract** — V(S) = realized utility of records accepted with only groups S present, computed over cached
  observations. Up to 12 groups by exact enumeration. Intervals by resampling documents.
- **Mathematics** — Möbius dividends d(T) = Σ\_\{S⊆T\} (−1)\^\{\|T\|−\|S\|\} V(S); Shapley values; Shapley
  interaction index; nested gain decomposition (assembly and closure, disambiguation, coverage); cluster bootstrap.
- **Library option** — ppi\_py for corpus-wide estimates from an audit sample.
- **Code reference** — `interpret/harness.py`
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [Is the labelling budget for the stage gates
  realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd), [Errors compound along
  long chains of combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda),
  [Candidate recall bounds every joint
  decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [The central hypothesis is
  tested first on three prototypes with generative calls disabled, against six
  baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a), [Generative calls stay off
  until the stage-5 baseline is measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612)

<a id="notion-40a141b58369812f9465f7037d397d37"></a>

## Seed ontology v0

**Status** Idea · **Order** 10 · [Notion record](https://app.notion.com/p/40a141b58369812f9465f7037d397d37)

- **Responsibility** — Supplies O to every factor: concepts, known entities, hierarchy, relation signatures, frame
  roles and unit dimensions.
- **Contract** — Versioned; its version is part of every cache key it affects. Tier 8 only proposes changes;
  accepting them creates v1.
- **Mathematics** — Compatibility factors g\_b(z, O) and hard constraints.
- **Library option** — Not chosen yet (see design questions).
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Questions** — [Which ontology becomes seed ontology v0, and in what
  format?](design-questions-and-decisions.md#notion-40a141b5836981a68cf6f8e9e81ff8ed), [Ontology expectations can
  coerce readings into existing
  categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020), [The versioned seed
  ontology is an input from tier 1; tier 8 only proposes reviewed
  changes](design-questions-and-decisions.md#notion-40b141b5836981cfb1fef9641df32bed)
