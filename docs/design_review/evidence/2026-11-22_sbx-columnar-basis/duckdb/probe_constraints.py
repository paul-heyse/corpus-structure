"""DuckDB 2.0.0: temp-table constraints as validation (what a violation reports), TRY and error(),
and bool_and over an empty group.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_constraints.py
"""

import duckdb
import pyarrow as pa

con = duckdb.connect()
t = pa.table({"block_id": [1, 1, 1, 2], "ordinal": [0, 1, 1, 0], "start": [0, 5, 9, 0], "end": [5, 3, 12, 4]})
con.register("t", t)
con.execute('CREATE TEMP TABLE tok (block_id BIGINT, ordinal BIGINT, start BIGINT, "end" BIGINT, '
            'PRIMARY KEY (block_id, ordinal), CHECK (start < "end"))')
try:
    con.execute("INSERT INTO tok SELECT * FROM t")
    print("K1 insert accepted")
except duckdb.Error as e:
    print(f"K1 constraint violation: {type(e).__name__}: {str(e).splitlines()[0][:200]}")
print("K1 rows retained after failed statement:", con.sql("SELECT count(*) FROM tok").fetchall()[0][0])

try:
    con.sql("SELECT CASE WHEN start < \"end\" THEN 1 ELSE error('span_order at ' || block_id || ':' || ordinal) END FROM t").fetchall()
except duckdb.Error as e:
    print(f"K2 error() aborts at first failing row: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
try:
    print("K3 TRY(error()) ->", con.sql("SELECT TRY(CASE WHEN start < \"end\" THEN 1 ELSE error('x') END) FROM t ORDER BY ALL").fetchall())
except duckdb.Error as e:
    print(f"K3 TRY(error()): {type(e).__name__}: {str(e).splitlines()[0][:160]}")
print("K4 bool_and over empty group ->", con.sql("SELECT bool_and(x) FROM (SELECT true AS x WHERE false)").fetchall(),
      "| coalesce(bool_and(x), true) ->", con.sql("SELECT coalesce(bool_and(x), true) FROM (SELECT true AS x WHERE false)").fetchall())
print("K5 FILTER aggregates, several rules in one pass ->", con.sql(
    "SELECT block_id, count(*) FILTER (WHERE start >= \"end\") AS span_order, "
    "count(*) - count(DISTINCT ordinal) AS duplicate_ordinals FROM t GROUP BY ALL ORDER BY ALL").fetchall())
print("K6 UNNEST WITH ORDINALITY ->", con.sql(
    "SELECT u.* FROM (SELECT [10, 20, 30] AS l) s, unnest(s.l) WITH ORDINALITY AS u(v, ord)").fetchall())
