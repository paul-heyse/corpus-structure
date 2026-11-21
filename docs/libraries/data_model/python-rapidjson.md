# python-rapidjson: Comprehensive Python Library Overview

Research date: November 20, 2026 | Target: python-rapidjson 1.26 | Language: Python / C++ extension

## 1. Executive overview

python-rapidjson is a high-performance JSON serialization, deserialization, and validation library implemented as a CPython extension around Tencent's C++ RapidJSON engine.

Unlike Python JSON libraries focused primarily on accelerating `json.dumps()` and `json.loads()`, python-rapidjson provides a configurable conversion system with native JSON Schema validation, streaming I/O, numeric precision controls, rich Python type support, extensible decoding and encoding hooks, and deliberate handling of nonstandard JSON.

Its particular strength is the combination of performance, configurable serialization semantics, and programmable object transformations.

The library's capabilities extend beyond ordinary JSON encoding:

- Configurable parsing and generation: Strict or relaxed JSON parsing, number-handling modes, formatting, Unicode output, and dictionary-key policies.
- Python type integration: Native support for `Decimal`, `datetime`, `date`, `time`, `UUID`, byte strings, arbitrary mappings, and iterables, with configurable semantics.
- Structural transformation: Custom Python decoder subclasses can intercept strings, construct alternative containers, preserve object key-value pairs, and transform completed arrays or objects.
- Streaming I/O: Incremental reads and writes through Python file-like objects, with configurable buffer sizes.
- JSON Schema validation: Native validation through RapidJSON's C++ schema engine, including structured failure information.
- Raw JSON composition: Embed already-serialized JSON fragments without decoding and re-encoding them.
- Reusable encoder/decoder configurations: Stateful class instances that combine type conversion rules, parsing options, and customization hooks.

The package is best understood as a high-performance JSON boundary and transformation layer, rather than merely a faster JSON parser.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



### Current release and compatibility

| Property              | Verified status                                                           |
| --------------------- | ------------------------------------------------------------------------- |
| Latest stable release | 1.26, released November 1, 2026                                           |
| Python requirement    | Python 3.10 or newer                                                      |
| Implementation        | C++ extension wrapping RapidJSON                                          |
| Package name          | `python-rapidjson`                                                        |
| Import name           | `rapidjson`                                                               |
| License               | MIT                                                                       |
| Platforms             | Prebuilt wheels across supported Linux, Windows, and macOS configurations |
| Python 3.15           | Wheels available, including free-threaded builds                          |
| Latest maintenance    | Parsing, validation, numeric and memory-safety corrections in 1.26        |

Version 1.26 is particularly relevant because its changes include rejecting embedded-NUL truncation, validating mode arguments more consistently, fixing combinations of parsing and numeric modes, and improving JSON Schema validation input handling. These are correctness and robustness changes, not a fundamental redesign of the public API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Documentation caveat: The published Read the Docs site still identifies itself as version 1.17, with a changelog extending to 1.20. This overview therefore uses its detailed API documentation together with the newer PyPI release notes and upstream implementation. Version-sensitive claims are distinguished where appropriate.

Primary resources:

- Repository: `https://github.com/python-rapidjson/python-rapidjson`
- Documentation: `https://python-rapidjson.readthedocs.io/en/latest/`
- PyPI and release history: `https://pypi.org/project/python-rapidjson/`

## 2. Architecture and capability map

The library exposes a Python-native interface while delegating much of the actual JSON parsing, generation, and schema validation to native C++ machinery.

Python application data

Objects, mappings, iterables, streams, and custom types

Conversion and extension hooks

### python-rapidjson

Parsing and generation

Type conversion policies

Custom object construction

Streaming adapters

Raw JSON insertion

Schema validation

Native C++ operations

RapidJSON C++ engine

Parser, writers, stream interfaces, schema validator

### Capability families

| Family                          | Core interfaces                  | Distinctive contribution                                                   |
| ------------------------------- | -------------------------------- | -------------------------------------------------------------------------- |
| Serialization                   | `dumps`, `dump`, `Encoder`       | Configurable type conversion, output formatting, custom encoders           |
| Deserialization                 | `loads`, `load`, `Decoder`       | Configurable parsing, native type reconstruction, structural hooks         |
| Numeric semantics               | `NM_*`                           | Arbitrary-precision integers, `Decimal`, native numeric conversion         |
| Temporal and identity types     | `DM_*`, `UM_*`                   | ISO 8601, Unix timestamps, timezone handling, UUID conversion              |
| Structural policies             | `IM_*`, `MM_*`, `BM_*`           | Generic iterable and mapping handling, string-key policies, bytes handling |
| JSON extensions                 | `PM_*`                           | Comments and trailing commas                                               |
| Schema validation               | `Validator`                      | Native schema checking with JSON-pointer error locations                   |
| Serialized-fragment composition | `RawJSON`                        | Direct insertion of preserialized JSON                                     |
| Stream processing               | `load`, `dump`, callable classes | Bounded I/O buffers instead of requiring an entire serialized string       |

### Important architectural boundaries

Three distinctions govern how these capabilities should be understood.

First, the Python package does not expose the entire C++ RapidJSON API. RapidJSON itself includes DOM and SAX interfaces, low-level memory allocators, encoding abstractions, and other C++ facilities. Their presence in the underlying engine does not mean they are separately accessible through python-rapidjson.

Second, streaming I/O does not automatically mean streaming Python object iteration. The library can read and write in chunks, but its documented decoding APIs return a complete Python value. They are not equivalent to an event-based parser yielding JSON tokens or records one at a time.

Third, the serializer and deserializer implement configurable policies, not a universal reversible representation of arbitrary Python objects. Type restoration depends on the chosen modes, and some conversions intentionally discard information.

These distinctions are important when assessing its suitability for structured interchange, large-document processing, or lossless data representation.

## 3. Core serialization and deserialization interfaces

python-rapidjson exposes two complementary APIs: stateless module functions and reusable class-based encoders/decoders.

| Interface                                | Operation                                      | Result                      |
| ---------------------------------------- | ---------------------------------------------- | --------------------------- |
| `rapidjson.dumps(obj, **options)`        | Serialize a Python value                       | JSON `str`                  |
| `rapidjson.dump(obj, stream, **options)` | Serialize into a writable stream               | Writes JSON, returns `None` |
| `rapidjson.loads(data, **options)`       | Parse JSON from `str`, `bytes`, or `bytearray` | Python value                |
| `rapidjson.load(stream, **options)`      | Parse JSON from a readable stream              | Python value                |
| `rapidjson.Encoder(**options)`           | Construct a reusable serializer                | Callable encoder            |
| `rapidjson.Decoder(**options)`           | Construct a reusable parser                    | Callable decoder            |

`Encoder` and `Decoder` are particularly useful because they encapsulate conversion policies and offer subclass-based extension mechanisms.

For example:

```
import rapidjson as rjencoder = rj.Encoder(    number_mode=rj.NM_DECIMAL,    datetime_mode=rj.DM_ISO8601,    uuid_mode=rj.UM_CANONICAL,    ensure_ascii=False,)decoder = rj.Decoder(    number_mode=rj.NM_DECIMAL,    datetime_mode=rj.DM_ISO8601,    uuid_mode=rj.UM_CANONICAL,)json_text = encoder(data)restored = decoder(json_text)
```

This separates serialization policy from the individual values being processed.

Unlike the standard library's custom `JSONEncoder`, `rapidjson.Encoder` is callable directly. Its `__call__(obj, stream=None, *, chunk_size=65536)` method can either return a string or write into a stream. Similarly, `Decoder.__call__()` accepts JSON text, UTF-8 bytes, or a readable stream.

The class APIs support some customization that cannot be expressed through the module functions alone, especially alternative container construction and primitive string conversion.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/encoder.html`

`https://python-rapidjson.readthedocs.io/en/latest/decoder.html`

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+3

## 4. Numeric representation and precision

Numeric handling is one of python-rapidjson's most consequential capabilities.

The library explicitly separates three concerns:

1. Whether JSON numeric literals should become native binary floating-point values or `Decimal` objects.
2. Whether arbitrarily large Python integers should retain their exact representation.
3. Whether non-finite values should be accepted, despite their incompatibility with strict JSON.

### 4.1 Number modes

| Mode         | Main behavior                                                                   | Important qualification                                        |
| ------------ | ------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `NM_NONE`    | Regular integer and floating-point handling without non-finite extensions       | Arbitrarily large integers can remain exact                    |
| `NM_DECIMAL` | Decode nonintegral JSON numbers as `Decimal`; serialize Python `Decimal` values | Retains decimal numeric representations                        |
| `NM_NATIVE`  | Use RapidJSON's native numeric conversion paths                                 | Faster in some workloads, but introduces machine-number limits |
| `NM_NAN`     | Enable `NaN`, `Infinity`, and `-Infinity`                                       | Not valid strict JSON                                          |

Most flags are combinable with bitwise OR, but compatibility differs between encoding and decoding.

### 4.2 Arbitrary-precision integers versus native arithmetic

By default, integer serialization preserves integers beyond the range supported by C++'s native 64-bit integer types.

```
n = 123456789012345678901234567890rj.dumps(n)# '123456789012345678901234567890'rj.loads(str(n))# 123456789012345678901234567890
```

The ordinary path avoids narrowing large integer representations to machine integers.

`NM_NATIVE` changes this behavior.

During encoding, integers that exceed the supported native range can raise `OverflowError`.

During decoding, an integer literal too large for the native integer representation can be converted to a `double`, thereby losing precision.

For example, the official documentation shows:

```
rj.loads(    "123456789012345678901234567890",    number_mode=rj.NM_NATIVE,)# 1.2345678901234566e+29
```

This asymmetry matters for large identifiers, database keys, exact counters, financial values, and reproducible scientific data.

`NM_NATIVE` is a performance optimization with a semantic cost, not an equivalent alternative to the default numeric representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



### 4.3 Decimal-preserving conversion

`NM_DECIMAL` changes the interpretation of JSON floating-point literals:

```
from decimal import Decimalvalue = rj.loads(    "3.1415926535897932384626433832795028841971",    number_mode=rj.NM_DECIMAL,)assert isinstance(value, Decimal)
```

Conversely:

```
rj.dumps(    Decimal("3.1415926535897932384626433832795028841971"),    number_mode=rj.NM_DECIMAL,)# '3.1415926535897932384626433832795028841971'
```

The important capability is native handling of decimal numbers without first converting them to binary floats.

This removes the need for a custom parser that reconstructs decimal numbers from their original JSON tokens.

The distinction also determines which types are reconstructed:

- Integer literals ordinarily remain Python `int` values.
- Floating-point literals become `Decimal` under `NM_DECIMAL`.
- Non-finite numeric tokens become `Decimal` equivalents when both `NM_DECIMAL` and `NM_NAN` are enabled.

