# python-json-logger — Comprehensive Python Library Overview

Target version: 4.2.0 (latest stable) · Research date: November 1, 2026 · Python 3.10–3.14 · BSD-2-Clause

python-json-logger is a structured JSON formatting library for Python's standard `logging` framework. It converts `logging.LogRecord` objects into machine-readable JSON while retaining the existing logger hierarchy, handlers, filters, levels, propagation, and logging configuration infrastructure.

Version 4.2.0 was released August 15, 2026. The active distribution is maintained by Nicholas Hairs; the original `madzak/python-json-logger` repository was archived in December 2024. The maintained fork continues under the same PyPI package name, with versions 3.0 and later.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Official sources

- Documentation: `https://nhairs.github.io/python-json-logger/latest/`
- Repository: `https://github.com/nhairs/python-json-logger`
- PyPI: `https://pypi.org/project/python-json-logger/`
- Changelog: `https://nhairs.github.io/python-json-logger/latest/changelog/`

## 1. Architectural orientation

The library's principal abstraction is a JSON-aware `logging.Formatter`. Rather than introducing a separate logging API, it transforms standard logging records into structured dictionaries and serializes those dictionaries through a configurable JSON backend.

Conceptual pipeline: Python logging manages record generation, routing, and emission; python-json-logger owns field projection and JSON formatting.

The distinction matters because JSON formatting and structured logging are related but not identical. `python-json-logger` can preserve structured application data, customize a record's output schema, and serialize nonstandard Python objects. It does not independently provide distributed tracing, context propagation, asynchronous log delivery, storage, search, retention, or an observability backend.

Its architectural value is concentrating output-schema construction and serialization at the formatter boundary, avoiding the need to replace existing logging infrastructure or manually construct JSON for individual logging calls.

## 2. Capability map

| Capability family             | Principal mechanisms                                              | Architectural significance                                                   |
| ----------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| JSON formatting               | `JsonFormatter`, `BaseJsonFormatter`                              | JSON output using existing logging infrastructure                            |
| Field selection               | `fmt`, `style`, `reserved_attrs`                                  | Control standard metadata without custom record-to-dictionary code           |
| Structured event data         | Dictionary messages, `extra`, custom `LogRecord` attributes       | Preserve named, typed fields rather than embedding them in message strings   |
| Schema shaping                | `defaults`, `static_fields`, `rename_fields`                      | Normalize output contracts for downstream log consumers                      |
| Serialization                 | Standard `json`, `orjson`, `msgspec` backends                     | Choose encoding behavior independently of field extraction                   |
| Type adaptation               | `JsonEncoder`, `json_default`, `pythonjsonlogger.defaults`        | Represent unsupported Python objects without manually converting every value |
| Exception and stack reporting | `exc_info`, `stack_info`, array-format options                    | Preserve diagnostic information in structured records                        |
| Context enrichment            | Standard logging filters, `LoggerAdapter`, formatter hooks        | Add contextual metadata across logging calls                                 |
| Extension                     | `add_fields`, `process_log_record`, `parse`, `jsonify_log_record` | Customize projection, transformation, field syntax, or encoding              |
| Configuration                 | `dictConfig`, formatter constructors, `ext://` resolution         | Centralize structured logging policy through standard configuration          |

## 3. Structured event construction and field semantics

### 3.1 Three sources of event information

A formatter can receive structured information through three distinct mechanisms.

Ordinary messages use the familiar Python logging API:

```
logger.info(    "Processed %d items",    count,    extra={"batch_id": "b42", "duration_ms": 18.5},)
```

The message is interpolated through the standard `LogRecord.getMessage()` mechanism. The additional fields are retained as attributes on the logging record, subsequently extracted by the JSON formatter.

Dictionary messages use the message object itself as a structured event:

```
logger.info({    "event": "batch_completed",    "batch_id": "b42",    "items": 120,    "duration_ms": 18.5,})
```

Here, the dictionary contributes top-level JSON fields, rather than being serialized into a single message string. If the dictionary does not provide a `message` entry, a formatter requesting that field uses an empty message value.

Record enrichment adds attributes upstream of the formatter, through standard logging facilities such as filters, `LoggerAdapter`, or a custom record factory. These attributes are processed alongside `extra`.

This last mechanism is particularly useful because libraries need not directly depend on `python-json-logger` to participate in structured output. They only need to produce ordinary `LogRecord` instances with useful attributes.

As of 4.2.0, formatting a dictionary message copies the dictionary before adding exception and stack details, rather than modifying the caller's original object.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



### 3.2 `fmt` is a field selector, not a JSON template

An important distinction from text-oriented formatters is that `fmt` identifies the `LogRecord` attributes that should become JSON fields.

The formatter supports four styles:

