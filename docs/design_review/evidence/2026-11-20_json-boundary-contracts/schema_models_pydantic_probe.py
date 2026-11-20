"""Contract probe: pydantic 2.14.1 / pydantic-core 2.50.1 validation modes, Decimal, JSON output,
JSON Schema generation, discriminators and the JSON parser.

Run from the repository root:
    uv run python docs/design_review/evidence/2026-11-20_json-boundary-contracts/schema_models_pydantic_probe.py
"""

from __future__ import annotations

import enum
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Literal, Union
from uuid import UUID

import pydantic_core
import rapidjson
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    JsonValue,
    PlainSerializer,
    Tag,
    TypeAdapter,
    ValidationError,
)
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import TypeAliasType
from pydantic_core import from_json, to_json

print("python", sys.version.split()[0], "pydantic-core", pydantic_core.__version__)


def outcome(fn):
    try:
        value = fn()
        return f"{type(value).__name__}:{value!r}"[:60]
    except ValidationError as exc:
        return "ERR:" + exc.errors(include_url=False)[0]["type"]
    except Exception as exc:  # noqa: BLE001
        return f"RAISE:{type(exc).__name__}"


def json_text(value):
    try:
        return rapidjson.dumps(value, number_mode=rapidjson.NM_DECIMAL)
    except Exception:  # noqa: BLE001 - not JSON-encodable (date, UUID ...)
        return None


class Colour(enum.Enum):
    RED = "red"


class Level(enum.IntEnum):
    ONE = 1


