# Logging event routing and causal histories

Investigation date: 2026-11-01. Source baseline: `28f735b87eb2672c521af816aed411ab665b79f4`.
Owner: structured-logging coordinator I01 (event/incident side) and I02.
Only this evidence folder changed. Product dependencies, runtime, plans and STATUS were not edited.
Other investigations own direct OTel versus local Logfire and package/exporter lifecycle choices.

## Questions and decisions

**I01 event routing: select structlog26.1.0 + stdlib, not a second Loguru router.**
Both preserve nested extra fields in this bounded probe. Structlog's native processor pipeline plus
stdlib routing preserves existing MethodContext/library loggers without creating a second singleton.
Use ProcessorFormatter with wrap_for_formatter, a foreign_pre_chain that deliberately extracts
foreign extras and producer context, destination-owned nested values and terminal formatters per
branch. DropEvent cannot safely run inside ProcessorFormatter. OTel conversion must occur before
terminal formatting; this probe does not implement or qualify the OTel bridge.

Pinned installed Loguru0.7.3 source confirms that StandardSink creates a new stdlib LogRecord whose
`msg` is rendered text and whose additional data is nested under `extra`; a default structured
handler cannot be assumed to see the same field layout as structlog/foreign producers. Its queued
handler uses multiprocessing.SimpleQueue without a capacity argument. Loguru remains technically
capable, especially for native file sinks, but does not remove more machinery under the chosen
bounded routing and ordinary stdlib producer requirements. This is a composition judgment, not a
performance ranking, security defect claim or assertion that Loguru cannot be configured safely.

**I01 incident branch: retain scoped Logbook1.10.1 FingersCrossedHandler.** Native buffer_size=3
retained exactly the last two DEBUG occurrences and the ERROR trigger, without emitting on capacity;
a separate operation buffer remained isolated and closing it without a trigger did not release it.
With reset=False, later DEBUG records pass through after triggering; reset=True re-buffers them.
The original occurrence IDs survive native emission. These semantics justify native failure
capture rather than inventing an error-only retention buffer around MemoryHandler.

Conditions matter: buffer_size defaults to zero (unbounded), bounds count rather than bytes,
wrapped destination filter/bubble/level settings are ignored, and native handler stacks alone do
not establish operation isolation. Allocate an explicit handler per accepted operation, apply
process-wide admission and event-size policy before its native buffer, and route safe detached
records directly to that chosen buffer. Map severity names deliberately across logging systems;
numeric stdlib levels are not Logbook levels. Decide and document reset/post-trigger policy.
This probe tests interleaved independent handlers, not a complete contextvars/stdlog adapter or a
process-wide byte-budget implementation. Those remain implementation obligations.

**I02: keep OTel parent/links as causal authority; do not add Eliot now.** Eliot1.18.0 Parser
really reconstructs reversed native records and recognizes missing root terminal or child-start
records as incomplete. It retains a genuinely failed attempt separately from successful recovery.
That is useful capability, not merely alternate trace IDs. However, the selected workflow requires
fan-in/reuse/retry links as well as nesting. The fan-in probe retains two contributors as message
metadata under a single native action parent; it does not turn the Eliot tree into a DAG.
Adding Eliot would require a second identity/lifecycle plus the separate relationship model anyway.

Use explicit retained-history coverage in the OTel read projection: missing spans/parents, archive
cut, sampling/loss and opaque dependencies are unknown/partial. Do not claim an OTel analogue of
Task.is_complete proves that every instrumented child was retained: a missing entire child without
an independent declared inventory is generally unknowable. The Eliot refusal probe also shows a
normal action return is `succeeded` even though the domain result is refused. Neither model's
technical completion is domain publication truth.

Reconsider Eliot if a consumer specifically requires its typed action-history and completeness
promise rather than the current graph-oriented diagnostic workflow. Do not adapt OTel records into
an Eliot task tree merely to access Parser; their identities and completion semantics differ.
No benchmark or OTel backend qualification follows from this comparison.

## Actual scope and results

