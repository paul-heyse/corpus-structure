# S0-C · Passes A and B against the worked trace (T1–T4)

**Done:** 2026-10-28, by the root (Claude Opus 5.5), by hand, before adjudication and before the
aligner review finished (no instrument figures here). **Inputs:** the trace's tables
(`docs/design/trace.md` §T1–T4, transcribed as `trace_batches/`), `pass_a/`, `pass_b/` (both Opus 5.5,
blind; transcripts audited: no reads outside their input and output folders), the golden-mode
packets, guideline v0 (`inputs/golden/guideline.md`). Display: `code/s0_show.py`.

**Transcription correction:** in `trace_batches/T4.json`, C7's `param_mapping` held entity refs
(`N.mean`, `N.sd`) where the trace states N's canonical names (`mean`, `standard_deviation`);
corrected and `trace_stored/` regenerated (`code/s0_check.py results/s0/trace_batches --out
results/s0/trace_stored`: passed, 0 issues).

## Summary

A and B agree with each other far more than either agrees with the trace. Of 26 differences, 2
are the trace's (a paragraph of the unit left out, and a capture §10.3 asks for missing), 2 are a pass's, and 22 are
readings the guideline v0 does not decide. Ten of those come from five rules (G1–G5 below), so
the guideline, not the schema, is where T1–T4 disagreement sits. No difference involves a
"must not appear" item: neither pass pairs "respectively" wrongly, gives `b \sigma` as a standard
deviation, makes the location-scale family a `DistributionFamily`, or states a derived fact.

| Classification | Count | Ids |
|---|---|---|
| Trace wrong or incomplete | 2 | d8, d17 |
| Pass wrong | 2 | d6 (B), d15 (B) |
| Both defensible (guideline underspecified) | 22 | the rest |

## Differences

Columns: what the trace has · what A and B have · classification · reason. "Role" is the
`statement_role`; "mod" the modality.

### T1 · location-scale definition

| Id | Item | Trace | A | B | Class | Reason |
|---|---|---|---|---|---|---|
| d1 | Bindings of `a`, `b` in C2, C4 | `free` | `family_param` LSF.loc / LSF.scale | same as A | defensible (G1) | s4 introduces a, b before s6 names them parameters; D1 §6.1 allows either; the guideline does not say which applies when a later sentence names the role |
| d2 | C2 (`X defined_as a + b Z`) mod and role | defined · definiens | defined · definiens | supposed · premise | defensible (G2) | §10.6 says "let" gives `supposed` and a definition's stipulation `defined`; "let X = …" inside a definition is both. Both annotators flagged it |
| d3 | C2 conditions | `and(a∈ℝ, b∈(0,∞))` | adds `claim C1` (Z's section premise) | as trace | defensible (G3) | §10.7 requires premise `claim` nodes on conclusions; C2 is a definiens, which the guideline does not cover |
| d4 | C3 `defines` mod | asserted | defined | asserted | defensible (G4) | §10.6 does not give a modality for structural claims (`defines`, `proves`) |
| d5 | C4 `construction_formula` object | `X = a + b \, Z` | `a + b \, Z` | `a + b \, Z` | defensible (G5) | The schema says "the formula generating members"; whether it includes the generated variable is unstated. Same in d21 |
| d6 | C4 conditions | as C2 | as trace | adds `claim` of its own C2 (a `supposed` definiens) | pass wrong (B) | Conditioning one stipulation on another stipulation of the same definition follows from B's d2 choice but states a dependency the text does not |
| d7 | C5, C6 `has_parameter` role | none | definiens | definiens | defensible | The guideline does not assign roles to structural claims |
| d8 | `parameter_role` claims for a, b | none | location, scale (defined) | same as A | trace wrong | §10.3 asks a definition's parameters with "roles and domains"; redundant with the canonical names, but asked for |
| d9 | C7, C8 `parameter_domain` role | restriction | definiens | definiens | defensible | Both roles exist in `StatementRole`; nothing says which a domain stated in "For a ∈ ℝ …" takes |
| d10 | Probability-space sentences s1–s2 and "defined on the probability space" | not represented (the trace has no column for unsupported items) | 1 `unsupported` | 3 `unsupported` | defensible | §10.3 skips motivation in narrative; the probability space is setup the schema cannot express. The trace is silent, not contrary |

### T2 · normal parameters "respectively"

| Id | Item | Trace | A | B | Class | Reason |
|---|---|---|---|---|---|---|
| d11 | Statement kind | remark | narrative | remark | defensible | The guideline treats remark and narrative alike (§10.3) and gives no criterion between them |
| d12 | C2, C3 `N has_parameter N.loc / N.scale` | present (asserted) | absent | absent | defensible | §10.3 for remarks keeps "only explicit claims"; whether "the normal distribution with location parameter μ" explicitly states `has_parameter` is not decided. Both annotators omitted it |
| d13 | C4, C5 role | conclusion | none | conclusion | defensible | No rule for roles in remarks |

Everything else in T2 is equal, including the section scope of X from "Suppose again" (both
passes, with the trace) and the respectively-pairing.

### T3 · affine transformation of a normal variable

| Id | Item | Trace | A | B | Class | Reason |
|---|---|---|---|---|---|---|
| d14 | Symbol of Y | none (expression in the label) | `a + b X` | `a + b X` | defensible | The model gives `symbol` for local entities without restricting it to single identifiers |
| d15 | C2 role | definiens | definiens | none | pass wrong (B) | §10.3 lists derived variables (`defined_as`) among a theorem's captures; A and the trace give `definiens` |
| d16 | C4 `proves` anchor | no statement | proof statement | proof statement | defensible (G4) | Structural claims have no stated anchor |

T3's claims, conditions (`claim C1`, `a∈ℝ`, `b∈ℝ∖{0}`) and bindings (`param_of`, `param_expr_of`)
are otherwise identical in all three. Both passes correctly omit the trace's D1 (derived standard
deviation), which §10.7 leaves to the pipeline.

