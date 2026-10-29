# FastMCP

**Realization assessed:** FastMCP 4.1.3.

**Researched:** 2026-10-29 by the R6 interfaces cluster.
- The [overview](../../../libraries/fastmcp.md) was read end to end.
- Follow-ups:
  - Context7 `/prefecthq/fastmcp/v4.1.3`, which matches the installed release.
  - Installed source: `server/server.py`, `tools/function_tool.py`, `tools/tool_transform.py`,
    `server/middleware/*` and `server/mixins/transport.py`.
  - Two probes using the in-process `Client`
    ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-interfaces/README.md)).

## Reusable opportunity types

<a id="fastmcp-tool-refusal-translation-middleware"></a>

### `fastmcp/tool-refusal-translation-middleware`

**Need.** Turn domain refusals into tool-error results (`isError`) in one place, for every tool.

**Recognize.** Repeated `try/except X → ToolError` inside tools.

**Mechanism.**
- Any tool exception that is not a FastMCP error is wrapped as
  `ToolError("Error calling tool 'name': msg") from original` before middleware sees it. It is also
  logged at error level with a traceback.
- A small custom `Middleware.on_call_tool` can check `error.__cause__` against a list of refusal
  types and re-raise `ToolError(str(cause))`. The client then receives `isError` with the bare
  message (probe).

**Do not use the built-in `ErrorHandlingMiddleware()` with defaults.** `ToolError` is not an
`MCPError`, so the middleware turns it into a protocol error (-32603). Every tool error becomes a
JSON-RPC error rather than an `isError` result (probe).

**Conditions.**
- Middleware order matters.
- `RetryMiddleware` inspects only one level of cause.
- Raising `from None` hides the cause.
- Refusals that a tool deliberately returns as typed results must not be raised.
- With `mask_error_details=True`, unhandled messages are masked.

<a id="fastmcp-response-size-backstop"></a>

### `fastmcp/response-size-backstop`

**Mechanism.** `ResponseLimitingMiddleware(max_size=, tools=None|[...])` measures the serialized
result. When the result is over the limit, it returns truncated text with no structured content.

**Side effect.** `on_list_tools` **removes `outputSchema`** from every limited tool, which means all
tools when `tools=None` (probe).

**Limit.** It is a lossy backstop, not a response budget: it offers no continuation, and typed
results are lost.

<a id="fastmcp-sync-tool-execution-context"></a>

### `fastmcp/sync-tool-execution-context`

**Model.**
- A synchronous tool runs by default in an AnyIO worker thread (`anyio.to_thread.run_sync`), and so
  does its argument validation.
- With `run_in_thread=False`, or for `async def` tools, the body runs on the event-loop thread.
- `FastMCP.run()` calls `anyio.run` on the calling thread.

**Probe results** (in-process `Client`):
- The default synchronous tool ran on the worker thread, and a signal-based deadline raised
  `OffMainThread`.
- An inline or async tool ran on the main thread, and the deadline fired.

**Conditions.**
- An inline or async body blocks the event loop while it runs.
- `run_in_thread=False` together with `timeout=` is refused at registration.
- `timeout` cannot stop a synchronous worker thread.
- HTTP and uvicorn layouts were not tested.

<a id="fastmcp-bound-tool-input-schema"></a>

### `fastmcp/bound-tool-input-schema`

**Routes.**
- `Tool.from_tool(parent, transform_args={"arg": ArgTransform(type=Model)})` rebuilds the advertised
  schema from a `TypeAdapter`.
- A custom `Provider` lists tools dynamically.
- The tool can be registered after the release is known.

**Conditions.**
- Tool listings grow with the schema.
- Argument validation fails before the tool body runs, so the tool's typed refusal shape is skipped.
- The schema must be well-defined for everything the server instance serves.
- Evidence: source only.

## Applicability at source `d739b88` (re-checked at `3d97504`)

<a id="applicability-cbo-012"></a>

### CBO-012 — refusal mapping and MCP conventions: **fits with conditions; premise partly stale**

**Opportunity:** [CBO-012](../../codebase/consumers-and-operations.md#cbo-012). **Types:**
refusal-translation-middleware, response-size-backstop, bound-tool-input-schema.

**Premise update (`3d97504`).**
- `intervene/server.py` now delegates to `build_semantic_server`.
- The legacy `ResponseLimitingMiddleware` backstop and the `DBAPIError → ToolError` mapping no longer
  exist anywhere.
- The default session (`SemanticProjectSession`) spans runs.
- A new `record_direction` tool has no refusal mapping.
- At the baseline, the legacy `tools=None` backstop was also removing every legacy tool's
  `outputSchema`, which went unrecorded.

**Fit.**
- **Refusal mapping.** A custom `on_call_tool` middleware can own refusal translation.
  - `propose_claims` returns refusals as typed `SubmissionResult` dispositions and must stay outside
    the mapping.
  - Cost: FastMCP logs the wrapped exceptions with tracebacks. A shared decorator avoids that.
- **Response backstop.** Fits only as a lossy backstop, scoped with `tools=[...]` if output schemas
  are to stay advertised.
- **Release-bound input schema.** Possible but weak. A session that spans runs makes a single
  release schema ill-defined, and early validation would bypass the held/refused disposition and the
  one-correction retry semantics.

<a id="applicability-cbo-023"></a>

### CBO-023 — math deadline: **settled by probe**

**Opportunity:** [CBO-023](../../codebase/consumers-and-operations.md#cbo-023). **Type:**
sync-tool-execution-context.

- **Default synchronous tools** run off the main thread, so the grammar raises `OffMainThread`.
- **`async def` or `run_in_thread=False` tools** run on the main thread under `ci mcp serve`, so the
  deadline works there. The cost is that the session blocks while the tool runs, and `timeout` cannot
  be combined with it.
- **No MCP path imports the grammar today.** The risk materializes only if an SP-08 tool calls
  finalize or equivalence.
- `ci run finalize` runs on the main thread.
- A process-based deadline is a standard-library alternative.

<a id="applicability-cbo-001"></a>

### CBO-001 (informs)

- FastMCP supplies typed results through Pydantic return models with `outputSchema`, and in-process
  testing through `Client`.
- It does **not** supply result pagination or response budgets, so the continuation and budget
  envelope stays with the application.

## Coverage limits

- Probes used only the in-process transport.
- A stand-in refusal class was used.
- Logging was not examined.
