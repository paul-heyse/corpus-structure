# Comparison instruments: test record (I-A, I-B)

**2026-10-28.** Implements packages I-A and I-B of
[comparison-instruments.md](../../../../../plans/design-spikes-s0-s1/comparison-instruments.md)
(§2–§9) against D1 §6–§7, §10–§11, D2 §6, §7.3, §9, §12.1, D4 §4.3, D5 §5.2, §5.6 and D7 §5.
Baseline: HEAD `60ac9e5`; review fixes on `249b0c2` (2026-10-28). Spike env: Python 3.14.10, pydantic 2.14.1, linkml-runtime 1.12.1, pint 0.26.2,
rapidfuzz 3.14.6, scipy 1.18.1, statsmodels 0.15.0, sympy 1.14.0 + lark 1.3.1 (pylatexenc is not
used by the instruments). Claims below are **Tested** on synthetic and S1 text unless marked.

## Result

| Command (from `code/tests_instruments/`) | Outcome |
|---|---|
| `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python run_all.py --logs` | **passed**: 50 tests (37 invalid-batch cases and 20 planted locator cases run as subtests), exit 0, 2026-10-28, after the review fixes below (first run: 40 tests, passed) |
| `… uv run python -m unittest test_locate_real` (S1 canonical text, `provisional` sentences) | **passed**: 11 real-text cases, 2026-10-28 (rerun after the review fixes) |
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
| `code/instruments/values.py` | Canonical forms, tiered `ValueComparator`, lark parse log |
| `code/instruments/conditions.py` | Condition canonicalization and equivalence (shared by keys and align) |
| `code/instruments/align.py` | `align_unit`, `describe` |
| `code/instruments/scores.py` | P/R/F1, bootstrap, agreement rows, binding/scope accuracy, kappa, key agreement, symmetrization |
| `code/instruments/keys.py` | `compute_keys`, `mismatch_causes` |
| `code/tests_instruments/` | `fixtures.py` (synthetic T2/T3 text and batches), `test_validate.py`, `test_locate.py`, `test_locate_real.py` + `real_text_cases.py` (**coordinator hook**), `test_values.py`, `test_align.py`, `run_all.py` |

## Public functions the coordinator calls

```python
from instruments.batch import load_batch, wrap                 # (envelope|None, batch) / enveloped dict
from instruments.validate import validate_batch                # -> ValidationReport (.ok .issues .categories() .counts() .lines() .conditional_claims)
validate_batch(raw, lookup=None, form="model"|"stored", *, canonical_text=None, sentence_ids=None, unit_ranges=None)

from s0_locate import UnitContext, locate_quote, to_stored, reanchor
UnitContext(text, unit_ranges, sentences={sid: (start, end)}, unit_keys=[], sentence_keys={sid: key},
            section_of=None,        # offset -> section segment key (S1's adopted synthesis)
            statement_scope=None,   # [anchor segment keys] -> one scope segment key (default: the single key)
            document_key=None)
locate_quote(quote, sentence_id, ctx) -> Located(start, end, tier, scope, matches, score, long_quote, coarse, dropped, note)
to_stored(model_batch, ctx) -> (stored_batch, LocateReport)    # .by_tier() .ambiguous() .unlocated() .problems .as_json()
reanchor(stored_batch, old_text, new_ctx) -> (stored_batch, failed_spans)

from instruments.values import ValueComparator, canonical_latex, canonical_value, PARSE_LOG
cmp = ValueComparator.with_manual_tsv("results/s0/manual_equivalence.tsv", macros=page_macros)  # TSV: kind a b decision reason
cmp.compare(va, vb, conds=(), ref_eq=None) -> Equivalence(equal, tier, kind, a, b, detail, shim); cmp.tally(); cmp.pending_tsv()

from instruments.align import Side, align_unit, describe
align_unit(Side(ref_stored, segment_spans={key: (s, e)}, sentences=[(s, e), ...], unit=...),
           Side(pred_stored, ...), lookup=None, comparator=cmp) -> UnitAlignment

from instruments.keys import compute_keys, mismatch_causes      # compute_keys(stored, lookup=None, macros=page_macros) -> BatchKeys
from instruments.scores import score, prf, agreement_rows, write_tsv, symmetrized, key_agreement, kappas
```

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

## Locator (D4 §4.3 step 2, instruments §3)

Planted synthetic cases (20) and real S1 cases (11) all hit their expected span and tier:

