"""Set-interface contracts that pair with Arrow transfer (PostgreSQL 18).

Streaming ingest without materialization, statement-trigger granularity under ADBC ingest,
typed-array parameters (ADBC Arrow bind, psycopg binary), MERGE from staged rows, JSON_TABLE
document-to-rows, composite[] -> jsonb, infinity timestamps in Arrow. Scratch database only.
Writes ``raw/set_interfaces.json``. Usage: uv run python <this file>
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import adbc_driver_postgresql.dbapi as adbc
import psycopg
import pyarrow as pa

DB = "sbx_columnar_probe_scratch"
URI = f"postgresql:///{DB}?host=/var/run/postgresql&port=5434"
PG = f"dbname={DB} host=/var/run/postgresql port=5434"
OUT = Path(__file__).with_name("raw") / "set_interfaces.json"
D103 = "12345678902345678902345678902345678902345678902345678902345678902345678902345678902345678902345678.12345"
res: dict[str, object] = {}


def rec(k, v):
    res[k] = v
    print(k, "=>", v)


def err(e):
    return f"{type(e).__name__}: {str(e).splitlines()[0][:220]}"


with psycopg.connect(PG, autocommit=True) as obs:
    obs.execute("""
    DROP SCHEMA IF EXISTS si CASCADE; CREATE SCHEMA si;
    CREATE TABLE si.target (k bigint PRIMARY KEY, v text);
    CREATE TABLE si.fired (stmt_rows bigint);
    CREATE FUNCTION si.count_new() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN INSERT INTO si.fired SELECT count(*) FROM new_rows; RETURN NULL; END $$;
    CREATE TRIGGER t_stmt AFTER INSERT ON si.target REFERENCING NEW TABLE AS new_rows
      FOR EACH STATEMENT EXECUTE FUNCTION si.count_new();
    INSERT INTO si.target SELECT g, 'old' FROM generate_series(1, 10) g;
    TRUNCATE si.fired;
    """)
    conn = adbc.connect(URI)
    cur = conn.cursor()
    cur.execute("SELECT pg_backend_pid()")
    pid = cur.fetchone()[0]
    conn.rollback()
    schema = pa.schema([("k", pa.int64()), ("v", pa.string())])
    progress = []

    def gen():
        for b in range(5):
            progress.append(obs.execute(
                "select coalesce((select tuples_processed from pg_stat_progress_copy where pid=%s), -1)",
                (pid,)).fetchone()[0])
            yield pa.record_batch([pa.array(range(100 + b * 1000, 100 + (b + 1) * 1000), pa.int64()),
                                   pa.array(["new"] * 1000)], schema=schema)

    n = cur.adbc_ingest("target", pa.RecordBatchReader.from_batches(schema, gen()),
                        mode="append", db_schema_name="si")
    rec("ingest_rows", n)
    rec("server_tuples_processed_when_producer_asked_for_each_batch", progress)
    conn.commit()
    rec("statement_trigger_firings_and_rows_for_one_5_batch_ingest",
        obs.execute("select array_agg(stmt_rows) from si.fired").fetchone()[0])

    # staged rows -> MERGE in the same transaction, returning merge_action() (PG17+)
    cur.adbc_ingest("delta", pa.table({"k": pa.array([1, 2, 999999], pa.int64()),
                                       "v": ["upd", None, "ins"]}), mode="create", temporary=True)
    cur.execute("""
      MERGE INTO si.target t USING pg_temp.delta d ON t.k = d.k
      WHEN MATCHED AND d.v IS NULL THEN DELETE
      WHEN MATCHED THEN UPDATE SET v = d.v
      WHEN NOT MATCHED THEN INSERT VALUES (d.k, d.v)
      RETURNING merge_action(), t.k""")
    rec("merge_from_staged_returning_via_adbc", sorted(cur.fetchall()))
    conn.rollback()

    # typed array parameters bound from Arrow through ADBC
    for label, arr, sql in (
        ("int8_list", pa.array([[1, 2, 3]], pa.list_(pa.int64())), "SELECT * FROM unnest($1::bigint[]) WITH ORDINALITY"),
        ("text_list", pa.array([["é", None]], pa.list_(pa.string())), "SELECT * FROM unnest($1::text[]) WITH ORDINALITY"),
        ("decimal_list", pa.array([[Decimal("1.5")]], pa.list_(pa.decimal128(10, 2))), "SELECT * FROM unnest($1::numeric[])"),
        ("string_103_as_numeric", pa.array([D103]), "SELECT ($1::text)::numeric::text = $1"),
    ):
        try:
            cur.execute(sql, parameters=pa.record_batch([arr], names=["p"]))
            rec(f"adbc_bind_{label}", cur.fetchall())
        except Exception as e:  # noqa: BLE001
            rec(f"adbc_bind_{label}", err(e))
        conn.rollback()
    cur.close()
    conn.close()

    # psycopg binary typed arrays: unnest of parallel columns, exact numeric
    with psycopg.connect(PG) as pc, pc.cursor(binary=True) as c:
        c.execute("SELECT k, n::text, t FROM unnest(%b::int8[], %b::numeric[], %b::text[]) "
                  "WITH ORDINALITY AS u(k, n, t, ord) ORDER BY ord",
                  ([1, 2], [Decimal(D103), Decimal("NaN")], ["é", None]))
        rows = c.fetchall()
        rec("psycopg_binary_unnest_parallel_arrays", rows)
        rec("psycopg_binary_numeric_103_exact", rows[0][1] == D103)
        pc.rollback()

    # one document turned into rows server-side once: JSON_TABLE (PG17+) with exact numeric
    doc = json.dumps({"items": [{"id": 1, "w": D103, "tags": ["a"]}, {"id": 2, "w": "0.5", "tags": []}]})
    rows = obs.execute("""
      SELECT jt.* FROM JSON_TABLE(%s::jsonb, '$.items[*]' COLUMNS (
        ord FOR ORDINALITY, id bigint PATH '$.id', w numeric PATH '$.w', tags jsonb PATH '$.tags'))
      AS jt""", (doc,)).fetchall()
    rec("json_table_rows", [(r[0], r[1], str(r[2]) == D103 if r[1] == 1 else str(r[2]), r[3]) for r in rows])
    # numeric JSON number (not string) through jsonb: exact?
    r = obs.execute("SELECT ((%s::jsonb)->'w')::numeric::text", (f'{{"w": {D103}}}',)).fetchone()[0]
    rec("jsonb_number_103_digits_exact", r == D103)

    # composite[] staged by pgpq-like route -> jsonb server-side
    rec("composite_array_to_jsonb", obs.execute(
        "SELECT to_jsonb(ARRAY[ROW(1,5,'w')::tm.span, ROW(6,9,NULL)::tm.span])").fetchone()[0])

    # infinity timestamptz arrives in Arrow as what?
    a = adbc.connect(URI, autocommit=True)
    c = a.cursor()
    c.execute("SELECT 'infinity'::timestamptz AS v UNION ALL SELECT '-infinity' UNION ALL SELECT '2000-01-01Z'")
    t = c.fetch_arrow_table()
    rec("timestamptz_infinity_arrow_int64", t.column("v").cast(pa.int64()).to_pylist())
    c.execute("SELECT 'infinity'::date AS v")
    try:
        rec("date_infinity_arrow_int32", c.fetch_arrow_table().column("v").cast(pa.int32()).to_pylist())
    except Exception as e:  # noqa: BLE001
        rec("date_infinity_arrow_int32", err(e))
    # adbc_execute_schema / prepare parameter schema for a set routine call
    try:
        rec("execute_schema_set_routine", str(c.adbc_execute_schema(
            "SELECT * FROM unnest('{1}'::bigint[]) WITH ORDINALITY")))
    except Exception as e:  # noqa: BLE001
        rec("execute_schema_set_routine", err(e))
    try:
        rec("prepare_parameter_schema", str(c.adbc_prepare("SELECT $1::bigint[] AS a, $2::numeric AS b")))
    except Exception as e:  # noqa: BLE001
        rec("prepare_parameter_schema", err(e))
    c.close()
    a.close()

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
