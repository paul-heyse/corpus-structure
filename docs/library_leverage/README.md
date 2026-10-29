# Library leverage

**Implemented template guidance.** A codebase-first workflow with three distinct
repository skills and evergreen assessment collections. Benefits to discovery and design quality
remain Proposed; installation does not establish an assessed codebase or qualified library fit.

Start with the [framework](library-leverage-framework.md) for responsibilities, handoffs, collection
paths and retention. Read the [base opportunity patterns](patterns.md) with additional patterns
from `assessment-patterns.md` when that output exists. All stages use relevant additions on the
same footing; promotion into base guidance is a manual operator decision.

| Skill | Question it answers | Collection it maintains |
| --- | --- | --- |
| [leverage-codebase-audit](../../.claude/skills/leverage-codebase-audit/SKILL.md) | Which concrete responsibilities and operations deserve investigation? | [Codebase opportunities](codebase/README.md) |
| [leverage-library-assessment](../../.claude/skills/leverage-library-assessment/SKILL.md) | Which focused library capabilities could address those opportunities, under what conditions? | [Library assessments](libraries/README.md) |
| [leverage-opportunity-review](../../.claude/skills/leverage-opportunity-review/SKILL.md) | Which complete option best addresses each opportunity, and why? | [Comparative reviews](reviews/README.md) |

## Use the workflow

Invoke the relevant skill with the intended scope, for example:

- `$leverage-codebase-audit` — identify library-leverage opportunities in a selected operation,
  subsystem or the codebase.
- `$leverage-library-assessment` — assess selected opportunities against relevant capabilities,
  using the opportunity IDs and existing library analysis.
- `$leverage-opportunity-review` — compare complete options for those opportunities and recommend
  bounded target designs.

An end-to-end request can authorize all three stages. Coordinate their substantive handoffs and
iterate where new evidence changes a premise. A focused inquiry needs only the relevant scope;
ordinary implementation and API questions do not initiate this workflow.

## Current accounts

The [codebase opportunity account](codebase/README.md) has its first baseline (2026-10-29,
source `9f8df02`, reconciled through `f697233`). It holds 24 opportunities, with a forward view on
the semantic-model pivot's SP-08–SP-10 work. That pass also created the shared
[additional assessment patterns](assessment-patterns.md) (LOP-X001–X004).

The [library assessment collection](libraries/README.md) has its first baseline (2026-10-29,
source `d739b88`, consuming codebase publication `d739b88`). It covers:
- reusable opportunity types across 19 library accounts, prioritized by the libraries the project
  uses;
- an applicability conclusion for every CBO;
- additional patterns LOP-X005–X007 and refinements to LOP-X001–X004.

The [comparative review](reviews/README.md) collection remains unassessed. Record inspected
baselines and limits rather than treating empty collections as assessed, and add patterns only when
a framing is genuinely missing.

The shared [vocabulary](references/shared-language.md) and
[collection-writing guidance](references/collection-writing.md) support all three skills. Keep
reusable library types and useful additional patterns when their originating matches retire.
The library collection is distinct from the broad [capability overviews](../libraries/README.md):
its research starts with codebase opportunities and accumulates focused capability knowledge.

The tracked skill source is `.claude/skills`, exposed to Codex through the existing `.agents/skills`
symlink and loaded directly by Claude Code. Discovery follows the repository's existing arrangement;
[official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)
describes repository skills and symlink support. Existing formal review, planning and implementation
routes retain their scope and authority under the [framework binding](library-leverage-framework.md#repository-binding-and-downstream-use).
