# MCP and optional external integrations

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns LOG-09/10 and I06. Consumes shared LOG-01/03 contracts, LOG-05 context and LOG-08 support.
Serves O10/O11, E06. No alternate interface is necessary for a selected application capability.

<a id="LOG-09"></a>
## LOG-09 — Native MCP correlation and typed diagnostic parity

Extend current FastMCP server lifespan and request middleware. Native OTel mode is native by
default; propagation_only is selected only when another MCP-aware layer owns spans, and off also
removes native propagation. Do not stack Logfire instrument_mcp intended for SDKv1 over FastMCP4.
Cover direct server construction, embedded/injected sessions and `ci mcp serve`, not only Typer
bootstrap. Host providers remain host-owned; request context resets after failures/cancellation.

Expose diagnostics_find/explain/summary and support_preview/export using the same services/results
as Typer. Typed parameters carry run/filters and opaque continuation, not arbitrary SQL or paths.
Tools/resources enforce run/principal and source/evaluation compartments before query selection.
An artifact reference is scoped access, not a server filesystem disclosure. Discovery visibility
is not authorization; future authentication scopes/roles supplement current principal enforcement.
Do not claim a hosted multi-user service until its actual identity/deployment prerequisites exist.

Use Context.log for selected plain-text notifications plus safe extra fields and report_progress
for actual token-associated progress. Clients may not request/handle progress, may change logging
level or disconnect; retained reads still work. Neither absence of notifications nor a progress
bar is task truth. Prevent loops through fastmcp.server.context.to_client. Disable raw payload
logging: custom serializer failure can fall back to the default serializer, so it is not a safe
redaction boundary. No Rich/ANSI/banner/SDK stdout output may pollute stdio protocol bytes.

Acceptance: real installed stdio client captures protocol bytes and log/progress callbacks separately;
the same scope queried through Typer and MCP has matching meaning; modes, ignored notifications,
reconnects, denied scopes and serializer-failure privacy are exercised. A mocked client does not
qualify this path. Existing worker task authority and bounded response semantics survive.

<a id="LOG-10"></a>
## LOG-10 — Qualified configuration, destinations and remote reads

Programmatic initialization is primary. Export selected telemetry via explicit local file and optional
OTLP HTTP/gRPC destinations, with masked endpoint/auth, TLS/compression/timeouts and per-signal
settings. Separate destinations may still contend: qualify queues and drain under failure. Native
batching is not durable storage acknowledgment; exporters do not turn local logs into audit records.

Add advanced declarative SDK config only as an explicit `ci` selection validated and explained by
config/check commands. Equivalent environment keys may be bypassed by file configuration; show
that mode/provenance rather than claiming ordinary layering. Reject contradictory selections.
The exact qualified configuration package/version belongs to LOG-00/I03. Do not expose an unbounded
raw SDK control tree as thousands of generated Typer options; support typed ordinary controls plus
an explicitly validated advanced config path with all inspection through Typer.

I06 qualifies LogfireQueryClient/query_json_rows/query_arrow/query_csv as a concrete optional
remote route. Require bounded time windows, read tokens, output limits, visible ingestion delay,
429/Retry-After handling and actual backend availability. Arrow attributes may remain JSON; preserve
them honestly. Query stable IDs by equality rather than assuming text search indexes every token.
Local queries remain available without tokens. A localhost OTLP URL does not imply a local query
backend; Logfire self-hosting is separate infrastructure, not an SDK feature or this plan's install.

ECS is an optional destination with explicit mapping. ecs-logging2.3 emits ECS1.6, not arbitrary
newer conformance; dotted/nested collisions fail, and its structlog formatter does not reproduce
all stdlib caller/exception fields. Structured exception lists need an intentional string stack
projection. Copy destination-owned nested structures before ECS normalization mutates them.
python-json-logger is an alternative destination formatter, not another schema authority: fmt is
not an allowlist, static_fields are overwriteable, and fallback stringification is not safe capture.
Serialization must preserve one-line framing and declared field fidelity.

All selected remote query/export/config operations have `ci diagnostics` entry points; SDK-specific
CLI tools, vendor dashboards and vendor MCP servers are optional conveniences. Optional imported
legacy receipts retain original provenance and bounded known parsing rules, never speculative
reclassification of arbitrary text as structured truth. Collectors, tail sampling and backend alert
rules can consume application-exported config; infrastructure lifecycle remains separately managed.

Completion: local export/config works without a backend; real selected remote write/read is qualified
with actual credentials and retention/ingestion conditions. Missing I06 credentials/endpoint marks
remote acceptance blocked, never passed by mocks. Other selected scope is independently executable.

Sources: [FastMCP](../../libraries/fastmcp.md) §§2.4,5,7,8.4,11;
[Logfire](../../libraries/logging/pydantic-logfire.md) §§8–10,13–16;
[OTel](../../libraries/logging/OpenTelemetry_Python.md) §§5,9–10;
[ECS](../../libraries/logging/ecs-logging.md) §§3–8;
[JSON logger](../../libraries/logging/python-json-logger.md) §§3–8.

## I06 and instrumentation disposition — 2026-11-01

Use direct OTel ownership for native FastMCP4 spans; local Logfire providers do not automatically
receive native global spans. No real MCP protocol journey was run by this investigation.
Public logfire.query_client.LogfireQueryClient is available in installed Logfire/logfire-sdk5.4.0
after adding HTTPX0.28.1; released5.4 already uses the split SDK distribution. Public query source
was inspected after presumed GitHub paths returned404; no API absence was inferred from404.

Local MockTransport checks exercised info(), required min_timestamp, explicit max_timestamp/limit,
/v2/query body, schema/data to columns/rows mapping and QueryRateLimitedError.retry_after. Exactly
three synthetic requests occurred, without automatic retry. Native default timeout is30s; choose
an explicit application timeout. CSV/Arrow runtime fidelity, live authentication, retention and
ingestion delay remain not_run. No authorized endpoint/read token/test scope was supplied, so
live I06 acceptance is blocked. Existing ingestion credentials would not establish read permission
or authorize a new write destination. See logging.i06 and the coordinator's remote evidence link.
