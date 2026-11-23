"""Three-way parity of the existing partition identity over typed columns.

Question: can the present partition digest (sha256 over the tagged canonical
frame) be produced by a straight-line expression over typed columns in DuckDB
and in PostgreSQL, equal to Python ``canonical_identity`` and to the installed
recursive ``data.ddo_identity``?  No timing is taken.

Run: uv run --no-sync python <this file>
The PostgreSQL leg uses only ``pg_temp`` in ``corpus_structure_dev`` and rolls back.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import duckdb
import psycopg
import pyarrow as pa
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_value_codec import semantic_value
from corpus_structure.semantic.identity import canonical_bytes

OUT = Path(__file__).parent / "raw" / "identity_parity.json"

TEXTS = [
    "plain",
    "naïve café",
    'quote " and \\ backslash',
    "tab\tnewline\ncarriage\r",
    "form\ffeed\bbs",
    "ctl \x01 \x0b \x0e \x0f \x1a \x1f",
    "del \x7f end",
    "漢字 😀     ﻿",
    "é combining",
    "</script> / solidus",
    "",
]


def rows_for(block: int, rng: random.Random) -> list[dict]:
    rows = []
    position = 0
    for ordinal in range(rng.randint(1, 12)):
        width = rng.randint(1, 9)
        row = {
            "record_type": "token",
            "ordinal": ordinal,
            "start": position,
            "end": position + width,
            "extent": 4096 + block,
            "space": bool(rng.getrandbits(1)),
            "piece_indices": [rng.randint(0, 2**40) for _ in range(rng.randint(0, 3))],
        }
        if rng.random() < 0.7:
            row["sentence"] = rng.randint(0, 3)
        if rng.random() < 0.8:
            row["lemma"] = rng.choice(TEXTS)
        if rng.random() < 0.5:
            row["morphology"] = [rng.choice(TEXTS) for _ in range(rng.randint(0, 3))]
        if rng.random() < 0.3:
            row["head"] = -rng.randint(0, 2**62)
        rows.append(row)
        position += width
    rows.append({"record_type": "sentence", "ordinal": 0, "start": 0, "end": position, "extent": 4096 + block})
    return sorted(rows, key=lambda r: (r["record_type"], r["ordinal"]))


SCHEMA = pa.schema(
    [
        ("block", pa.int32()),
        ("item", pa.int32()),
        ("record_type", pa.string()),
        ("ordinal", pa.int64()),
        ("start", pa.int64()),
        ("end", pa.int64()),
        ("extent", pa.int64()),
        ("space", pa.bool_()),
        ("piece_indices", pa.list_(pa.int64())),
        ("sentence", pa.int64()),
        ("lemma", pa.string()),
        ("morphology", pa.list_(pa.string())),
        ("head", pa.int64()),
    ]
)
# Field order inside a tagged mapping is code-point order of the key.
INT = ("end", "extent", "head", "ordinal", "sentence", "start")
KEYS = sorted(["record_type", "ordinal", "start", "end", "extent", "space", "piece_indices", "sentence", "lemma", "morphology", "head"])

# DuckDB writes nine C0 escapes in upper-case hex; canonical JSON uses lower case.
_DUCK_FIX = {"000B": "000b", "000E": "000e", "000F": "000f", "001A": "001a", "001B": "001b", "001C": "001c", "001D": "001d", "001E": "001e", "001F": "001f"}


def duck_string(expr: str) -> str:
    out = f"to_json({expr})::VARCHAR"
    for upper, lower in _DUCK_FIX.items():
        out = f"replace({out}, '\\u{upper}', '\\u{lower}')"
    return out


def duck_part(key: str) -> str:
    q = f'"{key}"'
    if key in INT:
        return f"""'["{key}",["integer","' || {q}::VARCHAR || '"]]'"""
    if key == "space":
        return f"""'["{key}",["boolean",' || CASE WHEN {q} THEN 'true' WHEN NOT {q} THEN 'false' END || ']]'"""
    if key == "piece_indices":
        return f"""'["{key}",["sequence",[' || array_to_string(list_transform({q}, lambda x: '["integer","' || x::VARCHAR || '"]'), ',') || ']]]'"""
    if key == "morphology":
        return f"""'["{key}",["sequence",[' || array_to_string(list_transform({q}, lambda x: '["string",' || {duck_string("x")} || ']'), ',') || ']]]'"""
    return f"""'["{key}",["string",' || {duck_string(q)} || ']]'"""


def pg_part(key: str) -> str:
    q = f'"{key}"'
    if key in INT:
        return f"""'["{key}",["integer","' || {q}::text || '"]]'"""
    if key == "space":
        return f"""'["{key}",["boolean",' || CASE WHEN {q} THEN 'true' WHEN NOT {q} THEN 'false' END || ']]'"""
    if key == "piece_indices":
        return f"""CASE WHEN {q} IS NOT NULL THEN '["{key}",["sequence",[' || coalesce((SELECT string_agg('["integer","' || x::text || '"]', ',' ORDER BY n) FROM unnest({q}) WITH ORDINALITY AS u(x, n)), '') || ']]]' END"""
    if key == "morphology":
        return f"""CASE WHEN {q} IS NOT NULL THEN '["{key}",["sequence",[' || coalesce((SELECT string_agg('["string",' || to_json(x)::text || ']', ',' ORDER BY n) FROM unnest({q}) WITH ORDINALITY AS u(x, n)), '') || ']]]' END"""
    return f"""'["{key}",["string",' || to_json({q})::text || ']]'"""


def main() -> None:
    rng = random.Random(20261122)
    blocks = {block: rows_for(block, rng) for block in range(60)}
    digits = 38  # no decimals occur in this population
    expected = {block: canonical_identity("partition", rows).key for block, rows in blocks.items()}
    flat = [
        {"block": block, "item": index, **{name: row.get(name) for name in SCHEMA.names[2:]}}
        for block, rows in blocks.items()
        for index, row in enumerate(rows)
    ]
    table = pa.Table.from_pylist(flat, schema=SCHEMA)

    # --- DuckDB: one statement over the typed table -------------------------------
    con = duckdb.connect()
    con.register("items", table)
    item = "'[\"mapping\",[' || array_to_string(list_filter([" + ", ".join(duck_part(k) for k in KEYS) + "], lambda p: p IS NOT NULL), ',') || ']]'"
    duck_sql = f"""
        SELECT block, 'partition:' || sha256('["ddo","partition","1",["sequence",[' ||
               string_agg({item}, ',' ORDER BY item) || ']]]') AS digest
        FROM items GROUP BY block"""
    duck = dict(con.sql(duck_sql).fetchall())

    # --- PostgreSQL: typed temp relation, set SQL; reference = installed recursive twin
    pg_item = "'[\"mapping\",[' || concat_ws(',', " + ", ".join(pg_part(k) for k in KEYS) + ") || ']]'"
    pg_sql = f"""
        SELECT block, 'partition:' || encode(sha256(convert_to('["ddo","partition","1",["sequence",[' ||
               string_agg({pg_item}, ',' ORDER BY item) || ']]]', 'UTF8')), 'hex')
        FROM pg_temp.items GROUP BY block"""
    with psycopg.connect("dbname=corpus_structure_dev port=5434") as pg, pg.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE items (block int, item int, record_type text, ordinal bigint, start bigint,"
            ' "end" bigint, extent bigint, space boolean, piece_indices bigint[], sentence bigint, lemma text,'
            " morphology text[], head bigint) ON COMMIT DROP"
        )
        with cur.copy("COPY pg_temp.items FROM STDIN") as copy:
            for row in flat:
                copy.write_row([row[name] for name in SCHEMA.names])
        cur.execute(pg_sql)
        pg_typed = dict(cur.fetchall())
        cur.execute("CREATE TEMP TABLE bodies (block int, body jsonb) ON COMMIT DROP")
        cur.executemany(
            "INSERT INTO bodies VALUES (%s, %s::jsonb)",
            [(b, canonical_bytes(semantic_value(rows, decimal_fixed_point_digits=digits)).decode()) for b, rows in blocks.items()],
        )
        cur.execute("SELECT block, data.ddo_identity('partition', body) FROM bodies")
        pg_recursive = dict(cur.fetchall())
        pg.rollback()

    result = {
        "partitions": len(blocks),
        "items": len(flat),
        "duckdb_typed_equals_python": sum(duck[b] == expected[b] for b in blocks),
        "postgresql_typed_equals_python": sum(pg_typed[b] == expected[b] for b in blocks),
        "postgresql_recursive_equals_python": sum(pg_recursive[b] == expected[b] for b in blocks),
        "first_mismatch": next(
            ({"block": b, "python": expected[b], "duckdb": duck[b], "pg_typed": pg_typed[b]} for b in blocks if not (duck[b] == expected[b] == pg_typed[b])),
            None,
        ),
        "versions": {"duckdb": duckdb.__version__, "pyarrow": pa.__version__, "psycopg": psycopg.__version__},
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
