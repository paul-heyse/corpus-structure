"""Staged-relation boundary probe: ADBC ingest -> set routine -> Arrow result, one session.

Runs only against the worker-owned scratch database ``sbx_columnar_probe_scratch`` on the
dedicated cluster (port 5434). Writes ``raw/staged_session.json`` next to this file.
Usage: uv run python <this file>
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import adbc_driver_postgresql.dbapi as adbc
import psycopg
import pyarrow as pa

DB = "sbx_columnar_probe_scratch"
URI = f"postgresql:///{DB}?host=/var/run/postgresql&port=5434&application_name=adbc_probe"
PG = f"dbname={DB} host=/var/run/postgresql port=5434 application_name=observer"
OUT = Path(__file__).with_name("raw") / "staged_session.json"
results: dict[str, object] = {}


def record(key, value):
    results[key] = value
    print(key, "=>", value)


def err(e: BaseException) -> dict:
    return {
        "type": type(e).__name__,
        "message": str(e).splitlines()[0][:300],
        "sqlstate": getattr(e, "sqlstate", None),
        "status_code": str(getattr(e, "status_code", None)),
        "vendor_code": getattr(e, "vendor_code", None),
        "details": [
            (k, v[:200].decode(errors="replace") if isinstance(v, bytes) else str(v)[:200])
            for k, v in (getattr(e, "details", None) or [])
        ],
    }


def tx_status(conn) -> str:
    return conn.adbc_connection.get_option("adbc.postgresql.transaction_status")


setup = """
DROP SCHEMA IF EXISTS probe CASCADE;
CREATE SCHEMA probe;
CREATE TABLE probe.item (item_id bigint PRIMARY KEY, label text NOT NULL);
INSERT INTO probe.item SELECT g, 'item-' || g FROM generate_series(1, 1000) g;
CREATE TABLE probe.settled (
    claim_id bigint NOT NULL, item_id bigint NOT NULL REFERENCES probe.item,
    weight bigint NOT NULL CHECK (weight >= 0), tags text[] NOT NULL,
    PRIMARY KEY (claim_id, item_id));
-- Routine with no document parameter: reads the session's staged relation.
CREATE FUNCTION probe.settle_staged(p_claim bigint)
RETURNS TABLE (item_id bigint, label text, weight bigint, tag_count int, backend int,
               lock_held boolean, local_guc text)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO probe.settled (claim_id, item_id, weight, tags)
    SELECT p_claim, s.item_id, s.weight, s.tags FROM pg_temp.staged s;
    RETURN QUERY
    SELECT s.item_id, i.label, s.weight, cardinality(s.tags), pg_backend_pid(),
           EXISTS (SELECT 1 FROM pg_locks l WHERE l.locktype = 'advisory'
                   AND l.pid = pg_backend_pid() AND l.objid = p_claim::oid),
           current_setting('probe.claim', true)
    FROM pg_temp.staged s JOIN probe.item i USING (item_id)
    ORDER BY s.item_id;
