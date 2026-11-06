# Reviews

Design and change reviews written by the `design-review` skill, usually through the
`design-reviewer` subagent. Evidence, never authority: a governed section changes only through the
ADR that responds to a finding.

- **Name:** `design_review_{slug}_{YYYY-MM-DD}.md`, using the template's numbered slots.
- **Findings:** `F01`, `F02`, … cited as `review#F01`; the binding's §4 says where their current
  disposition lives.
- **Retention:** a review stays while it supplies an open finding or needed decision evidence;
  then it is deleted and recovered from Git.

## Current unified-model target review

[Deepening the unified domain model](design_review_unified-domain-model_2026-11-01.md)
(2026-11-01) combines architectural comparison, eleven-library applicability and model-centered
functional opportunities. All targets remain Proposed; it consumes audit publication `cc2998d9`.

## Production enrichment improvements target review

[Evidence-grounded production enrichment](design_review_production-enrichment-improvements_2026-11-05.md)
(2026-11-05; recommendation-audit revision) integrates the refreshed production audit,
operator-supplied improved-M1 proposals and five new library addenda. Its
[net-change companion](audits/design_review_production-enrichment-improvements_2026-11-05_audit.md)
accounts for every original recommendation; the integrated review remains the planning input.
Target contracts, library mechanisms, assessment deltas and rule impacts remain Proposed; the separate
test-audit resolution scope is assumed complete for this target, not newly reported as implemented.
