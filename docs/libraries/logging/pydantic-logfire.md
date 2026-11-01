# Pydantic Logfire — Comprehensive Python Library Overview

Target: Logfire 5.4.0 (stable) | Research date: November 1, 2026 | Language: Python | Foundation: OpenTelemetry

Pydantic Logfire is an observability SDK and platform for understanding application execution through correlated traces, structured logs, metrics, exceptions, and rich runtime data. Its distinguishing capabilities include Python-native instrumentation, automatic tracing of frameworks and libraries, structured serialization of Python objects, distributed tracing, SQL-based telemetry analysis, and specialized observability for LLMs and AI agents.

Logfire combines three complementary layers:

1. Python instrumentation SDK: Captures application behavior, execution context, timings, structured values, exceptions, and metrics through explicit and automatic instrumentation.
2. OpenTelemetry infrastructure: Provides standardized trace context, semantic conventions, metric instruments, instrumentation packages, and telemetry export.
3. Observability platform: Supplies live trace exploration, SQL analytics, dashboards, alerts, error tracking, AI evaluations, and related operational capabilities.

The SDK and platform are related but distinct. The Python instrumentation capabilities can be used with alternative OpenTelemetry backends; the complete Logfire analysis experience depends on the Logfire backend and its associated services.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Version boundary: Version 5.4.0 was released October 26, 2026. The 6.0 series remains in beta as of this review. Version 6 introduces a packaging split between `logfire-sdk`, `logfire-cli`, and the compatibility distribution `logfire`; this overview targets the released 5.x API and identifies consequential boundaries separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary project resources:

