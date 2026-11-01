# OpenTelemetry for Python — Comprehensive Technical Reference

Research date: October 24, 2026 | OpenTelemetry Python 1.45.1 | Instrumentation series 0.66b1

## 1. Executive orientation

OpenTelemetry (OTel) is a vendor-neutral observability framework that provides a common programming model for producing, contextualizing, processing, and exporting telemetry from applications and infrastructure.

Its Python implementation offers considerably more than automatic tracing or application logging. It provides a composable observability architecture encompassing distributed execution traces, quantitative measurements, structured logs, context propagation, standardized telemetry semantics, configurable collection and export pipelines, and framework-level instrumentation.

The core architectural opportunity is to express observability through reusable instrumentation and common telemetry primitives rather than constructing separate diagnostic systems for different libraries, execution stages, and infrastructure components.

OpenTelemetry does not itself provide a complete observability database, query engine, profiler, or visualization platform. Its responsibility is to produce and transport semantically meaningful telemetry. Collectors and observability backends handle downstream processing, storage, analysis, and visualization.

### Version and maturity

The current Python core release is 1.45.1, published October 6, 2026. The corresponding experimental package series is 0.66b1. The OpenTelemetry Python Contrib repository's latest listed coordinated release is 0.66b0, while individual instrumentation packages such as `opentelemetry-instrumentation` have published 0.66b1.

The official Python project reports the following maturity:

| Signal              | Status                                      | Scope                                                                     |
| ------------------- | ------------------------------------------- | ------------------------------------------------------------------------- |
| Distributed tracing | Stable                                      | Span creation, trace context, sampling, processors, exporters             |
| Metrics             | Stable                                      | Instruments, aggregation, views, readers, exporters                       |
| Logs                | Development                                 | Structured log records, Python logging integration, processing and export |
| Profiling           | Not supported as a native Python SDK signal | Separate profiling tools and integrations required                        |

The Python implementation supports Python 3.10 and later, including Python 3.14.

The development status of the logging signal matters: log SDK interfaces can undergo incompatible changes even while tracing and metrics APIs have stronger stability guarantees.

Primary sources:

