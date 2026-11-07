# Stream behavior and diagnostics

**Status:** CLIR-CA07–08 own the open stream and stage corrections. CLIR-CA10 owns the reopened
diagnostic investigation. The [coordinator](../cli-reporting_2026-11-07.md#completion-audit)
owns scope, the compatibility decision and integrated acceptance. This plan consumes
[O06](../../functional_reviews/cli-reporting_2026-11-07.md#O06) and
[O07](../../functional_reviews/cli-reporting_2026-11-07.md#O07).

<a id="CLIR-06"></a>
## CLIR-06 · Report meaningful stages and settle stream outcomes

### Establish the stream contract early

Keep machine JSON and explicit text streams on stdout. Put bounded stage and diagnostic
lines on stderr. Keep parser errors, typed refusals, unexpected defects, cancellation,
operation settlement and output delivery distinguishable. A render or write failure
must leave the original managed outcome discoverable by ID. Cancellation follows the
operation supervisor's own process group and settlement protocol.

Use the retained installed control as the baseline. A successful lookup piped to an
immediate close yielded a Python stdout-flush `BrokenPipeError` and producer exit
120. Compare a concise, distinct nonzero output-close status with quiet termination
for an explicitly stream-oriented read. Prefer an identifiable nonzero delivery status
for an incomplete machine document and preserve a known operation failure in either
policy. Evaluate quiet termination only where a bounded consumer deliberately ends
an explicit text stream and the contract can represent that correctly. Verify both
write-time and flush-time closure and check exit-code collisions, downstream parse
behavior and shell `pipefail`. Confirm CLIR-D01 before changing existing semantics or
shipping the dependent routes. A closed stdout cannot carry a replacement JSON object.
[Installed stream control](../../design_review/evidence/2026-11-07_cli-reporting/README.md) ·
[Existing emitter](../../../python/corpus-structure/src/corpus_structure/cli/output.py) ·
[Python SIGPIPE guidance](https://docs.python.org/3.14/library/signal.html#note-on-sigpipe)

### Expose meaningful progress with optional terminal updates

Start with one bounded stderr line per meaningful stage or owner count and a final
result after settlement. The supervisor or result owner establishes stage and count
truth. Add a TTY view only if users need to track a changing stage or multiple tasks
between lines. Headless output remains readable and stable. TTY detection and cursor
behavior need explicit qualification. The probe found that `NO_COLOR` alone leaves
cursor controls enabled on a PTY.

| Library mechanism | Proposed use or adoption condition |
|---|---|
| Rich 15.0.0 `Console(stderr=True)`, `Status`, `Live.update` | Use one invocation-owned stderr console if status and diagnostics need coordination. Use `Status` for one indeterminate stage, or `Live(auto_refresh=False, redirect_stdout=False, redirect_stderr=False)` for a view refreshed on meaningful owner observations. Restore terminal state on success, exception and interruption. [Local live overview](../../libraries/python_introspection/rich.md#6-live-displays-progress-and-execution-state-visualization) · [Pinned Live](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py) |
| Rich `Progress`, `Task.fields`, `ProgressColumn.max_refresh` | Use when multiple changing tasks or real counts affect a decision. Use `total=None` for unknown denominators, named columns for owner counts, a bounded refresh policy and `get_time` in timing controls. Reset task state only for a real retry. [Pinned Progress](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py) |
| Rich `Traceback.from_exception` | Consider only for an explicit, authorized debug route. Set `show_locals=False` and bound frames, exception groups and notes at the diagnostic boundary. Sanitize source context and messages before emission. [Pinned Traceback](https://github.com/Textualize/rich/blob/v15.0.0/rich/traceback.py) |
| Typer 0.28.0 `Context.obj`, namespaced `Context.meta`, `with_resource`, `call_on_close`, `result_callback` | Prefer existing explicit scopes and the emitter. Consider a lifecycle hook if it simplifies one actual lease or presentation lifetime, and qualify cleanup ordering on the pin. `Context.invoke` composes callbacks. Use pipes and owner operations for command composition. Typer command chaining and Click extensions supply no required dependency. [Context and lifecycle](../../libraries/python_introspection/typer.md#4-parameter-sources-execution-context-and-lifecycle) · [Tagged context implementation](https://github.com/fastapi/typer/blob/0.28.0/typer/_click/core.py) |

Explicit paging can be considered for long human detail with a named consumer.
`Console.capture()` and bounded `StringIO` serve tests. Recording or text/HTML/SVG export
requires a deliberate presentation request and custody because recording retains rendered
segments. Consider scoped themes and literal styles for accessibility. Consider prompts,
single-character input, terminal-size APIs and `typer.progressbar` only for a named
interactive case. Full-screen interfaces, REPL inspection, notebook renderers and
decorative effects remain deferred until a concrete reporting need warrants review.
[Rich capture and export](../../libraries/python_introspection/rich.md#9-interactive-input-capture-and-output-export) ·
[Typer diagnostics](../../libraries/python_introspection/typer.md#8-testing-and-diagnostic-inspection)

Verify exact stdout bytes and bounded stderr in real installed processes. Use an early-close
consumer, a normally draining pipe and a PTY. Include an already-failed operation and confirm
its retained status. If TTY progress is selected, exercise interruption after the display
starts, cursor restoration, headless behavior, JSON delivery, and the original invocation's
actual settlement or recovery state.

<a id="CLIR-07"></a>
## CLIR-07 · Investigate missing diagnostic facts

Start with an actionable question and a failed or interrupted example that the updated
recipe report, operation status and receipts cannot answer. A candidate is identifying
the last productive supervised step before a cancellation with no final step receipt.
Document the decision the missing fact changes. Compare the existing process receipt,
a bounded owner event and a scoped stdlib handler. Compare setup, processing and
teardown burden with the answer each route adds. The earlier observability plan is
cancelled. This package owns only the selected reporting investigation.

| Candidate | Adoption and reference |
|---|---|
| Python 3.14 `logging.Handler`, `MemoryHandler`, Rich 15.0.0 `RichHandler` | Compare for a real missing event or pre-failure excerpt. Redact before buffering or forwarding. Bound bytes and records explicitly since the handler's record capacity supplies no byte cap. When rendering to stderr, use explicit markup, traceback and console policy. Test trigger, overflow, cleanup and invocation isolation. [Handler reference](https://docs.python.org/3.14/library/logging.handlers.html#logging.handlers.MemoryHandler) · [Pinned RichHandler](https://github.com/Textualize/rich/blob/v15.0.0/rich/logging.py) |
| Logbook `FingersCrossedHandler`, `GroupHandler` | Compare only if retaining preceding events is necessary and these hooks simplify that lifetime. Check wrapped filtering, byte caps, release of references and the added dispatch lifecycle. [Logbook buffering](../../libraries/logging/logbook.md#61-fingerscrossedhandler-retain-context-until-escalation) |
| structlog `bound_contextvars`, `merge_contextvars`, `ProcessorFormatter.foreign_pre_chain`, `wrap_for_formatter` | Compare when app and stdlib records need the same approved context and the small stdlib route duplicates work. Bind invocation or stage in the producer and pass approved fields explicitly across processes. Use `capture_logs` for event assertions and a real subprocess for the configured chain. [Context variables](https://www.structlog.org/en/stable/contextvars.html) · [Standard library integration](https://www.structlog.org/en/stable/standard-library.html) |
| Loguru `bind`, `contextualize`, `patch` and callable sinks, Eliot actions | Revisit for a reusable sink or enrichment requirement, or for a causal action relation that changes an operator decision. Account for queue ownership and flush. [Loguru](../../libraries/logging/loguru.md) · [Eliot](../../libraries/logging/Eliot.md) |
| Python JSON Logger `JsonFormatter`, ECS formatters | Revisit for a named downstream diagnostic schema with its own validation. [JSON Logger](../../libraries/logging/python-json-logger.md) · [ECS](../../libraries/logging/ecs-logging.md) |
| OpenTelemetry spans and links, Logfire typed spans and in-memory exporters | Revisit for a named cross-service decision local receipts and operation IDs cannot explain. Establish filtering, redaction, propagation, sampling and exporter lifetime for that consumer. [OpenTelemetry](../../libraries/logging/OpenTelemetry_Python.md) · [Logfire](../../libraries/logging/pydantic-logfire.md) |
| picologging | Revisit if profiling establishes a logging bottleneck and the required Python and handler compatibility is verified. [Logging overview](../../libraries/logging/Python_Structured_Logging_and_Observability.md) |

Prefer an invocation-scoped excerpt. A named post-settlement consumer can justify
retaining the approved excerpt in the existing managed result, with bounds and explicit
availability. If no gap survives the owner read work, close the investigation with
that result and its revisit condition. If a dependency is justified, select and
qualify the exact pin and document the chosen API and limits in this package before
adoption. [Prior I10 decision](../../plan_improvement_reviews/cli-operations_2026-11-07.md#i10--make-cli-diagnostics-actionable-within-the-result-lifecycle)
