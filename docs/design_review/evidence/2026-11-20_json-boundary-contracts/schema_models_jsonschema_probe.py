"""Contract probe: jsonschema 4.26.0 / referencing 0.37.0 behaviour on Python values.

Run from the repository root:
    uv run python docs/design_review/evidence/2026-11-20_json-boundary-contracts/schema_models_jsonschema_probe.py

No network: remote retrieval is observed by replacing urllib.request.urlopen.
"""

from __future__ import annotations

import sys
import urllib.request
import warnings
from decimal import Decimal
from importlib.metadata import version

import jsonschema
from jsonschema import Draft7Validator, Draft202012Validator, FormatChecker, validators
from jsonschema.exceptions import ErrorTree, best_match, relevance
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7, DRAFT202012


def show(label, fn):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - probe records every outcome
        result = f"RAISES {type(exc).__name__}: {exc}"
    print(f"  {label}: {result}")


def valid(cls, schema, instance, **kw):
    return cls(schema, **kw).is_valid(instance)


print("versions:", {n: version(n) for n in ("jsonschema", "referencing", "hypothesis-jsonschema")})
print("python:", sys.version.split()[0])

print("\n[A1] type keyword on Python values (Draft7 and 2020-12 share the draft6 type checker)")
values = [1, 1.0, True, Decimal("1"), Decimal("1.0"), Decimal("1E+2"), Decimal("1.5"), 10**30]
for t in ("integer", "number"):
    for cls in (Draft7Validator, Draft202012Validator):
        row = {repr(v): valid(cls, {"type": t}, v) for v in values}
        print(f"  {cls.__name__} type={t}: {row}")

print("\n[A1] numeric keywords, Decimal vs float vs int instances and schema constants")
cases = [
    ("minimum 0.1 (float) vs Decimal('0.1')", {"minimum": 0.1}, Decimal("0.1")),
    ("minimum Decimal('0.1') vs 0.1 float", {"minimum": Decimal("0.1")}, 0.1),
    ("maximum 1 vs Decimal('1.0')", {"maximum": 1}, Decimal("1.0")),
    ("multipleOf 0.1 (float) vs 0.3 (float)", {"multipleOf": 0.1}, 0.3),
    ("multipleOf 0.1 (float) vs Decimal('0.3')", {"multipleOf": 0.1}, Decimal("0.3")),
    ("multipleOf Decimal('0.1') vs Decimal('0.3')", {"multipleOf": Decimal("0.1")}, Decimal("0.3")),
    ("multipleOf Decimal('0.1') vs 0.3 float", {"multipleOf": Decimal("0.1")}, 0.3),
    ("multipleOf 2 (int) vs Decimal('4.0')", {"multipleOf": 2}, Decimal("4.0")),
    ("multipleOf 2 (int) vs Decimal('4.5')", {"multipleOf": 2}, Decimal("4.5")),
    ("const 1 vs 1.0", {"const": 1}, 1.0),
    ("const 1 vs Decimal('1.0')", {"const": 1}, Decimal("1.0")),
    ("const 0.1 (float) vs Decimal('0.1')", {"const": 0.1}, Decimal("0.1")),
    ("const 1 vs True", {"const": 1}, True),
    ("enum [0.1] vs Decimal('0.1')", {"enum": [0.1]}, Decimal("0.1")),
    ("enum [Decimal('0.1')] vs Decimal('0.10')", {"enum": [Decimal("0.1")]}, Decimal("0.10")),
    ("uniqueItems [1, 1.0]", {"uniqueItems": True}, [1, 1.0]),
    ("uniqueItems [1, Decimal('1.0')]", {"uniqueItems": True}, [1, Decimal("1.0")]),
    ("uniqueItems [1, True]", {"uniqueItems": True}, [1, True]),
    ("uniqueItems [0.1, Decimal('0.1')]", {"uniqueItems": True}, [0.1, Decimal("0.1")]),
]
for label, schema, instance in cases:
    show(label, lambda s=schema, i=instance: valid(Draft7Validator, s, i))

print("\n[A1] Decimal as a first-class integer via TypeChecker.redefine + validators.extend")


def is_integer(checker, instance):
    if isinstance(instance, bool):
        return False
    if isinstance(instance, int):
        return True
    if isinstance(instance, float):
        return instance.is_integer()
    if isinstance(instance, Decimal):
        return instance.is_finite() and instance == instance.to_integral_value()
    return False


ExactDraft7 = validators.extend(
    Draft7Validator,
    type_checker=Draft7Validator.TYPE_CHECKER.redefine("integer", is_integer),
)
for v in (Decimal("1"), Decimal("1.0"), Decimal("1E+2"), Decimal("1.5"), True):
    show(f"ExactDraft7 integer {v!r}", lambda v=v: ExactDraft7({"type": "integer"}).is_valid(v))
show("ExactDraft7 class name / META_SCHEMA id", lambda: (ExactDraft7.__name__, ExactDraft7.META_SCHEMA["$schema"]))
show(
    "ExactDraft7 still crashes on multipleOf float schema with Decimal instance",
    lambda: ExactDraft7({"multipleOf": 0.1}).is_valid(Decimal("0.3")),
)