| Style    | Example                     | Distinction                                          |
| -------- | --------------------------- | ---------------------------------------------------- |
| `%`      | `%(levelname)s %(message)s` | Familiar standard logging syntax                     |
| `{`      | `{levelname}{message}`      | Brace-style field references                         |
| `$`      | `$levelname ${message}`     | Template-style references                            |
| `,`      | `levelname,message`         | Package-specific comma-separated field list          |
| Sequence | `["levelname", "message"]`  | Direct specification without parsing a format string |

The last two options were introduced in 4.0. Version 4.2 corrected `$` parsing to recognize both `$name` and `${name}`.

The original `fmt` string is not used as a text rendering template. The formatter extracts the field names and assigns their corresponding values to the JSON object. Nonstandard fields supplied through `extra` are also included automatically unless excluded.

Consequently, specifying only `["message", "levelname"]` does not automatically discard a custom `request_id` attribute.

This makes `fmt` a projection mechanism for standard logging attributes, rather than a strict output schema or an allowlist for all fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



### 3.3 Field precedence and overwrite behavior

`BaseJsonFormatter.add_fields()` constructs each JSON record from multiple sources in a defined order.

| Precedence | Source                               | Behavior                                        |
| ---------- | ------------------------------------ | ----------------------------------------------- |
| 1 — Lowest | `defaults`                           | Fallback values available to be overridden      |
| 2          | Fields selected by `fmt`             | Values read from the `LogRecord`                |
| 3          | `static_fields`                      | Reusable formatter-level values                 |
| 4          | Dictionary message fields            | Structured data supplied as the message         |
| 5          | Non-reserved `LogRecord` attributes  | Includes fields supplied through `extra`        |
| 6          | Generated timestamp, if enabled      | Added after other fields                        |
| 7          | Missing renamed fields, if requested | Adds `None` only for absent renamed output keys |

When two sources resolve to the same output field, the later source wins. `rename_fields` is applied during this assembly process, not as a separate postprocessing pass.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



The distinction between `defaults` and `static_fields` is especially important:

- `defaults` is suitable for values that individual events may replace.
- `static_fields` has higher precedence than fields selected through `fmt`, but can still be replaced by dictionary messages or non-reserved record attributes.
- Neither mechanism guarantees an immutable value or an enforced schema.

There is a subtle interaction with reserved fields: a field already selected through `fmt` is excluded from the later generic merge. Thus `static_fields` can override a selected field even when the original value was present on the record.

### 3.4 Reserved attributes and implicit expansion

By default, `RESERVED_ATTRS` includes the standard Python logging metadata: `name`, `levelno`, `levelname`, `pathname`, `lineno`, `funcName`, `thread`, `process`, `created`, and others.

These attributes are excluded from automatic inclusion, but can be requested explicitly through `fmt`.

```
from pythonjsonlogger.core import RESERVED_ATTRSfrom pythonjsonlogger.json import JsonFormatterformatter = JsonFormatter(    ["message", "levelname", "name"],    reserved_attrs=RESERVED_ATTRS + ["internal_payload"],)
```

Conversely, `reserved_attrs=[]` includes all available record attributes except those separately skipped or prefixed with an underscore. This can provide comprehensive diagnostics without manually listing the standard fields.

The default reserved set varies with Python's `LogRecord` definition; for example, `taskName` is included for Python 3.12 and later.

A consequence is that automatic inclusion is not the same as a strict security or schema filter. Explicitly selected fields, dictionary messages, and fields introduced by other hooks must also be considered when constructing a controlled output schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 3.5 Renaming and missing-value behavior

`rename_fields` maps input names to output keys:

```
JsonFormatter(    ["message", "levelname", "name"],    rename_fields={        "levelname": "severity",        "name": "logger",        "message": "body",    },)
```

The behavior has several useful characteristics:

- Renaming applies to defaults, selected fields, static fields, dictionary messages, and extracted attributes.
- Renaming preserves the relative insertion order of fields.
- Missing source fields are normally omitted rather than emitted as `null`.
- `rename_fields_keep_missing=True` introduces `None` for missing renamed output keys, which serializes as JSON `null`.

This supports both sparse event formats and fixed-key output shapes. However, the fixed-key option does not validate types, required values, or schema compatibility.

A dotted renamed key is still a literal JSON key. For example, `"log.level"` does not automatically create `{"log": {"level": ...}}`. Nested object construction requires a separate transformation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



## 4. Serialization backends and Python type handling

The library separates event-field construction from JSON serialization. Three formatter implementations share the same `BaseJsonFormatter` machinery but delegate encoding to different libraries.

### 4.1 Available backends

