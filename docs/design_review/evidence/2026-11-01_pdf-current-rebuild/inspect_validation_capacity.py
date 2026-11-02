"""Read-only current frozen-build inventory and EXPLAIN, never ANALYZE or a guard call."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg

BUILD = "9372bc8fe8c89ac1d3b3a9ca57959846b81c6d44df78f09ad93402a56632056c"
ROOT = Path(__file__).resolve().parent
OWNER = Path("python/corpus-structure/src/corpus_structure/semantic/sql/pdf_record_access_correspondence.sql")


def main():
    source = OWNER.read_text()
    start = source.index(" IF EXISTS(SELECT FROM kb.pdf_record_access a WHERE a.product_id=p_build AND\n (SELECT count(*)")
    stop = source.index(" THEN\n RAISE EXCEPTION 'native access regions", start)
    expression = source[start:stop].strip()
    assert expression.startswith("IF ")
    query = "SELECT " + expression[3:].replace("p_build", "'" + BUILD + "'")
    with psycopg.connect("dbname=corpus_pdf_20261101 host=/var/run/postgresql port=5434") as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout='5s'")
        conn.execute("SET LOCAL ROLE corpus_sem_publisher")
        assert conn.execute("SELECT current_database()").fetchone()[0] == "corpus_pdf_20261101"
        settings = dict(conn.execute("SELECT name,setting FROM pg_settings WHERE name IN ('max_worker_processes','max_parallel_workers','max_parallel_workers_per_gather','work_mem','jit')"))
        counts = {}
        for name in ("native", "membership", "reference", "access", "region", "companion", "endpoint"):
            relation = "kb.pdf_record_" + name
            counts[name] = conn.execute("SELECT count(*) FROM " + relation + " WHERE product_id=%s", (BUILD,)).fetchone()[0]
        plan = conn.execute("EXPLAIN (FORMAT JSON, COSTS TRUE) " + query).fetchone()[0]
        indexes = conn.execute("SELECT tablename,indexdef FROM pg_indexes WHERE schemaname='kb' AND tablename IN ('pdf_record_membership','pdf_record_native','pdf_record_region') ORDER BY tablename,indexname").fetchall()
        functions = conn.execute("SELECT pronamespace::regnamespace::text,proname,proparallel,provolatile,prosecdef FROM pg_proc WHERE proname IN ('validate_pdf_build','pdf_native_record_shape','pdf_check_access_correspondence','pdf_record_logical_identity','pdf_projection_contract','pdf_identity_verify_artifact','pdf_identity_byte_root','pdf_reference_bytes_equal') ORDER BY proname").fetchall()
    output = dict(observed_at=datetime.now(UTC).isoformat(), outcome="passed", scope="read-only inventory and planner shape, no execution timing", build_id=BUILD, owner=str(OWNER), query=query, counts=counts, settings=settings, functions=functions, indexes=indexes, explain=plan)
    path = ROOT / "runtime/validation-capacity-current.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(dict(output=str(path), counts=counts, settings=settings)))


if __name__ == "__main__":
    main()
