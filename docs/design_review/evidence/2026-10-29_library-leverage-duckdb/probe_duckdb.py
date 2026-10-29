"""Pure-Python DuckDB 2.0.0 probe for the library-leverage assessment (no database server).

Questions: (1) does `DuckDBPyRelation.query` scope an input name to the call and stay lazy;
(2) can a table macro bind several per-operation inputs by passing names as values through
`query_table`, without rewriting SQL text; (3) does `COPY ... (FORMAT parquet, KV_METADATA ...)`
write file-level key-value metadata readable by DuckDB and pyarrow; (4) does Arrow schema/field
metadata survive a DuckDB round trip.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

out: dict[str, object] = {"duckdb": duckdb.__version__, "pyarrow": pa.__version__}
con = duckdb.connect(":memory:")


def catalog_names() -> list[str]:
    return sorted(
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables ORDER BY table_name"
        ).fetchall()
    )


# (1) relation.query scoped name and laziness
base = con.sql("SELECT * FROM range(5) t(x)")
before = catalog_names()
scoped = base.query("candidate_input", "SELECT sum(x) AS s FROM candidate_input")
after = catalog_names()
out["q1_query_scoped_result"] = scoped.fetchall()
out["q1_query_reread"] = scoped.fetchall()
out["q1_catalog_unchanged"] = before == after
try:
    con.sql("SELECT * FROM candidate_input").fetchall()
    out["q1_name_leaks_after_call"] = True
except duckdb.Error as error:
    out["q1_name_leaks_after_call"] = False
    out["q1_lookup_error"] = type(error).__name__

# (2) table macro with per-operation names passed as values via query_table
left = pa.table({"k": [1, 2, 3], "v": ["a", "b", "c"]})
right = pa.table({"k": [2, 3, 4], "w": [20, 30, 40]})
con.register("op7_view_claims", left)
con.register("op7_view_entities", right)
con.execute(
    """
    CREATE TEMP MACRO kernel(view_claims, view_entities) AS TABLE
    SELECT c.k, c.v, e.w
    FROM query_table(view_claims) c JOIN query_table(view_entities) e USING (k)
    ORDER BY c.k
    """
)
try:
    rel = con.sql("FROM kernel('op7_view_claims', 'op7_view_entities')")
    out["q2_macro_result"] = rel.fetchall()
    out["q2_macro_reread"] = rel.fetchall()
    out["q2_macro_bind_ok"] = True
except duckdb.Error as error:
    out["q2_macro_bind_ok"] = False
    out["q2_macro_error"] = f"{type(error).__name__}: {error}"

# (2b) a relation made into a uniquely named view, consumed via the macro
view_rel = con.sql("SELECT * FROM range(2, 5) t(k)").project("k, k * 10 AS w")
view_rel.create_view("op8_view_entities")
try:
    out["q2b_view_via_macro"] = con.sql(
        "FROM kernel('op7_view_claims', 'op8_view_entities')"
    ).fetchall()
except duckdb.Error as error:
    out["q2b_view_via_macro"] = f"{type(error).__name__}: {error}"

# (3) COPY TO parquet with file-level KV metadata
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "export.parquet"
    con.execute(
        f"COPY (SELECT * FROM op7_view_claims) TO '{path}' "
        "(FORMAT parquet, KV_METADATA {cs_release: 'release:abc', cs_revision: '7'})"
    )
    kv = con.execute(
        f"SELECT decode(key), decode(value) FROM parquet_kv_metadata('{path}') ORDER BY 1"
    ).fetchall()
    out["q3_duckdb_kv"] = kv
    meta = pq.read_metadata(path).metadata or {}
    out["q3_pyarrow_kv"] = sorted(
        (k.decode(), v.decode()) for k, v in meta.items() if k.startswith(b"cs_")
    )

# (4) Arrow schema/field metadata through DuckDB
tagged = pa.table(
    {"x": pa.array([1, 2], pa.int64())},
    schema=pa.schema(
        [pa.field("x", pa.int64(), metadata={"cs.field": "f"})], metadata={"cs.release": "r"}
    ),
)
con.register("tagged", tagged)
back = con.sql("SELECT * FROM tagged").to_arrow_table()
out["q4_schema_metadata_after_roundtrip"] = (
    {k.decode(): v.decode() for k, v in back.schema.metadata.items()}
    if back.schema.metadata
    else None
)
out["q4_field_metadata_after_roundtrip"] = (
    {k.decode(): v.decode() for k, v in back.schema.field("x").metadata.items()}
    if back.schema.field("x").metadata
    else None
)

print(json.dumps(out, indent=2, default=str))
