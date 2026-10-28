# S5 · Math parsing and verification

**Brief, 2026-10-28; revised after S0, S1 and S0-R2.** CPU. Ready: S1 has the math spans and
per-rendition macro tables, S0 built the math grammar (ADR-0009) and the M13 binder patterns, and
S0-R2 has the v1 reference.

## Question

How much of Siegrist's LaTeX does the one math grammar of ADR-0009 (`code/mathgrammar/`: SymPy's
shipped `latex.lark` extended, with terminals from each rendition's macro table) read, and where
does it fail? Is the canonical form that keys use independent of parse success, as D1 §6.2
requires? Does the formula machinery the design depends on work: symbol extraction (M09),
rule-based symbol scoping (M13), formula equivalence for evaluation, condition translation to z3,
and the statistics verifiers (M21) that check claims by algebra and simulation?

## Design questions it answers

| Id | Question |
|---|---|
| ADR-0009, D4 M09, M11 | Grammar coverage on the whole first pass, by failure and ambiguity category; which extensions to add |
| D1 §6.2 (B1) | Keys use the token canonical form for every value; does the tree printer agree with it wherever a value parses? |
| OPEN-D4-3 | Revisit check only: does SymPy's ANTLR backend read what the Lark grammar fails on? |
| OPEN-D4-5, OPEN-D1-2 | Does rule-based scoping reach the annotators' scopes beyond the core units? |
| OPEN-D7-2 | Formula equivalence: which tiers decide which pairs, with what timeouts |
| D4 M20 | Can reference condition trees be translated to z3 and checked? |
| D4 M21 | Do the verifiers confirm true claims and refute corrupted ones? |

## Inputs

- **Math spans.** All 28,956 math spans of the 78 first-pass pages (S1-D, record
  [s1.corpus](records/s1.corpus.json)): 28,948 delimited `ok` and 8 `partial`, the source's
  unbalanced delimiters. Segments of the four spike pages are in `results/s1/segments/`; the other
  pages' renditions come from `s1_adapter.adapt`, as `code/mathgrammar/coverage.py` does.
- **Renditions.** M01 may produce renditions with html5lib (D4 M01). S0 and S1 used libxml2; on the
  seven pages S0 and S0-R2 use the two are content-identical and only keys differ
  ([s1.rendition-identity](records/s1.rendition-identity.json));
  take renditions and offsets from `sample.json` and `results/s0r2/sample.json` as they stand,
  record the parser used for the other pages, and report the span count against S1's.
- **Macro tables.** Each rendition's own table (`parse_detail.macros`; S1 `results/s1/macros.tsv`),
  with the D2 §12.1 map only as fallback: bodies differ between pages for the same name (HTML-06).
- **Grammar.** `code/mathgrammar/` (`api.py`: `parse`, `canonical`, `occurrences`, `to_sympy`;
  `printer.py`: `tree_canonical`, `tokens_canonical`) and its coverage record on a 1,532-span sample
  (`results/mathgrammar/README.md`: 976 `ok`, 256 `ambiguous`, 1 `partial`, 299 `failed`, with
  categories).
- **References.** The v1 reference, `results/s0r2/reference_v1/` (formula values, bindings,
  conditions, scopes), and the v0 reference `results/s0/reference/`.
- **Value pairs.** The aligned batches of S0 (`results/s0/compare/`) and S0-R2
  (`results/s0r2/compare/`), and the root's manual decisions (`results/s0/manual_equivalence.tsv`).
- **Scoping.** `code/m13_binders.py` (binder patterns from the D2 §12.1 lexicon) and
  `code/s0e_m13_probe.py`, which reproduces 20 of 20 reference scopes on the core units with the
  paragraph-statement rule (record [s0.m13-probe-2](records/s0.m13-probe-2.json)).
- The equivalence instruments `code/instruments/values.py` (tiers `canonical`, `sympy`,
  `numeric`, `manual`).
- [D1 §3.1, §6–§7](../../../design/D1-knowledge-representation.md#6-values) and
  [D4 M09, M11, M13, M20, M21](../../../design/D4-method-catalog.md#m09-extractmath).

## Two statuses, kept apart

A math segment's `parse_status` comes only from delimiting: it is `partial` for the 8 unbalanced
delimiters and `ok` otherwise. Whether the grammar reads a span (`ok`, `ambiguous`, `failed`) is
a separate measured figure, grammar coverage (D1 §3.1), and never changes a segment's status or
any key.

## Procedure

1. **Macro tables.** Collect every macro used in math spans of the 78 pages with counts; mark
   which come from the rendition's own table and which from the fallback; list those with no
   expansion and those whose bodies differ between pages.
2. **Grammar coverage.** Parse all 28,956 spans with `code/mathgrammar/` under `any_value`, with
   each rendition's macro table. Record status, detected kind, failure category (the categories
   of `results/mathgrammar/README.md`: unexpected-token, environment, punctuation-or-list,
   unknown-command, limit-arrow, text-in-math, unsupported-relation, incomplete) and ambiguity
   cause (undeclared application or product, bare interval or pair, operator scope). List the 8
   partial spans with their delimiting reason and what the grammar does with them.
3. **Extensions.** Where failures concentrate, extend `extension.lark` (for example `cases` and
   `align` rows, evaluation bars, `\to` in subscripts) and re-measure on all spans. Report each
   extension with the spans it gains and any it breaks. Stop when the remaining failures are
   spread over rare constructs.
4. **ANTLR revisit check (`OPEN-D4-3`).** On the spans the Lark grammar still fails on, try
   SymPy's ANTLR backend with the same macro expansion. Report only how many it reads that Lark
   does not, and which constructs; this decides whether the revisit trigger fires.
5. **Canonical form for keys (B1).** Keys use the token canonical form (`tokens_canonical`) for
   every value: it is total, needs only the rendition's macro table and never depends on parse
   success. The tree serves validation, slot typing, SymPy conversion and equivalence. Make the
   token normalization drop sizing commands (`\big`, `\Big`, `\bigg`, `\Bigg` and their `l`, `r`
   and `m` variants), as the tree printer already ignores them: on the spike pages 4 of 881
   parsed spans differ between the tree and token forms, all at `\big/`. Then run the property
   check over all 28,956 spans: on every span the grammar reads, `tree_canonical` equals
   `tokens_canonical`. List each disagreement with its cause; where they cannot agree, the token
   form wins and the tree printer is the one to change.
6. **Sets.** Parse the set expressions occurring in reference conditions (`\R \setminus \{0\}`,
   `(0, \infty)`, `[0, 1]`, `\{1, 2, \ldots, n\}`) into SymPy sets; report what fails.
7. **Symbols (M09).** With the grammar's `occurrences`, extract symbol occurrences from the core
   and held-out units' math and compare with the symbols in the v1 reference's formula values and
   bindings (precision and recall of symbols).
8. **Scoping (M13).** Run `code/m13_binders.py` over S1 sentences and M09 symbols. Confirm that it
   still reproduces the 20 of 20 scopes on the core units, and report its agreement with the
   v1 reference's scopes. Then run it on math-heavy units: the six held-out units (compare with
   passes SV and HV, `results/s0r2/stored/`) and twenty units from the 78 pages with the highest math share (S1 `results/s1/sizes.tsv`; judge a sample of
   assignments by inspection), and on two sections of the Normal page that use "Suppose again".
   Report each disagreement by cause (missing binder, wrong extent, symbol bound inside the
   formula).
