# Library leverage framework

**Implemented guidance · edition 0.3.** Three assessment stages share an optional library-led
entry. Discovery and design-quality benefits remain Proposed.

## Purpose and design judgment

Help capable programming agents identify where established library capabilities could improve
a codebase, investigate their applicability and recommend the best realization of each worthwhile
opportunity. Improvement can mean simpler ownership, fewer independent decisions, less generic
machinery, better execution, stronger guarantees or a valuable new capability.

The normal screening point is the codebase. Start from responsibilities, complete operations,
credible changes and intended workflows. Use those observations to focus library research.
Broad library overviews orient that research; a second, focused collection preserves the
resulting capability analysis without cataloguing everything each library might displace.

Use library-led discovery when a library family motivates the question. It starts from the family
and a repository objective, then relates a broad capability map to representative local usage and
identifies research priorities. The three assessment stages own separate judgments. Investigation
can iterate or enter directly at the stage warranted by the question.

| Stage and skill | Main judgment | Owns | Leaves for later |
| --- | --- | --- | --- |
| Optional `leverage-library-discovery` | Which capability families merit investigation here? | Contextual briefings, usage interpretation and proposed research priorities | Concrete opportunity evidence, applicability and comparative choice |
| 1. `leverage-codebase-audit` | A concrete responsibility or activity is worth investigating for library leverage | Current codebase opportunities, their evidence, preservation constraints and coverage | Whether a candidate capability fits, and which option is best |
| 2. `leverage-library-assessment` | Particular library capabilities could address an opportunity under stated conditions | Reusable library opportunity types and context-specific applicability assessments | Comparative selection of the best complete option |
| 3. `leverage-opportunity-review` | A particular realization is preferable here, or a decision remains unsettled | Comparative reasoning, recommended target, interactions and decisive unknowns | Accepted implementation scope, detailed work packages and execution status |

The third stage is a substantive review. It can deepen research, challenge earlier conclusions,
find another candidate and develop a bounded target design. A list of pairings or a ranking of
capabilities already admitted by stage two would be insufficient.

## The shared reasoning framework

The [base opportunity patterns](patterns.md) are a portable framework with stable `LOP-01`–`LOP-12`
identifiers. Each articulates a recognizable shape of work, why it may offer leverage,
mechanisms worth investigating and important counterconditions. Concern families locate the
subject; patterns explain the potential leverage. Neither is a checklist or an adoption gate.

The working pattern set combines these base patterns with additional patterns discovered and
maintained in assessment outputs. Discovery and the assessment stages use relevant additional
patterns on the same footing as base patterns. Their use needs no prior promotion into a
skill or the base framework. Additional patterns guide recognition and reasoning; they inherit
the same limits on treating a pattern match as evidence of fit or a requirement to adopt.

The framework applies across languages, libraries, services and native system capabilities.
It includes product behavior, domain algorithms, tests, developer tooling and operations.
Using a library within a domain-critical algorithm is compatible with retaining authority over
its domain meaning. Existing dependencies deserve early consideration without restricting the
search to mechanisms already installed.

The governing objective is better fulfillment of the intended responsibility with proportionate
total machinery. Source lines, dependency counts, novelty and altitude are supporting observations,
not measures of success. A small native operation can remove a large burden; a broad framework
adoption can introduce one.

## Concepts and collections

| Concept | Meaning | Primary home |
| --- | --- | --- |
| Leverage pattern | A generally recognizable opportunity shape, from the base framework or assessment discoveries | Base `patterns.md`; additional patterns in output `assessment-patterns.md` |
| Codebase opportunity | A concrete occurrence or related footprint worth investigating | `codebase/` |
| Library-led briefings | A family-level view of capabilities, representative usage and proposed research priorities | `libraries/<library>/briefing.md`, optionally supported by `briefings/*.md` |
| Library opportunity type | A reusable account of a focused capability, needs it can serve, mechanisms and limits | `libraries/<library>/` |
| Applicability assessment | A context-specific connection between an opportunity and one or more library types | That library's current applicability account |
| Comparative judgment | A reasoned choice among complete options for an opportunity or coherent group | `reviews/` |

