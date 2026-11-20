"""rapidjson.Validator (python-rapidjson 1.25, bundled RapidJSON master 24b5e7a) against
jsonschema Draft7Validator, on synthetic cases and on the project's installed wire contracts.

Reads project code only (wire_contracts); no database, no writes. Run from the repository root:

    uv run python -I docs/design_review/evidence/2026-11-20_json-boundary-contracts/rapidjson_validator_probe.py
"""

import collections
import json
import sys
from decimal import Decimal

import rapidjson
from jsonschema import Draft7Validator


def rj(schema, instance_text):
    try:
        validator = rapidjson.Validator(json.dumps(schema) if not isinstance(schema, str) else schema)
    except Exception as exc:  # noqa: BLE001
        return f"schema raise {type(exc).__name__}: {exc}"
    try:
        validator(instance_text)
        return "valid"
    except rapidjson.ValidationError as exc:
        return f"INVALID {exc.args}"
    except Exception as exc:  # noqa: BLE001
        return f"raise {type(exc).__name__}: {exc}"


def js(schema, instance_text, parse=json.loads):
    try:
        errors = list(Draft7Validator(schema).iter_errors(parse(instance_text)))
    except Exception as exc:  # noqa: BLE001
        return f"raise {type(exc).__name__}: {exc}"
    return "valid" if not errors else f"INVALID {[e.validator for e in errors]}"


print("rapidjson", rapidjson.__version__, "| python", sys.version.split()[0])

print("\n== call contract")
v = rapidjson.Validator('{"type":"object","required":["a","b"],"properties":{"a":{"type":"string"}}}')
for arg in ('{"a":1}', b'{"a":"x","b":1}', bytearray(b"{}"), {"a": "x"}, '{"a":1', "[1]\x00junk"):
    try:
        print(f"  call({arg!r}):", v(arg) or "valid")
    except Exception as exc:  # noqa: BLE001
        print(f"  call({arg!r}): {type(exc).__name__} args={exc.args}")
print("  Validator(dict):", rj.__code__ and (lambda: None)() or "", end="")
try:
    rapidjson.Validator({"type": "string"})
except Exception as exc:  # noqa: BLE001
    print(f"{type(exc).__name__}: {exc}")
print("  first error only: instance violates 'type' of a and 'required' b ->", rj(
    {"type": "object", "required": ["b"], "properties": {"a": {"type": "string"}}}, '{"a":1}'),
    "| jsonschema", js({"type": "object", "required": ["b"], "properties": {"a": {"type": "string"}}}, '{"a":1}'))

print("\n== schema checking (invalid schemas are not reported)")
for schema in ({"type": 12}, {"minimum": "x"}, {"required": "a"}, {"$ref": "#/definitions/missing"},
               {"$ref": "http://example.com/s.json"}, {"properties": {"a": {"$ref": "#/nowhere"}}},
               {"$schema": "http://json-schema.org/draft-07/schema#", "type": "string"},
               {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "string"},
               {"$schema": "urn:unknown", "type": "string"}):
    print(f"  {json.dumps(schema):72} on 1 -> rapidjson {rj(schema, '1')} | jsonschema", end=" ")
    try:
        Draft7Validator.check_schema(schema)
        print("check_schema ok")
    except Exception as exc:  # noqa: BLE001
        print(f"check_schema {type(exc).__name__}")

