# Token-form parity fixture

`token_form_spike_pages.jsonl` holds one row per math span of the four spike pages
(`special/LocationScale.html`, `special/Normal.html`, `special/LogNormal.html`,
`special/Gamma.html`): 918 rows of `page`, `start`, `end`, `latex`, `macros` (the span's effective
macro table, each entry `{nargs, body}` with an optional `default`) and `token_form`.

**Provenance.** Copied unchanged on 2026-10-28 from the design spikes' I-R2 output,
`docs/design_review/evidence/2026-10-28_design-spikes/results/i_r2/token_form_spike_pages.jsonl`
(written by the revised spike `mathgrammar`, which implements D1 §6.2's token-form rules
independently of the product; execution plan cross-boundary decision 1).
sha256 `6ef886422275a5098c7dcae6757403539827850a450719e960ace7ab639ee9bf`, identical for the source
and this copy at the time of copying.

**Use.** `python/corpus-structure/tests/core/test_tex.py` reproduces every row with
`core/tex.py`. The two implementations share no code. A disagreement is decided by D1 §6.2, and the
side that changes is recorded. Replace this file only together with a new provenance line here.

**Coverage limits.** The four pages define no macro that takes arguments; the rows hold one
environment, 7 spans with sizing commands and 3 with text-mode arguments. The rules these rows do not
reach (arguments, optional defaults, the depth and size bounds, delimiter edge cases) are covered by
the module's own tests.

A deliberate change example is a new rule for an argument-bearing macro: write the proposed
old/new token forms and source macro definition, decide the meaning under D1 §6.2 independently
of `core/tex.py`, and select a new versioned reference for the affected `tests/core/test_tex.py`
consumer. A product rerun supplies a candidate diff, not its adjudication. Preserve this frozen
918-row witness and its provenance. An exact dependency pin is not an oracle hold; add a
`docs/pins.md` hold only when a concrete active comparison requires that version, with a revisit
condition.
