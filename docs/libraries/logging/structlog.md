# structlog 26.1.0 — Python Library Capability Reference

Research date: October 31, 2026 · Target: structlog 26.1.0 (current stable release) · Python 3.10–3.15 · Scope: architecture, structured logging, processing, context management, interoperability, diagnostics, performance, and extension mechanisms

## 1. Executive overview

structlog is a configurable structured-event processing framework that decouples the information an application records from how that information is transformed, formatted, and delivered.

Its central abstraction is deliberately small: a logging call produces an event dictionary, which is passed through an ordered sequence of processors before reaching an underlying logger or output destination.

Unlike libraries organized principally around `logging.LogRecord` objects, handlers, or formatted strings, structlog makes the application-defined event dictionary its primary unit of processing.

This enables several important architectural capabilities:

- Structured events as first-class data: Domain-specific attributes retain their names and types until processing or serialization.
- Composable transformation: Processors implement enrichment, normalization, filtering, redaction, exception transformation, and rendering without requiring changes at individual logging call sites.
- Multiple context models: Immutable-style bound logger contexts coexist with execution-local `contextvars`.
- Independent output backends: Native stream-oriented loggers can avoid the standard-library logging system, while integration adapters preserve compatibility with existing logging infrastructure.
- Machine-readable diagnostics: JSON, logfmt, and structured exception representations can support downstream indexing, analysis, and automated reasoning.
- Performance-oriented execution: Native level filtering, logger caching, byte-oriented output, alternative JSON serializers, and asynchronous logging methods provide several ways to manage overhead.
- Extensibility and testing: Custom processors, logger wrappers, logger factories, and capture utilities expose the logging pipeline for specialized behavior and verification.

The value of structlog is therefore broader than converting traditional log messages to JSON. It provides a reusable mechanism for producing consistent diagnostic event data independently of its ultimate consumer.

### 1.1 Version and compatibility

| Property               | Verified status                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Current stable release | 26.1.0, released June 6, 2026                                                         |
| Supported Python       | Python 3.10 and newer, including 3.15                                                 |
| Implementation         | Python; platform-independent wheel                                                    |
| License                | MIT OR Apache-2.0                                                                     |
| Primary package        | `structlog`                                                                           |
| Optional integrations  | Python `logging`, Rich, Twisted, third-party framework and observability integrations |

Version 26.1.0 introduces qualified module identification in callsite diagnostics, compatibility improvements to the standard-library bound logger, monochrome Rich exception rendering, and changes to file-output logger resource management. It also corrects async callsite identification to report the originating thread rather than an executor worker. Python 3.8 and 3.9 are no longer supported.

The changelog additionally describes unreleased Python 3.15 lazy-import optimizations; these should not be attributed to the released 26.1.0 implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary sources:

`https://pypi.org/project/structlog/`

`https://github.com/hynek/structlog/releases/tag/26.1.0`

`https://www.structlog.org/en/stable/`

### 1.2 Capability map

| Capability family            | Key mechanisms                                       | Primary value                                               |
| ---------------------------- | ---------------------------------------------------- | ----------------------------------------------------------- |
| Event construction           | `get_logger`, `bind`, `new`, `unbind`                | Consistent structured event creation                        |
| Processing                   | Processor chains, `DropEvent`, custom processors     | Centralized event transformation and policy                 |
| Context propagation          | `structlog.contextvars`                              | Request/task-local diagnostic attributes                    |
| Rendering                    | JSON, logfmt, key-value, console                     | Destination-specific presentation                           |
| Exception diagnostics        | `ExceptionRenderer`, structured tracebacks           | Machine-readable failure context                            |
| Standard logging integration | `LoggerFactory`, `BoundLogger`, `ProcessorFormatter` | Interoperability with third-party logging                   |
| Async integration            | `ainfo`, `aerror`, etc.                              | Offloading synchronous logging operations                   |
| Performance                  | Native filtering, caching, bytes output              | Reduced work on hot logging paths                           |
| Development and testing      | `ConsoleRenderer`, `capture_logs`, capture factories | Inspection and deterministic event assertions               |
| Extension architecture       | Custom wrappers, context classes, factories          | Specialized logging behavior without rewriting the pipeline |

The important organizing principle is that these facilities are largely independent. An application can use structlog's event processing without adopting its native output system, or its native output system without introducing standard-library handlers.

## 2. Architectural model: bound logger, event dictionary, processor chain, backend

Structlog separates event production into three configurable components.

Application logging call

Event name, keyword attributes, bound context

Bound logger

Copies context, merges event fields, invokes processor chain

Ordered processor chain

Enrich

Transform

Render / adapt

Wrapped logger / output backend

PrintLogger, WriteLogger, BytesLogger, standard logging, or custom backend

### 2.1 Bound logger semantics

A bound logger contains:

1. A context dictionary associated with that logger.
2. A processor sequence applied to its events.
3. A wrapped logger that ultimately handles output.

Binding operations return new logger instances with new context mappings. `bind()` adds or replaces fields; `new()` establishes a fresh bound context; `unbind()` removes named fields, raising when a field is absent; and `try_unbind()` removes fields without requiring their presence.

The original bound logger's context mapping is not mutated. This permits a parent logger to provide common context while derived loggers carry specialized context. The copying is a mapping-level operation, not a promise to deep-copy mutable objects contained in context values.

`structlog.get_context(logger)` exposes the context for inspection. `structlog.typing.BindableLogger` provides a runtime-checkable protocol for the common binding interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 2.2 Event construction

Consider a logger with bound context:

```
log = structlog.get_logger("worker").bind(    subsystem="ingestion",    batch_id="b-104",)log.info(    "batch_completed",    rows=2500,    elapsed_ms=18.5,)
```

Before enrichment processors execute, the event dictionary is conceptually:

```
{    "subsystem": "ingestion",    "batch_id": "b-104",    "rows": 2500,    "elapsed_ms": 18.5,    "event": "batch_completed",}
```

The `event` key is special: it contains the event name/message supplied to the logging call. Per-call keyword fields override identically named fields in the copied bound context.

The event dictionary can contain Python values that are not JSON-serializable. Conversion is deferred until an appropriate processor or renderer handles them.

This is a consequential distinction from prematurely stringifying application data. A numeric duration remains numeric, and a nested dictionary remains a nested object until the selected serialization path changes that representation.