The library's documentation explicitly distinguishes encoding and decoding combinations: `NM_NATIVE | NM_DECIMAL` is supported for serialization, but these modes are incompatible for deserialization because native conversion can already have discarded numeric precision.

Source: `https://python-rapidjson.readthedocs.io/en/latest/loads.html`

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1

### 4.4 Non-finite numeric values and standards compliance

By default, python-rapidjson accepts and emits non-finite numeric values:

```
rj.dumps([float("nan"), float("inf")])# '[NaN,Infinity]'
```

This is compatible with some JavaScript-style JSON implementations but is not valid RFC-compliant JSON.

For strict interchange:

```
rj.dumps(value, allow_nan=False)rj.loads(json_text, allow_nan=False)
```

Alternatively, use a `number_mode` configuration that excludes `NM_NAN`.

A subtle version-specific improvement in 1.26 normalizes certain unusual `Decimal` NaN representations before serialization so that enabled non-finite output remains readable by the corresponding decoder.

For strict JSON systems, the critical point is that `PM_NONE` alone does not disable non-finite numbers: numeric and syntax-extension settings are separate.

## 5. Native date, time, timezone, and UUID conversion

These are among the library's most useful alternatives to application-specific serialization callbacks.

### 5.1 Datetime mode system

| Flag              | Capability                                      |
| ----------------- | ----------------------------------------------- |
| `DM_NONE`         | No special temporal handling                    |
| `DM_ISO8601`      | Bidirectional ISO 8601 conversion               |
| `DM_UNIX_TIME`    | Serialize temporal values as numeric timestamps |
| `DM_ONLY_SECONDS` | Drop subsecond precision in Unix-time output    |
| `DM_IGNORE_TZ`    | Discard timezone information                    |
| `DM_NAIVE_IS_UTC` | Treat naive values as UTC                       |
| `DM_SHIFT_TO_UTC` | Normalize timezone-aware values to UTC          |

`DM_ISO8601` recognizes `datetime.datetime`, `datetime.date`, and `datetime.time` instances during serialization.

During deserialization, it can recognize corresponding ISO 8601 strings and reconstruct appropriate Python objects.

```
from datetime import datetime, timezonevalue = datetime(    2026, 11, 20, 18, 45,    tzinfo=timezone.utc,)mode = rj.DM_ISO8601 | rj.DM_SHIFT_TO_UTCencoded = rj.dumps(value, datetime_mode=mode)decoded = rj.loads(encoded, datetime_mode=mode)
```

### 5.2 Timezone policies are semantically different

`DM_NAIVE_IS_UTC` interprets naive timestamps as already being UTC.

`DM_SHIFT_TO_UTC` converts an aware timestamp to its equivalent UTC instant.

`DM_IGNORE_TZ` removes timezone information without preserving the same instant through normalization.

These operations are not interchangeable.

For example, ignoring a `+02:00` timezone preserves the displayed clock time while losing its original offset; shifting to UTC changes the clock time to preserve the instant.

For time-only values, `DM_SHIFT_TO_UTC` has a documented limitation: a shifted value that requires crossing a date boundary may not be representable by Python's `time` type, resulting in an error.

### 5.3 Unix timestamps are serialization-only

`DM_UNIX_TIME` emits numerical values:

- `datetime`: seconds relative to the Unix epoch.
- `date`: equivalent timestamp for midnight.
- `time`: seconds since midnight.

`DM_ONLY_SECONDS` suppresses microseconds, producing whole-second values.

Deserialization with `DM_UNIX_TIME` is intentionally unsupported because a number by itself provides no reliable indication of whether it represents a timestamp, quantity, identifier, or something else.

This is a useful distinction from libraries that automatically reinterpret arbitrary numeric fields.

### 5.4 Global inference during parsing

One significant consideration is that `DM_ISO8601` performs recognition based on string content.

A JSON string that happens to resemble a date may be converted into a Python date even if the application's schema intended it to remain text.

The same is true for UUID recognition.

The native modes therefore work particularly well when a JSON contract consistently assigns semantic meaning to these representations. They are less appropriate when identical-looking strings have different meanings in different fields.

In those cases, decoding plain strings and applying type conversions through object-level hooks or an external schema-aware layer gives the application more control.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/dumps.html`

`https://python-rapidjson.readthedocs.io/en/latest/loads.html`

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+3

### 5.5 UUID representations

UUID handling supports two modes:

| Mode           | Encoding                                     | Decoding                                          |
| -------------- | -------------------------------------------- | ------------------------------------------------- |
| `UM_NONE`      | No native UUID conversion                    | Strings remain strings                            |
| `UM_CANONICAL` | Hyphenated 36-character string               | Recognizes canonical representation               |
| `UM_HEX`       | Unhyphenated 32-character hexadecimal string | Recognizes both hex and canonical representations |

```
from uuid import uuid4value = uuid4()json_value = rj.dumps(    value,    uuid_mode=rj.UM_CANONICAL,)restored = rj.loads(    json_value,    uuid_mode=rj.UM_CANONICAL,)
```

The `UM_HEX` asymmetry is useful: it accepts both representations when parsing but produces one normalized representation when encoding.

However, reconstructing UUIDs from arbitrary matching strings remains a global inference policy, not field-aware validation.

## 6. Generic iterable, mapping, and byte handling

Unlike some high-performance JSON libraries that support a deliberately narrow selection of Python container types, python-rapidjson provides configurable support for Python's broader container protocols.

### 6.1 Iterable modes

| Mode              | Behavior                                            |
| ----------------- | --------------------------------------------------- |
| `IM_ANY_ITERABLE` | Encode arbitrary supported iterables as JSON arrays |
| `IM_ONLY_LISTS`   | Restrict automatic array encoding to Python lists   |

Under the default mode, tuples, generators, iterators, and custom iterable objects can become JSON arrays.

```
rj.dumps((1, 2, 3))# '[1,2,3]'rj.dumps(x * x for x in range(4))# '[0,1,4,9]'
```

This is useful for serialization directly from lazy Python computations.

There is an important tradeoff: a class with an iterator protocol may have richer semantics than an ordinary sequence. Automatically representing it as an array can erase that meaning.

`IM_ONLY_LISTS` disables the broad conversion behavior so that a custom `default` handler or encoder subclass can control those objects instead.

It also provides a way to distinguish subclasses and special sequence-like types that should not automatically use their ordinary iterable representation.

### 6.2 Mapping modes

| Mode                        | Behavior                                               |
| --------------------------- | ------------------------------------------------------ |
| `MM_ANY_MAPPING`            | Serialize mappings beyond ordinary dictionaries        |
| `MM_ONLY_DICTS`             | Restrict automatic object encoding to dictionaries     |
| `MM_COERCE_KEYS_TO_STRINGS` | Convert non-string keys using Python string conversion |
| `MM_SKIP_NON_STRING_KEYS`   | Discard non-string keys                                |
| `MM_SORT_KEYS`              | Sort object keys alphabetically                        |

The default generic-mapping support accommodates types such as `collections.Counter`, mapping implementations, and custom mapping objects.

`MM_ONLY_DICTS` becomes useful when such types should receive specialized serialization.

For example, a `Counter` may be intended to retain type metadata instead of becoming indistinguishable from a dictionary.

### 6.3 Dictionary-key semantics

Unlike Python's standard `json.dumps()`, python-rapidjson normally rejects non-string dictionary keys.

The native alternatives have distinct implications.

Coercion:

```
rj.dumps(    {-1: "negative", True: "boolean"},    mapping_mode=rj.MM_COERCE_KEYS_TO_STRINGS,)# '{"-1":"negative","True":"boolean"}'
```

Skipping:

```
rj.dumps(    {"name": "example", 42: "discarded"},    mapping_mode=rj.MM_SKIP_NON_STRING_KEYS,)# '{"name":"example"}'
```

Sorting:

```
rj.dumps(    {"z": 1, "a": 2},    mapping_mode=rj.MM_SORT_KEYS,)# '{"a":2,"z":1}'
```

The older keyword arguments `skipkeys` and `sort_keys` remain available for compatibility.

Key coercion deserves particular attention: it can create collisions between distinct Python keys and does not preserve their original types. For example, integer `1` and string `"1"` are distinct Python dictionary keys, but both can become the same JSON object key.

Sorting is useful for predictable key ordering, but it should not be confused with a complete canonical JSON serialization standard.

### 6.4 Bytes modes

The library's default `BM_UTF8` treats `bytes` and `bytearray` values as UTF-8 text.

This differs from serializers that reject all bytes objects or encode them automatically as Base64.

```
rj.dumps(b"hello")# '"hello"'
```

The default behavior does not provide arbitrary binary data interchange.

For genuine binary payloads, `BM_NONE` disables automatic text conversion, allowing a custom handler to select an explicit representation such as Base64, hexadecimal, or a tagged object.

```
import base64def serialize_special(value):    if isinstance(value, bytes):        return {            "__type__": "bytes",            "base64": base64.b64encode(value).decode("ascii"),        }    raise TypeError(f"Unsupported type: {type(value)!r}")encoded = rj.dumps(    b"\x00\xff",    bytes_mode=rj.BM_NONE,    default=serialize_special,)
```

This combination is important because it allows the application to establish a controlled, reversible binary representation while retaining the library's native handling of ordinary JSON types.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/api.html`

`https://python-rapidjson.readthedocs.io/en/latest/dumps.html`

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+3

## 7. Extensibility: custom serialization and structural decoding

The most distinctive extension capability is not the `default` serialization callback, which resembles Python's standard JSON library, but the ability to intervene at several stages of native decoding.

### 7.1 Custom serialization

For arbitrary Python classes, `dumps()` and `dump()` accept a `default` callback that converts otherwise unsupported values into JSON-compatible types.

The class-based equivalent is `Encoder.default(self, value)`.

```
from dataclasses import dataclassimport rapidjson as rj@dataclassclass Point:    x: float    y: floatclass DomainEncoder(rj.Encoder):    def default(self, value):        if isinstance(value, Point):            return {                "__type__": "Point",                "x": value.x,                "y": value.y,            }        raise TypeError(f"Cannot encode {type(value)!r}")encoder = DomainEncoder()encoded = encoder(Point(2.5, 4.0))
```

A `default` handler only receives values the native serializer does not already know how to represent.

That qualification matters when configuring `IM_ANY_ITERABLE` or `MM_ANY_MAPPING`. A custom class implementing the iterable or mapping protocol can be serialized automatically, preventing its `default` handler from running.

To give such objects specialized representations, the automatic conversion policies can be narrowed using `IM_ONLY_LISTS` or `MM_ONLY_DICTS`.

This is an important interaction: native container modes determine which objects remain available to application-defined conversion logic.

