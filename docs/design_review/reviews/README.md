# Reviews

Design and change reviews written by the `design-review` skill, usually through the
`design-reviewer` subagent. Evidence, never authority: a governed section changes only through the
ADR that responds to a finding.

- **Name:** `design_review_{slug}_{YYYY-MM-DD}.md`, using the template's numbered slots.
- **Findings:** `F01`, `F02`, … cited as `review#F01`; the binding's §4 says where their current
  disposition lives.
- **Retention:** a review stays while it supplies an open finding or needed decision evidence;
  then it is deleted and recovered from Git.

## Declared data operations target inquiry

[Declared data operations](design_review_declared-data-operations_2026-11-12.md) (2026-11-12) is
an operator-requested design/target inquiry at product source `8c0f4f951`, written by the root
session, not an independent `design-reviewer` engagement; it consumes no refreshed audit. It
proposes one declared form for every data operation, with identity, eligibility and change need
derived from the declarations in place of run and runtime identity. It gives `F01`–`F09`,
corrections `C1`–`C7` and rule impacts `RC01`–`RC07`. Supporting pages hold the
[operations](declared-data-operations/operations-and-sequencing-baseline.md) and
[identity](declared-data-operations/identity-and-provenance-baseline.md) baselines, the
[design authority map](declared-data-operations/design-authority-map.md) and the
[target contracts](declared-data-operations/target-contracts-and-storage.md). Decision: Revise;
every remedy is Proposed, no decision record is changed, and every finding is Deferred until a
plan selects it.

## Test architecture and efficiency target review

[Test architecture and efficiency](design_review_test-architecture-and-efficiency_2026-11-12.md)
(2026-11-12) is a test-scope design/target review at `main` `784d86f11`, consuming test audit
publication `cf24c0e80`. It gives a target state and change set for all thirty DTA findings, adds
`F01`–`F03`, and proposes rule impacts `RC01` (ADR-0032) and `RC02` (default workers for narrowed
selections) for operator confirmation in plan creation. Its
[supporting inventory](test-architecture-and-efficiency/efficiency-opportunities.md) ranks wider
efficiency opportunities structurally, without measurement. Decision: Revise; every remedy is
Proposed and every open finding is Deferred until a plan selects it.

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


## PostgreSQL typed-domain assembled target review

[Assembled PostgreSQL typed-domain capabilities](design_review_postgresql-typed-domain-assembled_2026-11-10.md)
(2026-11-10) assesses the PTD-00–10 implementation and CA01–04 repairs against typed-domain and
PostgreSQL library-realization change scenarios. It consumes audit publication `044915435` at
source `8e69e2b5f`. Its architectural decision is Accept scoped; final provider/native qualification
and adoption remain owned by the PTD coordinator, not established by the review.
