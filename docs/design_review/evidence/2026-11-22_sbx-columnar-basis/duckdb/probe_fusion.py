"""DuckDB 2.0.0 fusion probe: one lazily executed plan from a streamed Arrow source of nested token
partitions to streamed Arrow output, with four invariants, typed diagnostics and a per-block digest.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_fusion.py
Synthetic data only. No timing is reported. Raw plans go to probe_fusion.out.
"""

import hashlib
import tempfile
import threading
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from corpus_structure.core.canonical import canonical_json

print("duckdb", duckdb.__version__, "pyarrow", pa.__version__)

ATTRS = pa.struct([("flags", pa.list_(pa.string())), ("pos", pa.string())])  # fields in sorted order
SCHEMA = pa.schema(
    [
        ("block_id", pa.int64()),
        ("ordinal", pa.int64()),
        ("text", pa.string()),
        ("start", pa.int64()),
        ("end", pa.int64()),
        ("attrs", ATTRS),
        ("heads", pa.list_(pa.int64())),
    ]
)
N_BLOCKS, PER_BLOCK, ROWS_PER_BATCH = 40, 50, 100
BLOCK_LEN = 10 * PER_BLOCK


def block_rows(b):
    rows = []
    for i in range(PER_BLOCK):
        start, end = 10 * i, 10 * i + 5
        rows.append(dict(block_id=b, ordinal=i, text=f"t{b}.{i}é", start=start, end=end,
                         attrs={"flags": ["f"] if i % 2 else [], "pos": "N"}, heads=[i - 1] if i else []))
    if b == 3:  # ordinal gap
        rows[10]["ordinal"] = 99
    if b == 5:  # overlap with previous span
        rows[20]["start"] = rows[19]["end"] - 2
    if b == 7:  # end beyond block length
        rows[-1]["end"] = BLOCK_LEN + 1
    if b == 9:  # duplicate ordinal
        rows[30]["ordinal"] = 29
    return rows


class Counting:
    """A generator-backed RecordBatchReader that counts pulled batches and the pulling threads."""

    def __init__(self):
        self.pulled = 0
        self.threads = set()

    def batches(self):
        rows = [r for b in range(N_BLOCKS) for r in block_rows(b)]
        for k in range(0, len(rows), ROWS_PER_BATCH):
            self.pulled += 1
            self.threads.add(threading.get_ident())
            yield pa.RecordBatch.from_pylist(rows[k:k + ROWS_PER_BATCH], schema=SCHEMA)

    def reader(self):
        return pa.RecordBatchReader.from_batches(SCHEMA, self.batches())


TOTAL_BATCHES = N_BLOCKS * PER_BLOCK // ROWS_PER_BATCH
blocks = pa.table({"block_id": list(range(N_BLOCKS)), "length": [BLOCK_LEN] * N_BLOCKS})

# One plan: scan -> join block lengths -> one window pass -> per-row failed-rule list -> per-block
# aggregate producing digest + typed diagnostics. Single reference to the streamed source.
FUSED = """
WITH w AS (
    SELECT t.*, b.length,
           row_number() OVER blk - 1                                   AS expected_ordinal,
           lag(t."end") OVER blk                                       AS prev_end,
           count(*) OVER (PARTITION BY t.block_id, t.ordinal)          AS same_ordinal
    FROM tokens AS t JOIN blocks AS b USING (block_id)
    WINDOW blk AS (PARTITION BY t.block_id ORDER BY t.ordinal, t.start)
), r AS (
    SELECT *, list_filter([
        CASE WHEN ordinal <> expected_ordinal THEN {'rule': 'ordinal_contiguity', 'ordinal': ordinal, 'detail': expected_ordinal} END,
        CASE WHEN start >= "end" OR start < coalesce(prev_end, 0) THEN {'rule': 'span_order', 'ordinal': ordinal, 'detail': prev_end} END,
        CASE WHEN start < 0 OR "end" > length THEN {'rule': 'containment', 'ordinal': ordinal, 'detail': length} END,
        CASE WHEN same_ordinal > 1 THEN {'rule': 'unique_ordinal', 'ordinal': ordinal, 'detail': same_ordinal} END
    ], lambda d: d IS NOT NULL) AS failures
    FROM w
)
SELECT block_id,
       count(*) AS n_tokens,
       sha256(to_json(list({'attrs': attrs, 'end': "end", 'heads': heads, 'ordinal': ordinal,
                            'start': start, 'text': nfc_normalize(text)} ORDER BY ordinal, start))::VARCHAR) AS digest,
       flatten(list(failures ORDER BY ordinal, start)) AS diagnostics
FROM r
GROUP BY block_id
"""

