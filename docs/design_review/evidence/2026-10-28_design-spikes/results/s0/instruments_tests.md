# Comparison instruments: test record (I-A, I-B)

**2026-10-28.** Implements packages I-A and I-B of
[comparison-instruments.md](../../../../../plans/design-spikes-s0-s1/comparison-instruments.md)
(§2–§9) against D1 §6–§7, §10–§11, D2 §6, §7.3, §9, §12.1, D4 §4.3, D5 §5.2, §5.6 and D7 §5.
Baseline: HEAD `60ac9e5`; review fixes on `249b0c2`; instruments revisit I-R1 (one math grammar,
new quote cascade; ADR-0009, proposed) on `3e2ae5b` (all 2026-10-28). Spike env: Python 3.14.10,
pydantic 2.14.1, linkml-runtime 1.12.1, pint 0.26.2, rapidfuzz 3.14.6, regex 2026.9.29, scipy
1.18.1, statsmodels 0.15.0, sympy 1.14.0 + lark 1.3.1 (pylatexenc is not used by the
instruments). Claims below are **Tested** on synthetic and S1 text unless marked.

## Result

| Command (from `code/tests_instruments/`) | Outcome |
|---|---|
| `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python run_all.py --logs` | **passed**: 75 tests (41 invalid-batch cases, 21 planted locator cases, 8 cascade kinds and the probe reproduction run as subtests), exit 0, 2026-10-28, after I-R1 (earlier runs: 40, then 50 tests after the review fixes, passed) |
| `… uv run python -m unittest test_locate_real` (S1 canonical text, `provisional` sentences) | **passed**: 11 real-text cases, 2026-10-28 (rerun after I-R1) |
| `… uv run python code/mathgrammar/coverage.py --per-page 10` (from the evidence folder) | **passed** (ran to completion): figures in "Math grammar" below and `results/mathgrammar/` |
| Reviewer probes `e1`, `sym` rerun after I-R1 | **passed**: `e1` 6/6 at all tiers, bindings 12/12; `sym` symmetric on all 12 units |
| The 10 review regression tests (`test_align.TestReviewFindings`, `test_values.TestTiers.test_f*`) against the pre-fix instruments of `de5bd4c` (copied to a scratch tree) | **failed** as intended: 17 failures, 3 errors; every new test discriminates |
| Reviewer probes `e1` (both orders, `diff_ev`), `e2`, `e3`, `sym`, `keysreal`, `ents trace|ab`, `run_real trace_a|a_b` on the real trace and pass batches | **passed**: no exceptions; `e1` 6/6 at all tiers, bindings 12/12; `sym` symmetric on all 12 units. No agreement figures computed or reported here |
| `… uv run python ../s0_locate.py t3.json --context ctx.json --out … --report …` (CLI smoke, scratch files) | **passed**: 5 quotes tier 1, envelope carried, scope segments set |

Done-when, I-A: every deliberately invalid batch is reported in its category (exclusively in it,
except "unknown entity class", which also, correctly, yields type mismatches on the claims using
the class); every planted quote is at its hand-written span or expected-unlocated; stored-form
conversion resolves `extent` → `scope_segment` through caller-supplied `section_of` and
`statement_scope` lookups. I-B: value tiers 1–4 with the deciding tier recorded; entity and
claim alignment incl. alternatives and unsupported; D7 §5.4 scores with bootstrap intervals,
binding and scope accuracy, unsupported recall, kappa; claim and meaning keys with mismatch
causes; the §9 perturbation suite passes with the expected outcomes.

## Files

All under `docs/design_review/evidence/2026-10-28_design-spikes/`:

