# Agent CLI and diagnostics: integrated library discovery

**Discovery, 2026-11-10; benefits Proposed.** Typer, Rich integrated with Typer,
and structlog. The operator selected combined discovery across the whole agent journey,
ending before contextual applicability assessment, comparative selection or implementation.

## Objective and authority

Improve the design, functionality and usability of command authoring and operation for Codex,
the intended editor and primary analytical consumer. Useful improvement includes fewer independent
decisions when adding commands, clearer discovery and input contracts, complete inspectable results,
actionable failures and correlated execution observations. Terminal decoration alone is not a goal.

[D8 §4](../../../design/D8-agent-and-query-interfaces.md#4-cli) and
[ADR-0069](../../../adr/0069-cli-operations-custody.md) own CLI meaning, effects and custody.
Operator clarification, 2026-11-10: older CLI plans are complete/legacy and are not active
constraints or disposition owners for this inquiry. Ground investigation in current code and the active
[DMC coordinator](../../../plans/domain-data-model_2026-11-10.md) and its
[companions](../../../plans/domain-data-model/diagnostics-and-graph-workflows.md).
That series owns concurrent report/domain
changes; this account neither schedules nor qualifies them.

## Baseline and evidence

| Item | Inspected scope |
| --- | --- |
| Source | `0a384a64ef022fb3ce874ac9180a1a89ebb82061`, main, 2026-11-10 |
| Worktree | Concurrent DMC changes to CLI output/failures/operations/schema/registry, typed reports, settings, semantic operations and tests; new research/interpretation commands and diagnostic artifacts. Inspected as provisional source, preserved; no qualification of those edits |
| Environment | Root uv workspace, default groups; Linux x86_64/glibc2.39, Python3.14.10 |
| Selected/installed | Direct Typer0.28.0 and Rich15.0.0, confirmed by distribution metadata and locked inverted dependency tree; Rich advertises the jupyter extra, which alone establishes no selection/use |
| Candidate | structlog26.1.0 is the reference release; no structlog distribution in the prepared interpreter and no imports/declaration found in the searched application/operator paths |
| Coverage | All three supplied overviews including addenda read end to end during planning; [coverage and conditional territory](coverage.md) |
| Follow-up | Representative consumers and tests, installed Typer/Rich implementation and release-matched primary structlog documentation. Topic briefings distinguish source observations from proposed broader use |

Metadata was read with `uv run --locked --offline --no-sync --no-python-downloads python -B`
using `importlib.metadata.distribution`; selection with
`uv tree --locked --offline --no-python-downloads --invert --package typer --package rich`.
Both completed successfully on 2026-11-10. No target-package imports or synchronization were needed
for metadata. Typer also arrives through Docling, spaCy and other dependencies; the root
override documents the Docling Slim constraint. Independent provider/evidence project source
was sampled separately; their environments and full lock graphs were not qualified.

Source search covered `python/corpus-structure/src`, representative tests, `scripts`, `tools/evidence`
and `services`. A scoped no-hit is not a runtime absence guarantee. The overview's older Typer0.27.3
observations are not automatically 0.28.0 contracts. Existing November7 journey evidence retains
its original date and scope; no runtime journey, provider run, benchmark or new probe occurred here.

## Research priorities

| Lead | Proposed direction and present interpretation | Detail |
| --- | --- | --- |
| CLI-01 | Broaden native typed input and modular command declarations where they remove repeated parsing or authoring decisions | [Command model](briefings/command-model.md#cli-01) |
| CLI-02 | Improve discoverability through existing help/reference metadata and selective contextual suggestions | [Command model](briefings/command-model.md#cli-02) |
| CLI-03 | Use parameter provenance and invocation-scoped resources where they complement existing settings and lifetime owners | [Command model](briefings/command-model.md#cli-03) |
| CLI-04 | Extend bounded semantic report projections with exact identifiers, source excerpts and useful hierarchy | [Reporting](briefings/reporting-and-diagnostics.md#cli-04) |
| CLI-05 | Make optional presentation compose safely with machine streams and current delivery semantics | [Reporting](briefings/reporting-and-diagnostics.md#cli-05) |
| CLI-06 | Preserve actionable exception structure with one presentation owner per destination | [Reporting](briefings/reporting-and-diagnostics.md#cli-06) |
| CLI-07 | Investigate structured events plus third-party stdlib logging only for a concrete diagnostic consumer | [Events](briefings/execution-context-and-events.md#cli-07) |
| CLI-08 | Correlate actual operation boundaries using scoped context and explicit process transfers | [Events](briefings/execution-context-and-events.md#cli-08) |
| CLI-09 | Project meaningful progress and summaries from existing authoritative observations | [Events](briefings/execution-context-and-events.md#cli-09) |
| CLI-10 | Reuse native capture/testing facilities while qualifying final streams and configuration lifetimes separately | [Events](briefings/execution-context-and-events.md#cli-10) |

Investigate CLI-04/05/06/07 together first: establish what the agent needs from a failed or partial
operation, what the current typed report already supplies, and which representation belongs on each
destination. That constrains console and logging composition before either acquires global state.
CLI-01/02 form an independent authoring/discovery track. CLI-03/08 connect settings, leases and
diagnostic context, while retaining their different authorities. CLI-09 depends on a useful missing
observation, not on a new progress renderer. CLI-10 supports all tracks without requiring tests merely
to prove diligence. This is attention order, not an implementation queue or adoption ranking.

Representative journeys are test failure → inspection → exact retry → coverage; preview/candidate →
managed inspection; command discovery → precise invocation → typed result; and long operation →
stage/status → interruption/recovery. MCP stdio and provider/subprocess execution are meaningful
adjacent boundaries. Source inspection can expose composition questions without performing effects.

## Judgment and handoff

The [functional review](../../../functional_reviews/cli-and-logging_2026-11-10.md) develops
eight Proposed opportunities from all ten leads and conditional territory. It also refines the
foreign-exception formatter warning. Recommendations do not select implementation scope.

Apply the [selected standard](../../../design_review/design_principles/standard.toml), especially
FP-01/03/04/06/07, DP-06/13/14/15/21 and heuristics H4/H6/H18/H25/H26/H27. Preserve domain
authority while delegating generic conversion, rendering and event processing. Judge the whole
configuration, processing, retention and cleanup lifetime, not the terseness of a logging call.
Relevant [patterns](../../patterns.md) are LOP-02/03/08/09/10/12; [LOP-X011](../../assessment-patterns.md#lop-x011)
guards against replacing interruption evidence with an end-only summary. No new pattern is needed.

For a selected lead, establish the concrete responsibility through codebase-audit as needed, assess
contextual fit through library-assessment, then compare complete options through opportunity-review.
The [older Typer account](../typer/README.md) retains its October29 realization and applicability
judgments; its exception/lifetime types are useful starting points, not current adoption decisions.

Public APIs, dependencies, runtime defaults and database state are unchanged. Functional tests,
provider runs and performance checks are **not_run**: source and reference evidence suffice for
these discovery questions. Publication checks and the handoff are recorded in STATUS.
