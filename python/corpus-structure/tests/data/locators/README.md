# Locator fixture: the four spike pages

Thin fixture for `tests/core/test_locators.py` (ingest and math §3.1, §5 P0-I-0): one
`<page>.json` per spike page (`special/LocationScale.html`, `Normal.html`, `LogNormal.html`,
`Gamma.html`), each `{"page", "source_uri", "canonical_text", "document"}` with `document` the
nested segment tree that `RenditionContent` validates.

**Provenance.** Written by `build.py` (stdlib only, run from the repository root) from the frozen
S1 renditions in the [design-spikes evidence](../../../../../docs/design_review/evidence/2026-10-28_design-spikes/README.md):
`results/s1/canonical/<page>.txt`, `results/s1/segments/<page>.jsonl` and the source URIs in
`results/s1/renditions.json`, all last changed in commit `83c5658`. Those renditions were produced
by the S1-A adapter with lxml (records `s1.adapter`, `s1.rendition-identity`; the latter shows
html5lib gives identical canonical text and segments on these pages). The conversion drops the
spike's segment keys and the diagnostic attributes production segments do not carry (D1 §3.2:
`tag`, `sid`, `sourceline`, `roles`) and rebuilds the tree from the parent keys; text, kinds,
offsets, parse statuses and the remaining attributes are unchanged. The spike renditions have no
sentence segments and no macro table.

Committed output is the fixture's authority; rerun `build.py` only to change the conversion.
Production renditions replace this fixture's role when P0-I-1a's acceptance repeats the slice
locator check on them.