9. **Equivalence.** Take every pair of aligned formula or set values written differently in S0
   (A against B, each pass against the reference) and S0-R2 (SV against HV, each against the v1
   reference), with the expected answer from the adjudication, the reference or the manual
   decisions; add 20 deliberately non-equivalent pairs (perturbed coefficients). Run the
   instruments' tiers in order and record which tier decides each pair, its answer and its time;
   also test `simplify(a - b) == 0`, `equals`, and numeric evaluation at 20 random points
   satisfying the claims' conditions directly. Report agreement and time per pair.
10. **z3.** Translate the v1 reference's condition trees to z3 (D4 M20 rules). Check
    satisfiability of each, and implication between the conditions of pairs of claims about the
    same subject. Record untranslatable leaves.
11. **Verifiers.** Implement `affine_normal`, `moments` and `simulate` (D4 M21) as scripts. Run
    them on T3 (and its derived standard deviation), U5, U9, U11, U12, and on corrupted copies
    (`a + 2 b \mu`, variance `b \sigma^2`, a gamma sum with different scales, a wrong mean).
    Simulation: 10⁵ samples per point, five parameter points per claim.

## Data to collect

| File | Content |
|---|---|
| `results/s5/macros.tsv` | macro, count, source (rendition table or fallback), expansion or "unmapped", differing bodies |
| `results/s5/parse.tsv` | span (segment key, offsets), kind, page, delimiting status, grammar status, detected kind, failure category or ambiguity cause, ms |
| `results/s5/coverage.md` | Coverage by status and category before and after each extension; the 8 partial spans |
| `results/s5/antlr.tsv` | span failed under Lark, ANTLR result |
| `results/s5/canonical.tsv` | span, `tokens_canonical`, `tree_canonical`, agree, cause |
| `results/s5/sets.tsv` | expression, parsed set, status |
| `results/s5/symbols.tsv` | unit, symbol, in M09, in the reference |
| `results/s5/scope.tsv` | unit, symbol mention, M13 extent, reference or pass scope, agree, cause |
| `results/s5/equivalence.tsv` | pair, source, expected, deciding tier, answer, simplify, equals, numeric, ms |
| `results/s5/z3.tsv` | claim, translatable leaves, satisfiable, implications found |
| `results/s5/verify.tsv` | claim (true or corrupted), verifier, verdict, detail |

## How to interpret

| Finding | Reading |
|---|---|
| Grammar reads ≥ 90% of spans with the rendition macro tables | That grammar and those tables are M11's configuration; ADR-0009 confirmed |
| Failures concentrated in a few constructs | Grammar extensions for M11, listed in the report |
| ANTLR reads few spans Lark fails on | `OPEN-D4-3` stays closed on Lark; no revisit |
| Tree and token forms agree on every parsed span after the sizing-command rule | Token form for keys confirmed (D1 §6.2, ADR-0009 amendment); the property test becomes a P0 test |
| Disagreements remain in some constructs | Each is a token-normalization rule or a tree-printer fix, listed; keys still use the token form |
| M13 agrees with the reference and the passes on ≥ 90% of symbol mentions in math-heavy units | Rule-based scoping is sufficient; `OPEN-D4-5` closed; section extent rule confirmed or corrected (`OPEN-D1-2`) |
| The cheap tiers decide most pairs and agree with the expected answers | Tier order as in the instruments; `OPEN-D7-2` closed with the timeouts measured |
| Corrupted claims refuted and true claims consistent | Verifiers are viable witnesses and confidence sources (D5 §6, D7 §6) |
| Simulation flags true claims as refuted at the chosen thresholds | Tighten thresholds or sample sizes; report the false-alarm rate |

## Report

`S5-report.md` from the [template](report-template.md), giving grammar coverage with its
categories, the grammar extensions, the token canonical form with the sizing-command rule and the
property-check result, the M13 rules as validated, the equivalence procedure for D7, and verifier
outcomes.