| Backend          | Formatter                                   | Encoding mechanism                           | Distinctive options                                                                                      |
| ---------------- | ------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Standard library | `pythonjsonlogger.json.JsonFormatter`       | `json.dumps` and the package's `JsonEncoder` | Custom encoder, serializer, `json_default`, indentation, ASCII escaping                                  |
| orjson           | `pythonjsonlogger.orjson.OrjsonFormatter`   | `orjson.dumps`                               | Custom `json_default`, optional two-space indentation, non-string JSON key support within orjson's rules |
| msgspec          | `pythonjsonlogger.msgspec.MsgspecFormatter` | Reusable `msgspec.json.Encoder`              | Custom `json_default` passed as `enc_hook`                                                               |

The standard backend requires no additional JSON package. The other two require their corresponding libraries to be installed separately; importing their formatter modules without the dependency raises `MissingPackageError`, an `ImportError` subclass.

The package's 4.2.0 metadata does not declare installation extras for these backends, so `orjson` and `msgspec` should be treated as separately managed dependencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



Primary implementation references:

- `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/json/`
- `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/orjson/`
- `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/msgspec/`

### 4.2 Standard-library `JsonFormatter`

This is the most configurable backend:

```
JsonFormatter(    json_default=None,    json_encoder=None,    json_serializer=json.dumps,    json_indent=None,    json_ensure_ascii=True,)
```

Its native `JsonEncoder` extends `json.JSONEncoder` to handle additional Python types. The `format_datetime_obj()` method is itself overridable, allowing date/time representation to be changed independently of the rest of the encoder.

`json_serializer` can replace `json.dumps`, but the callable must accept the keyword arguments used by the formatter: `default`, `cls`, `indent`, and `ensure_ascii`, and return a string.

Important customization interaction: the library installs its built-in `JsonEncoder` only when both `json_encoder` and `json_default` are absent. Supplying a custom `json_default` therefore changes fallback behavior; it does not merely add one more type to an otherwise unchanged encoding pipeline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+1



### 4.3 orjson and msgspec

Both accelerated backends receive the same constructed `log_data` dictionary but have different type systems and option surfaces.

`OrjsonFormatter` uses `orjson.dumps` with `OPT_NON_STR_KEYS`, optionally adds `OPT_INDENT_2`, and decodes the encoder's UTF-8 bytes to the string expected by Python's logging formatter interface. Its default callback delegates handling of unsupported values to `orjson_default`.

`MsgspecFormatter` constructs one `msgspec.json.Encoder(enc_hook=json_default)` per formatter instance and reuses it across records. Its public constructor does not expose the same indentation or encoder-configuration controls as the standard-library formatter.

Both backends may natively serialize types that would pass through a fallback callback in another backend. Therefore, the choice can affect observable JSON representations, not just throughput.

For example, msgspec's documented enum handling is limited to enums with integer or string values; an arbitrary custom enum payload should not be assumed to have the same encoding across all three backends.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



The performance opportunity is avoiding some of the standard Python JSON encoding work, but serializer speed is not equivalent to end-to-end logging throughput. Event construction, exception formatting, handler locks, stream writes, and the conversion back to a Python string remain relevant. No universal quantitative speedup follows from choosing either backend.

### 4.4 Built-in fallback representations

`pythonjsonlogger.defaults` exposes reusable predicate/conversion pairs, such as `use_bytes_default()` and `bytes_default()`, for composing custom encoding behavior.

| Value category             | Package-provided representation                                          |
| -------------------------- | ------------------------------------------------------------------------ |
| `date`, `time`, `datetime` | ISO-format strings                                                       |
| `bytes`, `bytearray`       | URL-safe Base64 strings                                                  |
| Dataclass instances        | Dictionaries via `dataclasses.asdict()`                                  |
| Enum instances             | Their underlying values                                                  |
| Enum classes               | Lists of their member values                                             |
| Exception instances        | Exception class name and message                                         |
| Traceback objects          | Formatted traceback text                                                 |
| Class objects              | Class name                                                               |
| UUIDs                      | String form, through the dedicated helper or supported encoder behavior  |
| Unknown objects            | `str(obj)`, then `repr(obj)`, then `"__could_not_encode__"` if both fail |

These are available helper representations; the exact path taken depends on the chosen serializer and the types it handles natively. Not every backend explicitly calls every helper. For example, `msgspec_default` and `orjson_default` are smaller dispatch functions than the standard-library `JsonEncoder`, relying on their underlying encoders for more native types.

The result is deliberately tolerant observability serialization rather than a lossless, reversible object representation. Exception types, raw bytes, object identity, Python class semantics, and arbitrary custom state are not preserved automatically. The value of the fallback is that unfamiliar objects frequently remain representable in a log rather than causing serialization to fail.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



Source: `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/defaults/`

### 4.5 Custom serializers and error boundaries

For the orjson backend, a custom handler can delegate unrecognized objects back to the package's default:

```
from pythonjsonlogger.orjson import OrjsonFormatter, orjson_defaultdef encode_special(obj):    if isinstance(obj, DomainEvent):        return {            "kind": obj.kind,            "identifier": obj.identifier,        }    return orjson_default(obj)formatter = OrjsonFormatter(json_default=encode_special)
```

