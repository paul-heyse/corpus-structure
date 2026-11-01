# ecs-logging — Python Library Capability Reference

Version 2.3.0 · Research date: October 31, 2026 · Elastic Common Schema (ECS) logging

## 1. Executive overview

`ecs-logging` is Elastic's Python library for converting application logs into structured JSON following the Elastic Common Schema (ECS). It integrates with Python's standard `logging` module and the `structlog` ecosystem, allowing existing logging infrastructure to produce consistently structured, machine-readable events.

Its distinctive value is not simply JSON serialization. It provides a common event representation that combines logging metadata, structured application context, exception diagnostics, process identity, and distributed-tracing correlation, using field conventions understood by the Elastic observability ecosystem.

### Version and compatibility

| Property                 | Verified status                                                 |
| ------------------------ | --------------------------------------------------------------- |
| Latest stable version    | 2.3.0, released January 19, 2026                                |
| Python support           | 3.8–3.14                                                        |
| Implemented ECS version  | 1.6, distinct from the package version                          |
| Integration interfaces   | `logging.Formatter`, `structlog` processor                      |
| Distribution             | Pure Python, platform-independent wheel                         |
| License                  | Apache-2.0                                                      |
| Primary dependency model | Python standard library; `structlog` is an optional integration |
| Recent additions         | Unicode serialization control, Python 3.13/3.14 support         |
| Installation             | `uv add ecs-logging` or `pip install ecs-logging`               |

Version 2.3.0 is the latest published release identified on PyPI and GitHub. The library's ECS schema target remains 1.6 even though newer ECS schema versions exist. That distinction matters for field compatibility and downstream data modeling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Official sources:

- Release and package metadata: `https://pypi.org/project/ecs-logging/`
- Upstream repository: `https://github.com/elastic/ecs-logging-python`
- Release history: `https://github.com/elastic/ecs-logging-python/blob/main/CHANGELOG.md`
- Elastic documentation: `https://www.elastic.co/docs/reference/ecs/logging/python`

### Capability map

| Capability family            | Native mechanisms                                                    | Principal value                                                                                            |
| ---------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Standard logging integration | `StdlibFormatter`                                                    | Convert ordinary Python `LogRecord` objects into ECS JSON without replacing logging infrastructure         |
| Structured event integration | `StructlogFormatter`                                                 | Preserve and normalize structured event context within `structlog` pipelines                               |
| Automatic enrichment         | Record metadata and exception extraction                             | Standardize timestamps, severity, logger identity, source location, process/thread information, and errors |
| Contextual enrichment        | `extra`, nested dictionaries, dotted fields, bound structlog context | Associate application/domain data with events                                                              |
| Trace correlation            | Elastic APM field mappings                                           | Connect logs to distributed transactions, spans, and traces                                                |
| Output control               | Field exclusion, stack limits, Unicode handling                      | Control emitted information and diagnostic volume                                                          |
| Extensibility                | `format_to_ecs`, serializer customization, logging/structlog hooks   | Adapt event representation without replacing the logging framework                                         |
| Ecosystem integration        | Filebeat, Elastic Agent, Elasticsearch, Kibana                       | Produce structured events for independent collection, indexing, and investigation                          |

### Architectural position

Application instrumentation

logging calls · structured events · contextual metadata · exceptions

Python logging

LogRecord → StdlibFormatter

structlog

Event dictionary → StructlogFormatter

ECS-compatible JSON events

Standard metadata · domain context · errors · correlation identifiers

Independent transport and collection

Stream / file / logging handler → collector → search and observability platform

The central boundary is important: `ecs-logging` is an event formatter, not a log transport, logging runtime, tracing agent, or observability backend.

It delegates log filtering, handler lifecycles, concurrency, buffering, delivery, and stream management to Python logging or adjacent infrastructure. Distributed-tracing context comes from instrumentation such as Elastic APM; log collection and indexing are separate concerns.

This separation permits ECS formatting to be introduced without requiring an application to adopt an entirely new logging API or delivery system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS Logging Python+2



## 2. Standard-library logging integration

`ecs_logging.StdlibFormatter` subclasses `logging.Formatter`, making ECS serialization available wherever Python's logging system accepts a formatter.

It accepts ordinary `logging.LogRecord` objects and constructs the ECS event through `format_to_ecs(record)`, before producing JSON through `format(record)`.

### 2.1 Automatic field extraction

The formatter maps standard record attributes into ECS fields.

| ECS field              | Python source                            | Behavior                                             |
| ---------------------- | ---------------------------------------- | ---------------------------------------------------- |
| `@timestamp`           | `record.created`, `record.msecs`         | UTC timestamp with millisecond precision             |
| `log.level`            | `record.levelname`                       | Lowercase level name                                 |
| `message`              | `record.getMessage()`                    | Rendered log message, with `%` interpolation applied |
| `log.original`         | `record.getMessage()`                    | Retains the original rendered message                |
| `log.logger`           | `record.name`                            | Logger identity                                      |
| `log.origin.function`  | `record.funcName`                        | Calling function                                     |
| `log.origin.file.name` | `record.filename`                        | Calling source filename                              |
| `log.origin.file.line` | `record.lineno`                          | Source line number                                   |
| `process.pid`          | `record.process`                         | Process identifier                                   |
| `process.name`         | `record.processName`                     | Process name                                         |
| `process.thread.id`    | `record.thread`                          | Thread identifier                                    |
| `process.thread.name`  | `record.threadName`                      | Thread name                                          |
| `error.type`           | `record.exc_info`                        | Exception class name                                 |
| `error.message`        | `record.exc_info`                        | Exception string representation                      |
| `error.stack_trace`    | `record.exc_info` or `record.stack_info` | Formatted traceback or captured stack                |
| `ecs.version`          | Library constant                         | ECS schema version, presently `1.6.0`                |