| File | Content |
|---|---|
| `code/schema/core.yaml`, `code/schema/statistics.yaml` | D2 §6 and §9 copied verbatim (unedited; see S4 observations) |
| `code/instruments/batch.py` | Pydantic models, both forms; envelope; `load_batch`, `wrap` |
| `code/instruments/schema_lookup.py` | `SchemaLookup` over `SchemaView` |
| `code/instruments/validate.py` | `validate_batch` |
| `code/s0_locate.py` | Quote locator, stored-form conversion, re-anchoring, CLI |
| `code/mathgrammar/` | The math reader (ADR-0009): `extension.lark` (our additions to SymPy's grammar), `build.py` (assembly, macro classification, parser cache), `api.py` (parse, ambiguity, occurrences), `printer.py` (canonical form), `to_sympy.py` (transformer subclass), `coverage.py` (coverage record) |
| `code/instruments/values.py` | Canonical forms and tier-2 values from the math grammar; tiered `ValueComparator`; `PARSE_LOG` |
| `code/instruments/conditions.py` | Condition canonicalization and equivalence (shared by keys and align) |
| `code/instruments/align.py` | `align_unit`, `describe` |
| `code/instruments/scores.py` | P/R/F1, bootstrap, agreement rows, binding/scope accuracy, kappa, key agreement, symmetrization |
| `code/instruments/keys.py` | `compute_keys`, `mismatch_causes` |
| `code/tests_instruments/` | `fixtures.py` (synthetic T2/T3 text and batches), `test_validate.py`, `test_locate.py`, `test_locate_real.py` + `real_text_cases.py` (**coordinator hook**), `test_locate_cascade.py` (regex-probe perturbation kinds and figure reproduction), `test_mathgrammar.py`, `test_values.py`, `test_align.py`, `run_all.py` |
| `results/mathgrammar/` | Coverage record: `summary.json`, `values.tsv` (S0 values), `spans.tsv` (corpus sample), `README.md` |

## Public functions the coordinator calls

```python
from instruments.batch import load_batch, wrap                 # (envelope|None, batch) / enveloped dict
from instruments.validate import validate_batch                # -> ValidationReport (.ok .issues .categories() .counts() .lines() .conditional_claims)
validate_batch(raw, lookup=None, form="model"|"stored", *, canonical_text=None, sentence_ids=None, unit_ranges=None,
               macros=None)                                     # page macros for the slot-kind check; .notes lists unread values

from s0_locate import UnitContext, locate_quote, to_stored, reanchor
UnitContext(text, unit_ranges, sentences={sid: (start, end)}, unit_keys=[], sentence_keys={sid: key},
            section_of=None,        # offset -> section segment key (S1's adopted synthesis)
            statement_scope=None,   # [anchor segment keys] -> one scope segment key (default: the single key)
            document_key=None,
            macros=None)            # page parse_detail.macros for the macro step (D2 §12.1 fallback beneath)
locate_quote(quote, sentence_id, ctx) -> Located(start, end, tier, scope, matches, score, long_quote, coarse, dropped, note,
                                                 step, fuzzy_counts, ms)
to_stored(model_batch, ctx) -> (stored_batch, LocateReport)    # .by_tier() .ambiguous() .unlocated() .problems .as_json()
reanchor(stored_batch, old_text, new_ctx) -> (stored_batch, failed_spans)

from instruments.values import ValueComparator, canonical_latex, canonical_value, PARSE_LOG
cmp = ValueComparator.with_manual_tsv("results/s0/manual_equivalence.tsv", macros=page_macros)  # TSV: kind a b decision reason
cmp.compare(va, vb, conds=(), ref_eq=None) -> Equivalence(equal, tier, kind, a, b, detail, grammar); cmp.tally(); cmp.pending_tsv()

from instruments.align import Side, align_unit, describe
align_unit(Side(ref_stored, segment_spans={key: (s, e)}, sentences=[(s, e), ...], unit=...),
           Side(pred_stored, ...), lookup=None, comparator=cmp) -> UnitAlignment

from instruments.keys import compute_keys, mismatch_causes      # compute_keys(stored, lookup=None, macros=page_macros) -> BatchKeys
from instruments.scores import score, prf, agreement_rows, write_tsv, symmetrized, key_agreement, kappas

import mathgrammar as M                                          # the math reader (ADR-0009)
r = M.parse(latex, kind="formula"|"relation"|"member"|"set_expr"|"any_value", macros=page_macros,
            context={"variables": [...], "functions": [...]})   # -> MathResult(status, kind, tree, reason, occurrences, notes)
M.canonical(r); M.to_sympy(r)                                   # raises Ambiguous / NotRepresentable / NotParsed
r, occ = M.occurrences_in_span(text, start, end, macros=page_macros)   # M13: symbols of a math span, offsets into text
# Occurrence(name, base, sub, sup, start, end, constant, in_subscript_of)
```

`mathgrammar.parse` takes the macro table as given; the instruments pass
`values.merged_macros(page_macros)` (page over the D2 §12.1 fallback).

Pass the page's `parse_detail.macros` (S1 `renditions.json`) as `macros` to the comparator and
to `compute_keys`; `Side.segment_spans` must contain the statement anchor keys (unit, sentence
segments) so statements can be aligned by anchor overlap.

## Validation categories (instruments §2.3)

37 planted invalid batches (mutations of the T3 or T2 test batch), each with its expected
category and code written first. Reported exactly as expected:

| Category | Planted cases (code) |
|---|---|
| malformed | evidence without `quote` (`missing`); extra field on a claim (`extra_forbidden`); `param_of` binding without `param` (`binding_fields`); no `unit_ref` (`missing`); condition node with unknown `op` (`union_tag_invalid`) |
| unknown schema element | predicate, modality, entity class, statement kind, qualifier, bind kind, condition predicate, enum value (`unknown_*`) |
| type mismatch | subject outside domain; entity object for a formula predicate; object class outside range; qualifier not listed for the predicate; entity scope against `ci:scope`; `FamilyParameter` without identity; condition-predicate arity |
| reference error | unresolved subject; `variable` binding naming a claim; `param_of` binding naming an entity; `variable` binding naming a global entity; `param_of` to a parameter the claim lacks (`binding_param_missing`); condition claim node outside the batch (`INV-08`); condition cycle; duplicate local ref; unknown sentence id; `statement` naming an entity |
| invariant | INV-01; INV-02 (both ref and value; no object); INV-05 (local without extent; global with extent); INV-06; plus INV-05 and INV-10 on stored batches |

Also tested: the T2, T3 and T3-sd batches are valid in both forms; INV-09 marks a claim with a
`phrase` leaf conditional; one batch with four independent defects reports all four categories.

## Locator (D4 §4.3 step 2, instruments §3; cascade revised in I-R1)

The cascade is the one the regex probe measured (`code/regex_probe.py`, results/regex_probe/):
exact in the sentence (step 1), exact in the unit (2), exact up to spacing as a `regex` pattern
over the original text (3), the same with the page's macro spellings (4), RapidFuzz window
refined by `regex` BESTMATCH (5, or the window when the refine finds nothing); every span snapped
outward to word boundaries; coarse sentence span otherwise. Planted synthetic cases (21) and real
S1 cases (11) all hit their expected span and step:

| Case | Step |
|---|---|
| exact in cited sentence; verbatim quotes across an `a.ref` gap under conventions (a) nothing, (b) `[ref]`, (c) target text; list item with and without its "(a) " marker; real T1–T4 quotes | 1 `exact_sentence` |
| exact in the unit with the wrong sentence cited; phrase twice in the unit (nearest occurrence to the cited sentence chosen, `matches=2`) | 2 `exact_unit` |
| `$…$` with re-spaced LaTeX; `\(\sigma\)` against `\( \sigma \)`; real `let $X = a + b Z$` → `let \(X = a + b \, Z\)`; real `$b^2\sigma^2$` → `\(b^2 \sigma^2\)`; real `scale parameter $\sigma \in (0,\infty)$` | 3 `spacing` |
| `\mathbb{R}` in the quote for `\R` in the text (cascade test) | 4 `macros` |
| gap "repaired" under (a) (96.1, whole clause) and (b) (86.3, whole clause; coarse before I-R1); straight for curly quotes, 29 and 48 characters (coarse / step 4 before); "1." for "(a)" marker; 104-character quote with one typo (whole span; truncated before); real trace-style "1. The parameter $\sigma$ …" (91.2; coarse before) | 5 `fuzzy` |
| gap repaired under (c) (an 11-character gap); a long dropped word; an unrelated quote | coarse (sentence span) |
| unlocated with an unknown sentence id | dropped, reported |

**The probe's figures reproduced** (`test_locate_cascade.TestProbeFigures`, the probe's own
quotes and seeded perturbations through `s0_locate.locate_quote`, 2026-10-28): 0 mid-word cuts in
every kind; macro 16/16 exact; respace 60/60 exact; drop_word 43/99 exact (76 found); typo 130/132;
add_period 96/162; trim_end 47/58; worst case 210.7 ms (the 0.2 s refine timeout). A refine that
times out falls back to the RapidFuzz window, snapped (tested).