Illustrative code; `DomainEvent` represents an application-defined type.

The analogous msgspec callback is `msgspec_default`. For the standard-library backend, customization can instead use a `JsonEncoder` subclass or compose a fallback explicitly.

Custom callbacks can introduce serialization failures. A callback that raises, returns an object the encoder still cannot handle, or recursively produces unsupported objects can cause formatting to fail. The built-in unknown-object fallback is intentionally permissive, but it cannot guarantee that arbitrary user-provided serializers succeed.

This is an important design distinction: type adaptation is a policy boundary, not just a convenience for debugging. It determines how much of a domain object becomes observable data, what is lost, and whether a log record can be emitted at all.

## 5. Time, exceptions, and diagnostic fidelity

### 5.1 Timestamp mechanisms

Two different mechanisms deserve separate treatment.

| Mechanism                                                    | Source                           | Representation                                                                      |
| ------------------------------------------------------------ | -------------------------------- | ----------------------------------------------------------------------------------- |
| `timestamp=True`                                             | `record.created`                 | UTC-aware `datetime`, encoded by the selected JSON backend                          |
| `timestamp="event.time"`                                     | Same                             | UTC-aware timestamp with an explicitly named output key                             |
| `asctime` selected through `fmt`                             | `logging.Formatter.formatTime()` | Formatted string following standard logging's `datefmt` and time-converter behavior |
| `created`, `msecs`, `relativeCreated` selected through `fmt` | Native `LogRecord` attributes    | Numeric record metadata                                                             |

The `timestamp` option derives its value from the record's creation time, not from the moment the handler writes the output. It is added after the usual field merge, so it also has unusually high field precedence.

By contrast, `asctime` is computed only when included in the requested fields. Its default representation uses the normal logging formatter behavior rather than necessarily matching the UTC ISO representation of `timestamp`.

This distinction matters when downstream systems require a single canonical time field, when records cross queues or processes, or when consumers expect a specific timezone and timestamp type.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+1



### 5.2 Exceptions and stack traces

The formatter handles the standard logging diagnostic paths:

- `exc_info=True` or `logger.exception(...)` supplies exception information, normally rendered under `exc_info`.
- `stack_info=True` supplies the current call stack, rendered under `stack_info`.
- `exc_info_as_array=True` and `stack_info_as_array=True` split formatted diagnostic text into arrays of lines rather than single strings.
- Cached `record.exc_text` is recognized when `record.exc_info` is unavailable, supporting records that have already had exception text prepared upstream.

Array formatting was introduced in version 3.3.0. It is a representation choice: the library does not turn a Python traceback into a typed graph of frames, source spans, exception causes, and local variables.

A dictionary message can explicitly provide `exc_info` or `stack_info`; the built-in diagnostic value does not unconditionally replace a nonempty user-provided value.

The distinction between `exc_info` and ordinary exception objects also matters: an exception instance supplied through `extra` is handled by the JSON encoder's object fallback, whereas `exc_info=True` produces a formatted traceback.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+1



Direct API reference: `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/core/`

## 6. Integration with Python's logging infrastructure

### 6.1 Centralized configuration

Because the package provides normal `logging.Formatter` subclasses, it can be integrated through `logging.config.dictConfig()` rather than requiring application-wide changes to how loggers are obtained or how messages are emitted.

A representative configuration:

```
import logging.configlogging.config.dictConfig({    "version": 1,    "disable_existing_loggers": False,    "formatters": {        "json": {            "()": "pythonjsonlogger.json.JsonFormatter",            "fmt": ["message", "levelname", "name"],            "timestamp": True,            "rename_fields": {"levelname": "severity"},            "static_fields": {"service": "example"},            "json_ensure_ascii": False,        },    },    "handlers": {        "console": {            "class": "logging.StreamHandler",            "stream": "ext://sys.stdout",            "formatter": "json",        },    },    "root": {"level": "INFO", "handlers": ["console"]},})
```

The `()` entry selects the custom formatter factory. The remaining formatter-specific options are forwarded to its constructor. Handler selection, stream choice, logging levels, and propagation remain standard-library responsibilities.

An advantage is that independently authored libraries using `logging.getLogger(__name__)` can produce JSON output without depending on `python-json-logger` directly.

Since version 4.0, nested values supplied to `rename_fields` and `static_fields` can use logging configuration's `ext://` and `cfg://` object resolution, enabling configuration-driven enrichment without bespoke parsing.

One documentation caveat: the upstream cookbook shows YAML under a section titled `fileConfig`. Python's actual `fileConfig()` expects `configparser`/INI syntax; a YAML mapping should be parsed and passed to `dictConfig()`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



Source references:

