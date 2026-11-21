# orjson — Comprehensive Python Library Overview

Research date: November 20, 2026 | Latest stable release: 3.13.0 | Python: CPython 3.10–3.15

orjson is a high-performance, Rust-implemented JSON serialization and deserialization library for Python. It combines fast native encoding and parsing, strict JSON compliance, and specialized serialization of Python objects that would otherwise require substantial conversion or custom encoder logic.

Its value extends beyond replacing Python's standard `json` module with a faster implementation. Particularly important capabilities include native dataclass serialization, efficient NumPy conversion, configurable datetime semantics, selective custom serialization, and embedding pre-serialized JSON directly into larger documents.

The reference targets orjson 3.13.0, released on PyPI October 7, 2026. The version's upstream changelog is dated August 17, 2026. This release adds native serialization of Python 3.15's `frozendict`; the preceding 3.12.0 release substantially rewrote the serialization implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Primary sources:

- Tagged documentation: `https://github.com/ijl/orjson/blob/3.13.0/README.md`
- Release changelog: `https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md`
- Package distribution: `https://pypi.org/project/orjson/3.13.0/`

## 1. Architectural overview

### 1.1 Conceptual model

orjson operates at the boundary between Python's runtime object model and JSON's comparatively small set of interchange types.

Conceptual view. Decoding produces standard JSON-compatible Python values, not reconstructed domain objects.

The core API deliberately remains small:

```
orjson.dumps(obj, default=None, option=None) -> bytesorjson.loads(data) -> Any
```

`dumps()` converts Python objects into a complete UTF-8 JSON document. `loads()` parses a complete document into Python primitives and containers.

The additional expressiveness comes primarily from three mechanisms:

1. Native type recognition: specialized paths for dataclasses, datetime, UUIDs, NumPy values, enums, and built-in containers.
2. Serialization options: composable bitmask flags controlling output format, type dispatch, datetime representation, key handling, and numeric restrictions.
3. Extension and composition: `default` converts unsupported objects into supported representations, while `orjson.Fragment` embeds already-serialized JSON without decoding it first.

These mechanisms are asymmetric. Serialization can accept richer Python objects, but deserialization does not reconstruct those original types. A serialized dataclass becomes a JSON object and is decoded as a `dict`; a datetime becomes a JSON string and is decoded as a `str`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 1.2 Capability map

| Capability family          | Native mechanisms                           | Architectural significance                                        |
| -------------------------- | ------------------------------------------- | ----------------------------------------------------------------- |
| JSON serialization         | `dumps`, native Python types                | Fast UTF-8 encoding with fewer Python-level conversions           |
| JSON deserialization       | `loads`                                     | Strict parsing directly from supported byte buffers               |
| Structured Python objects  | Dataclasses, `TypedDict`, enums, UUIDs      | Avoids many custom `JSONEncoder` implementations                  |
| Numerical and array data   | NumPy scalars/arrays, `OPT_SERIALIZE_NUMPY` | Avoids Python object materialization for supported arrays         |
| Temporal data              | Native datetime, timezone options           | Consistent RFC 3339-style timestamp representation                |
| Custom serialization       | `default`, passthrough options              | Selective transformation of unsupported or otherwise native types |
| Pre-serialized JSON        | `Fragment`                                  | Avoids decoding and re-encoding embedded subdocuments             |
| Deterministic presentation | Sorting, indentation, integer controls      | Useful for snapshots and constrained interchange contracts        |
| Transport integration      | UTF-8 `bytes` result                        | Direct use at binary output boundaries                            |

### 1.3 Boundaries of responsibility

orjson is a JSON codec, not a general data-modeling, validation, document-processing, or streaming framework.

It does not provide typed deserialization, schema enforcement, configurable object reconstruction, automatic file I/O, or incremental JSON streaming. These remain responsibilities of surrounding libraries or application code.

This distinction matters architecturally: orjson can accelerate a serialization boundary without becoming the authoritative source of a data model's validation, invariants, or transformation semantics.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

## 2. Serialization: Python objects to JSON

### 2.1 Native type system

Unlike the standard library's encoder, orjson recognizes several Python-native types without requiring them to be converted into intermediate dictionaries, lists, or strings.

| Python type                | Serialization behavior                   | Important distinction                                 |
| -------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| `dict`                     | JSON object                              | Keys must be strings by default                       |
| `frozendict`               | JSON object                              | New in 3.13.0 for Python 3.15                         |
| `list`, `tuple`            | JSON array                               | Tuples lose their identity                            |
| `str`                      | JSON string                              | Strict Unicode/UTF-8 validity                         |
| `int`                      | JSON integer                             | Bounded to 64-bit integer representations             |
| `float`                    | JSON number                              | Non-finite values become `null`                       |
| `bool`, `None`             | JSON boolean/null                        | Native mapping                                        |
| `dataclasses.dataclass`    | JSON object                              | Fields serialized directly                            |
| `typing.TypedDict`         | JSON object                              | Runtime dictionary representation; no type validation |
| `enum.Enum`                | Underlying member value                  | Subject to normal value serialization                 |
| `uuid.UUID`                | JSON string                              | Standard hyphenated UUID representation               |
| `datetime`, `date`, `time` | JSON string                              | Built-in formatting and timezone controls             |
| `numpy.ndarray`            | JSON array                               | Requires `OPT_SERIALIZE_NUMPY`                        |
| NumPy scalar types         | JSON number, boolean, or datetime string | Requires `OPT_SERIALIZE_NUMPY`                        |
| `orjson.Fragment`          | Embedded raw JSON                        | Contents inserted without JSON validation             |

orjson also handles subclasses of certain built-ins, notably `str`, `int`, `dict`, and `list`. However, subclasses of `tuple` are intentionally not encoded as arrays, avoiding accidental serialization of named tuples. Float subclasses are also excluded from the native float path.

These distinctions affect both compatibility and whether custom serialization logic is invoked.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 2.2 Custom serialization through `default`

The `default` parameter is the library's primary extension mechanism for arbitrary Python objects.

It accepts a callable that converts an unsupported object into another representation that orjson can serialize.

