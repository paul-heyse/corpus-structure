# Agent CLI and diagnostics: integrated library discovery

**Discovery, 2026-11-10; mechanical facts refreshed 2026-11-17; benefits Proposed.** Typer, Rich
integrated with Typer, and structlog. The operator selected combined discovery across the whole agent journey,
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

The mechanical facts below were regenerated on 2026-11-17 with `uv run tooling library`
([guide](../../references/discovery-and-evidence.md#gather-the-mechanical-facts-with-tooling-library)).
The overview reading, the topic briefings' source analysis and the research priorities are the
2026-11-10 discovery and keep that date, except where this section says a fact changed.

| Item | Inspected scope |
| --- | --- |
| Source | `f699005497d2876804516bea9cb1a59e273fa2b4`, main, 2026-11-17 (`baseline`); the 2026-11-10 analysis read `0a384a64ef022fb3ce874ac9180a1a89ebb82061` |
| Worktree | 13 dirty paths from concurrent work at the refresh, none under the scanned scope's library use; not qualified |
| Environment | Root uv workspace, `.venv`, CPython 3.14.10, linux-x86_64 |
| Selected | Typer 0.28.0, Rich 15.0.0 and structlog 26.1.0 are each selected directly by `corpus-structure` (`selection`: every platform, default groups, lock read as it stands and not verified). Typer and Rich are also reached transitively, through 132 and 149 paths (Docling, spaCy, fastmcp and others); structlog through one |
| Installed | The same three versions, each shipping `py.typed` (`metadata`). Rich advertises the `jupyter` extra, which is not selected; structlog and Typer advertise no selected extras |
| Offered and used | `compare typer rich structlog --scope python/corpus-structure/src`: 785 files scanned, none skipped, pyrefly checked exactly the scope's 730 Python files; 2,467 offered symbols, 39 referenced, 1,690 unreferenced in scope, 738 unresolved; no deprecated API in use |
| Coverage | All three supplied overviews including addenda read end to end during the 2026-11-10 planning; [coverage and conditional territory](coverage.md) |

What changed since 2026-11-10:

- **structlog is adopted.** The earlier account recorded it as a candidate with no installed
  distribution and no imports. It is now a direct pin, imported by five product modules
  (`cli/observations.py`, `cli/observation_logging.py`, `cli/exception_observations.py`,
  `semantic/m1_products.py`, `methods/characterization_resources.py`). The census attributes
  calls to `structlog.stdlib.ProcessorFormatter` (with `foreign_pre_chain`, `processors`,
  `keep_exc_info`, `keep_stack_info`), `structlog.stdlib.ExtraAdder`,
  `structlog.processors.JSONRenderer`, `TimeStamper` and `ExceptionRenderer`,
  `structlog.tracebacks.ExceptionDictTransformer`, `structlog.wrap_logger`, and the
  `structlog.contextvars` bind, merge and reset functions. Those are the mechanisms
  [CLI-07](briefings/execution-context-and-events.md#cli-07) and
  [CLI-08](briefings/execution-context-and-events.md#cli-08) named as candidates. Those two leads
  are therefore **Used** in part; their counterconditions and the judgment of whether the
  adopted configuration serves the agent were not re-examined here.
- **Rich use is unchanged in kind.** The census finds `rich.text.Text`, `rich.table.Table`
  (including `Table.grid`), `rich.console.Group`, `rich.syntax.Syntax`, `rich.tree.Tree` and a
  `rich.console.Console` subclass. Every symbol of `rich.progress`, `rich.live`, `rich.layout`,
  `rich.logging` and `rich.traceback` is unreferenced in scope, which agrees with the earlier
  observation that no Live or Progress integration exists
  ([CLI-09](briefings/execution-context-and-events.md#cli-09) remains an **Unused lead**).
- **Typer:** `typer.Option` and `typer.Argument` carry nearly all direct references. Members of
  `Typer` and of the context classes are unresolved, as members reached through instances
  always are; read them in context before drawing on them.

Limits of these facts. `unreferenced in scope` describes direct, attributable reference under
`python/corpus-structure/src` only; tests, `scripts`, `tools/evidence`, `tooling` and `services`
were outside this scope, where the 2026-11-10 source search had covered representative parts of
them. Fifteen census rows reach no offered symbol (fourteen dynamic imports with computed module
names, one member of a call result). At the refresh the inventory still counted demonstration
names bound under `if __name__ == "__main__":` blocks in Rich as offered symbols, so the
unreferenced total is inflated; the per-module facts above do not depend on them. The overviews
describe Typer 0.27.3 against the installed 0.28.0 (`overview` reports the mismatch), so older
observations are not automatically 0.28.0 contracts. Independently locked provider projects were
not inspected. Existing November 7 journey evidence retains its original date and scope; no
runtime journey, provider run, benchmark or new probe occurred here.

## Research priorities

| Lead | Proposed direction and present interpretation | Detail |
| --- | --- | --- |
| CLI-01 | Broaden native typed input and modular command declarations where they remove repeated parsing or authoring decisions | [Command model](briefings/command-model.md#cli-01) |
| CLI-02 | Improve discoverability through existing help/reference metadata and selective contextual suggestions | [Command model](briefings/command-model.md#cli-02) |
| CLI-03 | Use parameter provenance and invocation-scoped resources where they complement existing settings and lifetime owners | [Command model](briefings/command-model.md#cli-03) |
| CLI-04 | Extend bounded semantic report projections with exact identifiers, source excerpts and useful hierarchy | [Reporting](briefings/reporting-and-diagnostics.md#cli-04) |
| CLI-05 | Make optional presentation compose safely with machine streams and current delivery semantics | [Reporting](briefings/reporting-and-diagnostics.md#cli-05) |
| CLI-06 | Preserve actionable exception structure with one presentation owner per destination | [Reporting](briefings/reporting-and-diagnostics.md#cli-06) |
| CLI-07 | Investigate structured events plus third-party stdlib logging only for a concrete diagnostic consumer (structlog since adopted; see the baseline) | [Events](briefings/execution-context-and-events.md#cli-07) |
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