Source: `https://python-rapidjson.readthedocs.io/en/latest/encoder.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



### 7.2 Object reconstruction with `object_hook`

The ordinary `loads()` and `load()` functions accept `object_hook`.

The callback receives a fully decoded dictionary and may return a replacement Python object.

For example, it could reconstruct tagged domain objects:

```
def restore_object(obj):    if obj.get("__type__") == "Point":        return Point(obj["x"], obj["y"])    return objdecoded = rj.loads(encoded, object_hook=restore_object)
```

The callback is invoked for nested JSON objects as they finish decoding, which permits bottom-up reconstruction of composite structures.

However, an ordinary dictionary is already created when `object_hook` runs. Duplicate JSON keys have consequently lost their distinct occurrences.

For applications that require access to the original key-value sequence, the class-based decoder provides a deeper extension point.

### 7.3 The four `Decoder` hooks

| Hook                  | Invocation point         | Capability                                               |
| --------------------- | ------------------------ | -------------------------------------------------------- |
| `start_object()`      | Encountering `{`         | Choose how object members will be collected              |
| `end_object(mapping)` | Completing a JSON object | Replace an object with another Python value              |
| `end_array(sequence)` | Completing a JSON array  | Replace an array with another Python value               |
| `string(s)`           | Completing a JSON string | Convert string values into custom Python representations |

These hooks let the application change the Python object graph during parsing rather than performing a separate recursive traversal afterward.

`start_object()` is particularly powerful. It may return a mutable mapping or a list. If it returns a list, the parser appends `(key, value)` pairs instead of immediately constructing a dictionary.

This provides direct access to information that conventional dictionary decoding discards.

### 7.4 Preserving key occurrences and detecting duplicates

Consider:

```
{"id": 10, "id": 20}
```

Ordinary dictionary decoding cannot represent both occurrences of `"id"`.

A decoder subclass can preserve the pairs and determine what to do with duplicates:

```
class UniqueKeyDecoder(rj.Decoder):    def start_object(self):        return []    def end_object(self, pairs):        result = {}        for key, value in pairs:            if key in result:                raise ValueError(                    f"Duplicate JSON object key: {key!r}"                )            result[key] = value        return resultdecoder = UniqueKeyDecoder()decoder('{"id": 10}')# {'id': 10}decoder('{"id": 10, "id": 20}')# ValueError
```

This is a useful native mechanism for strict ingestion, signature-sensitive payloads, or interchange formats where duplicate names must be rejected.

Alternatively, omitting `end_object()` entirely preserves the object as a list of key-value tuples. This can be valuable when the original member sequence, including duplicates, is part of the information being analyzed.

The key distinction is that `start_object()` changes collection behavior before the information is lost; `object_hook` operates after dictionary creation.

### 7.5 Custom array and string reconstruction

`end_array()` can replace ordinary lists with tuples, immutable collections, or domain-specific containers.

```
class TupleDecoder(rj.Decoder):    def end_array(self, sequence):        return tuple(sequence)decoder = TupleDecoder()decoder('[1, [2, 3]]')# (1, (2, 3))
```

`string()` provides a corresponding extension point for string values.

It can implement additional string representations, normalization conventions, or tagged scalar formats without a separate traversal.

There is an important ordering rule: the `string()` hook executes after the library's native ISO 8601 and UUID recognition.

If native recognition converts a JSON string to a `datetime` or `UUID`, the string hook does not receive that value as an ordinary string.

This gives native conversions priority over custom string transformations.

Taken together, the decoder hooks can support highly specialized Python object models while retaining the C++ parser's lexical and structural processing.

The main cost is additional Python callback execution, which can become significant when hooks run for every scalar or container.

Primary reference: `https://python-rapidjson.readthedocs.io/en/latest/decoder.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



## 8. Relaxed JSON parsing and output formatting

python-rapidjson separates input-language extensions from output-formatting decisions.

This distinction makes it possible to accept mildly nonstandard JSON while continuing to produce standards-oriented output.

### 8.1 Parsing modes

| Mode                                 | Accepted syntax                                   |
| ------------------------------------ | ------------------------------------------------- |
| `PM_NONE`                            | No comment or trailing-comma extensions           |
| `PM_COMMENTS`                        | `//` line comments and `/* ... */` block comments |
| `PM_TRAILING_COMMAS`                 | Trailing commas in arrays and objects             |
| `PM_COMMENTS \\| PM_TRAILING_COMMAS` | Both extensions                                   |

For example:

```
config_text = """{    // Processing options    "enabled": true,    "thresholds": [0.2, 0.5, 0.9,],}"""config = rj.loads(    config_text,    parse_mode=(        rj.PM_COMMENTS |        rj.PM_TRAILING_COMMAS    ),)
```

The parser discards comments and accepts trailing commas while constructing ordinary Python values.

This makes the library useful for configuration formats often referred to as JSON with comments or JSONC.

However, these modes do not turn the library into a general JSON5 or JavaScript parser. They do not imply support for unquoted property names, single-quoted strings, or arbitrary JavaScript expressions.

The separation between `parse_mode` and `number_mode` also matters: disabling comments and trailing commas does not, by itself, disable non-finite numbers. Strict RFC-oriented parsing requires an appropriate number mode or `allow_nan=False`.

Version 1.26 specifically corrected interactions between parsing flags and numeric modes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



### 8.2 Output formatting

The write modes provide distinct formatting behavior:

| Mode                   | Result                                                                   |
| ---------------------- | ------------------------------------------------------------------------ |
| `WM_COMPACT`           | Minimal whitespace                                                       |
| `WM_PRETTY`            | Multiline indented JSON                                                  |
| `WM_SINGLE_LINE_ARRAY` | Pretty formatting while keeping arrays on a single line where applicable |

`WM_SINGLE_LINE_ARRAY` is notable because it offers an intermediate format between compact JSON and fully expanded pretty-print output.

It is useful for configurations and structured reports where short arrays should remain easy to scan without consuming multiple lines.

The `indent` parameter accepts a nonnegative integer or a string consisting of repetitions of a single ASCII whitespace character. The latter permits tab indentation as well as spaces.

Specifying an explicit indentation value can also activate pretty-printing unless a write mode has been explicitly supplied.

```
rj.dumps(data, indent=2)rj.dumps(    data,    write_mode=rj.WM_SINGLE_LINE_ARRAY,    indent=2,)
```

Other formatting decisions are independent:

- `ensure_ascii=True` escapes non-ASCII characters; `False` emits them directly.
- `MM_SORT_KEYS` provides alphabetically ordered keys.
- Number modes determine numeric conversion.
- `RawJSON` can preserve an embedded fragment's original formatting.

The last point introduces an exception to the normal formatting policy: raw fragments are inserted without being reformatted by the surrounding writer.

Stable formatting is not automatically canonical JSON. Alphabetical key sorting and compact output do not establish all the number, Unicode, and representation rules required by a formal canonicalization specification.

Source: `https://python-rapidjson.readthedocs.io/en/latest/dumps.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



## 9. Streaming I/O and memory behavior

The file-oriented APIs are more substantial than convenience wrappers around `dumps()` and `loads()`.

They use stream adapters between Python's file-like objects and RapidJSON's native readers and writers.

### 9.1 Incremental stream reads

`load(stream, chunk_size=65536)` reads from a Python file-like object in chunks.

```
with open("document.json", "rb") as stream:    document = rj.load(        stream,        chunk_size=256 * 1024,    )
```

The buffer size controls the size of individual `read()` operations.

Increasing it may reduce Python method-call overhead, while smaller buffers may suit memory-constrained or latency-sensitive streams.

However, chunked reading does not imply that the decoded object graph is produced incrementally for the caller.

The result of `load()` is a complete Python value. A large JSON array ordinarily becomes a complete Python list before the call returns.

The API does not expose a Python generator of parser events, an element-at-a-time array iterator, or an asynchronous JSON parser.

### 9.2 Incremental stream writes

`dump(obj, stream, chunk_size=65536)` writes serialized data into a Python stream using a bounded output buffer.

```
with open("document.json", "wb") as stream:    rj.dump(        data,        stream,        chunk_size=256 * 1024,    )
```

Both binary and text streams are supported.

The implementation distinguishes them using the presence of an `encoding` attribute on the stream. This is worth knowing when supplying custom stream wrappers: a wrapper's attributes can determine whether the writer calls `write()` with bytes or strings.

### 9.3 Combining generic iterables and stream writing

A particularly useful combination is:

```
def generate_records():    for i in range(1_000_000):        yield {            "id": i,            "square": i * i,        }with open("records.json", "wb") as stream:    rj.dump(        generate_records(),        stream,        chunk_size=65536,    )
```

The serializer can consume the generator as a JSON array and write output incrementally.

This avoids creating both a million-element Python list and a giant serialized JSON string before writing.

It does not mean that every intermediate allocation is eliminated. Each yielded record still exists as a Python object while it is being encoded.

The distinction is especially valuable when evaluating large outbound datasets.

### 9.4 Input buffering and zero-copy limitations

Inspection of the version 1.26 C++ implementation shows that decoding JSON supplied directly as a string or byte buffer involves creating a mutable input copy for native parsing.

Consequently, it would be inaccurate to characterize ordinary `rapidjson.loads()` as a zero-copy JSON parser.

The stream-based reader can consume buffered input without requiring an initial application-level read of the entire document, but the decoded Python object graph must still be constructed.

The useful memory distinctions are therefore:

| Operation           | Buffering behavior                               | Result materialization                    |
| ------------------- | ------------------------------------------------ | ----------------------------------------- |
| `dumps(obj)`        | Constructs serialized output                     | Complete output string                    |
| `dump(obj, stream)` | Buffered output writes                           | Does not require a complete output string |
| `loads(data)`       | Uses native parsing over a prepared input buffer | Complete Python result                    |
| `load(stream)`      | Buffered input reads                             | Complete Python result                    |

For a JSON Lines or NDJSON dataset, an external record-framing layer remains necessary. Individual lines can be decoded with `loads()`, but `load()` is not itself a multi-document iterator.

This distinction also separates python-rapidjson from libraries specifically designed for streaming token or event extraction.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/load.html`

`https://python-rapidjson.readthedocs.io/en/latest/dump.html`

`https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/rapidjson.cpp`

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+2

## 10. Native JSON Schema validation

`rapidjson.Validator` is a substantial capability that distinguishes this library from serializers offering no schema-validation engine.

Rather than requiring JSON data to be decoded into Python and then checked by Python validation logic, it exposes RapidJSON's native schema machinery.

### 10.1 Core interface

```
schema = """{    "type": "object",    "required": ["id"],    "properties": {        "id": {"type": "integer"}    }}"""validate = rj.Validator(schema)validate('{"id": 42}')  # Success: returns Nonetry:    validate('{"id": "forty-two"}')except rj.ValidationError as exc:    keyword, schema_pointer, document_pointer = exc.args
```

The validator is constructed from JSON schema text and subsequently called with JSON document text.

On success, validation completes without returning a parsed Python object.

On failure, `ValidationError` exposes a structured three-part diagnostic:

1. The violated schema keyword.
2. A JSON Pointer locating the relevant part of the schema.
3. A JSON Pointer locating the corresponding part of the document.

For instance, the documented failure of an integer array element against a string schema produces:

```
("type", "#/items", "#/0")
```

This is useful for diagnostics because the caller can identify both the violated constraint and the offending document location without inferring them from an English error message.

Malformed JSON is handled separately through `JSONDecodeError`.

Reference: `https://python-rapidjson.readthedocs.io/en/latest/validator.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



### 10.2 Supported JSON Schema dialect

The underlying RapidJSON engine implements JSON Schema Draft 4.

Its capabilities include the major Draft 4 constraint families:

| Family                 | Examples                                         |
| ---------------------- | ------------------------------------------------ |
| Structural types       | `type`, `properties`, `items`                    |
| Required data          | `required`, `dependencies`                       |
| Additional content     | `additionalProperties`, `additionalItems`        |
| Cardinality and length | `minItems`, `maxItems`, `minLength`, `maxLength` |
| Numeric constraints    | `minimum`, `maximum`, `multipleOf`               |
| Enumeration            | `enum`                                           |
| Composition            | `allOf`, `anyOf`, `oneOf`, `not`                 |
| References             | Local `$ref` references                          |
| Patterns               | `pattern`, `patternProperties`                   |

The engine does not provide general support for the later JSON Schema 2019-09 and 2020-12 vocabularies through this interface.

In particular, one should not assume modern keywords such as `unevaluatedProperties`, `$dynamicRef`, or `prefixItems` will receive the semantics specified by newer JSON Schema drafts.

### 10.3 Important conformance limits

There are several material limitations inherited from the native implementation.

`format` is ignored. A schema that says a string has `"format": "email"` or `"format": "date-time"` does not thereby enforce the format through RapidJSON's validator.

Regular-expression support is limited. By default, the engine uses its own NFA-based pattern matcher rather than Python's `re` engine or a full PCRE implementation. Schemas using advanced regular-expression constructs may not behave as expected.

Remote `$ref` resolution is not exposed as a Python extension point. The C++ API supports an application-supplied `IRemoteSchemaDocumentProvider`. The Python binding does not document a corresponding provider callback, and inspection of its tagged implementation does not show such a provider being passed to schema construction.

Local references can therefore be useful, but external URI-based reference resolution should not be assumed.

RapidJSON's upstream documentation also identifies a Draft 4 conformance-suite limitation involving reference-scope resolution. This matters most for complex schema graphs rather than ordinary single-document validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rapidjson.org\&sz=32)

rapidjson.org+1



Primary engine reference: `https://rapidjson.org/md_doc_schema.html`

### 10.4 Validation is not integrated with Python decoding

The distinction between the native C++ engine and the Python binding is especially important here.

RapidJSON's C++ API supports validation directly from SAX parsing events, including early termination on failure.

However, the Python binding's `Validator` accepts an entire JSON document as a string or bytes object. Its implementation parses that input into a native RapidJSON document and validates the document against its schema.

It does not expose the engine's incremental SAX validation interface to Python applications.

Additionally, `Validator` operates on serialized JSON, not arbitrary Python objects.

The two general workflows are therefore different:

| Workflow                | Behavior                                                |
| ----------------------- | ------------------------------------------------------- |
| `Validator(json_text)`  | Validate the JSON document against Draft 4 schema rules |
| `loads(json_text, ...)` | Construct Python objects according to decoding modes    |

The validator does not automatically apply `NM_DECIMAL`, ISO 8601 recognition, UUID reconstruction, or custom decoder hooks.

Conversely, a custom `Decoder` does not automatically validate against the schema.

These capabilities can be composed sequentially, but their semantics remain separate.

That is a significant architectural distinction when exact numeric validation or schema-aware type reconstruction is required.

## 11. RawJSON: composing preserialized documents

`rapidjson.RawJSON` is another unusually powerful feature.

It represents a JSON fragment that should be included directly in the writer's output rather than encoded as a Python string.

```
fragment = rj.RawJSON(    '{"items": [1, 2, 3]}')result = rj.dumps({    "type": "batch",    "payload": fragment,})# {"type":"batch","payload":{"items": [1, 2, 3]}}
```

This is different from:

```
rj.dumps({    "payload": '{"items": [1, 2, 3]}'})
```

In the latter case, the fragment becomes an escaped JSON string value, not a nested object.

### 11.1 Architectural value

Suppose a system already stores serialized JSON records or receives serialized subdocuments from another component.

The conventional composition sequence is:

1. Decode each fragment into Python.
2. Construct the containing object.
3. Serialize everything again.

`RawJSON` can eliminate the fragment-specific decode/re-encode cycle.

It also allows the fragment's original whitespace to remain intact.

This may be useful for preserving already-generated JSON payloads or efficiently assembling compound responses from trusted serialized components.

### 11.2 Validation and trust boundary

`RawJSON` deliberately performs no validation of the embedded fragment.

```
rj.dumps({    "payload": rj.RawJSON("[1,")})
```

The resulting document can be invalid JSON.

This is not a bug in its intended behavior; it is the mechanism that makes direct insertion possible.

It follows that `RawJSON` is best treated as an operation on trusted, already-validated serialized data.

An application can validate fragments before storing or embedding them, but the library does not enforce that automatically.

Another consequential distinction is that the surrounding serializer's formatting policies do not normalize the raw fragment.

For systems depending on canonical representation or reproducible bytes, `RawJSON` needs particular care.

Reference: `https://python-rapidjson.readthedocs.io/en/latest/rawjson.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



## 12. Error handling, data integrity, and robustness

Several cross-cutting semantics deserve attention because they determine whether a serialized or reconstructed representation can be trusted.

### 12.1 Failure categories

| Situation                                         | Typical exception or behavior             |
| ------------------------------------------------- | ----------------------------------------- |
| Invalid JSON syntax                               | `rapidjson.JSONDecodeError`               |
| Invalid schema or document JSON                   | `rapidjson.JSONDecodeError`               |
| JSON Schema constraint failure                    | `rapidjson.ValidationError`               |
| Unsupported Python object without conversion hook | `TypeError`                               |
| Invalid mode combinations or arguments            | `ValueError`                              |
| Integer outside native-mode encoding range        | `OverflowError`                           |
| Excessive structural nesting                      | Parser failure or recursion-related limit |

`JSONDecodeError` provides parse diagnostics, including error offsets in documented examples, but should not be assumed to reproduce all of the standard library exception's attributes and formatting.

`ValidationError`, by contrast, provides explicitly documented structured diagnostic arguments.

### 12.2 Information loss and semantic coercion

The most significant information-loss mechanisms are:

| Mechanism                              | Information potentially lost                                   |
| -------------------------------------- | -------------------------------------------------------------- |
| Ordinary object decoding               | Duplicate key occurrences                                      |
| `MM_SKIP_NON_STRING_KEYS`              | Entire key-value pairs                                         |
| `MM_COERCE_KEYS_TO_STRINGS`            | Original key types; potentially distinct keys after collisions |
| `NM_NATIVE`                            | Exact representation of sufficiently large integers            |
| Ordinary binary floating-point parsing | Original decimal precision                                     |
| `DM_IGNORE_TZ`                         | Timezone and offset information                                |
| Generic iterable serialization         | Original container type and semantics                          |
| Native ISO 8601 / UUID recognition     | Whether a matching string was intended as plain text           |

Not every loss is undesirable. In many interchange formats, the conversion is precisely what the caller wants.

The important point is that the serializer's output contract must determine whether a conversion is acceptable, rather than assuming serialization and deserialization are universally reversible.

### 12.3 Limits for untrusted data

Because the core parser and generator are implemented in C++, native memory safety and robust input handling are significant considerations.

Recent maintenance demonstrates active attention to such issues. Version 1.24 addressed a crash when serializing a list that changes during encoding. Version 1.26 closed embedded-NUL truncation cases involving ordinary JSON input and validator schema/document input, alongside several mode-validation defects.

These changes improve robustness but are not equivalent to a guarantee that arbitrary hostile input can be processed with bounded CPU or memory.

At application boundaries, input size, nesting depth, schema complexity, and the behavior of custom Python hooks still need to be considered.

One particular risk is that decoding a very large valid JSON document can create a substantially larger Python object graph than the serialized input's size suggests.

Source: `https://pypi.org/project/python-rapidjson/1.26/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 13. Performance characteristics and benchmark interpretation

Performance is a central reason to consider python-rapidjson, but the library's benchmark documentation illustrates why the selected conversion policy matters as much as the engine itself.

### 13.1 What the native implementation accelerates

The library benefits from performing lexical parsing, structural JSON interpretation, and output generation in compiled C++ code.

Its performance advantages are most pronounced when the workload consists of conventional JSON-compatible structures that can move through the native conversion paths without extensive Python callbacks.

Several capabilities alter the workload:

- `NM_NATIVE` simplifies numeric conversion but can sacrifice precision.
- `NM_DECIMAL` constructs Python decimal objects, which is more semantically expressive but changes conversion costs.
- `MM_SORT_KEYS` introduces ordering work.
- Custom `default` and `Decoder` hooks reintroduce Python execution into the parsing or serialization path.
- Stream buffer sizes affect the frequency of Python I/O calls.
- `ensure_ascii` changes the amount of escaping performed for non-ASCII content.

These costs are workload-specific.

### 13.2 Upstream benchmark evidence

The project's published benchmark tables normalize python-rapidjson's standard configuration to `1.00`.

The reported overall serialization factor for its `NM_NATIVE` configuration is approximately `0.80`, indicating 20% less elapsed time than its ordinary configuration for that particular benchmark aggregate.

The corresponding overall deserialization factor is approximately `0.91`.

These results support the conclusion that native numeric modes can provide measurable speed improvements on the benchmark's tested data.

They do not establish that the same improvement will occur with arbitrary application data.

The benchmark material also includes older versions of Python and competing JSON libraries. Therefore, it should not be interpreted as a current cross-library ranking for November 2026.

In particular, the published results show that some competing libraries are faster on many datasets. python-rapidjson's appeal is not that it wins every raw-throughput comparison, but that it combines a relatively fast native engine with unusually flexible conversion policies and schema validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



Benchmark reference: `https://python-rapidjson.readthedocs.io/en/latest/benchmarks.html`

### 13.3 Evaluating actual performance

For advanced workloads, useful benchmark dimensions include:

| Dimension             | What it reveals                                        |
| --------------------- | ------------------------------------------------------ |
| Numeric distribution  | Effects of `NM_NATIVE`, `NM_DECIMAL`, large integers   |
| Object depth          | Recursion and nested allocation costs                  |
| Mapping size          | Key conversion and sorting overhead                    |
| Unicode content       | Encoding, escaping, and conversion costs               |
| Custom type frequency | Python callback overhead                               |
| Input size            | Memory amplification during Python object construction |
| Stream behavior       | Buffer size and I/O method-call overhead               |
| Schema complexity     | Validation time and native document allocation         |

A serialization benchmark that measures only small dictionaries of primitive values does not provide much information about performance with deeply nested custom objects, decimal-heavy data, or schema validation.

## 14. Integration boundaries and combinations

The library's capabilities create several useful combinations, but they also define where external functionality remains necessary.

### 14.1 Strict JSON ingestion with structural controls

A strict ingestion workflow can combine:

- Parsing without comments or trailing commas.
- Disabling non-finite numbers.
- `NM_DECIMAL` for decimal numeric precision.
- A custom `Decoder` that rejects duplicate keys.
- Separate JSON Schema validation where the supported dialect is sufficient.

This can reduce the need for bespoke recursive transformations or an entirely custom JSON parser.

However, the validator and decoder are separate APIs. A validation failure and a custom reconstruction failure may have different representations and diagnostics.

Moreover, the validator's numeric semantics should not be assumed identical to the Python `Decimal` conversion path.

### 14.2 JSONC configuration ingestion

The relaxed parsing modes can be used to accept comments and trailing commas for human-authored configuration.

Once decoded, ordinary serialization can produce standard JSON without those extensions.

This is a simple normalization path:

```
parsed = rj.loads(    source_text,    parse_mode=(        rj.PM_COMMENTS |        rj.PM_TRAILING_COMMAS    ),    allow_nan=False,)normalized = rj.dumps(    parsed,    allow_nan=False,    sort_keys=True,)
```

The transformation is not lossless: comments, original whitespace, and possibly key ordering disappear.

It is suitable for semantic configuration normalization, not preserving the original authored document.

### 14.3 Typed interchange without universal object tagging

Native `Decimal`, datetime, and UUID support can eliminate repetitive callbacks where their JSON representations are contractually unambiguous.

But global string inference is not schema-aware.

An application requiring field-specific typing may obtain a more reliable boundary by combining plain JSON parsing with object reconstruction rules, typed models, or a separate schema-aware system.

The benefit is not simply stricter validation: it is avoiding the accidental conversion of ordinary strings that happen to resemble timestamps or UUIDs.

### 14.4 JSON Schema versus typed Python models

`Validator` checks serialized JSON against Draft 4 constraints.

It does not provide Python class generation, object construction from schemas, field-specific coercion, or general-purpose typed model validation.

These responsibilities remain distinct:

| Concern                                      | Appropriate capability                                 |
| -------------------------------------------- | ------------------------------------------------------ |
| Fast JSON encoding/decoding                  | python-rapidjson                                       |
| Native primitive and special-type conversion | python-rapidjson modes                                 |
| Custom Python object reconstruction          | `object_hook`, `Decoder` subclasses                    |
| Draft 4 validation of JSON text              | `rapidjson.Validator`                                  |
| Current JSON Schema dialects                 | An appropriate modern schema-validation implementation |
| Python model/schema generation               | A dedicated modeling or schema library                 |
| Token-level streaming from huge documents    | A dedicated event-based JSON parser                    |
| JSON Lines framing                           | Application or companion record-processing layer       |

### 14.5 Comparison with the standard library and adjacent parsers

| Capability                               | `json` standard library                   | python-rapidjson                          |
| ---------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| Native C++ parsing/generation            | Uses CPython acceleration where available | RapidJSON-based extension                 |
| `Decimal`-preserving parsing             | `parse_float=Decimal`                     | `NM_DECIMAL`                              |
| Arbitrary Python iterables               | Custom handling generally required        | Supported by default                      |
| Arbitrary mappings                       | Custom handling generally required        | Supported by default                      |
| Built-in ISO 8601 reconstruction         | No                                        | `DM_ISO8601`                              |
| Built-in UUID reconstruction             | No                                        | `UM_CANONICAL`, `UM_HEX`                  |
| Comments and trailing commas             | No                                        | Optional parsing modes                    |
| Object-pair access                       | `object_pairs_hook`                       | `Decoder.start_object()` returning a list |
| Native JSON Schema validation            | No                                        | Draft 4 `Validator`                       |
| Raw fragment embedding                   | No corresponding built-in abstraction     | `RawJSON`                                 |
| Full compatibility with `json` arguments | Baseline                                  | Deliberately not exact                    |

In particular, python-rapidjson is not a strict drop-in replacement for the standard library.

The API has different defaults and capabilities, and it does not implement every standard `json` option. For instance, formatting uses `write_mode` instead of adopting the standard library's complete `separators` interface.

The dedicated incompatibility documentation is therefore relevant when substituting it within existing library integrations.

Reference: `https://python-rapidjson.readthedocs.io/en/latest/quickstart.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation



## 15. Distribution, runtime introspection, and maintenance

### Packaging

Installation is through:

```
pip install python-rapidjson
```

The project publishes precompiled wheels for supported combinations of CPython and major operating systems.

Version 1.26 includes builds for Python 3.10 through 3.15 and broad platform coverage, including Windows ARM64 and RISC-V Linux configurations.

When a compatible wheel is unavailable, installation uses a source build requiring a suitable C++ toolchain.

The project also documents installation through Conda.

### Version introspection

The module exposes runtime version information, including:

```
import rapidjsonprint(rapidjson.__version__)print(rapidjson.__rapidjson_version__)print(rapidjson.__rapidjson_exact_version__)
```

These values help distinguish the Python binding release from the underlying native RapidJSON engine version.

This can matter when investigating parsing behavior or C++ engine features that differ between upstream revisions.

### Free-threaded CPython

The availability of `cp314t` and `cp315t` wheels is significant for compatibility with free-threaded CPython builds.

However, wheel availability alone does not establish that JSON parsing and generation can execute fully concurrently without the GIL.

The Python binding creates and manipulates Python objects and calls arbitrary Python hooks. Those operations have runtime and synchronization implications even when native parsing code is involved.

Inspection of the tagged source does show a native GIL-release region around parts of schema validation, but that is not a basis for assuming GIL-free parallelism across all module operations.

Parallel throughput and the behavior of shared encoder/decoder instances should therefore be assessed separately from basic compatibility with a free-threaded interpreter.

### Maintenance profile

python-rapidjson is a mature library rather than an experimental Python binding.

The 2026 releases show continuing maintenance focused on platform support, correctness, C API error handling, and parser robustness.

The older public documentation remains useful for the stable API surface, but the tagged source and release notes are preferable for verifying the most recent behavior.

Primary release reference: `https://pypi.org/project/python-rapidjson/1.26/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 16. Capability synthesis

python-rapidjson occupies an interesting position among Python's JSON libraries.

It provides more than raw parsing and serialization throughput, but it is not a general-purpose structured-data framework.

Its most consequential capabilities are the ones that allow several common layers of application code to be simplified or removed:

| Capability                          | Potentially eliminates                         | Principal qualification                        |
| ----------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `NM_DECIMAL`                        | Custom exact-decimal parsing                   | Decimal arithmetic has additional costs        |
| Datetime and UUID modes             | Repetitive native-type conversion hooks        | Global inference can change plain strings      |
| Generic iterable/mapping support    | Container-conversion boilerplate               | Container-specific semantics may be lost       |
| `Decoder` structural hooks          | Separate recursive reconstruction passes       | Python callback overhead                       |
| Pair-preserving object construction | Special-purpose duplicate-key parsing          | Requires class-based decoding                  |
| Native JSON Schema validator        | Separate Draft 4 validation engine             | Later schema dialects unsupported              |
| Streaming output                    | Intermediate full JSON strings and input lists | Does not provide streaming decoded records     |
| `RawJSON`                           | Decoding and re-encoding trusted fragments     | Fragment validation is caller's responsibility |
| Relaxed parsing                     | A separate JSONC normalization parser          | Comments and original formatting are discarded |

The broader architectural opportunity is to combine native conversion policies, object construction hooks, and streaming generation into a single serialization boundary.

The corresponding limitation is that these capabilities operate at different semantic levels. JSON Schema validation does not create typed Python models, typed reconstruction does not provide schema validation, and streaming input does not expose a Python event parser.

Recognizing those boundaries is essential to using the library's capabilities accurately.

## 17. Primary-source reference map

The following sources are the most useful starting points for investigating specific behavior in greater detail.

| Source                                          | Direct URL                                                                                |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Project repository                              | `https://github.com/python-rapidjson/python-rapidjson`                                    |
| Version 1.26 release and distribution files     | `https://pypi.org/project/python-rapidjson/1.26/`                                         |
| Version 1.26 native implementation              | `https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/rapidjson.cpp` |
| API and mode constants                          | `https://python-rapidjson.readthedocs.io/en/latest/api.html`                              |
| Serialization options                           | `https://python-rapidjson.readthedocs.io/en/latest/dumps.html`                            |
| Deserialization options                         | `https://python-rapidjson.readthedocs.io/en/latest/loads.html`                            |
| Encoder subclassing                             | `https://python-rapidjson.readthedocs.io/en/latest/encoder.html`                          |
| Decoder structural hooks                        | `https://python-rapidjson.readthedocs.io/en/latest/decoder.html`                          |
| Stream serialization                            | `https://python-rapidjson.readthedocs.io/en/latest/dump.html`                             |
| Stream deserialization                          | `https://python-rapidjson.readthedocs.io/en/latest/load.html`                             |
| Native schema validation                        | `https://python-rapidjson.readthedocs.io/en/latest/validator.html`                        |
| Raw JSON fragments                              | `https://python-rapidjson.readthedocs.io/en/latest/rawjson.html`                          |
| Underlying RapidJSON schema engine              | `https://rapidjson.org/md_doc_schema.html`                                                |
| Published benchmark methodology and results     | `https://python-rapidjson.readthedocs.io/en/latest/benchmarks.html`                       |
| Installation and standard-library compatibility | `https://python-rapidjson.readthedocs.io/en/latest/quickstart.html`                       |

Overall assessment: python-rapidjson's distinctive value is the depth of its serialization semantics relative to its compact API. Exact decimal conversion, flexible Python container handling, pre-dictionary structural hooks, native Draft 4 validation, raw-fragment composition, and buffered stream generation make it particularly capable for JSON processing boundaries that need more control than a conventional `dumps()`/`loads()` implementation provides.

# python-rapidjson — Technical Capability Addendum

Research date: November 20, 2026 | Target release: 1.26 | Python 3.10+ | Supplement to the comprehensive library overview

## Scope and orientation

This addendum expands the original python-rapidjson overview in areas where additional research revealed important implementation mechanisms, behavioral distinctions, or operational constraints.

The most significant additions concern the library's internal parsing architecture, automatic object-key deduplication, recursion safeguards, Python-specific numeric formatting, precise stream contracts, custom decoder behavior, and build-time integration facilities.

The analysis distinguishes documented public APIs from behaviors verified through the tagged version 1.26 C++ implementation. Source-level implementation details are useful for understanding capabilities and tradeoffs, but are not necessarily permanent compatibility guarantees.

The current stable release is python-rapidjson 1.26, published November 1, 2026. Some online API documentation remains labeled 1.17 and does not describe every subsequent maintenance change. The version 1.26 source and PyPI release notes are therefore used for current behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Native parsing architecture and object construction

### 1.1 Direct SAX-to-Python decoding

The ordinary decoding path uses RapidJSON's event-driven `Reader`, but this does not mean the binding exposes a public SAX API.

Internally, python-rapidjson implements a custom C++ `PyHandler` that receives parsing events and directly constructs Python values.

The relevant architecture is:

JSON input

String, UTF-8 bytes, or readable stream

RapidJSON Reader

Lexical parsing and structural events

C++ PyHandler

Numeric conversion, key reuse, container construction, native type recognition, Python callbacks

Python object graph

Nested values returned to the caller

The `PyHandler` implements RapidJSON parsing callbacks for JSON objects, arrays, strings, numeric values, booleans, and null.

Its primary responsibilities include:

- Maintaining a stack of partially constructed Python containers.
- Creating Python dictionaries or alternative containers selected by decoder hooks.
- Converting numeric tokens into Python integers, floating-point values, or decimals.
- Recognizing ISO 8601 and UUID string representations when configured.
- Reusing Python objects representing repeated JSON member names.
- Invoking custom hooks as completed values become available.
- Inserting completed values into their enclosing containers.

The implementation does not construct an entire RapidJSON C++ DOM and subsequently perform a separate recursive conversion into Python.

This avoids allocating a second complete structural representation of the input during ordinary decoding.

However, direct string and byte-buffer inputs are copied into mutable memory so RapidJSON can use its in-situ parsing mode. This is not zero-copy decoding, and Python containers and objects still require allocation.

The optimization is therefore best understood as avoiding an intermediate C++ document tree, rather than avoiding all input copies or Python object allocations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 1.2 Schema validation uses a different native execution path

`rapidjson.Validator` follows a different architecture:

1. A JSON Schema is parsed into a RapidJSON `Document`.
2. The constructor compiles that document into a native `SchemaDocument`.
3. Each JSON document submitted for validation is independently parsed into a RapidJSON `Document`.
4. The document is traversed with a `SchemaValidator`.
5. Successful validation returns `None`; failures produce structured validation errors.

This distinction has several implications.

Schema compilation is reusable. A `Validator` instance retains the native compiled schema, avoiding repeated schema parsing for every validation request.

Validation does not require constructing Python dictionaries and lists. It operates on a native document representation.

Validation does require constructing a native document. Although the underlying RapidJSON C++ library also supports streaming SAX validation, the Python binding's `Validator` uses the DOM-based path.

Validation and decoding are separate operations. Calling `Validator` does not return the decoded Python document, and calling `loads()` does not automatically perform schema validation.

This matters when deciding where validation belongs in a JSON ingestion boundary. Schema compilation can be amortized across documents, but document parsing may be repeated if validation and Python reconstruction are both required.

The native validation path releases the Python GIL around document parsing and schema traversal. Ordinary Python object reconstruction cannot be assumed to have the same concurrency behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source:

`https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/rapidjson.cpp`

## 2. Automatic deduplication of JSON object keys

### 2.1 Mechanism

Since version 1.1, python-rapidjson has automatically reused Python string objects for repeated JSON member names within a decoding operation.

This is a particularly valuable optimization for large datasets consisting of many similarly structured objects.

Consider:

```
[
  {"record_id": 101, "status": "active", "value": 3.5},
  {"record_id": 102, "status": "active", "value": 7.2},
  {"record_id": 103, "status": "inactive", "value": 4.1}
]
```

Each dictionary requires keys representing `"record_id"`, `"status"`, and `"value"`.

Without key reuse, decoding may allocate separate Python string objects for every occurrence.

python-rapidjson's `PyHandler` maintains an internal dictionary named `sharedKeys`.

When it encounters an object member name, it constructs a Python Unicode value and uses `PyDict_SetDefault()` to retrieve a previously encountered equal string if one exists.

The canonical string object is then inserted into the destination dictionary or key-value pair.

Conceptually:

```
# Simplified illustration, not the actual C++ implementationshared_keys = {}def intern_document_key(key):    return shared_keys.setdefault(key, key)
```

For repeated keys, the decoder reuses the original string object's identity, not merely its value.

The mechanism works without an explicit mode flag and is independent of whether the destination object is an ordinary dictionary or the list-of-pairs representation supported by `Decoder.start_object()`.

The project's changelog records this as a decoder memory optimization introduced in version 1.1. The tagged 1.26 implementation confirms that it remains part of the object-construction path.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



### 2.2 Memory and computational implications

The optimization reduces the number of distinct Python string objects retained for repeated member names.

For a document containing \\(N\\) objects that share \\(K\\) field names, the potential savings come from replacing up to \\(N \times K\\) separately allocated key strings with approximately \\(K\\) canonical key strings.

This does not eliminate the keys' dictionary entries or their references. Every dictionary still needs its own hash-table structure and key-value associations.

It also does not eliminate all allocation work: the implementation initially creates a string for each encountered name and consults the reuse dictionary, even when the name has appeared previously.

The primary reduction is in retained duplicate key objects, not necessarily all temporary allocation or hashing work.

The internal reuse dictionary introduces its own memory and lookup costs, so benefits depend on the repetition and length of member names.

The optimization is particularly relevant to large arrays of relatively narrow records, where structural metadata may otherwise constitute a meaningful fraction of Python's in-memory representation.

No universal memory-reduction percentage can be inferred without measurements on a representative workload.

### 2.3 Scope and lifetime

The `sharedKeys` table belongs to an individual `PyHandler`, which is constructed for a decoding operation.

Consequently:

- Keys can be shared across objects in the same decoded document.
- Reusing a `Decoder` instance for separate calls does not establish a persistent cross-document key pool.
- The temporary lookup dictionary is destroyed when the handler is destroyed.
- Key strings remain alive through references from the resulting Python containers.
- The mechanism is unrelated to Python's global string-interning API.

The same canonical string may appear as keys in multiple decoded dictionaries even though those dictionaries remain independent mutable objects.

Custom decoding hooks that reconstruct keys themselves can change this identity-sharing property.

### 2.4 Architectural significance

Key deduplication improves the memory characteristics of conventional Python object materialization without requiring specialized record containers, an Arrow representation, or a separate interning pass.

It does not provide the more aggressive memory layout of columnar arrays or typed records, but it addresses a common source of overhead in dictionary-heavy JSON.

This is an important native capability to recognize when comparing the costs of alternative JSON ingestion strategies.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/changes.html`

`https://github.com/python-rapidjson/python-rapidjson/blob/v1.26/rapidjson.cpp`

## 3. Recursion-depth enforcement and cyclic data

### 3.1 Decoding limits

Starting with version 1.15, python-rapidjson enforces a nesting limit during JSON parsing based on Python's runtime recursion limit.

The native handler initializes its counter from `Py_GetRecursionLimit()`.

Each `StartObject()` or `StartArray()` event consumes one level. The matching end event restores that level.

When the available depth is exhausted, the handler raises `RecursionError` rather than continuing to construct an arbitrarily deep object graph.

This protects against one class of malicious or pathological inputs consisting of extremely deeply nested JSON containers.

The change was introduced in response to CVE-2024-27454.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



### 3.2 Encoding limits

Serialization separately uses Python's recursive-call checking mechanisms when traversing nested values.

The implementation invokes `Py_EnterRecursiveCall()` and `Py_LeaveRecursiveCall()` around recursive serialization of lists, tuples, dictionaries, generic iterables, and values returned by custom `default` functions.

The encoding and decoding implementations therefore share a relationship with `sys.getrecursionlimit()`, but they do not use identical counting logic.

For example, the decoder counts nested JSON containers directly, whereas encoder recursion checks also operate around Python-level recursive traversal.

It is consequently inaccurate to promise that a JSON document with a particular nesting depth will always be accepted for both encoding and decoding merely because the interpreter's recursion limit exceeds that number.

The exact boundary can depend on the operation and surrounding Python call stack.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.3 No independent per-call depth parameter

Earlier releases exposed `max_recursion_depth` for serialization.

That option was removed in version 0.3.0 in favor of Python's general recursion-limit mechanism.

The public 1.26 API does not offer an independent `max_depth` argument for `loads()`, `load()`, or `Decoder`.

Changing `sys.setrecursionlimit()` alters interpreter-wide behavior and is not equivalent to specifying a per-document resource budget.

An application that must enforce its own maximum document depth independently of interpreter settings needs another mechanism.

### 3.4 Cyclic Python graphs

JSON arrays and objects represent trees, not arbitrary cyclic object graphs.

The serializer does not expose a standard-library-style `check_circular` option, nor does it natively encode reference identities.

For example:

```
import rapidjsonvalue = []value.append(value)rapidjson.dumps(value)# Eventually raises RecursionError
```

The recursion guard prevents indefinite traversal but does not provide graph serialization.

The same issue can arise when a custom `default()` callback repeatedly returns a value that eventually refers back to an ancestor.

This distinguishes two requirements that are sometimes conflated:

- Preventing unbounded recursive traversal, which the library addresses.
- Preserving object identity and circular references, which requires a separate representation or conversion scheme.

### 3.5 Security implications

Recursion protection is one resource safeguard, not a comprehensive resource-control system.

It does not itself constrain:

- Total JSON input bytes.
- Total dictionary members or array elements.
- Number of distinct object keys.
- Memory consumed by constructed Python values.
- Time spent inside custom callbacks.
- Overall schema-validation cost.

These limits must be addressed independently where workloads require strict resource isolation.

Source:

`https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/rapidjson.cpp`

## 4. Numeric representation, defaults, and subclass behavior

### 4.1 Python-compatible number formatting

A consequential implementation detail is that python-rapidjson does not always use RapidJSON's native integer and floating-point formatting routines.

For finite Python floating-point values, the serializer calls the base Python `float` type's representation method and writes the result as a JSON numeric token.

This behavior was introduced because RapidJSON's native `dtoa()` conversion previously produced unexpected representations for certain floating-point values.

The relevant operation in version 1.26 is effectively:

```
PyObject* dr = PyFloat_Type.tp_repr(object);
```

The resulting string is passed to RapidJSON's `RawValue()` method with the numeric JSON type.

For non-native integer serialization, the implementation takes a similar approach using:

```
PyObject* intStrObj = PyLong_Type.tp_repr(object);
```

This allows arbitrary-precision Python integers to be emitted as numeric literals without narrowing them to fixed-width C++ integers.

These details explain why python-rapidjson's numeric output is not necessarily identical to what an application using RapidJSON's C++ `Writer::Double()` would produce.

The motivation is compatibility with Python's numeric semantics, especially floating-point string representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 4.2 Handling subclasses of numeric types

The direct use of the base numeric type's representation also affects subclasses.

Python allows subclasses of `float` and `int` to override `__repr__()`.

A serializer that indiscriminately calls `repr(value)` could accidentally serialize a custom presentation rather than the underlying numeric value.

python-rapidjson explicitly avoids this for recognized numeric subclasses.

For example, consider:

```
import rapidjsonclass CustomFloat(float):    def __repr__(self):        return "custom-value"value = CustomFloat(1.25)
```

The intended JSON representation remains the numeric value:

```
rapidjson.dumps(value)# '1.25'
```

The overridden `__repr__()` does not replace the numeric serialization behavior.

The same consideration applies to `int` subclasses, including `enum.IntEnum`.

This preserves numeric interchange semantics while allowing application classes to implement custom debugging or presentation representations.

Version 1.19 specifically corrected handling of `float` subclasses with custom `__repr__()` methods.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+2



### 4.3 `Decimal` serialization follows a separate path

When `NM_DECIMAL` is enabled, Python `Decimal` values are serialized using their string representation as numeric JSON tokens.

This preserves decimal digits without first narrowing values to binary floating-point numbers.

However, it is important to distinguish three forms of preservation:

| Property                                    | Behavior                                                     |
| ------------------------------------------- | ------------------------------------------------------------ |
| Decimal numeric value                       | Preserved by direct decimal serialization                    |
| Decimal representation                      | Based on the Python `Decimal` string representation          |
| Original source JSON lexical representation | Not guaranteed to survive arbitrary decoding and re-encoding |

For example, a `Decimal` constructed from `"1.200"` can be serialized with those decimal places.

However, ordinary JSON has no separate type marker identifying a decimal value. A downstream consumer may interpret the token as an IEEE 754 floating-point value or normalize its formatting.

Thus, python-rapidjson can preserve decimal values within a controlled Python serialization/deserialization contract, but it cannot require arbitrary JSON consumers to preserve that distinction.

Another subtlety is that integer JSON literals and floating-point literals are not treated identically by `NM_DECIMAL`: integer tokens ordinarily become Python `int` values.

For systems requiring all JSON numbers to become `Decimal` objects, the documented `NM_DECIMAL` mode alone is insufficient.

### 4.4 Distinguishing omitted number modes from explicit `None`

The default numeric configuration has a subtle implementation-level distinction.

The binding initializes its internal number mode to `NM_NAN` when no `number_mode` argument is supplied.

However, explicitly passing `number_mode=None` causes the argument parser to select `NM_NONE`.

Consequently, these calls are not equivalent:

```
import rapidjson as rj# Non-finite numbers enabled by defaultrj.loads("NaN")# Explicit None selects NM_NONErj.loads("NaN", number_mode=None)# Also disables the extensionrj.loads("NaN", number_mode=rj.NM_NONE)
```

The first is accepted; the latter two reject the non-finite token.

The distinction also exists in class construction because `Encoder` and `Decoder` initialize their internal number modes to `NM_NAN`, with explicit `None` selecting `NM_NONE`.

This is relevant when configuration dictionaries are assembled dynamically. Passing a parameter explicitly with value `None` is not always semantically equivalent to omitting it.

The `allow_nan` compatibility argument adds another layer. When explicitly supplied, it adds or removes the `NM_NAN` bit from the selected number mode.

The resulting precedence is:

1. Start with the internal default mode.
2. Apply an explicitly supplied `number_mode`, including `None`.
3. If supplied, apply the `allow_nan` override.

`Encoder` and `Decoder` constructors do not expose the same `allow_nan` compatibility argument as the module-level functions, so their non-finite policy is controlled through `number_mode`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



### 4.5 Version-specific numeric corrections

Version 1.26 includes several improvements relevant to numeric and temporal serialization:

- Corrected combinations of `parse_mode` with numeric modes that exclude native conversion and non-finite extensions.
- Consistent `number_mode` argument validation across additional decoding interfaces.
- Normalization of signed, signaling, and payload-bearing `Decimal` NaN values to the supported `NaN` token when non-finite serialization is enabled.
- Preservation of the numeric locale when serializing Unix timestamps.

These are important correctness refinements. They do not introduce a new numeric API, but they reduce the risk of encountering behavior that differs between otherwise similar entry points.

Source:

`https://pypi.org/project/python-rapidjson/1.26/`

## 5. Custom decoder semantics and reusable configurations

### 5.1 `Decoder.string()` operates on values, not member names

The custom string conversion hook has a narrower scope than an unrestricted string-token callback.

RapidJSON invokes separate events for JSON string values and JSON object member names.

In the Python binding, member names follow the native handler's `Key()` method, while string values follow its `String()` method.

`Decoder.string()` is called through the latter path.

For example:

```
import rapidjson as rjclass NormalizeValues(rj.Decoder):    def string(self, value):        return value.strip().lower()decoder = NormalizeValues()decoder('{"Status": " ACTIVE "}')# {'Status': 'active'}
```

The value is normalized, but the key remains `"Status"`.

This distinction is important when constructing custom normalized representations. The string hook is not a general object-key normalization mechanism.

Member names instead require transformation at the object-construction or object-completion level, such as through `end_object()`.

### 5.2 Precedence of native type recognition

The binding's string-processing path is:

1. Attempt ISO 8601 recognition when the datetime mode is enabled.
2. Attempt UUID recognition when the UUID mode is enabled.
3. Construct a Python string.
4. Invoke `Decoder.string()` if implemented.
5. Insert the result into its enclosing container.

The native recognition paths can return early.

Therefore, the string hook does not see a value that has already been recognized as a datetime or UUID.

This is a meaningful extension limitation. A custom string converter cannot reliably intercept all date-like input strings if native datetime recognition is also enabled.

For field-specific conversion, it may be more expressive to leave native string recognition disabled and perform conversions after the relevant object has been assembled.

The precise ordering is established by `PyHandler::String()` in the tagged implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 5.3 Container hooks and the parsing stack

The parser constructs nested containers incrementally.

A `start_object()` implementation can return a custom mapping instance or a list. The returned container becomes the target for subsequently decoded member values.

When object parsing completes, `end_object()` receives that container and may replace it with any Python value.

Likewise, `end_array()` receives the completed array and may return a replacement.

This means the hooks do not merely mutate a completed root document. They participate in assembling the nested object graph.

For example, replacing every completed array with a tuple can produce nested tuples directly during parsing, without a separate traversal of the completed document.

There is a performance tradeoff.

The parser has a specialized path for exact built-in dictionaries. When the destination is a custom mapping, it uses more general Python item-assignment operations.

The implementation explicitly identifies exact-dictionary insertion as a faster path.

Consequently, using a custom mapping during decoding can provide valuable semantics but may sacrifice some of the optimized built-in container path.

A list-of-pairs representation can preserve duplicate member names and ordering, but it also creates tuples and appends them to a list rather than using ordinary dictionary insertion.

These are different representations with different allocation patterns.

Source:

`https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/rapidjson.cpp`

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2

### 5.4 Encoder and Decoder configurations are read-only

The class-based APIs expose their configured modes as attributes.

For example:

```
encoder = rj.Encoder(    number_mode=rj.NM_DECIMAL,    ensure_ascii=False,    sort_keys=True,)encoder.number_modeencoder.ensure_asciiencoder.mapping_modeencoder.indent_charencoder.indent_count
```

The corresponding attributes are defined as read-only C extension members.

`Decoder` similarly exposes read-only properties for its numeric, datetime, UUID, and parsing modes.

This makes class instances useful as reusable, inspectable policy objects.

It does not mean that an existing instance can have all of its conversion behavior dynamically reconfigured through attribute assignment.

The intended mechanism is to construct appropriately configured instances, while subclass methods provide behavior-specific extensibility.

This distinction becomes useful when JSON conversion policies are represented as reusable application components.

Sources:

`https://python-rapidjson.readthedocs.io/en/latest/encoder.html`

`https://python-rapidjson.readthedocs.io/en/latest/decoder.html`

## 6. Stream integration: exact contracts and boundaries

### 6.1 Valid `chunk_size` range

The 1.26 implementation validates stream buffer sizes against:

\\[ 4 \leq \texttt{chunk\\\_size} \leq \texttt{UINT\\\_MAX} \\]

The default is 65,536.

Values outside this range are rejected. Noninteger values also produce an argument-validation error.

This applies to the streaming functions and class interfaces when they consume or write streams.

The minimum size of four bytes is noteworthy because it accommodates the maximum length of a single UTF-8 code point.

`chunk_size` controls the size of requested or buffered I/O operations; it is not a limit on total decoded document memory.

### 6.2 Input stream contract

The native read adapter uses the equivalent of:

```
chunk = stream.read(chunk_size)
```

It accepts `bytes` and `str` return values.

For text, the adapter obtains a UTF-8 representation before supplying the data to RapidJSON.

An empty result is interpreted as end-of-file.

For ordinary synchronous file-like objects, this is conventional behavior. For nonblocking streams, however, an empty result may mean that no data is currently available rather than that the stream has permanently ended.

The adapter does not expose a mechanism for representing that distinction.

This makes `load()` unsuitable as a general asynchronous or nonblocking parser without a separate stream abstraction that provides the expected blocking semantics.

One further subtlety: for text streams, the requested chunk size is expressed through the Python `read()` call, while the resulting UTF-8 byte sequence can be larger than the number of characters read.

The parser's internal offsets consequently relate to its encoded input representation, not necessarily character positions in the original Python text.

### 6.3 Output stream contract

The native writer classifies output streams using the presence of an `encoding` attribute:

- A stream without `encoding` is treated as binary and receives `bytes`.
- A stream with `encoding` is treated as text-oriented and receives `str`.

This is structural detection rather than a full check of the Python `io` class hierarchy.

For custom stream wrappers, merely exposing an `encoding` attribute can change the type of data passed to `write()`.

The writer also handles UTF-8 code-point boundaries when flushing its text buffer.

If the output buffer ends partway through a multibyte character, the implementation retains the incomplete bytes rather than immediately attempting to turn them into a Python Unicode string.

This prevents invalid UTF-8 fragments from being passed separately to a text stream.

### 6.4 Partial writes are not automatically retried

A consequential detail in the implementation is that the writer calls the stream's `write()` method but does not inspect the number of bytes or characters reported as written.

It checks whether `write()` raised an error, but it does not implement a retry loop for short writes.

For an ordinary buffered file object, this normally aligns with the expected contract.

For a custom stream or low-level I/O wrapper that can successfully write only part of the supplied buffer, the JSON output could be truncated without the serializer independently retrying the remainder.

Thus, the stream writer expects an adapter whose `write()` method consumes the supplied data completely or reports failure.

A generic socket send operation, for example, does not necessarily satisfy this contract directly.

This is particularly relevant when connecting the serializer to custom transports or output pipelines.

### 6.5 Stream errors and parser diagnostics

The input adapter preserves Python errors raised by stream operations.

When parsing subsequently fails, the decoder attempts to retain the underlying exception. For certain string-valued exceptions, it adds a parse offset to the resulting message.

This means not every failure encountered during `load()` is necessarily a `JSONDecodeError`.

An exception from a custom stream may propagate using the stream's original exception type.

That distinction is valuable when separating malformed JSON failures from I/O or callback failures.

The behavior is implemented in `do_decode()` and the Python stream adapter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



Primary source:

`https://github.com/python-rapidjson/python-rapidjson/blob/v1.26/rapidjson.cpp`

## 7. RawJSON storage and input restrictions

The `RawJSON` class accepts a Python Unicode string and stores it as its underlying value.

The constructor's C argument parser uses the Unicode-only format.

Consequently, these representations are not interchangeable:

```
rj.RawJSON('{"a": 1}')    # Supportedrj.RawJSON(b'{"a": 1}')   # TypeError
```

The input is not an arbitrary byte buffer.

The object's `value` attribute is read-only and retains the provided string.

This means `RawJSON` is not a writable native buffer abstraction or a mechanism for passing a `memoryview` directly into RapidJSON without representation conversion.

Its central function remains bypassing normal serialization of a trusted, preserialized JSON fragment.

A useful combination is to validate a candidate fragment before constructing or emitting a compound document:

```
fragment = '{"a": 1}'# Validates syntax and any configured schema constraintsvalidator(fragment)wrapped = rj.RawJSON(fragment)result = rj.dumps({    "metadata": {"source": "external"},    "payload": wrapped,})
```

This is illustrative, not a claim that `RawJSON` performs validation.

The validation step is explicitly separate.

It is also important that the embedded fragment is not transformed by the parent writer's numeric, indentation, or Unicode policies.

The parent document can therefore contain a preserialized fragment with different lexical formatting characteristics.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-rapidjson.readthedocs.io\&sz=32)

