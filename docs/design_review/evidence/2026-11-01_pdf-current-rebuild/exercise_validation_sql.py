"""Exercise only proposed read-only structural predicates over the preserved run9 rows."""
from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg

BUILD = "9372bc8fe8c89ac1d3b3a9ca57959846b81c6d44df78f09ad93402a56632056c"
ROOT = Path(__file__).resolve().parent


def main():
    source = Path("python/corpus-structure/src/corpus_structure/semantic/pdf_publication_native.py").read_text().replace("\\\n", "")
    first = source.index(" WITH RECURSIVE owner_edges AS MATERIALIZED")
    last = source.index(" IF bad_owner_ THEN", first)
    ownership = source[first:last].strip().rstrip(";").replace("INTO bad_owner_,unreachable_", "")
    first = source.index(" IF EXISTS(WITH member_counts AS")
    last = source.index(" THEN\n RAISE EXCEPTION 'native ordered membership", first)
    membership = "SELECT " + source[first:last].strip()[3:]
    access = Path("python/corpus-structure/src/corpus_structure/semantic/sql/pdf_record_access_correspondence.sql").read_text()
    first = access.index(" IF EXISTS(WITH region_counts AS")
    last = access.index(" THEN\n RAISE EXCEPTION 'native access regions", first)
    regions = "SELECT " + access[first:last].strip()[3:]
    output = dict(observed_at=datetime.now(UTC).isoformat(), outcome="passed", scope="three read-only structural predicates only; interrupted run9 remains unqualified", build_id=BUILD, checks={})
    with psycopg.connect("dbname=corpus_pdf_20261101 host=/var/run/postgresql port=5434") as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute("SET LOCAL statement_timeout='20s'")
        for name, query in (("ownership_and_reachability", ownership), ("ordered_membership", membership), ("region_counts_and_page_map", regions)):
            query = re.sub(r"\bp_build\b", "'" + BUILD + "'", query)
            plan = conn.execute("EXPLAIN (FORMAT JSON, COSTS FALSE) " + query).fetchone()[0]
            start = time.monotonic()
            result = conn.execute(query).fetchone()
            elapsed = time.monotonic() - start
            assert result == ((False, False) if name == "ownership_and_reachability" else (False,)), (name,result)
            output["checks"][name] = dict(query=query, result=result, elapsed_seconds=elapsed, explain=plan)
    path = ROOT / "runtime/validation-sql-structural-exercise.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({name:{"result":v["result"],"elapsed_seconds":v["elapsed_seconds"]} for name,v in output["checks"].items()}))


if __name__ == "__main__":
    main()