- Python implementation and signal status: [https://opentelemetry.io/docs/languages/python/](https://opentelemetry.io/docs/languages/python/?utm_source=chatgpt.com)
- Core releases and changes: [https://github.com/open-telemetry/opentelemetry-python/releases](https://github.com/open-telemetry/opentelemetry-python/releases?utm_source=chatgpt.com)
- Core SDK package: [https://pypi.org/project/opentelemetry-sdk/](https://pypi.org/project/opentelemetry-sdk/?utm_source=chatgpt.com)
- Instrumentation package: [https://pypi.org/project/opentelemetry-instrumentation/](https://pypi.org/project/opentelemetry-instrumentation/?utm_source=chatgpt.com)

### Capability map

| Capability family           | Main mechanisms                                                           | Architectural value                                                                          |
| --------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Distributed tracing         | Tracers, spans, links, events, status, sampling                           | Reconstruct execution and causal relationships across functions, services, and processes     |
| Metrics                     | Counters, gauges, histograms, asynchronous instruments                    | Measure throughput, latency distributions, resource utilization, and operational state       |
| Metrics processing          | Views, aggregations, exemplars, temporality, cardinality limits           | Control measurement semantics, memory consumption, dimensionality, and export behavior       |
| Structured logging          | Logger providers, handlers, processors, correlated records                | Connect detailed diagnostic events to distributed execution context                          |
| Context propagation         | W3C Trace Context, baggage, context attachment                            | Preserve execution identity across asynchronous tasks, service calls, and message boundaries |
| Automatic instrumentation   | Instrumentors, framework hooks, startup instrumentation                   | Capture common operations without implementing every span or metric manually                 |
| Semantic conventions        | Standard attributes, names, units, schemas                                | Make telemetry from independent libraries comparable and interoperable                       |
| Export architecture         | OTLP, exporters, batching, metric readers                                 | Decouple application instrumentation from observability infrastructure                       |
| Extensibility               | Custom samplers, processors, exporters, instrumentors, resource detectors | Support application-specific telemetry requirements through standard interfaces              |
| Configuration and lifecycle | Environment settings, declarative configuration, flush/shutdown           | Centralize observability policy and telemetry resource management                            |

The following sections develop these capabilities, their interactions, advanced mechanisms, and consequential limitations.

## 2. Architecture and Python package ecosystem

### 2.1 API, SDK, instrumentation, and backend are separate layers

The most important design distinction in OpenTelemetry is the separation between instrumentation semantics and telemetry collection policy.

Application code and instrumented libraries

Operations, measurements, exceptions, execution context

OpenTelemetry API

Tracers, meters, loggers, context, propagation

OpenTelemetry Python SDK

Providers · resources · samplers · views · processors · readers

Exporters and OTLP

Serialization, batching, transport, retries

Collector → Storage / Analysis / Visualization

Processing, routing, retention, querying and dashboards

Conceptual architecture. The Collector is optional; applications can also export directly to a compatible backend.

The layers have distinct responsibilities.

| Layer/package                        | Responsibility                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------- |
| `opentelemetry-api`                  | Public, implementation-independent interfaces for telemetry creation and context management |
| `opentelemetry-sdk`                  | Concrete tracing, metrics, and logging implementations, including recording and processing  |
| `opentelemetry-semantic-conventions` | Python constants for standardized names and attributes                                      |
| `opentelemetry-exporter-otlp`        | Convenience distribution for OTLP protobuf gRPC and HTTP exporters                          |
| `opentelemetry-instrumentation`      | Startup instrumentation infrastructure and discovery                                        |
| `opentelemetry-distro`               | Default distribution and configuration for automatic instrumentation                        |
| `opentelemetry-instrumentation-*`    | Integrations with individual frameworks and libraries                                       |
| `opentelemetry-propagator-*`         | Additional distributed-context propagation formats                                          |
| `opentelemetry-configuration`        | Experimental declarative SDK configuration                                                  |
| OpenTelemetry Collector              | Separate process/service for telemetry reception, processing, routing, and export           |

The Collector is not a Python library and is not a prerequisite for the SDK. Likewise, exporting a span does not imply that any backend has stored or indexed it.

### 2.2 The instrumentation-library contract

A particularly valuable capability is that third-party libraries can depend only on `opentelemetry-api`.

An instrumented library obtains a tracer or meter and emits telemetry through the abstract API. Its caller determines whether an SDK is installed, how sampling works, what telemetry gets exported, and where it goes.

Without an SDK, the API provides no-op behavior rather than requiring the library to implement observability configuration itself.

This permits:

- One instrumentation implementation to work with different SDK configurations.
- Libraries to expose trace and metric semantics without binding themselves to an observability vendor.
- Application-level policy to control collection without modifying each library.
- Composition of application-created telemetry with telemetry from independent dependencies.

This is an important route to reducing bespoke observability code: libraries describe their operations; the application or deployment determines the observability policy.

### 2.3 Providers, scopes, and resources

Three concepts form the foundation of telemetry identity.

| Concept               | Meaning                                          | Example                                             |
| --------------------- | ------------------------------------------------ | --------------------------------------------------- |
| Provider              | Configured implementation for producing a signal | `TracerProvider`, `MeterProvider`, `LoggerProvider` |
| Instrumentation scope | Which library or module generated the telemetry  | `payment.worker`, version `2.1`                     |
| Resource              | Which entity generated the telemetry             | Service, instance, deployment, host, runtime        |

A tracer obtained with `trace.get_tracer("package.module", "1.2.0")` carries an instrumentation scope. The SDK provider can attach a shared resource such as `service.name`, `service.version`, or `service.instance.id`.

Scopes and resources are orthogonal. Hundreds of instrumented modules may emit telemetry associated with the same service resource, while different instances of a service share instrumentation-scope names.

This distinction supports filtering and analysis by both logical operation ownership and physical deployment identity.

### 2.4 Initialization and global providers

Python exposes global provider facilities, but providers may also be supplied explicitly to instrumentors and application components.

Global initialization is convenient because independently instrumented libraries can all discover the same SDK. However, global provider installation is designed around one-time setup, not arbitrary replacement.

Important implications:

- Provider configuration belongs near process initialization.
- SDK startup and framework instrumentation initialization are different operations.
- A provider should not be recreated for each request or task.
- Explicit provider injection can be useful for tests or isolated library instances.
- Existing instrumentors and exported telemetry do not automatically transfer between independently created providers.

Source: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/index.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/index.html?utm_source=chatgpt.com)

## 3. Distributed tracing

Tracing is the most immediately expressive OpenTelemetry signal for reconstructing application execution.

A trace represents a causally related set of operations. Each operation is described by a span.

### 3.1 Span data model

A span contains more than a function name and elapsed time.

| Component                      | Function                                                              |
| ------------------------------ | --------------------------------------------------------------------- |
| Trace ID                       | Identifies a distributed trace                                        |
| Span ID                        | Identifies the individual operation                                   |
| Parent span context            | Establishes the execution hierarchy                                   |
| Name                           | Human-meaningful operation identifier                                 |
| Kind                           | `INTERNAL`, `SERVER`, `CLIENT`, `PRODUCER`, or `CONSUMER`             |
| Start/end timestamps           | Operation timing                                                      |
| Attributes                     | Typed dimensions describing the operation                             |
| Events                         | Timestamped annotations within the span                               |
| Links                          | Associations with other spans that are not parent-child relationships |
| Status                         | `UNSET`, `OK`, or `ERROR`                                             |
| Instrumentation scope/resource | Source of instrumentation and entity responsible for telemetry        |

Trace IDs are 128-bit identifiers; span IDs are 64-bit identifiers. Their principal role is correlation, not guaranteeing global operation uniqueness through a central allocator.

### 3.2 Span creation and lifecycle

Two important APIs are:

- `Tracer.start_as_current_span()` — creates a span and activates it in the current execution context.
- `Tracer.start_span()` — creates a span without automatically making it current.

Current-span activation enables downstream instrumented code to discover the appropriate parent automatically. Manual activation is available through `trace.use_span()`.

A span does not have to correspond to a Python function. It may represent a request, database operation, stage of a pipeline, external service invocation, retry attempt, or other meaningful unit of work.

This allows tracing to express the application's logical execution model rather than reproducing the call stack indiscriminately.

### 3.3 Span events versus child spans versus links

These constructs convey substantially different information.

| Construct  | Meaning                                             | Appropriate use                               |
| ---------- | --------------------------------------------------- | --------------------------------------------- |
| Child span | Nested operation with its own duration and context  | A database call made within a request         |
| Span event | Timestamped occurrence during an existing operation | Retry scheduled, checkpoint reached           |
| Span link  | Causal association without hierarchical ownership   | Batch fan-in, queue consumption, derived work |

Span links are especially important for non-tree execution graphs.

Consider a batch processor that consumes messages produced by several independent requests. Making every source span a parent is impossible because a span has at most one parent. Links allow the batch-processing span to reference multiple contributing contexts.

Likewise, an asynchronous task can be causally related to an initiating request without being a straightforward synchronous child.

Links can be supplied during span creation, which is also significant because samplers can examine them when making their decision.

Span events are suitable for bounded, meaningful annotations. They are not an unlimited substitute for structured logging or a high-volume event stream.

### 3.4 Exception and status semantics

OpenTelemetry distinguishes recording an exception from classifying the operation as failed.

`span.record_exception(exc)` records exception information as a span event. `span.set_status(Status(StatusCode.ERROR))` explicitly describes the operation outcome.

An exception may be handled successfully within an operation, so automatically treating every exception event as an operation failure can misrepresent application semantics.

The tracing context managers support automatic exception recording and status behavior, subject to their configuration.

For richer diagnostics, spans may also carry operation-specific outcome attributes, retry counts, error categories, and other low-cardinality dimensions.

### 3.5 Sampling: more than a percentage

Sampling is performed at span creation in the Python SDK.

Built-in and extensible mechanisms include:

| Sampler               | Behavior                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------- |
| `ALWAYS_ON`           | Record and sample all spans                                                                  |
| `ALWAYS_OFF`          | Drop all spans                                                                               |
| `TraceIdRatioBased`   | Deterministic, trace-ID-based probability selection                                          |
| `ParentBased`         | Select delegates according to the existence and sampled state of local or remote parents     |
| `AlwaysRecordSampler` | Preserve recording for processor use even when a delegate would normally drop the span       |
| Custom `Sampler`      | Make decisions from trace ID, initial attributes, span kind, name, links, and parent context |

The default configuration is parent-based, with an always-on root sampler.

There are three distinct sampling decisions:

DROP

No recording

RECORD_ONLY

Local processing

RECORD_AND_SAMPLE

Processing + export

The 1.45 series adds the stable `AlwaysRecordSampler`, which deserves particular attention.

It wraps another sampler and converts `DROP` decisions to `RECORD_ONLY`. Consequently, span processors can receive information from operations that will not be exported as sampled traces.

This opens an important architectural option: derive complete local metrics from recorded spans while exporting only a sampled subset of traces.

For example, a span processor can aggregate durations or failure counts across all completed operations, while the trace exporter sends only selected diagnostic traces.

The cost is that unsampled operations still incur span-recording and processor overhead. `RECORD_ONLY` is not equivalent to a no-op span.

#### Head versus tail sampling

The Python SDK performs head sampling: its decision is based on information available when the span starts.

Tail sampling occurs after more of the trace is available, commonly in the OpenTelemetry Collector. It can consider completed duration, errors, or other downstream facts.

These approaches are complementary but not interchangeable. A Collector cannot recover spans that the Python SDK never recorded or exported.

Also, the upstream tracing specification now marks `TraceIdRatioBased` as deprecated in favor of newer probability-sampling mechanisms. The Python 1.45.1 API still documents and supports `TraceIdRatioBased`; specification-level replacements must not be assumed to have equivalent released Python implementations.

### 3.6 Span processors and interception

A `SpanProcessor` receives hooks around span start and completion.

These hooks permit functionality such as:

- Transforming or filtering spans before export.
- Computing operation metrics from span information.
- Enriching telemetry from contextual metadata.
- Performing custom local diagnostics.
- Routing completed spans to multiple exporters.

The Python SDK provides `SimpleSpanProcessor`, `BatchSpanProcessor`, and multi-processor implementations.

`SimpleSpanProcessor` exports synchronously. `BatchSpanProcessor` queues completed spans for background batch export, reducing exporter work on the operation-completion path.

The SDK also contains `SynchronousMultiSpanProcessor` and `ConcurrentMultiSpanProcessor`. The latter invokes its underlying processors through a thread pool and waits for them to finish. It is not an unlimited asynchronous fire-and-forget mechanism.

Processor hooks are invoked in the application's execution path; expensive or blocking hooks can therefore affect latency.

### 3.7 Span limits and bounded telemetry

`SpanLimits` and corresponding environment settings control the maximum numbers of attributes, events, links, and associated values.

Bounding these quantities matters because tracing can otherwise become a source of unbounded memory consumption during failure storms, unusually large requests, or deeply instrumented operations.

The SDK tracks discarded information, but limits also imply information loss. A trace with its critical events truncated is not a complete execution record.

This becomes a correctness consideration when traces are used for auditing, not merely performance analysis.

Primary tracing references

- Trace API: [https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html?utm_source=chatgpt.com)
- Trace SDK and processors: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html?utm_source=chatgpt.com)
- Sampling implementation: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.sampling.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.sampling.html?utm_source=chatgpt.com)
- Sampling specification: [https://opentelemetry.io/docs/specs/otel/trace/sdk/](https://opentelemetry.io/docs/specs/otel/trace/sdk/?utm_source=chatgpt.com)
- Python tracing examples: [https://opentelemetry.io/docs/languages/python/instrumentation/](https://opentelemetry.io/docs/languages/python/instrumentation/?utm_source=chatgpt.com)

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+4



## 4. Metrics: collection, aggregation, and analytical structure

OpenTelemetry Metrics is not merely a collection of counters. It provides a programmable measurement and aggregation model in which instrumentation can remain stable while downstream aggregation changes.

### 4.1 Instruments and measurement semantics

| Instrument                | Recording model        | Important semantics                                 |
| ------------------------- | ---------------------- | --------------------------------------------------- |
| `Counter`                 | Synchronous `add()`    | Monotonically increasing count                      |
| `UpDownCounter`           | Synchronous `add()`    | Values can increase or decrease                     |
| `Histogram`               | Synchronous `record()` | Distribution of observed values                     |
| `Gauge`                   | Synchronous `set()`    | Most recently recorded measurement                  |
| `ObservableCounter`       | Collection callback    | Cumulative observed count                           |
| `ObservableUpDownCounter` | Collection callback    | Observed quantity that can move in either direction |
| `ObservableGauge`         | Collection callback    | Current observed state                              |

The distinction between synchronous and observable instruments is fundamental.

Synchronous instruments record measurements as operations happen. Observable instruments execute callbacks during collection, retrieving current values from existing application state.

A synchronous histogram is suitable for observing each completed operation duration. An observable gauge is more suitable when the application already maintains authoritative state, such as the current queue depth or number of active workers.

An observable instrument can avoid duplicating the application's underlying state in a separate metric counter.

### 4.2 Why histograms matter

A histogram preserves distribution information that a scalar average cannot.

A latency average of 100 milliseconds does not establish whether nearly all operations are close to 100 milliseconds or whether most complete instantly while a minority take several seconds.

The SDK supports two major histogram aggregations:

Explicit-bucket histograms assign measurements to configured boundaries. They are useful when known service-level thresholds or standardized buckets matter.

Exponential histograms use a base-2 exponential bucket structure. They are useful when measurements span large ranges or when relatively fine distribution resolution is desirable without hand-maintaining numerous explicit boundaries.

The SDK exposes `ExplicitBucketHistogramAggregation` and `ExponentialBucketHistogramAggregation`, including options for minimum/maximum values and histogram resolution.

These are alternatives, not simply differently named output formats.

Aggregation choice affects storage, resolution, compatibility, and the interpretation of downstream queries.

In 1.45.0, the SDK also tightened important numerical correctness behavior: non-finite measurements are discarded, explicit histogram boundaries must be strictly increasing and finite, and exponential-bucket aggregation is explicitly rejected for asynchronous instruments rather than silently generating no data.

### 4.3 Views: the most consequential advanced metrics capability

A `View` selects instruments and controls the metric streams derived from their measurements.

Views can match by:

- Instrument name or type.
- Meter name and version.
- Meter schema URL.
- Instrument unit.

They can then change the emitted metric stream's name, description, included attribute keys, aggregation, and exemplar-reservoir behavior.

This means the instrumentation and the desired statistical representation do not have to be encoded together.

For example, one generic duration histogram instrument can support different metric aggregation policies without modifying its instrumentation calls.

Important View capabilities include:

| Feature                                 | Effect                                            |
| --------------------------------------- | ------------------------------------------------- |
| `attribute_keys`                        | Keep only selected dimensions                     |
| `DropAggregation`                       | Discard measurements for matched instruments      |
| `SumAggregation`                        | Aggregate into sums                               |
| `LastValueAggregation`                  | Retain latest measurements                        |
| `ExplicitBucketHistogramAggregation`    | Define explicit bucket boundaries                 |
| `ExponentialBucketHistogramAggregation` | Define adaptive exponential buckets               |
| `exemplar_reservoir_factory`            | Customize which example observations are retained |

Views can also create multiple metric streams from one instrument when multiple views match.

That can be powerful—for example, retaining both a coarse low-cardinality service metric and a more detailed metric—but it can also increase collection cost and memory use.

#### Cardinality control

Metric cardinality is the number of distinct attribute combinations for which the SDK maintains measurement state.

A metric with a few attribute keys can still create very large numbers of streams if those keys contain request IDs, unique paths, user identifiers, or other effectively unbounded values.

Views are particularly useful because they permit cardinality reduction at the SDK aggregation layer rather than relying solely on backend-side filtering.

In addition, the SDK implements cardinality limits, with overflowing attributes mapped to bounded overflow behavior.

There is an important distinction between dropping an attribute before aggregation and discarding it later at an exporter or Collector: earlier filtering prevents the SDK from maintaining the unwanted set of distinct streams.

### 4.4 MetricReaders and temporality

A `MetricReader` defines how aggregated metrics are collected.

The two major patterns are:

| Pattern        | Implementation                  | Behavior                                     |
| -------------- | ------------------------------- | -------------------------------------------- |
| Periodic push  | `PeriodicExportingMetricReader` | Collects and exports at configured intervals |
| On-demand pull | `PrometheusMetricReader`        | Collects when a Prometheus scrape occurs     |

The SDK supports multiple readers attached to the same `MeterProvider`. Readers can specify preferred aggregation and temporality.

Cumulative temporality represents values accumulated since a starting point. Delta temporality represents changes over successive collection periods.

This difference is especially consequential for sums and histograms. A backend expecting deltas cannot necessarily interpret cumulative values as interchangeable without conversion and reset handling.

Since version 1.43.0, the SDK also exposes public `add_metric_reader()` and `remove_metric_reader()` methods, making reader registration and removal available at runtime.

This supports dynamic metrics destinations and collection arrangements, although reader lifecycle and collection-state management remain necessary.

### 4.5 Exemplars: connecting distributions to traces

Exemplars attach representative individual measurements, potentially including trace and span identifiers, to aggregated metric data.

For a latency histogram, an exemplar can connect a particular distribution observation to the trace that produced it.

OpenTelemetry Python provides:

- `TraceBasedExemplarFilter`
- `AlwaysOnExemplarFilter`
- `AlwaysOffExemplarFilter`
- Exemplar reservoirs, including fixed-size sampling implementations
- Custom exemplar-reservoir factories through Views

This creates a natural bridge between quantitative observability and execution-level diagnostics.

For example, a high-percentile latency metric can supply an exemplar associated with a concrete slow operation, allowing investigation of the corresponding trace.

Exemplars do not guarantee that every measurement has an associated retained and queryable trace. That depends on sampling, reservoir selection, exporter support, and backend storage.

### 4.6 Metric semantics and numerical correctness

Metric instruments are not interchangeable containers for numbers.

A counter assumes monotonic growth. An up/down counter represents an additive, potentially decreasing quantity. A gauge represents a measured state. A histogram describes a distribution.

Confusing these creates semantic errors that downstream aggregation cannot always correct.

For example, using a gauge to represent event throughput loses the additive information required to calculate reliable rates over time.

Equally, a metric stream's identity includes its relevant attributes and instrumentation context. Python's ordinary value equivalence is not sufficient to define OpenTelemetry metric attribute identity: the 1.45 SDK distinguishes values such as `True`, `1`, and `1.0` when forming streams.

Primary metrics references

- Metrics API: [https://opentelemetry-python.readthedocs.io/en/latest/api/metrics.html](https://opentelemetry-python.readthedocs.io/en/latest/api/metrics.html?utm_source=chatgpt.com)
- Metrics SDK: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.html?utm_source=chatgpt.com)
- Views and aggregations: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.view.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.view.html?utm_source=chatgpt.com)
- Metrics specification: [https://opentelemetry.io/docs/specs/otel/metrics/sdk/](https://opentelemetry.io/docs/specs/otel/metrics/sdk/?utm_source=chatgpt.com)
- Prometheus exporter: [https://opentelemetry-python.readthedocs.io/en/latest/exporter/prometheus.html](https://opentelemetry-python.readthedocs.io/en/latest/exporter/prometheus.html?utm_source=chatgpt.com)

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+5



Release clarification: The Contrib repository also has a verified `v0.66b1` tag dated October 6, 2026. Its GitHub release listing is not consistently surfaced in the general releases index, but the direct release page confirms it. This supersedes the earlier statement that `0.66b0` was the latest Contrib release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 5. Structured logging and log correlation

OpenTelemetry's logging architecture is designed to preserve structured diagnostic information and associate it with traces, resources, and instrumentation scopes.

For Python, the most consequential integration is with the standard-library `logging` framework. OpenTelemetry does not require replacing ordinary application loggers with a separate logging API.

### 5.1 Logging architecture

The logging signal has its own pipeline:

`logging.LogRecord → OpenTelemetry log record → LogRecordProcessor → LogExporter`

Important components include `LoggerProvider`, OpenTelemetry loggers, `LoggingHandler`, `SimpleLogRecordProcessor`, `BatchLogRecordProcessor`, and corresponding exporters.

An OpenTelemetry log record supports fields such as body, timestamp, observed timestamp, severity, attributes, trace ID, span ID, and resource information. This provides a common representation even when logs originate in different libraries.

The structured log body and attributes are particularly useful for diagnostics: meaningful fields can remain independently queryable instead of being embedded into a formatted text string.

### 5.2 Standard logging integration: two distinct functions

The `opentelemetry-instrumentation-logging` package supports two related but different activities:

1. Log collection: install a handler that converts standard Python log records into OpenTelemetry log records for processing and export.
2. Trace-context injection: enrich Python log records with the current trace and span identifiers so conventional log formats or handlers can correlate messages with traces.

These features do not necessarily have to be enabled together.

The integration exposes `LoggingInstrumentor`, `inject_trace_context=True`, and `set_logging_format=True`. The latter can call `logging.basicConfig()` to install an OpenTelemetry-aware format, but existing logging configuration may prevent that call from taking effect.

The current instrumentation package installs its OpenTelemetry logging handler by default when enabled through auto-instrumentation. `OTEL_PYTHON_LOG_AUTO_INSTRUMENTATION=false` disables that behavior; trace-context injection into ordinary log records remains opt-in.

A significant recent compatibility detail: the SDK's older `opentelemetry.sdk._logs.LoggingHandler` is deprecated in favor of the handler supplied by `opentelemetry-instrumentation-logging`.

### 5.3 Logging versus span events

Both log records and span events can describe occurrences within an operation, but they serve different purposes.

| Mechanism   | Characteristics                                                                   |
| ----------- | --------------------------------------------------------------------------------- |
| Span event  | Belongs to a particular span; suitable for bounded trace annotations              |
| Log record  | Independent structured diagnostic record; can include trace/span correlation      |
| Span status | Describes overall operation outcome rather than individual diagnostic occurrences |
| Metric      | Aggregated or sampled quantitative representation rather than an event narrative  |

For frequently occurring diagnostics, logs can be more appropriate than adding many span events. For a small number of significant lifecycle transitions, span events provide direct trace visibility.

OpenTelemetry's separate experimental Events API was removed in Python 1.44.0; named events can instead be represented through log records and their `event_name` field. This is distinct from `Span.add_event()`, which remains part of tracing.

### 5.4 Advanced log processing

Log processors permit filtering, transformation, enrichment, and exporter routing.

The SDK supports batching and multi-processor composition, including synchronous and concurrent multi-processor implementations. A separate log-processing pipeline can be used for each destination.

The 1.45 release also introduced facilities to check whether log emission is enabled before constructing expensive records, reducing unnecessary work for disabled telemetry.

Maturity limitation: Python's logging SDK is explicitly still under development. Its internal interfaces and behavior should not be treated as having the same stability guarantees as the tracing and metrics SDKs.

Sources:

- Logging instrumentation and correlation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html?utm_source=chatgpt.com)
- Logging SDK reference: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/\_logs.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/_logs.html?utm_source=chatgpt.com)
- Logging SDK examples and status: [https://opentelemetry-python.readthedocs.io/en/latest/examples/logs/README.html](https://opentelemetry-python.readthedocs.io/en/latest/examples/logs/README.html?utm_source=chatgpt.com)
- OpenTelemetry log data model: [https://opentelemetry.io/docs/specs/otel/logs/data-model/](https://opentelemetry.io/docs/specs/otel/logs/data-model/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python-contrib.readthedocs.io\&sz=32)

OpenTelemetry Python Contrib documentation

+2

## 6. Context propagation, concurrency, and distributed causality

Context propagation is one of OpenTelemetry's most valuable and frequently underestimated capabilities.

Tracing spans describe operations; context propagation allows independently executing operations to discover or reconstruct their causal relationship.

### 6.1 Execution Context is not the same as a Span

The OpenTelemetry `Context` holds context-local values. The current span is one such value.

The API provides `context.get_current()`, `context.set_value()`, `context.attach()`, and `context.detach()`.

`set_value()` returns a new context rather than mutating arbitrary global state; `attach()` makes a context current and returns a token that can later be detached.

This separates the data being propagated from the mechanism used to activate it.

### 6.2 Python concurrency behavior

| Execution boundary             | Context behavior                                                                |
| ------------------------------ | ------------------------------------------------------------------------------- |
| Ordinary nested function calls | Current context is inherited                                                    |
| `asyncio` tasks                | Python `contextvars` normally preserve context across task creation             |
| New threads / thread pools     | Requires attention to explicit propagation or appropriate instrumentation       |
| Subprocesses                   | Requires explicit transport or propagation; context-local memory is not shared  |
| HTTP/RPC/message boundaries    | Requires injecting and extracting carrier values                                |
| Forked workers                 | SDK workers, exporters, and resource state may require post-fork initialization |

`ThreadingInstrumentor` provides context propagation for supported threading and `ThreadPoolExecutor` operations. This is useful even when no additional thread spans are desired.

`AsyncioInstrumentor` serves a different purpose: it can instrument asynchronous operations, creating spans and associated measurements. It should not be confused with the underlying `contextvars` mechanism that already provides normal asyncio context isolation.

### 6.3 W3C Trace Context

For cross-service communication, OpenTelemetry normally uses the W3C Trace Context format:

- `traceparent` carries trace identity, parent span identity, and trace flags.
- `tracestate` carries additional vendor-specific trace context.

The Python API provides `propagate.inject()` and `propagate.extract()`, as well as text-map propagator interfaces for custom carriers.

This is not restricted to HTTP: a carrier can be a message-header collection or another key-value structure understood by both endpoints.

Automatic instrumentation often performs extraction on incoming requests and injection on outgoing calls.

A propagated span context is not an exported span. It supplies enough context for downstream instrumentation to create a correctly related span.

### 6.4 Baggage versus span attributes

OpenTelemetry baggage consists of key-value pairs propagated with execution context, typically through the W3C `baggage` header.

Unlike ordinary span attributes, baggage can cross service boundaries.

This makes it useful for carrying small amounts of correlation or classification context, but it creates an important security distinction:

Baggage is propagated to downstream services; a span attribute is not automatically propagated.

Baggage values are also not automatically copied onto every span or metric. Instrumentation must intentionally use them if they are to become telemetry attributes.

This matters for privacy, data minimization, cross-tenant isolation, and preventing accidental disclosure to external API providers.

### 6.5 Alternative propagation formats

The propagation ecosystem also supports formats such as B3 and AWS X-Ray through additional propagators.

These can bridge systems that do not uniformly use W3C Trace Context.

However, supporting multiple formats is not equivalent to resolving all trace semantics automatically. Conflicting incoming headers, sampling decisions, or baggage policies require explicit expectations about which propagator takes precedence.

Sources:

- Python context API: [https://opentelemetry-python.readthedocs.io/en/latest/api/context.html](https://opentelemetry-python.readthedocs.io/en/latest/api/context.html?utm_source=chatgpt.com)
- Python propagators API: [https://opentelemetry-python.readthedocs.io/en/latest/api/propagate.html](https://opentelemetry-python.readthedocs.io/en/latest/api/propagate.html?utm_source=chatgpt.com)
- Python baggage API: [https://opentelemetry-python.readthedocs.io/en/latest/api/baggage.html](https://opentelemetry-python.readthedocs.io/en/latest/api/baggage.html?utm_source=chatgpt.com)
- Python propagation guide: [https://opentelemetry.io/docs/languages/python/propagation/](https://opentelemetry.io/docs/languages/python/propagation/?utm_source=chatgpt.com)
- Threading instrumentation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/threading/threading.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/threading/threading.html?utm_source=chatgpt.com)
- Asyncio instrumentation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asyncio/asyncio.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asyncio/asyncio.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry.io\&sz=32)

OpenTelemetry

## 7. Automatic and library-level instrumentation

OpenTelemetry Python Contrib provides a substantial ecosystem of integrations that can instrument common frameworks, middleware, clients, and runtime facilities.

The important capability is not just automatic span creation. Mature instrumentations can also supply context propagation, standardized attributes, request metrics, exception recording, and hooks for application-specific enrichment.

### 7.1 Zero-code instrumentation

The typical automatic-instrumentation mechanism is:

```
pip install "opentelemetry-distro[otlp]"
opentelemetry-bootstrap -a install
opentelemetry-instrument python application.py
```

`opentelemetry-bootstrap` discovers relevant instrumentation packages for installed dependencies. The startup command configures and activates the available integrations before application execution.

`opentelemetry-instrument` supports environment-driven exporters, resource attributes, and instrumentation selection. It does not infer application-specific business operations: those still require manual instrumentation or specialized integrations.

There is also a programmatic initialization path when the command-line launcher cannot be used, but initialization order matters because some integrations must patch libraries before those libraries are imported.

### 7.2 Major integration families

| Family              | Representative integrations                             | Captured information                                                |
| ------------------- | ------------------------------------------------------- | ------------------------------------------------------------------- |
| HTTP servers        | ASGI, WSGI, FastAPI, Starlette, Flask, Django           | Incoming requests, duration, status, routes, trace extraction       |
| HTTP clients        | `requests`, `httpx`, `aiohttp`, `urllib3`, `urllib`     | Outgoing calls, dependency latency, errors, context injection       |
| RPC                 | gRPC client/server                                      | RPC spans, propagation, status, execution duration                  |
| Databases           | SQLAlchemy, psycopg, psycopg2, asyncpg, DB-API, PyMongo | Database interactions, query metadata, latency, errors              |
| Caches and search   | Redis, supported search clients                         | Command-level spans and dependency information                      |
| Messaging           | Celery, Kafka clients, AMQP integrations, SQS           | Produce/consume activity, messaging context, asynchronous execution |
| Cloud services      | Botocore, AWS Lambda and other provider integrations    | SDK calls, service operations, request context                      |
| Concurrency         | `threading`, `asyncio`                                  | Context transfer and selected task instrumentation                  |
| System measurements | `system_metrics`                                        | Process, host, runtime-related measurements                         |
| Logging             | Python `logging`                                        | Structured log export and optional trace correlation                |

Integration behavior is specific to the instrumented library and the particular instrumentation version. The table describes capability categories, not a guarantee that all implementations record identical fields.

### 7.3 Programmatic instrumentors and hooks

Instrumentation packages typically expose an `Instrumentor` class, such as `FastAPIInstrumentor`, `RequestsInstrumentor`, or `SQLAlchemyInstrumentor`.

These can permit explicit control over:

- Which application or client objects are instrumented.
- Which tracer or meter provider is used.
- Request or response hooks for additional attributes.
- Excluded URLs and selected span categories.
- HTTP header capture and sanitization.
- Uninstrumenting during controlled lifecycle changes or tests.

For instance, SQLAlchemy instrumentation can operate at the engine level, enabling observation of database operations regardless of which application component issued a particular query.

That is a different architectural boundary from tracing only application-level repository functions.

### 7.4 Instrumentation layering and duplication

Automatic instrumentation works by wrapping existing framework or library operations. Multiple wrappers can observe the same underlying work.

This is useful when each layer represents a distinct operation, but it can also create redundant spans or metrics.

For example, instrumenting an HTTP framework, its underlying ASGI implementation, an ORM, and the database driver may produce several correlated spans for one request.

Those spans are not inherently duplicates: some represent a logical request, others represent individual database operations. However, instrumenting two implementations of the same request boundary can produce unnecessary duplication.

Instrumentation boundaries should therefore be understood in terms of operation semantics, not simply whether an available integration can be enabled.

### 7.5 HTTP security and cardinality controls

HTTP integrations commonly expose controls for URL exclusions, captured headers, and sensitive-header sanitization.

Request paths, query strings, credentials, authorization headers, and error messages can all introduce sensitive data or high-cardinality telemetry.

Using normalized route templates, such as `/orders/{order_id}`, is materially different from using concrete URLs containing unique identifiers.

Application-specific hooks can enrich spans with useful structured dimensions, but indiscriminate metadata capture can increase both cost and information exposure.

### 7.6 SQLCommenter and database propagation

Some database integrations support SQLCommenter, which appends structured comments to SQL statements.

This can convey trace context into database-side logs or diagnostic facilities, making it possible to associate application traces with database activity even when the database itself does not run an OpenTelemetry Python SDK.

The tradeoff is that SQL text changes. Depending on the driver, database, query normalization, and caching behavior, comments can affect logging volume or statement identity.

SQLCommenter is therefore best understood as an optional integration mechanism, not a transparent property of all database instrumentation.

### 7.7 Generative AI and agent instrumentation

The OpenTelemetry ecosystem also maintains specialized GenAI semantic conventions and instrumentation for operations such as model inference, embeddings, and agent execution.

These may represent model names, token usage, inference parameters, provider operations, tool calls, and related execution spans.

Importantly, parts of this work live in the separate `opentelemetry-python-genai` repository and have their own release maturity and compatibility boundaries. They should not be assumed to be part of the stable core Python SDK.

GenAI telemetry requires particular care with prompts, completions, tool arguments, and retrieved document contents. Traceability does not imply that recording full model inputs and outputs is appropriate.

Sources:

- Python zero-code instrumentation: [https://opentelemetry.io/docs/zero-code/python/](https://opentelemetry.io/docs/zero-code/python/?utm_source=chatgpt.com)
- Zero-code configuration: [https://opentelemetry.io/docs/zero-code/python/configuration/](https://opentelemetry.io/docs/zero-code/python/configuration/?utm_source=chatgpt.com)
- Python library integrations: [https://opentelemetry.io/docs/languages/python/libraries/](https://opentelemetry.io/docs/languages/python/libraries/?utm_source=chatgpt.com)
- Contrib documentation index: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/](https://opentelemetry-python-contrib.readthedocs.io/en/latest/?utm_source=chatgpt.com)
- FastAPI instrumentation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html?utm_source=chatgpt.com)
- SQLAlchemy instrumentation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/sqlalchemy/sqlalchemy.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/sqlalchemy/sqlalchemy.html?utm_source=chatgpt.com)
- Psycopg instrumentation: [https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/psycopg/psycopg.html](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/psycopg/psycopg.html?utm_source=chatgpt.com)
- Separate GenAI Python repository: [https://github.com/open-telemetry/opentelemetry-python-genai](https://github.com/open-telemetry/opentelemetry-python-genai?utm_source=chatgpt.com)
- GenAI semantic conventions: [https://github.com/open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2

## 8. Semantic conventions, Resources, and consistent telemetry meaning

OpenTelemetry's semantic conventions define standardized names and meanings for telemetry produced by unrelated implementations.

They matter because independently collected telemetry becomes much more useful when it follows a common data model.

### 8.1 Resource identity

A `Resource` is an immutable collection of attributes describing the entity producing telemetry.

Common attributes include:

| Attribute                     | Meaning                                   |
| ----------------------------- | ----------------------------------------- |
| `service.name`                | Logical service identity                  |
| `service.namespace`           | Namespace containing the service          |
| `service.version`             | Version of the running service            |
| `service.instance.id`         | Identity of a particular service instance |
| `deployment.environment.name` | Deployment environment                    |
| `process.pid`                 | Operating-system process identifier       |
| `host.name`                   | Host identity, where available            |
| `container.id`                | Container identity, where detected        |

Resource attributes are associated with telemetry at the provider level rather than requiring instrumentation code to attach them to every span or measurement.

Consequently, a service can emit meaningful infrastructure and deployment metadata without duplicating those values across instrumented functions.

### 8.2 Resource detection and enrichment

The Python SDK exposes `ResourceDetector`, `ProcessResourceDetector`, `OsResourceDetector`, `HostResourceDetector`, and `ServiceInstanceIdResourceDetector`.

Detectors collect information from their respective environments, and custom detectors can contribute application-specific identity metadata.

The `ServiceInstanceIdResourceDetector`, added in 1.43, generates a process-associated UUID. Recent SDK changes also support refreshing process-dependent resource information when a worker is forked.

A useful safety improvement in 1.44 is that process command-line arguments are excluded by default. `ProcessResourceDetector(include_command_args=True)` enables them explicitly.

This matters because command-line values can contain credentials, tokens, user inputs, or other sensitive information.

### 8.3 Instrumentation scopes and schema versions

Instrumentation scopes associate telemetry with the component generating it, whereas Resources identify the producing entity.

A scope includes a name and optional version, schema URL, and attributes.

Schema URLs and semantic-convention versions help describe the interpretation of emitted telemetry. They are especially relevant when attributes or metric names change across semantic-convention releases.

The 1.45.0 core release updated its bundled semantic conventions to version 1.44.0. This is a separate version dimension from the Python SDK and instrumentation package versions.

### 8.4 Semantic-convention stability varies by domain

Different convention families have different maturity levels.

The service resource conventions are stable; database conventions have mixed maturity; messaging conventions remain under development in the current specification.

Some Python integrations support `OTEL_SEMCONV_STABILITY_OPT_IN` to select newer conventions. For database instrumentation, supported values include `database` and `database/dup`, with the latter producing both older and newer forms during a transition.

That dual-emission capability can preserve compatibility, but it may also duplicate dimensions or metric streams downstream. Support must be checked for the individual instrumentation package.

The general distinction is between semantic compatibility and wire-format compatibility: two telemetry records may both be valid OTLP while using different attribute names or measurement semantics.

Sources:

- Python Resources API: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/resources.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/resources.html?utm_source=chatgpt.com)
- Service conventions: [https://opentelemetry.io/docs/specs/semconv/resource/service/](https://opentelemetry.io/docs/specs/semconv/resource/service/?utm_source=chatgpt.com)
- Instrumentation scopes: [https://opentelemetry.io/docs/specs/otel/common/instrumentation-scope/](https://opentelemetry.io/docs/specs/otel/common/instrumentation-scope/?utm_source=chatgpt.com)
- Database conventions: [https://opentelemetry.io/docs/specs/semconv/db/](https://opentelemetry.io/docs/specs/semconv/db/?utm_source=chatgpt.com)
- Messaging conventions: [https://opentelemetry.io/docs/specs/semconv/messaging/](https://opentelemetry.io/docs/specs/semconv/messaging/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+5

## 9. Exporters, OTLP, and the Collector boundary

OpenTelemetry Python can produce telemetry independently of any particular backend. Exporters translate SDK data into formats and protocols understood by downstream systems.

### 9.1 OTLP as the principal interoperability layer

The OpenTelemetry Protocol (OTLP) supports all three principal signals: traces, metrics, and logs.

The most important transport options are:

| Transport          | Typical endpoint              | Characteristics                                                  |
| ------------------ | ----------------------------- | ---------------------------------------------------------------- |
| OTLP/gRPC          | `localhost:4317`              | Protobuf over gRPC/HTTP2                                         |
| OTLP/HTTP protobuf | `localhost:4318/v1/{signal}`  | Protobuf over HTTP                                               |
| OTLP/HTTP JSON     | Signal-specific HTTP endpoint | JSON OTLP encoding, supported by the newer JSON exporter package |

For HTTP, the signal paths are ordinarily `/v1/traces`, `/v1/metrics`, and `/v1/logs`.

Endpoint configuration contains a subtle distinction:

- `OTEL_EXPORTER_OTLP_ENDPOINT` specifies a base endpoint. OTLP/HTTP exporters append the signal-specific path.
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, and `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` specify complete signal endpoints.

Confusing the two can produce incorrect paths.

Exporters also support configuration for headers, timeouts, TLS certificates, compression, and transport behavior.

Version 1.45.1 restored Python `requests` as the default HTTP transport for the protobuf HTTP exporter, ensuring standard proxy environment variables are honored again.

### 9.2 Other supported export mechanisms

The ecosystem also includes console exporters, Zipkin integration, and Prometheus metric export.

The Prometheus exporter uses `PrometheusMetricReader` to collect metrics on demand. This differs from periodically pushing OTLP metrics.

Prometheus support has also gained options for representing selected Resource attributes and instrumentation-scope attributes as metric labels.

These options improve labeling flexibility but must be considered together with cardinality controls.

Recent core releases added OTLP JSON file and OTLP JSON HTTP exporter packages. They can be useful for development, replay-oriented workflows, file-based interchange, or endpoints requiring JSON rather than protobuf.

### 9.3 Multiple destinations

The SDK supports exporting to multiple destinations without duplicating instrumentation calls.

The documented approach is signal-specific:

| Signal  | Multi-destination mechanism                              |
| ------- | -------------------------------------------------------- |
| Traces  | Separate span processors, each owning its exporter       |
| Metrics | Separate metric readers, each owning its exporter        |
| Logs    | Separate log record processors, each owning its exporter |

The significance is pipeline independence.

One destination can use a different export interval, temporality, queue, or retry behavior from another.

Nevertheless, merely configuring multiple exporters does not guarantee complete delivery isolation. Each path still requires appropriate queueing and failure handling, and work performed synchronously in the application remains relevant to application latency.

### 9.4 The OpenTelemetry Collector

The Collector is a separately deployed component that can receive telemetry, transform it, and export it to one or more backends.

Its architecture consists of receivers, processors, exporters, connectors, and extensions.

| Collector capability       | Relationship to Python SDK                                     |
| -------------------------- | -------------------------------------------------------------- |
| OTLP reception             | Ingests exported Python telemetry                              |
| Batching and retry         | Buffers and manages downstream delivery                        |
| Filtering                  | Drops unwanted telemetry after reception                       |
| OTTL transformations       | Rewrites or enriches telemetry                                 |
| Resource detection         | Adds infrastructure metadata outside the application           |
| Tail sampling              | Evaluates traces after more execution information is available |
| Span-to-metrics connectors | Derives measurements from received spans                       |
| Multi-backend routing      | Sends different data to different consumers                    |

This creates a useful architectural separation: Python instrumentation can remain stable while downstream observability routing and enrichment evolve.

However, several limits are consequential.

A Collector cannot recover information never recorded or exported by an application. A span-to-metrics connector operating on head-sampled traces cannot infer exact unsampled request counts merely from the retained spans. Tail sampling also requires enough incoming spans to evaluate the relevant traces.

The Collector provides sophisticated post-emission processing; it does not eliminate the need to decide what information the SDK should produce.

### 9.5 Telemetry durability is not guaranteed

Neither `span.end()` nor `BatchSpanProcessor` necessarily means that data has reached durable storage.

Telemetry may still be:

- Buffered in memory.
- Awaiting exporter processing.
- In transit to a Collector.
- Queued within the Collector.
- Rejected or dropped by a backend.

`force_flush()` attempts to flush pending telemetry, and `shutdown()` performs lifecycle cleanup, but neither transforms OpenTelemetry into a transactional write-ahead log or durable audit mechanism.

This distinction matters for high-value diagnostic records and any workflow requiring provable event retention.

Sources:

- Python exporters: [https://opentelemetry.io/docs/languages/python/exporters/](https://opentelemetry.io/docs/languages/python/exporters/?utm_source=chatgpt.com)
- OTLP exporters API: [https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html](https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html?utm_source=chatgpt.com)
- OTLP exporter configuration: [https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/?utm_source=chatgpt.com)
- Collector architecture: [https://opentelemetry.io/docs/collector/architecture/](https://opentelemetry.io/docs/collector/architecture/?utm_source=chatgpt.com)
- Collector components: [https://opentelemetry.io/docs/collector/components/](https://opentelemetry.io/docs/collector/components/?utm_source=chatgpt.com)
- Collector transformations: [https://opentelemetry.io/docs/collector/transforming-telemetry/](https://opentelemetry.io/docs/collector/transforming-telemetry/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+5

## 10. SDK configuration and declarative observability

Python supports both explicit SDK construction in code and environment-driven configuration.

More recently, it has gained a substantial declarative configuration capability.

### 10.1 Environment-driven configuration

Widely useful environment variables include:

| Variable                                | Purpose                                     |
| --------------------------------------- | ------------------------------------------- |
| `OTEL_SERVICE_NAME`                     | Service identity                            |
| `OTEL_RESOURCE_ATTRIBUTES`              | Additional Resource attributes              |
| `OTEL_PROPAGATORS`                      | Context propagation formats                 |
| `OTEL_TRACES_SAMPLER`                   | Trace sampling policy                       |
| `OTEL_TRACES_SAMPLER_ARG`               | Sampler configuration argument              |
| `OTEL_TRACES_EXPORTER`                  | Configured trace exporters                  |
| `OTEL_METRICS_EXPORTER`                 | Configured metric exporters                 |
| `OTEL_LOGS_EXPORTER`                    | Configured log exporters                    |
| `OTEL_EXPORTER_OTLP_ENDPOINT`           | Base OTLP destination                       |
| `OTEL_EXPORTER_OTLP_PROTOCOL`           | OTLP transport format                       |
| `OTEL_BSP_*`                            | Batch span processor settings               |
| `OTEL_METRIC_EXPORT_INTERVAL`           | Periodic metrics collection interval        |
| `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` | Disable selected automatic instrumentations |

Additional variables control logging behavior, metric temporality, exporter security, and instrument-specific options.

These settings are particularly useful when the same application artifact needs different observability behavior across deployments.

### 10.2 Declarative configuration: an important newer capability

Starting in the 1.43 series, Python gained experimental support for OpenTelemetry declarative configuration through the separate `opentelemetry-configuration` package.

It supports a YAML or JSON configuration describing:

- Resource attributes and detectors.
- Tracer providers and samplers.
- Meter providers, metric readers, and exporters.
- Logger providers and log processors.
- Propagators.
- SDK limits and selected implementation extensions.
- Instrumentation activation and supported instrumentor options.

A configuration file can be selected through `OTEL_CONFIG_FILE`.

A short illustrative fragment:

```
file_format: "1.0"

resource:
  attributes:
    - name: service.name
      value: analytics-worker

tracer_provider:
  processors:
    - batch:
        exporter:
          otlp_http:
            endpoint: http://localhost:4318/v1/traces
  sampler:
    parent_based:
      root:
        always_on: {}
```

The mechanism makes observability configuration a declarative artifact rather than necessarily requiring application-owned initialization code.

This can reduce custom configuration wrappers and make the telemetry policy more inspectable.

### 10.3 File configuration has different precedence semantics

A crucial detail is that setting `OTEL_CONFIG_FILE` does not simply layer the file onto all ordinary `OTEL_*` environment settings.

The file becomes the authoritative source for SDK construction. Environment settings with equivalent schema fields are bypassed, although environment substitution inside the file is supported.

Python-specific `OTEL_PYTHON_*` initialization extensions are also bypassed by this initialization path.

The distinction is easy to miss when transitioning from auto-instrumentation environment configuration to declarative configuration.

Declarative configuration additionally supports experimental, Python-specific sections for activating instrumentors and configuring instrumentation scopes.

These capabilities are promising but remain experimental. Some specification fields are not yet implemented, and the current documentation explicitly warns about rough edges.

Sources:

- Declarative configuration: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/configuration.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/configuration.html?utm_source=chatgpt.com)
- SDK environment settings: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/environment_variables.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/environment_variables.html?utm_source=chatgpt.com)
- Declarative configuration specification: [https://opentelemetry.io/docs/specs/otel/configuration/](https://opentelemetry.io/docs/specs/otel/configuration/?utm_source=chatgpt.com)
- Python configuration examples: [https://opentelemetry-python.readthedocs.io/en/latest/examples/declarative-config/README.html](https://opentelemetry-python.readthedocs.io/en/latest/examples/declarative-config/README.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+2

## 11. Extensibility and advanced architectural composition

OpenTelemetry Python provides extension interfaces at several different levels. These are useful when generic framework instrumentation does not fully describe an application's domain-specific execution.

### 11.1 Extension points

| Extension                 | What can be customized                                     |
| ------------------------- | ---------------------------------------------------------- |
| `Sampler`                 | Whether and how operations are recorded or exported        |
| `SpanProcessor`           | Span enrichment, local analysis, routing, or preprocessing |
| `SpanExporter`            | Custom trace destinations                                  |
| `MetricReader`            | Collection cadence and collection behavior                 |
| `MetricExporter`          | Custom metric destinations                                 |
| `View`                    | Metric naming, dimensions, aggregation and exemplars       |
| Aggregation/reservoir     | Measurement aggregation and exemplar retention             |
| `LogRecordProcessor`      | Structured-log transformation or routing                   |
| `LogExporter`             | Custom log destinations                                    |
| `ResourceDetector`        | Entity identity and environmental metadata                 |
| `TextMapPropagator`       | Distributed context transport                              |
| Instrumentation package   | Automatic observation of application or library operations |
| Distribution/configurator | SDK setup and deployment-specific initialization           |

These capabilities allow observability concerns to be centralized at the appropriate abstraction level.

A custom metric aggregation policy can be implemented through Views instead of rewriting instrumentation. A custom telemetry destination can be reached through an exporter rather than modifying each instrumented module. An external execution library can be instrumented once through an integration instead of requiring every caller to create spans manually.

### 11.2 Combining traces and metrics

A powerful composition is using traces for detailed execution structure while using metrics for comprehensive quantitative coverage.

For example:

- Synchronous histogram instruments record latency distributions.
- Spans capture individual execution stages and dependencies.
- Trace-linked exemplars connect selected measurements to concrete traces.
- Span processors can compute additional local measurements.
- `AlwaysRecordSampler` can expose unsampled operations to local processors while controlling trace export volume.

These are complementary mechanisms, not automatic substitutes for one another.

An application that records only sampled spans cannot generally reconstruct exact distributions of all operations from the retained traces.

Conversely, recording metrics independently can preserve aggregate measurements without requiring every operation to become an exported trace.

### 11.3 A small cross-signal Python example

The following is an illustrative SDK setup, not an executed example. It shows that Resource identity, trace recording, and metrics aggregation are separate configuration decisions.

```
from opentelemetry import trace, metricsfrom opentelemetry.sdk.resources import Resourcefrom opentelemetry.sdk.trace import TracerProviderfrom opentelemetry.sdk.trace.export import BatchSpanProcessorfrom opentelemetry.sdk.metrics import MeterProviderfrom opentelemetry.sdk.metrics.export import InMemoryMetricReaderfrom opentelemetry.sdk.metrics.view import (    View,    ExplicitBucketHistogramAggregation,)from opentelemetry.exporter.otlp.proto.http.trace_exporter import (    OTLPSpanExporter,)resource = Resource.create({"service.name": "example-worker"})tracer_provider = TracerProvider(resource=resource)tracer_provider.add_span_processor(    BatchSpanProcessor(        OTLPSpanExporter(            endpoint="http://localhost:4318/v1/traces"        )    ))trace.set_tracer_provider(tracer_provider)metric_reader = InMemoryMetricReader()meter_provider = MeterProvider(    resource=resource,    metric_readers=[metric_reader],    views=[        View(            instrument_name="operation.duration",            aggregation=ExplicitBucketHistogramAggregation(                boundaries=[0.01, 0.1, 1.0, 10.0]            ),        )    ],)metrics.set_meter_provider(meter_provider)tracer = trace.get_tracer("example.worker")meter = metrics.get_meter("example.worker")duration = meter.create_histogram(    "operation.duration", unit="s")with tracer.start_as_current_span("operation.execute"):    duration.record(0.215, {"operation.kind": "batch"})
```

Here, the metrics reader is deliberately in-memory, while tracing uses OTLP. This demonstrates independent pipeline configuration, not a production exporter configuration.

The histogram's bucket policy resides in a View rather than in its recording call. The shared Resource provides a common service identity without making the metric depend on the span.

### 11.4 The boundary with continuous profilers

OpenTelemetry traces are useful for measuring logical operation duration, but they are not substitutes for CPU profilers, allocation profilers, statistical samplers, or runtime-level instrumentation.

Spans can establish which logical stage is slow. Profilers can investigate what execution occurred within that stage.

OpenTelemetry's broader specifications include profiling work, but the Python SDK does not currently provide a native Profiles signal comparable to its tracing, metrics, and logging implementations.

The useful architectural relationship is correlation between complementary signals, not assuming that tracing alone supplies instruction-level performance diagnostics.

## 12. Performance, resource lifecycle, reliability, and testing

OpenTelemetry is designed for production observability, but its overhead depends on how much information is recorded and how processing is configured.

### 12.1 Where overhead originates

| Mechanism              | Primary cost drivers                                            |
| ---------------------- | --------------------------------------------------------------- |
| Span creation          | Object creation, context management, timestamps, attributes     |
| Events and links       | Allocations, attribute storage, span limits                     |
| Synchronous processors | Work performed on application execution paths                   |
| Batching               | Buffer memory, queue contention, background processing          |
| Metrics                | Measurement recording, aggregation state, attribute cardinality |
| Observable callbacks   | Collection-time callback work and synchronization               |
| Log processing         | Formatting, structured attribute extraction, batching           |
| Export                 | Serialization, compression, networking, retries                 |
| Auto-instrumentation   | Wrappers, hooks, introspection, duplicated instrumentation      |

Sampler configuration matters, but it is not the only determinant of overhead.

For example, head sampling can avoid recording costs for dropped spans, but instrumentation wrappers and context propagation may still execute. A record-only sampler retains more local diagnostic information at the cost of additional recording work.

### 12.2 Cardinality and attribute design

Low-cardinality attributes such as operation category, normalized route, result category, and service name are often useful for metrics and aggregation.

Per-request identifiers and arbitrary user-generated strings can create very high cardinality.

The consequences include increased aggregation memory, exporter payload size, backend storage, and query costs.

Resource identity, span attributes, metric dimensions, and baggage should therefore be treated as distinct information channels with different propagation, cardinality, and retention properties.

### 12.3 Multiprocessing and shutdown

Python process models require particular care.

A tracing exporter using background threads must not be assumed to survive arbitrary forking semantics unchanged. The official Python examples include post-fork initialization for Gunicorn workers.

Likewise, an `atexit` shutdown hook does not guarantee delivery following a process crash or abrupt termination.

The SDK's lifecycle methods should be understood as best-effort telemetry processing operations, not durability primitives.

### 12.4 Observing the observability SDK

A useful advanced feature is experimental SDK internal metrics.

Setting `OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED=true` enables supported components to emit measurements of their own processing and export behavior.

Such metrics can reveal whether the observability pipeline itself is dropping records, overflowing queues, or encountering export failures.

This is useful because application telemetry can become incomplete precisely when the application or telemetry infrastructure is under stress.

The internal metric conventions are still under development, so their names and semantics do not have the same stability guarantees as mature SDK APIs.

### 12.5 Testing without external backends

The Python SDK includes test-friendly in-memory facilities.

| Utility                         | Purpose                                         |
| ------------------------------- | ----------------------------------------------- |
| `InMemorySpanExporter`          | Inspect completed spans without network export  |
| `InMemoryMetricReader`          | Collect and inspect metric streams              |
| `InMemoryLogRecordExporter`     | Inspect structured log export                   |
| Console exporters               | Examine telemetry during local development      |
| `CapturingSampler` test utility | Inspect sampler inputs in instrumentation tests |

These enable assertions about trace hierarchy, events, metric attributes, aggregation results, and log correlation without depending on a running observability backend.

However, they do not automatically validate Collector configuration, OTLP transport behavior, backend normalization, or visualization.

Testing those boundaries requires separate integration coverage.

Sources:

- SDK metrics: [https://opentelemetry-python.readthedocs.io/en/latest/examples/metrics/sdk-metrics/README.html](https://opentelemetry-python.readthedocs.io/en/latest/examples/metrics/sdk-metrics/README.html?utm_source=chatgpt.com)
- Metrics readers and in-memory collection: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.export.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.export.html?utm_source=chatgpt.com)
- Trace exporters and processors: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.export.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.export.html?utm_source=chatgpt.com)
- Fork-process example: [https://opentelemetry-python.readthedocs.io/en/latest/examples/fork-process-model/README.html](https://opentelemetry-python.readthedocs.io/en/latest/examples/fork-process-model/README.html?utm_source=chatgpt.com)
- Python SDK benchmarks: [https://opentelemetry.io/docs/languages/python/benchmarks/](https://opentelemetry.io/docs/languages/python/benchmarks/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation

+3

## 13. Important version-specific developments

The most recent releases contain several consequential features that might be absent from older documentation or library integrations.

| Release         | Notable capabilities and changes                                                                                                                                                                                             |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.43.0 / 0.64b0 | Dynamic metric-reader registration; `ServiceInstanceIdResourceDetector`; declarative SDK configuration entry point and file loading; OTLP JSON file exporter; expanded configuration support                                 |
| 1.44.0 / 0.65b0 | Process-dependent Resource refresh; optional omission of sensitive process arguments; expanded declarative instrumentation configuration; bounded in-memory span export; log record limits; public multi-log processors      |
| 1.45.0 / 0.66b0 | Stable `AlwaysRecordSampler`; extended attribute values; OTLP JSON HTTP exporter; enabled checks for logging; additional declarative configuration support; improved Prometheus Resource labels; semantic conventions 1.44.0 |
| 1.45.1 / 0.66b1 | Patch fixes including resource-initialization thread leakage, HTTP proxy behavior, and bounded `tracestate` parsing                                                                                                          |

Two versioning rules are especially important.

First, the stable core SDK and beta Contrib instrumentation packages do not share identical compatibility guarantees.

Second, specification support and Python implementation support are not always synchronized. A feature can exist in an OpenTelemetry specification while remaining experimental, incomplete, or unavailable in Python.

Official release references:

- Python 1.43.0: [https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.43.0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.43.0?utm_source=chatgpt.com)
- Python 1.44.0: [https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.44.0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.44.0?utm_source=chatgpt.com)
- Python 1.45.0: [https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.45.0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.45.0?utm_source=chatgpt.com)
- Python 1.45.1: [https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.45.1](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.45.1?utm_source=chatgpt.com)
- Contrib 0.66b1: [https://github.com/open-telemetry/opentelemetry-python-contrib/releases/tag/v0.66b1](https://github.com/open-telemetry/opentelemetry-python-contrib/releases/tag/v0.66b1?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+4

## 14. Technical distinctions worth retaining

The most useful way to reason about OpenTelemetry Python is as a collection of independent but composable mechanisms.

| Distinction                              | Consequence                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------- |
| API versus SDK                           | Instrumentation can remain independent of telemetry processing policy           |
| Instrumentation scope versus Resource    | The telemetry-producing software is different from the entity running it        |
| Span parent versus span link             | Hierarchical execution and non-tree causality require different representations |
| Span event versus log record             | Trace annotations and independent structured diagnostics serve different needs  |
| Baggage versus attributes                | Propagated context has different security and lifecycle semantics               |
| Sampling versus recording                | A span can be recorded locally without being selected for export                |
| Metric measurement versus View           | Instrumentation and aggregation policy can evolve independently                 |
| Cumulative versus delta metrics          | Downstream interpretation and reset semantics change                            |
| SDK filtering versus Collector filtering | Early filtering can prevent unnecessary local aggregation cost                  |
| Head versus tail sampling                | Sampling decisions are made with different available information                |
| Export success versus durable storage    | Telemetry pipelines are not transactional audit stores                          |
| Specification versus Python release      | A defined capability is not necessarily implemented or stable in Python         |

The most substantial architectural opportunities generally arise from combining these mechanisms: API-only library instrumentation, consistent semantic conventions, context propagation, independently configured trace and metric pipelines, View-based aggregation policies, and Collector-side downstream processing.

Those combinations can replace significant amounts of custom tracing, correlation, metric aggregation, configuration, and diagnostic plumbing. They do not eliminate the need for application-specific instrumentation semantics, cardinality control, lifecycle management, or reliable storage when telemetry must serve as an authoritative record.

## 15. Primary-source resource map

For deeper investigation, these are the most useful starting points beyond the capability-specific URLs already provided.

| Resource                                                                                                                                                                                                       | Coverage                                                           |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Python documentation: [https://opentelemetry.io/docs/languages/python/](https://opentelemetry.io/docs/languages/python/?utm_source=chatgpt.com)                                                                | Overall language support, maturity, integration paths              |
| Python SDK API reference: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/index.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/index.html?utm_source=chatgpt.com)                  | Concrete providers, processors, metrics, resources, logging        |
| Python API reference: [https://opentelemetry-python.readthedocs.io/en/latest/api/index.html](https://opentelemetry-python.readthedocs.io/en/latest/api/index.html?utm_source=chatgpt.com)                      | Implementation-independent APIs and context handling               |
| Core source: [https://github.com/open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python?utm_source=chatgpt.com)                                                           | SDK, API, exporters, release history, tests                        |
| Contrib source: [https://github.com/open-telemetry/opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib?utm_source=chatgpt.com)                                        | Framework, database, messaging, and runtime instrumentation        |
| OpenTelemetry specification: [https://opentelemetry.io/docs/specs/otel/](https://opentelemetry.io/docs/specs/otel/?utm_source=chatgpt.com)                                                                     | Normative signal and SDK behavior                                  |
| Semantic conventions: [https://opentelemetry.io/docs/specs/semconv/](https://opentelemetry.io/docs/specs/semconv/?utm_source=chatgpt.com)                                                                      | Standard telemetry identity, attributes, names, units              |
| OTLP specification: [https://opentelemetry.io/docs/specs/otlp/](https://opentelemetry.io/docs/specs/otlp/?utm_source=chatgpt.com)                                                                              | Protocol, wire format, transport, and delivery semantics           |
| Declarative configuration: [https://opentelemetry-python.readthedocs.io/en/latest/sdk/configuration.html](https://opentelemetry-python.readthedocs.io/en/latest/sdk/configuration.html?utm_source=chatgpt.com) | Experimental configuration-driven SDK construction                 |
| Collector documentation: [https://opentelemetry.io/docs/collector/](https://opentelemetry.io/docs/collector/?utm_source=chatgpt.com)                                                                           | Pipelines, routing, processors, connectors and extensions          |
| Ecosystem registry: [https://opentelemetry.io/ecosystem/registry/](https://opentelemetry.io/ecosystem/registry/?utm_source=chatgpt.com)                                                                        | Additional integrations, exporters, receivers, and related tooling |

Overall: OpenTelemetry Python is best understood not as a tracing wrapper, but as a configurable telemetry runtime and interoperability layer. Its most distinctive advanced capabilities are context propagation across execution boundaries, non-tree trace relationships, independent metrics aggregation through Views, record-only sampling, instrumentation ecosystem integration, and the ability to shift observability processing and routing outside application code.