### 2.3 Processor execution contract

A processor is any callable implementing the conceptual signature:

```
def processor(logger, method_name, event_dict):    ...    return event_dict
```

The processor can inspect the wrapped logger, the invoked logging method, and the event dictionary.

Processors execute sequentially, receiving the previous processor's return value. The typical contract is dictionary-in/dictionary-out, but structlog does not require every intermediate value to remain a dictionary if subsequent processors understand it.

The final processor is different: it adapts the result into a representation the wrapped logger can accept. Documented terminal forms include strings, bytes, bytearrays, `(args, kwargs)` tuples, and keyword-argument dictionaries.

An intermediate processor can raise `structlog.DropEvent` to suppress the event without invoking the output backend.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



The architectural significance is that event semantics and delivery mechanics can be developed independently. A processor can enforce a diagnostic field policy without knowing whether the final event will be serialized as JSON or forwarded to a standard logging handler.

### 2.4 Configuration and initialization

`structlog.configure()` controls five primary choices.

| Configuration field         | Responsibility                            |
| --------------------------- | ----------------------------------------- |
| `processors`                | Ordered event-processing sequence         |
| `wrapper_class`             | Concrete bound logger implementation      |
| `context_class`             | Container used for bound context          |
| `logger_factory`            | Construction of the wrapped output logger |
| `cache_logger_on_first_use` | Whether to retain the assembled logger    |

The configuration is global to structlog within the process. `configure()` can update individual settings; `reset_defaults()` restores built-in defaults; `is_configured()` and `get_config()` expose configuration state.

`get_logger()` deliberately returns a lazy proxy so loggers may be declared at module import time before application configuration occurs.

There is an important lifecycle consequence: calling `bind()` or `new()` immediately at module import time can force logger initialization before configuration is finalized. Passing initial context through `get_logger(..., key=value)` preserves lazy initialization. Once caching is enabled, previously resolved logger instances are not automatically rebuilt when global configuration changes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 2.5 Built-in defaults versus production configurations

Structlog works without explicit initialization. In 26.1.0, its defaults combine:

- `merge_contextvars`
- `add_log_level`
- `StackInfoRenderer`
- `structlog.dev.set_exc_info`
- A local-time `TimeStamper`
- `ConsoleRenderer`

The default bound logger uses native logging methods with no level filtering, output goes through `PrintLoggerFactory` to standard output, and logger caching is disabled.

These defaults emphasize immediate usability and readable output. They do not imply JSON output or production-oriented filtering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



Sources:

`https://www.structlog.org/en/stable/bound-loggers.html`

`https://www.structlog.org/en/stable/processors.html`

`https://www.structlog.org/en/stable/configuration.html`

`https://www.structlog.org/en/stable/getting-started.html`

## 3. Context management and propagation

Structlog provides two complementary mechanisms for attaching metadata to events.

### 3.1 Explicit bound context

`bind()` is appropriate for attributes that are logically owned by a particular logger or component.

A derived logger can accumulate context over an operation's lifetime without requiring every logging call to repeat common attributes.

Binding remains explicit: downstream code must use that derived logger to inherit its fields. Independently obtained loggers do not acquire the context merely because another logger was bound elsewhere.

This makes bound context especially useful for stable information such as a subsystem, component identity, task identifier, or persistent processing parameters.

### 3.2 Execution-local context variables

The `structlog.contextvars` module supplies context shared by logging calls within the active Python execution context.

| API                        | Purpose                                                                   |
| -------------------------- | ------------------------------------------------------------------------- |
| `bind_contextvars()`       | Bind one or more execution-local values; return reset tokens              |
| `unbind_contextvars()`     | Remove selected execution-local bindings                                  |
| `clear_contextvars()`      | Clear structlog's execution-local bindings                                |
| `bound_contextvars()`      | Temporarily bind values within a context manager or decorator             |
| `reset_contextvars()`      | Restore previous values using returned tokens                             |
| `get_contextvars()`        | Inspect the current context-variable values                               |
| `get_merged_contextvars()` | Inspect the combination of context variables and a bound logger's context |
| `merge_contextvars()`      | Copy execution-local fields into an event dictionary                      |

`merge_contextvars()` ordinarily appears early in the processor chain so subsequent enrichment, filtering, and rendering operate on the completed contextual event.

This is useful for automatically including request IDs, execution IDs, or correlation metadata in log calls made by deeply nested functions.

The context is not a global mutable dictionary shared indiscriminately by all concurrent tasks. Structlog stores context values using Python's `contextvars` machinery, isolating bindings according to the active execution context.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 3.3 Reset tokens and scoped overrides

`bind_contextvars()` returns tokens that can restore earlier values through `reset_contextvars()`.

This is more precise than clearing all context after a nested operation. For example, a helper can temporarily override an operation identifier and then restore the caller's binding without losing unrelated context.

`bound_contextvars()` packages the temporary-binding pattern into a context manager/decorator and is useful when a diagnostic attribute should exist only during a defined scope.

### 3.4 Concurrency boundaries

The context propagation model needs to be distinguished by execution mechanism.

| Boundary                                            | Behavior and consideration                                              |
| --------------------------------------------------- | ----------------------------------------------------------------------- |
| Calls within the same synchronous execution context | Bound values are visible until changed or cleared                       |
| Ordinary asyncio task execution                     | Context variables work with asyncio's execution-context mechanisms      |
| New threads or executor work                        | Propagation depends on the mechanism used to transfer the context       |
| Hybrid sync/async frameworks                        | Context changes may not be visible in both directions                   |
| Independent processes                               | No automatic shared context; identifiers must be passed explicitly      |
| Network requests or RPC                             | Distributed correlation requires application or tracing instrumentation |

Structlog specifically documents context isolation problems in hybrid applications built around Starlette, including FastAPI. It does not guarantee that setting a variable inside synchronous middleware makes that variable visible in every asynchronous execution context, or vice versa.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



This is a significant distinction between execution-local metadata and distributed tracing. Structlog can store and emit trace identifiers, but it does not independently implement a distributed trace propagation protocol.

### 3.5 Legacy thread-local context

`structlog.threadlocal` was deprecated in version 22.1.0 in favor of `contextvars`.