python-rapidjson 1.17 documentation+1



`https://python-rapidjson.readthedocs.io/en/latest/rawjson.html`

## 8. Exception semantics and error integration

The native extension creates `rapidjson.JSONDecodeError` and `rapidjson.ValidationError` as distinct exceptions derived from `ValueError`.

They are not aliases of Python's standard-library `json.JSONDecodeError`.

That matters because code written against the standard library may expect attributes such as `.lineno`, `.colno`, `.pos`, or `.doc`.

The python-rapidjson implementation does not establish the same exception interface.

A normal parse failure is generally reported with an offset in the message:

```
Parse error at offset N: ...
```

The appropriate exception handler is therefore:

```
try:    obj = rj.loads(payload)except rj.JSONDecodeError as exc:    message = str(exc)
```

rather than assuming the availability of the standard-library exception's location attributes.

Schema validation is different.

`ValidationError.args` contains three components:

```
(keyword, schema_pointer, document_pointer)
```

These are structured diagnostics identifying the failed schema keyword and the relevant schema/document locations.

Malformed JSON supplied to `Validator` raises `JSONDecodeError`, with the comparatively general message `"Invalid JSON"`.

There are therefore multiple independent failure sources at a JSON boundary:

| Failure source                        | Diagnostic type                                                   |
| ------------------------------------- | ----------------------------------------------------------------- |
| Syntax parsing                        | `JSONDecodeError`                                                 |
| Schema validation                     | `ValidationError`                                                 |
| Custom conversion hook                | Exception raised by the hook                                      |
| Stream read/write operation           | Exception from the stream, possibly with additional parse context |
| Recursion-depth exhaustion            | `RecursionError`                                                  |
| Unsupported encoding or argument type | Relevant Python argument/conversion exception                     |

