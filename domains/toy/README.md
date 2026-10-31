# Toy ownership domain

This pack demonstrates phase-0 extension through declarations and a query plug-in. Organization
identity uses case-sensitive registry IDs, so a shared trading name does not merge organizations.
The active input is `fixtures/toy/corpus/toy.pdf`, a small three-section PDF preserving the
fixture source text. Native section scopes and source-view policy route intact descendant
sections; the guideline excludes informational notice content from authored claims. The old
HTML profile and batches remain historical read controls, with no active HTML ingestion route.

`toy:share` is meaning-bearing and produces alternatives when values disagree; `toy:filing_ref`
is inert. `toy:reported` identifies attribution, so two cited sources produce separate claims.
The `asset_owners` view supports a finalize warning when another owner is reported for an asset.
Warnings preserve the ownership claims as stated.

`ownership_at(asset, date)` returns each ownership claim, evidence, its validity interval, and
`established`, `not_applicable`, or `unknown` applicability. Missing validity, symbolic bounds,
and incomplete dates remain unknown; a missing bound inside a declared interval is unbounded.

The corpus and authored submissions are in `fixtures/toy/`. The deterministic acceptance journey
initializes a project, completes a slice, submits through MCP, reruns, and asks generic and pack
queries. The pack increment requires no core-source edits or model regeneration.

`fixtures/toy/build_pdf.py` authors the active PDF from fixed source text using PDFium,
without Docling inference. Native conversion/provider qualification is separate from controlled
retained-input acceptance fixtures.
