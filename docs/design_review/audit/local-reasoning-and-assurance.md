# Local reasoning and assurance

Findings about diagnostics, lineage, labelled claims and verification: FP-06, DP-21–DP-23 and
CI-11. Baseline, scope and scenarios are in the [README](README.md).

Strengths that bound these findings:
- The key, TeX and locator tests use hand-written or relational expectations.
- The token-form parity fixture is independent of the product code.
- The database fixtures fail rather than skip.
- The evidence `Record` model is the single authority for records and validates supersession.

<a id="da-021"></a>

## DA-021 — Design claims cite evidence records by free text, so a superseded record keeps supporting a label

**Principles:** DP-22, DP-21, DP-01; CI-11 by analogy.
**Subject:** implemented (`tools/evidence`) and design text.

**Diagnosis.** The links from design claims to evidence records are record ids written in prose,
and `just evidence check` does not read them. For example, record `s0r2.scores` is superseded by
`s0r2.scores-ir2`, yet these still cite the old id (grep, 2026-10-28):
- DESIGN.md §B1 ("**Tested** … records `s0.gaps`, `s0r2.scores`");
- ADR-0013;
- D4 line 253;
- D7 lines 19, 157 and 396.

Inside the tool:
- `answers` and `consumed_by` are unchecked strings.
- `record.schema.json` is current, but `check` does not verify that.
- The catalog DDL mirrors the `Record` fields by hand (`catalog.py:18-41`).
- `render` lists as sources only records fetched through `record()` (`report.py:39-45`, `:79`).
  Figures read through `query()` or `value()` are untracked, and the S6 template calls `record()`
  in a hand-written loop to compensate.
- `Record.outcome` adds `partial` to AGENTS.md's reporting vocabulary.

**Consequence.** A result revised by supersession leaves the earlier labels standing, and a reader
cannot tell which record a "Tested" label now rests on.

**Counterevidence.** For I-R2 the superseding records left the figures unchanged, so these citations
are stale ids, not wrong claims.

**Leads:** let `check` resolve record ids cited in design text and ADRs and warn on superseded ones;
track every record a rendered report reads.

<a id="da-022"></a>

## DA-022 — The dependency check covers less than AGENTS.md says

**Principles:** DP-22.
**Subject:** implemented (`scripts/check_pins.py`, AGENTS.md).

**Diagnosis.** AGENTS.md says `just deps` checks that every registry dependency is pinned exactly.
`check_pins.py` reads only Cargo manifests. Python exactness rests on the `add-bounds = "exact"`
convention. Every Python manifest read on 2026-10-28 was exact.

**Consequence.** A hand-edited Python range would pass the stated check.

<a id="da-023"></a>

## DA-023 — The binding's map of binding decisions is empty

**Principles:** DP-24.
**Subject:** repository binding (`design_principles/binding/corpus-structure.md` §1).

**Diagnosis.** DESIGN §2 has binding decisions §B1–§B6, four of them with accepted ADRs. The
binding's §1 table still says "None yet". Reviews therefore have no route from a binding decision to
the rules and gates it bears on.

**Consequence.** The next design review reconstructs that mapping on its own.