A type describes, for example, selective data access or managed cancellation under particular
conditions. Its current applicability describes whether those conditions hold for an inspected
operation. The type remains useful when that operation changes or its opportunity disappears.

Use stable codebase IDs such as `CBO-001`, namespaced library handles such as
`example-library/selective-access`, and the original codebase IDs in review sections. One type
can serve several opportunities; one opportunity can use several types or a composed option.
Split or merge accounts when the meaning requires it, preserving identity and lineage.

## Discover and collect additional patterns

During the initial codebase inquiry, assess whether the working patterns adequately frame the
responsibilities, operations and opportunities encountered. During library applicability work,
reconsider that framing against what the library can actually do: a feature, composition or
semantic distinction may reveal an omitted opportunity shape or an insufficiency in the original
analysis. Comparative review can reveal the same gaps while assessing complete options.

When another framing would improve recognition or assessment, record or refine it in the shared
output `assessment-patterns.md`. Give it a stable `LOP-X001`-style ID, clear articulation,
recognition guidance, investigation questions and counterconditions at the depth it needs.
Explain what the existing patterns missed or obscured, its useful scope and the observations
that prompted it. A single revealing case can justify a reusable framing; no recurrence count
or quota applies. A specific occurrence or library feature can motivate a pattern without itself
being the pattern.

Keep one primary definition in that output and cite it from opportunities, library types,
applicability assessments and reviews. Each collection's entry page routes readers to it. The
discovering skill coordinates publication in the same pass, under the host's write-ownership
rules; read-only contributors return proposed text for the coordinator. Discovery can draw on
the shared patterns when framing research questions. The assessment stages own pattern maintenance.

Use new or refined patterns to reconsider the affected observations, research questions and
candidate capabilities within the inquiry. Follow the actual significance into adjacent work
where needed, without automatically restarting completed assessments. A pass may find the
current patterns sufficient. The purpose is useful expansion and correction, not producing new
patterns for their own sake.

Retain useful additional patterns after their originating opportunities and matches disappear.
Correct, merge or retire a pattern when its framing is misleading, redundant or obsolete,
preserving identity and useful provenance. Keep the definition understandable without its old
occurrences. Record consumed pattern editions/revisions with the assessment's existing baseline;
do not imply that adding a pattern refreshes earlier assessments automatically.

Over time the operator can manually select helpful framings for inclusion in the base framework
and its skill guidance. Discovering agents update the output account rather than automatically
editing skills or base patterns. When promotion is separately selected, preserve the originating
ID and its mapping to the base ID so existing assessments remain interpretable. Promotion is a
maintenance choice, not a prerequisite for using an additional pattern.

## Skill and collection locations

```text
.claude/skills/                           active tracked process skills
  leverage-library-discovery/SKILL.md
  leverage-codebase-audit/
    SKILL.md
    references/tells.md                   optional search cues
  leverage-library-assessment/SKILL.md
  leverage-opportunity-review/SKILL.md
.agents/skills -> ../.claude/skills        existing Codex discovery route

docs/library_leverage/
  README.md                              workflow and current-account routes
  library-leverage-framework.md           responsibilities and repository binding
  patterns.md                            portable base recognition framework
  references/
    discovery-and-evidence.md            briefing and evidence guidance
    shared-language.md                    one authored vocabulary
    collection-writing.md                 flexible record and maintenance guidance
  assessment-patterns.md                  shared additions; created on first discovery
  codebase/                               current opportunity account
    README.md                             synthesis, baseline, coverage, opportunity index
    <topic>.md                            concrete opportunities, grouped coherently
  libraries/                              focused library assessment account
    README.md                             researched libraries, type routes, coverage
    <library>/
      README.md                           focused type index and version coverage
      briefing.md                         complete discovery or summary and reading route
      briefings/                          optional focused discovery briefings
        <topic>.md                        supporting analysis grouped as useful
      <opportunity-type>.md                reusable capability analysis
      applicability.md                    current contextual matches, when large enough
  reviews/                                comparative judgment account
    README.md                             current recommendation synthesis and input scope
    <topic>.md                            options, target recommendations, unresolved choices
```

The collection entry pages route to current accounts. Create topic documents when they have
content and readers. A small library can keep its types and
applicability in its README; split when independently useful explanations warrant it. Topic
boundaries follow coherent responsibilities, operations or opportunities, rather than requiring
matching category trees across all collections. Several opportunities can share a review when
their options must be judged together.

