# Library evidence: interfaces and evaluation

**Date:** 2026-10-28 · **Lane:** library research (interfaces and evaluation group) · **Status:**
evidence for the phase 0 build plan and the D-documents' "Library realization" text; not
authority. No evidence record (`records/<id>.json`) has been written or finalized.

**Question.** How should phase 0 use the libraries behind D8 (the MCP server the Claude Code
session works through, the `ci` CLI, settings) and D7 §5 (alignment and scoring), and the test
tooling of D9 §4, so that the build starts from their real capabilities? Six decisions:

1. a FastMCP 4.1.3 server for D8 §2;
2. one process or two (OPEN-D8-1, OPEN-D9-2);
3. Typer 0.27 for `ci` (D8 §4);
4. pydantic-settings 2.16 for D9 §3;
5. SciPy's assignment and bootstrap, and NumPy's `Generator`, for D7 §5;
6. Hypothesis and import-linter for D9 §1 and §4.

**Baseline.** HEAD `71bb064`, plus the uncommitted working-tree edits to D6–D9 present at 11:39 on
2026-10-28. D8 §1–§7, D9 §1–§5 and §8, D7 §3 and §5, D6 §3 and §8, and rationale §3 (P9, P10) and
§4.11 were read. D7, D8 and D9 changed during this work and their changed sections were re-read
(the D9 dependency table now lists Hypothesis and import-linter). The spike instruments
`code/instruments/align.py` and `scores.py` and their tests in `code/tests_instruments/` were read.

**Evidence labels.** *Tested* means a probe in `probes/` ran on 2026-10-28 and `probes/out/`
holds its output. *Source-read* means the installed release's source was read. *Documented*
means official documentation (Context7 or the upstream site) states it. *Proposed* is a
recommendation.

## Sources and versions

