# Attributed operation inspection and meaningful progress

**Recommendations Proposed, 2026-11-10.** [Review and baseline](../cli-and-logging_2026-11-10.md).

<a id="O05"></a>
## O05 — A bounded correlated operation view

Recommend a selected inspection/timeline over managed outcomes, task/provider receipts and useful
diagnostic observations. Codex could request the last observations for an interrupted invocation,
then select warnings for one attempt, inspect a linked receipt and choose the right recovery or
semantic-run action. A possible interaction is a new timeline view on existing result inspection;
the spelling and detailed schema belong to planning, not the installed interface.

Current `Invocation.stage` stores the latest stage, `watch_result` reads changes/test-lane events,
the semantic MCP server records provider-reported task/attempt/holder links, automated execution
retains stdout/stderr receipts, and PostgreSQL notices already carry structured extras. Build the
view from those owners first. Add compact retained observations for useful lost transitions and
diagnostic fields, not one event for every primitive operation. Native task state remains authoritative.

Keep managed result, semantic run, provider invocation, leased task attempt and worker request as
distinct identity types/fields. Preserve provider-reported versus native assurance. Link by explicit
receipt relationships; cross-process timestamps alone do not establish causal order. Missing events
mean unavailable observation, not absence of activity. A final summary cannot replace interruption
evidence, and a quiet period cannot prove a stalled worker.

### Recommended realization and serious alternatives

For this richer target, recommend structlog26.1's processing with the existing stdlib producers:
`ProcessorFormatter.wrap_for_formatter`, `foreign_pre_chain`, allowlisted `ExtraAdder`, shared safe
enrichment and destination-specific rendering. Use explicitly configured/bound loggers, including
`wrap_logger` where suitable, instead of relying on mutable global defaults. Python logging owns
only the required logger/handler routes; restoring invocation-local handlers/sinks is part of delivery.
Use ordinary StreamHandler with structlog's ConsoleRenderer or JSONRenderer as final renderer;
Rich traceback formatting may participate inside that route. No additional full RichHandler renderer.

An explicit finite set of typed observation writes plus stdlib logging is a serious lower-burden
alternative. Choose it if the selected producer/consumer closure remains small enough that generic
processing adds more lifecycle machinery than it removes. Direct `WriteLoggerFactory` is another
native alternative when foreign logging has no useful consumer. It does not automatically collect
dependency records. The proposed complete target favors the bridge because it deliberately consumes
foreign extras and structured failures; ordinary current message formatting alone would not justify
adopting structlog. No dependency is installed by this review.

### Collection, retention and presentation boundaries

Finalize the safe retained event before sink fan-out. Nested values must not be mutated differently
by competing handlers: ProcessorFormatter shallow-copies the LogRecord and native event mapping,
leaving nested values shared. Redaction in only one formatter cannot protect another sink.
`DropEvent` is unsafe inside ProcessorFormatter; use native early filtering before adaptation,
appropriate stdlib filtering for foreign records, or selection during later reads.

Collection policy and presentation selection differ. A later severity/stage/method/attempt filter
cannot recover events rejected at collection time. Expose collection scope, dropped/truncated
observations and unavailable fields. Native `filter_by_level`, fixed filtering wrappers, selected
callsite enrichment and renderer columns can serve these distinct responsibilities without one
global verbose mode. Reuse owner facts rather than stack-inspecting every event for attribution.

Retain selected safe observations through existing managed artifact lifetime, leases, holds and
expiry; explicitly support incomplete/interrupted reads if useful observations are promised before
settlement. Settlement still follows its owner. Bound bytes as well as records; a byte limit cannot
silently erase the failed operation's standing. No new database, daemon, universal trace ID or
remote telemetry backend is needed. Raw diagnostic disclosure remains a separately requested route.

