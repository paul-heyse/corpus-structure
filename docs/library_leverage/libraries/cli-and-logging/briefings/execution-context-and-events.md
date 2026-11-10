# Execution context, structured events and progress

**Discovery, 2026-11-10; benefits Proposed.** [Baseline and authority](../briefing.md).
structlog26.1 is a researched candidate, not installed or selected for adoption.

## Current producers, identities and consumers

The code already has substantial structured operational information:

- [managed.py](../../../../../python/corpus-structure/src/corpus_structure/cli/managed.py)
  creates result IDs, manifests, stages and settled outcomes. `watch_result` reads stage/lane
  changes, emits diagnostics and returns a final typed report. Recovery specifically supports
  drained test-supervisor receipts, not arbitrary semantic runs.
- [testing.py](../../../../../python/corpus-structure/src/corpus_structure/cli/testing.py)
  derives exact retries from retained receipts and compares attempts with required coverage.
  [model.py](../../../../../python/corpus-structure/src/corpus_structure/cli/model.py) supplies
  preview/candidate inspection and explicit action guidance. These are agent usability strengths.
- [run status](../../../../../python/corpus-structure/src/corpus_structure/orchestrate/commands.py)
  and [CLI status](../../../../../python/corpus-structure/src/corpus_structure/cli/status.py)
  expose semantic run/task state separately from managed invocation IDs. These identities mean
  different things; merging their labels would lose useful distinctions.
- [database notices](../../../../../python/corpus-structure/src/corpus_structure/core/db/store.py)
  copy safe notice fields into stdlib logger `extra`. The
  [method context](../../../../../python/corpus-structure/src/corpus_structure/core/method.py)
  carries a stdlib logger supplied by the orchestrator. PDF ingestion warns while separately
  recording failed unit outcomes. Logging and typed result truth already have distinct roles.
- [automated.py](../../../../../python/corpus-structure/src/corpus_structure/intervene/automated.py)
  explicitly passes invocation/receipt identifiers to a fresh MCP process, retains separate
  provider stdout/stderr and uses reader threads. The
  [semantic server](../../../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py)
  records provider-reported assurance with run/task/attempt/holder bindings. The
  [PM2 worker](../../../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py)
  constructs a child environment and checks request/reply IDs.

The representative CLI scan found no Rich Live/Progress integration or central logging setup.
This is scoped source evidence, not a claim that no dependency configures logging dynamically.
MCP stdout carries protocol data; a generic stdout logger default would be inappropriate there.

<a id="cli-07"></a>
## CLI-07 — Structured events and foreign logging