### T4 · lognormal definition

| Id | Item | Trace | A | B | Class | Reason |
|---|---|---|---|---|---|---|
| d17 | s5 "If Z has the standard normal distribution then W = e^Z has the standard lognormal distribution" | absent | 4 entities, 5 claims | 4 entities, 6 claims | trace incomplete | The trace quotes the `p.dfn` paragraph and its list; the source's `div.unit#dfn` also holds this second paragraph (`LogNormal.html` line 52), so the unit D1 defines includes it. The old witness treats it as a separate target (`witness_diff.md`) |
| d18 | Restrictions `μ∈ℝ`, `σ∈(0,∞)` | on the premise C1 | on the conclusion C3, with `claim C1` | same as A | defensible (G3) | §10.7's letter puts restrictions on the conclusion; here they are stated inside the premise. Both annotators flagged it |
| d19 | C3 role | conclusion | definiens | definiens | defensible | In a definition the "then" clause is both what is defined and a conclusion |
| d20 | C4 `defines` mod | asserted | defined | asserted | defensible (G4) | As d4 |
| d21 | C7 `transform` | `X = e^Y` | `e^Y` | `e^Y` | defensible (G5) | As d5 |
| d22 | C8–C10 (shape role, scale parameter, `e^\mu`) mod | asserted | defined | defined | defensible (G2) | List items of a definition unit: stipulated or asserted? §10.6 does not say; the passes read the unit kind |
| d23 | `parameter_role scale` for LN.scale | none | none | present | defensible | Redundant with the canonical name; §10.3 "roles" |
| d24 | `parameter_domain` for LN.mu, LN.sigma | none | ℝ, (0,∞) | same as A | defensible | §10.3 asks domains; they come from the premise's restrictions, which §10.7's "no derived facts" may exclude |
| d25 | Entities N.mean, N.sd | declared | not declared | not declared | defensible | Only referenced by `param_mapping`, which uses canonical names; no claim uses them |
| d26 | Labels, local refs, alias forms ("normal" vs "normal distribution") | — | — | — | not a difference | Aligned by D2 §12.1's alias rules |

## Guideline rules the differences point at

| Rule | Ids | Proposed v1 rule |
|---|---|---|
| G1 symbol named as a parameter later in the unit | d1 | Bind `family_param` when the unit names the symbol as the construction's or family's parameter; `free` otherwise |
| G2 modality inside definitions | d2, d22 | Inside a definition unit, "let"/"suppose" before the defined term is `supposed` only for premises about other entities; stipulations about the defined term and its stated properties are `defined` |
| G3 restrictions inside a premise; definiens conditions | d3, d18 | A restriction stated in a premise is a condition of the premise's claim; conclusions reference the premise by `claim`, not by repeating its restrictions |
| G4 structural claims | d4, d16, d20 | `defines` and `proves` are `asserted` and anchored to the defining or proving statement |
| G5 formula with or without the generated variable | d5, d21 | Formula objects and `transform` exclude the left-hand variable (`a + b \, Z`, `e^Y`); the variable is the claim's subject or `base_variable` |

These rules are proposals for the guideline owner (D2 §10); the reference (S0-D) records each
use as a `guideline-gap` decision.
