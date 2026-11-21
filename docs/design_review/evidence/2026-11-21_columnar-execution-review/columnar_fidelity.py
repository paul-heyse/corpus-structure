"""Expressibility and fidelity checks behind the columnar-execution review.

In memory only: no repository files, no PostgreSQL. Each check prints PASS/DIFF and the
observation the review cites. Run: uv run python <this file>
"""

import hashlib
import json
import sqlite3
from decimal import Decimal

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
from duckdb import col, fn, lit

con = duckdb.connect(config={"TimeZone": "UTC", "threads": 1})
print("duckdb", duckdb.__version__, "pyarrow", pa.__version__)


def show(name, same, note=""):
    print(f"{'SAME' if same else 'DIFF'}  {name}{'  | ' + note if note else ''}")


# --- E: typed expressions (no SQL text) express the span and window forms -------------
tok = pa.table({"doc": ["d"] * 5, "i": [0, 1, 2, 3, 4], "s": [0, 4, 10, 15, 20], "e": [3, 9, 13, 19, 24]})
sent = pa.table({"doc": ["d", "d"], "sid": ["s0", "s1"], "s": [0, 15], "e": [13, 24]})
t, sn = con.from_arrow(tok).set_alias("t"), con.from_arrow(sent).set_alias("sn")
inside = (col("t", "doc") == col("sn", "doc")) & (col("t", "s") >= col("sn", "s")) & (col("t", "e") <= col("sn", "e"))
j = t.join(sn, inside).select(
    col("t", "i").alias("i"), col("t", "s").alias("s"), col("t", "e").alias("e"), col("sn", "sid").alias("sid")
)
ordinal = j.select(
    col("i"), (fn("row_number").over(partition_by=[col("sid")], order_by=[col("s")]) - lit(1)).alias("o")
).sort(col("i")).fetchall()
show("E1 containment join + ordinal within parent", ordinal == [(0, 0), (1, 1), (2, 2), (3, 0), (4, 1)])
gap = j.select(col("i"), (col("s") - fn("lag", col("e")).over(order_by=[col("s")])).alias("g")).sort(col("i")).fetchall()
show("E2 previous-end gap (lag)", gap == [(0, None), (1, 1), (2, 1), (3, 2), (4, 1)])
run = j.select(col("i"), fn("sum", col("e") - col("s")).over(order_by=[col("s")], rows=(None, 0)).alias("r")).sort(col("i")).fetchall()
show("E3 running sum, rows frame", run == [(0, 3), (1, 8), (2, 11), (3, 15), (4, 19)])
near = j.select(col("i"), fn("count", col("i")).over(order_by=[col("s")], range=(-6, 0)).alias("n")).sort(col("i")).fetchall()
show("E4 integer range frame", near == [(0, 1), (1, 2), (2, 2), (3, 2), (4, 2)])
brk = j.select(
    col("i"), col("s"),
    fn("ifnull", (col("s") - fn("lag", col("e")).over(order_by=[col("s")])) > lit(1), lit(False)).cast("INTEGER").alias("b"),
)
isl = brk.select(col("i"), fn("sum", col("b")).over(order_by=[col("s")]).alias("k")).sort(col("i")).fetchall()
show("E5 gaps-and-islands in two stages", isl == [(0, 0), (1, 0), (2, 0), (3, 1), (4, 1)])
first = j.select(col("i"), col("sid"), fn("row_number").over(partition_by=[col("sid")], order_by=[col("s")]).alias("rn")).filter(col("rn") == lit(1)).sort(col("i")).fetchall()
show("E6 first-per-key by filter on a window column", [r[0] for r in first] == [0, 3])
asof = t.join(sn, (col("t", "doc") == col("sn", "doc")) & (col("t", "s") >= col("sn", "s")), how="asof").select(col("t", "i"), col("sn", "sid")).sort(col("i")).fetchall()
show("E7 nearest preceding (ASOF join)", [r[1] for r in asof] == ["s0", "s0", "s0", "s1", "s1"])
bag = con.from_arrow(pa.table({"x": [1, 1, 1, 2]})).except_(con.from_arrow(pa.table({"x": [1]}))).sort(col("x")).fetchall()
show("E8 relation except_ keeps multiplicity (bag)", [r[0] for r in bag] == [1, 1, 2])

# --- O: ordering ---------------------------------------------------------------------
keys = ["a", "B", "b", "A", "aa", "a ", "é", "é", "Z", "z", "\U0001f600", "�", "", "10", "2",
        "#/tables/10", "#/tables/2", "", "ab", "aé", "a!", "ß"]
