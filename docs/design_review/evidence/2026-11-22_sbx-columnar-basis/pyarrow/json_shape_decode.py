"""Probe E/B: can pyarrow.json decode + shape-check documents in one native pass?

Checks pyarrow.json.read_json with an explicit schema against shape defects that a
json.loads + pydantic/jsonschema pass would catch, and a route for a column of JSON text
(one document per line). Also checks what the canonical JSON/UUID extension types validate.
Synthetic data only.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/pyarrow/json_shape_decode.py
"""

from __future__ import annotations

import json
import sys

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.json as pj

TOKEN = pa.struct([pa.field("text", pa.string(), nullable=False), pa.field("start", pa.int32()), pa.field("stop", pa.int32())])
SCHEMA = pa.schema(
    [
        pa.field("block", pa.string(), nullable=False),
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("tokens", pa.list_(TOKEN)),
        pa.field("amount", pa.decimal128(18, 3)),
        pa.field("note", pa.string()),
    ]
)
GOOD = {"block": "b1", "ordinal": 1, "tokens": [{"text": "é", "start": 0, "stop": 1}], "amount": 1.5, "note": None}


def read(lines: list[str], behaviour: str = "error"):
    data = ("\n".join(lines) + "\n").encode()
    opts = pj.ParseOptions(explicit_schema=SCHEMA, unexpected_field_behavior=behaviour)
    try:
        table = pj.read_json(pa.BufferReader(data), parse_options=opts)
        return {"ok": True, "rows": table.to_pylist()}
    except Exception as exc:  # noqa: BLE001 - recording the surfaced error
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def variant(**changes):
    doc = json.loads(json.dumps(GOOD))
    for key, value in changes.items():
        if value is ...:
            doc.pop(key)
        else:
            doc[key] = value
    return json.dumps(doc, ensure_ascii=False)


cases = {
    "good": read([json.dumps(GOOD, ensure_ascii=False)]),
    "extra_field_error_policy": read([variant(extra=1)]),
    "extra_field_ignore_policy": read([variant(extra=1)], "ignore"),
    "missing_non_nullable_field": read([variant(ordinal=...)]),
    "explicit_null_non_nullable": read([variant(ordinal=None)]),
    "absent_vs_null_nullable": read([variant(note=...), variant(note=None)]),
    "string_for_int": read([variant(ordinal="1")]),
    "float_for_int": read([variant(ordinal=1.0)]),
    "int_overflow_int64": read([variant(ordinal=2**63)]),
    "int32_overflow_in_nested": read([variant(tokens=[{"text": "a", "start": 2**31, "stop": 1}])]),
    "missing_nested_non_nullable": read([variant(tokens=[{"start": 0, "stop": 1}])]),
    "extra_nested_field": read([variant(tokens=[{"text": "a", "start": 0, "stop": 1, "x": 2}])]),
    "decimal_from_number_excess_scale": read([variant(amount=1.23456)]),
    "decimal_from_string": read([variant(amount="1.5")]),
    "duplicate_key": read(['{"block":"b1","block":"b2","ordinal":1,"tokens":[],"amount":1,"note":null}']),
    "error_in_second_of_three_rows": read([variant(), variant(ordinal="x"), variant()]),
    "top_level_array_document": read([json.dumps([GOOD])]),
}

# column of JSON text -> one native decode pass via newline-joined buffer
texts = pa.array([variant(ordinal=i) for i in range(5)])
joined = pc.binary_join(pa.ListArray.from_arrays([0, len(texts)], texts), "\n")[0].as_buffer()
table = pj.read_json(pa.BufferReader(joined), parse_options=pj.ParseOptions(explicit_schema=SCHEMA))
cases["column_of_json_text_rows"] = table.num_rows

# canonical extension types: what do they validate?
ext = {}
for label, build in {
    "json_accepts_invalid_text": lambda: pa.array(["{not json"], pa.json_()),
    "uuid_from_16_bytes": lambda: pa.ExtensionArray.from_storage(pa.uuid(), pa.array([b"0" * 16], pa.binary(16))),
}.items():
    try:
        arr = build()
        arr.validate(full=True)
        ext[label] = f"accepted: type={arr.type}"
    except Exception as exc:  # noqa: BLE001
        ext[label] = f"rejected: {type(exc).__name__}: {exc}"
cases["canonical_extension_types"] = ext

json.dump({"python": sys.version.split()[0], "pyarrow": pa.__version__, "cases": cases},
          sys.stdout, indent=2, default=str, ensure_ascii=False)
print()