| Case | Tier |
|---|---|
| exact in cited sentence; verbatim quotes across an `a.ref` gap under conventions (a) nothing, (b) `[ref]`, (c) target text; list item with and without its "(a) " marker; real T1–T4 quotes | 1 |
| exact in the unit with the wrong sentence cited; phrase twice in the unit (nearest occurrence to the cited sentence chosen, `matches=2`) | 2 |
| `$…$` with re-spaced LaTeX; `\(\sigma\)` against `\( \sigma \)`; real `let $X = a + b Z$` → `let \(X = a + b \, Z\)`; real `$b^2\sigma^2$` → `\(b^2 \sigma^2\)` | 3 |
| gap "repaired" by the annotator under (a) (96.1); straight for curly quotes, 48-char quote (95.8); "1." for "(a)" marker (96.2); 104-char quote with one typo (flagged `long_quote`) | 4 |
| gap repaired under (b) and (c); straight quotes, 29-char quote; real trace-style "1. The parameter $\sigma$ …" | coarse (sentence span) |
| unlocated with an unknown sentence id | dropped, reported |

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
| `b^2 \sigma^2` / `\sigma^2 b^{2}` | — | equal · sympy (shim) | correct |
| `a + b \mu` / `\mu b + a`; `X = e^Y` / `e^{Y} = X` | — | equal · sympy | correct |
| `\R \setminus \{0\}` / `(-\infty, 0) \cup (0, \infty)` | — | equal · sympy | correct |
| `\lvert b \rvert \sigma` / `\sqrt{b^2} \sigma` | b ∈ ℝ∖{0} | equal · numeric | correct for real b |
| `\lvert b \rvert \sigma` / `b \sigma` | b ∈ (0, ∞) | equal · numeric | correct |
| `\lvert b \rvert \sigma` / `b \sigma` | b ∈ ℝ∖{0} | unequal · numeric | correct |
| `a + b \mu` / `a + b`; `2 + 2` / `5`; `(0, \infty)` / `[0, \infty)` | — | unequal · numeric / sympy / sympy | correct |
| `\var(X)` / `\sigma^2` | — | pending (manual) | parse failure, correctly not decided |
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
| Locator tier 3 | Delimiters (`$`, `$$`, `\(\)`, `\[\]`) and `\,` `\;` `\!` dropped and **all** whitespace removed (spec: "collapsed"); collapsing cannot match re-spaced LaTeX. Sentence then unit; span extended over enclosing delimiters when the quote had them |
| Several exact matches in the unit | The occurrence nearest the cited sentence; `matches` records the count |
| `extent: statement` | Binding statement = the statement of the earliest-evidenced claim mentioning the entity (subject, object, entity qualifier, `variable`/`family_param` binding, `pred` argument); else the batch's only statement; else reported. Its anchor keys → one segment via the caller's `statement_scope` |
| `extent: section` | `section_of(earliest evidence start of those claims)` |
| Stored `scope` qualifier | `{extent, segment}` (D1 §5.2); `section` → section of the claim's first evidence, `statement` → statement scope, `document` → document key |
| Canonical LaTeX | D1 §6.2, except a space is kept after a control word followed by a letter (`\mu x` ≠ `\mux`); outer math delimiters stripped |
| Numbers | pint 0.26.2 (in the spike env since `de5bd4c`) converts to base units; its float factors are rounded to 15 significant digits so canonical strings carry no float noise. The fallback table (m, cm, mm, km, in, ft, kg, g, s, min, h, %) applies only when pint is absent or does not know the unit; an unknown unit is kept as written with factor 1 |
| SymPy tier | Raw `parse_latex(expanded, backend="lark")` first; on failure a shim (unsupported Greek → `\mathit{name}`, with any subscript token or group kept in the placeholder through an injective letters-only encoding and restored as `name_{sub}`; `\lvert`/`\rvert` → `|`; `\cdot` inserted after a power, a closing `|` or a closing argument group), recorded with `shim=True` and in `PARSE_LOG`. `simplify(a − b) == 0` → equal; nonzero constant → unequal; equations compared as `lhs − rhs` up to sign; `e` → E, `\pi` → π |
| Function application | A symbol (Latin letter, Greek letter, subscripted symbol) directly followed by `(` reads as application or product (`\Phi(-x)`, `f(x) y`, `\Gamma(k)`, `X_1(t)`); lark either returns an unresolved ambiguity or silently multiplies. Such formulas are not parsed: they go to manual with the reason. Undefined SymPy functions were not used because their equivalence would need the numeric tier, which cannot evaluate them |
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

## Ambiguities and contradictions found in the design

1. **D4 §4.3 step 2 vs D5 §5.6.** D4: an unlocated quote leaves the item with
   `evidence_unlocated: true`; D5: it falls back to the cited sentence's span with
   `evidence_coarse`. The instruments follow D5 and instruments §3.
2. **D4 §4.3 tier 4 spans (F-LOC-1).** `partial_ratio_alignment` returns a window of exactly
   `len(quote)` characters, so a quote shorter than the text it paraphrases gives a span cut at
   one end, mid-word ("… approximation hol"); windows shifted by one character can tie. Proposed:
   widen the window to word boundaries (or search the boundary that maximizes `fuzz.ratio`).
3. **D4 §4.3 tier 3 normalization.** "whitespace collapsed" does not match re-spaced LaTeX
   (implemented as removal); curly versus straight quotation marks (S1 renders `<q>` as “ ”) are
   not normalized, so a short quote typed with straight quotes falls back to coarse. Proposed:
   add quotation-mark (and dash) folding to tier 3.
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
16. **SymPy 1.14 lark (for S5, OPEN-D7-2, D2 §12.1 `normalize.formula: lark`).** The grammar has
    no `\sigma`, `\pi`, uppercase Greek, `\lvert`/`\rvert`, no implicit multiplication after a
    power or a closing group (`b^2 \sigma^2`, `x^{k-1} e^{-x/b}`, `\sqrt{2\pi} \sigma` all fail
    raw), and no `\text{var}`, `\mathbb{E}`. Every T3 formula containing σ failed raw and parsed
    only through the shim.

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
