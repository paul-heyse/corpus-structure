"""Probe C: are Arrow IPC bytes a deterministic digest basis for equal logical data?

Builds logically equal record batches by different routes (fresh, sliced, re-chunked,
validity bitmap present but all-valid, garbage under null slots, different dictionaries,
nested list<struct> slices) and compares `RecordBatch.equals` with sha256 over the IPC
stream bytes, before and after candidate normalizations. Synthetic data only.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/pyarrow/digest_determinism.py
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc

SPAN = pa.struct([("start", pa.int32()), ("stop", pa.int32())])
SCHEMA = pa.schema(
    [
        pa.field("block", pa.string(), nullable=False),
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("text", pa.string()),
        pa.field("spans", pa.list_(SPAN)),
        pa.field("score", pa.int64()),
    ],
    metadata={"cs.population": "token"},
)


def rows(n: int, start: int = 0) -> list[dict]:
    out = []
    for i in range(start, start + n):
        out.append(
            {
                "block": f"b{i // 4}",
                "ordinal": i,
                "text": "é" * (i % 3) + f"t{i}",
                "spans": [{"start": i, "stop": i + 1}] * (i % 3),
                "score": None if i % 5 == 0 else i * 10,
            }
        )
    return out


def ipc_bytes(data: pa.RecordBatch | pa.Table, options: ipc.IpcWriteOptions | None = None) -> pa.Buffer:
    sink = pa.BufferOutputStream()
    with ipc.new_stream(sink, data.schema, options=options) as writer:
        if isinstance(data, pa.Table):
            writer.write_table(data)
        else:
            writer.write_batch(data)
    return sink.getvalue()


def digest(data, options=None) -> str:
    # hashlib consumes the pa.Buffer through the buffer protocol; no bytes copy.
    return hashlib.sha256(ipc_bytes(data, options)).hexdigest()[:16]


def body_digest(batch: pa.RecordBatch) -> str:
    """Digest of only the record-batch message (schema message excluded)."""
    return hashlib.sha256(batch.serialize()).hexdigest()[:16]


def ipc_roundtrip(batch: pa.RecordBatch) -> pa.RecordBatch:
    return ipc.open_stream(ipc_bytes(batch)).read_next_batch()


def take_all(batch: pa.RecordBatch) -> pa.RecordBatch:
    return batch.take(pa.array(np.arange(batch.num_rows)))


def concat_cols(batch: pa.RecordBatch) -> pa.RecordBatch:
    return pa.RecordBatch.from_arrays(
        [pa.concat_arrays([c]) for c in batch.columns], schema=batch.schema
    )


results: dict[str, object] = {
    "python": sys.version.split()[0],
    "pyarrow": pa.__version__,
    "cases": {},
}
cases = results["cases"]

N = 40
fresh = pa.RecordBatch.from_pylist(rows(N), schema=SCHEMA)
big = pa.RecordBatch.from_pylist(rows(N + 13, start=0) + rows(7, start=N + 13), schema=SCHEMA)


def record(name: str, a: pa.RecordBatch, b: pa.RecordBatch, note: str = "") -> None:
    entry = {
        "equals": a.equals(b),
        "ipc_digest_equal": digest(a) == digest(b),
        "batch_message_equal": body_digest(a) == body_digest(b),
        "ipc_roundtrip_digest_equal": digest(ipc_roundtrip(a)) == digest(ipc_roundtrip(b)),
        "take_all_digest_equal": digest(take_all(a)) == digest(take_all(b)),
        "concat_arrays_digest_equal": digest(concat_cols(a)) == digest(concat_cols(b)),
    }
    if note:
        entry["note"] = note
    cases[name] = entry


# 1. sliced from a larger batch at a non-byte-aligned offset vs fresh
sliced = pa.RecordBatch.from_pylist(rows(N + 3), schema=SCHEMA).slice(3)
fresh_from3 = pa.RecordBatch.from_pylist(rows(N, start=3), schema=SCHEMA)
record("slice_offset3_vs_fresh", sliced, fresh_from3, "offset 3: validity bitmap and string offsets not rebased in memory")

# 2. sliced at offset 0 but shorter (buffers longer than needed)
head = pa.RecordBatch.from_pylist(rows(N + 20), schema=SCHEMA).slice(0, N)
record("slice_head_vs_fresh", head, fresh, "buffers extend past the slice")

# 2b. middle slice (leading and trailing parent bytes) vs fresh
middle = pa.RecordBatch.from_pylist(rows(N + 30), schema=SCHEMA).slice(3, N)
record("slice_middle_vs_fresh", middle, fresh_from3, "offset 3, buffers extend past the slice")

# 2c. per-type isolation of the head-slice difference
def single(arr):
    return pa.RecordBatch.from_arrays([arr], names=["x"])


per_type = {}
for label, make in {
    "int64_no_nulls": lambda n: pa.array(list(range(n)), pa.int64()),
    "int64_nullable": lambda n: pa.array([None if i % 5 == 0 else i for i in range(n)], pa.int64()),
    "string_no_nulls": lambda n: pa.array([str(i) for i in range(n)]),
    "list_int": lambda n: pa.array([[i] for i in range(n)]),
}.items():
    head_slice = make(100).slice(0, 40)
    mid_slice = make(100).slice(3, 40)
    per_type[label] = {
        "head_ipc_equal": digest(single(head_slice)) == digest(single(make(40))),
        "middle_ipc_equal": digest(single(mid_slice)) == digest(single(make(43).slice(3).take(pa.array(range(40))))),
        "head_buffer_sizes_vs_fresh": [
            [b.size if b is not None else None for b in head_slice.buffers()],
            [b.size if b is not None else None for b in make(40).buffers()],
        ],
    }
cases["slice_per_type"] = per_type

# 3. validity bitmap present but all valid vs absent
vals = np.arange(N, dtype=np.int64)
no_bitmap = pa.array(vals)
with_bitmap = pa.array(vals, mask=np.zeros(N, dtype=bool))
b1 = pa.RecordBatch.from_arrays([no_bitmap], names=["x"])
b2 = pa.RecordBatch.from_arrays([with_bitmap], names=["x"])
cases["validity_present_all_valid"] = {
    "bitmap_buffers": [str(no_bitmap.buffers()[0]), str(with_bitmap.buffers()[0] is not None)],
    "equals": b1.equals(b2),
    "ipc_digest_equal": digest(b1) == digest(b2),
}

# 4. garbage under a null slot (values buffer differs where validity is 0)
values_a = np.array([1, 0, 3], dtype=np.int64)
values_b = np.array([1, 999, 3], dtype=np.int64)
validity = pa.array([True, False, True]).buffers()[1]
garbage_a = pa.Array.from_buffers(pa.int64(), 3, [validity, pa.py_buffer(values_a)], null_count=1)
garbage_b = pa.Array.from_buffers(pa.int64(), 3, [validity, pa.py_buffer(values_b)], null_count=1)
ga = pa.RecordBatch.from_arrays([garbage_a], names=["x"])
gb = pa.RecordBatch.from_arrays([garbage_b], names=["x"])
garbage_entry = {
    "equals": ga.equals(gb),
    "ipc_digest_equal": digest(ga) == digest(gb),
    "ipc_roundtrip_digest_equal": digest(ipc_roundtrip(ga)) == digest(ipc_roundtrip(gb)),
    "take_all_digest_equal": digest(take_all(ga)) == digest(take_all(gb)),
    "concat_arrays_digest_equal": digest(concat_cols(ga)) == digest(concat_cols(gb)),
}
# candidate null-slot normalization: if_else(is_valid, x, null) and fill_null-then-mask
norm = lambda arr: pc.if_else(pc.is_valid(arr), arr, pa.scalar(None, arr.type))  # noqa: E731
garbage_entry["if_else_norm_digest_equal"] = digest(
    pa.RecordBatch.from_arrays([norm(garbage_a)], names=["x"])
) == digest(pa.RecordBatch.from_arrays([norm(garbage_b)], names=["x"]))
# python round trip as the reference normalizer
garbage_entry["from_pylist_digest_equal"] = digest(
    pa.RecordBatch.from_pylist(ga.to_pylist(), schema=ga.schema)
) == digest(pa.RecordBatch.from_pylist(gb.to_pylist(), schema=gb.schema))
cases["garbage_under_null_slot"] = garbage_entry

# 4b. garbage under a null string slot (offsets give the null a non-empty extent)
offs_a = np.array([0, 1, 1, 2], dtype=np.int32)
offs_b = np.array([0, 1, 4, 5], dtype=np.int32)
sa = pa.Array.from_buffers(pa.string(), 3, [validity, pa.py_buffer(offs_a), pa.py_buffer(b"ac")], null_count=1)
sb = pa.Array.from_buffers(pa.string(), 3, [validity, pa.py_buffer(offs_b), pa.py_buffer(b"axyzc")], null_count=1)
sa.validate(full=True)
sb.validate(full=True)
sba = pa.RecordBatch.from_arrays([sa], names=["s"])
sbb = pa.RecordBatch.from_arrays([sb], names=["s"])
cases["string_null_slot_nonempty_extent"] = {
    "equals": sba.equals(sbb),
    "ipc_digest_equal": digest(sba) == digest(sbb),
    "take_all_digest_equal": digest(take_all(sba)) == digest(take_all(sbb)),
    "if_else_norm_digest_equal": digest(pa.RecordBatch.from_arrays([norm(sa)], names=["s"]))
    == digest(pa.RecordBatch.from_arrays([norm(sb)], names=["s"])),
}

# 5. dictionary-encoded column with different dictionary order, same logical values
words = ["b", "a", "b", "c"]
d1 = pa.array(words).dictionary_encode()
d2 = pa.DictionaryArray.from_arrays(pa.array([2, 0, 2, 1], pa.int32()), pa.array(["a", "c", "b"]))
db1 = pa.RecordBatch.from_arrays([d1], names=["w"])
db2 = pa.RecordBatch.from_arrays([d2], names=["w"])
cases["dictionary_order"] = {
    "logical_values_equal": d1.to_pylist() == d2.to_pylist(),
    "equals": db1.equals(db2),
    "ipc_digest_equal": digest(db1) == digest(db2),
    "decoded_digest_equal": digest(pa.RecordBatch.from_arrays([d1.dictionary_decode()], names=["w"]))
    == digest(pa.RecordBatch.from_arrays([d2.dictionary_decode()], names=["w"])),
}

# 6. chunking: one table of one batch vs a table of three batches
t_one = pa.Table.from_batches([fresh])
t_three = pa.Table.from_batches([fresh.slice(0, 10), fresh.slice(10, 17), fresh.slice(27)])
cases["table_chunking"] = {
    "equals": t_one.equals(t_three),
    "ipc_digest_equal": digest(t_one) == digest(t_three),
    "combine_chunks_digest_equal": digest(t_one.combine_chunks()) == digest(t_three.combine_chunks()),
    "to_batches_counts": [len(t_one.combine_chunks().to_batches()), len(t_three.combine_chunks().to_batches())],
}

# 7. schema metadata difference: equals ignores it by default, the IPC schema message does not
meta_b = fresh.replace_schema_metadata({"cs.population": "other"})
cases["schema_metadata"] = {
    "equals_default": fresh.equals(meta_b),
    "equals_check_metadata": fresh.equals(meta_b, check_metadata=True),
    "ipc_digest_equal": digest(fresh) == digest(meta_b),
    "batch_message_equal": body_digest(fresh) == body_digest(meta_b),
}

# 8. repeat-run determinism and compression
cases["repeat_and_compression"] = {
    "same_object_twice": digest(fresh) == digest(fresh),
    "zstd_twice": digest(fresh, ipc.IpcWriteOptions(compression="zstd"))
    == digest(fresh, ipc.IpcWriteOptions(compression="zstd")),
    "zstd_vs_uncompressed": digest(fresh, ipc.IpcWriteOptions(compression="zstd")) == digest(fresh),
}

# 9. nested list<struct> sliced from inside a larger list array
spans_big = big.column("spans")
spans_slice = spans_big.slice(5, 20)
spans_fresh = pa.array(spans_slice.to_pylist(), type=spans_big.type)
nb1 = pa.RecordBatch.from_arrays([spans_slice], names=["spans"])
nb2 = pa.RecordBatch.from_arrays([spans_fresh], names=["spans"])
cases["nested_list_struct_slice"] = {
    "list_offsets_first": [spans_slice.offsets[0].as_py(), spans_fresh.offsets[0].as_py()],
    "equals": nb1.equals(nb2),
    "ipc_digest_equal": digest(nb1) == digest(nb2),
}

# 10. pickle uses out-of-band buffers under protocol 5 (no copy of column bodies)
oob: list = []
payload = pickle.dumps(pa.Table.from_batches([fresh]), protocol=5, buffer_callback=oob.append)
cases["pickle_protocol5"] = {
    "inband_bytes": len(payload),
    "out_of_band_buffers": len(oob),
    "table_nbytes": pa.Table.from_batches([fresh]).nbytes,
}

# 11. validate(full=True) does not enforce field nullability
bad = pa.RecordBatch.from_arrays(
    [pa.array(["x", None]), pa.array([1, 2])],
    schema=pa.schema([pa.field("block", pa.string(), nullable=False), pa.field("ordinal", pa.int64())]),
)
try:
    bad.validate(full=True)
    nullable_check = "accepted null in non-nullable field"
except pa.ArrowInvalid as exc:  # pragma: no cover - documents the alternative
    nullable_check = f"rejected: {exc}"
cases["validate_full_nullability"] = nullable_check

json.dump(results, sys.stdout, indent=2, default=str)
print()
