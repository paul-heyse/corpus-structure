# Loguru — Comprehensive Python Library Overview

Target: Loguru 0.7.3 (latest verified stable release) · Research date: November 1, 2026 · Python ≥3.5, <4.0 · MIT license

Loguru is a Python logging library that replaces much of the configuration machinery associated with the standard `logging` module with a unified logger, configurable output sinks, structured event records, contextual metadata, and integrated diagnostics.

Its architectural significance extends beyond simplified logging syntax. Loguru combines several capabilities that otherwise require separate handlers, formatters, filters, adapters, context management, file-management utilities, and exception-formatting components.

Official documentation: `https://loguru.readthedocs.io/en/stable/`

Source repository: `https://github.com/Delgan/loguru`

PyPI: `https://pypi.org/project/loguru/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 1. Architectural orientation

Loguru is built around a single shared logging core, exposed through `from loguru import logger`. Instead of instantiating named loggers and building a hierarchy of handlers, application modules use this shared interface. Each log event carries its originating module, function, file, line, timestamp, thread, process, severity, and contextual data.

The central processing model is:

Logging call

Level, template, arguments, exception, caller

Shared logger core

Level gating · Record construction · Context · Patching

Per-sink processing

Filter · Format · Serialize · Exception rendering · Optional queue

Console / files

TTY, rotation, retention

Python callables

Custom dispatch and inspection

Async sinks

Event-loop tasks

Standard logging

Existing Handler ecosystem

This architecture creates three useful distinctions:

1. Logger interface versus sink configuration. The logger creates events and manages shared state; individual sinks determine what is accepted and how it is delivered.
2. Structured records versus rendered messages. Metadata remains available to filters, patchers, and custom sinks even when the final output is human-readable text.
3. Global configuration versus contextual logger views. `bind()`, `patch()`, `contextualize()`, and `opt()` customize event construction without requiring independent logging infrastructures.

The default logger writes to `sys.stderr` at `DEBUG` level. It is immediately usable, but the default sink can be removed or replaced.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+1



## 2. Capability map

| Capability family     | Principal mechanisms                                                                    | Architectural significance                               |
| --------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Event generation      | `trace`, `debug`, `info`, `success`, `warning`, `error`, `critical`, `log`, `exception` | Common event interface with consistent metadata          |
| Dispatch              | `add`, `remove`, `configure`, `filter`, `level`                                         | Independently configurable destinations and filtering    |
| Context               | `bind`, `contextualize`, `patch`                                                        | Enrichment without custom logger classes                 |
| Structured logging    | Record dictionaries, `serialize`, custom sinks                                          | Machine-readable observability events                    |
| File lifecycle        | `rotation`, `retention`, `compression`, `watch`                                         | Integrated local log management                          |
| Concurrency           | `enqueue`, `context`, `complete`, coroutine sinks                                       | Thread, process, and event-loop integration              |
| Diagnostics           | `catch`, `exception`, `backtrace`, `diagnose`                                           | Exception capture and contextual tracebacks              |
| Performance controls  | Level gating, `opt(lazy=True)`, sink filtering                                          | Avoiding unnecessary event preparation and output work   |
| Ecosystem integration | `logging.Handler`, interception recipes, context enrichment                             | Compatibility with existing Python observability tooling |
| Operational tooling   | Environment defaults, `enable`/`disable`, `parse`                                       | Configuration, selective activation, and log extraction  |

The important design opportunity is that these capabilities compose. A single event can inherit task-local context, be enriched once, pass through different sink policies, and produce both compact structured output and detailed diagnostic output—without implementing a separate record-routing framework.

## 3. Event generation, severity, and filtering

### 3.1 Severity model

Loguru defines seven built-in levels:

| Level      | Numeric severity | Meaning                        |
| ---------- | ---------------- | ------------------------------ |
| `TRACE`    | 5                | Fine-grained execution tracing |
| `DEBUG`    | 10               | Debugging information          |
| `INFO`     | 20               | General operational events     |
| `SUCCESS`  | 25               | Successful operations          |
| `WARNING`  | 30               | Potential problems             |
| `ERROR`    | 40               | Failures                       |
| `CRITICAL` | 50               | Severe failures                |

`logger.level(name, no=..., color=..., icon=...)` supports custom levels and modifications to existing level presentation.

A consequential distinction: level identity is name-based, while filtering is severity-based. Multiple names may share a severity, and changing an existing level's numeric severity is not supported. Custom levels are emitted using `logger.log("CUSTOM", ...)`, rather than dynamically creating new logger methods.

### 3.2 Filtering at two different scopes

Loguru provides both:

- Module activation: `logger.disable("package")` and `logger.enable("package")` suppress or allow events originating from a module and its descendants.
- Per-sink admission: `logger.add(..., level=..., filter=...)` decides which events reach a particular destination.

The sink filter supports three representations:

| Filter type | Behavior                                                                     |
| ----------- | ---------------------------------------------------------------------------- |
| Callable    | Receives a record dictionary and decides admission                           |
| String      | Accepts events originating from a module and its descendants                 |
| Dictionary  | Defines module-specific severity thresholds, including hierarchical fallback |

For example:

```
levels = {    "": "INFO",    "app.parser": "DEBUG",    "third_party": "WARNING",    "noisy_package": False,}logger.add("application.log", level=0, filter=levels)
```

The empty-string entry supplies the general threshold. The most specific matching module entry controls the filter, while `False` suppresses an entire subtree. The outer sink `level` threshold still applies; setting the sink to `level=0` allows the dictionary to govern severity independently.

This allows module-specific verbosity without requiring an equivalent tree of logger objects or individually configured handlers.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+1



## 4. Sink architecture and routing

### 4.1 Heterogeneous output destinations

`logger.add()` is the central sink-registration mechanism.

| Sink type                 | Native capabilities                                                   | Important boundary                                          |
| ------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| File path (`str`, `Path`) | File opening, timestamped filenames, rotation, retention, compression | File-management options belong to this sink type            |
| File-like object          | `write()`, optional `flush()`, `stop()`, asynchronous `complete()`    | Resource ownership depends on the supplied object           |
| Ordinary callable         | Receives the formatted message with its associated record             | Application owns delivery, retries, and downstream behavior |
| Coroutine function        | Schedules async sink invocations on an event loop                     | Requires explicit lifecycle coordination                    |
| `logging.Handler`         | Converts Loguru messages into standard `LogRecord` objects            | Adapts rather than replaces the external handler's behavior |

Each registration returns an integer sink identifier. `logger.remove(id)` removes that sink; `logger.remove()` removes all active sinks, including the default console sink.

A callable sink is particularly expressive because its argument is not merely a plain string. The `Message` object is string-like and exposes `.record`, allowing a sink to process metadata independently of the rendered text.

```
def event_sink(message):    record = message.record    event = {        "timestamp": record["time"].isoformat(),        "severity": record["level"].name,        "message": record["message"],        "attributes": record["extra"],    }    publish(event)logger.add(event_sink, level="INFO")
```

This is an illustrative example of Loguru's data-access interface. `publish()` represents an application-defined integration, not a native Loguru transport.

### 4.2 Sink behavior and isolation

Each sink independently controls:

- Severity threshold and filtering.
- Text formatting and color processing.
- JSON serialization.
- Exception traceback presentation.
- Optional queue-based dispatch.
- Whether failures originating inside sink processing are caught.

A single event can therefore appear as detailed console text, a JSON object in a file, and a compact notification through another sink.

Important: Loguru does not guarantee that all sinks succeed together. `catch=True`, the default for `add()`, reports sink-processing failures to `stderr` rather than propagating them to the logging caller. `catch=False` allows those errors to propagate where execution semantics permit.

Custom sinks can replace substantial amounts of routing and output-adapter code, but transport guarantees, external retries, delivery acknowledgments, and durable buffering remain the responsibility of the sink implementation or its underlying service.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+2



## 5. Structured records and contextual enrichment

This is one of Loguru's most consequential capability families.

### 5.1 Record schema

Every event has a `record` dictionary with built-in fields:

| Category  | Record fields                                | Notable semantics                                        |
| --------- | -------------------------------------------- | -------------------------------------------------------- |
| Event     | `message`, `level`, `time`, `elapsed`        | Level is an object with name, numeric severity, and icon |
| Origin    | `name`, `module`, `function`, `file`, `line` | Automatically derived from the caller                    |
| Execution | `process`, `thread`                          | Objects exposing identifier and name                     |
| Failure   | `exception`                                  | Type, value, traceback, or `None`                        |
| Extension | `extra`                                      | Arbitrary application-defined attributes                 |

The timestamp is a timezone-aware local `datetime`. Source-file and process metadata are structured values rather than preformatted strings.

For standard formatting, Loguru supports expressions such as `{level.no}`, `{file.path}`, `{process.id}`, and `{extra[request_id]}`.

The record is accessible from filters, custom formatters, and sinks. This enables multiple representations of the same underlying event without first parsing Loguru's terminal output.

### 5.2 Four enrichment mechanisms

The distinction between enrichment mechanisms is important.

| Mechanism                        | Scope                                           | Typical role                                        |
| -------------------------------- | ----------------------------------------------- | --------------------------------------------------- |
| `logger.configure(extra=...)`    | Shared logger core                              | Common service or deployment attributes             |
| `logger.bind(**kwargs)`          | Returned logger view                            | Persistent component, object, or subsystem identity |
| `logger.contextualize(**kwargs)` | Dynamic execution context                       | Request IDs, task IDs, correlation metadata         |
| `logger.patch(callback)`         | Every record emitted through the patched logger | Computed fields, normalization, enrichment          |

`bind()` returns another logger interface sharing the same underlying core. It carries additional `extra` values, and multiple bound logger views can coexist without creating independent sink registries.

`contextualize()` uses Python `contextvars`. It temporarily supplies attributes visible to logging calls within the context and restores the preceding context afterward. It distinguishes concurrent threads and asynchronous tasks, making it useful for request-scoped logging in async applications.

`patch()` accepts a function that modifies the record in place before dispatch. Patchers can be chained, execute in registration order, and are applied once per event before the event is sent to its sinks. The global `configure(patcher=...)` callback executes before logger-view patchers.

Direct modification of `record["extra"]` is the preferred extension mechanism; altering reserved record fields can interfere with Loguru internals.

### 5.3 Composition example

```
from loguru import loggerlogger.configure(extra={"service": "ingestion"})log = logger.bind(component="parser")def enrich(record):    record["extra"]["event_class"] = (        "failure" if record["level"].no >= 40 else "operation"    )log = log.patch(enrich)with logger.contextualize(request_id="req-42"):    log.info("Parsed {} records", 125, source="incoming.csv")
```

The resulting event has its normal contextual information plus:

```
record["extra"] == {    "service": "ingestion",    "request_id": "req-42",    "component": "parser",    "source": "incoming.csv",    "event_class": "operation",}
```

This combination provides declarative event metadata without a dedicated adapter class, manually propagated request-context dictionary, or custom record factory.

The event's formatted text is `"Parsed 125 records"`; its additional context remains available independently.

### 5.4 Semantic limits of contextual data

`extra` is an extensible Python dictionary, not a validated schema. Loguru does not automatically enforce field names, types, semantic meanings, cardinality, or sensitive-data restrictions.

Important distinctions:

- `bind()` supplies values captured in a logger view; `patch()` can compute values for each emitted event.
- `contextualize()` follows execution context, not an automatically distributed network trace.
- Context is not automatically propagated across unrelated processes or network requests.
- Logging-call keyword arguments participate in message formatting and, by default, are also captured in `extra`.
- Unintended keyword capture can be disabled with `logger.opt(capture=False)`.

For a system with a canonical event schema, Loguru can perform capture and enrichment, while explicit validation and canonical serialization can remain in a dedicated event-processing layer.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+3



## 6. Message formatting and per-call controls

### 6.1 Message templates versus sink formatters

Loguru has two separate formatting stages.

Message construction uses Python's brace-style formatting:

```
logger.info("Processed {} items in {:.2f}s", count, elapsed)
```

Sink formatting determines how the constructed event appears:

```
logger.add(    "events.log",    format="{time:YYYY-MM-DD HH:mm:ss} | {level.name} | {name} | {message}")
```

The distinction matters for correctness and performance. The message template is associated with the call, while sink formatters independently consume the resulting record.

A sink's `format` can also be a callable receiving the record and returning a format-template string. This enables dynamic formatting based on severity, module, or attributes.

Unlike a string `format`, a callable format must explicitly supply newline handling and exception rendering, typically with `\n{exception}`.

### 6.2 `logger.opt()` — event construction controls

`opt()` returns a logger view with modified options.

| Option           | Capability                                                     | Important implication                                              |
| ---------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| `lazy=True`      | Evaluates callable formatting arguments only when needed       | Avoids expensive argument computation for globally disabled levels |
| `exception=True` | Includes current exception information                         | Generalizes `logger.exception()` beyond `ERROR` severity           |
| `record=True`    | Exposes the record to the message template                     | Enables contextual message formatting                              |
| `colors=True`    | Interprets color markup in the message template                | Useful for targeted console emphasis                               |
| `raw=True`       | Bypasses the normal sink text formatter                        | Useful for exact textual output and progress displays              |
| `capture=False`  | Suppresses automatic copying of formatting kwargs into `extra` | Separates presentation arguments from structured attributes        |
| `depth=N`        | Uses an earlier stack frame as the event origin                | Preserves caller attribution through logging wrappers              |

`lazy=True` is particularly useful when generating diagnostics requires expensive computation:

```
logger.opt(lazy=True).debug(    "Analysis result: {}",    lambda: expensive_analysis(),)
```

The lambda is not invoked when `DEBUG` is below the logger's global effective level threshold. However, this does not guarantee that it will be skipped when all sink-specific filters reject the event, because message preparation precedes those filters.

Two subtleties:

- Calling `opt()` repeatedly does not accumulate options. A subsequent `opt()` resets unspecified options to defaults.
- Using `{}`-format arguments with messages containing literal braces can raise formatting errors, including when an f-string has already embedded dictionary content. `bind()` can attach structured fields without causing another formatting pass.

### 6.3 Time and terminal formatting

Loguru provides a token-based date formatter with support for fractional seconds, calendar fields, ISO weeks, timezone offsets, and Unix timestamps.

Examples:

- `{time:YYYY-MM-DD HH:mm:ss.SSS}`
- `{time:YYYY-MM-DDTHH:mm:ss.SSSZ}`
- `{time:YYYY-MM-DD HH:mm:ss!UTC}`

The `!UTC` suffix converts the time to UTC before rendering.

Terminal formatting supports level-dependent markup, text styling, named colors, 8-bit colors, hexadecimal colors, and RGB foreground/background colors. Output is colorized or stripped based on sink configuration and terminal detection.

This formatting machinery is useful for interactive diagnostics, but text styling is separate from structured event semantics.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+3



## 7. File logging and storage lifecycle

Loguru includes file-management capabilities that otherwise often require separate rotating-file handlers or application-maintained cleanup logic.

### 7.1 Rotation, retention, and compression

| Feature               | Supported controls in 0.7.3                                              | Behavior                                      |
| --------------------- | ------------------------------------------------------------------------ | --------------------------------------------- |
| Rotation              | Byte size, time interval, time of day, human-readable schedule, callable | Closes the active file and starts another     |
| Retention             | File count, age, callable                                                | Removes or processes older matching log files |
| Compression           | gzip, bzip2, xz, lzma, tar variants, ZIP, callable                       | Archives closed log files                     |
| Timestamped paths     | `{time}` in file path                                                    | Incorporates creation time in filenames       |
| Delayed creation      | `delay=True`                                                             | Opens file only when first needed             |
| External file changes | `watch=True`                                                             | Reopens files replaced or deleted externally  |
| Open policy           | `mode`, `encoding`, `buffering`, other `open()` arguments                | Controls underlying file behavior             |

Example:

```
logger.add(    "logs/events_{time:YYYY-MM-DD}.log",    rotation="100 MB",    retention="14 days",    compression="gz",    watch=True,    enqueue=True,)
```

Rotation is evaluated when messages are emitted, rather than by an independent timer. A time boundary therefore does not necessarily cause an immediate rotation if logging is idle.

Retention considers matching log files from previous sessions as well as newly rotated files. Compression occurs at rotation, or at sink closure if rotation is disabled.

### 7.2 Custom lifecycle policies

Rotation, retention, and compression each have callable extension points:

- Rotation: receives the message and current file object; returns whether to rotate.
- Retention: receives the collection of candidate paths and controls their disposition.
- Compression: receives a closed file path and can implement custom archiving or relocation.

These extension points allow compound storage policies and custom archive workflows without replacing Loguru's file sink.

In 0.7.3, combining size and time rotation requires a custom rotation callable. Support for directly supplying a list of rotation conditions is present in the upstream unreleased changelog, not in the verified stable version.

### 7.3 Operational limitations

Loguru's managed file sink is not a distributed log store.

- Multiple independent processes should not each manage the same file path with separate rotating handlers.
- Rotation and compression involve file operations and may have significant cost.
- `watch=True` addresses externally changed files; it does not coordinate arbitrary independent log writers.
- Custom lifecycle callbacks must not recursively log through the same logger, because that can cause lock reentrancy failures.
- File permissions still follow operating-system behavior; Loguru supports custom file openers when restricted permissions are required.

The native machinery is well suited to local file lifecycle management, whereas coordinated retention across machines, remote archival guarantees, and centralized indexing belong to external infrastructure.

Source: `https://loguru.readthedocs.io/en/stable/api/logger.html`

