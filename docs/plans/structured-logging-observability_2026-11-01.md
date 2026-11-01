# Structured logging and observability

**Status:** Proposed implementation series; authored 2026-11-01, runtime not implemented.
**Basis:** [Functional review](../functional_reviews/structured-logging-observability_2026-10-31.md)
at `401ecc3d`; operator-approved plan creation and RC01–RC04 decisions on 2026-11-01.
This coordinator owns every package state, source-opportunity disposition and investigation below.
Supporting plans own their technical explanations, not duplicate queues. Execution requires a
subsequent instruction; authoring this series does not install libraries or change runtime behavior.

## 1. Outcome and boundaries

Deliver complete diagnostic workflows through the installed `ci` Typer app: activate/configure,
collect, inspect/follow/search, reconstruct causal execution, compare runs, inspect measurements,
investigate incidents/tests, and preview/export support material. Rich supplies useful terminal
presentation. MCP consumes the same scoped services and retains clean stdio. Local workflows work
offline without another launcher, script, dashboard or observability account. Optional external
collectors/backends are separately operated; this series supplies application integration, not
infrastructure provisioning or a hosted multi-tenant product.

Development/design, feature expansion, tests, troubleshooting, batch/long-running production and
end-user support are selected uses. Future deployed users, delayed feedback and other source domains
shape extension boundaries; they do not automatically introduce billing, durable security audits,
managed datasets/prompts or a second model/task scheduler. PostgreSQL task/knowledge/evaluation
records and existing source receipts retain their authority. Telemetry references them.

## 2. Baseline and focused foundation assessment

Inspected main `facd0af0` on 2026-11-01, with dirty STATUS, library guides, PDF plan/evidence and ADR
index work preserved. PDF native0059 has recorded broad qualification;0060 JSON-text publication
has landed in source while operational deployment/adoption remains separately owned by the PDF
coordinator. This is not a fresh PDF test result. Refresh relevant call sites at execution startup;
do not block logging design on full PDF closeout or change another plan.

Reusable foundations: `cli/app.py` ordinary Typer registration; `cli/output.py` lazy CliState and
per-command JSON emission; `cli/failures.py`/semantic refusals; Settings constructor/environment
ownership; MethodContext stdlib logger; worker-owned cancellation; FastMCP lifespan/run principals;
existing typed source/query/export models; DuckDB2.0 and Pydantic2.14 already declared. Settings
has no observability section in the inspected source. Help does not acquire DB/scientific kernels.

Required foundation changes: capture safe producer context before asynchronous delivery, reserve
identity fields, split process SDK ownership from operation/invocation scopes, share scoped query
contracts below Typer/MCP, and select measurement visibility before aggregation. Existing console
creation per emission does not coordinate Live/logs; replace it with invocation-owned consoles
while preserving test stream swapping. Spawned PDF/MCP processes need explicit initialization.
A logging flag in the root callback alone cannot satisfy these consumers.

Assessment uses declared core3.3, efficient-architecture heuristics1.0, applicable code-intelligence1.4
and test-assessment guidance. A1–A3 favor owned diagnostic meaning and native composed mechanisms;
A4 favors partitioned reads, bounded detached buffers and batched export over shared hot writers or
whole-history rescans. These are proposed qualitative judgments, not capacity measurements or a
whole-system audit. No new alignment lint, compliance register or mandatory benchmark is proposed.

## 3. Target, authority and shared choices

- Typed, versioned diagnostic occurrences describe events, not task truth. Core declarations own
  meaning; runtime assembly owns processors/providers; query/export services own scoped reads;
  CLI owns Rich/Typer presentation. SDK-specific objects stay outside core and domain method APIs.
- Preferred event path is structlog + stdlib routing, Rich presentation, OTel API/SDK native exporters
  and scoped Logbook failure capture. LOG-00 compares complete alternatives and qualifies pins
  before implementation; Logfire SDK is eligible for local instrumentation, independent of its service.
- One occurrence archive is authoritative for diagnostic occurrence identity. OTLP logs/ECS are
  delivery projections of the same ID; queries never count both as separate occurrences. Spans and
  metrics keep their separate native semantics. None is an authoritative semantic/audit store.
- Default normal profile retains safe INFO+ events and explicitly selected operation spans. Debug
  adds selected detail; incident captures safe DEBUG context independently of INFO console filtering;
  off disables optional diagnostics, not command results or authoritative task records.
- Local selected operation traces use sampled recording (AlwaysOn at those selected boundaries).
  Production sampling is explicit and marks coverage partial; no promise of complete local traces
  from RECORD_ONLY spans. Remote-only volume reduction must occur in a qualified destination filter
  or downstream collector, not an upstream sampler silently removing promised local records.