The module remains present in 26.1.0 as a compatibility mechanism. The documentation explicitly notes that its planned removal was deferred because of reported context-variable issues that could not be reproduced.

It should therefore be distinguished from both current recommended functionality and already-removed functionality.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



Sources:

`https://www.structlog.org/en/stable/contextvars.html`

`https://www.structlog.org/en/stable/thread-local.html`

## 4. Processor families and event transformation

The processor pipeline is structlog's main extension surface. Built-in processors address several distinct families of problems, and a custom processor can implement any compatible transformation that is missing.

### 4.1 Built-in processor inventory

| Functional family         | Processor/API                                             | Capability                                                                     |
| ------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Context enrichment        | `contextvars.merge_contextvars`                           | Merge execution-local bindings into each event                                 |
| Severity                  | `add_log_level`                                           | Add the textual severity                                                       |
| Standard logging severity | `stdlib.add_log_level_number`                             | Add numeric levels compatible with Python logging conventions                  |
| Logger identity           | `stdlib.add_logger_name`                                  | Include the wrapped logger's name                                              |
| Time                      | `TimeStamper`                                             | Add timestamps using epoch, ISO, or custom formats                             |
| Time preservation         | `MaybeTimeStamper`                                        | Add a timestamp only if none is already present                                |
| Callsite metadata         | `CallsiteParameterAdder`                                  | Capture source file, line, function, thread, process, and related information  |
| Current stack             | `StackInfoRenderer`                                       | Capture stack information independently of exception handling                  |
| Exception conversion      | `ExceptionRenderer`, `format_exc_info`, `dict_tracebacks` | Produce string or structured exception representations                         |
| Exception side output     | `ExceptionPrettyPrinter`                                  | Print exception information separately and remove it from the event dictionary |
| Field naming              | `EventRenamer`                                            | Rename the special `event` field and optionally replace it                     |
| Encoding                  | `UnicodeDecoder`, `UnicodeEncoder`                        | Convert selected text/bytes values                                             |
| JSON serialization        | `JSONRenderer`                                            | Serialize events using a selectable JSON serializer                            |
| Logfmt serialization      | `LogfmtRenderer`                                          | Render key/value pairs using logfmt syntax                                     |
| Simple text serialization | `KeyValueRenderer`                                        | Render key/value pairs using Python representations                            |
| Development output        | `dev.ConsoleRenderer`                                     | Render formatted console records, including configurable columns               |
| Standard logging bridge   | `stdlib.ExtraAdder`, `PositionalArgumentsFormatter`       | Extract `LogRecord` extras or perform positional message formatting            |

These are distinct mechanisms, not a mandatory sequence. For example, `TimeStamper` overwrites its configured field, whereas `MaybeTimeStamper` preserves an existing value. This matters when events originating in another component already have authoritative timestamps.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation+2



### 4.2 Callsite introspection

`CallsiteParameterAdder` can extract:

- Source location: `FILENAME`, `PATHNAME`, `LINENO`, `MODULE`, `FUNC_NAME`.
- Execution identity: `THREAD`, `THREAD_NAME`, `PROCESS`, `PROCESS_NAME`.
- Qualified identity: `QUAL_NAME`, `QUAL_MODULE`.

`QUAL_NAME` includes qualified function or class scope information and requires Python 3.11+. `QUAL_MODULE`, added in structlog 26.1.0, identifies the fully qualified import name.

The two qualified identifiers apply to structlog-originated events; ordinary standard-library `LogRecord` objects do not contain equivalent information from which the processor can reliably reconstruct those values.

For native structlog records, the processor can inspect the call stack. For foreign logging records processed through `ProcessorFormatter`, it can instead reuse available `LogRecord` metadata. The `additional_ignores` option excludes specified wrapper-module prefixes when searching for the relevant caller.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation



This is useful for source-level diagnostics and for selecting events based on their origin. The tradeoff is additional stack inspection, which can be significant relative to inexpensive log events.

### 4.3 Filtering beyond global log levels

There are two very different filtering locations.

Bound-logger filtering occurs before event construction. `make_filtering_bound_logger()` generates logging methods for which disabled levels return immediately, making it an efficient mechanism for a fixed minimum severity.

Processor-based filtering occurs after an event dictionary exists. A processor can inspect any field, including severity, event type, subsystem, source location or operation metadata, and raise `DropEvent`.

The second approach permits far more expressive policies, including selective suppression, conditional event retention, and subsystem-specific severity thresholds. Its cost depends on how many earlier processors have already executed.

The appropriate distinction is not simply speed versus configurability. Filtering early can prevent expensive exception conversion or serialization, while field-dependent filtering may require those fields to be populated first. Processor ordering directly determines how much work is avoided.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation+1



### 4.4 JSON serialization and custom object handling

`JSONRenderer` delegates to a JSON serializer implementing a `json.dumps()`-compatible interface.

Its default serializer supports custom objects using a `__structlog__()` method when available, falling back to `repr()` for otherwise unsupported values.

Providing an explicit `default` argument changes that behavior: it disables the built-in `__structlog__` fallback in favor of the supplied serializer policy.

This is important because `repr()` is not necessarily a stable, complete, or semantically useful representation. An object's `repr()` may contain memory addresses, omit important fields, or reveal sensitive information. Custom serialization methods and processors can provide more controlled representations.

Structlog can also use alternative serializers including `orjson` and `msgspec`. Those libraries supply the serialization implementation; structlog supplies the event-processing framework and invokes them. A serializer returning bytes should be paired with an output backend that accepts bytes without additional encoding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation



### 4.5 Semantic normalization and event contracts

Custom processors can implement policies such as:

- Stable field renaming and canonical event names.
- Unit normalization and consistent numeric representations.
- Conversion of domain objects into structured values.
- Field allowlisting, suppression, masking and redaction.
- Correlation and provenance enrichment.
- Conditional event rejection based on content or context.

These are general capabilities enabled by processor composition; they are not equivalent to built-in schema validation.

Structlog does not independently enforce a declared domain schema for arbitrary event dictionaries. Validation against Pydantic models, JSON Schema, typed records or other domain contracts would require an additional processor or another integration.

That distinction matters when diagnostic events are consumed as durable structured data rather than treated as transient operational messages.

Sources:

