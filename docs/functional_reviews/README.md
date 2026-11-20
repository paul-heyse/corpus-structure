# Functional opportunity reviews

Reviews here explore valuable additions or improvements to product, developer, operator and
research capabilities. The operator selects an outcome, workflow, subsystem or tooling/library
ecosystem; reviewers discover useful possibilities and assess their realization within that
scope. A prior diagnostic audit, existing caller or design-principle violation is not required.

Use [plan-functional-extension-review](../../.claude/skills/plan-functional-extension-review/SKILL.md)
for conversational preparation and [functional-extension-review](../../.claude/skills/functional-extension-review/SKILL.md)
for the review. Design principles shape proposed realizations alongside the functional-value
argument. The diagnostic [design-review workflow](../../.claude/skills/design-review/SKILL.md)
retains its separate audit prerequisite and review conventions.

## Outputs and traceability

The [JSON boundaries review](json-boundaries_2026-11-20.md) proposes one owner and a declared
value domain for each JSON role, and one meaning for each schema across Python and PostgreSQL.
O01–O11 cover the exact codec, identity bytes, a validator factory, a schema generator,
validating once, pydantic's scalar policy and configuration. It lists eleven confirmed defects
separately and states how the orjson review's opportunities carry forward. Recommendations
remain Proposed.

The [orjson and JSON codec review](orjson-json-codec_2026-11-20.md) recommends against
adopting orjson and keeps msgspec as a conditional replacement for python-rapidjson. O01–O07
need no new library: a declared value domain for identity bytes, separate owners for the uses
of canonical bytes, one response-size measure, `NaN` refusal at the worker boundary and
jsonschema number alignment. Recommendations remain Proposed.

The [cachetools and diskcache-community review](cachetools-and-diskcache-community_2026-11-20.md)
proposes bounded served rows as the first use of an unsharded persistent cache. It covers
generated program artifacts, process and disk composition, and cache diagnostics. Exact
workload custody remains with UDM.

The [agent CLI capabilities review](agent-cli-capabilities_2026-11-16.md) develops O01–O11 for
`ci` as a coding agent's working tool: pipe-first output, failure digests in the test report,
finding results without an ID, holds that name their consumer, a per-result table with source
currency and a two-run delta, change-partitioned diagnostics, working-tree code questions through
`ty` and the import graph, and worktree support. It rests on three days of Codex usage
[evidence](../design_review/evidence/2026-11-16_cli-agent-usage/README.md), declines a cross-run
SQLite store while history is out of scope, and names the earlier CLI recommendations it carries
forward. Recommendations remain Proposed.

The [agent CLI and diagnostics review](cli-and-logging_2026-11-10.md) develops O01–O08
from all ten Typer/Rich/structlog discovery leads and their conditional capabilities. Three
companions compare command authoring, correction/replay and correlated execution inspection.
Current code and the active DMC series ground the review; older CLI plans are complete/legacy.
Recommendations and benefits remain Proposed; implementation selection is separate.

The [integrated domain-data-model review](domain-data-model_2026-11-10.md) develops O01–O13
from all 14 DDM discovery leads and the additional conditional opportunities. Five companions
compare authoring, construction/archive, terminology/measurement, validation/graph and process
workflows. It corrects source premises about nested schemas and graph-report custody; all
recommendations remain Proposed and existing plans retain execution disposition.

Use `<subject>_<YYYY-MM-DD>.md` for the principal review, with its scope, inspected source
baseline and evidence limits near the beginning. Explain current capabilities, useful
opportunities, resulting behavior, concrete enabling mechanisms and precise sources, alternatives,
interactions and recommended priorities. Organize flexible Markdown around the argument; no
fixed field schema, feature count or complete ecosystem inventory is required.

Give opportunities stable references such as `O01`, cited as `review-path#O01`; explicit anchors
make these usable across documents. Preserve references when a recommendation changes, and
explain correspondence when opportunities split or combine. Link related diagnostic findings
when useful without requiring a finding or relabeling an opportunity as a defect.

A review proposes value and direction. It does not approve changes to the functional target,
rules or an existing plan, and it does not authorize installation or implementation. When selected
opportunities move into a plan, retain their source references and concrete mechanisms in the
relevant target and packages. The owning plan holds current scheduled scope and disposition;
unscheduled recommendations remain here with meaningful next decisions or revisit conditions.
There is no separate mutable opportunity register or required periodic refresh.

## Recommendation audits

Use [design-review-audit](../../.claude/skills/design-review-audit/SKILL.md) for a requested or
explicitly planned reassessment. It inherits this review's functional scope and assesses value,
scope, realization, interactions and missed opportunities. It does not initiate a broad diagnostic
audit or require the design-review report's full slot structure.

The [companion](audits/README.md) owns dispositions and net changes; the principal review is
revised in place into the complete resulting argument with dated attribution and recoverable
input. Planning consumes that clean integrated review. Editorial dispositions do not change
accepted implementation scope or plan progress.

Retain reviews and companions while they have current consumers. Follow the repository's
document lifecycle: carry surviving obligations and enduring knowledge to their owners before
retirement; Git preserves earlier accounts. Creating this scaffold performs no review or audit.

## Unified-model opportunities — 2026-11-01

