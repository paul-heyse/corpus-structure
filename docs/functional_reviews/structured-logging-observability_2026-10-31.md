# Structured logging and observability through Typer

**Functional-extension review · 2026-10-31 · Proposed.** The recommendation is a composed
structured-event, telemetry, local investigation and support capability, with Typer as the complete
application interface and MCP as another consumer of the same services. This is a functional-value
review under `functional-extension-review`, not a diagnostic audit or implementation approval.
All command examples below describe proposed behavior; none is an existing-command claim.

## 1. Scope, baseline and evidence

The operator selected development/design/feature expansion, testing, troubleshooting, plausible
long-term production scenarios and end-user use. Every selected capability must be usable through
`ci` without a separate script, instrumentation launcher, dashboard or MCP client. External
collectors/storage may be integrated, with their infrastructure managed separately. New dependencies
are eligible; an uninstalled library is not a reason to reject its capabilities.

Inspected source baseline: `73f6feaee1d907f8ad4405d16129c59108e4b31c`, plus the working-tree
versions of STATUS, D3, Typer/Rich guides and the active PDF series on 2026-10-31.
A publication-time refresh at `8dfe1f93b21f9db68531a5c8679ea8f6cf5f0d01` observed ADR-0041/0060 work on JSON-text admission to normalized tables;
it changes the PDF validation baseline, not the diagnostic ownership recommendation. The two supplied
logging/OTel guides were untracked inputs. PDF implementation and validation are concurrent and
still moving; this review makes no PDF completion or qualification claim. Refresh affected call
sites during implementation planning rather than freezing that work to this review's baseline.

The five supplied guides are the capability inputs:

- [Python structured logging and observability](../libraries/logging/Python_Structured_Logging_and_Observability.md), especially §§2–12.
- [OpenTelemetry Python](../libraries/logging/OpenTelemetry_Python.md), §§2–12.
- [Typer](../libraries/python_introspection/typer.md), particularly context/lifecycle, sources, testing and the 0.27.3 addendum.
- [Rich](../libraries/python_introspection/rich.md), especially §§5–10 and the exact Typer integration boundaries.
- [FastMCP](../libraries/python_introspection/fastmcp.md), context, middleware/lifespans, security, client handlers and telemetry.

Architecture context: [D6](../design/D6-orchestration-metrics-policies.md) owns task/outcome and
operational policy meaning; [D8](../design/D8-agent-and-query-interfaces.md) owns interfaces;
[D9](../design/D9-repository-and-phase0.md) owns dependency direction. Current PDF obligations remain
with the [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md). The declared core 3.3,
efficient-architecture heuristics, test-assessment companion and applicable code-intelligence 1.4
principles shape this recommendation. It introduces no broad audit prerequisite.

### Observed integration anchors — source-inspected, 2026-10-31

Paths in this subsection are relative to `python/corpus-structure/`.

| Surface | Current behavior and implication |
|---|---|
| `src/corpus_structure/cli/app.py`, `cli/output.py` | Typer 0.27.3 registration; lazy `CliState` settings; per-command `--json`; Rich 15.0.0 result output and stderr diagnostics. Extend invocation state without eager DB/kernel acquisition. |
| `cli/failures.py`, `semantic/refusals.py` | Typed expected failures and DB failure classification already exist. Reuse classifications; preserve programming errors and cancellation. |
| `settings.py`, `cli/status.py` | One settings owner, constructor over environment, explicit environment reporting and credential masking. No observability section in the inspected settings. Extend this owner rather than scattering environment reads. |
| `core/method.py`, `orchestrate/semantic.py`, `ingest/pdf_methods.py` | MethodContext already carries stdlib Logger; orchestration obtains method-name loggers and methods emit warnings. Preserve third-party/stdlog interoperability while adding structure. |
| `intervene/server.py`, `intervene/semantic_server.py` | FastMCP 4.1.3 stdio, no banner, lifespan-owned resources and direct/injected server construction. CLI-only bootstrap would miss embedded consumers. |
| `ingest/pdf_worker.py`, `intervene/automated.py` | Spawned PDF process and supervised provider/MCP processes have distinct lifetimes. Context and exporter ownership must cross those boundaries explicitly. |
| `tests/test_cli.py`, `tests/semantic/test_runtime_entrypoints.py`, `tests/conftest.py` | Existing lazy-help, stream/result and MCP binding controls are useful extension points. In-process runners are not proof of installed-process startup/shutdown. |

