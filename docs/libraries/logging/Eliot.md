# Eliot — Python Structured Logging and Causal Tracing

Technical capability reference | Eliot 1.18.0 | Research date: October 31, 2026

Eliot is a Python logging library built around causal actions rather than independent log statements. It produces structured event records from which the execution history of an operation can be reconstructed: what happened, why it happened, which operations contributed to an outcome, and where a failure occurred.

Its defining capability is to associate messages and nested operations with a shared causal hierarchy, including operations that cross asynchronous tasks, threads, processes, and network boundaries.

Verified release: 1.18.0, published May 7, 2026. Supports CPython 3.10–3.14 and PyPy 3.11; Apache 2.0 licensed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Official resources:

- Repository: [https://github.com/itamarst/eliot](https://github.com/itamarst/eliot?utm_source=chatgpt.com)
- Documentation: [https://eliot.readthedocs.io/](https://eliot.readthedocs.io/?utm_source=chatgpt.com)
- Package: [https://pypi.org/project/eliot/](https://pypi.org/project/eliot/?utm_source=chatgpt.com)

## 1. Architectural orientation

Eliot is best understood as a causally structured event-generation system, not simply an alternative formatting layer for Python's `logging` module.

Its core model combines three concepts:

1. Actions represent bounded operations with a beginning, an outcome, and optional children. They can be nested to express execution causality.
2. Messages record structured facts within an action's context, without necessarily representing a complete operation themselves.
3. Tasks are top-level causal trees. Context can be carried across execution boundaries to continue an existing task rather than creating unrelated logging histories.

The result is a forest of execution histories, represented physically as ordinary structured log records.

| Capability family                | What Eliot contributes                                                         |
| -------------------------------- | ------------------------------------------------------------------------------ |
| Causal tracing                   | Nested actions, parent-child relationships, success/failure outcomes           |
| Structured event semantics       | Named messages/actions, typed field definitions, validation                    |
| Context propagation              | Thread, coroutine, process, and explicit network-boundary continuation         |
| Instrumentation                  | Context managers, function decorators, manually controlled action lifecycles   |
| Diagnostics                      | Exception records, action outcomes, contextual metadata, timing reconstruction |
| Output integration               | JSON destinations, destination management, system logging integration          |
| Testing                          | In-memory event capture, structural assertions, validation, exception checking |
| Scientific and async integration | NumPy serialization, Dask tracing, asyncio, Trio, Twisted support              |

### What Eliot does not attempt to own

Eliot generates and structures telemetry; it is not a complete observability platform.

It does not replace log aggregation, retention, indexing, search infrastructure, metrics storage, or a distributed tracing backend. These remain responsibilities of external systems or companion tools.

This separation matters architecturally: Eliot's causal model can be useful independently of where logs are stored or how they are inspected. Conversely, reconstructing causal trees requires retaining the relevant structured fields and correlating records correctly.

Primary documentation: [https://eliot.readthedocs.io/en/stable/generating/actions.html](https://eliot.readthedocs.io/en/stable/generating/actions.html?utm_source=chatgpt.com)

## 2. The causal action model

### 2.1 Actions, messages, and execution identity

A normal Eliot action produces two records: a start event and a terminal event. The terminal status is `succeeded` or `failed`.

An action can contain other actions and ordinary messages. Eliot associates those records with the active action context, allowing the logical hierarchy to be recovered without requiring a separate span-storage service.

The fundamental identity fields are:

| Field                 | Semantics                                                     |
| --------------------- | ------------------------------------------------------------- |
| `task_uuid`           | Identifier shared across one causal task tree                 |
| `task_level`          | Hierarchical position of an individual event within that task |
| `action_type`         | Semantic operation identifier                                 |
| `action_status`       | `started`, `succeeded`, or `failed`                           |
| `message_type`        | Semantic identifier of an ordinary event                      |
| `timestamp`           | Wall-clock Unix timestamp                                     |
| `exception`, `reason` | Exception type and description on failure                     |
| `traceback`           | Explicitly logged exception traceback                         |

The combination of `task_uuid` and `task_level` uniquely identifies an Eliot event when context identifiers are used correctly.

For example, the following illustrative event sequence:

```
task_uuid = "abc..."

[1]       action=process_document   started
[2]       message=source_identified
[3,1]     action=parse_document     started
[3,2]     message=parser_selected
[3,3]     action=parse_document     succeeded
[4]       action=process_document   succeeded
```

encodes the hierarchy and order without relying on log arrival order.

`task_level` is particularly significant. It is not merely a nesting-depth counter. Its components identify positions within a task tree, so an individual event can be located even when records from multiple threads or processes have been interleaved.

The timestamp is useful for elapsed-time analysis but is not a reliable ordering authority: the system clock can move backward, and clocks across machines may be unsynchronized. Eliot's logical event positions provide the stronger ordering mechanism within a task.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation+1



Sources:

[https://eliot.readthedocs.io/en/stable/generating/actions.html](https://eliot.readthedocs.io/en/stable/generating/actions.html?utm_source=chatgpt.com)

[https://eliot.readthedocs.io/en/stable/reading/fields.html](https://eliot.readthedocs.io/en/stable/reading/fields.html?utm_source=chatgpt.com)

### 2.2 Action creation and lifecycle control

Eliot provides several ways to express operations, with materially different lifecycle semantics.

| API                           | Purpose and distinction                                                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| `start_action()`              | Creates an action nested within the current context, or a root action if no context exists |
| `start_task()`                | Explicitly starts a new top-level task independently of an existing context                |
| `Action.context()`            | Temporarily establishes an action as the current context without finishing it on exit      |
| `Action.finish()`             | Explicitly terminates an action, with an optional exception                                |
| `Action.run()`                | Executes a callable in a particular action context                                         |
| `Action.add_success_fields()` | Adds structured fields to the eventual success event                                       |
| `current_action()`            | Retrieves the active action, or `None` when there is none                                  |
| `log_call()`                  | Wraps a synchronous function call in action logging                                        |
| `log_message()`               | Emits a standalone message, attaching to the current action if present                     |

The important distinction is between action lifetime and action-context lifetime.

A context manager using `with start_action(...)` owns both: it makes the action current and automatically finishes it on exit.

By contrast, `Action.context()` controls only which action is current. The action remains unfinished until `finish()` is called, allowing an operation to span callbacks, separate execution phases, or manually coordinated asynchronous boundaries.

This avoids implementing separate parent-operation registries merely to keep a diagnostic operation open across phases.

An illustrative example:

```
from eliot import start_action, log_messagedef process_document(document_id, payload):    with start_action(        action_type="document:process",        document_id=document_id,    ) as action:        with start_action(            action_type="document:parse",            input_bytes=len(payload),        ) as parsing:            records = parse(payload)            parsing.add_success_fields(record_count=len(records))        log_message(            message_type="document:validated",            record_count=len(records),        )        result = store(records)        action.add_success_fields(stored_count=result)        return result
```

The parse operation and validation message become children of the document-processing action. The successful completion of each action is recorded separately.

Two consequences deserve emphasis:

Success does not mean business-level success. Eliot considers an action successful when it exits without an unhandled exception. A function returning an error result or a rejection status still produces a successful Eliot action unless the application explicitly models that outcome.

An action's logical completion must match the real operation's completion. Finishing an action before its spawned work completes can produce misleading parent-child histories even if context propagation itself works correctly.

### 2.3 Function instrumentation

`@log_call` can automatically capture function arguments, a returned result, and success/failure:

```
from eliot import log_call@log_call(    action_type="model:evaluate",    include_args=["model_id"],    include_result=False,)def evaluate(model_id, large_input):    return run_evaluation(model_id, large_input)
```

The argument and result controls matter because automatically serializing large inputs, sensitive information, or complex return values may be expensive or inappropriate.

Important limitation for asynchronous functions: the 1.18.0 implementation of `log_call()` is a synchronous wrapper. Applied directly to an `async def`, it invokes the function and receives the coroutine object rather than awaiting its execution. Thus, the logged action does not span the coroutine's actual work. An explicit `with start_action(...)` inside the coroutine, or a correctly designed async wrapper, is necessary for that semantic behavior.

This distinction follows from the tagged implementation, rather than the older documentation's generic description.

Source: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/\_action.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/_action.py?utm_source=chatgpt.com)

## 3. Causal context propagation

Context propagation is where Eliot becomes more than structured logging. It can preserve a logical task hierarchy despite changes in execution location.

| Boundary                   | Native mechanism                                   | Important condition                                      |
| -------------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| Synchronous calls          | Implicit active action context                     | Normal nested execution                                  |
| `asyncio` coroutines/tasks | Python `contextvars`                               | Parent lifecycle still must encompass intended children  |
| Trio tasks                 | `contextvars`                                      | Nursery/action nesting affects lifecycle                 |
| Threads                    | `preserve_context()`                               | One-time wrapper usage and thread-local action ownership |
| Processes/network          | `serialize_task_id()` and `Action.continue_task()` | Identifier must be explicitly transported                |
| Twisted Deferreds          | `DeferredContext` and Eliot-specific decorators    | Use Eliot-aware callback/generator handling              |
| Dask distributed tasks     | `compute_with_trace()` / `persist_with_trace()`    | Execution-graph transformation and worker logging        |

### 3.1 Asyncio and Trio

Eliot uses Python's context-variable machinery to associate the current action with coroutine execution. This avoids manually passing a logging context through every asynchronous function.

For standard `asyncio` and Trio coroutine execution, the library documents automatic context propagation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation



However, inherited context is not equivalent to structured task ownership.

In particular, a newly scheduled asynchronous child may inherit an action context even if the parent exits before that child actually executes. This creates an apparent causal relationship whose lifecycle is inconsistent.

Trio's nursery structure provides a useful illustration: the parent Eliot action should enclose the nursery lifetime when that action is intended to represent all work performed by the nursery.

The same underlying consideration applies to `asyncio.TaskGroup`, detached tasks, and other background task creation patterns.

Documentation: [https://eliot.readthedocs.io/en/stable/generating/asyncio.html](https://eliot.readthedocs.io/en/stable/generating/asyncio.html?utm_source=chatgpt.com)

### 3.2 Threads and explicit cross-boundary propagation

`preserve_context()` captures the current Eliot context and returns a callable that restores it when executed in another thread.

The returned callable is one-time use. The upstream implementation enforces this, raising `TooManyCalls` when a preserved wrapper is invoked again.

This is a deliberate identity safeguard: duplicating an already reserved causal location could generate conflicting event positions.

For processes or network calls, the corresponding mechanism is explicit serialization:

```
serialized = current_action().serialize_task_id()# Transport serialized to another process.with Action.continue_task(task_id=serialized):    perform_remote_work()
```

The serialized identifier encodes the task UUID and a reserved task-tree location, rather than merely carrying a high-level correlation UUID.

`Action.continue_task()` starts a continuation action, normally named `eliot:remote_task`, but its action type and start fields can be customized.

Retry semantics: each independent continuation should receive a newly generated serialized identifier. Reusing a continuation token can produce duplicate event identities, breaking unambiguous causal reconstruction.

Eliot also does not automatically define an HTTP, RPC, or message-queue context propagation standard. Transport headers and extraction are application or integration responsibilities. The official example uses a custom `x-eliot-task-id` HTTP header.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation



Documentation: [https://eliot.readthedocs.io/en/stable/generating/threads.html](https://eliot.readthedocs.io/en/stable/generating/threads.html?utm_source=chatgpt.com)

## 4. Typed logging and event contracts

Eliot's optional typed logging layer is one of its more valuable capabilities, particularly where observability events are treated as stable engineering interfaces rather than incidental debugging output.

The principal abstractions are `Field`, `MessageType`, and `ActionType`.

### 4.1 Field definitions and validation

`Field` describes a structured event field using a name, serializer, description, and optional validation function.

`Field.for_types()` constrains accepted Python types; `Field.for_value()` constrains a field to a particular value. `fields()` provides a more compact way to assemble definitions.

`MessageType` declares the fields belonging to a named message, while `ActionType` separately declares the fields expected at action start and successful completion.

For example:

```
from eliot import ActionType, MessageType, fieldsEVALUATE = ActionType(    "model:evaluate",    fields(model_id=str, input_count=int),    fields(output_count=int, elapsed_iterations=int),    "Evaluate a model against a collection of inputs.",)CACHE_DECISION = MessageType(    "model:cache_decision",    fields(hit=bool, cache_key=str),    "Record a cache lookup decision.",)
```

This mechanism allows instrumentation contracts to express more than arbitrary JSON dictionaries.

The underlying event schema can distinguish a model-evaluation operation from a cache-decision event, constrain their fields, and provide reusable semantic definitions.

### 4.2 Serialization and validation are intentionally different

Eliot separates two processes:

| Operation                 | When performed                                | Consequence                                                      |
| ------------------------- | --------------------------------------------- | ---------------------------------------------------------------- |
| Field serialization       | During normal log emission                    | Converts values into representable event fields                  |
| Field validation          | Primarily during logging tests                | Checks required fields, unexpected fields, and value constraints |
| Destination JSON encoding | When an output destination serializes records | Converts the resulting record to its physical output format      |

This distinction avoids paying the full cost of type validation on every production event while still allowing test suites to enforce logging contracts.

A `Field` serializer may be used to convert domain objects into compact structured representations. That can eliminate repeated, ad hoc serialization code across instrumentation sites.

A limitation is that the typed schema is not automatically a universal data contract. It is a Python-side event declaration, and Eliot does not derive persistence schemas, JSON Schema documents, or OpenTelemetry semantic conventions from it.

Validation is opt-in through testing. Untyped events remain legal, and the output pipeline is not a universal runtime schema-enforcement layer.

Documentation: [https://eliot.readthedocs.io/en/stable/generating/types.html](https://eliot.readthedocs.io/en/stable/generating/types.html?utm_source=chatgpt.com)

Tagged implementation: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/\_validation.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/_validation.py?utm_source=chatgpt.com)

## 5. Serialization and output pipeline

### 5.1 Eliot 1.18 serialization capabilities

The most consequential changes after the version represented by Read the Docs occurred in Eliot 1.15–1.18.

Release-relevant distinctions

| Release | Consequential change                                                                                                           |
| ------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1.15.0  | Adopted `orjson` on CPython; moved JSON customization toward a `default` function instead of `JSONEncoder` subclasses          |
| 1.15.0  | Nonfinite floats become JSON `null` through `orjson`; removed deprecated bytes serialization behavior and `ThreadedFileWriter` |
| 1.16.0  | Added official Python 3.13 support                                                                                             |
| 1.17.x  | Expanded JSON serialization support for several Python data and scientific types                                               |
| 1.18.0  | Added fallback string representations for otherwise unsupported objects; official Python 3.14 support; dropped Python 3.9      |

The 1.18.0 `eliot.json.json_default()` implementation recognizes several additional object families:

| Family                        | Representation                                           |
| ----------------------------- | -------------------------------------------------------- |
| NumPy scalars                 | Corresponding Python numeric/boolean values              |
| NumPy arrays                  | Lists, or bounded-prefix representation for large arrays |
| `pathlib.Path`                | String path                                              |
| `date`, `time`                | ISO-formatted string                                     |
| Pydantic `BaseModel`          | `model_dump()` result                                    |
| Pandas `Series`, `DataFrame`  | List or record-oriented representation                   |
| Polars `Series`, `DataFrame`  | List or dictionary-record representation                 |
| Sets                          | Lists                                                    |
| Complex numbers               | `real` / `imag` object                                   |
| Otherwise unsupported objects | Safe `repr()`-style text fallback                        |

The relevant conversions use optional libraries when those libraries are already imported; Eliot does not require installing Pandas, Polars, NumPy, and Pydantic simply to generate ordinary logs.

On CPython, `orjson` supplies the main JSON serializer. On PyPy, Eliot uses the standard-library JSON pathway with additional type handling.

The revised behavior has significant implications:

Serialization failure is no longer a reliable indication that an object is unsuitable for a structured event. In 1.18, an unsupported object may simply be represented by text. This improves log survivability but can lose type semantics, queryability, and fidelity.

Likewise, automatically serializable does not imply inexpensive. A large DataFrame converted into record dictionaries can produce substantial telemetry volume.

Sources:

[https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/docs/source/news.rst](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/docs/source/news.rst?utm_source=chatgpt.com)

[https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/json.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/json.py?utm_source=chatgpt.com)

### 5.2 Output destinations

Eliot uses destination callables receiving event dictionaries. This is a flexible boundary between event construction and downstream storage.

`add_destinations()` registers destinations, and `remove_destination()` unregisters them.

`FileDestination` serializes each event as a JSON line to a file-like object. `to_file()` is the convenience entry point for constructing and registering one.

Custom destinations can route events to other infrastructure, alter output representation, or incorporate additional metadata.

The architecture makes it possible to keep event instrumentation independent from the final storage choice.

However, this flexibility also means destination behavior is important:

- Destination calls occur synchronously unless explicitly decoupled.
- A `FileDestination` writes and flushes each event.
- Destinations are expected not to raise or mutate records.
- Eliot attempts to report destination failures, but cannot guarantee delivery when output infrastructure fails.
- Custom destinations control their own serialization; not all necessarily use `eliot.json.json_default()`.

The 1.18 API detail: `to_file()` and `FileDestination()` accept `json_default`, a callable handling types the JSON serializer does not directly support. The older documentation still demonstrates an `encoder=` subclass argument; that path remains for compatibility but is deprecated.

Example:

```
from eliot import to_filefrom eliot.json import json_defaultdef encode_event_value(value):    if isinstance(value, DomainIdentifier):        return {            "namespace": value.namespace,            "value": value.value,        }    return json_default(value)to_file(    open("events.jsonl", "ab"),    json_default=encode_event_value,)
```

This is an illustrative extension pattern, not an executed example.

### 5.3 Initial buffering and global metadata

Eliot buffers up to 1,000 messages before the first destination is registered. When the first destination set is added, buffered messages are delivered.

This is useful for application startup, although it is not a durable queue: records beyond that capacity are evicted.

`add_global_fields()` adds metadata to every event, such as process identity, service name, software version, or deployment environment. These fields make aggregation and cross-process inspection more useful without requiring each instrumentation site to emit repetitive metadata.

The tagged implementation applies global fields during destination dispatch, so name collisions with event fields are worth avoiding.

Documentation: [https://eliot.readthedocs.io/en/stable/outputting/output.html](https://eliot.readthedocs.io/en/stable/outputting/output.html?utm_source=chatgpt.com)

Tagged output implementation: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/\_output.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/_output.py?utm_source=chatgpt.com)

### 5.4 Journald and Twisted-aware output

Eliot provides a native journald destination through `eliot.journald.JournaldDestination`, enabled with the `journald` extra. It uses `cffi` to call the systemd journal API.

It stores the JSON record in `MESSAGE` and exposes separately indexed fields including `ELIOT_TASK` and `ELIOT_TYPE`. Failed actions and explicitly logged tracebacks receive appropriate journal priorities, allowing filtering before JSON parsing.

For Twisted applications, `eliot.logwriter.ThreadedWriter` wraps a blocking destination in a dedicated writer-thread service. It integrates registration and deregistration into Twisted's `Service` lifecycle.

This avoids blocking the reactor on ordinary file I/O, but the implementation uses an unbounded `SimpleQueue` and does not provide durable delivery or a general backpressure mechanism.

The distinction is important: moving logging off an event-loop thread addresses latency coupling, not necessarily reliability or memory growth.

Sources:

[https://eliot.readthedocs.io/en/stable/outputting/journald.html](https://eliot.readthedocs.io/en/stable/outputting/journald.html?utm_source=chatgpt.com)

[https://eliot.readthedocs.io/en/stable/generating/twisted.html](https://eliot.readthedocs.io/en/stable/generating/twisted.html?utm_source=chatgpt.com)

[https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/logwriter.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/logwriter.py?utm_source=chatgpt.com)

## 6. Framework and legacy-logging integration

### 6.1 Python standard-library logging

`eliot.stdlib.EliotHandler` accepts conventional Python `logging.LogRecord` instances and emits corresponding Eliot messages.

The resulting events inherit the active Eliot action context, so existing logs can participate in the causal hierarchy without rewriting every logging call.

The bridge produces messages of type `eliot:stdlib` with fields including the original logger name, log level, and formatted message. Where `exc_info` is present, Eliot also records an explicit traceback.

One limitation is that the bridge uses `record.getMessage()`: structured values contained in the original `LogRecord` do not automatically become a complete Eliot field schema. Rich event preservation may require a specialized adapter.

Eliot itself has no native severity-level hierarchy comparable to the standard library's DEBUG/INFO/WARNING/ERROR/CRITICAL set. Severity is an ordinary event field; failed actions and traceback records are distinguished through their semantics.

This makes Eliot's primary diagnostic structure orthogonal to traditional severity-based filtering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation+1



Sources:

[https://eliot.readthedocs.io/en/stable/generating/migrating.html](https://eliot.readthedocs.io/en/stable/generating/migrating.html?utm_source=chatgpt.com)

[https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/stdlib.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/stdlib.py?utm_source=chatgpt.com)

### 6.2 Twisted integration

Eliot has unusually substantial native Twisted support. Its functionality addresses both context propagation and output integration.

| Mechanism                           | Function                                                                                                                |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `eliot.twisted.inline_callbacks`    | Twisted `inlineCallbacks` equivalent that correctly preserves Eliot context through generator suspension and resumption |
| `DeferredContext`                   | Wraps Deferred callback/errback registration so callbacks run under the captured Eliot context                          |
| `DeferredContext.addActionFinish()` | Finishes an action based on Deferred completion rather than immediate scope exit                                        |
| `TwistedDestination`                | Routes Eliot records into `twisted.logger`                                                                              |
| `redirectLogsForTrial()`            | Integrates Eliot logs into Twisted's `trial` test output                                                                |
| `ThreadedWriter`                    | Offloads destination I/O outside the reactor thread                                                                     |

The `DeferredContext` mechanism addresses a fundamental mismatch between lexical scope and asynchronous completion. If an action is started around Deferred creation, the ordinary context manager may finish before the Deferred's callbacks run.

`DeferredContext` allows callbacks and completion to remain associated with the intended action.

This is more than attaching a correlation identifier: it preserves the action's lifecycle semantics through an asynchronous callback chain.

The documentation also warns about logging redirection loops when both Eliot-to-Twisted and Twisted-to-Eliot routing are configured simultaneously.

Source: [https://eliot.readthedocs.io/en/stable/generating/twisted.html](https://eliot.readthedocs.io/en/stable/generating/twisted.html?utm_source=chatgpt.com)

## 7. Failure diagnostics and exception enrichment

Eliot distinguishes an action failing from an exception traceback being logged.

When an exception escapes an action's context, Eliot marks the action as `failed`, recording the exception's qualified type and textual reason.

It does not automatically record the full traceback on every failed action. This is deliberate: action failure records provide the causal location and outcome without necessarily duplicating stack traces at every level.

For stack-level diagnostics, Eliot provides `write_traceback()`. Twisted applications also have `writeFailure()` for Twisted `Failure` instances.

### Structured exception enrichment

`register_exception_extractor()` registers a callable that extracts additional structured fields from an exception.

For example, a domain exception containing a solver status, rejected configuration, or external response code can produce machine-queryable diagnostic fields rather than relying exclusively on exception prose.

Eliot searches registered exception types through their inheritance hierarchy, enabling an extractor defined for a base exception to cover related subclasses.

This provides a useful division of responsibility: exception classes retain operational error information, while Eliot's extractors expose selected attributes as telemetry.

### Failure semantics and limits

Three distinctions matter here.

Action failure is not a full stack trace. Explicit traceback emission remains useful for unexpected exceptions.

A caught exception does not necessarily fail its enclosing action. An application can recover, retry, emit a diagnostic message, and finish successfully. Such a result can be correct, provided retries and recoveries are represented meaningfully.

A structured exception is not automatically a root-cause diagnosis. Eliot exposes the causal execution hierarchy, but identifying a business or numerical root cause depends on the fields and operations the program actually records.

Documentation: [https://eliot.readthedocs.io/en/stable/generating/errors.html](https://eliot.readthedocs.io/en/stable/generating/errors.html?utm_source=chatgpt.com)

## 8. Scientific and distributed computation

Eliot includes features that are particularly useful for long-running computational workloads.

### 8.1 NumPy and large-array handling

Eliot recognizes NumPy scalar types and arrays, allowing computational inputs and intermediate results to appear as structured fields.

An important safeguard is its default array-size limit.

For NumPy arrays containing more than 10,000 elements, the JSON conversion records a bounded prefix and the original shape rather than serializing the complete array.

This is a serialization-volume safeguard, not a statistical summarization mechanism. The retained prefix is not necessarily representative, and the original array cannot be reconstructed from the logged information.

In computational workflows, other event representations may be more useful: dimensions, dtypes, extrema, convergence residuals, checksums, sample statistics, or references to persisted artifacts.

Eliot's typed fields and custom JSON conversion provide extension points for these representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation



Documentation: [https://eliot.readthedocs.io/en/stable/scientific-computing.html](https://eliot.readthedocs.io/en/stable/scientific-computing.html?utm_source=chatgpt.com)

### 8.2 Dask integration: reconstructing a task graph as causal events

Eliot's Dask integration is particularly distinctive.

Dask expresses computations as directed acyclic graphs, whereas Eliot's causal model is a forest of trees. The two representations are not structurally identical.

Eliot bridges them using explicit graph instrumentation.

Its two relevant functions are:

- `eliot.dask.compute_with_trace()`
- `eliot.dask.persist_with_trace()`

These wrap Dask computation operations and modify their execution graphs to preserve Eliot contexts across task execution.

The implementation first invokes Dask graph optimization and then wraps graph tasks with Eliot context restoration. Each wrapped task receives a reserved Eliot task identity and logs the task key together with its dependencies.

Consequently, the resulting data contains both the causal execution tree and information about the original graph dependencies.

This offers a useful combination of models:

| Information                              | Representation                              |
| ---------------------------------------- | ------------------------------------------- |
| Which operation launched the computation | Parent Eliot action                         |
| Which distributed work belongs to it     | Serialized task continuation                |
| What individual operation ran            | Child action and `dask:task` message        |
| What dataflow dependencies it had        | Logged Dask task keys and dependency fields |
| What happened inside the operation       | Additional nested Eliot actions/messages    |

The integration does not convert an arbitrary DAG into a mathematically equivalent tree. Dependencies are preserved separately as metadata.

Important limitations: Eliot's Dask source explicitly documents difficulty handling retries. Re-executed graph tasks may produce confusing causal histories. Also, `persist_with_trace()` does not imply that all future execution of persisted data has completed when the wrapper returns.

Worker processes need their own output configuration, and logs must be brought together for unified analysis.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation



Source: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/dask.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/dask.py?utm_source=chatgpt.com)

## 9. Reading, reconstructing, and querying causal histories

Eliot provides more than event generation. It also includes a programmatic parser for reconstructing action trees from stored records.

### 9.1 Built-in parser

`eliot.parse.Parser` reads serialized event dictionaries and reconstructs `Task` objects containing `WrittenAction` and `WrittenMessage` nodes.

The principal interfaces include:

| API                                           | Role                                                                              |
| --------------------------------------------- | --------------------------------------------------------------------------------- |
| `Parser.parse_stream()`                       | Reconstructs tasks from an iterable of event dictionaries                         |
| `Parser.add()`                                | Incrementally adds a record and returns completed tasks plus updated parser state |
| `Task.root()`                                 | Returns the root action/message                                                   |
| `Task.is_complete()`                          | Reports whether the causal task has been completely reconstructed                 |
| `WrittenAction.children`                      | Ordered child actions and messages                                                |
| `WrittenAction.start_time`, `end_time`        | Event-derived timing information                                                  |
| `WrittenAction.status`, `exception`, `reason` | Reconstructed outcome and failure context                                         |

An important implementation detail is that the parser accommodates records arriving before their parents by constructing intermediate action nodes as necessary.

This makes causal reconstruction more robust than simply sorting a log by its timestamps.

At the same time, the parser's notion of completeness depends on having the required records. A missing start, terminal event, or intermediate child can prevent a task from being recognized as complete.

`Parser.parse_stream()` yields remaining incomplete tasks at end-of-input, while incremental consumers must consider memory retention for unfinished tasks.

This parser makes the causal structure available to applications without requiring a separate tree visualization library.

Documentation: [https://eliot.readthedocs.io/en/stable/reading/reading.html](https://eliot.readthedocs.io/en/stable/reading/reading.html?utm_source=chatgpt.com)

Tagged source: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/parse.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/parse.py?utm_source=chatgpt.com)

### 9.2 Command-line and third-party inspection

Eliot has its own `eliot-prettyprint` utility, which formats individual JSON records for human inspection. It supports compact presentation and local-timezone formatting.

The separately distributed `eliot-tree` package provides the more powerful causal-tree visualization.

Companion package: eliot-tree 24.0.0, independently versioned from Eliot.

| Tool                           | Capabilities                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------- |
| `eliot-prettyprint`            | Formats individual Eliot records                                                 |
| `eliot-tree`                   | Renders action hierarchies with nested messages, fields, outcomes, and durations |
| `eliot-tree --task-uuid`       | Selects a particular causal task                                                 |
| `eliot-tree --start` / `--end` | Filters tasks by date/time                                                       |
| `eliot-tree --select`          | Filters using JMESPath expressions against event data                            |
| `jq`                           | Field-level extraction and transformation of JSON Lines                          |
| `eliot.parse`                  | Native Python reconstruction and programmable analysis                           |

`eliot-tree` also supports programmatic use and configurable output formatting.

Its streaming behavior has a material constraint: an in-progress tree is ordinarily not rendered until its root terminal event is encountered. Very long-running actions can therefore delay the appearance of their assembled histories.

The distinction between raw records and assembled trees is useful operationally. Individual events can remain immediately searchable even when an operation has not yet finished.

Companion source: [https://github.com/jonathanj/eliot-tree](https://github.com/jonathanj/eliot-tree?utm_source=chatgpt.com)

Package: [https://pypi.org/project/eliot-tree/](https://pypi.org/project/eliot-tree/?utm_source=chatgpt.com)

Official inspection documentation: [https://eliot.readthedocs.io/en/stable/reading/reading.html](https://eliot.readthedocs.io/en/stable/reading/reading.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 10. Testing observability as program behavior

One of Eliot's strongest capabilities is its explicit testing infrastructure.

Rather than treating log output as unverified diagnostic text, Eliot allows tests to assert that specific operations, transitions, and messages were recorded with the correct structure.

### 10.1 Capture and inspect log output

`eliot.testing.capture_logging` redirects normal Eliot logging to an in-memory logger during a test.

`MemoryLogger` exposes captured messages and associated serialization information, enabling tests to inspect emitted records without requiring a running log aggregation system.

Eliot supplies assertions for individual messages, actions, and hierarchical relationships.

| Facility                     | What can be verified                                 |
| ---------------------------- | ---------------------------------------------------- |
| `capture_logging()`          | Captured event output during a test                  |
| `MemoryLogger`               | In-memory records, serialization and traceback state |
| `assertHasMessage()`         | Existence and field values of a message              |
| `assertHasAction()`          | Action type, success status, start/end fields        |
| `LoggedAction.of_type()`     | Find logged actions of a particular type             |
| `LoggedMessage.of_type()`    | Find messages of a particular type                   |
| `LoggedAction.children`      | Immediate action/message relationships               |
| `LoggedAction.descendants()` | Nested causal relationships                          |
| `LoggedAction.type_tree()`   | Hierarchical structure of action/message types       |
| `check_for_errors()`         | Validation errors and unexpected traceback records   |
| `swap_logger()`              | Lower-level logger substitution                      |

For instance, a test can verify not merely that a parser emitted a warning, but that it emitted the warning within a particular parsing action and that the action eventually completed with the expected outcome.

This enables observability contracts to become testable aspects of application behavior.

### 10.2 Typed logging validation

When tests capture messages created using `MessageType` or `ActionType`, Eliot can validate the defined field contracts.

It can detect missing fields, unexpected fields, and invalid values according to registered `Field` definitions.

`MemoryLogger.flush_tracebacks()` allows explicitly expected traceback records to be acknowledged; otherwise, unexpected tracebacks can fail a logging test.

There is an important distinction for version 1.18: the generic JSON fallback can encode many unsupported values as string representations. Therefore, successful JSON encoding by itself is weaker evidence of a properly structured event than it was under stricter serialization behavior.

Typed field validation remains valuable for enforcing semantic structure.

### 10.3 Test isolation and asynchronous operation

`capture_logging()` integrates naturally with `unittest.TestCase` cleanup mechanisms.

For more specialized cases, such as asynchronous test methods or Twisted Deferred-based tests, the lower-level `swap_logger()` and `check_for_errors()` interfaces offer greater lifecycle control.

Because the default logger and destination configuration have process-global elements, tests that simultaneously manipulate logging configuration require attention to isolation. Thread-safe individual writes do not automatically make global logger replacement independent across concurrently executing tests.

The result is a framework for treating event schemas and causal relationships as maintained interfaces, rather than relying entirely on manual inspection.

Documentation: [https://eliot.readthedocs.io/en/stable/generating/testing.html](https://eliot.readthedocs.io/en/stable/generating/testing.html?utm_source=chatgpt.com)

Tagged source: [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/testing.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/testing.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eliot.readthedocs.io\&sz=32)

Eliot 1.14.0+0.g3584072 documentation



## 11. Architectural distinctions and important limitations

### 11.1 Eliot versus other logging and tracing models

Eliot occupies an interesting position between structured logging and distributed tracing.

| System           | Primary abstraction                                     | Important distinction                                                                      |
| ---------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Python `logging` | Logger, level, `LogRecord`, handler                     | Mature event routing and severity handling; causal hierarchy requires additional machinery |
| `structlog`      | Structured events, context binding, processor pipelines | Particularly focused on event construction, enrichment, and processing                     |
| Eliot            | Causally nested actions, tasks, typed messages          | Records why operations occurred through explicit causal relationships                      |
| OpenTelemetry    | Spans, trace contexts, metrics, logs, exporters         | Standardized telemetry model and broad cross-language instrumentation ecosystem            |

Eliot's `task_uuid`/`task_level` system is not the same representation as an OpenTelemetry trace/span identity.

It does not automatically emit W3C `traceparent` headers or OTLP spans merely because it can serialize causal contexts.

Interoperability can be implemented at integration boundaries, but requires decisions about identity mapping, parent-child relationships, completion, errors, and event attributes.

OpenTelemetry Python documentation: [https://opentelemetry.io/docs/languages/python/](https://opentelemetry.io/docs/languages/python/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry.io\&sz=32)

OpenTelemetry



### 11.2 Consequential limitations

| Concern               | Eliot behavior and implication                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Coverage              | Only instrumented actions/messages reveal domain-level causality; Eliot does not automatically discover arbitrary control flow    |
| Ordering              | Task-tree positions express causal structure, not a total real-time execution order across concurrent workers                     |
| Timekeeping           | Uses wall-clock timestamps; elapsed times across unsynchronized hosts require caution                                             |
| Incomplete operations | Crashes, lost records, and incorrectly managed lifecycles can produce unfinished action trees                                     |
| Task fan-out          | Context propagation does not guarantee parent actions remain open until all child work completes                                  |
| Correlation tokens    | Serialized task identifiers are not authentication credentials; untrusted remote context requires appropriate boundary validation |
| Log volume            | Detailed arguments, DataFrames, nested objects, and high-frequency actions can generate substantial payloads                      |
| Performance           | Normal file destinations can block; threaded output introduces queue and shutdown considerations                                  |
| Reliability           | No built-in durable delivery guarantee, retrying collector, or centralized retention system                                       |
| Severity              | No native severity taxonomy beyond action outcomes and traceback distinctions                                                     |
| Interoperability      | No automatic conversion of Eliot causal identities into OpenTelemetry/W3C trace identities is established by the reviewed APIs    |
| Dask semantics        | Task retries and DAG-to-tree projection have documented limitations                                                               |

These are not all reasons to avoid Eliot. Many follow directly from its decision to concentrate on causal event generation instead of owning an entire telemetry platform.

### 11.3 What native Eliot machinery can replace

From an architectural perspective, Eliot's most useful value is frequently the combination of several capabilities.

| General problem                                        | Native Eliot machinery that may remove custom implementation work |
| ------------------------------------------------------ | ----------------------------------------------------------------- |
| Correlating events from nested operations              | Action contexts and task-tree identifiers                         |
| Cross-thread or cross-process task relationships       | Context preservation and serialized continuation identifiers      |
| Tracking success/failure through operation hierarchies | Lifecycle-managed action records                                  |
| Maintaining structured diagnostic contracts            | `Field`, `MessageType`, `ActionType`, and testing facilities      |
| Reconstructing operation histories from raw events     | `eliot.parse`                                                     |
| Testing that diagnostics preserve causal meaning       | `LoggedAction`, `LoggedMessage`, and structural assertions        |
| Incorporating existing Python logging                  | `EliotHandler`                                                    |
| Instrumenting Dask computations                        | Dask graph wrappers and dependency logging                        |

The architectural opportunity is a unified event model: the same action structure can be used for operational troubleshooting, domain-level diagnostics, test assertions, and downstream analytical reconstruction.

The tradeoff is that Eliot remains an instrumentation component rather than a complete observability stack.

## 12. Version and documentation considerations

The current stable package is Eliot 1.18.0, but the hosted documentation labeled `stable` still identifies itself as version 1.14.0. The `latest` documentation channel is even older.

This matters materially because several examples in that documentation predate the `orjson` migration and the newer serialization behavior.

For 1.18 specifically, the tagged upstream source is the stronger authority for:

- JSON default-function behavior and deprecated encoder classes.
- Supported Python versions and packaging extras.
- Broader automatic object serialization.
- Removal of older APIs and runtime support.
- Precise synchronous behavior of `log_call()`.
- Current implementations of Dask wrappers, destinations, and testing helpers.

The core causal model, distributed continuation facilities, typed logging model, and most integration concepts remain consistent with the older published documentation.

### Primary source map

| Topic                             | Direct source                                                                                                                                                                                                                       |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version-specific release notes    | [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/docs/source/news.rst](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/docs/source/news.rst?utm_source=chatgpt.com) |
| Actions, nesting, task identity   | [https://eliot.readthedocs.io/en/stable/generating/actions.html](https://eliot.readthedocs.io/en/stable/generating/actions.html?utm_source=chatgpt.com)                                                                             |
| Event fields and ordering         | [https://eliot.readthedocs.io/en/stable/reading/fields.html](https://eliot.readthedocs.io/en/stable/reading/fields.html?utm_source=chatgpt.com)                                                                                     |
| Typed messages and actions        | [https://eliot.readthedocs.io/en/stable/generating/types.html](https://eliot.readthedocs.io/en/stable/generating/types.html?utm_source=chatgpt.com)                                                                                 |
| Distributed context propagation   | [https://eliot.readthedocs.io/en/stable/generating/threads.html](https://eliot.readthedocs.io/en/stable/generating/threads.html?utm_source=chatgpt.com)                                                                             |
| Asyncio and Trio                  | [https://eliot.readthedocs.io/en/stable/generating/asyncio.html](https://eliot.readthedocs.io/en/stable/generating/asyncio.html?utm_source=chatgpt.com)                                                                             |
| Twisted                           | [https://eliot.readthedocs.io/en/stable/generating/twisted.html](https://eliot.readthedocs.io/en/stable/generating/twisted.html?utm_source=chatgpt.com)                                                                             |
| Output destinations               | [https://eliot.readthedocs.io/en/stable/outputting/output.html](https://eliot.readthedocs.io/en/stable/outputting/output.html?utm_source=chatgpt.com)                                                                               |
| Current JSON serialization source | [https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/json.py](https://github.com/itamarst/eliot/blob/92ecc03d3e557e2a55c78eefc763193587650600/eliot/json.py?utm_source=chatgpt.com)               |
| Scientific computing / Dask       | [https://eliot.readthedocs.io/en/stable/scientific-computing.html](https://eliot.readthedocs.io/en/stable/scientific-computing.html?utm_source=chatgpt.com)                                                                         |
| Testing infrastructure            | [https://eliot.readthedocs.io/en/stable/generating/testing.html](https://eliot.readthedocs.io/en/stable/generating/testing.html?utm_source=chatgpt.com)                                                                             |
| Parsing and inspecting logs       | [https://eliot.readthedocs.io/en/stable/reading/reading.html](https://eliot.readthedocs.io/en/stable/reading/reading.html?utm_source=chatgpt.com)                                                                                   |
| Companion tree renderer           | [https://github.com/jonathanj/eliot-tree](https://github.com/jonathanj/eliot-tree?utm_source=chatgpt.com)                                                                                                                           |

## Overall assessment

Eliot's most distinctive contribution is the treatment of causal structure as a first-class property of logging.

Its action model, hierarchical event identities, explicit distributed continuation, optional typed event definitions, and structural testing infrastructure provide capabilities that are usually assembled separately when using conventional structured-logging libraries.

For complex Python systems, particularly those involving asynchronous execution, distributed operations, multi-stage computation, or domain-specific diagnostics, Eliot can provide a coherent causal record with relatively little custom tracing machinery.

Its principal limitations are equally clear: its telemetry is only as meaningful as its instrumentation, event generation is not guaranteed delivery, its own task identities are not interoperable tracing standards, and its synchronous destinations and automatic value serialization require attention to cost.

The most consequential architectural distinction is therefore Eliot as a causal event model, with storage, search, visualization, standardized telemetry exchange, and operational reliability delegated to complementary systems.