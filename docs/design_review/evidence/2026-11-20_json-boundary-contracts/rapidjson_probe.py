"""python-rapidjson 1.25 contracts for the JSON-boundary functional review (questions 1-7).

Synthetic values only; no project import. Run from the repository root:

    uv run python -I docs/design_review/evidence/2026-11-20_json-boundary-contracts/rapidjson_probe.py

Each section prints what the installed module does. Interpretation lives in the review.
"""

import collections
import dataclasses
import enum
import io
import json
import pathlib
import sys
import types
import uuid
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal

import rapidjson

NM = rapidjson.NM_DECIMAL


def show(fn):
    try:
        return "ok   " + repr(fn())
    except BaseException as exc:  # noqa: BLE001 - the probe reports every outcome
        return f"raise {type(exc).__module__}.{type(exc).__qualname__}: {exc}"


def section(title):
    print(f"\n== {title}")


print("rapidjson", rapidjson.__version__, rapidjson.__rapidjson_version__,
      rapidjson.__rapidjson_exact_version__, "| python", sys.version.split()[0],
      "| recursionlimit", sys.getrecursionlimit())
print("JSONDecodeError MRO", [c.__name__ for c in rapidjson.JSONDecodeError.__mro__])
print("ValidationError MRO", [c.__name__ for c in rapidjson.ValidationError.__mro__])

# --------------------------------------------------------------------------- Q1
section("Q1 decoder hooks and duplicate keys")