The package already declares DuckDB 2.0.0 and Pydantic; richer logging dependencies are not assumed
installed. The inspected source and documentation establish integration routes, not runtime delivery.

## 2. Recommended composition and alternatives

**Selected direction — Proposed:** structlog event processing + standard logging delivery + Rich
terminal presentation + OpenTelemetry SDK/instrumentors and native OTLP file/network exporters.
Use existing DuckDB for local query projections over retained structured data, loaded only by
investigation commands. Keep event/telemetry services below CLI/MCP; Rich and Typer stay in `cli`.

| Responsibility | Preferred mechanism | Alternatives and reason |
|---|---|---|
| Application events and context | structlog `bind`, `contextvars`, processor chains, exception processors; existing Pydantic models for consequential typed diagnostics | Stdlib plus python-json-logger is smaller for JSON-only needs, but leaves application context/processing less composable. Loguru is capable, but its additional singleton/sink configuration would overlap chosen stdlib routing. |
| Existing/library records and delivery | Stdlib handlers/filters, `QueueHandler`/`QueueListener` where blocking delivery warrants them; destination-specific formatting | Keep native library logger identities. No universal logger replacement or mandatory queue for every invocation. |
| Causality and cross-signal context | OTel spans, events and links; structured logs retain domain identifiers and trace/span IDs | Eliot actions add meaningful typed causal diagnostics, but a second causal tree would duplicate OTel ownership. Choose Eliot instead only if its action contracts become a distinct requirement that spans cannot meet. |
| Failure context and aggregation | Scoped Logbook `FingersCrossedHandler` for failure-triggered capture; query-time incident grouping | Stdlib `MemoryHandler` is suitable for capacity/severity batch flushing, not error-only retention. Use Logbook only in the selected incident-capture profile, not as another global router; durable ticketing remains optional. |
| Terminal UX | RichHandler plus one invocation-owned diagnostic Console, Progress/Live, structured renderables | Plain mode for automation/accessibility; no separate Textual application is necessary for the selected workflows. |
| Interoperable telemetry | OTel API/SDK, signal processors/readers, programmatic instrumentors, OTLP exporters | Logfire is an optional integrated instrumentation/query backend, not required for local operation. Preserve OTLP portability and choose one instrumentation owner per boundary. |
| Local telemetry and investigation | Native OTel JSON file exporters, structured JSONL event segments, typed DuckDB views | OTLP is not a query protocol. Do not pretend all remote backends share a read API. Local files avoid a compulsory collector or database service; remote query adapters need explicit backend support. |
| Schema/export formats | Native OTLP for telemetry; versioned application diagnostic fields | ECS is useful for an Elastic integration, not an additional internal semantic authority. python-json-logger/ECS formatters can serve specific destinations without replacing event construction. |

Do not install all alternatives. picologging supplies no compelling new functional capability here;
its archived state and native-extension/Python compatibility burden weaken its technical case.
Logfire's scrubbing and instrumentation are useful optional mechanisms; mandatory Logfire would add
a service/account dependency to basic diagnosis. Compare package compatibility on Python 3.14.10
before selecting exact pins; none of the guide's reported versions implies an installed, tested
combination. Deliberate additions remain exact-pinned with bounded lock changes and affected checks.

### Important composition boundaries

Render once per destination after safe structure exists. A `ProcessorFormatter` JSON string is not
an OTel attribute map: bridge structured fields before terminal/file formatting. Preserve third-party
`LogRecord` fields and exception information without re-ingesting the same event recursively.
Do not manufacture an OTel span for every log record. Maintain distinct event occurrence IDs and
causal span identity; repeated deliveries or summaries must not become new domain occurrences.
Application event JSONL is the canonical diagnostic-occurrence archive, not a semantic audit store.
OTLP logs are an optional correlated delivery projection sharing that occurrence ID. Local queries
select the occurrence archive rather than unioning both copies; telemetry-only foreign records keep
their source identity. Trace/metric archives have their own signal semantics.