`https://www.structlog.org/en/stable/processors.html`

`https://www.structlog.org/en/stable/api.html`

`https://www.structlog.org/en/stable/recipes.html`

## 5. Output backends and standard-library interoperability

Structlog's independence from Python's logging infrastructure is one of its most consequential architectural characteristics.

### 5.1 Native output backends

| Backend                              | Accepted output       | Principal distinction                                                          |
| ------------------------------------ | --------------------- | ------------------------------------------------------------------------------ |
| `PrintLogger` / `PrintLoggerFactory` | Text                  | Uses `print()` and is convenient for default development output                |
| `WriteLogger` / `WriteLoggerFactory` | Text                  | Writes a complete text event to a stream in one write operation, then flushes  |
| `BytesLogger` / `BytesLoggerFactory` | Bytes                 | Supports byte-producing serializers without an intermediate Unicode conversion |
| `stdlib.LoggerFactory`               | Adapted logging calls | Delegates routing, levels, handlers and output to Python `logging`             |
| Custom logger factory                | Backend-specific      | Adapts events to arbitrary compatible output implementations                   |

`PrintLogger` writes message content and newline separately, which can permit interleaving when another logger writes to the same stream. `WriteLogger` performs a single write of the record and newline, reducing this particular risk. It does not establish universal atomicity across arbitrary destinations or multiple processes.

`BytesLogger` is especially useful with serializers such as `orjson.dumps`, which return bytes. In 26.1.0 it has an optional `name` attribute that `stdlib.add_logger_name()` can recognize even without using the standard logging backend.

Version 26.1.0 also changes native file-output logger references to avoid retaining files unnecessarily when loggers are repeatedly created for short-lived outputs. This is resource-management behavior, distinct from adding a transport or persistent file-management system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation+2



### 5.2 Four interoperability patterns

The standard-library integration documentation describes four main choices.

| Pattern                                     | Final rendering occurs in                          | Main characteristic                                                                  |
| ------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Independent logging systems                 | Each system separately                             | Structlog and standard logging coexist without a shared formatter                    |
| Structlog rendering before standard logging | structlog                                          | Structlog emits completed strings to `logging.Logger`                                |
| Standard logging rendering                  | Standard logging formatters                        | Structlog passes message and event fields as logging arguments                       |
| `ProcessorFormatter` integration            | structlog processors invoked by logging formatters | Both structlog and foreign logging records share compatible processing and rendering |

These are materially different configurations. Using a standard-library logger as an output destination does not automatically imply that third-party logging events will be processed through structlog.

### 5.3 Rendering within structlog

This mode uses `structlog.stdlib.LoggerFactory()` as the output backend while keeping a renderer such as `JSONRenderer` at the end of the structlog processor chain.

A structlog event becomes a completed string before entering the standard logging infrastructure.

Advantages include a clear application-owned event schema and use of established logging handlers. The tradeoff is that ordinary third-party `logging` calls may still appear in a different format unless those loggers are configured separately.

This configuration does not automatically make all standard logging records structured.

### 5.4 Rendering within standard logging

`render_to_log_kwargs()` converts an event dictionary to `logging.Logger` keyword arguments. The `event` field becomes the logging message, while other event fields are passed via `extra`, apart from specially handled logging parameters.

`render_to_log_args_and_kwargs()`, added in version 25.1.0, additionally preserves positional arguments for the underlying standard logging API. This can avoid requiring `PositionalArgumentsFormatter` in certain configurations.

The important limitation is that the selected standard logging formatter must actually render the `extra` attributes. A simple formatter using only `%(message)s` will discard the visible structured context even though it was passed into the logging record.

Likewise, fields supplied as `extra` must obey Python logging's restrictions on reserved record attributes. Arbitrary application dictionaries are not identical to unrestricted `LogRecord` attributes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation+1



### 5.5 ProcessorFormatter: unified logging pipelines

`structlog.stdlib.ProcessorFormatter` provides a particularly powerful integration architecture.

It is a standard `logging.Formatter` that applies structlog processors to both structlog-originated events and ordinary `logging.LogRecord` objects.

There are three important processing paths:

1. The application's structlog processor chain prepares a structured event.
2. `ProcessorFormatter.wrap_for_formatter` transfers it to standard logging in the expected form.
3. `ProcessorFormatter` applies its rendering chain; foreign standard logging records first traverse `foreign_pre_chain`.

The `foreign_pre_chain` exists because a normal standard logging record did not previously pass through the structlog-side processors.

For example, the formatter can attach timestamps and levels to foreign logging records while avoiding redundant enrichment of structlog records that already have those fields.

`ProcessorFormatter` exposes `_record` and `_from_structlog` inside its event dictionary, allowing processors to inspect the original `LogRecord` and distinguish the two origins. `ProcessorFormatter.remove_processors_meta` removes those internal fields before final rendering.

Additional options include `keep_exc_info`, `keep_stack_info`, `pass_foreign_args`, and `use_get_message`. `ExtraAdder` can copy foreign `LogRecord.extra` attributes into the event dictionary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation+2



Two constraints are particularly important.

The terminal adapter is not interchangeable. A configuration using `ProcessorFormatter` must end its structlog-side processor chain with `ProcessorFormatter.wrap_for_formatter`, not `render_to_log_kwargs()` or `render_to_log_args_and_kwargs()`.

`DropEvent` is not safe in the formatter stage. The official API explicitly warns that raising `DropEvent` inside `ProcessorFormatter` can crash the application, because the formatter is executing within standard logging rather than structlog's normal event-suppression wrapper. Filtering should therefore occur in an appropriate earlier stage or through standard logging's filtering machinery.

These are consequential differences from the otherwise simple rule that a processor may raise `DropEvent`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation



### 5.6 Configuring standard logging remains a separate concern

Using `stdlib.LoggerFactory` does not replace Python logging's own configuration.

Logger hierarchy, thresholds, propagation, handlers, file rotation, asynchronous queue handlers, and formatter assignment are controlled by standard logging.

`structlog.stdlib.recreate_defaults()` offers a convenience path for adapting structlog's defaults to standard logging, but more sophisticated configurations still require understanding both systems.

This separation is often beneficial: Python libraries can retain their existing standard logging behavior, while structlog contributes contextual event processing and unified formatting. It also means that configuration ordering and duplicate handlers can materially affect output.