```
import decimalimport pathlibimport orjsondef default(obj):    if isinstance(obj, decimal.Decimal):        return str(obj)    if isinstance(obj, pathlib.Path):        return str(obj)    if isinstance(obj, set):        return sorted(obj)    raise TypeError(f"Unsupported type: {type(obj)!r}")payload = {    "amount": decimal.Decimal("123.456789123456789"),    "path": pathlib.Path("/data/file.json"),    "labels": {"verified", "active"},}encoded = orjson.dumps(payload, default=default)
```

This mechanism can support essentially any custom object type for which a suitable JSON-compatible representation can be constructed.

The important architectural distinction is that `default` is a fallback converter, not a general serialization hook.

If orjson natively recognizes an object, its native serialization path ordinarily takes precedence. A custom `default` function will not automatically intercept dataclasses, datetimes, or built-in subclasses.

There are several consequences:

Custom transformations are explicit. orjson does not automatically consult a model's `to_dict()`, `model_dump()`, or other convention-based serializer.

The returned representation can require further conversion. A `default` function can return another unsupported object, allowing recursive conversion. orjson permits up to 254 such fallback invocations before raising an exception.

Unrecognized types must raise an exception. If the callable implicitly returns `None`, that value becomes JSON `null`, potentially concealing a serialization failure.

Exceptions retain diagnostic context. Errors raised by the callable are wrapped as `JSONEncodeError`, with the original exception available through `__cause__`.

Numeric representations remain the caller's responsibility. Returning `str(Decimal)` preserves its decimal digits as text, whereas converting it to a binary floating-point number can lose precision. orjson does not impose either representation automatically.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.3 Intercepting natively supported types

Three options allow callers to override orjson's native dispatch:

| Option                      | What it intercepts            | Examples of additional control                                    |
| --------------------------- | ----------------------------- | ----------------------------------------------------------------- |
| `OPT_PASSTHROUGH_DATACLASS` | Dataclass instances           | Field filtering, redaction, alternative field names               |
| `OPT_PASSTHROUGH_DATETIME`  | `datetime`, `date`, `time`    | Custom timestamp conventions                                      |
| `OPT_PASSTHROUGH_SUBCLASS`  | Supported built-in subclasses | Special treatment for domain-specific scalar/container subclasses |

For example, dataclasses ordinarily expose all their fields to native serialization:

```
from dataclasses import dataclassimport orjson@dataclassclass Credential:    username: str    secret: strcredential = Credential("alice", "private-value")orjson.dumps(credential)# b'{"username":"alice","secret":"private-value"}'
```

If serialization needs a controlled public representation, the dataclass can be routed through `default`:

```
def public_default(obj):    if isinstance(obj, Credential):        return {"username": obj.username}    raise TypeErrororjson.dumps(    credential,    default=public_default,    option=orjson.OPT_PASSTHROUGH_DATACLASS,)# b'{"username":"alice"}'
```

This reveals an important architectural tradeoff: native serialization minimizes conversions but does not enforce domain-specific serialization policies.

The passthrough mechanisms can make custom encoding more selective without replacing all native serialization. However, the developer must still explicitly choose the fields and representations.

There is also a key limitation: passthrough options for datetime and built-in subclasses do not change their normal serialization as dictionary keys under `OPT_NON_STR_KEYS`. Therefore, custom key representations require a separate transformation strategy.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

## 3. Serialization configuration

orjson uses integer option flags that can be combined with bitwise OR (`|`). The configuration is per serialization call rather than a mutable global encoder object.

### 3.1 Complete active option families

| Option                      | Effect                                              |
| --------------------------- | --------------------------------------------------- |
| `OPT_INDENT_2`              | Pretty-print JSON with two-space indentation        |
| `OPT_APPEND_NEWLINE`        | Append a newline to the resulting bytes             |
| `OPT_SORT_KEYS`             | Sort dictionary keys lexicographically              |
| `OPT_NON_STR_KEYS`          | Accept supported non-string dictionary key types    |
| `OPT_STRICT_INTEGER`        | Enforce the interoperable 53-bit safe integer range |
| `OPT_NAIVE_UTC`             | Treat timezone-naive datetimes as UTC               |
| `OPT_UTC_Z`                 | Emit `Z` instead of `+00:00` for UTC datetimes      |
| `OPT_OMIT_MICROSECONDS`     | Suppress fractional seconds                         |
| `OPT_SERIALIZE_NUMPY`       | Enable native NumPy serialization                   |
| `OPT_PASSTHROUGH_DATACLASS` | Route dataclasses to `default`                      |
| `OPT_PASSTHROUGH_DATETIME`  | Route datetime/date/time values to `default`        |
| `OPT_PASSTHROUGH_SUBCLASS`  | Route supported built-in subclasses to `default`    |

Two older flags remain for compatibility: `OPT_SERIALIZE_DATACLASS` and `OPT_SERIALIZE_UUID`. Both are deprecated and have no effect in orjson 3.x because the corresponding types are serialized by default.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 3.2 Composing configuration

A useful property of the bitmask design is that representation and dispatch controls can be combined.

```
import orjsonWIRE_OPTIONS = (    orjson.OPT_SERIALIZE_NUMPY    | orjson.OPT_NAIVE_UTC    | orjson.OPT_UTC_Z    | orjson.OPT_STRICT_INTEGER)encoded = orjson.dumps(data, option=WIRE_OPTIONS)
```

This makes it possible to establish a consistent output policy across heterogeneous data structures.

However, these options do not constitute a schema or enforce complete semantic consistency. They apply to the types and serialization paths documented for each flag, rather than imposing universal validation rules.

### 3.3 Sorting, determinism, and canonicalization

`OPT_SORT_KEYS` produces sorted keys for dictionaries and `frozendict` objects.

This can reduce accidental variation in output caused by different dictionary insertion orders, making it useful for snapshots, caching, and hashing.

There are three important qualifications.

First, sorting adds overhead. The upstream README reports a substantial penalty in some benchmarks.

Second, sorting is lexicographic and not locale-aware. It also does not sort dataclass fields, which retain their definition order.

Third, sorted output is not automatically canonical JSON. Canonicalization may additionally require prescribed numeric formatting, string escaping, normalization, and handling of duplicate keys. orjson does not document compliance with a canonical JSON standard such as RFC 8785.

Accordingly, `OPT_SORT_KEYS` is useful for deterministic representation within a controlled serialization contract, but it should not be treated as a universal cross-language canonicalization mechanism.