END $$;
"""

with psycopg.connect(PG, autocommit=True) as obs:
    obs.execute(setup)
    record("server_version", obs.execute("show server_version").fetchone()[0])

    def sessions_total() -> int:
        obs.execute("select pg_stat_force_next_flush()")
        obs.execute("select pg_stat_clear_snapshot()")
        return obs.execute(
            "select sessions from pg_stat_database where datname = %s", (DB,)
        ).fetchone()[0]

    # --- sessions opened by one adbc connect ------------------------------------------
    before = sessions_total()
    bare = adbc.connect(URI)
    bare.close()
    time.sleep(1.0)
    record("observer_sessions_delta_for_one_bare_adbc_connect", sessions_total() - before)
    conn = adbc.connect(URI)  # autocommit=False is the DBAPI default
    time.sleep(1.0)
    pids_visible = obs.execute(
        "select pid from pg_stat_activity where datname=%s and application_name='adbc_probe'",
        (DB,),
    ).fetchall()
    record("adbc_connect_visible_backends", len(pids_visible))
    cur = conn.cursor()
    cur.execute("select pg_backend_pid()")
    pid = cur.fetchone()[0]
    record("adbc_backend_pid", pid)
    record("tx_status_after_first_select", tx_status(conn))
    conn.rollback()

    # --- non-result statements with use_copy on (default) ------------------------------
    for label, stmt in {
        "begin_set_local": "SET LOCAL probe.claim = '42'",
        "advisory_lock": "SELECT pg_advisory_xact_lock(42)",
    }.items():
        try:
            cur.execute(stmt)
            record(f"use_copy_default_{label}", "ok")
        except Exception as e:  # noqa: BLE001
            record(f"use_copy_default_{label}", err(e))
            conn.rollback()
    conn.rollback()

    # --- the end-to-end unit of work ---------------------------------------------------
    # nested Arrow stream: list<string> tags and a struct column carried alongside
    schema = pa.schema(
        [
            pa.field("item_id", pa.int64(), nullable=False),
            pa.field("weight", pa.int64(), nullable=False),
            pa.field("tags", pa.list_(pa.string()), nullable=False),
        ]
    )

    def batches(n_batches=4, per=250, fail_at=None):
        for b in range(n_batches):
            if fail_at is not None and b == fail_at:
                raise RuntimeError("producer failed mid-stream")
            ids = list(range(b * per + 1, (b + 1) * per + 1))
            yield pa.record_batch(
                [
                    pa.array(ids, pa.int64()),
                    pa.array([i % 7 for i in ids], pa.int64()),
                    pa.array([[f"t{i}", "é漢🙂"][: 1 + i % 2] for i in ids], pa.list_(pa.string())),
                ],
                schema=schema,
            )

    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
    cur.execute("SET LOCAL probe.claim = '42'")
    cur.execute("SELECT pg_advisory_xact_lock(42)")
    cur.execute("SELECT pg_backend_pid()")
    record("unit_pid_matches_connection", cur.fetchone()[0] == pid)
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
    record("tx_status_before_ingest", tx_status(conn))
    reader = pa.RecordBatchReader.from_batches(schema, batches())
    n = cur.adbc_ingest("staged", reader, mode="create", temporary=True)
    record("ingest_rows_returned", n)
    record("tx_status_after_ingest", tx_status(conn))
    staged_type = obs.execute(
        "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where c.relname='staged' and n.nspname like 'pg_temp%%'"
    ).fetchone()[0]
    record("observer_sees_uncommitted_temp_table_in_catalog", staged_type)
    cur.execute("SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'pg_temp.staged'::regclass AND attnum > 0 ORDER BY attnum")
    record("temp_table_inferred_types", [r[0] for r in cur.fetchall()])
    # observer cannot see the lock holder's uncommitted settled rows; lock is visible
    lock_rows = obs.execute(
        "select pid, granted from pg_locks where locktype='advisory' and objid=42"
    ).fetchall()
    record("observer_sees_advisory_lock_pid", [r[0] == pid for r in lock_rows])

    cur.execute("SELECT * FROM probe.settle_staged(42)")
    reader = cur.fetch_record_batch()
    record("result_schema", [str(f) for f in reader.schema])
    tbl = reader.read_all()
    record("result_rows", tbl.num_rows)
    record("result_backend_is_connection", set(tbl.column("backend").to_pylist()) == {pid})
    record("result_lock_held_inside_routine", set(tbl.column("lock_held").to_pylist()))
    record("result_set_local_visible_inside_copy_query", set(tbl.column("local_guc").to_pylist()))
    record("result_nonascii_tagcount_sample", tbl.slice(0, 2).to_pylist())
    before_commit = obs.execute("select count(*) from probe.settled").fetchone()[0]
    record("observer_settled_rows_before_commit", before_commit)
    record("tx_status_before_commit", tx_status(conn))
    conn.commit()
    record("observer_settled_rows_after_commit", obs.execute("select count(*) from probe.settled").fetchone()[0])
    record("observer_lock_after_commit", obs.execute(
        "select count(*) from pg_locks where locktype='advisory' and objid=42").fetchone()[0])
    record("guc_after_commit", (cur.execute("select current_setting('probe.claim', true)"), cur.fetchone()[0])[1])
    # temp table survives commit (session scope) unless ON COMMIT DROP
    cur.execute("select count(*) from pg_temp.staged")
    record("temp_table_rows_after_commit", cur.fetchone()[0])
    conn.commit()

    # --- reuse a pre-created session temp table (append + temporary) ---------------------
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
    cur.execute("DROP TABLE pg_temp.staged")
    cur.execute(
        "CREATE TEMP TABLE staged (item_id bigint NOT NULL, weight bigint NOT NULL, "
        "tags text[] NOT NULL) ON COMMIT DELETE ROWS"
    )
    conn.commit()
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
    n = cur.adbc_ingest("staged", pa.RecordBatchReader.from_batches(schema, batches(1, 10)),
                        mode="append", temporary=True)
    cur.execute("select count(*) from pg_temp.staged")
    record("append_temporary_into_precreated_rows", (n, cur.fetchone()[0]))
    conn.commit()
    cur.execute("select count(*) from pg_temp.staged")
    record("on_commit_delete_rows_after_commit", cur.fetchone()[0])
    conn.commit()
    # catalog churn: does append into the pre-created table create relations?
    relcount = lambda: obs.execute("select count(*) from pg_class").fetchone()[0]  # noqa: E731
    r0 = relcount()
    for _ in range(5):
        cur.adbc_ingest("staged", pa.RecordBatchReader.from_batches(schema, batches(1, 10)),
                        mode="append", temporary=True)
        conn.commit()
    r1 = relcount()
    for i in range(5):
        cur.adbc_ingest(f"churn_{i}", pa.RecordBatchReader.from_batches(schema, batches(1, 10)),
                        mode="create", temporary=True)
        conn.commit()
    r2 = relcount()
    record("pg_class_delta_append_x5_vs_create_x5", (r1 - r0, r2 - r1))

    # --- error mid-ingest: constraint violation in batch 3 into a permanent table ----------
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
    cur.execute("INSERT INTO probe.item VALUES (5000, 'pre-ingest work')")
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
    bad = pa.schema([pa.field("claim_id", pa.int64()), pa.field("item_id", pa.int64()),
                     pa.field("weight", pa.int64()), pa.field("tags", pa.list_(pa.string()))])

    def bad_batches():
        for b in range(4):
            yield pa.record_batch([
                pa.array([7] * 10, pa.int64()), pa.array(range(b * 10 + 1, b * 10 + 11), pa.int64()),
                pa.array([-1 if b == 2 else 1] * 10, pa.int64()), pa.array([["x"]] * 10)],
                schema=bad)

    try:
        cur.adbc_ingest("settled", pa.RecordBatchReader.from_batches(bad, bad_batches()),
                        mode="append", db_schema_name="probe")
        record("constraint_mid_ingest", "no error")
    except Exception as e:  # noqa: BLE001
        record("constraint_mid_ingest", err(e))
    record("tx_status_after_constraint_error", tx_status(conn))
    try:
        cur.execute("select 1")
        cur.fetchall()
        record("statement_after_error_without_rollback", "ok")
    except Exception as e:  # noqa: BLE001
        record("statement_after_error_without_rollback", err(e))
    conn.rollback()
    cur.execute("select count(*) from probe.item where item_id = 5000")
    record("pre_ingest_work_after_rollback", cur.fetchone()[0])
    cur.execute("select count(*) from probe.settled where claim_id = 7")
    record("partial_ingest_rows_after_rollback", cur.fetchone()[0])
    conn.rollback()

    # --- producer (Python) exception mid-stream -----------------------------------------
    try:
        cur.adbc_ingest("settled", pa.RecordBatchReader.from_batches(
            schema, batches(4, 10, fail_at=2)), mode="append", db_schema_name="probe")
        record("producer_failure_mid_ingest", "no error")
    except Exception as e:  # noqa: BLE001
        record("producer_failure_mid_ingest", err(e))
    record("tx_status_after_producer_error", tx_status(conn))
    conn.rollback()
    cur.execute("select 1")
    record("connection_usable_after_producer_error_rollback", cur.fetchone()[0] == 1)
    conn.rollback()

    # --- unique violation diagnostics via a result-producing statement ----------------------
    try:
        cur.execute("INSERT INTO probe.item VALUES (1, 'dup') RETURNING item_id")
        cur.fetchall()
    except Exception as e:  # noqa: BLE001
        record("unique_violation_copy_path", err(e))
    conn.rollback()
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
    try:
        cur.execute("INSERT INTO probe.item VALUES (1, 'dup') RETURNING item_id")
        cur.fetchall()
    except Exception as e:  # noqa: BLE001
        record("unique_violation_nocopy_path", err(e))
    conn.rollback()
    try:
        cur.execute("INSERT INTO probe.item VALUES ($1, $2) RETURNING item_id", parameters=(1, "dup"))
        cur.fetchall()
    except Exception as e:  # noqa: BLE001
        record("unique_violation_bound_path", err(e))
    conn.rollback()
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})

    # --- statement_timeout via SET LOCAL and cancellation ----------------------------------
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
    cur.execute("SET LOCAL statement_timeout = '200ms'")
    cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
    try:
        cur.execute("SELECT pg_sleep(2)")
        cur.fetchall()
        record("statement_timeout", "no error")
    except Exception as e:  # noqa: BLE001
        record("statement_timeout", err(e))
    conn.rollback()
    t = threading.Timer(0.3, cur.adbc_cancel)
    t.start()
    t0 = time.monotonic()
    try:
        cur.execute("SELECT pg_sleep(5)")
        cur.fetchall()
        record("adbc_cancel", "no error")
    except Exception as e:  # noqa: BLE001
        record("adbc_cancel", {**err(e), "elapsed_s": round(time.monotonic() - t0, 2)})
    record("tx_status_after_cancel", tx_status(conn))
    conn.rollback()

    # --- parameterized result query against the set routine; Arrow multi-row bind ----------
    cur.execute("select count(*) from probe.settled")
    base = cur.fetchone()[0]
    cur.execute("SELECT item_id, label FROM probe.item WHERE item_id = $1", parameters=(3,))
    record("bound_select", cur.fetchall())
    params = pa.record_batch([pa.array([4, 5, 6], pa.int64())], names=["p"])
    cur.execute("SELECT item_id, label FROM probe.item WHERE item_id = $1", parameters=params)
    record("bound_select_arrow_three_rows_one_stream", cur.fetch_arrow_table().to_pylist())
    conn.rollback()

    # --- COPY (data-modifying CTE / RETURNING) TO via use_copy path ---------------------------
    try:
        cur.execute("WITH ins AS (INSERT INTO probe.item VALUES (6001,'w') RETURNING *) SELECT * FROM ins")
        record("copy_wrapped_data_modifying_cte", cur.fetchall())
    except Exception as e:  # noqa: BLE001
        record("copy_wrapped_data_modifying_cte", err(e))
    conn.rollback()
    try:
        cur.execute("INSERT INTO probe.item VALUES (6002,'w') RETURNING *")
        record("copy_wrapped_insert_returning", cur.fetchall())
    except Exception as e:  # noqa: BLE001
        record("copy_wrapped_insert_returning", err(e))
    conn.rollback()

    # --- multi-statement and multiple result sets --------------------------------------
    try:
        cur.execute("SELECT 1; SELECT 2")
        record("multi_statement_execute", cur.fetchall())
    except Exception as e:  # noqa: BLE001
        record("multi_statement_execute", err(e))
    conn.rollback()
    try:
        cur.nextset()
    except Exception as e:  # noqa: BLE001
        record("nextset", err(e))

    # --- batch size hint on a COPY result ------------------------------------------------
    cur.adbc_statement.set_options(**{"adbc.postgresql.batch_size_hint_bytes": "4096"})
    cur.execute("SELECT g AS id, repeat('x', 50) AS t FROM generate_series(1, 5000) g")
    rdr = cur.fetch_record_batch()
    sizes = [b.num_rows for b in rdr]
    record("copy_batch_rows_with_4096_hint", {"batches": len(sizes), "first": sizes[:3]})
    cur.execute("SELECT g AS id, repeat('x', 50) AS t FROM generate_series(1, $1) g",
                parameters=(5000,))
    sizes = [b.num_rows for b in cur.fetch_record_batch()]
    record("bound_batch_rows_with_4096_hint", {"batches": len(sizes), "first": sizes[:3]})
    conn.rollback()
    cur.close()
    conn.close()

    # --- psycopg comparator: COPY into temp + routine + binary cursor, same transaction ------
    with psycopg.connect(PG) as pc:
        with pc.cursor() as c:
            c.execute("SET LOCAL probe.claim = '43'")
            c.execute("SELECT pg_advisory_xact_lock(43)")
            c.execute("CREATE TEMP TABLE staged (item_id bigint, weight bigint, tags text[]) "
                      "ON COMMIT DROP")
            with c.copy("COPY pg_temp.staged FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "int8", "text[]"])
                for i in range(1, 11):
                    cp.write_row((i, i % 7, [f"t{i}"]))
        with pc.cursor(binary=True) as c:
            c.execute("SELECT item_id, weight, lock_held, local_guc FROM probe.settle_staged(43)")
            rows = c.fetchall()
        record("psycopg_comparator_rows", (len(rows), rows[0]))
        pc.rollback()

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(results, indent=2, default=str))