File lifecycle recipes: `https://loguru.readthedocs.io/en/stable/resources/recipes.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+4



## 8. JSON serialization and observability event schemas

### 8.1 Built-in JSON serialization

Passing `serialize=True` converts an emitted event into a JSON string.

```
logger.add("events.jsonl", serialize=True)
```

The default representation is an envelope containing two top-level fields:

```
{
  "text": "formatted log line",
  "record": {
    "message": "An event happened",
    "level": {"name": "INFO", "no": 20, "icon": "ℹ️"},
    "extra": {"request_id": "req-42"},
    "time": {
      "repr": "timezone-aware datetime representation",
      "timestamp": 0
    }
  }
}
```

Conceptual excerpt of the output schema, not a complete literal event. The timestamp above is illustrative.

The actual `record` envelope includes origin, process, thread, timing, and exception fields. The source implementation converts the record with `json.dumps(..., default=str, ensure_ascii=False)`, followed by a newline.

Consequently:

- Python objects in `extra` that are not directly JSON serializable may become string representations.
- Exception information is converted to a JSON-compatible description; the original traceback object is not preserved as a JSON object.
- The emitted JSON contains both rendered text and structured metadata.
- Serialization does not automatically impose a conventional observability schema.

This is valuable when preserving diagnostic context is more important than imposing a narrow ingestion contract.

### 8.2 Custom structured schemas

For a predefined schema, Loguru supports two useful approaches.

Custom callable sink: read `message.record`, construct the required event, validate or serialize it, and deliver it to the target system.

Custom formatter or patcher: compute the desired representation and put it into `record["extra"]`, where a sink template can emit it.

`patch()` is useful when multiple sinks need the same computed canonical representation, since a patcher is invoked once per logged event rather than independently by each sink.

### 8.3 Integration boundary

Loguru's built-in JSON format is not automatically ECS, OpenTelemetry LogRecord, or another vendor-defined schema. Nor does its `serialize=True` flag implement transport, batching, retry, or trace-export protocols.

An integration can nevertheless map Loguru records into those representations using their structured fields.

For example, OpenTelemetry's active trace/span context can be read by application code and inserted into `extra` via a patcher. A separate OpenTelemetry SDK or exporter remains responsible for distributed-tracing semantics and transport.

This distinction is important: Loguru provides structured event capture and output extensibility, not a complete distributed telemetry system.

Source implementation: `https://raw.githubusercontent.com/Delgan/loguru/0.7.3/loguru/_handler.py`

