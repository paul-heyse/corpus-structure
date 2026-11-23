"""DuckDB 2.0.0 plan shapes: range/IE join selection at non-trivial sizes, filter pushdown into
Arrow Table vs pyarrow.dataset, ASOF, and the join build side over an unknown-cardinality reader.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_plans.py
"""

import duckdb
import pyarrow as pa
import pyarrow.dataset as ds


def ops(plan):
    names = []
    for line in plan.splitlines():
        if "─ " in line and "╭" in line:
            for part in line.split("╭─ ")[1:]:
                names.append(part.split(" ─")[0].strip())
    return names


con = duckdb.connect(config={"threads": 4})
tok = pa.table({"block_id": [i // 50 for i in range(20000)], "ordinal": [i % 50 for i in range(20000)],
                "start": [10 * i for i in range(20000)], "end": [10 * i + 5 for i in range(20000)]})
sent = pa.table({"sid": list(range(2000)), "s_start": [100 * i for i in range(2000)], "s_end": [100 * i + 100 for i in range(2000)]})
con.register("tok", tok)
con.register("sent", sent)
con.register("tok_ds", ds.dataset(tok))

def show(label, q):
    plan = con.sql("EXPLAIN " + q).fetchall()[0][1]
    print(f"{label}: {ops(plan)}")
    return plan

show("P1 containment (two inequalities, no equality)", 'SELECT s.sid, t.ordinal FROM tok t JOIN sent s ON t.start >= s.s_start AND t."end" <= s.s_end')
show("P2 single inequality", "SELECT count(*) FROM tok t JOIN sent s ON t.start >= s.s_start")
show("P3 overlap with equality key", 'SELECT count(*) FROM tok a JOIN tok b ON a.block_id = b.block_id AND a.ordinal < b.ordinal AND a.start < b."end" AND b.start < a."end"')
show("P4 ASOF", "SELECT t.ordinal, s.sid FROM tok t ASOF JOIN sent s ON t.start >= s.s_start")
show("P5 anti join", "SELECT * FROM tok t ANTI JOIN sent s ON t.block_id = s.sid")
p = show("P6 filter over Arrow Table", "SELECT ordinal FROM tok WHERE block_id = 3")
print("   Filter operator present above scan:", "Filter" in ops(p), "| scan has Filters:", "Filters:" in p)
p = show("P7 filter over pyarrow.dataset", "SELECT ordinal FROM tok_ds WHERE block_id = 3")
print("   Filter operator present above scan:", "Filter" in ops(p), "| scan has Filters:", "Filters:" in p)
print(p)
p = show("P8 EXCEPT ALL", "SELECT block_id, ordinal FROM tok EXCEPT ALL SELECT sid, 0 FROM sent")
p = con.sql("EXPLAIN (FORMAT JSON) SELECT block_id, count(*) FROM tok GROUP BY ALL").fetchall()[0][1]
print("P9 EXPLAIN (FORMAT JSON) available:", p.lstrip().startswith("["))
try:
    print("P10 EXPLAIN (SQL):", con.sql("EXPLAIN (SQL) SELECT block_id, count(*) FROM tok WHERE 1 = 1 GROUP BY ALL").fetchall())
except duckdb.Error as e:
    print("P10 EXPLAIN (SQL) over a registered Arrow table:", type(e).__name__, str(e).splitlines()[0])
print("P10b EXPLAIN (SQL) over range():", con.sql("EXPLAIN (SQL) SELECT range % 3 AS g, count(*) FROM range(10) WHERE 1 = 1 GROUP BY ALL").fetchall())