print("\n== keywords beyond Draft 4 (and Draft 4 controls)")
cases = [
    ("const", {"const": "a"}, '"b"'),
    ("const object", {"const": {"k": 1}}, '{"k":2}'),
    ("contains", {"type": "array", "contains": {"type": "string"}}, "[1]"),
    ("propertyNames", {"propertyNames": {"pattern": "^a"}}, '{"b":1}'),
    ("if/then", {"if": {"type": "string"}, "then": {"minLength": 2}}, '"a"'),
    ("if/else", {"if": {"type": "string"}, "else": {"type": "null"}}, "1"),
    ("exclusiveMinimum number", {"exclusiveMinimum": 5}, "5"),
    ("exclusiveMaximum number", {"exclusiveMaximum": 5}, "6"),
    ("exclusiveMinimum bool (Draft 4)", {"minimum": 5, "exclusiveMinimum": True}, "5"),
    ("root schema false", False, "1"),
    ("root schema true", True, "1"),
    ("property schema false", {"properties": {"a": False}}, '{"a":1}'),
    ("items false", {"items": False}, "[1]"),
    ("additionalProperties false (D4)", {"additionalProperties": False, "properties": {"a": {}}}, '{"b":1}'),
    ("additionalItems schema (D4)", {"items": [{"type": "integer"}], "additionalItems": {"type": "string"}}, "[1, 2]"),
    ("anyOf branch false", {"anyOf": [False, {"type": "string"}]}, "1"),
    ("$ref definitions", {"definitions": {"s": {"type": "string"}}, "$ref": "#/definitions/s"}, "1"),
    ("$ref sibling ignored (D7)", {"definitions": {"s": {}}, "$ref": "#/definitions/s", "type": "string"}, "1"),
    ("format email", {"format": "email"}, '"not-an-email"'),
    ("format date-time", {"format": "date-time"}, '"yesterday"'),
    ("examples/$comment ignored", {"examples": [1], "$comment": "x", "type": "string"}, '"s"'),
    ("contentMediaType", {"contentMediaType": "application/json", "contentEncoding": "base64"}, '"%%%"'),
    ("dependencies schema (D4)", {"dependencies": {"a": {"required": ["b"]}}}, '{"a":1}'),
    ("unknown keyword", {"frobnicate": True, "type": "string"}, '"s"'),
    ("enum mixed", {"enum": ["a", 1, None]}, '"b"'),
]
for label, schema, instance in cases:
    print(f"  {label:34} {instance:10} rapidjson {rj(schema, instance):60} | jsonschema {js(schema, instance)}")

print("\n== number semantics")
numbers = [
    ("integer 1.0", {"type": "integer"}, "1.0"),
    ("integer 1e2", {"type": "integer"}, "1e2"),
    ("integer 10**30", {"type": "integer"}, str(10**30)),
    ("integer 2**64", {"type": "integer"}, str(2**64)),
    ("maximum 10**20 vs 10**20+1", {"maximum": 10**20}, str(10**20 + 1)),
    ("maximum 2**53 vs 2**53+1", {"maximum": 2**53}, str(2**53 + 1)),
    ("maximum 0.1 vs 0.1000000000000000000001", {"maximum": 0.1}, "0.1000000000000000000001"),
    ("minimum 0.3 vs 0.29999999999999999999", {"minimum": 0.3}, "0.29999999999999999999"),
    ("multipleOf 0.1 vs 0.3", {"multipleOf": 0.1}, "0.3"),
    ("multipleOf 0.01 vs 19.99", {"multipleOf": 0.01}, "19.99"),
    ("multipleOf 1 vs 10**30", {"multipleOf": 1}, str(10**30)),
    ("enum [1] vs 1.0", {"enum": [1]}, "1.0"),
    ("enum [1.0] vs 1", {"enum": [1.0]}, "1"),
    ("enum [10**20] vs 10**20+1", {"enum": [10**20]}, str(10**20 + 1)),
    ("enum [0.1] vs 0.1000000000000000000001", {"enum": [0.1]}, "0.1000000000000000000001"),
    ("uniqueItems [1, 1.0]", {"uniqueItems": True}, "[1, 1.0]"),
    ("uniqueItems [10**20, 10**20+1]", {"uniqueItems": True}, f"[{10**20}, {10**20 + 1}]"),
    ("uniqueItems objects key order", {"uniqueItems": True}, '[{"a":1,"b":2},{"b":2,"a":1}]'),
    ("const 1 vs 1.0", {"const": 1}, "1.0"),
]
decimal_parse = lambda text: json.loads(text, parse_float=Decimal)  # noqa: E731
for label, schema, instance in numbers:
    print(f"  {label:42} rapidjson {rj(schema, instance):58} | jsonschema(float) {js(schema, instance):24}"
          f" | jsonschema(Decimal floats) {js(schema, instance, decimal_parse)}")

