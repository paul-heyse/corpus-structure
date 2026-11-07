# Documentation

For consequential design and implementation choices, read the
[design principles](design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](design_review/design_principles/core/efficient-architecture-heuristics.md) together.
Consider relevant patterns before physical choices become entrenched; use judgment rather than
a checklist or added proof machinery.

Start with the task, then read the owning contract and adjacent consumer. Expand scope when a
contradiction or dependency requires it; the whole corpus is not the default reading context.

| Task | Start here |
|---|---|
| Understand the system | [Architecture map](design/README.md) → relevant owner |
| Resume work | [STATUS](../STATUS.md) → the relevant active plan in [plans](plans/README.md) (queue, open findings, qualification boundary) |
| Run supported repository or corpus operations | [ci skill](../.claude/skills/ci/SKILL.md) → the relevant workflow and result handling |
| Audit design-principle alignment | [Audit skill](../.claude/skills/design-principle-audit/SKILL.md) → [living diagnosis](design_review/audit/README.md) |
| Audit test design and evidence | [Test audit skill](../.claude/skills/design-principle-audit-tests/SKILL.md) → [separate test account](design_review/test-audit/README.md) |
| Audit review recommendations | [Recommendation audit](../.claude/skills/design-review-audit/SKILL.md) → design or functional review's companion and revised principal |
| Audit plan completion | [Completion audit](../.claude/skills/plan-completion-audit/SKILL.md) → same owning plan |
| Review a design or implementation | [Review skill](../.claude/skills/design-review/SKILL.md) → [repository binding](design_review/design_principles/binding/corpus-structure.md) |
| Explore functional enhancements | [Preparation](../.claude/skills/plan-functional-extension-review/SKILL.md) → [functional-extension review](../.claude/skills/functional-extension-review/SKILL.md) → [opportunity review](functional_reviews/README.md), without a diagnostic audit prerequisite |
| Improve remaining plan scope | [Plan-improvement review](../.claude/skills/plan-improvement-review/SKILL.md) → [published assessment](plan_improvement_reviews/README.md) of the remaining change footprint; plan revision is separately instructed |
| Research a library capability | [Library overviews](libraries/README.md); choose sources using [library-research guidance](../AGENTS.md#library-knowledge-and-reference-sources) |
| Discover and assess library leverage | [Framework and skills](library_leverage/README.md) → concrete codebase opportunities → focused library applicability → comparative option review |
| Understand why a decision was made | Owner section's `> Decision:` line → [ADR index](adr/README.md) |
| Maintain this site | [Publishing operations](publishing.md) |

## Authority

The architectural collection owns accepted contracts and labeled targets. Current ADRs own
rationale and open choices; each active plan owns execution and the current disposition of its
scheduled findings ([plans](plans/README.md)); retained reviews hold dated evidence for open findings; STATUS links the
current checkpoint. Executable declarations own detailed implementation contracts.
Functional opportunity reviews live in `docs/functional_reviews/`, with net-change companions
under `audits/`. Selected opportunities retain their source references in the owning plan;
proposals and editorial dispositions do not approve implementation or change plan progress.
Standalone plan-improvement assessments live in `docs/plan_improvement_reviews/`; revising the
plan from a review is separately instructed.

The [library-leverage collections](library_leverage/README.md) separate current opportunities,
reusable library types and contextual fit, and comparative judgments. Shared additional patterns
are collected in outputs and used alongside the base set; manual promotion is separate. Plans
retain execution disposition. Collection entry pages begin explicitly unassessed.

The site derives navigation and search from the retained working set. **Current** is the default:
architecture, entry pages, the active standard and process, accepted decisions and selected work.
**Reference** contains proposals, supporting reviews and evidence, pins and guidance.
**Everything** searches both. A search result's scope is a reading aid, not a truth verdict;
evidence labels still apply. Local capability indexes are not bundled into the website.

## Historical recovery

Retired plans, reviews, evidence and ADRs are not part of the working set (ADR-0001); current
owners carry every surviving obligation, so recovery is never a reading prerequisite. To recover
a deleted path:

- Find the commit that deleted it: `git log --diff-filter=D --name-only --format=%h -- '<path or glob>'`
  (for an ADR id, `'docs/adr/NNNN-*'`).
- Show its last content: `git show <commit>^:<path>`; list a deleted directory with
  `git ls-tree -r --name-only <commit>^ -- <dir>`.
- Raw evidence is in Git LFS: `git lfs fetch origin <commit>^ --include=<path>`, then
  `git show <commit>^:<path> | git lfs smudge`.