Serialization recipes: `https://loguru.readthedocs.io/en/stable/resources/recipes.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



## 9. Concurrency, asynchronous sinks, and process lifecycles

Loguru's concurrency capabilities are substantial, but three different execution models must be distinguished.

### 9.1 Synchronous, queued, and coroutine sinks

| Mode                     | Execution model                                                                      | Principal advantage                                                 | Main limitation                                      |
| ------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------- | ---------------------------------------------------- |
| Default synchronous sink | Logging caller performs formatting and sink write                                    | Immediate dispatch, straightforward lifecycle                       | Slow sinks can delay callers                         |
| `enqueue=True`           | Event enters a multiprocessing-compatible queue; dedicated consumer thread writes it | Separates producer from sink I/O and coordinates multiple processes | Queue growth, serialization cost, consumer lifecycle |
| Coroutine sink           | Logging call schedules a task on an asyncio event loop                               | Integrates asynchronous I/O destinations                            | Tasks need a running loop and explicit completion    |

Loguru protects ordinary sinks with internal locks, providing thread-safe writes without requiring custom locking in each sink.

However, thread safety does not mean lock-free operation, unlimited concurrency, or freedom from I/O latency.

### 9.2 Queued dispatch

With `enqueue=True`, Loguru 0.7.3 uses `multiprocessing.SimpleQueue` and an internal consumer thread.

This changes the execution boundary:

- The caller constructs and formats the event.
- The event is submitted to the queue.
- A consumer thread receives it and performs the actual sink write.
- Logging calls generally avoid waiting for slow sink I/O.

The design supports a shared destination for multiple related processes when the queue and handler lifecycle are configured correctly.

Important performance limitation: The queue is unbounded. If producers persistently outpace the sink, buffered records can accumulate in memory. The queue is not a bounded backpressure mechanism or a durable message broker. Queue submission, serialization, and operating-system operations can also contribute latency.

An upstream issue specifically reports unbounded growth under slow-sink workloads. The use of `SimpleQueue` is independently verifiable in the tagged implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Source: `https://raw.githubusercontent.com/Delgan/loguru/0.7.3/loguru/_handler.py`

