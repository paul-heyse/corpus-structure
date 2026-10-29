"""Pure-Python probes against installed pyarrow (no database, no network).

P1  Parquet / dataset key-value metadata round trip (schema- and field-level).
P2  Decimal: string->decimal casts, rescale refusal, pc.round HALF_EVEN on decimals,
    compared with an independent stdlib Decimal reference (quantize, HALF_EVEN, prec 38).
P3  Float hexadecimal spelling through Arrow casts.
P4  IPC stream round trip of schema/field metadata.
"""

from __future__ import annotations

import sys
import tempfile
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq


def show(label, fn):
    try:
        out = fn()
        print(f"  {label}: OK -> {out}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {label}: {type(exc).__name__}: {exc}")


print("python", sys.version.split()[0], "pyarrow", pa.__version__)

# ---------------------------------------------------------------- P1
print("\nP1 Parquet/dataset metadata round trip")
schema_md = {b"cs.release": b"r1", b"cs.projection": b"projection:abc", b"cs.relation": b"fact"}
fields = [
    pa.field("fact_id", pa.string(), nullable=False, metadata={b"cs.field": b"id"}),
    pa.field("decimal_value", pa.decimal128(38, 12), metadata={b"cs.scale": b"12"}),
    pa.field("datetime_value", pa.timestamp("ns", tz="UTC")),
    pa.field("flag", pa.bool_(), nullable=False),
]
schema = pa.schema(fields, metadata=schema_md)
table = pa.Table.from_pylist(
    [
        {"fact_id": "f1", "decimal_value": Decimal("1.000000000002"), "datetime_value": 1, "flag": True},
        {"fact_id": "f2", "decimal_value": None, "datetime_value": None, "flag": False},
    ],
    schema=schema,
)
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    def rt(path, **kw):
        pq.write_table(table, path, **kw)
        back = pq.read_table(path)
        return back

    for label, kw in [
        ("write_table default", {}),
        ("write_table store_schema=False", {"store_schema": False}),
        ("write_table version=2.6 coerce_timestamps=None", {"version": "2.6"}),
    ]:
        back = rt(tmp / f"{label.replace(' ', '_')}.parquet", **kw)
        print(f"  {label}:")
        print("    schema.equals(check_metadata=True):", back.schema.equals(schema, check_metadata=True))
        print("    schema metadata keys:", sorted(back.schema.metadata or {}))
        print("    field metadata:", {f.name: dict(f.metadata or {}) for f in back.schema})
        print("    types:", [str(f.type) for f in back.schema], "nullable:", [f.nullable for f in back.schema])
        print("    values equal:", back.equals(table))
    # raw parquet footer key-value metadata
    md = pq.read_metadata(tmp / "write_table_default.parquet")
    print("  footer KV keys (default):", sorted(md.metadata))
    md2 = pq.read_metadata(tmp / "write_table_store_schema=False.parquet")
    print("  footer KV keys (store_schema=False):", md2.metadata)

    # ParquetWriter incremental batches
    p = tmp / "writer.parquet"
    with pq.ParquetWriter(p, schema) as w:
        for b in table.to_batches(max_chunksize=1):
            w.write_batch(b)
    back = pq.read_table(p)
    print("  ParquetWriter batches: equals(check_metadata=True):", back.schema.equals(schema, check_metadata=True))

    # dataset writer, table input
    d = tmp / "ds_table"
    ds.write_dataset(table, d, format="parquet")
    back = ds.dataset(d, format="parquet").to_table()
    print("  write_dataset(table) -> ds.dataset().to_table(): equals(check_metadata=True):",
          back.schema.equals(schema, check_metadata=True), "schema md:", back.schema.metadata)
    back2 = pq.read_table(d)
    print("  write_dataset(table) -> pq.read_table(dir): equals(check_metadata=True):",
          back2.schema.equals(schema, check_metadata=True))
    # dataset writer, reader input (incremental)
    d2 = tmp / "ds_reader"
    reader = pa.RecordBatchReader.from_batches(schema, table.to_batches(max_chunksize=1))
    ds.write_dataset(reader, d2, format="parquet")
    back = ds.dataset(d2, format="parquet").to_table()
    print("  write_dataset(reader): equals(check_metadata=True):", back.schema.equals(schema, check_metadata=True))
    # dataset writer with explicit schema without metadata
    d3 = tmp / "ds_explicit_schema"
    ds.write_dataset(table, d3, format="parquet", schema=schema.remove_metadata())
    back = ds.dataset(d3, format="parquet").to_table()
    print("  write_dataset(schema=metadata-stripped): schema md:", back.schema.metadata)
    # dataset writer with partitioning on a column
    d4 = tmp / "ds_partitioned"
    ds.write_dataset(table, d4, format="parquet", partitioning=["flag"], partitioning_flavor="hive")
    frag_paths = sorted(str(p.relative_to(d4)) for p in d4.rglob("*.parquet"))
    one = pq.read_table(d4 / frag_paths[0])
    print("  partitioned fragment file schema md:", one.schema.metadata, "fields:", one.schema.names)
    # file_visitor exposes per-file metadata
    seen = []
    ds.write_dataset(table, tmp / "ds_visit", format="parquet",
                     file_visitor=lambda wf: seen.append(sorted(wf.metadata.metadata)))
    print("  file_visitor footer KV keys:", seen)
    # metadata of a projected/filtered dataset scan
    back = ds.dataset(d, format="parquet").to_table(columns=["fact_id", "flag"], filter=pc.field("flag"))
    print("  projected scan schema md:", back.schema.metadata,
          "field md:", {f.name: dict(f.metadata or {}) for f in back.schema})
    # select / cast effects on metadata in memory
    print("  Table.select keeps schema md:", table.select(["fact_id"]).schema.metadata == schema_md)
    print("  Table.cast(target w/o md) md:", table.cast(schema.remove_metadata()).schema.metadata)