Source:

`https://www.structlog.org/en/stable/standard-library.html`

## 6. Exceptions, stack traces, and development diagnostics

### 6.1 Exception handling model

Structlog uses an `exc_info` event field to represent exception information.

The field can contain a conventional `sys.exc_info()` tuple, an exception instance, or a truthy flag indicating that the active exception should be captured.

`ExceptionRenderer` consumes that information and writes the converted result under the `exception` key.

The conversion is independently configurable:

| Mechanism                               | Result                                                                           |
| --------------------------------------- | -------------------------------------------------------------------------------- |
| `format_exc_info`                       | Conventional string traceback                                                    |
| `dict_tracebacks`                       | Structured, JSON-serializable exception data                                     |
| `ExceptionRenderer(custom_transformer)` | Custom exception representation                                                  |
| `ExceptionPrettyPrinter`                | Side-effecting readable exception output, removing exception data from the event |
| `dev.RichTracebackFormatter`            | Rich-based human-readable traceback                                              |
| `dev.plain_traceback`                   | Plain console traceback                                                          |

The important distinction is whether the exception remains inspectable as structured data, becomes a formatted string, or is presented separately from the main event.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 6.2 Structured traceback extraction

`structlog.tracebacks.ExceptionDictTransformer` converts exception information into structured dictionaries.

Its configurable facilities include frame limits, source suppression, local-variable capture, maximum local-value lengths, omission of specially named locals, and Rich-based representation generation.

The resulting model can represent exception types, messages, cause relationships, individual frames, source locations, and local values.

The implementation also supports Python exception groups, exception notes, and nested group structure in current releases. Support for exception groups was added in structlog 25.4.0, while other structured-exception enhancements arrived across 25.x.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation+1



### 6.3 Sensitive-data consequences

A non-obvious behavior is that `ExceptionDictTransformer` defaults to `show_locals=True`.

That is excellent for reconstructing failures but potentially hazardous for operational logging. Stack-local values may contain credentials, passwords, access tokens, personal data, or large objects.

The available controls include disabling locals entirely, limiting the length and size of captured representations, suppressing modules, and subclassing the transformer to remove selected values.

However, redacting a local variable does not guarantee that its value is absent from an exception message or another attribute. The documentation explicitly warns about this residual exposure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



Because structured traceback generation may inspect and render many frames and objects, it can also be substantially more expensive than logging a concise exception type and message.

### 6.4 ConsoleRenderer and configurable presentation

`structlog.dev.ConsoleRenderer` provides aligned, colored human-readable diagnostics and automatically integrates with Rich when installed.

Beyond basic color support, it offers:

- Configurable event, timestamp, and severity rendering.
- Custom column definitions and per-column formatter callables.
- Field suppression from the visible console output.
- Optional key ordering and sorting.
- Customizable exception rendering.
- Runtime access to the active renderer through `ConsoleRenderer.get_active()`.

The active renderer's properties became mutable in version 25.5.0, allowing diagnostic presentation to be changed without rebuilding the entire logging configuration.

This functionality has an important internal distinction: explicitly configured columns and the convenience properties represent different configuration approaches. Changing certain convenience properties can reconstruct the column configuration, overwriting previously supplied custom columns.

The default renderer honors `NO_COLOR` and `FORCE_COLOR`; `NO_COLOR` takes precedence. Rich and Colorama are separate optional dependencies for enhanced presentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation+1



For rich exception output, `format_exc_info` generally must not run before `ConsoleRenderer`, because it consumes the raw exception information that the Rich renderer would otherwise use.

Version 26.1.0 adds `rich_monochrome_traceback`, allowing Rich-based diagnostic formatting without requiring color. Support for `better-exceptions` is deprecated in that release, with Rich serving as the maintained alternative.

Sources:

`https://www.structlog.org/en/stable/exceptions.html`

`https://www.structlog.org/en/stable/console-output.html`

`https://www.structlog.org/en/stable/recipes.html`

## 7. Async execution and runtime behavior

Structlog's asynchronous logging capabilities are useful, but their implementation is sometimes misunderstood.

### 7.1 Synchronous logging is the default

A normal logging call such as `logger.info(...)` executes the processor chain and invokes the wrapped logger synchronously.

Consequently, expensive processors, JSON serialization, traceback extraction, and blocking output can all contribute to the calling thread's latency.

This is true even in an asyncio application: invoking an ordinary synchronous logging method from an async coroutine does not make the logging work asynchronous.

### 7.2 Async logging methods

Structlog's native filtering logger and standard-library bound logger expose asynchronous variants of conventional logging methods.

| Synchronous   | Asynchronous   |
| ------------- | -------------- |
| `info()`      | `ainfo()`      |
| `debug()`     | `adebug()`     |
| `warning()`   | `awarning()`   |
| `error()`     | `aerror()`     |
| `critical()`  | `acritical()`  |
| `exception()` | `aexception()` |
| `log()`       | `alog()`       |

The asynchronous methods offload synchronous processing and output to a thread-pool executor. They do not transform the processors or wrapped logger into intrinsically asynchronous implementations.

This provides a mechanism for avoiding synchronous logging work on the event-loop thread, but each logging operation incurs executor dispatch and scheduling costs.

Structlog copies execution context into the executor work so that context-variable values remain available. It also preserves originating callsite information for diagnostics. Version 26.1.0 fixes async thread metadata so it identifies the calling thread rather than the executor worker.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation+1



### 7.3 Deprecated AsyncBoundLogger

`structlog.stdlib.AsyncBoundLogger` is a different abstraction: its ordinary logging methods themselves are coroutines.

That design was deprecated in version 23.1.0. The supported approach is to use a regular bound logger and explicitly invoke asynchronous methods where appropriate.

This distinction matters because switching an entire logging API from synchronous to asynchronous methods changes every call site. The `a`-prefixed API allows synchronous and asynchronous logging to coexist.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation



### 7.4 Async tradeoffs

Async offloading does not guarantee nonblocking behavior at every layer or durable delivery. Work still executes synchronously in another thread, and its cost has not disappeared.

For inexpensive processor chains and fast output streams, direct synchronous logging can be more efficient overall. For potentially blocking destinations, async offloading can protect event-loop responsiveness.