print("\n== strings: pattern dialect and length")
strings = [
    ("pattern unanchored 'a' on 'ba'", {"pattern": "a"}, '"ba"'),
    ("pattern ^\\d+$", {"pattern": "^\\d+$"}, '"12"'),
    ("pattern \\w+ on é", {"pattern": "^\\w+$"}, '"é"'),
    ("pattern [a-z]{2,3}", {"pattern": "^[a-z]{2,3}$"}, '"abcd"'),
    ("pattern lookahead", {"pattern": "^(?=a)a$"}, '"a"'),
    ("pattern (?i)", {"pattern": "(?i)A"}, '"a"'),
    ("pattern \\p{L}", {"pattern": "^\\p{L}$"}, '"a"'),
    ("pattern non-greedy", {"pattern": "^a+?$"}, '"aa"'),
    ("pattern backref", {"pattern": "^(a)\\1$"}, '"aa"'),
    ("pattern . on astral", {"pattern": "^.$"}, '"😀"'),
    ("pattern \\s", {"pattern": "^\\s$"}, '" "'),
    ("pattern \\S+", {"pattern": "^\\S+$"}, '"ab"'),
    ("pattern [^/]+", {"pattern": "^[^/]+$"}, '"a/b"'),
    ("pattern \\.", {"pattern": "^a\\.b$"}, '"a.b"'),
    ("pattern \\u escapes", {"pattern": "^\\u0041$"}, '"A"'),
    ("pattern invalid regex", {"pattern": "("}, '"x"'),
    ("maxLength 1 on astral", {"maxLength": 1}, '"😀"'),
    ("maxLength 1 on é", {"maxLength": 1}, '"é"'),
    ("patternProperties", {"patternProperties": {"^x-": {"type": "string"}}}, '{"x-a":1}'),
]
for label, schema, instance in strings:
    print(f"  {label:34} {instance:8} rapidjson {rj(schema, instance):52} | jsonschema {js(schema, instance)}")

# ----------------------------------------------------------------------------- wire set
print("\n== installed wire contracts (corpus_structure.semantic.data_operation_wire.wire_contracts)")
from corpus_structure.semantic.data_operation_wire import wire_contracts  # noqa: E402
from corpus_structure.semantic.identity import canonical_bytes  # noqa: E402

contracts = wire_contracts()
SCHEMA_MAP = ("properties", "patternProperties", "definitions", "dependencies")
SCHEMA_ONE = ("additionalProperties", "additionalItems", "items", "contains", "propertyNames", "not",
              "if", "then", "else")
SCHEMA_LIST = ("allOf", "anyOf", "oneOf", "items")
counts = collections.Counter()
bool_schemas = collections.Counter()
numeric_exclusive = 0
formats = collections.Counter()
patterns = collections.Counter()
seen_nodes = set()


def walk(node, where):
    global numeric_exclusive
    if isinstance(node, bool):
        bool_schemas[str(node)] += 1
        return
    if not isinstance(node, dict):
        return
    key = id(node)
    if key in seen_nodes:
        return
    seen_nodes.add(key)
    for name, value in node.items():
        counts[name] += 1
        if name in ("exclusiveMinimum", "exclusiveMaximum") and not isinstance(value, bool):
            numeric_exclusive += 1
        if name == "format":
            formats[value] += 1
        if name == "pattern":
            patterns[value] += 1
    for name in SCHEMA_MAP:
        if isinstance(node.get(name), dict):
            for child_name, child in node[name].items():
                if name == "dependencies" and isinstance(child, list):
                    continue
                walk(child, f"{where}/{name}/{child_name}")
    for name in SCHEMA_ONE:
        if name in node and not isinstance(node[name], list):
            walk(node[name], f"{where}/{name}")
    for name in SCHEMA_LIST:
        if isinstance(node.get(name), list):
            for index, child in enumerate(node[name]):
                walk(child, f"{where}/{name}/{index}")


# The contracts embed the same definitions repeatedly; count each distinct definition once.
distinct = {}
for operation, directions in contracts.items():
    for direction, schema in directions.items():
        for name, definition in schema.get("definitions", {}).items():
            distinct.setdefault(name, definition)
        walk({k: v for k, v in schema.items() if k != "definitions"}, f"{operation}/{direction}")