Issue: `https://github.com/Delgan/loguru/issues/1419`

### 9.3 Multiprocessing semantics

Loguru's process integration depends on how workers are created.

Fork-based workers: May inherit the existing logger and handlers, including shared queue resources. Queue-based dispatch helps prevent concurrent writes to the same sink.

Spawn-based workers: Start a fresh interpreter. Logger configuration is not automatically reconstructed as if the processes shared global memory. Passing an appropriately configured logger or initializing workers explicitly becomes necessary.

Mixed multiprocessing contexts: A queue created with one context may not be compatible with processes created using another. Loguru 0.7.3 supports an explicit `context` parameter:

```
import multiprocessingfrom loguru import loggerctx = multiprocessing.get_context("spawn")logger.add("events.log", enqueue=True, context=ctx)
```

The owner process is responsible for the queue's consumer thread and lifecycle. Removing its queued handler while child processes continue producing messages can disrupt delivery.

The official recipes distinguish direct processes from process pools and show initializer-based sharing when necessary. They also recommend `logger.complete()` before a worker exits.

Modern worker frameworks such as Gunicorn and Uvicorn add additional lifecycle complications. Per-worker file destinations can be simpler than attempting to share independent rotating-file sinks across workers.

### 9.4 Coroutine sinks

A coroutine function can be registered as a sink:

