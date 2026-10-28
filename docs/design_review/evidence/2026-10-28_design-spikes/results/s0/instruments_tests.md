# Comparison instruments: test record (I-A, I-B)

**2026-10-28.** Implements packages I-A and I-B of
[comparison-instruments.md](../../../../../plans/design-spikes-s0-s1/comparison-instruments.md)
(§2–§9) against D1 §6–§7, §10–§11, D2 §6, §7.3, §9, §12.1, D4 §4.3, D5 §5.2, §5.6 and D7 §5.
Baseline: HEAD `60ac9e5`. Spike env: Python 3.14.10, pydantic 2.14.1, linkml-runtime 1.12.1,
rapidfuzz 3.14.6, scipy 1.18.1, statsmodels 0.15.0, sympy 1.14.0 + lark 1.3.1 (pylatexenc is not
used by the instruments). Claims below are **Tested** on synthetic and S1 text unless marked.

## Result

| Command (from `code/tests_instruments/`) | Outcome |
|---|---|
| `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python run_all.py --logs` | **passed**: 40 tests (37 invalid-batch cases and 20 planted locator cases run as subtests), exit 0, 2026-10-28 |
| `… uv run python -m unittest test_locate_real` (S1 canonical text, `provisional` sentences) | **passed**: 11 real-text cases, 2026-10-28 |
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
| Numbers | pint is not installed (**blocked** for exact D1 §6.2 base units): fallback table (m, cm, mm, km, in, ft, kg, g, s, min, h, %) |
| SymPy tier | Raw `parse_latex(expanded, backend="lark")` first; on failure a shim (unsupported Greek → `\mathit{name}`, `\lvert`/`\rvert` → `|`, `\cdot` inserted after a power, a closing `|` or a closing argument group), recorded with `shim=True` and in `PARSE_LOG`. `simplify(a − b) == 0` → equal; nonzero constant → unequal; equations compared as `lhs − rhs` up to sign; `e` → E, `\pi` → π |
| Simplify time limit | 5 s (SIGALRM; main thread only) |
| Numeric sampling | Seed 20261028; 12 accepted points, at most 4,000 draws; reals uniform in [−5, 5], integers in [−10, 10] for symbols in integer sets; top-level conjunctive `member`/`cmp` leaves of both claims' conditions; `isclose(rel 1e-9, abs 1e-12)`; at least 3 valid points to decide; any disagreeing point → unequal |
| Tree matching | Canonical-only pass first, then the tiered comparison (so cross pairs such as `member(a,…)`/`member(b,…)` do not reach the numeric tier and pad the OPEN-D7-2 tally) |
| Entity weights and threshold | See `align.py` docstring: local symbol 0.7 + scope 0.2; global label/alias 1.0, D2 §12.1 alias rules 0.9, `token_sort_ratio` ≥ 90 → 0.6–0.8; `FamilyParameter` identity 1.0 or not aligned (near miss recorded); statements by anchor overlap 0.6–1.0; evidence tie-break +0.05; threshold 0.5 |
| Claim leaves in full-tier conditions | Matched through the core-tier claim matching (no cascade of a premise's own full-tier failure) |
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
   tier's alignment; core chosen.
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
- Not implemented (outside instruments §5.3's list): D7 §5.4 breakdowns by statement kind and
  chapter, identity quality (B-cubed across units), the S2 span-overlap entity alignment of §7.
- Typing/lint of the spike code was not run (`not_run`); `just turn-end` is the root's.
