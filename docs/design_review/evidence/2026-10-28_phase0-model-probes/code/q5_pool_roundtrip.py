"""Probe Q-5 (P0-P-Q5, record ``p0q.pool-roundtrip``): the pool round trip PostgreSQL → ADBC → DuckDB → Arrow →
PostgreSQL, and the memory of one join.

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q5_pool_roundtrip.py all

On the ``18/corpus`` cluster, database ``p0q_pool`` (cloned from ``cs_template``; dropped by ``drop``):

1. ``fidelity``: a hand-made source table ``src_obs`` (JSONB payloads with present-null, absent, JSON-null and SQL-NULL
   cases, big and tiny JSON numbers, unicode; a ``json`` column with whitespace, key order and duplicate keys;
   NUMERIC with 39 significant digits, scale-carrying ``1.50``, ``NaN`` and ``±Infinity``; ``timestamptz`` values
   around both epochs and at the type's ends; text with empty string and NULL) and a dimension ``src_dim``.

   - **Load** with ADBC 1.13 ``cursor.fetch_record_batch()`` (the reader is consumed once with ``read_all``);
     the parameter-binding question: a ``$1`` SELECT, and the temporary-table route for binding the run and cut;
     which statements reach the server as ``COPY (…) TO STDOUT`` (read back from ``pg_stat_statements``).
   - **DuckDB 2.0**: the Arrow table registered; one join (``src_obs ⋈ src_dim USING (kind)``) and one group-by;
     ``json_exists``/``->`` on present-null versus absent; Arrow back through ``rel.to_arrow_table()``; the 2.0
     result lifecycle (an open ``execute()`` result and a second statement on the same connection).
   - **Write back** the join result into PostgreSQL by (a) psycopg 3.3.6 binary COPY with ``Copy.set_types``
     (JSON text passed through ``Jsonb``/``Json`` with an identity ``dumps``, so nothing is re-serialized;
     NUMERIC as ``Decimal``) and (b) pgpq 0.12 ``ArrowToPostgresBinaryEncoder`` → ``Copy.write`` with the JSONB
     string encoder, in three forms for NUMERIC: text straight into ``numeric``, ``decimal128`` cast, and a staging
     table with a server-side cast. Each destination is compared with ``src_obs`` in SQL, column by column.
   - **psycopg as the loader** (P1's alternative): the same rows through a binary cursor into Arrow, with the
     loaders that keep JSONB as text and NUMERIC as text, compared with ADBC's Arrow.
   - ``±infinity`` timestamps through ADBC are checked separately (they do not survive; see the result).

2. ``memory --rows N``: in a fresh process, ``vol_obs`` (N observations, ~300 B JSONB each) and ``vol_claim``
   (20,000 claims) loaded by ADBC, registered in DuckDB, joined on the claim key and grouped; process RSS and
   high-water mark (``/proc/self/status``), ``pyarrow.total_allocated_bytes()`` and DuckDB's
   ``system.peak_buffer_memory`` from JSON profiling at each step; the same load by psycopg for comparison.
   Run at N = 10⁵ (D3 §11 run scale) and 10⁶.

Writes ``results/q5/fidelity.json``, ``results/q5/fidelity.md`` and ``results/q5/memory_<N>.json``.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import os
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path

os.environ["PGHOST"] = "/var/run/postgresql"
os.environ["PGPORT"] = "5434"

CODE = Path(__file__).resolve().parent
OUT = CODE.parent / "results" / "q5"
DB = "p0q_pool"
URI = f"postgresql:///{DB}?host=/var/run/postgresql&port=5434"
ADMIN = "postgresql:///postgres?host=/var/run/postgresql&port=5434"
SCRATCH = Path(os.environ.get("Q5_SCRATCH", "/tmp"))

SRC_DDL = """
DROP TABLE IF EXISTS src_obs, src_dim, src_edge CASCADE;
CREATE TABLE src_obs (
  id           bigint PRIMARY KEY,
  run_id       bigint NOT NULL,
  kind         text   NOT NULL,
  payload      jsonb,
  payload_json json,
  amount       numeric,
  at           timestamptz,
  label        text,
  note         text NOT NULL            -- what the row exercises
);
CREATE TABLE src_dim (kind text PRIMARY KEY, weight numeric NOT NULL, cls text NOT NULL);
CREATE TABLE src_edge (id bigint PRIMARY KEY, at timestamptz, note text);
"""

ROWS = [
    # id, run, kind, payload, payload_json, amount, at, label, note
    (1, 7, "mention", '{"a": 1, "b": null}', '{"a": 1, "b": null}', "1.50", "2026-10-28 09:00:00.123456+02", "x", "present-null field b; scale 1.50"),
    (2, 7, "mention", '{"a": 1}', '{"a": 1}', "-0.000001", "2026-10-28 07:00:00.123456Z", "", "absent field b; empty-string label"),
    (3, 7, "relation", "{}", "{}", "0", "2000-01-01 00:00:00Z", None, "empty object; NULL label; PostgreSQL epoch"),
    (4, 7, "relation", "null", "null", "NaN", "1969-12-31 23:59:59.999999Z", "tab\tnew\nline", "JSON null at top level; NaN; Unix epoch minus 1 µs"),
    (5, 7, "value", None, None, None, None, None, "SQL NULL everywhere"),
    (6, 7, "value", '{"v": 12345678901234567890.12345678901234567890, "t": 1e-30, "i": -0}', '{"v": 12345678901234567890.12345678901234567890, "t": 1e-30}',
     "123456789012345678901234567890.123456789", "0001-01-01 00:00:00Z", "back\\slash", "big and tiny JSON numbers; 39-digit NUMERIC; year 1"),
    (7, 7, "value", '{"s": "é 😀 \\u00e9-escaped \\"q\\"", "arr": [null, 1, {"b": null}]}', '{"s": "é 😀", "arr": [null, 1, {"b": null}]}',
     "Infinity", "9999-12-31 23:59:59.999999Z", "é 😀", "unicode; nulls inside arrays; +Infinity NUMERIC; last microsecond of 9999"),
    (8, 7, "scope", '{"z": 1, "a": 2}', '{ "z" : 1,  "a":2, "a": 3 }', "-Infinity", "2026-03-29 01:30:00+01", "y", "json text: whitespace, key order, duplicate key; -Infinity"),
    (9, 7, "scope", '{"b": false}', '{"b": false}', "1e-40", "2026-10-28 09:00:00.000001-09:30", "z", "false is not null; 1e-40; odd offset"),
]
DIM = [("mention", "0.25", "extract"), ("relation", "1.000", "extract"), ("value", "3.14159265358979323846264338327950288", "normalize"), ("scope", "2", "resolve")]
EDGE = [(1, "infinity", "+infinity"), (2, "-infinity", "-infinity")]

DST_COLS = ["id", "run_id", "kind", "payload", "payload_json", "amount", "at", "label", "note", "weight", "cls"]
DST_TYPES = ["int8", "int8", "text", "jsonb", "json", "numeric", "timestamptz", "text", "text", "numeric", "text"]
DST_DDL = "CREATE TABLE {name} (id bigint PRIMARY KEY, run_id bigint, kind text, payload jsonb, payload_json json, amount numeric, at timestamptz, label text, note text, weight numeric, cls text)"

COMPARE = """
SELECT s.id,
  (d.id IS NOT NULL)                                              AS row_present,
  (d.payload IS NOT DISTINCT FROM s.payload)                      AS jsonb_equal,
  (d.payload ? 'b') IS NOT DISTINCT FROM (s.payload ? 'b')        AS b_presence_equal,
  (d.payload -> 'b') IS NOT DISTINCT FROM (s.payload -> 'b')      AS b_value_equal,
  (jsonb_typeof(d.payload) IS NOT DISTINCT FROM jsonb_typeof(s.payload)) AS top_type_equal,
  (d.payload_json::text IS NOT DISTINCT FROM s.payload_json::text) AS json_text_identical,
  (d.amount IS NOT DISTINCT FROM s.amount)                        AS numeric_equal,
  (d.amount::text IS NOT DISTINCT FROM s.amount::text)            AS numeric_text_identical,
  (d.at IS NOT DISTINCT FROM s.at)                                AS timestamptz_equal,
  (d.label IS NOT DISTINCT FROM s.label)                          AS text_equal,
  (d.weight::text IS NOT DISTINCT FROM m.weight::text)            AS dim_numeric_text_identical,
  d.amount::text AS dst_amount, s.amount::text AS src_amount, d.at::text AS dst_at, s.at::text AS src_at,
  d.payload::text AS dst_payload, s.payload::text AS src_payload, d.payload_json::text AS dst_json, s.payload_json::text AS src_json