- Process metrics are operator-visible only. Run summaries use authoritative run/task measurements.
  Explicit run-scoped metric streams may add bounded dimensions; user/run filtering is refused when
  identity was aggregated away. Sampling does not redefine exact denominators.
- Configuration extends Settings; explicit CLI values override environment-resolved values without
  CLI defaults overwriting them. SDK/file configuration is explicit, not an accidental extra layer.
- Data capture is opt-in beyond safe metadata. Secrets, source text, SQL values, prompts/responses,
  baggage and locals do not flow into records by default. Isolation precedes buffering and export.

### Accepted rule impacts

| Review item | Operator decision | Execution route |
|---|---|---|
| RC01 | Accepted 2026-11-01: shared diagnostic services, explicit CLI overrides, lazy runtime and dependency direction retained | LOG-01 ADR and D8/D9 owner update before dependent code |
| RC02 | Accepted 2026-11-01: archive/schema/retention/scoped query contracts; D3/D6 authority retained | LOG-01 decision and LOG-03 owner contracts |
| RC03 | Accepted 2026-11-01: explicit child telemetry/correlation and credential boundaries | LOG-02/05 D6/D8 updates and supervisor migration |
| RC04 | Accepted 2026-11-01: explicit declarative configuration and optional remote reads; hosted access conditional | LOG-01/10 design updates; no hosted infrastructure rollout |

Accepted ADRs are not edited retroactively. LOG-01 records meaningful choices and amends relevant
architectural owners through the existing ADR route. No ADR, authority or existing plan is changed
by publication of this proposed series.

## 4. Reading route and execution queue

LOG-00 investigative choices are complete at the bounded scope below; LOG-01–LOG-12 remain
planned and not implemented. This table alone owns their live state.

