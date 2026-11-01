# Diagnostic contracts, runtime and instrumentation

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns package state, I01–I06, opportunity disposition and accepted rule decisions.
This plan explains LOG-00/01/02/05 and consumes O01/O02/O05/O12, E01/E02/E04.

## Intended behavior and reusable foundations

A command emits safe structured occurrences and selected causal spans, regardless of whether it
runs interactively, in a test, from a script or through an owned child. Methods continue to use
MethodContext's ordinary logger. Domain outcomes stay owned by their existing result/operation
contracts. Safe diagnostic construction is reusable without Typer, Rich, DB access or an exporter.
Runtime acquisition is explicit and lazy; generic module imports do not configure global logging.

Current roots are `cli/app.py`, `cli/output.py`, Settings, `core/method.py`, orchestration's
MethodContext construction, `intervene/server.py`/`semantic_server.py`, `intervene/automated.py`
and `ingest/pdf_worker.py`. The D6/D8/D9 contracts determine integration; do not create a second
scheduler, settings service or generic plug-in framework.

<a id="LOG-00"></a>
## LOG-00 — Resolve composition and qualify the library boundary

Settle I01/I02/I03 before implementation contracts depend on them. Inspect exact package source
and metadata for Python3.14.10. Starting candidates from the guides are structlog26.1.0,
Logbook1.10.1, OTel1.45.1/contrib0.66b1 and Logfire5.4.0; these are research candidates, not an
instruction to install an unqualified combination. Produce a compact decision in this plan with
exact selected registry pins, required extras, API imports, family compatibility, rejected options
and local initialization route. Deliberate installation later uses bounded manifest/lock changes,
not wholesale resolution. `just ready` follows dependency changes, not this documentation task.

Compare two questions separately: event/routing composition (structlog/stdlog vs Loguru) and Python
instrumentation (direct OTel vs local Logfire). Preferred event composition remains structlog/stdlog:
processors preserve application semantics and existing library producers. Loguru has worthwhile
rotation/retention/compression and Handler sinks, but `enqueue=True` uses an unbounded SimpleQueue,
`catch` suppresses by default and `diagnose` exposes values by default. Do not add a second global
router merely to gain file rotation. Select a different composition if it demonstrably removes
more machinery while preserving bounded delivery and field fidelity.

Logfire `configure(local=True, send_to_logfire=False, console=False)` is eligible for local
instrumentation, not dismissed as a hosted dependency. Compare `instrument_pydantic(record='failure')`,
selected-engine/client SQLAlchemy/HTTPX instrumentation and `capfire` against direct instrumentors.
Resolve import timing: Pydantic instrumentation applies to subsequently defined models and selective
auto-tracing is import-sensitive. Never eagerly import every model/kernel to activate it. Native
FastMCP4 tracing remains the MCP instrumentation owner. Claude Agent SDK instrumentation is not
instrumentation of the existing external claude CLI. Adaptive minimum-duration tracing does not
retain the first triggering call. These limits can determine selection.

For causal inspection, compare OTel parent/links against Eliot `Parser.parse_stream`,
`Task.is_complete`, ActionType start/success fields and typed structural assertions. Do not coerce
an OTel graph into an Eliot tree or treat an action's normal return as successful publication.
Select Eliot only if the intended incomplete-history workflow needs its distinct semantics; keep
OTel as the interoperable causal identity otherwise. Evidence is a specified out-of-order/missing
terminal/fan-in example, not a benchmark campaign. Store a warranted probe in the existing dated
evidence route, never a new scratch/process framework.

<a id="LOG-01"></a>
## LOG-01 — Meaning, configuration and privacy contracts

Record meaningful architecture choices through an ADR and D6/D8/D9 owner updates, using the already
accepted RC01–RC04 decisions. Diagnostic structure is a versioned application contract; do not add
corpus knowledge-model tables just to persist logs. Define typed occurrence/context, scope/query,
coverage and support-selection contracts at the smallest existing/new coherent owners.