print("\n[A2] validator_for without $schema; evolve; check_schema")
show("validator_for({'type':'integer'})", lambda: validators.validator_for({"type": "integer"}).__name__)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    show(
        "validator_for unknown $schema",
        lambda: validators.validator_for({"$schema": "urn:unknown"}).__name__,
    )
    print("   warnings:", [str(w.category.__name__) for w in caught])
v7 = Draft7Validator({"type": "integer"})
show("evolve(schema=2020-12 schema) class", lambda: type(v7.evolve(schema={"$schema": "https://json-schema.org/draft/2020-12/schema"})).__name__)
show("evolve(schema without $schema) keeps class", lambda: type(v7.evolve(schema={"type": "string"})).__name__)
show("construction does not check schema: Draft7Validator({'type': 12}) constructed", lambda: Draft7Validator({"type": 12}) is not None)
show("...but validating with it", lambda: Draft7Validator({"type": 12}).is_valid(1))
show("check_schema({'type': 12})", lambda: Draft7Validator.check_schema({"type": 12}))

print("\n[A3] remote $ref with default registry vs Registry()")
calls = []
real_urlopen = urllib.request.urlopen


def fake_urlopen(request, *a, **k):
    calls.append(getattr(request, "full_url", request))
    raise OSError("probe: network refused")


urllib.request.urlopen = fake_urlopen
remote = {"$ref": "http://example.invalid/remote.json"}
show("default registry", lambda: Draft7Validator(remote).is_valid(1))
print("   urlopen calls:", calls)
calls.clear()
show("registry=Registry()", lambda: Draft7Validator(remote, registry=Registry()).is_valid(1))
print("   urlopen calls:", calls)
urllib.request.urlopen = real_urlopen
show(
    "metaschema $ref still resolvable with Registry() (SPECIFICATIONS combined)",
    lambda: Draft7Validator({"$ref": "http://json-schema.org/draft-07/schema#"}, registry=Registry()).is_valid({"type": "string"}),
)
shared = Resource.from_contents({"type": "integer"}, default_specification=DRAFT7)
reg = Registry().with_resources([("urn:corpus:int", shared)])
show("with_resources urn ref: 'x' / 3", lambda: (Draft7Validator({"$ref": "urn:corpus:int"}, registry=reg).is_valid("x"), Draft7Validator({"$ref": "urn:corpus:int"}, registry=reg).is_valid(3)))
crawled = (Resource.from_contents({"$id": "urn:corpus:s", "type": "string"}, default_specification=DRAFT202012) @ Registry()).crawl()
show("resource @ Registry() by $id: 1 / 's'", lambda: (Draft202012Validator({"$ref": "urn:corpus:s"}, registry=crawled).is_valid(1), Draft202012Validator({"$ref": "urn:corpus:s"}, registry=crawled).is_valid("s")))
show("Resource.from_contents without $schema or default_specification", lambda: Resource.from_contents({"type": "x"}))

print("\n[A4] diagnostics")
schema = {
    "type": "object",
    "properties": {
        "a": {"type": "integer", "minimum": 0},
        "b": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "c": {"oneOf": [{"type": "object", "required": ["k"]}, {"type": "array"}]},
    },
    "required": ["a", "z"],
    "additionalProperties": False,
}
instance = {"a": -5, "b": 12, "c": {"secret": "s3cr3t-value"}, "extra": "hidden-input"}
validator = Draft7Validator(schema)
errors = list(validator.iter_errors(instance))
for e in errors:
    print(
        "  error:",
        dict(
            validator=e.validator,
            validator_value=e.validator_value,
            absolute_path=list(e.absolute_path),
            json_path=e.json_path,
            absolute_schema_path=list(e.absolute_schema_path),
            context=[(c.validator, list(c.absolute_schema_path)) for c in e.context],
            message=e.message,
        ),
    )
bm = best_match(validator.iter_errors(instance))
print("  best_match:", bm.validator, bm.json_path, bm.message)
print("  sorted by relevance:", [e.validator for e in sorted(errors, key=relevance)])
tree = ErrorTree(validator.iter_errors(instance))
print("  ErrorTree total_errors:", tree.total_errors, "root keywords:", sorted(tree.errors), "children:", sorted(tree._contents))
print("  tree['a'].errors keys:", sorted(tree["a"].errors), "| tree['c'].errors['oneOf'].context size:", len(tree["c"].errors["oneOf"].context))
print("  output formats: hasattr(jsonschema, 'output')", hasattr(jsonschema, "output"), "| hasattr(validator,'iter_output')", hasattr(validator, "iter_output"))

