# S0 and S1 — disposition of the design owner's review

**Date:** 2026-10-28. **By:** the in-repo agent, which holds primary design authority from this
date (operator direction). **Answers:** [design-owner-review-S0-S1.md](design-owner-review-S0-S1.md).
Every item below is now in the design documents or the findings table of
[design-phase_2026-10-28](../../../plans/design-phase_2026-10-28.md). The project-conversation
reviewer's next pass checks for missing design reasoning.

## Positions taken where the review and this response differ

| Item | Review | Decision |
|---|---|---|
| B9 | Write the retention ADR now | Deferred. The operator will propose the evidence system and wants to continue before settling it; the AGENTS.md override (never delete plans or evidence) is in force. Findings row EVID-01 |
| A3 | Port the instruments into `evaluate/` | Pipeline methods (M01, M03, grammar, M13, quote cascade, reference compiler, rules) are listed in D9 §7. Where the alignment and scoring instruments live long-term waits on the operator's evidence-apparatus design. Row APPARATUS-01 |
| A12 | Rerun with html5lib before M01 is frozen | Done now, before S2/S3. The renditions are content-identical on all seven S0/S0-R2 pages; `attrs.sourceline` is ruled a diagnostic outside the contract (D1 §3.2). Only keys differ, so the spikes keep the libxml2 renditions and phase 0 re-stores from model-facing batches (records s1.corpus-html5lib, s1.rendition-identity). Row RENDITION-01 |
| A1 acceptance | Reproduce "28,948 ok and 8 partial" | Split in two: delimiting reproduces the 8 `partial` spans; grammar coverage is reported per page and is not a gate (D9 P0.5b) |
| A7 RG-1 | P0-blocking | OPEN-D1-5: the `extref` shape is decided early in phase 0, before consolidation is built; it does not block writing the phase 0 plan |
| B1 fix | Token form for keys | Adopted (ADR-0012, superseding ADR-0009; ADR-0009 kept, marked superseded), with one addition: sizing commands (`\big` and family) are removed by token normalization. Measured: 4 of 881 parsed spike-page spans differed between the forms, all at `\big/` |
| B2 check | "Likely no change" in SV and HV | Not so: SV, HV and the S0-R2 adjudicator followed v1's wording on T4 and named σ `shape`; the reference and the trace use `sigma` plus a role claim. The reworded rule (first naming phrase) is adopted; part of the passes' T4 loss was the rule's defect (D2 §10.4 status line) |
| B4 | Choose how `family_profile(normal)` answers T2 | From the `FamilyParameter` entities, whose identity names the family, and C4–C5; `family_profile` lists parameters from entity identity as well as `has_parameter` claims (D8 §5.2, §5.3) |
| A10 | Score context premises once | Adopted, sequenced after B3: it relies on the premise's statement keying the same in every unit |
| A11 | S0-R2 procedure for every rule revision | Adopted for rule-class changes; the held-out units are fresh each time, and Haiku is a clarity probe, not an author (D7 §2) |

## Where each item went

| Item | Where |
|---|---|
| A1, B10 | D4 §3 (M09, M11's grammar part, M13 in phase 0); D6 §2 phase 0 stage list; D9 P0.5b and P0.6 stages |
| A2 | D9 P0.4 (annotator-reference compiler, `guideline:` warnings), P0.7 (golden tools serve inputs, record model and inputs), P0.10 (reserved pages) |
| A4 | D7 §3.1 (reserved Weibull; forced-dev spike pages, Pareto, ChiSquare); D3 `eval.document_split` |
| A5, B13 | D2 §12.1 profile (S1 additions, references, rendering conventions, orphan text); D4 M01 profile vocabulary with defaults; D9 P0.5 |
| A6, A8, B12, C | D2 §11 OPEN-D2-7 … OPEN-D2-20 (one row each); findings table |
| A7, C | D1 §13 OPEN-D1-5 (`extref`), OPEN-D1-6 … OPEN-D1-8 |
| A9 | D5 §3.5 (statements by kind, context premises), §4 (binding by guideline rows and first appearance), §9 (derived conditions) |
| A13 | D8 §3 output cap row; D4 §4.1 |
| A14 | Deferred table, with its trigger |
| B3 | D1 §10.1 statement key (anchor segment and first-sentence ordinal; context premise joins the existing statement); D5 §3.5; S6 recomputes the key figures |
| B5 | trace.md expected observations (M09 counts measured from `sample.json`, M10 ranges, M13 for T4) |
| B6 | D1 §12, D3 §10 `clm:C2` |
| B7, B16 | D3 `eval.golden_pass.model`, `.inputs`; `eval.golden_item.context`; D7 §3.2 (M13 is the one pipeline output), §5.4 (scope accuracy caveat) |
| B8 | D8 §2.1, §2.2 |
| B11 | D1 §5.2: `posed` reserved until `asks_for` (OPEN-D2-15) |
| B14 | docs/pins.md: pylatexenc 3.0b2 hold |
| B15, D | Spike README and briefs S2–S7 |
| E | Q8 row lists the five owed ADRs; findings dispositions as the review asked (OPEN-D1-3 reworded rule, HTML-07 merged, OPEN-D2-9 split) |
