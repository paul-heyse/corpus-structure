---
id: ADR-0039
title: Stream outputs are observations combined by calibrated joint inference
status: proposed
date: 2026-10-31
supersedes: []
superseded-by: null
design: []
evidence: Proposed
revisit: A rollout stage needs a decision whose local template exceeds the exact-inference budget after conformal pruning, or corpus-scale weighted rules are scheduled.
---

## Context

The CPU parser stack planned on the operator's Notion pipeline page adds streams in stages
(layout and tables, syntax and coreference, entity and relation models, condition and argument
models, corpus aggregation, then a CPU LLM for what remains). The operator asked for the outputs
to be combined so their value is "more than a sum of their parts", and for that to hold at every
rollout stage, not only in the finished design. The formalization and staged plan (Claude Docs,
2026-10-31) locate that extra value in four mechanisms: conjunctive assembly, mutual
disambiguation, deductive closure and corpus aggregation. All four need the streams' outputs on
one probability scale, joined by factors that span decisions.

Current implementation: [D5 §5.3](../design/D5-consolidation-identity-confidence.md#53-fusion)
fuses observations per claim, and [§6](../design/D5-consolidation-identity-confidence.md#6-confidence)
estimates claim confidence by a cold-start noisy-OR and, from phase 2, a per-predicate-group
Dawid–Skene network. Both treat a claim's sources as conditionally independent votes on one
claim; neither can let one decision (a unit dimension) change another (which antecedent a
reference denotes). The parsers the later stages need are not in the repository yet, so the
machinery has to be parser-agnostic and testable on its own.

## Options

1. **Extend the §6 noisy-OR / latent-truth model per claim.** Least new code, but it votes on
   finished claims, so it cannot express cross-decision constraints, `UNKNOWN` candidates or
   candidate-set sizing, and stream contributions cannot be separated from their interactions.
2. **A general probabilistic-programming or graphical-model library (pgmpy, a Markov logic or
   PSL engine) from the start.** Strong for corpus-scale weighted rules, but local templates are
   small enough for exact enumeration, the libraries do not provide lineage, conformal sizing,
   value of information or the Shapley/Möbius harness, and adopting one now fixes an engine
   before the corpus-scale stage that would justify it.
3. **A small numpy layer of explicit contracts with exact local inference (selected).** Each
   piece (calibration, decisions, factors, lineage, acceptance, support, harness) has one owner,
   is tested against independent brute-force or textbook results, and can later hand a component
   to a library engine without changing what templates declare.

## Decision

Parser outputs are **observations**, never records. Each decision is typed and offers `UNKNOWN`.
Evidence enters as calibrated LLRs per model, decision type and reliability grade; templates add
compatibility and hard-constraint factors; inference is exact per connected component within a
stated budget and refuses, rather than approximates, beyond it. Records are accepted at
`τ = c / (c + v)` per record type and carry provenance polynomials. Escalation is by expected
value of information per unit CPU cost. Corpus support uses `Λ_g = π_g r_g + (1 − π_g)` with a
correlation-discounted effective count. Stream contributions are measured by `V(S)` over cached
observations, with Möbius dividends, Shapley values and a nested gain decomposition.

The layer is `corpus_structure.interpret`, owned by [D5 §14](../design/D5-consolidation-identity-confidence.md#14-joint-interpretation-of-stream-observations).

## Consequences

- Each rollout stage can be judged by what it adds jointly, not only by its own accuracy; a
  stream whose dividends are all near zero is a candidate for removal.
- The §6.4 latent-truth model keeps its role as the estimator of source reliability `π_g`; its
  pgmpy choice is unchanged.
- Corpus-scale weighted rules (Markov logic, PSL) are not covered and will need their own
  decision when scheduled; that is the revisit trigger.
- Value and cost per record type, the CPU price `λ`, the labelling budget and seed ontology v0
  are open operator inputs; the tests use illustrative values only.
- Remaining work: adopt the layer for one production decision type with calibrators fitted on
  labelled data, then add templates as their parsers arrive. Acceptance would not establish any
  measured gain.