The last three categories should not be indiscriminately normalized to `JSONDecodeError`, because they represent failures other than malformed JSON syntax.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



`https://python-rapidjson.readthedocs.io/en/latest/validator.html`

## 9. Build customization, version identity, and typing support

### 9.1 Selecting RapidJSON headers at build time

The Python extension normally compiles against the RapidJSON headers bundled with the project's source distribution.

Its `setup.py` also recognizes a custom build argument:

```
--rj-include-dir=<path>
```

This overrides the default RapidJSON include directory.

The extension is therefore not irrevocably tied to the exact bundled header revision when built from source.

This facility enables controlled experiments with alternative RapidJSON headers, for example when evaluating bug fixes or changes in the native engine.

However, it is a compile-time customization, not a runtime engine-switching mechanism.

It also does not guarantee compatibility with arbitrary RapidJSON revisions.

The underlying C++ API must remain compatible with the wrapper's implementation, and any changed behavior must be independently verified.

The source build uses C++11.

### 9.2 Runtime version reporting

The module exposes three related values:

```
import rapidjsonrapidjson.__version__rapidjson.__rapidjson_version__rapidjson.__rapidjson_exact_version__
```

They have distinct meanings:

| Attribute                     | Meaning                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `__version__`                 | Version of the Python binding                                          |
| `__rapidjson_version__`       | RapidJSON engine version reported by the native headers                |
| `__rapidjson_exact_version__` | More precise build-time RapidJSON revision information, when available |

