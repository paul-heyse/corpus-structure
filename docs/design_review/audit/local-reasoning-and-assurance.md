# Local reasoning and assurance

This page originally held the findings on diagnostics, lineage, labelled claims and verification.
At the [audited baseline](README.md#baseline) (`ad4593f`, 2026-10-29), all three earlier findings
here are resolved. The current findings on these concerns have their primary homes elsewhere,
according to their structural causes:
- **Design claims and their authority:** [DA-011](semantic-model-and-authority.md#da-011).
- **Outcomes, refusals and diagnostics:** [DA-013](structure-and-invariants.md#da-013) and
  [DA-041](structure-and-invariants.md#da-041).
- **Native lineage and deployment identity:** [DA-032](native-integrity.md#da-032).
- **Verification that re-runs the producer:** [DA-042](execution-fit.md#da-042) and
  [DA-033](execution-fit.md#da-033).
- **Evaluation non-circularity:** [DA-037](served-claims.md#da-037).
- **Mirrored recipes without conformance:** [DA-009](semantic-model-and-authority.md#da-009).

Test architecture and test evidence belong to the separate [test audit](../test-audit/README.md).

<a id="da-021"></a>

## DA-021 — Retired at this baseline

*Was: "Design claims cite evidence records by free text, so a superseded record keeps supporting a
label" (2026-10-28).*

Phase 0 corrected it:
- `tools/evidence/src/corpus_evidence/citations.py` checks citations as part of `just evidence`;
- the catalog derives from `Record`.

The superseded record id survives only in the immutable ADR-0013. Verified 2026-10-29 at `ad4593f`.
The earlier text is in Git.

<a id="da-022"></a>

## DA-022 — Retired at this baseline

*Was: "The dependency check covers less than AGENTS.md says" (2026-10-28).*

`scripts/check_pins.py` now checks every Python manifest of the uv workspace, as well as the Cargo
workspace (`:12-18`, `:62+`). Verified 2026-10-29. The earlier text is in Git.

<a id="da-023"></a>

## DA-023 — Retired at this baseline

*Was: "The binding's map of binding decisions is empty" (2026-10-28).*

The binding's §1 now lists §B1–§B6 with the principles and gates each bears on, reworded for the
pivot (`docs/design_review/design_principles/binding/corpus-structure.md`, §1). Verified 2026-10-29.
The earlier text is in Git.