### 3.4 Non-string keys and representational collisions

`OPT_NON_STR_KEYS` supports keys of type `str`, `int`, `float`, `bool`, `None`, datetime/date/time, enum, and UUID.

This is particularly valuable for mapping data keyed by numeric identifiers or timestamps.

```
import orjsonobj = {    12: "numeric",    "12": "text",}encoded = orjson.dumps(    obj,    option=orjson.OPT_NON_STR_KEYS,)
```

Both original keys become the JSON key `"12"`.

Because the JSON object model uses string keys, the resulting document contains duplicate names. A subsequent decode into a Python dictionary cannot preserve both original entries.

Sorting does not resolve this ambiguity. When `OPT_SORT_KEYS` and `OPT_NON_STR_KEYS` are combined, sorting is unstable for keys that collide after conversion.

Another subtlety is that `OPT_STRICT_INTEGER` does not apply to integer dictionary keys converted using `OPT_NON_STR_KEYS`.

These are genuine information-model constraints, not merely formatting details. Converting non-string keys into JSON object names can be lossy even when encoding succeeds.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.5 Pretty printing and newline optimization

`OPT_INDENT_2` provides exactly two-space indentation. Other indentation widths, custom separators, and arbitrary pretty-printing policies are not supported.

`OPT_APPEND_NEWLINE` is an output-buffer optimization. Since Python `bytes` objects are immutable, appending `b"\n"` after serialization requires allocation and copying; adding the newline during serialization avoids that additional operation.

These two flags can be combined, although indentation increases output size and generally reduces serialization throughput.

## 4. Specialized serialization capabilities

### 4.1 Dataclasses and structured Python data

Native dataclass serialization is one of orjson's most consequential capabilities.

The library reads dataclass fields directly rather than requiring a recursive conversion through `dataclasses.asdict()`.

This reduces intermediate Python allocations and avoids repeated traversal by Python-level conversion machinery.

Supported dataclass variants include ordinary, frozen, slotted, inherited, and nested dataclasses, as well as those with optional fields or defaults.

The native representation preserves the order in which fields are defined.

There are important distinctions from a dedicated data-model serializer:

| Concern                     | Native orjson behavior                                                    |
| --------------------------- | ------------------------------------------------------------------------- |
| Field inclusion             | Serializes dataclass attributes, without a schema-driven exclusion policy |
| Nested dataclasses          | Serialized recursively                                                    |
| Field ordering              | Class definition order                                                    |
| Optional fields             | Values such as `None` are serialized normally                             |
| Renaming fields             | Requires an explicit transformation                                       |
| Aliases and computed fields | No general schema-aware handling                                          |
| Type annotations            | Do not enforce runtime validation                                         |
| Unknown or custom values    | Routed through `default` if unsupported                                   |
| Dataclass reconstruction    | Not provided by `loads()`                                                 |

The upstream benchmark comparing native orjson dataclass serialization with the standard-library approach using `dataclasses.asdict()` reports especially large speed differences, although that benchmark includes conversion overhead incurred by the comparison implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This makes native dataclass serialization attractive for structures whose fields already correspond to the desired wire representation.

By contrast, if serialized output requires field-level policy, aliases, versioned schemas, or validation, a schema-aware layer may be more appropriate.

### 4.2 Datetime and timezone handling

orjson natively serializes Python's `datetime.datetime`, `datetime.date`, and `datetime.time` types.

Datetime strings use RFC 3339-compatible representations, including explicit numeric timezone offsets when applicable.

| Input or option              | JSON representation           |
| ---------------------------- | ----------------------------- |
| Naive datetime               | `"2026-01-01T12:30:00"`       |
| `OPT_NAIVE_UTC`              | `"2026-01-01T12:30:00+00:00"` |
| `OPT_NAIVE_UTC \| OPT_UTC_Z` | `"2026-01-01T12:30:00Z"`      |
| Aware datetime, UTC+05:30    | `"2026-01-01T12:30:00+05:30"` |
| `datetime.date`              | `"2026-01-01"`                |
| `datetime.time`              | `"12:30:00"`                  |

Illustrative representations assuming the corresponding input values and timezone state.

The supported timezone implementations include `datetime.timezone.utc`, standard-library `zoneinfo.ZoneInfo`, and compatible objects from `dateutil`, `pytz`, `pendulum`, and `arrow`.

The upstream documentation identifies `zoneinfo.ZoneInfo` as the fastest supported timezone implementation.

Important temporal semantics:

Naive UTC interpretation is not timezone conversion. `OPT_NAIVE_UTC` adds an assumption about an otherwise timezone-unaware value. It does not establish that the original timestamp was actually UTC.

UTC suffix formatting is separate. `OPT_UTC_Z` controls representation of UTC offsets. It does not convert non-UTC aware datetimes into UTC.

Microseconds can be omitted. `OPT_OMIT_MICROSECONDS` changes the serialized representation and can discard temporal precision.

Timezone-aware `datetime.time` is unsupported. Native serialization requires a `time` object without `tzinfo`.

Custom temporal contracts require passthrough. For epoch numbers, alternative date conventions, or specialized timezone normalization, callers can use `OPT_PASSTHROUGH_DATETIME` and implement the conversion explicitly.

This combination provides relatively sophisticated temporal output control without requiring every datetime value to be converted to a string in Python.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

### 4.3 Native NumPy serialization

`OPT_SERIALIZE_NUMPY` enables optimized traversal of supported NumPy arrays and scalar types.

This is a particularly important performance capability because conventional JSON serialization of arrays often begins with `ndarray.tolist()`, materializing large numbers of Python objects before encoding.

orjson's native path can avoid that intermediate conversion.

```
import numpy as npimport orjsonmatrix = np.array(    [[1.25, 2.50], [3.75, 4.00]],    dtype=np.float32,)encoded = orjson.dumps(    matrix,    option=orjson.OPT_SERIALIZE_NUMPY,)# b'[[1.25,2.5],[3.75,4.0]]'
```

Illustrative output; the exact JSON number spelling can vary with formatting changes across releases.

#### Supported numerical representations