- Documentation: [https://pydantic.dev/docs/logfire/](https://pydantic.dev/docs/logfire/?utm_source=chatgpt.com)
- Repository: [https://github.com/pydantic/logfire](https://github.com/pydantic/logfire?utm_source=chatgpt.com)
- Release history: [https://github.com/pydantic/logfire/releases](https://github.com/pydantic/logfire/releases?utm_source=chatgpt.com)
- Python package: [https://pypi.org/project/logfire/](https://pypi.org/project/logfire/?utm_source=chatgpt.com)
- Python API reference: [https://pydantic.dev/docs/logfire/api/logfire/](https://pydantic.dev/docs/logfire/api/logfire/?utm_source=chatgpt.com)

## 1. Conceptual model and capability map

Logfire treats application execution as a causal, structured stream of operations and observations, rather than as independent text messages.

| Capability family         | Principal mechanisms                                                      | Architectural significance                                                     |
| ------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Tracing                   | Spans, traces, instrumentation decorators, context propagation            | Reconstruct execution and latency across functions, services, and dependencies |
| Structured logging        | Severity methods, message templates, attributes, exception records        | Attach detailed application state to causal execution context                  |
| Automatic instrumentation | Import-time function tracing, framework integrations                      | Obtain execution visibility without manually instrumenting every operation     |
| Metrics                   | Counters, histograms, gauges, observable instruments                      | Aggregate continuous operational signals                                       |
| Distributed execution     | W3C trace context, OpenTelemetry propagation                              | Connect separate processes, threads, services, and tasks into coherent traces  |
| AI observability          | LLM/provider instrumentation, agent execution traces, token and cost data | Inspect model interactions, tool calls, agent behavior, and operational cost   |
| Control and privacy       | Sampling, scrubbing, suppression, filtering, resource metadata            | Regulate telemetry completeness, expense, and information disclosure           |
| Telemetry analysis        | SQL, query clients, dashboards, alerts, evaluations                       | Convert collected events into debugging, monitoring, and analysis workflows    |

### Core data semantics

- Span: A timed operation with a name, attributes, context, status, and potentially child operations.
- Trace: A causally connected collection of spans sharing a trace identity.
- Log: A point-in-time observation that can be associated with an active trace and span.
- Metric: A numerical measurement aggregated across observations and time.
- Resource: Metadata identifying the producing service or execution environment.

These concepts follow OpenTelemetry, but Logfire adds a Python-oriented presentation and serialization model, message templates, and its own analysis conventions. The platform makes related logs and spans navigable together, including in its SQL `records` representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



The central architectural opportunity is to make application behavior observable through existing library instrumentation and standardized telemetry, reserving custom event collection for domain-specific behavior that generic instrumentation cannot infer.

## 2. Structured tracing and logging

### 2.1 Explicit spans and structured events

The principal APIs are `logfire.span()`, the severity-specific logging methods, and `@logfire.instrument()`.

A span defines a timed execution boundary. Nested spans and logs inherit its context, creating a hierarchy without explicitly passing trace identifiers through function calls.

```
import logfirelogfire.configure(service_name="processing-service")@logfire.instrument("Process batch {batch_id}", record_return=True)def process_batch(batch_id: str, records: list[dict]):    with logfire.span(        "Validate records",        batch_id=batch_id,        record_count=len(records),    ) as span:        valid = [r for r in records if "id" in r]        span.set_attribute("valid_count", len(valid))    logfire.info(        "Batch {batch_id} validated",        batch_id=batch_id,        valid_count=len(valid),    )    return len(valid)
```

Illustrative example; not executed.

The example produces a function span containing validation work and a correlated completion log. Its structured attributes can be searched independently of the rendered message.

Significant API capabilities:

| Mechanism                                               | Behavior                                                                 |
| ------------------------------------------------------- | ------------------------------------------------------------------------ |
| `logfire.span(template, **attributes)`                  | Creates a contextual timed operation                                     |
| `logfire.debug/info/notice/warn/error/fatal(...)`       | Records severity-classified observations                                 |
| `logfire.exception(...)`                                | Records an error with exception information                              |
| `@logfire.instrument(...)`                              | Instruments a function, optionally capturing arguments and return values |
| `span.set_attribute(...)`                               | Adds or updates structured span attributes                               |
| `span.set_level(...)`                                   | Changes a span's Logfire severity                                        |
| `span.record_exception(...)`                            | Records a handled exception explicitly                                   |
| `span.message`                                          | Allows the displayed message to be updated                               |
| `_tags`, `_span_name`, `_level`, `_links`, `_span_kind` | Provide additional span classification, naming, and tracing controls     |

Logfire's methods are deliberately higher-level than creating raw OpenTelemetry spans and events manually. It handles much of the serialization, message formatting, source-location metadata, and export integration.

### 2.2 Message templates versus rendered messages

Logfire distinguishes two representations:

- Span name / message template: A relatively stable operation identifier, such as `Process batch {batch_id}`.
- Rendered message: A human-readable instance, such as `Process batch batch-42`.

The associated attributes preserve `batch_id` separately.

This separation matters because stable span names are easier to aggregate and index than messages containing dynamically generated identifiers.

For example:

```
logfire.info("Processing {item_id}", item_id=42)
```

is preferable to constructing an entirely new message string for every item when the intention is to query or aggregate instances of the same operation.

In Logfire's SQL representation, these can be investigated through `span_name`, `message`, and structured `attributes`. The documentation explicitly identifies indexed `span_name` filtering as more efficient than matching rendered messages.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



### 2.3 Python-aware formatting and object capture

A distinctive capability is source-aware argument inspection, which allows Logfire to recover structured attributes from inline f-strings.

On Python 3.11 and newer:

```
logfire.info(f"Processing {item_id}")
```

can be interpreted similarly to:

```
logfire.info("Processing {item_id}", item_id=item_id)
```

This behavior is enabled through `inspect_arguments`, rather than ordinary Python f-string semantics.

Important limitations:

- The source code must be available for inspection.
- The expression must appear in the supported call form; passing a previously formatted string loses the special interpretation.
- Expressions may be evaluated again, so side effects and expensive computations inside formatted expressions are undesirable.
- If inspection fails, the resulting message may become a high-cardinality span name.
- Source inspection introduces some overhead, particularly on the first inspection of a source file.

Logfire also serializes complex Python attributes into structured JSON-compatible representations and records schema metadata for richer interpretation.

This can substantially reduce bespoke diagnostic serialization, although it does not establish that arbitrary Python objects can always be reconstructed losslessly from exported telemetry.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



### 2.4 Function instrumentation and exception semantics

`@logfire.instrument()` supports automatic argument capture, optional return-value capture, custom names, severity, and the ability to start a separate trace linked to the active one.

Its important controls include:

- `extract_args=False` to avoid capturing function inputs.
- `record_return=True` to capture successful return values.
- `level='debug'` or another supported severity.
- `new_trace=True` to separate an operation causally without losing the relationship to its parent.

An exception escaping a span is automatically recorded, and the span's level is raised to error. An exception caught internally is not automatically captured; `span.record_exception()` can record it explicitly without necessarily changing the span's severity.

The function decorator also has constraints involving source-code accessibility and decorator ordering.

Generator lifecycle caveat: A span containing `yield` may remain active while a generator is suspended. If consumption ends early, that span can incorrectly remain in the current execution context; asynchronous generators can additionally encounter context-detachment errors. Logfire documents this limitation and excludes generators from automatic tracing. Spans around iteration or properly managed context-manager lifetimes avoid the ambiguity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/logfire/instrument/python/add-manual-tracing/](https://pydantic.dev/docs/logfire/instrument/python/add-manual-tracing/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/reference/generators/](https://pydantic.dev/docs/logfire/reference/generators/?utm_source=chatgpt.com)

## 3. Automatic instrumentation and Pydantic integration

### 3.1 Automatic function tracing

`logfire.install_auto_tracing()` instruments function calls in selected Python modules through an import-time mechanism.

It supports module-name selection, regular expressions, and a predicate receiving module information. It must be installed before importing the modules to be traced.

A significant advanced feature is duration-triggered tracing:

```
logfire.install_auto_tracing(    modules=["application"],    min_duration=0.01,)
```

This is not simply a per-call filter that records every invocation longer than 10 ms.

Its behavior is adaptive:

1. Calls are initially timed without necessarily producing spans.
2. Once a function exceeds the threshold, that invocation is not retained.
3. Subsequent calls to that function are traced, including faster calls.

`min_duration=0` enables tracing from the outset. `@logfire.no_auto_trace` excludes selected functions and their nested functions from this instrumentation.

This mechanism can expose slow or previously unidentified application operations without widespread manual decorators. However, it still incurs timing overhead, depends on import order, and does not provide precise completeness guarantees for early invocations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/instrument/python/add-auto-tracing/](https://pydantic.dev/docs/logfire/instrument/python/add-auto-tracing/?utm_source=chatgpt.com)

### 3.2 Pydantic model validation instrumentation

`logfire.instrument_pydantic()` integrates with Pydantic's validation plugin system, capturing successful or failed model validation and recording validation metrics.

The important modes are:

| `record` mode | Individual validation spans | Aggregate validation metrics |
| ------------- | --------------------------- | ---------------------------- |
| `all`         | Successes and failures      | Yes                          |
| `failure`     | Failures only               | Yes                          |
| `metrics`     | None                        | Yes                          |
| `off`         | None                        | No                           |

The plugin also exposes meaningful scoping controls:

- Global configuration through code, environment variables, or `pyproject.toml`.
- `include` and `exclude` patterns over model identifiers.
- Per-model `plugin_settings`.
- Custom tags attached to validation telemetry.

Two consequential details distinguish this integration from ordinary application tracing.

Instrumentation is definition-sensitive. Calling `instrument_pydantic()` programmatically instruments models defined and imported afterward, rather than retroactively instrumenting all existing classes.

Version 5 excludes third-party models by default. The distinction is based on module location, not conceptual ownership. An application's own installed package may therefore be treated as third-party if it resides in `site-packages`. Explicit inclusion patterns can override this behavior.

This enables targeted observability of validation contracts without requiring custom wrappers around every `BaseModel` or `TypeAdapter` validation path. However, validation inputs and errors may contain sensitive application data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Source: [https://pydantic.dev/docs/logfire/integrations/pydantic/](https://pydantic.dev/docs/logfire/integrations/pydantic/?utm_source=chatgpt.com)

### 3.3 Capturing existing logging systems

Logfire also integrates with logging machinery that is already present.

`LogfireLoggingHandler` can capture standard `logging` records and preserve their severity, logger identity, and structured metadata. Documented integrations also cover `structlog`, `loguru`, and `print()` instrumentation.

This is distinct from replacing existing logging calls with Logfire methods. A handler bridges existing records into Logfire's telemetry system, while direct Logfire instrumentation exposes additional native message-template and span functionality.

One subtlety is that Logfire represents its native logs using span-based conventions internally. A third-party OpenTelemetry backend may therefore display these records differently from a backend with dedicated Logfire support.

The logging handler also supports a fallback handler when instrumentation is suppressed. Console output needs separate consideration when another handler already prints the same records.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Sources:

[https://pydantic.dev/docs/logfire/integrations/logging/logging/](https://pydantic.dev/docs/logfire/integrations/logging/logging/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/instrument/python/integrate/](https://pydantic.dev/docs/logfire/instrument/python/integrate/?utm_source=chatgpt.com)

## 4. Metrics and quantitative observability

Logfire builds metric collection on OpenTelemetry and exposes convenient instrument constructors.

| Instrument                      | API                         | Measurement semantics                |
| ------------------------------- | --------------------------- | ------------------------------------ |
| Counter                         | `metric_counter()`          | Monotonically accumulated increments |
| Histogram                       | `metric_histogram()`        | Distribution of observed values      |
| Up-down counter                 | `metric_up_down_counter()`  | Increasing and decreasing quantities |
| Gauge                           | `metric_gauge()`            | Latest measured value                |
| Observable/callback instruments | Corresponding callback APIs | Values observed during collection    |

Custom metrics can express queue depths, operation counts, payload sizes, durations, resource utilization, or other numerical properties not inferred by generic instrumentation.

### 4.1 Metrics are not individual event records

A histogram measures a distribution, not necessarily a durable record for every sample. Counters and gauges similarly have aggregation semantics that differ from logs and spans.

Logfire does not store OTLP `Summary` metrics. Histograms are the documented alternative when percentile analysis is required.

Custom metric definitions should also account for attribute cardinality, units, aggregation temporality, and collection behavior. These are inherited substantially from OpenTelemetry and the backend's aggregation model.

### 4.2 Synchronous and asynchronous measurement

OpenTelemetry observable callbacks execute synchronously during collection. They cannot directly await an asynchronous API.

For asynchronously sourced values, a separate application-owned polling task can update a normal gauge. This introduces lifecycle obligations—task cancellation, failure handling, stale-value detection, and worker-level aggregation—that the gauge instrument itself does not eliminate.

### 4.3 Aggregating metrics into parent spans

One of Logfire's more easily overlooked capabilities is in-span metric aggregation.

With:

```
logfire.configure(    metrics=logfire.MetricsOptions(collect_in_spans=True))
```

counter and histogram measurements can be aggregated into the active span and its ancestors, appearing in the `logfire.metrics` attribute.

This permits an operation spanning several child calls to carry cumulative measurements without requiring a later SQL join across all child spans.

The capability is particularly useful for AI token and cost attribution. The `operation.cost` metric is specially enabled for in-span aggregation.

Status and limitation: The official documentation marks general in-span aggregation as experimental. Aggregation is process-local; it does not aggregate metrics across distributed tracing boundaries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+3



Sources:

[https://pydantic.dev/docs/logfire/instrument/python/add-metrics/](https://pydantic.dev/docs/logfire/instrument/python/add-metrics/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/reference/metrics-in-spans/](https://pydantic.dev/docs/logfire/reference/metrics-in-spans/?utm_source=chatgpt.com)

## 5. Framework, database, and infrastructure integrations

The integration layer is one of Logfire's principal sources of leverage. Many integrations wrap existing OpenTelemetry instrumentation packages, while others provide Logfire-specific instrumentation or enhance existing library hooks.

This distinction matters: an `instrument_*()` method does not necessarily implement the underlying instrumentation itself. It may configure or adapt another project's instrumentor, including inheriting that project's compatibility and lifecycle constraints.

### 5.1 Integration coverage

| Domain                     | Representative integrations                                                         | Captured behavior                                                          |
| -------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Web servers                | FastAPI, Starlette, Django, Flask, Litestar, ASGI, WSGI, aiohttp                    | Requests, routes, latency, status, exceptions, selected request attributes |
| HTTP clients               | HTTPX, HTTPX2, Requests, aiohttp, urllib                                            | Outbound requests, response status, latency, errors, propagation           |
| Relational databases       | Psycopg 3/2, SQLAlchemy, asyncpg, MySQL, SQLite                                     | SQL operations, statement metadata, connection context, duration, errors   |
| Other data systems         | Redis, PyMongo, Elasticsearch, Snowflake, BigQuery, SurrealDB                       | Client/database operations and their timing                                |
| Asynchronous processing    | Celery, Airflow, FastStream                                                         | Task execution, queue-related activity, failure and workflow context       |
| Runtime and infrastructure | System metrics, AWS Lambda, Gunicorn                                                | Runtime activity, infrastructure state, execution environment              |
| AI systems                 | Pydantic AI, OpenAI, Anthropic, Google Gen AI, LiteLLM, DSPy, MCP, agent frameworks | Model calls, messages, tools, retries, usage, and execution structure      |

OpenTelemetry-compatible third-party instrumentation can also produce useful telemetry without an explicit Logfire-specific integration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://logfire.pydantic.dev\&sz=32)

Pydantic Docs+4



Integration catalog: [https://pydantic.dev/docs/logfire/integrations/](https://pydantic.dev/docs/logfire/integrations/?utm_source=chatgpt.com)

### 5.2 FastAPI and application request boundaries

`logfire.instrument_fastapi(app)` supplies more than ordinary ASGI request timing.

It can capture parsed endpoint arguments, validation errors, matched routes, request context, and additional endpoint-related spans.

This allows application-level work, database calls, outbound HTTP requests, and custom spans to be nested under the originating request.

Important controls include OpenTelemetry instrumentor options and a `request_attributes_mapper` for modifying captured endpoint attributes.

The latter is consequential for privacy because route parameters and parsed arguments can contain personally identifiable or otherwise sensitive information.

Source: [https://pydantic.dev/docs/logfire/integrations/web-frameworks/fastapi/](https://pydantic.dev/docs/logfire/integrations/web-frameworks/fastapi/?utm_source=chatgpt.com)

### 5.3 Database instrumentation

Database instrumentation makes it possible to associate a slow application operation with the actual queries executed inside it.

The mechanism varies by client:

- `instrument_psycopg()` supports Psycopg 3 and Psycopg 2, with global or connection-specific instrumentation.
- `instrument_sqlalchemy(engine=...)` instruments a selected engine; multiple engines are supported. Without explicit engines, instrumentation depends on being activated before SQLAlchemy is imported.
- `instrument_asyncpg()` provides asyncpg-specific instrumentation and capture controls.
- `instrument_surrealdb()` supports instrumentation of the Python SurrealDB client's operations, with global, class-specific, or connection-specific scope.

For SurrealDB, generator-based operations such as live subscriptions have different instrumentation semantics from ordinary operations: their invocation is represented as a log rather than a complete operation-duration span, and errors during subsequent iteration are not captured automatically.

Instrumenting both an ORM and its underlying database driver requires care. Multiple layers may describe the same physical query, potentially introducing duplicate or nested spans rather than independent database operations.

Sources:

[https://pydantic.dev/docs/logfire/integrations/databases/psycopg/](https://pydantic.dev/docs/logfire/integrations/databases/psycopg/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/databases/sqlalchemy/](https://pydantic.dev/docs/logfire/integrations/databases/sqlalchemy/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/databases/asyncpg/](https://pydantic.dev/docs/logfire/integrations/databases/asyncpg/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/databases/surrealdb/](https://pydantic.dev/docs/logfire/integrations/databases/surrealdb/?utm_source=chatgpt.com)

### 5.4 HTTP client and task integration

`instrument_httpx()` supports global instrumentation or selected client instances, including synchronous and asynchronous clients.

Request and response bodies and headers are optional captures, disabled by default. This is an important distinction from basic HTTP request metadata, which can be recorded without collecting payloads.

HTTPX2 support depends on a sufficiently recent underlying OpenTelemetry HTTPX instrumentor.

For Celery, instrumentation can link the producer and consumer of a task through propagated trace context. Worker initialization is particularly important with prefork execution: exporters initialized in the parent process may have background threads in the wrong process after forking.

The documented Celery approach initializes Logfire and its instrumentation in worker processes and also instruments the task-producing application.

Sources:

[https://pydantic.dev/docs/logfire/integrations/http-clients/httpx/](https://pydantic.dev/docs/logfire/integrations/http-clients/httpx/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/event-streams/celery/](https://pydantic.dev/docs/logfire/integrations/event-streams/celery/?utm_source=chatgpt.com)

## 6. Distributed tracing and execution context

Logfire uses OpenTelemetry tracing context and W3C `traceparent` propagation to correlate operations across process and service boundaries.

Its fundamental identity model includes trace IDs, span IDs, parent span IDs, trace flags, and optional additional context.

### 6.1 Automatic and manual propagation

Instrumented HTTP clients inject propagation headers; instrumented servers extract them. Other compatible instrumentation can propagate context through message brokers and task frameworks.

For manual propagation, Logfire exposes:

```
with logfire.span("originating operation"):    context = logfire.get_context()# In a separate execution context:with logfire.attach_context(context):    logfire.info("related operation")
```

The context is portable as serialized propagation metadata, not as a live Python span object.

Logfire also patches `ThreadPoolExecutor` and `ProcessPoolExecutor` for context propagation. Process-pool propagation has configuration-serialization limitations: an unpicklable configuration can prevent Logfire configuration from being transferred to workers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 6.2 Distributed tracing versus independent traces

A shared trace is appropriate when operations form one causal execution.

However, an asynchronous job may need its own trace while retaining a relationship to its origin. `@logfire.instrument(new_trace=True)` provides this distinction using a span link.

This is different from simply making an operation a child of an existing span. Span links allow related operations to have separate trace identities and lifecycles.

The choice also affects sampling, since one trace may be retained while another is discarded.

### 6.3 Important boundaries

Incoming trace context is not always trustworthy or appropriate.

The documentation warns that automatically accepting externally provided trace context can cause unexpected relationships or missing-parent spans, particularly when clients or infrastructure already inject trace headers.

Other limits include cross-service sampling consistency, producer/consumer instrumentation completeness, process initialization, and asynchronous work that outlives its originating request.

A trace context is a correlation mechanism, not a guarantee that all causally related operations will be captured.

Source: [https://pydantic.dev/docs/logfire/instrument/python/distributed-tracing/](https://pydantic.dev/docs/logfire/instrument/python/distributed-tracing/?utm_source=chatgpt.com)

## 7. Sampling, filtering, and telemetry-volume control

Logfire supports both OpenTelemetry head sampling and SDK-level tail sampling.

### 7.1 Head sampling

`SamplingOptions(head=0.1)` retains approximately 10% of newly started traces.

The sampling decision is made early, reducing the cost of capturing and exporting the excluded traces. Custom OpenTelemetry samplers can express more selective policies.

`ParentBased` composition matters: without parent-aware sampling, child spans may be retained despite their parents being excluded, creating incomplete traces.

### 7.2 Tail sampling

`SamplingOptions.level_or_duration()` can retain traces based on observed severity or elapsed duration.

Its documented default criteria include:

- A log or span with severity above `info`.
- An operation exceeding five seconds.

It can also preserve a background fraction of otherwise unremarkable traces.

Custom tail-sampling callbacks receive `TailSamplingSpanInfo` and return an inclusion probability, enabling specialized rules based on available span information.

### 7.3 What sampling does not guarantee

Tail sampling retains spans in memory until a retention decision can be made. This has several consequences:

- Large or long-running traces can require substantial buffers.
- Traces spanning processes may not have complete information available to a local sampler.
- Work continuing after a root span ends can lead to partial retention or unexpected child behavior.
- Head sampling combined with tail sampling still permanently loses traces rejected at the head.

Consequently, selective tail sampling can improve diagnostic usefulness per retained trace, but cannot guarantee complete error or latency visibility across arbitrary distributed execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+3



### 7.4 Suppression and severity filtering

Logfire also exposes controls that are distinct from sampling:

| Mechanism                           | Purpose                                                                |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `min_level`                         | Prevent creation of qualifying low-severity logs/spans                 |
| `suppress_scopes(...)`              | Exclude telemetry from particular OpenTelemetry instrumentation scopes |
| `suppress_instrumentation()`        | Temporarily suppress instrumented activity within a context            |
| `ConsoleOptions(min_log_level=...)` | Filter console display independently of backend collection             |

These are not equivalent operations. Sampling controls which recorded traces survive, while suppression and level thresholds can prevent selected telemetry from being recorded or exported through the relevant pipeline.

Source: [https://pydantic.dev/docs/logfire/instrument/python/sampling/](https://pydantic.dev/docs/logfire/instrument/python/sampling/?utm_source=chatgpt.com)

Source: [https://pydantic.dev/docs/logfire/instrument/python/suppress/](https://pydantic.dev/docs/logfire/instrument/python/suppress/?utm_source=chatgpt.com)

## 8. AI, LLM, and agent observability

Logfire provides specialized instrumentation for model-provider SDKs and agent frameworks. The essential distinction is between model-call instrumentation and agent-execution instrumentation.

A provider integration can show what happened during a model request. An agent integration can additionally reconstruct the surrounding decision process: tool selection, retries, model handoffs, and nested application work.

### 8.1 LLM provider instrumentation

Representative APIs include:

- `logfire.instrument_openai()`
- `logfire.instrument_anthropic()`
- `logfire.instrument_google_genai()`
- `logfire.instrument_litellm()`

The precise data depends on the provider and operation, but can include model identity, request/response content, tool calls, latency, exceptions, token usage, and related metadata.

The OpenAI integration supports chat completions, completions, embeddings, image generation, and the Responses API, including synchronous and asynchronous clients. It can instrument all clients or a selected instance.

Streaming calls have different lifecycles. The OpenAI integration creates separate spans for the initial request and streamed response. Observing only the initial API invocation is therefore insufficient to understand the complete duration and outcome of streaming generation.

In Logfire 5.x, OpenAI instrumentation uses version 2 of its GenAI semantic conventions by default. `instrument_openai(version=[1, 2])` can emit both the legacy and newer attribute formats for migration. This matters when existing queries expect old fields such as `request_data` and `response_data`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources:

[https://pydantic.dev/docs/logfire/integrations/llms/openai/](https://pydantic.dev/docs/logfire/integrations/llms/openai/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/llms/anthropic/](https://pydantic.dev/docs/logfire/integrations/llms/anthropic/?utm_source=chatgpt.com)

### 8.2 Agent framework instrumentation

The principal integrations include Pydantic AI, OpenAI Agents, Claude Agent SDK, and other supported frameworks.

For Pydantic AI, `logfire.instrument_pydantic_ai()` captures:

- Individual agent runs and model requests.
- Conversation history rendered as an inspectable transcript.
- Tool calls, arguments, and results.
- Retries and failed attempts.
- Token consumption and exceptions.

Instrumentation can apply globally or to selected agents.

`logfire.instrument_openai_agents()` similarly exposes agent runs, tool execution, and nested spans. For example, an HTTP client request made inside an agent tool can appear beneath the corresponding tool span when both integrations are active.

`logfire.instrument_claude_agent_sdk()` is a distinct integration from `instrument_anthropic()`. The Claude Agent SDK does not use the normal Anthropic Python client underneath. Its instrumentation captures conversations, turns, and tools, but the documented supported entry point is `ClaudeSDKClient`, not the SDK's standalone `query()` function.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Sources:

[https://pydantic.dev/docs/logfire/integrations/llms/pydanticai/](https://pydantic.dev/docs/logfire/integrations/llms/pydanticai/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/integrations/llms/claude-agent-sdk/](https://pydantic.dev/docs/logfire/integrations/llms/claude-agent-sdk/?utm_source=chatgpt.com)

### 8.3 MCP and cross-process agent tracing

MCP integration extends tracing across the boundary between an agent or tool client and an MCP server.

For MCP Python SDK version 1, `logfire.instrument_mcp()` on both the client and server enables correlated spans for requests, tool arguments, responses, durations, and errors.

MCP version 2 is materially different: The newer SDK, including FastMCP 4, implements OpenTelemetry tracing and propagation itself. In that configuration, `logfire.configure()` on each side is sufficient, and the explicit `instrument_mcp()` call is unnecessary.

This is an example of an important ecosystem boundary: Logfire can act as an OpenTelemetry consumer without owning or duplicating the instrumentation mechanism.

A traced MCP tool call can also contain child spans from HTTP clients, databases, or explicit application instrumentation. That can expose whether a slow agent step was caused by model latency, tool dispatch, remote service execution, or a dependency called inside the tool.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/integrations/llms/mcp/](https://pydantic.dev/docs/logfire/integrations/llms/mcp/?utm_source=chatgpt.com)

### 8.4 Specialized AI analysis

Beyond ordinary trace navigation, the hosted platform provides agent-oriented views, LLM provider analysis, and cost/token dashboards.

These views depend on recognizable instrumentation and semantic attributes. A generic span called `model request` does not automatically carry all the information needed for specialized AI analysis.

Token usage also needs to be distinguished from actual billing: provider-specific accounting, cached tokens, missing usage values, pricing schedules, and instrumentation coverage can affect the accuracy of inferred costs.

The most useful composition is agent-level tracing plus model-provider instrumentation plus application-dependency spans. This links what the agent decided to do with what actually happened when its tools executed.

## 9. Privacy, sensitive data, and telemetry control

Logfire's detailed object capture is valuable diagnostically, but it makes privacy controls especially consequential.

### 9.1 SDK-side scrubbing

The SDK provides configurable scrubbing before telemetry export:

```
logfire.configure(    scrubbing=logfire.ScrubbingOptions(        extra_patterns=["internal_access_code"]    ))
```

It has default patterns targeting credentials, tokens, secrets, cookies, and other potentially sensitive values. A `ScrubMatch` callback can customize decisions or prevent false-positive redactions.

The key limitation is that Logfire does not scrub every textual representation in the same way. The formatted log/span message itself is not scrubbed; the structured fields are. Message templates with separate attributes therefore have both analytical and security advantages over manually concatenated sensitive values into strings.

There are further explicit exceptions:

| Content                             | Scrubbing behavior and implication                                             |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| Structured attributes               | Scanned using the configured patterns, subject to documented exclusions        |
| Fully formatted messages            | Not generally scrubbed                                                         |
| `http.url`                          | Treated as safe by default; secrets in URL query strings can be exposed        |
| `db.statement`                      | Treated as safe by default; interpolated sensitive SQL literals can be exposed |
| LLM input/output message attributes | Scrubbing deliberately disabled                                                |

For AI systems, the official documentation recommends excluding message content from instrumentation when it might contain sensitive information:

```
logfire.instrument_pydantic_ai(include_content=False)
```

This preserves operation timings and metadata while omitting the actual model conversation and tool input/output content.

Regex-based redaction cannot reliably identify arbitrary secrets or private information embedded in natural language.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 9.2 Collector-side controls

For centrally enforced or more complex transformations, an OpenTelemetry Collector can scrub, drop, or transform attributes through its processors and OTTL expressions.

This offers consistency across languages and services and supports conditional policies that are awkward to express in each application.

When using the Collector as the mandatory transformation point, application export must not also send unmodified telemetry directly to Logfire. The documentation explicitly calls for `send_to_logfire=False` for that arrangement.

This boundary is important for privacy guarantees: a centralized collector policy is ineffective if another exporter bypasses it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources:

[https://pydantic.dev/docs/logfire/instrument/python/scrubbing/](https://pydantic.dev/docs/logfire/instrument/python/scrubbing/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/instrument/python/otel-collector-scrubbing/](https://pydantic.dev/docs/logfire/instrument/python/otel-collector-scrubbing/?utm_source=chatgpt.com)

## 10. SQL analytics and programmatic telemetry access

Logfire's analysis model is unusually SQL-centric for an observability product.

The hosted query engine is based on Apache DataFusion, with SQL syntax broadly aligned with PostgreSQL and additional JSON functions and operators. This should not be confused with running queries against a PostgreSQL database: the execution engine and some supported functions and semantics differ.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 10.1 Queryable records and metrics

The principal tables are:

| Table         | Contents                          | Typical analysis                                             |
| ------------- | --------------------------------- | ------------------------------------------------------------ |
| `records`     | Completed spans and logs          | Exceptions, latency, trace reconstruction, service behavior  |
| `records_all` | Records including pending spans   | Specialized inspection of in-progress operations             |
| `metrics`     | Aggregated numerical observations | Time series, rates, percentiles, infrastructure measurements |

Useful `records` columns include `trace_id`, `span_id`, `parent_span_id`, `span_name`, `message`, `attributes`, `level`, `start_timestamp`, `duration`, `service_name`, and exception-related fields.

The SQL schema preserves the span tree through trace and parent identifiers. For example, a join can pair individual child operations with their parents:

```
SELECT
    parent.span_name AS operation,
    child.span_name AS dependency,
    child.duration
FROM records AS parent
JOIN records AS child
    ON child.trace_id = parent.trace_id
   AND child.parent_span_id = parent.span_id
WHERE parent.span_name = 'Process batch {batch_id}'
```

Illustrative query, not executed.

For metrics, the backend provides functions such as `metric_quantile()` and `time_bucket()`, allowing histogram analysis and time-bucketed aggregate queries without reconstructing distributions from individual spans.

A useful distinction is that querying metrics usually offers a more appropriate representation for fleet-wide statistics, while span SQL preserves the details required to explain an individual slow or failed operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



### 10.2 Query-performance and correctness considerations

Structured fields improve search precision.

Filtering by a stable `span_name`, service, or explicitly recorded attribute is often preferable to searching rendered messages. Traces should generally be identified using their complete `trace_id`; when identifying a specific span, the combination of `trace_id` and `span_id` is more useful than `span_id` alone.

There is also a documented query accuracy limitation: text search using `LIKE`, `ILIKE`, regexes, and full-text search can miss substrings of uninterrupted words of 40 bytes or longer. Long hashes, opaque tokens, and encoded values are therefore better searched as dedicated structured attributes with equality comparisons.

This is not merely a performance concern; partial text search can produce false negatives.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/logfire/reference/sql/](https://pydantic.dev/docs/logfire/reference/sql/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/reference/query-accuracy/](https://pydantic.dev/docs/logfire/reference/query-accuracy/?utm_source=chatgpt.com)

### 10.3 Python query clients and Arrow export

Logfire supplies synchronous and asynchronous query clients:

```
from logfire.query_client import (    LogfireQueryClient,    AsyncLogfireQueryClient,)
```

Their supported result formats include:

| API                 | Result                                            |
| ------------------- | ------------------------------------------------- |
| `query_json_rows()` | Structured column metadata and JSON-oriented rows |
| `query_arrow()`     | `pyarrow.Table`                                   |
| `query_csv()`       | CSV string                                        |
| `info()`            | Read-token information                            |

Unlike the instrumentation API, these methods query already-ingested hosted telemetry and require a Logfire read token.

The v5 query methods require a `min_timestamp` argument. They also support a maximum timestamp, row limit, timezone, and environment filter.

The Arrow result is particularly relevant for analytical processing: it can be passed to `polars.from_arrow()`, or used with other Arrow-compatible tooling.

However, a structured JSON attribute column may be returned as JSON-serialized strings rather than automatically materialized as nested Arrow structs. The Arrow transport avoids manually parsing the whole response format but does not remove every schema interpretation step.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 10.4 PEP 249 / Python DB API compatibility

Logfire also exposes a less obvious integration:

```
import logfire.db_apiwith logfire.db_api.connect(read_token="...") as conn:    cursor = conn.cursor()    cursor.execute(        "SELECT message FROM records "        "WHERE service_name = %(service)s LIMIT 10",        {"service": "api"},    )    rows = cursor.fetchall()
```

`logfire.db_api` presents a Python DB API 2.0-style connection and cursor interface. This supports existing SQL-oriented tooling, including pandas, marimo SQL cells, and notebook SQL integrations, without a custom Logfire query adapter for each tool.

It supports `pyformat` parameters. The documented defaults include a 24-hour query time window and a 10,000-row response limit, both configurable.

This is a read/query integration, not a general-purpose writable SQL database connection.

Cloud queries also have concurrency and daily-budget limits, with `429` responses and `Retry-After` handling when limits are exceeded.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Sources:

[https://pydantic.dev/docs/logfire/manage/query-api/](https://pydantic.dev/docs/logfire/manage/query-api/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/api/query_client/](https://pydantic.dev/docs/logfire/api/query_client/?utm_source=chatgpt.com)

## 11. Hosted investigation, monitoring, and operational workflows

The Logfire backend builds multiple analysis interfaces on the same underlying telemetry.

### 11.1 Live traces and SQL Workbench

The Live View reconstructs span hierarchies and displays logs in their execution context. Trace and span identifiers can connect SQL query results directly to individual execution histories.

The SQL Workbench supports custom queries, aggregations, filtering, joins, and exports.

This allows the same telemetry to support two distinct investigation styles: starting with one anomalous trace and drilling down, or using SQL to find patterns across many executions.

### 11.2 Dashboards and alerts

Dashboards combine SQL-driven visualizations with variables and reusable templates. Standard dashboards include request monitoring, exceptions, LLM token/cost analysis, and system metrics.

Custom dashboards support time series, aggregate values, tables, variables, and JSON-based export/editing.

Alerts evaluate SQL conditions periodically. Their notification modes distinguish persistent results, transitions from zero to nonzero results, and changes in query output. They can be associated with service-level objectives and burn-rate conditions.

This arrangement reduces the need for separate bespoke alerting queries and dashboard-specific aggregation pipelines, but alert correctness remains dependent on instrumentation coverage, query semantics, sampling, and ingestion delay.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



### 11.3 Error tracking

Error Tracking groups recorded exceptions into issues using exception fingerprints, supports status management, and links occurrences back to the original trace evidence.

An error-level message is not enough to create an exception issue. The telemetry must contain actual exception information.

The grouping mechanism is backend functionality; the Python SDK's responsibility is to capture the exception event and relevant execution context.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources:

[https://pydantic.dev/docs/logfire/observe/live/](https://pydantic.dev/docs/logfire/observe/live/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/observe/explore/](https://pydantic.dev/docs/logfire/observe/explore/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/observe/dashboards/](https://pydantic.dev/docs/logfire/observe/dashboards/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/observe/alerts/](https://pydantic.dev/docs/logfire/observe/alerts/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/observe/issues/](https://pydantic.dev/docs/logfire/observe/issues/?utm_source=chatgpt.com)

## 12. Managed variables, prompt configuration, and evaluations

Logfire now includes capabilities beyond passive observability: configuration distribution, AI prompt management, and evaluation workflows.

These are important, but they belong to different architectural layers from the core tracing SDK.

### 12.1 Typed managed variables

`logfire.var()` defines a typed runtime variable with a default value.

With the `variables` integration enabled, the value may come from a hosted configuration, and the application can select versions through labels, targeting keys, and rollout rules.

A Pydantic model can serve as the variable's type, allowing its JSON Schema to define valid remote values.

Notable SDK operations include:

- `variables_push()` — publish variable definitions and schemas.
- `variables_push_types()` — publish reusable variable type definitions.
- `variables_validate()` — detect missing or incompatible remote definitions.
- `variables_build_config()`, `variables_push_config()` — work with fuller programmatic configurations.

Definition synchronization is not the same as version deployment. `variables_push()` synchronizes metadata and schemas but does not create production value versions or labels. The fuller configuration APIs address that separate concern.

A background polling mechanism updates remote state, with a default 60-second interval and SSE-triggered refresh when available. The first-resolution blocking behavior is configurable.

Remote variables require a scoped API key, separate from the write token used for telemetry.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



### 12.2 Deterministic targeting and rollouts

A `targeting_key` determines which configured variant or label a caller receives.

It can be supplied per lookup or inherited through `targeting_context()`. The resolution order distinguishes explicit keys, variable-specific context, general context, and a trace-ID fallback.

This allows one logical variable to resolve consistently for a particular user, tenant, or execution context without routing all decisions through bespoke application configuration logic.

It also makes rollout assignment reproducible. It does not make the execution using that configuration deterministic—for example, LLM outputs can still vary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/manage/managed-variables/remote/](https://pydantic.dev/docs/logfire/manage/managed-variables/remote/?utm_source=chatgpt.com)

Source: [https://pydantic.dev/docs/logfire/manage/managed-variables/targeting/](https://pydantic.dev/docs/logfire/manage/managed-variables/targeting/?utm_source=chatgpt.com)

### 12.3 Versioned prompt management and composition

The hosted Prompt Management system distinguishes:

- A prompt, which is the authorable configuration object.
- An immutable version, preserving the prompt template text.
- A backing managed variable, which determines what is served through labels and rollout rules.
- Scenarios, datasets, and runs, which support testing.

Templates can reference reusable fragments through `@{variable_name}@` and runtime parameters through `{{...}}`.

`logfire.template_var()` resolves variable references and renders templates with typed runtime inputs. By separating version creation from promotion, applications can consume a stable `production` label while prompt authors revise and evaluate new versions.

One important reproducibility limit: a version freezes the template text, not every setting used during model execution. Re-running an old prompt version with changed model parameters or tools is not necessarily a reproduction of the original experiment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+2



Sources:

[https://pydantic.dev/docs/logfire/prompt-management/](https://pydantic.dev/docs/logfire/prompt-management/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/prompt-management/application/](https://pydantic.dev/docs/logfire/prompt-management/application/?utm_source=chatgpt.com)

### 12.4 Datasets, experiments, and evaluations

Logfire's evaluation workspace and the companion `pydantic-evals` library support repeatable evaluation over datasets.

The division of responsibility is:

| Component                         | Responsibility                                             |
| --------------------------------- | ---------------------------------------------------------- |
| `pydantic-evals`                  | Execute cases and evaluators in Python                     |
| Logfire tracing                   | Capture execution evidence and metrics                     |
| Hosted datasets                   | Store and manage reusable cases                            |
| Hosted experiments                | Compare results, errors, scores, duration, usage, and cost |
| `logfire.experimental.api_client` | Manage hosted datasets programmatically                    |

The dataset SDK provides synchronous and asynchronous API clients, typed cases, JSON-schema inference from Pydantic models or dataclasses, and dataset publication and retrieval.

The hosted dataset management SDK is explicitly experimental. It lives under `logfire.experimental.api_client` and requires the `datasets` extra, which brings `pydantic-evals` and HTTP dependencies.

This distinction matters when planning durable automation: the evaluation model is a broader platform capability, while this particular management interface is not presented as a stable API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Sources:

[https://pydantic.dev/docs/logfire/evaluate/datasets-and-experiments/](https://pydantic.dev/docs/logfire/evaluate/datasets-and-experiments/?utm_source=chatgpt.com)

[https://pydantic.dev/docs/logfire/evaluate/datasets-sdk/](https://pydantic.dev/docs/logfire/evaluate/datasets-sdk/?utm_source=chatgpt.com)

## 13. Baggage, span enrichment, and reusable context

OpenTelemetry baggage is a separate propagation mechanism from tracing identity.

Where `traceparent` identifies causal relationships, baggage carries contextual key/value metadata between participating services.

Logfire adds `set_baggage()` and `get_baggage()` and, by default, copies baggage values into attributes on newly created spans.

```
with logfire.set_baggage(workload="reconciliation"):    with logfire.span("Run analysis"):        ...
```

The result is a form of distributed contextual enrichment. A correlation field can become queryable on many descendant spans without each library call explicitly accepting the field.

This can simplify cross-service analysis—such as finding database queries attributable to a workload category—but there are important semantics:

- The OpenTelemetry specification does not itself require baggage to become span attributes. Logfire performs that projection.
- Other SDKs may propagate the baggage correctly without copying its fields onto spans.
- `add_baggage_to_attributes=False` disables this automatic projection without disabling propagation.
- Logfire truncates baggage strings longer than 1,000 characters.

Security caveat: Baggage propagates through HTTP headers, potentially to external services. The transmitted baggage header is not scrubbed, even though copied span attributes undergo ordinary attribute scrubbing. Baggage should not contain credentials, private data, or large payloads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/reference/baggage/](https://pydantic.dev/docs/logfire/reference/baggage/?utm_source=chatgpt.com)

### 13.1 Scoped Logfire instances

Logfire also supports logically scoped instances, useful when different instrumentation families need different presentation or configuration behavior.

`logfire.configure(local=True, ...)` returns a locally configured Logfire instance, rather than replacing the module-level default.

For example, an instance configured with `console=False` can instrument database activity without displaying those database spans in the main console output, while still exporting them to the configured destination.

Related APIs such as `with_tags()` and `with_settings()` provide reusable instrumentation context and settings without requiring every call site to repeat the same metadata.

This offers a middle ground between one entirely global instrumentation policy and manually maintaining independent OpenTelemetry provider stacks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Source: [https://pydantic.dev/docs/logfire/manage/different-configurations/](https://pydantic.dev/docs/logfire/manage/different-configurations/?utm_source=chatgpt.com)

## 14. Configuration, exporters, and OpenTelemetry interoperability

### 14.1 Configuration hierarchy

`logfire.configure()` is the principal integration point for runtime setup.

Configuration is available through:

1. Explicit Python arguments.
2. Environment variables.
3. `pyproject.toml`.

Explicit arguments take precedence over environment variables, which take precedence over the configuration file.

Major configuration dimensions include:

| Dimension                  | Important controls                                                      |
| -------------------------- | ----------------------------------------------------------------------- |
| Service identity           | `service_name`, `service_version`, `environment`, `resource_attributes` |
| Destination                | `send_to_logfire`, `token`, OTLP exporter settings                      |
| Local output               | `console`, `ConsoleOptions`                                             |
| Privacy                    | `scrubbing`, `ScrubbingOptions`                                         |
| Sampling                   | `sampling`, `SamplingOptions`                                           |
| Filtering                  | `min_level`                                                             |
| Metrics                    | `metrics`, `MetricsOptions`                                             |
| Execution context          | `distributed_tracing`, `add_baggage_to_attributes`                      |
| Extension                  | `additional_span_processors`, `advanced`                                |
| Configuration distribution | `variables`, `api_key`                                                  |
| Source provenance          | `code_source`, `CodeSource`                                             |

Operationally, the distinction between the write token, read token, and API key is important. They serve different authorization functions and should not be treated as interchangeable credentials.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Source: [https://pydantic.dev/docs/logfire/manage/configuration/](https://pydantic.dev/docs/logfire/manage/configuration/?utm_source=chatgpt.com)

### 14.2 Alternative OpenTelemetry backends

Logfire can export to alternative OpenTelemetry-compatible systems.

The documented path uses OTLP over HTTP with Protobuf encoding, commonly configured through:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Separate trace, metric, and log endpoints can also be provided.

A critical configuration distinction is that setting an alternative OTLP endpoint does not automatically disable direct export to Logfire:

```
logfire.configure(    send_to_logfire=False,    service_name="processing-service",)
```

This makes Logfire useful as a Python instrumentation and serialization layer even when the telemetry backend is Jaeger, an OpenTelemetry Collector, or another compatible system.

However, the target backend does not necessarily understand Logfire's special representation of logs, pending spans, message templates, or JSON schema metadata. Standard OpenTelemetry transport compatibility does not imply identical UI or query semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/guides/alternative-backends/](https://pydantic.dev/docs/logfire/guides/alternative-backends/?utm_source=chatgpt.com)

### 14.3 Export lifecycle and multi-project delivery

Logfire provides `force_flush()` and `shutdown()` controls, relevant for short-lived processes, scripts, workers, and applications that must coordinate exporter completion before termination.

A successful call to `force_flush()` concerns the configured export pipeline; it should not be interpreted as a blanket guarantee that every downstream database or analysis view has made the telemetry durably queryable.

An additional advanced capability is simultaneous multi-project export. `configure(token=[...])` creates independent export pipelines for the listed project tokens, each with its own HTTP session and processors. Sampling, scrubbing, and baggage transformations are shared before the data is sent to each project.

This supports parallel project migration or verification without duplicating the application's instrumentation calls, but it also multiplies export traffic and destination-level data exposure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Source: [https://pydantic.dev/docs/logfire/reference/migrate-to-new-project/](https://pydantic.dev/docs/logfire/reference/migrate-to-new-project/?utm_source=chatgpt.com)

### 14.4 Source-code provenance

`CodeSource` attaches repository, revision, and source-root information so recorded code locations can link back to source control.

This helps connect an exception or slow operation with the precise deployed revision rather than merely a function name.

The integration is based on source metadata and compatible repository URL conventions, not on Logfire hosting or indexing the source repository itself.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/guides/link-to-code-source/](https://pydantic.dev/docs/logfire/guides/link-to-code-source/?utm_source=chatgpt.com)

## 15. Testing, zero-code instrumentation, and CLI diagnostics

### 15.1 Deterministic instrumentation testing

`logfire.testing` is designed to test telemetry as an application contract rather than sending real data to a hosted observability service.

Its `capfire` fixture exposes captured spans, logs, and metrics.

Particularly useful mechanisms include:

- `TestExporter` for in-memory span collection.
- `exported_spans_as_dict()` for readable, normalized assertions.
- `InMemoryMetricReader` for inspecting recorded metrics.
- `IncrementalIdGenerator` for deterministic trace/span IDs.
- `TimeGenerator` for deterministic timestamps.
- Compatibility with snapshot-based assertions.

The distinction from ordinary application testing is substantial: it allows tests to verify that particular operations produce the expected parent/child relationships, structured attributes, and exception events.

Under pytest, Logfire defaults to `send_to_logfire=False`, reducing accidental export of test data.

This is separate from its pytest integration for observing actual test execution in the Logfire platform.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Source: [https://pydantic.dev/docs/logfire/reference/testing/](https://pydantic.dev/docs/logfire/reference/testing/?utm_source=chatgpt.com)

### 15.2 CLI-driven instrumentation

`logfire run` can launch Python scripts, modules, and installed console commands with automatic instrumentation for detected supported libraries.

```
logfire run script.py
logfire run -m my_module
logfire run --exclude sqlalchemy,fastapi script.py
```

This is different from `install_auto_tracing()`:

| Mechanism                | Scope                                                                            |
| ------------------------ | -------------------------------------------------------------------------------- |
| `logfire run`            | Automatically activates supported package integrations around a launched program |
| `install_auto_tracing()` | Instruments selected Python function definitions at import time                  |
| `@logfire.instrument()`  | Explicitly marks individual functions                                            |
| `logfire.instrument_*()` | Configures specific frameworks or clients                                        |

These mechanisms can complement one another, although overlapping instrumentation must be checked for duplicate spans.

The CLI also provides useful independent diagnostics:

- `logfire inspect` identifies installed libraries that have potentially missing instrumentation dependencies.
- `logfire info` reports Logfire, Python environment, OS, and related package versions.
- `logfire projects status` summarizes recently received telemetry by service, allowing a missing worker or service to be noticed without opening individual traces.
- `logfire prompt` constructs coding-agent investigation prompts using Logfire MCP access.
- `logfire gateway` exposes local authentication/proxy workflows for the Logfire AI Gateway.

Thus the CLI is not only a setup utility; it can help establish whether instrumentation has been installed, initialized, and successfully delivered.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/reference/cli/](https://pydantic.dev/docs/logfire/reference/cli/?utm_source=chatgpt.com)

## 16. Additional platform capabilities and integration boundaries

Several important Logfire capabilities extend beyond passive observation. They are useful to understand, but should not be attributed entirely to the Python instrumentation SDK.

### 16.1 AI Gateway: model routing versus model instrumentation

The Logfire AI Gateway is an optional model-request intermediary. Applications direct requests through the Gateway instead of connecting to each provider directly.

It supports provider-compatible interfaces, centralized key management, spending limits, provider failover, weighted routing, and gateway-generated telemetry.

Its architectural role differs fundamentally from `instrument_openai()` or `instrument_anthropic()`:

| Capability                               | Provider SDK instrumentation       | AI Gateway                       |
| ---------------------------------------- | ---------------------------------- | -------------------------------- |
| Observes model calls                     | Yes                                | Yes, for calls routed through it |
| Sits in the model request path           | No                                 | Yes                              |
| Manages upstream credentials             | No                                 | Yes                              |
| Routes between providers                 | No                                 | Yes                              |
| Controls gateway spending                | No                                 | Yes                              |
| Captures application-side tool execution | Through additional instrumentation | Not inherently                   |

Applications can combine both mechanisms, although correlated telemetry and duplicate model-call spans require attention.

Gateway guardrails provide additional data inspection and protection capabilities. As of the research date, guardrails are beta, while advanced optimizations and spending policies have separate early-access or experimental restrictions. Guardrails apply only to traffic passing through the Gateway, not to all model calls merely observed by Logfire.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/manage/ai-gateway/](https://pydantic.dev/docs/logfire/manage/ai-gateway/?utm_source=chatgpt.com)

### 16.2 Online evaluations and feedback correlation

Logfire's Live Evaluations interface consumes OpenTelemetry `gen_ai.evaluation.result` events, including results emitted by Pydantic AI's `OnlineEvaluation` and function-level `@evaluate` instrumentation.

It groups observations by evaluation target and evaluator identity, supporting numeric, categorical, and pass/fail analysis.

This is distinct from offline dataset evaluation:

- Offline evaluation: Execute known test cases against a candidate behavior, ordinarily before deployment or promotion.
- Online evaluation: Evaluate production executions or collect feedback after real interactions.
- Trace observability: Explain what happened during an execution, irrespective of whether an evaluator judged it successful.

The capabilities compose because evaluation events can be correlated with the trace of the behavior being assessed.

An important advanced mechanism is delayed feedback association. `logfire.get_context()` can capture the context of the original response, and `logfire.attach_context()` can associate later feedback with that execution. When feedback arrives in a separate process or HTTP request, the application must preserve the original context alongside its response identifier.

The telemetry system provides correlation primitives; it does not automatically maintain the application's feedback-to-response identity mapping.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/evaluate/live-evals/](https://pydantic.dev/docs/logfire/evaluate/live-evals/?utm_source=chatgpt.com)

### 16.3 Two distinct MCP capabilities

Logfire's relationship with MCP has two separate directions:

| MCP role                   | Purpose                                                                                              | Owned by                                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `logfire.instrument_mcp()` | Observe MCP clients, servers, tools, and requests                                                    | Python SDK / underlying MCP instrumentation |
| Logfire MCP Server         | Give coding agents access to recorded traces, metrics, queries, alerts, and other platform functions | Logfire service                             |

The second capability enables an engineering agent to investigate production telemetry programmatically rather than manually searching a dashboard.

It is not limited to raw trace retrieval. Documented server tools also provide access to additional operational resources, subject to the authenticated user's permissions.

Security boundary: Recorded telemetry is untrusted diagnostic data. Exceptions, tool outputs, logs, and model responses may contain instructions originating from outside an organization's trusted source code. Agents using the MCP Server should not execute such instructions merely because they appear in a trace.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Source: [https://pydantic.dev/docs/logfire/guides/mcp-server/](https://pydantic.dev/docs/logfire/guides/mcp-server/?utm_source=chatgpt.com)

### 16.4 Cross-language instrumentation and deployment

The broader Logfire ecosystem includes support for TypeScript, Rust, Go, .NET, Java, and other languages through native SDKs or OpenTelemetry integrations.

Browser instrumentation, including session replay, belongs to the separate TypeScript/browser tooling rather than the Python SDK.

The platform supports cloud deployment and enterprise self-hosting arrangements. These should be distinguished from the open-source MIT-licensed Python instrumentation library: obtaining the SDK source does not provide the complete hosted ingestion, SQL, dashboard, and management server implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs+1



Source: [https://pydantic.dev/docs/logfire/deploy/enterprise/](https://pydantic.dev/docs/logfire/deploy/enterprise/?utm_source=chatgpt.com)

The separate infrastructure-as-code integration can manage Logfire resources such as projects, tokens, alerts, and dashboards through Terraform/OpenTofu. This is a platform administration capability, not a Python runtime feature.

Source: [https://pydantic.dev/docs/logfire/manage/infrastructure-as-code/](https://pydantic.dev/docs/logfire/manage/infrastructure-as-code/?utm_source=chatgpt.com)

## 17. Package requirements, optional dependencies, and release boundaries

### 17.1 Logfire 5.4.0

The verified current stable distribution is `logfire` 5.4.0.

| Property             | Verified status                                 |
| -------------------- | ----------------------------------------------- |
| Python requirement   | Python 3.10 or newer                            |
| License              | MIT                                             |
| Stable release       | 5.4.0, October 26, 2026                         |
| Install distribution | `logfire`                                       |
| Python import        | `import logfire`                                |
| Runtime foundation   | OpenTelemetry SDK and instrumentation ecosystem |
| Platform backend     | Separate from the open-source Python SDK        |

The distribution exposes numerous optional extras, including `fastapi`, `httpx`, `sqlalchemy`, `psycopg`, `asyncpg`, `celery`, `redis`, `system-metrics`, `datasets`, `variables`, `gateway`, and `agent-sandboxes`.

These extras matter because they determine whether particular integrations and their dependencies are available. They do not imply that importing the library automatically activates every supported instrumentation package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Source: [https://pypi.org/project/logfire/](https://pypi.org/project/logfire/?utm_source=chatgpt.com)

### 17.2 New in 5.4: agent sandboxes

Version 5.4.0 introduces `logfire.agent_sandboxes()`.

This is a separate capability from ordinary observability: it provides an integration with Pydantic's Monty-based agent sandbox infrastructure and its client library.

It can give an agent execution system access to sandboxed execution sessions while integrating their activity with Logfire.

The `agent-sandboxes` extra identifies the relevant optional dependency family.

Because this is a newly released interface, the precise sandbox resource guarantees, execution security model, quotas, and backend availability should be established from the corresponding sandbox documentation rather than inferred from the Logfire API alone. In particular, instrumenting a sandbox does not itself establish an isolation guarantee.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/pydantic/logfire/releases/tag/v5.4.0](https://github.com/pydantic/logfire/releases/tag/v5.4.0?utm_source=chatgpt.com)

### 17.3 Logfire 6 beta

The 6.0 prerelease series separates the distribution into:

- `logfire-sdk` — the Python instrumentation package.
- `logfire-cli` — the command-line tooling.
- `logfire` — a compatibility distribution installing both and preserving the existing import interface.

This changes installation and dependency composition, especially for deployments that do not need the CLI.

As of November 1, 2026, 6.0.0b8 is a prerelease, not the stable target of this overview. Development-branch documentation and examples may expose functionality or packaging behavior that should not be assumed present in 5.4.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Source: [https://github.com/pydantic/logfire/releases](https://github.com/pydantic/logfire/releases?utm_source=chatgpt.com)

A version-specific clarification to §2.4: ordinary `@logfire.instrument()` does not require accessible source code in Logfire 5.x; that restriction was removed in Logfire 2.0. Source availability remains relevant to automatic import-time tracing and source-aware f-string inspection.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 18. Architectural interactions and important limitations

The following distinctions are particularly consequential when using Logfire as a component in larger systems.

| Interaction                                        | Capability enabled                                                        | Boundary or tradeoff                                                                                 |
| -------------------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Framework + HTTP client + database instrumentation | End-to-end request and dependency tracing                                 | Requires appropriate context propagation and avoids duplicated instrumentors                         |
| Pydantic validation + structured spans             | Connect validation failures to the operation that produced them           | Model-definition timing, capture policies, and sensitive inputs matter                               |
| Agent instrumentation + model SDK + MCP tools      | Observe model decisions and their actual downstream effects               | Different integrations capture different portions of execution                                       |
| Head + tail sampling                               | Reduce telemetry volume while prioritizing informative executions         | Discarded data cannot be reconstructed; distributed completeness is limited                          |
| Metrics aggregated inside spans                    | Attribute resource and token usage to an operation                        | Experimental and process-local, not an arbitrary distributed aggregation system                      |
| Managed variables + prompt versions + evaluations  | Relate configuration changes to observed quality and cost                 | Remote configuration, versioning, and evaluation have separate identities and lifecycles             |
| OTLP + alternative backend                         | Reuse the Python instrumentation stack without the hosted Logfire service | Backend-specific Logfire representations and analysis features may not transfer                      |
| Query API + Arrow + SQL                            | Analyze telemetry using external analytical applications                  | Hosted read access, query limits, serialized nested attributes, and ingestion timing remain relevant |
| Baggage + distributed traces                       | Attach cross-service context to a causal workflow                         | Propagated headers can expose values to other services                                               |
| OpenTelemetry Collector + central scrubbing        | Enforce shared telemetry transformations across heterogeneous services    | All export paths must pass through the intended control point                                        |

### 18.1 The greatest distinction: instrumentation completeness versus evidence completeness

Logfire can capture a large amount of application behavior automatically, but several independent mechanisms determine whether a complete explanation of an execution survives:

1. Was the relevant operation instrumented?
2. Was its causal context propagated correctly?
3. Did sampling retain the necessary spans?
4. Did attribute filtering or scrubbing remove needed detail?
5. Did the process successfully export its telemetry?
6. Did the receiving backend preserve and expose the required semantics?

A gap at any layer can make a trace incomplete even when the application itself executed successfully.

This distinction is critical when interpreting absence of evidence. No observed error, query, or tool call does not necessarily mean none occurred.

### 18.2 Structured state capture versus application-state persistence

Logfire can serialize complex objects and attach meaningful values to execution events. That makes it powerful for diagnostics, comparison, and retrospective analysis.

It is not a replacement for a transactional domain database, persistent workflow state machine, durable message queue, or application event ledger.

A trace describes observed execution. An authoritative domain record establishes the state and consistency guarantees of the underlying system.

The two can complement one another through shared identifiers, but OpenTelemetry spans do not inherit transactional durability simply because they contain structured application data.

### 18.3 Performance: where the costs arise

Logfire's runtime costs arise from several different activities:

- Wrapping functions and framework operations.
- Constructing spans and handling execution context.
- Inspecting source expressions and serializing Python objects.
- Creating rich exception or payload attributes.
- Running sampling, scrubbing, and span processors.
- Buffering and exporting telemetry.
- Increasing storage and query cardinality in the backend.

These costs are not equivalent.

For example, head sampling can avoid significant recording work for rejected traces, whereas tail sampling may still require buffering and processing the spans under consideration. Capturing complete LLM messages or large Python objects changes both serialization expense and exported data volume, even when the number of spans remains constant.

Similarly, collecting a latency histogram is different from recording a span for every operation. Metrics generally exchange per-event diagnostic detail for efficient aggregation.

The appropriate level of instrumentation depends on the information required and on which costs dominate the execution being observed. The official documentation does not establish a single overhead figure that should be applied indiscriminately to arbitrary workloads.

### 18.4 Extension points worth understanding

For advanced integrations, Logfire exposes several meaningful extension seams:

- OpenTelemetry samplers: Customize early inclusion policies.
- Tail-sampling callbacks: Retain traces based on observed execution properties.
- Span processors and exporters: Extend or redirect telemetry handling.
- Scrubbing callbacks: Customize sensitive-data treatment.
- Custom metrics: Represent quantitative domain properties without one-off collection pipelines.
- OpenTelemetry instrumentation packages: Add support for libraries without native Logfire integration.
- Custom spans and span links: Represent execution boundaries or relationships not inferred automatically.
- Scoped Logfire instances: Apply locally differentiated instrumentation behavior.
- Query APIs and DB API adapters: Analyze observations in external Python and SQL tooling.
- Managed-variable schemas and targeting: Connect typed runtime configuration with controlled distribution.

These extension points operate at different layers. An OpenTelemetry processor transforms telemetry; a Logfire SQL query analyzes ingested telemetry; a managed variable changes runtime configuration. Keeping those responsibilities separate helps avoid using an observability mechanism to solve a persistence or coordination problem it does not guarantee.

## 19. Overall technical assessment

Pydantic Logfire's most distinctive value is not an individual logging method or dashboard. It is the combination of Python-native structured instrumentation, OpenTelemetry execution context, broad library integration, SQL-queryable telemetry, and specialized AI execution analysis.

Several capabilities deserve particular attention because they can displace substantial custom diagnostic machinery:

- Automatic and selective instrumentation across application code and third-party libraries.
- Rich structured object capture that makes runtime values available for analysis without designing a separate serializer for every diagnostic event.
- Causal trace composition across web requests, databases, asynchronous workers, model calls, and MCP tools.
- DataFusion-backed SQL and Arrow query interfaces that make telemetry accessible to general analytical tooling.
- Agent and evaluation integration that connects execution behavior, cost, configuration, and measured output quality.
- Standard OpenTelemetry integration that preserves useful interoperability even when the Logfire backend is not the chosen destination.

Its principal constraints are equally important: instrumentation and sampling do not imply complete observation; detailed capture increases security and runtime obligations; some advanced features are experimental or platform-dependent; and OpenTelemetry compatibility does not guarantee preservation of every Logfire-specific representation or analysis feature.

The library is therefore best understood as a Python-oriented observability and execution-analysis layer built on OpenTelemetry, with optional hosted capabilities extending into query analytics, AI evaluation, and managed configuration—not as a replacement for application-state persistence or an independently complete distributed execution framework.

This overview is based on the released 5.4.0 package, official documentation, upstream release history, and source-level references. Examples are illustrative and were not executed.