FROM src_obs s JOIN src_dim m USING (kind) LEFT JOIN {name} d ON d.id = s.id ORDER BY s.id
"""
CHECKS = ["row_present", "jsonb_equal", "b_presence_equal", "b_value_equal", "top_type_equal", "json_text_identical", "numeric_equal",
          "numeric_text_identical", "timestamptz_equal", "text_equal", "dim_numeric_text_identical"]


def versions() -> dict:
    return {p: md.version(p) for p in ("adbc-driver-postgresql", "adbc-driver-manager", "duckdb", "pyarrow", "pgpq", "psycopg", "psycopg-binary")}


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")


def status() -> dict:
    out = {}
    for ln in Path("/proc/self/status").read_text().splitlines():
        k, _, v = ln.partition(":")
        if k in ("VmRSS", "VmHWM"):
            out[k] = int(v.split()[0]) * 1024
    import pyarrow as pa

    out["arrow_allocated"] = pa.total_allocated_bytes()
    return out


# ---- setup ------------------------------------------------------------------------------------------

def cmd_create() -> int:
    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
        c.execute(f"CREATE DATABASE {DB} TEMPLATE cs_template")
    with psycopg.connect(URI, autocommit=True) as c:
        c.execute(SRC_DDL)
        c.cursor().executemany("INSERT INTO src_obs VALUES (%s, %s, %s, %s::jsonb, %s::json, %s::numeric, %s::timestamptz, %s, %s)", ROWS)
        c.cursor().executemany("INSERT INTO src_dim VALUES (%s, %s::numeric, %s)", DIM)
        c.cursor().executemany("INSERT INTO src_edge VALUES (%s, %s::timestamptz, %s)", EDGE)
        c.execute("ANALYZE")
    return 0


def cmd_drop() -> int:
    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
        left = c.execute("SELECT datname FROM pg_database WHERE datname LIKE 'p0q_pool%%'").fetchall()
    print("dropped", DB, "remaining:", left)
    return 0


# ---- fidelity ---------------------------------------------------------------------------------------

def adbc_load(sql: str, params=None):
    import adbc_driver_postgresql.dbapi as ad

    with ad.connect(URI) as conn:
        cur = conn.cursor()
        cur.execute(sql, parameters=params) if params is not None else cur.execute(sql)
        reader = cur.fetch_record_batch()
        schema = reader.schema
        tbl = reader.read_all()
        cur.close()
    return schema, tbl


def describe_schema(schema) -> list:
    return [{"name": f.name, "type": str(f.type), "metadata": {k.decode(): v.decode() for k, v in (f.metadata or {}).items()}} for f in schema]


def storage_pylist(col):
    import pyarrow as pa

    arr = col.combine_chunks() if isinstance(col, pa.ChunkedArray) else col
    if isinstance(arr, pa.ExtensionArray):
        arr = arr.storage
    if pa.types.is_timestamp(arr.type):
        return arr.cast(pa.int64()).to_pylist()
    return arr.to_pylist()


def binding(out: dict) -> None:
    """ADBC parameter binding on a SELECT, the temp-table route, and which statements went out as COPY."""
    import adbc_driver_postgresql.dbapi as ad
    import psycopg

    res = {}
    with ad.connect(URI) as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT /*q5-param*/ id, kind FROM src_obs WHERE run_id = $1 AND id > $2 ORDER BY id", parameters=(7, 6))
            t = cur.fetch_arrow_table()
            res["param_select"] = {"outcome": "accepted", "ids": t["id"].to_pylist()}
        except Exception as e:  # noqa: BLE001
            res["param_select"] = {"outcome": "refused", "error": f"{type(e).__name__}: {e}"}
        try:
            cur.execute("SELECT /*q5-param-rb*/ id FROM src_obs WHERE id = $1", parameters=(3,))
            res["param_select_record_batch"] = {"outcome": "accepted", "ids": cur.fetch_record_batch().read_all()["id"].to_pylist()}
        except Exception as e:  # noqa: BLE001
            res["param_select_record_batch"] = {"outcome": "refused", "error": f"{type(e).__name__}: {e}"}
        # the temp-table route: bind the run and cut with a parameterized INSERT (no result set), then join
        cur.execute("CREATE TEMP TABLE q5_cut (run_id bigint, cut_at timestamptz)")
        from datetime import datetime, timezone

        cut = datetime(2026, 10, 28, 8, 0, tzinfo=timezone.utc)
        try:
            cur.execute("INSERT INTO q5_cut VALUES ($1, $2)", parameters=(7, "2026-10-28 08:00:00+00"))
            res["param_insert_str_into_timestamptz"] = "accepted"
        except Exception as e:  # noqa: BLE001
            res["param_insert_str_into_timestamptz"] = f"{type(e).__name__}: {str(e).splitlines()[0]}"
            conn.rollback()
            cur.execute("CREATE TEMP TABLE IF NOT EXISTS q5_cut (run_id bigint, cut_at timestamptz)")
        cur.execute("INSERT INTO q5_cut VALUES ($1, $2)", parameters=(7, cut))   # a tz-aware datetime binds as timestamptz
        cur.execute("SELECT /*q5-cut*/ o.id FROM src_obs o JOIN q5_cut c ON o.run_id = c.run_id WHERE o.at <= c.cut_at ORDER BY o.id")
        res["temp_table_cut"] = {"ids": cur.fetch_record_batch().read_all()["id"].to_pylist()}
        cur.execute("SELECT /*q5-plain*/ id FROM src_obs ORDER BY id")
        cur.fetch_arrow_table()
        conn.commit()
        cur.close()
    with psycopg.connect(URI) as c:
        expect = [r[0] for r in c.execute("SELECT id FROM src_obs WHERE run_id = 7 AND at <= '2026-10-28 08:00:00+00' ORDER BY id")]
        res["temp_table_cut"]["expected"] = expect
        try:
            res["server_statements"] = [r[0] for r in c.execute(
                "SELECT DISTINCT query FROM pg_stat_statements WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database()) "
                "AND query LIKE '%%q5-%%' AND query NOT LIKE '%%pg_stat_statements%%' ORDER BY query")]
        except psycopg.Error as e:
            res["server_statements"] = f"{e.sqlstate}: {e.diag.message_primary}"
    out["binding"] = res


def duck_stage(tbl_obs, tbl_dim, out: dict):
    import duckdb

    con = duckdb.connect()
    lc = {}
    lc["timezone"] = con.sql("SELECT current_setting('TimeZone')").fetchall()[0][0]
    try:
        con.sql("SELECT 1").fetchone()
        lc["relation_fetchone"] = "available"
    except AttributeError as e:
        lc["relation_fetchone"] = f"AttributeError: {e}"
    con.register("obs", tbl_obs)
    con.register("dim", tbl_dim)
    try:
        con.sql("SELECT min(at) FROM obs").fetchall()
        lc["unquoted_at_identifier"] = "accepted"
    except Exception as e:  # noqa: BLE001
        lc["unquoted_at_identifier"] = f"{type(e).__name__}: {str(e).splitlines()[0]}"
    lc["duck_types"] = dict(zip(con.table("obs").columns, [str(t) for t in con.table("obs").types]))
    join = con.sql("SELECT o.id, o.run_id, o.kind, o.payload, o.payload_json, o.amount, o.\"at\", o.label, o.note, d.weight, d.cls "
                   "FROM obs o JOIN dim d USING (kind) ORDER BY o.id")
    grp = con.sql("SELECT kind, count(*) AS n, count(payload) AS n_payload, "
                  "sum(CASE WHEN json_exists(payload, '$.b') THEN 1 ELSE 0 END) AS b_exists, "
                  "sum(CASE WHEN (payload -> '$.b') = 'null'::JSON THEN 1 ELSE 0 END) AS b_json_null, "
                  "min(\"at\") AS first_at FROM obs GROUP BY kind ORDER BY kind")
    try:
        grp.fetchall()
        lc["fetchall_timestamptz"] = "accepted"
    except Exception as e:  # noqa: BLE001
        lc["fetchall_timestamptz"] = f"{type(e).__name__}: {str(e).splitlines()[0]}"
    gt = grp.to_arrow_table()
    lc["group_by"] = [dict(zip(gt.column_names, r)) for r in zip(*(storage_pylist(gt[n]) for n in gt.column_names))]
    lc["absent_vs_null"] = [list(map(str, r)) for r in con.sql(
        "SELECT id, json_exists(payload, '$.b'), payload -> '$.b', (payload -> '$.b') IS NULL, json_type(payload) FROM obs ORDER BY id").fetchall()]
    out_tbl = join.to_arrow_table()
    lc["arrow_out_schema"] = describe_schema(out_tbl.schema)
    # 2.0 result lifecycle: an open execute() result and a second statement
    life = {}
    r1 = con.execute("SELECT * FROM range(5)")
    life["first_fetchone"] = r1.fetchone()
    try:
        life["second_statement"] = con.execute("SELECT 42").fetchall()
    except Exception as e:  # noqa: BLE001
        life["second_statement"] = f"{type(e).__name__}: {e}"
    try:
        life["first_after_second"] = r1.fetchall()
    except Exception as e:  # noqa: BLE001
        life["first_after_second"] = f"{type(e).__name__}: {e}"
    life["relation_reevaluated_twice"] = [join.count("*").fetchall()[0][0], join.count("*").fetchall()[0][0]]
    lc["result_lifecycle"] = life
    out["duckdb"] = lc
    con.close()
    return out_tbl


def write_psycopg(tbl, name: str) -> dict:
    import psycopg
    from psycopg.types.json import Json, Jsonb

    import pyarrow as pa

    ident = lambda s: s  # noqa: E731  the Arrow value is already JSON text
    res: dict = {"arrow_at_type": str(tbl.schema.field("at").type)}
    try:
        tbl["at"].to_pylist()
        res["to_pylist_at_as_returned"] = "accepted"
    except OverflowError as e:
        res["to_pylist_at_as_returned"] = f"OverflowError: {e} (Python datetime in the DuckDB session zone)"
    # convert in UTC: every instant PostgreSQL holds then has a Python datetime
    tbl = tbl.set_column(tbl.schema.get_field_index("at"), "at", tbl["at"].cast(pa.timestamp("us", tz="UTC")))
    t0 = time.perf_counter()
    with psycopg.connect(URI) as c:
        c.execute(f"DROP TABLE IF EXISTS {name}")
        c.execute(DST_DDL.format(name=name))
        with c.cursor().copy(f"COPY {name} ({', '.join(DST_COLS)}) FROM STDIN (FORMAT BINARY)") as cp:
            cp.set_types(DST_TYPES)
            for batch in tbl.to_batches():
                cols = [storage_pylist(batch.column(i)) if DST_TYPES[i] != "timestamptz" else batch.column(i).to_pylist() for i in range(batch.num_columns)]
                for row in zip(*cols):
                    r = list(row)
                    r[3] = None if r[3] is None else Jsonb(r[3], dumps=ident)
                    r[4] = None if r[4] is None else Json(r[4], dumps=ident)
                    r[5] = None if r[5] is None else Decimal(r[5])
                    r[9] = None if r[9] is None else Decimal(r[9])
                    cp.write_row(r)
    return res | {"outcome": "written", "ms": round((time.perf_counter() - t0) * 1000, 2)}


def pgpq_encoder(tbl, numeric: str):
    import pyarrow as pa
    from pgpq import ArrowToPostgresBinaryEncoder, encoders, schema

    if numeric == "decimal128":
        cols = []
        for i, f in enumerate(tbl.schema):
            col = tbl.column(i)
            if f.name in ("amount", "weight"):
                col = col.cast(pa.decimal128(38, 9))   # raises on values that do not fit
            cols.append(col)
        tbl = pa.table(cols, names=tbl.column_names)
    mapping = {f.name: ArrowToPostgresBinaryEncoder.infer_encoder(f) for f in tbl.schema}
    mapping["payload"] = encoders.StringEncoderBuilder.new_with_output(tbl.schema.field("payload"), schema.Jsonb())
    enc = ArrowToPostgresBinaryEncoder.new_with_encoders(tbl.schema, mapping)
    return tbl, enc


def write_pgpq(tbl, name: str, numeric: str) -> dict:
    """numeric: 'text' (strings straight into numeric columns), 'decimal128' (Arrow cast), 'staging' (text staging + cast)."""
    import psycopg

    t0 = time.perf_counter()
    res: dict = {"numeric_route": numeric}
    try:
        tbl2, enc = pgpq_encoder(tbl, "decimal128" if numeric == "decimal128" else "text")
    except Exception as e:  # noqa: BLE001
        return res | {"outcome": "refused before COPY", "error": f"{type(e).__name__}: {e}"}
    res["pgpq_schema"] = [(col.name, type(col.data_type).__name__, col.nullable) for col in enc.schema().columns]
    with psycopg.connect(URI) as c:
        c.execute(f"DROP TABLE IF EXISTS {name}")
        c.execute(DST_DDL.format(name=name))
        target = name
        if numeric == "staging":
            target = f"{name}_stage"
            c.execute(f"CREATE TEMP TABLE {target} (id bigint, run_id bigint, kind text, payload jsonb, payload_json json, amount text, at timestamptz, "
                      "label text, note text, weight text, cls text)")
        try:
            with c.transaction():
                with c.cursor().copy(f"COPY {target} ({', '.join(DST_COLS)}) FROM STDIN (FORMAT BINARY)") as cp:
                    cp.write(enc.write_header())
                    for b in tbl2.to_batches():
                        chunk = enc.write_batch(b)
                        if chunk:
                            cp.write(chunk)
                    cp.write(enc.finish())
                if numeric == "staging":
                    c.execute(f"INSERT INTO {name} SELECT id, run_id, kind, payload, payload_json, amount::numeric, at, label, note, weight::numeric, cls FROM {target}")
            res["outcome"] = "written"
        except psycopg.Error as e:
            res |= {"outcome": "refused by the server", "error": f"{e.sqlstate}: {e.diag.message_primary}"}
    res["ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return res


def compare(name: str) -> dict:
    import psycopg

    with psycopg.connect(URI) as c:
        n = c.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        cur = c.execute(COMPARE.format(name=name))
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    fails = {k: [r["id"] for r in rows if not r[k]] for k in CHECKS}
    detail = [{k: r[k] for k in ("id", "src_amount", "dst_amount", "src_at", "dst_at", "src_payload", "dst_payload", "src_json", "dst_json")}
              for r in rows if any(not r[k] for k in CHECKS)]
    return {"rows": n, "failures_by_check": {k: v for k, v in fails.items() if v}, "all_pass": n > 0 and not any(fails.values()), "failing_rows": detail}


def psycopg_loader(out: dict, adbc_tbl) -> None:
    """P1's alternative loader: psycopg binary cursor, JSONB and NUMERIC kept as text, built into Arrow."""
    import psycopg
    import pyarrow as pa
    from psycopg.types.string import TextBinaryLoader, TextLoader

    tz_attempts = {}
    q = "SELECT id, run_id, kind, payload, payload_json, amount, at, label, note FROM src_obs ORDER BY id"
    for label, kw in (("server TimeZone, text", {"binary": False}), ("server TimeZone, binary", {"binary": True})):
        with psycopg.connect(URI) as c:
            tz = c.execute("SHOW TimeZone").fetchone()[0]
            try:
                c.cursor(**kw).execute(q).fetchall()
                tz_attempts[label] = f"{tz}: accepted"
            except psycopg.Error as e:
                tz_attempts[label] = f"{tz}: {type(e).__name__}: {e}"
    with psycopg.connect(URI, options="-c TimeZone=UTC") as c:
        for t in ("jsonb", "json", "numeric"):
            c.adapters.register_loader(t, TextLoader)
        cur = c.cursor(binary=False)
        cur.execute(q)
        rows = cur.fetchall()
        default_rows = psycopg.connect(URI).execute("SELECT payload, amount FROM src_obs WHERE id = 6").fetchone()
    sch = pa.schema([("id", pa.int64()), ("run_id", pa.int64()), ("kind", pa.string()), ("payload", pa.json_(pa.string())), ("payload_json", pa.json_(pa.string())),
                     ("amount", pa.string()), ("at", pa.timestamp("us", tz="UTC")), ("label", pa.string()), ("note", pa.string())])
    tbl = pa.Table.from_pylist([dict(zip(sch.names, r)) for r in rows], schema=sch)
    same = {}
    for name in sch.names:
        a, b = storage_pylist(tbl[name]), storage_pylist(adbc_tbl[name])
        same[name] = a == b if name != "amount" else [x for x, y in zip(a, b) if x != y]
    out["psycopg_loader"] = {"equal_to_adbc_by_column": same, "timestamptz_load_by_session_zone": tz_attempts,
                             "note": "text-format cursor with TextLoader for jsonb/json/numeric; binary jsonb would come back as dicts via json.loads",
                             "default_loaders_row6": {"payload": repr(default_rows[0]), "amount": repr(default_rows[1])},
                             "binary_text_loader": TextBinaryLoader.__name__}