| NumPy type family       | Supported representations                      |
| ----------------------- | ---------------------------------------------- |
| Signed integers         | `int8`, `int16`, `int32`, `int64`, `intp`      |
| Unsigned integers       | `uint8`, `uint16`, `uint32`, `uint64`, `uintp` |
| Floating point          | `float16`, `float32`, `float64`                |
| Boolean                 | NumPy boolean scalars and arrays               |
| Temporal                | `datetime64`                                   |
| Multidimensional arrays | `ndarray` with supported dtype and layout      |

Both NumPy 1.x and 2.x are documented as supported. NumPy itself is not a required installation dependency of orjson.

The implementation accesses compatible array representations through NumPy's array interface rather than depending on NumPy's Python conversion functions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



#### Layout and dtype constraints

The optimized path has structural requirements.

| Condition                                          | Behavior                              |
| -------------------------------------------------- | ------------------------------------- |
| C-contiguous array                                 | Eligible for native serialization     |
| Non-C-contiguous array                             | Falls back to `default` when provided |
| Supported native-endian dtype                      | Eligible for native serialization     |
| Unsupported dtype                                  | Falls back to `default` when provided |
| Non-native byte order                              | Raises `JSONEncodeError`              |
| Malformed array interface                          | Raises `JSONEncodeError`              |
| Unsupported or unrepresentable `datetime64` values | Can raise serialization errors        |

A typical fallback can convert a noncontiguous or unsupported array:

```
import numpy as npimport orjsondef numpy_fallback(obj):    if isinstance(obj, np.ndarray):        return obj.tolist()    raise TypeErrororjson.dumps(    array,    option=orjson.OPT_SERIALIZE_NUMPY,    default=numpy_fallback,)
```

The fallback is not equivalent to the native path. Converting an array to a Python list incurs additional object materialization and may change numerical formatting.

In particular, `float32` values serialized directly can produce different decimal spellings from values first converted by `tolist()`, which promotes them to Python's double-precision float representation.

This matters for numerical regression tests and byte-exact comparisons.

#### Temporal arrays

NumPy `datetime64` values are emitted as datetime strings, and the temporal flags compose with NumPy serialization.

For example:

```
options = (    orjson.OPT_SERIALIZE_NUMPY    | orjson.OPT_NAIVE_UTC    | orjson.OPT_OMIT_MICROSECONDS)encoded = orjson.dumps(    np.datetime64("2026-01-01T12:30:00.125"),    option=options,)
```

Not every NumPy datetime unit and value is representable. Very fine-resolution units and out-of-range values require special attention rather than assuming that all `datetime64` arrays serialize successfully.

#### The representational limitation

Native NumPy serialization is an efficient conversion to JSON, not a lossless numerical array interchange format.

JSON does not retain NumPy dtype, byte order, strides, array ownership, or an explicit shape schema. Decoding yields Python lists and scalar values, not an `ndarray`.

This distinction is important when comparing orjson with Arrow, NumPy's binary formats, or other typed numerical transports.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

### 4.4 UUIDs, enums, and numerical edge cases

UUIDs are serialized directly to conventional hyphenated UUID strings without needing `default`.

Enums are serialized through their member values. Serialization options then apply to those values, including datetime options for datetime-valued enums.

The numeric boundary behavior deserves separate attention:

| Input/requirement                              | Behavior                                      |
| ---------------------------------------------- | --------------------------------------------- |
| Finite Python float                            | Encoded as a JSON number                      |
| `float("nan")`                                 | Encoded as JSON `null`                        |
| Positive or negative infinity                  | Encoded as JSON `null`                        |
| Integer within the supported 64-bit range      | Encoded as an integer                         |
| Integer outside that range                     | Raises `JSONEncodeError`                      |
| Integer outside ±(2⁵³ − 1), with strict option | Raises `JSONEncodeError`                      |
| `decimal.Decimal`                              | Requires `default`                            |
| Arbitrary-precision numeric semantics          | Not provided by the native JSON numeric model |

The conversion of non-finite floating-point values to `null` is especially important because it is lossy rather than fail-fast.

If NaN and infinity carry different meanings from missing values, a domain-specific transformation or validation step is needed.

`OPT_STRICT_INTEGER` is useful for JSON consumers using IEEE-754 binary64 numbers, particularly JavaScript environments, where integers beyond the safe integer range may not be represented exactly.

The library's native integer range is effectively from signed 64-bit minimum through unsigned 64-bit maximum; `OPT_STRICT_INTEGER` narrows permitted value integers to the interoperable safe range.

Source: `https://github.com/ijl/orjson/blob/3.13.0/src/serialize/num.rs`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 5. Deserialization and JSON correctness

### 5.1 Whole-document parsing

`orjson.loads()` consumes a complete JSON document and returns ordinary Python values.

```
import orjsondata = orjson.loads(    b'{"id":42,"active":true,"items":[1,2,3]}')
```

Supported input representations are `bytes`, `bytearray`, `memoryview`, and `str`.

The ability to accept byte-oriented inputs is significant because it can remove an otherwise unnecessary UTF-8 decoding step.

For example, when a transport or file reader already supplies UTF-8 bytes, there is generally no reason to create a Python `str` merely to pass it to the JSON parser.

However, accepting a `memoryview` does not mean the output shares memory with the input. Parsing still constructs Python objects, including dictionaries, lists, and strings.

### 5.2 Strict parsing semantics

orjson follows RFC 8259 JSON syntax and requires valid UTF-8.

Among the inputs it rejects are malformed JSON syntax, invalid Unicode, unpaired surrogate escapes, and nonstandard numeric literals such as `NaN` and `Infinity`.

These are meaningful differences from the standard-library `json` module, which accepts certain nonstandard constructs.

| Concern                       | orjson behavior                       |
| ----------------------------- | ------------------------------------- |
| UTF-8 input                   | Strictly validated                    |
| Unpaired surrogate characters | Rejected                              |
| JSON comments                 | Not supported                         |
| Trailing commas               | Not supported                         |
| `NaN` and infinity literals   | Rejected                              |
| Complete document             | Required                              |
| Nested arrays/objects         | Depth limited to 1024                 |
| Decoded types                 | Standard Python JSON-compatible types |
| Custom object reconstruction  | Not supported                         |

One important asymmetry is that `dumps()` converts non-finite floating-point values to `null`, while `loads()` rejects nonstandard non-finite numeric literals.