The exact revision can be unavailable.

In that case, the extension returns the string `"not available"` rather than guaranteeing a Git-derived revision identifier.

The distinction becomes particularly relevant when building against custom RapidJSON headers.

The Python package version alone does not necessarily establish the exact native engine revision used in a custom source build.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 9.3 PEP 484 typing stubs

Version 1.18 introduced Python typing stubs.

The build configuration includes them as a separate stub package:

```
package_dir = {    "rapidjson-stubs": "typings/rapidjson"}packages = ["rapidjson-stubs"]package_data = {    "rapidjson-stubs": ["*.pyi"]}
```

This is significant because the runtime library is a native extension, which does not expose ordinary annotated Python implementations for static-analysis tools.

The stubs describe its callable interfaces and allow compatible type checkers to understand the package without inspecting the C++ implementation.

Subsequent releases corrected annotations for:

- `loads()`
- `Decoder.__call__()`
- The optional stream argument of `Encoder.__call__()`

Static typing remains an interface-level approximation.

For example, a general `loads()` annotation cannot fully express the return-type changes produced by arbitrary custom decoder subclasses or the interaction between numeric modes and JSON content.

Likewise, a statically typed `Decoder` cannot infer the specific Python class returned by an arbitrary `end_object()` implementation merely from the constructor's mode flags.