Required occurrence meaning: occurrence ID, schema/code/severity, producer UTC timestamp,
component/operation, safe attributes, optional domain references and trace/span identity. Reserve
identity/principal/code/time fields against caller override; namespace weaker foreign LogRecord
extras. Distinguish producer time from observation/export time. Reject or mark unsupported values
rather than stringify arbitrary objects, model instances or whole source products. Artifact IDs
permit later permission-checked hydration. Domain codes/refusals reuse current classifications.

Define normal/debug/incident/off profiles and explicit Settings fields for capture/display levels,
paths, selected instrumentation, destinations, retention and bounds. Initial defaults: normal,
INFO console/events, meaningful selected operation traces enabled, remote off, locals/payloads off.
Incident DEBUG capture is independent of console threshold; LOG-04 defines process-wide capture
admission and original-ID retention of released records, so concurrent scopes cannot multiply
unbudgeted buffers. Only explicit Typer options override
constructor/environment resolution; report safe provenance with `get_parameter_source` rather
than comparing a value with its default. No new scattered CORPUS_/OTEL_ environment reads.

Select permitted fields before fan-out, queuing, redaction-sensitive buffers or serialization.
Freeze safe normalized context; branches receive destination-owned nested values because binding
is shallow and ECS can mutate nested data. Sensitive capture requires explicit scoped selection,
preview and source/evaluation access permission. Security compartments are selected from the
trusted caller, never from an arbitrary event field or trace ID.

<a id="LOG-02"></a>
## LOG-02 — Native pipeline and process/invocation lifetime

Build one real `ci` operation using event construction, stdlib routing, Rich diagnostics and local
OTel output, with Settings activation and original result/exit semantics. Process SDK owner installs
providers once; invocation owns spans/context tokens/consoles/handlers. Embedded callers inject
providers or reuse their host, which this application never shuts down. Spawned children initialize
independently. Repeated test invocations must not shut down/reinstall process globals.

Capture safe producer context, origin and exceptions before queue delivery; a listener formatter
cannot recover the producer's active context. Configure `ExceptionDictTransformer(show_locals=False)`
explicitly. Preserve a renderer-specific exception branch without leaking raw tracebacks/frames into
retained buffers. No handler recursively consumes its own export errors.

The ProcessorFormatter topology requires `wrap_for_formatter`, foreign_pre_chain and stripping
processor metadata before serialization. `render_to_log_kwargs` is a different topology. Do not
DropEvent inside a formatter or feed already formatted JSON strings into an OTel structured handler.
Use producer/logger/handler filtering appropriate to each branch; keep diagnostic capture eligible
even if console filtering hides it. QueueHandler preparation must not destroy required exception
fields. A direct synchronous local file path is acceptable for short commands; queues are added
only where blocking sinks need isolation and have explicit capacity/drop behavior.

Use FileSpanExporter/FileMetricExporter/FileLogExporter with explicit owned paths/streams. Never
accept their stdout default. Sampling of selected operations is AlwaysOn locally by default; losses
still occur under disk/queue/shutdown failure. Standard processors discard unsampled RECORD_ONLY
spans. Opt-in upstream sampling marks local and remote coverage partial. Do not introduce a custom
full-local/sampled-remote processor unless an actual deployment requires that distinction.

I05 establishes actual exporter timeouts and shared cleanup deadline. Proposed defaults are2s
network request timeout and5s total diagnostic shutdown budget, configurable as operational bounds,
not measured guarantees. Final metric collection precedes drain; periodic intervals alone can miss
short commands. An exporter/process callback that cannot honor deadlines remains an acceptance
block, not something certified by `OTEL_BSP_EXPORT_TIMEOUT`. Original domain exceptions/cancellation
survive cleanup; exporter failure cannot retroactively fail committed domain work.

<a id="LOG-05"></a>
## LOG-05 — Actual producer, dependency and child integration