Consequently, a successful encode/decode round trip does not necessarily preserve the distinction between a non-finite number and a null-like value.

The parser's depth restriction also means that JSON syntactic validity does not guarantee successful deserialization: excessively deep but otherwise valid structures are rejected.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.3 Process-level dictionary-key caching

An easily overlooked optimization is orjson's cache of decoded JSON object keys.

The documentation describes a process-lifetime cache containing up to 2,048 entries for keys no longer than 64 bytes.

The purpose is to avoid repeatedly allocating equivalent Python strings when similar JSON object structures are decoded.

This can be valuable for repeated structured records whose field names are largely identical, such as application events or API messages.

The optimization should be understood narrowly:

It is not general-purpose interning of arbitrary JSON string values, a memoization cache of complete documents, or a mechanism for sharing parsed objects.

It reduces allocations associated with qualifying object keys, but the actual benefit depends on repetition and workload characteristics.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

### 5.4 Errors and diagnostic compatibility

The principal exceptions are:

| Exception                | Inheritance                             | Typical trigger                                                             |
| ------------------------ | --------------------------------------- | --------------------------------------------------------------------------- |
| `orjson.JSONEncodeError` | `TypeError`                             | Unsupported object, invalid string, integer overflow, serialization failure |
| `orjson.JSONDecodeError` | `json.JSONDecodeError` and `ValueError` | Invalid input type, malformed document, invalid Unicode, depth violation    |

The standard-library-compatible inheritance makes it easier to integrate orjson into code that already catches broad JSON errors.

For encoding, exceptions from a custom `default` callback are chained as the cause of the resulting `JSONEncodeError`.

For decoding, `JSONDecodeError` supplies parser diagnostics, including location information for applicable syntax failures.

Strict error behavior is useful when JSON is an interchange contract or trust boundary. However, orjson's parser is not a substitute for schema validation or resource limits enforced at the surrounding transport/application layer.

### 5.5 Features deliberately absent from `loads()`

The decoder does not provide equivalents of the standard library's `object_hook`, `object_pairs_hook`, `parse_float`, or `parse_int` callbacks.

There is therefore no native way to request that arbitrary JSON numbers be parsed directly into `Decimal`, that objects be reconstructed as dataclasses, or that object pairs be exposed to a custom duplicate-key handler.

A complete parse produces Python data structures first. Any typed interpretation must be performed afterward by application code or another library.

For applications requiring both strict typed deserialization and high performance, libraries with schema-aware decoding have a different capability profile.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`

## 6. Pre-serialized JSON composition with `orjson.Fragment`

`orjson.Fragment` is one of the library's most distinctive advanced features.

It allows a pre-existing JSON document or value to be embedded within another serialized structure without first converting that fragment back into Python objects.

```
import orjsoncached = b'{"score":0.98,"labels":["a","b"]}'document = {    "request_id": "r-123",    "result": orjson.Fragment(cached),}encoded = orjson.dumps(document)# b'{"request_id":"r-123","result":{"score":0.98,"labels":["a","b"]}}'
```

### 6.1 What the mechanism avoids

Without `Fragment`, inserting a cached JSON object typically requires one of two approaches.

The caller can decode it with `loads()`, insert the Python value into the surrounding structure, then encode the entire document again. Alternatively, the caller can implement custom byte/string concatenation while ensuring that the resulting JSON remains structurally correct.

`Fragment` supports a third approach: the outer document is serialized normally, but the fragment is copied directly into its value position.

This avoids constructing an intermediate Python representation of the fragment and avoids re-serializing its individual members.

It can therefore be useful for composing JSON responses from previously serialized results, cached subdocuments, or JSON values retrieved from storage systems.

### 6.2 Critical semantic and security boundaries

The fragment must contain `bytes` or `str`. Its contents are inserted without ordinary string escaping or JSON structural validation.

That has significant implications.

No automatic validation. A fragment containing malformed JSON may result in an invalid final document.

No reformatting. `OPT_INDENT_2` and other output-format options do not recursively transform fragment contents.

No schema enforcement. The outer serializer does not examine fragment members or verify their fields.

No normalization. A fragment's existing numeric formatting, whitespace, and key ordering remain as supplied.

Not zero-copy output. The mechanism avoids decoding and re-encoding the fragment's value tree, but the fragment bytes still become part of the final output buffer.

`Fragment` is therefore most appropriate for trusted, already-validated JSON whose representation should remain unchanged.

For untrusted content, validation before constructing a fragment is essential. The fact that orjson can insert the bytes efficiently does not establish that the resulting document is safe or valid.

Source: `https://github.com/ijl/orjson/blob/3.13.0/README.md`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 7. Performance architecture and concurrency

### 7.1 Where the speed advantage comes from

orjson's implementation combines native Rust serialization, optimized JSON parsing, specialized type handling, and CPU-specific optimizations.

The relevant performance mechanisms operate at different layers.

| Mechanism                      | Work avoided or accelerated                      | When it matters                                           |
| ------------------------------ | ------------------------------------------------ | --------------------------------------------------------- |
| Native Rust serialization      | Python-level loops and generic encoder dispatch  | Repeated serialization of large or nested structures      |
| Specialized dataclass handling | Recursive `asdict()` conversion                  | Structured object graphs                                  |
| Native NumPy traversal         | `ndarray.tolist()` and Python scalar allocation  | Large homogeneous arrays                                  |
| Direct byte-buffer parsing     | Preliminary UTF-8 `bytes`-to-`str` conversion    | Network and binary I/O boundaries                         |
| Decoded key cache              | Repeated allocation of common object-key strings | Similar documents with repeated field names               |
| `Fragment`                     | Decoding and re-encoding existing JSON subtrees  | Document composition and cached results                   |
| `OPT_APPEND_NEWLINE`           | An extra immutable-bytes concatenation           | Line-oriented output generated by the caller              |
| SIMD and CPU dispatch          | Some low-level parsing and encoding operations   | Supported hardware and sufficiently substantial workloads |

The source uses Rust for the Python extension and serialization machinery, alongside a vendored C implementation of the `yyjson` parser and optimized supporting components. It is therefore more precise to describe orjson as a Rust-implemented Python extension with native parsing components than as a pure-Rust JSON parser.