Stored conversion: T2 `X` (extent section) → `seg:section`; `scope: section` → `{extent, segment}`;
T3 `X`, `Y` (extent statement, statement anchored to two sentences) → the enclosing unit; an
entity no claim mentions in a two-statement batch is reported; phrase leaves get offsets;
unlocated evidence becomes a coarse sentence span, evidence without a valid sentence is dropped.
Re-anchoring moves spans after an insertion and lists the one span whose text was reworded.

**Hook.** `code/tests_instruments/real_text_cases.py` holds the real-text cases; append T1–T4
cases there once the trace batches exist. Set `S0_SENTENCE_VARIANT` to the adopted variant name
(default `provisional`).

## Value equivalence (instruments §4)

Tested decisions, each re-checked by hand (the equivalence spot-check of §9 for these cases):

| Pair | Conditions | Decision · tier | Hand check |
|---|---|---|---|
| `b^{2} \sigma^2` / `b^2\sigma^{2}` | — | equal · canonical | correct |
| `b^2 \sigma^2` / `\sigma^2 b^{2}` | — | equal · sympy (math grammar) | correct |
| `a + b \mu` / `\mu b + a`; `X = e^Y` / `e^{Y} = X` | — | equal · sympy | correct |
| `\R \setminus \{0\}` / `(-\infty, 0) \cup (0, \infty)` | — | equal · sympy | correct |
| `\lvert b \rvert \sigma` / `\sqrt{b^2} \sigma` | b ∈ ℝ∖{0} | equal · numeric | correct for real b |
| `\lvert b \rvert \sigma` / `b \sigma` | b ∈ (0, ∞) | equal · numeric | correct |
| `\lvert b \rvert \sigma` / `b \sigma` | b ∈ ℝ∖{0} | unequal · numeric | correct |
| `a + b \mu` / `a + b`; `2 + 2` / `5`; `(0, \infty)` / `[0, \infty)` | — | unequal · numeric / sympy / sympy | correct |
| `\var(X)` / `\sigma^2` | — | pending (manual) | `\var(X)` reads as the undefined operator var(X): simplify cannot decide, numeric cannot evaluate; correctly not decided |
| `\Gamma(a+1)` / `a \Gamma(a)` | — | equal · sympy | correct (`\Gamma` is a declared known function) |
| `a(b + c)` / `a b + a c` | a, b, c bound | equal · sympy; pending without the binding map | correct (product only when declared) |
| 1 cm / 0.01 m; 0.1 / 0.1000000000001 | — | equal · canonical / numeric | correct |

## Perturbation suite (§9)

Original stored batch (reference) against a perturbed copy (prediction); expected outcomes
written before running; each also aligned in the other direction with equal match counts.

| Perturbation | Expected and observed |
|---|---|
| identity (T2, T3) | all claims match at core, full, evidence |
| swap the "respectively" pairing (T2 C4/C5) | C4, C5 fail core; C1–C3 match at every tier |
| drop the `claim` condition from T3's conclusion C3 | C3 core only; full failure `conditions` |
| `\lvert b \rvert \sigma` → `b \sigma` (T3 with the standard deviation stated) | C3 core only; failure `param_values.values`; decided at **numeric** (simplify inconclusive) |
| T3 premise C1 `supposed` → `asserted` | C1 core only; failure `modality`; C3 still full (its `claim` leaf uses the core matching) |
| rename local symbol X → W (T3) | X, Y unaligned; only C4 (`proves`) matches |
| reorder `and` arguments (T3 C3) | everything matches; claim keys unchanged |
| `b^2 \sigma^2` → `\sigma^2 b^{2}` (T3 C3) | everything matches; decided at **sympy**; claim key differs (`param_values.canonical_latex`) |