**Mechanisms.** Event dictionaries with bound attributes; processor chains for enrichment,
normalization/filtering and final JSON or console rendering. `ProcessorFormatter` with
`wrap_for_formatter`, `foreign_pre_chain` and `ExtraAdder` can retain stdlib producers.
Compare direct `WriteLoggerFactory`/`BytesLoggerFactory` when only application events need a sink.
Python logging still owns its hierarchy, handler routing and levels; structlog configuration alone
does not configure it. These are documented [26.1 stdlib contracts](https://www.structlog.org/en/26.1.0/standard-library.html).

**Potential value.** Codex could inspect useful fields such as PostgreSQL notice codes or operation
identity without parsing prose. Reusable enrichment may remove repeated field plumbing. Native
processors can provide a coherent path for both application and relevant third-party events.

**Counterconditions.** Existing typed reports/receipts may already contain the actionable facts.
Formatting cannot recover fields a foreign producer never supplied. Direct sinks do not unify
stdlib logging. Adding handlers, queues, retained logs and another inspection interface could
increase the agent's work rather than simplify it. No new event schema or telemetry service is
needed merely because structlog accepts arbitrary dictionaries.

**Next question.** Which useful producer fields currently disappear before Codex receives them,
and which existing result consumer should expose them? Inspect one concrete failure path before
choosing the stdlib bridge or a direct sink. Preserve the original receipt's authority and assurance.
Follow [CLI-06](reporting-and-diagnostics.md#cli-06) for the source-verified RichHandler/formatter
composition hazard; select one row/traceback owner per destination in any later assessment.

<a id="cli-08"></a>
## CLI-08 — Correlation using existing identities

**Mechanisms.** Explicit logger `bind`, `bound_contextvars`, `merge_contextvars`, reset tokens and
boundary cleanup; explicit identifier transfer across subprocesses. Use separate keys for managed
result, semantic run, provider invocation, leased attempt and worker request when those distinctions
matter. Do not mint a universal trace identity before showing what existing identities cannot do.

**Potential value.** Deep diagnostic calls can retain their operation binding without repeating
the same keyword arguments everywhere. Correlation could connect provider stderr to the existing
receipt or distinguish which invocation owns a warning during parallel work.

**Source contracts and limits.** The [contextvars guide](https://www.structlog.org/en/26.1.0/contextvars.html)
warns about hybrid sync/async isolation. In tagged26.1
[stdlib.py](https://github.com/hynek/structlog/blob/26.1.0/src/structlog/stdlib.py), async dispatch
copies context before executor execution and captures exception information before async exception
logging. This observed implementation does not promise propagation through arbitrary executors.
Python3.14 [asyncio](https://docs.python.org/3.14/library/asyncio-task.html) and
[threading](https://docs.python.org/3.14/library/threading.html) have different propagation rules;
raw threads/processes must be considered at their actual creation boundaries. Context changes in
a worker do not automatically constitute a returned result.

**Counterconditions.** Explicit parameters or a bound logger may be clearer for the small producer
footprint. Ambient context can leak between nested commands/tests if reset at the wrong boundary.
The current provider environment already transfers identities deliberately; contextvars cannot
replace cross-process receipt transport or durable attempt state.

**Next question.** In one failure investigation spanning CLI, MCP and provider/worker, which
diagnostic lacks an identity needed to join it to an existing result? Trace only those task,
thread and process boundaries; absence of automatic context is not itself a product defect.

<a id="cli-09"></a>
## CLI-09 — Useful progress, selective enrichment and summaries

**Mechanisms.** Rich `Status`, `Live.update`, `Progress` task fields, unknown totals, retry resets
and explicit refresh; structlog early level filtering, `DropEvent`, `MaybeTimeStamper`, selected
`CallsiteParameterAdder` fields and a terminal operation summary.

**Potential value.** An optional terminal projection can show multiple meaningful counts; an
information-rich summary can reduce scattered prose and repeated lookup. Existing stage and count
observations should supply truth. A diagnostic can include the exact next inspection command and
identity type without adding another execution supervisor. These mechanisms also offer new
functionality when an actual operation lacks an actionable observation.

**Counterconditions.** Codex usually consumes captured output, where redraw frames do not preserve
intermediate state. Current `watch_result` stage lines may suffice. An end-only summary cannot
replace partial/interrupted outcome evidence. Callsite inspection and unrestricted exception/object
expansion can amplify auxiliary work. Async logging methods offload blocking work but do not
provide durable queues or backpressure. `DropEvent` is unsafe inside ProcessorFormatter: filtering
placement matters, not just the processor's presence.

**Next question.** What material state or distinction is missing from the current watch/status
products? In particular, can Codex distinguish semantic RUN from managed result ID and choose the
right recovery/status command? Add a projection only if it answers a real decision better than
bounded lines. Retain unknown denominators and owner-defined interruption outcomes.

Sources: [Progress15](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py),
[structlog processors](https://www.structlog.org/en/26.1.0/processors.html),
[performance tradeoffs](https://www.structlog.org/en/26.1.0/performance.html),
[logging practices](https://www.structlog.org/en/26.1.0/logging-best-practices.html).
No speed or usability improvement has been measured; expected benefits remain qualitative.

<a id="cli-10"></a>
## CLI-10 — Native verification at the correct boundary

**Mechanisms.** Typer `CliRunner` exact stdout/stderr/bytes/return values and environment controls;
Rich capture/fixed-width StringIO and controlled clocks; structlog `capture_logs`, `LogCapture`,
`CapturingLoggerFactory`, `ReturnLogger`, `reset_defaults` and deliberate logger caching.

**Potential value.** Test event meaning separately from the configured processors and final output.
Reuse native capture rather than a new diagnostic-testing framework. Existing repeated in-process
CLI tests are a concrete consumer for predictable logger/handler initialization and restoration.

**Contracts.** [structlog testing](https://www.structlog.org/en/26.1.0/testing.html) explains that
ordinary capture disables processors and cached loggers can bypass changed capture configuration.
Post-processing backend capture answers a different question. [Configuration](https://www.structlog.org/en/26.1.0/configuration.html)
is process-global; lazy/cached loggers and handler stream references need deliberate lifetimes.
Typer0.28's [runner](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py) changes process
streams and uses the constructed command; the actual application
[entrypoint](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py) also owns traceback hooks.
Runner assertions alone do not establish fresh-process hook or signal behavior.

**Counterconditions.** Lifecycle scaffolding can outweigh a few logging calls. Capturing the same
validator as both producer and expectation provides no independent semantic check. Full-process
tests for every layout or pure transformation would add unnecessary work.

**Next question.** For a selected candidate, which plausible failure is invisible to ordinary
event capture? Then use a configured-pipeline check for nested redaction, stdlib extras, exception
field retention and final stream routing; use sequential in-process invocations for context/config
leakage; use a subprocess/PTY only for process and terminal contracts. These are follow-up scenarios,
not an acceptance obligation imposed on the current documentation-only discovery.

## Handoff

Research CLI-07/08 using actual producer fields and the consuming inspection command first.
Depth, persistence and rendering follow from that consumer. Keep machine command results and MCP
protocol data distinct from logs; preserve typed outcome and provider-assurance ownership.
No runtime probe, installation or provider execution was necessary for this account.