Migrate run/task/attempt operations, methods, source conversion/recognition, preparation/admission,
queries/exports, evaluation and supervision. Every new boundary records only its owned semantics;
reuse existing result/receipt references rather than logging payloads. Capture selection/reuse,
refusal, recovery and cancellation without duplicating domain lifecycle state.

Use programmatic supported HTTP/DB/model instrumentors at engine/client ownership. Choose one
layer per physical call, not SQLAlchemy plus duplicate driver spans. Allowlist W3C carriers into
threads/spawned PDF workers and owned MCP children; reset context in finally. Fan-in/reuse links
are not false nesting. External services lacking propagation remain explicit opaque spans/receipts.
Do not inherit exporter credentials or baggage into supervised model environments.

Acceptance: an installed Typer operation and spawned child retain the same domain/attempt linkage
with distinct span identities; concurrent contexts do not leak; unknown service coverage is visible;
failed values trigger classified failure events; warnings/cancellation retain their distinctions.
Use independent known event/causal expectations and fresh-process startup/cleanup controls.

## Sources and execution fit

[structlog](../../libraries/logging/structlog.md) §§2–6,8–9;
[Loguru](../../libraries/logging/loguru.md) §§4–11,15;
[Logfire](../../libraries/logging/pydantic-logfire.md) §§3,5,8,13–15;
[Eliot](../../libraries/logging/Eliot.md) §§4,9–11;
[OTel](../../libraries/logging/OpenTelemetry_Python.md) §§2–3,5–7,10–12.
These capability sources were read during preparation; I01–I03 qualify the actual selected pins.
Use processor chains and native instrumentors before bespoke wrappers. Safe context is captured
once, compact references replace payload copies, and disabled detail avoids expensive construction.

## LOG-00 investigation decision — 2026-11-01

Select structlog26.1.0 + stdlib and scoped Logbook1.10.1; retain OTel causal parent/links rather
than Eliot1.18.0's additional action identity. Select direct OTel process ownership. Qualified
isolated pins: opentelemetry-api/sdk/exporter-otlp-proto-http1.45.1; exporter-otlp-json-file and
instrumentation-logging/sqlalchemy0.66b1; HTTPX0.28.1. Pydantic2.14.1/SQLAlchemy2.1.5 were
co-resolved, and structlog/Logbook/Typer0.27.3/Rich15.0 were subsequently combined in that lock.
Loguru/Eliot/Logfire were comparison candidates, not required production additions. Product-lock
resolution and any extra instrumentors remain implementation prerequisites, not implied passes.

Exact imports: FileSpanExporter/FileMetricExporter at opentelemetry.exporter.otlp.json.file;
FileLogExporter at its private _log_exporter module; LoggingHandler at
opentelemetry.instrumentation.logging.handler. Pin and qualify that private-module boundary.
The first same-version file-exporter pin1.45.1 failed; the correct distribution version is0.66b1.

Local Logfire/logfire-sdk5.4.0 explicit spans work, but local=True leaves native global consumers
on their host provider. Its Pydantic plugin uses GLOBAL_CONFIG/default instance; local-only capture
produced no validation spans, whereas fresh global configuration captured a later-defined model.
Do not silently enable global Logfire in an embedded host. Optional Logfire/Pydantic capture needs
an explicit global-owner mode and import-order contract; it is not default instrumentation.

Native final metrics and borrowed-stream ownership passed bounded probes. force_flush(timeout=10ms)
did not preempt a250ms exporter; the configured transport timeout separately bounded a controlled
loopback request. I05 therefore remains partial: actual supported exporter execution must establish
the overall cleanup budget before LOG-02 acceptance. The disposable Typer/Rich/native-span app
passed stream separation; installed ci and real MCP integration remain not_run.

See coordinator investigation disposition and its linked evidence/records for commands, original
failures and scope. No runtime/manifest/ADR changes follow solely from these choices.