The additional-pattern output is shared across the three collections and lives outside the
skill package. Its definitions are maintained once; collection indexes expose a route rather
than carrying their own copies. Until an assessment discovers a useful addition, no empty
pattern account or invented pattern is required.

The skills link to shared guidance under `references/` in this collection. Keep that
guidance authored once. Tracked skill directories are allowlisted in `.gitignore` and use the
existing shared discovery route; central library-specific skills remain inactive references.

## What each collection must make understandable

### Codebase opportunity account

Explain the system's relevant responsibilities and direction, its current mechanisms, and the
opportunities that deserve investigation. For each opportunity, connect representative source
evidence to the operation, relevant patterns, possible value and constraints on a better realization.
Include contrary evidence and distinguish inspected manifestations from a suspected wider footprint.

Differentiate current promised behavior, accepted planned work and proposed functional additions.
Tests and callers reveal dependencies; they do not make every observed quirk a preservation
requirement. Identify unsettled interpretations. Library names are useful research leads, without
being prerequisites for identifying an opportunity or binding adoption choices.

### Library assessment account

Optional [library-led briefings](references/discovery-and-evidence.md) provide contextual
orientation and proposed questions. The entry `briefing.md` may hold the complete discovery or
synthesize focused briefings under `briefings/`. Agents choose organization and depth to explain
the opportunities. Discovery can precede a concrete opportunity and links to reusable types when
available. Applicability judgments belong to focused assessments.