```
async def async_sink(message):    await send_event(message.record)logger.add(async_sink)
```

Loguru schedules each accepted event as an asyncio task.

By default, it uses the running event loop at logging time. The optional `loop` argument associates a sink with a specified loop.

An important behavior in 0.7.3: when no loop was supplied and no event loop is running, a coroutine-sink invocation can be discarded. A logging call does not itself create and manage an event loop.

### 9.5 `logger.complete()` — synchronization, not durable acknowledgment

`complete()` performs two operations:

1. Waits for already queued messages to be processed by queued handlers.
2. Returns an awaitable that can wait for coroutine-sink tasks associated with the currently running event loop.

```
async def main():    logger.info("Processing completed")    await logger.complete()
```

The method is also callable from synchronous code to drain queued messages.

This is an important shutdown primitive, but it is not equivalent to persistent delivery acknowledgment from a remote system. It does not guarantee that downstream infrastructure stored or indexed an event, or that a message lost during a process crash will be recovered.

It also does not await arbitrary tasks scheduled on unrelated event loops.

Source: `https://loguru.readthedocs.io/en/stable/resources/recipes.html`

Async and lifecycle API: `https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+6



## 10. Exception capture and diagnostic tracebacks

Loguru combines exception event generation, automatic interception, and rich traceback rendering.

### 10.1 Exception event mechanisms

| Mechanism                    | Function                                                             |
| ---------------------------- | -------------------------------------------------------------------- |
| `logger.exception(...)`      | Logs an `ERROR` event with the currently handled exception           |
| `logger.opt(exception=True)` | Includes exception data at a chosen log level                        |
| `logger.opt(exception=exc)`  | Associates an explicit exception object                              |
| `logger.catch()`             | Decorates or surrounds an operation to intercept matching exceptions |

`logger.exception()` is intended for use within exception-handling code. `opt(exception=...)` is more general and accepts exception objects or exception-info tuples.

### 10.2 Automatic error interception

`logger.catch()` is both a function decorator and a synchronous context manager.

It supports:

- `exception`: exception types to intercept.
- `exclude`: exception types explicitly allowed to propagate.
- `level`: severity of the generated event.
- `reraise`: whether to propagate after logging.
- `onerror`: callback invoked after a caught exception is logged.
- `default`: return value when a decorated function fails and the exception is suppressed.
- `message`: custom event description.

```
@logger.catch(reraise=True, level="ERROR")def execute_operation():    perform_work()
```

By default, `reraise=False`, which means Loguru can suppress the exception after recording it.

This is desirable for some fault-containment boundaries, but potentially dangerous for operations in which failure must propagate through the application.

For example, wrapping a command-line entry point with default `catch()` behavior can produce a logged error while allowing the process to exit successfully. The documented `onerror` mechanism can influence the failure exit status.

The feature is therefore an exception-control mechanism, not merely a formatting convenience.

### 10.3 Backtrace and diagnosis

Loguru separates two enhancements:

`backtrace=True` extends the displayed traceback beyond the exception-catching frame, helping expose the call path that led to the failure.

`diagnose=True` annotates the traceback with variable values and expressions, using functionality influenced by `better_exceptions`.

These options are configured independently for each sink:

```
logger.add(    "errors.log",    level="ERROR",    backtrace=True,    diagnose=False,)
```

Both default to `True` in `logger.add()` in 0.7.3.

`diagnose=True` is especially useful in controlled debugging environments but can expose secrets, credentials, request contents, or other private values. The upstream documentation explicitly recommends disabling it in production.

Additional diagnostic capabilities include rendering chained exceptions, `ExceptionGroup` instances, and exception notes. `ExceptionGroup` formatting support was introduced in 0.7.2, while 0.7.3 corrected a Python 3.13 diagnostic-formatting issue.

Loguru also supports custom exception rendering through formatter callbacks—for example, delegating to another traceback-formatting package. It does not need to own the entire exception-presentation pipeline.

Sources:

`https://loguru.readthedocs.io/en/stable/api/logger.html`

`https://loguru.readthedocs.io/en/stable/resources/recipes.html`

`https://github.com/Delgan/loguru/blob/0.7.3/CHANGELOG.rst`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+3



## 11. Interoperability with Python's `logging` ecosystem

Loguru interoperates with the standard library but does not transparently replace its logging hierarchy. The direction of integration matters.

### 11.1 Loguru to standard `logging`

A standard `logging.Handler` can be registered directly as a Loguru sink:

```
import loggingfrom loguru import loggerhandler = logging.StreamHandler()logger.add(handler, level="INFO", format="{message}")
```

Loguru converts events into standard `logging.LogRecord` objects and passes them to the supplied handler.

This permits reuse of existing handler implementations, including handlers supplied by observability SDKs and other Python packages.

Version-specific subtlety: In 0.7.3, the standard handler's `.level` is not independently enforced by this adapter. The Loguru sink's `level` and `filter` settings should govern admission. Respecting `logging.Handler.level` is listed as a fix in unreleased upstream changes.

### 11.2 Standard `logging` to Loguru

Libraries that emit events through `logging.getLogger()` do not automatically send those events to Loguru.