- Package cookbook: `https://nhairs.github.io/python-json-logger/latest/cookbook/`
- Python logging configuration: `https://docs.python.org/3/library/logging.config.html`

### 6.2 Contextual information and correlation IDs

The library will serialize non-reserved custom attributes already present on a `LogRecord`. It does not itself establish, propagate, or isolate execution context.

The primary integration mechanisms are inherited from standard logging:

| Mechanism                       | Context acquisition                               | Important distinction                                    |
| ------------------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| `extra={...}`                   | Individual logging call                           | Explicit, per-event context                              |
| `logging.LoggerAdapter`         | Adapter-provided attributes                       | Reusable context associated with a logger wrapper        |
| `logging.Filter`                | Record mutation during filtering                  | Shared enrichment at a logger or handler boundary        |
| `logging.setLogRecordFactory()` | Record construction                               | Central interception of record creation                  |
| `contextvars.ContextVar`        | Context-local state read by a filter or formatter | Can isolate context across concurrent asynchronous tasks |
| `process_log_record()`          | Formatter-time lookup or transformation           | Enrichment occurs at the output boundary                 |

The upstream cookbook demonstrates request/trace ID injection through `extra`, filters, and formatter subclassing. Python's own logging cookbook documents how `contextvars` can provide per-request information for threads and `asyncio`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



In distributed systems, there is a meaningful timing distinction:

- Context attached when the record is created travels as part of that record, subject to transport serialization.
- Context looked up later in `process_log_record()` depends on the execution context of the thread or task performing formatting.

Consequently, formatter-time context lookup is not automatically equivalent to producer-time context capture when records cross asynchronous queues, threads, or processes.

### 6.3 Transport and buffering remain separate

`python-json-logger` does not implement a new handler, queue, or transport protocol. It composes with existing `StreamHandler`, `FileHandler`, rotating handlers, queue-based logging, and third-party handlers.

This introduces a particularly important integration constraint with `logging.handlers.QueueHandler`: the standard `prepare()` implementation formats messages and clears attributes such as `args`, `exc_info`, and `exc_text` to make records easier to enqueue and transport. A downstream JSON formatter may therefore receive a transformed record rather than the original structured event.

In particular, formatting to JSON before queuing and then formatting again at the consumer can produce an unintended JSON-string-inside-JSON representation.

The queue boundary should preserve the desired event structure and diagnostic information through a deliberate preparation/formatting arrangement; that behavior is controlled by Python logging, not automatically resolved by the package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.0 documentation+1



Python logging handlers: `https://docs.python.org/3/library/logging.handlers.html`

## 7. Formatter extension architecture

The main extension point is `BaseJsonFormatter`, an abstract `logging.Formatter` subclass. Its design separates field selection, record enrichment, representation transformation, and final serialization.

### 7.1 Formatting pipeline

The effective 4.2.0 flow is:

```
logging.LogRecord
    │
    ├─ string message → record.getMessage()
    │  dictionary message → shallow copy of dictionary
    │
    ├─ compute requested asctime
    ├─ collect exception and stack text
    │
    ▼
add_fields(log_data, record, message_dict)
    ├─ defaults
    ├─ fmt-selected fields
    ├─ static_fields
    ├─ dictionary message
    ├─ non-reserved LogRecord attributes
    └─ optional UTC timestamp / absent-field markers
    │
    ▼
process_log_record(log_data)
    │
    ▼
serialize_log_record(log_data)
    └─ prefix + jsonify_log_record(log_data)
    │
    ▼
formatted string → logging handler
```

The explicit separation of these phases allows schema transformations and alternative encoding strategies to share the same log-record extraction semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger



### 7.2 Extension hooks and their responsibilities

| Hook                                         | Role                                           | Appropriate customization                                     |
| -------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------- |
| `parse()`                                    | Determine fields selected by `fmt`             | Custom formatting syntax or alternative field-selection rules |
| `add_fields(log_data, record, message_dict)` | Construct the dictionary to encode             | Specialized field extraction, inclusion, or precedence        |
| `process_log_record(log_data)`               | Transform the complete event dictionary        | Redaction, key normalization, nesting, derived fields         |
| `formatException(ei)`                        | Render exception information                   | Alternative exception representation                          |
| `formatStack(stack_info)`                    | Render stack information                       | Alternative stack representation                              |
| `jsonify_log_record(log_data)`               | Convert the dictionary to JSON text            | New serialization backend                                     |
| `serialize_log_record(log_data)`             | Return the final string                        | Final framing or presentation behavior                        |
| `merge_record_extra(...)`                    | Utility for extracting non-reserved attributes | Reuse native extra-field logic in custom formatters           |

`process_log_record()` receives the assembled output dictionary and must return the dictionary to serialize. It is the least invasive extension point for operations that do not need access to the original `LogRecord`.

For example:

