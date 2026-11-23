"""DuckDB 2.0.0 JSON ingestion strictness: read_json with an explicit `columns` schema and
json_transform_strict as one-pass decode plus shape validation.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_json_ingest.py
Synthetic files in a temporary directory; no repository data.
"""

import json
import tempfile
from pathlib import Path

import duckdb

COLUMNS = {"id": "BIGINT", "text": "VARCHAR", "span": "STRUCT(start BIGINT, \"end\" BIGINT)", "tags": "VARCHAR[]"}
STRUCTURE = json.dumps({"id": "BIGINT", "text": "VARCHAR", "span": {"start": "BIGINT", "end": "BIGINT"}, "tags": ["VARCHAR"]})

CASES = {
    "ok": '{"id":1,"text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "extra_key": '{"id":1,"text":"a","span":{"start":0,"end":1},"tags":["x"],"extra":1}',
    "extra_nested_key": '{"id":1,"text":"a","span":{"start":0,"end":1,"zz":2},"tags":["x"]}',
    "missing_key": '{"id":1,"text":"a","span":{"start":0,"end":1}}',
    "explicit_null": '{"id":1,"text":"a","span":{"start":0,"end":1},"tags":null}',
    "numeric_string": '{"id":"7","text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "nonnumeric_string": '{"id":"x","text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "float_into_bigint": '{"id":1.5,"text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "bool_into_bigint": '{"id":true,"text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "int_into_varchar": '{"id":1,"text":5,"span":{"start":0,"end":1},"tags":["x"]}',
    "nested_wrong": '{"id":1,"text":"a","span":{"start":"q","end":1},"tags":["x"]}',
    "duplicate_key": '{"id":1,"id":2,"text":"a","span":{"start":0,"end":1},"tags":["x"]}',
    "malformed": '{"id":1,"text":"a",',
}

con = duckdb.connect(config={"threads": 1})
print("duckdb", duckdb.__version__)


def show(label, fn):
    try:
        print(f"  {label:<18} -> {fn()}")
    except duckdb.Error as e:
        print(f"  {label:<18} -> ERROR {type(e).__name__}: {str(e).splitlines()[0][:150]}")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    print("A1 read_json(columns=..., format='newline_delimited', ignore_errors=false), one case per file")
    for name, line in CASES.items():
        path = root / f"{name}.ndjson"
        path.write_text(line + "\n")
        show(name, lambda p=path: con.execute(
            "SELECT * FROM read_json(?, columns=?, format='newline_delimited')", [str(p), COLUMNS]).fetchall())

    print("A2 same files with ignore_errors=true")
    for name in ("extra_key", "nonnumeric_string", "float_into_bigint", "nested_wrong", "malformed"):
        path = root / f"{name}.ndjson"
        show(name, lambda p=path: con.execute(
            "SELECT * FROM read_json(?, columns=?, format='newline_delimited', ignore_errors=true)", [str(p), COLUMNS]).fetchall())

    print("A3 json_transform_strict(text, structure) per line")
    for name, line in CASES.items():
        show(name, lambda line=line: con.execute("SELECT json_transform_strict(?, ?)", [line, STRUCTURE]).fetchall())

    print("A4 json_transform (non-strict) per line")
    for name in ("extra_key", "missing_key", "nonnumeric_string", "float_into_bigint", "nested_wrong"):
        show(name, lambda line=CASES[name]: con.execute("SELECT json_transform(?, ?)", [line, STRUCTURE]).fetchall())

    print("A5 absence versus explicit null after read_json: both NULL?  ->",
          con.execute("SELECT tags IS NULL FROM read_json(?, columns=?, format='newline_delimited')",
                      [str(root / "missing_key.ndjson"), COLUMNS]).fetchall(),
          con.execute("SELECT tags IS NULL FROM read_json(?, columns=?, format='newline_delimited')",
                      [str(root / "explicit_null.ndjson"), COLUMNS]).fetchall())
    print("A5b presence via json_exists / json_keys on the raw text:",
          con.execute("SELECT json_exists(?, '$.tags'), json_exists(?, '$.tags')",
                      [CASES["missing_key"], CASES["explicit_null"]]).fetchall())

    # A6 one large single JSON object against maximum_object_size (default and raised)
    big = root / "big.json"
    payload = {"rows": [{"i": i, "s": "x" * 90} for i in range(200_000)]}  # ~20 MB
    big.write_text(json.dumps(payload, separators=(",", ":")))
    size = big.stat().st_size
    print(f"A6 single object of {size} bytes")
    show("default max", lambda: con.execute("SELECT len(rows) FROM read_json(?, columns={'rows': 'STRUCT(i BIGINT, s VARCHAR)[]'})", [str(big)]).fetchall())
    show("raised max", lambda: con.execute(
        "SELECT len(rows) FROM read_json(?, columns={'rows': 'STRUCT(i BIGINT, s VARCHAR)[]'}, maximum_object_size=67108864)", [str(big)]).fetchall())
    show("unnest rows", lambda: con.execute(
        "SELECT count(*), max(r.i) FROM (SELECT unnest(rows) AS r FROM read_json(?, columns={'rows': 'STRUCT(i BIGINT, s VARCHAR)[]'}, maximum_object_size=67108864))", [str(big)]).fetchall())
    show("read_json_objects", lambda: con.execute(
        "SELECT json_array_length(json, '$.rows') FROM read_json_objects(?, maximum_object_size=67108864)", [str(big)]).fetchall())

    # A7 per-row diagnostics without failing the scan: read raw text, then classify with json_valid / TRY
    good_bad = root / "mixed.ndjson"
    good_bad.write_text("\n".join([CASES["ok"], CASES["nonnumeric_string"], CASES["extra_key"]]) + "\n")
    show("A7 raw+classify", lambda: con.execute(
        """
        SELECT ordinality, json_valid(json) AS valid,
               TRY(json_transform_strict(json, ?)) IS NULL AS shape_failed,
               list_sort(json_keys(json)) AS keys
        FROM read_json_objects(?, format='newline_delimited') WITH ORDINALITY
        """, [STRUCTURE, str(good_bad)]).fetchall())
