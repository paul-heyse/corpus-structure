# S5 · Math parsing and verification

**Brief, 2026-10-28.** CPU. Parsing can start after S1; scoping, equivalence and verification
need S0 references.

## Question

How much of Siegrist's LaTeX parses into SymPy with the source's macros, and does the formula
machinery the design depends on work: symbol extraction (M09), rule-based symbol scoping (M13),
formula equivalence for evaluation, condition translation to z3, and the statistics verifiers
(M21) that check claims by algebra and simulation?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D4-3 | SymPy LaTeX backend (lark or ANTLR) and the macro map |
| OPEN-D4-5, OPEN-D1-2 | Does rule-based scoping reach the S0 annotators' scopes? |
| OPEN-D7-2 | Formula equivalence: simplification or numeric sampling, with what timeouts |
| D4 M20 | Can S0 condition trees be translated to z3 and checked? |
| D4 M21 | Do the verifiers confirm true claims and refute corrupted ones? |

## Inputs

- S1 math segments for the four spike pages and the 78 first-pass pages.
- S0 references (formula values, bindings, conditions, scopes).
- [D1 §6–§7](../../../design/D1-knowledge-representation.md#6-values) and
  [D4 M09, M11, M13, M20, M21](../../../design/D4-method-catalog.md#m09-extractmath).

## Procedure

1. **Macro map.** Collect every macro used in math segments of the 78 pages with counts. Pages
   define their macros in a `div.latex` block, which M01 records; compare those definitions with
   the fallback map in D2 §12.1. Define
   expansions for those with mathematical meaning (`\R`, `\N`, `\E`, `\var`, `\cov`, `\P`, `\ms`,
   …) and list the rest.
2. **Parse rates.** Parse every math segment with `parse_latex` under the lark and ANTLR backends,
   with and without the macro map. Record status and a failure class (unknown macro, `\text`,
   alignment environments, set-builder, piecewise, ellipsis, other).
3. **Sets.** Parse the set expressions occurring in conditions (`\R \setminus \{0\}`,
   `(0, \infty)`, `[0, 1]`, `\{1, 2, \ldots, n\}`) into SymPy sets; report what fails.
4. **Symbols (M09).** With pylatexenc, extract symbol occurrences from the core units' math and
   compare with the symbols in S0 formula values (precision and recall of symbols).
5. **Scoping (M13).** Implement D4 M13's binding-site rules in `code/s5_scope.py` over S1
   sentences and M09 symbols. Compare each symbol mention's assigned extent with the S0 scopes
   (local entity scope segments) on the core units and, by inspection, on two sections of the
   Normal page that use "Suppose again".
6. **Equivalence.** Take every pair of formula values that S0 passes A and B wrote differently but
   adjudicated as the same, plus 20 pairs deliberately non-equivalent (perturbed coefficients).
   Test `simplify(a - b) == 0`, `equals`, and numeric evaluation at 20 random points satisfying the
   claims' conditions. Report agreement and time per pair.
7. **z3.** Translate S0 condition trees to z3 (D4 M20 rules). Check satisfiability of each, and
   implication between the conditions of pairs of claims about the same subject. Record
   untranslatable leaves.
8. **Verifiers.** Implement `affine_normal`, `moments` and `simulate` (D4 M21) as scripts. Run
   them on T3 (and its derived standard deviation), U5, U9, U11, U12, and on corrupted copies
   (`a + 2 b \mu`, variance `b \sigma^2`, a gamma sum with different scales, a wrong mean).
   Simulation: 10⁵ samples per point, five parameter points per claim.

## Data to collect

| File | Content |
|---|---|
| `results/s5/macros.tsv` | macro, count, expansion or "unmapped" |
| `results/s5/parse.tsv` | segment key, kind, page, backend, macros on/off, status, failure class |
| `results/s5/sets.tsv` | expression, parsed set, status |
| `results/s5/symbols.tsv` | unit, symbol, in M09, in S0 |
| `results/s5/scope.tsv` | unit, symbol mention, M13 extent, S0 scope, agree |
| `results/s5/equivalence.tsv` | pair, expected, simplify, equals, numeric, ms |
| `results/s5/z3.tsv` | claim, translatable leaves, satisfiable, implications found |
| `results/s5/verify.tsv` | claim (true or corrupted), verifier, verdict, detail |

## How to interpret

| Finding | Reading |
|---|---|
| Parse rate ≥ 90% with macros on one backend | That backend and map are M11's configuration; `OPEN-D4-3` closed |
| Failures concentrated in a few constructs | Pre-normalization rules in M11, listed in the report |
| M13 agrees with S0 on ≥ 90% of symbol mentions | Rule-based scoping is sufficient; `OPEN-D4-5` closed; section extent rule confirmed or corrected (`OPEN-D1-2`) |
| Simplification agrees with numeric sampling and is fast | Simplification first, numeric fallback on timeout; `OPEN-D7-2` closed |
| Corrupted claims refuted and true claims consistent | Verifiers are viable witnesses and confidence sources (D5 §6, D7 §6) |
| Simulation flags true claims as refuted at the chosen thresholds | Tighten thresholds or sample sizes; report the false-alarm rate |

## Report

`S5-report.md` from the [template](report-template.md), giving the M11 configuration, the M13
rules as validated, the equivalence procedure for D7, and verifier outcomes.
