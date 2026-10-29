# Toy ownership domain

This pack demonstrates phase-0 extension through declarations and a query plug-in. Organization
identity uses case-sensitive registry IDs, so a shared trading name does not merge organizations.
`toy:clause` is claim-bearing; `toy:notice` is not. The source profile has paragraphs and sections,
with no unit containers or synthesized proof relations.

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