The practical value of the stubs is improved discoverability, autocomplete, and argument checking—not automatic schema-aware type reconstruction.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



`https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/setup.py`

`https://pypi.org/project/python-rapidjson/1.26/`

## 10. Boundary between the Python binding and the C++ engine

The previous gap analysis identified several additional RapidJSON capabilities that could be mistaken for python-rapidjson functionality.

The most important distinction is that using a native capability internally is not equivalent to exposing it as a programmable Python interface.

| C++ engine capability                 | Relationship to python-rapidjson 1.26                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| SAX reader and handler events         | Used internally during Python decoding; no public SAX event iterator                                    |
| Native DOM manipulation               | Used internally for validation; no public Python DOM node API                                           |
| In-situ parsing                       | Used with a mutable input copy for ordinary buffer decoding; no caller-owned zero-copy buffer interface |
| Native memory allocator customization | No corresponding public configuration                                                                   |
| SAX JSON Schema validation            | Available in C++ RapidJSON; not exposed through the Python `Validator` API                              |
| Remote schema provider                | Native C++ integration point; not exposed as a Python callback                                          |
| Low-level JSON Pointer operations     | Not exported as standalone Python functions                                                             |
| Async/event-driven stream processing  | Not provided by the Python binding                                                                      |

Some of these engine capabilities could be accessed through a separate extension or another binding, but that would constitute an additional integration layer rather than native python-rapidjson functionality.