Use explicit bound logger context first. `bound_contextvars`/`merge_contextvars` help only where
they remove repeated plumbing; restore nested tokens at actual invocation/tool/attempt boundaries.
Retain explicit process transfer already present in automated execution. Python3.14 task, thread
and executor semantics differ; structlog's own async dispatch copying does not qualify arbitrary
reader threads or MCP task scheduling. Configure process policy separately from invocation context
and stream ownership; avoid first-use cached objects retaining obsolete test streams.

**Delivery criteria.** Inspect one interrupted provider journey by result identity, follow its
attempt/receipt with honest assurance and identify the correct next owner action. Missing/corrupt
events yield partial/unavailable detail; a second invocation sees no previous context or handler.
Independent configured-sink checks establish foreign extras, nested redaction, grouped exceptions,
collection omissions and protocol-safe streams. Extend custody contracts explicitly where needed;
do not presume the current final-artifact publisher already supplies an append-only event journal.

Sources: [managed owner](../../../python/corpus-structure/src/corpus_structure/cli/managed.py),
[provider links](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py),
[process capture](../../../python/corpus-structure/src/corpus_structure/intervene/automated.py),
[stdlib integration26.1](https://www.structlog.org/en/26.1.0/standard-library.html),
[ProcessorFormatter source26.1](https://github.com/hynek/structlog/blob/26.1.0/src/structlog/stdlib.py),
[processors](https://www.structlog.org/en/26.1.0/processors.html),
[scoped context](https://www.structlog.org/en/26.1.0/contextvars.html).

### Corrected composition warning

Rich15 `RichHandler.emit` calls `format` then may rebuild the message using the original record's
`exc_info`. ProcessorFormatter clears exception state only on a copied record, so its default
`keep_exc_info=False` does not generally disable the foreign-exception branch. The discovery's
earlier condition was too narrow. This is an Interface-checked source conclusion, not an executed
composition test. Keep one final row/traceback owner and qualify the selected pipeline at delivery.
[Rich15 emit](https://github.com/Textualize/rich/blob/v15.0.0/rich/logging.py).

<a id="O06"></a>
## O06 — Progress that supports an agent decision

Recommend extending the same inspection owner with current stage, last useful observation, scoped
counts/known-or-unknown denominator, relevant attempt bindings, interruption/cleanup standing and
an identity-qualified next action. The captured primary interface is bounded append-only stage
information plus a final report. It helps Codex decide whether to watch, inspect, resume a semantic
run or recover a test result; these operations must not become interchangeable generic recovery.

Current status/watch is a strong baseline. Improve labels and joins before inventing another
supervisor. Information-rich completion summaries supplement retained transitions, not replace them.
An operational limit or stale observation must not become an asserted complete status.

Rich Status/Live/Progress is a conditional projection when terminal users need multiple changing
counts. Use task fields, `total=None` and reset only for a real new attempt. Disable stream
redirection and own cleanup with the display's context manager; no independent timer should
manufacture domain progress. Native deterministic clocks help focused display checks.

TTY animation has insufficient value to be a prerequisite for the selected captured-agent target.
Async log methods, bytes sinks and alternate serializers similarly wait for a blocking-sink or
whole-transport need. OpenTelemetry/Logfire/ECS/framework adapters wait for an actual tracing,
remote ingestion or runtime consumer. Local identity correlation does not justify those systems.

**Delivery criteria.** A waiting or interrupted agent receives the right identity and next command,
with no invented denominator or stall conclusion. Final JSON stays parseable under concurrent
diagnostics; a selected TTY branch restores state after interruption. Existing process-group and
settlement responsibilities remain with their owners.

Sources: [status](../../../python/corpus-structure/src/corpus_structure/cli/status.py),
[watch/recovery](../../../python/corpus-structure/src/corpus_structure/cli/managed.py),
[Live15](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py),
[Progress15](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py),
[configuration26.1](https://www.structlog.org/en/26.1.0/configuration.html),
[performance tradeoffs](https://www.structlog.org/en/26.1.0/performance.html).