```
from pythonjsonlogger.json import JsonFormatterclass NormalizedJsonFormatter(JsonFormatter):    def process_log_record(self, log_data):        log_data.pop("internal_token", None)        log_data["schema_version"] = 1        return log_data
```

This changes output without changing how callers log messages. For a more complete redaction policy, nested values, alternative field names, and multiple handlers would also need to be accounted for.

Overriding `add_fields()` is more powerful but exposes the caller to responsibility for the extraction order, reserved-field rules, and default timestamp semantics.

A completely new encoder can subclass `BaseJsonFormatter` and implement `jsonify_log_record()`, which must return a string. This permits additional backend implementations without recreating the field-processing logic.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+2



### 7.3 Important extension distinctions

Transformation versus enrichment. `process_log_record()` operates after extraction and renaming. It sees final output keys, not necessarily the original `LogRecord` attribute names. A transformation that needs native caller information can instead use `add_fields()` or override `format()`.

Custom styles versus native styles. `style=","` is already supported in 4.x. For genuinely new syntax, `validate=False` together with a custom `parse()` implementation can be used. This is distinct from Python's own standard formatter style support.

Prefix versus structured fields. `prefix` prepends literal characters to the serialized string. It does not create a JSON field. A nonempty prefix can make the resulting line invalid as standalone JSON even when the serialized dictionary is valid.

Formatter extensibility versus central logging policy. Subclassing a formatter affects only handlers using that formatter. A logging filter or record factory operates at a different boundary and can affect additional handlers or output formats.

The extension surface is therefore sufficiently modular for many custom JSON output requirements without introducing a separate structured logging framework. The appropriate hook depends on whether the desired semantics belong to record creation, event extraction, output schema, or serialization.

Direct source: `https://github.com/nhairs/python-json-logger/blob/v4.2.0/src/pythonjsonlogger/core.py`

## 8. Operational characteristics and limitations

### 8.1 JSON formatting is not strict schema enforcement

The library produces JSON objects, but it does not validate those objects against JSON Schema, ECS, OpenTelemetry semantic conventions, or an application-specific event contract.

Several behaviors affect schema consistency:

| Issue                          | Consequence                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------- |
| Automatic inclusion of `extra` | New attributes can change the output structure without formatter changes        |
| Dictionary messages            | Individual callers can introduce arbitrary event fields                         |
| Field collisions               | Later sources overwrite earlier sources according to the established precedence |
| `rename_fields`                | Renamed keys can collide with preexisting output names                          |
| `rename_fields_keep_missing`   | Missing fields become JSON `null`, not validated placeholders                   |
| Custom serialization fallback  | Unsupported objects may become strings rather than structured data              |
| Literal dotted field names     | Nested schema structures are not automatically generated                        |

For logs consumed as a stable data contract, field validation, schema normalization, and stricter control over unrecognized attributes must be supplied through application conventions, formatter extensions, or downstream processing.

An especially subtle limitation is that `reserved_attrs` only participates in the automatic record-attribute merge. It is not a universal output suppression mechanism for every source or every phase of formatting.

### 8.2 Newline-delimited JSON and output framing

The common deployment format is one JSON object per line, usually written to stdout, stderr, or a log file.

`JsonFormatter` returns a JSON string; the standard `StreamHandler` adds its normal line terminator. With default compact serialization and no prefix, this produces conventional JSON-lines-style output.

However:

- `json_indent` on the standard or orjson backend can introduce actual line breaks within a single record.
- `prefix` can add characters before the opening JSON object.
- A custom serializer may produce a representation unsuitable for line-oriented consumers.
- Multiple processes sharing an output destination require coordination from the handler or collection infrastructure.

Thus, JSON validity and newline-delimited framing are distinct properties. A record can contain valid JSON while the resulting output stream no longer represents one JSON value per physical line.

### 8.3 Serialization cost and logging overhead

The formatters run only when the standard logging pipeline sends a record to an enabled handler. Disabled logging levels do not incur JSON serialization cost.

Nevertheless, logging calls may still evaluate arguments and construct objects before the logging framework decides to discard the event.

The cost structure is approximately:

\\[ T\_{\text{event}} = T\_{\text{record}}+ T\_{\text{field extraction}}+ T\_{\text{transform}}+ T\_{\text{serialization}}+ T\_{\text{handler}} \\]

This is a conceptual decomposition, not a benchmark or claim that these stages are independent.

The most consequential performance considerations are:

- Field extraction: iterating over `LogRecord` attributes and merging dictionaries is per-event Python work common to all backends.
- Object encoding: large nested structures, exceptions, dataclasses, and fallback string conversion can dominate serializer cost.
- Alternative encoders: orjson and msgspec can reduce encoding overhead for suitable data, but do not eliminate surrounding formatter and handler work.
- Multiple handlers: distinct formatters can separately serialize the same record.
- Handler delivery: synchronous stream writes, handler locks, network delivery, and queue behavior may dominate total latency.
- Deferred arguments: standard lazy `%s` interpolation or explicit level checks can avoid work that would otherwise occur before filtering.