| Package | Owner and delivered capability | Prerequisite |
|---|---|---|
| LOG-00 | **Investigated 2026-11-01**; [Contracts/runtime](structured-logging-observability/contracts-runtime-and-instrumentation.md#LOG-00): settle consequential compositions, compatibility and native boundaries | Current source/guides |
| LOG-01 | Same plan: decisions, event/configuration contracts, privacy and visibility | LOG-00 choices |
| LOG-02 | Same plan: owned runtime, safe pipeline and first installed Typer operation | LOG-01 |
| LOG-03 | [Retention/analysis](structured-logging-observability/retention-query-and-incidents.md#LOG-03): archives and scoped event/trace query, basic Typer reads | LOG-02 |
| LOG-04 | Same plan: native incident capture/grouping with CLI access | LOG-03; failure event contract LOG-01 |
| LOG-05 | [Runtime plan](structured-logging-observability/contracts-runtime-and-instrumentation.md#LOG-05): actual workers/dependencies/model processes instrumented | LOG-02, working archival sink LOG-03 |
| LOG-06 | [Typer/Rich](structured-logging-observability/typer-workflows-and-rich.md#LOG-06): full local diagnostics UX and safe streams | LOG-03/04; incremental LOG-05/07 consumers |
| LOG-07 | [Metrics](structured-logging-observability/metrics-and-operational-analysis.md#LOG-07): correct metrics, comparisons and telemetry health | LOG-01 visibility, LOG-02 runtime, LOG-03 reads |
| LOG-08 | [Typer/support](structured-logging-observability/typer-workflows-and-rich.md#LOG-08): portable support preview/export | LOG-03 scope/pinning and LOG-06 rendering |
| LOG-09 | [MCP/external](structured-logging-observability/mcp-and-external-integrations.md#LOG-09): native MCP correlation, typed reads and support parity | Working LOG-03/05; LOG-08 exports |
| LOG-10 | Same plan: explicit advanced config, OTLP destinations and qualified optional remote query | LOG-02/03/07 contracts; I06 prerequisites |
| LOG-11 | [Adoption/testing](structured-logging-observability/adoption-testing-and-qualification.md#LOG-11): test diagnostics and complete consumer adoption | LOG-02 onward, integrated incrementally |
| LOG-12 | Same plan: final assembled acceptance and operational handoff | Selected functional scope complete; LOG-11 inventory reconciled |

This is a useful route, not a barrier per row. Domain instrumentor preparation, CLI design and MCP
schema work can overlap after shared contracts settle; working acceptance needs implemented inputs.
LOG-03 supplies minimal real CLI query consumers, so archival infrastructure is not a disconnected
slice. LOG-06 completes UX rather than serving as a delayed integration phase. LOG-11 migrates and
checks consumers as the owning packages land, not only at the end. One integrator owns shared
Settings, pipeline and package-contract changes; documents are not fixed worker assignments.

### Bounded investigations — single current owner

| ID | Question, settling evidence and decision consequence |
|---|---|
| I01 | LOG-00 compare structlog/stdlog vs Loguru routing and direct OTel vs local Logfire SDK: pinned sources/dependency metadata, field-preserving branch topology, provider ownership, bounded queues. A probe only if those leave a material uncertainty; blocks LOG-01 composition. |
| I02 | LOG-00 compare OTel parent/links with Eliot parse_stream/Task.is_complete for partial/out-of-order histories. Use known expected history including missing terminal record/fan-in; select native Eliot only for a distinct action-history promise, otherwise OTel remains the causal model. Blocks LOG-03 causal-query contract. |
| I03 | LOG-00 qualify native file exporters, contrib logging handler and selected Python3.14 dependency family; record exact proposed versions and API paths, including local Logfire span projections. Blocks LOG-02 exporter wiring, not CLI design. |
| I04 | LOG-03 settle native stream rotation, interrupted tails, cursor/export pinning and query projection under concurrency; inspect native contracts and use a bounded failure scenario if needed. Blocks retained query acceptance. |
| I05 | LOG-02 qualify provider/reader ownership, short-lived final collection and real exporter shutdown deadlines. Test blocked destination only where source cannot establish behavior; blocks bounded-cleanup claim. |
| I06 | LOG-10 qualify LogfireQueryClient API/version, time windows/read tokens/rate/ingestion semantics and actual test endpoint. Missing endpoint/credentials blocks remote acceptance only; offline required scope stays executable. |

## 5. Opportunity and enhancement disposition

Source IDs below refer to the [original review](../functional_reviews/structured-logging-observability_2026-10-31.md).
Every selected row is planned, with closure requiring named package evidence; none is closed.

| Source | Responsible packages and closure obligation |
|---|---|
| [O01](../functional_reviews/structured-logging-observability_2026-10-31.md#O01) | LOG-01/02/05: one structured meaning/code/identity across actual producers |
| [O02](../functional_reviews/structured-logging-observability_2026-10-31.md#O02) | LOG-01/02/06: complete configuration/lifecycle/help and effective provenance |
| [O03](../functional_reviews/structured-logging-observability_2026-10-31.md#O03) | LOG-06: coordinated Rich and parseable machine streams |
| [O04](../functional_reviews/structured-logging-observability_2026-10-31.md#O04) | LOG-03/06: local retained event/trace reads, following and comparisons |
| [O05](../functional_reviews/structured-logging-observability_2026-10-31.md#O05) | LOG-05: honest thread/process/dependency causality and attempts |
| [O06](../functional_reviews/structured-logging-observability_2026-10-31.md#O06) | LOG-07: scoped metrics, correct aggregation/temporality and trace navigation |
| [O07](../functional_reviews/structured-logging-observability_2026-10-31.md#O07) | LOG-04: failure context and incident grouping without occurrence loss |
| [O08](../functional_reviews/structured-logging-observability_2026-10-31.md#O08) | LOG-11: independent telemetry controls and existing-runner integration |
| [O09](../functional_reviews/structured-logging-observability_2026-10-31.md#O09) | LOG-08: permission-preserving support preview/export |
| [O10](../functional_reviews/structured-logging-observability_2026-10-31.md#O10) | LOG-09: actual MCP native context and typed diagnostic parity |
| [O11](../functional_reviews/structured-logging-observability_2026-10-31.md#O11) | LOG-10: local/export configuration; remote reads conditional on I06 |
| [O12](../functional_reviews/structured-logging-observability_2026-10-31.md#O12) | LOG-01/02/03/05/12: privacy, bounded resources, coverage and original failure preservation |
| E01 | LOG-00/05/11: newly identified local Logfire instrumentation and capfire comparison, independent of hosted service |
| E02 | LOG-01/02: reserved fields, producer-time context, detached exceptions and destination mutation isolation |
| E03 | LOG-03/I02: native causal history/incompleteness comparison with Eliot |
| E04 | LOG-02/07: sampling-versus-export contract and metric visibility before aggregation |
| E05 | LOG-04: capture-vs-presentation thresholds, trigger mapping, bounded native Logbook semantics |
| E06 | LOG-10: qualified ECS projection, remote read clients and declarative precedence |

E01–E06 are enhancements discovered during authoring preparation, not retroactive review findings.
The supplied guides were read end to end across focused contributions; the plans retain concrete
mechanisms and source sections. Useful but unselected capabilities remain explicit deferrals:
Logbook persistent tickets/acknowledgments reopen with an incident-resolution consumer; managed
prompts/datasets/gateways reopen only with a separate authority-changing requirement; profiling
reopens for a CPU/allocation attribution need; hosted tenancy reopens with actual participants and
access infrastructure; alternate ECS consumers reopen with their external schema contract.
No silent adoption of those adjacent platform features follows from this series.

## 6. Completion and evidence

Complete selected scope means real installed Typer local workflows, actual spawned worker and
stdio MCP journeys, correct metrics/incidents, safe portable support, migration of all in-scope
producers, and final-source functional/provider/nonfunctional obligations. Optional external reads
are separately labelled unavailable until exercised against their actual backend; in-memory or
mocked exporters do not qualify that route. Quantitative overhead/capacity claims require measured
conditions; no such claim or mandatory performance target is currently selected.

LOG-12 owns assembled acceptance. Focused tests belong with each capability; full `just test-all`
and applicable `just hygiene` follow complete selected scope. Preserve failed/interrupted receipts.
Do not reuse the PDF baseline's pass as logging evidence. The series remains Proposed until
execution; no logging runtime, dependency installation or new tests were performed in plan authoring.

Publication outcomes are reported in the authoring commit and STATUS. Documentation check failures
outside this series do not authorize repairs to existing plans.

### Authoring verification — 2026-11-01

- **passed:** focused stdlib link/anchor/whitespace inspection: seven documents,54 local destinations,13 unique LOG package anchors and O01–O12 source links.
- **passed:** `just turn-end`; required ADR-index/format maintenance, no product qualification claim.
- **failed:** `just docs-check`; existing parsing plan references removed `ingest/profile.py`, and the source review references the pre-relocation OpenTelemetry guide path. Existing `<descriptor>` warnings also remain. Neither failure is in the new series; no existing plan repair is included.
- **not_run:** `just test-all`, runtime/exporter/backend journeys and dependency installation; this task authored proposed plans only.

Focused independent advice checked all seven plans and found no package prerequisite cycle. Its
incident first-retention and aggregate-buffering corrections are integrated here and in LOG-01/04.
This is focused plan advice, not a formal recommendation audit or implementation acceptance.

## Investigation disposition — 2026-11-01

Executed from clean baseline `28f735b87eb2672c521af816aed411ab665b79f4`. No production
manifests, runtime code, databases or services changed. Isolated probe environments live outside
the repository; exact specifications/locks and failed attempts are retained with evidence.

| Item | Current scoped conclusion | Evidence owner |
|---|---|---|
| I01 | passed bounded comparisons: select structlog26.1.0/stdlog, scoped Logbook1.10.1 and direct OTel core ownership. Local Logfire is not a drop-in global/native/Pydantic instrumentation owner. | [events/history](../design_review/evidence/2026-11-01_logging-events-history/README.md), [SDK runtime](../design_review/evidence/2026-11-01_logging-telemetry-runtime/README.md) |
| I02 | passed comparison: OTel parent/links plus explicit coverage; do not add Eliot identity/tree now. Missing entire children remain unknowable without independent inventory. | events/history; record logging.i02 |
| I03 | passed isolated family/import and native three-signal path: SDK/API1.45.1, file exporter/contrib0.66b1. Private FileLogExporter module requires explicit pin qualification. Product lock integration remains LOG-01/02. | SDK runtime; record logging.i03 |
| I04 | partial overall; primitive probes passed and mechanism selected: stable rotation stream, samefs closedsegment hardlinks/private snapshot manifest, active-prefix copies, ingestion-position cursors. Production lifecycle/security remains LOG-03. | [archive/query](../design_review/evidence/2026-11-01_logging-archive-queries/README.md); record logging.i04 |
| I05 | partial; final collection/host ownership and loopback transport control exercised. Hard overall graceful deadline remains unestablished:10ms force_flush took about250ms. Blocks LOG-02 bounded-cleanup acceptance until a qualified strategy is supplied. | SDK runtime; record logging.i05 |
| I06 | partial; exact query source and local MockTransport checks passed. Live reads blocked by missing authorized endpoint/read token/known test scope; no remote query or ingestion occurred. | [remote contract](../design_review/evidence/2026-11-01_logging-remote-contract/README.md); record logging.i06 |

LOG-00 closes composition/causality/candidate-family investigation only, not product implementation
or all-source qualification. The next package is LOG-01 decision/contracts. Before LOG-02 can claim
its5s shutdown guarantee, qualify a shared-deadline execution/isolation strategy or explicitly
restrict supported destinations without weakening the accepted failure contract. No hard graceful
guarantee follows from a watchdog killing a stuck exporter. I04 integrated lifecycle and I06 live
access remain open at their existing package owners. No new ADR has been accepted by this task.

Investigation publication checks (2026-11-01): **passed** `just evidence` (114 records,0errors,
38historical warnings), `just ready`, required `just turn-end` and scoped link/whitespace inspection.
**failed** `just docs-check` on the pre-existing parsing-profile and moved-library review links;
those unrelated owners were not edited. **not_run** broad product qualification and real remote
acceptance. Six finalized records preserve original failed setup/probe attempts.