Fields with `None` values are generally omitted. False and zero values are not automatically discarded.

This is an important distinction from generic JSON logging: source location, execution identity, and error metadata can be captured from the existing logging runtime rather than manually supplied with every event.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



Source: `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_stdlib.py`

### 2.2 Structured application context

Python's existing `extra` mechanism provides application-level enrichment:

```
logger.info(    "request completed",    extra={        "service.name": "orders-api",        "http.request.method": "POST",        "http.response.status_code": 201,        "event.duration": 12_500_000,        "labels.operation": "create_order",    },)
```

The formatter combines generated metadata with fields explicitly supplied through the record.

The important capabilities are:

- Arbitrary structured context: Additional fields need not be predefined by the formatter.
- Nested dictionaries: An `http` dictionary containing `request` and `response` objects can be supplied directly.
- Dotted field notation: Keys such as `http.request.method` are expanded into nested dictionaries.
- Typed JSON values: Numeric, boolean, array, and object values can survive serialization when they are JSON-compatible.
- Reusable context: The formatter's constructor-level `extra` argument adds metadata to every record using that formatter.

For example, both of these represent the same intended ECS field:

```
{"http.request.method": "POST"}{"http": {"request": {"method": "POST"}}}
```

The result can be an event with a nested `http.request.method` structure without the application implementing its own recursive field conversion.

Important limitation: There is no unrestricted overwrite policy. The internal merge machinery raises exceptions for incompatible or duplicate nonempty values. Applications cannot assume that constructor-level context, record-level context, and automatically generated fields will silently override one another.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 2.3 Configuration controls

The important `StdlibFormatter` constructor arguments are:

| Option                                | Default                          | Function                                                               |
| ------------------------------------- | -------------------------------- | ---------------------------------------------------------------------- |
| `extra`                               | `None`                           | Fields attached to every formatted record                              |
| `exclude_fields`                      | `()`                             | Suppress individual ECS fields or whole prefixes                       |
| `stack_trace_limit`                   | `None`                           | Limit exception traceback frames                                       |
| `ensure_ascii`                        | `True`                           | Escape or preserve non-ASCII characters in JSON                        |
| `fmt`, `datefmt`, `style`, `validate` | Standard formatter compatibility | Retain compatibility with applications configuring `logging.Formatter` |

For example:

```
formatter = ecs_logging.StdlibFormatter(    extra={"service.name": "orders-api"},    exclude_fields=[        "process.thread",        "log.origin",        "log.original",    ],    stack_trace_limit=-5,    ensure_ascii=False,)
```

Field-prefix exclusion is useful because it operates on ECS field paths. Excluding `log.origin` suppresses the source-location family without listing individual subfields. Excluding `process` suppresses the broader process family.

This allows output volume and information exposure to be controlled without changing the original logging calls. The mechanism is particularly valuable where some diagnostic fields are expensive to store, unnecessary to downstream consumers, or inappropriate to expose.

`stack_trace_limit` has three materially different behaviors: positive values keep the first N traceback frames, negative values keep the last N frames closest to the error, and zero suppresses exception-derived traceback frames. It does not impose the same restriction on preformatted `LogRecord.stack_info`. Consequently, setting zero is not equivalent to guaranteeing that every possible stack capture is removed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS Logging Python+2



### 2.4 Integration with the logging runtime

Because it is a standard formatter, `StdlibFormatter` composes with existing Python logging facilities:

- Hierarchical logger names, propagation, handlers, and severity filtering.
- `dictConfig` and framework logging configuration, including common Django/Gunicorn-style formatter construction.
- `LoggerAdapter`, filters, and custom `LogRecord` factories for contextual enrichment.
- `StreamHandler`, `FileHandler`, rotating handlers, and queue-based logging architectures.

These facilities belong to Python's logging system, not to `ecs-logging`. Their behavior is preserved rather than reimplemented.

The `fmt`, `datefmt`, and `style` compatibility arguments should not be confused with ECS-output templates. The formatter constructs its own JSON representation and does not interpret `fmt` as a configurable ECS message layout.

An important semantic distinction is that standard logging renders `record.msg` and `record.args` into a message string. It does not automatically preserve every original interpolation argument as a separate typed ECS field. When those arguments matter independently, structured `extra` data provides the necessary representation.

## 3. `structlog` integration

`ecs_logging.StructlogFormatter` is a terminal processor for structlog. It receives a structured event dictionary, normalizes it, enriches it with ECS fields, and serializes it.

Unlike the standard-library formatter, it operates directly on structured application events rather than extracting most context from a `LogRecord`.

### 3.1 Processor model

The principal interface is:

```
__call__(logger, method_name, event_dict) -> str
```

The formatter performs the following sequence:

1. Moves the structlog `event` value into ECS `message`, converting it to a string.
2. Normalizes dotted dictionary keys into nested objects.
3. Populates `log.level` from the logging method name if not already present.
4. Adds `@timestamp` when absent.
5. Converts an `exception` field into `error.stack_trace`.
6. Adds the ECS version marker.
7. Serializes the resulting event dictionary to JSON.

