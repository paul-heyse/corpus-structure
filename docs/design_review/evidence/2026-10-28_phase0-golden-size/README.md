# Evidence: size of the phase 0 extraction scope

**Date:** 2026-10-28 · **Question:** how many agent packets does the `phase0-golden` scope ask of
the session, as a unit-level scope (the four spike pages whole plus the dev golden units by locator)
and as whole golden pages? · **Consumer:** the phase 0 coordinator (decision 9, P0CL-09), D6 §7.4,
the evaluation-and-goldens document (P0-E-1). No evidence record has been finalized.

## Method

`phase0_golden_size.py` simulates D7 §3.1's page split and dev sampler over 500 seeds, on S1's
annotation units (`results/s1/` of the design-spikes folder and the corpus index). Its docstring
states the simulated rules: Weibull reserved; the four spike pages, Pareto and ChiSquare forced into
dev; every fifth other page per chapter to test by hash order; 40 dev units with the 13 trace and
core units forced; strata by statement kind and math-share tercile. Unit keys are S1 segment keys,
not product locators, so the figures are a distribution, not the exact count; the evaluation
document's `ci golden status` computes the exact count once the dev set exists.

Run (2026-10-28, Python 3.14.10, read-only over the tracked S1 results and the gitignored corpus
index): `python3 -I phase0_golden_size.py` → `out.txt` (`passed`).

## Result

| Scope | Packets, median (5–95 %) |
|---|---|
| Four spike pages whole plus the dev golden units by locator (adopted) | 234 (231–235) |
| Whole pages holding dev golden units | 1,655 (1,405–1,914), on 22–29 pages |
| Every non-test, non-reserved unit (the full first pass) | 3,826 (3,709–3,945) |

An earlier run of the same simulation reported about 245 and 2,100: it failed to match the forced
units (the S1 html5lib run's segment keys differ from the lxml-run keys in `locators.json`), so it
sampled 40 units instead of 27 beyond the forced 13. This run matches all 13 forced units. The
operator's choice of the unit-level scope (2026-10-28) holds on the corrected figures.
