"""Differential probe: Python jsonschema 4.26.0 versus pg_jsonschema 0.3.4 (Rust jsonschema 0.37.1).

Run from the repository root:
    uv run python docs/design_review/evidence/2026-11-20_json-boundary-contracts/schema_models_pg_probe.py

PostgreSQL access is read-only: each case is one SELECT through
`psql -p 5434 corpus_structure_dev` with PGOPTIONS='-c default_transaction_read_only=on'.
The statements are also written to schema_models_pg.sql next to this script.
Python columns:
  py7_float   Draft7Validator, schema and instance decoded with stdlib json (floats)
  py7_dec     Draft7Validator, schema stdlib json, instance rapidjson NM_DECIMAL (the exact-wire decoder)
  pyauto      validator_for(schema) (2020-12 when $schema is absent), stdlib json
All Python validators use registry=Registry() (no retrieval).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import rapidjson
from jsonschema import Draft7Validator, validators
from referencing import Registry

HERE = Path(__file__).parent
D7 = "http://json-schema.org/draft-07/schema#"

CASES = [
    ("int_1.0", '{"type":"integer"}', "1.0"),
    ("int_1e2", '{"type":"integer"}', "1e2"),
    ("int_-0.0", '{"type":"integer"}', "-0.0"),
    ("int_bigint", '{"type":"integer"}', "123456789012345678901234567890"),
    ("int_near1", '{"type":"integer"}', "1.00000000000000000001"),
    ("max1_near1", '{"maximum":1}', "1.00000000000000000001"),
    ("min0.1_0.1", '{"minimum":0.1}', "0.1"),
    ("mult0.1_0.3", '{"multipleOf":0.1}', "0.3"),
    ("mult0.01_0.07", '{"multipleOf":0.01}', "0.07"),
    ("mult2_4.0", '{"multipleOf":2}', "4.0"),
    ("const1_1.0", '{"const":1}', "1.0"),
    ("const1.0_1", '{"const":1.0}', "1"),
    ("const0.1_0.10", '{"const":0.1}', "0.10"),
    ("enum_1.0", '{"enum":[1,"a"]}', "1.0"),
    ("unique_1_1.0", '{"uniqueItems":true}', "[1,1.0]"),
    ("unique_1_true", '{"uniqueItems":true}', "[1,true]"),
    ("pat_dollar_newline", '{"pattern":"^abc$"}', '"abc\\n"'),
    ("pat_digit_arabic", '{"pattern":"^\\\\d+$"}', '"\\u0661\\u0662"'),
    ("pat_word_eacute", '{"pattern":"^\\\\w$"}', '"\\u00e9"'),
    ("pat_lookahead", '{"pattern":"^(?=.*x).+$"}', '"axb"'),
    ("pat_backslash_Z", '{"pattern":"^a\\\\Z"}', '"a"'),
    ("pat_named_group", '{"pattern":"^(?P<n>a)$"}', '"a"'),
    ("pat_posix_class", '{"pattern":"^[[:alpha:]]+$"}', '"abc"'),
    ("pat_unanchored", '{"pattern":"b"}', '"abc"'),
    ("maxlen_astral", '{"maxLength":1}', '"\\ud83d\\ude00"'),
    ("fmt_dt_bad_noschema", '{"format":"date-time"}', '"nope"'),
    ("fmt_dt_bad_d7", '{"$schema":"' + D7 + '","format":"date-time"}', '"nope"'),
    ("fmt_dt_ok_d7", '{"$schema":"' + D7 + '","format":"date-time"}', '"2026-11-20T10:00:00Z"'),
    ("fmt_uuid_bad_noschema", '{"format":"uuid"}', '"nope"'),
    ("prefixItems_noschema", '{"prefixItems":[{"type":"string"}]}', "[1]"),
    ("prefixItems_d7", '{"$schema":"' + D7 + '","prefixItems":[{"type":"string"}]}', "[1]"),
    ("itemsarray_noschema", '{"items":[{"type":"string"}]}', "[1]"),
    ("itemsarray_d7", '{"$schema":"' + D7 + '","items":[{"type":"string"}]}', "[1]"),
    ("additionalItems_noschema", '{"items":[{"type":"string"}],"additionalItems":false}', '["a",2]'),
    ("addlProps_false", '{"properties":{"a":{}},"additionalProperties":false}', '{"a":1,"b":2}'),
    ("ref_definitions_noschema", '{"definitions":{"x":{"type":"string"}},"properties":{"a":{"$ref":"#/definitions/x"}}}', '{"a":1}'),
    ("ref_defs_d7", '{"$schema":"' + D7 + '","$defs":{"x":{"type":"string"}},"properties":{"a":{"$ref":"#/$defs/x"}}}', '{"a":1}'),
    ("ref_sibling_noschema", '{"definitions":{"x":{}},"$ref":"#/definitions/x","type":"integer"}', '"s"'),
    ("ref_sibling_d7", '{"$schema":"' + D7 + '","definitions":{"x":{}},"$ref":"#/definitions/x","type":"integer"}', '"s"'),
    ("if_then_else", '{"if":{"type":"integer"},"then":{"minimum":0},"else":{"type":"string"}}', "-1"),
    ("bool_schema_false", "false", "1"),
    ("bool_schema_true", "true", "1"),
    ("bool_subschema_false", '{"properties":{"a":false}}', '{"a":1}'),
    ("dependentRequired_noschema", '{"dependentRequired":{"p":["q"]}}', '{"p":1}'),
    ("dependentRequired_d7", '{"$schema":"' + D7 + '","dependentRequired":{"p":["q"]}}', '{"p":1}'),
    ("dependencies_noschema", '{"dependencies":{"p":["q"]}}', '{"p":1}'),
    ("unevaluatedProps_noschema", '{"properties":{"a":{}},"unevaluatedProperties":false}', '{"a":1,"b":2}'),
    ("unknown_keyword", '{"x-corpus":1,"bogus":{"a":1},"type":"string"}', '"s"'),
    ("dup_key_last_string", '{"properties":{"a":{"type":"string"}}}', '{"a":1,"a":"x"}'),
    ("dup_key_last_int", '{"properties":{"a":{"type":"string"}}}', '{"a":"x","a":1}'),
    ("invalid_schema_type12", '{"type":12}', "1"),
    ("remote_ref", '{"$ref":"http://127.0.0.1:9/x.json"}', "1"),
    ("unknown_dialect", '{"$schema":"urn:unknown","type":"string"}', "1"),
    # Shapes taken from the installed SQL schemas (catalog survey in the raw output header).
    ("installed_hash_pattern_newline", '{"$schema":"' + D7 + '","type":"string","pattern":"^[0-9a-f]{64}$"}', '"' + "a" * 64 + '\\n"'),
    ("installed_format_binary_d7", '{"$schema":"' + D7 + '","type":"string","format":"binary"}', '"anything"'),
    ("installed_decimal_text_pattern", '{"$schema":"' + D7 + '","type":"string","pattern":"^[+-]?[0-9]+$"}', '"12\\n"'),
]


def py_result(cls_factory, schema_text, instance_text, decoder):
    try:
        schema = json.loads(schema_text)
        instance = decoder(instance_text)
        cls = cls_factory(schema)
        return "t" if cls(schema, registry=Registry()).is_valid(instance) else "f"
    except Exception as exc:  # noqa: BLE001 - record every outcome
        return f"ERR:{type(exc).__name__}"


def dec_decoder(text):
    return rapidjson.loads(text, number_mode=rapidjson.NM_DECIMAL, allow_nan=False)


def lit(text):
    assert "$j$" not in text
    return f"$j${text}$j$"


def sql_for(schema_text, instance_text):
    return (
        f"SELECT json_matches_schema({lit(schema_text)}::json, {lit(instance_text)}::json),"
        f" jsonb_matches_schema({lit(schema_text)}::json, {lit(instance_text)}::jsonb),"
        f" jsonschema_validation_errors({lit(schema_text)}::json, {lit(instance_text)}::json);"
    )


def pg(statement):
    env = dict(os.environ, PGOPTIONS="-c default_transaction_read_only=on")
    proc = subprocess.run(
        ["psql", "-X", "-p", "5434", "corpus_structure_dev", "-At", "-F", "\t", "-c", statement],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if proc.returncode:
        return ("ERR", "ERR", proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "error")
    parts = proc.stdout.rstrip("\n").split("\t")
    return tuple(parts) if len(parts) == 3 else ("?", "?", proc.stdout.strip())


version = subprocess.run(
    ["psql", "-X", "-p", "5434", "corpus_structure_dev", "-At", "-c",
     "SELECT extversion FROM pg_extension WHERE extname='pg_jsonschema'"],
    capture_output=True, text=True, check=True,
).stdout.strip()
print("pg_jsonschema extversion:", version)
statements = []
header = f"{'case':28} py7_float py7_dec pyauto | pg_json pg_jsonb | pg_errors"
print(header)
disagreements = []
for name, schema_text, instance_text in CASES:
    stmt = sql_for(schema_text, instance_text)
    statements.append(f"-- {name}\n{stmt}")
    p7f = py_result(lambda s: Draft7Validator, schema_text, instance_text, json.loads)
    p7d = py_result(lambda s: Draft7Validator, schema_text, instance_text, dec_decoder)
    pau = py_result(lambda s: validators.validator_for(s), schema_text, instance_text, json.loads)
    pj, pjb, perr = pg(stmt)
    print(f"{name:28} {p7f:9} {p7d:7} {pau:6} | {pj:7} {pjb:8} | {perr[:150]}")
    if len({p7f, p7d, pau, pj, pjb}) > 1:
        disagreements.append(name)
print("\ncases where any column differs:", disagreements)
(HERE / "schema_models_pg.sql").write_text(
    "-- Generated by schema_models_pg_probe.py; read-only SELECTs, one per case.\n"
    "-- psql -X -p 5434 corpus_structure_dev with PGOPTIONS='-c default_transaction_read_only=on'\n\n"
    + "\n\n".join(statements)
    + "\n"
)