It is the final processor because its return value is a serialized string, not another event dictionary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Source: `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_structlog.py`

### 3.2 Composition with upstream processors

The architectural benefit of this integration is that context generation and ECS serialization remain independent.

An illustrative pipeline is:

```
import structlogimport ecs_loggingstructlog.configure(    processors=[        structlog.contextvars.merge_contextvars,        structlog.processors.format_exc_info,        ecs_logging.StructlogFormatter(ensure_ascii=False),    ],    logger_factory=structlog.PrintLoggerFactory(),)log = structlog.get_logger().bind(    **{"service.name": "orders-api"})log.info(    "order created",    order_id="A123",    **{"event.action": "order_created"},)
```

This example is illustrative, not an executed integration test.

The three processors have distinct responsibilities:

| Layer                | Responsibility                                                       |
| -------------------- | -------------------------------------------------------------------- |
| `merge_contextvars`  | Add context previously associated with the current execution context |
| `format_exc_info`    | Convert exception information into a printable traceback field       |
| `StructlogFormatter` | Normalize event fields, apply ECS conventions, and serialize         |

The first two processors are provided by `structlog`, not by `ecs-logging`.

This separation is consequential for asynchronous execution. Context variables can attach request, task, or transaction metadata without explicitly passing those identifiers through every intermediate function. The formatter simply receives the resulting event dictionary.

Additional upstream processors can compute fields, sanitize sensitive values, rename keys, populate logger identifiers, or normalize types. A custom ECS-specific event-building framework is not necessary for those operations.

The principal caveat is that processor ordering is semantically significant: enrichment and transformation must generally occur before terminal serialization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation+1



Structlog processor reference: `https://www.structlog.org/en/stable/processors.html`

### 3.3 Differences from `StdlibFormatter`

| Dimension              | `StdlibFormatter`                                    | `StructlogFormatter`                                      |
| ---------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| Input                  | `logging.LogRecord`                                  | Structured event dictionary                               |
| Execution point        | Handler formatting                                   | Terminal structlog processor                              |
| Log message            | `record.getMessage()`                                | String conversion of `event`                              |
| Source-location fields | Automatically extracted                              | Supplied by earlier processors or context                 |
| Process/thread fields  | Automatically extracted                              | Not automatically populated                               |
| Exceptions             | Extracted from `exc_info` / `stack_info`             | Existing `exception` field moved into `error.stack_trace` |
| Static global context  | Constructor `extra`                                  | Structlog binding/context processors                      |
| Field exclusions       | Built-in `exclude_fields`                            | Implement through upstream processors                     |
| Traceback limits       | Built-in `stack_trace_limit`                         | Configure upstream exception processing                   |
| JSON customization     | Override `format()` or use its serialization helpers | Override `_json_dumps()`                                  |
| ECS customization      | Override `format_to_ecs()`                           | Override `format_to_ecs()`                                |

Two consequences deserve particular attention.

First, the structlog formatter does not automatically reproduce all the diagnostic metadata supplied by `StdlibFormatter`. If logger name, caller function, process identity, or thread information is required, those attributes must be provided by other processors or event context.

Second, the source uses `method_name.lower()` for level enrichment. It does not implement a comprehensive normalization layer for alternative logging method names. Existing event values and processor conventions therefore matter when exact severity terminology is required.

### 3.4 Structlog exception representation

`StructlogFormatter` recognizes a preexisting `exception` event field, moving its value to `error.stack_trace`.

It does not independently reconstruct `error.type` and `error.message` from arbitrary structlog exception objects. Nor does it automatically transform every possible `exc_info` representation into a valid ECS traceback string.

For conventional text tracebacks, an upstream `structlog.processors.format_exc_info` processor can perform that conversion.

For `dict_tracebacks` or other structured exception processors, the resulting payload may be a dictionary or list rather than the string expected by the ECS `error.stack_trace` field. The formatter does not perform comprehensive ECS datatype validation. That is a meaningful integration distinction, not merely a formatting preference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 4. JSON serialization and field-normalization semantics

The internal serialization machinery is a significant part of the library's behavior. It affects schema compatibility, data retention, error handling, and event interpretation.

The relevant helpers are implemented in `ecs_logging._utils`:

| Function               | Responsibility                                                             |
| ---------------------- | -------------------------------------------------------------------------- |
| `flatten_dict`         | Convert nested mappings into dotted field paths                            |
| `de_dot`               | Convert a dotted path and value into a nested dictionary                   |
| `normalize_dict`       | Recursively expand dotted field names, including dictionaries inside lists |
| `merge_dicts`          | Merge nested structures and reject incompatible field collisions           |
| `json_dumps`           | Produce ECS-oriented JSON with deliberate field ordering                   |
| `_json_dumps_fallback` | Handle values unsupported by standard JSON serialization                   |

Source: `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_utils.py`

### 4.1 Deliberate output ordering

The serializer specifically places three properties first when present:

1. `@timestamp`
2. `log.level`
3. `message`

Other properties are serialized using sorted keys and compact JSON separators.

This produces stable, relatively compact output and makes the most important event information visible first when reading raw log lines.

A particularly important detail is that `json_dumps` can extract `log.level` from a nested `log` dictionary and serialize it as a top-level dotted key, while leaving other `log` properties nested.

Consequently, output can mix flat dotted keys and nested JSON objects. This is intentional rather than an accidental inconsistency.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 4.2 The `ecs.version` compatibility detail

