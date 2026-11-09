# Matched interpretation development comparison

This investigation supports [PM2-07](../../../plans/production-milestone-two/gliner-and-d1-interpretation.md#PM2-07)
and [PM2-11](../../../plans/production-milestone-two/textbook-assessment-and-adoption.md#PM2-11).
The existing Standard and Nemotron source product 1627, five named opportunities on four
of its views, and retained parser run 421 supply the bounded comparison. The source-only
cut is 523/run 419. Both prediction arms use the same released questions under
`release:d79e9a624e59a449d549a933bc512c3fed2780c1198276596a486696084b727f`.
No new source intake, recognition, projection or Chandra work was used.

**Tested · 2026-11-09.** Two protected source-first V2 sets froze the literal and passage
controls (set 36, units 54–56) and the attachment controls (set 37, units 57–58).
Three distinct actors reviewed only the pinned source, with adjudication linking the retained
A/B pass IDs (passes 138–152). The [rubric](rubric.md) fixes complete probability magnitude
as the primary gain and preserves definition function and loss magnitude controls. The earlier
development exposure is explicit. The [source reviews](source-reviews.json) and
[protected passes](raw/protected-passes.json) are separate from the inference requests.

The incumbent is the same d1 adapter at method/operation version 1. Version 2 puts compact
request-local option labels beside the existing located evidence and role descriptions and maps
them back to the same retained candidate keys. It keeps the provider reply and a separately
typed decision. An exact, single native literal can support deterministic decimal normalization;
nonterminating, locale-dependent, composite, and unavailable values remain unresolved. No
configuration pin, released question declaration, or database schema changed. Scope and vocabulary
continue to come from the released questions and admitted source, whether the text is textbook
or procedural. GLiNER/M1 extraction supplies no same-question operation on these five focal
scopes, so no GLiNER head-to-head quality claim follows from this paired d1 comparison.

The `ci golden operation-create` invocations initially refused an invalid split spelling
and an incomplete sampling object. Their receipts remain in `raw/`; both corrected
invocations sealed native sets before either prediction arm started. The installed focused
command `uv run ci test --json -- python/corpus-structure/tests/semantic/test_pm2_interpretation.py python/corpus-structure/tests/methods/test_pm2_source.py python/corpus-structure/tests/semantic/test_contribution_composition.py`
passed all 24 selected ordinary tests (`8fa24c4c4c154f3b8ee7fbe785f93592`).

**Tested native pair · 2026-11-09.** `ci run interpret` completed the five version 1
scopes at run 429/cut 529 and the corresponding version 2 scopes at run 431/cut 531.
`ci eval run --comparison-arm` graded both against the same protected sets. The
[literal/function comparison](raw/set-36-comparison.json) is evaluations 38 and 40;
the [attachment comparison](raw/set-37-comparison.json) is evaluations 39 and 41.

| Source opportunity | Version 1 | Version 2 |
| --- | --- | --- |
| Definition function | Supported | Supported |
| Probability `1/8` per outcome | Located; complete structure unsupported | Exact literal and decimal `0.125` supported |
| Roulette loss magnitude | Complete structure unsupported | Located `1 dollar` wholly within the second native item; no exact standalone digit read or declared unit normalization |
| Fair-coin condition host | No match | No match |
| Referent of `She` | Missing candidate with `A gambler` offered | Missing candidate with the same candidate offered |

The primary normalization case improved and the supported definition control survived.
No new spurious case was recorded on this panel. The loss, host and referent remain
unresolved despite successful native operation settlement. This supports the bounded
normalization gain only. It does not qualify attachment selection, wider population gain,
calibration, new standing, or full-book adoption.

**Tested reviewed-candidate diagnostic · 2026-11-09.** Maverick run 432/cut 532
replayed only the exposed source scope with the independently located mentions `A gambler`
and `She` supplied. The first request used view-relative offsets where the adapter required
scope-local offsets and was correctly refused; both the refused request and the corrected
request are retained. Diagnostic d1 run 433/cut 533 used these supplied mentions and separately
asked the host question with only the reviewed assignment-frame alternative. Its
[Reader facets](raw/diagnostic-reader-facets.json) show both native operations succeeded,
but still no match for the condition host and missing candidate for the referent. This is
a changed-population diagnostic and stays outside the ordinary comparisons. Neither observed
miss can be attributed solely to the absence of a reviewed candidate in these scopes.

The [revised Reader](raw/revised-reader-facets.json) resolves the exact probability as
`source_exact` decimal `0.125` while the composition remains `retained_private`.
After the alias population check was made explicit and formatted, the same 24 focused
ordinary tests passed (`39d81c9ee7c241b387fc10f362f236d6`). Focused `ruff check` and
`pyrefly check` also passed. The retained native runs preserve their original runtime pins.

## Records

<!-- evidence-index:start -->
<!-- evidence-index:end -->