The package's own cookbook discusses guarding expensive logging data with standard logging level checks. No end-to-end speedup should be assumed without considering record shapes and destination behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger+1



### 8.4 Error behavior and loss of diagnostics

The package's default encoding fallbacks attempt to make arbitrary objects representable. Custom encoders, however, can raise during formatting.

Failures may occur when a value cannot be serialized, a custom `json_default` raises, a serializer violates its expected callable interface, or a transformation returns an unsupported structure.

How such a failure is reported depends on how the formatter is invoked and which Python logging handler handles the record. Calling `formatter.format(record)` directly exposes the exception. During normal handler emission, standard logging error-handling behavior may report or suppress the failure rather than deliver the intended event.

Errors must therefore be considered at two separate layers: formatting correctness and delivery/error handling.

### 8.5 Sensitive information and output volume

Structured fields can make logs easier to query, but they can also make unintended disclosure easier.

Dictionary messages and `extra` can expose nested objects, identifiers, credentials, or request data. Exception text can contain sensitive values. Unknown-object fallback can invoke `str()` or `repr()`, potentially revealing state not intentionally selected for logging.

Formatter-level redaction through `process_log_record()` can be useful, but it is not a universal security boundary if the same `LogRecord` is also sent to other handlers.

The package does not itself provide recursive secret detection, field-level access control, event-size limits, sampling, retention policy, or a guaranteed data classification system.

These concerns are especially relevant when large objects are serialized automatically: the encoder may transform or traverse substantially more data than the event's intended diagnostic content.

## 9. Relationship to adjacent logging and observability libraries

The distinction between an output formatter and a broader logging system helps determine where other components remain necessary.

| Component            | Primary responsibility                                                     | Relationship to python-json-logger                                                |
| -------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Python `logging`     | Logger hierarchy, levels, filters, record construction, handlers, delivery | Underlying infrastructure on which python-json-logger depends                     |
| `structlog`          | Structured event production, contextual binding, processors, rendering     | Provides a richer event-processing model; can interoperate with standard logging  |
| `ecs-logging`        | Output normalization to Elastic Common Schema                              | More prescriptive schema formatter, including nested ECS fields                   |
| OpenTelemetry Python | Instrumentation, telemetry context, processors, and export                 | Separate telemetry pipeline; context may also be attached to standard log records |
| orjson / msgspec     | JSON encoding                                                              | Optional engines used by the corresponding formatter implementations              |

### 9.1 Versus structlog

`structlog` offers a structured event-processing architecture centered on dictionaries, bound context, processor chains, and configurable rendering.

`python-json-logger` starts at a later boundary: ordinary Python logging records already exist, and the formatter converts them into JSON.

The latter is a narrower abstraction with less machinery to introduce. The former offers more native functionality for managing contextual structured events before they become final output.

If the problem is simply turning existing standard logging into flexible JSON records, python-json-logger covers that directly. If it includes bound contexts, extensive processor pipelines, or structured event APIs throughout the application, structlog addresses a broader capability set.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.structlog.org\&sz=32)

structlog 26.1.0 documentation



Source: `https://www.structlog.org/en/stable/`

### 9.2 Versus ecs-logging

`ecs-logging` produces Elastic Common Schema-compatible events with predefined semantic conventions, including nested fields and standardized error metadata.

`python-json-logger` offers arbitrary field naming and custom transformations, but its field-renaming mechanism does not implement ECS nesting or validation by itself.

This creates a consequential distinction between flexibility of JSON output and compliance with an external log schema. When ECS compatibility is an actual requirement, a schema-specific formatter can avoid custom normalization work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.elastic.co\&sz=32)

ECS Logging Python+1



Source: `https://www.elastic.co/docs/reference/ecs/logging/python`

### 9.3 Versus OpenTelemetry logging

The OpenTelemetry ecosystem provides mechanisms for telemetry collection, context instrumentation, processing, batching, and export that are outside python-json-logger's remit.

The two can still share standard Python logging infrastructure. For example, tracing instrumentation can add correlation attributes to `LogRecord` objects; python-json-logger can then emit those attributes into JSON, subject to reserved-field and renaming configuration.

This does not imply that the resulting JSON lines are automatically OpenTelemetry log records or that a Python JSON formatter replaces an OpenTelemetry exporter. Those are different data and transport contracts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://opentelemetry-python.readthedocs.io\&sz=32)

OpenTelemetry Python documentation+1



Sources:

- `https://opentelemetry.io/docs/languages/python/`
- `https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html`

## 10. Version history and compatibility

Version-sensitive behavior is significant because code written for the original package or early 3.x releases can look superficially compatible while behaving differently.