class Inner(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    a: int


print("\n[C11] mode table: py_strict | py_lax | json_strict (input JSON-encoded) | str_strict | str_lax")
rows = [
    (Decimal, ["1.10", 1, 1.5, Decimal("1.1")]),
    (date, ["2026-11-20", 1763596800, date(2026, 11, 20)]),
    (datetime, ["2026-11-20T10:00:00Z", 1763632800]),
    (Colour, ["red", Colour.RED]),
    (Level, [1, "1"]),
    (tuple[int, int], [[1, 2]]),
    (frozenset[int], [[1, 2]]),
    (set[int], [[1, 2]]),
    (bytes, ["abc"]),
    (UUID, ["12345678-1234-5678-1234-567812345678"]),
    (int, [1.0, 1.5, "1", True]),
    (float, [1, "1.5", True]),
    (bool, [0, 1, "true"]),
    (str, [1]),
    (Literal["a"], ["a"]),
    (Literal[1], [1, 1.0, True]),
    (Inner, [{"a": 1}, {"a": "1"}]),
]
for tp, inputs in rows:
    adapter = TypeAdapter(tp)
    for value in inputs:
        encoded = json_text(value)
        cells = [
            outcome(lambda: adapter.validate_python(value, strict=True)),
            outcome(lambda: adapter.validate_python(value)),
            outcome(lambda: adapter.validate_json(encoded, strict=True)) if encoded is not None else "n/a",
            outcome(lambda: adapter.validate_strings(value, strict=True)),
            outcome(lambda: adapter.validate_strings(value)),
        ]
        print(f"  {getattr(tp, '__name__', str(tp))[:16]:16} {value!r:34.34} " + " | ".join(c[:34] for c in cells))

print("\n[C11] per-field strict=False inside a strict model (python input)")


class Mixed(BaseModel):
    model_config = ConfigDict(strict=True)
    when: Annotated[date, Field(strict=False)]
    amount: Annotated[Decimal, Field(strict=False)]
    count: int


print("  Mixed.model_validate({'when':'2026-11-20','amount':'1.10','count':1}):", outcome(lambda: Mixed.model_validate({"when": "2026-11-20", "amount": "1.10", "count": 1})))
print("  ... count=1.0:", outcome(lambda: Mixed.model_validate({"when": "2026-11-20", "amount": "1.10", "count": 1.0})))

print("\n[C12] Decimal from JSON text")
dec = TypeAdapter(Decimal)
for raw in [b"1.10", b"1e2", b"1E-7", b"0.1000000000000000055511151231257827021181583404541015625", b"12345678901234567890.123456789", b"1e400", b'"1.10"', b'"NaN"', b"NaN"]:
    print(f"  validate_json({raw.decode()[:40]!s}): {outcome(lambda: dec.validate_json(raw))}  strict: {outcome(lambda: dec.validate_json(raw, strict=True))}")
from corpus_structure.semantic.data_operation_json import json_bytes  # noqa: E402

for value in (Decimal("1.10"), Decimal("12345678901234567890.123456789"), Decimal("1E+2")):
    print(f"  project round trip validate_json(json_bytes({value!r})) -> {outcome(lambda: dec.validate_json(json_bytes(value), strict=True))}  vs validate_python strict -> {outcome(lambda: dec.validate_python(value, strict=True))}")
fl = TypeAdapter(float)
print("  float validate_json(1e400):", outcome(lambda: fl.validate_json(b"1e400")))
print("  float validate_json(NaN):", outcome(lambda: fl.validate_json(b"NaN")))
print("  float allow_inf_nan=False validate_json(NaN):", outcome(lambda: TypeAdapter(Annotated[float, Field(allow_inf_nan=False)]).validate_json(b"NaN")))
print("  Decimal serialization: to_json(Decimal('1.10'))", to_json(Decimal("1.10")), "| dump_python json mode", dec.dump_python(Decimal("1E+2"), mode="json"), "| to_json(Decimal('-0'))", to_json(Decimal("-0")))
print("  Decimal('1E+2') via model json:", TypeAdapter(Decimal).dump_json(Decimal("1E+2")))

print("\n[C12] JsonValue and Decimal")
jv = TypeAdapter(JsonValue)
print("  JsonValue.validate_python(Decimal('1.1')):", outcome(lambda: jv.validate_python(Decimal("1.1"))))
print("  JsonValue.validate_python(Decimal('1.1'), strict=True):", outcome(lambda: jv.validate_python(Decimal("1.1"), strict=True)))
print("  JsonValue.validate_json(b'1.10'):", outcome(lambda: jv.validate_json(b"1.10")))
ExactJson = TypeAliasType(
    "ExactJson",
    Union[None, bool, int, Decimal, float, str, list["ExactJson"], dict[str, "ExactJson"]],
)
ej = TypeAdapter(ExactJson)
decoded = rapidjson.loads('{"a":[1,1.10,true,null,"s"]}', number_mode=rapidjson.NM_DECIMAL)
print("  ExactJson.validate_python(rapidjson NM_DECIMAL decode, strict=True):", outcome(lambda: ej.validate_python(decoded, strict=True)))
print("  ExactJson strict rejects tuple:", outcome(lambda: ej.validate_python((1,), strict=True)), "| NaN Decimal:", outcome(lambda: ej.validate_python(Decimal("NaN"), strict=True)))
print("  ExactJson.dump_json:", ej.dump_json(decoded))
print("  strict float accepts Decimal instance?:", outcome(lambda: TypeAdapter(float).validate_python(Decimal("1.1"), strict=True)), "| strict int accepts Decimal('1')?:", outcome(lambda: TypeAdapter(int).validate_python(Decimal("1"), strict=True)))

print("\n[C12] project ExactDecimal sketch: one spelling via PlainSerializer(when_used='json')")
ExactDecimal = Annotated[
    Decimal,
    Field(allow_inf_nan=False),
    PlainSerializer(lambda d: format(d, "f"), return_type=str, when_used="json"),
]
ed = TypeAdapter(ExactDecimal)
print("  dump_json(Decimal('1E+2')):", ed.dump_json(Decimal("1E+2")), "| dump_python python:", ed.dump_python(Decimal("1E+2")), "| NaN:", outcome(lambda: ed.validate_python(Decimal("NaN"))))

print("\n[C13] JSON output spellings: pydantic_core.to_json vs json.dumps")
samples = [0.1, 1e16, 1e-7, 1.0, -0.0, "\x1f", "é", " ", datetime(2026, 11, 20, 10, tzinfo=timezone.utc), b"\xff", {"b": 1, "a": 2}]
for s in samples:
    try:
        std = json.dumps(s, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception as exc:  # noqa: BLE001
        std = f"RAISE:{type(exc).__name__}"
    print(f"  {s!r:40.40} to_json={outcome(lambda: to_json(s))[:50]}  json.dumps={std}")
print("  to_json(float('nan')):", to_json(float("nan")), "| inf_nan_mode='null':", to_json(float("nan"), inf_nan_mode="null"), "| 'strings':", to_json(float("nan"), inf_nan_mode="strings"))
print("  to_json(b'\\xff', bytes_mode='base64'):", to_json(b"\xff", bytes_mode="base64"), "| bytes_mode='hex':", to_json(b"\xff", bytes_mode="hex"))
print("  to_json(object()) default:", outcome(lambda: to_json(object())), "| serialize_unknown=True:", to_json(object(), serialize_unknown=True)[:40])
print("  to_json(frozenset({2,1})):", to_json(frozenset({2, 1})), "| to_json((1,2)):", to_json((1, 2)))
print("  to_json(Decimal('1.10')) with fallback:", to_json(Decimal("1.10"), fallback=lambda v: 0))


class Field7(BaseModel):
    a: int
    b: str | None = None


print("  model_dump_json(exclude_none=True):", Field7(a=1).model_dump_json(exclude_none=True), "| indent=None compact:", Field7(a=1).model_dump_json())

print("\n[C14] JSON Schema generation: Draft 7 subclass vs project hand lowering")
D7 = "http://json-schema.org/draft-07/schema#"


class Draft7JsonSchema(GenerateJsonSchema):
    schema_dialect = D7

    def __init__(self, by_alias: bool = True, ref_template: str = "#/definitions/{model}", **kw: Any):
        super().__init__(by_alias=by_alias, ref_template=ref_template, **kw)

    def generate(self, schema, mode="validation"):
        result = super().generate(schema, mode=mode)
        if "$defs" in result:
            result["definitions"] = result.pop("$defs")
        return result

    def tuple_schema(self, schema):
        result = super().tuple_schema(schema)
        if "prefixItems" in result:
            result["additionalItems"] = result.pop("items", True)
            result["items"] = result.pop("prefixItems")
        return result


class Leaf(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["leaf"]
    value: Decimal | None = None
    pair: tuple[int, str]
    rest: tuple[int, ...] = ()


class Root(BaseModel):
    model_config = ConfigDict(extra="forbid")
    leaves: list[Leaf]
    one: Leaf = Field(description="a described ref")
    maybe: Leaf | None = None
    when: datetime
    blob: bytes


from corpus_structure.semantic.data_operation_wire import generated_json_schema  # noqa: E402

hand = generated_json_schema(Root.model_json_schema())
native = Root.model_json_schema(ref_template="#/definitions/{model}", schema_generator=Draft7JsonSchema)
canon = lambda v: json.dumps(v, sort_keys=True, separators=(",", ":"))  # noqa: E731
print("  native subclass == hand lowering (canonical):", canon(native) == canon(hand))
if canon(native) != canon(hand):
    print("  hand:  ", canon(hand)[:600])
    print("  native:", canon(native)[:600])
print("  native definitions keys:", sorted(native.get("definitions", {})), "| refs use #/definitions:", "#/$defs" not in canon(native))
print("  Leaf in native:", canon(native["definitions"]["Leaf"])[:700])
print("  'one' property (ref with sibling description):", native["properties"]["one"])
print("  Decimal validation-mode schema:", TypeAdapter(Decimal).json_schema(), "| serialization-mode:", TypeAdapter(Decimal).json_schema(mode="serialization"))
print("  key order of generated schema is sorted by pydantic's sort():", list(Root.model_json_schema().keys()))
from jsonschema import Draft7Validator  # noqa: E402

Draft7Validator.check_schema(native)
print("  Draft7Validator.check_schema(native subclass output): ok")

print("\n[C15] discriminated unions")


class DecimalTagged(BaseModel):
    model_config = ConfigDict(strict=True)
    kind: Literal["decimal"]
    text: str


class TextTagged(BaseModel):
    model_config = ConfigDict(strict=True)
    kind: Literal["text"]
    text: str


Plain = TypeAdapter(Annotated[DecimalTagged | TextTagged, Field(discriminator="kind")])
print("  field discriminator ok:", outcome(lambda: Plain.validate_python({"kind": "text", "text": "a"})))
try:
    Plain.validate_python({"kind": "nope", "text": "a"})
except ValidationError as exc:
    print("  unknown tag error:", exc.errors(include_url=False, include_input=False))
try:
    Plain.validate_python({"kind": "decimal"})
except ValidationError as exc:
    print("  missing field error loc:", [e["loc"] for e in exc.errors(include_url=False)])
print("  field discriminator JSON schema:", json.dumps(Plain.json_schema())[:400])


def array_tag(value):
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], str):
        return value[0]
    if isinstance(value, dict):
        return value.get("kind")
    return None


TaggedArray = TypeAdapter(
    Annotated[
        Union[
            Annotated[tuple[Literal["decimal"], str], Tag("decimal")],
            Annotated[tuple[Literal["decimal-report"], str, int], Tag("decimal-report")],
            Annotated[DecimalTagged, Tag("object")],
        ],
        Discriminator(lambda v: "object" if isinstance(v, dict) else array_tag(v)),
    ]
)
print("  callable discriminator ['decimal','1.1']:", outcome(lambda: TaggedArray.validate_json(b'["decimal","1.1"]', strict=True)))
print("  callable discriminator ['decimal-report','1.1',2]:", outcome(lambda: TaggedArray.validate_json(b'["decimal-report","1.1",2]', strict=True)))
try:
    TaggedArray.validate_python(["other", "1"])
except ValidationError as exc:
    print("  callable discriminator unknown tag:", exc.errors(include_url=False, include_input=False))
print("  callable discriminator JSON schema:", json.dumps(TaggedArray.json_schema())[:300])
Smart = TypeAdapter(DecimalTagged | TextTagged)
try:
    Smart.validate_python({"kind": "nope", "text": "a"})
except ValidationError as exc:
    print("  smart union error count:", exc.error_count(), [e["loc"] for e in exc.errors()])

print("\n[C16] TypeAdapter defer_build and revalidation")
deferred = TypeAdapter(Inner, config=None) if False else TypeAdapter(list[int], config=ConfigDict(defer_build=True))
print("  defer_build: pydantic_complete before use:", deferred.pydantic_complete, "| after validate:", (deferred.validate_python([1]), deferred.pydantic_complete))


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="never")
    a: int


