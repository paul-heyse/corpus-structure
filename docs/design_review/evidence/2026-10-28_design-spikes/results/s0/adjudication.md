# S0-D · Adjudication of passes A and B into the reference

**Done:** 2026-10-28 by the root (Claude Opus 5.5), from the aligner's `compare/a_vs_b`
run (after the instrument review's fixes) and `trace_diff.md`. Built by
`code/s0d_reference.py`, which holds the same table; base pass per unit: T1 A, T2 B, T3 A, T4 A, U5 A, U6 B, U7 B, U8 B, U9 A, U10 A, U11 A, U12 A.

Kinds: guideline (v0 decides it) · guideline-gap (v0 does not; the root chose; G1–G5 are
the proposed rules in `trace_diff.md`) · trace-corrected · alternative · unsupported.

| Unit | Id | Kind | Decision | Reason |
|---|---|---|---|---|
| T1 | r1 | guideline-gap | X defined_as: modality `defined`, role `definiens` (A, trace) | G2: "let X = …" inside a definition stipulates the defined construction's variable; B's `supposed` premise reading follows §10.6's "let" literally |
| T1 | r2 | guideline-gap | X defined_as: no `claim` condition on Z's section premise (B, trace) | G3: premise `claim` nodes belong to conclusions (§10.7); a definiens is not one |
| T1 | r3 | guideline-gap | `defines`: modality `asserted` (B, trace) | G4: structural claims are asserted |
| T1 | r4 | trace-corrected | `parameter_role` claims kept (A and B) | §10.3 asks a definition's roles (trace diff d8) |
| T1 | r5 | unsupported | B's three unsupported items replace A's one | B separates the probability space, its components and Z's relation to it; each is an expressible-later fact |
| T2 | r6 | guideline-gap | Statement kind `remark`; identities with role `conclusion` (B, trace) | The paragraph states a result about the parameters; §10.3 gives no remark/narrative criterion |
| T2 | r7 | guideline | No `has_parameter` claims (A and B agree) | §10.3 keeps only explicit claims in remarks; the trace's C2, C3 are not stated as such (trace diff d12, defensible) |
| T3 | r8 | guideline | a + b X defined_as: role `definiens` (A, trace) | §10.3 lists derived variables in theorems; B omitted the role |
| T4 | r9 | guideline-gap | `defines` (LN, standard LN): modality `asserted` (B) | G4 |
| T4 | r10 | guideline-gap | `parameter_role scale` for the scale parameter added (B) | §10.3: the source names the role ("the scale parameter"); kept even though the canonical name says it, as in T1 |
| T4 | r11 | trace-corrected | s5 (standard normal → standard lognormal) annotated (A and B) | The unit includes the second paragraph (trace diff d17) |
| U5 | r12 | guideline-gap | Indexed premise as one claim on X_i with `member(i, {1, 2})`; conclusions `and(claim premise, independent(X_1, X_2))` (A) | B's `forall i ∈ {1, 2}: claim premise` says the same; A's form is the simpler one and is used for U9 and U11 too |
| U6 | r13 | guideline-gap | Two statements: the recalled definition (`remark`) and the corollary (B) | s2 is introduced as "a corollary of the last result"; A's single narrative statement loses the claim-bearing kind |
| U6 | r14 | unsupported | Both unsupported items kept: "standard deviation σ > 0" (A) and "is the standard score of X" (B) | Each records a different gap: the schema has no standard-deviation-value predicate, and no standard-score relation |
| U6 | r15 | guideline-gap | The "last result" is a local Statement stand-in (A and B, B's label) | §10.2 does not say how to cite a statement outside the unit; both annotators made the same stand-in |
| U7 | r16 | guideline-gap | No `refers_to` claims or stand-in statements for the bracketed cross-references (B) | The facts about [14]…[26] are unsupported in both passes; links to statements whose targets are outside the unit add no claim |
| U8 | r17 | unsupported | Means and sds as plain numbers; the unit cm and the setup sentence as unsupported items (B) | A's "1 cm" as a formula would read c·m as symbols; `param_values` cannot carry units (witness_diff limit 1) |
| U9 | r18 | guideline-gap | Indexed premise with `member(i, {1, …, n})`; conclusion with `claim` premise, `n ∈ ℕ₊`, `independent(X_1, X_2, X_n)` and the where-equalities (A) | As r12 |
| U10 | r19 | guideline-gap | `defines`: modality `asserted` (B) | G4 |
| U11 | r20 | guideline-gap | Indexed premise and conclusions in A's form | As r12 |
| T4 | r21 | guideline-gap | `defines`: set to asserted in the A-based batch | G4 (applies r9) |

Counts: guideline 2, guideline-gap 14, trace-corrected 2, unsupported 3.
No difference was kept as an `alternatives` group: none was a reading of the text the
other annotator would reject; all were representational choices the guideline leaves open.