| Release | Consequential change                                                                                                         |
| ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 3.1.0   | Introduced `BaseJsonFormatter`, `defaults` helpers, orjson/msgspec backends, and the reorganized import structure            |
| 3.2.0   | Corrected handling of `defaults`; improved optional-backend import errors                                                    |
| 3.3.0   | Introduced array formatting for exception and stack information                                                              |
| 4.0.0   | Added comma-separated and sequence-based field selectors, configuration reference handling, and renamed extension parameters |
| 4.1.0   | Added Python 3.14 and PyPy 3.11 support; dropped Python 3.8 and 3.9                                                          |
| 4.2.0   | Stopped modifying caller-provided dictionary messages; fixed unbraced `$name` field selection                                |

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger

### 10.1 Import-path migration

The preferred import is:

```
from pythonjsonlogger.json import JsonFormatterfrom pythonjsonlogger.core import RESERVED_ATTRS
```

The former `pythonjsonlogger.jsonlogger` module remains as a deprecated compatibility stub. It is not the preferred location for new code.

The formatters for the other two engines reside in `pythonjsonlogger.orjson` and `pythonjsonlogger.msgspec`.

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger

### 10.2 Subclass compatibility across 4.0

Version 4.0 renamed the library-specific `LogRecord` type alias to `LogData`, distinguishing it from Python's real `logging.LogRecord`.

It also changed the `log_record` parameter name to `log_data` for several formatter methods:

- `add_fields`
- `process_log_record`
- `jsonify_log_record`
- `serialize_log_record`

Positional calls may continue to work, but code depending on named arguments, method overrides, or the old type alias should recognize the updated API.

Version 4.0 also removed the ability to supply certain serializer functions through arbitrary dotted strings. Callables are now passed as objects, or resolved through `ext://` in appropriate standard logging configurations.

These are relevant compatibility differences for custom formatter subclasses and declarative logging configurations, not merely cosmetic renamings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://nhairs.github.io\&sz=32)

Python JSON Logger



### 10.3 Python and packaging requirements

For 4.2.0:

- Python requirement: `>=3.10`, with published classifiers through Python 3.14.
- PyPy 3.11 support was added in 4.1.0.
- The core distribution has no declared mandatory third-party runtime dependencies.
- `orjson` and `msgspec` are independent encoder dependencies, with their own platform and interpreter compatibility requirements.
- The package includes a `py.typed` marker for static typing tooling.

The package being pure Python does not mean that optional native serialization backends have identical deployment or platform support.

Tagged package metadata: `https://github.com/nhairs/python-json-logger/blob/v4.2.0/pyproject.toml`

## 11. Primary-source reference map

| Topic                                                 | Direct source                                                                              |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Orientation, setup, event fields                      | `https://nhairs.github.io/python-json-logger/latest/quickstart/`                           |
| Request IDs, custom styles, processing, configuration | `https://nhairs.github.io/python-json-logger/latest/cookbook/`                             |
| Core formatter, precedence, hooks                     | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/core/`      |
| Standard JSON formatter and encoder                   | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/json/`      |
| orjson backend                                        | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/orjson/`    |
| msgspec backend                                       | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/msgspec/`   |
| Type conversion helpers                               | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/defaults/`  |
| Exceptions and missing dependencies                   | `https://nhairs.github.io/python-json-logger/latest/reference/pythonjsonlogger/exception/` |
| Changes and migration                                 | `https://nhairs.github.io/python-json-logger/latest/changelog/`                            |
| Exact 4.2.0 implementation                            | `https://github.com/nhairs/python-json-logger/tree/v4.2.0/src/pythonjsonlogger`            |
| Python logging integration                            | `https://docs.python.org/3/howto/logging-cookbook.html`                                    |

## 12. Overall architectural significance

`python-json-logger` is best understood as a structured projection and JSON serialization layer for Python logging records.

Its most consequential capabilities are not simply that it produces JSON, but that it combines:

1. Native logging compatibility: existing records, filters, handlers, and configuration mechanisms remain useful.
2. Configurable event assembly: output fields can be selected, renamed, enriched, overridden, and transformed with deterministic precedence.
3. Replaceable serialization: standard JSON, orjson, msgspec, and custom encoder behavior share a common extraction pipeline.

This combination can eliminate substantial bespoke record-to-JSON code while retaining control over output representation.

The important limitations are equally clear: it is not a complete event-schema system, contextual logging framework, asynchronous delivery engine, tracing implementation, or observability exporter. Those capabilities remain separate and can be composed with it where their distinct responsibilities are needed.

For a formatter-focused library, the unusually valuable extension points are `process_log_record()` for schema transformation, `add_fields()` for extraction semantics, and `jsonify_log_record()` for new encoding backends. Understanding these three boundaries—and the precedence and serialization semantics around them—provides the strongest foundation for using the library beyond basic JSON logging.