Scores over these nine as units: core matched 33 of 38 per side (F1 0.868, by hand), full 30;
bootstrap interval contains the point and lies in [0, 1], n = 9; field breakdown
`conditions 1, modality 1, param_values.values 1`; modality kappa defined on n = 33.
Symmetrized T2 swap agreement 0.6 in both directions.

## Decisions taken

| Choice | Decision |
|---|---|
| Module layout | As instruments §8, plus `conditions.py` (canonicalization shared by keys and align so the two cannot diverge) |
| Batch typing | Pydantic checks structure only; every schema-owned value (predicate, class, qualifier, statement kind and role, modality, polarity, scope extent, bind kind, condition predicate, enum values) is a string checked through `SchemaLookup`, so it reports as "unknown schema element", not "malformed". Items are validated one by one; references are collected from raw items so one malformed item does not cascade |
| Formula positions in conditions; entity positions | A value object or a bare LaTeX string (coerced, no bindings); `{"ref"}`, `{"t": "entity", "ref"}` or a bare local ref |
| Phrase anchoring | `phrase`/`unsupported` nodes and phrase values: `text` + optional `sentence` (model-facing), `start`/`end`/`coarse` (stored); located like quotes; located text replaced by the canonical substring |
| Predicate names | `has_distribution` and `stat:has_distribution` both accepted; keys use the prefixed name |
| Wrong-kind binding | `reference_error` / `binding_wrong_ref_kind`, naming the ref, its actual kind and the expected kind; `variable` must name a local entity, `family_param` a `FamilyParameter`, `param_of`/`param_expr_of` a claim (plus `binding_param_missing` when that claim's `param_values` lacks `param`) |
| Missing identity attributes; scope against `ci:scope` | `type_mismatch` (`identity_keys_missing`, `scope_disagrees_with_class`) |
| Locator cascade (I-R1) | As measured by the probe; cutoff 85; refine window widened by 30% of the quote, error budget ⌈0.15·len⌉, timeout 0.2 s; quote stripped of trailing `.,;:` for the fuzzy step. Additions to the probe's pattern, both recorded because D4 requires them: the joiner also skips math delimiters (`\(`, `\)`, `\[`, `\]`) and a delimiter written in the quote (`$`, `$$`, `\(` …) is an optional, preferred delimiter (D4 §4.3: "$…$ and \(…\) are equivalent"); the joiner is lazy and span ends are trimmed of whitespace (a greedy joiner swallowed a closing `\)` and the following space, caught by the planted tests). Steps 3 and 4 search the cited sentence, then the unit (the probe searched the sentence only; the figures are unchanged since its quotes cite the right sentence). The macro step uses the context's `macros` (page) over the D2 §12.1 fallback, so `s0_check.context` works unchanged |
| Several exact matches in the unit | The occurrence nearest the cited sentence; `matches` records the count |
| `extent: statement` | Binding statement = the statement of the earliest-evidenced claim mentioning the entity (subject, object, entity qualifier, `variable`/`family_param` binding, `pred` argument); else the batch's only statement; else reported. Its anchor keys → one segment via the caller's `statement_scope` |
| `extent: section` | `section_of(earliest evidence start of those claims)` |
| Stored `scope` qualifier | `{extent, segment}` (D1 §5.2); `section` → section of the claim's first evidence, `statement` → statement scope, `document` → document key |
| Canonical LaTeX | D1 §6.2, printed from the math grammar's tree (`mathgrammar.canonical`): leaves in order, macros expanded from the table, what the grammar ignores dropped (spacing commands, `\left`/`\right`, `\quad`, whitespace, …), braces around single tokens dropped; a space is kept after a control word followed by a letter (`\mu x` ≠ `\mux`). Values that do not parse get the same normalization on their tokens. On all 86 S0 values the output equals the pre-I-R1 form, so keys do not move |
| Numbers | pint 0.26.2 (in the spike env since `de5bd4c`) converts to base units; its float factors are rounded to 15 significant digits so canonical strings carry no float noise. The fallback table (m, cm, mm, km, in, ft, kg, g, s, min, h, %) applies only when pint is absent or does not know the unit; an unknown unit is kept as written with factor 1 |
| SymPy tier (I-R1) | The value read by the math grammar under its slot's kind (formula: `formula`, then `relation`, then `member`; set: `set_expr`), converted by `mathgrammar.to_sympy`; the shim is gone. The formula's binding-map symbols are declared variables. Ambiguous, unparsed and unrepresentable values go to manual, each logged once in `PARSE_LOG` with status and reason. `simplify(a − b) == 0` → equal; nonzero constant → unequal; equations compared as `lhs − rhs` up to sign; `e` → E, `\pi` → π; memberships and chains compare by SymPy equality, else manual |
| Function application | Through the grammar's ambiguity rules: `symbol(...)` is an application only for a declared function (`\Gamma`, the gamma function, by default; or a definition `g(x) = …` in the same value) and a product only when every such symbol is a declared variable (binding map); otherwise ambiguous → manual. Operators from the macro table (`\E(X)`, `\var(X)`) are undefined SymPy functions, never ambiguous |
| Relations | `x < 1`, `X \le x`: kind `relation`. `>`/`>=` rewritten as `<`/`<=`; same operator and `lhs − rhs` simplifying to the same expression → equal; differing by a nonzero constant → unequal; relation against an expression or equation → unequal; different operators or anything else → manual |
| Simplify time limit | 5 s (SIGALRM; main thread only) |
| Numeric sampling | Seed 20261028; up to 12 **distinct** accepted points, at most 4,000 draws; reals half uniform in [−5, 5], half of magnitude 10⁻²…10³ with random sign (so `\min(x, 10)` is exercised), shifted or bounded by numeric bounds read from `member` sets and `symbol <rel> number` leaves; integers (symbols in integer sets) uniform over [lower bound, lower bound + 200], default [−100, 100]; top-level conjunctive `member`/`cmp` leaves of both claims' conditions; `isclose(rel 1e-9, abs 1e-12)`; at least **6 distinct** valid points to decide, else manual; any disagreeing point → unequal |
| Tree matching | Canonical-only pass first, then the tiered comparison (so cross pairs such as `member(a,…)`/`member(b,…)` do not reach the numeric tier and pad the OPEN-D7-2 tally) |
| Entity weights and threshold | See `align.py` docstring: local symbol 0.7 + scope 0.2; global label/alias 1.0, D2 §12.1 alias rules 0.9; `FamilyParameter` identity 1.0 or not aligned (near miss recorded); statements by anchor overlap 0.6–1.0; evidence tie-break +0.05; threshold 0.5 |
| Fuzzy label matching | `token_sort_ratio` ≥ 90 aligns only classes in `FUZZY_TYPES`, **empty for v0**. Every v0 global class (DistributionFamily, FamilyConstruction, Concept, FamilyParameter) names a mathematical object whose identity turns on a prefix or one word ("normal"/"lognormal" 92.7, "standard normal"/"standard lognormal" 94.9, "scale"/"shape"), which an edit-distance ratio cannot tell from a typo; so no class qualifies. A fuzzy-only candidate is recorded in `label_near_misses` (shown by `describe`) for hand checking; aligned fuzzy-basis pairs would be listed in `fuzzy_pairs` (none possible in v0). A class is added only with an argument that small label edits never change its identity |
| Core claim matching | Lexicographic: most core pairs, then most full-compatible, then most evidence-compatible pairs, then evidence overlap (weights 1e6 / 1e3 / 1 / 1e-3; at most 999 claims a side) |
| Claim leaves in full-tier conditions | Fixed point: pass 0 accepts a leaf pair when the premises are core-compatible (any core edge); each later pass judges leaves through the current core matching and re-chooses the matching; stop when stable (at most 8 passes; 2 in every test and probe). Full, evidence, field failures, bindings, kappa and key agreement all use the final matching |
| Cascade | A premise that fails the core tier makes each conclusion citing it fail the full tier (its `claim` leaf has no counterpart). Such pairs are listed in `UnitAlignment.cascaded` and counted by `field_breakdown` and `score()["cascade"]`; tiers `full_nocascade` / `evidence_nocascade` repeat the matching with leaves accepted when neither side's premise is core-matched (`prf(alignments, ("full_nocascade", "evidence_nocascade"))`), so figures can be given with and without the cascade. A premise's own full-tier failure does not cascade |
| Alternatives scoring | D7 §5.3: an alternatives group is **one item** on its side (overlapping groups merged), matched at a tier when any of its readings is matched there; its other readings are neither misses nor extra matches. Symmetric for prediction groups. Precision = matched prediction items / prediction items, recall = matched reference items / reference items, F1 their harmonic mean (equal to 2m/(n_ref + n_pred) without groups). Item predicate: the group's first listed reading. Totals report `matched_ref`, `matched_pred` (and `matched` = `matched_ref`) |
| Unsupported items | Paired by maximum count (any span overlap qualifies); total overlap share breaks ties only |
| Bindings, extent | Per-field *diagnostics* on core-matched pairs, not full-tier criteria (D7 §5.3 does not list them) |
| Keys | Part layout in `keys.py`; defaults dropped; meaning key uses the referenced claims' meaning keys inside conditions; cycles drop the claims on or behind them |
| Symmetrization | Mean of the two directions' F1 per tier; a difference is flagged `asymmetric` |
| Bootstrap | 1,000 resamples over units, percentile 95% interval, seed 20261028, NaN resamples skipped |

## Math grammar (instruments revisit I-R1, ADR-0009)

One reader of math for every instrument: `code/mathgrammar`. SymPy 1.14's shipped `latex.lark`
is read unedited from the installed package (as `LarkLaTeXParser` does); our additions are in
`extension.lark` (`%extend` / `%override` only); a block generated from the rendition's macro
table defines the operator, set and wrapper terminals. Earley, `ambiguity="explicit"`,
`propagate_positions`, `keep_all_tokens`. **Measured** coverage (`results/mathgrammar/`,
2026-10-28): S0 values 86/86 read under their declared kind (formula 70, set 16), 85 with a SymPy
value, canonical form unchanged on all 86; corpus sample of 1,532 spans from 78 pages: 976 ok,
256 ambiguous, 1 partial, 299 failed (inline 664/780 ok). Failures by category and what is left
to S5 are in `results/mathgrammar/README.md`.

| Choice | Decision |
|---|---|
| Assembly | shipped grammar + generated whole-name `%override`s of SymPy's own command terminals (derived from its definitions, so `\sinh` never lexes as `\sin`+`h`, `\le` never inside `\left`) + `extension.lark` + `GEN_SET` / `GEN_OP` / `GEN_STYLE` from the macro table. All command terminals end in `(?![A-Za-z])`: `\P` never matches the start of `\Phi` |
| Macro classification (source data) | nargs-0 bodies, spacing ignored (`\,\text{sgn}`): `\mathbb{R|N|Z|Q|C}` → set constant; other `\mathbb{X}` → operator X; `\text{w}` / `\operatorname{w}` / `\textrm{w}` / `\mathrm{w}` (≥ 2 letters) → operator w; a bare typeface command → transparent wrapper; anything else → `other` (not in the grammar, listed). Macros with arguments only expand in the canonical form. One parser per classification (cached), results cached per (latex, kind, table, context) |
| Symbols | Sub- and superscripts as rules: `sub_symbol` (base `_` token or `{list}`), `sup_sub` (`\sigma^2_X`), replacing SymPy's four `*_WITH_*_SUBSCRIPT` regex terminals; SymPy names are taken from the structure (`sigma_{X_1}`, `X_{(n)}`, `X_{1}`), so no subscript is lost or merged (F2) |
| Implicit multiplication | SymPy's particular adjacent pairs replaced by one rule, a power-level factor before a product (right-associative): `b^2 \sigma^2`, `\sqrt{2\pi}\sigma`, `(r_1 + r_2)\lambda(A)`, `\binom{n}{k} p^k` |
| Kinds | Start symbols `formula` (expression or equation), `relation` (inequalities, ≠, chains `a = b \le c`, `\subset`, convergence `\to`/`\uparrow`, `\sim`/`\approx`/`\equiv`/`\propto`), `member` (`a, b \in S`, `\notin`), `set_expr`, `any_value` (any of these, or a comma list `f(x) = …, \quad x \in S`). An equation is a formula only, so equations are not read twice |
| Sets | `\R`-type constants with `_+`/`_-` or a power, intervals `(a, b]`, braced lists (ellipses allowed), set-builder `\{x \in S: …\}`, events `\{X \le x\}`, named sets, `\setminus`/`\cup`/`\cap`/`\times`, `\emptyset`. SymPy: ℕ → `Naturals0`, ℕ₊/ℤ₊ → `Naturals` (as before I-R1), `\R^2` → `ProductSet`, set-builder → `ConditionSet` |
| Operators | `op_name (…)` / `op_name […]` with lists, relations, memberships and conditions inside (`\P(X \in A \mid Y)`, `\P(I = 1, V \le u)`) → undefined SymPy `Function` named by the operator (`E`, `var`); a condition is `Given(lhs, rhs)` |
| No SymPy value (parse, then `NotRepresentable`) | `\pm`, ellipses, norms, `\liminf`/`\limsup`, `\sup`/`\inf`, set-indexed sums and integrals, `\wedge`/`\vee`, named sets, events, `\subset`, convergence and `\sim`-type relations, symbolic set powers |
| Ambiguity | Explicit; resolved only from declared context: `symbol(…)` is an application for a declared function (`\Gamma` by default; `context["functions"]`; a definition `g(x) = …` in the same value) and a product only when every such symbol is a declared variable (`context["variables"]`: the binding map); readings with identical SymPy values are one (associativity); under `any_value` a lone symbol is a formula (a named set needs a set position) and `a, b \in S` is the membership of every element (standard convention; both noted); a bare `(a, b)` under `any_value` is ambiguous (interval or pair); `F^{-1}(p)` with undeclared F is ambiguous (inverse notation the grammar would read as a product); anything else ambiguous is reported, never picked |
| Status | `ok`; `ambiguous`; `partial` (read only after dropping trailing `.`, `,`, `;`); `failed` with `{error, pos, at, category}`. Category: the offending command first (`\lim`/`\to` limit-arrow, `\int` integral-bounds, `\sum`/`\prod` sum-bounds, `\begin` environment, `\text` text-in-math, `\Rightarrow`-type unsupported-relation, else unknown-command), `UnexpectedInput.match_examples` otherwise (with Earley, an error where an expression is expected shares its parser state with most examples, so `match_examples` alone labelled `\begin{cases}` "limit-arrow"; caught by a test) |
| Occurrences (M13) | From token positions: `Occurrence(name, base, sub, sup, start, end, constant, in_subscript_of)`; a subscript's own symbols are occurrences too (`X_1` inside `\sigma_{X_1}`); `e` and `\pi` flagged constant; operator names and `\text` words are not symbols. `occurrences_in_span(text, start, end, macros)` gives offsets into canonical text |
| Canonical form | Printed from the tree's leaves (see Decisions, "Canonical LaTeX"); the token form is the fallback for unread values, with the same rules, so a value's canonical form does not change when the grammar learns to read it |
| Validator slot check | A formula, set or condition-operand value must read under its slot's kind: read only as another kind → `type_mismatch` / `slot_kind` (a set in a Formula slot, a relation where a formula belongs, a formula as a member's set); a number followed by letters that pint knows as a unit (≥ 2 letters: `1 cm`) → `type_mismatch` / `bare_unit_formula` (single letters such as `2 x` are not flagged); not read under any kind → `ValidationReport.notes` (coverage is not the annotator's fault) |

Defects found while building I-R1 and fixed: the quote pattern's greedy joiner swallowed a
closing `\)` and the following space, and an optional leading delimiter let a match start on a
space (planted locator tests); `match_examples` mislabelled errors (above); the lone-symbol,
`a, b \in S` and `g(x) = …` rules were added after the first coverage run showed 364 ambiguous
spans dominated by them (now 256, of which 222 are undeclared application-or-product).

## Ambiguities and contradictions found in the design

1. **D4 §4.3 step 2 vs D5 §5.6.** D4: an unlocated quote leaves the item with
   `evidence_unlocated: true`; D5: it falls back to the cited sentence's span with
   `evidence_coarse`. The instruments follow D5 and instruments §3.
2. **D4 §4.3 fuzzy spans (F-LOC-1), addressed by I-R1.** `partial_ratio_alignment` returns a
   window of exactly `len(quote)` characters, so a paraphrased quote was cut mid-word ("…
   approximation hol"). The I-R1 cascade refines inside the window with `regex` BESTMATCH and snaps
   every span to word boundaries: 0 cuts on the probe's 527 perturbed quotes. D4 §4.3 should name
   the refine and the snap.
3. **D4 §4.3 normalization, addressed by I-R1.** "Whitespace collapsed" did not match re-spaced
   LaTeX; the spacing step now matches up to spacing over the original text (60/60 re-spaced quotes
   exact), and straight for curly quotes is found by the fuzzy step (2 substitutions) instead of
   falling back to coarse. D4 §4.3 should state the cutoff (85, not 95) and the steps.
4. **D7 §5.2 vs §5.4.** "Normalized symbol and same scope segment" as an alignment *condition*
   makes scope accuracy over aligned local entities 1 by construction; implemented as a weight.
5. **D7 §5.3 claim leaves.** "By the alignment of the referenced claims" does not say which
   tier's alignment (core chosen), nor that the alignment and the full-tier judgment depend on
   each other (resolved by fixed-point iteration). It also implies the cascade: a premise
   failing core fails every conclusion citing it at the full tier.
6. **D1 §7 / D2 §7.3 phrase anchoring.** `phrase` and `unsupported` nodes have a `span`, which
   the model-facing form cannot carry; D2 §7.3 does not say how phrase values and leaves are
   cited (chosen: `text` + `sentence`). Phrase-valued qualifiers (`hedge`, `limit`) likewise.
7. **D1 §7 formula positions.** Whether `member.x`, `cmp.lhs` … are value objects (with
   `symbols`) or LaTeX strings is not stated; both accepted.
8. **D2 §7.3 identity values.** `identity{slot: value}` for an entity-ranged slot (`family`)
   is not said to be a local ref; also the predicate form (`const <p>`, bare or `stat:`).
9. **D2 §7.3 extent `statement`.** "The statement that binds it" is not defined for an entity
   (D2 has no entity → statement link); and a statement anchored to several sentences has no
   single segment. Both are resolved by caller lookups and the heuristic above.
10. **INV-09** cannot be violated by a batch (no "unconditional" flag); the validator marks.
11. **D1 §6.2 "whitespace removed"** conflates `\mu x` and `\mux`; the separator after control
    words is kept.
12. **D1 §5.2 vs D2 §6.** D1 gives `scope` as `{segment, extent}`; core.yaml types the qualifier
    as the `ScopeExtent` enum ("the stored form adds the segment"). Consistent if read as the
    two forms; the stored shape `{extent, segment}` is an instrument choice.
13. **D5 §5.2 key cascade.** Because condition `claim` refs enter keys as claim keys, a
    premise's modality change changes the conclusion's claim key (tested: cause `conditions`)
    although the conclusion matches at the full tier. Key agreement therefore understates
    agreement on conclusions; evidence for OPEN-D3-4.
14. **D1 §10.1 global keys include the label** even for `FamilyParameter`, whose identity is
    declared by `ci:identity_keys`: "mean" and "mean parameter" with the same identity get
    different keys (cause `label`).
15. **D2 §4 map qualifiers.** LinkML's inlined `ParamValue` (`key`, `value`) would serialize
    as `{mean: {value: …}}`; batches use `{mean: <formula>}`. S4 should confirm the JSON shape.
16. **SymPy 1.14 lark (for S5, OPEN-D7-2, D2 §12.1 `normalize.formula: lark`).** The shipped
    grammar has no `\sigma`, `\pi`, uppercase Greek, `\lvert`/`\rvert`, implicit multiplication
    after a power or a closing group (`b^2 \sigma^2`, `\sqrt{2\pi} \sigma`), `\text{var}`,
    `\mathbb{E}`; it reads `X_1`, `\mu_1` as single regex terminals (no `\sigma_{X_1}`, `X_{(n)}`),
    returns an unresolved `_ambig` for `f(x)` and silently multiplies `f(x) y`. I-R1 extends it by
    Lark directives only (see "Math grammar"); S5 should take `code/mathgrammar` as its M09/M11
    starting point rather than the shipped grammar or a string shim.

## S4 observations (byproduct)

- `statistics.yaml` imports `../../core/schema/core` (D2 §2 layout). The flat `code/schema/`
  copy loads **unedited** with `SchemaView(path, importmap={"../../core/schema/core": …/core})`.
- OPEN-D2-6: list-valued annotations survive in linkml-runtime 1.12.1 — `ci:qualifiers` reads
  back as `list ['param_values']`, `ci:examples` as a list; booleans (`ci:functional`) as `bool`.
- 19 classes, 62 slots, 9 enums, 25 predicates; `class_ancestors('RandomVariable')` includes the
  mixin `Distributed`.

## Independent review findings (2026-10-28), fixed

| Id | Defect (pre-fix) | Fix | Test |
|---|---|---|---|
| F1 | The core matching was arbitrary among equally large ones, and premise leaves were judged through that one map: T3 plus a second premise X ~ N(0, 1) and its conclusion against a renamed, reordered copy gave full and evidence 4/6, bindings 7/12 | Lexicographic core matching and fixed-point leaf judgment (Decisions) | `TestReviewFindings.test_f1_*`: 6/6 at every tier, no field failures, bindings 12/12, both claim orders, and with B's premise spans shifted |
| F2 | Shim dropped non-alphanumeric subscripts: `\sigma_{X_1}^2` = `\sigma_{X_2}^2`, `\sigma_{\mu}` = `\sigma`, `\sigma_{X_1}+\sigma_{X_2}` = `2\sigma` | Subscript kept in the placeholder | `test_f2_*`: these and `\sigma_{1,2}`/`\sigma_{2,1}`, `\Sigma_1`/`\Sigma_2` not equal; `\sigma_{X_1}\sigma_{X_2}` still equal to its reorder |
| F3 | `\Phi(x)` became `Phi·x`, so `\Phi(-x)` = `-\Phi(x)` | Application ambiguity → manual | `test_f3_*`: `\Phi(-x)`/`-\Phi(x)` pending, `\Gamma(2a)`, `\Gamma(a+1)`, `f(x) y`, `\phi(2x)` not equal |
| F4 | Fuzzy matching aligned "normal distribution" with "lognormal distribution" (92.7) and "standard normal" with "standard lognormal" (94.9) | `FUZZY_TYPES` empty; near misses recorded | `test_f4_*`: unaligned, near miss listed, no fuzzy pairs |
| F5a | A relation (`x < 1`) raised `TypeError` | Relation comparison | `test_f5a_*` |
| F5b | Duplicate points counted; integers only in [−10, 10], reals in [−5, 5]: `n^2` = `19n − 90` for n ∈ ℕ, n > 8 (only 9 and 10 admissible) and `\min(x, 10)` = `x` | Distinct points, bound-aware ranges, large-magnitude reals, 6 distinct points needed | `test_f5b_*`: both unequal; with only two admissible integers → manual |
| F5c | Every reading of an alternatives group counted as a separate item | Group = one item, both sides | `test_f5c_*`: recall 1 with one reading predicted, either reading; precision 1 with groups on the prediction side |
| F5d | Unsupported pairs maximized total overlap, not count | Maximum count, overlap breaks ties | `test_f5d_*`: 2 pairs where the old rule gave 1 |
| F5e | Cascade not reported | `cascaded`, `*_nocascade` tiers, counts | `test_f5e_*`: premise failing core → conclusion cascaded and matched in `full_nocascade`; a genuinely dropped condition is not a cascade |
| F5f | Record said pint was not installed | Record and `number_base` updated; pint errors on unknown units fall back instead of raising | `test_f5f_*` |

## Defects found and fixed while testing

- Numeric tier sampled only the symbols of `a − b`, so the relative scale (needs all symbols of
  `a`) never evaluated and every pair went to manual; caught by the hand expectation for
  `a + b\mu` / `a + b`.
- A malformed condition tree hid its `claim` references and produced a false INV-06 on the
  premise; references are now harvested from raw items.

## Not done here; for the coordinator

- **I-R1 follow-ups.** Pass the page's macros: `UnitContext(..., macros=...)` in
  `s0_check.context` (the macro step otherwise uses the D2 §12.1 fallback, identical for the four
  spike pages), `validate_batch(..., macros=...)`, and `ValueComparator(macros=...)` as before.
  Switch `s0e_m13_probe.py` to `mathgrammar.occurrences_in_span`. No key recomputation is
  needed: canonical forms are unchanged on every S0 value (86/86). Re-locating the stored passes
  with the new cascade changes fuzzy spans (now whole words) and locates quotes that were coarse;
  re-run `to_stored` before figures that depend on evidence spans.

- Write the trace's T1–T4 tables as stored batches, align a pass to them by hand, compare with
  `describe(align_unit(...))`, and write `results/s0/aligner_verification.md` (instruments §9);
  run the perturbations on those batches (the suite here uses my T2/T3 test batches).
- Create `results/s0/manual_equivalence.tsv` from `ValueComparator.pending_tsv()` and decide it.
- Add T1–T4 real-text locator cases to `real_text_cases.py` once the adopted sentence variant
  exists; rerun with `S0_SENTENCE_VARIANT`.
- Report full and evidence figures with and without the cascade (`full_nocascade`), and check
  every `label_near_misses` entry by hand.
- Not implemented (outside instruments §5.3's list): D7 §5.4 breakdowns by statement kind and
  chapter, identity quality (B-cubed across units), the S2 span-overlap entity alignment of §7.
- Typing/lint of the spike code was not run (`not_run`); `just turn-end` is the root's.