The documented approach is an `InterceptHandler` subclass of `logging.Handler` that forwards records to the Loguru logger, using:

- Original severity name or numeric level.
- `record.getMessage()` for the already formatted message.
- `record.exc_info` for exception information.
- `logger.opt(depth=...)` to preserve the original caller location.

The bridge can be installed through standard logging configuration.

For heterogeneous applications, this may provide one formatting and routing plane for both standard-library and Loguru events.

However, a bridge based only on `getMessage()` does not necessarily preserve arbitrary structured attributes from the original `LogRecord`. Those need deliberate mapping when required.

### 11.3 Avoiding double logging and recursion

Two-way forwarding requires careful handling:

- Existing standard-logging handlers may continue emitting independently, causing duplicate output.
- A Loguru sink forwarding to standard logging can feed an interception handler and create a cycle.
- Third-party frameworks may install or replace handlers during initialization.
- Source attribution can become inaccurate without appropriate caller-frame handling.

Loguru's migration and troubleshooting documentation covers these behaviors explicitly.

### 11.4 Testing interoperability

Pytest's `caplog` and `unittest.TestCase.assertLogs()` are built around standard `logging`, not Loguru's sink registry.

The official pytest recipe temporarily attaches `caplog.handler` as a Loguru sink:

```
@pytest.fixturedef caplog(caplog):    sink_id = logger.add(        caplog.handler,        level=0,        format="{message}",        filter=lambda record: record["level"].no >= caplog.handler.level,    )    yield caplog    logger.remove(sink_id)
```

This provides access to conventional captured logging output while preserving normal Loguru event emission.

The third-party `pytest-loguru` package offers an alternative integration. The `logot` testing library also documents Loguru-specific log assertions.

Architectural distinction: Test capture is another sink-routing problem. No separate test-only logging infrastructure is inherently required, but fixture isolation and global sink cleanup remain important.

Sources:

`https://loguru.readthedocs.io/en/stable/resources/migration.html`

`https://loguru.readthedocs.io/en/stable/resources/troubleshooting.html`

`https://github.com/Delgan/loguru/blob/0.7.3/loguru/_simple_sinks.py`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+2



## 12. Configuration, library boundaries, and extensibility

### 12.1 Centralized configuration

`logger.configure()` consolidates five configuration families:

| Parameter    | Responsibility                                                    |
| ------------ | ----------------------------------------------------------------- |
| `handlers`   | Replaces the active sink set with supplied `add()` configurations |
| `levels`     | Adds or updates custom level definitions                          |
| `extra`      | Sets shared contextual defaults                                   |
| `patcher`    | Configures one global record-enrichment function                  |
| `activation` | Applies module enable/disable rules in sequence                   |

Only supplied parameters are changed. In particular, supplying `handlers` removes existing sinks first; changing unrelated settings does not automatically rebuild sink configuration.

This provides a native configuration model for application initialization without introducing a configuration class hierarchy.

It is not a native YAML/JSON configuration-file loader. The third-party `loguru-config` package supplies that capability.

### 12.2 Environment-driven defaults

Loguru supports environment variables for sink parameter defaults and built-in level appearance.

Examples:

```
LOGURU_LEVEL=WARNING
LOGURU_FORMAT="{time} | {level.name} | {message}"
LOGURU_DIAGNOSE=NO
LOGURU_AUTOINIT=False
LOGURU_DEBUG_COLOR="<blue>"
```

`LOGURU_AUTOINIT=False` disables installation of the initial `stderr` sink, which is distinct from suppressing the creation of all possible future sinks.

Environment variables configure defaults; they are not a live settings-reload or distributed configuration mechanism.

Changing the configuration of an already registered sink generally requires removing and re-adding it, or designing its filter to consult mutable external state.

### 12.3 Application versus library ownership

The official guidance makes a useful distinction:

- Applications own output policy: destination selection, levels, formatting, rotation, and lifecycle.
- Libraries may emit through Loguru, but should avoid unilaterally installing global sinks or imposing application-wide configuration.

A library using Loguru can disable logging for its own namespace and let an application selectively enable it.

This is important because the singleton logger's sink registry is shared across modules in the same Python interpreter. `configure(handlers=...)` is consequently not an isolated operation local to one imported package.

The standard `logging` ecosystem still has an interoperability advantage where dependencies are expected to expose a standard logger hierarchy and leave routing entirely to the host application.

### 12.4 Type hints and platform support

Loguru exposes typing information through dedicated type declarations, including names such as `Logger`, `Message`, `Record`, `Level`, and sink-related protocols.

Some of these are typing-only definitions, not runtime objects importable directly from Loguru. Import-time use should be distinguished from annotations consumed by static type checkers.

The 0.7.3 distribution is a pure-Python wheel. Its platform-dependent dependencies include `colorama` and `win32-setctime` on Windows; `aiocontextvars` supports older Python versions without native `contextvars`.

The package metadata declares Python 3.5–3.x compatibility below Python 4, but the published classifiers extend through Python 3.13. The declared range should not be interpreted as independently verified compatibility with every newer interpreter release.

Sources:

`https://loguru.readthedocs.io/en/stable/api/logger.html`

`https://loguru.readthedocs.io/en/stable/api/type_hints.html`

`https://raw.githubusercontent.com/Delgan/loguru/0.7.3/pyproject.toml`

