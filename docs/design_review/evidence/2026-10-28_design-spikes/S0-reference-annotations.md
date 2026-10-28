# S0 · Reference annotations

**Brief, 2026-10-28.** Run after S1 has produced canonical text for the spike pages, or start on
the raw page text and re-anchor offsets when S1 lands. Needs Opus; no GPU.

## Question

Can the claim model of [D1](../../../design/D1-knowledge-representation.md) and the statistics
schema and guideline v0 of [D2 §9–§10](../../../design/D2-schema-and-guidelines.md#9-statistics-schema-v0)
express what the core units state, and is the result determinate: do two independent annotators
following the same guideline produce the same claims?

It also produces the **reference annotations** that S2 and S3 compare GLiNER2 and the local LLM
against. These are spike references, not goldens: goldens are produced later under the D7
protocol.

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D1-2 | Do variable scopes need a `section` extent, or does statement scope plus "Suppose again" resolution suffice? |
| OPEN-D1-3 | Should `FamilyParameter` identity use role names or source symbols when no role is stated? |
| OPEN-D1-4 | Is `section` the right extent for page-level standing assumptions? |
| OPEN-D2-4 | Separate property predicates (`mean_value`, `pdf`, …) or one `has_property` with a qualifier? |
| OPEN-D2-5 | "Standard normal": a family with `special_case_of`, or a parameterization of the normal family? |

and, more broadly, which facts in the core units the schema cannot state (`unsupported` items)
and where the guideline is ambiguous.

## Inputs

- The twelve core units and their offsets (`sample.json` from S1), or the raw page text.
- D1 §1–§11 (not §12), D2 §9 (schema v0) and §10 (guideline v0).
- The output format `ClaimProposalBatch` of D2 §7.3. The compiled JSON Schema does not exist
  yet; follow the field list by hand.

## Procedure

1. **Two blind passes.** Use two fresh subagents, A and B. Give each only: the guideline (D2
   §10), the schema (D2 §9), D1 §1–§11, the output format (D2 §7.3) and the source text of the
   units with their offsets. **Neither may read [trace.md](../../../design/trace.md), D1 §12 or
   the other's output.** Each annotates all twelve core units and writes one batch per unit.
2. **Compare with the trace.** For T1–T4, compare each pass with the trace's target tables. List
   every difference and classify it: the trace is wrong, the pass is wrong, or both readings are
   defensible (the guideline is underspecified).
3. **Compare A with B.** For every unit, align the two passes: entities by type and label or
   symbol, claims by predicate, aligned subject and object, and canonical value. Count agreement
   at three tiers: core (subject, predicate, object), full (plus qualifiers and conditions),
   evidence (plus overlapping primary spans). A short script in `code/s0_compare.py` may do the
   counting; judgement on equivalent formulas may be manual.
4. **Adjudicate.** As root, resolve each A/B difference into one adjudicated batch per unit with
   a one-line reason for each decision. These adjudicated batches are the S0 reference.
5. **Collect gaps.** Gather every `unsupported` item from both passes and every point where an
   annotator had to guess, and group them: schema gap (a predicate, class or qualifier is
   missing), guideline gap (the rule is unclear), representation gap (D1 cannot express it).
6. **Answer the OPEN questions** above, each with the units and spans that decided it.
7. **Size.** Record the output size per unit (characters and approximate tokens) for each pass.
   This sizes the work packets of D8.

## Data to collect

| File | Content |
|---|---|
| `results/s0/pass_a/<unit>.json`, `results/s0/pass_b/<unit>.json` | The two blind batches |
| `results/s0/reference/<unit>.json` | Adjudicated reference batches, with decision reasons |
| `results/s0/agreement.tsv` | Unit × predicate × tier: A count, B count, agreed |
| `results/s0/trace_diff.md` | T1–T4: pass versus trace differences and their classification |
| `results/s0/gaps.md` | Schema, guideline and representation gaps, each with its units and quotes |
| `results/s0/size.tsv` | Unit × pass: characters, approximate tokens, claims |

## How to interpret

| Finding | Reading |
|---|---|
| Core-tier agreement is high and full-tier much lower | Entities and predicates are determinate; qualifiers, conditions or bindings are not. Tighten the guideline rule involved, not the schema |
| Disagreement concentrated in one predicate | Its description or guideline rule is ambiguous; propose a rewrite |
| Many `unsupported` items of one kind | A schema gap; propose the class or predicate, with examples |
| Annotators disagree on scope or parameter identity | Decides `OPEN-D1-2/3/4` |
| The trace is wrong on some point | Report it; the design owner corrects the trace |
| Batches are large for dense units | Sizes D8 work packets; may argue for sentence-level packets |

## Report

`S0-report.md` from the [template](report-template.md). Its "Design implications" section lists
proposed changes to D1, the D2 schema and the guideline, each with its evidence, and answers the
OPEN questions above.