The distributed x86-64 wheels target a broad CPU baseline while using AVX-512 instructions at runtime when available. Hardware-specific acceleration can improve throughput without requiring separate application code.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 7.2 Upstream benchmark results and their scope

The tagged README provides latency measurements against Python's standard `json` module:

| Benchmark document  | `orjson.dumps()` | `json.dumps()` | Relative speedup |
| ------------------- | ---------------- | -------------- | ---------------- |
| `twitter.json`      | 0.1 ms           | 1.3 ms         | 11.1×            |
| `github.json`       | 0.01 ms          | 0.13 ms        | 13.6×            |
| `citm_catalog.json` | 0.3 ms           | 3.0 ms         | 11.8×            |
| `canada.json`       | 2.5 ms           | 29.8 ms        | 11.9×            |

For decoding:

| Benchmark document  | `orjson.loads()` | `json.loads()` | Relative speedup |
| ------------------- | ---------------- | -------------- | ---------------- |
| `twitter.json`      | 0.5 ms           | 2.2 ms         | 4.2×             |
| `github.json`       | 0.04 ms          | 0.1 ms         | 2.2×             |
| `citm_catalog.json` | 1.3 ms           | 4.0 ms         | 3.1×             |
| `canada.json`       | 3.0 ms           | 18.0 ms        | 6.0×             |

Benchmark qualification: These are upstream-published measurements made using CPython 3.11.10, Fedora 42, x86-64-v4 hardware, and orjson 3.10.11. They are not measurements of the 3.13.0 release or guarantees for other workloads. The benchmarks primarily isolate JSON operations rather than end-to-end application performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



The library also publishes memory and latency comparisons for NumPy serialization. Their architectural relevance is that avoiding `tolist()` can reduce both time and peak memory consumption, not simply accelerate an otherwise identical sequence of operations.

### 7.3 End-to-end performance is different from codec performance

The benefits depend on where the work occurs.

For an ordinary Python dictionary already populated with JSON-compatible values, replacing `json.dumps()` with `orjson.dumps()` can be a relatively direct substitution.

But for a large data model, the conversion pipeline might be:

Conversion-heavy approach

Domain object

Python dict/list conversion

JSON encoding

Eligible native orjson approach

Supported domain object

Native JSON encoding

Native type support can eliminate a conversion stage, but only when the required wire semantics match the native serializer.

This distinction can matter more than the raw speed difference between JSON encoders.

Conversely, introducing a `default` callback that recursively constructs large intermediate structures can reintroduce much of the cost that native serialization avoids.

### 7.4 GIL behavior and concurrency

The upstream documentation explicitly states that both `dumps()` and `loads()` hold the Python global interpreter lock for the duration of each call in conventional GIL-enabled CPython.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This has practical consequences:

- A long serialization or parse operation does not automatically create parallel CPU execution across Python threads within the same GIL-enabled interpreter.
- Multiple worker processes can provide separate interpreter execution contexts.
- Faster individual calls may reduce time spent under the GIL, indirectly improving overall responsiveness.
- Calling a native Rust implementation does not, by itself, imply that Python object traversal can safely release the GIL.

The 3.13.0 source includes conditional module declarations relating to Python's free-threaded interpreter builds. However, the published README still describes PEP 703 support as prospective rather than offering a general free-threaded concurrency guarantee. It would be inappropriate to infer fully supported parallel codec execution from those module declarations alone.

This is a distinction between documented support and implementation-level preparation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.5 Additional memory and latency considerations

orjson generally emits a newly allocated `bytes` object. There is no public API for serializing directly into a caller-provided output buffer.

It also materializes Python values during decoding. Even when the input arrives as a `memoryview`, decoding is not a zero-copy view of the JSON document.

Therefore, memory-efficient behavior arises mainly from avoiding unnecessary intermediate conversions and from optimized internal allocation, not from providing a general zero-copy interchange abstraction.

For very large arrays or columnar data, a binary format may offer a fundamentally different efficiency profile by preserving typed buffers and avoiding text representation entirely.

## 8. Integration with application frameworks and data-model libraries

### 8.1 FastAPI and Starlette

orjson can integrate naturally into ASGI applications because HTTP response implementations ultimately need byte-oriented content.

For example, an application can construct a response directly:

```
import orjsonfrom fastapi import FastAPI, Responseapp = FastAPI()@app.get("/data")def get_data():    content = orjson.dumps({"status": "ok"})    return Response(        content=content,        media_type="application/json",    )
```

This provides direct control over the JSON representation and avoids an additional string-to-bytes conversion.

However, using a direct `Response` bypasses parts of FastAPI's normal response-model processing. That can affect validation, serialization policy, and automatic documentation behavior.

An important 2026 development changes the usual performance advice.

In FastAPI 0.130.0, released February 22, 2026, FastAPI introduced direct Pydantic-based Rust serialization for responses with suitable return types or response models. In 0.131.0, it deprecated the convenience classes `ORJSONResponse` and `UJSONResponse`.

Current FastAPI documentation consequently recommends response models over choosing orjson solely to accelerate ordinary JSON responses.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fastapi.tiangolo.com\&sz=32)

FastAPI+1



This does not make orjson irrelevant in FastAPI. It remains useful when the caller explicitly needs its serialization flags, `Fragment`, native NumPy behavior, or a custom byte-oriented output contract.

FastAPI also documents the construction of custom response classes by implementing `Response.render()` and returning bytes produced by `orjson.dumps()`.

Primary sources:

`https://fastapi.tiangolo.com/advanced/custom-response/`

`https://fastapi.tiangolo.com/release-notes/`

### 8.2 Flask and Quart

The separate `flask-orjson` package implements Flask and Quart's JSON-provider interface using orjson.

Its `OrjsonProvider` supports application-level JSON configuration and additional object conversions:

```
from flask import Flaskfrom flask_orjson import OrjsonProviderapp = Flask(__name__)app.json = OrjsonProvider(app)
```

The companion package adds handling for `Decimal` and objects implementing `__html__`, and enables `OPT_NAIVE_UTC` by default.

These are capabilities of flask-orjson's integration layer, not additional native behaviors of orjson itself.