con = duckdb.connect(config={"TimeZone": "UTC", "threads": 4, "default_collation": "binary"})
con.register("blocks", blocks)


def expected():
    out = {}
    for b in range(N_BLOCKS):
        rows = sorted(block_rows(b), key=lambda r: (r["ordinal"], r["start"]))
        items = [{k: r[k] for k in ("attrs", "end", "heads", "ordinal", "start", "text")} for r in rows]
        out[b] = hashlib.sha256(canonical_json(items)).hexdigest()
    return out


# G1 laziness of relation construction and of the reader
src = Counting()
con.register("tokens", src.reader())
rel = con.sql(FUSED)
after_bind = src.pulled
reader = rel.to_arrow_reader(batch_size=8)
after_reader = src.pulled
first = reader.read_next_batch()
after_first = src.pulled
rest = [first] + list(reader)
reader.close()
result = pa.Table.from_batches(rest)
print(f"G1 pulled after con.sql: {after_bind}; after to_arrow_reader(): {after_reader}; after first output batch: {after_first}; total input batches {TOTAL_BATCHES}")
print(f"G1 output batches {len(rest)} (batch_size=8), rows {result.num_rows}; distinct pulling threads {len(src.threads)}; main thread among them: {threading.get_ident() in src.threads}")

exp = expected()
got = dict(zip(result["block_id"].to_pylist(), result["digest"].to_pylist()))
print("G2 digests equal canonical_json sha256 for all blocks:", all(got[b] == exp[b] for b in exp))
diag = {b: d for b, d in zip(result["block_id"].to_pylist(), result["diagnostics"].to_pylist()) if d}
print("G2 blocks with diagnostics:", sorted(diag))
for b in sorted(diag):
    print(f"   block {b}: {[(d['rule'], d['ordinal'], d['detail']) for d in diag[b]]}")
print("G2 diagnostics column type:", result.schema.field("diagnostics").type)

# G3 a second read of the same relation over a single-use reader
try:
    again = rel.to_arrow_table()
    print(f"G3 re-reading the relation over the consumed RecordBatchReader -> {again.num_rows} rows")
except duckdb.Error as e:
    print(f"G3 re-reading the relation over the consumed RecordBatchReader -> {type(e).__name__}: {str(e).splitlines()[0][:120]}")

# G4 streaming (non-blocking) query: does output arrive before the source is drained?
src2 = Counting()
con.register("tokens", src2.reader())
r2 = con.sql("SELECT block_id, ordinal, sha256(text) AS h FROM tokens WHERE start < \"end\"").to_arrow_reader(batch_size=64)
r2.read_next_batch()
print(f"G4 streaming projection: pulled {src2.pulled}/{TOTAL_BATCHES} after first output batch")
r2.close()
print(f"G4 after close(): pulled {src2.pulled}; connection usable: {con.sql('SELECT 42').fetchall() == [(42,)]}")

# G5 execute().to_arrow_reader() (DB-API result) on the same streaming query
src3 = Counting()
con.register("tokens", src3.reader())
r3 = con.execute("SELECT block_id, ordinal, sha256(text) AS h FROM tokens WHERE start < \"end\"").to_arrow_reader()
print(f"G5 execute().to_arrow_reader(): pulled {src3.pulled}/{TOTAL_BATCHES} before any batch read")
r3.read_all()
con.complete() if hasattr(con, "complete") else None