want = sorted(keys, key=lambda k: k.encode())
dd = [r[0] for r in con.from_arrow(pa.table({"k": keys})).sort(col("k")).fetchall()]
pa_ = pa.table({"k": keys}).sort_by("k")["k"].to_pylist()
sq = sqlite3.connect(":memory:")
sq.execute("create table t(k text)")
sq.executemany("insert into t values (?)", [(k,) for k in keys])
sl = [r[0] for r in sq.execute("select k from t order by k collate binary")]
show("O1 UTF-8 byte order: DuckDB default / pyarrow / SQLite BINARY / Python str", dd == want and pa_ == want and sl == want and sorted(keys) == want)
jk = sorted(keys, key=lambda k: json.dumps(["f", k]))
show("O2 order of json.dumps([family, id]) text vs byte order of id", jk == want, "JSON-text keys escape non-ASCII, so order differs")
nulls = [r[0] for r in con.sql("select x from (values (1),(null),(0)) v(x) order by x").fetchall()]
show("O3 NULL placement vs Python (x is not None, x)", nulls == [None, 0, 1], f"DuckDB default gives {nulls}; needs NULLS FIRST")

# --- I: identity bytes ---------------------------------------------------------------
def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


row = {"start": 4, "end": 9, "kind": "token", "block_id": "b é"}
dj = con.execute("select to_json(struct_pack(block_id := ?, \"end\" := ?, kind := ?, start := ?))", [row["block_id"], 9, "token", 4]).fetchall()[0][0]
show("I1 to_json == canonical bytes for str/int with fields in sorted order", dj.encode() == canon(row))
show("I2 sha256 of that text", con.execute("select sha256(?)", [dj]).fetchall()[0][0] == hashlib.sha256(canon(row)).hexdigest())
fl = con.sql("select to_json(1e-7::double), to_json(1e16::double), to_json(2.5e-5::double)").fetchall()[0]
show("I3 float spelling", list(fl) == [json.dumps(1e-7), json.dumps(1e16), json.dumps(2.5e-5)], f"DuckDB {list(fl)} vs Python {[json.dumps(x) for x in (1e-7, 1e16, 2.5e-5)]}")
show("I4 decimal text keeps declared scale", con.sql("select cast('1.5' as decimal(10,3))::varchar").fetchall()[0][0] == str(Decimal("1.5")), "DuckDB prints 1.500")

# --- S: semantics that differ --------------------------------------------------------
sp = con.execute("select regexp_matches(?, '^\\s$'), regexp_matches(?, '^\\w$')", [" ", "é"]).fetchall()[0]
show("S1 RE2 \\s and \\w are ASCII-only", sp == (" ".isspace(), True), f"DuckDB {sp}; pyarrow utf8_is_space={pc.utf8_is_space(pa.array([' ']))[0].as_py()}")
lv = con.execute("select levenshtein('café','cafe')").fetchall()[0][0]
show("S2 levenshtein counts characters", lv == 1, f"DuckDB {lv} (bytes)")
ba = con.sql("select bool_and(x) from (select true as x where false)").fetchall()[0][0]
show("S3 bool_and over empty group == all([])", ba is True, f"DuckDB {ba}")
xs = [1e16, 1.0, -1e16]
ds = con.execute("select sum(x) from (select unnest(?::double[]) x)", [xs]).fetchall()[0][0]
show("S4 float sum == Python sum", ds == sum(xs), f"DuckDB {ds} vs Python {sum(xs)}")
try:
    con.from_arrow(pa.table({"u": pa.UnionArray.from_dense(pa.array([0], pa.int8()), pa.array([0], pa.int32()), [pa.array([1])])})).fetchall()
    dense = True
except Exception as error:  # noqa: BLE001
    dense = False
show("S5 dense union imports into DuckDB", dense, "use sparse union or struct+discriminator")


# --- X: extension types over text are opaque to the engine -----------------------------
class ExactInteger(pa.ExtensionType):
    def __init__(self):
        super().__init__(pa.string(), "review.exact_integer")

    def __arrow_ext_serialize__(self):
        return b""

    @classmethod
    def __arrow_ext_deserialize__(cls, storage_type, serialized):
        return cls()


pa.register_extension_type(ExactInteger())
exact = pa.ExtensionArray.from_storage(ExactInteger(), pa.array(["10", "2", "99999999999999999999999"]))
back = con.from_arrow(pa.table({"n": exact})).sort(col("n")).to_arrow_table()
show("X1 extension type survives a DuckDB round trip", back.schema.field("n").type == ExactInteger(), f"returns {back.schema.field('n').type}")
show("X2 exact integers held as text sort numerically", back["n"].to_pylist() == ["2", "10", "99999999999999999999999"], f"sorted as {back['n'].to_pylist()}")