| Library | Version examined | Route |
|---|---|---|
| FastMCP (+ fastmcp-slim, MCP Python SDK `mcp`) | 4.1.3 (+ 4.1.3, 2.3.0) | [overview](../../../libraries/python_introspection/fastmcp.md) end to end. Context7 `/prefecthq/fastmcp/v4.1.3` (tools/structured output, `ToolResult`, testing, lifespan). Installed source: `fastmcp/server/{context,lifespan}.py`, `server/mixins/{lifespan,transport}.py`, `server/middleware/response_limiting.py`, `tools/function_tool.py`, `utilities/logging.py`, `mcp/server/stdio.py`. Probes P1, P2. The 4.1.4 release notes ([v4.1.4](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.1.4)) were also read |
| Claude Code (MCP host) | docs as of 2026-10-28 | [code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp) (`.mcp.json`, output limits, timeouts, description limits) and [/sub-agents](https://code.claude.com/docs/en/sub-agents) (inline `mcpServers`, agent ids, `model`) |
| Typer | 0.27.3 | [overview](../../../libraries/python_introspection/typer.md) end to end. Installed `typer/testing.py` (vendored-Click `CliRunner`). Probe P4 |
| Rich | 15.0.0 | [overview](../../../libraries/python_introspection/rich.md) end to end. Probe P4 |
| pydantic-settings | 2.16.1 installed; 2.16.2 published today | [overview](../../../libraries/data_model/pydantic-settings.md) end to end. Context7 `/pydantic/pydantic-settings` (source priority, `settings_customise_sources`). The [v2.16.1…v2.16.2 compare](https://github.com/pydantic/pydantic-settings/compare/v2.16.1...v2.16.2) was read. Probe P4 |
| SciPy | 1.18.1 | [overview](../../../libraries/scientific_compute/scipy.md) end to end. Installed `scipy/stats/_resampling.py` (`bootstrap`, `_bootstrap_iv`, `_bootstrap_resample`). Probe P3 and an inline `linear_sum_assignment` check (below) |
| NumPy | 2.5.4 | [overview](../../../libraries/scientific_compute/numpy.md) end to end, especially §6 (Generator, BitGenerator, SeedSequence) |
| Hypothesis | 6.170.12 (root dev pin); 6.170.13 published today | **No overview: re-check against one when it exists.** Context7 `/hypothesisworks/hypothesis` (settings profiles). Probe P5 |
| import-linter (+ grimp) | 2.15 (+ 3.18) | **No overview: re-check against one when it exists.** Context7 `/seddonym/import-linter` (layers: `|` and `:` siblings, `containers`, `exhaustive`). Probe P6 |
| psycopg, psycopg-pool | 3.3.6, 3.3.3 | Installed signatures only (`Connection.notifies(*, timeout, stop_after)`). The psycopg overview owns the details |

PyPI, checked 2026-10-28: fastmcp 4.1.4 (2026-10-26), pydantic-settings 2.16.2 (2026-10-28),
typer 0.27.3, rich 15.0.0, import-linter 2.15 (2026-09-04), hypothesis 6.170.13 (2026-10-28),
hypothesis-jsonschema 0.23.2 (2026-10-27), scipy 1.18.1, numpy 2.5.4, pytest-asyncio 1.4.1
(2026-10-25).

**Environments.** All runs used Python 3.14.10.

- `build/spike-venv`: typer 0.27.3, rich 15.0.0, pydantic 2.14.1, pydantic-settings 2.16.1,
  scipy 1.18.1, numpy 2.5.4.
- Root `.venv`: hypothesis 6.170.12 and pydantic 2.14.1.
- A scratch environment outside the repository (discarded) held fastmcp 4.1.3, mcp 2.3.0,
  import-linter 2.15, psycopg 3.3.6, psycopg-pool 3.3.3, anyio 4.15.1 and pytest-asyncio 1.4.1.
  To recreate it: `uv venv --python 3.14 $VENV && VIRTUAL_ENV=$VENV uv pip install fastmcp==4.1.3
  import-linter==2.15 "psycopg[binary]==3.3.6" psycopg-pool==3.3.3`.

## Probes

| Probe | Question | Command (from this folder unless noted) | Outcome |
|---|---|---|---|
| [P1](probes/p1_fastmcp_contract.py) | Strict vs loose tool inputs; `outputSchema` and `structuredContent`; text packets via `ToolResult`; lifespan count; sync tools' thread | `$VENV/bin/python -I probes/p1_fastmcp_contract.py` | passed (ran; [out](probes/out/p1_fastmcp_contract.txt)). The first run failed at registration: `WithJsonSchema` with a `$defs`/`$ref` schema raised `KeyError: '#/$defs/Claim'` (pydantic 2.14.1). The probe now inlines refs (documented in the file) |
| [P2](probes/p2_fastmcp_stdio.py) | A stray `print()` on stdio; `ctx.session_id` stability; lifespan per process | `$VENV/bin/python -I probes/p2_fastmcp_stdio.py` | passed ([out](probes/out/p2_fastmcp_stdio.json)). The first run failed through a probe bug (a local import under `from __future__ import annotations`), fixed before the recorded run |
| [P3](probes/p3_bootstrap_parity.py) | `scipy.stats.bootstrap` against the spike resampler on the recorded S0 A-versus-B counts; NaN behaviour; per-predicate, paired-difference and page-cluster forms | from repo root: `build/spike-venv/bin/python -I <folder>/probes/p3_bootstrap_parity.py recorded` (and `sorted`) | passed ([recorded order](probes/out/p3_bootstrap_parity.recorded-order.json), [sorted order](probes/out/p3_bootstrap_parity.sorted-order.json)) |
| [P4](probes/p4_typer_cli.py) | `ci` shape: groups, root callback building settings, `--json`, Rich and stderr under `CliRunner`; settings behaviour | from repo root: `build/spike-venv/bin/python -I <folder>/probes/p4_typer_cli.py` | passed ([out](probes/out/p4_typer_cli.json)) |
| [P5](probes/p5_hypothesis_pydantic.py) | `from_type`/`builds` on Pydantic models; recursive JSON; permutation and `and` reorder invariance; profiles | from repo root: `.venv/bin/python -I <folder>/probes/p5_hypothesis_pydantic.py` | passed ([out](probes/out/p5_hypothesis_pydantic.txt)), plus the inline follow-up quoted under decision 6 |
| [P6](probes/p6_importlinter_layers.py) | The D9 §1 layers contract in import-linter 2.15, with and without `intervene → serve` | `$VENV/bin/python -I probes/p6_importlinter_layers.py` | passed ([out](probes/out/p6_importlinter_layers.txt)) |

Inline check, not stored as a probe (spike venv, 2026-10-28). `linear_sum_assignment` has the
signature `(cost_matrix, maximize=False)`. For `m = [[0.5, 0], [0.98, 0.49]]`, assigning first and
then keeping pairs ≥ 0.5 keeps `(0, 0)` at 0.5. Masking pairs below 0.5 first keeps `(1, 0)` at
0.98. `lsa(-m)` and `lsa(m, maximize=True)` give the same assignment.

---

## 1. FastMCP 4.1.3 server for D8 §2

### 1.1 Submission tools: loose batch parameter, per-item validation in the body

**Mechanism (Tested, P1).** Envelope arguments are typed strictly, for example `task_id: str` and
`pass_: Literal["a", "b", "c"]`. The batch is declared `batch: dict[str, Any]` and the body
validates it item by item. That validation uses the compiled model-facing schema of the task's run
and schema version, quote location (D4 §4.3) and reference checks. The body returns a Pydantic
`SubmissionResult`: accepted count, rejected items with D8-style paths, unlocated quotes,
guideline warnings and the task state (open for one corrected resubmission, or completed). In P1
a batch with one bad item returned `is_error: false`, the structured result
`{"accepted": 1, "rejected": [{"path": "claims[1].predicate", …}], "task_open": true}`, and a
compact JSON text block of the same content.

**Why not a strict model parameter (Tested, P1).** With `batch: ClaimProposalBatch`, FastMCP
validates before the body runs. One bad item then fails the whole call with `isError` and
pydantic's own message (`batch.claims.1.predicate … [type=literal_error …]`), not D8 §2.1's
`claims[3].…` form. The body never runs, so the "one corrected resubmission" bookkeeping, quote
location and warnings cannot happen. Claude Code also trims error text over about 11,000
characters to its first and last 5,000 (Documented), which a large batch's error list can exceed.

**Where the schema lives.** Keep D8 §2.1's design: `read_instructions` serves the model-facing
JSON Schema with its hash. Do not advertise it as the tool's `inputSchema`, for three reasons:

- tool schemas are fixed for a server process, while the model-facing schema is versioned per run
  and schema version;
- it would duplicate the schema in context;
- `pydantic.WithJsonSchema` with the compiled schema's internal `$defs`/`$ref` fails at
  registration (Tested, P1 first run: `KeyError '#/$defs/Claim'`); only an inlined copy works.

A submission can carry the `schema_hash` it was given, so a stale batch is refused explicitly
(Proposed). Claude Code cuts tool descriptions and server `instructions` at 4,096 characters for
tools loaded upfront (Documented), so the description should only say where the schema comes from.

**Avoid:** strict model parameters on submission tools; `isError` for content problems (reserve it
for envelope or infrastructure failures); and the compiled schema in `inputSchema`.

### 1.2 Results: structured where a program reads them, text where the agent reads them

- A Pydantic return type yields `outputSchema` plus `structuredContent`, and FastMCP adds a text
  block with the same JSON (Tested, P1; Documented, Context7 `servers/tools.mdx`).
- Packets (`read_unit`, `read_golden_unit`, `read_instructions`) should return
  `ToolResult(content=<packet text>, structured_content={task_id, part, parts, hash})`. The model
  then reads the packet as text, not as an escaped JSON string, and no output schema is generated
  (Tested, P1).
- On the client, `result.data` is a generated dataclass (`Root` in P1). Tests should validate
  `result.structured_content` back into the Pydantic result model.
- Uncertain: the Claude Code pages read do not say whether the model sees `structuredContent` or
  only `content`. Keep every text block self-sufficient.

### 1.3 Lifespan and database pool

- **Lifespan (Source-read, Tested).** `@lifespan` (`fastmcp.server.lifespan`) yields a dict that
  tools read as `ctx.lifespan_context[...]`. Lifespans compose with `|`.
  `_lifespan_manager` is reference-counted: concurrent clients share one entry, and a later client
  re-enters it once the count drops to zero. On stdio the lifespan ran once per process (P2). In
  process, two sequential `Client(mcp)` sessions entered it twice (P1).
- **Pool (Proposed).** Open a small sync `psycopg_pool.ConnectionPool` (min 1, max about 4) in
  the lifespan, opening and closing it through `anyio.to_thread`.
- **Sync tools (Tested, P1).** Sync tools run on a worker thread, not the event-loop thread. So
  the application functions shared with the CLI can stay synchronous, matching Typer's synchronous
  dispatch.
- **Avoid:** a module-global pool, and an async-only application layer that the CLI would then
  have to wrap.

### 1.4 stdio and `.mcp.json`

- **Registration (Documented, Claude Code MCP docs).** Project scope uses `.mcp.json`:
  `{"mcpServers": {"corpus-structure": {"type": "stdio", "command": "uv", "args": ["run",
  "--directory", "${CLAUDE_PROJECT_DIR:-.}", "--frozen", "ci", "mcp", "serve"], "env":
  {"CORPUS_DATABASE__URL": "${CORPUS_DATABASE__URL:-postgresql:///corpus}"}}}}`.
  - `${VAR}` and `${VAR:-default}` expand in `command`, `args` and `env`.
  - `CLAUDE_PROJECT_DIR` needs a default when referenced in a project file.
  - Project servers need the user's approval in interactive sessions.
- **Timeouts (Documented).** A stdio call is aborted after 30 minutes with no response or progress
  notification. `MCP_TOOL_TIMEOUT` or a per-server `timeout` overrides the general tool timeout.
  A main-conversation call still running after 2 minutes is moved to the background. Subagent
  calls never are.
- **stdout (Source-read, Tested, P2).** While `stdio_server()` is active, MCP SDK 2.3.0 moves
  fd 1 onto stderr and serves the wire from a private duplicate (`mcp/server/stdio.py`,
  best-effort, POSIX). A stray `print()` inside a tool therefore did not break the stream.
  Nothing protects stdout before that point: imports, the lifespan (which `run_stdio_async`
  enters *before* `stdio_server()`), and Typer callbacks preceding `mcp.run()`. FastMCP's own
  logging goes to `Console(stderr=True)` (`utilities/logging.py`). Use `mcp.run(show_banner=False)`,
  and log through the standard library to stderr.

### 1.5 Size caps (D8 §3) and pagination

- **Caps are application contracts.** A tool takes `page_token` and `max_*` arguments and returns
  `next_page_token` and `truncated: true`. MCP's own pagination covers only list operations.
- **FastMCP's `ResponseLimitingMiddleware` is a backstop only (Source-read).** It measures UTF-8
  bytes, truncates, and collapses the result into one `TextContent`, dropping
  `structuredContent`. Register it with a generous limit, if at all.
- **Claude Code's limits (Documented).**
  - A warning appears above 10,000 tokens, and the default maximum is 25,000 tokens
    (`MAX_MCP_OUTPUT_TOKENS`).
  - Text results over 50,000 characters are saved to a file instead of the conversation, unless
    the tool declares `_meta["anthropic/maxResultSizeChars"]`.
  - D8's caps (6,000, 8,000 and 2,000 tokens) sit well below all of these.
- **The counter is open.** D8 states caps in tokens, but the server has no Claude tokenizer.
  Measuring in characters is deterministic and matches Claude Code's thresholds (see IE-3).

### 1.6 In-process testing and the trace acceptance test

- **Client (Tested, P1; Documented, `servers/testing.mdx`).** `async with Client(mcp) as c: r =
  await c.call_tool(name, args, raise_on_error=False)` exercises discovery, argument validation,
  result serialization, middleware and lifespan without a socket.
- **Fixtures.** Use a session- or module-scoped client fixture, because sequential clients
  re-enter the lifespan (§1.3).
- **Async plugin.** Use pytest-asyncio 1.4.1, which FastMCP's documentation uses, or anyio's
  pytest plugin, which is already installed with `mcp`. Both work under `--strict-markers`.
- **Trace acceptance path (Proposed).** It needs no concurrency:
  1. run the `trace` slice with `agent_mode: complete`, leaving M24 tasks `awaiting_agent`;
  2. the test drives `queue_next` → `read_unit` → `propose_claims` through `Client(mcp)` with the
     `fixtures/s0` batches;
  3. a second run reuses the submitted agent results (D6 §4) and the typed queries are asserted.

  A separate barrier test runs the orchestrator with `agent_mode: wait` in a thread and submits
  through the client, exercising `NOTIFY`.
- **Limits.** The in-process client does not test stdio framing, the subprocess environment or
  the `.mcp.json` command. One stdio smoke test shaped like P2 covers that.

### 1.7 Session identity for golden passes (D8 §2.2)

- **The MCP session id cannot tell callers apart (Source-read, Tested).** On stdio,
  `ctx.session_id` is a generated UUID. Under the 2026-07-28 protocol it changes per request: it
  differed across two calls in P2. On handshake-era connections it is fixed per connection.
  Subagents that reference the main server by name share the parent's connection (Documented). So
  the server cannot distinguish a pass-A subagent from a pass-B subagent, or either from Opus.
  "The tool records the session reference … and refuses a pass `b` from the session that wrote
  pass `a`" cannot rest on MCP session ids.
- **Mechanism (Documented, Claude Code `/sub-agents`).** A golden-pass agent file in
  `.claude/agents/` can declare an inline `mcpServers` stdio entry. "Each invocation gets its own
  connection", which on stdio means its own server process. The agent file then:
  - sets `model: sonnet` in its frontmatter;
  - narrows tools with `tools` and `disallowedTools` (for example
    `disallowedTools: mcp__corpus-structure__*` hides the main server);
  - starts the server as `ci mcp serve --profile golden`, which registers only the golden tools.

  The server mints an instance id in its lifespan (one per process, Tested, P2), records it on
  `eval.golden_pass` as the session reference, and refuses pass `b` when pass `a` has the same
  instance id.
- **Limits.**
  - The model cannot be observed by the server. Record the declared model, and audit it from the
    transcript at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`, as
    OPEN-D8-3 already does.
  - Inline servers from a project's `.claude/agents/` load only after the folder is trusted.
  - `.claude/agents/` is not gitignored, so the file would be tracked.
  - MCP tasks work only from the main conversation, so subagents cannot use the tasks extension.

### 1.8 Version caveats

- **Pin choice (Proposed, the coordinator's call).** 4.1.4 (2026-10-26) fixes, among other
  things, "stale client contexts no longer close newer sessions", Redis task credentials and
  generated-CLI JSON parameters, and bumps certifi. No listed change touches the behaviour probed
  here. Pin 4.1.3 as D9 says, or move to 4.1.4 at P0.7.
- **Locking.** The SDK beneath (`mcp` 2.3.0, `fastmcp-slim` 4.1.3) is held by the lockfile.
- **Imports.** Use `from fastmcp import FastMCP`, never `mcp.server.fastmcp`, which is the older
  lineage (overview §13).
- **Sampling.** `Context.sample()` was removed in 4.x, which is irrelevant here (P9: the pipeline
  never calls Opus).

## 2. One process or two (OPEN-D8-1, OPEN-D9-2)

**Recommendation (Proposed, reasoned from the Tested and Documented facts above; no end-to-end
PostgreSQL probe).** Use two kinds of process, with the database as the only shared state:

- the stdio MCP server, one per Claude Code session and one per golden subagent invocation
  (§1.7), thin over the application functions;
- the orchestrator, one per `ci run`.

Why:

- **Lifetime.** Claude Code starts and stops the stdio server (session end, reconnect, idle
  aborts), and golden subagents start their own instances. A run's stages cannot live in N
  short-lived processes.
- **Responsiveness.** CPU and GPU stages inside the server would contend with tool calls for the
  GIL and the worker threads.
- **stdout hazard.** Pipeline libraries that print at import or lifespan time are unprotected
  (§1.4).
- **The design already coordinates through the database.** D6 §1 makes `ops.task` with leases a
  database queue, and the agent barrier is `LISTEN`/`NOTIFY`.

Mechanics:

- **Submission side.** A submission tool commits the observation, the intervention row, the task
  status and `pg_notify('agent_tasks', <run id>)` in one transaction. PostgreSQL delivers a
  notification only at commit (PostgreSQL documentation; re-check against the psycopg overview).
- **Orchestrator side.** The orchestrator keeps a dedicated autocommit connection outside the pool
  with `LISTEN agent_tasks`, and waits in `conn.notifies(timeout=…)` (psycopg 3.3.6 signature
  verified).
- **Re-query.** On every wake-up, and on each timeout (tens of seconds), it re-reads the run's
  agent-task statuses. Notifications sent while it was not listening are lost, and lease expiry
  sends none.
- **The MCP server never listens.**

**Avoid:**

- FastMCP background tasks (`fastmcp-tasks`/Docket): they duplicate `ops.task`, need in-memory or
  Redis scheduling, and Claude Code accepts MCP tasks only from the main conversation;
- running the orchestrator inside the MCP lifespan.

A single long-lived HTTP daemon (FastMCP streamable HTTP, `type: http` in `.mcp.json`) is the
other coherent shape. It would lose the per-subagent process identity of §1.7 and add daemon
management, so it does not suit phase 0.

## 3. Typer 0.27.3 `ci` (D8 §4)

- **Groups (Tested, P4).**
  - Mounted with `app.add_typer(...)`: `db`, `project`, `schema`, `golden`, `experiment`,
    `explain`, `export`, and `mcp` (`ci mcp serve [--profile queue|golden]`).
  - Top-level commands: `ingest`, `run`, `status`, `tasks`, `query`, `eval`, `digest`, `direct`,
    `ack`, `veto`, `promote`.
  - A root `@app.callback()` builds `Settings` once into `ctx.obj`.
  - Use `Typer(no_args_is_help=True)`.
- **`--json` (Tested, P4).** Make it a per-command option through one shared alias,
  `JsonOpt = Annotated[bool, typer.Option("--json")]`. A root-callback option would have to
  precede the subcommand (`ci --json status`; overview §4.1). In P4, where `--json` is defined per
  command, `ci --json status` was rejected with exit 2, "No such option".
  - With `--json`, stdout carries only `model_dump_json()` of the result models that the query API
    and MCP return: one contract for scripts, agents and tests.
  - Otherwise Rich renders to stdout, and diagnostics and progress go to `Console(stderr=True)`.
- **Testing (Tested, P4; Source-read `typer/testing.py`).**
  - `typer.testing.CliRunner` (vendored Click) keeps `result.stdout` and `result.stderr` apart;
    `result.output` holds both.
  - A module-level `Console()` follows the runner's stream swap: the table landed in
    `result.stdout`.
  - Width is 80 when not a TTY. Fix `COLUMNS` or `Console(width=…)` in tests, and assert content,
    not ANSI.
- **Ownership (Proposed).**
  - All command modules live in one entry-point package, one module per group, as thin wrappers
    over application functions. Lower layers never import Typer or Rich.
  - D9 places the CLI in `serve/`; §6.2 shows why an entry-point layer above `serve` is cleaner.
  - The application functions are synchronous: Typer's native dispatch does not await coroutines
    (overview §11.2), and FastMCP runs sync tools in threads (§1.3).
- **Completion.**
  - `--install-completion` comes built in.
  - `autocompletion=` callbacks should read pack files (slice names from `slices.yaml`, the
    query registry), never the database, because completion runs on every Tab. They should also
    honour `ctx.resilient_parsing` (overview §6.2, §8).
  - `add_completion=False` is fine until wanted.
- **Version caveats.** Click is vendored since 0.26: no external Click plugins, `click_type` or
  rich-click patching. Keep `pretty_exceptions_show_locals=False`, the default. The application's
  Rich theme does not reach Typer's internal help consoles (Rich overview §7.7).
- **Minor.** GNU RCS also installs a `ci` command; inside `uv run` the venv's `bin` comes first.

## 4. pydantic-settings 2.16 (D9 §3)

- **Version (the discrepancy the brief named).**
  - D9 §2 lists 2.16.0, and the overview's header says 2.16.0. The overview's own correction says
    2.16.1 is current, with two CLI regression fixes: fixed-arity tuples and list-of-dict aliases.
    Those affect only `CliSettingsSource`, which this design does not use.
  - The spike venv has 2.16.1.
  - **2.16.2 was published today (2026-10-28) without release notes.** Its commits include "Fix
    JSON decoding of nested dictionary environment values (#1109)", "Decode nested dictionary
    values with complex union types (#1089)" with a regression follow-up (#1097), and "Fix
    explicit nested secrets directory precedence (#1093)".
  - Recommendation (Proposed): 2.16.1 at minimum. Move to 2.16.2 at P0.1 only after re-running
    P4's settings part, since nested environment decoding is exactly what `CORPUS_DATABASE__URL`
    uses.
- **Shape (Tested, P4).**
  - One `Settings(BaseSettings)` root with nested plain `BaseModel`s (`database`, `llm`/vLLM
    endpoint, `paths`, `gpu`), not nested `BaseSettings` (overview §2.2).
  - `env_prefix="CORPUS_"`: avoid `CI_`, because CI systems export `CI` and `CI_*`.
  - `env_nested_delimiter="__"`: `CORPUS_DATABASE__URL` set `database.url`.
- **Sources.** The default priority is init > environment > dotenv > secrets directory > defaults
  (Documented, Context7). Proposed: return only `(init_settings, env_settings)` from
  `settings_customise_sources`. direnv's reviewed `.envrc` and `.envrc.local` already own the
  environment, and no secrets directory exists.
- **Secrets.**
  - Keep the local PostgreSQL password out of settings: peer authentication or `PGPASSFILE`
    through libpq.
  - Any API key is `SecretStr`, whose repr is masked (Tested).
  - Keep one libpq URL (`postgresql:///corpus`) and derive SQLAlchemy's `postgresql+psycopg://`
    form in code.
- **Lifecycle.** Construct settings once at the entry point (the CLI callback or the MCP
  lifespan) and pass them down. `settings_cached()` exists and returns one instance (Tested), but
  a hidden cache makes tests depend on environment order. Tests pass
  `Settings(database={"url": test_url})`, since init wins (Tested), with `_env_file=None` if
  dotenv stays enabled.
- **Limits.**
  - `extra="forbid"` does not catch a mistyped variable: `CORPUS_DATA_DIRR` was silently ignored
    (Tested; overview §4.5). An operator-facing check listing unknown `CORPUS_*` names is optional.
  - Settings construction is synchronous; in the MCP lifespan, use `asyncio.to_thread(Settings)`
    if it ever reads files or the network.
- **Avoid:** `cli_parse_args` or `CliApp` beside Typer, which would put two parsers on one
  command line.

## 5. Evaluation (D7 §5)

### 5.1 One-to-one alignment: `scipy.optimize.linear_sum_assignment`

- **Already in use.** The spike uses it for entities, for claims per tier, and for `unsupported`
  items. D7 §5.2 names it, and it is the right primitive: the matrices per unit are small (tens of
  items), rectangular is supported, and the matching need not be full.
  `csgraph.min_weight_full_bipartite_matching` requires a full matching, and
  `maximum_bipartite_matching` ignores weights.
- **Use `maximize=True`, not negation.** The signature is `(cost_matrix, maximize=False)`, and both
  give the same assignment (inline check).
- **Weighted matching is correct as implemented.** Non-edges are 0, and zero-weight assignments
  are dropped afterwards. With positive weights that yields a maximum-weight matching.
- **Mask sub-threshold similarities to 0 before assigning (Proposed, inline counterexample).**
  `_assign` thresholds after assignment, which can keep a 0.5 pair and lose a 0.98 one. Today
  it is harmless, because every non-zero similarity in `align.py` is ≥ 0.6 against
  `ENTITY_THRESHOLD` 0.5. It matters once `FUZZY_TYPES` or other weights admit values below the
  threshold.
- **Lexicographic weights hold only for small units (Proposed).** The weights 1e6, 1e3, 1 and
  1e-3 are exact only while the smaller side has fewer than 1,000 candidates. Production should
  derive them from the unit size (base = min(|R|, |P|) + 1, weight k = base^k), or assert the
  bound.

### 5.2 Bootstrap intervals and paired comparisons: `scipy.stats.bootstrap`

**Parity (Tested, P3).** The call is
`stats.bootstrap((n_ref, n_pred, matched_ref, matched_pred), f1, paired=True, vectorized=True,
method="percentile", n_resamples=1000, rng=np.random.default_rng(20261028))`:

- the inputs are per-unit count arrays;
- `f1` sums along `axis=-1` and forms the ratio-of-sums micro F1.

On the recorded S0 A-versus-B table (12 units) it reproduces the recorded intervals:

| Tier | Recorded | SciPy |
|---|---|---|
| core | 0.82706–1.0 | 0.8270640543666858 vs 0.827064054366686 recorded (1 ulp apart); upper equal |
| full | 0.42854–0.75261 | equal to 1 ulp |
| evidence | 0.36797–0.74685 | equal |

The paired form resamples one index array and applies it to every sample (`_bootstrap_iv`,
`_bootstrap_resample`: `rng.integers(0, n, (n_resamples, n))`). That draws the same stream as the
spike's loop.

**Conditions (Tested, P3).**

1. **Unit order is part of the result.** Indices address array positions. Sorting the units
   lexicographically (U10 before U5) moved core to 0.8345–1.0 and full to 0.4165–0.7631. The scorer
   must fix a canonical unit order, for example by unit key, and record it with the seed and the
   NumPy and SciPy versions.
2. **Undefined resamples.**
   - SciPy 1.18.1 forms the interval with `stats.quantile`, which propagates NaN. Any resample
     with an undefined statistic makes the interval NaN and raises `DegenerateDataWarning`. That
     happened for 14 of 17 per-predicate core F1s on the 12 units.
   - The spike's NaN-skipping figure equals `np.nanpercentile(res.bootstrap_distribution,
     [2.5, 97.5], axis=-1)` exactly, for all 17 predicates.
   - Use that, and report the share of undefined resamples. An interval over resamples in which a
     predicate occurs is conditional, and should be labelled as such.
3. **The method changes the answer.** SciPy's default, BCa, gave core 0.790–0.993 against
   percentile 0.827–1.0. D7 should name the method. Percentile keeps parity with S0.
4. **Batching.** Per-predicate intervals come from one call, with predicates on a leading axis
   (shape `(preds, units)`, `axis=-1`).
5. **Paired difference between runs.** Pass both runs' four count arrays (eight samples, same
   units) with statistic `F1_A − F1_B`. That gives the interval of the difference and, from
   `bootstrap_distribution`, the share of resamples ≤ 0. Example: core − full = 0.307
   [0.181, 0.517], share ≤ 0 = 0.0.
6. **Page clusters.** Summing counts per page and resampling pages uses the same code. With
   core12's 4 pages it is degenerate (0.863–1.0). It becomes meaningful only with many pages
   (see IE-5).

**Recommendation (Proposed).** Replace the hand-written loop with `scipy.stats.bootstrap`, behind
a thin wrapper that:

- fixes the unit order;
- takes NaN-aware percentiles from `bootstrap_distribution`;
- reports the undefined share and the standard error;
- offers the paired-difference form.

It reproduces every S0 figure, and it adds batching, paired and difference forms, and the
distribution. Keeping the spike's twenty-line resampler is equivalent for the single-statistic
case; that choice is a matter of taste.

**Version caveat.** Pass `rng=`. `bootstrap` carries `@_transition_to_rng('random_state')`, and
the source's deprecation text says `random_state` support will be removed in SciPy 1.19.

### 5.3 Seeding: NumPy `Generator`

- Use `np.random.default_rng(seed)` (PCG64). For several independent streams, use
  `SeedSequence(root).spawn(k)`, or derive a child seed deterministically from a stable name or
  claim key (P8) (NumPy overview §6).
- The same applies to D7 §5.3's numeric equivalence "at random points satisfying the claims'
  conditions". Seeding those points from the claim pair's keys keeps equivalence decisions
  deterministic and cacheable (Proposed).
- Bit-for-bit streams are not promised across NumPy releases. 2.5 changed `binomial` and
  `multinomial`; `integers` was not reported as changed. Record the versions with scores.

## 6. Tests (D9 §4)

### 6.1 Hypothesis 6.170.12 (no overview; re-check)

- **Canonical JSON and keys (Tested, P5).**
  - A recursive JSON strategy: `st.recursive(none | booleans | integers | text,
    lambda k: lists(k) | dictionaries(text, k), max_leaves=20)`.
  - Shuffled dict insertion order (`st.permutations` over items) and reordered `and` arguments
    gave equal sha256 keys over sorted-key canonical JSON. Both properties passed.
  - Keep floats out of the generic strategy unless the canonical float form is defined, and test
    value canonical forms separately.
- **Add an NFC property.** `key(x) == key(nfd(x))`, since D1 §10.1 NFC-normalizes strings. If
  object keys are normalized too, two distinct keys can collide ("é" precomposed and decomposed);
  Hypothesis will find that case. D1 should say whether keys are normalized, or rejected when not
  NFC (a note for D1's owner).
- **Pydantic models (Tested, P5 and its inline follow-up).**
  - `st.from_type(Model)` and `st.builds(Model)` honour annotated-types constraints: `ge`, `le`,
    `gt`, `lt` and length gave 300/300 valid.
  - Recursive discriminated unions work: 200/200 valid.
  - `Field(pattern=…)` is ignored with `HypothesisWarning: Ignoring unsupported
    _PydanticGeneralMetadata(pattern=…)`, and generation then fails with `ValidationError`.
  - Register `st.register_type_strategy(Model, st.builds(Model, field=st.from_regex(r"…",
    fullmatch=True)))`, which worked (100/100).
  - For schema-driven fuzzing of the batch validator, hypothesis-jsonschema 0.23.2 (released
    2026-10-27) generates from the compiled JSON Schemas. Not probed; re-check.
- **Profiles (Documented, Context7; Tested, P5).** Register profiles in `tests/conftest.py`:
  `ci` = `deadline=None, derandomize=True, database=None, print_blob=True, max_examples=300`, and
  `dev` with defaults. Select one with `--hypothesis-profile` or `HYPOTHESIS_PROFILE`.
  - `derandomize=True` makes runs repeatable.
  - The default deadline of 200 ms is too short for properties that touch SymPy.
  - Even with `database=None`, Hypothesis writes `.hypothesis/` (charmap and constants caches) in
    the working directory. It carries its own `.gitignore` (`*`), so the repository needs no
    entry (Observed, P5; the probe's directory was removed afterwards).
- **Testing rule.** AGENTS.md requires independent expectations. The invariance properties above
  are relations between two keys, so they qualify. Equivalence to a reference implementation
  would not.

### 6.2 import-linter 2.15 (no overview; re-check)

- **Contract (Tested, P6; Documented, Context7).** In `pyproject.toml`:
  - `[tool.importlinter] root_package = "corpus_structure"`, then
    `[[tool.importlinter.contracts]] type = "layers"`, `containers = ["corpus_structure"]`, and
    `layers` listed highest first.
  - `"a | b"` declares independent siblings, `"a : b"` siblings that may import each other.
  - Optional: `exhaustive = true` with `exhaustive_ignores`, and `ignore_imports` for justified
    exceptions.
  - Run it as `uv run lint-imports`. The package must be importable, meaning the workspace member
    is installed in the root environment. Use `--no-cache`, or gitignore `.import_linter_cache`.
- **Finding (Tested, P6).** D9 §1's top tier as written, `evaluate | intervene | serve`, is kept
  only while no sibling imports another. It breaks as soon as `intervene` imports `serve`
  (`corpus_structure.intervene is not allowed to import corpus_structure.serve`). That is exactly
  what D8 requires:
  - §2.4's MCP `query` and `explain` return the typed queries of §5;
  - §1 says the MCP server and the CLI call the same application functions;
  - D9 also puts the CLI inside `serve`.

  A layering with an entry-point tier passed with `exhaustive = true`: `cli : intervene` above
  `evaluate | serve` above `orchestrate` … `core` (see IE-7).
- **Running it in `just`.** Add a guarded recipe like `rules-scan`, reporting
  `not_run (no package yet)` until `python/corpus-structure` exists, and include it in
  `hygiene_checks`.
- **Conflict to settle.** AGENTS.md's working agreement says "No new alignment linting. Don't add
  lints or checks for design alignment". D9 §1 plans this contract. Adopting it is the operator's
  or coordinator's decision.

---

## Library proposals

The ids below are provisional (IE = interfaces/evaluation); the coordinator assigns the `L-nn`
numbers.

| Id | Contract | Proposal | Why |
|---|---|---|---|
| IE-1 | D8 §2.1, §2.2 (`propose_claims`, `write_golden`, `adjudicate`) | The batch argument is a JSON object validated in the tool body against the task's compiled schema version. Per-item errors, warnings and unlocated quotes form a *successful* structured result. `isError` is reserved for envelope or infrastructure failures. The schema is served only by `read_instructions`, with a hash a submission may echo | §1.1: a strict parameter fails the whole call before the body runs, with a different error-path form; tool schemas are static; Claude Code trims long error text |
| IE-2 | D8 §2.2, OPEN-D8-3; the work-queue skill | Golden passes run as an agent file with an inline stdio `mcpServers` entry (`ci mcp serve --profile golden`, golden tools only), `model: sonnet` and restricted tools. "Session reference" = the server-instance id minted in the lifespan. The declared model is recorded and audited from the transcript | §1.7: MCP session ids cannot identify a subagent on stdio; inline servers give one process per invocation |
| IE-3 | D8 §3 | Caps measured in characters (or a named, deterministic counter). Every capped tool takes `page_token` and returns `next_page_token` and `truncated`. FastMCP's `ResponseLimitingMiddleware` is a byte backstop only. Tool descriptions and server instructions ≤ 4,096 characters | §1.5: the server has no token counter; Claude Code's thresholds are character-based; the middleware drops structured content |
| IE-4 | D8 §7 OPEN-D8-1, D9 §8 OPEN-D9-2 | Two processes. MCP servers (per session and per golden subagent) are thin over the database. The orchestrator `LISTEN`s on a dedicated connection with a timeout and re-queries task statuses on every wake-up. Submission commits and `NOTIFY` share one transaction. No FastMCP background tasks | §2 |
| IE-5 | D7 §5.4 (Uncertainty) | Name the interval: percentile, 1,000 resamples, a ratio-of-sums statistic over resampled units, a fixed canonical unit order, and a recorded seed and library versions. Undefined resamples are skipped and their share reported. "Paired bootstrap" = interval of the run-to-run difference over shared indices, with the share ≤ 0. Optionally report page-cluster intervals once the set spans enough pages (dev 40 across many pages; core12's 4 pages are too few) | §5.2: method and unit order change the interval; SciPy propagates NaN; units within a page are correlated |
| IE-6 | D7 §5.2, §5.3 | Similarity thresholds are applied before assignment. Lexicographic tier weights are derived from the unit size. Numeric equivalence draws its random points from a generator seeded by the claim pair's keys | §5.1, §5.3 |
| IE-7 | D9 §1 (and D8 §1, §4) | The dependency direction gets an entry-point tier: `cli : intervene` (composition roots) above `evaluate | serve` (shared application and query functions), with the CLI moved out of `serve/` into its own package. Lower layers do not import Typer, Rich or FastMCP | §6.2: D9's independent top tier contradicts D8's shared application functions and breaks the planned contract |
| IE-8 | D9 §2 (pins) | pydantic-settings 2.16.1 at minimum (2.16.2 released 2026-10-28; re-run P4's settings part before adopting it); fastmcp 4.1.3 or 4.1.4; import-linter 2.15; pytest-asyncio 1.4.1 or anyio's pytest plugin for the async MCP tests; hypothesis-jsonschema 0.23.2 optional | §1.8, §4, §6 |

## Uncertainties and what was not done

- No PostgreSQL probe of `LISTEN`/`NOTIFY` across processes; §2 is reasoning from documented and
  verified signatures.
- The Claude Code pages read do not say whether the model sees `structuredContent`. The
  subagent-to-server sharing of a name-referenced server is documented; the behaviour of
  `tools`/`disallowedTools` on inline servers is not stated on the page.
- Neither Claude Code's own MCP protocol era nor its `session_id` behaviour was observed; P2 used
  FastMCP's client.
- Hypothesis and import-linter have no overview in `docs/libraries/`; their findings should be
  re-checked against one when written.
- pydantic-settings 2.16.2 behaviour is unverified (no release notes, not installed).

## Files written

Everything in this folder:

- `README.md`;
- `probes/p1_fastmcp_contract.py`, `p2_fastmcp_stdio.py`, `p3_bootstrap_parity.py`,
  `p4_typer_cli.py`, `p5_hypothesis_pydantic.py`, `p6_importlinter_layers.py`;
- `probes/out/` (seven output files).

The scratch environment lived outside the repository.