`https://pypi.org/project/loguru/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+2



## 13. Less obvious integration and processing capabilities

### 13.1 Streaming log parsing

Loguru has a `logger.parse()` API for extracting structured data from existing text logs.

Its main inputs are:

- A file path or readable file object.
- A regular expression with named capture groups.
- Optional `cast` functions for converting captured strings.
- A chunk size for incremental reading.

```
pattern = (    r"(?P<time>.*?) \| "    r"(?P<level>[A-Z]+) \| "    r"(?P<message>.*)")for event in logger.parse(    "application.log",    pattern,    cast={"level": str},):    consume(event)
```

This offers a lightweight migration or inspection mechanism for known log formats without constructing a separate regex-scanning framework.

It is not a general parser for nested JSON, arbitrary multiline tracebacks, or log formats without stable matching rules. For JSON-formatted logs, a JSON parser is generally a better fit.

### 13.2 Network and notification integrations

Because custom sinks are functions, event forwarding can be integrated with:

- HTTP clients and event collectors.
- Message queues and streaming systems.
- Email or notification services.
- Application-defined persistence.
- OpenTelemetry or ECS transformation adapters.

The official examples include the third-party `apprise` notification library for error alerts.

These integrations are compositions, not transports bundled into Loguru itself. The sink or associated library determines batching, authentication, retry, persistence, rate limits, and destination-specific error handling.

### 13.3 Console tools, warnings, and redirected output

Official recipes also cover integration with:

- `tqdm` progress bars.
- Python `warnings`.
- Standard output and standard error capture.
- Function entry/exit instrumentation through decorators.
- Custom exception renderers.

Such integrations can consolidate diagnostics into one event stream. Redirecting standard output is not always safe or desirable: it can create feedback loops if Loguru itself writes to the redirected stream.

### 13.4 Execution environments with incomplete frame information

Source attribution and rich tracebacks rely on Python frame inspection.

Consequently, compiled Cython modules, certain framework-generated call sites, frozen-import mechanisms, and some REPL environments can provide incomplete or misleading origin data.

The documented techniques include specifying `depth` in wrappers and compensating for missing `__name__` information.

This limits the assumption that every event will always have meaningful source-file, function, and line metadata.

Sources:

`https://loguru.readthedocs.io/en/stable/resources/recipes.html`

`https://loguru.readthedocs.io/en/stable/resources/troubleshooting.html`

`https://loguru.readthedocs.io/en/stable/api/logger.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+3



## 14. Security, performance, and reliability boundaries

### 14.1 Security considerations

Several Loguru conveniences have security implications when events contain untrusted data.

| Concern                        | Mechanism                                             | Consequence                                                                                    |
| ------------------------------ | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Diagnostic variable disclosure | `diagnose=True`                                       | Local variables and secrets may appear in exception output                                     |
| Untrusted format strings       | Brace-style message formatting                        | Attacker-controlled templates may access object attributes or otherwise expose unintended data |
| Log injection                  | Unescaped line breaks and terminal control characters | External values may forge apparent records or alter terminal presentation                      |
| Structured-data leakage        | Automatic capture of formatting kwargs into `extra`   | Sensitive fields may enter JSON output even when omitted from the visible message              |
| Unsafe deserialization         | `pickle.loads()` in custom network integrations       | Untrusted payloads may execute code                                                            |
| File access                    | Operating-system default file permissions             | Log files may be readable by unintended users                                                  |
| Sink callbacks                 | Arbitrary application code                            | Slow or failing integrations can affect logging reliability                                    |

The official security recipes explicitly cover malicious formatting strings, newline injection, unsafe pickle deserialization, diagnostic disclosure, and restricted file permissions.

For a structured logging architecture, a record-normalization or serialization boundary offers an opportunity to apply redaction, field allowlists, schema validation, and stable escaping before external publication.

Such controls are not automatic guarantees supplied by Loguru.

Source: `https://loguru.readthedocs.io/en/stable/resources/recipes.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation



### 14.2 Cost model

Loguru's principal costs can be separated by processing stage.

| Stage               | Potential work                                 | Native control                                         |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| Event admission     | Level and activation checks                    | Levels, module activation                              |
| Record construction | Stack inspection, clock reads, context capture | `opt(depth=...)`; early level gating                   |
| Message rendering   | Argument evaluation, formatting                | `opt(lazy=True)`                                       |
| Enrichment          | Patcher computation                            | Conditional logic in patchers                          |
| Per-sink processing | Filtering, formatting, JSON conversion         | Sink-specific `level`, `filter`, `format`, `serialize` |
| Dispatch            | Queue synchronization, process serialization   | `enqueue`                                              |
| Output              | File writes, network requests, compression     | Sink selection, queueing, lifecycle policies           |

Three performance distinctions are particularly consequential.

First, queueing moves output work away from callers, but does not eliminate event-construction and formatting costs. In 0.7.3, handler formatting occurs before submission to the internal queue.

Second, lazy formatting avoids unnecessary argument evaluation only when the event is rejected before that evaluation. It is not a universal guarantee that callbacks will be skipped whenever no destination ultimately emits a record.

Third, richer diagnostics and structured output perform additional work. Backtrace rendering, variable inspection, JSON conversion, and custom patchers may outweigh the cost of ordinary text logging for sufficiently verbose workloads.

There is no defensible universal claim that Loguru is faster or slower than standard `logging` across all configurations. Performance depends strongly on message frequency, formatting complexity, sink I/O, concurrency, and filtering selectivity.

### 14.3 Reliability and resource lifetime

Loguru's dispatch mechanisms provide useful coordination, but they do not establish end-to-end delivery guarantees.

Particular constraints include:

- Reentrancy: Logging from within a sink, custom file lifecycle callback, or certain signal/finalizer contexts can trigger protective deadlock errors.
- Queue capacity: `enqueue=True` uses an unbounded queue, not bounded flow control.
- Process shutdown: Queued and coroutine sinks require lifecycle coordination.
- Sink errors: `catch=True` generally isolates handler errors from the logging caller, which can also obscure failures if nobody monitors `stderr`.
- Sink termination: In 0.7.3, exceptions raised during some sink shutdown activities are not uniformly covered by `catch=True`; the fix is listed in the unreleased changelog.
- Crash durability: Queued events and in-flight coroutine tasks are not automatically recovered after process termination.
- External stream ownership: Captured or replaced `stdout`/`stderr` streams can be closed while Loguru still holds references to them.

