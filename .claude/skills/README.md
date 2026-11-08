# Skills

**Shared design guidance:** the [design principles](../../docs/design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](../../docs/design_review/design_principles/core/efficient-architecture-heuristics.md)
are used together by review, planning, execution and ADR workflows. Consider relevant patterns
before physical choices become entrenched; reuse settled decisions during execution and address
material open choices or revealed mismatches. No checklist, cost model or proof machinery is added.

Tracked process skills are visible to Codex through the `.agents/skills` symlink.

## Process skills (tracked in this repo)

Workflows for building this repository. Add skills for repeated work or an explicitly selected
workflow with concrete consumers.

| Skill | Use |
|---|---|
| [ci](ci/SKILL.md) | Use installed `ci` for supported operations and repair defects surfaced during assigned work |
| [`design-principle-audit/`](design-principle-audit/SKILL.md) | Refresh the broad diagnostic account for production or broad system review |
| [design-principle-audit-tests](design-principle-audit-tests/SKILL.md) | Audit test code, evidence and support in a separate living account |
| [`design-review-audit/`](design-review-audit/SKILL.md) | Reassess recommendations and omissions, publish net changes and revise the principal review |
| [`plan-completion-audit/`](plan-completion-audit/SKILL.md) | Assess claimed accepted scope and correct the same owning plan |
| [`adr/`](adr/SKILL.md) | Record or supersede a decision; amend the owning architectural section in the same commit |
| [`plan-design-review/`](plan-design-review/SKILL.md) | Plan an approach to the user's review goal, grounded in the local standard |
| [`functional-extension-review/`](functional-extension-review/SKILL.md) | Explore valuable product, developer, operator or research capabilities and compare their realization within the operator's scope |
| [`plan-functional-extension-review/`](plan-functional-extension-review/SKILL.md) | Prepare a capability inquiry without requiring a diagnostic audit or predetermined feature list |
| [`leverage-codebase-audit/`](leverage-codebase-audit/SKILL.md) | Identify concrete codebase opportunities using base and assessment-discovered patterns |
| [`leverage-library-discovery/`](leverage-library-discovery/SKILL.md) | Brief a selected library family's capabilities, local usage and promising research directions |
| [`leverage-library-assessment/`](leverage-library-assessment/SKILL.md) | Research focused library applicability and accumulate reusable capability types |
| [`leverage-opportunity-review/`](leverage-opportunity-review/SKILL.md) | Compare complete options and recommend bounded target designs |
| [`design-review/`](design-review/SKILL.md) | Review explicit domain models, ownership, contracts, change scenarios and qualitative workload execution fit against the layered design standard (`docs/design_review/design_principles/standard.toml`); cadence in the corpus-structure binding |
| [`design-review-code-intelligence/`](design-review-code-intelligence/SKILL.md) | The code-intelligence profile, loaded with `design-review` |
| [`plan-creation/`](plan-creation/SKILL.md) | Plan the authoring approach from a review or existing plan, including focused assessment of foundations |
| [`create-plan/`](create-plan/SKILL.md) | Write the design and execution plan, including foundation improvements and an adaptable structure |
| [`plan-execution/`](plan-execution/SKILL.md) | Develop the approach to carrying out an existing plan |
| [`plan-improvement-review/`](plan-improvement-review/SKILL.md) | Review the remaining change footprint for design-principle alignment, general enhancements and execution improvements that fit coherently into the plan |
| [`execute-plan/`](execute-plan/SKILL.md) | Carry authorized scope through implementation, review, functional verification and handoff |
| [`handoff/`](handoff/SKILL.md) | Rewrite STATUS.md from the actual tree at session end |
| [`pin-check/`](pin-check/SKILL.md) | Add, bump, hold or release a dependency pin |

In Codex, use `/plan $plan-design-review <goal>`, `/plan $plan-creation <reference and goal>` or
`/plan $plan-execution <plan and scope>` to develop the approach. Leave Plan mode to perform the
work with `design-review`, `create-plan` or `execute-plan`; invoke the work directly when the
approach is already clear. Planning companions also work conversationally and do not switch modes.

The [suggested plan outline](create-plan/references/plan-structure.md) is adaptable. Existing plans
remain the durable owners of packages and receipts. The prepare/perform pairs use the
[shared agent roles](../../.agents/roles/README.md), which own coordination principles, briefs,
delegated decision scope, context loading and escalation. AGENTS.md owns local operating rules.
The coordinator remains accountable for design coherence, integration and acceptance. Shape
contributions around useful outcomes, shared decisions and readiness for the requested result.

A [living diagnostic audit](../../docs/design_review/audit/README.md) precedes a new diagnostic solution-review
engagement about production or broad system scope. The operator selects holistic, library-targeted, principle-focused or combined focus;
reviewers choose methods and depth. Recommendation and completion audits are deliberate requested
or explicitly planned assessments, not automatic slice checks. Reviews own reasoning, plans own
scheduled disposition, and a completion audit corrects that same plan.

Functional enhancement has a separate entry point: `plan-functional-extension-review` /
`functional-extension-review`. The operator selects the exploration scope; useful capabilities
need no diagnostic finding or existing caller. Design principles shape their realization.
[Opportunity reviews](../../docs/functional_reviews/README.md) can feed the same planning and
execution workflow. Recommendation auditing preserves their value lens and publishes a
[functional companion](../../docs/functional_reviews/audits/README.md) plus the integrated review,
without importing the diagnostic audit prerequisite.

The [library-leverage framework](../../docs/library_leverage/README.md) offers an optional
library-led briefing alongside its three assessment stages. Identification establishes
concrete opportunities and constraints; applicability research accumulates reusable library
types and contextual fit; comparative review judges complete options and bounded targets.
All stages use base and additional output patterns together. Useful types and patterns survive
retirement of current matches, while promotion into base guidance is manual. Existing plans
retain execution disposition; formal review cadence and implementation authorization remain.

Plan improvement uses `plan-improvement-review` at a requested or explicitly planned boundary.
Its scope is the remaining change footprint, including components substantially modified to
accommodate the plan. It actively assesses design-principle alignment and general enhancements
on their own merits, with recommendations judged for coherent integration. Publish a standalone
[plan-improvement review](../../docs/plan_improvement_reviews/README.md); updating the plan from
it is separately instructed. It has no broad audit prerequisite and does not replace a formal
review due under the binding or automatically change accepted scope.

## Inactive central library-skill references

Central library skills are no longer selected, synchronized, discovered or required here. Retained
links in an existing project's index can identify historical references without an installed skill.
Do not rewrite old plans merely for this transition. New capability research chooses sources according to
[AGENTS.md](../../AGENTS.md#library-knowledge-and-reference-sources) and the uncertainty being resolved;
[library overviews](../../docs/libraries/README.md) provide optional capability orientation.

| Reference | Former indexes | Source |
|---|---|---|

Test-only diagnostic reviews use the [test account](../../docs/design_review/test-audit/README.md);
mixed scope identifies applicable accounts under the binding. Load the selected
[test-assessment companion](../../docs/design_review/design_principles/core/test-assessment.md)
when tests or their evidence are in scope. Neither installation nor ordinary test editing
initiates an audit, and each finding retains one primary home.
