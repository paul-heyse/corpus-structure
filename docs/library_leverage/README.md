# Library leverage

**Implemented guidance.** A codebase-first assessment workflow with an optional library-led
entry and evergreen collections. Benefits to discovery and design quality remain Proposed.

Start with the [framework](library-leverage-framework.md) for responsibilities, handoffs, collection
paths and retention. Read the [base opportunity patterns](patterns.md) with additional patterns
from `assessment-patterns.md` when that output exists. All stages use relevant additions on the
same footing; promotion into base guidance is a manual operator decision.

| Skill | Question it answers | Collection it maintains |
| --- | --- | --- |
| [leverage-library-discovery](../../.claude/skills/leverage-library-discovery/SKILL.md) | What can this library family do, what do we use, and what warrants investigation? | [Library-led briefings](libraries/README.md#library-led-briefings) |
| [leverage-codebase-audit](../../.claude/skills/leverage-codebase-audit/SKILL.md) | Which concrete responsibilities and operations deserve investigation? | [Codebase opportunities](codebase/README.md) |
| [leverage-library-assessment](../../.claude/skills/leverage-library-assessment/SKILL.md) | Which focused library capabilities could address those opportunities, under what conditions? | [Library assessments](libraries/README.md) |
| [leverage-opportunity-review](../../.claude/skills/leverage-opportunity-review/SKILL.md) | Which complete option best addresses each opportunity, and why? | [Comparative reviews](reviews/README.md) |

## Use the workflow

Invoke the relevant skill with the intended scope, for example:

- `$leverage-library-discovery` — brief a selected library family against a repository objective
  and identify research directions. Start here when a library motivates the question.
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

The [spaCy and Lark text-characterization discovery](libraries/text-characterization/briefing.md) (2026-11-10)
explores a comprehensive source-aligned foundation of fundamental language and formal units,
followed by conceptual composition and analytics. Eight integrated leads connect complete
overview coverage, current retained products, five textbook journeys and broader library
compositions. Benefits remain Proposed; current plans retain their own dispositions.

The [agent CLI and diagnostics discovery](libraries/cli-and-logging/briefing.md)
(2026-11-10) connects Typer, Rich and structlog across command authoring, report delivery,
failures and execution boundaries. Ten research leads use current code and the active
domain-data-model series; older CLI plans are complete/legacy. Benefits remain Proposed.

The [integrated domain-data-model discovery](libraries/domain-data-model/briefing.md)
(2026-11-10) connects nine data-model overviews to current executable declarations, typed
boundaries, ontology/vocabulary use, qualified graphs, portable validation and settings.
It includes 14 capability leads, concrete broader-use directions and complete overview coverage.
Benefits remain Proposed; applicability and comparative selection remain follow-up work.

The [PostgreSQL library-led discovery](libraries/postgresql/briefing.md) (2026-11-09)
connects nine library overviews to typed-domain design, existing adoption, concrete underuse
candidates and conditional capabilities. Its own source baseline and seven topic companions
leave the older assessment dates and implementation-plan dispositions intact.


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

The [comparative review](reviews/README.md) collection has its first account (2026-10-29). It
consumes codebase publication `d739b88` (premises refreshed through `c13fbb0`, adding CBO-025) and
library publication `4c6d7f6`, with reviewers finishing at source `0350a7a`. It holds:
- a recommendation for each of CBO-001 to CBO-025;
- the recommendations' interactions and prerequisite order;
- unsettled decisions, defects found and rule impacts for existing decision routes;
- additional patterns LOP-X008–X011 and refinements to LOP-X001, X002, X006 and X007.

Record inspected baselines and limits rather than treating empty collections as assessed, and add
patterns only when a framing is genuinely missing.

The shared [vocabulary](references/shared-language.md) and
[collection-writing guidance](references/collection-writing.md) support the assessment stages. Keep
reusable library types and useful additional patterns when their originating matches retire.
The library collection is distinct from the broad [capability overviews](../libraries/README.md):
it keeps contextual briefings alongside focused capability knowledge and applicability judgments.

The tracked skill source is `.claude/skills`, exposed to Codex through the existing `.agents/skills`
symlink and loaded directly by Claude Code. Discovery follows the repository's existing arrangement;
[official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)
describes repository skills and symlink support. Existing formal review, planning and implementation
routes retain their scope and authority under the [framework binding](library-leverage-framework.md#repository-binding-and-downstream-use).