for name, definition in distinct.items():
    walk(definition, f"#/definitions/{name}")
print(f"  operations {len(contracts)}, contract schemas {sum(len(d) for d in contracts.values())},"
      f" distinct definitions {len(distinct)}")
BEYOND_DRAFT4 = {"const", "contains", "propertyNames", "if", "then", "else", "examples", "$comment",
                 "contentMediaType", "contentEncoding", "readOnly", "writeOnly", "$id"}
print("  keyword counts (schema positions, distinct definitions counted once):")
for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
    flag = "   <-- beyond Draft 4" if name in BEYOND_DRAFT4 else ""
    print(f"    {name:24} {count:6}{flag}")
print("  numeric exclusiveMinimum/exclusiveMaximum (Draft 6+ form):", numeric_exclusive)
print("  boolean subschemas (all False; located separately: 211 additionalProperties, 10 additionalItems, 1 else):", dict(bool_schemas))
print("  format values:", dict(formats))
print("  distinct patterns:", len(patterns), sorted(patterns)[:12])

print("\n  rapidjson compiles every contract schema:")
compiled = {}
failures = []
for operation, directions in contracts.items():
    for direction, schema in directions.items():
        try:
            compiled[operation, direction] = rapidjson.Validator(canonical_bytes(schema))
        except Exception as exc:  # noqa: BLE001
            failures.append((operation, direction, f"{type(exc).__name__}: {exc}"))
print(f"    compiled {len(compiled)}, failed {len(failures)} {failures[:3]}")

print("\n  real-contract laxity: hypothesis-jsonschema instances, then one beyond-Draft-4 mutation")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis_jsonschema import from_schema  # noqa: E402

const_definitions = [name for name, d in distinct.items()
                     if isinstance(d, dict) and any(isinstance(p, dict) and "const" in p
                                                     for p in d.get("properties", {}).values())]
print("    definitions with a const-valued property:", len(const_definitions), const_definitions[:6])
agree = collections.Counter()
mutations = []
rejected = []
for name in const_definitions[:8]:
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", "$ref": f"#/definitions/{name}",
              "definitions": {**distinct}}
    validator_rj = rapidjson.Validator(canonical_bytes(schema))
    validator_js = Draft7Validator(schema)
    examples = []

    @settings(max_examples=15, deadline=None, database=None, suppress_health_check=list(HealthCheck))
    @given(from_schema(schema))
    def collect(instance):
        examples.append(instance)

    try:
        collect()
    except Exception as exc:  # noqa: BLE001
        print(f"    {name}: hypothesis-jsonschema could not generate ({type(exc).__name__}: {str(exc)[:90]})")
        continue
    for instance in examples:
        text = rapidjson.dumps(instance, ensure_ascii=False)
        try:
            validator_rj(text)
            agree["valid instance accepted by rapidjson"] += 1
        except rapidjson.ValidationError as exc:
            agree[f"valid instance REJECTED by rapidjson {exc.args[0]}"] += 1
            if len(rejected) < 4:
                pointer = exc.args[2].lstrip("#").split("/")[1:]
                value = instance
                for part in pointer:
                    value = value[int(part)] if isinstance(value, list) else value[part]
                rejected.append((name, exc.args, repr(value)[:80]))
    if examples:
        instance = dict(examples[0])
        const_property = next(p for p, s in distinct[name]["properties"].items()
                              if isinstance(s, dict) and "const" in s)
        instance[const_property] = "__not_the_const__"
        text = json.dumps(instance)
        try:
            validator_rj(text)
            rj_verdict = "valid"
        except rapidjson.ValidationError as exc:
            rj_verdict = f"INVALID {exc.args}"
        js_errors = sorted({e.validator for e in validator_js.iter_errors(instance)})
        mutations.append((name, const_property, rj_verdict, js_errors))
print("    generated-instance agreement:", dict(agree))
for item in rejected:
    print("    rejected valid instance:", item)
for name, prop, rj_verdict, js_errors in mutations:
    print(f"    mutate {name}.{prop} -> rapidjson {rj_verdict} | jsonschema errors {js_errors}")