The distinction is relevant because Flask's provider contract and response lifecycle differ from orjson's minimal `dumps()`/`loads()` interface. The integration layer adapts the codec to that contract.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://flask-orjson.readthedocs.io\&sz=32)

flask-orjson.readthedocs.io+1



Primary source:

`https://flask-orjson.readthedocs.io/en/latest/api/`

### 8.3 Pydantic and typed serialization

Pydantic and orjson operate at different abstraction levels.

orjson serializes supported Python values with optional fallback conversion. Pydantic's serialization system uses knowledge of a model or type schema to control which values are included, how fields are transformed, and how they are represented.

Pydantic provides direct JSON serialization through `model_dump_json()` and `TypeAdapter.dump_json()`, without requiring an intermediate `dict` followed by `orjson.dumps()`.

This creates an important choice:

| Requirement                                                 | Mechanism                                   |
| ----------------------------------------------------------- | ------------------------------------------- |
| Fast JSON encoding of an existing ordinary Python structure | orjson                                      |
| Native NumPy-to-JSON conversion                             | orjson                                      |
| Embedding a pre-serialized JSON subtree                     | orjson `Fragment`                           |
| Model-aware aliases, exclusions, field serializers          | Pydantic serialization                      |
| Typed reconstruction and validation of JSON input           | Pydantic validation                         |
| Direct serialization from a Pydantic model                  | Pydantic's native JSON serializer           |
| Custom JSON wire format independent of Pydantic's schema    | Potentially orjson with explicit conversion |

For a Pydantic model, a pipeline such as:

```
encoded = orjson.dumps(model.model_dump(mode="json"))
```

can introduce a Python intermediate representation that direct Pydantic JSON serialization would avoid.

That does not mean it is always inappropriate. Explicit conversion may be needed when the output must use a specific orjson behavior. But it should be recognized as a distinct pipeline with its own allocation and semantic costs.

Primary source: `https://pydantic.dev/docs/validation/latest/concepts/serialization/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 8.4 File formats, storage systems, and message transports

orjson's `bytes` output can be passed directly to file writers, network APIs, message queues, object stores, or database client libraries that accept byte buffers.

For ordinary file writing:

```
import orjsonwith open("result.json", "wb") as file:    file.write(orjson.dumps(payload))
```

For line-delimited JSON, each record can be encoded with `OPT_APPEND_NEWLINE` and written by the caller:

```
with open("events.jsonl", "wb") as file:    for event in events:        file.write(            orjson.dumps(                event,                option=orjson.OPT_APPEND_NEWLINE,            )        )
```

This illustrates a composition pattern, not native JSONL support. orjson does not provide a JSONL reader/writer abstraction, record iteration, or incremental streaming parser.

The official documentation explicitly identifies these features as outside its scope and mentions the separate `orjsonl` package for JSONL use cases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



For database integration, it is useful to distinguish two operations:

- Encoding Python data into a JSON document that a driver can transmit or store.
- Allowing the database driver to adapt, bind, validate, and retrieve JSON or JSONB values according to the database protocol.

orjson supplies the codec for the first operation; it does not replace driver-level adaptation or database-specific semantics.

Similarly, `Fragment` can help compose JSON documents derived from stored JSON values, but it does not itself query databases or establish validity of retrieved subdocuments.

## 9. Deployment, compatibility, and release evolution

### 9.1 Python and platform support

The 3.13.0 release documents support for CPython 3.10 through 3.15.

Compiled wheels cover multiple Linux, macOS, and Windows architectures, subject to the platform-specific availability of each Python version.

Significant constraints include:

| Platform or feature         | Status                                         |
| --------------------------- | ---------------------------------------------- |
| CPython 3.10–3.15           | Supported                                      |
| Linux x86-64 and ARM64      | Published wheels                               |
| Linux x86-32 and ARMv7      | Published wheels for supported Python versions |
| Linux glibc and musl        | Published wheel variants                       |
| macOS x86-64 and ARM64      | Published wheels                               |
| Windows x86-64 and ARM64    | Published wheels for supported Python versions |
| Windows x86-32              | Wheels discontinued in 3.13.0                  |
| Linux ppc64le and s390x     | Wheels discontinued in 3.12.0                  |
| PyPy                        | Not supported                                  |
| Embedded Android/iOS Python | Not supported                                  |
| PEP 554 subinterpreters     | Not supported                                  |

The upstream README's general platform list has not been fully reconciled with the latest changelog, so the specific removal notices and published PyPI artifacts are more authoritative for 3.13.0 wheel availability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 9.2 Building from source

When an appropriate wheel is unavailable, source builds require a Rust toolchain and native build environment.

For 3.13.0, the documented requirements include Rust 1.95 or later, a C compiler, and maturin.

The published build command is:

```
maturin build --release --strip
```

The package uses a Rust 2024-edition codebase, native Python-extension interfaces, and compiled dependencies.

The project notes that its own builds can benefit from Rust nightly optimizations, although that does not establish an unconditional performance advantage for every source build or workload.

The current build requirements are materially more demanding than those of a pure-Python JSON implementation, but users installing compatible wheels ordinarily do not need to build the Rust extension themselves.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 9.3 Significant recent releases

| Version | Significant change                                                      | Consequence                                                                            |
| ------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 3.13.0  | Added native `frozendict` serialization for Python 3.15                 | New supported type; removed Windows x86 wheels                                         |
| 3.12.0  | Substantially rewrote serialization implementation                      | Internal performance and implementation characteristics can differ from older releases |
| 3.12.0  | Added Python 3.15 wheels                                                | New interpreter compatibility                                                          |
| 3.12.0  | Changed the Python 3.15+ Linux glibc wheel baseline to `manylinux_2_39` | Newer Linux requirements for those wheels                                              |
| 3.11.9  | Raised minimum Rust version to 1.95                                     | Source-build tooling requirement                                                       |
| 3.11.7  | Changed positive float exponent formatting to include `+`               | Potential byte-for-byte output differences                                             |
| 3.11.6  | Dropped Python 3.9 support                                              | Runtime compatibility boundary                                                         |

Source: `https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



A less obvious compatibility principle is documented in orjson's release policy: adding native serialization of a previously unsupported object type without an opt-in option is considered a breaking change.

That policy is meaningful because previously, such an object might have been routed through `default`. After native support is added, the library may bypass that callback, changing the serialized representation.