Use native file exporters rather than building an OTLP receiver. The source-checked OTel 1.45.1
file package exposes `FileSpanExporter`, `FileMetricExporter`, `FileLogExporter`; their path/stream
constructors support newline-delimited OTLP JSON. Always supply a destination: the default stdout
would violate JSON/MCP output. Use per-process/per-signal streams; locks are not process-shared,
flush is not fsync, and file export is not a durable audit guarantee. Batch processors/readers
still need lifecycle drain. Exact distribution installation and end-to-end integration remain
unverified. See [OTel file exporter source](https://github.com/open-telemetry/opentelemetry-python/tree/v1.45.1/exporter/opentelemetry-exporter-otlp-json-file).

## 3. Functional opportunities and resulting workflows

<a id="O01"></a>
### O01 — A common diagnostic language across development and product use

Developers and users should classify a problem without parsing message prose. Use stable codes,
severity, operation/stage, affected identities, reason, safe observed values and remediation where
useful. Reuse existing refusal/result distinctions: unsupported, invalid, infrastructure failure,
inconclusive, cancelled and partial are different outcomes. Add an event schema version and
resource/build identity. Optional run/task/attempt, release, source/product and policy references
link to existing owners; they are not required to initialize help or a failing startup.

`ci diagnostics explain EVENT --json` should return the structured diagnosis and permitted evidence
references; human output renders the same meaning. Preserve arbitrary third-party records as such,
without fabricating domain codes or incorrectly treating missing context as a negative result.
A feature extension adds its owned events and spans to this composition rather than editing every
handler. Delivery is demonstrated when the same deliberate refusal is intelligible through the
normal command result, retained diagnostics and later explanation, with consistent identity.

<a id="O02"></a>
### O02 — Complete activation, configuration and investigation through Typer

Use explicit `add_typer` groups, typed Options/Literals/ranges/paths, help panels and parameter
provenance. Proposed root controls include log level/format, telemetry selection, diagnostic path
and progress policy. Global options precede the subcommand; keep existing per-command `--json`.
`ci diagnostics config --json` reports effective safe settings, sources, destinations, retention,
sampling and active instrumentation. A documented set of diagnostic profiles (normal, debug,
incident and off) can select these settings without creating a second policy engine. `ci diagnostics check` explicitly tests writable destinations
and selected export connectivity; ordinary help performs neither check.

Extend Settings once and pass validated overrides from Typer. Use `get_parameter_source` to apply
only explicit CLI overrides; a default false flag must not overwrite an environment choice. Preserve
constructor-over-environment policy. A future declarative OTel configuration file is an explicitly
selected advanced source: validate it through `ci`, show its resolved policy, and surface its
different precedence semantics instead of silently merging two configuration authorities.

`Context.with_resource`/`call_on_close` own invocation teardown. Install global SDK providers at
most once per process: a standalone CLI process can own them until process exit, whereas repeated
embedded invocations use the host provider or explicitly passed test providers. Invocation spans,
context and scoped handlers close per invocation; a lifespan must not shut down and try to reinstall
a process-global provider. Isolated test exporters/providers are injected without resetting OTel
globals. The process owner alone flushes/shuts down its SDK after all consumers drain. Root callback initializes only what the selected
command needs. Parser failures occur before callbacks; cover safe minimal startup/error reporting
at the installed entry boundary without opening telemetry on help/completion. Result callbacks can
format successful returns but cannot own exception cleanup. Typer 0.27's vendored engine means no
external Click plugin assumptions, no chain-based workflow design, and no private-engine hooks
unless a demonstrated gap warrants them. Current completion is disabled; enabling it is optional,
and any eventual completion must remain local and free of telemetry/service side effects.

<a id="O03"></a>
### O03 — Rich execution views that coexist with scripts

Use a shared stderr Console for RichHandler, Progress and Live. Show truthful task phases, counts,
unknown totals, failures/recoveries and task references. Render a Tree for causal operations, Table
for summaries, Syntax for selected safe JSON/configuration, and Text for untrusted messages. Their
models remain structured data. Use `redirect_stdout=False` for live displays when stdout carries
results; make MCP mode free of live displays. A progress total reaching completion does not prove
transaction publication or semantic completion.

Offer automatic terminal detection plus explicit plain/no-progress controls, fixed-width capture
for tests and a low refresh rate. Human users can export text/HTML/SVG from `Console(record=True)`;
semantic JSON/OTLP remains separately available. Do not record unlimited live history. Pretty
representations are bounded; markup escaping does not sanitize ANSI control sequences. Exception
locals remain off by default. Typer creates its own help consoles, so an application theme or
recording does not automatically control help; use supported help panels and generated CLI docs.

<a id="O04"></a>
### O04 — Local search, following, trace inspection and comparisons

Proposed commands: `ci diagnostics events --run RUN --level warning --json`,
`ci diagnostics follow --run RUN`, `ci diagnostics trace TRACE`,
`ci diagnostics summary --run RUN`, and `ci diagnostics compare --left RUN --right RUN`.
Filters include time, code, operation, task/attempt, component and correlation. Paged JSON returns
continuation and coverage; following is an explicit JSONL stream with interruption behavior.
Explain absent, expired, sampled-out, truncated, corrupt and inaccessible material distinctly.

Write segmented, process-owned archives rather than multiple workers appending one shared file.
Partition archives/catalogs by security and evaluation compartment as well as process, using
restrictive file permissions; one process may serve multiple principals. A query first selects its
authorized compartment, and export cannot widen it. Per-process filenames alone provide no isolation.
Query a pinned set of closed segments and an explicitly bounded active tail; report cut/time and
partial tail. Detect interrupted final records without discarding earlier valid records. Retention
must not silently invalidate an active export or page cursor. Use native rolling handlers for event
files; reuse their stream ownership when coordinating OTel segments, with a thin rotation adapter
only for the native exporter's lifecycle gap. Do not grow an independent persistence framework.

DuckDB reads selected JSON partitions and constructs typed views preserving OTel resource/scope,
span parent/link meaning, metric kind/unit/temporality, histogram boundaries and exemplars. Apply
run/time/file selection before wide extraction; avoid reparsing all historical telemetry per page.
Persistent query projections are rebuildable, not authoritative task stores. User-provided SQL is
not required for ordinary queries. Optional expert SQL is local/trusted only with external file and
extension access constrained; it is not an MCP input. Remote backend queries use supported,
authenticated read adapters; unsupported reads are explicit, never delegated silently to a browser.

<a id="O05"></a>
### O05 — Causal troubleshooting across workers and dependencies

A failed recognition, source publication, query or agent attempt should lead to its operation,
dependency calls and retained products. Bind context with reset in `finally`; copy context into
thread submissions where needed, and serialize W3C context plus permitted identity fields into
spawned workers and owned child processes. Initialize each process's handlers/providers and
files independently. Use parent-child spans for actual nesting and links for fan-in/reuse/retry
relationships, not false temporal nesting. Do not claim a trace is complete when a third-party
service only supplies an opaque receipt.

Keep cancellation/drain/kill ownership with current workers/supervisors. Record attempt failures and
recovery separately; successful retry does not relabel the original failure. Stored source/product
references are hydration links, not payload copies in every event. Reproduction commands use
recorded recipes and existing product access, not replaying a rendered console transcript.

<a id="O06"></a>
### O06 — Operational metrics and measurement-to-trace navigation

Through `ci diagnostics metrics`, users inspect throughput, latency distributions, queue/resource
pressure, retries, error rates and instrumentation loss; filters and machine exports match the
other diagnostics commands. Use OTel Counters/Gauges/Histograms and observable instruments with
Views for attribute selection/aggregation, configured histogram boundaries and bounded cardinality.
Exemplars connect relevant measurements to traces where recording/sampling permits.

D6 policy/scientific metrics retain their authority: export their observations with definitions,
units and provenance rather than independently recomputing policy decisions from sampled logs.
A sampled trace set cannot provide exact task denominators. Preserve temporality/reset semantics
when comparing runs or restarts; do not sum cumulative snapshots. Continuous profiling remains a
separate optional integration: OTel metrics/spans are not a profiler. Add a Typer profile-capture
and inspect workflow only when a concrete CPU/memory attribution question justifies that tool.

<a id="O07"></a>
### O07 — Failure-triggered context and repeated-problem analysis

`ci diagnostics incidents --run RUN` groups repeated problems by declared code/operation/provider
and failure signature, with first/last occurrence, retained count and sample references. High
cardinality source IDs stay in evidence rather than group keys. Exact retained occurrence counts
and estimates over sampled/expired data are labelled differently. A summary never erases original
failure identity or claims every affected task was observed.

Select Logbook FingersCrossedHandler for the optional failure-context profile: a per-operation
bounded buffer releases preceding debug context on a failure, with explicit trigger/reset/factory
policy. Bridge already-sanitized structured events into that scoped handler and route released
records once to the chosen incident destination. Stdlib MemoryHandler can flush at capacity and
on close, so it cannot substitute for this promise without additional behavior. Bound event size
and record count together to bound retained bytes, and isolate concurrent operation buffers.
Advanced ticket/acknowledgment/notification lifecycle remains deferred to its actual consumer;
query-based grouping supplies immediate repeated-problem analysis with less machinery. Alerts can be machine-readable `ci diagnostics assess` results for existing
automation; external paging integrations remain optional destinations.

<a id="O08"></a>
### O08 — Useful test diagnostics without a second test framework

Tests capture structured events with structlog testing facilities or stdlib capture and use OTel
in-memory exporters/readers for local semantic assertions. Assert independent expectations for
codes, fields, parenting, resets and failures, not merely that a shared validator accepts its own
output. Failure bundles join test identity, worker/process, fixture/seed, selected configuration
and operation/trace references. Preserve normal pytest execution and strict markers/config.

Make the full user workflow available as `ci diagnostics test -- SELECTION` using an argument-list
subprocess invocation of the existing test runner and configuration, plus
`ci diagnostics tests REPORT --json` for retained results. Typer's forwarded-argument facility
must preserve token boundaries; do not introduce another test scheduler or redefine qualification.
Each test process initializes its own diagnostics; the wrapper alone cannot instrument xdist or
spawned children. Successful routine runs remain quiet; retained failure detail is bounded.
Do not run concurrent CliRunner calls in threads: they mutate global streams/environment.

<a id="O09"></a>
### O09 — End-user explanations and portable support bundles

`ci support preview --run RUN` shows precisely the time/scope, safe artifacts, omissions and output
size to be included. `ci support export --run RUN --out PATH` creates a local bundle with structured
records, relevant trace/metric slices, masked effective configuration, version/provenance references
and optional Rich HTML/text summary. End users can use a support ID from an error to locate this
scope without understanding SDK terminology. No automatic upload is implied.

Default exports exclude document text, prompts/responses, tokens, SQL parameter values and exception
locals. Explicit inclusion of sensitive artifacts is separately selected, previewed and subject to
source permissions. Sanitize at event construction and again at export boundaries; a later scrubber
cannot retract secrets already written. Preserve actionable source/product references when content
cannot be shared. Bundles explain sampled/expired/missing portions and do not promise bitwise
reproduction of remote/model execution. This capability benefits support today; future hosted-user
scope checks require real principal/tenant enforcement before cross-user access is enabled.
Future opt-in product-usage analytics can reuse event delivery with a separate declared purpose,
consent/retention and aggregation policy; sampled diagnostics cannot become billing records or
unqualified measures of user behavior.

<a id="O10"></a>
### O10 — MCP parity with bounded, authorized diagnostic access

Add typed `diagnostics_find`, `diagnostics_explain`, `diagnostics_summary`, `support_preview` and
`support_export` tools/resources over the same lower services as Typer. Paginate and bind reads to
the current run/principal; export returns a scoped artifact reference. Do not accept arbitrary
server paths or SQL. Discovery visibility is not authorization. Future hosted FastMCP scope/role
checks supplement, not replace, source/run permissions.

Use native telemetry mode `native` unless a selected MCP-aware layer already owns spans;
`propagation_only` is an explicit alternative, while `off` disables that propagation too.
Request middleware binds/resets context; lifespan owns only providers it creates, including the
injected-session branch. Do not shut down a host-injected provider. `Context.log` sends selected
plain-text/structured client diagnostics; `report_progress` depends on the client's request token.
Absent notifications do not mean absent work; persisted reads work after disconnect.

Keep payload logging disabled in native logging middleware: installed source falls back to its
default serializer if a custom serializer fails, so a redacting serializer alone is not a privacy
boundary. Prevent loops through `fastmcp.server.context.to_client` when routing client diagnostics.
Use typed outputs, never Rich/ANSI content, on MCP. The supervised external model environment
currently filters several setting prefixes but leaves telemetry variables ambient: pass sanitized
configuration/correlation explicitly to the owned MCP child and do not leak exporter credentials
or baggage into the provider process. No second task scheduler is proposed.

<a id="O11"></a>
### O11 — Optional production export and backend investigation

Programmatically initialize selected OTel providers/instrumentors from the application lifecycle;
no `opentelemetry-instrument` wrapper is needed. Instrument HTTP, database, logging and model-client
boundaries through supported instrumentors, with explicit spans for domain operations. Avoid double
HTTP/DB instrumentation and record instrumentation/resource/schema versions. GenAI semantic
conventions evolve independently; default content capture is off, and token/cost measurements are
labelled by provider and their actual evidence, never inferred from arbitrary text length.

`ci diagnostics destinations`, `config`, `check`, `export` and backend-aware query commands cover
activation, delivery checks and investigation. OTLP HTTP/gRPC, TLS/auth, timeouts, compression,
sampling and signal-specific settings stay visible and masked appropriately. Native local capture
remains usable offline. Logfire read/query integration is a candidate first optional remote adapter;
select and qualify its query API/auth/rate/retention contract before promising remote SQL. OTLP
alone does not make arbitrary vendors queryable. Backend dashboards may add convenience, but no
selected application capability may depend on them. Collector transforms/tail sampling and backend
alert rules are infrastructure configurations: `ci` can validate/export relevant settings and
inspect supported results without provisioning or upgrading the infrastructure.

<a id="O12"></a>
### O12 — Predictable diagnostic resource and failure behavior

Use process resource identity plus invocation/operation identity; trace IDs are not authentication.
Limit queues, buffers, file retention, attribute/string sizes and dimensions. Drop/summarize optional
detail according to explicit policy and expose dropped/export-failure counts through a nonrecursive
health path. Telemetry failure should not mask the original exception or mark a domain operation
failed after it committed. Explicit diagnostic export/check commands may fail on their own delivery
obligation. A future regulated durable-audit requirement needs a separately designed authoritative
transaction/retention contract; OTel batching and ordinary log files do not supply it.

Flush with a bounded shutdown budget, then close only owned resources. Hard kill and power loss
can lose trailing telemetry; report that limitation. Do not hold DB transactions/leases or GPU
resources while waiting on an optional exporter. Disabled events should avoid expensive payload
construction; aggregate high-frequency work rather than logging every token, cell or row. Normal
investigation narrows files/time first. Hosted multi-user isolation, remote authorization and
retention administration are extension scenarios, not claims of current product support.

## 4. Capability coverage and technical sources

This table accounts for supplied observability capabilities; selection is by useful workflow, not
by installing one library per row. Guide sections are orientation; linked primary contracts below
carry the consequential mechanisms.

| Guide capability family | Disposition / opportunity |
|---|---|
| structlog event construction, bound/execution-local context, processors, exception/developer facilities, interoperability, performance/testing | Select O01/O02/O05/O08/O12; stdlib records remain supported. |
| Loguru binding/contextualize/patch, sinks/rotation/retention/compression, serialized records, exception diagnostics, enqueue/complete | Alternative composition to O01/O07/O12; no parallel router. Preserve its functional aims in selected stdlib/structlog design; locals off. |
| Eliot actions, typed messages, causal serialization, concurrency and testing | O01/O05/O08 via typed diagnostics and OTel causality; alternative when separate action semantics earn their burden. |
| Logbook handler/context stacks, FingersCrossed buffering, ticket aggregation/transports/testing | O07/O08; select scoped native failure-triggered capture and query grouping, defer ticket lifecycle to explicit incident consumer. |
| python-json-logger formatting/fields and stdlib filters/queues/handlers | O01/O12 destination alternative; JSON rendering alone is insufficient context or telemetry. |
| ECS schema families and native bridges | Optional O11 backend projection; retain mapping/version, no redefinition of internal identity. |
| OTel API/SDK/providers/scopes/resources and initialization | Select O02/O05/O12; application owns lifecycle, no SDK initialization in generic lower imports. |
| Spans, events, links, exceptions/status, sampling, processors and limits | Select O05/O12; keep logs distinct, failures honest, sampling visible. |
| Metrics/instruments, views/histograms, readers/temporality, exemplars and numerical semantics | Select O06; independent of D6 policy authority. |
| Logs, correlation, processing and instrumentation | Select O01/O05/O11; structure before formatting, maturity qualified at chosen version. |
| Context, async/thread/process propagation, W3C, baggage and alternative formats | Select O05/O10; W3C default, additional formats only for an actual peer; baggage allowlisted. |
| Zero-code/programmatic instrumentors, hooks, duplication, HTTP/SQL/GenAI conventions | Select programmatic route O11; wrappers unnecessary; SQLCommenter optional only if a DB trace consumer warrants it, parameter/content capture off. |
| Semantic conventions, resource detectors and schema stability | Select explicit local identity O01/O11; cloud/Kubernetes detectors only in those deployments, no speculative metadata-network calls. |
| OTLP/exporters/multiple destinations, Collector and durability | Select local native file and optional network O04/O11/O12; separately managed collector; no durable-audit claim. |
| Environment/declarative configuration and differing precedence | O02 advanced explicit source; no silent environment/file merge. |
| Samplers/processors/exporters/detectors and other extensibility | Use native mechanisms first; custom code only for a named gap, not an application plugin platform. |
| Trace/metric composition and continuous profiling boundary | O06; profiler integration deferred to an attribution need with full Typer workflow. |
| Resource lifecycle, concurrency, SDK self-observation and deterministic tests | Select O08/O12; tests/local exporters do not qualify remote delivery. |
| Logfire instrumentation, stdlib/structlog bridges, sampling/scrubbing, queries, portability and languages | Optional O11 composition; query adapter qualification remains prerequisite, no mandatory service. |
| picologging native logging implementation | Not selected: no unique functional benefit versus compatibility/maintenance burden; reconsider only for a measured bottleneck. |
| Cross-library structured schemas, three buffering meanings, exception exposure and combinations | O01/O05/O07/O09/O12 preserve semantic differences; no conflation of action buffers, export batches and forensic buffers. |

Additional primary contracts consulted on 2026-10-31:

- [Typer context](https://typer.tiangolo.com/reference/context/) via Context7: supported resource
  ownership; [Typer 0.27.3 source](https://github.com/fastapi/typer/tree/0.27.3) for version-specific boundaries.
- [Rich 15 Live](https://github.com/Textualize/rich/blob/v15.0.0/docs/source/live.rst),
  [logging](https://rich.readthedocs.io/en/stable/logging.html), and
  [console](https://rich.readthedocs.io/en/stable/console.html): stream redirection and presentation.
- [structlog stdlib integration](https://www.structlog.org/en/stable/standard-library.html),
  [contextvars](https://www.structlog.org/en/stable/contextvars.html), and
  [testing](https://www.structlog.org/en/stable/testing.html): preserve processor/context semantics.
- [OTel Python source](https://github.com/open-telemetry/opentelemetry-python/tree/v1.45.1),
  [logging integration](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html),
  and the file exporter source linked above. Context7 corroborated SDK provider/flush APIs;
  its available indexed revisions lag the supplied guide, so exact pins need source qualification.
- [FastMCP 4.1.3 telemetry](https://github.com/prefecthq/fastmcp/blob/v4.1.3/docs/servers/telemetry.mdx),
  [client logging](https://github.com/prefecthq/fastmcp/blob/v4.1.3/docs/clients/logging.mdx),
  [client progress](https://github.com/prefecthq/fastmcp/blob/v4.1.3/docs/clients/progress.mdx).
  Context7 and installed `server/context.py` and `server/middleware/logging.py` establish token,
  notification routing and serializer-fallback limits.

## 5. Priorities, architectural judgment and decisions to carry forward

Deliver the Typer path as a coherent capability, not merely flags which emit data nobody can inspect.
Recommended ordering is O01/O02/O12 foundation, O03/O04/O05/O09 complete local investigation,
O06/O07/O08 operational/test depth, and O10 MCP parity. Develop shared services for MCP while
building the local path; MCP does not gate the primary development UX. O11 advanced deployment
integrations follow the local route. This is dependency/priority advice, not an adopted execution
queue. All opportunities remain unscheduled proposals owned here.

A1: Proposed owners localize event meaning in existing domain/failure owners, lifecycle at entry
points, query/export below interfaces and presentation in CLI. A2: diagnostic occurrences, spans,
metrics, task state and evidence references have separate meanings; partial coverage is explicit.
A3: native processors/exporters/renderables compose into both surfaces without a universal wrapper.
A4: per-process segments, signal batching, early filtering and bounded display/export avoid a shared
hot writer or repeated whole-history hydration. These are qualitative design judgments, not measured
latency/capacity claims. Native file exporter/Python compatibility, query projection behavior and
process integration must be qualified before implementation acceptance.

Applicable CI-01/04/06/11/12/13 concerns are attribution, unknown coverage, model-relative claims,
snapshot-consistent references and reference-data separation. No call-graph/relationship analysis
is proposed, so graph-specific profile mechanisms are not introduced. Diagnostic support bundles
must not expose independent evaluation references to extraction/model sessions.

Potential rule/architecture impacts to confirm during plan creation:

| Reference | Proposed impact and owner |
|---|---|
| RC01 | Extend D8/D9/Settings with shared diagnostic services and explicit CLI overrides; preserve dependency direction and lazy runtime ownership. |
| RC02 | Define archive/schema/retention and diagnostic-query contracts with scoped access; D6 task/metric authority and D3 semantic persistence remain authoritative. |
| RC03 | Add explicit telemetry carriers/credential boundaries to D6 worker and D8 supervision lifecycles; no ambient provider/export selection. |
| RC04 | Future declarative configuration, hosted diagnostic access and remote query adapters extend current settings/deployment targets; their prerequisites remain explicit. |

No accepted decision or active plan is changed by this review. A selected composition warrants the
normal ADR/architectural-owner route for meaningful alternatives; dependency additions alone do
not require ADRs. Plan creation should settle exact package pins, schema/segment format,
rotation/retention defaults, shutdown budget and the concrete remote adapter (if selected), carrying
these mechanisms and limits forward. User-facing workflows above establish the design direction;
illustrative command spelling is not a frozen public API migration.

## 6. Acceptance scenarios and evidence limits

These are proposed future delivery checks, not tests run in this review:

| Scenario | Required observation |
|---|---|
| Real installed Typer run + concurrent warnings + live display + JSON | Valid result-only stdout, coordinated stderr, retained structured events and causal references. |
| Help, bad option, invalid settings, DB unavailable, unexpected exception | Correct exit/classification, safe early diagnostics, no eager DB/export on help, no swallowed exception. |
| Local-only investigation after process exit | Events/trace/metrics/explanation/support export work without network, SDK wrapper or alternate UI. |
| Retained files interrupted, rotated, expired or sampled | Valid preceding records readable; explicit coverage, stable cursor/export pinning and honest loss. |
| Multiple threads/async tasks/spawned PDF and MCP children | No context leakage; actual parent/link identity, independent process writers, credential isolation. |
| Expected refusal, retry/recovery, cancellation, failed publication | Original outcomes remain distinct; source/task records control truth, not progress/span status. |
| Repeated CliRunner/direct server invocations and injected providers | No duplicate handlers/providers, leaked threads or shutting down host resources; process tests also cover uncaught exceptions. |
| Real stdio MCP client with/without log/progress handling | Clean protocol stdout, token-aware notifications, typed pages equal Typer meaning, native/propagation/off behavior qualified. |
| Failed exporters, full queue/disk, denied paths and slow shutdown | Defined drop/failure observations, bounded cleanup and original failure preserved; explicit export failures remain failures. |
| Redaction including middleware serializer failure and support bundle | Secrets/content/SQL values stay excluded; controls do not depend solely on a serializer or screen rendering. |
| Metrics restart/sampling and incident grouping | Correct units/temporality/count scope, no cumulative double count, trace links and unavailable exemplars explicit. |
| Future hosted user and independent reference material | Cross-principal/run access denied; extraction sessions cannot obtain evaluation references through diagnostics. |

**Evidence on 2026-10-31:** source/document inspection completed; native API details above are
Interface-checked only. Runtime logging, exporter compatibility, local DuckDB projections, remote
backend delivery, real Typer/MCP journeys and quantitative benefits are **not_run** for this scope.
No production dependencies were installed and no product tests/probes were needed to select this
proposed direction. Independent focused advice corrected failure-buffer selection, process/global
provider lifetime, duplicate archive counting and security compartment handling in this revision;
it was not a separate recommendation audit. Documentation publication checks are recorded with the review commit/handoff;
those checks do not qualify the application or concurrent PDF work.

### Publication checks — 2026-10-31

- **passed:** `just turn-end` (ADR index and required formatting; concurrent files remain owned by their existing work).
- **failed:** `just docs-check`; existing `docs/plans/parsing-pipeline/source-decomposition-and-html.md` links to removed `python/corpus-structure/src/corpus_structure/ingest/profile.py`. No repair to that separate plan is included here. The build also warned about existing `<descriptor>` tags in phase-0 plans.
- **passed:** focused stdlib link-target and whitespace inspection of this review (local Markdown destinations only); it does not replace the failed complete publication check.
- **not_run:** `just test-all` and runtime logging journeys; this is a documentation review, with no logging implementation to qualify.