Version 2.2.0 introduced a specific correction: the automatically emitted `ecs.version` field is no longer expanded into a nested object.

The current implementation uses the literal top-level property:

```
{"ecs.version": "1.6.0"}
```

rather than automatically producing:

```
{"ecs": {"version": "1.6.0"}}
```

This matters because some Elastic documentation examples still illustrate the latter form. The 2.3.0 source and the 2.2.0 changelog establish the actual default formatter behavior.

The larger implication is that serialized JSON shape and the indexed Elasticsearch field path must be treated as related but distinct concerns. A collector's dotted-key expansion settings can change the JSON structure presented downstream.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 4.3 Dictionary collision semantics

Normalization is not a generic last-write-wins merge.

For example:

```
{    "tls": "enabled",    "tls.cipher": "AES256",}
```

These representations conflict structurally: `tls` cannot simultaneously be a scalar value and an object containing `cipher`.

The merge logic raises `TypeError` rather than silently destroying one representation.

Similarly, a mapping containing both an existing nested value and an equivalent dotted path can produce a duplicate-field conflict.

This behavior improves visibility into ambiguous event structures, but it also creates a failure mode for uncontrolled combinations of logging enrichers. Field ownership and naming conventions matter when several independent libraries contribute context.

The implementation does not perform a comprehensive ECS schema validation pass. It checks structural consistency during merging, not whether every supplied ECS field has the correct semantic meaning or Elasticsearch datatype.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.4 Serialization of non-JSON-native objects

For values that Python's `json.dumps()` cannot serialize directly, the library uses a fallback:

1. If the object exposes `__structlog__()`, use that representation.
2. Otherwise, use `repr(value)`.

This makes the formatter tolerant of many custom application objects without requiring a specialized encoder for every type.

However, there are three limitations:

- `repr()` is not guaranteed to preserve a value's original structured type.
- Custom object representations can contain sensitive information or unexpectedly large amounts of text.
- A serializable Python value is not necessarily valid for its intended ECS field.

Thus, the fallback is primarily a resilience and convenience mechanism, not a typed serialization contract.

The `StructlogFormatter._json_dumps()` method is an explicit customization point introduced in 2.2.0. Subclasses can replace the serialization strategy, although doing so also makes the subclass responsible for preserving any desired ordering, escaping, and compatibility behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 4.5 Mutation and event lifetime

The serialization helpers are not purely functional transformations.

In particular:

- `normalize_dict()` mutates dictionaries and processes lists in place.
- The structlog formatter consumes the original `event` field.
- `json_dumps()` removes certain fields from its input dictionary while constructing the final output.

This is compatible with their use as terminal formatting operations. It is less suitable when an application expects to reuse the same mutable dictionary after serialization.

A shared event object being processed through multiple destinations should therefore not be assumed to remain unchanged.

### 4.6 Timestamp semantics

Both integrations generate UTC timestamps at millisecond resolution, but their reference points differ.

`StdlibFormatter` uses the `LogRecord` timestamp, which ordinarily reflects when Python created the record.

`StructlogFormatter` generates a timestamp when its formatting processor executes, unless the event already contains `@timestamp`.

This distinction can matter when event processing is deferred, buffered, or performed after a queue. The time at which an event occurred and the time at which its JSON representation was constructed need not be identical.

An upstream `@timestamp` supplied to `StructlogFormatter` is retained rather than automatically converted into the library's preferred timestamp representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 5. Distributed tracing and Elastic APM correlation

One of the most consequential integrations is automatic correlation between logs and distributed traces.

The formatter does not create spans or manage trace propagation. Instead, it consumes identifiers injected by the Elastic APM Python agent.

### 5.1 Automatic field mapping

For standard-library records, the following attributes are recognized:

| Elastic APM record attribute     | ECS output field      |
| -------------------------------- | --------------------- |
| `elasticapm_trace_id`            | `trace.id`            |
| `elasticapm_transaction_id`      | `transaction.id`      |
| `elasticapm_span_id`             | `span.id`             |
| `elasticapm_service_name`        | `service.name`        |
| `elasticapm_service_environment` | `service.environment` |

The formatter also suppresses flattened `elasticapm_labels.*` fields from its output.

Elastic APM's logging integration decorates Python's `LogRecord` factory so these identifiers can be added automatically to log records created during instrumented execution.

When translated into ECS fields, the identifiers allow logs from different functions, modules, and services to be associated with the same distributed request or trace.

Precedence: The source uses `setdefault` when mapping APM identifiers, allowing existing explicit ECS values to take precedence over corresponding agent-derived values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 5.2 Correlation in structlog

The integration boundary differs for `structlog`.

Elastic APM provides the separate processor:

`elasticapm.handlers.structlog.structlog_processor`

That processor adds trace, transaction, and span identifiers to structured events. `StructlogFormatter` then serializes the resulting event as ECS JSON.

The two responsibilities compose as follows:

Elastic APM instrumentation

Active trace, transaction, and span context

APM structlog processor

Injects correlation identifiers into the event dictionary

`StructlogFormatter`

Emits ECS-compatible fields including `trace.id`, `transaction.id`, and `span.id`

The trace identifiers are not inherently Elastic-specific in meaning, but this formatter's automatic record-attribute mapping specifically targets Elastic APM's conventions. Other tracing frameworks can provide equivalent ECS fields through ordinary `extra` data, logging filters, context processors, or formatter customization.