print("\n[A5] format")
fmt_schema = {"type": "string", "format": "date-time"}
show("Draft7Validator default (no format_checker) 'nope'", lambda: Draft7Validator(fmt_schema).is_valid("nope"))
show("Draft7Validator FORMAT_CHECKER 'nope'", lambda: Draft7Validator(fmt_schema, format_checker=Draft7Validator.FORMAT_CHECKER).is_valid("nope"))
show("FormatChecker() 'nope'", lambda: Draft7Validator(fmt_schema, format_checker=FormatChecker()).is_valid("nope"))
show("FormatChecker() '2026-11-20T10:00:00Z'", lambda: Draft7Validator(fmt_schema, format_checker=FormatChecker()).is_valid("2026-11-20T10:00:00Z"))
show("FormatChecker() date-time without offset", lambda: Draft7Validator(fmt_schema, format_checker=FormatChecker()).is_valid("2026-11-20T10:00:00"))
print("  FormatChecker().checkers:", sorted(FormatChecker().checkers))
print("  Draft7 FORMAT_CHECKER:", sorted(Draft7Validator.FORMAT_CHECKER.checkers))
show("format on non-string 12 with checker", lambda: Draft7Validator(fmt_schema | {"type": ["string", "integer"]}, format_checker=FormatChecker()).is_valid(12))
show("unknown format 'corpus-thing'", lambda: Draft7Validator({"format": "corpus-thing"}, format_checker=FormatChecker()).is_valid("x"))

print("\n[A6] dialect cross-checking")
two020 = {
    "$defs": {"x": {"type": "integer"}},
    "type": "object",
    "properties": {
        "t": {"type": "array", "prefixItems": [{"type": "string"}, {"type": "integer"}], "items": False},
        "r": {"$ref": "#/$defs/x"},
        "n": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "d": {"dependentRequired": {"p": ["q"]}},
    },
    "unevaluatedProperties": False,
}
inst = {"t": ["s", 1], "r": "not-int", "n": None, "extra": 1}
inst_t_bad = {"t": [1, "s"]}
for cls in (Draft7Validator, Draft202012Validator):
    print(f"  {cls.__name__}: errors on 2020-12 schema:", sorted((str(e.validator), e.json_path, e.message[:60]) for e in cls(two020).iter_errors(inst)))
    print(f"  {cls.__name__}: errors on reversed tuple:", sorted((str(e.validator), e.json_path) for e in cls(two020).iter_errors(inst_t_bad)))
    show(f"{cls.__name__}.check_schema(2020-12 schema)", lambda c=cls: c.check_schema(two020))
draft7 = {
    "definitions": {"x": {"type": "integer"}},
    "type": "object",
    "properties": {
        "t": {"type": "array", "items": [{"type": "string"}, {"type": "integer"}], "additionalItems": False},
        "r": {"$ref": "#/definitions/x"},
        "dep": {"dependencies": {"p": ["q"]}},
    },
}
inst7 = {"t": [1, "s", "extra"], "r": "x", "dep": {"p": 1}}
for cls in (Draft7Validator, Draft202012Validator):
    show(f"{cls.__name__}: errors on Draft7 schema", lambda c=cls: sorted((str(e.validator), e.json_path) for e in c(draft7).iter_errors(inst7)))
    show(f"{cls.__name__}.check_schema(Draft7 schema)", lambda c=cls: c.check_schema(draft7))
show("$ref sibling keywords in Draft7 are ignored", lambda: Draft7Validator({"definitions": {"x": {}}, "$ref": "#/definitions/x", "type": "integer"}).is_valid("s"))
show("$ref sibling keywords in 2020-12 apply", lambda: Draft202012Validator({"$defs": {"x": {}}, "$ref": "#/$defs/x", "type": "integer"}).is_valid("s"))

print("\n[A7] unknown and x- keywords; custom keyword")
show("unknown keyword ignored", lambda: Draft7Validator({"x-corpus": {"a": 1}, "bogus": 3, "type": "string"}).is_valid("s"))
show("check_schema with unknown keyword", lambda: Draft7Validator.check_schema({"x-corpus": 1, "bogus": 3}))


def exact_decimal(validator, value, instance, schema):
    if value and isinstance(instance, float):
        yield jsonschema.ValidationError("float not admitted where exact decimal is required")


WithKeyword = validators.extend(Draft7Validator, validators={"x-exact": exact_decimal})
show("custom keyword x-exact rejects float", lambda: [e.message for e in WithKeyword({"x-exact": True}).iter_errors(1.5)])
show("custom keyword accepts Decimal", lambda: WithKeyword({"x-exact": True}).is_valid(Decimal("1.5")))

print("\n[A8] hypothesis-jsonschema on a 2020-12 prefixItems schema")
try:
    from hypothesis import given, settings
    from hypothesis_jsonschema import from_schema

    produced = []
    tuple_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "array", "prefixItems": [{"type": "string"}, {"type": "integer"}], "items": False, "minItems": 2}

    @settings(max_examples=20, database=None)
    @given(from_schema(tuple_schema))
    def collect(value):
        produced.append(value)

    collect()
    ok = [Draft202012Validator(tuple_schema).is_valid(v) for v in produced]
    print("  examples valid under Draft202012Validator:", sum(ok), "/", len(ok), "sample:", produced[:3])
except Exception as exc:  # noqa: BLE001
    print("  RAISES", type(exc).__name__, str(exc)[:300])
