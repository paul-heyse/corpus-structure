# Library leverage R6: interfaces and rules (2026-10-29)

Three small pure-Python probes for the first library applicability assessment (cluster R6). They
settle fit questions that the documentation and the installed source left open. There is no
database connection, no network service and no installation.

**Environment.** Python 3.14.10 through `uv run --no-sync python`, from the repository root,
against the installed `.venv`. The libraries are FastMCP 4.1.3 (MCP SDK 2.3.0, anyio worker
threads), rule-engine 5.1.0 and Pydantic 2.14.1. The source tree was at `d739b88`.

## Probe 1: which thread runs a FastMCP tool body?

**Question.** Where does FastMCP 4.1.3 run a synchronous tool, an inline synchronous tool and an
async tool? Does a `SIGALRM` deadline work in each place? The probe uses the repository's own
`grammar.deadline`, which calls `require_main_thread`.

**Command.**
`uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-interfaces/probe_fastmcp_threads.py`

**Raw output.** [`probe_fastmcp_threads.out.txt`](probe_fastmcp_threads.out.txt)

**Outcome: passed (question settled).**

| Tool | Thread that runs it | Deadline result |
|---|---|---|
| Synchronous tool, default settings | AnyIO worker thread | `OffMainThread` |
| Synchronous tool, `run_in_thread=False` | the event-loop thread, which is the main thread here | `Expired` (the deadline fired) |
| `async def` tool | the event-loop thread, which is the main thread here | `Expired` (the deadline fired) |

FastMCP refuses to register a tool that combines `run_in_thread=False` with `timeout=`. It raises
`ValueError`.

**Limits.**
- The in-process `Client` ran the event loop on the main thread through `asyncio.run`.
  `FastMCP.run()` also calls `anyio.run` on the calling thread, so in the real server the
  event-loop thread is the main thread only when `run()` is called from the main thread.
- The probe does not test HTTP transports, uvicorn worker layouts or concurrency between tool
  calls.
- An inline or async tool blocks the event loop while the deadline runs.

## Probe 2: rule-engine type mapping and the owner of an attribute access

**Questions.**
1. Which annotation shapes from a release-generated Pydantic model map through
   `DataType.from_type`?
2. Can `type_resolver_from_dataclass` accept a `BaseModel` or a Pydantic dataclass?
3. Does the non-underscore route `DataType.NULLABLE.unwrap(node.object.result_type)` give the same
   owning OBJECT as the private `GetAttributeExpression._object_type`?

**Command.**
`uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-interfaces/probe_rule_engine_types.py`

**Raw output.** [`probe_rule_engine_types.out.txt`](probe_rule_engine_types.out.txt)

**Outcome: passed (questions settled within the shapes tried).**

**`DataType.from_type`.**
- These shapes map:
  - `str` maps to `STRING`.
  - `Annotated[str, Field(...)]` maps to `STRING`; the Pydantic constraint is discarded.
  - `list[str]` maps to `ARRAY(STRING)`.
  - `dict[str, int]` maps to `MAPPING(STRING, FLOAT)`.
  - `str | None` maps to `NULLABLE(STRING)`.
- `tuple[str, ...]` maps to `ARRAY(UNDEFINED)`, so the element type is lost.
- These shapes are refused:
  - `Literal['x']` raises `TypeError`.
  - A `StrEnum` raises `ValueError`.
  - A discriminated union of models raises `ValueError`.
  - A `BaseModel` class raises `ValueError`.

**`type_resolver_from_dataclass`.**
- It refuses a `BaseModel` with `TypeError`, because the argument must be a dataclass.
- It accepts a Pydantic dataclass, because `dataclasses.is_dataclass` is true for one.
- With `strict=True`, it fails on the enum field.
- With `strict=False`, it maps the enum field to `UNDEFINED`.

**Owner of an attribute access.** The non-underscore route agrees with `_object_type` in every
case tried:
- plain access;
- null-safe access (`&.`);
- a comprehension variable.

**Limits.**
- The route depends on `rule_engine.ast` node attributes (`object`, `result_type`). Upstream
  documents that module as private, so this narrows the private surface without removing it.
- A schema that uses `OBJECT.reference(...)` or `OBJECT.self` would need reference resolution.
  The probe built no references.
- For a receiver that is not an OBJECT, `result_type` is a scalar or compound type. The caller
  must check `DataType.is_type(t, DataType.OBJECT)`.

## Probe 3: FastMCP error translation and response-limiting middleware

**Question.** What reaches the client when a tool raises a domain refusal? The probe compares three
cases:
- no middleware;
- the built-in `ErrorHandlingMiddleware()` with its defaults;
- a ten-line custom `on_call_tool` middleware that maps the wrapped cause to `ToolError(str(cause))`.

It also asks whether `ResponseLimitingMiddleware` changes the tool listings or the structured
content of a response.

**Command.**
`uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-interfaces/probe_fastmcp_errors.py`
(stderr discarded)

**Raw output.** [`probe_fastmcp_errors.out.txt`](probe_fastmcp_errors.out.txt)

**Outcome: passed (questions settled).**

**Error translation.**
- *No middleware.* The client receives an `isError` tool result whose text is
  `Error calling tool 'refuse': <message>`. FastMCP wraps the exception as `ToolError(...)`, keeping
  the original exception as `__cause__`, before any middleware sees it.
- *Built-in `ErrorHandlingMiddleware()`.* The client receives a protocol-level `MCPError` with
  `Internal error: …`, and code -32603 according to the installed source. There is no `isError`
  result. `ToolError` is not an `MCPError` subclass, so `transform_errors=True` turns it into a
  JSON-RPC error. The cause-type mapping compares exact types, so a `ValueError` subclass still
  becomes -32603.
- *Custom middleware.* The client receives an `isError` result with the bare refusal message.

**Response limiting.**
- `ResponseLimitingMiddleware` with `tools=None` removes `outputSchema` from **every** tool in the
  listing.
- With `tools=[...]`, it removes `outputSchema` only from the named tools.
- The `big` row in the output is a response *over* the limit, despite its key name. It came back as
  a truncated text-only result without `structuredContent`.

**Limits.**
- Only the in-process transport was tested.
- The real refusal classes were not imported; a `ValueError` subclass stands in for them.
- Logging was not examined. According to the installed source, FastMCP logs the wrapped exception
  at error level with a traceback.

## Files

- `README.md`
- `probe_fastmcp_threads.py`
- `probe_fastmcp_threads.out.txt`
- `probe_rule_engine_types.py`
- `probe_rule_engine_types.out.txt`
- `probe_fastmcp_errors.py`
- `probe_fastmcp_errors.out.txt`

No evidence record has been written. The coordinator decides whether to accept these results under
ADR-0010.