bad = Strict.model_construct(a="not-int")
print("  model_construct skips validation:", bad.a, "| model_copy(update) skips:", Strict(a=1).model_copy(update={"a": "x"}).a)


class Holder(BaseModel):
    s: Strict


print("  revalidate_instances='never' passes constructed instance through:", outcome(lambda: Holder(s=bad).s.a))


class StrictAlways(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")
    a: int


class Holder2(BaseModel):
    s: StrictAlways


print("  revalidate_instances='always':", outcome(lambda: Holder2(s=StrictAlways.model_construct(a="x"))))

print("\n[C17] parser: partial, duplicates, NaN, depth, patterns")
print("  from_json(b'{\"a\":1,\"a\":2}'):", from_json(b'{"a":1,"a":2}'))
print("  validate_json duplicate keys dict[str,int]:", outcome(lambda: TypeAdapter(dict[str, int]).validate_json(b'{"a":1,"a":2}')))
print("  Inner.model_validate_json duplicate a:", outcome(lambda: Inner.model_validate_json(b'{"a":"x","a":1}')))
print("  from_json(b'[1, 2, {\"a\": \"tru', allow_partial=True):", from_json(b'[1, 2, {"a": "tru', allow_partial=True))
print("  from_json allow_partial='trailing-strings':", from_json(b'[1, 2, {"a": "tru', allow_partial="trailing-strings"))
print("  from_json(b'NaN') default:", outcome(lambda: from_json(b"NaN")), "| allow_inf_nan=False:", outcome(lambda: from_json(b"NaN", allow_inf_nan=False)))
print("  JsonValue.validate_json(b'[NaN]'):", outcome(lambda: jv.validate_json(b"[NaN]")))
print("  from_json float default 1.10 type:", type(from_json(b"1.10")).__name__)
deep = b"[" * 3000 + b"]" * 3000
print("  from_json 3000-deep:", outcome(lambda: from_json(deep)))
for depth in (200, 255, 256, 1000):
    try:
        from_json(b"[" * depth + b"]" * depth)
        print(f"  from_json depth {depth}: ok")
    except ValueError as exc:
        print(f"  from_json depth {depth}: ValueError {exc}")
print("  JsonValue.validate_json 3000-deep:", outcome(lambda: jv.validate_json(deep)))
print("  JsonValue.validate_python 3000-deep (python list):", outcome(lambda: jv.validate_python(json.loads(deep))))
hexpat = TypeAdapter(Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")])
print("  pydantic pattern ^[0-9a-f]{64}$ vs hash+'\\n' (rust-regex default):", outcome(lambda: hexpat.validate_python("a" * 64 + "\n")))
hexpy = TypeAdapter(Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")], config=ConfigDict(regex_engine="python-re"))
print("  same with regex_engine='python-re':", outcome(lambda: hexpy.validate_python("a" * 64 + "\n")))
print("  hide_input_in_errors:", TypeAdapter(Annotated[int, Field()], config=ConfigDict(hide_input_in_errors=True)).validate_python if False else outcome(lambda: TypeAdapter(Inner).validate_python({"a": "secret"})))
try:
    class Hidden(BaseModel):
        model_config = ConfigDict(hide_input_in_errors=True, strict=True)
        a: int

    Hidden.model_validate({"a": "s3cr3t"})
except ValidationError as exc:
    print("  hide_input_in_errors str(exc):", str(exc).replace("\n", " / ")[:200])
    print("  errors(include_input=False):", exc.errors(include_url=False, include_input=False))