# ---------------------------------------------------------------- P2
print("\nP2 Decimal behaviour")
PREC, SCALE = 38, 12


def reference(lexical):
    """Independent stdlib reference of the profile policy (quantize HALF_EVEN, refuse)."""
    v = Decimal(lexical)
    if not v.is_finite() or (v and v.adjusted() >= PREC - SCALE):
        return "refuse"
    try:
        r = v.quantize(Decimal((0, (1,), -SCALE)), context=Context(prec=PREC, rounding=ROUND_HALF_EVEN))
    except InvalidOperation:
        return "refuse"
    if r and r.adjusted() >= PREC - SCALE:
        return "refuse"
    return (r, r != v)


t12 = pa.decimal128(PREC, SCALE)
show("cast '1.0000000000015' -> decimal128(38,12) safe",
     lambda: pa.array(["1.0000000000015"]).cast(t12))
show("cast '1.0000000000015' -> decimal128(38,12) safe=False",
     lambda: pa.array(["1.0000000000015"]).cast(t12, safe=False))
show("decimal128(38,13) 1.0000000000015 -> decimal128(38,12) safe",
     lambda: pa.array([Decimal("1.0000000000015")], pa.decimal128(38, 13)).cast(t12))
show("decimal128(38,13) -> (38,12) safe=False (truncate?)",
     lambda: pa.array([Decimal("1.0000000000015"), Decimal("-1.0000000000019")], pa.decimal128(38, 13)).cast(t12, safe=False))
show("pc.round on decimal128(38,13) ndigits=12 half_to_even (type kept?)",
     lambda: (lambda r: (r.type, r.to_pylist()))(pc.round(pa.array([Decimal("1.0000000000015"), Decimal("1.0000000000025"), Decimal("-1.0000000000025")], pa.decimal128(38, 13)), ndigits=12, round_mode="half_to_even")))
show("cast exponent strings -> decimal128(38,12)",
     lambda: pa.array(["1E+5", "1.5e-3", "-0", "0E-20", "1.000000000000E+2"]).cast(t12).to_pylist())
show("cast 'NaN' -> decimal", lambda: pa.array(["NaN"]).cast(t12))
show("cast 'Infinity' -> decimal", lambda: pa.array(["Infinity"]).cast(t12))
show("cast '  1.5' (whitespace) -> decimal", lambda: pa.array([" 1.5"]).cast(t12))
show("cast '+1.5' -> decimal", lambda: pa.array(["+1.5"]).cast(t12))
show("cast '.5' -> decimal", lambda: pa.array([".5"]).cast(t12))
show("cast 27 integer digits -> decimal128(38,12)",
     lambda: pa.array(["1" + "0" * 26]).cast(t12))