Research focused capability families in response to codebase opportunity questions. Use the existing
overviews for awareness and choose reference sources according to
[AGENTS.md](../../AGENTS.md#library-knowledge-and-reference-sources) and the uncertainty being
resolved. Empty searches and absent overview sections do not establish missing functionality.

Reusable types explain recognizable needs and code shapes, concrete APIs or features, composition,
obligations the library discharges, residual obligations, version conditions and important limits.
Type explanations remain independent of repository particulars. Keep exact local paths, runtime
pins and opportunity references in the separate applicability portion.

Applicability assessments explain the actual fit to the inspected opportunity, any required
configuration or extension, the remaining contract gap and what is unsettled. Separate capability
availability from local applicability and from eventual superiority. Preserve useful negative
results with their exact semantic conditions, rather than claiming a library never supports a need.

### Comparative review account

Compare credible complete options: library capabilities alone or composed, existing repository
facilities, native system functionality, deliberate custom work and version changes where relevant.
Inspect deeper code and library details when they could change the choice. Current library types
are accumulated knowledge, not an admission list limiting the reviewer.

Recommend a bounded target with concrete mechanisms, responsibility boundaries, retained domain
rules, material behavior changes, consumer effects and a credible execution route. Explain which
machinery disappears, remains or is introduced across preparation, normal use, failure and change.
Use relevant design principles and heuristics, a revealing legitimate case and material alternatives.
Reason qualitatively; quantitative benefit claims require measurements.

Assess interactions between recommendations: alternatives, prerequisites, shared capabilities,
conflicts and opportunities that are better addressed together. Rank attention by consequences
and value while keeping prerequisite order distinct. A review can recommend retaining current
code, reject an opportunity's premise or leave a consequential choice unresolved with a clear
settling question. Applicability alone does not establish the best choice.

## Evergreen maintenance with asymmetric retention

All three collections describe their current account in place. Each records its inspected date,
source or library baseline, included dirty changes, relevant criteria edition and coverage limits.
Distinguish the inspected baseline from the Git revision publishing the assessment. A focused
refresh updates its actual scope; inherited conclusions retain their evidence dates and limits.
Git preserves previous accounts. No per-pass directory or accumulating review diary is required.

| Material | Retention and retirement |
| --- | --- |
| Codebase opportunity | Keep while the underlying opportunity is relevant, including while work is scheduled. Remove on evidence that it was resolved, withdrawn on corrected premises, superseded or no longer worth retaining. Choosing or rejecting one library does not resolve it. Preserve removal reasoning and evidence in Git; never reuse its ID. |
| Library-led briefings | Refresh the summary and affected focused briefings in place when relevant objectives, usage or available capabilities change. Keep inherited evidence dated, make differing source conditions explicit and explain changes to research priorities. |
| Reusable library type | Prefer growth, correction and deeper explanation. Retain when every current match disappears. Correct, merge or retire a type when its account is false, redundant or obsolete; retain an explicitly version-scoped account when older supported use still has a reader. Current unmatched status is never a retirement reason. |
| Additional assessment pattern | Retain a useful framing independently of its current occurrences. Refine, merge or retire for substantive reasons; preserve references on manual promotion into the base framework. Its original opportunity retiring is not a retirement reason. |
| Contextual applicability | Refresh when code, guarantees, configuration, library realization or other consequential premises change. Remove obsolete current matches when their codebase opportunities retire. Carry justified reusable lessons into the type, with their original evidence scope. |
| Comparative judgment | Refresh material assumptions and options while it informs a current opportunity or downstream decision. Retire when it loses its last consumer, after carrying surviving mechanism choices and obligations into their proper owners. |
| Evidence | Retain while an assessment or decision consumes it. Keep original failed/interrupted records and evidence limits; archive history through Git under existing repository conventions. |

Before retiring an opportunity, reconcile incoming links in the library applicability and review
accounts. Remove obsolete live links; preserve useful provenance as a source revision plus its
original path and anchor. Reusable type content must remain understandable without the retired
opportunity. This needs ordinary document editing, not a dependency registry or maintenance daemon.

Discovery owns briefings. The audit owns current opportunities, library assessment owns focused
capability analysis and local fit, and review owns comparative reasoning. Accepted plans own
scheduling, progress and closure evidence.
Link to the execution owner without mirroring its mutable status. A favorable review or accepted
decision is not implementation evidence.

## Repository binding and downstream use

These collections live under `docs/library_leverage/`. The broad overviews remain under
[docs/libraries](../libraries/README.md). Use the current
[design standard](../design_review/design_principles/standard.toml), its relevant principles,
heuristics and profiles when judging substantial options. The patterns guide discovery and add
no acceptance gates or alignment lints.

The existing review and planning routes retain their authority. The comparative review develops
a target recommendation sufficient to inform the next decision. A functional addition can need
the existing functional review; a consequential architectural choice can need formal design
review at its declared cadence. Use a single coherent engagement where the required assessments
can be satisfied together. A leverage opportunity audit does not substitute for the diagnostic
audit required by that formal design review. Installing or ordinarily using library APIs
initiates neither audit.
Selected scope proceeds through existing planning and decision routes; the third skill does not
authorize implementation or automatically initiate an additional review.

Probes follow the established evidence route:
`docs/design_review/evidence/YYYY-MM-DD_library-leverage-<topic>/`, with a README stating the
question, inspected source/environment, command, outcome and limits. Add evidence only when it
settles a real uncertainty. Link immutable recorded run artifacts instead of copying their payloads
into assessment prose. No probes, provider runs or benchmark campaign are required merely to
complete one of these skills.

For agent coordination, brief the intended result, scope, current source and consumed assessment
revisions, open assumptions and output ownership. Read-only contributors return evidence and
judgments for the collection coordinator to reconcile. Explicit ownership protects concurrent
writes; questions need not wait for a later scheduled pass. The third-stage reviewer should have
room to challenge earlier assessments rather than being briefed to justify their preferred option.

## Basis and limits

This workflow adapts the living-account approach of the
[design-principle audit](../../.claude/skills/design-principle-audit/SKILL.md), with different
retention for accumulated library knowledge. It preserves the original proposal's needs-based
join, inverse recognition and attention to complete responsibilities, while making applicability
and comparative selection distinct. The project's architecture and current ADRs own local
adoption rationale and its relationship to existing review policy.

Related research supplies discovery leads, not validation of this process. [Prefactory](https://arxiv.org/html/2607.17211v1)
studies localized behavior-preserving library refactoring and explicitly excludes architectural
changes. [Xu et al.](https://ink.library.smu.edu.sg/sis_research/4500/) discuss library awareness
and reasons for reuse or reimplementation. The usefulness of these particular skills and pattern
families for agent-led architectural discovery remains Proposed until assessed through actual use.