Neither approach independently provides queue persistence, batching, backpressure control, retry semantics, or delivery acknowledgments.

Source:

`https://www.structlog.org/en/stable/standard-library.html`

## 8. Performance architecture

Structlog offers several independent optimization mechanisms.

The relevant question is not simply how quickly a logging method executes, but which work occurs before an event is rejected, what work is repeated on each call, and how much serialization and output overhead remains.

### 8.1 Principal optimization mechanisms

| Mechanism                              | Avoided or reduced work                                        | Tradeoff                                                              |
| -------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------- |
| Native `make_filtering_bound_logger()` | Event construction and processor execution for disabled levels | Fixed minimum severity for the constructed logger                     |
| `cache_logger_on_first_use=True`       | Repeated lazy-proxy logger assembly                            | Cached loggers do not observe subsequent configuration changes        |
| Binding a local logger once            | Repeated proxy resolution and binding overhead                 | The bound logger must be held and reused                              |
| `WriteLoggerFactory`                   | Some standard logging record/handler overhead                  | Less built-in routing infrastructure                                  |
| `BytesLoggerFactory`                   | Avoidable text-to-bytes conversions                            | Requires a bytes-compatible final renderer                            |
| Alternative JSON serializers           | Serialization CPU overhead                                     | Different supported types, error behavior, and output representations |
| Early processor filtering              | Expensive downstream enrichment or serialization               | Fields required for filtering must already be available               |
| Async logging methods                  | Synchronous logging work on the event-loop thread              | Executor dispatch and scheduling overhead                             |

The upstream performance guidance identifies these mechanisms and supplies an example using native filtering, logger caching, `orjson.dumps`, and `BytesLoggerFactory`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 8.2 Fixed versus dynamic severity filtering

`make_filtering_bound_logger(logging.INFO)` creates a logger class with disabled methods that return immediately.

This is highly efficient, but its severity threshold is effectively fixed when the logger class is created.

By contrast, `structlog.stdlib.filter_by_level` checks the underlying standard logger's current level. This permits dynamic severity configuration, including changes to standard logging thresholds at runtime.

Thus, static filtering and dynamic filtering are not interchangeable when runtime logging controls matter.

One further consideration is that filtering at the logger method avoids structlog's event construction, but it cannot prevent Python from evaluating function arguments before the logging method is called. Eagerly constructing large event objects can therefore remain expensive even when logging is disabled.

### 8.3 Serializer and output coupling

A JSON serializer's return type affects the appropriate output backend.

For example, the upstream performance documentation pairs `orjson.dumps`, which returns bytes, with `BytesLoggerFactory`.

Using a bytes serializer with a text-oriented pipeline may require unnecessary decoding. Using a string serializer with a bytes-only logger may require encoding.

The benefit comes from eliminating repeated conversions between stages, not from structlog implementing its own JSON engine.

Serialization also affects information preservation: custom serializers, object representations, timestamp formatting and exception conversion can change the eventual output schema.

### 8.4 Expensive enrichment

Callsite discovery, stack extraction, exception transformation, and arbitrary custom processors can be substantially more expensive than adding fields already available in memory.

The ordering of processors therefore has a practical effect on cost:

Cheap rejection → context enrichment → selective diagnostics → expensive transformation → final serialization

This is a conditional processing principle, not a required processor sequence. For example, a filter that depends on a callsite field must follow whichever processor creates that field.

For advanced diagnostics, output costs and object serialization may dominate the overhead of the bound logger itself. No universal performance ranking against alternative logging libraries follows from these mechanisms alone.

### 8.5 Deployment and multiprocessing considerations

Enabling `cache_logger_on_first_use` prevents already cached loggers from reflecting later configuration changes and makes the cached bound logger non-pickleable.

That matters in process-based execution systems that serialize objects containing loggers.

For concurrent output, one complete write per event reduces certain forms of interleaving. It does not provide cross-process ordering guarantees or a durable event queue.

Structlog's upstream operational guidance favors writing structured events to standard output and delegating collection, rotation and centralized storage to surrounding infrastructure. This can avoid duplicating capabilities already supplied by a process manager, container runtime, or logging service.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation+1



Sources:

`https://www.structlog.org/en/stable/performance.html`

`https://www.structlog.org/en/stable/logging-best-practices.html`

## 9. Extensibility, typing, and testing

### 9.1 Custom bound logger implementations

`structlog.BoundLoggerBase` provides reusable context-management behavior for specialized logger wrappers.

A subclass can define its own logging methods and use `_proxy_to_logger()` to run the configured processors and invoke a method on the wrapped logger.

`_process_event()` exposes the lower-level event-processing stage when more control is necessary.

The older generic `structlog.BoundLogger` also remains available and can dynamically proxy methods to arbitrary wrapped logging objects.

These extension points enable specialized event creation or logging APIs without implementing context copying, processor dispatch, or `DropEvent` handling independently.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 9.2 Custom wrapped logger factories

`wrap_logger()` can wrap a pre-existing logger directly and accepts local configuration options.

This differs from `get_logger()`, which normally obtains the underlying logger through the globally configured factory.

Direct wrapping is useful when another system owns logger creation or when a logging backend's interface differs from standard `logging.Logger`.

A custom logger factory can likewise return an arbitrary object exposing methods compatible with the selected bound logger and final processor.

The important contract is the output adaptation: a final processor must produce an argument representation understood by the wrapped logger.

This flexibility is a major mechanism for integrating with external logging infrastructure while preserving structlog's event-processing abstraction.

### 9.3 Static typing

Structlog has shipped type annotations across its APIs since version 20.2.0.

The primary challenge is that `structlog.get_logger()` can return different bound logger implementations according to configuration. Its general return type is therefore `Any`.

The package supplies `structlog.typing.BindableLogger` as a runtime-checkable protocol for common context-binding operations.

For standard logging integration, `structlog.stdlib.get_logger()` provides a more specifically typed interface. This function does not configure or verify that the application is actually using the standard logging backend; it is a typed façade over the general logger acquisition mechanism.

The native filtering logger similarly exposes a `FilteringBoundLogger` protocol.

The distinction is important in statically checked code: typing a logger as a specific wrapper class helps tools recognize its methods, but that annotation does not enforce the global runtime configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 9.4 Testing at different layers