show("round overflow 99..9.9999999999995 (26 int digits) in decimal128(38,13) -> ndigits 12",
     lambda: pc.round(pa.array([Decimal("9" * 25 + "." + "9" * 13)], pa.decimal128(38, 13)), ndigits=12).to_pylist())

# Vectorized candidate: string -> decimal256(76, S) -> round(12, HALF_EVEN) -> cast decimal128(38,12)
S = 40
mid = pa.decimal256(76, S)
vectors = [
    "1.0000000000015", "1.0000000000025", "-1.0000000000025", "0.0000000000005",
    "0.0000000000015", "-0.0000000000005", "123.456", "1E+5", "1.5E-13", "2.5E-12",
    "0", "-0", "0E-20", "1e-30", "12345678901234567890123456", "99999999999999999999999999.9999999999995",
    "1" + "0" * 26, "NaN", "Infinity", "1e-41", "1." + "0" * 45 + "1", "100%", None,
]


def vectorized(lexicals):
    arr = pa.array(lexicals, pa.string())
    wide = arr.cast(mid)  # safe: refuses digits beyond scale S or beyond precision 76
    rounded = pc.round(wide, ndigits=SCALE, round_mode="half_to_even")
    narrow = rounded.cast(t12)  # safe: exact after rounding; refuses > 26 integer digits
    flag = pc.not_equal(rounded, wide)
    return narrow, flag


print("  per-value comparison of vectorized route vs stdlib reference:")
agree = disagree = 0
for lex in vectors:
    ref = None if lex is None else reference(lex) if lex != "100%" else "error"
    try:
        n, f = vectorized([lex])
        got = (n[0].as_py(), f[0].as_py())
        if got[0] is None:
            got = None
    except Exception as exc:  # noqa: BLE001
        got = f"refuse<{type(exc).__name__}: {str(exc)[:70]}>"
    ok = (
        (ref is None and got is None)
        or (ref in ("refuse", "error") and isinstance(got, str))
        or (isinstance(ref, tuple) and isinstance(got, tuple) and ref[0] == got[0] and ref[1] == got[1])
    )
    agree += ok
    disagree += not ok
    print(f"    {'agree' if ok else 'DIFFER'}  {lex!r:>50}  ref={ref}  arrow={got}")
print(f"  agree={agree} differ={disagree}")
print("  note: a whole-array cast fails on the first refusing element (all-or-nothing):")
show("vectorized(['1.5','NaN'])", lambda: vectorized(["1.5", "NaN"]))

# ---------------------------------------------------------------- P3
print("\nP3 float hexadecimal spelling")
h = (1.5).hex()
show(f"cast {h!r} -> float64", lambda: pa.array([h]).cast(pa.float64()).to_pylist())
show("cast '-0x0.0p+0' -> float64", lambda: pa.array(["-0x0.0p+0"]).cast(pa.float64()).to_pylist())
show("cast '5e-324' -> float64 (decimal text, subnormal)", lambda: pa.array(["5e-324"]).cast(pa.float64()).to_pylist())
show("cast '-0.0' -> float64 signbit", lambda: pc.sign(pa.array(["-0.0"]).cast(pa.float64())).to_pylist())
show("utf8 functions available for hex parse? (no 'parse_hex_float' kernel)",
     lambda: [n for n in pc.list_functions() if "hex" in n or "fromhex" in n])

# ---------------------------------------------------------------- P4
print("\nP4 IPC stream metadata round trip")
sink = pa.BufferOutputStream()
with pa.ipc.new_stream(sink, schema) as w:
    w.write_table(table)
buf = sink.getvalue()
back = pa.ipc.open_stream(buf).read_all()
print("  IPC equals(check_metadata=True):", back.schema.equals(schema, check_metadata=True))
print("  sink.getvalue() is immutable Buffer:", type(buf).__name__, "is_mutable=", buf.is_mutable)