The C++ library's broad API surface should not be used to infer Python capabilities that the wrapper does not implement.

Underlying engine reference:

`https://rapidjson.org/md_doc_schema.html`

Python binding source:

`https://github.com/python-rapidjson/python-rapidjson/blob/v1.26/rapidjson.cpp`

## 11. Consolidated architectural implications

The additional research reveals several properties that are easy to overlook when treating python-rapidjson as a conventional JSON serializer.

Its decoding implementation is architecturally optimized for direct Python reconstruction. It uses SAX parsing without first allocating a native DOM and automatically reuses member-name strings within a document. Together, these mechanisms can improve memory behavior for repetitive JSON structures without changing the ordinary Python-facing API.

The decoder's extension points operate during structural reconstruction, not exclusively after parsing. This gives it substantial expressive power, but custom mappings, pair-preserving representations, and per-value callbacks change the allocation and execution profile.

Numeric serialization intentionally incorporates Python's own representation semantics. This distinguishes the binding from a direct wrapper around the C++ writer's native numeric formatting and helps explain differences between default and native numeric modes.

Streaming is a buffered synchronous interface with specific Python I/O contracts. It can avoid constructing complete serialized output strings, but its read and write adapters are not asynchronous, do not provide record-at-a-time decoding, and assume conventional full-write behavior.

Schema validation and Python decoding have materially different execution paths. The former uses native DOM objects and releases the GIL around important native operations; the latter constructs Python objects directly and may execute Python callbacks.

Runtime protection is partial but meaningful. Recursion checks address excessively deep structures and cyclic serialization, while other limits—total input size, materialized object memory, and application callback behavior—remain outside those safeguards.

Finally, the package exposes useful build and static-analysis integration mechanisms through selectable RapidJSON headers, native version reporting, and distributed typing stubs. These facilities make the compiled binding more inspectable and configurable than its small high-level API might suggest.

The additions do not change the original overview's fundamental characterization of python-rapidjson. They deepen the explanation of how its native implementation, Python object model, and configurable policies interact—and where their guarantees stop.

## Primary-source references

These references provide the most direct evidence for the additions above.

| Source                                | Direct URL                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------ |
| Version 1.26 C++ implementation       | `https://github.com/python-rapidjson/python-rapidjson/blob/v1.26/rapidjson.cpp`      |
| Version 1.26 build configuration      | `https://raw.githubusercontent.com/python-rapidjson/python-rapidjson/v1.26/setup.py` |
| Version 1.26 release notes            | `https://pypi.org/project/python-rapidjson/1.26/`                                    |
| Historical implementation changes     | `https://python-rapidjson.readthedocs.io/en/latest/changes.html`                     |
| Decoder hooks and semantics           | `https://python-rapidjson.readthedocs.io/en/latest/decoder.html`                     |
| Encoder interface and subclassing     | `https://python-rapidjson.readthedocs.io/en/latest/encoder.html`                     |
| Native schema validation interface    | `https://python-rapidjson.readthedocs.io/en/latest/validator.html`                   |
| RawJSON representation                | `https://python-rapidjson.readthedocs.io/en/latest/rawjson.html`                     |
| Underlying C++ JSON Schema mechanisms | `https://rapidjson.org/md_doc_schema.html`                                           |

The code examples in this addendum are illustrative and have been checked against the documented interfaces and tagged source, but were not executed as a separate runtime test suite.