def edge_timestamps(out: dict) -> None:
    import psycopg

    schema, tbl = adbc_load("SELECT id, at, note FROM src_edge ORDER BY id")
    raw = storage_pylist(tbl["at"])
    with psycopg.connect(URI) as c:
        pg = [r[0] for r in c.execute("SELECT (extract(epoch FROM at) * 1000000)::text FROM src_edge ORDER BY id")]
    out["infinity_timestamps"] = {"adbc_int64_us": raw, "postgres_epoch_us_text": pg,
                                  "int64_min": -(2**63), "int64_max": 2**63 - 1, "pg_epoch_offset_us": 946684800000000}


def cmd_fidelity() -> int:
    out: dict = {"versions": versions(), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    schema, obs = adbc_load("SELECT id, run_id, kind, payload, payload_json, amount, at, label, note FROM src_obs ORDER BY id")
    _, dim = adbc_load("SELECT kind, weight, cls FROM src_dim ORDER BY kind")
    out["adbc_schema"] = describe_schema(schema)
    out["adbc_values"] = {n: storage_pylist(obs[n]) for n in ("payload", "payload_json", "amount", "at")}
    binding(out)
    joined = duck_stage(obs, dim, out)
    out["writes"] = {
        "psycopg_set_types": write_psycopg(joined, "dst_psycopg") | {"compare": compare("dst_psycopg")},
    }
    for route in ("text", "decimal128", "staging"):
        name = f"dst_pgpq_{route}"
        w = write_pgpq(joined, name, route)
        if w.get("outcome") == "written":
            w["compare"] = compare(name)
        out["writes"][f"pgpq_{route}"] = w
    psycopg_loader(out, obs)
    edge_timestamps(out)
    write_json(OUT / "fidelity.json", out)
    write_md(out)
    for k, v in out["writes"].items():
        print(k, v.get("outcome"), v.get("error"), (v.get("compare") or {}).get("failures_by_check"))
    print("binding", out["binding"])
    return 0


def write_md(out: dict) -> None:
    L = ["# Q-5 pool round trip: fidelity", "", f"Versions: {out['versions']}; run {out['at']}.", "",
         "## ADBC result schema", "", "| column | Arrow type | field metadata |", "|---|---|---|"]
    L += [f"| {f['name']} | `{f['type']}` | {f['metadata']} |" for f in out["adbc_schema"]]
    L += ["", "## Write-back routes compared with `src_obs`", "", "| route | outcome | failing checks (row ids) | error |", "|---|---|---|---|"]
    for k, v in out["writes"].items():
        cmp = v.get("compare") or {}
        L.append(f"| {k} | {v.get('outcome')} | {cmp.get('failures_by_check') if cmp else '—'} | {v.get('error', '')} |")
    L += ["", "Checks per row: " + ", ".join(f"`{c}`" for c in CHECKS) + ".", "",
          "## DuckDB", "", f"Types after `register`: {out['duckdb']['duck_types']}", "",
          f"Absent versus null (`id, json_exists(payload,'$.b'), payload->'$.b', (payload->'$.b') IS NULL, json_type`): {out['duckdb']['absent_vs_null']}", "",
          f"Group-by: {out['duckdb']['group_by']}", "", f"Result lifecycle: {out['duckdb']['result_lifecycle']}", "",
          "Arrow out of DuckDB: " + ", ".join(f"{f['name']} `{f['type']}`" for f in out["duckdb"]["arrow_out_schema"]), "",
          "## Binding", "", "```json", json.dumps(out["binding"], indent=1, ensure_ascii=False, default=str), "```", "",
          "## ±infinity timestamps through ADBC", "", "```json", json.dumps(out["infinity_timestamps"], indent=1), "```", "",
          "## psycopg as loader", "", "```json", json.dumps(out["psycopg_loader"], indent=1, ensure_ascii=False, default=str), "```", ""]
    (OUT / "fidelity.md").write_text("\n".join(L))


# ---- memory -----------------------------------------------------------------------------------------

VOL_DDL = """
DROP TABLE IF EXISTS vol_obs, vol_claim;
CREATE TABLE vol_claim AS
SELECT g AS id, 'clm:' || md5(g::text) AS claim_key, (ARRAY['stat:has_distribution','stat:has_parameter','core:defines','stat:has_support'])[1 + g % 4] AS predicate,
       (g % 1000)::numeric / 7 AS weight
FROM generate_series(1, 20000) g;
CREATE TABLE vol_obs AS
SELECT g AS id, 9 AS run_id, (ARRAY['mention','relation','scope','value','claim_proposal'])[1 + g % 5] AS kind,
       'clm:' || md5((1 + g % 20000)::text) AS claim_key,
       jsonb_build_object('label', 'random variable', 'text', repeat('x', 40 + g % 80), 'start', g % 5000, 'end', g % 5000 + 12,
                          'attributes', jsonb_build_object('role', jsonb_build_object('label', 'subject', 'score', 0.83)),
                          'b', CASE WHEN g % 3 = 0 THEN NULL ELSE to_jsonb(g) END,
                          'span', jsonb_build_object('start', g, 'end', g + 3, 'label', 'distribution family')) - CASE WHEN g % 7 = 0 THEN 'b' ELSE '' END AS payload,
       (g::numeric / 1000) AS amount, timestamptz '2026-10-28 09:00:00Z' + g * interval '1 ms' AS at
FROM generate_series(1, %(n)s) g;
ANALYZE vol_obs; ANALYZE vol_claim;
"""


def cmd_memory(n: int) -> int:
    import duckdb
    import psycopg

    res: dict = {"rows": n, "versions": versions(), "steps": []}

    def step(name, **kw):
        s = status() | {"step": name} | kw
        res["steps"].append(s)
        print(n, s)

    with psycopg.connect(URI, autocommit=True) as c:
        exists = c.execute("SELECT count(*) FROM vol_obs").fetchone()[0] if c.execute("SELECT to_regclass('vol_obs')").fetchone()[0] else -1
        if exists != n:
            c.execute(VOL_DDL.replace("%(n)s", str(n)))
        res["pg_sizes"] = dict(c.execute("SELECT relname, pg_total_relation_size(oid) FROM pg_class WHERE relname IN ('vol_obs','vol_claim')").fetchall())
        res["payload_mean_bytes"] = float(c.execute("SELECT avg(octet_length(payload::text)) FROM vol_obs").fetchone()[0])
    step("start")
    t0 = time.perf_counter()
    _, obs = adbc_load("SELECT id, run_id, kind, claim_key, payload, amount, at FROM vol_obs WHERE run_id = 9")
    _, clm = adbc_load("SELECT id, claim_key, predicate, weight FROM vol_claim")
    step("after ADBC load (Arrow tables)", ms=round((time.perf_counter() - t0) * 1000, 1), arrow_obs_nbytes=obs.nbytes, arrow_claim_nbytes=clm.nbytes)
    con = duckdb.connect()
    prof = SCRATCH / f"q5_prof_{n}.json"
    con.register("obs", obs)
    con.register("clm", clm)
    step("after DuckDB register")
    con.execute("PRAGMA enable_profiling = 'json'")
    con.execute(f"SET profiling_output = '{prof}'")
    t0 = time.perf_counter()
    joined = con.sql("SELECT o.id, o.kind, o.payload, o.amount, o.\"at\", c.predicate, c.weight FROM obs o JOIN clm c USING (claim_key)").to_arrow_table()
    jms = round((time.perf_counter() - t0) * 1000, 1)
    pj = json.loads(prof.read_text())
    step("after join → Arrow", ms=jms, rows_out=joined.num_rows, arrow_out_nbytes=joined.nbytes, duckdb_system=pj.get("system"))
    t0 = time.perf_counter()
    grp = con.sql("SELECT c.predicate, o.kind, count(*) AS n, sum(CASE WHEN json_exists(o.payload, '$.b') THEN 1 ELSE 0 END) AS b_exists, "
                  "max(o.\"at\") AS last_at FROM obs o JOIN clm c USING (claim_key) GROUP BY ALL ORDER BY ALL").to_arrow_table()
    gms = round((time.perf_counter() - t0) * 1000, 1)
    pg2 = json.loads(prof.read_text())
    step("after join + group-by → Arrow", ms=gms, rows_out=grp.num_rows, duckdb_system=pg2.get("system"))
    con.execute("PRAGMA disable_profiling")
    res["duckdb_memory_after"] = [list(map(str, r)) for r in con.sql("SELECT tag, memory_usage_bytes FROM duckdb_memory() WHERE memory_usage_bytes > 0").fetchall()]
    con.close()
    del joined, grp
    step("after closing DuckDB and dropping results")
    # the psycopg loader on the same rows, for comparison (text loaders for jsonb and numeric)
    from psycopg.types.string import TextLoader
    import pyarrow as pa

    t0 = time.perf_counter()
    with psycopg.connect(URI) as c:
        for t in ("jsonb", "numeric"):
            c.adapters.register_loader(t, TextLoader)
        cur = c.cursor(binary=False)
        cur.execute("SELECT id, run_id, kind, claim_key, payload, amount, at FROM vol_obs WHERE run_id = %s", (9,))
        cols = list(zip(*cur.fetchall()))
    ptbl = pa.table({"id": pa.array(cols[0], pa.int64()), "run_id": pa.array(cols[1], pa.int64()), "kind": pa.array(cols[2]), "claim_key": pa.array(cols[3]),
                     "payload": pa.array(cols[4], pa.json_(pa.string())), "amount": pa.array(cols[5]), "at": pa.array(cols[6], pa.timestamp("us", tz="UTC"))})
    pms = round((time.perf_counter() - t0) * 1000, 1)
    del cols
    step("after psycopg load (Arrow table)", ms=pms, arrow_nbytes=ptbl.nbytes, equal_payload_to_adbc=storage_pylist(ptbl["payload"]) == storage_pylist(obs["payload"]))
    del ptbl
    # the same load as a parameterized SELECT (no COPY transport) and as a literal (COPY), timing only
    for label, sql, params in (("adbc literal run_id (COPY)", "SELECT id, run_id, kind, claim_key, payload, amount, at FROM vol_obs WHERE run_id = 9", None),
                               ("adbc $1 run_id (extended protocol)", "SELECT id, run_id, kind, claim_key, payload, amount, at FROM vol_obs WHERE run_id = $1", (9,))):
        t0 = time.perf_counter()
        _, t = adbc_load(sql, params)
        res.setdefault("adbc_routes_ms", {})[label] = {"ms": round((time.perf_counter() - t0) * 1000, 1), "rows": t.num_rows, "schema_equal_to_copy_route": t.schema.equals(obs.schema, check_metadata=True)}
        del t
    write_json(OUT / f"memory_{n}.json", res)
    return 0


def cmd_all() -> int:
    for args in (["create"], ["fidelity"], ["memory", "--rows", "100000"], ["memory", "--rows", "1000000"], ["drop"]):
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), *args])
        if r.returncode:
            return r.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for s in ("create", "fidelity", "drop", "all"):
        sub.add_parser(s)
    m = sub.add_parser("memory")
    m.add_argument("--rows", type=int, default=100000)
    a = ap.parse_args()
    return {"create": cmd_create, "fidelity": cmd_fidelity, "drop": cmd_drop, "all": cmd_all}.get(a.cmd, lambda: cmd_memory(a.rows))()


if __name__ == "__main__":
    raise SystemExit(main())
