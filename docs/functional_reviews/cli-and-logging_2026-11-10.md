# Agent command and diagnostic capabilities

**Functional-extension review, 2026-11-10. Recommendations and benefits Proposed.**
Scope: every CLI-01–10 discovery lead, its conditional territory, and additional useful
Typer/Rich/structlog compositions. Target: Codex as the sole editor and primary operator.
The operator selected a complete target, with implementation selection afterward.

## Baseline and evidence limits

Inspected main `a3d2b8b24a4b3ba20274fa12769f09f6b04faaeb` and its concurrent dirty DMC
implementation: CLI schema/failures/output/registry, new diagnostic custody, interpretation and
research commands, settings and their semantic owners/tests. The
[discovery](../library_leverage/libraries/cli-and-logging/briefing.md) supplies complete overview
coverage and earlier release-source observations. Two independent reviewers and a library
researcher contributed bounded read-only inquiries; the coordinator reconciled their results.

Only the [DMC series](../plans/domain-data-model_2026-11-10.md) and its companions are active
planning context for this review. Older CLI plans are complete/legacy. Current code establishes
what exists; conflicting prose or stale completion labels do not establish tested behavior.
D8 and ADR-0069 remain the architectural/effect/custody owners. No accepted scope is amended here.

Selected library baseline remains Typer0.28.0/Rich15.0.0; candidate structlog26.1.0 is not installed.
Root workspace source and representative CLI/MCP/provider consumers were inspected, not every
independently locked service. Source-level claims are Interface-checked where the mechanism was
read; local functional suitability and expected benefits remain Proposed. No quantitative claims.

`uv run ci schema check --help` **passed**, 2026-11-10, through the installed entrypoint.
Its captured output exposes correction/retention/raw-evidence controls, but several names are
ellipsized and most lack descriptions at the observed width. That establishes this help rendering,
not a measured agent failure or general CLI qualification. Functional tests, provider/native runs
and new probes are **not_run**; the review's choices do not require runtime experiments.

## Recommended target

An agent can discover an operation, understand its inputs/effects, invoke it precisely, inspect
an attributed outcome, follow available evidence and choose an appropriate next action. It can
also inspect selected diagnostic events across an operation without rerunning the producer.
The same owned products support JSON, readable terminal views and deliberate saved presentations.
Command authoring reuses native parsing and scoped resources while domain decisions remain with
application owners. This is one composed interface, not a second workflow engine or telemetry service.