### 9.4 Licensing and project maintenance model

The project documents source code licensed under MPL 2.0, Apache 2.0, and MIT terms. Precise obligations depend on the relevant files and distribution arrangements.

The canonical upstream repository is `github.com/ijl/orjson`, with a mirror at `codeberg.org/ijl/orjson`.

The maintainer does not operate a public issue tracker or accept pull requests in the conventional open-maintenance model. This affects how downstream projects can report problems or contribute changes, though it does not by itself establish maintenance quality or release reliability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 10. Consequential limitations and interoperability choices

Several limitations are especially relevant when orjson is considered as more than a drop-in performance optimization.

| Requirement or concern                       | orjson's boundary                                | Appropriate complementary capability                        |
| -------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| Typed deserialization                        | Produces Python primitives, not model instances  | Pydantic, msgspec, cattrs, or another typed layer           |
| Schema validation                            | Does not enforce an object schema                | JSON Schema or domain-model validation                      |
| Arbitrary-size integers                      | Native encoding is 64-bit bounded                | Explicit application representation                         |
| Exact decimal arithmetic                     | `Decimal` needs custom conversion                | Decimal-aware schema or string-based encoding               |
| Preservation of NumPy dtype and layout       | JSON loses type/stride metadata                  | Arrow or typed binary data formats                          |
| True incremental parsing                     | Complete document required                       | Streaming parser or format-specific reader                  |
| Native JSONL iteration                       | Not provided                                     | File iteration and a JSONL-oriented companion               |
| Canonical JSON signatures                    | Key sorting alone is insufficient                | Standards-compliant canonicalization                        |
| Configurable decoder hooks                   | Not provided                                     | Standard `json` hooks or a dedicated decoder                |
| Stable representation across future versions | Some formatting and dispatch behavior can change | Version pinning and contract tests                          |
| Untrusted raw JSON fragments                 | `Fragment` skips validation                      | Strict validation before embedding                          |
| Parallel CPU encoding in GIL-enabled CPython | GIL held per call                                | Process-level parallelism or different concurrency strategy |

### 10.1 Comparison with Python's standard `json`

The standard library offers features not found in orjson, including direct file-oriented `dump()`/`load()`, custom parse hooks, arbitrary indentation configuration, ASCII-escaping controls, and an incremental `iterencode()` interface.

orjson trades much of that configurability for a smaller, performance-oriented API, native support for selected Python object families, strict JSON behavior, and direct UTF-8 bytes output.

It is not therefore a strict feature superset of `json`.

### 10.2 Where strictness is useful—and where it stops

Strict Unicode validation and rejection of invalid JSON syntax reduce ambiguity at the document boundary.

But the absence of a validation schema means syntactically valid documents can still contain invalid application data.

Similarly, strict parsing does not impose an application-specific limit on document size or on the number of records a caller chooses to accept. Surrounding systems still need suitable limits on payload size, allocation, request handling, and input trust.

### 10.3 Byte-for-byte reproducibility

Several mechanisms affect output stability:

- Dictionary insertion order and `OPT_SORT_KEYS`.
- Numeric spelling and release-dependent formatting.
- Dataclass field order.
- Datetime timezone and precision options.
- `Fragment` content, whose original bytes are preserved.
- The exact behavior of `default` and passthrough options.

If serialized bytes are used as content hashes, cache keys, digital-signature inputs, or regression-test fixtures, the serialization contract must be more explicit than simply calling `orjson.dumps()`.

The 3.11.7 exponent-format change is a concrete example of how an otherwise valid JSON representation can change at the byte level across releases.

## 11. Capability synthesis

orjson is most distinctive when its native capabilities remove work that would otherwise occur before or around JSON encoding.

Its strongest architectural opportunities are:

Eliminating intermediate object conversion. Native dataclass and NumPy serialization can replace pipelines that first materialize dictionaries, lists, and Python scalar objects.

Keeping representation control local to a serialization boundary. Composable options make it possible to enforce consistent datetime, integer, key, and formatting conventions without building a custom encoder framework.

Combining native and custom behavior. The `default` callback and selective passthrough flags allow specialized conversions while preserving fast native handling for most of the object graph.

Composing serialized documents efficiently. `Fragment` allows existing trusted JSON subdocuments to be reused without recursively decoding and encoding their values.

Reducing unnecessary text conversions. Native byte-buffer input and UTF-8 byte output fit naturally into binary I/O and transport interfaces.

The corresponding limits are equally important: orjson does not provide typed reconstruction, comprehensive validation, canonical serialization, incremental parsing, or preservation of the rich metadata inherent in numerical arrays.

For advanced Python systems, the key distinction is therefore between efficient conversion to and from the JSON data model—orjson's responsibility—and defining, validating, and reconstructing the meaning of that data, which generally belongs to a different layer.

## Primary source reference map

| Topic                                                         | Source                                                                |
| ------------------------------------------------------------- | --------------------------------------------------------------------- |
| Complete tagged API and behavioral documentation              | `https://github.com/ijl/orjson/blob/3.13.0/README.md`                 |
| Version history and compatibility changes                     | `https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md`              |
| PyPI release metadata and binary wheels                       | `https://pypi.org/project/orjson/3.13.0/`                             |
| Rust dependency and build configuration                       | `https://github.com/ijl/orjson/blob/3.13.0/Cargo.toml`                |
| Python package/build metadata                                 | `https://github.com/ijl/orjson/blob/3.13.0/pyproject.toml`            |
| Native extension implementation and interpreter compatibility | `https://github.com/ijl/orjson/blob/3.13.0/src/lib.rs`                |
| FastAPI response integration                                  | `https://fastapi.tiangolo.com/advanced/custom-response/`              |
| FastAPI performance-related release changes                   | `https://fastapi.tiangolo.com/release-notes/`                         |
| Flask/Quart JSON-provider integration                         | `https://flask-orjson.readthedocs.io/en/latest/api/`                  |
| Pydantic's schema-aware serialization                         | `https://pydantic.dev/docs/validation/latest/concepts/serialization/` |

Research basis: tagged orjson 3.13.0 upstream documentation, source and changelog; PyPI artifacts; and current primary documentation for related frameworks. Code examples are illustrative rather than execution-tested.