"""Codec contracts against this repository's JSON recipes.

Compares orjson and msgspec with the stdlib identity recipe (`canonical_bytes`) and the
rapidjson exact-decimal recipe (`json_bytes` / `json_loads`). Synthetic values only.
"""

import decimal
import json
import math
import random

import msgspec
import orjson
import rapidjson
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

D = decimal.Decimal


def exact(obj):
    if isinstance(obj, D):
        return {"decimal": str(obj)}
    raise TypeError(type(obj).__name__)


def stdlib_identity(value):
    return json.dumps(
        value,
        default=exact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def orjson_identity(value):
    return orjson.dumps(value, default=exact, option=orjson.OPT_SORT_KEYS)


MSGSPEC_IDENTITY = msgspec.json.Encoder(
    decimal_format=lambda d: {"decimal": str(d)}, order="deterministic"
)
MSGSPEC_NUMBER = msgspec.json.Encoder(decimal_format="number", order="deterministic")
MSGSPEC_DECIMAL = msgspec.json.Decoder(float_hook=D)


def rapidjson_bytes(value):
    return rapidjson.dumps(
        value,
        number_mode=rapidjson.NM_DECIMAL,
        allow_nan=False,
        sort_keys=True,
        ensure_ascii=False,
        bytes_mode=rapidjson.BM_NONE,
    ).encode()


def rapidjson_loads(content):
    return rapidjson.loads(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False)


def attempt(function, value):
    try:
        return function(value)
    except Exception as error:
        return f"raises {type(error).__name__}"


def show(value):
    if isinstance(value, str) and value.startswith("raises "):
        return value
    return f"{type(value).__name__} {value!a}"


def differential(label, leaf, candidates, reference, min_codepoint=0):
    text = st.text(st.characters(codec="utf-8", min_codepoint=min_codepoint))
    first = {}
    values = st.recursive(
        leaf(text),
        lambda inner: st.one_of(
            st.lists(inner, max_size=5), st.dictionaries(text, inner, max_size=5)
        ),
        max_leaves=40,
    )
    mismatches = dict.fromkeys(candidates, 0)

    @settings(
        max_examples=20000,
        deadline=None,
        derandomize=True,
        database=None,
        suppress_health_check=list(HealthCheck),
    )
    @given(values)
    def run(value):
        expected = attempt(reference, value)
        for name, function in candidates.items():
            actual = attempt(function, value)
            if actual != expected:
                mismatches[name] += 1
                first.setdefault(name, (value, expected, actual))

    run()
    print(f"{label}: mismatches in 20000 examples {mismatches}")
    for name, (value, expected, actual) in first.items():
        print(f"  first {name} mismatch: {value!a} reference {expected!a} candidate {actual!a}")


def float_bands(function):
    generator = random.Random(7)
    bands = set()
    for _ in range(400000):
        value = 10.0 ** generator.uniform(-323, 308)
        if value and math.isfinite(value) and function(value) != json.dumps(value).encode():
            bands.add(math.floor(math.log10(value)))
    return sorted(bands)


print("versions", orjson.__version__, msgspec.__version__, rapidjson.__version__)

print("\n== identity recipe, byte equality with stdlib")
differential(
    "no floats, Decimal via hook",
    lambda text: st.one_of(
        st.none(), st.booleans(), st.integers(-(2**63), 2**64 - 1), text, st.decimals()
    ),
    {"orjson": orjson_identity, "msgspec": MSGSPEC_IDENTITY.encode},
    stdlib_identity,
)
differential(
    "finite floats only",
    lambda text: st.floats(allow_nan=False, allow_infinity=False),
    {"orjson": orjson_identity, "msgspec": MSGSPEC_IDENTITY.encode},
    stdlib_identity,
)
print("float decimal exponents that differ: orjson", float_bands(orjson.dumps))
bands = float_bands(msgspec.json.encode)
print("float decimal exponents that differ: msgspec", bands[:5], "and", bands[5], "to", bands[-1])
for value in (1e-7, 1e-5, 1e-4, 1e16, -0.0, 5e-324):
    print(f"  {value!r}: stdlib {json.dumps(value)} orjson {orjson.dumps(value).decode()}"
          f" msgspec {msgspec.json.encode(value).decode()}")

print("\n== values the stdlib recipe refuses or spells differently")
import dataclasses
import enum
import uuid


class Colour(enum.Enum):
    RED = "red"


class Kind(enum.StrEnum):
    A = "a"


@dataclasses.dataclass
class Point:
    x: int


CASES = {
    "int 2**64": 2**64,
    "nan": float("nan"),
    "plain Enum": Colour.RED,
    "UUID": uuid.UUID(int=1),
    "dataclass": Point(1),
    "int key": {1: 1},
    "StrEnum key": {Kind.A: 1},
    "StrEnum value": Kind.A,
    "tuple": (1, 2),
}
for name, value in CASES.items():
    print(f"  {name}: stdlib {show(attempt(stdlib_identity, value))} | orjson"
          f" {show(attempt(orjson_identity, value))} | msgspec"
          f" {show(attempt(MSGSPEC_IDENTITY.encode, value))}")

print("\n== exact-decimal recipe: msgspec decimal_format='number' against rapidjson")
differential(
    "ints, Decimals, text from U+0020",
    lambda text: st.one_of(
        st.none(),
        st.booleans(),
        st.integers(-(2**63), 2**64 - 1),
        text,
        st.decimals(allow_nan=False, allow_infinity=False),
    ),
    {"msgspec": MSGSPEC_NUMBER.encode},
    rapidjson_bytes,
    min_codepoint=0x20,
)
for literal in ("NaN", "Infinity"):
    print(f"  Decimal({literal}): rapidjson {show(attempt(rapidjson_bytes, D(literal)))}"
          f" | msgspec {show(attempt(MSGSPEC_NUMBER.encode, D(literal)))}")
print(f"  U+000B: rapidjson {rapidjson_bytes(chr(11))!r} | msgspec {MSGSPEC_NUMBER.encode(chr(11))!r}")

print("\n== decoding")
DECODERS = {
    "stdlib": json.loads,
    "rapidjson NM_DECIMAL": rapidjson_loads,
    "orjson": orjson.loads,
    "msgspec": msgspec.json.decode,
    "msgspec float_hook": MSGSPEC_DECIMAL.decode,
}
for content in (
    b"1",
    b"1.0",
    b"1.10",
    b"1e2",
    b"1E400",
    b"18446744073709551616",
    b"1000000000000000000000000000000",
    b'{"a":1,"a":2}',
    b"NaN",
    b'"\\ud800"',
    b"\xef\xbb\xbf1",
):
    print(f"  {content!a}")
    for name, function in DECODERS.items():
        print(f"    {name}: {show(attempt(function, content))}".encode("ascii", "backslashreplace").decode())

print("\n== embedding encoded JSON")
print(" ", orjson.dumps({"b": orjson.Fragment(b'{"z": 1, "a":2}'), "a": 1}, option=orjson.OPT_SORT_KEYS))
print(" ", orjson.dumps([orjson.Fragment(b"not json{")]))


class Envelope(msgspec.Struct):
    kind: str
    body: msgspec.Raw


envelope = msgspec.json.decode(b'{"kind":"k","body":{"z": 1,  "a":[1.10]}}', type=Envelope)
print(" ", bytes(envelope.body), msgspec.json.encode(envelope))