| Opportunity | Recommendation | Detail |
| --- | --- | --- |
| O01 | Recommend focused command knowledge and legible exact syntax, extending existing native help/reference generation | [Authoring](cli-and-logging/command-authoring-and-discovery.md#O01) |
| O02 | Recommend reusable typed input conventions and local command-authoring patterns; retain explicit composition | [Authoring](cli-and-logging/command-authoring-and-discovery.md#O02) |
| O03 | Recommend faithful invocation explanation joining CLI explicitness to the actual settings snapshot; no new acquisition policy | [Authoring](cli-and-logging/command-authoring-and-discovery.md#O03) |
| O04 | Recommend action-oriented correction and failure dossiers over current DMC products, with separately typed unexpected-exception detail | [Reports](cli-and-logging/reporting-and-correction.md#O04) |
| O05 | Recommend a bounded, attributable diagnostic-event inspection capability; prefer the stdlib bridge for existing producers, with one final renderer per sink | [Execution](cli-and-logging/execution-and-diagnostic-events.md#O05) |
| O06 | Recommend meaningful headless progress and identity-qualified next actions; conditional TTY display over the same observations | [Execution](cli-and-logging/execution-and-diagnostic-events.md#O06) |
| O07 | Recommend replayable report presentation; conditional HTML/SVG delivery where saved presentation serves review/sharing | [Reports](cli-and-logging/reporting-and-correction.md#O07) |
| O08 | Recommend an example-led native authoring/verification path that tests meaning, configured processing and process behavior at their distinct boundaries | [Authoring](cli-and-logging/command-authoring-and-discovery.md#O08) |

These are functional recommendations, not eight required packages or a library-adoption quota.
O05's logging choice is a recommended realization for planning, not installation authority.
Existing structured reports already do much of the work; presentation alone is not a replacement
for correct selection, and logs cannot become proof of successful effects or provider assurance.

## Composition, priority and design judgment

Start with O01/O04 and O08: expose the new DMC inputs and correction products coherently, and make
the next command addition easy to verify. O02 joins that authoring work where repeated declarations
actually coincide. O03 consumes the DMC settings snapshot rather than creating another precedence
resolver. O05 adds new investigative value after agreeing which producer observations and retained
selection the agent can inspect. O06 uses those products without inventing progress truth. O07
reuses the resulting presentation functions; rendered export follows an actual sharing/review use.

The dependency is semantic: report/event selection precedes rendering; disclosure precedes sink
fan-out; process identity transfer precedes correlation; actual owner settlement precedes next-action
guidance. Work on independent command knowledge and rendering can proceed together. No production
increment or change to DMC scheduling is selected by this order.

Core3.3, heuristics1.0 and code-intelligence1.4 are selected through
[standard.toml](../design_review/design_principles/standard.toml), with test-assessment1.2 for O08.
FP-01/03/06 favor local command ownership and explicit composition. FP-04/05, DP-01/02/21 and
CI-01/02/04/13 require outcome, observation, provider assertion, coverage and evidence references
to retain their different meanings. FP-07/A4 and H4/H6/H12/H16/H25–28 favor bounded owner-selected
reads, preparation at useful lifetimes and no duplicate logging store or repeated execution during
inspection. This is a functional value/realization review, not a diagnostic alignment verdict.

### Source corrections and integration decisions

The earlier discovery's RichHandler warning was too narrow. Tagged ProcessorFormatter copies the
record before clearing exception state; RichHandler can still see the original foreign record's
`exc_info` even with default `keep_exc_info=False`. A source-inspected composition must therefore
avoid relying on that option to preserve formatter output. O05 recommends ProcessorFormatter plus
ordinary StreamHandler, with structlog owning final console/JSON rendering; Rich supplies selected
traceback presentation within that route. [ProcessorFormatter26.1](https://github.com/hynek/structlog/blob/26.1.0/src/structlog/stdlib.py),
[RichHandler15](https://github.com/Textualize/rich/blob/v15.0.0/rich/logging.py).

DMC-11 already selects bounded original-engine correction detail and optional managed custody;
dirty source contains these adapters. O04 extends their use and presentation, not their existence.
DMC-15 already selects actual acquisition metadata; O03 does not reintroduce providers, reload or
native settings CLI parsing. Any selection that changes these meanings must name the DMC overlap
and amend the owner through subsequent planning.

Rule impacts: O01/O02 require no new binding rule when metadata and parsers stay thin. O03 must
preserve settings source policy. O04/O05/O07 may need D8/report contracts and ADR-0069 custody
clarification for newly retained content; new schema versions belong to their existing semantic
owner. Changing effect authority, default raw disclosure or expiry requires the existing decision
route. No new alignment lint, gate, register or universal command/event framework is recommended.

## Coverage and alternatives

| Discovery input | Review disposition |
| --- | --- |
| CLI-01 | O02 recommends native declarations; O08 covers authoring verification |
| CLI-02 | O01 recommends focused discovery; completion remains useful supporting functionality |
| CLI-03 | O03 recommends provenance; O02/O05 use resources only at real lifetimes |
| CLI-04 | O04/O07 recommend selected literal/located views and replay |
| CLI-05 | O04–07 preserve machine streams; TTY rendering is conditional |
| CLI-06 | O04 distinguishes typed correction and unexpected exceptions; O05 selects renderer ownership |
| CLI-07 | O05 recommends a bounded event consumer and stdlib-compatible realization |
| CLI-08 | O05 recommends scoped context and explicit process transfers using existing identities |
| CLI-09 | O06 recommends headless summaries/transitions; O05 retains filtering semantics |
| CLI-10 | O08 recommends native focused verification across all opportunities |
| File types, dash, lazy/atomic writes | O02 retain current bounded reads/custody; use native streams for a separately selected simple stream consumer |
| Custom groups/control options/normalization | O02 defer custom dispatch; use supported metadata/parsers first; preserve raw separator semantics |
| Runner/module/shell/prompt/launch | O01 retains installed entrypoint; local completion conditional; prompts/launch have insufficient value for unattended Codex |
| Render protocols/hooks/segments | O04/O07 use built-ins; custom protocol only for repeated layout they cannot express; no global hooks |
| ANSI/tokens/metadata/Markdown extensions | O04 permits existing classified tokens and literal text; ANSI is not sanitization; interactive metadata/custom Markdown lack a selected consumer |
| Recording/text/HTML/SVG | O07 recommends semantic replay, text presentation; rendered HTML/SVG conditional with explicit limits/custody |
| Pager/alternate-screen/notebook/REPL/terminal effects | Retain awareness; insufficient benefit for this agent audience. Revisit for a concrete alternative interface |
| Async/byte sinks/serializers | O05 retains synchronous stdlib route; reconsider blocking sinks or whole-transport pressure, not presumed speed |
| Custom structlog wrappers/factories | O05 uses native factories/processors; custom wrappers offer no demonstrated contract benefit |
| Telemetry/ECS/framework/Twisted companions | Defer until an actual remote ingestion, tracing or runtime consumer; current local correlation needs none |

Additional value beyond the original shortlist is explicit in O01's scoped command reference,
O04's observation-to-source/action navigation, O05's field-selected retained event reads and O07's
re-presentation of immutable products. These opportunities do not require a prior failure report.
The case is plausible usefulness for repeated editing/investigation, not fabricated demand counts.

## Delivery criteria and handoff

The [CLI and logging series](../plans/cli-and-logging_2026-11-10.md) owns scheduled O01–O08
scope, conditional decisions and future qualification. It follows DMC-17 before PM2; this review
remains recommendation evidence, not a duplicate execution ledger.

A delivered target lets Codex find exact DMC controls without reading implementation source,
inspect a located correction and its original binding, distinguish managed results from semantic
runs, retrieve a filtered diagnostic selection with honest collection coverage, and compare
attempts without replaying their producers. Saved presentation never changes underlying outcome.
Representative checks and counterconditions are in the companions; detailed acceptance and
consumer migration belong in the selected implementation plan.

Review publication updates navigation and STATUS only. No installation, production/database change,
provider execution, architectural decision adoption or plan amendment occurred. Proceed through
create-plan after selecting scope; unscheduled recommendations remain here with their conditions.