**passed:** Python3.14.10 isolated resolution/import of structlog26.1.0, Loguru0.7.3,
Logbook1.10.1 and Eliot1.18.0. `environment.toml` and `uv.lock` retain exact direct/transitive inputs.
The environment lives under `/home/paul/.cache/corpus-logging-investigations/events/.venv`.
No inherited UV_PROJECT_ENVIRONMENT was used. This qualifies this candidate subset only, not the
complete OTel/Logfire/product dependency family.

**passed:** `probe.py` final strengthened run:20 independent checks. Native/foreign fields remain
queryable, both destinations exclude the synthetic sensitive field, nested branch mutation is
isolated, ExceptionGroup survives structured extraction with locals off, context resets, native
incident behavior matches expected IDs and parser behavior matches the specified complete/partial
histories. Full raw output is in `raw/results.json` and `raw/probe-strengthened.txt`.

The first and intermediate executions passed their narrower checks; their original stdout remains
in `raw/probe-first.txt` and `raw/probe-final.txt`. The strengthened run uses a real failed attempt
and adds explicit fan-in/refusal assertions. No failed probe invocation was replaced or relabelled.
The initial shell orientation returned1 because an unset UV_PROJECT_ENVIRONMENT made printenv
return1; environment creation/probes were not failures. Subsequent commands explicitly clear that
variable for environment setup. No second repeated failure occurred.

**not_run:** real installed ci/Rich UX, OTel branch, actual subprocess context propagation,
remote delivery, threads racing one shared buffer, process-wide byte budgets, queue saturation,
resource lifecycle deadlines, full product qualification, and quantitative performance claims.
No production normalization helper or parallel diagnostic framework was introduced.

## Reproduce

From the repository root, choose a fresh external cache project directory and copy environment.toml
as its pyproject.toml and uv.lock as its uv.lock. For the original environment:

```bash
env -u UV_PROJECT_ENVIRONMENT UV_LOCKED=0 uv sync --project /home/paul/.cache/corpus-logging-investigations/events --python 3.14.10
/home/paul/.cache/corpus-logging-investigations/events/.venv/bin/python docs/design_review/evidence/2026-11-01_logging-events-history/probe.py
```

Use the copied lock for reproduction; UV_LOCKED=0 above is the original candidate setup command,
not permission for upgrading packages. The script writes synthetic raw outputs only in its folder.
A direct cache-environment interpreter intentionally maintains the independent provider boundary.
Root owns any evidence-record finalization and subsequent plan decisions.

## Sources and retained receipts

Context7 first: structlog standard-library/API docs, Eliot parser/continuation docs. Context7's
Logbook resolver returned Java Zalando Logbook, so it was not used as Python API evidence.
Python Logbook native installed source was inspected instead.

- [structlog standard-library contracts](https://www.structlog.org/en/stable/standard-library.html)
- [structlog exact source](https://github.com/hynek/structlog/tree/26.1.0/src/structlog)
- [Loguru0.7.3 handler](https://github.com/Delgan/loguru/blob/0.7.3/loguru/_handler.py)
- [Loguru0.7.3 stdlib bridge](https://github.com/Delgan/loguru/blob/0.7.3/loguru/_simple_sinks.py)
- [Logbook handler docs](https://logbook.readthedocs.io/en/stable/api/handlers.html)
- [Eliot exact parser](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/parse.py)
- [Eliot continuation contracts](https://eliot.readthedocs.io/en/stable/generating/threads.html)

`raw/native-sources.txt` retains installed Logbook FingersCrossedHandler and Eliot parser/completeness
methods. `raw/routing-source.txt` retains installed Loguru bridge/handler and structlog formatter.
`raw/package-metadata.json` retains version requirements and relevant source digests.
`raw/branches.json`, `raw/eliot-history.json`, and `raw/fanin-refusal.json` retain actual synthetic
observations; raw files contain no real credentials or source content.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**logging-investigations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Select field-preserving event routing and native incident capture](records/logging.i01.json) | LOG-00 | passed | I01, LOG-00 | 2026-11-01 |
| [Select causal history semantics](records/logging.i02.json) | LOG-00 | passed | I02, LOG-00 | 2026-11-01 |
<!-- evidence-index:end -->