Source: `https://www.elastic.co/docs/reference/apm/agents/python/logs`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

APM Python agent



### 5.3 APM-managed log reformatting

The Elastic APM agent also provides `log_ecs_reformatting`, controlled through the `LOG_ECS_REFORMATTING` configuration setting or its environment-variable equivalent, `ELASTIC_APM_LOG_ECS_REFORMATTING`.

The documented modes are `off` and `override`.

Under `override`, the agent can replace formatters attached to the root logger and replace configured structlog processors with ECS formatting machinery.

This is an agent capability, not a feature implemented inside `ecs-logging` itself.

Elastic labels it experimental/technical preview and explicitly warns that overriding existing processors can have unintended side effects. It can also remove application-specific enrichment and processing behavior.

The APM documentation describes version-dependent dependency handling, including changes introduced in agent version 6.16.0. This should not be mistaken for a new feature introduced by `ecs-logging` 2.3.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

APM Python agent+1



## 6. ECS schema and ingestion integration

### 6.1 ECS is a common vocabulary, not merely a JSON layout

ECS defines field names, types, meanings, and organizational conventions across application logs, system events, network telemetry, and other observability records.

The currently published ECS documentation describes schema version 9.5.0, while this Python formatter identifies its emitted schema as 1.6.0.

The formatter's default fields are therefore not a claim of complete conformance with every newer ECS definition. Custom fields and downstream mappings require independent semantic compatibility checks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

Elastic Common Schema (ECS)+1



For application events, the following field families are particularly useful:

| Field family                         | Representative fields                                          | Information modeled                      |
| ------------------------------------ | -------------------------------------------------------------- | ---------------------------------------- |
| `service.*`                          | `name`, `version`, `environment`, `node.name`                  | Application or deployed service identity |
| `event.*`                            | `action`, `category`, `type`, `outcome`, `duration`, `dataset` | Semantic description of an event         |
| `trace.*`, `transaction.*`, `span.*` | `id`                                                           | Distributed execution correlation        |
| `http.*`                             | `request.method`, `response.status_code`                       | HTTP request/response information        |
| `url.*`                              | `original`, `path`, `domain`, `scheme`                         | URL context                              |
| `user.*`                             | `id`, `name`                                                   | User or actor identity                   |
| `labels.*`                           | Application-defined scalar fields                              | Simple supplementary context             |
| `error.*`                            | `type`, `message`, `stack_trace`                               | Exception diagnostics                    |

These are primarily ECS schema capabilities, not automatically generated data from the Python formatter.

For example, `event.action` can identify a business operation such as an order being created, while `log.level` expresses the severity of the logging call. The two describe different dimensions and can support independent filtering and analysis.

Elastic recommends using existing ECS fields where they fit, `labels.*` for uncomplicated custom values, and namespaced custom objects for more complex application-specific structures. The goal is to avoid conflicts with future ECS field additions and reduce inconsistent field naming across data producers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS logging libraries+1



### 6.2 Filebeat and independent collection

The official integration guidance uses Filebeat to collect ECS-formatted events.

For Filebeat 7.16 and later, the documented file-based pattern uses the `filestream` input with an `ndjson` parser:

```
filebeat.inputs:
  - type: filestream
    paths:
      - /path/to/logs.json
    parsers:
      - ndjson:
          overwrite_keys: true
          add_error_key: true
          expand_keys: true
```

The consequential options are:

| Setting          | Function                                                           | Consideration                                                             |
| ---------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `ndjson`         | Parse individual JSON log lines                                    | Each event must occupy a valid JSON record                                |
| `expand_keys`    | Expand dotted keys into nested structures                          | Important because `ecs-logging` deliberately emits some dotted properties |
| `overwrite_keys` | Allow parsed event fields to overwrite fields supplied by Filebeat | Field provenance and precedence become important                          |
| `add_error_key`  | Attach diagnostics for malformed JSON                              | Helps identify collection failures                                        |

Filebeat also supports metadata processors for host, cloud, Docker, and Kubernetes information. Those enrichments come from the collection layer, not from the Python formatter.

Elastic additionally documents Docker labels and Kubernetes annotations for automatic JSON parsing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS Logging Python



Source: `https://www.elastic.co/docs/reference/ecs/logging/python/installation`

### 6.3 Storage and analysis remain independent

The resulting JSON can be consumed by systems other than Elasticsearch. The events are ordinary JSON objects, so collectors, stream processors, files, databases, and analytics systems can parse them independently.

However, standard ECS field names do not guarantee that non-Elastic consumers automatically implement ECS semantics. Those systems still need to interpret field types and preserve the required relationships.

The architectural benefit is a separation between:

- Instrumentation: What event occurred and what contextual information is available.
- Representation: How that event is expressed consistently as structured JSON.
- Collection and persistence: How the event is transported, retained, indexed, or queried.

That separation permits an application to produce portable structured events without embedding Elasticsearch APIs or log-delivery details directly into its application code.

## 7. Extension points and architectural composition

The library is intentionally small. Its extensibility comes primarily from standard Python logging mechanisms, structlog processors, and a few well-placed overrides.

### 7.1 Extension mechanisms