Structlog provides several testing abstractions with distinct purposes.

| Facility                            | What it captures or verifies                          |
| ----------------------------------- | ----------------------------------------------------- |
| `testing.capture_logs()`            | Event dictionaries produced during a controlled scope |
| `testing.LogCapture`                | Events reaching a chosen capture processor            |
| `testing.CapturingLogger`           | Calls received by a wrapped logger                    |
| `testing.CapturingLoggerFactory`    | A convenient factory for captured backend calls       |
| `testing.ReturnLogger`              | Values and arguments returned by a minimal logger     |
| `reset_defaults()` / `get_config()` | Configuration state and restoration                   |

`capture_logs()` is particularly convenient for asserting event content without comparing rendered strings. As of version 25.5.0 it also accepts an explicit processor sequence to apply before capture.

There are two important limitations.

First, `capture_logs()` normally disables the configured processors. A test using it does not automatically verify final JSON, redaction, timestamps, or backend behavior. Explicit processors can be supplied when those transformations need to be included.

Second, the facility works by changing structlog configuration. Loggers previously cached with `cache_logger_on_first_use=True` may not participate, and concurrent use of global configuration changes can interfere with other logging operations.

`CapturingLoggerFactory` addresses a different problem: it can capture the actual calls received by an output backend after processing, including their method names and arguments. This permits more direct testing of the terminal processing contract.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 9.5 Consequential testing distinction

Logging behavior can be verified at several independent stages:

- The event emitted by application code.
- The event after context enrichment.
- The event after redaction and normalization.
- The serialized representation.
- The arguments passed to the output backend.

Passing an assertion at one stage does not prove correctness at another.

For example, verifying that an event dictionary contains a `request_id` does not establish that the final standard logging formatter includes it. Likewise, verifying JSON serialization does not establish that a handler successfully persisted or transported the record.

These distinctions matter when logging output is consumed by automated diagnostics rather than inspected only by humans.

Sources:

`https://www.structlog.org/en/stable/recipes.html`

`https://www.structlog.org/en/stable/typing.html`

`https://www.structlog.org/en/stable/testing.html`

## 10. Frameworks, tracing, and companion integrations

Structlog is intended to compose with existing Python frameworks and logging infrastructure rather than replace them.

### 10.1 Application framework integration

| Ecosystem | Integration mechanism                                                | Key boundary                                                                |
| --------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Flask     | Application initialization and request signals                       | Context must be established and cleared in the appropriate request scope    |
| Django    | Standard logging compatibility; `django-structlog` companion package | Request/task context support is provided substantially by the companion     |
| Litestar  | Framework-provided structlog integration                             | Configuration is controlled partly by the framework                         |
| Celery    | Wrapping task loggers; task signals for contextual metadata          | Multiprocessing and task execution require careful logging/context handling |
| Pyramid   | Application initialization and request tweens                        | Request-local metadata depends on middleware scope                          |
| Twisted   | `structlog.twisted` bound logger and adapters                        | Integration targets Twisted's legacy logging system                         |

The upstream documentation covers these integrations and identifies which are native, framework-provided, or supplied by another package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 10.2 Twisted support

Structlog includes a dedicated Twisted bound logger with `msg()` and `err()` methods, as well as adapters and JSON-oriented observer utilities.

However, its documented Twisted support targets the legacy `twisted.python.log` system, not the newer `twisted.logger` infrastructure.

The documentation also warns about duplicate traceback behavior under Python 3. These are material compatibility constraints, not merely missing convenience features.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 10.3 OpenTelemetry integration

Structlog does not create distributed traces itself, but its processors can consume OpenTelemetry's active span context.

The upstream documentation includes a processor using `opentelemetry.trace.get_current_span()` to attach fields such as:

- `trace_id`
- `span_id`
- `parent_span_id`

This enables events to be correlated with tracing information produced by OpenTelemetry instrumentation.

The separation remains important: attaching identifiers to a structlog event does not itself create a span, record its duration, propagate trace context to another service, or export telemetry through OTLP.

Those functions belong to OpenTelemetry's API, SDK, instrumentation, and exporter ecosystem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 10.4 Pydantic Logfire integration

Logfire supplies `logfire.StructlogProcessor()` as a companion integration.

Placed before structlog's final renderer, it forwards structured events to Logfire's observability system while allowing the existing processor pipeline and local output mechanism to remain in use.

The integration preserves event attributes and severity for Logfire analysis. It also has controls for avoiding duplicate console output.

The Logfire processor does not make the structlog core package dependent on Logfire. Its backend, tracing instrumentation, credentials, and telemetry transport remain separate responsibilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source:

`https://pydantic.dev/docs/logfire/integrations/logging/structlog/`

### 10.5 Elastic Common Schema integration

Elastic's `ecs-logging` package includes a `StructlogFormatter` that acts as a terminal processor.

It converts the structured event into ECS-compatible JSON, supplying standardized field organization and relevant enrichment.

This is a useful example of delegating domain-specific serialization conventions to an established adapter rather than implementing schema mapping in every application processor.

The ECS formatter provides schema-oriented rendering. It does not independently provide ingestion, storage, indexing or distributed tracing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS Logging Python



Source:

`https://www.elastic.co/docs/reference/ecs/logging/python/installation`

## 11. Architectural possibilities enabled by structlog

Several particularly valuable possibilities emerge from the interaction of structlog's capabilities.

### 11.1 Canonical diagnostic event processing

Bound context, execution-local context, enrichment processors, normalization rules and JSON rendering can combine into a single diagnostic event-generation pipeline.

This can replace repeated application-level handling of timestamps, identifiers, source metadata, exception serialization and output formatting.

The resulting design permits event producers to remain concerned primarily with what happened, while shared processors define how events are represented consistently.

This is an architectural possibility rather than a built-in canonical event schema: structlog supplies the composition infrastructure, and the schema must still be defined.

### 11.2 A shared diagnostic processing layer for third-party libraries

`ProcessorFormatter` can apply common event enrichment and rendering to ordinary standard logging records and native structlog events.

That permits heterogeneous Python libraries to participate in a common output convention without replacing their logging APIs.

The value is especially significant for mature applications with dependencies that already produce extensive standard logging output.

The tradeoff is that foreign logging records do not necessarily carry the same structured attributes or semantic event conventions as native structlog events. Common formatting does not establish equal diagnostic completeness.