class RefuseDuplicates(rapidjson.Decoder):
    """Minimal duplicate-refusing decoder: objects arrive as (key, value) pairs."""

    def start_object(self):
        return []

    def end_object(self, pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key {key!r}")
            result[key] = value
        return result


class RefuseDuplicatesWithEndArray(RefuseDuplicates):
    def end_array(self, items):
        return items


strict = RefuseDuplicates(number_mode=NM)
print("Decoder attrs", strict.number_mode, strict.parse_mode, strict.datetime_mode, strict.uuid_mode)
for text in (
    '{"a":1,"a":2}',
    '{"a":1,"b":2}',
    '{"x":{"a":1,"a":2}}',
    '[{"a":1},{"a":1,"a":2}]',
    '{"a":{"b":1},"a":2}',
    '{"a":[1,{"c":1}],"b":{"d":[2]}}',
    '{"a":1.10,"b":[0.5]}',
    '{"\\u0061":1,"a":2}',
    '{}',
    '[]',
    '"top"',
):
    print(f"  RefuseDuplicates {text:40} {show(lambda: strict(text))}")
print("  stdlib-shaped loads on duplicates:", show(lambda: rapidjson.loads('{"a":1,"a":2}')))
print("  loads object_hook sees only the collapsed dict:",
      show(lambda: rapidjson.loads('{"a":1,"a":2}', object_hook=lambda d: sorted(d.items()))))
with_end_array = RefuseDuplicatesWithEndArray(number_mode=NM)
for text in ('{"a":[1]}', '[[1],{"a":2}]', '{"a":{"b":[1]}}'):
    print(f"  +end_array {text:30} {show(lambda: with_end_array(text))}")

section("Q1 decoder: number/parse modes and non-finite through a Decoder")
for label, dec in (
    ("Decoder(number_mode=NM_DECIMAL)", RefuseDuplicates(number_mode=NM)),
    ("Decoder()", RefuseDuplicates()),
    ("Decoder(number_mode=NM_DECIMAL|NM_NAN)", RefuseDuplicates(number_mode=NM | rapidjson.NM_NAN)),
    ("Decoder(parse_mode=PM_COMMENTS)", RefuseDuplicates(number_mode=NM, parse_mode=rapidjson.PM_COMMENTS)),
):
    for text in ('{"n":0.1}', '{"n":NaN}', '{"n":1e400}', '[1,]', '[1 /*c*/]'):
        print(f"  {label:42} {text:14} {show(lambda: dec(text))}")
print("  Decoder(allow_nan=False):", show(lambda: rapidjson.Decoder(allow_nan=False)))
print("  Decoder(number_mode=NM_NATIVE|NM_DECIMAL):",
      show(lambda: rapidjson.Decoder(number_mode=rapidjson.NM_NATIVE | NM)))
print("  Decoder(object_hook=...):", show(lambda: rapidjson.Decoder()('{}', object_hook=dict)))

section("Q1 decoder: hook call counts and key sharing")
calls = collections.Counter()


class Counting(rapidjson.Decoder):
    def start_object(self):
        calls["start_object"] += 1
        return []

    def end_object(self, pairs):
        calls["end_object"] += 1
        return dict(pairs)

    def string(self, s):
        calls["string"] += 1
        return s


Counting()('[{"a":"x","b":{"c":"y"}},{"a":"z"},["w"]]')
print("  calls for 3 objects, 3 string values, keys a,b,c,a:", dict(calls))
shared = rapidjson.loads('[{"key_name_x":1},{"key_name_x":2}]')
print("  repeated keys are one object (sharedKeys):", list(shared[0])[0] is list(shared[1])[0])


class Raising(rapidjson.Decoder):
    def end_object(self, mapping):
        raise KeyError("hook failure")


print("  hook exception propagates unchanged:", show(lambda: Raising()('{"a":1}')))
print("  string hook returning non-str is accepted:",
      show(lambda: type("S", (rapidjson.Decoder,), {"string": lambda self, s: len(s)})()('["abc"]')))

# --------------------------------------------------------------------------- Q2
section("Q2 decode numbers")
literals = ["NaN", "Infinity", "-Infinity", "nan", "inf", "1e400", "-1e400", "1e-400", "-0", "-0.0",
            "0.0", "1E2", "1e2", "1.0", "1.5e+3", "123456789012345678901234567890",
            "-123456789012345678901234567890", "18446744073709551616", "0.1000000000000000000001",
            "01", "1.", ".5", "+1", "0x10", "1e", "-"]
modes = {
    "NM_DECIMAL allow_nan=False": dict(number_mode=NM, allow_nan=False),
    "NM_DECIMAL": dict(number_mode=NM),
    "NM_DECIMAL|NM_NAN": dict(number_mode=NM | rapidjson.NM_NAN),
    "default": {},
    "allow_nan=False": dict(allow_nan=False),
    "NM_NATIVE": dict(number_mode=rapidjson.NM_NATIVE),
}
for literal in literals:
    for label, kwargs in modes.items():
        print(f"  {literal:34} {label:28} {show(lambda: rapidjson.loads(literal, **kwargs))}")
print("  stdlib json.loads('1e400') =", show(lambda: json.loads("1e400")),
      "| json.loads('NaN') =", show(lambda: json.loads("NaN")))

section("Q2 encode non-finite / extreme numbers (json_bytes options)")


def jb(value, **extra):
    options = dict(number_mode=NM, allow_nan=False, sort_keys=True, ensure_ascii=False,
                   bytes_mode=rapidjson.BM_NONE)
    options.update(extra)
    return rapidjson.dumps(value, **options)


for value in (float("nan"), float("inf"), Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
              Decimal("-0"), Decimal("1E+2"), Decimal("0E-7"), Decimal("1.10"), Decimal("1e400"),
              -0.0, 1e300, 10**40, True):
    print(f"  {value!r:24} {show(lambda: jb(value))}")

# --------------------------------------------------------------------------- Q3
section("Q3 depth (in-process, default recursion limit)")
limit = sys.getrecursionlimit()
for depth in (limit - 10, limit - 1, limit, limit + 1, 10 * limit):
    print(f"  loads [ * {depth:6}: {show(lambda: type(rapidjson.loads('[' * depth + ']' * depth)).__name__)}")
    print(f"  loads {{ * {depth:6}: "
          f"{show(lambda: type(rapidjson.loads(''.join(['{\"a\":'] * depth) + '1' + '}' * depth)).__name__)}")


def nested(depth):
    value = []
    for _ in range(depth):
        value = [value]
    return value


for depth in (limit // 2, limit - 60, limit, 10 * limit):
    print(f"  dumps nested list {depth:6}: {show(lambda: len(jb(nested(depth))))}")
    print(f"  stdlib json.dumps {depth:6}: {show(lambda: len(json.dumps(nested(depth))))}")
print("  stdlib json.loads 10*limit:", show(lambda: type(json.loads('[' * 10 * limit + ']' * 10 * limit)).__name__))
print("  loads/dumps signatures carry no depth or size parameter:",
      "max_depth" not in (rapidjson.loads.__doc__ or ""), "limit" not in (rapidjson.dumps.__doc__ or ""))

section("Q3 embedded NUL ends the document")
for text in ('[1]\x00garbage', '[1]\x00', '"a\x00b"', '{"a":1}\x00{"b":2}'):
    print(f"  loads {text!r:24} {show(lambda: rapidjson.loads(text))}")
    print(f"  loads bytes {text!r:18} {show(lambda: rapidjson.loads(text.encode()))}")
    print(f"  load(BytesIO) {text!r:16} {show(lambda: rapidjson.load(io.BytesIO(text.encode())))}")
    print(f"  stdlib {text!r:23} {show(lambda: json.loads(text))}")

section("Q3 invalid UTF-8 and escaped surrogates on decode")
for raw in (b'"\xff"', b'"\xed\xa0\x80"', b'"\\ud800"', b'"\\udc00x"', b'"\\ud83d\\ude00"', b'"\xc3\xa9"'):
    print(f"  loads {raw!r:22} {show(lambda: rapidjson.loads(raw))} | stdlib {show(lambda: json.loads(raw))}")

# --------------------------------------------------------------------------- Q4
section("Q4 encoder: which Python types pass")


class Plain(enum.Enum):
    A = "a"


class Colour(enum.StrEnum):
    RED = "red"


class Level(enum.IntEnum):
    ONE = 1


class StrSub(str):
    def __str__(self):
        return "OVERRIDDEN"


class IntSub(int):
    def __repr__(self):
        return "OVERRIDDEN"


class FloatSub(float):
    def __repr__(self):
        return "OVERRIDDEN"


class DecSub(Decimal):
    def __str__(self):
        return "OVERRIDDEN"

    def is_nan(self):
        print("    (DecSub.is_nan called)")
        return False


class DictSub(dict):
    def items(self):
        raise AssertionError("never called")


class ListSub(list):
    pass


class RoMapping(Mapping):
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


@dataclasses.dataclass
class DC:
    a: int = 1


try:
    import pydantic

    class Model(pydantic.BaseModel):
        a: int = 1

    model = Model()
except ImportError:  # pragma: no cover
    model = None

values = {
    "tuple": (1, 2),
    "set": {1},
    "frozenset": frozenset({1}),
    "generator": (i for i in range(2)),
    "iter(list)": iter([1, 2]),
    "range": range(2),
    "dict_keys": {"a": 1}.keys(),
    "list subclass": ListSub([1]),
    "dict subclass": DictSub(a=1),
    "OrderedDict": collections.OrderedDict(a=1),
    "defaultdict": collections.defaultdict(int, a=1),
    "Counter": collections.Counter(a=1),
    "abc.Mapping": RoMapping({"a": 1}),
    "MappingProxyType": types.MappingProxyType({"a": 1}),
    "str subclass": StrSub("text"),
    "int subclass": IntSub(5),
    "float subclass": FloatSub(0.5),
    "Decimal subclass": DecSub("1.5"),
    "IntEnum": Level.ONE,
    "StrEnum": Colour.RED,
    "Enum": Plain.A,
    "dataclass": DC(),
    "pydantic model": model,
    "datetime": datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    "date": date(2026, 1, 2),
    "UUID": uuid.UUID(int=1),
    "bytes": b"ab",
    "bytearray": bytearray(b"ab"),
    "memoryview": memoryview(b"ab"),
    "Path": pathlib.PurePosixPath("/x"),
    "complex": 1j,
    "RawJSON": rapidjson.RawJSON("[1]"),
    "keys bool": {True: 1},
    "keys int": {1: 1},
    "keys None": {None: 1},
    "keys StrEnum": {Colour.RED: 1},
    "keys str subclass": {StrSub("k"): 1},
    "keys tuple": {(1,): 1},
}
configs = {
    "rapidjson defaults": dict(),
    "json_bytes options": dict(number_mode=NM, allow_nan=False, sort_keys=True, ensure_ascii=False,
                                bytes_mode=rapidjson.BM_NONE),
    "strictest": dict(number_mode=NM, allow_nan=False, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE,
                      iterable_mode=rapidjson.IM_ONLY_LISTS,
                      mapping_mode=rapidjson.MM_ONLY_DICTS | rapidjson.MM_SORT_KEYS),
}
for label, value in values.items():
    for config, kwargs in configs.items():
        fresh = (i for i in range(2)) if label == "generator" else (iter([1, 2]) if label == "iter(list)" else value)
        print(f"  {label:18} {config:20} {show(lambda: rapidjson.dumps(fresh, **kwargs))}")

section("Q4 encoder: default= and Encoder.default()")
seen = []


def default(obj):
    seen.append(type(obj).__name__)
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"refused {type(obj).__name__}")


strict_kwargs = configs["strictest"]
for value in ({1, 2}, (1, 2), DictSub(a=1), Plain.A, Colour.RED, IntSub(3), [1, (2,)]):
    print(f"  default= {value!r:32} {show(lambda: rapidjson.dumps(value, default=default, **strict_kwargs))}")
print("  default saw:", seen)


class ExactEncoder(rapidjson.Encoder):
    def default(self, obj):
        raise TypeError(f"exact JSON refuses {type(obj).__name__}")


enc = ExactEncoder(number_mode=NM, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE,
                   iterable_mode=rapidjson.IM_ONLY_LISTS,
                   mapping_mode=rapidjson.MM_ONLY_DICTS | rapidjson.MM_SORT_KEYS)
print("  Encoder attrs", enc.number_mode, enc.mapping_mode, enc.iterable_mode, enc.write_mode)
for value in ({"b": 1, "a": (1,)}, {"a": [Decimal("1.0")]}, {"a": Colour.RED}):
    print(f"  ExactEncoder {value!r:36} {show(lambda: enc(value))}")
print("  Encoder(allow_nan=False):", show(lambda: rapidjson.Encoder(allow_nan=False)))
print("  Encoder(number_mode=NM_DECIMAL) on NaN float (NM_NAN not set):",
      show(lambda: rapidjson.Encoder(number_mode=NM)(float("nan"))))
print("  Encoder() default number_mode includes NM_NAN:", rapidjson.Encoder().number_mode,
      show(lambda: rapidjson.Encoder()(float("nan"))))

section("Q4 sort order and key coercion")
keys = ["b", "a", "B", "é", "z", "￿", "\U0001f600", "éa", "", "a\x00", "aa", " "]
doc = {k: i for i, k in enumerate(keys)}
r_order = list(json.loads(rapidjson.dumps(doc, sort_keys=True, ensure_ascii=False)))
s_order = list(json.loads(json.dumps(doc, sort_keys=True, ensure_ascii=False)))
print("  rapidjson order == stdlib order:", r_order == s_order, [hex(ord(k[0])) if k else "''" for k in r_order])
print("  sort_keys with int key:", show(lambda: rapidjson.dumps({1: 1, "a": 2}, sort_keys=True)))
print("  MM_COERCE|MM_SORT duplicate after coercion:",
      show(lambda: rapidjson.dumps({1: "int", "1": "str"},
                                   mapping_mode=rapidjson.MM_COERCE_KEYS_TO_STRINGS | rapidjson.MM_SORT_KEYS)))
print("  MM_SKIP_NON_STRING_KEYS:", show(lambda: rapidjson.dumps({1: 1, "a": 2},
                                                                 mapping_mode=rapidjson.MM_SKIP_NON_STRING_KEYS)))
print("  stdlib sort_keys with int key:", show(lambda: json.dumps({1: 1, "a": 2}, sort_keys=True)))

# --------------------------------------------------------------------------- Q5
section("Q5 escaping: rapidjson(json_bytes options) vs stdlib(canonical options)")


def stdlib(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


differ = []
for cp in list(range(0x00, 0x20)) + [0x22, 0x2F, 0x5C, 0x7F, 0x80, 0x9F, 0xA0, 0x2028, 0x2029,
                                       0xFEFF, 0xFFFF, 0x1F600, 0x10FFFF]:
    ch = chr(cp)
    r, s = jb(ch), stdlib(ch)
    ra = rapidjson.dumps(ch)
    sa = json.dumps(ch)
    mark = "" if r == s else "   <-- differs"
    if r != s:
        differ.append(f"U+{cp:04X}")
    print(f"  U+{cp:04X} rapidjson {r!r:12} stdlib {s!r:12} | ensure_ascii rapidjson {ra!r:16} stdlib {sa!r:16}{mark}")
print("  differing code points (ensure_ascii=False):", differ)
print("  key escaping:", repr(jb({"\x1f\x0b": 1})), "vs", repr(stdlib({"\x1f\x0b": 1})))
print("  lone surrogate value:", show(lambda: jb("\ud800")), "| stdlib", show(lambda: stdlib("\ud800")),
      "| stdlib .encode()", show(lambda: stdlib("\ud800").encode()))
print("  lone surrogate ensure_ascii=True:", show(lambda: rapidjson.dumps("\ud800")),
      "| stdlib", show(lambda: json.dumps("\ud800")))
print("  separators/indent: default", repr(rapidjson.dumps({"a": [1, 2]})),
      "| WM_PRETTY", repr(rapidjson.dumps({"a": [1, 2]}, write_mode=rapidjson.WM_PRETTY)),
      "| indent=2", repr(rapidjson.dumps({"a": [1, 2]}, indent=2)),
      "| WM_SINGLE_LINE_ARRAY", repr(rapidjson.dumps({"a": [1, 2]}, write_mode=rapidjson.WM_SINGLE_LINE_ARRAY)))
print("  separators= keyword:", show(lambda: rapidjson.dumps([1], separators=(",", ":"))))
print("  floats: rapidjson", jb([1e-7, 1e16, 0.1, -0.0, 1e22]), "stdlib", stdlib([1e-7, 1e16, 0.1, -0.0, 1e22]))

section("Q5 hypothesis differential (str/int/float/bool/None/list/dict incl. control characters)")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

text = st.text(alphabet=st.characters(codec="utf-8"), max_size=12)  # excludes lone surrogates
scalars = st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | text
values_strategy = st.recursive(
    scalars, lambda children: st.lists(children, max_size=4) | st.dictionaries(text, children, max_size=4),
    max_leaves=20)
mismatches = []


@settings(max_examples=3000, deadline=None, database=None, suppress_health_check=list(HealthCheck))
@given(values_strategy)
def differential(value):
    r, s = jb(value), stdlib(value)
    if r != s:
        mismatches.append((value, r, s))


differential()
kinds = collections.Counter()
for value, r, s in mismatches:
    lowered = r.encode().decode()
    # classify: identical after lowercasing the hex digits of \u00XX escapes?
    import re  # noqa: E402

    normalized = re.sub(r"\\u00([0-9A-F]{2})", lambda m: "\\u00" + m.group(1).lower(), lowered)
    kinds["control-escape case only" if normalized == s else "other"] += 1
print(f"  examples with byte differences: {len(mismatches)} classified {dict(kinds)}")
for value, r, s in [m for m in mismatches if True][:3]:
    print(f"    e.g. {value!r} rapidjson {r!r} stdlib {s!r}")
others = []
for value, r, s in mismatches:
    normalized = re.sub(r"\\u00([0-9A-F]{2})", lambda m: "\\u00" + m.group(1).lower(), r)
    if normalized != s:
        others.append((value, r, s))
for value, r, s in others[:5]:
    print(f"    OTHER {value!r} rapidjson {r!r} stdlib {s!r}")
print("  Decimal spellings (str(Decimal)):", jb([Decimal("1E+2"), Decimal("-0"), Decimal("0E-7"),
                                                  Decimal("1.10"), Decimal("12345678901234567890.123")]))

# --------------------------------------------------------------------------- Q6
section("Q6 RawJSON")
print("  RawJSON(bytes):", show(lambda: rapidjson.RawJSON(b"[1]")))
print("  RawJSON(str subclass):", show(lambda: rapidjson.RawJSON(StrSub("[1]")).value))
print("  subclassable:", show(lambda: type("R", (rapidjson.RawJSON,), {})))
print("  top level:", show(lambda: jb(rapidjson.RawJSON('{"b":1, "a":2}'))))
print("  sort_keys does not reorder inside:", show(lambda: jb({"z": rapidjson.RawJSON('{"b":1,"a":2}'), "a": 0})))
print("  invalid text emitted verbatim:", show(lambda: jb({"a": rapidjson.RawJSON("[1, ")})))
print("  as a key:", show(lambda: jb({rapidjson.RawJSON('"k"'): 1})))
print("  non-ASCII raw with ensure_ascii=False:", show(lambda: jb([rapidjson.RawJSON('"é€😀"')])))
print("  non-ASCII raw with ensure_ascii=True:", show(lambda: rapidjson.dumps([rapidjson.RawJSON('"é€😀"')])))
print("  raw NaN with allow_nan=False:", show(lambda: jb([rapidjson.RawJSON("NaN")])))
print("  raw survives IM_ONLY_LISTS/MM_ONLY_DICTS:", show(lambda: rapidjson.dumps(
    {"a": rapidjson.RawJSON("1.10")}, **configs["strictest"])))
print("  raw with embedded NUL:", show(lambda: jb([rapidjson.RawJSON("1\x002")])))
print("  dump(RawJSON) to BytesIO:", show(lambda: (lambda b: (rapidjson.dump(rapidjson.RawJSON("[1]"), b), b.getvalue())[1])(io.BytesIO())))


class KeepNumberText(rapidjson.Decoder):
    def string(self, s):
        return s


print("  Decoder hook names (no raw/number hook):",
      [n for n in ("start_object", "end_object", "end_array", "string", "number", "raw") if hasattr(rapidjson.Decoder, n)])

# --------------------------------------------------------------------------- Q7
section("Q7 streams")
binary, text_stream = io.BytesIO(), io.StringIO()
rapidjson.dump({"a": "é"}, binary, ensure_ascii=False)
rapidjson.dump({"a": "é"}, text_stream, ensure_ascii=False)
print("  dump to BytesIO", binary.getvalue(), "| to StringIO", repr(text_stream.getvalue()))
print("  load(BytesIO)", show(lambda: rapidjson.load(io.BytesIO('{"a":"é","n":1.5}'.encode()), number_mode=NM)))
print("  load(StringIO)", show(lambda: rapidjson.load(io.StringIO('{"a":"é","n":1.5}'), number_mode=NM)))
print("  load JSONL (two values):", show(lambda: rapidjson.load(io.BytesIO(b'{"a":1}\n{"b":2}\n'))))
print("  loads JSONL (two values):", show(lambda: rapidjson.loads('{"a":1}\n{"b":2}\n')))
print("  parse_mode constants:", [n for n in dir(rapidjson) if n.startswith("PM_")])
print("  load with object_hook:", show(lambda: rapidjson.load(io.BytesIO(b'{"a":1}'), object_hook=lambda d: list(d))))
print("  Decoder()(stream):", show(lambda: RefuseDuplicates()(io.BytesIO(b'{"a":1,"a":2}'), chunk_size=2)))


class Recorder:
    """Binary stream that records how far the producer had got at each write."""

    def __init__(self, limit=None):
        self.limit = limit
        self.total = 0
        self.writes = []

    def write(self, chunk):
        self.writes.append((len(chunk), progress[0]))
        self.total += len(chunk)
        if self.limit is not None and self.total > self.limit:
            raise OverflowError(f"frame exceeds {self.limit} bytes")
        return len(chunk)


progress = [0]


def produce(n):
    for i in range(n):
        progress[0] = i
        yield {"i": i, "pad": "x" * 20}


sink = Recorder()
rapidjson.dump(produce(20000), sink, chunk_size=65536, number_mode=NM, allow_nan=False, ensure_ascii=False)
print(f"  generator of 20000 items -> {len(sink.writes)} writes, {sink.total} bytes;"
      f" producer index at each of the first writes: {[p for _, p in sink.writes[:5]]}")
print("  generator refused under IM_ONLY_LISTS:",
      show(lambda: rapidjson.dump(produce(3), Recorder(), iterable_mode=rapidjson.IM_ONLY_LISTS)))

bounded = Recorder(limit=10000)
progress[0] = 0
outcome = show(lambda: rapidjson.dump(produce(20000), bounded, chunk_size=4096, ensure_ascii=False))
print(f"  byte bound 10000 via write(): {outcome}; writes={len(bounded.writes)} total={bounded.total}"
      f" producer stopped at index {progress[0]}")
bounded = Recorder(limit=100)
outcome = show(lambda: rapidjson.dump(["y" * 100000], bounded, chunk_size=64, ensure_ascii=False))
print(f"  byte bound 100 inside one long string (chunk 64): {outcome}; write calls={len(bounded.writes)}")
print("  sys.exc state clean afterwards:", sys.exc_info())


class TextRecorder(io.StringIO):
    pass


ts = TextRecorder()
rapidjson.dump(["é" * 50], ts, chunk_size=7, ensure_ascii=False)
print("  text stream with chunk_size splitting multibyte chars:", ts.getvalue() == jb(["é" * 50]))
print("  dump returns:", show(lambda: rapidjson.dump([1], io.BytesIO())))
print("  Encoder()(obj, stream):", show(lambda: (lambda b: (rapidjson.Encoder()([1], b), b.getvalue())[1])(io.BytesIO())))