| Mechanism                            | Extension point                                       | Suitable purpose                                              |
| ------------------------------------ | ----------------------------------------------------- | ------------------------------------------------------------- |
| Stdlib ECS transformation            | `StdlibFormatter.format_to_ecs(record)`               | Add, remove, or transform fields after the default extraction |
| Stdlib output serialization          | Override `StdlibFormatter.format(record)`             | Replace or extend the final serialization behavior            |
| Structlog ECS transformation         | `StructlogFormatter.format_to_ecs(event_dict)`        | Modify normalized event data before JSON rendering            |
| Structlog serialization              | Override `StructlogFormatter._json_dumps()`           | Supply an alternative JSON encoder or output policy           |
| Stdlib contextual instrumentation    | `logging.Filter`, `LoggerAdapter`, `LogRecordFactory` | Attach contextual attributes to logging records               |
| Structlog contextual instrumentation | Bound contexts, context variables, processors         | Add execution-scoped or event-specific metadata               |
| Delivery and buffering               | Python logging handlers and external collectors       | Control asynchronous delivery, retention, and routing         |

The clearest native extension point is `format_to_ecs()`. It exposes the ECS event as an ordinary Python dictionary before serialization.

For example:

```
import ecs_loggingclass DomainFormatter(ecs_logging.StdlibFormatter):    def format_to_ecs(self, record):        event = super().format_to_ecs(record)        event.setdefault("custom", {})["component"] = "ingestion"        return event
```

This supports additional domain metadata while retaining the default ECS metadata extraction and serialization behavior.

Because the hook operates on the event representation itself, it can also support deterministic renaming, enrichment, or removal of fields that cannot be expressed conveniently through constructor arguments.

Source: `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_stdlib.py`

### 7.2 Combining built-in mechanisms to reduce custom machinery

Several useful capabilities arise from combinations rather than individual APIs.

Structured request context: `structlog.contextvars` supplies execution-scoped context, upstream processors add event metadata, and `StructlogFormatter` creates the ECS representation. The application does not need its own request-context propagation system for logging.

Standardized third-party logging: Python's hierarchical loggers and handlers can route records from external Python packages through the same ECS formatter. The integration avoids requiring every dependency to emit structured events itself.

Error observability: Python logging captures exceptions through `exc_info`, `StdlibFormatter` maps their diagnostic fields, and Elastic APM adds correlation identifiers when instrumented. This yields a consistent relationship between failure diagnostics and distributed execution context.

Configurable event representation: Constructor-level context, exclusion prefixes, and `format_to_ecs()` make several forms of customization possible without introducing an entirely separate event-construction or serialization subsystem.

These capabilities are conditional on records reaching the relevant formatter with the required context still intact.

### 7.3 A subtle boundary: logging handlers are not interchangeable

Not every Python logging handler uses its formatter in the same way.

For instance, standard `SocketHandler` transports pickled record attributes rather than directly emitting formatted JSON. `HTTPHandler` uses a URL-encoded representation generated by `mapLogRecord()` instead of applying a configured formatter in its usual emission path.

As a result, setting an ECS formatter on an arbitrary handler does not guarantee that the handler will emit ECS JSON.

This becomes particularly relevant when selecting a remote transport or introducing a central logging process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 7.4 Queue-based logging and exception preservation

There is a more consequential interaction with Python's `QueueHandler`.

The default `QueueHandler.prepare()` transforms records before enqueueing them. In doing so, it removes information such as `args` and `exc_info` to make the record easier to transport.

If ECS formatting occurs only after that transformation, on the `QueueListener` side, the formatter may no longer have the original traceback needed to populate `error.type`, `error.message`, or `error.stack_trace`.

The formatter has not failed; its input has already lost information.

Python documents `QueueHandler.prepare()` as overridable specifically because the default transformation may be unsuitable for handlers that require custom exception formatting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



This is a useful general design distinction:

- Formatting before a queue preserves the resulting ECS representation but performs serialization on the producer side.
- Formatting after a queue can move serialization work to a consumer but requires preserving the necessary structured record information.

The distinction affects both performance and diagnostic completeness.

Python handler reference: `https://docs.python.org/3/library/logging.handlers.html`

## 8. Operational characteristics and limitations

### 8.1 Performance model

`ecs-logging` does not provide a compiled high-throughput serialization engine, internal asynchronous queue, or independent buffering subsystem.

Its principal operations are Python dictionary construction, recursive field normalization, merging, and JSON serialization.

Performance is therefore influenced by:

| Factor               | Mechanism                                | Implication                                                        |
| -------------------- | ---------------------------------------- | ------------------------------------------------------------------ |
| Number of fields     | Dictionary traversal and merging         | Larger events require more transformation work                     |
| Structural depth     | Recursive normalization                  | Deeply nested context adds traversal cost                          |
| Exception collection | Traceback formatting                     | Exception-heavy logging can be substantially more expensive        |
| Serialization        | Standard `json.dumps`, including sorting | CPU and allocation costs occur during rendering                    |
| Nonstandard objects  | `__structlog__()` or `repr()`            | Potentially expensive application-defined behavior                 |
| Output volume        | Size of JSON events                      | Storage and downstream ingestion costs increase with event size    |
| Handler architecture | Synchronous or delegated output          | Controls how much logging work runs on application execution paths |

Logging level filtering can eliminate downstream formatting for suppressed records, but behavior depends on the logging framework and its configuration.

No general throughput, allocation, or latency claims are justified by the upstream sources reviewed. The important architectural inference is that moving transport off an application thread does not necessarily remove the cost of constructing or serializing the event.

### 8.2 Information preservation

The library's two formatters have different behaviors regarding optional and missing information.