### 11.3 Machine-readable failure diagnostics

`dict_tracebacks`, callsite enrichment, bound identifiers, and structured output can produce failure events that retain substantially more machine-interpretable information than a flat traceback string.

Such output can support automated grouping, filtering, programmatic inspection and correlation with other application events.

It can also reduce the need for bespoke exception-parsing code downstream.

The principal constraints are serialization cost, sensitive data capture, event volume, and the absence of automatic durable retention.

### 11.4 Context-rich canonical log lines

The upstream best-practices documentation discusses canonical log lines: accumulating context throughout an operation and emitting a small number of information-rich records rather than many fragmented messages.

Structlog's incremental context binding and execution-local metadata support this pattern naturally.

It can simplify the later analysis of operations because relevant attributes arrive together in one event. However, minimizing event count is not equivalent to preserving a complete execution history. When timing, nesting and causal transitions matter, traces or more granular events may still be necessary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



### 11.5 Independent local diagnostics and centralized telemetry

A shared semantic processing chain can feed different terminal representations.

For example, the same event enrichment and normalization processors may precede `ConsoleRenderer` during development and `JSONRenderer` in production. Alternatively, `ProcessorFormatter` can support different standard logging formatters across handlers.

This permits differences in presentation without requiring every application call site to know the destination.

Care is necessary when different output paths have different data-retention policies. Rendering a secret differently is not the same as removing it from all destinations. Common redaction should occur before the data is copied or forwarded to sinks that must not receive it.

## 12. Important limitations and decisions

Structlog's flexibility does not eliminate the responsibilities of a logging architecture.

| Concern          | What structlog provides                                              | What remains outside its guarantees                                     |
| ---------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Structured data  | Event dictionaries and processors                                    | Automatic schema validation and semantic consistency                    |
| Context          | Bound fields and execution-local variables                           | Automatic remote propagation across processes/services                  |
| Diagnostics      | Stack and exception representations                                  | Complete crash reporting, failure collection, or incident management    |
| Output           | Native streams and standard logging adapters                         | Durable queuing, retries, and delivery acknowledgments                  |
| Concurrency      | Async offloading and context propagation within supported boundaries | Universal nonblocking I/O and cross-process ordering                    |
| Performance      | Early filtering, caching, fast serialization paths                   | Guaranteed throughput or latency for arbitrary pipelines                |
| Testing          | Event and backend-call capture                                       | Automatic verification of transport and downstream ingestion            |
| Interoperability | Logging adapters and processor extension points                      | Automatic OpenTelemetry instrumentation or standardized trace semantics |

### Version-sensitive and deprecated functionality

For implementations targeting 26.1.0, the most relevant compatibility details are:

- Python 3.10 is the minimum supported interpreter.
- `structlog.threadlocal` remains present but deprecated.
- `structlog.stdlib.AsyncBoundLogger` is deprecated; `a`-prefixed methods are the supported async interface.
- `better-exceptions` integration is deprecated in favor of Rich-based exception rendering.
- `render_to_log_args_and_kwargs()` is available from 25.1.0 onward.
- `ConsoleRenderer.get_active()` and mutable renderer properties are available from 25.5.0 onward.
- `CallsiteParameter.QUAL_NAME` requires Python 3.11+; `QUAL_MODULE` was added in 26.1.0.
- Python exception-group support is available in structured traceback extraction.
- Python 3.15 lazy-import changes described under Unreleased are not established features of the 26.1.0 release.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

  GitHub+2



### Overall assessment

Structlog's distinctive strength is the combination of a small event-processing abstraction, flexible context management, backend independence, and interoperability with Python's existing logging ecosystem.

It is particularly capable when diagnostic events should remain structured and programmable throughout their lifecycle, rather than becoming formatted strings near the point of emission.

Its most valuable advanced features are the processor abstraction itself; the ability to unify foreign and native logging with `ProcessorFormatter`; native filtering that avoids constructing discarded events; structured exception extraction; composable context-variable enrichment; and interchangeable output backends.

The largest functionality outside its native scope is causal execution tracing, metrics, telemetry transport guarantees, and centralized observability analysis. These are better understood as complementary responsibilities that can be delegated to existing libraries and infrastructure, rather than functionality structlog necessarily ought to implement itself.

The result is a logging library that can remain comparatively small at the application-facing API while supporting sophisticated diagnostic processing and integration architectures.

## 13. Primary source map

The following are the main authoritative entry points for further technical investigation. All URLs are provided in plain text.

| Topic                         | Direct source                                                     |
| ----------------------------- | ----------------------------------------------------------------- |
| Release information           | `https://github.com/hynek/structlog/releases/tag/26.1.0`          |
| Full version history          | `https://github.com/hynek/structlog/blob/main/CHANGELOG.md`       |
| Complete API                  | `https://www.structlog.org/en/stable/api.html`                    |
| Bound loggers                 | `https://www.structlog.org/en/stable/bound-loggers.html`          |
| Configuration                 | `https://www.structlog.org/en/stable/configuration.html`          |
| Processor composition         | `https://www.structlog.org/en/stable/processors.html`             |
| Context variables             | `https://www.structlog.org/en/stable/contextvars.html`            |
| Structured exceptions         | `https://www.structlog.org/en/stable/exceptions.html`             |
| Console customization         | `https://www.structlog.org/en/stable/console-output.html`         |
| Standard logging integration  | `https://www.structlog.org/en/stable/standard-library.html`       |
| Testing                       | `https://www.structlog.org/en/stable/testing.html`                |
| Static typing                 | `https://www.structlog.org/en/stable/typing.html`                 |
| Advanced recipes              | `https://www.structlog.org/en/stable/recipes.html`                |
| Framework integrations        | `https://www.structlog.org/en/stable/frameworks.html`             |
| Performance                   | `https://www.structlog.org/en/stable/performance.html`            |
| Operational logging practices | `https://www.structlog.org/en/stable/logging-best-practices.html` |
| Tagged upstream source        | `https://github.com/hynek/structlog/tree/26.1.0`                  |

This reference is based on the published structlog 26.1.0 documentation, release notes, API reference, and official companion-integration documentation. Illustrative examples were not executed, and no independent performance measurements were conducted.