The combined [unified-model target review](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md)
owns [O01 operation applicability](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O01),
[O02 semantic impact](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O02) and
[O03 actionable validation](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O03).
This engagement uses one principal report rather than duplicate opportunity text. These are
Proposed model-centered extensions; selection and implementation planning remain separate.


## First production milestone — 2026-11-03

The [M1 target-design review](m1-target-design_2026-11-03.md) develops O01–O07 for the proposed
five-family CPU-first release and stages O08–O11 as conditional or broader opportunities.
The [target package](../target-pipeline-design/README.md) holds the integrated detailed proposal.
These documents establish neither accepted implementation scope nor runtime qualification.

## Progressive corpus enrichment — 2026-11-04

The [progressive enrichment review](progressive-corpus-enrichment_2026-11-04.md) develops the
operator-selected revised target: independently retained structural contributions, operation-level
assessment and paired diffs, mathematical interpretation, parsing composition, contextual concept
linking and source-grounded dossiers. O01–O10 retain concrete mechanisms and proposed rule impacts.
The bounded retained-table comparison shows correct local structure inside unaccepted whole readings.
The review does not update active plans, change runtime contracts or resume stopped M1 execution.

## Typer CLI target — 2026-11-07

The [CLI functional extension review](typer-cli-target_2026-11-07.md) proposes O01–O07
for a routine development and production command surface, resolved context, managed results,
test reconciliation, terminal and machine output, controlled model changes and corpus operations.
The recommendations draw on observed Codex workflows and the eight introspection overviews.

## File-free CLI reporting — 2026-11-07

The [CLI reporting review](cli-reporting_2026-11-07.md) develops O01–O07 for direct owner-backed
reports, selected detail, typed pipes, and bounded Rich presentation. It prioritizes test
failure and coverage inspection and managed model preview reads. The review records the
installed broken-pipe behavior and the conditions for adding diagnostic capture.

## Next corpus enrichment increment — 2026-11-07

The [next enrichment review](next-corpus-enrichment_2026-11-07.md) reconciles both passes of
the supplied recommendations and details proposed source recovery, qualified roles, witnessed
links, artifact scoring, interpretation, attachment fitting and rooted delivery. O09–O12
develop GLiNER policy and additional library capabilities with explicit adoption conditions.
The crosswalk records the source recommendation dispositions. The WCE coordinator retains
execution and qualification status.

## Chandra 2 after Nemotron — 2026-11-08

The [Chandra functional review](chandra-2-post-nemotron_2026-11-08.md) evaluates
post-Nemotron recognition and new figure, chart, diagram and source-inspection
uses on Docling 2.148.0. It recommends starting with attributed visual evidence
and a typed read before considering governed promotion into the PDF product.

## GitHub visitor experience — 2026-11-08

The [GitHub visitor review](github-visitor-experience_2026-11-08.md) recommends a
visitor-first README, a traceable citation example, and a shared functional diagram.
It records tool and installation choices and the clean-checkout failures to resolve
before publishing the existing documentation site on GitHub Pages.

## Production milestone two — 2026-11-08

The [M2 functional extension review](production-milestone-two_2026-11-08.md) reconciles
both passes of the supplied target and recommends exact candidate profiles for HanLP,
Maverick, Dipo and d1-2B, with source-aligned composition, operation-level assessment,
and evidence required to enable conditional modes. O01–O09 and the baseline crosswalk
carry the recommendations into detailed planning.

## PostgreSQL typed-domain capabilities — 2026-11-09

The [PostgreSQL functional review](postgresql-typed-domain_2026-11-09.md) develops O01–O13
across released types, attributed SQL understanding, relational/retrieval operations, faithful
exchange, native inspection/evolution and operational control. Six companions compare complete
realizations and conditional future workflows. Its source crosswalk covers all38 discovery
shortlist entries,23 retained families and the inline observations/corrections. Recommendations
remain Proposed; active plans retain accepted implementation scope and disposition.

## Integrated primary text characterization — 2026-11-10

The [text-characterization review](text-characterization_2026-11-10.md) selects O01–O07:
shared linguistic/formal evidence, construction grammars with direct forest semantics, factorized
source readings, contextual characterization and complete consumer migration. Its feature crosswalk
disposes the full spaCy/Lark discovery collection, comparing existing HanLP, Maverick, Dipo, GLiNER
and d1 responsibilities. The finalized target remains Proposed; active plans retain execution scope.

## Book-processing efficiency and parallelism — 2026-11-11

The [book-processing review](book-processing-efficiency-and-parallelism_2026-11-11.md) develops
O01–O08: scoped preparation, immutable regional state, dependency-driven overlap, CPU processes,
resident provider lanes, batching, coordinated resource/device policy and operational control.
It recommends a local hybrid and identifies stage-barrier, admission and batch-attribution changes.
Recommendations remain Proposed; implementation planning and adoption are separate.

## Library-discovery tooling — 2026-11-17

The [library-discovery tooling review](library-discovery-tooling_2026-11-17.md) develops O01–O10
for a Typer and Rich tool under `tooling/` that supports the leverage-library-discovery skill:
an evidence envelope, baseline and installation snapshot, a Griffe inventory of what a library
offers, an `ast` and LibCST usage census, and their comparison with ty-reported deprecated use.
It finds ADR-0072's revisit trigger met and recommends a uv workspace member. Recommendations
remain Proposed; planning and adoption are separate.