| Input characteristic             | Stdlib integration                             | Structlog integration                                         |
| -------------------------------- | ---------------------------------------------- | ------------------------------------------------------------- |
| `None` value                     | Generally omitted during extraction/enrichment | Can remain as JSON `null`                                     |
| Unspecified ECS metadata         | Some fields generated from `LogRecord`         | Must often be supplied explicitly                             |
| Original interpolation arguments | Rendered into the message                      | Structured context can be retained separately                 |
| Exception type/message           | Automatically extracted from `exc_info`        | Not automatically derived from an arbitrary exception payload |
| Custom Python objects            | JSON fallback or representation conversion     | Same fallback, with processor customization available         |
| Existing timestamp               | Uses record metadata                           | Preserves supplied `@timestamp`                               |

For systems that distinguish missing values, explicit nulls, and meaningful defaults, these differences matter.

In particular, ECS serialization should not be treated as lossless event serialization. The formatters implement logging-oriented transformations, not an arbitrary-object preservation protocol.

### 8.3 Security and data governance

The library does not implement a comprehensive sensitive-data classification or redaction policy.

Potential exposure points include application-supplied context, exception messages, stack traces, URL values, and fallback `repr()` output.

`exclude_fields` is useful for omitting known field paths, but it is not a complete security boundary. In particular, it cannot prevent sensitive values from being embedded in the free-form `message` text, and the structlog formatter does not offer the same built-in exclusion argument.

Sensitive-data filtering is therefore most reliably handled before serialization, through application instrumentation or upstream logging processors.

The same distinction applies to structured logging field cardinality: the formatter can emit arbitrary field names, but Elasticsearch mappings and indexing costs are controlled by the schema and backend configuration.

### 8.4 Failure and delivery guarantees

The library does not guarantee durable delivery or exactly-once event persistence.

Failures can arise from incompatible nested field types, malformed event objects, serialization behavior, or the handler/collector lifecycle.

Python logging handlers have their own error-handling conventions, including cases where events may be dropped rather than propagated as ordinary application exceptions.

For systems in which logging is part of an audit or transactional record, this separation is material: producing ECS JSON is not equivalent to committing an event to durable storage.

### 8.5 ECS conformance limits

`ecs-logging` automatically supplies common ECS fields and imposes some structural normalization. It does not enforce every ECS datatype, field relationship, or semantic constraint.

The relevant responsibilities are distinct:

| Responsibility                                 | Owner                                             |
| ---------------------------------------------- | ------------------------------------------------- |
| Common ECS field names and definitions         | Elastic Common Schema                             |
| Automatic logging-record field mapping         | `ecs-logging`                                     |
| Custom application field semantics             | Application instrumentation                       |
| Collector-level enrichment and JSON processing | Filebeat, Elastic Agent, or alternative collector |
| Index mappings and field type enforcement      | Elasticsearch or another storage engine           |
| Schema compatibility and semantic validation   | Upstream/downstream validation machinery          |

For example, a field supplied as `http.response.status_code` is not made correct merely because its name matches ECS. Its value still needs to have the expected type and meaning.

ECS schema guidelines: `https://www.elastic.co/docs/reference/ecs/ecs-guidelines`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

Elastic Common Schema (ECS)



## 9. Relationship to adjacent libraries and tools

The important distinction is whether an adjacent tool handles event creation, context propagation, serialization, or delivery.

| Tool or mechanism             | Primary responsibility                           | Relationship to `ecs-logging`                                     |
| ----------------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| Python `logging`              | Log records, levels, filters, handlers           | Existing runtime used by `StdlibFormatter`                        |
| `structlog`                   | Structured event pipelines and context           | Supplies events and processors for `StructlogFormatter`           |
| `structlog.JSONRenderer`      | Generic JSON rendering                           | Alternative to ECS-aware terminal serialization                   |
| `python-json-logger`          | Generic JSON formatting of Python records        | Alternative formatter with different schema behavior              |
| Elastic APM Python agent      | Instrumentation, traces, correlation context     | Provides identifiers mapped or serialized by `ecs-logging`        |
| OpenTelemetry instrumentation | Vendor-neutral telemetry context                 | Can supply correlation data through additional mapping/enrichment |
| Filebeat / Elastic Agent      | Log collection, parsing, forwarding, enrichment  | Consumes ECS-formatted output                                     |
| Elasticsearch                 | Event indexing, mapping, search                  | Common downstream consumer                                        |
| Kibana                        | Log inspection, visualization, trace correlation | Uses indexed ECS fields                                           |
| ECS schema                    | Field definitions and semantics                  | Specification the formatter targets                               |

### `ecs-logging` versus generic JSON formatting

A generic JSON renderer primarily ensures that event content is encoded as JSON.

`ecs-logging` adds opinionated field mappings, logging metadata extraction, ECS-specific naming, error handling, serialization ordering, and APM correlation support.

The value increases when multiple applications, languages, and telemetry sources benefit from using shared field semantics.

Conversely, a system whose event model is intentionally independent of ECS may find a generic JSON renderer and separately defined schema more appropriate.

### `ecs-logging` versus `structlog`

These libraries are complementary rather than direct substitutes.

`structlog` provides a sophisticated event-processing architecture, including bound contexts, execution-context integration, filtering, and reusable processors.

`ecs-logging` contributes an ECS-aware terminal representation. It does not replace the broader processing facilities of `structlog`.

Using both enables context construction and schema-specific rendering to be separated cleanly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://structlog.org\&sz=32)

structlog 26.1.0 documentation