The practical architectural boundary is clear: Loguru coordinates event creation and local dispatch; a durable telemetry pipeline must supply its own persistence, acknowledgments, bounded buffering, and recovery semantics.

Sources:

`https://loguru.readthedocs.io/en/stable/resources/troubleshooting.html`

`https://github.com/Delgan/loguru/blob/0.7.3/loguru/_handler.py`

`https://github.com/Delgan/loguru/blob/master/CHANGELOG.rst`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://loguru.readthedocs.io\&sz=32)

loguru documentation+2



## 15. Version-sensitive functionality: 0.7.3 versus upstream development

PyPI identifies 0.7.3, released December 6, 2024, as the latest stable release. The development branch includes additional APIs and behavior documented under an Unreleased heading.

These distinctions matter because documentation from `master` or `/latest/` may expose functionality not available in a normal 0.7.3 installation.

| Capability or behavior                                | Stable 0.7.3                                                                       | Upstream unreleased changes                            |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Spawn-process logger initialization                   | Manual initialization or appropriate logger sharing                                | New `logger.reinstall()`                               |
| Compound file rotation                                | Custom rotation callable                                                           | List of rotation conditions                            |
| Raw message template in record                        | Not a native `record["template"]` field                                            | New `record["template"]`                               |
| Python template-string messages                       | Existing brace-style formatting                                                    | Additional template-string support                     |
| `logger.catch()` async context manager                | Decorator and synchronous context manager; supports decorating coroutine functions | Async context-manager and async-generator enhancements |
| Standard `logging.Handler.level`                      | Not enforced by adapter                                                            | Handler level honored                                  |
| `NO_COLOR` and `FORCE_COLOR`                          | Not the documented native controls                                                 | Explicit environment-variable support                  |
| Default timestamp format                              | Existing default                                                                   | Planned inclusion of timezone offset                   |
| Enqueued standard `LogRecord` process/thread identity | Existing behavior                                                                  | Correction to attribution when enqueued                |

The development changelog also identifies fixes for rare frame objects, timezone formatting, sink termination, and other edge conditions. These should be treated as development-branch changes until included in a published release.

Stable changes worth knowing include `ExceptionGroup` formatting in 0.7.2, multiprocessing-context selection in 0.7.1, and Python 3.13 diagnostic-formatting fixes in 0.7.3.

Sources:

`https://pypi.org/project/loguru/`

`https://github.com/Delgan/loguru/blob/0.7.3/CHANGELOG.rst`

`https://github.com/Delgan/loguru/blob/master/CHANGELOG.rst`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 16. Primary-source reference map

The following sources offer the most useful paths into implementation details.

| Subject                                              | Direct source                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------------ |
| Overview and conceptual model                        | `https://loguru.readthedocs.io/en/stable/overview.html`                  |
| Complete logger API                                  | `https://loguru.readthedocs.io/en/stable/api/logger.html`                |
| Standard logging interoperability                    | `https://loguru.readthedocs.io/en/stable/resources/migration.html`       |
| Advanced recipes, security, multiprocessing, testing | `https://loguru.readthedocs.io/en/stable/resources/recipes.html`         |
| Troubleshooting and edge cases                       | `https://loguru.readthedocs.io/en/stable/resources/troubleshooting.html` |
| Typed API and static analysis                        | `https://loguru.readthedocs.io/en/stable/api/type_hints.html`            |
| Stable 0.7.3 changelog                               | `https://github.com/Delgan/loguru/blob/0.7.3/CHANGELOG.rst`              |
| Unreleased changes                                   | `https://github.com/Delgan/loguru/blob/master/CHANGELOG.rst`             |
| Logger and record construction                       | `https://github.com/Delgan/loguru/blob/0.7.3/loguru/_logger.py`          |
| Sink formatting, serialization, queues               | `https://github.com/Delgan/loguru/blob/0.7.3/loguru/_handler.py`         |
| File, async, callable, and standard-handler adapters | `https://github.com/Delgan/loguru/blob/0.7.3/loguru/_simple_sinks.py`    |
| File rotation implementation                         | `https://github.com/Delgan/loguru/blob/0.7.3/loguru/_file_sink.py`       |
| Packaging and dependencies                           | `https://github.com/Delgan/loguru/blob/0.7.3/pyproject.toml`             |

## 17. Architectural synthesis

Loguru's strongest capability is not its simplified API alone. It is the combination of a shared event-construction interface, rich contextual records, flexible per-destination policies, extensible sinks, and integrated file and exception management.

The most consequential combinations are:

1\. `bind()` + `contextualize()` + `patch()` provides persistent, execution-scoped, and computed event enrichment without building custom logger adapters or separate context-propagation machinery inside an application.

2\. Structured records + sink-specific filters and serialization permits one event to serve both human-readable diagnostics and machine-readable observability systems, without parsing rendered log strings.

3\. `enqueue=True` + coroutine sinks + `complete()` supports several concurrency and dispatch arrangements with a unified logging API, provided their distinct lifecycle and reliability guarantees are respected.

4\. File rotation + retention + compression replaces substantial local log-management code, while deliberately stopping short of distributed retention, persistence, or reliable telemetry delivery.

5\. Standard-handler interoperability + callable sinks allows existing logging and observability components to be reused instead of replaced, though preservation of structured attributes, levels, caller information, and failure semantics requires attention.

The largest conceptual limitation is equally important: Loguru is a flexible logging and dispatch library, not a schema-governed event platform, distributed tracing SDK, or durable ingestion system.

Its native mechanisms can remove significant bespoke logging infrastructure, while canonical event contracts, distributed context propagation, bounded delivery, durable persistence, and external observability semantics remain separable concerns.