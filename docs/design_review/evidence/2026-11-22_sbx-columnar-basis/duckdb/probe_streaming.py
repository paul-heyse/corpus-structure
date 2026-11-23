"""DuckDB 2.0.0: does relation.to_arrow_reader() stream a non-blocking plan from a Python
RecordBatchReader, and what happens when one single-use reader is referenced twice?

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_streaming.py
"""

import duckdb
import pyarrow as pa

SCHEMA = pa.schema([("k", pa.int64()), ("v", pa.string())])
N = 2000  # input batches of 1,000 rows


class Counting:
    def __init__(self):
        self.pulled = 0

    def gen(self):
        for i in range(N):
            self.pulled += 1
            yield pa.RecordBatch.from_pydict({"k": list(range(i * 1000, i * 1000 + 1000)), "v": ["x"] * 1000}, schema=SCHEMA)

    def reader(self):
        return pa.RecordBatchReader.from_batches(SCHEMA, self.gen())


print("duckdb", duckdb.__version__)
for threads in (1, 4):
    for pio in (True, False):
        con = duckdb.connect(config={"threads": threads, "preserve_insertion_order": pio})
        src = Counting()
        con.register("src", src.reader())
        rel = con.sql("SELECT k, sha256(v) AS h FROM src WHERE k % 2 = 0")
        rd = rel.to_arrow_reader(batch_size=1024)
        at_reader = src.pulled
        rd.read_next_batch()
        at_first = src.pulled
        rd.close()
        at_close = src.pulled
        ok = con.sql("SELECT 1").fetchall() == [(1,)]
        print(f"S1 threads={threads} preserve_insertion_order={pio}: pulled at to_arrow_reader() {at_reader}/{N}, "
              f"after first batch {at_first}/{N}, after close {at_close}/{N}; connection reusable {ok}")
        con.close()

# S2 from_arrow(reader) relation vs register: also lazy?
con = duckdb.connect(config={"threads": 1})
src = Counting()
rel = con.from_arrow(src.reader()).filter(duckdb.col("k") < duckdb.lit(5))
rd = rel.to_arrow_reader(batch_size=1024)
print(f"S2 from_arrow(reader).filter(k<5).to_arrow_reader(): pulled at reader {src.pulled}/{N}; first batch rows {rd.read_next_batch().num_rows}; pulled {src.pulled}")
rd.close()

# S3 single-use reader referenced twice in one statement (self-join, no CTE)
for q in ("SELECT count(*) FROM src a JOIN src b USING (k)",
          "SELECT (SELECT count(*) FROM src) + (SELECT count(*) FROM src WHERE k >= 0)",
          "WITH t AS NOT MATERIALIZED (SELECT * FROM src) SELECT count(*) FROM t a JOIN t b USING (k)"):
    con = duckdb.connect(config={"threads": 4})
    src = Counting()
    con.register("src", src.reader())
    try:
        print(f"S3 {q!r}: {con.sql(q).fetchall()} (expected {N * 1000} / {2 * N * 1000}), pulled {src.pulled}")
    except duckdb.Error as e:
        print(f"S3 {q!r}: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
    try:
        print("   plan:", " | ".join(l.strip() for l in con.sql("EXPLAIN " + q).fetchall()[0][1].splitlines() if l.strip())[:400])
    except duckdb.Error as e:
        print("   plan error", type(e).__name__)
    con.close()

# S4 which construction drains the reader eagerly?
cases = {
    "register + pushable filter k<5": lambda con, r: (con.register("src", r), con.sql("SELECT * FROM src WHERE k < 5"))[1],
    "register + pushable non-selective filter k<1500000": lambda con, r: (con.register("src", r), con.sql("SELECT * FROM src WHERE k < 1500000"))[1],
    "register + projection only": lambda con, r: (con.register("src", r), con.sql("SELECT k FROM src"))[1],
    "from_arrow(reader), no filter": lambda con, r: con.from_arrow(r),
    "from_arrow(reader) + sql non-pushable": lambda con, r: con.from_arrow(r).query("x", "SELECT * FROM x WHERE k % 2 = 0"),
    "from_arrow(pa.dataset over reader)": None,
}
for label, build in cases.items():
    if build is None:
        continue
    con = duckdb.connect(config={"threads": 1})
    src = Counting()
    rel = build(con, src.reader())
    built = src.pulled
    rd = rel.to_arrow_reader(batch_size=1024)
    at_reader = src.pulled
    rd.read_next_batch()
    print(f"S4 {label}: pulled after build {built}, at to_arrow_reader() {at_reader}, after first batch {src.pulled} of {N}")
    rd.close()
    con.close()