# G6 a source referenced twice (self-join / UNION of rule queries) with the default CTE policy
for policy in ("", "MATERIALIZED", "NOT MATERIALIZED"):
    src4 = Counting()
    con.register("tokens", src4.reader())
    q = f"""
    WITH t AS {policy} (SELECT * FROM tokens)
    SELECT (SELECT count(*) FROM t) AS a, (SELECT count(*) FROM t WHERE ordinal >= 0) AS b
    """
    try:
        print(f"G6 two references, CTE {policy or 'default'}: {con.sql(q).fetchall()} (expected ({N_BLOCKS * PER_BLOCK}, {N_BLOCKS * PER_BLOCK})), pulled {src4.pulled}")
    except duckdb.Error as e:
        print(f"G6 two references, CTE {policy or 'default'}: ERROR {type(e).__name__}: {str(e).splitlines()[0][:160]}")

# G7 plans: EXPLAIN of the fused query (fresh source), pushdown into the Arrow scan, range join
plans = []
src5 = Counting()
con.register("tokens", src5.reader())
plans.append(("EXPLAIN fused", con.sql("EXPLAIN " + FUSED).fetchall()[0][1]))
plans.append(("EXPLAIN pushdown", con.sql("EXPLAIN SELECT ordinal FROM tokens WHERE block_id = 3").fetchall()[0][1]))
tok_tbl = pa.Table.from_batches(list(Counting().reader()))
con.register("tok_tbl", tok_tbl)
sent = pa.table({"sid": [0, 1], "s_start": [0, 200], "s_end": [200, 500]})
con.register("sent", sent)
plans.append(("EXPLAIN pushdown (Arrow Table)", con.sql("EXPLAIN SELECT ordinal FROM tok_tbl WHERE block_id = 3").fetchall()[0][1]))
plans.append(("EXPLAIN containment range join", con.sql(
    "EXPLAIN SELECT s.sid, t.ordinal FROM tok_tbl t JOIN sent s ON t.start >= s.s_start AND t.\"end\" <= s.s_end").fetchall()[0][1]))
plans.append(("EXPLAIN overlap self-join", con.sql(
    "EXPLAIN SELECT a.ordinal, b.ordinal FROM tok_tbl a JOIN tok_tbl b ON a.block_id = b.block_id AND a.ordinal < b.ordinal AND a.start < b.\"end\" AND b.start < a.\"end\"").fetchall()[0][1]))
src6 = Counting()
con.register("tokens", src6.reader())
plans.append(("EXPLAIN ANALYZE fused", con.sql("EXPLAIN ANALYZE " + FUSED).fetchall()[0][1]))

# G8 multiple outputs from one statement: data-modifying CTE with COPY (2.0) + returned digests
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "diagnostics.parquet"
    src7 = Counting()
    con.register("tokens", src7.reader())
    q = f"""
    WITH fused AS MATERIALIZED ({FUSED}),
         written AS (COPY (SELECT block_id, unnest(diagnostics, recursive := true) FROM fused WHERE len(diagnostics) > 0 ORDER BY block_id)
                     TO '{target}' (FORMAT parquet, KV_METADATA {{producer: 'probe'}}))
    SELECT block_id, digest FROM fused ORDER BY block_id
    """
    try:
        out = con.sql(q).to_arrow_table()
        written = pq.read_table(target) if target.exists() else None
        print(f"G8 COPY in CTE: returned {out.num_rows} digest rows; parquet rows {None if written is None else written.num_rows}; "
              f"kv {None if written is None else pq.read_metadata(target).metadata.get(b'producer')}; pulled {src7.pulled}")
    except duckdb.Error as e:
        print(f"G8 COPY in CTE: ERROR {type(e).__name__}: {str(e).splitlines()[0][:200]}")

    # G9 temp-table route: materialize once, then two reads, then drop
    src8 = Counting()
    con.register("tokens", src8.reader())
    con.execute(f"CREATE TEMP TABLE fused_t AS {FUSED}")
    n_diag = con.sql("SELECT count(*) FROM (SELECT unnest(diagnostics) FROM fused_t)").fetchall()[0][0]
    n_dig = con.sql("SELECT count(digest) FROM fused_t").fetchall()[0][0]
    con.execute("DROP TABLE fused_t")
    print(f"G9 temp table: diagnostics {n_diag}, digests {n_dig}, pulled {src8.pulled}")

with open(Path(__file__).with_suffix(".plans.txt"), "w") as fh:
    for label, text in plans:
        fh.write(f"===== {label}\n{text}\n")
print("plans written to", Path(__file__).with_suffix(".plans.txt").name)
