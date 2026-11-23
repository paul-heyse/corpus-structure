"""Type round-trip matrix: Arrow -> PostgreSQL by ADBC ingest (create, append) and pgpq
binary COPY, and PostgreSQL -> Arrow by ADBC fetch (COPY and bound paths).

Reference values are inserted from SQL literals and read as PostgreSQL text; an ingest is
"exact" when its text readback equals the reference text. Runs only against the worker-owned
scratch database ``sbx_columnar_probe_scratch``. Writes ``raw/type_matrix.json``.
Usage: uv run python <this file>
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import adbc_driver_postgresql.dbapi as adbc
import psycopg
import pyarrow as pa
from pgpq import ArrowToPostgresBinaryEncoder
from pgpq.encoders import StringEncoderBuilder
from pgpq.schema import Jsonb

DB = "sbx_columnar_probe_scratch"
URI = f"postgresql:///{DB}?host=/var/run/postgresql&port=5434"
PG = f"dbname={DB} host=/var/run/postgresql port=5434"
OUT = Path(__file__).with_name("raw") / "type_matrix.json"
UTC = dt.UTC
D103 = "1" + "234567890" * 11 + "12"  # 102 integer digits ...
D103 = D103[:98] + "." + "12345"  # 103 significant digits total
assert len(D103.replace(".", "")) == 103
DIGEST = hashlib.sha256(b"corpus").digest()

SETUP = """
DROP SCHEMA IF EXISTS tm CASCADE;
CREATE SCHEMA tm;
CREATE TYPE tm.span AS (start_offset int4, end_offset int4, label text);
CREATE TYPE tm.kind AS ENUM ('alpha', 'beta');
CREATE DOMAIN tm.pos_int AS bigint CHECK (VALUE >= 0);
"""

# name: (pg type, arrow array or None, SQL literal list)
L = lambda *xs: list(xs)  # noqa: E731
CASES: dict[str, tuple[str, pa.Array | None, list[str | None]]] = {
    "int16": ("smallint", pa.array([1, -32768, None], pa.int16()), L("1", "-32768", None)),
    "int32": ("integer", pa.array([2**31 - 1, None], pa.int32()), L(str(2**31 - 1), None)),
    "int64": ("bigint", pa.array([-(2**63), None], pa.int64()), L(str(-(2**63)), None)),
    "bool": ("boolean", pa.array([True, False, None]), L("true", "false", None)),
    "text_unicode": ("text", pa.array(["é漢字🙂", "", None]), L("'é漢字🙂'", "''", None)),
    "text_nul": ("text", pa.array(["a\x00b"]), L(None)),
    "bytea_digest": ("bytea", pa.array([DIGEST, b"", None], pa.binary()),
                     L(f"'\\x{DIGEST.hex()}'", "''", None)),
    "bytea_fixed32": ("bytea", pa.array([DIGEST], pa.binary(32)), L(f"'\\x{DIGEST.hex()}'")),
    "bytea_large": ("bytea", pa.array([DIGEST], pa.large_binary()), L(f"'\\x{DIGEST.hex()}'")),
    "numeric_dec128": ("numeric", pa.array([Decimal("12345678901234567890.0123456789"),
                                            Decimal("-0.0000000001"), None], pa.decimal128(38, 10)),
                       L("12345678901234567890.0123456789", "-0.0000000001", None)),
    "numeric_dec256": ("numeric", pa.array([Decimal("1" * 46 + "." + "9" * 30)], pa.decimal256(76, 30)),
                       L("1" * 46 + "." + "9" * 30)),
    "numeric_103_from_string": ("numeric", pa.array([D103]), L(D103)),
    "numeric_from_int64": ("numeric", pa.array([2**62, None], pa.int64()), L(str(2**62), None)),
    "timestamptz_us_utc": ("timestamptz", pa.array([dt.datetime(2026, 11, 22, 12, 0, 0, 123456, tzinfo=UTC), None],
                                                   pa.timestamp("us", "UTC")),
                           L("'2026-11-22 12:00:00.123456+00'", None)),
    "timestamptz_ns_utc": ("timestamptz", pa.array([1_795_000_000_123_456_789], pa.timestamp("ns", "UTC")),
                           L("to_timestamp(1795000000.123456)")),
    "timestamptz_from_naive_us": ("timestamptz", pa.array([dt.datetime(2026, 11, 22, 12)], pa.timestamp("us")),
                                  L("'2026-11-22 12:00:00+00'")),
    "date": ("date", pa.array([dt.date(2026, 11, 22), None], pa.date32()), L("'2026-11-22'", None)),
    "uuid_ext": ("uuid", pa.array([b"\x01" * 16], pa.uuid()), L("'01010101-0101-0101-0101-010101010101'")),
    "uuid_fixed16": ("uuid", pa.array([b"\x01" * 16], pa.binary(16)), L("'01010101-0101-0101-0101-010101010101'")),
    "uuid_from_string": ("uuid", pa.array(["01010101-0101-0101-0101-010101010101"]),
                         L("'01010101-0101-0101-0101-010101010101'")),
    "jsonb_ext": ("jsonb", pa.array(['{"b": [1, 2.50], "a": null}', "null", None], pa.json_(pa.string())),
                  L("'{\"b\": [1, 2.50], \"a\": null}'", "'null'", None)),
    "jsonb_plain_string": ("jsonb", pa.array(['{"a": 1}']), L("'{\"a\": 1}'")),
    "list_int64": ("bigint[]", pa.array([[1, 2], [], None, [None, 3]], pa.list_(pa.int64())),
                   L("'{1,2}'", "'{}'", None, "'{NULL,3}'")),
    "list_text": ("text[]", pa.array([["é", ""], None], pa.list_(pa.string())), L("'{é,\"\"}'", None)),
    "list_list_int64": ("bigint[]", pa.array([[[1, 2], [3, 4]]], pa.list_(pa.list_(pa.int64()))),
                        L("'{{1,2},{3,4}}'")),
    "struct_composite": ("tm.span", pa.array([{"start_offset": 1, "end_offset": 5, "label": "w"}, None],
                                             pa.struct([("start_offset", pa.int32()), ("end_offset", pa.int32()),
                                                        ("label", pa.string())])),
                         L("ROW(1,5,'w')", None)),
    "list_struct_composite_array": (
        "tm.span[]",
        pa.array([[{"start_offset": 1, "end_offset": 5, "label": "w"},
                   {"start_offset": 6, "end_offset": 9, "label": None}], []],
                 pa.list_(pa.struct([("start_offset", pa.int32()), ("end_offset", pa.int32()),
                                     ("label", pa.string())]))),
        L("ARRAY[ROW(1,5,'w'),ROW(6,9,NULL)]::tm.span[]", "'{}'")),
    "enum_from_dictionary": ("tm.kind", pa.array(["alpha", "beta", None]).dictionary_encode(),
                             L("'alpha'", "'beta'", None)),
    "enum_from_string": ("tm.kind", pa.array(["alpha", None]), L("'alpha'", None)),
    "domain_pos_int": ("tm.pos_int", pa.array([5, None], pa.int64()), L("5", None)),
    "domain_pos_int_violation": ("tm.pos_int", pa.array([-5], pa.int64()), L(None)),
}

FETCH_ONLY = {
    "int4range": ("int4range", L("'[1,5)'", "'empty'", "'(,3]'", None)),
    "int4multirange": ("int4multirange", L("'{[1,3),[5,7)}'", None)),
    "int_2d_array": ("integer[]", L("'{{1,2},{3,4}}'", "'[0:1]={7,8}'")),
    "numeric_special": ("numeric", L("'NaN'", "'Infinity'", "'-Infinity'", D103)),
    "numeric_typmod": ("numeric(12,4)", L("'1.5'",)),
    "timestamptz_infinity": ("timestamptz", L("'infinity'",)),
    "jsonb_nested": ("jsonb", L("'{\"z\":1,\"a\":[true,{\"k\":\"é\"}]}'",)),
    "composite_nested_array": ("tm.span[]", L("ARRAY[ROW(1,5,'w')]::tm.span[]", "'{}'", None)),
    "composite": ("tm.span", L("ROW(1,5,'w')", "ROW(NULL,NULL,NULL)", None)),
    "enum": ("tm.kind", L("'beta'",)),
    "domain": ("tm.pos_int", L("7",)),
    "uuid": ("uuid", L("'01010101-0101-0101-0101-010101010101'",)),
    "bytea": ("bytea", L(f"'\\x{DIGEST.hex()}'", "''")),
    "interval": ("interval", L("'1 mon 2 days 00:00:01.5'",)),
}

results: dict[str, dict] = {"ingest": {}, "fetch": {}}


def err(e: BaseException) -> str:
    return f"{type(e).__name__}: {str(e).splitlines()[0][:240]}"


def ref_table(pc, name: str, pgtype: str, literals: list[str | None]) -> list[str | None]:
    pc.execute(f"CREATE TABLE tm.ref_{name} (ord int4, v {pgtype})")
    for i, lit in enumerate(literals):
        pc.execute(f"INSERT INTO tm.ref_{name} VALUES ({i}, ({lit if lit is not None else 'NULL'})::{pgtype})")
    return readback(pc, f"tm.ref_{name}")


def readback(pc, table: str) -> list[str | None]:
    return [r[0] for r in pc.execute(f"SELECT v::text FROM {table} ORDER BY ord").fetchall()]


def textual_type(pc, table: str) -> str:
    return pc.execute(
        f"SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid = '{table}'::regclass "
        "AND attname = 'v'"
    ).fetchone()[0]


def pgpq_copy(pc, table: str, batch: pa.RecordBatch, pgtype: str) -> str:
    schema = batch.schema
    if pgtype == "jsonb" and pa.types.is_string(schema.field("v").type):
        enc = ArrowToPostgresBinaryEncoder.new_with_encoders(
            schema, {"ord": ArrowToPostgresBinaryEncoder.infer_encoder(schema.field("ord")),
                     "v": StringEncoderBuilder.new_with_output(schema.field("v"), Jsonb())})
    else:
        enc = ArrowToPostgresBinaryEncoder(schema)
    names = enc.composite_type_names()
    if names:
        oid = pc.execute("SELECT 'tm.span'::regtype::oid").fetchone()[0]
        enc.with_composite_oids(dict.fromkeys(names, oid))
    wire = [str(c.data_type.ddl()) for c in enc.schema().columns]
    with pc.cursor() as cur, cur.copy(f"COPY {table} (ord, v) FROM STDIN (FORMAT BINARY)") as cp:
        cp.write(enc.write_header())
        cp.write(enc.write_batch(batch))
        cp.write(enc.finish())
    return f"wire={wire}"


with psycopg.connect(PG, autocommit=True) as pc, adbc.connect(URI, autocommit=True) as ac:
    pc.execute(SETUP)
    cur = ac.cursor()
    for name, (pgtype, arr, literals) in CASES.items():
        row: dict = {"pg_type": pgtype, "arrow_type": str(arr.type)}
        try:
            row["reference_text"] = ref = ref_table(pc, name, pgtype, literals)
        except Exception as e:  # noqa: BLE001
            row["reference_text"] = ref = err(e)
        batch = pa.record_batch([pa.array(range(len(arr)), pa.int32()), arr], names=["ord", "v"])

        # ADBC create (type inference)
        try:
            cur.adbc_ingest(f"ac_{name}", batch, mode="create", db_schema_name="tm")
            got = readback(pc, f"tm.ac_{name}")
            row["adbc_create"] = {"inferred": textual_type(pc, f"tm.ac_{name}"), "text": got,
                                  "equals_reference": got == ref}
        except Exception as e:  # noqa: BLE001
            row["adbc_create"] = err(e)
        # ADBC append into declared target (target-aware encoding)
        pc.execute(f"CREATE TABLE tm.aa_{name} (ord int4, v {pgtype})")
        try:
            cur.adbc_ingest(f"aa_{name}", batch, mode="append", db_schema_name="tm")
            got = readback(pc, f"tm.aa_{name}")
            row["adbc_append"] = {"text": got, "equals_reference": got == ref}
        except Exception as e:  # noqa: BLE001
            row["adbc_append"] = err(e)
        # pgpq binary COPY via psycopg into declared target
        pc.execute(f"CREATE TABLE tm.pq_{name} (ord int4, v {pgtype})")
        try:
            note = pgpq_copy(pc, f"tm.pq_{name}", batch, pgtype)
            got = readback(pc, f"tm.pq_{name}")
            row["pgpq_copy"] = {"text": got, "equals_reference": got == ref, "note": note}
        except Exception as e:  # noqa: BLE001
            row["pgpq_copy"] = err(e)
        results["ingest"][name] = row
        print(name, {k: (v if isinstance(v, str) else v.get("equals_reference", v)) for k, v in row.items()
                     if k.startswith(("adbc", "pgpq"))})

    # Fetch matrix: reference tables from literals, ADBC server resolver and builtin resolver
    for name, (pgtype, literals) in FETCH_ONLY.items():
        try:
            ref_table(pc, "f_" + name, pgtype, literals)
        except Exception as e:  # noqa: BLE001
            results["fetch"][name] = {"setup": err(e)}
    builtin = adbc.connect(URI, autocommit=True, db_kwargs={"adbc.postgresql.type_resolver_mode": "builtin"})
    # A server-mode connection opened after the DDL: its resolver knows tm.span / tm.kind.
    fresh = adbc.connect(URI, autocommit=True)
    tables = [(n, f"tm.ref_f_{n}") for n in FETCH_ONLY] + [(n, f"tm.ref_{n}") for n in CASES]
    for name, table in tables:
        entry = results["fetch"].setdefault(name, {})
        entry["reference_text"] = readback(pc, table) if pc.execute(
            "SELECT to_regclass(%s)", (table,)).fetchone()[0] else None
        for label, conn, sql, params in (
            ("server_copy", ac, f"SELECT v FROM {table} ORDER BY ord", None),
            ("server_bound", ac, f"SELECT v FROM {table} WHERE $1::bool ORDER BY ord", (True,)),
            ("builtin_copy", builtin, f"SELECT v FROM {table} ORDER BY ord", None),
            ("fresh_server_copy", fresh, f"SELECT v FROM {table} ORDER BY ord", None),
        ):
            try:
                c = conn.cursor()
                c.execute(sql, parameters=params)
                t = c.fetch_arrow_table()
                f = t.schema.field("v")
                vals = t.column("v").to_pylist()
                entry[label] = {
                    "arrow_type": str(f.type),
                    "metadata": {k.decode(): v.decode(errors="replace")[:80]
                                 for k, v in (f.metadata or {}).items()},
                    "values": [repr(v)[:120] for v in vals],
                }
                c.close()
            except Exception as e:  # noqa: BLE001
                entry[label] = err(e)
        print("fetch", name, {k: (v["arrow_type"] if isinstance(v, dict) else v)
                              for k, v in entry.items() if k != "reference_text"})
    builtin.close()
    fresh.close()
    cur.close()

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False))
