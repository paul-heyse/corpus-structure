# I-B · Aligner verification (instruments plan §9)

**Done:** 2026-10-28 by the root. **Instruments:** `code/instruments/` after the review fixes
(implementation-reviewer on HEAD 83c5658: F1 core-matching dependence, F2/F3 SymPy shim, F4
fuzzy family labels, F5a–f; fixed by the instruments worker, 50 tests passed) plus one root fix
below. The review's findings, the worker's decisions and the test record are in
`instruments_tests.md`; the review itself was reported to the root and is summarized there.

## Hand alignment against the instrument

`trace_diff.md` was written by hand, before any instrument figure, from the trace's tables and
the two passes. `code/s0d_compare.py results/s0/trace_stored results/s0/stored/pass_a trace_vs_a`
(alignment in `compare/trace_vs_a/alignment.txt`) was then compared with it item by item.

| Hand difference (trace_diff) | Instrument on trace vs A | Agrees |
|---|---|---|
| d1 bindings of a, b | C2: diagnostic `bindings` | yes |
| d3 C2 premise `claim` condition | C2: full-tier failure `conditions` | yes |
| d4, d20 `defines` modality | C3, C4: `modality` | yes |
| d5, d21 formula with or without the generated variable | T1 C4 not core-matched (object differs); T4 C7 failure `transform` | yes |
| d7, d9, d13, d19 statement roles | `statement_role` failures on each | yes |
| d8, d24 `parameter_role` / `parameter_domain` only in the passes | prediction-only claims | yes |
| d10 unsupported only in the passes | unsupported 0 of (0, 1) | yes |
| d12 `has_parameter` only in the trace (T2) | C2, C3 reference-only | yes |
| d17 s5 only in the passes | entities Z, W, SN, SLN and their claims prediction-only | yes |
| d18 restrictions on premise vs conclusion | T4 C1 and C3: `conditions` | yes |
| d22 modality of list-item claims | C8–C10: `modality` | yes |
| d25 N.mean, N.sd only in the trace | reference-only entities | yes |
| d11 statement kind remark/narrative | statement entities aligned (0.90); kind is not a tier criterion | yes (by D7 §5.2) |
| d14 Y's symbol | entities aligned (symbol vs label) | yes |
| d16 `proves` anchored to the proof statement | not a tier difference | correct: D7 §5.2's full tier compares the statement *role*; the anchor enters only the claim key |
| — | T4 C5, C6, C10 `statement_role` (none vs definiens) | the instrument found what the hand diff grouped under d7 for T1 only; added there by reference |

No hand difference was missed by the instrument and no instrument difference was spurious.

## Root fix after the review

Local entities without a symbol were matched on their exact canonicalized label, so pass P's
"radius of the rod" did not align with the reference's "the radius of the rod" (U8). The
fallback when neither side has a symbol now compares labels after D2 §12.1's article rule
(`align.py`, local-entity similarity; test `test_symbolless_local_labels_drop_leading_article`).
A first version that replaced the symbol-or-label comparison broke the trace's Y (label
"a + b X") against pass A's symbol `a + b X`; the rule is therefore a fallback only. All
comparisons were rerun; only `ref_vs_p` changed (core F1 0.76 → 0.79, U8's two claims).

## Determinism and symmetry

A vs B gives identical F1 in both directions on all twelve units (`compare/a_vs_b/score.json`,
`symmetrized`: no asymmetry flagged). Every value comparison on the S0 data was decided
canonically except three (one SymPy, two numeric, all "unequal", U8's numbers with and without
cm); none pending, so `manual_equivalence.tsv` is not needed. No fuzzy-label pair occurred.

Commands (2026-10-28): `code/tests_instruments/run_all.py` — passed (51 tests);
`code/s0d_compare.py` for trace_vs_a, trace_vs_b, a_vs_b --symmetric, ref_vs_{a,b,p,trace} — passed.