### `ecs-logging` versus OpenTelemetry

OpenTelemetry provides instrumentation, telemetry data models, context propagation, SDKs, and export mechanisms.

`ecs-logging` does not implement those facilities. Its primary output is JSON following ECS conventions.

The two approaches can be combined if the application or logging pipeline maps appropriate trace identifiers and contextual fields into ECS. However, the Elastic APM-specific automatic mappings should not be assumed to cover every OpenTelemetry logging convention.

## 10. Version-sensitive capability history

| Version | Material change                                                                            |
| ------- | ------------------------------------------------------------------------------------------ |
| 0.2     | Support for Python logging `extra` fields                                                  |
| 0.3     | Exception metadata, process/thread enrichment, field exclusion, traceback limits           |
| 0.4     | Elastic APM trace, transaction, and span correlation                                       |
| 0.5     | ECS 1.6 support and stack information handling                                             |
| 1.1     | APM field precedence correction and removal of older `event.dataset` special handling      |
| 2.0     | Global `extra` context fields; Python 2 support removed                                    |
| 2.1     | APM `service.environment`; correction to structlog stack-trace handling                    |
| 2.2     | `ecs.version` output correction, customizable structlog JSON serialization, typing updates |
| 2.3     | `ensure_ascii` for both formatters and support for Python 3.13/3.14                        |

The last two releases are particularly important when reproducing older integration behavior. Field representation and serialization customization changed in 2.2, while Unicode-output configuration changed in 2.3.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 11. Critical technical distinctions

The following distinctions capture the main architectural considerations beyond the introductory APIs.

| Distinction                                          | Consequence                                                               |
| ---------------------------------------------------- | ------------------------------------------------------------------------- |
| Formatter vs. transport                              | ECS JSON generation does not establish delivery or persistence guarantees |
| `StdlibFormatter` vs. `StructlogFormatter`           | Automatic metadata enrichment differs substantially                       |
| Log message vs. structured context                   | Interpolated arguments are not automatically preserved as typed fields    |
| Dotted keys vs. nested JSON                          | Output representation and collector normalization can differ              |
| ECS version vs. package version                      | `ecs-logging` 2.3.0 still identifies its schema as ECS 1.6.0              |
| Structured merge vs. arbitrary overwrite             | Field collisions can raise errors instead of silently overwriting         |
| Event time vs. formatting time                       | Timestamp semantics differ between the two integrations                   |
| Exception traceback vs. exception object             | Structlog may require an upstream exception-rendering processor           |
| Native context injection vs. tracing instrumentation | The formatter consumes correlation context; it does not create traces     |
| Formatting vs. schema validation                     | ECS-compatible naming is not a guarantee of field type correctness        |
| Queueing vs. diagnostic preservation                 | Handler preparation can remove fields required for subsequent enrichment  |
| JSON fallback vs. typed preservation                 | Nonstandard objects may become `repr()` strings                           |

## 12. Primary-source reference map

The following references are independently accessible and cover the principal implementation and integration surfaces.

| Resource                                  | Direct URL                                                                          |
| ----------------------------------------- | ----------------------------------------------------------------------------------- |
| Python library repository                 | `https://github.com/elastic/ecs-logging-python`                                     |
| Version history                           | `https://github.com/elastic/ecs-logging-python/blob/main/CHANGELOG.md`              |
| Standard-library formatter implementation | `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_stdlib.py`    |
| Structlog formatter implementation        | `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_structlog.py` |
| Field normalization and JSON serializer   | `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/_utils.py`     |
| Public package exports                    | `https://github.com/elastic/ecs-logging-python/blob/main/ecs_logging/__init__.py`   |
| Package metadata and dependencies         | `https://github.com/elastic/ecs-logging-python/blob/main/pyproject.toml`            |
| Elastic installation and collection guide | `https://www.elastic.co/docs/reference/ecs/logging/python/installation`             |
| ECS logging architecture                  | `https://www.elastic.co/docs/reference/ecs/logging/intro`                           |
| ECS schema documentation                  | `https://www.elastic.co/docs/reference/ecs`                                         |
| ECS field guidelines                      | `https://www.elastic.co/docs/reference/ecs/ecs-guidelines`                          |
| Elastic APM log correlation               | `https://www.elastic.co/docs/reference/apm/agents/python/logs`                      |
| Elastic APM configuration                 | `https://www.elastic.co/docs/reference/apm/agents/python/configuration`             |
| Structlog processor documentation         | `https://www.structlog.org/en/stable/processors.html`                               |
| Python logging handlers                   | `https://docs.python.org/3/library/logging.handlers.html`                           |

## Overall architectural assessment

`ecs-logging` is best understood as a focused ECS representation adapter over established Python logging infrastructure.

Its main strengths are standardized field extraction, structured context normalization, exception diagnostics, and native compatibility with the two dominant Python logging approaches. Its highest-value interactions come from combining these features with context-aware processors, Elastic APM instrumentation, and independent collection machinery.

Its main constraints are equally clear: limited schema-version coverage, no comprehensive runtime ECS validation, no built-in redaction or durable transport, and meaningful differences between stdlib and structlog enrichment. Underlying logging-handler behavior can also affect the information available to the formatter.

The architectural opportunity is to establish a common semantic representation for logs without implementing custom JSON serialization, field mapping, exception extraction, and distributed-trace correlation logic throughout an application. The library provides that representation layer while leaving instrumentation, transport, persistence, and broader observability policy independently composable.